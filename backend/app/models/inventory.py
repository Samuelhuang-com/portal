"""
倉庫庫存 SQLAlchemy ORM Model
對應資料庫表：inventory_records
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, func
from app.core.database import Base


class InventoryRecord(Base):
    __tablename__ = "inventory_records"

    # ── 主鍵：使用 Ragic record ID（字串）作為自然主鍵 ─────────────────────
    ragic_id = Column(String(50), primary_key=True, comment="Ragic 記錄 ID")

    # ── 業務欄位 ──────────────────────────────────────────────────────────────
    inventory_no   = Column(String(50),  nullable=False, default="", comment="庫存編號")
    warehouse_code = Column(String(50),  nullable=False, default="", comment="倉庫代碼")
    warehouse_name = Column(String(100), nullable=False, default="", comment="倉庫名稱")
    product_no     = Column(String(50),  nullable=False, default="", comment="商品編號")
    product_name   = Column(String(200), nullable=False, default="", comment="商品名稱")
    quantity       = Column(Integer,     nullable=False, default=0,  comment="數量")
    category       = Column(String(100), nullable=False, default="", comment="種類")
    spec           = Column(String(200), nullable=False, default="", comment="規格")

    # ── 來自 Ragic 的時間戳 ────────────────────────────────────────────────────
    ragic_created_at = Column(String(30), nullable=False, default="", comment="Ragic 建立時間")
    ragic_updated_at = Column(String(30), nullable=False, default="", comment="Ragic 更新時間")

    # ── Portal 同步時間 ────────────────────────────────────────────────────────
    synced_at = Column(DateTime, nullable=False, server_default=func.now(),
                       onupdate=func.now(), comment="最後同步時間")

    def __repr__(self) -> str:
        return (
            f"<InventoryRecord ragic_id={self.ragic_id} "
            f"inventory_no={self.inventory_no} qty={self.quantity}>"
        )
