/**
 * 商場管理 Dashboard — 跨模組彙整 API
 * GET /api/v1/mall/daily-hours    每日工時彙總（五項工項）
 * GET /api/v1/mall/monthly-hours  每月工時彙總（五項工項）
 * GET /api/v1/mall/person-hours   人員工時佔比（五項工項 × Top-15 人員）
 *
 * 回傳格式與 work-category-analysis 對應端點完全一致，
 * 前端可沿用相同表格欄位建構邏輯。
 */
import apiClient from '@/api/client'

const BASE = '/mall'

// ── 型別定義 ──────────────────────────────────────────────────────────────────

export interface MallDailyRow {
  category:    string    // '現場報修' | '上級交辦' | '緊急事件' | '例行維護' | '每日巡檢' | 'TOTAL'
  hours:       number[]  // 每日 HR，長度 = 當月天數
  total:       number    // 整月合計 HR
  pct:         number    // 佔全部工項工時 % (0–100)
  cases:       number[]  // 每日案件數，與 hours 同長度
  cases_total: number    // 整月合計案件數
  cases_pct:   number    // 佔全部工項案件數 % (0–100)
}

export interface MallDailyHoursData {
  year:     number
  month:    number
  days:     number[]    // [1, 2, ..., 28/30/31]
  weekdays: string[]    // ['一', '二', ...] 與 days 同長度
  rows:     MallDailyRow[]  // 5 工項列 + TOTAL 列，共 6 列
}

export interface MallMonthlyRow {
  category:    string    // '現場報修' | '上級交辦' | '緊急事件' | '例行維護' | '每日巡檢' | 'TOTAL'
  hours:       number[]  // 每月 HR，長度固定 12（1月–12月）
  total:       number    // 全年合計 HR
  pct:         number    // 佔全部工項工時 % (0–100)
  cases:       number[]  // 每月案件數，長度固定 12
  cases_total: number    // 全年合計案件數
  cases_pct:   number    // 佔全部工項案件數 % (0–100)
}

export interface MallMonthlyHoursData {
  year:   number
  months: number[]         // [1, 2, ..., 12]
  rows:   MallMonthlyRow[]
}

export interface MallPersonRow {
  category:      string    // '現場報修' | ... (5 工項，無 TOTAL 列)
  pct_by_person: number[]  // 每位人員在該工項的工時佔比 (%)，與 persons[] 同長度
}

export interface MallPersonHoursData {
  year:          number
  persons:       string[]       // Top-15 人員名稱（依全類別合計工時降冪）
  person_totals: number[]       // 各人員全年合計工時（與 persons[] 同長度）
  rows:          MallPersonRow[]
}

// ── 工項顏色常數（供表格 Tag 使用）──────────────────────────────────────────────

export const MALL_CATEGORY_TAG_COLORS: Record<string, string> = {
  '現場報修': 'blue',
  '上級交辦': 'green',
  '緊急事件': 'red',
  '例行維護': 'orange',
  '每日巡檢': 'purple',
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得指定年月的每日工時彙總（五項工項）。
 * @param year  年份（2020–2030）
 * @param month 月份（1–12，不可為 0）
 */
export async function fetchMallDailyHours(
  year: number,
  month: number,
): Promise<MallDailyHoursData> {
  const res = await apiClient.get<MallDailyHoursData>(`${BASE}/daily-hours`, {
    params: { year, month },
  })
  return res.data
}

/**
 * 取得指定年份的每月工時彙總（五項工項，共 12 個月）。
 * @param year 年份（2020–2030）
 */
export async function fetchMallMonthlyHours(
  year: number,
): Promise<MallMonthlyHoursData> {
  const res = await apiClient.get<MallMonthlyHoursData>(`${BASE}/monthly-hours`, {
    params: { year },
  })
  return res.data
}

/**
 * 取得指定年份的人員工時佔比（五項工項 × Top-15 人員）。
 * @param year 年份（2020–2030）
 */
export async function fetchMallPersonHours(
  year: number,
): Promise<MallPersonHoursData> {
  const res = await apiClient.get<MallPersonHoursData>(`${BASE}/person-hours`, {
    params: { year },
  })
  return res.data
}

// ── PPTX 匯出 Payload 型別 ────────────────────────────────────────────────────

export interface KpiSummaryPayload {
  total_cases:      number
  completed_cases:  number
  total_work_hours: number
  abnormal_count:   number
  overdue_count:    number
}

export interface SourceCardPayload {
  source_name:     string
  source_key:      string
  case_count:      number
  completed_count: number
  completion_rate: number
  abnormal_count:  number
  overdue_count:   number
  work_hours:      number
  actual_hours?:   number
}

export interface RepairCostsPayload {
  outsource_fee:   number
  maintenance_fee: number
  deduction_fee:   number
  month_total_fee: number
  period_label:    string
}

export interface MallPptxPayload {
  kpi_summary:  KpiSummaryPayload
  source_cards: SourceCardPayload[]
  repair_costs: RepairCostsPayload
}

/**
 * POST mall/overview PPTX — 前端帶入 KPI payload，觸發瀏覽器下載。
 */
export async function exportMallOverviewPptx(
  year: number,
  month: number,
  payload: MallPptxPayload,
): Promise<void> {
  const token = localStorage.getItem('access_token') ?? ''
  const url = `/api/v1/mall/overview/export/pptx?year=${year}&month=${month}`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = `商場管理報告_${year}年${String(month).padStart(2, '0')}月.pptx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objectUrl)
}
