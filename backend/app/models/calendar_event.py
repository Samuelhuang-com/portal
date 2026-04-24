"""
行事曆自訂事件 SQLAlchemy ORM Model
資料表：calendar_custom_events

由使用者在 Portal 行事曆中手動建立的自訂事件，
不與任何 Ragic 模組關聯，Portal 獨立管理。
"""
import uuid
from datetime import datetime, timezone
from app.core.time import twnow
from sqlalchemy import Column, String, Text, DateTime, Boolean
from app.core.database import Base


def _now():
    return twnow()


def _new_uuid():
    return str(uuid.uuid4())


class CalendarCustomEvent(Base):
    """行事曆自訂事件主表"""
    __tablename__ = "calendar_custom_events"

    id            = Column(String(36),  primary_key=True, default=_new_uuid)
    title         = Column(String(255), nullable=False, default="")         # 事件標題
    description   = Column(Text,        nullable=False, default="")         # 事件說明
    start_date    = Column(String(20),  nullable=False, default="")         # YYYY-MM-DD
    end_date      = Column(String(20),  nullable=False, default="")         # YYYY-MM-DD（空=同 start_date）
    all_day       = Column(Boolean,     nullable=False, default=True)
    start_time    = Column(String(8),   nullable=False, default="")         # HH:MM
    end_time      = Column(String(8),   nullable=False, default="")         # HH:MM
    color         = Column(String(20),  nullable=False, default="#13c2c2")  # 事件顏色
    responsible   = Column(String(200), nullable=False, default="")         # 負責人
    created_by    = Column(String(100), nullable=False, default="")         # 建立者 full_name
    created_by_id = Column(String(36),  nullable=False, default="")         # 建立者 user.id
    created_at    = Column(DateTime,    nullable=False, default=_now)
    updated_at    = Column(DateTime,    nullable=False, default=_now, onupdate=_now)

    def __repr__(self):
        return f"<CalendarCustomEvent id={self.id} title={self.title[:20]}>"
