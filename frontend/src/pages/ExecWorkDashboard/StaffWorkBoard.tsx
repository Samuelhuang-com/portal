/**
 * 人員動態 — 「工作視角」（2026-10-06 新增）
 *
 * 辦公室隱喻：每位人員一張桌子，依飯店／商場分區。和「大樓視角」共用同一個時鐘（今天預設 LIVE）。
 *  - 工作中：依工作內容畫不同樣式（staffPoses.tsx P02～P15，後端 _pose_of 判斷）；P01＝坐在桌前打字
 *    紅點「進行中」＝已打卡開始、還沒填結束
 *  - 站在桌旁＝兩筆紀錄之間，未取到值（工作日誌沒有這段時間的紀錄，不代表沒在工作）
 *  - 空位＝今天還沒有第一筆；螢幕關＝之後沒有再紀錄
 *  - 下方「員工現況」卡片：現在／上一筆／下一筆、當日時間條
 *
 * ⚠️ 狀態全部來自工作日誌（工單子表的打卡時間），不是定位或刷卡。
 */
import React, { useMemo, useState } from 'react'
import { Button, Tag, Tooltip, Typography } from 'antd'
import { AimOutlined, InfoCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'

import type { PathStop, StaffPathDay } from '@/api/staffPath'
import { PANEL_TEXT, PANEL_MUTED, GRID, fmtMin, Panel, floorsText } from './staffPathShared'
import { ClockBar, stopEndMin, type DayClock } from './staffClock'
import { PoseArt, POSE_CSS, POSE_LABEL, isFieldPose, Desk, WMODE, type WMode } from './staffPoses'
import StaffWorkHelp from './StaffWorkHelp'

const { Text } = Typography

const TEAM_LABEL: Record<string, string> = { hotel: '飯店工務', mall: '商場工務', other: '其他' }

interface Seg { a: number; b: number; stop: PathStop }
interface WState { mode: WMode; cur?: Seg; last?: Seg; next?: Seg; workMin: number }

const locText = (s: PathStop) => s.room ?? (s.points?.length ? s.points[0].label : floorsText(s.floors))

function stateAt(segs: Seg[], t: number): WState {
  let cur: Seg | undefined
  for (const g of segs) if (g.a <= t && t < g.b) cur = g
  const done = segs.filter(g => g.b <= t)
  const last = done[done.length - 1]
  const next = segs.find(g => g.a > t)
  const workMin = Math.round(segs.reduce((acc, g) => acc + Math.max(0, Math.min(t, g.b) - g.a), 0))
  if (cur) return { mode: 'work', cur, last, next, workMin }
  if (!last) return { mode: 'off', next, workMin }
  if (next) return { mode: 'gap', last, next, workMin }
  return { mode: 'after', last, workMin }
}

// ══════════════════════════════════════════════════════════════════════════════
export default function StaffWorkBoard({
  data, colorOf, clock, loadedAt, onOpenStop, onFocusPerson,
}: {
  data: StaffPathDay
  colorOf: (p: string) => string
  clock: DayClock
  loadedAt?: Dayjs | null
  onOpenStop: (s: PathStop) => void
  onFocusPerson: (p: string) => void
}) {
  const { t, T0, T1, isToday, now } = clock
  const [helpOpen, setHelpOpen] = useState(false)

  const people = useMemo(() => data.persons.map(p => {
    const segs: Seg[] = p.stops.filter(s => s.start_min != null)
      .map(s => ({ a: s.start_min as number, b: stopEndMin(s, isToday, now), stop: s }))
      .sort((x, y) => x.a - y.a)
    const hotel = p.stops.filter(s => s.venue === 'hotel').length
    const mall = p.stops.filter(s => s.venue === 'mall').length
    const team = hotel === 0 && mall === 0 ? 'other' : hotel >= mall ? 'hotel' : 'mall'
    return { person: p.person, segs, team, untimed: p.stops.length - segs.length }
  }), [data, isToday, now])

  const states = people.map(p => ({ ...p, st: stateAt(p.segs, t) }))
  const count = (m: WMode) => states.filter(s => s.st.mode === m).length
  const openNow = states.filter(s => s.st.mode === 'work' && s.st.cur?.stop.open).length
  const doneCount = people.reduce((a, p) => a + p.segs.filter(g => g.b <= t && !(g.stop.open && isToday)).length, 0)
  const teams = (['hotel', 'mall', 'other'] as const).filter(k => states.some(s => s.team === k))

  const legend = (
    <>
      <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'baseline' }}>
        {(['work', 'gap', 'off', 'after'] as WMode[]).map(m => (
          <span key={m} style={{ color: PANEL_TEXT, fontSize: 13 }}>
            <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: 5, background: WMODE[m].color, marginRight: 5 }} />
            {WMODE[m].label} <b style={{ color: '#fff', fontSize: 16 }}>{count(m)}</b>
          </span>
        ))}
        {isToday && (
          <span style={{ color: PANEL_TEXT, fontSize: 13 }}>
            <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: 5, background: '#ff4d4f', marginRight: 5 }} />
            進行中 <b style={{ color: '#fff', fontSize: 16 }}>{openNow}</b>
          </span>
        )}
        <span style={{ color: PANEL_TEXT, fontSize: 13 }}>已完成 <b style={{ color: '#fff', fontSize: 16 }}>{doneCount}</b> 筆</span>
      </div>
      <Tooltip title="狀態來自工作日誌（工單子表的打卡開始／結束時間），不是定位或刷卡。站在桌旁＝兩筆紀錄之間沒有資料（未取到值），不代表沒在工作。">
        <Text style={{ color: PANEL_MUTED, fontSize: 12, marginLeft: 'auto' }}><InfoCircleOutlined /> 狀態說明</Text>
      </Tooltip>
    </>
  )

  const focusStop = (s: WState) => (s.cur ?? s.last ?? s.next)?.stop

  return (
    <div>
      <style>{`
        .swb-desk .swb-person, .swb-desk .swb-glow { transition: opacity .4s, transform .6s }
        .swb-desk .swb-ring, .swb-desk .swb-q, .swb-desk .swb-glow, .swb-desk .swb-code { opacity: 0 }
        .swb-desk .swb-screen { fill: #0d1e30 }
        .swb-work .swb-screen { fill: #18402e }
        .swb-work .swb-glow { opacity: .45; filter: blur(6px) }
        .swb-work .swb-code { opacity: 1; animation: swbCode 1.2s steps(3) infinite }
        .swb-work .swb-arm { animation: swbType .32s ease-in-out infinite alternate; transform-box: fill-box }
        .swb-work .swb-arm-r { animation-delay: .16s }
        .swb-work .swb-ring { animation: swbPulse 1.6s ease-out infinite; transform-origin: center; transform-box: fill-box }
        .swb-work .swb-open { animation: swbBlink 1s ease-in-out infinite }
        .swb-gap .swb-person { transform: translate(40px, 4px) }
        .swb-gap .swb-arm { transform: translateY(-14px) }
        .swb-gap .swb-q { opacity: 1 }
        .swb-gap .swb-head { animation: swbBob 2.4s ease-in-out infinite }
        .swb-off .swb-person, .swb-after .swb-person { opacity: 0 }
        @keyframes swbType { to { transform: translateY(-3px) } }
        @keyframes swbBob { 50% { transform: translateY(-2px) } }
        @keyframes swbPulse { from { opacity: .8; transform: scale(.6) } to { opacity: 0; transform: scale(1.6) } }
        @keyframes swbBlink { 50% { opacity: .2 } }
        @keyframes swbCode { 0% { opacity: .5 } 100% { opacity: 1 } }
        .swb-seat { cursor: pointer; border-radius: 10px; transition: background .2s }
        .swb-seat:hover { background: rgba(75,168,232,0.12) }
        .swb-seat:focus-visible { outline: 2px solid #4BA8E8 }
        .swb-card { transition: background .2s }
        .swb-card:hover { background: rgba(75,168,232,0.14) !important }
        @media (prefers-reduced-motion: reduce) { .swb-desk * { animation: none !important; transition: none !important } }
      ` + POSE_CSS}</style>

      <ClockBar clock={clock} data={data} loadedAt={loadedAt} legend={legend} />

      {/* ── 辦公室 ── */}
      <div style={{ marginTop: 12 }}>
        <Panel fill={false} title="工作視角" extra={
          <span style={{ display: 'inline-flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <Text style={{ color: PANEL_MUTED, fontSize: 12 }}>工作中依工作內容換樣式｜站在桌旁＝未取到值｜空位＝未開始｜點人物看明細</Text>
            <Button size="small" ghost icon={<QuestionCircleOutlined />} onClick={() => setHelpOpen(true)}>畫面說明</Button>
          </span>
        }>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, 330px), 1fr))`, gap: 12 }}>
            {teams.map(k => (
              <div key={k} style={{ background: 'rgba(255,255,255,0.04)', border: `1px solid ${GRID}`, borderRadius: 10, padding: '8px 10px 10px', minWidth: 0 }}>
                <div style={{ color: PANEL_MUTED, fontSize: 13, letterSpacing: 1, marginBottom: 4 }}>
                  {TEAM_LABEL[k]}　<span style={{ color: PANEL_TEXT }}>{states.filter(s => s.team === k && s.st.mode === 'work').length}</span>
                  ／{states.filter(s => s.team === k).length} 人工作中
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'space-around' }}>
                  {states.filter(s => s.team === k).map(s => {
                    const c = colorOf(s.person)
                    const st = s.st
                    const fs = focusStop(st)
                    const open = !!st.cur?.stop.open && isToday
                    let line: React.ReactNode
                    if (st.mode === 'work' && st.cur) {
                      line = <><b style={{ color: '#5BE49B' }}>{locText(st.cur.stop)}</b>　{st.cur.stop.row.task}</>
                    } else if (st.mode === 'gap' && st.last && st.next) {
                      line = <>未取到值｜上一筆 {fmtMin(Math.round(st.last.b))} 結束，下一筆 {fmtMin(Math.round(st.next.a))}</>
                    } else if (st.mode === 'off') {
                      line = st.next ? <>今天第一筆 {fmtMin(Math.round(st.next.a))}</> : <>今天沒有有時間的紀錄</>
                    } else if (st.last) {
                      line = <>最後一筆 {fmtMin(Math.round(st.last.b))} 結束</>
                    }
                    return (
                      <div key={s.person} className="swb-seat" role="button" tabIndex={0}
                           style={{ width: 160, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '4px 4px 6px' }}
                           onClick={() => fs && onOpenStop(fs)}
                           onKeyDown={e => { if ((e.key === 'Enter' || e.key === ' ') && fs) onOpenStop(fs) }}>
                        {st.mode === 'work' && isFieldPose(st.cur?.stop.pose)
                          ? <PoseArt pose={st.cur!.stop.pose as string} color={c} open={open} />
                          : <Desk color={c} mode={st.mode} open={open} />}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <b style={{ color: c, fontSize: 14 }}>{s.person}</b>
                          {open && <Tag color="red" style={{ margin: 0, fontSize: 11, lineHeight: '16px', padding: '0 5px' }}>進行中</Tag>}
                        </div>
                        <Tooltip title={st.cur ? `${POSE_LABEL[st.cur.stop.pose ?? 'P01'] ?? ''}｜${st.cur.stop.row.task}` : undefined}>
                          <div style={{ fontSize: 11, color: st.mode === 'work' ? PANEL_TEXT : PANEL_MUTED, textAlign: 'center', lineHeight: 1.4,
                                        minHeight: 31, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                            {line}
                          </div>
                        </Tooltip>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* ── 員工現況 ── */}
      <div style={{ marginTop: 12 }}>
        <Panel fill={false} title={`員工現況　${fmtMin(Math.floor(t))}`}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 280px), 1fr))', gap: 8 }}>
            {[...states].sort((a, b) => WMODE[a.st.mode].order - WMODE[b.st.mode].order || a.person.localeCompare(b.person)).map(s => {
              const c = colorOf(s.person)
              const st = s.st
              const seg = st.cur ?? st.last ?? st.next
              const head = st.cur ? '現在' : st.last ? '上一筆' : '下一筆'
              const total = Math.round(s.segs.reduce((a, g) => a + (g.b - g.a), 0))
              return (
                <div key={s.person} className="swb-card"
                     style={{ background: 'rgba(255,255,255,0.04)', borderLeft: `3px solid ${c}`, borderRadius: 8, padding: '8px 10px',
                              display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <b style={{ color: '#fff' }}>{s.person}</b>
                    <Tag color={WMODE[st.mode].color} style={{ margin: 0, color: '#0d1e30', fontWeight: 600 }}>{WMODE[st.mode].label}</Tag>
                    {st.cur?.stop.open && isToday && <Tag color="red" style={{ margin: 0 }}>進行中</Tag>}
                    <span style={{ marginLeft: 'auto', fontSize: 12, color: PANEL_MUTED, fontFamily: 'ui-monospace, Menlo, Consolas, monospace' }}>
                      {st.workMin}／{total} 分
                    </span>
                    <Tooltip title="看他的個人動線">
                      <Button size="small" type="text" icon={<AimOutlined style={{ color: PANEL_MUTED }} />} onClick={() => onFocusPerson(s.person)} />
                    </Tooltip>
                  </div>
                  {seg ? (
                    <div style={{ fontSize: 13, color: PANEL_TEXT, cursor: 'pointer', overflowWrap: 'anywhere' }} onClick={() => onOpenStop(seg.stop)}>
                      <span style={{ color: PANEL_MUTED }}>{head}：</span>
                      <span style={{ color: '#4BA8E8' }}>{locText(seg.stop)}</span>　{seg.stop.row.task}
                    </div>
                  ) : <div style={{ fontSize: 13, color: PANEL_MUTED }}>沒有有時間的紀錄</div>}
                  {seg && (
                    <div style={{ fontSize: 12, color: PANEL_MUTED }}>
                      {seg.stop.row.source_label}｜{fmtMin(Math.round(seg.a))}–{seg.stop.open && isToday ? '進行中' : fmtMin(Math.round(seg.b))}
                      {seg.stop.open && !isToday ? '（未填結束）' : ''}
                    </div>
                  )}
                  {/* 當日時間條 */}
                  <div style={{ position: 'relative', height: 8, background: 'rgba(0,0,0,0.25)', borderRadius: 3, marginTop: 2 }}>
                    {s.segs.map((g, i) => (
                      <span key={i} style={{ position: 'absolute', top: 0, bottom: 0, borderRadius: 2, opacity: 0.8,
                                             left: `${((g.a - T0) / (T1 - T0)) * 100}%`, width: `${Math.max(0.8, ((g.b - g.a) / (T1 - T0)) * 100)}%`,
                                             background: g.stop.open && isToday ? '#ff4d4f' : c }} />
                    ))}
                    <span style={{ position: 'absolute', top: -3, bottom: -3, width: 2, background: '#fff', left: `${((t - T0) / (T1 - T0)) * 100}%` }} />
                  </div>
                  {s.untimed > 0 && <div style={{ fontSize: 11, color: PANEL_MUTED }}>另有 {s.untimed} 筆沒有時間，無法排上時間軸</div>}
                </div>
              )
            })}
          </div>
          {!states.length && <Text style={{ color: PANEL_MUTED }}>沒有人員資料</Text>}
        </Panel>
      </div>
      <StaffWorkHelp open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  )
}
