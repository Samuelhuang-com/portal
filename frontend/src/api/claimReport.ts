/**
 * 核准請款單月報表 API
 * 所有 claim-report 相關 API 呼叫的封裝函數
 */
import apiClient from '@/api/client'

const BASE = '/claim-report'

// ── Types ─────────────────────────────────────────────────────────────────────

/** 請款單主單 */
export interface ClaimOrder {
  id: number
  department_display: string
  request_no: string
  department_request_no: string | null
  dept_request_no_label: string
  account_subject: string | null
  apply_date: string | null
  approved_date: string | null
  applicant: string | null
  payment_type: string | null          // 零用金 / 匯款
  purpose_description: string | null
  subtotal: number | null
  tax: number | null
  total: number | null
  payable_amount: number | null
  payee: string | null
  bank_name: string | null
  bank_branch: string | null
  bank_account: string | null
  payment_date: string | null
  status: string
  detail_synced: boolean
  last_updated_at: string | null
  ragic_sheet_path: string
  ragic_record_id: string
  ragic_url: string
}

/** 請款單品項（Detail Drawer 使用） */
export interface ClaimOrderItem {
  id: number
  seq: number
  item_name: string | null
  quantity: string | null
  unit: string | null
  item_note: string | null
  proposed_vendor_amount: number | null
  invoice_no: string | null
  receipt_no: string | null
}

/** 請款單完整詳情（含品項） */
export interface ClaimOrderDetail {
  order: ClaimOrder
  items: ClaimOrderItem[]
}

/** 月報明細（品項級，一筆 = 一個品項） */
export interface ClaimReportItem {
  claim_id: number
  department_display: string
  request_no: string
  department_request_no: string | null
  account_subject: string | null
  apply_date: string | null
  approved_date: string | null
  payment_date: string | null
  applicant: string | null
  payment_type: string | null
  purpose_description: string | null
  subtotal: number | null
  tax: number | null
  total: number | null
  payable_amount: number | null
  payee: string | null
  status: string
  ragic_url: string
  item_id: number | null
  seq: number | null
  item_name: string | null
  quantity: string | null
  unit: string | null
  proposed_vendor_amount: number | null
  invoice_no: string | null
  receipt_no: string | null
  item_note: string | null
}

/** 月報摘要 KPI */
export interface ClaimReportSummary {
  label?: string
  order_count: number
  total_subtotal: number
  total_tax: number
  total_payable: number
  item_count: number
  dept_count: number
  avg_payable: number
  top_order: string | null
  top_dept_by_count: string | null
  top_dept_by_amount: string | null
  dept_summary: Array<{
    department_display: string
    order_count: number
    total_payable: number
  }>
}

/** 部門統計 */
export interface ClaimDeptStat {
  department_display: string
  order_count: number
  total_subtotal: number
  total_tax: number
  total_payable: number
}

/** 同步狀態 */
export interface ClaimSyncStatus {
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
  per_page: number
  items: T[]
}

// ── API Functions ──────────────────────────────────────────────────────────────

/** 請款單清單（訂單級，分頁） */
export const getClaimOrders = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_subject?: string
  payment_type?: string
  payment_date_from?: string
  payment_date_to?: string
  status?: string
  keyword?: string
  page?: number
  per_page?: number
  company?: string
}) =>
  apiClient.get<PaginatedResponse<ClaimOrder>>(
    `${BASE}/approved/orders`,
    { params },
  )

/** 單筆請款單完整資料（含品項） */
export const getClaimOrderDetail = (orderId: number) =>
  apiClient.get<ClaimOrderDetail>(`${BASE}/approved/orders/${orderId}`)

/** 月報明細（品項級，分頁） */
export const getClaimMonthlyItems = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_subject?: string
  payment_type?: string
  payment_date_from?: string
  payment_date_to?: string
  q?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<ClaimReportItem>>(
    `${BASE}/approved/monthly`,
    { params },
  )

/** KPI 摘要 */
export const getClaimSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_subject?: string
  payment_type?: string
}) =>
  apiClient.get<ClaimReportSummary>(`${BASE}/approved/summary`, { params })

/** 部門統計 */
export const getClaimDepartments = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  account_subject?: string
  payment_type?: string
}) =>
  apiClient.get<ClaimDeptStat[]>(`${BASE}/approved/departments`, { params })

/** 有資料的年月清單 */
export const getClaimAvailableMonths = (company = '樂群') =>
  apiClient.get<string[]>(`${BASE}/approved/available-months`, { params: { company } })

/** 部門清單（下拉） */
export const getClaimDeptList = () =>
  apiClient.get<string[]>(`${BASE}/config/departments`)

/** 付款種類清單（下拉） */
export const getClaimPaymentTypes = () =>
  apiClient.get<string[]>(`${BASE}/config/payment-types`)

/** 會科清單（下拉） */
export const getClaimAccountSubjects = (company = '樂群') =>
  apiClient.get<string[]>(`${BASE}/config/account-subjects`, { params: { company } })

/** Excel 匯出（blob） */
export const exportClaimReport = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_subject?: string
  payment_type?: string
}) =>
  apiClient.get(`${BASE}/approved/export`, {
    params,
    responseType: 'blob',
  })

/** 觸發同步 */
export const triggerClaimSync = (fullResync = false) =>
  apiClient.post<{ message: string; task: string }>(
    `${BASE}/sync`,
    null,
    { params: { full_resync: fullResync } },
  )

/** 同步狀態 */
export const getClaimSyncStatus = () =>
  apiClient.get<ClaimSyncStatus>(`${BASE}/sync/status`)

// ── 資料異常稽核 ───────────────────────────────────────────────────────────────

import type {
  AuditAnomaly,
  AuditSummary,
} from '@/api/purchaseReport'

export type { AuditAnomaly, AuditSummary }

/** 請款資料異常列表（分頁） */
export const getClaimAuditAnomalies = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  company?: string
  rule_code?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<AuditAnomaly>>(
    `${BASE}/audit/anomalies`,
    { params },
  )

/** 請款資料異常 KPI 摘要 */
export const getClaimAuditSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  company?: string
}) =>
  apiClient.get<AuditSummary>(`${BASE}/audit/summary`, { params })
