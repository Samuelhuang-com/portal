"""
即時營運 — 與「營運分析」逐欄比對

規格書：docs/SPEC_realtime_operations.md
串接實測：docs/OHIP_INTEGRATION.md §6

目的
────
在把任何既有模組改成吃 API 之前，先證明**同一天、同一個欄位，兩邊數字一致**。
不一致就要先查清原因，不能直接切換。

比對雙方
────────
| 側 | 來源 | 特性 |
|----|------|------|
| API 房況 | 同步版 `inventoryStatistics` | 即時 |
| API 營收 | **非同步版** `revenueInventoryStatistics` | 同步版沒有營收，必須另打一支 |
| TXT | `opera_revenue_daily`（is_current=1） | 人工上傳落地 |

⚠️ 四個比對時必須知道的前提
────────────────────────────────────────────────────────────────────────────
1. **API 給的是「現在看到的那一天」**，TXT 是「匯出當下的那一天」。
   若那一天之後還有異動（改房、取消、加房），兩邊本來就會不同 ——
   差異不等於錯誤，要看差異的方向與大小。

2. **本頁每次比對會呼叫兩支 API**（同步版房況 + 非同步版營收）。
   營收若取不到不會讓整個比對失敗，房況那部分仍有價值。

3. **`roomRevenue` 與 `totalRevenue` 都列出來比。**
   TXT 的 `REVENUE` 對應哪一個尚未確認 —— 這正是本頁要回答的問題。
   兩者差額是房租以外的雜項收入。

4. **record_type 一律取 History**。Forecast 是 TXT 的預測列，
   與 API 的即時房況不是同一件事。
   四類 `*_DEDUCT_REVENUE` 拆分 API 確定沒有，仍標 `api_unavailable`。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.opera_revenue import RECORD_TYPE_HISTORY, OperaRevenueDaily
from app.services import ohip_client
from app.services import realtime_revenue_service as RS
from app.services import realtime_status_service as LS
from app.services.ohip_client import OhipError

# ── 欄位對應表 ───────────────────────────────────────────────────────────────
# (顯示名稱, API 欄位, TXT 欄位, 是否為整數)
# API 欄位為 None ⇒ 該欄位 API 拿不到，只呈現 TXT 值並標示原因。
FIELD_MAP: list[tuple[str, str | None, str, bool]] = [
    ("總房數",       "inventory_rooms", "inventory_rooms", True),
    ("售出房",       "rooms_sold",      "sold_rooms",      True),
    ("可售房",       "available_rooms", "available_rooms", True),
    ("OOO 房",       "ooo_rooms",       "ooo_rooms",       True),
    ("到達房數",     "arrival_rooms",   "arrival_rooms",   True),
    ("離店房數",     "departure_rooms", "departure_rooms", True),
    ("在店人數",     "people_in_house", "no_persons",      True),
    ("招待房",       "comp_rooms",      "complimentary_rooms", True),
    ("自用房",       "house_use_rooms", "house_use_rooms", True),
    ("Day use 房",   "day_use_rooms",   "day_use_rooms",   True),
    # ── 營收：來自**非同步版** API（2026-08-06 起可比對）──
    # ⚠️ `roomRevenue` 與 `totalRevenue` 都列出來 ——
    #    TXT 的 `REVENUE` 對應哪一個**尚未確認**，這正是本頁要回答的問題。
    ("營收（API=roomRevenue）",  "room_revenue",  "revenue", False),
    ("營收（API=totalRevenue）", "total_revenue", "revenue", False),
    # ── 以下 API 確定拿不到 ──
    ("散客扣房營收", None,              "individual_deduct_revenue", False),
    ("散客不扣房營收", None,            "individual_non_deduct_revenue", False),
    ("團體扣房營收", None,              "group_deduct_revenue", False),
    ("團體不扣房營收", None,            "group_non_deduct_revenue", False),
    ("No show 房",   None,              "no_show_rooms",   True),
]

# API 側單次查詢上限
MAX_SPAN_DAYS = 62


def _to_num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _fetch_api_days(db: Session, days_back: int, days_ahead: int,
                    triggered_by: str = "") -> tuple[dict[str, dict], dict]:
    """向 API 取指定區間的全館逐日資料，回傳 {business_date: row} 與 source meta。

    ⚠️ 這裡刻意**不走** `realtime_status_service` 的 5 分鐘快取 ——
    比對是查證行為，必須拿到當下真值，不能用幾分鐘前的快照。
    """
    end = date.today() + timedelta(days=days_ahead)
    start = date.today() - timedelta(days=days_back)

    if (end - start).days + 1 > MAX_SPAN_DAYS:
        start = end - timedelta(days=MAX_SPAN_DAYS - 1)

    hotel_id = settings.OHIP_HOTEL_ID
    params: list[tuple[str, str]] = [
        ("dateRangeStart", start.isoformat()),
        ("dateRangeEnd", end.isoformat()),
        ("reportCode", LS.REPORT_CODE),
    ]
    for p in LS._PARAMETERS:
        params.append(("parameterName", p))
        params.append(("parameterValue", "Y"))   # ⚠️ 必須成對

    payload, meta = ohip_client.get(
        f"/inv/v1/hotels/{hotel_id}/inventoryStatistics",
        params=params, hotel_id=hotel_id,
    )
    parsed = LS._parse(payload)
    by_date = {r["business_date"]: r for r in parsed["house"] if r.get("business_date")}
    meta["date_start"] = start.isoformat()
    meta["date_end"] = end.isoformat()

    # ── 營收：另打一次**非同步版** API 合併進來 ────────────────────────────────
    # 同步版沒有營收（2026-08-06 實測四個 reportCode 全滅），
    # 所以比對營收欄位必須額外呼叫非同步版。這會讓本頁的 API 用量變成兩倍，
    # 但比對本來就是低頻的查證行為，值得。
    # ⚠️ 2026-08-07 改用 `RS.fetch_rows`（走落地快取）而不是 `RS._fetch`（直打）。
    #    原設計是「比對是查證行為，必須拿當下真值」，但 Oracle 對 async 端點
    #    強制相同條件最短間隔 30 分鐘 —— **「每次都拿當下真值」在物理上做不到**。
    #    連按兩次重新比對會被 OPERA 拒絕，比拿到 20 分鐘前的快取更糟。
    #    房況（同步版）那半仍然是每次直打，不受影響。
    try:
        rev_rows, _rev_meta, _epoch, _cached = RS.fetch_rows(
            db, start, end, [], triggered_by)
        for raw in rev_rows:
            r = RS._normalize(raw)
            d = r.get("business_date")
            if not d:
                continue
            tgt = by_date.setdefault(d, {"business_date": d})
            tgt["room_revenue"] = float(r["room_revenue"]) if r["room_revenue"] is not None else None
            tgt["total_revenue"] = float(r["total_revenue"]) if r["total_revenue"] is not None else None
        meta["revenue_included"] = True
    except (OhipError, RS.CooldownActive) as e:
        # 營收拿不到不該讓整個比對失敗 —— 房況那部分仍然有價值
        meta["revenue_included"] = False
        meta["revenue_error"] = str(e)

    return by_date, meta


def compare(db: Session, *, days_back: int = 30, days_ahead: int = 0,
            property_code: str = "", tolerance: float = 0.0,
            triggered_by: str = "") -> dict[str, Any]:
    """逐日、逐欄比對 API 與 TXT。

    Args:
        days_back / days_ahead: 相對今天的區間
        property_code: TXT 側的 property 篩選；空字串代表不限
        tolerance: 容許誤差（絕對值）。0 代表要求完全相同

    Returns:
        `rows`（逐日逐欄）＋ `summary`（統計）＋ `source`（API 執行資料）
    """
    if not ohip_client.is_configured():
        return {
            "configured": False,
            "missing": ohip_client.missing_settings(),
            "rows": [], "summary": {}, "source": None,
        }

    try:
        api_days, meta = _fetch_api_days(db, days_back, days_ahead, triggered_by)
    except OhipError as e:
        LS._log_call(db, endpoint="/inv/v1/.../inventoryStatistics（比對）",
                     hotel_id=settings.OHIP_HOTEL_ID,
                     date_start="", date_end="",
                     meta={"status_code": e.status_code or 0,
                           "request_id": e.request_id or ""},
                     success=False, error=str(e), triggered_by=triggered_by)
        raise

    LS._log_call(db, endpoint=meta.get("endpoint", ""),
                 hotel_id=settings.OHIP_HOTEL_ID,
                 date_start=meta.get("date_start", ""),
                 date_end=meta.get("date_end", ""),
                 meta=meta, success=True, triggered_by=triggered_by)

    # ── TXT 側 ────────────────────────────────────────────────────────────────
    q = (
        db.query(OperaRevenueDaily)
        .filter(OperaRevenueDaily.is_current == 1)
        .filter(OperaRevenueDaily.record_type == RECORD_TYPE_HISTORY)
        .filter(OperaRevenueDaily.business_date >= meta["date_start"])
        .filter(OperaRevenueDaily.business_date <= meta["date_end"])
    )
    if property_code:
        q = q.filter(OperaRevenueDaily.property_code == property_code)
    txt_days = {r.business_date: r for r in q.all()}

    # ── 逐日比對 ──────────────────────────────────────────────────────────────
    all_dates = sorted(set(api_days) | set(txt_days))
    rows: list[dict[str, Any]] = []

    n_match = n_diff = n_api_only = n_txt_only = n_unavailable = 0

    for d in all_dates:
        a = api_days.get(d)
        t = txt_days.get(d)

        if a and not t:
            coverage = "api_only"
            n_api_only += 1
        elif t and not a:
            coverage = "txt_only"
            n_txt_only += 1
        else:
            coverage = "both"

        fields: list[dict[str, Any]] = []
        day_has_diff = False

        for label, api_key, txt_key, is_int in FIELD_MAP:
            txt_val = _to_num(getattr(t, txt_key, None)) if t else None

            if api_key is None:
                fields.append({
                    "label": label, "api": None, "txt": txt_val,
                    "diff": None, "status": "api_unavailable",
                })
                n_unavailable += 1
                continue

            api_val = _to_num(a.get(api_key)) if a else None

            if api_val is None or txt_val is None:
                status, diff = "missing", None
            else:
                diff = api_val - txt_val
                if abs(diff) <= tolerance:
                    status = "match"
                    n_match += 1
                else:
                    status = "diff"
                    n_diff += 1
                    day_has_diff = True

            fields.append({
                "label": label,
                "api": int(api_val) if (api_val is not None and is_int) else api_val,
                "txt": int(txt_val) if (txt_val is not None and is_int) else txt_val,
                "diff": diff,
                "status": status,
            })

        rows.append({
            "business_date": d,
            "coverage": coverage,
            "has_diff": day_has_diff,
            "fields": fields,
        })

    comparable = n_match + n_diff
    return {
        "configured": True,
        "missing": [],
        "range": {"start": meta["date_start"], "end": meta["date_end"]},
        "rows": rows,
        "summary": {
            "days_total": len(all_dates),
            "days_both": sum(1 for r in rows if r["coverage"] == "both"),
            "days_api_only": n_api_only,
            "days_txt_only": n_txt_only,
            "days_with_diff": sum(1 for r in rows if r["has_diff"]),
            "fields_match": n_match,
            "fields_diff": n_diff,
            "fields_api_unavailable": n_unavailable,
            "match_rate": round(n_match / comparable, 4) if comparable else None,
            "tolerance": tolerance,
        },
        "source": {
            "provider": "OPERA Cloud（OHIP API）",
            "hotel_id": settings.OHIP_HOTEL_ID,
            "endpoint": meta.get("endpoint", ""),
            "status_code": meta.get("status_code"),
            "elapsed_ms": meta.get("elapsed_ms"),
            "request_id": meta.get("request_id", ""),
            "from_cache": False,          # 比對一律即時取數，不走快取
            "fetched_at": datetime.fromtimestamp(
                meta.get("called_at_epoch", 0)).isoformat(timespec="seconds"),
            "txt_source": "opera_revenue_daily（is_current=1，record_type=History）",
        },
        "notes": [
            "API 給的是「現在看到的那一天」，TXT 是「匯出當下的那一天」；"
            "若該日之後仍有異動，兩邊本來就會不同，差異不等於錯誤。",
            "營收類欄位 API 不回傳，一律標示為「API 無此資料」，不計入差異統計。",
            "TXT 側固定取 record_type=History；Forecast 是預測列，與即時房況不是同一件事。",
            "營收來自**非同步版** API（同步版沒有營收），因此本頁每次比對會呼叫兩支 API。",
            "`roomRevenue` 與 `totalRevenue` 都列出來 —— TXT 的 `REVENUE` 對應哪一個尚未確認，"
            "這正是本頁要回答的問題。",
        ],
    }
