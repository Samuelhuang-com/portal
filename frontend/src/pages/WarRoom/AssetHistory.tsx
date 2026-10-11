/**
 * 戰情 KPI — 房間／設備履歷（點擊即檢視）
 *
 *  - AssetHistoryPanel：房間（報修＋IHG 客房保養＋今日到訪）或設備（當日檢查結果＋當月每日狀況）
 *  - AssetHistoryDrawer：把 Panel 包成 Drawer，給戰情圖、樓層明細點擊用
 *  - RepairDrawer：單筆未完成報修明細（標題列格式依 CLAUDE.md §7）
 */
import React, { useEffect, useState } from 'react'
import { Descriptions, Drawer, Empty, Space, Spin, Table, Tag, Tooltip, Typography, Alert } from 'antd'
import { LinkOutlined } from '@ant-design/icons'

import {
  fetchWarRoomPoint, fetchWarRoomRoom,
  type WrPointDetail, type WrRoomDetail, type WrRepair, type WrPersonStop,
} from '@/api/warRoom'
import { FLOOR_MAP_STATUS } from '@/components/FloorPlanMap/status'

const { Text, Title } = Typography

export type AssetTarget = { type: 'room'; room: string } | { type: 'point'; id: number; label?: string }

const RagicLink = ({ url }: { url: string }) => url
  ? <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }} onClick={e => e.stopPropagation()}>
      <LinkOutlined /> Ragic
    </a>
  : <Text type="secondary">—</Text>

// IHG 保養狀態：與 IHG 客房保養模組同一判定（後端 _calc_record_status）
const IHG_STATUS: Record<string, { label: string; color: string }> = {
  completed: { label: '已完成', color: 'green' },
  abnormal:  { label: '異常（待料）', color: 'red' },
  pending:   { label: '未完成', color: 'default' },
}

const statusTag = (s: keyof typeof FLOOR_MAP_STATUS) => {
  const m = FLOOR_MAP_STATUS[s] ?? FLOOR_MAP_STATUS.no_record
  return <Tag color={m.color} style={{ margin: 0 }}>{m.label}</Tag>
}

// ── 房間 ─────────────────────────────────────────────────────────────────────
function RoomPanel({ room, visits, onOpenVisit, onOpenRepair }: {
  room: string
  visits?: { person: string; stop: WrPersonStop }[]
  onOpenVisit?: (s: WrPersonStop) => void
  onOpenRepair?: (r: WrRepair) => void
}) {
  const [data, setData] = useState<WrRoomDetail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    setData(null); setErr(null)
    fetchWarRoomRoom(room)
      .then(d => { if (alive) setData(d) })
      .catch(e => { if (alive) setErr(e?.response?.data?.detail ?? '載入失敗') })
    return () => { alive = false }
  }, [room])

  if (err) return <Alert type="error" showIcon message={err} />
  if (!data) return <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div>
  const lastIhg = data.ihg[0]

  return (
    <div>
      <Space align="baseline" size={12} wrap>
        <Title level={3} style={{ margin: 0, color: '#1B3A5C' }}>{data.room}</Title>
        <Tag color="blue">{data.floor.toUpperCase()} 客房</Tag>
        <Tag color={data.repairs_open ? 'red' : 'green'}>未完成報修 {data.repairs_open}</Tag>
        <Text type="secondary">近 {data.days} 天報修 {data.repairs.length} 件</Text>
        {lastIhg && <Text type="secondary">最近 IHG 保養 {lastIhg.maint_date || '—'}（{IHG_STATUS[lastIhg.status]?.label ?? (lastIhg.status || '—')}）</Text>}
      </Space>

      {visits && (
        <div style={{ marginTop: 16 }}>
          <Text strong>今日到訪</Text>
          {visits.length === 0
            ? <div><Text type="secondary">今天沒有人到這間</Text></div>
            : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
                {visits.map(v => (
                  <div key={`${v.person}-${v.stop.seq}`} onClick={() => onOpenVisit?.(v.stop)}
                       style={{ cursor: onOpenVisit ? 'pointer' : 'default', padding: '4px 8px', background: '#f5f7fa', borderRadius: 6 }}>
                    <Text strong>{v.person}</Text>　<Text type="secondary">{v.stop.start_time || '—'}–{v.stop.end_time || '—'}</Text>　{v.stop.task}
                  </div>
                ))}
              </div>
            )}
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        <Text strong>報修紀錄</Text><Text type="secondary">（未完成全列；已完成列近 {data.days} 天）</Text>
        <Table
          size="small" style={{ marginTop: 6 }} rowKey={r => `${r.source}-${r.ragic_id}`} pagination={false}
          dataSource={data.repairs} locale={{ emptyText: '沒有報修紀錄' }}
          onRow={r => ({ onClick: () => onOpenRepair?.(r), style: { cursor: onOpenRepair ? 'pointer' : 'default' } })}
          columns={[
            { title: '報修時間', dataIndex: 'occurred_at', width: 130 },
            { title: '標題', dataIndex: 'title', render: (v: string) => <Text>{v}</Text> },
            { title: '狀態', dataIndex: 'status', width: 96,
              render: (v: string, r: WrRepair) => <Tag color={r.open ? 'red' : 'green'} style={{ margin: 0 }}>{v || '—'}</Tag> },
            { title: '等待', dataIndex: 'wait_days', width: 70, align: 'right' as const,
              render: (v: number | null, r: WrRepair) => r.open && v != null ? <Text type={v > 7 ? 'danger' : undefined}>{v} 天</Text> : '—' },
            { title: '', dataIndex: 'ragic_url', width: 70, render: (v: string) => <RagicLink url={v} /> },
          ]}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        <Text strong>IHG 客房保養</Text><Text type="secondary">（最近 12 次）</Text>
        <Table
          size="small" style={{ marginTop: 6 }} rowKey="ragic_id" pagination={false}
          dataSource={data.ihg} locale={{ emptyText: '沒有 IHG 保養紀錄' }}
          columns={[
            { title: '保養日期', dataIndex: 'maint_date', width: 110 },
            { title: '類型', dataIndex: 'maint_type', width: 90, render: (v: string) => v || '—' },
            { title: '狀態', dataIndex: 'status', width: 90,
              render: (v: string) => { const m = IHG_STATUS[v]; return <Tag color={m?.color} style={{ margin: 0 }}>{m?.label ?? (v || '—')}</Tag> } },
            { title: '保養人員', dataIndex: 'assignee', width: 90, render: (v: string) => v || '—' },
            { title: '工時', dataIndex: 'work_minutes', width: 70, align: 'right' as const, render: (v: number | null) => v != null ? `${v} 分` : '—' },
            { title: 'NG', dataIndex: 'ng_count', width: 56, align: 'right' as const,
              render: (v: number) => v ? <Text type="danger" strong>{v}</Text> : <Text type="secondary">0</Text> },
            { title: '備註', dataIndex: 'notes', render: (v: string) => <Text type="secondary">{v || '—'}</Text> },
            { title: '', dataIndex: 'ragic_url', width: 70, render: (v: string) => <RagicLink url={v} /> },
          ]}
        />
      </div>
    </div>
  )
}

// ── 設備（巡檢點位）─────────────────────────────────────────────────────────
function PointPanel({ id, date }: { id: number; date: string }) {
  const [data, setData] = useState<WrPointDetail | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    setData(null); setErr(null)
    fetchWarRoomPoint(id, date)
      .then(d => { if (alive) setData(d) })
      .catch(e => { if (alive) setErr(e?.response?.data?.detail ?? '載入失敗') })
    return () => { alive = false }
  }, [id, date])

  if (err) return <Alert type="error" showIcon message={err} />
  if (!data) return <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div>
  const p = data.point

  return (
    <div>
      <Space align="baseline" size={10} wrap>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>{p.label}</Title>
        {p.equipment_code && <Tag>{p.equipment_code}</Tag>}
        <Tag color="blue">{p.floor_key.toUpperCase()}</Tag>
        {statusTag(data.today.status)}
        {p.placement !== 'confirmed' && <Tag color="gold">點位尚未校正</Tag>}
      </Space>
      <Descriptions size="small" column={2} style={{ marginTop: 10 }}
                    labelStyle={{ width: 90, background: '#f5f7fa' }} bordered>
        <Descriptions.Item label="模組">{p.module_label}</Descriptions.Item>
        <Descriptions.Item label="設備組">{p.group_label}{p.system ? `（${p.system}）` : ''}</Descriptions.Item>
        {p.shared_label ? <Descriptions.Item label="共用" span={2}><Tag color="purple">{p.shared_label}</Tag></Descriptions.Item> : null}
        {Object.entries(p.attrs ?? {}).map(([k, v]) => <Descriptions.Item key={k} label={k}>{v}</Descriptions.Item>)}
        <Descriptions.Item label="巡檢人員">{data.today.inspectors.join('、') || '—'}</Descriptions.Item>
        <Descriptions.Item label="巡檢時段">
          <Space size={8} wrap>
            {data.today.batches.length
              ? data.today.batches.map((b, i) => (
                  <span key={i}>{b.start_hhmm || '—'}–{b.end_hhmm || '—'} <RagicLink url={b.ragic_url} /></span>
                ))
              : '—'}
          </Space>
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 16 }}>
        <Text strong>{data.date} 檢查結果</Text>
        <Table
          size="small" style={{ marginTop: 6 }} rowKey={(r, i) => `${r.check_content}-${i}`} pagination={false}
          dataSource={data.today.rows} locale={{ emptyText: '這天沒有巡檢紀錄' }}
          rowClassName={r => (r.abnormal ? 'ant-table-row-danger' : '')}
          columns={[
            { title: '檢查項目', dataIndex: 'check_content' },
            { title: '狀態', dataIndex: 'status', width: 80,
              render: (v: string) => statusTag((v in FLOOR_MAP_STATUS ? v : 'no_record') as keyof typeof FLOOR_MAP_STATUS) },
            { title: '結果', key: 'res',
              render: (_: unknown, r) => r.results.length
                ? r.results.map((x, i) => <div key={i}>{x.time_label ? <Text type="secondary">{x.time_label} </Text> : null}{x.text || '—'}</div>)
                : '—' },
            { title: '異常說明', dataIndex: 'abnormal_note', render: (v: string) => v ? <Text type="danger">{v}</Text> : '—' },
          ]}
        />
      </div>

      <div style={{ marginTop: 16 }}>
        <Text strong>本月每日狀況</Text>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
          {data.month.map(d => {
            const m = FLOOR_MAP_STATUS[d.status] ?? FLOOR_MAP_STATUS.no_record
            return (
              <Tooltip key={d.day} title={`${d.date}　${m.label}${d.abnormal_rows ? `（異常 ${d.abnormal_rows} 項）` : ''}`}>
                <div style={{
                  width: 26, height: 26, borderRadius: 5, background: m.color, color: '#fff', fontSize: 11,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600,
                  outline: d.date.replace(/\//g, '-') === data.date ? '2px solid #1B3A5C' : undefined,
                }}>{d.day}</div>
              </Tooltip>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export function AssetHistoryPanel({ target, date, visits, onOpenVisit, onOpenRepair }: {
  target: AssetTarget | null
  date: string
  visits?: { person: string; stop: WrPersonStop }[]
  onOpenVisit?: (s: WrPersonStop) => void
  onOpenRepair?: (r: WrRepair) => void
}) {
  if (!target) return <Empty description="選一間房或一台設備" />
  return target.type === 'room'
    ? <RoomPanel room={target.room} visits={visits} onOpenVisit={onOpenVisit} onOpenRepair={onOpenRepair} />
    : <PointPanel id={target.id} date={date} />
}

export function AssetHistoryDrawer({ target, date, visits, onClose, onOpenVisit, onOpenRepair, getContainer }: {
  target: AssetTarget | null
  date: string
  visits?: { person: string; stop: WrPersonStop }[]
  onClose: () => void
  onOpenVisit?: (s: WrPersonStop) => void
  onOpenRepair?: (r: WrRepair) => void
  getContainer?: () => HTMLElement
}) {
  return (
    <Drawer
      open={!!target} onClose={onClose} width={720} getContainer={getContainer}
      title={target ? (target.type === 'room' ? `房間履歷：${target.room}` : `設備履歷${target.label ? `：${target.label}` : ''}`) : ''}
      styles={{ body: { padding: '16px 20px' } }}
    >
      {target && <AssetHistoryPanel target={target} date={date} visits={visits} onOpenVisit={onOpenVisit} onOpenRepair={onOpenRepair} />}
    </Drawer>
  )
}

/** 單筆報修明細 Drawer（CLAUDE.md §7 標題列格式） */
export function RepairDrawer({ repair, onClose, onOpenRoom, getContainer }: {
  repair: WrRepair | null
  onClose: () => void
  onOpenRoom?: (room: string) => void
  getContainer?: () => HTMLElement
}) {
  const r = repair
  return (
    <Drawer
      open={!!r} onClose={onClose} width={480} getContainer={getContainer}
      styles={{ body: { padding: '16px 20px' } }}
      title={r && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Tag color="#4BA8E8" style={{ margin: 0 }}>現場報修</Tag>
          <span style={{ fontSize: 16, color: '#1B3A5C', fontWeight: 600 }}>
            {r.source_label}：<span style={{ fontWeight: 400 }}>{r.case_no || r.ragic_id}</span>
          </span>
          {!!r.ragic_url && (
            <a href={r.ragic_url} target="_blank" rel="noopener noreferrer"
               style={{ fontSize: 14, color: '#4BA8E8', display: 'flex', alignItems: 'center', gap: 3, fontWeight: 400 }}>
              <LinkOutlined /> 在 Ragic 查看
            </a>
          )}
        </div>
      )}
    >
      {r && (
        <>
          <Title level={5} style={{ margin: '0 0 12px', color: '#1B3A5C' }}>{r.title}</Title>
          <Descriptions bordered size="small" column={1} labelStyle={{ width: 100, background: '#f5f7fa', fontWeight: 500 }}>
            <Descriptions.Item label="處理狀況"><Tag color="red" style={{ margin: 0 }}>{r.status || '—'}</Tag></Descriptions.Item>
            <Descriptions.Item label="報修類型">{r.repair_type ? <Tag style={{ margin: 0 }}>{r.repair_type}</Tag> : '—'}</Descriptions.Item>
            <Descriptions.Item label="發生樓層">{r.floor_raw || '—'}</Descriptions.Item>
            <Descriptions.Item label="房號">
              {r.room
                ? <a onClick={() => onOpenRoom?.(r.room as string)}>{r.room}（看房間履歷）</a>
                : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="負責單位">{r.responsible_unit || '—'}</Descriptions.Item>
            <Descriptions.Item label="發生時間">{r.occurred_at || '—'}</Descriptions.Item>
            <Descriptions.Item label="等待天數">
              {r.wait_days != null ? <Text strong type={r.wait_days > 7 ? 'danger' : undefined}>{r.wait_days} 天</Text> : '—'}
            </Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Drawer>
  )
}
