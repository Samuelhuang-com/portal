"""
週期採購 — 彙整單 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11（第三期：彙整＋轉採購單）：
GET    /summary                         彙整單清單（依週期／期別／公司／供應商／狀態篩選）
GET    /summary/vendor-groups           轉採購單畫面用：依公司＋供應商分組統計（僅 draft）
POST   /summary/generate                產生彙整（只彙總已核准請購明細，冪等）
PUT    /summary/{id}                    調整量／調整原因（僅 draft 可編輯）
POST   /summary/convert-to-po           轉採購單（指定週期＋期別＋公司＋供應商）
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_summary import (
    ConvertToPoPayload, GenerateSummaryPayload, SummaryOut, SummaryUpdate, VendorGroupOut,
)
from app.schemas.cycle_purchase_po import PODetail
from app.services import cycle_purchase_summary_service as svc
from app.services.cycle_purchase_summary_service import SummaryServiceError

router = APIRouter()


def _handle(fn, *args, **kwargs):
    """共用：把 SummaryServiceError 轉成 422，統一錯誤訊息格式。"""
    try:
        return fn(*args, **kwargs)
    except SummaryServiceError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/summary", response_model=List[SummaryOut], summary="週期採購彙整單清單")
def list_summary(
    cycle_id: Optional[int] = Query(None),
    period_label: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    status_: Optional[str] = Query(None, alias="status"),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_summary(
        db, cycle_id=cycle_id, period_label=period_label,
        company=company, vendor_id=vendor_id, status=status_,
    )


@router.get(
    "/summary/vendor-groups",
    response_model=List[VendorGroupOut],
    summary="轉採購單畫面用：依公司＋供應商分組統計（僅草稿）",
)
def vendor_groups(
    cycle_id: int = Query(...),
    period_label: str = Query(...),
    company: Optional[str] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_vendor_groups(db, cycle_id, period_label, company)


@router.post(
    "/summary/generate",
    response_model=List[SummaryOut],
    summary="產生彙整（只彙總已核准請購明細，冪等，不會覆寫已存在的彙整列）",
)
def generate_summary(
    payload: GenerateSummaryPayload,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.generate_summary, db, payload.cycle_id, payload.period_label)


@router.put("/summary/{summary_id}", response_model=SummaryOut, summary="調整彙整列的調整量／調整原因")
def update_summary_item(
    summary_id: int,
    payload: SummaryUpdate,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    row = _handle(svc.update_summary_item, db, summary_id, payload)
    if not row:
        raise HTTPException(status_code=404, detail="彙整列不存在")
    return row


@router.post(
    "/summary/convert-to-po",
    response_model=PODetail,
    status_code=status.HTTP_201_CREATED,
    summary="轉採購單（同一週期＋期別＋公司＋供應商的草稿彙整列合成一張採購單）",
)
def convert_to_po(
    payload: ConvertToPoPayload,
    current_user: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(
        svc.convert_to_po,
        db, payload.cycle_id, payload.period_label, payload.company, payload.vendor_id,
        current_user,
    )
