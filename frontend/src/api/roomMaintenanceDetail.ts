/**
 * 客房保養明細 API functions
 * 對應後端 /api/v1/room-maintenance-detail/*
 */
import apiClient from './client'
import type {
  RoomMaintenanceDetailListResponse,
  RoomSummaryResponse,
  RoomMaintenanceDetailFilters,
  RoomMaintenanceDetailSyncResponse,
  RoomHistoryResponse,
  StaffHoursResponse,
  MaintenanceStatsResponse,
} from '@/types/roomMaintenanceDetail'

const BASE = '/room-maintenance-detail'

/** 明細列表（含分頁 & 篩選 & 日期區間） */
export async function fetchRoomDetailRecords(
  filters: RoomMaintenanceDetailFilters = {},
): Promise<RoomMaintenanceDetailListResponse> {
  const { data } = await apiClient.get<RoomMaintenanceDetailListResponse>(BASE, {
    params: filters,
  })
  return data
}

/** 總表（全房間清單，依日期區間聚合） */
export async function fetchRoomDetailSummary(
  date_from?: string,
  date_to?:   string,
): Promise<RoomSummaryResponse> {
  const params: Record<string, string> = {}
  if (date_from) params.date_from = date_from
  if (date_to)   params.date_to   = date_to
  const { data } = await apiClient.get<RoomSummaryResponse>(
    `${BASE}/summary`,
    { params },
  )
  return data
}

/** 單一房間保養歷史（月曆摘要 + 全記錄） */
export async function fetchRoomHistory(
  room_no: string,
  months = 12,
): Promise<RoomHistoryResponse> {
  const { data } = await apiClient.get<RoomHistoryResponse>(
    `${BASE}/room-history/${encodeURIComponent(room_no)}`,
    { params: { months } },
  )
  return data
}

/** 人員工時月報表（近 N 個月 pivot，分鐘→小時） */
export async function fetchStaffHours(
  months = 12,
  date_from?: string,
  date_to?:   string,
): Promise<StaffHoursResponse> {
  const params: Record<string, string | number> = { months }
  if (date_from) params.date_from = date_from
  if (date_to)   params.date_to   = date_to
  const { data } = await apiClient.get<StaffHoursResponse>(
    `${BASE}/staff-hours`,
    { params },
  )
  return data
}

/** 保養統計分析（近 N 個月完成率趨勢、異常項目、樓層分析、高風險房間、月份對比） */
export async function fetchMaintenanceStats(
  months = 12,
): Promise<MaintenanceStatsResponse> {
  const { data } = await apiClient.get<MaintenanceStatsResponse>(
    `${BASE}/maintenance-stats`,
    { params: { months } },
  )
  return data
}

/** 手動觸發 Ragic → SQLite 同步 */
export async function syncRoomDetailFromRagic(): Promise<RoomMaintenanceDetailSyncResponse> {
  const { data } = await apiClient.post<RoomMaintenanceDetailSyncResponse>(
    `${BASE}/sync`,
  )
  return data
}
