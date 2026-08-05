/**
 * 收入結構分析（/jinxu/revenue）— 規格書 §13.4
 * TAB：科目別 / 大類 / 月趨勢 / 客房vs非客房 / 班別 / 分錄明細
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Card, Radio, Space, Table, Tabs, Tag, Typography,
} from 'antd'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'
import type { Dayjs } from 'dayjs'

import {
  fetchLedgerEntries, fetchRevenueByRoomKind, fetchRevenueBySubject,
  fetchRevenueMonthly, fetchShifts,
} from '@/api/jinxu'
import type {
  LedgerEntry, MonthlyGroupRow, RoomKindRow, ShiftRow, SubjectRow,
} from '@/types/jinxu'
import FilterBar, { toIso } from '../components/FilterBar'
import LedgerEntryDrawer from '../components/LedgerEntryDrawer'
import {
  CHART_PALETTE, GROUP_COLORS, dash, fmtInt, fmtMoney, fmtPct, moneyStyle,
} from '../components/constants'

const { Text } = Typography

export default function JinxuRevenue() {
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [tab, setTab] = useState('subject')
  const [subjects, setSubjects] = useState<SubjectRow[]>([])
  const [groups, setGroups] = useState<SubjectRow[]>([])
  const [monthly, setMonthly] = useState<MonthlyGroupRow[]>([])
  const [roomKind, setRoomKind] = useState<{ items: RoomKindRow[]; note: string } | null>(null)
  const [shifts, setShifts] = useState<{ shifts: ShiftRow[]; excluded_shifts: ShiftRow[]; note: string } | null>(null)
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [netMode, setNetMode] = useState<'net' | 'gross'>('net')
  const [drawerId, setDrawerId] = useState<number | null>(null)

  const f = { start_date: toIso(range?.[0]), end_date: toIso(range?.[1]) }

  const load = useCallback(async () => {
    setSubjects((await fetchRevenueBySubject(f, 'code')).items)
    setGroups((await fetchRevenueBySubject(f, 'group')).items)
    setMonthly((await fetchRevenueMonthly(f)).items)
    setRoomKind(await fetchRevenueByRoomKind(f.start_date, f.end_date))
    setShifts(await fetchShifts(f.start_date, f.end_date))
  }, [range])

  const loadEntries = useCallback(async () => {
    const r = await fetchLedgerEntries(
      { ...f, include_reversal: netMode === 'net' }, page, 50)
    setEntries(r.items); setTotal(r.total)
  }, [range, page, netMode])

  useEffect(() => { void load() }, [load])
  useEffect(() => { void loadEntries() }, [loadEntries])

  const subjectCols = [
    { title: '科目代碼', dataIndex: 'key', width: 100 },
    { title: '科目名稱', dataIndex: 'label', render: dash },
    { title: '筆數', dataIndex: 'count', align: 'right' as const, width: 90, render: fmtInt },
    {
      title: '淨額', dataIndex: 'amount', align: 'right' as const, width: 140,
      render: (v: number) => <Text strong style={moneyStyle(v)}>{fmtMoney(v)}</Text>,
      sorter: (a: SubjectRow, b: SubjectRow) => a.amount - b.amount,
    },
    {
      title: '佔比', dataIndex: 'share_pct', align: 'right' as const, width: 90,
      render: (v: number) => fmtPct(v, 2),
    },
    {
      title: '沖帳筆數', dataIndex: 'reversal_count', align: 'right' as const, width: 100,
      render: (v: number) => (v ? <Tag color="error">{v}</Tag> : '—'),
    },
  ]

  const entryCols = [
    { title: '營業日', dataIndex: 'business_date', width: 105 },
    { title: '建檔時間', dataIndex: 'created_at_text', width: 160 },
    { title: '班別', dataIndex: 'shift', width: 60 },
    { title: '操作員', dataIndex: 'operator_id', width: 95 },
    {
      title: '房號', dataIndex: 'room_no', width: 90,
      render: (v: string, r: LedgerEntry) => (
        <>{dash(v)}{r.room_kind !== 'GUEST' && <Tag color="default" style={{ marginLeft: 4 }}>非客房</Tag>}</>
      ),
    },
    {
      title: '科目', dataIndex: 'subject_code', width: 170,
      render: (_: unknown, r: LedgerEntry) => (
        <Tag color={GROUP_COLORS[r.subject_group] || '#bdc3c7'}>
          {r.subject_code}.{r.subject_name}
        </Tag>
      ),
    },
    {
      title: '金額', dataIndex: 'amount', align: 'right' as const, width: 125,
      render: (v: number) => <Text strong style={moneyStyle(v)}>{fmtMoney(v)}</Text>,
    },
    { title: '帳單別', dataIndex: 'folio_type', width: 80, render: dash },
    { title: '訂房號碼', dataIndex: 'booking_no', width: 100, render: dash },
    {
      title: '沖帳', dataIndex: 'is_reversal', width: 70,
      render: (v: number) => (v ? <Tag color="error">沖帳</Tag> : '—'),
    },
  ]

  return (
    <div>
      <FilterBar range={range} onChange={setRange} onReload={() => { void load(); void loadEntries() }} />
      <Tabs activeKey={tab} onChange={setTab} items={[
        {
          key: 'subject', label: '科目別',
          children: (
            <Card size="small">
              <Table<SubjectRow> rowKey="key" size="small" dataSource={subjects}
                                 columns={subjectCols} pagination={false} />
            </Card>
          ),
        },
        {
          key: 'group', label: '大類',
          children: (
            <Card size="small">
              <ResponsiveContainer width="100%" height={320}>
                <PieChart>
                  <Pie data={groups} dataKey="amount" nameKey="label" cx="50%" cy="50%"
                       outerRadius={110} label={(p: { label?: string }) => p.label ?? ''}>
                    {groups.map((g, i) => (
                      <Cell key={i} fill={GROUP_COLORS[g.key] || CHART_PALETTE[i % CHART_PALETTE.length]} />
                    ))}
                  </Pie>
                  <RcTooltip formatter={(v: number) => fmtMoney(v)} />
                </PieChart>
              </ResponsiveContainer>
              <Table<SubjectRow> rowKey="key" size="small" dataSource={groups}
                                 columns={subjectCols} pagination={false} />
            </Card>
          ),
        },
        {
          key: 'monthly', label: '月趨勢',
          children: (
            <Card size="small">
              <ResponsiveContainer width="100%" height={360}>
                <BarChart data={monthly.map((m) => ({
                  month: m.month,
                  ...Object.fromEntries(Object.entries(m.groups).map(([k, v]) => [k, v.amount])),
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis tickFormatter={(v) => `${Math.round(v / 10000)}萬`} />
                  <RcTooltip formatter={(v: number) => fmtMoney(v)} />
                  <Legend />
                  {Array.from(new Set(monthly.flatMap((m) => Object.keys(m.groups)))).map((g) => (
                    <Bar key={g} dataKey={g} stackId="a" name={g}
                         fill={GROUP_COLORS[g] || '#bdc3c7'} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </Card>
          ),
        },
        {
          key: 'roomkind', label: '客房 vs 非客房',
          children: (
            <Card size="small">
              {roomKind && <Alert type="info" showIcon message={roomKind.note} style={{ marginBottom: 12 }} />}
              {roomKind?.items.map((k) => (
                <Card key={k.room_kind} size="small" title={
                  <Space><Tag color={k.room_kind === 'GUEST' ? 'blue' : 'default'}>{k.label}</Tag>
                    <Text strong>{fmtMoney(k.amount)}</Text>
                    <Text type="secondary">{fmtInt(k.count)} 筆</Text></Space>
                } style={{ marginBottom: 12 }}>
                  <Table size="small" rowKey="subject_code" pagination={false}
                         dataSource={k.subjects}
                         columns={[
                           { title: '科目', dataIndex: 'subject_code', width: 90 },
                           { title: '名稱', dataIndex: 'subject_name', render: dash },
                           { title: '筆數', dataIndex: 'count', align: 'right', width: 90, render: fmtInt },
                           { title: '金額', dataIndex: 'amount', align: 'right', width: 140,
                             render: (v: number) => <span style={moneyStyle(v)}>{fmtMoney(v)}</span> },
                         ]} />
                </Card>
              ))}
            </Card>
          ),
        },
        {
          key: 'shift', label: '班別',
          children: (
            <Card size="small">
              {shifts && <Alert type="info" showIcon message={shifts.note} style={{ marginBottom: 12 }} />}
              <Table size="small" rowKey="shift" pagination={false} dataSource={shifts?.shifts ?? []}
                     columns={[
                       { title: '班別', dataIndex: 'shift', width: 90 },
                       { title: '交易筆數', dataIndex: 'count', align: 'right', width: 120, render: fmtInt },
                       { title: '金額', dataIndex: 'amount', align: 'right', width: 160,
                         render: (v: number) => <span style={moneyStyle(v)}>{fmtMoney(v)}</span> },
                       { title: '沖帳次數', dataIndex: 'reversal_count', align: 'right', width: 110,
                         render: (v: number) => (v ? <Tag color="error">{v}</Tag> : '—') },
                     ]} />
              {!!shifts?.excluded_shifts.length && (
                <>
                  <Text type="secondary" style={{ display: 'block', margin: '16px 0 8px' }}>
                    已排除的系統作業班別
                  </Text>
                  <Table size="small" rowKey="shift" pagination={false}
                         dataSource={shifts.excluded_shifts}
                         columns={[
                           { title: '班別', dataIndex: 'shift', width: 90 },
                           { title: '筆數', dataIndex: 'count', align: 'right', width: 120, render: fmtInt },
                           { title: '金額', dataIndex: 'amount', align: 'right', width: 160,
                             render: (v: number) => fmtMoney(v) },
                         ]} />
                </>
              )}
            </Card>
          ),
        },
        {
          key: 'entries', label: '分錄明細',
          children: (
            <Card size="small">
              <Space style={{ marginBottom: 12 }}>
                <Radio.Group value={netMode} onChange={(e) => { setNetMode(e.target.value); setPage(1) }}
                             optionType="button" buttonStyle="solid">
                  <Radio.Button value="net">淨額（含沖帳，正負抵銷）</Radio.Button>
                  <Radio.Button value="gross">僅原始入帳（排除沖帳列）</Radio.Button>
                </Radio.Group>
              </Space>
              <Table<LedgerEntry>
                rowKey="id" size="small" dataSource={entries} columns={entryCols}
                scroll={{ x: 1180 }}
                onRow={(r) => ({ onClick: () => setDrawerId(r.id), style: { cursor: 'pointer' } })}
                pagination={{
                  current: page, pageSize: 50, total, showSizeChanger: false,
                  onChange: setPage, showTotal: (t) => `共 ${fmtInt(t)} 筆`,
                }}
              />
            </Card>
          ),
        },
      ]} />
      <LedgerEntryDrawer entryId={drawerId} open={drawerId !== null} onClose={() => setDrawerId(null)} />
    </div>
  )
}
