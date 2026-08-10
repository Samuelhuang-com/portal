"""
營運分析 — 市場區隔／房型別趨勢分析

建立日期：2026-08-07
資料表：`ohip_revenue_history`（來源：OHIP API，**不是** TXT 上傳）

═══════════════════════════════════════════════════════════════════════════
這一頁要回答的三個問題（主管視角）
═══════════════════════════════════════════════════════════════════════════
1. **結構**：這段期間，錢是從哪些市場區隔／房型來的？佔比多少？
2. **趨勢**：逐月看下來，哪個區隔在成長、哪個在萎縮？
3. **YoY**：跟去年同期比，是變好還是變差？（這是「35% 算高還是低」的唯一答案）

═══════════════════════════════════════════════════════════════════════════
兩個計算口徑上的堅持（與既有分析服務一致）
═══════════════════════════════════════════════════════════════════════════
① **比率一律加權（SUM ÷ SUM），不是逐日平均。**
   ADR = 期間房租總額 ÷ 期間售出房晚。
   用「逐日 ADR 取平均」會讓一間都沒賣的日子跟滿房的日子權重相同。

② **可售房 = physical − OOO**，與 `opera_analysis_service` / `opera_revenue.py`
   的既有規則一致。不可直接拿 physical 當分母。

⚠️ **一個必須在畫面上說清楚的限制**
   `market_code` 是**貴飯店在 OPERA 自己設定的分類**，語意不是通用的。
   它與 TXT 報表的「散客扣房／散客不扣房／團體扣房／團體不扣房」
   **不是同一套分類，不能互相對照**。本服務不做任何映射猜測。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.opera_segment import OhipRevenueHistory

DIM_MARKET = "market_code"
DIM_ROOM_TYPE = "room_type"
VALID_DIMS = {DIM_MARKET, DIM_ROOM_TYPE}

UNCLASSIFIED = "（未分類）"


def _d(v: Any) -> Decimal:
    """⚠️ 金額全程 Decimal。用 float 累加一年會差到幾塊錢。"""
    if v is None:
        return Decimal(0)
    return v if isinstance(v, Decimal) else Decimal(str(v))


def _f(v: Decimal | None) -> float | None:
    return float(v) if v is not None else None


def data_range(db: Session) -> dict[str, Any]:
    """資料實際涵蓋的起迄。

    ⚠️ 這個值要給前端當 `StandardRangePicker` 的 `anchor`（CLAUDE.md §8.2）——
       本模組的資料同樣落後現實（增量排程一天跑一次、且刻意不含今天），
       用 `dayjs()` 當基準會讓「本月」選到還沒有資料的日子，看起來像資料缺漏。
    """
    hotel_id = settings.OHIP_HOTEL_ID
    row = (db.query(func.min(OhipRevenueHistory.business_date),
                    func.max(OhipRevenueHistory.business_date))
             .filter(OhipRevenueHistory.hotel_id == hotel_id)
             .one())
    return {"start": row[0], "end": row[1], "has_data": bool(row[1])}


def _fetch(db: Session, start: str, end: str) -> list[OhipRevenueHistory]:
    hotel_id = settings.OHIP_HOTEL_ID
    return (db.query(OhipRevenueHistory)
              .filter(OhipRevenueHistory.hotel_id == hotel_id,
                      OhipRevenueHistory.business_date >= start,
                      OhipRevenueHistory.business_date <= end)
              .all())


def _blank() -> dict[str, Decimal]:
    return {k: Decimal(0) for k in
            ("rooms_sold", "available_rooms", "room_revenue", "total_revenue",
             "cancelled_rooms", "arrival_rooms")}


def _add(acc: dict[str, Decimal], r: OhipRevenueHistory) -> None:
    phys = _d(r.physical_rooms)
    ooo = _d(r.ooo_rooms)
    acc["available_rooms"] += (phys - ooo)     # ⚠️ 可售房 = physical − OOO
    acc["rooms_sold"] += _d(r.rooms_sold)
    acc["room_revenue"] += _d(r.room_revenue)
    acc["total_revenue"] += _d(r.total_revenue)
    acc["cancelled_rooms"] += _d(r.cancelled_rooms)
    acc["arrival_rooms"] += _d(r.arrival_rooms)


def _derive(acc: dict[str, Decimal]) -> dict[str, Any]:
    """⚠️ 比率**最後才算**（加權，非逐日平均）。"""
    sold, avail = acc["rooms_sold"], acc["available_rooms"]
    rev, cancelled = acc["room_revenue"], acc["cancelled_rooms"]
    out: dict[str, Any] = {k: _f(v) for k, v in acc.items()}
    out["adr"] = _f(rev / sold) if sold else None
    out["revpar"] = _f(rev / avail) if avail else None
    out["occupancy"] = _f(sold / avail) if avail else None
    out["cancel_rate"] = _f(cancelled / (sold + cancelled)) if (sold + cancelled) else None
    return out


def _yoy(cur: float | None, prev: float | None) -> float | None:
    """年增率。⚠️ 去年為 0 或缺值時回 None，**不回 0 也不回 100%** ——
    「去年沒有」與「持平」是完全不同的事。"""
    if cur is None or prev in (None, 0):
        return None
    return (cur - prev) / abs(prev)


def _shift_year(iso: str, years: int = -1) -> str:
    d = date.fromisoformat(iso)
    try:
        return d.replace(year=d.year + years).isoformat()
    except ValueError:
        return d.replace(year=d.year + years, day=28).isoformat()


def analyze(db: Session, *, start: str, end: str, dimension: str = DIM_MARKET,
            compare_yoy: bool = True) -> dict[str, Any]:
    """區間內依 `dimension` 分組的結構、逐月趨勢與 YoY。

    Args:
        dimension: `market_code` 或 `room_type`
        compare_yoy: 是否一併撈去年同期（會多一次 DB 查詢，不多打 API）
    """
    if dimension not in VALID_DIMS:
        dimension = DIM_MARKET

    rows = _fetch(db, start, end)

    # ── ① 結構：依維度彙總 ──────────────────────────────────────────────────
    by_dim: dict[str, dict[str, Decimal]] = defaultdict(_blank)
    # ── ② 趨勢：維度 × 月份 ────────────────────────────────────────────────
    by_dim_month: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(_blank)
    by_month: dict[str, dict[str, Decimal]] = defaultdict(_blank)
    total = _blank()

    for r in rows:
        key = (getattr(r, dimension) or "") or UNCLASSIFIED
        month = (r.business_date or "")[:7]
        _add(by_dim[key], r)
        _add(by_dim_month[(key, month)], r)
        _add(by_month[month], r)
        _add(total, r)

    prev_by_dim: dict[str, dict[str, Decimal]] = defaultdict(_blank)
    prev_total = _blank()
    if compare_yoy:
        for r in _fetch(db, _shift_year(start), _shift_year(end)):
            key = (getattr(r, dimension) or "") or UNCLASSIFIED
            _add(prev_by_dim[key], r)
            _add(prev_total, r)

    total_rev = total["room_revenue"]

    segments = []
    for key, acc in by_dim.items():
        d = _derive(acc)
        d[dimension] = key
        d["share"] = _f(acc["room_revenue"] / total_rev) if total_rev else None
        if compare_yoy:
            prev = _derive(prev_by_dim[key]) if key in prev_by_dim else None
            d["prev_room_revenue"] = prev["room_revenue"] if prev else None
            d["prev_adr"] = prev["adr"] if prev else None
            d["yoy_room_revenue"] = _yoy(d["room_revenue"], d["prev_room_revenue"])
            d["yoy_adr"] = _yoy(d["adr"], d["prev_adr"])
            # ⚠️ 去年完全沒有這個區隔 → 標記出來，不要顯示成「成長 ∞」
            d["is_new"] = key not in prev_by_dim
        segments.append(d)
    segments.sort(key=lambda x: (x.get("room_revenue") or 0), reverse=True)

    months = sorted(by_month.keys())
    trend = []
    for m in months:
        d = _derive(by_month[m])
        d["month"] = m
        d["by_dimension"] = {
            k: _f(by_dim_month[(k, m)]["room_revenue"])
            for k in by_dim.keys() if (k, m) in by_dim_month
        }
        trend.append(d)

    summary = _derive(total)
    if compare_yoy:
        prev_sum = _derive(prev_total)
        summary["prev_room_revenue"] = prev_sum["room_revenue"]
        summary["prev_adr"] = prev_sum["adr"]
        summary["prev_occupancy"] = prev_sum["occupancy"]
        summary["yoy_room_revenue"] = _yoy(summary["room_revenue"], prev_sum["room_revenue"])
        summary["yoy_adr"] = _yoy(summary["adr"], prev_sum["adr"])
        summary["yoy_occupancy"] = _yoy(summary["occupancy"], prev_sum["occupancy"])

    return {
        "range": {"start": start, "end": end},
        "yoy_range": ({"start": _shift_year(start), "end": _shift_year(end)}
                      if compare_yoy else None),
        "dimension": dimension,
        "summary": summary,
        "segments": segments,
        "trend": trend,
        "row_count": len(rows),
        "source": {
            "provider": "OPERA Cloud（OHIP 非同步營收 API，已落地）",
            "table": "ohip_revenue_history",
            "hotel_id": settings.OHIP_HOTEL_ID,
            # ⚠️ 這一句會直接顯示在畫面上。同一個模組裡混了兩種來源，
            #    不標示清楚會被當成 TXT 上傳的資料看待。
            "note": ("本頁資料來自 OPERA Cloud API，**不是**人工上傳的 TXT 報表。"
                     "市場區隔（Market Code）是貴飯店在 OPERA 自行設定的分類，"
                     "與 TXT 的「散客／團體」四類**不是同一套分類，不可互相對照**。"),
        },
        "data_range": data_range(db),
    }


def dimension_options(db: Session, *, dimension: str = DIM_MARKET) -> list[str]:
    """該維度出現過哪些值（給前端篩選器）。"""
    if dimension not in VALID_DIMS:
        dimension = DIM_MARKET
    col = getattr(OhipRevenueHistory, dimension)
    rows = (db.query(col).distinct()
              .filter(OhipRevenueHistory.hotel_id == settings.OHIP_HOTEL_ID)
              .all())
    return sorted({(r[0] or "") or UNCLASSIFIED for r in rows})
