export type WikiCategory = 'sop' | 'dev' | 'all'

export interface WikiArticle {
  id: string
  title: string
  slug: string
  body: string
  summary: string
  category: 'sop' | 'dev'
  tags: string[]
  author: string
  author_id: string
  is_published: boolean
  created_at: string
  updated_at: string
}

export interface WikiListResponse {
  items: WikiArticle[]
  total: number
  page: number
  per_page: number
}

export interface WikiArticleCreate {
  title: string
  body: string
  category: 'sop' | 'dev'
  tags: string[]
  summary?: string
  is_published?: boolean
}

export interface WikiArticleUpdate {
  title?: string
  body?: string
  category?: 'sop' | 'dev'
  tags?: string[]
  summary?: string
  is_published?: boolean
}

export interface WikiAskRequest {
  question: string
  category?: WikiCategory
}

export interface WikiAskResponse {
  answer: string
  sources: WikiArticle[]
  model_used: string | null
}
