"""
日期工具函式 — 共用於各 Dashboard 月份統計
"""
import calendar
from datetime import date


def get_month_range(month: str) -> tuple[date, date]:
    """
    將 "YYYY-MM" 或 "YYYY/MM" 格式轉換為該月的起始日與結束日（兩端均含）。

    Args:
        month: 月份字串，如 "2026-05" 或 "2026/05"

    Returns:
        (start_date, end_date): 該月第一天與最後一天

    Examples:
        >>> get_month_range("2026-05")
        (date(2026, 5, 1), date(2026, 5, 31))
        >>> get_month_range("2026/02")
        (date(2026, 2, 1), date(2026, 2, 28))
    """
    normalized = month.replace("/", "-")   # 統一為 YYYY-MM
    parts = normalized.split("-")
    year, mon = int(parts[0]), int(parts[1])
    start_date = date(year, mon, 1)
    last_day   = calendar.monthrange(year, mon)[1]
    end_date   = date(year, mon, last_day)
    return start_date, end_date


def to_ragic_year_month(month: str) -> str:
    """
    將 "YYYY-MM" 轉換為 Ragic DB 查詢用的 "YYYY/MM" 格式。

    Examples:
        >>> to_ragic_year_month("2026-05")
        "2026/05"
    """
    return month.replace("-", "/")


def current_month_str() -> str:
    """回傳目前月份的 YYYY-MM 字串"""
    return date.today().strftime("%Y-%m")
