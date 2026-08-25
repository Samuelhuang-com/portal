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
from app.schemas.ota_review import (DataRangeOut, MonthlyPoint, OverviewOut,
                                    OtaReviewListOut, PlatformStat, TopicStat)
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
    db: Session = Depends(get_db),
    _: User = Depends(_VIEW),
):
    """P4 分析引擎上線前會回空陣列（`topics_json` 尚未填值）。"""
    return SS.get_topic_stats(db, hotel_code=hotel_code, platform=platform, start=start, end=end)


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
