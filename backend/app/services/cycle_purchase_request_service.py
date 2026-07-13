"""
週期採購 — 請購單 Service 層

2026-07-11（與 Samuel 討論後拿掉「批次」）：
  - 請購單不再掛 batch_id，改掛 cycle_id + period_label（期別標籤，如
    「2026-07」）。「產生本期請購單」（generate_requests_for_period）取代
    原本的 generate_requests_for_batch，隨時可觸發，不需要先手動開批次，
    也沒有固定時間窗限制 —— 這是 Samuel 的核心訴求：週採的範圍界線是
    「料號主檔」，不是時間窗。
  - 同一週期＋同一期別＋同一部門只能有一張請購單（冪等）。
  - 新增「待辦提醒」：get_dashboard_todos 依登入者是否為某部門的
    owner_user_id，回傳他自己部門「待填」的請購單；若有簽核權限，
    另外回傳全部「待簽核」的請購單。

2026-07-11 與 Samuel 確認之設計（第一次，仍然有效）：
  - 請購明細單價＝該公司在 cycle_purchase_item_mappings 的
    original_unit_price（不是 item.unit_price）。
  - 會計科目由填單人在明細逐行手動選（不做自動帶入）。
  - 簽核為單一關卡：draft -> submitted -> approved / rejected，
    rejected 可再編輯、重新送出（不是死路）。
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.cycle_purchase_request import CyclePurchaseRequest, CyclePurchaseRequestItem
from app.models.cycle_purchase_cycle import CyclePurchaseCycle
from app.models.cycle_purchase_reference import (
    CyclePurchaseDepartment, CyclePurchaseCostCenter, CyclePurchaseAccountCode,
)
from app.models.cycle_purchase_item import CyclePurchaseItem, CyclePurchaseItemMapping


class RequestServiceError(Exception):
    """給 router 轉成適當 HTTP 錯誤用的一般性例外。"""
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 請購單號
# ═══════════════════════════════════════════════════════════════════════════

def _next_request_no(db: Session, on_date: date) -> str:
    prefix = f"PR-{on_date.strftime('%Y%m')}-"
    count = (
        db.query(func.count(CyclePurchaseRequest.id))
        .filter(CyclePurchaseRequest.request_no.like(f"{prefix}%"))
        .scalar()
        or 0
    )
    return f"{prefix}{count + 1:04d}"


# ═══════════════════════════════════════════════════════════════════════════
# 產生本期請購單（取代原本的批次開放觸發）
# ═══════════════════════════════════════════════════════════════════════════

def _applicable_departments(db: Session, cycle: CyclePurchaseCycle):
    """依 cycle.applicable_scope（逗號分隔的公司名稱，或 'all'）找出適用的啟用中部門。"""
    scope = (cycle.applicable_scope or "").strip()
    query = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.is_active == True)  # noqa: E712

    if not scope or scope.lower() == "all":
        return query.all()

    companies = {s.strip() for s in scope.split(",") if s.strip()}
    if not companies:
        return query.all()
    return query.filter(CyclePurchaseDepartment.company.in_(companies)).all()


def generate_requests_for_period(db: Session, cycle_id: int, period_label: str) -> list[CyclePurchaseRequest]:
    """
    「產生本期請購單」：為每個適用部門建立一張空白請購單。
    隨時可呼叫，沒有時間窗限制；同一 cycle_id+period_label 冪等
    （已經產生過的部門會直接回傳既有那張，不會重複建立）。
    """
    period_label = (period_label or "").strip()
    if not period_label:
        raise RequestServiceError("期別標籤不能是空白")

    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == cycle_id).first()
    if not cycle:
        raise RequestServiceError("週期設定不存在")

    departments = _applicable_departments(db, cycle)
    if not departments:
        raise RequestServiceError("這個週期設定目前沒有任何適用的啟用中部門，請先確認 applicable_scope 與部門主檔")

    today = date.today()
    created = []
    for dept in departments:
        exists = (
            db.query(CyclePurchaseRequest)
            .filter(
                CyclePurchaseRequest.cycle_id == cycle_id,
                CyclePurchaseRequest.period_label == period_label,
                CyclePurchaseRequest.department_id == dept.id,
            )
            .first()
        )
        if exists:
            created.append(exists)
            continue
        req = CyclePurchaseRequest(
            request_no=_next_request_no(db, today),
            cycle_id=cycle_id,
            period_label=period_label,
            department_id=dept.id,
            company=dept.company,
            status="draft",
            total_amount=0,
        )
        db.add(req)
        db.flush()
        created.append(req)

    for r in created:
        _attach_display_fields(db, r)
    return created


# ═══════════════════════════════════════════════════════════════════════════
# 請購單 CRUD / 查詢
# ═══════════════════════════════════════════════════════════════════════════

def _attach_display_fields(db: Session, req: CyclePurchaseRequest) -> CyclePurchaseRequest:
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == req.cycle_id).first()
    req.cycle_name = cycle.cycle_name if cycle else None
    dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == req.department_id).first()
    req.department_name = dept.dept_name if dept else None
    req.cost_center_name = None
    if req.cost_center_id:
        cc = db.query(CyclePurchaseCostCenter).filter(CyclePurchaseCostCenter.id == req.cost_center_id).first()
        req.cost_center_name = cc.cc_name if cc else None
    return req


def _attach_item_account_label(db: Session, item: CyclePurchaseRequestItem) -> CyclePurchaseRequestItem:
    item.account_code_label = None
    if item.account_code_id:
        ac = db.query(CyclePurchaseAccountCode).filter(CyclePurchaseAccountCode.id == item.account_code_id).first()
        if ac:
            item.account_code_label = f"{ac.code} {ac.name}"
    return item


def list_requests(
    db: Session,
    cycle_id: Optional[int] = None,
    period_label: Optional[str] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
):
    query = db.query(CyclePurchaseRequest)
    if cycle_id is not None:
        query = query.filter(CyclePurchaseRequest.cycle_id == cycle_id)
    if period_label:
        query = query.filter(CyclePurchaseRequest.period_label == period_label)
    if department_id is not None:
        query = query.filter(CyclePurchaseRequest.department_id == department_id)
    if status:
        query = query.filter(CyclePurchaseRequest.status == status)
    rows = query.order_by(CyclePurchaseRequest.request_no.desc()).all()
    for r in rows:
        _attach_display_fields(db, r)
    return rows


def get_request(db: Session, request_id: int) -> Optional[CyclePurchaseRequest]:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return None
    _attach_display_fields(db, req)
    for it in req.items:
        _attach_item_account_label(db, it)
    return req


def create_request(db: Session, payload) -> CyclePurchaseRequest:
    """手動建立單一部門的請購單（備用路徑；一般由 generate_requests_for_period 一次幫全部部門建立）。"""
    dept = db.query(CyclePurchaseDepartment).filter(CyclePurchaseDepartment.id == payload.department_id).first()
    if not dept:
        raise RequestServiceError("部門不存在")
    cycle = db.query(CyclePurchaseCycle).filter(CyclePurchaseCycle.id == payload.cycle_id).first()
    if not cycle:
        raise RequestServiceError("週期設定不存在")

    period_label = (payload.period_label or "").strip()
    if not period_label:
        raise RequestServiceError("期別標籤不能是空白")

    # 防呆：cycle_purchase_requests 有 (cycle_id, period_label, department_id) 唯一鍵限制，
    # 若不先檢查，重複建立會在 flush 時丟出未攔截的 IntegrityError（500），
    # 這裡改成清楚的訊息。
    existing = (
        db.query(CyclePurchaseRequest)
        .filter(
            CyclePurchaseRequest.cycle_id == payload.cycle_id,
            CyclePurchaseRequest.period_label == period_label,
            CyclePurchaseRequest.department_id == payload.department_id,
        )
        .first()
    )
    if existing:
        raise RequestServiceError(
            f"「{cycle.cycle_name}／{period_label}」的「{dept.dept_name}」已經有一張請購單"
            f"（{existing.request_no}），不能重複建立"
        )

    req = CyclePurchaseRequest(
        request_no=_next_request_no(db, date.today()),
        cycle_id=payload.cycle_id,
        period_label=period_label,
        department_id=payload.department_id,
        company=dept.company,
        cost_center_id=payload.cost_center_id,
        status="draft",
        total_amount=0,
    )
    db.add(req)
    db.flush()
    return _attach_display_fields(db, req)


def update_request(db: Session, request_id: int, payload) -> Optional[CyclePurchaseRequest]:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return None
    if req.status not in ("draft", "rejected"):
        raise RequestServiceError("只有草稿或已退回狀態的請購單可以編輯")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(req, k, v)
    db.flush()
    return _attach_display_fields(db, req)


# ═══════════════════════════════════════════════════════════════════════════
# 請購明細
# ═══════════════════════════════════════════════════════════════════════════

def _recompute_total(db: Session, request_id: int):
    total = (
        db.query(func.coalesce(func.sum(CyclePurchaseRequestItem.subtotal), 0))
        .filter(CyclePurchaseRequestItem.request_id == request_id)
        .scalar()
    )
    db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).update(
        {"total_amount": total}
    )


def get_available_items(db: Session, request_id: int):
    """
    該請購單所屬「公司＋部門」，有對照表資料的啟用中料號清單（給選料號畫面用）。

    2026-07-11 新增部門篩選：逐列核對兩家公司的「設料號明細表.xlsx」後確認，
    分頁（工務用／清潔用品／文具&印刷／營業用品）對應真實的功能性部門，
    同一家公司內沒有任何料號橫跨兩個分頁。因此這裡不能只按公司篩，要同時
    按 department_id 篩，否則營業部的請購單會看到工務部的料號可以選。
    """
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")

    rows = (
        db.query(CyclePurchaseItem, CyclePurchaseItemMapping)
        .join(
            CyclePurchaseItemMapping,
            CyclePurchaseItemMapping.item_id == CyclePurchaseItem.id,
        )
        .filter(
            CyclePurchaseItemMapping.company == req.company,
            CyclePurchaseItemMapping.department_id == req.department_id,
            CyclePurchaseItem.is_active == True,  # noqa: E712
        )
        .order_by(CyclePurchaseItem.item_code)
        .all()
    )
    result = []
    for item, mapping in rows:
        result.append(
            {
                "item_id": item.id,
                "item_mapping_id": mapping.id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "unit": item.unit,
                "category": item.category,
                "unit_price": mapping.original_unit_price,
                "is_confirmed": mapping.is_confirmed,
            }
        )
    return result


def add_request_item(db: Session, request_id: int, payload) -> CyclePurchaseRequestItem:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")
    if req.status not in ("draft", "rejected"):
        raise RequestServiceError("只有草稿或已退回狀態的請購單可以新增明細")

    item = db.query(CyclePurchaseItem).filter(CyclePurchaseItem.id == payload.item_id).first()
    if not item:
        raise RequestServiceError("料號不存在")

    # 2026-07-11：新增部門篩選，跟 get_available_items() 的可選清單邏輯保持一致。
    # 不能只擋在前端「可選料號」清單上，這裡也要擋，否則直接呼叫 API 可以繞過
    # 部門邊界（例如營業部的請購單加進工務部的料號）。
    mapping = (
        db.query(CyclePurchaseItemMapping)
        .filter(
            CyclePurchaseItemMapping.item_id == payload.item_id,
            CyclePurchaseItemMapping.company == req.company,
            CyclePurchaseItemMapping.department_id == req.department_id,
        )
        .first()
    )
    if not mapping:
        raise RequestServiceError(f"此料號不屬於「{req.company}」這個部門的可選清單，無法加入本請購單")

    existing = (
        db.query(CyclePurchaseRequestItem)
        .filter(
            CyclePurchaseRequestItem.request_id == request_id,
            CyclePurchaseRequestItem.item_id == payload.item_id,
        )
        .first()
    )
    if existing:
        raise RequestServiceError("此料號已經在明細中，請直接修改數量")

    row = CyclePurchaseRequestItem(
        request_id=request_id,
        item_id=item.id,
        item_mapping_id=mapping.id,
        account_code_id=payload.account_code_id,
        item_code=item.item_code,
        item_name=item.item_name,
        unit=item.unit,
        unit_price=mapping.original_unit_price,
        request_qty=payload.request_qty or 0,
        subtotal=(mapping.original_unit_price or Decimal("0")) * (payload.request_qty or 0),
        notes=payload.notes,
    )
    db.add(row)
    db.flush()
    _recompute_total(db, request_id)
    db.flush()
    return _attach_item_account_label(db, row)


def update_request_item(db: Session, request_id: int, item_row_id: int, payload) -> Optional[CyclePurchaseRequestItem]:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return None
    if req.status not in ("draft", "rejected"):
        raise RequestServiceError("只有草稿或已退回狀態的請購單可以修改明細")

    row = (
        db.query(CyclePurchaseRequestItem)
        .filter(
            CyclePurchaseRequestItem.id == item_row_id,
            CyclePurchaseRequestItem.request_id == request_id,
        )
        .first()
    )
    if not row:
        return None

    data = payload.model_dump(exclude_unset=True)
    if "request_qty" in data:
        row.request_qty = data["request_qty"] or 0
        row.subtotal = (row.unit_price or Decimal("0")) * row.request_qty
    if "account_code_id" in data:
        row.account_code_id = data["account_code_id"]
    if "notes" in data:
        row.notes = data["notes"]

    db.flush()
    _recompute_total(db, request_id)
    db.flush()
    return _attach_item_account_label(db, row)


def delete_request_item(db: Session, request_id: int, item_row_id: int) -> bool:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        return False
    if req.status not in ("draft", "rejected"):
        raise RequestServiceError("只有草稿或已退回狀態的請購單可以刪除明細")

    row = (
        db.query(CyclePurchaseRequestItem)
        .filter(
            CyclePurchaseRequestItem.id == item_row_id,
            CyclePurchaseRequestItem.request_id == request_id,
        )
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.flush()
    _recompute_total(db, request_id)
    db.flush()
    return True


# ═══════════════════════════════════════════════════════════════════════════
# 送出 / 簽核 / 退回
# ═══════════════════════════════════════════════════════════════════════════

def submit_request(db: Session, request_id: int, user) -> CyclePurchaseRequest:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")
    if req.status not in ("draft", "rejected"):
        raise RequestServiceError("只有草稿或已退回狀態的請購單可以送出")

    item_count = (
        db.query(func.count(CyclePurchaseRequestItem.id))
        .filter(
            CyclePurchaseRequestItem.request_id == request_id,
            CyclePurchaseRequestItem.request_qty > 0,
        )
        .scalar()
        or 0
    )
    if item_count == 0:
        raise RequestServiceError("請至少填寫一筆數量大於 0 的料號才能送出")

    req.status = "submitted"
    req.submitted_by_user_id = user.id
    req.submitted_by_name = user.full_name
    req.submitted_at = datetime.now()
    req.reject_reason = None
    db.flush()
    return _attach_display_fields(db, req)


def approve_request(db: Session, request_id: int, user) -> CyclePurchaseRequest:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")
    if req.status != "submitted":
        raise RequestServiceError("只有已送出狀態的請購單可以簽核")

    req.status = "approved"
    req.approved_by_user_id = user.id
    req.approved_by_name = user.full_name
    req.approved_at = datetime.now()
    req.reject_reason = None
    db.flush()
    return _attach_display_fields(db, req)


def reject_request(db: Session, request_id: int, user, reason: str) -> CyclePurchaseRequest:
    req = db.query(CyclePurchaseRequest).filter(CyclePurchaseRequest.id == request_id).first()
    if not req:
        raise RequestServiceError("請購單不存在")
    if req.status != "submitted":
        raise RequestServiceError("只有已送出狀態的請購單可以退回")

    req.status = "rejected"
    req.approved_by_user_id = user.id
    req.approved_by_name = user.full_name
    req.approved_at = datetime.now()
    req.reject_reason = reason
    db.flush()
    return _attach_display_fields(db, req)


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard 待辦提醒
# ═══════════════════════════════════════════════════════════════════════════

def get_dashboard_todos(db: Session, user, is_approver: bool):
    """
    待辦提醒：
      - my_pending：登入者是 owner_user_id 的部門，狀態為 draft/rejected 的請購單
        （這些是「我自己部門還沒填/被退回要改」的單）。
      - pending_approval：若登入者有簽核權限，回傳全部 submitted 狀態的請購單
        （簽核目前是全域單一關卡，不分部門，所以不用篩選 owner）。
    """
    my_dept_ids = [
        d.id
        for d in db.query(CyclePurchaseDepartment.id)
        .filter(CyclePurchaseDepartment.owner_user_id == user.id)
        .all()
    ]

    my_pending = []
    if my_dept_ids:
        my_pending = (
            db.query(CyclePurchaseRequest)
            .filter(
                CyclePurchaseRequest.department_id.in_(my_dept_ids),
                CyclePurchaseRequest.status.in_(("draft", "rejected")),
            )
            .order_by(CyclePurchaseRequest.request_no.desc())
            .all()
        )
        for r in my_pending:
            _attach_display_fields(db, r)

    pending_approval = []
    if is_approver:
        pending_approval = (
            db.query(CyclePurchaseRequest)
            .filter(CyclePurchaseRequest.status == "submitted")
            .order_by(CyclePurchaseRequest.request_no.desc())
            .all()
        )
        for r in pending_approval:
            _attach_display_fields(db, r)

    return {
        "my_pending": my_pending,
        "pending_approval_count": len(pending_approval),
        "pending_approval": pending_approval,
    }
