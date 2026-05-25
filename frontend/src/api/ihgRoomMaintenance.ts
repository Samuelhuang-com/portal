/**
 * IHG 客房保養 API 封裝
 * Base: /api/v1/ihg-room-maintenance
 */
import apiClient from './client'
import type {
  IHGStats,
  MatrixResponse,
  IHGRecord,
  IHGListResponse,
  SectionMatrixResponse,
  IHGCalendarResponse,
} from '@/types/ihgRoomMaintenance'

const BASE = '/ihg-room-maintenance'

export async function syncIHGFromRagic(): Promise<{ success: boolean; message: string }> {
  const res = await apiClient.post<{ success: boolean; message: string }>(`${BASE}/sync`)
  return res.data
}

export async function fetchIHGStats(year?: string, month?: string): Promise<IHGStats> {
  const params: Record<string, string> = {}
  if (year)  params.year  = year
  if (month) params.month = month
  const res = await apiClient.get<IHGStats>(`${BASE}/stats`, { params })
  return res.data
}

export async function fetchIHGMatrix(params?: {
  year?: string
  room_no?: string
  floor?: string
  cell_status?: string
}): Promise<MatrixResponse> {
  const res = await apiClient.get<MatrixResponse>(`${BASE}/matrix`, { params })
  return res.data
}

export async function fetchIHGRecords(params?: {
  year?: string
  month?: string
  day?: string
  room_no?: string
  floor?: string
  status?: string
  page?: number
  per_page?: number
}): Promise<IHGListResponse> {
  const res = await apiClient.get<IHGListResponse>(`${BASE}/records`, { params })
  return res.data
}

export async function fetchIHGCalendar(params: {
  year: string
  month: string
}): Promise<IHGCalendarResponse> {
  const res = await apiClient.get<IHGCalendarResponse>(`${BASE}/calendar`, { params })
  return res.data
}

export async function fetchIHGRecord(ragicId: string): Promise<IHGRecord> {
  const res = await apiClient.get<IHGRecord>(`${BASE}/${ragicId}`)
  return res.data
}

export async function fetchIHGSectionMatrix(params: {
  year: string
  month: string
  floor?: string
}): Promise<SectionMatrixResponse> {
  const res = await apiClient.get<SectionMatrixResponse>(`${BASE}/section-matrix`, { params })
  return res.data
}

export async function fetchIHGDebugRaw(): Promise<Record<string, unknown>> {
  const res = await apiClient.get<Record<string, unknown>>(`${BASE}/debug-raw`)
  return res.data
}
