"""
MemoFile ORM model — 公告附件
"""
import uuid
from datetime import datetime
from app.core.time import twnow

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class MemoFile(Base):
    __tablename__ = "memo_file"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    memo_id      = Column(String, ForeignKey("memos.id", ondelete="CASCADE"), nullable=False)
    orig_name    = Column(String, nullable=False, default="")
    stored_name  = Column(String, nullable=False, default="")
    content_type = Column(String, nullable=False, default="application/octet-stream")
    size_bytes   = Column(Integer, nullable=False, default=0)
    uploaded_by  = Column(String, nullable=False, default="")
    uploaded_at  = Column(DateTime, nullable=False, default=twnow)

    memo = relationship("Memo", back_populates="attachments")
