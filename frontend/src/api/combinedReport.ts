/**
 * 請購 + 請款 整合總表 API
 * 對應後端 /api/v1/combined-report 端點
 */
import apiClient from '@/api/client'

const BASE = '/combined-report'

// ── Types ─────────────────────────────────────────────────────────────────────

/** 合併清單一列（source_type 決定顏色）*/
export interface CombinedOrderRow {
  source_type: 'purchase' | 'claim'
  id: number
  department_display: string
  doc_no: string                    // 請購單號 or 請款單號
  account_label: string | null      // 會科
  apply_date: string | null
  approved_date: string | null
  applicant: string | null
  description: string | null        // 說明/事由
  amount: number | null             // 未稅
  tax: number | null
  total: number | null
  payable_amount: number | null
  payment_type: string | null       // 請款才有
  payee: string | null              // 請款才有
  status: string
  detail_synced: boolean
  last_updated_at: string | null
}

/** 合併摘要 KPI */
export interface CombinedSummary {
  label?: string
  year_month: string | null
  purchase: {
    order_count: number
    total_amount: number
    total_tax: number
  }
  claim: {
    order_count: number
    total_payable: number
    total_tax: number
  }
  combined: {
    order_count: number
    total_amount: number
    total_tax: number
  }
}

/** 部門雙色統計（請購藍 + 請款橙） */
export interface CombinedDeptStat {
  department_display: string
  purchase_count: number
  purchase_amount: number
  purchase_tax: number
  claim_count: number
  claim_payable: number
  claim_tax: number
}

/** 分頁回應 */
export interface PaginatedResponse<T> {
  total: number
  page: number
  per_page: number
  purchase_count: number
  claim_count: number
  items: T[]
}

// ── API Functions ──────────────────────────────────────────────────────────────

/** 合併清單（請購 + 請款，分頁） */
export const getCombinedOrders = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  company?: string
  department?: string
  source_type?: 'purchase' | 'claim'
  keyword?: string
  page?: number
  per_page?: number
}) =>
  apiClient.get<PaginatedResponse<CombinedOrderRow>>(
    `${BASE}/orders`,
    { params },
  )

/** 合計 KPI */
export const getCombinedSummary = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  company?: string
  department?: string
}) =>
  apiClient.get<CombinedSummary>(`${BASE}/summary`, { params })

/** 部門雙色統計 */
export const getCombinedDepartments = (params: {
  year_month?: string
  year_month_from?: string
  year_month_to?: string
  company?: string
}) =>
  apiClient.get<CombinedDeptStat[]>(`${BASE}/departments`, { params })
