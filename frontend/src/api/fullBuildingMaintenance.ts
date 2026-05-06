import apiClient from '@/api/client'
import type {
  PMBatchListItem, PMBatchDetail, PMStats, PMTaskHistory,
  PMPeriodStats, PMYearMatrix,
} from '@/types/periodicMaintenance'

const BASE = '/mall/full-building-maintenance'

/** 全棟例行維護批次清單 */
export async function fetchFullBldgPMBatches(year?: string): Promise<PMBatchListItem[]> {
  const params: Record<string, string> = {}
  if (year) params.year = year
  const res = await apiClient.get<PMBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

/** 單筆批次完整資料（含項目 + KPI） */
export async function fetchFullBldgPMBatchDetail(
  batchId: string,
  opts?: {
    currentMonthOnly?: boolean
    category?: string
    status?: string
  },
): Promise<PMBatchDetail> {
  const params: Record<string, string | boolean> = {}
  if (opts?.currentMonthOnly) params.current_month_only = true
  if (opts?.category) params.category = opts.category
  if (opts?.status) params.status = opts.status
  const res = await apiClient.get<PMBatchDetail>(`${BASE}/batches/${batchId}`, { params })
  return res.data
}

/** 全站統計（Dashboard 資料來源） */
export async function fetchFullBldgPMStats(year?: string, month?: number): Promise<PMStats> {
  const params: Record<string, string | number> = {}
  if (year)  params.year  = year
  if (month) params.month = month
  const res = await apiClient.get<PMStats>(`${BASE}/stats`, { params })
  return res.data
}

/** 手動觸發 Ragic 同步 */
export async function syncFullBldgPMFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

/** 依保養項目名稱查詢近 N 個月執行歷史 */
export async function fetchFullBldgPMTaskHistory(
  taskName: string,
  months = 12,
): Promise<PMTaskHistory> {
  const res = await apiClient.get<PMTaskHistory>(`${BASE}/items/task-history`, {
    params: { task_name: taskName, months },
  })
  return res.data
}

/** 週期統計（月/季/年） */
export async function fetchFullBldgPMPeriodStats(params: {
  period_type: 'month' | 'quarter' | 'year'
  year?: number
  month?: number
  quarter?: number
  frequency_type?: 'monthly' | 'quarterly' | 'yearly'
}): Promise<PMPeriodStats> {
  const res = await apiClient.get<PMPeriodStats>(`${BASE}/period-stats`, { params })
  return res.data
}

/** 全年 12 個月矩陣統計 */
export async function fetchFullBldgPMYearMatrix(
  year?: number,
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<PMYearMatrix> {
  const params: Record<string, number | string> = {}
  if (year) params.year = year
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<PMYearMatrix>(`${BASE}/period-stats/year-matrix`, { params })
  return res.data
}


/** 月曆格（類別 × 日） */
export async function fetchFullBldgPMCalendar(
  year: number,
  month: number,
): Promise<{ year: number; month: number; max_day: number; rows: import('@/components/MonthlyCalendarGrid').CalendarRow[] }> {
  const res = await apiClient.get(`${BASE}/calendar`, { params: { year, month } })
  return res.data
}

// ── 矩陣格明細（數字點擊查詢）────────────────────────────────────────────────
export type PMMatrixMetric = 'prev_carry_over' | 'prev_resolved' | 'period_total' | 'period_completed'

export interface FullBldgPMMatrixItem {
  ragic_id:            string
  batch_ragic_id:      string
  period_month:        string
  category:            string
  task_name:           string
  frequency:           string
  scheduled_date_full: string
  end_time:            string
  status:              string
  executor_name:       string
  result_note:         string
  abnormal_flag:       boolean
  abnormal_note:       string
  ragic_link:          string
}

export interface FullBldgPMMatrixItemsResponse {
  total: number
  items: FullBldgPMMatrixItem[]
}

export async function fetchFullBldgPMMatrixItems(params: {
  year: number
  month: number
  metric: PMMatrixMetric
  frequency_type?: string
}): Promise<FullBldgPMMatrixItemsResponse> {
  const res = await apiClient.get<FullBldgPMMatrixItemsResponse>(
    `${BASE}/period-stats/year-matrix/items`, { params }
  )
  return res.data
}

// ── 保養項目目錄（依頻率分類）────────────────────────────────────────────────
export interface FullBldgPMCatalogItem {
  seq_no:            number
  category:          string
  frequency:         string
  task_name:         string
  location:          string
  estimated_minutes: number
  exec_months_raw:   string
}

export interface FullBldgPMCatalogResponse {
  total: number
  items: FullBldgPMCatalogItem[]
}


export async function fetchFullBldgPMCatalog(
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<FullBldgPMCatalogResponse> {
  const params: Record<string, string> = {}
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<FullBldgPMCatalogResponse>(`${BASE}/items/catalog`, { params })
  return res.data
}
