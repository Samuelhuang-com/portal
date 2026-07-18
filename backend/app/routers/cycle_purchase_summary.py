"""
週期採購 — 彙整單 API Router
Prefix: /api/v1/cycle-purchase

2026-07-11（第三期：彙整＋轉採購單）：
GET    /summary                         彙整單清單（依週期／期別／公司／供應商／狀態篩選）
GET    /summary/vendor-groups           轉採購單畫面用：依公司＋供應商分組統計（僅 draft）
PUT    /summary/{id}                    調整量／調整原因（僅 draft 可編輯）
POST   /summary/convert-to-po           轉採購單（指定週期＋期別＋公司＋供應商）

2026-07-16（匯總請購單改版，見 models/cycle_purchase_summary.py 開頭說明）：
GET    /summary/department-breakdown    依料號分組展開部門別＋小計（匯總請購單畫面用）
POST   /summary/push-to-ragic           拋轉到 Ragic（目前為 stub，Ragic 端表單尚未建立）

2026-07-16（第二次調整，「彙整單產生方式」改版，見
services/cycle_purchase_summary_service.py 開頭說明——原本 POST /summary/generate
是靠使用者輸入的「週期＋期別」字串完全比對抓資料，期別字串不一致就會查到
0 筆；已整個移除，不保留備用路徑）：
GET    /summary/eligible-requests       列出某週期＋公司＋期別下，已關閉且尚未
                                         被彙整過的請購單，供勾選
POST   /summary/generate-from-requests  把勾選的請購單彙整成彙整列（period_label
                                         由系統從勾選的請購單本身的 period_label
                                         讀出來）

2026-07-17（第三次調整，配合請購單流程大改版——拿掉送出／核准，改成「關閉」）：
eligible-requests／generate-from-requests 的判斷條件從「status == approved」
改成「is_closed == True」，月份篩選也從「approved_at 換算年月」改成直接比對
period_label，見 services/cycle_purchase_summary_service.py 開頭第三次調整說明。
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cycle_purchase_database import get_cycle_purchase_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.cycle_purchase_summary import (
    ConvertToPoPayload, DepartmentBreakdownOut, EligibleRequestOut, GenerateFromRequestsPayload,
    PushToRagicPayload, PushToRagicResult, SummaryOut, SummaryUpdate, VendorGroupOut,
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
    department_id: Optional[int] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_summary(
        db, cycle_id=cycle_id, period_label=period_label,
        company=company, vendor_id=vendor_id, status=status_,
        department_id=department_id,
    )


@router.get(
    "/summary/department-breakdown",
    response_model=List[DepartmentBreakdownOut],
    summary="匯總請購單畫面用：依料號分組展開部門別＋小計",
)
def department_breakdown(
    cycle_id: int = Query(...),
    period_label: str = Query(...),
    company: Optional[str] = Query(None),
    _: User = Depends(require_permission("cycle_purchase_view")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return svc.list_department_breakdown(db, cycle_id, period_label, company)


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


@router.get(
    "/summary/eligible-requests",
    response_model=List[EligibleRequestOut],
    summary="列出某週期＋公司＋期別下，已關閉且尚未被彙整過的請購單（供勾選產生彙整）",
)
def eligible_requests(
    cycle_id: int = Query(...),
    company: str = Query(...),
    year_month: str = Query(..., description="期別，格式 YYYY-MM，依請購單 period_label 判斷"),
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.list_eligible_requests, db, cycle_id, company, year_month)


@router.post(
    "/summary/generate-from-requests",
    response_model=List[SummaryOut],
    summary="把勾選的請購單彙整成彙整列（period_label 由系統從請購單本身的 period_label 讀出來）",
)
def generate_summary_from_requests(
    payload: GenerateFromRequestsPayload,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(svc.generate_summary_from_requests, db, payload.request_ids)


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


@router.post(
    "/summary/push-to-ragic",
    response_model=PushToRagicResult,
    summary="拋轉到 Ragic「匯總請購單」（目前為 stub，Ragic 端表單尚未建立，見 cycle_purchase_ragic_push.py）",
)
def push_to_ragic(
    payload: PushToRagicPayload,
    _: User = Depends(require_permission("cycle_purchase_buyer")),
    db: Session = Depends(get_cycle_purchase_db),
):
    return _handle(
        svc.push_summary_to_ragic,
        db, payload.cycle_id, payload.period_label, payload.company,
    )
