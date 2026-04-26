/**
 * IHG 客房保養 TypeScript 型別定義
 */

// ── 矩陣表欄格 ────────────────────────────────────────────────────────────────
export type CellStatus = 'completed' | 'pending' | 'scheduled' | 'abnormal'

export interface MatrixCell {
  ragic_id: string
  status: CellStatus
  date: string           // 保養日期
  assignee: string       // 保養人員
  completion_date: string
  maint_type: string
  notes: string
  normal_count: number        // raw_json 中值="正常" 的欄位數
  done_count: number          // raw_json 中值="當時維護完成" 的欄位數
  maint_count: number         // raw_json 中值="等待維護(待料中)" 的欄位數
  unchecked_count: number     // raw_json 中值="" 的欄位數（未檢查）
  work_minutes: number | null // 工時計算（分鐘）
}

// 某個房號的矩陣列
export interface MatrixRoom {
  room_no: string
  floor: string
  cells: Partial<Record<string, MatrixCell>>  // key = "1"~"12"（月份）
}

// 矩陣 API 回傳
export interface MatrixResponse {
  year: string
  months: number[]                         // [1, 2, ..., 12]
  floors: string[]                         // 所有已出現的樓層，如 ["5F","6F","7F"]
  rooms: MatrixRoom[]
  month_hours: Partial<Record<number, number>>  // {4: 10.33} 分鐘已轉小時
}

// ── KPI 統計 ──────────────────────────────────────────────────────────────────
export interface IHGStats {
  year: string
  total_scheduled: number
  completed: number   // check 欄位全正常/完成
  abnormal: number    // 有「等待維護(待料中)」欄位
  pending: number     // 無 check 資料（尚未填寫）
  completion_rate: number
  synced_at: string
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
  room_no: string
  floor: string
  maint_year: string
  maint_month: string
  maint_date: string
  status: CellStatus   // may be 'abnormal' when maint_count > 0
  is_completed: boolean
  assignee_name: string
  checker_name: string
  completion_date: string
  maint_type: string
  notes: string
  ragic_created_at: string
  ragic_updated_at: string
  synced_at: string | null
  raw_fields: Record<string, unknown>
  details: IHGDetail[]
}

// ── 清單 API 回傳 ─────────────────────────────────────────────────────────────
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
  synced_at: string | null
}

export interface IHGListResponse {
  total: number
  page: number
  per_page: number
  data: IHGListItem[]
}
