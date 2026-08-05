/**
 * 歷史同期查詢（/opera/lookup）
 * 評估文件：docs/EVAL_opera_rate_forecasting.md §3.1（需求 4）
 *
 * TAB：單日查詢 / 期間查詢
 *
 * 這一頁**不做預測**，只查歷史事實 —— 訂價會議上最常問的
 * 「去年這天賣多少、賣得掉嗎」，現在一頁就能回答。
 * 資料來源：營收走 History and Forecast、住客結構走 Departure（決策 D7）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Card, Col, DatePicker, Descriptions, Empty, Row, Space, Spin, Statistic,
  Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import { InfoCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, Pie, PieChart,
  ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'

import { fetchDateLookup, fetchPeriodLookup } from '@/api/opera'
import type {
  DateLookupResult, LookupComparison, PeriodLookupResult, RevenueDailyRow, WeekdayRow,
} from '@/types/opera'
import BackToTop from '../components/BackToTop'
import StandardRangePicker from '@/components/StandardRangePicker'
import {
  ACCENT, BRAND, CHART_COLORS, EMPTY, GREEN, GREY, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct, fmtPpt, fmtYoY, periodTagColor, shortDate, trendColor,
} from '../components/formatters'

const { Title, Text, Paragraph } = Typography

const CHART_HEIGHT = 300

const OperaLookupPage: React.FC = () => {
  const [tab, setTab] = useState('date')
  const [loading, setLoading] = useState(false)

  const [pickedDate, setPickedDate] = useState<Dayjs | null>(null)
  const [dateResult, setDateResult] = useState<DateLookupResult | null>(null)

  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [periodResult, setPeriodResult] = useState<PeriodLookupResult | null>(null)

  // ── 載入 ────────────────────────────────────────────────────────────────
  const loadDate = useCallback(async (d: Dayjs) => {
    setLoading(true)
    try {
      setDateResult(await fetchDateLookup(d.format('YYYY-MM-DD')))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入單日查詢失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadPeriod = useCallback(async (r: [Dayjs, Dayjs]) => {
    setLoading(true)
    try {
      setPeriodResult(await fetchPeriodLookup(r[0].format('YYYY-MM-DD'), r[1].format('YYYY-MM-DD')))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入期間查詢失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  // 第一次進頁：用資料庫最後一天當預設，而不是今天
  // （OPERA 匯出通常落後幾天，用今天會查到空資料讓人以為壞了）
  useEffect(() => {
    if (pickedDate) return
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetchDateLookup(dayjs().format('YYYY-MM-DD'))
        if (cancelled) return
        const fallback = res.has_data ? dayjs(res.business_date) : dayjs(res.data_range.end)
        setPickedDate(fallback)
        if (res.has_data) {
          setDateResult(res)
        } else {
          setDateResult(await fetchDateLookup(fallback.format('YYYY-MM-DD')))
        }
      } catch {
        if (!cancelled) setPickedDate(dayjs())
      }
    })()
    return () => { cancelled = true }
  }, [pickedDate])

  useEffect(() => {
    if (tab === 'period' && !periodResult && !range) {
      const end = dateResult ? dayjs(dateResult.data_range.end) : dayjs()
      const r: [Dayjs, Dayjs] = [end.startOf('month'), end]
      setRange(r)
      loadPeriod(r)
    }
  }, [tab, periodResult, range, dateResult, loadPeriod])

  // ══════════════════════════════════════════════════════════════════════════
  // 單日查詢
  // ══════════════════════════════════════════════════════════════════════════

  const comparisonColumns: ColumnsType<LookupComparison> = [
    {
      title: '對照基準',
      dataIndex: 'label',
      width: 230,
      render: (v: string, r) => (
        <Space direction="vertical" size={0}>
          <Text strong>{v}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{r.hint}</Text>
        </Space>
      ),
    },
    {
      title: 'ADR',
      width: 110,
      align: 'right',
      render: (_, r) => (r.metrics ? `$${fmtMoney(r.metrics.adr)}` : <Text type="secondary">{EMPTY}</Text>),
    },
    {
      title: '住房率',
      width: 100,
      align: 'right',
      render: (_, r) => (r.metrics ? fmtPct(r.metrics.occupancy) : <Text type="secondary">{EMPTY}</Text>),
    },
    {
      title: 'RevPAR',
      width: 110,
      align: 'right',
      render: (_, r) => (r.metrics ? `$${fmtMoney(r.metrics.revpar)}` : <Text type="secondary">{EMPTY}</Text>),
    },
    {
      title: 'ADR 差',
      width: 120,
      align: 'right',
      render: (_, r) =>
        r.diff.adr_diff === null
          ? <Text type="secondary">{EMPTY}</Text>
          : (
            <Text style={{ color: trendColor(r.diff.adr_diff) }}>
              {`${r.diff.adr_diff >= 0 ? '+' : '−'}$${fmtMoney(Math.abs(r.diff.adr_diff))}`}
            </Text>
          ),
    },
    {
      title: '住房率差',
      width: 110,
      align: 'right',
      render: (_, r) =>
        r.diff.occupancy_ppt === null
          ? <Text type="secondary">{EMPTY}</Text>
          : <Text style={{ color: trendColor(r.diff.occupancy_ppt) }}>{fmtPpt(r.diff.occupancy_ppt)}</Text>,
    },
  ]

  const recentChart = useMemo(() => {
    if (!dateResult) return []
    // 由舊到新排（後端是由新到舊往前找）
    return [...dateResult.recent_same_weekday].reverse().map((d) => ({
      date: shortDate(d.business_date),
      ADR: Math.round(d.adr),
      住房率: Number((d.occupancy * 100).toFixed(1)),
    }))
  }, [dateResult])

  const renderDateTab = () => {
    if (!dateResult) return <Empty description="請選擇日期" />
    const t = dateResult.target
    const mc = dateResult.month_context

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        {!dateResult.has_data && (
          <Alert
            type="warning"
            showIcon
            message={`${dateResult.business_date} 沒有營收資料`}
            description={`目前資料範圍：${dateResult.data_range.start} ~ ${dateResult.data_range.end}。`
              + '下方仍會顯示同期對照與當月概況。'}
          />
        )}

        {/* KPI */}
        <Row gutter={16}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<Space size={4}>
                  <span>當日 ADR</span>
                  <Tag color={dateResult.weekday >= 4 ? ORANGE : ACCENT}>{dateResult.weekday_label}</Tag>
                </Space>}
                value={t ? fmtMoney(t.adr) : EMPTY}
                prefix={t ? '$' : ''}
                valueStyle={{ color: BRAND }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="住房率" value={t ? fmtPct(t.occupancy) : EMPTY} valueStyle={{ color: BRAND }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="RevPAR" value={t ? fmtMoney(t.revpar) : EMPTY} prefix={t ? '$' : ''} valueStyle={{ color: BRAND }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={<Tooltip title="總人數 ÷ 已售房晚，判斷賣的是雙人房還是單人使用">
                  <span>每房人數 <InfoCircleOutlined style={{ color: GREY }} /></span>
                </Tooltip>}
                value={t ? t.persons_per_room.toFixed(2) : EMPTY}
                valueStyle={{ color: BRAND }}
              />
            </Card>
          </Col>
        </Row>

        {/* 標記與事件 */}
        {(dateResult.flags.length > 0 || dateResult.events.length > 0) && (
          <Card size="small" title="這天的特殊狀況">
            <Space size={6} wrap>
              {dateResult.flags.map((f) => (
                <Tag key={f.label} color={f.source === '兩者' ? RED : f.source === '年度基準' ? ORANGE : 'blue'}>
                  {f.label}
                </Tag>
              ))}
              {dateResult.events.map((e) => (
                <Tag key={e.id} color="purple">{`${e.category}：${e.name}`}</Tag>
              ))}
              {dateResult.flags.length === 0 && dateResult.events.length === 0 && (
                <Text type="secondary">無</Text>
              )}
            </Space>
          </Card>
        )}

        {/* 同期對照 */}
        <Card size="small" title="同期對照">
          <Table
            rowKey="key"
            size="small"
            pagination={false}
            dataSource={dateResult.comparisons}
            columns={comparisonColumns}
          />
        </Card>

        <Row gutter={16}>
          {/* 近期同星期 */}
          <Col span={12}>
            <Card size="small" title={`最近幾個${dateResult.weekday_label}`} style={{ height: '100%' }}>
              {recentChart.length ? (
                <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                  <ComposedChart data={recentChart}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis yAxisId="l" tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                    <YAxis yAxisId="r" orientation="right" domain={[0, 100]} unit="%" />
                    <RcTooltip />
                    <Legend />
                    <Bar yAxisId="l" dataKey="ADR" fill={BRAND} />
                    <Line yAxisId="r" dataKey="住房率" stroke={ORANGE} strokeWidth={2} />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : <Empty description="沒有足夠的同星期資料" />}
            </Card>
          </Col>

          {/* 當月概況 */}
          <Col span={12}>
            <Card size="small" title={`當月概況（${mc.month}${mc.is_partial ? '，MTD' : ''}）`} style={{ height: '100%' }}>
              <Descriptions size="small" column={1} bordered>
                <Descriptions.Item label="當月加權 ADR">
                  <Space>
                    <Text strong>{`$${fmtMoney(mc.current.adr)}`}</Text>
                    {mc.has_compare_data && (
                      <Text style={{ color: trendColor(mc.yoy.adr) }}>{fmtYoY(mc.yoy.adr)}</Text>
                    )}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="當月住房率">
                  <Space>
                    <Text strong>{fmtPct(mc.current.occupancy)}</Text>
                    {mc.has_compare_data && (
                      <Text style={{ color: trendColor(mc.yoy.occupancy_ppt) }}>{fmtPpt(mc.yoy.occupancy_ppt)}</Text>
                    )}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="當月營收">
                  <Space>
                    <Text strong>{`$${fmtMoney(mc.current.revenue)}`}</Text>
                    {mc.has_compare_data && (
                      <Text style={{ color: trendColor(mc.yoy.revenue) }}>{fmtYoY(mc.yoy.revenue)}</Text>
                    )}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="比較基準">
                  {mc.has_compare_data
                    ? mc.compare_label
                    : <Text type="secondary">{`${mc.compare_label}　無資料`}</Text>}
                </Descriptions.Item>
                <Descriptions.Item label={`${dateResult.weekday_label}在當月`}>
                  {dateResult.weekday_context.in_month
                    ? `ADR $${fmtMoney(dateResult.weekday_context.in_month.adr)}　`
                      + `住房率 ${fmtPct(dateResult.weekday_context.in_month.occupancy)}　`
                      + `（${dateResult.weekday_context.in_month.days} 天）`
                    : EMPTY}
                </Descriptions.Item>
              </Descriptions>
              {dateResult.weekday_context.thin_data && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  ⚠️ 當月每個星期別不到 8 天，星期比較容易被單一活動日扭曲。
                </Text>
              )}
            </Card>
          </Col>
        </Row>

        {/* 住客結構 */}
        <Card
          size="small"
          title="當日退房的住客結構"
          extra={<Text type="secondary" style={{ fontSize: 12 }}>{dateResult.stay_mix.basis_note}</Text>}
        >
          {dateResult.stay_mix.has_data ? (
            <Row gutter={16}>
              <Col span={6}>
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="退房筆數">{fmtInt(dateResult.stay_mix.stays)}</Descriptions.Item>
                  <Descriptions.Item label="房晚">{fmtInt(dateResult.stay_mix.room_nights)}</Descriptions.Item>
                  <Descriptions.Item label="成人／兒童">
                    {`${fmtInt(dateResult.stay_mix.adults)} ／ ${fmtInt(dateResult.stay_mix.child_count)}`}
                  </Descriptions.Item>
                  <Descriptions.Item label="平均住宿天數">{`${dateResult.stay_mix.avg_los} 晚`}</Descriptions.Item>
                </Descriptions>
              </Col>
              <Col span={9}>
                <Text type="secondary" style={{ fontSize: 12 }}>通路</Text>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={dateResult.stay_mix.channels}
                      dataKey="stays"
                      nameKey="name"
                      outerRadius={80}
                      isAnimationActive={false}
                      label={(e: any) => e.name}
                    >
                      {dateResult.stay_mix.channels.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <RcTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Col>
              <Col span={9}>
                <Text type="secondary" style={{ fontSize: 12 }}>房型</Text>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={dateResult.stay_mix.room_categories}
                      dataKey="stays"
                      nameKey="name"
                      outerRadius={80}
                      isAnimationActive={false}
                      label={(e: any) => e.name}
                    >
                      {dateResult.stay_mix.room_categories.map((_, i) => (
                        <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <RcTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Col>
            </Row>
          ) : <Empty description="當日沒有退房紀錄" />}
        </Card>
      </Space>
    )
  }

  // ══════════════════════════════════════════════════════════════════════════
  // 期間查詢
  // ══════════════════════════════════════════════════════════════════════════

  const dailyChart = useMemo(
    () => (periodResult?.daily || []).map((d) => ({
      date: shortDate(d.business_date),
      ADR: Math.round(d.adr),
      住房率: Number((d.occupancy * 100).toFixed(1)),
    })),
    [periodResult],
  )

  const dayColumns: ColumnsType<RevenueDailyRow> = [
    { title: '日期', dataIndex: 'business_date', width: 120 },
    { title: 'ADR', dataIndex: 'adr', width: 110, align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
    { title: '住房率', dataIndex: 'occupancy', width: 100, align: 'right', render: (v: number) => fmtPct(v) },
    { title: 'RevPAR', dataIndex: 'revpar', width: 110, align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
    { title: '營收', dataIndex: 'revenue', width: 130, align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
  ]

  const weekdayColumns: ColumnsType<WeekdayRow> = [
    { title: '星期', dataIndex: 'label', width: 90 },
    { title: '天數', dataIndex: 'days', width: 70, align: 'right' },
    { title: 'ADR', dataIndex: 'adr', width: 110, align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
    {
      title: 'vs 整體',
      dataIndex: 'adr_vs_overall',
      width: 110,
      align: 'right',
      render: (v: number) => (
        <Text style={{ color: trendColor(v) }}>{`${v >= 0 ? '+' : '−'}$${fmtMoney(Math.abs(v))}`}</Text>
      ),
    },
    { title: '住房率', dataIndex: 'occupancy', width: 100, align: 'right', render: (v: number) => fmtPct(v) },
    {
      title: 'vs 整體',
      dataIndex: 'occupancy_vs_overall',
      width: 100,
      align: 'right',
      render: (v: number) => <Text style={{ color: trendColor(v) }}>{fmtPpt(v)}</Text>,
    },
    { title: 'RevPAR', dataIndex: 'revpar', width: 110, align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
  ]

  const renderPeriodTab = () => {
    if (!periodResult) return <Empty description="請選擇期間" />
    const p = periodResult

    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Space size={8} wrap>
          <Tag color={periodTagColor(p.period.period_type)}>{p.period.period_label}</Tag>
          <Text type="secondary">{`比較基準：${p.period.compare_label}（${p.period.compare_start} ~ ${p.period.compare_end}）`}</Text>
          {!p.has_compare_data && <Tag color={ORANGE}>去年同期無資料</Tag>}
        </Space>

        <Row gutter={16}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="加權 ADR" value={fmtMoney(p.current.adr)} prefix="$" valueStyle={{ color: BRAND }} />
              {p.has_compare_data && (
                <Text style={{ color: trendColor(p.yoy.adr) }}>{`${fmtYoY(p.yoy.adr)} vs 同期`}</Text>
              )}
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="住房率" value={fmtPct(p.current.occupancy)} valueStyle={{ color: BRAND }} />
              {p.has_compare_data && (
                <Text style={{ color: trendColor(p.yoy.occupancy_ppt) }}>{`${fmtPpt(p.yoy.occupancy_ppt)} vs 同期`}</Text>
              )}
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="RevPAR" value={fmtMoney(p.current.revpar)} prefix="$" valueStyle={{ color: BRAND }} />
              {p.has_compare_data && (
                <Text style={{ color: trendColor(p.yoy.revpar) }}>{`${fmtYoY(p.yoy.revpar)} vs 同期`}</Text>
              )}
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="總營收" value={fmtMoney(p.current.revenue)} prefix="$" valueStyle={{ color: BRAND }} />
              {p.has_compare_data && (
                <Text style={{ color: trendColor(p.yoy.revenue) }}>{`${fmtYoY(p.yoy.revenue)} vs 同期`}</Text>
              )}
            </Card>
          </Col>
        </Row>

        <Card size="small" title="逐日走勢">
          <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
            <ComposedChart data={dailyChart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" minTickGap={24} />
              <YAxis yAxisId="l" tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
              <YAxis yAxisId="r" orientation="right" domain={[0, 100]} unit="%" />
              <RcTooltip />
              <Legend />
              <Line yAxisId="l" dataKey="ADR" stroke={BRAND} dot={false} strokeWidth={2} />
              <Line yAxisId="r" dataKey="住房率" stroke={ORANGE} dot={false} strokeWidth={2} />
            </ComposedChart>
          </ResponsiveContainer>
        </Card>

        <Row gutter={16}>
          <Col span={12}>
            <Card size="small" title="星期分布（加權）">
              <Table rowKey="weekday" size="small" pagination={false}
                dataSource={p.weekday} columns={weekdayColumns} />
              {p.weekday_thin && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  ⚠️ 有星期別的樣本不到 8 天，容易被單一活動日扭曲。
                </Text>
              )}
            </Card>
          </Col>
          <Col span={12}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Card size="small" title="表現最好的 5 天（依 RevPAR）">
                <Table rowKey="business_date" size="small" pagination={false}
                  dataSource={p.best_days} columns={dayColumns} />
              </Card>
              <Card size="small" title="表現最差的 5 天（依 RevPAR）">
                <Table rowKey="business_date" size="small" pagination={false}
                  dataSource={p.worst_days} columns={dayColumns} />
              </Card>
            </Space>
          </Col>
        </Row>

        {p.months.length > 1 && (
          <Card size="small" title="月分布">
            <Table
              rowKey="month"
              size="small"
              pagination={false}
              dataSource={p.months}
              columns={[
                { title: '月份', dataIndex: 'month', width: 110 },
                { title: '天數', dataIndex: 'days', width: 70, align: 'right' },
                { title: 'ADR', dataIndex: 'adr', width: 110, align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                { title: '住房率', dataIndex: 'occupancy', width: 100, align: 'right', render: (v: number) => fmtPct(v) },
                { title: 'RevPAR', dataIndex: 'revpar', width: 110, align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                { title: '營收', dataIndex: 'revenue', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
              ]}
            />
          </Card>
        )}

        <Card size="small" title="期間退房的住客結構">
          {p.stay_mix.has_data ? (
            <Row gutter={16}>
              <Col span={8}>
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="退房筆數">{fmtInt(p.stay_mix.stays)}</Descriptions.Item>
                  <Descriptions.Item label="房晚">{fmtInt(p.stay_mix.room_nights)}</Descriptions.Item>
                  <Descriptions.Item label="人數">{fmtInt(p.stay_mix.persons)}</Descriptions.Item>
                  <Descriptions.Item label="平均住宿天數">{`${p.stay_mix.avg_los} 晚`}</Descriptions.Item>
                </Descriptions>
              </Col>
              <Col span={16}>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={p.stay_mix.channels} layout="vertical" margin={{ left: 80 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="name" width={140} />
                    <RcTooltip />
                    <Bar dataKey="stays" name="退房筆數" fill={ACCENT} />
                  </BarChart>
                </ResponsiveContainer>
              </Col>
            </Row>
          ) : <Empty description="期間內沒有退房紀錄" />}
        </Card>
      </Space>
    )
  }

  // ══════════════════════════════════════════════════════════════════════════

  return (
    <div style={{ padding: 24 }}>
      <Title level={4} style={{ color: BRAND }}>歷史同期查詢</Title>
      <Paragraph type="secondary" style={{ marginTop: -8 }}>
        查歷史事實，不做預測。輸入日期或期間，看去年同期、近期同星期與當月概況。
      </Paragraph>

      <Card
        size="small"
        style={{ marginBottom: 16 }}
        extra={
          tab === 'date' ? (
            <DatePicker
              value={pickedDate}
              allowClear={false}
              onChange={(d) => { if (d) { setPickedDate(d); loadDate(d) } }}
            />
          ) : (
            <StandardRangePicker
              value={range}
              anchor={dateResult?.data_range.end}
              onChange={(r) => {
                // 「全部」會回傳 null。本頁的 API 兩端都必填，
                // 所以把它對應成「完整資料範圍」而不是不篩選。
                const rr = r ?? (dateResult
                  ? [dayjs(dateResult.data_range.start), dayjs(dateResult.data_range.end)] as [Dayjs, Dayjs]
                  : null)
                if (!rr) return
                setRange(rr)
                loadPeriod(rr)
              }}
            />
          )
        }
      >
        <Spin spinning={loading}>
          <Tabs
            activeKey={tab}
            onChange={setTab}
            items={[
              { key: 'date', label: '單日查詢', children: renderDateTab() },
              { key: 'period', label: '期間查詢', children: renderPeriodTab() },
            ]}
          />
        </Spin>
      </Card>

      <Text type="secondary" style={{ fontSize: 12 }}>
        {dateResult?.source_label || periodResult?.source_label
          || '資料來源：History and Forecast（營收）／Departure All（住客結構）'}
      </Text>

      <BackToTop />
    </div>
  )
}

export default OperaLookupPage
