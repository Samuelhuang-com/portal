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
  sort_by?: string
  sort_order?: 'asc' | 'desc'
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
