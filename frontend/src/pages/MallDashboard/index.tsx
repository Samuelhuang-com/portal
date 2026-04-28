/**
 * 商場週期保養 Dashboard
 *
 * Tab 1「統計總覽」：KPI 卡 + 樓層比較圖 + 狀態圓餅 + 趨勢圖 + 重點追蹤清單
 * Tab 2「週期保養」：商場週期保養批次清單（原 /mall/periodic-maintenance）
 * Tab 3「B4F 巡檢」：B4F 每日巡檢紀錄
 * Tab 4「RF 巡檢」 ：RF 每日巡檢紀錄
 * Tab 5「B2F 巡檢」：B2F 每日巡檢紀錄
 * Tab 6「B1F 巡檢」：B1F 每日巡檢紀錄
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Row, Col, Card, Table, Tag, Button, Space,
  Typography, Breadcrumb, Select, Segmented, Alert,
  message, Badge, DatePicker, Tooltip, Tabs, Divider,
  Progress,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, WarningOutlined,
  CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
  BarChartOutlined, SafetyOutlined, CalendarOutlined,
  DashboardOutlined, RightOutlined, AlertOutlined, QuestionCircleOutlined,
  SyncOutlined, ToolOutlined,
} from '@ant-design/icons'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RcTooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

// ── API ────────────────────────────────────────────────────────────────────────
import {
  fetchDashboardSummary,
  fetchDashboardIssues,
  fetchDashboardTrend,
} from '@/api/mallDashboard'
import { fetchMallPMBatches, syncMallPMFromRagic } from '@/api/mallPeriodicMaintenance'
import { fetchB4FBatches, syncB4FFromRagic } from '@/api/b4fInspection'
import { fetchRFBatches,  syncRFFromRagic  } from '@/api/rfInspection'
import { fetchB2FBatches, syncB2FFromRagic } from '@/api/b2fInspection'
import { fetchB1FBatches, syncB1FFromRagic } from '@/api/b1fInspection'

// ── Types ──────────────────────────────────────────────────────────────────────
import type {
  DashboardSummary, FloorInspectionStats, IssueItem, TrendPoint,
} from '@/types/mallDashboard'
import type { PMBatchListItem } from '@/types/periodicMaintenance'
import type { InspectionBatchListItem  } from '@/types/b4fInspection'
import type { RFInspectionBatchListItem } from '@/types/rfInspection'
import type { B2FInspectionBatchListItem } from '@/types/b2fInspection'
import type { B1FInspectionBatchListItem } from '@/types/b1fInspection'

import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import { MALL_KPI_DESC } from '@/constants/kpiDesc/mallDashboard'

const { Title, Text } = Typography

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

// PM 批次狀態推導
const BATCH_STATUS_CFG: Record<string, { label: string; color: string }> = {
  draft:     { label: '草稿',   color: '#999999' },
  active:    { label: '執行中', color: '#4BA8E8' },
  completed: { label: '已完成', color: '#52C41A' },
  abnormal:  { label: '有異常', color: '#722ED1' },
  closed:    { label: '已結案', color: '#1B3A5C' },
}
function derivePMBatchStatus(kpi: PMBatchListItem['kpi']): string {
  if (!kpi || kpi.total === 0) return 'draft'
  if (kpi.abnormal > 0) return 'abnormal'
  if (kpi.completed === kpi.total) return 'completed'
  if (kpi.in_progress > 0 || kpi.completed > 0) return 'active'
  return 'draft'
}

// 巡檢批次狀態推導（B4F / RF / B2F / B1F 共用結構）
function deriveInspBatchStatus(kpi: {
  total: number; abnormal: number; pending: number; unchecked: number; completion_rate: number
}): { label: string; color: string } {
  if (!kpi || kpi.total === 0) return { label: '草稿',   color: '#999' }
  if (kpi.abnormal > 0)        return { label: '有異常', color: '#FF4D4F' }
  if (kpi.pending > 0)         return { label: '待處理', color: '#FAAD14' }
  if (kpi.unchecked === 0)     return { label: '已完成', color: '#52C41A' }
  if (kpi.completion_rate > 0) return { label: '巡檢中', color: '#4BA8E8' }
  return { label: '未開始', color: '#999' }
}

// ── Sub：KPI 卡片 ─────────────────────────────────────────────────────────────

function KpiCard({
  title, value, suffix = '', color, icon, sub, onClick, desc,
}: {
  title: string; value: string | number; suffix?: string
  color: string; icon: React.ReactNode; sub?: string
  onClick?: () => void; desc?: string
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
      <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
        {title}
        {desc && (
          <Tooltip title={desc} placement="top">
            <QuestionCircleOutlined
              style={{ color: '#bbb', fontSize: 11, marginLeft: 4, cursor: 'help' }}
              onClick={e => e.stopPropagation()}
            />
          </Tooltip>
        )}
      </div>
      {sub && <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </Card>
  )
}

// ── Sub：樓層橫條比較圖 ───────────────────────────────────────────────────────

function FloorCompareChart({ floors }: { floors: FloorInspectionStats[] }) {
  if (!floors.length) return <div style={{ textAlign: 'center', color: '#999', paddingTop: 60 }}>暫無資料</div>
  const data = floors.map(f => ({
    name:   f.floor_label,
    完成率: f.completion_rate,
    異常數: f.abnormal_items + f.pending_items,
    未巡檢: f.unchecked_items,
    fill:   FLOOR_COLORS[f.floor] ?? '#999',
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
              {data.map((entry, idx) => <Cell key={idx} fill={entry.fill} />)}
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
            <Bar dataKey="異常數" stackId="a" fill="#FF4D4F" />
            <Bar dataKey="未巡檢" stackId="a" fill="#CCCCCC" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Col>
    </Row>
  )
}

// ── Sub：巡檢狀態圓餅 ─────────────────────────────────────────────────────────

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

// ── Sub：共用巡檢批次清單（B4F / RF / B2F / B1F 共用相同欄位結構）─────────────

interface GenericBatch {
  ragic_id: string; inspection_date: string; inspector_name: string
  start_time: string; end_time: string; work_hours: string
}
interface GenericKPI {
  total: number; unchecked: number; abnormal: number; pending: number; completion_rate: number
}
interface GenericBatchItem { batch: GenericBatch; kpi: GenericKPI }

function InspectionListTab({
  batches, loading, syncing, yearMonth,
  onYearMonthChange, onReload, onSync, detailPath,
}: {
  floor?: string
  batches: GenericBatchItem[]; loading: boolean; syncing: boolean
  yearMonth: string
  onYearMonthChange: (ym: string) => void
  onReload: () => void; onSync: () => void
  detailPath: (id: string) => string
}) {
  const navigate = useNavigate()

  const columns: ColumnsType<GenericBatchItem> = [
    {
      title: '巡檢日期', dataIndex: ['batch', 'inspection_date'], width: 110,
      sorter: (a, b) => a.batch.inspection_date.localeCompare(b.batch.inspection_date),
      defaultSortOrder: 'descend',
    },
    {
      title: '開始時間', dataIndex: ['batch', 'start_time'], width: 140,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title: '結束時間', dataIndex: ['batch', 'end_time'], width: 140,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title: '工時', dataIndex: ['batch', 'work_hours'], width: 85,
      render: (v) => v ? <Tag color="geekblue">{v}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: '巡檢人員', dataIndex: ['batch', 'inspector_name'], width: 100,
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, fontWeight: 600 }}
          onClick={() => navigate(detailPath(row.batch.ragic_id))}>
          {v || row.batch.ragic_id}
        </Button>
      ),
    },
    {
      title: '狀態', width: 90,
      render: (_, row) => {
        const s = deriveInspBatchStatus(row.kpi)
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '巡檢進度', width: 200,
      render: (_, row) => {
        const { completion_rate, total, unchecked } = row.kpi
        return (
          <div>
            <Progress percent={completion_rate} size="small"
              strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
              format={() => `${completion_rate}%`} />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {total - unchecked} / {total} 已巡檢
            </Text>
          </div>
        )
      },
    },
    {
      title: '異常', dataIndex: ['kpi', 'abnormal'], width: 65, align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理', dataIndex: ['kpi', 'pending'], width: 65, align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '操作', width: 90,
      render: (_, row) => (
        <Button type="primary" size="small" icon={<RightOutlined />}
          style={{ background: '#1B3A5C' }}
          onClick={() => navigate(detailPath(row.batch.ragic_id))}>
          查看明細
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <DatePicker picker="month" value={dayjs(yearMonth, 'YYYY/MM')} format="YYYY/MM"
            allowClear={false}
            onChange={(d) => { if (d) onYearMonthChange(d.format('YYYY/MM')) }} />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={onReload} loading={loading}>重新整理</Button>
        </Col>
        <Col flex="auto" />
        <Col>
          <Button icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={onSync}>
            同步 Ragic
          </Button>
        </Col>
      </Row>
      <Table<GenericBatchItem>
        dataSource={batches}
        rowKey={(r) => r.batch.ragic_id}
        columns={columns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢紀錄' }}
      />
    </div>
  )
}

// ── Sub：週期保養批次清單 ──────────────────────────────────────────────────────

function PMListTab({
  batches, loading, syncing, year, onYearChange, onReload, onSync,
}: {
  batches: PMBatchListItem[]; loading: boolean; syncing: boolean
  year: string; onYearChange: (y: string) => void
  onReload: () => void; onSync: () => void
}) {
  const navigate = useNavigate()
  const yearOptions = [2024, 2025, 2026, 2027].map(y => ({ value: String(y), label: `${y} 年` }))

  const columns: ColumnsType<PMBatchListItem> = [
    {
      title: '保養單號', dataIndex: ['batch', 'journal_no'],
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, fontWeight: 600 }}
          onClick={() => navigate(`/mall/periodic-maintenance/${row.batch.ragic_id}`)}>
          {v}
        </Button>
      ),
    },
    {
      title: '保養月份', dataIndex: ['batch', 'period_month'], width: 100,
      sorter: (a, b) => a.batch.period_month.localeCompare(b.batch.period_month),
    },
    {
      title: '批次狀態', width: 100,
      render: (_, row) => {
        const s = derivePMBatchStatus(row.kpi)
        const cfg = BATCH_STATUS_CFG[s]
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '完成率', width: 190,
      render: (_, row) => {
        const { completion_rate, completed, total } = row.kpi
        return (
          <div>
            <Progress percent={completion_rate} size="small"
              strokeColor={{ from: '#4BA8E8', to: '#52C41A' }}
              format={() => `${completion_rate}%`} />
            <Text type="secondary" style={{ fontSize: 11 }}>{completed} / {total} 已完成</Text>
          </div>
        )
      },
    },
    {
      title: '逾期', dataIndex: ['kpi', 'overdue'], width: 70,
      render: (v) => v > 0 ? <Badge count={v} color="#C0392B" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '異常', dataIndex: ['kpi', 'abnormal'], width: 70,
      render: (v) => v > 0 ? <Badge count={v} color="#722ED1" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '最後更新', dataIndex: ['batch', 'ragic_updated_at'], width: 140,
      render: (v) => v || '—',
    },
    {
      title: '操作', width: 100,
      render: (_, row) => (
        <Button type="primary" size="small" icon={<RightOutlined />}
          style={{ background: '#1B3A5C' }}
          onClick={() => navigate(`/mall/periodic-maintenance/${row.batch.ragic_id}`)}>
          查看明細
        </Button>
      ),
    },
  ]

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <Select value={year} onChange={onYearChange} options={yearOptions} style={{ width: 110 }} />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={onReload} loading={loading}>重新整理</Button>
        </Col>
        <Col flex="auto" />
        <Col>
          <Button icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={onSync}>
            同步 Ragic
          </Button>
        </Col>
      </Row>
      <Table<PMBatchListItem>
        dataSource={batches}
        rowKey={(r) => r.batch.ragic_id}
        columns={columns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無保養批次資料' }}
      />
    </div>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function MallDashboardPage() {
  const navigate = useNavigate()

  // ── 統計總覽 state ─────────────────────────────────────────────────────────
  const [summary, setSummary]               = useState<DashboardSummary | null>(null)
  const [issues, setIssues]                 = useState<IssueItem[]>([])
  const [trend, setTrend]                   = useState<TrendPoint[]>([])
  const [trendDays, setTrendDays]           = useState<7 | 30>(7)
  const [issueTab, setIssueTab]             = useState('all')
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [loadingIssues, setLoadingIssues]   = useState(false)
  const [loadingTrend, setLoadingTrend]     = useState(false)
  const [targetDate, setTargetDate]         = useState<string>(dayjs().format('YYYY/MM/DD'))

  // ── 週期保養 state ─────────────────────────────────────────────────────────
  const [pmBatches, setPmBatches] = useState<PMBatchListItem[]>([])
  const [pmLoading, setPmLoading] = useState(false)
  const [pmSyncing, setPmSyncing] = useState(false)
  const [pmYear, setPmYear]       = useState(dayjs().format('YYYY'))

  // ── B4F state ──────────────────────────────────────────────────────────────
  const [b4fBatches, setB4fBatches] = useState<InspectionBatchListItem[]>([])
  const [b4fLoading, setB4fLoading] = useState(false)
  const [b4fSyncing, setB4fSyncing] = useState(false)
  const [b4fYM, setB4fYM]           = useState(dayjs().format('YYYY/MM'))

  // ── RF state ───────────────────────────────────────────────────────────────
  const [rfBatches, setRfBatches] = useState<RFInspectionBatchListItem[]>([])
  const [rfLoading, setRfLoading] = useState(false)
  const [rfSyncing, setRfSyncing] = useState(false)
  const [rfYM, setRfYM]           = useState(dayjs().format('YYYY/MM'))

  // ── B2F state ──────────────────────────────────────────────────────────────
  const [b2fBatches, setB2fBatches] = useState<B2FInspectionBatchListItem[]>([])
  const [b2fLoading, setB2fLoading] = useState(false)
  const [b2fSyncing, setB2fSyncing] = useState(false)
  const [b2fYM, setB2fYM]           = useState(dayjs().format('YYYY/MM'))

  // ── B1F state ──────────────────────────────────────────────────────────────
  const [b1fBatches, setB1fBatches] = useState<B1FInspectionBatchListItem[]>([])
  const [b1fLoading, setB1fLoading] = useState(false)
  const [b1fSyncing, setB1fSyncing] = useState(false)
  const [b1fYM, setB1fYM]           = useState(dayjs().format('YYYY/MM'))

  // ── 目前分頁（支援 ?tab=xxx 從明細頁返回時自動切換）─────────────────────────
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState(() => {
    const t = searchParams.get('tab')
    return (t && ['pm', 'b4f', 'rf', 'b2f', 'b1f'].includes(t)) ? t : 'dashboard'
  })

  // ── 統計總覽載入 ───────────────────────────────────────────────────────────
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
    loadSummary(); loadIssues(); loadTrend()
  }, [loadSummary, loadIssues, loadTrend])

  useEffect(() => { loadAll() }, [])  // eslint-disable-line

  // ── 子 Tab 懶載入 ──────────────────────────────────────────────────────────
  const loadPM = useCallback(async (y?: string) => {
    setPmLoading(true)
    try { setPmBatches(await fetchMallPMBatches(y ?? pmYear)) }
    catch { message.error('載入週期保養批次失敗') }
    finally { setPmLoading(false) }
  }, [pmYear])

  const loadB4F = useCallback(async (ym?: string) => {
    setB4fLoading(true)
    try { setB4fBatches(await fetchB4FBatches({ year_month: ym ?? b4fYM })) }
    catch { message.error('載入 B4F 巡檢紀錄失敗') }
    finally { setB4fLoading(false) }
  }, [b4fYM])

  const loadRF = useCallback(async (ym?: string) => {
    setRfLoading(true)
    try { setRfBatches(await fetchRFBatches({ year_month: ym ?? rfYM })) }
    catch { message.error('載入 RF 巡檢紀錄失敗') }
    finally { setRfLoading(false) }
  }, [rfYM])

  const loadB2F = useCallback(async (ym?: string) => {
    setB2fLoading(true)
    try { setB2fBatches(await fetchB2FBatches({ year_month: ym ?? b2fYM })) }
    catch { message.error('載入 B2F 巡檢紀錄失敗') }
    finally { setB2fLoading(false) }
  }, [b2fYM])

  const loadB1F = useCallback(async (ym?: string) => {
    setB1fLoading(true)
    try { setB1fBatches(await fetchB1FBatches({ year_month: ym ?? b1fYM })) }
    catch { message.error('載入 B1F 巡檢紀錄失敗') }
    finally { setB1fLoading(false) }
  }, [b1fYM])

  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'pm'  && pmBatches.length  === 0) loadPM()
    if (key === 'b4f' && b4fBatches.length === 0) loadB4F()
    if (key === 'rf'  && rfBatches.length  === 0) loadRF()
    if (key === 'b2f' && b2fBatches.length === 0) loadB2F()
    if (key === 'b1f' && b1fBatches.length === 0) loadB1F()
  }

  // query param 帶入的 tab 初次掛載時觸發懶載入
  useEffect(() => {
    const t = searchParams.get('tab')
    if (!t || t === 'dashboard') return
    if (t === 'pm')  loadPM()
    if (t === 'b4f') loadB4F()
    if (t === 'rf')  loadRF()
    if (t === 'b2f') loadB2F()
    if (t === 'b1f') loadB1F()
  }, [])  // eslint-disable-line

  // ── Sync handlers ──────────────────────────────────────────────────────────
  const syncPM = async () => {
    setPmSyncing(true)
    try { await syncMallPMFromRagic(); message.success('週期保養同步完成'); loadPM() }
    catch { message.error('同步失敗') } finally { setPmSyncing(false) }
  }
  const syncB4F = async () => {
    setB4fSyncing(true)
    try { await syncB4FFromRagic(); message.success('B4F 同步完成'); loadB4F() }
    catch { message.error('同步失敗') } finally { setB4fSyncing(false) }
  }
  const syncRF = async () => {
    setRfSyncing(true)
    try { await syncRFFromRagic(); message.success('RF 同步完成'); loadRF() }
    catch { message.error('同步失敗') } finally { setRfSyncing(false) }
  }
  const syncB2F = async () => {
    setB2fSyncing(true)
    try { await syncB2FFromRagic(); message.success('B2F 同步完成'); loadB2F() }
    catch { message.error('同步失敗') } finally { setB2fSyncing(false) }
  }
  const syncB1F = async () => {
    setB1fSyncing(true)
    try { await syncB1FFromRagic(); message.success('B1F 同步完成'); loadB1F() }
    catch { message.error('同步失敗') } finally { setB1fSyncing(false) }
  }

  // ── 統計總覽衍生 ───────────────────────────────────────────────────────────
  const ins    = summary?.inspection
  const pm     = summary?.pm
  const floors = ins?.by_floor ?? []

  const trendChartData = trend.map(t => ({
    date:   t.date.slice(5),
    B1F:    t.b1f_completion,
    B2F:    t.b2f_completion,
    RF:     t.rf_completion,
    異常數: t.total_abnormal,
  }))

  const handleKpiClick = (tab: string) => {
    setIssueTab(tab)
    loadIssues(tab)
    document.getElementById('issues-section')?.scrollIntoView({ behavior: 'smooth' })
  }

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
    { title: '區域', dataIndex: 'floor', width: 70, render: (v) => <Tag color="geekblue">{v}</Tag> },
    { title: '項目名稱', dataIndex: 'item_name', ellipsis: true },
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
        const fp = row.floor === 'B1F' ? 'b1f' : row.floor === 'B2F' ? 'b2f' : row.floor === 'RF' ? 'rf' : null
        if (!fp) return null
        return (
          <Button type="link" size="small" icon={<RightOutlined />}
            onClick={() => navigate(`/mall/${fp}-inspection/${row.batch_id}`)}>
            明細
          </Button>
        )
      },
    },
  ]

  const filteredIssues = issueTab === 'all' ? issues : issues.filter(i => i.status === issueTab)
  const issueCounts = issues.reduce((acc, i) => {
    acc[i.status] = (acc[i.status] ?? 0) + 1; return acc
  }, {} as Record<string, number>)

  // ── 統計總覽 Tab 內容 ──────────────────────────────────────────────────────

  // ── 統計總覽 Tab 內容 ──────────────────────────────────────────────────────
  const DashboardTabContent = (
    <div>
      {/* 日期選擇列 */}
      <Row align="middle" justify="end" style={{ marginBottom: 16 }}>
        <Space>
          <DatePicker
            value={dayjs(targetDate, 'YYYY/MM/DD')} format="YYYY/MM/DD" allowClear={false}
            onChange={(d) => { if (d) { const ds = d.format('YYYY/MM/DD'); setTargetDate(ds); loadSummary(ds) } }}
          />
          <Button onClick={() => { const today = dayjs().format('YYYY/MM/DD'); setTargetDate(today); loadSummary(today) }}>
            今日
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadAll} loading={loadingSummary}>重新整理</Button>
        </Space>
      </Row>

      {summary?.generated_at && (
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 16 }}>
          資料截至 {summary.generated_at}
        </Text>
      )}

      {/* KPI 卡片 2 x 4 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={6}>
          <KpiCard title="今日應完成巡檢" value={ins?.total_items ?? 0} suffix="項"
            color="#1B3A5C" icon={<SafetyOutlined />}
            sub={`${ins?.total_batches ?? 0} 場次 · ${targetDate}`}
            desc={MALL_KPI_DESC['今日巡檢應巡件數']} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="今日已完成巡檢" value={ins?.checked_items ?? 0} suffix="項"
            color="#52C41A" icon={<CheckCircleOutlined />}
            sub={ins && ins.total_items > 0 ? `完成率 ${ins.completion_rate}%` : '尚無巡檢資料'}
            onClick={() => handleKpiClick('all')} desc={MALL_KPI_DESC['今日已完成巡檢']} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="今日未完成巡檢" value={ins?.unchecked_items ?? 0} suffix="項"
            color={ins?.unchecked_items ? '#FAAD14' : '#52C41A'} icon={<ClockCircleOutlined />}
            onClick={() => handleKpiClick('unchecked')} desc={MALL_KPI_DESC['今日未完成巡檢']} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="今日異常件數" value={ins?.abnormal_items ?? 0} suffix="件"
            color={ins?.abnormal_items ? '#FF4D4F' : '#52C41A'} icon={<WarningOutlined />}
            sub="含待處理" onClick={() => handleKpiClick('abnormal')} desc={MALL_KPI_DESC['今日異常件數']} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="本月保養應執行" value={pm?.total_items ?? 0} suffix="項"
            color="#1B3A5C" icon={<BarChartOutlined />} sub={pm?.period_month ?? ''}
            desc={MALL_KPI_DESC['本月保養應執行']} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="本月保養已完成" value={pm?.completed_items ?? 0} suffix="項"
            color="#52C41A" icon={<CheckCircleOutlined />}
            sub={pm ? `完成率 ${pm.completion_rate}%` : ''} desc={MALL_KPI_DESC['本月保養已完成']} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="逾期未保養" value={pm?.overdue_items ?? 0} suffix="項"
            color={pm?.overdue_items ? '#FF4D4F' : '#52C41A'} icon={<ExclamationCircleOutlined />}
            onClick={() => handleKpiClick('overdue')} desc={MALL_KPI_DESC['逾期未保養']} />
        </Col>
        <Col xs={12} sm={6}>
          <KpiCard title="異常待追蹤"
            value={(ins?.abnormal_items ?? 0) + (pm?.abnormal_items ?? 0)} suffix="件"
            color={((ins?.abnormal_items ?? 0) + (pm?.abnormal_items ?? 0)) > 0 ? '#FF4D4F' : '#52C41A'}
            icon={<AlertOutlined />} onClick={() => handleKpiClick('abnormal')}
            desc={MALL_KPI_DESC['異常待追蹤']} />
        </Col>
      </Row>

      {ins && ins.total_items > 0 && (
        <Card size="small" style={{ marginBottom: 16, background: '#fafcff' }}>
          <Row align="middle" gutter={16}>
            <Col flex="120px"><Text strong>整體巡檢完成率</Text></Col>
            <Col flex="auto">
              <Progress percent={ins.completion_rate}
                strokeColor={{ from: ins.completion_rate < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
                format={(p) => `${p}%（${ins.checked_items}/${ins.total_items}）`} />
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

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={15}>
          <Card title={<><BarChartOutlined /> 各樓層執行情況比較</>} size="small"
            loading={loadingSummary}
            extra={<Text type="secondary" style={{ fontSize: 12 }}>{targetDate}</Text>}>
            <FloorCompareChart floors={floors} />
            {floors.length > 0 && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Row gutter={[8, 8]}>
                  {floors.map(f => (
                    <Col key={f.floor} xs={8}>
                      <Card size="small"
                        style={{ borderLeft: `4px solid ${FLOOR_COLORS[f.floor] ?? '#999'}`, background: '#fafafa' }}>
                        <Text strong style={{ color: FLOOR_COLORS[f.floor] }}>{f.floor_label}</Text>
                        <div style={{ marginTop: 4 }}>
                          {f.has_data
                            ? <Progress percent={f.completion_rate} size="small" strokeColor={FLOOR_COLORS[f.floor]} format={() => `${f.completion_rate}%`} />
                            : <Text type="secondary" style={{ fontSize: 11 }}>尚無資料</Text>}
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
                      </Card>
                    </Col>
                  ))}
                </Row>
              </>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={9}>
          <Card title={<><SafetyOutlined /> 今日巡檢狀態分布</>} size="small"
            loading={loadingSummary} style={{ height: '100%' }}>
            <InspectionDonut floors={floors} />
            {pm && pm.total_items > 0 && (
              <>
                <Divider style={{ margin: '10px 0' }} />
                <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
                  <CalendarOutlined style={{ marginRight: 6 }} />本月保養狀態（{pm.period_month}）
                </Text>
                <Row gutter={[8, 6]}>
                  {[
                    { label: '已完成', value: pm.completed_items,  color: '#52C41A' },
                    { label: '未完成', value: pm.incomplete_items, color: '#FAAD14' },
                    { label: '逾期',   value: pm.overdue_items,    color: '#FF4D4F' },
                    { label: '異常',   value: pm.abnormal_items,   color: '#FF4D4F' },
                  ].map(s => (
                    <Col span={12} key={s.label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between',
                        padding: '3px 6px', borderRadius: 4, background: '#f9f9f9' }}>
                        <Text style={{ fontSize: 12 }}>{s.label}</Text>
                        <Text strong style={{ fontSize: 12, color: s.color }}>{s.value}</Text>
                      </div>
                    </Col>
                  ))}
                </Row>
                <Progress percent={pm.completion_rate} size="small" style={{ marginTop: 10 }}
                  strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
                  format={(p) => `完成率 ${p}%`} />
              </>
            )}
          </Card>
        </Col>
      </Row>

      <Card title={<><BarChartOutlined /> 近期巡檢趨勢分析</>} size="small"
        loading={loadingTrend} style={{ marginBottom: 20 }}
        extra={
          <Segmented value={trendDays}
            options={[{ label: '近 7 日', value: 7 }, { label: '近 30 日', value: 30 }]}
            onChange={(v) => { setTrendDays(v as 7 | 30); loadTrend(v as number) }} />
        }>
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

      <Card id="issues-section" title={<><ExclamationCircleOutlined /> 重點追蹤清單</>}
        size="small" loading={loadingIssues}
        extra={<Button size="small" icon={<ReloadOutlined />} onClick={() => loadIssues()}>重新載入</Button>}>
        <Tabs
          activeKey={issueTab}
          onChange={(k) => { setIssueTab(k); loadIssues(k) }}
          items={[
            { key: 'all', label: <span>全部 <Badge count={issues.length} color="#999" style={{ marginLeft: 4 }} /></span> },
            { key: 'abnormal', label: <span>異常 <Badge count={(issueCounts.abnormal ?? 0) + (issueCounts.pending ?? 0)} color="#FF4D4F" style={{ marginLeft: 4 }} /></span> },
            { key: 'unchecked', label: <span>未完成 <Badge count={issueCounts.unchecked ?? 0} color="#FAAD14" style={{ marginLeft: 4 }} /></span> },
            { key: 'overdue', label: <span>逾期保養 <Badge count={issueCounts.overdue ?? 0} color="#FF4D4F" style={{ marginLeft: 4 }} /></span> },
          ]}
        />
        {filteredIssues.length === 0 ? (
          <Alert
            message={issueTab === 'all' ? '目前無待追蹤項目' : '此分類無待追蹤項目'}
            type="success" showIcon style={{ marginTop: 16 }}
          />
        ) : (
          <Table<IssueItem>
            dataSource={filteredIssues} rowKey="id" columns={issueColumns} size="small"
            pagination={{ pageSize: 20, showTotal: n => `共 ${n} 筆` }}
            onRow={(rec) => ({ style: { background: STATUS_COLOR[rec.status] + '1A' } })}
            locale={{ emptyText: '暫無資料' }}
          />
        )}
      </Card>
    </div>
  )

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 4px 40px' }}>
      <Breadcrumb style={{ marginBottom: 12 }} items={[
        { title: <HomeOutlined /> },
        { title: NAV_GROUP.mall },
        { title: NAV_PAGE.mallDashboard },
      ]} />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Space align="baseline">
            <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
              <ToolOutlined style={{ marginRight: 8 }} />
              {NAV_PAGE.mallDashboard}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>Mall Periodic Maintenance</Text>
          </Space>
        </Col>
      </Row>

      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        type="card"
        items={[
          {
            key: 'dashboard',
            label: <><DashboardOutlined /> 統計總覽</>,
            children: DashboardTabContent,
          },
          {
            key: 'pm',
            label: <><CalendarOutlined /> 週期保養</>,
            children: (
              <PMListTab
                batches={pmBatches} loading={pmLoading} syncing={pmSyncing} year={pmYear}
                onYearChange={(y) => { setPmYear(y); loadPM(y) }}
                onReload={() => loadPM()} onSync={syncPM}
              />
            ),
          },
          {
            key: 'b4f',
            label: <><SafetyOutlined /> B4F 巡檢</>,
            children: (
              <InspectionListTab
                floor="b4f"
                batches={b4fBatches as unknown as GenericBatchItem[]}
                loading={b4fLoading} syncing={b4fSyncing} yearMonth={b4fYM}
                onYearMonthChange={(ym) => { setB4fYM(ym); loadB4F(ym) }}
                onReload={() => loadB4F()} onSync={syncB4F}
                detailPath={(id) => `/mall/b4f-inspection/${id}`}
              />
            ),
          },
          {
            key: 'rf',
            label: <><SafetyOutlined /> RF 巡檢</>,
            children: (
              <InspectionListTab
                floor="rf"
                batches={rfBatches as unknown as GenericBatchItem[]}
                loading={rfLoading} syncing={rfSyncing} yearMonth={rfYM}
                onYearMonthChange={(ym) => { setRfYM(ym); loadRF(ym) }}
                onReload={() => loadRF()} onSync={syncRF}
                detailPath={(id) => `/mall/rf-inspection/${id}`}
              />
            ),
          },
          {
            key: 'b2f',
            label: <><SafetyOutlined /> B2F 巡檢</>,
            children: (
              <InspectionListTab
                floor="b2f"
                batches={b2fBatches as unknown as GenericBatchItem[]}
                loading={b2fLoading} syncing={b2fSyncing} yearMonth={b2fYM}
                onYearMonthChange={(ym) => { setB2fYM(ym); loadB2F(ym) }}
                onReload={() => loadB2F()} onSync={syncB2F}
                detailPath={(id) => `/mall/b2f-inspection/${id}`}
              />
            ),
          },
          {
            key: 'b1f',
            label: <><SafetyOutlined /> B1F 巡檢</>,
            children: (
              <InspectionListTab
                floor="b1f"
                batches={b1fBatches as unknown as GenericBatchItem[]}
                loading={b1fLoading} syncing={b1fSyncing} yearMonth={b1fYM}
                onYearMonthChange={(ym) => { setB1fYM(ym); loadB1F(ym) }}
                onReload={() => loadB1F()} onSync={syncB1F}
                detailPath={(id) => `/mall/b1f-inspection/${id}`}
              />
            ),
          },
        ]}
      />
    </div>
  )
}
