"""
核准請款單 SQLAlchemy ORM Models

資料表：
  approved_claim_requests      — 主單表（每張請款單一列）
  approved_claim_request_items — 品項子表（每個品項一列，月報表以此為粒度）

設計原則：
  - 欄位對照來源：ragic_claim_form_field_inventory.xlsx 標準欄位模型
  - 付款種類（payment_type）決定銀行欄位是否必填（零用金/匯款）
  - department_request_no 統一欄位，前端依部門顯示中文標籤（財請/工請/管請等）
  - detail_synced=False 表示品項尚未從 subtable 解析；True 表示品項已同步
  - raw_data_json 保留完整 API 原始 JSON，供欄位 mapping 補正
  - UNIQUE (ragic_sheet_path, ragic_record_id) 防重複同步
"""
import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean,
    Index, UniqueConstraint, func,
)

from app.core.database import Base

# ── 部門顯示名稱對照表（與請購單共用邏輯）────────────────────────────────────
# 停管部 Ragic 值為「客服」，需映射
CLAIM_DEPT_DISPLAY_MAP: dict[str, str] = {
    "執董室": "執董室",
    "營業":   "營業部",
    "行銷":   "行銷部",
    "財務":   "財務部",
    "客服":   "客服部",
    "管理":   "管理部",
    "資訊":   "資訊部",
    "設計":   "設計部",
}

# ── 部門請款編號標籤（前端顯示用，依部門決定中文標籤）──────────────────────
DEPT_REQUEST_NO_LABEL: dict[str, str] = {
    "執董室": "執董請",
    "營業部": "營請",
    "行銷部": "行請",
    "財務部": "財請",
    "客服部": "客請",
    "管理部": "管請",
    "資訊部": "資請",
    "設計部": "設請",
}

# ── 8 個部門的請款單 Ragic 設定 ─────────────────────────────────────────────
CLAIM_DEPT_SHEETS: list[dict] = [
    {
        "display_name": "執董室",
        "ragic_dept":   "執董室",
        "list_path":    "free-executive-office/9",
        "detail_path":  "free-executive-office/9",
        "flow_type":    "零用金型",
    },
    {
        "display_name": "營業部",
        "ragic_dept":   "營業",
        "list_path":    "free-business-division/21",
        "detail_path":  "free-business-division/21",
        "flow_type":    "比價型",
    },
    {
        "display_name": "行銷部",
        "ragic_dept":   "行銷",
        "list_path":    "marketing/40",
        "detail_path":  "marketing/40",
        "flow_type":    "比價型",
    },
    {
        "display_name": "管理部",
        "ragic_dept":   "管理",
        "list_path":    "freed-management-division/19",
        "detail_path":  "freed-management-division/19",
        "flow_type":    "零用金型",
    },
    {
        "display_name": "資訊部",
        "ragic_dept":   "資訊",
        "list_path":    "department-of-free-information/23",
        "detail_path":  "department-of-free-information/23",
        "flow_type":    "匯款型",
    },
    {
        "display_name": "客服部",
        "ragic_dept":   "客服",
        "list_path":    "free-management-department/10",
        "detail_path":  "free-management-department/10",
        "flow_type":    "零用金型",
    },
    {
        "display_name": "財務部",
        "ragic_dept":   "財務",
        "list_path":    "free-finance-department/15",
        "detail_path":  "free-finance-department/15",
        "flow_type":    "匯款型",
    },
    {
        "display_name": "設計部",
        "ragic_dept":   "設計",
        "list_path":    "free-design-department/2",
        "detail_path":  "free-design-department/2",
        "flow_type":    "比價型",
    },
]


class ApprovedClaimRequest(Base):
    """核准請款單主單表（每張請款單一列）"""
    __tablename__ = "approved_claim_requests"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 公司 / 部門 ──────────────────────────────────────────────────────────
    company             = Column(String(20),  nullable=False, default="樂群",
                                  comment="公司別")
    department_raw      = Column(String(20),  nullable=False, default="",
                                  comment="Ragic 原始部門值（如「客服」）")
    department_display  = Column(String(50),  nullable=False, default="",
                                  comment="Portal 顯示名稱（如「停管部」）")

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
                         name="uq_acr_sheet_record"),
        Index("ix_acr_status_approved_date", "status", "approved_date"),
        Index("ix_acr_company_dept",         "company", "department_display"),
        Index("ix_acr_applicant",            "applicant"),
        Index("ix_acr_detail_synced",        "detail_synced"),
        Index("ix_acr_payment_type",         "payment_type"),
    )

    def get_raw(self) -> dict:
        try:
            return json.loads(self.raw_data_json or "{}")
        except Exception:
            return {}

    def __repr__(self):
        return (
            f"<ACR id={self.id} no={self.request_no} "
            f"dept={self.department_display} status={self.status}>"
        )


class ApprovedClaimRequestItem(Base):
    """核准請款單品項子表（每個品項一列；月報表以此為輸出粒度）"""
    __tablename__ = "approved_claim_request_items"

    # ── 主鍵 ─────────────────────────────────────────────────────────────────
    id              = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯主單 ─────────────────────────────────────────────────────────────
    claim_id        = Column(Integer, nullable=False,
                              comment="FK → approved_claim_requests.id")

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
        UniqueConstraint("claim_id", "seq", name="uq_acri_claim_seq"),
        Index("ix_acri_claim_id", "claim_id"),
    )

    def __repr__(self):
        return (
            f"<ACRItem id={self.id} claim_id={self.claim_id} "
            f"seq={self.seq} name={str(self.item_name or '')[:30]}>"
        )
