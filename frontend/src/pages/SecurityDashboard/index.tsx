/**
 * 保全巡檢統計 Dashboard
 * 顯示所有 7 張 Sheet 的今日巡檢統計、異常清單、近 7 日趨勢
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, RightOutlined, CalendarOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchSecurityDashboardSummary,
  fetchSecurityDashboardIssues,
  fetchSecurityDashboardTrend,
  syncPatrolFromRagic,
} from '@/api/securityPatrol'
import type {
  SecurityDashboardSummary,
  SecurityIssueItem,
  SecurityTrendPoint,
  SheetStats,
} from '@/types/securityPatrol'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

// ── 狀態設定 ──────────────────────────────────────────────────────────────────
const STATUS_TAG: Record<string, string> = {
  abnormal:  'error',
  pending:   'warning',
  unchecked: 'default',
}

export default function SecurityDashboardPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab]   = useState('summary')
  const [targetDate, setTargetDate] = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [summary, setSummary]       = useState<SecurityDashboardSummary | null>(null)
  const [issues, setIssues]         = useState<SecurityIssueItem[]>([])
  const [trend, setTrend]           = useState<SecurityTrendPoint[]>([])
  const [loading, setLoading]       = useState(false)
  const [syncing, setSyncing]       = useState(false)

  const loadSummary = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchSecurityDashboardSummary(targetDate)
      setSummary(data)
    } catch {
      message.error('載入統計失敗')
    } finally {
      setLoading(false)
    }
  }, [targetDate])

  const loadIssues = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchSecurityDashboardIssues({ start_date: targetDate, end_date: targetDate })
      setIssues(res.items)
    } catch {
      message.error('載入異常清單失敗')
    } finally {
      setLoading(false)
    }
  }, [targetDate])

  const loadTrend = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchSecurityDashboardTrend(7)
      setTrend(res.trend)
    } catch {
      message.error('載入趨勢失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadSummary() }, [loadSummary])
  useEffect(() => {
    if (activeTab === 'issues') loadIssues()
    if (activeTab === 'trend')  loadTrend()
  }, [activeTab, loadIssues, loadTrend])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncPatrolFromRagic()
      message.success('全部 Sheet 同步完成')
      await loadSummary()
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // ── 摘要 Tab ───────────────────────────────────────────────────────────────
  const sheetCols: ColumnsType<SheetStats> = [
    {
      title: 'Sheet',
      dataIndex: 'sheet_name',
      ellipsis: true,
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, textAlign: 'left' }}
          onClick={() => navigate(`/security/patrol/${row.sheet_key}`)}>
          {v}
        </Button>
      ),
    },
    {
      title: '場次',
      dataIndex: 'total_batches',
      width: 60,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#1B3A5C" showZero /> : <Text type="secondary">—</Text>,
    },
    {
      title: '完成率',
      dataIndex: 'completion_rate',
      width: 130,
      render: (v, row) => row.has_data ? (
        <Progress
          percent={v} size="small"
          strokeColor={{ from: v < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
          format={(p) => `${p}%`}
        />
      ) : <Text type="secondary">無資料</Text>,
    },
    {
      title: '異常',
      dataIndex: 'abnormal_items',
      width: 60,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: 'pending_items',
      width: 65,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '未巡檢',
      dataIndex: 'unchecked_items',
      width: 65,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#999" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '操作',
      width: 80,
      render: (_, row) => (
        <Button type="primary" size="small" icon={<RightOutlined />}
          style={{ background: '#1B3A5C' }}
          onClick={() => navigate(`/security/patrol/${row.sheet_key}`)}>
          詳情
        </Button>
      ),
    },
  ]

  const SummaryTab = (
    <div>
      <Row style={{ marginBottom: 16 }} align="middle" gutter={8}>
        <Col>
          <Text strong>查詢日期：</Text>
        </Col>
        <Col>
          <DatePicker
            value={dayjs(targetDate, 'YYYY/MM/DD')}
            format="YYYY/MM/DD"
            allowClear={false}
            onChange={(d) => { if (d) setTargetDate(d.format('YYYY/MM/DD')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadSummary} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      {/* 全體 KPI */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          {
            title: '今日巡檢場次',
            value: summary?.total_batches_all ?? 0,
            color: '#1B3A5C',
            icon: <DashboardOutlined />,
          },
          {
            title: `已巡檢項目`,
            value: summary?.checked_items_all ?? 0,
            suffix: `/${summary?.total_items_all ?? 0}`,
            color: '#4BA8E8',
            icon: <CheckCircleOutlined />,
          },
          {
            title: '異常 + 待處理',
            value: summary?.abnormal_items_all ?? 0,
            color: '#FF4D4F',
            icon: <WarningOutlined />,
          },
          {
            title: '整體完成率',
            value: summary?.completion_rate_all ?? 0,
            suffix: '%',
            color: (summary?.completion_rate_all ?? 0) >= 80 ? '#52C41A' : '#FAAD14',
            icon: <ExclamationCircleOutlined />,
          },
        ].map(card => (
          <Col xs={12} sm={12} lg={6} key={card.title}>
            <Card size="small" hoverable>
              <Statistic
                title={card.title}
                value={card.value}
                suffix={card.suffix}
                prefix={<span style={{ color: card.color }}>{card.icon}</span>}
                valueStyle={{ color: card.color, fontSize: 26 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 各 Sheet 明細表 */}
      <Card title={<><CalendarOutlined /> 各巡檢 Sheet 今日統計</>} size="small">
        <Table<SheetStats>
          dataSource={summary?.sheets ?? []}
          rowKey="sheet_key"
          columns={sheetCols}
          loading={loading}
          size="small"
          pagination={false}
          locale={{ emptyText: '尚無資料' }}
        />
      </Card>

      {/* 注意：無資料時顯示提示 */}
      {!loading && (summary?.total_items_all ?? 0) === 0 && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          message={`${targetDate} 尚無任何保全巡檢記錄，請確認巡檢是否已執行並同步。`}
          showIcon
        />
      )}
    </div>
  )

  // ── 異常清單 Tab ───────────────────────────────────────────────────────────
  const issueColumns: ColumnsType<SecurityIssueItem> = [
    { title: '日期',   dataIndex: 'issue_date',  width: 110 },
    {
      title: 'Sheet',
      dataIndex: 'sheet_name',
      width: 200,
      ellipsis: true,
      render: (v, row) => (
        <Button type="link" style={{ padding: 0 }}
          onClick={() => navigate(`/security/patrol/${row.sheet_key}`)}>
          {v}
        </Button>
      ),
    },
    { title: '巡檢點', dataIndex: 'item_name',   ellipsis: true },
    {
      title: '狀態', dataIndex: 'status_label', width: 80,
      render: (v, row) => <Tag color={STATUS_TAG[row.status] ?? 'default'}>{v}</Tag>,
    },
    { title: '巡檢人員', dataIndex: 'inspector', width: 90 },
    { title: '原始值',   dataIndex: 'note',      width: 100, ellipsis: true },
    {
      title: '操作', width: 80,
      render: (_, row) => (
        <Button type="link" size="small" icon={<RightOutlined />}
          onClick={() => navigate(`/security/patrol/${row.sheet_key}/${row.batch_id}`)}>
          明細
        </Button>
      ),
    },
  ]

  const IssuesTab = (
    <div>
      <Row style={{ marginBottom: 16 }} align="middle" gutter={8}>
        <Col>
          <Text type="secondary">顯示 {issues.length} 筆異常記錄（{targetDate}）</Text>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadIssues} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>
      {issues.length === 0 && !loading ? (
        <Alert message="今日無異常記錄" type="success" showIcon />
      ) : (
        <Table<SecurityIssueItem>
          dataSource={issues}
          rowKey="id"
          columns={issueColumns}
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }}
        />
      )}
    </div>
  )

  // ── 趨勢 Tab ───────────────────────────────────────────────────────────────
  const trendChartData = trend.map(t => ({
    date:    t.date.slice(5),
    異常數量:  t.abnormal_count,
    場次數:   t.total_batches,
  }))

  const TrendTab = (
    <div>
      <Row style={{ marginBottom: 16 }} justify="end">
        <Button icon={<ReloadOutlined />} onClick={loadTrend} loading={loading}>
          重新整理
        </Button>
      </Row>
      <Card title="近 7 日異常趨勢" size="small">
        {trendChartData.some(t => t.場次數 > 0) ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={trendChartData} margin={{ left: 0, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <RcTooltip />
              <Legend />
              <Bar dataKey="場次數" fill="#4BA8E8" radius={[3, 3, 0, 0]} />
              <Bar dataKey="異常數量" fill="#FF4D4F" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#999' }}>
            暫無趨勢資料（請先確認資料已同步）
          </div>
        )}
      </Card>
    </div>
  )

  // ── 頁面渲染 ──────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 4px' }}>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.security },
          { title: NAV_PAGE.securityDashboard },
        ]}
      />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <DashboardOutlined /> {NAV_PAGE.securityDashboard}
          </Title>
        </Col>
        <Col>
          <Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {summary?.generated_at ? `更新：${summary.generated_at}` : ''}
            </Text>
            <Button
              icon={<SyncOutlined spin={syncing} />}
              loading={syncing}
              onClick={handleSync}
            >
              同步全部 Sheet
            </Button>
          </Space>
        </Col>
      </Row>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'summary', label: '今日統計', children: SummaryTab },
          { key: 'issues',  label: '異常清單', children: IssuesTab },
          { key: 'trend',   label: '趨勢分析', children: TrendTab },
        ]}
      />
    </div>
  )
}
