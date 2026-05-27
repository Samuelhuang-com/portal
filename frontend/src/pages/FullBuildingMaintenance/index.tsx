/**
 * 全棟例行維護主頁
 *
 * Tab 1「Dashboard」：KPI 六卡（含保養時間）+ 類別 Bar 圖 + 狀態 Donut 圖 + 逾期/即將到期預警
 * Tab 2「每日巡檢表」：整棟巡檢每日巡檢表
 * Tab 3「每月維護」：月統計 + 年度矩陣（每月）+ 單月鑽取
 * Tab 4「每季維護」：季統計 + 年度矩陣（每季）+ 季度鑽取
 * Tab 5「每年維護」：年統計 + 年度矩陣（每年）+ 年度鑽取
 * Tab 6「排程管理」：Portal 自有排程，可產生任意月份排程
 * Tab 7「年度計劃表」：12欄矩陣視圖
 * Tab 8「批次清單」：保養批次列表，含進度條、狀態標籤、操作入口
 */
import { useEffect, useState, useCallback, type CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Progress, Alert, Select,
  message, Tooltip, Badge, Divider, Modal, Spin, Drawer, Form, Switch,
  Input,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, ToolOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, RightOutlined, BarChartOutlined,
  ShopOutlined, CalendarOutlined, LineChartOutlined, LinkOutlined,
  ScheduleOutlined, TableOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchFullBldgPMStats, fetchFullBldgPMBatches, fetchFullBldgPMBatchDetail, fetchFullBldgPMPeriodStats, fetchFullBldgPMYearMatrix,
  fetchFullBldgPMCalendar, fetchFullBldgPMMatrixItems, fetchFullBldgPMCatalog,
  getFullBldgScheduleList, getFullBldgScheduleKpi, getFullBldgOverdueSchedule,
  patchFullBldgSchedule, postGenerateFullBldgSchedule, getFullBldgAnnualMatrix,
} from '@/api/fullBuildingMaintenance'
import type {
  PMMatrixMetric, FullBldgPMMatrixItem, FullBldgPMCatalogItem,
  FullBldgPMScheduleItem, FullBldgPMScheduleKpi,
  FullBldgPMScheduleAnnualMatrix, FullBldgPMScheduleMatrixRow,
  FullBldgPMScheduleUpdatePayload, FullBldgPMScheduleGenerateResult,
} from '@/api/fullBuildingMaintenance'
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'
import type {
  PMStats, PMBatchListItem, PMItem,
  PMPeriodStats, PMIncompleteItem, PMSubPeriodBreakdown,
  PMYearMatrix, PMYearMatrixMonth,
} from '@/types/periodicMaintenance'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import FullBldgDailyFormTab from './FullBldgDailyFormTab'

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

// ── 排程狀態設定 ──────────────────────────────────────────────────────────────
const SCHED_STATUS_CFG: Record<string, { label: string; color: string; tagColor: string }> = {
  completed:   { label: '已完成', color: '#52C41A', tagColor: 'success' },
  in_progress: { label: '進行中', color: '#4BA8E8', tagColor: 'processing' },
  overdue:     { label: '逾期',   color: '#C0392B', tagColor: 'error' },
  scheduled:   { label: '待執行', color: '#FA8C16', tagColor: 'warning' },
  unscheduled: { label: '未排定', color: '#FAAD14', tagColor: 'default' },
}

// ── 年度計劃矩陣儲存格樣式 ────────────────────────────────────────────────────
const ANNUAL_CELL_STYLE: Record<string, { icon: string; bg: string; color: string }> = {
  completed:   { icon: '✅', bg: '#f6ffed', color: '#52C41A' },
  overdue:     { icon: '🔴', bg: '#fff1f0', color: '#C0392B' },
  in_progress: { icon: '🔵', bg: '#e6f4ff', color: '#1890FF' },
  scheduled:   { icon: '⭕', bg: '#fff7e6', color: '#FA8C16' },
  unscheduled: { icon: '?',  bg: '#fffbe6', color: '#FAAD14' },
  non_month:   { icon: '─',  bg: '#fafafa', color: '#aaa' },
  no_data:     { icon: '！', bg: '#fff0f6', color: '#eb2f96' },
  no_frequency:{ icon: '∅',  bg: '#f5f5f5', color: '#ccc' },
}

const ANNUAL_TH: CSSProperties = {
  padding: '6px 8px', fontWeight: 600, border: '1px solid #e8e8e8',
  whiteSpace: 'nowrap', textAlign: 'left',
}
const ANNUAL_TD: CSSProperties = {
  padding: '4px 8px', border: '1px solid #f0f0f0', verticalAlign: 'middle',
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
          { title: `${prevLabel}累計未完成`,                 value: data.prev_carry_over,         suffix: '筆', color: '#C0392B' },
          { title: `${prevLabel}未完成於${currLabel}結案`,   value: data.prev_resolved_in_period, suffix: '筆', color: '#4BA8E8' },
          { title: '累計完成率', value: fmtRate(data.carry_over_rate), suffix: '', color: data.carry_over_rate === null ? '#999' : '#1B3A5C' },
        ].map((c) => (
          <Col flex={1} style={{ minWidth: 160 }} key={c.title}>
            <Card size="small" hoverable>
              <Statistic title={c.title} value={c.value} suffix={c.suffix} valueStyle={{ color: c.color, fontSize: 24 }} />
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
          { title: `${currLabel}項目數`, value: data.period_total,     suffix: '筆', color: '#1B3A5C' },
          { title: `${currLabel}完成數`, value: data.period_completed, suffix: '筆', color: '#52C41A' },
          { title: `${currLabel}完成率`, value: fmtRate(data.period_rate), suffix: '', color: data.period_rate === null ? '#999' : '#52C41A' },
        ].map((c) => (
          <Col flex={1} style={{ minWidth: 160 }} key={c.title}>
            <Card size="small" hoverable>
              <Statistic title={c.title} value={c.value} suffix={c.suffix} valueStyle={{ color: c.color, fontSize: 24 }} />
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
  tooltip?: string
}[] = [
  { key: 'prev_carry_over',
    label: '截至上月底累計未結案數',
    tooltip: '前期結轉未完成數：截至上月底，所有尚未結案的週期保養項目累計總數（含更早期遞延未完成項目）。' },
  { key: 'prev_resolved_in_period',
    label: '其中本月已結案數',
    tooltip: '本月已結案數：上列「截至上月底累計未結案數」中，在本月內完成並結案的項目數。\n完成率（累計項目完成率）＝ 已結案數 ÷ 累計未結案數 × 100%。' },
  { key: 'carry_over_rate',  label: '累計項目完成率', isRate: true },
  { key: '_sep1',            label: '' },
  { key: 'period_total',     label: '本期應完成總數' },
  { key: 'period_completed', label: '本期已完成' },
  { key: 'period_rate',      label: '本月週期保養完成率', isRate: true },
  { key: '_sep2',            label: '' },
  { key: 'incomplete_notes', label: '未完成事項說明（原因/待協助事項）', isText: true },
]

const CLICKABLE_METRIC_MAP: Record<string, PMMatrixMetric> = {
  prev_carry_over:         'prev_carry_over',
  prev_resolved_in_period: 'prev_resolved',
  period_total:            'period_total',
  period_completed:        'period_completed',
}

function YearMatrixTable({
  data, frequencyType, onCellClick,
}: {
  data: PMYearMatrix
  frequencyType?: string
  onCellClick?: (year: number, month: number, metric: PMMatrixMetric, monthLabel: string) => void
}) {
  const nowYear  = dayjs().year()
  const nowMonth = dayjs().month() + 1
  const isFuture = (month: number) =>
    data.year > nowYear || (data.year === nowYear && month > nowMonth)

  const pastMonths           = data.months.filter((m) => !isFuture(m.month))
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
    incomplete_notes: '',
  }

  const futureCell = () => (
    <Typography.Text type="secondary" style={{ fontSize: 18 }}>—</Typography.Text>
  )

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

  const cols: ColumnsType<Record<string, unknown>> = [
    {
      title: '', dataIndex: 'label', width: 310, fixed: 'left',
      onCell: (row) => ({ style: { background: row['_isSep'] ? '#fafafa' : undefined } }),
      render: (v: string, row) => {
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
        },
      }),
      render: (v: unknown, row: Record<string, unknown>) => {
        if (row['_isSep']) return null
        if (isFuture(m.month)) return futureCell()
        return renderCell(v, row, false, m.month, m.label)
      },
    })),
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
          borderLeft:  '2px solid #d9e4f0',
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

  const freqTitle = frequencyType === 'monthly' ? '每月' : frequencyType === 'quarterly' ? '每季' : frequencyType === 'yearly' ? '每年' : ''

  return (
    <Card
      title={<><BarChartOutlined /> {data.year} 年度全棟例行維護統計總表{freqTitle ? `（${freqTitle}）` : ''}</>}
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
type FormRow = PMItem & { _catSpan: number }

export default function FullBuildingMaintenancePage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats]     = useState<PMStats | null>(null)
  const [batches, setBatches] = useState<PMBatchListItem[]>([])
  const [dashYear,  setDashYear]  = useState(dayjs().format('YYYY'))
  const [dashMonth, setDashMonth] = useState(dayjs().month() + 1)
  const [year, setYear]       = useState(dayjs().format('YYYY'))
  const [loading, setLoading] = useState(false)

  // ── 月統計 state ────────────────────────────────────────────────────────
  const [monthlyData,    setMonthlyData]    = useState<PMPeriodStats | null>(null)
  const [monthlyYear,    setMonthlyYear]    = useState(dayjs().year())
  const [monthlyMonth,   setMonthlyMonth]   = useState(dayjs().month() + 1)
  const [monthlyLoading, setMonthlyLoading] = useState(false)

  // ── 年度矩陣 state（每月）───────────────────────────────────────────────
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
  const [yearlyData,          setYearlyData]          = useState<PMPeriodStats | null>(null)
  const [yearlyMatrixData,    setYearlyMatrixData]    = useState<PMYearMatrix | null>(null)
  const [yearlyYear,          setYearlyYear]          = useState(dayjs().year())
  const [yearlyLoading,       setYearlyLoading]       = useState(false)
  const [yearlyMatrixLoading, setYearlyMatrixLoading] = useState(false)

  // ── 矩陣格點擊明細 Modal state ──────────────────────────────────────────
  const [modalOpen,       setModalOpen]       = useState(false)
  const [modalYear,       setModalYear]       = useState(0)
  const [modalMonth,      setModalMonth]      = useState(0)
  const [modalMetric,     setModalMetric]     = useState<PMMatrixMetric>('period_total')
  const [modalFreqType,   setModalFreqType]   = useState<string>('')
  const [modalMonthLabel, setModalMonthLabel] = useState('')

  const openDetailModal = useCallback((freqType: string, year: number, month: number, metric: PMMatrixMetric, monthLabel: string) => {
    setModalFreqType(freqType)
    setModalYear(year)
    setModalMonth(month)
    setModalMetric(metric)
    setModalMonthLabel(monthLabel)
    setModalOpen(true)
  }, [])

  // ── 保養項目目錄 Modal state ────────────────────────────────────────────
  const [catalogOpen,     setCatalogOpen]     = useState(false)
  const [catalogFreqType, setCatalogFreqType] = useState<'monthly' | 'quarterly' | 'yearly'>('monthly')
  const [catalogItems,    setCatalogItems]    = useState<FullBldgPMCatalogItem[]>([])
  const [catalogLoading,  setCatalogLoading]  = useState(false)

  const openCatalogModal = useCallback(async (freqType: 'monthly' | 'quarterly' | 'yearly') => {
    setCatalogFreqType(freqType)
    setCatalogOpen(true)
    setCatalogLoading(true)
    try {
      const res = await fetchFullBldgPMCatalog(freqType)
      setCatalogItems(res.items)
    } catch {
      setCatalogItems([])
    } finally {
      setCatalogLoading(false)
    }
  }, [])

  // ── Dashboard 月曆格 state ───────────────────────────────────────────────
  const [calRows,   setCalRows]   = useState<CalendarRow[]>([])
  const [calMaxDay, setCalMaxDay] = useState(31)

  // ── 排程管理 Tab state ────────────────────────────────────────────────────
  const [schedYear,         setSchedYear]         = useState(dayjs().year())
  const [schedMonth,        setSchedMonth]        = useState(dayjs().month() + 1)
  const [schedItems,        setSchedItems]        = useState<FullBldgPMScheduleItem[]>([])
  const [schedKpi,          setSchedKpi]          = useState<FullBldgPMScheduleKpi | null>(null)
  const [schedLoading,      setSchedLoading]      = useState(false)
  const [schedShouldDo,     setSchedShouldDo]     = useState(0)
  const [schedCatFilter,    setSchedCatFilter]    = useState<string | undefined>(undefined)
  const [schedStatusFilter, setSchedStatusFilter] = useState<string | undefined>(undefined)
  const [overdueItems,      setOverdueItems]      = useState<(FullBldgPMScheduleItem & { overdue_days: number })[]>([])
  const [overdueExpanded,   setOverdueExpanded]   = useState(false)
  const [overdueLoading,    setOverdueLoading]    = useState(false)
  const [generateLoading,   setGenerateLoading]   = useState(false)
  const [generateModalOpen, setGenerateModalOpen] = useState(false)

  // ScheduleDrawer state
  const [schedDrawerOpen,  setSchedDrawerOpen]  = useState(false)
  const [schedDrawerItem,  setSchedDrawerItem]  = useState<FullBldgPMScheduleItem | null>(null)
  const [schedEditMode,    setSchedEditMode]    = useState(false)
  const [schedEditLoading, setSchedEditLoading] = useState(false)
  const [schedEditForm]                         = Form.useForm()

  // ── 年度計劃表 Tab state ──────────────────────────────────────────────────
  const [annualYear,        setAnnualYear]        = useState(dayjs().year())
  const [annualCat,         setAnnualCat]         = useState<string | undefined>(undefined)
  const [annualFreq,        setAnnualFreq]        = useState<string | undefined>(undefined)
  const [annualMatrix,      setAnnualMatrix]      = useState<FullBldgPMScheduleAnnualMatrix | null>(null)
  const [annualLoading,     setAnnualLoading]     = useState(false)
  const [annualDrawerOpen,  setAnnualDrawerOpen]  = useState(false)
  const [annualDrawerCell,  setAnnualDrawerCell]  = useState<{
    row: FullBldgPMScheduleMatrixRow; scheduleId: number | null; status: string; month: number
  } | null>(null)
  const [annualCellDetail,  setAnnualCellDetail]  = useState<FullBldgPMScheduleItem | null>(null)
  const [annualCellLoading, setAnnualCellLoading] = useState(false)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const yr = parseInt(dashYear)
      const mo = dashMonth
      const [s, calData] = await Promise.all([
        fetchFullBldgPMStats(dashYear, dashMonth),
        fetchFullBldgPMCalendar(yr, mo).catch(() => null),
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
      const data = await fetchFullBldgPMPeriodStats({ period_type: 'month', year: monthlyYear, month: monthlyMonth, frequency_type: 'monthly' })
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
      const data = await fetchFullBldgPMYearMatrix(monthlyYear, 'monthly')
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
      const data = await fetchFullBldgPMYearMatrix(quarterlyYear, 'quarterly')
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
      const data = await fetchFullBldgPMPeriodStats({ period_type: 'quarter', year: quarterlyYear, quarter: quarterlyQuarter, frequency_type: 'quarterly' })
      setQuarterlyData(data)
    } catch {
      message.error('載入季統計失敗')
    } finally {
      setQuarterlyLoading(false)
    }
  }, [quarterlyYear, quarterlyQuarter])

  const loadYearlyMatrix = useCallback(async () => {
    setYearlyMatrixLoading(true)
    try {
      const data = await fetchFullBldgPMYearMatrix(yearlyYear, 'yearly')
      setYearlyMatrixData(data)
    } catch {
      message.error('載入年度矩陣失敗')
    } finally {
      setYearlyMatrixLoading(false)
    }
  }, [yearlyYear])

  const loadYearlyStats = useCallback(async () => {
    setYearlyLoading(true)
    try {
      const data = await fetchFullBldgPMPeriodStats({ period_type: 'year', year: yearlyYear, frequency_type: 'yearly' })
      setYearlyData(data)
    } catch {
      message.error('載入年統計失敗')
    } finally {
      setYearlyLoading(false)
    }
  }, [yearlyYear])

  // ── 排程管理 handlers ──────────────────────────────────────────────────────
  const loadSchedule = useCallback(async () => {
    setSchedLoading(true)
    const ym = `${schedYear}/${String(schedMonth).padStart(2, '0')}`
    try {
      const [res, kpiRes] = await Promise.all([
        getFullBldgScheduleList({ year_month: ym }),
        getFullBldgScheduleKpi(ym),
      ])
      setSchedItems(res.items)
      setSchedShouldDo(res.should_do_not_done)
      setSchedKpi(kpiRes)
    } catch {
      message.error('載入排程資料失敗')
    } finally {
      setSchedLoading(false)
    }
  }, [schedYear, schedMonth])

  const loadOverdue = useCallback(async () => {
    setOverdueLoading(true)
    try {
      const res = await getFullBldgOverdueSchedule()
      setOverdueItems(res.items)
    } catch {
      setOverdueItems([])
    } finally {
      setOverdueLoading(false)
    }
  }, [])

  const handleSchedDrawerOpen = useCallback((item: FullBldgPMScheduleItem) => {
    setSchedDrawerItem(item)
    setSchedEditMode(false)
    setSchedDrawerOpen(true)
  }, [])

  const handleScheduleSave = useCallback(async () => {
    if (!schedDrawerItem) return
    setSchedEditLoading(true)
    try {
      const values = await schedEditForm.validateFields() as FullBldgPMScheduleUpdatePayload
      await patchFullBldgSchedule(schedDrawerItem.id, values)
      message.success('儲存成功')
      setSchedDrawerOpen(false)
      loadSchedule()
    } catch {
      message.error('儲存失敗')
    } finally {
      setSchedEditLoading(false)
    }
  }, [schedDrawerItem, schedEditForm, loadSchedule])

  const handleGenerateSchedule = useCallback(async () => {
    setGenerateLoading(true)
    try {
      const res: FullBldgPMScheduleGenerateResult = await postGenerateFullBldgSchedule(schedYear, schedMonth)
      message.success(`排程產生完成：新增 ${res.generated} 筆、更新 ${res.updated} 筆`)
      setGenerateModalOpen(false)
      loadSchedule()
      loadOverdue()
    } catch {
      message.error('產生排程失敗')
    } finally {
      setGenerateLoading(false)
    }
  }, [schedYear, schedMonth, loadSchedule, loadOverdue])

  // ── 年度計劃表 handlers ──────────────────────────────────────────────────
  const loadAnnualMatrix = useCallback(async () => {
    setAnnualLoading(true)
    try {
      const res = await getFullBldgAnnualMatrix(annualYear, annualCat)
      setAnnualMatrix(res)
    } catch {
      message.error('載入年度計劃表失敗')
    } finally {
      setAnnualLoading(false)
    }
  }, [annualYear, annualCat])

  const openAnnualCell = useCallback(async (
    row: FullBldgPMScheduleMatrixRow,
    scheduleId: number | null,
    status: string,
    month: number,
  ) => {
    if (status === 'non_month' || status === 'no_frequency') return
    setAnnualDrawerCell({ row, scheduleId, status, month })
    setAnnualCellDetail(null)
    setAnnualCellLoading(false)
    setAnnualDrawerOpen(true)
    if (scheduleId) {
      setAnnualCellLoading(true)
      try {
        const ym = `${annualYear}/${String(month).padStart(2, '0')}`
        const res = await getFullBldgScheduleList({ year_month: ym })
        const found = res.items.find(i => i.id === scheduleId) ?? null
        setAnnualCellDetail(found)
      } catch {
        setAnnualCellDetail(null)
      } finally {
        setAnnualCellLoading(false)
      }
    }
  }, [annualYear])

  useEffect(() => { loadDashboard() }, [loadDashboard])

  useEffect(() => {
    if (activeTab === 'list')      loadBatches()
    if (activeTab === 'monthly')   { loadYearMatrix(); loadMonthlyStats() }
    if (activeTab === 'quarterly') { loadQuarterlyMatrix(); loadQuarterlyStats() }
    if (activeTab === 'yearly')    { loadYearlyMatrix(); loadYearlyStats() }
    if (activeTab === 'schedule')  { loadSchedule(); loadOverdue() }
    if (activeTab === 'annual')    loadAnnualMatrix()
  }, [activeTab, loadBatches, loadMonthlyStats, loadQuarterlyStats, loadYearlyStats, loadYearMatrix, loadQuarterlyMatrix, loadYearlyMatrix, loadSchedule, loadOverdue, loadAnnualMatrix])

  useEffect(() => { if (activeTab === 'monthly')   loadYearMatrix() },      [loadYearMatrix])
  useEffect(() => { if (activeTab === 'quarterly') loadQuarterlyMatrix() }, [loadQuarterlyMatrix])
  useEffect(() => { if (activeTab === 'quarterly') loadQuarterlyStats() },  [loadQuarterlyStats])
  useEffect(() => { if (activeTab === 'yearly')    loadYearlyMatrix() },    [loadYearlyMatrix])

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

      {/* 月曆格：類別 × 日期 */}
      <Card
        size="small"
        style={{ marginTop: 16 }}
        title={
          <Space>
            <CalendarOutlined />
            <Text strong>全棟例行維護排程狀況</Text>
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
        <YearMatrixTable data={matrixData} frequencyType="monthly"
          onCellClick={(y, m, metric, label) => openDetailModal('monthly', y, m, metric, label)} />
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
          <Typography.Text type="secondary">載入季度矩陣中…</Typography.Text>
        </Card>
      ) : quarterlyMatrixData ? (
        <YearMatrixTable data={quarterlyMatrixData} frequencyType="quarterly"
          onCellClick={(y, m, metric, label) => openDetailModal('quarterly', y, m, metric, label)} />
      ) : (
        <Alert message="尚未載入季度矩陣，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      <Divider orientation="left" style={{ fontSize: 13, color: '#666' }}>
        季度鑽取
      </Divider>

      {quarterlyMatrixData && (
        <QuarterSelectorCards
          matrix={quarterlyMatrixData}
          selectedQ={quarterlyQuarter}
          onSelect={(q) => { setQuarterlyQuarter(q) }}
        />
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
        <YearMatrixTable data={yearlyMatrixData} frequencyType="yearly"
          onCellClick={(y, m, metric, label) => openDetailModal('yearly', y, m, metric, label)} />
      ) : (
        <Alert message="尚未載入年度矩陣，請點擊重新整理" type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      <Divider orientation="left" style={{ fontSize: 13, color: '#666' }}>年度鑽取</Divider>

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
      width: 140,
      render: (_, row) => (
        <Space size={8}>
          <Button
            type="primary"
            size="small"
            icon={<RightOutlined />}
            style={{ background: '#1B3A5C' }}
            onClick={() => navigate(`/mall/full-building-maintenance/${row.batch.ragic_id}`)}
          >
            查看明細
          </Button>
          {row.batch.ragic_url && (
            <Tooltip title="在 Ragic 查看原始表單">
              <a
                href={row.batch.ragic_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#4BA8E8', fontSize: 16, lineHeight: 1, display: 'inline-flex', alignItems: 'center' }}
              >
                <LinkOutlined />
              </a>
            </Tooltip>
          )}
        </Space>
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

  // ── 排程管理 Tab ──────────────────────────────────────────────────────────

  const filteredSchedItems = schedItems.filter(item => {
    if (schedCatFilter && item.category !== schedCatFilter) return false
    if (schedStatusFilter) {
      if (schedStatusFilter === 'abnormal') return item.abnormal_flag
      return item.status === schedStatusFilter
    }
    return true
  })

  const schedCatOptions = [...new Set(schedItems.map(i => i.category))].map(c => ({ value: c, label: c }))

  const schedColumns: ColumnsType<FullBldgPMScheduleItem> = [
    { title: '類別', dataIndex: 'category', width: 80,
      render: (v: string) => <Tag color="blue" style={{ fontSize: 11 }}>{v || '—'}</Tag> },
    { title: '保養項目', dataIndex: 'task_name', ellipsis: true,
      render: (v: string, row) => (
        <Button type="link" size="small" style={{ padding: 0, textAlign: 'left' }}
          onClick={() => handleSchedDrawerOpen(row)}>{v}</Button>
      ) },
    { title: '位置', dataIndex: 'location', width: 100, ellipsis: true,
      render: (v: string) => v || <Text type="secondary">—</Text> },
    { title: '頻率', dataIndex: 'frequency', width: 60,
      render: (v: string) => v ? <Tag>{v}</Tag> : <Text type="secondary">—</Text> },
    { title: '排定日期', dataIndex: 'scheduled_date', width: 85,
      render: (v: string) => v || <Text type="secondary">未排定</Text> },
    { title: '執行人員', dataIndex: 'executor_name', width: 80, ellipsis: true,
      render: (v: string) => v || <Text type="secondary">—</Text> },
    { title: '狀態', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const cfg = SCHED_STATUS_CFG[v] ?? { label: v, tagColor: 'default' }
        return <Tag color={cfg.tagColor}>{cfg.label}</Tag>
      } },
    { title: '來源', dataIndex: 'schedule_source', width: 70,
      render: (v: string) => v === 'manual'
        ? <Tag color="purple" style={{ fontSize: 11 }}>人工</Tag>
        : <Tag color="cyan" style={{ fontSize: 11 }}>自動</Tag> },
    { title: '操作', width: 60,
      render: (_, row) => (
        <Button size="small" onClick={() => handleSchedDrawerOpen(row)}>詳情</Button>
      ) },
  ]

  const overdueColumns: ColumnsType<FullBldgPMScheduleItem & { overdue_days: number }> = [
    { title: '月份', dataIndex: 'year_month', width: 80 },
    { title: '類別', dataIndex: 'category', width: 75,
      render: (v: string) => <Tag color="blue" style={{ fontSize: 11 }}>{v}</Tag> },
    { title: '保養項目', dataIndex: 'task_name', ellipsis: true },
    { title: '排定日期', dataIndex: 'scheduled_date', width: 80,
      render: (v: string) => <Text type="danger">{v}</Text> },
    { title: '逾期天數', dataIndex: 'overdue_days', width: 90,
      render: (v: number) => <Tag color="error">{v} 天</Tag> },
    { title: '操作', width: 60,
      render: (_, row) => (
        <Button size="small" danger onClick={() => handleSchedDrawerOpen(row)}>處理</Button>
      ) },
  ]

  const ScheduleTab = (
    <div>
      {/* 篩選器列 */}
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Select value={schedYear} onChange={setSchedYear} options={yearNumOptions} style={{ width: 90 }} />
        </Col>
        <Col>
          <Select value={schedMonth} onChange={setSchedMonth} options={monthOptions} style={{ width: 80 }} />
        </Col>
        <Col>
          <Select
            allowClear placeholder="類別" value={schedCatFilter}
            onChange={setSchedCatFilter} options={schedCatOptions} style={{ width: 110 }}
          />
        </Col>
        <Col>
          <Select
            allowClear placeholder="狀態" value={schedStatusFilter}
            onChange={setSchedStatusFilter} style={{ width: 110 }}
            options={[
              { value: 'unscheduled', label: '未排定' },
              { value: 'scheduled',   label: '待執行' },
              { value: 'in_progress', label: '進行中' },
              { value: 'overdue',     label: '逾期' },
              { value: 'completed',   label: '已完成' },
              { value: 'abnormal',    label: '異常' },
            ]}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadSchedule} loading={schedLoading}>重新整理</Button>
        </Col>
        <Col flex="auto" />
        <Col>
          <Button type="primary" icon={<ScheduleOutlined />}
            onClick={() => setGenerateModalOpen(true)}
            style={{ background: '#1B3A5C' }}
          >
            ▶ 產生本月排程
          </Button>
        </Col>
      </Row>

      {/* 應做未做警示 */}
      {schedShouldDo > 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message={`本月尚有 ${schedShouldDo} 筆項目依頻率應執行，但尚未納入排程。請點擊「產生本月排程」補建。`}
        />
      )}

      {/* KPI 迷你卡片 */}
      {schedKpi && (
        <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
          {[
            { label: '全部',   value: schedKpi.total,              color: '#1B3A5C' },
            { label: '應做未做', value: schedShouldDo,             color: '#FA8C16' },
            { label: '未排定', value: schedKpi.unscheduled,        color: '#FAAD14' },
            { label: '待執行', value: schedKpi.scheduled,          color: '#4BA8E8' },
            { label: '進行中', value: schedKpi.in_progress,        color: '#52C41A' },
            { label: '逾期',   value: schedKpi.overdue,            color: '#C0392B' },
            { label: '已完成', value: schedKpi.completed,          color: '#52C41A' },
            { label: '異常',   value: schedKpi.abnormal,           color: '#722ED1' },
            { label: '完成率', value: `${schedKpi.completion_rate}%`, color: '#52C41A' },
          ].map(kpi => (
            <Col key={kpi.label}>
              <Card size="small" style={{ minWidth: 80, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>{kpi.label}</div>
                <div style={{ fontSize: 18, fontWeight: 600, color: kpi.color }}>{kpi.value}</div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 排程明細表 */}
      <Table<FullBldgPMScheduleItem>
        dataSource={filteredSchedItems}
        rowKey="id"
        columns={schedColumns}
        loading={schedLoading}
        size="small"
        scroll={{ x: 'max-content' }}
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 筆` }}
        rowClassName={(row) => row.status === 'overdue' ? 'ant-table-row-danger' : ''}
      />

      {/* 逾期累積清單 */}
      <Divider style={{ cursor: 'pointer' }}
        onClick={() => setOverdueExpanded(e => !e)}>
        <Space>
          <Badge count={overdueItems.length} size="small">
            <Text style={{ fontSize: 13 }}>逾期未執行（跨月累積）</Text>
          </Badge>
          <Text type="secondary" style={{ fontSize: 12 }}>{overdueExpanded ? '▲ 收合' : '▼ 展開'}</Text>
        </Space>
      </Divider>
      {overdueExpanded && (
        <Table<FullBldgPMScheduleItem & { overdue_days: number }>
          dataSource={overdueItems}
          rowKey="id"
          columns={overdueColumns}
          loading={overdueLoading}
          size="small"
          pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 筆` }}
        />
      )}

      {/* 產生排程確認 Modal */}
      <Modal
        open={generateModalOpen}
        title="產生本月排程"
        onOk={handleGenerateSchedule}
        onCancel={() => setGenerateModalOpen(false)}
        confirmLoading={generateLoading}
        okText="確認產生"
        cancelText="取消"
      >
        <p>確認為 <strong>{schedYear} 年 {schedMonth} 月</strong> 產生全棟例行維護排程？</p>
        <p style={{ color: '#888', fontSize: 13 }}>已完成或人工調整的記錄不會被覆蓋。</p>
      </Modal>
    </div>
  )

  // ── 年度計劃表 Tab ──────────────────────────────────────────────────────────

  const annualCatOptions = annualMatrix
    ? [
        { value: '', label: '全部類別' },
        ...Array.from(new Set(annualMatrix.rows.map(r => r.category).filter(Boolean)))
          .map(c => ({ value: c, label: c })),
      ]
    : [{ value: '', label: '全部類別' }]

  const annualFreqOptions = annualMatrix
    ? [
        { value: '', label: '全部頻率' },
        ...Array.from(new Set(annualMatrix.rows.map(r => r.frequency).filter(Boolean)))
          .sort().map(f => ({ value: f, label: f })),
      ]
    : [{ value: '', label: '全部頻率' }]

  const filteredAnnualRows = annualMatrix
    ? annualMatrix.rows.filter(r => !annualFreq || r.frequency === annualFreq)
    : []

  const MONTH_LABELS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

  const ANNUAL_STATUS_LABEL: Record<string, string> = {
    completed: '已完成', overdue: '逾期', in_progress: '進行中',
    scheduled: '待執行', unscheduled: '未排定', non_month: '非本月',
    no_data: '應做未排', no_frequency: '頻率未設',
  }
  const ANNUAL_TOOLTIP_LABEL: Record<string, string> = {
    completed: '已完成', overdue: '逾期', in_progress: '進行中',
    scheduled: '待執行', unscheduled: '未排定', non_month: '非本月',
    no_data: '應做未排程', no_frequency: '頻率未設定',
  }

  const AnnualTab = (
    <div>
      {/* 篩選器 */}
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Select value={annualYear} onChange={setAnnualYear} options={yearNumOptions} style={{ width: 90 }} />
        </Col>
        <Col>
          <Select allowClear placeholder="全部類別" value={annualCat}
            onChange={setAnnualCat} options={annualCatOptions} style={{ width: 110 }} />
        </Col>
        <Col>
          <Select allowClear placeholder="全部頻率" value={annualFreq}
            onChange={setAnnualFreq} options={annualFreqOptions} style={{ width: 100 }} />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadAnnualMatrix} loading={annualLoading}>重新整理</Button>
        </Col>
      </Row>

      {/* 圖例 */}
      <Row gutter={4} style={{ marginBottom: 12 }}>
        {Object.entries(ANNUAL_CELL_STYLE).map(([k, v]) => (
          <Col key={k}>
            <span style={{ display:'inline-flex', alignItems:'center', gap:4, padding:'2px 8px',
              borderRadius:4, background:v.bg, border:'1px solid #eee', fontSize:12, color:v.color }}>
              {v.icon}&nbsp;{ANNUAL_STATUS_LABEL[k]}
            </span>
          </Col>
        ))}
      </Row>

      {/* 矩陣表格 */}
      <Spin spinning={annualLoading}>
        {annualMatrix && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width:'100%', borderCollapse:'collapse', fontSize:15, tableLayout:'auto' }}>
              <thead>
                <tr style={{ background:'#f0f4f8' }}>
                  <th style={{ ...ANNUAL_TH, fontSize:15, width:'1%' }}>類別</th>
                  <th style={{ ...ANNUAL_TH, fontSize:15, width:'1%' }}>保養項目</th>
                  <th style={{ ...ANNUAL_TH, fontSize:15, width:'1%' }}>頻率</th>
                  {MONTH_LABELS.map(m => <th key={m} style={{ ...ANNUAL_TH, fontSize:15, textAlign:'center' }}>{m}</th>)}
                </tr>
              </thead>
              <tbody>
                {filteredAnnualRows.map(row => (
                  <tr key={row.item_ragic_id} style={{ borderBottom:'1px solid #eee' }}>
                    <td style={{ ...ANNUAL_TD, whiteSpace:'nowrap' }}>
                      <Tag style={{ fontSize:14 }}>{row.category || '—'}</Tag>
                    </td>
                    <td style={{ ...ANNUAL_TD, whiteSpace:'nowrap' }}>
                      <Tooltip title={row.location || undefined}>
                        <span style={{ fontSize:15 }}>{row.task_name}</span>
                      </Tooltip>
                    </td>
                    <td style={{ ...ANNUAL_TD, textAlign:'center', whiteSpace:'nowrap' }}>
                      {row.frequency ? <Tag style={{ fontSize:14 }}>{row.frequency}</Tag> : '—'}
                    </td>
                    {row.cells.map(cell => {
                      const cs = ANNUAL_CELL_STYLE[cell.status] ?? ANNUAL_CELL_STYLE['no_frequency']
                      const clickable = cell.status !== 'non_month' && cell.status !== 'no_frequency'
                      return (
                        <td key={cell.month}
                          style={{ ...ANNUAL_TD, textAlign:'center', background:cs.bg, color:cs.color,
                            cursor:clickable?'pointer':'default', fontWeight:600, padding:'4px 2px', fontSize:18 }}
                          onClick={() => clickable && openAnnualCell(row, cell.schedule_id, cell.status, cell.month)}>
                          <Tooltip title={ANNUAL_TOOLTIP_LABEL[cell.status] ?? cell.status}>
                            <div style={{ lineHeight:1.2 }}>
                              {cs.icon}
                              {cell.scheduled_date && (
                                <div style={{ fontSize:13, fontWeight:500, color:cs.color,
                                  opacity:cell.status==='no_data'?1:0.85, marginTop:1 }}>
                                  {cell.scheduled_date}
                                </div>
                              )}
                            </div>
                          </Tooltip>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!annualMatrix && !annualLoading && (
          <Alert message="尚無資料，請先產生排程後再查看年度計劃表" type="info" showIcon />
        )}
      </Spin>

      {/* 底部摘要 */}
      {annualMatrix && (
        <Row style={{ marginTop: 12 }}>
          <Col>
            <Text type="secondary">
              共 {annualMatrix.summary.total_items} 個保養項目，本年已完成 {annualMatrix.summary.completed_count} 筆排程記錄
            </Text>
          </Col>
        </Row>
      )}
    </div>
  )

  // ── 頁面渲染 ──────────────────────────────────────────────────────────────
  return (
    <>
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
        </Row>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            { key: 'dashboard', label: 'Dashboard', children: DashboardTab },
            {
              key:      'daily-form',
              label:    <span><CalendarOutlined /> 每日巡檢表</span>,
              children: activeTab === 'daily-form' ? <FullBldgDailyFormTab /> : null,
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
            {
              key:      'schedule',
              label:    <span><ScheduleOutlined /> 排程管理</span>,
              children: ScheduleTab,
            },
            {
              key:      'annual',
              label:    <span><TableOutlined /> 年度計劃表</span>,
              children: AnnualTab,
            },
            { key: 'list', label: '批次清單', children: ListTab },
          ]}
        />
      </div>
      <MatrixDetailModal
        open={modalOpen}
        year={modalYear}
        month={modalMonth}
        metric={modalMetric}
        frequencyType={modalFreqType}
        monthLabel={modalMonthLabel}
        onClose={() => setModalOpen(false)}
      />
      <CatalogModal
        open={catalogOpen}
        frequencyType={catalogFreqType}
        items={catalogItems}
        loading={catalogLoading}
        onClose={() => setCatalogOpen(false)}
      />

      {/* ScheduleDrawer */}
      <Drawer
        open={schedDrawerOpen}
        width={480}
        onClose={() => { setSchedDrawerOpen(false); setSchedEditMode(false) }}
        title={schedDrawerItem && (
          <Space>
            <Tag>{schedDrawerItem.category || '未分類'}</Tag>
            <span style={{ fontWeight: 600 }}>{schedDrawerItem.task_name}</span>
            <Tag color={SCHED_STATUS_CFG[schedDrawerItem.status]?.tagColor ?? 'default'}>
              {SCHED_STATUS_CFG[schedDrawerItem.status]?.label ?? schedDrawerItem.status}
            </Tag>
            {schedDrawerItem.ragic_url && (
              <Tooltip title="在 Ragic 查看原始表單">
                <a
                  href={schedDrawerItem.ragic_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#4BA8E8', fontSize: 16, lineHeight: 1 }}
                >
                  <LinkOutlined />
                </a>
              </Tooltip>
            )}
          </Space>
        )}
        extra={
          !schedEditMode ? (
            <Button onClick={() => {
              setSchedEditMode(true)
              if (schedDrawerItem) {
                schedEditForm.setFieldsValue({
                  scheduled_date: schedDrawerItem.scheduled_date,
                  executor_name:  schedDrawerItem.executor_name,
                  start_time:     schedDrawerItem.start_time,
                  end_time:       schedDrawerItem.end_time,
                  is_completed:   schedDrawerItem.is_completed,
                  result_note:    schedDrawerItem.result_note,
                  abnormal_flag:  schedDrawerItem.abnormal_flag,
                  abnormal_note:  schedDrawerItem.abnormal_note,
                })
              }
            }}>編輯</Button>
          ) : (
            <Space>
              <Button onClick={() => setSchedEditMode(false)}>取消</Button>
              <Button type="primary" loading={schedEditLoading} onClick={handleScheduleSave}>儲存</Button>
            </Space>
          )
        }
      >
        {schedDrawerItem && !schedEditMode && (
          <div>
            <div style={{ marginBottom: 12 }}>
              {[
                { label: '月份',    value: schedDrawerItem.year_month },
                { label: '頻率',    value: schedDrawerItem.frequency || '—' },
                { label: '位置',    value: schedDrawerItem.location || '—' },
                { label: '預估工時', value: schedDrawerItem.estimated_minutes ? `${schedDrawerItem.estimated_minutes} 分鐘` : '—' },
                { label: '排定日期', value: schedDrawerItem.scheduled_date || '未排定' },
                { label: '執行人員', value: schedDrawerItem.executor_name || '—' },
                { label: '開始時間', value: schedDrawerItem.start_time || '—' },
                { label: '結束時間', value: schedDrawerItem.end_time || '—' },
              ].map(row => (
                <Row key={row.label} style={{ marginBottom: 8 }}>
                  <Col span={8}><Text type="secondary">{row.label}</Text></Col>
                  <Col span={16}><Text>{row.value}</Text></Col>
                </Row>
              ))}
              <Row style={{ marginBottom: 8 }}>
                <Col span={8}><Text type="secondary">完成</Text></Col>
                <Col span={16}>
                  <Tag color={schedDrawerItem.is_completed ? 'success' : 'default'}>
                    {schedDrawerItem.is_completed ? '已完成' : '未完成'}
                  </Tag>
                </Col>
              </Row>
              <Row style={{ marginBottom: 8 }}>
                <Col span={8}><Text type="secondary">異常</Text></Col>
                <Col span={16}>
                  {schedDrawerItem.abnormal_flag
                    ? <Tag color="error">異常：{schedDrawerItem.abnormal_note || '（無說明）'}</Tag>
                    : <Tag>無</Tag>}
                </Col>
              </Row>
              <Row style={{ marginBottom: 8 }}>
                <Col span={8}><Text type="secondary">備註</Text></Col>
                <Col span={16}><Text>{schedDrawerItem.result_note || '—'}</Text></Col>
              </Row>
              <Row style={{ marginBottom: 8 }}>
                <Col span={8}><Text type="secondary">來源</Text></Col>
                <Col span={16}>
                  <Tag color={schedDrawerItem.schedule_source === 'manual' ? 'purple' : 'cyan'}>
                    {schedDrawerItem.schedule_source === 'manual' ? '人工調整' : '自動產生'}
                  </Tag>
                </Col>
              </Row>
              {schedDrawerItem.portal_edited_at && (
                <Row style={{ marginBottom: 8 }}>
                  <Col span={8}><Text type="secondary">最後編輯</Text></Col>
                  <Col span={16}><Text style={{ fontSize: 12 }}>{schedDrawerItem.portal_edited_at}</Text></Col>
                </Row>
              )}
            </div>
          </div>
        )}
        {schedDrawerItem && schedEditMode && (
          <Form form={schedEditForm} layout="vertical">
            <Form.Item name="scheduled_date" label="排定日期（MM/DD）">
              <Input placeholder="如 05/15" />
            </Form.Item>
            <Form.Item name="executor_name" label="執行人員">
              <Input />
            </Form.Item>
            <Form.Item name="start_time" label="開始時間">
              <Input placeholder="如 2026/05/15 09:00" />
            </Form.Item>
            <Form.Item name="end_time" label="結束時間">
              <Input placeholder="如 2026/05/15 10:30" />
            </Form.Item>
            <Form.Item name="is_completed" label="標記完成" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="result_note" label="執行備註">
              <Input.TextArea rows={3} />
            </Form.Item>
            <Form.Item name="abnormal_flag" label="標記異常" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="abnormal_note" label="異常說明">
              <Input.TextArea rows={2} />
            </Form.Item>
          </Form>
        )}
      </Drawer>

      {/* AnnualCellDrawer */}
      <Drawer
        open={annualDrawerOpen}
        width={420}
        onClose={() => setAnnualDrawerOpen(false)}
        title={annualDrawerCell && (
          <Space>
            <Tag>{annualDrawerCell.row.category || '—'}</Tag>
            <span>{annualDrawerCell.row.task_name}</span>
            <Tag>{annualYear}/{String(annualDrawerCell.month).padStart(2, '0')}</Tag>
            {annualMatrix?.month_batch_urls?.[String(annualDrawerCell.month)] && (
              <Tooltip title="在 Ragic 查看原始表單">
                <a
                  href={annualMatrix.month_batch_urls[String(annualDrawerCell.month)]}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#4BA8E8', fontSize: 16, lineHeight: 1 }}
                >
                  <LinkOutlined />
                </a>
              </Tooltip>
            )}
          </Space>
        )}
      >
        {annualCellLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}><Spin tip="載入中…" /></div>
        ) : annualCellDetail ? (
          <div>
            {[
              { label: '狀態',    value: <Tag color={SCHED_STATUS_CFG[annualCellDetail.status]?.tagColor ?? 'default'}>{SCHED_STATUS_CFG[annualCellDetail.status]?.label ?? annualCellDetail.status}</Tag> },
              { label: '排定日期', value: annualCellDetail.scheduled_date || '未排定' },
              { label: '執行人員', value: annualCellDetail.executor_name || '—' },
              { label: '開始時間', value: annualCellDetail.start_time || '—' },
              { label: '結束時間', value: annualCellDetail.end_time || '—' },
              { label: '備註',    value: annualCellDetail.result_note || '—' },
            ].map(row => (
              <Row key={row.label} style={{ marginBottom: 10 }}>
                <Col span={8}><Text type="secondary">{row.label}</Text></Col>
                <Col span={16}>{typeof row.value === 'string' ? <Text>{row.value}</Text> : row.value}</Col>
              </Row>
            ))}
            {annualCellDetail.abnormal_flag && (
              <Row style={{ marginBottom: 10 }}>
                <Col span={8}><Text type="secondary">異常</Text></Col>
                <Col span={16}><Tag color="error">異常：{annualCellDetail.abnormal_note || '（無說明）'}</Tag></Col>
              </Row>
            )}
          </div>
        ) : annualDrawerCell?.status === 'no_data' ? (
          <Alert type="warning" showIcon
            message="此月份應執行保養但尚未產生排程，請至「排程管理」Tab 產生排程。"
          />
        ) : (
          <Alert type="info" showIcon message="此月份無排程記錄。" />
        )}
      </Drawer>
    </>
  )
}

// ── 矩陣格明細 Modal ──────────────────────────────────────────────────────────
const METRIC_LABELS: Record<string, string> = {
  prev_carry_over:   '截至上月底累計未結案數',
  prev_resolved:     '其中本月已結案數',
  period_total:      '本期應完成總數',
  period_completed:  '本期已完成',
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
  const [items,   setItems]   = useState<FullBldgPMMatrixItem[]>([])
  const [total,   setTotal]   = useState(0)

  useEffect(() => {
    if (!open || !year) return
    setLoading(true)
    fetchFullBldgPMMatrixItems({ year, month, metric, frequency_type: frequencyType || undefined })
      .then((res) => { setItems(res.items); setTotal(res.total) })
      .catch(() => { setItems([]); setTotal(0) })
      .finally(() => setLoading(false))
  }, [open, year, month, metric, frequencyType])

  const freqLabel = frequencyType === 'monthly' ? '每月' : frequencyType === 'quarterly' ? '每季' : frequencyType === 'yearly' ? '每年' : ''
  const metricLabel = METRIC_LABELS[metric] || metric
  const monthDisplay = month === 0 ? '全年' : monthLabel

  const columns: ColumnsType<FullBldgPMMatrixItem> = [
    { title: '保養月份', dataIndex: 'period_month', width: 90 },
    { title: '類別', dataIndex: 'category', width: 80,
      render: (v: string) => <Tag color="blue" style={{ fontSize: 11 }}>{v || '—'}</Tag> },
    { title: '保養項目', dataIndex: 'task_name', ellipsis: true },
    { title: '頻率', dataIndex: 'frequency', width: 70, align: 'center' as const,
      render: (v: string) => <Tag color="purple" style={{ fontSize: 11 }}>{v || '—'}</Tag> },
    { title: '排定日期', dataIndex: 'scheduled_date_full', width: 100 },
    { title: '狀態', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const color = v === '已完成' ? 'success' : v === '進行中' ? 'processing' : 'default'
        return <Tag color={color}>{v}</Tag>
      } },
    { title: '執行人員', dataIndex: 'executor_name', width: 90, ellipsis: true },
    { title: '備註', dataIndex: 'result_note', ellipsis: true,
      render: (v: string) => <Typography.Text style={{ fontSize: 11 }}>{v || '—'}</Typography.Text> },
  ]

  return (
    <Modal open={open} onCancel={onClose} footer={null} width={1000}
      title={
        <Space>
          <BarChartOutlined style={{ color: '#1677ff' }} />
          <span style={{ fontWeight: 600 }}>{year} 年 {monthDisplay}｜{freqLabel}｜{metricLabel}</span>
          {!loading && <Typography.Text type="secondary" style={{ fontSize: 12 }}>共 {total} 筆</Typography.Text>}
        </Space>
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin tip="載入明細中…" /></div>
      ) : (
        <Table dataSource={items} columns={columns}
          rowKey={(r) => `${r.ragic_id}-${r.batch_ragic_id}`}
          size="small" scroll={{ x: 900 }}
          pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 筆`, showSizeChanger: false }}
        />
      )}
    </Modal>
  )
}

// ── 保養項目目錄 Modal ────────────────────────────────────────────────────────
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
  items: FullBldgPMCatalogItem[]
  loading: boolean
  onClose: () => void
}) {
  const columns: ColumnsType<FullBldgPMCatalogItem> = [
    { title: '項次', dataIndex: 'seq_no', width: 60, align: 'center' as const,
      render: (v: number) => <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text> },
    { title: '類別', dataIndex: 'category', width: 90,
      render: (v: string) => <Tag color="blue" style={{ fontSize: 11 }}>{v}</Tag> },
    { title: '頻率', dataIndex: 'frequency', width: 80, align: 'center' as const,
      render: (v: string) => <Tag color="purple" style={{ fontSize: 11 }}>{v}</Tag> },
    { title: '保養項目', dataIndex: 'task_name',
      render: (v: string) => <Typography.Text style={{ fontSize: 12 }}>{v}</Typography.Text> },
    { title: '區域/位置', dataIndex: 'location', width: 120,
      render: (v: string) => <Typography.Text style={{ fontSize: 12 }}>{v || '—'}</Typography.Text> },
    { title: '執行月份', dataIndex: 'exec_months_raw', width: 130,
      render: (v: string) => <Typography.Text style={{ fontSize: 11, color: '#666' }}>{v || '—'}</Typography.Text> },
    { title: '預估工時', dataIndex: 'estimated_minutes', width: 90, align: 'center' as const,
      render: (v: number) => <Typography.Text style={{ fontSize: 12 }}>{v > 0 ? `${v} 分` : '—'}</Typography.Text> },
  ]

  const freqLabel = FREQ_TYPE_LABELS[frequencyType] || frequencyType

  return (
    <Modal open={open} onCancel={onClose} footer={null} width={900}
      title={
        <Space>
          <ToolOutlined style={{ color: '#764ba2' }} />
          <span style={{ fontWeight: 600 }}>{freqLabel}保養項目清單</span>
          {!loading && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>共 {items.length} 項</Typography.Text>
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
