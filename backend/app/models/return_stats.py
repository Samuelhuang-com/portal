"""
退件統計 ORM Models（規格：docs/SPEC_return_reject_stats.md）

資料表：
  return_stats_source  — 來源登錄（每張 Ragic 清單一列，source_key 唯一）
  return_stats_record  — 每張 Ragic 單一列（以 source_key + ragic_record_id 唯一）
  return_stats_step    — 每張單的每一個簽核格一列
"""
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    ForeignKey, Index, UniqueConstraint,
)

from app.core.database import Base


class ReturnStatsSource(Base):
    __tablename__ = "return_stats_source"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    source_key     = Column(String(120), nullable=False, unique=True,
                            comment="穩定識別碼，建立後不可改")
    company        = Column(String(20),  nullable=False, comment="樂群／日曜／台中")
    form_type      = Column(String(10),  nullable=False, comment="purchase／claim／seal")
    dept_display   = Column(String(50),  nullable=False, default="")
    form_name      = Column(String(100), nullable=False, default="")
    ragic_path     = Column(String(200), nullable=False, comment="Ragic 清單路徑")
    origin         = Column(String(20),  nullable=False, default="module_table",
                            comment="module_table=讀既有同步表 raw_data_json；ragic_api=直接呼叫 Ragic API")
    origin_table   = Column(String(60),  nullable=True, comment="origin=module_table 時的既有同步表名")
    parser_profile = Column(String(40),  nullable=False, default="standard_v1")
    is_active      = Column(Boolean,     nullable=False, default=True)
    sort_order     = Column(Integer,     nullable=False, default=0)


class ReturnStatsRecord(Base):
    __tablename__ = "return_stats_record"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    source_key      = Column(String(120), nullable=False, index=True)
    ragic_record_id = Column(String(30),  nullable=False)
    company         = Column(String(20),  nullable=False, default="")
    form_type       = Column(String(10),  nullable=False, default="")
    dept_display    = Column(String(50),  nullable=False, default="")
    form_name       = Column(String(100), nullable=False, default="")
    applicant       = Column(String(100), nullable=True)
    apply_date      = Column(Date,        nullable=True)
    amount          = Column(Integer,     nullable=True)
    purpose         = Column(Text,        nullable=True)
    ragic_status    = Column(String(20),  nullable=True, comment="原始簽核狀態")
    submitter       = Column(String(100), nullable=True)
    next_approver   = Column(String(200), nullable=True)
    outcome         = Column(String(20),  nullable=False, default="unknown")
    outcome_reason  = Column(String(200), nullable=False, default="")
    inferred_last_step = Column(Integer,  nullable=True, comment="推斷最後簽核的步驟號（僅 F）")
    last_sign_date  = Column(Date,        nullable=True)
    is_deleted      = Column(Boolean,     nullable=False, default=False)
    synced_at       = Column(DateTime,    nullable=True)
    raw_json        = Column(Text,        nullable=False, default="{}")

    __table_args__ = (
        UniqueConstraint("source_key", "ragic_record_id", name="uq_rs_record_source_rid"),
        Index("ix_rs_record_company_dept", "company", "dept_display"),
        Index("ix_rs_record_apply_date",   "apply_date"),
        Index("ix_rs_record_outcome",      "outcome"),
    )


class ReturnStatsStep(Base):
    __tablename__ = "return_stats_step"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    record_id       = Column(Integer, ForeignKey("return_stats_record.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    step_no         = Column(Integer,     nullable=False, default=0)
    role_field      = Column(String(40),  nullable=False, default="")
    approver_text   = Column(String(200), nullable=False, default="")
    sign_date       = Column(Date,        nullable=True)
    remark          = Column(Text,        nullable=True, comment="回應／備註（完整文字）")
    is_inferred_last = Column(Boolean,    nullable=False, default=False)
    response_code   = Column(String(10),  nullable=True, comment="Ragic _step_response：A=同意、REJ=拒絕簽核、N=尚未處理")
