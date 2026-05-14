/**
 * 整棟巡檢 — 統一整合頁面（掛於商場管理群組）
 *
 * 將原本分散的 Dashboard + RF / B4F / B2F / B1F 巡檢紀錄整合為 Tabs
 *   Tab 1 Dashboard    — 今日各樓層 KPI + Sheet 完成率彙整 + 月曆格
 *   Tab 2 每日巡檢表   — 模板結構（待本地同步接通後顯示真實資料）
 *   Tab 3 RF 巡檢      — 月份篩選 + 場次清單
 *   Tab 4 B4F 巡檢     — 同上
 *   Tab 5 B2F 巡檢     — 同上
 *   Tab 6 B1F 巡檢     — 同上
 *
 * URL query param：?tab=summary|daily-form|rf|b4f|b2f|b1f
 * 資料來源：尚未建立本地同步，各欄位顯示空狀態，保留結構供日後擴充。
 */
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress, Tooltip,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, SafetyOutlined, ClockCircleOutlined, LinkOutlined,
  CalendarOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  FULL_BUILDING_INSPECTION_SHEETS,
} from '@/constants/fullBuildingInspection'
import {
  fetchFullBuildingMonthlyDashboard,
  fetchFullBuildingInspectionCalendar,
  fetchFullBuildingDailyForm,
  type FullBuildingMonthlySheetSummary,
  type FullBuildingDailyFormRow,
} from '@/api/fullBuildingInspection'
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'

const { Title, Text } = Typography

// ── 型別 ─────────────────────────────────────────────────────────────────────
// (SheetStats 已替換為 FullBuildingMonthlySheetSummary，來自 API 型別定義)

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

// ── 每日巡檢表 Tab ────────────────────────────────────────────────────────────

function FullBuildingDailyFormTab() {
  const today = dayjs()
  const [inspectionDate, setInspectionDate] = useState<string>(today.format('YYYY/MM/DD'))
  const [loading,  setLoading]  = useState(false)
  const [rows,     setRows]     = useState<FullBuildingDailyFormRow[]>([])
  const [stdTotal, setStdTotal] = useState(0)

  const load = useCallback(async (date: string) => {
    setLoading(true)
    try {
      const [yr, mo] = date.split('/').map(Number)
      const data = await fetchFullBuildingDailyForm(yr, mo, date)
      setRows(data.rows)
      setStdTotal(data.standard_minutes_total)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(inspectionDate) }, [load, inspectionDate])

  // ── Table 欄位 ────────────────────────────────────────────────────────────

  const columns = [
    {
      title:     '樓層',
      dataIndex: 'floor',
      width: 60,
      onCell: (record: FullBuildingDailyFormRow) => ({
        rowSpan: record.floor_first_row ? record.floor_row_count : 0,
        style:   { fontWeight: 600, verticalAlign: 'middle', background: '#f0f4f8', textAlign: 'center' as const },
      }),
    },
    {
      title:     '項目',
      dataIndex: 'item',
      width: 160,
      onCell: (record: FullBuildingDailyFormRow) => ({
        rowSpan: record.item_first_row ? record.item_row_count : 0,
        style:   { verticalAlign: 'middle', fontWeight: 500 },
      }),
    },
    {
      title:     '檢查內容',
      dataIndex: 'check_content',
      width: 240,
    },
    {
      title:     '運轉狀況（結果）',
      dataIndex: 'result_options',
      width: 200,
      render: (_: string, row: FullBuildingDailyFormRow) => {
        if (!row.matched) return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        return (
          <Space size={4} wrap>
            {row.result_text
              ? <Tag color={row.result_status === 'normal' ? '#52C41A' : row.result_status === 'abnormal' ? '#FF4D4F' : '#FAAD14'}>{row.result_text}</Tag>
              : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
            }
          </Space>
        )
      },
    },
    {
      title:     '實際巡檢人員',
      dataIndex: 'inspector',
      width: 110,
      render: (v: string) => v || <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title:     '異常說明',
      dataIndex: 'abnormal_note',
      render: (v: string) => v
        ? <Text type="danger" style={{ fontSize: 11, whiteSpace: 'pre-wrap' }}>{v}</Text>
        : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title:  '時間(分)',
      dataIndex: 'minutes',
      width: 75,
      align: 'center' as const,
      render: (v: number) => v > 0 ? <Text style={{ fontSize: 11 }}>{v}</Text> : null,
      onCell: (record: FullBuildingDailyFormRow) => ({
        rowSpan: record.item_first_row ? record.item_row_count : 0,
        style:   { verticalAlign: 'middle', textAlign: 'center' as const },
      }),
    },
  ]

  return (
    <div>
      {/* 操作列 */}
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <DatePicker
            value={dayjs(inspectionDate, 'YYYY/MM/DD')}
            format="YYYY/MM/DD"
            allowClear={false}
            onChange={(d) => { if (d) setInspectionDate(d.format('YYYY/MM/DD')) }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={() => load(inspectionDate)} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 12 }}
        message="整棟巡檢本地同步功能開發中"
        description="目前每日巡檢表尚未接通本地 DB，模板欄位已備妥。請至 Ragic 系統填寫各樓層巡檢表單，接通後資料將自動顯示於此。"
      />

      <Table<FullBuildingDailyFormRow>
        dataSource={rows}
        rowKey={(r) => `${r.floor}-${r.item}-${r.check_content}`}
        columns={columns}
        loading={loading}
        size="small"
        pagination={false}
        bordered
        rowClassName={(r) => r.abnormal ? 'row-abnormal' : ''}
        style={{ fontSize: 12 }}
        locale={{ emptyText: '尚無巡檢資料' }}
      />

      {/* 底部時間摘要 */}
      <Row gutter={24} style={{ marginTop: 12, padding: '8px 0' }}>
        <Col>
          <Space>
            <ClockCircleOutlined style={{ color: '#4BA8E8' }} />
            <Text type="secondary">標準巡檢時間（整體）：</Text>
            <Text strong>{stdTotal} 分鐘</Text>
          </Space>
        </Col>
      </Row>
    </div>
  )
}

// ── 共用樓層巡檢紀錄 Tab ──────────────────────────────────────────────────────

function FloorInspectionListTab({ sheetKey }: { sheetKey: string }) {
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
  const [batches,   setBatches]   = useState<BatchRow[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    // TODO: 接 API → fetchFullBuildingBatches(sheetKey, { year_month: yearMonth })
    await new Promise((r) => setTimeout(r, 100))
    setBatches([])
    setLoading(false)
  }, [sheetKey, yearMonth])

  useEffect(() => { load() }, [load])

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

// ── 統計總覽 Tab — 月份統計版 ─────────────────────────────────────────────────

function SummaryTabContent() {
  const [searchParams, setSearchParams] = useSearchParams()

  const initMonth = searchParams.get('month') ?? dayjs().format('YYYY-MM')
  const [queryMonth, setQueryMonth] = useState<string>(initMonth)
  const [loading,    setLoading]    = useState(false)
  const [sheets,     setSheets]     = useState<FullBuildingMonthlySheetSummary[]>([])
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
        fetchFullBuildingMonthlyDashboard(queryMonth),
        fetchFullBuildingInspectionCalendar(yr, mo).catch(() => null),
      ])
      setSheets(data.sheets)
      if (calData) { setCalMaxDay(calData.max_day); setCalRows(calData.rows) }
    } catch {
      setError('取得統計資料失敗，請稍後再試')
      setSheets([])
    } finally {
      setLoading(false)
    }
  }, [queryMonth])

  useEffect(() => { loadSummary() }, [loadSummary])

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
          { title: todayLabel,              value: totalLogged,  suffix: `/ ${sheets.length} 樓層`,
            color: hasAllToday ? '#52C41A' : '#FAAD14',          icon: hasAllToday ? <CheckCircleOutlined /> : <ExclamationCircleOutlined /> },
          { title: `${monthLabel}累計缺漏`, value: totalMissing, suffix: '天',
            color: totalMissing > 0 ? '#FF4D4F' : '#52C41A',    icon: totalMissing > 0 ? <WarningOutlined /> : <CheckCircleOutlined /> },
          { title: `${monthLabel}登錄場次`, value: totalCount,  suffix: '筆',
            color: '#1B3A5C',                                     icon: <DashboardOutlined /> },
          { title: '監控樓層數',             value: sheets.length, suffix: '層',
            color: '#4BA8E8',                                     icon: <SafetyOutlined /> },
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
          const sheetCfg = FULL_BUILDING_INSPECTION_SHEETS[sheet.key]
          const color    = sheetCfg?.color ?? '#1B3A5C'

          return (
            <Col xs={24} sm={12} md={12} lg={6} key={sheet.key}>
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

                <div style={{ marginTop: 8, color: '#64748b', fontSize: 12 }}>
                  最近登錄：{sheet.latest_batch_date || '（無資料）'}
                </div>

                {sheet.missing_count > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <Text type="danger" style={{ fontSize: 11 }}>
                      缺漏：{sheet.missing_days.slice(0, 5).join('、')}
                      {sheet.missing_count > 5 && ` 等 ${sheet.missing_count} 天`}
                    </Text>
                  </div>
                )}

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

      {!loading && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          message="整棟巡檢本地同步功能開發中"
          description="目前統計資料尚未接通本地 DB，請直接至 Ragic 查看各樓層巡檢表單。接通後數據將自動顯示於此。"
          showIcon
        />
      )}

      {/* 月曆格：各樓層 × 當月逐日巡檢狀況 */}
      <Card
        size="small"
        style={{ marginTop: 16 }}
        title={
          <Space>
            <CalendarOutlined />
            <Text strong>整棟巡檢月曆格</Text>
            <Text type="secondary" style={{ fontSize: 11, fontWeight: 400 }}>
              （{monthLabel} 各樓層逐日出勤）
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
            rowHeaderLabel="樓層"
          />
        ) : (
          <Text type="secondary">尚無月曆資料</Text>
        )}
      </Card>
    </div>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

const VALID_TABS = ['summary', 'daily-form', 'rf', 'b4f', 'b2f', 'b1f']

export default function FullBuildingInspectionDashboard() {
  const [searchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<string>(() => {
    const t = searchParams.get('tab')
    return t && VALID_TABS.includes(t) ? t : 'summary'
  })

  // 已開啟過的 Tab（懶載入：只在首次切入時掛載子元件）
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
          { title: NAV_PAGE.fullBuildingDashboard },
        ]}
      />

      <Row align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <SafetyOutlined /> {NAV_PAGE.fullBuildingDashboard}
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
            children: openedTabs.has('daily-form') ? <FullBuildingDailyFormTab /> : null,
          },
          {
            key:      'rf',
            label:    'RF 巡檢',
            children: openedTabs.has('rf') ? <FloorInspectionListTab sheetKey="rf" /> : null,
          },
          {
            key:      'b4f',
            label:    'B4F 巡檢',
            children: openedTabs.has('b4f') ? <FloorInspectionListTab sheetKey="b4f" /> : null,
          },
          {
            key:      'b2f',
            label:    'B2F 巡檢',
            children: openedTabs.has('b2f') ? <FloorInspectionListTab sheetKey="b2f" /> : null,
          },
          {
            key:      'b1f',
            label:    'B1F 巡檢',
            children: openedTabs.has('b1f') ? <FloorInspectionListTab sheetKey="b1f" /> : null,
          },
        ]}
      />
    </div>
  )
}
