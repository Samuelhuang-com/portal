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
};
