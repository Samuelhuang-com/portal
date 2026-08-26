"""
OTA 口碑分析 — 統計 API Router
Prefix: /api/v1/ota/stats

規格：`docs/SPEC_ota_reviews.md` §8.2

⚠️ 全部端點皆為同步 def。
⚠️ 所有統計一律用 `score_10`（統一 10 分制），並排除跨站重複與空日期。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.ota_review import (AlertAgingOut, AlertDailyOut, DataRangeOut,
                                    MonthlyPoint, OverviewOut, OtaReviewListOut,
                                    PlatformStat, ScoreDistributionOut,
                                    TopicStat)
from app.services import ota_review_service as RS
from app.services import ota_stats_service as SS

router = APIRouter(dependencies=[Depends(get_current_user)])
_VIEW = require_permission("ota_view")
_TREND = require_permission("ota_trend_view")
_ALERT = require_permission("ota_alerts_view")


@router.get("/data-range", response_model=DataRangeOut, summary="評論資料涵蓋範圍")
def data_range(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """
    ⚠️ 前端 `StandardRangePicker` 的 `anchor` **必須**取本端點的 `end`，
       不可用 `dayjs()`（CLAUDE.md §8.2）。

       OTA 評論落後現實好幾天 —— 客人退房後才留言，爬蟲又是每日排程。
       以今天為基準的「本月」會選到一片還沒有資料的日子，
       使用者會誤以為資料缺漏。
    """
    return SS.get_data_range(db, hotel_code)


@router.get("/overview", response_model=OverviewOut, summary="Dashboard KPI")
def overview(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    platform: str = Query("", description="平台代碼；**逗號串接可多選**（booking,agoda）。單值格式向下相容"),
    start: str = Query(""),
    end: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """本月／上月以**資料最後一天**所在月份為準，不是今天。"""
    return SS.get_overview(db, hotel_code=hotel_code, platform=platform, start=start, end=end)


@router.get("/monthly", response_model=list[MonthlyPoint], summary="月度分數趨勢（雙館）")
def monthly(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    platform: str = Query("", description="平台代碼；**逗號串接可多選**（booking,agoda）。單值格式向下相容"),
    start: str = Query(""),
    end: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(_TREND),
):
    return SS.get_monthly(db, hotel_code=hotel_code, platform=platform, start=start, end=end)


@router.get("/platform", response_model=list[PlatformStat], summary="各 OTA 平均分對照")
def platform_stats(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    start: str = Query(""),
    end: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(_TREND),
):
    return SS.get_platform_stats(db, hotel_code=hotel_code, start=start, end=end)


@router.get("/topics", response_model=list[TopicStat], summary="主題分佈（負面提及優先）")
def topics(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    platform: str = Query("", description="平台代碼；**逗號串接可多選**（booking,agoda）。單值格式向下相容"),
    start: str = Query(""),
    end: str = Query(""),
    include_duplicate: bool = Query(False, description="是否含跨站重複的評論（要與清單頁一致）"),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """
    P4 分析引擎上線前會回空陣列（`topics_json` 尚未填值）。

    ⚠️ `include_duplicate` 必須與清單頁一致（2026-08-25）——
       清單有「顯示重複」開關，圖不跟著動就會出現
       「圖上寫 12、點下去只有 9 筆」。
    """
    return SS.get_topic_stats(db, hotel_code=hotel_code, platform=platform,
                              start=start, end=end,
                              include_duplicate=include_duplicate)


@router.get("/score-distribution", response_model=ScoreDistributionOut,
            summary="分數分布（清單頁的橫條）")
def score_distribution(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    platform: str = Query("", description="平台代碼；**逗號串接可多選**（booking,agoda）。單值格式向下相容"),
    start: str = Query(""),
    end: str = Query(""),
    include_duplicate: bool = Query(False, description="是否含跨站重複的評論"),
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """
    ⚠️ **參數必須與清單頁完全一致**（含 `include_duplicate`），
       否則會出現「圖上寫 12、點下去只有 9 筆」——
       那種不一致比沒有圖更糟，因為它看起來是對的。

    ⚠️ 這裡**不吃 `score_below` 之類的分數篩選**：這張圖是給人選分數區間的，
       自己先被分數篩過就只會剩一根柱子。
    """
    return SS.get_score_distribution(
        db, hotel_code=hotel_code, platform=platform,
        start=start, end=end, include_duplicate=include_duplicate)


@router.get("/alert-aging", response_model=AlertAgingOut, summary="警示積壓天數分桶")
def alert_aging(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    platform: str = Query("", description="平台代碼；**逗號串接可多選**（booking,agoda）。單值格式向下相容"),
    db: Session = Depends(get_db),
    _: User = Depends(_ALERT),
):
    """
    待處理警示放了多久（2026-08-25）。

    ⚠️ **不吃 start／end**。積壓是相對於「現在」的，硬加期間篩選會變成
       「在某段期間留言、而且到今天還沒處理的」—— 那是另一個問題，
       而且很容易被誤讀成「這段期間的積壓狀況」。

    ⚠️ 起算日是**客人留言那天**（`review_date`），不是我們抓到的那天。
       第一次回補歷史評論後，舊評論會全部落在最後一桶 ——
       那是這個口徑的必然結果，不是計算錯誤（前端有註明）。
    """
    return SS.get_alert_aging(db, hotel_code=hotel_code, platform=platform)


@router.get("/alert-daily", response_model=AlertDailyOut, summary="每日警示條帶")
def alert_daily(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    platform: str = Query("", description="平台代碼；**逗號串接可多選**（booking,agoda）。單值格式向下相容"),
    days: int = Query(60, ge=1, le=180, description="回看幾天"),
    db: Session = Depends(get_db),
    _: User = Depends(_ALERT),
):
    """
    最近 N 天每天發生幾件警示。

    ⚠️⚠️ **與 `/alert-aging` 的口徑不同**：

      · `/alert-aging` ＝ 還沒處理的**存量**（open + acknowledged）
      · 這一支　　　　 ＝ 當天**發生**了幾件（不論後來處理了沒）

    只算未處理的話，處理完的日子會變乾淨 —— 看起來像那幾天沒出事。
    兩個口徑都對，但畫面上必須講清楚，否則就是「兩個數字對不起來」。

    ⚠️ 回傳的 `no_data` 標記哪幾天**還沒有資料**（晚於評論資料的最後一天）。
       OTA 評論落後現實好幾天，不分開標的話最近幾格會顯示 0，
       看起來像「這幾天很平靜」。
    """
    return SS.get_alert_daily(db, hotel_code=hotel_code, platform=platform, days=days)


@router.get("/alerts", response_model=OtaReviewListOut, summary="負評警示清單")
def alerts(
    hotel_code: str = Query("", description="飯店代碼；**逗號串接可多選**（HANNS,HANNS_SUMMER）。單值格式向下相容"),
    platform: str = Query("", description="平台代碼；**逗號串接可多選**（booking,agoda）。單值格式向下相容"),
    start: str = Query(""),
    end: str = Query(""),
    alert_status: str = Query("", description="open / acknowledged / resolved / ignored"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(_ALERT),
):
    return RS.list_reviews(
        db, page=page, page_size=page_size,
        hotel_code=hotel_code, platform=platform, start=start, end=end,
        alert_only=True, alert_status=alert_status,
    )


@router.get("/hotels", summary="飯店篩選選項")
def hotels(db: Session = Depends(get_db), _: User = Depends(_VIEW)):
    return SS.hotel_options(db)
