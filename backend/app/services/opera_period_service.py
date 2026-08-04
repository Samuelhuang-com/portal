"""
OPERA 期間規則服務 — 完整／部分期間判定與同期比較範圍

規格書：docs/SPEC_opera_analytics.md §9.2

核心原則（不可便宜行事）：
  * 部分月份只能比「去年同月 1 日～相同日」的 MTD，不可比去年整月。
  * 部分年度只能比「去年同期 YTD」，不可比去年整年。
  * Forecast 不得混入 Actual／History 的同期比較。
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.opera_revenue import RECORD_TYPE_HISTORY

PERIOD_FULL_YEAR = "FULL_YEAR"
PERIOD_PARTIAL_YEAR = "PARTIAL_YEAR"
PERIOD_FULL_MONTH = "FULL_MONTH"
PERIOD_PARTIAL_MONTH = "PARTIAL_MONTH"
PERIOD_CUSTOM = "CUSTOM"

PERIOD_LABELS = {
    PERIOD_FULL_YEAR:     "完整年度",
    PERIOD_PARTIAL_YEAR:  "部分年度（YTD）",
    PERIOD_FULL_MONTH:    "完整月份",
    PERIOD_PARTIAL_MONTH: "部分月份（MTD）",
    PERIOD_CUSTOM:        "自訂期間",
}

COMPARE_LABELS = {
    PERIOD_FULL_YEAR:     "去年全年",
    PERIOD_PARTIAL_YEAR:  "去年同期 YTD",
    PERIOD_FULL_MONTH:    "去年同月",
    PERIOD_PARTIAL_MONTH: "去年同期 MTD",
    PERIOD_CUSTOM:        "去年同期",
}


@dataclass
class PeriodInfo:
    start: str
    end: str
    period_type: str
    period_label: str
    compare_start: str
    compare_end: str
    compare_label: str
    data_days: int
    expected_days: int
    is_complete: bool

    def as_dict(self) -> dict:
        return {
            "start":         self.start,
            "end":           self.end,
            "period_type":   self.period_type,
            "period_label":  self.period_label,
            "compare_start": self.compare_start,
            "compare_end":   self.compare_end,
            "compare_label": self.compare_label,
            "data_days":     self.data_days,
            "expected_days": self.expected_days,
            "is_complete":   self.is_complete,
        }


# ── 日期工具 ──────────────────────────────────────────────────────────────────

def to_date(iso: str) -> date:
    y, m, d = iso.split("-")
    return date(int(y), int(m), int(d))


def days_in_year(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def month_end(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def shift_year(d: date, delta: int) -> date:
    """安全地位移年份（2/29 → 非閏年時退到 2/28）。"""
    y = d.year + delta
    day = d.day
    if d.month == 2 and day == 29 and not calendar.isleap(y):
        day = 28
    return date(y, d.month, day)


# ── 期間判定 ──────────────────────────────────────────────────────────────────

def count_data_days(
    db: Session, start: str, end: str,
    property_code: str = "", record_type: str = RECORD_TYPE_HISTORY,
) -> int:
    """該期間內實際有資料的「不重複日數」（規格書 §9.2 判定完整期間的必要條件）。"""
    sql = (
        "SELECT COUNT(DISTINCT business_date) FROM opera_revenue_daily "
        "WHERE is_current = 1 AND record_type = :rt "
        "AND business_date >= :s AND business_date <= :e"
    )
    params: dict = {"rt": record_type, "s": start, "e": end}
    if property_code:
        sql += " AND property_code = :p"
        params["p"] = property_code
    row = db.execute(text(sql), params).first()
    return int(row[0]) if row and row[0] else 0


def resolve_period(
    db: Session, start: str, end: str,
    property_code: str = "", record_type: str = RECORD_TYPE_HISTORY,
) -> PeriodInfo:
    """判定期間型態並算出同期比較範圍。"""
    s, e = to_date(start), to_date(end)
    if s > e:
        s, e = e, s
    data_days = count_data_days(db, s.isoformat(), e.isoformat(), property_code, record_type)

    period_type = PERIOD_CUSTOM
    expected_days = (e - s).days + 1

    same_year = s.year == e.year
    # ⚠️ 先判月再判年：1/1～1/31 是「完整月份」而不是「部分年度」。
    if same_year and s.month == e.month and s.day == 1:
        if e.day == month_end(e.year, e.month):
            period_type = PERIOD_FULL_MONTH
            expected_days = month_end(e.year, e.month)
        else:
            period_type = PERIOD_PARTIAL_MONTH
    elif same_year and s.month == 1 and s.day == 1:
        if e.month == 12 and e.day == 31:
            period_type = PERIOD_FULL_YEAR
            expected_days = days_in_year(s.year)
        else:
            period_type = PERIOD_PARTIAL_YEAR

    # 「完整」的認定：起迄日對齊 **且** 資料日數等於應有日數（規格書 §9.2）
    is_complete = period_type in (PERIOD_FULL_YEAR, PERIOD_FULL_MONTH) and data_days == expected_days
    if period_type == PERIOD_FULL_YEAR and not is_complete:
        period_type = PERIOD_PARTIAL_YEAR
    elif period_type == PERIOD_FULL_MONTH and not is_complete:
        period_type = PERIOD_PARTIAL_MONTH

    # 同期比較範圍：一律「去年相同月日」
    #   完整年度 → 去年整年；完整月份 → 去年整月；其餘一律截到相同月日（YTD／MTD）
    if period_type == PERIOD_FULL_YEAR:
        cs, ce = date(s.year - 1, 1, 1), date(s.year - 1, 12, 31)
    elif period_type == PERIOD_FULL_MONTH:
        py, pm = s.year - 1, s.month
        cs, ce = date(py, pm, 1), date(py, pm, month_end(py, pm))
    else:
        cs, ce = shift_year(s, -1), shift_year(e, -1)

    label = PERIOD_LABELS[period_type]
    if period_type == PERIOD_PARTIAL_YEAR:
        # 區分兩種「不完整」：日期沒到年底 vs 日期到了但資料有缺口
        if e.month == 12 and e.day == 31:
            label = f"部分年度（資料未滿全年，{data_days}／{expected_days} 天）"
        else:
            label = f"部分年度（YTD 至 {e.month:02d}-{e.day:02d}）"
    elif period_type == PERIOD_PARTIAL_MONTH:
        if e.day == month_end(e.year, e.month):
            label = f"部分月份（資料未滿整月，{data_days}／{expected_days} 天）"
        else:
            label = f"部分月份（MTD 至 {e.day} 日）"
    elif period_type == PERIOD_FULL_MONTH:
        label = f"完整月份（{s.year}-{s.month:02d}）"
    elif period_type == PERIOD_FULL_YEAR:
        label = f"完整年度（{s.year}）"

    return PeriodInfo(
        start=s.isoformat(),
        end=e.isoformat(),
        period_type=period_type,
        period_label=label,
        compare_start=cs.isoformat(),
        compare_end=ce.isoformat(),
        compare_label=COMPARE_LABELS[period_type],
        data_days=data_days,
        expected_days=expected_days,
        is_complete=is_complete,
    )


def default_range(db: Session, property_code: str = "") -> tuple[str, str]:
    """預設分析區間 = 資料庫中 History 的完整涵蓋範圍。"""
    sql = (
        "SELECT MIN(business_date), MAX(business_date) FROM opera_revenue_daily "
        "WHERE is_current = 1 AND record_type = :rt"
    )
    params: dict = {"rt": RECORD_TYPE_HISTORY}
    if property_code:
        sql += " AND property_code = :p"
        params["p"] = property_code
    row = db.execute(text(sql), params).first()
    if not row or not row[0]:
        today = date.today()
        return date(today.year, 1, 1).isoformat(), today.isoformat()
    return row[0], row[1]


def month_range(year: int, month: int) -> tuple[str, str]:
    return (
        date(year, month, 1).isoformat(),
        date(year, month, month_end(year, month)).isoformat(),
    )


def year_range(year: int) -> tuple[str, str]:
    return date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat()


def iter_dates(start: str, end: str):
    cur, last = to_date(start), to_date(end)
    while cur <= last:
        yield cur.isoformat()
        cur += timedelta(days=1)
