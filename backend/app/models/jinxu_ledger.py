"""
金旭 PMS 分析 — FCR02 客帳帳目原始層、交易分錄事實表、科目分類對照表

規格書：docs/SPEC_jinxu_analytics.md §7.3 / §7.5 / §7.8

⚠️ 實測重點（規格書 §4，改動前務必先看）
  1. FCR02 是分組列印報表：52,310 列中只有 40,706 列是資料，其餘是重複表頭
     （2,900）、分組小計（2,900）、空白（5,801）、標題與簽核列。
  2. 「日期」是營業日、「建檔時間」是系統寫入時戳，實測 46.7% 兩者不同（夜稽
     跨日）。統計歸期一律用 business_date，**絕不可用 create_seq[:8]**。
  3. 「建檔時間」實測 40,706 筆 100% 唯一 → 直接當業務唯一鍵，不需要 OPERA
     那套 record_key + weak_key 機制。
  4. 沖帳判定用「收入類科目 + 金額為負」，**不可只靠備註字串**——實測 186 筆
     沖帳沒寫備註。
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow

# ── FCR02 來源欄位（固定 14 欄，順序即位置索引）────────────────────────────────

FCR02_COLUMNS: list[str] = [
    "日期", "建檔時間", "班別", "ID", "房號", "帳單名稱", "科目",
    "金額", "單據號碼", "應收代碼", "備註", "轉帳", "訂房號碼", "帳單別",
]

FCR02_WIDTH = 14

# 表頭第 4 欄原文是 " ID"（含前導空格），比對時需 .strip()
FCR02_HEADER_FIRST = "日期"
FCR02_HEADER_SECOND = "建檔時間"

# ── 科目分側（規格書 §11.1）───────────────────────────────────────────────────

SIDE_REVENUE = "REVENUE"        # 收入（科目代碼數字 < 71）
SIDE_SETTLEMENT = "SETTLEMENT"  # 抵充（科目代碼數字 >= 71）

SETTLEMENT_CODE_THRESHOLD = 71

# ── 科目大類（規格書 附錄 C）──────────────────────────────────────────────────

GROUP_ROOM = "ROOM"                 # 房費
GROUP_SERVICE = "SERVICE"           # 加值服務
GROUP_TELECOM = "TELECOM"           # 通訊
GROUP_DEPOSIT_IN = "DEPOSIT_IN"     # 預收訂金（收）
GROUP_OTHER_REV = "OTHER_REV"       # 其他收入
GROUP_CARD = "CARD"                 # 信用卡
GROUP_EPAY = "EPAY"                 # 電子支付
GROUP_CASH = "CASH"                 # 現金
GROUP_DEPOSIT_OUT = "DEPOSIT_OUT"   # 預收訂金（沖）
GROUP_AR = "AR"                     # 簽帳
GROUP_OTHER_SET = "OTHER_SET"       # 其他抵充
GROUP_UNCLASSIFIED = "UNCLASSIFIED" # 未分類（未知科目自動歸此）

GROUP_LABELS = {
    GROUP_ROOM: "房費",
    GROUP_SERVICE: "加值服務",
    GROUP_TELECOM: "通訊",
    GROUP_DEPOSIT_IN: "預收訂金",
    GROUP_OTHER_REV: "其他",
    GROUP_CARD: "信用卡",
    GROUP_EPAY: "電子支付",
    GROUP_CASH: "現金",
    GROUP_DEPOSIT_OUT: "預收訂金",
    GROUP_AR: "簽帳",
    GROUP_OTHER_SET: "其他",
    GROUP_UNCLASSIFIED: "未分類",
}

# 預收訂金對沖科目（規格書 §11.8，J21：只做總額層級，不做逐筆配對）
DEPOSIT_IN_CODES = ("64", "64A")
DEPOSIT_OUT_CODES = ("81", "81A")

# 純記錄性分錄（J20）：實測 587 筆金額恆為 0，排除於收入統計
MEMO_ONLY_CODES = ("39", "67", "61")

# ── 班別（規格書 §4.8，J16）──────────────────────────────────────────────────
#  A/B/C/D = 人工班別；X = 話務與自助洗衣自動計費；Y = 洗衣；N = 轉帳作業
#  J16 決策：只有 N 排除於班別分析。X（596,194）與 Y（375,166）是真實收入，
#  在所有金額統計中全數保留。
SHIFT_EXCLUDED_FROM_SHIFT_ANALYSIS = ("N",)

# ── 房號類別（規格書 §4.8，J24）──────────────────────────────────────────────
ROOM_KIND_GUEST = "GUEST"   # 客房：房號前 2 碼為數字（03~12 樓）
ROOM_KIND_OTHER = "OTHER"   # 非客房：H0 / M0 / OT / RV（實測 1,615 筆）

_SUBJECT_CODE_RE = re.compile(r"^\s*(\d+[A-Za-z]?)")
_LEADING_DIGITS_RE = re.compile(r"^(\d+)")


def split_subject(raw: str) -> tuple[str, str]:
    """把「01.房租」拆成 ("01", "房租")。無法解析時回傳 ("", 原文)。"""
    text = (raw or "").strip()
    if not text:
        return "", ""
    m = _SUBJECT_CODE_RE.match(text)
    if not m:
        return "", text
    code = m.group(1).upper()
    name = text[m.end():].lstrip(".． ").strip()
    return code, name


def subject_side(subject_code: str) -> str:
    """依科目代碼的數字前綴判斷收入／抵充。

    ⚠️ 一律用數字前綴，**不可用中文名稱比對**（科目名稱可能改）。
    """
    m = _LEADING_DIGITS_RE.match(subject_code or "")
    if not m:
        return SIDE_REVENUE
    return SIDE_SETTLEMENT if int(m.group(1)) >= SETTLEMENT_CODE_THRESHOLD else SIDE_REVENUE


def classify_room_kind(room_no: str) -> str:
    """房號前 2 碼為數字 → 客房；否則非客房（J24：仍寫入 DB，統計另立區塊）。"""
    text = (room_no or "").strip()
    return ROOM_KIND_GUEST if text[:2].isdigit() else ROOM_KIND_OTHER


class JinxuFcr02Raw(Base):
    """FCR02 原始層（規格書 §7.3）—— 14 欄原文照存，永不覆蓋。"""

    __tablename__ = "jinxu_fcr02_raw"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, default=0, index=True)

    source_row_no: Mapped[int] = mapped_column(Integer, default=0)
    row_hash:      Mapped[str] = mapped_column(String(64), default="")
    create_seq:    Mapped[str] = mapped_column(String(20), default="", index=True)

    date_text:        Mapped[str] = mapped_column(Text, default="")
    create_seq_text:  Mapped[str] = mapped_column(Text, default="")
    shift_text:       Mapped[str] = mapped_column(Text, default="")
    operator_text:    Mapped[str] = mapped_column(Text, default="")
    room_no_text:     Mapped[str] = mapped_column(Text, default="")
    folio_name_text:  Mapped[str] = mapped_column(Text, default="")
    subject_text:     Mapped[str] = mapped_column(Text, default="")
    amount_text:      Mapped[str] = mapped_column(Text, default="")
    document_no_text: Mapped[str] = mapped_column(Text, default="")
    ar_code_text:     Mapped[str] = mapped_column(Text, default="")
    remark_text:      Mapped[str] = mapped_column(Text, default="")   # J17：存但全站不顯示
    transfer_text:    Mapped[str] = mapped_column(Text, default="")
    booking_no_text:  Mapped[str] = mapped_column(Text, default="")
    folio_type_text:  Mapped[str] = mapped_column(Text, default="")

    imported_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)


class JinxuLedgerEntry(Base):
    """交易分錄事實表（規格書 §7.5）

    業務鍵：create_seq（＝「建檔時間」），UNIQUE。
    覆蓋規則（§8.2）：撞鍵且 row_hash 不同 → UPDATE；相同 → SKIP。
    ⚠️ 不設 is_current。分錄一經產生內容不應變動，若變動代表金旭端修正，
       覆蓋才是正確語意。
    """

    __tablename__ = "jinxu_ledger_entry"

    id:       Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(Integer, default=0, index=True)
    raw_id:   Mapped[int] = mapped_column(Integer, default=0)

    create_seq: Mapped[str] = mapped_column(String(20), default="", unique=True, index=True)
    row_hash:   Mapped[str] = mapped_column(String(64), default="")

    first_imported_at: Mapped[datetime] = mapped_column(DateTime, default=twnow)
    last_updated_at:   Mapped[datetime] = mapped_column(DateTime, default=twnow)

    # ── 日期 ──────────────────────────────────────────────────────────────────
    # business_date 是唯一的統計歸期依據（§4.3）
    business_date:   Mapped[str] = mapped_column(String(10), default="", index=True)
    created_at_text: Mapped[str] = mapped_column(String(20), default="")
    created_date:    Mapped[str] = mapped_column(String(10), default="")  # 僅供稽核

    # ── 作業 ──────────────────────────────────────────────────────────────────
    shift:           Mapped[str] = mapped_column(String(2), default="")
    is_manual_shift: Mapped[int] = mapped_column(Integer, default=1)   # J16：只有 N = 0
    operator_id:     Mapped[str] = mapped_column(String(20), default="", index=True)

    # ── 帳務 ──────────────────────────────────────────────────────────────────
    room_no:    Mapped[str] = mapped_column(String(20), default="", index=True)
    room_kind:  Mapped[str] = mapped_column(String(10), default=ROOM_KIND_GUEST, index=True)
    folio_name: Mapped[str] = mapped_column(String(100), default="")
    folio_seq:  Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    folio_type: Mapped[str] = mapped_column(String(20), default="")

    # ── 科目 ──────────────────────────────────────────────────────────────────
    subject_code:  Mapped[str] = mapped_column(String(10), default="", index=True)
    subject_name:  Mapped[str] = mapped_column(String(50), default="")
    subject_side:  Mapped[str] = mapped_column(String(10), default=SIDE_REVENUE, index=True)
    subject_group: Mapped[str] = mapped_column(String(20), default=GROUP_UNCLASSIFIED, index=True)

    # ── 金額 ──────────────────────────────────────────────────────────────────
    amount:       Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    is_reversal:  Mapped[int] = mapped_column(Integer, default=0, index=True)  # 沖帳
    is_memo_only: Mapped[int] = mapped_column(Integer, default=0, index=True)  # J20 純記錄

    # ── 關聯 ──────────────────────────────────────────────────────────────────
    booking_no:  Mapped[str] = mapped_column(String(20), default="", index=True)
    document_no: Mapped[str] = mapped_column(String(30), default="")
    ar_code:     Mapped[str] = mapped_column(String(50), default="")
    transfer_no: Mapped[str] = mapped_column(String(30), default="")
    # J17：儲存但全站不顯示。API 一律不得回傳此欄。
    remark:      Mapped[str] = mapped_column(String(255), default="")

    property_code: Mapped[str] = mapped_column(String(20), default="")


class JinxuSubjectMap(Base):
    """科目分類對照表（規格書 §7.8）

    分類不寫死在程式碼，存 DB 供管理員維護。遇到未登錄的科目代碼時
    **不可拒絕該列**，改以 side 推斷、group 設 UNCLASSIFIED 並發 WARNING。
    """

    __tablename__ = "jinxu_subject_map"

    id:           Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_code: Mapped[str] = mapped_column(String(10), default="", unique=True, index=True)
    subject_name: Mapped[str] = mapped_column(String(50), default="")
    side:         Mapped[str] = mapped_column(String(10), default=SIDE_REVENUE)
    group_code:   Mapped[str] = mapped_column(String(20), default=GROUP_UNCLASSIFIED)
    sort_order:   Mapped[int] = mapped_column(Integer, default=999)
    is_memo_only: Mapped[int] = mapped_column(Integer, default=0)   # J20
    is_active:    Mapped[int] = mapped_column(Integer, default=1)

    updated_at:         Mapped[datetime] = mapped_column(DateTime, default=twnow)
    updated_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
