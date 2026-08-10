/**
 * OPERA 營運分析 — 含「與去年同期增減」的共用圖表 Tooltip
 *
 * 用途：Dashboard 上凡是同時畫了「本年 X」與「去年 X」兩條序列的圖表，
 *       滑鼠移過去時除了原本的數值，再多一行增減值 + 增減百分比，
 *       讓使用者一眼看出比去年同期是增加還是減少。
 *
 * 比較基準：去年同期（YoY），與 KPI 卡的 YoY 口徑一致，不是上個月（MoM）。
 *
 * 顯示規則：
 *   增減值    → 上升綠、下降紅、持平不上色（沿用 formatters.trendColor）
 *   百分比    → diff / |去年值| × 100，一位小數
 *   去年值為 0 或無比較期資料 → 該行顯示 —（不顯示無意義的 ∞%）
 *   diffMode='ppt' → 本身已是百分比的指標（住房率），增減值用百分點表示
 */
import React from 'react'

import { EMPTY, GREY, trendColor } from './formatters'

export interface CompareMetric {
  /** 顯示用的指標名稱，例如「營收」「ADR」「住房率」 */
  label: string
  /** 本年序列的 dataKey，例如「本年營收」 */
  currentKey: string
  /** 去年序列的 dataKey，例如「去年營收」 */
  compareKey: string
  /** 指標代表色（沿用圖表上該序列的顏色） */
  color: string
  /** 數值格式化，預設千分位整數 */
  format?: (v: number) => string
  /**
   * 增減值的呈現方式
   *   'number' → 一般數值差（營收、ADR）
   *   'ppt'    → 百分點差（住房率這類本身已是 % 的指標）
   */
  diffMode?: 'number' | 'ppt'
}

interface Props {
  /** recharts 注入 */
  active?: boolean
  payload?: any[]
  label?: string
  /** 本圖要顯示的指標配對 */
  metrics: CompareMetric[]
}

const defaultFormat = (v: number) => Math.round(v).toLocaleString('en-US')

function pickValue(payload: any[] | undefined, key: string): number | null {
  const hit = (payload || []).find((p) => p.dataKey === key)
  const v = hit?.payload?.[key]
  return typeof v === 'number' && !Number.isNaN(v) ? v : null
}

const ComparisonTooltip: React.FC<Props> = ({ active, payload, label, metrics }) => {
  if (!active || !payload || payload.length === 0) return null

  // payload[0].payload 才是該筆完整資料列；直接取，避免序列被隱藏時抓不到值
  const row = payload[0]?.payload || {}

  return (
    <div
      style={{
        background: '#fff',
        border: '1px solid #d9d9d9',
        borderRadius: 4,
        padding: '8px 12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
        fontSize: 12,
        lineHeight: 1.7,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>

      {metrics.map((m) => {
        const fmt = m.format || defaultFormat
        const cur = typeof row[m.currentKey] === 'number' ? row[m.currentKey] : pickValue(payload, m.currentKey)
        const cmp = typeof row[m.compareKey] === 'number' ? row[m.compareKey] : pickValue(payload, m.compareKey)

        const hasDiff = cur !== null && cmp !== null
        const diff = hasDiff ? (cur as number) - (cmp as number) : null
        const pct = hasDiff && cmp !== 0 ? ((cur as number) - (cmp as number)) / Math.abs(cmp as number) * 100 : null

        const sign = (v: number) => (v > 0 ? '+' : '')
        const arrow = diff === null || diff === 0 ? '' : diff > 0 ? '▲' : '▼'

        const diffText = diff === null
          ? EMPTY
          : m.diffMode === 'ppt'
            ? `${sign(diff)}${diff.toFixed(1)} ppt`
            : `${sign(diff)}${fmt(diff)}`

        const pctText = pct === null ? EMPTY : `${sign(pct)}${pct.toFixed(1)}%`

        return (
          <div key={m.currentKey} style={{ marginBottom: 6 }}>
            <div style={{ color: m.color }}>
              {`本年${m.label}：${cur === null ? EMPTY : fmt(cur)}`}
            </div>
            <div style={{ color: GREY }}>
              {`去年${m.label}：${cmp === null ? EMPTY : fmt(cmp)}`}
            </div>
            <div style={{ color: trendColor(diff), fontWeight: 600 }}>
              {`較去年 ${arrow}${arrow ? ' ' : ''}${diffText}`}
              {diff !== null && <span>{`（${pctText}）`}</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default ComparisonTooltip
