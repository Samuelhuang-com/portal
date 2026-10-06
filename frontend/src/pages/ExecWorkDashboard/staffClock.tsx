/**
 * 人員動態 — 共用時鐘（大樓視角／工作視角共用同一個時間）2026-10-06
 *
 *  - 今天：預設 LIVE，時間跟著現在走（每 15 秒對時）；拖曳或播放＝離開 LIVE 回放今天，
 *    「回到現在」接回 LIVE；回放播到現在會自動接回 LIVE。今天的時間軸不能拖到未來。
 *  - 過去的日期：從當天第一筆前開始，可播放／拖曳。
 *  - 進行中（open：已打卡開始、還沒填結束）：今天＝做到現在；過去日期＝視為 10 分鐘並標「未結束」。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Segmented, Slider, Space, Tooltip } from 'antd'
import { CaretRightOutlined, PauseOutlined, FieldTimeOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import type { PathStop, StaffPathDay } from '@/api/staffPath'
import { PANEL_MUTED, fmtMin, Panel } from './staffPathShared'

export const nowMinute = () => dayjs().hour() * 60 + dayjs().minute()

/** 停留點的結束分鐘（處理進行中／缺結束時間） */
export function stopEndMin(s: PathStop, isToday: boolean, now: number): number {
  const t0 = s.start_min as number
  if (s.open) return isToday ? Math.max(t0 + 1, now) : t0 + 10
  return Math.max(t0 + 5, s.end_min ?? (t0 + (s.work_min ?? 10)))
}

export interface DayClock {
  /** 目前畫面時間（分鐘，可含小數） */
  t: number
  T0: number
  T1: number
  now: number
  isToday: boolean
  live: boolean
  playing: boolean
  speed: number
  setT: (v: number) => void
  goLive: () => void
  togglePlay: () => void
  setSpeed: (v: number) => void
}

export function useDayClock(data: StaffPathDay | null): DayClock {
  const [now, setNow] = useState<number>(nowMinute)
  useEffect(() => {
    const id = window.setInterval(() => setNow(nowMinute()), 15000)
    return () => window.clearInterval(id)
  }, [])
  const isToday = !!data && data.date === dayjs().format('YYYY-MM-DD')

  const [T0, T1] = useMemo(() => {
    const ts: number[] = []
    data?.persons.forEach(p => p.stops.forEach(s => {
      if (s.start_min == null) return
      ts.push(s.start_min, stopEndMin(s, isToday, now))
    }))
    if (isToday) ts.push(now)
    if (!ts.length) return [480, 1080]
    return [Math.floor((Math.min(...ts) - 20) / 30) * 30, Math.ceil((Math.max(...ts) + 20) / 30) * 30]
  }, [data, isToday, now])

  const [tRaw, setTRaw] = useState<number>(T0)
  const [live, setLive] = useState<boolean>(false)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState<number>(10)
  const maxT = isToday ? Math.min(T1, now) : T1
  const clamp = useCallback((v: number) => Math.min(Math.max(v, T0), maxT), [T0, maxT])

  // 換日：今天＝LIVE；過去＝從頭（同一天的定時重抓不重置）
  const dateKey = data?.date
  useEffect(() => {
    setPlaying(false)
    if (isToday) setLive(true)
    else { setLive(false); setTRaw(T0) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateKey])

  // 播放
  const raf = useRef<number | null>(null)
  useEffect(() => {
    if (!playing) return
    let last = performance.now()
    const step = (ts: number) => {
      const dt = (ts - last) / 1000
      last = ts
      setTRaw(prev => {
        const n = prev + dt * speed
        if (n >= maxT) {
          setPlaying(false)
          if (isToday) setLive(true)
          return maxT
        }
        return n
      })
      raf.current = requestAnimationFrame(step)
    }
    raf.current = requestAnimationFrame(step)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [playing, speed, maxT, isToday])

  const t = live ? clamp(now) : clamp(tRaw)

  return {
    t, T0, T1, now, isToday, live, playing, speed,
    setT: v => { setLive(false); setPlaying(false); setTRaw(clamp(v)) },
    goLive: () => { setPlaying(false); setLive(true) },
    togglePlay: () => {
      if (playing) { setPlaying(false); return }
      if (live || t >= maxT - 0.5) setTRaw(T0)
      setLive(false)
      setPlaying(true)
    },
    setSpeed,
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// 時鐘列：大字時間＋LIVE／回放＋播放＋忙碌度直條＋時間軸
// ══════════════════════════════════════════════════════════════════════════════
export function ClockBar({ clock, data, legend, loadedAt }: {
  clock: DayClock
  data: StaffPathDay
  legend?: React.ReactNode
  loadedAt?: Dayjs | null
}) {
  const { t, T0, T1, now, isToday, live, playing, speed } = clock

  // 每 10 分鐘工作中的人數
  const buckets = useMemo(() => {
    const iv = data.persons.map(p => p.stops.filter(s => s.start_min != null)
      .map(s => [s.start_min as number, stopEndMin(s, isToday, now)] as const))
    const out: { m: number; n: number }[] = []
    for (let m = T0; m < T1; m += 10) {
      out.push({ m, n: iv.filter(list => list.some(([a, b]) => a < m + 10 && b > m)).length })
    }
    return out
  }, [data, T0, T1, isToday, now])
  const maxB = Math.max(1, ...buckets.map(b => b.n))
  const W = Math.max(1, buckets.length * 10)
  const xT = (m: number) => ((m - T0) / Math.max(1, T1 - T0)) * W

  return (
    <Panel title={null} fill={false}>
      <style>{`
        @keyframes clkLive { 0%,100% { opacity: 1 } 50% { opacity: .35 } }
        .clk-live-dot { animation: clkLive 1.4s ease-in-out infinite }
        @media (prefers-reduced-motion: reduce) { .clk-live-dot { animation: none } }
      `}</style>
      <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
        <div style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace', fontSize: 40, fontWeight: 700,
                      color: '#fff', letterSpacing: 2, lineHeight: 1, minWidth: 128, textShadow: '0 0 18px rgba(75,168,232,0.55)' }}>
          {fmtMin(Math.floor(t))}
        </div>
        {live ? (
          <Tooltip title={`時間跟著現在走；資料每 5 分鐘自動重抓${loadedAt ? `（上次 ${loadedAt.format('HH:mm')}）` : ''}`}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid #ff4d4f', color: '#ff7875',
                           borderRadius: 4, padding: '1px 8px', fontWeight: 700, fontSize: 12, letterSpacing: 1 }}>
              <span className="clk-live-dot" style={{ width: 8, height: 8, borderRadius: 4, background: '#ff4d4f' }} />LIVE
            </span>
          </Tooltip>
        ) : isToday ? (
          <span style={{ color: PANEL_MUTED, fontSize: 12 }}>回放今天</span>
        ) : null}
        <Space size={6}>
          <Tooltip title={live ? '從今天一早開始回放' : playing ? '暫停' : '播放'}>
            <Button type="primary" shape="circle" size="large"
                    icon={playing ? <PauseOutlined /> : <CaretRightOutlined />} onClick={clock.togglePlay} />
          </Tooltip>
          <Segmented size="small" value={speed} onChange={v => clock.setSpeed(v as number)}
                     options={[{ label: '慢', value: 3 }, { label: '中', value: 10 }, { label: '快', value: 30 }]} />
          {isToday && !live && (
            <Button size="small" ghost icon={<FieldTimeOutlined />} onClick={clock.goLive}>回到現在</Button>
          )}
        </Space>
        {legend}
      </div>

      <div style={{ marginTop: 10 }}>
        <svg width="100%" height={34} viewBox={`0 0 ${W} 34`} preserveAspectRatio="none"
             style={{ display: 'block', cursor: 'pointer' }}
             onClick={e => {
               const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect()
               clock.setT(T0 + ((e.clientX - r.left) / r.width) * (T1 - T0))
             }}>
          {isToday && now < T1 && (
            <rect x={xT(now)} y={0} width={W - xT(now)} height={34} fill="rgba(127,155,184,0.08)" />
          )}
          {buckets.map((b, i) => (
            <rect key={b.m} x={i * 10 + 1} y={34 - (b.n / maxB) * 32} width={8} height={(b.n / maxB) * 32}
                  rx={1.5} fill={b.m <= t ? '#4BA8E8' : 'rgba(127,155,184,0.35)'} />
          ))}
          <rect x={xT(t) - 0.75} y={0} width={1.5} height={34} fill={live ? '#ff4d4f' : '#fff'} />
        </svg>
        <Slider min={T0} max={T1} step={1} value={Math.round(t)} style={{ margin: '4px 2px 0' }}
                onChange={v => clock.setT(v as number)}
                tooltip={{ formatter: v => fmtMin(v ?? 0) }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: PANEL_MUTED }}>
          <span>{fmtMin(T0)}</span>
          <span>每條＝10 分鐘內工作中的人數{isToday ? '｜灰底＝還沒到' : ''}</span>
          <span>{fmtMin(T1)}</span>
        </div>
      </div>
    </Panel>
  )
}
