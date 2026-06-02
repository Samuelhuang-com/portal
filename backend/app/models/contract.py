"""
合約管理 SQLAlchemy ORM Models

資料表：
  contracts               — 合約主檔（每份合約一列）
  contract_items          — 合約明細項目（子表，可多筆）
  vendors                 — 廠商主檔
  budget_categories       — 科目與預算字典

設計原則：
  - contract_id 為自然鍵，格式 CON-YYYY-NNNN（唯一）
  - vendor_id 為廠商主檔鍵，格式 VND-NNNN
  - 所有金額使用 Numeric(12,2) 精度
  - 從 Excel 36 欄直接對應到 Contract 模型
  - detail dict 保存所有欄位供 Drawer 前端使用
"""
import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Numeric, Boolean,
    ForeignKey, UniqueConstraint, CheckConstraint, Index, func
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.time import twnow


def _now():
    """台灣時間戳"""
    return twnow()


# ══════════════════════════════════════════════════════════════════════════
# 1. 合約主檔 (Contract)
# ══════════════════════════════════════════════════════════════════════════

class Contract(Base):
    __tablename__ = "contracts"

    # ── 主鍵與唯一識別 ────────────────────────────────────────────────────────
    contract_id = Column(
        String(50),
        primary_key=True,
        comment="合約編號（CON-YYYY-NNNN，唯一鍵）"
    )

    # ── 基本資訊 ──────────────────────────────────────────────────────────────
    contract_name = Column(String(255), nullable=False, default="", comment="合約名稱")
    contract_type = Column(
        String(50),
        nullable=False,
        default="",
        comment="合約類型（定額月費/浮動/一次性/框架）"
    )
    contract_status = Column(
        String(50),
        nullable=False,
        default="草稿",
        comment="合約狀態（草稿/審核中/生效中/即將到期/已終止）"
    )
    responsible_dept = Column(String(100), nullable=False, default="", comment="權責部門")
    using_depts = Column(
        String(255),
        nullable=False,
        default="",
        comment="使用部門（多個時以;分隔）"
    )

    # ── 廠商資訊 ──────────────────────────────────────────────────────────────
    vendor_id = Column(
        String(50),
        ForeignKey("vendors.vendor_id", ondelete="RESTRICT"),
        nullable=False,
        default="",
        comment="廠商編號（VND-NNNN）"
    )
    vendor_name = Column(String(255), nullable=False, default="", comment="廠商名稱")

    # ── 合約期間 ──────────────────────────────────────────────────────────────
    start_date = Column(Date, nullable=False, comment="合約起日")
    end_date = Column(Date, nullable=False, comment="合約迄日")
    notification_days = Column(
        Integer,
        nullable=False,
        default=0,
        comment="到期前通知天數"
    )
    latest_termination_date = Column(
        Date,
        nullable=True,
        comment="最晚解約通知日（自動計算：end_date - notification_days）"
    )
    auto_renewal = Column(Boolean, nullable=False, default=False, comment="是否自動續約")

    # ── 金額與計價 ────────────────────────────────────────────────────────────
    currency = Column(String(10), nullable=False, default="TWD", comment="幣別")
    total_amount_tax_included = Column(
        Numeric(12, 2),
        nullable=False,
        default=0,
        comment="合約總金額含稅"
    )
    monthly_fixed_amount = Column(
        Numeric(10, 2),
        nullable=True,
        comment="每月固定金額"
    )
    pricing_method = Column(
        String(100),
        nullable=False,
        default="",
        comment="計價方式（固定金額/依實際用量/依單價×數量等）"
    )

    # ── 請購與請款設定 ────────────────────────────────────────────────────────
    needs_purchase_order = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否需請購單"
    )
    can_claim_without_po = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否可無請購請款"
    )

    # ── 分攤設定 ──────────────────────────────────────────────────────────────
    needs_allocation = Column(Boolean, nullable=False, default=False, comment="是否需分攤")
    allocation_method = Column(
        String(50),
        nullable=True,
        comment="分攤方式（比例/固定金額/不分攤）"
    )

    # ── 預算與科目 ────────────────────────────────────────────────────────────
    budget_year = Column(Integer, nullable=False, default=0, comment="預算年度")
    budget_category_l1 = Column(String(100), nullable=False, default="", comment="預算大項")
    budget_category_l2 = Column(String(100), nullable=False, default="", comment="預算細項")
    accounting_code = Column(String(50), nullable=False, default="", comment="會計科目")

    # ── 預算管理（新增欄位）────────────────────────────────────────────────────
    budget_source = Column(
        String(50),
        nullable=False,
        default="年度預算",
        comment="預算來源（年度預算/追加預算/專案預算）"
    )
    budget_control_method = Column(
        String(50),
        nullable=False,
        default="提醒",
        comment="預算控管方式（提醒/擋單/主管覆核）"
    )

    # ── 驗收與法律條款 ────────────────────────────────────────────────────────
    require_acceptance = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否需驗收"
    )

    # ── 風險與管理 ────────────────────────────────────────────────────────────
    risk_level = Column(
        String(20),
        nullable=False,
        default="中",
        comment="風險等級（低/中/高/關鍵）"
    )
    manager = Column(String(100), nullable=False, default="", comment="管理人")
    reviewer = Column(String(100), nullable=False, default="", comment="覆核人")

    # ── 審核流程欄位 ────────────────────────────────────────────────────────────
    approved_by = Column(String(100), nullable=True, comment="核准人（審核通過後填入）")
    approved_at = Column(DateTime, nullable=True, comment="核准時間")
    approval_comment = Column(Text, nullable=True, comment="審核意見（通過或拒絕原因）")

    # ── F3：公司別 / 部門別 / 計價規格（2026-06-01）────────────────────────────
    signing_company = Column(String(100), nullable=True, comment="簽約公司名稱")
    signing_dept    = Column(String(100), nullable=True, comment="簽約權責部門名稱")
    budget_company  = Column(String(100), nullable=True, comment="預算使用公司名稱")
    budget_dept     = Column(String(100), nullable=True, comment="預算使用部門名稱")
    pricing_spec    = Column(String(200), nullable=True, comment="計價規格名稱")

    # ── 附件 ────────────────────────────────────────────────────────────────────
    attachment_url = Column(String(500), nullable=True, comment="附件連結")
    remarks = Column(Text, nullable=False, default="", comment="備註")

    # ── 系統欄位 ────────────────────────────────────────────────────────────────
    created_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        comment="更新時間"
    )

    # ── 外部系統欄位 ──────────────────────────────────────────────────────────
    detail = Column(
        Text,
        nullable=False,
        default="{}",
        comment="Drawer detail dict（JSON 格式，含所有欄位的中文鍵）"
    )

    # ── 約束條件 ──────────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("contract_id", name="uk_contract_id"),
        CheckConstraint("start_date <= end_date", name="ck_date_order"),
        Index("idx_contract_status", "contract_status"),
        Index("idx_contract_vendor", "vendor_id"),
        Index("idx_contract_dept", "responsible_dept"),
        Index("idx_budget_year", "budget_year"),
    )

    # ── 關聯 ──────────────────────────────────────────────────────────────────
    vendor = relationship("Vendor", foreign_keys=[vendor_id], primaryjoin="Contract.vendor_id == Vendor.vendor_id", lazy="select")
    claims = relationship("ContractClaim", back_populates="contract", cascade="all, delete-orphan", lazy="select")

    def __repr__(self) -> str:
        return f"<Contract {self.contract_id} {self.contract_name}>"

    def get_detail(self) -> dict:
        """從 detail JSON 解析"""
        try:
            return json.loads(self.detail or "{}")
        except Exception:
            return {}

    def set_detail(self, detail_dict: dict) -> None:
        """設定 detail JSON"""
        self.detail = json.dumps(detail_dict, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════
# 2. 合約明細項目 (ContractItem)
# ══════════════════════════════════════════════════════════════════════════

class ContractItem(Base):
    __tablename__ = "contract_items"

    # ── 主鍵 ──────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 外鍵 ──────────────────────────────────────────────────────────────────
    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號（外鍵）"
    )

    # ── 明細資訊 ──────────────────────────────────────────────────────────────
    item_seq = Column(Integer, nullable=False, default=1, comment="項次（1, 2, 3...）")
    item_name = Column(String(255), nullable=False, default="", comment="項目名稱")
    item_category = Column(
        String(50),
        nullable=False,
        default="",
        comment="項目類別（月費/年費/一次性/用量/加購等）"
    )

    # ── 計價資訊 ──────────────────────────────────────────────────────────────
    unit_price_tax_excluded = Column(
        Numeric(10, 2),
        nullable=True,
        comment="單價（未稅）"
    )
    quantity = Column(
        Numeric(10, 2),
        nullable=True,
        comment="數量"
    )
    unit = Column(
        String(20),
        nullable=True,
        comment="單位（月/年/次/人/間/坪等）"
    )
    tax_rate = Column(
        Numeric(5, 2),
        nullable=False,
        default=5,
        comment="稅率（%）"
    )

    # ── 金額 ──────────────────────────────────────────────────────────────────
    amount_tax_excluded = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="金額（未稅）"
    )
    amount_tax_included = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="金額（含稅）"
    )

    # ── 固定/浮動 ────────────────────────────────────────────────────────────
    is_fixed = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否固定金額"
    )
    is_floating = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否浮動（如CPI調整）"
    )

    # ── 系統欄位 ──────────────────────────────────────────────────────────────
    created_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        comment="更新時間"
    )

    # ── 約束條件 ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_contract_items_contract_id", "contract_id"),
        Index("idx_contract_items_seq", "contract_id", "item_seq"),
    )

    def __repr__(self) -> str:
        return f"<ContractItem {self.contract_id}#{self.item_seq} {self.item_name}>"


# ══════════════════════════════════════════════════════════════════════════
# 3. 廠商主檔 (Vendor)
# ══════════════════════════════════════════════════════════════════════════

class Vendor(Base):
    __tablename__ = "vendors"

    # ── 主鍵 ──────────────────────────────────────────────────────────────────
    vendor_id = Column(
        String(50),
        primary_key=True,
        comment="廠商編號（VND-NNNN）"
    )

    # ── 基本資訊 ──────────────────────────────────────────────────────────────
    vendor_name = Column(
        String(255),
        nullable=False,
        default="",
        unique=True,
        comment="廠商名稱"
    )
    tax_id = Column(String(20), nullable=False, default="", comment="統一編號")

    # ── 聯絡資訊 ──────────────────────────────────────────────────────────────
    contact_person = Column(String(100), nullable=True, comment="聯絡人")
    phone = Column(String(20), nullable=True, comment="聯絡電話")
    email = Column(String(100), nullable=True, comment="Email")
    address = Column(String(500), nullable=True, comment="地址")

    # ── 付款資訊 ──────────────────────────────────────────────────────────────
    payment_terms = Column(
        String(100),
        nullable=True,
        comment="付款條件（月結30天/即付等）"
    )
    bank_name = Column(String(100), nullable=True, comment="銀行名稱")
    bank_account = Column(
        String(50),
        nullable=True,
        comment="銀行帳號（敏感欄位，需權限保護）"
    )

    # ── 廠商屬性 ──────────────────────────────────────────────────────────────
    vendor_type = Column(
        String(50),
        nullable=True,
        comment="廠商類別（系統/工程/維護/物料等）"
    )
    risk_level = Column(String(20), nullable=True, comment="風險等級（低/中/高）")
    is_critical = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否為關鍵供應商"
    )
    # F7（2026-06-01）
    managing_company = Column(String(100), nullable=True, comment="管理公司名稱")

    # ── 系統欄位 ──────────────────────────────────────────────────────────────
    created_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        comment="更新時間"
    )

    # ── 約束條件 ──────────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("vendor_id", name="uk_vendor_id"),
        UniqueConstraint("vendor_name", name="uk_vendor_name"),
        Index("idx_vendor_risk", "risk_level"),
    )

    def __repr__(self) -> str:
        return f"<Vendor {self.vendor_id} {self.vendor_name}>"


# ══════════════════════════════════════════════════════════════════════════
# 4. 科目與預算字典 (BudgetCategory)
# ══════════════════════════════════════════════════════════════════════════

class BudgetCategory(Base):
    __tablename__ = "budget_categories"

    # ── 主鍵 ──────────────────────────────────────────────────────────────────
    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 預算定義 ──────────────────────────────────────────────────────────────
    budget_year = Column(Integer, nullable=False, comment="預算年度")
    dept = Column(String(100), nullable=False, default="", comment="部門")
    category_l1 = Column(String(100), nullable=False, default="", comment="預算大項")
    category_l2 = Column(
        String(100),
        nullable=False,
        default="",
        comment="預算細項（必填，不得為空）"
    )
    accounting_code = Column(String(50), nullable=False, default="", comment="會計科目")
    payment_code = Column(
        String(50),
        nullable=True,
        comment="付款科目"
    )

    # ── 狀態 ──────────────────────────────────────────────────────────────────
    is_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否啟用"
    )
    effective_date = Column(Date, nullable=False, comment="生效日期")
    disabled_date = Column(Date, nullable=True, comment="停用日期")

    # ── 維護單位 ──────────────────────────────────────────────────────────────
    maintain_unit = Column(
        String(100),
        nullable=False,
        default="",
        comment="維護單位（財務/管理部等）"
    )

    # ── 系統欄位 ──────────────────────────────────────────────────────────────
    created_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=_now,
        onupdate=_now,
        comment="更新時間"
    )

    # ── 約束條件 ──────────────────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "budget_year",
            "category_l1",
            "category_l2",
            "dept",
            name="uk_budget_category"
        ),
        Index("idx_budget_category_year", "budget_year"),
        Index("idx_budget_category_dept", "dept"),
        Index("idx_budget_category_enabled", "is_enabled"),
    )

    def __repr__(self) -> str:
        return f"<BudgetCategory {self.budget_year} {self.category_l1}/{self.category_l2}>"


# ══════════════════════════════════════════════════════════════════════════
# 5. 請款 / 核銷記錄 (ContractClaim)
# ══════════════════════════════════════════════════════════════════════════

class ContractClaim(Base):
    """合約請款 / 核銷記錄"""
    __tablename__ = "contract_claims"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯合約 ────────────────────────────────────────────────────────
    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    contract = relationship("Contract", back_populates="claims")

    # ── 核心欄位 ────────────────────────────────────────────────────────
    claim_type = Column(
        String(20),
        nullable=False,
        default="請款",
        comment="類型（請款/核銷/其他）"
    )
    claim_date = Column(
        String(10),
        nullable=False,
        comment="請款日期（YYYY-MM-DD）"
    )
    invoice_no = Column(String(100), nullable=True, comment="發票號碼")
    amount = Column(Numeric(14, 2), nullable=False, default=0, comment="請款金額")
    status = Column(
        String(20),
        nullable=False,
        default="待審核",
        comment="狀態（待審核/已核准/已拒絕/已付款）"
    )
    approver = Column(String(100), nullable=True, comment="核准人")
    remarks = Column(String(500), nullable=True, comment="備註")
    review_log = Column(Text, nullable=True, default="[]", comment="審核軌跡（JSON array）")
    # F6（2026-06-01）
    cost_company = Column(String(100), nullable=True, comment="費用歸屬公司名稱")

    # ── 稽核時間 ────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, default=_now, comment="建立時間")
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now, comment="更新時間")

    __table_args__ = (
        Index("idx_claim_contract", "contract_id"),
        Index("idx_claim_date",     "claim_date"),
        Index("idx_claim_status",   "status"),
    )

    def __repr__(self) -> str:
        return f"<ContractClaim {self.id} {self.claim_type} {self.amount}>"


# ══════════════════════════════════════════════════════════════════════════
# 6. 合約續約申請 (ContractRenewal)
# ══════════════════════════════════════════════════════════════════════════

class ContractRenewal(Base):
    """
    合約續約申請記錄。
    每筆對應一份原合約的一次續約申請，含審核流程與審核軌跡。
    """
    __tablename__ = "contract_renewals"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯合約 ──────────────────────────────────────────────────────────
    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="原合約編號"
    )
    contract = relationship("Contract", foreign_keys=[contract_id], lazy="select")

    # ── 申請內容 ──────────────────────────────────────────────────────────
    renewal_start_date = Column(
        String(10),
        nullable=False,
        comment="續約起日（YYYY-MM-DD）"
    )
    renewal_end_date = Column(
        String(10),
        nullable=False,
        comment="續約迄日（YYYY-MM-DD）"
    )
    new_amount = Column(
        Numeric(14, 2),
        nullable=True,
        comment="續約金額（含稅）；None 表示與原合約相同"
    )
    renewal_reason = Column(
        Text,
        nullable=False,
        default="",
        comment="續約原因 / 說明"
    )
    remarks = Column(String(500), nullable=True, comment="備註")

    # ── 申請人 ────────────────────────────────────────────────────────────
    applicant = Column(
        String(100),
        nullable=False,
        default="",
        comment="申請人帳號或姓名"
    )
    applicant_dept = Column(
        String(100),
        nullable=True,
        comment="申請部門"
    )

    # ── 審核狀態 ──────────────────────────────────────────────────────────
    status = Column(
        String(20),
        nullable=False,
        default="待審核",
        comment="狀態（待審核/已核准/已拒絕/已撤回）"
    )
    reviewer = Column(String(100), nullable=True, comment="審核人帳號或姓名")
    reviewed_at = Column(DateTime, nullable=True, comment="審核時間")
    review_comment = Column(String(500), nullable=True, comment="審核意見")

    # ── 審核軌跡 ──────────────────────────────────────────────────────────
    review_log = Column(
        Text,
        nullable=False,
        default="[]",
        comment="審核操作紀錄（JSON array）"
    )

    # ── 系統欄位 ──────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, default=_now, comment="建立時間")
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now, comment="更新時間")

    __table_args__ = (
        Index("idx_renewal_contract", "contract_id"),
        Index("idx_renewal_status",   "status"),
        Index("idx_renewal_created",  "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ContractRenewal {self.id} {self.contract_id} {self.status}>"


# ══════════════════════════════════════════════════════════════════════════
# 7. 請款附件 (ContractClaimAttachment)
# ══════════════════════════════════════════════════════════════════════════

class ContractClaimAttachment(Base):
    """
    請款單附件記錄。
    每筆對應一份 ContractClaim 的一個上傳檔案（PDF / 圖片）。
    """
    __tablename__ = "contract_claim_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯請款 ──────────────────────────────────────────────────────────
    claim_id = Column(
        Integer,
        ForeignKey("contract_claims.id", ondelete="CASCADE"),
        nullable=False,
        comment="請款 ID"
    )
    claim = relationship("ContractClaim", backref="attachments", lazy="select")

    # ── 檔案資訊 ──────────────────────────────────────────────────────────
    stored_filename = Column(
        String(255),
        nullable=False,
        comment="儲存在磁碟上的檔名（UUID + 副檔名）"
    )
    original_filename = Column(
        String(500),
        nullable=False,
        comment="使用者上傳的原始檔名"
    )
    content_type = Column(
        String(100),
        nullable=False,
        comment="MIME type（application/pdf / image/*）"
    )
    file_size = Column(
        Integer,
        nullable=False,
        default=0,
        comment="檔案大小（bytes）"
    )

    # ── 上傳者 ────────────────────────────────────────────────────────────
    uploader = Column(String(100), nullable=False, default="", comment="上傳者帳號")

    # ── 系統欄位 ──────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, default=_now, comment="上傳時間")

    __table_args__ = (
        Index("idx_attachment_claim", "claim_id"),
    )

    def __repr__(self) -> str:
        return f"<ContractClaimAttachment {self.id} claim={self.claim_id} {self.original_filename}>"


# ══════════════════════════════════════════════════════════════════════════════
# ContractAttachment — 合約本體附件
# ══════════════════════════════════════════════════════════════════════════════

class ContractAttachment(Base):
    """
    合約本體附件記錄。
    每筆對應一份 Contract 的一個上傳檔案（PDF / 圖片）。
    """
    __tablename__ = "contract_attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── 關聯合約 ──────────────────────────────────────────────────────────
    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    contract = relationship("Contract", backref="attachments", lazy="select")

    # ── 檔案資訊 ──────────────────────────────────────────────────────────
    stored_filename = Column(
        String(255),
        nullable=False,
        comment="儲存在磁碟上的檔名（UUID + 副檔名）"
    )
    original_filename = Column(
        String(500),
        nullable=False,
        comment="使用者上傳的原始檔名"
    )
    content_type = Column(
        String(100),
        nullable=False,
        comment="MIME type（application/pdf / image/*）"
    )
    file_size = Column(
        Integer,
        nullable=False,
        default=0,
        comment="檔案大小（bytes）"
    )

    # ── 上傳者 ────────────────────────────────────────────────────────────
    uploader = Column(String(100), nullable=False, default="", comment="上傳者帳號")

    # ── 系統欄位 ──────────────────────────────────────────────────────────
    created_at = Column(DateTime, nullable=False, default=_now, comment="上傳時間")

    __table_args__ = (
        Index("idx_contract_attachment_contract", "contract_id"),
    )

    def __repr__(self) -> str:
        return f"<ContractAttachment {self.id} contract={self.contract_id} {self.original_filename}>"


# ══════════════════════════════════════════════════════════════════════════
# F3 — 費用分攤明細 (ContractCostAllocation)
# ══════════════════════════════════════════════════════════════════════════

class ContractCostAllocation(Base):
    """
    合約費用分攤明細。
    一份合約可對應多筆分攤記錄（多家公司，各有比例或固定金額）。
    使用整批覆寫（PUT）：前端每次更新時刪舊插新。
    """
    __tablename__ = "contract_cost_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    company_name    = Column(String(100),   nullable=False, comment="分攤公司名稱（冗餘儲存，歷史保全）")
    allocation_type = Column(String(20),    nullable=False, default="percentage",
                             comment="分攤類型：percentage（比例）/ fixed（固定金額）")
    value           = Column(Numeric(14, 4), nullable=False, comment="數值：比例 0~100 或金額")
    created_at      = Column(DateTime,      nullable=False, default=_now)

    contract = relationship("Contract", foreign_keys=[contract_id], lazy="select")

    __table_args__ = (
        Index("idx_cost_alloc_contract", "contract_id"),
    )

    def __repr__(self) -> str:
        return f"<CostAlloc {self.id} {self.company_name} {self.allocation_type}={self.value}>"


# ══════════════════════════════════════════════════════════════════════════
# H1 — 合約範本 (ContractTemplate)
# ══════════════════════════════════════════════════════════════════════════

class ContractTemplate(Base):
    """
    合約範本主檔。
    儲存常用合約類型的預設欄位值，新增合約時可一鍵套用。
    """
    __tablename__ = "contract_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="範本名稱")
    contract_type = Column(String(50), nullable=False, default="", comment="合約類型（與合約主表一致）")
    description = Column(Text, nullable=True, comment="範本說明")

    # 套用後預填的欄位預設值
    default_currency = Column(String(10), nullable=False, default="TWD", comment="預設幣別")
    default_notification_days = Column(Integer, nullable=False, default=30, comment="預設到期通知天數")
    default_auto_renewal = Column(Boolean, nullable=False, default=False, comment="預設是否自動續約")
    default_needs_purchase_order = Column(Boolean, nullable=False, default=False, comment="預設需請購單")
    default_require_acceptance = Column(Boolean, nullable=False, default=False, comment="預設需驗收")
    default_risk_level = Column(String(20), nullable=False, default="中", comment="預設風險等級")
    default_pricing_method = Column(String(100), nullable=False, default="", comment="預設計價方式")
    default_budget_source = Column(String(50), nullable=False, default="年度預算", comment="預設預算來源")
    default_remarks = Column(Text, nullable=True, comment="預設備註範本（可含說明文字）")

    is_enabled = Column(Boolean, nullable=False, default=True, comment="是否啟用")
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        Index("idx_template_type", "contract_type"),
        Index("idx_template_enabled", "is_enabled"),
    )

    def __repr__(self) -> str:
        return f"<ContractTemplate {self.id} {self.name}>"


# ══════════════════════════════════════════════════════════════════════════
# H2 — 合約變更歷程 (ContractChangeLog)
# ══════════════════════════════════════════════════════════════════════════

class ContractChangeLog(Base):
    """
    合約欄位變更歷程。
    每次 PUT /{contract_id} 執行時，對比舊值與新值，
    有差異的欄位各自建立一筆記錄。
    """
    __tablename__ = "contract_change_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    field_name = Column(String(100), nullable=False, comment="欄位名稱（英文）")
    field_label = Column(String(100), nullable=False, default="", comment="欄位中文標籤")
    old_value = Column(Text, nullable=True, comment="舊值（轉字串）")
    new_value = Column(Text, nullable=True, comment="新值（轉字串）")
    operator = Column(String(100), nullable=False, default="", comment="操作人帳號")
    operated_at = Column(DateTime, nullable=False, default=_now, comment="操作時間")

    __table_args__ = (
        Index("idx_change_log_contract", "contract_id"),
        Index("idx_change_log_time", "operated_at"),
    )

    def __repr__(self) -> str:
        return f"<ContractChangeLog {self.id} {self.contract_id}.{self.field_name}>"


# ══════════════════════════════════════════════════════════════════════════
# H3 — 分期付款計劃 (ContractPaymentSchedule)
# ══════════════════════════════════════════════════════════════════════════

class ContractPaymentSchedule(Base):
    """
    合約分期付款里程碑。
    一份合約可有多個付款里程碑，
    排程每日 09:45 掃描逾期未付里程碑並建立 Memo 提醒。
    """
    __tablename__ = "contract_payment_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    milestone_name = Column(String(200), nullable=False, default="", comment="里程碑名稱（如：第一期款）")
    due_date = Column(String(10), nullable=False, comment="應付日期（YYYY-MM-DD）")
    amount = Column(Numeric(14, 2), nullable=False, default=0, comment="應付金額（含稅）")
    status = Column(
        String(20),
        nullable=False,
        default="待付款",
        comment="狀態（待付款/已付款/逾期/取消）"
    )
    paid_date = Column(String(10), nullable=True, comment="實際付款日期（YYYY-MM-DD）")
    notes = Column(Text, nullable=True, comment="備註")

    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    contract = relationship("Contract", foreign_keys=[contract_id], lazy="select")

    __table_args__ = (
        Index("idx_payment_schedule_contract", "contract_id"),
        Index("idx_payment_schedule_due", "due_date"),
        Index("idx_payment_schedule_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ContractPaymentSchedule {self.id} {self.contract_id} {self.milestone_name}>"


# ══════════════════════════════════════════════════════════════════════════
# H4 — 操作稽核日誌 (ContractAuditLog)
# ══════════════════════════════════════════════════════════════════════════

class ContractAuditLog(Base):
    """
    合約模組操作稽核日誌。
    記錄所有 POST / PUT / DELETE 操作，
    含操作端點、操作人、payload 摘要、執行結果。
    """
    __tablename__ = "contract_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    contract_id = Column(
        String(50),
        nullable=True,
        comment="相關合約編號（刪除合約後保留 contract_id 字串，不設外鍵）"
    )
    action = Column(String(50), nullable=False, comment="動作（create/update/delete/approve/reject/submit 等）")
    resource = Column(String(50), nullable=False, default="contract", comment="資源類型（contract/claim/renewal/vendor/template）")
    resource_id = Column(String(100), nullable=True, comment="資源 ID（contract_id / claim.id 等）")
    operator = Column(String(100), nullable=False, default="", comment="操作人帳號")
    payload_summary = Column(Text, nullable=True, comment="操作摘要（JSON 或文字，敏感欄位已遮罩）")
    result = Column(String(20), nullable=False, default="success", comment="結果（success/error）")
    error_detail = Column(Text, nullable=True, comment="錯誤詳情（result=error 時填入）")
    operated_at = Column(DateTime, nullable=False, default=_now, comment="操作時間")
    ip_address = Column(String(45), nullable=True, comment="操作者 IP（IPv4/IPv6）")

    __table_args__ = (
        Index("idx_audit_log_contract", "contract_id"),
        Index("idx_audit_log_operator", "operator"),
        Index("idx_audit_log_time", "operated_at"),
        Index("idx_audit_log_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<ContractAuditLog {self.id} {self.action} {self.resource}/{self.resource_id}>"


# ══════════════════════════════════════════════════════════════════════════
# I1 — 多層審核關卡 (ContractApprovalStage)
# ══════════════════════════════════════════════════════════════════════════

class ContractApprovalStage(Base):
    """
    合約多層審核關卡記錄。
    送審（POST /submit）時，若合約類型有預設關卡設定，
    系統自動建立各關卡記錄；每個關卡由對應審核人獨立核准或拒絕。

    狀態機：
      待審核 → 已核准（下一關卡解鎖）
      待審核 → 已拒絕（合約退回草稿，後續關卡取消）

    向下相容：無此表記錄時走原有單階段流程。
    """
    __tablename__ = "contract_approval_stages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    submission_round = Column(
        Integer,
        nullable=False,
        default=1,
        comment="第幾次送審（每次送審 +1，用於區隔歷次送審的關卡記錄）"
    )
    stage_order = Column(Integer, nullable=False, comment="關卡順序（1=主管, 2=財務, 3=法務）")
    stage_name = Column(String(50), nullable=False, comment="關卡名稱（主管審核/財務審核/法務審核）")
    assigned_to = Column(String(100), nullable=True, comment="指定審核人帳號（空=任何有權限者皆可）")
    status = Column(
        String(20),
        nullable=False,
        default="待審核",
        comment="關卡狀態（待審核/已核准/已拒絕/已取消）"
    )
    reviewer = Column(String(100), nullable=True, comment="實際審核人帳號")
    comment = Column(Text, nullable=True, comment="審核意見")
    reviewed_at = Column(DateTime, nullable=True, comment="審核時間")
    created_at = Column(DateTime, nullable=False, default=_now)

    contract = relationship("Contract", foreign_keys=[contract_id], lazy="select")

    __table_args__ = (
        Index("idx_approval_stage_contract", "contract_id"),
        Index("idx_approval_stage_status", "status"),
        Index("idx_approval_stage_round", "contract_id", "submission_round"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalStage {self.id} {self.contract_id} R{self.submission_round} S{self.stage_order} {self.status}>"


# ══════════════════════════════════════════════════════════════════════════
# I1 — 多層審核關卡設定 (ContractApprovalConfig)
# ══════════════════════════════════════════════════════════════════════════

class ContractApprovalConfig(Base):
    """
    審核關卡設定。
    定義各合約類型的預設審核關卡清單；
    送審時查詢此設定，自動建立 ContractApprovalStage 記錄。
    若某合約類型無設定，走原有單階段流程。
    """
    __tablename__ = "contract_approval_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_type = Column(
        String(50),
        nullable=False,
        comment="合約類型（對應 contracts.contract_type；'*' 表示所有類型預設）"
    )
    stage_order = Column(Integer, nullable=False, comment="關卡順序（1/2/3）")
    stage_name = Column(String(50), nullable=False, comment="關卡名稱")
    assigned_to = Column(String(100), nullable=True, comment="預設指定審核人帳號（空=任何有權限者）")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    __table_args__ = (
        Index("idx_approval_config_type", "contract_type"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalConfig {self.id} {self.contract_type} S{self.stage_order} {self.stage_name}>"


# ══════════════════════════════════════════════════════════════════════════
# I2 — 驗收記錄 (ContractAcceptance)
# ══════════════════════════════════════════════════════════════════════════

class ContractAcceptance(Base):
    """
    合約驗收記錄。
    服務完成後建立驗收，驗收通過後才可提交請款
    （若合約設定 require_acceptance=True）。
    """
    __tablename__ = "contract_acceptances"

    id = Column(Integer, primary_key=True, autoincrement=True)

    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    acceptance_name = Column(String(200), nullable=False, default="", comment="驗收項目名稱")
    acceptance_date = Column(String(10), nullable=False, comment="驗收日期（YYYY-MM-DD）")
    accepted_by = Column(String(100), nullable=False, default="", comment="驗收人帳號")
    status = Column(
        String(20),
        nullable=False,
        default="待驗收",
        comment="驗收狀態（待驗收/已驗收/驗收失敗）"
    )
    period_start = Column(String(10), nullable=True, comment="驗收服務期間起（YYYY-MM-DD）")
    period_end = Column(String(10), nullable=True, comment="驗收服務期間迄（YYYY-MM-DD）")
    notes = Column(Text, nullable=True, comment="驗收說明/備註")
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    contract = relationship("Contract", foreign_keys=[contract_id], lazy="select")

    __table_args__ = (
        Index("idx_acceptance_contract", "contract_id"),
        Index("idx_acceptance_date", "acceptance_date"),
        Index("idx_acceptance_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ContractAcceptance {self.id} {self.contract_id} {self.acceptance_name} {self.status}>"


# ══════════════════════════════════════════════════════════════════════════
# I3 — 保證金追蹤 (ContractDeposit)
# ══════════════════════════════════════════════════════════════════════════

class ContractDeposit(Base):
    """
    合約保證金追蹤。
    記錄廠商保證金（履約/投標/其他），
    排程每日 10:00 掃描退還日 30 天內的保證金並建立 Memo 提醒。
    """
    __tablename__ = "contract_deposits"

    id = Column(Integer, primary_key=True, autoincrement=True)

    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    deposit_type = Column(
        String(50),
        nullable=False,
        default="履約保證金",
        comment="保證金類型（履約保證金/投標保證金/其他）"
    )
    deposit_amount = Column(Numeric(14, 2), nullable=False, default=0, comment="保證金金額")
    deposit_date = Column(String(10), nullable=False, comment="存入日期（YYYY-MM-DD）")
    expected_return_date = Column(String(10), nullable=False, comment="預計退還日（YYYY-MM-DD）")
    actual_return_date = Column(String(10), nullable=True, comment="實際退還日（YYYY-MM-DD）")
    status = Column(
        String(20),
        nullable=False,
        default="保留中",
        comment="狀態（保留中/申請退還/已退還/已沒收）"
    )
    bank_name = Column(String(100), nullable=True, comment="銀行名稱")
    notes = Column(Text, nullable=True, comment="備註")
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    contract = relationship("Contract", foreign_keys=[contract_id], lazy="select")

    __table_args__ = (
        Index("idx_deposit_contract", "contract_id"),
        Index("idx_deposit_return_date", "expected_return_date"),
        Index("idx_deposit_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ContractDeposit {self.id} {self.contract_id} {self.deposit_type} ${self.deposit_amount}>"


# ══════════════════════════════════════════════════════════════════════════
# K2 — SLA 指標定義 (ContractSlaMetric)
# ══════════════════════════════════════════════════════════════════════════

class ContractSlaMetric(Base):
    """
    合約 SLA 指標定義。
    每份服務合約可設定多個 SLA 指標（可用率、回應時間、解決時間等），
    各指標有目標值與衡量週期。
    """
    __tablename__ = "contract_sla_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(
        String(50),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        comment="合約編號"
    )
    metric_name = Column(String(100), nullable=False, comment="指標名稱（如：系統可用率）")
    metric_type = Column(
        String(50),
        nullable=False,
        default="自訂",
        comment="指標類型（可用率/回應時間/解決時間/自訂）"
    )
    target_value = Column(Numeric(10, 4), nullable=False, comment="目標值")
    target_unit = Column(
        String(20),
        nullable=False,
        default="%",
        comment="單位（%/小時/天/次）"
    )
    measurement_period = Column(
        String(20),
        nullable=False,
        default="monthly",
        comment="衡量週期（monthly/quarterly/annual）"
    )
    description = Column(Text, nullable=True, comment="指標說明")
    is_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=_now)
    updated_at = Column(DateTime, nullable=False, default=_now, onupdate=_now)

    contract = relationship("Contract", foreign_keys=[contract_id], lazy="select")

    __table_args__ = (
        Index("idx_sla_metric_contract", "contract_id"),
    )

    def __repr__(self) -> str:
        return f"<SlaMetric {self.id} {self.metric_name} target={self.target_value}{self.target_unit}>"


# ══════════════════════════════════════════════════════════════════════════
# K2 — SLA 達成記錄 (ContractSlaRecord)
# ══════════════════════════════════════════════════════════════════════════

class ContractSlaRecord(Base):
    """
    SLA 達成記錄。
    每個衡量週期結束後，由管理人登錄實際達成值；
    系統自動判斷是否達標並計算達成率趨勢。
    """
    __tablename__ = "contract_sla_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_id = Column(
        Integer,
        ForeignKey("contract_sla_metrics.id", ondelete="CASCADE"),
        nullable=False,
        comment="SLA 指標 ID"
    )
    contract_id = Column(
        String(50),
        nullable=False,
        comment="合約編號（冗餘儲存，方便查詢）"
    )
    period_label = Column(String(20), nullable=False, comment="衡量期間標籤（如：2026-01 或 2026-Q1）")
    period_start = Column(String(10), nullable=False, comment="期間起（YYYY-MM-DD）")
    period_end = Column(String(10), nullable=False, comment="期間迄（YYYY-MM-DD）")
    actual_value = Column(Numeric(10, 4), nullable=False, comment="實際達成值")
    target_value = Column(Numeric(10, 4), nullable=False, comment="當期目標值（快照）")
    achieved = Column(Boolean, nullable=False, default=False, comment="是否達標")
    notes = Column(Text, nullable=True, comment="備註（未達標原因等）")
    recorded_by = Column(String(100), nullable=False, default="", comment="登錄人帳號")
    created_at = Column(DateTime, nullable=False, default=_now)

    metric = relationship("ContractSlaMetric", foreign_keys=[metric_id], lazy="select")

    __table_args__ = (
        Index("idx_sla_record_metric", "metric_id"),
        Index("idx_sla_record_contract", "contract_id"),
        Index("idx_sla_record_period", "period_label"),
    )

    def __repr__(self) -> str:
        return f"<SlaRecord {self.id} metric={self.metric_id} {self.period_label} actual={self.actual_value}>"
