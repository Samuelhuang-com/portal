/**
 * IHG 客房保養 TypeScript 型別定義
 */

// ── 矩陣表欄格 ────────────────────────────────────────────────────────────────
export type CellStatus = 'completed' | 'pending' | 'scheduled' | 'abnormal'

export interface MatrixCell {
  ragic_id: string
  status: CellStatus
  date: string
  assignee: string
  completion_date: string
  maint_type: string
  notes: string
  normal_count: number
  done_count: number
  maint_count: number
  unchecked_count: number
  work_minutes: number | null
}

export interface MatrixRoom {
  room_no: string
  floor: string
  cells: Partial<Record<string, MatrixCell>>
}

export interface MatrixResponse {
  year: string
  months: number[]
  floors: string[]
  rooms: MatrixRoom[]
  month_hours: Partial<Record<number, number>>
}

// ── KPI 統計 ──────────────────────────────────────────────────────────────────
export interface IHGStats {
  year:             string
  month?:           string | null
  total_scheduled:  number
  completed:        number
  abnormal:         number
  pending:          number
  completion_rate:  number
  work_hours:       number
  synced_at:        string
}

// ── 單筆記錄明細 ──────────────────────────────────────────────────────────────
export interface IHGDetail {
  ragic_id: string
  seq_no: number
  task_name: string
  result: string
  is_ok: boolean
  notes: string
}

export interface IHGRecord {
  ragic_id: string
  ragic_url: string
  room_no: string
  floor: string
  maint_year: string
  maint_month: string
  maint_date: string
  status: CellStatus
  is_completed: boolean
  assignee_name: string
  checker_name: string
  completion_date: string
  maint_type: string
  notes: string
  start_time: string
  end_time: string
  work_minutes: number | null
  ragic_created_at: string
  ragic_updated_at: string
  synced_at: string | null
  raw_fields: Record<string, unknown>
  detail: Record<string, string>
  details: IHGDetail[]
}

// ── 區段矩陣 API ──────────────────────────────────────────────────────────────
export type SectionValue = 'V' | '\u25b2' | 'X'

export interface SectionRoom {
  room_no: string
  floor: string
  maint_date: string
  ragic_id: string
  sections: Record<string, SectionValue>
  has_data: boolean
}

export interface CategoryStat {
  v_count: number
  triangle_count: number
  x_count: number
  reported: number
  rate: number   // V 數 / total_rooms * 100
}

export interface SectionMatrixResponse {
  year: string
  month: string

  categories: string[]
  rooms: SectionRoom[]
  category_stats: Record<string, CategoryStat>
  total_rooms: number
}

// ── 清單 API 回傳 ─────────────────────────────────────────────────
export interface IHGListItem {
  ragic_id: string
  room_no: string
  floor: string
  maint_year: string
  maint_month: string
  maint_date: string
  status: CellStatus
  is_completed: boolean
  assignee_name: string
  checker_name: string
  completion_date: string
  maint_type: string
  notes: string
  start_time: string
  end_time: string
  work_minutes: number | null
  synced_at: string | null
}

export interface IHGListResponse {
  total: number
  page: number
  per_page: number
  data: IHGListItem[]
}
