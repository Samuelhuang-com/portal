/**
 * 飯店管理 Dashboard — 跨模組彙整 API
 * 對應後端 hotel_overview.py 三支端點
 */
import apiClient from './client';

// ────────────────────────────────────────────────────────────────────────────
// B. 每日累計 — 六項來源 × 天數交叉表
// ────────────────────────────────────────────────────────────────────────────

export interface HotelDailyRow {
  category: string;
  hours: number[];
  total: number;
  pct: number;
  cases: number[];
  cases_total: number;
  cases_pct: number;
}

export interface HotelDailyHoursData {
  year: number;
  month: number;
  days: number[];
  weekdays: string[];
  rows: HotelDailyRow[];
}

export async function fetchHotelDailyHours(
  year: number,
  month: number,
): Promise<HotelDailyHoursData> {
  const res = await apiClient.get<HotelDailyHoursData>('/hotel/daily-hours', {
    params: { year, month },
  });
  return res.data;
}

// ────────────────────────────────────────────────────────────────────────────
// C. 每月累計 — 六項來源 × 12 個月交叉表
// ────────────────────────────────────────────────────────────────────────────

export interface HotelMonthlyRow {
  category: string;
  hours: number[];
  total: number;
  pct: number;
  cases: number[];
  cases_total: number;
  cases_pct: number;
}

export interface HotelMonthlyHoursData {
  year: number;
  months: number[];
  rows: HotelMonthlyRow[];
}

export async function fetchHotelMonthlyHours(
  year: number,
): Promise<HotelMonthlyHoursData> {
  const res = await apiClient.get<HotelMonthlyHoursData>('/hotel/monthly-hours', {
    params: { year },
  });
  return res.data;
}

// ────────────────────────────────────────────────────────────────────────────
// D. 人員工時% — 六項來源 × Top-15 人員
// ────────────────────────────────────────────────────────────────────────────

export interface HotelPersonRow {
  category: string;
  pct_by_person: number[];
}

export interface HotelPersonHoursData {
  year: number;
  persons: string[];
  person_totals: number[];   // 各人員全年合計工時（hr），與 persons 索引對應
  rows: HotelPersonRow[];
}

export async function fetchHotelPersonHours(
  year: number,
): Promise<HotelPersonHoursData> {
  const res = await apiClient.get<HotelPersonHoursData>('/hotel/person-hours', {
    params: { year },
  });
  return res.data;
}

// ────────────────────────────────────────────────────────────────────────────
// E. 匯出 PowerPoint 報告（方向 B：前端算好 KPI 傳入）
// ────────────────────────────────────────────────────────────────────────────

export interface KpiSummaryPayload {
  total_cases:      number
  completed_cases:  number
  total_work_hours: number
  abnormal_count:   number
  overdue_count:    number
}

export interface SourceCardPayload {
  source_name:     string
  source_key:      string
  case_count:      number
  completed_count: number
  completion_rate: number
  abnormal_count:  number
  overdue_count:   number
  work_hours:      number
  actual_hours?:   number
}

export interface RepairCostsPayload {
  outsource_fee:   number
  maintenance_fee: number
  deduction_fee:   number
  month_total_fee: number
  period_label:    string
}

export interface HotelPptxPayload {
  kpi_summary:  KpiSummaryPayload
  source_cards: SourceCardPayload[]
  repair_costs: RepairCostsPayload
}

/**
 * POST hotel/overview PPTX — 前端帶入已計算好的 KPI payload，觸發瀏覽器下載。
 */
export async function exportHotelOverviewPptx(
  year: number,
  month: number,
  payload: HotelPptxPayload,
): Promise<void> {
  const token = localStorage.getItem('access_token') ?? ''
  const url = `/api/v1/hotel/overview/export/pptx?year=${year}&month=${month}`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const errJson = await res.json()
      if (errJson?.detail) detail = errJson.detail
    } catch { /* ignore parse error */ }
    throw new Error(detail)
  }
  const blob = await res.blob()
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = `飯店管理報告_${year}年${String(month).padStart(2, '0')}月.pptx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
}

// ────────────────────────────────────────────────────────────────────────────
// 顏色對照（五項來源）
// ────────────────────────────────────────────────────────────────────────────

export const HOTEL_CATEGORY_COLORS: Record<string, string> = {
  '飯店週期保養': '#4BA8E8',
  'IHG客房保養': '#52C41A',
  '飯店每日巡檢': '#FA8C16',
  '保全巡檢':    '#722ED1',
  '飯店工務部':  '#13C2C2',
  TOTAL:       '#FF4D4F',
};
