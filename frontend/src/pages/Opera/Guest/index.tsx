/**
 * 住客與通路分析（/opera/guest）
 * 規格書：docs/SPEC_opera_analytics.md §11.4、§11.10、圖表 C9～C13
 *
 * TAB：住宿明細 / 通路 / 房型 / Rate Code / 公司 / 回訪與長住
 * 資料來源一律為 Departure All（決策 D7）。
 * 維度統計支援雙口徑切換（決策 D5）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Empty, Input, Radio, Row, Select,
  Space, Spin, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import { InfoCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LabelList,
  Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'

import {
  fetchDimensionStats, fetchGuestFilterOptions, fetchLongStay,
  fetchRepeatGuests, fetchStayDetail, fetchStays,
} from '@/api/opera'
import type { OperaDimension } from '@/api/opera'
import type {
  DimensionResult, LongStayResult, OperaBasis,
  RepeatGuestResult, StayRow,
} from '@/types/opera'
import StayDetailDrawer from '../components/StayDetailDrawer'
import {
  ACCENT, BRAND, CHART_COLORS, EMPTY, GREEN, ORANGE, RED,
  fmtInt, fmtPct,
} from '../components/formatters'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const SOURCE_NOTE = '資料來源：Departure All'
const CHART_HEIGHT = 300

const BASIS_TIP = (
  <div style={{ maxWidth: 320 }}>
    <b>以房數計</b>：只計 <code>NO_OF_ROOMS = 1</code> 的列，與 OPERA footer 的房數口徑一致。<br />
    <b>以訂單計</b>：計入全部列（含 <code>NO_OF_ROOMS = 0</code>）。<br />
    <br />
    實測有 36.6% 的列 <code>NO_OF_ROOMS = 0</code>，其語意（share／次要訂房？）尚待 OPERA 顧問確認，
    因此兩種口徑並存，避免預設其中一種造成誤讀。
  </div>
)

const OperaGuestPage: React.FC = () => {
  const [tab, setTab] = useState('stays')
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [basis, setBasis] = useState<OperaBasis>('room')
  const [loading, setLoading] = useState(false)

  // 住宿明細
  const [stays, setStays] = useState<StayRow[]>([])
  const [stayTotal, setStayTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [search, setSearch] = useState('')
  const [channelFilter, setChannelFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [options, setOptions] = useState<{ channel: string[]; room_category: string[]; rate_code: string[] }>({
    channel: [], room_category: [], rate_code: [],
  })

  // 維度
  const [dimData, setDimData] = useState<Record<string, DimensionResult | null>>({})
  const [repeat, setRepeat] = useState<RepeatGuestResult | null>(null)
  const [longStay, setLongStay] = useState<LongStayResult | null>(null)

  const [drawerStay, setDrawerStay] = useState<StayRow | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const rangeParams = useMemo(
    () => (range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
    [range],
  )

  // ── 初始化日期範圍與篩選選項 ────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const opt = await fetchGuestFilterOptions()
        setOptions({ channel: opt.channel, room_category: opt.room_category, rate_code: opt.rate_code })
        if (!range) setRange([dayjs(opt.start), dayjs(opt.end)])
      } catch {
        /* 靜默：主畫面仍可運作 */
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadStays = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchStays({
        ...rangeParams, basis, page, page_size: pageSize,
        search, channel: channelFilter, room_category: categoryFilter,
      })
      setStays(res.items)
      setStayTotal(res.total)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入住宿明細失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis, page, pageSize, search, channelFilter, categoryFilter])

  const loadDimension = useCallback(async (dim: OperaDimension, limit = 0) => {
    setLoading(true)
    try {
      const res = await fetchDimensionStats(dim, { ...rangeParams, basis, limit })
      setDimData((prev) => ({ ...prev, [dim]: res }))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入統計失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis])

  const loadGuestTab = useCallback(async () => {
    setLoading(true)
    try {
      const [rp, ls] = await Promise.all([
        fetchRepeatGuests({ ...rangeParams, basis }),
        fetchLongStay({ ...rangeParams, basis }),
      ])
      setRepeat(rp)
      setLongStay(ls)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入住客統計失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis])

  useEffect(() => {
    if (!range) return
    if (tab === 'stays') loadStays()
    else if (tab === 'channel') loadDimension('channel')
    else if (tab === 'room_category') loadDimension('room_category')
    else if (tab === 'rate_code') loadDimension('rate_code', 15)
    else if (tab === 'company') loadDimension('company', 20)
    else if (tab === 'guest') loadGuestTab()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, range, basis, page, pageSize, search, channelFilter, categoryFilter])

  const openStayDrawer = useCallback(async (row: StayRow) => {
    setDrawerStay(row)
    setDrawerOpen(true)
    try {
      setDrawerStay(await fetchStayDetail(row.id))
    } catch {
      /* 列表資料已足夠顯示 */
    }
  }, [])

  // ── 住宿明細欄位 ────────────────────────────────────────────────────────
  const stayColumns: ColumnsType<StayRow> = [
    { title: '退房日', dataIndex: 'departure_date', width: 110, fixed: 'left' },
    { title: '入住日', dataIndex: 'arrival_date', width: 110 },
    { title: '房號', dataIndex: 'room_no', width: 80 },
    {
      title: '房型', dataIndex: 'room_category_label', width: 80,
      render: (v: string) => (v ? <Tag color="cyan">{v}</Tag> : EMPTY),
    },
    { title: '晚數', dataIndex: 'nights', width: 70, align: 'right', render: fmtInt },
    { title: '房晚', dataIndex: 'room_nights', width: 70, align: 'right', render: (v: number) => <Text strong>{fmtInt(v)}</Text> },
    { title: '成人', dataIndex: 'adults', width: 60, align: 'right', render: fmtInt },
    // ⚠️ dataIndex 是 child_count 不是 children —— antd Table 會把 record.children
    //    當成子列陣列，數字值會讓整頁崩潰（見 types/opera.ts StayRow 說明）
    { title: '兒童', dataIndex: 'child_count', width: 60, align: 'right', render: fmtInt },
    {
      title: '通路', dataIndex: 'channel', width: 160,
      render: (v: string) => <Tag color={v === '直客／未標註' ? 'default' : 'blue'}>{v}</Tag>,
    },
    { title: 'Rate Code', dataIndex: 'rate_code', width: 120, render: (v: string) => v || EMPTY },
    { title: '付款', dataIndex: 'payment_desc', width: 80, render: (v: string) => v || EMPTY },
    {
      title: '住客（遮罩）', dataIndex: 'guest_name_masked', width: 180,
      render: (v: string, r) => (r.is_purged ? <Text type="secondary">{v}</Text> : v || EMPTY),
    },
  ]

  // ── C9：通路 Pareto ─────────────────────────────────────────────────────
  // 圖只畫前 PARETO_TOP_N 名（長尾通路的長條在畫面上只有 1~2 px，標籤反而會
  // 互相重疊到看不懂）；累計占比仍以「全部通路」為分母計算，所以 Pareto 的
  // 判讀不受影響。完整清單在下方表格。
  const PARETO_TOP_N = 15
  const truncateLabel = (s: string, max = 14) => (s.length > max ? `${s.slice(0, max)}…` : s)

  const renderPareto = (data: DimensionResult | null | undefined) => {
    if (!data || data.items.length === 0) return <Empty description="期間內無資料" />
    const shown = data.items.slice(0, PARETO_TOP_N)
    const chartData = shown.map((i) => ({
      key: i.key,
      值: data.metric === 'room_nights' ? i.room_nights : i.records,
      累計占比: Number((i.cumulative_share * 100).toFixed(1)),
    }))
    return (
      <>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 50, left: 0, bottom: 70 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
            <XAxis
              dataKey="key"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: string) => truncateLabel(v)}
              angle={-35}
              textAnchor="end"
              interval={0}
              height={90}
            />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}%`} />
            <RcTooltip
              formatter={(v: any, n: string) => [n === '累計占比' ? `${v}%` : Number(v).toLocaleString('en-US'), n === '值' ? data.metric_label : n]}
              labelFormatter={(l: string) => l}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <ReferenceLine yAxisId="right" y={80} stroke={RED} strokeDasharray="5 4" label={{ value: '80%', position: 'right', fontSize: 11, fill: RED }} />
            <Bar yAxisId="left" dataKey="值" name={data.metric_label} fill={BRAND} />
            <Line yAxisId="right" type="monotone" dataKey="累計占比" stroke={ORANGE} strokeWidth={2} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
        {data.items.length > PARETO_TOP_N && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {`圖表僅顯示前 ${PARETO_TOP_N} 名（共 ${data.items.length} 項），累計占比仍以全部項目為分母；完整清單見下方表格。`}
          </Text>
        )}
      </>
    )
  }

  const dimensionTable = (data: DimensionResult | null | undefined) => (
    <Table
      rowKey="key"
      size="small"
      dataSource={data?.items || []}
      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 項` }}
      columns={[
        { title: data?.dimension_label || '項目', dataIndex: 'key', width: 240 },
        { title: '訂房筆數', dataIndex: 'records', align: 'right', render: fmtInt, sorter: (a, b) => a.records - b.records },
        { title: '房晚', dataIndex: 'room_nights', align: 'right', render: fmtInt, sorter: (a, b) => a.room_nights - b.room_nights },
        { title: '住宿晚數', dataIndex: 'nights', align: 'right', render: fmtInt },
        { title: '成人', dataIndex: 'adults', align: 'right', render: fmtInt },
        { title: '占比', dataIndex: 'share', align: 'right', render: (v: number) => fmtPct(v) },
        { title: '累計占比', dataIndex: 'cumulative_share', align: 'right', render: (v: number) => fmtPct(v) },
      ]}
    />
  )

  // ── C10：房型圓餅 ───────────────────────────────────────────────────────
  const renderPie = (data: DimensionResult | null | undefined) => {
    if (!data || data.items.length === 0) return <Empty description="期間內無資料" />
    const pieData = data.items.map((i) => ({
      name: i.key,
      value: data.metric === 'room_nights' ? i.room_nights : i.records,
    }))
    return (
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <PieChart>
          {/* ⚠️ isAnimationActive={false} 是必要的，不是效能微調：App 跑在
              React.StrictMode 下，開發模式的雙重掛載會取消 recharts 的進場動畫，
              而 Pie 的 sector 只在動畫啟動後才產生 → 圓餅完全畫不出來（只剩標籤）。
              Bar／Line 不受影響。2026-08-04 實測確認。 */}
          <Pie
            data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
            outerRadius={100}
            isAnimationActive={false}
            label={(e: any) => (e.percent > 0.03 ? `${e.name} ${(e.percent * 100).toFixed(1)}%` : '')}
            labelLine={false}
          >
            {pieData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Pie>
          <RcTooltip formatter={(v: any) => Number(v).toLocaleString('en-US')} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  // ── C11：Rate Code 橫向長條 ─────────────────────────────────────────────
  const renderHorizontalBar = (data: DimensionResult | null | undefined) => {
    if (!data || data.items.length === 0) return <Empty description="期間內無資料" />
    const chartData = data.items.map((i) => ({
      key: i.key,
      值: data.metric === 'room_nights' ? i.room_nights : i.records,
    }))
    return (
      <ResponsiveContainer width="100%" height={Math.max(240, chartData.length * 28)}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 10, right: 60, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#eee" />
          <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
          <YAxis type="category" dataKey="key" tick={{ fontSize: 11 }} width={140} />
          <RcTooltip formatter={(v: any) => [Number(v).toLocaleString('en-US'), data.metric_label]} />
          <Bar dataKey="值" name={data.metric_label} fill={ACCENT} barSize={16}>
            <LabelList dataKey="值" position="right" formatter={(v: any) => Number(v).toLocaleString('en-US')} style={{ fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )
  }

  const basisControl = (
    <Space>
      <Text>統計口徑</Text>
      <Tooltip title={BASIS_TIP}>
        <InfoCircleOutlined style={{ color: ACCENT }} />
      </Tooltip>
      <Radio.Group size="small" value={basis} onChange={(e) => { setBasis(e.target.value); setPage(1) }}>
        <Radio.Button value="room">以房數計</Radio.Button>
        <Radio.Button value="reservation">以訂單計</Radio.Button>
      </Radio.Group>
    </Space>
  )

  return (
    <Spin spinning={loading}>
      <div style={{ padding: 24 }}>
        <Row justify="space-between" align="middle" style={{ marginBottom: 12 }}>
          <Col><Title level={4} style={{ margin: 0, color: BRAND }}>住客與通路分析</Title></Col>
          <Col>
            <Space wrap>
              {basisControl}
              <RangePicker value={range} onChange={(v) => setRange(v as [Dayjs, Dayjs] | null)} allowClear={false} />
              <Button icon={<ReloadOutlined />} onClick={() => setTab((t) => t)}>重新整理</Button>
            </Space>
          </Col>
        </Row>

        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message={`${SOURCE_NOTE}　｜　本頁不含營收金額`}
          description="Departure 報表的 BALANCE 欄位在實測資料中全為 0，無法推估單筆訂房營收。營收、ADR、住房率請看「營收分析」（來源：History and Forecast）。"
        />

        <Tabs
          activeKey={tab}
          onChange={(k) => { setTab(k); setPage(1) }}
          items={[
            // ── 住宿明細 ──────────────────────────────────────────────────
            {
              key: 'stays',
              label: '住宿明細',
              children: (
                <Card size="small" title="住宿明細（點擊列開啟明細）">
                  <Space wrap style={{ marginBottom: 12 }}>
                    <Input.Search
                      allowClear
                      placeholder="搜尋房號／訂房編號／外部參考號"
                      style={{ width: 260 }}
                      onSearch={(v) => { setSearch(v); setPage(1) }}
                    />
                    <Select
                      allowClear placeholder="通路" style={{ width: 200 }}
                      value={channelFilter || undefined}
                      onChange={(v) => { setChannelFilter(v || ''); setPage(1) }}
                      options={options.channel.map((c) => ({ value: c, label: c }))}
                    />
                    <Select
                      allowClear placeholder="房型" style={{ width: 140 }}
                      value={categoryFilter || undefined}
                      onChange={(v) => { setCategoryFilter(v || ''); setPage(1) }}
                      options={options.room_category.map((c) => ({ value: c, label: c }))}
                    />
                  </Space>
                  <Table
                    rowKey="id"
                    size="small"
                    dataSource={stays}
                    columns={stayColumns}
                    scroll={{ x: 1300 }}
                    pagination={{
                      current: page,
                      pageSize,
                      total: stayTotal,
                      showSizeChanger: true,
                      showTotal: (t) => `共 ${t.toLocaleString('en-US')} 筆`,
                      onChange: (p, ps) => { setPage(p); setPageSize(ps) },
                    }}
                    onRow={(record) => ({ onClick: () => openStayDrawer(record), style: { cursor: 'pointer' } })}
                  />
                </Card>
              ),
            },

            // ── 通路 ─────────────────────────────────────────────────────
            {
              key: 'channel',
              label: '通路',
              children: (
                <>
                  <Card
                    size="small"
                    title="通路貢獻 Pareto（累計占比達 80% 的通路即為主力）"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.channel?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderPareto(dimData.channel)}
                  </Card>
                  <Card size="small" title="通路統計">{dimensionTable(dimData.channel)}</Card>
                </>
              ),
            },

            // ── 房型 ─────────────────────────────────────────────────────
            {
              key: 'room_category',
              label: '房型',
              children: (
                <>
                  <Card
                    size="small"
                    title="房型占比"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.room_category?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderPie(dimData.room_category)}
                  </Card>
                  <Card size="small" title="房型統計">{dimensionTable(dimData.room_category)}</Card>
                </>
              ),
            },

            // ── Rate Code ────────────────────────────────────────────────
            {
              key: 'rate_code',
              label: 'Rate Code',
              children: (
                <>
                  <Card
                    size="small"
                    title="Rate Code Top 15"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.rate_code?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderHorizontalBar(dimData.rate_code)}
                  </Card>
                  <Card size="small" title="Rate Code 統計">{dimensionTable(dimData.rate_code)}</Card>
                </>
              ),
            },

            // ── 公司 ─────────────────────────────────────────────────────
            {
              key: 'company',
              label: '公司',
              children: (
                <>
                  <Alert
                    type="warning"
                    showIcon
                    style={{ marginBottom: 12 }}
                    message="公司欄位母體偏小"
                    description="實測 Departure 資料中約 86% 的紀錄沒有填寫公司名稱，本頁統計僅涵蓋有填寫的部分。"
                  />
                  <Card
                    size="small"
                    title="公司 Top 20"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.company?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderHorizontalBar(dimData.company)}
                  </Card>
                  <Card size="small" title="公司統計">{dimensionTable(dimData.company)}</Card>
                </>
              ),
            },

            // ── 回訪與長住 ────────────────────────────────────────────────
            {
              key: 'guest',
              label: '回訪與長住',
              children: (
                <>
                  {repeat && (
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginBottom: 12 }}
                      message={`本分析僅涵蓋非「已清除」住客，母體佔比 ${fmtPct(repeat.coverage.coverage)}`}
                      description={`期間共 ${fmtInt(repeat.coverage.total)} 筆住宿紀錄，其中 ${fmtInt(repeat.coverage.purged)} 筆的住客資料已被 OPERA 清除（Purged-Individual），無法識別身分，因此不納入回訪統計。`}
                    />
                  )}

                  <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                    {/* C12：回訪次數分布 */}
                    <Col xs={24} lg={12}>
                      <Card size="small" title="回訪次數分布">
                        {!repeat || repeat.total_guests === 0 ? <Empty description="期間內無可識別住客" /> : (
                          <>
                            <ResponsiveContainer width="100%" height={240}>
                              <BarChart data={repeat.distribution} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
                                <RcTooltip formatter={(v: any) => [Number(v).toLocaleString('en-US'), '住客數']} />
                                <Bar dataKey="guests" name="住客數" fill={BRAND} barSize={40}>
                                  <LabelList dataKey="guests" position="top" style={{ fontSize: 11 }} />
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {`可識別住客 ${fmtInt(repeat.total_guests)} 人，其中回訪 ${fmtInt(repeat.repeat_guests)} 人（${fmtPct(repeat.repeat_rate)}）　${SOURCE_NOTE}`}
                            </Text>
                          </>
                        )}
                      </Card>
                    </Col>

                    {/* C13：住宿晚數分布 */}
                    <Col xs={24} lg={12}>
                      <Card size="small" title="住宿晚數分布">
                        {!longStay || longStay.distribution.length === 0 ? <Empty description="期間內無資料" /> : (
                          <>
                            <ResponsiveContainer width="100%" height={240}>
                              <BarChart
                                data={longStay.distribution.filter((d) => d.nights <= 21)}
                                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                              >
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="nights" tick={{ fontSize: 11 }} />
                                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
                                <RcTooltip formatter={(v: any) => [Number(v).toLocaleString('en-US'), '筆數']} labelFormatter={(l) => `${l} 晚`} />
                                <ReferenceLine
                                  x={longStay.threshold}
                                  stroke={RED}
                                  strokeDasharray="5 4"
                                  label={{ value: `長住門檻 ${longStay.threshold} 晚`, position: 'top', fontSize: 11, fill: RED }}
                                />
                                <Bar dataKey="records" name="筆數" fill={ACCENT}>
                                  {longStay.distribution.filter((d) => d.nights <= 21).map((d, i) => (
                                    <Cell key={i} fill={d.is_long_stay ? ORANGE : ACCENT} />
                                  ))}
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {`長住 ${fmtInt(longStay.long_records)} / ${fmtInt(longStay.total_records)} 筆（${fmtPct(longStay.long_rate)}）　僅顯示 21 晚以內　${SOURCE_NOTE}`}
                            </Text>
                          </>
                        )}
                      </Card>
                    </Col>
                  </Row>

                  <Card size="small" title="回訪住客（2 次以上）">
                    <Table
                      rowKey="guest_hash"
                      size="small"
                      dataSource={repeat?.top_guests || []}
                      pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 位` }}
                      columns={[
                        { title: '住客（遮罩）', dataIndex: 'guest_label', width: 220 },
                        { title: '識別碼', dataIndex: 'guest_hash', width: 140, render: (v: string) => <Text code style={{ fontSize: 11 }}>{v}</Text> },
                        { title: '入住次數', dataIndex: 'visits', align: 'right', render: (v: number) => <Text strong style={{ color: GREEN }}>{fmtInt(v)}</Text>, sorter: (a, b) => a.visits - b.visits },
                        { title: '總房晚', dataIndex: 'room_nights', align: 'right', render: fmtInt },
                        { title: '總住宿晚數', dataIndex: 'nights', align: 'right', render: fmtInt },
                        { title: '最近退房日', dataIndex: 'last_departure', width: 120 },
                      ]}
                    />
                  </Card>
                </>
              ),
            },
          ]}
        />

        <StayDetailDrawer open={drawerOpen} stay={drawerStay} onClose={() => setDrawerOpen(false)} />
      </div>
    </Spin>
  )
}

export default OperaGuestPage
