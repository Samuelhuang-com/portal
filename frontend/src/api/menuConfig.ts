/**
 * 選單設定 API 封裝
 * 對應後端 /settings/menu-config
 */
import apiClient from '@/api/client'

export interface MenuConfigItem {
  menu_key: string
  parent_key: string | null
  custom_label: string | null
  sort_order: number
  is_visible: boolean
  // 權限控制：null = 公開顯示；有值 = 需具備對應 permission_key
  permission_key: string | null
}

export interface MenuConfigHistoryItem {
  id: string
  changed_at: string
  changed_by: string
  diff_json: string     // JSON string：[{key, label?, order?}, ...]
  snapshot_json: string // JSON string：MenuConfigItem[]
}

/** 取得目前全部設定 */
export async function fetchMenuConfig(): Promise<MenuConfigItem[]> {
  const res = await apiClient.get<MenuConfigItem[]>('/settings/menu-config')
  return res.data
}

/** 批次儲存設定（覆寫全部） */
export async function saveMenuConfig(items: MenuConfigItem[]): Promise<MenuConfigItem[]> {
  const res = await apiClient.put<MenuConfigItem[]>('/settings/menu-config', { items })
  return res.data
}

/** 取得最近 5 筆變更記錄 */
export async function fetchMenuConfigHistory(): Promise<MenuConfigHistoryItem[]> {
  const res = await apiClient.get<MenuConfigHistoryItem[]>('/settings/menu-config/history')
  return res.data
}
