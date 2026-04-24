/**
 * 樂群工務報修 API 封裝
 * 所有對 /api/v1/luqun-repair/* 的請求統一在此處理
 */
import apiClient from '@/api/client'
import type {
  DashboardData,
  RepairStatsData,
  ClosingTimeData,
  TypeStatsData,
  RoomRepairTableData,
  DetailQueryParams,
  DetailResult,
  FilterOptions,
  FeeStatsData,
} from '@/types/luqunRepair'

const BASE = '/luqun-repair'

// ── 年份清單 ──────────────────────────────────────────────────────────────────
export async function fetchYears(): Promise<{ years: number[] }> {
  const res = await apiClient.get(`${BASE}/years`)
  return res.data
}

// ── 過濾條件選項 ───────────────────────────────────────────────────────────────
export async function fetchFilterOptions(): Promise<FilterOptions> {
  const res = await apiClient.get<FilterOptions>(`${BASE}/filter-options`)
  return res.data
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export async function fetchDashboard(year: number, month = 0): Promise<DashboardData> {
  const res = await apiClient.get<DashboardData>(`${BASE}/dashboard`, {
    params: { year, month },
  })
  return res.data
}

// ── 4.1 報修統計 ──────────────────────────────────────────────────────────────
export async function fetchRepairStats(year: number): Promise<RepairStatsData> {
  const res = await apiClient.get<RepairStatsData>(`${BASE}/stats/repair`, {
    params: { year },
  })
  return res.data
}

// ── 4.2 結案時間統計 ───────────────────────────────────────────────────────────
export async function fetchClosingStats(year: number, month?: number): Promise<ClosingTimeData> {
  const params: Record<string, number> = { year }
  if (month !== undefined) params.month = month
  const res = await apiClient.get<ClosingTimeData>(`${BASE}/stats/closing`, { params })
  return res.data
}

// ── 4.3 報修類型統計 ───────────────────────────────────────────────────────────
export async function fetchTypeStats(year: number, month?: number): Promise<TypeStatsData> {
  const params: Record<string, number> = { year }
  if (month !== undefined) params.month = month
  const res = await apiClient.get<TypeStatsData>(`${BASE}/stats/type`, { params })
  return res.data
}

// ── 金額統計 ──────────────────────────────────────────────────────────────────
export async function fetchFeeStats(year: number): Promise<FeeStatsData> {
  const res = await apiClient.get<FeeStatsData>(`${BASE}/stats/fee`, { params: { year } })
  return res.data
}

// ── 4.4 客房報修表 ────────────────────────────────────────────────────────────
export async function fetchRoomRepairTable(year: number, month: number): Promise<RoomRepairTableData> {
  const res = await apiClient.get<RoomRepairTableData>(`${BASE}/stats/room`, {
    params: { year, month },
  })
  return res.data
}

// ── 明細清單 ──────────────────────────────────────────────────────────────────
export async function fetchDetail(params: DetailQueryParams): Promise<DetailResult> {
  const p: Record<string, unknown> = {}
  if (params.year        !== undefined) p.year        = params.year
  if (params.month       !== undefined) p.month       = params.month
  if (params.repair_type !== undefined) p.repair_type = params.repair_type
  if (params.floor       !== undefined) p.floor       = params.floor
  if (params.status      !== undefined) p.status      = params.status
  if (params.keyword     !== undefined) p.keyword     = params.keyword
  if (params.page        !== undefined) p.page        = params.page
  if (params.page_size   !== undefined) p.page_size   = params.page_size
  if (params.sort_by     !== undefined) p.sort_by     = params.sort_by
  if (params.sort_desc   !== undefined) p.sort_desc   = params.sort_desc

  const res = await apiClient.get<DetailResult>(`${BASE}/detail`, { params: p })
  return res.data
}

// ── 匯出 Excel ────────────────────────────────────────────────────────────────
export function buildExportUrl(params: {
  year?: number; month?: number; repair_type?: string;
  floor?: string; status?: string; keyword?: string;
}): string {
  const apiBase = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
  const query = new URLSearchParams()
  if (params.year        !== undefined) query.set('year',        String(params.year))
  if (params.month       !== undefined) query.set('month',       String(params.month))
  if (params.repair_type !== undefined) query.set('repair_type', params.repair_type)
  if (params.floor       !== undefined) query.set('floor',       params.floor)
  if (params.status      !== undefined) query.set('status',      params.status)
  if (params.keyword     !== undefined) query.set('keyword',     params.keyword)

  // attach token
  const token = localStorage.getItem('access_token')
  if (token) query.set('token', token)

  return `${apiBase}/luqun-repair/export?${query.toString()}`
}

// ── Ragic 欄位 debug ─────────────────────────────────────────────────────────
export async function fetchRawFields(): Promise<unknown> {
  const res = await apiClient.get(`${BASE}/raw-fields`)
  return res.data
}

// ── Ragic 快速連線 Ping ───────────────────────────────────────────────────────
export interface PingTestResult {
  test: string
  status_code?: number
  elapsed_ms: number
  body_type?: string
  record_count?: number
  body_preview?: unknown
  first_record_id?: string
  first_record_raw?: Record<string, unknown>
  error?: string
  tip?: string
}
export interface PingResult {
  ragic_base_url: string
  pageid: string | null
  api_key_prefix: string
  results: PingTestResult[]
}

export async function fetchPing(): Promise<PingResult> {
  const res = await apiClient.get<PingResult>(`${BASE}/ping`)
  return res.data
}

// ── Ragic 同步診斷 ────────────────────────────────────────────────────────────
export interface SyncFeeTotals {
  outsource_fee:               number
  maintenance_fee:             number
  deduction_fee:               number
  deduction_counter:           number
  outsource_plus_maintenance:  number
}

export interface SyncFeeSample {
  ragic_id:          string
  case_no:           string
  outsource_fee:     number
  maintenance_fee:   number
  deduction_fee:     number
  deduction_counter: number
  _raw_outsource:    unknown
  _raw_maintenance:  unknown
  _raw_deduction:    unknown
  _raw_ded_counter:  unknown
}

export interface SyncResult {
  ok: boolean
  total_parsed: number
  no_date_count: number
  year_distribution: Record<number, number>
  fee_totals?: SyncFeeTotals
  fee_samples?: SyncFeeSample[]
  field_names: string[]
  sample_raw: Record<string, unknown>
  recent_samples: Array<{
    ragic_id: string; case_no: string; title: string
    occurred_at: string; status: string
  }>
  ragic_url: string
}

export async function fetchSync(): Promise<SyncResult> {
  const res = await apiClient.get<SyncResult>(`${BASE}/sync`)
  return res.data
}
