/**
 * 使用監控頁面（僅 system_admin 可見）
 *
 * 包含：
 *   - 整體概覽 KPI 卡片（今日 DAU、總請求、平均回應、錯誤率）
 *   - 模組使用排行 Table
 *   - 用戶活躍度排行 Table
 *   - 各模組回應時間 Table（P95 標色）
 *   - DAU 趨勢折線圖（Recharts）
 *   - 每小時請求量折線圖
 *   - 各模組錯誤率 Table
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Card, Row, Col, Statistic, Table, Select, Tabs, Tag, Spin,
  Typography, Space, Badge,
} from 'antd'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Legend,
} from 'recharts'
import {
  EyeOutlined, ThunderboltOutlined, TeamOutlined,
  WarningOutlined, ReloadOutlined,
} from '@ant-design/icons'
import { usageStatsApi, ModuleStat, UserStat, ResponseTimeStat, ErrorStat } from '@/api/usageStats'

const { Title, Text } = Typography
const { Option } = Select

const DAY_OPTIONS = [1, 7, 14, 30]

// ── 回應時間顏色 ──────────────────────────────────────────────────────────────
function msColor(ms: number): string {
  if (ms < 200)  return '#22863a'   // 綠
  if (ms < 800)  return '#e67e22'   // 橘
  return '#e74c3c'                   // 紅
}

export default function UsageMonitor() {
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(true)

  // ── 資料狀態 ─────────────────────────────────────────────────────────────
  const [summary,       setSummary]       = useState<any>(null)
  const [modules,       setModules]       = useState<ModuleStat[]>([])
  const [users,         setUsers]         = useState<UserStat[]>([])
  const [responseTimes, setResponseTimes] = useState<ResponseTimeStat[]>([])
  const [dau,           setDau]           = useState<any[]>([])
  const [errors,        setErrors]        = useState<ErrorStat[]>([])
  const [timeline,      setTimeline]      = useState<any[]>([])

  const fetchAll = useCallback(async (d: number) => {
    setLoading(true)
    try {
      const [s, m, u, r, dauRes, e, t] = await Promise.all([
        usageStatsApi.getSummary(d),
        usageStatsApi.getModules(d),
        usageStatsApi.getUsers(d),
        usageStatsApi.getResponseTimes(d),
        usageStatsApi.getDau(d),
        usageStatsApi.getErrors(d),
        usageStatsApi.getTimeline(d),
      ])
      setSummary(s.data)
      setModules(m.data.modules)
      setUsers(u.data.users)
      setResponseTimes(r.data.modules)
      setDau(dauRes.data.data)
      setErrors(e.data.modules)
      setTimeline(t.data.data)
    } catch (err) {
      console.error('UsageMonitor fetch error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchAll(days) }, [days, fetchAll])

  // ── 模組排行 columns ──────────────────────────────────────────────────────
  const moduleColumns = [
    { title: '模組', dataIndex: 'module', key: 'module',
      render: (v: string) => <Text code>{v}</Text> },
    { title: '總請求', dataIndex: 'total', key: 'total', sorter: (a: ModuleStat, b: ModuleStat) => a.total - b.total,
      render: (v: number) => v.toLocaleString() },
    { title: '瀏覽（GET）', dataIndex: 'reads', key: 'reads',
      render: (v: number) => <Tag color="blue">{v.toLocaleString()}</Tag> },
    { title: '操作（寫入）', dataIndex: 'writes', key: 'writes',
      render: (v: number) => v > 0 ? <Tag color="orange">{v.toLocaleString()}</Tag> : <Text type="secondary">—</Text> },
  ]

  // ── 用戶排行 columns ──────────────────────────────────────────────────────
  const userColumns = [
    { title: '#', key: 'rank', render: (_: any, __: any, i: number) => i + 1, width: 50 },
    { title: 'Email', dataIndex: 'user_email', key: 'user_email' },
    { title: '請求數', dataIndex: 'total', key: 'total', sorter: (a: UserStat, b: UserStat) => a.total - b.total,
      render: (v: number) => v.toLocaleString() },
    { title: '最常用模組', dataIndex: 'top_module', key: 'top_module',
      render: (v: string) => <Text code>{v}</Text> },
    { title: '最後活動', dataIndex: 'last_seen', key: 'last_seen',
      render: (v: string | null) => v ? new Date(v).toLocaleString('zh-TW') : '—' },
  ]

  // ── 回應時間 columns ──────────────────────────────────────────────────────
  const rtColumns = [
    { title: '模組', dataIndex: 'module', key: 'module',
      render: (v: string) => <Text code>{v}</Text> },
    { title: '請求數', dataIndex: 'count', key: 'count' },
    { title: '平均（ms）', dataIndex: 'avg_ms', key: 'avg_ms',
      sorter: (a: ResponseTimeStat, b: ResponseTimeStat) => a.avg_ms - b.avg_ms,
      render: (v: number) => <span style={{ color: msColor(v), fontWeight: 600 }}>{v}</span> },
    { title: 'P95（ms）', dataIndex: 'p95_ms', key: 'p95_ms',
      sorter: (a: ResponseTimeStat, b: ResponseTimeStat) => a.p95_ms - b.p95_ms,
      render: (v: number) => <span style={{ color: msColor(v) }}>{v}</span> },
    { title: '最慢（ms）', dataIndex: 'max_ms', key: 'max_ms',
      render: (v: number) => <span style={{ color: msColor(v) }}>{v}</span> },
  ]

  // ── 錯誤率 columns ────────────────────────────────────────────────────────
  const errorColumns = [
    { title: '模組', dataIndex: 'module', key: 'module',
      render: (v: string) => <Text code>{v}</Text> },
    { title: '總請求', dataIndex: 'total', key: 'total' },
    { title: '4xx', dataIndex: 'err4xx', key: 'err4xx',
      render: (v: number) => v > 0 ? <Tag color="orange">{v}</Tag> : '—' },
    { title: '5xx', dataIndex: 'err5xx', key: 'err5xx',
      render: (v: number) => v > 0 ? <Tag color="red">{v}</Tag> : '—' },
    { title: '錯誤率', dataIndex: 'error_rate_pct', key: 'error_rate_pct',
      sorter: (a: ErrorStat, b: ErrorStat) => a.error_rate_pct - b.error_rate_pct,
      render: (v: number) => (
        <span style={{ color: v > 5 ? '#e74c3c' : v > 1 ? '#e67e22' : '#22863a', fontWeight: 600 }}>
          {v.toFixed(2)}%
        </span>
      ) },
  ]

  return (
    <div style={{ padding: '0 4px' }}>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>使用監控</Title>
        <Space>
          <Text type="secondary">統計區間：</Text>
          <Select value={days} onChange={(v) => setDays(v)} style={{ width: 100 }}>
            {DAY_OPTIONS.map(d => <Option key={d} value={d}>{d} 天</Option>)}
          </Select>
          <ReloadOutlined
            onClick={() => fetchAll(days)}
            style={{ cursor: 'pointer', color: '#4BA8E8', fontSize: 16 }}
          />
        </Space>
      </Row>

      <Spin spinning={loading}>
        {/* ── KPI 卡片 ──────────────────────────────────────────────────── */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="今日活躍用戶（DAU）"
                value={summary?.dau_today ?? '—'}
                prefix={<TeamOutlined style={{ color: '#4BA8E8' }} />}
                valueStyle={{ color: '#1B3A5C' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={`總請求數（${days}天）`}
                value={summary?.total_requests ?? '—'}
                prefix={<EyeOutlined style={{ color: '#4BA8E8' }} />}
                formatter={(v) => Number(v).toLocaleString()}
                valueStyle={{ color: '#1B3A5C' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="平均回應時間"
                value={summary?.avg_response_ms ?? '—'}
                suffix="ms"
                prefix={<ThunderboltOutlined style={{ color: summary?.avg_response_ms > 800 ? '#e74c3c' : '#22863a' }} />}
                valueStyle={{ color: summary?.avg_response_ms > 800 ? '#e74c3c' : '#1B3A5C' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="API 錯誤率"
                value={summary?.error_rate_pct ?? '—'}
                suffix="%"
                prefix={<WarningOutlined style={{ color: summary?.error_rate_pct > 5 ? '#e74c3c' : '#22863a' }} />}
                valueStyle={{ color: summary?.error_rate_pct > 5 ? '#e74c3c' : '#1B3A5C' }}
                precision={2}
              />
            </Card>
          </Col>
        </Row>

        {/* ── Tabs ──────────────────────────────────────────────────────── */}
        <Tabs
          defaultActiveKey="modules"
          items={[
            {
              key: 'modules',
              label: '模組使用排行',
              children: (
                <Card>
                  <Table
                    dataSource={modules}
                    columns={moduleColumns}
                    rowKey="module"
                    size="small"
                    pagination={{ pageSize: 15 }}
                  />
                </Card>
              ),
            },
            {
              key: 'users',
              label: '用戶活躍度',
              children: (
                <Card>
                  <Table
                    dataSource={users}
                    columns={userColumns}
                    rowKey="user_id"
                    size="small"
                    pagination={{ pageSize: 15 }}
                  />
                </Card>
              ),
            },
            {
              key: 'response',
              label: '回應時間',
              children: (
                <Card extra={
                  <Space>
                    <Badge color="green" text="< 200ms 正常" />
                    <Badge color="orange" text="< 800ms 注意" />
                    <Badge color="red" text="≥ 800ms 慢" />
                  </Space>
                }>
                  <Table
                    dataSource={responseTimes}
                    columns={rtColumns}
                    rowKey="module"
                    size="small"
                    pagination={{ pageSize: 15 }}
                  />
                </Card>
              ),
            },
            {
              key: 'dau',
              label: 'DAU 趨勢',
              children: (
                <Card title={`每日活躍用戶數（過去 ${days} 天）`}>
                  <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={dau} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip />
                      <Line type="monotone" dataKey="dau" stroke="#4BA8E8" strokeWidth={2} dot={{ r: 3 }} name="DAU" />
                    </LineChart>
                  </ResponsiveContainer>
                </Card>
              ),
            },
            {
              key: 'timeline',
              label: '請求量時間軸',
              children: (
                <Card title={`每小時請求量（過去 ${days} 天）`}>
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={timeline} margin={{ top: 8, right: 24, left: 0, bottom: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="hour" tick={{ fontSize: 10 }}
                        tickFormatter={(v: string) => v?.slice(5, 13) ?? v} />
                      <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                      <Tooltip labelFormatter={(v: string) => `時間：${v}`} />
                      <Bar dataKey="requests" fill="#1B3A5C" name="請求數" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              ),
            },
            {
              key: 'errors',
              label: '錯誤率',
              children: (
                <Card>
                  <Table
                    dataSource={errors}
                    columns={errorColumns}
                    rowKey="module"
                    size="small"
                    pagination={{ pageSize: 15 }}
                  />
                </Card>
              ),
            },
          ]}
        />
      </Spin>
    </div>
  )
}
