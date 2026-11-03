/**
 * 開發統計 API — /api/v1/dev-log
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

export const getDevLogEntries = (params: { module?: string; month?: string; unknown_only?: boolean }) =>
  client.get<{ total: number; items: DevLogItem[] }>('/dev-log/entries', { params })

export const getDevLogStats = (params: { module?: string; month?: string }) =>
  client.get<DevLogStats>('/dev-log/stats', { params })

export const patchDevLogEntry = (id: number, body: { start_at?: string | null; end_at?: string | null; time_note?: string }) =>
  client.patch<DevLogItem>(`/dev-log/entries/${id}`, body)

export const syncDevLogGit = () =>
  client.post<{ commits: number; added: number; skipped_existing: number }>('/dev-log/sync-git', null, { timeout: 300_000 })

export const importDevLog = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  // client 預設 Content-Type 為 application/json，上傳檔案必須明確指定 multipart（同 contract.ts 的做法）
  return client.post<{ parsed: number; added: number; skipped_existing: number }>('/dev-log/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
}
