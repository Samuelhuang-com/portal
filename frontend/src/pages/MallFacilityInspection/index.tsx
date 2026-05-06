/**
 * 商場工務巡檢 — 統一整合頁面（掛於商場管理群組）
 *
 * 將原本分散的 Dashboard + 4F / 3F / 1F~3F / 1F / B1F~B4F 巡檢紀錄整合為 Tabs
 *   Tab 1 統計總覽      — 今日各區域 KPI + Sheet 完成率彙整
 *   Tab 2 4F 巡檢      — 月份篩選 + 場次清單
 *   Tab 3 3F 巡檢      — 同上
 *   Tab 4 1F~3F 巡檢   — 同上
 *   Tab 5 1F 巡檢      — 同上
 *   Tab 6 B1F~B4F 巡檢 — 同上
 *
 * URL query param：?tab=summary|daily-form|4f|3f|1f-3f|1f|b1f-b4f
 */
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress, Tooltip,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, ToolOutlined, ClockCircleOutlined, LinkOutlined,
  CalendarOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  MALL_FACILITY_INSPECTION_SHEET_LIST,
  MALL_FACILITY_INSPECTION_SHEETS,
  type MallFacilityInspectionSheet,
} from '@/constants/mallFacilityInspection'
import {
  fetchMallFacilityMonthlyDashboard,
  fetchMallFacilityBatches,
  syncMallFacilityAllFromRagic,
  syncMallFacilityFromRagic,
  fetchMallFIDailyCalendar,
  type MallFIMonthlySheetSummary,
} from '@/api/mallFacilityInspection'
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'
import MallDailyInspectionFormTab from '@/pages/MallPeriodicMaintenance/MallDailyInspectionFormTab'

const { Title, Text } = Typography

// Type definitions (SheetStats no longer needed — SummaryTabContent uses MallFIMonthlySheetSummary)

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
      const data = await fetchMallFacilityBatches(sheetKey, { year_month: yearMonth })
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
      await syncMallFacilityFromRagic(sheetKey)
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

// Summary tab — 月份統計版

function SummaryTabContent() {
  const [searchParams, setSearchParams] = useSearchParams()

  const initMonth = searchParams.get('month') ?? dayjs().format('YYYY-MM')
  const [queryMonth, setQueryMonth] = useState<string>(initMonth)
  const [loading,    setLoading]    = useState(false)
  const [syncing,    setSyncing]    = useState(false)
  const [sheets,     setSheets]     = useState<MallFIMonthlySheetSummary[]>([])
  const [error,      setError]      = useState<string | null>(null)
  const [calRows,    setCalRows]    = useState<CalendarRow[]>([])
  const [calMaxDay,  setCalMaxDay]  = useState(31)

  const isCurrentMonth = queryMonth === dayjs().format('YYYY-MM')
  const monthLabel     = dayjs(queryMonth, 'YYYY-MM').format('YYYY年M月')

  const handleMonthChange = (m: string) => {
    setQueryMonth(m)
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('month', m)
      return next
    }, { replace: true })
  }

  const loadSummary = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [yr, mo] = queryMonth.split('-').map(Number)
      const [data, calData] = await Promise.all([
        fetchMallFacilityMonthlyDashboard(queryMonth),
        fetchMallFIDailyCalendar(yr, mo).catch(() => null),
      ])
      setSheets(data.sheets)
      if (calData) {
        setCalMaxDay(calData.max_day)
        setCalRows(calData.sheets.map((s) => ({
          key:   s.key,
          label: s.floor,
          daily: s.daily,
        })))
      }
    } catch {
      setError('取得統計資料失敗，請稍後再試')
      setSheets([])
    } finally {
      setLoading(false)
    }
  }, [queryMonth])

  useEffect(() => { loadSummary() }, [loadSummary])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncMallFacilityAllFromRagic()
      message.success('全部 Sheet 同步已啟動，稍後請重新整理查看最新資料')
      setTimeout(() => loadSummary(), 3000)
    } catch {
      message.error('同步失敗，請稍後再試')
    } finally {
      setSyncing(false)
    }
  }

  const totalLogged  = sheets.filter((s) => s.has_today).length
  const totalMissing = sheets.reduce((acc, s) => acc + s.missing_count, 0)
  const totalCount   = sheets.reduce((acc, s) => acc + s.month_count, 0)
  const hasAllToday  = sheets.length > 0 && totalLogged === sheets.length
  const todayLabel   = isCurrentMonth ? '今日已登錄' : '末日已登錄'

  return (
    <div>
      {/* ── 操作列 ────────────────────────────────────────────────────────── */}
      <Row style={{ marginBottom: 16 }} align="middle" gutter={8}>
        <Col>
          <Space>
            <Text strong>查詢月份：</Text>
            <DatePicker
              picker="month"
              value={dayjs(queryMonth, 'YYYY-MM')}
              format="YYYY/MM"
              allowClear={false}
              onChange={(d) => { if (d) handleMonthChange(d.format('YYYY-MM')) }}
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
        <Col flex="auto" />
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>{monthLabel}統計</Text>
        </Col>
      </Row>

      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 16 }} closable onClose={() => setError(null)} />
      )}

      {/* ── 頂部 KPI 卡片 ─────────────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          { title: todayLabel,           value: totalLogged,  suffix: `/ ${sheets.length} 區域`,
            color: hasAllToday ? '#52C41A' : '#FAAD14',       icon: hasAllToday ? <CheckCircleOutlined /> : <ExclamationCircleOutlined /> },
          { title: `${monthLabel}累計缺漏`, value: totalMissing, suffix: '天',
            color: totalMissing > 0 ? '#FF4D4F' : '#52C41A', icon: totalMissing > 0 ? <WarningOutlined /> : <CheckCircleOutlined /> },
          { title: `${monthLabel}登錄場次`, value: totalCount,  suffix: '筆',
            color: '#1B3A5C',                                 icon: <DashboardOutlined /> },
          { title: '監控區域數',            value: sheets.length, suffix: '區',
            color: '#4BA8E8',                                 icon: <ToolOutlined /> },
        ].map((card) => (
          <Col flex={1} style={{ minWidth: 140 }} key={card.title}>
            <Card size="small" hoverable loading={loading} style={{ height: '100%' }}>
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
      </Row>

      {/* ── 各 Sheet 狀態卡片 ─────────────────────────────────────────────── */}
      <Row gutter={[16, 16]}>
        {sheets.map((sheet) => {
          const sheetCfg = MALL_FACILITY_INSPECTION_SHEETS[sheet.key]
          const color    = sheetCfg?.color ?? '#1B3A5C'

          return (
            <Col xs={24} sm={12} md={12} lg={8} key={sheet.key}>
              <Card
                size="small"
                loading={loading}
                title={
                  <Space>
                    <span style={{ color }}>{sheet.title}</span>
                    {sheet.has_today
                      ? <Tag color="success">{isCurrentMonth ? '今日已登錄' : '末日已登錄'}</Tag>
                      : <Tag color="warning">{isCurrentMonth ? '今日未登錄' : '末日未登錄'}</Tag>}
                  </Space>
                }
                extra={
                  sheetCfg && (
                    <Tooltip title="前往 Ragic 原始表單">
                      <a href={sheetCfg.ragicUrl} target="_blank" rel="noreferrer">
                        <LinkOutlined />
                      </a>
                    </Tooltip>
                  )
                }
              >
                <Row gutter={8}>
                  <Col span={12}>
                    <Statistic
                      title={`${monthLabel}登錄`}
                      value={sheet.month_count}
                      suffix="筆"
                      valueStyle={{ fontSize: 18 }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="缺漏天數"
                      value={sheet.missing_count}
                      suffix="天"
                      valueStyle={{
                        fontSize: 18,
                        color: sheet.missing_count > 0 ? '#ff4d4f' : '#52c41a',
                      }}
                    />
                  </Col>
                </Row>

                {/* 最近登錄日期 */}
                <div style={{ marginTop: 8, color: '#64748b', fontSize: 12 }}>
                  最近登錄：{sheet.latest_batch_date || '（無資料）'}
                </div>

                {/* 缺漏日期列表（最多顯示 5 個） */}
                {sheet.missing_count > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <Text type="danger" style={{ fontSize: 11 }}>
                      缺漏：{sheet.missing_days.slice(0, 5).join('、')}
                      {sheet.missing_count > 5 && ` 等 ${sheet.missing_count} 天`}
                    </Text>
                  </div>
                )}

                {/* 近 7 天趨勢點 */}
                <div style={{ marginTop: 8, display: 'flex', gap: 3 }}>
                  {sheet.trend_7d.map((t) => (
                    <Tooltip key={t.date} title={t.date}>
                      <div
                        style={{
                          width: 10, height: 10, borderRadius: '50%',
                          backgroundColor: t.has_record ? '#52c41a' : '#ff7875',
                        }}
                      />
                    </Tooltip>
                  ))}
                  <Text type="secondary" style={{ fontSize: 10, marginLeft: 4 }}>
                    近 7 天
                  </Text>
                </div>
              </Card>
            </Col>
          )
        })}
      </Row>

      {/* 月曆格：樓層 × 日期 */}
      <Card
        size="small"
        style={{ marginTop: 16 }}
        title={
          <Space>
            <CalendarOutlined />
            <Text strong>商場工務每日巡檢狀況</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              （{monthLabel}）
            </Text>
          </Space>
        }
        loading={loading}
      >
        {calRows.length > 0 ? (
          <MonthlyCalendarGrid
            year={parseInt(queryMonth.split('-')[0])}
            month={parseInt(queryMonth.split('-')[1])}
            maxDay={calMaxDay}
            rows={calRows}
            rowHeaderLabel="巡檢區域"
          />
        ) : (
          <Text type="secondary">尚無月曆資料</Text>
        )}
      </Card>

      {!loading && sheets.length === 0 && !error && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          message={`${monthLabel}尚無任何工務巡檢記錄，請確認巡檢是否已執行並同步。`}
          showIcon
        />
      )}
    </div>
  )
}

// Main component

const VALID_TABS = ['summary', 'daily-form', '4f', '3f', '1f-3f', '1f', 'b1f-b4f']

export default function MallFacilityInspectionDashboard() {
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
          { title: NAV_GROUP.mall },
          { title: NAV_PAGE.mallFacilityDashboard },
        ]}
      />

      <Row align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <ToolOutlined /> {NAV_PAGE.mallFacilityDashboard}
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
            label:    <span><CalendarOutlined /> 每日巡檢表</span>,
            children: openedTabs.has('daily-form') ? <MallDailyInspectionFormTab /> : null,
          },
          {
            key:      '4f',
            label:    '4F 巡檢',
            children: openedTabs.has('4f') ? <FloorListTab sheetKey="4f" /> : null,
          },
          {
            key:      '3f',
            label:    '3F 巡檢',
            children: openedTabs.has('3f') ? <FloorListTab sheetKey="3f" /> : null,
          },
          {
            key:      '1f-3f',
            label:    '1F~3F 巡檢',
            children: openedTabs.has('1f-3f') ? <FloorListTab sheetKey="1f-3f" /> : null,
          },
          {
            key:      '1f',
            label:    '1F 巡檢',
            children: openedTabs.has('1f') ? <FloorListTab sheetKey="1f" /> : null,
          },
          {
            key:      'b1f-b4f',
            label:    'B1F~B4F 巡檢',
            children: openedTabs.has('b1f-b4f') ? <FloorListTab sheetKey="b1f-b4f" /> : null,
          },
        ]}
      />
    </div>
  )
}
