/**
 * 影音教學（單集影片）API functions
 * 對應後端 /api/v1/tutorial-videos/*（本地模組，不對接 Ragic）
 */
import apiClient from './client'
import type {
  TutorialVideoCategory,
  TutorialVideoItem,
  TutorialVideoListResponse,
  TutorialVideoUpdatePayload,
  TutorialVideoUploadPayload,
} from '@/types/tutorial_video'

const BASE = '/tutorial-videos'

export async function fetchTutorialVideos(params: { category?: TutorialVideoCategory; module_id?: string } = {}): Promise<TutorialVideoListResponse> {
  const { data } = await apiClient.get<TutorialVideoListResponse>(BASE, { params })
  return data
}

export async function fetchTutorialVideo(id: string): Promise<TutorialVideoItem> {
  const { data } = await apiClient.get<TutorialVideoItem>(`${BASE}/${id}`)
  return data
}

export async function uploadTutorialVideo(payload: TutorialVideoUploadPayload): Promise<TutorialVideoItem> {
  const formData = new FormData()
  formData.append('module_id', payload.module_id)
  formData.append('episode', payload.episode ?? '')
  formData.append('title', payload.title)
  formData.append('description', payload.description ?? '')
  if (payload.sort_order !== undefined) {
    formData.append('sort_order', String(payload.sort_order))
  }
  formData.append('video_file', payload.video_file)
  if (payload.script_file) {
    formData.append('script_file', payload.script_file)
  }
  const { data } = await apiClient.post<TutorialVideoItem>(BASE, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function updateTutorialVideo(id: string, payload: TutorialVideoUpdatePayload): Promise<TutorialVideoItem> {
  const { data } = await apiClient.patch<TutorialVideoItem>(`${BASE}/${id}`, payload)
  return data
}

export async function deleteTutorialVideo(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}

export async function reorderTutorialVideos(moduleId: string, orderedIds: string[]): Promise<void> {
  await apiClient.put(`${BASE}/${moduleId}/videos/reorder`, { ordered_ids: orderedIds })
}

/** <video> 標籤播放用網址（帶 ?token= 供瀏覽器直接播放，與匯出下載相同慣例） */
export function tutorialVideoStreamUrl(id: string): string {
  const token = localStorage.getItem('access_token') ?? ''
  return `/api/v1/tutorial-videos/${id}/stream?token=${encodeURIComponent(token)}`
}

export function tutorialVideoScriptUrl(id: string): string {
  return `/api/v1/tutorial-videos/${id}/script`
}
