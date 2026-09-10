"""
競品分析 — 競爭組候選搜尋

用途
────────────────────────────────────────────────────────────────────────────
「從地圖／清單挑一家加進競爭組」的資料來源。跑一次**地點查詢**，
把回傳的飯店（含經緯度）整理成候選清單給前端畫地圖與列表。

═══════════════════════════════════════════════════════════════════════════
⚠️⚠️ 這支**會花錢**，而且是排程以外的第二個花錢入口
═══════════════════════════════════════════════════════════════════════════
本模組是 Portal 唯一產生外部費用的模組。多開一個入口就多一個漏錢的地方，
所以這支**必須**與排程走完全相同的三道手續，一道都不能省：

  1. `QS.reserve()` 原子預留 —— 預留不到就不送請求（不是送了才發現超額）
  2. 送出**之前** `commit()` —— 見 `compset_fetch_service` 檔頭規則 1：
     請求送出去了錢就花了，交易在那之後回滾也拿不回來
  3. 寫 `compset_fetch_logs` —— 使用者要在「抓取紀錄」看得到這幾次是誰按的、
     花了多少。查不到來源的支出，事後沒有人說得清楚

⚠️ **不做「拖曳地圖就重新搜尋」。** 那是地圖的直覺操作，但每動一次就是一次錢。
   重新搜尋一律要使用者明確按按鈕（前端負責二次確認），本層只管「被呼叫就花錢」。

⚠️ 翻頁也是錢。`pages` 上限刻意壓在 `MAX_PAGES`，
   P0 實測「公館 台北」有 356 筆結果 —— 不設上限的話一次搜尋可以燒掉幾十次配額。

═══════════════════════════════════════════════════════════════════════════
已知限制（畫面必須說明，否則使用者會以為是壞掉）
═══════════════════════════════════════════════════════════════════════════
· **搜尋不到的家仍然要手動新增。** P0 實測五月家青年旅舍台大館不在前 38 名裡
  （`COMPSET_P0_REPORT.md` §2）。地圖不是完整的世界地圖，是「這次查詢回了什麼」。
· **地點查詢沒有 `address`**（只有 token 路徑有）。所以帶入的資料一定缺地址與房數，
  那兩個當初是人工去觀光署旅宿網查的。
· `ads` 一律不解析（SPEC D12）、`type != "hotel"` 一律濾掉（規則 2）——
  這兩條由 `parse_location_response` 處理，本層不重複實作。
"""
from __future__ import annotations

import json
import logging
import math
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.compset_analysis import (CompsetFetchLog, CompsetHotel,
                                         CompsetSubscriber)
from app.services import compset_quota_service as QS
from app.services import compset_serpapi_client as C

logger = logging.getLogger(__name__)

#: 一次搜尋最多翻幾頁。⚠️ 每一頁 ＝ 一次 API ＝ 一次配額。
MAX_PAGES = 3

#: 搜尋用的入住日預設值：D+7。
#: ⚠️ 選一個「一定有報價」的日子 —— 太近可能整片滿房、太遠可能還沒開賣，
#:    兩種都會讓候選清單看起來像壞掉。
DEFAULT_LEAD_DAYS = 7

#: 判定「這家已經在競爭組裡」的方式。token 優先，沒有 token 才比名稱。
#: ⚠️ 不可以只比名稱：Google 的名稱會變（「承攜行旅」vs「承攜行旅 - 台北台大館」），
#:    只比名稱會讓同一家被重複加進競爭組。


class SearchError(RuntimeError):
    """搜尋失敗（含未設定 API key、配額不足）。"""


class QuotaUnavailable(SearchError):
    """配額不足 —— 這不是錯誤是狀態，畫面要能好好講。"""


def default_check_in(today: date | None = None) -> str:
    return ((today or twnow().date()) + timedelta(days=DEFAULT_LEAD_DAYS)).isoformat()


def haversine_km(lat1: float | None, lng1: float | None,
                 lat2: float | None, lng2: float | None) -> float | None:
    """
    兩點直線距離（公里）。任一點缺座標就回 None。

    ⚠️ 用直線距離不是路網距離。P0 報告吐槽過 Google 的「N 公里遠」會把北車、
       西門町的飯店列進公館的搜尋結果 —— 那是因為它用的基準點不是我們的飯店。
       這裡的基準點固定是**自己**，所以直線距離就足夠回答
       「這家在不在我的商圈裡」。要精確路程請自己開 Google Maps。
    """
    if None in (lat1, lng1, lat2, lng2):
        return None
    r = 6371.0088
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lng2) - float(lng1))
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return round(2 * r * math.asin(math.sqrt(a)), 3)


def _self_coords(hotels: list[CompsetHotel]) -> tuple[float | None, float | None]:
    for h in hotels:
        if h.is_self and h.latitude is not None and h.longitude is not None:
            return float(h.latitude), float(h.longitude)
    return None, None


def _existing_index(hotels: list[CompsetHotel]) -> tuple[set[str], set[str]]:
    """(已有的 token 集合, 已有的名稱集合)。名稱去空白後比對。"""
    tokens = {(h.google_property_token or "").strip()
              for h in hotels if (h.google_property_token or "").strip()}
    names = {(h.display_name or "").strip() for h in hotels}
    names |= {(h.google_query_name or "").strip()
              for h in hotels if (h.google_query_name or "").strip()}
    return tokens, {n for n in names if n}


def search_candidates(db: Session, subscriber_id: int, *,
                      q: str = "", check_in_date: str = "",
                      pages: int = 1,
                      today: date | None = None) -> dict[str, Any]:
    """
    跑一次地點查詢，回傳候選飯店清單。

    ⚠️ **呼叫端要先確認使用者真的想花這筆錢。** 進到這裡就一定會扣配額。

    回傳：
        {
          "items": [...],            # 候選（含經緯度、價格、距離、是否已在組內）
          "self": {...} | None,      # 自己的座標，給地圖定中心用
          "request_count": int,      # 實際送出幾次（＝扣了幾次配額）
          "quota": {...},            # 扣完之後的配額狀態
          "warnings": [...],
        }
    """
    sub = db.get(CompsetSubscriber, subscriber_id)
    if sub is None:
        raise SearchError("找不到這筆訂閱客戶")

    query = (q or sub.location_query or "").strip()
    if not query:
        raise SearchError(
            "沒有查詢字串。請在搜尋框輸入地點（例如「公館 台北 飯店」），"
            "或先到「訂閱與配額」設定地點查詢字串。")

    if not C.is_configured():
        raise SearchError(
            "尚未設定 SERPAPI_API_KEY，無法搜尋。"
            "（未設定時系統是安靜跳過，不會報錯 —— 所以這裡明講。）")

    pages = max(1, min(int(pages or 1), MAX_PAGES))
    check_in = (check_in_date or "").strip() or default_check_in(today)

    # ── 1. 先預留，預留不到就不送 ────────────────────────────────────
    period_start = QS.ensure_period(db, subscriber_id, today)
    quota_before = sub.quota_used
    if not QS.reserve(db, subscriber_id, pages, today):
        st = QS.quota_status(db, subscriber_id)
        raise QuotaUnavailable(
            f"配額不足，這次搜尋需要 {pages} 次、剩餘 {st['available']} 次。"
            "請到「訂閱與配額」手動加發，或改抓少一點頁數。")
    # ⚠️ 送出之前一定要 commit —— 請求送出去錢就花了，之後回滾也拿不回來
    db.commit()

    hotels = list(db.execute(
        select(CompsetHotel).where(CompsetHotel.subscriber_id == subscriber_id)
    ).scalars().all())
    known_tokens, known_names = _existing_index(hotels)
    self_lat, self_lng = _self_coords(hotels)

    warnings: list[str] = []
    parsed: list[C.ParsedRate] = []
    sent = 0
    token: str | None = None
    error = ""
    started_at = twnow()

    try:
        for _ in range(pages):
            # ⭐ **先計數再送出**，不是成功才計數。
            #
            # 例外丟出來時我們**無法知道錢有沒有花掉**：`_request()` 內部會對
            # 429／5xx 重試，所以一個最終失敗的呼叫可能已經送出好幾次請求。
            # 兩個方向的代價不對稱：
            #   · 少算 → 以為還有額度、實際已超支（硬停失效，會真的多花錢）
            #   · 多算 → 白白浪費幾次額度
            # 這是成本控管模組，**寧可多算**。
            sent += 1
            payload = C.fetch_location(
                q=query, check_in_date=check_in, next_page_token=token,
                adults=sub.param_adults, nights=sub.param_nights,
                gl=sub.param_gl, hl=sub.param_hl, currency=sub.param_currency)
            parsed.extend(C.parse_location_response(payload))
            token = C.next_page_token_of(payload)
            if not token:
                break
    except Exception as exc:                                  # noqa: BLE001
        error = str(exc)
        logger.warning("compset 搜尋失敗：%s", exc)

    # ── 2. **完全沒有嘗試過**的頁數才退還 ───────────────────────────
    # ⚠️ 退的是「沒送出去過的」，不是「沒成功的」—— 理由見上面的先計數註解。
    if sent < pages:
        QS.refund(db, subscriber_id, pages - sent, period_start)

    # ── 3. 整理候選 ────────────────────────────────────────────────
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    no_gps = 0
    for r in parsed:
        key = (r.property_token or "").strip() or f"name:{r.name.strip()}"
        if key in seen:
            continue          # 同一家在多頁重複出現，只留第一筆
        seen.add(key)

        in_compset = (
            ((r.property_token or "").strip() in known_tokens)
            or (r.name.strip() in known_names)
        )
        if r.latitude is None or r.longitude is None:
            no_gps += 1
        items.append({
            "name": r.name,
            "property_token": r.property_token,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "price_gross": r.price_gross,
            "price_pretax": r.price_pretax,
            "hotel_class": r.hotel_class,
            "overall_rating": r.overall_rating,
            "reviews": r.reviews,
            "distance_km": haversine_km(self_lat, self_lng,
                                        r.latitude, r.longitude),
            "in_compset": in_compset,
        })

    # 由近到遠；沒有距離的排最後（不是排最前 —— 那會讓最沒用的浮到上面）
    items.sort(key=lambda x: (x["distance_km"] is None,
                              x["distance_km"] if x["distance_km"] is not None else 0))

    if no_gps:
        warnings.append(f"{no_gps} 家沒有座標，只會出現在清單、不會出現在地圖上。")
    if self_lat is None:
        warnings.append(
            "競爭組裡的「自己」還沒有座標，所以算不出距離、地圖也不會自動定位到你。"
            "把自己那一家從搜尋結果重新帶入一次，或手動填經緯度即可。")
    if error:
        warnings.append("部分頁面查詢失敗，清單可能不完整。")

    # ── 4. 記帳：這幾次是誰花的、花在哪 ──────────────────────────────
    quota_after = QS.quota_status(db, subscriber_id)["used"]
    db.add(CompsetFetchLog(
        subscriber_id=subscriber_id,
        tier="-",                       # 不屬於 A／B／C，是人工搜尋
        fetch_path="location",
        started_at=started_at, finished_at=twnow(),
        stay_date_from=check_in, stay_date_to=check_in,
        request_count=sent, row_count=len(items),
        quota_before=quota_before, quota_after=quota_after,
        status="failed" if error and not items else
               ("partial" if error else "success"),
        params_json=json.dumps(
            {"mode": "hotel_search", "q": query, "pages": pages},
            ensure_ascii=False),
        warnings_json=json.dumps(warnings, ensure_ascii=False) if warnings else None,
        error_message=error[:500],
    ))
    db.commit()

    if error and not items:
        raise SearchError(f"搜尋失敗：{error}")

    return {
        "items": items,
        "self": ({"latitude": self_lat, "longitude": self_lng}
                 if self_lat is not None else None),
        "query": query,
        "check_in_date": check_in,
        "request_count": sent,
        "quota": QS.quota_status(db, subscriber_id),
        "warnings": warnings,
    }
