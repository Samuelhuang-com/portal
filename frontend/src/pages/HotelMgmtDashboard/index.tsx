/**
 * ★飯店管理 Dashboard — 跨模組總覽
 *
 * 整合來源：
 *   1. 飯店週期保養表    /periodic-maintenance/stats
 *   2. IHG客房保養       /ihg-room-maintenance/stats
 *   3. 飯店每日巡檢      /hotel-daily-inspection/dashboard/summary
 *   4. 保全巡檢          /security/dashboard/summary + trend
 *   5. 工務部            /dazhi-repair/dashboard
 *
 * 不新增後端 API，所有 normalize 在前端 adapter layer 完成。
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Row, Col, Card, Statistic, Typography, Breadcrumb, Select,
  Spin, Alert, Tabs, Tag, Space, Progress, Divider, Tooltip,
  Badge, Table, Button, DatePicker,
} from 'antd'
import {
  HomeOutlined, ToolOutlined, SafetyOutlined, BuildOutlined,
  ClockCircleOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  BarChartOutlined, LineChartOutlined, PieChartOutlined,
  DashboardOutlined, WarningOutlined, RightOutlined,
  ReloadOutlined, QuestionCircleOutlined, FilePptOutlined, DownloadOutlined,
  CalendarOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip as RcTooltip, ResponsiveContainer, Legend,
} from 'recharts'
import dayjs from 'dayjs'

// ── 既有 API ──────────────────────────────────────────────────────────────────
import { fetchPMStats }                  from '@/api/periodicMaintenance'
import { fetchIHGStats }                 from '@/api/ihgRoomMaintenance'
import {
  fetchHotelDailyDashboardSummary,
  fetchHotelDailyMonthlyDashboard,
  type HotelDIDashboardSummary,
  type HotelDIMonthlyDashboard,
} from '@/api/hotelDailyInspection'
import {
  fetchSecurityDashboardSummary,
  fetchSecurityDashboardTrend,
  fetchSecurityMonthlyDashboard,
  type SecurityMonthlyDashboard,
} from '@/api/securityPatrol'
import type {
  SecurityDashboardSummary,
  SecurityDashboardTrend,
  SecurityTrendPoint,
} from '@/types/securityPatrol'
import { fetchDashboard }                from '@/api/dazhiRepair'
import { SourceStatusCard }              from '@/components/SourceStatusCard'
import {
  fetchHotelDailyHours,
  fetchHotelMonthlyHours,
  fetchHotelPersonHours,
  exportHotelOverviewPptx,
  HOTEL_CATEGORY_COLORS,
  type HotelDailyHoursData,
  type HotelMonthlyHoursData,
  type HotelPersonHoursData,
  type HotelPptxPayload,
} from '@/api/hotelOverview'
import type { PMStats }                  from '@/types/periodicMaintenance'
import type { IHGStats }                 from '@/types/ihgRoomMaintenance'
import type { DashboardData }            from '@/types/dazhiRepair'
import { NAV_GROUP, NAV_PAGE }           from '@/constants/navLabels'

const { Title, Text } = Typography

// ── 色彩常數（沿用現有設計規範）───────────────────────────────────────────────
const BRAND_BLUE  = '#1B3A5C'
const ACCENT_BLUE = '#4BA8E8'
const GREEN       = '#52C41A'
const ORANGE      = '#FA8C16'
const RED         = '#FF4D4F'
const PURPLE      = '#722ED1'
const CYAN        = '#13C2C2'

const SOURCE_COLORS: Record<string, string> = {
  periodic:          ACCENT_BLUE,
  ihg:               PURPLE,
  daily_inspection:  GREEN,
  security:          ORANGE,
  dazhi:             CYAN,
}

const PIE_COLORS = [ACCENT_BLUE, PURPLE, GREEN, ORANGE, CYAN]

// ── Tab B — 五項工作類別（B. 每日累計）───────────────────────────────────────
const HOTEL_5CATS = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢'] as const
type Hotel5Cat = typeof HOTEL_5CATS[number]

const HOTEL_5CAT_TAG_COLORS: Record<string, string> = {
  現場報修: 'blue',
  上級交辦: 'green',
  緊急事件: 'red',
  例行維護: 'orange',
  每日巡檢: 'purple',
}

// ── 來源 Icon / 路由設定（供 SourceCards 使用）────────────────────────────────
const HOTEL_SOURCE_ICONS: Record<string, React.ReactNode> = {
  periodic:         <BuildOutlined />,
  ihg:              <BuildOutlined />,
  daily_inspection: <SafetyOutlined />,
  security:         <SafetyOutlined />,
  dazhi:            <ToolOutlined />,
}

const HOTEL_SOURCE_ROUTES: Record<string, string> = {
  periodic:         '/hotel/periodic-maintenance',
  ihg:              '/hotel/ihg-room-maintenance',
  daily_inspection: '/hotel/daily-inspection',
  security:         '/security/dashboard',
  dazhi:            '/hotel/dazhi-repair/dashboard',
}

// ── Normalize 結構 ────────────────────────────────────────────────────────────
/**
 * 統一正規化結構 — 每個來源都轉換成此介面後供 Dashboard 使用
 */
interface NormalizedSource {
  source_key:      string    // 唯一識別 key
  source_name:     string    // 顯示名稱
  source_color:    string    // 顏色
  case_count:      number    // 案件/工項數（-1 = 不適用）
  completed_count: number    // 已完成數量
  work_hours:      number    // 工時（小時）（-1 = 不適用）；對 PM 來源 = 預估工時（planned_minutes/60）
  actual_hours?:   number    // 保養時間（實際完成工時，actual_minutes/60）；僅 showPmHours 來源設定
                             // ⚠️ 後端 periodic_maintenance /stats 目前未計算 actual_minutes，
                             //    欄位存在但值為 0；待後端補上後自動生效。
  completion_rate: number    // 完成率 % (0–100)（-1 = 不適用）
  abnormal_count:  number    // 異常/未完成 數量
  overdue_count:   number    // 逾期數量
  status_label:    string    // 狀態摘要文字
  is_ok:           boolean   // 整體健康狀態
}

// ── Adapter 函式 ──────────────────────────────────────────────────────────────

function adaptPeriodic(stats: PMStats): NormalizedSource {
  const kpi = stats.current_kpi
  const rate = kpi?.completion_rate ?? 0
  return {
    source_key:      'periodic',
    source_name:     '飯店週期保養',
    source_color:    SOURCE_COLORS.periodic,
    case_count:      kpi?.current_month_total ?? 0,
    completed_count: kpi?.completed ?? 0,
    work_hours:      (kpi?.planned_minutes  ?? 0) / 60,  // 預估工時（計劃工時）
    actual_hours:    (kpi?.actual_minutes   ?? 0) / 60,  // 保養時間（實際工時）⚠️ 後端目前未輸出，值為 0
    completion_rate: rate,
    abnormal_count:  kpi?.overdue ?? 0,
    overdue_count:   kpi?.overdue ?? 0,
    status_label:    `完成率 ${rate.toFixed(1)}%`,
    is_ok:           rate >= 70,
  }
}

function adaptIHG(stats: IHGStats): NormalizedSource {
  return {
    source_key:      'ihg',
    source_name:     'IHG客房保養',
    source_color:    SOURCE_COLORS.ihg,
    case_count:      stats.total_scheduled,  // 當月有執行的房間數（distinct room_no）
    completed_count: stats.completed,
    work_hours:      stats.work_hours ?? -1, // 來自 raw_json「工時計算」加總 / 60
    completion_rate: stats.completion_rate,
    abnormal_count:  stats.abnormal,
    overdue_count:   0,
    status_label:    `完成率 ${stats.completion_rate.toFixed(1)}%`,
    is_ok:           stats.completion_rate >= 70,
  }
}

/** 月份彙總口徑：HotelDIMonthlyDashboard（後端 /dashboard/monthly-summary） */
function adaptHotelDI(summary: HotelDIMonthlyDashboard): NormalizedSource {
  const rate = summary.completion_rate
  return {
    source_key:      'daily_inspection',
    source_name:     '飯店每日巡檢',
    source_color:    SOURCE_COLORS.daily_inspection,
    case_count:      summary.total_items,
    completed_count: summary.checked_items,
    work_hours:      summary.total_minutes / 60,
    completion_rate: rate,
    abnormal_count:  summary.abnormal_items,
    overdue_count:   0,
    status_label:    `完成率 ${rate.toFixed(1)}%`,
    is_ok:           rate >= 80,
  }
}

/** 月份彙總口徑：SecurityMonthlyDashboard（後端 /monthly-summary） */
function adaptSecurity(summary: SecurityMonthlyDashboard): NormalizedSource {
  return {
    source_key:      'security',
    source_name:     '保全巡檢',
    source_color:    SOURCE_COLORS.security,
    case_count:      summary.total_items,
    completed_count: summary.checked_items,
    work_hours:      summary.total_minutes / 60,
    completion_rate: summary.completion_rate,
    abnormal_count:  summary.abnormal_items,
    overdue_count:   0,
    status_label:    `完成率 ${summary.completion_rate.toFixed(1)}%`,
    is_ok:           summary.completion_rate >= 80,
  }
}

function adaptDazhi(data: DashboardData): NormalizedSource {
  const kpi  = data.kpi
  const rate = kpi.total > 0 ? Math.round(kpi.completed / kpi.total * 1000) / 10 : 0
  return {
    source_key:      'dazhi',
    source_name:     '飯店工務部',
    source_color:    SOURCE_COLORS.dazhi,
    case_count:      kpi.total,
    completed_count: kpi.completed,
    work_hours:      kpi.total_work_hours,
    completion_rate: rate,
    abnormal_count:  kpi.uncompleted,  // 未完成（非已完成、非待辦驗）
    overdue_count:   0,
    status_label:    `結案率 ${rate.toFixed(1)}%`,
    is_ok:           rate >= 50,
  }
}

// ── 工具函式 ──────────────────────────────────────────────────────────────────
const fmtHours = (h: number) =>
  h < 0 ? '—' : h < 100 ? `${h.toFixed(1)} HR` : `${Math.round(h)} HR`

const fmtCount = (n: number) => n < 0 ? '—' : n.toLocaleString()

// ── CSV 匯出工具（BOM 確保 Excel 開啟中文不亂碼）────────────────────────────
function exportCSV(filename: string, headers: string[], rows: (string | number)[][]) {
  const lines = [headers, ...rows].map(r =>
    r.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
  )
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}


// ════════════════════════════════════════════════════════════════════════════
// 主頁面
// ════════════════════════════════════════════════════════════════════════════
export default function HotelMgmtDashboardPage() {
  // ── 各類別計算公式說明（Tooltip 內容，用 createElement 避免 JSX 在物件值的 parser 問題）─
  const ce = React.createElement
  const HOTEL_5CAT_TOOLTIPS: Record<Hotel5Cat, React.ReactNode> = {
    現場報修: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      ce('b', null, '飯店工務部 / Hotel Engineering'), '（hotel/dazhi-repair）', ce('br'),
      '以 ', ce('code', null, '_stat_year/_stat_month'), ' 口徑歸屬月份：', ce('br'),
      '・已結案且 ', ce('code', null, 'completed_at'), ' 有值 → 以 completed_at 歸屬', ce('br'),
      '・其餘 → 以 ', ce('code', null, 'occurred_at'), '（事件發生日）歸屬', ce('br'),
      ce('span', { style: { color: '#ccc', fontSize: 11 } },
        '已結案狀態：結案／已辦驗／已驗收／已結案／完修／已完成／完成'),
    ),
    上級交辦: ce('div', { style: { fontSize: 12 } }, '建置中，目前顯示 0'),
    緊急事件: ce('div', { style: { fontSize: 12 } }, '建置中，目前顯示 0'),
    例行維護: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      '① ', ce('b', null, '飯店例行維護 / Hotel Periodic Maintenance'), '（hotel/periodic-maintenance）', ce('br'),
      '　同「每月維護」TAB「本月週期保養項目數」口徑：', ce('br'),
      '　', ce('code', null, 'frequency'), ' 為月維護（月／每月／月維護／Monthly／monthly）', ce('br'),
      '　＋ ', ce('code', null, 'exec_months'), ' 包含目標月份', ce('br'),
      '　＋ ', ce('code', null, 'scheduled_date'), ' 重組後落在目標月份', ce('br'),
      '② ', ce('b', null, 'IHG客房保養 / IHG Room Maintenance'), '（hotel/ihg-room-maintenance）', ce('br'),
      '　目標月份內 ', ce('code', null, 'maint_date'), ' 有資料的不重複房號數（distinct room_no）', ce('br'),
      ce('b', null, '總和 = ①＋②'),
    ),
    每日巡檢: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      '① ', ce('b', null, '飯店每日巡檢 / Hotel Daily Inspection'), '（hotel/daily-inspection）', ce('br'),
      '　以 ', ce('code', null, 'inspection_date'), ' 歸屬，每筆批次 = 一次巡邏', ce('br'),
      '② ', ce('b', null, '保全巡檢 / Security Patrol'), '（security/patrol）', ce('br'),
      '　以 ', ce('code', null, 'inspection_date'), ' 歸屬，每筆批次 = 一次巡邏', ce('br'),
      ce('b', null, '總和 = ①＋②'),
    ),
  }

  const navigate  = useNavigate()
  const thisYear  = dayjs().year()
  const thisMonth = dayjs().month() + 1

  // ── 巡檢日期（可由 DatePicker 更改）─────────────────────────────────────
  const [targetDate, setTargetDate] = useState<string>(dayjs().format('YYYY/MM/DD'))

  // ── 篩選狀態 ────────────────────────────────────────────────────────────
  const [year,  setYear]  = useState<number>(thisYear)
  const [month, setMonth] = useState<number>(thisMonth)

  // ── 資料狀態 ────────────────────────────────────────────────────────────
  const [loading, setLoading] = useState(false)
  const [errors,  setErrors]  = useState<string[]>([])

  const [pmStats,           setPmStats]           = useState<PMStats | null>(null)
  const [ihgStats,          setIhgStats]          = useState<IHGStats | null>(null)
  const [hotelDiMonthly,    setHotelDiMonthly]    = useState<HotelDIMonthlyDashboard | null>(null)
  const [secMonthly,        setSecMonthly]        = useState<SecurityMonthlyDashboard | null>(null)
  // 以下保留供圖表 / 趨勢 Tab 使用（單日口徑）
  const [hotelDiSummary,    setHotelDiSummary]    = useState<HotelDIDashboardSummary | null>(null)
  const [secSummary,        setSecSummary]        = useState<SecurityDashboardSummary | null>(null)
  const [secTrend,          setSecTrend]          = useState<SecurityDashboardTrend | null>(null)
  const [dazhiData,         setDazhiData]         = useState<DashboardData | null>(null)

  // ── 新 Tab 資料狀態（懶載入）─────────────────────────────────────────────
  const [dailyData,       setDailyData]        = useState<HotelDailyHoursData | null>(null)
  const [monthlyData,     setMonthlyData]      = useState<HotelMonthlyHoursData | null>(null)
  const [personData,      setPersonData]       = useState<HotelPersonHoursData | null>(null)
  const [tabBLoading,     setTabBLoading]      = useState(false)
  const [tabCLoading,     setTabCLoading]      = useState(false)
  const [tabDLoading,      setTabDLoading]       = useState(false)
  const [yearlyData,       setYearlyData]        = useState<HotelMonthlyHoursData | null>(null)
  const [yearlyYear,       setYearlyYear]        = useState<number>(thisYear)
  const [tabYearlyLoading, setTabYearlyLoading]  = useState(false)
  const [exportLoading,    setExportLoading]     = useState(false)

  // ── Tab 獨立篩選狀態（各 Tab 不影響 Dashboard 的 year/month）────────────
  const [tabBYear,   setTabBYear]   = useState<number>(thisYear)
  const [tabBMonth,  setTabBMonth]  = useState<number>(thisMonth)
  const [tabCYear,   setTabCYear]   = useState<number>(thisYear)
  const [personYear, setPersonYear] = useState<number>(thisYear)


  // ── 載入函式 ─────────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    setLoading(true)
    const errs: string[] = []

    await Promise.allSettled([
      // 週期保養：傳入 year/month
      fetchPMStats(String(year), month > 0 ? month : undefined).then(setPmStats).catch(() => { errs.push('週期保養表') }),
      // IHG客房保養：傳入 year 和 month，回傳當月房間數與工時
      fetchIHGStats(String(year), month > 0 ? String(month) : undefined).then(setIhgStats).catch(() => { errs.push('IHG客房保養') }),
      // 飯店每日巡檢：改為月份彙總口徑
      ...(month > 0
        ? [fetchHotelDailyMonthlyDashboard(year, month).then(setHotelDiMonthly).catch(() => { errs.push('飯店每日巡檢') })]
        : []
      ),
      // 保全巡檢：改為月份彙總口徑
      ...(month > 0
        ? [fetchSecurityMonthlyDashboard(year, month).then(setSecMonthly).catch(() => { errs.push('保全巡檢') })]
        : []
      ),
      // 單日口徑保留供趨勢圖使用
      fetchHotelDailyDashboardSummary(targetDate).then(setHotelDiSummary).catch(() => {}),
      fetchSecurityDashboardSummary(targetDate).then(setSecSummary).catch(() => {}),
      fetchSecurityDashboardTrend(30).then(setSecTrend).catch(() => {}),
      fetchDashboard(year, month).then(setDazhiData).catch(() => { errs.push('工務部') }),
    ])

    setErrors(errs)
    setLoading(false)
  }, [year, month, targetDate]) // eslint-disable-line

  // 單獨重新載入巡檢資料（DatePicker 變更時用）
  const loadInspections = useCallback(async (date: string) => {
    setLoading(true)
    await Promise.allSettled([
      fetchHotelDailyDashboardSummary(date).then(setHotelDiSummary).catch(() => {}),
      fetchSecurityDashboardSummary(date).then(setSecSummary).catch(() => {}),
      fetchSecurityDashboardTrend(30).then(setSecTrend).catch(() => {}),
    ])
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  // 切換 tab 時懶載入對應資料（各 Tab 使用獨立 year/month state，首次切換時觸發）
  const handleTabChange = useCallback((key: string) => {
    if (key === 'daily' && !dailyData) {
      setTabBLoading(true)
      fetchHotelDailyHours(tabBYear, tabBMonth).then(setDailyData).finally(() => setTabBLoading(false))
    } else if (key === 'monthly' && !monthlyData) {
      setTabCLoading(true)
      fetchHotelMonthlyHours(tabCYear).then(setMonthlyData).finally(() => setTabCLoading(false))
    } else if (key === 'yearly' && !yearlyData) {
      setTabYearlyLoading(true)
      fetchHotelMonthlyHours(yearlyYear).then(setYearlyData).finally(() => setTabYearlyLoading(false))
    } else if ((key === 'person_pct' || key === 'ranking') && !personData) {
      setTabDLoading(true)
      fetchHotelPersonHours(personYear).then(setPersonData).finally(() => setTabDLoading(false))
    }
  }, [tabBYear, tabBMonth, tabCYear, yearlyYear, personYear, dailyData, monthlyData, yearlyData, personData])

  // ── Normalize 各來源（KPI Card 用月份彙總口徑）────────────────────────
  const sources: NormalizedSource[] = [
    pmStats         ? adaptPeriodic(pmStats)           : null,
    ihgStats        ? adaptIHG(ihgStats)               : null,
    hotelDiMonthly  ? adaptHotelDI(hotelDiMonthly)     : null,  // 月份彙總
    secMonthly      ? adaptSecurity(secMonthly)        : null,  // 月份彙總
    dazhiData       ? adaptDazhi(dazhiData)            : null,
  ].filter(Boolean) as NormalizedSource[]

  // ── 聚合 KPI ──────────────────────────────────────────────────────────
  const totalWorkHours    = sources.reduce((s, x) => s + (x.work_hours > 0 ? x.work_hours : 0), 0)
  const totalCases        = sources.reduce((s, x) => s + (x.case_count > 0 ? x.case_count : 0), 0)
  const totalCompleted    = sources.reduce((s, x) => s + x.completed_count, 0)
  const totalAbnormal     = sources.reduce((s, x) => s + x.abnormal_count, 0)
  const totalOverdue      = sources.reduce((s, x) => s + x.overdue_count, 0)
  const overallRate       = totalCases > 0 ? Math.round(totalCompleted / totalCases * 100) : 0

  // ── 篩選選項 + 費用標籤 ───────────────────────────────────────────────
  const yearOptions  = [2024, 2025, 2026, 2027].map(y => ({ value: y, label: `${y} 年` }))
  const monthOptions = [
    { value: 0,  label: '全年' },
    ...Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: `${i + 1} 月` })),
  ]
  const monthOptions12 = Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: `${i + 1} 月` }))
  const ytdLabel = month > 0 ? `累計至 ${month} 月` : '全年'

  // ── 圖表資料 ──────────────────────────────────────────────────────────

  // 1. 各來源工時占比（Pie）
  const sourcePieData = sources
    .filter(s => s.work_hours > 0)
    .map(s => ({ name: s.source_name, value: parseFloat(s.work_hours.toFixed(1)), color: s.source_color }))

  // 1b. 各來源工項數比較（Horizontal Bar）
  const barData = sources
    .filter(s => s.case_count > 0)
    .map(s => ({ name: s.source_name, 工項數: s.case_count, 完成數: s.completed_count, fill: s.source_color }))

  // 1c. 各來源完成率比較（Horizontal Bar）
  const rateBarData = sources
    .filter(s => s.completion_rate >= 0)
    .map(s => ({ name: s.source_name, 完成率: Math.round(s.completion_rate), fill: s.source_color }))

  // 2. 工務 12個月趨勢
  const dazhiTrend = dazhiData?.trend_12m ?? []

  // 3. 保全巡檢近 30 日異常趨勢
  const secTrendData = (secTrend?.trend ?? [])
    .filter((t: SecurityTrendPoint) => t.has_data)
    .map((t: SecurityTrendPoint) => ({ date: t.date.slice(5), abnormal: t.abnormal_count }))
    .slice(-14) // 最近 14 天有資料的

  // ── 來源卡片（6 有資料 + 2 佔位，共 8 張，2 排 × 4 欄）──────────────────
  function SourceCards() {
    if (!sources.length) return null

    const PLACEHOLDER_CARDS = [
      { key: 'mgmt_order', label: '飯店主管交辦', color: ORANGE, icon: <ExclamationCircleOutlined /> },
      { key: 'emergency',  label: '飯店緊急事件', color: RED,    icon: <WarningOutlined />           },
    ]

    return (
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {/* ── 六個有資料的來源卡 ── */}
        {sources.map(s => (
          <Col key={s.source_key} xs={12} sm={12} md={6}>
            <SourceStatusCard
              {...s}
              icon={HOTEL_SOURCE_ICONS[s.source_key]}
              onClick={() => navigate(HOTEL_SOURCE_ROUTES[s.source_key] ?? '#')}
            />
          </Col>
        ))}

        {/* ── 兩張佔位卡（數據準備中）── */}
        {PLACEHOLDER_CARDS.map(p => (
          <Col key={p.key} xs={12} sm={12} md={6}>
            <SourceStatusCard
              source_key={p.key}
              source_name={p.label}
              source_color={p.color}
              case_count={-1}
              completed_count={0}
              work_hours={-1}
              completion_rate={-1}
              abnormal_count={0}
              overdue_count={0}
              status_label=""
              is_placeholder
              icon={p.icon}
            />
          </Col>
        ))}
      </Row>
    )
  }

  // ── 聚合 KPI Cards ─────────────────────────────────────────────────────
  function KpiAggregate() {
    return (
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${BRAND_BLUE}` }}>
            <Statistic
              title={<span style={{ fontSize: 11, color: '#888' }}>本期總工項</span>}
              value={totalCases}
              suffix="筆"
              valueStyle={{ fontSize: 22, color: BRAND_BLUE, fontWeight: 700 }}
              prefix={<BarChartOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${GREEN}` }}>
            <Statistic
              title={<span style={{ fontSize: 11, color: '#888' }}>已完成工項</span>}
              value={totalCompleted}
              suffix="筆"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: GREEN }}
              prefix={<CheckCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${ORANGE}` }}>
            <Statistic
              title={
                <Tooltip title="客房保養（實際）+ 週期保養（預估計劃）+ IHG 保養（暫無）+ 每日巡檢（實際）+ 保全巡檢（實際）+ 現場報修（work_hours / close_days）合計">
                  <span style={{ fontSize: 11, color: '#888', cursor: 'help' }}>
                    本期工時合計 <QuestionCircleOutlined style={{ color: '#bbb' }} />
                  </span>
                </Tooltip>
              }
              value={totalWorkHours}
              suffix="HR"
              precision={1}
              valueStyle={{ fontSize: 22, fontWeight: 700, color: ORANGE }}
              prefix={<ClockCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${totalAbnormal > 0 ? RED : GREEN}` }}>
            <Statistic
              title={<span style={{ fontSize: 11, color: '#888' }}>異常/未完成</span>}
              value={totalAbnormal}
              suffix="件"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: totalAbnormal > 0 ? RED : GREEN }}
              prefix={<WarningOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
            {totalAbnormal === 0 && <Tag color="success" style={{ marginTop: 4, fontSize: 11 }}>全部正常</Tag>}
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${totalOverdue > 0 ? '#C0392B' : GREEN}` }}>
            <Statistic
              title={<span style={{ fontSize: 11, color: '#888' }}>逾期未完成</span>}
              value={totalOverdue}
              suffix="項"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: totalOverdue > 0 ? '#C0392B' : GREEN }}
              prefix={<ExclamationCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>
      </Row>
    )
  }

  // ── 工務趨勢圖 ────────────────────────────────────────────────────────
  function DazhiTrendChart() {
    if (!dazhiTrend.length) return null
    return (
      <Card
        title={<><ToolOutlined /> 工務 — 12個月報修趨勢</>}
        size="small"
        bodyStyle={{ padding: '8px' }}
        style={{ marginBottom: 12 }}
      >
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={dazhiTrend} margin={{ top: 4, right: 20, left: -10, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <RcTooltip formatter={(v: number, name: string) => [v, name === 'total' ? '總件數' : '完成']} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }}
              formatter={(v) => v === 'total' ? '總件數' : '完成件數'} />
            <Line type="monotone" dataKey="total"     stroke={CYAN}  strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="completed" stroke={GREEN} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  // ── 工時來源占比 ───────────────────────────────────────────────────────
  function SourcePieChart() {
    if (!sourcePieData.length) return null
    return (
      <Card
        title={<><PieChartOutlined /> 工時來源占比</>}
        size="small"
        bodyStyle={{ padding: '8px' }}
        style={{ marginBottom: 12 }}
      >
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={sourcePieData} dataKey="value" nameKey="name"
              cx="50%" cy="50%" innerRadius={40} outerRadius={70}
            >
              {sourcePieData.map((entry, i) => (
                <Cell key={i} fill={entry.color ?? PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <RcTooltip formatter={(v: number, name: string) => [`${v.toFixed(1)} HR`, name]} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  // ════════════════════════════════════════════════════════════════════════
  // B. 每日累計 — 欄位建構 + 渲染
  // ════════════════════════════════════════════════════════════════════════

  // ── Tab B — 欄位建構（五項工作類別 × 每日）──────────────────────────────
  function buildDailyCols(days: number[], weekdays: string[]) {
    type Row5 = { category: string; cases: number[]; total: number; cases_pct: number; key: string }
    return [
      {
        title: '工項類別', dataIndex: 'category', key: 'category',
        fixed: 'left' as const, width: 100,
        render: (v: string) =>
          v === 'TOTAL'
            ? <Text strong style={{ color: BRAND_BLUE }}>TOTAL</Text>
            : <Tag color={HOTEL_5CAT_TAG_COLORS[v] ?? 'default'} style={{ fontSize: 13 }}>{v}</Tag>,
      },
      ...days.map((d, i) => ({
        title: (
          <div style={{ textAlign: 'center' as const, lineHeight: 1.2 }}>
            <div style={{ fontSize: 12 }}>{d}</div>
            <div style={{ fontSize: 11, color: '#888' }}>{weekdays[i]}</div>
          </div>
        ),
        key: `d${d}`, width: 38, align: 'center' as const,
        render: (_: unknown, row: Row5) => {
          const v = row.cases[i] ?? 0
          return <Text style={{ fontSize: 13, color: v > 0 ? BRAND_BLUE : '#ccc' }}>
            {v > 0 ? v : '—'}
          </Text>
        },
      })),
      {
        title: '案件數', dataIndex: 'total', key: 'total', width: 62,
        align: 'center' as const,
        render: (v: number, row: Row5) => (
          <Text strong style={{ color: row.category === 'TOTAL' ? BRAND_BLUE : '#333' }}>
            {v}
          </Text>
        ),
      },
      {
        title: '%', dataIndex: 'cases_pct', key: 'cases_pct', width: 54, align: 'center' as const,
        render: (v: number, row: Row5) => (
          <Text style={{
            color: row.category === 'TOTAL' ? '#888' : ORANGE,
            fontWeight: row.category !== 'TOTAL' ? 600 : 400,
          }}>
            {v.toFixed(1)}%
          </Text>
        ),
      },
    ]
  }

  function TabBDaily() {
    if (!dailyData) return <Alert message="切換至此 Tab 後自動載入" type="info" showIcon />

    // ── 將後端六項來源合併為主管要的五項工作類別 ─────────────────────────
    const find = (name: string) => dailyData.rows.find(r => r.category === name)
    const n = dailyData.days.length
    const zeroes = (): number[] => Array(n).fill(0)
    const addH   = (a: number[] | undefined, b: number[] | undefined): number[] =>
      zeroes().map((_, i) => (a?.[i] ?? 0) + (b?.[i] ?? 0))

    const dazhi    = find('飯店工務部')
    const room     = find('客房保養管理')
    const periodic = find('飯店週期保養')
    const ihg      = find('IHG客房保養')
    const diHotel  = find('飯店每日巡檢')
    const security = find('保全巡檢')

    const catCases: Record<Hotel5Cat, number[]> = {
      現場報修: dazhi?.cases                                     ?? zeroes(),
      上級交辦: zeroes(),
      緊急事件: zeroes(),
      例行維護: addH(addH(room?.cases, periodic?.cases), ihg?.cases),
      每日巡檢: addH(diHotel?.cases, security?.cases),
    }

    const grandTotal = (HOTEL_5CATS as readonly Hotel5Cat[]).reduce(
      (s, cat) => s + catCases[cat].reduce((a, b) => a + b, 0), 0
    )

    type Row5 = { key: string; category: string; cases: number[]; total: number; cases_pct: number }
    const tableRows: Row5[] = (HOTEL_5CATS as readonly Hotel5Cat[]).map(cat => {
      const cases = catCases[cat]
      const total = cases.reduce((a, b) => a + b, 0)
      const cases_pct = grandTotal > 0 ? Math.round(total / grandTotal * 1000) / 10 : 0
      return { key: cat, category: cat, cases, total, cases_pct }
    })

    // TOTAL 合計列
    const totalCases = dailyData.days.map((_, i) =>
      (HOTEL_5CATS as readonly Hotel5Cat[]).reduce((s, cat) => s + (catCases[cat][i] ?? 0), 0)
    )
    const totalTotal = totalCases.reduce((a, b) => a + b, 0)
    tableRows.push({ key: 'TOTAL', category: 'TOTAL', cases: totalCases, total: totalTotal, cases_pct: 100 })

    return (
      <>
        {/* 篩選列 */}
        <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
          <Row gutter={[16, 8]} align="middle">
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>每日累計案件數</Text>
            </Col>
            <Col>
              <Select
                value={tabBYear} options={yearOptions} style={{ width: 100 }}
                onChange={(v) => {
                  setTabBYear(v)
                  setTabBLoading(true)
                  fetchHotelDailyHours(v, tabBMonth).then(setDailyData).finally(() => setTabBLoading(false))
                }}
              />
            </Col>
            <Col>
              <Select
                value={tabBMonth} options={monthOptions12} style={{ width: 90 }}
                onChange={(v) => {
                  setTabBMonth(v)
                  setTabBLoading(true)
                  fetchHotelDailyHours(tabBYear, v).then(setDailyData).finally(() => setTabBLoading(false))
                }}
              />
            </Col>
            <Col>
              <Button
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => {
                  setTabBLoading(true)
                  fetchHotelDailyHours(tabBYear, tabBMonth).then(setDailyData).finally(() => setTabBLoading(false))
                }}
              >重新整理</Button>
            </Col>
            <Col flex="auto" />
            <Col>
              <Button
                icon={<DownloadOutlined />}
                size="small"
                disabled={!dailyData}
                onClick={() => {
                  if (!dailyData) return
                  const headers = ['工項類別', ...dailyData.days.map((d, i) => `${d}日(${dailyData.weekdays[i]})`), '案件數', '%']
                  const rows = dailyData.rows.map(r => [
                    r.category,
                    ...dailyData.days.map((_, i) => r.cases?.[i] ?? 0),
                    r.cases_total,
                    `${(r.cases_pct ?? 0).toFixed(1)}%`,
                  ])
                  exportCSV(`飯店管理_每日累計_${tabBYear}年${tabBMonth}月.csv`, headers, rows)
                }}
              >匯出 CSV</Button>
            </Col>
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>{tabBYear} 年 {tabBMonth} 月</Text>
            </Col>
          </Row>
        </Card>

        {/* 類別圖例 */}
        <Space wrap style={{ marginBottom: 12 }}>
          {(HOTEL_5CATS as readonly Hotel5Cat[]).map(cat => (
            <Space key={cat} size={2}>
              <Tag color={HOTEL_5CAT_TAG_COLORS[cat]}>{cat}</Tag>
              <Tooltip title={HOTEL_5CAT_TOOLTIPS[cat]} overlayStyle={{ maxWidth: 440 }}>
                <Text style={{ fontSize: 11, cursor: 'help', color: '#bbb' }}>ⓘ</Text>
              </Tooltip>
            </Space>
          ))}
        </Space>

        {/* 表格 */}
        <Card
          title={<Text strong>每日累計案件數</Text>}
          extra={<Text type="secondary">{dailyData.year} 年 {dailyData.month} 月</Text>}
          bodyStyle={{ padding: '6px 0' }}
        >
          <Table<Row5>
            dataSource={tableRows}
            columns={buildDailyCols(dailyData.days, dailyData.weekdays) as object[]}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            rowClassName={(r) => r.category === 'TOTAL' ? 'ant-table-row-total' : ''}
            style={{ fontSize: 14 }}
          />
        </Card>
      </>
    )
  }

  // ════════════════════════════════════════════════════════════════════════
  // C. 每月累計 — 欄位建構 + 渲染（五項工作類別，對齊 Tab B 版型）
  // ════════════════════════════════════════════════════════════════════════

  function buildMonthlyCols() {
    type Row5M = { category: string; cases: number[]; total: number; cases_pct: number; key: string }
    const zhMonths = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
    return [
      {
        title: '工項類別', dataIndex: 'category', key: 'category',
        fixed: 'left' as const, width: 100,
        render: (v: string) =>
          v === 'TOTAL'
            ? <Text strong style={{ color: BRAND_BLUE }}>TOTAL</Text>
            : <Tag color={HOTEL_5CAT_TAG_COLORS[v] ?? 'default'} style={{ fontSize: 13 }}>{v}</Tag>,
      },
      ...zhMonths.map((label, i) => ({
        title: label,
        key: `m${i + 1}`,
        width: 62,
        align: 'center' as const,
        render: (_: unknown, row: Row5M) => {
          const v = row.cases[i] ?? 0
          return <Text style={{ fontSize: 13, color: v > 0 ? BRAND_BLUE : '#ccc' }}>
            {v > 0 ? v : '—'}
          </Text>
        },
      })),
      {
        title: '案件數', dataIndex: 'total', key: 'total', width: 62,
        align: 'center' as const,
        render: (v: number, row: Row5M) => (
          <Text strong style={{ color: row.category === 'TOTAL' ? BRAND_BLUE : '#333' }}>
            {v}
          </Text>
        ),
      },
      {
        title: '%', dataIndex: 'cases_pct', key: 'cases_pct', width: 54, align: 'center' as const,
        render: (v: number, row: Row5M) => (
          <Text style={{
            color: row.category === 'TOTAL' ? '#888' : ORANGE,
            fontWeight: row.category !== 'TOTAL' ? 600 : 400,
          }}>
            {v.toFixed(1)}%
          </Text>
        ),
      },
    ]
  }

  function TabCMonthly() {
    if (!monthlyData) return <Alert message="切換至此 Tab 後自動載入" type="info" showIcon />

    // ── 將後端六項來源合併為五項工作類別（同 Tab B）────────────────────
    const find = (name: string) => monthlyData.rows.find(r => r.category === name)
    const n = 12
    const zeroes = (): number[] => Array(n).fill(0)
    const addH   = (a: number[] | undefined, b: number[] | undefined): number[] =>
      zeroes().map((_, i) => (a?.[i] ?? 0) + (b?.[i] ?? 0))

    const dazhi    = find('飯店工務部')
    const room     = find('客房保養管理')
    const periodic = find('飯店週期保養')
    const ihg      = find('IHG客房保養')
    const diHotel  = find('飯店每日巡檢')
    const security = find('保全巡檢')

    const catCases: Record<Hotel5Cat, number[]> = {
      現場報修: dazhi?.cases                                      ?? zeroes(),
      上級交辦: zeroes(),
      緊急事件: zeroes(),
      例行維護: addH(addH(room?.cases, periodic?.cases), ihg?.cases),
      每日巡檢: addH(diHotel?.cases, security?.cases),
    }

    const grandTotal = (HOTEL_5CATS as readonly Hotel5Cat[]).reduce(
      (s, cat) => s + catCases[cat].reduce((a, b) => a + b, 0), 0
    )

    type Row5M = { key: string; category: string; cases: number[]; total: number; cases_pct: number }
    const tableRows: Row5M[] = (HOTEL_5CATS as readonly Hotel5Cat[]).map(cat => {
      const cases = catCases[cat]
      const total = cases.reduce((a, b) => a + b, 0)
      const cases_pct = grandTotal > 0 ? Math.round(total / grandTotal * 1000) / 10 : 0
      return { key: cat, category: cat, cases, total, cases_pct }
    })

    // TOTAL 合計列
    const totalCases = Array.from({ length: 12 }, (_, i) =>
      (HOTEL_5CATS as readonly Hotel5Cat[]).reduce((s, cat) => s + (catCases[cat][i] ?? 0), 0)
    )
    const totalTotal = totalCases.reduce((a, b) => a + b, 0)
    tableRows.push({ key: 'TOTAL', category: 'TOTAL', cases: totalCases, total: totalTotal, cases_pct: 100 })

    return (
      <>
        {/* 篩選列 */}
        <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
          <Row gutter={[16, 8]} align="middle">
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>年度案件數彙總</Text>
            </Col>
            <Col>
              <Select
                value={tabCYear} options={yearOptions} style={{ width: 100 }}
                onChange={(v) => {
                  setTabCYear(v)
                  setTabCLoading(true)
                  fetchHotelMonthlyHours(v).then(setMonthlyData).finally(() => setTabCLoading(false))
                }}
              />
            </Col>
            <Col>
              <Button
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => {
                  setTabCLoading(true)
                  fetchHotelMonthlyHours(tabCYear).then(setMonthlyData).finally(() => setTabCLoading(false))
                }}
              >重新整理</Button>
            </Col>
            <Col flex="auto" />
            <Col>
              <Button
                icon={<DownloadOutlined />}
                size="small"
                disabled={!monthlyData}
                onClick={() => {
                  if (!monthlyData) return
                  const headers = ['工項類別', ...Array.from({length:12}, (_,i)=>`${i+1}月`), '案件數', '%']
                  const rows = monthlyData.rows.map(r => [
                    r.category,
                    ...Array.from({length:12}, (_,i) => r.cases?.[i] ?? 0),
                    r.cases_total,
                    `${(r.cases_pct ?? 0).toFixed(1)}%`,
                  ])
                  exportCSV(`飯店管理_每月累計_${tabCYear}年.csv`, headers, rows)
                }}
              >匯出 CSV</Button>
            </Col>
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>{tabCYear} 年</Text>
            </Col>
          </Row>
        </Card>

        {/* 類別圖例 */}
        <Space wrap style={{ marginBottom: 12 }}>
          {(HOTEL_5CATS as readonly Hotel5Cat[]).map(cat => (
            <Space key={cat} size={2}>
              <Tag color={HOTEL_5CAT_TAG_COLORS[cat]}>{cat}</Tag>
              <Tooltip title={HOTEL_5CAT_TOOLTIPS[cat]} overlayStyle={{ maxWidth: 440 }}>
                <Text style={{ fontSize: 11, cursor: 'help', color: '#bbb' }}>ⓘ</Text>
              </Tooltip>
            </Space>
          ))}
        </Space>

        {/* 表格 */}
        <Card
          title={<Text strong>每月累計案件數</Text>}
          extra={<Text type="secondary">{tabCYear} 年</Text>}
          bodyStyle={{ padding: '6px 0' }}
        >
          <Table<Row5M>
            dataSource={tableRows}
            columns={buildMonthlyCols() as object[]}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            rowClassName={(r) => r.category === 'TOTAL' ? 'ant-table-row-total' : ''}
            style={{ fontSize: 14 }}
          />
        </Card>
      </>
    )
  }

  // ════════════════════════════════════════════════════════════════════════
  // D. 每年累計 — 五項工作類別 × 12 個月（Running Total）
  // ════════════════════════════════════════════════════════════════════════

  function TabDYearly() {
    if (!yearlyData) return <Alert message="切換至此 Tab 後自動載入" type="info" showIcon />

    // 將後端來源合併為五項工作類別（同 TabCMonthly）
    const find = (name: string) => yearlyData.rows.find(r => r.category === name)
    const n = 12
    const zeroes = (): number[] => Array(n).fill(0)
    const addH   = (a: number[] | undefined, b: number[] | undefined): number[] =>
      zeroes().map((_, i) => (a?.[i] ?? 0) + (b?.[i] ?? 0))

    const dazhi    = find('飯店工務部')
    const room     = find('客房保養管理')
    const periodic = find('飯店週期保養')
    const ihg      = find('IHG客房保養')
    const diHotel  = find('飯店每日巡檢')
    const security = find('保全巡檢')

    const catMonthly: Record<Hotel5Cat, number[]> = {
      現場報修: dazhi?.cases                                      ?? zeroes(),
      上級交辦: zeroes(),
      緊急事件: zeroes(),
      例行維護: addH(addH(room?.cases, periodic?.cases), ihg?.cases),
      每日巡檢: addH(diHotel?.cases, security?.cases),
    }

    // 轉為累計（Running Total）：每月值 = 1 月到該月的加總（案件數，整數）
    const toCumulative = (arr: number[]): number[] => {
      let sum = 0
      return arr.map(v => { sum += v; return sum })
    }

    const catCases: Record<Hotel5Cat, number[]> = {
      現場報修: toCumulative(catMonthly.現場報修),
      上級交辦: toCumulative(catMonthly.上級交辦),
      緊急事件: toCumulative(catMonthly.緊急事件),
      例行維護: toCumulative(catMonthly.例行維護),
      每日巡檢: toCumulative(catMonthly.每日巡檢),
    }

    // 全年合計 = 12 月的累計值（= 全年各類別加總）
    const grandTotal = (HOTEL_5CATS as readonly Hotel5Cat[]).reduce(
      (s, cat) => s + (catCases[cat][11] ?? 0), 0
    )

    type Row5Y = { key: string; category: string; cases: number[]; total: number; cases_pct: number }
    const tableRows: Row5Y[] = (HOTEL_5CATS as readonly Hotel5Cat[]).map(cat => {
      const cases = catCases[cat]
      const total = cases[11] ?? 0   // 12 月累計 = 全年合計
      const cases_pct = grandTotal > 0 ? Math.round(total / grandTotal * 1000) / 10 : 0
      return { key: cat, category: cat, cases, total, cases_pct }
    })

    // TOTAL 列：每月所有類別累計之和
    const totalCases = Array.from({ length: 12 }, (_, i) =>
      (HOTEL_5CATS as readonly Hotel5Cat[]).reduce((s, cat) => s + (catCases[cat][i] ?? 0), 0)
    )
    tableRows.push({
      key: 'TOTAL', category: 'TOTAL',
      cases: totalCases,
      total: grandTotal,
      cases_pct: 100,
    })

    return (
      <>
        {/* 篩選列 */}
        <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
          <Row gutter={[16, 8]} align="middle">
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>年度累計案件數</Text>
            </Col>
            <Col>
              <Select
                value={yearlyYear}
                options={yearOptions}
                style={{ width: 100 }}
                onChange={(v) => {
                  setYearlyYear(v)
                  setTabYearlyLoading(true)
                  fetchHotelMonthlyHours(v).then(setYearlyData).finally(() => setTabYearlyLoading(false))
                }}
              />
            </Col>
            <Col>
              <Button
                icon={<ReloadOutlined />}
                size="small"
                onClick={() => {
                  setTabYearlyLoading(true)
                  fetchHotelMonthlyHours(yearlyYear).then(setYearlyData).finally(() => setTabYearlyLoading(false))
                }}
              >重新整理</Button>
            </Col>
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>{yearlyYear} 年（累計）</Text>
            </Col>
          </Row>
        </Card>

        {/* 類別圖例 */}
        <Space wrap style={{ marginBottom: 12 }}>
          {(HOTEL_5CATS as readonly Hotel5Cat[]).map(cat => (
            <Space key={cat} size={2}>
              <Tag color={HOTEL_5CAT_TAG_COLORS[cat]}>{cat}</Tag>
              <Tooltip title={HOTEL_5CAT_TOOLTIPS[cat]} overlayStyle={{ maxWidth: 440 }}>
                <Text style={{ fontSize: 11, cursor: 'help', color: '#bbb' }}>ⓘ</Text>
              </Tooltip>
            </Space>
          ))}
          <Tooltip title="各月數值為 1 月至該月的累計案件數總和（Running Total）。例：3 月欄位 = 1+2+3 月案件數合計。">
            <Text type="secondary" style={{ fontSize: 11, cursor: 'help', color: '#aaa' }}>
              ⓘ 累計說明
            </Text>
          </Tooltip>
        </Space>

        {/* 表格 */}
        <Card
          title={<Text strong>年度累計案件數</Text>}
          extra={<Text type="secondary">{yearlyYear} 年（累計至各月）</Text>}
          bodyStyle={{ padding: '6px 0' }}
        >
          <Table<Row5Y>
            dataSource={tableRows}
            columns={buildMonthlyCols() as object[]}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            rowClassName={(r) => r.category === 'TOTAL' ? 'ant-table-row-total' : ''}
            style={{ fontSize: 14 }}
          />
        </Card>
      </>
    )
  }

  // ════════════════════════════════════════════════════════════════════════
  // 人員工時% — 欄位建構 + 渲染
  // ════════════════════════════════════════════════════════════════════════

  function buildPersonCols(persons: string[]) {
    return [
      {
        title: '來源', dataIndex: 'category', key: 'category', fixed: 'left' as const, width: 110,
        render: (v: string) => (
          <span style={{ fontWeight: 500, color: HOTEL_CATEGORY_COLORS[v] ?? '#333' }}>{v}</span>
        ),
      },
      ...persons.map((name, i) => ({
        title: <span style={{ fontSize: 13 }}>{name}</span>,
        dataIndex: `p${i}`,
        key: `p${i}`,
        width: 70,
        align: 'center' as const,
        render: (v: number) => v > 0
          ? (
            <Tooltip title={`${name}: ${v}%`}>
              <Progress
                percent={v} size="small" showInfo={false}
                strokeColor={ACCENT_BLUE}
                style={{ minWidth: 50 }}
              />
              <div style={{ fontSize: 12, textAlign: 'center', color: '#666', marginTop: 2 }}>{v}%</div>
            </Tooltip>
          )
          : <span style={{ color: '#ddd', fontSize: 12 }}>-</span>,
      })),
    ]
  }

  function TabDPerson() {
    const personFilterCard = (
      <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
        <Row gutter={[16, 8]} align="middle">
          <Col><Text type="secondary" style={{ fontSize: 12 }}>人員工時%</Text></Col>
          <Col>
            <Select value={personYear} options={yearOptions} style={{ width: 100 }}
              onChange={(v) => {
                setPersonYear(v)
                setTabDLoading(true)
                fetchHotelPersonHours(v).then(setPersonData).finally(() => setTabDLoading(false))
              }} />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} size="small"
              onClick={() => {
                setTabDLoading(true)
                fetchHotelPersonHours(personYear).then(setPersonData).finally(() => setTabDLoading(false))
              }}>重新整理</Button>
          </Col>
          <Col><Text type="secondary" style={{ fontSize: 12 }}>{personYear} 年 · Top 15 人員</Text></Col>
        </Row>
      </Card>
    )
    if (!personData) return <>{personFilterCard}<Alert message="切換至此 Tab 後自動載入" type="info" showIcon /></>
    if (!personData.persons.length) return <>{personFilterCard}<Alert message="本年度暫無人員工時資料" type="info" showIcon /></>
    const tableData = personData.rows.map((row) => {
      const base: Record<string, number | string> = {
        key: row.category, category: row.category,
      }
      personData.persons.forEach((_, i) => { base[`p${i}`] = row.pct_by_person[i] })
      return base
    })
    return (
      <>
        {personFilterCard}
        <div style={{ marginBottom: 8, fontSize: 12, color: '#888' }}>
          共 {personData.persons.length} 位人員（依全年合計工時排序，取前15名）
        </div>
        <Table
          columns={buildPersonCols(personData.persons)}
          dataSource={tableData}
          pagination={false}
          size="small"
          scroll={{ x: 'max-content' }}
          style={{ fontSize: 14 }}
        />
      </>
    )
  }

  // ════════════════════════════════════════════════════════════════════════
  // 人員排名 — 橫向 Bar + 明細表
  // ════════════════════════════════════════════════════════════════════════

  function TabRanking() {
    const rankingFilterCard = (
      <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
        <Row gutter={[16, 8]} align="middle">
          <Col><Text type="secondary" style={{ fontSize: 12 }}>人員排名</Text></Col>
          <Col>
            <Select value={personYear} options={yearOptions} style={{ width: 100 }}
              onChange={(v) => {
                setPersonYear(v)
                setTabDLoading(true)
                fetchHotelPersonHours(v).then(setPersonData).finally(() => setTabDLoading(false))
              }} />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} size="small"
              onClick={() => {
                setTabDLoading(true)
                fetchHotelPersonHours(personYear).then(setPersonData).finally(() => setTabDLoading(false))
              }}>重新整理</Button>
          </Col>
          <Col><Text type="secondary" style={{ fontSize: 12 }}>{personYear} 年 · Top 15 人員</Text></Col>
        </Row>
      </Card>
    )
    if (!personData) return <>{rankingFilterCard}<Alert message="切換至此 Tab 後自動載入" type="info" showIcon /></>
    if (!personData.persons.length) return <>{rankingFilterCard}<Alert message="本年度暫無人員工時資料" type="info" showIcon /></>

    const medals = ['🥇', '🥈', '🥉']
    const barData = personData.persons.map((name, i) => ({
      name,
      total: personData.person_totals[i],
      medal: medals[i] ?? '',
    }))

    // 明細表：各人員 × 各來源工時（從 pct × category_total 反推，實際工時直接取 person_totals）
    const detailCols = [
      { title: '排名', dataIndex: 'rank', key: 'rank', width: 52, align: 'center' as const,
        render: (_: unknown, __: unknown, idx: number) => (
          <span style={{ fontSize: 16 }}>{medals[idx] ?? `${idx + 1}`}</span>
        ),
      },
      { title: '人員', dataIndex: 'name', key: 'name', width: 90,
        render: (v: string) => <span style={{ fontWeight: 600 }}>{v}</span>,
      },
      { title: '合計工時(HR)', dataIndex: 'total', key: 'total', width: 100, align: 'right' as const,
        render: (v: number) => <span style={{ fontWeight: 700, color: BRAND_BLUE }}>{v.toFixed(1)}</span>,
      },
      ...personData.rows.map(row => ({
        title: <span style={{ fontSize: 13, color: HOTEL_CATEGORY_COLORS[row.category] ?? '#333' }}>
          {row.category}
        </span>,
        dataIndex: `cat_${row.category}`,
        key: `cat_${row.category}`,
        width: 80,
        align: 'right' as const,
        render: (v: number) => v > 0
          ? <span style={{ fontSize: 13 }}>{v.toFixed(1)}</span>
          : <span style={{ color: '#ddd', fontSize: 12 }}>-</span>,
      })),
    ]

    // 計算各人員 × 各來源的實際工時（pct / 100 × category_total）
    const catTotals = personData.rows.map(row =>
      row.pct_by_person.reduce((s, p, i) => {
        // 反推 category total：total_person / (pct/100) 但用 person_totals 加總更準確
        // 直接使用每人合計 × pct/100 作為近似
        return s
      }, 0)
    )
    void catTotals // suppress unused warning

    const detailData = personData.persons.map((name, pi) => {
      const row: Record<string, number | string> = {
        key: name, name, rank: pi + 1, total: personData.person_totals[pi],
      }
      personData.rows.forEach(catRow => {
        // 各類別工時 = 人員在該類別的佔比 × 人員合計工時（近似，實際以 person_totals 為準）
        row[`cat_${catRow.category}`] = parseFloat(
          (catRow.pct_by_person[pi] / 100 * personData.person_totals[pi]).toFixed(1)
        )
      })
      return row
    })

    const maxTotal = Math.max(...personData.person_totals, 1)

    return (
      <>
        {rankingFilterCard}
        {/* 橫向工時 Bar Chart */}
        <Card
          title={<><BarChartOutlined /> {personYear}年 飯店部門人員工時排名（Top {personData.persons.length}）</>}
          size="small"
          bodyStyle={{ padding: '12px 16px' }}
          style={{ marginBottom: 12 }}
        >
          {barData.map((item, i) => (
            <div key={item.name} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <Text style={{ fontSize: 12, fontWeight: i < 3 ? 700 : 500 }}>
                  {item.medal} {i + 1}. {item.name}
                </Text>
                <Text strong style={{ fontSize: 12, color: BRAND_BLUE }}>
                  {item.total.toFixed(1)} HR
                </Text>
              </div>
              <div style={{ background: '#f5f5f5', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  width: `${(item.total / maxTotal) * 100}%`,
                  background: i === 0 ? 'linear-gradient(135deg, #667eea, #764ba2)'
                    : i === 1 ? BRAND_BLUE : i === 2 ? ACCENT_BLUE : '#8FB8D9',
                  height: 18,
                  borderRadius: 3,
                  transition: 'width 0.3s',
                }} />
              </div>
            </div>
          ))}
        </Card>

        {/* 明細表 */}
        <Card
          title="各來源工時明細"
          size="small"
          bodyStyle={{ padding: '8px' }}
        >
          <Table
            columns={detailCols}
            dataSource={detailData}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            style={{ fontSize: 14 }}
          />
        </Card>
      </>
    )
  }

  // ── Tab 設定 ──────────────────────────────────────────────────────────
  const tabItems = [
    {
      key: 'dashboard',
      label: <><DashboardOutlined /> Dashboard</>,
      children: (
        <>
          {/* ── 篩選列 ── */}
          <Card size="small" style={{ marginBottom: 16, background: '#f9fbff' }}>
            <Row gutter={[16, 8]} align="middle">
              <Col><Text type="secondary" style={{ fontSize: 12 }}>工務篩選：</Text></Col>
              <Col>
                <Select
                  value={year} options={yearOptions} style={{ width: 100 }}
                  onChange={(v) => { setYear(v) }}
                />
              </Col>
              <Col>
                <Select
                  value={month} options={monthOptions} style={{ width: 90 }}
                  onChange={(v) => { setMonth(v) }}
                />
              </Col>
              <Col><Divider type="vertical" /></Col>
              <Col><Text type="secondary" style={{ fontSize: 12 }}>巡檢日期：</Text></Col>
              <Col>
                <DatePicker
                  value={dayjs(targetDate, 'YYYY/MM/DD')}
                  format="YYYY/MM/DD"
                  allowClear={false}
                  onChange={(d) => {
                    if (d) {
                      const ds = d.format('YYYY/MM/DD')
                      setTargetDate(ds)
                      loadInspections(ds)
                    }
                  }}
                />
              </Col>
              <Col>
                <Button size="small" onClick={() => {
                  const t = dayjs().format('YYYY/MM/DD')
                  setTargetDate(t)
                  loadInspections(t)
                }}>今日</Button>
              </Col>
              <Col flex="auto" />
              <Col>
                <Button
                  icon={loading ? undefined : <ReloadOutlined />}
                  onClick={load}
                  loading={loading}
                >全部重新整理</Button>
              </Col>
            </Row>
          </Card>

          {/* ── 主管摘要 ── */}
          <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>
            主管摘要
          </Divider>
          <KpiAggregate />

          {/* ── 各來源本期狀態 ── */}
          <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>
            各來源本期狀態
          </Divider>
          <SourceCards />

          {/* ── 報修費用摘要 ── */}
          <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>
            報修費用摘要
            <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>（{year} 年 {ytdLabel}）</Text>
          </Divider>
          <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
            {/* 委外 + 維修費用 */}
            <Col xs={24} sm={8}>
              <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${ORANGE}` }} loading={loading}>
                {!dazhiData ? (
                  <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: 12 }}>數據準備中</div>
                ) : (
                  <>
                    <Statistic
                      title={
                        <Tooltip title={`委外費用 $${(dazhiData.kpi.annual_outsource_fee ?? 0).toLocaleString()} ／ 維修費用 $${(dazhiData.kpi.annual_maintenance_fee ?? 0).toLocaleString()}`}>
                          <span style={{ fontSize: 11, color: '#888', cursor: 'help' }}>
                            委外+維修費用（{ytdLabel}）<QuestionCircleOutlined style={{ color: '#bbb', marginLeft: 3 }} />
                          </span>
                        </Tooltip>
                      }
                      value={dazhiData.kpi.annual_fee ?? 0}
                      formatter={(v) => `$${Number(v).toLocaleString()}`}
                      valueStyle={{ fontSize: 20, fontWeight: 700, color: ORANGE }}
                      prefix={<DashboardOutlined style={{ fontSize: 14, marginRight: 4 }} />}
                    />
                    <div style={{ marginTop: 6, fontSize: 11, color: '#888' }}>
                      委外 <Text strong style={{ color: ORANGE }}>${(dazhiData.kpi.annual_outsource_fee ?? 0).toLocaleString()}</Text>
                      <Divider type="vertical" />
                      維修 <Text strong style={{ color: ORANGE }}>${(dazhiData.kpi.annual_maintenance_fee ?? 0).toLocaleString()}</Text>
                    </div>
                  </>
                )}
              </Card>
            </Col>

            {/* 扣款費用 */}
            <Col xs={24} sm={8}>
              <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #C0392B' }} loading={loading}>
                {!dazhiData ? (
                  <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: 12 }}>數據準備中</div>
                ) : (
                  <Statistic
                    title={<span style={{ fontSize: 11, color: '#888' }}>扣款費用（{ytdLabel}）</span>}
                    value={dazhiData.kpi.annual_deduction_fee ?? 0}
                    formatter={(v) => `$${Number(v).toLocaleString()}`}
                    valueStyle={{ fontSize: 20, fontWeight: 700, color: '#C0392B' }}
                    prefix={<ExclamationCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
                  />
                )}
              </Card>
            </Col>

            {/* 本月費用合計 */}
            <Col xs={24} sm={8}>
              <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #D4380D' }} loading={loading}>
                {!dazhiData ? (
                  <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: 12 }}>數據準備中</div>
                ) : (
                  <>
                    <Statistic
                      title={<span style={{ fontSize: 11, color: '#888' }}>本月費用合計（{month > 0 ? `${month}月` : '本年'}）</span>}
                      value={dazhiData.kpi.month_total_fee ?? 0}
                      formatter={(v) => `$${Number(v).toLocaleString()}`}
                      valueStyle={{ fontSize: 20, fontWeight: 700, color: '#D4380D' }}
                      prefix={<ToolOutlined style={{ fontSize: 14, marginRight: 4 }} />}
                    />
                    <div style={{ marginTop: 6, fontSize: 11, color: '#888' }}>
                      委外 <Text strong style={{ color: '#D4380D' }}>${(dazhiData.kpi.month_outsource_fee ?? 0).toLocaleString()}</Text>
                      <Divider type="vertical" />
                      維修 <Text strong style={{ color: '#D4380D' }}>${(dazhiData.kpi.month_maintenance_fee ?? 0).toLocaleString()}</Text>
                    </div>
                  </>
                )}
              </Card>
            </Col>
          </Row>

          {/* ── 決策分析圖表 ── */}
          <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>
            決策分析圖表
          </Divider>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {/* 各來源工項/案件數比較 */}
            <Col xs={24} lg={12}>
              <Card title={<><BarChartOutlined /> 各來源工項/案件數比較</>} size="small">
                {barData.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>暫無資料</div>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 30 }}>
                      <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <RcTooltip />
                      <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="工項數" name="工項/案件總數" radius={[0, 4, 4, 0]}>
                        {barData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Bar>
                      <Bar dataKey="完成數" fill={GREEN} opacity={0.7} radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </Col>

            {/* 各來源完成率比較 */}
            <Col xs={24} lg={12}>
              <Card title={<><BarChartOutlined /> 各來源完成率（%）</>} size="small">
                {rateBarData.length === 0 ? (
                  <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>暫無資料</div>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={rateBarData} layout="vertical" margin={{ left: 10, right: 30 }}>
                      <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} />
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <RcTooltip formatter={(v) => [`${v}%`, '完成率']} />
                      <Bar dataKey="完成率" radius={[0, 4, 4, 0]}>
                        {rateBarData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </Card>
            </Col>
          </Row>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} lg={16}><DazhiTrendChart /></Col>
            <Col xs={24} lg={8}><SourcePieChart /></Col>
          </Row>
        </>
      ),
    },
    {
      key: 'daily',
      label: <><BarChartOutlined /> B. 每日累計</>,
      children: (
        <Spin spinning={tabBLoading}>
          <TabBDaily />
        </Spin>
      ),
    },
    {
      key: 'monthly',
      label: <><LineChartOutlined /> C. 每月累計</>,
      children: (
        <Spin spinning={tabCLoading}>
          <TabCMonthly />
        </Spin>
      ),
    },
    {
      key: 'yearly',
      label: <><CalendarOutlined /> D. 每年累計</>,
      children: (
        <Spin spinning={tabYearlyLoading}>
          <TabDYearly />
        </Spin>
      ),
    },
    {
      key: 'person_pct',
      label: <><PieChartOutlined /> 人員工時%</>,
      children: (
        <Spin spinning={tabDLoading}>
          <div style={{ marginBottom: 8, fontSize: 12, color: '#888' }}>
            {year}年 — 六大來源 × Top-15 人員工時佔比
          </div>
          <TabDPerson />
        </Spin>
      ),
    },
    {
      key: 'ranking',
      label: <><BarChartOutlined /> 人員排名</>,
      children: (
        <Spin spinning={tabDLoading}>
          <TabRanking />
        </Spin>
      ),
    },
  ]

  // ════════════════════════════════════════════════════════════════════════
  // Render
  // ════════════════════════════════════════════════════════════════════════
  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { href: '/dashboard', title: <HomeOutlined /> },
          { title: NAV_GROUP.hotel },
          { title: NAV_PAGE.hotelMgmtDashboard },
        ]}
      />

      {/* 標題 + 篩選列 */}
      <Card bodyStyle={{ padding: '12px 16px' }} style={{ marginBottom: 12 }}>
        <Row justify="space-between" align="middle" gutter={[0, 8]}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              🏨 {NAV_PAGE.hotelMgmtDashboard}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              客房保養 · 週期保養 · IHG保養 · 每日巡檢 · 保全巡檢 · 工務 — 整合總覽
            </Text>
          </Col>
          <Col>
            <Space wrap>
              <Select value={year} options={yearOptions} onChange={setYear} style={{ width: 100 }} size="small" />
              <Select value={month} options={monthOptions} onChange={setMonth} style={{ width: 90 }} size="small" />
              <Tag color="default" style={{ fontSize: 11 }}>巡檢日期：{targetDate}</Tag>
              <Button
                size="small"
                icon={<FilePptOutlined />}
                loading={exportLoading}
                disabled={month === 0}
                style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', color: '#fff', border: 'none' }}
                onClick={async () => {
                  setExportLoading(true)
                  try {
                    const payload: HotelPptxPayload = {
                      kpi_summary: {
                        total_cases:      totalCases,
                        completed_cases:  totalCompleted,
                        total_work_hours: Math.round(totalWorkHours * 10) / 10,
                        abnormal_count:   totalAbnormal,
                        overdue_count:    totalOverdue,
                      },
                      source_cards: sources.map(s => ({
                        source_name:     s.source_name,
                        source_key:      s.source_key,
                        case_count:      Math.max(0, s.case_count),
                        completed_count: s.completed_count,
                        completion_rate: Math.round(s.completion_rate * 10) / 10,
                        abnormal_count:  s.abnormal_count,
                        overdue_count:   s.overdue_count,
                        work_hours:      Math.max(0, s.work_hours),
                        actual_hours:    s.actual_hours,
                      })),
                      repair_costs: {
                        outsource_fee:   dazhiData?.kpi.annual_outsource_fee   ?? 0,
                        maintenance_fee: dazhiData?.kpi.annual_maintenance_fee ?? 0,
                        deduction_fee:   dazhiData?.kpi.annual_deduction_fee   ?? 0,
                        month_total_fee: (dazhiData?.kpi.month_outsource_fee   ?? 0)
                                       + (dazhiData?.kpi.month_maintenance_fee ?? 0),
                        period_label:    ytdLabel,
                      },
                    }
                    await exportHotelOverviewPptx(year, month, payload)
                  } catch (e) {
                    console.error('PPTX export failed', e)
                  } finally {
                    setExportLoading(false)
                  }
                }}
              >
                匯出 PowerPoint
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 資料載入錯誤提示 */}
      {errors.length > 0 && (
        <Alert
          message={`以下模組資料載入失敗：${errors.join('、')}`}
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          closable
        />
      )}

      {/* 主體 */}
      <Spin spinning={loading}>
        <Tabs
          items={tabItems}
          size="small"
          onChange={handleTabChange}
          style={{ background: '#fff', padding: '0 12px 12px', borderRadius: 8 }}
        />
      </Spin>
    </div>
  )
}
