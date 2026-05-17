/**
 * 靜態頁面 API
 */
import apiClient from './client'

export interface StaticPageItem {
  filename: string
  url: string
}

export async function fetchStaticPages(): Promise<StaticPageItem[]> {
  const res = await apiClient.get<StaticPageItem[]>('/settings/static-pages')
  return res.data
}
