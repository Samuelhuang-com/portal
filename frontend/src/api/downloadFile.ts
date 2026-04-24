/**
 * downloadFile / openFile — 帶 JWT Auth 的檔案下載 / 開啟工具
 *
 * 使用原生 fetch（非 apiClient），避免 apiClient.baseURL 重複拼接
 * （fileDownloadUrl / memoFileDownloadUrl 已回傳完整 /api/v1/... 路徑）
 */
import { message } from 'antd'

/** 取得 JWT token（與 apiClient 使用相同 key） */
function getToken(): string {
  return localStorage.getItem('access_token') ?? ''
}

/** 用 fetch + Bearer token 取得 Blob；失敗時拋出 Error */
async function fetchBlob(url: string): Promise<{ blob: Blob; contentType: string }> {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  const blob = await res.blob()
  const contentType = res.headers.get('content-type') ?? 'application/octet-stream'
  return { blob, contentType }
}

/**
 * 用 fetch（帶 JWT）下載檔案並存到磁碟。
 * 下載完成後瀏覽器會在下載列顯示，使用者可進一步選擇「開啟」。
 *
 * @param url       後端 API 完整路徑（如 /api/v1/memos/{id}/files/{fileId}）
 * @param filename  存檔時的預設檔名（支援中文）
 */
export async function downloadFile(url: string, filename: string): Promise<void> {
  try {
    const { blob, contentType } = await fetchBlob(url)
    const objectUrl = URL.createObjectURL(new Blob([blob], { type: contentType }))
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename          // 瀏覽器使用此檔名存檔（中文亦可）
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(objectUrl), 10_000)
  } catch {
    message.error(`下載失敗：${filename}`)
  }
}

/**
 * 用 fetch（帶 JWT）取得 Blob 後，在新分頁中開啟。
 * - 瀏覽器可顯示格式（PDF、圖片）：直接在新分頁預覽
 * - 其他格式（xlsx、docx…）：瀏覽器觸發下載，系統自動用預設程式開啟
 *
 * @param url       後端 API 完整路徑
 * @param filename  下載時的預設檔名（瀏覽器無法預覽時使用）
 */
export async function openFile(url: string, filename: string): Promise<void> {
  try {
    const { blob, contentType } = await fetchBlob(url)
    const objectUrl = URL.createObjectURL(new Blob([blob], { type: contentType }))
    const win = window.open(objectUrl, '_blank')
    if (!win) {
      // 被 popup blocker 擋住時，退回成下載
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
    setTimeout(() => URL.revokeObjectURL(objectUrl), 30_000)
  } catch {
    message.error(`開啟失敗：${filename}`)
  }
}
