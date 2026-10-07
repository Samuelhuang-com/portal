/**
 * 專案知識圖譜 API
 * 對應後端 /api/v1/knowledge-graph/
 */
import client from './client'

export type GraphStatus = 'idle' | 'generating' | 'ready'

export interface KnowledgeGraphStatus {
  status: GraphStatus
  generated_at: string | null
  html_exists: boolean
  error: string | null
}

/** 查詢圖譜狀態 */
export async function fetchGraphStatus(): Promise<KnowledgeGraphStatus> {
  const { data } = await client.get<KnowledgeGraphStatus>('/knowledge-graph/status')
  return data
}

/**
 * 取得已產生的圖譜 HTML 內容（走 JWT 驗證的 /knowledge-graph/result）。
 * 2026-10-07：原本 iframe 直接指向 /kg-files/graph.html，但後端該靜態掛載已不存在，
 * 正式區會落到 SPA fallback（iframe 裡出現 Portal 本身）。改為帶 token 取回內容，
 * 由 iframe srcDoc 呈現。
 */
export async function fetchGraphHtml(): Promise<string> {
  const { data } = await client.get<string>('/knowledge-graph/result', {
    responseType: 'text',
    timeout: 120_000, // 檔案約 2MB
  })
  return data
}

/** 觸發知識圖譜產生（BackgroundTask），回傳 { message } */
export async function triggerGenerate(): Promise<{ message: string }> {
  const { data } = await client.post<{ message: string }>('/knowledge-graph/generate')
  return data
}
