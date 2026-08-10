"""
即時營運 — 即時房況（同步版 inventoryStatistics）

規格書：docs/SPEC_realtime_operations.md
串接實測：docs/OHIP_INTEGRATION.md §4

⚠️ 與 `/opera/*` 既有模組的關係
────────────────────────────────────────────────────────────────────────────
**完全獨立，不共用任何資料表、不寫入 `opera_*`。**
既有模組是「人工上傳 TXT → 落地 → 分析」，資料會落後現實數天；
本服務是「即時打 API」，兩者是不同時點的資料，畫面上必須分開標示。

⚠️ 本服務拿不到營收
────────────────────────────────────────────────────────────────────────────
2026-08-06 實測確認：`getInventoryStatistics` **不回傳 ADR / RevPAR / 營收**
（`HouseAverageDailyRateYN`、`HouseRevPARYN` 列在 spec enum 但沒有實作）。
所以即時區塊只呈現房況面，營收面一律留在既有的 TXT 落地資料。

⚠️ 這是「現在看到的那一天」，不是「那一天當時的樣子」
────────────────────────────────────────────────────────────────────────────
API 給的是 OPERA 此刻的記錄。今天查 8/1，拿到的是現在的 8/1。
因此 **pickup / booking pace 分析做不出來**，除非每天自行存快照。
本服務刻意不存快照 —— 那是另一個決策，不該在原型階段偷偷做掉。
"""
from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import twnow
from app.models.realtime import OhipCallLog
from app.services import ohip_client
from app.services.ohip_client import OhipError

# ── 快取（記憶體，5 分鐘）────────────────────────────────────────────────────
# 房況變化不快，而 OHIP 按呼叫量計費。同一組參數 5 分鐘內只實際打一次。
CACHE_TTL_SECONDS = 300

_cache_lock = threading.Lock()
_cache: dict[str, tuple[float, dict[str, Any]]] = {}

# 預設視野：今日 + 未來 14 天（規格書 §8.2）
DEFAULT_DAYS_AHEAD = 14

REPORT_CODE = "RoomsAvailabilitySummary"

# 要向 API 索取的指標。⚠️ name 與 value 必須成對，否則回傳只有 SequenceId。
_PARAMETERS = [
    "HouseInventoryRoomsYN",
    "HouseAvailRoomsYN",
    "HouseOOOYN",
    "HouseRoomsSoldYN",
    "HouseArrRoomsYN",
    "HouseDepRoomsYN",
    "HousePeopleInHouseYN",
    "HouseCompRoomsYN",
    "HouseHouseUseRoomsYN",
    "HouseDayUseRoomYN",
]

# OHIP 回傳 code → Portal 內部欄位名
_CODE_MAP = {
    "InventoryRooms":   "inventory_rooms",
    "RoomsSold":        "rooms_sold",
    "AvailableRooms":   "available_rooms",
    "OutOfOrderRooms":  "ooo_rooms",
    "ArrivalRooms":     "arrival_rooms",
    "DepartureRooms":   "departure_rooms",
    "PeopleInHouse":    "people_in_house",
    "CompRooms":        "comp_rooms",
    "HouseUseRooms":    "house_use_rooms",
    "DayuseRoom":       "day_use_rooms",
    "OverBookingRooms": "overbooking_rooms",
    "SellLimitRooms":   "sell_limit_rooms",
}


# ── 呼叫日誌 ─────────────────────────────────────────────────────────────────

def _log_call(db: Session, *, endpoint: str, hotel_id: str,
              date_start: str, date_end: str, meta: dict | None,
              success: bool, error: str = "", triggered_by: str = "") -> None:
    """記錄一次**實際發出**的呼叫。快取命中不記 —— 那次沒有真的呼叫。"""
    try:
        db.add(OhipCallLog(
            endpoint=endpoint,
            hotel_id=hotel_id,
            date_start=date_start,
            date_end=date_end,
            status_code=(meta or {}).get("status_code", 0),
            elapsed_ms=(meta or {}).get("elapsed_ms", 0),
            request_id=(meta or {}).get("request_id", "") or "",
            success=success,
            error=error[:2000],
            triggered_by=triggered_by[:120],
        ))
        db.commit()
    except Exception:
        # 日誌寫入失敗不能影響主流程
        db.rollback()


# ── 解析 ─────────────────────────────────────────────────────────────────────

def _parse(payload: Any) -> dict[str, Any]:
    """把 OHIP 的巢狀回傳攤平。

    ⚠️ 最外層是 list 不是 dict（實測）：
        [ { "statistics": [ { statCategoryCode, statCode, statisticDate: [...] } ] } ]
    """
    blocks: list[dict] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                blocks.extend(item.get("statistics") or [])
    elif isinstance(payload, dict):
        blocks.extend(payload.get("statistics") or [])

    house_days: list[dict[str, Any]] = []
    room_types: list[dict[str, Any]] = []

    for b in blocks:
        cat = b.get("statCategoryCode")
        rows = []
        for r in (b.get("statisticDate") or []):
            vals = {
                _CODE_MAP[i["code"]]: i.get("value")
                for i in (r.get("inventory") or [])
                if i.get("code") in _CODE_MAP
            }
            if not vals:
                continue
            vals["business_date"] = r.get("statisticDate")
            vals["is_weekend"] = bool(r.get("weekendDate"))
            vals["occupancy"] = _occupancy(vals)
            rows.append(vals)

        if cat == "HotelCode":
            house_days = rows
        elif cat == "HotelRoomCode":
            room_types.append({
                "room_type": b.get("statCode"),
                "description": b.get("description") or "",
                "days": rows,
            })

    return {"house": house_days, "room_types": room_types}


def _occupancy(v: dict[str, Any]) -> float | None:
    """住房率 API 不回傳，自行計算。

    分母照 `opera_revenue.py` 註解 1 的既有規則：可售房 = 總房數 − OOO。
    不可以直接用 InventoryRooms（本次實測 OOO=0 只是碰巧相同）。
    """
    inv = v.get("inventory_rooms")
    ooo = v.get("ooo_rooms") or 0
    sold = v.get("rooms_sold")
    if inv is None or sold is None:
        return None
    denom = inv - ooo
    if denom <= 0:
        return None
    return round(sold / denom, 4)


# ── 主查詢 ───────────────────────────────────────────────────────────────────

def get_live_status(db: Session, *, days_ahead: int = DEFAULT_DAYS_AHEAD,
                    force: bool = False, triggered_by: str = "") -> dict[str, Any]:
    """今日 + 未來 N 天的即時房況。

    回傳一律附帶 `source` 區塊，供畫面標示「這筆數字是什麼時候、從哪裡來的」。
    憑證未設定時**不拋錯**，回 `configured: False` 讓畫面優雅降級。
    """
    if not ohip_client.is_configured():
        return {
            "configured": False,
            "missing": ohip_client.missing_settings(),
            "house": [],
            "room_types": [],
            "source": _source_meta(cached=False, meta=None, fetched_at=None),
        }

    hotel_id = settings.OHIP_HOTEL_ID
    start = date.today()
    end = start + timedelta(days=max(days_ahead, 0))

    # 上限 62 天是 API 硬限制
    if (end - start).days + 1 > 62:
        end = start + timedelta(days=61)

    cache_key = f"{hotel_id}|{start}|{end}|{REPORT_CODE}"

    if not force:
        with _cache_lock:
            hit = _cache.get(cache_key)
            if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
                cached_at, data = hit
                out = dict(data)
                out["source"] = _source_meta(
                    cached=True, meta=data.get("_meta"), fetched_at=cached_at,
                )
                out.pop("_meta", None)
                return out

    endpoint = f"/inv/v1/hotels/{hotel_id}/inventoryStatistics"
    params: list[tuple[str, str]] = [
        ("dateRangeStart", start.isoformat()),
        ("dateRangeEnd", end.isoformat()),
        ("reportCode", REPORT_CODE),
    ]
    for p in _PARAMETERS:
        params.append(("parameterName", p))
        params.append(("parameterValue", "Y"))     # ⚠️ 必須成對

    try:
        payload, meta = ohip_client.get(endpoint, params=params, hotel_id=hotel_id)
    except OhipError as e:
        _log_call(db, endpoint=endpoint, hotel_id=hotel_id,
                  date_start=start.isoformat(), date_end=end.isoformat(),
                  meta={"status_code": e.status_code or 0,
                        "request_id": e.request_id or ""},
                  success=False, error=str(e), triggered_by=triggered_by)
        raise

    _log_call(db, endpoint=endpoint, hotel_id=hotel_id,
              date_start=start.isoformat(), date_end=end.isoformat(),
              meta=meta, success=True, triggered_by=triggered_by)

    parsed = _parse(payload)
    fetched_at = time.time()

    # ⚠️ 快取的內容必須**由最終回傳的同一個 dict 複製**，不可只快取 `parsed`。
    #    2026-08-05 白畫面事故就是這樣來的：當時只把 `parsed`（僅 house／room_types）
    #    存進快取，5 分鐘內的第二次請求走快取分支，回傳的 `configured` 是 undefined，
    #    前端判斷式 `!data.configured` 誤判成「尚未設定」，接著讀 `data.missing.join()`
    #    而丟出 TypeError —— 由於營運分析 Dashboard 直接嵌用本面板，
    #    整個 React 樹被卸載，變成整頁空白。
    #    規則：**快取分支與直接回傳的欄位必須完全一致**。
    result = {
        "configured": True,
        "missing": [],
        "house": parsed["house"],
        "room_types": parsed["room_types"],
    }

    cached_payload = dict(result)
    cached_payload["_meta"] = meta
    with _cache_lock:
        _cache[cache_key] = (fetched_at, cached_payload)

    result["source"] = _source_meta(cached=False, meta=meta, fetched_at=fetched_at)
    return result


def get_business_date(db: Session, *, triggered_by: str = "") -> dict[str, Any]:
    """OPERA 的當前營業日。

    比自家 DB 反推可靠 —— 這正是 CLAUDE.md §8.2 要求 `StandardRangePicker`
    的 `anchor` 用「資料最後一天」的權威來源。
    """
    if not ohip_client.is_configured():
        return {"configured": False, "business_date": None}

    hotel_id = settings.OHIP_HOTEL_ID
    endpoint = f"/bof/v1/hotels/{hotel_id}/businessDate"
    try:
        payload, meta = ohip_client.get(endpoint, hotel_id=hotel_id)
    except OhipError as e:
        _log_call(db, endpoint=endpoint, hotel_id=hotel_id,
                  date_start="", date_end="",
                  meta={"status_code": e.status_code or 0,
                        "request_id": e.request_id or ""},
                  success=False, error=str(e), triggered_by=triggered_by)
        return {"configured": True, "business_date": None, "error": str(e)}

    _log_call(db, endpoint=endpoint, hotel_id=hotel_id,
              date_start="", date_end="", meta=meta, success=True,
              triggered_by=triggered_by)

    hotels = (payload or {}).get("hotels") or []
    bd = hotels[0].get("businessDate") if hotels else None
    return {"configured": True, "business_date": bd}


# ── 給畫面用的來源標示 ───────────────────────────────────────────────────────

def _source_meta(*, cached: bool, meta: dict | None,
                 fetched_at: float | None) -> dict[str, Any]:
    """畫面上「API 執行資料」那一列所需的全部欄位。"""
    return {
        "provider":       "OPERA Cloud（OHIP API）",
        "gateway":        settings.OHIP_GATEWAY_URL,
        "hotel_id":       settings.OHIP_HOTEL_ID,
        "endpoint":       (meta or {}).get("endpoint", ""),
        "status_code":    (meta or {}).get("status_code"),
        "elapsed_ms":     (meta or {}).get("elapsed_ms"),
        "request_id":     (meta or {}).get("request_id", ""),
        "from_cache":     cached,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        # 資料實際從 API 抓下來的時間（快取命中時為當初那一次）
        "fetched_at":     (datetime.fromtimestamp(fetched_at).isoformat(timespec="seconds")
                           if fetched_at else None),
        "cache_age_seconds": (int(time.time() - fetched_at) if fetched_at else None),
        "checked_at":     twnow().isoformat(timespec="seconds"),
        "token":          ohip_client.token_status(),
    }


def get_call_logs(db: Session, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """API 呼叫紀錄（供日誌頁）"""
    q = db.query(OhipCallLog).order_by(OhipCallLog.id.desc())
    total = q.count()
    rows = q.offset(offset).limit(min(limit, 500)).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "called_at": r.called_at.isoformat(timespec="seconds") if r.called_at else "",
                "endpoint": r.endpoint,
                "hotel_id": r.hotel_id,
                "date_start": r.date_start,
                "date_end": r.date_end,
                "status_code": r.status_code,
                "elapsed_ms": r.elapsed_ms,
                "request_id": r.request_id,
                "success": r.success,
                "error": r.error,
                "triggered_by": r.triggered_by,
            }
            for r in rows
        ],
    }


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
