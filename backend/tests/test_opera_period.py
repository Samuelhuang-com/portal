"""
OPERA 期間規則單元測試（規格書 §9.2）

重點是「部分期間不可與去年完整期間相比」這條規則，以及
1/1～1/31 必須判為完整月份（不是部分年度）。

執行：
    cd backend && python -m pytest tests/test_opera_period.py -v
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.services import opera_period_service as PS


@pytest.fixture()
def db():
    """建一個只有 opera_revenue_daily 的臨時 SQLite，塞 2025 全年 + 2026 前 8 月的 History。"""
    engine = create_engine("sqlite://")   # in-memory
    Session = sessionmaker(bind=engine)
    session = Session()
    session.execute(text(
        "CREATE TABLE opera_revenue_daily ("
        " id INTEGER PRIMARY KEY, property_code TEXT, record_type TEXT,"
        " business_date TEXT, is_current INTEGER)"
    ))
    from datetime import date, timedelta
    rows = []
    cur, end = date(2025, 1, 1), date(2026, 8, 3)
    while cur <= end:
        rows.append({"p": "SUMMER", "rt": "History", "d": cur.isoformat()})
        cur += timedelta(days=1)
    session.execute(
        text("INSERT INTO opera_revenue_daily (property_code, record_type, business_date, is_current)"
             " VALUES (:p, :rt, :d, 1)"),
        rows,
    )
    session.commit()
    yield session
    session.close()


# ── 期間型態判定 ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("start,end,expected_type", [
    ("2025-01-01", "2025-12-31", PS.PERIOD_FULL_YEAR),
    ("2025-01-01", "2025-01-31", PS.PERIOD_FULL_MONTH),    # ⚠️ 不是部分年度
    ("2025-02-01", "2025-02-28", PS.PERIOD_FULL_MONTH),
    ("2026-01-01", "2026-08-03", PS.PERIOD_PARTIAL_YEAR),
    ("2026-08-01", "2026-08-03", PS.PERIOD_PARTIAL_MONTH),
    ("2026-03-15", "2026-04-10", PS.PERIOD_CUSTOM),
])
def test_period_type(db, start, end, expected_type):
    assert PS.resolve_period(db, start, end).period_type == expected_type


def test_full_year_requires_complete_data(db):
    """2026 只有到 8/3，即使起迄填整年也必須降級為部分年度。"""
    p = PS.resolve_period(db, "2026-01-01", "2026-12-31")
    assert p.period_type == PS.PERIOD_PARTIAL_YEAR
    assert p.is_complete is False
    assert p.data_days < p.expected_days
    assert "資料未滿全年" in p.period_label


# ── 同期比較範圍 ─────────────────────────────────────────────────────────────

def test_full_year_compares_full_previous_year(db):
    p = PS.resolve_period(db, "2025-01-01", "2025-12-31")
    assert p.is_complete is True
    assert (p.compare_start, p.compare_end) == ("2024-01-01", "2024-12-31")


def test_partial_year_compares_ytd_not_full_year(db):
    """部分年度只能比去年同期 YTD —— 這是最容易做錯的一條。"""
    p = PS.resolve_period(db, "2026-01-01", "2026-08-03")
    assert (p.compare_start, p.compare_end) == ("2025-01-01", "2025-08-03")
    assert p.compare_end != "2025-12-31"


def test_partial_month_compares_mtd_not_full_month(db):
    """部分月份只能比去年同月 1 日～相同日的 MTD。"""
    p = PS.resolve_period(db, "2026-08-01", "2026-08-03")
    assert (p.compare_start, p.compare_end) == ("2025-08-01", "2025-08-03")
    assert p.compare_end != "2025-08-31"


def test_full_month_compares_full_previous_month(db):
    p = PS.resolve_period(db, "2025-03-01", "2025-03-31")
    assert (p.compare_start, p.compare_end) == ("2024-03-01", "2024-03-31")


def test_leap_day_shift_is_safe(db):
    """2024-02-29 往前一年沒有 2/29，必須退到 2/28 而不是拋例外。"""
    assert PS.shift_year(PS.to_date("2024-02-29"), -1).isoformat() == "2023-02-28"


# ── 工具函式 ─────────────────────────────────────────────────────────────────

def test_days_in_year():
    assert PS.days_in_year(2024) == 366
    assert PS.days_in_year(2025) == 365


def test_month_end():
    assert PS.month_end(2024, 2) == 29
    assert PS.month_end(2025, 2) == 28
    assert PS.month_end(2025, 4) == 30


def test_default_range_uses_history_coverage(db):
    assert PS.default_range(db) == ("2025-01-01", "2026-08-03")


def test_count_data_days(db):
    assert PS.count_data_days(db, "2025-01-01", "2025-01-31") == 31
    assert PS.count_data_days(db, "2026-08-01", "2026-08-31") == 3
