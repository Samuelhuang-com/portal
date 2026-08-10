"""
即時營運 — API Router
Prefix: /api/v1/realtime

規格書：docs/SPEC_realtime_operations.md

⚠️ 與既有 `/api/v1/opera/*` 端點完全獨立，不共用資料表、不改動任何既有行為。
⚠️ 全部端點皆為同步 def —— async def 直接呼叫同步 DB 會凍結整站
   （見 CLAUDE.md 與 `project_async_def_blocking_fix` 的教訓）。
⚠️ 對 OHIP 一律唯讀，本 router 不提供任何**對 OHIP** 的寫入端點。
   `POST /snapshot/run` 是唯一的 POST：它觸發的是**對 OHIP 的讀取**，
   只寫入 Portal 自己的快照表，不會改動 OPERA 的任何資料。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import (get_current_user, require_any_permission,
                              require_permission, require_roles)
from app.models.user import User
from app.services import realtime_revenue_service as RS
from app.services import realtime_compare_service as CS
from app.services import ohip_snapshot_service as SS
from app.services import realtime_status_service as LS
from app.services.ohip_async_cache import CooldownActive
from app.services.ohip_client import OhipError

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/status", summary="即時房況（今日 + 未來 N 天，直接向 OPERA Cloud 取數）")
def live_status(
    days_ahead: int = Query(LS.DEFAULT_DAYS_AHEAD, ge=0, le=61,
                            description="往後幾天；API 硬限制單次最多 62 天"),
    force: bool = Query(False, description="略過 5 分鐘快取，強制重新呼叫"),
    db: Session = Depends(get_db),
    # 這支同時被「營運分析 Dashboard 頂端的即時區塊」與「OPERA API 串接 → 即時房況」
    # 兩處使用，因此兩個 key 任一即可 —— 否則 Dashboard 上的區塊會對既有使用者消失。
    user: User = Depends(require_any_permission("opera_view", "realtime_view")),
):
    """回傳全館層與房型層的逐日房況，並附 `source` 供畫面標示資料來源與抓取時間。

    ⚠️ 不含 ADR / RevPAR / 營收 —— 實測確認 OHIP 這支端點不回傳（見規劃文件 §4.3）。
    """
    try:
        return LS.get_live_status(
            db, days_ahead=days_ahead, force=force,
            triggered_by=getattr(user, "email", "") or getattr(user, "username", ""),
        )
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/business-date", summary="OPERA 當前營業日")
def business_date(
    db: Session = Depends(get_db),
    user: User = Depends(require_any_permission("opera_view", "realtime_view")),
):
    return LS.get_business_date(
        db, triggered_by=getattr(user, "email", "") or getattr(user, "username", ""),
    )


@router.get("/revenue", summary="營收與結構分析（非同步版 API，含房型別／市場區隔／取消率）")
def revenue(
    start: str = Query(..., description="ISO YYYY-MM-DD"),
    end: str = Query(..., description="ISO YYYY-MM-DD"),
    group_by: list[str] = Query(
        default=[],
        description="MarketCode / RoomType / GuaranteeType，可多選；空值為全館合計",
    ),
    force: bool = Query(
        False,
        description=("略過快取重新取數。⚠️ 相同條件距上次取數未滿 30 分鐘時會回 429 —— "
                     "OPERA 對非同步查詢強制此間隔，Portal 在本地先擋以免浪費計費呼叫"),
    ),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("realtime_revenue")),
):
    """區間營收，含 ADR／RevPAR／住房率／**取消率**。

    ⚠️ 走非同步 API（POST 啟動 → 輪詢 → GET），**實測單段約 3 秒**。
       單段上限先試 400 天（OPERA Cloud 23.2+），被拒自動降回 94 天。
    ⚠️ 這是 TXT 版做不到的三件事：房型別營收、市場區隔別營收、取消率。
    ⚠️ 回傳的 `source` 含 `cooldown_remaining_seconds` 與 `can_force`，
       前端據此決定「略過快取重查」按鈕要不要 disable。
    """
    try:
        return RS.get_revenue(
            db, start=start, end=end, group_by=group_by, force=force,
            triggered_by=getattr(user, "email", "") or getattr(user, "username", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{e}")
    except CooldownActive as e:
        # 429 = Too Many Requests。⚠️ 這一次**沒有真的打 OHIP** —— 是 Portal 本地擋下的。
        # Retry-After 用秒數，符合 RFC 7231，前端可直接拿來倒數。
        raise HTTPException(
            status_code=429, detail=str(e),
            headers={"Retry-After": str(e.remaining_seconds)},
        )
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/compare", summary="API vs TXT 逐欄比對（Phase 0-6 驗證工具）")
def compare_api_vs_txt(
    days_back: int = Query(30, ge=0, le=61, description="往前幾天"),
    days_ahead: int = Query(0, ge=0, le=61, description="往後幾天"),
    property_code: str = Query("", description="TXT 側 property 篩選；空字串不限"),
    tolerance: float = Query(0.0, ge=0, description="容許誤差絕對值；0 表示要求完全相同"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("realtime_compare")),
):
    """把 API 與 `opera_revenue_daily` 同一天、同一欄位攤開對照。

    ⚠️ **房況**（同步版）每次都直打，不走快取 —— 比對是查證行為。
    ⚠️ **營收**（非同步版）2026-08-07 起改走 30 分鐘落地快取：
       OPERA 對相同條件的非同步查詢強制最短間隔 30 分鐘，
       「每次都拿當下真值」在該端點上物理上做不到。
       冷卻中會在 `meta.revenue_error` 說明，房況比對不受影響。
    ⚠️ 營收類欄位 API 不回傳，標示為 `api_unavailable`，不計入差異統計。
    """
    try:
        return CS.compare(
            db, days_back=days_back, days_ahead=days_ahead,
            property_code=property_code, tolerance=tolerance,
            triggered_by=getattr(user, "email", "") or getattr(user, "username", ""),
        )
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/logs", summary="OHIP API 呼叫紀錄")
def call_logs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("opera_view", "realtime_view")),
):
    """只記錄**實際發出**的呼叫；快取命中不會出現在這裡。"""
    return LS.get_call_logs(db, limit=limit, offset=offset)


# ═══════════════════════════════════════════════════════════════════════════
# 每日快照（2026-08-07 新增）
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/snapshot/runs", summary="每日快照的執行紀錄與累積覆蓋情形")
def snapshot_runs(
    limit: int = Query(60, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("opera_view", "realtime_view")),
):
    """回傳最近幾次的快照執行紀錄，以及 `coverage` 區塊。

    ⚠️ 有兩個數字要一起看：
       - `coverage.distinct_snapshot_days`：已累積幾天的快照
       - `coverage.business_days_with_final`：**有幾天已取得「最終實績」**
         （即有 `lead_days < 0` 的紀錄）。pickup 曲線要有基準線才判讀得出
         「進度算好還是壞」，所以這個數字才是真正的門檻，通常比上面那個少。
    """
    return SS.list_runs(db, limit=limit)


@router.post("/snapshot/run", summary="手動執行一次每日快照（管理員）")
def snapshot_run_now(
    horizon_days: int = Query(SS.HORIZON_DAYS, ge=1, le=400,
                              description="今日起往後幾天；預設 180"),
    lookback_days: int = Query(SS.LOOKBACK_DAYS, ge=0, le=61,
                               description=("往前回看幾天；預設 7。"
                                            "回看是為了拿到 pickup 曲線的終點 —— "
                                            "設 0 就永遠拿不到任何一天的最終實績")),
    include_revenue: bool = Query(True, description="是否一併抓營收（較慢）"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("system_admin")),
):
    """立刻跑一次快照。**同一天重跑會覆蓋當天的快照**（冪等）。

    用途：首次上線先補一天、排程失敗後補跑、或調整參數後驗證。

    ⚠️ 這支會實際打 OHIP（房況 3 次 + 營收 4 次，約 20 秒），且**計費**。
       平常請讓每日 06:00 的排程自己跑，不要手動觸發。
    ⚠️ 補跑**只能補「今天」** —— API 沒有「回到過去」的參數，
       昨天沒跑到的快照永遠補不回來。這是本模組的根本限制，不是 bug。
       （`lookback_days` 抓的是「過去日期**現在**看起來如何」，
       不是「過去某一天當時看未來如何」，兩者不同，不要混淆。）
    """
    try:
        return SS.run_snapshot(
            db, horizon_days=horizon_days, lookback_days=lookback_days,
            include_revenue=include_revenue,
            triggered_by=getattr(user, "email", "") or getattr(user, "username", ""),
        )
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))
