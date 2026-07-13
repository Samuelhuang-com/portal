"""
週期採購 — 驗收單（獨立資料庫 cycle-purchase.db）

2026-07-11（第四期規劃，與 Samuel 確認）：
  1. 一張採購單可以分好幾次驗收（部分到貨），系統依累計驗收數量自動把採購單
     狀態帶成「部分到貨」或「完全到貨」（見 cycle_purchase_po.py 的狀態機
     更新說明）。
  2. 這期先不記錄「發票數量」——驗收當下通常還沒拿到發票，發票金額／數量
     的核對留到第五期「請款單」再處理。差異只比對「驗收數量 vs 訂購數量」。
  3. 驗收用獨立權限 cycle_purchase_receive（在 role_permissions.py 裡本來
     就已經預先註冊好，不需要新增）。
  4. 「驗收異常」狀態由系統自動判定：送出時只要有任一明細差異數量≠0，
     驗收單狀態自動變 discrepancy，不需要人工勾選。

分批驗收的差異計算設計（原規劃報告只寫「差異數量（公式）」，沒有講清楚
分批到貨時怎麼算，這裡是我方的實作決策，之後如果跟 Samuel 想的不一樣
可以再調整）：
  每一筆驗收明細有 is_final_for_item 旗標（預設 True，代表「這是這個料號
  這次驗收就完結了，不會再有後續驗收」——多數情況一次到齊，維持預設即可）。
  只有 is_final_for_item=True 的列，送出時才會計算 variance_qty（＝
  「這張採購單這個料號累計已驗收數量（含本次）」－「訂購數量」），
  ≠0 時要求填 variance_reason。is_final_for_item=False 的列（代表「這只是
  部分到貨，之後還會再驗收」）不計算差異，等到真正最後一次驗收時才計算。
  這樣分批到貨的中間過程不會被誤判成「差異」。

狀態機：draft（可編輯，還沒確定）-> completed（送出後沒有差異）／
        discrepancy（送出後有差異，見上述判定規則）。
        送出後（無論 completed 或 discrepancy）都不能再編輯明細——如果驗收
        資料本身填錯，屬於資料更正情境，目前沒有做「取消驗收單」，需要時
        再討論怎麼安全地反向沖銷已經影響到採購單狀態的數字。
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, Date,
    ForeignKey, UniqueConstraint, func,
)

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseReceiving(CyclePurchaseBase):
    """週期採購驗收單（一張採購單可以有多張驗收單，對應分批到貨）"""
    __tablename__ = "cycle_purchase_receiving"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    receiving_no    = Column(String(30), nullable=False, unique=True,
                              comment="驗收單號（系統產生，如 RC-202607-0001）")
    po_id           = Column(
        Integer, ForeignKey("cycle_purchase_pos.id", ondelete="RESTRICT"), nullable=False
    )
    receiver_user_id = Column(String(36), nullable=True, comment="驗收人員（portal.db users.id，軟關聯）")
    receiver_name     = Column(String(100), nullable=True, comment="驗收人員姓名快照")
    received_date     = Column(Date, nullable=False, comment="實際到貨／驗收日期")

    status = Column(String(20), nullable=False, default="draft",
                     comment="狀態：draft | completed | discrepancy"
                              "（completed/discrepancy 由送出時依明細差異自動判定，不可人工指定）")
    notes  = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CyclePurchaseReceiving id={self.id} no={self.receiving_no}>"


class CyclePurchaseReceivingItem(CyclePurchaseBase):
    """驗收明細（單一驗收單裡的一個採購明細行，本次驗收的數量）"""
    __tablename__ = "cycle_purchase_receiving_items"
    __table_args__ = (
        UniqueConstraint("receiving_id", "po_item_id", name="uq_cp_receiving_item"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    receiving_id = Column(
        Integer, ForeignKey("cycle_purchase_receiving.id", ondelete="CASCADE"), nullable=False
    )
    po_item_id   = Column(
        Integer, ForeignKey("cycle_purchase_po_items.id", ondelete="RESTRICT"), nullable=False,
        comment="對應的採購明細行",
    )
    item_id      = Column(
        Integer, ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False,
        comment="冗餘存一份料號 id，方便進貨數量報表直接查詢不必多層 join",
    )

    item_code = Column(String(30),  nullable=False, comment="料號快照")
    item_name = Column(String(200), nullable=False, comment="品名快照")
    unit      = Column(String(20),  nullable=True,  comment="單位快照")

    ordered_qty             = Column(Integer, nullable=False, comment="採購明細訂購數量快照")
    previously_received_qty = Column(Integer, nullable=False, default=0,
                                      comment="這張驗收單之前，這個採購明細行累計已驗收數量快照"
                                               "（建立本列時計算，供顯示與追溯用）")
    received_qty             = Column(Integer, nullable=False, default=0, comment="本次驗收數量")

    is_final_for_item = Column(Boolean, nullable=False, default=True,
                                comment="這個料號是否驗收完結（不會再有後續驗收）。"
                                         "True 才會在送出時計算差異；多數情況一次到齊，預設 True。")
    variance_qty    = Column(Integer, nullable=True,
                              comment="差異數量＝累計已驗收數量（含本次）－訂購數量。"
                                       "只有 is_final_for_item=True 的列，送出時才會計算；"
                                       "非最後一次驗收的列維持 NULL（分批到貨中途不算差異）。")
    variance_reason = Column(Text, nullable=True, comment="差異原因（variance_qty ≠ 0 時必填）")

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CyclePurchaseReceivingItem id={self.id} receiving_id={self.receiving_id} item={self.item_code}>"
