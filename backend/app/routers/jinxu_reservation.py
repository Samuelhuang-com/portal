"""
金旭 PMS 分析 — 訂房與通路分析 API
Prefix: /api/v1/jinxu/reservation     規格書：§12.5

⚠️ 母體規則（§11.4）：`include_cancelled` 預設 **False**，所有營運統計自動
   排除取消（實測 29.7%）與虛擬訂房（J15）。每個回應都附 population_note，
   前端必須顯示。

⚠️ 權限分層：
     jinxu_resv_view   → 通路／房型／業務碼／月趨勢／明細
     jinxu_cancel_view → 取消分析、訂價 vs 實收、回訪分析
   後者暴露業務績效與價格執行資訊，敏感度較高，故另立 key。它沒有對應路由
   （是 /jinxu/reservation 頁的 TAB），但仍登錄於 PERMISSION_DEFINITIONS。
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

VIEW = "jinxu_resv_view"
CANCEL_VIEW = "jinxu_cancel_view"


def _filters(
    start_date: str = Query("", description="ISO 日期起"),
    end_date: str = Query("", description="ISO 日期迄"),
    date_basis: str = Query("arrival", pattern="^(arrival|departure)$"),
    company_name: str | None = Query(None),
    rate_code: str | None = Query(None),
    source_name: str | None = Query(None),
    resv_type: str | None = Query(None, pattern="^(FIT|GIT)$"),
    status_code: str | None = Query(None),
    include_cancelled: bool = Query(False, description="預設 False —— 營運統計排除取消"),
) -> dict:
    return {
        "start_date": start_date, "end_date": end_date, "date_basis": date_basis,
        "company_name": company_name, "rate_code": rate_code,
        "source_name": source_name, "resv_type": resv_type,
        "status_code": status_code, "include_cancelled": include_cancelled,
    }


def _no_cancel(f: dict) -> dict:
    """取消分析自帶母體，呼叫端不得覆寫。"""
    out = dict(f)
    out.pop("include_cancelled", None)
    return out


# ── 訂房統計 ─────────────────────────────────────────────────────────────────

@router.get("/summary", summary="訂房 KPI（含取消率）")
async def summary(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("jinxu_view")),
):
    return await run_in_threadpool(A.resv_summary, db, **_no_cancel(f))


@router.get("/by-channel", summary="通路別彙總（不合併同 OTA）")
async def by_channel(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.resv_by_channel, db, **f)


@router.get("/by-roomtype", summary="房型別彙總（只顯示代碼）")
async def by_roomtype(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.resv_by_roomtype, db, **f)


@router.get("/by-ratecode", summary="業務碼別彙總")
async def by_ratecode(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.resv_by_ratecode, db, **f)


@router.get("/by-source", summary="業務源別彙總")
async def by_source(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.resv_by_source, db, **f)


@router.get("/by-type", summary="散客／團體彙總")
async def by_type(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.resv_by_type, db, **f)


@router.get("/monthly", summary="訂房月趨勢")
async def monthly(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.resv_monthly, db, **_no_cancel(f))


@router.get("/status-breakdown", summary="7 種訂房狀態分布")
async def status_breakdown(
    start_date: str = Query(""),
    end_date: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(
        A.status_breakdown, db, start_date=start_date, end_date=end_date)


# ── 取消分析（權限較高）──────────────────────────────────────────────────────

@router.get("/cancellation", summary="取消率總覽")
async def cancellation(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(CANCEL_VIEW)),
):
    return await run_in_threadpool(A.cancellation_summary, db, **_no_cancel(f))


@router.get("/cancellation/by-channel", summary="依通路取消率")
async def cancellation_by_channel(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(CANCEL_VIEW)),
):
    return await run_in_threadpool(A.cancellation_by_channel, db, **_no_cancel(f))


@router.get("/cancellation/by-ratecode", summary="依業務碼取消率")
async def cancellation_by_ratecode(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(CANCEL_VIEW)),
):
    return await run_in_threadpool(A.cancellation_by_ratecode, db, **_no_cancel(f))


@router.get("/cancellation/monthly", summary="逐月取消率")
async def cancellation_monthly(
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(CANCEL_VIEW)),
):
    return await run_in_threadpool(A.cancellation_monthly, db, **_no_cancel(f))


# ── 訂價 vs 實收（需兩個來源都匯入）─────────────────────────────────────────

@router.get("/rate-gap", summary="訂價 vs 實收差異")
async def rate_gap(
    gap_alert_pct: float = Query(10.0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(CANCEL_VIEW)),
):
    return await run_in_threadpool(
        A.rate_gap, db, gap_alert_pct=gap_alert_pct, limit=limit, **_no_cancel(f))


# ── 回訪分析（J12／J13）─────────────────────────────────────────────────────

@router.get("/repeat-guests", summary="回訪住客分析")
async def repeat_guests(
    min_visits: int = Query(2, ge=2, le=100),
    limit: int = Query(200, ge=1, le=1000),
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(CANCEL_VIEW)),
):
    return await run_in_threadpool(
        A.repeat_guests, db, min_visits=min_visits, limit=limit, **_no_cancel(f))


# ── 明細 ─────────────────────────────────────────────────────────────────────

@router.get("/list", summary="訂房明細（分頁）")
async def resv_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    f: dict = Depends(_filters),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    return await run_in_threadpool(A.resv_list, db, page=page, page_size=page_size, **f)


@router.get("/list/{resv_id}", summary="單筆訂房（Drawer：含住宿段與關聯分錄）")
async def resv_detail(
    resv_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(VIEW)),
):
    out = await run_in_threadpool(A.resv_detail, db, resv_id)
    if out is None:
        raise HTTPException(404, f"訂房 #{resv_id} 不存在")
    return out
