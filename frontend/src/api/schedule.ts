/**
 * 班表模組 API 封裝
 * 對應後端 /api/v1/schedule/*
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

const BASE = '/schedule'

// ── 部門管理 ────────────────────────────────────────────────

export const fetchDepartments = async (): Promise<Department[]> => {
  const { data } = await apiClient.get<Department[]>(`${BASE}/departments`)
  return data
}

export const createDepartment = async (body: DepartmentInput): Promise<Department> => {
  const { data } = await apiClient.post<Department>(`${BASE}/departments`, body)
  return data
}

export const updateDepartment = async (id: string, body: DepartmentInput): Promise<Department> => {
  const { data } = await apiClient.put<Department>(`${BASE}/departments/${id}`, body)
  return data
}

export const deleteDepartment = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/departments/${id}`)
}

// ── 班別管理 ────────────────────────────────────────────────

export const fetchShifts = async (): Promise<ShiftType[]> => {
  const { data } = await apiClient.get<ShiftType[]>(`${BASE}/shifts`)
  return data
}

export const createShift = async (body: ShiftTypeInput): Promise<ShiftType> => {
  const { data } = await apiClient.post<ShiftType>(`${BASE}/shifts`, body)
  return data
}

export const updateShift = async (id: string, body: ShiftTypeInput): Promise<ShiftType> => {
  const { data } = await apiClient.put<ShiftType>(`${BASE}/shifts/${id}`, body)
  return data
}

export const deleteShift = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/shifts/${id}`)
}

// ── 人員管理 ────────────────────────────────────────────────

export const fetchStaff = async (params?: {
  department_id?: string
  employment_type?: string
  is_active?: boolean
}): Promise<StaffMember[]> => {
  const { data } = await apiClient.get<StaffMember[]>(`${BASE}/staff`, { params })
  return data
}

export const createStaff = async (body: StaffMemberInput): Promise<StaffMember> => {
  const { data } = await apiClient.post<StaffMember>(`${BASE}/staff`, body)
  return data
}

export const updateStaff = async (id: string, body: StaffMemberInput): Promise<StaffMember> => {
  const { data } = await apiClient.put<StaffMember>(`${BASE}/staff/${id}`, body)
  return data
}

export const deleteStaff = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/staff/${id}`)
}

// ── 班表主檔 ─────────────────────────────────────────────────

export const fetchSchedules = async (params?: { year?: number; month?: number }): Promise<Schedule[]> => {
  const { data } = await apiClient.get<Schedule[]>(`${BASE}/`, { params })
  return data
}

export const deleteSchedule = async (id: string): Promise<void> => {
  await apiClient.delete(`${BASE}/${id}`)
}

// ── 表格式班表資料 ────────────────────────────────────────────

export const fetchScheduleTable = async (scheduleId: string): Promise<ScheduleTableData> => {
  const { data } = await apiClient.get<ScheduleTableData>(`${BASE}/${scheduleId}/details`)
  return data
}

// ── 明細列表 ─────────────────────────────────────────────────

export const fetchDetailList = async (filters: ScheduleFilters): Promise<ScheduleDetailRow[]> => {
  const { data } = await apiClient.get<ScheduleDetailRow[]>(`${BASE}/details/list`, { params: filters })
  return data
}

// ── 明細 CRUD ─────────────────────────────────────────────────

export const addDetail = async (
  scheduleId: string,
  body: { work_date: string; staff_id: string; shift_code: string; remark?: string }
): Promise<{ id: string; ok: boolean }> => {
  const { data } = await apiClient.post(`${BASE}/${scheduleId}/details`, body)
  return data
}

export const editDetail = async (
  scheduleId: string,
  detailId: string,
  body: { shift_code: string; remark?: string }
): Promise<{ ok: boolean }> => {
  const { data } = await apiClient.put(`${BASE}/${scheduleId}/details/${detailId}`, body)
  return data
}

export const deleteDetail = async (scheduleId: string, detailId: string): Promise<void> => {
  await apiClient.delete(`${BASE}/${scheduleId}/details/${detailId}`)
}

// ── Excel 匯入 ────────────────────────────────────────────────

export const importExcel = async (
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

export const fetchImportLogs = async (limit = 20): Promise<ImportLog[]> => {
  const { data } = await apiClient.get<ImportLog[]>(`${BASE}/import-logs`, { params: { limit } })
  return data
}

// ── 班別區間查詢（供工作日誌整合使用）────────────────────────

export interface ShiftInfo {
  shift_code:  string
  shift_name:  string
  shift_color: string
  is_working:  boolean
}

/** { "2026-05-20": { "王大明": ShiftInfo, ... }, ... } */
export type ShiftsRangeData = Record<string, Record<string, ShiftInfo>>

export const fetchShiftsRange = async (
  dateFrom: string,
  dateTo:   string,
): Promise<ShiftsRangeData> => {
  const { data } = await apiClient.get<ShiftsRangeData>(`${BASE}/shifts-range`, {
    params: { date_from: dateFrom, date_to: dateTo },
  })
  return data
}

// ── 統計 ─────────────────────────────────────────────────────

export const fetchStats = async (year: number, month: number): Promise<MonthlyStats> => {
  const { data } = await apiClient.get<MonthlyStats>(`${BASE}/stats`, { params: { year, month } })
  return data
}
