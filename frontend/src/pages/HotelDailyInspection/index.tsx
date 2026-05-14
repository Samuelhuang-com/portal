/**
 * 飯店每日巡檢 — 統一整合頁面（掛於飯店管理群組）
 *
 * TAB 順序：
 *   1. Dashboard   — 月份彙整 KPI + 各 Sheet 摘要 + 每日狀況月曆格
 *   2. 每日巡檢表  — 標準模板彙整（YYYY+M + 可選日期篩選）
 *   3. RF 巡檢     — 月份篩選 + 場次清單
 *   4. 4F~10F 巡檢 — 同上
 *   5. 4F 巡檢     — 同上
 *   6. 2F 巡檢     — 同上
 *   7. 1F 巡檢     — 同上
 *
 * URL query param：?tab=summary|daily-form|rf|4f-10f|4f|2f|1f
 */
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Button, Space, Tooltip,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, ToolOutlined, ClockCircleOutlined,
  CalendarOutlined as CalendarOutlinedIcon,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  HOTEL_DAILY_INSPECTION_SHEET_LIST,
  type HotelDailyInspectionSheet,
} from '@/constants/hotelDailyInspection'
import {
  fetchHotelDailyMonthlyDashboard,
  fetchHotelDailyCalendar,
  fetchHotelDailyBatches,
  type HotelDISheetSummary,
  type DailyCalendarSheet,
} from '@/api/hotelDailyInspection'
import DailyInspectionFormTab from './DailyInspectionFormTab'
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'

const { Title, Text } = Typography

// ── 型別 ─────────────────────────────────────────────────────────────────────

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

// ── 共用：巡檢場次清單 TAB ───────────────────────────────────────────────────

function FloorListTab({ sheetKey }: { sheetKey: string }) {
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
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

  const columns = [
    {
      title: '巡檢日期',
      dataIndex: 'inspection_date',
      width: 110,
      sorter: (a: BatchRow, b: BatchRow) => a.inspection_date.localeCompare(b.inspection_date),
      defaultSortOrder: 'descend' as const,
    },
    { title: '巡檢人員', dataIndex: 'inspector_name', width: 100 },
    {
      title: '狀態',
      width: 90,
      render: (_: unknown, row: BatchRow) => {
        if (row.abnormal > 0)                          return <Badge status="error"   text="有異常" />
        if (row.pending  > 0)                          return <Badge status="warning" text="待處理" />
        if (row.checked >= row.total && row.total > 0) return <Badge status="success" text="已完成" />
        return <Badge status="processing" text="巡檢中" />
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
      title: '異常', dataIndex: 'abnormal', width: 65, align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理', dataIndex: 'pending', width: 65, align: 'center' as const,
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
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
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

// ── Dashboard TAB 內容 ────────────────────────────────────────────────────────

function SummaryTabContent() {
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)

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

  const [sheets,    setSheets]    = useState<SheetStats[]>(buildEmptyStats())
  const [calSheets, setCalSheets] = useState<DailyCalendarSheet[]>([])
  const [maxDay,    setMaxDay]    = useState<number>(31)

  const loadSummary = useCallback(async () => {
    setLoading(true)
    const [y, m] = yearMonth.split('/').map(Number)
    try {
      // 月份彙整 + 月曆格 並行取得
      const [monthData, calData] = await Promise.all([
        fetchHotelDailyMonthlyDashboard(y, m),
        fetchHotelDailyCalendar(y, m),
      ])

      const merged: SheetStats[] = HOTEL_DAILY_INSPECTION_SHEET_LIST.map((s) => {
        const api = monthData.sheets.find((d) => d.key === s.key)
        return api
          ? { ...s, ...api }
          : { ...s, total_batches: 0, total_items: 0, checked_items: 0,
              abnormal_items: 0, pending_items: 0, unchecked_items: 0,
              completion_rate: 0, total_minutes: 0, has_data: false }
      })
      setSheets(merged)
      setCalSheets(calData.sheets)
      setMaxDay(calData.max_day)
    } catch {
      setSheets(buildEmptyStats())
      setCalSheets([])
    } finally {
      setLoading(false)
    }
  }, [yearMonth])

  useEffect(() => { loadSummary() }, [loadSummary])

  const [y, m]       = yearMonth.split('/').map(Number)
  const totalBatches = sheets.reduce((s, r) => s + r.total_batches, 0)
  const checkedAll   = sheets.reduce((s, r) => s + r.checked_items, 0)
  const totalAll     = sheets.reduce((s, r) => s + r.total_items,   0)
  const abnormalAll  = sheets.reduce((s, r) => s + r.abnormal_items + r.pending_items, 0)
  const rateAll      = totalAll > 0 ? Math.round((checkedAll / totalAll) * 100) : 0
  const totalMinutes = sheets.reduce((s, r) => s + (r.total_minutes ?? 0), 0)

  const sheetCols = [
    {
      title: '巡檢區域',
      dataIndex: 'title',
      ellipsis: true,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '場次', dataIndex: 'total_batches', width: 60, align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#1B3A5C" showZero /> : <Text type="secondary">—</Text>,
    },
    {
      title: '完成率', dataIndex: 'completion_rate', width: 130,
      render: (v: number, row: SheetStats) =>
        row.has_data ? (
          <Progress
            percent={v} size="small"
            strokeColor={{ from: v < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
            format={(p) => `${p}%`}
          />
        ) : (
          <Text type="secondary">無資料</Text>
        ),
    },
    {
      title: '異常', dataIndex: 'abnormal_items', width: 60, align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理', dataIndex: 'pending_items', width: 65, align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '未巡檢', dataIndex: 'unchecked_items', width: 65, align: 'center' as const,
      render: (v: number) =>
        v > 0 ? <Badge count={v} color="#999" /> : <Text type="secondary">—</Text>,
    },
  ]

  return (
    <div>
      {/* 篩選列 */}
      <Row style={{ marginBottom: 16 }} align="middle" gutter={8}>
        <Col>
          <Space wrap>
            <Text strong>查詢月份：</Text>
            <DatePicker
              picker="month"
              value={dayjs(yearMonth, 'YYYY/MM')}
              format="YYYY/MM"
              allowClear={false}
              onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
            />
            <Button icon={<ReloadOutlined />} onClick={loadSummary} loading={loading}>
              重新整理
            </Button>
          </Space>
        </Col>
      </Row>

      {/* KPI 卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          { title: '本月巡檢場次',  value: totalBatches, color: '#1B3A5C', icon: <DashboardOutlined /> },
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
              title="本月巡檢時間"
              value={Math.round(totalMinutes / 60 * 10) / 10}
              suffix="小時"
              prefix={<span style={{ color: '#4BA8E8' }}><ClockCircleOutlined /></span>}
              valueStyle={{ color: '#4BA8E8', fontSize: 26 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Sheet 摘要表 */}
      <Card size="small" style={{ marginBottom: 16 }}>
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

      {/* 每日巡檢月曆格 */}
      <Card
        size="small"
        title={
          <Space>
            <CalendarOutlinedIcon style={{ color: '#4BA8E8' }} />
            <Text strong style={{ color: '#1B3A5C' }}>
              {yearMonth} 每日巡檢狀況
            </Text>
          </Space>
        }
        loading={loading}
      >
        {calSheets.length > 0 ? (
          <MonthlyCalendarGrid
            year={y} month={m} maxDay={maxDay}
            rows={calSheets.map((s) => ({ key: s.key, label: s.floor, daily: s.daily }))}
          />
        ) : (
          <Text type="secondary">尚無資料</Text>
        )}
      </Card>

      {!loading && totalAll === 0 && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          message={`${yearMonth} 整月尚無任何飯店每日巡檢記錄，請確認資料是否已同步。`}
          showIcon
        />
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

const VALID_TABS = ['summary', 'daily-form', 'rf', '4f-10f', '4f', '2f', '1f']

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
            key:      'daily-form',
            label:    '每日巡檢表',
            children: openedTabs.has('daily-form') ? <DailyInspectionFormTab /> : null,
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
