/**
 * 班表模組 TypeScript 型別定義
 * 對應後端 app/models/schedule.py 與 app/routers/schedule.py
 */

// ── 部門 ────────────────────────────────────────────────────
export interface Department {
  id: string
  name: string
  remark: string
  sort_order: number
  is_active: boolean
}

export interface DepartmentInput {
  name: string
  remark?: string
  sort_order?: number
  is_active?: boolean
}

// ── 班別 ────────────────────────────────────────────────────
export interface ShiftType {
  id: string
  code: string
  name: string
  start_time: string    // HH:MM
  end_time: string      // HH:MM
  work_minutes: number
  is_overnight: boolean
  color: string         // hex
  is_active: boolean
}

export interface ShiftTypeInput {
  code: string
  name: string
  start_time?: string
  end_time?: string
  work_minutes?: number
  is_overnight?: boolean
  color?: string
  is_active?: boolean
}

// ── 人員 ────────────────────────────────────────────────────
export interface StaffMember {
  id: string
  name: string
  source_name: string
  staff_code: string
  department_id: string | null
  department_name: string
  employment_type: string   // 正職 / PT / 支援人員
  remark: string
  is_active: boolean
}

export interface StaffMemberInput {
  name: string
  source_name?: string
  staff_code?: string
  department_id?: string | null
  employment_type?: string
  remark?: string
  is_active?: boolean
}

// ── 班表主檔 ─────────────────────────────────────────────────
export interface Schedule {
  id: string
  schedule_year: number
  schedule_month: number
  title: string
  source_file_name: string
  status: 'draft' | 'imported' | 'confirmed'
  created_at: string
}

// ── 表格式班表（橫向日期 × 縱向人員）─────────────────────────
export interface ScheduleTableHeader {
  day: number
  weekday: string   // 一二三四五六日
}

export interface ScheduleTableCell {
  detail_id: string
  shift_code: string
  color: string
  work_minutes: number
}

export interface ScheduleTableRow {
  staff_id: string | null
  staff_name: string
  employment_type: string
  department_name: string
  cells: Record<number, ScheduleTableCell>   // day → cell
  work_days: number
  work_minutes: number
  raw_summary: Record<string, number | string>
}

export interface ScheduleTableData {
  schedule: Schedule | null
  days_in_month: number
  headers: ScheduleTableHeader[]
  rows: ScheduleTableRow[]
}

// ── 明細列表（逐筆） ─────────────────────────────────────────
export interface ScheduleDetailRow {
  id: string
  work_date: string     // YYYY-MM-DD
  weekday: string
  staff_id: string | null
  staff_name: string
  department_name: string
  employment_type: string
  shift_code: string
  shift_name: string
  shift_color: string
  start_time: string
  end_time: string
  work_minutes: number
  remark: string
  schedule_id: string
}

// ── Excel 匯入結果 ───────────────────────────────────────────
export interface ImportResult {
  schedule_id: string | null
  schedule_year?: number
  schedule_month?: number
  year_month_detected: boolean
  already_exists?: boolean
  total_rows?: number
  total_details?: number
  success_count?: number
  warning_count?: number
  error_count?: number
  unknown_shift_codes?: string[]
  new_staff_names?: string[]
  message: string
  import_batch_id: string
  warnings?: string[]
}

// ── 匯入紀錄 ─────────────────────────────────────────────────
export interface ImportLog {
  id: string
  import_batch_id: string
  file_name: string
  sheet_name: string
  schedule_year: number
  schedule_month: number
  total_details: number
  success_count: number
  warning_count: number
  error_count: number
  unknown_shift_codes: string[] | null
  new_staff_names: string[] | null
  message: string
  created_at: string
}

// ── 統計 ─────────────────────────────────────────────────────
export interface MonthlyStats {
  schedule_id: string
  year: number
  month: number
  total_staff: number
  total_details: number
  person_stats: Record<string, {
    work_days: number
    work_minutes: number
    shifts: Record<string, number>
  }>
  shift_stats: Record<string, number>
  daily_stats: Record<string, Record<string, number>>
}

// ── 篩選參數 ─────────────────────────────────────────────────
export interface ScheduleFilters {
  year?: number
  month?: number
  staff_id?: string
  department_id?: string
  shift_code?: string
}
