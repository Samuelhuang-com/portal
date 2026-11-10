/**
 * 戰情 KPI — 「工務營運中控台」TAB（2026-11-10 新增；規格 docs/SPEC_ops_control_center.md）
 *
 * 給工務室／中控室大螢幕用：只看今天、自動刷新、一個畫面看完人員／點位／報修／告警。
 * 不新增後端，全部讀戰情 KPI 既有 API，口徑與其他 TAB 相同：
 *   ① 狀態列　　　畫面時鐘／資料寫入時間（/ragic/sync-logs/last-updated）／下次更新倒數
 *   ② KPI 列　　　/war-room/floors summary ＋ /war-room/overview（涵蓋率）＋ /war-room/alerts（待通知）
 *   ③ 3D 樓層　　 直接嵌入 FloorIso（與「3D 樓層」TAB 同一元件），每 5 分鐘以 key 重新掛載
 *   ④ 人員即時清單 /war-room/floors 的 people.stops，以現在時間判定 作業中／未取到值／尚未開始
 *   ⑤ 巡檢模組燈號 /war-room/overview modules
 *   ⑥ 事件日誌　　/war-room/alerts（點擊開履歷或 Ragic）
 *   ⑦ 跑馬燈　　　嚴重＋警告告警
 * 刷新：floors／alerts／寫入時間每 2 分鐘；overview 與 3D 每 5 分鐘；背景分頁暫停、回前景立即更新。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Space, Switch, Tooltip } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import {
  fetchWarRoomAlerts, fetchWarRoomFloors, fetchWarRoomOverview,
  type OverviewLevel, type WrAlert, type WrAlerts, type WrFloors, type WrOverview,
} from '@/api/warRoom'
import { fetchLastUpdated, type LastUpdatedResult } from '@/api/ragic'
import { PANEL_MUTED, PANEL_TEXT, PERSON_COLORS, Panel } from '@/pages/ExecWorkDashboard/staffPathShared'
import FloorIso from './FloorIso'
import { AssetHistoryDrawer, type AssetTarget } from './AssetHistory'

/** 與值班總覽相同的巡檢資料來源 */
const FRESH_SOURCES = ['商場工務巡檢', 'B1F巡檢', 'B2F巡檢', 'B4F巡檢', 'RF巡檢']
const FAST_MS = 2 * 60 * 1000        // floors／alerts／寫入時間
const SLOW_MS = 5 * 60 * 1000        // overview／3D 重新掛載
const STALE_MINUTES = 120

const COL = { bad: '#ef5a5a', warn: '#f2a93b', ok: '#3ccf91', idle: '#6b7c99', accent: '#4BA8E8' }
const LEVEL_COL: Record<OverviewLevel, string> = { critical: COL.bad, warning: COL.warn, ok: COL.ok, none: COL.idle }
const LEVEL_TEXT: Record<OverviewLevel, string> = { critical: '嚴重', warning: '警告', ok: '正常', none: '無排定' }
const ALERT_COL: Record<string, string> = { critical: COL.bad, warning: COL.warn, info: COL.accent }
const ALERT_RANK: Record<string, number> = { critical: 0, warning: 1, info: 2 }

const toMin = (s: string) => { const [h, m] = (s || '0:0').split(':').map(Number); return (h || 0) * 60 + (m || 0) }
const hhmm = (m: number) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

type PersonState = 'active' | 'gap' | 'pending'
interface PersonRow {
  person: string
  state:  PersonState
  floor:  string
  room:   string | null
  task:   string
  time:   string
  color:  string
}
const STATE_META: Record<PersonState, { text: string; color: string }> = {
  active:  { text: '作業中', color: COL.ok },
  gap:     { text: '未取到值', color: COL.warn },
  pending: { text: '尚未開始', color: COL.idle },
}

function Kpi({ label, value, sub, color }: { label: string; value: React.ReactNode; sub?: React.ReactNode; color?: string }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: 8, padding: '8px 12px', minWidth: 0 }}>
      <div style={{ fontSize: 12, color: PANEL_MUTED }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: color ?? '#fff', lineHeight: 1.2, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      <div style={{ fontSize: 11, color: PANEL_MUTED, minHeight: 16 }}>{sub}</div>
    </div>
  )
}

export default function ControlCenterTab({ getContainer }: { getContainer?: () => HTMLElement }) {
  const [floors, setFloors] = useState<WrFloors | null>(null)
  const [overview, setOverview] = useState<WrOverview | null>(null)
  const [alerts, setAlerts] = useState<WrAlerts | null>(null)
  const [fresh, setFresh] = useState<LastUpdatedResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [auto, setAuto] = useState(true)
  const [isoKey, setIsoKey] = useState(0)
  const [clock, setClock] = useState(() => dayjs())
  const [nextFast, setNextFast] = useState(() => Date.now() + FAST_MS)
  const [asset, setAsset] = useState<AssetTarget | null>(null)
  const today = clock.format('YYYY-MM-DD')
  const todayRef = useRef(today)
  todayRef.current = today

  // ── 載入（失敗保留上一次資料）──
  const loadFast = useCallback(async () => {
    const d = todayRef.current
    setLoading(true)
    const errs: string[] = []
    await Promise.all([
      fetchWarRoomFloors(d).then(setFloors).catch(e => errs.push(`樓層：${e?.response?.data?.detail ?? e?.message ?? '失敗'}`)),
      fetchWarRoomAlerts(d).then(setAlerts).catch(e => errs.push(`告警：${e?.response?.data?.detail ?? e?.message ?? '失敗'}`)),
      fetchLastUpdated(FRESH_SOURCES).then(setFresh).catch(() => undefined),
    ])
    setError(errs.length ? `${dayjs().format('HH:mm:ss')} 更新失敗（保留上一次資料）— ${errs.join('；')}` : null)
    setNextFast(Date.now() + FAST_MS)
    setLoading(false)
  }, [])
  const loadSlow = useCallback(async () => {
    try { setOverview(await fetchWarRoomOverview(todayRef.current)) } catch { /* 保留上一次 */ }
    setIsoKey(k => k + 1)
  }, [])
  const loadAll = useCallback(() => { loadFast(); loadSlow() }, [loadFast, loadSlow])

  useEffect(() => { loadFast(); fetchWarRoomOverview(todayRef.current).then(setOverview).catch(() => undefined) }, [loadFast])

  // ── 自動刷新（背景分頁暫停，回前景立即更新）──
  useEffect(() => {
    if (!auto) return
    const visible = () => document.visibilityState === 'visible'
    const f = window.setInterval(() => { if (visible()) loadFast() }, FAST_MS)
    const s = window.setInterval(() => { if (visible()) loadSlow() }, SLOW_MS)
    const onVis = () => { if (visible()) loadAll() }
    document.addEventListener('visibilitychange', onVis)
    return () => { window.clearInterval(f); window.clearInterval(s); document.removeEventListener('visibilitychange', onVis) }
  }, [auto, loadFast, loadSlow, loadAll])

  // ── 時鐘（跨日時重新載入今天）──
  useEffect(() => {
    const id = window.setInterval(() => setClock(dayjs()), 1000)
    return () => window.clearInterval(id)
  }, [])
  const lastDay = useRef(today)
  useEffect(() => { if (lastDay.current !== today) { lastDay.current = today; loadAll() } }, [today, loadAll])

  // ── ④ 人員即時清單（每分鐘重算）──
  const minuteNow = clock.hour() * 60 + clock.minute()
  const people: PersonRow[] = useMemo(() => {
    const m = new Map<string, { floor: string; room: string | null; task: string; s: number; e: number }[]>()
    for (const f of floors?.floors ?? []) {
      for (const p of f.people) {
        const list = m.get(p.person) ?? []
        for (const st of p.stops) {
          const s = toMin(st.start_time)
          list.push({ floor: f.label, room: st.room, task: st.task, s, e: Math.max(toMin(st.end_time || st.start_time), s + 6) })
        }
        m.set(p.person, list)
      }
    }
    const names = [...m.keys()].sort((a, b) => a.localeCompare(b))
    const rows = names.map((person, i): PersonRow => {
      const stops = (m.get(person) ?? []).sort((a, b) => a.s - b.s)
      const color = PERSON_COLORS[i % PERSON_COLORS.length]
      const cur = stops.find(x => minuteNow >= x.s && minuteNow <= x.e)
      if (cur) return { person, state: 'active', floor: cur.floor, room: cur.room, task: cur.task, time: `${hhmm(cur.s)}～${hhmm(cur.e)}`, color }
      const past = stops.filter(x => x.s <= minuteNow)
      if (past.length) {
        const last = past.reduce((a, b) => (b.e > a.e ? b : a))
        return { person, state: 'gap', floor: last.floor, room: last.room, task: last.task, time: `最後 ${hhmm(last.e)}`, color }
      }
      const first = stops[0]
      return { person, state: 'pending', floor: first?.floor ?? '—', room: first?.room ?? null, task: first?.task ?? '', time: first ? `${hhmm(first.s)} 起` : '', color }
    })
    const rank: Record<PersonState, number> = { active: 0, gap: 1, pending: 2 }
    return rows.sort((a, b) => rank[a.state] - rank[b.state] || a.person.localeCompare(b.person))
  }, [floors, minuteNow])
  const activeCount = people.filter(p => p.state === 'active').length

  // ── ② 涵蓋率（各模組今日加總，口徑同值班總覽）──
  const coverage = useMemo(() => {
    if (!overview) return null
    let done = 0, judged = 0
    for (const m of overview.modules) { done += m.today.normal + m.today.abnormal; judged += m.today.judged }
    return judged ? Math.round(done * 100 / judged) : null
  }, [overview])

  // ── ⑥⑦ 告警 ──
  const events = useMemo(() => [...(alerts?.alerts ?? [])].sort((a, b) =>
    (ALERT_RANK[a.level] ?? 9) - (ALERT_RANK[b.level] ?? 9) || (b.since || '').localeCompare(a.since || '')), [alerts])
  const ticker = events.filter(a => a.level !== 'info')
  const openAlert = (a: WrAlert) => {
    const r = a.ref ?? {}
    if (r.kind === 'point' && typeof r.point_id === 'number') return setAsset({ type: 'point', id: r.point_id })
    if (r.kind === 'points' && r.point_ids?.length) return setAsset({ type: 'point', id: r.point_ids[0] })
    if (r.kind === 'room' && r.room) return setAsset({ type: 'room', room: String(r.room) })
    if (r.ragic_url) window.open(String(r.ragic_url), '_blank', 'noopener,noreferrer')
    else if (a.room) setAsset({ type: 'room', room: a.room })
  }

  // ── ① 資料寫入時間 ──
  const freshAt = fresh?.last_updated ? dayjs(fresh.last_updated) : null
  const staleMin = freshAt ? clock.diff(freshAt, 'minute') : null
  const isStale = staleMin !== null && staleMin > STALE_MINUTES
  const countdown = Math.max(0, Math.round((nextFast - clock.valueOf()) / 1000))

  const s = floors?.summary
  const dark: React.CSSProperties = { background: '#0b1726', borderRadius: 10, padding: 12, color: PANEL_TEXT }
  const listBox: React.CSSProperties = { maxHeight: 340, overflowY: 'auto', paddingRight: 4 }
  const rowStyle: React.CSSProperties = { display: 'flex', gap: 8, alignItems: 'center', padding: '5px 0', borderBottom: '1px solid rgba(127,155,184,0.15)', fontSize: 13 }

  return (
    <div style={dark}>
      {/* ① 狀態列 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 10 }}>
        <Space size={16} wrap>
          <span style={{ fontSize: 24, fontWeight: 700, color: '#fff', fontFamily: 'ui-monospace, Menlo, monospace' }}>{clock.format('HH:mm:ss')}</span>
          <span style={{ color: PANEL_MUTED }}>{clock.format('YYYY-MM-DD（dd）')}</span>
          <span style={{ color: isStale ? COL.warn : PANEL_MUTED, fontSize: 12 }}>
            巡檢資料寫入：{freshAt ? freshAt.format('MM-DD HH:mm') : '—'}{isStale ? `（已 ${staleMin} 分鐘未更新，可能過期）` : ''}
          </span>
          {floors && <span style={{ color: PANEL_MUTED, fontSize: 12 }}>畫面資料：{floors.generated_at}</span>}
        </Space>
        <Space size={12} wrap>
          {auto && <span style={{ color: PANEL_MUTED, fontSize: 12 }}>下次更新 {Math.floor(countdown / 60)}:{String(countdown % 60).padStart(2, '0')}</span>}
          <Space size={4}><Switch size="small" checked={auto} onChange={setAuto} /><span style={{ fontSize: 12 }}>自動更新</span></Space>
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={loadAll}>立即更新</Button>
        </Space>
      </div>
      {error && <div style={{ background: 'rgba(239,90,90,0.15)', border: `1px solid ${COL.bad}`, borderRadius: 6, padding: '4px 10px', fontSize: 12, marginBottom: 10 }}>{error}</div>}

      {/* ② KPI 列 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 8, marginBottom: 12 }}>
        <Kpi label="出勤人員" value={s?.persons ?? '—'} sub="今日有工作日誌" />
        <Kpi label="作業中" value={floors ? activeCount : '—'} color={COL.ok} sub={`現在 ${hhmm(minuteNow)}`} />
        <Kpi label="巡檢涵蓋率" value={coverage === null ? '—' : `${coverage}%`} color={COL.accent} sub="已判定÷應判定" />
        <Kpi label="異常點位" value={s?.abnormal ?? '—'} color={s?.abnormal ? COL.bad : undefined} />
        <Kpi label="未填點位" value={s?.unchecked ?? '—'} color={s?.unchecked ? COL.warn : undefined} />
        <Kpi label="未完成報修" value={s?.repairs_open ?? '—'} sub={s ? `飯店 ${s.repairs_open_hotel}／商場 ${s.repairs_open_mall}` : ''} />
        <Kpi label="報修 > 7 天" value={s?.repairs_over_7d ?? '—'} color={s?.repairs_over_7d ? COL.bad : undefined} />
        <Kpi label="待通知告警" value={alerts?.summary.due ?? '—'} color={alerts?.summary.due ? COL.warn : undefined}
             sub={alerts ? `嚴重 ${alerts.summary.critical}` : ''} />
      </div>

      {/* ③ 3D 樓層（與「3D 樓層」TAB 同一元件；每 5 分鐘重新掛載＝刷新） */}
      <div style={{ background: '#f0f4f8', borderRadius: 8, padding: 10, marginBottom: 12 }}>
        <FloorIso key={isoKey} getContainer={getContainer} />
      </div>

      {/* ④⑤⑥ */}
      <div className="wr-cc-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
        <Panel title={`人員即時清單（${activeCount}／${people.length}）`} fill={false}>
          <div style={listBox}>
            {!people.length && <div style={{ color: PANEL_MUTED }}>今天尚無工作日誌</div>}
            {people.map(p => (
              <div key={p.person} style={rowStyle}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: p.color, flex: 'none' }} />
                <span style={{ width: 64, flex: 'none', color: '#fff' }}>{p.person}</span>
                <span style={{ width: 64, flex: 'none', color: STATE_META[p.state].color, fontSize: 12 }}>{STATE_META[p.state].text}</span>
                <span style={{ width: 72, flex: 'none' }}>{p.floor}{p.room ? `｜${p.room}` : ''}</span>
                <Tooltip title={p.task} getPopupContainer={getContainer}>
                  <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: PANEL_MUTED }}>{p.task}</span>
                </Tooltip>
                <span style={{ flex: 'none', fontSize: 11, color: PANEL_MUTED }}>{p.time}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="巡檢模組燈號" fill={false}
               extra={overview && <span style={{ fontSize: 11, color: PANEL_MUTED }}>{overview.generated_at}</span>}>
          <div style={listBox}>
            {!overview && <div style={{ color: PANEL_MUTED }}>載入中…</div>}
            {overview?.modules.map(m => (
              <div key={m.module} style={{ ...rowStyle, alignItems: 'flex-start' }}>
                <span style={{ width: 12, height: 12, marginTop: 4, borderRadius: '50%', background: LEVEL_COL[m.level], flex: 'none',
                               boxShadow: m.level === 'critical' ? `0 0 8px ${COL.bad}` : undefined }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ color: '#fff' }}>{m.label}<span style={{ marginLeft: 6, fontSize: 11, color: LEVEL_COL[m.level] }}>{LEVEL_TEXT[m.level]}</span></div>
                  <div style={{ fontSize: 12, color: PANEL_MUTED }}>{m.headline}</div>
                </div>
                <div style={{ textAlign: 'right', flex: 'none', fontSize: 12 }}>
                  <div style={{ color: '#fff', fontSize: 15 }}>{m.today.coverage === null ? '—' : `${m.today.coverage}%`}</div>
                  <div style={{ color: PANEL_MUTED }}>異常 {m.today.abnormal}／未填 {m.today.unchecked}</div>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title={`事件日誌（${events.length}）`} fill={false}>
          <div style={listBox}>
            {alerts && !events.length && <div style={{ color: PANEL_MUTED }}>目前無告警</div>}
            {events.map(a => (
              <div key={a.key} style={{ ...rowStyle, cursor: 'pointer' }} onClick={() => openAlert(a)}>
                <span style={{ flex: 'none', fontSize: 11, padding: '0 6px', borderRadius: 4, border: `1px solid ${ALERT_COL[a.level]}`, color: ALERT_COL[a.level] }}>{a.level_label}</span>
                <span style={{ flex: 'none', fontSize: 11, color: PANEL_MUTED, width: 40 }}>{a.type}</span>
                <Tooltip title={a.detail} getPopupContainer={getContainer}>
                  <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.title}</span>
                </Tooltip>
                <span style={{ flex: 'none', fontSize: 11, color: PANEL_MUTED }}>{(a.since || '').slice(5, 10)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* ⑦ 跑馬燈 */}
      <div style={{ marginTop: 12, overflow: 'hidden', whiteSpace: 'nowrap', borderRadius: 6, background: 'rgba(255,255,255,0.05)', padding: '6px 0' }}>
        {ticker.length ? (
          <div className="wr-cc-marquee" style={{ display: 'inline-block', paddingLeft: '100%', animationDuration: `${Math.max(30, ticker.length * 8)}s` }}>
            {ticker.map(a => (
              <span key={a.key} style={{ marginRight: 48, color: ALERT_COL[a.level] }}>● {a.title}</span>
            ))}
          </div>
        ) : <span style={{ paddingLeft: 12, color: PANEL_MUTED }}>{alerts ? '目前無嚴重／警告告警' : '載入中…'}</span>}
      </div>

      <style>{`
        @media (max-width: 1200px) { .wr-cc-grid { grid-template-columns: minmax(0, 1fr) !important; } }
        @keyframes wrCcMarquee { from { transform: translateX(0); } to { transform: translateX(-100%); } }
        .wr-cc-marquee { animation-name: wrCcMarquee; animation-timing-function: linear; animation-iteration-count: infinite; }
        @media (prefers-reduced-motion: reduce) { .wr-cc-marquee { animation: none; padding-left: 12px !important; } }
      `}</style>

      <AssetHistoryDrawer target={asset} date={today} onClose={() => setAsset(null)} getContainer={getContainer} />
    </div>
  )
}
