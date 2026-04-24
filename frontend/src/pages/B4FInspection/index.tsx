/**
 * 整棟工務每日巡檢 - B4F 主頁
 *
 * Tab 1「主管儀表板」：KPI 卡 + 異常趨勢折線 + 狀態 Donut + 預警清單
 * Tab 2「巡檢紀錄」：場次清單 + 日期篩選 + 進度條
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Progress, Alert,
  message, Badge, DatePicker,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, RightOutlined, BarChartOutlined,
  SafetyOutlined, CalendarOutlined,
} from '@ant-design/icons'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import { fetchB4FStats, fetchB4FBatches, syncB4FFromRagic } from '@/api/b4fInspection'
import type {
  InspectionStats, InspectionBatchListItem, InspectionItem,
} from '@/types/b4fInspection'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

// ── 狀態設定 ──────────────────────────────────────────────────────────────────
const STATUS_CFG: Record<string, { label: string; color: string; tagColor: string }> = {
  normal:    { label: '正常',   color: '#52C41A', tagColor: 'success' },
  abnormal:  { label: '異常',   color: '#FF4D4F', tagColor: 'error' },
  pending:   { label: '待處理', color: '#FAAD14', tagColor: 'warning' },
  unchecked: { label: '未填寫', color: '#999999', tagColor: 'default' },
}

function deriveBatchStatus(kpi: InspectionBatchListItem['kpi']): { label: string; color: string } {
  if (!kpi || kpi.total === 0) return { label: '草稿', color: '#999' }
  if (kpi.abnormal > 0)        return { label: '有異常', color: '#FF4D4F' }
  if (kpi.pending > 0)         return { label: '待處理', color: '#FAAD14' }
  if (kpi.unchecked === 0)     return { label: '已完成', color: '#52C41A' }
  if (kpi.completion_rate > 0) return { label: '巡檢中', color: '#4BA8E8' }
  return { label: '未開始', color: '#999' }
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function B4FInspectionPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('dashboard')
  const [stats, setStats]     = useState<InspectionStats | null>(null)
  const [batches, setBatches] = useState<InspectionBatchListItem[]>([])
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const s = await fetchB4FStats()
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
      const data = await fetchB4FBatches({ year_month: yearMonth })
      setBatches(data)
    } catch {
      message.error('載入巡檢紀錄失敗')
    } finally {
      setLoading(false)
    }
  }, [yearMonth])

  useEffect(() => { loadDashboard() }, [loadDashboard])
  useEffect(() => { if (activeTab === 'list') loadBatches() }, [activeTab, loadBatches])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncB4FFromRagic()
      message.success('同步完成')
      await loadDashboard()
      if (activeTab === 'list') await loadBatches()
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // ── Dashboard ──────────────────────────────────────────────────────────────
  const kpi        = stats?.latest_kpi
  const trendData  = (stats?.abnormal_trend ?? []).map(t => ({
    date:    t.date.slice(5),
    異常數量: t.abnormal_count,
  }))
  const pieData = (stats?.status_distribution ?? []).filter(s => s.count > 0)

  const DashboardTab = (
    <div>
      {/* KPI Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {[
          {
            title: '已巡檢（本次）',
            value: kpi ? kpi.total - kpi.unchecked : 0,
            suffix: `/${kpi?.total ?? 0} 項`,
            icon: <SafetyOutlined />,
            color: '#1B3A5C',
          },
          {
            title: `正常（${kpi?.normal_rate ?? 0}%）`,
            value: kpi?.normal ?? 0,
            suffix: '項',
            icon: <CheckCircleOutlined />,
            color: '#52C41A',
          },
          {
            title: '異常',
            value: kpi?.abnormal ?? 0,
            suffix: '項',
            icon: <WarningOutlined />,
            color: '#FF4D4F',
          },
          {
            title: '待處理',
            value: kpi?.pending ?? 0,
            suffix: '項',
            icon: <ExclamationCircleOutlined />,
            color: '#FAAD14',
          },
        ].map(card => (
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
      {kpi && kpi.total > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row align="middle" gutter={16}>
            <Col flex="100px"><Text strong>巡檢完成率</Text></Col>
            <Col flex="auto">
              <Progress
                percent={kpi.completion_rate}
                strokeColor={{ from: kpi.completion_rate < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
                format={(p) => `${p}%（${kpi.total - kpi.unchecked}/${kpi.total}）`}
              />
            </Col>
            <Col flex="100px">
              <Text type="secondary">近7日：{stats?.total_batches_7d ?? 0} 次</Text>
            </Col>
          </Row>
        </Card>
      )}

      {/* 圖表區 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {/* 近7日異常趨勢 */}
        <Col xs={24} lg={14}>
          <Card title={<><BarChartOutlined /> 近 7 日異常趨勢</>} size="small" style={{ height: 300 }}>
            {trendData.some(t => t.異常數量 > 0) ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendData} margin={{ left: 0, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} />
                  <RcTooltip />
                  <Legend />
                  <Line type="monotone" dataKey="異常數量" stroke="#FF4D4F" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', paddingTop: 80, color: '#999' }}>暫無異常記錄</div>
            )}
          </Card>
        </Col>

        {/* 狀態分布 Donut */}
        <Col xs={24} lg={10}>
          <Card title="本次巡檢狀態分布" size="small" style={{ height: 300 }}>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData} dataKey="count" nameKey="label"
                    cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                    label={({ label, count }) => `${label}:${count}`} labelLine={false}
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

      {/* 預警清單 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title={<><WarningOutlined style={{ color: '#FF4D4F' }} /> 本次異常項目</>} size="small">
            {(stats?.recent_abnormal ?? []).length === 0 ? (
              <Alert message="本次巡檢無異常" type="success" showIcon />
            ) : (
              <Table<InspectionItem>
                dataSource={stats?.recent_abnormal ?? []}
                rowKey="ragic_id"
                size="small"
                pagination={false}
                columns={[
                  { title: '設備項目', dataIndex: 'item_name', ellipsis: true },
                  {
                    title: '狀態', dataIndex: 'result_status', width: 72,
                    render: (v) => {
                      const cfg = STATUS_CFG[v] ?? { label: v, tagColor: 'default' }
                      return <Tag color={cfg.tagColor}>{cfg.label}</Tag>
                    },
                  },
                  {
                    title: '', width: 44,
                    render: (_, row) => (
                      <Button type="link" size="small" icon={<RightOutlined />}
                        onClick={() => navigate(`/mall/b4f-inspection/${row.batch_ragic_id}`)} />
                    ),
                  },
                ]}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title={<><ClockCircleOutlined style={{ color: '#FAAD14' }} /> 待處理項目</>} size="small">
            {(stats?.recent_pending ?? []).length === 0 ? (
              <Alert message="目前無待處理項目" type="info" showIcon />
            ) : (
              <Table<InspectionItem>
                dataSource={stats?.recent_pending ?? []}
                rowKey="ragic_id"
                size="small"
                pagination={false}
                columns={[
                  { title: '設備項目', dataIndex: 'item_name', ellipsis: true },
                  { title: '原始值', dataIndex: 'result_raw', width: 80, ellipsis: true },
                  {
                    title: '', width: 44,
                    render: (_, row) => (
                      <Button type="link" size="small" icon={<RightOutlined />}
                        onClick={() => navigate(`/mall/b4f-inspection/${row.batch_ragic_id}`)} />
                    ),
                  },
                ]}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 最新場次快速入口 */}
      {stats?.latest_batch && (
        <Card size="small" style={{ marginTop: 16 }}>
          <Row align="middle" justify="space-between">
            <Col>
              <Space>
                <CalendarOutlined style={{ color: '#1B3A5C' }} />
                <Text strong>{stats.latest_batch.inspection_date}</Text>
                {stats.latest_batch.start_time && (
                  <Text type="secondary">{stats.latest_batch.start_time}</Text>
                )}
                {stats.latest_batch.inspector_name && (
                  <Text type="secondary">巡檢人員：{stats.latest_batch.inspector_name}</Text>
                )}
                {stats.latest_batch.work_hours && (
                  <Tag color="blue">{stats.latest_batch.work_hours}</Tag>
                )}
              </Space>
            </Col>
            <Col>
              <Button
                type="primary" icon={<RightOutlined />}
                onClick={() => navigate(`/mall/b4f-inspection/${stats.latest_batch!.ragic_id}`)}
                style={{ background: '#1B3A5C' }}
              >
                查看最新明細
              </Button>
            </Col>
          </Row>
        </Card>
      )}
    </div>
  )

  // ── 巡檢紀錄 Tab ──────────────────────────────────────────────────────────
  const batchColumns: ColumnsType<InspectionBatchListItem> = [
    {
      title: '巡檢日期',
      dataIndex: ['batch', 'inspection_date'],
      width: 110,
      sorter: (a, b) => a.batch.inspection_date.localeCompare(b.batch.inspection_date),
      defaultSortOrder: 'descend',
    },
    {
      title: '開始時間',
      dataIndex: ['batch', 'start_time'],
      width: 150,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title: '結束時間',
      dataIndex: ['batch', 'end_time'],
      width: 150,
      render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v || '—'}</Text>,
    },
    {
      title: '工時',
      dataIndex: ['batch', 'work_hours'],
      width: 90,
      render: (v) => v ? <Tag color="geekblue">{v}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: '巡檢人員',
      dataIndex: ['batch', 'inspector_name'],
      width: 100,
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, fontWeight: 600 }}
          onClick={() => navigate(`/mall/b4f-inspection/${row.batch.ragic_id}`)}>
          {v || row.batch.ragic_id}
        </Button>
      ),
    },
    {
      title: '狀態',
      width: 90,
      render: (_, row) => {
        const s = deriveBatchStatus(row.kpi)
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '巡檢進度',
      width: 200,
      render: (_, row) => {
        const { completion_rate, total, unchecked } = row.kpi
        const checked = total - unchecked
        return (
          <div>
            <Progress
              percent={completion_rate} size="small"
              strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
              format={() => `${completion_rate}%`}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              {checked} / {total} 已巡檢
            </Text>
          </div>
        )
      },
    },
    {
      title: '異常',
      dataIndex: ['kpi', 'abnormal'],
      width: 65,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: ['kpi', 'pending'],
      width: 65,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '操作',
      width: 90,
      render: (_, row) => (
        <Button
          type="primary" size="small" icon={<RightOutlined />}
          style={{ background: '#1B3A5C' }}
          onClick={() => navigate(`/mall/b4f-inspection/${row.batch.ragic_id}`)}
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
          <DatePicker
            picker="month"
            value={dayjs(yearMonth, 'YYYY/MM')}
            format="YYYY/MM"
            allowClear={false}
            onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadBatches} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>
      <Table<InspectionBatchListItem>
        dataSource={batches}
        rowKey={(r) => r.batch.ragic_id}
        columns={batchColumns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢紀錄' }}
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
          { title: NAV_PAGE.b4fInspection },
        ]}
      />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <SafetyOutlined /> {NAV_PAGE.b4fInspection}
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
          { key: 'dashboard', label: '主管儀表板', children: DashboardTab },
          { key: 'list',      label: '巡檢紀錄',   children: ListTab },
        ]}
      />
    </div>
  )
}
