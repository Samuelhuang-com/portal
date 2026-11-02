/**
 * 退件統計 API（規格 docs/SPEC_return_reject_stats.md §6）
 * 所有呼叫統一經由 @/api/client 的 apiClient，回傳 axios Promise（呼叫端用 .data）。
 */
import apiClient from '@/api/client'

const BASE = '/return-stats'

/**
 * axios 預設把陣列序列化為 `company[]=台中`，FastAPI 的 `Query(list)` 讀不到，篩選會被忽略。
 * 改用 `indexes: null` → `company=台中&company=台中｜業務部`。
 */
const LIST_PARAMS = { paramsSerializer: { indexes: null } } as const

export type Outcome = 'rejected' | 'withdrawn' | 'approved' | 'agreed' | 'pending' | 'unknown'

export interface RRFilters {
  companies: string[]
  departments: { company: string; dept: string }[]
  form_types: string[]
  form_names: string[]
  outcomes: { value: Outcome; label: string }[]
  rejection_approvers: string[]
  data_end: string | null
}

export interface RRQuery {
  company?: string[]
  dept?: string[]
  form_type?: string[]
  form_name?: string[]
  outcome?: string[]
  start?: string
  end?: string
  date_field?: 'apply' | 'last_sign'
  approver?: string
  rejection_approver?: string
  applicant?: string
  keyword?: string
}

export interface RRSummary {
  total: number
  counts: Record<Outcome, number>
  by_dept: ({ company: string; dept: string; total: number } & Record<Outcome, number>)[]
}

export interface RRListItem {
  id: number
  company: string
  form_type: string
  dept: string
  form_name: string
  ragic_record_id: string
  ragic_url: string
  applicant: string | null
  apply_date: string | null
  amount: number | null
  purpose: string | null
  ragic_status: string | null
  outcome: Outcome
  outcome_label: string
  outcome_reason: string
  rejection_note: string
  rejection_approver: string
  next_approver: string | null
  last_sign_date: string | null
}

export interface RRListResponse {
  total: number
  page: number
  page_size: number
  items: RRListItem[]
}

export interface RRStep {
  step_no: number
  role_field: string
  approver: string
  sign_date: string | null
  remark: string
  inferred_last: boolean
}

export interface RRDetail extends Omit<RRListItem, 'rejection_note' | 'amount'> {
  amount: number | null
  submitter: string | null
  steps: RRStep[]
  detail: Record<string, string>
}

export const getReturnStatsFilters = () =>
  apiClient.get<RRFilters>(`${BASE}/filters`)

export const getReturnStatsSummary = (params: RRQuery) =>
  apiClient.get<RRSummary>(`${BASE}/summary`, { params, ...LIST_PARAMS })

export const getReturnStatsRecords = (params: RRQuery & { page: number; page_size: number }) =>
  apiClient.get<RRListResponse>(`${BASE}/records`, { params, ...LIST_PARAMS })

export const getReturnStatsDetail = (id: number) =>
  apiClient.get<RRDetail>(`${BASE}/records/${id}`)

export const exportReturnStatsExcel = (params: RRQuery) =>
  apiClient.get<Blob>(`${BASE}/export`, { params, ...LIST_PARAMS, responseType: 'blob' })

export const runReturnStatsSync = () =>
  apiClient.post(`${BASE}/sync`)
