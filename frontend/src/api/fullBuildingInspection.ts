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

// ── 每日巡檢表 ────────────────────────────────────────────────────────────────

export interface FullBuildingDailyFormRow {
  floor:           string
  item:            string
  check_content:   string
  result_options:  string
  minutes:         number
  source_tab:      string
  item_first_row:  boolean
  floor_first_row: boolean
  floor_row_count: number
  item_row_count:  number
  inspector:       string
  result_text:     string
  result_status:   'normal' | 'abnormal' | 'pending' | 'unchecked'
  abnormal_note:   string
  matched:         boolean
  abnormal:        boolean
  actual_minutes:  number
}

export interface FullBuildingDailyFormResponse {
  year:                     number
  month:                    number
  inspection_date:          string
  rows:                     FullBuildingDailyFormRow[]
  standard_minutes_morning: number
  standard_minutes_total:   number
  actual_minutes:           number
}

/**
 * 取得整棟巡檢每日巡檢表
 * @param year            年份
 * @param month           月份
 * @param inspectionDate  巡檢日期 YYYY/MM/DD（不填則顯示整月模板）
 */
export async function fetchFullBuildingDailyForm(
  year: number,
  month: number,
  inspectionDate?: string,
): Promise<FullBuildingDailyFormResponse> {
  const params: Record<string, unknown> = { year, month }
  if (inspectionDate) params.inspection_date = inspectionDate
  const res = await apiClient.get<FullBuildingDailyFormResponse>(`${BASE}/daily-form`, { params })
  return res.data
}

// ── 月曆格（樓層 × 日）────────────────────────────────────────────────────────

export async function fetchFullBuildingInspectionCalendar(
  year: number,
  month: number,
): Promise<{ year: number; month: number; max_day: number; rows: import('@/components/MonthlyCalendarGrid').CalendarRow[] }> {
  const res = await apiClient.get(`${BASE}/dashboard/calendar`, { params: { year, month } })
  return res.data
}

// ── 各樓層場次清單 / 場次明細 ─────────────────────────────────────────────────
//
// ⚠️ 四個樓層的 router 掛在 /mall/{key}-inspection 底下（見 main.py 約 2769~2795 行），
//    不是 /full-building-inspection/ —— 這裡是「整棟巡檢」的 API 封裝檔，
//    但這幾支的 prefix 不同，不可套用檔案頂端的 BASE。

export interface FloorBatch {
  ragic_id:        string
  inspection_date: string   // YYYY/MM/DD
  inspector_name:  string
  start_time:      string   // 原始值，含時間
  end_time:        string
  work_hours:      string
  item_count:      number
  synced_at:       string | null
}

export interface FloorBatchKPI {
  total:           number
  normal:          number
  abnormal:        number
  pending:         number
  unchecked:       number
  /** 量測/程度型欄位（水位＝高/中/低、電瓶電壓＝靜置12.4V~12.7V…）的記錄值。
   *  有填就算「已巡檢」，但**不是異常、也不算合格** —— 它不是 pass/fail 判定。 */
  measure:         number
  completion_rate: number   // (normal + abnormal + pending + measure) / total × 100
  normal_rate:     number   // normal / (normal + abnormal + pending) × 100（分母不含 measure）
}

/** GET /batches 的一列 */
export interface FloorBatchRow {
  batch: FloorBatch
  kpi:   FloorBatchKPI
}

export interface FloorInspectionItem {
  ragic_id:       string
  batch_ragic_id: string
  seq_no:         number
  item_name:      string
  result_raw:     string
  result_status:  'normal' | 'abnormal' | 'pending' | 'unchecked' | 'measure'
  abnormal_flag:  boolean
  synced_at:      string | null
}

export interface FloorBatchDetail {
  batch: FloorBatch
  kpi:   FloorBatchKPI
  items: FloorInspectionItem[]
}

const floorBase = (sheetKey: string) => `/mall/${sheetKey}-inspection`

/**
 * 取得某樓層的巡檢場次清單
 * @param sheetKey  rf | b4f | b2f | b1f
 * @param yearMonth 篩選年月 YYYY/MM（後端用 LIKE 'YYYY/MM%' 比對 inspection_date）
 */
export async function fetchFloorBatches(
  sheetKey: string,
  yearMonth?: string,
): Promise<FloorBatchRow[]> {
  const params = yearMonth ? { year_month: yearMonth } : {}
  const res = await apiClient.get<FloorBatchRow[]>(
    `${floorBase(sheetKey)}/batches`, { params },
  )
  return res.data
}

/** 取得單一場次完整資料（含所有設備項目 + KPI），供明細 Drawer 使用 */
export async function fetchFloorBatchDetail(
  sheetKey: string,
  batchId: string,
): Promise<FloorBatchDetail> {
  const res = await apiClient.get<FloorBatchDetail>(
    `${floorBase(sheetKey)}/batches/${encodeURIComponent(batchId)}`,
  )
  return res.data
}

/** 狀態分佈（後端 StatusDistItem） */
export interface FloorStatusDistItem {
  status: string
  label:  string
  count:  number
  color:  string
}

/** 近 7 日異常趨勢的一點（後端 abnormal_trend: List[dict]） */
export interface FloorAbnormalTrendPoint {
  date:           string   // YYYY/MM/DD
  abnormal_count: number
  has_record:     boolean
}

/** GET /stats（後端 *InspectionStats） */
export interface FloorStats {
  latest_batch:        FloorBatch | null
  latest_kpi:          FloorBatchKPI | null
  recent_abnormal:     FloorInspectionItem[]
  recent_pending:      FloorInspectionItem[]
  status_distribution: FloorStatusDistItem[]
  total_batches_7d:    number
  abnormal_trend:      FloorAbnormalTrendPoint[]
}

/**
 * 取得某樓層的全站統計（最新一場次 KPI、異常/待處理清單、近 7 日趨勢）
 *
 * ⚠️ latest_batch / latest_kpi 在「該樓層一筆資料都沒有」時為 null，
 *    呼叫端必須處理，不可假設一定有值。
 */
export async function fetchFloorStats(sheetKey: string): Promise<FloorStats> {
  const res = await apiClient.get<FloorStats>(`${floorBase(sheetKey)}/stats`)
  return res.data
}

/** 場次附圖（後端由已同步的「拍照」欄位值組出 Ragic 下載連結） */
export interface FloorImage {
  url:      string
  filename: string
}

/**
 * 取得某場次的附圖
 *
 * ⚠️ 回傳的 url 指向 Ragic 的 file.jsp，是**外部連結**，不經過 Portal 後端。
 *    Ragic 端若要求登入，未登入的瀏覽器會拿到 401/破圖 —— 這是既有模組
 *    （full_building_maintenance / mall_periodic_maintenance）共同的行為，
 *    不是本模組特有的問題。
 */
export async function fetchFloorBatchImages(
  sheetKey: string,
  batchId: string,
): Promise<FloorImage[]> {
  const res = await apiClient.get<FloorImage[]>(
    `${floorBase(sheetKey)}/db-images/${encodeURIComponent(batchId)}`,
  )
  return res.data
}
