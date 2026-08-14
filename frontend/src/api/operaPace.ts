/**
 * 營運分析 — 訂房 Pace／Pickup API 封裝
 * Prefix: /api/v1/opera/pace
 *
 * ⚠️ **這一頁的歷史進度是「回推」出來的**：訂房同步是整列覆寫、無版本，
 *    所以我們只有「每筆訂房現在長什麼樣」。本模組用 booking_date /
 *    cancellation_date 把現況往回切，已含後續改期與取消的結果。
 *    `source.population` 會把這句話帶到畫面上 —— 不要拿掉。
 *
 * ⚠️ 與 `api/operaReservation.ts` 的差別：那邊看訂單「現在」長什麼樣，
 *    這邊多一個 `as_of`（觀察時點）維度。
 *
 * ⚠️ 只讀本地資料表，不打 OHIP，不計費。
 */
import apiClient from '@/api/client'

const PACE = '/opera/pace'

export type PaceDimension =
  | 'market_code' | 'room_type' | 'channel' | 'rate_code' | 'source_code'

export type CompareMode = 'weekday' | 'date'

export interface Coverage {
  filled: number
  total: number
  ratio: number | null
  /** 填充率 < 50%，畫面必須加警語 */
  is_low: boolean
}

export interface PaceSource {
  provider: string
  hotel_id: string
  /** ⚠️ 回推失真說明，必須顯示在畫面上 */
  population: string
  precision: string
  note: string
}

export interface SnapshotReadiness {
  distinct_snapshot_days: number
  first_snapshot_date: string | null
  last_snapshot_date: string | null
  business_days_with_final: number
  required_days: number
  ready: boolean
  remaining_days: number
}

export interface PaceDataRange {
  start: string | null
  end: string | null
  last_past: string | null
  earliest_booking_date: string | null
  has_data: boolean
  /** 狀態是取消但無取消日期，無法定位時點，已從所有觀察點排除 */
  unresolved_cancels: number
  snapshot: SnapshotReadiness
  source: PaceSource
}

export interface CurvePoint {
  lead_days: number
  as_of: string
  room_nights: number
  room_revenue: number | null
  adr: number | null
  ly_room_nights: number | null
  vs_ly: number | null
  vs_ly_rooms: number | null
}

export interface CurveResult {
  stay_date: string
  compare: CompareMode
  ly_stay_date: string
  points: CurvePoint[]
  final: number
  ly_final: number
  unresolved_cancels: number
  /** ⚠️ 沒有訂房日的房晚數，無法回推故排除。這是本頁與訂房分析對不起來的原因，必須顯示 */
  missing_booking_date: number
  source: PaceSource
}

export interface OtbRow {
  stay_date: string
  weekday: number
  is_weekend: boolean
  lead_days_now: number
  /** key 是 lead 天數字串；⚠️ null = 觀察日還沒到，不是 0 */
  otb: Record<string, number | null>
  room_nights: number
  room_revenue: number | null
  adr: number | null
  /** 以 as_of 為右端點、往前 window 天的淨 pickup */
  pickup_net: number
  pickup_new: number
  pickup_cancels: number
  ly_stay_date: string
  ly_room_nights: number
  vs_ly: number | null
}

export interface OtbMatrixResult {
  range: { start: string; end: string }
  leads: number[]
  compare: CompareMode
  /** 實際採用的觀察日（未帶參數時是今天） */
  as_of: string
  window: number
  rows: OtbRow[]
  summary: { room_nights: number; ly_room_nights: number; pickup_net: number }
  unresolved_cancels: number
  /** ⚠️ 沒有訂房日的房晚數，無法回推故排除。這是本頁與訂房分析對不起來的原因，必須顯示 */
  missing_booking_date: number
  revenue_coverage: Coverage
  source: PaceSource
}

export interface PickupRow {
  stay_date: string
  weekday: number
  gross_new: number
  cancels: number
  net: number
  otb_before: number
  otb_after: number
  /** 恆等式自我檢查：OTB 差值 == 淨 pickup */
  verified: boolean
}

export interface PickupResult {
  range: { start: string; end: string }
  window: number
  from: string
  to: string
  rows: PickupRow[]
  summary: { gross_new: number; cancels: number; net: number }
  unresolved_cancels: number
  /** ⚠️ 沒有訂房日的房晚數，無法回推故排除 */
  missing_booking_date: number
  verify: { all_passed: boolean; warnings: string[] }
  source: PaceSource
}

export interface PickupDimensionResult {
  range: { start: string; end: string }
  dimension: PaceDimension
  window: number
  from: string
  to: string
  rows: Array<{
    key: string; gross_new: number; cancels: number
    net: number; otb_after: number
  }>
  unresolved_cancels: number
  /** ⚠️ 沒有訂房日的房晚數，無法回推故排除 */
  missing_booking_date: number
  coverage: Coverage
  /** ⚠️ 恆為 true：維度取自訂房目前狀態，畫面必須標「參考值」 */
  is_reference_only: boolean
  source: PaceSource
}

export interface DayDetailItem {
  confirmation_no: string
  booking_date: string
  cancellation_date: string
  cancellation_reason_code: string
  arrival: string
  departure: string
  nights: number | null
  lead_days: number | null
  resv_status: string
  market_code: string
  room_type: string
  rate_code: string
  channel: string
  room_revenue: number | null
  /** 非 Ragic 來源，恆為空字串（CLAUDE.md §7 該欄不適用） */
  ragic_url: string
}

export interface DayDetailResult {
  stay_date: string
  window: number
  from: string
  to: string
  added: DayDetailItem[]
  cancelled: DayDetailItem[]
  summary: { gross_new: number; cancels: number; net: number }
  source: PaceSource
}

const get = async <T>(path: string, params?: any): Promise<T> =>
  (await apiClient.get(`${PACE}${path}`, { params })).data

export const fetchPaceDataRange = () => get<PaceDataRange>('/data-range')

export const fetchPaceReadiness = () => get<SnapshotReadiness>('/readiness')

export const fetchPaceCurve = (p: {
  stay_date: string; compare?: CompareMode; max_lead?: number
}) => get<CurveResult>('/curve', p)

/** ⚠️ 看歷史區間務必帶 as_of，否則 pickup 欄永遠是 0 */
export const fetchOtbMatrix = (p: {
  start: string; end: string; leads?: string; compare?: CompareMode
  as_of?: string; window?: number
}) => get<OtbMatrixResult>('/otb-matrix', p)

export const fetchPacePickup = (p: {
  start: string; end: string; window?: number; as_of?: string
}) => get<PickupResult>('/pickup', p)

export const fetchPacePickupDimension = (p: {
  start: string; end: string; dimension: PaceDimension
  window?: number; as_of?: string
}) => get<PickupDimensionResult>('/pickup/dimension', p)

export const fetchPaceDayDetail = (p: {
  stay_date: string; window?: number; as_of?: string
}) => get<DayDetailResult>('/day-detail', p)
