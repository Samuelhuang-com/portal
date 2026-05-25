"""
PPT 匯出設定 — 資料表模型
每位使用者各有一份設定（user_id 區分）；以 module_key 區分不同 Dashboard。
config_json 儲存使用者偏好：enabled / include_detail / sort_order / second_title_override
Section metadata 由 ppt_section_registry 維護。
"""
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class PptExportConfig(Base):
    __tablename__ = "ppt_export_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 哪個 Dashboard 的設定（預留多模組共用）
    module_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # 使用者 ID（C-1：多人隔離）nullable=True 向後相容舊全局設定
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # JSON Array，每個 item：
    # {
    #   "export_key": str,
    #   "enabled": bool,
    #   "include_detail": bool,
    #   "sort_order": int,
    #   "second_title_override": str | null   (B-1)
    # }
    config_json: Mapped[str] = mapped_column(Text, nullable=False)

    # 模板 ID（C-2：多模板支援）
    template_id: Mapped[str] = mapped_column(String(64), nullable=True, default="default")

    # 追蹤：最後儲存者與時間
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        # 同一 user + module 只有一份設定
        Index("ix_ppt_config_user_module", "user_id", "module_key"),
    )
