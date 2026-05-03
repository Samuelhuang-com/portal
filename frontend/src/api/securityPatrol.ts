/**
 * 保全巡檢 API 封裝
 */
import apiClient from '@/api/client'
import type {
  SheetConfig,
  PatrolBatchListItem,
  PatrolBatchDetail,
  PatrolStats,
  SecurityDashboardSummary,
  SecurityIssueListResponse,
  SecurityDashboardTrend,
} from '@/types/securityPatrol'

const BASE = '/security'

// ── Sheet 設定 ────────────────────────────────────────────────────────────────

export async function fetchSheetConfigs(): Promise<SheetConfig[]> {
  const { data } = await apiClient.get(`${BASE}/patrol/sheets`)
  return data
}

// ── 同步 ──────────────────────────────────────────────────────────────────────

export async function syncPatrolFromRagic(sheetKey?: string): Promise<{ status: string; result: unknown }> {
  const params: Record<string, string> = {}
  if (sheetKey) params.sheet_key = sheetKey
  const { data } = await apiClient.post(`${BASE}/patrol/sync`, null, { params })
  return data
}

// ── 場次清單 ──────────────────────────────────────────────────────────────────

export async function fetchPatrolBatches(
  sheetKey: string,
  opts?: { year_month?: string; start_date?: string; end_date?: string },
): Promise<PatrolBatchListItem[]> {
  const { data } = await apiClient.get(`${BASE}/patrol/${sheetKey}/batches`, { params: opts ?? {} })
  return data
}

// ── 場次明細 ──────────────────────────────────────────────────────────────────

export async function fetchPatrolBatchDetail(
  sheetKey: string,
  batchId: string,
  opts?: { status?: string; search?: string },
): Promise<PatrolBatchDetail> {
  const { data } = await apiClient.get(
    `${BASE}/patrol/${sheetKey}/batches/${batchId}`,
    { params: opts ?? {} },
  )
  return data
}

// ── Stats（Dashboard 用）──────────────────────────────────────────────────────

export async function fetchPatrolStats(sheetKey: string): Promise<PatrolStats> {
  const { data } = await apiClient.get(`${BASE}/patrol/${sheetKey}/stats`)
  return data
}

// ── Dashboard Summary ─────────────────────────────────────────────────────────

export async function fetchSecurityDashboardSummary(
  targetDate?: string,
): Promise<SecurityDashboardSummary> {
  const { data } = await apiClient.get(`${BASE}/dashboard/summary`, {
    params: targetDate ? { target_date: targetDate } : {},
  })
  return data
}

// ── Dashboard Issues ──────────────────────────────────────────────────────────

export async function fetchSecurityDashboardIssues(opts?: {
  sheet_key?:  string
  status?:     string
  start_date?: string
  end_date?:   string
}): Promise<SecurityIssueListResponse> {
  const { data } = await apiClient.get(`${BASE}/dashboard/issues`, { params: opts ?? {} })
  return data
}

// ── Dashboard Trend ───────────────────────────────────────────────────────────

export async function fetchSecurityDashboardTrend(days = 7): Promise<SecurityDashboardTrend> {
  const { data } = await apiClient.get(`${BASE}/dashboard/trend`, { params: { days } })
  return data
}

// ── 月份彙總（供飯店管理 Dashboard KPI Card 使用）────────────────────────────

export interface SecurityMonthlyDashboard {
  year:            number
  month:           number
  year_month:      string
  total_items:     number
  checked_items:   number
  abnormal_items:  number
  total_minutes:   number
  completion_rate: number
  sheets: {
    sheet_key:       string
    sheet_name:      string
    total_batches:   number
    total_items:     number
    checked_items:   number
    abnormal_items:  number
    unchecked_items: number
    completion_rate: number
    has_data:        boolean
    total_minutes:   number
  }[]
}

export async function fetchSecurityMonthlyDashboard(
  year: number,
  month: number,
): Promise<SecurityMonthlyDashboard> {
  const { data } = await apiClient.get<SecurityMonthlyDashboard>(
    `${BASE}/dashboard/monthly-summary`,
    { params: { year, month } },
  )
  return data
}

// ── Monthly Summary ───────────────────────────────────────────────────────────

export interface SecurityMonthlySheetStats {
  sheet_key:       string
  sheet_name:      string
  total_batches:   number
  total_items:     number
  checked_items:   number
  abnormal_items:  number   // abnormal + pending 已合併
  unchecked_items: number
  completion_rate: number
  has_data:        boolean
  total_minutes:   number
}

export interface SecurityMonthlySummary {
  year:            number
  month:           number
  year_month:      string
  total_items:     number
  checked_items:   number
  abnormal_items:  number
  total_minutes:   number
  completion_rate: number
  sheets:          SecurityMonthlySheetStats[]
}

export async function fetchSecurityDashboardMonthlySummary(
  year: number,
  month: number,
): Promise<SecurityMonthlySummary> {
  const { data } = await apiClient.get<SecurityMonthlySummary>(
    `${BASE}/dashboard/monthly-summary`,
    { params: { year, month } },
  )
  return data
}
