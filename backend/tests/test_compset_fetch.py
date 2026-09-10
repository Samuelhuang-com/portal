"""
競品分析 — 抓取服務測試

規格書：docs/SPEC_compset_analysis.md v1.3 §3、§6
服務層：app/services/compset_fetch_service.py

測試策略
────────
不打網路：把 `compset_serpapi_client.fetch_property` / `fetch_location`
換成假的，回傳 P0 真實樣本（`tests/fixtures/compset_serpapi_samples.json`）。

重點測的是**會讓資料悄悄變錯的路徑**：
  · 配額不足時整組跳過，不可以留下半套資料
  · 某一家 API 失敗時，預留的額度要退回來
  · 地點查詢抓不到的家**不寫列**（寫空列會讓 sample_count 是假的）
  · 抓到 0 筆算失敗不算成功
  · 同一天重跑是更新不是新增（唯一鍵含 snapshot_date）

執行：
    cd backend && python -m pytest tests/test_compset_fetch.py -v
"""
from __future__ import annotations

import copy
import importlib
import json
import pkgutil
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models as _models_pkg
from app.core.database import Base

for _m in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app.models.compset_analysis import (CompsetFetchLog,          # noqa: E402
                                         CompsetHotel,
                                         CompsetRateSnapshot,
                                         CompsetSubscriber)
from app.services import compset_fetch_service as F                # noqa: E402
from app.services import compset_quota_service as QS               # noqa: E402
from app.services import compset_serpapi_client as SC              # noqa: E402

SAMPLES = json.loads(
    (Path(__file__).parent / "fixtures" / "compset_serpapi_samples.json")
    .read_text(encoding="utf-8")
)
TODAY = date(2026, 9, 20)


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
        quota_anchor_day=1, quota_period_start="",
        plan_level="A", window_a_days=2, window_b_days=4, window_c_days=6,
        freq_a_days=1, freq_b_days=1, freq_c_days=1,
        location_query="公館 台北",
        param_adults=2, param_nights=1, param_gl="tw", param_hl="zh-tw",
        param_currency="TWD", is_active=True,
        contact_name="", contact_email="", note="",
    )
    db.add(row)
    db.flush()
    names = [("瀚寓夏天 Hanns Summer", "tok-self", True),
             ("承攜行旅-台北台大館", "tok-guide", False),
             ("谷墨商旅 GoodMore Hotel", "tok-goodmore", False)]
    for i, (nm, tok, is_self) in enumerate(names):
        db.add(CompsetHotel(subscriber_id=row.id, display_name=nm,
                            google_property_token=tok, google_query_name=nm,
                            is_self=is_self, is_enabled=True, sort_order=i,
                            hotel_code="", registered_address="", note=""))
    db.commit()
    return row


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(SC, "is_configured", lambda: True)


def fake_property(**kwargs):
    return copy.deepcopy(SAMPLES["tok_ok"])


def fake_location(**kwargs):
    return copy.deepcopy(SAMPLES["loc_p1"])


# ══════════════════════════════════════════════════════════════════════════
# 1. 純函式
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("level,expected", [
    ("A", ("A",)), ("B", ("A", "B")), ("C", ("A", "B", "C")),
    ("", ("A",)), ("Z", ("A",)),
])
def test_tiers_open_is_cumulative(level, expected):
    """買 B 一定含 A —— 只買 B 沒有營運意義（SPEC D2）。"""
    assert F.tiers_open(level) == expected


def test_tier_windows_do_not_overlap(sub):
    a = F.tier_window(sub, "A")
    b = F.tier_window(sub, "B")
    c = F.tier_window(sub, "C")
    assert a == (1, 2) and b == (3, 4) and c == (5, 6)
    assert a[1] + 1 == b[0] and b[1] + 1 == c[0]


def test_tier_path_split():
    """⭐ D10 混合路徑：A 級 token、B/C 級地點查詢。"""
    assert F.tier_path("A") == SC.PATH_TOKEN
    assert F.tier_path("B") == F.tier_path("C") == SC.PATH_LOCATION


@pytest.mark.parametrize("today,freq,expected", [
    (date(2026, 9, 1), 3, True),    # 第 0 天
    (date(2026, 9, 2), 3, False),
    (date(2026, 9, 4), 3, True),    # 第 3 天
    (date(2026, 9, 8), 7, True),    # 第 7 天
    (date(2026, 9, 9), 1, True),    # 每日一定跑
])
def test_is_tier_due_uses_anchor_not_last_success(today, freq, expected):
    """
    ⭐ 用「距錨定日幾天」取餘數，不是「距上次成功幾天」。
    失敗一次不會讓節奏永久漂移。
    """
    assert F.is_tier_due("2026-09-01", today, freq) is expected


@pytest.mark.parametrize("raw,expected", [
    ("承攜行旅 - 台北台大館", "承攜行旅台北台大館"),
    ("承攜行旅-台北台大館", "承攜行旅台北台大館"),
    ("GoodMore Hotel", "goodmorehotel"),
])
def test_name_normalisation(raw, expected):
    """Google 的名稱分隔符與我們建檔的不一定一樣。"""
    assert F._norm(raw) == expected


# ══════════════════════════════════════════════════════════════════════════
# 2. A 級：token 逐家查
# ══════════════════════════════════════════════════════════════════════════
def test_tier_a_writes_one_row_per_hotel_per_day(db, sub, monkeypatch):
    monkeypatch.setattr(SC, "fetch_property", fake_property)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))
    assert results[0].status == F.STATUS_SUCCESS
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert len(rows) == 3 * 2                      # 3 家 × 2 天
    assert {r.fetch_path for r in rows} == {SC.PATH_TOKEN}
    assert {r.tier for r in rows} == {"A"}
    assert {r.is_sold_out for r in rows} == {SC.SOLD_NO}
    assert QS.quota_status(db, sub.id, TODAY)["used"] == 6


def test_tier_a_quota_shortfall_skips_whole_stay_date(db, sub, monkeypatch):
    """
    ⭐ SPEC D15：額度只夠一組時，第二個入住日必須**整個跳過**，
    絕不可以留下「部分競品有價、部分沒有」的半套資料。
    """
    sub.monthly_quota = 4                          # 只夠 1 組（3 次），不夠第 2 組
    db.commit()
    monkeypatch.setattr(SC, "fetch_property", fake_property)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))

    assert results[0].status == F.STATUS_QUOTA
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    stay_dates = {r.stay_date for r in rows}
    assert len(stay_dates) == 1                    # 只有第一天有資料
    assert len(rows) == 3                          # 而且是完整的一組
    assert any("配額不足" in w for w in results[0].warnings)


def test_tier_a_never_writes_a_partial_group(db, sub, monkeypatch):
    """
    ⭐⭐ D15 的核心：額度只夠 2 家、但一組有 3 家時，
    正確行為是**一筆都不寫**；錯誤實作（逐家預留、跑到停為止）會寫 2 筆。

    2 筆的中位數看起來完全正常 —— 這正是這條規則存在的理由。
    （已用變異測試確認：把整組預留改成逐家預留，本測試會失敗。）
    """
    sub.monthly_quota = 2                          # 一組要 3 次
    db.commit()
    monkeypatch.setattr(SC, "fetch_property", fake_property)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))

    assert results[0].status == F.STATUS_QUOTA
    assert db.execute(select(CompsetRateSnapshot)).scalars().all() == []
    assert QS.quota_status(db, sub.id, TODAY)["used"] == 0      # 一次都沒扣


def test_tier_a_refunds_quota_when_api_fails(db, sub, monkeypatch):
    """某一家連線失敗 → 該次沒送出，預留的額度要退回來。"""
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] % 3 == 0:                    # 每組第三家失敗
            raise SC.SerpApiError("HTTP 500")
        return copy.deepcopy(SAMPLES["tok_ok"])

    monkeypatch.setattr(SC, "fetch_property", flaky)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))

    assert results[0].status == F.STATUS_PARTIAL
    assert results[0].request_count == 4           # 6 次預留、2 次失敗
    assert QS.quota_status(db, sub.id, TODAY)["used"] == 4      # 已退還 2
    assert len(results[0].warnings) == 2


def test_tier_a_skips_hotel_without_token(db, sub, monkeypatch):
    """
    沒有 property_token 的家抓不了 —— 記 warning，
    而且**不要為它預留額度**。
    """
    hotel = db.execute(select(CompsetHotel)
                       .where(CompsetHotel.display_name.like("谷墨%"))).scalar_one()
    hotel.google_property_token = ""
    db.commit()
    monkeypatch.setattr(SC, "fetch_property", fake_property)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))

    assert results[0].request_count == 4           # 2 家 × 2 天
    assert QS.quota_status(db, sub.id, TODAY)["used"] == 4
    assert any("缺 google_property_token" in w for w in results[0].warnings)


def test_tier_a_sold_out_recorded(db, sub, monkeypatch):
    """⭐ 賣完要寫 is_sold_out='yes'，不是不寫列、也不是留 NULL。"""
    monkeypatch.setattr(SC, "fetch_property",
                        lambda **kw: copy.deepcopy(SAMPLES["tok_soldout"]))
    F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert rows and all(r.is_sold_out == SC.SOLD_YES for r in rows)
    assert all(r.price_gross is None for r in rows)


def test_rerun_same_day_updates_not_duplicates(db, sub, monkeypatch):
    """同一天重跑是更新（唯一鍵含 snapshot_date），不是新增。"""
    monkeypatch.setattr(SC, "fetch_property", fake_property)
    F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))
    F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert len(rows) == 6                          # 沒有變成 12


# ══════════════════════════════════════════════════════════════════════════
# 3. B／C 級：地點查詢
# ══════════════════════════════════════════════════════════════════════════
def test_tier_bc_matches_by_token_and_name(db, sub, monkeypatch):
    """
    樣本裡「承攜行旅 - 台北台大館」的 token 與我們建檔的不同，
    要靠正規化後的名稱比對接回來。
    """
    sub.plan_level = "B"
    db.commit()
    monkeypatch.setattr(SC, "fetch_location", fake_location)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("B",))

    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    names = {db.get(CompsetHotel, r.compset_hotel_id).display_name for r in rows}
    assert "承攜行旅-台北台大館" in names          # 名稱比對成功
    assert {r.fetch_path for r in rows} == {SC.PATH_LOCATION}
    assert results[0].request_count == 2           # B 級窗口 2 天，每天 1 次


def test_tier_bc_sold_out_always_unknown(db, sub, monkeypatch):
    """⭐ SPEC D13：地點路徑分不出「賣完」與「不在前 N 名」。"""
    sub.plan_level = "B"
    db.commit()
    monkeypatch.setattr(SC, "fetch_location", fake_location)
    F.fetch_subscriber(db, sub, TODAY, only_tiers=("B",))
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert rows and all(r.is_sold_out == SC.SOLD_UNKNOWN for r in rows)


def test_tier_bc_missing_hotel_gets_warning_not_empty_row(db, sub, monkeypatch):
    """
    ⭐ 抓不到的家**不寫列**。寫一筆空的 unknown 會讓 sample_count
    看起來很健康，實際上分母是假的。
    """
    db.add(CompsetHotel(subscriber_id=sub.id, display_name="五月家青年旅舍台大館",
                        google_property_token="tok-may", google_query_name="五月家青年旅舍台大館",
                        is_self=False, is_enabled=True, sort_order=9,
                        hotel_code="", registered_address="", note=""))
    sub.plan_level = "B"
    db.commit()
    monkeypatch.setattr(SC, "fetch_location", fake_location)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("B",))

    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    names = {db.get(CompsetHotel, r.compset_hotel_id).display_name for r in rows}
    assert "五月家青年旅舍台大館" not in names
    assert any("未涵蓋" in w for w in results[0].warnings)
    assert results[0].status == F.STATUS_PARTIAL


def test_tier_bc_without_location_query_is_skipped(db, sub, monkeypatch):
    sub.plan_level = "B"
    sub.location_query = ""
    db.commit()
    monkeypatch.setattr(SC, "fetch_location", fake_location)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("B",))
    assert results[0].status == F.STATUS_SKIPPED
    assert any("location_query" in w for w in results[0].warnings)


# ══════════════════════════════════════════════════════════════════════════
# 4. 狀態與稽核
# ══════════════════════════════════════════════════════════════════════════
def test_zero_rows_is_failure_not_success(db, sub, monkeypatch):
    """⭐ SPEC §6.3：抓到 0 筆視為錯誤（SPEC_ota_reviews R3 的教訓）。"""
    def always_fail(**kwargs):
        raise SC.SerpApiError("HTTP 500")

    monkeypatch.setattr(SC, "fetch_property", always_fail)
    results = F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))
    assert results[0].status == F.STATUS_FAILED
    assert results[0].error_message


def test_fetch_log_records_quota_movement(db, sub, monkeypatch):
    """配額直接對應對外收費，必須查得回去。"""
    monkeypatch.setattr(SC, "fetch_property", fake_property)
    F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))
    log = db.execute(select(CompsetFetchLog)).scalars().one()
    assert log.quota_before == 0 and log.quota_after == 6
    assert log.request_count == 6 and log.row_count == 6
    assert log.stay_date_from == "2026-09-21" and log.stay_date_to == "2026-09-22"
    params = json.loads(log.params_json)
    assert params["gl"] == "tw" and params["freq_days"] == 1
    assert "api_key" not in log.params_json        # ⭐ 金鑰不得入庫


def test_warnings_and_error_message_are_separate(db, sub, monkeypatch):
    """部分失敗歸 warnings，error_message 要留空 —— 否則來源端永遠黃燈。"""
    calls = {"n": 0}

    def flaky(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise SC.SerpApiError("HTTP 429")
        return copy.deepcopy(SAMPLES["tok_ok"])

    monkeypatch.setattr(SC, "fetch_property", flaky)
    F.fetch_subscriber(db, sub, TODAY, only_tiers=("A",))
    log = db.execute(select(CompsetFetchLog)).scalars().one()
    assert log.status == F.STATUS_PARTIAL
    assert log.warnings_json and log.error_message == ""


# ══════════════════════════════════════════════════════════════════════════
# 5. 入口
# ══════════════════════════════════════════════════════════════════════════
def test_fetch_all_due_skips_when_key_missing(db, sub, monkeypatch):
    """未設定金鑰不可以拋例外 —— 整個排程不該因為一個模組沒設定而中斷。"""
    monkeypatch.setattr(SC, "is_configured", lambda: False)
    out = F.fetch_all_due(db, TODAY)
    assert out["total"] == 0 and out["success"] == 0
    assert any("SERPAPI_API_KEY" in w for w in out["warnings"])


def test_fetch_all_due_isolates_failures(db, sub, monkeypatch):
    """一家客戶爆炸不可以害其他客戶當天沒資料。"""
    other = CompsetSubscriber(
        code="CUST-A", name="客戶A", monthly_quota=1000, quota_used=0,
        quota_anchor_day=1, quota_period_start="", plan_level="A",
        window_a_days=1, window_b_days=4, window_c_days=6,
        freq_a_days=1, freq_b_days=1, freq_c_days=1, location_query="x",
        param_adults=2, param_nights=1, param_gl="tw", param_hl="zh-tw",
        param_currency="TWD", is_active=True,
        contact_name="", contact_email="", note="",
    )
    db.add(other)
    db.flush()
    db.add(CompsetHotel(subscriber_id=other.id, display_name="別家飯店",
                        google_property_token="tok-x", google_query_name="別家飯店",
                        is_self=True, is_enabled=True, sort_order=0,
                        hotel_code="", registered_address="", note=""))
    db.commit()

    def by_sub(**kwargs):
        if kwargs.get("property_token") == "tok-x":
            raise RuntimeError("boom")
        return copy.deepcopy(SAMPLES["tok_ok"])

    monkeypatch.setattr(SC, "fetch_property", by_sub)
    out = F.fetch_all_due(db, TODAY)
    assert out["total"] == 2
    assert out["success"] == 1                     # INTERNAL 仍然成功
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert {r.subscriber_id for r in rows} == {sub.id}
