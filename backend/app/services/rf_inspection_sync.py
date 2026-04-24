"""
整棟工務每日巡檢 - RF 同步服務【寬表格 Pivot 架構 + 動態欄位偵測】

資料來源：
  https://ap12.ragic.com/soutlet001/full-building-inspection/1

【結構說明】
  Ragic Sheet 1 每一 Row = 一次完整巡檢場次（寬表格格式）
  場次欄位：巡檢人員、開始巡檢時間、巡檢結束時間、工時計算
  結果欄位：N 個設備/項目欄位，各自儲存 正常/異常 等狀態值

【動態欄位偵測】
  不硬編碼 CHECK_ITEMS；同步時自動掃描 Ragic Row 的所有欄位，
  排除已知的場次 metadata 欄位後，其餘視為設備巡檢欄位。
  好處：RF Sheet 增減欄位時，無需修改程式碼。
"""
import logging
from datetime import datetime, timezone
from app.core.time import twnow
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.rf_inspection import RFInspectionBatch, RFInspectionItem
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ────────────────────────────────────────────────────────────
RF_SERVER_URL = getattr(settings, "RAGIC_RF_SERVER_URL",  "ap12.ragic.com")
RF_ACCOUNT    = getattr(settings, "RAGIC_RF_ACCOUNT",     "soutlet001")
RF_SHEET_PATH = getattr(settings, "RAGIC_RF_SHEET_PATH",  "full-building-inspection/1")

# ── Ragic 場次欄位 key（已知 metadata，不視為設備巡檢欄位）────────────────────
SESSION_FIELDS = {
    "巡檢人員",
    "開始巡檢時間",
    "巡檢結束時間",
    "工時計算",
    # Ragic 系統欄位（通常以 _ 開頭或為數字型 id）
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


# ── 轉換輔助函式 ──────────────────────────────────────────────────────────────

def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _extract_date(raw_datetime: str) -> str:
    """從 '2026/4/14 09:26' 或 '2026-04-14 09:26' 萃取 YYYY/MM/DD。"""
    raw = (raw_datetime or "").strip()
    if not raw:
        return ""
    date_part = raw[:10].replace("-", "/")
    parts = date_part.split("/")
    if len(parts) == 3:
        try:
            return f"{parts[0]}/{int(parts[1]):02d}/{int(parts[2]):02d}"
        except ValueError:
            pass
    return date_part


def _normalize_result_status(raw: str) -> tuple[str, bool]:
    """將原始值轉為正規化狀態與異常旗標。"""
    raw = (raw or "").strip()
    status = RESULT_STATUS_MAP.get(raw, "unchecked" if not raw else "abnormal")
    return status, status in ("abnormal", "pending")


def _extract_check_items(row: dict) -> list[str]:
    """
    從 Ragic Row dict 動態提取巡檢設備欄位清單。
    排除場次 metadata 欄位、系統欄位（底線開頭）及純數字 key。
    """
    items = []
    for key in row.keys():
        if key in SESSION_FIELDS:
            continue
        if str(key).startswith("_"):
            continue
        try:
            int(key)  # 數字型 key（Ragic field ID）跳過
            continue
        except (ValueError, TypeError):
            pass
        items.append(key)
    return items


# ── 同步主程式 ────────────────────────────────────────────────────────────────

async def sync_from_ragic() -> dict:
    """
    從 Ragic Sheet 1 同步：
      每個 Row → 1 筆 RFInspectionBatch + pivot 成 N 筆 RFInspectionItem。
    動態偵測設備欄位，無需預先定義 CHECK_ITEMS。
    """
    adapter = RagicAdapter(
        sheet_path=RF_SHEET_PATH,
        server_url=RF_SERVER_URL,
        account=RF_ACCOUNT,
    )
    logger.info("[RFSync] 開始同步（寬表格 Pivot + 動態欄位偵測）...")

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        logger.error(f"[RFSync] 拉取失敗：{exc}")
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [str(exc)]}

    fetched   = len(raw_data)
    upserted  = 0
    item_rows = 0
    errors: list[str] = []
    now = twnow()

    # 從第一筆記錄取得設備欄位清單（所有 Row 欄位結構相同）
    check_items: list[str] = []
    if fetched > 0:
        first_id  = next(iter(raw_data))
        first_rec = raw_data[first_id]
        check_items = _extract_check_items(first_rec)
        logger.info(
            f"[RFSync] 第一筆 id={first_id}, "
            f"偵測到 {len(check_items)} 個設備欄位：{check_items}"
        )

    db = SessionLocal()
    try:
        for ragic_id, raw in raw_data.items():
            batch_id = str(ragic_id)
            try:
                # ── 1. 寫入場次（Batch）──────────────────────────────────────
                start_raw = _stringify(raw.get(CK_START_TIME, ""))
                batch = RFInspectionBatch(
                    ragic_id        = batch_id,
                    inspection_date = _extract_date(start_raw),
                    inspector_name  = _stringify(raw.get(CK_INSPECTOR, "")),
                    start_time      = start_raw,
                    end_time        = _stringify(raw.get(CK_END_TIME, "")),
                    work_hours      = _stringify(raw.get(CK_WORK_HOURS, "")),
                    synced_at       = now,
                )

                existing_batch = db.get(RFInspectionBatch, batch_id)
                if existing_batch:
                    existing_batch.inspection_date = batch.inspection_date
                    existing_batch.inspector_name  = batch.inspector_name
                    existing_batch.start_time      = batch.start_time
                    existing_batch.end_time        = batch.end_time
                    existing_batch.work_hours      = batch.work_hours
                    existing_batch.synced_at       = now
                else:
                    db.add(batch)

                # ── 2. 清除舊 Items，再 Pivot 產生新 Items ───────────────────
                db.query(RFInspectionItem).filter(
                    RFInspectionItem.batch_ragic_id == batch_id
                ).delete(synchronize_session=False)

                row_check_items = check_items or _extract_check_items(raw)
                for seq, col_name in enumerate(row_check_items, start=1):
                    result_raw = _stringify(raw.get(col_name, ""))
                    result_status, abnormal_flag = _normalize_result_status(result_raw)

                    db.add(RFInspectionItem(
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
                logger.warning(f"[RFSync] 記錄 {ragic_id} 失敗：{exc}")

        db.commit()
        logger.info(
            f"[RFSync] 完成：fetched={fetched}, batches_upserted={upserted}, "
            f"items={item_rows}, errors={len(errors)}"
        )
    except Exception as exc:
        db.rollback()
        errors.append(f"DB commit error: {exc}")
        logger.error(f"[RFSync] DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {
        "fetched":    fetched,
        "upserted":   upserted,
        "item_rows":  item_rows,
        "check_item_count": len(check_items),
        "errors":     errors,
    }
