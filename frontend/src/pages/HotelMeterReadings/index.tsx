/**
 * 每日數值登錄表 — 統一整合頁面（掛於飯店管理群組）
 *
 * 將 4 個 Ragic Sheet 整合為 Tabs：
 *   Tab 1  Dashboard      — 今日登錄狀態 + 缺漏統計 + 本月趨勢
 *   Tab 2  全棟電錶        — 月份篩選 + 登錄清單
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
  message, Badge, Input, Tooltip,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined,
  DashboardOutlined, ReadOutlined, LinkOutlined,
  ExclamationCircleOutlined,
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
  syncHotelMeterAllFromRagic,
  syncHotelMeterFromRagic,
  type HotelMRSheetSummary,
  type HotelMRBatchRow,
} from '@/api/hotelMeterReadings'

const { Title, Text } = Typography
const { Search } = Input

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Tab — 跨 Sheet 今日登錄狀態 + 缺漏統計
// ─────────────────────────────────────────────────────────────────────────────

function DashboardTab() {
  const [targetDate, setTargetDate] = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [loading,    setLoading]    = useState(false)
  const [syncing,    setSyncing]    = useState(false)
  const [sheets,     setSheets]     = useState<HotelMRSheetSummary[]>([])
  const [error,      setError]      = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchHotelMeterDashboardSummary(targetDate)
      setSheets(data.sheets)
    } catch (err) {
      setError('取得統計資料失敗，請檢查網路或稍後重試')
      setSheets([])
    } finally {
      setLoading(false)
    }
  }, [targetDate])

  useEffect(() => { load() }, [load])

  const handleSyncAll = async () => {
    setSyncing(true)
    try {
      await syncHotelMeterAllFromRagic()
      message.success('全部 4 張 Sheet 同步已在背景啟動，約 1 分鐘後可重新載入查看')
    } catch {
      message.error('同步失敗，請稍後再試')
    } finally {
      setSyncing(false)
    }
  }

  // 統計數字
  const totalLogged  = sheets.filter((s) => s.has_today).length
  const totalMissing = sheets.reduce((acc, s) => acc + s.missing_count, 0)
  const hasAllToday  = sheets.length > 0 && totalLogged === sheets.length

  return (
    <div>
      {/* ── 操作列 ────────────────────────────────────────────────────────── */}
      <Row gutter={12} align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <DatePicker
            value={dayjs(targetDate, 'YYYY/MM/DD')}
            onChange={(d) => d && setTargetDate(d.format('YYYY/MM/DD'))}
            format="YYYY/MM/DD"
            allowClear={false}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新載入
          </Button>
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<SyncOutlined />}
            onClick={handleSyncAll}
            loading={syncing}
          >
            同步全部
          </Button>
        </Col>
        <Col flex="auto" />
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>
            查詢日期：{targetDate}
          </Text>
        </Col>
      </Row>

      {/* ── 錯誤提示 ──────────────────────────────────────────────────────── */}
      {error && (
        <Alert
          type="error"
          message={error}
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setError(null)}
        />
      )}

      {/* ── KPI 卡片 ──────────────────────────────────────────────────────── */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="今日已登錄"
              value={totalLogged}
              suffix={`/ ${sheets.length} 張表`}
              valueStyle={{ color: hasAllToday ? '#52c41a' : '#faad14' }}
              prefix={hasAllToday ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="本月累計缺漏天數"
              value={totalMissing}
              suffix="天"
              valueStyle={{ color: totalMissing > 0 ? '#ff4d4f' : '#52c41a' }}
              prefix={totalMissing > 0 ? <WarningOutlined /> : <CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="本月讀數欄位總數"
              value={sheets.reduce((acc, s) => acc + s.total_readings, 0)}
              suffix="筆"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" loading={loading}>
            <Statistic
              title="監控表單數"
              value={sheets.length}
              suffix="張"
            />
          </Card>
        </Col>
      </Row>

      {/* ── 各 Sheet 狀態卡片 ─────────────────────────────────────────────── */}
      <Row gutter={[16, 16]}>
        {sheets.map((sheet) => {
          const sheetCfg = HOTEL_METER_READINGS_SHEET_LIST.find((s) => s.key === sheet.key)
          const color = sheetCfg?.color ?? '#1B3A5C'

          return (
            <Col xs={24} sm={12} md={12} lg={6} key={sheet.key}>
              <Card
                size="small"
                loading={loading}
                title={
                  <Space>
                    <span style={{ color }}>{sheet.title}</span>
                    {sheet.has_today
                      ? <Tag color="success">今日已登錄</Tag>
                      : <Tag color="warning">今日未登錄</Tag>}
                  </Space>
                }
                extra={
                  <Tooltip title="前往 Ragic 原始表單">
                    <a href={sheet.ragic_url} target="_blank" rel="noreferrer">
                      <LinkOutlined />
                    </a>
                  </Tooltip>
                }
              >
                <Row gutter={8}>
                  <Col span={12}>
                    <Statistic
                      title="本月登錄"
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
                  最近登錄：{sheet.latest_record_date || '（無資料）'}
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
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
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

      {/* ── 空資料提示 ────────────────────────────────────────────────────── */}
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
  const [syncing,   setSyncing]   = useState(false)
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

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncHotelMeterFromRagic(sheet.key)
      message.success(`${sheet.title} 同步已在背景啟動，約 1 分鐘後可重新載入`)
    } catch {
      message.error('同步失敗，請稍後再試')
    } finally {
      setSyncing(false)
    }
  }

  const columns = [
    {
      title: '登錄日期',
      dataIndex: 'record_date',
      key: 'record_date',
      width: 120,
      render: (v: string) => (
        <Text strong style={{ color: sheet.color }}>{v || '—'}</Text>
      ),
    },
    {
      title: '登錄人員',
      dataIndex: 'recorder_name',
      key: 'recorder_name',
      width: 120,
      render: (v: string) => v || <Text type="secondary">（未填）</Text>,
    },
    {
      title: '讀數筆數',
      dataIndex: 'readings_count',
      key: 'readings_count',
      width: 100,
      align: 'center' as const,
      render: (v: number) => (
        <Badge count={v} showZero style={{ backgroundColor: v > 0 ? sheet.color : '#d9d9d9' }} />
      ),
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
      width: 100,
      render: (_: unknown, row: HotelMRBatchRow) => (
        <Space>
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
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* ── 操作列 ────────────────────────────────────────────────────────── */}
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
            placeholder="搜尋日期、登錄人員"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onSearch={load}
            allowClear
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            重新載入
          </Button>
        </Col>
        <Col>
          <Button
            icon={<SyncOutlined />}
            onClick={handleSync}
            loading={syncing}
          >
            從 Ragic 同步
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

      {/* ── 錯誤提示 ──────────────────────────────────────────────────────── */}
      {error && (
        <Alert
          type="error"
          message={error}
          style={{ marginBottom: 12 }}
          closable
          onClose={() => setError(null)}
        />
      )}

      {/* ── 資料表格 ──────────────────────────────────────────────────────── */}
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

  // URL ?tab= 決定初始 Tab，若不合法則預設 dashboard
  const rawTab    = searchParams.get('tab') ?? ''
  const activeTab = VALID_TABS.includes(rawTab) ? rawTab : 'dashboard'

  // 懶載入：記錄已開啟過的 Tab（避免重複 fetch）
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
      {/* ── 麵包屑 ──────────────────────────────────────────────────────── */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.hotel },
          { title: NAV_PAGE.hotelMeterReadings },
        ]}
      />

      {/* ── 頁面標題 ─────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
          {NAV_PAGE.hotelMeterReadings}
        </Title>
        <Text type="secondary" style={{ fontSize: 13 }}>
          整合全棟電錶、商場空調箱電錶、專櫃電錶、專櫃水錶每日數值登錄資料
        </Text>
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────────────── */}
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
