/**
 * 稽核檢查（Audit Check）— API 封裝
 * 對應後端 /api/v1/audit-check（app/routers/audit_check.py）
 *
 * 規格：docs/SPEC_audit_check.md
 * ⚠️ CLAUDE.md §6：元件內不直接用 axios，一律透過這裡的函式。
 */
import client from './client'

// ── 型別 ──────────────────────────────────────────────────────────────────

/** 判定類型（取代 Excel 的字色語意，由使用者自行維護） */
export interface ResultType {
  id: number
  code: string
  label: string
  color: string
  /** 是否計入「達標項數」 */
  counts_as_pass: boolean
  /** 是否列入「缺失」自動彙整 */
  include_in_summary: boolean
  is_default: boolean
  is_system: boolean
  sort_order: number
  is_active: boolean
}

export interface AuditItem {
  id: number
  parent_id: number | null
  name: string
  description: string | null
  sort_order: number
  is_active: boolean
  /** 已被任一期稽核單引用 → 不可改名／刪除，只能停用 */
  in_use: boolean
  children: AuditItem[]
}

export interface SheetSummary {
  id: number
  company_id: number
  company_name: string
  audited_on: string | null
  status: string
  completion_rate: number | null
  completion_label: string
}

export interface Period {
  id: number
  period: string
  title: string
  goal_major: number
  goal_minor: number
  note: string | null
  /** 覆核區是否計為一個稽核子項（影響各部門分數） */
  review_counts_in_score: boolean
  status: string
  created_at: string
  sheets: SheetSummary[]
}

export interface SheetDepartment {
  id: number
  department_id: number
  name: string
  sort_order: number
  deficiency_override: string | null
  deficiency: string
}

export interface SheetItem {
  id: number
  item_id: number
  parent_sheet_item_id: number | null
  /** 1 = 大項、2 = 子項（只有子項計分） */
  level: number
  display_no: string | null
  name: string
  scope_note: string | null
  target_department_ids: number[]
  sort_order: number
}

export interface Cell {
  sheet_item_id: number
  sheet_department_id: number
  comment: string | null
  result_code: string
  updated_at: string | null
}

export interface DepartmentScore {
  sheet_department_id: number
  department_id: number
  name: string
  sub_count: number
  pass_count: number
  score: number | null
  score_label: string
}

export interface Review {
  sheet_department_id: number
  source_period: string | null
  pending_text: string | null
  pending_result: string
  result_text: string | null
  result_status: string
}

export interface SheetDetail {
  id: number
  period_id: number
  period: string
  title: string
  goal_major: number
  goal_minor: number
  review_counts_in_score: boolean
  company_id: number
  company_name: string
  audited_on: string | null
  audited_session: string | null
  audited_label: string
  executor_label: string | null
  /** 完成率分母的人工調整（Excel 的「3*3-1=8」：本期少做一項填 -1） */
  completion_adjust: number
  remark: string | null
  status: string
  departments: SheetDepartment[]
  items: SheetItem[]
  cells: Cell[]
  scores: DepartmentScore[]
  reviews: Review[]
  completion_rate: number | null
  completion_label: string
  result_types: ResultType[]
}

export interface SheetItemSpec {
  item_id: number
  scope_note?: string | null
  target_department_ids: number[]
}

export interface StatisticsCell {
  period: string
  score: number | null
  label: string
}

export interface StatisticsBlock {
  company_id: number
  company_name: string
  periods: string[]
  audited_labels: string[]
  major_items: string[][]
  rows: { department_id: number; name: string; cells: StatisticsCell[] }[]
  completion: StatisticsCell[]
}

export interface Statistics {
  year: number
  note: string | null
  blocks: StatisticsBlock[]
}

export interface FlaggedRow {
  period: string
  company_name: string
  department_id: number
  department_name: string
  item_name: string
  display_no: string
  result_code: string
  result_label: string
  result_color: string
  comment: string
}

export interface MobileSheetRow {
  id: number
  period: string
  title: string
  company_id: number
  company_name: string
  audited_on: string | null
  status: string
  completion_rate: number | null
  completion_label: string
}

// ── 判定類型 ──────────────────────────────────────────────────────────────
export const resultTypesApi = {
  list: () => client.get<ResultType[]>('/audit-check/result-types'),
  create: (body: Partial<ResultType> & { code: string; label: string }) =>
    client.post<ResultType>('/audit-check/result-types', body),
  update: (id: number, body: Partial<ResultType>) =>
    client.put<ResultType>(`/audit-check/result-types/${id}`, body),
  toggle: (id: number) => client.patch<ResultType>(`/audit-check/result-types/${id}/toggle`),
  remove: (id: number) => client.delete(`/audit-check/result-types/${id}`),
}

// ── 檢查項主檔 ────────────────────────────────────────────────────────────
export const itemsApi = {
  list: (includeInactive = false) =>
    client.get<AuditItem[]>('/audit-check/items', { params: { include_inactive: includeInactive } }),
  create: (body: { name: string; parent_id?: number | null; description?: string; sort_order?: number }) =>
    client.post<AuditItem>('/audit-check/items', body),
  update: (id: number, body: { name?: string; description?: string; sort_order?: number }) =>
    client.put<AuditItem>(`/audit-check/items/${id}`, body),
  toggle: (id: number) => client.patch<AuditItem>(`/audit-check/items/${id}/toggle`),
  remove: (id: number) => client.delete(`/audit-check/items/${id}`),
}

// ── 期別 ──────────────────────────────────────────────────────────────────
export const periodsApi = {
  list: (year?: number) =>
    client.get<Period[]>('/audit-check/periods', { params: year ? { year } : undefined }),
  create: (body: { period: string; title?: string; goal_major?: number; goal_minor?: number; note?: string; review_counts_in_score?: boolean }) =>
    client.post<Period>('/audit-check/periods', body),
  update: (id: number, body: Record<string, unknown>) =>
    client.put<Period>(`/audit-check/periods/${id}`, body),
  remove: (id: number) => client.delete(`/audit-check/periods/${id}`),
}

// ── 稽核單 ────────────────────────────────────────────────────────────────
export const sheetsApi = {
  get: (id: number) => client.get<SheetDetail>(`/audit-check/sheets/${id}`),
  create: (body: {
    period_id: number
    company_id: number
    audited_on?: string | null
    audited_session?: string | null
    executor_label?: string | null
    department_ids: number[]
    items: SheetItemSpec[]
    carry_over?: boolean
  }) => client.post<SheetDetail>('/audit-check/sheets', body),
  update: (id: number, body: Record<string, unknown>) =>
    client.put<SheetDetail>(`/audit-check/sheets/${id}`, body),
  updateLayout: (id: number, body: { department_ids: number[]; items: SheetItemSpec[] }) =>
    client.put<SheetDetail>(`/audit-check/sheets/${id}/layout`, body),
  remove: (id: number) => client.delete(`/audit-check/sheets/${id}`),

  upsertCell: (id: number, body: {
    sheet_item_id: number
    sheet_department_id: number
    comment?: string | null
    result_code?: string | null
  }) => client.put<SheetDetail>(`/audit-check/sheets/${id}/cells`, body),

  upsertCellsBulk: (id: number, cells: {
    sheet_item_id: number
    sheet_department_id: number
    comment?: string | null
    result_code?: string | null
  }[]) => client.put<SheetDetail>(`/audit-check/sheets/${id}/cells/bulk`, { cells }),

  upsertReview: (id: number, sheetDepartmentId: number, body: Record<string, unknown>) =>
    client.put<SheetDetail>(`/audit-check/sheets/${id}/reviews/${sheetDepartmentId}`, body),

  upsertDeficiency: (id: number, sheetDepartmentId: number, text: string | null) =>
    client.put<SheetDetail>(
      `/audit-check/sheets/${id}/departments/${sheetDepartmentId}/deficiency`,
      { deficiency_override: text },
    ),

  /** 完整路徑（給 downloadFile 用，不經過 client.baseURL） */
  exportUrl: (id: number) => `/api/v1/audit-check/sheets/${id}/export`,
}

// ── 統計 ──────────────────────────────────────────────────────────────────
export const statisticsApi = {
  get: (year: number, companyId?: number) =>
    client.get<Statistics>('/audit-check/statistics', {
      params: { year, ...(companyId != null ? { company_id: companyId } : {}) },
    }),
  flagged: (params: {
    period_id?: number
    company_id?: number
    department_id?: number
    only_failing?: boolean
  }) => client.get<FlaggedRow[]>('/audit-check/statistics/flagged', { params }),
  /** 完整路徑（給 downloadFile 用） */
  exportUrl: (year: number) => `/api/v1/audit-check/statistics/export?year=${year}`,
}

// ── 手機版 ────────────────────────────────────────────────────────────────
export const mobileApi = {
  sheets: (limit = 12) =>
    client.get<MobileSheetRow[]>('/audit-check/my-sheets', { params: { limit } }),
}
