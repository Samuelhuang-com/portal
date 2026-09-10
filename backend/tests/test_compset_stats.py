"""
競品分析 — 統計與指標測試

規格書：docs/SPEC_compset_analysis.md §7
服務層：app/services/compset_stats_service.py

重點測「會讓指標悄悄變錯」的路徑：
  · 同一格有 serpapi ＋ csv 兩列時，**只能算一次**（算兩次中位數直接歪）
  · 中位數要排除自己與賣完；**滿房未知有價格時仍要算**（否則 B/C 級全空）
  · 稅前與含稅兩種指數都要算
  · 排名用含稅（稅前不保證存在）
  · 沒有 is_self 時指數回 None，**不可以回 0**
  · rate_daily 是快取，隨時可從 snapshots 重算

執行：
    cd backend && python -m pytest tests/test_compset_stats.py -v
"""
from __future__ import annotations

import importlib
import pkgutil
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models as _models_pkg
from app.core.database import Base

for _m in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"app.models.{_m.name}")

from app.models.compset_analysis import (CompsetHotel,             # noqa: E402
                                         CompsetRateDaily,
                                         CompsetRateSnapshot,
                                         CompsetSubscriber)
from app.services import compset_stats_service as S                # noqa: E402

SNAP = "2026-09-09"
STAY = "2026-09-20"


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
    # 用 P0 2026-09-20 的真實價格（稅前）：承攜 1103、谷墨 1169、
    # 自己 1645、福華 2110、捷絲旅 2720 → 競品中位數 1639.5、指數 1.003
    for i, (name, is_self) in enumerate([
            ("瀚寓夏天", True), ("承攜行旅", False), ("谷墨商旅", False),
            ("福華國際文教會館", False), ("捷絲旅臺大尊賢館", False)]):
        db.add(CompsetHotel(subscriber_id=row.id, display_name=name,
                            hotel_code=f"H{i}", google_property_token=f"tok{i}",
                            google_query_name=name, is_self=is_self,
                            is_enabled=True, sort_order=i,
                            registered_address="", note=""))
    db.commit()
    return row


def hid(db, name: str) -> int:
    return db.execute(select(CompsetHotel.id)
                      .where(CompsetHotel.display_name == name)).scalar_one()


def snap(db, sub, name, *, gross=None, pretax=None, sold="no",
         source="serpapi", stay=STAY, snapshot=SNAP, path="token"):
    row = CompsetRateSnapshot(
        subscriber_id=sub.id, compset_hotel_id=hid(db, name),
        snapshot_date=snapshot, stay_date=stay, tier="A", fetch_path=path,
        source=source, price_gross=gross, price_pretax=pretax,
        currency="TWD", tax_included="yes" if pretax else "unknown",
        ota_name="", is_official=False, free_cancellation=False,
        room_type_raw="", is_sold_out=sold,
    )
    db.add(row)
    return row


def seed_real_prices(db, sub):
    """P0 2026-09-20 的真實資料。"""
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103)
    snap(db, sub, "谷墨商旅", gross=1227, pretax=1169)
    snap(db, sub, "福華國際文教會館", gross=2444, pretax=2110)
    snap(db, sub, "捷絲旅臺大尊賢館", gross=3142, pretax=2720)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════
# 1. 來源優先序（D16）
# ══════════════════════════════════════════════════════════════════════════
def test_pick_by_source_prefers_serpapi(db, sub):
    """
    ⭐⭐ 同一格有兩列時**只能算一次**。
    兩列都算 ＝ 同一家被算兩次，中位數直接歪掉，而且看起來完全正常。
    """
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, source="serpapi")
    snap(db, sub, "承攜行旅", gross=9999, pretax=9999, source="csv")
    db.commit()
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    picked = S.pick_by_source(rows)
    assert len(picked) == 1
    assert float(list(picked.values())[0].price_gross) == 1274.0


def test_csv_used_when_serpapi_absent(db, sub):
    """CSV 的用途是補上抓不到的格子 —— 沒有 serpapi 時要採用。"""
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, source="csv")
    db.commit()
    picked = S.pick_by_source(db.execute(select(CompsetRateSnapshot)).scalars().all())
    assert float(list(picked.values())[0].price_gross) == 1274.0


# ══════════════════════════════════════════════════════════════════════════
# 2. 指數（用 P0 真實數字）
# ══════════════════════════════════════════════════════════════════════════
def test_index_matches_hand_computed_p0_numbers(db, sub):
    """
    P0 實測（2026-09-20，稅前）：
      承攜 1103、谷墨 1169、**自己 1645**、福華 2110、捷絲旅 2720
      競品中位數 = (1169 + 2110) / 2 = 1639.5 → 指數 = 1645 / 1639.5 = 1.0034
    """
    seed_real_prices(db, sub)
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    st = S.compute_stat(rows, hid(db, "瀚寓夏天"))
    assert st.median_pretax == 1639.5
    assert st.index_pretax == pytest.approx(1.0034, abs=0.0001)
    assert st.self_pretax == 1645.0
    assert st.sample_count == 4                 # 四家競品，不含自己


def test_both_bases_are_computed(db, sub):
    """⭐ D11：稅前與含稅都要算，單一口徑會誤導。"""
    seed_real_prices(db, sub)
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.median_gross == 1859.0            # (1274 + 2444) / 2
    assert st.index_gross == pytest.approx(1900 / 1859.0, abs=0.0001)
    assert st.index_pretax != st.index_gross    # 兩個口徑本來就不同


def test_median_excludes_self(db, sub):
    """分子分母不可以是同一家。"""
    seed_real_prices(db, sub)
    rows = db.execute(select(CompsetRateSnapshot)).scalars().all()
    with_self = sorted(float(r.price_pretax) for r in rows)
    st = S.compute_stat(rows, hid(db, "瀚寓夏天"))
    # 五家的中位數是 1645（自己），排除自己之後才是 1639.5
    assert with_self[2] == 1645.0
    assert st.median_pretax == 1639.5


def test_sold_out_excluded_from_median_but_counted(db, sub):
    """賣完 → 不進中位數（沒有價就沒有價），但 `sold_out_count` 要算。"""
    seed_real_prices(db, sub)
    row = db.execute(select(CompsetRateSnapshot)
                     .where(CompsetRateSnapshot.compset_hotel_id
                            == hid(db, "捷絲旅臺大尊賢館"))).scalar_one()
    row.is_sold_out = "yes"
    row.price_gross = row.price_pretax = None
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.sold_out_count == 1
    assert st.sample_count == 3
    assert st.median_pretax == 1169.0           # 1103 / 1169 / 2110 的中位數


def test_unknown_with_price_still_counts_but_is_flagged(db, sub):
    """
    ⭐⭐ 2026-09-09 修正：`unknown` **有價格時仍然算進中位數**。

    一度寫成「unknown 也排除」，但 B／C 級（地點查詢）每一列都是 unknown ——
    那條規則會讓三分之二的產品完全算不出指數，而畫面上只會顯示「沒有資料」，
    看不出是規則寫錯。一家在地點查詢裡帶著價格出現，就代表它那天有房。
    """
    seed_real_prices(db, sub)
    row = db.execute(select(CompsetRateSnapshot)
                     .where(CompsetRateSnapshot.compset_hotel_id
                            == hid(db, "福華國際文教會館"))).scalar_one()
    row.is_sold_out = "unknown"
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.unknown_count == 1          # 仍然計數，畫面要標示
    assert st.sample_count == 4           # 但沒有被排除
    assert st.max_pretax == 2720.0
    assert st.median_pretax == 1639.5     # 指數不受影響


def test_bc_tier_all_unknown_still_produces_index(db, sub):
    """
    ⭐ 上面那條修正的實際後果：B／C 級（整批 unknown）也要算得出指數，
    否則三分之二的產品是空的。
    """
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645, path="location", sold="unknown")
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, path="location", sold="unknown")
    snap(db, sub, "谷墨商旅", gross=1227, pretax=1169, path="location", sold="unknown")
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.median_pretax == 1136.0     # (1103 + 1169) / 2
    assert st.index_pretax is not None
    assert st.unknown_count == 2


# ══════════════════════════════════════════════════════════════════════════
# 3. 排名（規則 4：用含稅）
# ══════════════════════════════════════════════════════════════════════════
def test_rank_uses_gross_and_includes_self(db, sub):
    """含稅排序：1227 谷墨 / 1274 承攜 / **1900 自己** / 2444 福華 / 3142 捷絲旅。"""
    seed_real_prices(db, sub)
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert (st.self_rank, st.rank_total) == (3, 5)


def test_rank_still_works_without_pretax(db, sub):
    """
    ⭐ 規則 4 的理由：`price_pretax` 不保證存在（地點查詢第 2 頁全部沒有）。
    用稅前排名會讓大半 B／C 級資料排不出來。
    """
    snap(db, sub, "瀚寓夏天", gross=1900, path="location", sold="unknown")
    snap(db, sub, "承攜行旅", gross=1274, path="location", sold="unknown")
    snap(db, sub, "谷墨商旅", gross=1227, path="location", sold="unknown")
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.self_rank == 3 and st.rank_total == 3
    assert st.median_gross == 1250.5      # (1227 + 1274) / 2
    assert st.median_pretax is None       # 稅前全缺，但含稅口徑照樣算得出來
    assert st.sample_count == 2           # 退回含稅口徑的家數
    assert st.unknown_count == 2


# ══════════════════════════════════════════════════════════════════════════
# 4. 樣本充足度與缺 is_self
# ══════════════════════════════════════════════════════════════════════════
def test_low_sample_flag(db, sub):
    """樣本不足要跟數字一起顯示，不能只回一個看起來很正常的指數。"""
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103)
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.sample_count == 1 and st.is_low_sample is True
    assert st.index_pretax is not None          # 仍然算，但要標灰


def test_sold_out_hotel_ids_records_who_not_just_how_many(db, sub):
    """
    ⭐ 「2 家滿房」不夠用 —— 使用者要知道**是哪兩家**才能決定要不要跟著漲。

    ⚠️ 自己滿房**不算進去**（這一欄的語意是「競品」滿房）。
    """
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, sold="yes")
    snap(db, sub, "谷墨商旅", gross=1227, pretax=1169, sold="yes")
    snap(db, sub, "福華國際文教會館", gross=2110, pretax=1827)
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.sold_out_count == 2
    assert st.sold_out_hotel_ids == sorted([hid(db, "承攜行旅"), hid(db, "谷墨商旅")])
    # 排序穩定，畫面與測試才不會每次順序不同
    assert st.sold_out_hotel_ids == sorted(st.sold_out_hotel_ids)


def test_self_sold_out_is_not_listed_as_a_competitor(db, sub):
    """自己滿房不進 `sold_out_hotel_ids` —— 那一欄問的是「競品賣完了沒」。"""
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645, sold="yes")
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, sold="yes")
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.sold_out_hotel_ids == [hid(db, "承攜行旅")]
    assert hid(db, "瀚寓夏天") not in st.sold_out_hotel_ids


def test_matrix_and_dashboard_report_last_updated_time(db, sub):
    """
    ⭐ `snapshot_date` 只有日期，答不出「今天早上到底跑了沒、幾點跑的」——
       而那是使用者拿畫面對 Google 對不上時第一個要問的事。

    ⚠️ 取 **max** 不是 min：同一天可能排程跑完又被手動觸發，
       使用者要看的是「最後更新」。
    """
    from datetime import datetime

    r1 = snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)
    r2 = snap(db, sub, "承攜行旅", gross=1274, pretax=1103)
    db.flush()
    r1.created_at = datetime(2026, 9, 10, 4, 10, 33)
    r2.created_at = datetime(2026, 9, 10, 9, 25, 8)     # 手動補跑，比較晚
    db.commit()

    out = S.matrix(db, sub.id, stay_from=STAY, stay_to=STAY)
    assert out["fetched_at"] == "2026-09-10 09:25:08", "要取最後一次，不是第一次"
    assert out["snapshot_date"] == SNAP

    # 沒有資料時仍要有這個 key（前端會直接讀）
    empty = S.matrix(db, sub.id, stay_from="2030-01-01", stay_to="2030-01-02")
    assert empty["fetched_at"] is None
    assert S.dashboard(db, sub.id, today=date(2030, 1, 1))["fetched_at"] is None


def test_fetched_at_survives_rows_without_created_at(db, sub):
    """`created_at` 可以是 NULL（CSV 匯入的舊列）—— 不可以整個炸掉。"""
    from datetime import datetime

    r1 = snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)
    r2 = snap(db, sub, "承攜行旅", gross=1274, pretax=1103)
    db.flush()
    r1.created_at = None
    r2.created_at = datetime(2026, 9, 10, 4, 10, 33)
    db.commit()
    out = S.matrix(db, sub.id, stay_from=STAY, stay_to=STAY)
    assert out["fetched_at"] == "2026-09-10 04:10:33"

    # 全部都沒有時間 → None，不是空字串也不是崩潰
    db.query(CompsetRateSnapshot).update({"created_at": None})
    db.commit()
    assert S.matrix(db, sub.id, stay_from=STAY,
                    stay_to=STAY)["fetched_at"] is None


def test_dashboard_returns_hotel_lookup_for_sold_out_names(db, sub):
    """
    `sold_out_hotel_ids` 只有 id，前端要顯示名字就必須有對照表。
    ⚠️ **沒有資料時也要回 `hotels`**（空陣列）—— 少了這個 key，
       前端的 `.find()` 會直接炸在一個「本來就沒資料」的正常狀態上。
    """
    empty = S.dashboard(db, sub.id)
    assert empty["hotels"] == [], "無資料時仍必須有 hotels 這個 key"

    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645,
         stay=(date.today() + timedelta(days=1)).isoformat())
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, sold="yes",
         stay=(date.today() + timedelta(days=1)).isoformat())
    db.commit()
    out = S.dashboard(db, sub.id)
    ids = {h["id"] for h in out["hotels"]}
    assert ids >= set(out["next_7d"][0]["sold_out_hotel_ids"]), \
        "滿房的 id 必須都查得到名字"
    assert out["hotels"][0]["is_self"] is True, "自己排最前面"
    assert all("short_name" in h for h in out["hotels"])


def test_short_label_falls_back_to_display_name(db, sub):
    """
    ⚠️ `short_name` **留空是允許的**（使用者不一定會填）。
       顯示端一律走 `short_label`，不可以直接讀 `short_name` ——
       否則沒填簡稱的飯店在畫面上會變成空白標籤。
    """
    h = db.execute(select(CompsetHotel)
                   .where(CompsetHotel.display_name == "谷墨商旅")).scalar_one()
    assert h.short_name == ""              # 這個 fixture 沒有設簡稱
    assert h.short_label == "谷墨商旅"      # 退回全名

    h.short_name = "谷墨"
    db.flush()
    assert h.short_label == "谷墨"

    h.short_name = "   "                   # 只有空白也算沒填
    db.flush()
    assert h.short_label == "谷墨商旅"


def test_sample_count_is_reported_per_basis(db, sub):
    """
    ⭐ 兩個口徑的樣本數**不一樣**，畫面切換口徑時必須跟著換。

    情境（地點查詢的真實樣貌）：4 家有含稅價，其中只有 1 家有稅前價。
      · 稅前指數 ＝ 1 家算出來的 → 樣本不足，該標警告
      · 含稅指數 ＝ 3 家算出來的 → 樣本充足，**不該**標警告

    只回一個 `sample_count` 的話，切到含稅口徑會把一個沒問題的指數
    標成「僅供參考」——等於叫使用者不要相信一個對的數字。
    """
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)          # 自己
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103)          # 兩個口徑都有
    snap(db, sub, "谷墨商旅", gross=1227)                        # 只有含稅
    snap(db, sub, "福華國際文教會館", gross=2110)                # 只有含稅
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))

    assert st.sample_count_pretax == 1
    assert st.sample_count_gross == 3
    # 舊欄位語意不變（稅前優先），DB 快取與 is_low_sample 都還在用
    assert st.sample_count == 1
    assert st.is_low_sample is True

    d = st.as_dict()
    assert d["sample_count_pretax"] == 1 and d["sample_count_gross"] == 3


def test_sample_count_gross_falls_back_into_legacy_field_when_no_pretax(db, sub):
    """稅前全缺時 `sample_count` 退回含稅家數（既有行為），但兩個新欄位仍各自正確。"""
    snap(db, sub, "瀚寓夏天", gross=1900, path="location", sold="unknown")
    snap(db, sub, "承攜行旅", gross=1274, path="location", sold="unknown")
    snap(db, sub, "谷墨商旅", gross=1227, path="location", sold="unknown")
    db.commit()
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        hid(db, "瀚寓夏天"))
    assert st.sample_count_pretax == 0
    assert st.sample_count_gross == 2
    assert st.sample_count == 2


def test_recompute_daily_ignores_the_non_column_sample_fields(db, sub):
    """
    `sample_count_pretax/_gross` **不是** `compset_rate_daily` 的欄位。
    `recompute_daily()` 用白名單逐欄寫入，所以新增欄位不會意外污染快取表 ——
    這條測試是在釘住那個白名單，避免日後有人改成 `for k, v in as_dict()`。
    """
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103)
    snap(db, sub, "谷墨商旅", gross=1227)
    db.commit()
    S.recompute_daily(db, sub.id)
    db.commit()
    row = db.execute(select(CompsetRateDaily)).scalar_one()
    assert not hasattr(row, "sample_count_pretax")
    assert not hasattr(row, "sample_count_gross")
    assert row.sample_count == 1        # 稅前口徑


def test_dashboard_uses_taiwan_date_not_server_date(db, sub, monkeypatch):
    """
    ⭐ Dashboard 的 7 天窗格用**台灣時間**。

    正式機若跑在 UTC，台灣早上 8 點的 `date.today()` 還停在昨天，
    整個窗格會位移一天 —— 「明天」那張卡會顯示今天，而且畫面上看不出來。
    """
    called = {"n": 0}

    class _FakeNow:
        @staticmethod
        def date():
            called["n"] += 1
            return date(2026, 9, 9)

    monkeypatch.setattr(S, "twnow", lambda: _FakeNow())
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645, stay="2026-09-10")
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, stay="2026-09-10")
    db.commit()
    out = S.dashboard(db, sub.id)
    assert called["n"] >= 1, "dashboard 必須走 twnow()，不可以用 date.today()"
    assert out["today"] is not None and out["today"]["stay_date"] == "2026-09-10"


def test_no_self_returns_none_not_zero(db, sub):
    """
    ⭐ 沒有 is_self 時指數必須是 None。
    回 0 會被畫面當成「跟市場一樣便宜」，那是完全錯誤的訊息。
    """
    seed_real_prices(db, sub)
    st = S.compute_stat(db.execute(select(CompsetRateSnapshot)).scalars().all(),
                        None)
    assert st.index_pretax is None and st.index_gross is None
    assert st.self_rank is None
    assert st.median_pretax is not None         # 中位數仍然算得出來
    assert any("is_self" in w for w in st.warnings)


# ══════════════════════════════════════════════════════════════════════════
# 5. 快取重算
# ══════════════════════════════════════════════════════════════════════════
def test_recompute_daily_is_idempotent(db, sub):
    seed_real_prices(db, sub)
    assert S.recompute_daily(db, sub.id) == 1
    assert S.recompute_daily(db, sub.id) == 1
    db.commit()
    rows = db.execute(select(CompsetRateDaily)).scalars().all()
    assert len(rows) == 1
    assert float(rows[0].median_pretax) == 1639.5
    assert float(rows[0].index_pretax) == pytest.approx(1.0034, abs=0.0001)
    assert rows[0].self_rank == 3 and rows[0].rank_total == 5


def test_recompute_reflects_corrected_snapshots(db, sub):
    """快取不是來源：改了 snapshots 再重算，數字要跟著變。"""
    seed_real_prices(db, sub)
    S.recompute_daily(db, sub.id)
    db.commit()
    row = db.execute(select(CompsetRateSnapshot)
                     .where(CompsetRateSnapshot.compset_hotel_id
                            == hid(db, "瀚寓夏天"))).scalar_one()
    row.price_pretax = 3000
    db.commit()
    S.recompute_daily(db, sub.id)
    db.commit()
    daily = db.execute(select(CompsetRateDaily)).scalars().one()
    assert float(daily.index_pretax) == pytest.approx(3000 / 1639.5, abs=0.0001)


# ══════════════════════════════════════════════════════════════════════════
# 6. 查詢
# ══════════════════════════════════════════════════════════════════════════
def test_matrix_puts_self_first(db, sub):
    seed_real_prices(db, sub)
    m = S.matrix(db, sub.id, stay_from=STAY, stay_to=STAY)
    assert m["snapshot_date"] == SNAP
    assert m["hotels"][0]["is_self"] is True
    assert m["stay_dates"] == [STAY]
    cell = m["cells"][f"{STAY}|{hid(db, '承攜行旅')}"]
    assert cell["price_gross"] == 1274.0 and cell["source"] == "serpapi"
    assert m["daily"][STAY]["median_pretax"] == 1639.5


def test_matrix_empty_when_no_data(db, sub):
    m = S.matrix(db, sub.id, stay_from=STAY, stay_to=STAY)
    assert m["snapshot_date"] is None and m["warnings"]


def test_trend_shows_price_moving_over_snapshots(db, sub):
    """⭐ 這是 snapshot_date 進唯一鍵的唯一目的：看競品什麼時候降價。"""
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645, snapshot="2026-09-01")
    snap(db, sub, "承攜行旅", gross=1500, pretax=1300, snapshot="2026-09-01")
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645, snapshot="2026-09-09")
    snap(db, sub, "承攜行旅", gross=1274, pretax=1103, snapshot="2026-09-09")
    db.commit()
    t = S.trend(db, sub.id, stay_date=STAY)
    assert t["snapshot_dates"] == ["2026-09-01", "2026-09-09"]
    guide = t["series"][hid(db, "承攜行旅")]
    assert [p["price_gross"] for p in guide] == [1500.0, 1274.0]   # 降價看得出來


def test_dashboard_reports_low_sample_and_sold_out(db, sub):
    today = date(2026, 9, 19)
    snap(db, sub, "瀚寓夏天", gross=1900, pretax=1645)
    snap(db, sub, "承攜行旅", gross=None, pretax=None, sold="yes")
    db.commit()
    d = S.dashboard(db, sub.id, today)
    assert d["snapshot_date"] == SNAP
    assert d["today"]["sold_out_count"] == 1
    assert d["low_sample_days"] == 1
