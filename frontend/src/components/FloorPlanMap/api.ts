/**
 * 樓層巡檢圖（共用）API —— 後端 backend/app/routers/floor_map.py（/api/v1/floor-map）
 * 規格：docs/DEV_SPEC_floor_plan_map.md §5.1、§6
 */
import apiClient from '@/api/client'
import type { CheckRow } from './CheckRowResult'
import type { FloorMapPlacement, FloorMapStatus } from './status'

const BASE = '/floor-map'

export interface FloorPlan {
  key:     string
  label:   string
  width:   number
  height:  number
  version: string
}

export interface FloorMapGroupMeta {
  source_ref:   string
  label:        string
  system:       string
  shared_label: string   // 非空＝這組資料被多台設備共用，畫面必須顯示
}

export interface FloorMapModuleMeta {
  module:          string
  label:           string
  floors:          string[]
  default_floor:   string
  attr_fields:     string[]
  edit_permission: string
  groups:          FloorMapGroupMeta[]
  systems:         string[]
  data_end:        string | null   // 資料最後一天 YYYY/MM/DD
}

export interface FloorMapPoint {
  id:             number
  module:         string
  floor_key:      string
  x:              number   // 0～1，左→右
  y:              number   // 0～1，上→下
  label:          string
  equipment_code: string
  source_ref:     string
  group_label:    string
  system:         string
  shared_label:   string
  placement:      FloorMapPlacement
  attrs:          Record<string, string>
  note:           string
  updated_by:     string
  updated_at:     string
  status?:        FloorMapStatus
}

export interface FloorMapBatch {
  ragic_id:       string
  ragic_url:      string
  inspector:      string
  start_hhmm:     string
  end_hhmm:       string
  actual_minutes: number
}

export interface FloorMapGroupDay extends FloorMapGroupMeta {
  status:         FloorMapStatus
  rows:           CheckRow[]
  batches:        FloorMapBatch[]
  inspectors:     string[]
  actual_minutes: number
}

export interface FloorMapStatusResponse {
  date:      string
  module:    string
  floor_key: string
  points:    FloorMapPoint[]
  groups:    Record<string, FloorMapGroupDay>
}

export interface FloorMapDayCell {
  day:           number
  date:          string
  status:        FloorMapStatus
  abnormal_rows: number
}

export interface FloorMapPointInput {
  x:               number
  y:               number
  label:           string
  equipment_code?: string | null
  source_ref:      string
  placement?:      FloorMapPlacement
  attrs?:          Record<string, string | null> | null
  note?:           string | null
}

export async function fetchFloorPlans(): Promise<FloorPlan[]> {
  const res = await apiClient.get(`${BASE}/floors`)
  return res.data.floors
}

/** 底圖需登入才能取，以 blob 載入後轉成 object URL（呼叫端負責 revoke） */
export async function fetchFloorPlanImageUrl(floorKey: string): Promise<string> {
  const res = await apiClient.get(`${BASE}/floors/${floorKey}/image`, { responseType: 'blob' })
  return URL.createObjectURL(res.data as Blob)
}

export async function fetchFloorMapMeta(module: string): Promise<FloorMapModuleMeta> {
  const res = await apiClient.get(`${BASE}/${module}/meta`)
  return res.data
}

export async function fetchFloorMapStatus(module: string, floorKey: string, date: string): Promise<FloorMapStatusResponse> {
  const res = await apiClient.get(`${BASE}/${module}/floors/${floorKey}/status`, { params: { date } })
  return res.data
}

export async function fetchFloorMapMonth(
  module: string, sourceRef: string, year: number, month: number,
): Promise<FloorMapDayCell[]> {
  const res = await apiClient.get(`${BASE}/${module}/month`, { params: { source_ref: sourceRef, year, month } })
  return res.data.days
}

export async function createFloorMapPoint(module: string, floorKey: string, body: FloorMapPointInput): Promise<FloorMapPoint> {
  const res = await apiClient.post(`${BASE}/${module}/floors/${floorKey}/points`, body)
  return res.data
}

export async function updateFloorMapPoint(module: string, id: number, body: Partial<FloorMapPointInput>): Promise<FloorMapPoint> {
  const res = await apiClient.patch(`${BASE}/${module}/points/${id}`, body)
  return res.data
}

export async function deleteFloorMapPoint(module: string, id: number): Promise<void> {
  await apiClient.delete(`${BASE}/${module}/points/${id}`)
}
