// ── 客房保養 TypeScript 型別定義 ─────────────────────────────────────────────

export interface RoomMaintenanceRecord {
  id: string
  room_no: string
  inspect_items: string[]
  dept: string
  work_item: string
  inspect_datetime: string
  created_at: string
  updated_at: string
  close_date: string
  subtotal: number
  incomplete: number
}

export interface RoomMaintenanceMeta {
  total: number
  page: number
  per_page: number
}

export interface RoomMaintenanceListResponse {
  success: boolean
  data: RoomMaintenanceRecord[]
  meta: RoomMaintenanceMeta
}

export interface RoomMaintenanceSingleResponse {
  success: boolean
  data: RoomMaintenanceRecord
}

export interface RoomMaintenanceStats {
  total: number
  completed: number
  not_scheduled: number
  total_incomplete: number
  completion_rate: number
}

export interface RoomMaintenanceStatsResponse {
  success: boolean
  data: RoomMaintenanceStats
}

export interface OptionsResponse {
  inspect_item_options: string[]
  work_item_options: string[]
}

export interface RoomMaintenanceCreate {
  room_no: string
  inspect_items: string[]
  dept: string
  work_item: string
  inspect_datetime: string
  close_date?: string
}

export interface RoomMaintenanceUpdate {
  room_no?: string
  inspect_items?: string[]
  dept?: string
  work_item?: string
  inspect_datetime?: string
  close_date?: string
}

// ── Filter params ─────────────────────────────────────────────────────────────
export interface RoomMaintenanceFilters {
  room_no?: string
  work_item?: string
  dept?: string
  page?: number
  per_page?: number
}
