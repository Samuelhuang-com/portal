"""
週期採購 — 採購單 API Router
Prefix: /api/v1/cycle-purchase

GET    /pos                   採購單清單（依週期／期別／公司／供應商／狀態篩選）
GET    /pos/{id}               採購單詳情（含明細）
PUT    /pos/{id}               更新採購單（預計到貨日／備註，僅草稿可編輯）
POST   /pos/{id}/status        變更狀態（issued | cancelled）
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_any_permission, require_permission
from app.models.user import User
from app.schemas.cycle_purchase_po import (
    PODetail, POOut, POStatusPayload, POUpdate, RevertPoPayload, RevertPoResult,
)
from app.services import cycle_purchase_po_service as svc
from app.services.cycle_purchase_po_service import POServiceError

router = APIRouter()


def _handle(fn, *args, **kwargs):
    """共用：把 POServiceError 轉成 422，統一錯誤訊息格式。"""
    try:
        return fn(*args, **kwargs)
    except POServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/pos", response_model=List[POOut], summary="週期採購採購單清單")
def list_pos(
    cycle_id: Optional[int] = Query(None),
    period_label: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    _: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_pos(
        db, cycle_id=cycle_id, period_label=period_label,
        company=company, vendor_id=vendor_id, status=status_,
    )


@router.get("/pos/{po_id}", response_model=PODetail, summary="採購單詳情（含明細）")
def get_po(
    po_id: int,
    _: User = Depends(require_any_permission("cycle_purchase_view", "cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    po = svc.get_po(db, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    return po


@router.put("/pos/{po_id}", response_model=POOut, summary="更新採購單（預計到貨日／備註）")
def update_po(
    po_id: int,
    payload: POUpdate,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    po = _handle(svc.update_po, db, po_id, payload)
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    return po


@router.post("/pos/{po_id}/status", response_model=POOut, summary="變更採購單狀態（issued／cancelled）")
def set_po_status(
    po_id: int,
    payload: POStatusPayload,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    po = _handle(svc.set_po_status, db, po_id, payload.status)
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    return po


@router.post(
    "/pos/{po_id}/revert-to-summary",
    response_model=RevertPoResult,
    summary="退回彙整單（採購單作廢，對應的彙整列解鎖回草稿讓買家重新調整後再轉單）",
)
def revert_po_to_summary(
    po_id: int,
    payload: RevertPoPayload,
    current_user: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    """與「取消」是兩個不同動作：取消只標 cancelled、彙整列維持鎖定；
    退回會把彙整列放回 draft。唯一擋下條件是「已經有驗收單」，見
    services/cycle_purchase_po_service.py 開頭說明。"""
    return _handle(svc.revert_po_to_summary, db, po_id, payload.reason, current_user)
