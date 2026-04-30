/**
 * 角色權限 API 封裝
 * 對應後端 /api/v1/role-permissions
 */
import apiClient from '@/api/client'

export interface PermissionKeyDef {
  key: string
  label: string
  group: string
}

export interface RolePermissionsData {
  role_id: string
  role_name: string
  permissions: string[]
}

/** 取得系統所有已知的 permission_key 定義 */
export async function fetchPermissionKeys(): Promise<PermissionKeyDef[]> {
  const res = await apiClient.get<PermissionKeyDef[]>('/role-permissions/keys')
  return res.data
}

/** 取得指定角色的 permission_key 清單 */
export async function fetchRolePermissions(roleId: string): Promise<RolePermissionsData> {
  const res = await apiClient.get<RolePermissionsData>(`/role-permissions/${roleId}`)
  return res.data
}

/** 覆寫指定角色的 permission_key 清單 */
export async function saveRolePermissions(
  roleId: string,
  permissions: string[]
): Promise<RolePermissionsData> {
  const res = await apiClient.put<RolePermissionsData>(`/role-permissions/${roleId}`, {
    permissions,
  })
  return res.data
}
