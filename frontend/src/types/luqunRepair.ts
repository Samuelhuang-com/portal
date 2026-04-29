/**
 * 樂群工務報修 TypeScript 型別定義
 */

// ── 單筆報修案件 ──────────────────────────────────────────────────────────────
export interface RepairImage {
  url:      string
  filename: string
}

export interface RepairCase {
  ragic_id:         string
  case_no:          string
  title:            string
  reporter_name:    string
  repair_type:      string
  floor:            string
  floor_normalized: string
  occurred_at:      string
  responsible_unit: string
  work_hours:       number
  status:           string
  outsource_fee:    number
  maintenance_fee:  number
  total_fee:        number
  acceptor:         string
  accept_status:    string
  closer:           string
  deduction_item:         string
  deduction_fee:          number
  deduction_counter:      number        // 保持 0（欄位存名稱，非金額）
  deduction_counter_name: string        // 扣款專櫃名稱（如"牪肉舖"或"多櫃"）
  counter_stores:         string[]      // 解析後的專櫃列表
  mgmt_response:          string        // 管理單位回應
  finance_note:           string
  is_completed:     boolean
  completed_at:     string
  close_days:       number | null
  pending_days:     number | null
  year:             number | null
  month:            number | null
  is_room_case:     boolean
  room_no:          string
  room_category:    string
  images:           RepairImage[]
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export interface DashboardKpi {
  total:                    number
  completed:                number
  uncompleted:              number
  avg_close_days:           number | null
  total_fee:                number
  total_deduction_fee:      number
  total_deduction_counter:  number        // 保持 0
  total_counter_stores:     number        // 本月有扣款的專櫃家數
  total_counter_fee:        number        // 本月扣款專櫃費用合計
  counter_store_names:      string[]      // 本月專櫃名稱列表
  total_work_hours:         number
  room_cases:               number
  pending_verify:           number          // 待辦驗件數
  // 年度費用（費用 KPI 卡片用，不受月份篩選影響）
  annual_fee:                    number
  annual_outsource_fee:          number
  annual_maintenance_fee:        number
  annual_deduction_fee:          number
  annual_deduction_counter:      number
  // 年度扣款專櫃（全年統計，與費用 KPI 卡片對齊）
  annual_counter_stores:         number        // 全年有扣款的專櫃家數
  annual_counter_fee:            number        // 全年扣款專櫃費用合計
  annual_counter_store_names:    string[]      // 全年專櫃名稱列表
  // 當月費用（費用 KPI 卡片用，依年+月篩選）
  month_outsource_fee:     number
  month_maintenance_fee:   number
  month_deduction_fee:     number
  month_deduction_counter: number
  month_total_fee:         number
}

export interface Trend12MPoint {
  label:     string
  year:      number
  month:     number
  total:     number
  completed: number
}

export interface TypeDistItem {
  type:  string
  count: number
}

export interface FloorDistItem {
  floor: string
  count: number
}

export interface StatusDistItem {
  status: string
  count:  number
}

export interface DashboardData {
  kpi:               DashboardKpi
  trend_12m:         Trend12MPoint[]
  type_dist:         TypeDistItem[]
  floor_dist:        FloorDistItem[]
  status_dist:       StatusDistItem[]
  top_uncompleted:   RepairCase[]
  top_fee:           RepairCase[]
  top_hours:         RepairCase[]
  // KPI 明細（點擊 KPI 卡片時用）
  kpi_total_detail:            RepairCase[]
  kpi_completed_detail:        RepairCase[]
  kpi_uncompleted_detail:      RepairCase[]
  kpi_pending_verify_detail:   RepairCase[]
  kpi_close_days_detail:       RepairCase[]
  kpi_room_detail:             RepairCase[]
  kpi_hours_detail:            RepairCase[]
  kpi_counter_stores_detail:   RepairCase[]
  // 年度費用明細（點擊費用卡片時用）
  annual_fee_detail:       RepairCase[]
  annual_deduction_detail: RepairCase[]
  annual_counter_detail:   RepairCase[]
}

// ── 4.1 報修統計 ──────────────────────────────────────────────────────────────
export interface MonthRepairStat {
  month:                      number
  prev_uncompleted:           number
  closed_from_prev:           number
  prev_remaining:             number
  cum_completion_rate:        number | null
  this_month_total:           number
  this_month_completed:       number
  this_month_uncompleted:     number
  this_month_completion_rate: number | null
  // 明細（點擊展開）
  prev_uncompleted_detail:    RepairCase[]
  closed_from_prev_detail:    RepairCase[]
  prev_remaining_detail:          RepairCase[]
  this_month_uncompleted_detail:  RepairCase[]
  this_month_total_detail:    RepairCase[]
  this_month_completed_detail:RepairCase[]
}

export interface RepairStatsData {
  year:   number
  months: Record<number, MonthRepairStat>
}

// ── 4.2 結案時間統計 ──────────────────────────────────────────────────────────
export interface ClosingBlock {
  closed_count: number
  total_days:   number
  avg_days:     number | null
  cases:        RepairCase[]
}

export interface ClosingMonthlyItem {
  small: ClosingBlock
  large: ClosingBlock
}

export interface ClosingTimeData {
  year:                  number
  month:                 number | null
  small:                 ClosingBlock
  large:                 ClosingBlock
  monthly:               Record<number, ClosingMonthlyItem>
  classification_note:   string
}

// ── 4.3 報修類型統計 ──────────────────────────────────────────────────────────
export interface TypeStatRow {
  type:           string
  example:        string
  monthly:        Record<number, number>
  monthly_detail: Record<number, RepairCase[]>
  row_total:      number
  prev_month:     number
  this_month:     number
  cum_pct:        number
}

export interface TypeStatsData {
  year:        number
  focus_month: number | null
  rows:        TypeStatRow[]
  year_total:  number
  type_order:  string[]
}

// ── 4.4 客房報修表 ────────────────────────────────────────────────────────────
export interface RoomCategoryEntry {
  ragic_id: string
  title:    string
  status:   string
}

export interface RoomRepairRow {
  room_no:    string
  floor:      string
  categories: Record<string, RoomCategoryEntry[]>
}

export interface RoomRepairTableData {
  year:               number
  month:              number
  categories:         string[]
  rows:               RoomRepairRow[]
  unknown_room_cases: RepairCase[]
  floors_with_data:   string[]
  total_room_cases:   number
}

// ── 明細查詢 ──────────────────────────────────────────────────────────────────
export interface DetailQueryParams {
  year?:        number
  month?:       number
  repair_type?: string
  floor?:       string
  status?:      string
  keyword?:     string
  page?:        number
  page_size?:   number
  sort_by?:     string
  sort_desc?:   boolean
}

export interface DetailResult {
  total:     number
  page:      number
  page_size: number
  items:     RepairCase[]
}

// ── 過濾選項 ──────────────────────────────────────────────────────────────────
export interface FilterOptions {
  repair_types: string[]
  floors:       string[]
  statuses:     string[]
}

// ── 金額統計 ──────────────────────────────────────────────────────────────────
export type FeeKey = 'outsource_fee' | 'maintenance_fee' | 'deduction_fee' | 'deduction_counter'

export interface FeeMonthRow {
  outsource_fee:     number
  maintenance_fee:   number
  deduction_fee:     number
  deduction_counter: number
}

export interface FeeTotals {
  outsource_fee:     number
  maintenance_fee:   number
  deduction_fee:     number
  deduction_counter: number
}

export interface FeeStatsData {
  year:            number
  monthly_totals:  Record<number, FeeMonthRow>   // key = 1..12
  fee_totals:      FeeTotals                      // annual total per fee type
  month_totals:    Record<number, number>          // monthly sum of all fee types
  grand_total:     number
  monthly_detail:  Record<string, RepairCase[]>   // key = "{m}_{fk}"
  fee_labels:      Record<FeeKey, string>
}
