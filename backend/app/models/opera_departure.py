"""
OPERA 營運分析 — Departure All 原始層與住宿事實表 ORM Model

規格書：docs/SPEC_opera_analytics.md §5.3 / §5.5

⚠️ 實測重點（規格書 §3.1、§3.2）
  1. TXT 表頭 52 欄，但資料列只有 45 欄；索引 45～51（RESV_NAME_ID1、RESORT、
     MEMBERSHIP_*）在匯出時被裁掉，raw 層仍保留欄位定義並寫入空字串。
  2. PROF_ATTACHED 內含換行時，OPERA 會把一筆資料拆成 43 欄 + 3 欄兩個實體列，
     解析階段必須合併；raw 層以 source_row_no / source_row_no_end 保留關係。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── Departure TXT 表頭（固定 52 欄，順序即位置索引）─────────────────────────────
DEPARTURE_COLUMNS: list[str] = [
    "DEPARTURE", "GRP_BY_COL", "GRP_BY_DESC", "SEC_RMNO", "CHAR_DEPDATE",
    "SUM_CHD", "SUM_ADTS", "SUM_NTS", "SUM_RMS", "SUM_BALANCE", "RESORT1",
    "IS_SHARED_YN", "ROOM", "NIGHTS", "ARRIVAL", "NO_OF_ROOMS", "BALANCE",
    "RESV_STATUS", "DEPARTURE_TIME", "COMPUTED_RESV_STATUS", "GUEST_NAME",
    "ADULTS", "CHILDREN", "BLOCK_CODE", "ALLOTMENT_HEADER_ID",
    "ROOM_CATEGORY_LABEL", "COMPANY_NAME", "TRAVEL_AGENT_NAME", "SOURCE_NAME",
    "GROUP_NAME", "ROOM_CATEGORY", "PAYMENT_DESC", "RESV_NAME_ID", "GUEST_NAME_ID",
    "COMPUTED_RESV_STATUS_DISPLAY", "RATE_CODE", "SPECIAL_REQUESTS", "VIP",
    "SHARE_NAMES", "EXTERNAL_REFERENCE", "CHAR_DEPART", "CHAR_ARRIVAL",
    "PROF_ATTACHED", "PROF_COUNT", "RES_COUNT", "RESV_NAME_ID1", "RESORT",
    "MEMBERSHIP_TYPE", "MEMBERSHIP_CARD_NO", "MEMBERSHIP_LEVEL",
    "MEMBERSHIP_TYPE_DESC1", "MEMBERSHIP_LEVEL_DESC1",
]

# 合併續行後每列應有的欄數（規格書 §3.2）
DEPARTURE_MERGED_WIDTH = 45

# 實際存在於資料列的欄數上限（索引 45 起為缺欄）
DEPARTURE_PRESENT_WIDTH = 45

# 敏感欄位：一律不落地（規格書 §13.1）
DEPARTURE_SENSITIVE_COLUMNS = {"MEMBERSHIP_CARD_NO"}

# Departure footer 兩行結構的欄名（規格書 §3.3）
DEPARTURE_FOOTER_KEYS = [
    "SUMBALANCEPERREPORT", "SUMNO_OF_ROOMSPERREPORT", "SUMPERSONSPERREPORT", "LOGO",
]


class OperaDepartureRaw(Base):
    """Departure All 原始層 — 所有來源欄位一律 TEXT，永不覆蓋（規格書 §5.3）"""

    __tablename__ = "opera_departure_raw"

    id:                Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id:          Mapped[int]      = mapped_column(Integer, index=True, default=0)
    source_row_no:     Mapped[int]      = mapped_column(Integer, default=0)
    source_row_no_end: Mapped[int]      = mapped_column(Integer, default=0)
    row_hash:          Mapped[str]      = mapped_column(String(64),  default="", index=True)
    record_key:        Mapped[str]      = mapped_column(String(200), default="", index=True)
    imported_at:       Mapped[datetime] = mapped_column(DateTime, default=twnow)

    # ── 來源欄位（索引 0～44：實際存在）─────────────────────────────────────
    departure:                    Mapped[str] = mapped_column(Text, default="")
    grp_by_col:                   Mapped[str] = mapped_column(Text, default="")
    grp_by_desc:                  Mapped[str] = mapped_column(Text, default="")
    sec_rmno:                     Mapped[str] = mapped_column(Text, default="")
    char_depdate:                 Mapped[str] = mapped_column(Text, default="")
    sum_chd:                      Mapped[str] = mapped_column(Text, default="")
    sum_adts:                     Mapped[str] = mapped_column(Text, default="")
    sum_nts:                      Mapped[str] = mapped_column(Text, default="")
    sum_rms:                      Mapped[str] = mapped_column(Text, default="")
    sum_balance:                  Mapped[str] = mapped_column(Text, default="")
    resort1:                      Mapped[str] = mapped_column(Text, default="")
    is_shared_yn:                 Mapped[str] = mapped_column(Text, default="")
    room:                         Mapped[str] = mapped_column(Text, default="")
    nights:                       Mapped[str] = mapped_column(Text, default="")
    arrival:                      Mapped[str] = mapped_column(Text, default="")
    no_of_rooms:                  Mapped[str] = mapped_column(Text, default="")
    balance:                      Mapped[str] = mapped_column(Text, default="")
    resv_status:                  Mapped[str] = mapped_column(Text, default="")
    departure_time:               Mapped[str] = mapped_column(Text, default="")
    computed_resv_status:         Mapped[str] = mapped_column(Text, default="")
    guest_name:                   Mapped[str] = mapped_column(Text, default="")   # ⚠️ 寫入前已遮罩
    adults:                       Mapped[str] = mapped_column(Text, default="")
    children:                     Mapped[str] = mapped_column(Text, default="")
    block_code:                   Mapped[str] = mapped_column(Text, default="")
    allotment_header_id:          Mapped[str] = mapped_column(Text, default="")
    room_category_label:          Mapped[str] = mapped_column(Text, default="")
    company_name:                 Mapped[str] = mapped_column(Text, default="")
    travel_agent_name:            Mapped[str] = mapped_column(Text, default="")
    source_name:                  Mapped[str] = mapped_column(Text, default="")
    group_name:                   Mapped[str] = mapped_column(Text, default="")
    room_category:                Mapped[str] = mapped_column(Text, default="")
    payment_desc:                 Mapped[str] = mapped_column(Text, default="")
    resv_name_id:                 Mapped[str] = mapped_column(Text, default="")
    guest_name_id:                Mapped[str] = mapped_column(Text, default="")
    computed_resv_status_display: Mapped[str] = mapped_column(Text, default="")
    rate_code:                    Mapped[str] = mapped_column(Text, default="")
    special_requests:             Mapped[str] = mapped_column(Text, default="")
    vip:                          Mapped[str] = mapped_column(Text, default="")
    share_names:                  Mapped[str] = mapped_column(Text, default="")
    external_reference:           Mapped[str] = mapped_column(Text, default="")
    char_depart:                  Mapped[str] = mapped_column(Text, default="")
    char_arrival:                 Mapped[str] = mapped_column(Text, default="")
    prof_attached:                Mapped[str] = mapped_column(Text, default="")
    prof_count:                   Mapped[str] = mapped_column(Text, default="")
    res_count:                    Mapped[str] = mapped_column(Text, default="")

    # ── 來源欄位（索引 45～51：目前匯出被裁掉，恆為空字串）─────────────────
    resv_name_id1:                Mapped[str] = mapped_column(Text, default="")
    resort:                       Mapped[str] = mapped_column(Text, default="")
    membership_type:              Mapped[str] = mapped_column(Text, default="")
    membership_card_no:           Mapped[str] = mapped_column(Text, default="")   # ⚠️ 一律寫入 ""
    membership_level:             Mapped[str] = mapped_column(Text, default="")
    membership_type_desc1:        Mapped[str] = mapped_column(Text, default="")
    membership_level_desc1:       Mapped[str] = mapped_column(Text, default="")

    def to_source_dict(self) -> dict:
        """回傳「原始欄名 → 值」的有序 dict，供前端「原始資料列」Modal 顯示。"""
        return {
            col: getattr(self, col.lower(), "") or ""
            for col in DEPARTURE_COLUMNS
        }


class OperaDepartureStay(Base):
    """Departure 住宿事實表（規格書 §5.5）

    版本管理：同一 record_key 只有一筆 is_current=1。
    """

    __tablename__ = "opera_departure_stay"

    id:         Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id:   Mapped[int] = mapped_column(Integer, index=True, default=0)
    raw_id:     Mapped[int] = mapped_column(Integer, default=0)
    record_key: Mapped[str] = mapped_column(String(200), default="", index=True)
    row_hash:   Mapped[str] = mapped_column(String(64),  default="")
    is_current: Mapped[int] = mapped_column(Integer, default=1, index=True)
    weak_key:   Mapped[int] = mapped_column(Integer, default=0)

    # 飯店與訂房
    property_code:      Mapped[str]        = mapped_column(String(20),  default="", index=True)
    resv_name_id:       Mapped[str]        = mapped_column(String(30),  default="")
    guest_name_id:      Mapped[str | None] = mapped_column(String(30),  nullable=True, default=None)
    external_reference: Mapped[str]        = mapped_column(String(100), default="")
    reservation_status: Mapped[str]        = mapped_column(String(30),  default="")

    # 日期
    arrival_date:           Mapped[str]        = mapped_column(String(10), default="", index=True)
    departure_date:         Mapped[str]        = mapped_column(String(10), default="", index=True)
    departure_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    # 住宿量
    no_of_rooms: Mapped[int] = mapped_column(Integer, default=0)
    nights:      Mapped[int] = mapped_column(Integer, default=0)
    room_nights: Mapped[int] = mapped_column(Integer, default=0)
    adults:      Mapped[int] = mapped_column(Integer, default=0)
    children:    Mapped[int] = mapped_column(Integer, default=0)

    # 房務
    room_no:             Mapped[str] = mapped_column(String(20), default="")
    room_category:       Mapped[str] = mapped_column(String(30), default="")
    room_category_label: Mapped[str] = mapped_column(String(20), default="", index=True)
    is_shared:           Mapped[int] = mapped_column(Integer, default=0)

    # 客源
    company_name:      Mapped[str] = mapped_column(String(200), default="")
    travel_agent_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    source_name:       Mapped[str] = mapped_column(String(200), default="")
    group_name:        Mapped[str] = mapped_column(String(200), default="")
    rate_code:         Mapped[str] = mapped_column(String(50),  default="", index=True)

    # 付款
    payment_desc: Mapped[str]   = mapped_column(String(30), default="")
    balance:      Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    # 住客（⚠️ 姓名只存遮罩版；hash 供分析，Purged 者為 NULL）
    guest_name_masked:   Mapped[str]        = mapped_column(String(100), default="")
    guest_identity_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, index=True)
    is_purged:           Mapped[int]        = mapped_column(Integer, default=0)
    vip:                 Mapped[str]        = mapped_column(String(20), default="")

    # 會員（目前來源無資料，預留）
    membership_type:  Mapped[str] = mapped_column(String(50), default="")
    membership_level: Mapped[str] = mapped_column(String(50), default="")

    imported_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)

    # ── 輔助 ──────────────────────────────────────────────────────────────────

    @property
    def departure_time_str(self) -> str:
        if self.departure_time_minutes is None:
            return ""
        return f"{self.departure_time_minutes // 60:02d}:{self.departure_time_minutes % 60:02d}"

    def to_dict(self) -> dict:
        """列表 + 明細 Drawer 共用（CLAUDE.md §7）

        ⚠️ 兒童數的 key 是 `child_count` 不是 `children`：
           Ant Design Table 預設把 `record.children` 當成「子列陣列」
           （`childrenColumnName` 預設值就是 `'children'`），
           回傳 `children: 2` 會讓 Table 去跑 `2.forEach()` 而整頁白畫面
           （2026-08-04 實際踩過）。這個欄位名在任何要當 Table dataSource
           的 dict 裡都不能用。
        """
        channel = self.travel_agent_name or "直客／未標註"
        return {
            "id":                  self.id,
            "raw_id":              self.raw_id,
            "batch_id":            self.batch_id,
            "record_key":          self.record_key,
            "departure_date":      self.departure_date,
            "arrival_date":        self.arrival_date,
            "departure_time":      self.departure_time_str,
            "room_no":             self.room_no,
            "room_category_label": self.room_category_label,
            "nights":              self.nights,
            "no_of_rooms":         self.no_of_rooms,
            "room_nights":         self.room_nights,
            "adults":              self.adults,
            "child_count":         self.children,   # ⚠️ 不可叫 children，見上方 docstring
            "channel":             channel,
            "travel_agent_name":   self.travel_agent_name,
            "company_name":        self.company_name,
            "rate_code":           self.rate_code,
            "payment_desc":        self.payment_desc,
            "guest_name_masked":   self.guest_name_masked,
            "is_purged":           self.is_purged,
            "vip":                 self.vip,
            "detail": {
                "通路":         channel,
                "公司":         self.company_name or "",
                "Rate Code":    self.rate_code or "",
                "付款方式":     self.payment_desc or "",
                "訂房編號":     self.resv_name_id or "",
                "外部參考號":   self.external_reference or "",
                "訂房狀態":     self.reservation_status or "",
                "房型代碼":     self.room_category_label or "",
                "房型內部 ID":  self.room_category or "",
                "住客":         self.guest_name_masked or "",
                "VIP":          self.vip or "",
                "退房時間":     self.departure_time_str,
                "批次編號":     str(self.batch_id),
                "匯入時間":     self.imported_at.strftime("%Y/%m/%d %H:%M") if self.imported_at else "",
            },
        }
