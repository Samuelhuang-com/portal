/**
 * 營收分析（/opera/revenue）
 * 規格書：docs/SPEC_opera_analytics.md §11.3、圖表 C4 / C5 / C6 / C7 / C8
 *
 * TAB：每日 / 每月 / 每年 / 四象限 / 營收異常
 * 資料來源一律為 History and Forecast（決策 D7）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Empty, Radio, Row, Select, Space,
  Spin, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import { InfoCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip as RcTooltip, XAxis, YAxis, ZAxis, Cell,
} from 'recharts'

import {
  fetchAnomalies, fetchQuadrant, fetchRevenueDaily, fetchRevenueDayDetail,
  fetchRevenueMonthly, fetchRevenueYearly,
} from '@/api/opera'
import type {
  AnomalyResult, QuadrantBasis, QuadrantResult, RevenueDailyRow,
  RevenueMonthlyResult, RevenueYearRow,
} from '@/types/opera'
import RevenueDayDetailDrawer from '../components/RevenueDayDetailDrawer'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED, TRIGGER_TAG,
  fmtInt, fmtMoney, fmtPct, fmtPpt, fmtYoY, periodTagColor, trendColor,
} from '../components/formatters'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const CHART_HEIGHT = 320
const SOURCE_NOTE = '資料來源：History and Forecast'

const QUADRANT_COLORS: Record<string, string> = {
  Q1: GREEN, Q2: ACCENT, Q3: GREY, Q4: ORANGE,
}

const OperaRevenuePage: React.FC = () => {
  const [tab, setTab] = useState('daily')
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [loading, setLoading] = useState(false)

  const [daily, setDaily] = useState<RevenueDailyRow[]>([])
  const [monthly, setMonthly] = useState<RevenueMonthlyResult | null>(null)
  const [yearly, setYearly] = useState<RevenueYearRow[]>([])
  const [quadrant, setQuadrant] = useState<QuadrantResult | null>(null)
  const [anomalies, setAnomalies] = useState<AnomalyResult | null>(null)

  const [year, setYear] = useState<number>(dayjs().year())
  const [quadrantBasis, setQuadrantBasis] = useState<QuadrantBasis>('common')
  const [drawerRow, setDrawerRow] = useState<RevenueDailyRow | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const rangeParams = useMemo(
    () => (range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
    [range],
  )

  // ── 載入 ────────────────────────────────────────────────────────────────
  const load = useCallback(async (which: string) => {
    setLoading(true)
    try {
      if (which === 'daily') {
        const res = await fetchRevenueDaily(rangeParams)
        setDaily(res.items)
        if (!range) setRange([dayjs(res.start), dayjs(res.end)])
      } else if (which === 'monthly') {
        setMonthly(await fetchRevenueMonthly(year))
      } else if (which === 'yearly') {
        const res = await fetchRevenueYearly()
        setYearly(res.years)
        if (res.years.length && !res.years.some((y) => y.year === year)) {
          setYear(res.years[res.years.length - 1].year)
        }
      } else if (which === 'quadrant') {
        setQuadrant(await fetchQuadrant({ ...rangeParams, basis: quadrantBasis }))
      } else if (which === 'anomalies') {
        setAnomalies(await fetchAnomalies(rangeParams))
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入營收分析失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, range, year, quadrantBasis])

  useEffect(() => { load(tab) }, [tab, load])

  const openDayDrawer = useCallback(async (row: RevenueDailyRow) => {
    setDrawerRow(row)
    setDrawerOpen(true)
    try {
      setDrawerRow(await fetchRevenueDayDetail(row.business_date, { record_type: row.record_type }))
    } catch {
      /* 已有列表資料可顯示，忽略 */
    }
  }, [])

  // ── C4：每日營收 + 住房率 ────────────────────────────────────────────────
  const dailyChart = useMemo(
    () => daily.map((d) => ({
      date: d.business_date.slice(5),
      營收: Math.round(d.revenue),
      住房率: Number((d.occupancy * 100).toFixed(1)),
      ADR: Math.round(d.adr),
    })),
    [daily],
  )

  const dailyColumns: ColumnsType<RevenueDailyRow> = [
    { title: '營業日', dataIndex: 'business_date', width: 110, fixed: 'left', sorter: (a, b) => a.business_date.localeCompare(b.business_date) },
    { title: '房間營收', dataIndex: 'revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}`, sorter: (a, b) => a.revenue - b.revenue },
    { title: '已售房晚', dataIndex: 'sold_rooms', align: 'right', render: fmtInt, sorter: (a, b) => a.sold_rooms - b.sold_rooms },
    { title: '可售房晚', dataIndex: 'available_rooms', align: 'right', render: fmtInt },
    { title: 'OOO', dataIndex: 'ooo_rooms', align: 'right', render: (v: number) => (v > 0 ? <Text style={{ color: ORANGE }}>{fmtInt(v)}</Text> : EMPTY) },
    { title: 'ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}`, sorter: (a, b) => a.adr - b.adr },
    { title: '住房率', dataIndex: 'occupancy', align: 'right', render: (v: number) => fmtPct(v), sorter: (a, b) => a.occupancy - b.occupancy },
    { title: 'RevPAR', dataIndex: 'revpar', align: 'right', render: (v: number) => `$${fmtMoney(v)}`, sorter: (a, b) => a.revpar - b.revpar },
    { title: '散客房晚', dataIndex: 'individual_rooms', align: 'right', render: fmtInt },
    { title: '團體房晚', dataIndex: 'group_rooms', align: 'right', render: fmtInt },
  ]

  // ── C5：月營收 YoY + 成長率 ─────────────────────────────────────────────
  const monthlyChart = useMemo(() => {
    if (!monthly) return []
    return monthly.months.map((m) => ({
      label: m.label,
      本年營收: Math.round(m.current.revenue),
      去年營收: m.has_compare ? Math.round(m.compare.revenue) : null,
      成長率: m.revenue_yoy === null ? null : Number((m.revenue_yoy * 100).toFixed(1)),
    }))
  }, [monthly])

  // ── C6：年度橫向對比 ────────────────────────────────────────────────────
  const yearlyChart = useMemo(
    () => yearly.map((y) => ({
      label: `${y.year}${y.is_complete ? '' : '（部分）'}`,
      營收: Math.round(y.revenue),
      ADR: Math.round(y.adr),
      住房率: Number((y.occupancy * 100).toFixed(1)),
    })),
    [yearly],
  )

  // ── C7：四象限散佈圖 ────────────────────────────────────────────────────
  const quadrantSeries = useMemo(() => {
    if (!quadrant) return []
    return quadrant.points.map((p) => ({
      x: Number((p.occupancy * 100).toFixed(1)),
      y: p.adr,
      z: Math.max(p.revenue, 1),
      ...p,
    }))
  }, [quadrant])

  return (
    <Spin spinning={loading}>
      <div style={{ padding: 24 }}>
        <Row justify="space-between" align="middle" style={{ marginBottom: 12 }}>
          <Col>
            <Title level={4} style={{ margin: 0, color: BRAND }}>營收分析</Title>
          </Col>
          <Col>
            <Space wrap>
              <RangePicker
                value={range}
                onChange={(v) => setRange(v as [Dayjs, Dayjs] | null)}
                allowClear={false}
              />
              <Button icon={<ReloadOutlined />} onClick={() => load(tab)}>重新整理</Button>
            </Space>
          </Col>
        </Row>

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message={`${SOURCE_NOTE}　｜　可售房晚 = 實體房數 − OOO（CF_CALC_INV_ROOMS）`}
          description="ADR／住房率／RevPAR 一律用加總後的加權公式計算，不是每日數值的平均。"
        />

        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            // ── 每日 ─────────────────────────────────────────────────────
            {
              key: 'daily',
              label: '每日',
              children: (
                <>
                  <Card size="small" title="每日營收與住房率" style={{ marginBottom: 12 }}>
                    {dailyChart.length === 0 ? <Empty description="期間內無 History 資料" /> : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <ComposedChart data={dailyChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" minTickGap={24} />
                          <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
                          <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}%`} />
                          <RcTooltip formatter={(v: any, n: string) => [n === '住房率' ? `${v}%` : Number(v).toLocaleString('en-US'), n]} />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Bar yAxisId="left" dataKey="營收" fill={BRAND} />
                          <Line yAxisId="right" type="monotone" dataKey="住房率" stroke={ORANGE} strokeWidth={2} dot={false} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                  </Card>

                  <Card size="small" title="每日明細（點擊列開啟明細）">
                    <Table
                      rowKey="id"
                      size="small"
                      dataSource={daily}
                      columns={dailyColumns}
                      scroll={{ x: 1100 }}
                      pagination={{ pageSize: 31, showSizeChanger: true, showTotal: (t) => `共 ${t} 天` }}
                      onRow={(record) => ({ onClick: () => openDayDrawer(record), style: { cursor: 'pointer' } })}
                    />
                  </Card>
                </>
              ),
            },

            // ── 每月 ─────────────────────────────────────────────────────
            {
              key: 'monthly',
              label: '每月',
              children: (
                <>
                  <Space style={{ marginBottom: 12 }}>
                    <Text>年度</Text>
                    <Select
                      value={year}
                      style={{ width: 120 }}
                      onChange={(v) => { setYear(v); }}
                      options={(yearly.length ? yearly.map((y) => y.year) : [year]).map((y) => ({ value: y, label: `${y} 年` }))}
                    />
                    <Button size="small" onClick={() => load('monthly')}>套用</Button>
                  </Space>

                  <Card size="small" title="月營收 YoY 對照與成長率" style={{ marginBottom: 12 }}>
                    {monthlyChart.length === 0 ? <Empty description="該年度尚無 History 資料" /> : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <ComposedChart data={monthlyChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                          <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 10000)}萬`} />
                          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}%`} />
                          <RcTooltip formatter={(v: any, n: string) => [v === null ? EMPTY : (n === '成長率' ? `${v}%` : Number(v).toLocaleString('en-US')), n]} />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <ReferenceLine yAxisId="right" y={0} stroke={GREY} />
                          <Bar yAxisId="left" dataKey="本年營收" fill={BRAND} barSize={20} />
                          <Bar yAxisId="left" dataKey="去年營收" fill={GREY} barSize={20} />
                          <Line yAxisId="right" type="monotone" dataKey="成長率" stroke={RED} strokeWidth={2} dot={{ r: 3 }} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                  </Card>

                  <Card size="small" title="月彙總">
                    <Table
                      rowKey={(r) => `${r.year}-${r.month}`}
                      size="small"
                      dataSource={monthly?.months || []}
                      pagination={false}
                      scroll={{ x: 1100 }}
                      columns={[
                        { title: '月份', dataIndex: 'label', width: 70, fixed: 'left' },
                        {
                          title: '期間狀態',
                          dataIndex: 'period_label',
                          width: 200,
                          render: (v: string, r) => <Tag color={periodTagColor(r.period_type)}>{v}</Tag>,
                        },
                        { title: '本期營收', align: 'right', render: (_, r) => `$${fmtMoney(r.current.revenue)}` },
                        { title: '去年同期', align: 'right', render: (_, r) => (r.has_compare ? `$${fmtMoney(r.compare.revenue)}` : EMPTY) },
                        {
                          title: '營收 YoY',
                          align: 'right',
                          render: (_, r) => <Text style={{ color: trendColor(r.revenue_yoy) }}>{fmtYoY(r.revenue_yoy)}</Text>,
                        },
                        { title: 'ADR', align: 'right', render: (_, r) => `$${fmtMoney(r.current.adr)}` },
                        {
                          title: 'ADR YoY',
                          align: 'right',
                          render: (_, r) => <Text style={{ color: trendColor(r.adr_yoy) }}>{fmtYoY(r.adr_yoy)}</Text>,
                        },
                        { title: '住房率', align: 'right', render: (_, r) => fmtPct(r.current.occupancy) },
                        {
                          title: '住房率差異',
                          align: 'right',
                          render: (_, r) => (r.has_compare
                            ? <Text style={{ color: trendColor(r.occupancy_ppt) }}>{fmtPpt(r.occupancy_ppt)}</Text>
                            : EMPTY),
                        },
                        { title: 'RevPAR', align: 'right', render: (_, r) => `$${fmtMoney(r.current.revpar)}` },
                      ]}
                    />
                  </Card>
                </>
              ),
            },

            // ── 每年 ─────────────────────────────────────────────────────
            {
              key: 'yearly',
              label: '每年',
              children: (
                <>
                  <Card size="small" title="年度營收對比" style={{ marginBottom: 12 }}>
                    {yearlyChart.length === 0 ? <Empty description="尚無 History 資料" /> : (
                      <ResponsiveContainer width="100%" height={Math.max(200, yearlyChart.length * 60)}>
                        <BarChart data={yearlyChart} layout="vertical" margin={{ top: 10, right: 40, left: 20, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#eee" />
                          <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 10000)}萬`} />
                          <YAxis type="category" dataKey="label" tick={{ fontSize: 12 }} width={110} />
                          <RcTooltip formatter={(v: any) => Number(v).toLocaleString('en-US')} />
                          <Bar dataKey="營收" fill={BRAND} barSize={26} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                  </Card>

                  <Card size="small" title="年彙總">
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginBottom: 12 }}
                      message="只有雙方都是「完整年度」才可直接比較"
                      description="部分年度（資料未涵蓋全年）的營收、ADR、住房率只代表已有資料的期間，直接與完整年度相比會失真。表格的「可直接比較」欄已標示。"
                    />
                    <Table
                      rowKey="year"
                      size="small"
                      dataSource={yearly}
                      pagination={false}
                      scroll={{ x: 1000 }}
                      columns={[
                        { title: '年度', dataIndex: 'year', width: 80, fixed: 'left' },
                        {
                          title: '期間狀態',
                          dataIndex: 'period_label',
                          width: 230,
                          render: (v: string, r) => <Tag color={periodTagColor(r.period_type)}>{v}</Tag>,
                        },
                        { title: '資料天數', align: 'right', render: (_, r) => `${r.data_days} / ${r.expected_days}` },
                        { title: '房間營收', dataIndex: 'revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '已售房晚', dataIndex: 'sold_rooms', align: 'right', render: fmtInt },
                        { title: '可售房晚', dataIndex: 'available_rooms', align: 'right', render: fmtInt },
                        { title: 'ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '住房率', dataIndex: 'occupancy', align: 'right', render: (v: number) => fmtPct(v) },
                        { title: 'RevPAR', dataIndex: 'revpar', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: '營收 YoY',
                          align: 'right',
                          render: (_, r) => <Text style={{ color: trendColor(r.revenue_yoy) }}>{fmtYoY(r.revenue_yoy)}</Text>,
                        },
                        {
                          title: '可直接比較',
                          align: 'center',
                          render: (_, r) => (r.comparable
                            ? <Tag color="green">是</Tag>
                            : <Tooltip title="其中一方不是完整年度"><Tag color="orange">否</Tag></Tooltip>),
                        },
                      ]}
                    />
                  </Card>
                </>
              ),
            },

            // ── 四象限 ───────────────────────────────────────────────────
            {
              key: 'quadrant',
              label: '四象限',
              children: (
                <Card
                  size="small"
                  title={
                    <Space>
                      ADR × 住房率四象限
                      <Tooltip title="每個點代表一天；點的大小代表當日營收。兩條參考線為基準 ADR 與基準住房率。">
                        <InfoCircleOutlined style={{ color: ACCENT }} />
                      </Tooltip>
                    </Space>
                  }
                  extra={
                    <Radio.Group
                      size="small"
                      value={quadrantBasis}
                      onChange={(e) => { setQuadrantBasis(e.target.value); }}
                      onBlur={() => load('quadrant')}
                    >
                      <Radio.Button value="common">共同基準</Radio.Button>
                      <Radio.Button value="annual">年度自有基準</Radio.Button>
                    </Radio.Group>
                  }
                >
                  <Space style={{ marginBottom: 8 }} wrap>
                    <Button size="small" type="primary" onClick={() => load('quadrant')}>套用基準</Button>
                    {quadrant && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {`目前基準：${quadrant.basis_label}　基準 ADR $${fmtMoney(quadrant.baseline.adr)}　基準住房率 ${fmtPct(quadrant.baseline.occupancy)}`}
                      </Text>
                    )}
                  </Space>

                  {!quadrant || quadrant.points.length === 0 ? <Empty description="期間內無 History 資料" /> : (
                    <>
                      <ResponsiveContainer width="100%" height={380}>
                        <ScatterChart margin={{ top: 20, right: 30, left: 10, bottom: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                          <XAxis
                            type="number" dataKey="x" name="住房率" unit="%" domain={[0, 100]}
                            tick={{ fontSize: 11 }}
                            label={{ value: '住房率 (%)', position: 'insideBottom', offset: -10, fontSize: 12 }}
                          />
                          <YAxis
                            type="number" dataKey="y" name="ADR"
                            tick={{ fontSize: 11 }}
                            tickFormatter={(v: number) => v.toLocaleString('en-US')}
                            label={{ value: 'ADR', angle: -90, position: 'insideLeft', fontSize: 12 }}
                          />
                          <ZAxis type="number" dataKey="z" range={[20, 200]} name="營收" />
                          <RcTooltip
                            cursor={{ strokeDasharray: '3 3' }}
                            content={({ payload }: any) => {
                              if (!payload || !payload.length) return null
                              const p = payload[0].payload
                              return (
                                <div style={{ background: '#fff', border: '1px solid #ddd', padding: 8, fontSize: 12 }}>
                                  <div><b>{p.business_date}</b></div>
                                  <div>{`住房率 ${p.x}%　ADR $${fmtMoney(p.y)}`}</div>
                                  <div>{`營收 $${fmtMoney(p.revenue)}　已售 ${fmtInt(p.sold_rooms)}`}</div>
                                  <div>{`象限：${p.quadrant} ${p.quadrant_label}`}</div>
                                </div>
                              )
                            }}
                          />
                          <ReferenceLine
                            x={Number((quadrant.baseline.occupancy * 100).toFixed(1))}
                            stroke={RED} strokeDasharray="5 4"
                          />
                          <ReferenceLine y={quadrant.baseline.adr} stroke={RED} strokeDasharray="5 4" />
                          <Scatter data={quadrantSeries} fillOpacity={0.65}>
                            {quadrantSeries.map((p, i) => (
                              <Cell key={i} fill={QUADRANT_COLORS[p.quadrant]} />
                            ))}
                          </Scatter>
                        </ScatterChart>
                      </ResponsiveContainer>

                      <Row gutter={[8, 8]} style={{ marginTop: 12 }}>
                        {[
                          { q: 'Q1', label: '高 ADR 高住房（理想）' },
                          { q: 'Q2', label: '低 ADR 高住房（可提價）' },
                          { q: 'Q3', label: '低 ADR 低住房（需檢討）' },
                          { q: 'Q4', label: '高 ADR 低住房（可促銷）' },
                        ].map((item) => (
                          <Col xs={12} md={6} key={item.q}>
                            <Card size="small" bodyStyle={{ padding: '8px 12px' }} style={{ borderLeft: `3px solid ${QUADRANT_COLORS[item.q]}` }}>
                              <Text style={{ fontSize: 12 }}>{item.label}</Text>
                              <div><Text strong style={{ fontSize: 18 }}>{fmtInt(quadrant.counts[item.q] || 0)}</Text> 天</div>
                            </Card>
                          </Col>
                        ))}
                      </Row>
                      <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                    </>
                  )}
                </Card>
              ),
            },

            // ── 營收異常 ──────────────────────────────────────────────────
            {
              key: 'anomalies',
              label: (
                <span>
                  營收異常
                  {anomalies && anomalies.total > 0 && <Tag color="red" style={{ marginLeft: 6 }}>{anomalies.total}</Tag>}
                </span>
              ),
              children: (
                <>
                  <Card size="small" title="異常天數（依月份與觸發來源）" style={{ marginBottom: 12 }}>
                    {!anomalies || anomalies.monthly_series.length === 0 ? <Empty description="期間內無營收異常" /> : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <BarChart data={anomalies.monthly_series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                          <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                          <RcTooltip />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Bar dataKey="固定門檻" stackId="a" fill={ACCENT} />
                          <Bar dataKey="年度基準" stackId="a" fill={ORANGE} />
                          <Bar dataKey="兩者" stackId="a" fill={RED} />
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                  </Card>

                  <Card size="small" title="異常明細">
                    <Table
                      rowKey="business_date"
                      size="small"
                      dataSource={anomalies?.items || []}
                      scroll={{ x: 1100 }}
                      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 天` }}
                      columns={[
                        { title: '營業日', dataIndex: 'business_date', width: 110, fixed: 'left' },
                        {
                          title: '觸發來源',
                          dataIndex: 'trigger_source',
                          width: 100,
                          render: (v: string) => <Tag color={TRIGGER_TAG[v] || 'default'}>{v}</Tag>,
                          filters: [
                            { text: '固定門檻', value: '固定門檻' },
                            { text: '年度基準', value: '年度基準' },
                            { text: '兩者', value: '兩者' },
                          ],
                          onFilter: (val, r) => r.trigger_source === val,
                        },
                        {
                          title: '異常原因',
                          dataIndex: 'reasons',
                          render: (v: string[]) => (
                            <Space size={4} wrap>
                              {v.map((r) => <Tag key={r} color="orange">{r}</Tag>)}
                            </Space>
                          ),
                        },
                        { title: '房間營收', dataIndex: 'revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '已售/可售', align: 'right', render: (_, r) => `${fmtInt(r.sold_rooms)} / ${fmtInt(r.available_rooms)}` },
                        { title: 'ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '住房率', dataIndex: 'occupancy', align: 'right', render: (v: number) => fmtPct(v) },
                        {
                          title: '與年度基準差',
                          dataIndex: 'occupancy_diff',
                          align: 'right',
                          render: (v: number) => <Text style={{ color: trendColor(v) }}>{fmtPpt(v)}</Text>,
                        },
                      ]}
                    />
                  </Card>
                </>
              ),
            },
          ]}
        />

        <RevenueDayDetailDrawer
          open={drawerOpen}
          row={drawerRow}
          onClose={() => setDrawerOpen(false)}
        />
      </div>
    </Spin>
  )
}

export default OperaRevenuePage
