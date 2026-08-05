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

// ── 星期績效 / OOO 損失 / 趨勢（2026-08-04 新增）────────────────────────────

export interface WeekdayRow {
  weekday: number          // 0 = 星期一
  label: string
  days: number
  revenue: number
  sold_rooms: number
  available_rooms: number
  ooo_rooms: number
  adr: number
  occupancy: number
  revpar: number
  avg_daily_revenue: number
  adr_vs_overall: number
  occupancy_vs_overall: number
}

export interface WeekdayPerformanceResult {
  weekdays: WeekdayRow[]
  baseline: { adr: number; occupancy: number; revpar: number }
  min_days: number
  thin_data: boolean
  source_label: string
}

export interface OooLossRow {
  business_date: string
  month: string
  ooo_rooms: number
  inventory_rooms: number
  available_rooms: number
  sold_rooms: number
  revenue: number
  adr: number
  occupancy: number
  est_loss: number
  net_revpar: number
  physical_revpar: number
  denominator_effect: number
}

export interface OooLossResult {
  items: OooLossRow[]
  total_days: number
  total_ooo_rooms: number
  total_est_loss: number
  loss_share: number
  period_revenue: number
  net_revpar: number
  physical_revpar: number
  denominator_effect: number
  sum_available_rooms: number
  sum_inventory_rooms: number
  monthly_series: Array<{ month: string; ooo_rooms: number; est_loss: number; days: number }>
  source_label: string
  disclaimer: string
}

export interface TrendDailyRow {
  business_date: string
  revenue: number
  ma7: number
  ma28: number
  rel_ma28: number | null
  momentum: number
}

export interface TrendMonthRow extends RevenueAggregate {
  month: string
  label: string
  revenue_mom: number | null
  adr_mom: number | null
  revpar_mom: number | null
  occupancy_mom_ppt: number | null
  is_partial: boolean
}

export interface TrendResult {
  daily: TrendDailyRow[]
  monthly: TrendMonthRow[]
  warmup_start: string
  source_label: string
  note: string
}

// ── 退房時間 / 入退房星期（2026-08-04 新增）──────────────────────────────────

export interface CheckoutTimeResult {
  buckets: Array<{ label: string; records: number; share: number }>
  total_records: number
  missing_records: number
  missing_share: number
  basis: OperaBasis
  basis_label: string
  source_label: string
  note: string
}

export interface StayWeekdayRow {
  weekday: number
  label: string
  arrival_rooms: number
  departure_rooms: number
  arrival_share: number
  departure_share: number
  net_rooms: number
}

export interface StayWeekdayResult {
  weekdays: StayWeekdayRow[]
  total_arrival_rooms: number
  total_departure_rooms: number
  basis: OperaBasis
  basis_label: string
  source_label: string
}

// ── 房號使用 / 營運指標 / 客群結構（2026-08-04 新增）─────────────────────────

export interface RoomUsageRow {
  room_no: string
  floor: string
  records: number
  share: number
  vs_avg: number
  monthly: number[]
  active_months: number
  zero_months: number
  first_month: string
  last_month: string
  trailing_zero_months: number
  suspicious_zero_months: number
  suspected_inactive: boolean
}

export interface RoomUsageResult {
  rooms: RoomUsageRow[]
  months: string[]
  monthly_occupancy: number[]
  floors: Array<{ floor: string; records: number; rooms: number; avg_per_room: number; share: number }>
  total_records: number
  room_count: number
  avg_per_room: number
  busiest: number
  quietest: number
  spread_ratio: number | null
  suspected_inactive_count: number
  inactive_months_threshold: number
  basis: OperaBasis
  basis_label: string
  source_label: string
  inference_note: string
}

export interface OperationsResult {
  days: number
  persons: number
  sold_rooms: number
  persons_per_room: number
  arrival_rooms: number
  departure_rooms: number
  turnover_rooms: number
  avg_daily_arrival: number
  avg_daily_departure: number
  avg_daily_turnover: number
  turnover_rate: number
  avg_inventory: number
  stayover_rooms: number
  non_revenue: {
    complimentary: number
    house_use: number
    day_use: number
    no_show: number
    total: number
    share_of_sold: number
  }
  daily: Array<{
    business_date: string
    arrival_rooms: number
    departure_rooms: number
    turnover_rooms: number
    sold_rooms: number
    stayover_rooms: number
    persons_per_room: number
  }>
  source_label: string
  note: string
}

export interface GuestMixResult {
  distribution: Array<{ pax: number; records: number; room_nights: number; share: number }>
  total_records: number
  persons_per_room: number
  family: {
    records: number
    share: number
    children: number
    room_nights: number
    avg_los: number
    overall_avg_los: number
    by_category: Array<{
      room_category: string
      family_records: number
      total_records: number
      family_share: number
      index: number
    }>
  }
  basis: OperaBasis
  basis_label: string
  source_label: string
  note: string
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
  /** 平均住宿天數 = room_nights ÷ records（以房數計時 records 即房數） */
  avg_los: number
  one_night_records: number
  one_night_share: number
  /** 僅 dimension=group：原值是否帶 OTA 訂房參考號前綴 */
  had_ref?: number
  /** 僅 dimension=group：是否判定為個人訂房 */
  is_person?: number
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
  min_nights: number
  source_label: string
  /** 以下僅 dimension=group 會回傳 */
  exclude_person?: boolean
  person_records?: number
  group_note?: string
}

export interface LosBucket {
  label: string
  lower: number
  upper: number | null
  records: number
  room_nights: number
  share: number
  is_long_stay: boolean
}

export interface LosBucketResult {
  threshold: number
  buckets: LosBucket[]
  total_records: number
  total_room_nights: number
  avg_los: number
  basis: OperaBasis
  basis_label: string
  source_label: string
}

export interface OpportunityRow {
  business_date: string
  month: string
  revenue: number
  sold_rooms: number
  available_rooms: number
  occupancy: number
  adr: number
  baseline_adr: number
  adr_gap: number
  est_uplift: number
}

export interface OpportunityResult {
  threshold: number
  baseline_adr: number
  baseline_occupancy: number
  period_revenue: number
  items: OpportunityRow[]
  total_days: number
  total_uplift: number
  uplift_share: number
  monthly_series: Array<{ month: string; days: number; uplift: number }>
  source_label: string
  disclaimer: string
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

// ══════════════════════════════════════════════════════════════════════════════
// 歷史同期查詢 / 房價預測 / 事件月曆（2026-08-05 新增）
// 評估文件：docs/EVAL_opera_rate_forecasting.md
// ══════════════════════════════════════════════════════════════════════════════

/** 單日指標（歷史同期查詢用；期間平均時 business_date 為空字串） */
export interface LookupDayMetrics {
  business_date: string
  days?: number
  revenue: number
  total_revenue?: number
  sold_rooms: number
  available_rooms: number
  ooo_rooms: number
  no_persons: number
  arrival_rooms: number
  departure_rooms: number
  adr: number
  occupancy: number
  revpar: number
  persons_per_room: number
}

export interface LookupDiff {
  adr_diff: number | null
  adr_pct: number | null
  occupancy_ppt: number | null
  revenue_pct: number | null
}

export interface LookupComparison {
  key: string
  label: string
  hint: string
  date: string
  metrics: LookupDayMetrics | null
  diff: LookupDiff
}

export interface LookupStayMix {
  stays: number
  room_nights: number
  adults: number
  /** ⚠️ 後端刻意不叫 children：antd Table 會把 record.children 當成子列陣列 */
  child_count: number
  persons: number
  avg_los: number
  channels: Array<{ name: string; stays: number; room_nights: number; share: number }>
  room_categories: Array<{ name: string; stays: number; room_nights: number; share: number }>
  has_data: boolean
  basis_note: string
}

export interface DateLookupResult {
  business_date: string
  weekday: number
  weekday_label: string
  has_data: boolean
  target: LookupDayMetrics | null
  forecast: LookupDayMetrics | null
  comparisons: LookupComparison[]
  recent_same_weekday: LookupDayMetrics[]
  month_context: {
    month: string
    start: string
    end: string
    is_partial: boolean
    current: RevenueAggregate
    compare: RevenueAggregate
    compare_label: string
    has_compare_data: boolean
    yoy: { adr: number | null; revenue: number | null; occupancy_ppt: number | null }
  }
  weekday_context: {
    label: string
    in_month: WeekdayRow | null
    baseline: { adr: number; occupancy: number; revpar: number }
    thin_data: boolean
  }
  stay_mix: LookupStayMix
  flags: Array<{ label: string; source: string }>
  events: OperaEventItem[]
  data_range: { start: string; end: string }
  source_label: string
}

export interface PeriodLookupResult {
  period: PeriodInfo
  current: RevenueAggregate
  compare: RevenueAggregate
  yoy: RevenueKpi['yoy']
  has_compare_data: boolean
  daily: RevenueDailyRow[]
  months: Array<{
    month: string
    days: number
    revenue: number
    sold_rooms: number
    adr: number
    occupancy: number
    revpar: number
  }>
  weekday: WeekdayRow[]
  weekday_thin: boolean
  best_days: RevenueDailyRow[]
  worst_days: RevenueDailyRow[]
  stay_mix: LookupStayMix
  events: OperaEventItem[]
  source_label: string
}

// ── 事件月曆 ─────────────────────────────────────────────────────────────────

export type OperaEventSource = 'manual' | 'learned'

export interface OperaEventItem {
  id: number
  property_code: string
  name: string
  category: string
  start_date: string
  end_date: string
  days: number
  expected_adr_index: number
  expected_occ_index: number
  learned_adr_index: number | null
  learned_occ_index: number | null
  sample_count: number
  is_learnable: boolean
  learned_at: string
  source: OperaEventSource
  source_label: string
  effective_adr_index: number
  effective_occ_index: number
  is_active: boolean
  note: string
  updated_at: string
  updated_by_name: string
  detail: Record<string, string>
}

export interface EventListResult {
  items: OperaEventItem[]
  total: number
  categories: string[]
  min_samples: number
  hint: string
}

export interface EventLearnResult {
  ok: boolean
  items: Array<{
    name: string
    category: string
    occurrences: number
    covered_days: number
    learned_adr_index: number | null
    learned_occ_index: number | null
    is_reliable: boolean
    note: string
  }>
  min_samples: number
  reliable_count: number
  total: number
}

export interface EventPayload {
  property_code?: string
  name: string
  category: string
  start_date: string
  end_date: string
  expected_adr_index: number
  expected_occ_index: number
  source?: OperaEventSource
  is_active?: boolean
  note?: string
}

// ── 模型係數 ─────────────────────────────────────────────────────────────────

export type CoefKind = 'baseline' | 'dow' | 'month' | 'growth' | 'holiday' | 'interval' | 'anchor'

export interface ForecastCoefficient {
  id: number
  property_code: string
  kind: CoefKind
  kind_label: string
  coef_key: string
  key_label: string
  metric: 'adr' | 'occupancy'
  metric_label: string
  value: number
  fitted_value: number
  sample_days: number
  is_reliable: boolean
  is_editable: boolean
  is_manual: boolean
  fit_start: string
  fit_end: string
  fitted_at: string
  updated_at: string
  updated_by_name: string
}

export interface CoefficientListResult {
  items: ForecastCoefficient[]
  editable_kinds: CoefKind[]
  has_fitted: boolean
  source_label: string
}

export interface FitResult {
  ok: boolean
  written: number
  fit_start: string
  fit_end: string
  fit_days: number
  anchor_date: string
  baseline_adr: number
  baseline_occ: number
  growth_adr: number
  growth_occ: number
  available_rooms: number
  adr_interval: [number, number]
  occ_interval: [number, number]
  warnings: string[]
  excluded: Array<{
    business_date: string
    revenue: number
    sold_rooms: number
    available_rooms: number
    reasons: string[]
  }>
  excluded_count: number
  note: string
}

// ── 預測 ─────────────────────────────────────────────────────────────────────

export interface ForecastBreakdown {
  baseline_adr: number
  baseline_occ: number
  dow_adr: number
  dow_occ: number
  month_adr: number
  month_occ: number
  growth_adr: number
  growth_occ: number
  event_adr: number
  event_occ: number
  years_from_anchor: number
  anchor_date: string
  available_rooms: number
  formula_adr: string
}

export interface ForecastDayRow {
  business_date: string
  weekday: number
  weekday_label: string
  predicted_adr: number
  predicted_occupancy: number
  predicted_sold_rooms: number
  predicted_revenue: number
  adr_lower: number
  adr_upper: number
  occ_lower: number
  occ_upper: number
  events: Array<{
    id: number | null
    name: string
    category: string
    adr_index: number
    occ_index: number
    source_label: string
  }>
  breakdown: ForecastBreakdown
  naive: {
    business_date: string
    reference_date: string
    predicted_adr: number
    predicted_occupancy: number
    predicted_sold_rooms: number
    predicted_revenue: number
  } | null
  actual: { adr: number; occupancy: number; revenue: number; sold_rooms: number } | null
  is_history: boolean
}

export interface ForecastResult {
  ok: boolean
  reason?: string
  start: string
  end: string
  items: ForecastDayRow[]
  summary: {
    days: number
    predicted_revenue: number
    predicted_sold_rooms: number
    available_rooms: number
    predicted_adr: number
    predicted_occupancy: number
    predicted_revpar: number
    adr_lower: number
    adr_upper: number
  }
  naive_summary: {
    days: number
    predicted_adr: number
    predicted_revenue: number
    predicted_sold_rooms: number
  } | null
  coefficients: {
    anchor_date: string
    baseline_adr: number
    baseline_occ: number
    growth_adr: number
    growth_occ: number
    available_rooms: number
    fit_start: string
    fit_end: string
    fit_days: number
    adr_interval: [number, number]
  }
  events: OperaEventItem[]
  history_days: number
  warnings: string[]
  scenario_events?: ScenarioEvent[]
  saved_run_id?: number
  source_label: string
}

export interface ScenarioEvent {
  name: string
  category?: string
  start_date: string
  end_date: string
  adr_index: number
  occ_index: number
}

// ── 回測 ─────────────────────────────────────────────────────────────────────

export interface ErrorMetrics {
  n: number
  mape: number | null
  mae: number | null
  rmse: number | null
  bias: number | null
}

export interface BacktestResult {
  ok: boolean
  reason?: string
  train: { start: string; end: string; days: number }
  test: { start: string; end: string; days: number }
  models: Array<{
    model: 'decomp' | 'naive'
    label: string
    adr: ErrorMetrics
    occupancy: ErrorMetrics
    revenue: ErrorMetrics
  }>
  series: Array<{
    business_date: string
    actual_adr: number
    decomp_adr: number
    naive_adr: number | null
    actual_occupancy: number
    decomp_occupancy: number
    adr_lower: number
    adr_upper: number
    in_interval: boolean
  }>
  monthly_series: Array<{
    month: string
    days: number
    decomp_mape: number | null
    naive_mape: number | null
  }>
  interval_coverage: number
  interval_target: number
  beats_naive: boolean
  improvement: number | null
  verdict: string
  warnings: string[]
  source_label: string
}

// ── 預測快照 ─────────────────────────────────────────────────────────────────

export interface ForecastRun {
  id: number
  property_code: string
  run_at: string
  horizon_start: string
  horizon_end: string
  model: string
  model_label: string
  model_version: string
  days: number
  predicted_adr: number
  predicted_occ: number
  predicted_revenue: number
  created_by_name: string
  note: string
}

export interface RunCompareResult {
  filled: number
  compared: number
  adr: ErrorMetrics
  occupancy: ErrorMetrics
  revenue: ErrorMetrics
  note: string
}
