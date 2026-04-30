"""
每日數值登錄表 同步服務【統一 Sync + 寬表格 Pivot + 動態欄位偵測】

支援 4 張 Ragic Sheet（hotel-routine-inspection/11、12、14、15）。
  Sheet 11: 全棟電錶
  Sheet 12: 商場空調箱電錶
  Sheet 14: 專櫃電錶
  Sheet 15: 專櫃水錶

【動態欄位偵測】
  同步時自動掃描欄位，排除已知 metadata 欄位後，其餘視為儀表讀數欄位。
  欄位名稱以實際 Ragic 表單為準。

【注意】
  以下欄位名稱為候選清單，如 Ragic 表單欄位名不符請修改 METADATA_FIELDS、
  DATE_CANDIDATES、RECORDER_CANDIDATES 等常數。
"""
import logging
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.hotel_meter_readings import HotelMRBatch, HotelMRReading
from app.services.ragic_adapter import RagicAdapter

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ─────────────────────────────────────────────────────────────
HMR_SERVER_URL = getattr(settings, "RAGIC_HDI_SERVER_URL", "ap12.ragic.com")
HMR_ACCOUNT    = getattr(settings, "RAGIC_HDI_ACCOUNT",    "soutlet001")

# ── Sheet 設定表 ──────────────────────────────────────────────────────────────
# hotel-routine-inspection（注意：與 daily-inspection 使用的 main-project-inspection 不同）
SHEET_CONFIGS: dict[str, dict] = {
    "building-electric": {
        "path": "hotel-routine-inspection/11",
        "name": "全棟電錶",
    },
    "mall-ac-electric": {
        "path": "hotel-routine-inspection/12",
        "name": "商場空調箱電錶",
    },
    "tenant-electric": {
        "path": "hotel-routine-inspection/14",
        "name": "專櫃電錶",
    },
    "tenant-water": {
        "path": "hotel-routine-inspection/15",
        "name": "專櫃水錶",
    },
}

# ── 場次 metadata 欄位（不視為儀表讀數欄位）──────────────────────────────────
# TODO: 若 Ragic 實際欄位名稱與下列不符，請修改此集合
METADATA_FIELDS: set[str] = {
    # 日期欄位候選
    "登錄日期",
    "記錄日期",
    "日期",
    "填寫日期",
    "抄表日期",
    # 人員欄位候選
    "登錄人員",
    "記錄人員",
    "人員",
    "填寫人員",
    "抄表人員",
    # Ragic 系統欄位
    "_ragicId",
    "_owner",
    "_create",
    "_modify",
    "_approval",
    "_approvalLog",
}

# ── 登錄日期欄位候選（依優先順序）────────────────────────────────────────────
# TODO: 確認 Ragic 表單實際欄位名稱
DATE_CANDIDATES = ["登錄日期", "抄表日期", "日期", "記錄日期", "填寫日期"]

# ── 登錄人員欄位候選（依優先順序）────────────────────────────────────────────
# TODO: 確認 Ragic 表單實際欄位名稱
RECORDER_CANDIDATES = ["登錄人員", "抄表人員", "記錄人員", "人員", "填寫人員"]


# ── 欄位值輔助函式 ─────────────────────────────────────────────────────────────

def _pick_field(row: dict, candidates: list[str], default: str = "") -> str:
    """從候選欄位清單中，取第一個有值的欄位"""
    for key in candidates:
        val = row.get(key, "")
        if val and str(val).strip():
            return str(val).strip()
    return default


def _extract_date(raw: str) -> str:
    """
    從各種日期格式萃取 YYYY/MM/DD。
    Ragic 常見格式：
      2026/04/30 00:00       → 2026/04/30
      2026-04-30             → 2026/04/30
      2026/04/30             → 2026/04/30（原樣返回）
    """
    if not raw:
        return ""
    raw = raw.strip()
    # 取空格前的日期部分
    date_part = raw.split(" ")[0]
    # 統一用 / 分隔
    return date_part.replace("-", "/")


def _extract_meter_fields(row: dict) -> list[tuple[int, str, str]]:
    """
    動態偵測並萃取儀表讀數欄位。

    排除規則（不視為讀數欄位）：
      1. 在 METADATA_FIELDS 集合中的欄位
      2. 以底線 _ 開頭的欄位（Ragic 系統欄位）
      3. 純數字 key（Ragic 內部 ID）
      4. 空值欄位不排除（保留讀數為空的情況）

    返回：[(seq_no, meter_name, reading_value), ...]
    """
    results: list[tuple[int, str, str]] = []
    seq = 0
    for key, val in row.items():
        # 排除 metadata / 系統欄位
        if key in METADATA_FIELDS:
            continue
        if str(key).startswith("_"):
            continue
        if str(key).isdigit():
            continue

        reading_value = str(val).strip() if val is not None else ""
        results.append((seq, str(key), reading_value))
        seq += 1

    return results


# ── 主同步邏輯 ─────────────────────────────────────────────────────────────────

def sync_sheet(sheet_key: str) -> dict:
    """
    從 Ragic 同步指定 Sheet 的資料到本地 DB。

    返回：{"synced": N, "skipped": M, "sheet_key": sheet_key, "sheet_name": ...}
    """
    cfg = SHEET_CONFIGS.get(sheet_key)
    if not cfg:
        raise ValueError(f"Unknown sheet_key: {sheet_key}")

    sheet_name = cfg["name"]
    sheet_path = cfg["path"]

    adapter = RagicAdapter(
        server_url=HMR_SERVER_URL,
        account=HMR_ACCOUNT,
        api_key=settings.RAGIC_API_KEY,
    )

    logger.info("[HMR Sync] 開始同步 sheet=%s path=%s", sheet_key, sheet_path)

    try:
        rows: list[dict[str, Any]] = adapter.fetch_all(sheet_path)
    except Exception as exc:
        logger.error("[HMR Sync] Ragic 取資料失敗 sheet=%s: %s", sheet_key, exc)
        raise

    db = SessionLocal()
    synced = 0
    skipped = 0

    try:
        for row in rows:
            raw_id = row.get("_ragicId") or row.get("ragicId") or ""
            if not raw_id:
                skipped += 1
                continue

            batch_ragic_id = f"{sheet_key}_{raw_id}"

            # ── 萃取場次欄位 ───────────────────────────────────────────────
            raw_date      = _pick_field(row, DATE_CANDIDATES)
            record_date   = _extract_date(raw_date) if raw_date else ""
            recorder_name = _pick_field(row, RECORDER_CANDIDATES)

            # ── Upsert Batch ───────────────────────────────────────────────
            batch = db.get(HotelMRBatch, batch_ragic_id)
            if batch is None:
                batch = HotelMRBatch(ragic_id=batch_ragic_id)
                db.add(batch)

            batch.sheet_key     = sheet_key
            batch.sheet_name    = sheet_name
            batch.record_date   = record_date
            batch.recorder_name = recorder_name
            batch.synced_at     = twnow()

            # ── 萃取儀表讀數欄位並 Upsert ──────────────────────────────────
            meter_fields = _extract_meter_fields(row)
            for seq_no, meter_name, reading_value in meter_fields:
                reading_ragic_id = f"{batch_ragic_id}_{seq_no:04d}"

                reading = db.get(HotelMRReading, reading_ragic_id)
                if reading is None:
                    reading = HotelMRReading(ragic_id=reading_ragic_id)
                    db.add(reading)

                reading.batch_ragic_id = batch_ragic_id
                reading.sheet_key      = sheet_key
                reading.seq_no         = seq_no
                reading.meter_name     = meter_name
                reading.reading_value  = reading_value
                reading.synced_at      = twnow()

            synced += 1

        db.commit()

    except Exception as exc:
        db.rollback()
        logger.error("[HMR Sync] DB 寫入失敗 sheet=%s: %s", sheet_key, exc)
        raise
    finally:
        db.close()

    logger.info("[HMR Sync] 完成 sheet=%s synced=%d skipped=%d", sheet_key, synced, skipped)
    return {
        "synced":     synced,
        "skipped":    skipped,
        "sheet_key":  sheet_key,
        "sheet_name": sheet_name,
    }


def sync_all() -> dict:
    """同步全部 4 張 Sheet"""
    results = {}
    for sheet_key in SHEET_CONFIGS:
        try:
            results[sheet_key] = sync_sheet(sheet_key)
        except Exception as exc:
            results[sheet_key] = {"error": str(exc), "sheet_key": sheet_key}
    return results
