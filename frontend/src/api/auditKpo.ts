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

export interface KpoPeriodSummary {
  id: number
  period: string
  title: string
  note: string | null
  created_at: string | null
  dept_count: number
  total: KpoSubtotal
}

export interface KpoPeriodDetail {
  id: number
  period: string
  title: string
  note: string | null
  /** 本期自訂的部門順序（空＝依主檔） */
  dept_order: number[]
  departments: KpoDeptBlock[]
  total: KpoSubtotal
}

export const kpoDeptApi = {
  list: () => client.get<KpoDept[]>(`${BASE}/departments`),
  /** 公司別＋部門別一律取自 settings/company-departments 主檔 */
  create: (body: { company_id: number; ref_department_id: number; source_title?: string | null }) =>
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
  setSelection: (id: number, departmentId: number, itemIds: number[]) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/selection`, {
      department_id: departmentId, item_ids: itemIds,
    }),
  setDeptOrder: (id: number, departmentIds: number[]) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/dept-order`, { department_ids: departmentIds }),
  setLinesOrder: (id: number, departmentId: number, lineIds: number[]) =>
    client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/lines-order`, { department_id: departmentId, line_ids: lineIds }),
  updateLine: (id: number, lineId: number, body: {
    name?: string; score?: number; is_key?: boolean; method?: string | null
    result?: 'pass' | 'fail' | ''; remark?: string | null
  }) => client.put<KpoPeriodDetail>(`${BASE}/periods/${id}/lines/${lineId}`, body),
}
