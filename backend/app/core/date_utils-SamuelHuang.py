"""
日期工具函式 — 共用於各 Dashboard 月份統計
"""
import calendar
import re
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


def ascii_filename_label(label: str) -> str:
    """
    將期間標籤轉為純 ASCII 的檔名片段。

    用途：Content-Disposition 的 `filename=` 只能是 Latin-1，
    中文（例如「2026年度」）會讓 Starlette 在組 header 時丟
    UnicodeEncodeError，整支匯出 API 直接 500。中文檔名一律走
    `filename*=UTF-8''...`，`filename=` 只放這個 ASCII 後備值。

    Examples:
        >>> ascii_filename_label("2026-09")
        '2026-09'
        >>> ascii_filename_label("2026年度")
        '2026FY'
        >>> ascii_filename_label("2026-01~2026-06")
        '2026-01_2026-06'
        >>> ascii_filename_label("")
        'all'
    """
    safe = (label or "").replace("~", "_")
    safe = re.sub(r"(\d{4})\s*年度", r"\1FY", safe)   # 2026年度 → 2026FY
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", safe)      # 其餘非 ASCII 一律換掉
    safe = re.sub(r"_{2,}", "_", safe).strip("_")
    return safe or "all"
