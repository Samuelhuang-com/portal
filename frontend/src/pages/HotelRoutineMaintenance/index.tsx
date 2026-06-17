/**
 * 飯店例行維護主頁
 *
 * Tab 1「主管儀表板」：KPI 四卡 + 類別 Bar 圖 + 狀態 Donut 圖 + 逾期/即將到期預警
 * Tab 2「批次清單」：保養批次列表，含進度條、狀態標籤、操作入口
 * Tab 3「每月維護」：月統計（上月累計 / 本月完成 / 未完成說明）
 * Tab 4「每季維護」：季統計（上季累計 / 本季完成 / 月份分布）
 * Tab 5「每年維護」：年統計（上年累計 / 本年完成 / Q1-Q4 分布）
 */
import React, { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Progress, Alert, Select,
  message, Tooltip, Badge, Divider, Modal, Spin, Drawer,
  Descriptions, Form, Input, DatePicker, Switch,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, ToolOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, RightOutlined, BarChartOutlined,
  CalendarOutlined, LineChartOutlined, LinkOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchHotelRoutinePMStats, fetchHotelRoutinePMBatches, fetchHotelRoutinePMPeriodStats,
  fetchHotelRoutinePMYearMatrix, fetchHotelRoutinePMCalendar, fetchHotelRoutinePMBatchDetail,
  fetchHotelRoutinePMMatrixItems, fetchHotelRoutinePMCatalog,
  generateHotelRoutinePMSchedule, fetchHotelRoutinePMSchedule, fetchHotelRoutinePMScheduleKPI,
  fetchHotelRoutinePMOverdueSchedule, fetchHotelRoutinePMAnnualMatrix, updateHotelRoutinePMSchedule,
} from '@/api/hotelRoutineMaintenance'
import type { HotelRoutinePMCatalogItem } from '@/api/hotelRoutineMaintenance'
import type { HotelRoutinePMMatrixMetric, HotelRoutinePMMatrixItem } from '@/api/hotelRoutineMaintenance'
import type {
  HotelRoutinePMStats, HotelRoutinePMBatchListItem, HotelRoutinePMItem,
  HotelRoutinePMItemStatus, HotelRoutinePMPeriodStats,
  HotelRoutinePMIncompleteItem, HotelRoutinePMSubPeriodBreakdown,
  HotelRoutinePMYearMatrix, HotelRoutinePMYearMatrixMonth,
  HotelRoutinePMScheduleItem, HotelRoutinePMScheduleKPI,
  HotelRoutinePMScheduleGenerateResult,
  HotelRoutinePMScheduleAnnualMatrix, HotelRoutinePMMatrixCellStatus,
} from '@/types/hotelRoutineMaintenance'
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

function deriveBatchStatus(kpi: HotelRoutinePMBatchListItem['kpi']): string {
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
  data: HotelRoutinePMPeriodStats
  prevLabel: string
  currLabel: string
}
function PeriodKpiCards({ data, prevLabel, currLabel }: PeriodKpiCardsProps) {
  return (
    <>
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
  rows: HotelRoutinePMSubPeriodBreakdown[]
  title: string
}
function SubBreakdownTable({ rows, title }: SubBreakdownTableProps) {
  if (rows.length === 0) return null
  const cols: ColumnsType<HotelRoutinePMSubPeriodBreakdown> = [
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
      <Table<HotelRoutinePMSubPeriodBreakdown>
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
  items: HotelRoutinePMIncompleteItem[]
}
function IncompleteTable({ items }: IncompleteTableProps) {
  const cols: ColumnsType<HotelRoutinePMIncompleteItem> = [
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
        <Table<HotelRoutinePMIncompleteItem>
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

// ── 季度選擇卡片（Q1-Q4）────────────────────────────────────────────────────
interface QuarterSummary {
  q:          number
  months:     string
  total:      number
  completed:  number
  rate:       number | null
}

function deriveQuarterSummaries(matrix: HotelRoutinePMYearMatrix): QuarterSummary[] {
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
  matrix:    HotelRoutinePMYearMatrix
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
  key: keyof HotelRoutinePMYearMatrixMonth | '_sep1' | '_sep2'
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

function YearMatrixTable({ data, frequencyType, onCellClick }: { data: HotelRoutinePMYearMatrix; frequencyType?: string; onCellClick?: (year: number, month: number, metric: HotelRoutinePMMatrixMetric, monthLabel: string) => void }) {
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
    <Typography.Text type="secondary" style={{ fontSize: 18 }}>—</Typography.Text>
  )

  const CLICKABLE_METRIC_MAP: Record<string, HotelRoutinePMMatrixMetric> = {
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
      row[`m${m.month}`] = isSep ? null : m[metric.key as keyof HotelRoutinePMYearMatrixMonth]
    })
    return row
  })

  return (
    <Card
      title={<><BarChartOutlined /> {data.year} 年度例行維護統計總表</>}
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

// ── 年度計劃表儲存格樣式常數 ─────────────────────────────────────────────────
const TH: React.CSSProperties = {
  padding: '6px 8px', fontWeight: 600, border: '1px solid #e8e8e8',
  whiteSpace: 'nowrap', textAlign: 'left',
}
const TD: React.CSSProperties = {
  padding: '4px 8px', border: '1px solid #f0f0f0', verticalAlign: 'middle',
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function HotelRoutineMaintenancePage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats] = useState<HotelRoutinePMStats | null>(null)
  const [batches, setBatches] = useState<HotelRoutinePMBatchListItem[]>([])
  const [dashYear,  setDashYear]  = useState(dayjs().format('YYYY'))
  const [dashMonth, setDashMonth] = useState(dayjs().month() + 1)
  const [year, setYear] = useState(dayjs().format('YYYY'))
  const [loading, setLoading] = useState(false)
  const [calRows,   setCalRows]   = useState<CalendarRow[]>([])
  const [calMaxDay, setCalMaxDay] = useState(31)
  const [formItems,   setFormItems]   = useState<HotelRoutinePMItem[]>([])
  const [formLoading, setFormLoading] = useState(false)
  const [formYear,    setFormYear]    = useState(dayjs().format('YYYY'))
  const [formMonth,   setFormMonth]   = useState(dayjs().month() + 1)

  const [monthlyData,  setMonthlyData]  = useState<HotelRoutinePMPeriodStats | null>(null)
  const [monthlyYear,  setMonthlyYear]  = useState(dayjs().year())
  const [monthlyMonth, setMonthlyMonth] = useState(dayjs().month() + 1)
  const [monthlyLoading, setMonthlyLoading] = useState(false)

  const [matrixData,    setMatrixData]    = useState<HotelRoutinePMYearMatrix | null>(null)
  const [matrixLoading, setMatrixLoading] = useState(false)

  const [quarterlyData,        setQuarterlyData]        = useState<HotelRoutinePMPeriodStats | null>(null)
  const [quarterlyMatrixData,  setQuarterlyMatrixData]  = useState<HotelRoutinePMYearMatrix | null>(null)
  const [yearlyMatrixData,     setYearlyMatrixData]     = useState<HotelRoutinePMYearMatrix | null>(null)
  const [yearlyMatrixLoading,  setYearlyMatrixLoading]  = useState(false)
  const [quarterlyYear,        setQuarterlyYear]        = useState(dayjs().year())
  const [quarterlyQuarter,     setQuarterlyQuarter]     = useState(Math.ceil((dayjs().month() + 1) / 3))
  const [quarterlyLoading,     setQuarterlyLoading]     = useState(false)
  const [quarterlyMatrixLoading, setQuarterlyMatrixLoading] = useState(false)

  const [yearlyData,    setYearlyData]    = useState<HotelRoutinePMPeriodStats | null>(null)
  const [yearlyYear,    setYearlyYear]    = useState(dayjs().year())
  const [yearlyLoading, setYearlyLoading] = useState(false)

  const [catalogOpen,        setCatalogOpen]       = useState(false)
  const [catalogFreqType,    setCatalogFreqType]   = useState<'monthly' | 'quarterly' | 'yearly'>('monthly')
  const [catalogItems,       setCatalogItems]      = useState<HotelRoutinePMCatalogItem[]>([])
  const [catalogLoading,     setCatalogLoading]    = useState(false)

  const openCatalogModal = useCallback(async (freqType: 'monthly' | 'quarterly' | 'yearly') => {
    setCatalogFreqType(freqType)
    setCatalogOpen(true)
    setCatalogLoading(true)
    try {
      const res = await fetchHotelRoutinePMCatalog(freqType)
      setCatalogItems(res.items)
    } catch {
      setCatalogItems([])
    } finally {
      setCatalogLoading(false)
    }
  }, [])

  const [schedYear,       setSchedYear]       = useState(dayjs().year())
  const [schedMonth,      setSchedMonth]      = useState(dayjs().month() + 1)
  const [schedItems,      setSchedItems]      = useState<HotelRoutinePMScheduleItem[]>([])
  const [schedKpi,        setSchedKpi]        = useState<HotelRoutinePMScheduleKPI | null>(null)
  const [schedLoading,    setSchedLoading]    = useState(false)
  const [schedShouldDo,   setSchedShouldDo]   = useState(0)
  const [schedCatFilter,  setSchedCatFilter]  = useState<string | undefined>(undefined)
  const [schedStatusFilter, setSchedStatusFilter] = useState<string | undefined>(undefined)
  const [overdueItems,    setOverdueItems]    = useState<HotelRoutinePMScheduleItem[]>([])
  const [overdueTotal,    setOverdueTotal]    = useState(0)
  const [overdueMonths,   setOverdueMonths]   = useState<string[]>([])
  const [overdueLoading,  setOverdueLoading]  = useState(false)
  const [overdueVisible,  setOverdueVisible]  = useState(false)
  const [schedDrawerOpen, setSchedDrawerOpen] = useState(false)
  const [schedDrawerItem, setSchedDrawerItem] = useState<HotelRoutinePMScheduleItem | null>(null)
  const [schedEditMode,   setSchedEditMode]   = useState(false)
  const [schedEditForm]                       = Form.useForm()

  const schedYearMonth = `${schedYear}/${String(schedMonth).padStart(2, '0')}`

  const loadSchedule = useCallback(async () => {
    setSchedLoading(true)
    try {
      const [listRes, kpiRes] = await Promise.all([
        fetchHotelRoutinePMSchedule(schedYearMonth, schedCatFilter, schedStatusFilter),
        fetchHotelRoutinePMScheduleKPI(schedYearMonth),
      ])
      setSchedItems(listRes.items)
      setSchedShouldDo(listRes.should_do_not_done)
      setSchedKpi(kpiRes)
    } catch {
      message.error('載入排程資料失敗')
    } finally {
      setSchedLoading(false)
    }
  }, [schedYearMonth, schedCatFilter, schedStatusFilter])

  const loadOverdue = useCallback(async () => {
    setOverdueLoading(true)
    try {
      const res = await fetchHotelRoutinePMOverdueSchedule()
      setOverdueItems(res.items)
      setOverdueTotal(res.total)
      setOverdueMonths(res.months_affected)
    } catch {
      message.error('載入逾期資料失敗')
    } finally {
      setOverdueLoading(false)
    }
  }, [])

  const handleGenerateSchedule = useCallback(async () => {
    Modal.confirm({
      title: `產生 ${schedYearMonth} 保養排程`,
      content: '系統將依頻率規則自動產生排程，已完成與人工調整的記錄不會被覆蓋。確認繼續？',
      okText: '確認產生',
      cancelText: '取消',
      onOk: async () => {
        try {
          const res: HotelRoutinePMScheduleGenerateResult = await generateHotelRoutinePMSchedule(schedYear, schedMonth)
          message.success(
            `已產生 ${res.generated} 筆，更新 ${res.updated} 筆，` +
            `跳過已完成 ${res.skipped_completed} 筆，非本月 ${res.skipped_non_month} 筆`
          )
          loadSchedule()
        } catch {
          message.error('產生排程失敗')
        }
      },
    })
  }, [schedYear, schedMonth, schedYearMonth, loadSchedule])

  const openSchedDrawer = useCallback((item: HotelRoutinePMScheduleItem) => {
    setSchedDrawerItem(item)
    setSchedEditMode(false)
    setSchedDrawerOpen(true)
  }, [])

  const handleSchedUpdate = useCallback(async () => {
    if (!schedDrawerItem) return
    try {
      const values = await schedEditForm.validateFields()
      await updateHotelRoutinePMSchedule(schedDrawerItem.id, values)
      message.success('已更新')
      setSchedDrawerOpen(false)
      loadSchedule()
    } catch {
      message.error('更新失敗')
    }
  }, [schedDrawerItem, schedEditForm, loadSchedule])

  const [modalOpen,       setModalOpen]       = useState(false)
  const [modalYear,       setModalYear]       = useState(0)
  const [modalMonth,      setModalMonth]      = useState(0)
  const [modalMetric,     setModalMetric]     = useState<HotelRoutinePMMatrixMetric>('period_total')
  const [modalFreqType,   setModalFreqType]   = useState<string>('')
  const [modalMonthLabel, setModalMonthLabel] = useState('')

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const [s, calData] = await Promise.all([
        fetchHotelRoutinePMStats(dashYear, dashMonth),
        fetchHotelRoutinePMCalendar(parseInt(dashYear), dashMonth).catch(() => null),
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
      const data = await fetchHotelRoutinePMBatches(year)
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
      const data = await fetchHotelRoutinePMPeriodStats({ period_type: 'month', year: monthlyYear, month: monthlyMonth, frequency_type: 'monthly' })
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
      const data = await fetchHotelRoutinePMYearMatrix(monthlyYear, 'monthly')
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
      const data = await fetchHotelRoutinePMYearMatrix(quarterlyYear, 'quarterly')
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
      const data = await fetchHotelRoutinePMPeriodStats({ period_type: 'quarter', year: quarterlyYear, quarter: quarterlyQuarter, frequency_type: 'quarterly' })
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
      const data = await fetchHotelRoutinePMPeriodStats({ period_type: 'year', year: yearlyYear, frequency_type: 'yearly' })
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
      const data = await fetchHotelRoutinePMYearMatrix(yearlyYear, 'yearly')
      setYearlyMatrixData(data)
    } catch {
      message.error('載入年度矩陣失敗')
    } finally {
      setYearlyMatrixLoading(false)
    }
  }, [yearlyYear])

  const openDetailModal = (freqType: string, year: number, month: number, metric: HotelRoutinePMMatrixMetric, monthLabel: string) => {
    setModalFreqType(freqType)
    setModalYear(year)
    setModalMonth(month)
    setModalMetric(metric)
    setModalMonthLabel(monthLabel)
    setModalOpen(true)
  }

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  useEffect(() => {
    if (activeTab === 'list')      loadBatches()
    if (activeTab === 'monthly')   { loadYearMatrix(); loadMonthlyStats() }
    if (activeTab === 'quarterly') { loadQuarterlyMatrix(); loadQuarterlyStats() }
    if (activeTab === 'yearly')    { loadYearlyMatrix(); loadYearlyStats() }
  }, [activeTab, loadBatches, loadMonthlyStats, loadQuarterlyStats, loadYearlyStats, loadYearMatrix, loadQuarterlyMatrix, loadYearlyMatrix])

  useEffect(() => {
    if (activeTab === 'monthly')   loadYearMatrix()
  }, [loadYearMatrix])
  useEffect(() => {
    if (activeTab === 'quarterly') loadQuarterlyMatrix()
  }, [loadQuarterlyMatrix])

  useEffect(() => {
    if (activeTab === 'quarterly') loadQuarterlyStats()
  }, [loadQuarterlyStats])

  useEffect(() => {
    if (activeTab === 'schedule') loadSchedule()
  }, [activeTab, loadSchedule])

  useEffect(() => {
    if (activeTab === 'schedule') loadOverdue()
  }, [activeTab, loadOverdue])

  const loadFormItems = useCallback(async () => {
    setFormLoading(true)
    try {
      const batchList = await fetchHotelRoutinePMBatches(formYear)
      const targetPM  = `${formYear}/${String(formMonth).padStart(2, '0')}`
      const found     = batchList.find((b) => b.batch.period_month === targetPM)
      if (!found) { setFormItems([]); return }
      const detail = await fetchHotelRoutinePMBatchDetail(found.batch.ragic_id, { currentMonthOnly: true })
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
              <Table<HotelRoutinePMItem>
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
                        onClick={() => navigate(`/hotel/routine-maintenance/${row.batch_ragic_id}`)}
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
              <Table<HotelRoutinePMItem>
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
                        onClick={() => navigate(`/hotel/routine-maintenance/${row.batch_ragic_id}`)}
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
                onClick={() => navigate(`/hotel/routine-maintenance/${stats.current_batch!.ragic_id}`)}
                style={{ background: '#1B3A5C' }}
              >
                查看本月明細
              </Button>
            </Col>
          </Row>
        </Card>
      )}

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

  type FormRow = HotelRoutinePMItem & { _catRowSpan: number }

  const buildFormRows = (items: HotelRoutinePMItem[]): FormRow[] => {
    const buckets: Record<string, HotelRoutinePMItem[]> = {}
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
      render:    (v: HotelRoutinePMItemStatus) => {
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
  const batchColumns: ColumnsType<HotelRoutinePMBatchListItem> = [
    {
      title: '保養單號',
      dataIndex: ['batch', 'journal_no'],
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, fontWeight: 600 }}
          onClick={() => navigate(`/hotel/routine-maintenance/${row.batch.ragic_id}`)}>
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
      width: 160,
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Button
            type="primary"
            size="small"
            icon={<RightOutlined />}
            style={{ background: '#1B3A5C' }}
            onClick={() => navigate(`/hotel/routine-maintenance/${row.batch.ragic_id}`)}
          >
            查看明細
          </Button>
          {row.batch.ragic_url && (
            <Tooltip title="在 Ragic 查看原始表單">
              <a
                href={row.batch.ragic_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#4BA8E8', fontSize: 16, lineHeight: 1 }}
              >
                <LinkOutlined />
              </a>
            </Tooltip>
          )}
        </div>
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
      <Table<HotelRoutinePMBatchListItem>
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

  // ── 排程管理 Tab ────────────────────────────────────────────────────────────

  const SCHED_STATUS_CFG: Record<string, { label: string; color: string }> = {
    completed:   { label: '已完成', color: 'success' },
    in_progress: { label: '進行中', color: 'processing' },
    overdue:     { label: '逾期',   color: 'error' },
    scheduled:   { label: '待執行', color: 'warning' },
    unscheduled: { label: '未排定', color: 'default' },
  }

  const schedColumns: ColumnsType<HotelRoutinePMScheduleItem> = [
    {
      title: '類別', dataIndex: 'category', width: 80,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '保養項目', dataIndex: 'task_name',
      render: (v: string, row) => (
        <Button type="link" style={{ padding: 0, textAlign: 'left' }}
          onClick={() => openSchedDrawer(row)}>
          {v}
        </Button>
      ),
    },
    { title: '位置', dataIndex: 'location', width: 120,
      render: (v: string) => v || <Text type="secondary">—</Text> },
    { title: '頻率', dataIndex: 'frequency', width: 70,
      render: (v: string) => v ? <Tag>{v}</Tag> : <Text type="secondary">—</Text> },
    {
      title: '排定日期', dataIndex: 'scheduled_date', width: 90,
      render: (v: string) => v || <Text type="secondary">未排定</Text>,
    },
    {
      title: '執行人員', dataIndex: 'executor_name', width: 100,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '狀態', width: 90,
      render: (_: unknown, row: HotelRoutinePMScheduleItem) => {
        const cfg = SCHED_STATUS_CFG[row.status] ?? { label: row.status, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '來源', dataIndex: 'schedule_source', width: 80,
      render: (v: string) => (
        <Tag color={v === 'manual' ? 'purple' : 'cyan'}>{v === 'manual' ? '人工' : '自動'}</Tag>
      ),
    },
    {
      title: '操作', width: 70,
      render: (_: unknown, row: HotelRoutinePMScheduleItem) => (
        <Button size="small" onClick={() => openSchedDrawer(row)}>詳情</Button>
      ),
    },
  ]

  const overdueColumns: ColumnsType<HotelRoutinePMScheduleItem & { overdue_days?: number }> = [
    { title: '月份', dataIndex: 'year_month', width: 90 },
    { title: '類別', dataIndex: 'category',   width: 80 },
    { title: '保養項目', dataIndex: 'task_name' },
    { title: '排定日期', dataIndex: 'scheduled_date', width: 90 },
    {
      title: '逾期天數', dataIndex: 'overdue_days', width: 90,
      render: (v?: number) => v != null
        ? <Tag color="error">{v} 天</Tag>
        : <Text type="secondary">—</Text>,
    },
    {
      title: '操作', width: 70,
      render: (_: unknown, row: HotelRoutinePMScheduleItem) => (
        <Button size="small" onClick={() => openSchedDrawer(row)}>處理</Button>
      ),
    },
  ]

  const schedCatOptions = [
    { value: '', label: '全部類別' },
    ...Array.from(new Set(schedItems.map(i => i.category).filter(Boolean)))
      .map(c => ({ value: c, label: c })),
  ]

  const ScheduleTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }} wrap>
        <Col>
          <Select
            value={schedYear}
            onChange={setSchedYear}
            options={yearNumOptions}
            style={{ width: 90 }}
          />
        </Col>
        <Col>
          <Select
            value={schedMonth}
            onChange={setSchedMonth}
            style={{ width: 80 }}
            options={Array.from({ length: 12 }, (_, i) => ({
              value: i + 1, label: `${i + 1} 月`,
            }))}
          />
        </Col>
        <Col>
          <Select
            allowClear
            placeholder="全部類別"
            value={schedCatFilter}
            onChange={setSchedCatFilter}
            options={schedCatOptions}
            style={{ width: 110 }}
          />
        </Col>
        <Col>
          <Select
            allowClear
            placeholder="全部狀態"
            value={schedStatusFilter}
            onChange={setSchedStatusFilter}
            style={{ width: 110 }}
            options={[
              { value: 'unscheduled', label: '未排定' },
              { value: 'scheduled',   label: '待執行' },
              { value: 'in_progress', label: '進行中' },
              { value: 'overdue',     label: '逾期'   },
              { value: 'completed',   label: '已完成' },
              { value: 'abnormal',    label: '異常'   },
            ]}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadSchedule} loading={schedLoading}>
            重新整理
          </Button>
        </Col>
        <Col>
          <Button
            type="primary"
            style={{ background: '#1B3A5C' }}
            onClick={handleGenerateSchedule}
          >
            ▶ 產生本月排程
          </Button>
        </Col>
      </Row>

      {schedShouldDo > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message={
            <span>
              本月尚有 <strong>{schedShouldDo}</strong> 筆項目依頻率應執行，但尚未納入排程。
              請點擊「產生本月排程」補建，或確認是否確實無需保養。
            </span>
          }
        />
      )}

      {schedKpi && (
        <Row gutter={8} style={{ marginBottom: 16 }}>
          {[
            { label: '全部',      value: schedKpi.total,               color: '#1B3A5C' },
            { label: '應做未做',  value: schedShouldDo,                 color: '#FA8C16' },
            { label: '未排定',    value: schedKpi.unscheduled,          color: '#FAAD14' },
            { label: '待執行',    value: schedKpi.scheduled,            color: '#4BA8E8' },
            { label: '進行中',    value: schedKpi.in_progress,          color: '#52C41A' },
            { label: '逾期',      value: schedKpi.overdue,              color: '#C0392B' },
            { label: '已完成',    value: schedKpi.completed,            color: '#52C41A' },
            { label: '異常',      value: schedKpi.abnormal,             color: '#722ED1' },
          ].map(({ label, value, color }) => (
            <Col key={label}>
              <Card size="small" style={{ minWidth: 80, textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
                <div style={{ fontSize: 11, color: '#666' }}>{label}</div>
              </Card>
            </Col>
          ))}
          <Col>
            <Card size="small" style={{ minWidth: 90, textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#52C41A' }}>
                {schedKpi.completion_rate}%
              </div>
              <div style={{ fontSize: 11, color: '#666' }}>完成率</div>
            </Card>
          </Col>
        </Row>
      )}

      <Table<HotelRoutinePMScheduleItem>
        dataSource={schedItems}
        rowKey="id"
        columns={schedColumns}
        loading={schedLoading}
        size="small"
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無排程資料，請先點擊「產生本月排程」' }}
        rowClassName={(row) => row.status === 'overdue' ? 'ant-table-row-danger' : ''}
      />

      <Divider orientation="left">
        <span
          style={{ cursor: 'pointer', color: overdueTotal > 0 ? '#C0392B' : undefined }}
          onClick={() => { setOverdueVisible(v => !v); if (!overdueItems.length) loadOverdue() }}
        >
          逾期未執行（跨月累積）
          {overdueTotal > 0 && <Badge count={overdueTotal} style={{ marginLeft: 8 }} />}
        </span>
      </Divider>
      {overdueVisible && (
        <Table<HotelRoutinePMScheduleItem & { overdue_days?: number }>
          dataSource={overdueItems as (HotelRoutinePMScheduleItem & { overdue_days?: number })[]}
          rowKey="id"
          columns={overdueColumns}
          loading={overdueLoading}
          size="small"
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
          locale={{ emptyText: '無逾期未執行記錄' }}
        />
      )}
    </div>
  )

  // ── 排程明細 Drawer ────────────────────────────────────────────────────────
  const ScheduleDrawer = (
    <Drawer
      open={schedDrawerOpen}
      onClose={() => setSchedDrawerOpen(false)}
      width={480}
      title={
        schedDrawerItem && (
          <Space>
            <Tag>{schedDrawerItem.category || '未分類'}</Tag>
            <span style={{ fontWeight: 600 }}>{schedDrawerItem.task_name}</span>
            <Tag color={
              SCHED_STATUS_CFG[schedDrawerItem.status]?.color ?? 'default'
            }>
              {SCHED_STATUS_CFG[schedDrawerItem.status]?.label ?? schedDrawerItem.status}
            </Tag>
            {schedDrawerItem.item_ragic_id && (
              <Tooltip title="在 Ragic 查看原始表單">
                <a
                  href={`https://ap12.ragic.com/soutlet001/routine-maintenance/6/${schedDrawerItem.item_ragic_id.split('_')[0]}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#4BA8E8', fontSize: 16, lineHeight: 1 }}
                >
                  <LinkOutlined />
                </a>
              </Tooltip>
            )}
          </Space>
        )
      }
      extra={
        <Space>
          {!schedEditMode && (
            <Button size="small" onClick={() => {
              setSchedEditMode(true)
              schedEditForm.setFieldsValue(schedDrawerItem)
            }}>
              編輯
            </Button>
          )}
          {schedEditMode && (
            <>
              <Button size="small" onClick={() => setSchedEditMode(false)}>取消</Button>
              <Button size="small" type="primary" onClick={handleSchedUpdate}>儲存</Button>
            </>
          )}
        </Space>
      }
    >
      {schedDrawerItem && !schedEditMode && (
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="月份">{schedDrawerItem.year_month}</Descriptions.Item>
          <Descriptions.Item label="頻率">{schedDrawerItem.frequency || '—'}</Descriptions.Item>
          <Descriptions.Item label="位置">{schedDrawerItem.location || '—'}</Descriptions.Item>
          <Descriptions.Item label="預估工時">
            {schedDrawerItem.estimated_minutes ? `${schedDrawerItem.estimated_minutes} 分鐘` : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="排定日期">{schedDrawerItem.scheduled_date || '未排定'}</Descriptions.Item>
          <Descriptions.Item label="執行人員">{schedDrawerItem.executor_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="開始時間">{schedDrawerItem.start_time || '—'}</Descriptions.Item>
          <Descriptions.Item label="結束時間">{schedDrawerItem.end_time || '—'}</Descriptions.Item>
          <Descriptions.Item label="完成">
            <Tag color={schedDrawerItem.is_completed ? 'success' : 'default'}>
              {schedDrawerItem.is_completed ? '已完成' : '未完成'}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="異常">
            {schedDrawerItem.abnormal_flag
              ? <Tag color="error">異常：{schedDrawerItem.abnormal_note || '—'}</Tag>
              : <Tag color="default">無</Tag>}
          </Descriptions.Item>
          <Descriptions.Item label="備註">{schedDrawerItem.result_note || '—'}</Descriptions.Item>
          <Descriptions.Item label="來源">
            <Tag color={schedDrawerItem.schedule_source === 'manual' ? 'purple' : 'cyan'}>
              {schedDrawerItem.schedule_source === 'manual' ? '人工調整' : '自動產生'}
            </Tag>
          </Descriptions.Item>
          {schedDrawerItem.portal_edited_at && (
            <Descriptions.Item label="最後編輯">{schedDrawerItem.portal_edited_at}</Descriptions.Item>
          )}
        </Descriptions>
      )}
      {schedEditMode && (
        <Form form={schedEditForm} layout="vertical" size="small">
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
  )

  // ── 年度計劃表 Tab ────────────────────────────────────────────────────────

  const [annualYear,    setAnnualYear]    = useState(dayjs().year())
  const [annualCat,     setAnnualCat]     = useState<string | undefined>(undefined)
  const [annualFreq,    setAnnualFreq]    = useState<string | undefined>(undefined)
  const [annualMatrix,  setAnnualMatrix]  = useState<HotelRoutinePMScheduleAnnualMatrix | null>(null)
  const [annualLoading, setAnnualLoading] = useState(false)
  const [annualDrawerOpen, setAnnualDrawerOpen] = useState(false)
  const [annualDrawerCell, setAnnualDrawerCell] = useState<{
    scheduleId: number | null; status: HotelRoutinePMMatrixCellStatus; month: number; row: HotelRoutinePMScheduleAnnualMatrix['rows'][0]
  } | null>(null)
  const [annualCellDetail, setAnnualCellDetail] = useState<HotelRoutinePMScheduleItem | null>(null)
  const [annualCellLoading, setAnnualCellLoading] = useState(false)

  const loadAnnualMatrix = useCallback(async () => {
    setAnnualLoading(true)
    try {
      const res = await fetchHotelRoutinePMAnnualMatrix(annualYear, annualCat)
      setAnnualMatrix(res)
    } catch {
      message.error('載入年度計劃表失敗')
    } finally {
      setAnnualLoading(false)
    }
  }, [annualYear, annualCat])

  useEffect(() => {
    if (activeTab === 'annual') loadAnnualMatrix()
  }, [activeTab, loadAnnualMatrix])

  const openAnnualDrawer = useCallback(async (
    scheduleId: number | null,
    status: HotelRoutinePMMatrixCellStatus,
    month: number,
    row: HotelRoutinePMScheduleAnnualMatrix['rows'][0],
  ) => {
    setAnnualDrawerCell({ scheduleId, status, month, row })
    setAnnualDrawerOpen(true)
    setAnnualCellDetail(null)
    if (scheduleId) {
      setAnnualCellLoading(true)
      try {
        const res = await fetchHotelRoutinePMSchedule(
          `${annualYear}/${String(month).padStart(2, '0')}`,
        )
        const found = res.items.find(i => i.id === scheduleId) ?? null
        setAnnualCellDetail(found)
      } finally {
        setAnnualCellLoading(false)
      }
    }
  }, [annualYear])

  const MATRIX_CELL_CFG: Record<HotelRoutinePMMatrixCellStatus, { bg: string; text: string; label: string }> = {
    completed:    { bg: '#f6ffed', text: '#52C41A', label: '✅' },
    overdue:      { bg: '#fff1f0', text: '#C0392B', label: '🔴' },
    in_progress:  { bg: '#e6f4ff', text: '#1890FF', label: '🔵' },
    scheduled:    { bg: '#fff7e6', text: '#FA8C16', label: '⭕' },
    unscheduled:  { bg: '#fffbe6', text: '#FAAD14', label: '?' },
    non_month:    { bg: '#fafafa', text: '#aaa',    label: '─' },
    no_data:      { bg: '#fff0f6', text: '#eb2f96', label: '！' },
    no_frequency: { bg: '#f5f5f5', text: '#ccc',    label: '∅' },
  }

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

  const MONTHS = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

  const AnnualTab = (
    <div>
      <Row gutter={8} align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Select value={annualYear} onChange={setAnnualYear} options={yearNumOptions} style={{ width: 90 }} />
        </Col>
        <Col>
          <Select allowClear placeholder="全部類別" value={annualCat} onChange={setAnnualCat}
            options={annualCatOptions} style={{ width: 110 }} />
        </Col>
        <Col>
          <Select allowClear placeholder="全部頻率" value={annualFreq} onChange={setAnnualFreq}
            options={annualFreqOptions} style={{ width: 100 }} />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadAnnualMatrix} loading={annualLoading}>重新整理</Button>
        </Col>
      </Row>

      <Row gutter={4} style={{ marginBottom: 12 }}>
        {(Object.entries(MATRIX_CELL_CFG) as [HotelRoutinePMMatrixCellStatus, { bg: string; text: string; label: string }][]).map(([k, v]) => (
          <Col key={k}>
            <span style={{ display:'inline-flex', alignItems:'center', gap:4, padding:'2px 8px',
              borderRadius:4, background:v.bg, border:'1px solid #eee', fontSize:12, color:v.text }}>
              {v.label}&nbsp;{{ completed:'已完成', overdue:'逾期', in_progress:'進行中',
                scheduled:'待執行', unscheduled:'未排定', non_month:'非本月',
                no_data:'應做未排', no_frequency:'頻率未設' }[k]}
            </span>
          </Col>
        ))}
      </Row>

      <Spin spinning={annualLoading}>
        {annualMatrix && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width:'100%', borderCollapse:'collapse', fontSize:16, tableLayout:'auto' }}>
              <thead>
                <tr style={{ background:'#f0f4f8' }}>
                  <th style={{ ...TH, fontSize:16, width:'1%', whiteSpace:'nowrap' }}>類別</th>
                  <th style={{ ...TH, fontSize:16, width:'1%', whiteSpace:'nowrap' }}>保養項目</th>
                  <th style={{ ...TH, fontSize:16, width:'1%', whiteSpace:'nowrap' }}>頻率</th>
                  {MONTHS.map(m => <th key={m} style={{ ...TH, fontSize:16, textAlign:'center' }}>{m}</th>)}
                </tr>
              </thead>
              <tbody>
                {filteredAnnualRows.map(row => (
                  <tr key={row.item_ragic_id} style={{ borderBottom:'1px solid #eee' }}>
                    <td style={{ ...TD, whiteSpace:'nowrap' }}><Tag style={{ fontSize:14 }}>{row.category || '—'}</Tag></td>
                    <td style={{ ...TD, whiteSpace:'nowrap' }}>
                      <Tooltip title={row.location || undefined}>
                        <span style={{ fontSize:16 }}>{row.task_name}</span>
                      </Tooltip>
                    </td>
                    <td style={{ ...TD, textAlign:'center', whiteSpace:'nowrap' }}>
                      {row.frequency ? <Tag style={{ fontSize:14 }}>{row.frequency}</Tag> : '—'}
                    </td>
                    {row.cells.map(cell => {
                      const cfg = MATRIX_CELL_CFG[cell.status]
                      const clickable = cell.status !== 'non_month' && cell.status !== 'no_frequency'
                      return (
                        <td key={cell.month} style={{ ...TD, textAlign:'center', background:cfg.bg, color:cfg.text,
                          cursor:clickable ? 'pointer' : 'default', fontWeight:600, padding:'4px 2px', fontSize:18 }}
                          onClick={() => clickable && openAnnualDrawer(cell.schedule_id, cell.status, cell.month, row)}>
                          <Tooltip title={{ completed:'已完成', overdue:'逾期', in_progress:'進行中',
                            scheduled:'待執行', unscheduled:'未排定', non_month:'非本月',
                            no_data:'應做未排程', no_frequency:'頻率未設定' }[cell.status]}>
                            <div style={{ lineHeight: 1.2 }}>
                              {cfg.label}
                              {cell.scheduled_date && (
                                <div style={{ fontSize: 12, fontWeight: 500, color: cfg.text,
                                  opacity: cell.status === 'no_data' ? 1 : 0.85, marginTop: 1 }}>
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
      {annualMatrix && (
        <Row style={{ marginTop:12 }}>
          <Col>
            <Text type="secondary">
              共 {annualMatrix.summary.total_items} 個保養項目，本年已完成 {annualMatrix.summary.completed_count} 筆排程記錄
            </Text>
          </Col>
        </Row>
      )}
    </div>
  )

  const AnnualCellDrawer = (
    <Drawer open={annualDrawerOpen} onClose={() => setAnnualDrawerOpen(false)} width={420}
      title={annualDrawerCell && (
        <Space>
          <Tag>{annualDrawerCell.row.category || '—'}</Tag>
          <span>{annualDrawerCell.row.task_name}</span>
          <Tag>{annualYear}/{String(annualDrawerCell.month).padStart(2,'0')}</Tag>
          {annualDrawerCell.row.item_ragic_id && (
            <Tooltip title="在 Ragic 查看原始表單">
              <a
                href={`https://ap12.ragic.com/soutlet001/routine-maintenance/6/${annualDrawerCell.row.item_ragic_id.split('_')[0]}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#4BA8E8', fontSize: 16, lineHeight: 1 }}
              >
                <LinkOutlined />
              </a>
            </Tooltip>
          )}
        </Space>
      )}>
      {annualCellLoading && <Spin />}
      {!annualCellLoading && annualCellDetail && (
        <Descriptions column={1} size="small" bordered>
          <Descriptions.Item label="狀態">
            <Tag color={SCHED_STATUS_CFG[annualCellDetail.status]?.color ?? 'default'}>
              {SCHED_STATUS_CFG[annualCellDetail.status]?.label ?? annualCellDetail.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="排定日期">{annualCellDetail.scheduled_date || '—'}</Descriptions.Item>
          <Descriptions.Item label="執行人員">{annualCellDetail.executor_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="開始時間">{annualCellDetail.start_time || '—'}</Descriptions.Item>
          <Descriptions.Item label="結束時間">{annualCellDetail.end_time || '—'}</Descriptions.Item>
          <Descriptions.Item label="備註">{annualCellDetail.result_note || '—'}</Descriptions.Item>
          {annualCellDetail.abnormal_flag && (
            <Descriptions.Item label="異常">
              <Tag color="error">{annualCellDetail.abnormal_note || '有異常'}</Tag>
            </Descriptions.Item>
          )}
        </Descriptions>
      )}
      {!annualCellLoading && !annualCellDetail && annualDrawerCell && (
        <Alert type={annualDrawerCell.status === 'no_data' ? 'warning' : 'info'} showIcon
          message={annualDrawerCell.status === 'no_data'
            ? '此月份應執行保養但尚未產生排程，請至「排程明細」Tab 確認。'
            : '此月份無排程記錄。'} />
      )}
    </Drawer>
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
        <YearMatrixTable data={matrixData} frequencyType='monthly' onCellClick={(y, m, metric, lbl) => openDetailModal('monthly', y, m, metric, lbl)} />
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
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.hotel },
          { title: '飯店例行維護' },
        ]}
      />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <ToolOutlined /> 飯店例行維護
          </Title>
        </Col>
      </Row>

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
          {
            key: 'schedule',
            label: <span><CalendarOutlined /> 排程明細</span>,
            children: ScheduleTab,
          },
          {
            key: 'annual',
            label: <span><BarChartOutlined /> 年度計劃表</span>,
            children: AnnualTab,
          },
          { key: 'list',      label: '批次清單',    children: ListTab },
        ]}
      />
    </div>

    {ScheduleDrawer}

    {AnnualCellDrawer}

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
  metric: HotelRoutinePMMatrixMetric
  frequencyType: string
  monthLabel: string
  onClose: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [items,   setItems]   = useState<HotelRoutinePMMatrixItem[]>([])
  const [total,   setTotal]   = useState(0)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetchHotelRoutinePMMatrixItems({ year, month, metric, frequency_type: frequencyType })
      .then((res) => { setItems(res.items); setTotal(res.total) })
      .catch(() => message.error('載入明細失敗'))
      .finally(() => setLoading(false))
  }, [open, year, month, metric, frequencyType])

  const columns: ColumnsType<HotelRoutinePMMatrixItem> = [
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
  items: HotelRoutinePMCatalogItem[]
  loading: boolean
  onClose: () => void
}) {
  const columns: ColumnsType<HotelRoutinePMCatalogItem> = [
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
