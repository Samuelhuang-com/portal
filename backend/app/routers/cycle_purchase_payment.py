"""
週期採購 — 請款單 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11（第五期：請款單＋費用分攤明細）：
GET    /payments                              請款單清單（依採購單／狀態／公司篩選）
GET    /payments/payable-receivings           建立請款單畫面用：這張採購單底下還沒被涵蓋的已送出驗收單
GET    /payments/{id}                          請款單詳情（含分攤明細／涵蓋的驗收單）
POST   /payments                               新增請款單（草稿，自動試算分攤明細）
PUT    /payments/{id}                          更新發票資訊／備註（僅草稿可編輯）
PUT    /payments/{id}/allocations/{alloc_id}   調整一筆分攤明細（僅草稿可編輯）
POST   /payments/{id}/submit                   送出（檢查分攤總額 vs 發票金額，不符需填原因）
POST   /payments/{id}/status                   變更狀態（submitted -> paying -> paid，只能依序推進）

注意：/payments/payable-receivings 必須宣告在 /payments/{payment_id} 之前，
否則 FastAPI 會把 "payable-receivings" 當成 {payment_id} 嘗試轉成 int 而 422。
"""
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_payment import (
    AllocationUpdate, PayableReceivingOut, PaymentCreate, PaymentDetail,
    PaymentOut, PaymentStatusPayload, PaymentUpdate,
)
from app.services import cycle_purchase_payment_service as svc
from app.services.cycle_purchase_payment_service import PaymentServiceError

router = APIRouter()


def _handle(fn, *args, **kwargs):
    """共用：把 PaymentServiceError 轉成 422，統一錯誤訊息格式。"""
    try:
        return fn(*args, **kwargs)
    except PaymentServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/payments", response_model=List[PaymentOut], summary="週期採購請款單清單")
def list_payments(
    po_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    company: Optional[str] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_payments(db, po_id=po_id, status=status_, company=company)


@router.get(
    "/payments/payable-receivings",
    response_model=List[PayableReceivingOut],
    summary="建立請款單畫面用：這張採購單底下還沒被涵蓋的已送出驗收單",
)
def get_payable_receivings(
    po_id: int = Query(...),
    _: User = Depends(require_permission("cycle_purchase_finance")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.get_payable_receivings, db, po_id)


@router.get("/payments/{payment_id}", response_model=PaymentDetail, summary="請款單詳情（含分攤明細／涵蓋的驗收單）")
def get_payment(
    payment_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    payment = svc.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="請款單不存在")
    return payment


@router.post(
    "/payments",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增請款單（草稿，自動試算費用分攤明細）",
)
def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(require_permission("cycle_purchase_finance")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(
        svc.create_payment,
        db, payload.po_id, payload.receiving_ids, payload.invoice_no, payload.invoice_date,
        payload.invoice_amount, payload.notes, current_user,
    )


@router.put("/payments/{payment_id}", response_model=PaymentOut, summary="更新發票資訊／備註（僅草稿可編輯）")
def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    _: User = Depends(require_permission("cycle_purchase_finance")),
    db: Session = Depends(get_cycle_purchase_db),
):
    payment = _handle(svc.update_payment, db, payment_id, payload)
    if not payment:
        raise HTTPException(status_code=404, detail="請款單不存在")
    return payment


@router.put(
    "/payments/{payment_id}/allocations/{allocation_id}",
    summary="調整一筆分攤明細（僅草稿可編輯，金額與試算值不同時需填原因）",
)
def update_allocation_item(
    payment_id: int,
    allocation_id: int,
    payload: AllocationUpdate,
    _: User = Depends(require_permission("cycle_purchase_finance")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.update_allocation_item, db, payment_id, allocation_id, payload)


@router.post(
    "/payments/{payment_id}/submit",
    response_model=PaymentOut,
    summary="送出請款單（檢查分攤總額 vs 發票金額，不符需已填差異原因）",
)
def submit_payment(
    payment_id: int,
    _: User = Depends(require_permission("cycle_purchase_finance")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.submit_payment, db, payment_id)


@router.post(
    "/payments/{payment_id}/status",
    response_model=PaymentOut,
    summary="變更請款單狀態（submitted -> paying -> paid，只能依序推進）",
)
def set_payment_status(
    payment_id: int,
    payload: PaymentStatusPayload,
    _: User = Depends(require_permission("cycle_purchase_finance")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.set_payment_status, db, payment_id, payload.status)
