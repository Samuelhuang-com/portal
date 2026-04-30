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
  // 使用者所有 permission_key 清單；system_admin 為 ["*"]（萬用符）
  permissions?: string[]
  is_active?: boolean
}

interface AuthState {
  token: string | null
  user: AuthUser | null
  setToken: (token: string) => void
  setUser: (user: AuthState['user']) => void
  logout: () => void
  isAuthenticated: boolean
  /**
   * 檢查使用者是否具備指定的 permission_key。
   * - system_admin（permissions=["*"]）永遠回傳 true
   * - permissions 尚未載入（空陣列）時回傳 false
   *
   * 【新模組開發規則】
   * 開發期間在 menuItems 設 permissionKey = 'system_admin_only'，
   * 此 key 不會被加入任何角色，僅 system_admin 可見。
   * 測試完成後改為正確的 permission_key，並在角色管理頁面授予。
   */
  hasPermission: (key: string) => boolean
}

/**
 * 從 JWT token 解析出基本使用者資訊（id / email / roles）。
 * 供頁面重新整理後在呼叫 /me 之前先取得角色，避免閃爍或誤判。
 * 注意：JWT 不包含 permissions，需等 /me API 回應後由 setUser 帶入。
 */
function decodeUserFromToken(token: string | null): AuthUser | null {
  if (!token) return null
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()) return null
    return {
      id:          payload.sub   || '',
      email:       payload.email || '',
      name:        '',
      full_name:   '',
      roles:       Array.isArray(payload.roles) ? payload.roles : [],
      permissions: undefined,  // 需等 /me 回應後才有
    }
  } catch {
    return null
  }
}

const _storedToken = localStorage.getItem('access_token')

export const useAuthStore = create<AuthState>((set, get) => ({
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

  hasPermission: (key: string): boolean => {
    const user = get().user
    if (!user) return false
    const perms = user.permissions
    // permissions 尚未從 /me 載入時，暫以 roles 判斷 system_admin
    if (perms === undefined) {
      return !!(user.roles?.includes('system_admin'))
    }
    // ["*"] = system_admin 萬用符
    if (perms.includes('*')) return true
    return perms.includes(key)
  },
}))
