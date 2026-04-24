/**
 * 公告系統 TypeScript 型別定義
 * 對應後端 /api/v1/memos
 */

export type MemoVisibility = 'org' | 'restricted'

export interface MemoFileItem {
  id: string
  orig_name: string
  content_type: string
  size_bytes: number
  uploaded_by: string
  uploaded_at: string
}

export interface MemoListItem {
  id: string
  title: string
  preview: string         // 前 160 字純文字
  visibility: MemoVisibility
  author: string
  doc_no: string
  recipient: string
  source: string          // 'manual' | 'approval'
  source_id: string
  created_at: string
}

export interface MemoListResponse {
  items: MemoListItem[]
  total: number
  page: number
  per_page: number
}

export interface MemoDetail {
  id: string
  title: string
  body: string            // HTML / 純文字
  visibility: MemoVisibility
  author: string
  author_id: string
  doc_no: string
  recipient: string
  source: string
  source_id: string
  created_at: string
  updated_at: string
  attachments: MemoFileItem[]
}

export interface MemoCreatePayload {
  title: string
  body: string
  visibility: MemoVisibility
  doc_no: string
  recipient: string
}

export interface MemoUpdatePayload {
  title?: string
  body?: string
  visibility?: MemoVisibility
  doc_no?: string
  recipient?: string
}

export interface MemoFilters {
  q?: string
  visibility?: 'all' | MemoVisibility
  page?: number
  per_page?: number
}
