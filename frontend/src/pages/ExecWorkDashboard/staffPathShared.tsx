/**
 * 人員動線 — 共用常數／工具（StaffPathTab 與 StaffLiveBoard 共用）
 */
import React, { useEffect, useRef, useState } from 'react'
import type { HotelFloorPlan } from '@/api/staffPath'

// ── 色彩（深色中控台面板；品牌主色 #1B3A5C／輔色 #4BA8E8 不變）──────────────────
export const PANEL_BG = 'linear-gradient(160deg, #0d1e30 0%, #13304d 55%, #1B3A5C 100%)'
export const PANEL_TEXT = '#dbe7f3'
export const PANEL_MUTED = '#7f9bb8'
export const GRID = 'rgba(127,155,184,0.18)'
export const PERSON_COLORS = [
  '#4BA8E8', '#FFB547', '#5BE49B', '#FF6B8B', '#B18CFF',
  '#3DD6D0', '#F5E663', '#FF8F5A', '#8FA8FF', '#E58FE0',
]


// ── 工具 ───────────────────────────────────────────────────────────────────────
export function fmtMin(m: number | null): string {
  if (m == null) return '—'
  const day = Math.floor(m / 1440)
  const mm = ((m % 1440) + 1440) % 1440
  const s = `${String(Math.floor(mm / 60)).padStart(2, '0')}:${String(mm % 60).padStart(2, '0')}`
  return day < 0 ? `前日 ${s}` : day > 0 ? `次日 ${s}` : s
}

export function useWidth<T extends HTMLElement>(): [React.RefObject<T>, number] {
  const ref = useRef<T>(null)
  const [w, setW] = useState(800)
  useEffect(() => {
    if (!ref.current) return
    const ro = new ResizeObserver(entries => {
      const cw = entries[0]?.contentRect.width
      if (cw) setW(Math.max(320, Math.floor(cw)))
    })
    ro.observe(ref.current)
    return () => ro.disconnect()
  }, [])
  return [ref, w]
}

export function Panel({ title, extra, children, minHeight, fill = true }: {
  title: React.ReactNode; extra?: React.ReactNode; children: React.ReactNode; minHeight?: number
  /** true＝高度撐滿父層（並排面板等高）；false＝依內容高度 */
  fill?: boolean
}) {
  return (
    <div style={{
      background: PANEL_BG, borderRadius: 10, padding: '12px 14px', color: PANEL_TEXT,
      boxShadow: '0 4px 16px rgba(13,30,48,0.25)', minHeight, height: fill ? '100%' : undefined,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, gap: 8, flexWrap: 'wrap' }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: '#fff', letterSpacing: 0.5 }}>{title}</div>
        {extra}
      </div>
      {children}
    </div>
  )
}

// ── 客房標準層走道中心線（投影／沿走道取點）──────────────────────────────────
export type Pt = [number, number]

export function buildCenterline(plan: HotelFloorPlan) {
  const pts = plan.centerline
  const cum = [0]
  for (let i = 1; i < pts.length; i++) {
    cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]))
  }
  const project = (q: Pt): number => {
    let best = Infinity, bestS = 0
    for (let i = 0; i < pts.length - 1; i++) {
      const [ax, ay] = pts[i], [bx, by] = pts[i + 1]
      const dx = bx - ax, dy = by - ay
      const len2 = dx * dx + dy * dy || 1e-9
      const t = Math.max(0, Math.min(1, ((q[0] - ax) * dx + (q[1] - ay) * dy) / len2))
      const px = ax + dx * t, py = ay + dy * t
      const dist = Math.hypot(q[0] - px, q[1] - py)
      if (dist < best) { best = dist; bestS = cum[i] + Math.sqrt(len2) * t }
    }
    return bestS
  }
  const at = (s: number): Pt => {
    const ss = Math.max(0, Math.min(cum[cum.length - 1], s))
    let i = 1
    while (i < cum.length - 1 && cum[i] < ss) i++
    const seg = cum[i] - cum[i - 1] || 1e-9
    const t = (ss - cum[i - 1]) / seg
    return [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t]
  }
  /** 沿走道由 s0 走到 s1 的折線點（含兩端） */
  const between = (s0: number, s1: number): Pt[] => {
    const out: Pt[] = [at(s0)]
    const lo = Math.min(s0, s1), hi = Math.max(s0, s1)
    const mids = cum.map((c, i) => [c, i] as const).filter(([c]) => c > lo && c < hi).map(([, i]) => pts[i])
    out.push(...(s0 <= s1 ? mids : mids.reverse()))
    out.push(at(s1))
    return out
  }
  return { project, between }
}

/** 停留點的短位置描述 */
export function floorsText(floors: string[]): string {
  if (!floors.length) return '未定位'
  if (floors.length > 3) return `${floors[0].toUpperCase()}～${floors[floors.length - 1].toUpperCase()}`
  return floors.map(f => f.toUpperCase()).join('、')
}
