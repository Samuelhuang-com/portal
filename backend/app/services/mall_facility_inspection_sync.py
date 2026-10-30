"""
春大直商場工務每日巡檢 同步服務【統一 Sync + 寬表格 Pivot + 動態欄位偵測】

支援 5 張 Ragic Sheet（mall-facility-inspection/2、3、4、5、7）。
所有 Sheet 結構相同：
  每一 Row = 一次完整巡檢場次（寬表格格式）
  場次欄位：巡檢人員、開始/結束巡檢時間、工時計算
  結果欄位：N 個設備/項目欄，各自儲存 正常/異常 等狀態值

【動態欄位偵測】
  同步時自動掃描欄位，排除已知 metadata 欄位後，其餘視為巡檢點欄位。
"""
import logging
import re
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.mall_facility_inspection import MallFIBatch, MallFIItem
from app.services.ragic_adapter import RagicAdapter
from app.services.sync_dispatcher import register
from app.services.sync_result import aggregate_sync_results

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ─────────────────────────────────────────────────────────────
MFI_SERVER_URL = getattr(settings, "RAGIC_MFI_SERVER_URL", "ap12.ragic.com")
MFI_ACCOUNT    = getattr(settings, "RAGIC_MFI_ACCOUNT",    "soutlet001")

# ── Sheet 設定表 ──────────────────────────────────────────────────────────────
_TAB_NAMES: dict[str, str] = {
    "1-4f":    "商場工務每日巡檢 - 1F ~ 4F",
    "4f":      "商場工務每日巡檢 - 4F",
    "3f":      "商場工務每日巡檢 - 3F",
    "1f-3f":   "商場工務每日巡檢 - 1F ~ 3F",
    "1f":      "商場工務每日巡檢 - 1F",
    "b1f-b4f": "商場工務每日巡檢 - B1F ~ B4F",
}
# 頁籤 → 現行來源路徑（僅供舊有引用相容；實際同步依 mall_facility_sources.SOURCES）
SHEET_CONFIGS: dict[str, dict] = {
    tab: {"path": "", "name": name} for tab, name in _TAB_NAMES.items()
}

# ── 場次 metadata 欄位（不視為巡檢點）────────────────────────────────────────
SESSION_FIELDS = {
    "巡檢人員",
    "預估時間",
    "保全人員",
    "工務人員",
    "開始巡檢時間",
    "開始時間",
    "巡檢開始時間",
    "巡檢結束時間",
    "結束時間",
    "結束巡檢時間",
    "工時計算",
    "巡檢日期",
    "日期",
    "_ragicId",
    "_owner",
    "_create",
    "_modify",
}

# 常用的場次欄位 key（候選清單，sync 時逐一嘗試）
INSPECTOR_CANDIDATES  = ["巡檢人員", "工務人員", "保全人員"]
START_TIME_CANDIDATES = ["開始巡檢時間", "開始時間", "巡檢開始時間", "巡檢日期", "日期"]
END_TIME_CANDIDATES   = ["巡檢結束時間", "結束時間", "結束巡檢時間"]
WORK_HOURS_CANDIDATES = ["工時計算"]

# ── 巡檢結果 → result_status 對照 ────────────────────────────────────────────
RESULT_STATUS_MAP: dict[str, str] = {
    "正常":   "normal",
    "OK":     "normal",
    "ok":     "normal",
    "O":      "normal",
    "✓":      "normal",
    "V":      "normal",
    "v":      "normal",
    "異常":   "abnormal",
    "待處理": "pending",
    "待修":   "pending",
    "待修繕": "pending",
    "X":      "abnormal",
    "x":      "abnormal",
}


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


# 允許 2026/8/3、2026-08-03、2026/08/03 三種寫法；後面接不接時間都可以
_DATE_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")


def _extract_date(raw_datetime: str) -> str:
    """從 '2026/4/14 09:26'、'2026-04-14 09:26'、'2026/8/3 09:26' 萃取 YYYY/MM/DD。

    ⚠️ 不可改回 raw[:10] 的切法（2026-08-24 修正）。
       月與日**同時**是個位數又帶時間時，前 10 碼會切進時間裡：
           '2026/8/3 09:26'[:10] == '2026/8/3 0'
       split('/') 得到 ['2026', '8', '3 0']，int('3 0') 直接 ValueError，
       於是原樣回傳 '2026/8/3 0' —— 這個值不會 match 任何 LIKE 'YYYY/MM%'，
       那筆資料總筆數對得上卻永遠落不進任何月份，統計看不到它且不會報錯。
       解析不出來一律回空字串，與「來源欄位為空」同一種表示法。
    """
    m = _DATE_RE.search(raw_datetime or "")
    if not m:
        return ""
    year, month, day = m.groups()
    return f"{year}/{int(month):02d}/{int(day):02d}"


def _normalize_result_status(raw: str) -> tuple[str, bool]:
    """將原始值轉為正規化狀態與異常旗標。"""
    raw = (raw or "").strip()
    status = RESULT_STATUS_MAP.get(raw, "unchecked" if not raw else "abnormal")
    return status, status in ("abnormal", "pending")


def _pick_field(raw: dict, candidates: list[str]) -> str:
    """從候選欄位清單中挑選第一個存在且有值的欄位。"""
    for key in candidates:
        val = _stringify(raw.get(key, ""))
        if val:
            return val
    return ""


def _extract_check_items(row: dict) -> list[str]:
    """
    從 Ragic Row dict 動態提取巡檢點欄位清單。
    排除場次 metadata 欄位、系統欄位（底線開頭）、純數字 key，
    以及拍照欄位（含「拍照」字樣）。
    """
    items = []
    for key in row.keys():
        if key in SESSION_FIELDS:
            continue
        if str(key).startswith("_"):
            continue
        if "拍照" in str(key):
            continue
        try:
            int(key)  # 數字型 key 跳過
            continue
        except (ValueError, TypeError):
            pass
        items.append(key)
    return items


# ── 單一頁籤同步（頁籤下的所有來源：現行＋封存） ─────────────────────────────

def _parse_minutes(raw: str) -> int | None:
    m = re.search(r"\d+(?:\.\d+)?", raw or "")
    return int(round(float(m.group()))) if m else None


async def _sync_one_source(src, tab: str, log_tag: str) -> dict:
    """同步單一 Ragic Sheet（來源）。場次 ID = {source_key}_{Row ID}，sheet_key = 頁籤。"""
    from app.services.mall_daily_inspection_sheet import item_status

    adapter = RagicAdapter(sheet_path=src.sheet_path, server_url=MFI_SERVER_URL, account=MFI_ACCOUNT)
    logger.info(f"[{log_tag}] 開始同步 {src.source_key}（{src.sheet_path}）...")
    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[{log_tag}] {src.source_key} 拉取失敗：{exc}")
        return {"source_key": src.source_key, "fetched": 0, "upserted": 0, "item_rows": 0,
                "errors": [f"{src.source_key} 拉取失敗：{exc}"]}

    fetched = len(raw_data)
    upserted = 0
    item_rows = 0
    errors: list[str] = []
    now = twnow()

    check_items: list[str] = []
    if fetched > 0:
        check_items = _extract_check_items(next(iter(raw_data.values())))

    db = SessionLocal()
    try:
        for ragic_row_id, raw in raw_data.items():
            batch_id = f"{src.source_key}_{ragic_row_id}"
            try:
                start_raw = _pick_field(raw, START_TIME_CANDIDATES)
                fields = dict(
                    sheet_key         = tab,
                    sheet_name        = _TAB_NAMES.get(tab, tab),
                    inspection_date   = _extract_date(start_raw),
                    inspector_name    = _pick_field(raw, INSPECTOR_CANDIDATES),
                    start_time        = start_raw,
                    end_time          = _pick_field(raw, END_TIME_CANDIDATES),
                    work_hours        = _pick_field(raw, WORK_HOURS_CANDIDATES),
                    estimated_minutes = _parse_minutes(_pick_field(raw, ["預估時間"])),
                    synced_at         = now,
                )
                existing = db.get(MallFIBatch, batch_id)
                if existing:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                else:
                    db.add(MallFIBatch(ragic_id=batch_id, **fields))

                db.query(MallFIItem).filter(MallFIItem.batch_ragic_id == batch_id).delete(synchronize_session=False)

                row_check_items = check_items or _extract_check_items(raw)
                for seq, col_name in enumerate(row_check_items, start=1):
                    result_raw = _stringify(raw.get(col_name, ""))
                    is_note = "異常說明" in str(col_name)
                    # 與畫面、每日巡檢表同一套規則（mall_daily_inspection_sheet.item_status）
                    result_status = item_status(tab, col_name, result_raw, is_note)
                    abnormal_flag = result_status in ("abnormal", "pending")

                    db.add(MallFIItem(
                        ragic_id       = f"{batch_id}_{seq}",
                        batch_ragic_id = batch_id,
                        sheet_key      = tab,
                        seq_no         = seq,
                        item_name      = col_name,
                        result_raw     = result_raw,
                        result_status  = result_status,
                        abnormal_flag  = abnormal_flag,
                        is_note        = is_note,
                        synced_at      = now,
                    ))
                    item_rows += 1
                upserted += 1
            except Exception as exc:
                errors.append(f"{src.source_key} row={ragic_row_id}: {exc}")
                logger.warning(f"[{log_tag}] {src.source_key} 記錄 {ragic_row_id} 失敗：{exc}")

        db.commit()
        logger.info(f"[{log_tag}] {src.source_key} 完成：fetched={fetched}, batches={upserted}, items={item_rows}, errors={len(errors)}")
    except Exception as exc:
        db.rollback()
        errors.append(f"{src.source_key} DB commit error: {exc}")
        logger.error(f"[{log_tag}] {src.source_key} DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"source_key": src.source_key, "fetched": fetched, "upserted": upserted,
            "item_rows": item_rows, "check_item_count": len(check_items), "errors": errors}


async def sync_sheet(sheet_key: str) -> dict:
    """同步指定頁籤（sheet_key）下的所有來源（含封存）。"""
    from app.services.mall_facility_sources import sources_for
    if sheet_key not in SHEET_CONFIGS:
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [f"未知的 sheet_key: {sheet_key}"]}
    summary = {"fetched": 0, "upserted": 0, "item_rows": 0, "check_item_count": 0, "errors": [], "sources": {}}
    for src in sources_for(sheet_key):
        res = await _sync_one_source(src, sheet_key, "MFISync")
        summary["sources"][src.source_key] = res
        for k in ("fetched", "upserted", "item_rows", "check_item_count"):
            summary[k] += res.get(k, 0)
        summary["errors"].extend(res.get("errors", []))
    return summary


# ── 全部頁籤同步 ──────────────────────────────────────────────────────────────

@register("mall_facility_inspection")
async def sync_all() -> dict:
    """同步所有頁籤（每個頁籤包含其現行與封存來源）。"""
    results = {}
    for sheet_key in SHEET_CONFIGS:
        results[sheet_key] = await sync_sheet(sheet_key)
    return aggregate_sync_results(results)
