/**
 * 主管交辦／緊急事件 頁面
 *
 * TAB 1：上級交辦  ← 屬性 = "上級交辦"
 * TAB 2：緊急事件  ← 屬性 = "緊急事件"
 *
 * 遵守 CLAUDE.md Drawer Detail 強制規範
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Table, Tag, Button, Space,
  Typography, Select, Tabs,
  Drawer, Descriptions, message, Input, Badge,
  Image, Divider, Spin,
} from 'antd'
import {
  ReloadOutlined,
  AlertOutlined, BellOutlined, LinkOutlined,
  PictureOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import { fetchYears, fetchFilterOptions, fetchDetail, fetchDbImages } from '@/api/otherTasks'
import type { OtherTask, OtherTaskFilterOptions, OtherTaskImage } from '@/types/otherTasks'

const { Title, Text } = Typography
const { Option } = Select
const { Search } = Input

// ── 常數 ──────────────────────────────────────────────────────────────────────
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)

const STATUS_TAG_COLOR: Record<string, string> = {
  '結案':  'success',
  '已結案': 'success',
  '已完成': 'success',
  '完成':  'success',
  '處理中': 'processing',
  '進行中': 'processing',
  '候辦':  'warning',
  '待辦':  'warning',
  '待排程': 'warning',
  '取消':  'default',
}

const TAB_CONFIG = [
  { key: '上級交辦', label: '上級交辦', icon: <BellOutlined />,  tagColor: '#1B3A5C' },
  { key: '緊急事件', label: '緊急事件', icon: <AlertOutlined />, tagColor: '#c0392b' },
] as const

const fmtHours = (h: number | null | undefined) => {
  if (h == null) return '—'
  if (h < 0 || h > 9999) return '—'
  return `${h.toFixed(2)}`
}

// ═════════════════════════════════════════════════════════════════════════════
// 主元件
// ═════════════════════════════════════════════════════════════════════════════
export default function OtherTasksPage() {
  // ── 篩選狀態 ────────────────────────────────────────────────────────────────
  const [years, setYears] = useState<number[]>([])
  const [filterOptions, setFilterOptions] = useState<OtherTaskFilterOptions>({
    statuses: [], supervisors: [], engineers: [],
  })
  const [selectedYear,       setSelectedYear]       = useState<number | undefined>(undefined)
  const [selectedMonth,      setSelectedMonth]      = useState<number | undefined>(undefined)
  const [selectedStatus,     setSelectedStatus]     = useState<string | undefined>(undefined)
  const [selectedSupervisor, setSelectedSupervisor] = useState<string | undefined>(undefined)
  const [selectedEngineer,   setSelectedEngineer]   = useState<string | undefined>(undefined)
  const [search,             setSearch]             = useState<string>('')
  const [activeTab,          setActiveTab]          = useState<string>('上級交辦')

  // ── 表格狀態 ────────────────────────────────────────────────────────────────
  const [loading,  setLoading]  = useState(false)
  const [items,    setItems]    = useState<OtherTask[]>([])
  const [total,    setTotal]    = useState(0)
  const [page,     setPage]     = useState(1)
  const [pageSize, setPageSize] = useState(50)

  // ── Drawer 狀態 ─────────────────────────────────────────────────────────────
  const [drawerOpen,   setDrawerOpen]   = useState(false)
  const [drawerRecord, setDrawerRecord] = useState<OtherTask | null>(null)
  const [drawerImages, setDrawerImages] = useState<OtherTaskImage[]>([])
  const [imagesLoading, setImagesLoading] = useState(false)

  // ── 初始化 ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    fetchYears().then(({ years }) => {
      setYears(years)
      if (years.length > 0) setSelectedYear(years[0])
    }).catch(() => {})
    fetchFilterOptions().then(setFilterOptions).catch(() => {})
  }, [])

  // ── 資料載入 ────────────────────────────────────────────────────────────────
  const loadData = useCallback(async (resetPage = false) => {
    const currentPage = resetPage ? 1 : page
    if (resetPage) setPage(1)
    setLoading(true)
    try {
      const result = await fetchDetail({
        task_type:  activeTab,
        year:       selectedYear,
        month:      selectedMonth,
        status:     selectedStatus,
        supervisor: selectedSupervisor,
        engineer:   selectedEngineer,
        search:     search || undefined,
        page:       currentPage,
        page_size:  pageSize,
        sort_field: 'created_at',
        sort_order: 'desc',
      })
      setItems(result.items)
      setTotal(result.total)
    } catch (err) {
      message.error('資料載入失敗')
    } finally {
      setLoading(false)
    }
  }, [activeTab, selectedYear, selectedMonth, selectedStatus,
      selectedSupervisor, selectedEngineer, search, page, pageSize])

  useEffect(() => { loadData() }, [loadData])

  // ── TAB 切換時重置頁碼 ──────────────────────────────────────────────────────
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    setPage(1)
  }

  // ── Drawer 開啟 ──────────────────────────────────────────────────────────────
  const handleRowClick = (record: OtherTask) => {
    setDrawerRecord(record)
    setDrawerImages(record.images ?? [])
    setDrawerOpen(true)
    // 如果 to_dict 回傳的 images 是空的，從 /db-images 再撈一次
    if (!record.images || record.images.length === 0) {
      setImagesLoading(true)
      fetchDbImages(record.ragic_id)
        .then(({ images }) => setDrawerImages(images))
        .catch(() => {})
        .finally(() => setImagesLoading(false))
    }
  }

  // ── 表格欄位定義 ─────────────────────────────────────────────────────────────
  const columns: ColumnsType<OtherTask> = [
    {
      title: '建立日期',
      dataIndex: 'created_at',
      width: 150,
      sorter: false,
      render: (v: string) => v || '—',
    },
    {
      title: '交辦主管',
      dataIndex: 'supervisor',
      width: 100,
      render: (v: string) => v || '—',
    },
    {
      title: '工程人員',
      dataIndex: 'engineer',
      width: 100,
      render: (v: string) => v || '—',
    },
    {
      title: '問題說明',
      dataIndex: 'description',
      ellipsis: true,
      render: (v: string) => v || '—',
    },
    {
      title: '備註',
      dataIndex: 'notes',
      width: 180,
      ellipsis: true,
      render: (v: string) => v || '—',
    },
    {
      title: '最後更新日期',
      dataIndex: 'updated_at',
      width: 150,
      render: (v: string) => v || '—',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => (
        <Tag color={STATUS_TAG_COLOR[v] ?? 'default'}>{v || '—'}</Tag>
      ),
    },
    {
      title: '維修工時',
      dataIndex: 'work_hours',
      width: 90,
      align: 'right',
      render: (v: number | null) => (
        <Text style={{ color: v != null && v > 0 ? '#1B3A5C' : undefined, fontWeight: v != null && v > 0 ? 600 : 400 }}>
          {fmtHours(v)}
        </Text>
      ),
    },
  ]

  // ── 篩選列 ────────────────────────────────────────────────────────────────────
  const FilterBar = () => (
    <Row gutter={[8, 8]} align="middle" style={{ marginBottom: 12 }}>
      <Col>
        <Select
          placeholder="年份"
          allowClear
          style={{ width: 90 }}
          value={selectedYear}
          onChange={(v) => { setSelectedYear(v); setPage(1) }}
        >
          {years.map(y => <Option key={y} value={y}>{y}</Option>)}
        </Select>
      </Col>
      <Col>
        <Select
          placeholder="月份"
          allowClear
          style={{ width: 80 }}
          value={selectedMonth}
          onChange={(v) => { setSelectedMonth(v); setPage(1) }}
        >
          {MONTHS.map(m => <Option key={m} value={m}>{m} 月</Option>)}
        </Select>
      </Col>
      <Col>
        <Select
          placeholder="狀態"
          allowClear
          style={{ width: 110 }}
          value={selectedStatus}
          onChange={(v) => { setSelectedStatus(v); setPage(1) }}
        >
          {filterOptions.statuses.map(s => (
            <Option key={s} value={s}>
              <Tag color={STATUS_TAG_COLOR[s] ?? 'default'} style={{ margin: 0 }}>{s}</Tag>
            </Option>
          ))}
        </Select>
      </Col>
      <Col>
        <Select
          placeholder="交辦主管"
          allowClear
          style={{ width: 120 }}
          value={selectedSupervisor}
          onChange={(v) => { setSelectedSupervisor(v); setPage(1) }}
        >
          {filterOptions.supervisors.map(s => <Option key={s} value={s}>{s}</Option>)}
        </Select>
      </Col>
      <Col>
        <Select
          placeholder="工程人員"
          allowClear
          style={{ width: 120 }}
          value={selectedEngineer}
          onChange={(v) => { setSelectedEngineer(v); setPage(1) }}
        >
          {filterOptions.engineers.map(e => <Option key={e} value={e}>{e}</Option>)}
        </Select>
      </Col>
      <Col flex="1">
        <Search
          placeholder="搜尋問題說明、備註"
          allowClear
          style={{ maxWidth: 280 }}
          onSearch={(v) => { setSearch(v); setPage(1) }}
          onChange={(e) => { if (!e.target.value) { setSearch(''); setPage(1) } }}
        />
      </Col>
      <Col>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => loadData(true)}
          loading={loading}
        >
          重新整理
        </Button>
      </Col>
    </Row>
  )

  // ── 表格 ──────────────────────────────────────────────────────────────────────
  const TaskTable = ({ taskType }: { taskType: string }) => (
    <Table<OtherTask>
      rowKey="ragic_id"
      columns={columns}
      dataSource={items}
      loading={loading}
      size="small"
      scroll={{ x: 1000 }}
      pagination={{
        current:   page,
        pageSize:  pageSize,
        total:     total,
        showSizeChanger: true,
        showTotal: (t) => `共 ${t} 筆`,
        pageSizeOptions: ['20', '50', '100'],
        onChange: (p, ps) => { setPage(p); setPageSize(ps) },
      }}
      onRow={(record) => ({
        onClick: () => handleRowClick(record),
        style:   { cursor: 'pointer' },
      })}
      rowClassName={(record) =>
        record.status && ['候辦', '待辦', '待排程'].includes(record.status)
          ? 'ant-table-row-warning'
          : ''
      }
    />
  )

  // ── Drawer 標題列（CLAUDE.md 強制規範）─────────────────────────────────────────
  const drawerTitle = drawerRecord ? (() => {
    const tabCfg  = TAB_CONFIG.find(t => t.key === drawerRecord.task_type) ?? TAB_CONFIG[0]
    const identifier =
      drawerRecord.detail['報修編號'] ||
      drawerRecord.detail['日誌編號'] ||
      drawerRecord.description?.slice(0, 20) ||
      drawerRecord.ragic_id
    return (
      <Space size={8} wrap>
        <Tag color={tabCfg.tagColor} style={{ margin: 0 }}>{drawerRecord.task_type}</Tag>
        <Text strong>
          {drawerRecord.task_type === '緊急事件' ? '緊急事件' : '主管交辦'}：{identifier}
        </Text>
        {drawerRecord.ragic_url && (
          <a href={drawerRecord.ragic_url} target="_blank" rel="noreferrer"
             onClick={(e) => e.stopPropagation()}
             style={{ color: '#4BA8E8', fontSize: 13 }}>
            <LinkOutlined /> 在 Ragic 查看
          </a>
        )}
      </Space>
    )
  })() : null

  // ── Drawer 內容 ───────────────────────────────────────────────────────────────
  const DrawerContent = () => {
    if (!drawerRecord) return null
    const d = drawerRecord.detail

    // 基本欄位
    const basicItems = [
      { label: '屬性',       children: <Tag color={drawerRecord.task_type === '緊急事件' ? '#c0392b' : '#1B3A5C'}>{d['屬性'] || '—'}</Tag> },
      { label: '交辦主管',   children: d['交辦主管'] || '—' },
      { label: '工程人員',   children: d['工程人員'] || '—' },
      { label: '建立日期',   children: d['建立日期'] || '—' },
      { label: '最後更新',   children: d['最後更新日期'] || '—' },
      { label: '狀態',       children: <Tag color={STATUS_TAG_COLOR[d['狀態'] ?? ''] ?? 'default'}>{d['狀態'] || '—'}</Tag> },
      { label: '維修工時',   children: d['維修工時'] ? `${d['維修工時']} hr` : '—' },
    ]

    return (
      <div style={{ padding: '0 4px' }}>
        {/* 基本欄位 */}
        <Descriptions
          title="基本資訊"
          bordered
          size="small"
          column={2}
          style={{ marginBottom: 20 }}
          items={basicItems}
        />

        {/* 明細欄位 */}
        <Descriptions
          title="明細資訊"
          bordered
          size="small"
          column={1}
          items={[
            {
              label: '問題說明',
              children: (
                <Text style={{ whiteSpace: 'pre-wrap', fontWeight: 600 }}>
                  {d['問題說明'] || '—'}
                </Text>
              ),
            },
            {
              label: '備註',
              children: d['備註'] || '—',
            },
          ]}
        />

        {/* 附圖預覽 */}
        {imagesLoading && (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Spin tip="載入附圖..." />
          </div>
        )}
        {!imagesLoading && drawerImages.length > 0 && (
          <>
            <Divider orientation="left" style={{ marginTop: 20 }}>
              <Space><PictureOutlined /> 附圖（{drawerImages.length} 張）</Space>
            </Divider>
            <Image.PreviewGroup>
              <Row gutter={[8, 8]}>
                {drawerImages.map((img, idx) => (
                  <Col key={idx} span={8}>
                    <Image
                      src={img.url}
                      alt={img.filename || `附圖${idx + 1}`}
                      style={{ width: '100%', borderRadius: 4, objectFit: 'cover', aspectRatio: '1' }}
                    />
                  </Col>
                ))}
              </Row>
            </Image.PreviewGroup>
          </>
        )}
      </div>
    )
  }

  // ── 頁面渲染 ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 0 24px 0' }}>
      {/* 頁面標題 */}
      <Row align="middle" style={{ marginBottom: 16 }}>
        <Col flex="1">
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            主管交辦／緊急事件
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            來源：Ragic other-tasks/1
          </Text>
        </Col>
      </Row>

      {/* 篩選列 */}
      <Card bodyStyle={{ paddingBottom: 4, paddingTop: 12 }} style={{ marginBottom: 12 }}>
        <FilterBar />
      </Card>

      {/* 主要 TAB */}
      <Card bodyStyle={{ padding: '12px 16px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={handleTabChange}
          size="middle"
          tabBarExtraContent={
            <Text type="secondary" style={{ fontSize: 12 }}>
              共 <strong>{total}</strong> 筆
            </Text>
          }
          items={TAB_CONFIG.map(tab => ({
            key:   tab.key,
            label: (
              <Space>
                {tab.icon}
                {tab.label}
                {activeTab === tab.key && total > 0 && (
                  <Badge count={total} size="small" style={{ backgroundColor: tab.key === '緊急事件' ? '#c0392b' : '#1B3A5C' }} />
                )}
              </Space>
            ),
            children: <TaskTable taskType={tab.key} />,
          }))}
        />
      </Card>

      {/* Drawer 明細 */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={drawerImages.length > 0 ? 640 : 480}
        title={drawerTitle}
        destroyOnClose
      >
        <DrawerContent />
      </Drawer>
    </div>
  )
}
