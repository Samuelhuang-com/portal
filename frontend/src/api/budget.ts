/**
 * Budget Management API
 * 所有 budget 相關 API 呼叫的封裝函數
 */
import apiClient from '@/api/client'

const BASE = '/budget'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BudgetYear {
  id: number
  budget_year: number
  roc_year?: number
  start_date?: string
  end_date?: string
  is_active: number
  notes?: string
}

export interface BudgetPlan {
  id: number
  plan_code: string
  plan_name: string
  dept_id: number
  dept_name?: string
  dept_code?: string
  budget_year_id: number
  budget_year?: number
  plan_type: string
  version_no: number
  status: string
  notes?: string
}

export interface BudgetPlanDetail {
  id: number
  budget_plan_id: number
  line_type: string
  seq_num?: number
  seq_raw?: string
  raw_account_code_name?: string
  standard_account_code_id?: number
  account_code_name?: string
  raw_budget_item_name?: string
  standard_budget_item_id?: number
  budget_item_name?: string
  month_01_budget?: number
  month_02_budget?: number
  month_03_budget?: number
  month_04_budget?: number
  month_05_budget?: number
  month_06_budget?: number
  month_07_budget?: number
  month_08_budget?: number
  month_09_budget?: number
  month_10_budget?: number
  month_11_budget?: number
  month_12_budget?: number
  annual_budget?: number
  raw_remark?: string
  is_active_detail: number
}

export interface BudgetTransaction {
  id: number
  budget_year_id: number
  budget_year?: number
  dept_id?: number
  dept_name?: string
  month_num?: number
  quarter_code?: string
  raw_account_code_name?: string
  account_code_id?: number
  account_code_name?: string
  raw_budget_item_name?: string
  budget_item_id?: number
  budget_item_name?: string
  description?: string
  amount_ex_tax?: number
  requester?: string
  note_1?: string
  note_2?: string
  note_3?: string
  has_formula_amount: number
  amount_missing_flag: number
}

export interface Department {
  id: number
  dept_code: string
  dept_name: string
  dept_group?: string
  sort_order: number
  is_active: number
}

export interface AccountCode {
  id: number
  account_code_name: string
  normalized_name: string
  is_raw_group: number
  is_active?: number
  notes?: string
}

export interface BudgetItem {
  id: number
  budget_item_name: string
  normalized_name: string
  is_capex: number
  is_active?: number
  notes?: string
}

export interface BudgetMapping {
  id: number
  dept_id?: number
  dept_name?: string
  quarter_code?: string
  source_account_header: string
  account_code_id?: number
  account_code_name?: string
  mapped_budget_item_name: string
  budget_item_id?: number
  budget_item_name?: string
  mapping_method: string
  notes?: string
}

export interface DashboardData {
  year: BudgetYear
  summary: {
    total_budget: number
    total_actual: number
    variance: number
    exec_rate: number
    overrun_count: number
    near_overrun_count: number
  }
  overrun_items: Array<{
    dept_name: string
    account_code_name: string
    annual_budget: number
    annual_actual: number
    annual_variance: number
  }>
  near_overrun_items: Array<{
    dept_name: string
    account_code_name: string
    annual_budget: number
    annual_actual: number
    exec_rate: number
  }>
  dept_summary: Array<{
    dept_name: string
    plan_budget: number
    actual_amount: number
    exec_rate: number
    variance: number
  }>
  data_quality: {
    dq_issue_count: number
    missing_amount_count: number
    unresolved_plan_count: number
  }
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export const getBudgetDashboard = (yearId = 1) =>
  apiClient.get<DashboardData>(`${BASE}/dashboard`, { params: { year_id: yearId } })

// ── Years ────────────────────────────────────────────────────────────────────

export const getBudgetYears = () =>
  apiClient.get<BudgetYear[]>(`${BASE}/years`)

// ── Plans ────────────────────────────────────────────────────────────────────

export const getBudgetPlans = (params?: {
  year_id?: number
  dept_id?: number
  status?: string
}) => apiClient.get<BudgetPlan[]>(`${BASE}/plans`, { params })

export const createBudgetPlan = (data: {
  plan_code: string
  plan_name: string
  dept_id: number
  budget_year_id: number
  plan_type?: string
  notes?: string
}) => apiClient.post<BudgetPlan>(`${BASE}/plans`, data)

export const getBudgetPlan = (planId: number) =>
  apiClient.get<BudgetPlan>(`${BASE}/plans/${planId}`)

export const updateBudgetPlan = (planId: number, data: {
  plan_name?: string
  status?: string
  notes?: string
}) => apiClient.put<BudgetPlan>(`${BASE}/plans/${planId}`, data)

export const deleteBudgetPlan = (planId: number) =>
  apiClient.delete(`${BASE}/plans/${planId}`)

// ── Plan Details ──────────────────────────────────────────────────────────────

export const getBudgetPlanDetails = (planId: number, activeOnly = true) =>
  apiClient.get<BudgetPlanDetail[]>(`${BASE}/plans/${planId}/details`, {
    params: { active_only: activeOnly },
  })

export const createBudgetPlanDetail = (planId: number, data: Partial<BudgetPlanDetail>) =>
  apiClient.post<BudgetPlanDetail>(`${BASE}/plans/${planId}/details`, data)

export const updateBudgetPlanDetail = (
  planId: number,
  detailId: number,
  data: Partial<BudgetPlanDetail>,
) => apiClient.put<BudgetPlanDetail>(`${BASE}/plans/${planId}/details/${detailId}`, data)

export const deleteBudgetPlanDetail = (planId: number, detailId: number) =>
  apiClient.delete(`${BASE}/plans/${planId}/details/${detailId}`)

// ── Transactions ──────────────────────────────────────────────────────────────

export const getTransactions = (params?: {
  year_id?: number
  dept_id?: number
  month_num?: number
  account_code_id?: number
  budget_item_id?: number
  amount_missing?: boolean
  search?: string
  limit?: number
  offset?: number
}) => apiClient.get<{ total: number; items: BudgetTransaction[] }>(
  `${BASE}/transactions`,
  { params },
)

export const exportTransactions = (params?: {
  year_id?: number
  dept_id?: number
  month_num?: number
  amount_missing?: boolean
  search?: string
}) => apiClient.get(`${BASE}/transactions/export`, {
  params,
  responseType: 'blob',
})

export const getTransaction = (id: number) =>
  apiClient.get<BudgetTransaction>(`${BASE}/transactions/${id}`)

export const updateTransaction = (id: number, data: Partial<BudgetTransaction>) =>
  apiClient.put<BudgetTransaction>(`${BASE}/transactions/${id}`, data)

// ── Masters — Departments ─────────────────────────────────────────────────────

export const getDepartments = (activeOnly = false) =>
  apiClient.get<Department[]>(`${BASE}/masters/departments`, {
    params: { active_only: activeOnly },
  })

export const createDepartment = (data: Omit<Department, 'id'>) =>
  apiClient.post<Department>(`${BASE}/masters/departments`, data)

export const updateDepartment = (id: number, data: Partial<Department>) =>
  apiClient.put<Department>(`${BASE}/masters/departments/${id}`, data)

// ── Masters — Account Codes ───────────────────────────────────────────────────

export const getAccountCodes = () =>
  apiClient.get<AccountCode[]>(`${BASE}/masters/account-codes`)

export const createAccountCode = (data: Omit<AccountCode, 'id'>) =>
  apiClient.post<AccountCode>(`${BASE}/masters/account-codes`, data)

export const updateAccountCode = (id: number, data: Partial<AccountCode>) =>
  apiClient.put<AccountCode>(`${BASE}/masters/account-codes/${id}`, data)

// ── Masters — Budget Items ────────────────────────────────────────────────────

export const getBudgetItems = () =>
  apiClient.get<BudgetItem[]>(`${BASE}/masters/budget-items`)

export const createBudgetItem = (data: Omit<BudgetItem, 'id'>) =>
  apiClient.post<BudgetItem>(`${BASE}/masters/budget-items`, data)

export const updateBudgetItem = (id: number, data: Partial<BudgetItem>) =>
  apiClient.put<BudgetItem>(`${BASE}/masters/budget-items/${id}`, data)

// ── Mappings ──────────────────────────────────────────────────────────────────

export const getMappings = (deptId?: number) =>
  apiClient.get<BudgetMapping[]>(`${BASE}/mappings`, {
    params: deptId ? { dept_id: deptId } : undefined,
  })

export const createMapping = (data: Omit<BudgetMapping, 'id' | 'dept_name' | 'account_code_name' | 'budget_item_name'>) =>
  apiClient.post<BudgetMapping>(`${BASE}/mappings`, data)

export const updateMapping = (id: number, data: Partial<BudgetMapping>) =>
  apiClient.put<BudgetMapping>(`${BASE}/mappings/${id}`, data)

export const deleteMapping = (id: number) =>
  apiClient.delete(`${BASE}/mappings/${id}`)

// ── Reports ───────────────────────────────────────────────────────────────────

export const getBudgetVsActual = (params?: {
  dept_name?: string
  account_code_name?: string
  plan_code?: string
  view_type?: 'total' | 'monthly'
}) => apiClient.get<{
  view_type: string
  total: number
  items: Array<Record<string, unknown>>
}>(`${BASE}/reports/budget-vs-actual`, { params })

export const getDataQuality = () =>
  apiClient.get<{
    data_quality_issues: unknown[]
    missing_amount_transactions: unknown[]
    unresolved_plan_details: unknown[]
    summary: {
      dq_issue_count: number
      missing_amount_count: number
      unresolved_plan_count: number
    }
  }>(`${BASE}/reports/data-quality`)

export const getMonthlyActual = (yearId: number, deptName?: string) =>
  apiClient.get<unknown[]>(`${BASE}/reports/monthly-actual`, {
    params: { year_id: yearId, dept_name: deptName },
  })
