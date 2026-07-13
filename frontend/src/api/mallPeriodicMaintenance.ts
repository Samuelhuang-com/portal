import apiClient from '@/api/client'
import type {
  PMBatchListItem, PMBatchDetail, PMStats, PMTaskHistory,
  PMPeriodStats, PMYearMatrix,
} from '@/types/periodicMaintenance'

const BASE = '/mall/periodic-maintenance'

/** 商場保養批次清單 */
export async function fetchMallPMBatches(year?: string): Promise<PMBatchListItem[]> {
  const params: Record<string, string> = {}
  if (year) params.year = year
  const res = await apiClient.get<PMBatchListItem[]>(`${BASE}/batches`, { params })
  return res.data
}

/** 單筆批次完整資料（含項目 + KPI） */
export async function fetchMallPMBatchDetail(
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
export async function fetchMallPMStats(year?: string, month?: number): Promise<PMStats> {
  const params: Record<string, string | number> = {}
  if (year)  params.year  = year
  if (month) params.month = month
  const res = await apiClient.get<PMStats>(`${BASE}/stats`, { params })
  return res.data
}

/** 手動觸發 Ragic 同步 */
export async function syncMallPMFromRagic(): Promise<{ status: string; result: unknown }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

/** 依保養項目名稱查詢近 N 個月執行歷史 */
export async function fetchMallPMTaskHistory(
  taskName: string,
  months = 12,
): Promise<PMTaskHistory> {
  const res = await apiClient.get<PMTaskHistory>(`${BASE}/items/task-history`, {
    params: { task_name: taskName, months },
  })
  return res.data
}

// ── 維修記錄明細（Sheet24 巢狀子表格，2026-07-13 新增，比照 full_bldg_pm Sheet28）──────
export interface PMWorklogItem {
  ragic_id:      string
  item_ragic_id: string
  seq_no:        number
  repair_note:   string
  start_time:    string
  end_time:      string
  staff_name:    string
}

/** 單一項目維修記錄明細（來源 Ragic Sheet24 巢狀子表格） */
export async function fetchMallPMItemWorklogs(itemRagicId: string): Promise<PMWorklogItem[]> {
  const res = await apiClient.get<PMWorklogItem[]>(`${BASE}/items/${itemRagicId}/worklogs`)
  return res.data
}

// ── 附圖（Sheet24「圖片上傳」欄位，2026-07-13 新增，遵循全站 db-images 端點慣例）──────
export interface PMImageItem {
  url:      string
  filename: string
}

/** 單一項目附圖（DB 優先，缺資料時後端會即時向 Ragic 補抓一次） */
export async function fetchMallPMItemImages(itemRagicId: string): Promise<PMImageItem[]> {
  const res = await apiClient.get<PMImageItem[]>(`${BASE}/items/${itemRagicId}/db-images`)
  return res.data
}

/** 週期統計（月/季/年） */
export async function fetchMallPMPeriodStats(params: {
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
export async function fetchMallPMYearMatrix(
  year?: number,
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<PMYearMatrix> {
  const params: Record<string, number | string> = {}
  if (year) params.year = year
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<PMYearMatrix>(`${BASE}/period-stats/year-matrix`, { params })
  return res.data
}

// Matrix cell detail (click to query)
export type PMMatrixMetric = 'prev_carry_over' | 'prev_resolved' | 'period_total' | 'period_completed'

export interface MallPMMatrixItem {
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

export interface MallPMMatrixItemsResponse {
  total: number
  items: MallPMMatrixItem[]
}

export async function fetchMallPMMatrixItems(params: {
  year: number
  month: number
  metric: PMMatrixMetric
  frequency_type?: string
}): Promise<MallPMMatrixItemsResponse> {
  const res = await apiClient.get<MallPMMatrixItemsResponse>(
    `${BASE}/period-stats/year-matrix/items`, { params }
  )
  return res.data
}

// Maintenance item catalog (by frequency type)
export interface MallPMCatalogItem {
  seq_no:            number
  category:          string
  frequency:         string
  task_name:         string
  location:          string
  estimated_minutes: number
  exec_months_raw:   string
}

export interface MallPMCatalogResponse {
  total: number
  items: MallPMCatalogItem[]
}

export async function fetchMallPMCatalog(
  frequency_type?: 'monthly' | 'quarterly' | 'yearly',
): Promise<MallPMCatalogResponse> {
  const params: Record<string, string> = {}
  if (frequency_type) params.frequency_type = frequency_type
  const res = await apiClient.get<MallPMCatalogResponse>(`${BASE}/items/catalog`, { params })
  return res.data
}

// ══════════════════════════════════════════════════════════════════════
// 排程管理（mall_pm_schedule）相關 API
// ══════════════════════════════════════════════════════════════════════

export interface MallPMScheduleItem {
  id:                number
  year_month:        string
  item_ragic_id:     string
  category:          string
  task_name:         string
  location:          string
  frequency:         string
  estimated_minutes: number
  scheduled_date:    string
  executor_name:     string
  schedule_source:   string
  start_time:        string
  end_time:          string
  is_completed:      boolean
  result_note:       string
  abnormal_flag:     boolean
  abnormal_note:     string
  portal_edited_at:  string | null
  created_at:        string
  updated_at:        string
  status:            string
}

export interface MallPMScheduleKPI {
  total:              number
  unscheduled:        number
  scheduled:          number
  in_progress:        number
  completed:          number
  overdue:            number
  abnormal:           number
  should_do_not_done: number
  completion_rate:    number
}

export interface MallPMScheduleGenerateResult {
  year_month:             string
  generated:              number
  updated:                number
  skipped_completed:      number
  skipped_edited:         number
  skipped_non_month:      number
  skipped_no_frequency:   number
  errors:                 string[]
}

export interface MallPMScheduleListResponse {
  year_month:         string
  total:              number
  should_do_not_done: number
  items:              MallPMScheduleItem[]
}

export interface MallPMScheduleMatrixCell {
  month:          number
  status:         string
  schedule_id:    number | null
  scheduled_date: string | null
}

export interface MallPMScheduleMatrixRow {
  item_ragic_id: string
  category:      string
  task_name:     string
  location:      string
  frequency:     string
  cells:         MallPMScheduleMatrixCell[]
}

export interface MallPMScheduleAnnualMatrix {
  year:    number
  rows:    MallPMScheduleMatrixRow[]
  summary: {
    total_items:     number
    total_cells:     number
    completed_count: number
    completion_rate: number
  }
}

/** 產生指定月份商場排程 */
export async function generateMallSchedule(year: number, month: number): Promise<MallPMScheduleGenerateResult> {
  const res = await apiClient.post<MallPMScheduleGenerateResult>(
    `${BASE}/schedule/generate`,
    null,
    { params: { year, month } }
  )
  return res.data
}

/** 查詢商場排程明細列表 */
export async function getMallScheduleList(params: {
  year_month?: string
  category?: string
  status?: string
}): Promise<MallPMScheduleListResponse> {
  const res = await apiClient.get<MallPMScheduleListResponse>(`${BASE}/schedule`, { params })
  return res.data
}

/** 商場排程 KPI 統計 */
export async function getMallScheduleKpi(year_month?: string): Promise<MallPMScheduleKPI> {
  const params: Record<string, string> = {}
  if (year_month) params.year_month = year_month
  const res = await apiClient.get<MallPMScheduleKPI>(`${BASE}/schedule/kpi`, { params })
  return res.data
}

/** 商場跨月逾期清單 */
export async function getMallOverdueSchedule(before_date?: string) {
  const params: Record<string, string> = {}
  if (before_date) params.before_date = before_date
  const res = await apiClient.get(`${BASE}/schedule/overdue`, { params })
  return res.data
}

/** 商場年度計劃矩陣 */
export async function getMallAnnualMatrix(year: number, category?: string): Promise<MallPMScheduleAnnualMatrix> {
  const params: Record<string, string | number> = { year }
  if (category) params.category = category
  const res = await apiClient.get<MallPMScheduleAnnualMatrix>(`${BASE}/schedule/annual-matrix`, { params })
  return res.data
}

/** 人工調整商場排程明細 */
export async function updateMallSchedule(
  scheduleId: number,
  body: Partial<Pick<MallPMScheduleItem,
    'scheduled_date' | 'executor_name' | 'start_time' | 'end_time' |
    'is_completed' | 'result_note' | 'abnormal_flag' | 'abnormal_note'
  >>
): Promise<MallPMScheduleItem> {
  const res = await apiClient.patch<MallPMScheduleItem>(`${BASE}/schedule/${scheduleId}`, body)
  return res.data
}
