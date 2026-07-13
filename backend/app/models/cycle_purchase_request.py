"""
週期採購 — 請購單 + 請購明細（獨立資料庫 cycle-purchase.db）

2026-07-11（第二次調整，與 Samuel 討論後拿掉「批次」實體）：
原本第三層是「批次開放後系統自動產生請購單」，Samuel 認為「批次」的
開放/關閉狀態管理太重，且週採真正的範圍界線是「料號主檔」（不在料號
主檔裡的東西，如電腦設備，本來就不會出現在可選清單），不需要另外用
「批次時間窗」限制何時能請購。

拿掉批次後的設計：
  - 請購單改成直接掛在「週期設定」（cycle_id）+ 系統或使用者標記的
    「期別」（period_label，例如「2026-07」），取代原本的 batch_id。
  - 同一週期＋同一期別＋同一部門只能有一張請購單
    （UniqueConstraint 從 (batch_id, department_id) 改成
    (cycle_id, period_label, department_id)）。
  - 保留「一次幫所有適用部門建好空白單」的便利性，但改成隨時可觸發的
    動作（見 cycle_purchase_request_service.generate_requests_for_period），
    不需要先手動開一個「批次」才能動作，也沒有固定時間窗限制。
  - 批次相關的 model／schema／router（cycle_purchase_batch.py 系列）
    已搬到 _to_delete/ 保留備查，不再掛載進 app。

2026-07-11 與 Samuel 確認之設計（第一次，仍然有效）：
  - 會計科目：不在料號/部門主檔加欄位，由填單人在請購明細逐行手動選。
  - 簽核層級：第一版單一關卡（送出 -> 簽核 -> 核准/退回）。
  - 單價來源：請購明細的單價取自「該公司」在 cycle_purchase_item_mappings
    的 original_unit_price（不是 item.unit_price），因為兩家公司實際
    成交價可能不同，即使是集團共用的料號也一樣。
  - 送出人／簽核人：比照本專案「應用層軟關聯」原則，只存 portal.db 的
    user.id（字串 UUID，不建跨檔案 FK）與當下的 full_name 快照，
    不做即時跨資料庫 join。
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, DateTime, Date,
    ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseRequest(CyclePurchaseBase):
    """週期採購請購單（單一部門在單一週期＋期別下的一張單）"""
    __tablename__ = "cycle_purchase_requests"
    __table_args__ = (
        UniqueConstraint("cycle_id", "period_label", "department_id", name="uq_cp_request_cycle_period_dept"),
    )

    id             = Column(Integer, primary_key=True, autoincrement=True)
    request_no     = Column(String(30), nullable=False, unique=True,
                             comment="請購單號（系統產生，如 PR-202607-0001）")
    cycle_id       = Column(
        Integer, ForeignKey("cycle_purchase_cycles.id", ondelete="RESTRICT"), nullable=False
    )
    period_label   = Column(String(30), nullable=False,
                             comment="期別標籤（如「2026-07」），取代原本的批次，"
                                      "供之後彙整單把同一期各部門需求合併用")
    department_id  = Column(
        Integer, ForeignKey("cycle_purchase_departments.id", ondelete="RESTRICT"), nullable=False
    )
    company        = Column(String(50), nullable=False, comment="公司別（快照自部門主檔）")
    cost_center_id = Column(
        Integer, ForeignKey("cycle_purchase_cost_centers.id", ondelete="SET NULL"), nullable=True
    )
    total_amount   = Column(Numeric(14, 2), nullable=False, default=0, comment="請購總金額（明細加總，系統維護）")
    status         = Column(String(20), nullable=False, default="draft",
                             comment="狀態：draft | submitted | approved | rejected")

    submitted_by_user_id = Column(String(36), nullable=True, comment="送出人（portal.db users.id，軟關聯）")
    submitted_by_name    = Column(String(100), nullable=True, comment="送出人姓名快照")
    submitted_at         = Column(DateTime, nullable=True)

    approved_by_user_id  = Column(String(36), nullable=True, comment="簽核人（portal.db users.id，軟關聯）")
    approved_by_name     = Column(String(100), nullable=True, comment="簽核人姓名快照")
    approved_at          = Column(DateTime, nullable=True)
    reject_reason        = Column(Text, nullable=True, comment="退回原因（狀態為 rejected 時）")

    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    items = relationship(
        "CyclePurchaseRequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="CyclePurchaseRequestItem.id",
    )

    def __repr__(self):
        return f"<CyclePurchaseRequest id={self.id} no={self.request_no} status={self.status}>"


class CyclePurchaseRequestItem(CyclePurchaseBase):
    """請購明細（單一請購單裡的一個料號行）"""
    __tablename__ = "cycle_purchase_request_items"
    __table_args__ = (
        UniqueConstraint("request_id", "item_id", name="uq_cp_request_item"),
    )

    id              = Column(Integer, primary_key=True, autoincrement=True)
    request_id      = Column(
        Integer, ForeignKey("cycle_purchase_requests.id", ondelete="CASCADE"), nullable=False
    )
    item_id         = Column(
        Integer, ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False
    )
    item_mapping_id = Column(
        Integer, ForeignKey("cycle_purchase_item_mappings.id", ondelete="RESTRICT"), nullable=True,
        comment="採用哪一筆公司料號對照的單價",
    )
    account_code_id = Column(
        Integer, ForeignKey("cycle_purchase_account_codes.id", ondelete="SET NULL"), nullable=True,
        comment="會計科目（由填單人手動選）",
    )

    # 以下為新增當下的快照，避免日後料號主檔異動影響已送出的歷史金額
    item_code   = Column(String(30),  nullable=False, comment="料號快照")
    item_name   = Column(String(200), nullable=False, comment="品名快照")
    unit        = Column(String(20),  nullable=True,  comment="單位快照")
    unit_price  = Column(Numeric(12, 4), nullable=True, comment="單價快照（來自該公司料號對照表）")

    request_qty = Column(Integer, nullable=False, default=0, comment="請購數量")
    subtotal    = Column(Numeric(14, 2), nullable=False, default=0, comment="小計＝單價×數量（系統維護）")

    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    request = relationship("CyclePurchaseRequest", back_populates="items")

    def __repr__(self):
        return f"<CyclePurchaseRequestItem id={self.id} request_id={self.request_id} item={self.item_code}>"
