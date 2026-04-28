/**
 * ★工項類別分析 API 封裝  (v2 — 主管決策 Dashboard)
 * 對應後端 /api/v1/work-category-analysis/*
 */
import apiClient from '@/api/client'

const BASE = '/work-category-analysis'

// ── 常數 ─────────────────────────────────────────────────────────────────────

export const CATEGORIES = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢'] as const
export type Category = typeof CATEGORIES[number]

export const SOURCES = ['luqun', 'dazhi', 'hotel_room'] as const
export type Source = typeof SOURCES[number]

export const SOURCE_LABELS: Record<Source | string, string> = {
  luqun:      '樂群工務',
  dazhi:      '大直工務',
  hotel_room: '房務保養',
}

export const CATEGORY_COLORS: Record<string, string> = {
  '現場報修': '#4BA8E8',
  '上級交辦': '#52C41A',
  '緊急事件': '#FF4D4F',
  '例行維護': '#FA8C16',
  '每日巡檢': '#722ED1',
}

export const CATEGORY_TAG_COLORS: Record<string, string> = {
  '現場報修': 'blue',
  '上級交辦': 'green',
  '緊急事件': 'red',
  '例行維護': 'orange',
  '每日巡檢': 'purple',
}

export const SOURCE_COLORS: Record<string, string> = {
  luqun:      '#1B3A5C',
  dazhi:      '#4BA8E8',
  hotel_room: '#722ED1',
}

// ── 型別定義 ──────────────────────────────────────────────────────────────────

export interface KpiTopItem { name: string; hours: number; pct: number }
export interface KpiSourceItem { source: string; label: string; hours: number; pct: number }

export interface KpiData {
  total_hours:      number
  total_cases:      number
  total_persons:    number
  avg_person_hours: number
  top_category:     KpiTopItem
  top_person:       KpiTopItem
  source_breakdown: KpiSourceItem[]
  mom_change_pct:   number | null
  prev_month_hours: number
}

export interface ChartPoint {
  label: string
  現場報修: number; 上級交辦: number; 緊急事件: number; 例行維護: number; 每日巡檢: number
}

export interface CategoryBreakdownItem { name: string; value: number; pct: number }

export interface PersonRankingItem {
  rank: number; person: string; hours: number; pct: number
  sources: string[]; source_labels: string[]; top_category: string
}

export interface CategoryPersonMatrixItem {
  person: string
  現場報修: number; 上級交辦: number; 緊急事件: number; 例行維護: number; 每日巡檢: number
}

export interface SourceBreakdownItem {
  source: string; label: string; hours: number; pct: number
  cases: number; persons: number; top_category: string
}

export interface ConcentrationData {
  total_persons:   number
  top3_pct:        number
  top5_pct:        number
  top10_pct:       number
  is_concentrated: boolean
}

export interface HoursRow { category: string; hours: number[]; total: number; pct: number }
export interface DailyHours  { days: number[]; weekdays: string[]; rows: HoursRow[] }
export interface MonthlyHours { months: number[]; rows: HoursRow[] }
export interface PersonHoursRow { category: string; pct_by_person: number[] }
export interface PersonHours { persons: string[]; rows: PersonHoursRow[] }

export interface CategoryStats {
  kpi:                    KpiData
  chart_data:             ChartPoint[]
  category_breakdown:     CategoryBreakdownItem[]
  person_ranking:         PersonRankingItem[]
  category_person_matrix: CategoryPersonMatrixItem[]
  source_breakdown:       SourceBreakdownItem[]
  concentration:          ConcentrationData
  daily_hours:            DailyHours
  monthly_hours:          MonthlyHours
  person_hours:           PersonHours
  meta:                   { year: number; month: number; sources: string[]; category: string; person: string; total_rows: number; last_sync_at?: string }
}

export interface StatsParams {
  year:     number
  month?:   number
  sources?: string
  category?: string
  person?:  string
}

// ── API 函數 ──────────────────────────────────────────────────────────────────

export async function fetchYears(): Promise<{ years: number[] }> {
  const res = await apiClient.get<{ years: number[] }>(`${BASE}/years`)
  return res.data
}

export async function fetchPersons(year?: number, sources?: string): Promise<{ persons: string[] }> {
  const params: Record<string, string | number> = {}
  if (year    !== undefined) params.year    = year
  if (sources !== undefined) params.sources = sources
  const res = await apiClient.get<{ persons: string[] }>(`${BASE}/persons`, { params })
  return res.data
}

export async function fetchStats(params: StatsParams): Promise<CategoryStats> {
  const p: Record<string, string | number> = { year: params.year }
  if (params.month    !== undefined) p.month    = params.month
  if (params.sources  !== undefined) p.sources  = params.sources
  if (params.category !== undefined) p.category = params.category
  if (params.person   !== undefined) p.person   = params.person
  const res = await apiClient.get<CategoryStats>(`${BASE}/stats`, { params: p })
  return res.data
}
