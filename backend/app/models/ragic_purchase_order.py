"""
Ragic 採購單 ORM Model（庫存管理 Phase 1，2026-11-17，docs/SPEC_stock_management.md §4、§11）

資料表：ragic_purchase_orders（主單）／ragic_purchase_order_items（品項）
來源：ragic_sheet_config 的 module = purchase_po（樂群）／nichiyo_po（日曜）／taichung_po（台中）

【Phase 0 實測（SPEC §4.4）】
  - 採購單**沒有簽核欄位**（請購核准後才產生），因此不存 status，只標 Ragic 是否已刪除。
  - 台中採購單有「來源請購單號」（＝請購單「編號」），樂群／日曜沒有（存 NULL）。
  - 管理部等表單沒有「申請日期」，改用「到貨日期」。
  - 子表列的 `_ragicId` 是穩定的列鍵，品項以 (order_id, ragic_row_id) 唯一；
    之後進貨匯入（stock_import_lines）以此作為唯一鍵，避免同一列重複入庫。
"""
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime, Index, Integer, Numeric, String, Text,
    UniqueConstraint, func,
)

from app.core.database import Base


class RagicPurchaseOrder(Base):
    """Ragic 採購單主單（每張採購單一列）"""
    __tablename__ = "ragic_purchase_orders"

    id                 = Column(Integer, primary_key=True, autoincrement=True)

    # ── 公司／部門 ────────────────────────────────────────────────────────────
    company            = Column(String(20),  nullable=False, default="", comment="公司別（樂群／日曜／台中）")
    sheet_module       = Column(String(50),  nullable=False, default="", comment="ragic_sheet_config.module")
    department_display = Column(String(50),  nullable=False, default="", comment="部門（依表單歸屬，取 ragic_sheet_config.display_name）")
    department_raw     = Column(String(50),  nullable=True,  comment="Ragic「請購部門」原始值")

    # ── Ragic 來源 ───────────────────────────────────────────────────────────
    ragic_sheet_path   = Column(String(100), nullable=False, default="", comment="來源 Sheet 路徑")
    ragic_record_id    = Column(String(30),  nullable=False, default="", comment="Ragic 記錄 ID")

    # ── 主單欄位 ─────────────────────────────────────────────────────────────
    po_no              = Column(String(50),  nullable=False, default="", comment="採購編號（如 樂營採00014）")
    source_pr_no       = Column(String(50),  nullable=True,  comment="來源請購單號（台中才有）")
    requester          = Column(String(50),  nullable=True,  comment="申請人")
    apply_date         = Column(Date,        nullable=True,  comment="申請日期")
    arrival_date       = Column(Date,        nullable=True,  comment="到貨日期")
    purpose            = Column(Text,        nullable=True,  comment="用途說明")
    vendor_name        = Column(String(200), nullable=True,  comment="擬定廠商")
    vendor_code        = Column(String(50),  nullable=True,  comment="最終擬定廠商編號（台中才有）")
    subtotal           = Column(Numeric(14, 2), nullable=True, comment="小計（未稅）")
    tax                = Column(Numeric(14, 2), nullable=True, comment="營業稅")
    total              = Column(Numeric(14, 2), nullable=True, comment="總計（含稅）")
    payment_terms      = Column(String(200), nullable=True,  comment="付款條件")
    receiver           = Column(String(100), nullable=True,  comment="收貨人")

    # ── 同步狀態 ─────────────────────────────────────────────────────────────
    is_ragic_deleted   = Column(Boolean,     nullable=False, default=False, server_default="false",
                                comment="最近一次同步時 Ragic 已無此筆")
    source_hash        = Column(String(64),  nullable=False, default="", comment="來源資料雜湊（偵測匯入後被修改）")
    ragic_data_ts      = Column(BigInteger,  nullable=True,  comment="Ragic _dataTimestamp（毫秒）")
    raw_data_json      = Column(Text,        nullable=False, default="{}", comment="清單 API 原始 JSON")

    sync_at            = Column(DateTime,    nullable=False, server_default=func.now(), comment="本次同步時間")
    created_at         = Column(DateTime,    nullable=False, server_default=func.now())
    updated_at         = Column(DateTime,    nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("ragic_sheet_path", "ragic_record_id", name="uq_rpo_sheet_record"),
        Index("ix_rpo_company_dept", "company", "department_display"),
        Index("ix_rpo_po_no", "po_no"),
    )

    def __repr__(self) -> str:
        return f"<RagicPurchaseOrder id={self.id} no={self.po_no} {self.company}/{self.department_display}>"


class RagicPurchaseOrderItem(Base):
    """Ragic 採購單品項（子表格每列一筆）"""
    __tablename__ = "ragic_purchase_order_items"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(Integer, nullable=False, comment="ragic_purchase_orders.id")
    ragic_row_id  = Column(String(30),  nullable=False, default="", comment="子表列 _ragicId（穩定列鍵）")
    seq           = Column(Integer,     nullable=True,  comment="項次")
    item_code     = Column(String(50),  nullable=True,  comment="料號（週採採購單才有）")
    product_name  = Column(Text,        nullable=True,  comment="產品名稱")
    qty           = Column(Numeric(14, 4), nullable=True, comment="數量（解析後）")
    qty_raw       = Column(String(50),  nullable=True,  comment="數量原始字串")
    unit          = Column(String(50),  nullable=True,  comment="單位")
    remark        = Column(Text,        nullable=True,  comment="品項備註")
    unit_price    = Column(Numeric(14, 4), nullable=True, comment="擬定廠商單價（未稅）")
    amount        = Column(Numeric(14, 2), nullable=True, comment="擬定廠商金額（未稅）")
    item_dept     = Column(String(50),  nullable=True,  comment="品項部門（週採採購單才有）")
    sync_at       = Column(DateTime,    nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("order_id", "ragic_row_id", name="uq_rpoi_order_row"),
        Index("ix_rpoi_order_id", "order_id"),
    )
