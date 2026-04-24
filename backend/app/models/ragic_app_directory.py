"""
Ragic 應用程式對應表 — Portal 標註
存放每筆 Ragic 應用程式對應的 Portal 頁面名稱與超連結。
靜態資料（序號/模組/應用程式名/URL/類型/備註）存在前端，
此 model 只持久化可編輯的兩個 portal 欄位。
"""

from datetime import datetime
from app.core.time import twnow
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import mapped_column, Mapped
from app.core.database import Base


class RagicAppPortalAnnotation(Base):
    __tablename__ = "ragic_app_portal_annotations"

    # 以 Ragic 應用程式序號（1~219）為主鍵
    item_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    portal_name: Mapped[str] = mapped_column(String(200), default="")
    portal_url: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=twnow, onupdate=twnow
    )
