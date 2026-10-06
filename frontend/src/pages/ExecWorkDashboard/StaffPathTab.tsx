/**
 * 集團工務決策駕駛艙 — 「人員動線」TAB（2026-10-05 新增，第一版）
 *
 * 中文名稱：人員動線　英文名稱：Staff Path
 * 前端路由：/exec-work-dashboard（TAB key: staff-path）
 * 後端 router：backend/app/routers/work_journal_path.py（/api/v1/work-journal/path/*）
 * 資料來源：工作日誌（_build_daily，具名人員）＋ services/staff_path/locator.py 位置解析
 *
 * 畫面：
 *  ① KPI（4 欄）
 *  ② 大樓剖面運行圖：X＝時間、Y＝樓層（RF～B4F），每人一條線；換層＝垂直線段
 *  ③ 樓層平面動線：客房層（5F～10F）用依 5F 疏散圖描繪的標準層向量圖，沿走道畫路徑；
 *     其他樓層顯示共用底圖＋該層工作清單（第一版尚無點位座標）
 *  ④ 停留點清單（點列開明細 Drawer，§7）
 *
 * ⚠️ 路徑是依時間把「工作地點」串起來的推定動線，不是定位軌跡。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Row, Col, Card, Statistic, Typography, Tag, Table, Segmented, DatePicker, Button, Space,
  Select, Spin, Empty, Alert, Tooltip, Slider, Switch, ConfigProvider,
} from 'antd'
import {
  LeftOutlined, RightOutlined, ReloadOutlined, CaretRightOutlined, PauseOutlined,
  StepBackwardOutlined, InfoCircleOutlined, WarningOutlined,
  FullscreenOutlined, FullscreenExitOutlined,
} from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import {
  fetchStaffPathDay, fetchHotelFloorPlan, fetchSharedFloorImageUrl,
  CONFIDENCE_LABEL, CONFIDENCE_COLOR,
  type StaffPathDay, type PathPerson, type PathStop, type PathFloor, type HotelFloorPlan,
} from '@/api/staffPath'
import type { JournalVenue } from '@/api/workJournal'
import JournalRowDrawer from '@/components/WorkJournal/JournalRowDrawer'
import StaffLiveBoard from './StaffLiveBoard'
import StaffWorkBoard from './StaffWorkBoard'
import { useDayClock } from './staffClock'
import { FLOOR_MAP_STATUS } from '@/components/FloorPlanMap/status'
import {
  PANEL_BG, PANEL_TEXT, PANEL_MUTED, GRID, PERSON_COLORS,
  fmtMin, useWidth, Panel, buildCenterline, type Pt,
} from './staffPathShared'

const { Text } = Typography

const FLOOR_KIND_LABEL: Record<PathFloor['kind'], string> = { guest: '客房', plan: '公區', none: '' }

// ══════════════════════════════════════════════════════════════════════════════
// ② 大樓剖面運行圖
// ══════════════════════════════════════════════════════════════════════════════
function BuildingTimeline({
  floors, persons, colorOf, selected, onlySelected, activeStop, onStopClick,
}: {
  floors: PathFloor[]
  persons: PathPerson[]
  colorOf: (p: string) => string
  selected: string | null
  onlySelected: boolean
  activeStop: PathStop | null
  onStopClick: (person: string, s: PathStop) => void
}) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const shown = onlySelected && selected ? persons.filter(p => p.person === selected) : persons

  const ROW = 26, TOP = 22, LEFT = 74, RIGHT = 12
  const rows = [...floors.map(f => f.key), '__unknown']
  const height = TOP + rows.length * ROW + 6
  const rowY = (k: string) => TOP + rows.indexOf(k) * ROW + ROW / 2

  // 時間範圍：所有顯示人員的停留點，取整點；無資料時 08:00～18:00
  const [t0, t1] = useMemo(() => {
    const ts: number[] = []
    shown.forEach(p => p.stops.forEach(s => {
      if (s.start_min != null) ts.push(s.start_min)
      if (s.end_min != null) ts.push(s.end_min)
    }))
    if (!ts.length) return [480, 1080]
    const lo = Math.max(-240, Math.floor((Math.min(...ts) - 15) / 60) * 60)
    const hi = Math.min(1680, Math.ceil((Math.max(...ts) + 15) / 60) * 60)
    return [lo, Math.max(hi, lo + 120)]
  }, [shown])

  const x = (m: number) => LEFT + ((m - t0) / (t1 - t0)) * (width - LEFT - RIGHT)
  const hourStep = (t1 - t0) / 60 > 14 ? 120 : 60
  const ticks: number[] = []
  for (let m = Math.ceil(t0 / hourStep) * hourStep; m <= t1; m += hourStep) ticks.push(m)

  return (
    <div ref={ref} style={{ width: '100%', overflowX: 'hidden' }}>
      <svg width={width} height={height} style={{ display: 'block' }}>
        {/* 樓層列 */}
        {rows.map((k, i) => {
          const f = floors.find(ff => ff.key === k)
          const y = TOP + i * ROW
          const isGuest = f?.kind === 'guest'
          return (
            <g key={k}>
              <rect x={LEFT} y={y + 1} width={width - LEFT - RIGHT} height={ROW - 2}
                    fill={k === '__unknown' ? 'rgba(255,255,255,0.03)' : isGuest ? 'rgba(75,168,232,0.07)' : 'rgba(255,255,255,0.025)'} rx={3} />
              <text x={8} y={y + ROW / 2 + 4} fill={k === '__unknown' ? PANEL_MUTED : '#fff'} fontSize={12} fontWeight={600}>
                {k === '__unknown' ? '未定位' : f?.label}
              </text>
              {f && FLOOR_KIND_LABEL[f.kind] && (
                <text x={40} y={y + ROW / 2 + 4} fill={isGuest ? '#4BA8E8' : PANEL_MUTED} fontSize={10}>
                  {FLOOR_KIND_LABEL[f.kind]}
                </text>
              )}
            </g>
          )
        })}
        {/* 時間刻度 */}
        {ticks.map(m => (
          <g key={m}>
            <line x1={x(m)} x2={x(m)} y1={TOP - 4} y2={height - 6} stroke={GRID} />
            <text x={x(m)} y={TOP - 8} fill={PANEL_MUTED} fontSize={10} textAnchor="middle">{fmtMin(m)}</text>
          </g>
        ))}

        {/* 每位人員 */}
        {shown.map(p => {
          const color = colorOf(p.person)
          const dim = !onlySelected && selected && p.person !== selected
          const opacity = dim ? 0.18 : 1
          const timed = p.stops.filter(s => s.start_min != null)
          // 換層連線：前一個「單一樓層」停留點結束 → 下一個單一樓層停留點開始
          const singles = timed.filter(s => s.floors.length === 1)
          let d = ''
          singles.forEach((s, i) => {
            const y = rowY(s.floors[0])
            const xs = x(s.start_min as number)
            const xe = x((s.end_min ?? s.start_min) as number)
            if (i === 0) d += `M${xs},${y} H${xe}`
            else d += ` H${xs} V${y} H${xe}`
          })
          return (
            <g key={p.person} opacity={opacity}>
              {d && <path d={d} fill="none" stroke={color} strokeWidth={selected === p.person ? 2.4 : 1.6}
                          strokeLinejoin="round" />}
              {timed.map(s => {
                const xs = x(s.start_min as number)
                const xe = Math.max(xs + 4, x((s.end_min ?? s.start_min) as number))
                const isActive = activeStop === s
                const title = `${p.person}｜${fmtMin(s.start_min)}–${fmtMin(s.end_min)}｜${s.row.task}`
                  + `\n位置：${s.room ?? (s.floors.map(f => f.toUpperCase()).join('、') || '未定位')}（${CONFIDENCE_LABEL[s.confidence]}）`
                if (s.confidence === 'unknown') {
                  const y = rowY('__unknown')
                  return (
                    <rect key={s.seq} x={xs} y={y - 5} width={xe - xs} height={10} rx={3}
                          fill={color} opacity={0.55} style={{ cursor: 'pointer' }}
                          onClick={() => onStopClick(p.person, s)}>
                      <title>{title}</title>
                    </rect>
                  )
                }
                const ys = s.floors.map(rowY)
                const multi = s.floors.length > 1
                return (
                  <g key={s.seq} style={{ cursor: 'pointer' }} onClick={() => onStopClick(p.person, s)}>
                    {multi && (
                      <line x1={(xs + xe) / 2} x2={(xs + xe) / 2} y1={Math.min(...ys)} y2={Math.max(...ys)}
                            stroke={color} strokeWidth={1} strokeDasharray="2 3" opacity={0.7} />
                    )}
                    {ys.map(y => (
                      <rect key={y} x={xs} y={y - 8} width={xe - xs} height={16} rx={4}
                            fill={color} fillOpacity={multi ? 0.3 : s.estimated ? 0.35 : 0.85}
                            stroke={color} strokeWidth={isActive ? 2.5 : 1}
                            strokeDasharray={multi || s.estimated ? '3 2' : undefined} />
                    ))}
                    {s.room && (xe - xs) > 22 && (
                      <text x={(xs + xe) / 2} y={ys[0] + 4} fill="#0d1e30" fontSize={10} fontWeight={700} textAnchor="middle">
                        {s.room}
                      </text>
                    )}
                    {isActive && (
                      <circle cx={xs} cy={ys[0]} r={7} fill="none" stroke="#fff" strokeWidth={2}>
                        <animate attributeName="r" values="6;11;6" dur="1.2s" repeatCount="indefinite" />
                      </circle>
                    )}
                    <title>{title}</title>
                  </g>
                )
              })}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// ③ 客房標準層平面動線
// ══════════════════════════════════════════════════════════════════════════════
function HotelFloorView({
  plan, floor, stops, allStopsCount, color, activeSeq, onStopClick,
}: {
  plan: HotelFloorPlan
  floor: PathFloor
  stops: PathStop[]          // 此人在此樓層的停留點（已依時間、已依回放進度截斷）
  allStopsCount: number
  color: string
  activeSeq: number | null
  onStopClick: (s: PathStop) => void
}) {
  const prefix = floor.key.replace('f', '')
  const roomSet = useMemo(() => new Set(floor.rooms), [floor.rooms])
  const cl = useMemo(() => buildCenterline(plan), [plan])

  const roomUnit = useMemo(() => {
    const m = new Map<string, HotelFloorPlan['units'][number]>()
    plan.units.forEach(u => { if (u.kind === 'room' && u.suffix) m.set(u.suffix, u) })
    return m
  }, [plan])
  const elevators = plan.units.filter(u => u.kind === 'elevator')

  // 房號 → 停留序號
  const visits = new Map<string, number[]>()
  const extraVisits = new Set<string>()
  stops.forEach(s => {
    if (s.room && s.floors[0] === floor.key) visits.set(s.room, [...(visits.get(s.room) ?? []), s.seq])
    s.extra_rooms.forEach(r => extraVisits.add(r))
  })

  // 路徑：每一趟「上到本層」各自成段——電梯 → 房 → … → 房 → 電梯（沿走道）
  //  中間若去過別層（序號不連續），就切成新的一趟，避免畫出沒走過的連線
  const roomStops = stops.filter(s => s.room && s.start_min != null && roomUnit.has(s.room.slice(-2)))
  const trips: PathStop[][] = []
  roomStops.forEach(s => {
    const lastTrip = trips[trips.length - 1]
    const prev = lastTrip?.[lastTrip.length - 1]
    const contiguous = prev && !onOtherFloorBetween(prev.seq, s.seq)
    if (lastTrip && contiguous) lastTrip.push(s)
    else trips.push([s])
  })
  function onOtherFloorBetween(a: number, b: number): boolean {
    // stops 只含本層；序號不連續＝中間有一站不在本層
    for (let q = a + 1; q < b; q++) if (!stops.some(x => x.seq === q)) return true
    return false
  }
  const nearestElev = (s: number) => elevators.reduce((best, e) => {
    const es = cl.project(e.door as Pt)
    return Math.abs(es - s) < Math.abs(best.s - s) ? { s: es, door: e.door as Pt } : best
  }, { s: Infinity, door: [0, 0] as Pt })
  const pathDs = trips.map((trip, ti) => {
    const doors = trip.map(s => roomUnit.get((s.room as string).slice(-2))!.door as Pt)
    const sv = doors.map(d => cl.project(d))
    const start = nearestElev(sv[0])
    const pts: Pt[] = [start.door, ...cl.between(start.s, sv[0]), doors[0]]
    for (let i = 1; i < doors.length; i++) pts.push(...cl.between(sv[i - 1], sv[i]), doors[i])
    // 回放中、且是最後一趟（人還在這層）就不畫回電梯
    const stillHere = activeSeq != null && ti === trips.length - 1 && trip[trip.length - 1].seq === activeSeq
    if (!stillHere) {
      const end = nearestElev(sv[sv.length - 1])
      pts.push(...cl.between(sv[sv.length - 1], end.s), end.door)
    }
    return 'M' + pts.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' L')
  })
  const activeStop = stops.find(s => s.seq === activeSeq && s.room)
  const activeDoor = activeStop ? roomUnit.get((activeStop.room as string).slice(-2))?.door : undefined

  const floorLevel = stops.filter(s => !s.room)

  return (
    <div>
      <svg viewBox={`-10 -10 ${plan.width + 20} ${plan.height + 20}`} style={{ width: '100%', display: 'block' }}>
        <style>{`
          @keyframes spDash { to { stroke-dashoffset: -36; } }
          .sp-path { animation: spDash 1.1s linear infinite; }
        `}</style>
        <polygon points={plan.corridor.map(p => p.join(',')).join(' ')}
                 fill="rgba(75,168,232,0.10)" stroke="rgba(75,168,232,0.35)" strokeWidth={1} />
        {plan.units.map(u => {
          const num = u.kind === 'room' ? `${prefix}${u.suffix}` : ''
          const exists = u.kind !== 'room' || roomSet.has(num)
          const v = visits.get(num)
          const isExtra = extraVisits.has(num)
          let fill = 'rgba(22,50,79,0.85)', stroke = 'rgba(91,140,184,0.55)', dash: string | undefined
          if (u.kind === 'elevator') { fill = 'rgba(255,181,71,0.18)'; stroke = 'rgba(255,181,71,0.6)' }
          if (u.kind === 'stair')    { fill = 'rgba(91,228,155,0.14)'; stroke = 'rgba(91,228,155,0.5)' }
          if (u.kind === 'service')  { fill = 'rgba(255,255,255,0.04)'; stroke = 'rgba(127,155,184,0.3)' }
          if (!exists) { fill = 'rgba(255,255,255,0.02)'; dash = '4 3' }
          if (v) { fill = color; stroke = '#fff' }
          else if (isExtra) { fill = `${color}55`; stroke = color }
          const label = u.kind === 'room' ? (exists ? num : '—') : u.label
          return (
            <g key={u.key} style={{ cursor: v ? 'pointer' : 'default' }}
               onClick={() => { if (v) { const s = stops.find(ss => ss.seq === v[v.length - 1]); if (s) onStopClick(s) } }}>
              <polygon points={u.poly.map(p => p.join(',')).join(' ')}
                       fill={fill} fillOpacity={v ? 0.55 : 1} stroke={stroke} strokeWidth={v ? 2 : 1} strokeDasharray={dash} />
              <text x={u.center[0]} y={u.center[1] + 4} textAnchor="middle"
                    fontSize={u.kind === 'room' ? 13 : 11} fontWeight={u.kind === 'room' ? 600 : 400}
                    fill={v ? '#fff' : exists ? '#c9dbec' : '#4c6680'}>
                {label}
              </text>
              {u.kind === 'room' && !exists && <title>{num}：不在 IHG 規範房號清單（可能為合併房／非客房）</title>}
              {v && <title>{num}｜第 {v.join('、')} 站</title>}
            </g>
          )
        })}
        {pathDs.map((d, i) => (
          <g key={i} opacity={i === pathDs.length - 1 ? 1 : 0.6}>
            <path d={d} fill="none" stroke={color} strokeOpacity={0.25} strokeWidth={9} strokeLinejoin="round" strokeLinecap="round" />
            <path d={d} className="sp-path" fill="none" stroke={color} strokeWidth={3.5}
                  strokeDasharray="12 6" strokeLinejoin="round" strokeLinecap="round" />
          </g>
        ))}
        {/* 停留序號徽章 */}
        {[...visits.entries()].map(([num, seqs]) => {
          const u = roomUnit.get(num.slice(-2))
          if (!u) return null
          const label = seqs.join('·')
          const w = Math.max(20, label.length * 8 + 10)
          return (
            <g key={`b-${num}`} transform={`translate(${u.door[0]},${u.door[1]})`} pointerEvents="none">
              <rect x={-w / 2} y={-10} width={w} height={20} rx={10} fill="#0d1e30" stroke={color} strokeWidth={2} />
              <text y={4} textAnchor="middle" fontSize={11} fontWeight={700} fill="#fff">{label}</text>
            </g>
          )
        })}
        {activeDoor && (
          <circle cx={activeDoor[0]} cy={activeDoor[1]} r={10} fill={color} stroke="#fff" strokeWidth={2}>
            <animate attributeName="r" values="9;16;9" dur="1.2s" repeatCount="indefinite" />
            <animate attributeName="fill-opacity" values="1;0.35;1" dur="1.2s" repeatCount="indefinite" />
          </circle>
        )}
      </svg>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 12, color: PANEL_MUTED, marginTop: 4 }}>
        <span>房號 {visits.size} 間｜本層停留 {stops.length} 站、上下樓 {trips.length} 趟（全日 {allStopsCount} 站）</span>
        <span><span style={{ color: '#FFB547' }}>■</span> 電梯　<span style={{ color: '#5BE49B' }}>■</span> 樓梯　虛線框＝非規範房號</span>
      </div>
      {floorLevel.length > 0 && (
        <div style={{ marginTop: 6 }}>
          <Text style={{ color: PANEL_MUTED, fontSize: 12 }}>本層樓層級工作（無房號）：</Text>
          <Space size={[4, 4]} wrap style={{ marginTop: 2 }}>
            {floorLevel.map(s => (
              <Tag key={s.seq} color="geekblue" style={{ cursor: 'pointer' }} onClick={() => onStopClick(s)}>
                #{s.seq} {fmtMin(s.start_min)} {s.row.task.slice(0, 18)}
              </Tag>
            ))}
          </Space>
        </div>
      )}
    </div>
  )
}

// ── 其他樓層：共用底圖＋清單 ──────────────────────────────────────────────────
function PlainFloorView({ floor, stops, color, activeSeq, onStopClick }: {
  floor: PathFloor; stops: PathStop[]; color: string; activeSeq: number | null; onStopClick: (s: PathStop) => void
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [size, setSize] = useState<{ w: number; h: number } | null>(null)
  useEffect(() => {
    if (floor.kind !== 'plan') { setUrl(null); return }
    let alive = true, made: string | null = null
    setErr(null); setUrl(null); setSize(null)
    fetchSharedFloorImageUrl(floor.key)
      .then(u => { made = u; if (alive) setUrl(u); else URL.revokeObjectURL(u) })
      .catch(e => { if (alive) setErr(e?.response?.status === 403 ? '沒有樓層底圖的檢視權限' : '底圖載入失敗') })
    return () => { alive = false; if (made) URL.revokeObjectURL(made) }
  }, [floor.key, floor.kind])

  // 本層每個巡檢停留點的點位（依樓層巡檢圖 sort_order＝推測順序）
  const tours = stops
    .map(s => ({ stop: s, pts: (s.points ?? []).filter(p => p.floor_key === floor.key) }))
    .filter(t => t.pts.length > 0)
  const statusCount: Record<string, number> = {}
  tours.forEach(t => t.pts.forEach(p => { statusCount[p.status] = (statusCount[p.status] ?? 0) + 1 }))
  const k = size ? size.w / 650 : 1   // 圖面尺寸不一，標記大小依底圖寬度縮放

  return (
    <div>
      <div style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', background: 'rgba(255,255,255,0.04)', minHeight: 160 }}>
        {url
          ? <img src={url} alt={`${floor.label} 平面圖`}
                 onLoad={e => setSize({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })}
                 style={{ width: '100%', display: 'block', filter: 'invert(0.92) hue-rotate(180deg) brightness(0.9)', opacity: 0.55 }} />
          : (
            <div style={{ padding: 28, textAlign: 'center', color: PANEL_MUTED }}>
              {floor.kind === 'none' ? `${floor.label} 尚無平面圖` : err ?? <Spin size="small" />}
            </div>
          )}
        {url && size && tours.length > 0 && (
          <svg viewBox={`0 0 ${size.w} ${size.h}`} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
            <style>{`@keyframes spDash2 { to { stroke-dashoffset: ${-36 * k}; } } .sp-path2 { animation: spDash2 1.1s linear infinite; }`}</style>
            {tours.map(({ stop, pts }, ti) => {
              const xy = pts.map(p => [p.x * size.w, p.y * size.h] as const)
              const d = 'M' + xy.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' L')
              const dim = activeSeq != null && stop.seq !== activeSeq
              return (
                <g key={stop.seq} opacity={dim ? 0.35 : 1}>
                  {xy.length > 1 && (
                    <>
                      <path d={d} fill="none" stroke={color} strokeOpacity={0.25} strokeWidth={10 * k} strokeLinejoin="round" />
                      <path d={d} className="sp-path2" fill="none" stroke={color} strokeWidth={3.5 * k}
                            strokeDasharray={`${12 * k} ${6 * k}`} strokeLinejoin="round" strokeLinecap="round" />
                    </>
                  )}
                  {pts.map((p, i) => {
                    const st = FLOOR_MAP_STATUS[p.status] ?? FLOOR_MAP_STATUS.no_record
                    const [x, y] = xy[i]
                    return (
                      <g key={p.id} style={{ cursor: 'pointer' }} onClick={() => onStopClick(stop)}>
                        <circle cx={x} cy={y} r={11 * k} fill={st.color} stroke={i === 0 ? '#fff' : color}
                                strokeWidth={(i === 0 ? 3 : 2) * k} strokeDasharray={p.placement === 'confirmed' ? undefined : `${3 * k} ${2 * k}`} />
                        <text x={x} y={y + 4 * k} textAnchor="middle" fontSize={11 * k} fontWeight={700} fill="#0d1e30">{i + 1}</text>
                        <title>
                          {`#${stop.seq}-${i + 1} ${p.label}${p.equipment_code ? `（${p.equipment_code}）` : ''}\n`
                            + `當日狀態：${st.label}｜${p.group_label}${p.shared_label ? `｜${p.shared_label}` : ''}`
                            + (p.placement !== 'confirmed' ? '\n點位位置尚未校正' : '')
                            + (tours.length > 1 ? `\n第 ${ti + 1} 趟巡檢` : '')}
                        </title>
                      </g>
                    )
                  })}
                </g>
              )
            })}
          </svg>
        )}
      </div>

      {tours.length > 0 && (
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center', fontSize: 12, color: PANEL_MUTED, marginTop: 6 }}>
          {(Object.keys(FLOOR_MAP_STATUS) as (keyof typeof FLOOR_MAP_STATUS)[]).map(key => (
            <span key={key}>
              <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 5, background: FLOOR_MAP_STATUS[key].color, marginRight: 4 }} />
              {FLOOR_MAP_STATUS[key].label} {statusCount[key] ?? 0}
            </span>
          ))}
          <Tooltip title="巡檢紀錄只有整張表的起迄時間，沒有每一點的檢查時間；連線順序依樓層巡檢圖的點位排序推測，不代表實際走法。狀態為當日彙總（同日多次巡檢合併）。">
            <span style={{ color: '#FFB547' }}><WarningOutlined /> 連線順序為推測</span>
          </Tooltip>
          <span>白框＝起點　虛線圈＝點位尚未校正</span>
        </div>
      )}

      <Space size={[4, 4]} wrap style={{ marginTop: 6 }}>
        {stops.map(s => (
          <Tag key={s.seq} color={s.points?.length ? 'cyan' : 'geekblue'} style={{ cursor: 'pointer' }} onClick={() => onStopClick(s)}>
            #{s.seq} {fmtMin(s.start_min)}–{fmtMin(s.end_min)} {s.row.task.slice(0, 20)}
            {s.points?.length ? `（${s.points.filter(p => p.floor_key === floor.key).length} 點）` : ''}
          </Tag>
        ))}
      </Space>
      {floor.kind === 'plan' && tours.length === 0 && stops.length > 0 && (
        <div style={{ fontSize: 12, color: PANEL_MUTED, marginTop: 4 }}>
          這層的工作只定位到「樓層」；商場工務巡檢、整棟巡檢會在底圖上標出巡檢點位。
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// 主元件
// ══════════════════════════════════════════════════════════════════════════════
export default function StaffPathTab() {
  const [date, setDate] = useState<Dayjs>(dayjs())
  const [venue, setVenue] = useState<JournalVenue>('all')
  const [data, setData] = useState<StaffPathDay | null>(null)
  const [plan, setPlan] = useState<HotelFloorPlan | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [person, setPerson] = useState<string | null>(null)
  const [onlySelected, setOnlySelected] = useState(false)
  const [floorKey, setFloorKey] = useState<string | null>(null)
  const [playIdx, setPlayIdx] = useState<number | null>(null)
  const [playing, setPlaying] = useState(false)
  const [drawerStop, setDrawerStop] = useState<PathStop | null>(null)
  // 畫面：大樓視角（剖面時鐘看板）／工作視角（辦公室）／個人動線　2026-10-06 改名＋新增工作視角
  const [view, setView] = useState<'live' | 'work' | 'person'>('live')
  const [loadedAt, setLoadedAt] = useState<Dayjs | null>(null)

  // ── 全螢幕（只把本 TAB 放大；彈出層全部掛在本容器內，否則全螢幕時看不到）──
  const rootRef = useRef<HTMLDivElement>(null)
  const [isFs, setIsFs] = useState(false)
  useEffect(() => {
    const onChange = () => setIsFs(document.fullscreenElement === rootRef.current && !!rootRef.current)
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])
  const toggleFs = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined)
    else rootRef.current?.requestFullscreen().catch(() => undefined)
  }, [])
  const popupContainer = useCallback(() => rootRef.current ?? document.body, [])

  const load = useCallback(async () => {
    setLoading(true); setError(null); setPlaying(false); setPlayIdx(null)
    try {
      const d = await fetchStaffPathDay(date.format('YYYY-MM-DD'), venue)
      setData(d)
      setLoadedAt(dayjs())
      setPerson(prev => (prev && d.persons.some(p => p.person === prev)) ? prev : (d.persons[0]?.person ?? null))
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? '載入失敗')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [date, venue])

  useEffect(() => { load() }, [load])

  // ── 共用時鐘（大樓視角／工作視角）：今天預設 LIVE ──
  const clock = useDayClock(data)
  // LIVE：每 5 分鐘靜默重抓（不轉圈、不重置時間）
  useEffect(() => {
    if (!clock.live) return
    const id = window.setInterval(async () => {
      try {
        const d = await fetchStaffPathDay(date.format('YYYY-MM-DD'), venue)
        setData(d)
        setLoadedAt(dayjs())
      } catch { /* 下一輪再試 */ }
    }, 5 * 60 * 1000)
    return () => window.clearInterval(id)
  }, [clock.live, date, venue])
  // LIVE 跨過午夜：自動換到新的一天（只在「看的是昨天＝剛剛的今天」時觸發，不干擾手動換日）
  const todayRef = useRef<string>(dayjs().format('YYYY-MM-DD'))
  useEffect(() => {
    const today = dayjs().format('YYYY-MM-DD')
    const prev = todayRef.current
    todayRef.current = today
    if (prev !== today && clock.live && data?.date === prev) setDate(dayjs())
  }, [clock.now, clock.live, data])
  useEffect(() => {
    fetchHotelFloorPlan().then(setPlan).catch(() => setPlan(null))
  }, [])

  const colorOf = useMemo(() => {
    const m = new Map<string, string>()
    data?.persons.forEach((p, i) => m.set(p.person, PERSON_COLORS[i % PERSON_COLORS.length]))
    return (p: string) => m.get(p) ?? '#4BA8E8'
  }, [data])

  const cur = data?.persons.find(p => p.person === person) ?? null
  const playable = useMemo(
    () => (cur?.stops ?? []).filter(s => s.start_min != null && s.confidence !== 'unknown'),
    [cur],
  )
  const activeStop = playIdx != null ? playable[playIdx] ?? null : null

  // 樓層頁籤：此人去過的樓層（依建築由上而下）
  const visitedFloors = useMemo(() => {
    if (!data || !cur) return [] as PathFloor[]
    const set = new Set(cur.stops.flatMap(s => s.floors))
    return data.floors.filter(f => set.has(f.key))
  }, [data, cur])

  // 換人時預設到「第一個有房號的樓層」，否則第一站樓層
  useEffect(() => {
    if (!cur) { setFloorKey(null); return }
    const firstRoom = cur.stops.find(s => s.room)
    const first = cur.stops.find(s => s.floors.length)
    setFloorKey(firstRoom?.floors[0] ?? first?.floors[0] ?? null)
    setPlaying(false); setPlayIdx(null)
  }, [cur])

  // 回放
  useEffect(() => {
    if (!playing) return
    const t = window.setInterval(() => {
      setPlayIdx(i => {
        const n = (i ?? -1) + 1
        if (n >= playable.length) { setPlaying(false); return i }
        return n
      })
    }, 1400)
    return () => window.clearInterval(t)
  }, [playing, playable.length])

  useEffect(() => {
    if (activeStop?.floors.length) setFloorKey(activeStop.floors[0])
  }, [activeStop])

  const floor = data?.floors.find(f => f.key === floorKey) ?? null
  const floorStops = useMemo(() => {
    if (!cur || !floorKey) return [] as PathStop[]
    return cur.stops.filter(s =>
      s.floors.includes(floorKey) && (activeStop == null || (s.start_min != null && s.seq <= activeStop.seq)))
  }, [cur, floorKey, activeStop])

  const openStop = (s: PathStop) => setDrawerStop(s)

  // ── KPI ──
  const sum = data?.summary
  const totalChanges = data?.persons.reduce((a, p) => a + p.stats.floor_changes, 0) ?? 0
  const totalRooms = data ? new Set(data.persons.flatMap(p => p.stops.map(s => s.room).filter(Boolean))).size : 0

  const stopColumns = [
    { title: '#', dataIndex: 'seq', key: 'seq', width: 44, align: 'center' as const },
    {
      title: '時間', key: 'time', width: 120,
      render: (_: unknown, s: PathStop) => (
        <Space size={4}>
          <Text style={{ fontSize: 13 }}>{fmtMin(s.start_min)}–{fmtMin(s.end_min)}</Text>
          {s.overlap && <Tooltip title="與前一站時間重疊（同時段多件工作）"><WarningOutlined style={{ color: '#fa8c16' }} /></Tooltip>}
        </Space>
      ),
    },
    {
      title: '位置', key: 'loc', width: 150,
      render: (_: unknown, s: PathStop) => (
        <Space size={4} wrap>
          {s.room
            ? <Tag color="green" style={{ margin: 0 }}>{s.room}</Tag>
            : s.points?.length
              ? <Tag color="cyan" style={{ margin: 0 }}>{s.floors.map(f => f.toUpperCase()).join('、')}｜{s.points.length} 點</Tag>
            : s.floors.length
              ? <Tag color={s.floors.length > 1 ? 'purple' : 'blue'} style={{ margin: 0 }}>
                  {s.floors.length > 3 ? `${s.floors[0].toUpperCase()}～${s.floors[s.floors.length - 1].toUpperCase()}` : s.floors.map(f => f.toUpperCase()).join('、')}
                </Tag>
              : <Text type="secondary">—</Text>}
        </Space>
      ),
    },
    { title: '工作內容', key: 'task', render: (_: unknown, s: PathStop) => <Text>{s.row.task}</Text> },
    { title: '來源', key: 'src', width: 120, render: (_: unknown, s: PathStop) => <Text style={{ fontSize: 12, color: '#666' }}>{s.row.source_label}</Text> },
    {
      title: '工時', key: 'wm', width: 70, align: 'right' as const,
      render: (_: unknown, s: PathStop) => s.work_min != null
        ? <Tooltip title={s.estimated ? '無實際起迄，為預估工時' : undefined}>
            <Text style={{ color: s.estimated ? '#999' : undefined }}>{s.work_min}{s.estimated ? '*' : ''}</Text>
          </Tooltip>
        : '—',
    },
    {
      title: '定位', key: 'conf', width: 90, align: 'center' as const,
      render: (_: unknown, s: PathStop) => (
        <Tooltip title={`依據：${s.basis}`}>
          <Tag color={CONFIDENCE_COLOR[s.confidence]} style={{ margin: 0 }}>{CONFIDENCE_LABEL[s.confidence]}</Tag>
        </Tooltip>
      ),
    },
  ]

  return (
    <ConfigProvider getPopupContainer={popupContainer}>
    <div
      ref={rootRef}
      style={isFs ? { position: 'relative', background: '#f0f4f8', height: '100vh', overflow: 'hidden' } : undefined}
    >
    <div style={isFs ? { height: '100%', overflowY: 'auto', overflowX: 'hidden', padding: 16 } : undefined}>
      {isFs && (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 10 }}>
          <span style={{ fontSize: 20, fontWeight: 700, color: '#1B3A5C' }}>人員動態</span>
          <Text type="secondary">集團工務決策駕駛艙｜{date.format('YYYY-MM-DD')}（{['日', '一', '二', '三', '四', '五', '六'][date.day()]}）</Text>
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>按 Esc 離開全螢幕</Text>
        </div>
      )}
      {/* 工具列 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap size={[12, 8]} style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space wrap>
            <Button size="small" icon={<LeftOutlined />} onClick={() => setDate(d => d.subtract(1, 'day'))} />
            <DatePicker size="small" value={date} allowClear={false} onChange={v => v && setDate(v)} />
            <Button size="small" icon={<RightOutlined />} onClick={() => setDate(d => d.add(1, 'day'))} />
            <Button size="small" onClick={() => setDate(dayjs())}>今天</Button>
            <Segmented
              value={view} onChange={v => setView(v as 'live' | 'work' | 'person')}
              options={[{ label: '大樓視角', value: 'live' }, { label: '工作視角', value: 'work' }, { label: '個人動線', value: 'person' }]}
            />
            <Segmented size="small" value={venue} onChange={v => setVenue(v as JournalVenue)}
                       options={[{ label: '全部', value: 'all' }, { label: '飯店', value: 'hotel' }, { label: '商場', value: 'mall' }]} />
            {view === 'person' && <Select
              size="small" style={{ minWidth: 220 }} placeholder="選擇人員" value={person ?? undefined}
              onChange={v => setPerson(v)}
              options={(data?.persons ?? []).map(p => ({
                value: p.person,
                label: (
                  <Space size={6}>
                    <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 5, background: colorOf(p.person) }} />
                    {p.person}
                    <Text type="secondary" style={{ fontSize: 12 }}>{p.stats.stops} 站／換層 {p.stats.floor_changes}</Text>
                  </Space>
                ),
              }))}
            />}
            {view === 'person' && <Space size={4}>
              <Switch size="small" checked={onlySelected} onChange={setOnlySelected} />
              <Text style={{ fontSize: 13 }}>只看選定人員</Text>
            </Space>}
          </Space>
          <Space>
            <Tooltip title="路徑是依工作日誌時間把「工作地點」串起來的推定動線，不是定位軌跡；兩站之間實際怎麼走，資料裡沒有。">
              <Text type="secondary" style={{ fontSize: 12 }}><InfoCircleOutlined /> 推定動線說明</Text>
            </Tooltip>
            <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
            <Button size="small" type={isFs ? 'default' : 'primary'} ghost={!isFs}
                    icon={isFs ? <FullscreenExitOutlined /> : <FullscreenOutlined />} onClick={toggleFs}>
              {isFs ? '離開全螢幕' : '全螢幕'}
            </Button>
          </Space>
        </Space>
      </Card>

      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}

      <Spin spinning={loading}>
        {/* ① KPI */}
        <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #1B3A5C' }}>
              <Statistic title="出勤人員（具名）" value={sum?.persons ?? 0} suffix="人" valueStyle={{ color: '#1B3A5C', fontWeight: 700 }} />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #4BA8E8' }}>
              <Statistic title="停留點／可定位率" value={sum?.stops ?? 0} suffix={<Text type="secondary" style={{ fontSize: 14 }}>站／{sum?.located_pct ?? 0}%</Text>}
                         valueStyle={{ color: '#4BA8E8', fontWeight: 700 }} />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #52c41a' }}>
              <Statistic title="到訪客房" value={totalRooms} suffix="間" valueStyle={{ color: '#389e0d', fontWeight: 700 }} />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #fa8c16' }}>
              <Statistic title="換層次數（全員）" value={totalChanges} suffix="次" valueStyle={{ color: '#d46b08', fontWeight: 700 }} />
            </Card>
          </Col>
        </Row>

        {!loading && data && data.persons.length === 0 ? (
          <Card><Empty description={`${data.date} 沒有具名人員的工作日誌，可切換到前一天看看`} /></Card>
        ) : data && view === 'live' ? (
          <StaffLiveBoard
            data={data}
            plan={plan}
            colorOf={colorOf}
            clock={clock}
            loadedAt={loadedAt}
            onOpenStop={openStop}
            onFocusPerson={p => { setPerson(p); setView('person') }}
          />
        ) : data && view === 'work' ? (
          <StaffWorkBoard
            data={data}
            colorOf={colorOf}
            clock={clock}
            loadedAt={loadedAt}
            onOpenStop={openStop}
            onFocusPerson={p => { setPerson(p); setView('person') }}
          />
        ) : data && (
          <>
            <Row gutter={[12, 12]}>
              {/* ② 大樓剖面運行圖 */}
              <Col xs={24} xl={13}>
                <Panel
                  title="大樓剖面運行圖（時間 × 樓層）"
                  extra={
                    <Space size={10} style={{ fontSize: 12, color: PANEL_MUTED }}>
                      <span>實心＝單層</span><span>虛框＝跨樓層／預估工時</span><span>垂直線＝換層</span>
                    </Space>
                  }
                >
                  <BuildingTimeline
                    floors={data.floors}
                    persons={data.persons}
                    colorOf={colorOf}
                    selected={person}
                    onlySelected={onlySelected}
                    activeStop={activeStop}
                    onStopClick={(p, s) => { setPerson(p); openStop(s) }}
                  />
                  {cur && (
                    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 8, fontSize: 13 }}>
                      <span><span style={{ color: colorOf(cur.person) }}>●</span> <b style={{ color: '#fff' }}>{cur.person}</b></span>
                      <span>首站 {fmtMin(cur.stats.first_min)}・末站 {fmtMin(cur.stats.last_min)}</span>
                      <span>停留 {cur.stats.stops} 站（可定位 {cur.stats.located}）</span>
                      <span>換層 {cur.stats.floor_changes} 次／垂直移動 {cur.stats.vertical_floors} 層</span>
                      <span>工時 {cur.stats.work_min} 分</span>
                      {cur.stats.overlaps > 0 && <span style={{ color: '#FFB547' }}>時間重疊 {cur.stats.overlaps} 站</span>}
                      {cur.stats.untimed > 0 && <span style={{ color: PANEL_MUTED }}>無時間 {cur.stats.untimed} 站（未畫入）</span>}
                    </div>
                  )}
                </Panel>
              </Col>

              {/* ③ 樓層平面動線 */}
              <Col xs={24} xl={11}>
                <Panel
                  title={<>樓層平面動線{floor ? <span style={{ color: '#4BA8E8' }}>　{floor.label}</span> : null}</>}
                  extra={
                    <Space size={6}>
                      <Tooltip title="回到起點">
                        <Button size="small" ghost icon={<StepBackwardOutlined />}
                                onClick={() => { setPlaying(false); setPlayIdx(null) }} />
                      </Tooltip>
                      <Button size="small" type="primary" disabled={!playable.length}
                              icon={playing ? <PauseOutlined /> : <CaretRightOutlined />}
                              onClick={() => {
                                if (playing) { setPlaying(false); return }
                                if (playIdx == null || playIdx >= playable.length - 1) setPlayIdx(0)
                                setPlaying(true)
                              }}>
                        {playing ? '暫停' : '回放'}
                      </Button>
                    </Space>
                  }
                >
                  <Space size={[4, 4]} wrap style={{ marginBottom: 8 }}>
                    {visitedFloors.map(f => (
                      <Tag.CheckableTag key={f.key} checked={f.key === floorKey}
                                        onChange={() => { setPlaying(false); setFloorKey(f.key) }}
                                        style={{ border: '1px solid rgba(75,168,232,0.5)', color: f.key === floorKey ? '#fff' : PANEL_TEXT }}>
                        {f.label}{f.kind === 'guest' ? ' 客房' : ''}
                      </Tag.CheckableTag>
                    ))}
                    {!visitedFloors.length && <Text style={{ color: PANEL_MUTED }}>此人沒有可定位的樓層</Text>}
                  </Space>

                  {playable.length > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                      <Slider
                        style={{ flex: 1, margin: '4px 6px' }}
                        min={0} max={Math.max(0, playable.length - 1)}
                        value={playIdx ?? playable.length - 1}
                        onChange={v => { setPlaying(false); setPlayIdx(v as number) }}
                        tooltip={{ formatter: v => {
                          const s = playable[v ?? 0]
                          return s ? `#${s.seq} ${fmtMin(s.start_min)} ${s.room ?? s.floors.map(f => f.toUpperCase()).join('、')}` : ''
                        } }}
                      />
                      <Text style={{ color: PANEL_TEXT, fontSize: 12, minWidth: 150 }}>
                        {activeStop
                          ? <>#{activeStop.seq} {fmtMin(activeStop.start_min)}　{activeStop.room ?? activeStop.floors.map(f => f.toUpperCase()).join('、')}</>
                          : '完整路徑'}
                      </Text>
                    </div>
                  )}

                  {floor && cur && (
                    floor.kind === 'guest' && plan
                      ? <HotelFloorView
                          plan={plan}
                          floor={floor}
                          stops={floorStops}
                          allStopsCount={cur.stops.length}
                          color={colorOf(cur.person)}
                          activeSeq={activeStop?.seq ?? null}
                          onStopClick={openStop}
                        />
                      : <PlainFloorView floor={floor} stops={floorStops} color={colorOf(cur.person)}
                                        activeSeq={activeStop?.seq ?? null} onStopClick={openStop} />
                  )}
                  {activeStop && (
                    <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 6, background: 'rgba(255,255,255,0.06)', fontSize: 13 }}>
                      <b style={{ color: '#fff' }}>#{activeStop.seq}</b>　{fmtMin(activeStop.start_min)}–{fmtMin(activeStop.end_min)}　{activeStop.row.task}
                    </div>
                  )}
                </Panel>
              </Col>
            </Row>

            {/* ④ 停留點清單 */}
            {cur && (
              <Card
                size="small"
                style={{ marginTop: 12 }}
                title={<Space><span style={{ color: colorOf(cur.person) }}>●</span>{cur.person} 的停留點（依時間）</Space>}
                extra={
                  <Space size={4}>
                    {(['room', 'point', 'floor', 'multi', 'unknown'] as const).map(c => (
                      <Tag key={c} color={CONFIDENCE_COLOR[c]} style={{ margin: 0 }}>
                        {CONFIDENCE_LABEL[c]} {cur.stops.filter(s => s.confidence === c).length}
                      </Tag>
                    ))}
                  </Space>
                }
              >
                <Table
                  size="small"
                  rowKey="seq"
                  pagination={false}
                  dataSource={cur.stops}
                  columns={stopColumns}
                  scroll={{ x: 'max-content' }}
                  rowClassName={s => (activeStop && s.seq === activeStop.seq ? 'ant-table-row-selected' : '')}
                  onRow={s => ({ onClick: () => openStop(s), style: { cursor: 'pointer' } })}
                />
              </Card>
            )}
          </>
        )}
      </Spin>

    </div>
      <JournalRowDrawer
        row={drawerStop?.row ?? null}
        onClose={() => setDrawerStop(null)}
        getContainer={isFs ? popupContainer : undefined}
        extra={drawerStop ? [
          { label: '定位', value: <Tag color={CONFIDENCE_COLOR[drawerStop.confidence]} style={{ margin: 0 }}>{CONFIDENCE_LABEL[drawerStop.confidence]}</Tag> },
          { label: '位置', value: drawerStop.room ?? (drawerStop.floors.map(f => f.toUpperCase()).join('、') || '—') },
          { label: '定位依據', value: <Text style={{ color: '#666' }}>{drawerStop.basis}</Text> },
        ] : undefined}
      />
    </div>
    </ConfigProvider>
  )
}
