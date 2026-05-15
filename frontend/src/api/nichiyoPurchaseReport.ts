/**
 * 日曜核准請購單月報表 API
 * 所有 nichiyo-purchase-report 相關 API 呼叫的封裝函數
 */
import apiClient from '@/api/client'

const BASE = '/nichiyo-purchase-report'

// ── Types ─────────────────────────────────────────────────────────────────────

/** 月報明細（品項級，一筆 = 一個品項） */
export interface NichiyoPurchaseReportItem {
  // 主單欄位（每列重複）
  order_id: number
  department_display: string
  purchase_no: string
  account_category: string
  request_date: string | null
  approved_date: string | null
  applicant: string
  description: string
  amount: number | null         // 全案小計（未稅）
  amount_tax: number | null     // 營業稅
  amount_total: number | null   // 含稅總計
  vendor1: string
  vendor2: string
  vendor3: string
  // 品項欄位
  item_id: number | null
  seq: number | null
  product_name: string
  qty: number | null
  unit: string
  selected_vendor: string
  selected_unit_price: number | null
  selected_amount: number | null
  is_confirmed: boolean | null
  item_remark: string
}

/** 月報摘要 KPI */
export interface NichiyoPurchaseReportSummary {
  order_count: number
  total_amount: number
  total_tax: number
  item_count: number
  dept_count: number
  avg_amount: number
  rej_count: number
  top_order: string | null
  top_dept_by_count: string | null
  top_dept_by_amount: string | null
  dept_summary: Array<{
    department_display: string
    order_count: number
    total_amount: number
    total_tax: number
  }>
}

/** 部門統計 */
export interface NichiyoPurchaseDeptStat {
  department_display: string
  order_count: number
  total_amount: number
  total_tax: number
}

/** 同步狀態 */
export interface NichiyoPurchaseSyncStatus {
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

// ── 請購單主單 / Detail ────────────────────────────────────────────────────────

/** 請購單主單（訂單級） */
export interface NichiyoPurchaseOrder {
  id: number
  purchase_no: string
  department_display: string
  account_category: string | null
  applicant: string | null
  description: string | null
  amount: number | null
  amount_tax: number | null
  amount_total: number | null
  status: string            // 'F' | 'N' | 'REJ'
  vendor1: string | null
  vendor2: string | null
  vendor3: string | null
  remark: string | null
  request_date: string | null
  approved_date: string | null
  last_updated_at: string | null
  detail_synced: boolean
  ragic_sheet_path: string
  ragic_record_id: string
  ragic_url: string
  selected_vendors: string
}

/** 請購單品項（Detail Drawer 使用） */
export interface NichiyoPurchaseOrderItem {
  id: number
  seq: number
  product_name: string | null
  qty: string | null
  unit: string | null
  vendor1_price: number | null
  vendor2_price: number | null
  vendor3_price: number | null
  selected_vendor: string | null
  selected_unit_price: number | null
  selected_amount: number | null
  is_confirmed: boolean | null
  item_remark: string | null
}

/** 請購單完整詳情（含品項） */
export interface NichiyoPurchaseOrderDetail {
  order: NichiyoPurchaseOrder
  items: NichiyoPurchaseOrderItem[]
}

// ── 稽核 ──────────────────────────────────────────────────────────────────────

export interface NichiyoAuditAnomaly {
  source: 'nichiyo_purchase'
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

export interface NichiyoAuditRuleStat {
  rule_code: string
  rule_name: string
  severity: 'high' | 'medium' | 'low'
  applies_to: string[]
  count: number
}

export interface NichiyoAuditSummary {
  total_anomalies: number
  total_orders: number
  by_rule: NichiyoAuditRuleStat[]
}

// ── API Functions ──────────────────────────────────────────────────────────────

/** 請購單主單清單（訂單級分頁） */
export const getNichiyoApprovedOrders = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
  status?: string
  keyword?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<NichiyoPurchaseOrder>>(
    `${BASE}/approved/orders`,
    { params },
  )

/** 單筆請購單完整資料（含品項） */
export const getNichiyoOrderDetail = (orderId: number) =>
  apiClient.get<NichiyoPurchaseOrderDetail>(`${BASE}/approved/orders/${orderId}`)

/** 月報明細（品項級，分頁） */
export const getNichiyoMonthlyItems = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
  q?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<NichiyoPurchaseReportItem>>(
    `${BASE}/approved/monthly`,
    { params },
  )

/** 月報 KPI 摘要 */
export const getNichiyoSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
}) =>
  apiClient.get<NichiyoPurchaseReportSummary>(`${BASE}/approved/summary`, { params })

/** 部門統計 */
export const getNichiyoDepartments = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  account_category?: string
}) =>
  apiClient.get<NichiyoPurchaseDeptStat[]>(`${BASE}/approved/departments`, { params })

/** Excel 匯出（blob） */
export const exportNichiyoPurchaseReport = (params: {
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
export const getNichiyoAvailableMonths = () =>
  apiClient.get<string[]>(`${BASE}/approved/available-months`)

/** 部門清單（下拉選項） */
export const getNichiyoDeptList = () =>
  apiClient.get<string[]>(`${BASE}/config/departments`)

/** 會科清單（下拉選項） */
export const getNichiyoAccountCategories = () =>
  apiClient.get<string[]>(`${BASE}/config/account-categories`)

/** 觸發同步 */
export const triggerNichiyoSync = (fullResync = false) =>
  apiClient.post<{ message: string; task: string }>(
    `${BASE}/sync`,
    null,
    { params: { full_resync: fullResync } },
  )

/** 同步狀態 */
export const getNichiyoSyncStatus = () =>
  apiClient.get<NichiyoPurchaseSyncStatus>(`${BASE}/sync/status`)

/** 資料異常列表（分頁） */
export const getNichiyoAuditAnomalies = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  rule_code?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<NichiyoAuditAnomaly>>(
    `${BASE}/audit/anomalies`,
    { params },
  )

/** 資料異常 KPI 摘要 */
export const getNichiyoAuditSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
}) =>
  apiClient.get<NichiyoAuditSummary>(`${BASE}/audit/summary`, { params })

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
