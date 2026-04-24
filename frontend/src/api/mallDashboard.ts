import apiClient from '@/api/client'
import type {
  DashboardSummary,
  IssueListResponse,
  DashboardTrend,
} from '@/types/mallDashboard'

const BASE = '/mall/dashboard'

export async function fetchDashboardSummary(
  targetDate?: string,
): Promise<DashboardSummary> {
  const params: Record<string, string> = {}
  if (targetDate) params.target_date = targetDate
  const res = await apiClient.get<DashboardSummary>(`${BASE}/summary`, { params })
  return res.data
}

export async function fetchDashboardIssues(opts?: {
  issue_type?: string
  floor?:      string
  status?:     string
  start_date?: string
  end_date?:   string
}): Promise<IssueListResponse> {
  const params: Record<string, string> = {}
  if (opts?.issue_type) params.issue_type = opts.issue_type
  if (opts?.floor)      params.floor      = opts.floor
  if (opts?.status)     params.status     = opts.status
  if (opts?.start_date) params.start_date = opts.start_date
  if (opts?.end_date)   params.end_date   = opts.end_date
  const res = await apiClient.get<IssueListResponse>(`${BASE}/issues`, { params })
  return res.data
}

export async function fetchDashboardTrend(days = 7): Promise<DashboardTrend> {
  const res = await apiClient.get<DashboardTrend>(`${BASE}/trend`, {
    params: { days },
  })
  return res.data
}
