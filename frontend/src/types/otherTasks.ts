/**
 * 主管交辦／緊急事件 TypeScript 型別定義
 */

export interface OtherTaskImage {
  url:      string
  filename: string
}

export interface OtherTask {
  ragic_id:    string
  ragic_url:   string
  task_type:   string   // "上級交辦" | "緊急事件"
  supervisor:  string   // 交辦主管
  engineer:    string   // 工程人員
  created_at:  string   // 建立日期
  description: string   // 問題說明
  notes:       string   // 備註
  updated_at:  string   // 最後更新日期
  status:      string   // 狀態
  work_hours:  number | null  // 維修工時
  year:        number | null
  month:       number | null
  images:      OtherTaskImage[]
  detail:      Record<string, string>
}

export interface OtherTaskDetailResult {
  items:     OtherTask[]
  total:     number
  page:      number
  page_size: number
}

export interface OtherTaskFilterOptions {
  statuses:    string[]
  supervisors: string[]
  engineers:   string[]
}

export interface OtherTaskDetailParams {
  task_type?:  string
  year?:       number
  month?:      number
  status?:     string
  supervisor?: string
  engineer?:   string
  search?:     string
  page?:       number
  page_size?:  number
  sort_field?: string
  sort_order?: 'asc' | 'desc'
}
