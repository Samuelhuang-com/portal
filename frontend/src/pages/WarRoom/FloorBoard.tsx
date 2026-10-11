/**
 * 戰情 KPI — Dashboard（整棟戰情圖）
 *
 * 左：大樓剖面（RF～B4F），每層顯示 有人工作／巡檢異常・未填／未完成報修，依狀態上色
 * 右：選中樓層的明細（未選＝全棟待處理）：人員工作、巡檢點位、未完成報修、今日到訪房間
 * 點房間／設備 → 履歷（AssetHistoryDrawer）；點報修 → RepairDrawer；點工作 → 工作日誌明細 Drawer
 *
 * 口徑見 backend/app/routers/war_room.py 檔頭（未完成報修＝今日現況）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Empty, Row, Segmented, Space, Spin, Statistic, Switch, Tag, Tooltip, Typography,
} from 'antd'
import { LeftOutlined, ReloadOutlined, RightOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import { fetchWarRoomFloors, type WrFloors, type WrFloor, type WrRepair, type WrPoint, type WrPersonStop } from '@/api/warRoom'
import type { JournalRow } from '@/api/workJournal'
import { FLOOR_MAP_STATUS } from '@/components/FloorPlanMap/status'
import JournalRowDrawer from '@/components/WorkJournal/JournalRowDrawer'
import { PANEL_MUTED, PERSON_COLORS, Panel } from '@/pages/ExecWorkDashboard/staffPathShared'
import { AssetHistoryDrawer, RepairDrawer, type AssetTarget } from './AssetHistory'

const { Text } = Typography

type Filter = 'all' | 'abnormal' | 'repairs' | 'people'

const LEVEL = {
  abnormal: { color: '#FF4D4F', label: '巡檢異常' },
  warn:     { color: '#FAAD14', label: '待處理（未完成報修／未填）' },
  busy:     { color: '#52C41A', label: '有人工作' },
  idle:     { color: 'rgba(127,155,184,0.35)', label: '無事件' },
} as const

function floorLevel(f: WrFloor): keyof typeof LEVEL {
  if (f.point_status.abnormal > 0) return 'abnormal'
  if (f.repairs_count > 0 || f.point_status.unchecked > 0) return 'warn'
  if (f.people_count > 0) return 'busy'
  return 'idle'
}

const shortName = (n: string) => (n.length <= 2 ? n : n.slice(-2))

export default function FloorBoard({ getContainer }: { getContainer?: () => HTMLElement }) {
  const [date, setDate] = useState<Dayjs>(dayjs())
  const [data, setData] = useState<WrFloors | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<Filter>('all')
  const [sel, setSel] = useState<string | null>(null)
  const [auto, setAuto] = useState(true)
  const [asset, setAsset] = useState<AssetTarget | null>(null)
  const [repair, setRepair] = useState<WrRepair | null>(null)
  const [row, setRow] = useState<JournalRow | null>(null)

  const isToday = date.isSame(dayjs(), 'day')

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      setData(await fetchWarRoomFloors(date.format('YYYY-MM-DD')))
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [date])
  useEffect(() => { load() }, [load])

  // 今天：每 5 分鐘自動更新（資料本身跟著 Ragic 同步頻率，無法更即時）
  useEffect(() => {
    if (!isToday || !auto) return
    const t = window.setInterval(load, 5 * 60 * 1000)
    return () => window.clearInterval(t)
  }, [isToday, auto, load])

  const colorOf = useMemo(() => {
    const names = Array.from(new Set((data?.floors ?? []).flatMap(f => f.people.map(p => p.person)))).sort()
    const m = new Map(names.map((n, i) => [n, PERSON_COLORS[i % PERSON_COLORS.length]]))
    return (n: string) => m.get(n) ?? '#4BA8E8'
  }, [data])

  const floors = data?.floors ?? []
  const match = (f: WrFloor) =>
    filter === 'all' ? true
      : filter === 'abnormal' ? f.point_status.abnormal + f.point_status.unchecked > 0
        : filter === 'repairs' ? f.repairs_count > 0
          : f.people_count > 0
  const selFloor = floors.find(f => f.key === sel) ?? null
  const s = data?.summary

  // 今日到訪某房間（給房間履歷）
  const visitsOf = (room: string) =>
    floors.flatMap(f => f.people.flatMap(p => p.stops.filter(st => st.room === room).map(st => ({ person: p.person, stop: st }))))
      .filter((v, i, arr) => arr.findIndex(x => x.person === v.person && x.stop.seq === v.stop.seq) === i)

  const openPoint = (p: WrPoint) => setAsset({ type: 'point', id: p.id, label: p.label })
  const openRoom = (room: string) => setAsset({ type: 'room', room })

  // ── 右側明細 ──
  const detailFloors = selFloor ? [selFloor] : floors
  const people = selFloor ? selFloor.people : []
  const pts = detailFloors.flatMap(f => f.points)
  const attention = pts.filter(p => p.status === 'abnormal' || p.status === 'unchecked')
    .sort((a, b) => (a.status === 'abnormal' ? 0 : 1) - (b.status === 'abnormal' ? 0 : 1))
  const okCount = pts.length - attention.length
  const repairs = detailFloors.flatMap(f => f.repairs).sort((a, b) => (b.wait_days ?? 0) - (a.wait_days ?? 0))
  const roomsVisited = selFloor ? selFloor.rooms_visited : []

  return (
    <div>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap size={[12, 8]} style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space wrap>
            <Button size="small" icon={<LeftOutlined />} onClick={() => setDate(d => d.subtract(1, 'day'))} />
            <DatePicker size="small" value={date} allowClear={false} onChange={v => v && setDate(v)} getPopupContainer={getContainer} />
            <Button size="small" icon={<RightOutlined />} onClick={() => setDate(d => d.add(1, 'day'))} />
            <Button size="small" onClick={() => setDate(dayjs())}>今天</Button>
            <Segmented size="small" value={filter} onChange={v => setFilter(v as Filter)} options={[
              { label: '全部樓層', value: 'all' },
              { label: '只看巡檢異常／未填', value: 'abnormal' },
              { label: '只看未完成報修', value: 'repairs' },
              { label: '只看有人工作', value: 'people' },
            ]} />
          </Space>
          <Space>
            {isToday && (
              <Space size={4}>
                <Switch size="small" checked={auto} onChange={setAuto} />
                <Text style={{ fontSize: 12 }}>每 5 分鐘自動更新</Text>
              </Space>
            )}
            {data && <Text type="secondary" style={{ fontSize: 12 }}>更新於 {data.generated_at}</Text>}
            <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
          </Space>
        </Space>
      </Card>

      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}

      <Spin spinning={loading && !data}>
        {/* KPI（4 欄、size small） */}
        <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #1B3A5C', cursor: 'pointer' }} onClick={() => setFilter('people')}>
              <Statistic title="今日出勤人員（具名）" value={s?.persons ?? 0} suffix="人" valueStyle={{ color: '#1B3A5C', fontWeight: 700 }} />
              <Text type="secondary" style={{ fontSize: 12 }}>{s?.stops ?? 0} 件工作／{Math.round((s?.work_min ?? 0) / 60 * 10) / 10} 小時</Text>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #FF4D4F', cursor: 'pointer' }} onClick={() => setFilter('abnormal')}>
              <Statistic title="巡檢異常點位" value={s?.abnormal ?? 0} suffix="點" valueStyle={{ color: '#cf1322', fontWeight: 700 }} />
              <Text type="secondary" style={{ fontSize: 12 }}>未填 {s?.unchecked ?? 0}・無紀錄 {s?.no_record ?? 0}／共 {s?.points ?? 0} 點</Text>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #FAAD14', cursor: 'pointer' }} onClick={() => setFilter('repairs')}>
              <Statistic title="未完成報修（今日現況）" value={s?.repairs_open ?? 0} suffix="件" valueStyle={{ color: '#d46b08', fontWeight: 700 }} />
              <Text type="secondary" style={{ fontSize: 12 }}>飯店 {s?.repairs_open_hotel ?? 0}・商場 {s?.repairs_open_mall ?? 0}・超過 7 天 {s?.repairs_over_7d ?? 0}</Text>
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card size="small" bordered={false} style={{ borderTop: '3px solid #52c41a' }}>
              <Statistic title="巡檢涵蓋率" valueStyle={{ color: '#389e0d', fontWeight: 700 }} suffix="%"
                         value={s && s.points ? Math.round(100 * (s.points - s.no_record) / s.points) : 0} />
              <Text type="secondary" style={{ fontSize: 12 }}>有巡檢紀錄 {s ? s.points - s.no_record : 0}／{s?.points ?? 0} 點</Text>
            </Card>
          </Col>
        </Row>

        {data && (
          <Row gutter={[12, 12]}>
            {/* 大樓剖面 */}
            <Col xs={24} xl={13}>
              <Panel
                title="整棟戰情圖"
                extra={
                  <Space size={10} wrap style={{ fontSize: 12, color: PANEL_MUTED }}>
                    {Object.values(LEVEL).map(l => (
                      <span key={l.label}><span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: l.color, marginRight: 4 }} />{l.label}</span>
                    ))}
                  </Space>
                }
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {floors.map(f => {
                    const lv = LEVEL[floorLevel(f)]
                    const on = match(f)
                    const active = sel === f.key
                    return (
                      <div key={f.key} onClick={() => setSel(active ? null : f.key)}
                           style={{
                             display: 'flex', alignItems: 'center', gap: 10, padding: '6px 10px', borderRadius: 6, cursor: 'pointer',
                             background: active ? 'rgba(75,168,232,0.22)' : f.kind === 'guest' ? 'rgba(75,168,232,0.07)' : 'rgba(255,255,255,0.04)',
                             borderLeft: `5px solid ${lv.color}`, opacity: on ? 1 : 0.28,
                             outline: active ? '1px solid #4BA8E8' : undefined, transition: 'opacity .2s, background .2s',
                           }}>
                        <div style={{ width: 54, color: '#fff', fontWeight: 700 }}>
                          {f.label}
                          {f.kind === 'guest' && <div style={{ fontSize: 10, color: '#4BA8E8', fontWeight: 400 }}>客房</div>}
                        </div>
                        <Space size={6} wrap style={{ flex: 1 }}>
                          {f.people_count > 0 && <Tag color="green" style={{ margin: 0 }}>{f.people_count} 人・{f.stops} 件</Tag>}
                          {f.point_status.abnormal > 0 && <Tag color="red" style={{ margin: 0 }}>異常 {f.point_status.abnormal}</Tag>}
                          {f.point_status.unchecked > 0 && <Tag color="gold" style={{ margin: 0 }}>未填 {f.point_status.unchecked}</Tag>}
                          {f.repairs_count > 0 && <Tag color="orange" style={{ margin: 0 }}>報修 {f.repairs_count}</Tag>}
                          {f.points.length > 0 && f.point_status.abnormal + f.point_status.unchecked === 0 && (
                            <Text style={{ color: PANEL_MUTED, fontSize: 12 }}>巡檢 {f.point_status.normal}/{f.points.length} 正常</Text>
                          )}
                        </Space>
                        <div style={{ display: 'flex', gap: 2 }}>
                          {f.people.slice(0, 6).map(p => (
                            <Tooltip key={p.person} title={`${p.person}：${p.stops.length} 件`}>
                              <span style={{ width: 22, height: 22, borderRadius: 11, background: colorOf(p.person), color: '#0d1e30',
                                             fontSize: 9, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                                {shortName(p.person)}
                              </span>
                            </Tooltip>
                          ))}
                          {f.people.length > 6 && <Text style={{ color: PANEL_MUTED, fontSize: 11 }}>+{f.people.length - 6}</Text>}
                        </div>
                      </div>
                    )
                  })}
                </div>
                <div style={{ fontSize: 12, color: PANEL_MUTED, marginTop: 8 }}>
                  點樓層看明細，再點一次取消。未完成報修為「今日現況」，人員工作與巡檢為所選日期。
                </div>
              </Panel>
            </Col>

            {/* 明細 */}
            <Col xs={24} xl={11}>
              <Card
                size="small"
                title={selFloor ? `${selFloor.label}${selFloor.kind === 'guest' ? ' 客房' : ''} 明細` : '全棟待處理'}
                extra={selFloor && <Button size="small" onClick={() => setSel(null)}>看全棟</Button>}
                styles={{ body: { maxHeight: 720, overflowY: 'auto' } }}
              >
                {selFloor && (
                  <Section title={`有人工作（${people.length} 人）`}>
                    {people.length === 0 ? <Text type="secondary">這層今天沒有工作紀錄</Text> : people.map(p => (
                      <div key={p.person} style={{ marginBottom: 8 }}>
                        <Space size={6}>
                          <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 5, background: colorOf(p.person) }} />
                          <Text strong>{p.person}</Text><Text type="secondary">{p.stops.length} 件</Text>
                        </Space>
                        {p.stops.map(st => <StopLine key={st.seq} st={st} onOpen={() => setRow(st.row)} onRoom={openRoom} />)}
                      </div>
                    ))}
                  </Section>
                )}

                {selFloor && roomsVisited.length > 0 && (
                  <Section title={`今日到訪房間（${roomsVisited.length}）`}>
                    <Space size={[4, 4]} wrap>
                      {roomsVisited.map(r => <Tag key={r} color="green" style={{ cursor: 'pointer' }} onClick={() => openRoom(r)}>{r}</Tag>)}
                    </Space>
                  </Section>
                )}

                <Section title={`巡檢點位：需注意 ${attention.length}${okCount ? `（其餘 ${okCount} 點正常或無紀錄）` : ''}`}>
                  {attention.length === 0 ? <Text type="secondary">沒有異常或未填的點位</Text> : attention.slice(0, 60).map(p => (
                    <div key={p.id} onClick={() => openPoint(p)}
                         style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '3px 6px', cursor: 'pointer', borderRadius: 4 }}
                         className="wr-hover">
                      <span style={{ width: 10, height: 10, borderRadius: 5, background: FLOOR_MAP_STATUS[p.status].color, flex: 'none' }} />
                      {!selFloor && <Tag style={{ margin: 0 }}>{p.floor_key.toUpperCase()}</Tag>}
                      <Text>{p.label}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>{p.group_label}{p.shared_label ? `・${p.shared_label}` : ''}</Text>
                      <span style={{ marginLeft: 'auto' }}>
                        <Tag color={FLOOR_MAP_STATUS[p.status].color} style={{ margin: 0 }}>{FLOOR_MAP_STATUS[p.status].label}</Tag>
                      </span>
                    </div>
                  ))}
                </Section>

                <Section title={`未完成報修 ${repairs.length} 件（等待最久在前）`}>
                  {repairs.length === 0 ? <Text type="secondary">沒有未完成報修</Text> : repairs.slice(0, selFloor ? 100 : 15).map(r => (
                    <div key={`${r.source}-${r.ragic_id}`} onClick={() => setRepair(r)}
                         style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '3px 6px', cursor: 'pointer', borderRadius: 4 }}
                         className="wr-hover">
                      <Text type={(r.wait_days ?? 0) > 7 ? 'danger' : undefined} style={{ minWidth: 44, textAlign: 'right' }}>{r.wait_days ?? '—'} 天</Text>
                      {r.room ? <Tag color="green" style={{ margin: 0 }}>{r.room}</Tag>
                        : <Tag style={{ margin: 0 }}>{r.floors[0]?.toUpperCase() ?? '未定位'}</Tag>}
                      <Text ellipsis style={{ flex: 1 }}>{r.title}</Text>
                      <Tag color={r.source === 'dazhi' ? '#1565C0' : '#2E7D32'} style={{ margin: 0 }}>{r.source === 'dazhi' ? '飯' : '商'}</Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>{r.status || '—'}</Text>
                    </div>
                  ))}
                  {!selFloor && repairs.length > 15 && <Text type="secondary" style={{ fontSize: 12 }}>只列前 15 件，點樓層看該層全部</Text>}
                </Section>
              </Card>
            </Col>
          </Row>
        )}
        {!loading && data && floors.every(f => !f.people_count && !f.repairs_count && !f.points.length) && (
          <Empty description="這一天沒有任何資料" style={{ marginTop: 24 }} />
        )}
      </Spin>

      <style>{`.wr-hover:hover { background: #f0f7ff; }`}</style>

      <AssetHistoryDrawer
        target={asset}
        date={date.format('YYYY-MM-DD')}
        visits={asset?.type === 'room' ? visitsOf(asset.room) : undefined}
        onClose={() => setAsset(null)}
        onOpenVisit={st => setRow(st.row)}
        onOpenRepair={r => setRepair(r)}
        getContainer={getContainer}
      />
      <RepairDrawer repair={repair} onClose={() => setRepair(null)} onOpenRoom={room => { setRepair(null); openRoom(room) }} getContainer={getContainer} />
      <JournalRowDrawer row={row} onClose={() => setRow(null)} getContainer={getContainer} />
    </div>
  )
}

function Section({ title, children }: { title: React.ReactNode; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600, color: '#1B3A5C', marginBottom: 6, borderBottom: '1px solid #f0f0f0', paddingBottom: 4 }}>{title}</div>
      {children}
    </div>
  )
}

function StopLine({ st, onOpen, onRoom }: { st: WrPersonStop; onOpen: () => void; onRoom: (r: string) => void }) {
  return (
    <div onClick={onOpen} className="wr-hover"
         style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '2px 6px 2px 18px', cursor: 'pointer', borderRadius: 4, fontSize: 13 }}>
      <Text type="secondary" style={{ minWidth: 86 }}>{st.start_time || '—'}–{st.end_time || '—'}</Text>
      {st.room && <Tag color="green" style={{ margin: 0 }} onClick={e => { e.stopPropagation(); onRoom(st.room as string) }}>{st.room}</Tag>}
      <Text ellipsis style={{ flex: 1 }}>{st.task}</Text>
      <Text type="secondary" style={{ fontSize: 11 }}>{st.source_label}</Text>
    </div>
  )
}

