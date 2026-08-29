"""
營運分析 — 訂房 Pace／Pickup：以訂房日回推的歷史進度分析

建立日期：2026-08-13
規格文件：`docs/SPEC_opera_pace.md`
資料表：`app/models/opera_reservation.py`（**不新增任何資料表或欄位**）

═══════════════════════════════════════════════════════════════════════════
⚠️ 本模組的數字是「回推」出來的，不是當時真正看到的
═══════════════════════════════════════════════════════════════════════════
`opera_reservation_sync._upsert()` 是**整列覆寫、無版本**的 upsert。
所以我們手上只有「每筆訂房現在長什麼樣」，沒有「它在 8/1 那天長什麼樣」。

本模組的作法是用 `booking_date` / `cancellation_date` 兩個時間欄位，
把現在這份資料往回切：

    某訂房在 as_of 這天算在手  ⟺  booking_date <= as_of < cancellation_date

這在「訂了幾間」這件事上是準的（訂房日不會變），但有三個失真：

| 失真 | 說明 |
|------|------|
| 改期 | 訂單從 8/15 改到 8/20，回推會顯示它「一直都是 8/20」 |
| 改房型／改房數 | `night` 列反映的是最新行程，維度別 pickup 會有偏差 |
| 硬刪 | 被 OPERA 從回應移除的訂單留在 DB 成 stale 列（實測未觀察到） |

**這句話必須顯示在畫面上**（`source.note` 會帶過去），不要拿掉。
精確版本要等 `ohip_*_snapshot` 累積足夠天數（見 `readiness()`）。

═══════════════════════════════════════════════════════════════════════════
⚠️ 狀態是取消但沒有取消日期 → 保守排除，不猜
═══════════════════════════════════════════════════════════════════════════
`cancellation_date` 填充率 19%。若 `resv_status` 已是取消類但 `cancellation_date`
為空，**無法定位取消時點**。本模組的處理是：這類訂房在**所有** as_of 都不計入，
並把筆數放進 `unresolved_cancels` 回傳，畫面必須顯示。

猜一個取消日（例如用 last_modified_date）會讓 pickup 憑空多出一批取消，
比誠實地少算更糟。

═══════════════════════════════════════════════════════════════════════════
三個口徑上的堅持（沿用 opera_reservation_service）
═══════════════════════════════════════════════════════════════════════════
① **主指標是房晚（room_nights），不是訂單數** —— 一筆 5 晚的訂單對 Pace 的
   意義是 5，不是 1。
② 比率一律加權（SUM ÷ SUM），不逐筆平均。
③ 金額全程 `Decimal`，輸出前才轉 float。且 `room_revenue` 填充率僅 48%，
   ADR 一律附 `coverage`，畫面必須顯示警語。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.opera_reservation import OhipReservation, OhipReservationNight
from app.models.realtime import OhipInventorySnapshot

# 觀察點（入住日前 N 天）。⚠️ 由大到小＝由遠到近，畫曲線時 X 軸方向就對了。
DEFAULT_LEADS: tuple[int, ...] = (90, 60, 30, 14, 7, 3, 1, 0)

# Pickup 觀察窗（天）
PICKUP_WINDOWS: tuple[int, ...] = (1, 3, 7, 14)

# 可拆的維度 → (資料表, 欄位)。⚠️ 這些是「現在的」維度，回推後有偏差，標參考值。
DIMENSIONS: dict[str, tuple[str, str]] = {
    "market_code": ("night", "market_code"),
    "room_type":   ("night", "room_type"),
    "channel":     ("night", "channel"),
    "rate_code":   ("night", "rate_code"),
    "source_code": ("night", "source_code"),
}

# 與 opera_reservation_service 保持一致 —— 兩邊判定不同會讓驗收恆等式對不上
CANCELLED_MARKERS = ("CANCEL", "NO SHOW", "NOSHOW")

UNCLASSIFIED = "（未填）"

# 單次查詢的入住日區間上限。超過就要求分次查 —— 一次撈兩年會把記憶體吃光。
MAX_RANGE_DAYS = 366

# 快照要累積多少天，Phase 2（精確版）才有意義
SNAPSHOT_READY_DAYS = 60


def _hotel() -> str:
    return settings.OHIP_HOTEL_ID


def _f(v: Any) -> float | None:
    return float(v) if v is not None else None


def _is_cancelled(status: str) -> bool:
    s = (status or "").upper()
    return any(m in s for m in CANCELLED_MARKERS)


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _shift(s: str, days: int) -> str:
    return (_d(s) + timedelta(days=days)).isoformat()


def _check_range(start: str, end: str) -> tuple[str, str]:
    """驗證區間。⚠️ 這裡丟 ValueError，router 轉 400。"""
    a, b = _d(start), _d(end)
    if b < a:
        raise ValueError("結束日不可早於開始日")
    if (b - a).days + 1 > MAX_RANGE_DAYS:
        raise ValueError(f"單次查詢最多 {MAX_RANGE_DAYS} 天，請分次查詢")
    return start, end


# ═══════════════════════════════════════════════════════════════════════════
# 核心：把區間內的 night 列連同訂房的三個時間欄位一次撈進記憶體
# ═══════════════════════════════════════════════════════════════════════════

class _Fact:
    """一列 night ＋ 它所屬訂房的時間欄位。

    ⚠️ 刻意用 __slots__ —— 兩年約 8 萬列，每列一個 dict 會多吃很多記憶體。
    """

    __slots__ = ("stay", "booked", "cancelled", "revenue", "dims")

    def __init__(self, stay: str, booked: str, cancelled: str,
                 revenue: Decimal, dims: dict[str, str]):
        self.stay = stay
        self.booked = booked
        self.cancelled = cancelled   # "" 代表未取消
        self.revenue = revenue
        self.dims = dims


def _load(db: Session, start: str, end: str) -> tuple[list[_Fact], int, int]:
    """撈出入住日落在 [start, end] 的所有 night 列。

    回傳 (facts, unresolved_cancels, missing_booking_date)。

    ⚠️ **一次撈完在記憶體算所有 lead 點**，不要為每個 lead 各查一次 DB ——
       8 個 lead 點 × 366 天會變成 8 次全表掃描。

    ⚠️ `missing_booking_date`（2026-08-13 runtime 測試後補上）：
       `models/opera_reservation.py` 檔頭寫 `bookingDate` 填充率 100%，
       但那是 2 個月 2,375 筆的抽樣。實測 2024-09-01～06 這一段，
       本模組算出 583 房晚、`/opera/reservations/dimension` 算出 593，
       差的 10 筆就是**沒有訂房日**的訂房 —— 沒有訂房日就無法回推，只能排除。
       **這個數字必須跟著回傳並顯示在畫面上**，否則使用者會發現兩頁對不起來
       卻找不到原因（本專案對 coverage 的一貫要求）。
    """
    q = (db.query(OhipReservationNight, OhipReservation)
           .join(OhipReservation,
                 (OhipReservation.confirmation_no
                  == OhipReservationNight.confirmation_no)
                 & (OhipReservation.hotel_id == OhipReservationNight.hotel_id))
           .filter(OhipReservationNight.hotel_id == _hotel(),
                   OhipReservationNight.trx_date >= start,
                   OhipReservationNight.trx_date <= end))

    facts: list[_Fact] = []
    unresolved = 0
    missing_bd = 0
    seen_unresolved: set[str] = set()

    for night, resv in q.all():
        # 狀態是取消但沒有取消日 → 無法定位時點，整筆排除（見檔頭）
        if _is_cancelled(resv.resv_status) and not resv.cancellation_date:
            if resv.confirmation_no not in seen_unresolved:
                seen_unresolved.add(resv.confirmation_no)
                unresolved += 1
            continue
        # 沒有訂房日就無法回推。⚠️ 實測確實存在（見函式 docstring），要計數不能靜默丟掉
        if not resv.booking_date:
            missing_bd += 1
            continue
        facts.append(_Fact(
            stay=night.trx_date,
            booked=resv.booking_date,
            cancelled=resv.cancellation_date or "",
            revenue=night.room_revenue or Decimal(0),
            dims={k: (getattr(night, col, None) or UNCLASSIFIED)
                  for k, (kind, col) in DIMENSIONS.items() if kind == "night"},
        ))
    return facts, unresolved, missing_bd


def _otb_at(facts: Iterable[_Fact], as_of: str) -> tuple[int, Decimal, int]:
    """as_of 這天看到的在手房晚。回傳 (房晚, 營收, 有營收的房晚數)。

    某訂房算在手 ⟺ booking_date <= as_of 且 (未取消 或 cancellation_date > as_of)
    """
    nights = 0
    rev = Decimal(0)
    with_rev = 0
    for f in facts:
        if f.booked > as_of:
            continue
        if f.cancelled and f.cancelled <= as_of:
            continue
        nights += 1
        if f.revenue:
            rev += f.revenue
            with_rev += 1
    return nights, rev, with_rev


def _cov(filled: int, total: int) -> dict[str, Any]:
    return {"filled": filled, "total": total,
            "ratio": (filled / total) if total else None,
            "is_low": bool(total and filled / total < 0.5)}


def _source(note: str) -> dict[str, Any]:
    return {
        "provider": "OPERA Cloud（OHIP rsvasync，已落地）",
        "hotel_id": _hotel(),
        # ⚠️ 這三句會直接顯示在畫面上，是本模組不被誤解的關鍵，不要拿掉
        "population": ("本頁的歷史進度是以「訂房日」回推得出，"
                       "已含後續改期與取消的結果，"
                       "與當時真實看到的數字可能略有差異。"),
        "precision": ("精確版本需累積每日快照（見「快照精確版」分頁）。"),
        "note": note,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ① 資料涵蓋範圍
# ═══════════════════════════════════════════════════════════════════════════

def data_range(db: Session) -> dict[str, Any]:
    """涵蓋範圍 + 無法定位的取消筆數 + 快照就緒度。

    ⚠️ 本模組**含未來資料**。入住日區間是未來導向，
       所以前端用 antd 原生 RangePicker，**不是** StandardRangePicker
       （CLAUDE.md §8.4：未來導向不適用）。
    """
    row = (db.query(func.min(OhipReservationNight.trx_date),
                    func.max(OhipReservationNight.trx_date))
             .filter(OhipReservationNight.hotel_id == _hotel()).one())
    bk = (db.query(func.min(OhipReservation.booking_date))
            .filter(OhipReservation.hotel_id == _hotel(),
                    OhipReservation.booking_date != "").scalar())

    unresolved = (db.query(func.count(OhipReservation.id))
                    .filter(OhipReservation.hotel_id == _hotel(),
                            OhipReservation.cancellation_date == "",
                            func.upper(OhipReservation.resv_status).like("%CANCEL%"))
                    .scalar() or 0)

    today = date.today().isoformat()
    end = row[1]
    return {
        "start": row[0], "end": end,
        "last_past": min(end, today) if end else None,
        # 回推能回到多早，取決於最早的訂房日
        "earliest_booking_date": bk,
        "has_data": bool(end),
        "unresolved_cancels": int(unresolved),
        "snapshot": readiness(db),
        "source": _source("涵蓋範圍取自訂房逐日明細（含未來）。"),
    }


def readiness(db: Session) -> dict[str, Any]:
    """快照累積了幾天 —— 決定 Phase 2（精確版）能不能開。

    ⚠️ 這裡只讀 `ohip_inventory_snapshot`，**不打 OHIP**。
    """
    days = (db.query(func.count(func.distinct(OhipInventorySnapshot.snapshot_date)))
              .filter(OhipInventorySnapshot.hotel_id == _hotel()).scalar() or 0)
    first, last = (db.query(func.min(OhipInventorySnapshot.snapshot_date),
                            func.max(OhipInventorySnapshot.snapshot_date))
                     .filter(OhipInventorySnapshot.hotel_id == _hotel()).one())
    # lead_days < 0 ＝ 回看日，代表這個入住日已經有「最終值」可以當 pickup 曲線終點
    final_days = (db.query(func.count(func.distinct(OhipInventorySnapshot.business_date)))
                    .filter(OhipInventorySnapshot.hotel_id == _hotel(),
                            OhipInventorySnapshot.lead_days < 0).scalar() or 0)
    return {
        "distinct_snapshot_days": int(days),
        "first_snapshot_date": first,
        "last_snapshot_date": last,
        "business_days_with_final": int(final_days),
        "required_days": SNAPSHOT_READY_DAYS,
        "ready": int(days) >= SNAPSHOT_READY_DAYS,
        "remaining_days": max(SNAPSHOT_READY_DAYS - int(days), 0),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ② Booking Curve（單一入住日）
# ═══════════════════════════════════════════════════════════════════════════

def curve(db: Session, *, stay_date: str, compare: str = "weekday",
          max_lead: int = 120) -> dict[str, Any]:
    """單一入住日的訂房曲線：OTB 隨觀察日逐日演進，附去年同期對照。

    🎯 **這是路線 A 最大的價值** —— 去年同期曲線用同一套邏輯就能回推，
       快照路線要等滿一年才有。

    compare：
      - `weekday`（預設）＝去年同一天往前後找最近的**同星期**。飯店的需求
        是跟著星期走的，8/15 週六對 8/15 週四沒有可比性。
      - `date` ＝去年同一個日期。做節慶（固定日期）比較時用。
    """
    _d(stay_date)  # 格式驗證
    ly = _last_year(stay_date, compare)

    cur = _one_curve(db, stay_date, max_lead)
    prv = _one_curve(db, ly, max_lead)

    # 依 lead 對齊兩條曲線
    prv_map = {p["lead_days"]: p for p in prv["points"]}
    points = []
    for p in cur["points"]:
        q = prv_map.get(p["lead_days"])
        ly_n = q["room_nights"] if q else None
        points.append({
            **p,
            "ly_room_nights": ly_n,
            "vs_ly": ((p["room_nights"] - ly_n) / ly_n) if ly_n else None,
            "vs_ly_rooms": (p["room_nights"] - ly_n) if ly_n is not None else None,
        })

    return {
        "stay_date": stay_date,
        "compare": compare,
        "ly_stay_date": ly,
        "points": points,
        "final": cur["final"],
        "ly_final": prv["final"],
        "unresolved_cancels": cur["unresolved"] + prv["unresolved"],
        "missing_booking_date": cur["missing_bd"] + prv["missing_bd"],
        "source": _source(
            f"曲線的每一點＝該觀察日看到的在手房晚。"
            f"去年同期以「{'同星期' if compare == 'weekday' else '同日期'}」對齊。"),
    }


def _last_year(stay_date: str, compare: str) -> str:
    d = _d(stay_date)
    try:
        base = d.replace(year=d.year - 1)
    except ValueError:          # 2/29
        base = d.replace(year=d.year - 1, day=28)
    if compare != "weekday":
        return base.isoformat()
    # 往前後 3 天內找同星期（差距最多 3 天，一定找得到）
    delta = (d.weekday() - base.weekday()) % 7
    if delta > 3:
        delta -= 7
    return (base + timedelta(days=delta)).isoformat()


def _one_curve(db: Session, stay_date: str, max_lead: int) -> dict[str, Any]:
    facts, unresolved, missing_bd = _load(db, stay_date, stay_date)
    today = date.today().isoformat()
    pts = []
    for lead in range(max_lead, -1, -1):
        as_of = _shift(stay_date, -lead)
        # 還沒發生的觀察日沒有意義 —— 未來的入住日只畫到今天為止
        if as_of > today:
            continue
        n, rev, with_rev = _otb_at(facts, as_of)
        pts.append({
            "lead_days": lead, "as_of": as_of, "room_nights": n,
            "room_revenue": _f(rev),
            "adr": _f(rev / with_rev) if with_rev else None,
        })
    final = pts[-1]["room_nights"] if pts else 0
    return {"points": pts, "final": final, "unresolved": unresolved,
            "missing_bd": missing_bd}


# ═══════════════════════════════════════════════════════════════════════════
# ③ OTB 矩陣（主表格）
# ═══════════════════════════════════════════════════════════════════════════

def otb_matrix(db: Session, *, start: str, end: str,
               leads: tuple[int, ...] = DEFAULT_LEADS,
               compare: str = "weekday", as_of: str | None = None,
               window: int = 7) -> dict[str, Any]:
    """入住日 × lead 觀察點的 OTB 矩陣，附去年同期與淨 pickup。

    ⚠️ 觀察日晚於 `as_of` 的格子回 `None`（不是 0）——
       「還沒到那一天」與「那一天是 0」意義完全不同，畫面必須分開呈現。

    ⚠️ `as_of`（2026-08-13 runtime 測試後新增）：預設今天。
       原本整支函式寫死 `date.today()`，導致看歷史區間時 pickup 欄永遠是 0
       （「最近 7 天」對兩年前的入住日當然沒有任何異動）。改為跟隨畫面上的
       「觀察日」，回頭看某個時點的訂房進度才有意義。
    """
    _check_range(start, end)
    if window not in PICKUP_WINDOWS:
        raise ValueError(f"window 必須是 {PICKUP_WINDOWS} 其中之一")
    today = as_of or date.today().isoformat()
    _d(today)

    facts, unresolved, missing_bd = _load(db, start, end)
    by_stay: dict[str, list[_Fact]] = defaultdict(list)
    for f in facts:
        by_stay[f.stay].append(f)

    # 去年同期：一次撈完整段，避免逐日查詢
    ly_start = _last_year(start, compare)
    ly_end = _last_year(end, compare)
    if ly_end < ly_start:
        ly_start, ly_end = ly_end, ly_start
    ly_facts, ly_unresolved, ly_missing_bd = _load(db, ly_start, ly_end)
    ly_by_stay: dict[str, list[_Fact]] = defaultdict(list)
    for f in ly_facts:
        ly_by_stay[f.stay].append(f)

    rows = []
    cur = _d(start)
    last = _d(end)
    while cur <= last:
        s = cur.isoformat()
        fs = by_stay.get(s, [])
        cells: dict[str, int | None] = {}
        for lead in leads:
            as_of = _shift(s, -lead)
            cells[str(lead)] = None if as_of > today else _otb_at(fs, as_of)[0]

        # 目前在手（以今天為觀察日；已過的入住日就是最終值）
        now_as_of = min(s, today)
        n_now, rev_now, with_rev = _otb_at(fs, now_as_of)

        # 淨 pickup（以 as_of 為右端點，往前 window 天）
        p7 = _pickup_of(fs, _shift(today, -window), today)

        ly_s = _last_year(s, compare)
        ly_fs = ly_by_stay.get(ly_s, [])
        # 去年「同提前期」—— 拿今年目前的提前期去看去年的同一個提前期
        lead_now = (cur - _d(today)).days
        ly_as_of = _shift(ly_s, -lead_now) if lead_now > 0 else ly_s
        n_ly = _otb_at(ly_fs, ly_as_of)[0]

        rows.append({
            "stay_date": s,
            "weekday": cur.weekday(),          # 0=週一 … 6=週日
            # ⚠️ 飯店口徑的假日是**週五、週六**（隔天不用上班的那兩晚），
            #    週日晚上屬平日價。2026-08-13 runtime 測試發現原本寫 `>= 4`
            #    把週日也算進去，與註解不符，已修正。
            "is_weekend": cur.weekday() in (4, 5),
            "lead_days_now": lead_now,
            "otb": cells,
            "room_nights": n_now,
            "room_revenue": _f(rev_now),
            "adr": _f(rev_now / with_rev) if with_rev else None,
            "pickup_net": p7["net"],
            "pickup_new": p7["gross_new"],
            "pickup_cancels": p7["cancels"],
            "ly_stay_date": ly_s,
            "ly_room_nights": n_ly,
            "vs_ly": ((n_now - n_ly) / n_ly) if n_ly else None,
        })
        cur += timedelta(days=1)

    with_rev_total = sum(1 for f in facts if f.revenue)
    return {
        "range": {"start": start, "end": end},
        "leads": list(leads),
        "compare": compare,
        "as_of": today,
        "window": window,
        "rows": rows,
        "summary": {
            "room_nights": sum(r["room_nights"] for r in rows),
            "ly_room_nights": sum(r["ly_room_nights"] for r in rows),
            "pickup_net": sum(r["pickup_net"] for r in rows),
        },
        "unresolved_cancels": unresolved + ly_unresolved,
        "missing_booking_date": missing_bd + ly_missing_bd,
        "revenue_coverage": _cov(with_rev_total, len(facts)),
        "source": _source(
            f"以 {today} 的眼光回看。空白格＝該觀察日還沒到（不是 0）。"
            "「vs 去年」比的是同一個提前期，不是去年的最終值。"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ④ Pickup（新增／取消／淨）
# ═══════════════════════════════════════════════════════════════════════════

def _pickup_of(facts: Iterable[_Fact], t1: str, t2: str) -> dict[str, int]:
    """(t1, t2] 之間的 pickup 組成。

    ⚠️ 區間是**左開右閉** —— 這樣相鄰兩段不會重複計算同一筆。
    """
    new = can = 0
    for f in facts:
        if t1 < f.booked <= t2:
            new += 1
        if f.cancelled and t1 < f.cancelled <= t2:
            can += 1
    return {"gross_new": new, "cancels": can, "net": new - can}


def pickup(db: Session, *, start: str, end: str, window: int = 7,
           as_of: str | None = None) -> dict[str, Any]:
    """逐入住日的 pickup 組成。

    🎯 **淨值相同但組成不同的日子，處置完全不同** ——
       「新增 5」與「新增 20 取消 15」都是淨 +5，但後者代表需求不穩，
       所以 gross_new 與 cancels 一定要分開列，不能只給淨值。

    ⚠️ 回傳同時附 `verify`：OTB(t2) − OTB(t1) 應等於 net。
       不相等代表回推邏輯有 bug，會寫進 warnings。
    """
    _check_range(start, end)
    if window not in PICKUP_WINDOWS:
        raise ValueError(f"window 必須是 {PICKUP_WINDOWS} 其中之一")
    t2 = as_of or date.today().isoformat()
    _d(t2)
    t1 = _shift(t2, -window)

    facts, unresolved, missing_bd = _load(db, start, end)
    by_stay: dict[str, list[_Fact]] = defaultdict(list)
    for f in facts:
        by_stay[f.stay].append(f)

    rows = []
    warnings: list[str] = []
    cur, last = _d(start), _d(end)
    while cur <= last:
        s = cur.isoformat()
        fs = by_stay.get(s, [])
        p = _pickup_of(fs, t1, t2)
        n1 = _otb_at(fs, t1)[0]
        n2 = _otb_at(fs, t2)[0]
        ok = (n2 - n1) == p["net"]
        if not ok:
            warnings.append(f"{s}：OTB 差值 {n2 - n1} ≠ 淨 pickup {p['net']}")
        rows.append({
            "stay_date": s, "weekday": cur.weekday(),
            **p,
            "otb_before": n1, "otb_after": n2, "verified": ok,
        })
        cur += timedelta(days=1)

    return {
        "range": {"start": start, "end": end},
        "window": window, "from": t1, "to": t2,
        "rows": rows,
        "summary": {
            "gross_new": sum(r["gross_new"] for r in rows),
            "cancels": sum(r["cancels"] for r in rows),
            "net": sum(r["net"] for r in rows),
        },
        "unresolved_cancels": unresolved,
        "missing_booking_date": missing_bd,
        # ⚠️ 恆等式自我檢查（規格 §九驗收標準第一項）
        "verify": {"all_passed": not warnings, "warnings": warnings[:20]},
        "source": _source(
            f"統計區間為 {t1}（不含）～ {t2}（含）新增與取消的房晚。"
            "新增與取消分開列 —— 淨值相同不代表狀況相同。"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ 維度別 Pickup
# ═══════════════════════════════════════════════════════════════════════════

def pickup_dimension(db: Session, *, start: str, end: str,
                     dimension: str = "market_code", window: int = 7,
                     as_of: str | None = None) -> dict[str, Any]:
    """依維度拆分 pickup。

    ⚠️ **這是參考值。** 維度取自 night 列的**現在**狀態，若訂單中途改過房型
       或通路，回推時會算到新的維度上。畫面必須標「參考值」。
    """
    _check_range(start, end)
    if dimension not in DIMENSIONS:
        raise ValueError(f"不支援的維度：{dimension}")
    if window not in PICKUP_WINDOWS:
        raise ValueError(f"window 必須是 {PICKUP_WINDOWS} 其中之一")
    t2 = as_of or date.today().isoformat()
    _d(t2)
    t1 = _shift(t2, -window)

    facts, unresolved, missing_bd = _load(db, start, end)
    agg: dict[str, dict[str, int]] = defaultdict(
        lambda: {"gross_new": 0, "cancels": 0, "net": 0, "otb_after": 0})
    filled = 0
    for f in facts:
        key = f.dims.get(dimension) or UNCLASSIFIED
        if key != UNCLASSIFIED:
            filled += 1
        a = agg[key]
        if t1 < f.booked <= t2:
            a["gross_new"] += 1
        if f.cancelled and t1 < f.cancelled <= t2:
            a["cancels"] += 1
        if f.booked <= t2 and not (f.cancelled and f.cancelled <= t2):
            a["otb_after"] += 1
    for a in agg.values():
        a["net"] = a["gross_new"] - a["cancels"]

    # ⚠️ key 是次要鍵：net 平手時兩個引擎的順序會不同。
    rows = sorted(({"key": k, **v} for k, v in agg.items()),
                  key=lambda x: (-x["net"], x["key"]))
    return {
        "range": {"start": start, "end": end},
        "dimension": dimension, "window": window, "from": t1, "to": t2,
        "rows": rows,
        "unresolved_cancels": unresolved,
        "missing_booking_date": missing_bd,
        "coverage": _cov(filled, len(facts)),
        "is_reference_only": True,
        "source": _source(
            "⚠️ 維度取自訂房「目前」的房型／通路。若訂單中途改過，"
            "回推會算在新的維度上 —— 這裡是參考值，不是精確歸因。"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ⑥ 單日明細（Drawer 用）
# ═══════════════════════════════════════════════════════════════════════════

def day_detail(db: Session, *, stay_date: str, window: int = 7,
               as_of: str | None = None) -> dict[str, Any]:
    """某入住日在觀察窗內新增／取消了哪些訂單（CLAUDE.md §7 Drawer 明細）。

    ⚠️ 本模組資料源非 Ragic，§7 的 `ragic_url` 不適用，回傳空字串。
    """
    _d(stay_date)
    t2 = as_of or date.today().isoformat()
    t1 = _shift(t2, -window)

    q = (db.query(OhipReservationNight, OhipReservation)
           .join(OhipReservation,
                 (OhipReservation.confirmation_no
                  == OhipReservationNight.confirmation_no)
                 & (OhipReservation.hotel_id == OhipReservationNight.hotel_id))
           .filter(OhipReservationNight.hotel_id == _hotel(),
                   OhipReservationNight.trx_date == stay_date))

    added, cancelled = [], []
    for night, resv in q.all():
        if _is_cancelled(resv.resv_status) and not resv.cancellation_date:
            continue
        item = {
            "confirmation_no": resv.confirmation_no,
            "booking_date": resv.booking_date,
            "cancellation_date": resv.cancellation_date or "",
            "cancellation_reason_code": resv.cancellation_reason_code or "",
            "arrival": resv.arrival, "departure": resv.departure,
            "nights": resv.nights, "lead_days": resv.lead_days,
            "resv_status": resv.resv_status,
            "market_code": night.market_code, "room_type": night.room_type,
            "rate_code": night.rate_code, "channel": night.channel,
            "room_revenue": _f(night.room_revenue),
            "ragic_url": "",   # 非 Ragic 來源
        }
        if t1 < resv.booking_date <= t2:
            added.append(item)
        if resv.cancellation_date and t1 < resv.cancellation_date <= t2:
            cancelled.append(item)

    added.sort(key=lambda x: x["booking_date"], reverse=True)
    cancelled.sort(key=lambda x: x["cancellation_date"], reverse=True)
    return {
        "stay_date": stay_date, "window": window, "from": t1, "to": t2,
        "added": added, "cancelled": cancelled,
        "summary": {"gross_new": len(added), "cancels": len(cancelled),
                    "net": len(added) - len(cancelled)},
        "source": _source("列出觀察窗內新增與取消的訂單明細。"),
    }
