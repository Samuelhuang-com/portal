/**
 * KPO 稽核（財#1 稽核系統建構）— API 封裝
 * 對應後端 /api/v1/audit-check/kpo（app/routers/audit_kpo.py）
 *
 * 規格：docs/SPEC_audit_kpo.md
 * ⚠️ CLAUDE.md §6：元件內不直接用 axios，一律透過這裡的函式。
 */
import client from './client'

const BASE = '/audit-check/kpo'

export type KpoResult = 'pass' | 'fail' | null

export interface KpoDept {
  id: number
  name: string
  /** 「公司｜部門」；未連結部門主檔者只有部門名稱 */
  display_name: string
  company_id: number | null
  company_name: string | null
  ref_department_id: number | null
  source_title: string | null
  sort_order: number
  is_active: boolean
  item_count: number
  key_count: number
  total_score: number
}

export interface KpoItem {
  id: number
  department_id: number
  item_no: number | null
  is_key: boolean
  name: string
  score: number
  method: string | null
  sort_order: number
  is_active: boolean
  in_use: boolean
}

export interface KpoSubtotal {
  item_count: number
  key_count: number
  full_score: number
  pass_count: number
  fail_count: number
  pending_count: number
  earned_score: number
  rate: number | null
  /** 本期分數＝得分÷滿分×100，四捨五入取整數（不呈現 %）；滿分 0 → null */
  score100: number | null
}

export interface KpoLine {
  id: number
  department_id: number
  source_item_id: number | null
  item_no: number | null
  is_key: boolean
  name: string
  score: number
  method: string | null
  result: KpoResult
  remark: string | null
  sort_order: number
}

export interface KpoDeptBlock {
  department_id: number
  department_name: string
  lines: KpoLine[]
  subtotal: KpoSubtotal
}

export interface KpoSheetBrief {
  id: number
  company_id: number
  company_name: string
  dept_count: number
}

/** 公司別稽核單：公司 → 受稽部門 → 稽核項目 */
export interface KpoSheetBlock {
  id: number
  company_id: number
  company_name: string
  departments: KpoDeptBlock[]
  total: KpoSubtotal
}

export interface KpoPeriodSummary {
  id: number
  period: string
  title: string
  note: string | null
  created_at: string | null
  sheets: KpoSheetBrief[]
  dept_count: number
  total: KpoSubtotal
}

export interface KpoPeriodDetail {
  id: number
  period: string
  title: string
  note: string | null
  sheets: KpoSheetBlock[]
  total: KpoSubtotal
}

export interface KpoDeptHistory {
  periods: { period_id: number; period: string; score100: number | null }[]
  period_count: number
  /** 各期本期分數加總 */
  score_sum: number
  /** 分數 ÷ 期別數（1 位小數）；沒有歷史為 null */
  score_avg: number | null
  /** 主檔項目 id → 曾被選定的期別與判定（result null＝未查核） */
  items: Record<string, { period_id: number; period: string; result: 'pass' | 'fail' | null }[]>
}

export interface KpoDashPeriod { period_id: number; period: string; score100: number | null }
export interface KpoDashMonth { avg: number | null; count: number; periods: KpoDashPeriod[] }
export interface KpoDashRow {
  department_id: number
  department_name: string
  /** 1~12 月（沒稽核的月份沒有 key）；同月多期 avg＝各期本期分數平均 */
  months: Record<string, KpoDashMonth>
  period_count: number
  score_sum: number
  /** 年度平均＝各期本期分數 ÷ 期別數；沒稽核為 null */
  avg: number | null
}
export interface KpoDashCompany { company_id: number; company_name: string; rows: KpoDashRow[] }
export interface KpoDashboard { year: number; years: number[]; companies: KpoDashCompany[] }

export const kpoDeptApi = {
  list: () => client.get<KpoDept[]>(`${BASE}/departments`),
  /** 2026-10-11：公司別先隱藏，只傳 name 即可；傳 company_id＋ref_department_id 則名稱取自 settings/company-departments */
  create: (body: { name?: string; company_id?: number; ref_department_id?: number; source_title?: string | null }) =>
    client.post<KpoDept>(`${BASE}/departments`, body),
  update: (id: number, body: Partial<Pick<KpoDept, 'name' | 'source_title' | 'sort_order' | 'is_active' | 'company_id' | 'ref_department_id'>>) =>
    client.put<KpoDept>(`${BASE}/departments/${id}`, body),
}

export const kpoItemApi = {
  list: (departmentId?: number) =>
    client.get<KpoItem[]>(`${BASE}/items`, { params: departmentId ? { department_id: departmentId } : undefined }),
  create: (body: {
    department_id: number; item_no?: number | null; is_key: boolean
    name: string; score?: number | null; method?: string | null
  }) => client.post<KpoItem>(`${BASE}/items`, body),
  update: (id: number, body: Partial<Pick<KpoItem, 'item_no' | 'is_key' | 'name' | 'score' | 'method' | 'sort_order' | 'is_active'>>) =>
    client.put<KpoItem>(`${BASE}/items/${id}`, body),
  remove: (id: number) => client.delete(`${BASE}/items/${id}`),
}

export const kpoPeriodApi = {
  list: () => client.get<KpoPeriodSummary[]>(`${BASE}/periods`),
  get: (id: number) => client.get<KpoPeriodDetail>(`${BASE}/periods/${id}`),
  create: (body: { period: string; title?: string; note?: string | null }) =>
    client.post<KpoPeriodDetail>(`${BASE}/periods`, body),
  update: (id: number, body: { period?: string; title?: string; note?: string | null }) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}`, body),
  remove: (id: number) => client.delete(`${BASE}/periods/${id}`),
  /** 新增公司別稽核單：受稽部門任選現場營運稽核項目的部門，與公司別無連動 */
  createSheet: (id: number, body: { company_id: number; department_ids: number[] }) =>
    client.post<KpoPeriodDetail>(`${BASE}/periods/${id}/sheets`, body),
  removeSheet: (id: number, sheetId: number) =>
    client.delete<KpoPeriodDetail>(`${BASE}/periods/${id}/sheets/${sheetId}`),
  setSheetDepartments: (id: number, sheetId: number, departmentIds: number[]) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/sheets/${sheetId}/departments`, { department_ids: departmentIds }),
  /** 選擇項目視窗：同公司、同部門在其他期別的歷史（不含本期） */
  deptHistory: (id: number, sheetId: number, departmentId: number) =>
    client.get<KpoDeptHistory>(`${BASE}/periods/${id}/sheets/${sheetId}/departments/${departmentId}/history`),
  setSelection: (id: number, sheetId: number, departmentId: number, itemIds: number[]) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/sheets/${sheetId}/selection`, {
      department_id: departmentId, item_ids: itemIds,
    }),
  setDeptOrder: (id: number, sheetId: number, departmentIds: number[]) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/sheets/${sheetId}/dept-order`, { department_ids: departmentIds }),
  setLinesOrder: (id: number, sheetId: number, departmentId: number, lineIds: number[]) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/sheets/${sheetId}/lines-order`, { department_id: departmentId, line_ids: lineIds }),
  updateLine: (id: number, lineId: number, body: {
    name?: string; score?: number; is_key?: boolean; method?: string | null
    result?: 'pass' | 'fail' | ''; remark?: string | null
  }) => client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/lines/${lineId}`, body),
}

export const kpoDashboardApi = {
  /** 年度 Dashboard：公司 × 部門 × 月份的本期分數；不帶 year＝有資料的最新年度 */
  get: (year?: number) => client.get<KpoDashboard>(`${BASE}/dashboard`, { params: year ? { year } : undefined }),
}
