/**
 * 簽核清單頁
 * 路由：/approvals/list
 */
import { useState, useCallback, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button, Card, DatePicker, Input, Radio, Select, Space, Table, Tag, Tooltip, Typography, Row, Col,
} from 'antd'
import { PlusOutlined, SearchOutlined, ClearOutlined, UserOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import { searchApprovals } from '@/api/approvals'
import type { ApprovalSearchItem } from '@/types/approval'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const STATUS_COLOR: Record<string, string> = {
  pending:  'blue',
  approved: 'green',
  rejected: 'red',
}
const STATUS_LABEL: Record<string, string> = {
  pending:  '待處理',
  approved: '已核准',
  rejected: '已退回',
}

export default function ApprovalListPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ApprovalSearchItem[]>([])

  // 篩選條件
  const [q, setQ] = useState('')
  const [scope, setScope] = useState<'all' | 'mine' | 'todo'>('todo')
  const [statusFilter, setStatusFilter] = useState('all')
  const [dateRange, setDateRange] = useState<[string, string]>(['', ''])
  const [limit, setLimit] = useState(50)

  const doSearch = useCallback(async () => {
    setLoading(true)
    try {
      const res = await searchApprovals({
        q,
        scope,
        status: statusFilter,
        date_from: dateRange[0],
        date_to:   dateRange[1],
        limit,
      })
      setData(res)
    } catch {
      setData([])
    } finally {
      setLoading(false)
    }
  }, [q, scope, statusFilter, dateRange, limit])

  useEffect(() => { doSearch() }, [])   // 頁面載入後先查一次

  const reset = () => {
    setQ('')
    setScope('todo')
    setStatusFilter('all')
    setDateRange(['', ''])
    setLimit(50)
  }

  const columns: ColumnsType<ApprovalSearchItem> = [
    { title: '#', width: 48, render: (_v, _r, i) => i + 1 },
    {
      title: '主旨',
      dataIndex: 'subject',
      render: (v, r) => (
        <a onClick={() => navigate(`/approvals/${r.id}`)}>{v || '（無主旨）'}</a>
      ),
    },
    { title: '申請人', dataIndex: 'requester', width: 120 },
    {
      title: '狀態',
      dataIndex: 'status',
      width: 90,
      render: (v) => <Tag color={STATUS_COLOR[v]}>{STATUS_LABEL[v] ?? v}</Tag>,
    },
    {
      title: '目前關卡 / 簽核人',
      width: 180,
      render: (_v, r) => {
        if (r.status !== 'pending' || r.current_step < 0) {
          return <Text type="secondary">—</Text>
        }
        return (
          <Space size={4}>
            <Tag color="processing" style={{ marginRight: 0 }}>
              第 {r.current_step + 1} 關
            </Tag>
            {r.current_approver_name && (
              <Tooltip title="目前待簽核人員">
                <Space size={2} style={{ color: '#374151', fontSize: 13 }}>
                  <UserOutlined style={{ fontSize: 11, color: '#6b7280' }} />
                  {r.current_approver_name}
                </Space>
              </Tooltip>
            )}
          </Space>
        )
      },
    },
    {
      title: '送出時間',
      dataIndex: 'submitted_at',
      width: 180,
      render: (v) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '—',
    },
    {
      title: '',
      width: 80,
      render: (_v, r) => (
        <Button size="small" type="primary" onClick={() => navigate(`/approvals/${r.id}`)}>
          檢視
        </Button>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>📋 簽核清單</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/approvals/new')}
        >
          新增簽核單
        </Button>
      </Row>

      {/* 篩選區 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]}>
          <Col xs={24} md={8}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="主旨 / 說明 / 申請人"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onPressEnter={doSearch}
              allowClear
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              style={{ width: '100%' }}
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: 'all',      label: '全部狀態' },
                { value: 'pending',  label: '待處理' },
                { value: 'approved', label: '已核准' },
                { value: 'rejected', label: '已退回' },
              ]}
            />
          </Col>
          <Col xs={24} md={8}>
            <RangePicker
              style={{ width: '100%' }}
              onChange={(_, strs) => setDateRange(strs as [string, string])}
            />
          </Col>
          <Col xs={24} md={4}>
            <Select
              style={{ width: '100%' }}
              value={limit}
              onChange={setLimit}
              options={[
                { value: 20,  label: '20 筆' },
                { value: 50,  label: '50 筆' },
                { value: 100, label: '100 筆' },
                { value: 200, label: '200 筆' },
              ]}
            />
          </Col>

          {/* 範圍 Radio */}
          <Col xs={24}>
            <Space wrap>
              <span style={{ color: '#6b7280', fontSize: 13 }}>範圍：</span>
              <Radio.Group
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                buttonStyle="solid"
              >
                <Radio.Button value="todo">我的待簽（含我在鏈中）</Radio.Button>
                <Radio.Button value="mine">我送出的</Radio.Button>
                <Radio.Button value="all">全部（我相關）</Radio.Button>
              </Radio.Group>
            </Space>
          </Col>

          <Col xs={24} style={{ textAlign: 'right' }}>
            <Space>
              <Button icon={<ClearOutlined />} onClick={reset}>清除</Button>
              <Button type="primary" icon={<SearchOutlined />} onClick={doSearch}>查詢</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 結果表格 */}
      <Card title={`📑 查詢結果（共 ${data.length} 筆）`}>
        <Table<ApprovalSearchItem>
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={false}
          size="small"
          locale={{ emptyText: '無符合資料' }}
        />
      </Card>
    </div>
  )
}
