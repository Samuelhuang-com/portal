"""
公告系統 SQLAlchemy ORM Model
資料表：memos

欄位說明：
  title       公告主旨
  body        內文（HTML/純文字）
  visibility  org=全公司 | restricted=僅相關人員
  author      發文者（full_name）
  author_id   發文者 user.id
  doc_no      文號（選填，供正式公文使用）
  recipient   收文者（選填，供正式公文使用）
  source      來源模組（如 'approval'）
  source_id   來源記錄 ID（如 approval.id）
"""
import uuid
from datetime import datetime, timezone
from app.core.time import twnow
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base


def _now():
    return twnow()


def _new_uuid():
    return str(uuid.uuid4())


class Memo(Base):
    __tablename__ = "memos"

    id          = Column(String(36),  primary_key=True, default=_new_uuid)
    title       = Column(String(255), nullable=False, default="")
    body        = Column(Text,        nullable=False, default="")
    visibility  = Column(String(20),  nullable=False, default="org")   # org | restricted
    author      = Column(String(100), nullable=False, default="")      # full_name
    author_id   = Column(String(36),  nullable=False, default="")      # user.id
    doc_no      = Column(String(100), nullable=False, default="")      # 文號（選填）
    recipient   = Column(String(255), nullable=False, default="")      # 收文者（選填）
    source      = Column(String(50),  nullable=False, default="")      # 'approval' | 'manual'
    source_id   = Column(String(36),  nullable=False, default="")      # 來源記錄 id
    created_at  = Column(DateTime,    nullable=False, default=_now)
    updated_at  = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    attachments = relationship(
        "MemoFile",
        back_populates="memo",
        cascade="all, delete-orphan",
        order_by="MemoFile.uploaded_at",
    )
