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

/** 取得所有可單獨觸發同步的模組名稱清單 */
export async function listSyncableModules(): Promise<string[]> {
  const { data } = await apiClient.get<{ modules: string[] }>(`${BASE}/sync-logs/modules`)
  return data.modules
}

/** 手動觸發單一模組同步 */
export async function triggerSingleModuleSync(moduleName: string): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.post(`${BASE}/sync-logs/trigger/${encodeURIComponent(moduleName)}`)
  return data
}


// ── 資料比對（verify-count）──────────────────────────────────────────────────

export interface VerifyCountResult {
  module:         string
  portal_count:   number
  ragic_count:    number
  diff:           number
  match:          boolean
  last_synced_at: string | null
}

/** 比對大直工務報修 Portal DB vs Ragic 筆數 */
export async function verifyDazhiRepairCount(): Promise<VerifyCountResult> {
  const { data } = await apiClient.get<VerifyCountResult>('/dazhi-repair/verify-count')
  return data
}

/** 比對商場工務報修 Portal DB vs Ragic 筆數 */
export async function verifyLuqunRepairCount(): Promise<VerifyCountResult> {
  const { data } = await apiClient.get<VerifyCountResult>('/luqun-repair/verify-count')
  return data
}

// ── 差集明細（verify-diff）───────────────────────────────────────────────────

export interface VerifyDiffItem {
  ragic_id:  string
  ragic_url?: string   // Ragic 有但 Portal 沒有時才有
  case_no?:  string    // Portal 有但 Ragic 沒有時才有
  title?:    string
  status?:   string
}

export interface VerifyDiffResult {
  in_ragic_not_portal: VerifyDiffItem[]   // Ragic 有，Portal 缺
  in_portal_not_ragic: VerifyDiffItem[]   // Portal 有，Ragic 已刪
}

export async function verifyDazhiRepairDiff(): Promise<VerifyDiffResult> {
  const { data } = await apiClient.get<VerifyDiffResult>('/dazhi-repair/verify-diff')
  return data
}

export async function verifyLuqunRepairDiff(): Promise<VerifyDiffResult> {
  const { data } = await apiClient.get<VerifyDiffResult>('/luqun-repair/verify-diff')
  return data
}
