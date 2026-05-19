/**
 * 每日數值登錄表 — 統一整合頁面（掛於飯店管理群組）
 *
 * 將 4 個 Ragic Sheet 整合為 Tabs：
 *   Tab 1  Dashboard      — 今日登錄狀態 + 月曆格 + 缺漏統計
 *   Tab 2  全棟水電錶      — 月份篩選 + 登錄清單
 *   Tab 3  商場空調箱電錶  — 同上
 *   Tab 4  專櫃電錶        — 同上
 *   Tab 5  專櫃水錶        — 同上
 *
 * URL query param：?tab=dashboard|building-electric|mall-ac-electric|tenant-electric|tenant-water
 */
import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker,
  Tooltip, Input,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined,
  DashboardOutlined, ReadOutlined, LinkOutlined,
  CalendarOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  HOTEL_METER_READINGS_SHEET_LIST,
  VALID_TABS,
  type HotelMeterReadingsSheet,
} from '@/constants/hotelMeterReadings'
import {
  fetchHotelMeterDashboardSummary,
  fetchHotelMeterBatches,
  fetchHotelMeterCalendar,
  type HotelMRSheetSummary,
  type HotelMRBatchRow,
  type HotelMRCalendarRow,
} from '@/api/hotelMeterReadings'
import MonthlyCalendarGrid, { type CalendarRow } from '@/components/MonthlyCalendarGrid'

const { Title, Text } = Typography
const { Search } = Input

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Tab — KPI + 月曆格 + Sheet 狀態卡片
// ─────────────────────────────────────────────────────────────────────────────

function DashboardTab() {
  const [searchParams, setSearchParams] = useSearchParams()

  const initMonth = searchParams.get('month') ?? dayjs().format('YYYY-MM')
  const [queryMonth,   setQueryMonth]   = useState<string>(initMonth)
  const [loading,      setLoading]      = useState(false)
  const [sheets,       setSheets]       = useState<HotelMRSheetSummary[]>([])
  const [calendarRows, setCalendarRows] = useState<CalendarRow[]>([])
  const [maxDay,       setMaxDay]       = useState<number>(31)
  const [error,        setError]        = useState<string | null>(null)

  const isCurrentMonth = queryMonth === dayjs().format('YYYY-MM')
  const monthLabel     = dayjs(queryMonth, 'YYYY-MM').format('YYYY年M月')
  const calYear        = parseInt(queryMonth.split('-')[0], 10)
  const calMonth       = parseInt(queryMonth.split('-')[1], 10)

  const handleMonthChange = (m: string) => {
    setQueryMonth(m)
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('month', m)
      return next
    }, { replace: true })
  }

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [summaryData, calendarData] = await Promise.all([
        fetchHotelMeterDashboardSummary({ month: queryMonth }),
        fetchHotelMeterCalendar(calYear, calMonth),
      ])
      setSheets(Array.isArray(summaryData?.sheets) ? summaryData.sheets : [])

      // 將後端 CalendarRow 轉換為 MonthlyCalendarGrid 所需格式
      const rows: CalendarRow[] = (calendarData?.rows ?? []).map(
        (r: HotelMRCalendarRow) => ({
          key:   r.key,
          label: r.label,
          daily: r.daily,
        }),
      )
      setCalendarRows(rows)
      setMaxDay(calendarData?.max_day ?? 31)
    } catch (err) {
      setError('取得資料失敗，請確認網路連線或稍後重試')
      setSheets([])
      setCalendarRows([])
    } finally {
      setLoading(false)
    }
  }, [queryMonth, calYear, calMonth])

  useEffect(() => { load() }, [load])

  return (
    <div>
      {/* ── 操作列 ──────────────────────────────────────────────────────────── */}
      <Row gutter={12} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space>
            <CalendarOutlined style={{ color: '#1B3A5C' }} />
            <Text strong>查詢月份：</Text>
            <DatePicker
              picker="month"
              value={dayjs(queryMonth, 'YYYY-MM')}
              onChange={(d) => d && handleMonthChange(d.format('YYYY-MM'))}
              format="YYYY/MM"
              allowClear={false}
            />
          </Space>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新載入
          </Button>
        </Col>
        <Col flex="auto" />
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {monthLabel}統計
          </Text>
        </Col>
      </Row>

      {/* ── 錯誤提示 ────────────────────────────────────────────────────────── */}
      {error && (
        <Alert
          type="error"
          message={error}
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setError(null)}
        />
      )}

      {/* ── KPI 卡片（暫時隱藏，待確認設計後恢復）─────────────────────────── */}

      {/* ── 月曆格（各 Sheet × 各日登錄狀態）──────────────────────────────── */}
      <Card
        size="small"
        loading={loading}
        title={
          <Space>
            <CalendarOutlined style={{ color: '#1B3A5C' }} />
            <span>{monthLabel} 每日抄表月曆</span>
          </Space>
        }
        style={{ marginBottom: 20 }}
      >
        {calendarRows.length > 0 ? (
          <MonthlyCalendarGrid
            year={calYear}
            month={calMonth}
            maxDay={maxDay}
            rows={calendarRows}
            rowHeaderLabel="抄表表單"
            legend={[
              { dot: '✓', color: '#52c41a', label: '已抄表', bg: '#f6ffed' },
              { dot: '—', color: '#ccc',    label: '無紀錄', bg: '#fff'    },
            ]}
            renderCell={(_day, data) => {
              if (data?.has_record) return '✓'
              return '—'
            }}
            cellStyle={(_day, data) => ({
              color:      data?.has_record ? '#52c41a' : '#bfbfbf',
              fontWeight: data?.has_record ? 700 : 400,
              fontSize:   data?.has_record ? 14 : 12,
            })}
          />
        ) : (
          !loading && (
            <div style={{ textAlign: 'center', color: '#bfbfbf', padding: '24px 0' }}>
              暫無資料
            </div>
          )
        )}
      </Card>

      {/* ── 各 Sheet 狀態卡片 ───────────────────────────────────────────────── */}
      <Row gutter={[16, 16]}>
        {sheets.map((sheet) => {
          const sheetCfg = HOTEL_METER_READINGS_SHEET_LIST.find((s) => s.key === sheet.key)
          const color = sheetCfg?.color ?? '#1B3A5C'

          return (
            <Col xs={24} sm={12} lg={6} key={sheet.key}>
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
                  sheet.ragic_url ? (
                    <Tooltip title="前往 Ragic 原始表單">
                      <a
                        href={sheet.ragic_url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: '#4BA8E8' }}
                      >
                        <LinkOutlined />
                      </a>
                    </Tooltip>
                  ) : null
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
                  最近登錄：{sheet.latest_record_date || '（無資料）'}
                </div>

                {sheet.missing_count > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <Text type="danger" style={{ fontSize: 11 }}>
                      缺漏：{(sheet.missing_days ?? []).slice(0, 5).join('、')}
                      {sheet.missing_count > 5 && ` 等 ${sheet.missing_count} 天`}
                    </Text>
                  </div>
                )}

                {/* 近 7 天趨勢點 */}
                <div style={{ marginTop: 8, display: 'flex', gap: 3, alignItems: 'center' }}>
                  {(sheet.trend_7d ?? []).map((t) => (
                    <Tooltip key={t.date} title={t.date}>
                      <div
                        style={{
                          width:           10,
                          height:          10,
                          borderRadius:    '50%',
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

      {!loading && sheets.length === 0 && !error && (
        <Alert
          type="info"
          message="尚無資料"
          description="請點擊「同步全部」從 Ragic 取得資料，或確認 Ragic 連線設定。"
          style={{ marginTop: 16 }}
        />
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 各 Sheet 資料列表 Tab（共用元件）
// ─────────────────────────────────────────────────────────────────────────────

function MeterListTab({ sheet }: { sheet: HotelMeterReadingsSheet }) {
  const [yearMonth, setYearMonth] = useState<string>(dayjs().format('YYYY/MM'))
  const [search,    setSearch]    = useState<string>('')
  const [loading,   setLoading]   = useState(false)
  const [rows,      setRows]      = useState<HotelMRBatchRow[]>([])
  const [error,     setError]     = useState<string | null>(null)
  const [lastSync,  setLastSync]  = useState<string>('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchHotelMeterBatches(sheet.key, {
        year_month: yearMonth,
        search: search || undefined,
      })
      setRows(data)
      if (data.length > 0) setLastSync(data[0].synced_at)
    } catch {
      setError('取得資料失敗，請確認網路連線或稍後再試')
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [sheet.key, yearMonth, search])

  useEffect(() => { load() }, [load])

  const columns = [
    {
      title: '抄表日期',
      dataIndex: 'record_date',
      key: 'record_date',
      width: 120,
      render: (v: string) => (
        <Text strong style={{ color: sheet.color }}>{v || '—'}</Text>
      ),
    },
    {
      title: '抄表人員',
      dataIndex: 'recorder_name',
      key: 'recorder_name',
      width: 120,
      render: (v: string) => v || <Text type="secondary">（未填）</Text>,
    },
    {
      title: '抄表時間起',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 100,
      align: 'center' as const,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '抄表時間迄',
      dataIndex: 'end_time',
      key: 'end_time',
      width: 100,
      align: 'center' as const,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '工時計算',
      dataIndex: 'work_hours',
      key: 'work_hours',
      width: 100,
      align: 'center' as const,
      render: (v: string) =>
        v ? <Tag color="blue">{v}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: '最後同步',
      dataIndex: 'synced_at',
      key: 'synced_at',
      width: 140,
      render: (v: string) => (
        <Text type="secondary" style={{ fontSize: 12 }}>{v || '—'}</Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, row: HotelMRBatchRow) => (
        row.ragic_url ? (
          <Tooltip title="前往 Ragic 查看原始資料">
            <Button
              type="link"
              size="small"
              icon={<LinkOutlined />}
              href={row.ragic_url}
              target="_blank"
            >
              Ragic
            </Button>
          </Tooltip>
        ) : null
      ),
    },
  ]

  return (
    <div>
      {/* ── 操作列 ──────────────────────────────────────────────────────────── */}
      <Row gutter={12} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <DatePicker
            picker="month"
            value={dayjs(yearMonth, 'YYYY/MM')}
            onChange={(d) => d && setYearMonth(d.format('YYYY/MM'))}
            format="YYYY/MM"
            allowClear={false}
          />
        </Col>
        <Col flex="200px">
          <Search
            placeholder="搜尋日期、抄表人員"
            value={search}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
            onSearch={load}
            allowClear
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新載入
          </Button>
        </Col>
        <Col flex="auto" />
        {lastSync && (
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>
              最近同步：{lastSync}
            </Text>
          </Col>
        )}
        <Col>
          <Tooltip title="前往 Ragic 原始表單">
            <Button
              size="small"
              type="link"
              icon={<LinkOutlined />}
              href={sheet.ragicUrl}
              target="_blank"
            >
              Ragic 表單
            </Button>
          </Tooltip>
        </Col>
      </Row>

      {/* ── 錯誤提示 ────────────────────────────────────────────────────────── */}
      {error && (
        <Alert
          type="error"
          message={error}
          style={{ marginBottom: 12 }}
          closable
          onClose={() => setError(null)}
        />
      )}

      {/* ── 資料表格 ────────────────────────────────────────────────────────── */}
      <Table
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        size="small"
        pagination={{ pageSize: 30, showSizeChanger: false, showTotal: (t) => `共 ${t} 筆` }}
        locale={{
          emptyText: (
            <div style={{ padding: '24px 0', color: '#64748b' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📊</div>
              <div>{yearMonth} 暫無登錄資料</div>
              <div style={{ fontSize: 12, marginTop: 4 }}>
                請點擊「從 Ragic 同步」取得最新資料
              </div>
            </div>
          ),
        }}
      />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 主頁面
// ─────────────────────────────────────────────────────────────────────────────

export default function HotelMeterReadingsDashboard() {
  const [searchParams, setSearchParams] = useSearchParams()

  const rawTab    = searchParams.get('tab') ?? ''
  const activeTab = VALID_TABS.includes(rawTab) ? rawTab : 'dashboard'

  const [openedTabs, setOpenedTabs] = useState<Set<string>>(new Set([activeTab]))

  const handleTabChange = (key: string) => {
    setOpenedTabs((prev) => new Set([...prev, key]))
    setSearchParams({ tab: key }, { replace: true })
  }

  const tabItems = [
    {
      key: 'dashboard',
      label: (
        <Space>
          <DashboardOutlined />
          Dashboard
        </Space>
      ),
      children: openedTabs.has('dashboard') ? <DashboardTab /> : null,
    },
    ...HOTEL_METER_READINGS_SHEET_LIST.map((sheet) => ({
      key: sheet.key,
      label: (
        <Space>
          <ReadOutlined />
          {sheet.title}
        </Space>
      ),
      children: openedTabs.has(sheet.key) ? <MeterListTab sheet={sheet} /> : null,
    })),
  ]

  return (
    <div style={{ padding: '0 4px' }}>
      {/* ── 麵包屑 ──────────────────────────────────────────────────────────── */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.hotel },
          { title: NAV_PAGE.hotelMeterReadings },
        ]}
      />

      {/* ── 頁面標題 ─────────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
          {NAV_PAGE.hotelMeterReadings}
        </Title>
        <Text type="secondary" style={{ fontSize: 13 }}>
          整合全棟水電錶、商場空調箱電錶、專櫃電錶、專櫃水錶每日數值登錄資料
        </Text>
      </div>

      {/* ── Tabs ──────────────────────────────────────────────────────────────── */}
      <Tabs
        type="card"
        activeKey={activeTab}
        onChange={handleTabChange}
        items={tabItems}
        style={{ background: '#fff', padding: '12px 16px', borderRadius: 8 }}
      />
    </div>
  )
}
