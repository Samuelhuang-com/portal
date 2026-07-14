import apiClient from '@/api/client'
import type {
  PMBatchListItem, PMBatchDetail, PMStats, PMItem, PMTaskHistory,
  PMPeriodStats, PMYearMatrix,
} from '@/types/periodicMaintenance'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'

// ── 月曆格資料型別 ────────────────────────────────────────────────────────────

export interface PMCalendarResponse {
  year:    number
  month:   number
  max_day: number
  rows:    CalendarRow[]
}

const BASE = '/periodic-maintenance'

/** 保養批次清單 */
export async function fetchPMBatches(year?: string): Promise<PMBatchListItem[]> {
  const params: Record<string, string> = {}
  if (year) params.year = year
  const res = await apiClient.get<PMBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

/** 單筆批次完整資料（含項目 + KPI） */
export async function fetchPMBatchDetail(
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
export async function fetchPMStats(year?: string, month?: number): Promise<PMStats> {
  const params: Record<string, string | number> = {}
  if (year)  params.year  = year
  if (month) params.month = month
  const res = await apiClient.get<PMStats>(`${BASE}/stats`, { params })
  return res.data
}

// updatePMItem 已停用（Portal 不提供編輯，資料全部來自 Ragic 同步）

/** 手動觸發 Ragic 同步 */
export async function syncPMFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

/** 週期統計（月 / 季 / 年） */
export async function fetchPMPeriodStats(params: {
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
export async function fetchPMYearMatrix(
  year?: number,
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<PMYearMatrix> {
  const params: Record<string, number | string> = {}
  if (year) params.year = year
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<PMYearMatrix>(`${BASE}/period-stats/year-matrix`, { params })
  return res.data
}

// ── 矩陣格明細（數字點擊查詢）────────────────────────────────────────────────
export type PMMatrixMetric = 'prev_carry_over' | 'prev_resolved' | 'period_total' | 'period_completed'

export interface PMMatrixItem {
  ragic_id:              string
  batch_ragic_id:        string
  period_month:          string
  category:              string
  task_name:             string
  frequency:             string
  scheduled_date_full:   string
  end_time:              string
  status:                string
  executor_name:         string
  result_note:           string
  abnormal_flag:         boolean
  abnormal_note:         string
  ragic_link:            string
}

export interface PMMatrixItemsResponse {
  total: number
  items: PMMatrixItem[]
}

export async function fetchPMMatrixItems(params: {
  year: number
  month: number     // 0 = 全年合計
  metric: PMMatrixMetric
  frequency_type?: string
}): Promise<PMMatrixItemsResponse> {
  const res = await apiClient.get<PMMatrixItemsResponse>(`${BASE}/period-stats/year-matrix/items`, { params })
  return res.data
}

/** 週期保養月曆格（類別 × 日期） */
export async function fetchPMCalendar(year: number, month: number): Promise<PMCalendarResponse> {
  const res = await apiClient.get<PMCalendarResponse>(`${BASE}/calendar`, { params: { year, month } })
  return res.data
}

// ── 保養項目目錄（依頻率分類）────────────────────────────────────────────────
export interface PMCatalogItem {
  seq_no:            number
  category:          string
  frequency:         string
  task_name:         string
  location:          string
  estimated_minutes: number
  exec_months_raw:   string
}

export interface PMCatalogResponse {
  total: number
  items: PMCatalogItem[]
}

export async function fetchPMCatalog(
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<PMCatalogResponse> {
  const params: Record<string, string> = {}
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<PMCatalogResponse>(`${BASE}/items/catalog`, { params })
  return res.data
}

/** 依保養項目名稱查詢近 N 個月執行歷史 */
export async function fetchPMTaskHistory(
  taskName: string,
  months = 12,
): Promise<PMTaskHistory> {
  const res = await apiClient.get<PMTaskHistory>(`${BASE}/items/task-history`, {
    params: { task_name: taskName, months },
  })
  return res.data
}

// ── 維修記錄明細（Sheet11 巢狀子表格，2026-07-14 同日追加，比照 mall_pm Sheet24）────
// 原始遷移評估誤判 Sheet 11 無巢狀子表格，實測記錄（277/477）證實存在，欄位與
// mall_pm 完全相同，比照補上。
export interface PMWorklogItem {
  ragic_id:      string
  item_ragic_id: string
  seq_no:        number
  repair_note:   string
  start_time:    string
  end_time:      string
  staff_name:    string
}

/** 單一項目維修記錄明細（來源 Ragic Sheet11 巢狀子表格） */
export async function fetchPMItemWorklogs(itemRagicId: string): Promise<PMWorklogItem[]> {
  const res = await apiClient.get<PMWorklogItem[]>(`${BASE}/items/${itemRagicId}/worklogs`)
  return res.data
}

// ── 附圖（Sheet11「圖片上傳」欄位，2026-07-14 新增，遵循全站 db-images 端點慣例）──────
export interface PMImageItem {
  url:      string
  filename: string
}

/** 單一項目附圖（DB 優先，缺資料時後端會即時向 Ragic 補抓一次） */
export async function fetchPMItemImages(itemRagicId: string): Promise<PMImageItem[]> {
  const res = await apiClient.get<PMImageItem[]>(`${BASE}/items/${itemRagicId}/db-images`)
  return res.data
}

// ════════════════════════════════════════════════════════════════════════════
// 排程管理（pm_schedule）API
// ════════════════════════════════════════════════════════════════════════════

import type {
  PMScheduleListResponse,
  PMScheduleKPI,
  PMScheduleGenerateResult,
  PMScheduleOverdueResponse,
  PMScheduleAnnualMatrix,
  PMScheduleItem,
} from '@/types/periodicMaintenance'

/** 產生指定月份排程（防重複） */
export async function generatePMSchedule(
  year: number,
  month: number,
): Promise<PMScheduleGenerateResult> {
  const res = await apiClient.post<PMScheduleGenerateResult>(
    `${BASE}/schedule/generate`,
    null,
    { params: { year, month } },
  )
  return res.data
}

/** 查詢排程明細列表 */
export async function fetchPMSchedule(
  yearMonth?: string,
  category?: string,
  status?: string,
): Promise<PMScheduleListResponse> {
  const params: Record<string, string> = {}
  if (yearMonth) params.year_month = yearMonth
  if (category)  params.category  = category
  if (status)    params.status    = status
  const res = await apiClient.get<PMScheduleListResponse>(`${BASE}/schedule`, { params })
  return res.data
}

/** 排程 KPI */
export async function fetchPMScheduleKPI(yearMonth?: string): Promise<PMScheduleKPI> {
  const params: Record<string, string> = {}
  if (yearMonth) params.year_month = yearMonth
  const res = await apiClient.get<PMScheduleKPI>(`${BASE}/schedule/kpi`, { params })
  return res.data
}

/** 跨月逾期清單 */
export async function fetchPMOverdueSchedule(
  beforeDate?: string,
): Promise<PMScheduleOverdueResponse> {
  const params: Record<string, string> = {}
  if (beforeDate) params.before_date = beforeDate
  const res = await apiClient.get<PMScheduleOverdueResponse>(`${BASE}/schedule/overdue`, { params })
  return res.data
}

/** 年度計劃矩陣 */
export async function fetchPMAnnualMatrix(
  year: number,
  category?: string,
): Promise<PMScheduleAnnualMatrix> {
  const params: Record<string, string | number> = { year }
  if (category) params.category = category
  const res = await apiClient.get<PMScheduleAnnualMatrix>(`${BASE}/schedule/annual-matrix`, { params })
  return res.data
}

/** 人工調整排程明細 */
export async function updatePMSchedule(
  id: number,
  data: Partial<Pick<PMScheduleItem,
    'scheduled_date' | 'executor_name' | 'start_time' | 'end_time' |
    'is_completed' | 'result_note' | 'abnormal_flag' | 'abnormal_note'
  >>,
): Promise<PMScheduleItem> {
  const res = await apiClient.patch<PMScheduleItem>(`${BASE}/schedule/${id}`, data)
  return res.data
}
