/**
 * OPERA 營運分析 API 封裝
 * 所有對 /api/v1/opera/* 的請求統一在此處理（不在元件內直接用 axios）
 */
import apiClient from '@/api/client'
import type {
  AnalysisSetting,
  AnomalyResult,
  CheckoutTimeResult,
  CommitResult,
  DimensionResult,
  GuestMixResult,
  ImportBatch,
  ImportIssue,
  ImportStatus,
  LongStayResult,
  LosBucketResult,
  OooLossResult,
  OperaBasis,
  OperationsResult,
  OperaDashboard,
  OperaRecordType,
  OperaSourceType,
  OpportunityResult,
  QuadrantBasis,
  QuadrantResult,
  RawRowResult,
  RepeatGuestResult,
  RevenueDailyRow,
  RevenueKpi,
  RevenueMonthlyResult,
  RevenueYearRow,
  RoomUsageResult,
  SegmentResult,
  StayListResult,
  StayRow,
  StaySummaryResult,
  StayWeekdayResult,
  TrendResult,
  ValidateResult,
  WeekdayPerformanceResult,
  // ── 房價預測（2026-08-05）────────────────────────────────────────────────
  BacktestResult,
  CoefficientListResult,
  DateLookupResult,
  EventListResult,
  EventLearnResult,
  EventPayload,
  FitResult,
  ForecastResult,
  ForecastRun,
  OperaEventItem,
  PeriodLookupResult,
  RunCompareResult,
  ScenarioEvent,
} from '@/types/opera'

const IMPORT = '/opera/import'
const REVENUE = '/opera/revenue'
const GUEST = '/opera/guest'

export interface RangeParams {
  start?: string
  end?: string
  property_code?: string
}

// ══════════════════════════════════════════════════════════════════════════
// 匯入
// ══════════════════════════════════════════════════════════════════════════

export async function validateOperaFile(
  file: File,
  sourceType?: OperaSourceType,
): Promise<ValidateResult> {
  const form = new FormData()
  form.append('file', file)
  if (sourceType) form.append('source_type', sourceType)
  const res = await apiClient.post<ValidateResult>(`${IMPORT}/validate`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180_000,
  })
  return res.data
}

export async function commitOperaFile(
  file: File,
  opts: { sourceType?: OperaSourceType; sessionId?: string; allowWarnings?: boolean } = {},
): Promise<CommitResult> {
  const form = new FormData()
  form.append('file', file)
  if (opts.sourceType) form.append('source_type', opts.sourceType)
  if (opts.sessionId) form.append('session_id', opts.sessionId)
  form.append('allow_warnings', String(Boolean(opts.allowWarnings)))
  const res = await apiClient.post<CommitResult>(`${IMPORT}/commit`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 600_000,   // 3.5 萬列約需 10~60 秒，留足餘裕
  })
  return res.data
}

export async function fetchImportStatus(): Promise<ImportStatus> {
  const res = await apiClient.get<ImportStatus>(`${IMPORT}/status`)
  return res.data
}

export async function fetchBatches(params: {
  source_type?: string
  status?: string
  page?: number
  page_size?: number
} = {}): Promise<{ items: ImportBatch[]; total: number; page: number; page_size: number }> {
  const res = await apiClient.get(`${IMPORT}/batches`, { params })
  return res.data
}

export async function fetchBatch(batchId: number): Promise<ImportBatch> {
  const res = await apiClient.get<ImportBatch>(`${IMPORT}/batches/${batchId}`)
  return res.data
}

export async function fetchBatchErrors(
  batchId: number,
  params: { severity?: string; page?: number; page_size?: number } = {},
): Promise<{ items: ImportIssue[]; total: number; page: number; page_size: number }> {
  const res = await apiClient.get(`${IMPORT}/batches/${batchId}/errors`, { params })
  return res.data
}

export function batchErrorsCsvUrl(batchId: number): string {
  return `${apiClient.defaults.baseURL}${IMPORT}/batches/${batchId}/errors.csv`
}

/** 明細 Drawer 的「🔗 原始資料列」 */
export async function fetchRawRow(
  sourceType: OperaSourceType,
  rawId: number,
): Promise<RawRowResult> {
  const res = await apiClient.get<RawRowResult>(`${IMPORT}/raw/${sourceType}/${rawId}`)
  return res.data
}

// ══════════════════════════════════════════════════════════════════════════
// 營收（來源：History and Forecast）
// ══════════════════════════════════════════════════════════════════════════

export async function fetchOperaDashboard(
  params: { year?: number; property_code?: string } = {},
): Promise<OperaDashboard> {
  const res = await apiClient.get<OperaDashboard>(`${REVENUE}/dashboard`, { params })
  return res.data
}

export async function fetchRevenueKpi(
  params: RangeParams & { include_forecast?: boolean } = {},
): Promise<RevenueKpi> {
  const res = await apiClient.get<RevenueKpi>(`${REVENUE}/kpi`, { params })
  return res.data
}

export async function fetchRevenueDaily(
  params: RangeParams & { record_type?: OperaRecordType } = {},
): Promise<{ items: RevenueDailyRow[]; start: string; end: string; record_type: OperaRecordType; source_label: string }> {
  const res = await apiClient.get(`${REVENUE}/daily`, { params })
  return res.data
}

export async function fetchRevenueDayDetail(
  businessDate: string,
  params: { property_code?: string; record_type?: OperaRecordType } = {},
): Promise<RevenueDailyRow> {
  const res = await apiClient.get<RevenueDailyRow>(`${REVENUE}/daily/${businessDate}`, { params })
  return res.data
}

export async function fetchRevenueMonthly(
  year: number,
  propertyCode = '',
): Promise<RevenueMonthlyResult> {
  const res = await apiClient.get<RevenueMonthlyResult>(`${REVENUE}/monthly`, {
    params: { year, property_code: propertyCode },
  })
  return res.data
}

export async function fetchRevenueYearly(
  propertyCode = '',
): Promise<{ years: RevenueYearRow[]; source_label: string }> {
  const res = await apiClient.get(`${REVENUE}/yearly`, { params: { property_code: propertyCode } })
  return res.data
}

export async function fetchQuadrant(
  params: RangeParams & { basis?: QuadrantBasis } = {},
): Promise<QuadrantResult> {
  const res = await apiClient.get<QuadrantResult>(`${REVENUE}/quadrant`, { params })
  return res.data
}

export async function fetchAnomalies(params: RangeParams = {}): Promise<AnomalyResult> {
  const res = await apiClient.get<AnomalyResult>(`${REVENUE}/anomalies`, { params })
  return res.data
}

export async function fetchSegment(params: RangeParams = {}): Promise<SegmentResult> {
  const res = await apiClient.get<SegmentResult>(`${REVENUE}/segment`, { params })
  return res.data
}

/** 高住房率低 ADR 機會（含提升金額估算） */
export async function fetchOpportunity(params: RangeParams = {}): Promise<OpportunityResult> {
  const res = await apiClient.get<OpportunityResult>(`${REVENUE}/opportunity`, { params })
  return res.data
}

/** 星期營收績效（加權） */
export async function fetchWeekdayPerformance(
  params: RangeParams = {},
): Promise<WeekdayPerformanceResult> {
  const res = await apiClient.get<WeekdayPerformanceResult>(`${REVENUE}/weekday`, { params })
  return res.data
}

/** OOO 營收損失估算與雙分母 RevPAR */
export async function fetchOooLoss(params: RangeParams = {}): Promise<OooLossResult> {
  const res = await apiClient.get<OooLossResult>(`${REVENUE}/ooo-loss`, { params })
  return res.data
}

/** 月增率（MoM）與 7／28 日移動平均 */
export async function fetchTrend(params: RangeParams = {}): Promise<TrendResult> {
  const res = await apiClient.get<TrendResult>(`${REVENUE}/trend`, { params })
  return res.data
}

/** 退房時間分布 */
export async function fetchCheckoutTime(
  params: RangeParams & { basis?: OperaBasis } = {},
): Promise<CheckoutTimeResult> {
  const res = await apiClient.get<CheckoutTimeResult>(`${GUEST}/checkout-time`, { params })
  return res.data
}

/** 營運指標：每房人數、翻房率、每日進出、非營收房 */
export async function fetchOperations(params: RangeParams = {}): Promise<OperationsResult> {
  const res = await apiClient.get<OperationsResult>(`${REVENUE}/operations`, { params })
  return res.data
}

/** 房號使用分析（含疑似停用推論） */
export async function fetchRoomUsage(
  params: RangeParams & { basis?: OperaBasis; inactive_months?: number } = {},
): Promise<RoomUsageResult> {
  const res = await apiClient.get<RoomUsageResult>(`${GUEST}/room-usage`, { params })
  return res.data
}

/** 客群結構：每房人數分布與家庭客分析 */
export async function fetchGuestMix(
  params: RangeParams & { basis?: OperaBasis } = {},
): Promise<GuestMixResult> {
  const res = await apiClient.get<GuestMixResult>(`${GUEST}/guest-mix`, { params })
  return res.data
}

/** 入退房星期分布 */
export async function fetchStayWeekday(
  params: RangeParams & { basis?: OperaBasis } = {},
): Promise<StayWeekdayResult> {
  const res = await apiClient.get<StayWeekdayResult>(`${GUEST}/weekday`, { params })
  return res.data
}

// ══════════════════════════════════════════════════════════════════════════
// 住客與通路（來源：Departure All）
// ══════════════════════════════════════════════════════════════════════════

export interface StayQueryParams extends RangeParams {
  basis?: OperaBasis
  channel?: string
  room_category?: string
  rate_code?: string
  search?: string
  sort_field?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export async function fetchStays(params: StayQueryParams = {}): Promise<StayListResult> {
  const res = await apiClient.get<StayListResult>(`${GUEST}/stays`, { params })
  return res.data
}

export async function fetchStayDetail(stayId: number): Promise<StayRow> {
  const res = await apiClient.get<StayRow>(`${GUEST}/stays/${stayId}`)
  return res.data
}

export type OperaDimension =
  | 'channel' | 'room_category' | 'rate_code' | 'company' | 'payment' | 'group'

export interface DimensionParams extends RangeParams {
  basis?: OperaBasis
  limit?: number
  /** 只計住宿晚數 ≥ 此值（長住拆解用） */
  min_nights?: number
  /** 僅 dimension=group 有效：排除疑似個人訂房 */
  exclude_person?: boolean
}

export async function fetchDimensionStats(
  dimension: OperaDimension,
  params: DimensionParams = {},
): Promise<DimensionResult> {
  const res = await apiClient.get<DimensionResult>(`${GUEST}/dimension/${dimension}`, { params })
  return res.data
}

/** 住宿天數（LOS）分桶；桶界由「分析門檻設定」的長住門檻推導 */
export async function fetchLosBuckets(
  params: RangeParams & { basis?: OperaBasis } = {},
): Promise<LosBucketResult> {
  const res = await apiClient.get<LosBucketResult>(`${GUEST}/los-buckets`, { params })
  return res.data
}

export async function fetchRepeatGuests(
  params: RangeParams & { basis?: OperaBasis; limit?: number } = {},
): Promise<RepeatGuestResult> {
  const res = await apiClient.get<RepeatGuestResult>(`${GUEST}/repeat`, { params })
  return res.data
}

export async function fetchLongStay(
  params: RangeParams & { basis?: OperaBasis } = {},
): Promise<LongStayResult> {
  const res = await apiClient.get<LongStayResult>(`${GUEST}/long-stay`, { params })
  return res.data
}

export async function fetchStaySummary(params: RangeParams = {}): Promise<StaySummaryResult> {
  const res = await apiClient.get<StaySummaryResult>(`${GUEST}/summary`, { params })
  return res.data
}

export async function fetchGuestFilterOptions(
  params: RangeParams = {},
): Promise<{ channel: string[]; room_category: string[]; rate_code: string[]; start: string; end: string }> {
  const res = await apiClient.get(`${GUEST}/filter-options`, { params })
  return res.data
}

// ══════════════════════════════════════════════════════════════════════════
// 設定
// ══════════════════════════════════════════════════════════════════════════

export async function fetchAnalysisSettings(
  propertyCode = '',
): Promise<{ items: AnalysisSetting[] }> {
  const res = await apiClient.get(`${REVENUE}/settings`, { params: { property_code: propertyCode } })
  return res.data
}

export async function updateAnalysisSettings(
  settings: Record<string, number>,
  propertyCode = '',
): Promise<{ ok: boolean; changed: Array<{ key: string; before: number; after: number }>; items: AnalysisSetting[] }> {
  const res = await apiClient.put(`${REVENUE}/settings`, {
    property_code: propertyCode,
    settings,
  })
  return res.data
}

// ══════════════════════════════════════════════════════════════════════════
// 歷史同期查詢 / 房價預測 / 事件月曆（2026-08-05 新增）
// 評估文件：docs/EVAL_opera_rate_forecasting.md
// ══════════════════════════════════════════════════════════════════════════

const FORECAST = '/opera/forecast'

// ── 歷史同期查詢 ──────────────────────────────────────────────────────────

export async function fetchDateLookup(
  businessDate: string,
  propertyCode = '',
): Promise<DateLookupResult> {
  const res = await apiClient.get(`${FORECAST}/lookup/date/${businessDate}`, {
    params: { property_code: propertyCode },
  })
  return res.data
}

export async function fetchPeriodLookup(
  start: string,
  end: string,
  propertyCode = '',
): Promise<PeriodLookupResult> {
  const res = await apiClient.get(`${FORECAST}/lookup/period`, {
    params: { start, end, property_code: propertyCode },
  })
  return res.data
}

// ── 模型係數 ──────────────────────────────────────────────────────────────

export async function fetchCoefficients(propertyCode = ''): Promise<CoefficientListResult> {
  const res = await apiClient.get(`${FORECAST}/coefficients`, {
    params: { property_code: propertyCode },
  })
  return res.data
}

export async function fitCoefficients(propertyCode = ''): Promise<FitResult> {
  const res = await apiClient.post(`${FORECAST}/coefficients/fit`, null, {
    params: { property_code: propertyCode },
  })
  return res.data
}

export async function updateCoefficients(
  items: Array<{ id: number; value?: number; is_manual: boolean }>,
  propertyCode = '',
): Promise<CoefficientListResult & { changed: unknown[] }> {
  const res = await apiClient.put(`${FORECAST}/coefficients`, {
    property_code: propertyCode,
    items,
  })
  return res.data
}

// ── 預測 ──────────────────────────────────────────────────────────────────

export async function fetchForecast(
  start: string,
  end?: string,
  propertyCode = '',
): Promise<ForecastResult> {
  const res = await apiClient.get(`${FORECAST}/predict`, {
    params: { start, end, property_code: propertyCode },
  })
  return res.data
}

export async function runForecastScenario(payload: {
  start: string
  end: string
  property_code?: string
  events?: ScenarioEvent[]
  save?: boolean
  note?: string
}): Promise<ForecastResult> {
  const res = await apiClient.post(`${FORECAST}/predict`, payload)
  return res.data
}

export async function fetchBacktest(
  propertyCode = '',
  testDays = 365,
): Promise<BacktestResult> {
  const res = await apiClient.get(`${FORECAST}/backtest`, {
    params: { property_code: propertyCode, test_days: testDays },
  })
  return res.data
}

// ── 預測快照 ──────────────────────────────────────────────────────────────

export async function fetchForecastRuns(
  propertyCode = '',
  limit = 50,
): Promise<{ items: ForecastRun[]; total: number }> {
  const res = await apiClient.get(`${FORECAST}/runs`, {
    params: { property_code: propertyCode, limit },
  })
  return res.data
}

export async function compareForecastRuns(propertyCode = ''): Promise<RunCompareResult> {
  const res = await apiClient.post(`${FORECAST}/runs/compare`, null, {
    params: { property_code: propertyCode },
  })
  return res.data
}

// ── 事件月曆 ──────────────────────────────────────────────────────────────

export async function fetchEvents(params: {
  property_code?: string
  start?: string
  end?: string
  include_inactive?: boolean
} = {}): Promise<EventListResult> {
  const res = await apiClient.get(`${FORECAST}/events`, { params })
  return res.data
}

export async function createEvent(payload: EventPayload): Promise<{ ok: boolean; item: OperaEventItem }> {
  const res = await apiClient.post(`${FORECAST}/events`, payload)
  return res.data
}

export async function updateEvent(
  eventId: number,
  payload: EventPayload,
): Promise<{ ok: boolean; item: OperaEventItem }> {
  const res = await apiClient.put(`${FORECAST}/events/${eventId}`, payload)
  return res.data
}

export async function deleteEvent(eventId: number): Promise<{ ok: boolean; deleted_id: number }> {
  const res = await apiClient.delete(`${FORECAST}/events/${eventId}`)
  return res.data
}

export async function learnEventCoefficients(propertyCode = ''): Promise<EventLearnResult> {
  const res = await apiClient.post(`${FORECAST}/events/learn`, null, {
    params: { property_code: propertyCode },
  })
  return res.data
}
