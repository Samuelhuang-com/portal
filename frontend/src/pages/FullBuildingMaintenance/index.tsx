/**
 * 全棟例行維護主頁
 *
 * Tab 1「Dashboard」：KPI 五卡（含保養時間）+ 類別 Bar 圖 + 狀態 Donut 圖 + 逾期/即將到期預警
 * Tab 2「每月維護」：月統計（上月累計 / 本月完成 / 未完成說明）
 * Tab 3「每季維護」：季統計（上季累計 / 本季完成 / 月份分布）
 * Tab 4「每年維護」：年統計（上年累計 / 本年完成 / Q1-Q4 分布）
 * Tab 5「批次清單」：保養批次列表，含進度條、狀態標籤、操作入口
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Progress, Alert, Select,
  message, Tooltip, Badge, Divider,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined, ToolOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, RightOutlined, BarChartOutlined,
  ShopOutlined, CalendarOutlined, LineChartOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchFullBldgPMStats, fetchFullBldgPMBatches, syncFullBldgPMFromRagic,
  fetchFullBldgPMPeriodStats, fetchFullBldgPMYearMatrix,
} from '@/api/fullBuildingMaintenance'
import type {
  PMStats, PMBatchListItem, PMItem,
  PMPeriodStats, PMIncompleteItem, PMSubPeriodBreakdown,
  PMYearMatrix, PMYearMatrixMonth,
} from '@/types/periodicMaintenance'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

// ── 狀態設定 ──────────────────────────────────────────────────────────────────
const STATUS_CFG: Record<string, { label: string; color: string; tagColor: string }> = {
  completed:         { label: '已完成', color: '#52C41A', tagColor: 'success' },
  in_progress:       { label: '進行中', color: '#4BA8E8', tagColor: 'processing' },
  scheduled:         { label: '已排定', color: '#FAAD14', tagColor: 'warning' },
  unscheduled:       { label: '未排定', color: '#FF4D4F', tagColor: 'error' },
  overdue:           { label: '逾期',   color: '#C0392B', tagColor: 'error' },
  non_current_month: { label: '非本月', color: '#999999', tagColor: 'default' },
}

const BATCH_STATUS_CFG: Record<string, { label: string; color: string }> = {
  draft:     { label: '草稿',   color: '#999999' },
  active:    { label: '執行中', color: '#4BA8E8' },
  completed: { label: '已完成', color: '#52C41A' },
  abnormal:  { label: '有異常', color: '#722ED1' },
  closed:    { label: '已結案', color: '#1B3A5C' },
}

function deriveBatchStatus(kpi: PMBatchListItem['kpi']): string {
  if (!kpi || kpi.total === 0) return 'draft'
  if (kpi.abnormal > 0) return 'abnormal'
  if (kpi.completed === kpi.total) return 'completed'
  if (kpi.in_progress > 0 || kpi.completed > 0) return 'active'
  return 'draft'
}

// ── 共用：統計數值格式化 ──────────────────────────────────────────────────────
function fmtRate(rate: number | null): string {
  return rate === null ? 'N/A' : `${rate}%`
}

// ── 共用：統計卡片區（上期累計 + 本期）────────────────────────────────────────
interface PeriodKpiCardsProps {
  data: PMPeriodStats
  prevLabel: string
  currLabel: string
}
function PeriodKpiCards({ data, prevLabel, currLabel }: PeriodKpiCardsProps) {
  return (
    <>
      {/* 上期累計區塊 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 8 }}>
        <Col span={24}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            ▸ {prevLabel}累計
          </Typography.Text>
        </Col>
        {[
          {
            title: `${prevLabel}累計未完成`,
            value: data.prev_carry_over,
            suffix: '筆',
            color: '#C0392B',
          },
          {
            title: `${prevLabel}未完成於${currLabel}結案`,
            value: data.prev_resolved_in_period,
            suffix: '筆',
            color: '#4BA8E8',
          },
          {
            title: '累計完成率',
            value: fmtRate(data.carry_over_rate),
            suffix: '',
            color: data.carry_over_rate === null ? '#999' : '#1B3A5C',
          },
        ].map((c) => (
          <Col flex={1} style={{ minWidth: 160 }} key={c.title}>
            <Card size="small" hoverable>
              <Statistic
                title={c.title}
                value={c.value}
                suffix={c.suffix}
                valueStyle={{ color: c.color, fontSize: 24 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 本期統計區塊 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            ▸ {currLabel}統計
          </Typography.Text>
        </Col>
        {[
          {
            title: `${currLabel}項目數`,
            value: data.period_total,
            suffix: '筆',
            color: '#1B3A5C',
          },
          {
            title: `${currLabel}完成數`,
            value: data.period_completed,
            suffix: '筆',
            color: '#52C41A',
          },
          {
            title: `${currLabel}完成率`,
            value: fmtRate(data.period_rate),
            suffix: '',
            color: data.period_rate === null ? '#999' : '#52C41A',
          },
        ].map((c) => (
          <Col flex={1} style={{ minWidth: 160 }} key={c.title}>
            <Card size="small" hoverable>
              <Statistic
                title={c.title}
                value={c.value}
                suffix={c.suffix}
                valueStyle={{ color: c.color, fontSize: 24 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 本期完成率進度條 */}
      {data.period_total > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row align="middle" gutter={16}>
            <Col flex="80px">
              <Typography.Text strong>{currLabel}完成率</Typography.Text>
            </Col>
            <Col flex="auto">
              <Progress
                percent={data.period_rate ?? 0}
                strokeColor={{ from: '#4BA8E8', to: '#52C41A' }}
                format={() => `${fmtRate(data.period_rate)}（${data.period_completed}/${data.period_total}）`}
              />
            </Col>
          </Row>
        </Card>
      )}
    </>
  )
}

// ── 共用：子期間分布表格 ──────────────────────────────────────────────────────
interface SubBreakdownTableProps {
  rows: PMSubPeriodBreakdown[]
  title: string
}
function SubBreakdownTable({ rows, title }: SubBreakdownTableProps) {
  if (rows.length === 0) return null
  const cols: ColumnsType<PMSubPeriodBreakdown> = [
    { title: '期間', dataIndex: 'label', width: 80 },
    { title: '項目數', dataIndex: 'total', width: 90, align: 'right' },
    { title: '完成數', dataIndex: 'completed', width: 90, align: 'right' },
    {
      title: '完成率',
      width: 200,
      render: (_, r) => (
        r.total === 0
          ? <Typography.Text type="secondary">N/A</Typography.Text>
          : <Progress
              percent={r.rate ?? 0}
              size="small"
              strokeColor={{ from: '#4BA8E8', to: '#52C41A' }}
              format={() => `${fmtRate(r.rate)}`}
            />
      ),
    },
  ]
  return (
    <Card title={title} size="small" style={{ marginBottom: 16 }}>
      <Table<PMSubPeriodBreakdown>
        dataSource={rows}
        rowKey="label"
        columns={cols}
        pagination={false}
        size="small"
      />
    </Card>
  )
}

// ── 共用：未完成事項說明表格 ──────────────────────────────────────────────────
interface IncompleteTableProps {
  items: PMIncompleteItem[]
}
function IncompleteTable({ items }: IncompleteTableProps) {
  const cols: ColumnsType<PMIncompleteItem> = [
    { title: '項目名稱', dataIndex: 'task_name', ellipsis: true },
    { title: '類別',     dataIndex: 'category',  width: 80 },
    { title: '頻率',     dataIndex: 'frequency', width: 70 },
    { title: '排定日期', dataIndex: 'scheduled_date_full', width: 100 },
    { title: '備註',     dataIndex: 'result_note', ellipsis: true },
  ]
  return (
    <Card
      title={<><WarningOutlined style={{ color: '#C0392B' }} /> 未完成事項說明</>}
      size="small"
    >
      {items.length === 0 ? (
        <Alert message="無未完成且有備註的項目" type="success" showIcon />
      ) : (
        <Table<PMIncompleteItem>
          dataSource={items}
          rowKey={(r) => `${r.task_name}-${r.scheduled_date_full}`}
          columns={cols}
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
          size="small"
        />
      )}
    </Card>
  )
}

// ── 季度選擇卡片（Q1-Q4）──────────────────────────────────────────────────────
interface QuarterSummary {
  q:         number
  months:    string
  total:     number
  completed: number
  rate:      number | null
}

function deriveQuarterSummaries(matrix: PMYearMatrix): QuarterSummary[] {
  return [1, 2, 3, 4].map((q) => {
    const slice = matrix.months.slice((q - 1) * 3, q * 3)
    const total     = slice.reduce((s, m) => s + m.period_total,     0)
    const completed = slice.reduce((s, m) => s + m.period_completed, 0)
    return {
      q,
      months:    slice.map((m) => `${m.month}月`).join(' '),
      total,
      completed,
      rate: total > 0 ? Math.round((completed / total) * 1000) / 10 : null,
    }
  })
}

function QuarterSelectorCards({
  matrix,
  selectedQ,
  onSelect,
}: {
  matrix:    PMYearMatrix
  selectedQ: number
  onSelect:  (q: number) => void
}) {
  const summaries = deriveQuarterSummaries(matrix)
  return (
    <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
      {summaries.map(({ q, months, total, completed, rate }) => {
        const selected  = selectedQ === q
        const rateColor = rate === null ? '#999' : rate >= 80 ? '#52C41A' : rate >= 50 ? '#FAAD14' : '#FF4D4F'
        return (
          <Col span={6} key={q}>
            <Card
              size="small"
              hoverable
              onClick={() => onSelect(q)}
              style={{
                cursor:     'pointer',
                border:     selected ? '2px solid #4BA8E8' : '1px solid #d9d9d9',
                background: selected ? '#f0f8ff' : undefined,
                textAlign:  'center',
              }}
            >
              <Typography.Title level={4} style={{ margin: '0 0 2px', color: '#1B3A5C' }}>
                Q{q}
              </Typography.Title>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {months}
              </Typography.Text>
              <Divider style={{ margin: '8px 0' }} />
              <Row gutter={4} justify="center">
                <Col span={8}>
                  <div style={{ fontSize: 11, color: '#999' }}>項目</div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#1B3A5C' }}>{total || '—'}</div>
                </Col>
                <Col span={8}>
                  <div style={{ fontSize: 11, color: '#999' }}>完成</div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#52C41A' }}>{completed || '—'}</div>
                </Col>
                <Col span={8}>
                  <div style={{ fontSize: 11, color: '#999' }}>完成率</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: rateColor }}>
                    {fmtRate(rate)}
                  </div>
                </Col>
              </Row>
            </Card>
          </Col>
        )
      })}
    </Row>
  )
}

// ── 年度矩陣總表（12個月橫軸、指標縱軸）─────────────────────────────────────
const MATRIX_METRICS: {
  key: keyof PMYearMatrixMonth | '_sep1' | '_sep2'
  label: string
  isRate?: boolean
  isText?: boolean
}[] = [
  { key: 'prev_carry_over',         label: '上月累計未完成項目數' },
  { key: 'prev_resolved_in_period', label: '上月累計未完成項目，於本月結案數' },
  { key: 'carry_over_rate',         label: '累計項目完成率', isRate: true },
  { key: '_sep1',                   label: '' },
  { key: 'period_total',            label: '本月週期保養項目數' },
  { key: 'period_completed',        label: '本月週期保養完成數' },
  { key: 'period_rate',             label: '本月週期保養完成率', isRate: true },
  { key: '_sep2',                   label: '' },
  { key: 'incomplete_notes',        label: '未完成事項說明（原因/待協助事項）', isText: true },
]

function YearMatrixTable({ data }: { data: PMYearMatrix }) {
  const nowYear  = dayjs().year()
  const nowMonth = dayjs().month() + 1
  const isFuture = (month: number) =>
    data.year > nowYear || (data.year === nowYear && month > nowMonth)

  const pastMonths = data.months.filter((m) => !isFuture(m.month))
  const totalPrevCarryOver   = pastMonths.reduce((s, m) => s + m.prev_carry_over,         0)
  const totalPrevResolved    = pastMonths.reduce((s, m) => s + m.prev_resolved_in_period, 0)
  const totalPeriodTotal     = pastMonths.reduce((s, m) => s + m.period_total,            0)
  const totalPeriodCompleted = pastMonths.reduce((s, m) => s + m.period_completed,        0)
  const summaryValues: Record<string, unknown> = {
    prev_carry_over:         totalPrevCarryOver,
    prev_resolved_in_period: totalPrevResolved,
    carry_over_rate:         totalPrevCarryOver > 0
                               ? Math.round(totalPrevResolved / totalPrevCarryOver * 1000) / 10
                               : null,
    period_total:            totalPeriodTotal,
    period_completed:        totalPeriodCompleted,
    period_rate:             totalPeriodTotal > 0
                               ? Math.round(totalPeriodCompleted / totalPeriodTotal * 1000) / 10
                               : null,
    incomplete_notes:        '',
  }

  const futureCell = () => (
    <Typography.Text type="secondary" style={{ fontSize: 12 }}>—</Typography.Text>
  )

  const renderCell = (v: unknown, row: Record<string, unknown>, isTotal = false) => {
    if (row['_isSep']) return null
    const metric = MATRIX_METRICS.find((x) => x.key === row['_key'])
    if (!metric) return null
    if (metric.isText) {
      if (isTotal) return futureCell()
      const text = (v as string) || ''
      if (!text) return futureCell()
      return (
        <Tooltip title={<span style={{ whiteSpace: 'pre-wrap' }}>{text}</span>} placement="topLeft">
          <Typography.Text
            ellipsis
            style={{ fontSize: 11, display: 'block', maxWidth: 70, cursor: 'pointer' }}
          >
            {text}
          </Typography.Text>
        </Tooltip>
      )
    }
    if (metric.isRate) {
      const rate = v as number | null
      return (
        <Typography.Text
          style={{ fontSize: 12, color: rate === null ? '#999' : rate >= 80 ? '#52C41A' : rate >= 50 ? '#FAAD14' : '#FF4D4F' }}
        >
          {fmtRate(rate)}
        </Typography.Text>
      )
    }
    const num = v as number
    return (
      <Typography.Text style={{ fontSize: 12, color: num === 0 ? '#ccc' : undefined, fontWeight: isTotal ? 600 : undefined }}>
        {num === 0 ? '—' : num}
      </Typography.Text>
    )
  }

  const cols: ColumnsType<Record<string, unknown>> = [
    {
      title:     '',
      dataIndex: 'label',
      width:     230,
      fixed:     'left',
      onCell:    (row) => ({ style: { background: row['_isSep'] ? '#fafafa' : undefined } }),
      render:    (v: string) => (
        <Typography.Text style={{ fontSize: 12, fontWeight: v ? 500 : undefined }}>{v}</Typography.Text>
      ),
    },
    ...data.months.map((m) => ({
      title:     m.label,
      dataIndex: `m${m.month}`,
      width:     75,
      align:     'center' as const,
      onCell:    (row: Record<string, unknown>) => ({
        style: {
          background:    row['_isSep'] ? '#fafafa' : isFuture(m.month) ? '#fafafa' : undefined,
          verticalAlign: 'top',
          color:         isFuture(m.month) ? '#ccc' : undefined,
        },
      }),
      render: (v: unknown, row: Record<string, unknown>) => {
        if (row['_isSep']) return null
        if (isFuture(m.month)) return futureCell()
        return renderCell(v, row)
      },
    })),
    {
      title:     <Typography.Text strong style={{ color: '#1B3A5C' }}>合計</Typography.Text>,
      dataIndex: '_total',
      width:     80,
      align:     'center' as const,
      fixed:     'right' as const,
      onCell:    (row: Record<string, unknown>) => ({
        style: {
          background:    row['_isSep'] ? '#fafafa' : '#f6f8fc',
          verticalAlign: 'top',
          borderLeft:    '2px solid #d9e4f0',
        },
      }),
      render: (v: unknown, row: Record<string, unknown>) => renderCell(v, row, true),
    },
  ]

  const tableData: Record<string, unknown>[] = MATRIX_METRICS.map((metric) => {
    const isSep = metric.key === '_sep1' || metric.key === '_sep2'
    const row: Record<string, unknown> = {
      key:    metric.key,
      _key:   metric.key,
      label:  metric.label,
      _isSep: isSep,
      _total: isSep ? null : summaryValues[metric.key as string] ?? null,
    }
    data.months.forEach((m) => {
      row[`m${m.month}`] = isSep ? null : m[metric.key as keyof PMYearMatrixMonth]
    })
    return row
  })

  return (
    <Card
      title={<><BarChartOutlined /> {data.year} 年度全棟例行維護統計總表</>}
      size="small"
      style={{ marginBottom: 16 }}
    >
      <Table
        dataSource={tableData}
        columns={cols}
        pagination={false}
        size="small"
        scroll={{ x: 'max-content' }}
        bordered
      />
    </Card>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function FullBuildingMaintenancePage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats]     = useState<PMStats | null>(null)
  const [batches, setBatches] = useState<PMBatchListItem[]>([])
  const [dashYear,  setDashYear]  = useState(dayjs().format('YYYY'))
  const [dashMonth, setDashMonth] = useState(dayjs().month() + 1)
  const [year, setYear]       = useState(dayjs().format('YYYY'))
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  // ── 月統計 state ────────────────────────────────────────────────────────
  const [monthlyData,    setMonthlyData]    = useState<PMPeriodStats | null>(null)
  const [monthlyYear,    setMonthlyYear]    = useState(dayjs().year())
  const [monthlyMonth,   setMonthlyMonth]   = useState(dayjs().month() + 1)
  const [monthlyLoading, setMonthlyLoading] = useState(false)

  // ── 年度矩陣 state（共用 monthlyYear）───────────────────────────────────
  const [matrixData,    setMatrixData]    = useState<PMYearMatrix | null>(null)
  const [matrixLoading, setMatrixLoading] = useState(false)

  // ── 季統計 state ────────────────────────────────────────────────────────
  const [quarterlyData,          setQuarterlyData]          = useState<PMPeriodStats | null>(null)
  const [quarterlyMatrixData,    setQuarterlyMatrixData]    = useState<PMYearMatrix | null>(null)
  const [quarterlyYear,          setQuarterlyYear]          = useState(dayjs().year())
  const [quarterlyQuarter,       setQuarterlyQuarter]       = useState(Math.ceil((dayjs().month() + 1) / 3))
  const [quarterlyLoading,       setQuarterlyLoading]       = useState(false)
  const [quarterlyMatrixLoading, setQuarterlyMatrixLoading] = useState(false)

  // ── 年統計 state ────────────────────────────────────────────────────────
  const [yearlyData,    setYearlyData]    = useState<PMPeriodStats | null>(null)
  const [yearlyYear,    setYearlyYear]    = useState(dayjs().year())
  const [yearlyLoading, setYearlyLoading] = useState(false)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const s = await fetchFullBldgPMStats(dashYear, dashMonth)
      setStats(s)
    } catch {
      message.error('載入統計資料失敗')
    } finally {
      setLoading(false)
    }
  }, [dashYear, dashMonth])

  const loadBatches = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchFullBldgPMBatches(year)
      setBatches(data)
    } catch {
      message.error('載入批次清單失敗')
    } finally {
      setLoading(false)
    }
  }, [year])

  const loadMonthlyStats = useCallback(async () => {
    setMonthlyLoading(true)
    try {
      const data = await fetchFullBldgPMPeriodStats({ period_type: 'month', year: monthlyYear, month: monthlyMonth })
      setMonthlyData(data)
    } catch {
      message.error('載入月統計失敗')
    } finally {
      setMonthlyLoading(false)
    }
  }, [monthlyYear, monthlyMonth])

  const loadYearMatrix = useCallback(async () => {
    setMatrixLoading(true)
    try {
      const data = await fetchFullBldgPMYearMatrix(monthlyYear)
      setMatrixData(data)
    } catch {
      message.error('載入年度矩陣失敗')
    } finally {
      setMatrixLoading(false)
    }
  }, [monthlyYear])

  const loadQuarterlyMatrix = useCallback(async () => {
    setQuarterlyMatrixLoading(true)
    try {
      const data = await fetchFullBldgPMYearMatrix(quarterlyYear)
      setQuarterlyMatrixData(data)
    } catch {
      message.error('載入季度概覽失敗')
    } finally {
      setQuarterlyMatrixLoading(false)
    }
  }, [quarterlyYear])

  const loadQuarterlyStats = useCallback(async () => {
    setQuarterlyLoading(true)
    try {
      const data = await fetchFullBldgPMPeriodStats({ period_type: 'quarter', year: quarterlyYear, quarter: quarterlyQuarter })
      setQuarterlyData(data)
    } catch {
      message.error('載入季統計失敗')
    } finally {
      setQuarterlyLoading(false)
    }
  }, [quarterlyYear, quarterlyQuarter])

  const loadYearlyStats = useCallback(async () => {
    setYearlyLoading(true)
    try {
      const data = await fetchFullBldgPMPeriodStats({ period_type: 'year', year: yearlyYear })
      setYearlyData(data)
    } catch {
      message.error('載入年統計失敗')
    } finally {
      setYearlyLoading(false)
    }
  }, [yearlyYear])

  useEffect(() => { loadDashboard() }, [loadDashboard])

  useEffect(() => {
    if (activeTab === 'list')      loadBatches()
    if (activeTab === 'monthly')   { loadYearMatrix(); loadMonthlyStats() }
    if (activeTab === 'quarterly') { loadQuarterlyMatrix(); loadQuarterlyStats() }
    if (activeTab === 'yearly')    loadYearlyStats()
  }, [activeTab, loadBatches, loadMonthlyStats, loadQuarterlyStats, loadYearlyStats, loadYearMatrix, loadQuarterlyMatrix])

  useEffect(() => { if (activeTab === 'monthly')   loadYearMatrix() }, [loadYearMatrix])
  useEffect(() => { if (activeTab === 'quarterly') loadQuarterlyMatrix() }, [loadQuarterlyMatrix])
  useEffect(() => { if (activeTab === 'quarterly') loadQuarterlyStats() }, [loadQuarterlyStats])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncFullBldgPMFromRagic()
      message.success('同步完成')
      await loadDashboard()
      if (activeTab === 'list')      await loadBatches()
      if (activeTab === 'monthly')   { await loadYearMatrix(); await loadMonthlyStats() }
      if (activeTab === 'quarterly') { await loadQuarterlyMatrix(); await loadQuarterlyStats() }
      if (activeTab === 'yearly')    await loadYearlyStats()
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  const yearOptions = [2024, 2025, 2026, 2027].map(y => ({
    value: String(y),
    label: `${y} 年`,
  }))
  const yearNumOptions = [2024, 2025, 2026, 2027].map(y => ({
    value: y,
    label: `${y} 年`,
  }))
  const monthOptions = Array.from({ length: 12 }, (_, i) => ({
    value: i + 1,
    label: `${i + 1} 月`,
  }))

  // ── Dashboard Tab ──────────────────────────────────────────────────────────
  const kpi = stats?.current_kpi
  const catChartData = (stats?.category_stats ?? []).map(c => ({
    name:   c.category,
    已完成: c.completed,
    未完成: c.total - c.completed,
    完成率: c.rate,
  }))
  const pieData = (stats?.status_distribution ?? []).filter(s => s.count > 0)

  const DashboardTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Text type="secondary" style={{ marginRight: 4 }}>查詢月份：</Text>
        </Col>
        <Col>
          <Select
            value={dashYear}
            onChange={(v) => setDashYear(v)}
            options={yearOptions}
            style={{ width: 100 }}
          />
        </Col>
        <Col>
          <Select
            value={dashMonth}
            onChange={(v) => setDashMonth(v)}
            options={monthOptions}
            style={{ width: 85 }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadDashboard} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {[
          {
            title: `${dashYear}/${String(dashMonth).padStart(2, '0')} 有效項目`,
            value: kpi?.current_month_total ?? 0,
            suffix: '筆',
            icon: <ToolOutlined />,
            color: '#1B3A5C',
          },
          {
            title: `已完成（${kpi?.completion_rate ?? 0}%）`,
            value: kpi?.completed ?? 0,
            suffix: '筆',
            icon: <CheckCircleOutlined />,
            color: '#52C41A',
          },
          {
            title: '逾期件數',
            value: kpi?.overdue ?? 0,
            suffix: '筆',
            icon: <WarningOutlined />,
            color: '#C0392B',
          },
          {
            title: '異常待追蹤',
            value: kpi?.abnormal ?? 0,
            suffix: '筆',
            icon: <ExclamationCircleOutlined />,
            color: '#722ED1',
          },
        ].map((card) => (
          <Col flex={1} style={{ minWidth: 140 }} key={card.title}>
            <Card size="small" hoverable style={{ height: '100%' }}>
              <Statistic
                title={card.title}
                value={card.value}
                suffix={card.suffix}
                prefix={<span style={{ color: card.color }}>{card.icon}</span>}
                valueStyle={{ color: card.color, fontSize: 28 }}
              />
            </Card>
          </Col>
        ))}
        <Col flex={1} style={{ minWidth: 140 }}>
          <Card size="small" hoverable style={{ height: '100%' }}>
            <Statistic
              title="預估工時"
              value={Math.round((kpi?.planned_minutes ?? 0) / 60 * 10) / 10}
              suffix="小時"
              prefix={<span style={{ color: '#4BA8E8' }}><ClockCircleOutlined /></span>}
              valueStyle={{ color: '#4BA8E8', fontSize: 28 }}
            />
          </Card>
        </Col>
        <Col flex={1} style={{ minWidth: 140 }}>
          <Card size="small" hoverable style={{ height: '100%' }}>
            <Statistic
              title="保養時間"
              value={Math.round((kpi?.actual_minutes ?? 0) / 60 * 10) / 10}
              suffix="小時"
              prefix={<span style={{ color: '#52C41A' }}><ClockCircleOutlined /></span>}
              valueStyle={{ color: '#52C41A', fontSize: 28 }}
            />
          </Card>
        </Col>
      </Row>

      {kpi && kpi.current_month_total > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row align="middle" gutter={16}>
            <Col flex="100px"><Text strong>{dashYear}/{String(dashMonth).padStart(2, '0')} 完成率</Text></Col>
            <Col flex="auto">
              <Progress
                percent={kpi.completion_rate}
                strokeColor={{ from: '#4BA8E8', to: '#52C41A' }}
                format={(p) => `${p}%（${kpi.completed}/${kpi.total}）`}
              />
            </Col>
          </Row>
        </Card>
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={14}>
          <Card
            title={<><BarChartOutlined /> 各類別完成率</>}
            size="small"
            style={{ height: 300 }}
          >
            {catChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={catChartData} layout="vertical" margin={{ left: 20, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 'dataMax']} />
                  <YAxis type="category" dataKey="name" width={60} tick={{ fontSize: 12 }} />
                  <RcTooltip />
                  <Bar dataKey="已完成" stackId="a" fill="#52C41A" />
                  <Bar dataKey="未完成" stackId="a" fill="#FF7875" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', paddingTop: 80, color: '#999' }}>暫無資料</div>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title="狀態分布" size="small" style={{ height: 300 }}>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="count"
                    nameKey="label"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    label={({ label, count }) => `${label}:${count}`}
                    labelLine={false}
                  >
                    {pieData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Pie>
                  <RcTooltip formatter={(v, n) => [v, n]} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', paddingTop: 80, color: '#999' }}>暫無資料</div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={<><WarningOutlined style={{ color: '#C0392B' }} /> 逾期項目（Top 10）</>}
            size="small"
          >
            {(stats?.overdue_items ?? []).length === 0 ? (
              <Alert message="該月無逾期項目" type="success" showIcon />
            ) : (
              <Table<PMItem>
                dataSource={stats?.overdue_items ?? []}
                rowKey="ragic_id"
                size="small"
                pagination={false}
                columns={[
                  { title: '項目', dataIndex: 'task_name', ellipsis: true },
                  { title: '類別', dataIndex: 'category', width: 70 },
                  {
                    title: '排定日',
                    dataIndex: 'scheduled_date',
                    width: 75,
                    render: (v) => <Text type="danger">{v || '—'}</Text>,
                  },
                  {
                    title: '',
                    width: 50,
                    render: (_, row) => (
                      <Button
                        type="link"
                        size="small"
                        icon={<RightOutlined />}
                        onClick={() => navigate(`/mall/full-building-maintenance/${row.batch_ragic_id}`)}
                      />
                    ),
                  },
                ]}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title={<><ClockCircleOutlined style={{ color: '#FAAD14' }} /> 待執行項目（排定中）</>}
            size="small"
          >
            {(stats?.upcoming_items ?? []).length === 0 ? (
              <Alert message="該月無待執行項目" type="info" showIcon />
            ) : (
              <Table<PMItem>
                dataSource={stats?.upcoming_items ?? []}
                rowKey="ragic_id"
                size="small"
                pagination={false}
                columns={[
                  { title: '項目', dataIndex: 'task_name', ellipsis: true },
                  { title: '排定日', dataIndex: 'scheduled_date', width: 75 },
                  { title: '執行人員', dataIndex: 'executor_name', width: 80, ellipsis: true },
                  {
                    title: '',
                    width: 50,
                    render: (_, row) => (
                      <Button
                        type="link"
                        size="small"
                        icon={<RightOutlined />}
                        onClick={() => navigate(`/mall/full-building-maintenance/${row.batch_ragic_id}`)}
                      />
                    ),
                  },
                ]}
              />
            )}
          </Card>
        </Col>
      </Row>

      {stats?.current_batch && (
        <Card size="small" style={{ marginTop: 16 }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Space>
                <Text strong>{stats.current_batch.journal_no}</Text>
                <Text type="secondary">（{stats.current_batch.period_month}）</Text>
                <Tag color={BATCH_STATUS_CFG[deriveBatchStatus(stats.current_kpi!)].color}>
                  {BATCH_STATUS_CFG[deriveBatchStatus(stats.current_kpi!)].label}
                </Tag>
              </Space>
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<RightOutlined />}
                onClick={() => navigate(`/mall/full-building-maintenance/${stats.current_batch!.ragic_id}`)}
                style={{ background: '#1B3A5C' }}
              >
                查看本月明細
              </Button>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  )

  // ── 每月維護統計 Tab ──────────────────────────────────────────────────────
  const MonthlyStatsTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Typography.Text type="secondary" style={{ marginRight: 4 }}>年度：</Typography.Text>
        </Col>
        <Col>
          <Select
            value={monthlyYear}
            onChange={(v) => { setMonthlyYear(v) }}
            options={yearNumOptions}
            style={{ width: 100 }}
          />
        </Col>
        <Col>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { loadYearMatrix(); loadMonthlyStats() }}
            loading={matrixLoading || monthlyLoading}
          >
            重新整理
          </Button>
        </Col>
      </Row>

      {matrixLoading ? (
        <Card size="small" style={{ marginBottom: 16, textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入年度矩陣中…</Typography.Text>
        </Card>
      ) : matrixData ? (
        <YearMatrixTable data={matrixData} />
      ) : (
        <Alert message="尚未載入年度矩陣，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      <Divider orientation="left" style={{ fontSize: 13, color: '#666' }}>
        單月鑽取
      </Divider>
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Typography.Text type="secondary" style={{ marginRight: 4 }}>查詢月份：</Typography.Text>
        </Col>
        <Col>
          <Select
            value={monthlyMonth}
            onChange={(v) => setMonthlyMonth(v)}
            options={monthOptions}
            style={{ width: 85 }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadMonthlyStats} loading={monthlyLoading}>
            查詢
          </Button>
        </Col>
      </Row>

      {monthlyData ? (
        <>
          <PeriodKpiCards data={monthlyData} prevLabel="上月" currLabel="本月" />
          <IncompleteTable items={monthlyData.incomplete_items} />
        </>
      ) : (
        <Alert message="請選擇月份後點擊查詢" type="info" showIcon />
      )}
    </div>
  )

  // ── 每季維護統計 Tab ──────────────────────────────────────────────────────
  const QuarterlyStatsTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Typography.Text type="secondary" style={{ marginRight: 4 }}>年度：</Typography.Text>
        </Col>
        <Col>
          <Select
            value={quarterlyYear}
            onChange={(v) => setQuarterlyYear(v)}
            options={yearNumOptions}
            style={{ width: 100 }}
          />
        </Col>
        <Col>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { loadQuarterlyMatrix(); loadQuarterlyStats() }}
            loading={quarterlyMatrixLoading || quarterlyLoading}
          >
            重新整理
          </Button>
        </Col>
      </Row>

      {quarterlyMatrixLoading ? (
        <Card size="small" style={{ marginBottom: 16, textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入季度概覽中…</Typography.Text>
        </Card>
      ) : quarterlyMatrixData ? (
        <QuarterSelectorCards
          matrix={quarterlyMatrixData}
          selectedQ={quarterlyQuarter}
          onSelect={(q) => { setQuarterlyQuarter(q) }}
        />
      ) : (
        <Alert message="尚未載入季度概覽，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      <Divider orientation="left" style={{ fontSize: 13, color: '#666' }}>
        Q{quarterlyQuarter}（{[1,4,7,10][quarterlyQuarter-1]}～{[3,6,9,12][quarterlyQuarter-1]}月）詳細統計
      </Divider>

      {quarterlyLoading ? (
        <Card size="small" style={{ textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入中…</Typography.Text>
        </Card>
      ) : quarterlyData ? (
        <>
          <PeriodKpiCards data={quarterlyData} prevLabel="上季" currLabel="本季" />
          <IncompleteTable items={quarterlyData.incomplete_items} />
        </>
      ) : (
        <Alert message="請選擇季度後點擊重新整理" type="info" showIcon />
      )}
    </div>
  )

  // ── 每年維護統計 Tab ──────────────────────────────────────────────────────
  const YearlyStatsTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Typography.Text type="secondary" style={{ marginRight: 4 }}>查詢年度：</Typography.Text>
        </Col>
        <Col>
          <Select
            value={yearlyYear}
            onChange={(v) => setYearlyYear(v)}
            options={yearNumOptions}
            style={{ width: 100 }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadYearlyStats} loading={yearlyLoading}>
            重新整理
          </Button>
        </Col>
      </Row>

      {yearlyData ? (
        <>
          <PeriodKpiCards data={yearlyData} prevLabel="上年" currLabel="本年" />
          <SubBreakdownTable rows={yearlyData.sub_period_breakdown} title="本年季度分布（Q1～Q4）" />
          <IncompleteTable items={yearlyData.incomplete_items} />
        </>
      ) : (
        <Alert message="尚未載入資料，請選擇年度後點擊重新整理" type="info" showIcon />
      )}
    </div>
  )

  // ── 批次清單 Tab ──────────────────────────────────────────────────────────
  const batchColumns: ColumnsType<PMBatchListItem> = [
    {
      title: '保養單號',
      dataIndex: ['batch', 'journal_no'],
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, fontWeight: 600 }}
          onClick={() => navigate(`/mall/full-building-maintenance/${row.batch.ragic_id}`)}>
          {v}
        </Button>
      ),
    },
    {
      title: '保養月份',
      dataIndex: ['batch', 'period_month'],
      width: 100,
      sorter: (a, b) => a.batch.period_month.localeCompare(b.batch.period_month),
    },
    {
      title: '批次狀態',
      width: 100,
      render: (_, row) => {
        const s = deriveBatchStatus(row.kpi)
        const cfg = BATCH_STATUS_CFG[s]
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '完成率',
      width: 180,
      render: (_, row) => {
        const { completion_rate, completed, total } = row.kpi
        return (
          <div>
            <Progress
              percent={completion_rate}
              size="small"
              strokeColor={{ from: '#4BA8E8', to: '#52C41A' }}
              format={() => `${completion_rate}%`}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {completed} / {total} 已完成/全部
            </Text>
          </div>
        )
      },
    },
    {
      title: '逾期',
      dataIndex: ['kpi', 'overdue'],
      width: 70,
      render: (v) => v > 0 ? <Badge count={v} color="#C0392B" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '異常',
      dataIndex: ['kpi', 'abnormal'],
      width: 70,
      render: (v) => v > 0 ? <Badge count={v} color="#722ED1" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '最後更新',
      dataIndex: ['batch', 'ragic_updated_at'],
      width: 140,
      render: (v) => v || '—',
    },
    {
      title: '操作',
      width: 100,
      render: (_, row) => (
        <Button
          type="primary"
          size="small"
          icon={<RightOutlined />}
          style={{ background: '#1B3A5C' }}
          onClick={() => navigate(`/mall/full-building-maintenance/${row.batch.ragic_id}`)}
        >
          查看明細
        </Button>
      ),
    },
  ]

  const ListTab = (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }}>
        <Col>
          <Select
            value={year}
            onChange={setYear}
            options={yearOptions}
            style={{ width: 110 }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadBatches} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>
      <Table<PMBatchListItem>
        dataSource={batches}
        rowKey={(r) => r.batch.ragic_id}
        columns={batchColumns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無保養批次資料' }}
      />
    </div>
  )

  // ── 頁面渲染 ──────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 4px' }}>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.mall },
          { title: NAV_PAGE.fullBuildingMaintenance },
        ]}
      />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <ShopOutlined /> {NAV_PAGE.fullBuildingMaintenance}
          </Title>
        </Col>
        <Col>
          <Button
            icon={<SyncOutlined spin={syncing} />}
            loading={syncing}
            onClick={handleSync}
          >
            同步 Ragic
          </Button>
        </Col>
      </Row>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'dashboard', label: 'Dashboard', children: DashboardTab },
          {
            key: 'monthly',
            label: <span><CalendarOutlined /> 每月維護</span>,
            children: MonthlyStatsTab,
          },
          {
            key: 'quarterly',
            label: <span><LineChartOutlined /> 每季維護</span>,
            children: QuarterlyStatsTab,
          },
          {
            key: 'yearly',
            label: <span><BarChartOutlined /> 每年維護</span>,
            children: YearlyStatsTab,
          },
          { key: 'list', label: '批次清單', children: ListTab },
        ]}
      />
    </div>
  )
}
