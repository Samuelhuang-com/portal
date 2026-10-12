/**
 * SQL 查詢工具 API（僅系統管理員）
 * 路由前綴：/api/v1/settings/sql-console
 * 後端：backend/app/routers/sql_console.py
 */
import apiClient from '@/api/client'

const BASE = '/settings/sql-console'

export interface TableInfo {
  table: string
  est_rows: number
  columns: { name: string; type: string }[]
}

export interface SelectResult {
  kind: 'select'
  columns: string[]
  rows: any[][]
  row_count: number
  truncated: boolean
  limit: number
  elapsed_ms: number
}

export interface DeletePreview {
  kind: 'delete_preview'
  table: string
  affected: number
  columns: string[]
  sample_rows: any[][]
  sample_size: number
  token: string
  expires_in: number
  max_delete_rows: number
}

export interface DeleteDone {
  kind: 'delete_done'
  table: string
  affected: number
  log_id: string
}

export type ExecuteResult = SelectResult | DeletePreview | DeleteDone

export interface SqlLogRow {
  id: string
  created_at: string | null
  email: string | null
  action: 'select' | 'export' | 'delete' | 'blocked' | string
  table: string | null
  affected: number | null
  row_count: number | null
  reason: string | null
  sql: string | null
  has_backup: boolean
  ip: string | null
}

export interface SqlLogDetail {
  id: string
  action: string
  sql: string | null
  table: string | null
  affected: number | null
  columns: string[]
  rows: any[][]
}

/** 取出後端 detail 訊息（blob 回應也能解析） */
export async function sqlErrMsg(e: any): Promise<string> {
  const data = e?.response?.data
  if (data instanceof Blob) {
    try {
      const t = await data.text()
      return JSON.parse(t).detail ?? t
    } catch {
      return '匯出失敗'
    }
  }
  const d = data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x: any) => x.msg).join('；')
  return e?.message ?? '發生錯誤'
}

export const sqlConsoleApi = {
  tables: () => apiClient.get<{ tables: TableInfo[] }>(`${BASE}/tables`),

  execute: (sql: string, limit: number, confirmToken?: string) =>
    apiClient.post<ExecuteResult>(
      `${BASE}/execute`,
      { sql, limit, confirm_token: confirmToken ?? null },
      { timeout: 120_000 },
    ),

  exportFile: (sql: string, format: 'xlsx' | 'csv') =>
    apiClient.post(`${BASE}/export`, { sql, format }, { responseType: 'blob', timeout: 180_000 }),

  logs: (limit = 100) => apiClient.get<{ logs: SqlLogRow[] }>(`${BASE}/logs`, { params: { limit } }),

  logDetail: (id: string) => apiClient.get<SqlLogDetail>(`${BASE}/logs/${id}`),
}
