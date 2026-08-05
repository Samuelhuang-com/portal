/**
 * 金旭 PMS 分析 — TypeScript 型別定義
 * 規格書：docs/SPEC_jinxu_analytics.md
 *
 * ⚠️ J17：FCR02 的「備註」欄儲存於 DB 但全站不顯示，後端 API 不回傳，
 *    因此本檔案的任何型別都**不得**出現 remark。
 */

export type JinxuSourceType = 'FCR02_LEDGER' | 'RESV_DETAIL'
export type SubjectSide = 'REVENUE' | 'SETTLEMENT'
export type RoomKind = 'GUEST' | 'OTHER'
export type DateBasis = 'arrival' | 'departure'
export type QualityResult = 'PASS' | 'PASS_WITH_WARNINGS' | 'FAIL'
export type BatchStatus =
  | 'PENDING' | 'VALIDATED' | 'COMMITTED' | 'FAILED' | 'ROLLED_BACK'
export type IssueSeverity = 'ERROR' | 'WARNING' | 'INFO'

/** J27：住宿晚數兩種口徑。業主 2026-08-05 決定預設用 billable（Day Use 算 1 晚）。 */
export type NightsBasis = 'nights' | 'billable'
export const DEFAULT_NIGHTS_BASIS: NightsBasis = 'billable'

// ── 匯入 ─────────────────────────────────────────────────────────────────────

export interface JinxuBatch {
  id: number
  source_type: JinxuSourceType
  source_label: string
  source_file_name: string
  file_size: number
  report_start_date: string
  report_end_date: string
  row_count_data: number
  row_count_inserted: number
  row_count_updated: number
  row_count_skipped: number
  row_count_rejected: number
  row_count_child: number
  status: BatchStatus
  quality_result: QualityResult
  started_at: string
  completed_at: string
  uploaded_by_name: string
  error_message: string
}

export interface JinxuBatchDetail extends JinxuBatch {
  session_id: string
  property_code: string
  property_name: string
  file_sha256: string
  sheet_name: string
  printed_at: string
  row_count_source: number
  program_version: string
  totals: Record<string, unknown>
  reconcile: Record<string, unknown>
  issue_summary: IssueSummary[]
}

export interface IssueSummary {
  error_code: string
  severity: IssueSeverity
  count: number
}

export interface JinxuIssue {
  id: number
  source_row_no: number
  field_name: string
  raw_value: string
  error_code: string
  error_message: string
  severity: IssueSeverity
}

export interface ValidateResult {
  ok: boolean
  error?: string
  detected_source_type?: JinxuSourceType | null
  source_type: JinxuSourceType
  source_label: string
  file_name: string
  file_sha256: string
  file_size: number
  sheet_name: string
  total_source_rows: number
  row_counts: Record<string, number>
  data_rows: number
  child_rows: number
  report_start_date: string
  report_end_date: string
  printed_at: string
  property_name: string
  unknown_subjects: string[]
  duplicate_batch: { id: number; file_name: string; completed_at: string; uploaded_by: string } | null
  quality_result: QualityResult
  can_commit: boolean
  reconcile: Record<string, unknown>
  issue_summary: IssueSummary[]
  issue_samples: JinxuIssue[]
  delta: { insert: number; update: number; skip: number }
}

export interface CommitResult {
  ok: boolean
  message?: string
  batch_id?: number
  source_type: JinxuSourceType
  source_label: string
  quality_result: QualityResult
  row_count_data: number
  row_count_inserted: number
  row_count_updated: number
  row_count_skipped: number
  row_count_rejected: number
  row_count_child: number
  reconcile: Record<string, unknown>
}

export interface RollbackResult {
  ok: boolean
  batch_id: number
  deleted_raw_rows: number
  updated_keys_count: number
  updated_keys: string[]
  warning: string
}

export interface SourceStatus {
  label: string
  row_count: number
  child_count?: number
  date_start: string
  date_end: string
  has_data: boolean
}

export interface ImportStatus {
  sources: Record<JinxuSourceType, SourceStatus>
  cross_analysis_available: boolean
  years_covered: string[]
  yoy_available: boolean
  last_batch: { id: number; source_label: string; file_name: string; completed_at: string; uploaded_by: string } | null
}

// ── 收入 ─────────────────────────────────────────────────────────────────────

export interface RevenueSummary {
  transaction_count: number
  revenue_net: number
  settlement_total: number
  reversal_count: number
  reversal_amount: number
  reversal_rate_by_count: number
  reversal_rate_by_amount: number
  note: string
}

export interface Coverage {
  ledger_start: string
  ledger_end: string
  resv_start: string
  resv_end: string
  years_covered: string[]
  yoy_available: boolean
  period_label?: string
}

export interface SubjectRow {
  key: string
  label: string
  count: number
  amount: number
  share_pct: number
  reversal_count: number
}

export interface MonthlyGroupRow {
  month: string
  total: number
  groups: Record<string, { label: string; amount: number; count: number }>
}

export interface DailyRow {
  business_date: string
  revenue_net: number
  settlement_total: number
  transaction_count: number
}

export interface RoomKindRow {
  room_kind: RoomKind
  label: string
  count: number
  amount: number
  subjects: { subject_code: string; subject_name: string; count: number; amount: number }[]
}

export interface ShiftRow {
  shift: string
  count: number
  amount: number
  reversal_count?: number
}

// ── 付款 ─────────────────────────────────────────────────────────────────────

export interface PaymentSummary {
  total: number
  by_subject: { subject_code: string; subject_name: string; count: number; amount: number; share_pct: number }[]
  by_macro: { key: string; label: string; count: number; amount: number; share_pct: number }[]
  note: string
}

// ── 訂金 ─────────────────────────────────────────────────────────────────────

export interface DepositSummary {
  inflow_count: number
  inflow_amount: number
  outflow_count: number
  outflow_amount: number
  net_balance: number
  data_start_date: string
  warning: string
  note: string
}

export interface DepositMonthRow {
  month: string
  inflow: number
  outflow: number
  net: number
  cumulative_balance: number
}

// ── 訂房 ─────────────────────────────────────────────────────────────────────

export interface ResvMetrics {
  reservation_count: number
  room_nights: number
  quoted_amount: number
  adr: number
  avg_nights: number
  avg_billable_nights: number
}

export interface ResvSummary extends ResvMetrics {
  total_count_incl_cancelled: number
  cancelled_count: number
  cancel_rate_by_count: number
  no_show_count: number
  population_note: string
  nights_note: string
}

export interface ResvGroupRow extends ResvMetrics {
  key: string
  label: string
  room_nights_share_pct: number
  amount_share_pct: number
}

export interface ResvGroupResult {
  total_room_nights: number
  total_quoted_amount: number
  items: ResvGroupRow[]
  population_note: string
  note?: string
}

export interface RoomTypeRow {
  room_type_code: string
  label: string
  reservation_count: number
  segment_count: number
  room_nights: number
  quoted_amount: number
  adr: number
  room_nights_share_pct: number
}

export interface ResvMonthRow extends ResvMetrics {
  month: string
}

export interface StatusRow {
  status_code: string
  label: string
  count: number
  share_pct: number
  room_nights: number
  excluded_from_stats: boolean
}

// ── 取消 ─────────────────────────────────────────────────────────────────────

export interface CancellationSummary {
  total_count: number
  cancelled_count: number
  cancel_rate_by_count: number
  total_room_nights: number
  cancelled_room_nights: number
  cancel_rate_by_room_nights: number
  cancelled_quoted_amount: number
  no_show_count: number
  no_show_rate: number
  population_note: string
  note: string
}

export interface CancellationGroupRow {
  key: string
  label: string
  total_count: number
  cancelled_count: number
  cancel_rate_by_count: number
  total_room_nights: number
  cancelled_room_nights: number
  cancel_rate_by_room_nights: number
  cancelled_quoted_amount: number
}

export interface CancellationMonthRow {
  month: string
  total_count: number
  cancelled_count: number
  cancel_rate_by_count: number
  cancel_rate_by_room_nights: number
  cancelled_quoted_amount: number
}

// ── 訂價 vs 實收 ─────────────────────────────────────────────────────────────

export interface RateGapRow {
  booking_no: string
  status_code: string
  arrival_date: string
  departure_date: string
  company_name: string
  room_type_codes: string
  room_nights: number
  quoted_amount: number
  actual_amount: number
  gap: number
  gap_pct: number
}

export interface RateGapResult {
  available: boolean
  reason?: string
  matched_count: number
  quoted_total: number
  actual_total: number
  gap_total: number
  gap_pct: number
  exact_match_count: number
  exact_match_pct: number
  flagged_count: number
  flagged: RateGapRow[]
  subject_scope: string
  gap_definition: string
  note: string
}

// ── 回訪 ─────────────────────────────────────────────────────────────────────

export interface RepeatGuestRow {
  guest_name_masked: string
  visit_count: number
  room_nights: number
  quoted_amount: number
  first_arrival: string
  last_arrival: string
  channel_count: number
}

export interface RepeatGuestResult {
  unique_guests: number
  repeat_guests: number
  repeat_guest_rate: number
  total_stays: number
  repeat_stays: number
  repeat_stay_rate: number
  min_visits: number
  items: RepeatGuestRow[]
  population_note: string
  note: string
}

// ── 明細 ─────────────────────────────────────────────────────────────────────

/** ⚠️ J17：刻意不含 remark。後端也不回傳。 */
export interface LedgerEntry {
  id: number
  create_seq: string
  business_date: string
  created_at_text: string
  shift: string
  operator_id: string
  room_no: string
  room_kind: RoomKind
  folio_name: string
  folio_seq: number | null
  folio_type: string
  subject_code: string
  subject_name: string
  subject_side: SubjectSide
  subject_group: string
  subject_group_label: string
  amount: number
  is_reversal: number
  is_memo_only: number
  booking_no: string
  document_no: string
  ar_code: string
  transfer_no: string
}

export interface LedgerEntryDetail extends LedgerEntry {
  related_entries?: LedgerEntry[]
  reservation?: Reservation | null
}

export interface Reservation {
  id: number
  booking_no: string
  status_code: string
  status_label: string
  is_cancelled: number
  is_dummy: number
  is_no_show: number
  arrival_date: string
  departure_date: string
  nights: number
  billable_nights: number
  is_day_use: number
  guest_name_masked: string
  guest_is_placeholder: number
  company_name: string
  rate_code: string
  source_name: string
  resv_type: string
  is_group: number
  stay_segment_count: number
  total_room_nights: number
  total_quoted_amount: number
  room_type_codes: string
  has_nights_mismatch: number
}

export interface StaySegment {
  seq_no: number
  room_type_code: string
  rooms: number
  nights: number
  amount_per_night: number
  unit_rate: number
  room_nights: number
  segment_amount: number
  has_n_suffix: number
  raw_segment: string
}

export interface ReservationDetail extends Reservation {
  segments: StaySegment[]
  ledger_entries: LedgerEntry[]
  ledger_available: boolean
  rate_comparison: {
    quoted_amount: number
    actual_room_revenue: number
    gap: number
    gap_pct: number
  } | null
}

// ── 設定 ─────────────────────────────────────────────────────────────────────

export interface SubjectMapRow {
  subject_code: string
  subject_name: string
  side: SubjectSide
  side_label: string
  group_code: string
  group_label: string
  sort_order: number
  is_memo_only: number
  is_active: number
  updated_at: string
}

export interface ThresholdRow {
  setting_key: string
  setting_value: string
  value_type: string
  description: string
  updated_at: string
}

// ── 共用分頁 ─────────────────────────────────────────────────────────────────

export interface Paged<T> {
  total: number
  page: number
  page_size: number
  items: T[]
  population_note?: string
}
