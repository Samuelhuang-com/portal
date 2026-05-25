"""
PPT 匯出歷史紀錄 — 資料表模型
每次 POST /export 成功後寫入一筆，供設定頁「最近匯出紀錄」面板顯示。
"""
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PptExportHistory(Base):
    __tablename__ = "ppt_export_history"

    id:           Mapped[int]      = mapped_column(Integer,     primary_key=True, autoincrement=True)
    module_key:   Mapped[str]      = mapped_column(String(64),  nullable=False, index=True)
    year:         Mapped[int]      = mapped_column(Integer,     nullable=False)
    month:        Mapped[int]      = mapped_column(Integer,     nullable=False)
    exported_by:  Mapped[str]      = mapped_column(String(128), nullable=False)
    exported_at:  Mapped[datetime] = mapped_column(DateTime,    nullable=False)
    # JSON list of enabled export_keys（供顯示「哪些區塊被匯出」）
    sections_json: Mapped[str]     = mapped_column(Text,        nullable=False, default="[]")
    # 此次使用的模板
    template_id:  Mapped[str | None] = mapped_column(String(64), nullable=True)
