/**
 * Ragic 連線管理 API 客戶端
 * 對應後端 /api/v1/ragic/*
 */
import apiClient from './client'

const BASE = '/ragic'

// ── 型別定義 ──────────────────────────────────────────────────────────────────

export interface RagicConnectionOut {
  id: string
  tenant_id: string
  display_name: string
  server: string
  account_name: string
  sheet_path: string
  field_mappings: Record<string, unknown>
  sync_interval: number
  is_active: boolean
  last_synced_at: string | null
  created_at: string
}

export interface RagicConnectionCreate {
  tenant_id: string
  display_name: string
  server: string
  account_name: string
  api_key: string
  sheet_path: string
  field_mappings?: Record<string, unknown>
  sync_interval?: number
}

export interface RagicConnectionUpdate {
  display_name: string
  server: string
  account_name: string
  api_key?: string          // 選填：不傳則沿用現有
  sheet_path: string
  field_mappings?: Record<string, unknown>
  sync_interval: number
}

export interface SyncLogOut {
  id: string
  connection_id: string
  started_at: string
  finished_at: string | null
  records_fetched: number | null
  status: 'running' | 'success' | 'error' | 'partial'
  error_msg: string | null
  triggered_by: string
}

export interface SchedulerJob {
  conn_id: string
  job_id: string
  next_run_at: string | null
  trigger: string
}

export interface ModuleSyncLogOut {
  id: number
  module_name: string
  started_at: string
  finished_at: string | null
  duration_sec: number | null
  status: 'running' | 'success' | 'error' | 'partial'
  fetched: number
  upserted: number
  errors_count: number
  error_msg: string | null
  triggered_by: string
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/** 列出所有連線 */
export async function listConnections(): Promise<RagicConnectionOut[]> {
  const { data } = await apiClient.get<RagicConnectionOut[]>(`${BASE}/connections`)
  return data
}

/** 建立連線 */
export async function createConnection(
  payload: RagicConnectionCreate,
): Promise<RagicConnectionOut> {
  const { data } = await apiClient.post<RagicConnectionOut>(`${BASE}/connections`, payload)
  return data
}

/** 更新連線 */
export async function updateConnection(
  connId: string,
  payload: RagicConnectionUpdate,
): Promise<RagicConnectionOut> {
  const { data } = await apiClient.put<RagicConnectionOut>(`${BASE}/connections/${connId}`, payload)
  return data
}

/** 軟刪除連線 */
export async function deleteConnection(connId: string): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.delete(`${BASE}/connections/${connId}`)
  return data
}

/** 切換啟用/停用 */
export async function toggleConnectionActive(connId: string): Promise<RagicConnectionOut> {
  const { data } = await apiClient.patch<RagicConnectionOut>(`${BASE}/connections/${connId}/active`)
  return data
}

/** 手動觸發同步 */
export async function triggerSync(connId: string): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.post(`${BASE}/connections/${connId}/sync`)
  return data
}

/** 取得同步日誌 */
export async function getSyncLogs(connId: string, limit = 50): Promise<SyncLogOut[]> {
  const { data } = await apiClient.get<SyncLogOut[]>(
    `${BASE}/connections/${connId}/logs`,
    { params: { limit } },
  )
  return data
}

/** 取得最新快照 */
export async function getLatestSnapshot(connId: string): Promise<{
  id: string
  connection_id: string
  synced_at: string
  record_count: number
  data: Record<string, unknown>
}> {
  const { data } = await apiClient.get(`${BASE}/snapshots/${connId}/latest`)
  return data
}

/** 取得排程任務狀態 */
export async function getSchedulerStatus(): Promise<{ jobs: SchedulerJob[] }> {
  const { data } = await apiClient.get<{ jobs: SchedulerJob[] }>(`${BASE}/scheduler/status`)
  return data
}

/** 取得最近 N 小時內的模組同步紀錄（預設 24 小時） */
export async function getRecentSyncLogs(hours = 24): Promise<ModuleSyncLogOut[]> {
  const { data } = await apiClient.get<ModuleSyncLogOut[]>(
    `${BASE}/sync-logs/recent`,
    { params: { hours } },
  )
  return data
}

/** 手動觸發一次所有硬編碼模組的完整同步 */
export async function triggerAllModulesSync(): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.post(`${BASE}/sync-logs/trigger`)
  return data
}
