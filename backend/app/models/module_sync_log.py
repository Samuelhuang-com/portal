"""
模組自動同步日誌 ORM Model

記錄 _auto_sync() 每次執行時各模組的同步結果，供前端「同步紀錄」頁面查詢。
"""
from datetime import datetime
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base


class ModuleSyncLog(Base):
    __tablename__ = "module_sync_log"

    id:           Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_name:  Mapped[str]            = mapped_column(String(50),  nullable=False)
    started_at:   Mapped[datetime]       = mapped_column(DateTime,    nullable=False)
    finished_at:  Mapped[datetime | None] = mapped_column(DateTime,   nullable=True)
    duration_sec: Mapped[float | None]   = mapped_column(Float,       nullable=True)
    status:       Mapped[str]            = mapped_column(String(20),  default="running")  # success|error|partial
    fetched:      Mapped[int]            = mapped_column(Integer,     default=0)
    upserted:     Mapped[int]            = mapped_column(Integer,     default=0)
    errors_count: Mapped[int]            = mapped_column(Integer,     default=0)
    error_msg:    Mapped[str | None]     = mapped_column(Text,        nullable=True)
    triggered_by: Mapped[str]            = mapped_column(String(20),  default="scheduler")  # scheduler|manual
