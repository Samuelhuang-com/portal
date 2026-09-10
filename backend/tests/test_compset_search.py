"""
競品分析 — 競爭組候選搜尋測試

規格書：docs/SPEC_compset_analysis.md §9.4c
服務層：app/services/compset_search_service.py

⚠️ 這支服務是**排程以外的第二個花錢入口**，所以測試重心不是「有沒有回清單」，
   而是「錢有沒有被算對」：

   · 預留不到就**不送請求**（不是送了才發現超額）
   · 沒用到的頁數要**退還**
   · 每一次都要寫 `compset_fetch_logs`（查不到來源的支出＝事後說不清）
   · 已在競爭組的家要標出來（否則會重複加）
   · 沒有座標的家不能消失，只是不上地圖

執行：
    cd backend && python -m pytest tests/test_compset_search.py -v
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

from app.models.compset_analysis import (CompsetFetchLog,          # noqa: E402
                                         CompsetHotel,
                                         CompsetSubscriber)
from app.services import compset_quota_service as QS               # noqa: E402
from app.services import compset_search_service as S               # noqa: E402

TODAY = date(2026, 9, 10)


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
        code="INTERNAL", name="內部", monthly_quota=100, quota_used=0,
        quota_anchor_day=1, quota_period_start="", plan_level="A",
        window_a_days=14, window_b_days=45, window_c_days=120,
        freq_a_days=1, freq_b_days=3, freq_c_days=7, location_query="公館 台北",
        param_adults=2, param_nights=1, param_gl="tw", param_hl="zh-tw",
        param_currency="TWD", is_active=True,
        contact_name="", contact_email="", note="",
    )
    db.add(row)
    db.flush()
    # 自己（有座標）＋ 一家已在組內（有 token）
    db.add(CompsetHotel(
        subscriber_id=row.id, display_name="瀚寓夏天", short_name="瀚寓",
        hotel_code="HANNS", google_property_token="tok_self",
        google_query_name="瀚寓夏天", is_self=True, is_enabled=True, sort_order=0,
        latitude=25.0154982, longitude=121.5313595,
        registered_address="", note=""))
    db.add(CompsetHotel(
        subscriber_id=row.id, display_name="承攜行旅", short_name="承攜",
        hotel_code="GUIDE", google_property_token="tok_guide",
        google_query_name="承攜行旅 - 台北台大館", is_self=False,
        is_enabled=True, sort_order=1, registered_address="", note=""))
    db.commit()
    QS.ensure_period(db, row.id, TODAY)
    db.commit()
    return row


def _page(properties, next_token=None):
    out = {"search_parameters": {"currency": "TWD"}, "properties": properties}
    if next_token:
        out["serpapi_pagination"] = {"next_page_token": next_token}
    return out


def _prop(name, token, lat, lng, price=2000):
    return {
        "type": "hotel", "name": name, "property_token": token,
        "gps_coordinates": ({"latitude": lat, "longitude": lng}
                            if lat is not None else None),
        "rate_per_night": {"lowest": f"${price}", "extracted_lowest": price},
    }


@pytest.fixture()
def fake_api(monkeypatch):
    """記錄實際送出幾次，並回傳假頁面。"""
    calls: list[dict] = []

    def _fetch(**kwargs):
        calls.append(kwargs)
        n = len(calls)
        if n == 1:
            return _page([
                _prop("承攜行旅 - 台北台大館", "tok_guide", 25.0215859, 121.5268865, 1274),
                _prop("谷墨商旅 GoodMore Hotel", "tok_goodmore", 25.0266799, 121.5307666, 1227),
                _prop("沒有座標旅店", "tok_nogps", None, None, 999),
            ], next_token="PAGE2")
        return _page([
            _prop("福華國際文教會館", "tok_howard", 25.0237161, 121.5342181, 2110),
        ])

    monkeypatch.setattr(S.C, "fetch_location", _fetch)
    monkeypatch.setattr(S.C, "is_configured", lambda: True)
    return calls


# ══════════════════════════════════════════════════════════════════════════
# 1. ⭐ 錢
# ══════════════════════════════════════════════════════════════════════════
def test_quota_is_reserved_before_any_request_is_sent(db, sub, fake_api):
    """預留成功才送請求，而且**預留的量 ＝ 頁數**。"""
    out = S.search_candidates(db, sub.id, pages=2, today=TODAY)
    assert out["request_count"] == 2
    assert len(fake_api) == 2
    assert QS.quota_status(db, sub.id)["used"] == 2


def test_insufficient_quota_sends_nothing_at_all(db, sub, monkeypatch):
    """
    ⭐ 配額不足時**一次請求都不可以送出**。

    送了才發現超額 ＝ 錢已經花掉了，交易回滾也拿不回來。
    """
    sent: list[dict] = []
    monkeypatch.setattr(S.C, "is_configured", lambda: True)
    monkeypatch.setattr(S.C, "fetch_location",
                        lambda **kw: sent.append(kw) or _page([]))

    QS.reserve(db, sub.id, 99, TODAY)      # 只剩 1 次
    db.commit()

    with pytest.raises(S.QuotaUnavailable) as exc:
        S.search_candidates(db, sub.id, pages=3, today=TODAY)
    assert sent == [], "配額不足卻送出了請求 —— 錢已經花掉了"
    assert "配額不足" in str(exc.value)
    assert QS.quota_status(db, sub.id)["used"] == 99, "不可以扣到額度"


def test_unused_pages_are_refunded(db, sub, monkeypatch):
    """要 3 頁但第 1 頁就沒有下一頁 → 只送 1 次，另外 2 次要退還。"""
    monkeypatch.setattr(S.C, "is_configured", lambda: True)
    monkeypatch.setattr(S.C, "fetch_location",
                        lambda **kw: _page([_prop("A 旅店", "tokA", 25.0, 121.5)]))
    out = S.search_candidates(db, sub.id, pages=3, today=TODAY)
    assert out["request_count"] == 1
    assert QS.quota_status(db, sub.id)["used"] == 1, "沒用到的 2 次要退回去"


def test_pages_are_capped(db, sub, fake_api):
    """⚠️ 不設上限的話一次搜尋可以燒掉幾十次配額（P0 實測 356 筆結果）。"""
    S.search_candidates(db, sub.id, pages=999, today=TODAY)
    assert len(fake_api) <= S.MAX_PAGES


def test_every_search_is_written_to_the_fetch_log(db, sub, fake_api):
    """查不到來源的支出，事後沒有人說得清楚。"""
    S.search_candidates(db, sub.id, pages=2, today=TODAY)
    log = db.execute(select(CompsetFetchLog)).scalars().one()
    assert log.request_count == 2
    assert log.quota_before == 0 and log.quota_after == 2
    assert "hotel_search" in (log.params_json or "")
    assert log.status == "success"


def test_api_failure_refunds_and_records_the_error(db, sub, monkeypatch):
    """對方掛掉時：沒送出的要退還，錯誤要進 log，而且要丟得出來。"""
    monkeypatch.setattr(S.C, "is_configured", lambda: True)

    def _boom(**kw):
        raise RuntimeError("HTTP 500")
    monkeypatch.setattr(S.C, "fetch_location", _boom)

    with pytest.raises(S.SearchError):
        S.search_candidates(db, sub.id, pages=2, today=TODAY)
    assert QS.quota_status(db, sub.id)["used"] == 1, "第 1 次真的送出了，只退第 2 次"
    log = db.execute(select(CompsetFetchLog)).scalars().one()
    assert "HTTP 500" in log.error_message


def test_no_api_key_fails_loudly_without_touching_quota(db, sub, monkeypatch):
    """⚠️ 沒設 key 時系統平常是**安靜跳過**，所以這裡一定要明講。"""
    monkeypatch.setattr(S.C, "is_configured", lambda: False)
    with pytest.raises(S.SearchError) as exc:
        S.search_candidates(db, sub.id, today=TODAY)
    assert "SERPAPI_API_KEY" in str(exc.value)
    assert QS.quota_status(db, sub.id)["used"] == 0


# ══════════════════════════════════════════════════════════════════════════
# 2. 候選整理
# ══════════════════════════════════════════════════════════════════════════
def test_already_in_compset_is_flagged_not_hidden(db, sub, fake_api):
    """
    已在組內的家要**標出來**而不是濾掉 —— 濾掉的話使用者會在地圖上
    找不到自己已經加過的家，然後懷疑是不是漏了。
    """
    out = S.search_candidates(db, sub.id, pages=2, today=TODAY)
    by_name = {i["name"]: i for i in out["items"]}
    assert by_name["承攜行旅 - 台北台大館"]["in_compset"] is True
    assert by_name["谷墨商旅 GoodMore Hotel"]["in_compset"] is False


def test_duplicate_across_pages_is_kept_once(db, sub, monkeypatch):
    """同一家在多頁重複出現只留一筆，否則地圖上會疊兩個 marker。"""
    monkeypatch.setattr(S.C, "is_configured", lambda: True)
    calls = []

    def _fetch(**kw):
        calls.append(kw)
        p = _prop("重複旅店", "tok_dup", 25.02, 121.53)
        return _page([p], next_token="X" if len(calls) == 1 else None)
    monkeypatch.setattr(S.C, "fetch_location", _fetch)

    out = S.search_candidates(db, sub.id, pages=2, today=TODAY)
    assert [i["name"] for i in out["items"]].count("重複旅店") == 1


def test_hotels_without_gps_are_listed_but_warned(db, sub, fake_api):
    """沒有座標的家不能消失 —— 它仍然可以被加進競爭組，只是不上地圖。"""
    out = S.search_candidates(db, sub.id, pages=2, today=TODAY)
    names = [i["name"] for i in out["items"]]
    assert "沒有座標旅店" in names
    nogps = next(i for i in out["items"] if i["name"] == "沒有座標旅店")
    assert nogps["latitude"] is None and nogps["distance_km"] is None
    assert any("沒有座標" in w for w in out["warnings"])


def test_sorted_by_distance_with_unknown_last(db, sub, fake_api):
    """
    ⚠️ 沒有距離的排**最後**不是最前 —— 排最前會讓最沒用的資訊浮到上面。
    """
    out = S.search_candidates(db, sub.id, pages=2, today=TODAY)
    dists = [i["distance_km"] for i in out["items"]]
    known = [d for d in dists if d is not None]
    assert known == sorted(known), "有距離的要由近到遠"
    assert dists[-1] is None, "沒有距離的要排最後"


def test_distance_is_measured_from_self_not_from_the_query(db, sub, fake_api):
    """
    ⭐ 基準點是**自己那一家**。

    P0 報告吐槽過 Google 的「N 公里遠」會把北車、西門町的飯店列進公館的結果 ——
    那是因為它的基準點不是我們的飯店。
    """
    out = S.search_candidates(db, sub.id, pages=2, today=TODAY)
    guide = next(i for i in out["items"] if i["name"].startswith("承攜"))
    # 瀚寓(25.0154982,121.5313595) → 承攜(25.0215859,121.5268865) 約 0.77 km
    assert 0.6 < guide["distance_km"] < 0.9
    assert out["self"]["latitude"] == pytest.approx(25.0154982)


def test_haversine_edges():
    assert S.haversine_km(None, 121.5, 25.0, 121.5) is None
    assert S.haversine_km(25.0, 121.5, 25.0, 121.5) == 0.0
    # 台北→高雄 約 300 km
    assert 280 < S.haversine_km(25.0330, 121.5654, 22.6273, 120.3014) < 320


def test_missing_query_is_a_clear_error_not_a_wasted_call(db, sub, monkeypatch):
    """沒有查詢字串時不要送出一個必然無用的請求。"""
    sent = []
    monkeypatch.setattr(S.C, "is_configured", lambda: True)
    monkeypatch.setattr(S.C, "fetch_location",
                        lambda **kw: sent.append(kw) or _page([]))
    sub.location_query = ""
    db.commit()
    with pytest.raises(S.SearchError):
        S.search_candidates(db, sub.id, q="", today=TODAY)
    assert sent == []
    assert QS.quota_status(db, sub.id)["used"] == 0
