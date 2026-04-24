/**
 * 客房保養明細 — TypeScript 型別定義
 * 對應後端 /api/v1/room-maintenance-detail/*
 */

// ── 明細列表 ─────────────────────────────────────────────────────────────────

export interface RoomMaintenanceDetailRecord {
  [key: string]: string | null
  ragic_id:      string
  maintain_date: string
  staff_name:    string
  room_no:       string
  work_hours:    string
  created_date:  string
  chk_door:      string
  chk_fire:      string
  chk_equipment: string
  chk_furniture: string
  chk_light:     string
  chk_window:    string
  chk_sink:      string
  chk_toilet:    string
  chk_bath:      string
  chk_surface:   string
  chk_ac:        string
  chk_balcony:   string
  synced_at:     string | null
}

export interface RoomMaintenanceDetailListResponse {
  data: RoomMaintenanceDetailRecord[]
  meta: { total: number; page: number; per_page: number }
}

// ── 總表 ─────────────────────────────────────────────────────────────────────

/** 總表中每一個房間的聚合列 */
export interface RoomSummaryRow {
  floor:          string          // "9F"
  floor_no:       number          // 9
  room_no:        string          // "923"
  serviced:       boolean         // 是否在選定日期區間有保養記錄
  maintain_date:  string | null   // 最近一筆保養日期
  staff_name:     string | null
  work_hours:     string | null
  created_date:   string | null
  checks:         Record<string, string>  // { "房門": "V", "消防": "X", ... }
  abnormal_count: number
  total_checks:   number
  record_count:   number          // 區間內保養記錄筆數
}

/** 總表統計數字 */
export interface RoomSummaryStats {
  total_records:    number   // 保養記錄總數
  total_abnormal:   number   // 異常項次總數
  fully_ok_count:   number   // 全項目正常房間數
  work_hours_total: number   // 工時數（分鐘加總）
  unserviced_count: number   // 未保養房間數
}

/** 總表 API 回應 */
export interface RoomSummaryResponse {
  data:             RoomSummaryRow[]
  stats:            RoomSummaryStats
  unserviced_rooms: string[]
}

// ── 篩選 ─────────────────────────────────────────────────────────────────────

export interface RoomMaintenanceDetailFilters {
  room_no?:       string
  staff_name?:    string
  maintain_date?: string
  date_from?:     string
  date_to?:       string
  page?:          number
  per_page?:      number
}

// ── 同步 ─────────────────────────────────────────────────────────────────────

export interface RoomMaintenanceDetailSyncResponse {
  success:  boolean
  fetched:  number
  upserted: number
  errors:   string[]
}

// ── 房間歷史記錄 ──────────────────────────────────────────────────────────────

/** 單月保養摘要 */
export interface MonthlyMaintenanceSummary {
  year:           number
  month:          number
  month_label:    string          // "2026/04"
  is_current:     boolean         // 是否為當月或未來月
  serviced:       boolean
  record_count:   number
  work_hours_sum: number          // 該月工時加總（分鐘）
  latest_date:    string | null
  latest_staff:   string | null
  checks:         Record<string, string>  // 最近一筆的 checks
}

/** 房間歷史統計 */
export interface RoomHistoryStats {
  total_records:      number
  last_serviced:      string | null
  consecutive_missed: number   // 連續未保養月數
  serviced_months:    number   // 近 N 月中已保養月數
  total_months:       number   // 查詢月數
}

/** 房間歷史 API 回應 */
export interface RoomHistoryResponse {
  room:             { floor: string; room_no: string }
  monthly_summary:  MonthlyMaintenanceSummary[]
  records:          RoomMaintenanceDetailRecord[]
  stats:            RoomHistoryStats
}

// ── 人員工時月報表 ────────────────────────────────────────────────────────────

/** 每位人員的工時列 */
export interface StaffHoursRow {
  staff_name:    string
  /** 月份 → 小時數，e.g. { "2025/05": 1.5, "2026/04": 3.0 } */
  monthly_hours: Record<string, number>
  total_hours:   number    // 近 N 月合計（小時）
  total_minutes: number    // 近 N 月合計（分鐘，供顯示用）
}

/** 人員工時月報表 API 回應 */
export interface StaffHoursResponse {
  months:            string[]              // ["2025/05", "2025/06", ..., "2026/04"]
  rows:              StaffHoursRow[]
  month_totals:      Record<string, number> // 每月全員合計（小時）
  grand_total_hours: number                // 全期合計（小時）
}

// ── 常數：12 個檢查項目 ───────────────────────────────────────────────────────

export const CHECK_FIELD_LABELS: Record<string, string> = {
  chk_door:      '房門',
  chk_fire:      '消防',
  chk_equipment: '設備',
  chk_furniture: '傢俱',
  chk_light:     '客房燈/電源',
  chk_window:    '客房窗',
  chk_sink:      '面盆/台面',
  chk_toilet:    '浴厠',
  chk_bath:      '浴間',
  chk_surface:   '天地壁',
  chk_ac:        '客房空調',
  chk_balcony:   '陽台',
}

export const CHECK_FIELD_KEYS = Object.keys(CHECK_FIELD_LABELS) as Array<
  keyof typeof CHECK_FIELD_LABELS
>

// ── 保養統計分析（maintenance-stats）────────────────────────────────────────

/** 月別完成率趨勢（Phase 1） */
export interface MonthlyTrend {
  month_label:         string
  completion_rate:     number   // 完成率 %（有保養記錄的房間 / 總房間數）
  serviced_count:      number
  total_rooms:         number
  abnormal_item_count: number   // 異常項次總數（X 的欄位數累計）
  rooms_with_abnormal: number   // 有任一 X 的房間數
  abnormal_rate:       number   // 異常率 %（有X房間 / 已保養房間）
  work_hours_total:    number   // 工時分鐘加總
}

/** 單一檢查項目統計（Phase 2） */
export interface CheckItemStat {
  field_name:     string
  label:          string
  abnormal_count: number
  normal_count:   number
  total_count:    number
  abnormal_rate:  number
}

/** 樓層統計（Phase 3A） */
export interface FloorStat {
  floor:               string
  floor_no:            number
  total_rooms:         number
  serviced_this_month: number
  completion_rate:     number   // 當月完成率 %
  abnormal_count:      number   // 全期累計異常項次
  total_records:       number
}

/** 連續未保養高風險房間 */
export interface ConsecutiveMissedRoom {
  room_no:       string
  floor:         string
  missed_months: number
  last_serviced: string | null
}

/** 同一項目重複異常房間 */
export interface RepeatedAbnormalRoom {
  room_no:            string
  floor:              string
  field_name:         string
  field_label:        string
  consecutive_months: number
}

/** 全正常房間 */
export interface FullyOkRoom {
  room_no:         string
  floor:           string
  ok_record_count: number
  last_serviced:   string | null
}

/** 月份對比快照（Phase 3B） */
export interface MonthComparison {
  month_label:      string
  serviced_count:   number
  completion_rate:  number
  abnormal_count:   number
  work_hours_total: number
  record_count:     number
}

/** 保養統計 API 回應 */
export interface MaintenanceStatsResponse {
  months:           string[]
  monthly_trend:    MonthlyTrend[]
  check_item_stats: CheckItemStat[]
  floor_stats:      FloorStat[]
  risk_rooms: {
    consecutive_missed: ConsecutiveMissedRoom[]
    repeated_abnormal:  RepeatedAbnormalRoom[]
    fully_ok:           FullyOkRoom[]
  }
  comparison: {
    current_month:        MonthComparison
    prev_month:           MonthComparison
    same_month_last_year: MonthComparison
  }
  kpi: {
    current_month_completion_rate: number
    current_month_abnormal_rate:   number
    consecutive_missed_rooms:      number
    fully_ok_rooms:                number
    avg_completion_rate_12m:       number
    trend_direction:               'up' | 'down' | 'stable'
  }
}
