/**
 * 商場管理統計 Dashboard
 * Mall Operations Monitoring Dashboard
 *
 * 整合 B1F / B2F / RF 每日巡檢 + 商場週期保養 的主管管理視圖
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Select, Segmented, Alert,
  message, Badge, DatePicker, Tooltip, Tabs, Divider,
  Progress,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, WarningOutlined,
  CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
  BarChartOutlined, SafetyOutlined, CalendarOutlined,
  DashboardOutlined, RightOutlined, AlertOutlined,
} from '@ant-design/icons'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RcTooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchDashboardSummary,
  fetchDashboardIssues,
  fetchDashboardTrend,
} from '@/api/mallDashboard'
import type {
  DashboardSummary, FloorInspectionStats, IssueItem, TrendPoint,
} from '@/types/mallDashboard'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

// ── 常數 ──────────────────────────────────────────────────────────────────────

const FLOOR_COLORS: Record<string, string> = {
  b1f: '#1B3A5C',
  b2f: '#4BA8E8',
  rf:  '#52C41A',
}
const STATUS_TAG: Record<string, string> = {
  abnormal:  'error',
  pending:   'warning',
  unchecked: 'default',
  overdue:   'error',
}
const STATUS_COLOR: Record<string, string> = {
  abnormal:  '#FF4D4F',
  pending:   '#FAAD14',
  unchecked: '#999999',
  overdue:   '#FF4D4F',
}
const PIE_STATUS_MAP = [
  { key: 'normal',    label: '正常',   fill: '#52C41A' },
  { key: 'abnormal',  label: '異常',   fill: '#FF4D4F' },
  { key: 'pending',   label: '待處理', fill: '#FAAD14' },
  { key: 'unchecked', label: '未巡檢', fill: '#AAAAAA' },
]

// ── 子元件：KPI 卡片 ──────────────────────────────────────────────────────────

function KpiCard({
  title, value, suffix = '', color, icon, sub, onClick,
}: {
  title: string; value: string | number; suffix?: string
  color: string; icon: React.ReactNode; sub?: string
  onClick?: () => void
}) {
  return (
    <Card
      size="small"
      hoverable={!!onClick}
      onClick={onClick}
      style={{
        textAlign: 'center',
        cursor: onClick ? 'pointer' : 'default',
        borderTop: `3px solid ${color}`,
        transition: 'box-shadow .2s',
      }}
    >
      <div style={{ color, fontSize: 28, marginBottom: 2 }}>{icon}</div>
      <div style={{ color, fontSize: 32, fontWeight: 700, lineHeight: 1.2 }}>
        {value}
        {suffix && <span style={{ fontSize: 14, marginLeft: 4, fontWeight: 400 }}>{suffix}</span>}
      </div>
      <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>{title}</div>
      {sub && <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </Card>
  )
}

// ── 子元件：樓層橫條比較圖 ────────────────────────────────────────────────────

function FloorCompareChart({ floors }: { floors: FloorInspectionStats[] }) {
  if (!floors.length) return <div style={{ textAlign: 'center', color: '#999', paddingTop: 60 }}>暫無資料</div>

  const data = floors.map(f => ({
    name:       f.floor_label,
    完成率:     f.completion_rate,
    異常數:     f.abnormal_items + f.pending_items,
    未巡檢:     f.unchecked_items,
    正常:       f.normal_items,
    fill:       FLOOR_COLORS[f.floor] ?? '#999',
  }))

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} md={12}>
        <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13 }}>各樓層完成率（%）</Text>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30 }}>
            <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 13, fontWeight: 600 }} width={40} />
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <RcTooltip formatter={(v) => [`${v}%`, '完成率']} />
            <Bar dataKey="完成率" radius={[0, 4, 4, 0]}>
              {data.map((entry, idx) => (
                <Cell key={idx} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Col>
      <Col xs={24} md={12}>
        <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13 }}>各樓層異常 / 未巡檢數</Text>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30 }}>
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 13, fontWeight: 600 }} width={40} />
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <RcTooltip />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="異常數" stackId="a" fill="#FF4D4F" radius={[0, 0, 0, 0]} />
            <Bar dataKey="未巡檢" stackId="a" fill="#CCCCCC" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Col>
    </Row>
  )
}

// ── 子元件：巡檢狀態圓餅 ──────────────────────────────────────────────────────

function InspectionDonut({ floors }: { floors: FloorInspectionStats[] }) {
  const totals = floors.reduce(
    (acc, f) => {
      acc.normal    += f.normal_items
      acc.abnormal  += f.abnormal_items
      acc.pending   += f.pending_items
      acc.unchecked += f.unchecked_items
      return acc
    },
    { normal: 0, abnormal: 0, pending: 0, unchecked: 0 },
  )

  const data = PIE_STATUS_MAP
    .map(s => ({ name: s.label, value: totals[s.key as keyof typeof totals] ?? 0, fill: s.fill }))
    .filter(d => d.value > 0)

  if (!data.length) return <div style={{ textAlign: 'center', color: '#999', paddingTop: 40 }}>暫無資料</div>

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name"
          cx="50%" cy="50%" innerRadius={50} outerRadius={80}
          label={({ name, value }) => `${name}:${value}`} labelLine={false}>
          {data.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
        </Pie>
        <RcTooltip formatter={(v, n) => [v, n]} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function MallDashboardPage() {
  const navigate = useNavigate()

  // ── State ──────────────────────────────────────────────────────────────────
  const [summary, setSummary]         = useState<DashboardSummary | null>(null)
  const [issues, setIssues]           = useState<IssueItem[]>([])
  const [trend, setTrend]             = useState<TrendPoint[]>([])
  const [trendDays, setTrendDays]     = useState<7 | 30>(7)
  const [issueTab, setIssueTab]       = useState('all')
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [loadingIssues, setLoadingIssues]   = useState(false)
  const [loadingTrend, setLoadingTrend]     = useState(false)
  const [targetDate, setTargetDate]   = useState<string>(dayjs().format('YYYY/MM/DD'))

  // ── 資料載入 ───────────────────────────────────────────────────────────────
  const loadSummary = useCallback(async (dt?: string) => {
    setLoadingSummary(true)
    try { setSummary(await fetchDashboardSummary(dt ?? targetDate)) }
    catch { message.error('載入 KPI 摘要失敗') }
    finally { setLoadingSummary(false) }
  }, [targetDate])

  const loadIssues = useCallback(async (tab?: string) => {
    setLoadingIssues(true)
    const t = tab ?? issueTab
    const opts: Record<string, string> = {}
    if (t !== 'all') opts.status = t
    try { const res = await fetchDashboardIssues(opts); setIssues(res.items) }
    catch { message.error('載入清單失敗') }
    finally { setLoadingIssues(false) }
  }, [issueTab])

  const loadTrend = useCallback(async (days?: number) => {
    setLoadingTrend(true)
    try { const res = await fetchDashboardTrend(days ?? trendDays); setTrend(res.trend) }
    catch { message.error('載入趨勢資料失敗') }
    finally { setLoadingTrend(false) }
  }, [trendDays])

  const loadAll = useCallback(() => {
    loadSummary()
    loadIssues()
    loadTrend()
  }, [loadSummary, loadIssues, loadTrend])

  useEffect(() => { loadAll() }, [])  // eslint-disable-line

  // ── KPI 快速導向 ───────────────────────────────────────────────────────────
  const handleKpiClick = (tab: string) => {
    setIssueTab(tab)
    loadIssues(tab)
    document.getElementById('issues-section')?.scrollIntoView({ behavior: 'smooth' })
  }

  // ── 衍生數值 ───────────────────────────────────────────────────────────────
  const ins  = summary?.inspection
  const pm   = summary?.pm
  const floors = ins?.by_floor ?? []

  const trendChartData = trend.map(t => ({
    date:   t.date.slice(5),   // MM/DD
    B1F:    t.b1f_completion,
    B2F:    t.b2f_completion,
    RF:     t.rf_completion,
    異常數: t.total_abnormal,
  }))

  // ── Issues 表格欄位 ────────────────────────────────────────────────────────
  const issueColumns: ColumnsType<IssueItem> = [
    {
      title: '日期', dataIndex: 'issue_date', width: 110,
      sorter: (a, b) => a.issue_date.localeCompare(b.issue_date),
      defaultSortOrder: 'descend',
    },
    {
      title: '類型', dataIndex: 'issue_type', width: 80,
      render: (v) => (
        <Tag color={v === 'inspection' ? 'blue' : 'purple'}>
          {v === 'inspection' ? '巡檢' : '保養'}
        </Tag>
      ),
    },
    {
      title: '區域', dataIndex: 'floor', width: 70,
      render: (v) => <Tag color="geekblue">{v}</Tag>,
    },
    {
      title: '項目名稱', dataIndex: 'item_name', ellipsis: true,
    },
    {
      title: '狀態', dataIndex: 'status', width: 90,
      render: (v, row) => <Tag color={STATUS_TAG[v] ?? 'default'}>{row.status_label}</Tag>,
    },
    {
      title: '負責人', dataIndex: 'responsible', width: 90,
      render: (v) => v ? <Text>{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: '說明', dataIndex: 'note', width: 160, ellipsis: true,
      render: (v) => v ? <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: '', width: 70,
      render: (_, row) => {
        const floorPath = row.floor === 'B1F' ? 'b1f'
          : row.floor === 'B2F' ? 'b2f'
          : row.floor === 'RF'  ? 'rf'
          : null
        if (!floorPath) return null
        return (
          <Button type="link" size="small" icon={<RightOutlined />}
            onClick={() => navigate(`/mall/${floorPath}-inspection/${row.batch_id}`)}>
            明細
          </Button>
        )
      },
    },
  ]

  const filteredIssues = issueTab === 'all'
    ? issues
    : issues.filter(i => i.status === issueTab)

  const issueCounts = issues.reduce((acc, i) => {
    acc[i.status] = (acc[i.status] ?? 0) + 1
    return acc
  }, {} as Record<string, number>)

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 4px 40px' }}>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <Breadcrumb style={{ marginBottom: 12 }} items={[
        { title: <HomeOutlined /> },
        { title: NAV_GROUP.mall },
        { title: NAV_PAGE.mallDashboard },
      ]} />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Space align="baseline">
            <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
              <DashboardOutlined style={{ marginRight: 8 }} />
              {NAV_PAGE.mallDashboard}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>Mall Operations Monitoring Dashboard</Text>
          </Space>
        </Col>
        <Col>
          <Space>
            <DatePicker
              value={dayjs(targetDate, 'YYYY/MM/DD')}
              format="YYYY/MM/DD"
              allowClear={false}
              onChange={(d) => {
                if (d) {
                  const ds = d.format('YYYY/MM/DD')
                  setTargetDate(ds)
                  loadSummary(ds)
                }
              }}
            />
            <Button onClick={() => { setTargetDate(dayjs().format('YYYY/MM/DD')); loadSummary(dayjs().format('YYYY/MM/DD')) }}>
              今日
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loadingSummary}>
              重新整理
            </Button>
          </Space>
        </Col>
      </Row>

      {summary?.generated_at && (
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 16 }}>
          資料截至 {summary.generated_at}
        </Text>
      )}

      {/* ── KPI 卡片（2 × 4）────────────────────────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {/* 巡檢 KPI */}
        <Col xs={12} sm={6}>
          <KpiCard title="今日應完成巡檢"
            value={ins?.total_items ?? 0} suffix="項"
            color="#1B3A5C" icon={<SafetyOutlined />}
            sub={`${ins?.total_batches ?? 0} 場次 · ${targetDate}`} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="今日已完成巡檢"
            value={ins?.checked_items ?? 0} suffix="項"
            color="#52C41A" icon={<CheckCircleOutlined />}
            sub={ins ? `完成率 ${ins.completion_rate}%` : ''}
            onClick={() => handleKpiClick('all')} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="今日未完成巡檢"
            value={ins?.unchecked_items ?? 0} suffix="項"
            color={ins?.unchecked_items ? '#FAAD14' : '#52C41A'}
            icon={<ClockCircleOutlined />}
            onClick={() => handleKpiClick('unchecked')} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="今日異常件數"
            value={ins?.abnormal_items ?? 0} suffix="件"
            color={ins?.abnormal_items ? '#FF4D4F' : '#52C41A'}
            icon={<WarningOutlined />}
            sub="含待處理" onClick={() => handleKpiClick('abnormal')} />
        </Col>

        {/* 保養 KPI */}
        <Col xs={12} sm={6}>
          <KpiCard title="本月保養應執行"
            value={pm?.total_items ?? 0} suffix="項"
            color="#1B3A5C" icon={<BarChartOutlined />}
            sub={pm?.period_month ?? ''} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="本月保養已完成"
            value={pm?.completed_items ?? 0} suffix="項"
            color="#52C41A" icon={<CheckCircleOutlined />}
            sub={pm ? `完成率 ${pm.completion_rate}%` : ''} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="逾期未保養"
            value={pm?.overdue_items ?? 0} suffix="項"
            color={pm?.overdue_items ? '#FF4D4F' : '#52C41A'}
            icon={<ExclamationCircleOutlined />}
            onClick={() => handleKpiClick('overdue')} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="異常待追蹤"
            value={(ins?.abnormal_items ?? 0) + (pm?.abnormal_items ?? 0)} suffix="件"
            color={((ins?.abnormal_items ?? 0) + (pm?.abnormal_items ?? 0)) > 0 ? '#FF4D4F' : '#52C41A'}
            icon={<AlertOutlined />}
            onClick={() => handleKpiClick('abnormal')} />
        </Col>
      </Row>

      {/* ── 巡檢完成率進度條 ─────────────────────────────────────────────── */}
      {ins && ins.total_items > 0 && (
        <Card size="small" style={{ marginBottom: 16, background: '#fafcff' }}>
          <Row align="middle" gutter={16}>
            <Col flex="120px"><Text strong>整體巡檢完成率</Text></Col>
            <Col flex="auto">
              <Progress
                percent={ins.completion_rate}
                strokeColor={{
                  from: ins.completion_rate < 50 ? '#FF4D4F' : '#FAAD14',
                  to:   '#52C41A',
                }}
                format={(p) => `${p}%（${ins.checked_items}/${ins.total_items}）`}
              />
            </Col>
            <Col flex="120px">
              <Space>
                {ins.abnormal_items > 0 && <Badge count={ins.abnormal_items} color="#FF4D4F" />}
                <Text type="secondary" style={{ fontSize: 12 }}>異常</Text>
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* ── 樓層比較 + 狀態圓餅 ──────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={15}>
          <Card
            title={<><BarChartOutlined /> 各樓層執行情況比較</>}
            size="small"
            loading={loadingSummary}
            extra={<Text type="secondary" style={{ fontSize: 12 }}>{targetDate}</Text>}
          >
            <FloorCompareChart floors={floors} />

            {/* 樓層摘要列 */}
            {floors.length > 0 && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Row gutter={[8, 8]}>
                  {floors.map(f => (
                    <Col key={f.floor} xs={8}>
                      <Card
                        size="small"
                        style={{
                          borderLeft: `4px solid ${FLOOR_COLORS[f.floor] ?? '#999'}`,
                          background: '#fafafa',
                        }}
                      >
                        <Text strong style={{ color: FLOOR_COLORS[f.floor] }}>{f.floor_label}</Text>
                        <div style={{ marginTop: 4 }}>
                          <Progress
                            percent={f.completion_rate}
                            size="small"
                            strokeColor={FLOOR_COLORS[f.floor]}
                            format={() => `${f.completion_rate}%`}
                          />
                        </div>
                        <Row gutter={4} style={{ marginTop: 4 }}>
                          <Col span={12}>
                            <Text type="secondary" style={{ fontSize: 11 }}>異常：</Text>
                            <Text style={{ fontSize: 11, color: f.abnormal_items + f.pending_items > 0 ? '#FF4D4F' : '#52C41A' }}>
                              {f.abnormal_items + f.pending_items}
                            </Text>
                          </Col>
                          <Col span={12}>
                            <Text type="secondary" style={{ fontSize: 11 }}>未巡檢：</Text>
                            <Text style={{ fontSize: 11, color: f.unchecked_items > 0 ? '#FAAD14' : '#52C41A' }}>
                              {f.unchecked_items}
                            </Text>
                          </Col>
                        </Row>
                        <Button
                          type="link" size="small" style={{ padding: 0, fontSize: 11 }}
                          onClick={() => navigate(`/mall/${f.floor.toLowerCase()}-inspection`)}>
                          查看明細 <RightOutlined />
                        </Button>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={9}>
          <Card
            title={<><SafetyOutlined /> 今日巡檢狀態分布</>}
            size="small"
            loading={loadingSummary}
            style={{ height: '100%' }}
          >
            <InspectionDonut floors={floors} />

            {/* 保養狀態摘要 */}
            {pm && pm.total_items > 0 && (
              <>
                <Divider style={{ margin: '10px 0' }} />
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
                  <CalendarOutlined style={{ marginRight: 6 }} />
                  本月保養狀態（{pm.period_month}）
                </Text>
                <Row gutter={[8, 6]}>
                  {[
                    { label: '已完成', value: pm.completed_items,  color: '#52C41A' },
                    { label: '未完成', value: pm.incomplete_items, color: '#FAAD14' },
                    { label: '逾期',   value: pm.overdue_items,    color: '#FF4D4F' },
                    { label: '異常',   value: pm.abnormal_items,   color: '#FF4D4F' },
                  ].map(s => (
                    <Col span={12} key={s.label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 6px',
                        borderRadius: 4, background: '#f9f9f9' }}>
                        <Text style={{ fontSize: 12 }}>{s.label}</Text>
                        <Text strong style={{ fontSize: 12, color: s.color }}>{s.value}</Text>
                      </div>
                    </Col>
                  ))}
                </Row>
                <Progress
                  percent={pm.completion_rate}
                  size="small"
                  style={{ marginTop: 10 }}
                  strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
                  format={(p) => `完成率 ${p}%`}
                />
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* ── 趨勢圖 ───────────────────────────────────────────────────────── */}
      <Card
        title={<><BarChartOutlined /> 近期巡檢趨勢分析</>}
        size="small"
        loading={loadingTrend}
        style={{ marginBottom: 20 }}
        extra={
          <Segmented
            value={trendDays}
            options={[{ label: '近 7 日', value: 7 }, { label: '近 30 日', value: 30 }]}
            onChange={(v) => {
              setTrendDays(v as 7 | 30)
              loadTrend(v as number)
            }}
          />
        }
      >
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>各樓層完成率趨勢（%）</Text>
            {trendChartData.some(t => t.B1F > 0 || t.B2F > 0 || t.RF > 0) ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendChartData} margin={{ left: 0, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                  <RcTooltip formatter={(v, n) => [`${v}%`, n]} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="B1F" stroke={FLOOR_COLORS.b1f} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  <Line type="monotone" dataKey="B2F" stroke={FLOOR_COLORS.b2f} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  <Line type="monotone" dataKey="RF"  stroke={FLOOR_COLORS.rf}  strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', paddingTop: 80, color: '#999' }}>暫無資料</div>
            )}
          </Col>
          <Col xs={24} lg={10}>
            <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>每日異常件數趨勢</Text>
            {trendChartData.some(t => t.異常數 > 0) ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={trendChartData} margin={{ left: 0, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <RcTooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="異常數" fill="#FF4D4F" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Alert message="趨勢期間無異常記錄" type="success" showIcon style={{ marginTop: 60 }} />
            )}
          </Col>
        </Row>
      </Card>

      {/* ── 重點追蹤清單 ─────────────────────────────────────────────────── */}
      <Card
        id="issues-section"
        title={<><ExclamationCircleOutlined /> 重點追蹤清單</>}
        size="small"
        loading={loadingIssues}
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={() => loadIssues()}>
            重新載入
          </Button>
        }
      >
        <Tabs
          activeKey={issueTab}
          onChange={(k) => { setIssueTab(k); loadIssues(k) }}
          items={[
            {
              key: 'all',
              label: (
                <span>全部 <Badge count={issues.length} color="#999" style={{ marginLeft: 4 }} /></span>
              ),
            },
            {
              key: 'abnormal',
              label: (
                <span>異常 <Badge count={(issueCounts.abnormal ?? 0) + (issueCounts.pending ?? 0)} color="#FF4D4F" style={{ marginLeft: 4 }} /></span>
              ),
            },
            {
              key: 'unchecked',
              label: (
                <span>未完成 <Badge count={issueCounts.unchecked ?? 0} color="#FAAD14" style={{ marginLeft: 4 }} /></span>
              ),
            },
            {
              key: 'overdue',
              label: (
                <span>逾期保養 <Badge count={issueCounts.overdue ?? 0} color="#FF4D4F" style={{ marginLeft: 4 }} /></span>
              ),
            },
          ]}
        />
        {filteredIssues.length === 0 ? (
          <Alert
            message={issueTab === 'all' ? '目前無待追蹤項目' : '此分類無待追蹤項目'}
            type="success"
            showIcon
            style={{ marginTop: 16 }}
          />
        ) : (
          <Table<IssueItem>
            dataSource={filteredIssues}
            rowKey="id"
            columns={issueColumns}
            size="small"
            pagination={{ pageSize: 20, showTotal: n => `共 ${n} 筆` }}
            onRow={(rec) => ({
              style: { background: STATUS_COLOR[rec.status] + '1A' },
            })}
            locale={{ emptyText: '暫無資料' }}
          />
        )}
      </Card>
    </div>
  )
}
