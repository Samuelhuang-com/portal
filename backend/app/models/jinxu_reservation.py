"""
金旭 PMS 分析 — 訂房狀況表原始層、訂房事實表、住宿明細段

規格書：docs/SPEC_jinxu_analytics.md §7.4 / §7.6 / §7.7

⚠️ 實測重點（規格書 §5，改動前務必先看）
  1. 「訂房號碼」實測 8,716 筆 100% 唯一 → 業務唯一鍵。
  2. 「住宿資料」是打包欄位，格式 `{房型}*{房數}*{晚數}({金額}N)`，一列最多
     12 段、全檔 15,161 段。**必須用 finditer 掃描，不可 split(',')**——金額
     含千分位逗號，naive split 會把一段切成兩半。
  3. `N` 後綴**不是必定存在**（實測 14 段沒有），regex 要寫成選擇性群組，
     否則那 13 列整列解析失敗、夜次對帳會差 14。
  4. 括號內金額是「該段一晚的總額（房數 × 單價）」，**不含晚數**。
     已用團體單 `SK * 8 * 1(54,400N)` = 8 × 6,800 與 FCR02 房租（91.9% 逐筆
     吻合）雙重驗證。段總額 = 金額 × 晚數。
  5. 「登記名稱」含個資 → 遮罩後才落地；hash 依 J13：只做 .strip()，
     字串完全一致才視為同一人。

⚠️ 個資（規格書 §15）
  guest_name_text 存的是**遮罩後**版本，不是原文。原文只存在於 parser 的
  區域變數，不落地、不寫 log。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── RV_detail 來源欄位（固定 10 欄，順序即位置索引）───────────────────────────

RESV_COLUMNS: list[str] = [
    "訂房/登記狀況", "到達日期", "退房日期", "訂房號碼", "登記名稱",
    "合約/訂房公司", "業務碼", "業務源", "訂房類別", "住宿資料",
]

RESV_WIDTH = 10

RESV_HEADER_FIRST = "訂房/登記狀況"

# ── 訂房狀態（規格書 附錄 D.1）────────────────────────────────────────────────
# 狀態碼結構 `{狀態}-{類型}`：前 4 碼狀態、後 2 碼 RV/CO/IH

STATUS_ACTIVE = "ACTV"    # 有效（CO=已退房 / IH=在住 / RV=待到）
STATUS_CANCEL = "CXNL"    # 已取消
STATUS_CONFIRM = "CNFM"   # 已確認未到
STATUS_DUMMY = "DUMY"     # 虛擬訂房
STATUS_NO_SHOW = "NOSH"   # 未到

# J15：DUMY 非實際可入住房間（暫掛訂房／帳務過帳／訂金／團體主帳／系統介接），
#      不計入可售房數與住房率。
STATUS_LABELS = {
    "ACTV-CO": "已退房",
    "ACTV-IH": "在住中",
    "ACTV-RV": "已訂待到",
    "CNFM-RV": "已確認",
    "CXNL-RV": "已取消",
    "DUMY-RV": "虛擬訂房",
    "NOSH-RV": "未到",
}

# 訂房狀態配色（規格書 §13.8，前端 Tag 用）
STATUS_COLORS = {
    "ACTV-CO": "success",
    "ACTV-IH": "processing",
    "ACTV-RV": "warning",
    "CNFM-RV": "warning",
    "CXNL-RV": "error",
    "NOSH-RV": "orange",
    "DUMY-RV": "default",
}

# ── 訂房類別 ──────────────────────────────────────────────────────────────────

RESV_TYPE_FIT = "FIT"   # 散客
RESV_TYPE_GIT = "GIT"   # 團體

# ── 房型代碼（規格書 附錄 D.2，J23：只顯示代碼，不顯示中文名、不分級）────────
# 實測 15 種。刻意**不**提供中文名稱對照——房務尚未提供正式對照表（Q17），
# 自行推斷（如 V 前綴 = 景觀）會讓整份房型分析失真。

KNOWN_ROOM_TYPE_CODES = (
    "PR", "SK", "VDR", "ER", "VER", "VST", "ST", "VPR",
    "VSK", "PS", "VK", "VPS", "SPR", "HS", "SST",
)


class JinxuResvRaw(Base):
    """訂房狀況表原始層（規格書 §7.4）—— 10 欄照存，永不覆蓋。

    ⚠️ guest_name_text 是**遮罩後**版本（§15.2）。
    """

    __tablename__ = "jinxu_resv_raw"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, default=0, index=True)

    source_row_no: Mapped[int] = mapped_column(Integer, default=0)
    row_hash:      Mapped[str] = mapped_column(String(64), default="")
    booking_no:    Mapped[str] = mapped_column(String(20), default="", index=True)

    status_text:       Mapped[str] = mapped_column(Text, default="")
    arrival_text:      Mapped[str] = mapped_column(Text, default="")
    departure_text:    Mapped[str] = mapped_column(Text, default="")
    booking_no_text:   Mapped[str] = mapped_column(Text, default="")
    guest_name_text:   Mapped[str] = mapped_column(Text, default="")   # ⚠️ 遮罩後
    company_text:      Mapped[str] = mapped_column(Text, default="")
    rate_code_text:    Mapped[str] = mapped_column(Text, default="")
    source_text:       Mapped[str] = mapped_column(Text, default="")
    resv_type_text:    Mapped[str] = mapped_column(Text, default="")
    stay_detail_text:  Mapped[str] = mapped_column(Text, default="")

    imported_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)


class JinxuReservation(Base):
    """訂房事實表（規格書 §7.6）

    業務鍵：booking_no（＝「訂房號碼」），UNIQUE。
    覆蓋規則（§8.2）：撞鍵且 row_hash 不同 → UPDATE，且**子表整組重建**
    （DELETE + 重新拆段），不做逐段 UPDATE。

    ⚠️ 統計母體（§11.4）：營運統計必須帶 is_cancelled=0 AND is_dummy=0。
       實測取消佔 29.7%，母體選錯數字差三成。
    """

    __tablename__ = "jinxu_reservation"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    raw_id:   Mapped[int] = mapped_column(Integer, default=0)

    booking_no: Mapped[str] = mapped_column(String(20), default="", unique=True, index=True)
    row_hash:   Mapped[str] = mapped_column(String(64), default="")

    first_imported_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    last_updated_at:   Mapped[datetime] = mapped_column(DateTime, default=twnow)

    # ── 狀態 ──────────────────────────────────────────────────────────────────
    status_code:  Mapped[str] = mapped_column(String(10), default="", index=True)
    status_main:  Mapped[str] = mapped_column(String(10), default="")
    status_kind:  Mapped[str] = mapped_column(String(10), default="")
    is_cancelled: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_dummy:     Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_no_show:   Mapped[int] = mapped_column(Integer, default=0)

    # ── 日期 ──────────────────────────────────────────────────────────────────
    arrival_date:   Mapped[str] = mapped_column(String(10), default="", index=True)
    departure_date: Mapped[str] = mapped_column(String(10), default="", index=True)
    nights:         Mapped[int] = mapped_column(Integer, default=0)
    # J27：Day Use（同日進出）日期差為 0，但金旭住宿段寫 1 晚且確實收房租。
    #      兩種口徑都存，前端可切換；報表必須明確標示用哪一種。
    billable_nights: Mapped[int] = mapped_column(Integer, default=0)
    is_day_use:     Mapped[int] = mapped_column(Integer, default=0)

    # ── 客戶（⚠️ 個資，§15.2）────────────────────────────────────────────────
    guest_name_masked:    Mapped[str] = mapped_column(String(100), default="")
    # J13：hash = sha256(property_code + "|" + 原文.strip())，不轉大小寫、
    #      不做任何其他正規化。字串不一致即視為不同人。
    guest_identity_hash:  Mapped[str] = mapped_column(String(64), default="", index=True)
    # J14：OTHERS／公司名／訂房壓房等非人名 → 1，排除於回訪分析
    guest_is_placeholder: Mapped[int] = mapped_column(Integer, default=0, index=True)
    guest_has_cjk:        Mapped[int] = mapped_column(Integer, default=0)

    # ── 通路（J18/J19：照原值，不合併、不特別處理 SiteMinder）────────────────
    company_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    rate_code:    Mapped[str] = mapped_column(String(50), default="", index=True)
    source_name:  Mapped[str] = mapped_column(String(50), default="")
    resv_type:    Mapped[str] = mapped_column(String(10), default="")
    is_group:     Mapped[int] = mapped_column(Integer, default=0)

    # ── 住宿彙總（由子表回填）────────────────────────────────────────────────
    stay_segment_count:  Mapped[int] = mapped_column(Integer, default=0)
    total_room_nights:   Mapped[int] = mapped_column(Integer, default=0)   # 夜次對帳用
    total_quoted_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    room_type_codes:     Mapped[str] = mapped_column(String(100), default="")
    # J22：段晚數加總 != 住宿天數 → 標 1，記錄但不阻擋（實測 241 筆／2.8%）
    has_nights_mismatch: Mapped[int] = mapped_column(Integer, default=0, index=True)

    property_code: Mapped[str] = mapped_column(String(20), default="")


class JinxuReservationStay(Base):
    """住宿明細段（規格書 §7.7）—— 「住宿資料」拆解後一段一列。

    實測 8,716 訂房 → 15,161 段。

    金額語意（§5.3 坑 3）：
        amount_per_night = 括號內金額 = 該段「一晚」的總額（房數 × 單價）
        unit_rate        = amount_per_night / rooms   每房每晚單價
        room_nights      = rooms * nights
        segment_amount   = amount_per_night * nights  ← 乘晚數，不是乘房數
    """

    __tablename__ = "jinxu_reservation_stay"

    id:             Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reservation_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    booking_no:     Mapped[str] = mapped_column(String(20), default="", index=True)

    seq_no:         Mapped[int] = mapped_column(Integer, default=0)
    room_type_code: Mapped[str] = mapped_column(String(10), default="", index=True)
    rooms:          Mapped[int] = mapped_column(Integer, default=0)
    nights:         Mapped[int] = mapped_column(Integer, default=0)

    amount_per_night: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    unit_rate:        Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    room_nights:      Mapped[int] = mapped_column(Integer, default=0)
    segment_amount:   Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)

    # 0 = 原字串缺 N 後綴（實測 14 段），僅記錄不影響計算
    has_n_suffix: Mapped[int] = mapped_column(Integer, default=1)
    raw_segment:  Mapped[str] = mapped_column(String(50), default="")
