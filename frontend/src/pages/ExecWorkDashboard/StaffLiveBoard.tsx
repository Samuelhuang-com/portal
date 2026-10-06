/**
 * 人員動線 — 「全員動態」看板（2026-10-05 新增）
 *
 * 一個時鐘驅動整棟大樓：拖曳或播放時間，所有人員以頭像在大樓剖面上移動，
 * 同時看到「此刻誰在哪、做什麼、下一站去哪」。
 *
 *  - 大樓剖面：RF～B4F 樓板，客房層依房號在走道上的位置排開、巡檢點依點位 x 座標排開
 *  - 人員狀態：工作中（脈動光圈）／移動中（經電梯換層、拖尾）／空檔／未開始／已收工
 *  - 右側名冊：此刻每人在做什麼、進度條、下一站
 *  - 下方：事件跑馬燈（開始／完成）＋全日忙碌度直條（點擊跳到該時間）
 *
 * ⚠️ 位置來自工作日誌的工作地點；兩站之間的移動（經電梯、走道）是畫面推定，不是定位軌跡。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Progress, Segmented, Slider, Space, Tag, Tooltip, Typography } from 'antd'
import {
  CaretRightOutlined, PauseOutlined, FieldTimeOutlined, AimOutlined, InfoCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import type { StaffPathDay, PathStop, HotelFloorPlan } from '@/api/staffPath'
import {
  PANEL_TEXT, PANEL_MUTED, GRID, fmtMin, useWidth, Panel, buildCenterline, floorsText, type Pt,
} from './staffPathShared'

const { Text } = Typography

// ── 型別 ───────────────────────────────────────────────────────────────────────
type Mode = 'work' | 'move' | 'idle' | 'off' | 'done'

const MODE_META: Record<Mode, { label: string; color: string; order: number }> = {
  work: { label: '工作中', color: '#52C41A', order: 0 },
  move: { label: '移動中', color: '#4BA8E8', order: 1 },
  idle: { label: '空檔',   color: '#FAAD14', order: 2 },
  off:  { label: '未開始', color: '#8c9db0', order: 3 },
  done: { label: '已收工', color: '#8c9db0', order: 4 },
}

/** 一個「在某處停留」的區段；巡檢停留點會依點位拆成多段 */
interface WP {
  t0: number
  t1: number
  floor: string | null     // null＝未定位
  xf: number               // 樓板上的水平位置 0～1
  span: string[]           // 跨樓層工作（無點位）時涵蓋的樓層
  label: string            // 位置短標（房號／點位名／樓層）
  stop: PathStop
}

interface PState {
  mode: Mode
  floor: string | null
  xf: number
  /** 移動中換層：起訖樓層與進度（0～1），畫在兩層之間 */
  rowF?: number
  vFrom?: string
  vTo?: string
  wp?: WP
  next?: WP
  prog?: number
}

const MOVE_MAX = 12          // 兩站之間最多以 12 分鐘畫移動
const ENTRY: { floor: string; xf: number } = { floor: '1f', xf: 0.5 }   // 上下班進出點（1F 大廳，推定）

const ease = (p: number) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2)
const shortName = (n: string) => (n.length <= 2 ? n : n.slice(-2))

// ══════════════════════════════════════════════════════════════════════════════
export default function StaffLiveBoard({
  data, plan, colorOf, onOpenStop, onFocusPerson,
}: {
  data: StaffPathDay
  plan: HotelFloorPlan | null
  colorOf: (p: string) => string
  onOpenStop: (s: PathStop) => void
  onFocusPerson: (p: string) => void
}) {
  // ── 房號 → 走道位置比例 ──
  const roomXf = useMemo(() => {
    const m = new Map<string, number>()
    let elev = 0.5
    if (plan) {
      const cl = buildCenterline(plan)
      plan.units.forEach(u => {
        const f = cl.project(u.door as Pt) / plan.length
        if (u.kind === 'room' && u.suffix) m.set(u.suffix, f)
      })
      const e = plan.units.filter(u => u.kind === 'elevator').map(u => cl.project(u.door as Pt) / plan.length)
      if (e.length) elev = e.reduce((a, b) => a + b, 0) / e.length
    }
    return { m, elev: Math.min(0.85, Math.max(0.15, elev)) }
  }, [plan])
  const XE = roomXf.elev

  // ── 每人的停留區段 ──
  const tracks = useMemo(() => data.persons.map((p, pi) => {
    const wps: WP[] = []
    p.stops.filter(s => s.start_min != null).forEach(s => {
      const t0 = s.start_min as number
      const t1 = Math.max(t0 + 5, s.end_min ?? (t0 + (s.work_min ?? 10)))
      const spread = 0.12 + 0.76 * (((pi * 0.37) + (s.seq * 0.137)) % 1)
      if (s.points?.length) {
        const n = s.points.length, d = (t1 - t0) / n
        s.points.forEach((pt, i) => wps.push({
          t0: t0 + d * i, t1: t0 + d * (i + 1), floor: pt.floor_key, xf: pt.x, span: [],
          label: pt.label, stop: s,
        }))
      } else if (s.room) {
        wps.push({ t0, t1, floor: s.floors[0] ?? null, xf: roomXf.m.get(s.room.slice(-2)) ?? spread, span: [], label: s.room, stop: s })
      } else if (s.floors.length) {
        wps.push({ t0, t1, floor: s.floors[0], xf: spread, span: s.floors.length > 1 ? s.floors : [], label: floorsText(s.floors), stop: s })
      } else {
        wps.push({ t0, t1, floor: null, xf: spread, span: [], label: '未定位', stop: s })
      }
    })
    wps.sort((a, b) => a.t0 - b.t0)
    return { person: p.person, wps }
  }), [data, roomXf])

  // ── 時間範圍 ──
  const [T0, T1] = useMemo(() => {
    const ts = tracks.flatMap(t => t.wps.flatMap(w => [w.t0, w.t1]))
    if (!ts.length) return [480, 1080]
    return [Math.floor((Math.min(...ts) - 20) / 30) * 30, Math.ceil((Math.max(...ts) + 20) / 30) * 30]
  }, [tracks])

  const isToday = data.date === dayjs().format('YYYY-MM-DD')
  const nowMin = () => dayjs().hour() * 60 + dayjs().minute()
  const [t, setT] = useState<number>(() => (isToday ? Math.min(Math.max(nowMin(), T0), T1) : T0))
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<number>(10)     // 每秒前進幾分鐘
  const [hover, setHover] = useState<string | null>(null)

  // 換日／換資料：回到起點（今天則跳到現在）
  useEffect(() => {
    setPlaying(false)
    setT(isToday ? Math.min(Math.max(nowMin(), T0), T1) : T0)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, T0, T1])

  // 播放迴圈
  const raf = useRef<number | null>(null)
  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    const step = (now: number) => {
      const dt = (now - last) / 1000
      last = now
      setT(prev => {
        const n = prev + dt * speed
        if (n >= T1) { setPlaying(false); return T1 }
        return n
      })
      raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [playing, speed, T1])

  // ── 每人在時間 t 的狀態 ──
  const stateAt = useCallback((wps: WP[], tt: number): PState => {
    if (!wps.length) return { mode: 'off', floor: null, xf: 0.5 }
    const first = wps[0], last = wps[wps.length - 1]
    let active: WP | undefined
    for (const w of wps) if (w.t0 <= tt && tt <= w.t1) active = w
    if (active) {
      const idx = wps.indexOf(active)
      return { mode: 'work', floor: active.floor, xf: active.xf, wp: active, next: wps[idx + 1],
               prog: (tt - active.t0) / Math.max(1, active.t1 - active.t0) }
    }
    if (tt < first.t0) {
      if (tt >= first.t0 - MOVE_MAX) return moveState(ENTRY, first, (tt - (first.t0 - MOVE_MAX)) / MOVE_MAX)
      return { mode: 'off', floor: null, xf: 0.5, next: first }
    }
    if (tt > last.t1) {
      if (tt <= last.t1 + MOVE_MAX) return { ...moveState(last, ENTRY, (tt - last.t1) / MOVE_MAX), wp: last }
      return { mode: 'done', floor: null, xf: 0.5, wp: last }
    }
    // 兩站之間
    let a = first, b = last
    for (let i = 0; i < wps.length - 1; i++) {
      if (wps[i].t1 <= tt && tt <= wps[i + 1].t0) { a = wps[i]; b = wps[i + 1]; break }
    }
    const gap = b.t0 - a.t1
    const mv = Math.min(gap, MOVE_MAX)
    if (tt >= b.t0 - mv && mv > 0) return { ...moveState(a, b, (tt - (b.t0 - mv)) / mv), wp: a }
    return { mode: 'idle', floor: a.floor, xf: a.xf, wp: a, next: b }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [XE])

  /** 移動：水平走到電梯 → 垂直換層 → 水平走到下一站（同層則直接走） */
  function moveState(a: { floor: string | null; xf: number }, b: WP | { floor: string; xf: number }, p0: number): PState {
    const p = Math.max(0, Math.min(1, p0))
    const fa = a.floor ?? '__unknown', fb = (b.floor ?? '__unknown')
    const next = 'stop' in b ? (b as WP) : undefined
    if (fa === fb) return { mode: 'move', floor: a.floor, xf: a.xf + (b.xf - a.xf) * ease(p), next }
    if (p < 1 / 3) return { mode: 'move', floor: a.floor, xf: a.xf + (XE - a.xf) * ease(p * 3), next }
    if (p < 2 / 3) return { mode: 'move', floor: a.floor, xf: XE, rowF: ease((p - 1 / 3) * 3), next, vFrom: fa, vTo: fb }
    return { mode: 'move', floor: b.floor ?? null, xf: XE + (b.xf - XE) * ease((p - 2 / 3) * 3), next }
  }

  const states = tracks.map(tr => ({ person: tr.person, st: stateAt(tr.wps, t), wps: tr.wps }))

  // ── 版面 ──
  const [ref, width] = useWidth<HTMLDivElement>()
  const rows = [...data.floors.map(f => f.key), '__unknown']
  const ROW = 32, TOP = 26, LEFT = 66, RIGHT = 26, SK = 16
  const H = TOP + rows.length * ROW + 10
  const rowIdx = (k: string | null) => rows.indexOf(k ?? '__unknown')
  const rowY = (k: string | null) => TOP + rowIdx(k) * ROW + ROW / 2
  const slabW = width - LEFT - RIGHT - SK
  const xOf = (xf: number) => LEFT + SK / 2 + xf * slabW
  const yOfState = (st: PState): number => {
    if (st.vFrom && st.vTo && st.rowF != null) {
      const yA = rowY(st.vFrom === '__unknown' ? null : st.vFrom)
      const yB = rowY(st.vTo === '__unknown' ? null : st.vTo)
      return yA + (yB - yA) * st.rowF
    }
    return rowY(st.floor)
  }

  // 每人像素位置（含換層途中的插值）
  const placed = states.map(({ person, st, wps }) => {
    if (st.mode === 'off' || st.mode === 'done') return { person, st, wps, x: 0, y: 0, visible: false }
    const y = yOfState(st)
    return { person, st, wps, x: xOf(st.xf), y, visible: true }
  })
  // 重疊錯開
  const vis = placed.filter(p => p.visible).sort((a, b) => a.y - b.y || a.x - b.x)
  for (let i = 1; i < vis.length; i++) {
    for (let j = 0; j < i; j++) {
      if (Math.abs(vis[i].y - vis[j].y) < 10 && Math.abs(vis[i].x - vis[j].x) < 24) vis[i].x = vis[j].x + 24
    }
  }

  // ── 計數 ──
  const counts: Record<Mode, number> = { work: 0, move: 0, idle: 0, off: 0, done: 0 }
  states.forEach(s => { counts[s.st.mode]++ })

  // ── 忙碌度直條（每 10 分鐘工作中人數）──
  const buckets = useMemo(() => {
    const out: { m: number; n: number }[] = []
    for (let m = T0; m < T1; m += 10) {
      const n = tracks.filter(tr => tr.wps.some(w => w.t0 < m + 10 && w.t1 > m)).length
      out.push({ m, n })
    }
    return out
  }, [tracks, T0, T1])
  const maxB = Math.max(1, ...buckets.map(b => b.n))

  // ── 事件跑馬燈 ──
  const events = useMemo(() => {
    const ev: { k: string; m: number; person: string; kind: 'start' | 'end'; stop: PathStop }[] = []
    data.persons.forEach(p => p.stops.forEach(s => {
      if (s.start_min == null) return
      ev.push({ k: `${p.person}-${s.seq}-s`, m: s.start_min, person: p.person, kind: 'start', stop: s })
      const e = s.end_min ?? (s.start_min + (s.work_min ?? 10))
      ev.push({ k: `${p.person}-${s.seq}-e`, m: e, person: p.person, kind: 'end', stop: s })
    }))
    return ev.sort((a, b) => a.m - b.m)
  }, [data])
  const recent = events.filter(e => e.m <= t).slice(-7).reverse()

  const ordered = [...states].sort((a, b) =>
    MODE_META[a.st.mode].order - MODE_META[b.st.mode].order || a.person.localeCompare(b.person))

  const where = (st: PState): string => {
    if (st.mode === 'move') return st.next ? `前往 ${st.next.label}` : '離開'
    if (st.wp) return st.wp.label
    return '—'
  }

  return (
    <div>
      <style>{`
        @keyframes slbIn { from { opacity: 0; transform: translateY(-6px) } to { opacity: 1; transform: none } }
        .slb-ev { animation: slbIn .45s ease-out }
        .slb-card { transition: background .2s, transform .2s }
        .slb-card:hover { background: rgba(75,168,232,0.16) !important; transform: translateX(2px) }
      `}</style>

      {/* ── 時鐘列 ── */}
      <Panel title={null} fill={false}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
          <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace', fontSize: 40, fontWeight: 700,
                        color: '#fff', letterSpacing: 2, lineHeight: 1, minWidth: 128, textShadow: '0 0 18px rgba(75,168,232,0.55)' }}>
            {fmtMin(Math.floor(t))}
          </div>
          <Space size={6}>
            <Button type="primary" shape="circle" size="large"
                    icon={playing ? <PauseOutlined /> : <CaretRightOutlined />}
                    onClick={() => { if (!playing && t >= T1) setT(T0); setPlaying(p => !p) }} />
            <Segmented size="small" value={speed} onChange={v => setSpeed(v as number)}
                       options={[{ label: '慢', value: 3 }, { label: '中', value: 10 }, { label: '快', value: 30 }]} />
            {isToday && (
              <Tooltip title="跳到現在">
                <Button size="small" ghost icon={<FieldTimeOutlined />}
                        onClick={() => { setPlaying(false); setT(Math.min(Math.max(nowMin(), T0), T1)) }}>現在</Button>
              </Tooltip>
            )}
          </Space>
          <Space size={12} wrap>
            {(['work', 'move', 'idle', 'off', 'done'] as Mode[]).map(m => (
              <span key={m} style={{ color: PANEL_TEXT, fontSize: 13 }}>
                <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: 5, background: MODE_META[m].color, marginRight: 5 }} />
                {MODE_META[m].label} <b style={{ color: '#fff', fontSize: 16 }}>{counts[m]}</b>
              </span>
            ))}
          </Space>
          <Tooltip title="人員位置來自工作日誌的工作地點；兩站之間經電梯、走道的移動是畫面推定，不是定位軌跡。上下班以 1F 大廳為進出點（推定）。">
            <Text style={{ color: PANEL_MUTED, fontSize: 12, marginLeft: 'auto' }}><InfoCircleOutlined /> 移動為推定</Text>
          </Tooltip>
        </div>

        {/* 忙碌度直條＋時間軸 */}
        <div style={{ marginTop: 10 }}>
          <svg width="100%" height={34} viewBox={`0 0 ${buckets.length * 10} 34`} preserveAspectRatio="none"
               style={{ display: 'block', cursor: 'pointer' }}
               onClick={e => {
                 const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
                 setPlaying(false); setT(T0 + ((e.clientX - r.left) / r.width) * (T1 - T0))
               }}>
            {buckets.map((b, i) => (
              <rect key={b.m} x={i * 10 + 1} y={34 - (b.n / maxB) * 32} width={8} height={(b.n / maxB) * 32}
                    rx={1.5} fill={b.m <= t ? '#4BA8E8' : 'rgba(127,155,184,0.35)'} />
            ))}
            <rect x={((t - T0) / (T1 - T0)) * buckets.length * 10 - 0.75} y={0} width={1.5} height={34} fill="#fff" />
          </svg>
          <Slider min={T0} max={T1} step={1} value={Math.round(t)} style={{ margin: '4px 2px 0' }}
                  onChange={v => { setPlaying(false); setT(v as number) }}
                  tooltip={{ formatter: v => fmtMin(v ?? 0) }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: PANEL_MUTED }}>
            <span>{fmtMin(T0)}</span><span>每條＝10 分鐘內工作中的人數</span><span>{fmtMin(T1)}</span>
          </div>
        </div>
      </Panel>

      <div style={{ display: 'flex', gap: 12, marginTop: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        {/* ── 大樓剖面 ── */}
        <div style={{ flex: '1 1 620px', minWidth: 0 }}>
          <Panel fill={false} title="大樓即時動態" extra={<Text style={{ color: PANEL_MUTED, fontSize: 12 }}>點頭像看明細｜客房層依房號位置排開</Text>}>
            <div ref={ref} style={{ width: '100%' }}>
              <svg width={width} height={H} style={{ display: 'block' }}>
                <defs>
                  <linearGradient id="slbGuest" x1="0" x2="1">
                    <stop offset="0%" stopColor="rgba(75,168,232,0.22)" /><stop offset="100%" stopColor="rgba(75,168,232,0.06)" />
                  </linearGradient>
                  <linearGradient id="slbPub" x1="0" x2="1">
                    <stop offset="0%" stopColor="rgba(255,255,255,0.10)" /><stop offset="100%" stopColor="rgba(255,255,255,0.03)" />
                  </linearGradient>
                  <filter id="slbGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
                  </filter>
                </defs>

                {/* 樓板 */}
                {rows.map((k, i) => {
                  const f = data.floors.find(ff => ff.key === k)
                  const yc = TOP + i * ROW + ROW / 2
                  const top = yc - 9, bot = yc + 9
                  const busy = placed.filter(p => p.visible && rowIdx(p.st.floor) === i && p.st.mode === 'work').length
                  const unknown = k === '__unknown'
                  return (
                    <g key={k}>
                      <polygon
                        points={`${LEFT},${bot} ${LEFT + slabW},${bot} ${LEFT + slabW + SK},${top} ${LEFT + SK},${top}`}
                        fill={unknown ? 'rgba(255,255,255,0.025)' : f?.kind === 'guest' ? 'url(#slbGuest)' : 'url(#slbPub)'}
                        stroke={busy ? 'rgba(91,228,155,0.7)' : 'rgba(127,155,184,0.28)'} strokeWidth={busy ? 1.4 : 1}
                        strokeDasharray={unknown ? '4 3' : undefined} />
                      <text x={8} y={yc + 4} fill={unknown ? PANEL_MUTED : '#fff'} fontSize={12} fontWeight={600}>
                        {unknown ? '未定位' : f?.label}
                      </text>
                      {f?.kind === 'guest' && <text x={36} y={yc + 4} fill="#4BA8E8" fontSize={9}>客房</text>}
                      {busy > 0 && (
                        <text x={LEFT + slabW + SK + 4} y={yc + 4} fill="#5BE49B" fontSize={10} fontWeight={700}>{busy}</text>
                      )}
                    </g>
                  )
                })}

                {/* 電梯井 */}
                <rect x={xOf(XE) - 6} y={TOP + 2} width={12} height={(rows.length - 1) * ROW - 4}
                      fill="rgba(255,181,71,0.07)" stroke="rgba(255,181,71,0.35)" strokeDasharray="3 3" rx={3} />
                <text x={xOf(XE)} y={TOP - 8} fill="rgba(255,181,71,0.85)" fontSize={10} textAnchor="middle">電梯</text>

                {/* 跨樓層工作的範圍條 */}
                {placed.filter(p => p.visible && p.st.mode === 'work' && p.st.wp?.span.length).map(p => {
                  const ys = (p.st.wp as WP).span.map(f => rowY(f))
                  return (
                    <rect key={`span-${p.person}`} x={p.x - 3} y={Math.min(...ys) - 8} width={6}
                          height={Math.max(...ys) - Math.min(...ys) + 16} rx={3}
                          fill={colorOf(p.person)} opacity={0.25} />
                  )
                })}

                {/* 拖尾 */}
                {placed.filter(p => p.visible && p.st.mode === 'move').map(p => {
                  const tr = tracks.find(x => x.person === p.person)!
                  return [1.2, 2.4, 3.6].map((dt, i) => {
                    const s2 = stateAt(tr.wps, t - dt)
                    if (s2.mode === 'off' || s2.mode === 'done') return null
                    const y2 = yOfState(s2)
                    return <circle key={`tr-${p.person}-${i}`} cx={xOf(s2.xf)} cy={y2} r={9 - i * 2.2}
                                   fill={colorOf(p.person)} opacity={0.32 - i * 0.09} />
                  })
                })}

                {/* 頭像 */}
                {placed.filter(p => p.visible).map(p => {
                  const c = colorOf(p.person)
                  const hl = hover === p.person
                  const st = p.st
                  return (
                    <g key={p.person} transform={`translate(${p.x},${p.y})`} style={{ cursor: 'pointer' }}
                       opacity={hover && !hl ? 0.35 : st.mode === 'idle' ? 0.6 : 1}
                       onMouseEnter={() => setHover(p.person)} onMouseLeave={() => setHover(null)}
                       onClick={() => { const s = st.wp?.stop ?? st.next?.stop; if (s) onOpenStop(s) }}>
                      {st.mode === 'work' && (
                        <circle r={13} fill="none" stroke={c} strokeWidth={2}>
                          <animate attributeName="r" values="13;24" dur="1.6s" repeatCount="indefinite" />
                          <animate attributeName="opacity" values="0.8;0" dur="1.6s" repeatCount="indefinite" />
                        </circle>
                      )}
                      <circle r={hl ? 15 : 13} fill={c} stroke={hl ? '#fff' : 'rgba(13,30,48,0.9)'} strokeWidth={2}
                              filter={st.mode === 'work' ? 'url(#slbGlow)' : undefined} />
                      <text y={4} textAnchor="middle" fontSize={10} fontWeight={800} fill="#0d1e30">{shortName(p.person)}</text>
                      {st.mode === 'idle' && <text x={12} y={-10} fontSize={11} fill="#FAAD14">…</text>}
                      {(st.mode === 'work' || hl) && st.wp && (
                        <g transform="translate(0,-26)">
                          <rect x={-((st.wp.label.length * 7 + 12) / 2)} y={-9} width={st.wp.label.length * 7 + 12} height={16} rx={8}
                                fill="rgba(13,30,48,0.88)" stroke={c} strokeWidth={1} />
                          <text y={3} textAnchor="middle" fontSize={10} fill="#fff">{st.wp.label.slice(0, 12)}</text>
                        </g>
                      )}
                      <title>
                        {`${p.person}｜${MODE_META[st.mode].label}\n${st.wp ? st.wp.stop.row.task : ''}`
                          + (st.next ? `\n下一站 ${fmtMin(Math.round(st.next.t0))} ${st.next.label}` : '')}
                      </title>
                    </g>
                  )
                })}
              </svg>
            </div>
          </Panel>

          {/* 事件跑馬燈 */}
          <div style={{ marginTop: 12 }}>
            <Panel title="即時事件" fill={false}>
              {recent.length === 0
                ? <Text style={{ color: PANEL_MUTED }}>這個時間之前還沒有事件</Text>
                : recent.map(e => (
                  <div key={e.k} className="slb-ev" style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '4px 0',
                                                         borderBottom: `1px solid ${GRID}`, fontSize: 13, cursor: 'pointer' }}
                       onClick={() => onOpenStop(e.stop)}>
                    <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', color: PANEL_MUTED, minWidth: 44 }}>{fmtMin(e.m)}</span>
                    <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 4, background: colorOf(e.person) }} />
                    <b style={{ color: '#fff', minWidth: 56 }}>{e.person}</b>
                    <Tag color={e.kind === 'start' ? 'green' : 'default'} style={{ margin: 0 }}>{e.kind === 'start' ? '▶ 開始' : '✓ 完成'}</Tag>
                    <span style={{ color: '#4BA8E8' }}>{e.stop.room ?? floorsText(e.stop.floors)}</span>
                    <span style={{ color: PANEL_TEXT, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.stop.row.task}</span>
                  </div>
                ))}
            </Panel>
          </div>
        </div>

        {/* ── 此刻名冊 ── */}
        <div style={{ flex: '1 1 340px', minWidth: 300, maxWidth: 460 }}>
          <Panel fill={false} title={`此刻 ${fmtMin(Math.floor(t))}　誰在做什麼`}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: H + 260, overflowY: 'auto', paddingRight: 2 }}>
              {ordered.map(({ person, st }) => {
                const c = colorOf(person)
                const meta = MODE_META[st.mode]
                return (
                  <div key={person} className="slb-card"
                       onMouseEnter={() => setHover(person)} onMouseLeave={() => setHover(null)}
                       style={{ background: hover === person ? 'rgba(75,168,232,0.16)' : 'rgba(255,255,255,0.04)',
                                borderLeft: `3px solid ${c}`, borderRadius: 8, padding: '7px 10px',
                                opacity: st.mode === 'off' || st.mode === 'done' ? 0.6 : 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ width: 26, height: 26, borderRadius: 13, background: c, color: '#0d1e30', fontSize: 10, fontWeight: 800,
                                     display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: 'none' }}>
                        {shortName(person)}
                      </span>
                      <b style={{ color: '#fff' }}>{person}</b>
                      <Tag color={meta.color} style={{ margin: 0, color: '#0d1e30', fontWeight: 600 }}>{meta.label}</Tag>
                      <span style={{ marginLeft: 'auto', color: '#4BA8E8', fontSize: 13 }}>
                        {st.mode === 'off' || st.mode === 'done' ? '' : where(st)}
                      </span>
                      <Tooltip title="看他的個人動線">
                        <Button size="small" type="text" icon={<AimOutlined style={{ color: PANEL_MUTED }} />}
                                onClick={() => onFocusPerson(person)} />
                      </Tooltip>
                    </div>
                    {st.wp && st.mode !== 'done' && (
                      <div style={{ fontSize: 12, color: PANEL_TEXT, marginTop: 3, cursor: 'pointer',
                                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                           onClick={() => onOpenStop((st.wp as WP).stop)}>
                        {st.mode === 'work' ? '' : '上一站：'}{st.wp.stop.row.task}
                      </div>
                    )}
                    {st.mode === 'work' && st.prog != null && (
                      <Progress percent={Math.round(st.prog * 100)} size="small" showInfo={false}
                                strokeColor={c} trailColor="rgba(255,255,255,0.08)" style={{ margin: '2px 0 0' }} />
                    )}
                    {st.next && st.mode !== 'work' && (
                      <div style={{ fontSize: 12, color: PANEL_MUTED, marginTop: 2 }}>
                        下一站 {fmtMin(Math.round(st.next.t0))}　{st.next.label}
                      </div>
                    )}
                    {st.mode === 'work' && st.next && (
                      <div style={{ fontSize: 11, color: PANEL_MUTED, marginTop: 1 }}>
                        接著 {fmtMin(Math.round(st.next.t0))} {st.next.label}
                      </div>
                    )}
                    {st.mode === 'done' && st.wp && (
                      <div style={{ fontSize: 12, color: PANEL_MUTED, marginTop: 2 }}>最後一站 {fmtMin(Math.round(st.wp.t1))} {st.wp.label}</div>
                    )}
                  </div>
                )
              })}
              {!ordered.length && <Text style={{ color: PANEL_MUTED }}>沒有人員資料</Text>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}
