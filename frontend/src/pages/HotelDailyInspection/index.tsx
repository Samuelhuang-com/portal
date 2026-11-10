/**
 * 飯店每日巡檢 — 統一整合頁面（掛於飯店管理群組）
 *
 * 2026-11-10 改版：照抄 pages/MallFacilityInspection/index.tsx（Samuel 裁示：完全照商場模組的程式與架構）。
 * Ragic：main-project-inspection/17、28～33（新表）＋ archive-old-data/31～40（舊表，掛在最接近的新頁籤）。
 *   Tab Dashboard   — 月份統計 + 月曆格（點格子開每日巡檢表 Drawer，共用 MallFIDailySheetDrawer）
 *   Tab 樓層巡檢圖  — 共用元件 FloorMapWorkspace（module=hotel_daily_inspection，CLAUDE.md §12）
 *   Tab ×7          — RF 樓層 早班巡檢／5-10F 客房公共區域／4F BAR-D公區／B1F 高壓機房／
 *                     B1F 晚班巡檢 辦公室公區 廚房瓦斯設備／B4F 早班巡檢 下水塔／B4F 晚班巡檢 空調機房
 * 「每日巡檢表」TAB 比照商場隱藏（每日巡檢表改由 Dashboard 月曆格 Drawer 呈現）。
 *
 * URL query param：?tab=summary|floor-map|rf|5f-10f|4f|b1f-hv|b1f-office|b4f-water|b4f-ac
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
  DashboardOutlined, ToolOutlined, ClockCircleOutlined, LinkOutlined,
  CalendarOutlined, EnvironmentOutlined, EditOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import {
  HOTEL_DAILY_INSPECTION_SHEETS,
  HOTEL_DAILY_INSPECTION_TAB_LABELS,
} from '@/constants/hotelDailyInspection'
import { useAuthStore } from '@/stores/authStore'
import {
  fetchHotelDailyMonthlyDashboard,
  fetchHotelDIDailyCalendar,
  fetchHotelDIDailySheet,
  fetchHotelDITabLabels,
  saveHotelDITabLabels,
  type HotelDIMonthlySheetSummary,
} from '@/api/hotelDailyInspection'
import TabLabelEditModal from './TabLabelEditModal'
import MonthlyCalendarGrid from '@/components/MonthlyCalendarGrid'
import type { CalendarRow } from '@/components/MonthlyCalendarGrid'
import { renderIssueCell } from '@/components/CalendarIssueCell'
// 每日巡檢表 Drawer 與商場、整棟巡檢共用同一個元件（回傳格式相同）
import MallFIDailySheetDrawer from '@/pages/MallFacilityInspection/MallFIDailySheetDrawer'
import HotelFloorInspectionList from './HotelFloorInspectionList'
import FloorMapWorkspace from '@/components/FloorPlanMap/FloorMapWorkspace'

const { Title, Text } = Typography

// Type definitions (SummaryTabContent 使用 HotelDIMonthlySheetSummary)

// 各頁籤：清單＋明細 Drawer 用 HotelFloorInspectionList（照抄 MallFloorInspectionList）

// Summary tab — 月份統計版

function SummaryTabContent() {
  const [searchParams, setSearchParams] = useSearchParams()

  const initMonth = searchParams.get('month') ?? dayjs().format('YYYY-MM')
  const [queryMonth, setQueryMonth] = useState<string>(initMonth)
  const [loading,    setLoading]    = useState(false)
  const [sheets,     setSheets]     = useState<HotelDIMonthlySheetSummary[]>([])
  const [error,      setError]      = useState<string | null>(null)
  const [calRows,    setCalRows]    = useState<CalendarRow[]>([])
  const [calMaxDay,  setCalMaxDay]  = useState(31)
  // 月曆格下一層：點「樓層 × 日」開啟該日每日巡檢表（Excel 版型）
  const [sheetDate,  setSheetDate]  = useState<string | null>(null)
  const [sheetFocus, setSheetFocus] = useState<string | null>(null)

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
        fetchHotelDailyMonthlyDashboard(queryMonth),
        fetchHotelDIDailyCalendar(yr, mo).catch(() => null),
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
          const sheetCfg = HOTEL_DAILY_INSPECTION_SHEETS[sheet.key]
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
            <Text strong>飯店每日巡檢狀況</Text>
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
            rowHeaderLabel="巡檢頁籤"
            renderCell={renderIssueCell}
            onCellClick={(day, rowKey) => {
              setSheetFocus(rowKey)
              setSheetDate(`${queryMonth}-${String(day).padStart(2, '0')}`)
            }}
          />
        ) : (
          <Text type="secondary">尚無月曆資料</Text>
        )}
        {calRows.length > 0 && (
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 4 }}>
            點選有紀錄的格子，可查看當日完整每日巡檢表；滑鼠移到 ⚠ 可直接看是哪幾項異常／待處理
          </Text>
        )}
      </Card>

      <MallFIDailySheetDrawer
        open={!!sheetDate}
        date={sheetDate}
        focusSheet={sheetFocus}
        onClose={() => { setSheetDate(null); setSheetFocus(null) }}
        onDateChange={(d) => { setSheetDate(d); setSheetFocus(null) }}
        fetchSheet={fetchHotelDIDailySheet}
        titleText="飯店每日巡檢"
      />

      {!loading && sheets.length === 0 && !error && (
        <Alert
          style={{ marginTop: 16 }}
          type="info"
          message={`${monthLabel}尚無任何飯店每日巡檢記錄，請確認巡檢是否已執行並同步。`}
          showIcon
        />
      )}
    </div>
  )
}

// Main component

// 舊書籤 ?tab=daily-form／4f-10f／2f／1f 會退回 summary，不會停在不存在的分頁
const TAB_KEYS   = ['rf', '5f-10f', '4f', 'b1f-hv', 'b1f-office', 'b4f-water', 'b4f-ac']
const VALID_TABS = ['summary', 'floor-map', ...TAB_KEYS]

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

  // ── 頁籤名稱（2026-11-10：有權限者可在頁面上直接修改，套用到整個頁面）──────
  const [tabLabels,    setTabLabels]    = useState<Record<string, string>>(HOTEL_DAILY_INSPECTION_TAB_LABELS)
  const [tabDefaults,  setTabDefaults]  = useState<Record<string, string>>(HOTEL_DAILY_INSPECTION_TAB_LABELS)
  const [editPerm,     setEditPerm]     = useState<string>('hotel_daily_inspection_tab_label_edit')
  const [labelEditing, setLabelEditing] = useState(false)
  const [labelVersion, setLabelVersion] = useState(0)   // 改名後重新掛載已開啟的頁籤，讓卡片／月曆格／Drawer 一起換
  const canEditLabels = useAuthStore((s) => s.hasPermission(editPerm))

  useEffect(() => {
    fetchHotelDITabLabels()
      .then((r) => { setTabLabels(r.labels); setTabDefaults(r.defaults); setEditPerm(r.edit_permission) })
      .catch(() => { /* 取不到就用預設名稱 */ })
  }, [])

  const handleSaveLabels = async (labels: Record<string, string | null>) => {
    const r = await saveHotelDITabLabels(labels)
    setTabLabels(r.labels)
    setLabelVersion((v) => v + 1)
    setLabelEditing(false)
    message.success('頁籤名稱已更新')
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
        key={labelVersion}
        type="card"
        activeKey={activeTab}
        onChange={handleTabChange}
        tabBarExtraContent={canEditLabels ? (
          <Button size="small" icon={<EditOutlined />} onClick={() => setLabelEditing(true)}>
            編輯頁籤名稱
          </Button>
        ) : null}
        items={[
          {
            key:      'summary',
            label:    'Dashboard',
            children: openedTabs.has('summary') ? <SummaryTabContent /> : null,
          },
          {
            key:      'floor-map',
            label:    <span><EnvironmentOutlined /> 樓層巡檢圖</span>,
            children: openedTabs.has('floor-map') ? <FloorMapWorkspace module="hotel_daily_inspection" /> : null,
          },
          ...TAB_KEYS.map((k) => ({
            key:      k,
            label:    tabLabels[k] ?? HOTEL_DAILY_INSPECTION_TAB_LABELS[k],
            children: openedTabs.has(k) ? <HotelFloorInspectionList sheetKey={k} tabLabel={tabLabels[k]} /> : null,
          })),
        ]}
      />

      <TabLabelEditModal
        open={labelEditing}
        order={TAB_KEYS}
        labels={tabLabels}
        defaults={tabDefaults}
        onCancel={() => setLabelEditing(false)}
        onSave={handleSaveLabels}
      />
    </div>
  )
}
