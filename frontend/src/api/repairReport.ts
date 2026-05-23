/**
 * 報修未完成報表 API Client
 * Prefix: /api/v1/repair-report
 */
import apiClient from '@/api/client'

// apiClient 的 baseURL 已設為 /api/v1，此處只需路徑後綴
const BASE = '/repair-report'

// ── 型別定義 ──────────────────────────────────────────────────────────────────

export interface UnifiedCase {
  source:           'hotel' | 'mall'
  source_label:     string
  ragic_id:         string
  case_no:          string
  occurred_at:      string | null
  floor:            string
  repair_type:      string
  title:            string
  status:           string
  responsible_unit: string
  pending_days:     number | null
  is_overdue:       boolean
  synced_at:        string | null
  finance_note:     string
  ragic_url:        string
}

export interface KpiData {
  total_unfinished:   number
  hotel_unfinished:   number
  mall_unfinished:    number
  overdue_count:      number
  avg_pending_days:   number
  max_pending_days:   number
  new_this_month:     number
  new_today:          number
}

export interface FilterOptions {
  statuses:     string[]
  repair_types: string[]
}

export interface UnfinishedCasesResponse {
  items:          UnifiedCase[]
  total:          number
  kpi:            KpiData
  filter_options: FilterOptions
}

export interface UnfinishedCasesParams {
  year:               number
  month:              number
  source?:            'all' | 'hotel' | 'mall'
  status_filter?:     string
  overdue_only?:      boolean
  repair_type_filter?: string
  keyword?:           string
  page?:              number
  page_size?:         number
}

export interface Recipient {
  id:         number
  name:       string
  email:      string
  department: string
  role:       string
  is_active:  boolean
  created_at: string | null
  updated_at: string | null
  created_by: string
  updated_by: string
}

export interface RecipientCreate {
  name:       string
  email:      string
  department?: string
  role?:      string
  is_active?: boolean
}

export interface RecipientUpdate {
  name?:       string
  email?:      string
  department?: string
  role?:       string
  is_active?:  boolean
}

export interface ScheduleSettings {
  id:                       number
  schedule_name:            string
  is_enabled:               boolean
  send_time:                string
  report_year_month_mode:   'current_month' | 'previous_month'
  include_hotel:            boolean
  include_mall:             boolean
  include_excel_attachment: boolean
  email_subject_template:   string
  email_body_template:      string
  created_at:               string | null
  updated_at:               string | null
  updated_by:               string
}

export interface ManualSendRequest {
  year:                    number
  month:                   number
  include_hotel?:          boolean
  include_mall?:           boolean
  include_excel_attachment?: boolean
  recipient_ids?:          number[]
}

export interface SendResult {
  recipient_email: string
  recipient_name:  string
  success:         boolean
  error_message:   string | null
}

export interface ManualSendResponse {
  sent_count:   number
  failed_count: number
  results:      SendResult[]
}

export interface MailLog {
  id:                     number
  send_date:              string
  send_time:              string
  report_year:            number
  report_month:           number
  recipient_email:        string
  recipient_name:         string
  subject:                string
  status:                 'success' | 'failed' | 'skipped'
  error_message:          string | null
  hotel_unfinished_count: number | null
  mall_unfinished_count:  number | null
  total_unfinished_count: number | null
  attachment_filename:    string | null
  created_at:             string | null
}

export interface MailLogListResponse {
  items: MailLog[]
  total: number
}

// ── API 函數 ──────────────────────────────────────────────────────────────────

export const repairReportApi = {
  /** 取得未完成案件（含 KPI + filter_options） */
  getUnfinishedCases: (params: UnfinishedCasesParams) =>
    apiClient.get<UnfinishedCasesResponse>(`${BASE}/unfinished-cases`, { params })
      .then(r => r.data),

  /** 匯出 Excel（產生下載 URL） */
  getExportUrl: (params: Omit<UnfinishedCasesParams, 'page' | 'page_size'>) => {
    const qs = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null && v !== '')
          .map(([k, v]) => [k, String(v)])
      )
    ).toString()
    return `/api/v1${BASE}/export?${qs}`
  },

  // ── 收件人 ────────────────────────────────────────────────────────────────
  listRecipients: () =>
    apiClient.get<Recipient[]>(`${BASE}/recipients`).then(r => r.data),

  createRecipient: (payload: RecipientCreate) =>
    apiClient.post<Recipient>(`${BASE}/recipients`, payload).then(r => r.data),

  updateRecipient: (id: number, payload: RecipientUpdate) =>
    apiClient.put<Recipient>(`${BASE}/recipients/${id}`, payload).then(r => r.data),

  deleteRecipient: (id: number) =>
    apiClient.delete(`${BASE}/recipients/${id}`).then(r => r.data),

  testSendToRecipient: (id: number) =>
    apiClient.post<{ success: boolean; message: string }>(`${BASE}/recipients/${id}/test-send`)
      .then(r => r.data),

  // ── 排程設定 ──────────────────────────────────────────────────────────────
  getSchedule: () =>
    apiClient.get<ScheduleSettings>(`${BASE}/schedule`).then(r => r.data),

  updateSchedule: (payload: Partial<ScheduleSettings>) =>
    apiClient.put<ScheduleSettings>(`${BASE}/schedule`, payload).then(r => r.data),

  // ── 手動寄送 ──────────────────────────────────────────────────────────────
  sendNow: (payload: ManualSendRequest) =>
    apiClient.post<ManualSendResponse>(`${BASE}/send-now`, payload).then(r => r.data),

  // ── 寄送紀錄 ──────────────────────────────────────────────────────────────
  getMailLogs: (params?: {
    year?: number; month?: number; status?: string; email?: string;
    page?: number; page_size?: number
  }) =>
    apiClient.get<MailLogListResponse>(`${BASE}/mail-logs`, { params }).then(r => r.data),
}
