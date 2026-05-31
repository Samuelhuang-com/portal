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


class ContractClaimUpdate(BaseModel):
    claim_type:  Optional[str] = Field(None, max_length=20)
    claim_date:  Optional[str] = None
    invoice_no:  Optional[str] = Field(None, max_length=100)
    amount:      Optional[float] = Field(None, ge=0)
    status:      Optional[str] = Field(None, max_length=20)
    approver:    Optional[str] = Field(None, max_length=100)
    remarks:     Optional[str] = Field(None, max_length=500)


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
