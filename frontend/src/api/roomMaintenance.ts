/**
 * 客房保養 API functions
 * 對應後端 /api/v1/room-maintenance/*
 */
import apiClient from './client'
import type {
  RoomMaintenanceListResponse,
  RoomMaintenanceSingleResponse,
  RoomMaintenanceStatsResponse,
  OptionsResponse,
  RoomMaintenanceCreate,
  RoomMaintenanceUpdate,
  RoomMaintenanceFilters,
} from '@/types/roomMaintenance'

const BASE = '/room-maintenance'

/** 取得下拉選項（檢查項目、工作狀態） */
export async function fetchOptions(): Promise<OptionsResponse> {
  const { data } = await apiClient.get<OptionsResponse>(`${BASE}/options`)
  return data
}

/** 統計總覽 (KPI) */
export async function fetchStats(): Promise<RoomMaintenanceStatsResponse> {
  const { data } = await apiClient.get<RoomMaintenanceStatsResponse>(`${BASE}/stats`)
  return data
}

/** 清單（含分頁 & 篩選） */
export async function fetchRecords(
  filters: RoomMaintenanceFilters = {},
): Promise<RoomMaintenanceListResponse> {
  const { data } = await apiClient.get<RoomMaintenanceListResponse>(BASE, {
    params: filters,
  })
  return data
}

/** 單筆 */
export async function fetchRecord(id: string): Promise<RoomMaintenanceSingleResponse> {
  const { data } = await apiClient.get<RoomMaintenanceSingleResponse>(`${BASE}/${id}`)
  return data
}

/** 新增 */
export async function createRecord(
  payload: RoomMaintenanceCreate,
): Promise<RoomMaintenanceSingleResponse> {
  const { data } = await apiClient.post<RoomMaintenanceSingleResponse>(BASE, payload)
  return data
}

/** 更新 */
export async function updateRecord(
  id: string,
  payload: RoomMaintenanceUpdate,
): Promise<RoomMaintenanceSingleResponse> {
  const { data } = await apiClient.put<RoomMaintenanceSingleResponse>(`${BASE}/${id}`, payload)
  return data
}

/** 刪除 */
export async function deleteRecord(id: string): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete<{ success: boolean }>(`${BASE}/${id}`)
  return data
}

/** 手動觸發 Ragic → SQLite 同步 */
export async function syncFromRagic(): Promise<{
  success: boolean
  fetched: number
  upserted: number
  errors: string[]
}> {
  const { data } = await apiClient.post(`${BASE}/sync`)
  return data
}
