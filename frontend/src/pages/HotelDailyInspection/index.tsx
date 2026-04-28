/**
 * 飯店每日巡檢 — 統一整合頁面（掛於飯店管理群組）
 *
 * 將各區域 Dashboard + 巡檢紀錄整合為 Tabs
 *   Tab 1 統計總覽      — 今日各區域 KPI + Sheet 完成率彙整
 *   Tab 2 RF 巡檢       — 月份篩選 + 場次清單
 *   Tab 3 4F-10F 巡檢   — 同上
 *   Tab 4 4F 巡檢       — 同上
 *   Tab 5 2F 巡檢       — 同上
 *   Tab 6 1F 巡檢       — 同上
 *
 * URL query param：?tab=summary|rf|4f-10f|4f|2f|1f
 */
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, ToolOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  HOTEL_DAILY_INSPECTION_SHEET_LIST,
  type HotelDailyInspectionSheet,
} from '@/constants/hotelDailyInspection'
import {
  fetchHotelDailyDashboardSummary,
  fetchHotelDailyBatches,
  syncHotelDailyAllFromRagic,
  syncHotelDailyFromRagic,
  type HotelDISheetSummary,
} from '@/api/hotelDailyInspection'

const { Title, Text } = Typography

// Type definitions

interface SheetStats extends HotelDailyInspectionSheet, HotelDISheetSummary {}

interface BatchRow {
  id:              string
  inspection_date: string
  inspector_name:  string
  completion_rate: number
  total:           number
  checked:         number
  abnormal:        number
  pending:         number
}

// Shared floor inspection list tab

function FloorListTab({ sheetKey }: { sheetKey: string }) {
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
  const [syncing,   setSyncing]   = useState(false)
  const [batches,   setBatches]   = useState<BatchRow[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchHotelDailyBatches(sheetKey, { year_month: yearMonth })
      setBatches(data)
    } catch {
      setBatches([])
    } finally {
      setLoading(false)
    }
  }, [sheetKey, yearMonth])

  useEffect(() => { load() }, [load])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncHotelDailyFromRagic(sheetKey)
      message.success('同步已啟動，稍後請重新整理查看最新資料')
      setTimeout(() => load(), 3000)
    } catch {
      message.error('同步失敗，請稍後再試')
    } finally {
      setSyncing(false)
    }
  }

  const columns = [
    {
      title: '巡檢日期',
      dataIndex: 'inspection_date',
      width: 110,
      sorter: (a: BatchRow, b: BatchRow) =>
        a.inspection_date.localeCompare(b.inspection_date),
      defaultSortOrder: 'descend' as const,
    },
    {
      title: '巡檢人員',
      dataIndex: 'inspector_name',
      width: 100,
    },
    {
      title: '狀態',
      width: 90,
      render: (_: unknown, row: BatchRow) => {
        if (row.abnormal > 0)                          return <Tag color="#FF4D4F">有異常</Tag>
        if (row.pending  > 0)                          return <Tag color="#FAAD14">待處理</Tag>
        if (row.checked >= row.total && row.total > 0) return <Tag color="#52C41A">已完成</Tag>
        return <Tag color="#4BA8E8">巡檢中</Tag>
      },
    },
    {
      title: '巡檢進度',
      width: 200,
      render: (_: unknown, row: BatchRow) => (
        <div>
          <Progress
            percent={row.completion_rate}
            size="small"
            strokeColor={{ from: '#FAAD14', to: '#52C41A' }}
            format={() => `${row.completion_rate}%`}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            {row.checked} / {row.total} 已巡檢
          </Text>
        </div>
      ),
    },
    {
      title: '異常',
      dataIndex: 'abnormal',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: 'pending',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
  ]

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
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
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新整理
          </Button>
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
      <Table<BatchRow>
        dataSource={batches}
        rowKey="id"
        columns={columns}
        loading={loading}
        size="middle"
        pagination={{ pageSize: 30, showTotal: (t) => `共 ${t} 筆` }}
        locale={{ emptyText: '尚無巡檢紀錄（請先執行資料同步）' }}
      />
    </div>
  )
}

// Summary tab

function SummaryTabContent() {
  const [targetDate, setTargetDate] = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [loading,    setLoading]    = useState(false)
  const [syncing,    setSyncing]    = useState(false)

  const buildEmptyStats = (): SheetStats[] =>
    HOTEL_DAILY_INSPECTION_SHEET_LIST.map((s) => ({
      ...s,
      total_batches:   0,
      total_items:     0,
      checked_items:   0,
      abnormal_items:  0,
      pending_items:   0,
      unchecked_items: 0,
      completion_rate: 0,
      total_minutes:   0,
      has_data:        false,
    }))

  const [sheets, setSheets] = useState<SheetStats[]>(buildEmptyStats())

  const loadSummary = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchHotelDailyDashboardSummary(targetDate)
      const merged: SheetStats[] = HOTEL_DAILY_INSPECTION_SHEET_LIST.map((s) => {
        const apiSheet = data.sheets.find((d) => d.key === s.key)
        return apiSheet
          ? { ...s, ...apiSheet }
          : { ...s, total_batches: 0, total_items: 0, checked_items: 0,
              abnormal_items: 0, pending_items: 0, unchecked_items: 0,
              completion_rate: 0, total_minutes: 0, has_data: false }
      })
      setSheets(merged)
    } catch {
      setSheets(buildEmptyStats())
    } finally {
      setLoading(false)
    }
  }, [targetDate])

  useEffect(() => { loadSummary() }, [loadSummary])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncHotelDailyAllFromRagic()
      message.success('全部 Sheet 同步已啟動，稍後請重新整理查看最新資料')
      setTimeout(() => loadSummary(), 3000)
    } catch {
      message.error('同步失敗，請稍後再試')
    } finally {
      setSyncing(false)
    }
  }

  const totalBatches   = sheets.reduce((s, r) => s + r.total_batches, 0)
  const checkedAll     = sheets.reduce((s, r) => s + r.checked_items, 0)
  const totalAll       = sheets.reduce((s, r) => s + r.total_items,   0)
  const abnormalAll    = sheets.reduce((s, r) => s + r.abnormal_items + r.pending_items, 0)
  const rateAll        = totalAll > 0 ? Math.round((checkedAll / totalAll) * 100) : 0
  const totalMinutes   = sheets.reduce((s, r) => s + (r.total_minutes ?? 0), 0)

  const sheetCols = [
    {
      title: '巡檢區域',
      dataIndex: 'title',
      ellipsis: true,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '場次',
      dataIndex: 'total_batches',
      width: 60,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#1B3A5C" showZero /> : <Text type="secondary">—</Text>,
    },
    {
      title: '完成率',
      dataIndex: 'completion_rate',
      width: 130,
      render: (v: number, row: SheetStats) =>
        row.has_data ? (
          <Progress
            percent={v}
            size="small"
            strokeColor={{ from: v < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
            format={(p) => `${p}%`}
          />
        ) : (
          <Text type="secondary">無資料</Text>
        ),
    },
    {
      title: '異常',
      dataIndex: 'abnormal_items',
      width: 60,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: 'pending_items',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '未巡檢',
      dataIndex: 'unchecked_items',
      width: 65,
      align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#999" /> : <Text type="secondary">—</Text>,
    },
  ]

  return (
    <div>
      <Row style={{ marginBottom: 16 }} align="middle" gutter={8}>
        <Col>
          <Space>
            <Text strong>查詢日期：</Text>
            <DatePicker
              value={dayjs(targetDate, 'YYYY/MM/DD')}
              format="YYYY/MM/DD"
              allowClear={false}
              onChange={(d) => { if (d) setTargetDate(d.format('YYYY/MM/DD')) }}
            />
            <Button icon={<ReloadOutlined />} onClick={loadSummary} loading={loading}>
              重新整理
            </Button>
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

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          { title: '今日巡檢場次',  value: totalBatches, color: '#1B3A5C', icon: <DashboardOutlined /> },
          { title: '已巡檢項目',    value: checkedAll, suffix: `/${totalAll}`, color: '#4BA8E8', icon: <CheckCircleOutlined /> },
          { title: '異常 + 待處理', value: abnormalAll, color: '#FF4D4F', icon: <WarningOutlined /> },
          { title: '整體完成率',    value: rateAll, suffix: '%', color: rateAll >= 80 ? '#52C41A' : '#FAAD14', icon: <ExclamationCircleOutlined /> },
        ].map((card) => (
          <Col flex={1} style={{ minWidth: 140 }} key={card.title}>
            <Card size="small" hoverable style={{ height: '100%' }}>
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
        <Col flex={1} style={{ minWidth: 140 }}>
          <Card size="small" hoverable style={{ height: '100%' }}>
            <Statistic
              title="巡檢時間"
              value={Math.round(totalMinutes / 60 * 10) / 10}
              suffix="小時"
              prefix={<span style={{ color: '#4BA8E8' }}><ClockCircleOutlined /></span>}
              valueStyle={{ color: '#4BA8E8', fontSize: 26 }}
            />
          </Card>
        </Col>
      </Row>

      <Card size="small">
        <Table<SheetStats>
          dataSource={sheets}
          rowKey="key"
          columns={sheetCols}
          loading={loading}
          size="small"
          pagination={false}
          locale={{ emptyText: '尚無資料' }}
        />
      </Card>

      {!loading && totalAll === 0 && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          message={`${targetDate} 尚無任何飯店每日巡檢記錄，請確認巡檢是否已執行並同步。`}
          showIcon
        />
      )}
    </div>
  )
}

// Main component

const VALID_TABS = ['summary', 'rf', '4f-10f', '4f', '2f', '1f']

export default function HotelDailyInspectionDashboard() {
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<string>(() => {
    const t = searchParams.get('tab')
    return t && VALID_TABS.includes(t) ? t : 'summary'
  })

  const [openedTabs, setOpenedTabs] = useState<Set<string>>(
    () => new Set([activeTab])
  )

  const handleTabChange = (key: string) => {
    setActiveTab(key)
    setOpenedTabs((prev) => new Set([...prev, key]))
  }

  return (
    <div style={{ padding: '0 4px' }}>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.hotel },
          { title: NAV_PAGE.hotelDailyInspection },
        ]}
      />

      <Row align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <ToolOutlined /> {NAV_PAGE.hotelDailyInspection}
          </Title>
        </Col>
      </Row>

      <Tabs
        type="card"
        activeKey={activeTab}
        onChange={handleTabChange}
        items={[
          {
            key:      'summary',
            label:    'Dashboard',
            children: openedTabs.has('summary') ? <SummaryTabContent /> : null,
          },
          {
            key:      'rf',
            label:    'RF 巡檢',
            children: openedTabs.has('rf') ? <FloorListTab sheetKey="rf" /> : null,
          },
          {
            key:      '4f-10f',
            label:    '4F~10F 巡檢',
            children: openedTabs.has('4f-10f') ? <FloorListTab sheetKey="4f-10f" /> : null,
          },
          {
            key:      '4f',
            label:    '4F 巡檢',
            children: openedTabs.has('4f') ? <FloorListTab sheetKey="4f" /> : null,
          },
          {
            key:      '2f',
            label:    '2F 巡檢',
            children: openedTabs.has('2f') ? <FloorListTab sheetKey="2f" /> : null,
          },
          {
            key:      '1f',
            label:    '1F 巡檢',
            children: openedTabs.has('1f') ? <FloorListTab sheetKey="1f" /> : null,
          },
        ]}
      />
    </div>
  )
}
