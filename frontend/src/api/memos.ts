/**
 * 公告系統 API functions
 * 對應後端 /api/v1/memos/*
 */
import apiClient from './client'
import type {
  MemoCreatePayload,
  MemoDetail,
  MemoFileItem,
  MemoFilters,
  MemoListResponse,
  MemoUpdatePayload,
} from '@/types/memo'

const BASE = '/memos'

export async function fetchMemos(filters: MemoFilters = {}): Promise<MemoListResponse> {
  const { data } = await apiClient.get<MemoListResponse>(BASE, { params: filters })
  return data
}

export async function fetchMemo(id: string): Promise<MemoDetail> {
  const { data } = await apiClient.get<MemoDetail>(`${BASE}/${id}`)
  return data
}

export async function createMemo(payload: MemoCreatePayload): Promise<MemoDetail> {
  const { data } = await apiClient.post<MemoDetail>(BASE, payload)
  return data
}

export async function updateMemo(id: string, payload: MemoUpdatePayload): Promise<MemoDetail> {
  const { data } = await apiClient.patch<MemoDetail>(`${BASE}/${id}`, payload)
  return data
}

export async function deleteMemo(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}

export async function uploadMemoFiles(id: string, files: File[]): Promise<MemoFileItem[]> {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  const { data } = await apiClient.post<MemoFileItem[]>(`${BASE}/${id}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export function memoFileDownloadUrl(memoId: string, fileId: string): string {
  return `/api/v1/memos/${memoId}/files/${fileId}`
}
