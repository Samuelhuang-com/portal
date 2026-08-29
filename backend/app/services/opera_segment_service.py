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


def source_info() -> dict[str, Any]:
    """本模組的資料來源說明（給前端的「?」說明用）。

    ⚠️ `note` 會直接顯示在畫面上。同一個模組裡混了兩種來源，
       不標示清楚會被當成 TXT 上傳的資料看待。

    ⚠️ `/segments` 與 `/sync/status` **共用這一份**。歷史資料還沒回補完時
       `/segments` 前端根本不會呼叫（沒有 data_range 就不查），
       說明卻恰好是那時候最需要看的，所以 `/sync/status` 也要帶。
    """
    return {
        "provider": "OPERA Cloud（OHIP 非同步營收 API，已落地）",
        "table": "ohip_revenue_history",
        "hotel_id": settings.OHIP_HOTEL_ID,
        "note": ("本頁資料來自 OPERA Cloud API，**不是**人工上傳的 TXT 報表。"
                 "市場區隔（Market Code）是貴飯店在 OPERA 自行設定的分類，"
                 "與 TXT 的「散客／團體」四類**不是同一套分類，不可互相對照**。"),
        # ⚠️ 這句必須顯示在畫面上：市場區隔那張表的住房率分母不是「該區隔的房間數」。
        "occupancy_note": ("依市場區隔看時，住房率與 RevPAR 的分母是**全館可售房**"
                           "（房間本身不屬於任何一個市場區隔），因此各列的住房率"
                           "相加才等於全館住房率。依房型看時，分母才是該房型自己的可售房。"),
    }


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


# 直接 SUM 的欄位（`available_rooms` 是 physical − OOO，另外處理）
_SUM_FIELDS: tuple[str, ...] = (
    "rooms_sold", "room_revenue", "total_revenue", "cancelled_rooms", "arrival_rooms",
)


def _grouped(db: Session, start: str, end: str, dimension: str) -> list[tuple]:
    """依「維度 × 年月」在 SQL 端聚合後才回 Python（2026-08-27 改）。

    ⚠️⚠️ **絕對不要改回 `db.query(OhipRevenueHistory)...all()` 全撈。**
       這張表目前 19.7 萬列且以每天約 266 列成長。實測（740 天全期間）：
         · 全撈 + Python 迴圈：4,521 ms / 常駐記憶體 500 MB
         · 本函式（GROUP BY 下推）：159 ms / 115 KB
       `analyze()` 開 YoY 會查兩次，全撈版的單一請求峰值接近 1 GB。
       後端是單 worker，任何人打開這頁選「全部」就會讓整個 Portal 停住數秒。

    ⚠️ 每個欄位都要包 `COALESCE(...,0)`：SQL 的 `NULL - NULL` 是 NULL 而
       `SUM()` 會直接略過 NULL，與原本 `_d(None) == 0` 的語意不同。
       少包一個 COALESCE，可售房就會在來源缺值時被少算而不報錯。

    ⚠️ **這裡不算可售房** —— `physical_rooms` 在每個 market 列上重複，
       直接 `SUM()` 會被放大成 market 數倍。可售房一律走 `_inventory()`。

    回傳每列：`(維度值, 年月, *_SUM_FIELDS, 原始列數)`
    """
    H = OhipRevenueHistory
    dim_col = getattr(H, dimension)          # dimension 已由呼叫端限定在 VALID_DIMS
    ym_col = func.substr(func.coalesce(H.business_date, ""), 1, 7)
    sum_cols = [func.sum(func.coalesce(getattr(H, f), 0)) for f in _SUM_FIELDS]

    return (db.query(dim_col, ym_col, *sum_cols, func.count())
              .filter(H.hotel_id == settings.OHIP_HOTEL_ID,
                      H.business_date >= start,
                      H.business_date <= end)
              .group_by(dim_col, ym_col)
              .all())


def _inventory(db: Session, start: str, end: str) -> list[tuple]:
    """可售房：先按 `(日期, 房型)` 去重，再加總（2026-08-27 修正）。

    ⚠️⚠️ **這是本模組最容易算錯的一件事。**
       `ohip_revenue_history` 的唯一鍵是 `(hotel_id, business_date, market_code,
       room_type)`，而 `physical_rooms` 是**該房型的存量、原封不動重複在每個
       market 列上**。直接 `SUM(physical_rooms - ooo_rooms)` 會乘上 market 數。

       實測 2026-08-20：19 個 market 每個都顯示 69（＝全館存量），
       加總得 1,311 ＝ 69 × 19。整段期間 OHIP 每日 1,310.2 對上 TXT 來源
       （`/opera/revenue/kpi`）每日 68.96，比值正好 19.00 ＝ market 基數。
       修正前畫面顯示住房率 3.8%，真實值是 72.8%。

    ⚠️ 內層用 `MAX()` 而不是 `SELECT DISTINCT`：若同一 `(日期, 房型)` 的各
       market 列之間 `physical_rooms` 不一致（來源異常），`DISTINCT` 會留下
       多列而再次重複計算，`MAX()` 則保證每組只取一個值。

    ⚠️ `rooms_sold` / 各項營收**沒有**這個問題 —— 它們本來就按
       `(market × 房型)` 分開記錄，實測依兩個維度加總都是 67，一致。

    回傳每列：`(房型, 年月, available_rooms)`
    """
    H = OhipRevenueHistory
    ym_expr = func.substr(func.coalesce(H.business_date, ""), 1, 7)

    # 內層：每個 (日期, 房型) 只留一組存量
    per_day = (db.query(
                   H.business_date.label("bd"),
                   H.room_type.label("rt"),
                   ym_expr.label("ym"),
                   func.max(func.coalesce(H.physical_rooms, 0)).label("phys"),
                   func.max(func.coalesce(H.ooo_rooms, 0)).label("ooo"))
                 .filter(H.hotel_id == settings.OHIP_HOTEL_ID,
                         H.business_date >= start,
                         H.business_date <= end)
                 .group_by(H.business_date, H.room_type)
                 .subquery())

    return (db.query(per_day.c.rt, per_day.c.ym,
                     func.sum(per_day.c.phys - per_day.c.ooo))
              .group_by(per_day.c.rt, per_day.c.ym)
              .all())


def _blank() -> dict[str, Decimal]:
    return {k: Decimal(0) for k in
            ("rooms_sold", "available_rooms", "room_revenue", "total_revenue",
             "cancelled_rooms", "arrival_rooms")}


def _add(acc: dict[str, Decimal], row: tuple) -> None:
    """把一列 `_grouped()` 的結果累加進 `acc`（不含可售房，見 `_inventory()`）。

    ⚠️ SQLite 的 `SUM()` 走 float，這裡才轉回 Decimal。實測 19.7 萬列、
       總額 54.8 億時與「逐列 Decimal 相加」差 0.000014 元，`round(2)` 後一致。
    """
    for i, field in enumerate(_SUM_FIELDS, start=2):
        acc[field] += _d(row[i])


def _inv_maps(db: Session, start: str, end: str
              ) -> tuple[dict[str, Decimal], dict[str, Decimal],
                         dict[tuple[str, str], Decimal], Decimal]:
    """把 `_inventory()` 攤成四份對照表：依房型／依月／依房型×月／總計。"""
    by_rt: dict[str, Decimal] = defaultdict(Decimal)
    by_month: dict[str, Decimal] = defaultdict(Decimal)
    by_rt_month: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    for rt_raw, ym_raw, avail in _inventory(db, start, end):
        rt = (rt_raw or "") or UNCLASSIFIED     # 與 `_grouped()` 的正規化一致
        ym = ym_raw or ""
        v = _d(avail)
        by_rt[rt] += v
        by_month[ym] += v
        by_rt_month[(rt, ym)] += v
        total += v
    return by_rt, by_month, by_rt_month, total


def _apply_available(by_dim, by_dim_month, by_month, total,
                     dimension: str, inv: tuple) -> None:
    """把可售房填進四個累加器。

    ⚠️ **分母的歸屬依維度而不同，這是刻意的：**
       · `room_type`：房型**擁有**存量 → 用該房型自己的可售房。
       · `market_code`：市場區隔**不擁有**存量（69 間房不屬於任何一個 market）
         → 一律用**全館**可售房。因此各 market 的住房率是
         「該 market 售出 ÷ 全館可售」，各列相加才等於全館住房率。
         這個定義已於 2026-08-27 與使用者確認。
    """
    inv_by_rt, inv_by_month, inv_by_rt_month, inv_total = inv

    total["available_rooms"] = inv_total
    for m in by_month:
        by_month[m]["available_rooms"] = inv_by_month.get(m, Decimal(0))

    if dimension == DIM_ROOM_TYPE:
        for k in by_dim:
            by_dim[k]["available_rooms"] = inv_by_rt.get(k, Decimal(0))
        for key in by_dim_month:
            by_dim_month[key]["available_rooms"] = inv_by_rt_month.get(key, Decimal(0))
    else:
        for k in by_dim:
            by_dim[k]["available_rooms"] = inv_total
        for (k, m) in by_dim_month:
            by_dim_month[(k, m)]["available_rooms"] = inv_by_month.get(m, Decimal(0))


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

    # ⚠️ 只發一支「維度 × 年月」查詢，其餘三個累加器由這份結果往上捲。
    #    分四支各自 GROUP BY 也可以，但那會讓四個口徑有機會各自漂移。
    rows = _grouped(db, start, end, dimension)

    # ── ① 結構：依維度彙總 ──────────────────────────────────────────────────
    by_dim: dict[str, dict[str, Decimal]] = defaultdict(_blank)
    # ── ② 趨勢：維度 × 月份 ────────────────────────────────────────────────
    by_dim_month: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(_blank)
    by_month: dict[str, dict[str, Decimal]] = defaultdict(_blank)
    total = _blank()
    row_count = 0

    for r in rows:
        # ⚠️ SQL 會把 NULL 與空字串分成兩組，這裡正規化後才合併，
        #    與原本「全撈」版的 `(v or "") or UNCLASSIFIED` 結果一致。
        key = (r[0] or "") or UNCLASSIFIED
        month = r[1] or ""
        _add(by_dim[key], r)
        _add(by_dim_month[(key, month)], r)
        _add(by_month[month], r)
        _add(total, r)
        row_count += int(r[-1] or 0)      # 原始列數，供前端顯示樣本數

    # ⚠️ 可售房另外查（`physical_rooms` 在每個 market 列上重複，不能直接 SUM）
    _apply_available(by_dim, by_dim_month, by_month, total,
                     dimension, _inv_maps(db, start, end))

    prev_by_dim: dict[str, dict[str, Decimal]] = defaultdict(_blank)
    prev_total = _blank()
    if compare_yoy:
        prev_start, prev_end = _shift_year(start), _shift_year(end)
        prev_dummy_month: dict[str, dict[str, Decimal]] = defaultdict(_blank)
        prev_dummy_dim_month: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(_blank)
        for r in _grouped(db, prev_start, prev_end, dimension):
            key = (r[0] or "") or UNCLASSIFIED
            _add(prev_by_dim[key], r)
            _add(prev_total, r)
        # 去年同期的可售房要用**去年的**存量，不能沿用今年的
        _apply_available(prev_by_dim, prev_dummy_dim_month, prev_dummy_month,
                         prev_total, dimension, _inv_maps(db, prev_start, prev_end))

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
    # ⚠️ 第二個鍵是**穩定性次要鍵**，不是排序需求（2026-08-29 補）。
    #    只用 room_revenue 的話，營收相同的區隔（多半是一群 0 元的，
    #    像 A/R、CMP 這些非營收科目）先後由引擎決定 —— SQLite 與 PostgreSQL
    #    的實作不同，切換後這份清單的順序會變**且不會報錯**。
    #    ⚠️ 改用 `-營收` 而不是 `reverse=True`：reverse 會把次要鍵也一起反轉，
    #       維度名稱就變成倒序了。
    segments.sort(key=lambda x: (-(x.get("room_revenue") or 0), str(x.get(dimension) or "")))

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
        "row_count": row_count,
        "source": source_info(),
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
