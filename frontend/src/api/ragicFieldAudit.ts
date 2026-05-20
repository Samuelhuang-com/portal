/**
 * Ragic 與 Portal 欄位比對 API
 * 路由前綴：/api/v1/settings/ragic-field-audit
 */
import apiClient from '@/api/client'

const BASE = '/settings/ragic-field-audit'

// ── 型別定義 ──────────────────────────────────────────────────────────────────

export interface AuditSummary {
  total_modules: number
  audited_modules: number
  normal_modules: number
  error_modules: number
  unmapped_fields: number
  high_risk_issues: number
  last_run_time: string | null
  last_run_status: string | null
}

export interface ModuleOverview {
  item_no: number
  company: string
  module_name: string
  portal_name: string
  portal_route: string
  local_tables: string[]
  ragic_url: string
  ragic_field_count: number
  portal_db_field_count: number
  portal_api_field_count: number
  portal_fe_field_count: number
  normal_count: number
  issue_count: number
  unmapped_count: number
  total_mapping_count: number
  last_checked_at: string | null
  status: 'normal' | 'warning' | 'error' | 'not_audited'
  is_active: boolean
}

export interface FieldMapping {
  id: number | null
  app_directory_id: number | null
  company: string | null
  module_name: string | null
  portal_route: string | null
  ragic_url: string | null
  ragic_form_name: string | null
  ragic_field_id: string
  ragic_field_name: string
  ragic_field_type: string
  is_ragic_required: boolean
  is_ragic_formula: boolean
  is_ragic_subtable: boolean
  portal_db_table: string
  portal_db_field: string
  portal_api_field: string
  portal_frontend_field: string
  display_name: string
  is_displayed: boolean
  is_filter: boolean
  is_export: boolean
  is_calculated: boolean
  mapping_status: string
  severity: string | null
  issue_type: string | null
  issue_message: string | null
  suggestion: string | null
  is_resolved: boolean
  notes: string | null
  last_checked_at: string | null
  // 草稿模式（API 生成但未存 DB）
  category?: string
}

export interface KpiMapping {
  id: number | null
  module_name: string | null
  portal_route: string | null
  kpi_name: string
  page_section: string | null
  api_endpoint: string | null
  db_table: string | null
  source_fields: string | null
  date_field: string | null
  filters: string | null
  formula: string | null
  ragic_source_fields: string | null
  trace_status: 'traceable' | 'partial' | 'untraceable' | 'unknown'
  issue_message: string | null
  suggestion: string | null
  last_checked_at: string | null
}

export interface AuditRun {
  id: number
  run_time: string
  triggered_by: string | null
  scope: string | null
  total_modules: number
  normal_count: number
  warning_count: number
  error_count: number
  status: string
  notes: string | null
}

// ── API 函數 ──────────────────────────────────────────────────────────────────

/** 首頁 KPI Card 摘要 */
export async function fetchAuditSummary(): Promise<AuditSummary> {
  const res = await apiClient.get(`${BASE}/summary`)
  return res.data
}

/** 模組比對總覽（Tab 1） */
export async function fetchModules(params?: {
  company?: string
  status?: string
  keyword?: string
}): Promise<{ items: ModuleOverview[]; total: number }> {
  const res = await apiClient.get(`${BASE}/modules`, { params })
  return res.data
}

/** 單一模組欄位 Mapping 明細（Tab 2） */
export async function fetchModuleDetail(route: string): Promise<{
  route: string
  items: FieldMapping[]
  total: number
}> {
  const res = await apiClient.get(`${BASE}/module`, { params: { route } })
  return res.data
}

/** 異常清單（Tab 3） */
export async function fetchIssues(params?: {
  severity?: string
  is_resolved?: boolean
  module_name?: string
  keyword?: string
}): Promise<{ items: FieldMapping[]; total: number }> {
  const res = await apiClient.get(`${BASE}/issues`, { params })
  return res.data
}

/** KPI 計算追溯（Tab 4） */
export async function fetchKpiMappings(params?: {
  module_name?: string
  trace_status?: string
}): Promise<{ items: KpiMapping[]; total: number }> {
  const res = await apiClient.get(`${BASE}/kpi-mappings`, { params })
  return res.data
}

/** 執行比對稽核 */
export async function runAudit(scope = 'all'): Promise<{
  run_id: number
  run_time: string
  total_modules: number
  normal_count: number
  warning_count: number
  error_count: number
  created_mappings: number
  status: string
}> {
  const res = await apiClient.post(`${BASE}/run`, { scope })
  return res.data
}

/** 匯出 Excel（觸發下載） */
export async function exportExcel(): Promise<void> {
  const res = await apiClient.get(`${BASE}/export`, { responseType: 'blob' })
  const url = URL.createObjectURL(new Blob([res.data]))
  const a = document.createElement('a')
  a.href = url
  const now = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, (c) =>
    c === 'T' ? '_' : c === ':' ? '' : c
  )
  a.download = `ragic_field_audit_${now}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

/** 標記異常為已處理 */
export async function resolveMappingIssue(
  mappingId: number,
  isResolved: boolean,
  notes?: string,
): Promise<{ id: number; is_resolved: boolean; notes: string | null }> {
  const res = await apiClient.patch(`${BASE}/mapping/${mappingId}/resolve`, {
    is_resolved: isResolved,
    notes,
  })
  return res.data
}

/** 歷史比對執行紀錄 */
export async function fetchAuditRuns(): Promise<{ items: AuditRun[] }> {
  const res = await apiClient.get(`${BASE}/runs`)
  return res.data
}

export interface SyncRagicFieldsResult {
  item_no: number
  ragic_url: string
  portal_route: string
  ragic_field_count: number
  synced_count: number
  updated_count: number
  ragic_fields: string[]
  fetch_error: string | null
}

/** 從 Ragic API 抓取指定表單的所有欄位並儲存至比對表 */
export async function syncRagicFields(
  itemNo: number,
  ragicUrl: string,
): Promise<SyncRagicFieldsResult> {
  const res = await apiClient.post(`${BASE}/sync-ragic-fields`, {
    item_no: itemNo,
    ragic_url: ragicUrl,
  })
  return res.data
}

/** 取得系統已知的 Ragic URL 對照表（itemNo → ragic_url） */
export async function fetchRagicUrlMap(): Promise<{ items: { item_no: number; ragic_url: string }[] }> {
  const res = await apiClient.get(`${BASE}/ragic-url-map`)
  return res.data
}

/** 設定（或清除）指定模組的 Ragic 表單 URL */
export async function setModuleRagicUrl(
  itemNo: number,
  ragicUrl: string,
): Promise<{ item_no: number; ragic_url: string; portal_route: string; updated_mappings: number }> {
  const res = await apiClient.patch(`${BASE}/modules/${itemNo}/ragic-url`, {
    ragic_url: ragicUrl,
  })
  return res.data
}
