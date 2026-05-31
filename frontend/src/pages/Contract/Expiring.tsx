/**
 * 合約到期預警頁面
 *
 * 路徑：/contract/expiring
 * 顯示未來 N 天內到期的合約清單，依剩餘天數三色標示。
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Card, Table, Tag, Button, Space, Typography, Breadcrumb,
  Select, Row, Col, Statistic, Alert, Tooltip, message,
} from 'antd'
import {
  HomeOutlined, WarningOutlined, ReloadOutlined,
  ExclamationCircleOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'

import { fetchExpiringContracts } from '@/api/contract'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography
const { Option } = Select

// ── 工具函式 ──────────────────────────────────────────────────────────────────
const fmtDate = (d: string | null | undefined) =>
  d ? d.slice(0, 10) : '-'

const fmtMoney = (n: number | null | undefined) =>
  n == null ? '-' : `$${n.toLocaleString('zh-TW')}`

/** 依剩餘天數給顏色 */
const urgencyColor = (days: number): string => {
  if (days <= 30) return '#FF4D4F'   // 紅
  if (days <= 60) return '#FA8C16'   // 橙
  return '#FAAD14'                   // 黃
}

/** 依剩餘天數給 Tag color */
const urgencyTagColor = (days: number): string => {
  if (days <= 30) return 'error'
  if (days <= 60) return 'warning'
  return 'gold'
}

type ExpiringItem = {
  contract_id: string
  contract_name: string
  contract_type: string
  contract_status: string
  responsible_dept: string
  vendor_name: string
  end_date: string
  remaining_days: number
  total_amount_tax_included: number
  risk_level: string
  manager: string
}

// ═════════════════════════════════════════════════════════════════════════════
// 主元件
// ═════════════════════════════════════════════════════════════════════════════

export default function ExpiringContractsPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<ExpiringItem[]>([])
  const [loading, setLoading] = useState(false)
  const [days, setDays] = useState(90)

  const load = useCallback(async (d: number) => {
    setLoading(true)
    try {
      const resp = await fetchExpiringContracts(d)
      setItems(resp.items)
    } catch (err: any) {
      message.error(err?.message || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(days) }, [days])

  // 統計數字
  const critical30  = items.filter(i => i.remaining_days <= 30).length
  const critical60  = items.filter(i => i.remaining_days > 30 && i.remaining_days <= 60).length
  const warning90   = items.filter(i => i.remaining_days > 60).length

  const columns: ColumnsType<ExpiringItem> = [
    {
      title: '剩餘天數',
      dataIndex: 'remaining_days',
      key: 'remaining_days',
      width: 110,
      sorter: (a, b) => a.remaining_days - b.remaining_days,
      defaultSortOrder: 'ascend',
      render: (days: number) => (
        <Tag color={urgencyTagColor(days)} style={{ fontWeight: 700, fontSize: 13 }}>
          {days} 天
        </Tag>
      ),
    },
    {
      title: '到期日',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 110,
      render: (d: string, record) => (
        <span style={{ color: urgencyColor(record.remaining_days), fontWeight: record.remaining_days <= 30 ? 700 : 400 }}>
          {fmtDate(d)}
        </span>
      ),
    },
    {
      title: '合約名稱',
      dataIndex: 'contract_name',
      key: 'contract_name',
      ellipsis: true,
      render: (name: string, record) => (
        <Button
          type="link"
          style={{ padding: 0, height: 'auto', textAlign: 'left' }}
          onClick={() => navigate(`/contract?search=${record.contract_id}`)}
        >
          {name}
        </Button>
      ),
    },
    {
      title: '合約編號',
      dataIndex: 'contract_id',
      key: 'contract_id',
      width: 130,
      ellipsis: true,
    },
    {
      title: '廠商',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      width: 140,
      ellipsis: true,
    },
    {
      title: '部門',
      dataIndex: 'responsible_dept',
      key: 'responsible_dept',
      width: 120,
      ellipsis: true,
    },
    {
      title: '金額',
      dataIndex: 'total_amount_tax_included',
      key: 'total_amount_tax_included',
      width: 130,
      align: 'right' as const,
      render: (v: number) => <span style={{ color: '#722ED1' }}>{fmtMoney(v)}</span>,
    },
    {
      title: '風險',
      dataIndex: 'risk_level',
      key: 'risk_level',
      width: 80,
      render: (r: string) => {
        const colorMap: Record<string, string> = { '低': '#52C41A', '中': '#FAAD14', '高': '#FF7A45', '關鍵': '#FF4D4F' }
        return r ? <Tag color={colorMap[r] ?? 'default'}>{r}</Tag> : '-'
      },
    },
    {
      title: '管理人',
      dataIndex: 'manager',
      key: 'manager',
      width: 90,
      ellipsis: true,
      render: (m: string) => m || '-',
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 麵包屑 */}
      <Breadcrumb style={{ marginBottom: '16px' }}>
        <Breadcrumb.Item><HomeOutlined /> 首頁</Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_GROUP.contract}</Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_PAGE.contractExpiring}</Breadcrumb.Item>
      </Breadcrumb>

      <Title level={4} style={{ marginBottom: 16 }}>
        <WarningOutlined style={{ color: '#FA8C16', marginRight: 8 }} />
        {NAV_PAGE.contractExpiring}
      </Title>

      {/* 警告提示 */}
      {critical30 > 0 && (
        <Alert
          type="error"
          showIcon
          icon={<ExclamationCircleOutlined />}
          message={`有 ${critical30} 份合約將在 30 天內到期，請儘速處理！`}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small" style={{ borderLeft: '4px solid #FF4D4F' }}>
            <Statistic
              title="30 天內到期"
              value={critical30}
              suffix="份"
              valueStyle={{ color: '#FF4D4F', fontWeight: 700 }}
              prefix={<ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ borderLeft: '4px solid #FA8C16' }}>
            <Statistic
              title="31–60 天到期"
              value={critical60}
              suffix="份"
              valueStyle={{ color: '#FA8C16', fontWeight: 700 }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ borderLeft: '4px solid #FAAD14' }}>
            <Statistic
              title="61–90 天到期"
              value={warning90}
              suffix="份"
              valueStyle={{ color: '#FAAD14', fontWeight: 700 }}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 篩選列 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Text strong>預警範圍：</Text>
          </Col>
          <Col>
            <Select value={days} onChange={v => setDays(v)} style={{ width: 140 }}>
              <Option value={30}>30 天內</Option>
              <Option value={60}>60 天內</Option>
              <Option value={90}>90 天內（預設）</Option>
              <Option value={180}>180 天內</Option>
            </Select>
          </Col>
          <Col style={{ marginLeft: 'auto' }}>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => load(days)} loading={loading}>
                重新整理
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 表格 */}
      <Card>
        <Table<ExpiringItem>
          columns={columns}
          dataSource={items}
          loading={loading}
          rowKey="contract_id"
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 份即將到期合約`,
          }}
          rowClassName={(record) => {
            if (record.remaining_days <= 30) return 'ant-table-row-danger'
            if (record.remaining_days <= 60) return 'ant-table-row-warning'
            return ''
          }}
          locale={{ emptyText: `未來 ${days} 天內無到期合約` }}
          scroll={{ x: 1000 }}
        />
      </Card>

      <style>{`
        .ant-table-row-danger td { background: #fff2f0 !important; }
        .ant-table-row-warning td { background: #fff7e6 !important; }
      `}</style>
    </div>
  )
}
