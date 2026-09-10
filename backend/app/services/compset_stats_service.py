"""
競品分析 — 統計與指標

建立日期：2026-09-09
規格書：`docs/SPEC_compset_analysis.md` §7

═══════════════════════════════════════════════════════════════════════════
六條指標規則
═══════════════════════════════════════════════════════════════════════════
1. **⭐ 一家一天只能算一次（SOURCE_PRIORITY，D16）**
   唯一鍵含 `source`，所以同一格可能同時有 `serpapi` 與 `csv` 兩列。
   **兩列都算進中位數 ＝ 同一家被算兩次，中位數直接歪掉**，而且看起來完全正常。
   一律先用 `SOURCE_PRIORITY` 挑一列（SerpApi 優先），再開始算。

2. **⭐ 中位數排除自己**（分子分母不可以是同一家）與 `is_sold_out='yes'`
   （沒有價就沒有價）。

   ⚠️ **`unknown` 有價格時仍然算進中位數**（2026-09-09 修正）。
      一度寫成「`unknown` 也排除」，但 B／C 級（地點查詢）的每一列都是 `unknown`
      —— 那條規則會讓**三分之二的產品完全算不出指數**，而且畫面上只會顯示
      「沒有資料」，看不出是規則寫錯。
      D13 真正要防的是「**沒看到的飯店不可以當成有房**」，而沒看到的飯店
      根本不會寫列（`compset_fetch_service` 規則），所以那個風險不存在。
      一家在地點查詢裡**帶著價格出現**，就代表它那天有房。
      `unknown_count` 保留為資料品質訊號，畫面標「遠期資料，滿房狀態未知」。

3. **⭐ 稅前與含稅兩種指數都算**（D11）。
   實測各家稅費結構不同（+15.5%／+5%／+0%），單一口徑一定會誤導。
   畫面預設顯示稅前（排除各家服務費政策差異），可切換為含稅（旅客實付）。

4. **⭐ 排名用含稅價，不用稅前價。**
   理由有二：①含稅價是旅客實際看到、實際付的，排名的商業意義在這裡；
   ②`price_pretax` **不保證存在**（地點查詢第 2 頁全部沒有），
   用稅前排名會讓大半 B／C 級資料排不出來。
   ⚠️ 所以「指數用稅前、排名用含稅」是刻意的，不是漏改。

5. **樣本不足要跟數字一起顯示**（比照 `project_opera_reservation_module`：
   填充率必須跟數字一起顯示）。`sample_count < MIN_SAMPLE` 時
   `is_low_sample=True`，畫面標灰並附註。

6. **`compset_rate_daily` 是快取不是來源**，任何時候都必須能重算。
   數字怪怪的第一件事是 `recompute_daily()`，不是改那張表。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import twnow
from app.models.compset_analysis import (SOURCE_PRIORITY, CompsetHotel,
                                         CompsetRateDaily,
                                         CompsetRateSnapshot)

logger = logging.getLogger(__name__)

SOLD_YES, SOLD_NO, SOLD_UNKNOWN = "yes", "no", "unknown"

# 少於這個家數就標「樣本不足」。3 是中位數還有意義的最低門檻
# （2 家的中位數等於平均，1 家等於那一家）。
MIN_SAMPLE = 3

BASIS_PRETAX = "pretax"
BASIS_GROSS = "gross"


# ══════════════════════════════════════════════════════════════════════════
# 純函式
# ══════════════════════════════════════════════════════════════════════════
def pick_by_source(rows: Iterable[CompsetRateSnapshot]) -> dict[int, CompsetRateSnapshot]:
    """
    ⭐ 一家一天只留一列（規則 1）。

    同一格可能有 `serpapi` 與 `csv` 兩列；照 `SOURCE_PRIORITY` 取優先度最高的。
    未列在 `SOURCE_PRIORITY` 裡的來源排在最後（不是丟掉 —— 有資料總比沒有好）。
    """
    order = {src: i for i, src in enumerate(SOURCE_PRIORITY)}
    best: dict[int, CompsetRateSnapshot] = {}
    for row in rows:
        hid = row.compset_hotel_id
        cur = best.get(hid)
        if cur is None or order.get(row.source, 99) < order.get(cur.source, 99):
            best[hid] = row
    return best


def _f(value: Any) -> float | None:
    """Numeric → float。⚠️ PG 回 Decimal、SQLite 回 float，統一成 float 再算。"""
    return None if value is None else float(value)


def _counts_in_median(row: CompsetRateSnapshot, basis: str) -> float | None:
    """
    這一列能不能進中位數？能的話回傳金額。

    排除條件（規則 2）：賣完、或沒有該口徑的價格。
    ⚠️ `unknown` **不排除** —— 見檔頭規則 2 的修正說明。
    """
    if row.is_sold_out == SOLD_YES:
        return None
    return _f(row.price_pretax if basis == BASIS_PRETAX else row.price_gross)


@dataclass
class DailyStat:
    """單一 (snapshot_date, stay_date) 的彙總。欄位對齊 `compset_rate_daily`。"""

    stay_date: str = ""
    snapshot_date: str = ""
    self_pretax: float | None = None
    median_pretax: float | None = None
    min_pretax: float | None = None
    max_pretax: float | None = None
    index_pretax: float | None = None
    self_gross: float | None = None
    median_gross: float | None = None
    min_gross: float | None = None
    max_gross: float | None = None
    index_gross: float | None = None
    sample_count: int = 0          # 進中位數的**競品**家數（排除自己）
    # ⚠️ 兩個口徑的樣本數**會不一樣**。地點查詢第 2 頁沒有 `before_taxes_fees`，
    #    那幾家有含稅價、沒有稅前價 —— 稅前只算得到 1 家、含稅算得到 4 家是常態。
    #    畫面切到含稅口徑時如果還顯示稅前的家數，就會把一個樣本充足的指數
    #    標成「樣本不足、僅供參考」，等於叫使用者不要相信一個沒問題的數字。
    #    `sample_count` 保留原語意（稅前優先、全缺才退回含稅），供 DB 欄位與
    #    `is_low_sample` 使用，**不新增欄位到 `compset_rate_daily`**（免 migration）。
    sample_count_pretax: int = 0
    sample_count_gross: int = 0
    sold_out_count: int = 0
    #: 滿房的**競品** hotel id（不含自己）。⚠️ 只放 id 不放名字 ——
    #: `compute_stat()` 是純函式、看得到的只有快照列，名字由呼叫端解析。
    #: ⚠️ 這個欄位**不寫進 `compset_rate_daily`**（那張表沒有這一欄）。
    sold_out_hotel_ids: list[int] = field(default_factory=list)
    unknown_count: int = 0   # 有進中位數，但滿房狀態未知（B／C 級）
    self_rank: int | None = None   # 含稅價由低到高的名次（含自己）
    rank_total: int | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def is_low_sample(self) -> bool:
        return self.sample_count < MIN_SAMPLE

    def as_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["is_low_sample"] = self.is_low_sample
        return d



def compute_stat(rows: Iterable[CompsetRateSnapshot], self_hotel_id: int | None,
                 *, stay_date: str = "", snapshot_date: str = "") -> DailyStat:
    """
    從一組快照算出一天的指標。**純函式**，不碰 DB —— 好測、也好在別處重用。

    ⚠️ `self_hotel_id` 是 None（競爭組沒設 `is_self`）時仍會算中位數與滿房家數，
       但指數與排名回 None 並記 warning。**不可以靜默回 0** ——
       0 會被畫面當成「跟市場一樣便宜」，那是完全錯誤的訊息。
    """
    stat = DailyStat(stay_date=stay_date, snapshot_date=snapshot_date)
    picked = pick_by_source(rows)

    if self_hotel_id is None:
        stat.warnings.append("競爭組沒有設定 is_self，無法計算價位指數與排名")

    others = [r for hid, r in picked.items() if hid != self_hotel_id]
    stat.sold_out_count = sum(1 for r in others if r.is_sold_out == SOLD_YES)
    # 排序讓輸出穩定（測試與畫面都不希望順序每次不一樣）
    stat.sold_out_hotel_ids = sorted(
        r.compset_hotel_id for r in others if r.is_sold_out == SOLD_YES)
    stat.unknown_count = sum(1 for r in others if r.is_sold_out == SOLD_UNKNOWN)

    me = picked.get(self_hotel_id) if self_hotel_id is not None else None
    if me is not None and me.is_sold_out != SOLD_YES:
        stat.self_pretax = _f(me.price_pretax)
        stat.self_gross = _f(me.price_gross)

    for basis in (BASIS_PRETAX, BASIS_GROSS):
        values = [v for v in (_counts_in_median(r, basis) for r in others)
                  if v is not None]
        if not values:
            continue
        med, lo, hi = median(values), min(values), max(values)
        self_v = stat.self_pretax if basis == BASIS_PRETAX else stat.self_gross
        idx = (self_v / med) if (self_v is not None and med) else None
        if basis == BASIS_PRETAX:
            stat.median_pretax, stat.min_pretax, stat.max_pretax = med, lo, hi
            stat.index_pretax = round(idx, 4) if idx is not None else None
            stat.sample_count_pretax = len(values)
            stat.sample_count = len(values)     # ⭐ 以稅前口徑的家數為準
        else:
            stat.median_gross, stat.min_gross, stat.max_gross = med, lo, hi
            stat.index_gross = round(idx, 4) if idx is not None else None
            stat.sample_count_gross = len(values)
            if stat.sample_count == 0:
                # 稅前全缺（地點查詢第 2 頁的情形）時，退而用含稅口徑的家數，
                # 否則畫面會誤以為「完全沒有樣本」。
                stat.sample_count = len(values)

    # ── 排名：含稅價，含自己（規則 4）───────────────────────────────
    ranked = sorted(
        (v for v in ((_counts_in_median(r, BASIS_GROSS)) for r in picked.values())
         if v is not None)
    )
    if ranked and stat.self_gross is not None:
        stat.rank_total = len(ranked)
        stat.self_rank = ranked.index(stat.self_gross) + 1
    elif ranked:
        stat.rank_total = len(ranked)

    return stat


# ══════════════════════════════════════════════════════════════════════════
# DB 讀取
# ══════════════════════════════════════════════════════════════════════════
def self_hotel_id(db: Session, subscriber_id: int) -> int | None:
    rows = db.execute(
        select(CompsetHotel.id).where(CompsetHotel.subscriber_id == subscriber_id,
                                      CompsetHotel.is_self.is_(True))
    ).scalars().all()
    if len(rows) != 1:
        logger.warning("compset: subscriber %s 的 is_self 有 %d 筆（應為 1）",
                       subscriber_id, len(rows))
        return rows[0] if rows else None
    return rows[0]


def _snapshots(db: Session, subscriber_id: int, *, snapshot_date: str | None = None,
               stay_from: str | None = None, stay_to: str | None = None,
               stay_date: str | None = None) -> list[CompsetRateSnapshot]:
    stmt = select(CompsetRateSnapshot).where(
        CompsetRateSnapshot.subscriber_id == subscriber_id)
    if snapshot_date:
        stmt = stmt.where(CompsetRateSnapshot.snapshot_date == snapshot_date)
    if stay_date:
        stmt = stmt.where(CompsetRateSnapshot.stay_date == stay_date)
    if stay_from:
        stmt = stmt.where(CompsetRateSnapshot.stay_date >= stay_from)
    if stay_to:
        stmt = stmt.where(CompsetRateSnapshot.stay_date <= stay_to)
    return list(db.execute(stmt).scalars().all())


def latest_snapshot_date(db: Session, subscriber_id: int) -> str | None:
    return db.execute(
        select(CompsetRateSnapshot.snapshot_date)
        .where(CompsetRateSnapshot.subscriber_id == subscriber_id)
        .order_by(CompsetRateSnapshot.snapshot_date.desc())
        .limit(1)
    ).scalar_one_or_none()


# ══════════════════════════════════════════════════════════════════════════
# 彙總快取
# ══════════════════════════════════════════════════════════════════════════
def recompute_daily(db: Session, subscriber_id: int, *,
                    snapshot_date: str | None = None,
                    stay_from: str | None = None,
                    stay_to: str | None = None) -> int:
    """
    重算 `compset_rate_daily`。回傳寫入的列數。

    ⚠️ **這張表是快取不是來源**（規則 6）。發現數字怪怪的，
       第一件事是重算，不是手動改那張表。

    不帶任何條件時會重算該訂閱的**全部**資料 —— 資料量大時請帶區間。
    """
    rows = _snapshots(db, subscriber_id, snapshot_date=snapshot_date,
                      stay_from=stay_from, stay_to=stay_to)
    if not rows:
        return 0

    sid = self_hotel_id(db, subscriber_id)
    buckets: dict[tuple[str, str], list[CompsetRateSnapshot]] = {}
    for r in rows:
        buckets.setdefault((r.snapshot_date, r.stay_date), []).append(r)

    written = 0
    for (snap, stay), group in buckets.items():
        stat = compute_stat(group, sid, stay_date=stay, snapshot_date=snap)
        row = db.execute(
            select(CompsetRateDaily).where(
                CompsetRateDaily.subscriber_id == subscriber_id,
                CompsetRateDaily.snapshot_date == snap,
                CompsetRateDaily.stay_date == stay,
            )
        ).scalar_one_or_none()
        if row is None:
            row = CompsetRateDaily(subscriber_id=subscriber_id,
                                   snapshot_date=snap, stay_date=stay)
            db.add(row)
        for f in ("self_pretax", "median_pretax", "min_pretax", "max_pretax",
                  "index_pretax", "self_gross", "median_gross", "min_gross",
                  "max_gross", "index_gross", "sample_count", "sold_out_count",
                  "unknown_count", "self_rank", "rank_total"):
            setattr(row, f, getattr(stat, f))
        row.computed_at = twnow()
        written += 1

    db.flush()
    return written


# ══════════════════════════════════════════════════════════════════════════
# 查詢：矩陣、軌跡、Dashboard
# ══════════════════════════════════════════════════════════════════════════
def _latest_created_at(rows: Iterable[CompsetRateSnapshot]) -> str | None:
    """
    這批快照**最後一次寫入的時間**（`YYYY-MM-DD HH:MM:SS`）。

    ⚠️ `snapshot_date` 只有日期，答不出「今天早上到底跑了沒、幾點跑的」——
       而那正是使用者拿畫面對 Google 對不上時第一個要問的事。

    ⚠️ 取 **max** 不是 min：一天之內可能跑過排程（04:10）又被手動觸發，
       使用者要看的是「最後更新」。

    ⚠️ `created_at` 是 `twnow()` 存的**台灣時間 naive datetime**。
       這裡直接輸出字串，前端**不可以再做時區換算**（會平白多／少 8 小時）。
    """
    stamps = [r.created_at for r in rows if r.created_at is not None]
    if not stamps:
        return None
    return max(stamps).strftime("%Y-%m-%d %H:%M:%S")


def _hotel_map(db: Session, subscriber_id: int) -> dict[int, CompsetHotel]:
    return {h.id: h for h in db.execute(
        select(CompsetHotel)
        .where(CompsetHotel.subscriber_id == subscriber_id)
        .order_by(CompsetHotel.sort_order, CompsetHotel.id)
    ).scalars().all()}


def _cell(row: CompsetRateSnapshot) -> dict[str, Any]:
    return {
        "price_gross": _f(row.price_gross),
        "price_pretax": _f(row.price_pretax),
        "tax_included": row.tax_included,
        "is_sold_out": row.is_sold_out,
        "source": row.source,
        "fetch_path": row.fetch_path,
        "tier": row.tier,
        "ota_name": row.ota_name,
        "is_official": bool(row.is_official),
        "num_guests": row.num_guests,
        "snapshot_id": row.id,
    }


def matrix(db: Session, subscriber_id: int, *, stay_from: str, stay_to: str,
           snapshot_date: str | None = None) -> dict[str, Any]:
    """
    價格矩陣：橫軸入住日、縱軸競爭組。

    ⚠️ 自己那一列固定排在最前面（`is_self` 優先，其次 `sort_order`）——
       畫面上要一眼看到自己在哪。
    """
    snap = snapshot_date or latest_snapshot_date(db, subscriber_id)
    if not snap:
        return {"snapshot_date": None, "fetched_at": None,
                "hotels": [], "stay_dates": [],
                "cells": {}, "daily": {}, "warnings": ["尚無任何快照資料"]}

    rows = _snapshots(db, subscriber_id, snapshot_date=snap,
                      stay_from=stay_from, stay_to=stay_to)
    hotels = _hotel_map(db, subscriber_id)
    sid = self_hotel_id(db, subscriber_id)

    cells: dict[str, dict[str, Any]] = {}
    by_stay: dict[str, list[CompsetRateSnapshot]] = {}
    for r in rows:
        by_stay.setdefault(r.stay_date, []).append(r)
    for stay, group in by_stay.items():
        for hid, row in pick_by_source(group).items():
            cells[f"{stay}|{hid}"] = _cell(row)

    daily = {stay: compute_stat(group, sid, stay_date=stay,
                                snapshot_date=snap).as_dict()
             for stay, group in by_stay.items()}

    ordered = sorted(hotels.values(),
                     key=lambda h: (0 if h.is_self else 1, h.sort_order, h.id))
    stay_dates = sorted(by_stay.keys())
    return {
        "snapshot_date": snap,
        "fetched_at": _latest_created_at(rows),
        "hotels": [{"id": h.id, "name": h.display_name,
                    "short_name": h.short_label, "is_self": bool(h.is_self),
                    "hotel_code": h.hotel_code, "room_count": h.room_count}
                   for h in ordered],
        "stay_dates": stay_dates,
        "cells": cells,
        "daily": daily,
        "warnings": [] if sid else ["競爭組沒有設定 is_self，指數與排名無法計算"],
    }


def trend(db: Session, subscriber_id: int, *, stay_date: str,
          snapshot_from: str | None = None,
          snapshot_to: str | None = None) -> dict[str, Any]:
    """
    價格軌跡：固定一個入住日，看各家報價隨快照日怎麼走。

    ⭐ **這張圖是 `snapshot_date` 進唯一鍵的唯一目的**（SPEC §5.5）——
       也是唯一能回答「競品什麼時候降價」的畫面。
    """
    stmt = select(CompsetRateSnapshot).where(
        CompsetRateSnapshot.subscriber_id == subscriber_id,
        CompsetRateSnapshot.stay_date == stay_date)
    if snapshot_from:
        stmt = stmt.where(CompsetRateSnapshot.snapshot_date >= snapshot_from)
    if snapshot_to:
        stmt = stmt.where(CompsetRateSnapshot.snapshot_date <= snapshot_to)
    rows = list(db.execute(stmt).scalars().all())

    hotels = _hotel_map(db, subscriber_id)
    sid = self_hotel_id(db, subscriber_id)

    by_snap: dict[str, list[CompsetRateSnapshot]] = {}
    for r in rows:
        by_snap.setdefault(r.snapshot_date, []).append(r)

    series: dict[int, list[dict[str, Any]]] = {hid: [] for hid in hotels}
    for snap in sorted(by_snap):
        for hid, row in pick_by_source(by_snap[snap]).items():
            if hid in series:
                series[hid].append({"snapshot_date": snap, **_cell(row)})

    index_line = [compute_stat(by_snap[s], sid, stay_date=stay_date,
                               snapshot_date=s).as_dict()
                  for s in sorted(by_snap)]

    ordered = sorted(hotels.values(),
                     key=lambda h: (0 if h.is_self else 1, h.sort_order, h.id))
    return {
        "stay_date": stay_date,
        "snapshot_dates": sorted(by_snap.keys()),
        "hotels": [{"id": h.id, "name": h.display_name,
                    "short_name": h.short_label, "is_self": bool(h.is_self)}
                   for h in ordered],
        "series": series,
        "index_line": index_line,
    }


def dashboard(db: Session, subscriber_id: int,
              today: date | None = None) -> dict[str, Any]:
    """
    Dashboard 的 KPI。

    ⚠️ 指數與排名一律附帶 `sample_count` 與 `is_low_sample`，
       **不可以只回一個數字** —— 樣本不足的指數看起來和樣本充足的一模一樣。
    """
    # ⚠️ 用台灣時間，不是伺服器本地時間。正式機若跑在 UTC，
    #    台灣早上 8 點的 `date.today()` 還停在昨天 —— 整個 7 天窗格會位移一天，
    #    「明天」那張卡會顯示今天，而且完全看不出來。
    today = today or twnow().date()
    snap = latest_snapshot_date(db, subscriber_id)
    if not snap:
        return {"snapshot_date": None, "fetched_at": None,
                "today": None, "next_7d": [],
                "hotels": [], "warnings": ["尚無任何快照資料"]}

    sid = self_hotel_id(db, subscriber_id)
    tomorrow = (today + timedelta(days=1)).isoformat()
    week_end = (today + timedelta(days=7)).isoformat()

    rows = _snapshots(db, subscriber_id, snapshot_date=snap,
                      stay_from=tomorrow, stay_to=week_end)
    by_stay: dict[str, list[CompsetRateSnapshot]] = {}
    for r in rows:
        by_stay.setdefault(r.stay_date, []).append(r)

    stats = [compute_stat(g, sid, stay_date=s, snapshot_date=snap)
             for s, g in sorted(by_stay.items())]
    head = stats[0] if stats else None

    # ⚠️ 附上 id → 名稱對照。`sold_out_hotel_ids` 只有 id，
    #    前端要顯示「哪幾家滿房」就必須有這張表。
    hotels = _hotel_map(db, subscriber_id)

    return {
        "snapshot_date": snap,
        # ⚠️ 這裡的 rows 只涵蓋未來 7 天。整批的最後更新時間以這個窗格為準，
        #    與矩陣頁可能差幾秒（不同 tier 的寫入時間），不是錯誤。
        "fetched_at": _latest_created_at(rows),
        "today": head.as_dict() if head else None,
        "next_7d": [s.as_dict() for s in stats],
        "hotels": [{"id": h.id, "name": h.display_name,
                    "short_name": h.short_label, "is_self": bool(h.is_self)}
                   for h in sorted(hotels.values(),
                                   key=lambda x: (0 if x.is_self else 1,
                                                  x.sort_order, x.id))],
        "sold_out_days": sum(1 for s in stats if s.sold_out_count > 0),
        "low_sample_days": sum(1 for s in stats if s.is_low_sample),
        "warnings": [] if sid else ["競爭組沒有設定 is_self，指數與排名無法計算"],
    }
