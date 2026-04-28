"""
選單設定 Models
- MenuConfig        : 每個 menu key 的自訂 label 與排序
- MenuConfigHistory : 每次 Save 的快照，最多保留 5 筆
"""
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from app.core.database import Base
from app.core.time import twnow


def _now():
    return twnow()


class MenuConfig(Base):
    __tablename__ = "menu_configs"

    # menu key：一級群組用群組 key（如 'hotel'），二級頁面用路由（如 '/hotel/periodic-maintenance'）
    menu_key: Mapped[str] = mapped_column(String(120), primary_key=True)
    # 父層 key；一級群組為 None
    parent_key: Mapped[str | None] = mapped_column(String(120), nullable=True, default=None)
    # 自訂顯示名稱；None 表示使用 navLabels 預設值
    custom_label: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    # 排序順序（同層內由小到大）
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # 保留欄位：未來可做隱藏功能
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)


class MenuConfigHistory(Base):
    __tablename__ = "menu_config_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    # 本次變更摘要（JSON 字串）：記錄哪些 key 的 label / order 發生了變化
    diff_json: Mapped[str] = mapped_column(Text, nullable=False)
    # 儲存當下全量快照（JSON 字串），可供還原參考
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
