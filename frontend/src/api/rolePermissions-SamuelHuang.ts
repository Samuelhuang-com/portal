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

/** 取得被鎖定為「限系統管理員」的模組群組（2026-09-30） */
export async function fetchLockedGroups(): Promise<string[]> {
  const res = await apiClient.get<string[]>('/role-permissions/locked-groups')
  return Array.isArray(res.data) ? res.data : []
}

/** 整批取代鎖定群組清單（僅系統管理員） */
export async function saveLockedGroups(groups: string[]): Promise<string[]> {
  const res = await apiClient.put<string[]>('/role-permissions/locked-groups', { groups })
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
