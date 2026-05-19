"""
每日數值登錄表 同步服務【統一 Sync + 場次登錄（不讀子表單）】

支援 4 張 Ragic Sheet（hotel-routine-inspection/11、12、14、15）。
  Sheet 11: 全棟水電錶
  Sheet 12: 商場空調箱電錶
  Sheet 14: 專櫃電錶
  Sheet 15: 專櫃水錶

【設計說明】
  每筆 Ragic 主表記錄 = 一次抄表登錄場次（hotel_mr_batch）。
  同步只讀主表欄位，不讀子表單（無 HotelMRReading 寫入）。
  抄表人員、抄表日期、抄表時間起/迄、工時計算均從主表欄位自動偵測。

【欄位名稱候選清單】
  若 Ragic 表單欄位名稱與下列不符，請修改各 *_CANDIDATES 常數。
"""
import logging
import re
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.hotel_meter_readings import HotelMRBatch, HotelMRReading
from app.services.ragic_adapter import RagicAdapter
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ─────────────────────────────────────────────────────────────
HMR_SERVER_URL = getattr(settings, "RAGIC_HDI_SERVER_URL", "ap12.ragic.com")
HMR_ACCOUNT    = getattr(settings, "RAGIC_HDI_ACCOUNT",    "soutlet001")

# ── Sheet 設定表 ──────────────────────────────────────────────────────────────
SHEET_CONFIGS: dict[str, dict] = {
    "building-electric": {
        "path": "hotel-routine-inspection/11",
        "name": "全棟水電錶",
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

# ── 欄位候選清單（依優先順序，取第一個有值的欄位）────────────────────────────
#
# 注意：「錶」（金字旁，電錶/水錶的錶）與「表」（一般的表）是不同字！
# Ragic 表單可能使用「抄錶日期」（錶）或「抄表日期」（表），兩者都納入候選。
#
DATE_CANDIDATES = [
    "抄錶日期",   # ★ Ragic 實際欄位名（錶 = 金字旁，確認於 2026-05-19）
    "抄表日期",   # 備援（表 = 一般的表）
    "登錄日期",
    "記錄日期",
    "日期",
    "填寫日期",
]
RECORDER_CANDIDATES = [
    "抄表人員",   # ★ Ragic 實際欄位名（確認於 2026-05-19）
    "抄錶人員",   # 備援（錶 字旁）
    "登錄人員",
    "記錄人員",
    "人員",
    "填寫人員",
]
TIME_START_CANDIDATES = [
    "抄表時間起",   # ★ Ragic 實際欄位名（確認於 2026-05-19）
    "抄錶時間起",   # 備援
    "開始時間",
    "起始時間",
    "時間起",
]
TIME_END_CANDIDATES = [
    "抄表時間迄",   # ★ Ragic 實際欄位名（確認於 2026-05-19）
    "抄錶時間迄",   # 備援
    "結束時間",
    "截止時間",
    "時間迄",
]
WORK_HOURS_CANDIDATES = [
    "工時計算",   # ★ Ragic 實際欄位名（確認於 2026-05-19）
    "工時",
    "工作時數",
    "作業時間",
]


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
    date_part = raw.split(" ")[0]
    return date_part.replace("-", "/")


def _extract_time(raw: str) -> str:
    """
    從各種時間格式萃取 HH:MM（或保留原始字串）。
    Ragic 常見格式：
      2026/04/30 08:30       → 08:30
      08:30                  → 08:30
      08:30:00               → 08:30
    """
    if not raw:
        return ""
    raw = raw.strip()
    # 若含空格（日期+時間），取空格後半
    if " " in raw:
        raw = raw.split(" ", 1)[1]
    # 截取 HH:MM（前 5 字元）
    if len(raw) >= 5 and ":" in raw:
        return raw[:5]
    return raw


# 日期值正規表達式（用於自動偵測）：YYYY/MM/DD 或 YYYY-MM-DD
_DATE_VALUE_PATTERN = re.compile(r"^\d{4}[/\-]\d{1,2}[/\-]\d{1,2}")

# 不應被誤判為日期欄位的欄位（數值型或時間型）
_NON_DATE_CANDIDATES = set(
    TIME_START_CANDIDATES + TIME_END_CANDIDATES + WORK_HOURS_CANDIDATES
)


def _auto_detect_date_field(row: dict) -> tuple[str, str]:
    """
    若候選清單（DATE_CANDIDATES）找不到日期，自動掃描所有欄位：
    取第一個「值符合 YYYY/MM/DD 或 YYYY-MM-DD 開頭」的文字欄位。

    返回 (field_name, raw_value)。找不到時返回 ("", "")。
    排除：以 "_" 開頭的系統欄位、純數字 key、已知時間/工時欄位。
    """
    for key, val in row.items():
        key_str = str(key)
        # 跳過系統欄位（"_ragicId", "_create" 等）
        if key_str.startswith("_"):
            continue
        # 跳過數字 key（Ragic 欄位 ID）
        if key_str.lstrip("-").isdigit():
            continue
        # 跳過已知非日期欄位（時間起/迄、工時）
        if key_str in _NON_DATE_CANDIDATES:
            continue
        val_str = str(val or "").strip()
        if _DATE_VALUE_PATTERN.match(val_str):
            return key_str, val_str
    return "", ""


# ── 主同步邏輯 ─────────────────────────────────────────────────────────────────

async def sync_sheet(sheet_key: str) -> dict:
    """
    從 Ragic 同步指定 Sheet 的主表資料到本地 DB（不讀子表單）。

    每筆記錄 = 一次抄表場次（HotelMRBatch），包含：
      抄表人員、抄表日期、抄表時間起/迄、工時計算。

    返回：{"fetched": N, "upserted": N, "errors": [], "sheet_key": ..., "sheet_name": ...}
    """
    cfg = SHEET_CONFIGS.get(sheet_key)
    if not cfg:
        raise ValueError(f"Unknown sheet_key: {sheet_key}")

    sheet_name = cfg["name"]
    sheet_path = cfg["path"]

    adapter = RagicAdapter(
        sheet_path=sheet_path,
        server_url=HMR_SERVER_URL,
        account=HMR_ACCOUNT,
        api_key=settings.RAGIC_API_KEY,
    )

    logger.info("[HMR Sync] 開始同步 sheet=%s path=%s", sheet_key, sheet_path)

    try:
        raw_data: dict[str, Any] = await adapter.fetch_all()
    except Exception as exc:
        logger.error("[HMR Sync] Ragic 取資料失敗 sheet=%s: %s", sheet_key, exc)
        raise

    db = SessionLocal()
    upserted = 0
    skipped  = 0
    errors: list[str] = []

    # ── 首筆資料：印出所有 Ragic 欄位名稱供診斷（INFO 等級，方便在 sync_tool 確認）──
    _first_row_logged = False

    try:
        for raw_id_str, row in raw_data.items():
            if not raw_id_str:
                skipped += 1
                continue

            # 印出第一筆的所有欄位名稱，方便確認 Ragic 實際回傳欄位
            if not _first_row_logged:
                _first_row_logged = True
                all_keys     = list(row.keys())
                visible_keys = [k for k in all_keys
                                if not str(k).startswith("_") and not str(k).isdigit()]
                numeric_keys = [k for k in all_keys if str(k).lstrip("-").isdigit()]
                logger.info(
                    "[HMR Sync] sheet=%s 第一筆欄位（共%d個）文字key=%s 數字key個數=%d",
                    sheet_key, len(all_keys), visible_keys, len(numeric_keys),
                )

            batch_ragic_id = f"{sheet_key}_{raw_id_str}"

            # ── 萃取主表欄位 ───────────────────────────────────────────────
            raw_date = _pick_field(row, DATE_CANDIDATES)

            # ── 日期自動偵測 Fallback（候選清單未命中時掃描所有欄位的值）──
            auto_date_field = ""
            if not raw_date:
                auto_date_field, raw_date = _auto_detect_date_field(row)
                if auto_date_field:
                    logger.info(
                        "[HMR Sync] sheet=%s id=%s 日期自動偵測成功：field='%s' value='%s'（請將此欄位名加入 DATE_CANDIDATES）",
                        sheet_key, raw_id_str, auto_date_field, raw_date,
                    )

            record_date   = _extract_date(raw_date) if raw_date else ""
            recorder_name = _pick_field(row, RECORDER_CANDIDATES)
            raw_start     = _pick_field(row, TIME_START_CANDIDATES)
            raw_end       = _pick_field(row, TIME_END_CANDIDATES)
            start_time    = _extract_time(raw_start)
            end_time      = _extract_time(raw_end)
            work_hours    = _pick_field(row, WORK_HOURS_CANDIDATES)

            # ── 欄位命中情況（INFO，每筆都記，方便核對）──────────────────
            logger.info(
                "[HMR Sync] sheet=%s id=%s → date='%s' recorder='%s' start='%s' end='%s' hours='%s'",
                sheet_key, raw_id_str, record_date, recorder_name, start_time, end_time, work_hours,
            )

            # ── 日期最終仍未命中：記警告並附出所有 key ─────────────────────
            if not record_date:
                logger.warning(
                    "[HMR Sync] ⚠ sheet=%s id=%s 日期欄位未命中！row所有key=%s",
                    sheet_key, raw_id_str,
                    [k for k in row.keys() if not str(k).startswith("_")],
                )

            # ── Upsert Batch ───────────────────────────────────────────────
            batch = db.get(HotelMRBatch, batch_ragic_id)
            if batch is None:
                batch = HotelMRBatch(ragic_id=batch_ragic_id)
                db.add(batch)

            batch.sheet_key     = sheet_key
            batch.sheet_name    = sheet_name
            batch.record_date   = record_date
            batch.recorder_name = recorder_name
            batch.start_time    = start_time
            batch.end_time      = end_time
            batch.work_hours    = work_hours
            batch.synced_at     = twnow()

            # ── Upsert HotelMRReading（扁平化摘要，與 Batch 一對一）──────────
            reading = db.get(HotelMRReading, batch_ragic_id)
            if reading is None:
                reading = HotelMRReading(ragic_id=batch_ragic_id)
                db.add(reading)

            reading.sheet_key     = sheet_key
            reading.sheet_name    = sheet_name
            reading.record_date   = record_date
            reading.recorder_name = recorder_name
            reading.start_time    = start_time
            reading.end_time      = end_time
            reading.work_hours    = work_hours
            reading.synced_at     = twnow()

            upserted += 1

        db.commit()

    except Exception as exc:
        db.rollback()
        logger.error("[HMR Sync] DB 寫入失敗 sheet=%s: %s", sheet_key, exc)
        errors.append(str(exc))
    finally:
        db.close()

    logger.info("[HMR Sync] 完成 sheet=%s fetched=%d upserted=%d skipped=%d errors=%d",
                sheet_key, len(raw_data), upserted, skipped, len(errors))
    return {
        "fetched":    len(raw_data),
        "upserted":   upserted,
        "errors":     errors,
        "sheet_key":  sheet_key,
        "sheet_name": sheet_name,
    }


@register("hotel_meter_readings")
async def sync_all() -> dict:
    """同步全部 4 張 Sheet，彙總 fetched / upserted / errors 供 sync_tool 顯示"""
    total_fetched  = 0
    total_upserted = 0
    all_errors: list[str] = []

    for sheet_key in SHEET_CONFIGS:
        try:
            r = await sync_sheet(sheet_key)
            total_fetched  += r.get("fetched",  0)
            total_upserted += r.get("upserted", 0)
            all_errors.extend(r.get("errors", []))
        except Exception as exc:
            all_errors.append(f"{sheet_key}: {exc}")

    return {
        "fetched":  total_fetched,
        "upserted": total_upserted,
        "errors":   all_errors,
    }
