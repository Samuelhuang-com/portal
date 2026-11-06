/**
 * 戰情 KPI — 人員工作日誌（人員 × 日期）
 *
 * Y 軸＝人員、X 軸＝MM/DD；每格列出當天工作（顏色＝工項類別，點了開工作日誌明細）。
 * 資料來源：GET /war-room/person-journal（與 exec-work-dashboard「工作日誌」TAB 同口徑：具名人員、全部場所）。
 * 區間：StandardRangePicker（錨點＝資料最後一天），上限 31 天；人員篩選在前端做。（2026-11-06 新增）
 */
import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Card, Empty, Select, Space, Spin, Table, Tag, Tooltip, Typography } from 'antd'
import dayjs from 'dayjs'

import { fetchWarRoomPersonJournal, type WrPersonJournal, type WrPersonJournalResp } from '@/api/warRoom'
import type { JournalRow } from '@/api/workJournal'
import JournalRowDrawer from '@/components/WorkJournal/JournalRowDrawer'
import StandardRangePicker, { type StandardRange } from '@/components/StandardRangePicker'

const { Text } = Typography

const CAT_COLORS = ['#4BA8E8', '#3ccf91', '#f2a93b', '#b37feb', '#ef5a5a', '#36cfc9', '#ffd666', '#9254de', '#73d13d', '#ff85c0']
const MAX_SHOWN = 3
const DAY_W = 104
const NAME_W = 110

function CellItems({ items, colorOf, onOpen }: {
  items: JournalRow[]
  colorOf: (cat: string) => string
  onOpen: (r: JournalRow) => void
}) {
  const shown = items.slice(0, MAX_SHOWN)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {shown.map((r, i) => (
        <Tooltip key={`${r.seq}-${i}`}
                 title={`${r.start_time ? `${r.start_time}${r.end_time ? `～${r.end_time}` : ''} ` : ''}${r.task}（${r.source_label}）${r.work_min != null ? `・${r.work_min} 分` : ''}`}>
          <div onClick={() => onOpen(r)}
               style={{
                 background: colorOf(r.category), color: '#06101f', borderRadius: 3, padding: '1px 4px',
                 fontSize: 11, lineHeight: '16px', whiteSpace: 'nowrap', overflow: 'hidden',
                 textOverflow: 'ellipsis', cursor: 'pointer',
               }}>
            {r.task || r.source_label}
          </div>
        </Tooltip>
      ))}
      {items.length > MAX_SHOWN && <Text type="secondary" style={{ fontSize: 11 }}>+{items.length - MAX_SHOWN} 筆</Text>}
    </div>
  )
}

export default function PersonJournalTab() {
  const [range, setRange] = useState<StandardRange>(() => [dayjs().startOf('month'), dayjs()])
  const [data, setData] = useState<WrPersonJournalResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pick, setPick] = useState<string[]>([])
  const [row, setRow] = useState<JournalRow | null>(null)

  useEffect(() => {
    if (!range) return
    let alive = true
    setLoading(true); setError(null)
    fetchWarRoomPersonJournal(range[0].format('YYYY-MM-DD'), range[1].format('YYYY-MM-DD'))
      .then(d => { if (alive) setData(d) })
      .catch((e: any) => { if (alive) setError(e?.response?.data?.detail ?? e?.message ?? '載入失敗') })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [range])

  const cats = useMemo(() => {
    const s = new Set<string>()
    data?.persons.forEach(p => Object.values(p.cells).forEach(l => l.forEach(r => s.add(r.category))))
    return Array.from(s).sort()
  }, [data])
  const colorOf = (cat: string) => CAT_COLORS[Math.max(0, cats.indexOf(cat)) % CAT_COLORS.length]

  const persons: WrPersonJournal[] = (data?.persons ?? []).filter(p => pick.length === 0 || pick.includes(p.person))
  const itemCount = persons.reduce((n, p) => n + Object.values(p.cells).reduce((m, l) => m + l.length, 0), 0)
  const totalMin = persons.reduce((n, p) => n + p.total_min, 0)

  const columns = [
    {
      title: '人員', dataIndex: 'person', key: 'person', fixed: 'left' as const, width: NAME_W,
      render: (_: string, p: WrPersonJournal) => (
        <div>
          <div style={{ fontWeight: 600 }}>{p.person}</div>
          <Text type="secondary" style={{ fontSize: 11 }}>{(p.total_min / 60).toFixed(1)} h</Text>
        </div>
      ),
    },
    ...(data?.days ?? []).map(d => {
      const weekend = d.weekday === '六' || d.weekday === '日'
      return {
        title: (
          <div style={{ textAlign: 'center', lineHeight: 1.2, color: weekend ? '#FAAD14' : undefined }}>
            <div>{dayjs(d.date).format('MM/DD')}</div>
            <div style={{ fontSize: 11 }}>{d.weekday}</div>
          </div>
        ),
        key: d.date, width: DAY_W, align: 'left' as const,
        render: (_: unknown, p: WrPersonJournal) => {
          const items = p.cells[d.date] ?? []
          return items.length ? <CellItems items={items} colorOf={colorOf} onOpen={setRow} /> : null
        },
      }
    }),
  ]

  return (
    <Card size="small">
      <Space wrap size={[12, 8]} style={{ width: '100%', justifyContent: 'space-between', marginBottom: 10 }}>
        <Space wrap>
          <StandardRangePicker value={range} anchor={data?.data_end} onChange={setRange}
                               hidePresets={['thisYear', 'lastYear', 'all']} />
          <Select mode="multiple" allowClear placeholder="全部人員" style={{ minWidth: 240 }}
                  value={pick} onChange={setPick} maxTagCount="responsive"
                  options={(data?.persons ?? []).map(p => ({ label: p.person, value: p.person }))} />
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {persons.length} 人・{itemCount} 筆工作・{(totalMin / 60).toFixed(1)} h
          {data && `　資料至 ${data.data_end}`}
        </Text>
      </Space>

      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 10 }} />}

      {cats.length > 0 && (
        <Space size={[6, 6]} wrap style={{ marginBottom: 8 }}>
          {cats.map(c => <Tag key={c} style={{ background: colorOf(c), color: '#06101f', border: 'none', margin: 0 }}>{c}</Tag>)}
        </Space>
      )}

      <Spin spinning={loading && !data}>
        {data && persons.length > 0 ? (
          <Table
            size="small"
            bordered
            pagination={false}
            rowKey="person"
            columns={columns}
            dataSource={persons}
            scroll={{ x: NAME_W + (data.days.length * DAY_W), y: 640 }}
          />
        ) : (
          !loading && <Empty description={`${range?.[0]?.format('MM/DD') ?? ''}～${range?.[1]?.format('MM/DD') ?? ''} 沒有具名人員的工作日誌`} />
        )}
      </Spin>

      <JournalRowDrawer row={row} onClose={() => setRow(null)} />
    </Card>
  )
}
