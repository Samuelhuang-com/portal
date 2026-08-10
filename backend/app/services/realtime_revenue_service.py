"""
即時營運 — 營收與結構分析（非同步版 revenueInventoryStatistics）

規格書：docs/SPEC_realtime_operations.md
串接實測：docs/OHIP_INTEGRATION.md §4.3.1
可行性評估：docs/EVAL_opera_api_module.md

⚠️ 與 `/opera/*`（人工上傳 TXT）完全獨立，不共用資料表、不寫入任何 `opera_*` 表。

本服務刻意只做 TXT 版**做不到**的分析（評估文件 §7 的結論）：

| 能力 | TXT 有嗎 | 說明 |
|------|---------|------|
| 房型別營收／ADR | ❌ 只有全館 | `groupBy: RoomType` |
| 市場區隔別營收 | ❌ 完全沒有 | `groupBy: MarketCode` |
| 取消房數 | ❌ 完全沒有 | `cancelledRooms`，可算取消率 |
| out of service 房 | ❌ 只有 OOO | `osRooms`，維修 vs 停售的區分 |

⚠️ 2026-08-06 實測踩到的四個坑（每一個都會讓程式出錯或算錯）
────────────────────────────────────────────────────────────────────────────
1. **值為 0 的欄位會被整個省略**，不是回 0。`ooRooms` 只出現在 30 筆中的 4 筆。
   → 一律用 `_num(row.get(k))`，直接 `row[k]` 會 KeyError。
2. **spec 有 16 欄，實際只回 11 欄**。`foodRevenue`／`noShowRooms` 這次完全沒回。
   → 缺欄位一律當 None 呈現，不要自己補 0（0 和「沒有」是不同的事）。
3. **數值是字串**（`"153103.809523809525"`，18 位有效數字）。
   → 一律轉 `Decimal`，**不要用 float**（會有精度誤差，月合計會差幾塊錢）。
4. `totalRevenue` ≥ `roomRevenue`，差額是房租以外的雜項收入。
   → 兩個都保留並分開呈現，讓使用者自己判斷要看哪一個。
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.services import ohip_async_cache
from app.services import ohip_client
from app.services import realtime_status_service as LS
from app.services.ohip_async_cache import CooldownActive
from app.services.ohip_client import OhipError

# ── 日期區間上限（2026-08-07 調整）──────────────────────────────────────────
# Oracle 官方：OPERA Cloud **23.2 以上**，revenueInventoryStatistics 的單次區間
# 上限從 94 天放寬到 400 天。
# ⚠️ **SUMMER 的 OPERA Cloud 版本目前未知**（見 EVAL_ohip_strategic_data.md §6 待驗 #1），
#    所以不能直接寫死 400 —— 若實際是 23.2 以前，每一次查詢都會 400 錯誤。
#    做法：先試 400，收到 400 錯誤且該段確實超過 94 天，就自動降回 94 並記住。
PREFERRED_SPAN_DAYS = 400     # OPERA Cloud 23.2+
FALLBACK_SPAN_DAYS = 94       # 23.2 以前

# 目前確認可用的區間上限。None = 尚未確認（下次查詢會試 400）。
# ⚠️ 刻意只放記憶體不落地：服務重啟後會再試一次 400，
#    這樣 OPERA 哪天升版我們會自動受惠，不需要有人記得回來改設定。
_span_lock = threading.Lock()
_effective_span_days: int | None = None

# ── 快取（2026-08-07 從記憶體改為落地）──────────────────────────────────────
# 原本是 15 分鐘記憶體快取。改的原因見 docs/EVAL_ohip_strategic_data.md §3.1：
# Oracle 規定**相同參數的 async 請求最短間隔 30 分鐘**，15 分鐘的快取擋不住，
# 而且記憶體快取一重啟就沒了。TTL 必須 ≥ 冷卻時間，否則會出現
# 「快取過期了但還不能重打」的空窗期。
CACHE_TTL_SECONDS = ohip_async_cache.MIN_INTERVAL_SECONDS

# groupBy 可選值（spec enum）
GROUP_BY_MARKET = "MarketCode"
GROUP_BY_ROOM_TYPE = "RoomType"
GROUP_BY_GUARANTEE = "GuaranteeType"
VALID_GROUP_BY = {GROUP_BY_MARKET, GROUP_BY_ROOM_TYPE, GROUP_BY_GUARANTEE}


def _num(v: Any) -> Decimal | None:
    """字串 → Decimal。缺值回 None，**不補 0**。"""
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _f(v: Decimal | None) -> float | None:
    """輸出給 JSON 時才轉 float —— 計算全程用 Decimal。"""
    return float(v) if v is not None else None


def current_span_days() -> int:
    """目前採用的單段上限。未確認過就先試 `PREFERRED_SPAN_DAYS`。"""
    with _span_lock:
        return _effective_span_days or PREFERRED_SPAN_DAYS


def _downgrade_span() -> bool:
    """把上限降到 94 天並記住。已經是 94 就回 False（代表沒得再降）。"""
    global _effective_span_days
    with _span_lock:
        if _effective_span_days == FALLBACK_SPAN_DAYS:
            return False
        _effective_span_days = FALLBACK_SPAN_DAYS
        return True


def _split_ranges(start: date, end: date, span: int | None = None) -> list[tuple[date, date]]:
    """把長區間切成 `span` 天以內的段。"""
    span = span or current_span_days()
    out: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        seg_end = min(cur + timedelta(days=span - 1), end)
        out.append((cur, seg_end))
        cur = seg_end + timedelta(days=1)
    return out


def _endpoint(ext: str, hotel_id: str) -> str:
    return (f"/inv/async/v1/externalSystems/{ext}"
            f"/hotels/{hotel_id}/revenueInventoryStatistics")


def _fetch(db: Session, start: date, end: date, group_by: list[str],
           triggered_by: str) -> tuple[list[dict], dict]:
    """向 OHIP 取一段（≤94 天）的營收資料。回傳 (rows, meta)。"""
    hotel_id = settings.OHIP_HOTEL_ID
    ext = settings.OHIP_EXT_SYSTEM_CODE
    path = _endpoint(ext, hotel_id)
    body = {
        "dateRangeStart": start.isoformat(),
        "dateRangeEnd": end.isoformat(),
        "groupBy": group_by,
    }

    try:
        payload, meta = ohip_client.async_read(path, body, hotel_id=hotel_id)
    except OhipError as e:
        LS._log_call(db, endpoint=path, hotel_id=hotel_id,
                     date_start=start.isoformat(), date_end=end.isoformat(),
                     meta={"status_code": e.status_code or 0,
                           "request_id": e.request_id or ""},
                     success=False, error=str(e), triggered_by=triggered_by)
        raise

    LS._log_call(db, endpoint=path, hotel_id=hotel_id,
                 date_start=start.isoformat(), date_end=end.isoformat(),
                 meta=meta, success=True, triggered_by=triggered_by)

    rows = (payload or {}).get("revInvStats") or []
    return rows, meta


def _rows_cache_key(start: date, end: date, group_by: list[str]) -> str:
    """⚠️ 從寬涵蓋所有會送出的參數 —— 「identical request」的判定範圍
    官方沒有明講，從嚴的代價是踩 30 分鐘限制，從寬只是多存幾筆。"""
    return ohip_async_cache.build_key(
        "revrows",
        settings.OHIP_HOTEL_ID,
        settings.OHIP_EXT_SYSTEM_CODE,
        start.isoformat(), end.isoformat(),
        ",".join(sorted(group_by)),
    )


def fetch_rows(db: Session, start: date, end: date, group_by: list[str],
               triggered_by: str, *, force: bool = False
               ) -> tuple[list[dict], dict, float, bool]:
    """取一段的原始 rows，**走落地快取與 30 分鐘冷卻**。

    Returns:
        (rows, meta, fetched_epoch, from_cache)

    Raises:
        CooldownActive: 相同條件距上次取數未滿 30 分鐘。**本地擋下，沒有真的發請求。**
        OhipError:      實際呼叫失敗。

    ⚠️ 為什麼是「本地先擋」而不是「打了看對方回什麼」：
       Oracle 沒有寫違規時回哪個狀態碼，我們無法可靠地辨識。
       本地擋住則不論對方回什麼都不會踩到，而且不浪費一次計費呼叫。
    """
    key = _rows_cache_key(start, end, group_by)

    if not force:
        hit = ohip_async_cache.get(db, key, ttl_seconds=CACHE_TTL_SECONDS)
        if hit is not None:
            rows, meta, epoch = hit
            return rows, meta, epoch, True

    remaining = ohip_async_cache.cooldown_remaining(db, key)
    if remaining > 0:
        raise CooldownActive(remaining, key)

    rows, meta = _fetch(db, start, end, group_by, triggered_by)
    epoch = ohip_async_cache.put(
        db, key, rows, meta,
        endpoint=meta.get("endpoint", ""),
        hotel_id=settings.OHIP_HOTEL_ID,
        date_start=start.isoformat(), date_end=end.isoformat(),
    )
    return rows, meta, epoch, False


def _normalize(row: dict) -> dict[str, Any]:
    """一筆原始 row → 內部表示（Decimal）。⚠️ 缺欄位一律 None，不補 0。"""
    phys = _num(row.get("physicalRooms"))
    ooo = _num(row.get("ooRooms")) or Decimal(0)      # 缺 = 0 房（這個補 0 是對的）
    oos = _num(row.get("osRooms")) or Decimal(0)
    sold = _num(row.get("roomsSold"))
    room_rev = _num(row.get("roomRevenue"))
    total_rev = _num(row.get("totalRevenue"))

    avail = (phys - ooo) if phys is not None else None

    return {
        "business_date":   row.get("occupancyDate"),
        "market_code":     row.get("marketCode"),
        "room_type":       row.get("roomType"),
        "res_type":        row.get("resType"),
        "physical_rooms":  phys,
        "ooo_rooms":       ooo,
        "oos_rooms":       oos,
        "available_rooms": avail,
        "rooms_sold":      sold,
        "room_revenue":    room_rev,
        "total_revenue":   total_rev,
        "other_revenue":   (total_rev - room_rev)
                           if (total_rev is not None and room_rev is not None) else None,
        "arrival_rooms":   _num(row.get("roomArrivals")),
        "departure_rooms": _num(row.get("roomDepartures")),
        "cancelled_rooms": _num(row.get("cancelledRooms")),
        "no_show_rooms":   _num(row.get("noShowRooms")),
        "food_revenue":    _num(row.get("foodRevenue")),
    }


def _derive(r: dict[str, Any]) -> dict[str, Any]:
    """加上 ADR／RevPAR／住房率。口徑與 opera_analysis_service.py 一致。"""
    sold, avail = r.get("rooms_sold"), r.get("available_rooms")
    rev = r.get("room_revenue")
    r["adr"] = (rev / sold) if (rev is not None and sold) else None
    r["revpar"] = (rev / avail) if (rev is not None and avail) else None
    r["occupancy"] = (sold / avail) if (sold is not None and avail) else None
    return r


def _to_json(r: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in r.items():
        out[k] = _f(v) if isinstance(v, Decimal) else v
    return out


def _aggregate(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """依指定維度彙總。金額用 Decimal 相加，比率**最後才算**（加權，非平均）。"""
    buckets: dict[str, dict[str, Any]] = {}
    for r in rows:
        k = r.get(key) or "（未分類）"
        b = buckets.setdefault(k, {
            key: k, "days": 0,
            "rooms_sold": Decimal(0), "available_rooms": Decimal(0),
            "room_revenue": Decimal(0), "total_revenue": Decimal(0),
            "cancelled_rooms": Decimal(0),
            "arrival_rooms": Decimal(0), "departure_rooms": Decimal(0),
        })
        b["days"] += 1
        for f in ("rooms_sold", "available_rooms", "room_revenue", "total_revenue",
                  "cancelled_rooms", "arrival_rooms", "departure_rooms"):
            v = r.get(f)
            if v is not None:
                b[f] += v

    out = []
    for b in buckets.values():
        b = dict(b)
        sold, avail, rev = b["rooms_sold"], b["available_rooms"], b["room_revenue"]
        b["adr"] = (rev / sold) if sold else None
        b["revpar"] = (rev / avail) if avail else None
        b["occupancy"] = (sold / avail) if avail else None
        out.append(_to_json(b))

    out.sort(key=lambda x: (x.get("room_revenue") or 0), reverse=True)
    return out


# ── 對外主函式 ───────────────────────────────────────────────────────────────

def get_revenue(db: Session, *, start: str, end: str,
                group_by: list[str] | None = None,
                force: bool = False, triggered_by: str = "") -> dict[str, Any]:
    """查詢區間營收。

    Args:
        start / end: ISO 日期。超過單段上限會自動切段（每段各算一次 API 呼叫）。
                     上限預設試 400 天（OPERA Cloud 23.2+），被拒則自動降回 94 天
        group_by:    `MarketCode` / `RoomType` / `GuaranteeType`，可多選；
                     空 list 代表全館合計（回傳粒度最細到日）
        force:       略過快取重新取數。⚠️ 若相同條件距上次取數未滿 30 分鐘，
                     會丟出 `CooldownActive`（本地擋下，不會浪費一次計費呼叫）

    Raises:
        CooldownActive: 30 分鐘冷卻未過
        OhipError:      實際呼叫失敗

    ⚠️ 每段都是一次非同步查詢（POST + 輪詢 + GET），**實測單段約 3 秒**。
    """
    if not ohip_client.is_configured():
        return {"configured": False, "missing": ohip_client.missing_settings(),
                "days": [], "summary": {}, "source": None}

    group_by = [g for g in (group_by or []) if g in VALID_GROUP_BY]
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    if s > e:
        s, e = e, s

    # ── 取數：逐段走落地快取；400 天被拒就自動降回 94 天重跑 ──────────────────
    raw_rows, last_meta, oldest_epoch, all_cached, segments = _collect(
        db, s, e, group_by, triggered_by, force=force)

    norm = [_derive(_normalize(r)) for r in raw_rows]
    norm.sort(key=lambda r: (r.get("business_date") or "",
                             r.get("market_code") or "",
                             r.get("room_type") or ""))

    result: dict[str, Any] = {
        "configured": True,
        "missing": [],
        "range": {"start": s.isoformat(), "end": e.isoformat(),
                  "days": (e - s).days + 1, "segments": len(segments)},
        "group_by": group_by,
        "days": [_to_json(r) for r in norm],
        "summary": _summary(norm),
        "by_market": _aggregate(norm, "market_code") if GROUP_BY_MARKET in group_by else [],
        "by_room_type": _aggregate(norm, "room_type") if GROUP_BY_ROOM_TYPE in group_by else [],
        "notes": _notes(norm, last_meta),
    }

    # 整批資料的新鮮度以**最舊的一段**為準 —— 有一段是 25 分鐘前的快取，
    # 就不能說整份資料是「剛剛抓的」。
    result["source"] = _source(
        last_meta, oldest_epoch, all_cached, len(segments),
        cooldown=_max_cooldown(db, s, e, group_by),
    )
    return result


def _collect(db: Session, s: date, e: date, group_by: list[str],
             triggered_by: str, *, force: bool
             ) -> tuple[list[dict], dict, float, bool, list[tuple[date, date]]]:
    """逐段取數。遇到「區間太長」的 400 錯誤時，自動降到 94 天重跑一次。

    ⚠️ **降級判定刻意保守**：只有在「這一段確實超過 94 天」時才視為區間過長。
       因為 400 也可能代表 30 分鐘限制（Oracle 沒寫違規回哪個碼），
       若不加這個條件，一次限流就會讓系統誤以為 OPERA 是舊版而永久降級。
    """
    for attempt in (1, 2):
        span = current_span_days()
        segments = _split_ranges(s, e, span)
        raw_rows: list[dict] = []
        last_meta: dict = {}
        epochs: list[float] = []
        cached_flags: list[bool] = []
        try:
            for seg_start, seg_end in segments:
                rows, meta, epoch, from_cache = fetch_rows(
                    db, seg_start, seg_end, group_by, triggered_by, force=force)
                raw_rows.extend(rows)
                last_meta = meta or last_meta
                epochs.append(epoch)
                cached_flags.append(from_cache)
        except OhipError as ex:
            seg_len = (segments[0][1] - segments[0][0]).days + 1
            too_long = (ex.status_code == 400
                        and seg_len > FALLBACK_SPAN_DAYS
                        and attempt == 1)
            if too_long and _downgrade_span():
                # 換成 94 天重跑。⚠️ 重跑用的是**不同的**日期參數，
                # 所以不構成「相同請求」，不受 30 分鐘限制。
                continue
            raise

        return (raw_rows, last_meta,
                min(epochs) if epochs else time.time(),
                all(cached_flags) if cached_flags else False,
                segments)

    raise OhipError("取得營收資料失敗：降級重試後仍未成功")


def _max_cooldown(db: Session, s: date, e: date, group_by: list[str]) -> int:
    """整個查詢還要等幾秒才能再取一次 —— 取各段中**最長**的剩餘時間。"""
    remains = [
        ohip_async_cache.cooldown_remaining(db, _rows_cache_key(a, b, group_by))
        for a, b in _split_ranges(s, e)
    ]
    return max(remains) if remains else 0


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """期間合計。比率一律**加權**（SUM/SUM），不是逐日平均。"""
    if not rows:
        return {}

    tot = {k: Decimal(0) for k in
           ("rooms_sold", "available_rooms", "room_revenue", "total_revenue",
            "cancelled_rooms", "arrival_rooms", "departure_rooms")}
    for r in rows:
        for k in tot:
            v = r.get(k)
            if v is not None:
                tot[k] += v

    sold, avail = tot["rooms_sold"], tot["available_rooms"]
    rev = tot["room_revenue"]
    cancelled = tot["cancelled_rooms"]

    return {
        **{k: _f(v) for k, v in tot.items()},
        "other_revenue": _f(tot["total_revenue"] - rev),
        "adr": _f(rev / sold) if sold else None,
        "revpar": _f(rev / avail) if avail else None,
        "occupancy": _f(sold / avail) if avail else None,
        # 取消率：TXT 版算不出來的指標
        "cancel_rate": _f(cancelled / (sold + cancelled)) if (sold + cancelled) else None,
        "days": len(rows),
    }


def _notes(rows: list[dict[str, Any]], meta: dict | None = None) -> list[str]:
    """把「這批資料有哪些欄位其實沒回」如實告訴使用者，而不是默默顯示空白。"""
    notes: list[str] = []

    # ⚠️ 2 MB 靜默截斷：Oracle 會在不通知的情況下砍掉超出的部分。
    #    這裡只能示警，**無法確認**是否真的被截斷（官方沒有提供任何訊號）。
    if (meta or {}).get("truncation_risk"):
        size = (meta or {}).get("response_bytes", 0)
        notes.append(
            f"⚠️ 本次 API 回應大小 {size:,} bytes，已逼近 OPERA 的 2 MB 上限。"
            "超過的部分會被**靜默截斷**（不會報錯），資料可能不完整。"
            "請縮小查詢區間後再查一次，並比對兩次的筆數是否一致。"
        )

    if not rows:
        return notes

    for field, label in [("food_revenue", "餐飲營收 foodRevenue"),
                         ("no_show_rooms", "No-show 房數 noShowRooms")]:
        if all(r.get(field) is None for r in rows):
            notes.append(f"{label}：本次查詢 OPERA 完全沒有回傳此欄位，畫面上顯示為「—」。")

    if any(r.get("cancelled_rooms") is not None for r in rows):
        notes.append("取消房數 cancelledRooms 有值 —— 這是人工上傳的 TXT 報表沒有的指標。")

    return notes


def _source(meta: dict | None, fetched_at: float | None,
            cached: bool, segments: int, cooldown: int = 0) -> dict[str, Any]:
    return {
        "provider":   "OPERA Cloud（OHIP 非同步營收 API）",
        "hotel_id":   settings.OHIP_HOTEL_ID,
        "ext_system_code": settings.OHIP_EXT_SYSTEM_CODE,
        "endpoint":   (meta or {}).get("endpoint", ""),
        "status_code": (meta or {}).get("status_code"),
        "elapsed_ms": (meta or {}).get("elapsed_ms"),
        "poll_count": (meta or {}).get("poll_count"),
        "request_id": (meta or {}).get("request_id", ""),
        "segments":   segments,
        "from_cache": cached,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "fetched_at": (datetime.fromtimestamp(fetched_at).isoformat(timespec="seconds")
                       if fetched_at else None),
        "cache_age_seconds": (int(time.time() - fetched_at) if fetched_at else None),
        "checked_at": twnow().isoformat(timespec="seconds"),

        # ── 區間上限（可能因 OPERA 版本自動降級）──────────────────────────
        "max_span_days": current_span_days(),
        "preferred_span_days": PREFERRED_SPAN_DAYS,
        "span_downgraded": current_span_days() == FALLBACK_SPAN_DAYS,

        # ── 30 分鐘冷卻（前端據此 disable「略過快取重查」）────────────────
        "min_interval_seconds": ohip_async_cache.MIN_INTERVAL_SECONDS,
        "cooldown_remaining_seconds": cooldown,
        "can_force": cooldown <= 0,

        # ── 2 MB 靜默截斷風險 ─────────────────────────────────────────────
        "response_bytes": (meta or {}).get("response_bytes"),
        "truncation_risk": bool((meta or {}).get("truncation_risk")),
    }


def clear_cache(db: Session | None = None) -> int:
    """清掉落地快取。

    ⚠️ 清快取**不會**解除 OPERA 端的 30 分鐘限制 —— 對方是依自己的紀錄判定，
       清完立刻重打仍可能被拒。這個函式只適合用在快取格式改版時。
    """
    if db is None:
        return 0
    return ohip_async_cache.purge(db)
