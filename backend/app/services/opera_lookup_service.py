"""
OPERA 歷史同期查詢 — 輸入日期或期間，回答「過去這天／這段期間賣多少」

評估文件：docs/EVAL_opera_rate_forecasting.md §3.1（需求 4）

這支服務**不做任何預測**，只查歷史事實。之所以獨立成一個 service，
是因為它回答的是訂價會議上最常見的問題（「去年這天賣多少、賣得掉嗎」），
價值不比預測低，而且完全不需要模型、沒有誤差。

口徑一律沿用既有規範（不可另立一套）：
  * 營收／ADR／住房率／RevPAR → 只用 History and Forecast（決策 D7）
  * 通路／房型／住客結構       → 只用 Departure（決策 D7）
  * 加權公式：ADR = Σ營收 ÷ Σ售出房晚，禁止用每日 ADR 平均
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.opera_departure import OperaDepartureStay
from app.models.opera_forecast import OperaEvent
from app.models.opera_revenue import (
    OperaRevenueDaily,
    RECORD_TYPE_FORECAST,
    RECORD_TYPE_HISTORY,
)
from app.services import opera_analysis_service as AS
from app.services import opera_period_service as PS

SOURCE_NOTE = "資料來源：History and Forecast（營收）／Departure All（住客結構）"

# 近期同星期要看幾次（4 次≈ 一個月，夠看出趨勢又不會被太舊的資料稀釋）
RECENT_SAME_WEEKDAY_COUNT = 4


# ══════════════════════════════════════════════════════════════════════════════
# 共用小工具
# ══════════════════════════════════════════════════════════════════════════════

def _day_metrics(row: OperaRevenueDaily | None) -> dict | None:
    if row is None:
        return None
    return {
        "business_date":   row.business_date,
        "revenue":         round(float(row.revenue), 2),
        "sold_rooms":      row.sold_rooms,
        "available_rooms": row.available_rooms,
        "ooo_rooms":       row.ooo_rooms,
        "no_persons":      row.no_persons,
        "arrival_rooms":   row.arrival_rooms,
        "departure_rooms": row.departure_rooms,
        "adr":             round(row.adr, 2),
        "occupancy":       round(row.occupancy, 6),
        "revpar":          round(row.revpar, 2),
        # 每房人數：訂價時判斷「賣的是雙人房還是單人使用」很有用
        "persons_per_room": round(row.no_persons / row.sold_rooms, 2) if row.sold_rooms else 0.0,
    }


def _fetch_day(db: Session, business_date: str, property_code: str,
               record_type: str = RECORD_TYPE_HISTORY) -> OperaRevenueDaily | None:
    q = db.query(OperaRevenueDaily).filter(
        OperaRevenueDaily.is_current == 1,
        OperaRevenueDaily.record_type == record_type,
        OperaRevenueDaily.business_date == business_date,
    )
    if property_code:
        q = q.filter(OperaRevenueDaily.property_code == property_code)
    return q.first()


def _diff_block(target: dict | None, other: dict | None) -> dict:
    """target 相對於 other 的差異。無資料時一律回 None，不可用 0 混充。"""
    if not target or not other:
        return {"adr_diff": None, "adr_pct": None, "occupancy_ppt": None, "revenue_pct": None}
    adr_diff = target["adr"] - other["adr"]
    return {
        "adr_diff":      round(adr_diff, 2),
        "adr_pct":       AS._pct_change(target["adr"], other["adr"]),
        "occupancy_ppt": round(target["occupancy"] - other["occupancy"], 6),
        "revenue_pct":   AS._pct_change(target["revenue"], other["revenue"]),
    }


def _avg_of(rows: list[dict]) -> dict | None:
    """多天的加權平均（⚠️ 用 Σ營收 ÷ Σ房晚，不是把每天 ADR 平均）。"""
    if not rows:
        return None
    revenue = sum(r["revenue"] for r in rows)
    sold = sum(r["sold_rooms"] for r in rows)
    available = sum(r["available_rooms"] for r in rows)
    persons = sum(r["no_persons"] for r in rows)
    return {
        "business_date":   "",
        "days":            len(rows),
        "revenue":         round(revenue / len(rows), 2),      # 每日平均營收
        "total_revenue":   round(revenue, 2),
        "sold_rooms":      round(sold / len(rows), 1),
        "available_rooms": round(available / len(rows), 1),
        "ooo_rooms":       0,
        "no_persons":      round(persons / len(rows), 1),
        "arrival_rooms":   0,
        "departure_rooms": 0,
        "adr":             round(revenue / sold, 2) if sold else 0.0,
        "occupancy":       round(sold / available, 6) if available else 0.0,
        "revpar":          round(revenue / available, 2) if available else 0.0,
        "persons_per_room": round(persons / sold, 2) if sold else 0.0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 事件
# ══════════════════════════════════════════════════════════════════════════════

def find_events(db: Session, start: str, end: str, property_code: str = "",
                only_active: bool = True) -> list[dict]:
    """回傳與 [start, end] 有重疊的事件（區間重疊，不是包含）。"""
    q = db.query(OperaEvent).filter(
        OperaEvent.start_date <= end,
        OperaEvent.end_date >= start,
    )
    if only_active:
        q = q.filter(OperaEvent.is_active == 1)
    if property_code:
        q = q.filter(OperaEvent.property_code.in_([property_code, ""]))
    return [e.to_dict() for e in q.order_by(OperaEvent.start_date).all()]


# ══════════════════════════════════════════════════════════════════════════════
# 住客結構（Departure）
# ══════════════════════════════════════════════════════════════════════════════

def _stay_mix(db: Session, start: str, end: str, property_code: str,
              top_n: int = 6) -> dict:
    """該期間**退房**的住客結構（通路／房型／住宿天數）。

    ⚠️ Departure 記錄的是退房日，所以這裡回答的是「當天走的客人長什麼樣」，
       不是「當天在住的客人」。畫面上必須寫清楚，否則會被誤解成在住客結構。
    """
    conds = [
        OperaDepartureStay.is_current == 1,
        OperaDepartureStay.departure_date >= start,
        OperaDepartureStay.departure_date <= end,
        OperaDepartureStay.no_of_rooms > 0,     # 以房數計（決策 D5 的 basis=room）
    ]
    if property_code:
        conds.append(OperaDepartureStay.property_code == property_code)

    total = (
        db.query(
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
            func.coalesce(func.sum(OperaDepartureStay.adults), 0),
            func.coalesce(func.sum(OperaDepartureStay.children), 0),
            func.coalesce(func.sum(OperaDepartureStay.nights), 0),
        )
        .filter(*conds)
        .first()
    )
    stays, room_nights, adults, children, nights = (
        int(total[0]), int(total[1]), int(total[2]), int(total[3]), int(total[4])
    )

    def _top(column, fallback: str) -> list[dict]:
        rows = (
            db.query(column, func.count(OperaDepartureStay.id),
                     func.coalesce(func.sum(OperaDepartureStay.room_nights), 0))
            .filter(*conds)
            .group_by(column)
            .all()
        )
        items = [
            {
                "name":        (r[0] or "").strip() or fallback,
                "stays":       int(r[1]),
                "room_nights": int(r[2]),
                "share":       round(int(r[1]) / stays, 4) if stays else 0.0,
            }
            for r in rows
        ]
        items.sort(key=lambda x: -x["stays"])
        if len(items) > top_n:
            rest = items[top_n:]
            items = items[:top_n] + [{
                "name":        f"其他（{len(rest)} 項）",
                "stays":       sum(i["stays"] for i in rest),
                "room_nights": sum(i["room_nights"] for i in rest),
                "share":       round(sum(i["stays"] for i in rest) / stays, 4) if stays else 0.0,
            }]
        return items

    return {
        "stays":           stays,
        "room_nights":     room_nights,
        "adults":          adults,
        "child_count":     children,     # ⚠️ 不可叫 children（antd Table 會當成子列）
        "persons":         adults + children,
        "avg_los":         round(nights / stays, 2) if stays else 0.0,
        "channels":        _top(OperaDepartureStay.travel_agent_name, "直客／未標註"),
        "room_categories": _top(OperaDepartureStay.room_category_label, "（未標註）"),
        "has_data":        stays > 0,
        "basis_note":      "以退房日歸戶，只計 no_of_rooms > 0 的資料列（以房數計）",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 單日查詢
# ══════════════════════════════════════════════════════════════════════════════

def get_date_lookup(db: Session, business_date: str, property_code: str = "") -> dict:
    """輸入一個日期，回傳「這天的歷史脈絡」（評估文件 §3.1）。"""
    d = PS.to_date(business_date)
    iso = d.isoformat()
    wd = AS._weekday_index(iso)

    target = _day_metrics(_fetch_day(db, iso, property_code))
    forecast = _day_metrics(_fetch_day(db, iso, property_code, RECORD_TYPE_FORECAST))

    # ── 對照 1：去年同一天（日曆日對齊）──────────────────────────────────
    ly_date = PS.shift_year(d, -1).isoformat()
    ly = _day_metrics(_fetch_day(db, ly_date, property_code))

    # ── 對照 2：去年同星期（−364 天，星期對齊）───────────────────────────
    #    −364 天剛好是 52 週，星期一定相同。訂價看星期比看日曆日更準。
    lw_date = (d - timedelta(days=364)).isoformat()
    lw = _day_metrics(_fetch_day(db, lw_date, property_code))

    # ── 對照 3：最近 N 個同星期（往前找，只取有資料的）────────────────────
    recent: list[dict] = []
    cursor = d - timedelta(days=7)
    guard = 0
    while len(recent) < RECENT_SAME_WEEKDAY_COUNT and guard < 60:
        row = _day_metrics(_fetch_day(db, cursor.isoformat(), property_code))
        if row:
            recent.append(row)
        cursor -= timedelta(days=7)
        guard += 1
    recent_avg = _avg_of(recent)

    comparisons = [
        {
            "key":   "last_year_same_date",
            "label": f"去年同一天（{ly_date}）",
            "hint":  "日曆日對齊，適合看節慶（如 12/25）",
            "date":  ly_date,
            "metrics": ly,
            "diff":  _diff_block(target, ly),
        },
        {
            "key":   "last_year_same_weekday",
            "label": f"去年同星期（{lw_date}，−364 天）",
            "hint":  "星期對齊，訂價比較常用這個",
            "date":  lw_date,
            "metrics": lw,
            "diff":  _diff_block(target, lw),
        },
        {
            "key":   "recent_same_weekday",
            "label": f"近 {len(recent)} 個{AS.WEEKDAY_LABELS[wd]}平均",
            "hint":  "看最近的實際成交水準",
            "date":  "",
            "metrics": recent_avg,
            "diff":  _diff_block(target, recent_avg),
        },
    ]

    # ── 當月概況 ─────────────────────────────────────────────────────────
    m_start, m_end = PS.month_range(d.year, d.month)
    data_start, data_end = PS.default_range(db, property_code)
    m_end_eff = min(m_end, data_end)
    month_current = AS._aggregate(db, m_start, m_end_eff, property_code)
    ly_m_start, ly_m_end = PS.month_range(d.year - 1, d.month)
    # 當月未過完 → 去年也只比到相同日（MTD 對 MTD，不可拿去年整月比）
    if m_end_eff < m_end:
        ly_m_end = PS.shift_year(PS.to_date(m_end_eff), -1).isoformat()
    month_compare = AS._aggregate(db, ly_m_start, ly_m_end, property_code)

    # ── 該月的星期基準（這天的星期在當月表現如何）─────────────────────────
    weekday_perf = AS.get_weekday_performance(db, m_start, m_end_eff, property_code)
    weekday_row = next((w for w in weekday_perf["weekdays"] if w["weekday"] == wd), None)

    # ── 特殊標記（以「該年度」為基準判定，不是全期）────────────────────────
    y_start, y_end = PS.year_range(d.year)
    y_end = min(y_end, data_end)
    y_start = max(y_start, data_start)
    flags: list[dict] = []
    if target:
        anomalies = AS.get_anomalies(db, y_start, y_end, property_code)
        hit = next((a for a in anomalies["items"] if a["business_date"] == iso), None)
        if hit:
            for reason in hit["reasons"]:
                flags.append({"label": reason, "source": hit["trigger_source"]})

    events = find_events(db, iso, iso, property_code)

    return {
        "business_date":  iso,
        "weekday":        wd,
        "weekday_label":  AS.WEEKDAY_LABELS[wd],
        "has_data":       target is not None,
        "target":         target,
        "forecast":       forecast,
        "comparisons":    comparisons,
        "recent_same_weekday": recent,
        "month_context": {
            "month":       f"{d.year}-{d.month:02d}",
            "start":       m_start,
            "end":         m_end_eff,
            "is_partial":  m_end_eff < m_end,
            "current":     month_current,
            "compare":     month_compare,
            "compare_label": f"{d.year - 1}-{d.month:02d}"
                             + ("（MTD 對 MTD）" if m_end_eff < m_end else ""),
            "has_compare_data": month_compare["days"] > 0,
            "yoy": {
                "adr":           AS._pct_change(month_current["adr"], month_compare["adr"]),
                "revenue":       AS._pct_change(month_current["revenue"], month_compare["revenue"]),
                # ⚠️ 沒有去年資料時必須回 None。若照算會變成「current − 0」，
                #    畫面上會顯示 +61.9 ppt 這種看起來像成長爆發、實際是沒資料的數字。
                "occupancy_ppt": (
                    round(month_current["occupancy"] - month_compare["occupancy"], 6)
                    if month_compare["days"] > 0 else None
                ),
            },
        },
        "weekday_context": {
            "label":     AS.WEEKDAY_LABELS[wd],
            "in_month":  weekday_row,
            "baseline":  weekday_perf["baseline"],
            "thin_data": weekday_perf["thin_data"],
        },
        "stay_mix":     _stay_mix(db, iso, iso, property_code),
        "flags":        flags,
        "events":       events,
        "data_range":   {"start": data_start, "end": data_end},
        "source_label": SOURCE_NOTE,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 期間查詢
# ══════════════════════════════════════════════════════════════════════════════

def get_period_lookup(db: Session, start: str, end: str,
                      property_code: str = "") -> dict:
    """輸入一段期間，回傳加權 KPI、同期比較、逐日明細與星期分布。"""
    kpi = AS.get_kpi(db, start, end, property_code)
    period = kpi["period"]

    daily = AS.get_daily(db, period["start"], period["end"], property_code)
    weekday = AS.get_weekday_performance(db, period["start"], period["end"], property_code)

    # 月分布（期間跨月時，看得出哪個月撐起營收）
    by_month: dict[str, dict] = defaultdict(
        lambda: {"revenue": 0.0, "sold_rooms": 0, "available_rooms": 0, "days": 0}
    )
    for row in daily:
        m = by_month[row["business_date"][:7]]
        m["revenue"] += row["revenue"]
        m["sold_rooms"] += row["sold_rooms"]
        m["available_rooms"] += row["available_rooms"]
        m["days"] += 1
    months = []
    for m in sorted(by_month):
        v = by_month[m]
        months.append({
            "month":      m,
            "days":       v["days"],
            "revenue":    round(v["revenue"], 2),
            "sold_rooms": v["sold_rooms"],
            "adr":        round(v["revenue"] / v["sold_rooms"], 2) if v["sold_rooms"] else 0.0,
            "occupancy":  round(v["sold_rooms"] / v["available_rooms"], 6) if v["available_rooms"] else 0.0,
            "revpar":     round(v["revenue"] / v["available_rooms"], 2) if v["available_rooms"] else 0.0,
        })

    # 最好／最差的日子（用 RevPAR 排，因為它同時涵蓋價與量）
    ranked = sorted(daily, key=lambda r: -r["revpar"])
    best = ranked[:5]
    worst = [r for r in ranked[::-1] if r["available_rooms"]][:5]

    return {
        "period":       period,
        "current":      kpi["current"],
        "compare":      kpi["compare"],
        "yoy":          kpi["yoy"],
        "has_compare_data": kpi["has_compare_data"],
        "daily":        daily,
        "months":       months,
        "weekday":      weekday["weekdays"],
        "weekday_thin": weekday["thin_data"],
        "best_days":    best,
        "worst_days":   worst,
        "stay_mix":     _stay_mix(db, period["start"], period["end"], property_code),
        "events":       find_events(db, period["start"], period["end"], property_code),
        "source_label": SOURCE_NOTE,
    }
