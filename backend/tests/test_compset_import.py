"""
競品分析 — CSV 備援匯入測試

規格書：docs/SPEC_compset_analysis.md §6.4、D16、D17
服務層：app/services/compset_import_service.py

重點測的是「會讓資料悄悄變錯」的路徑：
  · CSV **不可覆蓋** SerpApi 那一列（唯一鍵含 source，兩列並存）
  · 打錯字的價格要報錯，**不可以變成靜默的缺值**
  · 沒有價 ＋ 標示滿房 是**合法**的一列，不是錯誤
  · `tax_included='no'` 只有這裡合法

執行：
    cd backend && python -m pytest tests/test_compset_import.py -v
"""
from __future__ import annotations

import importlib
import pkgutil
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models as _models_pkg
from app.core.database import Base

for _m in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app.models.compset_analysis import (SOURCE_PRIORITY,          # noqa: E402
                                         CompsetHotel,
                                         CompsetRateSnapshot,
                                         CompsetSubscriber)
from app.services import compset_import_service as I               # noqa: E402
from app.services import compset_serpapi_client as SC              # noqa: E402
from app.services.compset_fetch_service import upsert_snapshot     # noqa: E402

TODAY = date(2026, 9, 9)
HEADER = "快照日期,入住日期,飯店,含稅價,稅前價,幣別,含稅,是否滿房,通路,房型,入住人數\n"


def csv_bytes(*rows: str, header: str = HEADER, encoding: str = "utf-8-sig") -> bytes:
    return (header + "".join(r + "\n" for r in rows)).encode(encoding)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    tables = [t for n, t in Base.metadata.tables.items()
              if n.startswith("compset_") or n in ("users", "audit_logs", "tenants")]
    Base.metadata.create_all(engine, tables=tables)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture()
def sub(db):
    row = CompsetSubscriber(
        code="INTERNAL", name="內部", monthly_quota=1000, quota_used=0,
        quota_anchor_day=1, quota_period_start="", plan_level="A",
        window_a_days=14, window_b_days=45, window_c_days=120,
        freq_a_days=1, freq_b_days=3, freq_c_days=7, location_query="公館 台北",
        param_adults=2, param_nights=1, param_gl="tw", param_hl="zh-tw",
        param_currency="TWD", is_active=True,
        contact_name="", contact_email="", note="",
    )
    db.add(row)
    db.flush()
    db.add(CompsetHotel(subscriber_id=row.id, display_name="承攜行旅-台北台大館",
                        hotel_code="GUIDE_NTU", google_property_token="tok-guide",
                        google_query_name="承攜行旅 - 台北台大館", is_self=False,
                        is_enabled=True, sort_order=1,
                        registered_address="", note=""))
    db.add(CompsetHotel(subscriber_id=row.id, display_name="瀚寓夏天",
                        hotel_code="SUMMER", google_property_token="tok-self",
                        google_query_name="瀚寓夏天 Hanns Summer", is_self=True,
                        is_enabled=True, sort_order=0,
                        registered_address="", note=""))
    db.commit()
    return row


# ══════════════════════════════════════════════════════════════════════════
# 1. 欄位解析
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("raw,expected", [
    ("1900", 1900.0), ("$1,900", 1900.0), ("NT$1,900", 1900.0),
    ("1,900 元", 1900.0), ("  1900.50 ", 1900.5), ("", None),
])
def test_parse_price(raw, expected):
    assert I.parse_price(raw) == expected


def test_parse_price_raises_on_garbage():
    """
    ⭐ 打錯字必須報錯，**不可以回 None**。
    回 None 會讓「打錯字」變成「刻意留空」，錯誤就此靜默。
    """
    with pytest.raises(ValueError):
        I.parse_price("約一千九")


@pytest.mark.parametrize("raw,expected", [
    ("2026-09-20", "2026-09-20"), ("2026/9/20", "2026-09-20"),
    ("2026.9.20", "2026-09-20"), ("", None),
])
def test_parse_date(raw, expected):
    assert I.parse_date(raw) == expected


@pytest.mark.parametrize("raw", ["2026-13-01", "2026-02-30", "20260920"])
def test_parse_date_rejects_invalid(raw):
    with pytest.raises(ValueError):
        I.parse_date(raw)


@pytest.mark.parametrize("raw,expected", [
    ("是", "yes"), ("否", "no"), ("不確定", "unknown"),
    ("Y", "yes"), ("no", "no"), ("", "unknown"),
])
def test_parse_tristate(raw, expected):
    assert I.parse_tristate(raw, "unknown") == expected


def test_parse_tristate_rejects_junk():
    with pytest.raises(ValueError):
        I.parse_tristate("大概吧", "unknown")


# ══════════════════════════════════════════════════════════════════════════
# 2. 檔案解析
# ══════════════════════════════════════════════════════════════════════════
def test_parse_csv_missing_required_header():
    rows, errors = I.parse_csv("入住日期,含稅價\n2026-09-20,1900\n".encode("utf-8-sig"))
    assert rows == [] and errors and "飯店" in errors[0]


def test_parse_csv_accepts_cp950():
    """舊版 Excel 繁中存檔會是 cp950，不能因此整檔讀不到。"""
    rows, errors = I.parse_csv(csv_bytes("2026-09-09,2026-09-20,瀚寓夏天,1900,,,,,,,",
                                         encoding="cp950"))
    assert not errors and len(rows) == 1


def test_template_round_trips():
    """範本自己要匯得回去 —— 範本填錯是最尷尬的 bug。"""
    rows, errors = I.parse_csv(I.csv_template())
    assert not errors and len(rows) == 2


# ══════════════════════════════════════════════════════════════════════════
# 3. 匯入
# ══════════════════════════════════════════════════════════════════════════
def test_import_happy_path(db, sub):
    res = I.import_rates(db, subscriber_id=sub.id, today=TODAY, content=csv_bytes(
        "2026-09-09,2026-09-20,承攜行旅-台北台大館,1274,1103,TWD,是,否,Booking.com,標準雙人房,2",
        "2026-09-09,2026-09-20,瀚寓夏天,1900,1645,TWD,是,否,官網,,2",
    ))
    assert res.inserted == 2 and res.skipped == 0 and res.errors == []
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert len(rows) == 2
    assert {r.source for r in rows} == {"csv"}
    guide = next(r for r in rows if r.ota_name == "Booking.com")
    assert (float(guide.price_gross), float(guide.price_pretax)) == (1274.0, 1103.0)
    assert guide.tax_included == "yes" and guide.is_sold_out == "no"
    assert guide.num_guests == 2 and guide.room_type_raw == "標準雙人房"


def test_import_matches_hotel_by_code_and_by_google_name(db, sub):
    """代碼、建檔名稱、Google 名稱三種寫法都要對得到同一家。"""
    res = I.import_rates(db, subscriber_id=sub.id, today=TODAY, content=csv_bytes(
        ",2026-09-20,GUIDE_NTU,1274,,,,,,,",
        ",2026-09-21,承攜行旅 - 台北台大館,1300,,,,,,,",
    ))
    assert res.inserted == 2 and res.errors == []


def test_import_defaults_snapshot_date_to_today(db, sub):
    I.import_rates(db, subscriber_id=sub.id, today=TODAY,
                   content=csv_bytes(",2026-09-20,瀚寓夏天,1900,,,,,,,"))
    row = db.execute(select(CompsetRateSnapshot)).scalars().one()
    assert row.snapshot_date == "2026-09-09"


def test_import_is_row_by_row_with_error_report(db, sub):
    """
    ⭐ D17：能匯的先匯，壞掉的列列出**行號**與原因。
    一列拼錯就整檔退回，救生艇就沒得用了。
    """
    res = I.import_rates(db, subscriber_id=sub.id, today=TODAY, content=csv_bytes(
        "2026-09-09,2026-09-20,瀚寓夏天,1900,,,,,,,",          # 第 2 列 OK
        "2026-09-09,2026-09-20,不存在的飯店,1900,,,,,,,",       # 第 3 列 對不到
        "2026-09-09,2026-13-99,瀚寓夏天,1900,,,,,,,",          # 第 4 列 日期爛
        "2026-09-09,2026-09-21,瀚寓夏天,約一千九,,,,,,,",       # 第 5 列 價格爛
    ))
    assert res.total_rows == 4
    assert res.inserted == 1 and res.skipped == 3
    assert len(res.errors) == 3
    assert res.errors[0].startswith("第 3 列") and "不存在的飯店" in res.errors[0]
    assert res.errors[1].startswith("第 4 列")
    assert res.errors[2].startswith("第 5 列")
    assert len(db.execute(select(CompsetRateSnapshot)).scalars().all()) == 1


def test_import_sold_out_row_without_price_is_valid(db, sub):
    """
    ⭐ 沒有價 ＋ 標示滿房 ＝ 合法的一列（SPEC §5.4）。
    「賣完」本身就是資料，不可以因為沒填價格就當成錯誤丟掉。
    """
    res = I.import_rates(db, subscriber_id=sub.id, today=TODAY,
                         content=csv_bytes(",2026-12-31,瀚寓夏天,,,,,是,,,"))
    assert res.inserted == 1 and res.errors == []
    row = db.execute(select(CompsetRateSnapshot)).scalars().one()
    assert row.is_sold_out == "yes" and row.price_gross is None


def test_import_rejects_row_with_neither_price_nor_sold_out(db, sub):
    res = I.import_rates(db, subscriber_id=sub.id, today=TODAY,
                         content=csv_bytes(",2026-09-20,瀚寓夏天,,,,,,,,"))
    assert res.inserted == 0 and len(res.errors) == 1


def test_import_allows_explicit_tax_no(db, sub):
    """
    ⭐ `tax_included='no'` **只有 CSV 合法** ——
    SerpApi 的回應永遠推導不出 no（見 compset_serpapi_client 規則 4）。
    只有人工匯入時，使用者才能宣告「這是稅前價」。
    """
    res = I.import_rates(db, subscriber_id=sub.id, today=TODAY,
                         content=csv_bytes(",2026-09-20,瀚寓夏天,1645,,,否,,,,"))
    assert res.inserted == 1
    assert db.execute(select(CompsetRateSnapshot)).scalars().one().tax_included == "no"


def test_import_infers_tax_state_when_blank(db, sub):
    """留空時沿用抓取層的推導：兩價相同 → unknown，不是 no。"""
    I.import_rates(db, subscriber_id=sub.id, today=TODAY,
                   content=csv_bytes(",2026-09-20,瀚寓夏天,1000,1000,,,,,,"))
    assert db.execute(select(CompsetRateSnapshot)).scalars().one().tax_included == "unknown"


def test_import_unknown_subscriber(db):
    res = I.import_rates(db, subscriber_id=999, today=TODAY,
                         content=csv_bytes(",2026-09-20,x,1,,,,,,,"))
    assert res.inserted == 0 and res.errors


# ══════════════════════════════════════════════════════════════════════════
# 4. ⭐ 與 SerpApi 並存（D16）
# ══════════════════════════════════════════════════════════════════════════
def test_csv_does_not_overwrite_serpapi_row(db, sub):
    """
    ⭐⭐ D16：唯一鍵含 `source`，所以同一格會有**兩列**。

    CSV 的用途是補上抓不到的格子，不是覆蓋抓得到的格子 ——
    如果這裡變成覆蓋，原本的 API 值就永遠拿不回來了。
    """
    hotel = db.execute(select(CompsetHotel)
                       .where(CompsetHotel.hotel_code == "SUMMER")).scalar_one()
    upsert_snapshot(db, sub_id=sub.id, hotel_id=hotel.id,
                    snapshot_date="2026-09-09", stay_date="2026-09-20",
                    tier="A", fetch_path="token",
                    parsed=SC.ParsedRate(price_gross=1900, price_pretax=1645,
                                         tax_included="yes", is_sold_out="no"))
    db.commit()

    I.import_rates(db, subscriber_id=sub.id, today=TODAY,
                   content=csv_bytes(",2026-09-20,瀚寓夏天,1750,,,,,,,"))

    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert len(rows) == 2
    by_source = {r.source: r for r in rows}
    assert float(by_source["serpapi"].price_gross) == 1900.0     # 原值沒被動到
    assert float(by_source["csv"].price_gross) == 1750.0


def test_source_priority_puts_serpapi_first(db):
    """
    統計層要照 `SOURCE_PRIORITY` 取一筆，不可以兩列都算進中位數 ——
    同一家在同一天被算兩次，中位數直接歪掉。
    """
    assert SOURCE_PRIORITY[0] == "serpapi"
    assert "csv" in SOURCE_PRIORITY


def test_reimport_same_cell_updates_csv_row_only(db, sub):
    """同一格重匯 CSV 是更新那一列，不是再長一列。"""
    for price in ("1750", "1800"):
        I.import_rates(db, subscriber_id=sub.id, today=TODAY,
                       content=csv_bytes(f",2026-09-20,瀚寓夏天,{price},,,,,,,"))
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert len(rows) == 1 and float(rows[0].price_gross) == 1800.0
