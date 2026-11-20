"""
需求管理（2026-11-20）：需求清單。與 dev_log_entries 為一對一（一個變更只對應一個需求）。
狀態：待評估／進行中／已完成／退回。Jira 匯入的需求以 jira_key 去重。
"""
from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from app.core.database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    title       = Column(String(300), nullable=False, default="")
    description = Column(Text, nullable=True)
    requester   = Column(String(120), nullable=True, comment="提出人")
    module      = Column(String(120), nullable=False, default="", comment="需求所屬模組（人工指定；空＝未分類）")
    status      = Column(String(20),  nullable=False, default="待評估", comment="待評估／進行中／已完成／退回")
    priority    = Column(String(10),  nullable=False, default="中", comment="高／中／低")
    jira_key    = Column(String(60),  nullable=True, unique=True, comment="Jira 匯入時的 Issue key，去重用")
    created_by  = Column(String(120), nullable=True)
    created_at  = Column(DateTime,    nullable=True)
    updated_by  = Column(String(120), nullable=True)
    updated_at  = Column(DateTime,    nullable=True)
    completed_at = Column(DateTime,   nullable=True)

    __table_args__ = (Index("ix_requirements_status", "status"),)
