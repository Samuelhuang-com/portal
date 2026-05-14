/**
 * 週期保養表主頁
 *
 * Tab 1「主管儀表板」：KPI 四卡 + 類別 Bar 圖 + 狀態 Donut 圖 + 逾期/即將到期預警
 * Tab 2「批次清單」：保養批次列表，含進度條、狀態標籤、操作入口
 * Tab 3「每月維護」：月統計（上月累計 / 本月完成 / 未完成說明）
 * Tab 4「每季維護」：季統計（上季累計 / 本季完成 / 月份分布）
 * Tab 5「每年維護」：年統計（上年累計 / 本年完成 / Q1-Q4 分布）
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Progress, Alert, Select,
  message, Tooltip, Badge, Divider, Modal, Spin,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, ToolOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, RightOutlined, BarChartOutlined,
  CalendarOutlined, LineChartOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import { fetchPMStats, fetchPMBatches, fetchPMPeriodStats, fetchPMYearMatrix, fetchPMCalendar, fetchPMBatchDetail, fetchPMMatrixItems, fetchPMCatalog } from '@/api/periodicMaintenance'
import type { PMCatalogItem } from '@/api/periodicMaintenance'
import type { PMMatrixMetric, PMMatrixItem } from '@/api/periodicMaintenance'
import type { PMStats, PMBatchListItem, PMItem, PMItemStatus, PMPeriodStats, PMIncompleteItem, PMSubPeriodBreakdown, PMYearMatrix, PMYearMatrixMonth } from '@/types/periodicMaintenance'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'

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
  // 全部項目（含非本月）都完成 → 已完成
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
  prevLabel: string   // "上月" / "上季" / "上年"
  currLabel: string   // "本月" / "本季" / "本年"
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

// ── 季度選擇卡片（Q1-Q4，加總各季 3 個月數值）────────────────────────────────
interface QuarterSummary {
  q:          number
  months:     string    // "1月 2月 3月"
  total:      number
  completed:  number
  rate:       number | null
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

// ── 年度矩陣總表（12個月橫軸、指標縱軸）────────────────────────────────────────
const MATRIX_METRICS: {
  key: keyof PMYearMatrixMonth | '_sep1' | '_sep2'
  label: string
  isRate?: boolean
  isText?: boolean
  tooltip?: string
}[] = [
  { key: 'prev_carry_over',         label: '截至上月底累計未結案數',
    tooltip: '前期結轉未完成數：截至上月底，所有尚未結案的週期保養項目累計總數（含更早期遞延未完成項目）。' },
  { key: 'prev_resolved_in_period', label: '其中本月已結案數',
    tooltip: '本月已結案數：上列「截至上月底累計未結案數」中，在本月內完成並結案的項目數。\n完成率（累計項目完成率）＝ 已結案數 ÷ 累計未結案數 × 100%。' },
  { key: 'carry_over_rate',         label: '累計項目完成率', isRate: true },
  { key: '_sep1',                   label: '' },
  { key: 'period_total',            label: '本月週期保養項目數' },
  { key: 'period_completed',        label: '本月週期保養完成數' },
  { key: 'period_rate',             label: '本月週期保養完成率', isRate: true },
  { key: '_sep2',                   label: '' },
  { key: 'incomplete_notes',        label: '未完成事項說明（原因/待協助事項）', isText: true },
]

function YearMatrixTable({ data, frequencyType, onCellClick }: { data: PMYearMatrix; frequencyType?: string; onCellClick?: (year: number, month: number, metric: PMMatrixMetric, monthLabel: string) => void }) {
  // ── 判斷尚未發生的月份（年份相同則 month > 本月；未來年份整年都是未來）──────
  const nowYear  = dayjs().year()
  const nowMonth = dayjs().month() + 1   // 1-based
  const isFuture = (month: number) =>
    data.year > nowYear || (data.year === nowYear && month > nowMonth)

  // ── 合計欄：只加總「已發生」月份，完成率從加總數重算 ──────────────────────
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

  // ── 通用 cell renderer（月欄 + 合計欄共用）────────────────────────────────
  const futureCell = () => (
    <Typography.Text type="secondary" style={{ fontSize: 18 }}>—</Typography.Text>
  )

  // 可點擊 metric key 對照表
  const CLICKABLE_METRIC_MAP: Record<string, PMMatrixMetric> = {
    prev_carry_over:         'prev_carry_over',
    prev_resolved_in_period: 'prev_resolved',
    period_total:            'period_total',
    period_completed:        'period_completed',
  }

  const renderCell = (v: unknown, row: Record<string, unknown>, isTotal = false, monthNum = 0, monthLabel = '') => {
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
            style={{ fontSize: 17, display: 'block', maxWidth: 90, cursor: 'pointer' }}
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
          style={{ fontSize: 18, color: rate === null ? '#999' : rate >= 80 ? '#52C41A' : rate >= 50 ? '#FAAD14' : '#FF4D4F' }}
        >
          {fmtRate(rate)}
        </Typography.Text>
      )
    }
    const num = v as number
    const matricMetric = CLICKABLE_METRIC_MAP[row['_key'] as string]
    const isClickable = !isTotal && num > 0 && !!matricMetric && !!onCellClick
    if (isClickable) {
      return (
        <Typography.Text
          style={{ fontSize: 18, fontWeight: isTotal ? 600 : undefined, color: '#1677ff', textDecoration: 'underline', cursor: 'pointer' }}
          onClick={() => onCellClick!(data.year, monthNum, matricMetric, monthLabel)}
        >
          {num}
        </Typography.Text>
      )
    }
    return (
      <Typography.Text style={{ fontSize: 18, color: num === 0 ? '#ccc' : undefined, fontWeight: isTotal ? 600 : undefined }}>
        {num === 0 ? '—' : num}
      </Typography.Text>
    )
  }

  // 建立欄位定義：最左側 label 欄 + 12 個月欄 + 合計欄
  const cols: ColumnsType<Record<string, unknown>> = [
    {
      title:     '',
      dataIndex: 'label',
      width:     310,
      fixed:     'left',
      onCell:    (row) => ({ style: { background: row['_isSep'] ? '#fafafa' : undefined } }),
      render:    (v: string, row) => {
        const metric = MATRIX_METRICS.find((x) => x.key === row['_key'])
        const tip = metric?.tooltip
        return (
          <Space size={4}>
            <Typography.Text style={{ fontSize: 18, fontWeight: v ? 500 : undefined }}>
              {v}
            </Typography.Text>
            {tip && (
              <Tooltip title={<span style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{tip}</span>} placement="right">
                <span style={{
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  width: 18, height: 18, borderRadius: '50%',
                  background: '#1677ff', color: '#fff',
                  fontSize: 12, fontWeight: 700, cursor: 'help', lineHeight: '18px',
                }}>?</span>
              </Tooltip>
            )}
          </Space>
        )
      },
    },
    ...data.months.map((m) => ({
      title:     <span style={{ fontSize: 18 }}>{m.label}</span>,
      dataIndex: `m${m.month}`,
      width:     90,
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
        return renderCell(v, row, false, m.month, m.label)
      },
    })),
    // 合計欄（僅加總已發生月份）
    {
      title:     <Typography.Text strong style={{ color: '#1B3A5C', fontSize: 18 }}>合計</Typography.Text>,
      dataIndex: '_total',
      width:     100,
      align:     'center' as const,
      fixed:     'right' as const,
      onCell:    (row: Record<string, unknown>) => ({
        style: {
          background:  row['_isSep'] ? '#fafafa' : '#f6f8fc',
          verticalAlign: 'top',
          borderLeft: '2px solid #d9e4f0',
        },
      }),
      render: (v: unknown, row: Record<string, unknown>) => renderCell(v, row, true),
    },
  ]

  // 轉置：每個 metric 一行，12個月的值當欄位值，最後加 _total
  const tableData: Record<string, unknown>[] = MATRIX_METRICS.map((metric) => {
    const isSep = metric.key === '_sep1' || metric.key === '_sep2'
    const row: Record<string, unknown> = {
      key:     metric.key,
      _key:    metric.key,
      label:   metric.label,
      _isSep:  isSep,
      _total:  isSep ? null : summaryValues[metric.key as string] ?? null,
    }
    data.months.forEach((m) => {
      row[`m${m.month}`] = isSep ? null : m[metric.key as keyof PMYearMatrixMonth]
    })
    return row
  })

  return (
    <Card
      title={<><BarChartOutlined /> {data.year} 年度週期保養統計總表</>}
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
        rowClassName={(row) => row['_isSep'] ? '' : ''}
      />
    </Card>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function PeriodicMaintenancePage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats] = useState<PMStats | null>(null)
  const [batches, setBatches] = useState<PMBatchListItem[]>([])
  // Dashboard 篩選：年月（預設當月）
  const [dashYear,  setDashYear]  = useState(dayjs().format('YYYY'))
  const [dashMonth, setDashMonth] = useState(dayjs().month() + 1)   // 1-based
  // 批次清單篩選：年
  const [year, setYear] = useState(dayjs().format('YYYY'))
  const [loading, setLoading] = useState(false)
  // 月曆格 state
  const [calRows,   setCalRows]   = useState<CalendarRow[]>([])
  const [calMaxDay, setCalMaxDay] = useState(31)
  // 每月保養表 state
  const [formItems,   setFormItems]   = useState<PMItem[]>([])
  const [formLoading, setFormLoading] = useState(false)
  const [formYear,    setFormYear]    = useState(dayjs().format('YYYY'))
  const [formMonth,   setFormMonth]   = useState(dayjs().month() + 1)

  // ── 月統計 state ────────────────────────────────────────────────────────
  const [monthlyData,  setMonthlyData]  = useState<PMPeriodStats | null>(null)
  const [monthlyYear,  setMonthlyYear]  = useState(dayjs().year())
  const [monthlyMonth, setMonthlyMonth] = useState(dayjs().month() + 1)
  const [monthlyLoading, setMonthlyLoading] = useState(false)

  // ── 年度矩陣 state（共用 monthlyYear 選擇器）────────────────────────────
  const [matrixData,    setMatrixData]    = useState<PMYearMatrix | null>(null)
  const [matrixLoading, setMatrixLoading] = useState(false)

  // ── 季統計 state ────────────────────────────────────────────────────────
  const [quarterlyData,        setQuarterlyData]        = useState<PMPeriodStats | null>(null)
  const [quarterlyMatrixData,  setQuarterlyMatrixData]  = useState<PMYearMatrix | null>(null)
  const [yearlyMatrixData,     setYearlyMatrixData]     = useState<PMYearMatrix | null>(null)
  const [yearlyMatrixLoading,  setYearlyMatrixLoading]  = useState(false)
  const [quarterlyYear,        setQuarterlyYear]        = useState(dayjs().year())
  const [quarterlyQuarter,     setQuarterlyQuarter]     = useState(Math.ceil((dayjs().month() + 1) / 3))
  const [quarterlyLoading,     setQuarterlyLoading]     = useState(false)
  const [quarterlyMatrixLoading, setQuarterlyMatrixLoading] = useState(false)

  // ── 年統計 state ────────────────────────────────────────────────────────
  const [yearlyData,    setYearlyData]    = useState<PMPeriodStats | null>(null)
  const [yearlyYear,    setYearlyYear]    = useState(dayjs().year())
  const [yearlyLoading, setYearlyLoading] = useState(false)

  // ── 保養項目目錄 Modal ─────────────────────────────────────────────────────
  const [catalogOpen,        setCatalogOpen]       = useState(false)
  const [catalogFreqType,    setCatalogFreqType]   = useState<'monthly' | 'quarterly' | 'yearly'>('monthly')
  const [catalogItems,       setCatalogItems]      = useState<PMCatalogItem[]>([])
  const [catalogLoading,     setCatalogLoading]    = useState(false)

  const openCatalogModal = useCallback(async (freqType: 'monthly' | 'quarterly' | 'yearly') => {
    setCatalogFreqType(freqType)
    setCatalogOpen(true)
    setCatalogLoading(true)
    try {
      const res = await fetchPMCatalog(freqType)
      setCatalogItems(res.items)
    } catch {
      setCatalogItems([])
    } finally {
      setCatalogLoading(false)
    }
  }, [])

  // ── 矩陣格明細 Modal ───────────────────────────────────────────────────────
  const [modalOpen,       setModalOpen]       = useState(false)
  const [modalYear,       setModalYear]       = useState(0)
  const [modalMonth,      setModalMonth]      = useState(0)
  const [modalMetric,     setModalMetric]     = useState<PMMatrixMetric>('period_total')
  const [modalFreqType,   setModalFreqType]   = useState<string>('')
  const [modalMonthLabel, setModalMonthLabel] = useState('')

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const [s, calData] = await Promise.all([
        fetchPMStats(dashYear, dashMonth),
        fetchPMCalendar(parseInt(dashYear), dashMonth).catch(() => null),
      ])
      setStats(s)
      if (calData) {
        setCalMaxDay(calData.max_day)
        setCalRows(calData.rows)
      }
    } catch {
      message.error('載入統計資料失敗')
    } finally {
      setLoading(false)
    }
  }, [dashYear, dashMonth])

  const loadBatches = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchPMBatches(year)
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
      const data = await fetchPMPeriodStats({ period_type: 'month', year: monthlyYear, month: monthlyMonth, frequency_type: 'monthly' })
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
      const data = await fetchPMYearMatrix(monthlyYear, 'monthly')
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
      const data = await fetchPMYearMatrix(quarterlyYear, 'quarterly')
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
      const data = await fetchPMPeriodStats({ period_type: 'quarter', year: quarterlyYear, quarter: quarterlyQuarter, frequency_type: 'quarterly' })
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
      const data = await fetchPMPeriodStats({ period_type: 'year', year: yearlyYear, frequency_type: 'yearly' })
      setYearlyData(data)
    } catch {
      message.error('載入年統計失敗')
    } finally {
      setYearlyLoading(false)
    }
  }, [yearlyYear])

  const loadYearlyMatrix = useCallback(async () => {
    setYearlyMatrixLoading(true)
    try {
      const data = await fetchPMYearMatrix(yearlyYear, 'yearly')
      setYearlyMatrixData(data)
    } catch {
      message.error('載入年度矩陣失敗')
    } finally {
      setYearlyMatrixLoading(false)
    }
  }, [yearlyYear])

  const openDetailModal = (freqType: string, year: number, month: number, metric: PMMatrixMetric, monthLabel: string) => {
    setModalFreqType(freqType)
    setModalYear(year)
    setModalMonth(month)
    setModalMetric(metric)
    setModalMonthLabel(monthLabel)
    setModalOpen(true)
  }

  // dashYear / dashMonth 改變時自動重新載入（依賴注入於 loadDashboard 的 useCallback）
  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  useEffect(() => {
    if (activeTab === 'list')      loadBatches()
    if (activeTab === 'monthly')   { loadYearMatrix(); loadMonthlyStats() }
    if (activeTab === 'quarterly') { loadQuarterlyMatrix(); loadQuarterlyStats() }
    if (activeTab === 'yearly')    { loadYearlyMatrix(); loadYearlyStats() }
  }, [activeTab, loadBatches, loadMonthlyStats, loadQuarterlyStats, loadYearlyStats, loadYearMatrix, loadQuarterlyMatrix, loadYearlyMatrix])

  // year 改變時自動重算矩陣
  useEffect(() => {
    if (activeTab === 'monthly')   loadYearMatrix()
  }, [loadYearMatrix])
  useEffect(() => {
    if (activeTab === 'quarterly') loadQuarterlyMatrix()
  }, [loadQuarterlyMatrix])

  // 季度卡片點擊後自動載入 detail（quarterlyQuarter 改變時）
  useEffect(() => {
    if (activeTab === 'quarterly') loadQuarterlyStats()
  }, [loadQuarterlyStats])

  // 每月保養表：依年/月獨立載入批次項目（與 Dashboard 無關）
  const loadFormItems = useCallback(async () => {
    setFormLoading(true)
    try {
      const batchList = await fetchPMBatches(formYear)
      const targetPM  = `${formYear}/${String(formMonth).padStart(2, '0')}`
      const found     = batchList.find((b) => b.batch.period_month === targetPM)
      if (!found) { setFormItems([]); return }
      const detail = await fetchPMBatchDetail(found.batch.ragic_id, { currentMonthOnly: true })
      setFormItems(detail.items)
    } catch {
      setFormItems([])
    } finally {
      setFormLoading(false)
    }
  }, [formYear, formMonth])

  useEffect(() => {
    loadFormItems()
  }, [loadFormItems])

  // ── 年份 / 月份 / 季度 選項 ──────────────────────────────────────────────────
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
  const quarterOptions = [1, 2, 3, 4].map(q => ({
    value: q,
    label: `Q${q}（${(q - 1) * 3 + 1}～${q * 3}月）`,
  }))

  // ── Dashboard Tab ──────────────────────────────────────────────────────────
  const kpi = stats?.current_kpi
  const catChartData = (stats?.category_stats ?? []).map(c => ({
    name:      c.category,
    已完成:    c.completed,
    未完成:    c.total - c.completed,
    完成率:    c.rate,
  }))
  const pieData = (stats?.status_distribution ?? []).filter(s => s.count > 0)

  const DashboardTab = (
    <div>
      {/* 年月篩選列 */}
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

      {/* KPI 卡片 */}
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

      {/* 完成率進度條 */}
      {kpi && kpi.current_month_total > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row align="middle" gutter={16}>
            <Col flex="100px">
              <Text strong>{dashYear}/{String(dashMonth).padStart(2, '0')} 完成率</Text>
            </Col>
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

      {/* 圖表區 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {/* 類別完成率 Bar */}
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
                  <Legend />
                  <Bar dataKey="已完成" stackId="a" fill="#52C41A" />
                  <Bar dataKey="未完成" stackId="a" fill="#FF7875" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', paddingTop: 80, color: '#999' }}>暫無資料</div>
            )}
          </Card>
        </Col>

        {/* 狀態分布 Donut */}
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

      {/* 預警區 */}
      <Row gutter={[16, 16]}>
        {/* 逾期清單 */}
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
                        onClick={() => navigate(`/hotel/periodic-maintenance/${row.batch_ragic_id}`)}
                      />
                    ),
                  },
                ]}
              />
            )}
          </Card>
        </Col>

        {/* 即將到期 */}
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
                        onClick={() => navigate(`/hotel/periodic-maintenance/${row.batch_ragic_id}`)}
                      />
                    ),
                  },
                ]}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 本月批次快速入口 */}
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
                onClick={() => navigate(`/hotel/periodic-maintenance/${stats.current_batch!.ragic_id}`)}
                style={{ background: '#1B3A5C' }}
              >
                查看本月明細
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 月曆格：類別 × 日期 */}
      <Card
        size="small"
        style={{ marginTop: 16 }}
        title={
          <Space>
            <CalendarOutlined />
            <Text strong>飯店例行維護每日狀況</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              （{dashYear}/{String(dashMonth).padStart(2, '0')}）
            </Text>
          </Space>
        }
        loading={loading}
      >
        {calRows.length > 0 ? (
          <MonthlyCalendarGrid
            year={parseInt(dashYear)}
            month={dashMonth}
            maxDay={calMaxDay}
            rows={calRows}
            rowHeaderLabel="保養類別"
          />
        ) : (
          <Text type="secondary">尚無月曆資料</Text>
        )}
      </Card>
    </div>
  )

  // ── 每月保養表 Tab ────────────────────────────────────────────────────────
  const FORM_CAT_ORDER = ['水電', '空調', '機修', '裝修', '弱電']

  type FormRow = PMItem & { _catRowSpan: number }

  const buildFormRows = (items: PMItem[]): FormRow[] => {
    const buckets: Record<string, PMItem[]> = {}
    for (const c of FORM_CAT_ORDER) buckets[c] = []
    for (const item of items) {
      const k = FORM_CAT_ORDER.includes(item.category) ? item.category : '其他'
      if (!buckets[k]) buckets[k] = []
      buckets[k].push(item)
    }
    const rows: FormRow[] = []
    for (const cat of [...FORM_CAT_ORDER, '其他']) {
      const catItems = buckets[cat] ?? []
      catItems.forEach((item, i) =>
        rows.push({ ...item, _catRowSpan: i === 0 ? catItems.length : 0 }),
      )
    }
    return rows
  }

  const formColumns: ColumnsType<FormRow> = [
    {
      title:     '序',
      dataIndex: 'seq_no',
      width:     38,
      render:    (v) => <Text style={{ fontSize: 11 }}>{v}</Text>,
    },
    {
      title:     '類別',
      dataIndex: 'category',
      width:     52,
      onCell:    (row) => ({ rowSpan: row._catRowSpan }),
      render:    (v) => <Text strong style={{ fontSize: 12, color: '#1B3A5C' }}>{v}</Text>,
    },
    {
      title:     '頻率',
      dataIndex: 'frequency',
      width:     52,
      render:    (v) => v
        ? <Tag style={{ fontSize: 10 }}>{v}</Tag>
        : <Text type="secondary">—</Text>,
    },
    {
      title:  '項目 / 區域',
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Text style={{ fontSize: 12 }}>{row.task_name || '—'}</Text>
          {row.location && (
            <Text type="secondary" style={{ fontSize: 11 }}>{row.location}</Text>
          )}
        </Space>
      ),
    },
    {
      title:     '預估(分)',
      dataIndex: 'estimated_minutes',
      width:     66,
      align:     'center',
      render:    (v) => <Text style={{ fontSize: 12 }}>{v > 0 ? v : '—'}</Text>,
    },
    {
      title:     '排定日期',
      dataIndex: 'scheduled_date',
      width:     78,
      render:    (v) => <Text style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title:     '排定人員',
      dataIndex: 'scheduler_name',
      width:     78,
      render:    (v) => <Text style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title:     '執行人員',
      dataIndex: 'executor_name',
      width:     78,
      render:    (v) => <Text style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title:     '狀態',
      dataIndex: 'status',
      width:     72,
      render:    (v: PMItemStatus) => {
        const cfg = STATUS_CFG[v] ?? { label: v, tagColor: 'default' }
        return <Tag color={cfg.tagColor} style={{ fontSize: 11 }}>{cfg.label}</Tag>
      },
    },
    {
      title:  '備註',
      render: (_, row) => (
        <Space direction="vertical" size={2}>
          {row.result_note && <Text style={{ fontSize: 11 }}>{row.result_note}</Text>}
          {row.abnormal_flag && <Tag color="error" style={{ fontSize: 10 }}>異常</Tag>}
        </Space>
      ),
    },
  ]

  const formRows = buildFormRows(formItems)

  const FormTab = (
    <div>
      {/* 篩選列 */}
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Text type="secondary" style={{ marginRight: 4 }}>查詢月份：</Text>
        </Col>
        <Col>
          <Select
            value={formYear}
            onChange={(v) => setFormYear(v)}
            options={yearOptions}
            style={{ width: 100 }}
          />
        </Col>
        <Col>
          <Select
            value={formMonth}
            onChange={(v) => setFormMonth(v)}
            options={monthOptions}
            style={{ width: 85 }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadFormItems} loading={formLoading}>
            重新整理
          </Button>
        </Col>
        <Col flex="auto" />
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {formItems.length} 筆保養項目
          </Text>
        </Col>
      </Row>

      {!formLoading && formItems.length === 0 ? (
        <Alert
          message={`${formYear} 年 ${formMonth} 月 尚無保養批次資料，請確認 Ragic 同步狀態`}
          type="info"
          showIcon
        />
      ) : (
        <>
          <Table<FormRow>
            dataSource={formRows}
            rowKey="ragic_id"
            columns={formColumns}
            loading={formLoading}
            size="small"
            pagination={false}
            scroll={{ x: 'max-content' }}
            bordered
            rowClassName={(row) => row.abnormal_flag ? 'pm-form-abnormal' : ''}
          />
          <style>{`.pm-form-abnormal td { background: #fff1f0 !important; }`}</style>
        </>
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
          onClick={() => navigate(`/hotel/periodic-maintenance/${row.batch.ragic_id}`)}>
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
          onClick={() => navigate(`/hotel/periodic-maintenance/${row.batch.ragic_id}`)}
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

  // ── 每月維護統計 Tab ──────────────────────────────────────────────────────
  const MonthlyStatsTab = (
    <div>
      {/* ─── 年度矩陣總表 ─────────────────────────────────────────────────── */}
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
        <Col>
          <Button
            icon={<ToolOutlined />}
            type="primary"
            style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none' }}
            onClick={() => openCatalogModal('monthly')}
          >
            保養項目
          </Button>
        </Col>
      </Row>

      {matrixLoading ? (
        <Card size="small" style={{ marginBottom: 16, textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入年度矩陣中…</Typography.Text>
        </Card>
      ) : matrixData ? (
        <YearMatrixTable data={matrixData} frequencyType='monthly' onCellClick={(y, m, metric, lbl) => openDetailModal('monthly', y, m, metric, lbl)} />
      ) : (
        <Alert message="尚未載入年度矩陣，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      {/* ─── 單月鑽取（KPI 卡片） ──────────────────────────────────────────── */}
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
      {/* ─── 年度矩陣總表 ─────────────────────────────────────────────────── */}
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
        <Col>
          <Button
            icon={<ToolOutlined />}
            type="primary"
            style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none' }}
            onClick={() => openCatalogModal('quarterly')}
          >
            保養項目
          </Button>
        </Col>
      </Row>

      {quarterlyMatrixLoading ? (
        <Card size="small" style={{ marginBottom: 16, textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入年度矩陣中…</Typography.Text>
        </Card>
      ) : quarterlyMatrixData ? (
        <YearMatrixTable
          data={quarterlyMatrixData}
          frequencyType='quarterly'
          onCellClick={(y, m, metric, lbl) => openDetailModal('quarterly', y, m, metric, lbl)}
        />
      ) : (
        <Alert message="尚未載入年度矩陣，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      {/* ─── Q1-Q4 選擇卡片 ───────────────────────────────────────────────── */}
      <Divider orientation="left" style={{ fontSize: 13, color: '#666' }}>季度鑽取</Divider>
      {quarterlyMatrixLoading ? (
        <Card size="small" style={{ marginBottom: 16, textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入季度概覽中…</Typography.Text>
        </Card>
      ) : quarterlyMatrixData ? (
        <QuarterSelectorCards
          matrix={quarterlyMatrixData}
          selectedQ={quarterlyQuarter}
          onSelect={(q) => {
            setQuarterlyQuarter(q)
          }}
        />
      ) : (
        <Alert message="尚未載入季度概覽，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      {/* ─── 選定季度詳細統計 ─────────────────────────────────────────────── */}
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
      {/* ─── 年度矩陣總表 ─────────────────────────────────────────────────── */}
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Typography.Text type="secondary" style={{ marginRight: 4 }}>年度：</Typography.Text>
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
          <Button
            icon={<ReloadOutlined />}
            onClick={() => { loadYearlyMatrix(); loadYearlyStats() }}
            loading={yearlyMatrixLoading || yearlyLoading}
          >
            重新整理
          </Button>
        </Col>
        <Col>
          <Button
            icon={<ToolOutlined />}
            type="primary"
            style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none' }}
            onClick={() => openCatalogModal('yearly')}
          >
            保養項目
          </Button>
        </Col>
      </Row>

      {yearlyMatrixLoading ? (
        <Card size="small" style={{ marginBottom: 16, textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入年度矩陣中…</Typography.Text>
        </Card>
      ) : yearlyMatrixData ? (
        <YearMatrixTable
          data={yearlyMatrixData}
          frequencyType='yearly'
          onCellClick={(y, m, metric, lbl) => openDetailModal('yearly', y, m, metric, lbl)}
        />
      ) : (
        <Alert message="尚未載入年度矩陣，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      {/* ─── 年度鑽取（KPI + 季度分布） ────────────────────────────────────── */}
      <Divider orientation="left" style={{ fontSize: 13, color: '#666' }}>年度鑽取</Divider>
      {yearlyLoading ? (
        <Card size="small" style={{ textAlign: 'center', padding: 24 }}>
          <Typography.Text type="secondary">載入中…</Typography.Text>
        </Card>
      ) : yearlyData ? (
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

  // ── 頁面渲染 ──────────────────────────────────────────────────────────────
  return (
    <>
    <div style={{ padding: '0 4px' }}>
      {/* Breadcrumb */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.hotel },
          { title: NAV_PAGE.periodicMaintenance },
        ]}
      />

      {/* 頁頭 */}
      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <ToolOutlined /> {NAV_PAGE.periodicMaintenance}
          </Title>
        </Col>
      </Row>

      {/* 主要內容 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'dashboard', label: 'Dashboard',  children: DashboardTab },
          {
            key:   'form',
            label: <span><CalendarOutlined /> 每月保養表</span>,
            children: FormTab,
          },
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
          { key: 'list',      label: '批次清單',    children: ListTab },
        ]}
      />
    </div>

    {/* ── 矩陣格明細 Modal ───────────────────────────────────────────── */}
    <MatrixDetailModal
      open={modalOpen}
      year={modalYear}
      month={modalMonth}
      metric={modalMetric}
      frequencyType={modalFreqType}
      monthLabel={modalMonthLabel}
      onClose={() => setModalOpen(false)}
    />

    {/* ── 保養項目目錄 Modal ──────────────────────────────────────────── */}
    <CatalogModal
      open={catalogOpen}
      frequencyType={catalogFreqType}
      items={catalogItems}
      loading={catalogLoading}
      onClose={() => setCatalogOpen(false)}
    />
    </>
  )
}

// ── 矩陣格明細 Modal 元件 ──────────────────────────────────────────────────────
const METRIC_LABELS: Record<string, string> = {
  prev_carry_over:   '截至上月底累計未結案數',
  prev_resolved:     '其中本月已結案數',
  period_total:      '本期應完成總數',
  period_completed:  '本期已完成',
}

const STATUS_COLOR: Record<string, string> = {
  '已完成': '#52c41a', '完成': '#52c41a',
  '進行中': '#1677ff',
  '未完成': '#ff4d4f', '逾期': '#ff4d4f',
  '非本月': '#d9d9d9', '待排程': '#faad14',
}

function MatrixDetailModal({
  open, year, month, metric, frequencyType, monthLabel, onClose,
}: {
  open: boolean
  year: number
  month: number
  metric: PMMatrixMetric
  frequencyType: string
  monthLabel: string
  onClose: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [items,   setItems]   = useState<PMMatrixItem[]>([])
  const [total,   setTotal]   = useState(0)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetchPMMatrixItems({ year, month, metric, frequency_type: frequencyType })
      .then((res) => { setItems(res.items); setTotal(res.total) })
      .catch(() => message.error('載入明細失敗'))
      .finally(() => setLoading(false))
  }, [open, year, month, metric, frequencyType])

  const columns: ColumnsType<PMMatrixItem> = [
    { title: '類別',     dataIndex: 'category',           width: 80,  ellipsis: true },
    { title: '保養項目', dataIndex: 'task_name',           width: 160, ellipsis: true },
    { title: '頻率',     dataIndex: 'frequency',           width: 60  },
    { title: '預定日期', dataIndex: 'scheduled_date_full', width: 90  },
    { title: '結束時間', dataIndex: 'end_time',            width: 90  },
    {
      title: '狀態', dataIndex: 'status', width: 80,
      render: (s: string) => (
        <Tag color={STATUS_COLOR[s] ?? '#d9d9d9'} style={{ fontSize: 11 }}>{s || '—'}</Tag>
      ),
    },
    { title: '執行人', dataIndex: 'executor_name', width: 80, ellipsis: true },
    {
      title: '連結', dataIndex: 'ragic_link', width: 60,
      render: (url: string) => url ? <a href={url} target="_blank" rel="noreferrer">Ragic</a> : null,
    },
  ]

  const monthStr = month === 0 ? '全年' : monthLabel
  const metricLabel = METRIC_LABELS[metric] ?? metric

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={900}
      title={
        <span>
          {year}年 {monthStr}・{metricLabel}
          <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>共 {total} 筆</Typography.Text>
        </span>
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 32 }}><Spin /></div>
      ) : (
        <Table
          dataSource={items}
          columns={columns}
          rowKey="ragic_id"
          size="small"
          scroll={{ x: 700 }}
          pagination={{ pageSize: 20, showSizeChanger: false }}
        />
      )}
    </Modal>
  )
}

// ── 保養項目目錄 Modal 元件 ────────────────────────────────────────────────────
const FREQ_TYPE_LABELS: Record<string, string> = {
  monthly:   '每月',
  quarterly: '每季',
  yearly:    '每年',
}

function CatalogModal({
  open, frequencyType, items, loading, onClose,
}: {
  open: boolean
  frequencyType: 'monthly' | 'quarterly' | 'yearly'
  items: PMCatalogItem[]
  loading: boolean
  onClose: () => void
}) {
  const columns: ColumnsType<PMCatalogItem> = [
    {
      title: '項次', dataIndex: 'seq_no', width: 60, align: 'center',
      render: (v: number) => <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text>,
    },
    {
      title: '類別', dataIndex: 'category', width: 90,
      render: (v: string) => <Tag color="blue" style={{ fontSize: 11 }}>{v}</Tag>,
    },
    {
      title: '頻率', dataIndex: 'frequency', width: 80, align: 'center',
      render: (v: string) => <Tag color="purple" style={{ fontSize: 11 }}>{v}</Tag>,
    },
    {
      title: '保養項目',
      dataIndex: 'task_name',
      render: (v: string) => (
        <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text>
      ),
    },
    {
      title: '區域/位置', dataIndex: 'location', width: 120,
      render: (v: string) => <Typography.Text style={{ fontSize: 12 }}>{v || '—'}</Typography.Text>,
    },
    {
      title: '執行月份', dataIndex: 'exec_months_raw', width: 130,
      render: (v: string) => (
        <Typography.Text style={{ fontSize: 11, color: '#666' }}>{v || '—'}</Typography.Text>
      ),
    },
    {
      title: '預估工時', dataIndex: 'estimated_minutes', width: 90, align: 'center',
      render: (v: number) => (
        <Typography.Text style={{ fontSize: 12 }}>
          {v > 0 ? `${v} 分` : '—'}
        </Typography.Text>
      ),
    },
  ]

  const freqLabel = FREQ_TYPE_LABELS[frequencyType] || frequencyType

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={900}
      title={
        <Space>
          <ToolOutlined style={{ color: '#764ba2' }} />
          <span style={{ fontWeight: 600 }}>{freqLabel}保養項目清單</span>
          {!loading && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              共 {items.length} 項
            </Typography.Text>
          )}
        </Space>
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin tip="載入保養項目中…" /></div>
      ) : (
        <Table
          dataSource={items}
          columns={columns}
          rowKey={(r) => `${r.category}-${r.seq_no}-${r.task_name}`}
          size="small"
          scroll={{ x: 800 }}
          pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 項`, showSizeChanger: false }}
        />
      )}
    </Modal>
  )
}
