"""
模組頁籤自訂名稱（2026-11-10 新增）

Samuel 裁示：飯店每日巡檢的頁籤名稱要能在 Portal 頁面上直接修改（新增權限 key、需明確指派），
改過的名稱套用到整個頁面（頁籤、Dashboard 卡片、月曆格、每日巡檢表 Drawer、場次明細）。
資料表設計成可給其他模組共用：(module, tab_key) 為主鍵；custom_label 為 NULL＝使用程式預設名稱。
每台 Server 各自一份（同 menu_configs）。
"""
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.time import twnow


class ModuleTabLabel(Base):
    __tablename__ = "module_tab_labels"

    module:       Mapped[str] = mapped_column(String(50), primary_key=True)    # 例：hotel_daily_inspection
    tab_key:      Mapped[str] = mapped_column(String(50), primary_key=True)    # 例：rf、5f-10f
    custom_label: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    updated_at:   Mapped[datetime] = mapped_column(DateTime, default=twnow, onupdate=twnow)
    updated_by:   Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
