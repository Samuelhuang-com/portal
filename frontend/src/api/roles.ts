/**
 * 角色管理 API 封裝
 * 對應後端 /api/v1/roles
 */
import apiClient from '@/api/client'

export interface RoleData {
  id: string
  name: string
  scope: string | null
  description: string | null
  is_builtin: boolean
}

export interface RoleCreatePayload {
  name: string
  description?: string
}

/** 取得所有角色清單（內建 + 自訂） */
export async function fetchRoles(): Promise<RoleData[]> {
  const res = await apiClient.get<RoleData[]>('/roles')
  // 防禦性處理：若後端回傳非陣列（如 HTML），回傳空陣列避免崩潰
  if (!Array.isArray(res.data)) return []
  return res.data
}

/** 新增自訂角色 */
export async function createRole(payload: RoleCreatePayload): Promise<RoleData> {
  const res = await apiClient.post<RoleData>('/roles', payload)
  return res.data
}

/** 刪除自訂角色（內建角色後端會拒絕） */
export async function deleteRole(roleId: string): Promise<void> {
  await apiClient.delete(`/roles/${roleId}`)
}
