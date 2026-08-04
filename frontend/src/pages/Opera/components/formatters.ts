/**
 * OPERA 營運分析 — 共用格式化與色票
 *
 * 數字格式規範（規格書 §16.4）：
 *   金額 → 千分位、無小數
 *   百分比 → 一位小數
 *   房晚／筆數 → 整數千分位
 *   空值 → —
 */

// ── 色票（取自 CLAUDE.md 受保護色碼，不得新增其他色）────────────────────────
export const BRAND = '#1B3A5C'        // 品牌主色
export const ACCENT = '#4BA8E8'       // 輔色
export const GREEN = '#52c41a'        // 正向
export const ORANGE = '#faad14'       // 警示
export const RED = '#e74c3c'          // 異常
export const GREY = '#bfbfbf'         // 去年對照
export const PURPLE = '#764ba2'       // 圖表第五色（沿用專案既有漸層色）

/** 圓餅／多序列圖表用的色序 */
export const CHART_COLORS = [BRAND, ACCENT, GREEN, ORANGE, PURPLE, RED, '#667eea', GREY]

export const EMPTY = '—'

// ── 數字 ─────────────────────────────────────────────────────────────────────

export function fmtMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY
  return Math.round(value).toLocaleString('en-US')
}

export function fmtInt(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY
  return Math.round(value).toLocaleString('en-US')
}

/** 0.6772 → "67.7%" */
export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY
  return `${(value * 100).toFixed(digits)}%`
}

/** 百分點差：0.031 → "+3.1 ppt" */
export function fmtPpt(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY
  const v = value * 100
  return `${v >= 0 ? '+' : ''}${v.toFixed(digits)} ppt`
}

/** YoY：0.083 → "+8.3%"；null → "—"（無比較期資料） */
export function fmtYoY(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY
  const v = value * 100
  return `${v >= 0 ? '+' : ''}${v.toFixed(digits)}%`
}

export function fmtText(value: string | null | undefined): string {
  const v = (value ?? '').trim()
  return v === '' ? EMPTY : v
}

export function fmtBytes(bytes: number | null | undefined): string {
  if (!bytes) return EMPTY
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** 漲跌色：營收／ADR 類指標上升為好（綠），下降為差（紅） */
export function trendColor(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return 'inherit'
  if (value > 0) return GREEN
  if (value < 0) return RED
  return 'inherit'
}

// ── Tag 色 ───────────────────────────────────────────────────────────────────

export const QUALITY_TAG: Record<string, { color: string; text: string }> = {
  PASS:               { color: 'success', text: 'PASS' },
  PASS_WITH_WARNINGS: { color: 'warning', text: 'PASS（有警示）' },
  FAIL:               { color: 'error',   text: 'FAIL' },
}

export const STATUS_TAG: Record<string, { color: string; text: string }> = {
  PENDING:     { color: 'default',    text: '處理中' },
  VALIDATED:   { color: 'processing', text: '已驗證' },
  COMMITTED:   { color: 'success',    text: '已匯入' },
  FAILED:      { color: 'error',      text: '失敗' },
  ROLLED_BACK: { color: 'default',    text: '已復原' },
}

export const TRIGGER_TAG: Record<string, string> = {
  固定門檻: 'blue',
  年度基準: 'orange',
  兩者:     'red',
}

export const RECORD_TYPE_TAG: Record<string, { color: string; text: string }> = {
  History:  { color: 'blue',   text: 'History（實績）' },
  Forecast: { color: 'purple', text: 'Forecast（預測）' },
}

/** 期間型態 Tag（規格書 §9.2：畫面必須明示目前是完整期還是 MTD/YTD） */
export function periodTagColor(periodType: string): string {
  switch (periodType) {
    case 'FULL_YEAR':
    case 'FULL_MONTH':
      return 'green'
    case 'PARTIAL_YEAR':
    case 'PARTIAL_MONTH':
      return 'orange'
    default:
      return 'default'
  }
}

// ── 日期 ─────────────────────────────────────────────────────────────────────

export function monthLabel(iso: string): string {
  // "2026-03" → "2026/03"
  return iso.replace('-', '/')
}

export function shortDate(iso: string): string {
  // "2026-03-15" → "03/15"
  const parts = iso.split('-')
  return parts.length === 3 ? `${parts[1]}/${parts[2]}` : iso
}
