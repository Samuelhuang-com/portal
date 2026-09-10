/**
 * 競品分析 — 型別定義
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §8
 *
 * ⚠️ 三個口徑名詞在整個前端都要用一致的字，不要各頁自己翻：
 *    · `price_gross`  ＝ **含稅價**（旅客實付）
 *    · `price_pretax` ＝ **稅前價**（排除各家不同的服務費政策，指數預設用它）
 *    · `is_sold_out`  ＝ **三態**：yes 賣完 / no 有房 / unknown 未知
 */

/** 價格口徑。畫面切換用，預設 pretax。 */
export type PriceBasis = 'pretax' | 'gross'

/** 滿房三態。⚠️ 不是布林 —— 地點查詢路徑判不出來，一律 unknown。 */
export type SoldOutState = 'yes' | 'no' | 'unknown'

/** 含稅三態。⚠️ `no` 只有 CSV 匯入會出現，SerpApi 永遠推導不出來。 */
export type TaxState = 'yes' | 'no' | 'unknown'

export type FetchPath = 'token' | 'location' | ''
export type PlanLevel = 'A' | 'B' | 'C'
export type FetchStatus =
  | 'running' | 'success' | 'partial' | 'failed' | 'quota_exceeded' | 'skipped'

export interface QuotaStatus {
  subscriber_id: number
  period_start: string
  monthly_quota: number
  granted: number
  limit: number
  used: number
  available: number
  usage_ratio: number
  is_exhausted: boolean
  is_active: boolean
}

export interface SubscriberBrief {
  id: number
  code: string
  name: string
  plan_level: PlanLevel
  is_active: boolean
}

export interface CompsetHotelRow {
  id: number
  subscriber_id: number
  hotel_code: string
  display_name: string
  google_property_token: string
  google_query_name: string
  /** 簡稱，可留空 */
  short_name: string
  /** 簡稱，留空時後端已退回 `display_name` —— 顯示一律用這個 */
  short_label: string
  is_self: boolean
  is_enabled: boolean
  sort_order: number
  room_count: number | null
  registered_address: string
  note: string
  /** 缺 token 的家 A 級抓不到 —— 畫面要提示，不要讓人以為系統壞了。 */
  has_token: boolean
  /** 經緯度。⚠️ 可為 null —— 手動新增的家不一定有座標 */
  latitude: number | null
  longitude: number | null
}

/**
 * 搜尋回來的候選飯店（尚未加入競爭組）。
 *
 * ⚠️ **沒有地址也沒有房數** —— 地點查詢的回應裡就是沒有這兩欄
 *    （只有 property_token 路徑才有地址）。帶入後要人自己補。
 */
export interface HotelCandidate {
  name: string
  property_token: string
  latitude: number | null
  longitude: number | null
  price_gross: number | null
  price_pretax: number | null
  hotel_class: number | null
  overall_rating: number | null
  reviews: number | null
  /** 與「自己」那一家的直線距離（公里）。任一方缺座標就是 null */
  distance_km: number | null
  /** 已經在競爭組裡。⚠️ 要**標出來**不是濾掉，否則使用者會以為漏抓 */
  in_compset: boolean
}

export interface HotelSearchResult {
  items: HotelCandidate[]
  self: { latitude: number | null; longitude: number | null } | null
  query: string
  check_in_date: string
  /** 實際送出幾次 ＝ 扣了幾次配額 */
  request_count: number
  quota: QuotaStatus
  warnings: string[]
}

/** 一格（某家 × 某入住日）的價格。 */
export interface RateCell {
  price_gross: number | null
  price_pretax: number | null
  tax_included: TaxState
  is_sold_out: SoldOutState
  source: string
  fetch_path: FetchPath
  tier: string
  ota_name: string
  is_official: boolean
  num_guests: number | null
  snapshot_id: number
}

/**
 * 一天的彙總指標。
 *
 * ⚠️ `index_*` 一定要跟 `sample_count` / `is_low_sample` 一起顯示 ——
 *    只給一個數字，「4 家算出來的指數」和「1 家算出來的指數」會長得一模一樣。
 */
export interface DailyStat {
  stay_date: string
  snapshot_date: string
  self_pretax: number | null
  median_pretax: number | null
  min_pretax: number | null
  max_pretax: number | null
  index_pretax: number | null
  self_gross: number | null
  median_gross: number | null
  min_gross: number | null
  max_gross: number | null
  index_gross: number | null
  /**
   * 進中位數的**競品**家數（不含自己）。
   * ⚠️ 語意是「稅前優先，稅前全缺才退回含稅」——這是給 DB 快取欄位與
   *    `is_low_sample` 用的。**畫面請用 `sample_count_pretax` /
   *    `sample_count_gross`**，或直接用 `components` 的 `sampleCountOf()`。
   */
  sample_count: number
  /** 稅前口徑進中位數的競品家數 */
  sample_count_pretax: number
  /** 含稅口徑進中位數的競品家數。⚠️ 與稅前常常不一樣（地點查詢第 2 頁沒有稅前價） */
  sample_count_gross: number
  sold_out_count: number
  /**
   * 滿房的**競品** hotel id（不含自己）。⚠️ 只有 id 沒有名字 ——
   * 用 `DashboardResult.hotels` / `MatrixResult.hotels` 去查。
   */
  sold_out_hotel_ids: number[]
  /** 有進中位數，但滿房狀態未知（B／C 級遠期資料） */
  unknown_count: number
  /** 含稅價由低到高的名次（含自己）。⚠️ 顯示成 `3 / 5`，不可只寫「第 3 名」 */
  self_rank: number | null
  rank_total: number | null
  /** ⚠️ 這是**稅前口徑**的判定（跟著 `sample_count`）。畫面請用 `isLowSample(stat, basis)` */
  is_low_sample: boolean
  warnings?: string[]
}

export interface MatrixHotel {
  id: number
  name: string
  /**
   * 表格與標籤用的簡稱。⚠️ 後端已經處理過退回邏輯（沒填就是全名），
   * 所以這個欄位**永遠有值**，直接用即可。
   */
  short_name: string
  is_self: boolean
  hotel_code?: string
  room_count?: number | null
}

export interface MatrixResult {
  snapshot_date: string | null
  /**
   * 這批快照最後一次寫入的時間，`YYYY-MM-DD HH:MM:SS`。
   * ⚠️ 後端存的已經是**台灣時間**，前端**不可以再做時區換算**（會平白差 8 小時）。
   *    直接當字串印出來就好，不要餵給 dayjs 再 format。
   */
  fetched_at: string | null
  hotels: MatrixHotel[]
  stay_dates: string[]
  /** key 是 `${stay_date}|${hotel_id}` */
  cells: Record<string, RateCell>
  daily: Record<string, DailyStat>
  warnings: string[]
}

export interface TrendPoint extends RateCell {
  snapshot_date: string
}

export interface TrendResult {
  stay_date: string
  snapshot_dates: string[]
  hotels: MatrixHotel[]
  /** key 是 hotel_id */
  series: Record<number, TrendPoint[]>
  index_line: DailyStat[]
}

export interface DashboardResult {
  snapshot_date: string | null
  /** 最後更新時間（台灣時間字串，⚠️ 不可再做時區換算） */
  fetched_at: string | null
  today: DailyStat | null
  next_7d: DailyStat[]
  /** 競爭組對照表，用來把 `sold_out_hotel_ids` 換成看得懂的名字 */
  hotels: MatrixHotel[]
  sold_out_days?: number
  low_sample_days?: number
  warnings: string[]
  quota?: QuotaStatus
  subscriber?: SubscriberBrief
}

/**
 * 單筆快照的完整明細。
 *
 * ⚠️ 刻意 `Omit<RateCell, 'snapshot_id'>`：`/rates/detail` 回的是 **`id`**，
 *    沒有 `snapshot_id` 欄位。直接 extends 的話型別會宣告一個實際上永遠
 *    `undefined` 的欄位，而 TypeScript 會替它背書。
 */
export interface RateDetail extends Omit<RateCell, 'snapshot_id'> {
  id: number
  hotel: {
    id: number | null
    name: string
    is_self: boolean
    room_count: number | null
    registered_address: string
  }
  snapshot_date: string
  stay_date: string
  currency: string
  free_cancellation: boolean
  room_type_raw: string
  typical_low: number | null
  typical_high: number | null
  /** 精簡後的通路報價（`raw_json`）。日後做 rate parity 的原料。 */
  offers: Array<{
    source: string
    gross: number | null
    pretax: number | null
    num_guests: number | null
    free_cancellation: boolean
    official: boolean
  }>
  created_at: string | null
}

export interface FetchLogRow {
  id: number
  tier: string
  fetch_path: FetchPath
  started_at: string | null
  finished_at: string | null
  stay_date_from: string
  stay_date_to: string
  request_count: number
  row_count: number
  quota_before: number | null
  quota_after: number | null
  status: FetchStatus
  params: Record<string, unknown> | null
  /** ⚠️ 與 error_message 分開顯示：黃色 vs 紅色，不可混在一起 */
  warnings: string[]
  error_message: string
}

export interface CadenceEstimate {
  per_tier: Record<string, number>
  total: number
  monthly_quota: number
  usage_ratio: number | null
  over_quota: boolean
}

export interface SubscriberDetail {
  id: number
  code: string
  name: string
  plan_level: PlanLevel
  is_active: boolean
  location_query: string
  windows: { A: number; B: number; C: number }
  freqs: { A: number; B: number; C: number }
  params: {
    adults: number; nights: number
    gl: string; hl: string; currency: string
  }
  contact_name: string
  contact_email: string
  note: string
  quota: QuotaStatus
}

export interface CadenceResult {
  subscriber: SubscriberDetail
  estimate: CadenceEstimate
  /** ⚠️ 改擷取參數 ＝ 前後期價格不可比。畫面必須顯示出來再讓人確認。 */
  data_break_warning?: string | null
  over_quota_warning?: string | null
}

export interface ImportResult {
  total_rows: number
  inserted: number
  skipped: number
  warnings: string[]
  errors: string[]
}

export interface FetchRunResult {
  ok: boolean
  results: Array<{
    tier: string
    status: FetchStatus
    request_count: number
    row_count: number
    stay_date_from: string
    stay_date_to: string
    warnings: string[]
    error_message: string
  }>
  quota: QuotaStatus
}

export interface QuotaGrantRow {
  id: number
  granted_qty: number
  reason: string
  period_start: string
  granted_by_user_id: string
  granted_at: string | null
}
