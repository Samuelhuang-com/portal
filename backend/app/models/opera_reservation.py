"""
營運分析 — 訂房分析（資料來源：OHIP `rsvasync` / `blkasync`，非 TXT 上傳）

建立日期：2026-08-07
實測依據：`docs/EVAL_ohip_strategic_data.md` §4.1、§4.2
探測腳本：`backend/ohip_probe_reservations.py`

═══════════════════════════════════════════════════════════════════════════
⚠️ 這個模組與 `/opera/guest`（住客與通路分析）**分析母體不同**，不是雙胞胎
═══════════════════════════════════════════════════════════════════════════
|  | `/opera/guest`（既有） | 本模組（新） |
|---|---|---|
| 來源 | 人工上傳 TXT **Departure 報表** | OHIP `rsvasync` API |
| 母體 | **已離店**的住客 | **所有訂房**（含未來、含取消） |
| 回答 | 「住過的人長什麼樣」 | 「訂單長什麼樣」 |

**同一個維度（例如通路佔比）在兩邊出現不同數字是正確的**，不是誰對誰錯 ——
一個算的是已住完的，一個算的是所有訂單。畫面上必須寫清楚，否則一定會被當成 bug。

═══════════════════════════════════════════════════════════════════════════
⚠️ TXT 比 API 完整，本模組**不取代**也**不重複**既有分析的定位
═══════════════════════════════════════════════════════════════════════════
`opera_departure` 有而 API **沒有**的：`guest_name_id`、`guest_identity_hash`、
`membership_card_no`／`level`／`type`、`payment_desc`、`departure_time`、
`vip`、`special_requests`。

→ **付款方式統計、退房時間分布、回訪住客**這三項仍然只能看 `/opera/guest`。

API 有而 TXT **永遠沒有**的（Departure 報表本質上只有已離店的訂房）：

| 欄位 | 填充率 | 解鎖的分析 |
|------|-------|-----------|
| `bookingDate` | **100%** | 🎯 訂房前置期（booking window / lead time） |
| `cancellationDate`／`cancellationReasonCode` | 19% | 🎯 取消分析（含原因碼） |
| 未來日期的訂房 | — | 🎯 在手訂房（on-the-books）結構 |

**這三項就是本模組存在的理由。** 其餘維度（通路／Rate Code／房型／公司／團體）
是順帶提供的「訂單口徑」對照，不是要取代 TXT 口徑。

═══════════════════════════════════════════════════════════════════════════
⚠️ 填充率必須隨數字一起呈現
═══════════════════════════════════════════════════════════════════════════
實測（2 個月 2375 筆）：`companyName` 只有 **15%**、`children1/2/3` 55%、
`dailySummary[].channel` 77%、`travelAgentName` 76%。

**低填充率的維度做成排行榜會嚴重偏頗**（例如「公司貢獻排行」只涵蓋 15% 的訂單）。
所以分析服務一律回傳該維度的 `coverage`，畫面必須顯示。
⚠️ OHIP **值為 0／空的欄位會被整個省略**，所以「沒有這個欄位」與「這個欄位是 0」
必須分開 —— 全部 nullable，**不補 0**。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (DateTime, Index, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


class OhipReservation(Base):
    """逐筆訂房（rsvasync `reservations/dailySummary` 的最外層）"""

    __tablename__ = "ohip_reservation"
    __table_args__ = (
        UniqueConstraint("hotel_id", "confirmation_no", name="uq_ohip_reservation"),
        # 主要查法：依到達日看區間
        Index("ix_rsv_arrival", "hotel_id", "arrival"),
        # 訂房前置期分析：依訂房日
        Index("ix_rsv_booking", "hotel_id", "booking_date"),
        # 取消分析
        Index("ix_rsv_cancel", "hotel_id", "cancellation_date"),
        Index("ix_rsv_status", "hotel_id", "resv_status"),
    )

    id:              Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id:        Mapped[str] = mapped_column(String(40), default="", index=True)

    # `reservationIdList[]` 裡 type="Confirmation" 的那一筆。100% 有值。
    confirmation_no: Mapped[str] = mapped_column(String(40), default="")

    # ── 日期（皆 100% 有值；API 回的是 ISO datetime，落地只取日期部分）──────
    arrival:         Mapped[str] = mapped_column(String(10), default="")
    departure:       Mapped[str] = mapped_column(String(10), default="")
    booking_date:    Mapped[str] = mapped_column(String(10), default="")
    checked_out_date: Mapped[str] = mapped_column(String(10), default="")   # 80%

    # 🎯 **本模組的核心衍生欄位**：訂房前置期 = 到達日 − 訂房日。
    #    直接落地不現算 —— 它是前置期分析的 X 軸，每次查詢現算會拖慢。
    lead_days:       Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    nights:          Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── 狀態 ─────────────────────────────────────────────────────────────────
    resv_status:     Mapped[str] = mapped_column(String(30), default="")
    resv_type:       Mapped[str] = mapped_column(String(30), default="")
    no_of_rooms:     Mapped[int | None] = mapped_column(Integer, nullable=True)
    shared_yn:       Mapped[str] = mapped_column(String(2), default="")
    origin_of_booking: Mapped[str] = mapped_column(String(20), default="")

    # ── 取消（19% 有值）—— TXT 永遠沒有的東西 ────────────────────────────────
    cancellation_date:        Mapped[str] = mapped_column(String(10), default="")
    cancellation_reason_code: Mapped[str] = mapped_column(String(30), default="")

    # ── 通路與客戶（填充率見檔頭；低填充率維度做排行要標示 coverage）─────────
    travel_agent_name: Mapped[str] = mapped_column(String(160), default="")   # 76%
    travel_agent_id:   Mapped[str] = mapped_column(String(40), default="")
    iata_code:         Mapped[str] = mapped_column(String(20), default="")    # 75%
    company_name:      Mapped[str] = mapped_column(String(160), default="")   # ⚠️ 只有 15%
    company_id:        Mapped[str] = mapped_column(String(40), default="")
    group_name:        Mapped[str] = mapped_column(String(160), default="")   # 8%
    group_id:          Mapped[str] = mapped_column(String(40), default="")
    block_code:        Mapped[str] = mapped_column(String(40), default="", index=True)

    # ── 客群 ─────────────────────────────────────────────────────────────────
    nationality:     Mapped[str] = mapped_column(String(10), default="")      # 79%
    guest_country:   Mapped[str] = mapped_column(String(10), default="")      # 62%
    children_total:  Mapped[int | None] = mapped_column(Integer, nullable=True)  # 55%

    # ⚠️ 這是**人名**（訂房聯絡人，7%）。落地與否見 sync service 的 `STORE_CONTACT_NAME`。
    resv_contact_name: Mapped[str] = mapped_column(String(160), default="")

    # `externalReferences[]` 中 idContext="GUESTID" 的值（56%）。
    # ⚠️ **能不能當回訪識別尚未驗證** —— 不要在驗證前拿來做回訪分析。
    guest_ext_id:    Mapped[str] = mapped_column(String(80), default="", index=True)

    created_datetime:   Mapped[str] = mapped_column(String(19), default="")
    last_modified_date: Mapped[str] = mapped_column(String(19), default="")
    synced_at:       Mapped[datetime] = mapped_column(DateTime, default=twnow, index=True)


class OhipReservationNight(Base):
    """訂房的逐日明細（`dailySummary[]`）

    ⚠️ 一筆訂房最多可以有 61 天（實測有長住月租客），所以列數約是訂房數的 2～3 倍。
    """

    __tablename__ = "ohip_reservation_night"
    __table_args__ = (
        UniqueConstraint("hotel_id", "confirmation_no", "trx_date",
                         name="uq_ohip_rsv_night"),
        Index("ix_rsvn_date", "hotel_id", "trx_date"),
        Index("ix_rsvn_market", "hotel_id", "market_code", "trx_date"),
        Index("ix_rsvn_rate", "hotel_id", "rate_code", "trx_date"),
    )

    id:              Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id:        Mapped[str] = mapped_column(String(40), default="", index=True)
    confirmation_no: Mapped[str] = mapped_column(String(40), default="", index=True)
    trx_date:        Mapped[str] = mapped_column(String(10), default="")

    # 100% 有值的四個維度
    market_code:     Mapped[str] = mapped_column(String(40), default="")
    rate_code:       Mapped[str] = mapped_column(String(40), default="")
    source_code:     Mapped[str] = mapped_column(String(40), default="")
    room_type:       Mapped[str] = mapped_column(String(40), default="")

    # `bookedRoomType` 與 `roomTypeCharged` 不同 → 升等分析
    booked_room_type:   Mapped[str] = mapped_column(String(40), default="")
    room_type_charged:  Mapped[str] = mapped_column(String(40), default="")

    channel:         Mapped[str] = mapped_column(String(40), default="")   # 77%
    room:            Mapped[str] = mapped_column(String(20), default="")   # 82%
    adults:          Mapped[int | None] = mapped_column(Integer, nullable=True)   # 96%
    children:        Mapped[int | None] = mapped_column(Integer, nullable=True)   # 2%

    # ⚠️ 金額用 Numeric 不用 Float，精度 (16,4) 與 `opera_revenue_daily` 一致 ——
    #    遲早要放在一起比對，精度不同會製造假差異。
    rate_amount:     Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)  # 69%
    net_rate_amount: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)  # 48%
    room_revenue:    Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)  # 48%
    total_revenue:   Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)  # 48%
    tax:             Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)  # 48%
    currency:        Mapped[str] = mapped_column(String(10), default="")


class OhipBlock(Base):
    """團體 Block（blkasync `blocks/allocationSummary` 的最外層）

    ⚠️ TXT 只有 `block_code` 與 `group_name`，**沒有配房／成交數**。
       本表與 `OhipBlockAllocation` 是團體 pickup 分析的唯一來源。
    """

    __tablename__ = "ohip_block"
    __table_args__ = (
        UniqueConstraint("hotel_id", "block_id", name="uq_ohip_block"),
        Index("ix_blk_dates", "hotel_id", "start_date", "end_date"),
        Index("ix_blk_code", "hotel_id", "block_code"),
    )

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id:      Mapped[str] = mapped_column(String(40), default="", index=True)
    block_id:      Mapped[str] = mapped_column(String(40), default="")

    block_code:    Mapped[str] = mapped_column(String(40), default="")
    block_name:    Mapped[str] = mapped_column(String(200), default="")
    status:        Mapped[str] = mapped_column(String(20), default="", index=True)
    block_type:    Mapped[str] = mapped_column(String(20), default="")

    market_code:   Mapped[str] = mapped_column(String(40), default="")
    source_code:   Mapped[str] = mapped_column(String(40), default="")
    booking_medium: Mapped[str] = mapped_column(String(40), default="")
    rate_plan_code: Mapped[str] = mapped_column(String(40), default="")

    start_date:    Mapped[str] = mapped_column(String(10), default="")
    end_date:      Mapped[str] = mapped_column(String(10), default="")

    # ⚠️ 實測樣本全是 0 —— 該飯店可能沒有在用 cut-off。
    #    做 cut-off 分析前先確認這個欄位有沒有實質值，否則會做出一張全 0 的表。
    cut_off_days:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency:      Mapped[str] = mapped_column(String(10), default="")

    # 從 `blockProfiles.blockProfile[].profile.company.companyName` 取出
    company_name:  Mapped[str] = mapped_column(String(200), default="")
    profile_type:  Mapped[str] = mapped_column(String(40), default="")

    cancellation_code:        Mapped[str] = mapped_column(String(30), default="")
    cancellation_date:        Mapped[str] = mapped_column(String(10), default="")
    cancellation_description: Mapped[str] = mapped_column(Text, default="")

    create_datetime:    Mapped[str] = mapped_column(String(19), default="")
    last_modified_date: Mapped[str] = mapped_column(String(19), default="")
    synced_at:     Mapped[datetime] = mapped_column(DateTime, default=twnow, index=True)


class OhipBlockAllocation(Base):
    """Block 的逐日 × 房型配房與成交

    ⚠️ 來源是**三層**巢狀：`allocationDates[].allocations[]`
       （第一版誤以為只有兩層，見 CHANGELOG [1.90.15]）。
    """

    __tablename__ = "ohip_block_allocation"
    __table_args__ = (
        UniqueConstraint("hotel_id", "block_id", "allocation_date", "room_type",
                         name="uq_ohip_block_alloc"),
        Index("ix_blkalloc_date", "hotel_id", "allocation_date"),
    )

    id:              Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id:        Mapped[str] = mapped_column(String(40), default="", index=True)
    block_id:        Mapped[str] = mapped_column(String(40), default="", index=True)
    allocation_date: Mapped[str] = mapped_column(String(10), default="")
    room_type:       Mapped[str] = mapped_column(String(40), default="")

    # 🎯 團體 pickup 分析的三個核心數字，API 直接給，不必自己推算
    original_rooms:  Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_rooms:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    pickup_rooms:    Mapped[int | None] = mapped_column(Integer, nullable=True)
    sell_limit:      Mapped[int | None] = mapped_column(Integer, nullable=True)

    rate_one_person:   Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    rate_two_person:   Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)

    room_revenue:    Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    food_revenue:    Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    other_revenue:   Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    total_revenue:   Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    currency:        Mapped[str] = mapped_column(String(10), default="")


class OhipReservationSync(Base):
    """訂房／團體同步的執行紀錄與回補進度（兩者共用一張）"""

    __tablename__ = "ohip_reservation_sync"
    __table_args__ = (Index("ix_rsv_sync_started", "started_at"),)

    id:            Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_id:      Mapped[str] = mapped_column(String(40), default="", index=True)

    # 'reservation' 或 'block'
    dataset:       Mapped[str] = mapped_column(String(20), default="", index=True)
    # 'backfill' 或 'incremental'
    mode:          Mapped[str] = mapped_column(String(20), default="", index=True)

    date_start:    Mapped[str] = mapped_column(String(10), default="")
    date_end:      Mapped[str] = mapped_column(String(10), default="")

    started_at:    Mapped[datetime] = mapped_column(DateTime, default=twnow)
    finished_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status:        Mapped[str] = mapped_column(String(20), default="", index=True)

    parent_rows:   Mapped[int] = mapped_column(Integer, default=0)   # 訂房數／block 數
    child_rows:    Mapped[int] = mapped_column(Integer, default=0)   # 逐日列數
    api_calls:     Mapped[int] = mapped_column(Integer, default=0)
    response_bytes: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_ms:    Mapped[int] = mapped_column(Integer, default=0)

    warnings:      Mapped[str] = mapped_column(Text, default="")
    error:         Mapped[str] = mapped_column(Text, default="")
    triggered_by:  Mapped[str] = mapped_column(String(120), default="")
