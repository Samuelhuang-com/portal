"""
台中核准請款單 SQLAlchemy ORM Models（2026-09-16 完整複製自樂群 claim_request.py）

資料表：
  taichung_claim_requests      — 主單表（每張請款單一列）
  taichung_claim_request_items — 品項子表（每個品項一列，月報表以此為粒度）

與樂群的差異（使用者 2026-09-16 裁示）：
  - 獨立資料表（比照日曜）
  - department_display 一律取表單歸屬（ragic_sheet_config.display_name）
  - 核准日期取「簽署日期～簽署日期6」最大值（台中請款單沒有「日期N」欄位）
  - 額外欄位：總金額、沖預支、幣別、付款銀行
"""
import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    Index, UniqueConstraint, func,
)

from app.core.database import Base

# ── 10 個表單的請款單 Ragic 設定（硬編碼備援，正式使用 ragic_sheet_config 資料表 module=taichung_claim）
TAICHUNG_CLAIM_DEPT_SHEETS: list[dict] = [
    {"display_name": "公用表單", "ragic_dept": "公用表單", "list_path": "taichung-public-form/6", "detail_path": "taichung-public-form/6", "flow_type": ""},
    {"display_name": "客務部", "ragic_dept": "客務部", "list_path": "customer-service/14", "detail_path": "customer-service/14", "flow_type": ""},
    {"display_name": "業務部", "ragic_dept": "業務部", "list_path": "business/5", "detail_path": "business/5", "flow_type": ""},
    {"display_name": "工程部", "ragic_dept": "工程部", "list_path": "construction/5", "detail_path": "construction/5", "flow_type": ""},
    {"display_name": "財務部", "ragic_dept": "財務部", "list_path": "finance/12", "detail_path": "finance/12", "flow_type": ""},
    {"display_name": "資訊部", "ragic_dept": "資訊部", "list_path": "info/50", "detail_path": "info/50", "flow_type": ""},
    {"display_name": "行政辦公室", "ragic_dept": "行政辦公室", "list_path": "hr/7", "detail_path": "hr/7", "flow_type": ""},
    {"display_name": "廚房", "ragic_dept": "廚房", "list_path": "kitchen/4", "detail_path": "kitchen/4", "flow_type": ""},
    {"display_name": "餐飲", "ragic_dept": "餐飲", "list_path": "food-drink/5", "detail_path": "food-drink/5", "flow_type": ""},
    {"display_name": "房務部", "ragic_dept": "房務部", "list_path": "housekeeping/4", "detail_path": "housekeeping/4", "flow_type": ""},
]


class TaichungClaimRequest(Base):
    """台中核准請款單主單表（每張請款單一列）"""
    __tablename__ = "taichung_claim_requests"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 公司 / 部門 ──────────────────────────────────────────────────────────
    company             = Column(String(20),  nullable=False, default="台中",
                                  comment="公司別")
    department_raw      = Column(String(20),  nullable=False, default="",
                                  comment="Ragic 原始部門值")
    department_display  = Column(String(50),  nullable=False, default="",
                                  comment="Portal 顯示名稱（＝表單歸屬，如「客務部」）")

    # ── Ragic 來源識別 ───────────────────────────────────────────────────────
    ragic_sheet_path    = Column(String(100), nullable=False, default="",
                                  comment="來源 Sheet 路徑，如 lequn-finance-department/6")
    ragic_record_id     = Column(String(30),  nullable=False, default="",
                                  comment="Ragic 記錄主鍵")

    # ── 請款單主欄位 ─────────────────────────────────────────────────────────
    request_no          = Column(String(30),  nullable=False, default="",
                                  comment="請款單號（系統唯一單號）")
    department_request_no = Column(String(30), nullable=True,
                                  comment="部門請款編號（財請/工請/管請/專請等，各部門標籤不同）")
    purchase_no         = Column(String(30),  nullable=True,
                                  comment="採購編號（有採購流程時填入）")
    payment_no          = Column(String(30),  nullable=True,
                                  comment="付款編號（常空白）")
    voucher_no          = Column(String(30),  nullable=True,
                                  comment="傳票號碼（底色偏橘，多數有）")
    account_subject     = Column(String(100), nullable=True,
                                  comment="會科（費用科目）")
    apply_date          = Column(Date,        nullable=True,
                                  comment="申請日期（YYYY-MM-DD）")
    approved_date       = Column(Date,        nullable=True,
                                  comment="核准日期（status=F 時有意義，月報以此為基準）")
    applicant           = Column(String(50),  nullable=True,
                                  comment="申請人姓名")
    payment_type        = Column(String(20),  nullable=True,
                                  comment="付款種類：零用金 / 匯款")
    purpose_description = Column(Text,        nullable=True,
                                  comment="事由/說明（各部門標籤不同但統一映射）")

    # ── 金額 ─────────────────────────────────────────────────────────────────
    subtotal            = Column(Integer,     nullable=True,
                                  comment="小計（未稅）")
    tax                 = Column(Integer,     nullable=True,
                                  comment="營業稅")
    total               = Column(Integer,     nullable=True,
                                  comment="總計（含稅）")
    payable_amount      = Column(Integer,     nullable=True,
                                  comment="應付(繳)款（最終付款金額）")

    # ── 台中額外欄位（2026-09-16 使用者指定加入並顯示）──────────────────────
    total_amount        = Column(Integer,     nullable=True, comment="總金額")
    advance_offset      = Column(Integer,     nullable=True, comment="沖預支")
    currency            = Column(String(20),  nullable=True, comment="幣別")
    payment_bank        = Column(String(200), nullable=True, comment="付款銀行（公司出款銀行）")

    # ── 付款資訊 ─────────────────────────────────────────────────────────────
    payee               = Column(String(100), nullable=True,
                                  comment="受款者（收款人/公司）")
    bank_name           = Column(String(100), nullable=True,
                                  comment="受款銀行（匯款型必填）")
    bank_branch         = Column(String(100), nullable=True,
                                  comment="受款銀行分行（匯款型必填）")
    bank_account        = Column(String(50),  nullable=True,
                                  comment="匯款帳號（匯款型必填）")
    payment_date        = Column(Date,        nullable=True,
                                  comment="付款日期（預計付款日）")

    # ── 簽核狀態 ─────────────────────────────────────────────────────────────
    status              = Column(String(5),   nullable=False, default="N",
                                  comment="F=已核准 / N=待審 / REJ=退回")

    # ── 同步狀態旗標 ─────────────────────────────────────────────────────────
    detail_synced       = Column(Boolean,     nullable=False, default=False,
                                  comment="是否已完成品項子表同步")

    # ── 原始資料備援 ─────────────────────────────────────────────────────────
    raw_data_json       = Column(Text,        nullable=False, default="{}",
                                  comment="清單 API 原始 JSON（供欄位 mapping 補正）")

    # ── 時間戳 ───────────────────────────────────────────────────────────────
    last_updated_at     = Column(DateTime,    nullable=True,
                                  comment="Ragic「最後更新日期」原始值")
    sync_at             = Column(DateTime,    nullable=False, server_default=func.now(),
                                  comment="本次同步時間")
    created_at          = Column(DateTime,    nullable=False, server_default=func.now(),
                                  comment="首次建立時間")
    updated_at          = Column(DateTime,    nullable=False, server_default=func.now(),
                                  onupdate=func.now(), comment="最後更新時間")

    __table_args__ = (
        UniqueConstraint("ragic_sheet_path", "ragic_record_id",
                         name="uq_tc_cr_sheet_record"),
        Index("ix_tc_cr_status_approved_date", "status", "approved_date"),
        Index("ix_tc_cr_company_dept",         "company", "department_display"),
        Index("ix_tc_cr_applicant",            "applicant"),
        Index("ix_tc_cr_detail_synced",        "detail_synced"),
        Index("ix_tc_cr_payment_type",         "payment_type"),
    )

    def get_raw(self) -> dict:
        try:
            return json.loads(self.raw_data_json or "{}")
        except Exception:
            return {}

    def __repr__(self):
        return (
            f"<TCCR id={self.id} no={self.request_no} "
            f"dept={self.department_display} status={self.status}>"
        )


class TaichungClaimRequestItem(Base):
    """台中核准請款單品項子表（每個品項一列；月報表以此為輸出粒度）"""
    __tablename__ = "taichung_claim_request_items"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id              = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯主單 ─────────────────────────────────────────────────────────────
    claim_id        = Column(Integer, nullable=False,
                              comment="FK → taichung_claim_requests.id")

    # ── 品項資訊 ─────────────────────────────────────────────────────────────
    seq             = Column(Integer,      nullable=False, default=0,
                              comment="項次（子表格序號）")
    item_name       = Column(Text,         nullable=True,
                              comment="產品名稱（品項/服務/工程項目）")
    quantity        = Column(String(30),   nullable=True,
                              comment="數量（保留原始字串格式）")
    unit            = Column(String(20),   nullable=True,
                              comment="單位（式/個/月等）")
    item_note       = Column(Text,         nullable=True,
                              comment="品項備註（憑證號碼/付款月份等）")

    # ── 金額（請款核心欄位）─────────────────────────────────────────────────
    proposed_vendor_amount = Column(Integer, nullable=True,
                              comment="擬定廠商金額（請款核心金額）")

    # ── 憑證資訊（建議獨立存，不只放備註）──────────────────────────────────
    invoice_no      = Column(String(50),   nullable=True,
                              comment="發票號碼")
    receipt_no      = Column(String(50),   nullable=True,
                              comment="憑證號碼（油資/收據/其他）")

    # ── 同步時間 ─────────────────────────────────────────────────────────────
    sync_at         = Column(DateTime,     nullable=False, server_default=func.now(),
                              comment="同步時間")

    __table_args__ = (
        UniqueConstraint("claim_id", "seq", name="uq_tc_cri_claim_seq"),
        Index("ix_tc_cri_claim_id", "claim_id"),
    )

    def __repr__(self):
        return (
            f"<TCCRItem id={self.id} claim_id={self.claim_id} "
            f"seq={self.seq} name={str(self.item_name or '')[:30]}>"
        )
