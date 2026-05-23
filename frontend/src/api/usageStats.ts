/**
 * 使用監控統計 API
 * 所有端點僅 system_admin 可呼叫（後端已驗證）
 */
import client from './client'

const BASE = '/usage'

export interface UsageSummary {
  days: number
  total_requests: number
  avg_response_ms: number
  error_count: number
  error_rate_pct: number
  dau_today: number
  unique_users_period: number
}

export interface ModuleStat {
  module: string
  total: number
  reads: number
  writes: number
}

export interface UserStat {
  user_id: string
  user_email: string
  total: number
  last_seen: string | null
  top_module: string
}

export interface ResponseTimeStat {
  module: string
  count: number
  avg_ms: number
  p95_ms: number
  max_ms: number
}

export interface DauPoint {
  date: string
  dau: number
}

export interface ErrorStat {
  module: string
  total: number
  err4xx: number
  err5xx: number
  error_rate_pct: number
}

export interface TimelinePoint {
  hour: string
  requests: number
}

export const usageStatsApi = {
  getSummary:       (days = 7)   => client.get<UsageSummary>(`${BASE}/summary?days=${days}`),
  getModules:       (days = 7)   => client.get<{ days: number; modules: ModuleStat[] }>(`${BASE}/modules?days=${days}`),
  getUsers:         (days = 7)   => client.get<{ days: number; users: UserStat[] }>(`${BASE}/users?days=${days}`),
  getResponseTimes: (days = 7)   => client.get<{ days: number; modules: ResponseTimeStat[] }>(`${BASE}/response-times?days=${days}`),
  getDau:           (days = 30)  => client.get<{ days: number; data: DauPoint[] }>(`${BASE}/dau?days=${days}`),
  getErrors:        (days = 7)   => client.get<{ days: number; modules: ErrorStat[] }>(`${BASE}/errors?days=${days}`),
  getTimeline:      (days = 7, module?: string) => {
    const q = module ? `&module=${encodeURIComponent(module)}` : ''
    return client.get<{ days: number; module: string; data: TimelinePoint[] }>(`${BASE}/timeline?days=${days}${q}`)
  },
}
