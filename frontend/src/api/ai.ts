/**
 * AI 工單查詢助理 API 封裝
 * 所有對 /api/v1/ai/* 的請求統一在此處理
 */
import apiClient from '@/api/client'

// ── 型別定義 ──────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface RepairRow {
  location: string        // "飯店" | "商場"
  case_no: string
  title: string
  floor: string
  status: string          // "已結案" | "未結案"
  occurred_at: string     // "YYYY-MM-DD"
  responsible_unit: string
  close_days: number | null
  total_fee: number
}

export interface AIQueryRequest {
  question: string
  messages: ChatMessage[]
}

export interface AIQueryResponse {
  answer: string
  has_table: boolean
  table_data: RepairRow[]
  total_count: number | null
}

export interface HistoryItem {
  id: string
  question: string
  answer: string
  has_table: boolean
  table_data: RepairRow[]
  total_count: number | null
  from_cache: boolean
  created_at: string   // "MM/DD HH:MM"
}

// ── API 呼叫 ──────────────────────────────────────────────────────────────────

export async function queryWorkorder(payload: AIQueryRequest): Promise<AIQueryResponse> {
  const res = await apiClient.post<AIQueryResponse>('/ai/query-workorder', payload)
  return res.data
}

export async function getAIHistory(limit = 30): Promise<HistoryItem[]> {
  const res = await apiClient.get<HistoryItem[]>(`/ai/history?limit=${limit}`)
  return res.data
}
