"""
合約管理 Pydantic Schema 驗證模型

使用場景：
  - ContractCreate：新增合約時驗證請求
  - ContractUpdate：編輯合約時驗證請求
  - ContractResponse：API 回應序列化
  - ContractDetailResponse：Drawer 詳細資訊
"""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


# ══════════════════════════════════════════════════════════════════════════
# 1. Contract 相關 Schema
# ══════════════════════════════════════════════════════════════════════════

class ContractBase(BaseModel):
    """合約基礎欄位"""
    contract_name: str = Field(..., min_length=1, max_length=255, description="合約名稱")
    contract_type: str = Field(..., max_length=50, description="合約類型")
    contract_status: Optional[str] = Field("草稿", max_length=50, description="合約狀態")
    responsible_dept: str = Field(..., max_length=100, description="權責部門")
    using_depts: Optional[str] = Field("", description="使用部門（多個時以;分隔）")

    vendor_id: str = Field(..., max_length=50, description="廠商編號")
    vendor_name: Optional[str] = Field("", max_length=255, description="廠商名稱（唯讀）")

    start_date: date = Field(..., description="合約起日")
    end_date: date = Field(..., description="合約迄日")
    notification_days: int = Field(0, ge=0, description="到期前通知天數")
    auto_renewal: bool = Field(False, description="是否自動續約")

    currency: str = Field("TWD", max_length=10, description="幣別")
    total_amount_tax_included: float = Field(..., ge=0, description="合約總金額含稅")
    monthly_fixed_amount: Optional[float] = Field(None, ge=0, description="每月固定金額")
    pricing_method: str = Field(..., max_length=100, description="計價方式")

    needs_purchase_order: bool = Field(False, description="是否需請購單")
    can_claim_without_po: bool = Field(False, description="是否可無請購請款")

    needs_allocation: bool = Field(False, description="是否需分攤")
    allocation_method: Optional[str] = Field(None, max_length=50, description="分攤方式")

    budget_year: int = Field(..., ge=2000, le=2100, description="預算年度")
    budget_category_l1: str = Field(..., max_length=100, description="預算大項")
    budget_category_l2: str = Field(..., max_length=100, description="預算細項")
    accounting_code: str = Field(..., max_length=50, description="會計科目")

    budget_source: str = Field("年度預算", description="預算來源")
    budget_control_method: str = Field("提醒", description="預算控管方式")
    require_acceptance: bool = Field(False, description="是否需驗收")

    risk_level: str = Field("中", max_length=20, description="風險等級")
    manager: Optional[str] = Field("", max_length=100, description="管理人")
    reviewer: Optional[str] = Field("", max_length=100, description="覆核人")

    attachment_url: Optional[str] = Field(None, max_length=500, description="附件連結")
    remarks: Optional[str] = Field("", description="備註")

    @validator("start_date", "end_date", pre=True)
    def parse_date(cls, v):
        """允許字串日期轉換"""
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    @validator("end_date")
    def end_date_after_start(cls, v, values):
        """驗證迄日 ≥ 起日"""
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("合約迄日必須晚於起日")
        return v

    @validator("budget_source")
    def validate_budget_source(cls, v):
        """驗證預算來源"""
        valid = ["年度預算", "追加預算", "專案預算"]
        if v not in valid:
            raise ValueError(f"預算來源必須為：{', '.join(valid)}")
        return v

    @validator("budget_control_method")
    def validate_budget_control(cls, v):
        """驗證預算控管方式"""
        valid = ["提醒", "擋單", "主管覆核"]
        if v not in valid:
            raise ValueError(f"預算控管方式必須為：{', '.join(valid)}")
        return v

    @validator("risk_level")
    def validate_risk_level(cls, v):
        """驗證風險等級"""
        valid = ["低", "中", "高", "關鍵"]
        if v not in valid:
            raise ValueError(f"風險等級必須為：{', '.join(valid)}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "contract_name": "電梯維護保養合約",
                "contract_type": "定額月費",
                "responsible_dept": "工務部",
                "vendor_id": "VND-0001",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "total_amount_tax_included": 720000,
                "monthly_fixed_amount": 60000,
            }
        }


class ContractCreate(ContractBase):
    """新增合約"""
    contract_id: str = Field(..., pattern="^CON-\\d{4}-\\d{4}$", description="合約編號")

    class Config:
        json_schema_extra = {
            "example": {
                "contract_id": "CON-2026-0001",
                "contract_name": "電梯維護保養合約",
                **ContractBase.Config.json_schema_extra["example"]
            }
        }


class ContractUpdate(BaseModel):
    """編輯合約（選擇性欄位）"""
    contract_name: Optional[str] = Field(None, max_length=255)
    contract_type: Optional[str] = Field(None, max_length=50)
    contract_status: Optional[str] = Field(None, max_length=50)
    responsible_dept: Optional[str] = Field(None, max_length=100)
    using_depts: Optional[str] = Field(None)

    vendor_id: Optional[str] = Field(None, max_length=50)

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    notification_days: Optional[int] = Field(None, ge=0)
    auto_renewal: Optional[bool] = None

    currency: Optional[str] = Field(None, max_length=10)
    total_amount_tax_included: Optional[float] = Field(None, ge=0)
    monthly_fixed_amount: Optional[float] = Field(None, ge=0)
    pricing_method: Optional[str] = Field(None, max_length=100)

    needs_purchase_order: Optional[bool] = None
    can_claim_without_po: Optional[bool] = None

    needs_allocation: Optional[bool] = None
    allocation_method: Optional[str] = Field(None, max_length=50)

    budget_year: Optional[int] = Field(None, ge=2000, le=2100)
    budget_category_l1: Optional[str] = Field(None, max_length=100)
    budget_category_l2: Optional[str] = Field(None, max_length=100)
    accounting_code: Optional[str] = Field(None, max_length=50)

    budget_source: Optional[str] = None
    budget_control_method: Optional[str] = None
    require_acceptance: Optional[bool] = None

    risk_level: Optional[str] = Field(None, max_length=20)
    manager: Optional[str] = Field(None, max_length=100)
    reviewer: Optional[str] = Field(None, max_length=100)

    attachment_url: Optional[str] = Field(None, max_length=500)
    remarks: Optional[str] = None

    # F3 — 公司別 / 部門別 / 計價規格
    signing_company: Optional[str] = Field(None, max_length=100)
    signing_dept:    Optional[str] = Field(None, max_length=100)
    budget_company:  Optional[str] = Field(None, max_length=100)
    budget_dept:     Optional[str] = Field(None, max_length=100)
    pricing_spec:    Optional[str] = Field(None, max_length=200)

    @validator("start_date", "end_date", pre=True)
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


class ContractResponse(ContractBase):
    """API 回應"""
    contract_id: str
    created_at: datetime
    updated_at: datetime
    # 審核欄位（nullable，向前兼容）
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approval_comment: Optional[str] = None
    # F3 新欄位
    signing_company: Optional[str] = None
    signing_dept:    Optional[str] = None
    budget_company:  Optional[str] = None
    budget_dept:     Optional[str] = None
    pricing_spec:    Optional[str] = None

    class Config:
        from_attributes = True


class ContractDetailResponse(ContractResponse):
    """Drawer 詳細資訊回應"""
    detail: dict = Field(default={}, description="Drawer 用 detail dict")

    @validator('detail', pre=True, always=True)
    @classmethod
    def parse_detail_str(cls, v):
        """DB 裡 detail 存 JSON 字串，from_orm 時自動轉 dict。"""
        import json as _json
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return {}
        return v or {}


class ContractApprovalRequest(BaseModel):
    """合約審核操作請求（approve / reject）"""
    comment: Optional[str] = Field(None, max_length=500, description="審核意見")


# ══════════════════════════════════════════════════════════════════════════
# 2. ContractItem 相關 Schema
# ══════════════════════════════════════════════════════════════════════════

class ContractItemBase(BaseModel):
    """合約明細基礎欄位"""
    item_name: str = Field(..., min_length=1, max_length=255, description="項目名稱")
    item_category: str = Field(..., max_length=50, description="項目類別")
    unit_price_tax_excluded: Optional[float] = Field(None, ge=0)
    quantity: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    tax_rate: float = Field(5, ge=0, le=100, description="稅率（%）")
    amount_tax_excluded: float = Field(..., ge=0)
    amount_tax_included: float = Field(..., ge=0)
    is_fixed: bool = Field(True)
    is_floating: bool = Field(False)


class ContractItemCreate(ContractItemBase):
    """新增合約明細"""
    item_seq: int = Field(1, ge=1)


class ContractItemResponse(ContractItemBase):
    """合約明細回應"""
    id: int
    contract_id: str
    item_seq: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# 3. Vendor 相關 Schema
# ══════════════════════════════════════════════════════════════════════════

class VendorBase(BaseModel):
    """廠商基礎欄位"""
    vendor_name: str = Field(..., min_length=1, max_length=255, description="廠商名稱")
    tax_id: str = Field(..., max_length=20, description="統一編號")
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    payment_terms: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=50)
    vendor_type: Optional[str] = Field(None, max_length=50)
    risk_level: Optional[str] = Field(None, max_length=20)
    is_critical: bool = Field(False)
    managing_company: Optional[str] = Field(None, max_length=100)  # F7


class VendorCreate(VendorBase):
    """新增廠商"""
    vendor_id: str = Field(..., pattern="^VND-\\d{4}$", description="廠商編號")


class VendorUpdate(BaseModel):
    """編輯廠商"""
    vendor_name: Optional[str] = Field(None, max_length=255)
    tax_id: Optional[str] = Field(None, max_length=20)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    payment_terms: Optional[str] = Field(None, max_length=100)
    bank_name: Optional[str] = Field(None, max_length=100)
    bank_account: Optional[str] = Field(None, max_length=50)
    vendor_type: Optional[str] = Field(None, max_length=50)
    risk_level: Optional[str] = Field(None, max_length=20)
    is_critical: Optional[bool] = None
    managing_company: Optional[str] = Field(None, max_length=100)  # F7


class VendorResponse(VendorBase):
    """廠商回應"""
    vendor_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# 4. BudgetCategory 相關 Schema
# ══════════════════════════════════════════════════════════════════════════

class BudgetCategoryBase(BaseModel):
    """預算科目基礎欄位"""
    budget_year: int = Field(..., ge=2000, le=2100)
    dept: str = Field(..., max_length=100)
    category_l1: str = Field(..., max_length=100)
    category_l2: str = Field(..., max_length=100)
    accounting_code: str = Field(..., max_length=50)
    payment_code: Optional[str] = Field(None, max_length=50)
    is_enabled: bool = Field(True)
    effective_date: date = Field(...)
    disabled_date: Optional[date] = None
    maintain_unit: str = Field(..., max_length=100)


class BudgetCategoryCreate(BudgetCategoryBase):
    """新增預算科目"""
    pass


class BudgetCategoryResponse(BudgetCategoryBase):
    """預算科目回應"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# 5. 其他 Schema
# ══════════════════════════════════════════════════════════════════════════

class VendorListResponse(BaseModel):
    """廠商下拉選項"""
    vendor_id: str
    vendor_name: str


class BudgetCategoryListResponse(BaseModel):
    """科目下拉選項"""
    id: int
    budget_year: int
    category_l1: str
    category_l2: str
    accounting_code: str


class ContractListRequest(BaseModel):
    """列表查詢參數"""
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)
    search: Optional[str] = None
    status: Optional[str] = None
    risk_level: Optional[str] = None
    budget_year: Optional[int] = None
    dept: Optional[str] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$")


class ContractListResponse(BaseModel):
    """列表回應"""
    total: int
    page: int
    size: int
    items: List[ContractResponse]


# ── 廠商分頁清單（GET /vendors） ─────────────────────────────────────────
class VendorPagedResponse(BaseModel):
    """廠商分頁回應"""
    total: int
    items: List[VendorResponse]


class VendorImportRowError(BaseModel):
    """單列匯入錯誤"""
    row: int
    vendor_id: str
    message: str


class VendorImportResult(BaseModel):
    """廠商 Excel 批次匯入結果"""
    total_rows: int
    created: int
    updated: int
    skipped: int
    errors: List[VendorImportRowError]


# ── 預算科目分頁清單（GET /budget-categories） ───────────────────────────
class BudgetCategoryPagedResponse(BaseModel):
    """預算科目分頁回應"""
    total: int
    items: List[BudgetCategoryResponse]


# ── 預算科目更新 ────────────────────────────────────────────────────────
class BudgetCategoryUpdate(BaseModel):
    """編輯預算科目（選擇性欄位）"""
    dept: Optional[str] = Field(None, max_length=100)
    category_l1: Optional[str] = Field(None, max_length=100)
    category_l2: Optional[str] = Field(None, max_length=100)
    accounting_code: Optional[str] = Field(None, max_length=50)
    payment_code: Optional[str] = Field(None, max_length=50)
    is_enabled: Optional[bool] = None
    effective_date: Optional[date] = None
    disabled_date: Optional[date] = None
    maintain_unit: Optional[str] = Field(None, max_length=100)


# ── 合約統計（GET /stats） ──────────────────────────────────────────────
class ContractStatsResponse(BaseModel):
    """合約統計回應"""
    total: int
    by_status: Dict[str, int]
    by_risk_level: Dict[str, int]


# ── Dashboard KPI（GET /dashboard/kpi） ─────────────────────────────────
class DashboardKPIResponse(BaseModel):
    """Dashboard KPI 指標"""
    active_contracts: int
    total_annual_amount: float
    high_risk_count: int
    expiring_in_90days: int
    monthly_claim_amount: float  # Phase 3，暫回 0
    accrual_amount: float        # Phase 3，暫回 0
    budget_year: int


# ── Dashboard by-dept（GET /dashboard/by-dept） ─────────────────────────
class DashboardByDeptItem(BaseModel):
    dept: str
    amount: float
    count: int


class DashboardByDeptResponse(BaseModel):
    """Dashboard 部門金額分組"""
    budget_year: int
    items: List[DashboardByDeptItem]


# ══════════════════════════════════════════════════════════════════════════
# 5. ContractClaim 請款 / 核銷記錄
# ══════════════════════════════════════════════════════════════════════════

class ContractClaimCreate(BaseModel):
    contract_id: str = Field(..., max_length=50)
    claim_type:  str = Field("請款", max_length=20)
    claim_date:  str = Field(..., description="YYYY-MM-DD")
    invoice_no:  Optional[str] = Field(None, max_length=100)
    amount:      float = Field(..., ge=0)
    status:      Optional[str] = Field("待審核", max_length=20)
    approver:    Optional[str] = Field(None, max_length=100)
    remarks:     Optional[str] = Field(None, max_length=500)
    cost_company: Optional[str] = Field(None, max_length=100)  # F6


class ContractClaimUpdate(BaseModel):
    claim_type:  Optional[str] = Field(None, max_length=20)
    claim_date:  Optional[str] = None
    invoice_no:  Optional[str] = Field(None, max_length=100)
    amount:      Optional[float] = Field(None, ge=0)
    status:      Optional[str] = Field(None, max_length=20)
    approver:    Optional[str] = Field(None, max_length=100)
    remarks:     Optional[str] = Field(None, max_length=500)
    cost_company: Optional[str] = Field(None, max_length=100)  # F6


class ContractClaimResponse(BaseModel):
    id:            int
    contract_id:   str
    contract_name: Optional[str] = None   # JOIN 補充，不在 ORM model 上
    claim_type:    str
    claim_date:    str
    invoice_no:    Optional[str]
    amount:        float
    status:        str
    approver:      Optional[str]
    remarks:       Optional[str]
    review_log:    Optional[str] = None   # JSON string，前端自行 JSON.parse
    created_at:    datetime
    updated_at:    datetime
    cost_company:  Optional[str] = None  # F6

    class Config:
        from_attributes = True


class ContractClaimReviewRequest(BaseModel):
    """請款審核動作請求"""
    action:   str            = Field(..., description="approve / reject / mark_paid / resubmit")
    comment:  Optional[str]  = Field(None, max_length=500)
    approver: Optional[str]  = Field(None, max_length=100)


class ContractClaimBatchReviewRequest(BaseModel):
    """批次請款審核"""
    claim_ids: List[int]     = Field(..., min_length=1, description="請款 ID 清單")
    action:    str           = Field(..., description="approve / reject")
    comment:   Optional[str] = Field(None, max_length=500)
    approver:  Optional[str] = Field(None, max_length=100)


# ══════════════════════════════════════════════════════════════════════════
# 6. ContractItem 合約項目明細
# ══════════════════════════════════════════════════════════════════════════

class ContractItemCreate(BaseModel):
    item_name:                str     = Field(..., max_length=255)
    item_category:            str     = Field("",  max_length=50)
    item_seq:                 Optional[int]   = None
    unit_price_tax_excluded:  Optional[float] = None
    quantity:                 Optional[float] = None
    unit:                     Optional[str]   = Field(None, max_length=20)
    tax_rate:                 float   = Field(5, ge=0, le=100)
    amount_tax_excluded:      float   = Field(0, ge=0)
    amount_tax_included:      float   = Field(0, ge=0)
    is_fixed:                 bool    = True
    is_floating:              bool    = False


class ContractItemUpdate(BaseModel):
    item_name:                Optional[str]   = Field(None, max_length=255)
    item_category:            Optional[str]   = Field(None, max_length=50)
    item_seq:                 Optional[int]   = None
    unit_price_tax_excluded:  Optional[float] = None
    quantity:                 Optional[float] = None
    unit:                     Optional[str]   = Field(None, max_length=20)
    tax_rate:                 Optional[float] = Field(None, ge=0, le=100)
    amount_tax_excluded:      Optional[float] = Field(None, ge=0)
    amount_tax_included:      Optional[float] = Field(None, ge=0)
    is_fixed:                 Optional[bool]  = None
    is_floating:              Optional[bool]  = None


class ContractItemResponse(BaseModel):
    id:                       int
    contract_id:              str
    item_seq:                 int
    item_name:                str
    item_category:            str
    unit_price_tax_excluded:  Optional[float]
    quantity:                 Optional[float]
    unit:                     Optional[str]
    tax_rate:                 float
    amount_tax_excluded:      float
    amount_tax_included:      float
    is_fixed:                 bool
    is_floating:              bool
    created_at:               datetime
    updated_at:               datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# 合約續約 Schemas
# ══════════════════════════════════════════════════════════════════════════

class RenewalCreate(BaseModel):
    """申請續約"""
    renewal_start_date: str   = Field(..., description="續約起日 YYYY-MM-DD")
    renewal_end_date:   str   = Field(..., description="續約迄日 YYYY-MM-DD")
    new_amount:         Optional[float] = Field(None, ge=0, description="續約金額（含稅）；不填表示同原合約")
    renewal_reason:     str   = Field(..., min_length=1, max_length=2000, description="續約原因")
    remarks:            Optional[str]   = Field(None, max_length=500)
    applicant_dept:     Optional[str]   = Field(None, max_length=100)


class RenewalReview(BaseModel):
    """審核 / 拒絕 / 撤回"""
    action:         str = Field(..., description="操作（approve/reject/withdraw）")
    review_comment: Optional[str] = Field(None, max_length=500, description="審核意見")


class RenewalResponse(BaseModel):
    id:                 int
    contract_id:        str
    renewal_start_date: str
    renewal_end_date:   str
    new_amount:         Optional[float]
    renewal_reason:     str
    remarks:            Optional[str]
    applicant:          str
    applicant_dept:     Optional[str]
    status:             str
    reviewer:           Optional[str]
    reviewed_at:        Optional[datetime]
    review_comment:     Optional[str]
    review_log:         str
    created_at:         datetime
    updated_at:         datetime

    class Config:
        from_attributes = True


# ── F3 費用分攤 Schema ────────────────────────────────────────────────────────

class CostAllocationItem(BaseModel):
    """單筆費用分攤（建立/更新用）"""
    company_name:    str   = Field(..., min_length=1, max_length=100, description="分攤公司名稱")
    allocation_type: str   = Field("percentage", description="percentage 或 fixed")
    value:           float = Field(..., ge=0, description="比例（0~100）或固定金額（≥0）")

    @validator("allocation_type")
    @classmethod
    def check_type(cls, v):
        if v not in ("percentage", "fixed"):
            raise ValueError("allocation_type 必須為 percentage 或 fixed")
        return v


class CostAllocationResponse(BaseModel):
    """單筆費用分攤回應"""
    id:              int
    contract_id:     str
    company_name:    str
    allocation_type: str
    value:           float
    created_at:      datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# H1 — 合約範本 Schema
# ══════════════════════════════════════════════════════════════════════════

class ContractTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="範本名稱")
    contract_type: str = Field(..., max_length=50, description="合約類型")
    description: Optional[str] = Field(None, description="範本說明")
    default_currency: str = Field("TWD", max_length=10)
    default_notification_days: int = Field(30, ge=0)
    default_auto_renewal: bool = Field(False)
    default_needs_purchase_order: bool = Field(False)
    default_require_acceptance: bool = Field(False)
    default_risk_level: str = Field("中", max_length=20)
    default_pricing_method: str = Field("", max_length=100)
    default_budget_source: str = Field("年度預算", max_length=50)
    default_remarks: Optional[str] = Field(None)
    is_enabled: bool = Field(True)


class ContractTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    contract_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    default_currency: Optional[str] = Field(None, max_length=10)
    default_notification_days: Optional[int] = Field(None, ge=0)
    default_auto_renewal: Optional[bool] = None
    default_needs_purchase_order: Optional[bool] = None
    default_require_acceptance: Optional[bool] = None
    default_risk_level: Optional[str] = Field(None, max_length=20)
    default_pricing_method: Optional[str] = Field(None, max_length=100)
    default_budget_source: Optional[str] = Field(None, max_length=50)
    default_remarks: Optional[str] = None
    is_enabled: Optional[bool] = None


class ContractTemplateResponse(BaseModel):
    id: int
    name: str
    contract_type: str
    description: Optional[str]
    default_currency: str
    default_notification_days: int
    default_auto_renewal: bool
    default_needs_purchase_order: bool
    default_require_acceptance: bool
    default_risk_level: str
    default_pricing_method: str
    default_budget_source: str
    default_remarks: Optional[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# H2 — 合約變更歷程 Schema
# ══════════════════════════════════════════════════════════════════════════

class ContractChangeLogResponse(BaseModel):
    id: int
    contract_id: str
    field_name: str
    field_label: str
    old_value: Optional[str]
    new_value: Optional[str]
    operator: str
    operated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# H3 — 分期付款計劃 Schema
# ══════════════════════════════════════════════════════════════════════════

class PaymentScheduleCreate(BaseModel):
    milestone_name: str = Field(..., min_length=1, max_length=200, description="里程碑名稱")
    due_date: str = Field(..., description="應付日期（YYYY-MM-DD）")
    amount: float = Field(..., ge=0, description="應付金額（含稅）")
    notes: Optional[str] = Field(None, description="備註")


class PaymentScheduleUpdate(BaseModel):
    milestone_name: Optional[str] = Field(None, min_length=1, max_length=200)
    due_date: Optional[str] = None
    amount: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, description="狀態（待付款/已付款/逾期/取消）")
    paid_date: Optional[str] = Field(None, description="實際付款日期（YYYY-MM-DD）")
    notes: Optional[str] = None


class PaymentScheduleResponse(BaseModel):
    id: int
    contract_id: str
    milestone_name: str
    due_date: str
    amount: float
    status: str
    paid_date: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# H4 — 操作稽核日誌 Schema
# ══════════════════════════════════════════════════════════════════════════

class ContractAuditLogResponse(BaseModel):
    id: int
    contract_id: Optional[str]
    action: str
    resource: str
    resource_id: Optional[str]
    operator: str
    payload_summary: Optional[str]
    result: str
    error_detail: Optional[str]
    operated_at: datetime
    ip_address: Optional[str]

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# I1 — 多層審核關卡 Schema
# ══════════════════════════════════════════════════════════════════════════

class ApprovalStageResponse(BaseModel):
    id: int
    contract_id: str
    submission_round: int
    stage_order: int
    stage_name: str
    assigned_to: Optional[str]
    status: str
    reviewer: Optional[str]
    comment: Optional[str]
    reviewed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalConfigCreate(BaseModel):
    contract_type: str = Field(..., max_length=50, description="合約類型（'*' 表示全部類型預設）")
    stage_order: int = Field(..., ge=1, le=10)
    stage_name: str = Field(..., min_length=1, max_length=50)
    assigned_to: Optional[str] = Field(None, max_length=100)
    is_enabled: bool = Field(True)


class ApprovalConfigUpdate(BaseModel):
    stage_name: Optional[str] = Field(None, min_length=1, max_length=50)
    assigned_to: Optional[str] = Field(None, max_length=100)
    is_enabled: Optional[bool] = None


class ApprovalConfigResponse(BaseModel):
    id: int
    contract_type: str
    stage_order: int
    stage_name: str
    assigned_to: Optional[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StageReviewRequest(BaseModel):
    comment: Optional[str] = Field(None, description="審核意見（選填）")


# ══════════════════════════════════════════════════════════════════════════
# I2 — 驗收記錄 Schema
# ══════════════════════════════════════════════════════════════════════════

class AcceptanceCreate(BaseModel):
    acceptance_name: str = Field(..., min_length=1, max_length=200, description="驗收項目名稱")
    acceptance_date: str = Field(..., description="驗收日期（YYYY-MM-DD）")
    accepted_by: str = Field(..., max_length=100, description="驗收人帳號")
    status: str = Field("待驗收", description="驗收狀態（待驗收/已驗收/驗收失敗）")
    period_start: Optional[str] = Field(None, description="服務期間起（YYYY-MM-DD）")
    period_end: Optional[str] = Field(None, description="服務期間迄（YYYY-MM-DD）")
    notes: Optional[str] = None


class AcceptanceUpdate(BaseModel):
    acceptance_name: Optional[str] = Field(None, min_length=1, max_length=200)
    acceptance_date: Optional[str] = None
    accepted_by: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    notes: Optional[str] = None


class AcceptanceResponse(BaseModel):
    id: int
    contract_id: str
    acceptance_name: str
    acceptance_date: str
    accepted_by: str
    status: str
    period_start: Optional[str]
    period_end: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# I3 — 保證金追蹤 Schema
# ══════════════════════════════════════════════════════════════════════════

class DepositCreate(BaseModel):
    deposit_type: str = Field("履約保證金", max_length=50, description="保證金類型")
    deposit_amount: float = Field(..., ge=0, description="保證金金額")
    deposit_date: str = Field(..., description="存入日期（YYYY-MM-DD）")
    expected_return_date: str = Field(..., description="預計退還日（YYYY-MM-DD）")
    bank_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class DepositUpdate(BaseModel):
    deposit_type: Optional[str] = Field(None, max_length=50)
    deposit_amount: Optional[float] = Field(None, ge=0)
    deposit_date: Optional[str] = None
    expected_return_date: Optional[str] = None
    actual_return_date: Optional[str] = None
    status: Optional[str] = Field(None, description="狀態（保留中/申請退還/已退還/已沒收）")
    bank_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class DepositResponse(BaseModel):
    id: int
    contract_id: str
    deposit_type: str
    deposit_amount: float
    deposit_date: str
    expected_return_date: str
    actual_return_date: Optional[str]
    status: str
    bank_name: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════════════
# I4 — 年化費用計算 Schema
# ══════════════════════════════════════════════════════════════════════════

class CostSummaryResponse(BaseModel):
    contract_id: str
    contract_name: str
    total_amount: float
    monthly_fixed_amount: Optional[float]
    annual_amount: Optional[float]        # monthly_fixed_amount * 12（月費類型）
    monthly_amortization: Optional[float] # total_amount / duration_months
    duration_days: int
    duration_months: float
    claimed_total: float                  # 所有狀態請款加總
    approved_total: float                 # 已核准+已付款
    claimed_percentage: float             # approved_total / total_amount * 100
    remaining_amount: float               # total_amount - approved_total
    is_monthly_contract: bool             # True = 月費合約（有 monthly_fixed_amount）


# ══════════════════════════════════════════════════════════════════════════
# K2 — SLA 追蹤 Schema
# ══════════════════════════════════════════════════════════════════════════

class SlaMetricCreate(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=100)
    metric_type: str = Field("自訂", max_length=50,
                             description="可用率/回應時間/解決時間/自訂")
    target_value: float = Field(..., description="目標值")
    target_unit: str = Field("%", max_length=20, description="單位（%/小時/天/次）")
    measurement_period: str = Field("monthly",
                                    description="衡量週期（monthly/quarterly/annual）")
    description: Optional[str] = None
    is_enabled: bool = True


class SlaMetricUpdate(BaseModel):
    metric_name: Optional[str] = Field(None, min_length=1, max_length=100)
    metric_type: Optional[str] = Field(None, max_length=50)
    target_value: Optional[float] = None
    target_unit: Optional[str] = Field(None, max_length=20)
    measurement_period: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class SlaMetricResponse(BaseModel):
    id: int
    contract_id: str
    metric_name: str
    metric_type: str
    target_value: float
    target_unit: str
    measurement_period: str
    description: Optional[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SlaRecordCreate(BaseModel):
    metric_id: int
    period_label: str = Field(..., description="期間標籤，如 2026-01 或 2026-Q1")
    period_start: str = Field(..., description="期間起（YYYY-MM-DD）")
    period_end: str = Field(..., description="期間迄（YYYY-MM-DD）")
    actual_value: float = Field(..., description="實際達成值")
    notes: Optional[str] = None


class SlaRecordResponse(BaseModel):
    id: int
    metric_id: int
    contract_id: str
    period_label: str
    period_start: str
    period_end: str
    actual_value: float
    target_value: float
    achieved: bool
    notes: Optional[str]
    recorded_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class SlaSummaryResponse(BaseModel):
    contract_id: str
    metrics: List[dict]   # 每個指標的達成率統計
    overall_achievement_rate: float  # 所有指標所有期間的平均達成率
