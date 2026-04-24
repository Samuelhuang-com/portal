import client from './client';
import type { User } from '../types';

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  login: (identifier: string, password: string) =>
    client.post<LoginResponse>('/auth/login', { identifier, password }),
  me: () =>
    client.get<User>('/auth/me'),
  logout: () =>
    client.post('/auth/logout'),
  changePassword: (old_password: string, new_password: string) =>
    client.post('/users/me/change-password', { old_password, new_password }),
};
