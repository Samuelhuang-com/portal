/**
 * 教學模組主檔 API functions
 * 對應後端 /api/v1/tutorial-videos/modules/*（本地模組，不對接 Ragic）
 */
import apiClient from './client'
import type {
  TutorialVideoCategory,
  TutorialVideoModuleCreatePayload,
  TutorialVideoModuleItem,
  TutorialVideoModuleUpdatePayload,
} from '@/types/tutorial_video'

const BASE = '/tutorial-videos/modules'

export async function fetchTutorialVideoModules(category?: TutorialVideoCategory): Promise<TutorialVideoModuleItem[]> {
  const { data } = await apiClient.get<TutorialVideoModuleItem[]>(BASE, {
    params: category ? { category } : {},
  })
  return data
}

export async function createTutorialVideoModule(payload: TutorialVideoModuleCreatePayload): Promise<TutorialVideoModuleItem> {
  const { data } = await apiClient.post<TutorialVideoModuleItem>(BASE, payload)
  return data
}

export async function updateTutorialVideoModule(id: string, payload: TutorialVideoModuleUpdatePayload): Promise<TutorialVideoModuleItem> {
  const { data } = await apiClient.patch<TutorialVideoModuleItem>(`${BASE}/${id}`, payload)
  return data
}

export async function deleteTutorialVideoModule(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}

export async function reorderTutorialVideoModules(category: TutorialVideoCategory, orderedIds: string[]): Promise<void> {
  await apiClient.put(`${BASE}/reorder`, { category, ordered_ids: orderedIds })
}
