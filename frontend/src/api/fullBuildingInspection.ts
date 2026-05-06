/**
 * 整棟巡檢 API 封裝
 * Prefix: /api/v1/full-building-inspection
 */
import apiClient from '@/api/client'

const BASE = '/full-building-inspection'

// ── 型別 ─────────────────────────────────────────────────────────────────────

export interface FullBuildingSheetConfig {
  key:         string
  floor:       string
  title:       string
  ragic_url:   string
  description: string
}

/** 月份統計 — 單一 Sheet */
export interface FullBuildingMonthlySheetSummary {
  key:               string
  floor:             string
  title:             string
  month_count:       number
  missing_count:     number
  missing_days:      string[]
  latest_batch_date: string
  has_today:         boolean
  is_current_month:  boolean
  trend_7d:          Array<{ date: string; has_record: boolean }>
  has_data:          boolean
}

/** 月份統計 — 跨 Sheet 總覽 */
export interface FullBuildingMonthlyDashboardSummary {
  month:      string   // YYYY-MM
  year_month: string   // YYYY/MM
  sheets:     FullBuildingMonthlySheetSummary[]
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得各樓層 Sheet 設定清單
 */
export async function fetchFullBuildingSheets(): Promise<FullBuildingSheetConfig[]> {
  const res = await apiClient.get<FullBuildingSheetConfig[]>(`${BASE}/sheets`)
  return res.data
}

/**
 * 取得整棟巡檢 Dashboard 月份統計（跨 Sheet）
 * @param month  查詢月份，YYYY-MM 格式（如 "2026-05"）。不填則後端自動使用當月。
 */
export async function fetchFullBuildingMonthlyDashboard(
  month?: string,
): Promise<FullBuildingMonthlyDashboardSummary> {
  const params = month ? { month } : {}
  const res = await apiClient.get<FullBuildingMonthlyDashboardSummary>(
    `${BASE}/dashboard/monthly-summary`,
    { params },
  )
  return res.data
}

// ── 每日巡檢表 ────────────────────────────────────────────────────────────────

export interface FullBuildingDailyFormRow {
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
  inspector:       string
  result_text:     string
  result_status:   'normal' | 'abnormal' | 'pending' | 'unchecked'
  abnormal_note:   string
  matched:         boolean
  abnormal:        boolean
  actual_minutes:  number
}

export interface FullBuildingDailyFormResponse {
  year:                     number
  month:                    number
  inspection_date:          string
  rows:                     FullBuildingDailyFormRow[]
  standard_minutes_morning: number
  standard_minutes_total:   number
  actual_minutes:           number
}

/**
 * 取得整棟巡檢每日巡檢表
 * @param year            年份
 * @param month           月份
 * @param inspectionDate  巡檢日期 YYYY/MM/DD（不填則顯示整月模板）
 */
export async function fetchFullBuildingDailyForm(
  year: number,
  month: number,
  inspectionDate?: string,
): Promise<FullBuildingDailyFormResponse> {
  const params: Record<string, unknown> = { year, month }
  if (inspectionDate) params.inspection_date = inspectionDate
  const res = await apiClient.get<FullBuildingDailyFormResponse>(`${BASE}/daily-form`, { params })
  return res.data
}

// ── 月曆格（樓層 × 日）────────────────────────────────────────────────────────

export async function fetchFullBuildingInspectionCalendar(
  year: number,
  month: number,
): Promise<{ year: number; month: number; max_day: number; rows: import('@/components/MonthlyCalendarGrid').CalendarRow[] }> {
  const res = await apiClient.get(`${BASE}/dashboard/calendar`, { params: { year, month } })
  return res.data
}
