"""
營運分析 — 市場區隔／房型別歷史營收（資料來源：OHIP API，非 TXT 上傳）

建立日期：2026-08-07
決策依據：`docs/EVAL_ohip_strategic_data.md` §4.3（重寫後的順位 2'）

═══════════════════════════════════════════════════════════════════════════
為什麼要另建一張表，而不是塞進既有的 `opera_revenue_daily`
═══════════════════════════════════════════════════════════════════════════
`opera_revenue_daily` 是**人工上傳 TXT** 的落地結果，一個 business_date 一列，
維度只有散客／團體四類（`individual_*` / `group_*`）。

本表是 **OHIP API** 取得的，一個 business_date 會有**多列**
（market_code × room_type 的交叉），維度是 TXT 完全沒有的。

兩者不可合併的三個理由：
1. **粒度不同** —— 硬合併就要在既有表加 market_code／room_type 欄位，
   等於把單列變多列，所有既有查詢的加總都會爆掉
2. **來源不同** —— 一個是人工上傳（落後數天、可能沒傳），一個是 API
   （可回補、可排程）。混在一起就分不出「這個月沒數字」是誰的問題
3. **口徑可能有落差** —— `/realtime/compare` 存在的理由就是這件事還沒完全對齊。
   在對齊之前，兩份資料必須各自可追溯

⚠️ 因此本表**不是** `opera_revenue_daily` 的替代品，也不是它的明細表。
   是「同一件事的另一個切面」，畫面上必須標示清楚來源，不可混用。

═══════════════════════════════════════════════════════════════════════════
與 `ohip_revenue_snapshot`（每日快照）的差別 —— 這兩張最容易搞混
═══════════════════════════════════════════════════════════════════════════
| | `ohip_revenue_snapshot` | `ohip_revenue_history`（本表） |
|---|---|---|
| 回答的問題 | 「**事前各時點**看起來如何」 | 「**這一天最後**是多少」 |
| 主鍵含 | snapshot_date（看的時間） | 沒有 —— 只有 business_date |
| 一個 business_date | 有 **187 列**（每天看一次） | 只有一組（每個維度組合一列） |
| 涵蓋範圍 | 過去 7 天 ～ 未來 180 天 | **過去 2 年**（可回補） |
| 用途 | 訂房進度 pickup | 月度趨勢、YoY |

**不要用快照表算月度趨勢** —— 那會把同一天算 187 次。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (DateTime, Index, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


class OhipRevenueHistory(Base):
    """歷史營收（business_date × market_code × room_type）"""

    __tablename__ = "ohip_revenue_history"
    __table_args__ = (
        UniqueConstraint("hotel_id", "business_date", "market_code", "room_type",
                         name="uq_rev_history"),
        # 主要查法：某段期間、依維度彙總
        Index("ix_rev_history_bd", "business_date"),
        Index("ix_rev_history_mc_bd", "market_code", "business_date"),
        Index("ix_rev_history_rt_bd", "room_type", "business_date"),
    )

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hotel_id:      Mapped[str] = mapped_column(String(40), default="", index=True)
    business_date: Mapped[str] = mapped_column(String(10), default="")

    # ⚠️ 缺值一律空字串不用 NULL —— 唯一鍵要用到，
    #    而 SQLite 的 NULL 不參與唯一性判定（兩個 NULL 不算重複），會出現重複列
    market_code:   Mapped[str] = mapped_column(String(40), default="")
    room_type:     Mapped[str] = mapped_column(String(40), default="")
    res_type:      Mapped[str] = mapped_column(String(40), default="")

    # ⚠️ 全部 nullable：OHIP **值為 0 的欄位會被整個省略**，不是回 0。
    #    補 0 會讓「沒有這個欄位」與「這個欄位是 0」混為一談。
    physical_rooms:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    ooo_rooms:       Mapped[int | None] = mapped_column(Integer, nullable=True)
    oos_rooms:       Mapped[int | None] = mapped_column(Integer, nullable=True)
    rooms_sold:      Mapped[int | None] = mapped_column(Integer, nullable=True)
    arrival_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    departure_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancelled_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    no_show_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ⚠️ 金額用 Numeric 不用 Float，精度 (16,4) 與既有 `opera_revenue_daily` 一致 ——
    #    這兩張表遲早要放在一起比對，精度不同會製造假差異
    room_revenue:  Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    total_revenue: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    food_revenue:  Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)

    synced_at:     Mapped[datetime] = mapped_column(DateTime, default=twnow, index=True)


class OhipRevenueHistorySync(Base):
    """回補／增量同步的執行紀錄與進度

    ⚠️ 為什麼回補需要「進度」而不是一次跑完
    ────────────────────────────────────────────────────────────────────────
    兩年 = 730 天。三維度交叉（日期 × 市場區隔 × 房型）很容易撞 2 MB 靜默截斷，
    所以必須切成小段（見 service 的 `CHUNK_DAYS`），約 17 段、每段 3 秒。
    走 HTTP 端點會逾時，所以做成「**每次呼叫補一段，回報還剩幾段**」，
    可以重複按到補完，中斷了也能接續。
    """

    __tablename__ = "ohip_revenue_history_sync"
    __table_args__ = (
        Index("ix_rev_hist_sync_started", "started_at"),
    )

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    hotel_id:      Mapped[str] = mapped_column(String(40), default="", index=True)
    # 'backfill'（歷史回補）或 'incremental'（每日增量）
    mode:          Mapped[str] = mapped_column(String(20), default="", index=True)

    date_start:    Mapped[str] = mapped_column(String(10), default="")
    date_end:      Mapped[str] = mapped_column(String(10), default="")

    started_at:    Mapped[datetime] = mapped_column(DateTime, default=twnow)
    finished_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status:        Mapped[str] = mapped_column(String(20), default="", index=True)
    rows_written:  Mapped[int] = mapped_column(Integer, default=0)
    api_calls:     Mapped[int] = mapped_column(Integer, default=0)
    response_bytes: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_ms:    Mapped[int] = mapped_column(Integer, default=0)

    warnings:      Mapped[str] = mapped_column(Text, default="")
    error:         Mapped[str] = mapped_column(Text, default="")
    triggered_by:  Mapped[str] = mapped_column(String(120), default="")
