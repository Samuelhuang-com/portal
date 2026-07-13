"""
週期採購 — 批次 API Router
Prefix: /api/v1/cycle-purchase

批次號由後端依開放月份自動產生（CP-YYYYMM-NNNN），呼叫端不需自行輸入，
避免人工編號重複（對應 RFP「週期批次不可重複產生」的要求，本期先以
批次號唯一 + 人工建立防呆；自動排程產生批次列入後續階段）。
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_batch import BatchCreate, BatchOut, BatchUpdate
from app.services import cycle_purchase_service as svc
from app.services import cycle_purchase_request_service as request_svc
from app.services.cycle_purchase_request_service import RequestServiceError

router = APIRouter()


@router.get("/batches", response_model=List[BatchOut], summary="週期採購批次清單")
def list_batches(
    cycle_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_batches(db, cycle_id=cycle_id, status=status_)


@router.get("/batches/{batch_id}", response_model=BatchOut, summary="批次詳情")
def get_batch(
    batch_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    batch = svc.get_batch(db, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    return batch


@router.post("/batches", response_model=BatchOut, status_code=status.HTTP_201_CREATED, summary="新增批次")
def create_batch(
    payload: BatchCreate,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    batch = svc.create_batch(db, payload)
    if not batch:
        raise HTTPException(status_code=404, detail="週期設定不存在")
    return batch


@router.put("/batches/{batch_id}", response_model=BatchOut, summary="更新批次")
def update_batch(
    batch_id: int,
    payload: BatchUpdate,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    before = svc.get_batch(db, batch_id)
    if not before:
        raise HTTPException(status_code=404, detail="批次不存在")
    prev_status = before.status

    batch = svc.update_batch(db, batch_id, payload)
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 批次狀態從其他狀態切為 open 時，自動產生本批次各適用部門的請購單
    # （冪等 —— 由 generate_requests_for_batch 內的 requests_generated 旗標防重複）。
    # 放在 router 層呼叫，避免 cycle_purchase_service.py 需要 import
    # cycle_purchase_request_service.py 造成循環引用。
    if batch.status == "open" and prev_status != "open" and not batch.requests_generated:
        try:
            request_svc.generate_requests_for_batch(db, batch_id)
        except RequestServiceError as e:
            raise HTTPException(status_code=422, detail=str(e))

    return batch
