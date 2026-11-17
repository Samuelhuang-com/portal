/**
 * Axios instance with JWT interceptor
 */
import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/authStore'

/** 週採目前選的公司代碼（記在 sessionStorage；網址的 co 優先）。 */
const CP_CO_KEY = 'cp_company'
export const getCpCompany = (): string | null => {
  try { return sessionStorage.getItem(CP_CO_KEY) } catch { return null }
}
export const setCpCompany = (code: string | null) => {
  try {
    if (code) sessionStorage.setItem(CP_CO_KEY, code)
    else sessionStorage.removeItem(CP_CO_KEY)
  } catch { /* 無痕或停用儲存時忽略：退回只靠網址 co */ }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor — attach JWT + 禁止瀏覽器快取 API 回應 ────────────────
// 加 Cache-Control: no-cache 防止 Vite proxy 在後端尚未啟動時的 SPA fallback（index.html）
// 被瀏覽器快取，導致後端啟動後仍拿到舊的 HTML 而非真實 API 回應。
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // 防止瀏覽器對 API 回應做 HTTP 快取
  config.headers['Cache-Control'] = 'no-cache'
  config.headers['Pragma'] = 'no-cache'
  // 週採多公司：/cycle-purchase 的請求一律帶上網址的 co（公司代碼），後端以此決定公司範圍
  // 2026-11-17：網址沒有 co（例如點側邊選單換頁後）改讀記住的公司，避免資料退回預設公司
  //             而頂部公司下拉仍顯示舊選擇、兩者不同步。
  if (config.url?.startsWith('/cycle-purchase')) {
    const co = new URLSearchParams(window.location.search).get('co') || getCpCompany()
    if (co) config.params = { co, ...(config.params || {}) }
  }
  return config
})

// ── Response interceptor — handle 401 ────────────────────────────────────────
// 防止同一批請求重複跳轉（例如頁面同時發出多個 API call）
let _redirecting = false

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !_redirecting) {
      _redirecting = true
      useAuthStore.getState().logout()   // 清除 store + localStorage
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default apiClient
