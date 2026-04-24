/**
 * 客房保養完成統計 — 主頁面
 *
 * 功能：
 *  1. KPI 統計卡（完成率、總筆數、未完項目）
 *  2. 篩選列（房號 / 工作狀態 / 部門）
 *  3. Ant Design Table
 *  4. 新增 / 編輯 / 刪除 Modal
 *  5. 圖表 Modal（管理儀表板）
 *  6. 手動同步按鈕 + 後端自動排程同步
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Table, Tag, Space, Button, Input, Select, Row, Col, Card,
  Statistic, Typography, Popconfirm, Modal, Form, DatePicker,
  Checkbox, message, Tooltip, Badge, Breadcrumb, Progress, Divider,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
  CheckCircleOutlined, ClockCircleOutlined, HomeOutlined, ToolOutlined,
  BarChartOutlined, SyncOutlined, WarningOutlined, SearchOutlined,
} from '@ant-design/icons'
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RTooltip, Legend, ResponsiveContainer, RadialBarChart,
  RadialBar, LabelList,
} from 'recharts'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchRecords, fetchStats, fetchOptions,
  createRecord, updateRecord, deleteRecord, syncFromRagic,
} from '@/api/roomMaintenance'
import type {
  RoomMaintenanceRecord, RoomMaintenanceStats,
  RoomMaintenanceFilters, RoomMaintenanceCreate, RoomMaintenanceUpdate,
} from '@/types/roomMaintenance'

const { Title, Text } = Typography
const { Option } = Select

// ── 完整檢查項目清單（fallback，若 API 尚未載入）──────────────────────────────
const ALL_INSPECT_ITEMS_DEFAULT = [
  '客房房門', '客房窗', '浴間', '配電盤',
  '客房設備', '客房燈/電源', '浴廁', '空調',
  '傢俱', '地板', '牆面', '天花板',
]

// ── 未檢查項目附表元件 ────────────────────────────────────────────────────────
interface MissingRow {
  key: string
  room_no: string
  dept: string
  work_item: string
  missing_items: string[]
  missing_count: number
  checked_count: number
}

function MissingInspectTable({
  records,
  allItems,
}: {
  records: RoomMaintenanceRecord[]
  allItems: string[]
}) {
  const [searchRoom, setSearchRoom] = useState('')

  const fullList = allItems.length > 0 ? allItems : ALL_INSPECT_ITEMS_DEFAULT

  // 計算每個房間「未檢查」的項目 = 全部項目 - 已檢查項目
  const missingData: MissingRow[] = records
    .map((r) => {
      const checked = new Set(r.inspect_items)
      const missing = fullList.filter((item) => !checked.has(item))
      return {
        key: r.id,
        room_no: r.room_no,
        dept: r.dept,
        work_item: r.work_item,
        missing_items: missing,
        missing_count: missing.length,
        checked_count: r.inspect_items.length,
      }
    })
    .filter((r) => r.missing_count > 0)
    .filter((r) =>
      searchRoom ? r.room_no.includes(searchRoom.trim()) : true,
    )
    .sort((a, b) => b.missing_count - a.missing_count)

  const MISSING_COLOURS = [
    'red', 'volcano', 'orange', 'gold',
    'magenta', 'purple', 'geekblue', 'cyan',
  ]
  const missingColour = (item: string) =>
    MISSING_COLOURS[item.charCodeAt(0) % MISSING_COLOURS.length]

  const columns: ColumnsType<MissingRow> = [
    {
      title: '房號',
      dataIndex: 'room_no',
      key: 'room_no',
      width: 80,
      sorter: (a, b) => {
        const na = parseInt(a.room_no) || 0
        const nb = parseInt(b.room_no) || 0
        return na - nb
      },
      render: (val) => (
        <Text strong style={{ fontSize: 15, color: '#c0392b' }}>{val}</Text>
      ),
    },
    {
      title: '缺漏檢查項目',
      dataIndex: 'missing_items',
      key: 'missing_items',
      render: (items: string[]) => (
        <Space size={[4, 6]} wrap>
          {items.map((item) => (
            <Tag
              key={item}
              color={missingColour(item)}
              style={{ margin: 0, fontWeight: 500 }}
              icon={<WarningOutlined />}
            >
              {item}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '負責人',
      dataIndex: 'dept',
      key: 'dept',
      width: 100,
      render: (val) => <Text style={{ color: '#e67e22' }}>{val || '—'}</Text>,
    },
    {
      title: '工作狀態',
      dataIndex: 'work_item',
      key: 'work_item',
      width: 150,
      render: (val: string) => {
        const cfg = WORK_ITEM_TAG[val]
        return cfg
          ? <Badge status={cfg.color as any} text={val} />
          : <Text type="secondary">{val || '—'}</Text>
      },
    },
    {
      title: '已檢查',
      dataIndex: 'checked_count',
      key: 'checked_count',
      width: 80,
      align: 'center',
      sorter: (a, b) => a.checked_count - b.checked_count,
      render: (val) => <Tag color="blue">{val} 項</Tag>,
    },
    {
      title: '缺漏數量',
      dataIndex: 'missing_count',
      key: 'missing_count',
      width: 90,
      align: 'center',
      defaultSortOrder: 'descend',
      sorter: (a, b) => a.missing_count - b.missing_count,
      render: (val) => (
        <Tag
          color="error"
          style={{ fontWeight: 700, fontSize: 13, padding: '2px 10px' }}
        >
          {val} 項
        </Tag>
      ),
    },
  ]

  return (
    <div style={{ marginTop: 24 }}>
      {/* 標題列 */}
      <div
        style={{
          background: 'linear-gradient(135deg, #c0392b 0%, #e74c3c 50%, #e67e22 100%)',
          borderRadius: '8px 8px 0 0',
          padding: '10px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Space>
          <WarningOutlined style={{ color: '#fff', fontSize: 18 }} />
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 15 }}>
            未檢查項目明細
          </span>
          <Tag
            style={{
              background: 'rgba(255,255,255,0.25)',
              border: 'none',
              color: '#fff',
              fontWeight: 700,
            }}
          >
            {missingData.reduce((s, r) => s + r.missing_count, 0)} 項缺漏
          </Tag>
        </Space>
        <Input
          size="small"
          placeholder="搜尋房號"
          prefix={<SearchOutlined style={{ color: 'rgba(255,255,255,0.7)' }} />}
          allowClear
          style={{
            width: 160,
            background: 'rgba(255,255,255,0.15)',
            border: '1px solid rgba(255,255,255,0.4)',
            color: '#fff',
            borderRadius: 6,
          }}
          value={searchRoom}
          onChange={(e) => setSearchRoom(e.target.value)}
        />
      </div>

      {/* 附表（橙紅色底）*/}
      <div
        style={{
          background: '#fff5f5',
          border: '1px solid #ffccc7',
          borderTop: 'none',
          borderRadius: '0 0 8px 8px',
        }}
      >
        <Table
          rowKey="key"
          columns={columns}
          dataSource={missingData}
          size="middle"
          scroll={{ x: 900 }}
          pagination={{
            pageSize: 10,
            showTotal: (t) => `共 ${t} 間客房有缺漏`,
            showSizeChanger: false,
          }}
          rowClassName={() => 'missing-inspect-row'}
          locale={{
            emptyText: (
              <div style={{ padding: 32, color: '#52c41a' }}>
                <CheckCircleOutlined style={{ fontSize: 32, marginBottom: 8 }} />
                <div style={{ fontWeight: 600 }}>所有客房檢查項目均完整！</div>
              </div>
            ),
          }}
          style={{ background: 'transparent' }}
        />
      </div>

      {/* 說明文字 */}
      <div style={{ marginTop: 6, color: '#aaa', fontSize: 12 }}>
        <WarningOutlined /> 缺漏項目 = 全部 {fullList.length} 個標準檢查項目中，該房號尚未記錄的項目
      </div>

      {/* 讓 row 有底色的 inline style */}
      <style>{`
        .missing-inspect-row td {
          background: #fff5f5 !important;
        }
        .missing-inspect-row:hover td {
          background: #ffe8e8 !important;
        }
      `}</style>
    </div>
  )
}

// ── Work item colour map ───────────────────────────────────────────────────────
const WORK_ITEM_TAG: Record<string, { color: string; hex: string }> = {
  '已完成檢視及保養': { color: 'success',    hex: '#52c41a' },
  '非本月排程':       { color: 'default',    hex: '#8c8c8c' },
  '進行中':           { color: 'processing', hex: '#1677ff' },
  '待排程':           { color: 'warning',    hex: '#faad14' },
}

const INSPECT_COLOURS = [
  'blue','geekblue','purple','cyan','green',
  'orange','gold','red','magenta','volcano',
]
const itemColour = (item: string) =>
  INSPECT_COLOURS[item.charCodeAt(0) % INSPECT_COLOURS.length]

// ── Chart colour palette ───────────────────────────────────────────────────────
const PIE_COLORS = ['#52c41a', '#1677ff', '#faad14', '#8c8c8c', '#ff4d4f']

// ─────────────────────────────────────────────────────────────────────────────
export default function RoomMaintenancePage() {
  const [records, setRecords]   = useState<RoomMaintenanceRecord[]>([])
  const [stats, setStats]       = useState<RoomMaintenanceStats | null>(null)
  const [options, setOptions]   = useState<{ inspect: string[]; workItems: string[] }>({
    inspect: [], workItems: [],
  })
  const [loading, setLoading]   = useState(false)
  const [syncing, setSyncing]   = useState(false)
  const [total, setTotal]       = useState(0)
  const [filters, setFilters]   = useState<RoomMaintenanceFilters>({ page: 1, per_page: 20 })

  // Modal state
  const [modalOpen, setModalOpen]         = useState(false)
  const [chartOpen, setChartOpen]         = useState(false)
  const [editingRecord, setEditingRecord] = useState<RoomMaintenanceRecord | null>(null)
  const [form] = Form.useForm()

  // ── Load data ──────────────────────────────────────────────────────────────
  const loadRecords = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchRecords(filters)
      setRecords(res.data)
      setTotal(res.meta.total)
    } catch {
      message.error('載入資料失敗')
    } finally {
      setLoading(false)
    }
  }, [filters])

  const loadStats = useCallback(async () => {
    try {
      const res = await fetchStats()
      setStats(res.data)
    } catch { /* non-critical */ }
  }, [])

  const loadOptions = useCallback(async () => {
    try {
      const res = await fetchOptions()
      setOptions({ inspect: res.inspect_item_options, workItems: res.work_item_options })
    } catch { /* fallback */ }
  }, [])

  useEffect(() => { loadRecords() }, [loadRecords])
  useEffect(() => { loadStats(); loadOptions() }, [loadStats, loadOptions])

  // ── Sync handler ───────────────────────────────────────────────────────────
  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await syncFromRagic()
      message.success(`同步完成：從 Ragic 取得 ${res.fetched} 筆，更新 ${res.upserted} 筆`)
      loadRecords()
      loadStats()
    } catch {
      message.error('同步失敗，請確認 Ragic API 設定')
    } finally {
      setSyncing(false)
    }
  }

  // ── Table change ───────────────────────────────────────────────────────────
  const handleTableChange = (pagination: TablePaginationConfig) => {
    setFilters((prev) => ({
      ...prev,
      page:     pagination.current  ?? 1,
      per_page: pagination.pageSize ?? 20,
    }))
  }

  // ── CRUD handlers ──────────────────────────────────────────────────────────
  const openCreate = () => { setEditingRecord(null); form.resetFields(); setModalOpen(true) }
  const openEdit   = (record: RoomMaintenanceRecord) => {
    setEditingRecord(record)
    form.setFieldsValue({
      room_no:          record.room_no,
      inspect_items:    record.inspect_items,
      dept:             record.dept,
      work_item:        record.work_item,
      inspect_datetime: record.inspect_datetime ? dayjs(record.inspect_datetime, 'YYYY/MM/DD HH:mm') : null,
      close_date:       record.close_date ? dayjs(record.close_date, 'YYYY/MM/DD') : null,
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteRecord(id)
      message.success('刪除成功')
      loadRecords(); loadStats()
    } catch { message.error('刪除失敗') }
  }

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        ...values,
        inspect_datetime: values.inspect_datetime
          ? (values.inspect_datetime as dayjs.Dayjs).format('YYYY/MM/DD HH:mm') : '',
        close_date: values.close_date
          ? (values.close_date as dayjs.Dayjs).format('YYYY/MM/DD') : undefined,
      }
      if (editingRecord) {
        await updateRecord(editingRecord.id, payload as RoomMaintenanceUpdate)
        message.success('更新成功')
      } else {
        await createRecord(payload as RoomMaintenanceCreate)
        message.success('新增成功')
      }
      setModalOpen(false); loadRecords(); loadStats()
    } catch { /* inline validation */ }
  }

  // ── Chart data derivation ──────────────────────────────────────────────────
  // All records (not paged) for charts — use full dataset from last fetch
  const allRecords = records  // already full page; charts reflect current filter

  // 1. Work status pie
  const statusPieData = Object.entries(
    allRecords.reduce<Record<string, number>>((acc, r) => {
      const key = r.work_item || '未設定'
      acc[key] = (acc[key] || 0) + 1
      return acc
    }, {})
  ).map(([name, value]) => ({ name, value }))

  // 2. Incomplete items per room (bar)
  const incompleteBarData = [...allRecords]
    .sort((a, b) => b.incomplete - a.incomplete)
    .slice(0, 10)
    .map((r) => ({ room: `${r.room_no}室`, incomplete: r.incomplete, subtotal: r.subtotal }))

  // 3. Inspect item frequency (horizontal bar)
  const itemFreqMap: Record<string, number> = {}
  allRecords.forEach((r) => {
    r.inspect_items.forEach((item) => {
      itemFreqMap[item] = (itemFreqMap[item] || 0) + 1
    })
  })
  const itemFreqData = Object.entries(itemFreqMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([item, count]) => ({ item, count }))

  // 4. Radial completion gauge
  const completionRate = stats?.completion_rate ?? 0
  const radialData = [
    { name: '完成', value: completionRate, fill: '#52c41a' },
    { name: '未完成', value: 100 - completionRate, fill: '#f0f0f0' },
  ]

  // ── Table columns ──────────────────────────────────────────────────────────
  const columns: ColumnsType<RoomMaintenanceRecord> = [
    {
      title: '房號', dataIndex: 'room_no', key: 'room_no', width: 80,
      sorter: (a, b) => a.room_no.localeCompare(b.room_no),
      render: (val) => <Text strong>{val}</Text>,
    },
    {
      title: '檢查項目', dataIndex: 'inspect_items', key: 'inspect_items', width: 280,
      render: (items: string[]) => (
        <Space size={[4, 4]} wrap>
          {items.map((item) => <Tag key={item} color={itemColour(item)} style={{ margin: 0 }}>{item}</Tag>)}
        </Space>
      ),
    },
    {
      title: '報修部門', dataIndex: 'dept', key: 'dept', width: 100,
      render: (val) => <Text style={{ color: '#1677ff' }}>{val}</Text>,
    },
    {
      title: '工作項目選擇', dataIndex: 'work_item', key: 'work_item', width: 160,
      render: (val: string) => {
        const cfg = WORK_ITEM_TAG[val]
        return cfg
          ? <Badge status={cfg.color as any} text={val} />
          : <Text type="secondary">{val || '—'}</Text>
      },
    },
    {
      title: '檢查日期時間', dataIndex: 'inspect_datetime', key: 'inspect_datetime', width: 150,
      sorter: (a, b) => a.inspect_datetime.localeCompare(b.inspect_datetime),
    },
    {
      title: '建立日期', dataIndex: 'created_at', key: 'created_at', width: 170,
      render: (val) => <Text type="secondary" style={{ fontSize: 12 }}>{val}</Text>,
    },
    {
      title: '最後更新日期', dataIndex: 'updated_at', key: 'updated_at', width: 170,
      render: (val) => <Text type="secondary" style={{ fontSize: 12 }}>{val}</Text>,
    },
    {
      title: '結案日期', dataIndex: 'close_date', key: 'close_date', width: 110,
      render: (val) => val ? <Tag color="green">{val}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: '小計', dataIndex: 'subtotal', key: 'subtotal', width: 70, align: 'center',
      sorter: (a, b) => a.subtotal - b.subtotal,
      render: (val) => <Tag color="blue">{val}</Tag>,
    },
    {
      title: '未完', dataIndex: 'incomplete', key: 'incomplete', width: 70, align: 'center',
      sorter: (a, b) => a.incomplete - b.incomplete,
      render: (val) => val > 0 ? <Tag color="red">{val}</Tag> : <Tag color="default">0</Tag>,
    },
    {
      title: '操作', key: 'actions', width: 90, fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="編輯">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          </Tooltip>
          <Popconfirm title="確定刪除此記錄？" onConfirm={() => handleDelete(record.id)}
            okText="刪除" cancelText="取消" okButtonProps={{ danger: true }}>
            <Tooltip title="刪除">
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb style={{ marginBottom: 16 }} items={[
        { title: <><HomeOutlined /> 首頁</> },
        { title: '飯店管理' },
        { title: <><ToolOutlined /> 客房保養</> },
      ]} />

      <Title level={4} style={{ marginBottom: 16, marginTop: 0 }}>客房保養完成統計</Title>

      {/* KPI Cards */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="本月完成率" value={stats?.completion_rate ?? 0} suffix="%"
              valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="總記錄數" value={stats?.total ?? 0} suffix="筆" />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="已完成保養" value={stats?.completed ?? 0} suffix="筆"
              valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card size="small">
            <Statistic title="未完成項目" value={stats?.total_incomplete ?? 0} suffix="項"
              valueStyle={{ color: stats?.total_incomplete ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
      </Row>

      {/* Toolbar */}
      <Card size="small" bodyStyle={{ padding: '12px 16px' }} style={{ marginBottom: 16 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col xs={24} sm={5}>
            <Input placeholder="搜尋房號" allowClear
              onChange={(e) => setFilters((p) => ({ ...p, room_no: e.target.value || undefined, page: 1 }))} />
          </Col>
          <Col xs={24} sm={7}>
            <Select placeholder="工作狀態" allowClear style={{ width: '100%' }}
              onChange={(val) => setFilters((p) => ({ ...p, work_item: val || undefined, page: 1 }))}>
              {options.workItems.map((item) => <Option key={item} value={item}>{item}</Option>)}
            </Select>
          </Col>
          <Col xs={24} sm={5}>
            <Input placeholder="報修部門 / 負責人" allowClear
              onChange={(e) => setFilters((p) => ({ ...p, dept: e.target.value || undefined, page: 1 }))} />
          </Col>
          <Col xs={24} sm={7} style={{ textAlign: 'right' }}>
            <Space>
              <Tooltip title="從 Ragic 同步最新資料">
                <Button icon={<SyncOutlined spin={syncing} />} onClick={handleSync} loading={syncing}>
                  重新整理
                </Button>
              </Tooltip>
              <Button
                icon={<BarChartOutlined />}
                onClick={() => setChartOpen(true)}
                style={{ background: 'linear-gradient(135deg,#667eea,#764ba2)', border: 'none', color: '#fff' }}
              >
                圖表
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Table */}
      <Card bodyStyle={{ padding: 0 }}>
        <Table rowKey="id" columns={columns} dataSource={records} loading={loading}
          scroll={{ x: 1400 }} size="middle" rowSelection={{ type: 'checkbox' }}
          pagination={{
            current: filters.page ?? 1, pageSize: filters.per_page ?? 20, total,
            showSizeChanger: true, showTotal: (t) => `共 ${t} 筆`,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          onChange={handleTableChange}
        />
      </Card>

      {/* ── 未檢查項目附表 ────────────────────────────────────────────────────── */}
      <MissingInspectTable records={records} allItems={options.inspect} />

      {/* ── Chart Modal ────────────────────────────────────────────────────── */}
      <Modal
        title={<Space><BarChartOutlined style={{ color: '#764ba2' }} /><span style={{ fontWeight: 700, fontSize: 16 }}>客房保養管理分析儀表板</span></Space>}
        open={chartOpen}
        onCancel={() => setChartOpen(false)}
        footer={null}
        width={960}
        style={{ top: 20 }}
        bodyStyle={{ padding: '16px 24px 24px', background: '#f5f6fa' }}
      >
        {/* Row 1: Completion Gauge + Status Pie */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          {/* Gauge */}
          <Col span={10}>
            <Card
              title="本月整體完成率"
              size="small"
              headStyle={{ background: 'linear-gradient(135deg,#667eea,#764ba2)', color: '#fff', borderRadius: '8px 8px 0 0' }}
              style={{ borderRadius: 8, height: 260 }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 8 }}>
                <ResponsiveContainer width="100%" height={150}>
                  <RadialBarChart
                    innerRadius="60%" outerRadius="100%"
                    data={radialData} startAngle={180} endAngle={0}
                  >
                    <RadialBar dataKey="value" cornerRadius={6} background={{ fill: '#f0f0f0' }}>
                      <Cell fill="#52c41a" />
                      <Cell fill="#f0f0f0" />
                    </RadialBar>
                  </RadialBarChart>
                </ResponsiveContainer>
                <div style={{ marginTop: -20, textAlign: 'center' }}>
                  <div style={{ fontSize: 36, fontWeight: 800, color: '#52c41a', lineHeight: 1 }}>
                    {completionRate}%
                  </div>
                  <div style={{ color: '#888', fontSize: 12, marginTop: 4 }}>
                    {stats?.completed ?? 0} / {stats?.total ?? 0} 筆已完成
                  </div>
                </div>
                <Progress
                  percent={completionRate}
                  strokeColor={{ '0%': '#52c41a', '100%': '#52c41a' }}
                  trailColor="#ffccc7"
                  style={{ width: '90%', marginTop: 8 }}
                  showInfo={false}
                />
              </div>
            </Card>
          </Col>

          {/* Status Pie */}
          <Col span={14}>
            <Card
              title="工作項目狀態分佈"
              size="small"
              headStyle={{ background: 'linear-gradient(135deg,#11998e,#38ef7d)', color: '#fff', borderRadius: '8px 8px 0 0' }}
              style={{ borderRadius: 8, height: 260 }}
            >
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={statusPieData} cx="40%" cy="50%"
                    innerRadius={50} outerRadius={80}
                    paddingAngle={3} dataKey="value"
                    label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {statusPieData.map((entry, index) => (
                      <Cell
                        key={entry.name}
                        fill={WORK_ITEM_TAG[entry.name]?.hex ?? PIE_COLORS[index % PIE_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <RTooltip formatter={(val, name) => [`${val} 筆`, name]} />
                  <Legend
                    layout="vertical" align="right" verticalAlign="middle"
                    formatter={(value) => <span style={{ fontSize: 12 }}>{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        </Row>

        {/* Row 2: Incomplete Bar + Item Frequency */}
        <Row gutter={16}>
          {/* Incomplete per room */}
          <Col span={13}>
            <Card
              title="各客房未完成 vs 小計項目數"
              size="small"
              headStyle={{ background: 'linear-gradient(135deg,#f7971e,#ffd200)', color: '#fff', borderRadius: '8px 8px 0 0' }}
              style={{ borderRadius: 8 }}
            >
              {incompleteBarData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={incompleteBarData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="room" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <RTooltip />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="subtotal" name="小計" fill="#1677ff" radius={[3, 3, 0, 0]}>
                      <LabelList dataKey="subtotal" position="top" style={{ fontSize: 10, fill: '#1677ff' }} />
                    </Bar>
                    <Bar dataKey="incomplete" name="未完成" fill="#ff4d4f" radius={[3, 3, 0, 0]}>
                      <LabelList dataKey="incomplete" position="top" style={{ fontSize: 10, fill: '#ff4d4f' }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa' }}>
                  暫無資料
                </div>
              )}
            </Card>
          </Col>

          {/* Inspect item frequency */}
          <Col span={11}>
            <Card
              title="檢查項目執行頻率 TOP 8"
              size="small"
              headStyle={{ background: 'linear-gradient(135deg,#c471ed,#12c2e9)', color: '#fff', borderRadius: '8px 8px 0 0' }}
              style={{ borderRadius: 8 }}
            >
              {itemFreqData.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart
                    data={itemFreqData} layout="vertical"
                    margin={{ top: 4, right: 40, left: 4, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
                    <YAxis type="category" dataKey="item" width={72} tick={{ fontSize: 11 }} />
                    <RTooltip formatter={(val) => [`${val} 次`, '頻率']} />
                    <Bar dataKey="count" name="次數" radius={[0, 4, 4, 0]}>
                      {itemFreqData.map((_, index) => (
                        <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                      <LabelList dataKey="count" position="right" style={{ fontSize: 11, fontWeight: 600 }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa' }}>
                  暫無資料
                </div>
              )}
            </Card>
          </Col>
        </Row>

        <Divider style={{ margin: '16px 0 8px' }} />
        <div style={{ textAlign: 'center', color: '#aaa', fontSize: 12 }}>
          數據來源：本地 SQLite（每 30 分鐘自動從 Ragic 同步）· 上次同步時間以右上角重新整理為準
        </div>
      </Modal>

      {/* ── Create / Edit Modal ───────────────────────────────────────────── */}
      <Modal
        title={editingRecord ? '編輯客房保養記錄' : '新增客房保養記錄'}
        open={modalOpen} onOk={handleModalOk} onCancel={() => setModalOpen(false)}
        okText={editingRecord ? '儲存' : '新增'} cancelText="取消"
        width={600} destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="room_no" label="房號" rules={[{ required: true, message: '請輸入房號' }]}>
                <Input placeholder="例：503" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="dept" label="報修部門 / 負責人" rules={[{ required: true, message: '請輸入負責人' }]}>
                <Input placeholder="例：郭傑夫" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="inspect_items" label="檢查項目">
            <Checkbox.Group style={{ width: '100%' }}>
              <Row gutter={[8, 8]}>
                {(options.inspect.length ? options.inspect : [
                  '客房房門','客房窗','浴間','配電盤','客房設備','客房燈/電源','浴廁','空調',
                ]).map((item) => (
                  <Col span={8} key={item}><Checkbox value={item}>{item}</Checkbox></Col>
                ))}
              </Row>
            </Checkbox.Group>
          </Form.Item>
          <Form.Item name="work_item" label="工作項目選擇" rules={[{ required: true, message: '請選擇工作狀態' }]}>
            <Select placeholder="選擇工作狀態">
              {(options.workItems.length ? options.workItems : [
                '已完成檢視及保養','非本月排程','進行中','待排程',
              ]).map((item) => <Option key={item} value={item}>{item}</Option>)}
            </Select>
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="inspect_datetime" label="檢查日期時間" rules={[{ required: true, message: '請選擇檢查日期' }]}>
                <DatePicker showTime={{ format: 'HH:mm' }} format="YYYY/MM/DD HH:mm" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="close_date" label="結案日期">
                <DatePicker format="YYYY/MM/DD" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  )
}
