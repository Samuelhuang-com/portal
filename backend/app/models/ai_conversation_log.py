"""
AI 工單查詢對話記錄 ORM Model

功能：
  - 永久保存每次 AI 工單查詢的問題與回答（含快取命中）
  - 提供「歷史問答」功能，讓使用者查看過去的查詢記錄
  - 與 AIQueryCache 不同：本表永久保留，不設 TTL；快取表僅用於節省 API 額度

資料量估計：每位使用者每日 10 次查詢 → 年約 3600 筆，SQLite 負擔輕微
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


class AIConversationLog(Base):
    __tablename__ = "ai_conversation_log"

    id:              Mapped[str]        = mapped_column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id:         Mapped[str]        = mapped_column(String(36),  index=True)          # 查詢者 user.id
    user_email:      Mapped[str]        = mapped_column(String(200), default="")          # 供人工審查
    question:        Mapped[str]        = mapped_column(String(500), default="")          # 原始問題
    answer:          Mapped[str]        = mapped_column(Text,        default="")          # AI 回答
    has_table:       Mapped[bool]       = mapped_column(Boolean,     default=False)
    table_data_json: Mapped[str]        = mapped_column(Text,        default="[]")        # JSON 序列化工單列表
    total_count:     Mapped[int | None] = mapped_column(Integer,     nullable=True)
    locations_key:   Mapped[str]        = mapped_column(String(50),  default="")          # e.g. "商場|飯店"
    from_cache:      Mapped[bool]       = mapped_column(Boolean,     default=False)       # 是否命中快取
    created_at:      Mapped[datetime]   = mapped_column(DateTime,    index=True, default=twnow)
