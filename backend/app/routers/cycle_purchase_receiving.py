"""
週期採購 — 驗收單 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11（第四期：驗收單＋進貨數量報表）：
GET    /receiving                              驗收單清單（依採購單／狀態／公司篩選）
GET    /receiving/report                       進貨數量報表（依日期區間／公司／供應商彙總）
GET    /receiving/{id}                          驗收單詳情（含明細）
POST   /receiving                               新增驗收單（草稿，僅 issued／partial_received 狀態的採購單可建立）
GET    /receiving/{id}/receivable-items         這張驗收單所屬採購單的可驗收明細（含累計已驗收量／剩餘量）
POST   /receiving/{id}/items                    新增／更新一筆驗收明細（upsert，僅草稿可編輯）
DELETE /receiving/{id}/items/{item_id}          刪除一筆驗收明細（僅草稿可編輯）
POST   /receiving/{id}/submit                   送出（自動判定 completed／discrepancy，並重算採購單狀態）

注意：/receiving/report 必須宣告在 /receiving/{receiving_id} 之前，
否則 FastAPI 會把 "report" 當成 {receiving_id} 嘗試轉成 int 而 422。
"""
from typing import Optional, List
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_receiving import (
    ReceivableItemOut, ReceivingCreate, ReceivingDetail, ReceivingItemOut,
    ReceivingItemUpsert, ReceivingOut, ReceivingReportRow,
)
from app.services import cycle_purchase_receiving_service as svc
from app.services.cycle_purchase_receiving_service import ReceivingServiceError

router = APIRouter()


def _handle(fn, *args, **kwargs):
    """共用：把 ReceivingServiceError 轉成 422，統一錯誤訊息格式。"""
    try:
        return fn(*args, **kwargs)
    except ReceivingServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/receiving", response_model=List[ReceivingOut], summary="週期採購驗收單清單")
def list_receiving(
    po_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    company: Optional[str] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_receiving(db, po_id=po_id, status=status_, company=company)


@router.get(
    "/receiving/report",
    response_model=List[ReceivingReportRow],
    summary="進貨數量報表（依月份＋公司＋供應商＋料號彙總，僅計已送出驗收單）",
)
def get_receiving_report(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    company: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_report")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.get_receiving_report(db, date_from=date_from, date_to=date_to, company=company, vendor_id=vendor_id)


@router.get("/receiving/{receiving_id}", response_model=ReceivingDetail, summary="驗收單詳情（含明細）")
def get_receiving(
    receiving_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    receiving = svc.get_receiving(db, receiving_id)
    if not receiving:
        raise HTTPException(status_code=404, detail="驗收單不存在")
    return receiving


@router.post(
    "/receiving",
    response_model=ReceivingOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增驗收單（草稿）",
)
def create_receiving(
    payload: ReceivingCreate,
    current_user: User = Depends(require_permission("cycle_purchase_receive")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(
        svc.create_receiving, db, payload.po_id, payload.received_date, payload.notes, current_user,
    )


@router.get(
    "/receiving/{receiving_id}/receivable-items",
    response_model=List[ReceivableItemOut],
    summary="這張驗收單所屬採購單的可驗收明細（含累計已驗收量／剩餘量）",
)
def get_receivable_items(
    receiving_id: int,
    _: User = Depends(require_permission("cycle_purchase_receive")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.get_receivable_items, db, receiving_id)


@router.post(
    "/receiving/{receiving_id}/items",
    response_model=ReceivingItemOut,
    summary="新增／更新一筆驗收明細（upsert，僅草稿可編輯）",
)
def upsert_receiving_item(
    receiving_id: int,
    payload: ReceivingItemUpsert,
    _: User = Depends(require_permission("cycle_purchase_receive")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.upsert_receiving_item, db, receiving_id, payload)


@router.delete("/receiving/{receiving_id}/items/{receiving_item_id}", summary="刪除一筆驗收明細")
def delete_receiving_item(
    receiving_id: int,
    receiving_item_id: int,
    _: User = Depends(require_permission("cycle_purchase_receive")),
    db: Session = Depends(get_cycle_purchase_db),
):
    ok = _handle(svc.delete_receiving_item, db, receiving_id, receiving_item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="驗收明細不存在")
    return {"ok": True}


@router.post(
    "/receiving/{receiving_id}/submit",
    response_model=ReceivingOut,
    summary="送出驗收單（自動判定 completed／discrepancy，並重算採購單狀態）",
)
def submit_receiving(
    receiving_id: int,
    _: User = Depends(require_permission("cycle_purchase_receive")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.submit_receiving, db, receiving_id)
