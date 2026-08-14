/**
 * 營運分析 — 訂房分析 API 封裝
 * Prefix: /api/v1/opera/reservations
 *
 * ⚠️ **分析母體與 `api/opera.ts` 的住客端點不同**：
 *    這裡是「**所有訂房**」（含未來、含取消），那裡是「**已離店的住客**」。
 *    同一維度數字不同是正常的。刻意另開檔案，讓差異在 import 時就看得出來。
 *
 * ⚠️ 查詢端點只讀本地資料表，不打 OHIP。只有 `/sync/*` 會實際呼叫 API。
 */
import apiClient from '@/api/client'

const RSV = '/opera/reservations'

export type RsvDimension =
  | 'market_code' | 'rate_code' | 'source_code' | 'channel' | 'room_type'
  | 'travel_agent_name' | 'company_name' | 'group_name' | 'nationality'

/** ⚠️ 每個分析都帶這個。低填充率的維度做排行會偏頗，畫面必須顯示。 */
export interface Coverage {
  filled: number
  total: number
  ratio: number | null
  /** 填充率 < 50%，畫面應加警語而不是直接畫排行榜 */
  is_low: boolean
}

export interface RsvSource {
  provider: string
  hotel_id: string
  /** ⚠️ 母體差異說明，必須顯示在畫面上 */
  population: string
  note: string
}

export interface DataRange {
  start: string | null
  end: string | null
  /** ⚠️ 本模組含未來資料，過去導向的分析要用這個當 anchor（CLAUDE.md §8.2） */
  last_past: string | null
  has_data: boolean
  reservations: number
}

export interface LeadBucket {
  bucket: string
  reservations: number
  room_nights: number
  cancelled: number
  share: number | null
  cancel_rate: number | null
}

export interface BookingWindowResult {
  range: { start: string; end: string; basis: string }
  buckets: LeadBucket[]
  stats: {
    count: number; median: number | null; p25: number | null
    p75: number | null; mean: number | null; max: number | null
  }
  coverage: Coverage
  source: RsvSource
}

export interface CancellationResult {
  range: { start: string; end: string; basis: string }
  summary: {
    reservations: number; cancelled: number; cancel_rate: number | null
    lost_room_nights: number; median_notice_days: number | null
  }
  reasons: Array<{ reason_code: string; count: number; share: number | null }>
  coverage: Coverage
  source: RsvSource
}

export interface OnTheBooksResult {
  range: { start: string; end: string; days_ahead: number }
  dimension: RsvDimension
  days: Array<{
    business_date: string; room_nights: number
    room_revenue: number | null; adr: number | null
    by_dimension: Record<string, number>
  }>
  segments: Array<Record<string, any>>
  summary: { room_nights: number; room_revenue: number | null }
  coverage: Coverage
  source: RsvSource
}

export interface DimensionResult {
  range: { start: string; end: string }
  dimension: RsvDimension
  rows: Array<Record<string, any>>
  coverage: Coverage
  source: RsvSource
}

export interface LosResult {
  range: { start: string; end: string }
  buckets: Array<{ bucket: string; reservations: number; room_nights: number; share: number | null }>
  source: RsvSource
}

export interface BlockRow {
  block_id: string; block_code: string; block_name: string
  status: string; block_type: string; market_code: string
  source_code: string; booking_medium: string; company_name: string
  start_date: string; end_date: string; cut_off_days: number | null
  original_rooms: number; current_rooms: number; pickup_rooms: number
  pickup_rate: number | null; unsold_rooms: number
  room_revenue: number | null
  cancellation_code: string; cancellation_date: string
}

export interface BlockResult {
  range: { start: string; end: string }
  blocks: BlockRow[]
  summary: {
    block_count: number; original_rooms: number; current_rooms: number
    pickup_rooms: number; pickup_rate: number | null; unsold_rooms: number
    room_revenue: number | null; cancelled_blocks: number
  }
  /** ⚠️ false = 整批 cutOffDays 都是 0，該飯店沒在用 cut-off，畫面應隱藏該欄 */
  cutoff_in_use: boolean
  source: RsvSource
}

export interface RsvSyncStatus {
  reservation: BackfillProgress
  block: BackfillProgress
  recent: Array<{
    dataset: string; mode: string; date_start: string; date_end: string
    status: string; parent_rows: number; child_rows: number
    api_calls: number; elapsed_ms: number; started_at: string | null
    warnings: string[]; error: string; triggered_by: string
  }>
  data_range: DataRange
  config: Record<string, any>
}

export interface BackfillProgress {
  dataset: string
  total_chunks: number; done_chunks: number; pending_chunks: number
  chunk_days: number
  range: { start: string | null; end: string | null; years: number }
  /** ⚠️ 2026-08-13 新增。**天數才是誠實的口徑** —— 舊版「整段有沒有資料就算補過」
   *  造成假性完成（顯示 24/24 完成，實際整月 0 筆）。段數會因缺口分散而失真，
   *  畫面請以 missing_days 為準。 */
  total_days: number
  covered_days: number
  missing_days: number
  next_chunk: { start: string; end: string } | null
  estimated_remaining_seconds: number
}

const get = async <T>(path: string, params?: any): Promise<T> =>
  (await apiClient.get(`${RSV}${path}`, { params })).data

export const fetchRsvDataRange = () => get<DataRange>('/data-range')
export const fetchBookingWindow = (p: { start: string; end: string }) =>
  get<BookingWindowResult>('/booking-window', p)
export const fetchCancellations = (p: { start: string; end: string }) =>
  get<CancellationResult>('/cancellations', p)
export const fetchOnTheBooks = (p: { days_ahead?: number; dimension?: RsvDimension }) =>
  get<OnTheBooksResult>('/on-the-books', p)
export const fetchRsvDimension = (p: { start: string; end: string; dimension: RsvDimension }) =>
  get<DimensionResult>('/dimension', p)
export const fetchRsvLos = (p: { start: string; end: string }) =>
  get<LosResult>('/los', p)
export const fetchBlocks = (p: { start: string; end: string }) =>
  get<BlockResult>('/blocks', p)
export const fetchRsvSyncStatus = () => get<RsvSyncStatus>('/sync/status')

/** ⚠️ 每次只補一段。可重複呼叫直到 `pending_chunks` 歸零。 */
export async function backfillRsvChunk(dataset: 'reservation' | 'block') {
  const res = await apiClient.post(`${RSV}/sync/backfill`, null, { params: { dataset } })
  return res.data as {
    done: boolean; message?: string
    result?: { status: string; parent_rows: number; child_rows: number; error: string }
    progress: BackfillProgress
  }
}
