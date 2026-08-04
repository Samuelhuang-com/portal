/**
 * OPERA 營運分析 API 封裝
 * 所有對 /api/v1/opera/* 的請求統一在此處理（不在元件內直接用 axios）
 */
import apiClient from '@/api/client'
import type {
  AnalysisSetting,
  AnomalyResult,
  CommitResult,
  DimensionResult,
  ImportBatch,
  ImportIssue,
  ImportStatus,
  LongStayResult,
  OperaBasis,
  OperaDashboard,
  OperaRecordType,
  OperaSourceType,
  QuadrantBasis,
  QuadrantResult,
  RawRowResult,
  RepeatGuestResult,
  RevenueDailyRow,
  RevenueKpi,
  RevenueMonthlyResult,
  RevenueYearRow,
  SegmentResult,
  StayListResult,
  StayRow,
  StaySummaryResult,
  ValidateResult,
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

export type OperaDimension = 'channel' | 'room_category' | 'rate_code' | 'company' | 'payment'

export async function fetchDimensionStats(
  dimension: OperaDimension,
  params: RangeParams & { basis?: OperaBasis; limit?: number } = {},
): Promise<DimensionResult> {
  const res = await apiClient.get<DimensionResult>(`${GUEST}/dimension/${dimension}`, { params })
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
