"""
競品分析（Competitive Analysis）— 資料模型（7 張表）

建立日期：2026-09-09
規格書：`docs/SPEC_compset_analysis.md` v1.1
P0 探測報告：`docs/COMPSET_P0_REPORT.md`

═══════════════════════════════════════════════════════════════════════════
本模組是「外部 API 擷取型」，與 Ragic 無關，也與 OPERA（人工上傳 TXT）無關
═══════════════════════════════════════════════════════════════════════════
資料來源是 SerpApi 的 `google_hotels` 引擎。沒有 ragic_id、沒有 ragic_url，
明細 Drawer 的原始連結改用該筆報價的 OTA 連結（等價替代，比照 SPEC_ota_reviews §9.3）。

⚠️ **前綴刻意用 `compset` 不用 `comp`**（SPEC D8）——
   飯店業 comp ＝ 招待房（complimentary），在 PMS 周邊系統裡會誤讀。

═══════════════════════════════════════════════════════════════════════════
六個最容易踩的坑（全部已在欄位設計中處理，改欄位前務必先讀）
═══════════════════════════════════════════════════════════════════════════
1. **掛牌價 ≠ ADR，永遠不可相減**（SPEC §5.1）
   本模組存的全部是「對外掛牌的最低可訂價」，`opera_revenue_daily.adr` 是成交後平均實收。
   兩者差 15~30% 是常態。正解是競爭組**包含自己**（`CompsetHotel.is_self`），
   比「掛牌 vs 掛牌」。任何把 `price_*` 直接減 `adr` 的程式碼都是 bug。

2. **⭐ 唯一鍵必須含 `snapshot_date`**（SPEC §5.5）
   「9/9 看 12/24 的價」和「9/20 看 12/24 的價」是**兩筆資料，不是覆蓋**。
   寫成覆蓋，「競品什麼時候降價」就永遠答不出來。
   （EVAL_opera_rate_forecasting §9.2 的 HF 快照已經踩過同一個坑。）

3. **⭐ 抓不到價 ＝ 賣完了，不是缺值**，而且是**三態不是布林**（SPEC §5.4、D13）
   `is_sold_out` 是 `yes` / `no` / `unknown` 的字串。
   P0 實測：token 查瀚寓夏天 2026-12-31 回 `status=Success` 但 `prices: []`；
   同一 token 在 D+11、D+90 都有完整報價 → 排除「太遠沒報價」，訊號成立。
   ⚠️ **但只有 `fetch_path='token'` 拿得到**。地點查詢時賣完的飯店會直接從結果消失，
   與「不在前 N 名」分不開 → `fetch_path='location'` 一律寫 `unknown`，
   **統計時不可當成「有房」**。

4. **⭐ 稅費雙欄，且兩價相同 ≠ 沒有稅**（SPEC §5.3、D11）
   P0 實測含稅÷稅前：瀚寓夏天／承攜／捷絲旅／福華＝1.155（5%營業稅＋10%服務費）、
   谷墨／慕居／金來／丰居＝1.05（只有 5%）、台北漫步旅店＝1.000（來源未拆分）。
   所以 `price_gross` 與 `price_pretax` 都要存，指數兩種都算。
   兩價相同時 `tax_included` 記 **`unknown`** 而不是 `no`。
   ⚠️ `price_pretax` 不保證存在——地點查詢第 2 頁的 20 筆全部沒有稅前欄位。

5. **⭐ `ads` 一律不入庫**（SPEC D12）
   SerpApi 回應同時有 `ads`（付費）與 `properties`（自然）兩個陣列，
   **同一家飯店兩邊的價格與 property_token 都不同**
   （實測承攜行旅 ads $1,583 vs properties $1,274，高 24%）。
   解析層只讀 `properties`。混進 `ads` 會系統性高估 10~25%，
   而且數字都很合理，**是看不出來的錯**。

6. **`raw_json` 只存精簡後的報價陣列，不存整包回應**
   token 路徑的完整回應含 images／nearby_places／reviews_breakdown／amenities，
   佔體積 90% 以上而且對分析零用途。A 級每月約 2,520 筆，存整包會是數十 GB 級。
   只保留 `prices[]` 的 source／rate／before_taxes_fees／num_guests／
   free_cancellation／official 六個欄位。

═══════════════════════════════════════════════════════════════════════════
欄位慣例（沿用 `ota_review.py` / `opera_segment.py`）
═══════════════════════════════════════════════════════════════════════════
- SQLAlchemy 2.0 `Mapped[]` / `mapped_column()` 風格
- **日期一律 `String(10)` 存 ISO 字串**（`YYYY-MM-DD`），不用 Date 型別
- **缺值一律空字串不用 NULL**——唯一鍵會用到，SQLite 的 NULL 行為與空字串不同
  （例外：金額與人數允許 NULL，因為「沒有價」與「0 元」語意不同）
- 複合索引寫在 `__table_args__`
- 時間戳一律 `app.core.time.twnow`（台灣時間 naive datetime）
- JSON 一律存 `Text` 並以 `_json` 結尾
- 不使用 `relationship()`（比照 `ota_review.py`，避免 lazy load 在同步 session 裡爆炸）

⚠️ **建表一律走 Alembic migration，不靠 `create_all()`**——
   正式區與測試區都已是 PostgreSQL，而 `create_all()` 補表不補欄位
   （見記憶 project_prod_update_pytag_broken）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── 列舉值（刻意用常數不用 Enum：DB 型別遷移成本高，且值會隨業務增加）──────────
PLAN_LEVELS = ("A", "B", "C")
FETCH_PATHS = ("token", "location")
SOURCES = ("serpapi", "csv", "manual")
# ⭐ 統計取值的優先序（前面的贏）。SPEC D16：
#    唯一鍵含 `source`，所以同一格可以同時有 serpapi 與 csv 兩列。
#    **SerpApi 優先** —— CSV 的用途是補上抓不到的格子，不是覆蓋抓得到的格子。
#    `compset_stats_service` 計算中位數時必須照這個順序取，不可以兩列都算進去
#    （會讓同一家在同一天被算兩次，中位數直接歪掉）。
SOURCE_PRIORITY = ("serpapi", "csv", "manual")
TAX_STATES = ("yes", "no", "unknown")
SOLD_OUT_STATES = ("yes", "no", "unknown")
FETCH_STATUSES = ("running", "success", "partial", "failed",
                  "quota_exceeded", "skipped")


# ══════════════════════════════════════════════════════════════════════════
# 1. 訂閱客戶
# ══════════════════════════════════════════════════════════════════════════
class CompsetSubscriber(Base):
    """
    一個「訂閱客戶」＝ 一組獨立的競爭組、一份分級與一份配額。

    ⚠️ **刻意不沿用 `tenants`**（SPEC D5）。`tenants` 是「據點主檔」，
       鏡像自系統設定的公司/部門管理，語意是**我們自己的公司**；
       把外部付費客戶塞進去會污染既有模型（見記憶 project_user_dept_company_model）。

    內部自用也是一筆訂閱：`code = "INTERNAL"`。

    ⚠️ 級別是**累進**的（SPEC D2）：`plan_level` 存「開放到哪一級」，
       `B` 代表 A＋B、`C` 代表 A＋B＋C。只買 B 不買 A 沒有營運意義。
    """

    __tablename__ = "compset_subscribers"
    __table_args__ = (
        UniqueConstraint("code", name="uq_compset_subscriber_code"),
        Index("ix_compset_subscriber_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    code: Mapped[str] = mapped_column(String(20))            # INTERNAL / 客戶自訂
    name: Mapped[str] = mapped_column(String(100), default="")

    # ── 分級：A / B / C，累進 ───────────────────────────────────────────
    plan_level: Mapped[str] = mapped_column(String(1), default="A")

    # 各級窗口「結束日」（距今天數）。預設 14 / 45 / 120，**不寫死在程式裡**
    window_a_days: Mapped[int] = mapped_column(Integer, default=14)
    window_b_days: Mapped[int] = mapped_column(Integer, default=45)
    window_c_days: Mapped[int] = mapped_column(Integer, default=120)

    # 各級抓取間隔天數。預設 1 / 3 / 7
    freq_a_days: Mapped[int] = mapped_column(Integer, default=1)
    freq_b_days: Mapped[int] = mapped_column(Integer, default=3)
    freq_c_days: Mapped[int] = mapped_column(Integer, default=7)

    # ── 配額（SPEC §3.3）─────────────────────────────────────────────
    # 預設 3500 ＝ 混合路徑（SPEC D10）約 3,153 次／月 ＋ 約 11% 緩衝
    monthly_quota: Mapped[int] = mapped_column(Integer, default=3500)
    quota_used: Mapped[int] = mapped_column(Integer, default=0)

    # ⚠️ 上限 **28**，不接受 29~31：2 月會歸零失敗，
    #    這種「只有兩個月會出錯」的 bug 最難被發現。API 層強制檢查。
    quota_anchor_day: Mapped[int] = mapped_column(Integer, default=1)
    quota_period_start: Mapped[str] = mapped_column(String(10), default="")

    # ── 擷取參數（SPEC §5.6：任一項變更即資料斷點，變更要寫進 fetch_logs）──
    # B／C 級地點查詢用的關鍵字（例如「公館 台北」）。
    # ⚠️ 空字串 ＝ B／C 級無法執行，抓取層會記 warning 並跳過（不會拋例外）。
    #    A 級走 property_token，不需要這個欄位。
    location_query: Mapped[str] = mapped_column(String(100), default="")
    param_adults: Mapped[int] = mapped_column(Integer, default=2)
    param_nights: Mapped[int] = mapped_column(Integer, default=1)
    param_gl: Mapped[str] = mapped_column(String(5), default="tw")
    param_hl: Mapped[str] = mapped_column(String(10), default="zh-tw")
    param_currency: Mapped[str] = mapped_column(String(3), default="TWD")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    contact_name: Mapped[str] = mapped_column(String(50), default="")
    contact_email: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=twnow, onupdate=twnow
    )


# ══════════════════════════════════════════════════════════════════════════
# 2. 訂閱客戶 ↔ 使用者
# ══════════════════════════════════════════════════════════════════════════
class CompsetSubscriberUser(Base):
    """
    哪些使用者「屬於」哪個訂閱客戶（SPEC D14）。

    ⚠️ 這張表存在的唯一理由是**防提權規則 P-1**：
       「不得對自己所屬的 subscriber 加發配額」——
       沒有這條關聯，P-1 根本無從判斷，加發端點等於只剩權限檢查一道關。

    ⚠️ **刻意不用 `users.tenant_id` 推導**（SPEC D5 的同一個理由）：
       `tenant` 是我們自己的「據點」，不是付費客戶。用 tenant 推 subscriber，
       等於又把兩個語意綁回一起。

    多對多：一個 user 可以屬於多個訂閱客戶（例如集團同時管兩家飯店的訂閱），
    一個訂閱客戶也可以有多個使用者。

    ⚠️ 沒有列在這張表裡的使用者（例如內部工程人員）**不屬於任何 subscriber**，
       因此 P-1 不會擋他 —— 這是刻意的：內部調整 INTERNAL 的配額是成本決策，
       不是提權。真正要防的是「客戶的管理員幫自己加額度」。
    """

    __tablename__ = "compset_subscriber_users"
    __table_args__ = (
        UniqueConstraint("subscriber_id", "user_id",
                         name="uq_compset_subscriber_user"),
        Index("ix_compset_subuser_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compset_subscribers.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)


# ══════════════════════════════════════════════════════════════════════════
# 3. 競爭組成員
# ══════════════════════════════════════════════════════════════════════════
class CompsetHotel(Base):
    """
    一個「訂閱客戶 × 飯店」＝ 一筆競爭組成員。

    ⚠️ **每個 subscriber 必須恰有一筆 `is_self = True`**（SPEC §4.2）。
       API 層在存檔時強制檢查（0 筆或 2 筆以上直接擋下）——
       價位指數的分子與分母都依賴它，缺了它整個模組算不出主要指標。
       DB 層沒有辦法用簡單 constraint 表達「恰一筆」，所以這條規則**只在 service 層**，
       改動 CRUD 時不要繞過。

    `hotel_code` 刻意與 OPERA 的 `property_code` 對齊（HANNS / HANNS_SUMMER），
    是為了日後把價位指數與 ADR／OTB Pace 疊圖。⚠️ 但兩者口徑不同（見本檔坑 1）。

    `google_property_token` 是 SerpApi `properties` 區的 token，
    ⚠️ **不是 `ads` 區的 token**（兩者不同，見本檔坑 5）。
    P0 尚未驗證跨日穩定性（TODO 1.2），所以保留 `google_query_name` 當名稱比對退路。
    """

    __tablename__ = "compset_hotels"
    __table_args__ = (
        UniqueConstraint("subscriber_id", "display_name",
                         name="uq_compset_hotel_sub_name"),
        Index("ix_compset_hotel_sub", "subscriber_id", "is_enabled", "sort_order"),
        Index("ix_compset_hotel_self", "subscriber_id", "is_self"),
        Index("ix_compset_hotel_code", "hotel_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    hotel_code: Mapped[str] = mapped_column(String(20), default="")
    display_name: Mapped[str] = mapped_column(String(100))
    #: 表格與標籤用的簡稱（例：「承攜」「捷絲旅」）。
    #: ⚠️ 中文飯店全名普遍 8～12 字（「承攜行旅-台北台大館」「福華國際文教會館」），
    #:    塞不進矩陣的欄位標題，更塞不進 Dashboard 的滿房標籤。
    #: ⚠️ **留空是允許的** —— 讀取端一律用 `short_label` 退回 `display_name`，
    #:    不要在任何地方假設它有值。
    short_name: Mapped[str] = mapped_column(String(20), default="")

    google_property_token: Mapped[str] = mapped_column(String(200), default="")
    google_query_name: Mapped[str] = mapped_column(String(100), default="")

    is_self: Mapped[bool] = mapped_column(Boolean, default=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 觀光署旅宿網的登記資料（規模對照用；⚠️ 地緣一律以登記地址為準，
    # 不要用 Google 的「N 公里遠」——P0 實測那個欄位會把北車/西門町的飯店
    # 列在公館的搜尋結果裡）
    room_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registered_address: Mapped[str] = mapped_column(String(200), default="")

    # 經緯度（來自 SerpApi 的 `gps_coordinates`，或人工填）。
    # ⚠️ **可以是 NULL** —— 手動新增的家不一定有。畫面要能處理「這家沒有座標」。
    # ⚠️ 用 Numeric 不用 Float：Float 在不同 DB 的精度不一致，
    #    小數第 7 位差一位就是一公尺，地圖上會看得出來。
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    note: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=twnow, onupdate=twnow
    )

    @property
    def short_label(self) -> str:
        """簡稱，沒填就退回全名。**顯示端一律走這支，不要直接讀 `short_name`。**"""
        return (self.short_name or "").strip() or self.display_name


# ══════════════════════════════════════════════════════════════════════════
# 4. 價格快照（主表）
# ══════════════════════════════════════════════════════════════════════════
class CompsetRateSnapshot(Base):
    """
    一筆 ＝「某訂閱客戶，在 `snapshot_date` 當天，看到某競品對 `stay_date` 的最低可訂價」。

    ⭐ **`snapshot_date` 是唯一鍵的一部分**，這是整個模組能不能回答
       「競品什麼時候降價」的關鍵。見本檔坑 2。

    ⚠️ 一筆 ＝ 一家飯店一天的**最低**報價，不是每個 OTA 一筆。
       token 路徑一次會回 8~16 個通路報價，全部精簡後放 `raw_json`；
       `ota_name` / `is_official` / `num_guests` 描述的是**最低那筆**來自哪裡。
       日後若要做 rate parity，正解是新開 `compset_rate_offers` 子表，
       而不是把本表的唯一鍵拆掉——本表是「每日一格」的時間序列，
       拆了之後價格軌跡圖與中位數計算全部要重寫。
    """

    __tablename__ = "compset_rate_snapshots"
    __table_args__ = (
        UniqueConstraint("subscriber_id", "snapshot_date", "stay_date",
                         "compset_hotel_id", "source",
                         name="uq_compset_snapshot"),
        # 價格矩陣：某一批快照、某段入住日
        Index("ix_compset_snap_matrix", "subscriber_id", "snapshot_date", "stay_date"),
        # 價格軌跡：固定 stay_date，看各 snapshot_date 的走勢
        Index("ix_compset_snap_trend", "subscriber_id", "stay_date", "snapshot_date"),
        Index("ix_compset_snap_hotel", "compset_hotel_id", "stay_date"),
        Index("ix_compset_snap_soldout", "subscriber_id", "stay_date", "is_sold_out"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    compset_hotel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compset_hotels.id", ondelete="RESTRICT"),
        nullable=False,
    )

    snapshot_date: Mapped[str] = mapped_column(String(10))   # 抓取當日
    stay_date: Mapped[str] = mapped_column(String(10))       # 入住日

    tier: Mapped[str] = mapped_column(String(1), default="")          # A / B / C
    # ⭐ 決定 is_sold_out 可不可信（SPEC D13）
    fetch_path: Mapped[str] = mapped_column(String(10), default="")   # token / location
    source: Mapped[str] = mapped_column(String(20), default="serpapi")

    # ── 價格：兩個口徑都存，統計兩種都算（SPEC D11，見本檔坑 4）──────────
    price_gross: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_pretax: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="TWD")
    # yes / no / unknown ——⚠️ 兩價相同時是 unknown，不是 no
    tax_included: Mapped[str] = mapped_column(String(10), default="unknown")

    # ── 最低那筆報價的來源描述 ──────────────────────────────────────
    ota_name: Mapped[str] = mapped_column(String(50), default="")
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    # ⚠️ 跨家比較前要先對齊人數，否則會拿 3 人房比 2 人房
    num_guests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_cancellation: Mapped[bool] = mapped_column(Boolean, default=False)

    # ⚠️ 原始字串，**不自行正規化成自訂分類**（SPEC §5.2）
    room_type_raw: Mapped[str] = mapped_column(String(200), default="")

    # ⭐ 三態 yes / no / unknown，不是布林（見本檔坑 3）
    is_sold_out: Mapped[str] = mapped_column(String(10), default="unknown")

    # Google 的 typical_price_range，只有 token 路徑有
    typical_low: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    typical_high: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # ⚠️ 精簡後的報價陣列，不是整包回應（見本檔坑 6）
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)


# ══════════════════════════════════════════════════════════════════════════
# 5. 抓取批次紀錄
# ══════════════════════════════════════════════════════════════════════════
class CompsetFetchLog(Base):
    """
    每次抓取一筆，讓「抓取是否真的成功」與「配額扣了多少」都可稽核。

    ⚠️ `warnings_json` 與 `error_message` 的分工不可混用
       （SPEC_ota_reviews §4.3 的教訓）：「某日跳過／某家沒抓到／部分失敗」歸 warnings，
       **只有真正的失敗才寫 `error_message`**。把 warning 當 error 記，
       來源端只要有一點小狀況就永遠黃燈，久了沒人看。

    ⚠️ `row_count = 0` **視為錯誤不是成功**（SPEC §6.3、R3 的教訓）。

    `quota_before` / `quota_after` 一定要寫——配額直接對應對外收費，必須查得回去。
    """

    __tablename__ = "compset_fetch_logs"
    __table_args__ = (
        Index("ix_compset_fetchlog_sub", "subscriber_id", "started_at"),
        Index("ix_compset_fetchlog_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    tier: Mapped[str] = mapped_column(String(1), default="")
    fetch_path: Mapped[str] = mapped_column(String(10), default="")

    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    stay_date_from: Mapped[str] = mapped_column(String(10), default="")
    stay_date_to: Mapped[str] = mapped_column(String(10), default="")

    request_count: Mapped[int] = mapped_column(Integer, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)

    quota_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quota_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # running / success / partial / failed / quota_exceeded / skipped
    status: Mapped[str] = mapped_column(String(20), default="running")

    # gl / hl / currency / adults / nights ＋ 當次使用的窗口與頻率設定
    params_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(String(500), default="")


# ══════════════════════════════════════════════════════════════════════════
# 6. 配額手動加發紀錄
# ══════════════════════════════════════════════════════════════════════════
class CompsetQuotaGrant(Base):
    """
    管理員手動加發一次性額度的紀錄（SPEC §3.4）。

    ⚠️ **加發不修改 `monthly_quota`**，只累加到當期可用額度——
       避免「臨時加一次」變成「永久漲價」。

    ⚠️ 防提權（SPEC §3.5，CLAUDE.md §11 的適用）：這是本模組唯一能
       「自己給自己加錢」的地方。三條規則都在 service／router 層強制：
         P-1 不得對自己所屬的 subscriber 加發（後端檢查，不靠前端隱藏按鈕）
         P-2 只有 `compset_subscriber_admin` 可呼叫，且該 key 不給 portal_general
         P-3 每次加發同時寫 `audit_log`（action="compset_quota_grant"）與本表
    """

    __tablename__ = "compset_quota_grants"
    __table_args__ = (
        Index("ix_compset_grant_sub", "subscriber_id", "granted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    granted_qty: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))      # 必填，API 層擋空字串
    # users.id 是 String(36) UUID
    granted_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    granted_at: Mapped[datetime | None] = mapped_column(DateTime, default=twnow)
    period_start: Mapped[str] = mapped_column(String(10), default="")   # 加在哪一期


# ══════════════════════════════════════════════════════════════════════════
# 7. 每日彙總快取
# ══════════════════════════════════════════════════════════════════════════
class CompsetRateDaily(Base):
    """
    每個「訂閱客戶 × 快照日 × 入住日」的彙總指標。

    ⚠️ **這張表是快取不是來源**：任何時候都必須能從 `compset_rate_snapshots` 重算。
       發現數字怪怪的，第一件事是重算，不是改這張表。

    指標定義（SPEC §7）：
      · `index_pretax = self_pretax ÷ median_pretax`（分母排除 is_self）
      · `index_gross  = self_gross  ÷ median_gross`
      · 中位數**排除** `is_sold_out='yes'` 的家（沒有價就沒有價）
      · ⚠️ `is_sold_out='unknown'` 但**有價格**的家**仍然算進中位數**
        （2026-09-09 修正）。B／C 級每一列都是 unknown，排除它們會讓
        三分之二的產品完全算不出指數。`unknown_count` 保留為資料品質訊號，
        畫面標「遠期資料，滿房狀態未知」
      · `sample_count < 3` 時指數與排名一律標灰並附註「樣本不足」
        （比照 project_opera_reservation_module：填充率必須跟數字一起顯示）
      · 排名顯示成 `self_rank / rank_total`（例如「3 / 5」），
        **不可只寫「第 3 名」**——分母會變動，只給名次會誤導
    """

    __tablename__ = "compset_rate_daily"
    __table_args__ = (
        UniqueConstraint("subscriber_id", "snapshot_date", "stay_date",
                         name="uq_compset_daily"),
        Index("ix_compset_daily_stay", "subscriber_id", "stay_date", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscriber_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("compset_subscribers.id", ondelete="RESTRICT"),
        nullable=False,
    )

    snapshot_date: Mapped[str] = mapped_column(String(10))
    stay_date: Mapped[str] = mapped_column(String(10))

    # ── 稅前口徑（畫面預設）──────────────────────────────────────────
    self_pretax: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    median_pretax: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_pretax: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_pretax: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    index_pretax: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)

    # ── 含稅口徑（旅客實付）──────────────────────────────────────────
    self_gross: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    median_gross: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    min_gross: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_gross: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    index_gross: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)

    # ── 樣本結構（必須與指數一起顯示）───────────────────────────────
    sample_count: Mapped[int] = mapped_column(Integer, default=0)    # 進中位數的家數
    sold_out_count: Mapped[int] = mapped_column(Integer, default=0)  # is_sold_out='yes'
    unknown_count: Mapped[int] = mapped_column(Integer, default=0)   # is_sold_out='unknown'

    self_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    computed_at: Mapped[datetime | None] = mapped_column(
        DateTime, default=twnow, onupdate=twnow
    )
