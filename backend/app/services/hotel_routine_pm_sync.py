"""
飯店例行維護同步服務：Ragic → SQLite

資料來源：
  Sheet 6：https://ap12.ragic.com/soutlet001/periodic-maintenance/6（批次主表）
  Sheet 11：https://ap12.ragic.com/soutlet001/periodic-maintenance/11（保養項目，平表）

【Sheet 11 結構說明】
  - 每筆記錄 = 一個保養項目（平表，非嵌入式）
  - 透過「編號」欄位（journal_no）關聯批次主表
  - item.ragic_id = Ragic _ragicId（直接使用，不拼接）
  - is_completed 判斷規則：ragic_work_minutes != 0（維修工時有值 → 已完成）
  - 無 location 欄位（Sheet 11 不提供，存空字串）

Ragic 欄位對應（Sheet 6 主表）：
  編號  → journal_no
  日期  → period_month（normalize 為 YYYY/MM）

Ragic 欄位對應（Sheet 11 子表）：
  項次      → seq_no
  類別      → category
  頻率      → frequency
  執行月份  → exec_months_raw / exec_months_json
  項目      → task_name
  預估耗時  → estimated_minutes
  排定日期  → scheduled_date（normalize 為 MM/DD）
  排定人員  → scheduler_name
  執行人員  → executor_name
  備註      → result_note
  保養時間啟 → start_time
  保養時間迄 → end_time
  維修工時  → ragic_work_minutes（有值 → is_completed=True）
"""
import json
import logging
import re
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.hotel_routine_pm import HotelRoutinePMBatch, HotelRoutinePMItem
from app.services.ragic_adapter import RagicAdapter
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

# ── Ragic 中文欄位 key（主表 Sheet 6）────────────────────────────────────────
CK_JOURNAL_NO   = "編號"
CK_PERIOD_MONTH = "日期"

# ── Ragic 中文欄位 key（子表 Sheet 11）──────────────────────────────────────
CK_SEQ_NO       = "項次"
CK_CATEGORY     = "類別"
CK_FREQUENCY    = "頻率"
CK_EXEC_MONTHS  = "執行月份"
CK_TASK_NAME    = "項目"
CK_EST_HOURS    = "預估耗時"
CK_SCHED_DATE   = "排定日期"
CK_SCHEDULER    = "排定人員"
CK_EXECUTOR     = "執行人員"
CK_NOTE         = "備註"
CK_START_TIME   = "保養時間啟"
CK_END_TIME     = "保養時間迄"
CK_WORK_HOURS   = "維修工時"   # 有值 → is_completed = True

# ── Ragic 連線設定 ────────────────────────────────────────────────────────────
HOTEL_ROUTINE_PM_SERVER_URL   = getattr(settings, "RAGIC_HOTEL_ROUTINE_PM_SERVER_URL",   "ap12.ragic.com")
HOTEL_ROUTINE_PM_ACCOUNT      = getattr(settings, "RAGIC_HOTEL_ROUTINE_PM_ACCOUNT",      "soutlet001")
HOTEL_ROUTINE_PM_JOURNAL_PATH = getattr(settings, "RAGIC_HOTEL_ROUTINE_PM_JOURNAL_PATH", "periodic-maintenance/6")
HOTEL_ROUTINE_PM_ITEMS_PATH   = getattr(settings, "RAGIC_HOTEL_ROUTINE_PM_ITEMS_PATH",   "periodic-maintenance/11")


# ══════════════════════════════════════════════════════════════════════════════
# 轉換輔助函式
# ══════════════════════════════════════════════════════════════════════════════

def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_stringify(x) for x in value)
    if isinstance(value, dict):
        return _stringify(value.get("value") or value.get("label") or "")
    return str(value).strip()


def _to_int(val: Any) -> int:
    try:
        return int(float(str(val))) if val not in (None, "", "None") else 0
    except (ValueError, TypeError):
        return 0


def _to_float(val: Any) -> float:
    try:
        return float(str(val)) if val not in (None, "", "None") else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_exec_months(raw: Any) -> list[int]:
    """
    執行月份解析：支援陣列格式或文字格式。
    ["2月","5月","8月","11月"] → [2,5,8,11]
    "2月 5月 8月 11月"        → [2,5,8,11]
    "每月"                    → [1..12]
    """
    if not raw:
        return []
    # Sheet 11 回傳 list（Ragic checkbox）
    if isinstance(raw, list):
        months = []
        for item in raw:
            m = re.search(r"(\d+)", str(item))
            if m:
                month = int(m.group(1))
                if 1 <= month <= 12:
                    months.append(month)
        return sorted(set(months))
    # 文字格式
    raw_str = str(raw).strip()
    if raw_str in ("每月", "每月份"):
        return list(range(1, 13))
    months = []
    for part in raw_str.split():
        m = re.search(r"(\d+)", part)
        if m:
            month = int(m.group(1))
            if 1 <= month <= 12:
                months.append(month)
    return sorted(set(months))


def _normalize_period_month(raw_date: str) -> str:
    """
    "2026/04/01" → "2026/04"
    "2026/04"    → "2026/04"
    """
    parts = raw_date.strip().split("/")
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return raw_date


def _normalize_sched_date(raw: str) -> str:
    """
    "2026/05/06" → "05/06"
    "05/06"      → "05/06"
    ""           → ""
    """
    if not raw:
        return ""
    parts = raw.strip().split("/")
    if len(parts) == 3:
        return f"{parts[1]}/{parts[2]}"
    if len(parts) == 2:
        return raw.strip()
    return raw.strip()


def _work_hours_to_minutes(raw: Any) -> int:
    """
    維修工時（小時或分鐘）→ 整數分鐘
    Ragic 欄位可能是小時（float）或分鐘（int），以 < 24 判斷為小時
    """
    v = _to_float(raw)
    if v <= 0:
        return 0
    if v < 24:
        return int(v * 60)
    return int(v)


def _ragic_url(path: str, ragic_id: str) -> str:
    return f"https://ap12.ragic.com/{HOTEL_ROUTINE_PM_ACCOUNT}/{path}/{ragic_id}"


# ══════════════════════════════════════════════════════════════════════════════
# 同步：主表批次（Sheet 6）
# ══════════════════════════════════════════════════════════════════════════════

def _sync_batches(db) -> dict:
    adapter = RagicAdapter(
        server_url=HOTEL_ROUTINE_PM_SERVER_URL,
        account=HOTEL_ROUTINE_PM_ACCOUNT,
        api_key=settings.RAGIC_API_KEY,
    )
    raw_data = adapter.fetch_all(HOTEL_ROUTINE_PM_JOURNAL_PATH)
    if not isinstance(raw_data, dict):
        return {"error": f"unexpected response type: {type(raw_data)}"}

    created = updated = 0
    for ragic_id_str, row in raw_data.items():
        if not isinstance(row, dict):
            continue
        ragic_id = str(ragic_id_str)
        journal_no   = _stringify(row.get(CK_JOURNAL_NO, ""))
        period_month = _normalize_period_month(_stringify(row.get(CK_PERIOD_MONTH, "")))
        if not journal_no or not period_month:
            continue

        existing = db.get(HotelRoutinePMBatch, ragic_id)
        if existing:
            existing.journal_no       = journal_no
            existing.period_month     = period_month
            existing.ragic_updated_at = str(row.get("_dataTimestamp", ""))
            updated += 1
        else:
            db.add(HotelRoutinePMBatch(
                ragic_id         = ragic_id,
                journal_no       = journal_no,
                period_month     = period_month,
                ragic_created_at = str(row.get("_dataTimestamp", "")),
                ragic_updated_at = str(row.get("_dataTimestamp", "")),
            ))
            created += 1

    db.commit()
    return {"created": created, "updated": updated}


# ══════════════════════════════════════════════════════════════════════════════
# 同步：保養項目（Sheet 11，平表）
# ══════════════════════════════════════════════════════════════════════════════

def _sync_items(db) -> dict:
    adapter = RagicAdapter(
        server_url=HOTEL_ROUTINE_PM_SERVER_URL,
        account=HOTEL_ROUTINE_PM_ACCOUNT,
        api_key=settings.RAGIC_API_KEY,
    )
    raw_data = adapter.fetch_all(HOTEL_ROUTINE_PM_ITEMS_PATH)
    if not isinstance(raw_data, dict):
        return {"error": f"unexpected response type: {type(raw_data)}"}

    # 建立 journal_no → batch.ragic_id 的 lookup（用於關聯主表）
    journal_lookup: dict[str, str] = {
        b.journal_no: b.ragic_id
        for b in db.query(HotelRoutinePMBatch).all()
    }

    created = updated = skipped = 0

    for ragic_id_str, row in raw_data.items():
        if not isinstance(row, dict):
            continue
        ragic_id = str(ragic_id_str)

        # 透過 journal_no 找到 batch_ragic_id
        journal_no = _stringify(row.get(CK_JOURNAL_NO, ""))
        batch_ragic_id = journal_lookup.get(journal_no, "")
        if not batch_ragic_id:
            logger.warning(f"[hotel_routine_pm_sync] 無法找到批次：journal_no={journal_no!r}")
            skipped += 1
            continue

        # 解析執行月份
        exec_months_raw_val = row.get(CK_EXEC_MONTHS, [])
        exec_months_list = _parse_exec_months(exec_months_raw_val)
        if isinstance(exec_months_raw_val, list):
            exec_months_raw_str = " ".join(exec_months_raw_val)
        else:
            exec_months_raw_str = _stringify(exec_months_raw_val)

        # 維修工時 → 完成判斷
        work_minutes  = _work_hours_to_minutes(row.get(CK_WORK_HOURS, ""))
        is_completed  = work_minutes > 0

        # 排定日期正規化
        sched_date = _normalize_sched_date(_stringify(row.get(CK_SCHED_DATE, "")))

        existing = db.get(HotelRoutinePMItem, ragic_id)
        if existing:
            # 若 Portal 已手動編輯，不覆寫執行欄位
            if not existing.portal_edited_at:
                existing.executor_name      = _stringify(row.get(CK_EXECUTOR, ""))
                existing.start_time         = _stringify(row.get(CK_START_TIME, ""))
                existing.end_time           = _stringify(row.get(CK_END_TIME, ""))
                existing.ragic_work_minutes = work_minutes if work_minutes else None
                existing.is_completed       = is_completed
                existing.result_note        = _stringify(row.get(CK_NOTE, ""))
            # 主檔欄位（不受保護）
            existing.batch_ragic_id    = batch_ragic_id
            existing.seq_no            = _to_int(row.get(CK_SEQ_NO, 0))
            existing.category          = _stringify(row.get(CK_CATEGORY, ""))
            existing.frequency         = _stringify(row.get(CK_FREQUENCY, ""))
            existing.exec_months_raw   = exec_months_raw_str
            existing.exec_months_json  = json.dumps(exec_months_list, ensure_ascii=False)
            existing.task_name         = _stringify(row.get(CK_TASK_NAME, ""))
            existing.estimated_minutes = _to_int(row.get(CK_EST_HOURS, 0))
            existing.scheduled_date    = sched_date
            existing.scheduler_name    = _stringify(row.get(CK_SCHEDULER, ""))
            updated += 1
        else:
            db.add(HotelRoutinePMItem(
                ragic_id            = ragic_id,
                batch_ragic_id      = batch_ragic_id,
                seq_no              = _to_int(row.get(CK_SEQ_NO, 0)),
                category            = _stringify(row.get(CK_CATEGORY, "")),
                frequency           = _stringify(row.get(CK_FREQUENCY, "")),
                exec_months_raw     = exec_months_raw_str,
                exec_months_json    = json.dumps(exec_months_list, ensure_ascii=False),
                task_name           = _stringify(row.get(CK_TASK_NAME, "")),
                location            = "",   # Sheet 11 無此欄
                estimated_minutes   = _to_int(row.get(CK_EST_HOURS, 0)),
                scheduled_date      = sched_date,
                scheduler_name      = _stringify(row.get(CK_SCHEDULER, "")),
                executor_name       = _stringify(row.get(CK_EXECUTOR, "")),
                start_time          = _stringify(row.get(CK_START_TIME, "")),
                end_time            = _stringify(row.get(CK_END_TIME, "")),
                ragic_work_minutes  = work_minutes if work_minutes else None,
                is_completed        = is_completed,
                result_note         = _stringify(row.get(CK_NOTE, "")),
            ))
            created += 1

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


# ══════════════════════════════════════════════════════════════════════════════
# 主同步進入點
# ══════════════════════════════════════════════════════════════════════════════

@register("hotel_routine_pm")
def sync_from_ragic() -> dict:
    """飯店例行維護：從 Ragic 同步批次主表 + 保養項目（Sheet 11 平表）"""
    db = SessionLocal()
    try:
        batch_result = _sync_batches(db)
        items_result = _sync_items(db)
    except Exception as exc:
        db.rollback()
        logger.error(f"[hotel_routine_pm_sync] 同步失敗：{exc}", exc_info=True)
        raise
    finally:
        db.close()

    return {
        "batches": batch_result,
        "items":   items_result,
    }
