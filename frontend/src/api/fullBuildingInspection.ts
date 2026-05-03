/**
 * 整棟巡檢 API 封裝
 * Prefix: /api/v1/full-building-inspection
 */
import apiClient from '@/api/client'

const BASE = '/full-building-inspection'

// ── 型別 ─────────────────────────────────────────────────────────────────────

export interface FullBuildingSheetConfig {
  key:         string
  floor:       string
  title:       string
  ragic_url:   string
  description: string
}

/** 月份統計 — 單一 Sheet */
export interface FullBuildingMonthlySheetSummary {
  key:               string
  floor:             string
  title:             string
  month_count:       number
  missing_count:     number
  missing_days:      string[]
  latest_batch_date: string
  has_today:         boolean
  is_current_month:  boolean
  trend_7d:          Array<{ date: string; has_record: boolean }>
  has_data:          boolean
}

/** 月份統計 — 跨 Sheet 總覽 */
export interface FullBuildingMonthlyDashboardSummary {
  month:      string   // YYYY-MM
  year_month: string   // YYYY/MM
  sheets:     FullBuildingMonthlySheetSummary[]
}

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得各樓層 Sheet 設定清單
 */
export async function fetchFullBuildingSheets(): Promise<FullBuildingSheetConfig[]> {
  const res = await apiClient.get<FullBuildingSheetConfig[]>(`${BASE}/sheets`)
  return res.data
}

/**
 * 取得整棟巡檢 Dashboard 月份統計（跨 Sheet）
 * @param month  查詢月份，YYYY-MM 格式（如 "2026-05"）。不填則後端自動使用當月。
 */
export async function fetchFullBuildingMonthlyDashboard(
  month?: string,
): Promise<FullBuildingMonthlyDashboardSummary> {
  const params = month ? { month } : {}
  const res = await apiClient.get<FullBuildingMonthlyDashboardSummary>(
    `${BASE}/dashboard/monthly-summary`,
    { params },
  )
  return res.data
}
