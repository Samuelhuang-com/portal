/**
 * 戰情 KPI — 3D 樓層（等角整棟模型）
 *
 * 一張圖看整棟：B4F～4F 為底座（地下室＋商場），5F～10F、RF 為客房塔樓。
 *  - 樓板顏色：紅＝有報修等超過 7 天或巡檢異常；橘＝有未完成報修或巡檢未填；綠＝今天有人工作；灰＝無事件
 *  - 客房層：用人員動線同一份向量標準層（hotel_std_floor.json）畫出每一間房，依報修／到訪上色
 *  - 其他樓層：巡檢點位依樓層巡檢圖的比例座標放到樓板上；報修沒有座標，以釘子排在樓板邊（位置不代表實際地點）
 *  - 時間軸：依工作日誌的開始～結束時間，把人員放到當時所在樓層／房間
 * 點房間 → 房間履歷；點點位 → 設備履歷；點釘子 → 報修明細；點人員 → 工作日誌明細
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Button, DatePicker, Slider, Space, Spin, Switch, Tooltip } from 'antd'
import { CaretRightOutlined, LeftOutlined, PauseOutlined, ReloadOutlined, RightOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import {
  fetchWarRoomFloors, fetchWarRoomHotelPlan,
  type WrFloor, type WrFloors, type WrPersonStop, type WrPoint, type WrRepair,
} from '@/api/warRoom'
import type { HotelFloorPlan } from '@/api/staffPath'
import type { JournalRow } from '@/api/workJournal'
import JournalRowDrawer from '@/components/WorkJournal/JournalRowDrawer'
import { PANEL_MUTED, PANEL_TEXT, PERSON_COLORS, Panel } from '@/pages/ExecWorkDashboard/staffPathShared'
import { AssetHistoryDrawer, RepairDrawer, type AssetTarget } from './AssetHistory'

// ── 顏色 ──
const COL = { bad: '#ef5a5a', warn: '#f2a93b', ok: '#3ccf91', idle: '#3a4d6e', accent: '#4BA8E8', room: '#1c2a44' }
const POINT_COL: Record<string, string> = { normal: '#3ccf91', abnormal: '#ef5a5a', unchecked: '#f2a93b', no_record: '#6b7c99' }

// ── 幾何（格單位）──
const S = 16
const COS = Math.cos(Math.PI / 6)
const SIN = 0.4
const GAP = 24
const TH = 6
const EXPLODE = 120
const TOWER_KEYS = new Set(['5f', '6f', '7f', '8f', '9f', '10f', 'rf'])
type Box = { x: number; y: number; w: number; d: number }
const PODIUM: Box = { x: 0, y: 0, w: 26, d: 17 }
const TOWER: Box = { x: 4, y: 2.5, w: 18, d: 12 }   // 1000×665 標準層比例
const boxOf = (k: string): Box => (TOWER_KEYS.has(k) ? TOWER : PODIUM)
const iso = (x: number, y: number, z: number): [number, number] => [(x - y) * S * COS, (x + y) * S * SIN - z]
const P = (a: [number, number][]) => a.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')

const toMin = (s: string) => { const [h, m] = (s || '0:0').split(':').map(Number); return (h || 0) * 60 + (m || 0) }
const mm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(Math.round(m % 60)).padStart(2, '0')}`
const hash = (s: string) => { let h = 7; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h }
const shortName = (n: string) => (n.length <= 2 ? n : n.slice(-2))

function floorLevel(f: WrFloor): keyof typeof COL {
  if (f.point_status.abnormal > 0 || f.repairs.some(r => (r.wait_days ?? 0) > 7)) return 'bad'
  if (f.repairs.length || f.point_status.unchecked > 0) return 'warn'
  if (f.people_count > 0) return 'ok'
  return 'idle'
}

interface Track { person: string; stops: { floor: string; room: string | null; s: number; e: number; stop: WrPersonStop }[] }

function personAt(t: Track, now: number) {
  let cur = null, last = null
  for (const s of t.stops) { if (now >= s.s && now <= s.e) cur = s; if (s.e <= now) last = s }
  if (cur) return { ...cur, active: true }
  if (last && now - last.e <= 30) return { ...last, active: false }
  return null
}

export default function FloorIso({ getContainer }: { getContainer?: () => HTMLElement }) {
  const [date, setDate] = useState<Dayjs>(dayjs())
  const [data, setData] = useState<WrFloors | null>(null)
  const [plan, setPlan] = useState<HotelFloorPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sel, setSel] = useState<string | null>(null)
  const [explode, setExplode] = useState(false)
  const [now, setNow] = useState(() => dayjs().hour() * 60 + dayjs().minute())
  const [playing, setPlaying] = useState(false)
  const [lift, setLift] = useState(0)
  const [asset, setAsset] = useState<AssetTarget | null>(null)
  const [repair, setRepair] = useState<WrRepair | null>(null)
  const [row, setRow] = useState<JournalRow | null>(null)

  const isToday = date.isSame(dayjs(), 'day')

  useEffect(() => { fetchWarRoomHotelPlan().then(setPlan).catch(() => setPlan(null)) }, [])

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const d = await fetchWarRoomFloors(date.format('YYYY-MM-DD'))
      setData(d)
      // 過去日期：時間停在最後一筆工作；今天：停在現在
      if (!date.isSame(dayjs(), 'day')) {
        const ends = d.floors.flatMap(f => f.people.flatMap(p => p.stops.map(s => toMin(s.start_time))))
        setNow(ends.length ? Math.max(...ends) : 17 * 60)
      } else {
        setNow(dayjs().hour() * 60 + dayjs().minute())
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [date])
  useEffect(() => { load() }, [load])

  // ── 樓層由下而上（不含「未定位」）──
  const floors = useMemo(() => [...(data?.floors ?? [])].filter(f => f.key !== '__unknown').reverse(), [data])
  const unknown = data?.floors.find(f => f.key === '__unknown') ?? null
  const order = floors.map(f => f.key)

  // ── 人員軌跡 ──
  const tracks: Track[] = useMemo(() => {
    const m = new Map<string, Track>()
    for (const f of data?.floors ?? []) {
      if (f.key === '__unknown') continue
      for (const p of f.people) {
        const t = m.get(p.person) ?? { person: p.person, stops: [] }
        for (const st of p.stops) {
          const s = toMin(st.start_time)
          t.stops.push({ floor: f.key, room: st.room, s, e: Math.max(toMin(st.end_time || st.start_time), s + 6), stop: st })
        }
        m.set(p.person, t)
      }
    }
    return [...m.values()].map(t => ({ ...t, stops: t.stops.sort((a, b) => a.s - b.s) })).sort((a, b) => a.person.localeCompare(b.person))
  }, [data])
  const colorOf = useCallback((n: string) => {
    const i = tracks.findIndex(t => t.person === n)
    return PERSON_COLORS[(i < 0 ? 0 : i) % PERSON_COLORS.length]
  }, [tracks])

  // 時間軸範圍：當天第一筆～最後一筆（前後各留半小時），至少 08:00～18:00
  const [tMin, tMax] = useMemo(() => {
    const all = tracks.flatMap(t => t.stops.flatMap(s => [s.s, s.e]))
    return [Math.min(480, ...all.map(v => v - 30)), Math.max(1080, ...all.map(v => v + 30))]
  }, [tracks])

  // ── 播放 ──
  useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => {
      setNow(v => { if (v >= tMax) { setPlaying(false); return v } return v + 3 })
    }, 60)
    return () => window.clearInterval(id)
  }, [playing, tMax])

  // ── 選取樓層時上方樓層抬升（動畫）──
  const target = sel ? (explode ? EXPLODE : 30) : 0
  const raf = useRef<number>()
  useEffect(() => {
    const step = () => {
      setLift(v => {
        const d = target - v
        if (Math.abs(d) < 0.5) return target
        raf.current = requestAnimationFrame(step)
        return v + d * 0.2
      })
    }
    raf.current = requestAnimationFrame(step)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [target])

  const zOf = (k: string) => {
    const i = order.indexOf(k)
    let z = i * GAP
    if (sel && i > order.indexOf(sel)) z += lift
    return z
  }

  // ── 客房標準層：房號尾碼 → 多邊形 ──
  const guestUnits = useMemo(() => plan?.units ?? [], [plan])
  const planXY = (b: Box, px: number, py: number): [number, number] =>
    [b.x + (px / (plan?.width || 1000)) * b.w, b.y + (py / (plan?.height || 665)) * b.d]
  const roomNoOf = (floorKey: string, suffix: string | null) => {
    const n = parseInt(floorKey, 10)
    return suffix && !Number.isNaN(n) ? `${n}${suffix}` : null
  }
  const unitCenter = (f: WrFloor, room: string) => {
    const u = guestUnits.find(x => x.kind === 'room' && roomNoOf(f.key, x.suffix) === room)
    return u ? planXY(boxOf(f.key), u.center[0], u.center[1]) : null
  }

  // viewBox：依最大抬升高度固定，避免畫面跳動
  const viewBox = useMemo(() => {
    const xs: number[] = [], ys: number[] = []
    for (const b of [PODIUM, TOWER]) for (const [x, y] of [[b.x, b.y], [b.x + b.w, b.y], [b.x, b.y + b.d], [b.x + b.w, b.y + b.d]])
      for (const z of [0, Math.max(order.length, 1) * GAP + (explode ? EXPLODE : 30) + 30]) { const p = iso(x, y, z); xs.push(p[0]); ys.push(p[1]) }
    const minX = Math.min(...xs) - 90, minY = Math.min(...ys) - 10
    return `${minX} ${minY} ${Math.max(...xs) - minX + 20} ${Math.max(...ys) - minY + 10}`
  }, [order.length, explode])

  const selFloor = floors.find(f => f.key === sel) ?? null
  const visitsOf = (room: string) =>
    (data?.floors ?? []).flatMap(f => f.people.flatMap(p => p.stops.filter(st => st.room === room).map(st => ({ person: p.person, stop: st }))))
      .filter((v, i, arr) => arr.findIndex(x => x.person === v.person && x.stop.seq === v.stop.seq) === i)

  const stop = (e: React.MouseEvent) => e.stopPropagation()

  // ── 樓板 ──
  const slabs = floors.map(f => {
    const b = boxOf(f.key), z = zOf(f.key), c = COL[floorLevel(f)], active = sel === f.key
    const T = (x: number, y: number) => iso(x, y, z + TH), B = (x: number, y: number) => iso(x, y, z)
    const A: [number, number] = [b.x, b.y], Bc: [number, number] = [b.x + b.w, b.y]
    const Cc: [number, number] = [b.x + b.w, b.y + b.d], D: [number, number] = [b.x, b.y + b.d]
    const lp = iso(b.x, b.y + b.d, z + TH / 2)
    const top = (x: number, y: number) => iso(x, y, z + TH + 0.6)
    const showGuest = f.kind === 'guest' && guestUnits.length > 0
    const roomSet = new Set(f.rooms)
    const visited = new Set(f.rooms_visited)
    const repByRoom = new Map<string, WrRepair[]>()
    f.repairs.forEach(r => { if (r.room) repByRoom.set(r.room, [...(repByRoom.get(r.room) ?? []), r]) })
    const loose = f.repairs.filter(r => !r.room || !showGuest)

    return (
      <g key={f.key} opacity={sel && !active ? 0.3 : 1} style={{ cursor: 'pointer', transition: 'opacity .2s', outline: 'none' }}
         onClick={() => setSel(active ? null : f.key)} role="button" tabIndex={0}
         onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSel(active ? null : f.key) } }}
         aria-label={`${f.label}：人員 ${f.people_count}、未完成報修 ${f.repairs_count}`}>
        <title>{`${f.label}｜人員 ${f.people_count}・工作 ${f.stops} 件・未完成報修 ${f.repairs_count}・巡檢 ${f.points.length} 點`}</title>
        <polygon points={P([T(...D), T(...Cc), B(...Cc), B(...D)])} fill={c} fillOpacity={0.5} stroke={c} strokeOpacity={0.8} strokeWidth={0.6} />
        <polygon points={P([T(...Bc), T(...Cc), B(...Cc), B(...Bc)])} fill={c} fillOpacity={0.32} stroke={c} strokeOpacity={0.8} strokeWidth={0.6} />
        <polygon points={P([T(...A), T(...Bc), T(...Cc), T(...D)])} fill={c} fillOpacity={active ? 0.28 : 0.13} stroke={c} strokeWidth={active ? 1.6 : 0.8} />

        {/* 客房層：向量標準層 */}
        {showGuest && plan && (
          <>
            <polygon points={P(plan.corridor.map(([px, py]) => top(...planXY(b, px, py))))} fill="#0b1220" fillOpacity={0.55} />
            {guestUnits.map(u => {
              const pts = P(u.poly.map(([px, py]) => top(...planXY(b, px, py))))
              if (u.kind !== 'room') return <polygon key={u.key} points={pts} fill="#2a3a58" fillOpacity={0.6} />
              const room = roomNoOf(f.key, u.suffix)
              if (!room || !roomSet.has(room)) return null
              const reps = repByRoom.get(room) ?? []
              const v = visited.has(room)
              const fill = reps.some(r => (r.wait_days ?? 0) > 7) ? COL.bad : reps.length ? COL.warn : v ? COL.ok : COL.room
              return (
                <polygon key={u.key} points={pts} fill={fill} fillOpacity={reps.length ? 0.9 : v ? 0.55 : 0.75}
                         stroke={v ? COL.ok : '#0b1220'} strokeWidth={v ? 1.2 : 0.5}
                         onClick={e => { stop(e); setAsset({ type: 'room', room }) }}>
                  <title>{`${room}${reps.length ? `・未完成報修 ${reps.length} 件` : ''}${v ? '・今天有人到訪' : ''}（點開看房間履歷）`}</title>
                </polygon>
              )
            })}
          </>
        )}

        {/* 巡檢點位：樓層巡檢圖的比例座標 */}
        {f.points.map(p => {
          const [x, y] = [b.x + p.x * b.w, b.y + p.y * b.d]
          const q = 0.32
          return (
            <polygon key={p.id} points={P([top(x - q, y - q), top(x + q, y - q), top(x + q, y + q), top(x - q, y + q)])}
                     fill={POINT_COL[p.status] ?? POINT_COL.no_record} stroke="#0b1220" strokeWidth={0.5}
                     onClick={e => { stop(e); setAsset({ type: 'point', id: p.id, label: p.label }) }}>
              <title>{`${p.label}（${p.module_label}）：${{ normal: '正常', abnormal: '異常', unchecked: '未填', no_record: '無紀錄' }[p.status]}`}</title>
            </polygon>
          )
        })}

        {/* 沒有房號的報修：沿樓板前緣排列的釘子（位置不代表實際地點） */}
        {loose.map((r, i) => {
          const n = loose.length
          const x = b.x + 1 + ((i + 0.5) / Math.max(n, 1)) * (b.w - 2)
          const y = b.y + b.d - 1 - (hash(r.ragic_id + r.source) % 10) / 10
          const base = iso(x, y, z + TH), head = iso(x, y, z + TH + 13)
          const c2 = (r.wait_days ?? 0) > 7 ? COL.bad : COL.warn
          return (
            <g key={`${r.source}-${r.ragic_id}`} onClick={e => { stop(e); setRepair(r) }}>
              <line x1={base[0]} y1={base[1]} x2={head[0]} y2={head[1]} stroke={c2} strokeWidth={1.2} />
              <circle cx={head[0]} cy={head[1]} r={3.4} fill={c2} />
              <title>{`${r.title}（${r.source_label}・等 ${r.wait_days ?? '—'} 天）`}</title>
            </g>
          )
        })}

        <text x={lp[0] - 10} y={lp[1] + 5} textAnchor="end" fontSize={16} fontWeight={600}
              fontFamily="ui-monospace, Menlo, monospace" fill={active ? COL.accent : PANEL_TEXT}>{f.label}</text>
        {f.repairs_count > 0 && (
          <text x={lp[0] - 50} y={lp[1] + 4} textAnchor="end" fontSize={11} fill={PANEL_MUTED}>報修 {f.repairs_count}</text>
        )}
      </g>
    )
  })

  // ── 人員 ──
  const slots: Record<string, number> = {}
  const markers = tracks.map(t => {
    const at = personAt(t, now)
    if (!at) return null
    const f = floors.find(x => x.key === at.floor)
    if (!f) return null
    const b = boxOf(f.key)
    const c0 = at.room && f.kind === 'guest' ? unitCenter(f, at.room) : null
    let [x, y] = c0 ?? [b.x + b.w * 0.35, b.y + b.d * 0.5]
    const key = at.floor + (at.room ?? '')
    const n = (slots[key] = (slots[key] ?? 0) + 1) - 1
    x += n * 1.1
    const z = zOf(f.key) + TH + 1
    const base = iso(x, y, z), head = iso(x, y, z + 26), c = colorOf(t.person)
    return (
      <g key={t.person} opacity={sel && sel !== f.key ? 0.3 : 1} style={{ cursor: 'pointer' }}
         onClick={() => setRow(at.stop.row)}>
        <title>{`${t.person}　${at.stop.start_time}–${at.stop.end_time || ''}　${at.stop.task}${at.active ? '（進行中）' : '（剛結束）'}`}</title>
        <line x1={base[0]} y1={base[1]} x2={head[0]} y2={head[1]} stroke={c} strokeWidth={1.4} strokeDasharray={at.active ? undefined : '2 2'} />
        <ellipse cx={base[0]} cy={base[1]} rx={6} ry={2.6} fill={c} fillOpacity={0.4} />
        {at.active && (
          <circle cx={head[0]} cy={head[1]} r={12} fill="none" stroke={c} strokeWidth={1.5} className="wr-iso-pulse">
            <animate attributeName="r" values="12;21;12" dur="1.6s" repeatCount="indefinite" />
            <animate attributeName="opacity" values=".9;0;.9" dur="1.6s" repeatCount="indefinite" />
          </circle>
        )}
        <circle cx={head[0]} cy={head[1]} r={12} fill={c} stroke="#0b1220" strokeWidth={1.5} />
        <text x={head[0]} y={head[1] + 4} textAnchor="middle" fontSize={10} fontWeight={700} fill="#06101f">{shortName(t.person)}</text>
      </g>
    )
  })

  // ── 右側 ──
  const nowList = tracks.map(t => ({ t, at: personAt(t, now) })).filter(x => x.at)
  const sideRepairs = (selFloor ? selFloor.repairs : floors.flatMap(f => f.repairs))
    .slice().sort((a, b) => (b.wait_days ?? 0) - (a.wait_days ?? 0))
  const floorStops = selFloor
    ? selFloor.people.flatMap(p => p.stops.map(s => ({ person: p.person, s }))).sort((a, b) => a.s.start_time.localeCompare(b.s.start_time))
    : []
  const attention: WrPoint[] = (selFloor ? selFloor.points : []).filter(p => p.status === 'abnormal' || p.status === 'unchecked')

  const rowStyle: React.CSSProperties = { display: 'flex', gap: 8, alignItems: 'center', fontSize: 13, padding: '5px 0', borderBottom: '1px solid rgba(127,155,184,0.15)', cursor: 'pointer' }
  const chip = (t: React.ReactNode, color = PANEL_MUTED) => (
    <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 11, border: `1px solid ${color}55`, color, borderRadius: 3, padding: '0 4px', flex: 'none' }}>{t}</span>
  )
  const h3 = (t: React.ReactNode) => <div style={{ fontSize: 12, color: PANEL_MUTED, margin: '12px 0 4px', letterSpacing: 1 }}>{t}</div>
  const ell: React.CSSProperties = { flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }
  const dot = (n: string) => (
    <span style={{ width: 22, height: 22, borderRadius: '50%', background: colorOf(n), color: '#06101f', fontSize: 10, fontWeight: 700, display: 'grid', placeItems: 'center', flex: 'none' }}>{shortName(n)}</span>
  )
  const repairRow = (r: WrRepair, withFloor: boolean) => {
    const w = r.wait_days ?? 0
    const c = w > 7 ? COL.bad : w > 3 ? COL.warn : PANEL_MUTED
    return (
      <div key={`${r.source}-${r.ragic_id}`} style={rowStyle} onClick={() => setRepair(r)}>
        <span style={{ width: 46, textAlign: 'right', color: c, fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12, flex: 'none' }}>{r.wait_days ?? '—'} 天</span>
        {r.room ? chip(r.room, COL.ok) : withFloor && r.floors[0] ? chip(r.floors[0].toUpperCase()) : null}
        <span style={ell} title={r.title}>{r.title}</span>
        <span style={{ fontSize: 10, borderRadius: 3, padding: '0 4px', background: r.source === 'dazhi' ? '#1565C0' : '#2E7D32', color: '#fff', flex: 'none' }}>{r.source === 'dazhi' ? '飯' : '商'}</span>
      </div>
    )
  }

  const side = selFloor ? (
    <>
      <FloorPlan2D floor={selFloor} plan={plan} onRoom={room => setAsset({ type: 'room', room })}
                   onPoint={p => setAsset({ type: 'point', id: p.id, label: p.label })}
                   people={tracks.map(t => ({ t, at: personAt(t, now) })).filter(x => x.at?.floor === selFloor.key)
                     .map(x => ({ person: x.t.person, room: x.at!.room, active: x.at!.active, color: colorOf(x.t.person) }))} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {[[selFloor.people_count, '人'], [selFloor.repairs_count, '未完成報修'],
          [selFloor.points.length ? `${selFloor.point_status.normal}/${selFloor.points.length}` : '—', '巡檢正常']].map(([v, l]) => (
          <div key={String(l)} style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 6, padding: '6px 8px' }}>
            <div style={{ fontSize: 20, fontWeight: 600, fontFamily: 'ui-monospace, Menlo, monospace' }}>{v}</div>
            <div style={{ fontSize: 11, color: PANEL_MUTED }}>{l}</div>
          </div>
        ))}
      </div>
      {h3('今天在這層的工作')}
      {floorStops.length ? floorStops.map(({ person, s }) => (
        <div key={`${person}-${s.seq}`} style={rowStyle} onClick={() => setRow(s.row)}>
          {dot(person)}
          <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 12, color: PANEL_MUTED, flex: 'none' }}>{s.start_time}</span>
          {s.room && chip(s.room, COL.ok)}
          <span style={ell} title={s.task}>{s.task}</span>
        </div>
      )) : <div style={{ fontSize: 12, color: PANEL_MUTED }}>沒有工作紀錄</div>}
      {selFloor.points.length > 0 && (
        <>
          {h3(`巡檢點位需注意 ${attention.length}`)}
          {attention.length ? attention.map(p => (
            <div key={p.id} style={rowStyle} onClick={() => setAsset({ type: 'point', id: p.id, label: p.label })}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: POINT_COL[p.status], flex: 'none' }} />
              <span style={ell}>{p.label}</span>
              <span style={{ fontSize: 12, color: POINT_COL[p.status] }}>{p.status === 'abnormal' ? '異常' : '未填'}</span>
            </div>
          )) : <div style={{ fontSize: 12, color: PANEL_MUTED }}>沒有異常或未填（無紀錄 {selFloor.point_status.no_record} 點）</div>}
        </>
      )}
      {h3(`未完成報修 ${selFloor.repairs_count}（等待最久在前）`)}
      {sideRepairs.length ? sideRepairs.map(r => repairRow(r, false)) : <div style={{ fontSize: 12, color: PANEL_MUTED }}>沒有未完成報修</div>}
    </>
  ) : (
    <>
      {h3(`${mm(now)} 誰在哪`)}
      {nowList.length ? nowList.map(({ t, at }) => (
        <div key={t.person} style={rowStyle} onClick={() => setRow(at!.stop.row)}>
          {dot(t.person)}
          {chip(`${at!.floor.toUpperCase()}${at!.room ? ` ${at!.room}` : ''}`, COL.accent)}
          <span style={ell} title={at!.stop.task}>{at!.stop.task}</span>
          <span style={{ fontSize: 11, color: at!.active ? COL.ok : PANEL_MUTED, flex: 'none' }}>{at!.active ? '進行中' : '剛結束'}</span>
        </div>
      )) : <div style={{ fontSize: 12, color: PANEL_MUTED }}>這個時間沒有人在工作紀錄中</div>}
      {unknown && unknown.people_count > 0 && (
        <div style={{ fontSize: 11, color: PANEL_MUTED, marginTop: 6 }}>另有 {unknown.people_count} 人的工作無法定位樓層，未放進模型。</div>
      )}
      {h3('等待最久的未完成報修')}
      {sideRepairs.slice(0, 15).map(r => repairRow(r, true))}
    </>
  )

  return (
    <div>
      <Space wrap size={[8, 8]} style={{ marginBottom: 10, width: '100%', justifyContent: 'space-between' }}>
        <Space wrap>
          <Button size="small" icon={<LeftOutlined />} onClick={() => setDate(d => d.subtract(1, 'day'))} />
          <DatePicker size="small" value={date} allowClear={false} onChange={v => v && setDate(v)} getPopupContainer={getContainer} />
          <Button size="small" icon={<RightOutlined />} onClick={() => setDate(d => d.add(1, 'day'))} />
          <Button size="small" onClick={() => setDate(dayjs())}>今天</Button>
          <Space size={4}><Switch size="small" checked={explode} onChange={v => { setExplode(v); if (v && !sel) setSel(floors.find(f => f.kind === 'guest')?.key ?? null) }} /><span style={{ fontSize: 12 }}>展開樓層</span></Space>
          {sel && <Button size="small" onClick={() => setSel(null)}>看全棟</Button>}
        </Space>
        <Space>
          {data && <span style={{ fontSize: 12, color: '#888' }}>更新於 {data.generated_at}</span>}
          <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
        </Space>
      </Space>

      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 10 }} />}

      <Spin spinning={loading && !data}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(280px, 340px)', gap: 12 }} className="wr-iso-grid">
          <Panel title="整棟 3D 樓層" fill={false}
                 extra={<span style={{ fontSize: 11, color: PANEL_MUTED }}>點樓層看明細；客房層每格是一間房；釘子＝沒有房號的報修（位置不代表實際地點）</span>}>
            <svg viewBox={viewBox} style={{ width: '100%', height: 'min(70vh, 780px)', display: 'block' }}
                 role="img" aria-label="整棟等角樓層模型">
              {slabs}
              {markers}
            </svg>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 14px', fontSize: 11, color: PANEL_MUTED }}>
              {[[COL.bad, '報修等超過 7 天／巡檢異常'], [COL.warn, '有未完成報修／巡檢未填'], [COL.ok, '今天有人工作／到訪'], [COL.idle, '無事件'], [POINT_COL.no_record, '巡檢點位（灰＝今天無紀錄）']].map(([c, l]) => (
                <span key={l}><i style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: c, marginRight: 4, verticalAlign: -1 }} />{l}</span>
              ))}
            </div>
          </Panel>
          <Panel title={selFloor ? `${selFloor.label}${selFloor.kind === 'guest' ? '　客房層' : ''}` : '全棟'} fill={false}>
            <div style={{ maxHeight: 'min(70vh, 780px)', overflowY: 'auto', paddingRight: 4 }}>{side}</div>
          </Panel>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 10, padding: '8px 14px', background: '#fff', borderRadius: 8, border: '1px solid #f0f0f0' }}>
          <Tooltip title={playing ? '暫停' : '播放這一天'}>
            <Button size="small" type="primary" icon={playing ? <PauseOutlined /> : <CaretRightOutlined />}
                    onClick={() => { if (!playing && now >= tMax) setNow(tMin); setPlaying(p => !p) }} />
          </Tooltip>
          <span style={{ fontFamily: 'ui-monospace, Menlo, monospace', fontSize: 22, fontWeight: 600, minWidth: 70 }}>{mm(now)}</span>
          <Slider style={{ flex: 1 }} min={tMin} max={tMax} step={1} value={Math.min(Math.max(now, tMin), tMax)}
                  onChange={(v: number) => { setPlaying(false); setNow(v) }} tooltip={{ formatter: v => mm(v ?? 0) }} />
          {isToday && <Button size="small" onClick={() => setNow(dayjs().hour() * 60 + dayjs().minute())}>現在</Button>}
        </div>
      </Spin>

      <style>{`
        @media (max-width: 900px) { .wr-iso-grid { grid-template-columns: minmax(0, 1fr) !important; } }
        @media (prefers-reduced-motion: reduce) { .wr-iso-pulse { display: none; } }
      `}</style>

      <AssetHistoryDrawer
        target={asset}
        date={date.format('YYYY-MM-DD')}
        visits={asset?.type === 'room' ? visitsOf(asset.room) : undefined}
        onClose={() => setAsset(null)}
        onOpenVisit={st => setRow(st.row)}
        onOpenRepair={r => setRepair(r)}
        getContainer={getContainer}
      />
      <RepairDrawer repair={repair} onClose={() => setRepair(null)} onOpenRoom={room => { setRepair(null); setAsset({ type: 'room', room }) }} getContainer={getContainer} />
      <JournalRowDrawer row={row} onClose={() => setRow(null)} getContainer={getContainer} />
    </div>
  )
}

/** 選取樓層的俯視平面（放大看）：客房層畫每間房並標房號；其他樓層畫巡檢點位 */
function FloorPlan2D({ floor, plan, people, onRoom, onPoint }: {
  floor: WrFloor
  plan: HotelFloorPlan | null
  people: { person: string; room: string | null; active: boolean; color: string }[]
  onRoom: (room: string) => void
  onPoint: (p: WrPoint) => void
}) {
  const guest = floor.kind === 'guest' && !!plan
  const W = guest ? plan!.width : 1000, H = guest ? plan!.height : 620
  // 客房層：裁到房間範圍，房號才看得清楚
  let vb = `0 0 ${W} ${H}`
  if (guest) {
    const xs = plan!.units.flatMap(u => u.poly.map(p => p[0])), ys = plan!.units.flatMap(u => u.poly.map(p => p[1]))
    const x0 = Math.min(...xs) - 10, y0 = Math.min(...ys) - 30
    vb = `${x0} ${y0} ${Math.max(...xs) - x0 + 10} ${Math.max(...ys) - y0 + 10}`
  }
  const n = parseInt(floor.key, 10)
  const roomSet = new Set(floor.rooms), visited = new Set(floor.rooms_visited)
  const reps = new Map<string, number>(), long = new Set<string>()
  floor.repairs.forEach(r => { if (r.room) { reps.set(r.room, (reps.get(r.room) ?? 0) + 1); if ((r.wait_days ?? 0) > 7) long.add(r.room) } })
  if (!guest && floor.points.length === 0) return null
  return (
    <svg viewBox={vb} style={{ width: '100%', height: 'auto', display: 'block', background: 'rgba(255,255,255,0.03)', borderRadius: 6, marginBottom: 4 }}>
      {guest && plan ? (
        <>
          <polygon points={plan.corridor.map(p => p.join(',')).join(' ')} fill="#0b1220" fillOpacity={0.5} />
          {plan.units.map(u => {
            const pts = u.poly.map(p => p.join(',')).join(' ')
            if (u.kind !== 'room') return <polygon key={u.key} points={pts} fill="#2a3a58" fillOpacity={0.7} />
            const room = u.suffix && !Number.isNaN(n) ? `${n}${u.suffix}` : null
            if (!room || !roomSet.has(room)) return null
            const fill = long.has(room) ? COL.bad : reps.has(room) ? COL.warn : visited.has(room) ? COL.ok : COL.room
            const here = people.filter(p => p.room === room)
            return (
              <g key={u.key} style={{ cursor: 'pointer' }} onClick={() => onRoom(room)}>
                <title>{`${room}${reps.get(room) ? `・未完成報修 ${reps.get(room)} 件` : ''}${visited.has(room) ? '・今天有人到訪' : ''}`}</title>
                <polygon points={pts} fill={fill} fillOpacity={reps.has(room) ? 0.9 : visited.has(room) ? 0.55 : 0.8}
                         stroke={visited.has(room) ? COL.ok : '#0b1220'} strokeWidth={visited.has(room) ? 3 : 1.5} />
                <text x={u.center[0]} y={u.center[1] + 7} textAnchor="middle" fontSize={24} fontWeight={700}
                      fill={reps.has(room) ? '#06101f' : PANEL_TEXT}>{room}</text>
                {here.map((p, i) => (
                  <circle key={p.person} cx={u.center[0] - 14 + i * 16} cy={u.center[1] - 22} r={9} fill={p.color}
                          stroke="#0b1220" strokeWidth={2} opacity={p.active ? 1 : 0.6} />
                ))}
              </g>
            )
          })}
        </>
      ) : (
        floor.points.map(p => (
          <g key={p.id} style={{ cursor: 'pointer' }} onClick={() => onPoint(p)}>
            <title>{`${p.label}（${p.module_label}）`}</title>
            <circle cx={p.x * W} cy={p.y * H} r={14} fill={POINT_COL[p.status] ?? POINT_COL.no_record} stroke="#0b1220" strokeWidth={2} />
          </g>
        ))
      )}
    </svg>
  )
}
