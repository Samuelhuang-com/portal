"""
知識庫（LLM Wiki）SQLAlchemy ORM Model
資料表：wiki_articles

欄位說明：
  title       文章標題
  slug        URL slug（自動從標題產生，可覆寫）
  body        Markdown 內文
  category    sop = 員工 SOP 知識庫 | dev = 開發者技術 Wiki
  tags        JSON array 字串（["tag1","tag2"]）
  summary     AI 自動摘要（最多 200 字）
  author      作者全名
  author_id   作者 user.id
  is_published  True = 已發佈，False = 草稿
  created_at  建立時間
  updated_at  最後更新時間
"""
import uuid
import re
from datetime import datetime
from app.core.time import twnow
from sqlalchemy import Column, String, Text, Boolean, DateTime
from app.core.database import Base


def _now():
    return twnow()


def _new_uuid():
    return str(uuid.uuid4())


def _slugify(text: str) -> str:
    """將標題轉為 URL-safe slug（支援中文→拼音省略，直接保留中文）"""
    text = text.lower().strip()
    text = re.sub(r"[\s\-–—/\\]+", "-", text)
    text = re.sub(r"[^\w\-一-鿿]", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:80] if text else _new_uuid()[:8]


class WikiArticle(Base):
    __tablename__ = "wiki_articles"

    id          = Column(String(36),  primary_key=True, default=_new_uuid)
    title       = Column(String(255), nullable=False, default="")
    slug        = Column(String(100), nullable=False, default="", index=True)
    body        = Column(Text,        nullable=False, default="")
    summary     = Column(String(400), nullable=False, default="")
    category    = Column(String(20),  nullable=False, default="sop")    # sop | dev
    tags        = Column(Text,        nullable=False, default="[]")     # JSON string
    author      = Column(String(100), nullable=False, default="")
    author_id   = Column(String(36),  nullable=False, default="")
    is_published = Column(Boolean,    nullable=False, default=True)
    created_at  = Column(DateTime,    nullable=False, default=_now)
    updated_at  = Column(DateTime,    nullable=False, default=_now, onupdate=_now)
