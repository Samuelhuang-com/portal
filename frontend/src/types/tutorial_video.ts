/**
 * 影音教學 TypeScript 型別定義
 * 對應後端 /api/v1/tutorial-videos/*（本地模組，不對接 Ragic）
 */

export type TutorialVideoCategory = 'hotel' | 'mall' | 'group'

// ── 教學模組主檔 ──────────────────────────────────────────────────────────────

export interface TutorialVideoModuleItem {
  id: string
  category: TutorialVideoCategory
  module_name: string
  module_route: string
  sort_order: number
  video_count: number
  created_at: string
  updated_at: string
}

export interface TutorialVideoModuleCreatePayload {
  category: TutorialVideoCategory
  module_name: string
  module_route?: string
}

export interface TutorialVideoModuleUpdatePayload {
  category?: TutorialVideoCategory
  module_name?: string
  module_route?: string
}

// ── 單集影片 ──────────────────────────────────────────────────────────────────

export interface TutorialVideoItem {
  id: string
  module_id: string
  episode: string
  title: string
  description: string
  video_orig_name: string
  video_size_bytes: number
  script_orig_name: string
  sort_order: number
  uploaded_by: string
  created_at: string
  updated_at: string
}

export interface TutorialVideoListResponse {
  items: TutorialVideoItem[]
  total: number
}

export interface TutorialVideoUploadPayload {
  module_id: string
  episode?: string
  title: string
  description?: string
  sort_order?: number
  video_file: File
  script_file?: File
}

export interface TutorialVideoUpdatePayload {
  module_id?: string
  episode?: string
  title?: string
  description?: string
  sort_order?: number
}
