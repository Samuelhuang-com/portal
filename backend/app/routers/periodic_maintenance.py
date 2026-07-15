"""
週期保養表 API Router
Prefix: /api/v1/periodic-maintenance

2026-07-14 起資料來源改為 Ragic Sheet 11（平表），Sheet 6/8 正式退役，
見 app/services/periodic_maintenance_sync.py 檔頭說明與 project memory
project_hotel_pm_sheet11_migration.md。

端點：
  POST /sync                         — 手動從 Ragic 同步
  GET  /batches                      — 批次清單（年份篩選）
  GET  /batches/{batch_id}           — 單筆批次 + 所有項目 + KPI
  GET  /batches/{batch_id}/items     — 該批次項目（含狀態篩選）
  GET  /batches/{batch_id}/kpi       — 批次 KPI 統計
  GET  /items                        — 所有項目跨批次查詢
  GET  /items/{item_ragic_id}/worklogs  — 單一項目維修記錄明細（2026-07-14 同日追加）
  GET  /items/{item_ragic_id}/db-images — 單一項目附圖（2026-07-14 新增）
  GET  /stats                        — 全站統計（Dashboard 資料來源）
  GET  /period-stats                 — 週期統計（月/季/年）
  PATCH /items/{item_id}             — Portal 回填（執行時間/異常等）
"""
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Optional, List

from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.periodic_maintenance import (
    PeriodicMaintenanceBatch, PeriodicMaintenanceItem, PeriodicMaintenanceItemWorklog,
)
from app.models.pm_schedule import PMSchedule
from app.schemas.periodic_maintenance import (
    PMBatchOut, PMItemOut, PMBatchKPI, PMBatchDetail,
    CategoryStat, StatusDistItem, PMStats, PMItemUpdate,
    PMPeriodStats, PMSubPeriodBreakdown, PMIncompleteItem,
    PMYearMatrix, PMYearMatrixMonth,
    PMScheduleOut, PMScheduleKPI, PMScheduleGenerateResult,
    PMScheduleUpdate, PMScheduleMatrixCell, PMScheduleMatrixRow,
    PMScheduleAnnualMatrix,
)
from app.services.periodic_maintenance_sync import sync_from_ragic
from app.services.ragic_adapter import RagicAdapter
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


# ── 業務邏輯輔助函式 ──────────────────────────────────────────────────────────

_TIME_FMTS = ["%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]

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


def _calc_status(item: PeriodicMaintenanceItem, check_month: int) -> str:
    """
    依 Ragic 欄位值推導保養項目狀態（唯讀，不依賴任何 Portal 編輯欄位）。

    判斷順序：
    1. 非本月 — 依頻率與 exec_months 判斷本月不適用
    2. 已完成 — 保養時間啟（start_time）AND 保養時間迄（end_time）均有值
    3. 進行中 — 保養時間啟有值，但無迄
    4. 逾期   — 排定日期有值，且該日期已過今天
    5. 已排定 — 排定日期有值，尚未到期
    6. 未排定 — 以上皆無

    修正（2026-05）：月頻率項目 exec_months 為空是正常情況（每月執行不需列月份），
    應視為「本月適用」，不落入 unscheduled。
    """
    exec_months: list[int] = []
    try:
        exec_months = json.loads(item.exec_months_json or "[]")
    except Exception:
        pass

    # 1. 非本月判斷：
    #    - exec_months 有值 → 直接判斷 check_month 是否在清單中
    #    - exec_months 為空 + 頻率有值 → 依頻率規則推算（月=永遠適用）
    if exec_months:
        if check_month not in exec_months:
            return "non_current_month"
    elif item.frequency:
        # 月頻率 exec_months 為空 → 每月適用，不視為非本月
        # 其他頻率 exec_months 為空 → 依週期公式推算（從 1 月起算）
        if not _should_schedule_by_frequency(item.frequency, check_month):
            return "non_current_month"
    # frequency 為空 → 無法判斷，繼續往下走（不判斷非本月）

    # 2. 已完成
    if item.start_time and item.end_time:
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


def _should_schedule(item: PeriodicMaintenanceItem, year: int, month: int) -> bool:
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


_ITEM_RAGIC_BASE = "https://ap12.ragic.com/soutlet001/periodic-maintenance/11"


def _item_to_out(item: PeriodicMaintenanceItem, check_month: int) -> PMItemOut:
    """ORM → Pydantic，注入 status 計算值。"""
    out = PMItemOut(
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
        start_time           = item.start_time,
        end_time             = item.end_time,
        ragic_work_minutes   = item.ragic_work_minutes,
        # 動態計算：啟+迄均有值 = 完成（與 _calc_status 邏輯一致，不依賴 DB 舊存值）
        is_completed         = bool(item.start_time and item.end_time),
        result_note       = item.result_note,
        abnormal_flag     = item.abnormal_flag,
        abnormal_note     = item.abnormal_note,
        portal_edited_at  = item.portal_edited_at,
        synced_at         = item.synced_at,
        status            = _calc_status(item, check_month),
        # 2026-07-14 新增：項目改用 Sheet 11 自己的 _ragicId 直連，並帶出「維修工時」
        # （小時，來源 Sheet11「維修工時」欄位，比照 mall_pm Sheet24 語意）
        ragic_url      = f"{_ITEM_RAGIC_BASE}/{item.ragic_id}" if item.ragic_id else "",
        repair_hours   = item.repair_hours,
    )
    return out


def _calc_kpi(items: list[PeriodicMaintenanceItem], check_month: int) -> PMBatchKPI:
    statuses = [_calc_status(it, check_month) for it in items]
    current_items = [(it, s) for it, s in zip(items, statuses) if s != "non_current_month"]
    total_current = len(current_items)

    # 已完成：所有保養時間啟+迄均有值的項目（含非本月，與表格「完成」☑ 欄一致）
    total_all   = len(items)
    completed   = sum(1 for it in items if it.start_time and it.end_time)
    in_progress = sum(1 for _, s in current_items if s == "in_progress")
    scheduled   = sum(1 for _, s in current_items if s == "scheduled")
    unscheduled = sum(1 for _, s in current_items if s == "unscheduled")
    overdue     = sum(1 for _, s in current_items if s == "overdue")
    # 2026-07-14 修正（比照 mall_periodic_maintenance.py 同日修正，OneDrive commit
    # 24e57b8「fix: 20260714-002」）：abnormal 原本算「整批全部項目」，跟
    # overdue/scheduled/unscheduled/in_progress 這幾個都只算「本月項目」
    # （current_items）的口徑不一致，改為比照這幾個欄位只算本月項目。
    abnormal    = sum(1 for it, _ in current_items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)
    # 2026-07-14 修正（比照 mall_pm/full_bldg_pm 2026-07-13 同型改版）：優先使用
    # Sheet 11「維修工時」（repair_hours，小時）換算為分鐘；若無值（例如舊 Sheet 8
    # 資料的 ragic_work_minutes），fallback 到舊版「工時計算」欄位；兩者皆無才用
    # end_time - start_time 時間跨度估算。
    actual      = sum(
        (round(it.repair_hours * 60) if it.repair_hours is not None
         else it.ragic_work_minutes if it.ragic_work_minutes is not None
         else _time_diff_minutes(it.start_time, it.end_time))
        for it in items if it.start_time and it.end_time
    )
    # 完成率：已完成 / 全部項目（含非本月），與 KPI「已完成」定義一致
    rate = round(completed / total_all * 100, 1) if total_all > 0 else 0.0

    return PMBatchKPI(
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


def _calc_category_stats(items: list[PeriodicMaintenanceItem], check_month: int) -> list[CategoryStat]:
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
        result.append(CategoryStat(
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
    空值或解析失敗回傳 None。
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
    """
    'YYYY/MM/DD HH:MM:SS' → date(YYYY, MM, DD)
    解析失敗回傳 None。
    """
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
    """
    回傳 (period_start, period_end, prev_period_end)

    period_type = "month"   → 月區間
    period_type = "quarter" → 季區間（quarter 1-4）
    period_type = "year"    → 年區間
    """
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
    """
    共用統計核心。
    回傳 dict 含：
      prev_carry_over, prev_resolved_in_period, carry_over_rate,
      period_total, period_completed, period_rate,
      incomplete_items, period_items_list（供子期間分布使用）
    """
    rows = (
        db.query(PeriodicMaintenanceItem, PeriodicMaintenanceBatch)
        .join(
            PeriodicMaintenanceBatch,
            PeriodicMaintenanceItem.batch_ragic_id == PeriodicMaintenanceBatch.ragic_id,
        )
        .all()
    )

    prev_carry_over_list: list[dict] = []
    period_items_list:    list[dict] = []

    for item, batch in rows:
        # ── 頻率篩選 ──
        if not _freq_match(item.frequency, frequency_type):
            continue

        # ── 僅計算本批次月份有效的項目（排除 non_current_month）──
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []
        batch_year_num  = int(batch.period_month.split("/")[0])
        batch_month_num = int(batch.period_month.split("/")[1])
        if exec_months and batch_month_num not in exec_months:
            continue

        # ── full_date = 批次月份 1 日（不依賴 scheduled_date，scheduled_date 只是排定計劃）──
        full_date = date(batch_year_num, batch_month_num, 1)

        end_date = _parse_end_date(item.end_time)
        is_done  = bool(item.start_time and item.end_time)

        entry = {
            "item":      item,
            "batch":     batch,
            "full_date": full_date,
            "end_date":  end_date,
            "is_done":   is_done,
        }

        # ── 上期累計未完成 ──
        # 表定日期 <= 上期末，且截至上期末仍未完成
        if full_date <= prev_period_end:
            done_before = (
                is_done
                and end_date is not None
                and end_date <= prev_period_end
            )
            if not done_before:
                prev_carry_over_list.append(entry)

        # ── 本期項目 ──
        if period_start <= full_date <= period_end:
            period_items_list.append(entry)

    # 上期未完成，本期結案
    prev_resolved_list = [
        x for x in prev_carry_over_list
        if x["end_date"] is not None
        and period_start <= x["end_date"] <= period_end
    ]

    # 本期完成
    period_completed_list = [x for x in period_items_list if x["is_done"]]

    # 未完成事項說明（result_note 非空才列入；空白不計算）
    incomplete_items = [
        PMIncompleteItem(
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
        "period_items_list":       period_items_list,   # 供子期間分布使用，caller 負責 pop
    }


def _calc_sub_breakdown(
    period_type: str,
    period_start: date,
    period_items_list: list[dict],
) -> list[PMSubPeriodBreakdown]:
    """
    季統計 → 3 個月分布
    年統計 → Q1-Q4 分布
    月統計 → 空清單
    """
    if period_type == "month":
        return []

    breakdown: list[PMSubPeriodBreakdown] = []
    year = period_start.year

    if period_type == "quarter":
        start_m = period_start.month          # Q 的第一個月
        for i in range(3):
            m = start_m + i
            _, last_day = monthrange(year, m)
            m_start = date(year, m, 1)
            m_end   = date(year, m, last_day)
            items_m = [x for x in period_items_list if m_start <= x["full_date"] <= m_end]
            total     = len(items_m)
            completed = sum(1 for x in items_m if x["is_done"])
            breakdown.append(PMSubPeriodBreakdown(
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
            breakdown.append(PMSubPeriodBreakdown(
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


def _calc_year_matrix(db: Session, year: int, frequency_type: Optional[str] = None) -> PMYearMatrix:
    """
    全年 12 個月矩陣統計。
    frequency_type: "monthly" | "quarterly" | "yearly" | None（不篩選）
    策略：一次 JOIN 查詢撈全部有效行，再用純 Python 按月分組計算，
    避免對 DB 發出 12 次獨立查詢。
    """
    # ── 一次撈出全部有效 item+batch ──────────────────────────────────────────
    rows = (
        db.query(PeriodicMaintenanceItem, PeriodicMaintenanceBatch)
        .join(
            PeriodicMaintenanceBatch,
            PeriodicMaintenanceItem.batch_ragic_id == PeriodicMaintenanceBatch.ragic_id,
        )
        .filter(PeriodicMaintenanceBatch.period_month.like(f"{year}/%"))   # 限制指定年份
        .all()
    )

    # ── 預處理：頻率篩選 + exec_months 過濾 + full_date（批次月份 1 日）──────
    processed: list[dict] = []
    for item, batch in rows:
        # ── 頻率篩選 ──
        if not _freq_match(item.frequency, frequency_type):
            continue
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []
        batch_year_num  = int(batch.period_month.split("/")[0])
        batch_month_num = int(batch.period_month.split("/")[1])
        if exec_months and batch_month_num not in exec_months:
            continue
        # full_date = 批次月份 1 日（不依賴 scheduled_date）
        full_date = date(batch_year_num, batch_month_num, 1)
        end_date = _parse_end_date(item.end_time)
        is_done  = bool(item.start_time and item.end_time)
        processed.append({
            "item":      item,
            "full_date": full_date,
            "end_date":  end_date,
            "is_done":   is_done,
        })

    # ── 預載當年 pm_schedule（補充 period_total / period_completed）────────────
    # 頻率關鍵字集合，用於 pm_schedule 篩選
    freq_kws: Optional[set] = _FREQ_KEYWORDS.get(frequency_type) if frequency_type else None

    # ── 逐月計算 ─────────────────────────────────────────────────────────────
    month_results: list[PMYearMatrixMonth] = []
    for m in range(1, 13):
        p_start, p_end, prev_end = _get_period_bounds("month", year, month=m)

        prev_carry_over_list: list[dict] = []
        period_items_list:    list[dict] = []

        for e in processed:
            fd       = e["full_date"]
            is_done  = e["is_done"]
            end_date = e["end_date"]

            # 上期累計未完成
            if fd <= prev_end:
                done_before = is_done and end_date is not None and end_date <= prev_end
                if not done_before:
                    prev_carry_over_list.append(e)

            # 本期項目（Ragic batch 資料）
            if p_start <= fd <= p_end:
                period_items_list.append(e)

        prev_resolved_list = [
            x for x in prev_carry_over_list
            if x["end_date"] is not None
            and p_start <= x["end_date"] <= p_end
        ]
        period_completed_list = [x for x in period_items_list if x["is_done"]]

        # ── 以 pm_schedule 補充本月件數（優先使用）────────────────────────────
        year_month_str = f"{year}/{m:02d}"
        sched_q = db.query(PMSchedule).filter(PMSchedule.year_month == year_month_str)
        if freq_kws:
            sched_q = sched_q.filter(PMSchedule.frequency.in_(freq_kws))
        sched_recs = sched_q.all()

        if sched_recs:
            # pm_schedule 有資料 → 使用排程記錄計數
            n_total = len(sched_recs)
            n_done  = sum(1 for r in sched_recs if r.is_completed)
            notes_parts = [
                f"{r.task_name}：{r.result_note}"
                for r in sched_recs
                if not r.is_completed and r.result_note
            ]
        elif period_items_list:
            # 有實際批次資料（無排程記錄）→ 直接以當月實際批次項目數為準
            # （與 /period-stats/year-matrix/items 明細查詢邏輯一致：兩者皆讀取
            #   period_items_list。過去改用「最新批次」的項目定義套用
            #   _should_schedule 公式反推應排月份，但年/季頻率項目在不同月份
            #   的批次本來就是彼此不同的項目集合，套用單一批次的 exec_months
            #   公式去判斷「其他月份」會導致矩陣格數字與點擊明細筆數不一致
            #   （例如 2026/04 矩陣顯示 2 筆，點擊明細卻有 4 筆）。）
            n_total = len(period_items_list)
            n_done  = len(period_completed_list)
            notes_parts = [
                f"{x['item'].task_name}：{x['item'].result_note}"
                for x in period_items_list
                if not x["is_done"] and x["item"].result_note
            ]
        else:
            # 無批次資料且無排程記錄 → 不顯示（前端渲染為 "—"）
            n_total     = 0
            n_done      = 0
            notes_parts = []

        n_carry    = len(prev_carry_over_list)
        n_resolved = len(prev_resolved_list)

        month_results.append(PMYearMatrixMonth(
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

    return PMYearMatrix(year=year, months=month_results)


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/sync", summary="從 Ragic 同步週期保養資料（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_periodic_maintenance(background_tasks: BackgroundTasks):
    """手動觸發：Ragic Sheet 11 → SQLite（2026-07-14 起，Sheet 6+8 已停用），立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"status": "ok", "message": "同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches", summary="取得保養批次清單")
def list_batches(
    year:   Optional[str] = Query(None, description="篩選年份，如 2026"),
    db:     Session = Depends(get_db),
):
    q = db.query(PeriodicMaintenanceBatch)
    if year:
        q = q.filter(PeriodicMaintenanceBatch.period_month.like(f"{year}%"))
    batches = q.order_by(PeriodicMaintenanceBatch.period_month.desc()).all()

    ragic_server  = getattr(settings, "RAGIC_PM_SERVER_URL", "ap12.ragic.com")
    ragic_account = "soutlet001"

    result = []
    for b in batches:
        items = db.query(PeriodicMaintenanceItem).filter(
            PeriodicMaintenanceItem.batch_ragic_id == b.ragic_id
        ).all()
        check_month = _get_check_month(b.period_month)
        kpi = _calc_kpi(items, check_month)
        batch_dict = PMBatchOut.model_validate(b).model_dump()
        # 2026-07-14 起：Sheet 6 已退役，批次沒有獨立 Ragic 記錄，「在 Ragic 查看」
        # 改連到 Sheet 11 這個 Tab 本身（不含記錄 ID）。
        batch_dict["ragic_url"] = (
            f"https://{ragic_server}/{ragic_account}/periodic-maintenance/11"
        )
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
    batch_id:          str,
    current_month_only: bool = Query(False, description="只回傳本月有效項目"),
    category:          Optional[str] = Query(None),
    status_filter:     Optional[str] = Query(None, alias="status"),
    db:                Session = Depends(get_db),
):
    batch = db.get(PeriodicMaintenanceBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    items = db.query(PeriodicMaintenanceItem).filter(
        PeriodicMaintenanceItem.batch_ragic_id == batch_id
    ).order_by(PeriodicMaintenanceItem.seq_no).all()

    check_month = _get_check_month(batch.period_month)
    kpi = _calc_kpi(items, check_month)
    cats = _calc_category_stats(items, check_month)

    # 套用篩選
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

    return PMBatchDetail(
        batch      = PMBatchOut.model_validate(batch),
        kpi        = kpi,
        items      = filtered,
        categories = cats,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches/{batch_id}/kpi
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches/{batch_id}/kpi", summary="取得批次 KPI 統計")
def get_batch_kpi(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(PeriodicMaintenanceBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    items = db.query(PeriodicMaintenanceItem).filter(
        PeriodicMaintenanceItem.batch_ragic_id == batch_id
    ).all()
    check_month = _get_check_month(batch.period_month)
    return _calc_kpi(items, check_month)


# ══════════════════════════════════════════════════════════════════════════════
# GET /items  — 跨批次查詢
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/items", summary="跨批次查詢保養項目")
def list_items(
    batch_id:  Optional[str] = Query(None),
    category:  Optional[str] = Query(None),
    status:    Optional[str] = Query(None),
    month:     Optional[int] = Query(None, ge=1, le=12),
    db:        Session = Depends(get_db),
):
    q = db.query(PeriodicMaintenanceItem)
    if batch_id:
        q = q.filter(PeriodicMaintenanceItem.batch_ragic_id == batch_id)
    if category:
        q = q.filter(PeriodicMaintenanceItem.category == category)
    items = q.order_by(
        PeriodicMaintenanceItem.batch_ragic_id,
        PeriodicMaintenanceItem.seq_no,
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
@router.get("/stats", summary="全站統計（Dashboard 資料來源）", response_model=PMStats)
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

    # 目標年月批次
    current_batch = db.query(PeriodicMaintenanceBatch).filter(
        PeriodicMaintenanceBatch.period_month == target_ym
    ).first()

    # 若無指定篩選且找不到批次，退而取最新批次
    if not current_batch and not (year or month):
        current_batch = db.query(PeriodicMaintenanceBatch).order_by(
            PeriodicMaintenanceBatch.period_month.desc()
        ).first()

    current_kpi = None
    overdue_items: list[PMItemOut] = []
    upcoming_items: list[PMItemOut] = []
    cats: list[CategoryStat] = []
    status_dist: list[StatusDistItem] = []

    if current_batch:
        items = db.query(PeriodicMaintenanceItem).filter(
            PeriodicMaintenanceItem.batch_ragic_id == current_batch.ragic_id
        ).order_by(PeriodicMaintenanceItem.seq_no).all()

        current_kpi = _calc_kpi(items, check_month)
        cats = _calc_category_stats(items, check_month)

        # 逾期項目（最多 10 筆）
        overdue_items = [
            _item_to_out(it, check_month)
            for it in items
            if _calc_status(it, check_month) == "overdue"
        ][:10]

        # 即將到期清單：
        #   - 本月：顯示本週 7 天內已排定項目
        #   - 其他月：顯示該批次所有已排定項目（最多 10 筆）
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

        # 狀態分布
        # 規則：
        #   - 非本月 且 啟+迄均有值 → 歸入「已完成」（與 KPI 已完成定義一致）
        #   - 非本月 且 無完成時間 → 不顯示（對圓餅無意義）
        #   - 其他狀態 → 依 _calc_status 結果
        from collections import Counter
        def _dist_status(it: PeriodicMaintenanceItem) -> str | None:
            s = _calc_status(it, check_month)
            if s == "non_current_month":
                return "completed" if (it.start_time and it.end_time) else None
            return s

        status_counts = Counter(
            s for it in items
            if (s := _dist_status(it)) is not None
        )
        for s, cnt in status_counts.items():
            status_dist.append(StatusDistItem(
                status=s,
                label=STATUS_LABELS.get(s, s),
                count=cnt,
                color=STATUS_COLORS.get(s, "#666666"),
            ))

    return PMStats(
        current_batch       = PMBatchOut.model_validate(current_batch) if current_batch else None,
        current_kpi         = current_kpi,
        overdue_items       = overdue_items,
        upcoming_items      = upcoming_items,
        category_stats      = cats,
        status_distribution = status_dist,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats/year-matrix  — 全年 12 個月矩陣統計
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats/year-matrix", summary="全年 12 個月矩陣統計", response_model=PMYearMatrix)
def get_period_stats_year_matrix(
    year:           Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly；None = 全部頻率"),
    db:             Session = Depends(get_db),
):
    """
    一次回傳指定年份全部 12 個月的統計矩陣。
    frequency_type 可依頻率分類過濾（monthly/quarterly/yearly）。
    前端以「月份為欄、指標為列」的表格呈現。
    """
    target_year = year or date.today().year
    return _calc_year_matrix(db, target_year, frequency_type)


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats/year-matrix/items  — 矩陣格明細（數字點擊用）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats/year-matrix/items", summary="矩陣格明細查詢（數字點擊）")
def get_year_matrix_items(
    year:           int           = Query(..., description="年份，如 2026"),
    month:          int           = Query(..., ge=1, le=12, description="月份 1-12；合計欄傳 0 查全年"),
    metric:         str           = Query(..., description="prev_carry_over | prev_resolved | period_total | period_completed"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly；None = 全部"),
    db:             Session = Depends(get_db),
):
    """
    點擊年度矩陣表格中的數字時，回傳對應明細列表。
    metric:
      prev_carry_over    → 上月截止仍未完成的項目
      prev_resolved      → 上月未完成、於本月結案的項目
      period_total       → 本月應保養項目
      period_completed   → 本月已完成項目
    month = 0 → 全年（合計欄）
    """
    # 決定時間範圍
    if month == 0:
        # 全年合計：使用整年區間
        p_start  = date(year, 1, 1)
        p_end    = date(year, 12, 31)
        prev_end = date(year - 1, 12, 31)
    else:
        p_start, p_end, prev_end = _get_period_bounds("month", year, month=month)

    # 一次撈出指定年份的有效 item+batch（不依賴 scheduled_date）
    rows = (
        db.query(PeriodicMaintenanceItem, PeriodicMaintenanceBatch)
        .join(PeriodicMaintenanceBatch,
              PeriodicMaintenanceItem.batch_ragic_id == PeriodicMaintenanceBatch.ragic_id)
        .filter(PeriodicMaintenanceBatch.period_month.like(f"{year}/%"))
        .all()
    )

    prev_carry_over_list: list[dict] = []
    period_items_list:    list[dict] = []

    for item, batch in rows:
        if not _freq_match(item.frequency, frequency_type):
            continue
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []
        batch_year_num  = int(batch.period_month.split("/")[0])
        batch_month_num = int(batch.period_month.split("/")[1])
        if exec_months and batch_month_num not in exec_months:
            continue
        # full_date = 批次月份 1 日（不依賴 scheduled_date）
        full_date = date(batch_year_num, batch_month_num, 1)
        end_date = _parse_end_date(item.end_time)
        is_done  = bool(item.start_time and item.end_time)
        entry = {"item": item, "batch": batch, "full_date": full_date,
                 "end_date": end_date, "is_done": is_done,
                 "full_date_str": full_date.strftime("%Y/%m/%d")}

        if full_date <= prev_end:
            done_before = is_done and end_date is not None and end_date <= prev_end
            if not done_before:
                prev_carry_over_list.append(entry)

        if p_start <= full_date <= p_end:
            period_items_list.append(entry)

    # 依 metric 選擇對應集合
    if metric == "prev_carry_over":
        target = prev_carry_over_list
    elif metric == "prev_resolved":
        target = [x for x in prev_carry_over_list
                  if x["end_date"] is not None and p_start <= x["end_date"] <= p_end]
    elif metric == "period_completed":
        target = [x for x in period_items_list if x["is_done"]]
    else:  # period_total
        target = period_items_list

    # 組裝回傳格式（明細清單）
    ragic_server = getattr(settings, "RAGIC_PM_SERVER_URL", "ap12.ragic.com")
    ragic_account = "soutlet001"
    result = []
    for e in target:
        it: PeriodicMaintenanceItem = e["item"]
        b:  PeriodicMaintenanceBatch = e["batch"]
        # 排定日期：優先使用 Ragic 填寫的 scheduled_date，否則顯示批次月份
        sched_display = it.scheduled_date or b.period_month
        # 狀態（中文，對應前端 Tag 顯示）
        is_done = e["is_done"]
        full_d  = e["full_date"]
        if is_done:
            status_zh = "已完成"
        elif it.start_time:
            status_zh = "進行中"
        elif full_d < date.today():
            status_zh = "逾期"
        elif it.scheduled_date:
            status_zh = "已排程"
        else:
            status_zh = "待排程"
        # 2026-07-14 起：項目改用 Sheet 11 自己的 _ragicId 直連（不再連回批次 Sheet 8 記錄）
        ragic_link = f"https://{ragic_server}/{ragic_account}/periodic-maintenance/11/{it.ragic_id}"
        result.append({
            "ragic_id":            it.ragic_id,
            "batch_ragic_id":      it.batch_ragic_id,
            "period_month":        b.period_month,
            "category":            it.category,
            "task_name":           it.task_name,
            "frequency":           it.frequency,
            "scheduled_date_full": sched_display,
            "end_time":            it.end_time,
            "status":              status_zh,
            "executor_name":       it.executor_name,
            "result_note":         it.result_note,
            "abnormal_flag":       it.abnormal_flag,
            "abnormal_note":       it.abnormal_note,
            "ragic_link":          ragic_link,
        })

    return {"total": len(result), "items": result}


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats  — 週期統計（月 / 季 / 年）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats", summary="週期統計（月/季/年）", response_model=PMPeriodStats)
def get_period_stats(
    period_type:    str           = Query("month", description="month | quarter | year"),
    year:           Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    month:          Optional[int] = Query(None, ge=1, le=12, description="月份（period_type=month 時使用）"),
    quarter:        Optional[int] = Query(None, ge=1, le=4,  description="季度 1-4（period_type=quarter 時使用）"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly；None = 全部頻率"),
    db:             Session = Depends(get_db),
):
    """
    共用週期統計端點。

    - **period_type=month**   → 指定 year + month（預設當月）
    - **period_type=quarter** → 指定 year + quarter（預設當季）
    - **period_type=year**    → 指定 year（預設今年）

    回傳統計指標：
      - 上期累計未完成數 / 本期結案數 / 累計完成率
      - 本期項目數 / 本期完成數 / 本期完成率
      - 子期間分布（季→月、年→Q1-Q4、月→空）
      - 未完成事項說明（僅含有備註的項目）
    """
    today = date.today()
    target_year = year or today.year

    if period_type not in ("month", "quarter", "year"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="period_type 須為 month | quarter | year")

    p_start, p_end, prev_end = _get_period_bounds(period_type, target_year, month, quarter)

    # 組 period_label
    if period_type == "month":
        m = month or today.month
        period_label = f"{target_year}年{m}月"
    elif period_type == "quarter":
        q = quarter or ((today.month - 1) // 3 + 1)
        period_label = f"{target_year} Q{q}"
    else:
        period_label = f"{target_year}年"

    # 核心計算
    core = _calc_period_stats_core(db, p_start, p_end, prev_end, frequency_type)
    period_items_list = core.pop("period_items_list")

    # 子期間分布
    breakdown = _calc_sub_breakdown(period_type, p_start, period_items_list)

    return PMPeriodStats(
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
# PATCH /items/{item_id}  — 已停用（Portal 不提供編輯功能，資料來源全部為 Ragic）
# ══════════════════════════════════════════════════════════════════════════════
# @router.patch("/items/{item_id}", summary="[已停用] Portal 回填")
# def update_item(...): ...


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/task-history — 依項目名稱查詢跨批次執行歷史
# ══════════════════════════════════════════════════════════════════════════════
def _offset_month(year: int, month: int, delta: int) -> tuple[int, int]:
    """月份偏移（delta 可為負）"""
    total = (year * 12 + (month - 1)) + delta
    return total // 12, (total % 12) + 1


@router.get("/items/task-history", summary="依保養項目名稱查詢近 N 個月執行歷史")
def get_item_task_history(
    task_name: str = Query(..., description="保養項目名稱（完整比對）"),
    months:    int = Query(12, ge=1, le=24, description="查詢最近幾個月"),
    db:        Session = Depends(get_db),
):
    """
    依 task_name 跨批次查詢該保養項目近 N 個月的執行狀態。
    用於「保養項目點擊 → 過往歷史 Drawer」。
    """
    today = date.today()

    # 查詢所有 task_name 相符的 items + 對應 batch
    rows = (
        db.query(PeriodicMaintenanceItem, PeriodicMaintenanceBatch)
        .join(
            PeriodicMaintenanceBatch,
            PeriodicMaintenanceItem.batch_ragic_id == PeriodicMaintenanceBatch.ragic_id,
        )
        .filter(PeriodicMaintenanceItem.task_name == task_name)
        .order_by(PeriodicMaintenanceBatch.period_month.desc())
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"找不到保養項目：{task_name}")

    # 取得第一筆的基本資訊（category / frequency / exec_months_raw）
    first_item: PeriodicMaintenanceItem = rows[0][0]

    # 建立 period_month → (item, batch) 的映射
    month_map: dict[str, tuple] = {}
    for item, batch in rows:
        month_map[batch.period_month] = (item, batch)

    # 計算近 N 個月月曆摘要
    monthly_summary = []
    for i in range(months - 1, -1, -1):
        y, m = _offset_month(today.year, today.month, -i)
        period_month = f"{y}/{m:02d}"
        is_current = (y == today.year and m == today.month)

        if period_month in month_map:
            item, _batch = month_map[period_month]
            item_status = _calc_status(item, m)
            monthly_summary.append({
                "period_month":  period_month,
                "status":        item_status,
                "has_record":    True,
                "executor_name": item.executor_name or "",
                "scheduled_date": item.scheduled_date or "",
                "start_time":    item.start_time or "",
                "end_time":      item.end_time or "",
                "result_note":   item.result_note or "",
                "abnormal_flag": bool(item.abnormal_flag),
                "abnormal_note": item.abnormal_note or "",
                "is_current":    is_current,
            })
        else:
            monthly_summary.append({
                "period_month":  period_month,
                "status":        "unscheduled" if is_current else "no_batch",
                "has_record":    False,
                "executor_name": "",
                "scheduled_date": "",
                "start_time":    "",
                "end_time":      "",
                "result_note":   "",
                "abnormal_flag": False,
                "abnormal_note": "",
                "is_current":    is_current,
            })

    # 統計
    completed_months = sum(1 for ms in monthly_summary if ms["status"] == "completed")
    abnormal_count   = sum(1 for ms in monthly_summary if ms["abnormal_flag"])

    return {
        "task_name":      task_name,
        "category":       first_item.category or "",
        "frequency":      first_item.frequency or "",
        "exec_months_raw": first_item.exec_months_raw or "",
        "monthly_summary": monthly_summary,
        "stats": {
            "total_months":     months,
            "completed_months": completed_months,
            "abnormal_count":   abnormal_count,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/{item_ragic_id}/worklogs（2026-07-14 同日追加：Sheet 11 巢狀「維修記錄」
# 子表格明細，原始遷移評估誤判無此結構，使用者實測記錄 277/477 證實存在，比照
# mall_periodic_maintenance 2026-07-13 同型端點）
# ══════════════════════════════════════════════════════════════════════════════
class PMWorklogOut(BaseModel):
    ragic_id:      str
    item_ragic_id: str
    seq_no:        int
    repair_note:   str
    start_time:    str
    end_time:      str
    staff_name:    str

    class Config:
        from_attributes = True


@router.get(
    "/items/{item_ragic_id}/worklogs",
    response_model=List[PMWorklogOut],
    summary="單一項目維修記錄明細（來源 Ragic Sheet11 巢狀子表格）",
)
def get_item_worklogs(item_ragic_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(PeriodicMaintenanceItemWorklog)
        .filter(PeriodicMaintenanceItemWorklog.item_ragic_id == item_ragic_id)
        .order_by(PeriodicMaintenanceItemWorklog.seq_no.asc())
        .all()
    )
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/{item_ragic_id}/db-images（2026-07-14 新增：Sheet 11「圖片上傳」欄位，
# 遵循全站「明細 Drawer 強制規範」的 /db-images/{ragic_id} 端點慣例，比照
# mall_periodic_maintenance 2026-07-13 同型端點）
# ══════════════════════════════════════════════════════════════════════════════
class PMImageOut(BaseModel):
    url:      str
    filename: str


@router.get(
    "/items/{item_ragic_id}/db-images",
    response_model=List[PMImageOut],
    summary="單一項目附圖（DB 優先，缺資料時即時向 Ragic 補抓一次，來源 Sheet11「圖片上傳」欄位）",
)
async def get_item_images(item_ragic_id: str, db: Session = Depends(get_db)):
    item = await run_in_threadpool(db.get, PeriodicMaintenanceItem, item_ragic_id)
    if item and item.images_json:
        try:
            cached = json.loads(item.images_json)
            if cached:
                return cached
        except Exception:
            pass

    # DB 沒資料（尚未同步過此欄位，或該筆項目本來就沒附圖）→ 即時向 Ragic 補抓一次；
    # 不寫回 DB，下次排程同步時會自然補齊。
    from app.services.periodic_maintenance_sync import (
        PM_SERVER_URL, PM_ACCOUNT, PM_SHEET11_PATH, CK11_IMAGES,
    )
    from app.services.ragic_data_service import parse_images

    adapter = RagicAdapter(
        sheet_path=PM_SHEET11_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )
    try:
        full_record = await adapter.fetch_one(item_ragic_id)
        if item_ragic_id in full_record and len(full_record) == 1:
            full_record = full_record[item_ragic_id]
        images = parse_images(
            full_record.get(CK11_IMAGES),
            server=PM_SERVER_URL,
            account=PM_ACCOUNT,
        )
        return images
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# GET /debug/ragic-raw  — 除錯用：直接回傳 Ragic 原始資料
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/debug/ragic-raw", summary="[除錯] 顯示 Ragic Sheet 11 原始欄位 key（含舊 Sheet 6 供比對）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_ragic_raw():
    """
    直接向 Ragic 拉取 Sheet 11（2026-07-14 起主要來源），回傳原始 dict 的欄位名稱
    與第一筆值。同時保留拉取舊 Sheet 6/8 供比對（Sheet 6/8 已停用，不再影響同步，
    僅供除錯／確認退役後資料狀態使用）。
    """
    from app.services.periodic_maintenance_sync import (
        PM_SERVER_URL, PM_ACCOUNT, PM_SHEET11_PATH, PM_ITEMS_PATH, PM_JOURNAL_PATH,
    )

    adapter_sheet11 = RagicAdapter(
        sheet_path=PM_SHEET11_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )
    adapter_items_legacy = RagicAdapter(
        sheet_path=PM_ITEMS_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )
    adapter_batch_legacy = RagicAdapter(
        sheet_path=PM_JOURNAL_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )

    try:
        raw_sheet11 = await adapter_sheet11.fetch_all()
    except Exception as exc:
        raw_sheet11 = {}
        sheet11_error = str(exc)
    else:
        sheet11_error = None

    try:
        raw_items_legacy = await adapter_items_legacy.fetch_all()
        raw_batch_legacy = await adapter_batch_legacy.fetch_all()
    except Exception as exc:
        return {
            "sheet11": {"error": sheet11_error} if sheet11_error else {
                "total_records": len(raw_sheet11),
                "record_ids": list(raw_sheet11.keys()),
                "first_record_fields": next(iter(raw_sheet11.values()), {}) if raw_sheet11 else {},
            },
            "legacy_sheet6_sheet8_error": str(exc),
        }

    first_sheet11 = next(iter(raw_sheet11.values()), {}) if raw_sheet11 else {}
    first_item_legacy = next(iter(raw_items_legacy.values()), {}) if raw_items_legacy else {}
    first_batch_legacy = next(iter(raw_batch_legacy.values()), {}) if raw_batch_legacy else {}

    return {
        "sheet11": {
            "error": sheet11_error,
            "total_records": len(raw_sheet11),
            "record_ids": list(raw_sheet11.keys()),
            "first_record_fields": first_sheet11,
        },
        "legacy_sheet8_items": {
            "total_records": len(raw_items_legacy),
            "record_ids": list(raw_items_legacy.keys()),
            "first_record_fields": first_item_legacy,
        },
        "legacy_sheet6_batch": {
            "total_records": len(raw_batch_legacy),
            "record_ids": list(raw_batch_legacy.keys()),
            "first_record_fields": first_batch_legacy,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# GET /calendar  — Dashboard 月曆格（類別 × 日期）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/calendar", summary="週期保養月曆格（依類別 × 日期）")
def get_pm_calendar(
    year:  int = Query(..., ge=2020, le=2099, description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份，如 5"),
    db:    Session = Depends(get_db),
):
    """
    回傳指定年月的「類別 × 日期」月曆格資料。

    - rows：固定類別順序（水電 / 空調 / 機修 / 裝修 / 弱電 / 其他）
    - daily：key = "1" ~ "31"，value = { has_record, completion_rate, abnormal_count, pending_count }
      - has_record       = 該日該類別有排定保養項目
      - completion_rate  = round(completed / total * 100)
      - abnormal_count   = 逾期項目數（scheduled_date 已過且未完成）
      - pending_count    = 進行中項目數

    cell 格式與 hotel/daily-inspection GET /daily-calendar 一致，
    可直接傳入 MonthlyCalendarGrid 元件。
    """
    from calendar import monthrange

    _, max_day = monthrange(year, month)
    target_period_month = f"{year}/{month:02d}"
    today = date.today()

    # 取得當月所有 batch + 跨月 batch（scheduled_date 月份可能與 period_month 不同）
    batches = (
        db.query(PeriodicMaintenanceBatch)
        .filter(PeriodicMaintenanceBatch.period_month == target_period_month)
        .all()
    )

    # 固定類別順序；額外類別歸入「其他」
    CATEGORIES = ["水電", "空調", "機修", "裝修", "弱電"]

    # cat → day → {total, completed, in_progress, overdue}
    grid: dict[str, dict[int, dict[str, int]]] = {
        cat: {d: {"total": 0, "completed": 0, "in_progress": 0, "overdue": 0}
              for d in range(1, max_day + 1)}
        for cat in CATEGORIES + ["其他"]
    }

    for batch in batches:
        items = db.query(PeriodicMaintenanceItem).filter(
            PeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id
        ).all()
        check_month = _get_check_month(batch.period_month)

        for it in items:
            if not it.scheduled_date:
                continue
            full_date = _reconstruct_full_date(it.scheduled_date, batch.period_month)
            if not full_date:
                continue
            # 只取落在目標 year/month 的項目
            if full_date.year != year or full_date.month != month:
                continue

            day = full_date.day
            cat = it.category or "其他"
            if cat not in CATEGORIES:
                cat = "其他"

            grid[cat][day]["total"] += 1
            status = _calc_status(it, check_month)
            if status == "completed":
                grid[cat][day]["completed"] += 1
            elif status == "in_progress":
                grid[cat][day]["in_progress"] += 1
            elif status == "overdue":
                grid[cat][day]["overdue"] += 1

    # 組裝回傳格式
    rows_out = []
    for cat in CATEGORIES + ["其他"]:
        daily_out: dict[str, dict] = {}
        has_any = False
        for d in range(1, max_day + 1):
            cell        = grid[cat][d]
            total       = cell["total"]
            completed   = cell["completed"]
            in_progress = cell["in_progress"]
            overdue     = cell["overdue"]
            if total > 0:
                has_any = True
            rate = round(completed / total * 100) if total > 0 else 0
            daily_out[str(d)] = {
                "has_record":      total > 0,
                "completion_rate": rate,
                "abnormal_count":  overdue,
                "pending_count":   in_progress,
            }
        if has_any or cat in CATEGORIES:
            rows_out.append({
                "key":   cat,
                "label": cat,
                "daily": daily_out,
            })

    return {
        "year":    year,
        "month":   month,
        "max_day": max_day,
        "rows":    rows_out,
    }


# ── 保養項目目錄（依頻率分類）──────────────────────────────────────────────────
@router.get("/items/catalog")
def get_items_catalog(
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    取得保養項目目錄（不分批次），依 frequency_type 篩選。
    結果為去重後的保養項目列表，以最新一筆批次的資料為準。
    回傳欄位：seq_no, category, frequency, task_name, location,
              estimated_minutes, exec_months_raw
    """
    from sqlalchemy import func as sqlfunc

    # 先找每個 (task_name, category, frequency) 最新的 ragic_id
    subq = (
        db.query(
            PeriodicMaintenanceItem.task_name,
            PeriodicMaintenanceItem.category,
            PeriodicMaintenanceItem.frequency,
            sqlfunc.max(PeriodicMaintenanceItem.seq_no).label("max_seq"),
        )
        .group_by(
            PeriodicMaintenanceItem.task_name,
            PeriodicMaintenanceItem.category,
            PeriodicMaintenanceItem.frequency,
        )
        .subquery()
    )

    rows = (
        db.query(PeriodicMaintenanceItem)
        .join(
            subq,
            (PeriodicMaintenanceItem.task_name     == subq.c.task_name)
            & (PeriodicMaintenanceItem.category    == subq.c.category)
            & (PeriodicMaintenanceItem.frequency   == subq.c.frequency)
            & (PeriodicMaintenanceItem.seq_no      == subq.c.max_seq),
        )
        .order_by(PeriodicMaintenanceItem.category, PeriodicMaintenanceItem.seq_no)
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
# 排程管理（pm_schedule）相關 Endpoints
# ══════════════════════════════════════════════════════════════════════════════

def _get_latest_batch_items(db: Session) -> list[PeriodicMaintenanceItem]:
    """取得最新批次的所有保養項目，作為主檔來源。

    2026-07-14 修正：原本只用 `ORDER BY period_month DESC .first()` 取「最新批次」，
    但 Sheet 6 → Sheet 11 遷移過程中，同一個 period_month 可能同時存在多筆 pm_batch
    記錄（例如舊 Sheet6 批次與遷移後依「編號」比對到的批次併存，其中一筆是沒有任何
    pm_batch_item 掛在底下的空殼批次）。實測發現 2026/07 同時有 batch_ragic_id=9
    （65 筆項目，含測試記錄 477）與 batch_ragic_id=11（0 筆項目）兩筆記錄，`.first()`
    在沒有明確 tiebreak 的情況下可能挑到空殼批次，導致整個「最新批次」變成空清單——
    連帶讓年度計劃表、KPI、period-stats、目錄等所有依賴本函式的功能全部顯示 0 筆。
    修正：同一個最新 period_month 若有多筆批次記錄，改為挑「實際掛有項目」的那一筆
    （多筆都有項目時取第一筆，維持原行為）。
    """
    from sqlalchemy import func as sqlfunc

    latest_period = (
        db.query(sqlfunc.max(PeriodicMaintenanceBatch.period_month))
        .scalar()
    )
    if not latest_period:
        return []
    candidate_batches = (
        db.query(PeriodicMaintenanceBatch)
        .filter(PeriodicMaintenanceBatch.period_month == latest_period)
        .all()
    )
    for batch in candidate_batches:
        items = (
            db.query(PeriodicMaintenanceItem)
            .filter(PeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id)
            .order_by(PeriodicMaintenanceItem.seq_no)
            .all()
        )
        if items:
            return items
    return []


def _calc_schedule_status(rec: PMSchedule) -> str:
    """計算 pm_schedule 記錄的狀態。"""
    if rec.is_completed or (rec.start_time and rec.end_time):
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


def _schedule_to_out(rec: PMSchedule) -> PMScheduleOut:
    """ORM → Pydantic，動態注入 status。"""
    return PMScheduleOut(
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
        is_completed     = rec.is_completed or bool(rec.start_time and rec.end_time),
        result_note      = rec.result_note,
        abnormal_flag    = rec.abnormal_flag,
        abnormal_note    = rec.abnormal_note,
        portal_edited_at = rec.portal_edited_at,
        created_at       = rec.created_at,
        updated_at       = rec.updated_at,
        status           = _calc_schedule_status(rec),
    )


# ── 排程產生核心邏輯（供 endpoint 與 scheduler / lazy auto-generate 共用）──────

def _do_generate_hotel_periodic_pm(
    year: int, month: int, db: Session
) -> PMScheduleGenerateResult:
    """
    為 year/month 產生 PMSchedule 記錄。
    來源優先順序：
      1. 該月已有實際 Ragic 批次資料（target_batch 存在）→ 直接以批次內的真實項目為準，
         全部產生排程（不再套用 _should_schedule 頻率公式反推）。
         原因：年/季頻率項目在不同月份的批次是彼此不同的項目集合，若仍用「最新批次」
         的項目定義 + 頻率公式去判斷「這個月該不該排」，會漏掉批次裡實際存在、但
         公式判斷不到的項目（例如 exec_months 落在最新批次沒有涵蓋的月份），導致
         產生的 pm_schedule 筆數少於 Ragic 實際筆數。
      2. 該月尚無批次資料（例如未來月份尚未同步）→ 退回用「最新批次」的項目定義
         套用 _should_schedule 頻率公式推算（沿用原本邏輯，僅作為預先排程的估算）。
    冪等保護：
      - is_completed=True / start+end 均有  → 跳過
      - portal_edited_at IS NOT NULL         → 跳過
      - 其他已存在記錄                        → 更新 scheduled_date / executor_name
        （use_actual_batch 時一併帶入 start_time/end_time/is_completed/result_note/
        abnormal_flag/abnormal_note，2026-07-14 修正，比照 mall_pm 同型修正——見下方
        迴圈內註解。原本這些欄位從未被寫回 pm_schedule，導致 Sheet11 同步後已完成的
        項目，年度計劃表仍顯示未完成，因為矩陣格狀態只看 pm_schedule 記錄本身）
    """
    year_month = f"{year}/{month:02d}"

    target_batch = (
        db.query(PeriodicMaintenanceBatch)
        .filter(PeriodicMaintenanceBatch.period_month == year_month)
        .first()
    )
    month_sched_lookup: dict[tuple, str] = {}
    use_actual_batch = False
    if target_batch:
        target_items = (
            db.query(PeriodicMaintenanceItem)
            .filter(PeriodicMaintenanceItem.batch_ragic_id == target_batch.ragic_id)
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
            month_sched_lookup[(ti.task_name.strip(), ti.category.strip(), ti.location.strip())] = mmdd
        # 該月已有實際批次資料 → 以批次內的真實項目為準（取代最新批次 + 頻率公式）
        items = target_items
        use_actual_batch = True
    else:
        items = _get_latest_batch_items(db)

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

            # 已有該月真實批次資料時，批次內的項目即代表「本來就該在這個月執行」，
            # 不再套用 _should_schedule 頻率公式（該公式只適用於「尚無真實資料、需要
            # 用最新批次推算未來月份」的情境）。
            if not use_actual_batch and not _should_schedule(item, year, month):
                skipped_non_month += 1
                continue

            existing = (
                db.query(PMSchedule)
                .filter(
                    PMSchedule.year_month    == year_month,
                    PMSchedule.item_ragic_id == item.ragic_id,
                )
                .first()
            )

            if existing:
                if existing.is_completed or (existing.start_time and existing.end_time):
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
                # 2026-07-14 修正（比照 mall_pm 2026-07-13 同型修正，見
                # generate_mall_schedule() 頂部說明）：帶入 Ragic 同步回來的完成狀態。
                # 原本這裡從未寫入 start_time/end_time/is_completed，導致 Sheet11 同步
                # 已把某筆項目標記完成後，若 pm_schedule 之前就已有該月的記錄（例如更早
                # 已產生過排程），年度計劃表會一直顯示舊狀態（未完成/逾期），因為矩陣格
                # 狀態只看 pm_schedule 本身，不會回頭比對 pm_batch_item 的最新完成狀態。
                # 只在 use_actual_batch（該月已有真實 Ragic 批次資料，items 就是這個月
                # 自己的批次項目）時才帶入，避免用「最新批次」的資料誤蓋到其他月份。
                if use_actual_batch:
                    existing.start_time    = item.start_time
                    existing.end_time      = item.end_time
                    existing.is_completed  = item.is_completed
                    existing.result_note   = item.result_note
                    existing.abnormal_flag = item.abnormal_flag
                    existing.abnormal_note = item.abnormal_note
                existing.updated_at        = datetime.now()
                updated += 1
            else:
                key = (item.task_name.strip(), item.category.strip(), item.location.strip())
                resolved_date = month_sched_lookup.get(key) or item.scheduled_date or ""
                new_rec = PMSchedule(
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
                    # 同上：新建記錄時，若該月已有真實批次資料也一併帶入 item 已知的完成狀態
                    start_time    = item.start_time    if use_actual_batch else "",
                    end_time      = item.end_time      if use_actual_batch else "",
                    is_completed  = item.is_completed  if use_actual_batch else False,
                    result_note   = item.result_note   if use_actual_batch else "",
                    abnormal_flag = item.abnormal_flag if use_actual_batch else False,
                    abnormal_note = item.abnormal_note if use_actual_batch else "",
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

    return PMScheduleGenerateResult(
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

@router.post("/schedule/generate", summary="產生指定月份保養排程（防重複）",
             response_model=PMScheduleGenerateResult)
def generate_schedule(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    db:    Session = Depends(get_db),
):
    return _do_generate_hotel_periodic_pm(year, month, db)


# ── GET /schedule ─────────────────────────────────────────────────────────────

@router.get("/schedule", summary="查詢排程明細列表")
def list_schedule(
    year_month: Optional[str] = Query(None, description="月份，如 2026/05；預設為本月"),
    category:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    db:         Session = Depends(get_db),
):
    if not year_month:
        today = date.today()
        year_month = f"{today.year}/{today.month:02d}"

    q = db.query(PMSchedule).filter(PMSchedule.year_month == year_month)
    if category:
        q = q.filter(PMSchedule.category == category)

    records   = q.order_by(PMSchedule.category, PMSchedule.task_name).all()
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

@router.get("/schedule/kpi", summary="排程 KPI 統計", response_model=PMScheduleKPI)
def get_schedule_kpi(
    year_month: Optional[str] = Query(None, description="月份，如 2026/05；預設本月"),
    db:         Session = Depends(get_db),
):
    if not year_month:
        today = date.today()
        year_month = f"{today.year}/{today.month:02d}"

    records   = db.query(PMSchedule).filter(PMSchedule.year_month == year_month).all()
    items_out = [_schedule_to_out(r) for r in records]

    total       = len(items_out)
    completed   = sum(1 for i in items_out if i.status == "completed")

    all_items    = _get_latest_batch_items(db)
    year_i       = int(year_month.split("/")[0])
    month_i      = int(year_month.split("/")[1])
    existing_ids = {r.item_ragic_id for r in records}
    should_do_not_done = sum(
        1 for it in all_items
        if _should_schedule(it, year_i, month_i) and it.ragic_id not in existing_ids
    )

    return PMScheduleKPI(
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
        db.query(PMSchedule)
        .filter(PMSchedule.is_completed == False)
        .filter(PMSchedule.scheduled_date != "")
        .order_by(PMSchedule.year_month, PMSchedule.scheduled_date)
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


# ── PATCH /schedule/{id} ──────────────────────────────────────────────────────

@router.patch("/schedule/{schedule_id}", summary="人工調整排程明細")
def update_schedule(
    schedule_id: int,
    body:        PMScheduleUpdate,
    db:          Session = Depends(get_db),
):
    rec = db.get(PMSchedule, schedule_id)
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

@router.get("/schedule/annual-matrix", summary="年度計劃矩陣（12欄）",
            response_model=PMScheduleAnnualMatrix)
def get_annual_matrix(
    year:     int = Query(..., description="年份，如 2026"),
    category: Optional[str] = Query(None),
    db:       Session = Depends(get_db),
):
    all_items = _get_latest_batch_items(db)
    if category:
        all_items = [it for it in all_items if it.category == category]

    year_records = (
        db.query(PMSchedule)
        .filter(PMSchedule.year_month.like(f"{year}/%"))
        .all()
    )
    schedule_map: dict[tuple[str, int], PMSchedule] = {}
    for rec in year_records:
        try:
            m = int(rec.year_month.split("/")[1])
            schedule_map[(rec.item_ragic_id, m)] = rec
        except Exception:
            pass

    # 載入該年各月批次的排定日期：(月份) -> {(task_name, category, location) -> "MM/DD"}
    # 用於補回 pm_schedule.scheduled_date 為空時的排定日期（Ragic 已填但 pm_schedule 尚未更新）
    year_batches = (
        db.query(PeriodicMaintenanceBatch)
        .filter(PeriodicMaintenanceBatch.period_month.like(f"{year}/%"))
        .all()
    )
    month_sched_lookup: dict[int, dict[tuple, str]] = {}
    for batch in year_batches:
        try:
            bm = int(batch.period_month.split("/")[1])
        except Exception:
            continue
        batch_items = (
            db.query(PeriodicMaintenanceItem)
            .filter(PeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id)
            .all()
        )
        lookup: dict[tuple, str] = {}
        for bi in batch_items:
            if not bi.scheduled_date:
                continue
            # scheduled_date 可能是 "YYYY/MM/DD" 或 "MM/DD"；統一轉為 "MM/DD"
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

    rows: list[PMScheduleMatrixRow] = []
    completed_cnt = 0

    for item in all_items:
        cells: list[PMScheduleMatrixCell] = []
        for m in range(1, 13):
            rec = schedule_map.get((item.ragic_id, m))
            if rec:
                # 決定顯示用排定日期：pm_schedule > 批次 lookup > MM/01 預設
                key = (item.task_name.strip(), item.category.strip(), item.location.strip())
                display_date: Optional[str] = rec.scheduled_date or None
                if not display_date:
                    batch_mmdd = month_sched_lookup.get(m, {}).get(key)
                    if batch_mmdd:
                        rec.scheduled_date = batch_mmdd   # 記憶體更新，供 status 計算用
                        display_date = batch_mmdd
                    else:
                        display_date = f"{m:02d}/01"      # 無日期時顯示本月 1 號（status 不改）
                status = _calc_schedule_status(rec)
                if status == "completed":
                    completed_cnt += 1
                cells.append(PMScheduleMatrixCell(
                    month          = m,
                    status         = status,
                    schedule_id    = rec.id,
                    scheduled_date = display_date,
                ))
            else:
                freq = (item.frequency or "").strip()
                if not freq:
                    cell_status = "no_frequency"
                    cells.append(PMScheduleMatrixCell(month=m, status=cell_status, schedule_id=None))
                elif _should_schedule(item, year, m):
                    # 無 pm_schedule 記錄
                    # 排定日期優先順序：該月批次 lookup > MM/01 預設
                    key = (item.task_name.strip(), item.category.strip(), item.location.strip())
                    batch_mmdd = month_sched_lookup.get(m, {}).get(key)

                    if batch_mmdd:
                        # Ragic 已為此月設排定日期 → 推算真實狀態
                        cell_sched_date = batch_mmdd
                        if item.is_completed or (item.start_time and item.end_time):
                            cell_status = "completed"
                            completed_cnt += 1
                        elif item.start_time:
                            cell_status = "in_progress"
                        else:
                            try:
                                full_sched = datetime.strptime(
                                    f"{year}/{batch_mmdd}", "%Y/%m/%d"
                                ).date()
                                cell_status = "overdue" if full_sched < date.today() else "scheduled"
                            except Exception:
                                cell_status = "no_data"
                    else:
                        # 無排定日期 → 預設 MM/01，狀態仍為 no_data（應做未排）
                        cell_sched_date = f"{m:02d}/01"
                        cell_status = "no_data"

                    cells.append(PMScheduleMatrixCell(
                        month          = m,
                        status         = cell_status,
                        schedule_id    = None,
                        scheduled_date = cell_sched_date,
                    ))
                else:
                    cells.append(PMScheduleMatrixCell(month=m, status="non_month", schedule_id=None))

        rows.append(PMScheduleMatrixRow(
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
    # _do_generate_hotel_periodic_pm 為冪等，不會覆蓋已完成/人工調整的記錄。
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
                _do_generate_hotel_periodic_pm(year, m, db)
            except Exception as exc:
                print(f"[periodic_maintenance] lazy auto-generate {year}/{m:02d} failed: {exc}")

    return PMScheduleAnnualMatrix(
        year  = year,
        rows  = rows,
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
