/**
 * 日曜核准請款單月報表 API
 * 所有 nichiyo-claim-report 相關 API 呼叫的封裝函數
 */
import apiClient from '@/api/client'

const BASE = '/nichiyo-claim-report'

// ── Types ─────────────────────────────────────────────────────────────────────

/** 月報明細（品項級，一筆 = 一個品項） */
export interface NichiyoClaimReportItem {
  // 主單欄位（每列重複）
  order_id: number
  department_display: string
  claim_no: string
  account_category: string | null
  request_date: string | null
  approved_date: string | null
  payment_date: string | null
  applicant: string | null
  purpose_description: string | null
  payment_type: string | null
  payee: string | null
  subtotal: number | null
  tax: number | null
  total: number | null
  payable_amount: number | null
  // 品項欄位
  item_id: number | null
  seq: number | null
  product_name: string | null
  qty: string | null
  unit: string | null
  unit_price: number | null
  amount: number | null
  item_remark: string | null
  invoice_no: string | null
}

/** 月報摘要 KPI */
export interface NichiyoClaimReportSummary {
  order_count: number
  total_payable: number
  total_tax: number
  item_count: number
  dept_count: number
  avg_payable: number
  rej_count: number
  top_order: string | null
  top_dept_by_count: string | null
  top_dept_by_amount: string | null
  dept_summary: Array<{
    department_display: string
    order_count: number
    total_payable: number
    total_tax: number
  }>
}

/** 部門統計 */
export interface NichiyoClaimDeptStat {
  department_display: string
  order_count: number
  total_payable: number
  total_tax: number
}

/** 同步狀態 */
export interface NichiyoClaimSyncStatus {
  recent_logs: Array<{
    id: number
    module: string
    trigger: string
    status: string
    message: string
    created_at: string
  }>
  pending_detail_count: number
  dept_stats: Array<{
    department_display: string
    total: number
    detail_synced: number
    pending: number
  }>
}

/** 分頁回應 */
export interface PaginatedResponse<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

// ── 請款單主單 / Detail ────────────────────────────────────────────────────────

/** 請款單主單（訂單級） */
export interface NichiyoClaimOrder {
  id: number
  claim_no: string
  department_display: string
  account_category: string | null
  applicant: string | null
  purpose_description: string | null
  payment_type: string | null
  payee: string | null
  subtotal: number | null
  tax: number | null
  total: number | null
  payable_amount: number | null
  status: string            // 'F' | 'N' | 'REJ'
  request_date: string | null
  approved_date: string | null
  payment_date: string | null
  last_updated_at: string | null
  detail_synced: boolean
  ragic_sheet_path: string
  ragic_record_id: string
  ragic_url: string
}

/** 請款單品項（Detail Drawer 使用） */
export interface NichiyoClaimOrderItem {
  id: number
  seq: number
  product_name: string | null
  qty: string | null
  unit: string | null
  unit_price: number | null
  amount: number | null
  item_remark: string | null
}

/** 請款單完整詳情（含品項） */
export interface NichiyoClaimOrderDetail {
  order: NichiyoClaimOrder
  items: NichiyoClaimOrderItem[]
}

// ── 稽核 ──────────────────────────────────────────────────────────────────────

export interface NichiyoClaimAuditAnomaly {
  source: 'nichiyo_claim'
  order_id: number
  doc_no: string
  department: string
  approved_date: string | null
  rule_code: string
  rule_name: string
  severity: 'high' | 'medium' | 'low'
  detail: string
  ragic_url: string
}

export interface NichiyoClaimAuditRuleStat {
  rule_code: string
  rule_name: string
  severity: 'high' | 'medium' | 'low'
  applies_to: string[]
  count: number
}

export interface NichiyoClaimAuditSummary {
  total_anomalies: number
  total_orders: number
  by_rule: NichiyoClaimAuditRuleStat[]
}

// ── API Functions ──────────────────────────────────────────────────────────────

/** 請款單主單清單（訂單級分頁） */
export const getNichiyoClaimOrders = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
  payment_date_from?: string
  payment_date_to?: string
  status?: string
  keyword?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<NichiyoClaimOrder>>(
    `${BASE}/approved/orders`,
    { params },
  )

/** 單筆請款單完整資料（含品項） */
export const getNichiyoClaimOrderDetail = (orderId: number) =>
  apiClient.get<NichiyoClaimOrderDetail>(`${BASE}/approved/orders/${orderId}`)

/** 月報明細（品項級，分頁） */
export const getNichiyoClaimMonthlyItems = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
  payment_date_from?: string
  payment_date_to?: string
  q?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<NichiyoClaimReportItem>>(
    `${BASE}/approved/monthly`,
    { params },
  )

/** 月報 KPI 摘要 */
export const getNichiyoClaimSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
}) =>
  apiClient.get<NichiyoClaimReportSummary>(`${BASE}/approved/summary`, { params })

/** 部門統計 */
export const getNichiyoClaimDepartments = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  account_category?: string
}) =>
  apiClient.get<NichiyoClaimDeptStat[]>(`${BASE}/approved/departments`, { params })

/** Excel 匯出（blob） */
export const exportNichiyoClaimReport = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
}) =>
  apiClient.get(`${BASE}/approved/export`, {
    params,
    responseType: 'blob',
  })

/** 有核准資料的年月清單（降冪） */
export const getNichiyoClaimAvailableMonths = () =>
  apiClient.get<string[]>(`${BASE}/approved/available-months`)

/** 部門清單（下拉選項） */
export const getNichiyoClaimDeptList = () =>
  apiClient.get<string[]>(`${BASE}/config/departments`)

/** 會科清單（下拉選項） */
export const getNichiyoClaimAccountCategories = () =>
  apiClient.get<string[]>(`${BASE}/config/account-categories`)

/** 觸發同步 */
export const triggerNichiyoClaimSync = (fullResync = false) =>
  apiClient.post<{ message: string; task: string }>(
    `${BASE}/sync`,
    null,
    { params: { full_resync: fullResync } },
  )

/** 同步狀態 */
export const getNichiyoClaimSyncStatus = () =>
  apiClient.get<NichiyoClaimSyncStatus>(`${BASE}/sync/status`)

/** 資料異常列表（分頁） */
export const getNichiyoClaimAuditAnomalies = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  rule_code?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<NichiyoClaimAuditAnomaly>>(
    `${BASE}/audit/anomalies`,
    { params },
  )

/** 資料異常 KPI 摘要 */
export const getNichiyoClaimAuditSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
}) =>
  apiClient.get<NichiyoClaimAuditSummary>(`${BASE}/audit/summary`, { params })

export interface NichiyoCombinedDeptStat {
  department_display: string
  purchase_count: number
  purchase_amount: number
  purchase_tax: number
  claim_count: number
  claim_payable: number
  claim_tax: number
}

export const getNichiyoCombinedDepartments = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
}) =>
  apiClient.get<NichiyoCombinedDeptStat[]>(`${BASE}/combined/departments`, { params })
export const getNichiyoClaimCombinedDepartments = getNichiyoCombinedDepartments
