"""
金旭 PMS 分析 — 預收訂金追蹤 API
Prefix: /api/v1/jinxu/deposit     規格書：§12.4

⚠️ J21：只做總額層級，不做 64A↔81A 逐筆配對。
⚠️ 「未沖餘額」需完整歷史資料才準確——前端必須把 summary 回傳的 warning
   原樣顯示為 Alert。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.jinxu_ledger import DEPOSIT_IN_CODES, DEPOSIT_OUT_CODES
from app.models.user import User
from app.services import jinxu_analysis_service as A

router = APIRouter(dependencies=[Depends(get_current_user)])

VIEW = "jinxu_deposit_view"


@router.get("/summary", summary="預收訂金發生／沖銷／未沖餘額")
async def summary(
    start_date: str = Query(""),
    end_date: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.deposit_summary, db, start_date=start_date, end_date=end_date)


@router.get("/monthly", summary="逐月發生 vs 沖銷（含累計餘額）")
async def monthly(
    start_date: str = Query(""),
    end_date: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.deposit_monthly, db, start_date=start_date, end_date=end_date)


@router.get("/entries", summary="訂金相關分錄明細（分頁）")
async def entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    start_date: str = Query(""),
    end_date: str = Query(""),
    direction: str = Query("all", pattern="^(all|in|out)$"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    codes = {
        "in": DEPOSIT_IN_CODES,
        "out": DEPOSIT_OUT_CODES,
        "all": tuple(DEPOSIT_IN_CODES) + tuple(DEPOSIT_OUT_CODES),
    }[direction]

    def _run():
        from app.models.jinxu_ledger import JinxuLedgerEntry
        q = A._ledger_q(db, start_date=start_date, end_date=end_date).filter(
            JinxuLedgerEntry.subject_code.in_(codes))
        total = q.count()
        rows = (
            q.order_by(JinxuLedgerEntry.business_date.desc())
            .offset((page - 1) * page_size).limit(page_size).all()
        )
        return {"total": total, "page": page, "page_size": page_size,
                "items": [A._ledger_dict(e) for e in rows]}

    return await run_in_threadpool(_run)
