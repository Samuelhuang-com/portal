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

from datetime import date, timedelta

from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.orm import Session

from app.models.ota_review import OtaReview, OtaSource
from app.schemas.ota_review import (AlertAgingBucket, AlertAgingOut,
                                    DataRangeOut, MonthlyPoint, OverviewOut,
                                    AlertDailyOut, AlertDailyPoint,
                                    PlatformStat, ScoreBucket,
                                    ScoreDistributionOut, TopicStat)
from app.services.ota_normalize import (NEGATIVE_SCORE_MAX, PLATFORM_LABEL,
                                        split_codes)

# SQLite 的 Numeric 欄位在 AVG 前需要轉 Float，否則回傳 Decimal 精度會怪
_SCORE = cast(OtaReview.score_10, Float)

# ⚠️ 指向 `ota_normalize.NEGATIVE_SCORE_MAX`，不要在這裡寫死數字 ——
#    兩份會漂移，症狀是兩個畫面的數字對不起來且沒有錯誤訊息。
NEGATIVE_THRESHOLD = NEGATIVE_SCORE_MAX


def _base_filters(stmt, hotel_code: str = "", platform: str = "",
                  include_duplicate: bool = False):
    """
    ⚠️ `hotel_code`／`platform` 自 2026-08-25 起**可以是逗號串接的多值**
       （`"HANNS,HANNS_SUMMER"`）。單值仍然照舊，格式向下相容。

    ⚠️ 拆解一律走 `split_codes()`，**不要在這裡自己 split** ——
       這個函式與 `ota_review_service` 那支是同一種篩選的兩個實作，
       只要有一邊自己解析，兩個畫面的數字遲早會對不起來。

    ⚠️ `include_duplicate` 必須是**參數**，不可以在外面「補一條 WHERE 取消它」。
       2026-08-25 第一版試過 `stmt.where(is_duplicate.in_([True, False]))` ——
       那是**再 AND 一個條件**，不是撤銷前面那條，
       所以重複的評論照樣被擋掉。**看起來有做事，其實是 no-op。**
       SQLAlchemy 的 `.where()` 只會疊加，沒有「移除某個條件」這種操作。
    """
    if not include_duplicate:
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
    start: str = "", end: str = "", include_duplicate: bool = False,
) -> list[TopicStat]:
    """
    主題分佈。

    `topics_json` 存的是 `["清潔:neg", "服務:pos"]` 形式，
    在 Python 端聚合而非 SQL —— SQLite 沒有 JSON 陣列展開，
    且資料量級（每月百餘筆）用不著另建關聯表。

    ⚠️ `include_duplicate` 2026-08-25 補上：清單頁的主題發散長條會用這支，
       而清單有「顯示重複」開關。不跟著動的話會出現
       「圖上寫 12、點下去只有 9 筆」——
       那種不一致比沒有圖更糟，因為它看起來是對的。
    """
    import json

    stmt = _date_filters(
        _base_filters(
            select(OtaReview.topics_json).where(OtaReview.topics_json.isnot(None)),
            hotel_code, platform, include_duplicate,
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


# ══════════════════════════════════════════════════════════════════════════
# 警示積壓分桶（2026-08-25）
# ══════════════════════════════════════════════════════════════════════════
# 這張圖回答的問題不是「有幾件待處理」（KPI 卡已經有了），
# 而是**「有幾件放太久」** —— 工作佇列真正會出事的地方。
#
# ⚠️ 起算日＝**客人留言那天**（`review_date`），2026-08-25 使用者裁示。
#    語意是「客人抱怨到現在多久沒人理」，不是「我們抓到之後多久沒處理」。
#
#    **已知的副作用**：第一次回補歷史評論之後，那幾百則舊評論會全部
#    落在最後一桶。那不是 bug，是這個口徑的必然結果 ——
#    畫面上每根柱子都必須標數字，不能只靠長度，否則其他三桶會被壓成看不見。
#
# ⚠️ 「積壓中」＝ `open` + `acknowledged`（使用者裁示）。
#    「已知悉」代表有人看過但還沒處理完 —— 它仍然是未完成的工作，
#    蔽掉的話畫面很乾淨但事情沒做完。
ALERT_OPEN_STATUSES = ("open", "acknowledged")

# (key, label, 起, 迄)　迄為 None ＝ 沒有上限
ALERT_AGING_BUCKETS: tuple[tuple[str, str, int, int | None], ...] = (
    ("0_3", "0–3 天", 0, 3),
    ("4_7", "4–7 天", 4, 7),
    ("8_14", "8–14 天", 8, 14),
    ("15_plus", "15 天以上", 15, None),
)


def get_alert_aging(db: Session, hotel_code: str = "",
                    platform: str = "") -> AlertAgingOut:
    """
    待處理警示的積壓天數分桶。

    ⚠️ **`as_of` 用今天，不是資料最後一天。**
       CLAUDE.md §8.2 規定期間快捷要以資料最後一天為基準，那是為了避免
       「本月」選到還沒有資料的日子。但**積壓是相對於現在**的：
       客人三週前抱怨就是積壓三週，跟我們什麼時候爬到無關。
       這裡用 `date.today()` 是刻意的例外，不是漏改。

    ⚠️ 日期解析不出來的評論**單獨計數回傳**，不可以靜默丟掉 ——
       不然 `sum(buckets)` 會小於待處理總數，看起來像圖表算錯。
    """
    today = date.today()

    stmt = _base_filters(
        select(OtaReview.review_date, func.count(OtaReview.id))
        .where(OtaReview.is_alert.is_(True))
        .where(OtaReview.alert_status.in_(ALERT_OPEN_STATUSES))
        .group_by(OtaReview.review_date),
        hotel_code, platform,
    )

    counts = {key: 0 for key, _, _, _ in ALERT_AGING_BUCKETS}
    unknown = 0
    total = 0

    for review_date, count in db.execute(stmt).all():
        if not review_date:
            unknown += count
            continue
        try:
            days = (today - date.fromisoformat(review_date)).days
        except ValueError:
            # ⚠️ 存進來就不該是壞格式，但真的壞了要算進 unknown 而不是當成 0 天
            unknown += count
            continue
        # ⚠️ 未來日期（時區或站方誤植）夾成 0，不要變成負數跑進最後一桶
        days = max(days, 0)
        for key, _label, lo, hi in ALERT_AGING_BUCKETS:
            if days >= lo and (hi is None or days <= hi):
                counts[key] += count
                total += count
                break

    last_key = ALERT_AGING_BUCKETS[-1][0]
    return AlertAgingOut(
        buckets=[
            AlertAgingBucket(
                key=key, label=label, count=counts[key],
                min_days=lo, max_days=hi, is_overdue=(key == last_key),
            )
            for key, label, lo, hi in ALERT_AGING_BUCKETS
        ],
        total=total,
        unknown_count=unknown,
        as_of=today.isoformat(),
    )


# ══════════════════════════════════════════════════════════════════════════
# 分數分布（2026-08-25）
# ══════════════════════════════════════════════════════════════════════════
# 清單頁上方的一排橫條：一眼看出分布，而且**點哪條就篩哪一段**。
# 在這之前要看低分評論得自己在「低分」欄打一個數字。
#
# ⚠️ **最後一格的邊界綁 `NEGATIVE_SCORE_MAX`，不可以寫死 6**。
#    那一格正好等於 Dashboard 的「負面評論」KPI（`score_10 < 6`）——
#    兩個畫面的數字可以互相驗證。哪天門檻改了，兩邊必須一起動；
#    寫死的話會變成「兩個畫面各說各話而且沒有錯誤訊息」。
#
# ⚠️ 區間一律是**半開** `[lo, hi)`，最高那格例外（含 10.0）。
#    用 `8.0–8.9` 這種閉區間表示法會漏掉 8.95 —— OTA 分數不保證只有一位小數
#    （Tripadvisor 的 5 分制換算後會出現 x.5 以外的值）。
SCORE_BUCKETS: tuple[tuple[str, str, float, float | None], ...] = (
    ("9_10", "9 – 10 分", 9.0, None),      # None ＝ 沒有上限（含滿分）
    ("8_9", "8 – 9 分", 8.0, 9.0),
    ("7_8", "7 – 8 分", 7.0, 8.0),
    ("6_7", "6 – 7 分", NEGATIVE_THRESHOLD, 7.0),
    ("below_6", f"低於 {NEGATIVE_THRESHOLD:g} 分", None, NEGATIVE_THRESHOLD),
)


def get_score_distribution(
    db: Session, *, hotel_code: str = "", platform: str = "",
    start: str = "", end: str = "", include_duplicate: bool = False,
) -> ScoreDistributionOut:
    """
    分數分布（清單頁上方的橫條）。

    ⚠️ **篩選條件必須跟清單完全一致**，否則「圖上寫 12、點下去只有 9 筆」。
       所以這裡吃的參數與 `list_reviews` 同一組（含 `include_duplicate`）。

    ⚠️ 沒有分數的評論（`score_10` 為 NULL）**單獨回報**，不可靜默丟掉 ——
       理由同積壓分桶：不講的話 `sum(桶) < 總數`，看起來像算錯。
       實際會發生：Expedia 有些版型抓不到分制，normalize 會留白。
    """
    # ⚠️ 清單頁有「顯示重複」開關，開著的時候這張圖也要跟著含進來，
    #    否則兩邊的總數對不起來。**交給 `_base_filters` 決定要不要加那條
    #    WHERE**，不要在外面補一條想把它取消（做不到，見該函式說明）。
    stmt = _date_filters(
        _base_filters(
            select(OtaReview.score_10, func.count(OtaReview.id))
            .group_by(OtaReview.score_10),
            hotel_code, platform, include_duplicate,
        ),
        start, end,
    )

    counts = {key: 0 for key, _, _, _ in SCORE_BUCKETS}
    no_score = 0
    total = 0

    for score, count in db.execute(stmt).all():
        if score is None:
            no_score += count
            continue
        value = float(score)
        for key, _label, lo, hi in SCORE_BUCKETS:
            if (lo is None or value >= lo) and (hi is None or value < hi):
                counts[key] += count
                total += count
                break

    return ScoreDistributionOut(
        buckets=[
            ScoreBucket(
                key=key, label=label, count=counts[key],
                min_score=lo, max_score=hi,
                # 低於門檻的那一格是負評 —— 畫成警戒色，與 Dashboard 一致
                is_negative=(hi is not None and hi <= NEGATIVE_THRESHOLD),
            )
            for key, label, lo, hi in SCORE_BUCKETS
        ],
        total=total,
        no_score_count=no_score,
    )


# ══════════════════════════════════════════════════════════════════════════
# 每日警示條帶（2026-08-25）
# ══════════════════════════════════════════════════════════════════════════
# 一天一格，顏色深淺 = 當天發生幾件警示。橫著看就是「哪幾天出事」。
#
# ⚠️⚠️ **與積壓分桶的口徑不同，同一頁上必須講清楚：**
#
#     · 積壓分桶 = **還沒處理的存量**（open + acknowledged）
#     · 這張條帶 = **當天發生了幾件**（不論後來處理了沒）
#
#    如果條帶也只算未處理，處理完的日子會變乾淨 ——
#    看起來像「那幾天沒出事」，但事情確實發生過。
#    兩個口徑都對，但混為一談就會變成「兩個數字對不起來」的老問題。
#
# ⚠️ 依 `review_date`（客人留言那天），與積壓分桶的起算日一致。
#    同一頁兩張圖用不同的日期定義是找麻煩。
ALERT_DAILY_DEFAULT_DAYS = 60
ALERT_DAILY_MAX_DAYS = 180


def get_alert_daily(
    db: Session, *, hotel_code: str = "", platform: str = "",
    days: int = ALERT_DAILY_DEFAULT_DAYS,
) -> AlertDailyOut:
    """
    最近 N 天每天發生幾件警示。

    ⚠️⚠️ **「沒有資料」與「沒有警示」必須分開標。**
       OTA 評論落後現實好幾天（客人退房後才留言 + 爬蟲每日才跑），
       所以最近幾格本來就還沒抓到。把它們畫成「0 件」的話，
       看起來像「這幾天很平靜」—— **那是這個模組最容易誤導人的一種呈現**，
       而且完全不會有錯誤訊息。
       用 `data_end`（評論資料的最後一天）判斷，晚於它的標 `no_data`。
    """
    days = max(1, min(days, ALERT_DAILY_MAX_DAYS))
    today = date.today()
    first = today - timedelta(days=days - 1)

    stmt = _base_filters(
        select(OtaReview.review_date, func.count(OtaReview.id))
        .where(OtaReview.is_alert.is_(True))
        .where(OtaReview.review_date >= first.isoformat())
        .where(OtaReview.review_date <= today.isoformat())
        .group_by(OtaReview.review_date),
        hotel_code, platform,
    )
    counts = {row[0]: row[1] for row in db.execute(stmt).all() if row[0]}

    data_end = get_data_range(db, hotel_code).end

    points: list[AlertDailyPoint] = []
    for offset in range(days):
        d = (first + timedelta(days=offset)).isoformat()
        points.append(AlertDailyPoint(
            date=d,
            count=counts.get(d, 0),
            # ⚠️ 沒有 data_end（整個模組還沒有資料）時不要把每一格都標成
            #    no_data —— 那會變成一整條灰色，看起來像功能壞掉。
            no_data=bool(data_end) and d > data_end,
        ))

    return AlertDailyOut(
        days=points,
        max_count=max((p.count for p in points), default=0),
        total=sum(p.count for p in points),
        data_end=data_end,
    )
