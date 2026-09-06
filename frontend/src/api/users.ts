import client from './client';
import type { User } from '../types';

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateUserPayload {
  email: string;
  full_name: string;
  password: string;
  tenant_id: string;
  role_names: string[];
  /** 所屬部門（RefDepartment.id 陣列），2026-09-01 多公司多部門 */
  department_ids?: number[];
}

export interface UpdateUserPayload {
  full_name?: string;
  is_active?: boolean;
  role_names?: string[];
  email?: string;        // 僅 system_admin / tenant_admin 可更新
  new_password?: string; // 管理員直接設定新密碼（選填，留空不改）
  tenant_id?: string;    // 主要公司別（＝公司/部門管理的公司），2026-09-01 起可在編輯時變更
  /** 所屬部門整批取代（undefined＝不動、[]＝清空），2026-09-01 多公司多部門 */
  department_ids?: number[];
}

export interface AdminResetPasswordResponse {
  otp: string;
  expires_minutes: number;
  message: string;
}

export interface UserOptionItem {
  value: string   // full_name
  label: string   // full_name
  user_id: string
}

export const usersApi = {
  list: (params?: { page?: number; per_page?: number; tenant_id?: string; search?: string }) =>
    client.get<UserListResponse>('/users', { params }),
  create: (data: CreateUserPayload) =>
    client.post<User>('/users', data),
  update: (id: string, data: UpdateUserPayload) =>
    client.put<User>(`/users/${id}`, data),
  delete: (id: string) =>
    client.delete(`/users/${id}`),
    /** 管理員產生 OTP（僅顯示，需口頭告知使用者） */
  resetPassword: (id: string) =>
    client.post<AdminResetPasswordResponse>(`/users/${id}/reset-password`),
  /** 取得啟用中使用者名稱清單，供 manager/reviewer 下拉使用（任何登入者可呼叫） */
  options: () =>
    client.get<UserOptionItem[]>('/users/options'),
};
