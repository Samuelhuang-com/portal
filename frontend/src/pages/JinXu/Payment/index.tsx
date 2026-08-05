/**
 * 付款方式分析（/jinxu/payment）— 規格書 §13.5
 * TAB：付款方式佔比 / 月趨勢 / 分錄明細
 *
 * ⚠️ 金額為刷卡／收款總額，不含手續費，**非淨收**（§19.2 Q5 未提供費率）。
 */
import { useCallback, useEffect, useState } from 'react'
import { Alert, Card, Table, Tabs, Tag, Typography } from 'antd'
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'
import type { Dayjs } from 'dayjs'

import { fetchPaymentEntries, fetchPaymentMonthly, fetchPaymentSummary } from '@/api/jinxu'
import type { LedgerEntry, MonthlyGroupRow, PaymentSummary } from '@/types/jinxu'
import FilterBar, { toIso } from '../components/FilterBar'
import LedgerEntryDrawer from '../components/LedgerEntryDrawer'
import { CHART_PALETTE, GROUP_COLORS, dash, fmtInt, fmtMoney, fmtPct } from '../components/constants'

const { Text } = Typography

export default function JinxuPayment() {
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [sum, setSum] = useState<PaymentSummary | null>(null)
  const [monthly, setMonthly] = useState<MonthlyGroupRow[]>([])
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [drawerId, setDrawerId] = useState<number | null>(null)

  const f = { start_date: toIso(range?.[0]), end_date: toIso(range?.[1]) }

  const load = useCallback(async () => {
    setSum(await fetchPaymentSummary(f.start_date, f.end_date))
    setMonthly((await fetchPaymentMonthly(f.start_date, f.end_date)).items)
  }, [range])

  const loadEntries = useCallback(async () => {
    const r = await fetchPaymentEntries({ ...f, page, page_size: 50 })
    setEntries(r.items); setTotal(r.total)
  }, [range, page])

  useEffect(() => { void load() }, [load])
  useEffect(() => { void loadEntries() }, [loadEntries])

  return (
    <div>
      <FilterBar range={range} onChange={setRange} onReload={() => { void load(); void loadEntries() }} />
      {sum && <Alert type="info" showIcon message={sum.note} style={{ marginBottom: 16 }} />}
      <Tabs items={[
        {
          key: 'share', label: '付款方式佔比',
          children: (
            <Card size="small">
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={sum?.by_macro ?? []} dataKey="amount" nameKey="label"
                       cx="50%" cy="50%" outerRadius={105}
                       label={(p: { label?: string }) => p.label ?? ''}>
                    {(sum?.by_macro ?? []).map((_, i) => (
                      <Cell key={i} fill={CHART_PALETTE[i % CHART_PALETTE.length]} />
                    ))}
                  </Pie>
                  <RcTooltip formatter={(v: number) => fmtMoney(v)} />
                </PieChart>
              </ResponsiveContainer>
              <Text strong style={{ display: 'block', margin: '8px 0' }}>合併大類</Text>
              <Table size="small" rowKey="key" pagination={false} dataSource={sum?.by_macro ?? []}
                     columns={[
                       { title: '類別', dataIndex: 'label' },
                       { title: '筆數', dataIndex: 'count', align: 'right', width: 100, render: fmtInt },
                       { title: '金額', dataIndex: 'amount', align: 'right', width: 150,
                         render: (v: number) => <Text strong>{fmtMoney(v)}</Text> },
                       { title: '佔比', dataIndex: 'share_pct', align: 'right', width: 90,
                         render: (v: number) => fmtPct(v, 2) },
                     ]} />
              <Text strong style={{ display: 'block', margin: '16px 0 8px' }}>明細科目</Text>
              <Table size="small" rowKey="subject_code" pagination={false} dataSource={sum?.by_subject ?? []}
                     columns={[
                       { title: '科目', dataIndex: 'subject_code', width: 90 },
                       { title: '名稱', dataIndex: 'subject_name', render: dash },
                       { title: '筆數', dataIndex: 'count', align: 'right', width: 100, render: fmtInt },
                       { title: '金額', dataIndex: 'amount', align: 'right', width: 150,
                         render: (v: number) => fmtMoney(v) },
                       { title: '佔比', dataIndex: 'share_pct', align: 'right', width: 90,
                         render: (v: number) => fmtPct(v, 2) },
                     ]} />
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
                    <Bar key={g} dataKey={g} stackId="a" name={g} fill={GROUP_COLORS[g] || '#bdc3c7'} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </Card>
          ),
        },
        {
          key: 'entries', label: '分錄明細',
          children: (
            <Card size="small">
              <Table<LedgerEntry> rowKey="id" size="small" dataSource={entries} scroll={{ x: 900 }}
                onRow={(r) => ({ onClick: () => setDrawerId(r.id), style: { cursor: 'pointer' } })}
                columns={[
                  { title: '營業日', dataIndex: 'business_date', width: 105 },
                  { title: '科目', dataIndex: 'subject_code', width: 175,
                    render: (_: unknown, r: LedgerEntry) => (
                      <Tag color={GROUP_COLORS[r.subject_group] || '#bdc3c7'}>
                        {r.subject_code}.{r.subject_name}</Tag>) },
                  { title: '金額', dataIndex: 'amount', align: 'right', width: 130,
                    render: (v: number) => <Text strong style={{ color: '#cf1322' }}>{fmtMoney(v)}</Text> },
                  { title: '房號', dataIndex: 'room_no', width: 90, render: dash },
                  { title: '訂房號碼', dataIndex: 'booking_no', width: 100, render: dash },
                  { title: '帳單別', dataIndex: 'folio_type', width: 80, render: dash },
                ]}
                pagination={{ current: page, pageSize: 50, total, showSizeChanger: false,
                              onChange: setPage, showTotal: (t) => `共 ${fmtInt(t)} 筆` }} />
            </Card>
          ),
        },
      ]} />
      <LedgerEntryDrawer entryId={drawerId} open={drawerId !== null} onClose={() => setDrawerId(null)} />
    </div>
  )
}
