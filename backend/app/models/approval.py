"""
簽核系統 SQLAlchemy ORM Models
4 張資料表：
  - approvals          主單
  - approval_steps     關卡（串簽順序）
  - approval_actions   歷程紀錄
  - approval_files     附件
"""
import uuid
from datetime import datetime, timezone
from app.core.time import twnow
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func
from app.core.database import Base


def _now():
    return twnow()


def _new_uuid():
    return str(uuid.uuid4())


class Approval(Base):
    __tablename__ = "approvals"

    id            = Column(String(36), primary_key=True, default=_new_uuid)
    subject       = Column(String(255), nullable=False, default="")
    description   = Column(Text,        nullable=False, default="")
    confidential  = Column(Text,        nullable=False, default="")   # 機敏欄位（僅 admin/相關人）
    requester     = Column(String(100), nullable=False, default="")   # 申請人 full_name
    requester_id  = Column(String(36),  nullable=False, default="")   # 申請人 user.id
    requester_dept= Column(String(100), nullable=False, default="")
    status        = Column(String(20),  nullable=False, default="pending")  # pending|approved|rejected
    current_step  = Column(Integer,     nullable=False, default=0)          # 目前關卡 index（-1=結案）
    view_scope    = Column(String(20),  nullable=False, default="restricted") # org|restricted|top_secret
    publish_memo  = Column(Integer,     nullable=False, default=0)          # 1=完成後建 memo
    submitted_at  = Column(DateTime,    nullable=False, default=_now)
    updated_at    = Column(DateTime,    nullable=False, default=_now, onupdate=_now)


class ApprovalStep(Base):
    __tablename__ = "approval_steps"

    id             = Column(String(36), primary_key=True, default=_new_uuid)
    approval_id    = Column(String(36), ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False)
    step_order     = Column(Integer,    nullable=False, default=0)
    approver_id    = Column(String(36), nullable=False, default="")   # user.id（可為空字串）
    approver_name  = Column(String(100), nullable=False, default="")  # full_name
    approver_email = Column(String(255), nullable=False, default="")
    status         = Column(String(20),  nullable=False, default="pending")  # pending|approved|rejected
    decided_at     = Column(DateTime,    nullable=True)
    comment        = Column(Text,        nullable=False, default="")


class ApprovalAction(Base):
    __tablename__ = "approval_actions"

    id          = Column(String(36), primary_key=True, default=_new_uuid)
    approval_id = Column(String(36), ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False)
    step_id     = Column(String(36), nullable=True)                    # 對應 ApprovalStep.id
    actor       = Column(String(100), nullable=False, default="")      # full_name
    actor_id    = Column(String(36),  nullable=False, default="")      # user.id
    action      = Column(String(50),  nullable=False, default="")      # submit|approve|reject|reorder|add_step|remove_step|upload
    note        = Column(Text,        nullable=False, default="")
    created_at  = Column(DateTime,    nullable=False, default=_now)


class ApprovalFile(Base):
    __tablename__ = "approval_files"

    id          = Column(String(36), primary_key=True, default=_new_uuid)
    approval_id = Column(String(36), ForeignKey("approvals.id", ondelete="CASCADE"), nullable=False)
    orig_name   = Column(String(255), nullable=False, default="")
    stored_name = Column(String(255), nullable=False, default="")      # UUID 命名防衝突
    content_type= Column(String(100), nullable=False, default="")
    size_bytes  = Column(Integer,     nullable=False, default=0)
    uploaded_by = Column(String(100), nullable=False, default="")      # full_name
    uploaded_at = Column(DateTime,    nullable=False, default=_now)
