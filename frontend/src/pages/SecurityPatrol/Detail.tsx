/**
 * 保全巡檢 批次明細頁（唯讀）
 * Route: /security/patrol/:sheetKey/:batchId
 */
import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Breadcrumb, Button, Card, Col, Row, Space,
  Table, Tag, Typography, message, Statistic, Divider,
} from 'antd'
import {
  ArrowLeftOutlined, ReloadOutlined, SearchOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  CalendarOutlined, ClockCircleOutlined, UserOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import { Input, Select } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { fetchPatrolBatchDetail } from '@/api/securityPatrol'
import type { PatrolBatchDetail, PatrolItem } from '@/types/securityPatrol'
import { NAV_GROUP } from '@/constants/navLabels'
import { SECURITY_SHEETS } from '@/constants/securitySheets'

const { Title, Text } = Typography

const STATUS_CFG: Record<string, { label: string; color: string; rowBg?: string; tagColor: string }> = {
  normal:    { label: '正常',   color: '#52C41A', tagColor: 'success' },
  abnormal:  { label: '異常',   color: '#FF4D4F', rowBg: '#fff1f0', tagColor: 'error' },
  pending:   { label: '待處理', color: '#FAAD14', rowBg: '#fff7e6', tagColor: 'warning' },
  unchecked: { label: '未巡檢', color: '#999999', rowBg: '#fafafa', tagColor: 'default' },
  note:      { label: '備註',   color: '#597EF7', rowBg: '#f0f5ff', tagColor: 'geekblue' },
}

const STATUS_TABS = [
  { key: 'all',       label: '全部' },
  { key: 'normal',    label: '正常' },
  { key: 'abnormal',  label: '異常' },
  { key: 'pending',   label: '待處理' },
  { key: 'unchecked', label: '未巡檢' },
  { key: 'note',      label: '備註說明' },
]

export default function SecurityPatrolDetailPage() {
  const { sheetKey = '', batchId = '' } = useParams<{ sheetKey: string; batchId: string }>()
  const navigate  = useNavigate()
  const sheetName = SECURITY_SHEETS[sheetKey]?.name ?? sheetKey

  const [detail, setDetail]   = useState<PatrolBatchDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchText, setSearchText]     = useState('')

  const loadDetail = useCallback(async () => {
    if (!sheetKey || !batchId) return
    setLoading(true)
    try {
      const data = await fetchPatrolBatchDetail(sheetKey, batchId)
      setDetail(data)
    } catch {
      message.error('載入明細失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetKey, batchId])

  useEffect(() => { loadDetail() }, [loadDetail])

  const batch = detail?.batch
  const kpi   = detail?.kpi

  // 篩選
  const filteredItems = (detail?.items ?? []).filter(it => {
    if (statusFilter !== 'all' && it.result_status !== statusFilter) return false
    if (searchText && !it.item_name.toLowerCase().includes(searchText.toLowerCase())) return false
    return true
  })

  const scoreItemCount = (detail?.items ?? []).filter(it => !it.is_note).length
  const noteItemCount  = (detail?.items ?? []).filter(it => it.is_note).length

  const columns: ColumnsType<PatrolItem> = [
    {
      title: '項次',
      dataIndex: 'seq_no',
      width: 60,
      align: 'center',
      render: (v) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '巡檢點',
      dataIndex: 'item_name',
      ellipsis: true,
      render: (v, row) => (
        row.is_note
          ? <Space size={4}><FileTextOutlined style={{ color: '#597EF7' }} /><Text style={{ color: '#597EF7' }}>{v}</Text></Space>
          : <Text style={{ color: row.abnormal_flag ? '#FF4D4F' : undefined }}>{v}</Text>
      ),
    },
    {
      title: '說明 / 原始值',
      dataIndex: 'result_raw',
      render: (v, row) =>
        row.is_note
          // 備註欄位：顯示文字內容（可能是空白=尚無說明，或有說明文字）
          ? (v
              ? <Text style={{ color: '#1D39C4' }}>{v}</Text>
              : <Text type="secondary" italic>（尚無說明）</Text>)
          : (v ? <Text code style={{ fontSize: 12 }}>{v}</Text> : <Text type="secondary">—</Text>),
    },
    {
      title: '狀態',
      dataIndex: 'result_status',
      width: 100,
      render: (v) => {
        const cfg = STATUS_CFG[v] ?? { label: v, tagColor: 'default' }
        return <Tag color={cfg.tagColor}>{cfg.label}</Tag>
      },
    },
  ]

  return (
    <div style={{ padding: '0 4px' }}>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: NAV_GROUP.security },
          { title: sheetName, onClick: () => navigate(`/security/patrol/${sheetKey}`), className: 'cursor-pointer' },
          { title: '巡檢明細' },
        ]}
      />

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/security/patrol/${sheetKey}`)}>
              返回清單
            </Button>
            <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
              巡檢明細
            </Title>
          </Space>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadDetail} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      {/* 場次資訊 */}
      {batch && (
        <Card size="small" style={{ marginBottom: 16, background: '#f8fafc' }}>
          <Row gutter={[24, 8]}>
            <Col xs={24} sm={6}>
              <Space>
                <CalendarOutlined style={{ color: '#1B3A5C' }} />
                <Text strong>{batch.inspection_date}</Text>
              </Space>
            </Col>
            <Col xs={24} sm={6}>
              <Space>
                <ClockCircleOutlined style={{ color: '#4BA8E8' }} />
                <Text type="secondary">{batch.start_time || '—'} → {batch.end_time || '—'}</Text>
              </Space>
            </Col>
            <Col xs={24} sm={6}>
              <Space>
                <UserOutlined />
                <Text>{batch.inspector_name || '—'}</Text>
              </Space>
            </Col>
            {batch.work_hours && (
              <Col xs={24} sm={6}>
                <Tag color="geekblue">{batch.work_hours}</Tag>
              </Col>
            )}
          </Row>
        </Card>
      )}

      {/* KPI */}
      {kpi && (
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          {[
            { title: '總巡檢點', value: kpi.total,     color: '#1B3A5C', icon: null },
            { title: '正常',     value: kpi.normal,    color: '#52C41A', icon: <CheckCircleOutlined /> },
            { title: '異常',     value: kpi.abnormal,  color: '#FF4D4F', icon: <WarningOutlined /> },
            { title: '待處理',   value: kpi.pending,   color: '#FAAD14', icon: <ExclamationCircleOutlined /> },
            { title: '未填寫',   value: kpi.unchecked, color: '#999',    icon: null },
          ].map(card => (
            <Col xs={12} sm={8} md={4} key={card.title}>
              <Card size="small" hoverable>
                <Statistic
                  title={card.title}
                  value={card.value}
                  prefix={card.icon ? <span style={{ color: card.color }}>{card.icon}</span> : undefined}
                  valueStyle={{ color: card.color, fontSize: 22 }}
                />
              </Card>
            </Col>
          ))}
          <Col xs={12} sm={8} md={4}>
            <Card size="small">
              <Statistic
                title="完成率"
                value={kpi.completion_rate}
                suffix="%"
                valueStyle={{ color: kpi.completion_rate >= 80 ? '#52C41A' : '#FAAD14', fontSize: 22 }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Divider style={{ margin: '12px 0' }} />

      {/* 篩選列 */}
      <Row gutter={[8, 8]} style={{ marginBottom: 12 }}>
        <Col>
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 100 }}
            options={STATUS_TABS.map(t => ({ value: t.key, label: t.label }))}
          />
        </Col>
        <Col flex="auto">
          <Input
            placeholder="搜尋巡檢點名稱"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ maxWidth: 300 }}
          />
        </Col>
        <Col>
          <Space size={4}>
            <Text type="secondary">顯示 {filteredItems.length} 筆</Text>
            {noteItemCount > 0 && (
              <Tag icon={<FileTextOutlined />} color="geekblue" style={{ margin: 0 }}>
                含備註說明 {noteItemCount} 項
              </Tag>
            )}
            <Text type="secondary">（評分項 {scoreItemCount}）</Text>
          </Space>
        </Col>
      </Row>

      {/* 巡檢點清單 */}
      <Table<PatrolItem>
        dataSource={filteredItems}
        rowKey="ragic_id"
        columns={columns}
        loading={loading}
        size="small"
        pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢資料' }}
        rowClassName={(row) => {
          const bg = STATUS_CFG[row.result_status]?.rowBg
          return bg ? '' : ''
        }}
        onRow={(row) => ({
          style: {
            background: STATUS_CFG[row.result_status]?.rowBg ?? undefined,
          },
        })}
      />
    </div>
  )
}
