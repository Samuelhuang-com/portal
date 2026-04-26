"""
行事曆聚合 API Router
Prefix: /api/v1/calendar

端點：
  GET  /events           — 聚合所有跨模組事件（依日期範圍 + 類型篩選）
  GET  /today            — 今日摘要 KPI
  GET  /custom           — 自訂事件清單
  POST /custom           — 新增自訂事件
  PUT  /custom/{id}      — 更新自訂事件
  DELETE /custom/{id}    — 刪除自訂事件

事件來源（第一階段已整合）：
  hotel_pm    — 飯店週期保養（pm_batch_item.scheduled_date + pm_batch.period_month）
  mall_pm     — 商場週期保養（mall_pm_batch_item.scheduled_date + mall_pm_batch.period_month）
  security    — 保全巡檢（security_patrol_batch.inspection_date）
  inspection  — 工務巡檢（b1f/b2f/rf/b4f_inspection_batch.inspection_date）
  approval    — 簽核管理（approvals.submitted_at）
  memo        — 公告牆（memos.created_at）
  custom      — 自訂事件（calendar_custom_events）

注意：附件舊 DB 連線一概不採用，僅使用 Portal 現有 SQLAlchemy Session (get_db)。
"""
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.calendar_event import CalendarCustomEvent
from app.models.periodic_maintenance import PeriodicMaintenanceBatch, PeriodicMaintenanceItem
from app.models.mall_periodic_maintenance import (
    MallPeriodicMaintenanceBatch,
    MallPeriodicMaintenanceItem,
)
from app.models.security_patrol import SecurityPatrolBatch
from app.models.b1f_inspection import B1FInspectionBatch
from app.models.b2f_inspection import B2FInspectionBatch
from app.models.rf_inspection import RFInspectionBatch
from app.models.b4f_inspection import B4FInspectionBatch
from app.models.approval import Approval
from app.models.memo import Memo
from app.schemas.calendar import (
    CalendarEventOut,
    CalendarEventsResponse,
    TodaySummary,
    CustomEventCreate,
    CustomEventUpdate,
    CustomEventOut,
    EVENT_TYPE_COLORS,
    EVENT_TYPE_LABELS,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ─────────────────────────────────────────────────────────────────────────────
# 日期工具
# ─────────────────────────────────────────────────────────────────────────────

def _slash_to_date(s: str) -> Optional[date]:
    """YYYY/MM/DD 或 YYYY-MM-DD → date；失敗回傳 None"""
    if not s:
        return None
    try:
        parts = s.replace("-", "/").split("/")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def _iso_to_date(s: str) -> Optional[date]:
    """YYYY-MM-DD → date；失敗回傳 None"""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _date_to_iso(d: Optional[date]) -> str:
    if d is None:
        return ""
    return d.isoformat()


def _pm_item_full_date(period_month: str, scheduled_date: str) -> Optional[date]:
    """
    飯店/商場週期保養項目的完整日期計算：
      period_month = "2026/04"   (YYYY/MM)
      scheduled_date = "04/23"  (MM/DD)
    → full = "2026/" + "04/23" = "2026/04/23"
    → return date(2026, 4, 23)
    """
    if not period_month or not scheduled_date:
        return None
    try:
        # period_month[:5] = "2026/"
        full = period_month[:5] + scheduled_date
        return _slash_to_date(full)
    except Exception:
        return None


def _should_include(event_type: str, types_filter: Optional[str]) -> bool:
    """判斷是否需要收集此類型事件"""
    if not types_filter:
        return True
    return event_type in [t.strip() for t in types_filter.split(",")]


# ─────────────────────────────────────────────────────────────────────────────
# 各模組事件收集函式
# ─────────────────────────────────────────────────────────────────────────────

def _collect_hotel_pm(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集飯店週期保養事件（pm_batch + pm_batch_item）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["hotel_pm"]
    label = EVENT_TYPE_LABELS["hotel_pm"]

    # 以 period_month 範圍篩選批次（月份字串 "2026/04" 可直接比較）
    start_month = start.strftime("%Y/%m")
    end_month   = end.strftime("%Y/%m")

    batches = db.query(PeriodicMaintenanceBatch).filter(
        PeriodicMaintenanceBatch.period_month >= start_month,
        PeriodicMaintenanceBatch.period_month <= end_month,
    ).all()

    for batch in batches:
        items = db.query(PeriodicMaintenanceItem).filter(
            PeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id,
            PeriodicMaintenanceItem.scheduled_date != "",
        ).all()

        for item in items:
            item_date = _pm_item_full_date(batch.period_month, item.scheduled_date)
            if not item_date or not (start <= item_date <= end):
                continue

            if item.is_completed:
                status, status_label = "completed", "已完成"
            elif item.abnormal_flag:
                status, status_label = "abnormal", "異常"
            else:
                status, status_label = "pending", "待執行"

            events.append(CalendarEventOut(
                id           = f"hotel_pm_{item.ragic_id}",
                title        = f"[飯店保養] {item.task_name}",
                start        = _date_to_iso(item_date),
                all_day      = True,
                event_type   = "hotel_pm",
                module_label = label,
                source_id    = item.ragic_id,
                status       = status,
                status_label = status_label,
                responsible  = item.executor_name or item.scheduler_name,
                description  = f"{item.category} | {item.location}",
                deep_link    = "/hotel/periodic-maintenance",
                color        = color,
            ))
    return events


def _collect_mall_pm(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集商場週期保養事件（mall_pm_batch + mall_pm_batch_item）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["mall_pm"]
    label = EVENT_TYPE_LABELS["mall_pm"]

    start_month = start.strftime("%Y/%m")
    end_month   = end.strftime("%Y/%m")

    batches = db.query(MallPeriodicMaintenanceBatch).filter(
        MallPeriodicMaintenanceBatch.period_month >= start_month,
        MallPeriodicMaintenanceBatch.period_month <= end_month,
    ).all()

    for batch in batches:
        items = db.query(MallPeriodicMaintenanceItem).filter(
            MallPeriodicMaintenanceItem.batch_ragic_id == batch.ragic_id,
            MallPeriodicMaintenanceItem.scheduled_date != "",
        ).all()

        for item in items:
            item_date = _pm_item_full_date(batch.period_month, item.scheduled_date)
            if not item_date or not (start <= item_date <= end):
                continue

            if item.is_completed:
                status, status_label = "completed", "已完成"
            elif item.abnormal_flag:
                status, status_label = "abnormal", "異常"
            else:
                status, status_label = "pending", "待執行"

            events.append(CalendarEventOut(
                id           = f"mall_pm_{item.ragic_id}",
                title        = f"[商場保養] {item.task_name}",
                start        = _date_to_iso(item_date),
                all_day      = True,
                event_type   = "mall_pm",
                module_label = label,
                source_id    = item.ragic_id,
                status       = status,
                status_label = status_label,
                responsible  = item.executor_name or item.scheduler_name,
                description  = f"{item.category} | {item.location}",
                deep_link    = "/mall/periodic-maintenance",
                color        = color,
            ))
    return events


def _collect_security_patrol(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集保全巡檢事件（security_patrol_batch）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["security"]
    label = EVENT_TYPE_LABELS["security"]

    start_str = start.strftime("%Y/%m/%d")
    end_str   = end.strftime("%Y/%m/%d")

    batches = db.query(SecurityPatrolBatch).filter(
        SecurityPatrolBatch.inspection_date >= start_str,
        SecurityPatrolBatch.inspection_date <= end_str,
    ).all()

    # 同日同 sheet 只顯示一筆（避免重複）
    seen: set = set()
    for b in batches:
        key = (b.inspection_date, b.sheet_key)
        if key in seen:
            continue
        seen.add(key)

        item_date = _slash_to_date(b.inspection_date)
        if not item_date:
            continue

        events.append(CalendarEventOut(
            id           = f"security_{b.sheet_key}_{b.inspection_date.replace('/', '')}",
            title        = f"[保全] {b.sheet_key} 巡檢",
            start        = _date_to_iso(item_date),
            all_day      = True,
            event_type   = "security",
            module_label = label,
            source_id    = b.ragic_id,
            status       = "completed",
            status_label = "已巡檢",
            responsible  = b.inspector_name or "",
            description  = f"巡檢日期：{b.inspection_date}",
            deep_link    = f"/security/patrol/{b.sheet_key}",
            color        = color,
        ))
    return events


def _collect_inspection(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集工務巡檢事件（B1F / B2F / RF / B4F）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["inspection"]
    label = EVENT_TYPE_LABELS["inspection"]

    start_str = start.strftime("%Y/%m/%d")
    end_str   = end.strftime("%Y/%m/%d")

    INSPECTION_CONFIGS = [
        ("b1f", "B1F 工務巡檢", B1FInspectionBatch, "/mall/b1f-inspection"),
        ("b2f", "B2F 工務巡檢", B2FInspectionBatch, "/mall/b2f-inspection"),
        ("rf",  "RF 工務巡檢",  RFInspectionBatch,  "/mall/rf-inspection"),
        ("b4f", "B4F 工務巡檢", B4FInspectionBatch, "/mall/b4f-inspection"),
    ]

    for floor_key, floor_label, BatchModel, deep_link in INSPECTION_CONFIGS:
        try:
            batches = db.query(BatchModel).filter(
                BatchModel.inspection_date >= start_str,
                BatchModel.inspection_date <= end_str,
            ).all()
        except Exception:
            continue

        seen_dates: set = set()
        for b in batches:
            if b.inspection_date in seen_dates:
                continue
            seen_dates.add(b.inspection_date)

            item_date = _slash_to_date(b.inspection_date)
            if not item_date:
                continue

            events.append(CalendarEventOut(
                id           = f"inspection_{floor_key}_{b.inspection_date.replace('/', '')}",
                title        = f"[工務巡檢] {floor_label}",
                start        = _date_to_iso(item_date),
                all_day      = True,
                event_type   = "inspection",
                module_label = label,
                source_id    = b.ragic_id,
                status       = "completed",
                status_label = "已巡檢",
                responsible  = getattr(b, "inspector_name", "") or "",
                description  = f"{floor_label}，巡檢日期：{b.inspection_date}",
                deep_link    = deep_link,
                color        = color,
            ))
    return events


def _collect_approvals(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集簽核事件（approvals.submitted_at）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["approval"]
    label = EVENT_TYPE_LABELS["approval"]

    start_dt = datetime(start.year, start.month, start.day, 0, 0, 0)
    end_dt   = datetime(end.year,   end.month,   end.day,   23, 59, 59)

    approvals = db.query(Approval).filter(
        Approval.submitted_at >= start_dt,
        Approval.submitted_at <= end_dt,
    ).all()

    STATUS_MAP = {
        "pending":  ("pending",   "待簽核"),
        "approved": ("completed", "已核准"),
        "rejected": ("abnormal",  "已退回"),
    }

    for ap in approvals:
        status, slabel = STATUS_MAP.get(ap.status, ("pending", ap.status))
        start_iso = (
            ap.submitted_at.strftime("%Y-%m-%d")
            if ap.submitted_at else _date_to_iso(start)
        )

        events.append(CalendarEventOut(
            id           = f"approval_{ap.id}",
            title        = f"[簽核] {ap.subject}",
            start        = start_iso,
            all_day      = True,
            event_type   = "approval",
            module_label = label,
            source_id    = ap.id,
            status       = status,
            status_label = slabel,
            responsible  = ap.requester,
            description  = f"申請人：{ap.requester}｜部門：{ap.requester_dept}",
            deep_link    = f"/approvals/{ap.id}",
            color        = color,
        ))
    return events


def _collect_memos(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集公告牆事件（memos.created_at）"""
    events: List[CalendarEventOut] = []
    color = EVENT_TYPE_COLORS["memo"]
    label = EVENT_TYPE_LABELS["memo"]

    start_dt = datetime(start.year, start.month, start.day, 0, 0, 0)
    end_dt   = datetime(end.year,   end.month,   end.day,   23, 59, 59)

    memos = db.query(Memo).filter(
        Memo.created_at >= start_dt,
        Memo.created_at <= end_dt,
    ).all()

    for memo in memos:
        start_iso = (
            memo.created_at.strftime("%Y-%m-%d")
            if memo.created_at else _date_to_iso(start)
        )
        events.append(CalendarEventOut(
            id           = f"memo_{memo.id}",
            title        = f"[公告] {memo.title}",
            start        = start_iso,
            all_day      = True,
            event_type   = "memo",
            module_label = label,
            source_id    = memo.id,
            status       = "completed",
            status_label = "已發布",
            responsible  = memo.author,
            description  = f"發文者：{memo.author}",
            deep_link    = f"/memos/{memo.id}",
            color        = color,
        ))
    return events


def _collect_custom(db: Session, start: date, end: date) -> List[CalendarEventOut]:
    """收集使用者自訂事件（calendar_custom_events）"""
    events: List[CalendarEventOut] = []
    label = EVENT_TYPE_LABELS["custom"]

    start_iso = _date_to_iso(start)
    end_iso   = _date_to_iso(end)

    customs = db.query(CalendarCustomEvent).filter(
        CalendarCustomEvent.start_date >= start_iso,
        CalendarCustomEvent.start_date <= end_iso,
    ).all()

    for ev in customs:
        events.append(CalendarEventOut(
            id           = f"custom_{ev.id}",
            title        = ev.title,
            start        = ev.start_date,
            end          = ev.end_date or None,
            all_day      = ev.all_day,
            event_type   = "custom",
            module_label = label,
            source_id    = ev.id,
            status       = "pending",
            status_label = "自訂",
            responsible  = ev.responsible,
            description  = ev.description,
            deep_link    = "",
            color        = ev.color or EVENT_TYPE_COLORS["custom"],
        ))
    return events


# ─────────────────────────────────────────────────────────────────────────────
# /events — 聚合查詢
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/events", summary="取得行事曆聚合事件", response_model=CalendarEventsResponse)
def get_calendar_events(
    start:  str           = Query(..., description="查詢起始日期 YYYY-MM-DD"),
    end:    str           = Query(..., description="查詢結束日期 YYYY-MM-DD"),
    types:  Optional[str] = Query(
        None,
        description="事件類型篩選，逗號分隔：hotel_pm,mall_pm,security,inspection,approval,memo,custom"
    ),
    db: Session = Depends(get_db),
):
    start_date = _iso_to_date(start)
    end_date   = _iso_to_date(end)

    if not start_date or not end_date:
        return CalendarEventsResponse(events=[], total=0)

    all_events: List[CalendarEventOut] = []

    if _should_include("hotel_pm",   types):
        all_events.extend(_collect_hotel_pm(db, start_date, end_date))
    if _should_include("mall_pm",    types):
        all_events.extend(_collect_mall_pm(db, start_date, end_date))
    if _should_include("security",   types):
        all_events.extend(_collect_security_patrol(db, start_date, end_date))
    if _should_include("inspection", types):
        all_events.extend(_collect_inspection(db, start_date, end_date))
    if _should_include("approval",   types):
        all_events.extend(_collect_approvals(db, start_date, end_date))
    if _should_include("memo",       types):
        all_events.extend(_collect_memos(db, start_date, end_date))
    if _should_include("custom",     types):
        all_events.extend(_collect_custom(db, start_date, end_date))

    all_events.sort(key=lambda e: e.start)
    return CalendarEventsResponse(events=all_events, total=len(all_events))


# ─────────────────────────────────────────────────────────────────────────────
# /today — 今日摘要 KPI
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/today", summary="取得今日摘要 KPI", response_model=TodaySummary)
def get_today_summary(db: Session = Depends(get_db)):
    today = date.today()
    today_iso = _date_to_iso(today)

    result = get_calendar_events(
        start=today_iso,
        end=today_iso,
        types=None,
        db=db,
    )

    ev_list = result.events
    total   = len(ev_list)

    pending_count  = sum(1 for e in ev_list if e.status == "pending")
    abnormal_count = sum(1 for e in ev_list if e.status == "abnormal")
    overdue_count  = sum(1 for e in ev_list if e.status == "overdue")

    # 全系統待簽核件數（不限日期）
    approval_pending = db.query(Approval).filter(Approval.status == "pending").count()

    high_risk = abnormal_count + overdue_count

    # 事件類型分布
    type_counts: dict = {}
    for e in ev_list:
        type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1

    return TodaySummary(
        today            = today.strftime("%Y/%m/%d"),
        total_events     = total,
        pending_count    = pending_count,
        abnormal_count   = abnormal_count,
        overdue_count    = overdue_count,
        approval_pending = approval_pending,
        high_risk_count  = high_risk,
        event_by_type    = type_counts,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /custom — 自訂事件 CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/custom", summary="取得自訂事件清單", response_model=List[CustomEventOut])
def list_custom_events(
    start: Optional[str] = Query(None, description="起始日期 YYYY-MM-DD"),
    end:   Optional[str] = Query(None, description="結束日期 YYYY-MM-DD"),
    db:    Session = Depends(get_db),
):
    q = db.query(CalendarCustomEvent)
    if start:
        q = q.filter(CalendarCustomEvent.start_date >= start)
    if end:
        q = q.filter(CalendarCustomEvent.start_date <= end)
    return q.order_by(CalendarCustomEvent.start_date).all()


@router.post("/custom", summary="新增自訂事件", status_code=201, response_model=CustomEventOut)
def create_custom_event(
    payload: CustomEventCreate,
    db: Session = Depends(get_db),
):
    ev = CalendarCustomEvent(
        title       = payload.title,
        description = payload.description,
        start_date  = payload.start_date,
        end_date    = payload.end_date or "",
        all_day     = payload.all_day,
        start_time  = payload.start_time or "",
        end_time    = payload.end_time or "",
        color       = payload.color or EVENT_TYPE_COLORS["custom"],
        responsible = payload.responsible or "",
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.put("/custom/{event_id}", summary="更新自訂事件", response_model=CustomEventOut)
def update_custom_event(
    event_id: str,
    payload:  CustomEventUpdate,
    db: Session = Depends(get_db),
):
    ev = db.query(CalendarCustomEvent).filter(
        CalendarCustomEvent.id == event_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="事件不存在")

    for field, val in payload.dict(exclude_unset=True).items():
        setattr(ev, field, val)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/custom/{event_id}", summary="刪除自訂事件", status_code=204)
def delete_custom_event(
    event_id: str,
    db: Session = Depends(get_db),
):
    ev = db.query(CalendarCustomEvent).filter(
        CalendarCustomEvent.id == event_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="事件不存在")
    db.delete(ev)
    db.commit()
