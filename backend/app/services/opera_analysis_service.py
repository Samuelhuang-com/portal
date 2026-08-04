"""
OPERA 分析服務 — 加權公式、四象限、營收異常、住客與通路統計

規格書：docs/SPEC_opera_analytics.md §9

資料口徑（業主 2026-08-04 決定 D7，不可混用）：
  * 營收 / ADR / 住房率 / RevPAR → **只用 History and Forecast**（唯一有營收的來源）
  * 通路 / 房型 / Rate Code / 公司 / 住客 → **只用 Departure**
  兩者不互相驗算房晚。

加權公式（禁止用每日值的簡單平均）：
    ADR    = SUM(revenue) / SUM(sold_rooms)
    OCC    = SUM(sold_rooms) / SUM(available_rooms)
    RevPAR = SUM(revenue) / SUM(available_rooms)
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.opera_departure import OperaDepartureStay
from app.models.opera_revenue import (
    DEFAULT_ANALYSIS_SETTINGS,
    OperaAnalysisSetting,
    OperaRevenueDaily,
    RECORD_TYPE_FORECAST,
    RECORD_TYPE_HISTORY,
)
from app.services import opera_period_service as PS

# 維度統計雙口徑（規格書 §11.10，決策 D5）
BASIS_ROOM = "room"                 # 只計 no_of_rooms = 1
BASIS_RESERVATION = "reservation"   # 全部列
BASIS_LABELS = {BASIS_ROOM: "以房數計", BASIS_RESERVATION: "以訂單計"}


# ══════════════════════════════════════════════════════════════════════════════
# 門檻設定
# ══════════════════════════════════════════════════════════════════════════════

def get_settings(db: Session, property_code: str = "") -> dict[str, float]:
    values = {k: v[0] for k, v in DEFAULT_ANALYSIS_SETTINGS.items()}
    q = db.query(OperaAnalysisSetting)
    if property_code:
        q = q.filter(OperaAnalysisSetting.property_code.in_([property_code, ""]))
    for row in q.all():
        if row.setting_key in values:
            values[row.setting_key] = row.typed_value()
    return values


def list_settings(db: Session, property_code: str = "") -> list[dict]:
    current = get_settings(db, property_code)
    stored = {r.setting_key: r for r in db.query(OperaAnalysisSetting).all()}
    out = []
    for key, (default, vtype, desc) in DEFAULT_ANALYSIS_SETTINGS.items():
        row = stored.get(key)
        out.append({
            "setting_key":   key,
            "setting_value": current[key],
            "default_value": default,
            "value_type":    vtype,
            "description":   desc,
            "is_default":    row is None,
            "updated_at":    row.updated_at.strftime("%Y/%m/%d %H:%M") if row and row.updated_at else "",
            "updated_by_name": row.updated_by_name if row else "",
        })
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 營收（來源：History and Forecast）
# ══════════════════════════════════════════════════════════════════════════════

def _revenue_query(db: Session, start: str, end: str, property_code: str, record_type: str):
    q = (
        db.query(OperaRevenueDaily)
        .filter(
            OperaRevenueDaily.is_current == 1,
            OperaRevenueDaily.record_type == record_type,
            OperaRevenueDaily.business_date >= start,
            OperaRevenueDaily.business_date <= end,
        )
    )
    if property_code:
        q = q.filter(OperaRevenueDaily.property_code == property_code)
    return q


def _aggregate(db: Session, start: str, end: str, property_code: str,
               record_type: str = RECORD_TYPE_HISTORY) -> dict:
    """期間加總 + 加權指標。"""
    row = (
        db.query(
            func.coalesce(func.sum(OperaRevenueDaily.revenue), 0),
            func.coalesce(func.sum(OperaRevenueDaily.sold_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.available_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.inventory_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.ooo_rooms), 0),
            func.count(OperaRevenueDaily.id),
        )
        .filter(
            OperaRevenueDaily.is_current == 1,
            OperaRevenueDaily.record_type == record_type,
            OperaRevenueDaily.business_date >= start,
            OperaRevenueDaily.business_date <= end,
            *( [OperaRevenueDaily.property_code == property_code] if property_code else [] ),
        )
        .first()
    )
    revenue, sold, available, inventory, ooo, days = (
        float(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5])
    )
    return {
        "revenue":         round(revenue, 2),
        "sold_rooms":      sold,
        "available_rooms": available,
        "inventory_rooms": inventory,
        "ooo_rooms":       ooo,
        "days":            days,
        "adr":             round(revenue / sold, 2) if sold else 0.0,
        "occupancy":       round(sold / available, 6) if available else 0.0,
        "revpar":          round(revenue / available, 2) if available else 0.0,
    }


def _pct_change(curr: float, prev: float) -> float | None:
    if not prev:
        return None
    return round(curr / prev - 1, 6)


def get_kpi(db: Session, start: str, end: str, property_code: str = "",
            include_forecast: bool = False) -> dict:
    """Dashboard / 營收分析頁的期間 KPI（含同期比較）。"""
    period = PS.resolve_period(db, start, end, property_code)
    current = _aggregate(db, period.start, period.end, property_code)
    compare = _aggregate(db, period.compare_start, period.compare_end, property_code)

    forecast = None
    if include_forecast:
        forecast = _aggregate(db, period.start, period.end, property_code, RECORD_TYPE_FORECAST)

    return {
        "period":   period.as_dict(),
        "current":  current,
        "compare":  compare,
        "forecast": forecast,
        "yoy": {
            "revenue":       _pct_change(current["revenue"], compare["revenue"]),
            "adr":           _pct_change(current["adr"], compare["adr"]),
            "revpar":        _pct_change(current["revpar"], compare["revpar"]),
            "sold_rooms":    _pct_change(current["sold_rooms"], compare["sold_rooms"]),
            # 住房率用百分點差，不用百分比變化
            "occupancy_ppt": round(current["occupancy"] - compare["occupancy"], 6),
        },
        "has_compare_data": compare["days"] > 0,
        "source_label": "資料來源：History and Forecast",
    }


def get_daily(db: Session, start: str, end: str, property_code: str = "",
              record_type: str = RECORD_TYPE_HISTORY) -> list[dict]:
    rows = (
        _revenue_query(db, start, end, property_code, record_type)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )
    return [r.to_dict() for r in rows]


def get_day_detail(db: Session, business_date: str, property_code: str = "",
                   record_type: str = RECORD_TYPE_HISTORY) -> dict | None:
    q = (
        db.query(OperaRevenueDaily)
        .filter(
            OperaRevenueDaily.is_current == 1,
            OperaRevenueDaily.business_date == business_date,
            OperaRevenueDaily.record_type == record_type,
        )
    )
    if property_code:
        q = q.filter(OperaRevenueDaily.property_code == property_code)
    row = q.first()
    return row.to_dict() if row else None


def get_monthly(db: Session, year: int, property_code: str = "") -> dict:
    """月彙總 + 去年同期（完整月比完整月、當月未過完則自動比 MTD）。

    ⚠️ 「當月是否過完」以**資料庫實際最後一天**判定，不用 date.today()：
       OPERA 匯出通常落後幾天，用今天會把最後一個月誤判成資料缺漏。
    """
    _, data_end = PS.default_range(db, property_code)
    months: list[dict] = []

    for m in range(1, 13):
        start, end = PS.month_range(year, m)
        # 該月尚未有完整資料 → 截到資料最後一天，比較期同步截到去年相同日（MTD）
        if data_end and start <= data_end < end:
            end = data_end
        period = PS.resolve_period(db, start, end, property_code)
        curr = _aggregate(db, period.start, period.end, property_code)
        if curr["days"] == 0:
            continue
        prev = _aggregate(db, period.compare_start, period.compare_end, property_code)
        months.append({
            "year":            year,
            "month":           m,
            "label":           f"{m}月",
            "period_type":     period.period_type,
            "period_label":    period.period_label,
            "compare_label":   period.compare_label,
            "current":         curr,
            "compare":         prev,
            "revenue_yoy":     _pct_change(curr["revenue"], prev["revenue"]),
            "adr_yoy":         _pct_change(curr["adr"], prev["adr"]),
            "occupancy_ppt":   round(curr["occupancy"] - prev["occupancy"], 6),
            "has_compare":     prev["days"] > 0,
        })

    return {
        "year":   year,
        "months": months,
        "total":  _aggregate(db, *PS.year_range(year), property_code),
        "source_label": "資料來源：History and Forecast",
    }


def get_yearly(db: Session, property_code: str = "") -> dict:
    """各年度彙總（自動標示完整／部分年度）。"""
    rows = db.execute(text(
        "SELECT DISTINCT substr(business_date, 1, 4) FROM opera_revenue_daily "
        "WHERE is_current = 1 AND record_type = :rt ORDER BY 1"
    ), {"rt": RECORD_TYPE_HISTORY}).all()
    years = [int(r[0]) for r in rows if r[0]]

    out: list[dict] = []
    for y in years:
        start, end = PS.year_range(y)
        period = PS.resolve_period(db, start, end, property_code)
        agg = _aggregate(db, start, end, property_code)
        out.append({
            "year":          y,
            "period_type":   period.period_type,
            "period_label":  period.period_label,
            "data_days":     period.data_days,
            "expected_days": period.expected_days,
            "is_complete":   period.is_complete,
            **agg,
        })

    for i, item in enumerate(out):
        prev = out[i - 1] if i > 0 else None
        item["revenue_yoy"]   = _pct_change(item["revenue"], prev["revenue"]) if prev else None
        item["adr_yoy"]       = _pct_change(item["adr"], prev["adr"]) if prev else None
        item["occupancy_ppt"] = round(item["occupancy"] - prev["occupancy"], 6) if prev else None
        # 只有雙方都是完整年度才算「可直接比較」
        item["comparable"] = bool(prev and prev["is_complete"] and item["is_complete"])

    return {"years": out, "source_label": "資料來源：History and Forecast"}


# ══════════════════════════════════════════════════════════════════════════════
# 四象限（規格書 §9.4）
# ══════════════════════════════════════════════════════════════════════════════

def get_quadrant(db: Session, start: str, end: str, property_code: str = "",
                 basis: str = "common") -> dict:
    """ADR × 住房率 散佈圖資料。

    basis = "common"：全期加權 ADR／住房率當基準（適合跨年度比較）
    basis = "annual"：各年度自己的加權值當基準（適合看當年內部結構）
    """
    rows = (
        _revenue_query(db, start, end, property_code, RECORD_TYPE_HISTORY)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )

    overall = _aggregate(db, start, end, property_code)
    annual: dict[str, dict] = {}
    if basis == "annual":
        for year in sorted({r.business_date[:4] for r in rows}):
            ys, ye = PS.year_range(int(year))
            annual[year] = _aggregate(db, max(ys, start), min(ye, end), property_code)

    points: list[dict] = []
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        if not r.available_rooms:
            continue
        year = r.business_date[:4]
        base = annual.get(year, overall) if basis == "annual" else overall
        adr, occ = r.adr, r.occupancy
        if adr >= base["adr"] and occ >= base["occupancy"]:
            quadrant, qlabel = "Q1", "高 ADR 高住房"
        elif adr < base["adr"] and occ >= base["occupancy"]:
            quadrant, qlabel = "Q2", "低 ADR 高住房"
        elif adr < base["adr"] and occ < base["occupancy"]:
            quadrant, qlabel = "Q3", "低 ADR 低住房"
        else:
            quadrant, qlabel = "Q4", "高 ADR 低住房"
        counts[quadrant] += 1
        points.append({
            "business_date": r.business_date,
            "year":          year,
            "adr":           round(adr, 2),
            "occupancy":     round(occ, 6),
            "revenue":       float(r.revenue),
            "sold_rooms":    r.sold_rooms,
            "quadrant":      quadrant,
            "quadrant_label": qlabel,
        })

    return {
        "basis":       basis,
        "basis_label": "共同基準（全期加權）" if basis != "annual" else "年度自有基準",
        "baseline":    {"adr": overall["adr"], "occupancy": overall["occupancy"]},
        "annual_baselines": {
            y: {"adr": a["adr"], "occupancy": a["occupancy"]} for y, a in annual.items()
        },
        "points":  points,
        "counts":  dict(counts),
        "source_label": "資料來源：History and Forecast",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 營收異常（規格書 §9.5）
# ══════════════════════════════════════════════════════════════════════════════

TRIGGER_FIXED = "固定門檻"
TRIGGER_ANNUAL = "年度基準"
TRIGGER_BOTH = "兩者"


def get_anomalies(db: Session, start: str, end: str, property_code: str = "") -> dict:
    cfg = get_settings(db, property_code)
    rows = (
        _revenue_query(db, start, end, property_code, RECORD_TYPE_HISTORY)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )
    overall = _aggregate(db, start, end, property_code)

    annual: dict[str, dict] = {}
    for year in sorted({r.business_date[:4] for r in rows}):
        ys, ye = PS.year_range(int(year))
        annual[year] = _aggregate(db, max(ys, start), min(ye, end), property_code)

    items: list[dict] = []
    type_counts: dict[str, int] = defaultdict(int)

    for r in rows:
        fixed: list[str] = []
        annual_flags: list[str] = []
        adr, occ = r.adr, r.occupancy

        if float(r.revenue) < 0:
            fixed.append("負營收")
        if float(r.revenue) > 0 and r.sold_rooms == 0:
            fixed.append("有營收但無房數")
        if r.sold_rooms > 0 and float(r.revenue) == 0:
            fixed.append("有房數但無營收")
        if r.available_rooms and r.sold_rooms > r.available_rooms:
            fixed.append("超賣")
        if r.ooo_rooms > 0:
            fixed.append("OOO")
        if overall["adr"] and adr > overall["adr"] * cfg["adr_high_multiplier"]:
            fixed.append("ADR 偏高")
        if overall["adr"] and 0 < adr < overall["adr"] * cfg["adr_low_multiplier"]:
            fixed.append("ADR 偏低")
        if (occ >= cfg["opportunity_occupancy_threshold"]
                and overall["adr"] and adr < overall["adr"]):
            fixed.append("高住房率低 ADR")
        if occ >= cfg["high_occupancy_threshold"]:
            fixed.append("高住房率")

        base = annual.get(r.business_date[:4], overall)
        diff = occ - base["occupancy"]
        if diff >= cfg["annual_occupancy_diff_pp"]:
            annual_flags.append("住房率高於年度基準")
        elif diff <= -cfg["annual_occupancy_diff_pp"]:
            annual_flags.append("住房率低於年度基準")

        if not fixed and not annual_flags:
            continue

        trigger = (
            TRIGGER_BOTH if fixed and annual_flags
            else TRIGGER_FIXED if fixed
            else TRIGGER_ANNUAL
        )
        for t in fixed + annual_flags:
            type_counts[t] += 1

        items.append({
            "business_date":    r.business_date,
            "month":            r.business_date[:7],
            "revenue":          float(r.revenue),
            "sold_rooms":       r.sold_rooms,
            "available_rooms":  r.available_rooms,
            "ooo_rooms":        r.ooo_rooms,
            "adr":              round(adr, 2),
            "occupancy":        round(occ, 6),
            "revpar":           round(r.revpar, 2),
            "annual_occupancy": round(base["occupancy"], 6),
            "occupancy_diff":   round(diff, 6),
            "fixed_reasons":    fixed,
            "annual_reasons":   annual_flags,
            "reasons":          fixed + annual_flags,
            "trigger_source":   trigger,
        })

    # 依月份 × 觸發來源堆疊（圖表 C8）
    monthly: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for it in items:
        monthly[it["month"]][it["trigger_source"]] += 1
    monthly_series = [
        {
            "month": m,
            TRIGGER_FIXED:  monthly[m].get(TRIGGER_FIXED, 0),
            TRIGGER_ANNUAL: monthly[m].get(TRIGGER_ANNUAL, 0),
            TRIGGER_BOTH:   monthly[m].get(TRIGGER_BOTH, 0),
        }
        for m in sorted(monthly)
    ]

    return {
        "settings":       cfg,
        "baseline":       {"adr": overall["adr"], "occupancy": overall["occupancy"]},
        "items":          items,
        "total":          len(items),
        "type_counts":    dict(type_counts),
        "monthly_series": monthly_series,
        "source_label":   "資料來源：History and Forecast",
    }


def get_segment(db: Session, start: str, end: str, property_code: str = "") -> dict:
    """散客 vs 團體、確定 vs 非確定拆分。"""
    row = (
        db.query(
            func.coalesce(func.sum(OperaRevenueDaily.individual_deduct_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.individual_non_deduct_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.group_deduct_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.group_non_deduct_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.individual_deduct_revenue), 0),
            func.coalesce(func.sum(OperaRevenueDaily.individual_non_deduct_revenue), 0),
            func.coalesce(func.sum(OperaRevenueDaily.group_deduct_revenue), 0),
            func.coalesce(func.sum(OperaRevenueDaily.group_non_deduct_revenue), 0),
        )
        .filter(
            OperaRevenueDaily.is_current == 1,
            OperaRevenueDaily.record_type == RECORD_TYPE_HISTORY,
            OperaRevenueDaily.business_date >= start,
            OperaRevenueDaily.business_date <= end,
            *( [OperaRevenueDaily.property_code == property_code] if property_code else [] ),
        )
        .first()
    )
    ind_d, ind_n, grp_d, grp_n = int(row[0]), int(row[1]), int(row[2]), int(row[3])
    rev_id, rev_in, rev_gd, rev_gn = float(row[4]), float(row[5]), float(row[6]), float(row[7])

    segments = [
        {"key": "individual", "label": "散客", "rooms": ind_d + ind_n, "revenue": round(rev_id + rev_in, 2)},
        {"key": "group",      "label": "團體", "rooms": grp_d + grp_n, "revenue": round(rev_gd + rev_gn, 2)},
    ]
    total_rev = sum(s["revenue"] for s in segments)
    total_rooms = sum(s["rooms"] for s in segments)
    for s in segments:
        s["revenue_share"] = round(s["revenue"] / total_rev, 6) if total_rev else 0.0
        s["rooms_share"] = round(s["rooms"] / total_rooms, 6) if total_rooms else 0.0
        s["adr"] = round(s["revenue"] / s["rooms"], 2) if s["rooms"] else 0.0

    return {
        "segments": segments,
        "detail": {
            "individual_deduct":     {"rooms": ind_d, "revenue": round(rev_id, 2)},
            "individual_non_deduct": {"rooms": ind_n, "revenue": round(rev_in, 2)},
            "group_deduct":          {"rooms": grp_d, "revenue": round(rev_gd, 2)},
            "group_non_deduct":      {"rooms": grp_n, "revenue": round(rev_gn, 2)},
        },
        "source_label": "資料來源：History and Forecast",
    }


# ══════════════════════════════════════════════════════════════════════════════
# 住客與通路（來源：Departure）
# ══════════════════════════════════════════════════════════════════════════════

def _stay_filters(start: str, end: str, property_code: str, basis: str) -> list:
    conds = [
        OperaDepartureStay.is_current == 1,
        OperaDepartureStay.departure_date >= start,
        OperaDepartureStay.departure_date <= end,
    ]
    if property_code:
        conds.append(OperaDepartureStay.property_code == property_code)
    if basis == BASIS_ROOM:
        conds.append(OperaDepartureStay.no_of_rooms > 0)
    return conds


DIMENSION_COLUMNS = {
    "channel":       (OperaDepartureStay.travel_agent_name, "通路", "直客／未標註"),
    "room_category": (OperaDepartureStay.room_category_label, "房型", "（未標註）"),
    "rate_code":     (OperaDepartureStay.rate_code, "Rate Code", "（未標註）"),
    "company":       (OperaDepartureStay.company_name, "公司", "（無公司）"),
    "payment":       (OperaDepartureStay.payment_desc, "付款方式", "（未標註）"),
}


def get_dimension_stats(db: Session, dimension: str, start: str, end: str,
                        property_code: str = "", basis: str = BASIS_ROOM,
                        limit: int = 0) -> dict:
    """通路／房型／Rate Code／公司／付款方式統計（雙口徑，規格書 §11.10）。"""
    if dimension not in DIMENSION_COLUMNS:
        raise ValueError(f"不支援的維度：{dimension}")
    column, label, blank_label = DIMENSION_COLUMNS[dimension]

    rows = (
        db.query(
            column,
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
            func.coalesce(func.sum(OperaDepartureStay.nights), 0),
            func.coalesce(func.sum(OperaDepartureStay.adults), 0),
            func.coalesce(func.sum(OperaDepartureStay.children), 0),
        )
        .filter(*_stay_filters(start, end, property_code, basis))
        .group_by(column)
        .all()
    )

    # ⚠️ 兒童數的 key 是 `child_count` 不是 `children`：Ant Design Table 預設把
    #    `record.children` 當成子列陣列，回傳數字會讓整個 Table 崩潰（見
    #    `OperaDepartureStay.to_dict()` 的說明）。這些 items 直接當 dataSource 用。
    items = [
        {
            "key":         (r[0] or "").strip() or blank_label,
            "records":     int(r[1]),
            "room_nights": int(r[2]),
            "nights":      int(r[3]),
            "adults":      int(r[4]),
            "child_count": int(r[5]),
        }
        for r in rows
    ]
    # 以房數計時 room_nights 才有意義；以訂單計時排序改用筆數
    sort_key = "room_nights" if basis == BASIS_ROOM else "records"
    items.sort(key=lambda x: (-x[sort_key], x["key"]))

    total_metric = sum(i[sort_key] for i in items) or 1
    total_records = sum(i["records"] for i in items)
    cumulative = 0
    for i in items:
        i["share"] = round(i[sort_key] / total_metric, 6)
        cumulative += i[sort_key]
        i["cumulative_share"] = round(cumulative / total_metric, 6)

    truncated = False
    if limit and len(items) > limit:
        items = items[:limit]
        truncated = True

    return {
        "dimension":     dimension,
        "dimension_label": label,
        "basis":         basis,
        "basis_label":   BASIS_LABELS.get(basis, basis),
        "metric":        sort_key,
        "metric_label":  "房晚" if sort_key == "room_nights" else "訂房筆數",
        "items":         items,
        "total_records": total_records,
        "total_metric":  total_metric,
        "truncated":     truncated,
        "source_label":  "資料來源：Departure All",
    }


def get_stays(db: Session, start: str, end: str, property_code: str = "",
              basis: str = BASIS_RESERVATION, page: int = 1, page_size: int = 50,
              channel: str = "", room_category: str = "", rate_code: str = "",
              search: str = "", sort_field: str = "departure_date",
              sort_order: str = "desc") -> dict:
    """住宿明細清單（分頁）。"""
    q = db.query(OperaDepartureStay).filter(*_stay_filters(start, end, property_code, basis))

    if channel:
        if channel in ("直客／未標註", "(blank)"):
            q = q.filter(OperaDepartureStay.travel_agent_name == "")
        else:
            q = q.filter(OperaDepartureStay.travel_agent_name == channel)
    if room_category:
        q = q.filter(OperaDepartureStay.room_category_label == room_category)
    if rate_code:
        q = q.filter(OperaDepartureStay.rate_code == rate_code)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (OperaDepartureStay.room_no.like(like))
            | (OperaDepartureStay.resv_name_id.like(like))
            | (OperaDepartureStay.external_reference.like(like))
        )

    total = q.count()

    sortable = {
        "departure_date": OperaDepartureStay.departure_date,
        "arrival_date":   OperaDepartureStay.arrival_date,
        "nights":         OperaDepartureStay.nights,
        "room_nights":    OperaDepartureStay.room_nights,
        "room_no":        OperaDepartureStay.room_no,
    }
    col = sortable.get(sort_field, OperaDepartureStay.departure_date)
    q = q.order_by(col.desc() if sort_order == "desc" else col.asc(), OperaDepartureStay.id.desc())

    rows = q.offset((max(page, 1) - 1) * page_size).limit(page_size).all()
    return {
        "items":     [r.to_dict() for r in rows],
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "basis":     basis,
        "basis_label": BASIS_LABELS.get(basis, basis),
        "source_label": "資料來源：Departure All",
    }


def get_stay_detail(db: Session, stay_id: int) -> dict | None:
    row = db.query(OperaDepartureStay).filter(OperaDepartureStay.id == stay_id).first()
    return row.to_dict() if row else None


def _purge_coverage(db: Session, start: str, end: str, property_code: str, basis: str) -> dict:
    row = (
        db.query(
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.is_purged), 0),
        )
        .filter(*_stay_filters(start, end, property_code, basis))
        .first()
    )
    total, purged = int(row[0]), int(row[1])
    identified = total - purged
    return {
        "total":      total,
        "purged":     purged,
        "identified": identified,
        "coverage":   round(identified / total, 6) if total else 0.0,
    }


def get_repeat_guests(db: Session, start: str, end: str, property_code: str = "",
                      basis: str = BASIS_RESERVATION, limit: int = 50) -> dict:
    """回訪住客統計（依 guest_identity_hash，排除 Purged）。"""
    conds = _stay_filters(start, end, property_code, basis) + [
        OperaDepartureStay.is_purged == 0,
        OperaDepartureStay.guest_identity_hash.isnot(None),
    ]
    rows = (
        db.query(
            OperaDepartureStay.guest_identity_hash,
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
            func.coalesce(func.sum(OperaDepartureStay.nights), 0),
            func.max(OperaDepartureStay.departure_date),
            func.max(OperaDepartureStay.guest_name_masked),
        )
        .filter(*conds)
        .group_by(OperaDepartureStay.guest_identity_hash)
        .all()
    )

    buckets = {"1 次": 0, "2 次": 0, "3 次": 0, "4 次以上": 0}
    top: list[dict] = []
    for h, cnt, rn, nights, last_dep, masked in rows:
        c = int(cnt)
        key = "1 次" if c == 1 else "2 次" if c == 2 else "3 次" if c == 3 else "4 次以上"
        buckets[key] += 1
        if c >= 2:
            top.append({
                "guest_hash":  (h or "")[:12],
                "guest_label": masked or "—",
                "visits":      c,
                "room_nights": int(rn),
                "nights":      int(nights),
                "last_departure": last_dep or "",
            })
    top.sort(key=lambda x: (-x["visits"], -x["nights"]))

    total_guests = len(rows)
    repeat_guests = sum(v for k, v in buckets.items() if k != "1 次")
    return {
        "distribution": [{"label": k, "guests": v} for k, v in buckets.items()],
        "top_guests":   top[:limit],
        "total_guests": total_guests,
        "repeat_guests": repeat_guests,
        "repeat_rate":  round(repeat_guests / total_guests, 6) if total_guests else 0.0,
        "coverage":     _purge_coverage(db, start, end, property_code, basis),
        "basis":        basis,
        "basis_label":  BASIS_LABELS.get(basis, basis),
        "source_label": "資料來源：Departure All",
    }


def get_long_stay(db: Session, start: str, end: str, property_code: str = "",
                  basis: str = BASIS_ROOM) -> dict:
    """住宿晚數分布 + 長住客統計。"""
    cfg = get_settings(db, property_code)
    threshold = int(cfg["long_stay_nights"])

    rows = (
        db.query(
            OperaDepartureStay.nights,
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
        )
        .filter(*_stay_filters(start, end, property_code, basis))
        .group_by(OperaDepartureStay.nights)
        .order_by(OperaDepartureStay.nights)
        .all()
    )
    distribution = [
        {
            "nights":      int(n or 0),
            "records":     int(c),
            "room_nights": int(rn),
            "is_long_stay": int(n or 0) >= threshold,
        }
        for n, c, rn in rows
    ]
    long_records = sum(d["records"] for d in distribution if d["is_long_stay"])
    total_records = sum(d["records"] for d in distribution)

    return {
        "threshold":     threshold,
        "distribution":  distribution,
        "long_records":  long_records,
        "total_records": total_records,
        "long_rate":     round(long_records / total_records, 6) if total_records else 0.0,
        "basis":         basis,
        "basis_label":   BASIS_LABELS.get(basis, basis),
        "source_label":  "資料來源：Departure All",
    }


def get_stay_summary(db: Session, start: str, end: str, property_code: str = "") -> dict:
    """Departure 側的期間總覽（兩種口徑並列，供 Dashboard 顯示）。"""
    out: dict[str, Any] = {}
    for basis in (BASIS_ROOM, BASIS_RESERVATION):
        row = (
            db.query(
                func.count(OperaDepartureStay.id),
                func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
                func.coalesce(func.sum(OperaDepartureStay.nights), 0),
                func.coalesce(func.sum(OperaDepartureStay.adults), 0),
                func.coalesce(func.sum(OperaDepartureStay.children), 0),
                func.coalesce(func.sum(OperaDepartureStay.no_of_rooms), 0),
            )
            .filter(*_stay_filters(start, end, property_code, basis))
            .first()
        )
        out[basis] = {
            "records":     int(row[0]),
            "room_nights": int(row[1]),
            "nights":      int(row[2]),
            "adults":      int(row[3]),
            "child_count": int(row[4]),   # ⚠️ 不可叫 children，理由同上
            "rooms":       int(row[5]),
            "basis_label": BASIS_LABELS[basis],
        }
    out["coverage"] = _purge_coverage(db, start, end, property_code, BASIS_RESERVATION)
    out["source_label"] = "資料來源：Departure All"
    return out
