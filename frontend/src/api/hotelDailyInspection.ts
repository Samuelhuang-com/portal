/**
 * 飯店每日巡檢 API 封裝
 * Prefix: /api/v1/hotel-daily-inspection
 */
import apiClient from '@/api/client'

const BASE = '/hotel-daily-inspection'

// ── 型別 ─────────────────────────────────────────────────────────────────────

export interface HotelDIStats {
  sheet_key:        string
  latest_batch:     HotelDIBatchInfo | null
  latest_kpi:       HotelDIKpi | null
  recent_abnormal:  HotelDIAbnormalItem[]
  total_batches_7d: number
  abnormal_trend:   HotelDITrendPoint[]
}

export interface HotelDIBatchInfo {
  ragic_id:        string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  work_hours:      string
}

export interface HotelDIKpi {
  total:           number
  normal:          number
  abnormal:        number
  pending:         number
  unchecked:       number
  checked:         number
  completion_rate: number
}

export interface HotelDIAbnormalItem {
  item_name:     string
  result_raw:    string
  result_status: string
}

export interface HotelDITrendPoint {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

export interface HotelDIBatchRow {
  id:              string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  total:           number
  checked:         number
  abnormal:        number
  pending:         number
  completion_rate: number
}

export interface HotelDISheetSummary {
  key:             string
  floor:           string
  title:           string
  total_batches:   number
  total_items:     number
  checked_items:   number
  abnormal_items:  number
  pending_items:   number
  unchecked_items: number
  completion_rate: number
  has_data:        boolean
  total_minutes:   number
}

export interface HotelDIDashboardSummary {
  target_date: string
  sheets:      HotelDISheetSummary[]
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得指定區域的 Dashboard 統計
 */
export async function fetchHotelDailyStats(
  sheetKey: string,
  targetDate?: string,
): Promise<HotelDIStats> {
  const params = targetDate ? { target_date: targetDate } : {}
  const res = await apiClient.get<HotelDIStats>(`${BASE}/${sheetKey}/stats`, { params })
  return res.data
}

/**
 * 取得指定區域指定月份的巡檢場次清單
 */
export async function fetchHotelDailyBatches(
  sheetKey: string,
  params: { year_month?: string },
): Promise<HotelDIBatchRow[]> {
  const res = await apiClient.get<HotelDIBatchRow[]>(`${BASE}/${sheetKey}/batches`, { params })
  return res.data
}

/**
 * 觸發指定區域 Ragic 同步（背景執行）
 */
export async function syncHotelDailyFromRagic(sheetKey: string): Promise<void> {
  await apiClient.post(`${BASE}/${sheetKey}/sync`)
}

/**
 * 觸發全部 5 張 Sheet Ragic 同步（背景執行）
 */
export async function syncHotelDailyAllFromRagic(): Promise<void> {
  await apiClient.post(`${BASE}/sync/all`)
}

/**
 * 取得全體飯店每日巡檢 Dashboard 統計（跨 Sheet）
 */
export async function fetchHotelDailyDashboardSummary(
  targetDate?: string,
): Promise<HotelDIDashboardSummary> {
  const params = targetDate ? { target_date: targetDate } : {}
  const res = await apiClient.get<HotelDIDashboardSummary>(`${BASE}/dashboard/summary`, { params })
  return res.data
}
