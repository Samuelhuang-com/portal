/**
 * 開發統計 API — /api/v1/dev-log
 * 2026-11-20：新增需求管理（需求清單、一對一綁定變更、Jira CSV 匯入）
 */
import client from './client'

export interface DevLogItem {
  id: number
  entry_date: string
  category: string
  title: string
  module: string
  route: string            // 模組路由（空＝未知）
  start_at: string | null   // YYYY-MM-DD HH:mm
  end_at: string | null
  time_note: string
  requirement_id: number | null    // 對應需求（一對一；null＝未綁定）
  requirement_no: string | null    // 例如 REQ-0012
  updated_by: string
  updated_at: string | null
}

export interface DevLogStats {
  total: number
  with_time: number
  unknown: number
  with_range: number
  by_module: { module: string; entries: number; with_time: number; hours: number }[]
  by_month: { month: string; entries: number; with_time: number }[]
  by_category: Record<string, number>
}

export type RequirementStatus = '待評估' | '進行中' | '已完成' | '退回'
export type RequirementPriority = '高' | '中' | '低'

export interface DevRequirement {
  id: number
  req_no: string
  title: string
  description: string
  requester: string
  module: string
  status: RequirementStatus
  priority: RequirementPriority
  jira_key: string
  created_at: string | null
  completed_at: string | null
  change_count: number
  hours: number
  modules: string[]        // 此需求的變更實際涉及的模組
  last_change_at: string | null
}

export interface RequirementSummary {
  items: DevRequirement[]
  modules: string[]
  matrix: { requirement_id: number; req_no: string; module: string; count: number }[]
  unbound_entries: number
  status_counts: Record<string, number>
}

export interface RequirementInput {
  title: string
  description?: string | null
  requester?: string | null
  module?: string | null
  status: RequirementStatus
  priority: RequirementPriority
}

export const getDevLogEntries = (params: { module?: string; month?: string; unknown_only?: boolean; unbound_only?: boolean }) =>
  client.get<{ total: number; items: DevLogItem[] }>('/dev-log/entries', { params })

export const getDevLogStats = (params: { module?: string; month?: string }) =>
  client.get<DevLogStats>('/dev-log/stats', { params })

// 只送出要更新的欄位；requirement_id 送 null 代表解除綁定
export const patchDevLogEntry = (
  id: number,
  body: { start_at?: string | null; end_at?: string | null; time_note?: string; requirement_id?: number | null },
) => client.patch<DevLogItem>(`/dev-log/entries/${id}`, body)

export const syncDevLogGit = () =>
  client.post<{ commits: number; added: number; skipped_existing: number; linked_requirement: number }>(
    '/dev-log/sync-git', null, { timeout: 300_000 })

export const importDevLog = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  // client 預設 Content-Type 為 application/json，上傳檔案必須明確指定 multipart（同 contract.ts 的做法）
  return client.post<{ parsed: number; added: number; skipped_existing: number; linked_requirement: number }>(
    '/dev-log/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export const getRequirements = () =>
  client.get<RequirementSummary>('/dev-log/requirements')

export const createRequirement = (body: RequirementInput) =>
  client.post<{ id: number; req_no: string }>('/dev-log/requirements', body)

export const patchRequirement = (id: number, body: Partial<RequirementInput>) =>
  client.patch<{ id: number; req_no: string }>(`/dev-log/requirements/${id}`, body)

export const importJiraCsv = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return client.post<{
    rows: number; added: number; skipped_existing: number; skipped_invalid: number; unmapped_statuses: string[]
  }>('/dev-log/requirements/import-jira', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}
