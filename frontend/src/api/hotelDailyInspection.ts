/**
 * 飯店每日巡檢 API 封裝
 * Prefix: /api/v1/hotel-daily-inspection
 */
import apiClient from '@/api/client'

const BASE = '/hotel-daily-inspection'

// ── 型別 ─────────────────────────────────────────────────────────────────────

export interface HotelDIStats {
  sheet_key:        string
  latest_batch:     HotelDIBatchInfo | null
  latest_kpi:       HotelDIKpi | null
  recent_abnormal:  HotelDIAbnormalItem[]
  total_batches_7d: number
  abnormal_trend:   HotelDITrendPoint[]
}

export interface HotelDIBatchInfo {
  ragic_id:        string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  work_hours:      string
}

export interface HotelDIKpi {
  total:           number
  normal:          number
  abnormal:        number
  pending:         number
  unchecked:       number
  checked:         number
  completion_rate: number
}

export interface HotelDIAbnormalItem {
  item_name:     string
  result_raw:    string
  result_status: string
}

export interface HotelDITrendPoint {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

export interface HotelDIBatchRow {
  id:              string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  total:           number
  checked:         number
  abnormal:        number
  pending:         number
  completion_rate: number
}

export interface HotelDISheetSummary {
  key:             string
  floor:           string
  title:           string
  total_batches:   number
  total_items:     number
  checked_items:   number
  abnormal_items:  number
  pending_items:   number
  unchecked_items: number
  completion_rate: number
  has_data:        boolean
  total_minutes:   number
}

export interface HotelDIDashboardSummary {
  target_date: string
  sheets:      HotelDISheetSummary[]
}

/** 月份彙總統計（供飯店管理 Dashboard KPI Card 使用） */
export interface HotelDIMonthlyDashboard {
  year:            number
  month:           number
  year_month:      string
  total_items:     number
  checked_items:   number
  abnormal_items:  number
  total_minutes:   number
  completion_rate: number
  sheets:          HotelDISheetSummary[]
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得指定區域的 Dashboard 統計
 */
export async function fetchHotelDailyStats(
  sheetKey: string,
  targetDate?: string,
): Promise<HotelDIStats> {
  const params = targetDate ? { target_date: targetDate } : {}
  const res = await apiClient.get<HotelDIStats>(`${BASE}/${sheetKey}/stats`, { params })
  return res.data
}

/**
 * 取得指定區域指定月份的巡檢場次清單
 */
export async function fetchHotelDailyBatches(
  sheetKey: string,
  params: { year_month?: string },
): Promise<HotelDIBatchRow[]> {
  const res = await apiClient.get<HotelDIBatchRow[]>(`${BASE}/${sheetKey}/batches`, { params })
  return res.data
}

/**
 * 觸發指定區域 Ragic 同步（背景執行）
 */
export async function syncHotelDailyFromRagic(sheetKey: string): Promise<void> {
  await apiClient.post(`${BASE}/${sheetKey}/sync`)
}

/**
 * 觸發全部 5 張 Sheet Ragic 同步（背景執行）
 */
export async function syncHotelDailyAllFromRagic(): Promise<void> {
  await apiClient.post(`${BASE}/sync/all`)
}

/**
 * 取得全體飯店每日巡檢 Dashboard 統計（跨 Sheet）— 單日口徑
 */
export async function fetchHotelDailyDashboardSummary(
  targetDate?: string,
): Promise<HotelDIDashboardSummary> {
  const params = targetDate ? { target_date: targetDate } : {}
  const res = await apiClient.get<HotelDIDashboardSummary>(`${BASE}/dashboard/summary`, { params })
  return res.data
}

// ── 每日巡檢表彙整 型別 ───────────────────────────────────────────────────────

export interface DailyFormRow {
  // 模板欄位
  floor:           string
  item:            string
  check_content:   string
  result_options:  string
  minutes:         number
  source_tab:      string
  item_first_row:  boolean
  floor_first_row: boolean
  floor_row_count: number
  item_row_count:  number
  // 比對結果欄位
  inspector:       string
  result_text:     string
  result_status:   'normal' | 'abnormal' | 'pending' | 'unchecked'
  abnormal_note:   string
  matched:         boolean
  abnormal:        boolean
  actual_minutes:  number   // 該 Sheet 本次／本月實際巡檢時間（分），0 = 無資料
}

export interface DailyFormResponse {
  year:             number
  month:            number
  inspection_date:  string | null
  has_data_today:   boolean | null   // null = 整月模式；true/false = 單日模式
  rows:             DailyFormRow[]
}

/**
 * 取得每日巡檢表彙整資料（依標準模板 + 年月篩選）
 * inspectionDate 選填：填入時只取該日結果
 */
export async function fetchHotelDailyForm(
  year: number,
  month: number,
  inspectionDate?: string,
): Promise<DailyFormResponse> {
  const params: Record<string, unknown> = { year, month }
  if (inspectionDate) params.inspection_date = inspectionDate
  const res = await apiClient.get<DailyFormResponse>(`${BASE}/daily-form`, { params })
  return res.data
}

// ── 月份每日巡檢狀況格 型別 ──────────────────────────────────────────────────

export interface DailyCalendarDay {
  has_record:      boolean
  completion_rate: number
  abnormal_count:  number
  pending_count:   number
}

export interface DailyCalendarSheet {
  key:   string
  floor: string
  title: string
  daily: Record<string, DailyCalendarDay>  // key = "1" ~ "31"
}

export interface DailyCalendarResponse {
  year:    number
  month:   number
  max_day: number
  sheets:  DailyCalendarSheet[]
}

/**
 * 取得指定月份每日巡檢狀況格（Dashboard 月曆格用）
 */
export async function fetchHotelDailyCalendar(
  year: number,
  month: number,
): Promise<DailyCalendarResponse> {
  const res = await apiClient.get<DailyCalendarResponse>(`${BASE}/daily-calendar`, {
    params: { year, month },
  })
  return res.data
}

/**
 * 取得飯店每日巡檢月份彙總統計（跨 Sheet）— 月份口徑
 * 供飯店管理 Dashboard KPI Card 使用
 */
export async function fetchHotelDailyMonthlyDashboard(
  year: number,
  month: number,
): Promise<HotelDIMonthlyDashboard> {
  const res = await apiClient.get<HotelDIMonthlyDashboard>(
    `${BASE}/dashboard/monthly-summary`,
    { params: { year, month } },
  )
  return res.data
}
