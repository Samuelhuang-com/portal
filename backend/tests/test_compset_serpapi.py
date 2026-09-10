"""
競品分析 — SerpApi 客戶端解析的離線測試

用 **P0 探測抓到的真實回應**（`tests/fixtures/compset_serpapi_samples.json`）驗證，
不打網路。

為什麼用真實樣本而不是手刻假資料
────────────────────────────────
本模組六條解析規則裡有四條，是**看了真實回應才發現的**：
`ads` 與 `properties` 兩套價格、第 2 頁沒有稅前欄位、
`vacation rental` 混在結果裡、賣完時 `typical_price_range` 會變成美元。
手刻的假資料只會反映我們「以為」的格式，測不出這些。

⚠️ 連線層（`fetch_*`）沒有測試 —— 本 session 的兩個環境都被網路政策擋掉
   serpapi.com。實際連線驗證要在 Portal 正式機做（COMPSET_TODO 1.10）。

執行：
    cd backend && python -m pytest tests/test_compset_serpapi.py -v
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.services import compset_serpapi_client as C

SAMPLES = json.loads(
    (Path(__file__).parent / "fixtures" / "compset_serpapi_samples.json")
    .read_text(encoding="utf-8")
)


def sample(key: str) -> dict:
    """每次都給一份深拷貝，避免某個測試改壞了影響其他測試。"""
    return copy.deepcopy(SAMPLES[key])


# ══════════════════════════════════════════════════════════════════════════
# 1. 參數
# ══════════════════════════════════════════════════════════════════════════
def test_build_params_never_contains_api_key():
    """⭐ 這份 dict 會被寫進 fetch_logs.params_json，絕不可以帶金鑰。"""
    p = C.build_params(q="公館 台北", check_in_date="2026-09-20")
    assert "api_key" not in p
    assert p["check_out_date"] == "2026-09-21"
    assert p["engine"] == "google_hotels"


def test_build_params_multi_night():
    p = C.build_params(q="x", check_in_date="2026-12-31", nights=2)
    assert p["check_out_date"] == "2027-01-02"     # 跨年


def test_build_params_requires_q_or_token():
    with pytest.raises(C.SerpApiError):
        C.build_params(check_in_date="2026-09-20")


# ══════════════════════════════════════════════════════════════════════════
# 2. 稅費三態（規則 4）
# ══════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("gross,pretax,expected", [
    (1900, 1645, C.TAX_YES),        # 正常拆分
    (1000, 1000, C.TAX_UNKNOWN),    # ⭐ 相同 ＝ 來源沒拆，不是「沒有稅」
    (943, None, C.TAX_UNKNOWN),     # 地點查詢第 2 頁
    (None, None, C.TAX_UNKNOWN),
])
def test_tax_state(gross, pretax, expected):
    assert C.tax_state(gross, pretax) == expected


def test_tax_state_never_returns_no():
    """SerpApi 的回應永遠推導不出 `no`；`no` 保留給 CSV 匯入。"""
    for g in (None, 0, 100, 1000):
        for p in (None, 0, 100, 1000):
            assert C.tax_state(g, p) != C.TAX_NO


# ══════════════════════════════════════════════════════════════════════════
# 3. 地點查詢（規則 1、2、6）
# ══════════════════════════════════════════════════════════════════════════
def test_location_ignores_ads():
    """
    ⭐ 最重要的一條：`ads` 的價格與 token 都和 `properties` 不同。

    承攜行旅：ads $1,583 / properties $1,274
    捷絲旅：  ads $3,468 / properties $3,142
    """
    rows = C.parse_location_response(sample("loc_p1"))
    by_name = {r.name: r for r in rows}
    assert by_name["承攜行旅 - 台北台大館"].price_gross == 1274
    assert by_name["捷絲旅 臺大尊賢館 (Just Sleep Taipei NTU)"].price_gross == 3142
    assert 1583 not in {r.price_gross for r in rows}
    assert 3468 not in {r.price_gross for r in rows}
    # ads 的 token 也不可以混進來
    assert "CgoIt8Lcl6XB0t84EAE" not in {r.property_token for r in rows}


def test_location_drops_vacation_rentals():
    """第 2 頁混了 type=vacation rental，不是可比的飯店庫存。"""
    payload = sample("loc_p2")
    assert any(p["type"] == "vacation rental" for p in payload["properties"])
    rows = C.parse_location_response(payload)
    assert len(rows) == 2
    assert "Mei Lodge - Double Room" not in {r.name for r in rows}


def test_location_sold_out_always_unknown():
    """⭐ 規則 6：地點路徑分不出「賣完」與「不在前 N 名」。"""
    rows = C.parse_location_response(sample("loc_p1"))
    assert rows and all(r.is_sold_out == C.SOLD_UNKNOWN for r in rows)


def test_location_page2_has_no_pretax():
    """P0 實測：第 2 頁 20 筆全部沒有 before_taxes_fees。"""
    rows = C.parse_location_response(sample("loc_p2"))
    assert all(r.price_pretax is None for r in rows)
    assert all(r.tax_included == C.TAX_UNKNOWN for r in rows)


def test_location_tax_variants():
    """各家稅費結構不同：瀚寓夏天 1.155、漫步旅店 1.000。"""
    by_name = {r.name: r for r in C.parse_location_response(sample("loc_p1"))}
    hanns = by_name["瀚寓夏天 Hanns Summer"]
    assert (hanns.price_gross, hanns.price_pretax) == (1900, 1645)
    assert hanns.tax_included == C.TAX_YES

    meander = by_name["台北漫步旅店 Meander Taipei Hostel"]
    assert meander.price_gross == meander.price_pretax == 1000
    assert meander.tax_included == C.TAX_UNKNOWN


def test_next_page_token():
    assert C.next_page_token_of(sample("loc_p1")) == "CBI="
    assert C.next_page_token_of({"serpapi_pagination": {}}) is None


# ══════════════════════════════════════════════════════════════════════════
# 4. token 查詢（規則 3、5、6）
# ══════════════════════════════════════════════════════════════════════════
def test_token_available():
    r = C.parse_property_response(sample("tok_ok"))
    assert r.is_sold_out == C.SOLD_NO
    assert (r.price_gross, r.price_pretax) == (1900, 1645)
    assert r.tax_included == C.TAX_YES
    assert r.currency == "TWD"
    assert r.name == "瀚寓夏天 Hanns Summer"


def test_token_headline_offer_identified():
    """最低價來自官網直訂 —— 這本身就是 rate parity 訊號。"""
    r = C.parse_property_response(sample("tok_ok"))
    assert r.ota_name == "Hanns Summer"
    assert r.is_official is True
    assert r.num_guests == 2
    assert r.free_cancellation is True


def test_token_headline_left_blank_when_ambiguous():
    """
    ⚠️ Expedia 與 Hotels.com 都是 $3,666。若頂層價剛好是這個數，
    就無法判斷來源 —— 寧可留空也不要猜錯。
    """
    payload = sample("tok_ok")
    payload["rate_per_night"]["extracted_lowest"] = 3666
    payload["rate_per_night"]["extracted_before_taxes_fees"] = 3491
    r = C.parse_property_response(payload)
    assert r.price_gross == 3666
    assert r.ota_name == "" and r.num_guests is None


def test_token_offers_are_not_sorted():
    """
    ⭐ `prices[]` 沒有排序 —— 實測 Traveloka($2,325) 排在 Booking($2,880) 之後。
    任何「拿 prices[0] 當最低價」的寫法都是 bug。
    """
    offers = C.slim_offers(sample("tok_ok")["prices"])
    grosses = [o["gross"] for o in offers]
    assert grosses != sorted(grosses)


def test_token_offers_slimmed_to_six_fields():
    offers = C.slim_offers(sample("tok_ok")["prices"])
    assert len(offers) == 6
    assert set(offers[0]) == set(C.OFFER_FIELDS)
    # 缺 before_taxes_fees 的通路（Traveloka）要留 None，不可以填 0
    traveloka = next(o for o in offers if o["source"] == "Traveloka.com")
    assert traveloka["pretax"] is None


def test_token_far_date_still_has_rate():
    """D+90 有完整報價 —— 這是「空結果 ≠ 太遠沒報價」的反證。"""
    r = C.parse_property_response(sample("tok_far"))
    assert r.is_sold_out == C.SOLD_NO
    assert r.price_gross == 1997


def test_token_sold_out():
    """⭐ 規則 6：status 成功、有基本資料，但沒有報價 ＝ 賣完。"""
    r = C.parse_property_response(sample("tok_soldout"))
    assert r.is_sold_out == C.SOLD_YES
    assert r.price_gross is None and r.price_pretax is None
    assert r.offers == [] and r.offers_json() is None


def test_sold_out_typical_price_range_rejected():
    """
    ⭐⭐ 最容易被忽略的陷阱：賣完那筆的 typical_price_range 是
    `{"extracted_lowest": 168, "extracted_highest": 252}` —— **沒有字串欄位，
    而且那是美元不是台幣**。存進去會讓 typical 區間跨幣別混在一起。
    """
    raw = sample("tok_soldout")
    assert raw["typical_price_range"]["extracted_lowest"] == 168
    r = C.parse_property_response(raw)
    assert r.typical_low is None and r.typical_high is None


def test_typical_price_range_accepted_when_string_present():
    r = C.parse_property_response(sample("tok_ok"))
    assert (r.typical_low, r.typical_high) == (1430, 1874)


def test_token_error_payload_raises():
    with pytest.raises(C.SerpApiError):
        C.parse_property_response({"error": "Invalid API key"})


# ══════════════════════════════════════════════════════════════════════════
# 5. 兩條路徑對同一天、同一家，價格必須一致
# ══════════════════════════════════════════════════════════════════════════
def test_both_paths_agree_on_headline_price():
    """
    ⭐ 規則 3 的理由：A 級（token）與 B/C 級（地點）都取頂層 `rate_per_night`，
    所以同一天同一家的價格必須完全相同。
    不一致就代表某條路徑改用了「自己挑最低」，
    跨期比較會在 D+14 的邊界上出現假跳動。
    """
    loc = {r.name: r for r in C.parse_location_response(sample("loc_p1"))}
    tok = C.parse_property_response(sample("tok_ok"))
    assert loc["瀚寓夏天 Hanns Summer"].price_gross == tok.price_gross == 1900
    assert loc["瀚寓夏天 Hanns Summer"].price_pretax == tok.price_pretax == 1645
