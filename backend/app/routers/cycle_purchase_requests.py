"""
週期採購 — 請購單 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11：拿掉「批次」後，請購單改掛 cycle_id + period_label（期別標籤）。
「產生本期請購單」（POST /requests/generate）取代原本批次開放時的自動觸發，
隨時可呼叫，同一週期＋期別冪等（不會重複建立）。

GET    /requests                              請購單清單（依週期／期別／部門／狀態篩選）
GET    /requests/todos                        Dashboard 待辦提醒（我的待填 + 全部待簽核）
GET    /requests/{id}                          請購單詳情（含明細）
POST   /requests/generate                      產生本期請購單（依週期設定的 applicable_scope，一次幫所有適用部門建空白單）
POST   /requests                               手動新增單一部門的請購單（備用路徑）
PUT    /requests/{id}                          更新請購單（成本中心／備註，僅草稿或已退回可編輯）
GET    /requests/{id}/available-items          可選料號清單（僅該公司有對照的啟用中料號）
POST   /requests/{id}/items                    新增請購明細
PUT    /requests/{id}/items/{item_row_id}      更新請購明細（數量／會計科目／備註）
DELETE /requests/{id}/items/{item_row_id}      刪除請購明細
POST   /requests/{id}/submit                   送出（draft/rejected -> submitted）
POST   /requests/{id}/approve                  簽核核准（submitted -> approved）
POST   /requests/{id}/reject                   簽核退回（submitted -> rejected，需填退回原因）
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.core.database import get_db
from app.dependencies import require_permission, get_user_permissions
from app.models.user import User
from app.schemas.cycle_purchase_request import (
    AvailableItemOut, GenerateRequestsPayload, RequestCreate, RequestDetail,
    RequestItemCreate, RequestItemOut, RequestItemUpdate, RequestOut,
    RequestRejectPayload, RequestUpdate, TodoSummary,
)
from app.services import cycle_purchase_request_service as svc
from app.services.cycle_purchase_request_service import RequestServiceError

router = APIRouter()


def _handle(fn, *args, **kwargs):
    """共用：把 RequestServiceError 轉成 422，統一錯誤訊息格式。"""
    try:
        return fn(*args, **kwargs)
    except RequestServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/requests", response_model=List[RequestOut], summary="週期採購請購單清單")
def list_requests(
    cycle_id: Optional[int] = Query(None),
    period_label: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_requests(
        db, cycle_id=cycle_id, period_label=period_label,
        department_id=department_id, status=status_,
    )


@router.get("/requests/todos", response_model=TodoSummary, summary="Dashboard 待辦提醒")
def get_todos(
    current_user: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
    portal_db: Session = Depends(get_db),
):
    perms = get_user_permissions(current_user.id, portal_db)
    is_approver = "*" in perms or "cycle_purchase_approve" in perms
    return svc.get_dashboard_todos(db, current_user, is_approver)


@router.get("/requests/{request_id}", response_model=RequestDetail, summary="請購單詳情（含明細）")
def get_request(
    request_id: int,
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    req = svc.get_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="請購單不存在")
    return req


@router.post(
    "/requests/generate",
    response_model=List[RequestOut],
    summary="產生本期請購單（一次幫所有適用部門建空白單，隨時可觸發、冪等）",
)
def generate_requests(
    payload: GenerateRequestsPayload,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.generate_requests_for_period, db, payload.cycle_id, payload.period_label)


@router.post("/requests", response_model=RequestOut, status_code=status.HTTP_201_CREATED, summary="手動新增單一部門的請購單")
def create_request(
    payload: RequestCreate,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.create_request, db, payload)


@router.put("/requests/{request_id}", response_model=RequestOut, summary="更新請購單")
def update_request(
    request_id: int,
    payload: RequestUpdate,
    _: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
):
    req = _handle(svc.update_request, db, request_id, payload)
    if not req:
        raise HTTPException(status_code=404, detail="請購單不存在")
    return req


@router.get(
    "/requests/{request_id}/available-items",
    response_model=List[AvailableItemOut],
    summary="可選料號清單（依請購單所屬公司過濾）",
)
def get_available_items(
    request_id: int,
    _: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.get_available_items, db, request_id)


@router.post(
    "/requests/{request_id}/items",
    response_model=RequestItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增請購明細",
)
def add_request_item(
    request_id: int,
    payload: RequestItemCreate,
    _: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.add_request_item, db, request_id, payload)


@router.put(
    "/requests/{request_id}/items/{item_row_id}",
    response_model=RequestItemOut,
    summary="更新請購明細",
)
def update_request_item(
    request_id: int,
    item_row_id: int,
    payload: RequestItemUpdate,
    _: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
):
    row = _handle(svc.update_request_item, db, request_id, item_row_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="請購明細不存在")
    return row


@router.delete("/requests/{request_id}/items/{item_row_id}", summary="刪除請購明細")
def delete_request_item(
    request_id: int,
    item_row_id: int,
    _: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
):
    ok = _handle(svc.delete_request_item, db, request_id, item_row_id)
    if not ok:
        raise HTTPException(status_code=404, detail="請購明細不存在")
    return {"ok": True}


@router.post("/requests/{request_id}/submit", response_model=RequestOut, summary="送出請購單")
def submit_request(
    request_id: int,
    current_user: User = Depends(require_permission("cycle_purchase_request")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.submit_request, db, request_id, current_user)


@router.post("/requests/{request_id}/approve", response_model=RequestOut, summary="簽核核准請購單")
def approve_request(
    request_id: int,
    current_user: User = Depends(require_permission("cycle_purchase_approve")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.approve_request, db, request_id, current_user)


@router.post("/requests/{request_id}/reject", response_model=RequestOut, summary="簽核退回請購單")
def reject_request(
    request_id: int,
    payload: RequestRejectPayload,
    current_user: User = Depends(require_permission("cycle_purchase_approve")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.reject_request, db, request_id, current_user, payload.reason)
