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
  source_label?:   string   // 點位表單「資料來源」欄位名稱（2026-11-04；未提供＝對應 Ragic 設備組）
  empty_day_text?: string   // 當日無資料時的提示（2026-11-04；未提供＝當日無巡檢紀錄）
  two_level?:      boolean  // 2026-11-05：點位＝母項，右側先列子項（例行維護類）
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
  hidden?:        boolean   // two_level：該層子項全部停用 → 只在編輯模式顯示
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
  children?:      FloorMapChildDay[]   // two_level：該層子項（含已停用）
  all_disabled?:  boolean
}

/** two_level 模組的子項（2026-11-05） */
export interface FloorMapChildDay {
  source_ref:     string
  label:          string
  system:         string
  frequency:      string
  schedule_label: string     // 排定 11/23 或 11/23～11/27
  in_batch:       boolean    // 本月批次是否有此項
  disabled:       boolean    // 已停用：顯示但不計入母項狀態
  status:         FloorMapStatus
  rows:           CheckRow[]
  batches:        FloorMapBatch[]
  ragic_url:      string
  inspectors:     string[]
  actual_minutes: number
}

export interface FloorMapStatusResponse {
  date:      string
  module:    string
  floor_key: string
  points:    FloorMapPoint[]
  groups:    Record<string, FloorMapGroupDay>
  unmapped?: FloorMapGroupMeta[]   // 所選期間有資料、但模組內沒有點位紀錄（含已停用）的資料來源（例行維護類，2026-11-04）
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

/** 置換樓層底圖（僅 WebP；需 floor_map_image_manage 權限） */
export async function uploadFloorPlanImage(
  floorKey: string,
  file: File,
  opts: { page?: number; dpi?: number } = {},
): Promise<{ key: string; width: number; height: number; version: string; source_format: string; page: number; page_count: number }> {
  const form = new FormData()
  form.append('file', file)
  // 全域預設 Content-Type 為 application/json，必須明確指定 multipart（同 approvals.ts／contract.ts）
  const res = await apiClient.post(`${BASE}/floors/${floorKey}/image`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params:  { page: opts.page ?? 1, dpi: opts.dpi ?? 150 },
  })
  return res.data
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

/** two_level 模組：子項停用／恢復（需編輯點位權限） */
export async function setFloorMapSourceDisabled(module: string, sourceRef: string, disabled: boolean): Promise<void> {
  await apiClient.post(`${BASE}/${module}/sources/disabled`, { source_ref: sourceRef, disabled })
}

export async function deleteFloorMapPoint(module: string, id: number): Promise<void> {
  await apiClient.delete(`${BASE}/${module}/points/${id}`)
}
