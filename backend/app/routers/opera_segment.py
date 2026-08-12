"""
營運分析 — 市場區隔／房型別趨勢：API Router
Prefix: /api/v1/opera/segments

決策依據：`docs/EVAL_ohip_strategic_data.md` §4.3（重寫後的順位 2'）

⚠️ 資料來源是 **OHIP API 落地**，不是 `/opera/*` 其他頁面的 TXT 上傳。
   頁面放在「營運分析」是因為**時間語意一致**（都是落地的歷史資料），
   但畫面必須標示來源，不可與 TXT 混用 —— 兩者口徑尚未完全對齊
   （對齊工作在 `/realtime/compare`）。

⚠️ 全部端點皆為同步 def —— async def 直接呼叫同步 DB 會凍結整站
   （見 CLAUDE.md 與 `project_async_def_blocking_fix` 的教訓）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, require_roles
from app.models.user import User
from app.services import opera_segment_service as SS
from app.services import opera_segment_sync as SY
from app.services.ohip_client import OhipError

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", summary="市場區隔／房型別的結構、逐月趨勢與 YoY")
def segments(
    start: str = Query(..., description="ISO YYYY-MM-DD"),
    end: str = Query(..., description="ISO YYYY-MM-DD"),
    dimension: str = Query(SS.DIM_MARKET, description="market_code 或 room_type"),
    compare_yoy: bool = Query(True, description="是否一併撈去年同期"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_segment_view")),
):
    """讀本地落地資料，**不打 OHIP**，所以很快、也不計費。

    ⚠️ 比率一律**加權**（SUM ÷ SUM），不是逐日平均。
    ⚠️ 去年同期為 0 或缺值時，YoY 回 `null` 而非 0 或 100% ——
       「去年沒有」與「持平」是完全不同的事。
    """
    try:
        return SS.analyze(db, start=start, end=end,
                          dimension=dimension, compare_yoy=compare_yoy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期格式錯誤：{e}")


@router.get("/options", summary="該維度出現過哪些值")
def options(
    dimension: str = Query(SS.DIM_MARKET),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_segment_view")),
):
    return {"dimension": dimension, "values": SS.dimension_options(db, dimension=dimension)}


@router.get("/sync/status", summary="回補進度與同步紀錄")
def sync_status(
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("opera_segment_view")),
):
    """`progress.pending_chunks` 是最該看的數字 —— 還有幾段沒補。"""
    return {
        "progress": SY.backfill_progress(db),
        "recent": SY.list_syncs(db, limit=limit),
        "data_range": SS.data_range(db),
        # 與 GET /segments 共用同一份。回補完成前前端不會呼叫 /segments，
        # 但畫面上的「?」說明那時候就要能顯示（不在前端寫死）。
        "source": SS.source_info(),
        "config": {
            "backfill_years": SY.BACKFILL_YEARS,
            "chunk_days": SY.CHUNK_DAYS,
            "incremental_days": SY.INCREMENTAL_DAYS,
        },
    }


@router.post("/sync/backfill", summary="回補下一段歷史（管理員，可重複按到補完）")
def backfill(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("system_admin")),
):
    """**每次只補一段**（預設 45 天），回傳剩餘段數。

    ⚠️ 刻意不做成「一次補完兩年」：
       兩年約 17 段、每段約 3 秒，一次跑完 HTTP 會逾時。
       做成可續跑之後，中斷了也能接著補，不必從頭來。
    ⚠️ 這支會實際打 OHIP 並**計費**。
    """
    try:
        return SY.backfill_next_chunk(
            db, triggered_by=getattr(user, "email", "") or getattr(user, "username", ""))
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/sync/incremental", summary="手動跑一次每日增量（管理員）")
def incremental(
    days: int = Query(SY.INCREMENTAL_DAYS, ge=1, le=61,
                      description="重抓最近幾天並覆蓋；預設 14"),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("system_admin")),
):
    """平常由每日 06:30 排程自動執行，這支只用於補跑或驗證。

    ⚠️ 重抓最近幾天（而不是只抓昨天）是刻意的：
       OPERA 日結後帳務還可能修正，排程也可能漏跑，
       覆蓋式重抓能自動修好這兩種情況。
    """
    try:
        return SY.sync_incremental(
            db, days=days,
            triggered_by=getattr(user, "email", "") or getattr(user, "username", ""))
    except OhipError as e:
        raise HTTPException(status_code=502, detail=str(e))
