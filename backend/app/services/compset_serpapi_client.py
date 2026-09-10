"""
競品分析 — SerpApi `google_hotels` 客戶端（參數封裝、重試、解析）

建立日期：2026-09-09
規格書：`docs/SPEC_compset_analysis.md` v1.2 §5、§6
P0 報告：`docs/COMPSET_P0_REPORT.md`
真實樣本：`backend/tests/fixtures/compset_serpapi_samples.json`

═══════════════════════════════════════════════════════════════════════════
設計：解析是純函式，連線是薄薄一層
═══════════════════════════════════════════════════════════════════════════
`parse_*` 全部是純函式（吃 dict、吐 dataclass），不碰網路、不碰 DB。
所有解析規則都用 P0 抓到的**真實回應**離線測試（`tests/test_compset_serpapi.py`）。

⚠️ 本 session 的雲端容器與桌面 VM 都被網路政策擋掉 serpapi.com，
   所以 `fetch_*` 這一層**尚未做過真實連線驗證**。
   部署前必須在 Portal 正式機跑一次（COMPSET_TODO 1.10）。

═══════════════════════════════════════════════════════════════════════════
六條解析規則（全部來自 P0 實測，不是猜的）
═══════════════════════════════════════════════════════════════════════════
1. **⭐ 只解析 `properties`，`ads` 一律丟掉**（SPEC D12）
   實測同一家飯店在兩邊的價格與 property_token 都不同：
   承攜行旅 ads $1,583 / properties $1,274（高 24%）、
   捷絲旅 ads $3,468 / properties $3,142。
   混進去會系統性高估 10~25%，而且數字都很合理 —— **是看不出來的錯**。

2. **只收 `type == "hotel"`**
   地點查詢第 2 頁混了 `type: "vacation rental"`（民宿／整層出租）。
   那不是可比的飯店庫存，會把中位數拉歪。

3. **⭐ 報價一律取「頂層 `rate_per_night`」，不是自己從 `prices[]` 挑**
   理由是**兩條路徑要可比**：地點查詢只給頂層值，token 查詢兩者都有。
   若 token 路徑改用「自己挑最低」，A 級與 B/C 級的價格語意就不一致，
   跨期比較會在 D+14 的邊界上出現假跳動。
   ⚠️ `prices[]` **沒有排序**（實測第 4 筆比第 2 筆便宜），
   任何「拿 prices[0] 當最低價」的寫法都是 bug。

4. **⭐ `tax_included` 只有 yes / unknown 兩種來自 SerpApi 的可能，永遠不會是 no**
   · 有 `before_taxes_fees` 且與 `lowest` 不同 → `yes`
   · 沒有 `before_taxes_fees`（地點查詢第 2 頁全部如此）→ `unknown`
   · 兩者相同（台北漫步旅店 1000/1000）→ `unknown`，**不是 `no`**
     那代表來源沒有拆分稅費，不代表沒有稅。
   `no` 保留給 CSV 匯入時使用者明確標示「這是稅前價」的情形。

5. **⭐ `typical_price_range` 沒有字串欄位就不採用**
   實測賣完那筆回傳 `{"extracted_lowest": 168, "extracted_highest": 252}`，
   **沒有 `lowest`/`highest` 字串** —— 168 對台北飯店不合理，那是美元。
   字串欄位帶幣別符號，是唯一能確認幣別的線索。
   沒有字串、或本來就沒有報價時，一律不寫入。

6. **滿房判定只在 token 路徑成立**（SPEC D13）
   · token 路徑、有 `rate_per_night` → `is_sold_out = "no"`
   · token 路徑、無 `rate_per_night` 且 `prices` 為空 → `is_sold_out = "yes"`
   · **地點路徑一律 `"unknown"`** —— 賣完的飯店會直接從結果消失，
     與「不在前 N 名」分不開。

═══════════════════════════════════════════════════════════════════════════
金鑰處理
═══════════════════════════════════════════════════════════════════════════
金鑰來自 `settings.SERPAPI_API_KEY`（`backend/.env`）。
⚠️ **任何 log、例外訊息、`params_json` 都不可以帶到金鑰。**
   `build_params()` 刻意不含 `api_key`，金鑰只在 `_request()` 送出前才併進去，
   而錯誤訊息只會印 `build_params()` 的內容。
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

ENGINE = "google_hotels"
MAX_RETRIES = 2                                  # 首次 ＋ 最多 2 次重試
RETRY_BACKOFF_SECONDS = (2, 5)
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

TAX_YES, TAX_NO, TAX_UNKNOWN = "yes", "no", "unknown"
SOLD_YES, SOLD_NO, SOLD_UNKNOWN = "yes", "no", "unknown"
PATH_TOKEN, PATH_LOCATION = "token", "location"

# `raw_json` 只留這六個欄位（SPEC §4.4 坑 6）。
# 完整回應的 images／nearby_places／reviews_breakdown 佔 90% 體積、對分析零用途。
OFFER_FIELDS = ("source", "gross", "pretax", "num_guests",
                "free_cancellation", "official")


class SerpApiError(RuntimeError):
    """SerpApi 呼叫失敗。訊息保證不含金鑰。"""


class SerpApiNotConfigured(SerpApiError):
    pass


# ══════════════════════════════════════════════════════════════════════════
# 解析結果
# ══════════════════════════════════════════════════════════════════════════
@dataclass
class ParsedRate:
    """一家飯店、一個入住日的解析結果。欄位對齊 `compset_rate_snapshots`。"""

    property_token: str = ""
    name: str = ""
    price_gross: float | None = None
    price_pretax: float | None = None
    currency: str = "TWD"
    tax_included: str = TAX_UNKNOWN
    ota_name: str = ""
    is_official: bool = False
    num_guests: int | None = None
    free_cancellation: bool = False
    room_type_raw: str = ""
    is_sold_out: str = SOLD_UNKNOWN
    typical_low: float | None = None
    typical_high: float | None = None
    hotel_class: int | None = None
    overall_rating: float | None = None
    reviews: int | None = None
    #: ⚠️ 地點查詢**每一筆都有** `gps_coordinates`（P0 實測 6/6），
    #:    這是「從地圖挑競爭組」能成立的前提。token 路徑也有。
    latitude: float | None = None
    longitude: float | None = None
    #: ⚠️ **只有 token 路徑有 `address`**，地點查詢沒有。
    #:    所以從搜尋結果新增競爭組時，地址一定是空的，要人自己補。
    address: str = ""
    offers: list[dict[str, Any]] = field(default_factory=list)

    def offers_json(self) -> str | None:
        """存進 `compset_rate_snapshots.raw_json` 的精簡報價陣列。"""
        return json.dumps(self.offers, ensure_ascii=False) if self.offers else None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════
# 純函式：參數
# ══════════════════════════════════════════════════════════════════════════
def check_out_for(check_in: str, nights: int = 1) -> str:
    """`check_out_date` ＝ 入住日 ＋ nights。"""
    d = date.fromisoformat(check_in) + timedelta(days=max(int(nights), 1))
    return d.isoformat()


def build_params(
    *,
    check_in_date: str,
    q: str | None = None,
    property_token: str | None = None,
    next_page_token: str | None = None,
    adults: int = 2,
    nights: int = 1,
    gl: str = "tw",
    hl: str = "zh-tw",
    currency: str = "TWD",
) -> dict[str, Any]:
    """
    組出查詢參數。**刻意不含 `api_key`** —— 這份 dict 會被寫進
    `compset_fetch_logs.params_json`，也會出現在錯誤訊息裡。

    ⚠️ `q` 與 `property_token` 至少要有一個。
       token 路徑仍然帶 `q`（飯店名）是 SerpApi 的要求。
    """
    if not q and not property_token:
        raise SerpApiError("build_params 需要 q 或 property_token 其中之一")
    params: dict[str, Any] = {
        "engine": ENGINE,
        "check_in_date": check_in_date,
        "check_out_date": check_out_for(check_in_date, nights),
        "adults": int(adults),
        "gl": gl,
        "hl": hl,
        "currency": currency,
    }
    if q:
        params["q"] = q
    if property_token:
        params["property_token"] = property_token
    if next_page_token:
        params["next_page_token"] = next_page_token
    return params


# ══════════════════════════════════════════════════════════════════════════
# 純函式：解析
# ══════════════════════════════════════════════════════════════════════════
def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _gps(payload: Any) -> tuple[float | None, float | None]:
    """取出 `gps_coordinates`。缺了就回 (None, None)，不要丟例外。"""
    g = (payload or {}).get("gps_coordinates") if isinstance(payload, dict) else None
    if not isinstance(g, dict):
        return None, None
    return _num(g.get("latitude")), _num(g.get("longitude"))


def _rate_pair(rate: Any) -> tuple[float | None, float | None]:
    """從 `rate_per_night` 取出（含稅費, 稅前）。"""
    if not isinstance(rate, dict):
        return None, None
    return (_num(rate.get("extracted_lowest")),
            _num(rate.get("extracted_before_taxes_fees")))


def tax_state(gross: float | None, pretax: float | None) -> str:
    """
    ⭐ 規則 4：SerpApi 的回應永遠推導不出 `no`。

    兩價相同代表**來源沒有拆分稅費**，不代表沒有稅 —— 記 `unknown`。
    """
    if gross is None or pretax is None:
        return TAX_UNKNOWN
    if abs(gross - pretax) < 0.005:
        return TAX_UNKNOWN
    return TAX_YES


def _typical(payload: dict[str, Any], has_rate: bool) -> tuple[float | None, float | None]:
    """
    ⭐ 規則 5：沒有 `lowest`/`highest` 字串就不採用（幣別無從確認）。

    實測賣完那筆回 `{"extracted_lowest": 168, "extracted_highest": 252}`，
    數值是美元 —— 直接存進去會讓 typical 區間跨幣別混在一起。
    """
    tp = payload.get("typical_price_range")
    if not has_rate or not isinstance(tp, dict):
        return None, None
    if not (isinstance(tp.get("lowest"), str) and isinstance(tp.get("highest"), str)):
        logger.warning("compset: typical_price_range 缺少字串欄位，幣別不可信，已忽略")
        return None, None
    return _num(tp.get("extracted_lowest")), _num(tp.get("extracted_highest"))


def slim_offers(prices: Any) -> list[dict[str, Any]]:
    """把 `prices[]` 精簡成六欄（SPEC §4.4 坑 6）。"""
    out: list[dict[str, Any]] = []
    for p in prices or []:
        if not isinstance(p, dict):
            continue
        gross, pretax = _rate_pair(p.get("rate_per_night"))
        out.append({
            "source": (p.get("source") or "")[:50],
            "gross": gross,
            "pretax": pretax,
            "num_guests": p.get("num_guests"),
            "free_cancellation": bool(p.get("free_cancellation")),
            "official": bool(p.get("official")),
        })
    return out


def _match_headline_offer(offers: list[dict[str, Any]],
                          gross: float | None) -> dict[str, Any] | None:
    """
    找出「哪一個通路提供了頂層那個最低價」。

    ⚠️ 只有**恰好一筆**吻合時才採用。有兩筆以上同價（實測 Expedia 與 Hotels.com
       都是 $3,666）就無法判斷是誰，寧可留空也不要猜錯來源。
    """
    if gross is None:
        return None
    hits = [o for o in offers if o["gross"] is not None
            and abs(o["gross"] - gross) < 0.005]
    return hits[0] if len(hits) == 1 else None


def parse_property_response(payload: dict[str, Any]) -> ParsedRate:
    """
    解析 `property_token` 路徑（A 級）的回應。

    這條路徑是**唯一**拿得到滿房訊號的（規則 6）。
    """
    if not isinstance(payload, dict):
        raise SerpApiError("回應不是 JSON 物件")
    if payload.get("error"):
        raise SerpApiError(f"SerpApi 回報錯誤：{payload['error']}")

    gross, pretax = _rate_pair(payload.get("rate_per_night"))
    has_rate = gross is not None
    offers = slim_offers(payload.get("prices"))

    # ── 規則 6：滿房判定 ────────────────────────────────────────────
    if has_rate:
        sold = SOLD_NO
    elif not offers:
        sold = SOLD_YES
    else:
        # 沒有頂層報價卻有通路報價 —— 不該發生，寧可標 unknown 也不要猜
        sold = SOLD_UNKNOWN
        logger.warning("compset: %s 無 rate_per_night 但有 %d 筆 prices，"
                       "滿房狀態標 unknown", payload.get("name"), len(offers))

    low, high = _typical(payload, has_rate)
    headline = _match_headline_offer(offers, gross)
    lat, lng = _gps(payload)

    return ParsedRate(
        property_token=payload.get("property_token") or "",
        name=payload.get("name") or "",
        latitude=lat, longitude=lng,
        address=payload.get("address") or "",
        price_gross=gross,
        price_pretax=pretax,
        currency=(payload.get("search_parameters") or {}).get("currency") or "TWD",
        tax_included=tax_state(gross, pretax),
        ota_name=(headline or {}).get("source", "") or "",
        is_official=bool((headline or {}).get("official")),
        num_guests=(headline or {}).get("num_guests"),
        free_cancellation=bool((headline or {}).get("free_cancellation")),
        is_sold_out=sold,
        typical_low=low,
        typical_high=high,
        hotel_class=payload.get("extracted_hotel_class"),
        overall_rating=_num(payload.get("overall_rating")),
        reviews=payload.get("reviews"),
        offers=offers,
    )


def parse_location_response(payload: dict[str, Any]) -> list[ParsedRate]:
    """
    解析地點查詢（B／C 級）的回應。

    ⭐ 規則 1：`ads` 一律丟掉。
    ⭐ 規則 2：只收 `type == "hotel"`。
    ⭐ 規則 6：`is_sold_out` 一律 `unknown` —— 這條路徑分不出「賣完」與「不在前 N 名」。
    """
    if not isinstance(payload, dict):
        raise SerpApiError("回應不是 JSON 物件")
    if payload.get("error"):
        raise SerpApiError(f"SerpApi 回報錯誤：{payload['error']}")

    currency = (payload.get("search_parameters") or {}).get("currency") or "TWD"
    results: list[ParsedRate] = []
    dropped_rentals = 0

    for prop in payload.get("properties") or []:
        if not isinstance(prop, dict):
            continue
        if prop.get("type") != "hotel":
            dropped_rentals += 1
            continue
        gross, pretax = _rate_pair(prop.get("rate_per_night"))
        lat, lng = _gps(prop)
        results.append(ParsedRate(
            property_token=prop.get("property_token") or "",
            name=prop.get("name") or "",
            latitude=lat, longitude=lng,
            price_gross=gross,
            price_pretax=pretax,
            currency=currency,
            tax_included=tax_state(gross, pretax),
            is_sold_out=SOLD_UNKNOWN,          # ⭐ 規則 6
            hotel_class=prop.get("extracted_hotel_class"),
            overall_rating=_num(prop.get("overall_rating")),
            reviews=prop.get("reviews"),
        ))

    if dropped_rentals:
        logger.info("compset: 已濾掉 %d 筆非飯店（vacation rental）", dropped_rentals)
    return results


def next_page_token_of(payload: dict[str, Any]) -> str | None:
    """取下一頁 token。沒有就回 None（代表已到底）。"""
    pag = payload.get("serpapi_pagination") or {}
    return pag.get("next_page_token") or None


# ══════════════════════════════════════════════════════════════════════════
# 連線層（薄）
# ══════════════════════════════════════════════════════════════════════════
def is_configured() -> bool:
    """未設定金鑰時抓取層應直接跳過並記 warning，而不是讓整個排程炸掉。"""
    return bool((settings.SERPAPI_API_KEY or "").strip())


def _request(params: dict[str, Any]) -> dict[str, Any]:
    """
    送出一次查詢並回傳 JSON。

    ⚠️ **金鑰只在這裡併進去**，且不會出現在任何 log 或例外訊息裡
       —— 錯誤訊息只印 `params`（不含金鑰的那份）。

    重試：429／5xx／連線逾時最多重試 2 次（2s、5s）。
    4xx（除了 429）不重試 —— 那是參數錯了，重試只是白白多花錢。
    """
    import requests                      # 函式內 import：不裝 requests 的環境仍可 import 本模組

    if not is_configured():
        raise SerpApiNotConfigured(
            "SERPAPI_API_KEY 未設定（backend/.env）。抓取層應跳過此訂閱並記 warning。"
        )

    sent = dict(params)
    sent["api_key"] = settings.SERPAPI_API_KEY.strip()
    last_err: str = ""

    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(settings.SERPAPI_BASE_URL, params=sent,
                                timeout=settings.SERPAPI_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.json()
            last_err = f"HTTP {resp.status_code}"
            if resp.status_code not in RETRYABLE_STATUS:
                break
        except Exception as exc:                       # 連線層例外一律可重試
            last_err = f"{type(exc).__name__}"
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)])

    raise SerpApiError(f"SerpApi 查詢失敗（{last_err}），params={params}")


def fetch_property(*, property_token: str, q: str, check_in_date: str,
                   **kwargs: Any) -> dict[str, Any]:
    """A 級：token 逐家查。回傳原始 JSON（解析交給 `parse_property_response`）。"""
    return _request(build_params(property_token=property_token, q=q,
                                 check_in_date=check_in_date, **kwargs))


def fetch_location(*, q: str, check_in_date: str,
                   next_page_token: str | None = None,
                   **kwargs: Any) -> dict[str, Any]:
    """B／C 級：地點查詢。回傳原始 JSON（解析交給 `parse_location_response`）。"""
    return _request(build_params(q=q, check_in_date=check_in_date,
                                 next_page_token=next_page_token, **kwargs))
