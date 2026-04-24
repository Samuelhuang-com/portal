// ── 週期保養表 TypeScript 型別定義 ────────────────────────────────────────────

export interface PMBatch {
  ragic_id:         string
  journal_no:       string
  period_month:     string
  ragic_created_at: string
  ragic_updated_at: string
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
  planned_minutes:      number
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
