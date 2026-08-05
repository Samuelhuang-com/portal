/**
 * 金旭 PMS 分析 API 封裝
 * 所有對 /api/v1/jinxu/* 的請求統一在此處理（不在元件內直接用 axios）
 *
 * 路由前綴 /jinxu/*，與 /opera/* 完全獨立，不共用任何端點（業主指定不混用）。
 */
import apiClient from '@/api/client'
import type {
  CancellationGroupRow,
  CancellationMonthRow,
  CancellationSummary,
  CommitResult,
  Coverage,
  DailyRow,
  DepositMonthRow,
  DepositSummary,
  ImportStatus,
  JinxuBatch,
  JinxuBatchDetail,
  JinxuIssue,
  JinxuSourceType,
  LedgerEntry,
  LedgerEntryDetail,
  MonthlyGroupRow,
  Paged,
  PaymentSummary,
  RateGapResult,
  RepeatGuestResult,
  Reservation,
  ReservationDetail,
  ResvGroupResult,
  ResvMonthRow,
  ResvSummary,
  RevenueSummary,
  RollbackResult,
  RoomKindRow,
  RoomTypeRow,
  ShiftRow,
  StatusRow,
  SubjectMapRow,
  SubjectRow,
  ThresholdRow,
  ValidateResult,
} from '@/types/jinxu'

const P = '/jinxu'

export interface LedgerFilters {
  start_date?: string
  end_date?: string
  subject_code?: string
  subject_group?: string
  room_kind?: string
  shift?: string
  operator_id?: string
  folio_type?: string
  booking_no?: string
  include_reversal?: boolean
  include_memo?: boolean
}

export interface ResvFilters {
  start_date?: string
  end_date?: string
  date_basis?: 'arrival' | 'departure'
  company_name?: string
  rate_code?: string
  source_name?: string
  resv_type?: string
  status_code?: string
  include_cancelled?: boolean
}

// ── 匯入 ─────────────────────────────────────────────────────────────────────

export async function validateFile(
  file: File,
  sourceType?: JinxuSourceType,
): Promise<ValidateResult> {
  const fd = new FormData()
  fd.append('file', file)
  if (sourceType) fd.append('source_type', sourceType)
  const { data } = await apiClient.post(`${P}/import/validate`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300_000, // 解析 2.8 MB xlsx 約需 4~8 秒，放寬逾時
  })
  return data
}

export async function commitFile(
  file: File,
  sourceType?: JinxuSourceType,
  sessionId?: string,
): Promise<CommitResult> {
  const fd = new FormData()
  fd.append('file', file)
  if (sourceType) fd.append('source_type', sourceType)
  if (sessionId) fd.append('session_id', sessionId)
  const { data } = await apiClient.post(`${P}/import/commit`, fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600_000, // 40,706 筆首次匯入實測約 9 秒，仍放寬以防正式區較慢
  })
  return data
}

export async function fetchBatches(params: {
  source_type?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<Paged<JinxuBatch>> {
  const { data } = await apiClient.get(`${P}/import/batches`, { params })
  return data
}

export async function fetchBatch(id: number): Promise<JinxuBatchDetail> {
  const { data } = await apiClient.get(`${P}/import/batches/${id}`)
  return data
}

export async function fetchBatchErrors(
  id: number,
  params: { severity?: string; error_code?: string; page?: number; page_size?: number },
): Promise<Paged<JinxuIssue>> {
  const { data } = await apiClient.get(`${P}/import/batches/${id}/errors`, { params })
  return data
}

export function batchErrorsCsvUrl(id: number): string {
  return `/api/v1${P}/import/batches/${id}/errors.csv`
}

export async function rollbackBatch(id: number): Promise<RollbackResult> {
  const { data } = await apiClient.post(`${P}/import/batches/${id}/rollback`)
  return data
}

export async function fetchImportStatus(): Promise<ImportStatus> {
  const { data } = await apiClient.get(`${P}/import/status`)
  return data
}

// ── 收入 ─────────────────────────────────────────────────────────────────────

export async function fetchRevenueSummary(f: LedgerFilters): Promise<RevenueSummary> {
  const { data } = await apiClient.get(`${P}/revenue/summary`, { params: f })
  return data
}

export async function fetchCoverage(
  start_date = '', end_date = '',
): Promise<Coverage> {
  const { data } = await apiClient.get(`${P}/revenue/coverage`, {
    params: { start_date, end_date },
  })
  return data
}

export async function fetchRevenueBySubject(
  f: LedgerFilters, groupBy: 'code' | 'group' = 'code',
): Promise<{ total: number; group_by: string; items: SubjectRow[] }> {
  const { data } = await apiClient.get(`${P}/revenue/by-subject`, {
    params: { ...f, group_by: groupBy },
  })
  return data
}

export async function fetchRevenueMonthly(
  f: LedgerFilters,
): Promise<{ items: MonthlyGroupRow[] }> {
  const { data } = await apiClient.get(`${P}/revenue/monthly`, { params: f })
  return data
}

export async function fetchRevenueDaily(f: LedgerFilters): Promise<{ items: DailyRow[] }> {
  const { data } = await apiClient.get(`${P}/revenue/daily`, { params: f })
  return data
}

export async function fetchRevenueByRoomKind(
  start_date = '', end_date = '',
): Promise<{ items: RoomKindRow[]; note: string }> {
  const { data } = await apiClient.get(`${P}/revenue/by-room-kind`, {
    params: { start_date, end_date },
  })
  return data
}

export async function fetchShifts(
  start_date = '', end_date = '',
): Promise<{ shifts: ShiftRow[]; excluded_shifts: ShiftRow[]; note: string }> {
  const { data } = await apiClient.get(`${P}/revenue/shifts`, {
    params: { start_date, end_date },
  })
  return data
}

export async function fetchLedgerEntries(
  f: LedgerFilters, page = 1, pageSize = 50,
): Promise<Paged<LedgerEntry>> {
  const { data } = await apiClient.get(`${P}/revenue/entries`, {
    params: { ...f, page, page_size: pageSize },
  })
  return data
}

export async function fetchLedgerEntry(id: number): Promise<LedgerEntryDetail> {
  const { data } = await apiClient.get(`${P}/revenue/entries/${id}`)
  return data
}

// ── 付款 ─────────────────────────────────────────────────────────────────────

export async function fetchPaymentSummary(
  start_date = '', end_date = '', room_kind?: string,
): Promise<PaymentSummary> {
  const { data } = await apiClient.get(`${P}/payment/summary`, {
    params: { start_date, end_date, room_kind },
  })
  return data
}

export async function fetchPaymentMonthly(
  start_date = '', end_date = '',
): Promise<{ items: MonthlyGroupRow[] }> {
  const { data } = await apiClient.get(`${P}/payment/monthly`, {
    params: { start_date, end_date },
  })
  return data
}

export async function fetchPaymentEntries(
  params: { start_date?: string; end_date?: string; subject_code?: string; page?: number; page_size?: number },
): Promise<Paged<LedgerEntry>> {
  const { data } = await apiClient.get(`${P}/payment/entries`, { params })
  return data
}

// ── 訂金 ─────────────────────────────────────────────────────────────────────

export async function fetchDepositSummary(
  start_date = '', end_date = '',
): Promise<DepositSummary> {
  const { data } = await apiClient.get(`${P}/deposit/summary`, {
    params: { start_date, end_date },
  })
  return data
}

export async function fetchDepositMonthly(
  start_date = '', end_date = '',
): Promise<{ items: DepositMonthRow[] }> {
  const { data } = await apiClient.get(`${P}/deposit/monthly`, {
    params: { start_date, end_date },
  })
  return data
}

export async function fetchDepositEntries(
  params: { start_date?: string; end_date?: string; direction?: 'all' | 'in' | 'out'; page?: number; page_size?: number },
): Promise<Paged<LedgerEntry>> {
  const { data } = await apiClient.get(`${P}/deposit/entries`, { params })
  return data
}

// ── 訂房 ─────────────────────────────────────────────────────────────────────

export async function fetchResvSummary(f: ResvFilters): Promise<ResvSummary> {
  const { data } = await apiClient.get(`${P}/reservation/summary`, { params: f })
  return data
}

export async function fetchResvByChannel(f: ResvFilters): Promise<ResvGroupResult> {
  const { data } = await apiClient.get(`${P}/reservation/by-channel`, { params: f })
  return data
}

export async function fetchResvByRoomType(
  f: ResvFilters,
): Promise<{ total_room_nights: number; total_quoted_amount: number; items: RoomTypeRow[]; population_note: string; note: string }> {
  const { data } = await apiClient.get(`${P}/reservation/by-roomtype`, { params: f })
  return data
}

export async function fetchResvByRateCode(f: ResvFilters): Promise<ResvGroupResult> {
  const { data } = await apiClient.get(`${P}/reservation/by-ratecode`, { params: f })
  return data
}

export async function fetchResvBySource(f: ResvFilters): Promise<ResvGroupResult> {
  const { data } = await apiClient.get(`${P}/reservation/by-source`, { params: f })
  return data
}

export async function fetchResvByType(f: ResvFilters): Promise<ResvGroupResult> {
  const { data } = await apiClient.get(`${P}/reservation/by-type`, { params: f })
  return data
}

export async function fetchResvMonthly(
  f: ResvFilters,
): Promise<{ date_basis: string; items: ResvMonthRow[]; population_note: string }> {
  const { data } = await apiClient.get(`${P}/reservation/monthly`, { params: f })
  return data
}

export async function fetchStatusBreakdown(
  start_date = '', end_date = '',
): Promise<{ items: StatusRow[] }> {
  const { data } = await apiClient.get(`${P}/reservation/status-breakdown`, {
    params: { start_date, end_date },
  })
  return data
}

export async function fetchResvList(
  f: ResvFilters, page = 1, pageSize = 50,
): Promise<Paged<Reservation>> {
  const { data } = await apiClient.get(`${P}/reservation/list`, {
    params: { ...f, page, page_size: pageSize },
  })
  return data
}

export async function fetchResvDetail(id: number): Promise<ReservationDetail> {
  const { data } = await apiClient.get(`${P}/reservation/list/${id}`)
  return data
}

// ── 取消分析（需 jinxu_cancel_view）──────────────────────────────────────────

export async function fetchCancellation(f: ResvFilters): Promise<CancellationSummary> {
  const { data } = await apiClient.get(`${P}/reservation/cancellation`, { params: f })
  return data
}

export async function fetchCancellationByChannel(
  f: ResvFilters,
): Promise<{ items: CancellationGroupRow[]; population_note: string; note: string }> {
  const { data } = await apiClient.get(`${P}/reservation/cancellation/by-channel`, { params: f })
  return data
}

export async function fetchCancellationByRateCode(
  f: ResvFilters,
): Promise<{ items: CancellationGroupRow[]; population_note: string; note: string }> {
  const { data } = await apiClient.get(`${P}/reservation/cancellation/by-ratecode`, { params: f })
  return data
}

export async function fetchCancellationMonthly(
  f: ResvFilters,
): Promise<{ items: CancellationMonthRow[]; population_note: string; note: string }> {
  const { data } = await apiClient.get(`${P}/reservation/cancellation/monthly`, { params: f })
  return data
}

export async function fetchRateGap(
  f: ResvFilters, gapAlertPct = 10, limit = 200,
): Promise<RateGapResult> {
  const { data } = await apiClient.get(`${P}/reservation/rate-gap`, {
    params: { ...f, gap_alert_pct: gapAlertPct, limit },
  })
  return data
}

export async function fetchRepeatGuests(
  f: ResvFilters, minVisits = 2, limit = 200,
): Promise<RepeatGuestResult> {
  const { data } = await apiClient.get(`${P}/reservation/repeat-guests`, {
    params: { ...f, min_visits: minVisits, limit },
  })
  return data
}

// ── 設定 ─────────────────────────────────────────────────────────────────────

export async function fetchSubjects(
  includeInactive = false,
): Promise<{ items: SubjectMapRow[]; group_options: { value: string; label: string }[]; note: string }> {
  const { data } = await apiClient.get(`${P}/settings/subjects`, {
    params: { include_inactive: includeInactive },
  })
  return data
}

export async function updateSubject(
  code: string, payload: Partial<SubjectMapRow>,
): Promise<SubjectMapRow> {
  const { data } = await apiClient.put(`${P}/settings/subjects/${code}`, payload)
  return data
}

export async function fetchThresholds(): Promise<{ items: ThresholdRow[] }> {
  const { data } = await apiClient.get(`${P}/settings/thresholds`)
  return data
}

export async function updateThreshold(
  setting_key: string, setting_value: string,
): Promise<{ setting_key: string; setting_value: string }> {
  const { data } = await apiClient.put(`${P}/settings/thresholds`, { setting_key, setting_value })
  return data
}
