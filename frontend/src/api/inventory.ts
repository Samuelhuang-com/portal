/**
 * 倉庫庫存 API functions
 * 對應後端 /api/v1/inventory/*
 */
import apiClient from './client'
import type {
  InventoryListResponse,
  InventorySingleResponse,
  InventoryStatsResponse,
  InventoryFilters,
} from '@/types/inventory'

const BASE = '/inventory'

/** 統計總覽 (KPI) */
export async function fetchInventoryStats(): Promise<InventoryStatsResponse> {
  const { data } = await apiClient.get<InventoryStatsResponse>(`${BASE}/stats`)
  return data
}

/** 清單（含分頁 & 篩選） */
export async function fetchInventoryRecords(
  filters: InventoryFilters = {},
): Promise<InventoryListResponse> {
  const { data } = await apiClient.get<InventoryListResponse>(BASE, {
    params: filters,
  })
  return data
}

/** 單筆 */
export async function fetchInventoryRecord(id: string): Promise<InventorySingleResponse> {
  const { data } = await apiClient.get<InventorySingleResponse>(`${BASE}/${id}`)
  return data
}

/** 手動觸發 Ragic → SQLite 同步 */
export async function syncInventoryFromRagic(): Promise<{
  success: boolean
  fetched: number
  upserted: number
  errors: string[]
}> {
  const { data } = await apiClient.post(`${BASE}/sync`)
  return data
}
