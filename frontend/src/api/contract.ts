/**
 * 合約管理 API functions
 * 對應後端 /api/v1/contract/*
 */
import apiClient from './client'
import type {
  ContractRecord,
  ContractListResponse,
  VendorConcentrationResponse,
  CostTrendResponse,
  SummaryReportResponse,
  SlaMetric,
  SlaMetricCreate,
  SlaRecord,
  SlaRecordCreate,
  SlaSummary,
  VendorRecord,
  VendorListResponse,
  BudgetCategoryRecord,
  BudgetCategoryListResponse,
  ContractCreate,
  ContractUpdate,
  VendorCreate,
  VendorUpdate,
  ContractFilters,
  VendorFilters,
  BudgetAnalysisRecord,
  RenewalRecord,
  RenewalListResponse,
  ContractTemplate,
  ContractTemplateCreate,
  ContractChangeLog,
  PaymentSchedule,
  PaymentScheduleCreate,
  ContractAuditLog,
  ApprovalStage,
  ApprovalConfig,
  ApprovalConfigCreate,
  Acceptance,
  AcceptanceCreate,
  Deposit,
  DepositCreate,
  CostSummary,
} from '@/types/contract'

const BASE = '/contract'

// ── 合約端點 ──────────────────────────────────────────────────────────────────

/** 取得合約清單（含分頁 & 篩選） */
export async function fetchContracts(
  filters: ContractFilters = {},
): Promise<ContractListResponse> {
  const { data } = await apiClient.get<ContractListResponse>(BASE, {
    params: filters,
  })
  return data
}

/** 取得單筆合約詳情 */
export async function fetchContract(contractId: string): Promise<{
  success: boolean
  data: ContractRecord
}> {
  const { data } = await apiClient.get(`${BASE}/${contractId}`)
  return data
}

/** 新增合約 */
export async function createContract(
  payload: ContractCreate,
): Promise<{ success: boolean; data: ContractRecord }> {
  const { data } = await apiClient.post(BASE, payload)
  return data
}

/** 更新合約 */
export async function updateContract(
  contractId: string,
  payload: ContractUpdate,
): Promise<ContractRecord> {
  const { data } = await apiClient.put(`${BASE}/${contractId}`, payload)
  return data
}

/** 刪除合約 */
export async function deleteContract(contractId: string): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete(`${BASE}/${contractId}`)
  return data
}

/** 送審（草稿 → 審核中） */
export async function submitContractForReview(contractId: string): Promise<ContractRecord> {
  const { data } = await apiClient.post(`${BASE}/${contractId}/submit`)
  return data
}

/** 核准合約（審核中 → 生效中） */
export async function approveContract(contractId: string, comment?: string): Promise<ContractRecord> {
  const { data } = await apiClient.post(`${BASE}/${contractId}/approve`, { comment })
  return data
}

/** 拒絕合約（審核中 → 草稿） */
export async function rejectContract(contractId: string, comment?: string): Promise<ContractRecord> {
  const { data } = await apiClient.post(`${BASE}/${contractId}/reject`, { comment })
  return data
}

// ── 廠商端點 ──────────────────────────────────────────────────────────────────

/** 取得廠商清單 */
export async function fetchVendors(
  filters: VendorFilters = {},
): Promise<{ total: number; items: VendorRecord[] }> {
  const { data } = await apiClient.get(`${BASE}/vendors`, {
    params: filters,
  })
  return data
}

/** 取得廠商下拉選項 */
export async function fetchVendorOptions(): Promise<VendorListResponse[]> {
  const { data } = await apiClient.get(`${BASE}/vendors/options`)
  return data
}

/** 取得單筆廠商詳情 */
export async function fetchVendor(vendorId: string): Promise<{
  success: boolean
  data: VendorRecord
}> {
  const { data } = await apiClient.get(`${BASE}/vendors/${vendorId}`)
  return data
}

/** 新增廠商 */
export async function createVendor(
  payload: VendorCreate,
): Promise<{ success: boolean; data: VendorRecord }> {
  const { data } = await apiClient.post(`${BASE}/vendors`, payload)
  return data
}

/** 更新廠商 */
export async function updateVendor(
  vendorId: string,
  payload: VendorUpdate,
): Promise<{ success: boolean; data: VendorRecord }> {
  const { data } = await apiClient.put(`${BASE}/vendors/${vendorId}`, payload)
  return data
}

/** 刪除廠商 */
export async function deleteVendor(vendorId: string): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete(`${BASE}/vendors/${vendorId}`)
  return data
}

export interface VendorImportRowError {
  row: number
  vendor_id: string
  message: string
}

export interface VendorImportResult {
  total_rows: number
  created: number
  updated: number
  skipped: number
  errors: VendorImportRowError[]
}

/** 廠商 Excel 批次匯入（upsert） */
export async function importVendors(file: File): Promise<VendorImportResult> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post(`${BASE}/vendors/import`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ── 預算科目端點 ────────────────────────────────────────────────────────────────

/** 取得預算科目清單 */
export async function fetchBudgetCategories(): Promise<{
  total: number
  items: BudgetCategoryRecord[]
}> {
  const { data } = await apiClient.get(`${BASE}/budget-categories`)
  return data
}

/** 取得預算科目下拉選項 */
export async function fetchBudgetCategoryOptions(): Promise<BudgetCategoryListResponse[]> {
  const { data } = await apiClient.get(`${BASE}/budget-categories/options`)
  return data
}

/** 新增預算科目 */
export async function createBudgetCategory(
  payload: Record<string, any>,
): Promise<{ success: boolean; data: BudgetCategoryRecord }> {
  const { data } = await apiClient.post(`${BASE}/budget-categories`, payload)
  return data
}

// ── 合約項目端點 ────────────────────────────────────────────────────────────────

/** 取得合約項目清單 */
export async function fetchContractItems(contractId: string): Promise<{
  total: number
  items: any[]
}> {
  const { data } = await apiClient.get(`${BASE}/${contractId}/items`)
  return data
}

/** 新增合約項目 */
export async function createContractItem(
  contractId: string,
  payload: any,
): Promise<{ success: boolean; data: any }> {
  const { data } = await apiClient.post(`${BASE}/${contractId}/items`, payload)
  return data
}

/** 更新合約項目 */
export async function updateContractItem(
  contractId: string,
  itemId: number,
  payload: any,
): Promise<{ success: boolean; data: any }> {
  const { data } = await apiClient.put(`${BASE}/${contractId}/items/${itemId}`, payload)
  return data
}

/** 刪除合約項目 */
export async function deleteContractItem(
  contractId: string,
  itemId: number,
): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete(`${BASE}/${contractId}/items/${itemId}`)
  return data
}

// ── 統計端點 ──────────────────────────────────────────────────────────────────

/** 取得合約統計資訊 */
export async function fetchContractStats(): Promise<{
  total: number
  by_status: Record<string, number>
  by_risk_level: Record<string, number>
}> {
  const { data } = await apiClient.get(`${BASE}/stats`)
  return data
}

/** 取得即將到期合約清單 */
export async function fetchExpiringContracts(days = 90): Promise<{
  total: number
  days: number
  items: Array<{
    contract_id: string
    contract_name: string
    contract_type: string
    contract_status: string
    responsible_dept: string
    vendor_name: string
    end_date: string
    remaining_days: number
    total_amount_tax_included: number
    risk_level: string
    manager: string
  }>
}> {
  const { data } = await apiClient.get(`${BASE}/expiring`, { params: { days } })
  return data
}

/** 手動觸發合約資料同步 */
export async function syncContractsFromRagic(): Promise<{
  success: boolean
  synced: number
  errors: string[]
}> {
  const { data } = await apiClient.post(`${BASE}/sync`)
  return data
}

// ── Dashboard 端點 ──────────────────────────────────────────────────────────

/** 取得 Dashboard KPI 指標 */
export async function fetchDashboardKPI(budgetYear?: number): Promise<{
  active_contracts: number
  total_annual_amount: number
  high_risk_count: number
  expiring_in_90days: number
  monthly_claim_amount: number
  accrual_amount: number
  budget_year: number
}> {
  const { data } = await apiClient.get(`${BASE}/dashboard/kpi`, {
    params: budgetYear ? { budget_year: budgetYear } : undefined,
  })
  return data
}

/** 取得 Dashboard 部門金額分組（可依簽約公司篩選） */
export async function fetchDashboardByDept(
  budgetYear?: number,
  company?: string,
): Promise<{
  budget_year: number
  items: Array<{ dept: string; amount: number; count: number }>
  company?: string
}> {
  const params: Record<string, any> = {}
  if (budgetYear) params.budget_year = budgetYear
  if (company)    params.company     = company
  const { data } = await apiClient.get(`${BASE}/dashboard/by-dept`, {
    params: Object.keys(params).length ? params : undefined,
  })
  return data
}


/** 更新預算科目 */
export async function updateBudgetCategory(
  categoryId: number,
  payload: Record<string, any>,
): Promise<BudgetCategoryRecord> {
  const { data } = await apiClient.put(`${BASE}/budget-categories/${categoryId}`, payload)
  return data
}

/** 刪除預算科目 */
export async function deleteBudgetCategory(categoryId: number): Promise<void> {
  await apiClient.delete(`${BASE}/budget-categories/${categoryId}`)
}

// ── 請款 / 核銷記錄端點 ──────────────────────────────────────────────────────

export interface ClaimReviewLogEntry {
  action: string
  actor: string
  from_status: string
  to_status: string
  comment: string
  timestamp: string
}

export interface ClaimRecord {
  id: number
  contract_id: string
  contract_name?: string   // 後端 JOIN 補充
  claim_type: string
  claim_date: string
  invoice_no?: string
  amount: number
  status: string
  approver?: string
  remarks?: string
  review_log?: string      // JSON string，解析為 ClaimReviewLogEntry[]
  created_at: string
  updated_at: string
  cost_company?: string    // F6 費用歸屬公司
}

export interface ContractItemRecord {
  id: number
  contract_id: string
  item_seq: number
  item_name: string
  item_category: string
  unit_price_tax_excluded?: number
  quantity?: number
  unit?: string
  tax_rate: number
  amount_tax_excluded: number
  amount_tax_included: number
  is_fixed: boolean
  is_floating: boolean
  created_at: string
  updated_at: string
}

export interface ContractItemCreate {
  item_name: string
  item_category?: string
  item_seq?: number
  unit_price_tax_excluded?: number
  quantity?: number
  unit?: string
  tax_rate?: number
  amount_tax_excluded?: number
  amount_tax_included?: number
  is_fixed?: boolean
  is_floating?: boolean
}

export interface ContractItemUpdate extends Partial<ContractItemCreate> {}

export interface ClaimCreate {
  contract_id: string
  claim_type: string
  claim_date: string
  invoice_no?: string
  amount: number
  status?: string
  approver?: string
  remarks?: string
  cost_company?: string  // F6
}

export interface ClaimUpdate {
  claim_type?: string
  claim_date?: string
  invoice_no?: string
  amount?: number
  status?: string
  approver?: string
  remarks?: string
}

/** 請款統計（各狀態筆數/金額、當月請款） */
export async function fetchClaimsStats(): Promise<{
  total_claims: number
  total_amount: number
  monthly_amount: number
  pending_count: number
  by_status: Record<string, number>
  by_status_amount: Record<string, number>
}> {
  const { data } = await apiClient.get(`${BASE}/claims/stats`)
  return data
}

/** 請款審核（核准 / 拒絕 / 付款 / 重送） */
export async function reviewClaim(
  claimId: number,
  action: 'approve' | 'reject' | 'mark_paid' | 'resubmit',
  comment?: string,
  approver?: string,
): Promise<ClaimRecord> {
  const { data } = await apiClient.post(`${BASE}/claims/${claimId}/review`, {
    action,
    comment,
    approver,
  })
  return data
}

/** 批次審核請款（approve / reject） */
export async function batchReviewClaims(
  claimIds: number[],
  action: 'approve' | 'reject',
  comment?: string,
  approver?: string,
): Promise<{ success_count: number; skipped_count: number; success_ids: number[]; skipped_ids: number[] }> {
  const { data } = await apiClient.post(`${BASE}/claims/batch-review`, {
    claim_ids: claimIds,
    action,
    comment,
    approver,
  })
  return data
}

/** 取得請款記錄清單 */
export async function fetchClaims(params: {
  contract_id?: string
  status?: string
  page?: number
  size?: number
} = {}): Promise<{ total: number; page: number; size: number; items: ClaimRecord[] }> {
  const { data } = await apiClient.get(`${BASE}/claims`, { params })
  return data
}

/** 新增請款記錄 */
export async function createClaim(
  payload: ClaimCreate,
): Promise<ClaimRecord> {
  const { data } = await apiClient.post(`${BASE}/claims`, payload)
  return data
}

/** 更新請款記錄 */
export async function updateClaim(
  claimId: number,
  payload: ClaimUpdate,
): Promise<ClaimRecord> {
  const { data } = await apiClient.put(`${BASE}/claims/${claimId}`, payload)
  return data
}

/** 刪除請款記錄 */
export async function deleteClaim(claimId: number): Promise<void> {
  await apiClient.delete(`${BASE}/claims/${claimId}`)
}


// ── 匯出 Excel ────────────────────────────────────────────────────────────────

/**
 * 匯出合約列表 Excel
 * 帶入與列表頁相同的篩選條件，瀏覽器直接下載。
 */
export function exportContractsExcel(params: {
  search?: string
  status?: string
  vendor_id?: string
  risk_level?: string
  budget_year?: number
  responsible_dept?: string
} = {}): void {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') query.set(k, String(v))
  })
  const qs = query.toString()
  const url = `/api/v1/contract/export${qs ? '?' + qs : ''}`
  const a = document.createElement('a')
  a.href = url
  a.download = ''
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

/**
 * 匯出請款清單 Excel
 * 帶入與請款頁相同的篩選條件，瀏覽器直接下載。
 */
export function exportClaimsExcel(params: {
  contract_id?: string
  status?: string
} = {}): void {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') query.set(k, String(v))
  })
  const qs = query.toString()
  const url = `/api/v1/contract/claims/export${qs ? '?' + qs : ''}`
  const a = document.createElement('a')
  a.href = url
  a.download = ''
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// ── 預算執行率分析 ──────────────────────────────────────────────────────────────

/**
 * 取得預算執行率分析（依科目聚合）
 */
export async function fetchBudgetAnalysis(
  budget_year: number,
): Promise<BudgetAnalysisRecord[]> {
  const { data } = await apiClient.get<BudgetAnalysisRecord[]>(
    `${BASE}/budget-analysis`,
    { params: { budget_year } },
  )
  return data
}

// ── 合約續約 ────────────────────────────────────────────────────────────────


/** 查詢某合約的所有續約申請 */
export async function fetchRenewalsByContract(contractId: string): Promise<RenewalRecord[]> {
  const { data } = await apiClient.get<RenewalRecord[]>(`${BASE}/${contractId}/renewals`)
  return data
}

/** 查詢全部續約申請（管理員） */
export async function fetchAllRenewals(params: {
  status?: string; page?: number; size?: number
} = {}): Promise<RenewalListResponse> {
  const { data } = await apiClient.get<RenewalListResponse>(`${BASE}/renewals/all`, { params })
  return data
}

/** 提交續約申請 */
export async function applyRenewal(contractId: string, payload: {
  renewal_start_date: string
  renewal_end_date: string
  new_amount?: number | null
  renewal_reason: string
  remarks?: string
  applicant_dept?: string
}): Promise<RenewalRecord> {
  const { data } = await apiClient.post<RenewalRecord>(`${BASE}/${contractId}/renewals`, payload)
  return data
}

/** 審核續約申請（approve / reject / withdraw） */
export async function reviewRenewal(renewalId: number, payload: {
  action: 'approve' | 'reject' | 'withdraw'
  review_comment?: string
}): Promise<RenewalRecord> {
  const { data } = await apiClient.post<RenewalRecord>(`${BASE}/renewals/${renewalId}/review`, payload)
  return data
}

// ── C4 廠商績效 ───────────────────────────────────────────────────────────────

import type { VendorPerformance, ClaimAttachment, ContractAttachment } from '@/types/contract'

/** 取得廠商績效指標 */
export async function fetchVendorPerformance(vendorId: string): Promise<VendorPerformance> {
  const { data } = await apiClient.get<VendorPerformance>(`${BASE}/vendors/${vendorId}/performance`)
  return data
}

// ── C5 請款附件 ───────────────────────────────────────────────────────────────

/** 列出請款附件 */
export async function fetchClaimAttachments(claimId: number): Promise<ClaimAttachment[]> {
  const { data } = await apiClient.get<ClaimAttachment[]>(`${BASE}/claims/${claimId}/attachments`)
  return data
}

/** 上傳請款附件 */
export async function uploadClaimAttachment(claimId: number, file: File): Promise<ClaimAttachment> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post<ClaimAttachment>(
    `${BASE}/claims/${claimId}/attachments`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return data
}

/** 刪除請款附件 */
export async function deleteClaimAttachment(attachmentId: number): Promise<void> {
  await apiClient.delete(`${BASE}/claims/attachments/${attachmentId}`)
}

/** 附件下載 / 預覽 URL（帶 JWT） */
export function getAttachmentUrl(downloadUrl: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
  return `${base}${downloadUrl}`
}

// ── E1 合約本體附件 ───────────────────────────────────────────────────────────

/** 列出合約本體附件 */
export async function fetchContractAttachments(contractId: string): Promise<ContractAttachment[]> {
  const { data } = await apiClient.get<ContractAttachment[]>(`${BASE}/${contractId}/attachments`)
  return data
}

/** 上傳合約本體附件 */
export async function uploadContractAttachment(contractId: string, file: File): Promise<ContractAttachment> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await apiClient.post<ContractAttachment>(
    `${BASE}/${contractId}/attachments`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

/** 刪除合約本體附件 */
export async function deleteContractAttachment(attachmentId: number): Promise<void> {
  await apiClient.delete(`${BASE}/doc-attachments/${attachmentId}`)
}

// ── F3 費用分攤 ───────────────────────────────────────────────────────────────

export interface CostAllocationItem {
  company_name:    string
  allocation_type: 'percentage' | 'fixed'
  value:           number
}

export interface CostAllocationRecord extends CostAllocationItem {
  id:          number
  contract_id: string
  created_at:  string
}

/** 查詢費用分攤明細 */
export async function fetchCostAllocations(contractId: string): Promise<CostAllocationRecord[]> {
  const { data } = await apiClient.get<CostAllocationRecord[]>(`${BASE}/${contractId}/cost-allocations`)
  return data
}

/** 整批覆寫費用分攤明細 */
export async function saveCostAllocations(
  contractId: string,
  items: CostAllocationItem[],
): Promise<CostAllocationRecord[]> {
  const { data } = await apiClient.put<CostAllocationRecord[]>(
    `${BASE}/${contractId}/cost-allocations`,
    items,
  )
  return data
}

// ── H1 — 合約範本 ─────────────────────────────────────────────────────────────

/** 取得合約範本清單 */
export async function fetchTemplates(enabledOnly = false): Promise<{
  total: number
  templates: ContractTemplate[]
}> {
  const { data } = await apiClient.get(`${BASE}/templates`, {
    params: enabledOnly ? { enabled_only: true } : undefined,
  })
  return data
}

/** 新增合約範本 */
export async function createTemplate(
  payload: ContractTemplateCreate,
): Promise<ContractTemplate> {
  const { data } = await apiClient.post<ContractTemplate>(`${BASE}/templates`, payload)
  return data
}

/** 修改合約範本 */
export async function updateTemplate(
  templateId: number,
  payload: Partial<ContractTemplateCreate>,
): Promise<ContractTemplate> {
  const { data } = await apiClient.put<ContractTemplate>(
    `${BASE}/templates/${templateId}`,
    payload,
  )
  return data
}

/** 刪除合約範本 */
export async function deleteTemplate(templateId: number): Promise<void> {
  await apiClient.delete(`${BASE}/templates/${templateId}`)
}

// ── H2 — 合約變更歷程 ─────────────────────────────────────────────────────────

/** 查詢合約欄位變更歷程 */
export async function fetchChangeLogs(
  contractId: string,
  limit = 100,
): Promise<{ total: number; logs: ContractChangeLog[] }> {
  const { data } = await apiClient.get(
    `${BASE}/${contractId}/change-logs`,
    { params: { limit } },
  )
  return data
}

// ── H3 — 分期付款計劃 ─────────────────────────────────────────────────────────

/** 查詢分期付款計劃 */
export async function fetchPaymentSchedules(
  contractId: string,
): Promise<{ total: number; schedules: PaymentSchedule[] }> {
  const { data } = await apiClient.get(`${BASE}/${contractId}/payment-schedules`)
  return data
}

/** 新增付款里程碑 */
export async function createPaymentSchedule(
  contractId: string,
  payload: PaymentScheduleCreate,
): Promise<PaymentSchedule> {
  const { data } = await apiClient.post<PaymentSchedule>(
    `${BASE}/${contractId}/payment-schedules`,
    payload,
  )
  return data
}

/** 更新付款里程碑（含標記已付款） */
export async function updatePaymentSchedule(
  contractId: string,
  scheduleId: number,
  payload: Partial<PaymentScheduleCreate & { status: string; paid_date: string }>,
): Promise<PaymentSchedule> {
  const { data } = await apiClient.put<PaymentSchedule>(
    `${BASE}/${contractId}/payment-schedules/${scheduleId}`,
    payload,
  )
  return data
}

/** 刪除付款里程碑 */
export async function deletePaymentSchedule(
  contractId: string,
  scheduleId: number,
): Promise<void> {
  await apiClient.delete(`${BASE}/${contractId}/payment-schedules/${scheduleId}`)
}

// ── H4 — 操作稽核日誌 ─────────────────────────────────────────────────────────

/** 查詢合約操作稽核日誌 */
export async function fetchAuditLogs(
  contractId: string,
  limit = 100,
): Promise<{ total: number; logs: ContractAuditLog[] }> {
  const { data } = await apiClient.get(
    `${BASE}/${contractId}/audit-logs`,
    { params: { limit } },
  )
  return data
}

// ── I1 — 多層審核關卡 ─────────────────────────────────────────────────────────

/** 查詢合約審核關卡（預設只回最新一輪） */
export async function fetchApprovalStages(
  contractId: string,
  latestOnly = true,
): Promise<{ total: number; stages: ApprovalStage[] }> {
  const { data } = await apiClient.get(`${BASE}/${contractId}/approval-stages`, {
    params: { latest_only: latestOnly },
  })
  return data
}

/** 核准某審核關卡 */
export async function approveStage(
  contractId: string,
  stageId: number,
  comment?: string,
): Promise<{ success: boolean; contract_promoted: boolean }> {
  const { data } = await apiClient.post(
    `${BASE}/${contractId}/approval-stages/${stageId}/approve`,
    { comment },
  )
  return data
}

/** 拒絕某審核關卡 */
export async function rejectStage(
  contractId: string,
  stageId: number,
  comment?: string,
): Promise<{ success: boolean }> {
  const { data } = await apiClient.post(
    `${BASE}/${contractId}/approval-stages/${stageId}/reject`,
    { comment },
  )
  return data
}

/** 取得審核關卡設定清單 */
export async function fetchApprovalConfigs(): Promise<{ total: number; configs: ApprovalConfig[] }> {
  const { data } = await apiClient.get(`${BASE}/approval-configs`)
  return data
}

/** 新增審核關卡設定 */
export async function createApprovalConfig(payload: ApprovalConfigCreate): Promise<ApprovalConfig> {
  const { data } = await apiClient.post<ApprovalConfig>(`${BASE}/approval-configs`, payload)
  return data
}

/** 修改審核關卡設定 */
export async function updateApprovalConfig(
  configId: number,
  payload: Partial<ApprovalConfigCreate>,
): Promise<ApprovalConfig> {
  const { data } = await apiClient.put<ApprovalConfig>(`${BASE}/approval-configs/${configId}`, payload)
  return data
}

/** 刪除審核關卡設定 */
export async function deleteApprovalConfig(configId: number): Promise<void> {
  await apiClient.delete(`${BASE}/approval-configs/${configId}`)
}

// ── I2 — 驗收管理 ─────────────────────────────────────────────────────────────

export async function fetchAcceptances(
  contractId: string,
): Promise<{ total: number; acceptances: Acceptance[] }> {
  const { data } = await apiClient.get(`${BASE}/${contractId}/acceptances`)
  return data
}

export async function createAcceptance(
  contractId: string,
  payload: AcceptanceCreate,
): Promise<Acceptance> {
  const { data } = await apiClient.post<Acceptance>(`${BASE}/${contractId}/acceptances`, payload)
  return data
}

export async function updateAcceptance(
  contractId: string,
  acceptanceId: number,
  payload: Partial<AcceptanceCreate & { status: string }>,
): Promise<Acceptance> {
  const { data } = await apiClient.put<Acceptance>(
    `${BASE}/${contractId}/acceptances/${acceptanceId}`,
    payload,
  )
  return data
}

export async function deleteAcceptance(contractId: string, acceptanceId: number): Promise<void> {
  await apiClient.delete(`${BASE}/${contractId}/acceptances/${acceptanceId}`)
}

// ── I3 — 保證金追蹤 ─────────────────────────────────────────────────────────

export async function fetchDeposits(
  contractId: string,
): Promise<{ total: number; deposits: Deposit[] }> {
  const { data } = await apiClient.get(`${BASE}/${contractId}/deposits`)
  return data
}

export async function createDeposit(
  contractId: string,
  payload: DepositCreate,
): Promise<Deposit> {
  const { data } = await apiClient.post<Deposit>(`${BASE}/${contractId}/deposits`, payload)
  return data
}

export async function updateDeposit(
  contractId: string,
  depositId: number,
  payload: Partial<DepositCreate & { actual_return_date: string; status: string }>,
): Promise<Deposit> {
  const { data } = await apiClient.put<Deposit>(
    `${BASE}/${contractId}/deposits/${depositId}`,
    payload,
  )
  return data
}

export async function deleteDeposit(contractId: string, depositId: number): Promise<void> {
  await apiClient.delete(`${BASE}/${contractId}/deposits/${depositId}`)
}

// ── I4 — 年化費用摘要 ─────────────────────────────────────────────────────────

export async function fetchCostSummary(contractId: string): Promise<CostSummary> {
  const { data } = await apiClient.get<CostSummary>(`${BASE}/${contractId}/cost-summary`)
  return data
}

// ── J1 — 廠商集中度分析 ───────────────────────────────────────────────────────

export async function fetchVendorConcentration(
  budgetYear?: number,
  threshold = 30,
): Promise<VendorConcentrationResponse> {
  const params: Record<string, any> = { threshold }
  if (budgetYear) params.budget_year = budgetYear
  const { data } = await apiClient.get<VendorConcentrationResponse>(
    `${BASE}/vendors/concentration`,
    { params },
  )
  return data
}

// ── J2 — 合約成本趨勢 ─────────────────────────────────────────────────────────

export async function fetchCostTrend(params: {
  budget_year?: number
  granularity?: 'month' | 'quarter'
  company?: string
  dept?: string
}): Promise<CostTrendResponse> {
  const { data } = await apiClient.get<CostTrendResponse>(
    `${BASE}/analytics/cost-trend`,
    { params },
  )
  return data
}

// ── J3 — 月度/季度報表 ────────────────────────────────────────────────────────

export async function fetchSummaryReport(
  budgetYear: number,
  periodType: 'monthly' | 'quarterly',
): Promise<SummaryReportResponse> {
  const { data } = await apiClient.get<SummaryReportResponse>(
    `${BASE}/reports/summary`,
    { params: { budget_year: budgetYear, period_type: periodType } },
  )
  return data
}

export function exportSummaryReport(budgetYear: number, periodType: 'monthly' | 'quarterly'): void {
  const params = new URLSearchParams({
    budget_year: String(budgetYear),
    period_type: periodType,
  })
  window.open(`/api/v1/contract/reports/summary/export?${params}`, '_blank')
}

// ── J4 — 批次操作 ─────────────────────────────────────────────────────────────

export async function batchUpdateManager(
  contractIds: string[],
  manager: string,
): Promise<{ success: boolean; updated: number }> {
  const { data } = await apiClient.patch(`${BASE}/batch/manager`, {
    contract_ids: contractIds,
    manager,
  })
  return data
}

export async function batchSubmit(
  contractIds: string[],
): Promise<{ success: boolean; submitted: number; failed: Array<{ contract_id: string; reason: string }> }> {
  const { data } = await apiClient.post(`${BASE}/batch/submit`, {
    contract_ids: contractIds,
  })
  return data
}

// ── K2 — SLA 追蹤 ─────────────────────────────────────────────────────────────

export async function fetchSlaMetrics(
  contractId: string,
): Promise<{ total: number; metrics: SlaMetric[] }> {
  const { data } = await apiClient.get(`${BASE}/${contractId}/sla-metrics`)
  return data
}

export async function createSlaMetric(
  contractId: string,
  payload: SlaMetricCreate,
): Promise<SlaMetric> {
  const { data } = await apiClient.post<SlaMetric>(
    `${BASE}/${contractId}/sla-metrics`,
    payload,
  )
  return data
}

export async function updateSlaMetric(
  contractId: string,
  metricId: number,
  payload: Partial<SlaMetricCreate>,
): Promise<SlaMetric> {
  const { data } = await apiClient.put<SlaMetric>(
    `${BASE}/${contractId}/sla-metrics/${metricId}`,
    payload,
  )
  return data
}

export async function deleteSlaMetric(
  contractId: string,
  metricId: number,
): Promise<void> {
  await apiClient.delete(`${BASE}/${contractId}/sla-metrics/${metricId}`)
}

export async function fetchSlaRecords(
  contractId: string,
  metricId?: number,
): Promise<{ total: number; records: SlaRecord[] }> {
  const { data } = await apiClient.get(`${BASE}/${contractId}/sla-records`, {
    params: metricId ? { metric_id: metricId } : undefined,
  })
  return data
}

export async function createSlaRecord(
  contractId: string,
  payload: SlaRecordCreate,
): Promise<SlaRecord> {
  const { data } = await apiClient.post<SlaRecord>(
    `${BASE}/${contractId}/sla-records`,
    payload,
  )
  return data
}

export async function deleteSlaRecord(
  contractId: string,
  recordId: number,
): Promise<void> {
  await apiClient.delete(`${BASE}/${contractId}/sla-records/${recordId}`)
}

export async function fetchSlaSummary(contractId: string): Promise<SlaSummary> {
  const { data } = await apiClient.get<SlaSummary>(`${BASE}/${contractId}/sla-summary`)
  return data
}
