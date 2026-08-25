"""
OTA 口碑分析 — 統計 service

規格書：`docs/SPEC_ota_reviews.md` §8.2

═══════════════════════════════════════════════════════════════════════════
本檔的兩條鐵律
═══════════════════════════════════════════════════════════════════════════
1. **一律用 `score_10`**，永遠不要出現 `AVG(score_raw)`。
   Booking 是 10 分制、Tripadvisor 是 5 分制，混在一起平均出來的數字是錯的。

2. **一律排除 `is_duplicate=True` 與空 `review_month`**。
   前者是跨站重複（會重複計數），後者是日期解析失敗（不屬於任何月份）。
"""
from __future__ import annotations

from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.orm import Session

from app.models.ota_review import OtaReview, OtaSource
from app.schemas.ota_review import (DataRangeOut, MonthlyPoint, OverviewOut,
                                    PlatformStat, TopicStat)
from app.services.ota_normalize import (NEGATIVE_SCORE_MAX, PLATFORM_LABEL,
                                        split_codes)

# SQLite 的 Numeric 欄位在 AVG 前需要轉 Float，否則回傳 Decimal 精度會怪
_SCORE = cast(OtaReview.score_10, Float)

# ⚠️ 指向 `ota_normalize.NEGATIVE_SCORE_MAX`，不要在這裡寫死數字 ——
#    兩份會漂移，症狀是兩個畫面的數字對不起來且沒有錯誤訊息。
NEGATIVE_THRESHOLD = NEGATIVE_SCORE_MAX


def _base_filters(stmt, hotel_code: str = "", platform: str = ""):
    """
    ⚠️ `hotel_code`／`platform` 自 2026-08-25 起**可以是逗號串接的多值**
       （`"HANNS,HANNS_SUMMER"`）。單值仍然照舊，格式向下相容。

    ⚠️ 拆解一律走 `split_codes()`，**不要在這裡自己 split** ——
       這個函式與 `ota_review_service` 那支是同一種篩選的兩個實作，
       只要有一邊自己解析，兩個畫面的數字遲早會對不起來。
    """
    stmt = stmt.where(OtaReview.is_duplicate.is_(False))
    hotels = split_codes(hotel_code)
    if hotels:
        stmt = stmt.where(OtaReview.hotel_code.in_(hotels))
    platforms = split_codes(platform)
    if platforms:
        stmt = stmt.where(OtaReview.platform.in_(platforms))
    return stmt


def _date_filters(stmt, start: str = "", end: str = ""):
    if start:
        stmt = stmt.where(OtaReview.review_date >= start, OtaReview.review_date != "")
    if end:
        stmt = stmt.where(OtaReview.review_date <= end, OtaReview.review_date != "")
    return stmt


def get_data_range(db: Session, hotel_code: str = "") -> DataRangeOut:
    """
    ⚠️ 這支端點存在的唯一理由：前端 `StandardRangePicker` 的 `anchor`。

    CLAUDE.md §8.2 規定快捷選項必須以「資料最後一天」為基準而非今天。
    OTA 評論落後現實好幾天（客人退房後才留言 + 爬蟲每日才跑），
    若用 `dayjs()` 當基準，「本月」會選到一片空白，使用者會誤判成資料缺漏。
    """
    stmt = _base_filters(
        select(
            func.min(OtaReview.review_date),
            func.max(OtaReview.review_date),
            func.count(OtaReview.id),
        ).where(OtaReview.review_date != ""),
        hotel_code,
    )
    start, end, total = db.execute(stmt).one()
    return DataRangeOut(start=start or "", end=end or "", total=total or 0)


def get_overview(
    db: Session, *, hotel_code: str = "", platform: str = "",
    start: str = "", end: str = "",
) -> OverviewOut:
    """Dashboard KPI。"""
    stmt = _date_filters(
        _base_filters(
            select(
                func.count(OtaReview.id),
                func.avg(_SCORE),
                func.sum(case((_SCORE < NEGATIVE_THRESHOLD, 1), else_=0)),
                func.sum(case(
                    ((OtaReview.is_alert.is_(True)) & (OtaReview.alert_status == "open"), 1),
                    else_=0,
                )),
            ),
            hotel_code, platform,
        ),
        start, end,
    )
    total, avg_score, negative, alert_open = db.execute(stmt).one()

    # 「本月 / 上月」以**資料最後一天**所在的月份為準，不是今天
    # （理由同 get_data_range —— 用今天會抓到還沒有資料的月份）
    data_range = get_data_range(db, hotel_code)
    this_month = data_range.end[:7] if data_range.end else ""
    last_month = _prev_month(this_month)

    def month_stat(month: str) -> tuple[int, float | None]:
        if not month:
            return 0, None
        row = db.execute(
            _base_filters(
                select(func.count(OtaReview.id), func.avg(_SCORE))
                .where(OtaReview.review_month == month),
                hotel_code, platform,
            )
        ).one()
        return row[0] or 0, (round(float(row[1]), 2) if row[1] is not None else None)

    this_count, this_avg = month_stat(this_month)
    last_count, last_avg = month_stat(last_month)

    return OverviewOut(
        total=total or 0,
        avg_score_10=round(float(avg_score), 2) if avg_score is not None else None,
        negative_count=int(negative or 0),
        alert_open_count=int(alert_open or 0),
        this_month_count=this_count,
        last_month_count=last_count,
        this_month_avg=this_avg,
        last_month_avg=last_avg,
    )


def _prev_month(month: str) -> str:
    """`2026-08` → `2026-07`；空字串進、空字串出。"""
    if len(month) != 7:
        return ""
    year, mon = int(month[:4]), int(month[5:7])
    mon -= 1
    if mon == 0:
        mon, year = 12, year - 1
    return f"{year:04d}-{mon:02d}"


def get_monthly(
    db: Session, *, hotel_code: str = "", platform: str = "",
    start: str = "", end: str = "",
) -> list[MonthlyPoint]:
    """月度趨勢（雙館各一條線）。"""
    stmt = _date_filters(
        _base_filters(
            select(
                OtaReview.review_month,
                OtaReview.hotel_code,
                func.avg(_SCORE),
                func.count(OtaReview.id),
                # ⭐ 與 Dashboard KPI **同一組條件**（2026-08-23）——
                #    月度圖上的「負評 18 / 警示 30」要跟上面的卡片對得起來，
                #    所以這兩個彙總必須跟 get_overview() 寫成一樣的式子。
                func.sum(case((_SCORE < NEGATIVE_THRESHOLD, 1), else_=0)),
                func.sum(case(
                    ((OtaReview.is_alert.is_(True))
                     & (OtaReview.alert_status == "open"), 1),
                    else_=0,
                )),
            ).where(OtaReview.review_month != ""),
            hotel_code, platform,
        ),
        start, end,
    ).group_by(OtaReview.review_month, OtaReview.hotel_code) \
     .order_by(OtaReview.review_month, OtaReview.hotel_code)

    names = _hotel_names(db)
    return [
        MonthlyPoint(
            review_month=month,
            hotel_code=code,
            hotel_name=names.get(code, code),
            avg_score_10=round(float(avg), 2) if avg is not None else None,
            count=count or 0,
            negative_count=int(neg or 0),
            alert_open_count=int(alert or 0),
        )
        for month, code, avg, count, neg, alert in db.execute(stmt).all()
    ]


def get_platform_stats(
    db: Session, *, hotel_code: str = "", start: str = "", end: str = "",
) -> list[PlatformStat]:
    """各 OTA 平均分對照（雙館分開）。"""
    stmt = _date_filters(
        _base_filters(
            select(
                OtaReview.platform,
                OtaReview.hotel_code,
                func.avg(_SCORE),
                func.count(OtaReview.id),
            ),
            hotel_code,
        ),
        start, end,
    ).group_by(OtaReview.platform, OtaReview.hotel_code) \
     .order_by(OtaReview.platform, OtaReview.hotel_code)

    return [
        PlatformStat(
            platform=platform,
            platform_label=PLATFORM_LABEL.get(platform, platform),
            hotel_code=code,
            avg_score_10=round(float(avg), 2) if avg is not None else None,
            count=count or 0,
        )
        for platform, code, avg, count in db.execute(stmt).all()
    ]


def get_topic_stats(
    db: Session, *, hotel_code: str = "", platform: str = "",
    start: str = "", end: str = "",
) -> list[TopicStat]:
    """
    主題分佈。

    `topics_json` 存的是 `["清潔:neg", "服務:pos"]` 形式，
    在 Python 端聚合而非 SQL —— SQLite 沒有 JSON 陣列展開，
    且資料量級（每月百餘筆）用不著另建關聯表。
    """
    import json

    stmt = _date_filters(
        _base_filters(
            select(OtaReview.topics_json).where(OtaReview.topics_json.isnot(None)),
            hotel_code, platform,
        ),
        start, end,
    )

    buckets: dict[str, dict[str, int]] = {}
    for (topics_json,) in db.execute(stmt).all():
        try:
            tags = json.loads(topics_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(tags, list):
            continue
        for tag in tags:
            name, _, polarity = str(tag).partition(":")
            bucket = buckets.setdefault(name, {"neg": 0, "pos": 0})
            if polarity == "pos":
                bucket["pos"] += 1
            else:
                bucket["neg"] += 1

    stats = [
        TopicStat(
            topic=name,
            negative_count=counts["neg"],
            positive_count=counts["pos"],
            total_count=counts["neg"] + counts["pos"],
        )
        for name, counts in buckets.items()
    ]
    # 負面提及多的排前面 —— 這張表是拿來找問題的，不是拿來看好話的
    stats.sort(key=lambda s: (-s.negative_count, -s.total_count, s.topic))
    return stats


def _hotel_names(db: Session) -> dict[str, str]:
    rows = db.execute(
        select(OtaSource.hotel_code, OtaSource.hotel_name).distinct()
    ).all()
    return {code: name or code for code, name in rows if code}


def hotel_options(db: Session) -> list[dict]:
    """前端篩選下拉用。"""
    return [{"value": code, "label": name} for code, name in sorted(_hotel_names(db).items())]
