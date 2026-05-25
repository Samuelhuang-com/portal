/**
 * Axios instance with JWT interceptor
 */
import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/authStore'

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
