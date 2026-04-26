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
  PATCH /items/{item_id}             — Portal 回填（執行時間/異常等）
"""
import json
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
        start_time        = item.start_time,
        end_time          = item.end_time,
        # 動態計算：啟+迄均有值 = 完成（與 _calc_status 邏輯一致，不依賴 DB 舊存值）
        is_completed      = bool(item.start_time and item.end_time),
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
def get_stats(db: Session = Depends(get_db)):
    today = date.today()
    current_ym = today.strftime("%Y/%m")
    check_month = today.month

    # 本月批次
    current_batch = db.query(PeriodicMaintenanceBatch).filter(
        PeriodicMaintenanceBatch.period_month == current_ym
    ).first()

    # 若無本月批次，取最新批次
    if not current_batch:
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

        # 今日 / 本週即將到期（已排定但 start_time 為空）
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
