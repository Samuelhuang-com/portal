/**
 * 商場管理統計 Dashboard  TypeScript 型別定義
 */

// ── 巡檢 ──────────────────────────────────────────────────────────────────────

export interface FloorInspectionStats {
  floor:           string   // "b1f" | "b2f" | "rf"
  floor_label:     string   // "B1F" | "B2F" | "RF"
  batches:         number
  total_items:     number
  normal_items:    number
  abnormal_items:  number
  pending_items:   number
  unchecked_items: number
  checked_items:   number
  completion_rate: number
  normal_rate:     number
}

export interface InspectionSummary {
  target_date:     string
  total_batches:   number
  total_items:     number
  checked_items:   number
  unchecked_items: number
  abnormal_items:  number
  completion_rate: number
  by_floor:        FloorInspectionStats[]
}

// ── 週期保養 ──────────────────────────────────────────────────────────────────

export interface PMSummary {
  period_month:     string
  total_items:      number
  completed_items:  number
  incomplete_items: number
  overdue_items:    number
  abnormal_items:   number
  completion_rate:  number
}

// ── Dashboard 整體摘要 ─────────────────────────────────────────────────────────

export interface DashboardSummary {
  inspection:   InspectionSummary
  pm:           PMSummary
  generated_at: string
}

// ── 異常 / 待追蹤清單 ─────────────────────────────────────────────────────────

export interface IssueItem {
  id:           string
  issue_date:   string
  issue_type:   'inspection' | 'pm'
  floor:        string
  item_name:    string
  status:       'abnormal' | 'pending' | 'unchecked' | 'overdue'
  status_label: string
  responsible:  string
  note:         string
  batch_id:     string
}

export interface IssueListResponse {
  items: IssueItem[]
  total: number
}

// ── 趨勢資料 ──────────────────────────────────────────────────────────────────

export interface TrendPoint {
  date:            string
  b1f_completion:  number
  b2f_completion:  number
  rf_completion:   number
  b1f_abnormal:    number
  b2f_abnormal:    number
  rf_abnormal:     number
  total_abnormal:  number
  has_data:        boolean
}

export interface DashboardTrend {
  trend: TrendPoint[]
  days:  number
}

// ── 篩選條件 ──────────────────────────────────────────────────────────────────

export interface DashboardFilters {
  startDate: string | null
  endDate:   string | null
  floor:     'all' | 'b1f' | 'b2f' | 'rf'
  issueType: 'all' | 'inspection' | 'pm'
  status:    'all' | 'abnormal' | 'pending' | 'unchecked' | 'overdue'
}
