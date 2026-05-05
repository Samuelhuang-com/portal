"""
週期保養表 API Router
Prefix: /api/v1/periodic-maintenance

端點：
  POST /sync                         — 手動從 Ragic 同步
  GET  /batches                      — 批次清單（年份篩選）
  GET  /batches/{batch_id}           — 單筆批次 + 所有項目 + KPI
  GET  /batches/{batch_id}/items     — 該批次項目（含狀態篩選）
  GET  /batches/{batch_id}/kpi       — 批次 KPI 統計
  GET  /items                        — 所有項目跨批次查詢
  GET  /stats                        — 全站統計（Dashboard 資料來源）
  GET  /period-stats                 — 週期統計（月/季/年）
  PATCH /items/{item_id}             — Portal 回填（執行時間/異常等）
"""
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.periodic_maintenance import PeriodicMaintenanceBatch, PeriodicMaintenanceItem
from app.schemas.periodic_maintenance import (
    PMBatchOut, PMItemOut, PMBatchKPI, PMBatchDetail,
    CategoryStat, StatusDistItem, PMStats, PMItemUpdate,
    PMPeriodStats, PMSubPeriodBreakdown, PMIncompleteItem,
    PMYearMatrix, PMYearMatrixMonth,
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
    1. 非本月 — exec_months_json 有值，且 check_month 不在清單中
    2. 已完成 — 保養時間啟（start_time）AND 保養時間迄（end_time）均有值
               ※ 與表格「完成」欄（is_completed）定義一致
    3. 進行中 — 保養時間啟有值，但無迄（仍在執行中）
    4. 逾期   — 排定日期（scheduled_date）有值，且該日期已過今天
    5. 已排定 — 排定日期有值，尚未到期
    6. 未排定 — 以上皆無
    """
    exec_months: list[int] = []
    try:
        exec_months = json.loads(item.exec_months_json or "[]")
    except Exception:
        pass

    # 1. 非本月：exec_months 有值且當月不在清單中
    if exec_months and check_month not in exec_months:
        return "non_current_month"

    # 2. 已完成：保養時間啟 AND 保養時間迄 均有值（與 is_completed 欄位定義相同）
    if item.start_time and item.end_time:
        return "completed"

    # 3. 進行中：保養時間啟有值但無迄
    if item.start_time:
        return "in_progress"

    # 4. 逾期 / 5. 已排定：排定日期有值
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
    abnormal    = sum(1 for it in items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)
    # 優先使用 Ragic「工時計算」欄位（ragic_work_minutes）；
    # 若該欄位為 None（舊資料或 Ragic 未填），fallback 到 end_time - start_time 計算
    actual      = sum(
        it.ragic_work_minutes if it.ragic_work_minutes is not None
        else _time_diff_minutes(it.start_time, it.end_time)
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
        # ── 跳過 scheduled_date 空白的項目 ──
        if not item.scheduled_date:
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


_MONTH_LABELS_ZH = ["1月","2月","3月","4月","5月","6月",
                    "7月","8月","9月","10月","11月","12月"]


def _calc_year_matrix(db: Session, year: int) -> PMYearMatrix:
    """
    全年 12 個月矩陣統計。
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
        .all()
    )

    # ── 預處理：只保留有效（有表定日期 + 非 non_current_month）的行 ──────────
    processed: list[dict] = []
    for item, batch in rows:
        if not item.scheduled_date:
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

            # 本期項目
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
            if not x["is_done"] and x["item"].result_note
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


# ══════════════════════════════════════════════════════════════════════════════
# POST /sync
# ══════════════════════════════════════════════════════════════════════════════
@router.post("/sync", summary="從 Ragic 同步週期保養資料（背景執行）", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def sync_periodic_maintenance(background_tasks: BackgroundTasks):
    """手動觸發：Ragic Sheet 6 + Sheet 8 → SQLite，立即回傳，不阻塞畫面"""
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

    result = []
    for b in batches:
        items = db.query(PeriodicMaintenanceItem).filter(
            PeriodicMaintenanceItem.batch_ragic_id == b.ragic_id
        ).all()
        check_month = _get_check_month(b.period_month)
        kpi = _calc_kpi(items, check_month)
        result.append({
            "batch": PMBatchOut.model_validate(b).model_dump(),
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
    year: Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    db:   Session = Depends(get_db),
):
    """
    一次回傳指定年份全部 12 個月的統計矩陣。
    前端以「月份為欄、指標為列」的表格呈現。
    單次 DB 查詢，效率優於逐月呼叫 /period-stats。
    """
    target_year = year or date.today().year
    return _calc_year_matrix(db, target_year)


# ══════════════════════════════════════════════════════════════════════════════
# GET /period-stats  — 週期統計（月 / 季 / 年）
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/period-stats", summary="週期統計（月/季/年）", response_model=PMPeriodStats)
def get_period_stats(
    period_type: str           = Query("month", description="month | quarter | year"),
    year:        Optional[int] = Query(None, description="年份，如 2026；預設今年"),
    month:       Optional[int] = Query(None, ge=1, le=12, description="月份（period_type=month 時使用）"),
    quarter:     Optional[int] = Query(None, ge=1, le=4,  description="季度 1-4（period_type=quarter 時使用）"),
    db:          Session = Depends(get_db),
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
    core = _calc_period_stats_core(db, p_start, p_end, prev_end)
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
# GET /debug/ragic-raw  — 除錯用：直接回傳 Ragic 原始資料
# ══════════════════════════════════════════════════════════════════════════════
@router.get("/debug/ragic-raw", summary="[除錯] 顯示 Ragic Sheet 8 原始欄位 key", dependencies=[Depends(require_roles("system_admin", "module_manager"))])
async def debug_ragic_raw():
    """
    直接向 Ragic 拉取 Sheet 8（附表），回傳原始 dict 的欄位名稱與第一筆值。
    用於確認 Ragic 實際回傳的 field key 是否與同步服務的常數相符。
    """
    from app.services.periodic_maintenance_sync import PM_SERVER_URL, PM_ACCOUNT, PM_ITEMS_PATH, PM_JOURNAL_PATH

    adapter_items = RagicAdapter(
        sheet_path=PM_ITEMS_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )
    adapter_batch = RagicAdapter(
        sheet_path=PM_JOURNAL_PATH,
        server_url=PM_SERVER_URL,
        account=PM_ACCOUNT,
    )

    try:
        raw_items = await adapter_items.fetch_all()
        raw_batch = await adapter_batch.fetch_all()
    except Exception as exc:
        return {"error": str(exc)}

    # 取第一筆記錄的所有 key（含值）
    first_item = next(iter(raw_items.values()), {}) if raw_items else {}
    first_batch = next(iter(raw_batch.values()), {}) if raw_batch else {}

    return {
        "sheet8_items": {
            "total_records": len(raw_items),
            "record_ids": list(raw_items.keys()),
            "first_record_fields": first_item,
        },
        "sheet6_batch": {
            "total_records": len(raw_batch),
            "record_ids": list(raw_batch.keys()),
            "first_record_fields": first_batch,
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
            cell = grid[cat][d]
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
        # 只輸出該類別在這個月有資料，或固定類別（始終輸出，讓前端顯示空列）
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
