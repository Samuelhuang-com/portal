"""
週期採購 — 料號主檔 + 料號對照表（獨立資料庫 cycle-purchase.db）

依《週期採購_Portal規劃評估_v1.0.md》第四節資料治理結論：
  - item_code 為「集團新編碼」，全集團唯一，不沿用日曜天地／春大直既有的
    E（工務）/C（清潔用品）/G（文具印刷）/S（營業用品）系列編碼——
    實測比對顯示兩家公司料號字串相同的 115 筆中，品名／廠商／單價三者
    完全一致的只有 7 筆，其餘 108 筆同號不同貨，不能假設「同代碼＝同品項」。
  - 各公司原始料號只存在 CyclePurchaseItemMapping，作為對照與追溯用途，
    不作為主鍵。

2026-07-11（與 Samuel 討論後新增部門範圍）：
  - 逐列核對兩家公司的「設料號明細表.xlsx」後確認：每家公司內部，分頁
    （工務用／清潔用品／文具&印刷／營業用品）、分頁內的「類別」、料號
    三者是乾淨的三層關係，沒有任何料號或類別橫跨兩個分頁。這個分頁邊界
    對應真實的功能性部門（工務部／清潔部／文具印刷部／營業部），不是單純
    的分類標籤。
  - 因此 CyclePurchaseItemMapping 新增 department_id：代表「這個料號在
    這家公司屬於哪個部門」，供請購單「可選料號」查詢按公司＋部門篩選用
    （見 cycle_purchase_request_service.get_available_items）。放在
    mapping 上而不是 item 上，因為部門歸屬本質是「公司＋料號」層級的
    事——理論上同一個集團料號在不同公司可能屬於不同部門（雖然這次資料
    裡 7 筆兩公司confirmed合併的料號剛好都落在同一個部門）。

2026-07-11（第三期彙整單／採購單規劃時發現並修正）：
  - 原本 original_vendor_name 只是文字欄位，沒有連到 cycle_purchase_vendors。
    對絕大多數單一公司專用的料號沒差，但 7 筆兩公司 confirmed 合併的料號，
    CyclePurchaseItem.default_vendor_id 只會記到「先建檔那家公司」（日曜
    天地）的供應商，春大直那邊實際供應商只剩文字、沒有 id 可用——彙整單
    「按供應商分」會分不出來。因此新增 vendor_id（可為 NULL，因為原始
    Excel 有些列的「廠商」欄位本來就是空的），透過一次性 SQL 回填腳本
    （scripts/backfill_item_mapping_vendor_id.py）比對 original_vendor_name
    字串補齊既有資料，不需要重跑整個匯入腳本、不需要再清空資料庫。日後
    彙整單一律依「料號對照表的 vendor_id」分供應商，不再看料號主檔的
    default_vendor_id（那個欄位保留給料號主檔頁面「預設供應商」顯示用，
    語意上代表「這個集團料號慣用的參考供應商」，不作為彙整/採購的依據）。
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Numeric, Text, DateTime,
    ForeignKey, UniqueConstraint, func,
)
from sqlalchemy.orm import relationship

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseItem(CyclePurchaseBase):
    """週期採購料號主檔（集團新編碼）"""
    __tablename__ = "cycle_purchase_items"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    item_code         = Column(String(30),  nullable=False, unique=True,
                                comment="集團料號（新編碼，非原公司料號）")
    item_name         = Column(String(200), nullable=False, comment="品名")
    spec              = Column(String(300), nullable=True,  comment="規格")
    category          = Column(String(50),  nullable=True,
                                comment="類別（如：清潔用品／文具印刷／營業用品／工務）")
    unit              = Column(String(20),  nullable=True,  comment="計量單位")
    default_qty       = Column(Integer,     nullable=False, default=0, comment="批次預載數量")
    moq               = Column(Integer,     nullable=False, default=0, comment="最小訂購量 MOQ")
    max_stock         = Column(Integer,     nullable=True,  comment="最大庫存量（僅供參考，不做消帳）")
    min_stock         = Column(Integer,     nullable=True,  comment="最小庫存量（僅供參考，不做消帳）")
    unit_price        = Column(Numeric(12, 4), nullable=True, comment="參考單價")
    default_vendor_id = Column(Integer, nullable=True,
                                comment="預設供應商 id（→ cycle_purchase_vendors.id，同資料庫內關聯）")
    is_active         = Column(Boolean, nullable=False, default=True, comment="是否啟用")
    is_cycle_item     = Column(Boolean, nullable=False, default=True, comment="是否週期採購專用標記")
    notes             = Column(Text, nullable=True, comment="備註（含原始資料來源說明）")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    mappings = relationship(
        "CyclePurchaseItemMapping",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="CyclePurchaseItemMapping.company",
    )

    def __repr__(self):
        return f"<CyclePurchaseItem id={self.id} code={self.item_code} name={self.item_name}>"


class CyclePurchaseItemMapping(CyclePurchaseBase):
    """
    週期採購料號對照表 — 集團料號 ↔ 公司原始料號

    ⚠️ 共同料號治理規則（依規劃報告第四節實測發現）：
    兩家公司即使原始料號字串相同，品項也極可能不同（實測僅約 6% 一致）。
    本表每一列代表「集團料號 + 特定公司」的一個對照關係，不得只憑原始料號
    字串自動建立對照，必須由人工確認品名／廠商／單價後，才把
    is_confirmed 設為 True。
    """
    __tablename__ = "cycle_purchase_item_mappings"
    __table_args__ = (
        UniqueConstraint("item_id", "company", name="uq_cp_item_mapping_item_company"),
    )

    id                   = Column(Integer, primary_key=True, autoincrement=True)
    item_id              = Column(
        Integer,
        ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    company              = Column(String(50),  nullable=False, comment="公司別（如：日曜天地／春大直）")
    department_id        = Column(
        Integer,
        ForeignKey("cycle_purchase_departments.id", ondelete="RESTRICT"),
        nullable=False,
        comment="這個料號在這家公司屬於哪個部門（2026-07-11 新增，供請購單可選料號按部門篩選用）",
    )
    original_code        = Column(String(30),  nullable=True, comment="公司原始料號（如 C0101001）")
    original_name        = Column(String(300), nullable=True, comment="公司原始品名")
    original_vendor_name = Column(String(200), nullable=True, comment="公司原始廠商名稱（文字，追溯用）")
    vendor_id            = Column(
        Integer,
        ForeignKey("cycle_purchase_vendors.id", ondelete="SET NULL"),
        nullable=True,
        comment="這個料號在這家公司實際跟哪個供應商叫貨（2026-07-11 新增，供彙整單/採購單"
                "按供應商分單用；可為 NULL，因為原始資料有些列廠商欄位本來就是空的）",
    )
    original_unit_price  = Column(Numeric(12, 4), nullable=True, comment="公司原始單價")
    is_confirmed         = Column(Boolean, nullable=False, default=False,
                                   comment="是否已由人工確認對照正確（不可自動合併帶入）")
    notes                = Column(Text, nullable=True, comment="備註（如資料清理過程說明）")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    item = relationship("CyclePurchaseItem", back_populates="mappings")

    def __repr__(self):
        return f"<CyclePurchaseItemMapping id={self.id} item_id={self.item_id} company={self.company}>"
