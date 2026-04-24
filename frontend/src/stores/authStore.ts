/**
 * Auth Zustand store
 */
import { create } from 'zustand'

export interface AuthUser {
  id: string
  email: string
  name: string
  full_name: string
  tenant_id?: string
  tenant_name?: string
  roles: string[]
  is_active?: boolean
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setToken: (token: string) => void
  setUser: (user: AuthState['user']) => void
  logout: () => void
  isAuthenticated: boolean
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('access_token'),
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),

  setToken: (token) => {
    localStorage.setItem('access_token', token)
    set({ token, isAuthenticated: true })
  },

  setUser: (user) => set({ user }),

  logout: () => {
    localStorage.removeItem('access_token')
    set({ token: null, user: null, isAuthenticated: false })
  },
}))
