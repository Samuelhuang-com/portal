"""
營運分析 — 訂房 Pace／Pickup：API Router
Prefix: /api/v1/opera/pace

規格：`docs/SPEC_opera_pace.md`

⚠️ 本模組的歷史進度是以**訂房日回推**得出（`opera_reservation_sync` 是整列覆寫、
   無版本），已含後續改期與取消的結果。每個回應的 `source.population` 都會帶
   這句話，畫面必須顯示。

⚠️ 與 `/opera/reservations` 的差別：那邊看的是「訂單**現在**長什麼樣」，
   這邊看的是「某個**過去時點**看到的在手訂房」。多一個 `as_of` 維度。

⚠️ 查詢端點只讀本地資料表，**不打 OHIP**，所以很快也不計費。

⚠️ 全部端點皆為同步 def —— async def 直接呼叫同步 DB 會凍結整站。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.services import opera_pace_service as PS

router = APIRouter(dependencies=[Depends(get_current_user)])
_VIEW = require_permission("opera_pace_view")


def _bad(e: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(e))


@router.get("/data-range", summary="資料涵蓋範圍與快照就緒度")
def data_range(db: Session = Depends(get_db), _: User = Depends(_VIEW)):
    """涵蓋範圍、無法定位時點的取消筆數、快照累積天數。

    ⚠️ 入住日區間是**未來導向**，前端請用 antd 原生 RangePicker，
       不要用 StandardRangePicker（CLAUDE.md §8.4）。
    """
    return PS.data_range(db)


@router.get("/readiness", summary="快照累積天數（Phase 2 就緒度）")
def readiness(db: Session = Depends(get_db), _: User = Depends(_VIEW)):
    """快照精確版還需要累積幾天。只讀本地表，不打 OHIP。"""
    return PS.readiness(db)


@router.get("/curve", summary="訂房曲線（含去年同期）")
def curve(
    stay_date: str = Query(..., description="ISO YYYY-MM-DD"),
    compare: str = Query("weekday", pattern="^(weekday|date)$"),
    max_lead: int = Query(120, ge=7, le=365),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """單一入住日的 OTB 隨觀察日演進，附去年同期對照曲線。

    🎯 去年同期曲線用同一套回推邏輯即可得出 —— 快照路線要等滿一年。
    """
    try:
        return PS.curve(db, stay_date=stay_date, compare=compare, max_lead=max_lead)
    except ValueError as e:
        raise _bad(e)


@router.get("/otb-matrix", summary="入住日 × 提前期 OTB 矩陣")
def otb_matrix(
    start: str = Query(..., description="入住日起（ISO）"),
    end: str = Query(...),
    leads: str = Query("90,60,30,14,7,3,1,0", description="逗號分隔的提前期"),
    compare: str = Query("weekday", pattern="^(weekday|date)$"),
    as_of: str | None = Query(None, description="觀察日，預設今天"),
    window: int = Query(7, description="pickup 欄的觀察窗：1／3／7／14"),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """主表格。⚠️ 觀察日還沒到的格子回 `null` 而不是 0。

    ⚠️ `as_of` 未帶時預設今天。看歷史區間時務必帶上，否則 pickup 欄永遠是 0
       （「最近 7 天」對兩年前的入住日不會有任何異動）。
    """
    try:
        ls = tuple(sorted({int(x) for x in leads.split(",") if x.strip()},
                          reverse=True))
        if not ls or any(x < 0 or x > 365 for x in ls):
            raise ValueError("leads 需為 0～365 的整數")
        return PS.otb_matrix(db, start=start, end=end, leads=ls, compare=compare,
                             as_of=as_of, window=window)
    except ValueError as e:
        raise _bad(e)


@router.get("/pickup", summary="逐入住日 Pickup（新增／取消／淨）")
def pickup(
    start: str = Query(...), end: str = Query(...),
    window: int = Query(7, description="觀察窗天數：1／3／7／14"),
    as_of: str | None = Query(None, description="觀察日，預設今天"),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """🎯 新增與取消**分開列** —— 淨值相同不代表狀況相同。

    回應含 `verify`：OTB 差值應等於淨 pickup，不符會列在 warnings。
    """
    try:
        return PS.pickup(db, start=start, end=end, window=window, as_of=as_of)
    except ValueError as e:
        raise _bad(e)


@router.get("/pickup/dimension", summary="維度別 Pickup（參考值）")
def pickup_dimension(
    start: str = Query(...), end: str = Query(...),
    dimension: str = Query("market_code"),
    window: int = Query(7), as_of: str | None = Query(None),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """⚠️ 維度取自訂房**目前**的房型／通路，中途改過會算在新維度上。
    回應帶 `is_reference_only=true`，畫面必須標「參考值」。
    """
    try:
        return PS.pickup_dimension(db, start=start, end=end,
                                   dimension=dimension, window=window, as_of=as_of)
    except ValueError as e:
        raise _bad(e)


@router.get("/day-detail", summary="單日 Pickup 組成明細（Drawer）")
def day_detail(
    stay_date: str = Query(...), window: int = Query(7),
    as_of: str | None = Query(None),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """觀察窗內新增／取消了哪些訂單。

    ⚠️ 非 Ragic 來源，`ragic_url` 一律為空字串（CLAUDE.md §7 該欄不適用）。
    """
    try:
        return PS.day_detail(db, stay_date=stay_date, window=window, as_of=as_of)
    except ValueError as e:
        raise _bad(e)
