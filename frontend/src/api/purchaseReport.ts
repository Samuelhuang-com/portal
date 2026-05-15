/**
 * 核准請購單月報表 API
 * 所有 purchase-report 相關 API 呼叫的封裝函數
 */
import apiClient from '@/api/client'

const BASE = '/purchase-report'

// ── Types ─────────────────────────────────────────────────────────────────────

/** 月報明細（品項級，一筆 = 一個品項） */
export interface PurchaseReportItem {
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
export interface PurchaseReportSummary {
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
export interface PurchaseDeptStat {
  department_display: string
  order_count: number
  total_amount: number
  total_tax: number
}

/** 同步狀態 */
export interface PurchaseSyncStatus {
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

// ── API Functions ──────────────────────────────────────────────────────────────

/** 月報明細（品項級，分頁） */
export const getPurchaseMonthlyItems = (params: {
  year_month?: string          // e.g. "2025-04"
  year_month_from?: string     // YYYY-MM 區間起
  year_month_to?: string       // YYYY-MM 區間迄
  department?: string
  account_category?: string
  q?: string                   // 全文搜尋關鍵字（後端 Query param 名稱: q）
  page?: number
  per_page?: number            // ← 後端 Query 參數名稱
}) =>
  apiClient.get<PaginatedResponse<PurchaseReportItem>>(
    `${BASE}/approved/monthly`,
    { params },
  )

/** 月報 KPI 摘要 */
export const getPurchaseSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
}) =>
  apiClient.get<PurchaseReportSummary>(`${BASE}/approved/summary`, { params })

/** 部門統計 */
export const getPurchaseDepartments = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  account_category?: string
}) =>
  apiClient.get<PurchaseDeptStat[]>(`${BASE}/approved/departments`, { params })

/** 部門清單（下拉選項） */
export const getPurchaseDeptList = () =>
  apiClient.get<string[]>(`${BASE}/config/departments`)

/** 會科清單（下拉選項） */
export const getPurchaseAccountCategories = (company = '樂群') =>
  apiClient.get<string[]>(`${BASE}/config/account-categories`, { params: { company } })

/** Excel 匯出（blob） */
export const exportPurchaseReport = (params: {
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

/** 觸發同步 */
export const triggerPurchaseSync = (fullResync = false) =>
  apiClient.post<{ message: string; task: string }>(
    `${BASE}/sync`,
    null,
    { params: { full_resync: fullResync } },
  )

/** 同步狀態 */
export const getPurchaseSyncStatus = () =>
  apiClient.get<PurchaseSyncStatus>(`${BASE}/sync/status`)

/** 有核准資料的年月清單（降冪，供 DatePicker 預設最新月份） */
export const getPurchaseAvailableMonths = (company = '樂群') =>
  apiClient.get<string[]>(`${BASE}/approved/available-months`, { params: { company } })

// ── 請購單清單 / Detail ────────────────────────────────────────────────────────

/** 請購單主單（訂單級，對應 Ragic list_path 清單視圖） */
export interface PurchaseOrder {
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
  selected_vendors: string   // 品項層擬定廠商彙整（去重，" / " 分隔）
}

/** 請購單品項（Detail Drawer 使用） */
export interface PurchaseOrderItem {
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
export interface PurchaseOrderDetail {
  order: PurchaseOrder
  items: PurchaseOrderItem[]
}

/** 請購單清單（訂單級分頁） */
export const getApprovedOrders = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  account_category?: string
  status?: string
  keyword?: string
  page?: number
  per_page?: number
  company?: string
}) =>
  apiClient.get<PaginatedResponse<PurchaseOrder>>(
    `${BASE}/approved/orders`,
    { params },
  )

/** 單筆請購單完整資料（含品項） */
export const getApprovedOrderDetail = (orderId: number) =>
  apiClient.get<PurchaseOrderDetail>(`${BASE}/approved/orders/${orderId}`)

// ── 資料異常稽核 ───────────────────────────────────────────────────────────────

/** 單筆異常記錄 */
export interface AuditAnomaly {
  source: 'purchase' | 'claim'
  order_id: number
  doc_no: string
  department: string
  approved_date: string | null
  rule_code: string          // R01–R08
  rule_name: string
  severity: 'high' | 'medium' | 'low'
  detail: string
  ragic_url: string
}

/** 各規則計數 */
export interface AuditRuleStat {
  rule_code: string
  rule_name: string
  severity: 'high' | 'medium' | 'low'
  applies_to: string[]
  count: number
}

/** 稽核 KPI 摘要 */
export interface AuditSummary {
  total_anomalies: number
  total_orders: number
  by_rule: AuditRuleStat[]
}

/** 請購資料異常列表（分頁） */
export const getPurchaseAuditAnomalies = (params: {
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

/** 請購資料異常 KPI 摘要 */
export const getPurchaseAuditSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  department?: string
  company?: string
}) =>
  apiClient.get<AuditSummary>(`${BASE}/audit/summary`, { params })
