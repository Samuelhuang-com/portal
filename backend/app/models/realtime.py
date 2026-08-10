"""
即時營運 — OHIP API 呼叫日誌

規格書：docs/SPEC_realtime_operations.md §4

只有一張表：每次對 OHIP 發出的實際請求記一筆（快取命中不記，因為那次沒有真的呼叫）。

為什麼要留這張表
────────────────────────────────────────────────────────────────────────────
1. OHIP 是 **Production 環境且按呼叫量計費**，必須看得到用量成長。
2. 出問題時 Oracle 會要 `x-request-id`，事後撈不到就只能重現。
3. 畫面上標示「這筆數字幾點抓的」需要有據可查，不能只靠前端記憶。

⚠️ 這張表**不存業務資料**，只存呼叫的 metadata。房況數字本身放記憶體快取，
   不落地 —— 落地就變成另一套事實來源，會跟 `opera_*` 打架。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (Boolean, DateTime, Float, Index, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


class OhipCallLog(Base):
    """每一次實際發出的 OHIP 請求"""

    __tablename__ = "ohip_call_log"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    called_at:   Mapped[datetime] = mapped_column(DateTime, default=twnow, index=True)
    endpoint:    Mapped[str] = mapped_column(String(200), default="")
    hotel_id:    Mapped[str] = mapped_column(String(40), default="", index=True)

    # 查詢區間（房況類才有值）
    date_start:  Mapped[str] = mapped_column(String(10), default="")
    date_end:    Mapped[str] = mapped_column(String(10), default="")

    status_code: Mapped[int] = mapped_column(Integer, default=0, index=True)
    elapsed_ms:  Mapped[int] = mapped_column(Integer, default=0)
    request_id:  Mapped[str] = mapped_column(String(64), default="")

    success:     Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    error:       Mapped[str] = mapped_column(Text, default="")

    # 誰觸發的（排程觸發時為空）
    triggered_by: Mapped[str] = mapped_column(String(120), default="")


class OhipAsyncCache(Base):
    """OHIP **非同步**端點的查詢結果落地快取

    為什麼一定要落地（2026-08-07 新增）
    ────────────────────────────────────────────────────────────────────────
    Oracle 官方規定：**相同參數的 async 請求強制間隔 30 分鐘**，
    而且「不管 POST／HEAD／GET 循環有沒有跑完都算」
    （見 `ohipu/c_oracle_hospitality_async_apis_types_and_recommendations.htm`）。

    原本的記憶體快取擋不住這件事：
      ① TTL 只有 15 分鐘 —— 第 16 分鐘重查就會撞限制
      ② 服務一重啟快取就空了，重啟後第一次查詢照樣撞
      ③ 未來若加 worker，每個行程各有一份快取，等於沒有防護

    所以快取必須跨行程、跨重啟 —— 也就是必須落地。

    ⚠️ 這張表存的是「**API 回應的快取**」，不是業務資料。
       它與 `opera_*` 不是競爭關係，過期或刪光都只會多打一次 API，不會遺失任何事實。
       這一點與 `ohip_call_log`「不存業務資料」的原則一致。

    ⚠️ `fetched_at` 與 `fetched_epoch` 兩個都存是**刻意的**：
       前者是台灣時間 naive datetime，給人看；
       後者是 epoch 浮點數，給程式算冷卻剩餘秒數。
       只留 naive datetime 做時間差運算，跨時區或跨機器時會出錯。
    """

    __tablename__ = "ohip_async_cache"

    id:           Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 「相同請求」的識別。⚠️ 必須涵蓋所有會影響 OHIP 判定 identical 的參數
    cache_key:    Mapped[str] = mapped_column(String(255), unique=True, index=True)

    endpoint:     Mapped[str] = mapped_column(String(200), default="")
    hotel_id:     Mapped[str] = mapped_column(String(40), default="", index=True)
    date_start:   Mapped[str] = mapped_column(String(10), default="")
    date_end:     Mapped[str] = mapped_column(String(10), default="")

    payload_json: Mapped[str] = mapped_column(Text, default="")
    meta_json:    Mapped[str] = mapped_column(Text, default="")

    fetched_at:   Mapped[datetime] = mapped_column(DateTime, default=twnow, index=True)
    fetched_epoch: Mapped[float] = mapped_column(Float, default=0.0)

    # 這份快取被讀取過幾次 —— 用來評估快取有沒有真的省到呼叫
    hit_count:    Mapped[int] = mapped_column(Integer, default=0)


# ═══════════════════════════════════════════════════════════════════════════
# 每日快照（2026-08-07 新增）
# ═══════════════════════════════════════════════════════════════════════════
#
# ⚠️ 為什麼這三張表**必須**存在，而且越早開始存越好
# ──────────────────────────────────────────────────────────────────────────
# OHIP 給的是「**現在看到的那一天**」，不是「那一天當時的樣子」。
# 今天查 8/20，拿到的是此刻的 8/20；明天再查，數字已經變了，
# 而**昨天看到的版本永遠拿不回來** —— API 沒有任何「回到過去」的參數。
#
# 因此「距離入住還有 30 天時，這一天已經賣了幾間」這種問題
# （pickup／booking pace，訂房進度）**只能靠自己每天存一份快照累積**。
# 這是 `ANALYSIS_opera_realtime_matrix.md` 與使用手冊 §10.2 都特別標注
# 「有時效性、今天不開始存就永遠補不回來」的原因。
#
# ⚠️ 這三張表與 `ohip_call_log`／`ohip_async_cache` 的性質**不同**
# ──────────────────────────────────────────────────────────────────────────
# 那兩張刪光只會多打一次 API，不會遺失事實。
# **這三張刪掉就是永久遺失** —— 沒有任何方式可以重建。備份策略要涵蓋它們。
#
# ⚠️ 這三張表也不與 `opera_*` 競爭
# ──────────────────────────────────────────────────────────────────────────
# `opera_*` 回答「那一天最後的結果是多少」（TXT 上傳，事後定案）。
# 快照回答「那一天在事前的各個時點，看起來是多少」。
# **兩者是不同的問題，不是同一份資料的兩個版本。**
#
# ⚠️ 複合索引直接寫在 `__table_args__`
# ──────────────────────────────────────────────────────────────────────────
# 專案既有做法是把複合索引放進 `add_*_tables.sql` 另外執行
# （因為 `create_all` 不會產生 Model 沒宣告的索引）。
# 但那個做法已經造成過「SQL 檔交付了卻沒人執行」的問題。
# 這裡改成在 Model 裡宣告 `Index(...)` —— `create_all` 就會一併建立，
# **不需要任何人手動執行 SQL**。


class OhipSnapshotRun(Base):
    """每一次快照作業的執行紀錄

    ⚠️ 一定要有這張表：快照是背景排程，沒人盯著。
       沒有執行紀錄的話，「這三個月的資料為什麼有缺口」永遠查不出來。
    """

    __tablename__ = "ohip_snapshot_run"

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 抓取當天（台灣日期）。同一天重跑會覆蓋，所以這裡不是唯一鍵而是查詢鍵。
    snapshot_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    hotel_id:      Mapped[str] = mapped_column(String(40), default="", index=True)

    started_at:    Mapped[datetime] = mapped_column(DateTime, default=twnow, index=True)
    finished_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ok / partial / failed
    #   partial = 有資料但不完整（例如營收段落被 2 MB 截斷，或營收失敗但房況成功）
    #   ⚠️ 刻意區分 partial 與 failed：房況拿到、營收沒拿到仍然有價值，不該整批丟掉
    status:        Mapped[str] = mapped_column(String(20), default="", index=True)

    horizon_days:  Mapped[int] = mapped_column(Integer, default=0)
    # 往前回看幾天。⚠️ 2026-08-07 稍後追加（見下方說明），舊紀錄為 0
    lookback_days: Mapped[int] = mapped_column(Integer, default=0)
    api_calls:     Mapped[int] = mapped_column(Integer, default=0)
    elapsed_ms:    Mapped[int] = mapped_column(Integer, default=0)

    house_rows:     Mapped[int] = mapped_column(Integer, default=0)
    room_type_rows: Mapped[int] = mapped_column(Integer, default=0)
    revenue_rows:   Mapped[int] = mapped_column(Integer, default=0)

    # 回應總位元組數 —— 用來觀察是否逼近 2 MB 截斷門檻
    response_bytes: Mapped[int] = mapped_column(Integer, default=0)

    # 每一則警告一行。⚠️ 警告不等於錯誤，但必須留下來讓人事後判讀資料可信度
    warnings:      Mapped[str] = mapped_column(Text, default="")
    error:         Mapped[str] = mapped_column(Text, default="")

    triggered_by:  Mapped[str] = mapped_column(String(120), default="")


class OhipInventorySnapshot(Base):
    """房況快照（同步版 inventoryStatistics）

    每天為「今日 ～ 今日+N 天」的每一天各存一列（全館層），
    再為每個房型各存一列（房型層）。
    """

    __tablename__ = "ohip_inventory_snapshot"
    __table_args__ = (
        # 同一次快照、同一個被觀測日、同一個粒度只能有一列
        UniqueConstraint("snapshot_date", "business_date", "scope", "room_type",
                         name="uq_inv_snapshot"),
        # pickup 分析的主要查法：「某一天，在各個前置天數時看起來如何」
        Index("ix_inv_snapshot_bd_lead", "business_date", "lead_days"),
        # 次要查法：「某一次快照看到的整條未來曲線」
        Index("ix_inv_snapshot_sd_bd", "snapshot_date", "business_date"),
    )

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ⚠️ 三個日期欄位的意義完全不同，命名不可簡化：
    #   snapshot_date = 「什麼時候看的」
    #   business_date = 「看的是哪一天」
    #   lead_days     = business_date − snapshot_date，即「提前幾天看」
    # pickup 分析幾乎都是用 lead_days 當 X 軸，所以直接落地而不是每次現算。
    snapshot_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    business_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    lead_days:     Mapped[int] = mapped_column(Integer, default=0, index=True)

    hotel_id:      Mapped[str] = mapped_column(String(40), default="", index=True)

    # 'house'（全館）或 'roomtype'（房型層）
    scope:         Mapped[str] = mapped_column(String(10), default="house")
    # scope='house' 時為空字串（不是 NULL —— 唯一鍵含此欄，NULL 在 SQLite 不參與唯一性判定）
    room_type:     Mapped[str] = mapped_column(String(40), default="")
    room_type_desc: Mapped[str] = mapped_column(String(120), default="")

    # ⚠️ 全部 nullable：OHIP **值為 0 的欄位會被整個省略**，不是回 0。
    #    補 0 會讓「沒有這個欄位」與「這個欄位是 0」混為一談。
    inventory_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    rooms_sold:        Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    ooo_rooms:         Mapped[int | None] = mapped_column(Integer, nullable=True)
    arrival_rooms:     Mapped[int | None] = mapped_column(Integer, nullable=True)
    departure_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    people_in_house:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    comp_rooms:        Mapped[int | None] = mapped_column(Integer, nullable=True)
    house_use_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_use_rooms:     Mapped[int | None] = mapped_column(Integer, nullable=True)
    overbooking_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sell_limit_rooms:  Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 住房率 API 不回傳，落地時一併算好（口徑 = rooms_sold ÷ (inventory − OOO)）
    occupancy:     Mapped[float | None] = mapped_column(Float, nullable=True)
    is_weekend:    Mapped[bool] = mapped_column(Boolean, default=False)

    created_at:    Mapped[datetime] = mapped_column(DateTime, default=twnow)


class OhipRevenueSnapshot(Base):
    """營收快照（非同步版 revenueInventoryStatistics）

    以 `groupBy = [MarketCode, RoomType]` 取數，所以每一列是
    **（日期 × 市場區隔 × 房型）** 的交叉組合。
    全館合計 = 同一個 business_date 的所有列相加，不另存一列合計
    （另存合計就會有兩份事實，加總對不起來時無從判斷哪個對）。
    """

    __tablename__ = "ohip_revenue_snapshot"
    __table_args__ = (
        UniqueConstraint("snapshot_date", "business_date", "market_code", "room_type",
                         name="uq_rev_snapshot"),
        Index("ix_rev_snapshot_bd_lead", "business_date", "lead_days"),
        Index("ix_rev_snapshot_sd_bd", "snapshot_date", "business_date"),
    )

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    snapshot_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    business_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    lead_days:     Mapped[int] = mapped_column(Integer, default=0, index=True)

    hotel_id:      Mapped[str] = mapped_column(String(40), default="", index=True)

    # 缺值一律空字串而非 NULL（理由同 `room_type`：唯一鍵要用得到）
    market_code:   Mapped[str] = mapped_column(String(40), default="")
    room_type:     Mapped[str] = mapped_column(String(40), default="")
    res_type:      Mapped[str] = mapped_column(String(40), default="")

    physical_rooms:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    ooo_rooms:       Mapped[int | None] = mapped_column(Integer, nullable=True)
    oos_rooms:       Mapped[int | None] = mapped_column(Integer, nullable=True)
    rooms_sold:      Mapped[int | None] = mapped_column(Integer, nullable=True)
    arrival_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    departure_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancelled_rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    no_show_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ⚠️ 金額用 Numeric 不用 Float。API 回的是 18 位有效數字的**字串**
    #    （例："153103.809523809525"），用 float 累加 180 天會差到幾塊錢。
    # ⚠️ 精度刻意採 (16, 4)，與既有 `opera_revenue_daily` 一致 ——
    #    這兩張表遲早要放在一起比對，精度不同會製造假差異。
    room_revenue:  Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    total_revenue: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    food_revenue:  Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)

    created_at:    Mapped[datetime] = mapped_column(DateTime, default=twnow)
