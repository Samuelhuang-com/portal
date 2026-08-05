/**
 * 預收訂金追蹤（/jinxu/deposit）— 規格書 §13.6
 * TAB：概況 / 月度收沖 / 分錄明細
 *
 * ⚠️ 概況 TAB 頂部固定 Alert：未沖餘額需完整歷史資料才準確（§11.8）。
 * ⚠️ J21：只做總額層級，不做 64A↔81A 逐筆配對。
 */
import { useCallback, useEffect, useState } from 'react'
import { Alert, Card, Col, Radio, Row, Space, Statistic, Table, Tabs, Tag, Typography } from 'antd'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, ComposedChart,
  ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'
import type { Dayjs } from 'dayjs'

import { fetchDepositEntries, fetchDepositMonthly, fetchDepositSummary } from '@/api/jinxu'
import type { DepositMonthRow, DepositSummary, LedgerEntry } from '@/types/jinxu'
import FilterBar, { toIso } from '../components/FilterBar'
import LedgerEntryDrawer from '../components/LedgerEntryDrawer'
import { GROUP_COLORS, dash, fmtInt, fmtMoney, moneyStyle } from '../components/constants'

const { Text } = Typography

export default function JinxuDeposit() {
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [sum, setSum] = useState<DepositSummary | null>(null)
  const [monthly, setMonthly] = useState<DepositMonthRow[]>([])
  const [dir, setDir] = useState<'all' | 'in' | 'out'>('all')
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [drawerId, setDrawerId] = useState<number | null>(null)

  const f = { start_date: toIso(range?.[0]), end_date: toIso(range?.[1]) }

  const load = useCallback(async () => {
    setSum(await fetchDepositSummary(f.start_date, f.end_date))
    setMonthly((await fetchDepositMonthly(f.start_date, f.end_date)).items)
  }, [range])

  const loadEntries = useCallback(async () => {
    const r = await fetchDepositEntries({ ...f, direction: dir, page, page_size: 50 })
    setEntries(r.items); setTotal(r.total)
  }, [range, dir, page])

  useEffect(() => { void load() }, [load])
  useEffect(() => { void loadEntries() }, [loadEntries])

  return (
    <div>
      <FilterBar range={range} onChange={setRange} onReload={() => { void load(); void loadEntries() }} />
      <Tabs items={[
        {
          key: 'overview', label: '概況',
          children: (
            <Card size="small">
              {sum && <Alert type="warning" showIcon message={sum.warning} style={{ marginBottom: 16 }} />}
              <Row gutter={16}>
                <Col span={6}><Card size="small">
                  <Statistic title="預收發生" value={sum?.inflow_amount ?? 0} precision={0} prefix="$" />
                  <Text type="secondary">{fmtInt(sum?.inflow_count ?? 0)} 筆</Text>
                </Card></Col>
                <Col span={6}><Card size="small">
                  <Statistic title="預收沖銷" value={sum?.outflow_amount ?? 0} precision={0} prefix="$" />
                  <Text type="secondary">{fmtInt(sum?.outflow_count ?? 0)} 筆</Text>
                </Card></Col>
                <Col span={6}><Card size="small">
                  <Statistic title="未沖餘額" value={sum?.net_balance ?? 0} precision={0} prefix="$"
                             valueStyle={{ color: (sum?.net_balance ?? 0) < 0 ? '#cf1322' : undefined }} />
                </Card></Col>
                <Col span={6}><Card size="small">
                  <Statistic title="資料起始日" value={sum?.data_start_date ?? '—'} />
                </Card></Col>
              </Row>
              {sum && <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>{sum.note}</Text>}
            </Card>
          ),
        },
        {
          key: 'monthly', label: '月度收沖',
          children: (
            <Card size="small">
              <ResponsiveContainer width="100%" height={360}>
                <ComposedChart data={monthly}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis tickFormatter={(v) => `${Math.round(v / 10000)}萬`} />
                  <RcTooltip formatter={(v: number) => fmtMoney(v)} />
                  <Legend />
                  <Bar dataKey="inflow" name="發生" fill="#f39c12" />
                  <Bar dataKey="outflow" name="沖銷" fill="#4BA8E8" />
                  <Line type="monotone" dataKey="cumulative_balance" name="累計餘額" stroke="#1B3A5C" />
                </ComposedChart>
              </ResponsiveContainer>
              <Table<DepositMonthRow> rowKey="month" size="small" pagination={false} dataSource={monthly}
                columns={[
                  { title: '月份', dataIndex: 'month', width: 110 },
                  { title: '發生', dataIndex: 'inflow', align: 'right', width: 150, render: (v: number) => fmtMoney(v) },
                  { title: '沖銷', dataIndex: 'outflow', align: 'right', width: 150, render: (v: number) => fmtMoney(v) },
                  { title: '淨額', dataIndex: 'net', align: 'right', width: 150,
                    render: (v: number) => <span style={moneyStyle(v)}>{fmtMoney(v)}</span> },
                  { title: '累計餘額', dataIndex: 'cumulative_balance', align: 'right', width: 160,
                    render: (v: number) => <Text strong style={moneyStyle(v)}>{fmtMoney(v)}</Text> },
                ]} />
            </Card>
          ),
        },
        {
          key: 'entries', label: '分錄明細',
          children: (
            <Card size="small">
              <Space style={{ marginBottom: 12 }}>
                <Radio.Group value={dir} onChange={(e) => { setDir(e.target.value); setPage(1) }}
                             optionType="button" buttonStyle="solid">
                  <Radio.Button value="all">全部</Radio.Button>
                  <Radio.Button value="in">預收（64／64A）</Radio.Button>
                  <Radio.Button value="out">沖銷（81／81A）</Radio.Button>
                </Radio.Group>
              </Space>
              <Table<LedgerEntry> rowKey="id" size="small" dataSource={entries} scroll={{ x: 900 }}
                onRow={(r) => ({ onClick: () => setDrawerId(r.id), style: { cursor: 'pointer' } })}
                columns={[
                  { title: '營業日', dataIndex: 'business_date', width: 105 },
                  { title: '科目', dataIndex: 'subject_code', width: 185,
                    render: (_: unknown, r: LedgerEntry) => (
                      <Tag color={GROUP_COLORS[r.subject_group] || '#bdc3c7'}>
                        {r.subject_code}.{r.subject_name}</Tag>) },
                  { title: '金額', dataIndex: 'amount', align: 'right', width: 130,
                    render: (v: number) => <Text strong style={moneyStyle(v)}>{fmtMoney(v)}</Text> },
                  { title: '單據號碼', dataIndex: 'document_no', width: 120, render: dash },
                  { title: '應收代碼', dataIndex: 'ar_code', width: 120, render: dash },
                  { title: '訂房號碼', dataIndex: 'booking_no', width: 100, render: dash },
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
