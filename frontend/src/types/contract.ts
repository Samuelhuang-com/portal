// ── 合約管理 TypeScript 型別定義 ─────────────────────────────────────────────────

export interface ContractRecord {
  contract_id: string
  contract_name: string
  contract_type: string
  contract_status: string
  responsible_dept: string
  using_depts: string
  vendor_id: string
  vendor_name: string
  start_date: string
  end_date: string
  notification_days: number
  auto_renewal: boolean
  currency: string
  total_amount_tax_included: number
  monthly_fixed_amount?: number
  pricing_method: string
  needs_purchase_order: boolean
  can_claim_without_po: boolean
  needs_allocation: boolean
  allocation_method?: string
  budget_year: number
  budget_category_l1: string
  budget_category_l2: string
  accounting_code: string
  budget_source: string
  budget_control_method: string
  require_acceptance: boolean
  risk_level: string
  manager: string
  reviewer: string
  attachment_url?: string
  remarks: string
  created_at: string
  updated_at: string
  detail: Record<string, string>
  ragic_id?: string
  ragic_url?: string
  // F3 新欄位
  signing_company?: string
  signing_dept?: string
  budget_company?: string
  budget_dept?: string
  pricing_spec?: string
  approved_by?: string
  approved_at?: string
  approval_comment?: string
  // 續約鏈（2026-07-21；2026-07-22 擴充編號規律推斷）
  renewed_from_contract_id?: string   // 明確 FK 關聯（只有走複製續約流程才會有值）
  is_renewal_copy?: boolean           // 是否為複製續約產生（FK 關聯 或 編號規律推斷）
  has_renewal_children?: boolean      // 是否已被複製續約過（FK 關聯 或 編號規律推斷）
  renewal_related_hint?: string       // 提示用的相關合約編號
}

// ── 原合約複製續約 + 上下層級查詢（2026-07-21）──────────────────────────────

export interface ContractChainNode {
  contract_id: string
  contract_name: string
  contract_status: string
  start_date: string
  end_date: string
  total_amount_tax_included: number
  renewed_from_contract_id?: string | null
  is_current: boolean
}

export interface VendorRecord {
  vendor_id: string
  vendor_name: string
  tax_id: string
  contact_person?: string
  phone?: string
  email?: string
  address?: string
  payment_terms?: string
  bank_name?: string
  bank_account?: string
  vendor_type?: string
  risk_level?: string
  is_critical: boolean
  managing_company?: string  // F7
  created_at: string
  updated_at: string
}

export interface BudgetCategoryRecord {
  id: number
  budget_year: number
  dept: string
  category_l1: string
  category_l2: string
  accounting_code: string
  payment_code?: string
  is_enabled: boolean
  effective_date: string
  disabled_date?: string
  maintain_unit: string
  created_at: string
  updated_at: string
}

export interface ContractListResponse {
  total: number
  page: number
  size: number
  items: ContractRecord[]
}

export interface VendorListResponse {
  vendor_id: string
  vendor_name: string
}

export interface BudgetCategoryListResponse {
  id: number
  budget_year: number
  category_l1: string
  category_l2: string
  accounting_code: string
}

export interface ContractCreate {
  contract_id: string
  contract_name: string
  contract_type: string
  responsible_dept: string
  vendor_id: string
  start_date: string
  end_date: string
  total_amount_tax_included: number
  pricing_method: string
  budget_year: number
  budget_category_l1: string
  budget_category_l2: string
  accounting_code: string
  [key: string]: any
}

export interface ContractUpdate {
  contract_name?: string
  contract_type?: string
  contract_status?: string
  total_amount_tax_included?: number
  [key: string]: any
}

export interface VendorCreate {
  vendor_id: string
  vendor_name: string
  tax_id: string
  [key: string]: any
}

export interface VendorUpdate {
  vendor_name?: string
  tax_id?: string
  [key: string]: any
}

export interface ContractFilters {
  page?: number
  size?: number
  search?: string
  status?: string
  risk_level?: string
  budget_year?: number
  dept?: string
  manager?: string          // J5 個人化篩選
  renewal_filter?: 'is_copy' | 'has_copies'   // 2026-07-21：續約鏈篩選
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

// ── J1 — 廠商集中度 ───────────────────────────────────────────────────────────

export interface VendorConcentrationItem {
  vendor_id: string
  vendor_name: string
  contract_count: number
  total_amount: number
  percentage: number
  is_high_concentration: boolean
}

export interface VendorConcentrationResponse {
  budget_year?: number
  threshold: number
  grand_total: number
  vendor_count: number
  high_concentration_count: number
  items: VendorConcentrationItem[]
}

// ── J2 — 成本趨勢 ─────────────────────────────────────────────────────────────

export interface CostTrendPoint {
  period: string
  label: string
  contract_amount: number
  claimed_amount: number
}

export interface CostTrendResponse {
  budget_year: number
  granularity: string
  company?: string
  dept?: string
  data: CostTrendPoint[]
}

// ── J3 — 月度/季度報表 ────────────────────────────────────────────────────────

export interface SummaryReportRow {
  period: string
  label: string
  new_contracts: number
  new_amount: number
  claim_count: number
  claim_amount: number
  approved_amount: number
}

export interface SummaryReportResponse {
  budget_year: number
  period_type: string
  rows: SummaryReportRow[]
  totals: {
    new_contracts: number
    new_amount: number
    claim_count: number
    claim_amount: number
    approved_amount: number
  }
}

export interface VendorFilters {
  page?: number
  size?: number
  search?: string
  [key: string]: any
}

export interface BudgetAnalysisRecord {
  category_l1: string
  category_l2: string
  accounting_code: string
  contract_count: number
  total_claimed: number
  paid_amount: number
  approved_amount: number
  pending_amount: number
}

export interface RenewalRecord {
  id: number
  contract_id: string
  renewal_start_date: string
  renewal_end_date: string
  new_amount: number | null
  renewal_reason: string
  remarks: string | null
  applicant: string
  applicant_dept: string | null
  status: string
  reviewer: string | null
  reviewed_at: string | null
  review_comment: string | null
  review_log: string
  created_at: string
  updated_at: string
}

export interface RenewalListResponse {
  total: number
  page: number
  size: number
  items: RenewalRecord[]
}

export interface VendorPerformance {
  vendor_id: string
  vendor_name: string
  total_claims: number
  approved_count: number
  rejected_count: number
  paid_count: number
  pending_count: number
  ontime_rate: number | null
  dispute_rate: number | null
  avg_process_days: number | null
  grade: 'A' | 'B' | 'C' | 'D' | null
  total_amount: number
  approved_amount: number
  paid_amount: number
  contract_count: number
}

export interface ClaimAttachment {
  id: number
  claim_id: number
  original_filename: string
  content_type: string
  file_size: number
  uploader: string
  created_at: string
  download_url: string
}

export interface ContractAttachment {
  id: number
  contract_id: string
  original_filename: string
  content_type: string
  file_size: number
  uploader: string
  created_at: string
  download_url: string
}

// ── H1 — 合約範本 ─────────────────────────────────────────────────────────────

export interface ContractTemplate {
  id: number
  name: string
  contract_type: string
  description?: string
  default_currency: string
  default_notification_days: number
  default_auto_renewal: boolean
  default_needs_purchase_order: boolean
  default_require_acceptance: boolean
  default_risk_level: string
  default_pricing_method: string
  default_budget_source: string
  default_remarks?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface ContractTemplateCreate {
  name: string
  contract_type: string
  description?: string
  default_currency?: string
  default_notification_days?: number
  default_auto_renewal?: boolean
  default_needs_purchase_order?: boolean
  default_require_acceptance?: boolean
  default_risk_level?: string
  default_pricing_method?: string
  default_budget_source?: string
  default_remarks?: string
  is_enabled?: boolean
}

// ── H2 — 合約變更歷程 ─────────────────────────────────────────────────────────

export interface ContractChangeLog {
  id: number
  contract_id: string
  field_name: string
  field_label: string
  old_value?: string
  new_value?: string
  operator: string
  operated_at: string
}

// ── H3 — 分期付款計劃 ─────────────────────────────────────────────────────────

export interface PaymentSchedule {
  id: number
  contract_id: string
  milestone_name: string
  due_date: string
  amount: number
  status: string
  paid_date?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface PaymentScheduleCreate {
  milestone_name: string
  due_date: string
  amount: number
  notes?: string
}

// ── I1 — 多層審核關卡 ─────────────────────────────────────────────────────────

export interface ApprovalStage {
  id: number
  contract_id: string
  submission_round: number
  stage_order: number
  stage_name: string
  assigned_to?: string
  status: string   // 待審核 / 已核准 / 已拒絕 / 已取消
  reviewer?: string
  comment?: string
  reviewed_at?: string
  created_at: string
}

export interface ApprovalConfig {
  id: number
  contract_type: string
  stage_order: number
  stage_name: string
  assigned_to?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface ApprovalConfigCreate {
  contract_type: string
  stage_order: number
  stage_name: string
  assigned_to?: string
  is_enabled?: boolean
}

// ── I2 — 驗收記錄 ─────────────────────────────────────────────────────────────

export interface Acceptance {
  id: number
  contract_id: string
  acceptance_name: string
  acceptance_date: string
  accepted_by: string
  status: string   // 待驗收 / 已驗收 / 驗收失敗
  period_start?: string
  period_end?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface AcceptanceCreate {
  acceptance_name: string
  acceptance_date: string
  accepted_by: string
  status?: string
  period_start?: string
  period_end?: string
  notes?: string
}

// ── I3 — 保證金追蹤 ─────────────────────────────────────────────────────────

export interface Deposit {
  id: number
  contract_id: string
  deposit_type: string
  deposit_amount: number
  deposit_date: string
  expected_return_date: string
  actual_return_date?: string
  status: string   // 保留中 / 申請退還 / 已退還 / 已沒收
  bank_name?: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface DepositCreate {
  deposit_type?: string
  deposit_amount: number
  deposit_date: string
  expected_return_date: string
  bank_name?: string
  notes?: string
}

// ── I4 — 年化費用摘要 ─────────────────────────────────────────────────────────

export interface CostSummary {
  contract_id: string
  contract_name: string
  total_amount: number
  monthly_fixed_amount?: number
  annual_amount?: number
  monthly_amortization?: number
  duration_days: number
  duration_months: number
  claimed_total: number
  approved_total: number
  claimed_percentage: number
  remaining_amount: number
  is_monthly_contract: boolean
}

// ── H4 — 操作稽核日誌 ─────────────────────────────────────────────────────────

export interface ContractAuditLog {
  id: number
  contract_id?: string
  action: string
  resource: string
  resource_id?: string
  operator: string
  payload_summary?: string
  result: string
  error_detail?: string
  operated_at: string
  ip_address?: string
}

// ── K2 — SLA 追蹤 ─────────────────────────────────────────────────────────────

export interface SlaMetric {
  id: number
  contract_id: string
  metric_name: string
  metric_type: string
  target_value: number
  target_unit: string
  measurement_period: string
  description?: string
  is_enabled: boolean
  created_at: string
  updated_at: string
}

export interface SlaMetricCreate {
  metric_name: string
  metric_type?: string
  target_value: number
  target_unit?: string
  measurement_period?: string
  description?: string
  is_enabled?: boolean
}

export interface SlaRecord {
  id: number
  metric_id: number
  contract_id: string
  period_label: string
  period_start: string
  period_end: string
  actual_value: number
  target_value: number
  achieved: boolean
  notes?: string
  recorded_by: string
  created_at: string
}

export interface SlaRecordCreate {
  metric_id: number
  period_label: string
  period_start: string
  period_end: string
  actual_value: number
  notes?: string
}

export interface SlaTrendPoint {
  period: string
  actual: number
  target: number
  achieved: boolean
}

export interface SlaMetricSummary {
  metric_id: number
  metric_name: string
  metric_type: string
  target_value: number
  target_unit: string
  measurement_period: string
  record_count: number
  achieved_count: number
  achievement_rate?: number
  trend: SlaTrendPoint[]
}

export interface SlaSummary {
  contract_id: string
  metrics: SlaMetricSummary[]
  overall_achievement_rate?: number
}
