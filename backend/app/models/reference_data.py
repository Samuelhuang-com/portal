"""
F1 — 基礎參考資料模型
  - Company        公司別
  - RefDepartment  部門別（每家公司獨立清單）
                   ※ 命名為 RefDepartment 以避免與 schedule.Department 衝突
  - PricingSpec    計價規格
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now()


class Company(Base):
    """公司別"""
    __tablename__ = "companies"

    id         = Column(Integer,     primary_key=True, autoincrement=True)
    name       = Column(String(100), nullable=False, unique=True, comment="公司名稱")
    is_active  = Column(Boolean,     nullable=False, default=True, comment="是否啟用")
    created_at = Column(DateTime,    nullable=False, default=_now)

    departments = relationship(
        "RefDepartment",
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="RefDepartment.name",
    )


class RefDepartment(Base):
    """部門別（依公司別分組）— class 名稱 RefDepartment，DB table 仍為 departments"""
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("name", "company_id", name="uq_dept_name_company"),
    )

    id         = Column(Integer,     primary_key=True, autoincrement=True)
    name       = Column(String(100), nullable=False, comment="部門名稱")
    company_id = Column(Integer,     ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    is_active  = Column(Boolean,     nullable=False, default=True, comment="是否啟用")
    created_at = Column(DateTime,    nullable=False, default=_now)

    company = relationship("Company", back_populates="departments")


class PricingSpec(Base):
    """計價規格"""
    __tablename__ = "pricing_specs"

    id         = Column(Integer,     primary_key=True, autoincrement=True)
    name       = Column(String(200), nullable=False, unique=True, comment="計價規格名稱")
    is_active  = Column(Boolean,     nullable=False, default=True, comment="是否啟用")
    created_at = Column(DateTime,    nullable=False, default=_now)


class SlaMetricType(Base):
    """SLA 指標類型（K2）— 可在合約設定頁維護"""
    __tablename__ = "sla_metric_types"

    id          = Column(Integer,     primary_key=True, autoincrement=True)
    name        = Column(String(100), nullable=False, unique=True, comment="指標類型名稱")
    description = Column(String(200), nullable=True,  comment="說明（如：以百分比衡量服務可用程度）")
    is_active   = Column(Boolean,     nullable=False, default=True, comment="是否啟用")
    created_at  = Column(DateTime,    nullable=False, default=_now)
