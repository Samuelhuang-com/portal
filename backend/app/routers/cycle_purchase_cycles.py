"""
週期採購 — 週期設定 API Router
Prefix: /api/v1/cycle-purchase
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_cycle import CycleCreate, CycleOut, CycleUpdate
from app.services import cycle_purchase_service as svc

router = APIRouter()


@router.get("/cycles", response_model=List[CycleOut], summary="週期採購週期設定清單")
def list_cycles(
    status_: Optional[str] = Query(None, alias="status"),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_cycles(db, status=status_)


@router.get("/cycles/{cycle_id}", response_model=CycleOut, summary="週期設定詳情")
def get_cycle(
    cycle_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    cycle = svc.get_cycle(db, cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="週期設定不存在")
    return cycle


@router.post("/cycles", response_model=CycleOut, status_code=status.HTTP_201_CREATED, summary="新增週期設定")
def create_cycle(
    payload: CycleCreate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        return svc.create_cycle(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="週期代碼已存在")


@router.put("/cycles/{cycle_id}", response_model=CycleOut, summary="更新週期設定")
def update_cycle(
    cycle_id: int,
    payload: CycleUpdate,
    _: User = Depends(require_permission("cycle_purchase_admin")),
    db: Session = Depends(get_cycle_purchase_db),
):
    try:
        cycle = svc.update_cycle(db, cycle_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="週期代碼已存在")
    if not cycle:
        raise HTTPException(status_code=404, detail="週期設定不存在")
    return cycle
