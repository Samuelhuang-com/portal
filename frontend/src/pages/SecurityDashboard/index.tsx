/**
 * 保全巡檢 統一入口頁
 *
 * 外層 TAB（8 個）：
 *   Tab 0「保全巡檢Dashboard」：一頁式綜合 Dashboard（無子 Tab）
 *   Tab 1-7：各巡檢 Sheet — 直接顯示巡檢紀錄清單（無主管儀表板）
 *
 * ── 2026-04-30 整合 ──────────────────────────────────────────────────────────
 * ── 2026-04-30 重構 ──────────────────────────────────────────────────────────
 * Dashboard 改為一頁式：KPI + 7 Sheet 狀態卡 + 今日統計表 + 異常清單 + 趨勢圖
 * 各 Sheet Tab 移除主管儀表板，直接顯示巡檢紀錄
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Tabs, Alert, DatePicker, Badge,
  message, Progress, Tooltip, Divider, Segmented,
} from 'antd'
import {
  HomeOutlined, SyncOutlined, ReloadOutlined,
  WarningOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, RightOutlined, CalendarOutlined, QuestionCircleOutlined,
  SafetyOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RcTooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchSecurityDashboardSummary,
  fetchSecurityDashboardIssues,
  fetchSecurityDashboardTrend,
  fetchSecurityDashboardMonthlySummary,
  fetchSecurityDashboardCalendar,
  fetchSecurityDashboardDailyForm,
  syncPatrolFromRagic,
  type SecurityMonthlySummary,
  type SecurityDailyFormRow,
} from '@/api/securityPatrol'
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'
import type {
  SecurityDashboardSummary,
  SecurityIssueItem,
  SecurityTrendPoint,
  SheetStats,
} from '@/types/securityPatrol'
import { NAV_GROUP } from '@/constants/navLabels'
import { SECURITY_KPI_DESC } from '@/constants/kpiDesc/securityDashboard'
import { SecurityPatrolContent } from '@/pages/SecurityPatrol'

// ── 每日巡檢表 Tab 元件 ───────────────────────────────────────────────────────

function SecurityDailyFormTab() {
  const today = dayjs()
  const [yearMonth, setYearMonth] = useState<string>(today.format('YYYY/MM'))
  const [loading,   setLoading]   = useState(false)
  const [syncing,   setSyncing]   = useState(false)
  const [rows,      setRows]      = useState<SecurityDailyFormRow[]>([])

  const load = useCallback(async (ym: string) => {
    setLoading(true)
    try {
      const [yr, mo] = ym.split('/').map(Number)
      const data = await fetchSecurityDashboardDailyForm(yr, mo)  // 不傳 inspection_date → 整月合併
      setRows(data.rows)
    } catch {
      message.error('載入每日巡檢表失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(yearMonth) }, [load, yearMonth])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncPatrolFromRagic()
      message.success('同步完成')
      await load(yearMonth)
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  const columns = [
    {
      title: '樓層',
      dataIndex: 'floor',
      width: 75,
      onCell: (r: SecurityDailyFormRow) => ({
        rowSpan: r.floor_first_row ? r.floor_row_count : 0,
        style: { fontWeight: 600, verticalAlign: 'middle', background: '#f0f4f8', textAlign: 'center' as const },
      }),
    },
    {
      title: '項目',
      dataIndex: 'item',
      width: 160,
      onCell: (r: SecurityDailyFormRow) => ({
        rowSpan: r.item_first_row ? r.item_row_count : 0,
        style: { verticalAlign: 'middle', fontWeight: 500 },
      }),
    },
    {
      title: '檢查內容',
      dataIndex: 'check_content',
      width: 240,
    },
    {
      title: '運轉狀況',
      dataIndex: 'result_options',
      width: 200,
      render: (_: string, r: SecurityDailyFormRow) => {
        if (!r.matched) return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        const color = r.result_status === 'normal' ? '#52C41A'
          : r.result_status === 'abnormal' ? '#FF4D4F'
          : r.result_status === 'pending'  ? '#FAAD14' : undefined
        return r.result_text
          ? <Tag color={color}>{r.result_text}</Tag>
          : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
      },
    },
    {
      title: '實際巡檢人員',
      dataIndex: 'inspector',
      width: 110,
      render: (v: string) => v || <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title: '異常說明',
      dataIndex: 'abnormal_note',
      render: (v: string) => v
        ? <Text type="danger" style={{ fontSize: 11, whiteSpace: 'pre-wrap' }}>{v}</Text>
        : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
  ]

  const hasData = rows.some((r) => r.matched)
  const monthLabel = dayjs(yearMonth, 'YYYY/MM').format('YYYY年M月')

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <Space>
            <Text strong>查詢月份：</Text>
            <DatePicker
              picker="month"
              value={dayjs(yearMonth, 'YYYY/MM')}
              format="YYYY/MM"
              allowClear={false}
              onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
            />
          </Space>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={() => load(yearMonth)} loading={loading}>
            重新整理
          </Button>
        </Col>
        <Col>
          <Button icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={handleSync}>
            同步 Ragic
          </Button>
        </Col>
      </Row>

      {!loading && !hasData && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message={`${monthLabel} 尚無巡檢資料`}
          description="請確認已執行同步，或切換至有資料的月份。"
        />
      )}

      <Table<SecurityDailyFormRow>
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
    </div>
  )
}

// ── 外層 TAB 定義 ─────────────────────────────────────────────────────────────
const OUTER_TABS = [
  { key: 'dashboard',  label: '保全巡檢Dashboard', icon: <DashboardOutlined /> },
  { key: 'daily-form', label: '每日巡檢表',         icon: <CalendarOutlined /> },
  { key: 'b1f-b4f',   label: 'B1F~B4F夜間巡檢',  icon: <SafetyOutlined /> },
  { key: '1f-3f',    label: '1F~3F夜間巡檢',     icon: <SafetyOutlined /> },
  { key: '5f-10f',   label: '5F~10F夜間巡檢',    icon: <SafetyOutlined /> },
  { key: '4f',       label: '4F夜間巡檢',         icon: <SafetyOutlined /> },
  { key: '1f-hotel', label: '1F飯店大廳',         icon: <SafetyOutlined /> },
  { key: '1f-close', label: '1F閉店巡檢',         icon: <SafetyOutlined /> },
  { key: '1f-open',  label: '1F開店準備',         icon: <SafetyOutlined /> },
] as const

const { Title, Text } = Typography

// ── 狀態 Tag 顏色 ──────────────────────────────────────────────────────────────
const STATUS_TAG: Record<string, string> = {
  abnormal:  'error',
  pending:   'warning',
  unchecked: 'default',
}

// ── Sheet 狀態 mini-card 顏色 ──────────────────────────────────────────────────
function sheetCardBorder(sheet: SheetStats): string {
  if (!sheet.has_data) return '#d9d9d9'
  if (sheet.abnormal_items > 0) return '#ff4d4f'
  if (sheet.pending_items > 0)  return '#faad14'
  if (sheet.completion_rate >= 100) return '#52c41a'
  return '#4BA8E8'
}

export default function SecurityDashboardPage() {
  const navigate = useNavigate()

  const [outerTab,     setOuterTab]     = useState('dashboard')
  const [viewMode,     setViewMode]     = useState<'day' | 'month'>('day')
  const [targetDate,   setTargetDate]   = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [yearMonth,    setYearMonth]    = useState<string>(dayjs().format('YYYY/MM'))
  const [summary,      setSummary]      = useState<SecurityDashboardSummary | null>(null)
  const [monthlyData,  setMonthlyData]  = useState<SecurityMonthlySummary | null>(null)
  const [issues,       setIssues]       = useState<SecurityIssueItem[]>([])
  const [trend,        setTrend]        = useState<SecurityTrendPoint[]>([])
  const [loading,      setLoading]      = useState(false)
  const [syncing,      setSyncing]      = useState(false)
  const [calRows,      setCalRows]      = useState<CalendarRow[]>([])
  const [calMaxDay,    setCalMaxDay]    = useState(31)

  // 並行載入資料（依篩選模式）
  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      if (viewMode === 'day') {
        const [dy, dm] = targetDate.split('/').map(Number)
        const [sumData, issueData, trendData, calData] = await Promise.all([
          fetchSecurityDashboardSummary(targetDate),
          fetchSecurityDashboardIssues({ start_date: targetDate, end_date: targetDate }),
          fetchSecurityDashboardTrend(7),
          fetchSecurityDashboardCalendar(dy, dm).catch(() => null),
        ])
        setSummary(sumData)
        setMonthlyData(null)
        setIssues(issueData.items)
        setTrend(trendData.trend)
        if (calData) { setCalMaxDay(calData.max_day); setCalRows(calData.rows) }
      } else {
        const [y, m] = yearMonth.split('/').map(Number)
        const firstDay = `${yearMonth}/01`
        const lastDay  = dayjs(yearMonth, 'YYYY/MM').endOf('month').format('YYYY/MM/DD')
        const [monthData, issueData, calData] = await Promise.all([
          fetchSecurityDashboardMonthlySummary(y, m),
          fetchSecurityDashboardIssues({ start_date: firstDay, end_date: lastDay }),
          fetchSecurityDashboardCalendar(y, m).catch(() => null),
        ])
        setMonthlyData(monthData)
        setSummary(null)
        setIssues(issueData.items)
        setTrend([])
        if (calData) { setCalMaxDay(calData.max_day); setCalRows(calData.rows) }
      }
    } catch {
      message.error('載入 Dashboard 失敗')
    } finally {
      setLoading(false)
    }
  }, [viewMode, targetDate, yearMonth])

  useEffect(() => { loadAll() }, [loadAll])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await syncPatrolFromRagic()
      message.success('全部 Sheet 同步完成')
      await loadAll()
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // ── Derived display values（單日 or 全月 皆適用）────────────────────────
  const modeLabel = viewMode === 'month' ? '本月' : '今日'

  const displaySheets: SheetStats[] = viewMode === 'day'
    ? (summary?.sheets ?? [])
    : (monthlyData?.sheets ?? []).map((s) => ({
        sheet_key:       s.sheet_key,
        sheet_name:      s.sheet_name,
        total_batches:   s.total_batches,
        total_items:     s.total_items,
        checked_items:   s.checked_items,
        unchecked_items: s.unchecked_items,
        abnormal_items:  s.abnormal_items,
        pending_items:   0,   // 月份彙總已合併至 abnormal_items
        completion_rate: s.completion_rate,
        normal_rate:     0,
        has_data:        s.has_data,
      }))

  const displayTotalBatches   = viewMode === 'day'
    ? (summary?.total_batches_all ?? 0)
    : displaySheets.reduce((acc, s) => acc + s.total_batches, 0)
  const displayCheckedItems   = viewMode === 'day'
    ? (summary?.checked_items_all ?? 0)
    : (monthlyData?.checked_items ?? 0)
  const displayTotalItems     = viewMode === 'day'
    ? (summary?.total_items_all ?? 0)
    : (monthlyData?.total_items ?? 0)
  const displayAbnormalItems  = viewMode === 'day'
    ? (summary?.abnormal_items_all ?? 0)
    : (monthlyData?.abnormal_items ?? 0)
  const displayCompletionRate = viewMode === 'day'
    ? (summary?.completion_rate_all ?? 0)
    : (monthlyData?.completion_rate ?? 0)

  // ── Section 1：全局 KPI 卡片 ──────────────────────────────────────────────
  const kpiCards = [
    {
      title: `${modeLabel}巡檢場次`,
      descKey: '今日巡檢場次',
      value: displayTotalBatches,
      color: '#1B3A5C',
      icon: <DashboardOutlined />,
    },
    {
      title: '已巡檢項目',
      descKey: '已巡檢項目',
      value: displayCheckedItems,
      suffix: `/${displayTotalItems}`,
      color: '#4BA8E8',
      icon: <CheckCircleOutlined />,
    },
    {
      title: '異常 + 待處理',
      descKey: '異常待處理',
      value: displayAbnormalItems,
      color: '#FF4D4F',
      icon: <WarningOutlined />,
    },
    {
      title: '整體完成率',
      descKey: '整體完成率',
      value: displayCompletionRate,
      suffix: '%',
      color: displayCompletionRate >= 80 ? '#52C41A' : '#FAAD14',
      icon: <ExclamationCircleOutlined />,
    },
  ]

  // ── Section 2：7 Sheet 狀態 mini-cards ───────────────────────────────────
  const sheets = displaySheets

  // ── Section 3：各 Sheet 今日統計表（左欄）────────────────────────────────
  const sheetCols: ColumnsType<SheetStats> = [
    {
      title: '巡檢表',
      dataIndex: 'sheet_name',
      ellipsis: true,
      render: (v, row) => (
        <Button type="link" style={{ padding: 0, textAlign: 'left', fontSize: 12 }}
          onClick={() => setOuterTab(row.sheet_key)}>
          {v}
        </Button>
      ),
    },
    {
      title: '場次',
      dataIndex: 'total_batches',
      width: 52,
      align: 'center',
      render: (v) => v > 0
        ? <Badge count={v} color="#1B3A5C" showZero />
        : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title: '完成率',
      dataIndex: 'completion_rate',
      width: 120,
      render: (v, row) => row.has_data
        ? <Progress percent={v} size="small"
            strokeColor={{ from: v < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
            format={(p) => `${p}%`} />
        : <Text type="secondary" style={{ fontSize: 11 }}>無資料</Text>,
    },
    {
      title: '異常',
      dataIndex: 'abnormal_items',
      width: 52,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FF4D4F" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '待處理',
      dataIndex: 'pending_items',
      width: 58,
      align: 'center',
      render: (v) => v > 0 ? <Badge count={v} color="#FAAD14" /> : <Text type="secondary">—</Text>,
    },
    {
      title: '',
      width: 60,
      render: (_, row) => (
        <Button size="small" icon={<RightOutlined />}
          onClick={() => setOuterTab(row.sheet_key)}>
          前往
        </Button>
      ),
    },
  ]

  // ── Section 4：今日異常 & 待處理清單（右欄）──────────────────────────────
  const issueColsCompact: ColumnsType<SecurityIssueItem> = [
    {
      title: '巡檢點',
      dataIndex: 'item_name',
      ellipsis: true,
      render: (v, row) => (
        <span>
          <Tag color={STATUS_TAG[row.status] ?? 'default'} style={{ fontSize: 10, padding: '0 4px' }}>
            {row.status_label}
          </Tag>
          <span style={{ fontSize: 12 }}>{v}</span>
        </span>
      ),
    },
    {
      title: '表單',
      dataIndex: 'sheet_name',
      width: 100,
      ellipsis: true,
      render: (v, row) => (
        <Button type="link" size="small" style={{ padding: 0, fontSize: 11 }}
          onClick={() => navigate(`/security/patrol/${row.sheet_key}/${row.batch_id}`, { state: { returnPath: '/security/dashboard' } })}>
          {v}
        </Button>
      ),
    },
  ]

  // ── Section 5：近 7 日趨勢圖 ─────────────────────────────────────────────
  const trendChartData = trend.map(t => ({
    date:   t.date.slice(5),
    異常數量: t.abnormal_count,
    場次數:  t.total_batches,
  }))

  // ── Dashboard 主體 ────────────────────────────────────────────────────────
  const DashboardContent = (
    <div>
      {/* Header 工具列 */}
      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }} gutter={8}>
        <Col>
          <Space size={8} wrap>
            <Segmented
              size="small"
              value={viewMode}
              onChange={(v) => setViewMode(v as 'day' | 'month')}
              options={[
                { label: '單日', value: 'day' },
                { label: '全月', value: 'month' },
              ]}
            />
            <Text strong style={{ fontSize: 13 }}>
              查詢{viewMode === 'month' ? '月份' : '日期'}：
            </Text>
            {viewMode === 'day' ? (
              <DatePicker
                value={dayjs(targetDate, 'YYYY/MM/DD')}
                format="YYYY/MM/DD"
                allowClear={false}
                size="small"
                onChange={(d) => { if (d) setTargetDate(d.format('YYYY/MM/DD')) }}
              />
            ) : (
              <DatePicker
                picker="month"
                value={dayjs(yearMonth, 'YYYY/MM')}
                format="YYYY/MM"
                allowClear={false}
                size="small"
                onChange={(d) => { if (d) setYearMonth(d.format('YYYY/MM')) }}
              />
            )}
            <Button size="small" icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>
              重新整理
            </Button>
          </Space>
        </Col>
        <Col>
          <Space size={8}>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {viewMode === 'day' && summary?.generated_at ? `更新：${summary.generated_at}` : ''}
            </Text>
            <Button size="small" icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={handleSync}>
              同步全部 Sheet
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Section 1：全局 KPI */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {kpiCards.map(card => (
          <Col xs={12} sm={12} lg={6} key={card.title}>
            <Card size="small" hoverable>
              <Statistic
                title={
                  <span style={{ fontSize: 12 }}>
                    {card.title}
                    <Tooltip title={SECURITY_KPI_DESC[card.descKey]} placement="top">
                      <QuestionCircleOutlined style={{ color: '#bbb', fontSize: 10, marginLeft: 4, cursor: 'help' }} />
                    </Tooltip>
                  </span>
                }
                value={card.value}
                suffix={card.suffix}
                prefix={<span style={{ color: card.color }}>{card.icon}</span>}
                valueStyle={{ color: card.color, fontSize: 24 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Section 2：7 Sheet 狀態 mini-cards */}
      <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
        {sheets.length === 0
          ? Array(7).fill(null).map((_, i) => (
              <Col xs={12} sm={8} lg={24 / 7} key={i}>
                <Card size="small" loading style={{ borderRadius: 6 }} />
              </Col>
            ))
          : sheets.map(sheet => (
              <Col xs={12} sm={8} lg={Math.floor(24 / 7)} key={sheet.sheet_key}
                style={{ minWidth: 120 }}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => setOuterTab(sheet.sheet_key)}
                  style={{
                    borderRadius: 6,
                    borderLeft: `3px solid ${sheetCardBorder(sheet)}`,
                    cursor: 'pointer',
                    height: '100%',
                  }}
                  bodyStyle={{ padding: '8px 10px' }}
                >
                  <Text strong style={{ fontSize: 11, display: 'block', marginBottom: 4, lineHeight: 1.3 }}>
                    {sheet.sheet_name.replace('保全巡檢 - ', '').replace('保全每日巡檢 - ', '')}
                  </Text>
                  {sheet.has_data ? (
                    <>
                      <Progress
                        percent={sheet.completion_rate} size="small"
                        strokeColor={{ from: sheet.completion_rate < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
                        format={(p) => `${p}%`}
                        style={{ marginBottom: 4 }}
                      />
                      <Space size={4}>
                        {sheet.abnormal_items > 0 && (
                          <Badge count={sheet.abnormal_items} color="#FF4D4F"
                            title={`異常 ${sheet.abnormal_items} 項`} />
                        )}
                        {sheet.pending_items > 0 && (
                          <Badge count={sheet.pending_items} color="#FAAD14"
                            title={`待處理 ${sheet.pending_items} 項`} />
                        )}
                        {sheet.abnormal_items === 0 && sheet.pending_items === 0 && (
                          <Tag color="success" style={{ fontSize: 10, padding: '0 4px', margin: 0 }}>正常</Tag>
                        )}
                      </Space>
                    </>
                  ) : (
                    <Text type="secondary" style={{ fontSize: 11 }}>{modeLabel}無資料</Text>
                  )}
                </Card>
              </Col>
            ))}
      </Row>

      {/* Section 3 + 4：統計表（左） + 異常清單（右） */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={14}>
          <Card
            title={<><CalendarOutlined /> 各巡檢 Sheet {modeLabel}統計</>}
            size="small"
            style={{ height: '100%' }}
          >
            <Table<SheetStats>
              dataSource={sheets}
              rowKey="sheet_key"
              columns={sheetCols}
              loading={loading}
              size="small"
              pagination={false}
              locale={{ emptyText: '尚無資料' }}
            />
            {!loading && displayTotalItems === 0 && (
              <Alert
                style={{ marginTop: 8 }}
                type="info"
                message={
                  viewMode === 'month'
                    ? `${yearMonth} 整月尚無任何保全巡檢記錄，請確認資料是否已同步。`
                    : `${targetDate} 尚無任何保全巡檢記錄，請確認巡檢是否已執行並同步。`
                }
                showIcon
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card
            title={
              <Space>
                <WarningOutlined style={{ color: '#FF4D4F' }} />
                <span>{modeLabel}異常 {'&'} 待處理</span>
                {issues.length > 0 && <Badge count={issues.length} color="#FF4D4F" />}
              </Space>
            }
            size="small"
            style={{ height: '100%' }}
          >
            {loading ? (
              <div style={{ padding: '20px 0', textAlign: 'center', color: '#999' }}>載入中…</div>
            ) : issues.length === 0 ? (
              <Alert message={`${modeLabel}無異常記錄`} type="success" showIcon />
            ) : (
              <Table<SecurityIssueItem>
                dataSource={issues}
                rowKey="id"
                columns={issueColsCompact}
                size="small"
                pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆`, size: 'small' }}
                locale={{ emptyText: '無異常' }}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* Section 5：近 7 日趨勢圖（僅單日模式顯示） */}
      {viewMode === 'day' && <Card
        title={
          <Space>
            <ClockCircleOutlined style={{ color: '#4BA8E8' }} />
            <span>近 7 日巡檢趨勢</span>
            <Text type="secondary" style={{ fontSize: 11, fontWeight: 400 }}>（場次數 + 異常數量）</Text>
          </Space>
        }
        size="small"
      >
        {trendChartData.some(t => t.場次數 > 0) ? (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={trendChartData} margin={{ left: 0, right: 20, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <RcTooltip />
              <Legend />
              <Bar dataKey="場次數"  fill="#4BA8E8" radius={[3, 3, 0, 0]} />
              <Bar dataKey="異常數量" fill="#FF4D4F" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div style={{ textAlign: 'center', padding: '50px 0', color: '#999' }}>
            暫無趨勢資料（請先確認資料已同步）
          </div>
        )}
      </Card>}

      {/* 月曆格：各巡檢表 × 當月出勤狀況 */}
      {(() => {
        const calYear  = viewMode === 'month'
          ? parseInt(yearMonth.split('/')[0])
          : parseInt(targetDate.split('/')[0])
        const calMonth = viewMode === 'month'
          ? parseInt(yearMonth.split('/')[1])
          : parseInt(targetDate.split('/')[1])
        return (
          <Card
            size="small"
            style={{ marginTop: 16 }}
            title={
              <Space>
                <CalendarOutlined />
                <Text strong>保全巡檢月曆格</Text>
                <Text type="secondary" style={{ fontSize: 11, fontWeight: 400 }}>
                  （{calYear}/{String(calMonth).padStart(2, '0')} 各表逐日出勤）
                </Text>
              </Space>
            }
            loading={loading}
          >
            {calRows.length > 0 ? (
              <MonthlyCalendarGrid
                year={calYear}
                month={calMonth}
                maxDay={calMaxDay}
                rows={calRows}
                rowHeaderLabel="巡檢表"
              />
            ) : (
              <Text type="secondary">尚無月曆資料</Text>
            )}
          </Card>
        )
      })()}
    </div>
  )

  // ── 頁面渲染 ──────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 4px' }}>
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.security },
        ]}
      />

      <Row align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
            <SafetyOutlined /> {NAV_GROUP.security}
          </Title>
        </Col>
      </Row>

      {/* 外層 TAB */}
      <Tabs
        activeKey={outerTab}
        onChange={setOuterTab}
        type="card"
        style={{ marginBottom: 0 }}
        items={OUTER_TABS.map((tab) => ({
          key: tab.key,
          label: (
            <span>
              {tab.icon}
              <span style={{ marginLeft: 6 }}>{tab.label}</span>
            </span>
          ),
          children: tab.key === 'dashboard'
            ? DashboardContent
            : tab.key === 'daily-form'
              ? <SecurityDailyFormTab />
              : <SecurityPatrolContent key={tab.key} sheetKey={tab.key} returnPath="/security/dashboard" />,
        }))}
      />
    </div>
  )
}
