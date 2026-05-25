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
}

export interface UpdateUserPayload {
  full_name?: string;
  is_active?: boolean;
  role_names?: string[];
  email?: string;  // 僅 system_admin / tenant_admin 可更新
}

export interface AdminResetPasswordResponse {
  otp: string;
  expires_minutes: number;
  message: string;
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
};
