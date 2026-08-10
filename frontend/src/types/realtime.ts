/**
 * 即時營運 — TypeScript 型別定義
 *
 * 規格書：docs/SPEC_realtime_operations.md
 *
 * ⚠️ 與 `types/opera.ts`（人工上傳 TXT）**完全獨立**：
 *    兩者資料來源與時點不同，型別刻意不共用，避免日後被誤當成同一份資料。
 */

// ── OPERA 即時房況（OHIP API，2026-08-06）─────────────────────────────────────
// ⚠️ 與上方的上傳型資料**來源不同、時點不同**，畫面上必須分開標示，不可混用。
// ⚠️ 不含 ADR / RevPAR / 營收 —— 實測確認 OHIP 這支端點不回傳（見 docs/OHIP_INTEGRATION.md §4.3）。

export interface LiveTokenStatus {
  cached: boolean
  expires_in_seconds: number
}

/** 畫面上「API 執行資料」那一列所需的全部欄位 */
export interface LiveSourceMeta {
  provider: string
  gateway: string
  hotel_id: string
  endpoint: string
  status_code: number | null
  elapsed_ms: number | null
  request_id: string
  from_cache: boolean
  cache_ttl_seconds: number
  /** 資料實際從 API 抓下來的時間；快取命中時為當初那一次 */
  fetched_at: string | null
  cache_age_seconds: number | null
  /** 這次請求的檢查時間 */
  checked_at: string
  token: LiveTokenStatus
}

export interface LiveDayRow {
  business_date: string
  is_weekend: boolean
  inventory_rooms: number | null
  rooms_sold: number | null
  available_rooms: number | null
  ooo_rooms: number | null
  arrival_rooms: number | null
  departure_rooms: number | null
  people_in_house: number | null
  comp_rooms: number | null
  house_use_rooms: number | null
  day_use_rooms: number | null
  overbooking_rooms: number | null
  sell_limit_rooms: number | null
  /** API 不回傳，由後端以 rooms_sold ÷ (inventory − ooo) 計算 */
  occupancy: number | null
}

export interface LiveRoomType {
  room_type: string
  description: string
  days: LiveDayRow[]
}

export interface LiveStatusResult {
  configured: boolean
  missing: string[]
  house: LiveDayRow[]
  room_types: LiveRoomType[]
  source: LiveSourceMeta
}

export interface OhipCallLogRow {
  id: number
  called_at: string
  endpoint: string
  hotel_id: string
  date_start: string
  date_end: string
  status_code: number
  elapsed_ms: number
  request_id: string
  success: boolean
  error: string
  triggered_by: string
}

export interface OhipCallLogResult {
  total: number
  items: OhipCallLogRow[]
}

export interface LiveBusinessDate {
  configured: boolean
  business_date: string | null
  error?: string
}

// ── API vs TXT 逐欄比對（Phase 0-6，2026-08-06）────────────────────────────────
// ⚠️ 營收類欄位 API 不回傳，status 為 'api_unavailable'，**不計入差異統計**，
//    否則差異率會被灌爆而失去意義。

export type CompareFieldStatus = 'match' | 'diff' | 'missing' | 'api_unavailable'
export type CompareCoverage = 'both' | 'api_only' | 'txt_only'

export interface CompareField {
  label: string
  api: number | null
  txt: number | null
  diff: number | null
  status: CompareFieldStatus
}

export interface CompareRow {
  business_date: string
  coverage: CompareCoverage
  has_diff: boolean
  fields: CompareField[]
}

export interface CompareSummary {
  days_total: number
  days_both: number
  days_api_only: number
  days_txt_only: number
  days_with_diff: number
  fields_match: number
  fields_diff: number
  fields_api_unavailable: number
  match_rate: number | null
  tolerance: number
}

export interface CompareSource {
  provider: string
  hotel_id: string
  endpoint: string
  status_code: number | null
  elapsed_ms: number | null
  request_id: string
  from_cache: boolean
  fetched_at: string
  txt_source: string
}

export interface CompareResult {
  configured: boolean
  missing: string[]
  range?: { start: string; end: string }
  rows: CompareRow[]
  summary: CompareSummary
  source: CompareSource | null
  notes?: string[]
}

// ── OPERA API 營收與結構分析（2026-08-06）──────────────────────────────────────
// ⚠️ 來自**非同步版** API，與上方即時房況（同步版）不是同一支端點。
// ⚠️ 缺欄位一律 null（不是 0）——「沒有回傳」與「值為 0」是不同的事。

export type RevenueGroupBy = 'MarketCode' | 'RoomType' | 'GuaranteeType'

export interface ApiRevenueDay {
  business_date: string
  market_code: string | null
  room_type: string | null
  res_type: string | null
  physical_rooms: number | null
  ooo_rooms: number | null
  oos_rooms: number | null
  available_rooms: number | null
  rooms_sold: number | null
  room_revenue: number | null
  total_revenue: number | null
  other_revenue: number | null
  arrival_rooms: number | null
  departure_rooms: number | null
  cancelled_rooms: number | null
  no_show_rooms: number | null
  food_revenue: number | null
  adr: number | null
  revpar: number | null
  occupancy: number | null
}

export interface ApiRevenueGroupRow {
  market_code?: string
  room_type?: string
  days: number
  rooms_sold: number
  available_rooms: number
  room_revenue: number
  total_revenue: number
  cancelled_rooms: number
  arrival_rooms: number
  departure_rooms: number
  adr: number | null
  revpar: number | null
  occupancy: number | null
}

export interface ApiRevenueSummary {
  days: number
  rooms_sold: number
  available_rooms: number
  room_revenue: number
  total_revenue: number
  other_revenue: number
  cancelled_rooms: number
  arrival_rooms: number
  departure_rooms: number
  adr: number | null
  revpar: number | null
  occupancy: number | null
  /** TXT 版算不出來的指標 */
  cancel_rate: number | null
}

export interface ApiRevenueSource {
  provider: string
  hotel_id: string
  ext_system_code: string
  endpoint: string
  status_code: number | null
  elapsed_ms: number | null
  poll_count: number | null
  request_id: string
  /** 超過單段上限會切段，每段各算一次 API 呼叫 */
  segments: number
  from_cache: boolean
  cache_ttl_seconds: number
  fetched_at: string | null
  cache_age_seconds: number | null
  checked_at: string

  /** 目前實際採用的單段上限（可能已從 400 自動降級為 94） */
  max_span_days: number
  /** 理論上限（OPERA Cloud 23.2+ 為 400） */
  preferred_span_days?: number
  /** true = 曾被 OPERA 拒絕過長區間，已降級 */
  span_downgraded?: boolean

  /**
   * OPERA 對相同條件的非同步查詢強制的最短間隔（秒，官方為 1800）。
   * ⚠️ 這不是 Portal 自訂的節流，是 OPERA 端的硬規定。
   */
  min_interval_seconds?: number
  /** 距離可以再次取數還剩幾秒；0 = 現在就可以 */
  cooldown_remaining_seconds?: number
  /** 前端據此 disable「略過快取重查」 */
  can_force?: boolean

  /** 本次 API 回應大小（bytes） */
  response_bytes?: number | null
  /** true = 已逼近 2 MB，資料可能被靜默截斷（**非確認值**） */
  truncation_risk?: boolean
}

export interface ApiRevenueResult {
  configured: boolean
  missing: string[]
  range?: { start: string; end: string; days: number; segments: number }
  group_by: RevenueGroupBy[]
  days: ApiRevenueDay[]
  summary: ApiRevenueSummary
  by_market: ApiRevenueGroupRow[]
  by_room_type: ApiRevenueGroupRow[]
  /** 如實說明哪些欄位這次沒回傳，而不是默默顯示空白 */
  notes: string[]
  source: ApiRevenueSource | null
}
