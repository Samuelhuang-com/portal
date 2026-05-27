// ── 週期保養表 TypeScript 型別定義 ────────────────────────────────────────────

export interface PMBatch {
  ragic_id:         string
  journal_no:       string
  period_month:     string
  ragic_created_at: string
  ragic_updated_at: string
  ragic_url?:       string
  synced_at?:       string
}

export interface PMItem {
  ragic_id:          string
  batch_ragic_id:    string
  seq_no:            number
  category:          string
  frequency:         string
  exec_months_raw:   string
  exec_months_json:  string   // JSON string e.g. "[2,5,8,11]"
  task_name:         string
  location:          string
  estimated_minutes: number
  scheduled_date:    string
  scheduler_name:    string
  executor_name:     string
  start_time:        string
  end_time:          string
  is_completed:      boolean   // 保養時間啟+迄均有值則自動 true；Portal 亦可手動設定
  result_note:       string
  abnormal_flag:     boolean
  abnormal_note:     string
  portal_edited_at?: string
  synced_at?:        string
  status:            PMItemStatus
}

export type PMItemStatus =
  | 'completed'
  | 'in_progress'
  | 'scheduled'
  | 'unscheduled'
  | 'overdue'
  | 'non_current_month'

export interface PMBatchKPI {
  total:                number
  current_month_total:  number
  completed:            number
  in_progress:          number
  scheduled:            number
  unscheduled:          number
  overdue:              number
  abnormal:             number
  completion_rate:      number
  planned_minutes:      number   // 預估工時合計（estimated_minutes 加總，分鐘）
  actual_minutes:       number   // 實際工時合計（end_time - start_time 加總，分鐘）
}

export interface CategoryStat {
  category:  string
  total:     number
  completed: number
  rate:      number
}

export interface StatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

export interface PMBatchListItem {
  batch: PMBatch
  kpi:   PMBatchKPI
}

export interface PMBatchDetail {
  batch:      PMBatch
  kpi:        PMBatchKPI
  items:      PMItem[]
  categories: CategoryStat[]
}

export interface PMStats {
  current_batch?:       PMBatch
  current_kpi?:         PMBatchKPI
  overdue_items:        PMItem[]
  upcoming_items:       PMItem[]
  category_stats:       CategoryStat[]
  status_distribution:  StatusDistItem[]
}

// PMItemUpdate 已停用（Portal 不提供編輯，資料全部來自 Ragic 同步）
export interface PMItemUpdate {
  [key: string]: never
}

// ── 週期統計（月 / 季 / 年）─────────────────────────────────────────────────

export interface PMIncompleteItem {
  task_name:            string
  category:             string
  scheduled_date_full:  string   // "YYYY/MM/DD"
  result_note:          string
  frequency:            string
}

export interface PMSubPeriodBreakdown {
  label:     string        // "1月" / "Q1" 等
  total:     number
  completed: number
  rate:      number | null  // null = N/A（分母為 0）
}

export interface PMPeriodStats {
  period_type:   string    // "month" | "quarter" | "year"
  period_label:  string    // "2026年4月" / "2026 Q2" / "2026年"
  period_start:  string    // "2026-04-01"
  period_end:    string    // "2026-04-30"
  prev_period_end: string  // "2026-03-31"

  // 上期累計
  prev_carry_over:         number
  prev_resolved_in_period: number
  carry_over_rate:         number | null  // null = N/A

  // 本期
  period_total:     number
  period_completed: number
  period_rate:      number | null  // null = N/A

  // 子期間分布（季→月、年→Q1-Q4、月→空陣列）
  sub_period_breakdown: PMSubPeriodBreakdown[]

  // 未完成事項說明（僅含 result_note 非空的項目）
  incomplete_items: PMIncompleteItem[]
}

// ── 年度矩陣統計（12個月橫軸）────────────────────────────────────────────────

export interface PMYearMatrixMonth {
  month:                   number    // 1-12
  label:                   string    // "一月" ... "十二月"
  prev_carry_over:         number    // 上月累計未完成項目數
  prev_resolved_in_period: number    // 上月未完成於本月結案數
  carry_over_rate:         number | null  // 累計項目完成率（%）
  period_total:            number    // 本月週期保養項目數
  period_completed:        number    // 本月週期保養完成數
  period_rate:             number | null  // 本月週期保養完成率（%）
  incomplete_notes:        string    // 未完成備註（\n 分隔；空=無）
}

export interface PMYearMatrix {
  year:   number
  months: PMYearMatrixMonth[]
}

// ── 保養項目歷史（跨批次 task-history）────────────────────────────────────────

export interface PMItemHistorySummary {
  period_month:   string   // e.g. "2026/04"
  status:         string   // PMItemStatus | 'no_batch'
  has_record:     boolean
  executor_name:  string
  scheduled_date: string
  start_time:     string
  end_time:       string
  result_note:    string
  abnormal_flag:  boolean
  abnormal_note:  string
  is_current:     boolean
}

export interface PMTaskHistoryStats {
  total_months:     number
  completed_months: number
  abnormal_count:   number
}

export interface PMTaskHistory {
  task_name:        string
  category:         string
  frequency:        string
  exec_months_raw:  string
  monthly_summary:  PMItemHistorySummary[]
  stats:            PMTaskHistoryStats
}


// ════════════════════════════════════════════════════════════════════════════
// 排程管理（pm_schedule）TypeScript 型別
// ════════════════════════════════════════════════════════════════════════════

export type PMScheduleStatus =
  | 'completed'
  | 'in_progress'
  | 'overdue'
  | 'scheduled'
  | 'unscheduled'

export interface PMScheduleItem {
  id:               number
  year_month:       string
  item_ragic_id:    string
  category:         string
  task_name:        string
  location:         string
  frequency:        string
  estimated_minutes: number
  scheduled_date:   string
  executor_name:    string
  schedule_source:  'auto' | 'manual'
  start_time:       string
  end_time:         string
  is_completed:     boolean
  result_note:      string
  abnormal_flag:    boolean
  abnormal_note:    string
  portal_edited_at: string | null
  created_at:       string
  updated_at:       string
  status:           PMScheduleStatus
  overdue_days?:    number   // 逾期清單專用
}

export interface PMScheduleKPI {
  total:               number
  unscheduled:         number
  scheduled:           number
  in_progress:         number
  completed:           number
  overdue:             number
  abnormal:            number
  should_do_not_done:  number
  completion_rate:     number
}

export interface PMScheduleGenerateResult {
  year_month:             string
  generated:              number
  updated:                number
  skipped_completed:      number
  skipped_edited:         number
  skipped_non_month:      number
  skipped_no_frequency:   number
  errors:                 string[]
}

export interface PMScheduleListResponse {
  year_month:         string
  total:              number
  should_do_not_done: number
  items:              PMScheduleItem[]
}

export interface PMScheduleOverdueResponse {
  total:           number
  months_affected: string[]
  items:           PMScheduleItem[]
}

// ── 年度計劃矩陣 ──────────────────────────────────────────────────────────────

export type PMMatrixCellStatus =
  | 'completed'
  | 'overdue'
  | 'in_progress'
  | 'scheduled'
  | 'unscheduled'
  | 'non_month'
  | 'no_data'
  | 'no_frequency'

export interface PMScheduleMatrixCell {
  month:          number
  status:         PMMatrixCellStatus
  schedule_id:    number | null
  scheduled_date: string | null   // e.g. "05/15"
}

export interface PMScheduleMatrixRow {
  item_ragic_id: string
  category:      string
  task_name:     string
  location:      string
  frequency:     string
  cells:         PMScheduleMatrixCell[]
}

export interface PMScheduleAnnualMatrix {
  year:    number
  rows:    PMScheduleMatrixRow[]
  summary: { total_items: number; completed_count: number }
}
