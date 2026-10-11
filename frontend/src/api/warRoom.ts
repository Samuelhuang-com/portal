/**
 * 戰情 KPI API 封裝 — 對應後端 /api/v1/war-room/*（routers/war_room.py）
 */
import apiClient from '@/api/client'
import type { JournalRow } from '@/api/workJournal'
import type { HotelFloorPlan } from '@/api/staffPath'

export type PointStatus = 'normal' | 'abnormal' | 'unchecked' | 'no_record'

export interface WrRepair {
  source:           'dazhi' | 'luqun'
  source_label:     string
  ragic_id:         string
  ragic_url:        string
  case_no:          string
  title:            string
  status:           string
  repair_type:      string
  floor_raw:        string
  room:             string | null
  floors:           string[]
  responsible_unit: string
  occurred_at:      string
  completed_at:     string
  wait_days:        number | null
  open?:            boolean
}

export interface WrPoint {
  id:             number
  module:         string
  module_label:   string
  floor_key:      string
  x:              number
  y:              number
  label:          string
  equipment_code: string
  source_ref:     string
  group_label:    string
  system:         string
  shared_label:   string
  placement:      'confirmed' | 'draft' | 'pending'
  status:         PointStatus
  attrs?:         Record<string, string>
  note?:          string
}

export interface WrPersonStop {
  seq:          number
  start_time:   string
  end_time:     string
  task:         string
  room:         string | null
  confidence:   string
  source_label: string
  row:          JournalRow
}

export interface WrFloor {
  key:           string
  label:         string
  kind:          'guest' | 'plan' | 'none'
  rooms:         string[]
  people:        { person: string; stops: WrPersonStop[] }[]
  people_count:  number
  stops:         number
  work_min:      number
  rooms_visited: string[]
  points:        WrPoint[]
  point_status:  Record<PointStatus, number>
  repairs:       WrRepair[]
  repairs_count: number
}

export interface WrFloors {
  date:         string
  generated_at: string
  floors:       WrFloor[]
  summary: {
    persons: number; stops: number; work_min: number
    points: number; abnormal: number; unchecked: number; no_record: number
    repairs_open: number; repairs_open_hotel: number; repairs_open_mall: number; repairs_over_7d: number
  }
}

export interface WrCheckRow {
  check_content:  string
  status:         string
  abnormal:       boolean
  abnormal_note:  string
  results:        { time_label: string; status: string; text: string }[]
}

export interface WrPointDetail {
  date:  string
  point: WrPoint
  today: {
    status:         PointStatus
    rows:           WrCheckRow[]
    batches:        { ragic_url: string; inspector: string; start_hhmm: string; end_hhmm: string }[]
    inspectors:     string[]
    actual_minutes: number
  }
  month: { day: number; date: string; status: PointStatus; abnormal_rows?: number }[]
}

export interface WrIhg {
  ragic_id:     string
  ragic_url:    string
  maint_date:   string
  maint_type:   string
  status:       string
  is_completed: boolean
  assignee:     string
  checker:      string
  work_minutes: number | null
  ng_count:     number
  notes:        string
}

export interface WrRoomDetail {
  room:         string
  floor:        string
  days:         number
  repairs:      WrRepair[]
  repairs_open: number
  ihg:          WrIhg[]
}

export async function fetchWarRoomAccess(): Promise<boolean> {
  try {
    const res = await apiClient.get<{ allowed: boolean }>('/war-room/access')
    return !!res.data?.allowed
  } catch {
    return false
  }
}

export async function fetchWarRoomFloors(date: string): Promise<WrFloors> {
  return (await apiClient.get<WrFloors>('/war-room/floors', { params: { date } })).data
}

export async function fetchWarRoomPoints(): Promise<{ points: WrPoint[]; rooms: string[] }> {
  return (await apiClient.get<{ points: WrPoint[]; rooms: string[] }>('/war-room/points')).data
}

export async function fetchWarRoomPoint(id: number, date: string): Promise<WrPointDetail> {
  return (await apiClient.get<WrPointDetail>(`/war-room/point/${id}`, { params: { date } })).data
}

export async function fetchWarRoomRoom(room: string, days = 180): Promise<WrRoomDetail> {
  return (await apiClient.get<WrRoomDetail>(`/war-room/room/${encodeURIComponent(room)}`, { params: { days } })).data
}

/** 客房標準層向量幾何（3D 樓層用；與人員動線同一份，但只需戰情 KPI 權限） */
export async function fetchWarRoomHotelPlan(): Promise<HotelFloorPlan> {
  return (await apiClient.get<HotelFloorPlan>('/war-room/hotel-floor-plan')).data
}

// ── 異常告警（A1～A5）────────────────────────────────────────────────────────
export type AlertLevel = 'critical' | 'warning' | 'info'
export type AlertVenue = 'hotel' | 'mall' | 'both'

export interface WrAlert {
  key:         string
  type:        'A1' | 'A2' | 'A3' | 'A4' | 'A5'
  type_label:  string
  level:       AlertLevel
  level_label: string
  venue:       AlertVenue
  venue_label: string
  title:       string
  detail:      string
  floor:       string
  room:        string
  ref:         { kind?: string; room?: string; point_id?: number; point_ids?: number[]; ragic_url?: string; [k: string]: unknown }
  since:       string
  wait_days:   number | null
  last_sent:   string
  due:         boolean
}

export interface WrAlerts {
  date:         string
  generated_at: string
  alerts:       WrAlert[]
  summary:      { total: number; critical: number; warning: number; info: number; due: number; by_type: Record<string, number> }
  recipients:   { hotel: string[]; mall: string[] }
  auto_send:    boolean
  type_labels:  Record<string, string>
}

export interface WrAlertSettings {
  enabled:              Record<string, boolean>
  repair_warn_days:     number
  repair_critical_days: number
  inspect_deadline:     string
  ihg_lookback_days:    number
  repeat_critical_days: number
  room_repeat_count:    number
  room_repeat_days:     number
  auto_send:            boolean
}

export interface WrAlertSendPlan { emails: string[]; venues: string[]; count: number; titles: string[] }
export interface WrAlertSendResult {
  dry_run: boolean; plans: WrAlertSendPlan[]
  sent_mails: number; sent_alerts: number; errors: string[]; message?: string
}
export interface WrAlertLogEntry { at: string; by: string; mode: string; alerts: number; mails: number; recipients: string[] }

export async function fetchWarRoomAlerts(date: string): Promise<WrAlerts> {
  return (await apiClient.get<WrAlerts>('/war-room/alerts', { params: { date } })).data
}

export async function sendWarRoomAlerts(keys: string[], dryRun: boolean, force: boolean): Promise<WrAlertSendResult> {
  return (await apiClient.post<WrAlertSendResult>('/war-room/alerts/send', { keys, dry_run: dryRun, force })).data
}

export async function fetchWarRoomAlertSettings(): Promise<WrAlertSettings> {
  return (await apiClient.get<WrAlertSettings>('/war-room/alert-settings')).data
}

export async function saveWarRoomAlertSettings(body: Partial<WrAlertSettings>): Promise<WrAlertSettings> {
  return (await apiClient.put<WrAlertSettings>('/war-room/alert-settings', body)).data
}

export async function fetchWarRoomAlertLog(): Promise<WrAlertLogEntry[]> {
  return (await apiClient.get<{ log: WrAlertLogEntry[] }>('/war-room/alert-log')).data.log
}

export interface WrAlertRecipient { email: string; name: string; venues: ('hotel' | 'mall')[]; enabled: boolean }

export async function fetchWarRoomAlertRecipients(): Promise<WrAlertRecipient[]> {
  return (await apiClient.get<{ recipients: WrAlertRecipient[] }>('/war-room/alert-recipients')).data.recipients
}

export async function saveWarRoomAlertRecipients(recipients: WrAlertRecipient[]): Promise<WrAlertRecipient[]> {
  return (await apiClient.put<{ recipients: WrAlertRecipient[] }>('/war-room/alert-recipients', { recipients })).data.recipients
}
