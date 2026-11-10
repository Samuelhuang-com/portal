"""
飯店每日巡檢 同步服務【逐來源同步 + 寬表格 Pivot + 動態欄位偵測】

2026-11-10 改版（比照 mall_facility_inspection_sync.py 的 2026-10-30 架構）：
  - 來源登錄：app/services/hotel_daily_inspection_sources.py（7 頁籤 × 現行表＋封存表）
      現行：main-project-inspection/17、28～33
      封存：archive-old-data/31～40（舊 18～21 與 Portal 以前未同步的 35～40）
  - 場次 ID ＝ "{source_key}_{Ragic Row ID}"（例：rf_17_0、4f_a32_12）；sheet_key ＝ 頁籤。
    ⚠️ 新 RF 表沿用表號 17、Row ID 從 0 起算 —— 舊 RF 場次必須先由 migration hdi1 改成
       rf_legacy_{n}，否則會被新資料覆蓋（舊 RF 在 Ragic 已找不到，Portal 是唯一一份）。
  - 「預估時間」寫入 hotel_di_inspection_batch.estimated_minutes，不再當成巡檢點。
  - 異常判定改用 hotel_daily_inspection_sheet.item_status（與畫面、每日巡檢表一致）。

每一 Row = 一次完整巡檢場次（寬表格）；場次欄位：巡檢人員、開始/結束巡檢時間、工時計算、預估時間。
"""
import logging
import re
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import twnow
from app.models.hotel_daily_inspection import HotelDIBatch, HotelDIItem
from app.services.ragic_adapter import RagicAdapter
from app.services.sync_dispatcher import register
from app.services.sync_result import aggregate_sync_results
from app.services.hotel_daily_inspection_sources import (
    SOURCES, TAB_LABELS, TABS, syncable_sources, live_source,
)

logger = logging.getLogger(__name__)

# ── Ragic 連線設定 ─────────────────────────────────────────────────────────────
HDI_SERVER_URL = getattr(settings, "RAGIC_HDI_SERVER_URL", "ap12.ragic.com")
HDI_ACCOUNT    = getattr(settings, "RAGIC_HDI_ACCOUNT",    "soutlet001")

# ── 頁籤設定（相容舊引用：key → {path: 現行表路徑, name: 顯示名稱}）─────────────
SHEET_CONFIGS: dict[str, dict] = {
    tab: {
        "path": (live_source(tab).sheet_path if live_source(tab) else ""),
        "name": f"飯店每日巡檢 - {TAB_LABELS[tab]}",
    }
    for tab in TABS
}

# ── 場次 metadata 欄位（不視為巡檢點）────────────────────────────────────────
SESSION_FIELDS = {
    "巡檢人員", "保全人員", "工務人員",
    "預估時間",
    "開始巡檢時間", "開始時間", "巡檢開始時間",
    "巡檢結束時間", "結束時間", "結束巡檢時間",
    "工時計算",
    "巡檢日期", "日期",
    "_ragicId", "_owner", "_create", "_modify",
}

INSPECTOR_CANDIDATES  = ["巡檢人員", "工務人員", "保全人員"]
# ⚠️ "巡檢日期"/"日期" 只含日期，不能拿來當 start_time → 獨立的 DATE_CANDIDATES
START_TIME_CANDIDATES = ["開始巡檢時間", "開始時間", "巡檢開始時間"]
DATE_CANDIDATES       = ["巡檢日期", "日期"]
END_TIME_CANDIDATES   = ["巡檢結束時間", "結束時間", "結束巡檢時間"]
WORK_HOURS_CANDIDATES = ["工時計算"]


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


# 允許 2026/8/3、2026-08-03、2026/08/03；後面接不接時間都可以
_DATE_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})")


def _extract_date(raw_datetime: str) -> str:
    """'2026/8/3 09:26' → '2026/08/03'。⚠️ 不可改回 raw[:10]（2026-08-24 修正，見商場同名函式）。"""
    m = _DATE_RE.search(raw_datetime or "")
    if not m:
        return ""
    year, month, day = m.groups()
    return f"{year}/{int(month):02d}/{int(day):02d}"


def _pick_field(raw: dict, candidates: list[str]) -> str:
    for key in candidates:
        val = _stringify(raw.get(key, ""))
        if val:
            return val
    return ""


def _best_date(raw: dict, start_raw: str) -> str:
    """優先取專用日期欄（巡檢日期／日期），否則從開始時間萃取；都失敗回空字串。"""
    date_raw = _pick_field(raw, DATE_CANDIDATES)
    if date_raw:
        d = _extract_date(date_raw)
        if d:
            return d
    return _extract_date(start_raw)


def _extract_check_items(row: dict) -> list[str]:
    """
    動態取巡檢點欄位：排除場次欄位、系統欄位（底線開頭）、純數字 key。
    2026-11-10：「拍照」等附件欄位改為收進 item（result_raw＝檔名），供 /db-images 組出附圖連結
    （比照整棟巡檢）；判定上一律為 note，不計入巡檢項目與異常。
    """
    items = []
    for key in row.keys():
        if key in SESSION_FIELDS or str(key).startswith("_"):
            continue
        try:
            int(key)
            continue
        except (ValueError, TypeError):
            pass
        items.append(key)
    return items


def _parse_minutes(raw: str) -> int | None:
    m = re.search(r"\d+(?:\.\d+)?", raw or "")
    return int(round(float(m.group()))) if m else None


# ── 單一來源同步 ──────────────────────────────────────────────────────────────

async def _sync_one_source(src, tab: str, log_tag: str) -> dict:
    """同步單一 Ragic Sheet（來源）。場次 ID = {source_key}_{Row ID}，sheet_key = 頁籤。"""
    from app.services.hotel_daily_inspection_sheet import item_status

    adapter = RagicAdapter(sheet_path=src.sheet_path, server_url=HDI_SERVER_URL, account=HDI_ACCOUNT)
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
                    sheet_name        = SHEET_CONFIGS[tab]["name"],
                    inspection_date   = _best_date(raw, start_raw),
                    inspector_name    = _pick_field(raw, INSPECTOR_CANDIDATES),
                    start_time        = start_raw,
                    end_time          = _pick_field(raw, END_TIME_CANDIDATES),
                    work_hours        = _pick_field(raw, WORK_HOURS_CANDIDATES),
                    estimated_minutes = _parse_minutes(_pick_field(raw, ["預估時間"])),
                    synced_at         = now,
                )
                existing = db.get(HotelDIBatch, batch_id)
                if existing:
                    for k, v in fields.items():
                        setattr(existing, k, v)
                else:
                    db.add(HotelDIBatch(ragic_id=batch_id, **fields))

                db.query(HotelDIItem).filter(HotelDIItem.batch_ragic_id == batch_id).delete(synchronize_session=False)

                row_check_items = check_items or _extract_check_items(raw)
                for seq, col_name in enumerate(row_check_items, start=1):
                    result_raw = _stringify(raw.get(col_name, ""))
                    is_note = "異常說明" in str(col_name)
                    result_status = item_status(tab, col_name, result_raw, is_note)
                    db.add(HotelDIItem(
                        ragic_id       = f"{batch_id}_{seq}",
                        batch_ragic_id = batch_id,
                        sheet_key      = tab,
                        seq_no         = seq,
                        item_name      = col_name,
                        result_raw     = result_raw,
                        result_status  = result_status,
                        abnormal_flag  = result_status in ("abnormal", "pending"),
                        is_note        = is_note,
                        synced_at      = now,
                    ))
                    item_rows += 1
                upserted += 1
            except Exception as exc:
                errors.append(f"{src.source_key} row={ragic_row_id}: {exc}")
                logger.warning(f"[{log_tag}] {src.source_key} 記錄 {ragic_row_id} 失敗：{exc}")

        db.commit()
        logger.info(f"[{log_tag}] {src.source_key} 完成：fetched={fetched}, batches={upserted}, "
                    f"items={item_rows}, errors={len(errors)}")
    except Exception as exc:
        db.rollback()
        errors.append(f"{src.source_key} DB commit error: {exc}")
        logger.error(f"[{log_tag}] {src.source_key} DB 寫入失敗：{exc}")
    finally:
        db.close()

    return {"source_key": src.source_key, "fetched": fetched, "upserted": upserted,
            "item_rows": item_rows, "check_item_count": len(check_items), "errors": errors}


def _legacy_ids_migrated() -> bool:
    """
    保護：舊 RF 場次還是 'rf_{數字}' 格式（migration hdi1 沒跑）時不同步，
    否則新 RF 表（同為表號 17、Row ID 從 0 起算）不會覆蓋，但舊場次會留在錯的 ID 格式、
    且畫面判斷不出它屬於哪個來源。PostgreSQL 正規式。
    """
    from sqlalchemy import text
    db = SessionLocal()
    try:
        n = db.execute(text(
            "SELECT COUNT(*) FROM hotel_di_inspection_batch "
            "WHERE ragic_id ~ '^(rf|4f-10f|4f|2f|1f)_[0-9]+$'"
        )).scalar()
        return not n
    except Exception as exc:
        logger.error(f"[HDISync] 檢查舊場次 ID 失敗：{exc}")
        return False
    finally:
        db.close()


async def sync_sheet(sheet_key: str) -> dict:
    """同步指定頁籤下所有有 Ragic 表的來源（現行＋封存）。"""
    if sheet_key not in SHEET_CONFIGS:
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [f"未知的 sheet_key: {sheet_key}"]}
    if not _legacy_ids_migrated():
        msg = "舊場次 ID 尚未改寫（請先執行 alembic upgrade head，revision hdi1），本次不同步"
        logger.error(f"[HDISync] {msg}")
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [msg]}
    summary = {"fetched": 0, "upserted": 0, "item_rows": 0, "check_item_count": 0, "errors": [], "sources": {}}
    for src in syncable_sources(sheet_key):
        res = await _sync_one_source(src, sheet_key, "HDISync")
        summary["sources"][src.source_key] = res
        for k in ("fetched", "upserted", "item_rows", "check_item_count"):
            summary[k] += res.get(k, 0)
        summary["errors"].extend(res.get("errors", []))
    return summary


# ── 全部頁籤同步 ──────────────────────────────────────────────────────────────

# 2026-11-05 暫停（舊表 17～21 已封存）；2026-11-10 新表接上後恢復。
HDI_SYNC_PAUSED = False


@register("hotel_daily_inspection")
async def sync_all() -> dict:
    """同步所有頁籤（每個頁籤包含其現行與封存來源）。"""
    if HDI_SYNC_PAUSED:
        logger.info("[HDISync] 飯店每日巡檢同步已暫停（HDI_SYNC_PAUSED=True），略過")
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [], "paused": True}
    # 舊場次 ID 未改寫時整個模組只回一筆錯誤（不要每個頁籤各報一次，sync_tool log 才看得清楚）
    if not _legacy_ids_migrated():
        msg = "舊場次 ID 尚未改寫（請先執行 alembic upgrade head，revision hdi1），本次不同步"
        logger.error(f"[HDISync] {msg}")
        return {"fetched": 0, "upserted": 0, "item_rows": 0, "errors": [msg]}
    results = {}
    for sheet_key in SHEET_CONFIGS:
        results[sheet_key] = await sync_sheet(sheet_key)
    return aggregate_sync_results(results)
