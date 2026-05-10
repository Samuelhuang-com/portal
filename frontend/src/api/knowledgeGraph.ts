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

/** 觸發知識圖譜產生（BackgroundTask），回傳 { message } */
export async function triggerGenerate(): Promise<{ message: string }> {
  const { data } = await client.post<{ message: string }>('/knowledge-graph/generate')
  return data
}
