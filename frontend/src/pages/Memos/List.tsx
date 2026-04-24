/**
 * 公告牆清單頁
 * 路由：/memos/list
 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Badge, Button, Card, Col, Input, Pagination, Row, Select, Space, Table, Tag, Typography,
} from 'antd'
import {
  NotificationOutlined, PlusOutlined, SearchOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import { fetchMemos } from '@/api/memos'
import type { MemoListItem } from '@/types/memo'

const { Title, Text } = Typography

const VISIBILITY_COLOR: Record<string, string> = {
  org:        'blue',
  restricted: 'orange',
}
const VISIBILITY_LABEL: Record<string, string> = {
  org:        '全公司',
  restricted: '僅相關',
}

export default function MemoListPage() {
  const navigate = useNavigate()
  const [loading,  setLoading]  = useState(false)
  const [items,    setItems]    = useState<MemoListItem[]>([])
  const [total,    setTotal]    = useState(0)
  const [page,     setPage]     = useState(1)
  const [perPage]               = useState(20)

  // 篩選
  const [q,          setQ]          = useState('')
  const [visibility, setVisibility] = useState<'all' | 'org' | 'restricted'>('all')

  const load = useCallback(async (p = page) => {
    setLoading(true)
    try {
      const res = await fetchMemos({ q, visibility, page: p, per_page: perPage })
      setItems(res.items)
      setTotal(res.total)
      setPage(p)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [q, visibility, page, perPage])

  useEffect(() => { load(1) }, [])

  const columns: ColumnsType<MemoListItem> = [
    {
      title: '主旨',
      dataIndex: 'title',
      render: (v, r) => (
        <Space direction="vertical" size={2}>
          <a onClick={() => navigate(`/memos/${r.id}`)} style={{ fontWeight: 500 }}>
            {r.source === 'approval' && (
              <Badge color="green" style={{ marginRight: 6 }} />
            )}
            {v}
          </a>
          {r.preview && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {r.preview.slice(0, 80)}{r.preview.length > 80 ? '…' : ''}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '收文者',
      dataIndex: 'recipient',
      width: 120,
      render: (v) => v || '—',
    },
    {
      title: '文號',
      dataIndex: 'doc_no',
      width: 120,
      render: (v) => v || '—',
    },
    {
      title: '發文者',
      dataIndex: 'author',
      width: 120,
      render: (v) => v || '系統',
    },
    {
      title: '範圍',
      dataIndex: 'visibility',
      width: 90,
      render: (v) => <Tag color={VISIBILITY_COLOR[v]}>{VISIBILITY_LABEL[v] ?? v}</Tag>,
    },
    {
      title: '發文日期',
      dataIndex: 'created_at',
      width: 155,
      render: (v) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '—',
    },
    {
      title: '',
      width: 72,
      render: (_v, r) => (
        <Button size="small" type="primary" onClick={() => navigate(`/memos/${r.id}`)}>
          查看
        </Button>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Space>
          <NotificationOutlined style={{ fontSize: 20, color: '#2563eb' }} />
          <Title level={4} style={{ margin: 0 }}>公告牆</Title>
          <Tag color="blue">共 {total} 則</Tag>
        </Space>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/memos/new')}
        >
          新增公告
        </Button>
      </Row>

      {/* 篩選列 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={12} align="middle">
          <Col xs={24} md={12}>
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜尋主旨 / 內文 / 發文者"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onPressEnter={() => load(1)}
              allowClear
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              style={{ width: '100%' }}
              value={visibility}
              onChange={(v) => setVisibility(v)}
              options={[
                { value: 'all',        label: '全部公告' },
                { value: 'org',        label: '全公司可見' },
                { value: 'restricted', label: '僅相關人員' },
              ]}
            />
          </Col>
          <Col xs={24} md={6} style={{ textAlign: 'right' }}>
            <Button type="primary" icon={<SearchOutlined />} onClick={() => load(1)}>
              搜尋
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 清單 */}
      <Card>
        <Table<MemoListItem>
          rowKey="id"
          columns={columns}
          dataSource={items}
          loading={loading}
          pagination={false}
          size="small"
          locale={{ emptyText: '目前沒有可顯示的公告' }}
        />
        {total > perPage && (
          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <Pagination
              current={page}
              pageSize={perPage}
              total={total}
              showTotal={(t) => `共 ${t} 筆`}
              onChange={(p) => load(p)}
              size="small"
            />
          </div>
        )}
      </Card>
    </div>
  )
}
