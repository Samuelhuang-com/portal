"""
稽核檢查（財#3 系統建置稽核）— SQLAlchemy ORM 模型

中文名稱：稽核檢查
英文名稱：Audit Check
前端路由：/audit-check/*      （手機版 /m/audit-check）
後端 router：app/routers/audit_check.py   （prefix /api/v1/audit-check）
對應 Excel：財_3系統建置稽核-202609執行.xlsx
規格文件：docs/SPEC_audit_check.md

設計重點（2026-09-20 使用者裁示）
────────────────────────────────────────────────────────────────────────────
1. 判定（原 Excel 的字色）改為**使用者自訂主檔** `audit_result_types`：
   名稱、顏色、是否算達標、是否列入缺失彙整，全部由使用者在設定頁維護。
   預設三筆（達標／扣分／建議）為系統內建，可改名改色但不可刪除。
2. 稽核子項數／達標項數／各部門分數一律**即時計算**，不存欄位。
3. 檢查項主檔可新增、改名、停用；**已被任一期稽核單引用即鎖定**（只能停用）。
4. 每期稽核單的檢查項與部門欄皆從主檔勾選，兩家公司可各自不同。
5. 公司別／部門一律沿用 settings/company-departments 的 companies /
   departments（reference_data.py），**不另建主檔**。因同屬 portal 資料庫，
   直接建 FK 即可，不需要比照週期採購做鏡像同步。

⚠️ CLAUDE.md §0：本模組一律 PostgreSQL，新表／改欄位一律走 Alembic migration。
⚠️ 時間一律用 app.core.time.twnow()，不得用 datetime.now() / date.today()。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import twnow


def _now() -> datetime:
    return twnow()


# ── 判定類型主檔（使用者自訂字色語意）──────────────────────────────────────
class AuditResultType(Base):
    """
    判定類型 — 取代 Excel 的「紅字＝扣分、藍字＝建議、黑字＝正常」慣例。

    使用者可自行新增類型、改名稱、改顏色，並自行決定：
      - counts_as_pass      ：是否計入「達標項數」
      - include_in_summary  ：是否出現在「缺失」彙整列
    """
    __tablename__ = "audit_result_types"

    id                 = Column(Integer,     primary_key=True, autoincrement=True)
    code               = Column(String(20),  nullable=False, unique=True, comment="程式用代碼（建立後不可改）")
    label              = Column(String(50),  nullable=False, comment="顯示名稱，如「扣分」")
    color              = Column(String(20),  nullable=False, default="#000000", comment="文字色碼 #RRGGBB")
    counts_as_pass     = Column(Boolean,     nullable=False, default=True,  comment="是否算達標（False 才扣分）")
    include_in_summary = Column(Boolean,     nullable=False, default=False, comment="是否列入「缺失」自動彙整")
    is_default         = Column(Boolean,     nullable=False, default=False, comment="新格子的預設判定（全表僅一筆為 True）")
    is_system          = Column(Boolean,     nullable=False, default=False, comment="系統內建，不可刪除（仍可改名改色）")
    sort_order         = Column(Integer,     nullable=False, default=0)
    is_active          = Column(Boolean,     nullable=False, default=True)
    created_at         = Column(DateTime,    nullable=False, default=_now)
    updated_at         = Column(DateTime,    nullable=False, default=_now, onupdate=_now)


# ── 檢查項主檔（兩階，自我參照）────────────────────────────────────────────
class AuditItem(Base):
    """
    檢查項主檔。parent_id 為 NULL ＝ 1 階大項；非 NULL ＝ 2 階子項。

    name 只存**純項目名稱**，不含 Excel 裡的「-工程.管理」部門後綴，也不含
    「(飲水機.排煙.污水設備)」這類店別補充——那兩者隨期別／公司而異，分別
    存在 AuditSheetItem.scope_note 與 AuditItemTarget。
    """
    __tablename__ = "audit_items"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_audit_items_parent_name"),
    )

    id          = Column(Integer,     primary_key=True, autoincrement=True)
    parent_id   = Column(Integer,     ForeignKey("audit_items.id", ondelete="CASCADE"), nullable=True)
    name        = Column(String(200), nullable=False, comment="項目名稱（純名稱）")
    description = Column(Text,        nullable=True,  comment="說明")
    sort_order  = Column(Integer,     nullable=False, default=0)
    is_active   = Column(Boolean,     nullable=False, default=True)
    created_at  = Column(DateTime,    nullable=False, default=_now)
    updated_at  = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    children = relationship(
        "AuditItem",
        backref="parent",
        remote_side=[id],
        uselist=True,
        viewonly=True,
    )


# ── 稽核期別（一個月一期）──────────────────────────────────────────────────
class AuditPeriod(Base):
    __tablename__ = "audit_periods"

    id          = Column(Integer,    primary_key=True, autoincrement=True)
    period      = Column(String(7),  nullable=False, unique=True, comment="YYYY-MM")
    title       = Column(String(100), nullable=False, default="財#3系統建置稽核")
    goal_major  = Column(Integer,    nullable=False, default=3, comment="目標大項數")
    goal_minor  = Column(Integer,    nullable=False, default=3, comment="每大項目標子項數")
    note        = Column(Text,       nullable=True,  comment="稽核方式說明（顯示於統計頁）")
    review_counts_in_score = Column(
        Boolean, nullable=False, default=True,
        comment="覆核區（待補正項目／結果）是否計為該部門的一個稽核子項；見 service 口徑說明",
    )
    status      = Column(String(20), nullable=False, default="open", comment="draft / open / closed")
    created_by  = Column(String(36), nullable=True)
    created_at  = Column(DateTime,   nullable=False, default=_now)
    updated_at  = Column(DateTime,   nullable=False, default=_now, onupdate=_now)

    sheets = relationship(
        "AuditSheet",
        back_populates="period_ref",
        cascade="all, delete-orphan",
    )


# ── 稽核單（期別 × 公司）──────────────────────────────────────────────────
class AuditSheet(Base):
    __tablename__ = "audit_sheets"
    __table_args__ = (
        UniqueConstraint("period_id", "company_id", name="uq_audit_sheets_period_company"),
    )

    id              = Column(Integer,     primary_key=True, autoincrement=True)
    period_id       = Column(Integer,     ForeignKey("audit_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id      = Column(Integer,     ForeignKey("companies.id"), nullable=False, index=True)
    audited_on      = Column(Date,        nullable=True,  comment="查核日期")
    audited_session = Column(String(10),  nullable=True,  comment="上午 / 下午")
    executor_label  = Column(String(50),  nullable=True,  comment="如「台北執行:項數」")
    completion_adjust = Column(
        Integer, nullable=False, default=0,
        comment="完成率「已完成數」的人工調整（Excel 的「3*3-1=8」：本期少做一項填 -1，分母仍是 3*3）",
    )
    remark          = Column(Text,        nullable=True,  comment="表尾自由備註")
    status          = Column(String(20),  nullable=False, default="draft", comment="draft / submitted / reviewed")
    created_by      = Column(String(36),  nullable=True)
    created_at      = Column(DateTime,    nullable=False, default=_now)
    updated_at      = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    period_ref  = relationship("AuditPeriod", back_populates="sheets")
    company     = relationship("Company")
    departments = relationship(
        "AuditSheetDepartment",
        back_populates="sheet",
        cascade="all, delete-orphan",
        order_by="AuditSheetDepartment.sort_order",
    )
    items = relationship(
        "AuditSheetItem",
        back_populates="sheet",
        cascade="all, delete-orphan",
        order_by="AuditSheetItem.sort_order",
    )
    cells = relationship(
        "AuditCell",
        back_populates="sheet",
        cascade="all, delete-orphan",
    )
    reviews = relationship(
        "AuditReview",
        back_populates="sheet",
        cascade="all, delete-orphan",
    )


# ── 稽核單的部門欄 ─────────────────────────────────────────────────────────
class AuditSheetDepartment(Base):
    __tablename__ = "audit_sheet_departments"
    __table_args__ = (
        UniqueConstraint("sheet_id", "department_id", name="uq_audit_sheet_dept"),
    )

    id                  = Column(Integer,     primary_key=True, autoincrement=True)
    sheet_id            = Column(Integer,     ForeignKey("audit_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id       = Column(Integer,     ForeignKey("departments.id"), nullable=False)
    column_label        = Column(String(50),  nullable=True, comment="顯示覆寫；空值取部門名稱")
    sort_order          = Column(Integer,     nullable=False, default=0)
    deficiency_override = Column(Text,        nullable=True, comment="「缺失」人工覆寫；空值＝自動彙整")

    sheet      = relationship("AuditSheet", back_populates="departments")
    department = relationship("RefDepartment")


# ── 稽核單的檢查項（列）───────────────────────────────────────────────────
class AuditSheetItem(Base):
    __tablename__ = "audit_sheet_items"
    __table_args__ = (
        UniqueConstraint("sheet_id", "item_id", name="uq_audit_sheet_item"),
    )

    id                   = Column(Integer,     primary_key=True, autoincrement=True)
    sheet_id             = Column(Integer,     ForeignKey("audit_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id              = Column(Integer,     ForeignKey("audit_items.id"), nullable=False)
    parent_sheet_item_id = Column(Integer,     ForeignKey("audit_sheet_items.id", ondelete="CASCADE"), nullable=True)
    display_no           = Column(String(10),  nullable=True, comment="該期顯示序號 1 / 1.1")
    scope_note           = Column(String(200), nullable=True, comment="店別補充，如「(飲水機.排煙.污水設備)」")
    sort_order           = Column(Integer,     nullable=False, default=0)

    sheet   = relationship("AuditSheet", back_populates="items")
    item    = relationship("AuditItem")
    targets = relationship(
        "AuditItemTarget",
        back_populates="sheet_item",
        cascade="all, delete-orphan",
    )


# ── 該期該項的「建議查核部門」後綴 ──────────────────────────────────────────
class AuditItemTarget(Base):
    __tablename__ = "audit_item_targets"
    __table_args__ = (
        UniqueConstraint("sheet_item_id", "department_id", name="uq_audit_item_target"),
    )

    id            = Column(Integer, primary_key=True, autoincrement=True)
    sheet_item_id = Column(Integer, ForeignKey("audit_sheet_items.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)

    sheet_item = relationship("AuditSheetItem", back_populates="targets")
    department = relationship("RefDepartment")


# ── 交叉格（資料主體）──────────────────────────────────────────────────────
class AuditCell(Base):
    """
    一格 ＝ 一個檢查項 × 一個部門的查核評語與判定。

    ⚠️ comment 為空的格子**不建列**（或寫入時刪除），因為「沒填 ＝ 該部門本期
       不查此項」，不計入分數分母。這條規則同時寫在 service 層。
    """
    __tablename__ = "audit_cells"
    __table_args__ = (
        UniqueConstraint("sheet_item_id", "sheet_department_id", name="uq_audit_cells_item_dept"),
    )

    id                  = Column(Integer,    primary_key=True, autoincrement=True)
    sheet_id            = Column(Integer,    ForeignKey("audit_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_item_id       = Column(Integer,    ForeignKey("audit_sheet_items.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_department_id = Column(Integer,    ForeignKey("audit_sheet_departments.id", ondelete="CASCADE"), nullable=False, index=True)
    comment             = Column(Text,       nullable=True, comment="查核評語（可多行）")
    result_code         = Column(String(20), nullable=False, default="ok", comment="對應 audit_result_types.code")
    updated_by          = Column(String(36), nullable=True)
    created_at          = Column(DateTime,   nullable=False, default=_now)
    updated_at          = Column(DateTime,   nullable=False, default=_now, onupdate=_now)

    sheet = relationship("AuditSheet", back_populates="cells")


# ── 覆核區（上期待補正項目 + 結果）─────────────────────────────────────────
class AuditReview(Base):
    __tablename__ = "audit_reviews"
    __table_args__ = (
        UniqueConstraint("sheet_id", "sheet_department_id", name="uq_audit_reviews_sheet_dept"),
    )

    id                  = Column(Integer,    primary_key=True, autoincrement=True)
    sheet_id            = Column(Integer,    ForeignKey("audit_sheets.id", ondelete="CASCADE"), nullable=False, index=True)
    sheet_department_id = Column(Integer,    ForeignKey("audit_sheet_departments.id", ondelete="CASCADE"), nullable=False)
    source_period       = Column(String(7),  nullable=True, comment="待補正項目的來源期別 YYYY-MM")
    pending_text        = Column(Text,       nullable=True, comment="上期待補正項目")
    pending_result      = Column(String(20), nullable=False, default="ok")
    result_text         = Column(Text,       nullable=True, comment="覆核結果")
    result_status       = Column(String(20), nullable=False, default="ok")
    updated_at          = Column(DateTime,   nullable=False, default=_now, onupdate=_now)

    sheet = relationship("AuditSheet", back_populates="reviews")
