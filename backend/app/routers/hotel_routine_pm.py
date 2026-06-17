"""
飯店例行維護 API Router
Prefix: /api/v1/hotel/routine-maintenance

端點：
  POST /sync                         — 手動從 Ragic 同步
  GET  /batches                      — 批次清單（年份篩選）
  GET  /batches/{batch_id}           — 單筆批次 + 所有項目 + KPI
  GET  /batches/{batch_id}/items     — 該批次項目（含狀態篩選）
  GET  /batches/{batch_id}/kpi       — 批次 KPI 統計
  GET  /items                        — 所有項目跨批次查詢
  GET  /stats                        — 全站統計（Dashboard 資料來源）
  GET  /items/task-history           — 依項目名稱查詢跨批次執行歷史
  GET  /period-stats/year-matrix     — 全年 12 個月矩陣統計（必須在 /period-stats 之前）
  GET  /period-stats                 — 週期統計（月/季/年）
  GET  /period-stats/year-matrix/items — 矩陣格明細
  GET  /items/catalog                — 保養項目目錄（依頻率分類）
  POST /schedule/generate            — 產生指定月份保養排程
  GET  /schedule                     — 查詢排程明細列表
  GET  /schedule/kpi                 — 排程 KPI 統計
  GET  /schedule/overdue             — 跨月逾期未執行清單
  PATCH /schedule/{schedule_id}      — 人工調整排程明細
  GET  /schedule/annual-matrix       — 年度計劃矩陣（12欄）
"""
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.hotel_routine_pm import HotelRoutinePMBatch, HotelRoutinePMItem
from app.models.hotel_routine_pm_schedule import HotelRoutinePMSchedule
from app.schemas.hotel_routine_pm import (
    HotelRoutinePMBatchOut, HotelRoutinePMItemOut, HotelRoutinePMBatchKPI,
    HotelRoutinePMBatchDetail, HotelRoutinePMCategoryStat,
    HotelRoutinePMStatusDistItem, HotelRoutinePMStats,
    HotelRoutinePMPeriodStats, HotelRoutinePMSubPeriodBreakdown,
    HotelRoutinePMIncompleteItem, HotelRoutinePMYearMatrix,
    HotelRoutinePMYearMatrixMonth, HotelRoutinePMScheduleOut,
    HotelRoutinePMScheduleKPI, HotelRoutinePMScheduleGenerateResult,
    HotelRoutinePMScheduleUpdate, HotelRoutinePMScheduleMatrixCell,
    HotelRoutinePMScheduleMatrixRow, HotelRoutinePMScheduleAnnualMatrix,
)
from app.services.hotel_routine_pm_sync import sync_from_ragic
from app.core.config import settings

router = APIRouter(dependencies=[Depends(get_current_user)])

# ── 狀態色彩對照 ──────────────────────────────────────────────────────────────
STATUS_COLORS = {
    "completed":         "#52C41A",
    "in_progress":       "#4BA8E8",
    "scheduled":         "#FAAD14",
    "unscheduled":       "#FF4D4F",
    "overdue":           "#C0392B",
    "non_current_month": "#999999",
}

STATUS_LABELS = {
    "completed":         "已完成",
    "in_progress":       "進行中",
    "scheduled":         "已排定",
    "unscheduled":       "未排定",
    "overdue":           "逾期",
    "non_current_month": "非本月",
}

RAGIC_PATH = "periodic-maintenance/6"


# ── 業務邏輯輔助函式 ──────────────────────────────────────────────────────────

_TIME_FMTS = ["%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]


def _ragic_url(path: str, ragic_id: str) -> str:
    ragic_server  = getattr(settings, "RAGIC_PM_SERVER_URL", "ap12.ragic.com")
    ragic_account = "soutlet001"
    return f"https://{ragic_server}/{ragic_account}/{path}/{ragic_id}"


def _time_diff_minutes(start: str, end: str) -> int:
    """計算 start_time ~ end_time 差值（分鐘），解析失敗回傳 0。"""
    if not start or not end:
        return 0
    for fmt in _TIME_FMTS:
        try:
            st = datetime.strptime(start.strip(), fmt)
            et = datetime.strptime(end.strip(), fmt)
            return max(0, int((et - st).total_seconds() / 60))
        except ValueError:
            continue
    return 0


def _calc_status(item: HotelRoutinePMItem, check_month: int) -> str:
    """
    依 Ragic 欄位值推導保養項目狀態。

    判斷順序：
    1. 非本月 — 依頻率與 exec_months 判斷本月不適用
    2. 已完成 — ragic_work_minutes 有值（> 0）
    3. 進行中 — start_time 有值，但 ragic_work_minutes 無值
    4. 逾期   — 排定日期有值，且該日期已過今天
    5. 已排定 — 排定日期有值，尚未到期
    6. 未排定 — 以上皆無
    """
    exec_months: list[int] = []
    try:
        exec_months = json.loads(item.exec_months_json or "[]")
    except Exception:
        pass

    # 1. 非本月判斷
    if exec_months:
        if check_month not in exec_months:
            return "non_current_month"
    elif item.frequency:
        if not _should_schedule_by_frequency(item.frequency, check_month):
            return "non_current_month"

    # 2. 已完成（ragic_work_minutes 有值）
    if bool(item.ragic_work_minutes):
        return "completed"

    # 3. 進行中
    if item.start_time:
        return "in_progress"

    # 4. 逾期 / 5. 已排定
    if item.scheduled_date:
        try:
            today = date.today()
            scheduled = datetime.strptime(
                f"{today.year}/{item.scheduled_date}", "%Y/%m/%d"
            ).date()
            if scheduled < today:
                return "overdue"
        except Exception:
            pass
        return "scheduled"

    # 6. 未排定
    return "unscheduled"


# ── 排程邏輯輔助函式 ──────────────────────────────────────────────────────────

# 頻率 → 週期間隔（月數）
_FREQ_INTERVAL: dict[str, int] = {
    "月":   1,
    "雙月": 2,
    "季":   3,
    "半年": 6,
    "年":   12,
}


def _should_schedule_by_frequency(frequency: str, month: int) -> bool:
    """
    純依頻率字串與月份判斷「本月是否應產生排程」。
    僅在 exec_months_json 為空時使用（有 exec_months 時以它為準）。

    規則（從 1 月起算）：
      月     → 永遠 True
      雙月   → (month - 1) % 2 == 0  → 1,3,5,7,9,11 月
      季     → (month - 1) % 3 == 0  → 1,4,7,10 月
      半年   → (month - 1) % 6 == 0  → 1,7 月
      年     → (month - 1) % 12 == 0 → 1 月
      其他   → False
    """
    interval = _FREQ_INTERVAL.get(frequency.strip())
    if interval is None:
        return False
    if interval == 1:
        return True
    return (month - 1) % interval == 0


def _should_schedule(item: HotelRoutinePMItem, year: int, month: int) -> bool:
    """
    判斷指定 year/month 是否應為此項目產生排程。

    優先順序：
    1. 頻率為空 → False（無法判斷，跳過）
    2. exec_months_json 有值 → month in exec_months
    3. exec_months_json 為空 → 依頻率公式推算
    """
    freq = (item.frequency or "").strip()
    if not freq:
        return False

    exec_months: list[int] = []
    try:
        exec_months = json.loads(item.exec_months_json or "[]")
    except Exception:
        pass

    if exec_months:
        return month in exec_months

    return _should_schedule_by_frequency(freq, month)


def _item_to_out(item: HotelRoutinePMItem, check_month: int) -> HotelRoutinePMItemOut:
    """ORM → Pydantic，注入 status 計算值。"""
    return HotelRoutinePMItemOut(
        ragic_id          = item.ragic_id,
        batch_ragic_id    = item.batch_ragic_id,
        seq_no            = item.seq_no,
        category          = item.category,
        frequency         = item.frequency,
        exec_months_raw   = item.exec_months_raw,
        exec_months_json  = item.exec_months_json,
        task_name         = item.task_name,
        location          = item.location,
        estimated_minutes = item.estimated_minutes,
        scheduled_date    = item.scheduled_date,
        scheduler_name    = item.scheduler_name,
        executor_name     = item.executor_name,
        start_time        = item.start_time,
        end_time          = item.end_time,
        ragic_work_minutes= item.ragic_work_minutes,
        is_completed      = bool(item.ragic_work_minutes),
        result_note       = item.result_note,
        abnormal_flag     = item.abnormal_flag,
        abnormal_note     = item.abnormal_note,
        portal_edited_at  = item.portal_edited_at,
        synced_at         = item.synced_at,
        status            = _calc_status(item, check_month),
    )


def _calc_kpi(items: list[HotelRoutinePMItem], check_month: int) -> HotelRoutinePMBatchKPI:
    statuses = [_calc_status(it, check_month) for it in items]
    current_items = [(it, s) for it, s in zip(items, statuses) if s != "non_current_month"]
    total_current = len(current_items)

    total_all   = len(items)
    completed   = sum(1 for it in items if bool(it.ragic_work_minutes))
    in_progress = sum(1 for _, s in current_items if s == "in_progress")
    scheduled   = sum(1 for _, s in current_items if s == "scheduled")
    unscheduled = sum(1 for _, s in current_items if s == "unscheduled")
    overdue     = sum(1 for _, s in current_items if s == "overdue")
    abnormal    = sum(1 for it in items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)
    actual      = sum(
        it.ragic_work_minutes if it.ragic_work_minutes is not None
        else _time_diff_minutes(it.start_time, it.end_time)
        for it in items if bool(it.ragic_work_minutes)
    )
    rate = round(completed / total_all * 100, 1) if total_all > 0 else 0.0

    return HotelRoutinePMBatchKPI(
        total               = len(items),
        current_month_total = total_current,
        completed           = completed,
        in_progress         = in_progress,
        scheduled           = scheduled,
        unscheduled         = unscheduled,
        overdue             = overdue,
        abnormal            = abnormal,
        completion_rate     = rate,
        planned_minutes     = planned,
        actual_minutes      = actual,
    )


def _calc_category_stats(
    items: list[HotelRoutinePMItem], check_month: int
) -> list[HotelRoutinePMCategoryStat]:
    from collections import defaultdict
    cats: dict[str, dict] = defaultdict(lambda: {"total": 0, "completed": 0})
    for it in items:
        s = _calc_status(it, check_month)
        if s == "non_current_month":
            continue
        cat = it.category or "其他"
        cats[cat]["total"] += 1
        if s == "completed":
            cats[cat]["completed"] += 1
    result = []
    for cat, counts in sorted(cats.items()):
        t = counts["total"]
        c = counts["completed"]
        result.append(HotelRoutinePMCategoryStat(
            category  = cat,
            total     = t,
            completed = c,
            rate      = round(c / t * 100, 1) if t > 0 else 0.0,
        ))
    return result


def _get_check_month(period_month: str) -> int:
    """從 'YYYY/MM' 取得月份整數；若解析失敗則用今天的月份。"""
    try:
        return int(period_month.split("/")[1])
    except Exception:
        return date.today().month


# ── 週期統計輔助函式 ──────────────────────────────────────────────────────────

def _reconstruct_full_date(scheduled_date: str, period_month: str) -> "date | None":
    """
    'MM/DD' + 'YYYY/MM' → date(YYYY, MM, DD)
    月份以 scheduled_date 為準，年份從 period_month 取。
    """
    if not scheduled_date:
        return None
    try:
        parts = scheduled_date.strip().split("/")
        if len(parts) != 2:
            return None
        month = int(parts[0])
        day   = int(parts[1])
        year  = int(period_month.strip().split("/")[0])
        return date(year, month, day)
    except Exception:
        return None


def _parse_end_date(end_time: str) -> "date | None":
    """'YYYY/MM/DD HH:MM:SS' → date(YYYY, MM, DD)"""
    if not end_time:
        return None
    for fmt in _TIME_FMTS:
        try:
            return datetime.strptime(end_time.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _get_period_bounds(
    period_type: str,
    year: int,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
) -> "tuple[date, date, date]":
    """回傳 (period_start, period_end, prev_period_end)"""
    today = date.today()

    if period_type == "month":
        m = month or today.month
        _, last_day = monthrange(year, m)
        p_start = date(year, m, 1)
        p_end   = date(year, m, last_day)
        if m == 1:
            _, prev_last = monthrange(year - 1, 12)
            prev_end = date(year - 1, 12, prev_last)
        else:
            _, prev_last = monthrange(year, m - 1)
            prev_end = date(year, m - 1, prev_last)

    elif period_type == "quarter":
        q = quarter or ((today.month - 1) // 3 + 1)
        q_start_m = (q - 1) * 3 + 1
        q_end_m   = q * 3
        _, last_day = monthrange(year, q_end_m)
        p_start = date(year, q_start_m, 1)
        p_end   = date(year, q_end_m, last_day)
        if q == 1:
            _, prev_last = monthrange(year - 1, 12)
            prev_end = date(year - 1, 12, prev_last)
        else:
            prev_q_end_m = (q - 1) * 3
            _, prev_last = monthrange(year, prev_q_end_m)
            prev_end = date(year, prev_q_end_m, prev_last)

    else:  # year
        p_start  = date(year, 1, 1)
        p_end    = date(year, 12, 31)
        prev_end = date(year - 1, 12, 31)

    return p_start, p_end, prev_end


def _calc_period_stats_core(
    db: Session,
    period_start: date,
    period_end: date,
    prev_period_end: date,
    frequency_type: Optional[str] = None,
) -> dict:
    """共用統計核心。"""
    rows = (
        db.query(HotelRoutinePMItem, HotelRoutinePMBatch)
        .join(
            HotelRoutinePMBatch,
            HotelRoutinePMItem.batch_ragic_id == HotelRoutinePMBatch.ragic_id,
        )
        .all()
    )

    prev_carry_over_list: list[dict] = []
    period_items_list:    list[dict] = []

    for item, batch in rows:
        if not item.scheduled_date:
            continue
        if not _freq_match(item.frequency, frequency_type):
            continue
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []
        batch_month = int(batch.period_month.split("/")[1])
        if exec_months and batch_month not in exec_months:
            continue

        full_date = _reconstruct_full_date(item.scheduled_date, batch.period_month)
        if full_date is None:
            continue

        is_done  = bool(item.ragic_work_minutes)
        end_date = _parse_end_date(item.end_time)

        entry = {
            "item":      item,
            "batch":     batch,
            "full_date": full_date,
            "end_date":  end_date,
            "is_done":   is_done,
        }

        if full_date <= prev_period_end:
            done_before = (
                is_done
                and end_date is not None
                and end_date <= prev_period_end
            )
            if not done_before:
                prev_carry_over_list.append(entry)

        if period_start <= full_date <= period_end:
            period_items_list.append(entry)

    prev_resolved_list = [
        x for x in prev_carry_over_list
        if x["end_date"] is not None
        and period_start <= x["end_date"] <= period_end
    ]

    period_completed_list = [x for x in period_items_list if x["is_done"]]

    incomplete_items = [
        HotelRoutinePMIncompleteItem(
            task_name           = x["item"].task_name,
            category            = x["item"].category or "未歸類位置",
            scheduled_date_full = x["full_date"].strftime("%Y/%m/%d"),
            result_note         = x["item"].result_note,
            frequency           = x["item"].frequency,
        )
        for x in period_items_list
        if not x["is_done"] and x["item"].result_note
    ]

    n_carry    = len(prev_carry_over_list)
    n_resolved = len(prev_resolved_list)
    n_total    = len(period_items_list)
    n_done     = len(period_completed_list)

    return {
        "prev_carry_over":         n_carry,
        "prev_resolved_in_period": n_resolved,
        "carry_over_rate":         round(n_resolved / n_carry * 100, 1) if n_carry > 0 else None,
        "period_total":            n_total,
        "period_completed":        n_done,
        "period_rate":             round(n_done / n_total * 100, 1) if n_total > 0 else None,
        "incomplete_items":        incomplete_items,
        "period_items_list":       period_items_list,
    }


def _calc_sub_breakdown(
    period_type: str,
    period_start: date,
    period_items_list: list[dict],
) -> list[HotelRoutinePMSubPeriodBreakdown]:
    if period_type == "month":
        return []

    breakdown: list[HotelRoutinePMSubPeriodBreakdown] = []
    year = period_start.year

    if period_type == "quarter":
        start_m = period_start.month
        for i in range(3):
            m = start_m + i
            _, last_day = monthrange(year, m)
            m_start = date(year, m, 1)
            m_end   = date(year, m, last_day)
            items_m = [x for x in period_items_list if m_start <= x["full_date"] <= m_end]
            total     = len(items_m)
            completed = sum(1 for x in items_m if x["is_done"])
            breakdown.append(HotelRoutinePMSubPeriodBreakdown(
                label     = f"{m}月",
                total     = total,
                completed = completed,
                rate      = round(completed / total * 100, 1) if total > 0 else None,
            ))

    elif period_type == "year":
        for q in range(1, 5):
            q_start_m = (q - 1) * 3 + 1
            q_end_m   = q * 3
            _, last_day = monthrange(year, q_end_m)
            q_start = date(year, q_start_m, 1)
            q_end   = date(year, q_end_m, last_day)
            items_q = [x for x in period_items_list if q_start <= x["full_date"] <= q_end]
            total     = len(items_q)
            completed = sum(1 for x in items_q if x["is_done"])
            breakdown.append(HotelRoutinePMSubPeriodBreakdown(
                label     = f"Q{q}",
                total     = total,
                completed = completed,
                rate      = round(completed / total * 100, 1) if total > 0 else None,
            ))

    return breakdown


# ── 頻率分類 mapping ─────────────────────────────────────────────────────────
_FREQ_KEYWORDS: dict[str, set[str]] = {
    "monthly":   {"月", "每月", "月維護", "Monthly", "monthly"},
    "quarterly": {"季", "每季", "季維護", "Quarterly", "quarterly"},
    "yearly":    {"年", "每年", "年維護", "Annual", "annual", "Yearly", "yearly"},
}


def _freq_match(frequency: str, frequency_type: Optional[str]) -> bool:
    """回傳 True 表示該 item 的頻率符合篩選條件（None = 不篩選）"""
    if not frequency_type:
        return True
    keywords = _FREQ_KEYWORDS.get(frequency_type, set())
    return frequency.strip() in keywords


_MONTH_LABELS_ZH = ["1月","2月","3月","4月","5月","6月",
                    "7月","8月","9月","10月","11月","12月"]


def _calc_year_matrix(
    db: Session, year: int, frequency_type: Optional[str] = None
) -> HotelRoutinePMYearMatrix:
    """全年 12 個月矩陣統計。"""
    rows = (
        db.query(HotelRoutinePMItem, HotelRoutinePMBatch)
        .join(
            HotelRoutinePMBatch,
            HotelRoutinePMItem.batch_ragic_id == HotelRoutinePMBatch.ragic_id,
        )
        .all()
    )

    processed: list[dict] = []
    for item, batch in rows:
        if not item.scheduled_date:
            continue
        if not _freq_match(item.frequency, frequency_type):
            continue
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []
        batch_month = int(batch.period_month.split("/")[1])
        if exec_months and batch_month not in exec_months:
            continue
        full_date = _reconstruct_full_date(item.scheduled_date, batch.period_month)
        if full_date is None:
            continue
        is_done  = bool(item.ragic_work_minutes)
        end_date = _parse_end_date(item.end_time)
        processed.append({
            "item":      item,
            "full_date": full_date,
            "end_date":  end_date,
            "is_done":   is_done,
        })

    freq_kws: Optional[set] = _FREQ_KEYWORDS.get(frequency_type) if frequency_type else None

    latest_items_all = _get_latest_batch_items(db)
    if frequency_type:
        latest_items_all = [it for it in latest_items_all if _freq_match(it.frequency, frequency_type)]

    month_results: list[HotelRoutinePMYearMatrixMonth] = []
    for m in range(1, 13):
        p_start, p_end, prev_end = _get_period_bounds("month", year, month=m)

        prev_carry_over_list: list[dict] = []
        period_items_list:    list[dict] = []

        for e in processed:
            fd       = e["full_date"]
            is_done  = e["is_done"]
            end_date = e["end_date"]

            if fd <= prev_end:
                done_before = is_done and end_date is not None and end_date <= prev_end
                if not done_before:
                    prev_carry_over_list.append(e)

            if p_start <= fd <= p_end:
                period_items_list.append(e)

        prev_resolved_list = [
            x for x in prev_carry_over_list
            if x["end_date"] is not None
            and p_start <= x["end_date"] <= p_end
        ]
        period_completed_list = [x for x in period_items_list if x["is_done"]]

        year_month_str = f"{year}/{m:02d}"
        sched_q = db.query(HotelRoutinePMSchedule).filter(
            HotelRoutinePMSchedule.year_month == year_month_str
        )
        if freq_kws:
            sched_q = sched_q.filter(HotelRoutinePMSchedule.frequency.in_(freq_kws))
        sched_recs = sched_q.all()

        if sched_recs:
            n_total = len(sched_recs)
            n_done  = sum(1 for r in sched_recs if r.is_completed)
            notes_parts = [
                f"{r.task_name}：{r.result_note}"
                for r in sched_recs
                if not r.is_completed and r.result_note
            ]
        else:
            n_total = sum(1 for it in latest_items_all if _should_schedule(it, year, m))
            n_done  = len(period_completed_list)
            notes_parts = [
                f"{x['item'].task_name}：{x['item'].result_note}"
                for x in period_items_list
                if not x["is_done"] and x["item"].result_note
            ]

        n_carry    = len(prev_carry_over_list)
        n_resolved = len(prev_resolved_list)

        month_results.append(HotelRoutinePMYearMatrixMonth(
            month                   = m,
            label                   = _MONTH_LABELS_ZH[m - 1],
            prev_carry_over         = n_carry,
            prev_resolved_in_period = n_resolved,
            carry_over_rate         = round(n_resolved / n_carry * 100, 1) if n_carry > 0 else None,
            period_total            = n_total,
            period_completed        = n_done,
            period_rate             = round(n_done / n_total * 100, 1) if n_total > 0 else None,
            incomplete_notes        = "\n".join(notes_parts),
        ))

    return HotelRoutinePMYearMatrix(year=year, months=month_results)


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync
# ══════════════════════════════════════════════════════════════════════════════
@router.post(
    "/sync",
    summary="從 Ragic 同步飯店例行維護資料（背景執行）",
    dependencies=[Depends(require_roles("system_admin", "module_manager"))],
)
async def sync_hotel_routine_pm(background_tasks: BackgroundTasks):
    """手動觸發：Ragic Sheet 6 + Sheet 11 → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"status": "ok", "message": "同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches", summary="取得例行維護批次清單")
def list_batches(
    year: Optional[str] = Query(None, description="篩選年份，如 2026"),
    db:   Session = Depends(get_db),
):
    q = db.query(HotelRoutinePMBatch)
    if year:
        q = q.filter(HotelRoutinePMBatch.period_month.like(f"{year}%"))
    batches = q.order_by(HotelRoutinePMBatch.period_month.desc()).all()

    result = []
    for b in batches:
        items = db.query(HotelRoutinePMItem).filter(
            HotelRoutinePMItem.batch_ragic_id == b.ragic_id
        ).all()
        check_month = _get_check_month(b.period_month)
        kpi = _calc_kpi(items, check_month)
        batch_dict = HotelRoutinePMBatchOut.model_validate(b).model_dump()
        batch_dict["ragic_url"] = _ragic_url(RAGIC_PATH, b.ragic_id)
        result.append({
            "batch": batch_dict,
            "kpi":   kpi.model_dump(),
        })
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches/{batch_id}
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches/{batch_id}", summary="取得單筆批次完整資料（含所有項目 + KPI）")
def get_batch_detail(
    batch_id:           str,
    current_month_only: bool = Query(False, description="只回傳本月有效項目"),
    category:           Optional[str] = Query(None),
    status_filter:      Optional[str] = Query(None, alias="status"),
    db:                 Session = Depends(get_db),
):
    batch = db.get(HotelRoutinePMBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    items = db.query(HotelRoutinePMItem).filter(
        HotelRoutinePMItem.batch_ragic_id == batch_id
    ).order_by(HotelRoutinePMItem.seq_no).all()

    check_month = _get_check_month(batch.period_month)
    kpi  = _calc_kpi(items, check_month)
    cats = _calc_category_stats(items, check_month)

    filtered = []
    for it in items:
        s = _calc_status(it, check_month)
        if current_month_only and s == "non_current_month":
            continue
        if category and it.category != category:
            continue
        if status_filter and s != status_filter:
            continue
        filtered.append(_item_to_out(it, check_month))

    return HotelRoutinePMBatchDetail(
        batch      = HotelRoutinePMBatchOut.model_validate(batch),
        kpi        = kpi,
        items      = filtered,
        categories = cats,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches/{batch_id}/items
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches/{batch_id}/items", summary="取得批次下所有項目（含狀態篩選）")
def list_batch_items(
    batch_id:      str,
    status_filter: Optional[str] = Query(None, alias="status"),
    category:      Optional[str] = Query(None),
    db:            Session = Depends(get_db),
):
    batch = db.get(HotelRoutinePMBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    items = db.query(HotelRoutinePMItem).filter(
        HotelRoutinePMItem.batch_ragic_id == batch_id
    ).order_by(HotelRoutinePMItem.seq_no).all()

    check_month = _get_check_month(batch.period_month)
    result = []
    for it in items:
        s = _calc_status(it, check_month)
        if category and it.category != category:
            continue
        if status_filter and s != status_filter:
            continue
        result.append(_item_to_out(it, check_month))
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches/{batch_id}/kpi
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches/{batch_id}/kpi", summary="取得批次 KPI 統計")
def get_batch_kpi(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(HotelRoutinePMBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    items = db.query(HotelRoutinePMItem).filter(
        HotelRoutinePMItem.batch_ragic_id == batch_id
    ).all()
    check_month = _get_check_month(batch.period_month)
    return _calc_kpi(items, check_month)


# ══════════════════════════════════════════════════════════════════════════════
# GET /items  — 跨批次查詢
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/items", summary="跨批次查詢例行維護項目")
def list_items(
    batch_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    month:    Optional[int] = Query(None, ge=1, le=12),
    db:       Session = Depends(get_db),
):
    q = db.query(HotelRoutinePMItem)
    if batch_id:
        q = q.filter(HotelRoutinePMItem.batch_ragic_id == batch_id)
    if category:
        q = q.filter(HotelRoutinePMItem.category == category)
    items = q.order_by(
        HotelRoutinePMItem.batch_ragic_id,
        HotelRoutinePMItem.seq_no,
    ).all()

    check_month = month or date.today().month
    result = []
    for it in items:
        s = _calc_status(it, check_month)
        if status and s != status:
            continue
        result.append(_item_to_out(it, check_month))
    return result


# ══════════════════════════════════════════════════════════════════════════════
# GET /stats  — Dashboard 資料來源
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/stats", summary="全站統計（Dashboard 資料來源）", response_model=HotelRoutinePMStats)
def get_stats(
    year:  Optional[int] = Query(None, description="篩選年份，如 2026"),
    month: Optional[int] = Query(None, ge=1, le=12, description="篩選月份，如 5"),
    db:    Session = Depends(get_db),
):
    today = date.today()
    target_year  = year  or today.year
    target_month = month or today.month
    check_month  = target_month
    target_ym    = f"{target_year}/{target_month:02d}"

    current_batch = db.query(HotelRoutinePMBatch).filter(
        HotelRoutinePMBatch.period_month == target_ym
    ).first()

    if not current_batch and not (year or month):
        current_batch = db.query(HotelRoutinePMBatch).order_by(
            HotelRoutinePMBatch.period_month.desc()
        ).first()

    current_kpi = None
    overdue_items: list[HotelRoutinePMItemOut] = []
    upcoming_items: list[HotelRoutinePMItemOut] = []
    cats: list[HotelRoutinePMCategoryStat] = []
    status_dist: list[HotelRoutinePMStatusDistItem] = []

    if current_batch:
        items = db.query(HotelRoutinePMItem).filter(
            HotelRoutinePMItem.batch_ragic_id == current_batch.ragic_id
        ).order_by(HotelRoutinePMItem.seq_no).all()

        current_kpi = _calc_kpi(items, check_month)
        cats = _calc_category_stats(items, check_month)

        overdue_items = [
            _item_to_out(it, check_month)
            for it in items
            if _calc_status(it, check_month) == "overdue"
        ][:10]

        is_current_month = (target_year == today.year and target_month == today.month)
        upcoming_items = []
        for it in items:
            s = _calc_status(it, check_month)
            if s == "scheduled" and it.scheduled_date:
                if is_current_month:
                    try:
                        sched = datetime.strptime(
                            f"{today.year}/{it.scheduled_date}", "%Y/%m/%d"
                        ).date()
                        days_left = (sched - today).days
                        if 0 <= days_left <= 7:
                            upcoming_items.append(_item_to_out(it, check_month))
                    except Exception:
                        pass
                else:
                    upcoming_items.append(_item_to_out(it, check_month))
        upcoming_items = upcoming_items[:10]

        from collections import Counter

        def _dist_status(it: HotelRoutinePMItem) -> "str | None":
            s = _calc_status(it, check_month)
            if s == "non_current_month":
                return "completed" if bool(it.ragic_work_minutes) else None
            return s

        status_counts = Counter(
            s for it in items
            if (s := _dist_status(it)) is not None
        )
        for s, cnt in status_counts.items():
            status_dist.append(HotelRoutinePMStatusDistItem(
                status=s,
                label=STATUS_LABELS.get(s, s),
                count=cnt,
                color=STATUS_COLORS.get(s, "#666666"),
            ))

    return HotelRoutinePMStats(
        current_batch       = HotelRoutinePMBatchOut.model_validate(current_batch) if current_batch else None,
        current_kpi         = current_kpi,
        overdue_items       = overdue_items,
        upcoming_items      = upcoming_items,
        category_stats      = cats,
        status_distribution = status_dist,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/task-history — 依項目名稱查詢跨批次執行歷史
# ══════════════════════════════════════════════════════════════════════════════
def _offset_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """月份偏移（delta 可為負）"""
    total = (year * 12 + (month - 1)) + delta
    return total // 12, (total % 12) + 1


@router.get("/items/task-history", summary="依例行維護項目名稱查詢近 N 個月執行歷史")
def get_item_task_history(
    task_name: str = Query(..., description="保養項目名稱（完整比對）"),
    months:    int = Query(12, ge=1, le=24, description="查詢最近幾個月"),
    db:        Session = Depends(get_db),
):
    today = date.today()

    rows = (
        db.query(HotelRoutinePMItem, HotelRoutinePMBatch)
        .join(
            HotelRoutinePMBatch,
            HotelRoutinePMItem.batch_ragic_id == HotelRoutinePMBatch.ragic_id,
        )
        .filter(HotelRoutinePMItem.task_name == task_name)
        .order_by(HotelRoutinePMBatch.period_month.desc())
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"找不到例行維護項目：{task_name}")

    first_item: HotelRoutinePMItem = rows[0][0]

    month_map: dict[str, tuple] = {}
    for item, batch in rows:
        month_map[batch.period_month] = (item, batch)

    monthly_summary = []
    for i in range(months - 1, -1, -1):
        y, m = _offset_month(today.year, today.month, -i)
        period_month = f"{y}/{m:02d}"
        is_current = (y == today.year and m == today.month)

        if period_month in month_map:
            item, _batch = month_map[period_month]
            item_status = _calc_status(item, m)
            monthly_summary.append({
                "period_month":   period_month,
                "status":         item_status,
                "has_record":     True,
                "executor_name":  item.executor_name or "",
                "scheduled_date": item.scheduled_date or "",
                "start_time":     item.start_time or "",
                "end_time":       item.end_time or "",
                "ragic_work_minutes": item.ragic_work_minutes,
                "result_note":    item.result_note or "",
                "abnormal_flag":  bool(item.abnormal_flag),
                "abnormal_note":  item.abnormal_note or "",
                "is_current":     is_current,
            })
        else:
            monthly_summary.append({
                "period_month":   period_month,
                "status":         "unscheduled" if is_current else "no_batch",
                "has_record":     False,
                "executor_name":  "",
                "scheduled_date": "",
                "start_time":     "",
                "end_time":       "",
                "ragic_work_minutes": None,
                "result_note":    "",
                "abnormal_flag":  False,
                "abnormal_note":  "",
                "is_current":     is_current,
            })

    completed_months = sum(1 for ms in monthly_summary if ms["status"] == "completed")
    abnormal_count   = sum(1 for ms in monthly_summary if ms["abnormal_flag"])

    return {
        "task_name":       task_name,
        "category":        first_item.category or "",
        "frequency":       first_item.frequency or "",
        "exec_months_raw": first_item.exec_months_raw or "",
        "monthly_summary": monthly_summary,
        "stats": {
            "total_months":     months,
            "completed_months": completed_months,
            "abnormal_count":   abnormal_count,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats/year-matrix  — 全年 12 個月矩陣統計（⚠️ 必須在 /period-stats 之前）
# ══════════════════════════════════════════════════════════════════════════════
@router.get(
    "/period-stats/year-matrix",
    summary="全年 12 個月矩陣統計",
    response_model=HotelRoutinePMYearMatrix,
)
def get_period_stats_year_matrix(
    year:           Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly；None = 全部頻率"),
    db:             Session = Depends(get_db),
):
    target_year = year or date.today().year
    return _calc_year_matrix(db, target_year, frequency_type)


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats  — 週期統計（月 / 季 / 年）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats", summary="週期統計（月/季/年）", response_model=HotelRoutinePMPeriodStats)
def get_period_stats(
    period_type:    str           = Query("month", description="month | quarter | year"),
    year:           Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    month:          Optional[int] = Query(None, ge=1, le=12, description="月份（period_type=month 時使用）"),
    quarter:        Optional[int] = Query(None, ge=1, le=4,  description="季度 1-4（period_type=quarter 時使用）"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly；None = 全部頻率"),
    db:             Session = Depends(get_db),
):
    today = date.today()
    target_year = year or today.year

    if period_type not in ("month", "quarter", "year"):
        raise HTTPException(status_code=400, detail="period_type 須為 month | quarter | year")

    p_start, p_end, prev_end = _get_period_bounds(period_type, target_year, month, quarter)

    if period_type == "month":
        m = month or today.month
        period_label = f"{target_year}年{m}月"
    elif period_type == "quarter":
        q = quarter or ((today.month - 1) // 3 + 1)
        period_label = f"{target_year} Q{q}"
    else:
        period_label = f"{target_year}年"

    core = _calc_period_stats_core(db, p_start, p_end, prev_end, frequency_type)
    period_items_list = core.pop("period_items_list")

    breakdown = _calc_sub_breakdown(period_type, p_start, period_items_list)

    return HotelRoutinePMPeriodStats(
        period_type              = period_type,
        period_label             = period_label,
        period_start             = p_start.strftime("%Y-%m-%d"),
        period_end               = p_end.strftime("%Y-%m-%d"),
        prev_period_end          = prev_end.strftime("%Y-%m-%d"),
        prev_carry_over          = core["prev_carry_over"],
        prev_resolved_in_period  = core["prev_resolved_in_period"],
        carry_over_rate          = core["carry_over_rate"],
        period_total             = core["period_total"],
        period_completed         = core["period_completed"],
        period_rate              = core["period_rate"],
        sub_period_breakdown     = breakdown,
        incomplete_items         = core["incomplete_items"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats/year-matrix/items  — 矩陣格明細（數字點擊用）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats/year-matrix/items", summary="矩陣格明細查詢（數字點擊）")
def get_year_matrix_items(
    year:           int           = Query(..., description="年份，如 2026"),
    month:          int           = Query(..., ge=0, le=12, description="月份 1-12；合計欄傳 0 查全年"),
    metric:         str           = Query(..., description="prev_carry_over | prev_resolved | period_total | period_completed"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly；None = 全部"),
    db:             Session = Depends(get_db),
):
    if month == 0:
        p_start  = date(year, 1, 1)
        p_end    = date(year, 12, 31)
        prev_end = date(year - 1, 12, 31)
    else:
        p_start, p_end, prev_end = _get_period_bounds("month", year, month=month)

    rows = (
        db.query(HotelRoutinePMItem, HotelRoutinePMBatch)
        .join(HotelRoutinePMBatch,
              HotelRoutinePMItem.batch_ragic_id == HotelRoutinePMBatch.ragic_id)
        .all()
    )

    prev_carry_over_list: list[dict] = []
    period_items_list:    list[dict] = []

    for item, batch in rows:
        if not item.scheduled_date:
            continue
        if not _freq_match(item.frequency, frequency_type):
            continue
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []
        batch_month = int(batch.period_month.split("/")[1])
        if exec_months and batch_month not in exec_months:
            continue
        full_date = _reconstruct_full_date(item.scheduled_date, batch.period_month)
        if full_date is None:
            continue
        is_done  = bool(item.ragic_work_minutes)
        end_date = _parse_end_date(item.end_time)
        entry = {
            "item": item, "batch": batch, "full_date": full_date,
            "end_date": end_date, "is_done": is_done,
        }

        if full_date <= prev_end:
            done_before = is_done and end_date is not None and end_date <= prev_end
            if not done_before:
                prev_carry_over_list.append(entry)

        if p_start <= full_date <= p_end:
            period_items_list.append(entry)

    if metric == "prev_carry_over":
        target = prev_carry_over_list
    elif metric == "prev_resolved":
        target = [x for x in prev_carry_over_list
                  if x["end_date"] is not None and p_start <= x["end_date"] <= p_end]
    elif metric == "period_completed":
        target = [x for x in period_items_list if x["is_done"]]
    else:  # period_total
        target = period_items_list

    result = []
    for e in target:
        it: HotelRoutinePMItem  = e["item"]
        b:  HotelRoutinePMBatch = e["batch"]
        full_date_str = e["full_date"].strftime("%Y/%m/%d")
        ragic_link = _ragic_url(RAGIC_PATH, it.batch_ragic_id)
        result.append({
            "ragic_id":            it.ragic_id,
            "batch_ragic_id":      it.batch_ragic_id,
            "period_month":        b.period_month,
            "category":            it.category,
            "task_name":           it.task_name,
            "frequency":           it.frequency,
            "scheduled_date_full": full_date_str,
            "end_time":            it.end_time,
            "ragic_work_minutes":  it.ragic_work_minutes,
            "status": (
                "completed"   if bool(it.ragic_work_minutes) else
                "in_progress" if it.start_time else (
                "overdue" if (e["full_date"] < date.today() and not it.start_time and it.scheduled_date)
                else "scheduled" if it.scheduled_date else "unscheduled"
                )
            ),
            "executor_name": it.executor_name,
            "result_note":   it.result_note,
            "abnormal_flag": it.abnormal_flag,
            "abnormal_note": it.abnormal_note,
            "ragic_link":    ragic_link,
        })

    return {"total": len(result), "items": result}


# ── 保養項目目錄（依頻率分類）──────────────────────────────────────────────────
@router.get("/items/catalog", summary="取得例行維護項目目錄（依頻率分類）")
def get_items_catalog(
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from sqlalchemy import func as sqlfunc

    subq = (
        db.query(
            HotelRoutinePMItem.task_name,
            HotelRoutinePMItem.category,
            HotelRoutinePMItem.frequency,
            sqlfunc.max(HotelRoutinePMItem.seq_no).label("max_seq"),
        )
        .group_by(
            HotelRoutinePMItem.task_name,
            HotelRoutinePMItem.category,
            HotelRoutinePMItem.frequency,
        )
        .subquery()
    )

    rows = (
        db.query(HotelRoutinePMItem)
        .join(
            subq,
            (HotelRoutinePMItem.task_name   == subq.c.task_name)
            & (HotelRoutinePMItem.category  == subq.c.category)
            & (HotelRoutinePMItem.frequency == subq.c.frequency)
            & (HotelRoutinePMItem.seq_no    == subq.c.max_seq),
        )
        .order_by(HotelRoutinePMItem.category, HotelRoutinePMItem.seq_no)
        .all()
    )

    result = []
    seen: set[tuple] = set()
    for r in rows:
        if not _freq_match(r.frequency, frequency_type):
            continue
        key = (r.task_name, r.category, r.frequency)
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "seq_no":            r.seq_no,
            "category":          r.category,
            "frequency":         r.frequency,
            "task_name":         r.task_name,
            "location":          r.location,
            "estimated_minutes": r.estimated_minutes,
            "exec_months_raw":   r.exec_months_raw,
        })

    return {"total": len(result), "items": result}


# ══════════════════════════════════════════════════════════════════════════════
# 排程管理（hotel_routine_pm_schedule）相關 Endpoints
# ══════════════════════════════════════════════════════════════════════════════

def _get_latest_batch_items(db: Session) -> list[HotelRoutinePMItem]:
    """取得最新批次的所有例行維護項目，作為主檔來源。"""
    latest_batch = (
        db.query(HotelRoutinePMBatch)
        .order_by(HotelRoutinePMBatch.period_month.desc())
        .first()
    )
    if not latest_batch:
        return []
    return (
        db.query(HotelRoutinePMItem)
        .filter(HotelRoutinePMItem.batch_ragic_id == latest_batch.ragic_id)
        .order_by(HotelRoutinePMItem.seq_no)
        .all()
    )


def _calc_schedule_status(rec: HotelRoutinePMSchedule) -> str:
    """計算 hotel_routine_pm_schedule 記錄的狀態。"""
    if rec.is_completed:
        return "completed"
    if rec.start_time:
        return "in_progress"
    if rec.scheduled_date:
        try:
            today = date.today()
            year = int(rec.year_month.split("/")[0])
            sched = datetime.strptime(f"{year}/{rec.scheduled_date}", "%Y/%m/%d").date()
            if sched < today:
                return "overdue"
        except Exception:
            pass
        return "scheduled"
    return "unscheduled"


def _schedule_to_out(rec: HotelRoutinePMSchedule) -> HotelRoutinePMScheduleOut:
    """ORM → Pydantic，動態注入 status。"""
    return HotelRoutinePMScheduleOut(
        id               = rec.id,
        year_month       = rec.year_month,
        item_ragic_id    = rec.item_ragic_id,
        category         = rec.category,
        task_name        = rec.task_name,
        location         = rec.location,
        frequency        = rec.frequency,
        estimated_minutes= rec.estimated_minutes,
        scheduled_date   = rec.scheduled_date,
        executor_name    = rec.executor_name,
        schedule_source  = rec.schedule_source,
        start_time       = rec.start_time,
        end_time         = rec.end_time,
        is_completed     = rec.is_completed,
        result_note      = rec.result_note,
        abnormal_flag    = rec.abnormal_flag,
        abnormal_note    = rec.abnormal_note,
        portal_edited_at = rec.portal_edited_at,
        created_at       = rec.created_at,
        updated_at       = rec.updated_at,
        status           = _calc_schedule_status(rec),
    )


# ── 排程產生核心邏輯（供 endpoint 與 scheduler / lazy auto-generate 共用）──────

def _do_generate_hotel_routine_pm(
    year: int, month: int, db: Session
) -> HotelRoutinePMScheduleGenerateResult:
    """
    依最新批次頻率規則，為 year/month 產生 HotelRoutinePMSchedule 記錄。
    冪等保護：
      - is_completed=True          → 跳過
      - portal_edited_at IS NOT NULL → 跳過
      - 其他已存在記錄               → 更新 scheduled_date / executor_name
    """
    year_month = f"{year}/{month:02d}"
    items = _get_latest_batch_items(db)

    target_batch = (
        db.query(HotelRoutinePMBatch)
        .filter(HotelRoutinePMBatch.period_month == year_month)
        .first()
    )
    month_sched_lookup: dict[tuple, str] = {}
    if target_batch:
        target_items = (
            db.query(HotelRoutinePMItem)
            .filter(HotelRoutinePMItem.batch_ragic_id == target_batch.ragic_id)
            .all()
        )
        for ti in target_items:
            if not ti.scheduled_date:
                continue
            parts = ti.scheduled_date.split("/")
            if len(parts) == 3:
                mmdd = f"{parts[1]}/{parts[2]}"
            elif len(parts) == 2:
                mmdd = ti.scheduled_date
            else:
                continue
            month_sched_lookup[
                (ti.task_name.strip(), ti.category.strip(), ti.location.strip())
            ] = mmdd

    generated             = 0
    updated               = 0
    skipped_completed     = 0
    skipped_edited        = 0
    skipped_non_month     = 0
    skipped_no_frequency  = 0
    errors: list[str]     = []

    for item in items:
        try:
            freq = (item.frequency or "").strip()

            if not freq:
                skipped_no_frequency += 1
                continue

            if not _should_schedule(item, year, month):
                skipped_non_month += 1
                continue

            existing = (
                db.query(HotelRoutinePMSchedule)
                .filter(
                    HotelRoutinePMSchedule.year_month    == year_month,
                    HotelRoutinePMSchedule.item_ragic_id == item.ragic_id,
                )
                .first()
            )

            if existing:
                if existing.is_completed:
                    skipped_completed += 1
                    continue
                if existing.portal_edited_at is not None:
                    skipped_edited += 1
                    continue
                key = (item.task_name.strip(), item.category.strip(), item.location.strip())
                resolved_date = month_sched_lookup.get(key) or item.scheduled_date or ""
                existing.scheduled_date    = resolved_date
                existing.executor_name     = item.executor_name
                existing.estimated_minutes = item.estimated_minutes
                existing.updated_at        = datetime.now()
                updated += 1
            else:
                key = (item.task_name.strip(), item.category.strip(), item.location.strip())
                resolved_date = month_sched_lookup.get(key) or item.scheduled_date or ""
                new_rec = HotelRoutinePMSchedule(
                    year_month        = year_month,
                    item_ragic_id     = item.ragic_id,
                    category          = item.category,
                    task_name         = item.task_name,
                    location          = item.location,
                    frequency         = item.frequency,
                    estimated_minutes = item.estimated_minutes,
                    scheduled_date    = resolved_date,
                    executor_name     = item.executor_name,
                    schedule_source   = "auto",
                )
                db.add(new_rec)
                generated += 1

        except Exception as exc:
            errors.append(f"item {item.ragic_id}: {exc}")

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        errors.append(f"commit error: {exc}")

    return HotelRoutinePMScheduleGenerateResult(
        year_month            = year_month,
        generated             = generated,
        updated               = updated,
        skipped_completed     = skipped_completed,
        skipped_edited        = skipped_edited,
        skipped_non_month     = skipped_non_month,
        skipped_no_frequency  = skipped_no_frequency,
        errors                = errors,
    )


# ── POST /schedule/generate ───────────────────────────────────────────────────

@router.post(
    "/schedule/generate",
    summary="產生指定月份例行維護排程（防重複）",
    response_model=HotelRoutinePMScheduleGenerateResult,
)
def generate_schedule(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    db:    Session = Depends(get_db),
):
    return _do_generate_hotel_routine_pm(year, month, db)


# ── GET /schedule ─────────────────────────────────────────────────────────────

@router.get("/schedule", summary="查詢例行維護排程明細列表")
def list_schedule(
    year_month: Optional[str] = Query(None, description="月份，如 2026/05；預設為本月"),
    category:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    db:         Session = Depends(get_db),
):
    if not year_month:
        today = date.today()
        year_month = f"{today.year}/{today.month:02d}"

    q = db.query(HotelRoutinePMSchedule).filter(HotelRoutinePMSchedule.year_month == year_month)
    if category:
        q = q.filter(HotelRoutinePMSchedule.category == category)

    records   = q.order_by(HotelRoutinePMSchedule.category, HotelRoutinePMSchedule.task_name).all()
    items_out = [_schedule_to_out(r) for r in records]

    if status:
        if status == "abnormal":
            items_out = [i for i in items_out if i.abnormal_flag]
        else:
            items_out = [i for i in items_out if i.status == status]

    all_items    = _get_latest_batch_items(db)
    year_i       = int(year_month.split("/")[0])
    month_i      = int(year_month.split("/")[1])
    existing_ids = {r.item_ragic_id for r in records}
    should_do_not_done = sum(
        1 for it in all_items
        if _should_schedule(it, year_i, month_i) and it.ragic_id not in existing_ids
    )

    return {
        "year_month":         year_month,
        "total":              len(items_out),
        "should_do_not_done": should_do_not_done,
        "items":              [i.model_dump() for i in items_out],
    }


# ── GET /schedule/kpi ─────────────────────────────────────────────────────────

@router.get(
    "/schedule/kpi",
    summary="例行維護排程 KPI 統計",
    response_model=HotelRoutinePMScheduleKPI,
)
def get_schedule_kpi(
    year_month: Optional[str] = Query(None, description="月份，如 2026/05；預設本月"),
    db:         Session = Depends(get_db),
):
    if not year_month:
        today = date.today()
        year_month = f"{today.year}/{today.month:02d}"

    records   = db.query(HotelRoutinePMSchedule).filter(
        HotelRoutinePMSchedule.year_month == year_month
    ).all()
    items_out = [_schedule_to_out(r) for r in records]

    total     = len(items_out)
    completed = sum(1 for i in items_out if i.status == "completed")

    all_items    = _get_latest_batch_items(db)
    year_i       = int(year_month.split("/")[0])
    month_i      = int(year_month.split("/")[1])
    existing_ids = {r.item_ragic_id for r in records}
    should_do_not_done = sum(
        1 for it in all_items
        if _should_schedule(it, year_i, month_i) and it.ragic_id not in existing_ids
    )

    return HotelRoutinePMScheduleKPI(
        total              = total,
        unscheduled        = sum(1 for i in items_out if i.status == "unscheduled"),
        scheduled          = sum(1 for i in items_out if i.status == "scheduled"),
        in_progress        = sum(1 for i in items_out if i.status == "in_progress"),
        completed          = completed,
        overdue            = sum(1 for i in items_out if i.status == "overdue"),
        abnormal           = sum(1 for i in items_out if i.abnormal_flag),
        should_do_not_done = should_do_not_done,
        completion_rate    = round(completed / total * 100, 1) if total > 0 else 0.0,
    )


# ── GET /schedule/overdue ─────────────────────────────────────────────────────

@router.get("/schedule/overdue", summary="跨月逾期未執行清單")
def list_overdue_schedule(
    before_date: Optional[str] = Query(None, description="截止日期 YYYY/MM/DD；預設今天"),
    db:          Session = Depends(get_db),
):
    if before_date:
        try:
            cutoff = datetime.strptime(before_date, "%Y/%m/%d").date()
        except ValueError:
            cutoff = date.today()
    else:
        cutoff = date.today()

    all_records = (
        db.query(HotelRoutinePMSchedule)
        .filter(HotelRoutinePMSchedule.is_completed == False)  # noqa: E712
        .filter(HotelRoutinePMSchedule.scheduled_date != "")
        .order_by(HotelRoutinePMSchedule.year_month, HotelRoutinePMSchedule.scheduled_date)
        .all()
    )

    overdue_items = []
    months_set: set[str] = set()

    for rec in all_records:
        if rec.start_time:
            continue
        try:
            year = int(rec.year_month.split("/")[0])
            sched = datetime.strptime(f"{year}/{rec.scheduled_date}", "%Y/%m/%d").date()
        except Exception:
            continue
        if sched >= cutoff:
            continue

        out_dict = _schedule_to_out(rec).model_dump()
        out_dict["overdue_days"] = (cutoff - sched).days
        overdue_items.append(out_dict)
        months_set.add(rec.year_month)

    return {
        "total":           len(overdue_items),
        "months_affected": sorted(months_set),
        "items":           overdue_items,
    }


# ── PATCH /schedule/{schedule_id} ─────────────────────────────────────────────

@router.patch("/schedule/{schedule_id}", summary="人工調整例行維護排程明細")
def update_schedule(
    schedule_id: int,
    body:        HotelRoutinePMScheduleUpdate,
    db:          Session = Depends(get_db),
):
    rec = db.get(HotelRoutinePMSchedule, schedule_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Schedule record not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(rec, field, value)

    rec.schedule_source  = "manual"
    rec.portal_edited_at = datetime.now()
    rec.updated_at       = datetime.now()
    if rec.start_time and rec.end_time:
        rec.is_completed = True

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

    return _schedule_to_out(rec)


# ── GET /schedule/annual-matrix ───────────────────────────────────────────────

@router.get(
    "/schedule/annual-matrix",
    summary="年度計劃矩陣（12欄）",
    response_model=HotelRoutinePMScheduleAnnualMatrix,
)
def get_annual_matrix(
    year:     int = Query(..., description="年份，如 2026"),
    category: Optional[str] = Query(None),
    db:       Session = Depends(get_db),
):
    all_items = _get_latest_batch_items(db)
    if category:
        all_items = [it for it in all_items if it.category == category]

    year_records = (
        db.query(HotelRoutinePMSchedule)
        .filter(HotelRoutinePMSchedule.year_month.like(f"{year}/%"))
        .all()
    )
    schedule_map: dict[tuple[str, int], HotelRoutinePMSchedule] = {}
    for rec in year_records:
        try:
            m = int(rec.year_month.split("/")[1])
            schedule_map[(rec.item_ragic_id, m)] = rec
        except Exception:
            pass

    year_batches = (
        db.query(HotelRoutinePMBatch)
        .filter(HotelRoutinePMBatch.period_month.like(f"{year}/%"))
        .all()
    )
    month_sched_lookup: dict[int, dict[tuple, str]] = {}
    for batch in year_batches:
        try:
            bm = int(batch.period_month.split("/")[1])
        except Exception:
            continue
        batch_items = (
            db.query(HotelRoutinePMItem)
            .filter(HotelRoutinePMItem.batch_ragic_id == batch.ragic_id)
            .all()
        )
        lookup: dict[tuple, str] = {}
        for bi in batch_items:
            if not bi.scheduled_date:
                continue
            parts = bi.scheduled_date.split("/")
            if len(parts) == 3:
                mmdd = f"{parts[1]}/{parts[2]}"
            elif len(parts) == 2:
                mmdd = bi.scheduled_date
            else:
                continue
            key = (bi.task_name.strip(), bi.category.strip(), bi.location.strip())
            lookup[key] = mmdd
        month_sched_lookup[bm] = lookup

    rows: list[HotelRoutinePMScheduleMatrixRow] = []
    completed_cnt = 0

    for item in all_items:
        cells: list[HotelRoutinePMScheduleMatrixCell] = []
        for m in range(1, 13):
            rec = schedule_map.get((item.ragic_id, m))
            if rec:
                if not rec.scheduled_date:
                    lookup = month_sched_lookup.get(m, {})
                    key = (item.task_name.strip(), item.category.strip(), item.location.strip())
                    batch_mmdd = lookup.get(key)
                    if batch_mmdd:
                        rec.scheduled_date = batch_mmdd
                status = _calc_schedule_status(rec)
                if status == "completed":
                    completed_cnt += 1
                cells.append(HotelRoutinePMScheduleMatrixCell(
                    month          = m,
                    status         = status,
                    schedule_id    = rec.id,
                    scheduled_date = rec.scheduled_date or None,
                ))
            else:
                freq = (item.frequency or "").strip()
                if not freq:
                    cells.append(HotelRoutinePMScheduleMatrixCell(
                        month=m, status="no_frequency", schedule_id=None
                    ))
                elif _should_schedule(item, year, m):
                    cell_sched_date: Optional[str] = None
                    cell_status = "no_data"
                    if item.scheduled_date:
                        try:
                            parts = item.scheduled_date.split("/")
                            sched_month = int(parts[0])
                            day = parts[-1].zfill(2)
                            cell_sched_date = f"{m:02d}/{day}"
                            if sched_month == m:
                                if item.is_completed or bool(item.ragic_work_minutes):
                                    cell_status = "completed"
                                    completed_cnt += 1
                                elif item.start_time:
                                    cell_status = "in_progress"
                                else:
                                    full_sched = datetime.strptime(
                                        f"{year}/{item.scheduled_date}", "%Y/%m/%d"
                                    ).date()
                                    cell_status = "overdue" if full_sched < date.today() else "scheduled"
                        except Exception:
                            cell_sched_date = None
                    cells.append(HotelRoutinePMScheduleMatrixCell(
                        month          = m,
                        status         = cell_status,
                        schedule_id    = None,
                        scheduled_date = cell_sched_date,
                    ))
                else:
                    cells.append(HotelRoutinePMScheduleMatrixCell(
                        month=m, status="non_month", schedule_id=None
                    ))

        rows.append(HotelRoutinePMScheduleMatrixRow(
            item_ragic_id = item.ragic_id,
            category      = item.category,
            task_name     = item.task_name,
            location      = item.location,
            frequency     = item.frequency or "",
            cells         = cells,
        ))

    total_cells = sum(
        1 for row in rows
        for c in row.cells
        if c.status not in ("non_month", "no_frequency")
    )

    # ── 方案 B：Lazy auto-generate ────────────────────────────────────────────
    # 當前年度：若過去或當月有 no_data 的格，代表排程記錄尚未建立，自動補產生。
    # _do_generate_hotel_routine_pm 為冪等，不會覆蓋已完成/人工調整的記錄。
    today = date.today()
    if year == today.year:
        months_need_generate = {
            c.month
            for row in rows
            for c in row.cells
            if c.status == "no_data" and c.month <= today.month
        }
        for m in sorted(months_need_generate):
            try:
                _do_generate_hotel_routine_pm(year, m, db)
            except Exception as exc:
                print(f"[hotel_routine_pm] lazy auto-generate {year}/{m:02d} failed: {exc}")

    return HotelRoutinePMScheduleAnnualMatrix(
        year    = year,
        rows    = rows,
        summary = {
            "total_items":     len(rows),
            "total_cells":     total_cells,
            "completed_count": completed_cnt,
            "completion_rate": (
                round(completed_cnt / total_cells * 100, 1)
                if total_cells > 0 else 0.0
            ),
        },
    )
