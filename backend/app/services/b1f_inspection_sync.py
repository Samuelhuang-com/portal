"""
整棟工務每日巡檢 - B1F 同步服務【寬表格 Pivot 架構 + 動態欄位偵測】

資料來源：
  https://ap12.ragic.com/soutlet001/full-building-inspection/4

【結構說明】
  Ragic Sheet 4 每一 Row = 一次完整巡檢場次（寬表格格式）
  場次欄位：巡檢人員、開始巡檢時間、巡檢結束時間、工時計算
  結果欄位：N 個設備/項目欄位，各自儲存 正常/異常 等狀態值

【動態欄位偵測】
  不硬編碼 CHECK_ITEMS；同步時自動掃描 Ragic Row 的所有欄位，
  排除已知的場次 metadata 欄位後，其餘視為設備巡檢欄位。
"""
import logging
import re
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.b1f_inspection import B1FInspectionBatch, B1FInspectionItem
from app.services.inspection_field_rules import (
    MEASURE_STATUS, build_measure_fields,
)
from app.services.ragic_adapter import RagicAdapter
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ────────────────────────────────────────────────────────────
B1F_SERVER_URL = getattr(settings, "RAGIC_B1F_SERVER_URL",  "ap12.ragic.com")
B1F_ACCOUNT    = getattr(settings, "RAGIC_B1F_ACCOUNT",     "soutlet001")
B1F_SHEET_PATH = getattr(settings, "RAGIC_B1F_SHEET_PATH",  "full-building-inspection/4")

# ── Ragic 場次欄位 key（已知 metadata，不視為設備巡檢欄位）────────────────────
SESSION_FIELDS = {
    "巡檢人員",
    "開始巡檢時間",
    "巡檢結束時間",
    "工時計算",
    "_ragicId",
    "_owner",
    "_create",
    "_modify",
}

CK_INSPECTOR  = "巡檢人員"
CK_START_TIME = "開始巡檢時間"
CK_END_TIME   = "巡檢結束時間"
CK_WORK_HOURS = "工時計算"

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
    raw = (raw or "").strip()
    status = RESULT_STATUS_MAP.get(raw, "unchecked" if not raw else "abnormal")
    return status, status in ("abnormal", "pending")


def _extract_check_items(row: dict) -> list[str]:
    """動態提取巡檢設備欄位清單，排除 metadata 和系統欄位。"""
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


@register("b1f_inspection")
async def sync_from_ragic() -> dict:
    """
    從 Ragic Sheet 4 同步：
      每個 Row → 1 筆 B1FInspectionBatch + pivot 成 N 筆 B1FInspectionItem。
    """
    adapter = RagicAdapter(
        sheet_path=B1F_SHEET_PATH,
        server_url=B1F_SERVER_URL,
        account=B1F_ACCOUNT,
    )
    logger.info("[B1FSync] 開始同步（寬表格 Pivot + 動態欄位偵測）...")

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[B1FSync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [str(exc)]}

    fetched   = len(raw_data)
    upserted  = 0
    item_rows = 0
    errors: list[str] = []
    now = twnow()

    check_items: list[str] = []
    if fetched > 0:
        first_id  = next(iter(raw_data))
        first_rec = raw_data[first_id]
        check_items = _extract_check_items(first_rec)
        logger.info(
            f"[B1FSync] 第一筆 id={first_id}, "
            f"偵測到 {len(check_items)} 個設備欄位：{check_items}"
        )

    # ── 欄位型別判定（整份資料掃一次）──────────────────────────────────────
    # 值域裡從未出現過「正常／異常」的欄位＝量測/程度型（水位＝高/中/低、
    # 電瓶電壓＝靜置12.4V~12.7V…），其值標為 measure，**不算異常**。
    # ⚠️ 必須用整份資料判定，不可只看單筆 —— 只看一筆的話，「隔熱材是否完好」
    #    那筆值為「查修表」的場次會被誤判成量測型，同一欄位在不同場次型別不同。
    measure_fields: set = set()
    if fetched > 0:
        measure_fields = build_measure_fields(
            raw_data, check_items, set(RESULT_STATUS_MAP.keys()), _stringify,
        )
        if measure_fields:
            logger.info(
                f"[B1FSync] 量測/程度型欄位 {len(measure_fields)} 個："
                f"{sorted(measure_fields)}"
            )

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            batch_id = str(ragic_id)
            try:
                start_raw = _stringify(raw.get(CK_START_TIME, ""))
                batch = B1FInspectionBatch(
                    ragic_id        = batch_id,
                    inspection_date = _extract_date(start_raw),
                    inspector_name  = _stringify(raw.get(CK_INSPECTOR, "")),
                    start_time      = start_raw,
                    end_time        = _stringify(raw.get(CK_END_TIME, "")),
                    work_hours      = _stringify(raw.get(CK_WORK_HOURS, "")),
                    synced_at       = now,
                )

                existing_batch = db.get(B1FInspectionBatch, batch_id)
                if existing_batch:
                    existing_batch.inspection_date = batch.inspection_date
                    existing_batch.inspector_name  = batch.inspector_name
                    existing_batch.start_time      = batch.start_time
                    existing_batch.end_time        = batch.end_time
                    existing_batch.work_hours      = batch.work_hours
                    existing_batch.synced_at       = now
                else:
                    db.add(batch)

                db.query(B1FInspectionItem).filter(
                    B1FInspectionItem.batch_ragic_id == batch_id
                ).delete(synchronize_session=False)

                row_check_items = check_items or _extract_check_items(raw)
                for seq, col_name in enumerate(row_check_items, start=1):
                    result_raw = _stringify(raw.get(col_name, ""))
                    result_status, abnormal_flag = _normalize_result_status(result_raw)
                    # 量測/程度型欄位：有填就是「已記錄」，不是異常
                    if result_raw and col_name in measure_fields:
                        result_status, abnormal_flag = MEASURE_STATUS, False

                    db.add(B1FInspectionItem(
                        ragic_id       = f"{batch_id}_{seq}",
                        batch_ragic_id = batch_id,
                        seq_no         = seq,
                        item_name      = col_name,
                        result_raw     = result_raw,
                        result_status  = result_status,
                        abnormal_flag  = abnormal_flag,
                        synced_at      = now,
                    ))
                    item_rows += 1

                upserted += 1

            except Exception as exc:
                errors.append(f"ragic_id={ragic_id}: {exc}")
                logger.warning(f"[B1FSync] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[B1FSync] 完成：fetched={fetched}, batches_upserted={upserted}, "
            f"items={item_rows}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[B1FSync] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {
        "fetched":          fetched,
        "upserted":         upserted,
        "item_rows":        item_rows,
        "check_item_count": len(check_items),
        "errors":           errors,
    }
