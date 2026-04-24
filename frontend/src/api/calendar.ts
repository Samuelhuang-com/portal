/**
 * 行事曆模組 API functions
 * 對應後端 /api/v1/calendar/*
 */
import apiClient from './client'
import type {
  CalendarEventsResponse,
  CalendarTodaySummary,
  CalendarCustomEvent,
  CustomEventCreatePayload,
} from '@/types/calendar'

const BASE = '/calendar'

// ── 聚合事件查詢 ──────────────────────────────────────────────────────────────

export async function fetchCalendarEvents(params: {
  start:  string        // YYYY-MM-DD
  end:    string        // YYYY-MM-DD
  types?: string        // 逗號分隔，空=全部
}): Promise<CalendarEventsResponse> {
  const { data } = await apiClient.get<CalendarEventsResponse>(`${BASE}/events`, {
    params: {
      start: params.start,
      end:   params.end,
      ...(params.types ? { types: params.types } : {}),
    },
  })
  return data
}

// ── 今日摘要 KPI ───────────────────────────────────────────────────────────────

export async function fetchCalendarToday(): Promise<CalendarTodaySummary> {
  const { data } = await apiClient.get<CalendarTodaySummary>(`${BASE}/today`)
  return data
}

// ── 自訂事件 CRUD ─────────────────────────────────────────────────────────────

export async function fetchCustomEvents(params?: {
  start?: string
  end?:   string
}): Promise<CalendarCustomEvent[]> {
  const { data } = await apiClient.get<CalendarCustomEvent[]>(`${BASE}/custom`, {
    params,
  })
  return data
}

export async function createCustomEvent(
  payload: CustomEventCreatePayload,
): Promise<CalendarCustomEvent> {
  const { data } = await apiClient.post<CalendarCustomEvent>(`${BASE}/custom`, payload)
  return data
}

export async function updateCustomEvent(
  id: string,
  payload: CustomEventCreatePayload,
): Promise<CalendarCustomEvent> {
  const { data } = await apiClient.put<CalendarCustomEvent>(`${BASE}/custom/${id}`, payload)
  return data
}

export async function deleteCustomEvent(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/custom/${id}`)
}
