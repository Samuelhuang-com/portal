"""
商場週期保養表 API Router
Prefix: /api/v1/mall/periodic-maintenance

端點：
  POST /sync                         — 手動從 Ragic 同步
  GET  /batches                      — 批次清單（年份篩選）
  GET  /batches/{batch_id}           — 單筆批次 + 所有項目 + KPI
  GET  /batches/{batch_id}/kpi       — 批次 KPI 統計
  GET  /items                        — 所有項目跨批次查詢
  GET  /stats                        — 全站統計（Dashboard 資料來源）
  GET  /items/task-history           — 依項目名稱查詢近 N 個月執行歷史
  GET  /items/{item_ragic_id}/worklogs — 單一項目維修記錄明細（Sheet24 巢狀子表格，2026-07-13 新增）
  GET  /items/{item_ragic_id}/db-images — 單一項目附圖（Sheet24「圖片上傳」欄位，2026-07-13 新增）
  GET  /debug/ragic-raw              — 除錯：顯示 Ragic Sheet 18 原始欄位
"""
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.mall_periodic_maintenance import (
    MallPeriodicMaintenanceBatch, MallPeriodicMaintenanceItem, MallPMItemWorklog,
)
from app.models.mall_pm_schedule import MallPMSchedule
from app.schemas.periodic_maintenance import (
    PMBatchOut, PMItemOut, PMBatchKPI, PMBatchDetail,
    CategoryStat, StatusDistItem, PMStats, PMItemUpdate,
    PMPeriodStats, PMSubPeriodBreakdown, PMIncompleteItem,
    PMYearMatrix, PMYearMatrixMonth,
)
from app.schemas.mall_periodic_maintenance import (
    MallPMScheduleOut, MallPMScheduleKPI, MallPMScheduleGenerateResult,
    MallPMScheduleUpdate, MallPMScheduleMatrixCell, MallPMScheduleMatrixRow,
    MallPMScheduleAnnualMatrix,
)
from app.services.mall_periodic_maintenance_sync import sync_from_ragic
from app.services.ragic_adapter import RagicAdapter
from app.core.config import settings

router = APIRouter(dependencies=[Depends(get_current_user)])

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
    return (frequency or "").strip() in keywords


def _infer_freq_type_from_exec_months(exec_months: list) -> Optional[str]:
    """
    當 frequency 欄位為空時，依 exec_months 數量推算頻率類型（規格書規定的 fallback）。
    10-12 個月 → monthly
    3-5  個月 → quarterly
    1-2  個月 → yearly
    其餘      → None（無法推算）
    """
    n = len(exec_months)
    if n >= 10:     return "monthly"
    if 3 <= n <= 5: return "quarterly"
    if 1 <= n <= 2: return "yearly"
    return None


def _freq_match_with_fallback(
    frequency: str,
    frequency_type: Optional[str],
    exec_months: list,
) -> bool:
    """
    同 _freq_match，但當 frequency 欄位為空時改用 exec_months 推算頻率類型。
    確保 exec_months 有數據的項目也能正確篩選到對應統計 TAB。
    """
    if not frequency_type:
        return True
    freq = (frequency or "").strip()
    if freq:
        keywords = _FREQ_KEYWORDS.get(frequency_type, set())
        return freq in keywords
    # frequency 為空 → 從 exec_months 數量推算
    inferred = _infer_freq_type_from_exec_months(exec_months)
    return inferred == frequency_type


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


def _calc_status(item: MallPeriodicMaintenanceItem, check_month: int) -> str:
    """
    依 Ragic 欄位值推導保養項目狀態（唯讀）。

    修正（2026-05）：月頻率項目 exec_months 為空是正常情況（每月執行不需列月份），
    應視為「本月適用」，不落入 unscheduled。
    """
    exec_months: list[int] = []
    try:
        exec_months = json.loads(item.exec_months_json or "[]")
    except Exception:
        pass

    # 非本月判斷：exec_months 有值 → 直接判斷；為空 + 頻率有值 → 依頻率公式
    if exec_months:
        if check_month not in exec_months:
            return "non_current_month"
    elif item.frequency:
        if not _should_schedule_by_frequency(item.frequency, check_month):
            return "non_current_month"

    if item.start_time and item.end_time:
        return "completed"
    if item.start_time:
        return "in_progress"
    if item.scheduled_date:
        try:
            today = date.today()
            fd = _reconstruct_full_date(item.scheduled_date, f"{today.year}/{today.month:02d}")
            if fd is None:
                raise ValueError
            scheduled = fd
            if scheduled < today:
                return "overdue"
        except Exception:
            pass
        return "scheduled"
    return "unscheduled"


# ── 排程邏輯輔助函式 ──────────────────────────────────────────────────────────

_FREQ_INTERVAL: dict[str, int] = {
    "月":   1,
    "雙月": 2,
    "季":   3,
    "半年": 6,
    "年":   12,
}


def _should_schedule_by_frequency(frequency: str, month: int) -> bool:
    """
    純依頻率字串與月份判斷「本月是否應產生排程」（exec_months 為空時使用）。
    月 → 永遠 True；其他 → (month - 1) % interval == 0（從 1 月起算）。
    """
    interval = _FREQ_INTERVAL.get(frequency.strip())
    if interval is None:
        return False
    if interval == 1:
        return True
    return (month - 1) % interval == 0


def _should_schedule(item: MallPeriodicMaintenanceItem, year: int, month: int) -> bool:
    """判斷指定 year/month 是否應為此項目產生排程。"""
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


_RAGIC_BASE = "https://ap12.ragic.com/soutlet001/periodic-maintenance/18"


def _item_to_out(item: MallPeriodicMaintenanceItem, check_month: int) -> PMItemOut:
    return PMItemOut(
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
        is_completed      = bool(item.start_time and item.end_time),
        result_note       = item.result_note,
        abnormal_flag     = item.abnormal_flag,
        abnormal_note     = item.abnormal_note,
        portal_edited_at  = item.portal_edited_at,
        synced_at         = item.synced_at,
        status            = _calc_status(item, check_month),
        ragic_url         = f"{_RAGIC_BASE}/{item.batch_ragic_id}" if item.batch_ragic_id else "",
        repair_hours      = item.repair_hours,
    )


def _calc_kpi(items: list[MallPeriodicMaintenanceItem], check_month: int) -> PMBatchKPI:
    statuses = [_calc_status(it, check_month) for it in items]
    current_items = [(it, s) for it, s in zip(items, statuses) if s != "non_current_month"]

    total_all   = len(items)
    completed   = sum(1 for it in items if it.start_time and it.end_time)
    in_progress = sum(1 for _, s in current_items if s == "in_progress")
    scheduled   = sum(1 for _, s in current_items if s == "scheduled")
    unscheduled = sum(1 for _, s in current_items if s == "unscheduled")
    overdue     = sum(1 for _, s in current_items if s == "overdue")
    # 2026-07-14 修正：abnormal 原本算「整批全部項目」，跟 overdue/scheduled/
    # unscheduled/in_progress 這幾個都只算「本月項目」（current_items）的口徑不一致；
    # 使用者確認後改為比照這幾個欄位，只算本月項目裡標記異常的筆數。
    abnormal    = sum(1 for it, _ in current_items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)
    # 2026-07-13 修正（比照 full_bldg_pm 同日改版）：repair_hours（來源 Sheet24「維修工時」）
    # 是 Ragic 端逐筆維修記錄實際工時的加總；start_time/end_time 則是 Portal 這邊從巢狀
    # 子表格「取最早開始、最晚結束」推算出來的時間跨度。同一保養項目若有多筆不連續的
    # 維修記錄，時間跨度會把中間的空檔也算進去，大幅高估實際工時。有 repair_hours 時
    # 一律以其為準，只有沒有 repair_hours（例如舊資料或極端情況）才退回時間跨度估算。
    actual = sum(
        (round(it.repair_hours * 60) if it.repair_hours is not None
         else _time_diff_minutes(it.start_time, it.end_time))
        for it in items if it.start_time and it.end_time
    )
    rate = round(completed / total_all * 100, 1) if total_all > 0 else 0.0

    return PMBatchKPI(
        total               = len(items),
        current_month_total = len(current_items),
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


def _calc_category_stats(items: list[MallPeriodicMaintenanceItem], check_month: int) -> list[CategoryStat]:
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
    try:
        return int(period_month.split("/")[1])
    except Exception:
        return date.today().month


# ── 週期統計輔助函式 ──────────────────────────────────────────────────────────

_MONTH_LABELS_ZH = ["1月","2月","3月","4月","5月","6月",
                    "7月","8月","9月","10月","11月","12月"]


def _reconstruct_full_date(scheduled_date: str, period_month: str) -> "date | None":
    """
    排定日期 + 批次月份 → date 物件。空值或解析失敗回傳 None。

    支援兩種格式（向下相容 DB 中尚未 normalize 的舊資料）：
      格式 A：'MM/DD'       → 以 period_month 的年份補齊
      格式 B：'YYYY/MM/DD'  → 直接解析，忽略 period_month
    """
    if not scheduled_date:
        return None
    try:
        parts = scheduled_date.strip().split("/")
        if len(parts) == 3:
            # 格式 B：YYYY/MM/DD（尚未 normalize 的 Ragic 原始格式）
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) != 2:
            return None
        month = int(parts[0])
        day   = int(parts[1])
        year  = int(period_month.strip().split("/")[0])
        return date(year, month, day)
    except Exception:
        return None


def _parse_end_date(end_time: str) -> "date | None":
    """'YYYY/MM/DD HH:MM:SS' → date，解析失敗回傳 None。"""
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


def _latest_batch_ids_per_month(db: Session) -> set:
    """每個 period_month 只保留 ragic_updated_at 最新的那張批次，回傳有效 ragic_id 集合。"""
    batches = db.query(MallPeriodicMaintenanceBatch).all()
    latest: dict[str, MallPeriodicMaintenanceBatch] = {}
    for b in batches:
        key = b.period_month
        existing = latest.get(key)
        if existing is None:
            latest[key] = b
        else:
            # 比較 ragic_updated_at 字串（格式 YYYY/MM/DD HH:MM:SS 或 YYYY/MM/DD，字典序可比）
            b_ts = b.ragic_updated_at or ""
            e_ts = existing.ragic_updated_at or ""
            if b_ts > e_ts:
                latest[key] = b
    return {b.ragic_id for b in latest.values()}


def _calc_period_stats_core(
    db: Session,
    period_start: date,
    period_end: date,
    prev_period_end: date,
    frequency_type: Optional[str] = None,
) -> dict:
    """共用統計核心（使用 MallPeriodicMaintenanceBatch / MallPeriodicMaintenanceItem）。"""
    valid_batch_ids = _latest_batch_ids_per_month(db)
    rows = (
        db.query(MallPeriodicMaintenanceItem, MallPeriodicMaintenanceBatch)
        .join(
            MallPeriodicMaintenanceBatch,
            MallPeriodicMaintenanceItem.batch_ragic_id == MallPeriodicMaintenanceBatch.ragic_id,
        )
        .filter(MallPeriodicMaintenanceBatch.ragic_id.in_(valid_batch_ids))
        .all()
    )

    prev_carry_over_list: list[dict] = []
    period_items_list:    list[dict] = []

    for item, batch in rows:
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []

        # ── 頻率篩選：優先 frequency 欄位，空時從 exec_months 數量推算 ──────
        if not _freq_match_with_fallback(item.frequency, frequency_type, exec_months):
            continue

        try:
            batch_month = int(batch.period_month.split("/")[1])
            batch_year  = int(batch.period_month.split("/")[0])
        except Exception:
            continue

        # ── full_date 以批次月份 1 號為基準（規格書規定）────────────────────
        # scheduled_date 是「排定計劃」，不代表執行月份；exec_months 亦不用於期間過濾
        # period_total 以批次月份為準，確保與保養項目清單件數一致
        full_date = date(batch_year, batch_month, 1)

        # 執行完成判斷：只依 end_time 有值（規格書規定，不看 start_time）
        is_done  = bool(item.end_time and item.end_time.strip())
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
        PMIncompleteItem(
            task_name           = x["item"].task_name,
            category            = x["item"].category or "未歸類位置",
            scheduled_date_full = x["full_date"].strftime("%Y/%m/%d"),
            result_note         = x["item"].result_note,
            frequency           = x["item"].frequency,
        )
        for x in period_items_list
        if not x["is_done"] and x["item"].result_note and x["item"].result_note.strip()
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
) -> list[PMSubPeriodBreakdown]:
    """季→月分布 / 年→Q分布 / 月→空清單"""
    if period_type == "month":
        return []

    breakdown: list[PMSubPeriodBreakdown] = []
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


def _calc_year_matrix(db: Session, year: int, frequency_type: Optional[str] = None) -> PMYearMatrix:
    """全年 12 個月矩陣統計（單次 JOIN 查詢）。"""
    valid_batch_ids = _latest_batch_ids_per_month(db)
    rows = (
        db.query(MallPeriodicMaintenanceItem, MallPeriodicMaintenanceBatch)
        .join(
            MallPeriodicMaintenanceBatch,
            MallPeriodicMaintenanceItem.batch_ragic_id == MallPeriodicMaintenanceBatch.ragic_id,
        )
        .filter(
            MallPeriodicMaintenanceBatch.ragic_id.in_(valid_batch_ids),
            MallPeriodicMaintenanceBatch.period_month.like(f"{year}/%"),   # 限制在指定年份
        )
        .all()
    )

    processed: list[dict] = []
    for item, batch in rows:
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []

        # ── 頻率篩選：優先 frequency 欄位，空時從 exec_months 數量推算 ──────
        if not _freq_match_with_fallback(item.frequency, frequency_type, exec_months):
            continue

        try:
            batch_month = int(batch.period_month.split("/")[1])
            batch_year  = int(batch.period_month.split("/")[0])
        except Exception:
            continue

        # ── full_date 以批次月份 1 號為基準（規格書規定，exec_months 不影響期間歸屬）
        full_date = date(batch_year, batch_month, 1)

        is_done  = bool(item.end_time and item.end_time.strip())
        end_date = _parse_end_date(item.end_time)
        processed.append({
            "item":      item,
            "full_date": full_date,
            "end_date":  end_date,
            "is_done":   is_done,
        })

    month_results: list[PMYearMatrixMonth] = []
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

        notes_parts = [
            f"{x['item'].task_name}：{x['item'].result_note}"
            for x in period_items_list
            if not x["is_done"] and x["item"].result_note and x["item"].result_note.strip()
        ]

        n_carry    = len(prev_carry_over_list)
        n_resolved = len(prev_resolved_list)
        n_total    = len(period_items_list)
        n_done     = len(period_completed_list)

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


def _batch_to_out(batch: MallPeriodicMaintenanceBatch) -> PMBatchOut:
    return PMBatchOut(
        ragic_id         = batch.ragic_id,
        journal_no       = batch.journal_no,
        period_month     = batch.period_month,
        ragic_created_at = batch.ragic_created_at,
        ragic_updated_at = batch.ragic_updated_at,
        synced_at        = batch.synced_at,
    )


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/sync", summary="從 Ragic 同步商場週期保養資料（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_mall_periodic_maintenance(background_tasks: BackgroundTasks):
    """手動觸發：Ragic → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"status": "ok", "message": "同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches", summary="取得商場保養批次清單")
def list_batches(
    year: Optional[str] = Query(None, description="篩選年份，如 2026"),
    db:   Session = Depends(get_db),
):
    q = db.query(MallPeriodicMaintenanceBatch)
    if year:
        q = q.filter(MallPeriodicMaintenanceBatch.period_month.like(f"{year}%"))
    batches = q.order_by(MallPeriodicMaintenanceBatch.period_month.desc()).all()

    result = []
    for b in batches:
        items = db.query(MallPeriodicMaintenanceItem).filter(
            MallPeriodicMaintenanceItem.batch_ragic_id == b.ragic_id
        ).all()
        check_month = _get_check_month(b.period_month)
        kpi = _calc_kpi(items, check_month)
        batch_dict = _batch_to_out(b).model_dump()
        batch_dict["ragic_url"] = (
            f"https://ap12.ragic.com/soutlet001/periodic-maintenance/18/{b.ragic_id}"
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
    batch_id:           str,
    current_month_only: bool = Query(False),
    category:           Optional[str] = Query(None),
    status_filter:      Optional[str] = Query(None, alias="status"),
    db:                 Session = Depends(get_db),
):
    batch = db.get(MallPeriodicMaintenanceBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    items = db.query(MallPeriodicMaintenanceItem).filter(
        MallPeriodicMaintenanceItem.batch_ragic_id == batch_id
    ).order_by(MallPeriodicMaintenanceItem.seq_no).all()

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

    return PMBatchDetail(
        batch      = _batch_to_out(batch),
        kpi        = kpi,
        items      = filtered,
        categories = cats,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches/{batch_id}/kpi
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches/{batch_id}/kpi", summary="取得批次 KPI 統計")
def get_batch_kpi(batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(MallPeriodicMaintenanceBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    items = db.query(MallPeriodicMaintenanceItem).filter(
        MallPeriodicMaintenanceItem.batch_ragic_id == batch_id
    ).all()
    check_month = _get_check_month(batch.period_month)
    return _calc_kpi(items, check_month)


# ══════════════════════════════════════════════════════════════════════════════
# GET /items
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/items", summary="跨批次查詢商場保養項目")
def list_items(
    batch_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    month:    Optional[int] = Query(None, ge=1, le=12),
    db:       Session = Depends(get_db),
):
    q = db.query(MallPeriodicMaintenanceItem)
    if batch_id:
        q = q.filter(MallPeriodicMaintenanceItem.batch_ragic_id == batch_id)
    if category:
        q = q.filter(MallPeriodicMaintenanceItem.category == category)
    items = q.order_by(
        MallPeriodicMaintenanceItem.batch_ragic_id,
        MallPeriodicMaintenanceItem.seq_no,
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
# GET /stats
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

    current_batch = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month == target_ym
    ).first()

    if not current_batch and not (year or month):
        current_batch = db.query(MallPeriodicMaintenanceBatch).order_by(
            MallPeriodicMaintenanceBatch.period_month.desc()
        ).first()

    current_kpi    = None
    overdue_items: list[PMItemOut] = []
    upcoming_items: list[PMItemOut] = []
    cats:           list[CategoryStat] = []
    status_dist:    list[StatusDistItem] = []

    if current_batch:
        items = db.query(MallPeriodicMaintenanceItem).filter(
            MallPeriodicMaintenanceItem.batch_ragic_id == current_batch.ragic_id
        ).order_by(MallPeriodicMaintenanceItem.seq_no).all()

        current_kpi = _calc_kpi(items, check_month)
        cats        = _calc_category_stats(items, check_month)

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
        def _dist_status(it: MallPeriodicMaintenanceItem) -> str | None:
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
        current_batch       = _batch_to_out(current_batch) if current_batch else None,
        current_kpi         = current_kpi,
        overdue_items       = overdue_items,
        upcoming_items      = upcoming_items,
        category_stats      = cats,
        status_distribution = status_dist,
    )


# ══════════════════════════════════════════════════════════════════════════════
# GET /calendar  — 月曆格（類別 × 日期）
# 2026-07-14 新增：Dashboard 原本沿用 mall_facility_inspection（商場工務巡檢，完全
# 不同模組）的每日巡檢月曆（fetchMallFIDailyCalendar）當佔位資料，標題「...每日巡檢
# 狀況」其實正確描述了那份資料本身，只是那份資料根本不屬於本模組（商場週期保養）。
# 比照 full_building_maintenance.py::get_calendar()（同一批 2026-07-13 Sheet 改版
# 模組，資料結構相同）補上本模組專屬版本，改為呈現週期保養項目的類別 × 日完成狀況。
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/calendar", summary="商場週期保養月曆格（類別 × 日）")
def get_mall_pm_calendar(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份，如 5"),
    db:    Session = Depends(get_db),
):
    """
    回傳指定年月的類別 × 日期月曆格資料。
    cell key = str(d)（非零填充，配合 MonthlyCalendarGrid）。
    """
    import calendar as cal_mod
    max_day   = cal_mod.monthrange(year, month)[1]
    target_ym = f"{year}/{month:02d}"

    batch = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month == target_ym
    ).first()

    # 已知類別順序（比照全棟例行維護；若商場實際類別不同，未知類別仍會依下方邏輯附加在後）
    CATEGORY_ORDER = ["水電", "空調", "照明", "消防", "申報", "整體"]

    def _empty_daily() -> dict:
        return {
            str(d): {"has_record": False, "completion_rate": 0, "abnormal_count": 0, "pending_count": 0}
            for d in range(1, max_day + 1)
        }

    if not batch:
        return {
            "year": year, "month": month, "max_day": max_day,
            "rows": [{"key": c, "label": c, "daily": _empty_daily()} for c in CATEGORY_ORDER],
        }

    items = db.query(MallPeriodicMaintenanceItem).filter(
        MallPeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id
    ).all()

    # 依類別 × 日分組（用 scheduled_date 的 MM/DD 推算日期）
    from collections import defaultdict
    cat_day: dict[str, dict[int, list]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        fd = _reconstruct_full_date(it.scheduled_date, batch.period_month)
        if fd is None or fd.year != year or fd.month != month:
            continue
        cat_day[it.category or "其他"][fd.day].append(it)

    # 確保所有已知類別都出現；額外類別附加在後
    all_cats = list(CATEGORY_ORDER)
    for c in cat_day:
        if c not in all_cats:
            all_cats.append(c)

    rows_out = []
    for cat in all_cats:
        daily: dict[str, dict] = {}
        for d in range(1, max_day + 1):
            day_items = cat_day[cat].get(d, [])
            if not day_items:
                daily[str(d)] = {"has_record": False, "completion_rate": 0, "abnormal_count": 0, "pending_count": 0}
            else:
                total     = len(day_items)
                completed = sum(1 for it in day_items if it.start_time and it.end_time)
                abnormal  = sum(1 for it in day_items if it.abnormal_flag)
                pending   = total - completed
                rate      = round(completed / total * 100, 1) if total > 0 else 0.0
                daily[str(d)] = {
                    "has_record":      True,
                    "completion_rate": rate,
                    "abnormal_count":  abnormal,
                    "pending_count":   pending,
                }
        rows_out.append({"key": cat, "label": cat, "daily": daily})

    return {"year": year, "month": month, "max_day": max_day, "rows": rows_out}


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/task-history
# ══════════════════════════════════════════════════════════════════════════════
def _offset_month(year: int, month: int, delta: int) -> tuple[int, int]:
    total = (year * 12 + (month - 1)) + delta
    return total // 12, (total % 12) + 1


@router.get("/items/task-history", summary="依保養項目名稱查詢近 N 個月執行歷史")
def get_item_task_history(
    task_name: str = Query(..., description="保養項目名稱（完整比對）"),
    months:    int = Query(12, ge=1, le=24),
    db:        Session = Depends(get_db),
):
    today = date.today()

    rows = (
        db.query(MallPeriodicMaintenanceItem, MallPeriodicMaintenanceBatch)
        .join(
            MallPeriodicMaintenanceBatch,
            MallPeriodicMaintenanceItem.batch_ragic_id == MallPeriodicMaintenanceBatch.ragic_id,
        )
        .filter(MallPeriodicMaintenanceItem.task_name == task_name)
        .order_by(MallPeriodicMaintenanceBatch.period_month.desc())
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"找不到保養項目：{task_name}")

    first_item: MallPeriodicMaintenanceItem = rows[0][0]

    month_map: dict[str, tuple] = {}
    for item, batch in rows:
        month_map[batch.period_month] = (item, batch)

    monthly_summary = []
    for i in range(months - 1, -1, -1):
        y, m = _offset_month(today.year, today.month, -i)
        period_month = f"{y}/{m:02d}"
        is_current   = (y == today.year and m == today.month)

        if period_month in month_map:
            item, _ = month_map[period_month]
            monthly_summary.append({
                "period_month":   period_month,
                "status":         _calc_status(item, m),
                "has_record":     True,
                "executor_name":  item.executor_name or "",
                "scheduled_date": item.scheduled_date or "",
                "start_time":     item.start_time or "",
                "end_time":       item.end_time or "",
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
# GET /items/{item_ragic_id}/worklogs（2026-07-13 新增：Sheet24 巢狀「維修記錄」明細）
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
    summary="單一項目維修記錄明細（來源 Ragic Sheet24 巢狀子表格）",
)
def get_item_worklogs(item_ragic_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(MallPMItemWorklog)
        .filter(MallPMItemWorklog.item_ragic_id == item_ragic_id)
        .order_by(MallPMItemWorklog.seq_no.asc())
        .all()
    )
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/{item_ragic_id}/db-images（2026-07-13 新增：Sheet24「圖片上傳」欄位，
# 遵循全站「明細 Drawer 強制規範」的 /db-images/{ragic_id} 端點慣例）
# ══════════════════════════════════════════════════════════════════════════════
class PMImageOut(BaseModel):
    url:      str
    filename: str


@router.get(
    "/items/{item_ragic_id}/db-images",
    response_model=List[PMImageOut],
    summary="單一項目附圖（DB 優先，缺資料時即時向 Ragic 補抓一次，來源 Sheet24「圖片上傳」欄位）",
)
async def get_item_images(item_ragic_id: str, db: Session = Depends(get_db)):
    item = await run_in_threadpool(db.get, MallPeriodicMaintenanceItem, item_ragic_id)
    if item and item.images_json:
        try:
            cached = json.loads(item.images_json)
            if cached:
                return cached
        except Exception:
            pass

    # DB 沒資料（尚未同步過此欄位，或該筆項目本來就沒附圖）→ 即時向 Ragic 補抓一次；
    # 不寫回 DB，下次排程同步時會自然補齊。
    from app.services.mall_periodic_maintenance_sync import (
        MALL_PM_SERVER_URL, MALL_PM_ACCOUNT, MALL_PM_SHEET24_PATH, CK24L_IMAGES,
    )
    from app.services.ragic_data_service import parse_images

    adapter = RagicAdapter(
        sheet_path=MALL_PM_SHEET24_PATH,
        server_url=MALL_PM_SERVER_URL,
        account=MALL_PM_ACCOUNT,
    )
    try:
        full_record = await adapter.fetch_one(item_ragic_id)
        if item_ragic_id in full_record and len(full_record) == 1:
            full_record = full_record[item_ragic_id]
        return parse_images(
            full_record.get(CK24L_IMAGES),
            server=MALL_PM_SERVER_URL,
            account=MALL_PM_ACCOUNT,
        )
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats/year-matrix  — 全年 12 個月矩陣統計
# ⚠️ 必須定義在 /period-stats 之前，否則 FastAPI 會誤判路徑
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats/year-matrix", summary="全年 12 個月矩陣統計", response_model=PMYearMatrix)
def get_period_stats_year_matrix(
    year:           Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db:             Session = Depends(get_db),
):
    target_year = year or date.today().year
    return _calc_year_matrix(db, target_year, frequency_type)


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats  — 週期統計（月 / 季 / 年）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats", summary="週期統計（月/季/年）", response_model=PMPeriodStats)
def get_period_stats(
    period_type:    str           = Query("month", description="month | quarter | year"),
    year:           Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    month:          Optional[int] = Query(None, ge=1, le=12, description="月份（period_type=month 時使用）"),
    quarter:        Optional[int] = Query(None, ge=1, le=4,  description="季度 1-4（period_type=quarter 時使用）"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
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
# GET /period-stats/year-matrix/items  — 矩陣格點擊查詢明細
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats/year-matrix/items", summary="矩陣格點擊查詢明細")
def get_year_matrix_items(
    year:           int           = Query(...),
    month:          int           = Query(..., description="0 = 全年合計"),
    metric:         str           = Query(..., description="prev_carry_over | prev_resolved | period_total | period_completed"),
    frequency_type: Optional[str] = Query(None),
    db:             Session       = Depends(get_db),
):
    """
    矩陣格點擊查詢明細。

    carry-over 邏輯說明：
      - 排定日期（scheduled_date）≠ 執行日期
      - 執行完成判斷：end_time 有值 → 已完成；end_time 空 → 未執行（未結案）
      - prev_carry_over：full_date ≤ 上月底 且 end_time 空（或 end_date > 上月底）的項目
      - prev_resolved ：full_date ≤ 上月底 且 end_date 落在本期內的項目
      - period_total  ：full_date 落在本月的所有項目
      - period_completed：period_total 中 end_time 有值的項目
    """
    valid_batch_ids = _latest_batch_ids_per_month(db)
    rows = (
        db.query(MallPeriodicMaintenanceItem, MallPeriodicMaintenanceBatch)
        .join(MallPeriodicMaintenanceBatch,
              MallPeriodicMaintenanceItem.batch_ragic_id == MallPeriodicMaintenanceBatch.ragic_id)
        .filter(
            MallPeriodicMaintenanceBatch.ragic_id.in_(valid_batch_ids),
            MallPeriodicMaintenanceBatch.period_month.like(f"{year}/%"),
        )
        .all()
    )

    # ── 計算期間邊界 ─────────────────────────────────────────────────────────────
    if month == 0:
        p_start = date(year, 1, 1)
        _, p_last = monthrange(year, 12)
        p_end    = date(year, 12, p_last)
        prev_end = date(year - 1, 12, 31)
    else:
        _, p_last = monthrange(year, month)
        p_start = date(year, month, 1)
        p_end   = date(year, month, p_last)
        if month == 1:
            prev_end = date(year - 1, 12, 31)
        else:
            _, prev_last = monthrange(year, month - 1)
            prev_end = date(year, month - 1, prev_last)

    results = []
    for item, batch in rows:
        if not _freq_match(item.frequency, frequency_type):
            continue

        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []

        try:
            batch_month = int(batch.period_month.split("/")[1])
            batch_year  = int(batch.period_month.split("/")[0])
        except Exception:
            continue

        # ── 判斷此批次月份是否為執行月份（與統計函式同邏輯）────────────────────
        if exec_months:
            if batch_month not in exec_months:
                continue
        elif not _should_schedule(item, batch_year, batch_month):
            continue

        # ── 計算 full_date ────────────────────────────────────────────────────
        if item.scheduled_date:
            full_date = _reconstruct_full_date(item.scheduled_date, batch.period_month)
        else:
            full_date = date(batch_year, batch_month, 1)
        if full_date is None:
            continue

        # ── 執行完成判斷：end_time 有值 = 已完成 ─────────────────────────────
        is_done  = bool(item.end_time and item.end_time.strip())
        end_date = _parse_end_date(item.end_time) if item.end_time else None

        # ── 依 metric 篩選 ────────────────────────────────────────────────────
        if metric == 'prev_carry_over':
            # 截至上月底：full_date ≤ 上月底，且尚未完成（end_time 空，或結案日期 > 上月底）
            if full_date > prev_end:
                continue
            done_before = is_done and end_date is not None and end_date <= prev_end
            if done_before:
                continue

        elif metric == 'prev_resolved':
            # 截至上月底的未結案中，本月已結案的項目
            if full_date > prev_end:
                continue
            if not (is_done and end_date and p_start <= end_date <= p_end):
                continue

        elif metric == 'period_total':
            # 本月應完成的項目（full_date 落在本月）
            if not (p_start <= full_date <= p_end):
                continue

        elif metric == 'period_completed':
            # 本月應完成且已完成
            if not (p_start <= full_date <= p_end and is_done):
                continue

        # ── 組裝 scheduled_date_full ──────────────────────────────────────────
        sched_full = ""
        if item.scheduled_date:
            fd = _reconstruct_full_date(item.scheduled_date, batch.period_month)
            sched_full = fd.strftime("%Y/%m/%d") if fd else ""

        results.append({
            "ragic_id":            item.ragic_id,
            "batch_ragic_id":      item.batch_ragic_id,
            "period_month":        batch.period_month,
            "category":            item.category,
            "task_name":           item.task_name,
            "frequency":           item.frequency,
            "scheduled_date_full": sched_full,
            "end_time":            item.end_time or "",
            "status":              "已完成" if is_done else ("進行中" if item.start_time else "待排程"),
            "executor_name":       item.executor_name or "",
            "result_note":         item.result_note or "",
            "abnormal_flag":       bool(item.abnormal_flag),
            "abnormal_note":       item.abnormal_note or "",
            "ragic_link":          "",
        })

    return {"total": len(results), "items": results}


# ── 保養項目目錄（依頻率分類）──────────────────────────────────────────────────
@router.get("/items/catalog", summary="保養項目目錄（依頻率分類）")
def get_items_catalog(
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db:             Session       = Depends(get_db),
):
    """
    取得保養項目目錄（不分批次），依 frequency_type 篩選。
    結果為去重後的保養項目列表，以最新 seq_no 的資料為準。
    """
    from sqlalchemy import func as sqlfunc

    subq = (
        db.query(
            MallPeriodicMaintenanceItem.task_name,
            MallPeriodicMaintenanceItem.category,
            MallPeriodicMaintenanceItem.frequency,
            sqlfunc.max(MallPeriodicMaintenanceItem.seq_no).label("max_seq"),
        )
        .group_by(
            MallPeriodicMaintenanceItem.task_name,
            MallPeriodicMaintenanceItem.category,
            MallPeriodicMaintenanceItem.frequency,
        )
        .subquery()
    )

    rows = (
        db.query(MallPeriodicMaintenanceItem)
        .join(
            subq,
            (MallPeriodicMaintenanceItem.task_name   == subq.c.task_name)
            & (MallPeriodicMaintenanceItem.category  == subq.c.category)
            & (MallPeriodicMaintenanceItem.frequency == subq.c.frequency)
            & (MallPeriodicMaintenanceItem.seq_no    == subq.c.max_seq),
        )
        .order_by(MallPeriodicMaintenanceItem.category, MallPeriodicMaintenanceItem.seq_no)
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
# GET /debug/ragic-raw  — 除錯用
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/debug/ragic-raw", summary="[除錯] 顯示 Ragic Sheet 18 原始欄位 key", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_ragic_raw():
    from app.services.mall_periodic_maintenance_sync import (
        MALL_PM_SERVER_URL, MALL_PM_ACCOUNT,
        MALL_PM_JOURNAL_PATH, MALL_PM_ITEMS_PATH,
    )

    adapter_batch = RagicAdapter(
        sheet_path=MALL_PM_JOURNAL_PATH,
        server_url=MALL_PM_SERVER_URL,
        account=MALL_PM_ACCOUNT,
    )
    adapter_items = RagicAdapter(
        sheet_path=MALL_PM_ITEMS_PATH,
        server_url=MALL_PM_SERVER_URL,
        account=MALL_PM_ACCOUNT,
    )

    try:
        raw_batch = await adapter_batch.fetch_all()
        raw_items = await adapter_items.fetch_all()
    except Exception as exc:
        return {"error": str(exc)}

    first_batch = next(iter(raw_batch.values()), {}) if raw_batch else {}
    first_item  = next(iter(raw_items.values()), {}) if raw_items else {}

    return {
        "sheet18_batch": {
            "total_records":      len(raw_batch),
            "record_ids":         list(raw_batch.keys()),
            "first_record_fields": first_batch,
        },
        "sheet18_items": {
            "total_records":      len(raw_items),
            "record_ids":         list(raw_items.keys()),
            "first_record_fields": first_item,
        },
    }


# ── GET /debug/ragic-sheet24-raw ─────────────────────────────────────────────

@router.get("/debug/ragic-sheet24-raw",
            summary="[除錯] 顯示 Ragic Sheet 24 原始欄位 key（維修工時來源）",
            dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_ragic_sheet24_raw(limit: int = 3):
    """
    顯示 Sheet 24（商場週期保養 - 子表: 項目）的前幾筆原始 JSON。

    用途：確認以下欄位名稱：
      1. 「維修工時」的實際 key（預設 CK24_REPAIR_HOURS）
      2. 指向 Sheet 18 父記錄的關聯欄位 key（預設 CK24_PARENT_REF）
      3. 其他可用於配對的欄位 key（項目/類別/位置）

    確認後請更新 .env 或 sync 程式碼中對應的 CK24_* 常數。
    """
    from app.services.mall_periodic_maintenance_sync import (
        MALL_PM_SERVER_URL, MALL_PM_ACCOUNT, MALL_PM_SHEET24_PATH,
        CK24_REPAIR_HOURS, CK24_TASK_NAME, CK24_CATEGORY, CK24_LOCATION, CK24_PARENT_REF,
    )

    adapter = RagicAdapter(
        sheet_path=MALL_PM_SHEET24_PATH,
        server_url=MALL_PM_SERVER_URL,
        account=MALL_PM_ACCOUNT,
    )

    try:
        raw_data = await adapter.fetch_all()
    except Exception as exc:
        return {"error": str(exc)}

    records = list(raw_data.items())[:limit]
    samples = {}
    for rec_id, rec in records:
        samples[rec_id] = rec

    all_keys = sorted(set(
        k for _, rec in records for k in rec.keys()
    ))

    return {
        "sheet24_path":      MALL_PM_SHEET24_PATH,
        "total_records":     len(raw_data),
        "all_field_keys":    all_keys,
        "current_ck24_config": {
            "CK24_REPAIR_HOURS": CK24_REPAIR_HOURS,
            "CK24_TASK_NAME":    CK24_TASK_NAME,
            "CK24_CATEGORY":     CK24_CATEGORY,
            "CK24_LOCATION":     CK24_LOCATION,
            "CK24_PARENT_REF":   CK24_PARENT_REF,
        },
        "sample_records": samples,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 排程管理（mall_pm_schedule）相關 Endpoints
# ══════════════════════════════════════════════════════════════════════════════

def _mall_get_latest_batch_items(db: Session) -> list[MallPeriodicMaintenanceItem]:
    """取得最新批次的所有保養項目，作為主檔來源。"""
    latest_batch = (
        db.query(MallPeriodicMaintenanceBatch)
        .order_by(MallPeriodicMaintenanceBatch.period_month.desc())
        .first()
    )
    if not latest_batch:
        return []
    return (
        db.query(MallPeriodicMaintenanceItem)
        .filter(MallPeriodicMaintenanceItem.batch_ragic_id == latest_batch.ragic_id)
        .order_by(MallPeriodicMaintenanceItem.seq_no)
        .all()
    )


def _mall_calc_schedule_status(rec: MallPMSchedule) -> str:
    """計算 mall_pm_schedule 記錄的狀態。"""
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


def _mall_schedule_to_out(rec: MallPMSchedule) -> MallPMScheduleOut:
    """ORM → Pydantic，動態注入 status。"""
    return MallPMScheduleOut(
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
        status           = _mall_calc_schedule_status(rec),
    )


# ── 輔助：依 exec_months 自動計算排定日期 ──────────────────────────────────────

def _calc_auto_scheduled_date(exec_months_json: Optional[str], batch_month: int) -> str:
    """
    依 exec_months_json 自動計算最近的排定日期。

    規則：找第一個 exec_month >= batch_month 的月份，回傳 "MM/01"。
    若找不到（如 12 月批次後沒有下一個 exec_month），回傳空字串。

    範例：
      exec_months=[1,4,7,11], batch_month=6 → "07/01"（下個執行月=7）
      exec_months=[1,4,7,11], batch_month=7 → "07/01"（當月即執行月）
      exec_months=[1,4,7,11], batch_month=12 → ""（無下一個執行月）
    """
    if not exec_months_json:
        return ""
    try:
        exec_months = json.loads(exec_months_json)
        if not exec_months:
            return ""
        future = sorted([m for m in exec_months if m >= batch_month])
        return f"{future[0]:02d}/01" if future else ""
    except Exception:
        return ""


# ── POST /schedule/generate ───────────────────────────────────────────────────

@router.post("/schedule/generate", summary="產生指定月份商場保養排程（防重複）",
             response_model=MallPMScheduleGenerateResult)
def generate_mall_schedule(
    year:  int = Query(..., description="年份，如 2026"),
    month: int = Query(..., ge=1, le=12, description="月份 1-12"),
    db:    Session = Depends(get_db),
):
    """
    依最新批次 mall_pm_batch_item 的頻率規則，為指定 year/month 產生 mall_pm_schedule 記錄。

    保護規則：
      - is_completed=True → 跳過（不覆蓋已完成）
      - portal_edited_at IS NOT NULL → 跳過（不覆蓋人工調整）
      - 其他已存在記錄 → 更新 scheduled_date / executor_name

    2026-07-13 修正（取消對非當期月份的自動備填，見對話紀錄）：
      舊版邏輯會用 (task_name, category, location) 到「目標月份自己的批次」查排定日期，
      查不到才 fallback 用 item.scheduled_date（永遠是最新批次/當期月份的值）。
      Sheet24 改版後 location 欄位永遠空白、且不同月份的保養目錄項目數量與組成本身
      就不是一對一（實測：06 月批次 16 筆項目、07 月批次僅 8 筆，任務內容也不同），
      改用 seq_no 比對一樣會錯配（07 月 seq=7 是「門扇→巡檢保養」，06 月 seq=7 卻是
      「商場送風機x14」）。結論：非當期月份的目錄本來就無法從現在的目錄可靠地反推，
      任何自動比對 key 都有風險，因此改為——只有「目標月份＝目前最新批次自己的月份」
      時才直接採用 item.scheduled_date（此時來源與目標是同一批次，比對必然正確）；
      其餘月份一律改用 exec_months 自動推算（每月固定 01 號，見 _calc_auto_scheduled_date），
      不再嘗試任何跨批次查表備填。
    """
    year_month = f"{year}/{month:02d}"
    items = _mall_get_latest_batch_items(db)

    latest_batch_period_month = ""
    if items:
        latest_batch = db.get(MallPeriodicMaintenanceBatch, items[0].batch_ragic_id)
        if latest_batch:
            latest_batch_period_month = latest_batch.period_month
    is_current_batch_month = bool(latest_batch_period_month) and (latest_batch_period_month == year_month)

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

            # 有 exec_months 的項目：一律納入排程，scheduled_date 由 exec_months 自動計算
            # 無 exec_months 的項目：依頻率公式，只在執行月份才建立排程記錄
            has_exec_months = bool(
                item.exec_months_json and item.exec_months_json.strip() not in ("[]", "")
            )
            if not has_exec_months and not _should_schedule(item, year, month):
                skipped_non_month += 1
                continue

            existing = (
                db.query(MallPMSchedule)
                .filter(
                    MallPMSchedule.year_month    == year_month,
                    MallPMSchedule.item_ragic_id == item.ragic_id,
                )
                .first()
            )

            # resolved_date 優先順序：
            #   1. 目標月份＝目前最新批次自己的月份時，直接採用 item.scheduled_date
            #      （來源與目標同一批次，比對必然正確；見函式頂部 2026-07-13 修正說明）
            #   2. 其餘月份一律用 exec_months 自動計算（MM/01），不再嘗試任何跨批次查表備填
            #   3. 都沒有 → 空字串
            if is_current_batch_month and item.scheduled_date:
                resolved_date = item.scheduled_date
            elif has_exec_months:
                resolved_date = _calc_auto_scheduled_date(item.exec_months_json, month)
            else:
                resolved_date = ""

            if existing:
                if existing.is_completed or (existing.start_time and existing.end_time):
                    skipped_completed += 1
                    continue
                if existing.portal_edited_at is not None:
                    skipped_edited += 1
                    continue
                existing.scheduled_date    = resolved_date
                existing.executor_name     = item.executor_name
                existing.estimated_minutes = item.estimated_minutes
                # 2026-07-13 修正：帶入 Ragic 同步回來的完成狀態（原本從未寫入，見函式頂部
                # 說明）。只在「目標月份＝目前最新批次自己的月份」時才帶入——其餘月份的
                # item.start_time/end_time 是當期月份的實際執行時間，跟過去/未來月份的排程
                # 無關，不應該被帶進去（理由同上方 resolved_date 只在當期月份採用 item 資料）。
                if is_current_batch_month:
                    existing.start_time    = item.start_time
                    existing.end_time      = item.end_time
                    existing.is_completed  = item.is_completed
                    existing.result_note   = item.result_note
                    existing.abnormal_flag = item.abnormal_flag
                    existing.abnormal_note = item.abnormal_note
                existing.updated_at        = datetime.now()
                updated += 1
            else:
                new_rec = MallPMSchedule(
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
                    # 同上：新建記錄時，若為當期月份也一併帶入 item 已知的完成狀態
                    start_time    = item.start_time    if is_current_batch_month else "",
                    end_time      = item.end_time      if is_current_batch_month else "",
                    is_completed  = item.is_completed  if is_current_batch_month else False,
                    result_note   = item.result_note   if is_current_batch_month else "",
                    abnormal_flag = item.abnormal_flag if is_current_batch_month else False,
                    abnormal_note = item.abnormal_note if is_current_batch_month else "",
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

    return MallPMScheduleGenerateResult(
        year_month            = year_month,
        generated             = generated,
        updated               = updated,
        skipped_completed     = skipped_completed,
        skipped_edited        = skipped_edited,
        skipped_non_month     = skipped_non_month,
        skipped_no_frequency  = skipped_no_frequency,
        errors                = errors,
    )


# ── GET /schedule ─────────────────────────────────────────────────────────────

@router.get("/schedule", summary="查詢商場排程明細列表")
def list_mall_schedule(
    year_month: Optional[str] = Query(None, description="月份，如 2026/05；預設為本月"),
    category:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None),
    db:         Session = Depends(get_db),
):
    if not year_month:
        today = date.today()
        year_month = f"{today.year}/{today.month:02d}"

    q = db.query(MallPMSchedule).filter(MallPMSchedule.year_month == year_month)
    if category:
        q = q.filter(MallPMSchedule.category == category)

    records   = q.order_by(MallPMSchedule.category, MallPMSchedule.task_name).all()
    items_out = [_mall_schedule_to_out(r) for r in records]

    if status:
        if status == "abnormal":
            items_out = [i for i in items_out if i.abnormal_flag]
        else:
            items_out = [i for i in items_out if i.status == status]

    all_items    = _mall_get_latest_batch_items(db)
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

@router.get("/schedule/kpi", summary="商場排程 KPI 統計", response_model=MallPMScheduleKPI)
def get_mall_schedule_kpi(
    year_month: Optional[str] = Query(None, description="月份，如 2026/05；預設本月"),
    db:         Session = Depends(get_db),
):
    if not year_month:
        today = date.today()
        year_month = f"{today.year}/{today.month:02d}"

    records   = db.query(MallPMSchedule).filter(MallPMSchedule.year_month == year_month).all()
    items_out = [_mall_schedule_to_out(r) for r in records]

    total       = len(items_out)
    completed   = sum(1 for i in items_out if i.status == "completed")

    all_items    = _mall_get_latest_batch_items(db)
    year_i       = int(year_month.split("/")[0])
    month_i      = int(year_month.split("/")[1])
    existing_ids = {r.item_ragic_id for r in records}
    should_do_not_done = sum(
        1 for it in all_items
        if _should_schedule(it, year_i, month_i) and it.ragic_id not in existing_ids
    )

    return MallPMScheduleKPI(
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

@router.get("/schedule/overdue", summary="商場跨月逾期未執行清單")
def list_mall_overdue_schedule(
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
        db.query(MallPMSchedule)
        .filter(MallPMSchedule.is_completed == False)
        .filter(MallPMSchedule.scheduled_date != "")
        .order_by(MallPMSchedule.year_month, MallPMSchedule.scheduled_date)
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

        out_dict = _mall_schedule_to_out(rec).model_dump()
        out_dict["overdue_days"] = (cutoff - sched).days
        overdue_items.append(out_dict)
        months_set.add(rec.year_month)

    return {
        "total":           len(overdue_items),
        "months_affected": sorted(months_set),
        "items":           overdue_items,
    }


# ── PATCH /schedule/{id} ──────────────────────────────────────────────────────

@router.patch("/schedule/{schedule_id}", summary="人工調整商場排程明細")
def update_mall_schedule(
    schedule_id: int,
    body:        MallPMScheduleUpdate,
    db:          Session = Depends(get_db),
):
    rec = db.get(MallPMSchedule, schedule_id)
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

    return _mall_schedule_to_out(rec)


# ── GET /schedule/annual-matrix ───────────────────────────────────────────────

@router.get("/schedule/annual-matrix", summary="商場年度計劃矩陣（12欄）",
            response_model=MallPMScheduleAnnualMatrix)
def get_mall_annual_matrix(
    year:     int = Query(..., description="年份，如 2026"),
    category: Optional[str] = Query(None),
    db:       Session = Depends(get_db),
):
    all_items = _mall_get_latest_batch_items(db)
    if category:
        all_items = [it for it in all_items if it.category == category]

    year_records = (
        db.query(MallPMSchedule)
        .filter(MallPMSchedule.year_month.like(f"{year}/%"))
        .all()
    )
    schedule_map: dict[tuple[str, int], MallPMSchedule] = {}
    for rec in year_records:
        try:
            m = int(rec.year_month.split("/")[1])
            schedule_map[(rec.item_ragic_id, m)] = rec
        except Exception:
            pass

    # 2026-07-13 修正：移除「用 (task_name, category, location) 到該月批次查表補回
    # scheduled_date」的備填邏輯。原因與 generate_mall_schedule() 同一批次修正（見該
    # 函式頂部說明）——location 欄位 Sheet24 改版後永遠空白、不同月份的保養目錄本身
    # 就不是一對一（同 task_name+category 常有多筆不同日期的項目），任何自動比對
    # key 都會有錯配風險，因此不再嘗試備填，scheduled_date 為空就如實顯示為空。

    rows: list[MallPMScheduleMatrixRow] = []
    completed_cnt = 0

    for item in all_items:
        cells: list[MallPMScheduleMatrixCell] = []
        for m in range(1, 13):
            rec = schedule_map.get((item.ragic_id, m))
            if rec:
                status = _mall_calc_schedule_status(rec)
                if status == "completed":
                    completed_cnt += 1
                cells.append(MallPMScheduleMatrixCell(
                    month          = m,
                    status         = status,
                    schedule_id    = rec.id,
                    scheduled_date = rec.scheduled_date or None,
                ))
            else:
                freq = (item.frequency or "").strip()
                if not freq:
                    cells.append(MallPMScheduleMatrixCell(month=m, status="no_frequency", schedule_id=None))
                elif _should_schedule(item, year, m):
                    # ── 決定 cell_sched_date ──────────────────────────────────
                    # 優先 1：Ragic item.scheduled_date；優先 2：MM/01（執行月預設）
                    cell_sched_date: Optional[str] = f"{m:02d}/01"
                    cell_status = "no_data"
                    if item.scheduled_date:
                        try:
                            parts = item.scheduled_date.split("/")
                            sched_month = int(parts[0])
                            day = parts[-1].zfill(2)
                            cell_sched_date = f"{m:02d}/{day}"
                            if sched_month == m:
                                if item.is_completed or (item.start_time and item.end_time):
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
                            cell_sched_date = f"{m:02d}/01"

                    # 未來月份不顯示「！」，改為「—」（但保留 scheduled_date 提示）
                    today = date.today()
                    if year > today.year or (year == today.year and m > today.month):
                        cells.append(MallPMScheduleMatrixCell(
                            month=m, status="non_month",
                            schedule_id=None, scheduled_date=cell_sched_date,
                        ))
                    else:
                        cells.append(MallPMScheduleMatrixCell(
                            month=m, status=cell_status,
                            schedule_id=None, scheduled_date=cell_sched_date,
                        ))
                else:
                    cells.append(MallPMScheduleMatrixCell(month=m, status="non_month", schedule_id=None))

        rows.append(MallPMScheduleMatrixRow(
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

    return MallPMScheduleAnnualMatrix(
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
