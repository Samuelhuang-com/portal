/**
 * 金旭分析 — 共用常數與格式化
 * 規格書 §13.8（樣式受保護，不得修改品牌色）
 */
import type { NightsBasis } from '@/types/jinxu'

/** 科目大類配色（規格書 §13.8） */
export const GROUP_COLORS: Record<string, string> = {
  ROOM: '#1B3A5C',
  SERVICE: '#4BA8E8',
  TELECOM: '#95a5a6',
  DEPOSIT_IN: '#f39c12',
  DEPOSIT_OUT: '#f39c12',
  OTHER_REV: '#bdc3c7',
  CARD: '#667eea',
  EPAY: '#764ba2',
  CASH: '#27ae60',
  AR: '#e67e22',
  OTHER_SET: '#bdc3c7',
  UNCLASSIFIED: '#e74c3c',
}

/** 訂房狀態配色（規格書 §13.8） */
export const STATUS_COLORS: Record<string, string> = {
  'ACTV-CO': 'success',
  'ACTV-IH': 'processing',
  'ACTV-RV': 'warning',
  'CNFM-RV': 'warning',
  'CXNL-RV': 'error',
  'NOSH-RV': 'orange',
  'DUMY-RV': 'default',
}

export const CHART_PALETTE = [
  '#1B3A5C', '#4BA8E8', '#667eea', '#764ba2', '#27ae60',
  '#e67e22', '#f39c12', '#95a5a6', '#e74c3c', '#16a085',
  '#8e44ad', '#2c3e50', '#d35400', '#7f8c8d', '#c0392b',
]

/**
 * J27：住宿晚數口徑。
 * 業主 2026-08-05 決定**預設 billable**（Day Use 算 1 晚，與房租認列一致）。
 */
export const NIGHTS_BASIS_DEFAULT: NightsBasis = 'billable'

export const NIGHTS_BASIS_OPTIONS = [
  { value: 'billable' as NightsBasis, label: '含 Day Use（算 1 晚）' },
  { value: 'nights' as NightsBasis, label: '純日期差（Day Use 算 0 晚）' },
]

export const fmtInt = (v: number | null | undefined): string =>
  v === null || v === undefined ? '—' : Math.round(v).toLocaleString('en-US')

export const fmtMoney = (v: number | null | undefined): string =>
  v === null || v === undefined ? '—' : `$${Math.round(v).toLocaleString('en-US')}`

export const fmtPct = (v: number | null | undefined, digits = 1): string =>
  v === null || v === undefined ? '—' : `${v.toFixed(digits)}%`

export const dash = (v: unknown): string => {
  if (v === null || v === undefined) return '—'
  const s = String(v).trim()
  return s === '' ? '—' : s
}

/** 金額為負時上紅字（規格書 §13.7 渲染規則） */
export const moneyStyle = (v: number): React.CSSProperties =>
  v < 0 ? { color: '#cf1322' } : {}
