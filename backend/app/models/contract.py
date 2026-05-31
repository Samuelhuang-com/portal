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
