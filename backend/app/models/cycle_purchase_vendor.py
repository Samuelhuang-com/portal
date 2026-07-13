"""
週期採購 — 供應商主檔 SQLAlchemy ORM Model（獨立資料庫 cycle-purchase.db）

2026-07-10 決策：週期採購自建獨立供應商主檔，不與 Contract 模組既有的
Vendors 主檔關聯（各自維護，避免跨 SQLite 檔案關聯）。
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseVendor(CyclePurchaseBase):
    """週期採購供應商主檔"""
    __tablename__ = "cycle_purchase_vendors"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    vendor_code   = Column(String(30),  nullable=False, unique=True, comment="供應商代碼")
    vendor_name   = Column(String(200), nullable=False, comment="供應商名稱")
    tax_id        = Column(String(20),  nullable=True,  comment="統一編號")
    contact_name  = Column(String(50),  nullable=True,  comment="聯絡人")
    contact_phone = Column(String(50),  nullable=True,  comment="聯絡電話")
    payment_terms = Column(String(100), nullable=True,  comment="付款條件")
    notes         = Column(Text,        nullable=True,  comment="備註")
    is_active     = Column(Boolean,     nullable=False, default=True, comment="是否啟用")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CyclePurchaseVendor id={self.id} code={self.vendor_code} name={self.vendor_name}>"
