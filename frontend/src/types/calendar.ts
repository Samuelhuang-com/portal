/**
 * 行事曆模組 TypeScript 型別定義
 */

// ── 區域別 ────────────────────────────────────────────────────────────────────
export type CalendarZone = '飯店' | '商場' | '公區' | '其它'

export const ZONE_VALUES: CalendarZone[] = ['飯店', '商場', '公區', '其它']

export const ZONE_COLORS: Record<CalendarZone, string> = {
  飯店: '#1B3A5C',  // 品牌主色（深藍）
  商場: '#4BA8E8',  // 品牌輔色（天藍）
  公區: '#389e0d',  // 公共區域（深綠）
  其它: '#8c8c8c',  // 其他（灰）
}

export const ZONE_LABELS: Record<CalendarZone, string> = {
  飯店: '飯店',
  商場: '商場',
  公區: '公區',
  其它: '其它',
}

// ── 事件類型 ──────────────────────────────────────────────────────────────────
export type CalendarEventType =
  | 'hotel_pm'    // 飯店週期保養（執行記錄）
  | 'mall_pm'     // 商場週期保養（執行記錄）
  | 'full_pm'     // 全棟例行維護（執行記錄，Sheet /21）
  | 'pm_plan'     // 週期保養預排（主管排定 /7 /13 /20）
  | 'approval'    // 簽核管理
  | 'memo'        // 公告牆
  | 'custom'      // 自訂事件

// 狀態
export type CalendarEventStatus =
  | 'pending'     // 待執行 / 待簽核
  | 'completed'   // 已完成 / 已核准
  | 'abnormal'    // 異常 / 退回
  | 'overdue'     // 逾期

// ── 事件顏色常數 ──────────────────────────────────────────────────────────────
export const EVENT_TYPE_COLORS: Record<CalendarEventType, string> = {
  hotel_pm:   '#1B3A5C',  // 飯店保養 — 品牌主色（深藍）
  mall_pm:    '#4BA8E8',  // 商場保養 — 品牌輔色（天藍）
  full_pm:    '#006d75',  // 全棟維護 — 暗青
  pm_plan:    '#52c41a',  // 週期保養預排 — 綠（主管排定）
  approval:   '#fa8c16',  // 簽核管理 — 橙
  memo:       '#722ed1',  // 公告牆   — 紫
  custom:     '#13c2c2',  // 自訂事件 — 青
}

export const EVENT_TYPE_LABELS: Record<CalendarEventType, string> = {
  hotel_pm:   '飯店保養',
  mall_pm:    '商場保養',
  full_pm:    '全棟維護',
  pm_plan:    '週期預排',
  approval:   '簽核管理',
  memo:       '公告牆',
  custom:     '自訂事件',
}

// ── 聚合事件（來自後端 /calendar/events）────────────────────────────────────
export interface CalendarEvent {
  id:           string
  title:        string
  start:        string           // ISO date "2026-04-15"
  end?:         string | null
  all_day:      boolean
  event_type:   CalendarEventType
  module_label: string
  source_id:    string
  status:       CalendarEventStatus | string
  status_label: string
  responsible:  string
  description:  string
  deep_link:    string           // React Router 路徑
  color:        string
  zone:         string           // 區域別：飯店/商場/公區/其它
  ragic_url:    string           // Ragic 原始記錄連結（空=無連結）

  // ── 明細 Drawer 強制規範欄位（CLAUDE.md §7 / WORK_JOURNAL_SPEC.md §9，2026-07-13 補上）──
  detail:         Record<string, string>  // 明細欄位區（來源模組原始欄位，中文 key）
  image_item_id:  string                  // 附圖查詢用項目 ragic_id（空=此事件無附圖可查）
}

export interface CalendarEventsResponse {
  events: CalendarEvent[]
  total:  number
}

// ── 今日摘要 KPI ──────────────────────────────────────────────────────────────
export interface CalendarTodaySummary {
  today:            string
  total_events:     number
  pending_count:    number
  abnormal_count:   number
  overdue_count:    number
  approval_pending: number
  high_risk_count:  number
  event_by_type:    Record<string, number>
}

// ── 自訂事件 ──────────────────────────────────────────────────────────────────
export interface CalendarCustomEvent {
  id:           string
  title:        string
  description:  string
  start_date:   string           // YYYY-MM-DD
  end_date:     string
  all_day:      boolean
  start_time:   string           // HH:MM
  end_time:     string
  color:        string
  responsible:  string
  created_by:   string
  created_at?:  string
}

export interface CustomEventCreatePayload {
  title:        string
  description?: string
  start_date:   string
  end_date?:    string
  all_day?:     boolean
  start_time?:  string
  end_time?:    string
  color?:       string
  zone?:        string           // 區域別：飯店/商場/公區/其它
  responsible?: string
}

// ── 前端 FullCalendar 事件格式（EventInput）──────────────────────────────────
export interface FCEventInput {
  id:            string
  title:         string
  start:         string
  end?:          string | null
  allDay?:       boolean
  backgroundColor: string
  borderColor:   string
  textColor?:    string
  extendedProps: CalendarEvent
}

// ── 篩選器狀態 ────────────────────────────────────────────────────────────────
export interface CalendarFilters {
  types: CalendarEventType[]   // 空陣列=全選
}
