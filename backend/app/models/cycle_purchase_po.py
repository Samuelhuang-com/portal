"""
週期採購 — 採購單（獨立資料庫 cycle-purchase.db）

2026-07-11（第三期規劃，與 Samuel 確認）：
一張採購單＝一個公司＋一個供應商（同一週期＋期別內，同公司同供應商的所有
彙整列合成一張採購單）。由「轉採購單」動作從 cycle_purchase_summary 狀態
為 draft、且調整量 > 0 的列產生；產生後對應彙整列的 status 改為
converted、po_id 回填（調整量＝0 的列也一併鎖定為 converted，代表「本期
決定不訂這個料號」，但不會出現在採購明細裡）。

狀態機（第三期僅實作 draft <-> issued <-> cancelled；partial_received／
received 是第四期「驗收單」串接時新增，見下方更新說明）：
  draft -> issued（已發出，通知供應商）
  draft / issued -> cancelled（取消，例如供應商無法供貨）

2026-07-11（第四期驗收單串接，與 Samuel 確認）：
  issued 狀態的採購單開始可以建立驗收單（一張可以分好幾次，對應分批到貨）。
  每次驗收單送出後，系統依「這張採購單底下每個採購明細行的累計已驗收數量」
  自動重算這張採購單的狀態：
    issued -> partial_received（尚有明細行累計已驗收數量 > 0 但還沒全部到齊）
    issued / partial_received -> received（所有明細行累計已驗收數量都 >= 訂購數量）
  這個狀態改變是系統自動算出來的，不能用 PUT /pos/{id}/status 手動指定
  partial_received／received（那個 endpoint 只保留給人工動作 issued／cancelled）。
  received 狀態的採購單不能再建立新的驗收單（沒有東西可以再驗收）；
  cancelled／draft 狀態的採購單也不能建立驗收單（沒有正式生效的訂單）。
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, DateTime, Date,
    ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchasePO(CyclePurchaseBase):
    """週期採購採購單（單一公司＋單一供應商在單一週期＋期別下的一張單）"""
    __tablename__ = "cycle_purchase_pos"
    __table_args__ = (
        UniqueConstraint("cycle_id", "period_label", "company", "vendor_id",
                          name="uq_cp_po_cycle_period_company_vendor"),
    )

    id            = Column(Integer, primary_key=True, autoincrement=True)
    po_no         = Column(String(30), nullable=False, unique=True,
                            comment="採購單號（系統產生，如 PO-202607-0001）")
    cycle_id      = Column(
        Integer, ForeignKey("cycle_purchase_cycles.id", ondelete="RESTRICT"), nullable=False
    )
    period_label  = Column(String(30), nullable=False)
    company       = Column(String(50), nullable=False)
    vendor_id     = Column(
        Integer, ForeignKey("cycle_purchase_vendors.id", ondelete="RESTRICT"), nullable=False
    )

    buyer_user_id = Column(String(36), nullable=True, comment="採購人員（portal.db users.id，軟關聯）")
    buyer_name    = Column(String(100), nullable=True, comment="採購人員姓名快照")
    expected_date = Column(Date, nullable=True, comment="預計到貨日")
    total_amount  = Column(Numeric(14, 2), nullable=False, default=0, comment="採購總金額，明細加總，系統維護")
    status        = Column(String(20), nullable=False, default="draft",
                            comment="狀態：draft | issued | partial_received | received | cancelled"
                                     "（partial_received/received 由驗收單送出後系統自動重算，"
                                     "不可透過 PUT /pos/{id}/status 人工指定）")
    notes         = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    items = relationship(
        "CyclePurchasePOItem",
        back_populates="po",
        cascade="all, delete-orphan",
        order_by="CyclePurchasePOItem.id",
    )

    def __repr__(self):
        return f"<CyclePurchasePO id={self.id} no={self.po_no}>"


class CyclePurchasePOItem(CyclePurchaseBase):
    """採購明細（單一採購單裡的一個料號行，來自彙整單的調整量）"""
    __tablename__ = "cycle_purchase_po_items"
    __table_args__ = (
        UniqueConstraint("po_id", "item_id", name="uq_cp_po_item"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    po_id       = Column(
        Integer, ForeignKey("cycle_purchase_pos.id", ondelete="CASCADE"), nullable=False
    )
    summary_id  = Column(
        Integer, ForeignKey("cycle_purchase_summary.id", ondelete="RESTRICT"), nullable=False,
        comment="來源彙整列",
    )
    item_id     = Column(
        Integer, ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False
    )

    item_code   = Column(String(30),  nullable=False, comment="料號快照")
    item_name   = Column(String(200), nullable=False, comment="品名快照")
    unit        = Column(String(20),  nullable=True,  comment="單位快照")
    unit_price  = Column(Numeric(12, 4), nullable=True, comment="單價快照（來自彙整列）")

    ordered_qty = Column(Integer, nullable=False, default=0, comment="訂購數量（＝彙整列的調整量）")
    subtotal    = Column(Numeric(14, 2), nullable=False, default=0, comment="小計＝單價×數量，系統維護")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    po = relationship("CyclePurchasePO", back_populates="items")

    def __repr__(self):
        return f"<CyclePurchasePOItem id={self.id} po_id={self.po_id} item={self.item_code}>"
