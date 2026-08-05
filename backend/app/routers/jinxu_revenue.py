"""
金旭 PMS 分析 — 收入結構分析 API
Prefix: /api/v1/jinxu/revenue     規格書：§12.2

⚠️ 一律使用同步 def，重運算透過 run_in_threadpool（CLAUDE.md）。
⚠️ J17：回傳內容不得包含 FCR02 的「備註」欄。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.services import jinxu_analysis_service as A

router = APIRouter(dependencies=[Depends(get_current_user)])

VIEW = "jinxu_revenue_view"


def _filters(
    start_date: str = Query("", description="營業日起（ISO）"),
    end_date: str = Query("", description="營業日迄（ISO）"),
    subject_code: str | None = Query(None),
    subject_group: str | None = Query(None),
    room_kind: str | None = Query(None, description="GUEST / OTHER；不傳=全部"),
    shift: str | None = Query(None),
    operator_id: str | None = Query(None),
    folio_type: str | None = Query(None),
    booking_no: str | None = Query(None),
    include_reversal: bool = Query(True, description="False=排除沖帳列（查核用）"),
    include_memo: bool = Query(False, description="True=含純記錄性分錄"),
) -> dict:
    return {
        "start_date": start_date, "end_date": end_date,
        "subject_code": subject_code, "subject_group": subject_group,
        "room_kind": room_kind, "shift": shift, "operator_id": operator_id,
        "folio_type": folio_type, "booking_no": booking_no,
        "include_reversal": include_reversal, "include_memo": include_memo,
    }


@router.get("/summary", summary="收入 KPI")
async def summary(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_view")),
):
    return await run_in_threadpool(A.revenue_summary, db, **f)


@router.get("/coverage", summary="資料涵蓋範圍與期間標籤")
async def coverage(
    start_date: str = Query(""),
    end_date: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_view")),
):
    cov = await run_in_threadpool(A.data_coverage, db)
    cov["period_label"] = A.period_label(start_date, end_date, cov["ledger_end"])
    return cov


@router.get("/by-subject", summary="科目別／大類別彙總")
async def by_subject(
    group_by: str = Query("code", pattern="^(code|group)$"),
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.revenue_by_subject, db, group_by=group_by, **f)


@router.get("/monthly", summary="月趨勢（依大類拆分）")
async def monthly(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.revenue_monthly, db, **f)


@router.get("/daily", summary="日別彙總")
async def daily(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.revenue_daily, db, **f)


@router.get("/by-room-kind", summary="客房 vs 非客房拆分（J24）")
async def by_room_kind(
    start_date: str = Query(""),
    end_date: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.revenue_by_room_kind, db, start_date=start_date, end_date=end_date)


@router.get("/shifts", summary="班別與操作員統計")
async def shifts(
    start_date: str = Query(""),
    end_date: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.shift_summary, db, start_date=start_date, end_date=end_date)


@router.get("/entries", summary="分錄明細（分頁）")
async def entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.ledger_entries, db, page=page, page_size=page_size, **f)


@router.get("/entries/{entry_id}", summary="單筆分錄（Drawer）")
async def entry_detail(
    entry_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    out = await run_in_threadpool(A.ledger_entry_detail, db, entry_id)
    if out is None:
        raise HTTPException(404, f"分錄 #{entry_id} 不存在")
    return out
