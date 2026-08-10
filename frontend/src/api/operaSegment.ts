/**
 * 營運分析 — 市場區隔／房型別趨勢 API 封裝
 *
 * Prefix: /api/v1/opera/segments
 *
 * ⚠️ 這一組端點的資料來源是 **OHIP API 落地**，不是 `api/opera.ts` 其他端點的
 *    TXT 上傳。刻意另開一個檔案而不是塞進 `opera.ts`，就是為了讓來源差異
 *    在 import 的時候就看得出來。
 * ⚠️ 查詢端點讀的是本地資料表，**不會打 OHIP**，所以很快也不計費。
 *    只有 `/sync/*` 那兩支會實際打 OHIP。
 */
import apiClient from '@/api/client'

const SEG = '/opera/segments'

export type SegmentDimension = 'market_code' | 'room_type'

export interface SegmentRow {
  market_code?: string
  room_type?: string
  rooms_sold: number
  available_rooms: number
  room_revenue: number
  total_revenue: number
  cancelled_rooms: number
  arrival_rooms: number
  adr: number | null
  revpar: number | null
  occupancy: number | null
  cancel_rate: number | null
  /** 佔期間房租總額的比例 */
  share: number | null
  prev_room_revenue?: number | null
  prev_adr?: number | null
  /** 去年同期為 0 或缺值時為 null —— 「去年沒有」與「持平」是不同的事 */
  yoy_room_revenue?: number | null
  yoy_adr?: number | null
  /** 去年完全沒有這個區隔 */
  is_new?: boolean
}

export interface SegmentTrendRow extends Omit<SegmentRow, 'share'> {
  month: string
  by_dimension: Record<string, number | null>
}

export interface SegmentSummary {
  rooms_sold: number
  available_rooms: number
  room_revenue: number
  total_revenue: number
  cancelled_rooms: number
  arrival_rooms: number
  adr: number | null
  revpar: number | null
  occupancy: number | null
  cancel_rate: number | null
  prev_room_revenue?: number | null
  prev_adr?: number | null
  prev_occupancy?: number | null
  yoy_room_revenue?: number | null
  yoy_adr?: number | null
  yoy_occupancy?: number | null
}

export interface SegmentResult {
  range: { start: string; end: string }
  yoy_range: { start: string; end: string } | null
  dimension: SegmentDimension
  summary: SegmentSummary
  segments: SegmentRow[]
  trend: SegmentTrendRow[]
  row_count: number
  source: {
    provider: string
    table: string
    hotel_id: string
    /** ⚠️ 這句必須顯示在畫面上 —— 同模組混了兩種資料來源 */
    note: string
  }
  data_range: { start: string | null; end: string | null; has_data: boolean }
}

export interface SegmentSyncStatus {
  progress: {
    total_chunks: number
    done_chunks: number
    pending_chunks: number
    chunk_days: number
    range: { start: string | null; end: string | null; years: number }
    next_chunk: { start: string; end: string } | null
    estimated_remaining_seconds: number
  }
  recent: Array<{
    mode: string
    date_start: string
    date_end: string
    status: string
    rows_written: number
    api_calls: number
    elapsed_ms: number
    started_at: string | null
    warnings: string[]
    error: string
    triggered_by: string
  }>
  data_range: { start: string | null; end: string | null; has_data: boolean }
  config: { backfill_years: number; chunk_days: number; incremental_days: number }
}

export async function fetchSegments(params: {
  start: string
  end: string
  dimension?: SegmentDimension
  compare_yoy?: boolean
}): Promise<SegmentResult> {
  const res = await apiClient.get(SEG, { params })
  return res.data
}

export async function fetchSegmentSyncStatus(): Promise<SegmentSyncStatus> {
  const res = await apiClient.get(`${SEG}/sync/status`)
  return res.data
}

/** ⚠️ 每次只補一段（約 45 天）。可以重複呼叫直到 `pending_chunks` 歸零。 */
export async function backfillNextChunk(): Promise<{
  done: boolean
  message?: string
  result?: { status: string; rows_written: number; warnings: string[]; error: string }
  progress: SegmentSyncStatus['progress']
}> {
  const res = await apiClient.post(`${SEG}/sync/backfill`)
  return res.data
}
