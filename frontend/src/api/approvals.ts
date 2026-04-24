/**
 * 簽核系統 API functions
 * 對應後端 /api/v1/approvals/*
 */
import apiClient from './client'
import type {
  ApprovalCreatePayload,
  ApprovalDetail,
  ApprovalFilters,
  ApprovalListResponse,
  ApprovalSearchItem,
  ApproverOption,
} from '@/types/approval'

const BASE = '/approvals'

// ── 清單 ─────────────────────────────────────────────────────────────────────

export async function fetchApprovals(
  filters: ApprovalFilters = {},
): Promise<ApprovalListResponse> {
  const { data } = await apiClient.get<ApprovalListResponse>(BASE, { params: filters })
  return data
}

// ── 搜尋（清單頁即時查詢） ─────────────────────────────────────────────────────

export async function searchApprovals(params: {
  q?: string
  scope?: string
  status?: string
  date_from?: string
  date_to?: string
  limit?: number
}): Promise<ApprovalSearchItem[]> {
  const { data } = await apiClient.get<ApprovalSearchItem[]>(`${BASE}/search`, { params })
  return data
}

// ── 詳情 ─────────────────────────────────────────────────────────────────────

export async function fetchApproval(id: string): Promise<ApprovalDetail> {
  const { data } = await apiClient.get<ApprovalDetail>(`${BASE}/${id}`)
  return data
}

// ── 新增（JSON，無附件） ──────────────────────────────────────────────────────

export async function createApproval(
  payload: ApprovalCreatePayload,
): Promise<ApprovalDetail> {
  const { data } = await apiClient.post<ApprovalDetail>(BASE, payload)
  return data
}

// ── 新增（multipart，含附件） ─────────────────────────────────────────────────

export async function createApprovalWithFiles(
  payload: ApprovalCreatePayload,
  files: File[],
): Promise<ApprovalDetail> {
  const form = new FormData()
  form.append('subject', payload.subject)
  form.append('description', payload.description)
  form.append('confidential', payload.confidential)
  form.append('requester_dept', payload.requester_dept)
  form.append('view_scope', payload.view_scope)
  form.append('publish_memo', String(payload.publish_memo))
  form.append('approver_chain', JSON.stringify(payload.approver_chain))
  files.forEach((f) => form.append('files', f))

  const { data } = await apiClient.post<ApprovalDetail>(`${BASE}/with-files`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ── 簽核動作 ─────────────────────────────────────────────────────────────────

export async function doApprovalAction(
  id: string,
  action: 'approve' | 'reject',
  comment: string,
): Promise<void> {
  await apiClient.post(`${BASE}/${id}/action`, { action, comment })
}

// ── 調整關卡順序 ─────────────────────────────────────────────────────────────

export async function reorderSteps(id: string, order: string[]): Promise<void> {
  await apiClient.post(`${BASE}/${id}/steps/reorder`, { order })
}

// ── 插入關卡 ─────────────────────────────────────────────────────────────────

export async function addStep(
  id: string,
  approver: ApproverOption,
  insertAfter = -1,
): Promise<void> {
  await apiClient.post(`${BASE}/${id}/steps/add`, {
    approver,
    insert_after: insertAfter,
  })
}

// ── 移除關卡 ─────────────────────────────────────────────────────────────────

export async function removeStep(approvalId: string, stepId: string): Promise<void> {
  await apiClient.delete(`${BASE}/${approvalId}/steps/${stepId}`)
}

// ── 上傳附件 ─────────────────────────────────────────────────────────────────

export async function uploadFiles(approvalId: string, files: File[]): Promise<void> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f))
  await apiClient.post(`${BASE}/${approvalId}/files`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── 附件下載 URL ─────────────────────────────────────────────────────────────

export function fileDownloadUrl(approvalId: string, fileId: string): string {
  return `/api/v1/approvals/${approvalId}/files/${fileId}`
}

// ── 可選簽核人 ────────────────────────────────────────────────────────────────

export async function fetchApprovers(q = ''): Promise<ApproverOption[]> {
  const { data } = await apiClient.get<ApproverOption[]>(`${BASE}/approvers`, {
    params: { q },
  })
  return data
}
