/**
 * 每日數值登錄表 API 封裝
 * Prefix: /api/v1/hotel-meter-readings
 */
import apiClient from '@/api/client'

const BASE = '/hotel-meter-readings'

// ── 型別 ─────────────────────────────────────────────────────────────────────

export interface HotelMRSheetConfig {
  key:         string
  title:       string
  ragic_url:   string
  description: string
}

/** 單一 Sheet 的 Dashboard 統計 */
export interface HotelMRSheetSummary {
  key:                string
  title:              string
  ragic_url:          string
  has_today:          boolean          // 今日是否已登錄
  month_count:        number           // 本月登錄筆數
  latest_record_date: string           // 最近登錄日期 YYYY/MM/DD
  total_readings:     number           // 本月讀數欄位總筆數
  missing_days:       string[]         // 缺漏日期清單
  missing_count:      number           // 缺漏天數
  trend_7d:           HotelMRTrendPoint[] // 近 7 天趨勢
  has_data:           boolean          // 是否有任何資料
}

export interface HotelMRTrendPoint {
  date:       string   // YYYY/MM/DD
  has_record: boolean  // 當日是否有登錄
}

/** 跨 Sheet Dashboard 總覽 */
export interface HotelMRDashboardSummary {
  target_date: string
  year_month:  string
  sheets:      HotelMRSheetSummary[]
}

/** 登錄清單（列表頁）每一列資料 */
export interface HotelMRBatchRow {
  id:             string
  record_date:    string
  recorder_name:  string
  readings_count: number
  synced_at:      string
  ragic_url:      string
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得全體每日數值登錄 Dashboard 統計（跨 Sheet）
 */
export async function fetchHotelMeterDashboardSummary(
  targetDate?: string,
): Promise<HotelMRDashboardSummary> {
  const params = targetDate ? { target_date: targetDate } : {}
  const res = await apiClient.get<HotelMRDashboardSummary>(
    `${BASE}/dashboard/summary`,
    { params },
  )
  return res.data
}

/**
 * 取得指定 Sheet 指定月份的登錄清單
 */
export async function fetchHotelMeterBatches(
  sheetKey: string,
  params: { year_month?: string; search?: string },
): Promise<HotelMRBatchRow[]> {
  const res = await apiClient.get<HotelMRBatchRow[]>(
    `${BASE}/${sheetKey}/batches`,
    { params },
  )
  return res.data
}

/**
 * 取得 4 張 Sheet 設定清單
 */
export async function fetchHotelMeterSheets(): Promise<HotelMRSheetConfig[]> {
  const res = await apiClient.get<HotelMRSheetConfig[]>(`${BASE}/sheets`)
  return res.data
}

/**
 * 觸發指定 Sheet Ragic 同步（背景執行）
 */
export async function syncHotelMeterFromRagic(sheetKey: string): Promise<void> {
  await apiClient.post(`${BASE}/${sheetKey}/sync`)
}

/**
 * 觸發全部 4 張 Sheet Ragic 同步（背景執行）
 */
export async function syncHotelMeterAllFromRagic(): Promise<void> {
  await apiClient.post(`${BASE}/sync/all`)
}
