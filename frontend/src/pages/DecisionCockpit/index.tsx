/**
 * 決策駕駛艙 — Decision Cockpit
 * route: /decision-cockpit
 *
 * 高階主管決策入口，整合 dashboard、hotel/overview、mall/overview 三大模組精華。
 *
 * 設計原則：
 *  - 完全沿用既有後端 API，不新增後端端點
 *  - 不使用 AI API，所有摘要均為規則式計算
 *  - 資料未接入者顯示「資料準備中」（灰燈），不使用假資料
 *  - 各 TAB 懶載入，避免首屏呼叫過多 API
 *
 * TAB 架構：
 *  A. 決策總覽     — 健康分數 + KPI + 主管最該注意的 5 件事
 *  B. 飯店管理摘要 — 六來源精華（Phase 3）
 *  C. 商場管理摘要 — 五工項精華（Phase 3）
 *  D. 工務與報修   — 大直 + 樂群（Phase 4）
 *  E. 人員工時     — 飯店 + 商場 Top 排行（Phase 4）
 *  F. 異常風險雷達 — 紅/黃/綠/灰燈（Phase 5）
 *  G. 趨勢分析     — 日度 + 月度折線（Phase 5）
 *  H. 主管晨會摘要 — 規則式文字模板（Phase 6）
 *  I. 資料品質監控 — 欄位完整度（Phase 6）
 */
import { useState, useCallback, lazy, Suspense } from 'react'
import {
  Breadcrumb,
  Button,
  Card,
  Select,
  Space,
  Tabs,
  Spin,
  Typography,
  Tooltip,
} from 'antd'
import {
  HomeOutlined,
  RadarChartOutlined,
  ReloadOutlined,
  ExportOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography
const { Option } = Select

// ── Portal 設計 Token（依 PROTECTED.md）─────────────────────────────────────
const T = {
  primary:    '#1B3A5C',
  accent:     '#4BA8E8',
  bg:         '#f0f4f8',
  success:    '#52c41a',
  danger:     '#ff4d4f',
  warning:    '#faad14',
  textMuted:  '#8c8c8c',
  cardBg:     '#ffffff',
}

// ── 各 TAB 懶載入（Phase 2+ 才建立實際元件）─────────────────────────────────
const TabOverview     = lazy(() => import('./tabs/TabOverview'))
const TabHotel        = lazy(() => import('./tabs/TabHotel'))
const TabMall         = lazy(() => import('./tabs/TabMall'))
const TabRepair       = lazy(() => import('./tabs/TabRepair'))
const TabPersonnel    = lazy(() => import('./tabs/TabPersonnel'))
const TabRiskRadar    = lazy(() => import('./tabs/TabRiskRadar'))
const TabTrend        = lazy(() => import('./tabs/TabTrend'))
const TabBriefing     = lazy(() => import('./tabs/TabBriefing'))
const TabDataQuality  = lazy(() => import('./tabs/TabDataQuality'))

// ── 月份選項（近 24 個月）───────────────────────────────────────────────────
function buildMonthOptions() {
  const opts: { label: string; value: string; year: number; month: number }[] = []
  const now = dayjs()
  for (let i = 0; i < 24; i++) {
    const d = now.subtract(i, 'month')
    const y = d.year()
    const m = d.month() + 1
    opts.push({
      label: `${y} 年 ${String(m).padStart(2, '0')} 月`,
      value: `${y}-${String(m).padStart(2, '0')}`,
      year:  y,
      month: m,
    })
  }
  return opts
}

const MONTH_OPTIONS = buildMonthOptions()

// ── 載入中 Fallback ──────────────────────────────────────────────────────────
function TabLoading() {
  return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <Spin size="large" />
      <div style={{ marginTop: 16, color: T.textMuted }}>載入資料中...</div>
    </div>
  )
}

// ── 未開發 TAB 佔位元件 ──────────────────────────────────────────────────────
function ComingSoon({ tabName }: { tabName: string }) {
  return (
    <Card style={{ margin: '24px 0', background: T.bg, border: 'none' }}>
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <RadarChartOutlined style={{ fontSize: 48, color: T.accent, marginBottom: 16 }} />
        <div style={{ fontSize: 18, fontWeight: 600, color: T.primary, marginBottom: 8 }}>
          {tabName} — 開發中
        </div>
        <div style={{ color: T.textMuted, fontSize: 14 }}>
          此 TAB 將於後續 Phase 實作，資料將直接沿用既有 API。
        </div>
      </div>
    </Card>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// 主元件
// ════════════════════════════════════════════════════════════════════════════
export default function DecisionCockpitPage() {
  // ── 查詢月份狀態 ──────────────────────────────────────────────────────────
  const nowOpt = MONTH_OPTIONS[0]
  const [selectedMonth, setSelectedMonth] = useState<string>(nowOpt.value)
  const [selectedYear,  setSelectedYear]  = useState<number>(nowOpt.year)
  const [selectedMonthNum, setSelectedMonthNum] = useState<number>(nowOpt.month)
  const [refreshKey,    setRefreshKey]    = useState<number>(0)
  const [activeTab,     setActiveTab]     = useState<string>('overview')

  const handleMonthChange = useCallback((val: string) => {
    const opt = MONTH_OPTIONS.find(o => o.value === val)
    if (!opt) return
    setSelectedMonth(val)
    setSelectedYear(opt.year)
    setSelectedMonthNum(opt.month)
  }, [])

  const handleRefresh = useCallback(() => {
    setRefreshKey(k => k + 1)
  }, [])

  // ── 共用 props（傳入各 TAB）──────────────────────────────────────────────
  const tabProps = {
    year:       selectedYear,
    month:      selectedMonthNum,
    monthStr:   selectedMonth,
    refreshKey,
  }

  // ── TAB 定義 ──────────────────────────────────────────────────────────────
  const tabItems = [
    {
      key:      'overview',
      label:    'A. 決策總覽',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabOverview {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'hotel',
      label:    'B. 飯店管理摘要',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabHotel {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'mall',
      label:    'C. 商場管理摘要',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabMall {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'repair',
      label:    'D. 工務與報修',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabRepair {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'personnel',
      label:    'E. 人員工時與效率',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabPersonnel {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'risk',
      label:    'F. 異常與風險雷達',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabRiskRadar {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'trend',
      label:    'G. 趨勢分析',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabTrend {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'briefing',
      label:    'H. 主管晨會摘要',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabBriefing {...tabProps} />
        </Suspense>
      ),
    },
    {
      key:      'quality',
      label:    'I. 資料品質監控',
      children: (
        <Suspense fallback={<TabLoading />}>
          <TabDataQuality {...tabProps} />
        </Suspense>
      ),
    },
  ]

  return (
    <div style={{ background: T.bg, minHeight: '100vh', padding: '0 0 40px' }}>

      {/* ── 頁頭 Card ──────────────────────────────────────────────────────── */}
      <Card
        style={{
          borderRadius: 0,
          borderBottom: `2px solid ${T.accent}`,
          marginBottom: 0,
        }}
        bodyStyle={{ padding: '16px 24px' }}
      >
        {/* 麵包屑 */}
        <Breadcrumb
          style={{ marginBottom: 12 }}
          items={[
            { href: '/dashboard', title: <HomeOutlined /> },
            { title: <><RadarChartOutlined /> {NAV_PAGE.decisionCockpit}</> },
          ]}
        />

        {/* 標題列 + 操作列 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          {/* 左：標題 */}
          <div>
            <Title level={4} style={{ margin: 0, color: T.primary }}>
              <RadarChartOutlined style={{ marginRight: 8, color: T.accent }} />
              {NAV_PAGE.decisionCockpit}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              整合飯店管理、商場管理、工務報修三大模組精華 · 高階主管決策入口
            </Text>
          </div>

          {/* 右：月份選擇器 + 操作按鈕 */}
          <Space wrap>
            <Select
              value={selectedMonth}
              onChange={handleMonthChange}
              style={{ width: 150 }}
              size="middle"
            >
              {MONTH_OPTIONS.map(o => (
                <Option key={o.value} value={o.value}>{o.label}</Option>
              ))}
            </Select>

            <Tooltip title="重新整理所有資料">
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
              >
                重新整理
              </Button>
            </Tooltip>

            <Tooltip title="列印 / 另存為 PDF（使用瀏覽器列印功能）">
              <Button
                icon={<ExportOutlined />}
                type="primary"
                ghost
                onClick={() => window.print()}
              >
                匯出報告
              </Button>
            </Tooltip>
          </Space>
        </div>
      </Card>

      {/* ── TAB 主體 ──────────────────────────────────────────────────────── */}
      <div style={{ padding: '0 24px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          type="card"
          size="middle"
          style={{ marginTop: 16 }}
          items={tabItems}
          destroyInactiveTabPane={false}
        />
      </div>
    </div>
  )
}
