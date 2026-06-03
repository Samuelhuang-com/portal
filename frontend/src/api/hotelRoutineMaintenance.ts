import apiClient from '@/api/client'
import type {
  HotelRoutinePMBatchListItem, HotelRoutinePMBatchDetail, HotelRoutinePMStats,
  HotelRoutinePMItem, HotelRoutinePMTaskHistory,
  HotelRoutinePMPeriodStats, HotelRoutinePMYearMatrix,
} from '@/types/hotelRoutineMaintenance'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'

// ── 月曆格資料型別 ────────────────────────────────────────────────────────────

export interface HotelRoutinePMCalendarResponse {
  year:    number
  month:   number
  max_day: number
  rows:    CalendarRow[]
}

const BASE = '/hotel/routine-maintenance'

/** 保養批次清單 */
export async function fetchHotelRoutinePMBatches(year?: string): Promise<HotelRoutinePMBatchListItem[]> {
  const params: Record<string, string> = {}
  if (year) params.year = year
  const res = await apiClient.get<HotelRoutinePMBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

/** 單筆批次完整資料（含項目 + KPI） */
export async function fetchHotelRoutinePMBatchDetail(
  batchId: string,
  opts?: {
    currentMonthOnly?: boolean
    category?: string
    status?: string
  },
): Promise<HotelRoutinePMBatchDetail> {
  const params: Record<string, string | boolean> = {}
  if (opts?.currentMonthOnly) params.current_month_only = true
  if (opts?.category) params.category = opts.category
  if (opts?.status) params.status = opts.status
  const res = await apiClient.get<HotelRoutinePMBatchDetail>(`${BASE}/batches/${batchId}`, { params })
  return res.data
}

/** 全站統計（Dashboard 資料來源） */
export async function fetchHotelRoutinePMStats(year?: string, month?: number): Promise<HotelRoutinePMStats> {
  const params: Record<string, string | number> = {}
  if (year)  params.year  = year
  if (month) params.month = month
  const res = await apiClient.get<HotelRoutinePMStats>(`${BASE}/stats`, { params })
  return res.data
}

// updateHotelRoutinePMItem 已停用（Portal 不提供編輯，資料全部來自 Ragic 同步）

/** 手動觸發 Ragic 同步 */
export async function syncHotelRoutinePMFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

/** 週期統計（月 / 季 / 年） */
export async function fetchHotelRoutinePMPeriodStats(params: {
  period_type: 'month' | 'quarter' | 'year'
  year?: number
  month?: number
  quarter?: number
  frequency_type?: 'monthly' | 'quarterly' | 'yearly'
}): Promise<HotelRoutinePMPeriodStats> {
  const res = await apiClient.get<HotelRoutinePMPeriodStats>(`${BASE}/period-stats`, { params })
  return res.data
}

/** 全年 12 個月矩陣統計 */
export async function fetchHotelRoutinePMYearMatrix(
  year?: number,
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<HotelRoutinePMYearMatrix> {
  const params: Record<string, number | string> = {}
  if (year) params.year = year
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<HotelRoutinePMYearMatrix>(`${BASE}/period-stats/year-matrix`, { params })
  return res.data
}

// ── 矩陣格明細（數字點擊查詢）────────────────────────────────────────────────
export type HotelRoutinePMMatrixMetric = 'prev_carry_over' | 'prev_resolved' | 'period_total' | 'period_completed'

export interface HotelRoutinePMMatrixItem {
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

export interface HotelRoutinePMMatrixItemsResponse {
  total: number
  items: HotelRoutinePMMatrixItem[]
}

export async function fetchHotelRoutinePMMatrixItems(params: {
  year: number
  month: number     // 0 = 全年合計
  metric: HotelRoutinePMMatrixMetric
  frequency_type?: string
}): Promise<HotelRoutinePMMatrixItemsResponse> {
  const res = await apiClient.get<HotelRoutinePMMatrixItemsResponse>(`${BASE}/period-stats/year-matrix/items`, { params })
  return res.data
}

/** 例行維護月曆格（類別 × 日期） */
export async function fetchHotelRoutinePMCalendar(year: number, month: number): Promise<HotelRoutinePMCalendarResponse> {
  const res = await apiClient.get<HotelRoutinePMCalendarResponse>(`${BASE}/calendar`, { params: { year, month } })
  return res.data
}

// ── 保養項目目錄（依頻率分類）────────────────────────────────────────────────
export interface HotelRoutinePMCatalogItem {
  seq_no:            number
  category:          string
  frequency:         string
  task_name:         string
  location:          string
  estimated_minutes: number
  exec_months_raw:   string
}

export interface HotelRoutinePMCatalogResponse {
  total: number
  items: HotelRoutinePMCatalogItem[]
}

export async function fetchHotelRoutinePMCatalog(
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<HotelRoutinePMCatalogResponse> {
  const params: Record<string, string> = {}
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<HotelRoutinePMCatalogResponse>(`${BASE}/items/catalog`, { params })
  return res.data
}

/** 依保養項目名稱查詢近 N 個月執行歷史 */
export async function fetchHotelRoutinePMTaskHistory(
  taskName: string,
  months = 12,
): Promise<HotelRoutinePMTaskHistory> {
  const res = await apiClient.get<HotelRoutinePMTaskHistory>(`${BASE}/items/task-history`, {
    params: { task_name: taskName, months },
  })
  return res.data
}

// ════════════════════════════════════════════════════════════════════════════
// 排程管理（hotel_routine_pm_schedule）API
// ════════════════════════════════════════════════════════════════════════════

import type {
  HotelRoutinePMScheduleListResponse,
  HotelRoutinePMScheduleKPI,
  HotelRoutinePMScheduleGenerateResult,
  HotelRoutinePMScheduleOverdueResponse,
  HotelRoutinePMScheduleAnnualMatrix,
  HotelRoutinePMScheduleItem,
} from '@/types/hotelRoutineMaintenance'

/** 產生指定月份排程（防重複） */
export async function generateHotelRoutinePMSchedule(
  year: number,
  month: number,
): Promise<HotelRoutinePMScheduleGenerateResult> {
  const res = await apiClient.post<HotelRoutinePMScheduleGenerateResult>(
    `${BASE}/schedule/generate`,
    null,
    { params: { year, month } },
  )
  return res.data
}

/** 查詢排程明細列表 */
export async function fetchHotelRoutinePMSchedule(
  yearMonth?: string,
  category?: string,
  status?: string,
): Promise<HotelRoutinePMScheduleListResponse> {
  const params: Record<string, string> = {}
  if (yearMonth) params.year_month = yearMonth
  if (category)  params.category  = category
  if (status)    params.status    = status
  const res = await apiClient.get<HotelRoutinePMScheduleListResponse>(`${BASE}/schedule`, { params })
  return res.data
}

/** 排程 KPI */
export async function fetchHotelRoutinePMScheduleKPI(yearMonth?: string): Promise<HotelRoutinePMScheduleKPI> {
  const params: Record<string, string> = {}
  if (yearMonth) params.year_month = yearMonth
  const res = await apiClient.get<HotelRoutinePMScheduleKPI>(`${BASE}/schedule/kpi`, { params })
  return res.data
}

/** 跨月逾期清單 */
export async function fetchHotelRoutinePMOverdueSchedule(
  beforeDate?: string,
): Promise<HotelRoutinePMScheduleOverdueResponse> {
  const params: Record<string, string> = {}
  if (beforeDate) params.before_date = beforeDate
  const res = await apiClient.get<HotelRoutinePMScheduleOverdueResponse>(`${BASE}/schedule/overdue`, { params })
  return res.data
}

/** 年度計劃矩陣 */
export async function fetchHotelRoutinePMAnnualMatrix(
  year: number,
  category?: string,
): Promise<HotelRoutinePMScheduleAnnualMatrix> {
  const params: Record<string, string | number> = { year }
  if (category) params.category = category
  const res = await apiClient.get<HotelRoutinePMScheduleAnnualMatrix>(`${BASE}/schedule/annual-matrix`, { params })
  return res.data
}

/** 人工調整排程明細 */
export async function updateHotelRoutinePMSchedule(
  id: number,
  data: Partial<Pick<HotelRoutinePMScheduleItem,
    'scheduled_date' | 'executor_name' | 'start_time' | 'end_time' |
    'is_completed' | 'result_note' | 'abnormal_flag' | 'abnormal_note'
  >>,
): Promise<HotelRoutinePMScheduleItem> {
  const res = await apiClient.patch<HotelRoutinePMScheduleItem>(`${BASE}/schedule/${id}`, data)
  return res.data
}
