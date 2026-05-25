/**
 * 飯店 Dashboard PPT 匯出 — API 封裝
 * 對應後端 /api/v1/hotel/ppt-export/*
 */
import apiClient from '@/api/client'

// ─────────────────────────────────────────────────────────────────────────────
// 型別定義
// ─────────────────────────────────────────────────────────────────────────────

export interface PptSectionMeta {
  export_key:         string
  module_key:         string
  tab_name:           string
  second_title:       string
  second_title_default: string
  description:        string
  export_type:        string
  slide_layout:       string
  supports_detail:    boolean
  detail_description: string
  data_source:        string
  sort_order:         number
  slide_group_id:     string | null
}

export interface PptConfigItem {
  export_key:           string
  tab_name:             string
  second_title:         string
  second_title_default: string       // registry 預設值（B-1 placeholder 用）
  second_title_override: string | null  // 使用者自訂覆寫值（B-1）
  description:          string
  supports_detail:      boolean
  detail_description:   string
  data_source:          string
  slide_layout:         string
  slide_group_id:       string | null  // A-1：Dashboard 群組代表 key
  // 使用者偏好
  enabled:              boolean
  include_detail:       boolean
  sort_order:           number
}

export interface PptConfigResponse {
  module_key:  string
  template_id: string
  config:      PptConfigItem[]
  updated_by:  string | null
  updated_at:  string | null
}

export interface SaveConfigPayload {
  config: {
    export_key:            string
    enabled:               boolean
    include_detail:        boolean
    sort_order:            number
    second_title_override: string | null
  }[]
  template_id: string
}

// B-3：匯出歷史
export interface PptExportHistoryItem {
  id:            number
  year:          number
  month:         number
  exported_by:   string
  exported_at:   string
  template_id:   string | null
  sections:      string[]
  section_count: number
}

// C-2：模板
export interface PptTemplate {
  id:          string
  label:       string
  filename:    string
  description: string
  available:   boolean
}

// 前端計算出的圖表資料（KPI / 決策圖表）
export interface PptFrontendData {
  kpi_summary?: {
    total_cases:       number
    total_completed:   number
    total_work_hours:  number
    completion_rate:   number
  }
  source_cards?: {
    category:        string
    total:           number
    completed:       number
    work_hours:      number
    completion_rate: number
  }[]
  repair_costs?: {
    category: string
    amount:   number
  }[]
  bar_chart_data?: {
    date:    string
    [key: string]: string | number
  }[]
  rate_chart_data?: {
    date: string
    rate: number
  }[]
  dazhi_trend_data?: {
    date:      string
    total:     number
    completed: number
  }[]
  hours_pie_data?: {
    category: string
    hours:    number
  }[]
}

export interface ExportPayload {
  year:            number
  month:           number
  inspection_date: string
  frontend_data:   PptFrontendData
}

// ─────────────────────────────────────────────────────────────────────────────
// API 函式
// ─────────────────────────────────────────────────────────────────────────────

/** 取得所有已註冊的 Section metadata（不含使用者偏好） */
export async function fetchPptSections(): Promise<PptSectionMeta[]> {
  const res = await apiClient.get<PptSectionMeta[]>('/hotel/ppt-export/sections')
  return res.data
}

/** 取得合併後的設定（Registry metadata + DB 使用者偏好） */
export async function fetchPptConfig(): Promise<PptConfigResponse> {
  const res = await apiClient.get<PptConfigResponse>('/hotel/ppt-export/config')
  return res.data
}

/** 儲存使用者偏好（enabled / include_detail / sort_order / second_title_override） */
export async function savePptConfig(payload: SaveConfigPayload): Promise<void> {
  await apiClient.post('/hotel/ppt-export/config', payload)
}

/** 取得匯出歷史（B-3） */
export async function fetchPptHistory(limit = 30): Promise<PptExportHistoryItem[]> {
  const res = await apiClient.get<PptExportHistoryItem[]>('/hotel/ppt-export/history', {
    params: { limit },
  })
  return res.data
}

/** 取得可用模板清單（C-2） */
export async function fetchPptTemplates(): Promise<PptTemplate[]> {
  const res = await apiClient.get<PptTemplate[]>('/hotel/ppt-export/templates')
  return res.data
}

/**
 * 觸發 PPTX 匯出並下載
 * 後端回傳 StreamingResponse（application/vnd.openxmlformats-officedocument.presentationml.presentation）
 */
export async function exportPptx(
  payload:  ExportPayload,
  filename = '飯店管理Dashboard.pptx',
): Promise<void> {
  const token = localStorage.getItem('access_token')
  const res = await fetch('/api/v1/hotel/ppt-export/export', {
    method:  'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization:  token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`匯出失敗：${res.status} ${text}`)
  }
  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
