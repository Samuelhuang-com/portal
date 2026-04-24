"""
Dashboard API Router
Prefix: /api/v1/dashboard

提供高階主管總覽所需的 KPI 數字與圖表資料。
端點：
  GET /summary        — 舊版相容
  GET /kpi            — 飯店客房保養 + 庫存 + 同步狀態
  GET /graph          — 模組關聯圖譜
  GET /trend          — 近 N 日三模組完成率折線資料（新增）
  GET /closure-stats  — 異常結案漏斗統計（新增）
"""
from collections import defaultdict
from datetime import date, datetime, timezone, timedelta
from app.core.time import twnow
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.approval import Approval
from app.models.b1f_inspection import B1FInspectionBatch, B1FInspectionItem
from app.models.b2f_inspection import B2FInspectionBatch, B2FInspectionItem
from app.models.b4f_inspection import B4FInspectionBatch, B4FInspectionItem
from app.models.inventory import InventoryRecord
from app.models.mall_periodic_maintenance import MallPeriodicMaintenanceBatch, MallPeriodicMaintenanceItem
from app.models.memo import Memo
from app.models.periodic_maintenance import PeriodicMaintenanceBatch, PeriodicMaintenanceItem
from app.models.ragic_connection import RagicConnection
from app.models.rf_inspection import RFInspectionBatch, RFInspectionItem
from app.models.room_maintenance import RoomMaintenanceRecord
from app.models.security_patrol import SecurityPatrolBatch, SecurityPatrolItem
from app.models.sync_log import SyncLog
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter()

# 工作狀態常數（對應 schemas/room_maintenance.py）
STATUS_COMPLETED      = "已完成檢視及保養"
STATUS_NOT_SCHEDULED  = "非本月排程"
STATUS_IN_PROGRESS    = "進行中"
STATUS_PENDING        = "待排程"


@router.get("/summary")
def get_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """舊版 summary（保留相容）"""
    tenants = db.query(Tenant).filter(Tenant.is_active == True).count()
    users = db.query(User).filter(User.is_active == True).count()
    connections = (
        db.query(RagicConnection).filter(RagicConnection.is_active == True).count()
    )
    recent_syncs = db.query(SyncLog).order_by(SyncLog.started_at.desc()).limit(5).all()
    return {
        "tenants": tenants,
        "active_users": users,
        "ragic_connections": connections,
        "recent_syncs": [
            {
                "id": s.id,
                "connection_id": s.connection_id,
                "status": s.status,
                "records_fetched": s.records_fetched,
                "started_at": s.started_at.isoformat() if s.started_at else None,
            }
            for s in recent_syncs
        ],
    }


@router.get("/kpi")
def get_kpi(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    高階主管 KPI 總覽
    回傳：客房保養統計、庫存摘要、系統同步狀態
    """

    # ── 客房保養 ─────────────────────────────────────────────────────────────
    all_rooms = db.query(RoomMaintenanceRecord).all()
    total_rooms = len(all_rooms)

    completed     = sum(1 for r in all_rooms if STATUS_COMPLETED     in (r.work_item or ""))
    in_progress   = sum(1 for r in all_rooms if STATUS_IN_PROGRESS   in (r.work_item or ""))
    not_scheduled = sum(1 for r in all_rooms if STATUS_NOT_SCHEDULED in (r.work_item or ""))
    pending       = sum(1 for r in all_rooms if STATUS_PENDING       in (r.work_item or ""))
    total_incomplete = sum(r.incomplete or 0 for r in all_rooms)
    completion_rate  = round(completed / total_rooms * 100, 1) if total_rooms > 0 else 0.0

    # 需重點關注的房間（incomplete > 0，依未完成數降冪，取前 10）
    focus_rooms = sorted(
        [r for r in all_rooms if (r.incomplete or 0) > 0],
        key=lambda r: r.incomplete,
        reverse=True,
    )[:10]

    # ── 庫存 ─────────────────────────────────────────────────────────────────
    all_inventory = db.query(InventoryRecord).all()
    total_skus = len(all_inventory)
    total_quantity = sum(r.quantity or 0 for r in all_inventory)

    # 依類別統計數量
    category_map: dict[str, dict] = {}
    for r in all_inventory:
        cat = r.category or "未分類"
        if cat not in category_map:
            category_map[cat] = {"name": cat, "skus": 0, "quantity": 0}
        category_map[cat]["skus"] += 1
        category_map[cat]["quantity"] += r.quantity or 0

    category_distribution = sorted(
        category_map.values(), key=lambda x: x["quantity"], reverse=True
    )

    # ── 系統同步狀態 ──────────────────────────────────────────────────────────
    recent_syncs = (
        db.query(SyncLog)
        .order_by(SyncLog.started_at.desc())
        .limit(10)
        .all()
    )

    last_sync = recent_syncs[0] if recent_syncs else None
    total_syncs = len(recent_syncs)
    success_count = sum(1 for s in recent_syncs if s.status == "success")
    sync_success_rate = round(success_count / total_syncs * 100, 1) if total_syncs > 0 else 0.0

    return {
        "room_maintenance": {
            "total": total_rooms,
            "completed": completed,
            "in_progress": in_progress,
            "not_scheduled": not_scheduled,
            "pending": pending,
            "total_incomplete": total_incomplete,
            "completion_rate": completion_rate,
            "status_distribution": [
                {"name": STATUS_COMPLETED,     "value": completed,     "color": "#52c41a"},
                {"name": STATUS_IN_PROGRESS,   "value": in_progress,   "color": "#1677ff"},
                {"name": STATUS_NOT_SCHEDULED, "value": not_scheduled, "color": "#8c8c8c"},
                {"name": STATUS_PENDING,       "value": pending,       "color": "#faad14"},
            ],
            "focus_rooms": [
                {
                    "room_no": r.room_no,
                    "work_item": r.work_item,
                    "incomplete": r.incomplete,
                    "dept": r.dept,
                }
                for r in focus_rooms
            ],
        },
        "inventory": {
            "total_skus": total_skus,
            "total_quantity": total_quantity,
            "category_distribution": category_distribution,
        },
        "system": {
            "last_sync_at": last_sync.started_at.isoformat() if last_sync and last_sync.started_at else None,
            "last_sync_status": last_sync.status if last_sync else None,
            "last_sync_records": last_sync.records_fetched if last_sync else None,
            "sync_success_rate": sync_success_rate,
            "recent_syncs": [
                {
                    "id": s.id,
                    "status": s.status,
                    "records_fetched": s.records_fetched,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "triggered_by": s.triggered_by,
                    "error_msg": s.error_msg,
                }
                for s in recent_syncs[:5]
            ],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/dashboard/graph  (v1.26 重設計)
# 操作流程鏈：巡檢 → 保養 → 簽核 → 公告
# 節點 11 個（3 群組）+ 關係邊 8 條（含 DB 直接關聯 + 業務邏輯關聯）
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/graph")
def get_graph(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    回傳操作流程關聯圖譜。
    三群組：inspection（巡檢）→ maintenance（保養）→ workflow（簽核/公告）
    邊類型：
      anomaly    — 巡檢異常觸發保養需求（業務邏輯，dashed）
      escalation — 異常/逾期升級至簽核（業務邏輯，dashed）
      workflow   — DB 直接關聯（Approval→Memo via source/source_id，solid）
    """
    now   = twnow()
    today = now.date()
    seven_days_ago = now - timedelta(days=7)

    # ──────────────────────────────────────────────────────────────────────────
    # 1. 巡檢：各樓層個別 abnormal 計數
    # ──────────────────────────────────────────────────────────────────────────
    b1f_alert = db.query(func.count(B1FInspectionItem.ragic_id)).filter(
        B1FInspectionItem.abnormal_flag == True).scalar() or 0
    b2f_alert = db.query(func.count(B2FInspectionItem.ragic_id)).filter(
        B2FInspectionItem.abnormal_flag == True).scalar() or 0
    rf_alert  = db.query(func.count(RFInspectionItem.ragic_id)).filter(
        RFInspectionItem.abnormal_flag == True).scalar() or 0
    b4f_alert = db.query(func.count(B4FInspectionItem.ragic_id)).filter(
        B4FInspectionItem.abnormal_flag == True).scalar() or 0
    security_alert = db.query(func.count(SecurityPatrolItem.ragic_id)).filter(
        SecurityPatrolItem.abnormal_flag == True).scalar() or 0

    # ──────────────────────────────────────────────────────────────────────────
    # 2. 客房保養：待排程 + 進行中
    # ──────────────────────────────────────────────────────────────────────────
    hotel_rooms = db.query(RoomMaintenanceRecord).all()
    hotel_room_alert = sum(
        1 for r in hotel_rooms
        if "待排程" in (r.work_item or "") or "進行中" in (r.work_item or "")
    )

    # ──────────────────────────────────────────────────────────────────────────
    # 3. 飯店週期保養：逾期未完成 & 有異常標記
    # ──────────────────────────────────────────────────────────────────────────
    hotel_pm_all = db.query(PeriodicMaintenanceItem).filter(
        PeriodicMaintenanceItem.is_completed == False,
        PeriodicMaintenanceItem.scheduled_date != "",
    ).all()
    hotel_pm_overdue = 0
    for item in hotel_pm_all:
        try:
            m, d = item.scheduled_date.strip().split("/")
            if datetime(today.year, int(m), int(d)).date() < today:
                hotel_pm_overdue += 1
        except Exception:
            pass
    hotel_pm_abnormal = db.query(func.count(PeriodicMaintenanceItem.ragic_id)).filter(
        PeriodicMaintenanceItem.abnormal_flag == True).scalar() or 0
    hotel_pm_alert = hotel_pm_overdue + hotel_pm_abnormal

    # ──────────────────────────────────────────────────────────────────────────
    # 4. 商場週期保養：逾期未完成 & 有異常標記
    # ──────────────────────────────────────────────────────────────────────────
    mall_pm_all = db.query(MallPeriodicMaintenanceItem).filter(
        MallPeriodicMaintenanceItem.is_completed == False,
        MallPeriodicMaintenanceItem.scheduled_date != "",
    ).all()
    mall_pm_overdue = 0
    for item in mall_pm_all:
        try:
            m, d = item.scheduled_date.strip().split("/")
            if datetime(today.year, int(m), int(d)).date() < today:
                mall_pm_overdue += 1
        except Exception:
            pass
    mall_pm_abnormal = db.query(func.count(MallPeriodicMaintenanceItem.ragic_id)).filter(
        MallPeriodicMaintenanceItem.abnormal_flag == True).scalar() or 0
    mall_pm_alert = mall_pm_overdue + mall_pm_abnormal

    # ──────────────────────────────────────────────────────────────────────────
    # 5. 簽核：待辦
    # ──────────────────────────────────────────────────────────────────────────
    approval_alert = db.query(func.count(Approval.id)).filter(
        Approval.status == "pending").scalar() or 0

    # ──────────────────────────────────────────────────────────────────────────
    # 6. 公告：近 7 天新增 & 由簽核產生的公告（DB 直接關聯）
    # ──────────────────────────────────────────────────────────────────────────
    memo_recent = db.query(func.count(Memo.id)).filter(
        Memo.created_at >= seven_days_ago).scalar() or 0
    memo_from_approval = db.query(func.count(Memo.id)).filter(
        Memo.source == "approval").scalar() or 0

    # ──────────────────────────────────────────────────────────────────────────
    # 輔助：status 判斷
    # ──────────────────────────────────────────────────────────────────────────
    def _status(alert: int) -> str:
        if alert >= 5:  return "danger"
        if alert >= 1:  return "warning"
        return "normal"

    # ──────────────────────────────────────────────────────────────────────────
    # 群組定義（前端用來著色和分區）
    # ──────────────────────────────────────────────────────────────────────────
    groups = [
        {"id": "inspection",  "label": "巡檢作業", "color": "#4BA8E8"},
        {"id": "maintenance", "label": "保養作業", "color": "#52c41a"},
        {"id": "workflow",    "label": "流程管理", "color": "#722ed1"},
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # 節點定義（13 個）
    # ──────────────────────────────────────────────────────────────────────────
    nodes = [
        # 巡檢群組
        {"id": "b1f_insp",   "label": "B1F 商場巡檢", "group": "inspection",
         "alert": b1f_alert,      "status": _status(b1f_alert),
         "path": "/mall/b1f-inspection"},
        {"id": "b2f_insp",   "label": "B2F 商場巡檢", "group": "inspection",
         "alert": b2f_alert,      "status": _status(b2f_alert),
         "path": "/mall/b2f-inspection"},
        {"id": "rf_insp",    "label": "RF 商場巡檢",  "group": "inspection",
         "alert": rf_alert,       "status": _status(rf_alert),
         "path": "/mall/rf-inspection"},
        {"id": "b4f_insp",   "label": "B4F 工務巡檢", "group": "inspection",
         "alert": b4f_alert,      "status": _status(b4f_alert),
         "path": "/mall/b4f-inspection"},
        {"id": "security",   "label": "保全巡檢",     "group": "inspection",
         "alert": security_alert, "status": _status(security_alert),
         "path": "/security/dashboard"},
        # Ragic 直連巡檢（無本地 DB，alert 固定為 0）
        {"id": "mall_facility", "label": "商場工務巡檢", "group": "inspection",
         "alert": 0, "status": "normal",
         "path": "/mall-facility-inspection/dashboard",
         "sub": "Ragic 直連作業"},
        {"id": "full_building", "label": "整棟巡檢",    "group": "inspection",
         "alert": 0, "status": "normal",
         "path": "/full-building-inspection/dashboard",
         "sub": "Ragic 直連作業"},
        # 保養群組
        {"id": "hotel_room", "label": "客房保養",       "group": "maintenance",
         "alert": hotel_room_alert, "status": _status(hotel_room_alert),
         "path": "/hotel/room-maintenance"},
        {"id": "hotel_pm",   "label": "飯店週期保養",   "group": "maintenance",
         "alert": hotel_pm_alert,   "status": _status(hotel_pm_alert),
         "path": "/hotel/periodic-maintenance",
         "sub": f"逾期{hotel_pm_overdue} 異常{hotel_pm_abnormal}"},
        {"id": "mall_pm",    "label": "商場週期保養",   "group": "maintenance",
         "alert": mall_pm_alert,    "status": _status(mall_pm_alert),
         "path": "/mall/periodic-maintenance",
         "sub": f"逾期{mall_pm_overdue} 異常{mall_pm_abnormal}"},
        # 流程群組
        {"id": "approval",   "label": "簽核管理",      "group": "workflow",
         "alert": approval_alert,  "status": _status(approval_alert),
         "path": "/approvals"},
        {"id": "memo",       "label": "公告備忘",      "group": "workflow",
         "alert": memo_recent,     "status": "normal",
         "path": "/memos",
         "sub": f"來自簽核 {memo_from_approval} 則"},
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # 關係邊定義（10 條）
    # 邊類型：
    #   anomaly    — 巡檢異常 → 保養需求（業務邏輯，dashed）
    #   escalation — 異常/逾期升級 → 簽核（業務邏輯，dashed）
    #   workflow   — DB 直接關聯：Approval → Memo（solid）
    # ──────────────────────────────────────────────────────────────────────────
    edges = [
        # 商場三樓層巡檢 → 商場週期保養（異常觸發保養需求）
        {"id": "e_b1f_mallpm",  "source": "b1f_insp", "target": "mall_pm",
         "label": "異常觸發",  "weight": b1f_alert,   "type": "anomaly"},
        {"id": "e_b2f_mallpm",  "source": "b2f_insp", "target": "mall_pm",
         "label": "異常觸發",  "weight": b2f_alert,   "type": "anomaly"},
        {"id": "e_rf_mallpm",   "source": "rf_insp",  "target": "mall_pm",
         "label": "異常觸發",  "weight": rf_alert,    "type": "anomaly"},
        # 工務巡檢 → 飯店週期保養
        {"id": "e_b4f_hotelpm", "source": "b4f_insp", "target": "hotel_pm",
         "label": "工務異常",  "weight": b4f_alert,   "type": "anomaly"},
        # 商場工務巡檢 → 商場週期保養
        {"id": "e_mf_mallpm",   "source": "mall_facility", "target": "mall_pm",
         "label": "工務異常",  "weight": 1, "type": "anomaly"},
        # 整棟巡檢 → 飯店週期保養
        {"id": "e_fb_hotelpm",  "source": "full_building", "target": "hotel_pm",
         "label": "整棟異常",  "weight": 1, "type": "anomaly"},
        # 保全異常 → 簽核升級
        {"id": "e_sec_appr",    "source": "security", "target": "approval",
         "label": "異常升級",  "weight": security_alert, "type": "escalation"},
        # 保養異常/逾期 → 簽核
        {"id": "e_hpm_appr",    "source": "hotel_pm", "target": "approval",
         "label": "異常簽核",  "weight": hotel_pm_alert, "type": "escalation"},
        {"id": "e_mpm_appr",    "source": "mall_pm",  "target": "approval",
         "label": "異常簽核",  "weight": mall_pm_alert,  "type": "escalation"},
        # 簽核 → 公告（DB 直接關聯：Memo.source='approval'）
        {"id": "e_appr_memo",   "source": "approval", "target": "memo",
         "label": f"通過→公告\n({memo_from_approval}則)",
         "weight": max(1, memo_from_approval), "type": "workflow"},
    ]

    total_alerts = (
        b1f_alert + b2f_alert + rf_alert + b4f_alert + security_alert
        + hotel_room_alert + hotel_pm_alert + mall_pm_alert + approval_alert
    )

    return {
        "groups": groups,
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "generated_at": now.isoformat(),
            "total_alerts": total_alerts,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/dashboard/trend
# 三模組（商場巡檢 / 保全巡檢 / 客房保養）近 N 日完成率折線資料
# ─────────────────────────────────────────────────────────────────────────────

# 商場巡檢樓層設定
_MALL_FLOOR_CONFIGS = [
    ("b1f", B1FInspectionBatch, B1FInspectionItem),
    ("b2f", B2FInspectionBatch, B2FInspectionItem),
    ("rf",  RFInspectionBatch,  RFInspectionItem),
]


def _mall_completion_for_day(db: Session, d_str: str) -> tuple[float, int, bool]:
    """回傳商場當日（完成率, 異常數, 有資料）"""
    total = checked = abnormal = 0
    for _, BatchModel, ItemModel in _MALL_FLOOR_CONFIGS:
        batches = db.query(BatchModel).filter(
            BatchModel.inspection_date == d_str
        ).all()
        for b in batches:
            items = db.query(ItemModel).filter(
                ItemModel.batch_ragic_id == b.ragic_id
            ).all()
            for it in items:
                total += 1
                if it.result_status in ("normal", "abnormal", "pending"):
                    checked += 1
                if it.result_status in ("abnormal", "pending"):
                    abnormal += 1
    rate = round(checked / total * 100, 1) if total > 0 else 0.0
    return rate, abnormal, total > 0


def _security_completion_for_day(db: Session, d_str: str) -> tuple[float, int, bool]:
    """回傳保全當日（完成率, 異常數, 有資料）"""
    total = checked = abnormal = 0
    batches = db.query(SecurityPatrolBatch).filter(
        SecurityPatrolBatch.inspection_date == d_str
    ).all()
    for b in batches:
        items = db.query(SecurityPatrolItem).filter(
            SecurityPatrolItem.batch_ragic_id == b.ragic_id,
            SecurityPatrolItem.is_note == False,  # noqa: E712
        ).all()
        for it in items:
            total += 1
            if it.result_status in ("normal", "abnormal", "pending"):
                checked += 1
            if it.result_status in ("abnormal", "pending"):
                abnormal += 1
    rate = round(checked / total * 100, 1) if total > 0 else 0.0
    return rate, abnormal, total > 0


@router.get("/trend")
def get_trend(
    days: int = Query(7, ge=3, le=30, description="趨勢天數，3~30"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    近 N 日三模組完成率折線資料。
    回傳：商場巡檢 / 保全巡檢 / 客房保養（依 inspect_datetime 統計）
    """
    today = date.today()

    # 客房：依 inspect_datetime 日期前綴預分組（避免 N+1）
    all_rooms = db.query(RoomMaintenanceRecord).all()
    hotel_by_date: dict[str, list] = defaultdict(list)
    for r in all_rooms:
        if r.inspect_datetime:
            d_key = r.inspect_datetime[:10]  # "YYYY/MM/DD" or "YYYY-MM-DD"
            hotel_by_date[d_key].append(r)

    trend = []
    for i in range(days - 1, -1, -1):
        d     = today - timedelta(days=i)
        d_str = d.strftime("%Y/%m/%d")

        # 商場
        mall_rate, mall_abn, mall_has = _mall_completion_for_day(db, d_str)
        # 保全
        sec_rate, sec_abn, sec_has = _security_completion_for_day(db, d_str)
        # 客房
        hotel_rooms_today = hotel_by_date.get(d_str, [])
        hotel_total     = len(hotel_rooms_today)
        hotel_completed = sum(
            1 for r in hotel_rooms_today
            if STATUS_COMPLETED in (r.work_item or "")
        )
        hotel_rate = round(hotel_completed / hotel_total * 100, 1) if hotel_total > 0 else 0.0
        hotel_abn  = sum(1 for r in hotel_rooms_today if (r.incomplete or 0) > 0)

        trend.append({
            "date":               d_str,
            "mall_completion":    mall_rate,
            "mall_abnormal":      mall_abn,
            "mall_has_data":      mall_has,
            "security_completion": sec_rate,
            "security_abnormal":   sec_abn,
            "security_has_data":   sec_has,
            "hotel_completion":   hotel_rate,
            "hotel_completed":    hotel_completed,
            "hotel_total":        hotel_total,
            "hotel_abnormal":     hotel_abn,
            "hotel_has_data":     hotel_total > 0,
        })

    return {"trend": trend, "days": days}


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/dashboard/closure-stats
# 各模組「異常 → 已處理 → 已結案」漏斗統計
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/closure-stats")
def get_closure_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    異常結案漏斗：
      - hotel   : 客房保養（以 incomplete / work_item / close_date 判斷）
      - mall_insp: 商場巡檢（以 abnormal_flag 為異常；無結案欄位，顯示已知異常數）
      - security : 保全巡檢（同上）
      - approvals: 簽核流程（pending → approved/rejected）
    """
    # ── 客房保養 ─────────────────────────────────────────────────────────────
    all_rooms   = db.query(RoomMaintenanceRecord).all()
    hotel_total = len(all_rooms)
    # 有問題的房間（incomplete > 0 OR 非已完成且非非本月）
    hotel_issues = [
        r for r in all_rooms
        if (r.incomplete or 0) > 0
        or STATUS_PENDING    in (r.work_item or "")
        or STATUS_IN_PROGRESS in (r.work_item or "")
    ]
    # 已處理：進行中（有人在處理）
    hotel_in_progress = sum(
        1 for r in hotel_issues
        if STATUS_IN_PROGRESS in (r.work_item or "")
    )
    # 已結案：close_date 有值
    hotel_closed = sum(
        1 for r in all_rooms
        if r.close_date and r.close_date.strip()
    )
    hotel_issue_count = len(hotel_issues)
    hotel_closure_rate = (
        round(hotel_closed / hotel_issue_count * 100, 1)
        if hotel_issue_count > 0 else 100.0
    )

    # ── 商場巡檢異常（近 30 日）────────────────────────────────────────────────
    cutoff_30 = (date.today() - timedelta(days=30)).strftime("%Y/%m/%d")
    mall_abn_total = 0
    for _, BatchModel, ItemModel in _MALL_FLOOR_CONFIGS:
        batch_ids = [
            b.ragic_id for b in
            db.query(BatchModel).filter(BatchModel.inspection_date >= cutoff_30).all()
        ]
        if batch_ids:
            mall_abn_total += db.query(func.count(ItemModel.ragic_id)).filter(
                ItemModel.batch_ragic_id.in_(batch_ids),
                ItemModel.result_status.in_(["abnormal", "pending"]),
            ).scalar() or 0

    # ── 保全巡檢異常（近 30 日）────────────────────────────────────────────────
    sec_batch_ids = [
        b.ragic_id for b in
        db.query(SecurityPatrolBatch).filter(
            SecurityPatrolBatch.inspection_date >= cutoff_30
        ).all()
    ]
    sec_abn_total = 0
    if sec_batch_ids:
        sec_abn_total = db.query(func.count(SecurityPatrolItem.ragic_id)).filter(
            SecurityPatrolItem.batch_ragic_id.in_(sec_batch_ids),
            SecurityPatrolItem.result_status.in_(["abnormal", "pending"]),
            SecurityPatrolItem.is_note == False,  # noqa: E712
        ).scalar() or 0

    # ── 簽核流程 ──────────────────────────────────────────────────────────────
    all_approvals = db.query(Approval).all()
    appr_total    = len(all_approvals)
    appr_pending  = sum(1 for a in all_approvals if a.status == "pending")
    appr_approved = sum(1 for a in all_approvals if a.status == "approved")
    appr_rejected = sum(1 for a in all_approvals if a.status == "rejected")
    appr_resolved = appr_approved + appr_rejected
    appr_closure_rate = (
        round(appr_resolved / appr_total * 100, 1) if appr_total > 0 else 0.0
    )

    # ── 總覽 ──────────────────────────────────────────────────────────────────
    total_anomalies = hotel_issue_count + mall_abn_total + sec_abn_total
    total_closed    = hotel_closed + appr_resolved

    return {
        "hotel": {
            "total_rooms":       hotel_total,
            "issue_count":       hotel_issue_count,
            "in_progress":       hotel_in_progress,
            "closed":            hotel_closed,
            "open":              hotel_issue_count - hotel_closed,
            "closure_rate":      hotel_closure_rate,
        },
        "mall_inspection": {
            "period":            "近 30 日",
            "abnormal_count":    mall_abn_total,
            "note":              "巡檢異常項目（結案追蹤需透過簽核流程）",
        },
        "security_inspection": {
            "period":            "近 30 日",
            "abnormal_count":    sec_abn_total,
            "note":              "保全異常項目（結案追蹤需透過簽核流程）",
        },
        "approvals": {
            "total":             appr_total,
            "pending":           appr_pending,
            "approved":          appr_approved,
            "rejected":          appr_rejected,
            "resolved":          appr_resolved,
            "closure_rate":      appr_closure_rate,
        },
        "summary": {
            "total_anomalies":   total_anomalies,
            "total_closed":      total_closed,
            "generated_at":      twnow().isoformat(),
        },
    }
