/**
 * 工作日誌 API 封裝
 * 對應後端 /api/v1/work-journal/*
 */
import apiClient from '@/api/client'

export const JOURNAL_CATEGORIES = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢'] as const
export type JournalCategory = typeof JOURNAL_CATEGORIES[number]

export const JOURNAL_SOURCES = [
  'dazhi', 'luqun', 'hotel_pm', 'ihg', 'hotel_di',
  'security', 'mall_pm', 'full_bldg_pm', 'mall_fi', 'full_bi', 'hotel_mr',
  'other_tasks',
] as const
export type JournalSource = typeof JOURNAL_SOURCES[number]

export const SOURCE_LABEL: Record<JournalSource, string> = {
  dazhi:        '飯店工務',
  luqun:        '商場工務',
  hotel_pm:     '飯店週期保養',
  ihg:          'IHG客房保養',
  hotel_di:     '飯店每日巡檢',
  security:     '保全巡檢',
  mall_pm:      '商場週期保養',
  full_bldg_pm: '整棟保養',
  mall_fi:      '商場設施巡檢',
  full_bi:      '整棟巡檢',
  hotel_mr:     '飯店水電錶抄表',
  other_tasks:  '主管交辦/緊急事件',
}

export const CATEGORY_COLOR: Record<JournalCategory, string> = {
  現場報修: '#4BA8E8',
  上級交辦: '#52C41A',
  緊急事件: '#FF4D4F',
  例行維護: '#FA8C16',
  每日巡檢: '#722ED1',
}

export const CATEGORY_TAG_COLOR: Record<JournalCategory, string> = {
  現場報修: 'blue',
  上級交辦: 'green',
  緊急事件: 'red',
  例行維護: 'orange',
  每日巡檢: 'purple',
}

// ── 型別定義 ──────────────────────────────────────────────────────────────────

export interface JournalRow {
  seq:          number
  source:       JournalSource
  source_label: string
  category:     JournalCategory
  task:         string
  person:       string
  est_min:      number | null   // 預估耗時（分鐘），null = 無資料
  start_time:   string          // 'HH:MM' 或 ''
  end_time:     string          // 'HH:MM' 或 ''
  work_min:     number | null   // 工時（分鐘），null = 無資料
  remark:       string          // 備註
  report:       string          // 回報事項
  ragic_id:     string          // 原始記錄 Ragic ID
  ragic_url:    string          // Ragic 記錄直連 URL（空字串 = 無）
  venue:        string          // 歸屬（飯店 / 商場），僅 other_tasks 有值
  detail:       Record<string, string>  // 模組專屬明細欄位
}

export interface JournalPerson {
  person: string
  rows:   JournalRow[]
}

export interface WorkJournalDaily {
  date:        string          // 'YYYY/MM/DD'
  persons:     JournalPerson[]
  total_rows:  number
}

// ── API 函數 ──────────────────────────────────────────────────────────────────

export async function fetchWorkJournalDaily(
  year: number,
  month: number,
  day: number,
): Promise<WorkJournalDaily> {
  const res = await apiClient.get<WorkJournalDaily>('/work-journal/daily', {
    params: { year, month, day },
  })
  return res.data
}

export interface WorkJournalRange {
  date_from:  string
  date_to:    string
  days:       WorkJournalDaily[]
  total_rows: number
}

export async function fetchWorkJournalRange(
  date_from: string,
  date_to: string,
): Promise<WorkJournalRange> {
  const res = await apiClient.get<WorkJournalRange>('/work-journal/range', {
    params: { date_from, date_to },
  })
  return res.data
}

/** 回傳匯出 Excel 的 API URL（由前端用 downloadFile() 觸發下載） */
export function getJournalExcelUrl(
  date_from: string,
  date_to: string,
  person?: string,
): string {
  const params = new URLSearchParams({ date_from, date_to })
  if (person) params.set('person', person)
  return `/api/v1/work-journal/export-excel?${params.toString()}`
}

export interface CaseImageItem { url: string; filename: string }

/**
 * 依來源模組取案件圖片（dazhi / luqun / other_tasks 有圖片端點）
 */
export async function fetchJournalImages(
  source: string,
  ragicId: string,
): Promise<CaseImageItem[]> {
  if (!ragicId) return []
  const BASE_MAP: Record<string, string> = {
    dazhi:       '/dazhi-repair',
    luqun:       '/luqun-repair',
    other_tasks: '/other-tasks',
  }
  const base = BASE_MAP[source]
  if (!base) return []
  try {
    const { default: apiClient } = await import('@/api/client')
    const res = await apiClient.get(`${base}/db-images/${encodeURIComponent(ragicId)}`)
    return res.data?.images ?? []
  } catch {
    return []
  }
}
