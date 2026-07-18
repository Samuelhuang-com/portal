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

2026-07-16（與 Samuel 確認，「彙整單產生方式」改版——見
services/cycle_purchase_summary_service.py 開頭說明）：
  - 原本「產生彙整」是靠「週期＋期別」完全字串比對去抓已核准的請購明細，
    但期別是使用者自己選/打的自由文字欄位，沒有主檔管控，一旦打字不一致
    （例如 "2026-07" vs "2026/07"，或測試資料亂打），就會查到 0 筆、
    誤以為「沒有已核准的請購單」。
  - 改成：買家在「彙整單」頁面用「週期＋公司＋月份（依 approved_at 篩選）」
    篩出所有已核准、尚未被彙整過的請購單，用勾選的方式手動確認要納入
    這次彙整的範圍，不再依賴期別字串是否一致。彙整單本身的 period_label
    仍然會自動蓋章為系統從勾選的請購單本身 approved_at 推導出的「YYYY-MM」
    （不是「產生當下」的日期，也不是自由文字），使用者不能手動輸入，
    避免同樣的字串不一致問題重演。
  - 新增 is_summarized／summary_batch_no／summarized_at 三個欄位，用來
    標記「這張請購單是否已經被某次彙整動作納入過」，避免同一張已核准的
    請購單被勾選彙整兩次、重複計入數量。同一張請購單只要 is_summarized
    還是 False，就會一直出現在「可彙整清單」裡（不管核准月份是幾月，
    只要落在使用者選的篩選月份範圍內）。
  - 舊版「輸入週期＋期別字串」的產生彙整方式（generate_summary /
    POST /summary/generate）已經整個移除，不再保留備用路徑。

2026-07-17（第三次調整，與 Samuel 確認，「請購單流程」大改版——拿掉送出／核准，
改成「填寫期間內自行編輯 + 買家關閉」）：
  - **拿掉送出／核准**：不再需要 draft -> submitted -> approved/rejected 這個簽核
    流程。填單人自己建立、自己編輯，不需要送出給誰核准。
  - **當期格式**：請購單號（request_no）格式改成「PR-YYYY-MM-NNN」（如
    「PR-2026-07-001」，3 位流水號、每月從 001 重新起算），取代原本的
    「PR-YYYYMM-NNNN」。`period_label` 不再是使用者填的自由文字，改成系統在
    建立當下自動蓋章為建立月份的「YYYY-MM」，使用者不能修改（跟彙整單那邊
    2026-07-16 的期別蓋章邏輯是同一個精神，這次套用到請購單本身建立的當下）。
  - **編輯期限**：「自己申請的請購單，當月可以編輯」——編輯權限同時檢查兩件事：
    (1) 這張請購單還沒被關閉（`is_closed == False`），(2) 現在的真實月份還是這張
    請購單建立時的月份（`period_label == 當下的 YYYY-MM`）。只要其中一個條件不
    成立就不能編輯，過月是**自動**鎖定（不需要人工關閉），關閉則是**人工**的
    提前鎖定手段（例如 7/20 就想關掉 7 月，不用等到 7/31）。
  - **關閉功能**：新增 `is_closed`／`closed_by_user_id`／`closed_by_name`／
    `closed_at`／`close_batch_no` 欄位。買家（`cycle_purchase_close` 權限）可以
    「全部關閉」（某週期＋公司＋月份範圍內全部還開放中的請購單一次關閉）或
    「選擇請購單」（勾選特定幾張關閉）。關閉之後不能再新增/編輯明細，但可以
    「重新開啟」（`reopened_by_user_id`／`reopened_by_name`／`reopened_at`）
    改回可編輯狀態——重新開啟不會清掉上一次的關閉紀錄（`closed_*` 欄位保留
    當作歷史軌跡），只是額外蓋章「這次是誰、什麼時候重新開啟的」。
  - **與彙整單的連動**：`cycle_purchase_summary_service.list_eligible_requests()`／
    `generate_summary_from_requests()` 原本篩選 `status == "approved"` 的邏輯，
    改成篩選 `is_closed == True`——「關閉」取代「核准」成為「這張請購單的數量
    已經定案，可以放心拿去彙整」的判斷依據。
  - **一次性資料轉換**：改版當下既有的請購單，`status == "approved"` 的舊資料
    視為已經是「定案」狀態，一次性轉換設定 `is_closed = True`，並把
    `closed_by_user_id`／`closed_by_name`／`closed_at` 回填自原本的
    `approved_by_user_id`／`approved_by_name`／`approved_at`（有清楚的對應
    關係，不是憑空推測）；`draft`／`submitted`／`rejected` 的舊資料
    `is_closed` 維持預設值 False。這個轉換只做一次，寫在 migration SQL 裡，
    不是程式碼裡的常態邏輯。
  - `submitted_by_user_id`／`submitted_by_name`／`submitted_at` 三個欄位保留
    （改稱「填寫人」語意，不再有「送出」這個動作本身，但保留「這張單是誰
    建立的」這個記錄方便之後查詢；編輯權限本身沿用既有設計，是角色權限
    `cycle_purchase_request`，不是限定「只有建立者本人」才能編輯，這點沒有
    因為這次改版而變動）；`approved_by_user_id`／`approved_by_name`／
    `approved_at`／`reject_reason`／`status` 四＋一個欄位保留但停止在新資料
    上寫入（只留給改版前的歷史資料顯示用，SQLite 不支援輕易 DROP COLUMN，
    不值得為了這幾個欄位做整表重建）。
"""
from sqlalchemy import (
    Boolean, Column, Integer, String, Numeric, Text, DateTime, Date,
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
                             comment="請購單號（系統產生，2026-07-17 起格式為 PR-YYYY-MM-NNN，"
                                      "如 PR-2026-07-001，3 位流水號每月重新起算；"
                                      "改版前的舊資料仍是 PR-YYYYMM-NNNN 格式，不回溯改寫）")
    cycle_id       = Column(
        Integer, ForeignKey("cycle_purchase_cycles.id", ondelete="RESTRICT"), nullable=False
    )
    period_label   = Column(String(30), nullable=False,
                             comment="期別標籤，2026-07-17 起由系統在建立當下自動蓋章為"
                                      "建立月份的「YYYY-MM」，使用者不能修改；"
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
                             comment="改版前的狀態機殘留欄位（draft|submitted|approved|rejected），"
                                      "2026-07-17 起不再有業務邏輯讀寫這個欄位，只留給改版前的歷史"
                                      "資料顯示用；新資料一律固定寫 draft，實際可不可以編輯看的是"
                                      "is_closed／period_label，不是這個欄位")

    submitted_by_user_id = Column(String(36), nullable=True, comment="填寫人（portal.db users.id，軟關聯）")
    submitted_by_name    = Column(String(100), nullable=True, comment="填寫人姓名快照")
    submitted_at         = Column(DateTime, nullable=True, comment="建立時間快照（沿用舊欄位名稱，"
                                                                     "2026-07-17 起沒有「送出」這個動作了）")

    approved_by_user_id  = Column(String(36), nullable=True, comment="[改版前歷史欄位，2026-07-17 起停止寫入] 簽核人")
    approved_by_name     = Column(String(100), nullable=True, comment="[改版前歷史欄位，2026-07-17 起停止寫入] 簽核人姓名快照")
    approved_at          = Column(DateTime, nullable=True, comment="[改版前歷史欄位，2026-07-17 起停止寫入]")
    reject_reason        = Column(Text, nullable=True, comment="[改版前歷史欄位，2026-07-17 起停止寫入] 退回原因")

    # 2026-07-16 新增：見上方 class 註解「彙整單產生方式改版」。
    is_summarized    = Column(Boolean, nullable=False, default=False, server_default="0",
                               comment="是否已被某次「產生彙整」動作納入過，避免重複計入數量")
    summary_batch_no = Column(String(40), nullable=True,
                               comment="納入的彙整批次號（對應這次產生彙整時系統產生的批次編號）")
    summarized_at    = Column(DateTime, nullable=True, comment="被納入彙整的時間")

    # 2026-07-17 新增：見上方 class 註解「請購單流程大改版」。取代送出/核准，
    # 「關閉」才是真正把數量定案、可以放心拿去彙整的判斷依據。
    is_closed          = Column(Boolean, nullable=False, default=False, server_default="0",
                                 comment="是否已關閉（關閉後不能再新增/編輯明細，也不能再修改請購單本身）")
    closed_by_user_id  = Column(String(36), nullable=True, comment="關閉人（portal.db users.id，軟關聯）")
    closed_by_name     = Column(String(100), nullable=True, comment="關閉人姓名快照")
    closed_at          = Column(DateTime, nullable=True, comment="關閉時間")
    close_batch_no     = Column(String(40), nullable=True,
                                 comment="關閉批次號（\"全部關閉\"或\"選擇請購單關閉\"同一次動作的請購單共用同一個批次號）")
    reopened_by_user_id = Column(String(36), nullable=True, comment="重新開啟人（portal.db users.id，軟關聯）")
    reopened_by_name     = Column(String(100), nullable=True, comment="重新開啟人姓名快照")
    reopened_at          = Column(DateTime, nullable=True,
                                   comment="最近一次重新開啟的時間；重新開啟不會清掉 closed_* 欄位，"
                                            "那些是保留的關閉歷史紀錄，is_closed 才是目前真正的狀態")

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
