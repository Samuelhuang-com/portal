/**
 * OPERA 營運分析 — TypeScript 型別定義
 * 規格書：docs/SPEC_opera_analytics.md §10
 *
 * ⚠️ 資料口徑（決策 D7）：
 *    營收／ADR／住房率／RevPAR → History and Forecast
 *    通路／房型／Rate Code／住客 → Departure All
 *    兩者不互相驗算房晚，畫面必須標註來源。
 */

// ── 共用 ─────────────────────────────────────────────────────────────────────

export type OperaSourceType = 'DEPARTURE' | 'HISTORY_FORECAST'
export type OperaRecordType = 'History' | 'Forecast'
export type OperaBasis = 'room' | 'reservation'
export type QuadrantBasis = 'common' | 'annual'
export type QualityResult = 'PASS' | 'PASS_WITH_WARNINGS' | 'FAIL'
export type BatchStatus = 'PENDING' | 'VALIDATED' | 'COMMITTED' | 'FAILED' | 'ROLLED_BACK'

export type PeriodType =
  | 'FULL_YEAR' | 'PARTIAL_YEAR' | 'FULL_MONTH' | 'PARTIAL_MONTH' | 'CUSTOM'

export interface PeriodInfo {
  start: string
  end: string
  period_type: PeriodType
  period_label: string
  compare_start: string
  compare_end: string
  compare_label: string
  data_days: number
  expected_days: number
  is_complete: boolean
}

// ── 營收 ─────────────────────────────────────────────────────────────────────

export interface RevenueAggregate {
  revenue: number
  sold_rooms: number
  available_rooms: number
  inventory_rooms: number
  ooo_rooms: number
  days: number
  adr: number
  occupancy: number      // 0~1
  revpar: number
}

export interface RevenueKpi {
  period: PeriodInfo
  current: RevenueAggregate
  compare: RevenueAggregate
  forecast: RevenueAggregate | null
  yoy: {
    revenue: number | null
    adr: number | null
    revpar: number | null
    sold_rooms: number | null
    occupancy_ppt: number
  }
  has_compare_data: boolean
  source_label: string
}

export interface RevenueDailyRow {
  id: number
  raw_id: number
  batch_id: number
  record_type: OperaRecordType
  business_date: string
  revenue: number
  sold_rooms: number
  available_rooms: number
  inventory_rooms: number
  ooo_rooms: number
  adr: number
  occupancy: number
  revpar: number
  individual_rooms: number
  group_rooms: number
  individual_revenue: number
  group_revenue: number
  arrival_rooms: number
  departure_rooms: number
  no_persons: number
  detail: Record<string, string>
}

export interface RevenueMonthRow {
  year: number
  month: number
  label: string
  period_type: PeriodType
  period_label: string
  compare_label: string
  current: RevenueAggregate
  compare: RevenueAggregate
  revenue_yoy: number | null
  adr_yoy: number | null
  occupancy_ppt: number
  has_compare: boolean
}

export interface RevenueMonthlyResult {
  year: number
  months: RevenueMonthRow[]
  total: RevenueAggregate
  source_label: string
}

export interface RevenueYearRow extends RevenueAggregate {
  year: number
  period_type: PeriodType
  period_label: string
  data_days: number
  expected_days: number
  is_complete: boolean
  revenue_yoy: number | null
  adr_yoy: number | null
  occupancy_ppt: number | null
  comparable: boolean
}

export interface QuadrantPoint {
  business_date: string
  year: string
  adr: number
  occupancy: number
  revenue: number
  sold_rooms: number
  quadrant: 'Q1' | 'Q2' | 'Q3' | 'Q4'
  quadrant_label: string
}

export interface QuadrantResult {
  basis: QuadrantBasis
  basis_label: string
  baseline: { adr: number; occupancy: number }
  annual_baselines: Record<string, { adr: number; occupancy: number }>
  points: QuadrantPoint[]
  counts: Record<string, number>
  source_label: string
}

export interface AnomalyRow {
  business_date: string
  month: string
  revenue: number
  sold_rooms: number
  available_rooms: number
  ooo_rooms: number
  adr: number
  occupancy: number
  revpar: number
  annual_occupancy: number
  occupancy_diff: number
  fixed_reasons: string[]
  annual_reasons: string[]
  reasons: string[]
  trigger_source: '固定門檻' | '年度基準' | '兩者'
}

export interface AnomalyResult {
  settings: Record<string, number>
  baseline: { adr: number; occupancy: number }
  items: AnomalyRow[]
  total: number
  type_counts: Record<string, number>
  monthly_series: Array<Record<string, string | number>>
  source_label: string
}

export interface SegmentResult {
  segments: Array<{
    key: string
    label: string
    rooms: number
    revenue: number
    revenue_share: number
    rooms_share: number
    adr: number
  }>
  detail: Record<string, { rooms: number; revenue: number }>
  source_label: string
}

// ── 住客與通路 ───────────────────────────────────────────────────────────────

/**
 * ⚠️ 兒童數的欄位名是 `child_count`，**不可**叫 `children`。
 *    Ant Design Table 預設把 `record.children` 當成「子列陣列」
 *    （`childrenColumnName` 預設值就是 `'children'`），值是數字時
 *    Table 會去跑 `2.forEach()` 直接整頁白畫面（2026-08-04 實際踩過）。
 *    任何要當 Table dataSource 的型別都適用這條規則。
 */
export interface StayRow {
  id: number
  raw_id: number
  batch_id: number
  record_key: string
  departure_date: string
  arrival_date: string
  departure_time: string
  room_no: string
  room_category_label: string
  nights: number
  no_of_rooms: number
  room_nights: number
  adults: number
  child_count: number
  channel: string
  travel_agent_name: string
  company_name: string
  rate_code: string
  payment_desc: string
  guest_name_masked: string
  is_purged: number
  vip: string
  detail: Record<string, string>
}

export interface StayListResult {
  items: StayRow[]
  total: number
  page: number
  page_size: number
  basis: OperaBasis
  basis_label: string
  source_label: string
}

export interface DimensionItem {
  key: string
  records: number
  room_nights: number
  nights: number
  adults: number
  child_count: number    // ⚠️ 不可叫 children，理由見 StayRow 上方說明
  share: number
  cumulative_share: number
}

export interface DimensionResult {
  dimension: string
  dimension_label: string
  basis: OperaBasis
  basis_label: string
  metric: 'room_nights' | 'records'
  metric_label: string
  items: DimensionItem[]
  total_records: number
  total_metric: number
  truncated: boolean
  source_label: string
}

export interface PurgeCoverage {
  total: number
  purged: number
  identified: number
  coverage: number
}

export interface RepeatGuestResult {
  distribution: Array<{ label: string; guests: number }>
  top_guests: Array<{
    guest_hash: string
    guest_label: string
    visits: number
    room_nights: number
    nights: number
    last_departure: string
  }>
  total_guests: number
  repeat_guests: number
  repeat_rate: number
  coverage: PurgeCoverage
  basis: OperaBasis
  basis_label: string
  source_label: string
}

export interface LongStayResult {
  threshold: number
  distribution: Array<{
    nights: number
    records: number
    room_nights: number
    is_long_stay: boolean
  }>
  long_records: number
  total_records: number
  long_rate: number
  basis: OperaBasis
  basis_label: string
  source_label: string
}

export interface StaySummaryBasis {
  records: number
  room_nights: number
  nights: number
  adults: number
  child_count: number    // ⚠️ 不可叫 children，理由見 StayRow 上方說明
  rooms: number
  basis_label: string
}

export interface StaySummaryResult {
  room: StaySummaryBasis
  reservation: StaySummaryBasis
  coverage: PurgeCoverage
  source_label: string
}

// ── 匯入 ─────────────────────────────────────────────────────────────────────

export interface QualityCheck {
  name: string
  ok: boolean
  detail: string
  fatal: boolean
}

export interface ReconcileItem {
  label: string
  footer_key: string
  footer_value: number
  computed_value: number
  diff: number
  ok: boolean
}

export interface ReconcileResult {
  ok: boolean
  items: ReconcileItem[]
}

export interface ImportIssue {
  source_row_no: number
  field_name: string
  raw_value: string
  error_code: string
  error_message: string
  severity: 'ERROR' | 'WARNING'
}

export interface ValidateResult {
  source_type: OperaSourceType
  source_label: string
  file_name: string
  file_size: number
  file_sha256: string
  encoding: string
  property_code: string
  report_start_date: string
  report_end_date: string
  row_count_source: number
  row_count_valid: number
  row_count_rejected: number
  merged_pairs: number
  stats: Record<string, number>
  footer: Record<string, string>
  reconcile: ReconcileResult
  quality_result: QualityResult
  quality_checks: QualityCheck[]
  duplicate: { batch_id: number; file_name: string; imported_at: string } | null
  file_state: 'NEW' | 'UPDATED' | 'DUPLICATE'
  delta: { will_insert: number; will_update: number; will_skip: number }
  issues: ImportIssue[]
  issue_total: number
  can_commit: boolean
  needs_warning_ack: boolean
}

export interface CommitResult {
  batch_id: number
  session_id: string
  source_type: OperaSourceType
  source_label: string
  quality_result: QualityResult
  quality_checks: QualityCheck[]
  reconcile: ReconcileResult
  stats: Record<string, number>
  inserted: number
  updated: number
  skipped: number
  rejected: number
  issue_total: number
  report_start_date: string
  report_end_date: string
}

export interface ImportBatch {
  id: number
  session_id: string
  source_type: OperaSourceType
  source_label: string
  property_code: string
  source_file_name: string
  file_sha256: string
  file_size: number
  encoding: string
  report_start_date: string
  report_end_date: string
  row_count_source: number
  row_count_inserted: number
  row_count_updated: number
  row_count_skipped: number
  row_count_rejected: number
  status: BatchStatus
  quality_result: QualityResult | ''
  footer: Record<string, string>
  reconcile: {
    footer?: ReconcileResult
    quality_checks?: QualityCheck[]
    stats?: Record<string, number>
  }
  started_at: string
  completed_at: string
  uploaded_by_name: string
  program_version: string
  error_message: string
  detail: Record<string, string>
}

export interface CoverageRange {
  start: string
  end: string
  rows: number
}

export interface ImportStatus {
  departure: CoverageRange
  history: CoverageRange
  forecast: CoverageRange
  coverage_by_year: Record<string, Record<string, number>>
  missing_history_years: string[]
  last_batch: ImportBatch | null
  has_data: boolean
}

export interface RawRowResult {
  id: number
  batch_id: number
  source_row_no: number
  source_row_no_end: number
  row_hash: string
  record_key: string
  imported_at: string
  fields: Record<string, string>
}

// ── Dashboard ────────────────────────────────────────────────────────────────

export interface OperaDashboard {
  has_data: boolean
  year?: number
  available_years?: number[]
  status: ImportStatus
  kpi?: RevenueKpi
  monthly?: RevenueMonthlyResult
  segment?: SegmentResult
  stay_summary?: StaySummaryResult
  anomaly_summary?: {
    total: number
    type_counts: Record<string, number>
    monthly_series: Array<Record<string, string | number>>
  }
}

// ── 設定 ─────────────────────────────────────────────────────────────────────

export interface AnalysisSetting {
  setting_key: string
  setting_value: number
  default_value: number
  value_type: 'int' | 'float'
  description: string
  is_default: boolean
  updated_at: string
  updated_by_name: string
}
