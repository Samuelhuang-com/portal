/**
 * 行事曆模組 TypeScript 型別定義
 */

// ── 事件類型 ──────────────────────────────────────────────────────────────────
export type CalendarEventType =
  | 'hotel_pm'    // 飯店週期保養
  | 'mall_pm'     // 商場週期保養
  | 'security'    // 保全巡檢
  | 'inspection'  // 工務巡檢
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
  hotel_pm:   '#1B3A5C',  // 飯店保養 — 品牌主色
  mall_pm:    '#4BA8E8',  // 商場保養 — 品牌輔色
  security:   '#52c41a',  // 保全巡檢 — 綠
  inspection: '#1677ff',  // 工務巡檢 — 藍
  approval:   '#fa8c16',  // 簽核管理 — 橙
  memo:       '#722ed1',  // 公告牆   — 紫
  custom:     '#13c2c2',  // 自訂事件 — 青
}

export const EVENT_TYPE_LABELS: Record<CalendarEventType, string> = {
  hotel_pm:   '飯店保養',
  mall_pm:    '商場保養',
  security:   '保全巡檢',
  inspection: '工務巡檢',
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
