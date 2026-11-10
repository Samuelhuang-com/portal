/**
 * 飯店每日巡檢 API 封裝
 * Prefix: /api/v1/hotel-daily-inspection
 *
 * 2026-11-10 改版：照抄 api/mallFacilityInspection.ts（Samuel 裁示）。
 * 檔尾保留舊版匯出名稱（飯店管理 Dashboard、決策駕駛艙、舊 DailyInspectionFormTab 使用）。
 */
import apiClient from '@/api/client'

const BASE = '/hotel-daily-inspection'

// ── 型別 ─────────────────────────────────────────────────────────────────────

export interface HotelDIStats {
  sheet_key:       string
  latest_batch:    HotelDIBatchInfo | null
  latest_kpi:      HotelDIKpi | null
  recent_abnormal: HotelDIAbnormalItem[]
  total_batches_7d: number
  abnormal_trend:  HotelDITrendPoint[]
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
  // 2026-10-05 新增（判定與每日巡檢表 Drawer 相同）
  work_hours?:     string
  estimated_minutes?: number | null
  ragic_url?:      string
  source_label?:   string    // 來源（新表／封存舊表）
  archived?:       boolean
  unchecked?:      number
  measure?:        number   // 記錄值（溫度、度數…），不算異常
}

// ── 場次明細（頁籤 TAB 點列開 Drawer）2026-10-05 ─────────────────────────────
export type HotelDIItemStatus = 'normal' | 'abnormal' | 'pending' | 'unchecked' | 'measure' | 'note'

export interface HotelDIBatchDetail {
  batch: {
    ragic_id:        string
    sheet_key:       string
    inspection_date: string
    inspector_name:  string
    start_time:      string
    end_time:        string
    work_hours:      string
    ragic_url:       string
    estimated_minutes?: number | null
    source_label?:   string
    archived?:       boolean
    tab_label?:      string
  }
  kpi: {
    total: number; checked: number; normal: number; abnormal: number
    pending: number; unchecked: number; measure: number; completion_rate: number
  }
  items: { ragic_id: string; seq_no: number; item_name: string; result_raw: string; status: HotelDIItemStatus; is_image?: boolean }[]
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

/** 月份統計 — 單一 Sheet */
export interface HotelDIMonthlySheetSummary {
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

/** 月份統計 — 跨頁籤總覽（後端同時回傳商場同款欄位與舊有彙總欄位） */
export interface HotelDIMonthlyDashboardSummary {
  year:            number
  month:           string | number   // ?month=YYYY-MM 呼叫時為字串；舊呼叫（year+month）時為數字
  year_month:      string            // YYYY/MM
  total_items:     number
  checked_items:   number
  abnormal_items:  number
  total_minutes:   number
  completion_rate: number
  sheets:          (HotelDIMonthlySheetSummary & HotelDISheetSummary)[]
}

/** 舊名稱（飯店管理 Dashboard、決策駕駛艙） */
export type HotelDIMonthlyDashboard = HotelDIMonthlyDashboardSummary

// ── API 函式 ──────────────────────────────────────────────────────────────────

/**
 * 取得指定頁籤的 Dashboard 統計（主管儀表板用）
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
 * 取得指定頁籤指定月份的巡檢場次清單
 */
export async function fetchHotelDailyBatches(
  sheetKey:  string,
  params: { year_month?: string },
): Promise<HotelDIBatchRow[]> {
  const res = await apiClient.get<HotelDIBatchRow[]>(`${BASE}/${sheetKey}/batches`, { params })
  return res.data
}

/**
 * 取得指定頁籤單一巡檢場次明細（頁籤 TAB 明細 Drawer 用）
 */
export async function fetchHotelDailyBatchDetail(sheetKey: string, batchId: string): Promise<HotelDIBatchDetail> {
  const res = await apiClient.get<HotelDIBatchDetail>(`${BASE}/${sheetKey}/batches/${encodeURIComponent(batchId)}`)
  return res.data
}

/**
 * 觸發指定頁籤 Ragic 同步（背景執行）
 */
export async function syncHotelDailyFromRagic(sheetKey: string): Promise<void> {
  await apiClient.post(`${BASE}/${sheetKey}/sync`)
}

/**
 * 觸發全部頁籤 Ragic 同步（背景執行）
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

/**
 * 取得飯店每日巡檢 Dashboard 月份統計（跨 Sheet）
 * @param month  查詢月份 YYYY-MM （如 "2026-05"）。不填則後端自動使用當月。
 */
export async function fetchHotelDailyMonthlyDashboard(
  monthOrYear?: string | number,
  monthNum?: number,
): Promise<HotelDIMonthlyDashboardSummary> {
  // 兩種呼叫：('YYYY-MM') —— 本模組 Dashboard；(year, month) —— 飯店管理 Dashboard／決策駕駛艙
  const params: Record<string, unknown> =
    typeof monthOrYear === 'number'
      ? { year: monthOrYear, month: monthNum }
      : monthOrYear ? { month: monthOrYear } : {}
  const res = await apiClient.get<HotelDIMonthlyDashboardSummary>(
    `${BASE}/dashboard/monthly-summary`,
    { params },
  )
  return res.data
}

// ── 每日巡檢表彙整 型別 ───────────────────────────────────────────────────────

export interface HotelDIDailyFormRow {
  // 模板欄位
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
  // 比對結果欄位
  inspector:       string
  result_text:     string
  result_status:   'normal' | 'abnormal' | 'pending' | 'unchecked'
  abnormal_note:   string
  matched:         boolean
  abnormal:        boolean
  actual_minutes:  number   // 該 Sheet 本次／本月實際巡檢時間（分），0 = 無資料
}

export interface HotelDIDailyFormResponse {
  year:             number
  month:            number
  inspection_date:  string | null
  has_data_today:   boolean | null   // null = 整月模式；true/false = 單日模式
  rows:             HotelDIDailyFormRow[]
}

// 2026-10-05：月曆格每格附「哪幾項異常／待處理」，判定與每日巡檢表 Drawer 同一套
export interface HotelDIDailyIssue {
  source_tab:    string
  floor:         string
  item:          string          // 設備（Excel 項目）；版型外欄位為「版型外欄位」
  check_content: string          // 檢查內容；版型外欄位為 Ragic 欄位名
  status:        'abnormal' | 'pending'
  note:          string          // 異常說明（版型外欄位為 Ragic 填報值）
  in_template:   boolean
}

export interface HotelDIDailyCalendarDay {
  has_record:      boolean
  completion_rate: number
  abnormal_count:  number
  pending_count:   number
  issues?:         HotelDIDailyIssue[]
}

export interface HotelDIDailyCalendarSheet {
  key:   string
  floor: string
  title: string
  daily: Record<string, HotelDIDailyCalendarDay>  // key = "1" ~ "31"
}

export interface HotelDIDailyCalendarResponse {
  year:    number
  month:   number
  max_day: number
  sheets:  HotelDIDailyCalendarSheet[]
}

/**
 * 取得飯店每日巡檢表彙整資料（依標準模板 + 年月篩選）
 * inspectionDate 選填：填入時只取該日結果
 */
export async function fetchHotelDIDailyForm(
  year: number,
  month: number,
  inspectionDate?: string,
): Promise<HotelDIDailyFormResponse> {
  const params: Record<string, unknown> = { year, month }
  if (inspectionDate) params.inspection_date = inspectionDate
  const res = await apiClient.get<HotelDIDailyFormResponse>(`${BASE}/daily-form`, { params })
  return res.data
}

/**
 * 取得飯店指定月份每日巡檢狀況格（Dashboard 月曆格用）
 */
export async function fetchHotelDIDailyCalendar(
  year: number,
  month: number,
): Promise<HotelDIDailyCalendarResponse> {
  const res = await apiClient.get<HotelDIDailyCalendarResponse>(`${BASE}/daily-calendar`, {
    params: { year, month },
  })
  return res.data
}

// ── 每日巡檢表（Excel 版型，Dashboard 月曆格下一層）2026-10-04 ──────────────────

export interface HotelDIDailySheetReading {
  field: string
  label: string
  value: string
}

export interface HotelDIDailySheetResult {
  batch_ragic_id: string
  time_label:     string   // 同日多場次時為開始時間 HH:MM，單一場次為空字串
  status:         'normal' | 'abnormal' | 'pending' | 'unchecked' | 'reading'
  text:           string
  readings:       HotelDIDailySheetReading[]
}

export interface HotelDIDailySheetRow {
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
  kind:            'status' | 'reading' | 'separate' | 'unmapped'
  ragic_fields:    string[]
  note_field:      string
  results:         HotelDIDailySheetResult[]
  status:          string
  abnormal:        boolean
  abnormal_note:   string
  remark:          string
}

export interface HotelDIDailySheetBatch {
  ragic_id:       string
  ragic_url:      string
  inspector:      string
  start_time:     string
  end_time:       string
  start_hhmm:     string
  end_hhmm:       string
  work_hours:     string
  actual_minutes: number
}

export interface HotelDIDailySheetFloor {
  key:            string
  floor:          string
  title?:         string
  sheet_url:      string
  has_record:     boolean
  estimated_minutes?: number
  inspectors:     string[]
  batches:        HotelDIDailySheetBatch[]
  actual_minutes: number
}

export interface HotelDIDailySheetResponse {
  date:    string
  floors:  HotelDIDailySheetFloor[]
  rows:    HotelDIDailySheetRow[]
  summary: {
    floors_total:        number
    floors_logged:       number
    normal:              number
    abnormal:            number
    pending:             number
    unchecked:           number
    reading:             number
    std_minutes_routine: number
    std_minutes_total:   number
    actual_minutes:      number
    shift_times:         { label: string; range: string }[]
    // 表尾時間列（整棟巡檢由後端提供；商場不給，Drawer 用 shift_times 組）
    footer?:             { text: string; minutes: number; note: string }[]
    extra_issues?:       number   // 版型外欄位的異常／待處理筆數（商場）
  }
  // 2026-10-05：Ragic 有、Excel 版型沒有的欄位，填了異常／待處理時另外列出（商場）
  extra_issues?: HotelDIDailyExtraIssue[]
}

export interface HotelDIDailyExtraIssue {
  source_tab: string
  floor:      string
  field:      string
  status:     'abnormal' | 'pending'
  text:       string
  time_label: string
}

/** 取得指定日期的每日巡檢表（date = YYYY-MM-DD） */
export async function fetchHotelDIDailySheet(date: string): Promise<HotelDIDailySheetResponse> {
  const res = await apiClient.get<HotelDIDailySheetResponse>(`${BASE}/daily-sheet`, {
    params: { date },
  })
  return res.data
}

// ── 場次附圖（2026-11-10，照抄整棟巡檢 fetchFloorBatchImages）───────────────────
// url 指向 Ragic file.jsp（外部連結，不經 Portal 後端；瀏覽器需已登入 Ragic 才看得到）
export interface HotelDIImage { url: string; filename: string }

export async function fetchHotelDailyBatchImages(batchId: string): Promise<HotelDIImage[]> {
  const res = await apiClient.get<HotelDIImage[]>(`${BASE}/db-images/${encodeURIComponent(batchId)}`)
  return res.data
}

// ── 頁籤名稱（2026-11-10：可在頁面上修改；空白＝預設）──────────────────────────
export interface HotelDITabLabels {
  order:           string[]
  defaults:        Record<string, string>
  labels:          Record<string, string>
  edit_permission: string
}

export async function fetchHotelDITabLabels(): Promise<HotelDITabLabels> {
  const res = await apiClient.get<HotelDITabLabels>(`${BASE}/tab-labels`)
  return res.data
}

export async function saveHotelDITabLabels(
  labels: Record<string, string | null>,
): Promise<{ labels: Record<string, string> }> {
  const res = await apiClient.put<{ labels: Record<string, string> }>(`${BASE}/tab-labels`, { labels })
  return res.data
}

// ══ 舊版匯出（2026-11-10 前的名稱，保留給既有頁面）══════════════════════════════

// ── 每日巡檢表彙整 型別 ───────────────────────────────────────────────────────

export interface DailyFormRow {
  // 模板欄位
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
  // 比對結果欄位
  inspector:       string
  result_text:     string
  result_status:   'normal' | 'abnormal' | 'pending' | 'unchecked'
  abnormal_note:   string
  matched:         boolean
  abnormal:        boolean
  actual_minutes:  number   // 該 Sheet 本次／本月實際巡檢時間（分），0 = 無資料
}

export interface DailyFormResponse {
  year:             number
  month:            number
  inspection_date:  string | null
  has_data_today:   boolean | null   // null = 整月模式；true/false = 單日模式
  rows:             DailyFormRow[]
}

/**
 * 取得每日巡檢表彙整資料（依標準模板 + 年月篩選）
 * inspectionDate 選填：填入時只取該日結果
 */
export async function fetchHotelDailyForm(
  year: number,
  month: number,
  inspectionDate?: string,
): Promise<DailyFormResponse> {
  const params: Record<string, unknown> = { year, month }
  if (inspectionDate) params.inspection_date = inspectionDate
  const res = await apiClient.get<DailyFormResponse>(`${BASE}/daily-form`, { params })
  return res.data
}

// ── 月份每日巡檢狀況格 型別 ──────────────────────────────────────────────────

export interface DailyCalendarDay {
  has_record:      boolean
  completion_rate: number
  abnormal_count:  number
  pending_count:   number
}

export interface DailyCalendarSheet {
  key:   string
  floor: string
  title: string
  daily: Record<string, DailyCalendarDay>  // key = "1" ~ "31"
}

export interface DailyCalendarResponse {
  year:    number
  month:   number
  max_day: number
  sheets:  DailyCalendarSheet[]
}

/**
 * 取得指定月份每日巡檢狀況格（Dashboard 月曆格用）
 */
/** 舊名稱（相容）；新畫面請用 fetchHotelDIDailyCalendar */
export async function fetchHotelDailyCalendar(
  year: number,
  month: number,
): Promise<DailyCalendarResponse> {
  const res = await apiClient.get<DailyCalendarResponse>(`${BASE}/daily-calendar`, {
    params: { year, month },
  })
  return res.data
}
