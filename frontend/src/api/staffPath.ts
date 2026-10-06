/**
 * 人員動線 API 封裝（集團工務決策駕駛艙「人員動線」TAB）
 * 對應後端 /api/v1/work-journal/path/*（routers/work_journal_path.py）
 *
 * ⚠️ 路徑是「依時間串起工作日誌的工作地點」推定而來，不是定位軌跡。
 */
import apiClient from '@/api/client'
import type { JournalRow, JournalVenue } from '@/api/workJournal'

export type PathConfidence = 'room' | 'point' | 'floor' | 'multi' | 'unknown'

export const CONFIDENCE_LABEL: Record<PathConfidence, string> = {
  room:    '房號',
  point:   '巡檢點位',
  floor:   '樓層',
  multi:   '跨樓層',
  unknown: '未定位',
}

export const CONFIDENCE_COLOR: Record<PathConfidence, string> = {
  room:    'green',
  point:   'cyan',
  floor:   'blue',
  multi:   'purple',
  unknown: 'default',
}

export interface PathFloor {
  key:   string                      // 'rf' | '10f' … | 'b4f'（由上而下）
  label: string
  kind:  'guest' | 'plan' | 'none'   // guest＝客房標準層向量圖；plan＝共用底圖；none＝尚無平面圖
  rooms: string[]                    // guest 層的規範房號
}

/** 巡檢類停留點涵蓋的樓層巡檢圖點位（座標為 0～1 比例；順序＝樓層巡檢圖 sort_order，為推測） */
export interface PathPoint {
  id:             number
  floor_key:      string
  x:              number
  y:              number
  label:          string
  equipment_code: string
  group_label:    string
  shared_label:   string
  placement:      'confirmed' | 'draft' | 'pending'
  status:         'normal' | 'abnormal' | 'unchecked' | 'no_record'
}

export interface PathStop {
  seq:         number
  confidence:  PathConfidence
  floors:      string[]
  room:        string | null
  extra_rooms: string[]
  basis:       string
  start_min:   number | null   // 距所選日期 00:00 的分鐘數（跨日可能 <0 或 >1440）
  end_min:     number | null
  start_time:  string
  end_time:    string
  start_dt:    string
  end_dt:      string
  work_min:    number | null
  estimated:   boolean
  overlap:     boolean
  venue:       'hotel' | 'mall'
  points?:     PathPoint[]       // 商場工務巡檢／整棟巡檢才有
  row:         JournalRow
}

export interface PathPersonStats {
  stops:           number
  located:         number
  rooms:           number
  floor_changes:   number
  vertical_floors: number
  floors:          string[]
  work_min:        number
  first_min:       number | null
  last_min:        number | null
  overlaps:        number
  untimed:         number
}

export interface PathPerson {
  person: string
  stats:  PathPersonStats
  stops:  PathStop[]
}

export interface StaffPathDay {
  date:    string
  venue:   JournalVenue
  floors:  PathFloor[]
  persons: PathPerson[]
  summary: {
    persons:     number
    stops:       number
    confidence:  Record<PathConfidence, number>
    located_pct: number
  }
}

export interface HotelPlanUnit {
  key:    string
  kind:   'room' | 'elevator' | 'stair' | 'service'
  suffix: string | null
  label:  string
  poly:   [number, number][]
  center: [number, number]
  door:   [number, number]
  s:      number              // 沿走道中心線的位置（弧長）
}

export interface HotelFloorPlan {
  name:       string
  source:     string
  width:      number
  height:     number
  centerline: [number, number][]
  corridor:   [number, number][]
  length:     number
  units:      HotelPlanUnit[]
}

/** 目前帳號能否看人員動線（白名單在後端 .env STAFF_PATH_ALLOWED_EMAILS；系統管理員也受限） */
export async function fetchStaffPathAccess(): Promise<boolean> {
  try {
    const res = await apiClient.get<{ allowed: boolean }>('/work-journal/path/access')
    return !!res.data?.allowed
  } catch {
    return false
  }
}

export async function fetchStaffPathDay(date: string, venue: JournalVenue = 'all'): Promise<StaffPathDay> {
  const res = await apiClient.get<StaffPathDay>('/work-journal/path/day', { params: { date, venue } })
  return res.data
}

export async function fetchHotelFloorPlan(): Promise<HotelFloorPlan> {
  const res = await apiClient.get<HotelFloorPlan>('/work-journal/path/hotel-floor-plan')
  return res.data
}

/** 共用樓層底圖（需登入＋任一樓層巡檢圖模組檢視權限），以 blob 轉 object URL */
export async function fetchSharedFloorImageUrl(floorKey: string): Promise<string> {
  const res = await apiClient.get(`/floor-map/floors/${floorKey}/image`, { responseType: 'blob' })
  return URL.createObjectURL(res.data as Blob)
}
