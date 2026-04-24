/**
 * 倉庫庫存頁面
 *
 * 功能：
 *  1. KPI 統計卡（SKU 數、總庫存量、零庫存數、倉庫數）
 *  2. 篩選列（倉庫代碼 / 商品編號 / 商品名稱）
 *  3. Ant Design Table（唯讀）
 *  4. 手動同步按鈕
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Table, Space, Button, Input, Row, Col, Card,
  Statistic, Typography, message, Breadcrumb, Tag, Tooltip,
} from 'antd'
import {
  ReloadOutlined, HomeOutlined, SyncOutlined,
  SearchOutlined, DatabaseOutlined, ShopOutlined,
  WarningOutlined, InboxOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'

import {
  fetchInventoryRecords,
  fetchInventoryStats,
  syncInventoryFromRagic,
} from '@/api/inventory'
import type { InventoryRecord, InventoryStats, InventoryFilters } from '@/types/inventory'

const { Title, Text } = Typography

// ── 數量顏色輔助 ──────────────────────────────────────────────────────────────
function QuantityTag({ qty }: { qty: number }) {
  if (qty <= 0)  return <Tag color="red">{qty}</Tag>
  if (qty <= 5)  return <Tag color="orange">{qty}</Tag>
  return <Tag color="green">{qty}</Tag>
}

// ── Table 欄位定義 ────────────────────────────────────────────────────────────
const columns: ColumnsType<InventoryRecord> = [
  {
    title: '庫存編號',
    dataIndex: 'inventory_no',
    key: 'inventory_no',
    width: 150,
    sorter: (a, b) => a.inventory_no.localeCompare(b.inventory_no),
    render: (val: string) => <Text strong>{val}</Text>,
  },
  {
    title: '倉庫代碼',
    dataIndex: 'warehouse_code',
    key: 'warehouse_code',
    width: 110,
  },
  {
    title: '倉庫名稱',
    dataIndex: 'warehouse_name',
    key: 'warehouse_name',
    width: 130,
  },
  {
    title: '商品編號',
    dataIndex: 'product_no',
    key: 'product_no',
    width: 110,
    render: (val: string) => <Text code>{val}</Text>,
  },
  {
    title: '商品名稱',
    dataIndex: 'product_name',
    key: 'product_name',
    ellipsis: true,
  },
  {
    title: '數量',
    dataIndex: 'quantity',
    key: 'quantity',
    width: 90,
    align: 'right',
    sorter: (a, b) => a.quantity - b.quantity,
    render: (val: number) => <QuantityTag qty={val} />,
  },
  {
    title: '種類',
    dataIndex: 'category',
    key: 'category',
    width: 100,
  },
  {
    title: '規格',
    dataIndex: 'spec',
    key: 'spec',
    ellipsis: true,
  },
]

// ── 主頁面 ────────────────────────────────────────────────────────────────────
export default function InventoryPage() {
  const [records,  setRecords]  = useState<InventoryRecord[]>([])
  const [stats,    setStats]    = useState<InventoryStats | null>(null)
  const [loading,  setLoading]  = useState(false)
  const [syncing,  setSyncing]  = useState(false)
  const [total,    setTotal]    = useState(0)
  const [filters,  setFilters]  = useState<InventoryFilters>({
    page: 1,
    per_page: 50,
  })

  // 篩選暫存（按下搜尋才套用）
  const [warehouseInput, setWarehouseInput] = useState('')
  const [productNoInput,  setProductNoInput]  = useState('')
  const [productNameInput, setProductNameInput] = useState('')

  // ── 載入資料 ────────────────────────────────────────────────────────────────
  const loadRecords = useCallback(async (f: InventoryFilters) => {
    setLoading(true)
    try {
      const res = await fetchInventoryRecords(f)
      setRecords(res.data)
      setTotal(res.meta?.total ?? res.data.length)
    } catch (err) {
      message.error('載入庫存資料失敗')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadStats = useCallback(async () => {
    try {
      const res = await fetchInventoryStats()
      setStats(res.data)
    } catch {
      // 統計失敗不影響主表格
    }
  }, [])

  useEffect(() => {
    loadRecords(filters)
    loadStats()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 手動同步 ────────────────────────────────────────────────────────────────
  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await syncInventoryFromRagic()
      if (res.errors?.length) {
        message.warning(`同步完成，但有 ${res.errors.length} 筆錯誤`)
      } else {
        message.success(`同步完成：共 ${res.fetched} 筆，更新 ${res.upserted} 筆`)
      }
      await loadRecords(filters)
      await loadStats()
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // ── 套用搜尋 ────────────────────────────────────────────────────────────────
  const handleSearch = () => {
    const newFilters: InventoryFilters = {
      ...filters,
      page: 1,
      warehouse_code: warehouseInput || undefined,
      product_no:     productNoInput  || undefined,
      product_name:   productNameInput || undefined,
    }
    setFilters(newFilters)
    loadRecords(newFilters)
  }

  const handleReset = () => {
    setWarehouseInput('')
    setProductNoInput('')
    setProductNameInput('')
    const newFilters: InventoryFilters = { page: 1, per_page: filters.per_page }
    setFilters(newFilters)
    loadRecords(newFilters)
  }

  // ── 分頁切換 ────────────────────────────────────────────────────────────────
  const handleTableChange = (pagination: TablePaginationConfig) => {
    const newFilters: InventoryFilters = {
      ...filters,
      page:     pagination.current  ?? 1,
      per_page: pagination.pageSize ?? 50,
    }
    setFilters(newFilters)
    loadRecords(newFilters)
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { href: '/dashboard', title: <><HomeOutlined /><span>首頁</span></> },
          { title: <><DatabaseOutlined /><span>倉庫管理</span></> },
          { title: '倉庫庫存' },
        ]}
      />

      {/* Page title + actions */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>倉庫庫存</Title>
        </Col>
        <Col>
          <Tooltip title="從 Ragic 重新同步庫存資料">
            <Button
              icon={<SyncOutlined spin={syncing} />}
              onClick={handleSync}
              loading={syncing}
            >
              同步資料
            </Button>
          </Tooltip>
        </Col>
      </Row>

      {/* KPI 統計卡 */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="SKU 總數"
              value={stats?.total_skus ?? '-'}
              prefix={<InboxOutlined />}
              valueStyle={{ color: '#1B3A5C' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="總庫存量"
              value={stats?.total_quantity ?? '-'}
              prefix={<ShopOutlined />}
              valueStyle={{ color: '#4BA8E8' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="零庫存 SKU"
              value={stats?.zero_stock_count ?? '-'}
              prefix={<WarningOutlined />}
              valueStyle={{ color: stats?.zero_stock_count ? '#cf1322' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title="倉庫數"
              value={stats?.warehouse_count ?? '-'}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1B3A5C' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 篩選列 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={12} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="倉庫代碼"
              value={warehouseInput}
              onChange={(e) => setWarehouseInput(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
            />
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="商品編號"
              value={productNoInput}
              onChange={(e) => setProductNoInput(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
            />
          </Col>
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="商品名稱"
              value={productNameInput}
              onChange={(e) => setProductNameInput(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
            />
          </Col>
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleSearch}
              >
                搜尋
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleReset}>
                重置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 資料表格 */}
      <Card size="small">
        <Table<InventoryRecord>
          rowKey="id"
          columns={columns}
          dataSource={records}
          loading={loading}
          size="small"
          scroll={{ x: 900 }}
          pagination={{
            current:  filters.page,
            pageSize: filters.per_page,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['20', '50', '100', '200'],
            showTotal: (t) => `共 ${t} 筆`,
          }}
          onChange={handleTableChange}
        />
      </Card>
    </div>
  )
}
