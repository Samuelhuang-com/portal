/**
 * 春大直商場工務巡檢 API 封裝
 * Prefix: /api/v1/mall-facility-inspection
 */
import apiClient from '@/api/client'

const BASE = '/mall-facility-inspection'

// ── 型別 ─────────────────────────────────────────────────────────────────────

export interface MallFIStats {
  sheet_key:       string
  latest_batch:    MallFIBatchInfo | null
  latest_kpi:      MallFIKpi | null
  recent_abnormal: MallFIAbnormalItem[]
  total_batches_7d: number
  abnormal_trend:  MallFITrendPoint[]
}

export interface MallFIBatchInfo {
  ragic_id:        string
  inspection_date: string
  inspector_name:  string
  start_time:      string
  end_time:        string
  work_hours:      string
}

export interface MallFIKpi {
  total:           number
  normal:          number
  abnormal:        number
  pending:         number
  unchecked:       number
  checked:         number
  completion_rate: number
}

export interface MallFIAbnormalItem {
  item_name:     string
  result_raw:    string
  result_status: string
}

export interface MallFITrendPoint {
  date:           string
  abnormal_count: number
  has_record:     boolean
}

export interface MallFIBatchRow {
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

export interface MallFISheetSummary {
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

export interface MallFIDashboardSummary {
  target_date: string
  sheets:      MallFISheetSummary[]
}

/** 月份統計 — 單一 Sheet */
export interface MallFIMonthlySheetSummary {
  key:               string
  floor:             string
  title:             string
  month_count:       number              // 查詢月份內登錄筆數
  missing_count:     number              // 缺漏天數
  missing_days:      string[]            // 缺漏日期清單
  latest_batch_date: string              // 查詢月份內最近登錄日期
  has_today:         boolean             // 今日（或末日）是否已登錄
  is_current_month:  boolean             // 是否為當月查詢
  trend_7d:          Array<{ date: string; has_record: boolean }>
  has_data:          boolean
}

/** 月份統計 — 跨 Sheet 總覽 */
export interface MallFIMonthlyDashboardSummary {
  month:      string   // YYYY-MM
  year_month: string   // YYYY/MM
  sheets:     MallFIMonthlySheetSummary[]
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得指定樓層的 Dashboard 統計（主管儀表板用）
 */
export async function fetchMallFacilityStats(
  sheetKey: string,
  targetDate?: string,
): Promise<MallFIStats> {
  const params = targetDate ? { target_date: targetDate } : {}
  const res = await apiClient.get<MallFIStats>(`${BASE}/${sheetKey}/stats`, { params })
  return res.data
}

/**
 * 取得指定樓層指定月份的巡檢場次清單
 */
export async function fetchMallFacilityBatches(
  sheetKey:  string,
  params: { year_month?: string },
): Promise<MallFIBatchRow[]> {
  const res = await apiClient.get<MallFIBatchRow[]>(`${BASE}/${sheetKey}/batches`, { params })
  return res.data
}

/**
 * 觸發指定樓層 Ragic 同步（背景執行）
 */
export async function syncMallFacilityFromRagic(sheetKey: string): Promise<void> {
  await apiClient.post(`${BASE}/${sheetKey}/sync`)
}

/**
 * 觸發全部 5 張 Sheet Ragic 同步（背景執行）
 */
export async function syncMallFacilityAllFromRagic(): Promise<void> {
  await apiClient.post(`${BASE}/sync/all`)
}

/**
 * 取得全體商場工務巡檢 Dashboard 統計（跨 Sheet）
 */
export async function fetchMallFacilityDashboardSummary(
  targetDate?: string,
): Promise<MallFIDashboardSummary> {
  const params = targetDate ? { target_date: targetDate } : {}
  const res = await apiClient.get<MallFIDashboardSummary>(`${BASE}/dashboard/summary`, { params })
  return res.data
}

/**
 * 取得商場工務巡檢 Dashboard 月份統計（跨 Sheet）
 * @param month  查詢月份 YYYY-MM （如 "2026-05"）。不填則後端自動使用當月。
 */
export async function fetchMallFacilityMonthlyDashboard(
  month?: string,
): Promise<MallFIMonthlyDashboardSummary> {
  const params = month ? { month } : {}
  const res = await apiClient.get<MallFIMonthlyDashboardSummary>(
    `${BASE}/dashboard/monthly-summary`,
    { params },
  )
  return res.data
}
