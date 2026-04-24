/**
 * 週期保養表主頁
 *
 * Tab 1「主管儀表板」：KPI 四卡 + 類別 Bar 圖 + 狀態 Donut 圖 + 逾期/即將到期預警
 * Tab 2「批次清單」：保養批次列表，含進度條、狀態標籤、操作入口
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
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import { fetchPMStats, fetchPMBatches, syncPMFromRagic } from '@/api/periodicMaintenance'
import type { PMStats, PMBatchListItem, PMItem } from '@/types/periodicMaintenance'
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
  // 全部項目（含非本月）都完成 → 已完成
  if (kpi.completed === kpi.total) return 'completed'
  if (kpi.in_progress > 0 || kpi.completed > 0) return 'active'
  return 'draft'
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function PeriodicMaintenancePage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats] = useState<PMStats | null>(null)
  const [batches, setBatches] = useState<PMBatchListItem[]>([])
  const [year, setYear] = useState(dayjs().format('YYYY'))
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const s = await fetchPMStats()
      setStats(s)
    } catch {
      message.error('載入統計資料失敗')
    } finally {
      setLoading(false)
    }
  }, [])

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

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  useEffect(() => {
    if (activeTab === 'list') loadBatches()
  }, [activeTab, loadBatches])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncPMFromRagic()
      message.success('同步完成')
      await loadDashboard()
      if (activeTab === 'list') await loadBatches()
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // ── 年份選項 ────────────────────────────────────────────────────────────────
  const yearOptions = [2024, 2025, 2026, 2027].map(y => ({
    value: String(y),
    label: `${y} 年`,
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
      {/* KPI 卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {[
          {
            title: '本月有效項目',
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
          <Col xs={24} sm={12} lg={6} key={card.title}>
            <Card size="small" hoverable>
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
      </Row>

      {/* 完成率進度條 */}
      {kpi && kpi.current_month_total > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row align="middle" gutter={16}>
            <Col flex="100px">
              <Text strong>本月完成率</Text>
            </Col>
            <Col flex="auto">
              <Progress
                percent={kpi.completion_rate}
                strokeColor={{ from: '#4BA8E8', to: '#52C41A' }}
                format={(p) => `${p}%（${kpi.completed}/${kpi.total}）`}
              />
            </Col>
            <Col flex="120px">
              <Text type="secondary">預估工時：{Math.round(kpi.planned_minutes / 60 * 10) / 10} 小時</Text>
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
              <Alert message="本月無逾期項目" type="success" showIcon />
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
            title={<><ClockCircleOutlined style={{ color: '#FAAD14' }} /> 本週待執行（排定中）</>}
            size="small"
          >
            {(stats?.upcoming_items ?? []).length === 0 ? (
              <Alert message="本週無即將到期項目" type="info" showIcon />
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

  // ── 頁面渲染 ──────────────────────────────────────────────────────────────
  return (
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

      {/* 主要內容 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'dashboard', label: '主管儀表板', children: DashboardTab },
          { key: 'list',      label: '批次清單',   children: ListTab },
        ]}
      />
    </div>
  )
}
