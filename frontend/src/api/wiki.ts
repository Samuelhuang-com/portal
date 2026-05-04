import apiClient from './client'
import type {
  WikiArticle,
  WikiArticleCreate,
  WikiArticleUpdate,
  WikiAskRequest,
  WikiAskResponse,
  WikiCategory,
  WikiListResponse,
} from '@/types/wiki'

const BASE = '/wiki'

export async function fetchWikiArticles(params: {
  q?: string
  category?: WikiCategory
  page?: number
  per_page?: number
  published_only?: boolean
}): Promise<WikiListResponse> {
  const { data } = await apiClient.get<WikiListResponse>(BASE, { params })
  return data
}

export async function fetchWikiArticle(id: string): Promise<WikiArticle> {
  const { data } = await apiClient.get<WikiArticle>(`${BASE}/${id}`)
  return data
}

export async function createWikiArticle(
  payload: WikiArticleCreate,
): Promise<WikiArticle> {
  const { data } = await apiClient.post<WikiArticle>(BASE, payload)
  return data
}

export async function updateWikiArticle(
  id: string,
  payload: WikiArticleUpdate,
): Promise<WikiArticle> {
  const { data } = await apiClient.patch<WikiArticle>(`${BASE}/${id}`, payload)
  return data
}

export async function deleteWikiArticle(id: string): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}

export async function askWiki(payload: WikiAskRequest): Promise<WikiAskResponse> {
  const { data } = await apiClient.post<WikiAskResponse>(`${BASE}/ask`, payload)
  return data
}

// ── 圖譜 ──────────────────────────────────────────────────────────────────────

export interface WikiGraphNode {
  id: string
  title: string
  slug: string
  category: 'sop' | 'dev'
  tags: string[]
  summary: string
}

export interface WikiGraphEdge {
  source: string
  target: string
  type: 'tag' | 'link'
  shared_tags?: string[]
}

export interface WikiGraphData {
  nodes: WikiGraphNode[]
  edges: WikiGraphEdge[]
}

export async function autoLinkArticles(dryRun = false): Promise<{
  updated: number
  skipped: number
  plan: { id: string; title: string; links: string[] }[]
  dry_run: boolean
}> {
  const { data } = await apiClient.post(`${BASE}/auto-link`, null, { params: { dry_run: dryRun } })
  return data
}

export async function fetchWikiGraph(
  category: 'sop' | 'dev' | 'all' = 'all',
): Promise<WikiGraphData> {
  const { data } = await apiClient.get<WikiGraphData>(`${BASE}/graph`, { params: { category } })
  return data
}

// ── Obsidian 同步 ─────────────────────────────────────────────────────────────

export interface ObsidianSyncResult {
  exported: number
  imported: number
  updated: number
  skipped: number
  errors: string[]
  wiki_dir: string
  message: string
}

export async function exportToObsidian(): Promise<ObsidianSyncResult> {
  const { data } = await apiClient.post<ObsidianSyncResult>(`${BASE}/export-obsidian`)
  return data
}

export async function importFromObsidian(): Promise<ObsidianSyncResult> {
  const { data } = await apiClient.post<ObsidianSyncResult>(`${BASE}/import-obsidian`)
  return data
}
