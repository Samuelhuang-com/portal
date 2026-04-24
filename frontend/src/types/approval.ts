/**
 * 簽核系統 TypeScript 型別定義
 * 對應後端 /api/v1/approvals
 */

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'
export type ViewScope     = 'org' | 'restricted' | 'top_secret'
export type StepStatus    = 'pending' | 'approved' | 'rejected'

// ── 關卡 ─────────────────────────────────────────────────────────────────────

export interface ApprovalStep {
  id: string
  step_order: number
  approver_id: string
  approver_name: string
  approver_email: string
  status: StepStatus
  decided_at: string | null
  comment: string
}

// ── 歷程 ─────────────────────────────────────────────────────────────────────

export interface ApprovalAction {
  id: string
  step_id: string | null
  actor: string
  actor_id: string
  action: string
  note: string
  created_at: string
}

// ── 附件 ─────────────────────────────────────────────────────────────────────

export interface ApprovalFile {
  id: string
  orig_name: string
  content_type: string
  size_bytes: number
  uploaded_by: string
  uploaded_at: string
}

// ── 清單項目 ─────────────────────────────────────────────────────────────────

export interface ApprovalListItem {
  id: string
  subject: string
  requester: string
  requester_id: string
  status: ApprovalStatus
  current_step: number
  submitted_at: string
  updated_at: string
}

export interface ApprovalListResponse {
  items: ApprovalListItem[]
  total: number
}

// ── 詳情 ─────────────────────────────────────────────────────────────────────

export interface ApprovalDetail {
  id: string
  subject: string
  description: string
  confidential: string
  requester: string
  requester_id: string
  requester_dept: string
  status: ApprovalStatus
  current_step: number
  view_scope: ViewScope
  publish_memo: number
  submitted_at: string
  updated_at: string
  steps: ApprovalStep[]
  actions: ApprovalAction[]
  attachments: ApprovalFile[]
  can_act: boolean
  can_manage: boolean
}

// ── 搜尋結果 ─────────────────────────────────────────────────────────────────

export interface ApprovalSearchItem {
  id: string
  subject: string
  requester: string
  status: ApprovalStatus
  current_step: number
  submitted_at: string
  preview: string
  current_approver_name: string   // 目前待簽關卡的簽核人姓名（pending 時有值）
}

// ── 可選簽核人 ────────────────────────────────────────────────────────────────

export interface ApproverOption {
  user_id: string
  name: string
  email: string
}

// ── 建立表單用 ────────────────────────────────────────────────────────────────

export interface ApproverIn {
  user_id: string
  name: string
  email: string
}

export interface ApprovalCreatePayload {
  subject: string
  description: string
  confidential: string
  requester_dept: string
  view_scope: ViewScope
  publish_memo: number
  approver_chain: ApproverIn[]
}

// ── 查詢篩選 ─────────────────────────────────────────────────────────────────

export interface ApprovalFilters {
  scope?: 'all' | 'mine' | 'todo'
  status?: 'all' | 'pending' | 'approved' | 'rejected'
  q?: string
  date_from?: string
  date_to?: string
  page?: number
  per_page?: number
}
