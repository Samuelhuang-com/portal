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
} from '@/types/ihgRoomMaintenance'

const BASE = '/ihg-room-maintenance'

// ── 同步 Ragic → 本地 DB ──────────────────────────────────────────────────────
export async function syncIHGFromRagic(): Promise<{ success: boolean; message: string }> {
  const res = await apiClient.post<{ success: boolean; message: string }>(`${BASE}/sync`)
  return res.data
}

// ── KPI 統計 ──────────────────────────────────────────────────────────────────
export async function fetchIHGStats(year?: string): Promise<IHGStats> {
  const res = await apiClient.get<IHGStats>(`${BASE}/stats`, {
    params: year ? { year } : {},
  })
  return res.data
}

// ── 年度矩陣表 ────────────────────────────────────────────────────────────────
export async function fetchIHGMatrix(params?: {
  year?: string
  room_no?: string
  floor?: string
  cell_status?: string
}): Promise<MatrixResponse> {
  const res = await apiClient.get<MatrixResponse>(`${BASE}/matrix`, { params })
  return res.data
}

// ── 記錄清單（帶篩選/分頁）──────────────────────────────────────────────────
export async function fetchIHGRecords(params?: {
  year?: string
  month?: string
  room_no?: string
  floor?: string
  status?: string
  page?: number
  per_page?: number
}): Promise<IHGListResponse> {
  const res = await apiClient.get<IHGListResponse>(`${BASE}/records`, { params })
  return res.data
}

// ── 單筆明細 ─────────────────────────────────────────────────────────────────
export async function fetchIHGRecord(ragicId: string): Promise<IHGRecord> {
  const res = await apiClient.get<IHGRecord>(`${BASE}/${ragicId}`)
  return res.data
}

// ── 除錯：Ragic 原始欄位結構 ─────────────────────────────────────────────────
export async function fetchIHGDebugRaw(): Promise<Record<string, unknown>> {
  const res = await apiClient.get<Record<string, unknown>>(`${BASE}/debug-raw`)
  return res.data
}
