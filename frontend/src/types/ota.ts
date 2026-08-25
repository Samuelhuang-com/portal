/**
 * OTA 口碑分析 — TypeScript 型別
 *
 * 對應後端 `backend/app/schemas/ota_review.py`
 * 規格書：`docs/SPEC_ota_reviews.md`
 *
 * ⚠️ 分數有三個欄位，用途不同，不要混用：
 *    - `score_raw`   各站原始分數（Booking 8.5、Tripadvisor 4.5）
 *    - `score_scale` 該筆的分制（10 或 5）
 *    - `score_10`    統一 10 分制 —— **所有統計、篩選、圖表一律用這個**
 */

export type OtaPlatform = 'booking' | 'expedia' | 'tripadvisor' | 'agoda' | 'google'
export type SyncStatus =
  | 'never' | 'running' | 'success' | 'partial' | 'captcha' | 'failed'
  /** 此平台尚無自動擷取器 —— 是設定事實不是錯誤，不可畫成紅色 */
  | 'unsupported'
export type AlertStatus = 'open' | 'acknowledged' | 'resolved' | 'ignored'
export type Sentiment = 'positive' | 'neutral' | 'negative'
export type Polarity = 'negative' | 'positive' | 'neutral'

// ══════════════════════════════════════════════════════════════════
// 來源設定
// ══════════════════════════════════════════════════════════════════
export interface OtaSourceInput {
  hotel_code: string
  hotel_name: string
  platform: OtaPlatform
  url: string
  score_scale: number
  is_enabled: boolean
  max_pages: number
  sort_order: number
}

export interface OtaSource extends OtaSourceInput {
  id: number
  overall_score: number | null
  overall_score_10: number | null
  review_count_site: number | null
  last_sync_at: string
  last_status: SyncStatus
  last_message: string
  /** 實際落地筆數（不含跨站重複）。與 review_count_site 差距大＝翻頁沒抓完 */
  stored_count: number
}

export interface PlatformOption {
  value: OtaPlatform
  label: string
  score_scale: number
  /** 是否有自動擷取器。false 代表只能用 CSV／HTML 檔匯入 */
  has_parser: boolean
}

export interface HotelOption {
  value: string
  label: string
}

// ══════════════════════════════════════════════════════════════════
// 評論
// ══════════════════════════════════════════════════════════════════
export interface OtaReviewRow {
  id: number
  hotel_code: string
  hotel_name: string
  platform: string
  platform_label: string
  author: string
  score_raw: number | null
  score_scale: number
  score_10: number | null
  summary: string
  review_date: string
  sentiment_label: string
  topics: string[]
  is_alert: boolean
  alert_status: string
  is_duplicate: boolean
}

export interface OtaReviewList {
  rows: OtaReviewRow[]
  total: number
  page: number
  page_size: number
}

export interface OtaReviewDetail {
  id: number
  hotel_code: string
  hotel_name: string
  platform: string
  platform_label: string
  /** §7 Drawer 規範中 `ragic_url` 的等價替代（本模組沒有 Ragic） */
  review_url: string
  author: string
  score_raw: number | null
  score_scale: number
  score_10: number | null
  title: string
  positive_text: string
  negative_text: string
  comment: string
  review_date: string
  stay_month: string
  sentiment_label: string
  sentiment_score: number | null
  sentiment_engine: string
  topics: string[]
  is_alert: boolean
  alert_status: string
  alert_note: string
  is_duplicate: boolean
  fetched_at: string
  /** 中文欄位名稱為 key，Drawer 逐項渲染 */
  detail: Record<string, string>
}

export interface ReviewFilters {
  hotel_code?: string
  platform?: string
  start?: string
  end?: string
  min_score?: number
  max_score?: number
  sentiment?: string
  topic?: string
  keyword?: string
  /** 只看分數**低於**此值的（不含等於）。帶 6 時與 Dashboard 的「負面評論」
   *  KPI 同條件。⚠️ 不要改用 `max_score`（那是 `<=`，會多含剛好等於門檻的） */
  score_below?: number
  alert_only?: boolean
  alert_status?: string
  include_duplicate?: boolean
  page?: number
  page_size?: number
}

// ══════════════════════════════════════════════════════════════════
// 統計
// ══════════════════════════════════════════════════════════════════
export interface DataRange {
  start: string
  /** ⚠️ StandardRangePicker 的 anchor 必須用這個值，不可用 dayjs() */
  end: string
  total: number
}

export interface OtaOverview {
  total: number
  avg_score_10: number | null
  negative_count: number
  alert_open_count: number
  this_month_count: number
  last_month_count: number
  this_month_avg: number | null
  last_month_avg: number | null
}

export interface MonthlyPoint {
  review_month: string
  hotel_code: string
  hotel_name: string
  avg_score_10: number | null
  count: number
  /** ⚠️ 與 Dashboard KPI 是同一組條件算出來的，數字要對得起來 */
  negative_count: number
  alert_open_count: number
}

export interface PlatformStat {
  platform: string
  platform_label: string
  hotel_code: string
  avg_score_10: number | null
  count: number
}

/**
 * 警示積壓分桶的一格（2026-08-25）。
 *
 * `min_days` / `max_days` 是用來把「點這根柱子」換算成日期區間的：
 * 積壓 N 天 ⇔ `review_date` 落在 `[今天-max, 今天-min]`。
 * 所以點擊篩選**沿用既有的 start／end 參數**，後端清單 API 一行都不用改。
 */
export interface AlertAgingBucket {
  key: string
  label: string
  count: number
  min_days: number | null
  /** null ＝ 最後一桶，沒有上限 */
  max_days: number | null
  is_overdue: boolean
}

export interface AlertAgingResult {
  buckets: AlertAgingBucket[]
  /** 分得出桶的總數（**不含** unknown） */
  total: number
  /**
   * ⚠️ 日期解析不出來、無法計算積壓的件數。
   * **畫面上必須講出來** —— 否則 sum(buckets) 小於待處理總數，
   * 看起來像圖表算錯。
   */
  unknown_count: number
  /** 起算基準日（今天）。⚠️ 不是「資料最後一天」，理由見後端註解 */
  as_of: string
}

export interface TopicStat {
  topic: string
  negative_count: number
  positive_count: number
  total_count: number
}

// ══════════════════════════════════════════════════════════════════
// 同步與匯入
// ══════════════════════════════════════════════════════════════════
export interface SyncLog {
  id: number
  source_id: number
  hotel_name: string
  platform_label: string
  trigger_type: string
  started_at: string
  completed_at: string
  status: string
  pages_fetched: number
  found_count: number
  inserted_count: number
  updated_count: number
  skipped_count: number
  /** ⚠️ 這是「某幾筆略過」，不是失敗。畫面上不要畫成紅色 */
  warnings: string[]
  /** ⚠️ 只有整個來源失敗才有值 */
  error_message: string
  duration_ms: number | null
}

export interface SyncStatusInfo {
  is_running: boolean
  running_source_ids: number[]
  /** 爬蟲是否可用。false 時不顯示「立即同步」按鈕 */
  scraper_available: boolean
  /** 已實作擷取器的平台（P2 只有 booking）。其餘平台的來源要用 CSV 匯入 */
  supported_platforms: string[]
  /** auto / headless / visible —— 規格書 §3.3 R1 的開關 */
  browser_mode: string
  note: string
  /**
   * 這次查詢順手回收掉的孤兒 running（2026-08-24）。
   *
   * 後端每次回狀態前會先收「pid 已不在」或「超過 90 分鐘」的紀錄。
   * 有值代表剛剛幫你解開了一個卡死 —— 要講出來，不要讓狀態默默變了。
   */
  reaped?: { log_id: number; source_id: number; reason: string }[]
}

export interface ForceUnlockResult {
  reaped: number
  details: { log_id: number; source_id: number }[]
  message: string
}

export interface SyncRunResult {
  started: boolean
  message: string
}

export interface ImportResult {
  total_rows: number
  inserted: number
  updated: number
  skipped: number
  marked_duplicate: number
  warnings: string[]
  errors: string[]
}

// ══════════════════════════════════════════════════════════════════
// 主題字典
// ══════════════════════════════════════════════════════════════════
export interface TopicRule {
  id: number
  topic: string
  keyword: string
  polarity: Polarity
  weight: number
  is_enabled: boolean
  /** 內建詞不可刪除，只能停用 */
  is_builtin: boolean
}

/**
 * AI 發現的、不在我們 12 個主題清單裡的議題候選。
 *
 * 閉環：AI 發現 → 候選累積 → 管理員確認 → 進字典 → 規則層免費抓到
 * （之後同樣的評論不必再送 AI）
 *
 * ⚠️ `sample_review_ids` 是評論 id 不是文字 —— 要看內容請用 id 回查，
 *    後端刻意不複製評論文字（著作權不屬於我們）。
 */
export interface TopicCandidate {
  id: number
  name: string
  description: string
  keywords: string[]
  hit_count: number
  neg_count: number
  sample_review_ids: number[]
  status: 'pending' | 'accepted' | 'rejected'
  first_seen_at: string
  last_seen_at: string
}

/**
 * OTA 平台。2026-08-23 從寫死的五個常數改為資料驅動 ——
 * 使用者可以自己新增 Hotels.com、Trip.com、KKday……
 *
 * ⚠️ `has_parser` 是後端**現算**的（看 `ota_parser.PARSERS`），不存 DB。
 *    沒有擷取器不代表不能用 —— 資料可以走 CSV／HTML 匯入，
 *    Tripadvisor 與 Expedia 現在就是這樣（站方擋自動存取）。
 *
 * ⚠️ `code` 建立後**不可修改** —— 它是既有評論的 platform 欄位值與統計分組鍵。
 */
export interface OtaPlatformRow {
  id: number
  code: string
  label: string
  score_scale: number
  domains: string
  note: string
  is_enabled: boolean
  is_builtin: boolean
  sort_order: number
  has_parser: boolean
}

export interface OtaPlatformInput {
  code?: string
  label: string
  score_scale: number
  domains: string
  note: string
  is_enabled: boolean
}
