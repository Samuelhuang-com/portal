/**
 * 保全巡檢 TypeScript 型別定義
 */

// ── Sheet 設定 ────────────────────────────────────────────────────────────────
export interface SheetConfig {
  key:  string
  id:   number
  name: string
  path: string
}

// ── 巡檢場次 ──────────────────────────────────────────────────────────────────
export interface PatrolBatch {
  ragic_id:        string
  sheet_key:       string
  sheet_id:        number
  sheet_name:      string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  work_hours:      string
  item_count:      number
  synced_at?:      string | null
}

// ── 巡檢項目 ──────────────────────────────────────────────────────────────────
export interface PatrolItem {
  ragic_id:       string
  batch_ragic_id: string
  sheet_key:      string
  seq_no:         number
  item_name:      string
  result_raw:     string
  result_status:  'normal' | 'abnormal' | 'pending' | 'unchecked' | 'note'
  abnormal_flag:  boolean
  is_note?:       boolean  // true = 文字備註欄位（異常說明），不計入統計
  synced_at?:     string | null
}

// ── KPI ───────────────────────────────────────────────────────────────────────
export interface PatrolBatchKPI {
  total:           number
  normal:          number
  abnormal:        number
  pending:         number
  unchecked:       number
  completion_rate: number
  normal_rate:     number
}

export interface StatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

// ── 批次詳情 ──────────────────────────────────────────────────────────────────
export interface PatrolBatchDetail {
  batch: PatrolBatch
  kpi:   PatrolBatchKPI
  items: PatrolItem[]
}

// ── 場次清單項目（含 KPI）────────────────────────────────────────────────────
export interface PatrolBatchListItem {
  batch: PatrolBatch
  kpi:   PatrolBatchKPI
}

// ── 全站統計 ──────────────────────────────────────────────────────────────────
export interface PatrolStats {
  sheet_key:           string
  sheet_name:          string
  latest_batch?:       PatrolBatch | null
  latest_kpi?:         PatrolBatchKPI | null
  recent_abnormal:     PatrolItem[]
  recent_pending:      PatrolItem[]
  status_distribution: StatusDistItem[]
  total_batches_7d:    number
  abnormal_trend:      AbnormalTrendPoint[]
}

export interface AbnormalTrendPoint {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

// ── Dashboard 型別 ────────────────────────────────────────────────────────────
export interface SheetStats {
  sheet_key:       string
  sheet_name:      string
  total_batches:   number
  total_items:     number
  checked_items:   number
  unchecked_items: number
  abnormal_items:  number
  pending_items:   number
  completion_rate: number
  normal_rate:     number
  has_data:        boolean
}

export interface SecurityDashboardSummary {
  target_date:           string
  sheets:                SheetStats[]
  total_batches_all:     number
  total_items_all:       number
  checked_items_all:     number
  abnormal_items_all:    number
  completion_rate_all:   number
  generated_at:          string
}

export interface SecurityIssueItem {
  id:           string
  issue_date:   string
  sheet_key:    string
  sheet_name:   string
  item_name:    string
  status:       string
  status_label: string
  inspector:    string
  note:         string
  batch_id:     string
}

export interface SecurityIssueListResponse {
  items: SecurityIssueItem[]
  total: number
}

export interface SecurityTrendPoint {
  date:           string
  abnormal_count: number
  total_batches:  number
  has_data:       boolean
  by_sheet:       Record<string, { batch_count: number; abnormal: number }>
}

export interface SecurityDashboardTrend {
  trend: SecurityTrendPoint[]
  days:  number
}
