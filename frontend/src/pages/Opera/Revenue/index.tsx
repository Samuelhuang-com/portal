/**
 * 營收分析（/opera/revenue）
 * 規格書：docs/SPEC_opera_analytics.md §11.3、圖表 C4 / C5 / C6 / C7 / C8
 *
 * TAB：每日 / 每月 / 每年 / 四象限 / 營收異常
 * 資料來源一律為 History and Forecast（決策 D7）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col,  Descriptions, Empty, Modal, Radio, Row, Select, Space,
  Spin, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  InfoCircleOutlined, QuestionCircleOutlined, ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip as RcTooltip, XAxis, YAxis, ZAxis, Cell,
} from 'recharts'

import {
  fetchAnomalies, fetchOooLoss, fetchOperations, fetchOpportunity, fetchQuadrant,
  fetchRevenueDaily, fetchRevenueDayDetail, fetchRevenueMonthly, fetchRevenueYearly,
  fetchTrend, fetchWeekdayPerformance,
} from '@/api/opera'
import type {
  AnomalyResult, OooLossResult, OperationsResult, OpportunityResult, QuadrantBasis,
  QuadrantResult, RevenueDailyRow, RevenueMonthlyResult, RevenueYearRow, TrendResult,
  WeekdayPerformanceResult,
} from '@/types/opera'
import BackToTop from '../components/BackToTop'
import StandardRangePicker from '@/components/StandardRangePicker'
import RevenueDayDetailDrawer from '../components/RevenueDayDetailDrawer'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED, TRIGGER_TAG,
  fmtInt, fmtMoney, fmtPct, fmtPpt, fmtYoY, periodTagColor, trendColor,
} from '../components/formatters'

const { Title, Text } = Typography

const CHART_HEIGHT = 320
const SOURCE_NOTE = '資料來源：History and Forecast'
/** 標題旁「?」的說明內容（原本是頁面頂端的固定 Alert，內容未變） */
const SOURCE_HEADLINE = `${SOURCE_NOTE}　｜　可售房晚 = 實體房數 − OOO（CF_CALC_INV_ROOMS）`
const SOURCE_DETAIL = 'ADR／住房率／RevPAR 一律用加總後的加權公式計算，不是每日數值的平均。'

const QUADRANT_COLORS: Record<string, string> = {
  Q1: GREEN, Q2: ACCENT, Q3: GREY, Q4: ORANGE,
}

const OperaRevenuePage: React.FC = () => {
  const [tab, setTab] = useState('daily')
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  // 快捷區間的錨點 = History 的資料最後一天（不用今天，OPERA 匯出會落後）
  const [dataEnd, setDataEnd] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)

  const [daily, setDaily] = useState<RevenueDailyRow[]>([])
  const [monthly, setMonthly] = useState<RevenueMonthlyResult | null>(null)
  const [yearly, setYearly] = useState<RevenueYearRow[]>([])
  const [quadrant, setQuadrant] = useState<QuadrantResult | null>(null)
  const [anomalies, setAnomalies] = useState<AnomalyResult | null>(null)
  const [opportunity, setOpportunity] = useState<OpportunityResult | null>(null)
  const [weekday, setWeekday] = useState<WeekdayPerformanceResult | null>(null)
  const [oooLoss, setOooLoss] = useState<OooLossResult | null>(null)
  const [trend, setTrend] = useState<TrendResult | null>(null)
  const [operations, setOperations] = useState<OperationsResult | null>(null)

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
        if (!dataEnd) setDataEnd(res.end)
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
      } else if (which === 'opportunity') {
        setOpportunity(await fetchOpportunity(rangeParams))
      } else if (which === 'weekday') {
        setWeekday(await fetchWeekdayPerformance(rangeParams))
      } else if (which === 'ooo') {
        setOooLoss(await fetchOooLoss(rangeParams))
      } else if (which === 'trend') {
        setTrend(await fetchTrend(rangeParams))
      } else if (which === 'operations') {
        setOperations(await fetchOperations(rangeParams))
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
            <Space size={6} align="center">
              <Title level={4} style={{ margin: 0, color: BRAND }}>營收分析</Title>
              <Tooltip title="資料來源說明">
                <Button
                  type="text" size="small" aria-label="資料來源說明"
                  icon={<QuestionCircleOutlined style={{ color: ACCENT, fontSize: 16 }} />}
                  onClick={() => setHelpOpen(true)}
                />
              </Tooltip>
            </Space>
          </Col>
          <Col>
            <Space wrap>
              <StandardRangePicker value={range} anchor={dataEnd} onChange={setRange} />
              <Button icon={<ReloadOutlined />} onClick={() => load(tab)}>重新整理</Button>
            </Space>
          </Col>
        </Row>

        <Modal
          open={helpOpen}
          onCancel={() => setHelpOpen(false)}
          footer={null}
          width={520}
          title={
            <Space size={8}>
              <InfoCircleOutlined style={{ color: ACCENT }} />
              <span>資料來源說明</span>
            </Space>
          }
        >
          <div style={{ lineHeight: 1.8 }}>
            <div>{SOURCE_HEADLINE}</div>
            <Text type="secondary">{SOURCE_DETAIL}</Text>
          </div>
        </Modal>

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

            // ── 星期營收績效 ──────────────────────────────────────────────
            {
              key: 'weekday',
              label: '星期績效',
              children: (
                <>
                  {weekday?.thin_data && (
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginBottom: 12 }}
                      message={`資料期間偏短（最少的星期別只有 ${weekday.min_days} 天）`}
                      description="某些星期出現次數少時，平均值容易被單一活動日扭曲，建議拉長期間再判讀。"
                    />
                  )}
                  <Card size="small" title="星期別加權績效" style={{ marginBottom: 12 }}>
                    {!weekday || weekday.weekdays.every((w) => w.days === 0) ? (
                      <Empty description="期間內無 History 資料" />
                    ) : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <ComposedChart data={weekday.weekdays} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                          <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 10000)}萬`} />
                          <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}%`} />
                          <RcTooltip
                            formatter={(v: any, n: string) =>
                              [n === '住房率' ? `${v}%` : Number(v).toLocaleString('en-US'), n]}
                          />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <ReferenceLine
                            yAxisId="right"
                            y={Number((weekday.baseline.occupancy * 100).toFixed(1))}
                            stroke={RED}
                            strokeDasharray="5 4"
                            label={{ value: '整體住房率', position: 'right', fontSize: 11, fill: RED }}
                          />
                          <Bar yAxisId="left" dataKey="revenue" name="總營收" fill={BRAND} barSize={26} />
                          <Line
                            yAxisId="right"
                            type="monotone"
                            dataKey={(d: any) => Number((d.occupancy * 100).toFixed(1))}
                            name="住房率"
                            stroke={ORANGE}
                            strokeWidth={2}
                            dot={{ r: 4 }}
                          />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                  </Card>

                  <Card size="small" title="星期別明細（與整體基準的差距）">
                    <Table
                      rowKey="weekday"
                      size="small"
                      dataSource={weekday?.weekdays || []}
                      pagination={false}
                      scroll={{ x: 1000 }}
                      columns={[
                        { title: '星期', dataIndex: 'label', width: 80, fixed: 'left' },
                        { title: '天數', dataIndex: 'days', align: 'right', width: 70, render: fmtInt },
                        { title: '總營收', dataIndex: 'revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '平均每日營收', dataIndex: 'avg_daily_revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '已售房晚', dataIndex: 'sold_rooms', align: 'right', render: fmtInt },
                        { title: 'ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: 'ADR vs 整體', dataIndex: 'adr_vs_overall', align: 'right',
                          // 負號要自己補：fmtMoney 吃的是絕對值，直接用 v >= 0 判斷會把負號吃掉
                          render: (v: number) => {
                            const rounded = Math.round(v)
                            const sign = rounded > 0 ? '+' : rounded < 0 ? '−' : ''
                            return (
                              <Text style={{ color: trendColor(v) }}>
                                {`${sign}$${fmtMoney(Math.abs(v))}`}
                              </Text>
                            )
                          },
                        },
                        { title: '住房率', dataIndex: 'occupancy', align: 'right', render: (v: number) => fmtPct(v) },
                        {
                          title: '住房率 vs 整體', dataIndex: 'occupancy_vs_overall', align: 'right',
                          render: (v: number) => <Text style={{ color: trendColor(v) }}>{fmtPpt(v)}</Text>,
                        },
                        { title: 'RevPAR', dataIndex: 'revpar', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                      ]}
                    />
                    <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                      高住房率、低 ADR 的星期優先檢查提前提價、折扣與通路庫存；
                      低住房率、低 ADR 的星期要先處理需求，只降價未必能創造需求。
                    </Text>
                  </Card>
                </>
              ),
            },

            // ── 趨勢：MoM 與移動平均 ──────────────────────────────────────
            {
              key: 'trend',
              label: '趨勢',
              children: (
                <>
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="移動平均已多取 27 天暖身資料計算"
                    description={
                      trend
                        ? `暖身起日 ${trend.warmup_start}。少了這步，期間開頭的移動平均會被低估。`
                          + `月中未完整的月份 MoM 會偏低，表格已標示。`
                        : ''
                    }
                  />

                  <Card size="small" title="每日營收與 7／28 日移動平均" style={{ marginBottom: 12 }}>
                    {!trend || trend.daily.length === 0 ? <Empty description="期間內無 History 資料" /> : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <ComposedChart data={trend.daily} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis
                            dataKey="business_date"
                            tick={{ fontSize: 10 }}
                            tickFormatter={(v: string) => v.slice(5)}
                            interval="preserveStartEnd"
                            minTickGap={30}
                          />
                          <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
                          <RcTooltip formatter={(v: any, n: string) => [`$${Number(v).toLocaleString('en-US')}`, n]} />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Bar dataKey="revenue" name="每日營收" fill="#dbe4ee" />
                          <Line type="monotone" dataKey="ma7" name="7 日移動平均" stroke={ORANGE} strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="ma28" name="28 日移動平均" stroke={BRAND} strokeWidth={2} dot={false} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      7 日線持續高於 28 日線通常表示近期動能改善；反之可能正在轉弱。　{SOURCE_NOTE}
                    </Text>
                  </Card>

                  <Card size="small" title="月增率（MoM）">
                    <Table
                      rowKey="month"
                      size="small"
                      dataSource={trend?.monthly || []}
                      pagination={false}
                      scroll={{ x: 1000 }}
                      columns={[
                        {
                          title: '月份', dataIndex: 'label', width: 110, fixed: 'left',
                          render: (v: string, r) => (
                            r.is_partial
                              ? <Tooltip title="該月資料未完整，MoM 會被低估"><span>{v} <Tag color="orange">未完整</Tag></span></Tooltip>
                              : v
                          ),
                        },
                        { title: '營收', dataIndex: 'revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: '營收 MoM', dataIndex: 'revenue_mom', align: 'right',
                          render: (v: number | null) => <Text style={{ color: trendColor(v) }}>{fmtYoY(v)}</Text>,
                        },
                        { title: 'ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: 'ADR MoM', dataIndex: 'adr_mom', align: 'right',
                          render: (v: number | null) => <Text style={{ color: trendColor(v) }}>{fmtYoY(v)}</Text>,
                        },
                        { title: '住房率', dataIndex: 'occupancy', align: 'right', render: (v: number) => fmtPct(v) },
                        {
                          title: '住房率 MoM', dataIndex: 'occupancy_mom_ppt', align: 'right',
                          render: (v: number | null) => <Text style={{ color: trendColor(v) }}>{v === null ? EMPTY : fmtPpt(v)}</Text>,
                        },
                        { title: 'RevPAR', dataIndex: 'revpar', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: 'RevPAR MoM', dataIndex: 'revpar_mom', align: 'right',
                          render: (v: number | null) => <Text style={{ color: trendColor(v) }}>{fmtYoY(v)}</Text>,
                        },
                      ]}
                    />
                    <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                      MoM 要同時拆解房晚與 ADR，才能判斷成長來自量還是價。
                      跨年度、春節或大型活動期間應搭配去年同期與預算一起看。
                    </Text>
                  </Card>
                </>
              ),
            },

            // ── 營運指標（每房人數／翻房率／非營收房）──────────────────────
            // 這些欄位 OPERA 一直都有給（NO_PERSONS、ARRIVAL_ROOMS、DEPARTURE_ROOMS、
            // COMPLIMENTARY／HOUSE_USE／DAY_USE／NO_SHOW_ROOMS），先前完全沒拿來分析。
            {
              key: 'operations',
              label: '營運指標',
              children: (
                <>
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="這一頁是給房務、餐飲備量與人力規劃用的"
                    description={operations?.note || ''}
                  />

                  {operations && (
                    <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                      {[
                        {
                          title: '每房人數', value: `${operations.persons_per_room.toFixed(2)} 人`,
                          hint: `${fmtInt(operations.persons)} 人 ÷ ${fmtInt(operations.sold_rooms)} 房晚`,
                          color: BRAND,
                        },
                        {
                          title: '翻房率', value: fmtPct(operations.turnover_rate),
                          hint: `到店 ${fmtInt(operations.arrival_rooms)} ÷ 已售 ${fmtInt(operations.sold_rooms)}`,
                          color: ORANGE,
                        },
                        {
                          title: '每日平均進出', value: `${operations.avg_daily_turnover} 房次`,
                          hint: `到店 ${operations.avg_daily_arrival} + 離店 ${operations.avg_daily_departure}（實體房 ${operations.avg_inventory}）`,
                          color: ACCENT,
                        },
                        {
                          title: '續住房晚', value: fmtInt(operations.stayover_rooms),
                          hint: '已售 − 到店，不需重新整理的房',
                          color: GREEN,
                        },
                      ].map((it) => (
                        <Col xs={12} lg={6} key={it.title}>
                          <Card size="small" bodyStyle={{ padding: '12px 16px' }} style={{ borderLeft: `3px solid ${it.color}` }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>{it.title}</Text>
                            <div><Text strong style={{ fontSize: 20, color: it.color }}>{it.value}</Text></div>
                            <Text type="secondary" style={{ fontSize: 11 }}>{it.hint}</Text>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  )}

                  <Card size="small" title="每日進出量與每房人數" style={{ marginBottom: 12 }}>
                    {!operations || operations.daily.length === 0 ? <Empty description="期間內無 History 資料" /> : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <ComposedChart data={operations.daily} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis
                            dataKey="business_date"
                            tick={{ fontSize: 10 }}
                            tickFormatter={(v: string) => v.slice(5)}
                            interval="preserveStartEnd"
                            minTickGap={30}
                          />
                          <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
                          <YAxis yAxisId="right" orientation="right" domain={[0, 4]} tick={{ fontSize: 11 }} />
                          <RcTooltip formatter={(v: any, n: string) => [Number(v).toLocaleString('en-US'), n]} />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Bar yAxisId="left" dataKey="arrival_rooms" name="到店房數" stackId="t" fill={GREEN} />
                          <Bar yAxisId="left" dataKey="departure_rooms" name="離店房數" stackId="t" fill={ORANGE} />
                          <Line yAxisId="right" type="monotone" dataKey="persons_per_room" name="每房人數" stroke={BRAND} strokeWidth={2} dot={false} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      堆疊高度即當日房務工作量（到店備房 + 離店清掃）。　{SOURCE_NOTE}
                    </Text>
                  </Card>

                  <Card size="small" title="非營收房監控">
                    {!operations ? <Empty /> : (
                      <>
                        <Descriptions size="small" column={{ xs: 2, md: 5 }} bordered>
                          <Descriptions.Item label="招待房">{fmtInt(operations.non_revenue.complimentary)}</Descriptions.Item>
                          <Descriptions.Item label="自用房">{fmtInt(operations.non_revenue.house_use)}</Descriptions.Item>
                          <Descriptions.Item label="日用房">{fmtInt(operations.non_revenue.day_use)}</Descriptions.Item>
                          <Descriptions.Item label="No-show">{fmtInt(operations.non_revenue.no_show)}</Descriptions.Item>
                          <Descriptions.Item label="合計">
                            <Text strong>{fmtInt(operations.non_revenue.total)}</Text>
                            <Text type="secondary" style={{ fontSize: 12, marginLeft: 6 }}>
                              {`（占已售 ${fmtPct(operations.non_revenue.share_of_sold, 2)}）`}
                            </Text>
                          </Descriptions.Item>
                        </Descriptions>
                        <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                          這幾項目前量都很小，屬於<Text strong>趨勢監控型</Text>指標——數字突然放大時才需要追查
                          （招待房浮濫、Day Use 未入帳、No-show 政策未落實等）。
                        </Text>
                      </>
                    )}
                  </Card>
                </>
              ),
            },

            // ── OOO 營收損失 ──────────────────────────────────────────────
            {
              key: 'ooo',
              label: (
                <span>
                  OOO 損失
                  {oooLoss && oooLoss.total_days > 0 && (
                    <Tag color="orange" style={{ marginLeft: 6 }}>{oooLoss.total_days}</Tag>
                  )}
                </span>
              ),
              children: (
                <>
                  <Alert
                    type="warning"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="估算採用當日 ADR，假設 OOO 房可以同價售出"
                    description={oooLoss?.disclaimer || ''}
                  />

                  {oooLoss && (
                    <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                      {[
                        { title: '有 OOO 的天數', value: `${fmtInt(oooLoss.total_days)} 天`, color: BRAND },
                        { title: 'OOO 房晚', value: fmtInt(oooLoss.total_ooo_rooms), color: ORANGE },
                        { title: '估算損失', value: `$${fmtMoney(oooLoss.total_est_loss)}`, color: RED },
                        { title: '占期間營收', value: fmtPct(oooLoss.loss_share, 2), color: ACCENT },
                      ].map((it) => (
                        <Col xs={12} lg={6} key={it.title}>
                          <Card size="small" bodyStyle={{ padding: '12px 16px' }} style={{ borderLeft: `3px solid ${it.color}` }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>{it.title}</Text>
                            <div><Text strong style={{ fontSize: 20, color: it.color }}>{it.value}</Text></div>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  )}

                  {oooLoss && (
                    <Card size="small" title="兩種分母的 RevPAR 比較" style={{ marginBottom: 12 }}>
                      <Descriptions size="small" column={{ xs: 1, md: 3 }} bordered>
                        <Descriptions.Item label="淨可售房 RevPAR">
                          <Text strong>{`$${fmtMoney(oooLoss.net_revpar)}`}</Text>
                          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                            {`營收 ÷ 可售房晚 ${fmtInt(oooLoss.sum_available_rooms)}`}
                          </Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="實體房 RevPAR">
                          <Text strong>{`$${fmtMoney(oooLoss.physical_revpar)}`}</Text>
                          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                            {`營收 ÷ 實體房晚 ${fmtInt(oooLoss.sum_inventory_rooms)}`}
                          </Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="分母效果">
                          <Text strong style={{ color: ORANGE }}>{`$${fmtMoney(oooLoss.denominator_effect)}`}</Text>
                        </Descriptions.Item>
                      </Descriptions>
                      <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                        OOO 多時「可售房晚」分母變小，報表住房率與 RevPAR 會看起來較好；
                        「實體房 RevPAR」才反映完整資產產能。兩者差距就是分母效果。
                      </Text>
                    </Card>
                  )}

                  <Card size="small" title="OOO 損失月分布" style={{ marginBottom: 12 }}>
                    {!oooLoss || oooLoss.monthly_series.length === 0 ? (
                      <Empty description="期間內沒有 OOO 房晚" />
                    ) : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <ComposedChart data={oooLoss.monthly_series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                          <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
                          <YAxis yAxisId="right" orientation="right" allowDecimals={false} tick={{ fontSize: 11 }} />
                          <RcTooltip
                            formatter={(v: any, n: string) =>
                              [n === '估算損失' ? `$${Number(v).toLocaleString('en-US')}` : `${v} 房晚`, n]}
                          />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Bar yAxisId="left" dataKey="est_loss" name="估算損失" fill={RED} />
                          <Line yAxisId="right" type="monotone" dataKey="ooo_rooms" name="OOO 房晚" stroke={BRAND} strokeWidth={2} dot={{ r: 3 }} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                  </Card>

                  <Card size="small" title="OOO 明細（依估算損失排序）">
                    <Table
                      rowKey="business_date"
                      size="small"
                      dataSource={oooLoss?.items || []}
                      scroll={{ x: 1000 }}
                      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 天` }}
                      columns={[
                        { title: '營業日', dataIndex: 'business_date', width: 110, fixed: 'left' },
                        {
                          title: 'OOO 房晚', dataIndex: 'ooo_rooms', align: 'right',
                          render: (v: number) => <Text strong style={{ color: ORANGE }}>{fmtInt(v)}</Text>,
                          sorter: (a, b) => a.ooo_rooms - b.ooo_rooms,
                        },
                        { title: '當日 ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: '估算損失', dataIndex: 'est_loss', align: 'right', width: 130,
                          render: (v: number, r) => (
                            <Tooltip title={`${fmtInt(r.ooo_rooms)} 房晚 × $${fmtMoney(r.adr)}`}>
                              <Text strong style={{ color: RED }}>{`$${fmtMoney(v)}`}</Text>
                            </Tooltip>
                          ),
                          sorter: (a, b) => a.est_loss - b.est_loss,
                          defaultSortOrder: 'descend',
                        },
                        { title: '住房率', dataIndex: 'occupancy', align: 'right', render: (v: number) => fmtPct(v) },
                        { title: '淨可售房 RevPAR', dataIndex: 'net_revpar', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '實體房 RevPAR', dataIndex: 'physical_revpar', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: '分母效果', dataIndex: 'denominator_effect', align: 'right',
                          render: (v: number) => <Text style={{ color: ORANGE }}>{`$${fmtMoney(v)}`}</Text>,
                        },
                      ]}
                    />
                    <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                      優先處理高 ADR 日期的 OOO，因為每一間不可售房的潛在收入較高；
                      把損失按月份彙總可協助維修排程避開高需求日。
                    </Text>
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

            // ── 高住房率低 ADR 機會 ───────────────────────────────────────
            {
              key: 'opportunity',
              label: (
                <span>
                  提價機會
                  {opportunity && opportunity.total_days > 0 && (
                    <Tag color="gold" style={{ marginLeft: 6 }}>{opportunity.total_days}</Tag>
                  )}
                </span>
              ),
              children: (
                <>
                  <Alert
                    type="warning"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="估算提升金額是「情境值」，不是可保證的收入，也不是會計損失"
                    description={
                      opportunity
                        ? `假設這些日子的同樣房晚可以用期間加權 ADR $${fmtMoney(opportunity.baseline_adr)} 售出。`
                          + `實務上提價可能影響需求，實際可實現金額通常低於估算值。門檻可在「分析門檻設定」調整。`
                        : ''
                    }
                  />

                  {opportunity && (
                    <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                      {[
                        { title: '機會日數', value: `${fmtInt(opportunity.total_days)} 天`, color: BRAND },
                        { title: '估算提升金額', value: `$${fmtMoney(opportunity.total_uplift)}`, color: ORANGE },
                        { title: '占期間營收', value: fmtPct(opportunity.uplift_share, 2), color: ACCENT },
                        { title: '基準 ADR', value: `$${fmtMoney(opportunity.baseline_adr)}`, color: GREEN },
                      ].map((it) => (
                        <Col xs={12} lg={6} key={it.title}>
                          <Card size="small" bodyStyle={{ padding: '12px 16px' }} style={{ borderLeft: `3px solid ${it.color}` }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>{it.title}</Text>
                            <div><Text strong style={{ fontSize: 20, color: it.color }}>{it.value}</Text></div>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  )}

                  <Card
                    size="small"
                    title={`機會日分布（住房率 ≥ ${opportunity ? (opportunity.threshold * 100).toFixed(0) : 90}% 且 ADR 低於基準）`}
                    style={{ marginBottom: 12 }}
                  >
                    {!opportunity || opportunity.monthly_series.length === 0 ? (
                      <Empty description="期間內沒有符合條件的機會日" />
                    ) : (
                      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                        <ComposedChart data={opportunity.monthly_series} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                          <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} />
                          <YAxis yAxisId="right" orientation="right" allowDecimals={false} tick={{ fontSize: 11 }} />
                          <RcTooltip
                            formatter={(v: any, n: string) =>
                              [n === '估算提升' ? `$${Number(v).toLocaleString('en-US')}` : `${v} 天`, n]}
                          />
                          <Legend wrapperStyle={{ fontSize: 12 }} />
                          <Bar yAxisId="left" dataKey="uplift" name="估算提升" fill={ORANGE} />
                          <Line yAxisId="right" type="monotone" dataKey="days" name="機會日數" stroke={BRAND} strokeWidth={2} dot={{ r: 3 }} />
                        </ComposedChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>{SOURCE_NOTE}</Text>
                  </Card>

                  <Card size="small" title="機會日明細（依估算提升金額排序）">
                    <Table
                      rowKey="business_date"
                      size="small"
                      dataSource={opportunity?.items || []}
                      scroll={{ x: 900 }}
                      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 天` }}
                      columns={[
                        { title: '營業日', dataIndex: 'business_date', width: 110, fixed: 'left' },
                        {
                          title: '住房率', dataIndex: 'occupancy', align: 'right',
                          render: (v: number) => <Text strong style={{ color: GREEN }}>{fmtPct(v)}</Text>,
                          sorter: (a, b) => a.occupancy - b.occupancy,
                        },
                        { title: '已售房晚', dataIndex: 'sold_rooms', align: 'right', render: fmtInt },
                        { title: '當日 ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        { title: '基準 ADR', dataIndex: 'baseline_adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                        {
                          title: 'ADR 差距', dataIndex: 'adr_gap', align: 'right',
                          render: (v: number) => <Text style={{ color: RED }}>{`$${fmtMoney(v)}`}</Text>,
                          sorter: (a, b) => a.adr_gap - b.adr_gap,
                        },
                        {
                          title: '估算提升金額', dataIndex: 'est_uplift', align: 'right', width: 140,
                          render: (v: number, r) => (
                            <Tooltip title={`$${fmtMoney(r.adr_gap)} × ${fmtInt(r.sold_rooms)} 房晚`}>
                              <Text strong style={{ color: ORANGE }}>{`$${fmtMoney(v)}`}</Text>
                            </Tooltip>
                          ),
                          sorter: (a, b) => a.est_uplift - b.est_uplift,
                          defaultSortOrder: 'descend',
                        },
                        { title: '房間營收', dataIndex: 'revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                      ]}
                    />
                  </Card>
                </>
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

        <BackToTop />
      </div>
    </Spin>
  )
}

export default OperaRevenuePage
