"""
整棟工務每日巡檢 — 多 Sheet 同步核心（RF / B1F / B2F / B4F / B1~B4 共用）

流程（逐來源 sheet_key 執行，互不影響）：
  1. RagicAdapter 拉取該 Sheet 所有 Row
  2. 動態偵測設備欄位（排除場次 metadata 與系統欄位）
  3. 量測/程度型欄位判定（整份資料掃描一次）
  4. 每個 Row → 1 筆 batch（ragic_id = {sheet_key}_{row_id}）＋ N 筆 item
  5. 同 batch 的舊 item 先刪再寫；刪除範圍只限該 batch，不會影響其他 Sheet

⚠️ 不可改回單一 Sheet 寫死的 ID（例如直接存 Ragic Row ID），
   否則不同 Sheet 的相同 Row ID 會互相覆蓋（2026-10-30 實測：Sheet 9 與 Sheet 12 都有 ID 0）。
"""
import logging
import re
from typing import Any

from app.core.database import SessionLocal
from app.core.time import twnow
from app.services.inspection_field_rules import (
    MEASURE_STATUS, build_measure_fields, is_equipment_field,
)

# 非設備欄位（附件／附註／系統）的狀態值：不參與 KPI，也不算異常
META_STATUS = "meta"
from app.services.inspection_sources import (
    ACCOUNT, SERVER_URL, InspectionSource, make_batch_id, sources_for,
)
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── 場次 metadata 欄位（不視為設備巡檢欄位）──────────────────────────────────
# 「預估時間」＝工單預排分鐘數，存入 batch.estimated_minutes，不是設備項目
SESSION_FIELDS = {
    "巡檢人員",
    "開始巡檢時間",
    "巡檢結束時間",
    "工時計算",
    "預估時間",
    "_ragicId",
    "_owner",
    "_create",
    "_modify",
}

CK_INSPECTOR  = "巡檢人員"
CK_START_TIME = "開始巡檢時間"
CK_END_TIME   = "巡檢結束時間"
CK_WORK_HOURS = "工時計算"
CK_ESTIMATED  = "預估時間"

# ── 巡檢結果 → result_status 對照 ────────────────────────────────────────────
RESULT_STATUS_MAP: dict[str, str] = {
    "正常":   "normal",
    "OK":     "normal",
    "ok":     "normal",
    "O":      "normal",
    "異常":   "abnormal",
    "待處理": "pending",
    "待修":   "pending",
    "待修繕": "pending",
    "X":      "abnormal",
}

_DATE_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")
_NUM_RE  = re.compile(r"\d+(?:\.\d+)?")


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _extract_date(raw_datetime: str) -> str:
    """從 '2026/4/14 09:26'、'2026-08-03 09:26' 萃取 YYYY/MM/DD。

    ⚠️ 不可改回 raw[:10] 的切法（2026-08-24 修正，月日同為個位數時會切進時間）。
    解析不出來回空字串。
    """
    m = _DATE_RE.search(raw_datetime or "")
    if not m:
        return ""
    year, month, day = m.groups()
    return f"{year}/{int(month):02d}/{int(day):02d}"


def _parse_minutes(raw: str) -> int | None:
    """'124' / '45.999999998' → 整數分鐘；解析不到回 None。"""
    m = _NUM_RE.search(raw or "")
    if not m:
        return None
    return int(round(float(m.group())))


def _normalize_result_status(raw: str) -> tuple[str, bool]:
    raw = (raw or "").strip()
    status = RESULT_STATUS_MAP.get(raw, "unchecked" if not raw else "abnormal")
    return status, status in ("abnormal", "pending")


def _extract_check_items(row: dict) -> list[str]:
    """動態提取巡檢設備欄位清單，排除 metadata 與系統欄位。"""
    items = []
    for key in row.keys():
        if key in SESSION_FIELDS:
            continue
        if str(key).startswith("_"):
            continue
        try:
            int(key)
            continue
        except (ValueError, TypeError):
            pass
        items.append(key)
    return items


async def _sync_one_source(
    src: InspectionSource,
    Batch: type,
    Item: type,
    log_tag: str,
) -> dict:
    """同步單一 Sheet。回傳該來源的摘要（fetched / upserted / item_rows / errors）。"""
    result: dict[str, Any] = {
        "sheet_key": src.sheet_key,
        "archived":  src.archived,
        "fetched": 0, "upserted": 0, "item_rows": 0,
        "check_item_count": 0, "errors": [],
    }
    adapter = RagicAdapter(sheet_path=src.sheet_path, server_url=SERVER_URL, account=ACCOUNT)
    logger.info(f"[{log_tag}] 開始同步 {src.sheet_key}（{src.sheet_path}）...")

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[{log_tag}] {src.sheet_key} 拉取失敗：{exc}")
        result["errors"].append(f"{src.sheet_key} 拉取失敗：{exc}")
        return result

    fetched = len(raw_data)
    result["fetched"] = fetched
    now = twnow()

    check_items: list[str] = []
    if fetched > 0:
        first_rec = raw_data[next(iter(raw_data))]
        check_items = _extract_check_items(first_rec)
        result["check_item_count"] = len(check_items)

    measure_fields: set = set()
    if fetched > 0:
        measure_fields = build_measure_fields(
            raw_data, check_items, set(RESULT_STATUS_MAP.keys()), _stringify,
        )

    db = SessionLocal()
    try:
        for row_id, raw in raw_data.items():
            bid = make_batch_id(src.sheet_key, row_id)
            try:
                start_raw = _stringify(raw.get(CK_START_TIME, ""))
                existing = db.get(Batch, bid)
                fields = dict(
                    sheet_key         = src.sheet_key,
                    inspection_date   = _extract_date(start_raw),
                    inspector_name    = _stringify(raw.get(CK_INSPECTOR, "")),
                    start_time        = start_raw,
                    end_time          = _stringify(raw.get(CK_END_TIME, "")),
                    work_hours        = _stringify(raw.get(CK_WORK_HOURS, "")),
                    estimated_minutes = _parse_minutes(_stringify(raw.get(CK_ESTIMATED, ""))),
                    synced_at         = now,
                )
                if existing:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                else:
                    db.add(Batch(ragic_id=bid, **fields))

                db.query(Item).filter(Item.batch_ragic_id == bid).delete(synchronize_session=False)

                row_check_items = check_items or _extract_check_items(raw)
                for seq, col_name in enumerate(row_check_items, start=1):
                    result_raw = _stringify(raw.get(col_name, ""))
                    result_status, abnormal_flag = _normalize_result_status(result_raw)
                    # 附件／附註／系統欄位（拍照、異常說明、建立日期…）不是設備結果：
                    # 標為 meta 且不算異常，否则儀表板的異常數會被檔名與說明文字灌水。
                    if not is_equipment_field(col_name, result_raw):
                        result_status, abnormal_flag = META_STATUS, False
                    # 量測/程度型欄位：有填就是「已記錄」，不是異常；空白仍記為未檢
                    elif result_raw and col_name in measure_fields:
                        result_status, abnormal_flag = MEASURE_STATUS, False

                    db.add(Item(
                        ragic_id       = f"{bid}_{seq}",
                        sheet_key      = src.sheet_key,
                        batch_ragic_id = bid,
                        seq_no         = seq,
                        item_name      = col_name,
                        result_raw     = result_raw,
                        result_status  = result_status,
                        abnormal_flag  = abnormal_flag,
                        synced_at      = now,
                    ))
                    result["item_rows"] += 1

                result["upserted"] += 1
            except Exception as exc:
                result["errors"].append(f"{src.sheet_key} row={row_id}: {exc}")
                logger.warning(f"[{log_tag}] {src.sheet_key} 記錄 {row_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[{log_tag}] {src.sheet_key} 完成：fetched={fetched}, "
            f"batches={result['upserted']}, items={result['item_rows']}, "
            f"errors={len(result['errors'])}"
        )
    except Exception as exc:
        db.rollback()
        result["errors"].append(f"{src.sheet_key} DB commit error: {exc}")
        logger.error(f"[{log_tag}] {src.sheet_key} DB 寫入失敗：{exc}")
    finally:
        db.close()

    return result


async def sync_floor_sources(floor: str, Batch: type, Item: type, log_tag: str) -> dict:
    """同步某樓層的所有來源（含封存來源），彙總成一份摘要。"""
    summary: dict[str, Any] = {
        "floor": floor,
        "fetched": 0, "upserted": 0, "item_rows": 0,
        "check_item_count": 0, "errors": [], "sources": {},
    }
    for src in sources_for(floor):
        res = await _sync_one_source(src, Batch, Item, log_tag)
        summary["sources"][src.sheet_key] = res
        for k in ("fetched", "upserted", "item_rows", "check_item_count"):
            summary[k] += res[k]
        summary["errors"].extend(res["errors"])
    return summary
