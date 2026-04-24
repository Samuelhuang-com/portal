"""
客房保養 SQLAlchemy ORM Model
對應資料庫表：room_maintenance_records
"""
import json
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, func
from app.core.database import Base


class RoomMaintenanceRecord(Base):
    __tablename__ = "room_maintenance_records"

    # ── 主鍵：使用 Ragic record ID（字串）作為自然主鍵 ─────────────────────
    ragic_id = Column(String(50), primary_key=True, comment="Ragic 記錄 ID")

    # ── 業務欄位 ──────────────────────────────────────────────────────────────
    room_no          = Column(String(20),  nullable=False, default="", comment="房號")
    inspect_items    = Column(Text,        nullable=False, default="[]", comment="檢查項目 JSON array")
    dept             = Column(String(100), nullable=False, default="", comment="報修部門/負責人")
    work_item        = Column(String(100), nullable=False, default="", comment="工作項目選擇")
    inspect_datetime = Column(String(30),  nullable=False, default="", comment="檢查日期時間")
    close_date       = Column(String(20),  nullable=False, default="", comment="結案日期")
    subtotal         = Column(Integer,     nullable=False, default=0,  comment="小計")
    incomplete       = Column(Integer,     nullable=False, default=0,  comment="未完成小計")

    # ── 來自 Ragic 的時間戳 ────────────────────────────────────────────────────
    ragic_created_at = Column(String(30), nullable=False, default="", comment="Ragic 建立時間")
    ragic_updated_at = Column(String(30), nullable=False, default="", comment="Ragic 更新時間")

    # ── Portal 同步時間 ────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    # ── Helper：inspect_items ↔ JSON ──────────────────────────────────────────
    def get_inspect_items(self) -> list[str]:
        try:
            return json.loads(self.inspect_items or "[]")
        except Exception:
            return []

    def set_inspect_items(self, items: list[str]) -> None:
        self.inspect_items = json.dumps(items, ensure_ascii=False)

    def __repr__(self) -> str:
        return f"<RoomMaintenanceRecord ragic_id={self.ragic_id} room_no={self.room_no}>"
