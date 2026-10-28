"""
週期採購 — 供應商主檔 SQLAlchemy ORM Model（獨立資料庫 cycle-purchase.db）

2026-07-10 決策：週期採購自建獨立供應商主檔，不與 Contract 模組既有的
Vendors 主檔關聯（各自維護，避免跨 SQLite 檔案關聯）。

2026-08-10 修訂（Samuel 確認）：改為「單向鏡像同步」——合約模組 vendors
（portal.db，其上游是 Ragic 廠商資料表 Sheet 15）是廠商資料的唯一真實來源，
本表退化成該來源在 cycle-purchase.db 的鏡像副本。

  Ragic Sheet 15 ──vendor_sync.py──▶ portal.db vendors
                   ──cycle_purchase_vendor_sync.py──▶ cycle_purchase_vendors

刻意「不」改成直接跨檔案關聯 portal.db 的原因：
  - 跨 SQLite 檔案不能建 FK，也不做 ATTACH DATABASE（見 cycle_purchase_database.py）。
  - 本表的 Integer `id` 已被 cycle_purchase_pos.vendor_id（RESTRICT）、
    cycle_purchase_summaries.vendor_id、cycle_purchase_item_mappings.vendor_id
    三處外鍵綁住。換成合約端的 VND-NNNN 字串鍵要改三張表的既有資料，風險過高。
  因此保留 id 與所有 FK 不動，只加 source_vendor_id 當跨庫對照鍵。

欄位權責（sync 只覆蓋前者，後者永遠不碰）：
  同步覆蓋：vendor_name / tax_id / contact_name / contact_phone
  週採自維護：payment_terms / notes / is_active
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

    # ── 合約模組鏡像同步（2026-08-10）────────────────────────────────────────
    # 應用層軟關聯：只存 portal.db vendors.vendor_id 的值（VND-NNNN），
    # 不建跨檔案 FK。NULL = 本地自建（同步比對不到，不會被覆蓋也不會被刪）。
    source_vendor_id = Column(
        String(50), nullable=True, unique=True, index=True,
        comment="來源廠商編號（portal.db vendors.vendor_id，VND-NNNN；NULL 表示本地自建）"
    )
    synced_at = Column(DateTime, nullable=True, comment="最後一次自合約模組同步的時間")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def is_synced(self) -> bool:
        """True = 鏡像自合約模組（受控欄位唯讀）；False = 本地自建"""
        return bool(self.source_vendor_id)

    def __repr__(self):
        return f"<CyclePurchaseVendor id={self.id} code={self.vendor_code} name={self.vendor_name}>"
