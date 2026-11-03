/**
 * 退件Dashboard API（後端 /api/v1/return-dashboard）
 * 統一經由 @/api/client 的 apiClient。陣列參數用 indexes:null 序列化（company=A&company=B）。
 */
import apiClient from '@/api/client'

const LIST_PARAMS = { paramsSerializer: { indexes: null } } as const

export interface MonthCell {
  month: number
  sent: number
  returned: number
  rate: number | null   // 月退件率（退件÷送件；送件為 0 → null）
}

export interface DeptRow {
  department: string
  cells: MonthCell[]
  year_sent: number
  year_returned: number
  year_rate: number | null
}

export interface CompanyBlock {
  company: string
  rows: DeptRow[]
  months: MonthCell[]
  year_sent: number
  year_returned: number
  year_rate: number | null
}

export interface MatrixResult {
  year: number
  form_type: string
  companies: string[]
  blocks: CompanyBlock[]
  months: MonthCell[]
  year_sent: number
  year_returned: number
  year_rate: number | null
}

export interface DetailItem {
  id: number
  company: string
  form_type: string
  dept: string
  form_name: string
  ragic_record_id: string
  ragic_url: string
  applicant: string | null
  apply_date: string | null
  amount: number | null
  outcome: string
  outcome_label: string
  rejection_note: string | null
  rejection_approver: string | null
  next_approver: string | null
  ragic_status: string | null
}

export interface DetailResult {
  total: number
  truncated: boolean
  items: DetailItem[]
}

export interface DetailQuery {
  year: number
  month: number
  kind: 'sent' | 'returned'
  company?: string[]
  dept?: string[]
  form_type?: string
}

export async function fetchReturnMatrix(year: number, formType: string, companies: string[], rejectionApprover = ''): Promise<MatrixResult> {
  const res = await apiClient.get('/return-dashboard/matrix', {
    params: {
      year, form_type: formType || undefined, company: companies.length ? companies : undefined,
      rejection_approver: rejectionApprover || undefined,
    },
    ...LIST_PARAMS,
  })
  return res.data
}

export async function exportReturnMatrixExcel(year: number, formType: string, companies: string[]) {
  return apiClient.get<Blob>('/return-dashboard/export', {
    params: { year, form_type: formType || undefined, company: companies.length ? companies : undefined },
    responseType: 'blob',
    timeout: 120_000,
    ...LIST_PARAMS,
  })
}

export async function fetchReturnDetail(q: DetailQuery): Promise<DetailResult> {
  const res = await apiClient.get('/return-dashboard/detail', {
    params: {
      year: q.year, month: q.month, kind: q.kind,
      company: q.company?.length ? q.company : undefined,
      dept: q.dept?.length ? q.dept : undefined,
      form_type: q.form_type || undefined,
    },
    ...LIST_PARAMS,
  })
  return res.data
}
