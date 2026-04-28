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

/**
 * 從 JWT token 解析出基本使用者資訊（id / email / roles）。
 * 供頁面重新整理後在呼叫 /me 之前先取得角色，避免閃爍或誤判。
 */
function decodeUserFromToken(token: string | null): AuthUser | null {
  if (!token) return null
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()) return null
    return {
      id:        payload.sub   || '',
      email:     payload.email || '',
      name:      '',
      full_name: '',
      roles:     Array.isArray(payload.roles) ? payload.roles : [],
    }
  } catch {
    return null
  }
}

const _storedToken = localStorage.getItem('access_token')

export const useAuthStore = create<AuthState>((set) => ({
  token: _storedToken,
  user: decodeUserFromToken(_storedToken),
  isAuthenticated: !!_storedToken,

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
