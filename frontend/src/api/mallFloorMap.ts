/**
 * 樓層巡檢圖（Floor Plan Inspection Map）API
 * 後端：backend/app/routers/mall_floor_map.py（prefix /api/v1/mall-floor-map）
 * 規格：docs/SPEC_floor_plan_inspection.md
 */
import apiClient from '@/api/client'
import type { MallFIDailySheetBatch, MallFIDailySheetRow } from '@/api/mallFacilityInspection'

const BASE = '/mall-floor-map'

export type FloorMapStatus = 'normal' | 'abnormal' | 'unchecked' | 'no_record'

export interface FloorMapFloor {
  key:     string
  label:   string
  width:   number
  height:  number
  version: string
}

export interface FloorMapGroupMeta {
  key:          string   // `${sheet_key}|${item}`
  sheet_key:    string
  item:         string
  system:       string
  sheet_label:  string
  shared_label: string   // 空字串＝不是共用
}

export interface FloorMapPoint {
  id:             number
  floor_key:      string
  x:              number   // 0～1，左→右
  y:              number   // 0～1，上→下
  label:          string
  equipment_code: string
  sheet_key:      string
  item:           string
  group_key:      string
  system:         string
  shared_label:   string
  location_desc:  string
  supply_area:    string
  note:           string
  updated_by:     string
  updated_at:     string
  status?:        FloorMapStatus
}

export interface FloorMapGroupDay extends FloorMapGroupMeta {
  status:         FloorMapStatus
  rows:           MallFIDailySheetRow[]
  batches:        MallFIDailySheetBatch[]
  inspectors:     string[]
  actual_minutes: number
}

export interface FloorMapStatusResponse {
  date:      string
  floor_key: string
  points:    FloorMapPoint[]
  groups:    Record<string, FloorMapGroupDay>
}

export interface FloorMapMonthDay {
  day:           number
  date:          string
  status:        FloorMapStatus
  abnormal_rows: number
}

export interface FloorMapPointInput {
  x:              number
  y:              number
  label:          string
  equipment_code?: string | null
  sheet_key:      string
  item:           string
  location_desc?: string | null
  supply_area?:   string | null
  note?:          string | null
}

export async function fetchFloorMapFloors(): Promise<{
  floors: FloorMapFloor[]; groups: FloorMapGroupMeta[]; systems: string[]
}> {
  const res = await apiClient.get(`${BASE}/floors`)
  return res.data
}

/** 底圖需登入才能取，以 blob 載入後轉成 object URL */
export async function fetchFloorMapImageUrl(floorKey: string): Promise<string> {
  const res = await apiClient.get(`${BASE}/floors/${floorKey}/image`, { responseType: 'blob' })
  return URL.createObjectURL(res.data as Blob)
}

export async function fetchFloorMapStatus(floorKey: string, date: string): Promise<FloorMapStatusResponse> {
  const res = await apiClient.get(`${BASE}/floors/${floorKey}/status`, { params: { date } })
  return res.data
}

export async function fetchFloorMapGroupMonth(
  sheetKey: string, item: string, year: number, month: number,
): Promise<{ days: FloorMapMonthDay[] }> {
  const res = await apiClient.get(`${BASE}/group-month`, {
    params: { sheet_key: sheetKey, item, year, month },
  })
  return res.data
}

export async function createFloorMapPoint(floorKey: string, body: FloorMapPointInput): Promise<FloorMapPoint> {
  const res = await apiClient.post(`${BASE}/floors/${floorKey}/points`, body)
  return res.data
}

export async function updateFloorMapPoint(id: number, body: Partial<FloorMapPointInput>): Promise<FloorMapPoint> {
  const res = await apiClient.patch(`${BASE}/points/${id}`, body)
  return res.data
}

export async function deleteFloorMapPoint(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/points/${id}`)
}
