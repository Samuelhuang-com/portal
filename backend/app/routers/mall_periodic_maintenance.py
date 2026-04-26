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
  GET  /debug/ragic-raw              — 除錯：顯示 Ragic Sheet 18 原始欄位
"""
import json
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.mall_periodic_maintenance import MallPeriodicMaintenanceBatch, MallPeriodicMaintenanceItem
from app.schemas.periodic_maintenance import (
    PMBatchOut, PMItemOut, PMBatchKPI, PMBatchDetail,
    CategoryStat, StatusDistItem, PMStats, PMItemUpdate,
)
from app.services.mall_periodic_maintenance_sync import sync_from_ragic
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

def _calc_status(item: MallPeriodicMaintenanceItem, check_month: int) -> str:
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
    abnormal    = sum(1 for it in items if it.abnormal_flag)
    planned     = sum(it.estimated_minutes for it, s in current_items)
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
def get_stats(db: Session = Depends(get_db)):
    today = date.today()
    current_ym  = today.strftime("%Y/%m")
    check_month = today.month

    current_batch = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month == current_ym
    ).first()

    if not current_batch:
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

        upcoming_items = []
        for it in items:
            s = _calc_status(it, check_month)
            if s == "scheduled" and it.scheduled_date:
                try:
                    sched = datetime.strptime(
                        f"{today.year}/{it.scheduled_date}", "%Y/%m/%d"
                    ).date()
                    days_left = (sched - today).days
                    if 0 <= days_left <= 7:
                        upcoming_items.append(_item_to_out(it, check_month))
                except Exception:
                    pass
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
