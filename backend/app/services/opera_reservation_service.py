"""
營運分析 — 訂房分析：查詢與統計

建立日期：2026-08-07
資料表：`app/models/opera_reservation.py`

═══════════════════════════════════════════════════════════════════════════
⚠️ 分析母體與 `/opera/guest` 不同 —— 這是本模組所有數字的前提
═══════════════════════════════════════════════════════════════════════════
`/opera/guest` 的母體是 **已離店的住客**（TXT Departure 報表）。
本模組的母體是 **所有訂房**，包含還沒住的與被取消的。

**同一個維度在兩邊出現不同數字是正確的**，不是誰對誰錯。
`source.note` 會把這句話帶到畫面上 —— 不要拿掉。

═══════════════════════════════════════════════════════════════════════════
⚠️ 填充率（coverage）必須跟著數字一起回傳
═══════════════════════════════════════════════════════════════════════════
實測填充率：`companyName` **15%**、`children` 55%、`channel` 77%、
`travelAgentName` 76%。

**低填充率的維度做成排行榜會嚴重偏頗** —— 例如「公司貢獻排行」只涵蓋 15% 的訂單，
看起來卻像是全部。所以每個維度統計都回傳 `coverage`（有值筆數 ÷ 母體），
畫面必須顯示。這不是可選的裝飾。

═══════════════════════════════════════════════════════════════════════════
三個口徑上的堅持
═══════════════════════════════════════════════════════════════════════════
① **比率一律加權（SUM ÷ SUM）**，不是逐筆平均。
② **取消率的分母是「所有訂房」**（含取消），不是「未取消的訂房」。
③ 金額全程 `Decimal`，輸出前才轉 float。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.opera_reservation import (OhipBlock, OhipBlockAllocation,
                                          OhipReservation, OhipReservationNight)

# 訂房前置期分桶（天）。⚠️ 上界含在該桶內。
LEAD_BUCKETS: list[tuple[str, int, int]] = [
    ("當天", 0, 0), ("1–3 天", 1, 3), ("4–7 天", 4, 7), ("8–14 天", 8, 14),
    ("15–30 天", 15, 30), ("31–60 天", 31, 60), ("61–90 天", 61, 90),
    ("91–180 天", 91, 180), ("180 天以上", 181, 10_000),
]

LOS_BUCKETS: list[tuple[str, int, int]] = [
    ("1 晚", 1, 1), ("2 晚", 2, 2), ("3 晚", 3, 3), ("4–6 晚", 4, 6),
    ("7–13 晚", 7, 13), ("14–29 晚", 14, 29), ("30 晚以上", 30, 10_000),
]

# 可分組的維度 → (資料表, 欄位)
DIMENSIONS = {
    "market_code":       ("night", "market_code"),
    "rate_code":         ("night", "rate_code"),
    "source_code":       ("night", "source_code"),
    "channel":           ("night", "channel"),
    "room_type":         ("night", "room_type"),
    "travel_agent_name": ("resv", "travel_agent_name"),
    "company_name":      ("resv", "company_name"),
    "group_name":        ("resv", "group_name"),
    "nationality":       ("resv", "nationality"),
}

# ⚠️ 取消的訂房不該計入「賣了幾間」。實測狀態值含 'CANCELLED'。
CANCELLED_MARKERS = ("CANCEL", "NO SHOW", "NOSHOW")

UNCLASSIFIED = "（未填）"


def _hotel() -> str:
    return settings.OHIP_HOTEL_ID


def _f(v: Any) -> float | None:
    return float(v) if v is not None else None


def _is_cancelled(status: str) -> bool:
    s = (status or "").upper()
    return any(m in s for m in CANCELLED_MARKERS)


def data_range(db: Session) -> dict[str, Any]:
    """資料涵蓋範圍。⚠️ 給前端當 `StandardRangePicker` 的 `anchor`（CLAUDE.md §8.2）。

    注意本模組**含未來資料**（在手訂房），所以 `end` 會是未來日期 ——
    這與其他模組不同，anchor 應該用 `last_past`（今天與資料最後一天取小）。
    """
    row = (db.query(func.min(OhipReservation.arrival),
                    func.max(OhipReservation.arrival))
             .filter(OhipReservation.hotel_id == _hotel()).one())
    today = date.today().isoformat()
    end = row[1]
    return {
        "start": row[0], "end": end,
        # 已發生的最後一天 —— 過去導向的分析用這個當 anchor
        "last_past": min(end, today) if end else None,
        "has_data": bool(end),
        "reservations": db.query(OhipReservation).filter(
            OhipReservation.hotel_id == _hotel()).count(),
    }


def _base(db: Session, start: str, end: str, *, by_booking: bool = False):
    col = OhipReservation.booking_date if by_booking else OhipReservation.arrival
    return (db.query(OhipReservation)
              .filter(OhipReservation.hotel_id == _hotel(),
                      col >= start, col <= end))


def _coverage(rows: list, attr: str) -> dict[str, Any]:
    """某個欄位有值的比例。⚠️ 這個數字必須顯示在畫面上（見檔頭）。"""
    total = len(rows)
    filled = sum(1 for r in rows if getattr(r, attr, None) not in (None, "", 0))
    return {
        "filled": filled, "total": total,
        "ratio": (filled / total) if total else None,
        # 低於這個門檻的維度，畫面應該加警語而不是直接畫排行榜
        "is_low": bool(total and (filled / total) < 0.5),
    }


# ── ① 訂房前置期（TXT 永遠做不到）──────────────────────────────────────────

def booking_window(db: Session, *, start: str, end: str) -> dict[str, Any]:
    """依**到達日**篩選，看這些訂房是提前多久訂的。

    🎯 這是 TXT（Departure 報表）**永遠做不到**的分析 —— 它沒有任何訂房日期欄位。
    """
    rows = _base(db, start, end).all()
    buckets = {name: {"bucket": name, "reservations": 0, "room_nights": 0,
                      "cancelled": 0} for name, _, _ in LEAD_BUCKETS}
    lead_values: list[int] = []

    for r in rows:
        if r.lead_days is None:
            continue
        lead_values.append(r.lead_days)
        for name, lo, hi in LEAD_BUCKETS:
            if lo <= r.lead_days <= hi:
                b = buckets[name]
                b["reservations"] += 1
                b["room_nights"] += (r.nights or 0) * (r.no_of_rooms or 1)
                if _is_cancelled(r.resv_status) or r.cancellation_date:
                    b["cancelled"] += 1
                break

    total = sum(b["reservations"] for b in buckets.values())
    out = []
    for name, _, _ in LEAD_BUCKETS:
        b = dict(buckets[name])
        b["share"] = (b["reservations"] / total) if total else None
        # 每一桶的取消率 —— 「越早訂越容易取消嗎」就是看這一欄
        b["cancel_rate"] = (b["cancelled"] / b["reservations"]
                            if b["reservations"] else None)
        out.append(b)

    lead_values.sort()
    n = len(lead_values)
    return {
        "range": {"start": start, "end": end, "basis": "arrival"},
        "buckets": out,
        "stats": {
            "count": n,
            "median": lead_values[n // 2] if n else None,
            "p25": lead_values[n // 4] if n else None,
            "p75": lead_values[n * 3 // 4] if n else None,
            "mean": (sum(lead_values) / n) if n else None,
            "max": lead_values[-1] if n else None,
        },
        "coverage": _coverage(rows, "booking_date"),
        "source": _source("本頁依**到達日**篩選，看的是「這些訂房提前多久訂的」。"),
    }


# ── ② 取消分析（TXT 永遠做不到）────────────────────────────────────────────

def cancellations(db: Session, *, start: str, end: str) -> dict[str, Any]:
    """取消率、取消原因碼分布、以及「訂多久前的單比較容易取消」。

    🎯 TXT 是 Departure 報表 —— **本質上只有已離店的訂房**，取消的根本不會出現。
    ⚠️ 取消率的分母是**所有訂房**（含取消），不是未取消的訂房。
    """
    rows = _base(db, start, end).all()
    total = len(rows)
    cancelled = [r for r in rows if _is_cancelled(r.resv_status) or r.cancellation_date]

    by_reason: dict[str, int] = defaultdict(int)
    lost_nights = 0
    notice_days: list[int] = []
    for r in cancelled:
        by_reason[(r.cancellation_reason_code or "") or UNCLASSIFIED] += 1
        lost_nights += (r.nights or 0) * (r.no_of_rooms or 1)
        # 取消提前期：距離原訂到達日還有幾天才取消（負數＝到達後才取消）
        if r.cancellation_date and r.arrival:
            try:
                notice_days.append(
                    (date.fromisoformat(r.arrival)
                     - date.fromisoformat(r.cancellation_date)).days)
            except ValueError:
                pass

    reasons = sorted(
        ({"reason_code": k, "count": v,
          "share": (v / len(cancelled)) if cancelled else None}
         for k, v in by_reason.items()),
        key=lambda x: x["count"], reverse=True)

    notice_days.sort()
    m = len(notice_days)
    return {
        "range": {"start": start, "end": end, "basis": "arrival"},
        "summary": {
            "reservations": total,
            "cancelled": len(cancelled),
            "cancel_rate": (len(cancelled) / total) if total else None,
            "lost_room_nights": lost_nights,
            "median_notice_days": notice_days[m // 2] if m else None,
        },
        "reasons": reasons,
        "coverage": _coverage(rows, "cancellation_reason_code"),
        "source": _source(
            "取消率的分母是**所有訂房**（含取消）。"
            "⚠️「住客與通路分析」看不到取消 —— 那份資料來自 Departure 報表，"
            "本質上只有已離店的訂房。"),
    }


# ── ③ 在手訂房 on-the-books（TXT 永遠做不到）────────────────────────────────

def on_the_books(db: Session, *, days_ahead: int = 90,
                 dimension: str = "market_code") -> dict[str, Any]:
    """未來每一天目前已經訂了多少（房晚與營收），並依維度拆分。

    🎯 TXT 只有已離店的資料，**未來一天都看不到**。
    ⚠️ 已取消的訂房不計入。
    """
    today = date.today().isoformat()
    end = (date.fromisoformat(today).toordinal() + max(days_ahead, 1))
    end_s = date.fromordinal(end).isoformat()

    dim_kind, dim_col = DIMENSIONS.get(dimension, DIMENSIONS["market_code"])
    q = (db.query(OhipReservationNight, OhipReservation)
           .join(OhipReservation,
                 (OhipReservation.confirmation_no == OhipReservationNight.confirmation_no)
                 & (OhipReservation.hotel_id == OhipReservationNight.hotel_id))
           .filter(OhipReservationNight.hotel_id == _hotel(),
                   OhipReservationNight.trx_date >= today,
                   OhipReservationNight.trx_date <= end_s))

    by_date: dict[str, dict[str, Any]] = {}
    by_dim: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"room_nights": 0, "room_revenue": Decimal(0)})
    filled = total = 0

    for night, resv in q.all():
        if _is_cancelled(resv.resv_status) or resv.cancellation_date:
            continue
        total += 1
        key = (getattr(night, dim_col, None) if dim_kind == "night"
               else getattr(resv, dim_col, None))
        if key:
            filled += 1
        key = key or UNCLASSIFIED

        d = by_date.setdefault(night.trx_date, {
            "business_date": night.trx_date, "room_nights": 0,
            "room_revenue": Decimal(0), "by_dimension": defaultdict(int)})
        d["room_nights"] += 1
        rev = night.room_revenue or Decimal(0)
        d["room_revenue"] += rev
        d["by_dimension"][key] += 1

        by_dim[key]["room_nights"] += 1
        by_dim[key]["room_revenue"] += rev

    days = []
    for k in sorted(by_date):
        d = by_date[k]
        days.append({
            "business_date": d["business_date"],
            "room_nights": d["room_nights"],
            "room_revenue": _f(d["room_revenue"]),
            "adr": _f(d["room_revenue"] / d["room_nights"]) if d["room_nights"] else None,
            "by_dimension": dict(d["by_dimension"]),
        })

    segs = sorted(
        ({dimension: k, "room_nights": v["room_nights"],
          "room_revenue": _f(v["room_revenue"]),
          "adr": _f(v["room_revenue"] / v["room_nights"]) if v["room_nights"] else None}
         for k, v in by_dim.items()),
        key=lambda x: x["room_nights"], reverse=True)

    return {
        "range": {"start": today, "end": end_s, "days_ahead": days_ahead},
        "dimension": dimension,
        "days": days,
        "segments": segs,
        "summary": {
            "room_nights": sum(d["room_nights"] for d in days),
            "room_revenue": _f(sum((by_dim[k]["room_revenue"] for k in by_dim),
                                   Decimal(0))),
        },
        "coverage": {"filled": filled, "total": total,
                     "ratio": (filled / total) if total else None,
                     "is_low": bool(total and filled / total < 0.5)},
        "source": _source(
            "「在手訂房」＝此刻已經訂下、尚未入住的房晚。已取消的不計入。"
            "⚠️ 這是 TXT 報表**永遠看不到**的視角 —— 它只有已離店的資料。"),
    }


# ── ④ 維度統計 ─────────────────────────────────────────────────────────────

def dimension_stats(db: Session, *, start: str, end: str,
                    dimension: str = "market_code") -> dict[str, Any]:
    """依維度統計房晚與營收。⚠️ 一律附 `coverage`。"""
    dim_kind, dim_col = DIMENSIONS.get(dimension, DIMENSIONS["market_code"])
    q = (db.query(OhipReservationNight, OhipReservation)
           .join(OhipReservation,
                 (OhipReservation.confirmation_no == OhipReservationNight.confirmation_no)
                 & (OhipReservation.hotel_id == OhipReservationNight.hotel_id))
           .filter(OhipReservationNight.hotel_id == _hotel(),
                   OhipReservationNight.trx_date >= start,
                   OhipReservationNight.trx_date <= end))

    acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"room_nights": 0, "room_revenue": Decimal(0),
                 "reservations": set(), "cancelled": 0})
    filled = total = 0
    for night, resv in q.all():
        total += 1
        key = (getattr(night, dim_col, None) if dim_kind == "night"
               else getattr(resv, dim_col, None))
        if key:
            filled += 1
        key = key or UNCLASSIFIED
        a = acc[key]
        cancelled = _is_cancelled(resv.resv_status) or bool(resv.cancellation_date)
        if cancelled:
            a["cancelled"] += 1
        else:
            a["room_nights"] += 1
            a["room_revenue"] += (night.room_revenue or Decimal(0))
        a["reservations"].add(night.confirmation_no)

    total_rev = sum((a["room_revenue"] for a in acc.values()), Decimal(0))
    rows = []
    for k, a in acc.items():
        rows.append({
            dimension: k,
            "room_nights": a["room_nights"],
            "reservations": len(a["reservations"]),
            "room_revenue": _f(a["room_revenue"]),
            "adr": _f(a["room_revenue"] / a["room_nights"]) if a["room_nights"] else None,
            "share": _f(a["room_revenue"] / total_rev) if total_rev else None,
            "cancelled_nights": a["cancelled"],
        })
    rows.sort(key=lambda x: (x["room_revenue"] or 0), reverse=True)

    cov = {"filled": filled, "total": total,
           "ratio": (filled / total) if total else None,
           "is_low": bool(total and filled / total < 0.5)}
    note = ("本頁母體是**所有訂房**（含未來、含取消），"
            "與「住客與通路分析」的**已離店住客**不同，數字本來就不會一樣。")
    if cov["is_low"]:
        note += (f"⚠️ 這個維度只有 {cov['ratio']:.0%} 的資料有值，"
                 "排行結果會偏頗，請不要當成全貌。")
    return {"range": {"start": start, "end": end}, "dimension": dimension,
            "rows": rows, "coverage": cov, "source": _source(note)}


# ── ⑤ LOS 分桶 ─────────────────────────────────────────────────────────────

def los_buckets(db: Session, *, start: str, end: str) -> dict[str, Any]:
    rows = [r for r in _base(db, start, end).all()
            if not (_is_cancelled(r.resv_status) or r.cancellation_date)]
    buckets = {n: {"bucket": n, "reservations": 0, "room_nights": 0}
               for n, _, _ in LOS_BUCKETS}
    for r in rows:
        if not r.nights:
            continue
        for n, lo, hi in LOS_BUCKETS:
            if lo <= r.nights <= hi:
                buckets[n]["reservations"] += 1
                buckets[n]["room_nights"] += r.nights * (r.no_of_rooms or 1)
                break
    total = sum(b["reservations"] for b in buckets.values())
    out = []
    for n, _, _ in LOS_BUCKETS:
        b = dict(buckets[n])
        b["share"] = (b["reservations"] / total) if total else None
        out.append(b)
    return {"range": {"start": start, "end": end}, "buckets": out,
            "source": _source("已取消的訂房不計入。")}


# ── ⑥ 團體 pickup ──────────────────────────────────────────────────────────

def block_pickup(db: Session, *, start: str, end: str) -> dict[str, Any]:
    """團體配房 vs 實際成交。

    🎯 `originalRooms`／`currentRooms`／`pickupRooms` 是 API 直接給的，
       TXT 只有 `block_code`／`group_name`，**沒有任何配房與成交數字**。

    ⚠️ 實測樣本的 `cutOffDays` 全是 0 —— 若整批都是 0，
       代表這間飯店沒有在用 cut-off，本頁的 cut-off 欄位就沒有意義。
       回傳 `cutoff_in_use` 讓畫面自行決定要不要顯示該欄。
    """
    blocks = (db.query(OhipBlock)
                .filter(OhipBlock.hotel_id == _hotel(),
                        OhipBlock.start_date <= end,
                        OhipBlock.end_date >= start).all())
    ids = [b.block_id for b in blocks]
    allocs = (db.query(OhipBlockAllocation)
                .filter(OhipBlockAllocation.hotel_id == _hotel(),
                        OhipBlockAllocation.block_id.in_(ids)).all()
              if ids else [])

    per_block: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"original": 0, "current": 0, "pickup": 0,
                 "room_revenue": Decimal(0)})
    for a in allocs:
        p = per_block[a.block_id]
        p["original"] += a.original_rooms or 0
        p["current"] += a.current_rooms or 0
        p["pickup"] += a.pickup_rooms or 0
        p["room_revenue"] += (a.room_revenue or Decimal(0))

    rows = []
    for b in blocks:
        p = per_block.get(b.block_id, {"original": 0, "current": 0,
                                       "pickup": 0, "room_revenue": Decimal(0)})
        rows.append({
            "block_id": b.block_id, "block_code": b.block_code,
            "block_name": b.block_name, "status": b.status,
            "block_type": b.block_type, "market_code": b.market_code,
            "source_code": b.source_code, "booking_medium": b.booking_medium,
            "company_name": b.company_name,
            "start_date": b.start_date, "end_date": b.end_date,
            "cut_off_days": b.cut_off_days,
            "original_rooms": p["original"], "current_rooms": p["current"],
            "pickup_rooms": p["pickup"],
            # 🎯 pickup 率：實際成交 ÷ 目前配房
            "pickup_rate": (p["pickup"] / p["current"]) if p["current"] else None,
            # 未售房＝目前配房 − 成交，cut-off 時會釋出
            "unsold_rooms": max(p["current"] - p["pickup"], 0),
            "room_revenue": _f(p["room_revenue"]),
            "cancellation_code": b.cancellation_code,
            "cancellation_date": b.cancellation_date,
        })
    rows.sort(key=lambda x: (x["current_rooms"] or 0), reverse=True)

    tot_cur = sum(r["current_rooms"] for r in rows)
    tot_pick = sum(r["pickup_rooms"] for r in rows)
    cutoff_vals = [b.cut_off_days for b in blocks if b.cut_off_days is not None]

    return {
        "range": {"start": start, "end": end},
        "blocks": rows,
        "summary": {
            "block_count": len(rows),
            "original_rooms": sum(r["original_rooms"] for r in rows),
            "current_rooms": tot_cur, "pickup_rooms": tot_pick,
            "pickup_rate": (tot_pick / tot_cur) if tot_cur else None,
            "unsold_rooms": max(tot_cur - tot_pick, 0),
            "room_revenue": _f(sum((per_block[b]["room_revenue"] for b in per_block),
                                   Decimal(0))),
            "cancelled_blocks": sum(1 for r in rows if r["cancellation_date"]),
        },
        # ⚠️ 全是 0 代表這間飯店沒在用 cut-off，畫面應隱藏該欄而不是顯示一整排 0
        "cutoff_in_use": bool(cutoff_vals and any(v for v in cutoff_vals)),
        "source": _source(
            "配房與成交數字由 OPERA 直接提供，不是推算的。"
            "TXT 報表只有團體代號與名稱，**沒有任何配房數字**。"),
    }


def _source(note: str) -> dict[str, Any]:
    return {
        "provider": "OPERA Cloud（OHIP rsvasync／blkasync，已落地）",
        "hotel_id": _hotel(),
        # ⚠️ 這句話會直接顯示在畫面上，是本模組不被誤解的關鍵
        "population": ("本模組的母體是**所有訂房**（含未來、含取消）；"
                       "「住客與通路分析」的母體是**已離店的住客**（TXT Departure 報表）。"
                       "兩者不是同一份資料的兩個版本，數字不同是正常的。"),
        "note": note,
    }
