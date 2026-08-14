/**
 * 商場班表模組 API 封裝
 * 對應後端 /api/v1/mall/schedule/*
 *
 * 飯店班表為完全獨立的另一套，見 api/schedule.ts（/api/v1/schedule/*）。
 * 兩邊型別共用 @/types/schedule，函數簽章也刻意保持一致，
 * 頁面元件只要換 import 來源就能沿用。
 */
import apiClient from './client'
import type {
  Department, DepartmentInput,
  ShiftType, ShiftTypeInput,
  StaffMember, StaffMemberInput,
  Schedule, ScheduleTableData,
  ScheduleDetailRow,
  ImportResult, ImportLog,
  MonthlyStats, ScheduleFilters,
} from '@/types/schedule'

const BASE = '/mall/schedule'

// ── 部門管理 ────────────────────────────────────────────────

export const mallFetchDepartments = async (): Promise<Department[]> => {
  const { data } = await apiClient.get<Department[]>(`${BASE}/departments`)
  return data
}

export const mallCreateDepartment = async (body: DepartmentInput): Promise<Department> => {
  const { data } = await apiClient.post<Department>(`${BASE}/departments`, body)
  return data
}

export const mallUpdateDepartment = async (id: string, body: DepartmentInput): Promise<Department> => {
  const { data } = await apiClient.put<Department>(`${BASE}/departments/${id}`, body)
  return data
}

export const mallDeleteDepartment = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/departments/${id}`)
}

// ── 班別管理 ────────────────────────────────────────────────

export const mallFetchShifts = async (): Promise<ShiftType[]> => {
  const { data } = await apiClient.get<ShiftType[]>(`${BASE}/shifts`)
  return data
}

export const mallCreateShift = async (body: ShiftTypeInput): Promise<ShiftType> => {
  const { data } = await apiClient.post<ShiftType>(`${BASE}/shifts`, body)
  return data
}

export const mallUpdateShift = async (id: string, body: ShiftTypeInput): Promise<ShiftType> => {
  const { data } = await apiClient.put<ShiftType>(`${BASE}/shifts/${id}`, body)
  return data
}

export const mallDeleteShift = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/shifts/${id}`)
}

// ── 人員管理 ────────────────────────────────────────────────

export const mallFetchStaff = async (params?: {
  department_id?: string
  employment_type?: string
  is_active?: boolean
}): Promise<StaffMember[]> => {
  const { data } = await apiClient.get<StaffMember[]>(`${BASE}/staff`, { params })
  return data
}

export const mallCreateStaff = async (body: StaffMemberInput): Promise<StaffMember> => {
  const { data } = await apiClient.post<StaffMember>(`${BASE}/staff`, body)
  return data
}

export const mallUpdateStaff = async (id: string, body: StaffMemberInput): Promise<StaffMember> => {
  const { data } = await apiClient.put<StaffMember>(`${BASE}/staff/${id}`, body)
  return data
}

export const mallDeleteStaff = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/staff/${id}`)
}

// ── 班表主檔 ─────────────────────────────────────────────────

export const mallFetchSchedules = async (params?: { year?: number; month?: number }): Promise<Schedule[]> => {
  const { data } = await apiClient.get<Schedule[]>(`${BASE}/`, { params })
  return data
}

export const mallDeleteSchedule = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/${id}`)
}

// ── 表格式班表資料 ────────────────────────────────────────────

export const mallFetchScheduleTable = async (scheduleId: string): Promise<ScheduleTableData> => {
  const { data } = await apiClient.get<ScheduleTableData>(`${BASE}/${scheduleId}/details`)
  return data
}

// ── 明細列表 ─────────────────────────────────────────────────

export const mallFetchDetailList = async (filters: ScheduleFilters): Promise<ScheduleDetailRow[]> => {
  const { data } = await apiClient.get<ScheduleDetailRow[]>(`${BASE}/details/list`, { params: filters })
  return data
}

// ── 明細 CRUD ─────────────────────────────────────────────────

export const mallAddDetail = async (
  scheduleId: string,
  body: { work_date: string; staff_id: string; shift_code: string; remark?: string }
): Promise<{ id: string; ok: boolean }> => {
  const { data } = await apiClient.post(`${BASE}/${scheduleId}/details`, body)
  return data
}

export const mallEditDetail = async (
  scheduleId: string,
  detailId: string,
  body: { shift_code: string; remark?: string }
): Promise<{ ok: boolean }> => {
  const { data } = await apiClient.put(`${BASE}/${scheduleId}/details/${detailId}`, body)
  return data
}

export const mallDeleteDetail = async (scheduleId: string, detailId: string): Promise<void> => {
  await apiClient.delete(`${BASE}/${scheduleId}/details/${detailId}`)
}

// ── Excel 匯入 ────────────────────────────────────────────────

export const mallImportExcel = async (
  file: File,
  overrideYear?: number,
  overrideMonth?: number,
): Promise<ImportResult> => {
  const form = new FormData()
  form.append('file', file)
  if (overrideYear)  form.append('override_year',  String(overrideYear))
  if (overrideMonth) form.append('override_month', String(overrideMonth))
  const { data } = await apiClient.post<ImportResult>(`${BASE}/import`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const mallFetchImportLogs = async (limit = 20): Promise<ImportLog[]> => {
  const { data } = await apiClient.get<ImportLog[]>(`${BASE}/import-logs`, { params: { limit } })
  return data
}

// ── 班別區間查詢（單一場域）──────────────────────────────────
//
// ⚠️ 工作日誌請勿使用本函數 —— 它只回商場資料。
//    要飯店＋商場合併結果，請用 @/api/workJournal 的 fetchMergedShiftsRange()。

// ShiftInfo / ShiftsRangeData 定義在 api/schedule.ts，此處直接沿用不重複宣告
import type { ShiftInfo, ShiftsRangeData } from './schedule'
export type { ShiftInfo, ShiftsRangeData }

export const mallFetchShiftsRange = async (
  dateFrom: string,
  dateTo:   string,
): Promise<ShiftsRangeData> => {
  const { data } = await apiClient.get<ShiftsRangeData>(`${BASE}/shifts-range`, {
    params: { date_from: dateFrom, date_to: dateTo },
  })
  return data
}

// ── 統計 ─────────────────────────────────────────────────────

export const mallFetchStats = async (year: number, month: number): Promise<MonthlyStats> => {
  const { data } = await apiClient.get<MonthlyStats>(`${BASE}/stats`, { params: { year, month } })
  return data
}
