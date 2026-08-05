"""
金旭 PMS 分析 — 付款方式分析 API
Prefix: /api/v1/jinxu/payment     規格書：§12.3

⚠️ 金額為刷卡／收款總額，**不含手續費，非淨收**（§19.2 Q5）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.jinxu_ledger import SIDE_SETTLEMENT
from app.models.user import User
from app.services import jinxu_analysis_service as A

router = APIRouter(dependencies=[Depends(get_current_user)])

VIEW = "jinxu_payment_view"


@router.get("/summary", summary="各付款方式金額與佔比")
async def summary(
    start_date: str = Query(""),
    end_date: str = Query(""),
    room_kind: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.payment_summary, db,
        start_date=start_date, end_date=end_date, room_kind=room_kind)


@router.get("/monthly", summary="付款方式月趨勢")
async def monthly(
    start_date: str = Query(""),
    end_date: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.payment_monthly, db, start_date=start_date, end_date=end_date)


@router.get("/entries", summary="抵充分錄明細（分頁）")
async def entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    start_date: str = Query(""),
    end_date: str = Query(""),
    subject_code: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.ledger_entries, db, page=page, page_size=page_size,
        start_date=start_date, end_date=end_date,
        subject_side=SIDE_SETTLEMENT, subject_code=subject_code)
