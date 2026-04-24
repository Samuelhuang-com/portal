"""
商場管理統計 Dashboard  API Router
Prefix: /api/v1/mall/dashboard

端點：
  GET /summary  — KPI 摘要（今日巡檢 + 本月週期保養）
  GET /issues   — 異常 / 未完成 / 逾期清單
  GET /trend    — 近 7 / 30 日趨勢資料
"""
from datetime import date, timedelta, datetime, timezone
from app.core.time import twnow
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.b1f_inspection import B1FInspectionBatch, B1FInspectionItem
from app.models.b2f_inspection import B2FInspectionBatch, B2FInspectionItem
from app.models.rf_inspection  import RFInspectionBatch,  RFInspectionItem
from app.models.mall_periodic_maintenance import (
    MallPeriodicMaintenanceBatch, MallPeriodicMaintenanceItem,
)
from app.schemas.mall_dashboard import (
    DashboardSummary, InspectionSummary, FloorInspectionStats, PMSummary,
    IssueItem, IssueListResponse, TrendPoint, DashboardTrend,
)

router = APIRouter()

# ── 樓層設定 ──────────────────────────────────────────────────────────────────
FLOOR_CONFIGS = [
    ("b1f", "B1F", B1FInspectionBatch, B1FInspectionItem),
    ("b2f", "B2F", B2FInspectionBatch, B2FInspectionItem),
    ("rf",  "RF",  RFInspectionBatch,  RFInspectionItem),
]


# ── 輔助函式 ──────────────────────────────────────────────────────────────────

def _parse_date_str(s: Optional[str]) -> date:
    """解析 YYYY/MM/DD 或 YYYY-MM-DD；失敗時回傳今日。"""
    if not s:
        return date.today()
    try:
        clean = s.replace("-", "/").strip()
        y, m, d_ = clean.split("/")
        return date(int(y), int(m), int(d_))
    except Exception:
        return date.today()


def _floor_stats(
    db: Session,
    BatchModel, ItemModel,
    floor_key: str,
    floor_label: str,
    target_date_str: str,
) -> FloorInspectionStats:
    """計算指定日期、指定樓層的巡檢統計。"""
    batches = db.query(BatchModel).filter(
        BatchModel.inspection_date == target_date_str
    ).all()

    total = normal = abnormal = pending = unchecked = 0
    for b in batches:
        items = db.query(ItemModel).filter(
            ItemModel.batch_ragic_id == b.ragic_id
        ).all()
        for it in items:
            total += 1
            if   it.result_status == "normal":    normal    += 1
            elif it.result_status == "abnormal":  abnormal  += 1
            elif it.result_status == "pending":   pending   += 1
            else:                                 unchecked += 1

    checked = normal + abnormal + pending
    return FloorInspectionStats(
        floor           = floor_key,
        floor_label     = floor_label,
        batches         = len(batches),
        total_items     = total,
        normal_items    = normal,
        abnormal_items  = abnormal,
        pending_items   = pending,
        unchecked_items = unchecked,
        checked_items   = checked,
        completion_rate = round(checked / total * 100, 1) if total > 0 else 0.0,
        normal_rate     = round(normal  / checked * 100, 1) if checked > 0 else 0.0,
    )


def _floor_stats_range(
    db: Session,
    BatchModel, ItemModel,
    start_str: str,
    end_str: str,
) -> dict:
    """計算日期區間的樓層巡檢統計（供趨勢使用）。"""
    batches = db.query(BatchModel).filter(
        BatchModel.inspection_date >= start_str,
        BatchModel.inspection_date <= end_str,
    ).all()

    total = normal = abnormal = pending = unchecked = 0
    for b in batches:
        items = db.query(ItemModel).filter(
            ItemModel.batch_ragic_id == b.ragic_id
        ).all()
        for it in items:
            total += 1
            if   it.result_status == "normal":    normal    += 1
            elif it.result_status == "abnormal":  abnormal  += 1
            elif it.result_status == "pending":   pending   += 1
            else:                                 unchecked += 1

    checked = normal + abnormal + pending
    return {
        "total":     total,
        "checked":   checked,
        "abnormal":  abnormal + pending,
        "completion_rate": round(checked / total * 100, 1) if total > 0 else 0.0,
        "has_data":  total > 0,
    }


# ── /summary ──────────────────────────────────────────────────────────────────

@router.get("/summary", summary="取得 Dashboard KPI 摘要", response_model=DashboardSummary)
def get_summary(
    target_date: Optional[str] = Query(None, description="查詢日期 YYYY/MM/DD，預設今日"),
    db: Session = Depends(get_db),
):
    target      = _parse_date_str(target_date)
    target_str  = target.strftime("%Y/%m/%d")
    period_month = target.strftime("%Y/%m")
    today_month  = date.today().strftime("%Y/%m")

    # ── 各樓層巡檢統計 ────────────────────────────────────────────────────────
    floor_stats_list = [
        _floor_stats(db, BM, IM, fk, fl, target_str)
        for fk, fl, BM, IM in FLOOR_CONFIGS
    ]

    total_batches   = sum(f.batches         for f in floor_stats_list)
    total_items     = sum(f.total_items     for f in floor_stats_list)
    checked_items   = sum(f.checked_items   for f in floor_stats_list)
    unchecked_items = sum(f.unchecked_items for f in floor_stats_list)
    abnormal_items  = sum(f.abnormal_items + f.pending_items for f in floor_stats_list)

    inspection = InspectionSummary(
        target_date     = target_str,
        total_batches   = total_batches,
        total_items     = total_items,
        checked_items   = checked_items,
        unchecked_items = unchecked_items,
        abnormal_items  = abnormal_items,
        completion_rate = round(checked_items / total_items * 100, 1) if total_items > 0 else 0.0,
        by_floor        = floor_stats_list,
    )

    # ── 商場週期保養統計（本月 + 過期）────────────────────────────────────────
    # 本月批次
    cur_batches = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month == period_month
    ).all()
    cur_ids = [b.ragic_id for b in cur_batches]

    cur_items = (
        db.query(MallPeriodicMaintenanceItem)
        .filter(MallPeriodicMaintenanceItem.batch_ragic_id.in_(cur_ids))
        .all()
    ) if cur_ids else []

    pm_total     = len(cur_items)
    pm_completed = sum(1 for it in cur_items if it.is_completed)
    pm_incomplete = pm_total - pm_completed
    pm_abnormal  = sum(1 for it in cur_items if it.abnormal_flag)

    # 逾期 = 過去月份批次中，尚未完成的項目
    past_batches = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month < today_month
    ).all()
    past_ids = [b.ragic_id for b in past_batches]
    pm_overdue = (
        db.query(MallPeriodicMaintenanceItem)
        .filter(
            MallPeriodicMaintenanceItem.batch_ragic_id.in_(past_ids),
            MallPeriodicMaintenanceItem.is_completed == False,  # noqa: E712
        )
        .count()
    ) if past_ids else 0

    pm = PMSummary(
        period_month     = period_month,
        total_items      = pm_total,
        completed_items  = pm_completed,
        incomplete_items = pm_incomplete,
        overdue_items    = pm_overdue,
        abnormal_items   = pm_abnormal,
        completion_rate  = round(pm_completed / pm_total * 100, 1) if pm_total > 0 else 0.0,
    )

    return DashboardSummary(
        inspection   = inspection,
        pm           = pm,
        generated_at = twnow().strftime("%Y/%m/%d %H:%M"),
    )


# ── /issues ───────────────────────────────────────────────────────────────────

@router.get("/issues", summary="取得異常/未完成/逾期清單", response_model=IssueListResponse)
def get_issues(
    issue_type:  Optional[str] = Query(None, description="inspection|pm|all"),
    floor:       Optional[str] = Query(None, description="b1f|b2f|rf|all"),
    status:      Optional[str] = Query(None, description="abnormal|pending|unchecked|overdue|all"),
    start_date:  Optional[str] = Query(None),
    end_date:    Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    today       = date.today()
    start       = _parse_date_str(start_date) if start_date else (today - timedelta(days=7))
    end         = _parse_date_str(end_date)   if end_date   else today
    start_str   = start.strftime("%Y/%m/%d")
    end_str     = end.strftime("%Y/%m/%d")
    today_month = today.strftime("%Y/%m")

    items: list[IssueItem] = []

    # ── 巡檢異常 / 未完成 ──────────────────────────────────────────────────────
    if issue_type in (None, "inspection", "all"):
        want_floors = [
            (fk, fl, BM, IM) for fk, fl, BM, IM in FLOOR_CONFIGS
            if floor in (None, "all", fk)
        ]
        for floor_key, floor_label, BatchModel, ItemModel in want_floors:
            batches = db.query(BatchModel).filter(
                BatchModel.inspection_date >= start_str,
                BatchModel.inspection_date <= end_str,
            ).order_by(BatchModel.inspection_date.desc()).all()

            for b in batches:
                q = db.query(ItemModel).filter(
                    ItemModel.batch_ragic_id == b.ragic_id
                )
                if status in (None, "all"):
                    q = q.filter(
                        ItemModel.result_status.in_(["abnormal", "pending", "unchecked"])
                    )
                elif status in ("abnormal", "pending"):
                    q = q.filter(ItemModel.result_status.in_(["abnormal", "pending"]))
                elif status == "unchecked":
                    q = q.filter(ItemModel.result_status == "unchecked")
                else:
                    continue  # 其他狀態不屬於巡檢問題

                STATUS_LABEL_MAP = {
                    "abnormal":  "異常",
                    "pending":   "待處理",
                    "unchecked": "未巡檢",
                }
                for it in q.all():
                    items.append(IssueItem(
                        id           = it.ragic_id,
                        issue_date   = b.inspection_date,
                        issue_type   = "inspection",
                        floor        = floor_label,
                        item_name    = it.item_name,
                        status       = it.result_status,
                        status_label = STATUS_LABEL_MAP.get(it.result_status, it.result_status),
                        responsible  = b.inspector_name or "",
                        note         = it.result_raw or "",
                        batch_id     = b.ragic_id,
                    ))

    # ── 保養逾期 / 異常 ────────────────────────────────────────────────────────
    if issue_type in (None, "pm", "all") and floor in (None, "all"):
        pm_status_filter = status in (None, "all", "overdue")

        if pm_status_filter:
            # 逾期 = 過去月份中未完成的
            past_batches = db.query(MallPeriodicMaintenanceBatch).filter(
                MallPeriodicMaintenanceBatch.period_month < today_month
            ).all()
            for pb in past_batches:
                overdue_items = db.query(MallPeriodicMaintenanceItem).filter(
                    MallPeriodicMaintenanceItem.batch_ragic_id == pb.ragic_id,
                    MallPeriodicMaintenanceItem.is_completed == False,  # noqa: E712
                ).all()
                for it in overdue_items:
                    items.append(IssueItem(
                        id           = it.ragic_id,
                        issue_date   = pb.period_month,
                        issue_type   = "pm",
                        floor        = "商場",
                        item_name    = it.task_name,
                        status       = "overdue",
                        status_label = "逾期",
                        responsible  = it.executor_name or it.scheduler_name or "",
                        note         = it.abnormal_note or "",
                        batch_id     = pb.ragic_id,
                    ))

        # 本月異常
        if status in (None, "all", "abnormal"):
            cur_batches = db.query(MallPeriodicMaintenanceBatch).filter(
                MallPeriodicMaintenanceBatch.period_month == today_month
            ).all()
            for cb in cur_batches:
                abn_items = db.query(MallPeriodicMaintenanceItem).filter(
                    MallPeriodicMaintenanceItem.batch_ragic_id == cb.ragic_id,
                    MallPeriodicMaintenanceItem.abnormal_flag == True,  # noqa: E712
                ).all()
                for it in abn_items:
                    items.append(IssueItem(
                        id           = f"pm_abn_{it.ragic_id}",
                        issue_date   = cb.period_month,
                        issue_type   = "pm",
                        floor        = "商場",
                        item_name    = it.task_name,
                        status       = "abnormal",
                        status_label = "異常",
                        responsible  = it.executor_name or it.scheduler_name or "",
                        note         = it.abnormal_note or "",
                        batch_id     = cb.ragic_id,
                    ))

    # 依日期排序（最新優先）
    items.sort(key=lambda x: x.issue_date, reverse=True)

    return IssueListResponse(items=items, total=len(items))


# ── /trend ────────────────────────────────────────────────────────────────────

@router.get("/trend", summary="取得近 N 日巡檢趨勢", response_model=DashboardTrend)
def get_trend(
    days: int = Query(7, ge=3, le=30, description="趨勢天數"),
    db: Session = Depends(get_db),
):
    today = date.today()
    trend_points: list[TrendPoint] = []

    for i in range(days - 1, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        floor_data: dict[str, dict] = {}
        has_data_any = False

        for floor_key, _, BatchModel, ItemModel in FLOOR_CONFIGS:
            stats = _floor_stats_range(db, BatchModel, ItemModel, d_str, d_str)
            floor_data[floor_key] = stats
            if stats["has_data"]:
                has_data_any = True

        total_abn = sum(v["abnormal"] for v in floor_data.values())

        trend_points.append(TrendPoint(
            date           = d_str,
            b1f_completion = floor_data["b1f"]["completion_rate"],
            b2f_completion = floor_data["b2f"]["completion_rate"],
            rf_completion  = floor_data["rf"]["completion_rate"],
            b1f_abnormal   = floor_data["b1f"]["abnormal"],
            b2f_abnormal   = floor_data["b2f"]["abnormal"],
            rf_abnormal    = floor_data["rf"]["abnormal"],
            total_abnormal = total_abn,
            has_data       = has_data_any,
        ))

    return DashboardTrend(trend=trend_points, days=days)
