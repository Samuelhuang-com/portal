import client from './client';
import type { User } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
  must_change_password: boolean;
}

export const authApi = {
  login: (identifier: string, password: string) =>
    client.post<LoginResponse>('/auth/login', { identifier, password }),
  me: () =>
    client.get<User>('/auth/me'),
  logout: () =>
    client.post('/auth/logout'),
  /** 一般改密碼（需舊密碼） */
  changePassword: (old_password: string, new_password: string) =>
    client.post('/users/me/change-password', { old_password, new_password }),
  /** OTP 登入後強制改密碼（免舊密碼） */
  changePasswordForced: (new_password: string) =>
    client.post('/users/me/change-password', { new_password }),
  /** 申請忘記密碼 OTP（真實 email 才能使用） */
  forgotPassword: (identifier: string) =>
    client.post<{ message: string }>('/auth/forgot-password', { identifier }),
};
