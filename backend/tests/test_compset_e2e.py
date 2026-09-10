"""
競品分析 — 端對端整合測試（種子 → 抓取 → 統計 → 匯入）

這支不測單一函式，測的是**整條路徑接得起來**：
    seed（訂閱＋競爭組）
      → fetch_all_due（配額預留 → 抓取 → 寫 snapshots ＋ fetch_logs）
        → recompute_daily（指數、排名、樣本）
          → matrix / trend / dashboard
            → CSV 補上抓不到的格子

為什麼需要這一支
────────────────
四支單元測試各自都過，不代表接起來會動 —— 常見的斷點是
「A 的輸出欄位名跟 B 讀的不一樣」「commit 時機錯了資料沒落地」。
這支用假的 SerpApi 回應（P0 真實樣本）把整條跑一遍。

執行：
    cd backend && python -m pytest tests/test_compset_e2e.py -v
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

from app.models.compset_analysis import (CompsetFetchLog,           # noqa: E402
                                         CompsetHotel,
                                         CompsetRateDaily,
                                         CompsetRateSnapshot,
                                         CompsetSubscriber)
from app.services import compset_fetch_service as F                 # noqa: E402
from app.services import compset_import_service as I                # noqa: E402
from app.services import compset_quota_service as QS                # noqa: E402
from app.services import compset_serpapi_client as SC               # noqa: E402
from app.services import compset_stats_service as S                 # noqa: E402

SAMPLES = json.loads(
    (Path(__file__).parent / "fixtures" / "compset_serpapi_samples.json")
    .read_text(encoding="utf-8")
)
TODAY = date(2026, 9, 9)

# 六家的假價格（含稅／稅前），用 P0 的量級
PRICES = {
    "tok-self":     (1900, 1645),
    "tok-guide":    (1274, 1103),
    "tok-justsleep": (3142, 2720),
    "tok-howard":   (2444, 2110),
    "tok-goodmore": (1227, 1169),
}


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
def seeded(db):
    """比照 `scripts/compset_seed_internal.py` 的定案內容（COMPSET_CANDIDATES §8）。"""
    sub = CompsetSubscriber(
        code="INTERNAL", name="瀚寓夏天（內部）", plan_level="A",
        location_query="公館 台北", monthly_quota=3500, quota_used=0,
        quota_anchor_day=1, quota_period_start="",
        window_a_days=3, window_b_days=6, window_c_days=9,     # 縮小以加快測試
        freq_a_days=1, freq_b_days=1, freq_c_days=1,
        param_adults=2, param_nights=1, param_gl="tw", param_hl="zh-tw",
        param_currency="TWD", is_active=True,
        contact_name="", contact_email="", note="",
    )
    db.add(sub)
    db.flush()
    rows = [
        ("瀚寓夏天", "HANNS_SUMMER", True, "tok-self", 69),
        ("承攜行旅-台北台大館", "GUIDE_NTU", False, "tok-guide", 35),
        ("捷絲旅臺大尊賢館", "JUSTSLEEP_NTU", False, "tok-justsleep", 72),
        ("福華國際文教會館", "HOWARD_CSIH", False, "tok-howard", None),
        ("谷墨商旅師大館", "GOODMORE_SHIDA", False, "tok-goodmore", 92),
        # ⚠️ 五月家目前沒有 token（P0 §2），A 級會跳過並記 warning
        ("五月家青年旅舍台大館", "MAYROOMS_NTU", False, "", None),
    ]
    for i, (name, code, is_self, token, rooms) in enumerate(rows):
        db.add(CompsetHotel(subscriber_id=sub.id, display_name=name,
                            hotel_code=code, is_self=is_self,
                            google_property_token=token, google_query_name=name,
                            room_count=rooms, is_enabled=True, sort_order=i,
                            registered_address="", note=""))
    db.commit()
    return sub


@pytest.fixture(autouse=True)
def _fake_api(monkeypatch):
    monkeypatch.setattr(SC, "is_configured", lambda: True)

    def fake_property(*, property_token, **kwargs):
        payload = copy.deepcopy(SAMPLES["tok_ok"])
        gross, pretax = PRICES[property_token]
        for key in ("rate_per_night", "total_rate"):
            payload[key]["extracted_lowest"] = gross
            payload[key]["extracted_before_taxes_fees"] = pretax
        payload["prices"] = [p for p in payload["prices"] if p["source"] == "Hanns Summer"]
        payload["prices"][0]["rate_per_night"]["extracted_lowest"] = gross
        payload["prices"][0]["rate_per_night"]["extracted_before_taxes_fees"] = pretax
        return payload

    monkeypatch.setattr(SC, "fetch_property", fake_property)


# ══════════════════════════════════════════════════════════════════════════
def test_full_pipeline(db, seeded):
    """種子 → 抓取 → 統計 → 查詢，一路走完。"""
    out = F.fetch_all_due(db, TODAY)

    # ── 抓取 ─────────────────────────────────────────────────────
    assert out["total"] == 1 and out["success"] == 1
    assert out["fetched"] == 5 * 3          # 5 家有 token × 3 天
    assert out["upserted"] == 15
    assert any("五月家" in w and "google_property_token" in w
               for w in out["warnings"])    # 缺 token 的家有記 warning

    snaps = db.execute(select(CompsetRateSnapshot)).scalars().all()
    assert len(snaps) == 15
    assert {s.snapshot_date for s in snaps} == {"2026-09-09"}
    assert {s.stay_date for s in snaps} == {"2026-09-10", "2026-09-11", "2026-09-12"}

    # ── 配額：只為有 token 的家預留 ───────────────────────────────
    assert QS.quota_status(db, seeded.id, TODAY)["used"] == 15

    # ── 稽核 ─────────────────────────────────────────────────────
    log = db.execute(select(CompsetFetchLog)).scalars().one()
    assert log.status == F.STATUS_PARTIAL   # 有 warning（缺 token）
    assert log.error_message == ""          # 但不是錯誤
    assert (log.quota_before, log.quota_after) == (0, 15)

    # ── 統計 ─────────────────────────────────────────────────────
    assert S.recompute_daily(db, seeded.id) == 3
    db.commit()
    daily = db.execute(select(CompsetRateDaily)
                       .order_by(CompsetRateDaily.stay_date)).scalars().all()
    assert len(daily) == 3
    d0 = daily[0]
    # 競品稅前 1103 / 1169 / 2110 / 2720 → 中位數 (1169+2110)/2 = 1639.5
    assert float(d0.median_pretax) == 1639.5
    assert float(d0.index_pretax) == pytest.approx(1645 / 1639.5, abs=0.0001)
    assert d0.sample_count == 4             # 五月家沒抓到 → 不在分母裡
    assert (d0.self_rank, d0.rank_total) == (3, 5)

    # ── 查詢 ─────────────────────────────────────────────────────
    m = S.matrix(db, seeded.id, stay_from="2026-09-10", stay_to="2026-09-12")
    assert m["hotels"][0]["is_self"] is True
    assert len(m["stay_dates"]) == 3
    assert len(m["cells"]) == 15

    dash = S.dashboard(db, seeded.id, TODAY)
    assert dash["snapshot_date"] == "2026-09-09"
    assert dash["today"]["index_pretax"] is not None
    assert dash["low_sample_days"] == 0


def test_csv_fills_the_gap_that_api_could_not(db, seeded):
    """
    ⭐ CSV 的實際用途：補上抓不到的格子（五月家沒有 token）。
    補完之後 `sample_count` 要從 4 變 5。
    """
    F.fetch_all_due(db, TODAY)
    S.recompute_daily(db, seeded.id)
    db.commit()
    before = db.execute(select(CompsetRateDaily)
                        .where(CompsetRateDaily.stay_date == "2026-09-10")).scalar_one()
    assert before.sample_count == 4

    csv = ("快照日期,入住日期,飯店,含稅價,稅前價,幣別,含稅,是否滿房,通路,房型,入住人數\n"
           "2026-09-09,2026-09-10,五月家青年旅舍台大館,1682,1456,TWD,是,否,官網,,2\n")
    res = I.import_rates(db, subscriber_id=seeded.id, today=TODAY,
                         content=csv.encode("utf-8-sig"))
    assert res.inserted == 1 and res.errors == []

    S.recompute_daily(db, seeded.id, stay_from="2026-09-10", stay_to="2026-09-10")
    db.commit()
    after = db.execute(select(CompsetRateDaily)
                       .where(CompsetRateDaily.stay_date == "2026-09-10")).scalar_one()
    assert after.sample_count == 5
    # 競品稅前 1103 / 1169 / 1456 / 2110 / 2720 → 中位數 1456
    assert float(after.median_pretax) == 1456.0


def test_quota_exhaustion_leaves_no_partial_day(db, seeded):
    """
    ⭐ D15 在整條路徑上的表現：額度只夠兩天，第三天必須完全沒有資料，
    而不是「有三家、缺兩家」的半套。
    """
    seeded.monthly_quota = 12               # 一組 5 次 → 只夠 2 天
    db.commit()
    out = F.fetch_all_due(db, TODAY)

    snaps = db.execute(select(CompsetRateSnapshot)).scalars().all()
    by_stay: dict[str, int] = {}
    for s in snaps:
        by_stay[s.stay_date] = by_stay.get(s.stay_date, 0) + 1
    assert len(by_stay) == 2                       # 只有兩天
    assert set(by_stay.values()) == {5}            # 每天都是完整的一組
    assert any("配額不足" in w for w in out["warnings"])


def test_rerunning_the_same_day_does_not_duplicate(db, seeded):
    """排程重跑／手動觸發是正常操作，不可以長出第二批。"""
    F.fetch_all_due(db, TODAY)
    F.fetch_all_due(db, TODAY)
    assert len(db.execute(select(CompsetRateSnapshot)).scalars().all()) == 15
    S.recompute_daily(db, seeded.id)
    db.commit()
    assert len(db.execute(select(CompsetRateDaily)).scalars().all()) == 3


def test_sold_out_flows_all_the_way_to_the_index(db, seeded, monkeypatch):
    """
    ⭐ 滿房訊號要一路傳到指標：捷絲旅賣完 → 不進中位數、但 `sold_out_count` 要有。
    """
    def fake_property(*, property_token, **kwargs):
        if property_token == "tok-justsleep":
            return copy.deepcopy(SAMPLES["tok_soldout"])
        payload = copy.deepcopy(SAMPLES["tok_ok"])
        gross, pretax = PRICES[property_token]
        for key in ("rate_per_night", "total_rate"):
            payload[key]["extracted_lowest"] = gross
            payload[key]["extracted_before_taxes_fees"] = pretax
        payload["prices"] = []
        return payload

    monkeypatch.setattr(SC, "fetch_property", fake_property)
    F.fetch_all_due(db, TODAY)
    S.recompute_daily(db, seeded.id)
    db.commit()

    d = db.execute(select(CompsetRateDaily)
                   .where(CompsetRateDaily.stay_date == "2026-09-10")).scalar_one()
    assert d.sold_out_count == 1
    assert d.sample_count == 3                     # 四家競品少掉賣完的那家
    assert float(d.median_pretax) == 1169.0        # 1103 / 1169 / 2110
