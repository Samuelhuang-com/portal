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
