"""
週期採購 — 彙整單（獨立資料庫 cycle-purchase.db）

2026-07-11（第三期規劃，與 Samuel 確認）：
批次拿掉後，彙整不再是「批次→彙整」，改成「選一個週期＋期別，把該期
所有已核准（approved）的請購單明細，按公司＋料號 group by 加總」。草稿／
已送出／已退回的請購單一律不算進來。沿用 Ragic 原始設計精神（一列＝一個
工作項目，不是主表+明細的單據格式），但把「批次號」欄位換成
「cycle_id + period_label」。

供應商：透過料號對照表（company + item_id 唯一）取得 vendor_id，不使用
料號主檔的 default_vendor_id（見 cycle_purchase_item.py 開頭說明，7 筆
兩公司合併料號的 default_vendor_id 只會記到單一公司，會讓彙整分不出
另一家公司的實際供應商）。

冪等規則：同一週期＋期別＋公司＋料號只會有一列（UniqueConstraint）。重複
按「產生彙整」只會新增這次才出現、還沒彙整過的（公司＋料號）組合，已經
存在的列（不論是否已轉採購單）不會被覆寫或刪除——如果核准的請購明細在
彙整之後又增加，需要人工重新整理，這是刻意的保守設計，避免自動改動已經
在跑後續流程（尤其是已轉採購單）的數字。

狀態機：draft（可調整調整量／原因）-> converted（已轉採購單，鎖定不可再改）。
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, DateTime,
    ForeignKey, UniqueConstraint, func,
)

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseSummary(CyclePurchaseBase):
    """週期採購彙整列（一列＝一個週期＋期別＋公司＋料號的彙整工作項目）"""
    __tablename__ = "cycle_purchase_summary"
    __table_args__ = (
        UniqueConstraint("cycle_id", "period_label", "company", "item_id",
                          name="uq_cp_summary_cycle_period_company_item"),
    )

    id               = Column(Integer, primary_key=True, autoincrement=True)
    cycle_id         = Column(
        Integer, ForeignKey("cycle_purchase_cycles.id", ondelete="RESTRICT"), nullable=False
    )
    period_label     = Column(String(30), nullable=False, comment="期別標籤，同請購單")
    company          = Column(String(50), nullable=False, comment="公司別")
    item_id          = Column(
        Integer, ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False
    )
    item_mapping_id  = Column(
        Integer, ForeignKey("cycle_purchase_item_mappings.id", ondelete="SET NULL"), nullable=True,
        comment="該公司該料號的對照列（取得供應商／單價用）",
    )
    vendor_id        = Column(
        Integer, ForeignKey("cycle_purchase_vendors.id", ondelete="SET NULL"), nullable=True,
        comment="供應商（來自料號對照表 vendor_id，可能為 NULL——原始資料廠商欄位空的情況，"
                 "此時無法轉採購單，需先到料號對照表補上供應商）",
    )

    # 新增當下快照
    item_code   = Column(String(30),  nullable=False, comment="料號快照")
    item_name   = Column(String(200), nullable=False, comment="品名快照")
    unit        = Column(String(20),  nullable=True,  comment="單位快照")
    unit_price  = Column(Numeric(12, 4), nullable=True, comment="單價快照（來自該公司料號對照表）")

    demand_qty    = Column(Integer, nullable=False, default=0, comment="需求總量（各已核准請購單明細加總，系統計算）")
    adjusted_qty  = Column(Integer, nullable=False, default=0, comment="調整量（採購人員可調整，預設＝需求總量）")
    adjust_reason = Column(Text, nullable=True, comment="調整原因（調整量≠需求總量時必填）")

    status = Column(String(20), nullable=False, default="draft", comment="狀態：draft | converted")
    po_id  = Column(
        Integer, ForeignKey("cycle_purchase_pos.id", ondelete="SET NULL"), nullable=True,
        comment="轉採購單後回填",
    )

    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CyclePurchaseSummary id={self.id} item={self.item_code} company={self.company}>"
