/**
 * 主管交辦／緊急事件 API 封裝
 * 所有對 /api/v1/other-tasks/* 的請求統一在此處理
 */
import apiClient from '@/api/client'
import type {
  OtherTaskDetailResult,
  OtherTaskFilterOptions,
  OtherTaskDetailParams,
} from '@/types/otherTasks'

const BASE = '/other-tasks'

export async function fetchYears(): Promise<{ years: number[] }> {
  const res = await apiClient.get(`${BASE}/years`)
  return res.data
}

export async function fetchFilterOptions(): Promise<OtherTaskFilterOptions> {
  const res = await apiClient.get<OtherTaskFilterOptions>(`${BASE}/filter-options`)
  return res.data
}

export async function fetchDetail(params: OtherTaskDetailParams): Promise<OtherTaskDetailResult> {
  const res = await apiClient.get<OtherTaskDetailResult>(`${BASE}/detail`, { params })
  return res.data
}

export async function triggerSync(): Promise<{ ok: boolean; message: string }> {
  const res = await apiClient.post(`${BASE}/sync`)
  return res.data
}

export async function fetchDbImages(ragicId: string): Promise<{ images: { url: string; filename: string }[] }> {
  const res = await apiClient.get(`${BASE}/db-images/${ragicId}`)
  return res.data
}

export interface OtherTaskTypeStat {
  total:      number
  work_hours: number
}

/**
 * 按 task_type 分組回傳件數與工時（供 Dashboard KPI 用）
 * 回傳 key 為 task_type（'上級交辦' | '緊急事件'）
 */
export async function fetchOtherTaskStats(
  year?: number,
  month?: number,
): Promise<Record<string, OtherTaskTypeStat>> {
  const res = await apiClient.get<Record<string, OtherTaskTypeStat>>(
    `${BASE}/stats`,
    { params: { year, month } },
  )
  return res.data
}
