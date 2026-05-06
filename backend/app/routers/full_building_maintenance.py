"""
全棟例行維護 API Router
Prefix: /api/v1/mall/full-building-maintenance

端點：
  POST /sync                         — 手動從 Ragic 同步
  GET  /batches                      — 批次清單（年份篩選）
  GET  /batches/{batch_id}           — 單筆批次 + 所有項目 + KPI
  GET  /batches/{batch_id}/kpi       — 批次 KPI 統計
  GET  /items                        — 所有項目跨批次查詢
  GET  /stats                        — 全站統計（Dashboard 資料來源）
  GET  /items/task-history           — 依項目名稱查詢近 N 個月執行歷史
  GET  /debug/ragic-raw              — 除錯：顯示 Ragic Sheet 21 原始欄位
"""
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.full_building_maintenance import FullBldgPMBatch, FullBldgPMItem
from app.schemas.periodic_maintenance import (
    PMBatchOut, PMItemOut, PMBatchKPI, PMBatchDetail,
    CategoryStat, StatusDistItem, PMStats, PMItemUpdate,
    PMPeriodStats, PMSubPeriodBreakdown, PMIncompleteItem,
    PMYearMatrix, PMYearMatrixMonth,
)
from app.services.full_building_maintenance_sync import sync_from_ragic
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


def _calc_status(item: FullBldgPMItem, check_month: int) -> str:
    exec_months: list[int] = []
    try:
        exec_months = json.loads(item.exec_months_json or "[]")
    except Exception:
        pass

    if exec_months and check_month not in exec_months:
        return "non_current_month"
    if item.start_time and item.end_time:
        return "completed"
    if item.start_time:
        return "in_progress"
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
    return "unscheduled"


def _item_to_out(item: FullBldgPMItem, check_month: int) -> PMItemOut:
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
    )


def _calc_kpi(items: list[FullBldgPMItem], check_month: int) -> PMBatchKPI:
    statuses = [_calc_status(it, check_month) for it in items]
    current_items = [(it, s) for it, s in zip(items, statuses) if s != "non_current_month"]

    total_all   = len(items)
    completed   = sum(1 for it in items if it.start_time and it.end_time)
    in_progress = sum(1 for _, s in current_items if s == "in_progress")
    scheduled   = sum(1 for _, s in current_items if s == "scheduled")
    unscheduled = sum(1 for _, s in current_items if s == "unscheduled")
    overdue     = sum(1 for _, s in current_items if s == "overdue")
    abnormal    = sum(1 for it in items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)
    actual      = sum(_time_diff_minutes(it.start_time, it.end_time) for it in items if it.start_time and it.end_time)
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


def _calc_category_stats(items: list[FullBldgPMItem], check_month: int) -> list[CategoryStat]:
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
    'MM/DD' + 'YYYY/MM' → date(YYYY, MM, DD)
    年份從 period_month 取，月份以 scheduled_date 為準。
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
        db.query(FullBldgPMItem, FullBldgPMBatch)
        .join(
            FullBldgPMBatch,
            FullBldgPMItem.batch_ragic_id == FullBldgPMBatch.ragic_id,
        )
        .all()
    )

    prev_carry_over_list: list[dict] = []
    period_items_list:    list[dict] = []

    for item, batch in rows:
        # ── 跳過 scheduled_date 空白的項目 ──
        if not item.scheduled_date:
            continue

        # ── 頻率篩選 ──
        if not _freq_match(item.frequency, frequency_type):
            continue

        # ── 僅計算本批次月份有效的項目（排除 non_current_month）──
        try:
            exec_months = json.loads(item.exec_months_json or "[]")
        except Exception:
            exec_months = []
        batch_month = int(batch.period_month.split("/")[1])
        if exec_months and batch_month not in exec_months:
            continue

        # ── 重建完整表定日期 ──
        full_date = _reconstruct_full_date(item.scheduled_date, batch.period_month)
        if full_date is None:
            continue

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
    """
    全年 12 個月矩陣統計。
    一次 JOIN 查詢撈全部有效行，再用純 Python 按月分組計算。
    """
    rows = (
        db.query(FullBldgPMItem, FullBldgPMBatch)
        .join(
            FullBldgPMBatch,
            FullBldgPMItem.batch_ragic_id == FullBldgPMBatch.ragic_id,
        )
        .all()
    )

    # 預處理：只保留有效（有表定日期 + 非 non_current_month）的行
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
        end_date = _parse_end_date(item.end_time)
        is_done  = bool(item.start_time and item.end_time)
        processed.append({
            "item":      item,
            "full_date": full_date,
            "end_date":  end_date,
            "is_done":   is_done,
        })

    # 逐月計算
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

        # 未完成備註（非空才列入）
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


def _batch_to_out(batch: FullBldgPMBatch) -> PMBatchOut:
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
@router.post("/sync", summary="從 Ragic 同步全棟例行維護資料（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_full_building_maintenance(background_tasks: BackgroundTasks):
    """手動觸發：Ragic → SQLite，立即回傳，不阻塞畫面"""
    background_tasks.add_task(sync_from_ragic)
    return {"status": "ok", "message": "同步已在背景啟動"}


# ══════════════════════════════════════════════════════════════════════════════
# GET /batches
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/batches", summary="取得全棟例行維護批次清單")
def list_batches(
    year: Optional[str] = Query(None, description="篩選年份，如 2026"),
    db:   Session = Depends(get_db),
):
    q = db.query(FullBldgPMBatch)
    if year:
        q = q.filter(FullBldgPMBatch.period_month.like(f"{year}%"))
    batches = q.order_by(FullBldgPMBatch.period_month.desc()).all()

    result = []
    for b in batches:
        items = db.query(FullBldgPMItem).filter(
            FullBldgPMItem.batch_ragic_id == b.ragic_id
        ).all()
        check_month = _get_check_month(b.period_month)
        kpi = _calc_kpi(items, check_month)
        result.append({
            "batch": _batch_to_out(b).model_dump(),
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
    batch = db.get(FullBldgPMBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    items = db.query(FullBldgPMItem).filter(
        FullBldgPMItem.batch_ragic_id == batch_id
    ).order_by(FullBldgPMItem.seq_no).all()

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
    batch = db.get(FullBldgPMBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    items = db.query(FullBldgPMItem).filter(
        FullBldgPMItem.batch_ragic_id == batch_id
    ).all()
    check_month = _get_check_month(batch.period_month)
    return _calc_kpi(items, check_month)


# ══════════════════════════════════════════════════════════════════════════════
# GET /items
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/items", summary="跨批次查詢全棟例行維護項目")
def list_items(
    batch_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    month:    Optional[int] = Query(None, ge=1, le=12),
    db:       Session = Depends(get_db),
):
    q = db.query(FullBldgPMItem)
    if batch_id:
        q = q.filter(FullBldgPMItem.batch_ragic_id == batch_id)
    if category:
        q = q.filter(FullBldgPMItem.category == category)
    items = q.order_by(
        FullBldgPMItem.batch_ragic_id,
        FullBldgPMItem.seq_no,
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

    current_batch = db.query(FullBldgPMBatch).filter(
        FullBldgPMBatch.period_month == target_ym
    ).first()

    if not current_batch and not (year or month):
        current_batch = db.query(FullBldgPMBatch).order_by(
            FullBldgPMBatch.period_month.desc()
        ).first()

    current_kpi    = None
    overdue_items: list[PMItemOut] = []
    upcoming_items: list[PMItemOut] = []
    cats:           list[CategoryStat] = []
    status_dist:    list[StatusDistItem] = []

    if current_batch:
        items = db.query(FullBldgPMItem).filter(
            FullBldgPMItem.batch_ragic_id == current_batch.ragic_id
        ).order_by(FullBldgPMItem.seq_no).all()

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
        def _dist_status(it: FullBldgPMItem) -> str | None:
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
        db.query(FullBldgPMItem, FullBldgPMBatch)
        .join(
            FullBldgPMBatch,
            FullBldgPMItem.batch_ragic_id == FullBldgPMBatch.ragic_id,
        )
        .filter(FullBldgPMItem.task_name == task_name)
        .order_by(FullBldgPMBatch.period_month.desc())
        .all()
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"找不到保養項目：{task_name}")

    first_item: FullBldgPMItem = rows[0][0]

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
# GET /period-stats/year-matrix  — 全年 12 個月矩陣統計
# ⚠️ 必須定義在 /period-stats 之前，否則 FastAPI 會誤判路徑
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats/year-matrix", summary="全年 12 個月矩陣統計", response_model=PMYearMatrix)
def get_period_stats_year_matrix(
    year:           Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db:             Session = Depends(get_db),
):
    """
    一次回傳指定年份全部 12 個月的統計矩陣。
    前端以「月份為欄、指標為列」的表格呈現。
    """
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
# GET /calendar  — 月曆格（類別 × 日期）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/calendar", summary="全棟例行維護月曆格（類別 × 日）")
def get_calendar(
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

    batch = db.query(FullBldgPMBatch).filter(
        FullBldgPMBatch.period_month == target_ym
    ).first()

    # 已知類別順序
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

    items = db.query(FullBldgPMItem).filter(
        FullBldgPMItem.batch_ragic_id == batch.ragic_id
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
# GET /period-stats/year-matrix/items  — 矩陣格點擊明細
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats/year-matrix/items", summary="矩陣格點擊查詢明細")
def get_year_matrix_items(
    year:           int           = Query(..., description="年份"),
    month:          int           = Query(..., description="月份（0 = 全年合計）"),
    metric:         str           = Query(..., description="prev_carry_over | prev_resolved | period_total | period_completed"),
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db:             Session = Depends(get_db),
):
    """矩陣格點擊查詢明細"""
    rows = (
        db.query(FullBldgPMItem, FullBldgPMBatch)
        .join(
            FullBldgPMBatch,
            FullBldgPMItem.batch_ragic_id == FullBldgPMBatch.ragic_id,
        )
        .filter(FullBldgPMBatch.period_month.like(f"{year}/%"))
        .all()
    )

    results = []
    for item, batch in rows:
        if not _freq_match(item.frequency, frequency_type):
            continue
        if month != 0 and not batch.period_month.endswith(f"/{str(month).zfill(2)}"):
            continue

        is_completed = bool(item.start_time and item.end_time)

        if metric == "period_total":
            pass  # 全部包含
        elif metric == "period_completed":
            if not is_completed:
                continue
        elif metric in ("prev_carry_over", "prev_resolved"):
            pass  # 簡化：月份過濾已完成，詳細邏輯依需求擴充

        results.append({
            "ragic_id":            item.ragic_id,
            "batch_ragic_id":      item.batch_ragic_id,
            "period_month":        batch.period_month,
            "category":            item.category or "",
            "task_name":           item.task_name or "",
            "frequency":           item.frequency or "",
            "scheduled_date_full": f"{batch.period_month[:4]}/{item.scheduled_date}" if item.scheduled_date else "",
            "end_time":            item.end_time or "",
            "status":              "已完成" if is_completed else ("進行中" if item.start_time else "待排程"),
            "executor_name":       item.executor_name or "",
            "result_note":         item.result_note or "",
            "abnormal_flag":       bool(item.abnormal_flag),
            "abnormal_note":       item.abnormal_note or "",
            "ragic_link":          "",
        })

    return {"total": len(results), "items": results}


# ══════════════════════════════════════════════════════════════════════════════
# GET /items/catalog  — 保養項目目錄（依頻率分類）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/items/catalog", summary="保養項目目錄（依頻率分類）")
def get_items_catalog(
    frequency_type: Optional[str] = Query(None, description="monthly | quarterly | yearly"),
    db:             Session = Depends(get_db),
):
    """
    取得保養項目目錄（不分批次），依 frequency_type 篩選。
    結果為去重後的保養項目列表，以最大 seq_no 為準。
    """
    from sqlalchemy import func as sqlfunc

    subq = (
        db.query(
            FullBldgPMItem.task_name,
            FullBldgPMItem.category,
            FullBldgPMItem.frequency,
            sqlfunc.max(FullBldgPMItem.seq_no).label("max_seq"),
        )
        .group_by(
            FullBldgPMItem.task_name,
            FullBldgPMItem.category,
            FullBldgPMItem.frequency,
        )
        .subquery()
    )

    rows = (
        db.query(FullBldgPMItem)
        .join(
            subq,
            (FullBldgPMItem.task_name   == subq.c.task_name)
            & (FullBldgPMItem.category  == subq.c.category)
            & (FullBldgPMItem.frequency == subq.c.frequency)
            & (FullBldgPMItem.seq_no    == subq.c.max_seq),
        )
        .order_by(FullBldgPMItem.category, FullBldgPMItem.seq_no)
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
            "category":          r.category or "",
            "frequency":         r.frequency or "",
            "task_name":         r.task_name or "",
            "location":          r.location or "",
            "estimated_minutes": r.estimated_minutes or 0,
            "exec_months_raw":   r.exec_months_raw or "",
        })

    return {"total": len(result), "items": result}


# ══════════════════════════════════════════════════════════════════════════════
# GET /debug/ragic-raw  — 除錯用
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/debug/ragic-raw", summary="[除錯] 顯示 Ragic Sheet 21 原始欄位 key", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_ragic_raw():
    from app.services.full_building_maintenance_sync import (
        FULL_BLDG_PM_SERVER_URL, FULL_BLDG_PM_ACCOUNT,
        FULL_BLDG_PM_JOURNAL_PATH, FULL_BLDG_PM_ITEMS_PATH,
    )

    adapter_batch = RagicAdapter(
        sheet_path=FULL_BLDG_PM_JOURNAL_PATH,
        server_url=FULL_BLDG_PM_SERVER_URL,
        account=FULL_BLDG_PM_ACCOUNT,
    )
    adapter_items = RagicAdapter(
        sheet_path=FULL_BLDG_PM_ITEMS_PATH,
        server_url=FULL_BLDG_PM_SERVER_URL,
        account=FULL_BLDG_PM_ACCOUNT,
    )

    try:
        raw_batch = await adapter_batch.fetch_all()
        raw_items = await adapter_items.fetch_all()
    except Exception as exc:
        return {"error": str(exc)}

    first_batch = next(iter(raw_batch.values()), {}) if raw_batch else {}
    first_item  = next(iter(raw_items.values()), {}) if raw_items else {}

    return {
        "sheet21_batch": {
            "total_records":       len(raw_batch),
            "record_ids":          list(raw_batch.keys()),
            "first_record_fields": first_batch,
        },
        "sheet21_items": {
            "total_records":       len(raw_items),
            "record_ids":          list(raw_items.keys()),
            "first_record_fields": first_item,
        },
    }
