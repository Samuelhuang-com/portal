/**
 * 員工操作手冊匯出 — API 封裝
 */
import apiClient from './client'
import type { ModuleInfo, GenerateRequest, GenerateResult, ExportStatus } from '@/types/employeeManualExport'

const BASE = '/employee-manual-export'

/** 取得所有可選模組清單 */
export async function fetchModuleList(): Promise<ModuleInfo[]> {
  const res = await apiClient.get(`${BASE}/modules`)
  return res.data.data
}

/** 產生指定模組的操作手冊文件 */
export async function generateManual(payload: GenerateRequest): Promise<GenerateResult> {
  const res = await apiClient.post(`${BASE}/generate`, payload)
  return res.data.data
}

/** 查詢指定模組的匯出狀態 */
export async function fetchExportStatus(moduleKey: string): Promise<ExportStatus> {
  const res = await apiClient.get(`${BASE}/status/${moduleKey}`)
  return res.data.data
}

/** 取得 ZIP 下載 URL（直接返回帶 token 的完整 URL 供瀏覽器下載） */
export function getDownloadUrl(moduleKey: string): string {
  const token = localStorage.getItem('access_token') ?? ''
  const base = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1'
  return `${base}/employee-manual-export/download/${moduleKey}?token=${encodeURIComponent(token)}`
}

/** 觸發瀏覽器下載 ZIP（使用 blob 方式，附帶 Authorization header） */
export async function downloadManualZip(moduleKey: string, moduleName: string): Promise<void> {
  const res = await apiClient.get(`${BASE}/download/${moduleKey}`, {
    responseType: 'blob',
  })

  const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/zip' }))
  const link = document.createElement('a')
  link.href = url
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  link.download = `員工操作手冊_${moduleName}_${today}.zip`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}
