"""
AI 查詢快取 ORM Model

快取策略：
  - key = SHA256(問題文字 + "\x00" + 地點清單)
  - TTL = 1 小時（expires_at）
  - 命中時直接回傳，不呼叫 Anthropic API
  - 過期條目由 router 在每次請求時以 10% 機率清除（lazy cleanup）
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


class AIQueryCache(Base):
    __tablename__ = "ai_query_cache"

    id:               Mapped[str]       = mapped_column(String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    question_hash:    Mapped[str]       = mapped_column(String(64),  index=True)        # SHA256 hex
    question_text:    Mapped[str]       = mapped_column(String(500), default="")        # 原始問題（供人工審查）
    locations_key:    Mapped[str]       = mapped_column(String(50),  default="")        # 地點排序字串 e.g. "商場|飯店"
    answer:           Mapped[str]       = mapped_column(Text,        default="")        # Claude 自然語言回答
    has_table:        Mapped[bool]      = mapped_column(Boolean,     default=False)
    table_data_json:  Mapped[str]       = mapped_column(Text,        default="[]")      # JSON array
    total_count:      Mapped[int | None] = mapped_column(Integer,    nullable=True)
    hit_count:        Mapped[int]       = mapped_column(Integer,     default=0)         # 命中次數
    created_at:       Mapped[datetime]  = mapped_column(DateTime,    default=twnow)
    expires_at:       Mapped[datetime]  = mapped_column(DateTime,    index=True)        # 到期時間
