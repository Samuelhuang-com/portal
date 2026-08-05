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

import re
from collections import defaultdict
from typing import Any

from sqlalchemy import case, func, text
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


# ── 星期別、OOO 損失、趨勢（2026-08-04 新增）─────────────────────────────────

WEEKDAY_LABELS = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]


def _weekday_index(iso_date: str) -> int:
    """ISO 日期字串 → 星期索引（0 = 星期一）。

    刻意在 Python 算而不用 SQL 的 strftime：一來 SQLite 的 `%w` 是 0=星期日，
    與這裡的 0=星期一不同容易搞錯；二來日後遷移 PostgreSQL 時 SQL 寫法會不一樣。
    """
    from datetime import date
    y, m, d = iso_date.split("-")
    return date(int(y), int(m), int(d)).weekday()


def get_weekday_performance(db: Session, start: str, end: str,
                            property_code: str = "") -> dict:
    """星期營收績效（規格書 §4.4）。

    ⚠️ 一律用加權公式：該星期別的總營收 ÷ 該星期別的總售出房晚，
       不是把每天的 ADR 拿來平均。
    """
    rows = (
        _revenue_query(db, start, end, property_code, RECORD_TYPE_HISTORY)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )

    acc = [
        {"weekday": i, "label": WEEKDAY_LABELS[i], "days": 0,
         "revenue": 0.0, "sold_rooms": 0, "available_rooms": 0, "ooo_rooms": 0}
        for i in range(7)
    ]
    for r in rows:
        a = acc[_weekday_index(r.business_date)]
        a["days"] += 1
        a["revenue"] += float(r.revenue)
        a["sold_rooms"] += r.sold_rooms
        a["available_rooms"] += r.available_rooms
        a["ooo_rooms"] += r.ooo_rooms

    overall = _aggregate(db, start, end, property_code)
    for a in acc:
        a["revenue"] = round(a["revenue"], 2)
        a["adr"] = round(a["revenue"] / a["sold_rooms"], 2) if a["sold_rooms"] else 0.0
        a["occupancy"] = round(a["sold_rooms"] / a["available_rooms"], 6) if a["available_rooms"] else 0.0
        a["revpar"] = round(a["revenue"] / a["available_rooms"], 2) if a["available_rooms"] else 0.0
        a["avg_daily_revenue"] = round(a["revenue"] / a["days"], 2) if a["days"] else 0.0
        # 與整體基準的差距，方便一眼看出哪幾天量強價弱
        a["adr_vs_overall"] = round(a["adr"] - overall["adr"], 2)
        a["occupancy_vs_overall"] = round(a["occupancy"] - overall["occupancy"], 6)

    min_days = min((a["days"] for a in acc if a["days"]), default=0)
    return {
        "weekdays":  acc,
        "baseline":  {"adr": overall["adr"], "occupancy": overall["occupancy"],
                      "revpar": overall["revpar"]},
        "min_days":  min_days,
        "thin_data": min_days < 8,   # 每個星期別不到 8 天時提醒容易被單一活動日扭曲
        "source_label": "資料來源：History and Forecast",
    }


def get_ooo_loss(db: Session, start: str, end: str, property_code: str = "") -> dict:
    """OOO 營收損失估算與雙分母 RevPAR 比較（規格書 §4.8）。

    ⚠️ 估算採用「當日 ADR」，假設 OOO 房可以同價售出；實際需求不足時真實損失較低。
    """
    rows = (
        _revenue_query(db, start, end, property_code, RECORD_TYPE_HISTORY)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )

    items: list[dict] = []
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"ooo_rooms": 0, "est_loss": 0.0, "days": 0})
    total_ooo = 0
    total_loss = 0.0
    sum_revenue = 0.0
    sum_available = 0
    sum_inventory = 0

    for r in rows:
        sum_revenue += float(r.revenue)
        sum_available += r.available_rooms
        sum_inventory += r.inventory_rooms
        if r.ooo_rooms <= 0:
            continue
        adr = r.adr
        loss = adr * r.ooo_rooms
        month = r.business_date[:7]
        total_ooo += r.ooo_rooms
        total_loss += loss
        monthly[month]["ooo_rooms"] += r.ooo_rooms
        monthly[month]["est_loss"] += loss
        monthly[month]["days"] += 1
        items.append({
            "business_date":   r.business_date,
            "month":           month,
            "ooo_rooms":       r.ooo_rooms,
            "inventory_rooms": r.inventory_rooms,
            "available_rooms": r.available_rooms,
            "sold_rooms":      r.sold_rooms,
            "revenue":         float(r.revenue),
            "adr":             round(adr, 2),
            "occupancy":       round(r.occupancy, 6),
            "est_loss":        round(loss, 2),
            "net_revpar":      round(r.revpar, 2),
            "physical_revpar": round(float(r.revenue) / r.inventory_rooms, 2) if r.inventory_rooms else 0.0,
        })

    for it in items:
        it["denominator_effect"] = round(it["net_revpar"] - it["physical_revpar"], 2)
    items.sort(key=lambda x: -x["est_loss"])

    net_revpar = round(sum_revenue / sum_available, 2) if sum_available else 0.0
    phys_revpar = round(sum_revenue / sum_inventory, 2) if sum_inventory else 0.0

    return {
        "items":          items,
        "total_days":     len(items),
        "total_ooo_rooms": total_ooo,
        "total_est_loss": round(total_loss, 2),
        "loss_share":     round(total_loss / sum_revenue, 6) if sum_revenue else 0.0,
        "period_revenue": round(sum_revenue, 2),
        "net_revpar":     net_revpar,
        "physical_revpar": phys_revpar,
        "denominator_effect": round(net_revpar - phys_revpar, 2),
        "sum_available_rooms": sum_available,
        "sum_inventory_rooms": sum_inventory,
        "monthly_series": [
            {"month": m, "ooo_rooms": v["ooo_rooms"], "est_loss": round(v["est_loss"], 2),
             "days": v["days"]}
            for m, v in sorted(monthly.items())
        ],
        "source_label":   "資料來源：History and Forecast",
        "disclaimer": (
            "估算採用當日 ADR，假設 OOO 房可以同價售出；實際需求不足時真實損失可能較低。"
            "另外 OOO 多時「可售房晚」分母變小，報表住房率與 RevPAR 會看起來較好，"
            "「實體房 RevPAR」才反映完整資產產能。"
        ),
    }


def get_trend(db: Session, start: str, end: str, property_code: str = "") -> dict:
    """月增率（MoM）與 7／28 日移動平均（規格書 §4.10）。

    ⚠️ 移動平均需要「期間開始日之前」的資料才算得準，因此會多抓 27 天當暖身，
       但只回傳期間內的列。少了這步，期間前 27 天的移動平均會被低估。
    """
    from datetime import timedelta

    warmup_start = (PS.to_date(start) - timedelta(days=27)).isoformat()
    rows = (
        _revenue_query(db, warmup_start, end, property_code, RECORD_TYPE_HISTORY)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )

    daily: list[dict] = []
    revenues: list[float] = []
    for r in rows:
        revenues.append(float(r.revenue))
        ma7 = sum(revenues[-7:]) / min(len(revenues), 7)
        ma28 = sum(revenues[-28:]) / min(len(revenues), 28)
        if r.business_date < start:
            continue
        daily.append({
            "business_date": r.business_date,
            "revenue":  round(float(r.revenue), 2),
            "ma7":      round(ma7, 2),
            "ma28":     round(ma28, 2),
            "rel_ma28": round(float(r.revenue) / ma28 - 1, 6) if ma28 else None,
            # 動能：7 日線高於 28 日線代表近期轉強
            "momentum": round(ma7 - ma28, 2),
        })

    # ── 月增率 ────────────────────────────────────────────────────────────
    months = sorted({r.business_date[:7] for r in rows if r.business_date >= start})
    monthly: list[dict] = []
    prev: dict | None = None
    for ym in months:
        y, m = int(ym[:4]), int(ym[5:7])
        ms, me = PS.month_range(y, m)
        agg = _aggregate(db, max(ms, start), min(me, end), property_code)
        if agg["days"] == 0:
            continue
        row = {
            "month": ym, "label": f"{y}/{m:02d}",
            **agg,
            "revenue_mom": _pct_change(agg["revenue"], prev["revenue"]) if prev else None,
            "adr_mom":     _pct_change(agg["adr"], prev["adr"]) if prev else None,
            "revpar_mom":  _pct_change(agg["revpar"], prev["revpar"]) if prev else None,
            "occupancy_mom_ppt": round(agg["occupancy"] - prev["occupancy"], 6) if prev else None,
            # 該月是否完整；不完整時 MoM 會被低估，前端要標示
            "is_partial": agg["days"] < (PS.month_end(y, m)),
        }
        monthly.append(row)
        prev = agg

    return {
        "daily":   daily,
        "monthly": monthly,
        "warmup_start": warmup_start,
        "source_label": "資料來源：History and Forecast",
        "note": (
            "移動平均已多取 27 天暖身資料計算，期間開頭的數值才不會被低估。"
            "月中未完整的月份 MoM 會偏低，表格已標示。"
        ),
    }


# ── 住客側：退房時間與入退房星期（2026-08-04 新增）───────────────────────────

CHECKOUT_BUCKETS: list[tuple[str, int | None, int | None]] = [
    ("10 點前",       None, 10 * 60 - 1),
    ("10:00–10:59",  10 * 60, 11 * 60 - 1),
    ("11:00–11:59",  11 * 60, 12 * 60 - 1),
    ("12:00–12:59",  12 * 60, 13 * 60 - 1),
    ("13 點後",       13 * 60, None),
]


def get_checkout_time_distribution(db: Session, start: str, end: str,
                                   property_code: str = "",
                                   basis: str = BASIS_ROOM) -> dict:
    """退房時間分布（規格書 §5.2）。用於櫃台、房務與行李服務的人力安排。"""
    rows = (
        db.query(
            OperaDepartureStay.departure_time_minutes,
            func.count(OperaDepartureStay.id),
        )
        .filter(*_stay_filters(start, end, property_code, basis))
        .group_by(OperaDepartureStay.departure_time_minutes)
        .all()
    )

    buckets = [{"label": lbl, "records": 0} for lbl, _, _ in CHECKOUT_BUCKETS]
    buckets.append({"label": "缺值", "records": 0})

    for minutes, cnt in rows:
        cnt = int(cnt)
        if minutes is None:
            buckets[-1]["records"] += cnt
            continue
        for idx, (_, lo, hi) in enumerate(CHECKOUT_BUCKETS):
            if (lo is None or minutes >= lo) and (hi is None or minutes <= hi):
                buckets[idx]["records"] += cnt
                break

    total = sum(b["records"] for b in buckets)
    for b in buckets:
        b["share"] = round(b["records"] / total, 6) if total else 0.0

    missing = buckets[-1]["records"]
    return {
        "buckets":       buckets,
        "total_records": total,
        "missing_records": missing,
        "missing_share": round(missing / total, 6) if total else 0.0,
        "basis":         basis,
        "basis_label":   BASIS_LABELS.get(basis, basis),
        "source_label":  "資料來源：Departure All",
        "note": (
            "缺值占比高時，應先改善前台輸入或報表欄位品質，再拿這張表做排班決策。"
        ),
    }


def get_stay_weekday(db: Session, start: str, end: str, property_code: str = "",
                     basis: str = BASIS_ROOM) -> dict:
    """入退房星期分布（規格書 §5.3）。

    ⚠️ 這是按訂單的「到店／離店事件」統計，**不是各星期的在住房晚**。
       到店高峰用於安排接待與備房，離店高峰用於安排結帳與清掃。
    """
    def _by_weekday(date_col) -> list[int]:
        rows = (
            db.query(date_col, func.coalesce(func.sum(OperaDepartureStay.no_of_rooms), 0))
            .filter(*_stay_filters(start, end, property_code, basis))
            .group_by(date_col)
            .all()
        )
        acc = [0] * 7
        for d, rooms in rows:
            if not d:
                continue
            try:
                acc[_weekday_index(d)] += int(rooms)
            except (ValueError, IndexError):
                continue
        return acc

    arrivals = _by_weekday(OperaDepartureStay.arrival_date)
    departures = _by_weekday(OperaDepartureStay.departure_date)
    ta, td = sum(arrivals) or 1, sum(departures) or 1

    return {
        "weekdays": [
            {
                "weekday": i,
                "label": WEEKDAY_LABELS[i],
                "arrival_rooms": arrivals[i],
                "departure_rooms": departures[i],
                "arrival_share": round(arrivals[i] / ta, 6),
                "departure_share": round(departures[i] / td, 6),
                "net_rooms": arrivals[i] - departures[i],
            }
            for i in range(7)
        ],
        "total_arrival_rooms": sum(arrivals),
        "total_departure_rooms": sum(departures),
        "basis":        basis,
        "basis_label":  BASIS_LABELS.get(basis, basis),
        "source_label": "資料來源：Departure All",
    }


# ── 房號使用、營運指標、客群結構（2026-08-04 新增）───────────────────────────

def get_room_usage(db: Session, start: str, end: str, property_code: str = "",
                   basis: str = BASIS_ROOM, inactive_months: int = 3) -> dict:
    """房號使用分析。

    找出「幾乎賣不出去」或「某個月之後就完全沒賣」的房間。

    ⚠️ **這是推論不是事實**：OPERA 的 OOO 只有每日總房數、沒有房號，
       Departure 也只記錄「賣出去」的房。因此無法直接得知哪一間房被停用，
       只能從「連續數月零銷售」推測。判讀時務必對照工程與房務紀錄。
    """
    rows = (
        db.query(
            OperaDepartureStay.room_no,
            func.substr(OperaDepartureStay.departure_date, 1, 7).label("ym"),
            func.count(OperaDepartureStay.id),
        )
        .filter(*_stay_filters(start, end, property_code, basis))
        .filter(OperaDepartureStay.room_no != "")
        .group_by(OperaDepartureStay.room_no, "ym")
        .all()
    )
    if not rows:
        return {"rooms": [], "months": [], "floors": [], "total_records": 0,
                "basis": basis, "basis_label": BASIS_LABELS.get(basis, basis),
                "source_label": "資料來源：Departure All", "inference_note": ""}

    matrix: dict[str, dict[str, int]] = defaultdict(dict)
    months: set[str] = set()
    for room_no, ym, cnt in rows:
        matrix[room_no][ym] = int(cnt)
        months.add(ym)
    month_list = sorted(months)

    # 期間各月的整體住房率 —— 用來判斷「該月沒賣」是因為沒需求還是房不能賣
    occ_by_month: dict[str, float] = {}
    for ym in month_list:
        y, m = int(ym[:4]), int(ym[5:7])
        ms, me = PS.month_range(y, m)
        agg = _aggregate(db, max(ms, start), min(me, end), property_code)
        occ_by_month[ym] = agg["occupancy"]

    total_records = sum(sum(v.values()) for v in matrix.values())
    avg_per_room = total_records / len(matrix) if matrix else 0

    rooms: list[dict] = []
    for room_no, per_month in matrix.items():
        counts = [per_month.get(ym, 0) for ym in month_list]
        records = sum(counts)
        active = [ym for ym in month_list if per_month.get(ym, 0) > 0]
        # 末次銷售之後連續幾個月完全沒賣
        trailing_zero = 0
        for ym in reversed(month_list):
            if per_month.get(ym, 0) > 0:
                break
            trailing_zero += 1
        # 零銷售月份中，全館住房率仍偏高的月數（更可疑）
        suspicious = sum(
            1 for ym in month_list
            if per_month.get(ym, 0) == 0 and occ_by_month.get(ym, 0) >= 0.6
        )
        rooms.append({
            "room_no": room_no,
            "floor": room_no[:2] if len(room_no) >= 3 else "—",
            "records": records,
            "share": round(records / total_records, 6) if total_records else 0.0,
            "vs_avg": round(records / avg_per_room, 3) if avg_per_room else 0.0,
            "monthly": counts,
            "active_months": len(active),
            "zero_months": len(month_list) - len(active),
            "first_month": active[0] if active else "",
            "last_month": active[-1] if active else "",
            "trailing_zero_months": trailing_zero,
            "suspicious_zero_months": suspicious,
            # 疑似停用：末次銷售後連續 N 個月零銷售
            "suspected_inactive": trailing_zero >= inactive_months,
        })
    rooms.sort(key=lambda x: x["records"])

    floors: dict[str, dict] = defaultdict(lambda: {"records": 0, "rooms": 0})
    for r in rooms:
        floors[r["floor"]]["records"] += r["records"]
        floors[r["floor"]]["rooms"] += 1
    floor_list = [
        {
            "floor": f,
            "records": v["records"],
            "rooms": v["rooms"],
            "avg_per_room": round(v["records"] / v["rooms"], 1) if v["rooms"] else 0.0,
            "share": round(v["records"] / total_records, 6) if total_records else 0.0,
        }
        for f, v in sorted(floors.items())
    ]

    busiest = rooms[-1]["records"] if rooms else 0
    quietest = rooms[0]["records"] if rooms else 0
    return {
        "rooms":          rooms,
        "months":         month_list,
        "monthly_occupancy": [round(occ_by_month.get(m, 0), 6) for m in month_list],
        "floors":         floor_list,
        "total_records":  total_records,
        "room_count":     len(rooms),
        "avg_per_room":   round(avg_per_room, 1),
        "busiest":        busiest,
        "quietest":       quietest,
        "spread_ratio":   round(busiest / quietest, 1) if quietest else None,
        "suspected_inactive_count": sum(1 for r in rooms if r["suspected_inactive"]),
        "inactive_months_threshold": inactive_months,
        "basis":          basis,
        "basis_label":    BASIS_LABELS.get(basis, basis),
        "source_label":   "資料來源：Departure All",
        "inference_note": (
            "OPERA 的 OOO 只有每日總房數、沒有房號，Departure 也只記錄賣出去的房，"
            "因此無法直接得知哪一間被停用。「疑似停用」是從『末次銷售後連續數月零銷售』推測，"
            "請對照工程與房務紀錄確認。「高住房率月份仍零銷售」的次數越多，越可能不是需求問題。"
        ),
    }


def get_operations_metrics(db: Session, start: str, end: str,
                           property_code: str = "") -> dict:
    """營運指標：每房人數、翻房率、每日進出量、非營收房監控。

    這些欄位 OPERA 都有給，但先前完全沒拿來分析。
    """
    row = (
        db.query(
            func.coalesce(func.sum(OperaRevenueDaily.no_persons), 0),
            func.coalesce(func.sum(OperaRevenueDaily.sold_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.arrival_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.departure_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.inventory_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.complimentary_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.house_use_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.day_use_rooms), 0),
            func.coalesce(func.sum(OperaRevenueDaily.no_show_rooms), 0),
            func.count(OperaRevenueDaily.id),
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
    persons, sold, arrivals, departures, inventory = (
        int(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4])
    )
    comp, house, day_use, no_show, days = (
        int(row[5]), int(row[6]), int(row[7]), int(row[8]), int(row[9])
    )

    daily_rows = (
        _revenue_query(db, start, end, property_code, RECORD_TYPE_HISTORY)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )
    daily = [
        {
            "business_date":  r.business_date,
            "arrival_rooms":  r.arrival_rooms,
            "departure_rooms": r.departure_rooms,
            "turnover_rooms": r.arrival_rooms + r.departure_rooms,
            "sold_rooms":     r.sold_rooms,
            "stayover_rooms": max(r.sold_rooms - r.arrival_rooms, 0),
            "persons_per_room": round(r.no_persons / r.sold_rooms, 2) if r.sold_rooms else 0.0,
        }
        for r in daily_rows
    ]

    avg_inventory = round(inventory / days, 1) if days else 0.0
    return {
        "days":              days,
        "persons":           persons,
        "sold_rooms":        sold,
        "persons_per_room":  round(persons / sold, 3) if sold else 0.0,
        "arrival_rooms":     arrivals,
        "departure_rooms":   departures,
        "turnover_rooms":    arrivals + departures,
        "avg_daily_arrival": round(arrivals / days, 1) if days else 0.0,
        "avg_daily_departure": round(departures / days, 1) if days else 0.0,
        "avg_daily_turnover": round((arrivals + departures) / days, 1) if days else 0.0,
        # 翻房率：到店房數 ÷ 已售房晚，代表每天有多少比例的房要重新整理
        "turnover_rate":     round(arrivals / sold, 6) if sold else 0.0,
        "avg_inventory":     avg_inventory,
        "stayover_rooms":    max(sold - arrivals, 0),
        "non_revenue": {
            "complimentary": comp,
            "house_use":     house,
            "day_use":       day_use,
            "no_show":       no_show,
            "total":         comp + house + day_use + no_show,
            "share_of_sold": round((comp + house + day_use + no_show) / sold, 6) if sold else 0.0,
        },
        "daily":         daily,
        "source_label":  "資料來源：History and Forecast",
        "note": (
            "翻房率 = 到店房數 ÷ 已售房晚，代表每天有多少比例的房需要重新整理（其餘為續住房）。"
            "每房人數影響早餐備量、備品消耗與加床需求的預估。"
        ),
    }


def get_guest_mix(db: Session, start: str, end: str, property_code: str = "",
                  basis: str = BASIS_ROOM) -> dict:
    """客群結構：每房人數分布與家庭客（帶兒童）分析。"""
    conds = _stay_filters(start, end, property_code, basis)

    occ_rows = (
        db.query(
            (OperaDepartureStay.adults + OperaDepartureStay.children).label("pax"),
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
        )
        .filter(*conds)
        .group_by("pax")
        .order_by("pax")
        .all()
    )
    distribution = [
        {"pax": int(p or 0), "records": int(c), "room_nights": int(rn)}
        for p, c, rn in occ_rows
    ]
    total_records = sum(d["records"] for d in distribution)
    total_pax = sum(d["pax"] * d["records"] for d in distribution)
    for d in distribution:
        d["share"] = round(d["records"] / total_records, 6) if total_records else 0.0

    fam_conds = conds + [OperaDepartureStay.children > 0]
    fam = (
        db.query(
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.children), 0),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
            func.coalesce(func.sum(OperaDepartureStay.nights), 0),
        )
        .filter(*fam_conds)
        .first()
    )
    fam_records, fam_children, fam_room_nights, fam_nights = (
        int(fam[0]), int(fam[1]), int(fam[2]), int(fam[3])
    )

    fam_by_category = (
        db.query(
            OperaDepartureStay.room_category_label,
            func.count(OperaDepartureStay.id),
        )
        .filter(*fam_conds)
        .group_by(OperaDepartureStay.room_category_label)
        .all()
    )
    # 家庭客在各房型的「集中度」＝ 該房型家庭客占比 ÷ 全體家庭客占比
    all_by_category = dict(
        db.query(OperaDepartureStay.room_category_label, func.count(OperaDepartureStay.id))
        .filter(*conds)
        .group_by(OperaDepartureStay.room_category_label)
        .all()
    )
    fam_share_overall = fam_records / total_records if total_records else 0
    categories = []
    for cat, cnt in fam_by_category:
        label = (cat or "").strip() or "（未標註）"
        total_cat = int(all_by_category.get(cat, 0)) or 1
        cat_share = int(cnt) / total_cat
        categories.append({
            "room_category": label,
            "family_records": int(cnt),
            "total_records": total_cat,
            "family_share": round(cat_share, 6),
            "index": round(cat_share / fam_share_overall, 2) if fam_share_overall else 0.0,
        })
    categories.sort(key=lambda x: -x["family_records"])

    all_nights = (
        db.query(func.coalesce(func.sum(OperaDepartureStay.nights), 0))
        .filter(*conds).scalar() or 0
    )

    return {
        "distribution":   distribution,
        "total_records":  total_records,
        "persons_per_room": round(total_pax / total_records, 3) if total_records else 0.0,
        "family": {
            "records":      fam_records,
            "share":        round(fam_share_overall, 6),
            "children":     fam_children,
            "room_nights":  fam_room_nights,
            "avg_los":      round(fam_nights / fam_records, 2) if fam_records else 0.0,
            "overall_avg_los": round(int(all_nights) / total_records, 2) if total_records else 0.0,
            "by_category":  categories,
        },
        "basis":        basis,
        "basis_label":  BASIS_LABELS.get(basis, basis),
        "source_label": "資料來源：Departure All",
        "note": (
            "「集中度」= 該房型的家庭客占比 ÷ 全體家庭客占比。大於 1 代表家庭客特別偏好這個房型，"
            "可用於加床、嬰兒床與早餐備量的房型別配置。"
        ),
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
    "group":         (OperaDepartureStay.group_name, "團體", "（無團體）"),
}


# ── 團體名稱正規化（2026-08-04）────────────────────────────────────────────────
# OPERA 的 GROUP_NAME 欄位實測混了兩種資料：
#   ① 真正的團體名稱      例：家扶基金會、中興大學森林系III、PIPE LIVE MUSIC CO., LTD.
#   ② OTA 訂房參考號＋人名 例：374648117 MA, WEI HSIN
# 而且 ② 的參考號後面「不一定」是人名，也可能是團體（例：392298933 中山醫學大學，30 筆）。
# 因此規則是：先剝掉參考號前綴，再判斷剩下的像不像「個人姓名」。
# 實測 35,334 筆：有值 3,807 筆 → 團體 1,534 筆（89 個）／個人 2,273 筆（794 個），
# 其中 156 筆是剝掉參考號後救回來的團體。
_GROUP_REF_PREFIX = re.compile(r"^\d{6,}\s+")
# OPERA 個人姓名格式：全大寫姓 + 逗號 + 名（與 GUEST_NAME 同格式）
_PERSON_LATIN = re.compile(r"^[A-Z][A-Z'\- ]*,\s*[A-Za-z]")
# 中文姓名：姓 1~2 字 + 逗號 + 名
_PERSON_CJK = re.compile(r"^[一-鿿]{1,2},\s*[一-鿿]{1,3}$")
# 逗號後若含這些字，判定為公司／組織而非個人（避免「森核, 公司」被誤殺）
_ORG_KEYWORDS = ("公司", "有限", "股份", "集團", "協會", "基金會", "中心", "學校", "大學", "工會")


def normalize_group_name(raw: str) -> tuple[str, bool, bool]:
    """回傳 (正規化後名稱, 原本是否帶訂房參考號, 是否疑似個人)。"""
    v = (raw or "").strip()
    if not v:
        return "", False, False
    had_ref = bool(_GROUP_REF_PREFIX.match(v))
    name = _GROUP_REF_PREFIX.sub("", v).strip()
    if not name:
        return "", had_ref, False
    is_person = bool(_PERSON_LATIN.match(name))
    if not is_person and _PERSON_CJK.match(name):
        tail = name.split(",", 1)[1] if "," in name else ""
        is_person = not any(k in tail for k in _ORG_KEYWORDS)
    return name, had_ref, is_person


def get_dimension_stats(db: Session, dimension: str, start: str, end: str,
                        property_code: str = "", basis: str = BASIS_ROOM,
                        limit: int = 0, min_nights: int = 0,
                        exclude_person: bool = True) -> dict:
    """通路／房型／Rate Code／公司／付款方式／團體統計（雙口徑，規格書 §11.10）。

    min_nights     > 0 時只計住宿晚數 ≥ 此值的紀錄（供長住客拆解用）
    exclude_person 僅對 dimension='group' 有效，排除疑似個人訂房
    """
    if dimension not in DIMENSION_COLUMNS:
        raise ValueError(f"不支援的維度：{dimension}")
    column, label, blank_label = DIMENSION_COLUMNS[dimension]

    conds = _stay_filters(start, end, property_code, basis)
    if min_nights > 0:
        conds.append(OperaDepartureStay.nights >= min_nights)
    if dimension == "group":
        # 團體維度不列「無團體」，否則 89% 的空白會把整張表洗掉
        conds.append(OperaDepartureStay.group_name != "")

    rows = (
        db.query(
            column,
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
            func.coalesce(func.sum(OperaDepartureStay.nights), 0),
            func.coalesce(func.sum(OperaDepartureStay.adults), 0),
            func.coalesce(func.sum(OperaDepartureStay.children), 0),
            # 一晚住宿的筆數（供「一晚住宿占比」用）
            func.coalesce(func.sum(
                case((OperaDepartureStay.nights == 1, 1), else_=0)
            ), 0),
        )
        .filter(*conds)
        .group_by(column)
        .all()
    )

    # ⚠️ 兒童數的 key 是 `child_count` 不是 `children`：Ant Design Table 預設把
    #    `record.children` 當成子列陣列，回傳數字會讓整個 Table 崩潰（見
    #    `OperaDepartureStay.to_dict()` 的說明）。這些 items 直接當 dataSource 用。
    raw_items = [
        {
            "key":         (r[0] or "").strip() or blank_label,
            "records":     int(r[1]),
            "room_nights": int(r[2]),
            "nights":      int(r[3]),
            "adults":      int(r[4]),
            "child_count": int(r[5]),
            "one_night_records": int(r[6]),
        }
        for r in rows
    ]

    person_records = 0
    if dimension == "group":
        raw_items, person_records = _merge_group_items(raw_items, exclude_person)

    items = raw_items
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
        # 平均住宿天數 LOS：以房數計時 records 即房數，故 room_nights ÷ records
        i["avg_los"] = round(i["room_nights"] / i["records"], 2) if i["records"] else 0.0
        i["one_night_share"] = (
            round(i["one_night_records"] / i["records"], 6) if i["records"] else 0.0
        )

    truncated = False
    if limit and len(items) > limit:
        items = items[:limit]
        truncated = True

    result = {
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
        "min_nights":    min_nights,
        "source_label":  "資料來源：Departure All",
    }
    if dimension == "group":
        result["exclude_person"] = exclude_person
        result["person_records"] = person_records
        result["group_note"] = (
            "OPERA 的 GROUP_NAME 欄位混了兩種資料：真正的團體名稱，以及「OTA 訂房參考號 + 訂房人姓名」。"
            "系統會先剝掉開頭的參考號（例如 `392298933 中山醫學大學` → `中山醫學大學`），"
            "再判斷剩下的是否為個人姓名格式。"
        )
    return result


def _merge_group_items(items: list[dict], exclude_person: bool) -> tuple[list[dict], int]:
    """把團體名稱正規化後合併同一團體，並依需要濾掉疑似個人訂房。"""
    merged: dict[str, dict] = {}
    person_records = 0
    for it in items:
        name, had_ref, is_person = normalize_group_name(it["key"])
        if not name:
            continue
        if is_person:
            person_records += it["records"]
            if exclude_person:
                continue
        tgt = merged.get(name)
        if tgt is None:
            merged[name] = {**it, "key": name, "had_ref": 1 if had_ref else 0,
                            "is_person": 1 if is_person else 0}
        else:
            for f in ("records", "room_nights", "nights", "adults", "child_count",
                      "one_night_records"):
                tgt[f] += it[f]
            tgt["had_ref"] = tgt["had_ref"] or (1 if had_ref else 0)
    return list(merged.values()), person_records


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


def get_los_buckets(db: Session, start: str, end: str, property_code: str = "",
                    basis: str = BASIS_ROOM) -> dict:
    """住宿天數（LOS）分桶。

    桶界由「分析門檻設定」的長住門檻 T 推導，而不是寫死 —— 這樣改門檻時
    分桶與長住占比不會打架（業主 2026-08-04 決定）。T = 7 時為：
        0 / 1 / 2 / 3 / 4–6 / 7–13 / 14+
    """
    cfg = get_settings(db, property_code)
    t = max(int(cfg["long_stay_nights"]), 2)

    rows = (
        db.query(
            OperaDepartureStay.nights,
            func.count(OperaDepartureStay.id),
            func.coalesce(func.sum(OperaDepartureStay.room_nights), 0),
        )
        .filter(*_stay_filters(start, end, property_code, basis))
        .group_by(OperaDepartureStay.nights)
        .all()
    )

    # (下界, 上界或 None 表示無上限, 標籤)
    edges: list[tuple[int, int | None, str]] = [
        (0, 0, "0 晚"), (1, 1, "1 晚"), (2, 2, "2 晚"), (3, 3, "3 晚"),
    ]
    if t > 4:
        edges.append((4, t - 1, f"4–{t - 1} 晚"))
    edges.append((t, 2 * t - 1, f"{t}–{2 * t - 1} 晚"))
    edges.append((2 * t, None, f"{2 * t}+ 晚"))

    buckets = [
        {"label": lbl, "lower": lo, "upper": hi, "records": 0, "room_nights": 0,
         "is_long_stay": lo >= t}
        for lo, hi, lbl in edges
    ]

    for nights, cnt, rn in rows:
        n = int(nights or 0)
        for b in buckets:
            if n >= b["lower"] and (b["upper"] is None or n <= b["upper"]):
                b["records"] += int(cnt)
                b["room_nights"] += int(rn)
                break

    total_records = sum(b["records"] for b in buckets)
    total_nights = sum(b["room_nights"] for b in buckets)
    for b in buckets:
        b["share"] = round(b["records"] / total_records, 6) if total_records else 0.0

    return {
        "threshold":     t,
        "buckets":       buckets,
        "total_records": total_records,
        "total_room_nights": total_nights,
        "avg_los":       round(total_nights / total_records, 2) if total_records else 0.0,
        "basis":         basis,
        "basis_label":   BASIS_LABELS.get(basis, basis),
        "source_label":  "資料來源：Departure All",
    }


def get_rate_opportunity(db: Session, start: str, end: str,
                         property_code: str = "") -> dict:
    """高住房率低 ADR 機會（規格書 §4.7）。

    找出住房率達門檻、但當日 ADR 低於期間加權 ADR 的日期，估算提升空間。

    ⚠️ 估算提升金額是**情境值**：假設同樣的房晚可以用基準 ADR 售出，
       不是已確定可追回的收入，也不是會計損失。
    """
    cfg = get_settings(db, property_code)
    threshold = float(cfg["opportunity_occupancy_threshold"])
    overall = _aggregate(db, start, end, property_code)
    base_adr = overall["adr"]

    rows = (
        _revenue_query(db, start, end, property_code, RECORD_TYPE_HISTORY)
        .order_by(OperaRevenueDaily.business_date)
        .all()
    )

    items: list[dict] = []
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"days": 0, "uplift": 0.0})
    for r in rows:
        if not r.available_rooms or not r.sold_rooms:
            continue
        occ, adr = r.occupancy, r.adr
        if occ < threshold or adr >= base_adr:
            continue
        gap = base_adr - adr
        uplift = gap * r.sold_rooms
        month = r.business_date[:7]
        monthly[month]["days"] += 1
        monthly[month]["uplift"] += uplift
        items.append({
            "business_date":   r.business_date,
            "month":           month,
            "revenue":         float(r.revenue),
            "sold_rooms":      r.sold_rooms,
            "available_rooms": r.available_rooms,
            "occupancy":       round(occ, 6),
            "adr":             round(adr, 2),
            "baseline_adr":    base_adr,
            "adr_gap":         round(gap, 2),
            "est_uplift":      round(uplift, 2),
        })

    items.sort(key=lambda x: -x["est_uplift"])
    total_uplift = round(sum(i["est_uplift"] for i in items), 2)
    total_revenue = overall["revenue"]

    return {
        "threshold":       round(threshold, 6),
        "baseline_adr":    base_adr,
        "baseline_occupancy": overall["occupancy"],
        "period_revenue":  total_revenue,
        "items":           items,
        "total_days":      len(items),
        "total_uplift":    total_uplift,
        "uplift_share":    round(total_uplift / total_revenue, 6) if total_revenue else 0.0,
        "monthly_series":  [
            {"month": m, "days": v["days"], "uplift": round(v["uplift"], 2)}
            for m, v in sorted(monthly.items())
        ],
        "source_label":    "資料來源：History and Forecast",
        "disclaimer":      (
            "估算提升金額是情境值：假設同樣房晚可以用期間加權 ADR 售出，"
            "並非已確定可追回的收入，也不是會計損失。"
        ),
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
