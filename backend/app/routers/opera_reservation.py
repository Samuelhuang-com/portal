"""
營運分析 — 訂房分析：API Router
Prefix: /api/v1/opera/reservations

⚠️ 母體與 `/opera/guest` 不同：本模組是**所有訂房**（含未來、含取消），
   `/opera/guest` 是**已離店的住客**（TXT Departure 報表）。
   同一維度數字不同是正常的 —— 每個回應的 `source.population` 都會帶這句話。

⚠️ 查詢端點只讀本地資料表，**不打 OHIP**，所以很快也不計費。
   只有 `/sync/*` 那兩支會實際呼叫 API。

⚠️ 全部端點皆為同步 def —— async def 直接呼叫同步 DB 會凍結整站。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.user import User
from app.services import opera_reservation_service as RS
from app.services import opera_reservation_sync as SY
from app.services.ohip_client import OhipError

router = APIRouter(dependencies=[Depends(get_current_user)])
_VIEW = require_permission("opera_reservation_view")


@router.get("/data-range", summary="資料涵蓋範圍（含未來）")
def data_range(db: Session = Depends(get_db), _: User = Depends(_VIEW)):
    """⚠️ 本模組**含未來資料**，所以 `end` 會是未來日期。
    過去導向的分析請用 `last_past` 當期間選擇器的 anchor（CLAUDE.md §8.2）。"""
    return RS.data_range(db)


@router.get("/booking-window", summary="訂房前置期分布（TXT 做不到）")
def booking_window(
    start: str = Query(..., description="ISO YYYY-MM-DD（依到達日）"),
    end: str = Query(...),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """提前多久訂的，以及各前置期的取消率。

    🎯 TXT Departure 報表**沒有任何訂房日期欄位**，這項只有 API 做得到。
    """
    try:
        return RS.booking_window(db, start=start, end=end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{e}")


@router.get("/cancellations", summary="取消分析（TXT 做不到）")
def cancellations(
    start: str = Query(...), end: str = Query(...),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """取消率、原因碼分布、取消提前期。

    ⚠️ 取消率的分母是**所有訂房**（含取消）。
    🎯 TXT 是 Departure 報表 —— 取消的訂房本質上不會出現在裡面。
    """
    try:
        return RS.cancellations(db, start=start, end=end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{e}")


@router.get("/on-the-books", summary="在手訂房（未來已訂房晚，TXT 做不到）")
def on_the_books(
    days_ahead: int = Query(90, ge=1, le=365),
    dimension: str = Query("market_code"),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """未來每一天目前已經訂了多少。已取消的不計入。"""
    return RS.on_the_books(db, days_ahead=days_ahead, dimension=dimension)


@router.get("/dimension", summary="維度統計（含填充率）")
def dimension(
    start: str = Query(...), end: str = Query(...),
    dimension: str = Query("market_code",
                           description="／".join(RS.DIMENSIONS.keys())),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """⚠️ 回應一定含 `coverage`。低填充率的維度（如 `company_name` 僅 15%）
    做成排行榜會嚴重偏頗，畫面**必須**顯示這個數字。"""
    try:
        return RS.dimension_stats(db, start=start, end=end, dimension=dimension)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{e}")


@router.get("/los", summary="住宿天數（LOS）分桶")
def los(
    start: str = Query(...), end: str = Query(...),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    try:
        return RS.los_buckets(db, start=start, end=end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{e}")


@router.get("/blocks", summary="團體 pickup（配房 vs 實際成交，TXT 做不到）")
def blocks(
    start: str = Query(...), end: str = Query(...),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    """🎯 `originalRooms`／`currentRooms`／`pickupRooms` 由 OPERA 直接提供。
    TXT 只有團體代號與名稱，**沒有任何配房數字**。

    ⚠️ 回應含 `cutoff_in_use` —— 若整批 `cutOffDays` 都是 0，
    代表這間飯店沒在用 cut-off，畫面應隱藏該欄而不是顯示一整排 0。
    """
    try:
        return RS.block_pickup(db, start=start, end=end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{e}")


# ── 同步 ─────────────────────────────────────────────────────────────────────

@router.get("/sync/status", summary="回補進度與同步紀錄")
def sync_status(
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db), _: User = Depends(_VIEW),
):
    return {
        "reservation": SY.backfill_progress(db, "reservation"),
        "block": SY.backfill_progress(db, "block"),
        "recent": SY.list_syncs(db, limit=limit),
        "data_range": RS.data_range(db),
        "config": {
            "backfill_years": SY.BACKFILL_YEARS,
            "reservation_chunk_days": SY.RSV_CHUNK_DAYS,
            "block_chunk_days": SY.BLK_CHUNK_DAYS,
            "incremental_days": SY.INCREMENTAL_DAYS,
            "store_contact_name": SY.STORE_CONTACT_NAME,
        },
    }


@router.post("/sync/backfill", summary="回補下一段歷史（管理員，可重複按到補完）")
def backfill(
    dataset: str = Query("reservation", description="reservation 或 block"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("system_admin")),
):
    """**每次只補一段**，回傳剩餘段數。

    ⚠️ 刻意不做成「一次補完兩年」：訂房兩年約 24 段、每段約 15 秒，
       一次跑完 HTTP 必逾時。做成可續跑後，中斷了也能接著補。
    ⚠️ 這支會實際打 OHIP 並**計費**。
    """
    if dataset not in ("reservation", "block"):
        raise HTTPException(status_code=400, detail="dataset 必須是 reservation 或 block")
    try:
        return SY.backfill_next_chunk(
            db, dataset,
            triggered_by=getattr(user, "email", "") or getattr(user, "username", ""))
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/sync/incremental", summary="手動跑一次每日增量（管理員）")
def incremental(
    days: int = Query(SY.INCREMENTAL_DAYS, ge=1, le=61),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("system_admin")),
):
    """平常由每日 07:00 排程執行。

    ⚠️ 增量區間**含未來 180 天** —— 在手訂房分析需要未來資料，
       只抓過去會讓那一頁永遠是空的。
    """
    try:
        return SY.sync_incremental(
            db, days=days,
            triggered_by=getattr(user, "email", "") or getattr(user, "username", ""))
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))
