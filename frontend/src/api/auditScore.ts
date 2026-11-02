/**
 * 稽核檢查統計（合併計分）API — 後端 /api/v1/audit-check/score
 */
import client from './client'

export interface AuditScoreMonthly {
  period: string
  source: '稽核檢查' | 'KPO'
  source_sheet_id: number
  sub: number
  pass: number
  module_score: number | null   // 原模組分數：稽核為 0~1，KPO 為 0~100
  module_label: string          // 原模組畫面文字
}

export interface AuditScoreRow {
  department: string
  audit_sub: number
  audit_pass: number
  kpo_sub: number
  kpo_pass: number
  total_sub: number
  total_pass: number
  rate: number | null
  audit_months: number
  kpo_months: number
  monthly: AuditScoreMonthly[]
}

export interface AuditScoreBlock {
  company_id: number
  company_name: string
  rows: AuditScoreRow[]
}

export interface AuditScoreResponse {
  year: number
  blocks: AuditScoreBlock[]
}

export const getAuditScore = (year: number) =>
  client.get<AuditScoreResponse>('/audit-check/score', { params: { year } })

export const exportAuditScore = (year: number) =>
  client.get<Blob>('/audit-check/score/export', { params: { year }, responseType: 'blob' })
