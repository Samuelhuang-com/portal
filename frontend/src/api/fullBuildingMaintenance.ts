import apiClient from '@/api/client'
import type {
  PMBatchListItem, PMBatchDetail, PMStats, PMTaskHistory,
  PMPeriodStats, PMYearMatrix, PMItem,
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

// ── 維修記錄明細（Sheet28 巢狀子表格，2026-07-13 新增）───────────────────────
export interface PMWorklogItem {
  ragic_id:      string
  item_ragic_id: string
  seq_no:        number
  repair_note:   string
  start_time:    string
  end_time:      string
  staff_name:    string
}

/** 單一項目維修記錄明細 */
export async function fetchFullBldgPMItemWorklogs(itemRagicId: string): Promise<PMWorklogItem[]> {
  const res = await apiClient.get<PMWorklogItem[]>(`${BASE}/items/${itemRagicId}/worklogs`)
  return res.data
}

// ── 附圖（Sheet28「圖片上傳」欄位，2026-07-13 新增，遵循全站 db-images 端點慣例）──────
export interface PMImageItem {
  url:      string
  filename: string
}

/** 單一項目附圖（DB 優先，缺資料時後端會即時向 Ragic 補抓一次） */
export async function fetchFullBldgPMItemImages(itemRagicId: string): Promise<PMImageItem[]> {
  const res = await apiClient.get<PMImageItem[]>(`${BASE}/items/${itemRagicId}/db-images`)
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

// ── 每日巡檢表（依排定日期篩選當日保養項目，來源 Sheet28，2026-07-13 由整棟巡檢改版）──
export interface PMDailyFormSummary {
  total:           number
  completed:       number
  overdue:         number
  abnormal:        number
  planned_minutes: number
  actual_minutes:  number
}

export type PMDailyFormView = 'day' | 'month'

export interface PMDailyFormResponse {
  view:            PMDailyFormView
  inspection_date: string   // YYYY/MM/DD（view=month 時為該月 1 號）
  period_month:    string   // YYYY/MM
  batch_ragic_id:  string | null
  rows:            PMItem[]
  summary:         PMDailyFormSummary
}

/** 每日巡檢表：依排定日期篩選當日保養項目，或 view='month' 檢視整月 */
export async function fetchFullBldgPMDailyForm(
  inspectionDate?: string,
  view: PMDailyFormView = 'day',
): Promise<PMDailyFormResponse> {
  const params: Record<string, string> = { view }
  if (inspectionDate) params.inspection_date = inspectionDate
  const res = await apiClient.get<PMDailyFormResponse>(`${BASE}/daily-form`, { params })
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

// ══════════════════════════════════════════════════════════════════════════════
// 排程管理（full_bldg_pm_schedule）API
// ══════════════════════════════════════════════════════════════════════════════

export interface FullBldgPMScheduleItem {
  id:               number
  year_month:       string
  item_ragic_id:    string
  category:         string
  task_name:        string
  location:         string
  frequency:        string
  estimated_minutes: number
  scheduled_date:   string
  executor_name:    string
  schedule_source:  string   // 'auto' | 'manual'
  start_time:       string
  end_time:         string
  is_completed:     boolean
  result_note:      string
  abnormal_flag:    boolean
  abnormal_note:    string
  portal_edited_at: string | null
  created_at:       string
  updated_at:       string
  status:    string   // 動態計算：completed / in_progress / scheduled / unscheduled / overdue
  ragic_url: string   // 對應月份批次的 Ragic 連結（後端動態注入）
}

export interface FullBldgPMScheduleKpi {
  total:               number
  unscheduled:         number
  scheduled:           number
  in_progress:         number
  completed:           number
  overdue:             number
  abnormal:            number
  should_do_not_done:  number
  completion_rate:     number
}

export interface FullBldgPMScheduleListResponse {
  year_month:         string
  total:              number
  should_do_not_done: number
  items:              FullBldgPMScheduleItem[]
}

export interface FullBldgPMScheduleGenerateResult {
  year_month:              string
  generated:               number
  updated:                 number
  skipped_completed:       number
  skipped_edited:          number
  skipped_non_month:       number
  skipped_no_frequency:    number
  errors:                  string[]
}

export interface FullBldgPMScheduleOverdueResponse {
  total:           number
  months_affected: string[]
  items:           (FullBldgPMScheduleItem & { overdue_days: number })[]
}

export interface FullBldgPMScheduleMatrixCell {
  month:          number
  status:         string
  schedule_id:    number | null
  scheduled_date: string | null
}

export interface FullBldgPMScheduleMatrixRow {
  item_ragic_id: string
  category:      string
  task_name:     string
  location:      string
  frequency:     string
  cells:         FullBldgPMScheduleMatrixCell[]
}

export interface FullBldgPMScheduleAnnualMatrix {
  year:             number
  rows:             FullBldgPMScheduleMatrixRow[]
  month_batch_urls: Record<string, string>   // { "5": "https://...", "6": "https://..." }
  summary: {
    total_items:     number
    total_cells:     number
    completed_count: number
    completion_rate: number
  }
}

export interface FullBldgPMScheduleUpdatePayload {
  scheduled_date?: string
  executor_name?:  string
  start_time?:     string
  end_time?:       string
  is_completed?:   boolean
  result_note?:    string
  abnormal_flag?:  boolean
  abnormal_note?:  string
}

/** 排程列表（含 should_do_not_done） */
export async function getFullBldgScheduleList(params: {
  year_month?: string
  category?:   string
  status?:     string
}): Promise<FullBldgPMScheduleListResponse> {
  const res = await apiClient.get<FullBldgPMScheduleListResponse>(`${BASE}/schedule`, { params })
  return res.data
}

/** 排程 KPI（9 個指標） */
export async function getFullBldgScheduleKpi(year_month?: string): Promise<FullBldgPMScheduleKpi> {
  const params: Record<string, string> = {}
  if (year_month) params.year_month = year_month
  const res = await apiClient.get<FullBldgPMScheduleKpi>(`${BASE}/schedule/kpi`, { params })
  return res.data
}

/** 跨月逾期未執行清單 */
export async function getFullBldgOverdueSchedule(): Promise<FullBldgPMScheduleOverdueResponse> {
  const res = await apiClient.get<FullBldgPMScheduleOverdueResponse>(`${BASE}/schedule/overdue`)
  return res.data
}

/** 更新單筆排程 */
export async function patchFullBldgSchedule(
  id: number,
  payload: FullBldgPMScheduleUpdatePayload,
): Promise<FullBldgPMScheduleItem> {
  const res = await apiClient.patch<FullBldgPMScheduleItem>(`${BASE}/schedule/${id}`, payload)
  return res.data
}

/** 產生指定月份排程 */
export async function postGenerateFullBldgSchedule(
  year: number,
  month: number,
): Promise<FullBldgPMScheduleGenerateResult> {
  const res = await apiClient.post<FullBldgPMScheduleGenerateResult>(
    `${BASE}/schedule/generate`,
    null,
    { params: { year, month } },
  )
  return res.data
}

/** 年度計劃矩陣 */
export async function getFullBldgAnnualMatrix(
  year: number,
  category?: string,
): Promise<FullBldgPMScheduleAnnualMatrix> {
  const params: Record<string, string | number> = { year }
  if (category) params.category = category
  const res = await apiClient.get<FullBldgPMScheduleAnnualMatrix>(`${BASE}/schedule/annual-matrix`, { params })
  return res.data
}
