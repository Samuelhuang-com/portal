"""
稽核檢查 → KPO 稽核（財#1 稽核系統建構）— SQLAlchemy ORM 模型

中文名稱：KPO 稽核（稽核檢查子模組）
英文名稱：Audit KPO
前端路由：/audit-check/kpo/*
後端 router：app/routers/audit_kpo.py   （prefix /api/v1/audit-check/kpo）
對應 Excel：財#1稽核系統建構（SheetA 整合／SheetB 2026.11 執行／各部門 Sheet）
規格文件：docs/SPEC_audit_kpo.md

資料結構（對應 Excel）
────────────────────────────────────────────────────────────────────────────
Excel「整合」Sheet：每個部門一個區塊（B2~Z2 為各部門），每區塊 16 項「品質項目」，
欄位＝項數／品質項目／分數／符合／不符合／備註；★ 為重點項（10 分），其餘 5 分，合計 100。
「2026.11 執行」Sheet：每部門每期從 16 項挑 4 項（1★＋3 項＝25 分）。

  audit_kpo_departments   KPO 部門（營業／客服停管／行銷…共 9 個）
  audit_kpo_items         各部門稽核項目主檔（依 Excel 整合 Sheet 植入，可編輯）
  audit_kpo_periods       稽核期別（月）
  audit_kpo_period_items  每期每部門「選定」的稽核項目；項目內容為**快照**，
                          主檔事後改名／刪除不影響已選定的歷史期別

⚠️ CLAUDE.md §0：一律 PostgreSQL，新表走 Alembic migration（20261010_kpoaud）。
⚠️ 時間一律用 app.core.time.twnow()。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import twnow


def _now() -> datetime:
    return twnow()


class AuditKpoDept(Base):
    """KPO 部門。集團層級（不分公司別），名稱取自 Excel 各部門區塊。"""
    __tablename__ = "audit_kpo_departments"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_audit_kpo_dept_company_name"),
    )

    id           = Column(Integer,     primary_key=True, autoincrement=True)
    name         = Column(String(100), nullable=False, index=True, comment="部門名稱（連結部門時取自 settings/company-departments）")
    company_id   = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True,
                          comment="公司別（settings/company-departments）；NULL＝Excel 植入、尚未連結")
    ref_department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True,
                          comment="部門別（settings/company-departments）；NULL＝尚未連結")
    source_title = Column(String(200), nullable=True,  comment="Excel 原標題（含會議定案日期），僅供參考")
    sort_order   = Column(Integer,     nullable=False, default=0)
    is_active    = Column(Boolean,     nullable=False, default=True)
    created_at   = Column(DateTime,    nullable=False, default=_now)
    updated_at   = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    items = relationship(
        "AuditKpoItem", back_populates="department",
        cascade="all, delete-orphan", order_by="AuditKpoItem.sort_order",
    )
    company = relationship("Company", foreign_keys=[company_id], lazy="joined")

    @property
    def display_name(self) -> str:
        """有連結公司別時顯示「公司｜部門」，同名部門（各公司都有營業部）才分得出來。"""
        return f"{self.company.name}｜{self.name}" if self.company is not None else self.name


class AuditKpoItem(Base):
    """各部門稽核項目主檔（Excel 的一列「品質項目」）。"""
    __tablename__ = "audit_kpo_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("audit_kpo_departments.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    item_no       = Column(Integer, nullable=True,  comment="項數（Excel B 欄去掉 ★ 後的數字）")
    is_key        = Column(Boolean, nullable=False, default=False, comment="★ 重點項")
    name          = Column(Text,    nullable=False, comment="品質項目")
    score         = Column(Integer, nullable=False, default=5, comment="分數（★ 通常 10、其餘 5）")
    method        = Column(Text,    nullable=True,  comment="備註／查核方式")
    sort_order    = Column(Integer, nullable=False, default=0)
    is_active     = Column(Boolean, nullable=False, default=True)
    created_at    = Column(DateTime, nullable=False, default=_now)
    updated_at    = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    department = relationship("AuditKpoDept", back_populates="items")


class AuditKpoPeriod(Base):
    """稽核期別（一個月）。同月可有多期（比照財#3 稽核檢查，期別不設限）。"""
    __tablename__ = "audit_kpo_periods"

    id         = Column(Integer,     primary_key=True, autoincrement=True)
    period     = Column(String(7),   nullable=False, index=True, comment="YYYY-MM")
    title      = Column(String(100), nullable=False, default="財#1稽核系統建構")
    note       = Column(Text,        nullable=True)
    dept_order = Column(Text,        nullable=True,
                        comment="本期部門顯示順序：部門 id 以逗號串接（2026-10-10，migration kpoaud2）；空＝依部門主檔順序")
    created_by = Column(String(36),  nullable=True)
    created_at = Column(DateTime,    nullable=False, default=_now)
    updated_at = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    lines = relationship(
        "AuditKpoPeriodItem", back_populates="period_ref",
        cascade="all, delete-orphan",
        order_by="AuditKpoPeriodItem.sort_order",
    )


class AuditKpoPeriodItem(Base):
    """某期某部門選定的一個稽核項目（內容為選定當下的快照，可在本期單獨編輯）。"""
    __tablename__ = "audit_kpo_period_items"
    __table_args__ = (
        UniqueConstraint("period_id", "source_item_id", name="uq_audit_kpo_pi_period_src"),
    )

    id             = Column(Integer, primary_key=True, autoincrement=True)
    period_id      = Column(Integer, ForeignKey("audit_kpo_periods.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    department_id  = Column(Integer, ForeignKey("audit_kpo_departments.id", ondelete="RESTRICT"),
                            nullable=False, index=True)
    source_item_id = Column(Integer, ForeignKey("audit_kpo_items.id", ondelete="SET NULL"),
                            nullable=True, comment="來源主檔項目；主檔刪除後為 NULL，快照仍保留")
    item_no        = Column(Integer, nullable=True)
    is_key         = Column(Boolean, nullable=False, default=False)
    name           = Column(Text,    nullable=False)
    score          = Column(Integer, nullable=False, default=5)
    method         = Column(Text,    nullable=True)
    result         = Column(String(10), nullable=True, comment="pass 符合／fail 不符合／NULL 尚未查核")
    remark         = Column(Text,    nullable=True, comment="本期查核備註")
    sort_order     = Column(Integer, nullable=False, default=0)
    created_at     = Column(DateTime, nullable=False, default=_now)
    updated_at     = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    period_ref = relationship("AuditKpoPeriod", back_populates="lines")
    department = relationship("AuditKpoDept")
