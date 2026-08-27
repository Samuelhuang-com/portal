/**
 * OTA 口碑分析 API 封裝
 * 所有對 /api/v1/ota/* 的請求統一在此處理（不在元件內直接用 axios）
 *
 * 規格書：`docs/SPEC_ota_reviews.md` §8
 */
import apiClient from '@/api/client'
import type {
  DataRange, HotelOption, ImportResult, MonthlyPoint, OtaOverview,
  OtaReviewDetail, OtaReviewList, OtaSource, OtaSourceInput, PlatformOption,
  PlatformStat, ReviewFilters, SyncLog, SyncRunResult, SyncStatusInfo, TopicRule,
  OtaPlatformInput, OtaPlatformRow, TopicCandidate, TopicStat,
  ForceUnlockResult, AlertAgingResult, ScoreDistributionResult,
  AlertDailyResult, TopicRotationBasis, TopicRotationResult,
} from '@/types/ota'

const REVIEWS = '/ota/reviews'
const STATS = '/ota/stats'
const ADMIN = '/ota/admin'

/**
 * `toParams` 的輸入：既有的 `ReviewFilters`，或任意鍵值物件
 * （同步紀錄那類參數不在 `ReviewFilters` 裡）。
 *
 * ⚠️ 不可只寫成 `Record<string, unknown>` —— TypeScript 的 **interface 沒有
 *    索引簽章，不能指派給 `Record<string, unknown>`**（type alias 可以，
 *    interface 不行），`ReviewFilters` 是 interface，全部呼叫端都會 TS2345。
 *
 * ⚠️ 也不要反過來給 `ReviewFilters` 加 `[key: string]: unknown` ——
 *    那會讓打錯的欄位名不再被編譯器攔下來，代價比這個 union 大得多。
 */
type ParamInput = ReviewFilters | Record<string, unknown>

/**
 * 把篩選條件轉成 query params。
 *
 * ⚠️ 空字串與 undefined 一律不帶 —— 後端把「沒帶 start/end」視為「全部資料」
 *    （StandardRangePicker 選「全部」時 onChange 收到 null，呼叫端不帶起迄）。
 */
function toParams(filters: ParamInput = {}): Record<string, unknown> {
  const params: Record<string, unknown> = {}
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (value === false && key !== 'alert_only' && key !== 'include_duplicate') return
    params[key] = value
  })
  return params
}

// ══════════════════════════════════════════════════════════════════
// 評論
// ══════════════════════════════════════════════════════════════════
export async function fetchReviews(filters: ReviewFilters = {}): Promise<OtaReviewList> {
  const res = await apiClient.get<OtaReviewList>(REVIEWS, { params: toParams(filters) })
  return res.data
}

export async function fetchReviewDetail(reviewId: number): Promise<OtaReviewDetail> {
  const res = await apiClient.get<OtaReviewDetail>(`${REVIEWS}/${reviewId}`)
  return res.data
}

export async function updateAlert(
  reviewId: number,
  payload: { alert_status: string; alert_note: string },
): Promise<OtaReviewDetail> {
  const res = await apiClient.patch<OtaReviewDetail>(`${REVIEWS}/${reviewId}/alert`, payload)
  return res.data
}

/** 匯出 Excel（沿用目前篩選條件）。回傳 Blob 由呼叫端觸發下載。 */
export async function exportReviews(filters: ReviewFilters = {}): Promise<Blob> {
  const res = await apiClient.get(`${REVIEWS}/export`, {
    params: toParams(filters),
    responseType: 'blob',
  })
  return res.data as Blob
}

export async function downloadImportTemplate(): Promise<Blob> {
  const res = await apiClient.get(`${REVIEWS}/import/template`, { responseType: 'blob' })
  return res.data as Blob
}

/** CSV 備援匯入（爬蟲失效時的資料入口，規格書 §6.6） */
export async function importReviewsCsv(file: File): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await apiClient.post<ImportResult>(`${REVIEWS}/import/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,   // 大檔匯入可能超過預設 30 秒
  })
  return res.data
}

// ══════════════════════════════════════════════════════════════════
// 統計
// ══════════════════════════════════════════════════════════════════
/**
 * ⚠️ 回傳的 `end` 就是 `StandardRangePicker` 的 `anchor`。
 *    絕對不要改用 `dayjs()` —— OTA 評論落後現實好幾天，
 *    以今天為基準的「本月」會選到一片空白（CLAUDE.md §8.2）。
 */
export async function fetchDataRange(hotelCode = ''): Promise<DataRange> {
  const res = await apiClient.get<DataRange>(`${STATS}/data-range`, {
    params: toParams({ hotel_code: hotelCode }),
  })
  return res.data
}

export async function fetchOverview(filters: ReviewFilters = {}): Promise<OtaOverview> {
  const res = await apiClient.get<OtaOverview>(`${STATS}/overview`, { params: toParams(filters) })
  return res.data
}

export async function fetchMonthly(filters: ReviewFilters = {}): Promise<MonthlyPoint[]> {
  const res = await apiClient.get<MonthlyPoint[]>(`${STATS}/monthly`, { params: toParams(filters) })
  return res.data
}

export async function fetchPlatformStats(filters: ReviewFilters = {}): Promise<PlatformStat[]> {
  const res = await apiClient.get<PlatformStat[]>(`${STATS}/platform`, { params: toParams(filters) })
  return res.data
}

export async function fetchTopicStats(filters: ReviewFilters = {}): Promise<TopicStat[]> {
  const res = await apiClient.get<TopicStat[]>(`${STATS}/topics`, { params: toParams(filters) })
  return res.data
}

/**
 * 主題輪動（月 × 主題）。
 *
 * ⚠️ `basis` 預設 `negative` —— 這張圖是拿來找問題的。切成 `all` 之後
 *    名次會被常態被稱讚的主題（早餐、服務）洗掉，負面訊號反而看不見。
 */
export async function fetchTopicRotation(
  filters: ReviewFilters = {},
  opts: { basis?: TopicRotationBasis; top_n?: number } = {},
): Promise<TopicRotationResult> {
  const res = await apiClient.get<TopicRotationResult>(`${STATS}/topic-rotation`, {
    params: { ...toParams(filters), ...opts },
  })
  return res.data
}

export async function fetchAlerts(filters: ReviewFilters = {}): Promise<OtaReviewList> {
  const res = await apiClient.get<OtaReviewList>(`${STATS}/alerts`, { params: toParams(filters) })
  return res.data
}

export async function fetchHotelOptions(): Promise<HotelOption[]> {
  const res = await apiClient.get<HotelOption[]>(`${STATS}/hotels`)
  return res.data
}

// ══════════════════════════════════════════════════════════════════
// 來源設定
// ══════════════════════════════════════════════════════════════════
export async function fetchSources(enabledOnly = false): Promise<OtaSource[]> {
  const res = await apiClient.get<OtaSource[]>(`${ADMIN}/sources`, {
    params: enabledOnly ? { enabled_only: true } : {},
  })
  return res.data
}

export async function fetchPlatformOptions(): Promise<PlatformOption[]> {
  const res = await apiClient.get<PlatformOption[]>(`${ADMIN}/sources/platforms`)
  return res.data
}

export async function createSource(payload: OtaSourceInput): Promise<OtaSource> {
  const res = await apiClient.post<OtaSource>(`${ADMIN}/sources`, payload)
  return res.data
}

export async function updateSource(id: number, payload: OtaSourceInput): Promise<OtaSource> {
  const res = await apiClient.put<OtaSource>(`${ADMIN}/sources/${id}`, payload)
  return res.data
}

export async function toggleSource(id: number): Promise<OtaSource> {
  const res = await apiClient.post<OtaSource>(`${ADMIN}/sources/${id}/toggle`)
  return res.data
}

/** ⚠️ 底下還有評論時後端會拒絕（FK RESTRICT）。要停止同步請用 toggleSource。 */
export async function deleteSource(id: number): Promise<void> {
  await apiClient.delete(`${ADMIN}/sources/${id}`)
}

// ══════════════════════════════════════════════════════════════════
// 同步紀錄
// ══════════════════════════════════════════════════════════════════
export async function fetchSyncLogs(sourceId?: number, limit = 50): Promise<SyncLog[]> {
  const res = await apiClient.get<SyncLog[]>(`${ADMIN}/sync/logs`, {
    params: toParams({ ...(sourceId ? { source_id: sourceId } : {}), limit }),
  })
  return res.data
}

/**
 * 手動觸發擷取。
 *
 * ⚠️ **立即回傳，實際擷取在背景跑**（翻 20 頁可能要好幾分鐘）。
 *    呼叫端請輪詢 fetchSyncStatus() 與 fetchSyncLogs() 看結果，
 *    不要等這個 Promise 拿到最終數字。
 *
 * 已有同步在跑時後端回 409。
 */
export async function runSync(sourceIds: number[] = []): Promise<SyncRunResult> {
  const res = await apiClient.post<SyncRunResult>(`${ADMIN}/sync/run`, {
    source_ids: sourceIds,
    force: true,
  })
  return res.data
}

/**
 * 分數分布（清單頁上方的橫條）。
 *
 * ⚠️ **參數必須與清單完全一致**（含 `include_duplicate`），
 *    否則會出現「圖上寫 12、點下去只有 9 筆」。
 * ⚠️ 但**不要傳分數篩選** —— 這張圖是給人選分數區間的，
 *    自己先被分數篩過就只剩一根柱子。
 */
export async function fetchScoreDistribution(
  params: {
    hotel_code?: string; platform?: string
    start?: string; end?: string; include_duplicate?: boolean
  } = {},
): Promise<ScoreDistributionResult> {
  const res = await apiClient.get<ScoreDistributionResult>(
    `${STATS}/score-distribution`, { params: toParams(params) })
  return res.data
}

/**
 * 最近 N 天每天發生幾件警示（2026-08-25）。
 *
 * ⚠️ **與 `fetchAlertAging` 口徑不同**：這支算「當天發生」，
 *    那支算「還沒處理的存量」。兩者都對，但畫面上要講清楚。
 */
export async function fetchAlertDaily(
  params: { hotel_code?: string; platform?: string; days?: number } = {},
): Promise<AlertDailyResult> {
  const res = await apiClient.get<AlertDailyResult>(`${STATS}/alert-daily`,
    { params: toParams(params) })
  return res.data
}

/**
 * 待處理警示的積壓天數分桶（2026-08-25）。
 *
 * ⚠️ 刻意**不吃 start／end** —— 積壓是相對於「現在」的，
 *    加期間篩選會變成另一個問題，而且很容易被誤讀。
 */
export async function fetchAlertAging(
  params: { hotel_code?: string; platform?: string } = {},
): Promise<AlertAgingResult> {
  const res = await apiClient.get<AlertAgingResult>(`${STATS}/alert-aging`,
    { params: toParams(params) })
  return res.data
}

export async function fetchSyncStatus(): Promise<SyncStatusInfo> {
  const res = await apiClient.get<SyncStatusInfo>(`${ADMIN}/sync/status`)
  return res.data
}

/**
 * 強制解除卡住的「擷取中」（2026-08-24）。
 *
 * ⚠️ 這是**最後一道保險**，不是日常操作。`/sync/status` 與 `/sync/run`
 *    已經會自動回收「pid 已不在」與「超過 90 分鐘」兩種孤兒紀錄；
 *    會需要按這個，是那兩層都判不出來的情況（同步跑在另一台機器、
 *    或還沒超過門檻但人已經知道它死了）。
 *
 * 背景：`status='running'` 一寫進 DB 就 commit，收尾卻只在 except Exception 裡 ——
 * Ctrl-C 是 BaseException，攔不到。剩下的孤兒會讓 runSync() 永遠回 409。
 */
export async function forceUnlockSync(): Promise<ForceUnlockResult> {
  const res = await apiClient.post<ForceUnlockResult>(`${ADMIN}/sync/force-unlock`)
  return res.data
}

// ══════════════════════════════════════════════════════════════════
// 主題字典
// ══════════════════════════════════════════════════════════════════
/**
 * 觸發情緒與主題分析。
 *
 * ⚠️ **背景執行、立即回傳**（`rerun_all` 重跑上千則時可能要幾分鐘）。
 * ⚠️ 重跑**不會**覆蓋人工填的警示處理狀態，只重算 `is_alert`。
 */
export async function runAnalyze(rerunAll = false, limit = 2000): Promise<SyncRunResult> {
  const res = await apiClient.post<SyncRunResult>(`${ADMIN}/analyze/run`, {
    rerun_all: rerunAll,
    limit,
  })
  return res.data
}

export async function fetchTopicRules(topic = ''): Promise<TopicRule[]> {
  const res = await apiClient.get<TopicRule[]>(`${ADMIN}/topic-rules`, {
    params: topic ? { topic } : {},
  })
  return res.data
}

export async function createTopicRule(payload: {
  topic: string; keyword: string; polarity: string; weight: number; is_enabled: boolean
}): Promise<TopicRule> {
  const res = await apiClient.post<TopicRule>(`${ADMIN}/topic-rules`, payload)
  return res.data
}

export async function updateTopicRule(
  id: number,
  payload: { weight?: number; is_enabled?: boolean; polarity?: string },
): Promise<TopicRule> {
  const res = await apiClient.put<TopicRule>(`${ADMIN}/topic-rules/${id}`, payload)
  return res.data
}

export async function deleteTopicRule(id: number): Promise<void> {
  await apiClient.delete(`${ADMIN}/topic-rules/${id}`)
}

// ══════════════════════════════════════════════════════════════════
// AI 發現的字典外主題候選（2026-08-23）
// ══════════════════════════════════════════════════════════════════
export async function fetchTopicCandidates(
  status: 'pending' | 'accepted' | 'rejected' | 'all' = 'pending',
): Promise<TopicCandidate[]> {
  const res = await apiClient.get<TopicCandidate[]>(`${ADMIN}/topic-candidates`, {
    params: { status },
  })
  return res.data
}

/**
 * 採納候選 → 寫進主題字典。
 *
 * ⚠️ topic 與 keywords 都可以改再送 —— AI 給的名字未必是我們想在圖表圖例上
 *    看到的（它可能寫「電梯設備」，我們想要「電梯」）。採納後改名成本很高。
 */
export async function acceptTopicCandidate(
  id: number,
  payload: { topic: string; keywords: string[]; polarity: string },
): Promise<{ ok: boolean; added: number; topic: string }> {
  const res = await apiClient.post(`${ADMIN}/topic-candidates/${id}/accept`, payload)
  return res.data
}

/** ⚠️ 否決之後不會再跳出來（後端不復活 rejected），要反悔得改回 pending。 */
export async function rejectTopicCandidate(id: number): Promise<void> {
  await apiClient.post(`${ADMIN}/topic-candidates/${id}/reject`)
}

// ══════════════════════════════════════════════════════════════════
// 平台維護（2026-08-23 平台改為資料驅動）
// ══════════════════════════════════════════════════════════════════
export async function fetchPlatforms(): Promise<OtaPlatformRow[]> {
  const res = await apiClient.get<OtaPlatformRow[]>(`${ADMIN}/platforms`)
  return res.data
}

export async function createPlatform(payload: OtaPlatformInput): Promise<OtaPlatformRow> {
  const res = await apiClient.post<OtaPlatformRow>(`${ADMIN}/platforms`, payload)
  return res.data
}

/** ⚠️ `code` 不會被更新 —— 它是既有評論的 platform 值與統計分組鍵。 */
export async function updatePlatform(
  id: number, payload: OtaPlatformInput,
): Promise<OtaPlatformRow> {
  const res = await apiClient.put<OtaPlatformRow>(`${ADMIN}/platforms/${id}`, payload)
  return res.data
}

export async function deletePlatform(id: number): Promise<void> {
  await apiClient.delete(`${ADMIN}/platforms/${id}`)
}

// ══════════════════════════════════════════════════════════════════
// 共用小工具
// ══════════════════════════════════════════════════════════════════
/** 觸發瀏覽器下載 Blob */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
