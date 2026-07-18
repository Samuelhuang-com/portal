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

2026-07-16（與 Samuel 確認，「匯總請購單」改版）：
⚠️ 重要背景：這張表與對應的採購單／驗收單／請款單／異常稽核，其實已在
2026-07-10～11 完整開發並掛載上線（main.py、navLabels.ts、前端頁面都已
存在），但當時的規劃文件（週期採購_Portal規劃評估_v1.1.md、欄位規格.md）
從未更新、CHANGELOG.md 也從未記錄，一直寫著「尚未實作」，直到本次才發現
文件與程式碼脫節。與 Samuel 確認後，採用「改寫現有 summary」而非另建新表
的方向，異動如下：

1. **新增 department_id**：原本彙整粒度是「公司＋料號」，會把同一料號在
   不同部門的需求量合計成一列，看不出部門別。會議討論（0715 會議記錄）
   需要「匯總請購單」呈現各部門別＋部門小計，因此把彙整粒度改為「公司＋
   料號＋部門」，一個部門一列，之後在 service 層依料號分組即可還原「部門
   別＋小計」的畫面。department_id 來自請購單（CyclePurchaseRequest.
   department_id），不是另外讓使用者填。
   ⚠️ 舊資料相容性：既有彙整列（2026-07-16 之前產生的）department_id 一律
   是 NULL，代表「歷史資料，未拆分部門」，不會回填（無法從已合併的
   demand_qty 反推是哪些部門貢獻的），新產生的彙整列才會有 department_id。
   ⚠️ UniqueConstraint 已改成含 department_id，但 SQLite 既有資料表的實體
   UNIQUE 限制不會因為改 ORM 而自動更新（SQLite ALTER TABLE 不支援改
   constraint，需要整張表重建才能真正生效於既有 DB）。目前的冪等性仍然是
   靠 service 層 `generate_summary()` 明確查詢再插入（不是靠 DB constraint
   擋重複），所以不影響功能正確性，只是 DB 層還沒有物理上的新約束把關，
   留下來供未來考慮要不要整張表重建時參考。

2. **新增 Ragic 拋轉追蹤欄位**：因為「匯總請購單」現在要能拋轉到 Ragic
   （由 Ragic 端另外新增一張「匯總請購單」表單，不是現有比價式請購單，
   見 cycle_purchase_ragic_push.py），需要記錄拋轉狀態。這批欄位用
   「同一批拋轉共用一個 batch_no」的方式記在每一列上（沒有另外開一張
   header 表），因為現有彙整單本來就是「一列＝一個工作項目」不做主表＋
   明細設計，延續同樣的精神。

狀態機：draft（可調整調整量／原因）-> converted（已轉採購單，鎖定不可再改）。
Ragic 拋轉不影響 draft/converted 狀態機，是額外的追蹤欄位（ragic_pushed）。
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Text, DateTime, Boolean,
    ForeignKey, UniqueConstraint, func,
)

from app.core.cycle_purchase_database import CyclePurchaseBase


class CyclePurchaseSummary(CyclePurchaseBase):
    """週期採購彙整列（一列＝一個週期＋期別＋公司＋料號＋部門的彙整工作項目，
    2026-07-16 起彙整粒度含部門；2026-07-16 之前產生的歷史列 department_id 為 NULL）"""
    __tablename__ = "cycle_purchase_summary"
    __table_args__ = (
        UniqueConstraint("cycle_id", "period_label", "company", "item_id", "department_id",
                          name="uq_cp_summary_cycle_period_company_item_dept"),
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
    department_id    = Column(
        Integer, ForeignKey("cycle_purchase_departments.id", ondelete="RESTRICT"), nullable=True,
        comment="部門別（2026-07-16 新增，來自請購單的 department_id）。"
                 "NULL 代表 2026-07-16 之前產生的歷史彙整列，未拆分部門",
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

    # 2026-07-16 新增：拋轉 Ragic「匯總請購單」追蹤欄位。同一次「拋轉到 Ragic」
    # 動作（同一 cycle+period+company 範圍）共用同一個 ragic_push_batch_no，
    # 沒有另外開 header 表，延續本表「一列＝一個工作項目」的設計精神。
    ragic_push_batch_no = Column(
        String(40), nullable=True,
        comment="拋轉批次號（同一次拋轉動作共用，如 CPSUM-202607-日曜天地-0001）",
    )
    ragic_pushed    = Column(Boolean, nullable=False, default=False, comment="是否已拋轉到 Ragic")
    ragic_record_id = Column(
        String(60), nullable=True,
        comment="Ragic 端回填的單號／記錄 ID（目前 Ragic「匯總請購單」表單尚未建立，"
                 "現階段為 stub 串接，此欄位可能是暫時性假值，見 cycle_purchase_ragic_push.py）",
    )
    ragic_pushed_at   = Column(DateTime, nullable=True, comment="拋轉成功時間")
    ragic_push_error  = Column(Text, nullable=True, comment="拋轉失敗時的錯誤訊息")

    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            f"<CyclePurchaseSummary id={self.id} item={self.item_code} "
            f"company={self.company} dept_id={self.department_id}>"
        )
