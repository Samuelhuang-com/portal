/**
 * 商場管理 Dashboard — 整合總覽（含 5 Tab）
 *
 * Tab 結構（對應 work-category-analysis 風格）：
 *   A. Dashboard    — 5 來源 KPI 卡片 + 各來源狀態卡 + 圖表
 *   B. 每日累計     — 商場工務報修：選月日別統計（occupied_at 聚合）
 *   C. 每月累計     — 商場 PM / 全棟 PM / 商場報修：月 × 來源完成率矩陣
 *   D. 人員工時%    — /mall/person-hours 五項來源人員工時佔比（Top-15）
 *   E. 人員排名     — /mall/person-hours 五項來源人員工時排名（Top-15）
 *
 * 資料說明：
 *   - Tab D/E 均使用 /mall/person-hours API（現場報修+上級交辦+緊急事件+例行維護+每日巡檢）
 *   - 不新增任何 Backend API，全部沿用既有 endpoint
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Row, Col, Card, Statistic, Typography, Breadcrumb,
  Select, Space, Tooltip, DatePicker, Button,
  Progress, Alert, Tag, Tabs, Table, Divider, Badge,
  Spin,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, ShopOutlined, DownloadOutlined,
  ClockCircleOutlined, WarningOutlined, CheckCircleOutlined,
  ExclamationCircleOutlined, BarChartOutlined, ToolOutlined,
  RightOutlined, DashboardOutlined, QuestionCircleOutlined,
  CalendarOutlined, SafetyOutlined, TrophyOutlined,
  TableOutlined, LineChartOutlined, TeamOutlined, FilePptOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, CartesianGrid,
  Tooltip as RcTooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'

// ── API ────────────────────────────────────────────────────────────────────────
import { fetchMallPMStats }                              from '@/api/mallPeriodicMaintenance'
import { fetchFullBldgPMStats }                          from '@/api/fullBuildingMaintenance'
import {
  fetchMallFacilityDashboardSummary,
  fetchMallFacilityMonthlyDashboard,
  type MallFIMonthlyDashboardSummary,
}                                                        from '@/api/mallFacilityInspection'
import {
  fetchDashboard as fetchLuqunDash,
} from '@/api/luqunRepair'
import {
  fetchOtherTaskStats,
  type OtherTaskTypeStat,
} from '@/api/otherTasks'
import { SourceStatusCard }              from '@/components/SourceStatusCard'
import {
  fetchMallDailyHours, fetchMallMonthlyHours, fetchMallPersonHours,
  exportMallOverviewPptx,
  MALL_CATEGORY_TAG_COLORS,
  type MallDailyHoursData, type MallDailyRow,
  type MallMonthlyHoursData, type MallMonthlyRow,
  type MallPersonHoursData, type MallPersonRow,
  type MallPptxPayload,
} from '@/api/mallOverview'

// ── Types ──────────────────────────────────────────────────────────────────────
import type { PMStats }                       from '@/types/periodicMaintenance'
import type { MallFIDashboardSummary }        from '@/api/mallFacilityInspection'
import type { DashboardData, RepairCase }     from '@/types/luqunRepair'

import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

// ── Normalize 共用型別 ────────────────────────────────────────────────────────
export interface NormalizedSummary {
  work_hours:       number   // 預估工時（planned_minutes / 60）
  actual_hours:     number   // 保養時間（actual_minutes / 60，實際 start–end 差值）
  case_count:       number
  completed_count:  number
  completion_rate:  number
  abnormal_count:   number
  overdue_count:    number
  is_placeholder:   boolean
  category_breakdown?: { name: string; count: number; rate: number }[]
}

// ── Normalize 型別 ─────────────────────────────────────────────────────────────
export interface SourceSummary {
  source_key:       string
  source_name:      string
  color:            string
  icon:             React.ReactNode
  route:            string
  work_hours:       number
  case_count:       number
  completed_count:  number
  completion_rate:  number
  abnormal_count:   number
  overdue_count:    number
  is_placeholder:   boolean
  category_breakdown?: { name: string; count: number; rate: number }[]
}

// ── 來源設定 ───────────────────────────────────────────────────────────────────
// 第一列：維護 / 巡檢類
const SOURCE_CONFIG_ROW1 = [
  { key: 'mall_pm',        label: '商場例行維護', color: '#1B3A5C', icon: <CalendarOutlined />, route: '/mall/periodic-maintenance',        showPmHours: true  },
  { key: 'full_bldg_pm',  label: '全棟例行維護', color: '#4BA8E8', icon: <ToolOutlined />,     route: '/mall/full-building-maintenance',   showPmHours: true  },
  { key: 'mall_facility', label: '商場工務巡檢', color: '#722ED1', icon: <SafetyOutlined />,   route: '/mall-facility-inspection/dashboard', showPmHours: false },
  { key: 'full_bldg_insp',label: '整棟巡檢',     color: '#52C41A', icon: <SafetyOutlined />,   route: '/full-building-inspection/dashboard', showPmHours: false },
] as const

// 第二列：報修 / 交辦 / 緊急事件
const SOURCE_CONFIG_ROW2 = [
  { key: 'luqun_repair',    label: '商場工務報修', color: '#FA8C16', icon: <WarningOutlined />,          route: '/luqun-repair/dashboard', showPmHours: false },
  { key: 'mall_supervisor', label: '商場主管交辦', color: '#C0392B', icon: <ExclamationCircleOutlined />, route: '/hotel/other-tasks', showPmHours: false },
  { key: 'mall_emergency',  label: '商場緊急事件', color: '#D4380D', icon: <WarningOutlined />,           route: '/hotel/other-tasks', showPmHours: false },
] as const

const SOURCE_CONFIG = [...SOURCE_CONFIG_ROW1, ...SOURCE_CONFIG_ROW2] as const

// ── Normalize 函式 ─────────────────────────────────────────────────────────────
function normalizePM(data: PMStats | null) {
  const kpi = data?.current_kpi
  return {
    work_hours:      kpi ? Math.round((kpi.planned_minutes / 60) * 10) / 10 : 0,
    actual_hours:    kpi ? Math.round(((kpi.actual_minutes ?? 0) / 60) * 10) / 10 : 0,
    case_count:      kpi?.total           ?? 0,
    completed_count: kpi?.completed       ?? 0,
    completion_rate: kpi?.completion_rate ?? 0,
    abnormal_count:  kpi?.abnormal        ?? 0,
    overdue_count:   kpi?.overdue         ?? 0,
    is_placeholder:  !data || !kpi,
    category_breakdown: data?.category_stats?.map(c => ({ name: c.category, count: c.total, rate: c.rate })),
  }
}

function normalizeFacility(data: MallFIDashboardSummary | null) {
  if (!data?.sheets?.length) return { work_hours: 0, actual_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: !data, category_breakdown: undefined }
  const sheets = data.sheets
  const total_items    = sheets.reduce((s, sh) => s + sh.total_items,    0)
  const checked_items  = sheets.reduce((s, sh) => s + sh.checked_items,  0)
  const abnormal_items = sheets.reduce((s, sh) => s + sh.abnormal_items + sh.pending_items, 0)
  const total_minutes  = sheets.reduce((s, sh) => s + (sh.total_minutes ?? 0), 0)
  return {
    work_hours:      Math.round((total_minutes / 60) * 10) / 10,
    actual_hours:    0,
    case_count:      total_items,
    completed_count: checked_items,
    completion_rate: total_items > 0 ? Math.round((checked_items / total_items) * 100) : 0,
    abnormal_count:  abnormal_items,
    overdue_count:   0,
    is_placeholder:  false,
    category_breakdown: sheets.map(sh => ({ name: sh.title, count: sh.total_items, rate: sh.completion_rate })),
  }
}

function normalizeFacilityMonthly(data: MallFIMonthlyDashboardSummary | null) {
  if (!data?.sheets?.length) return { work_hours: 0, actual_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: !data, category_breakdown: undefined }
  const sheets         = data.sheets
  const logged         = sheets.reduce((s, sh) => s + sh.month_count,  0)   // 本月登錄場次
  const missing        = sheets.reduce((s, sh) => s + sh.missing_count, 0)  // 缺漏天數
  const total_expected = logged + missing
  return {
    work_hours:      0,
    actual_hours:    0,
    case_count:      total_expected,    // 預期場次 = 已登 + 缺漏
    completed_count: logged,            // 實際登錄場次
    completion_rate: total_expected > 0 ? Math.round((logged / total_expected) * 100) : 0,
    abnormal_count:  missing,           // 缺漏天數（跨 Sheet 合計）
    overdue_count:   0,
    is_placeholder:  false,
    category_breakdown: sheets.map(sh => ({ name: sh.title, count: sh.month_count, rate: sh.has_data ? 100 : 0 })),
  }
}

function normalizeLuqun(data: DashboardData | null) {
  if (!data) return { work_hours: 0, actual_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: true, category_breakdown: undefined }
  const kpi = data.kpi
  const case_count = kpi.total
  return {
    work_hours:      Math.round((kpi.total_work_hours ?? 0) * 10) / 10,
    actual_hours:    0,
    case_count,
    completed_count: kpi.completed,
    completion_rate: case_count > 0 ? Math.round((kpi.completed / case_count) * 100) : 0,
    abnormal_count:  kpi.uncompleted,
    overdue_count:   0,
    is_placeholder:  false,
    category_breakdown: data.type_dist?.map(t => ({ name: t.type, count: t.count, rate: case_count > 0 ? Math.round((t.count / case_count) * 100) : 0 })),
  }
}

function normalizeOtherTask(stat: OtherTaskTypeStat | undefined): NormalizedSummary {
  if (!stat) return { work_hours: 0, actual_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: true }
  return {
    work_hours:      stat.work_hours,
    actual_hours:    0,
    case_count:      stat.total,
    completed_count: 0,
    completion_rate: 0,
    abnormal_count:  0,
    overdue_count:   0,
    is_placeholder:  false,
  }
}

// ── 來源卡片子元件 ─────────────────────────────────────────────────────────────
// SourceCard → 已移至 @/components/SourceStatusCard

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

// ── 每日累計 / 每月累計：Tag 渲染函式 ────────────────────────────────────────────
function renderMallCategory(val: string) {
  return <Tag color={MALL_CATEGORY_TAG_COLORS[val] ?? 'default'} style={{ fontSize: 13 }}>{val}</Tag>
}
function renderMallHour(v: number) {
  return <Text style={{ fontSize: 13, color: v > 0 ? '#1B3A5C' : '#ccc' }}>{v > 0 ? v.toFixed(1) : '-'}</Text>
}
function renderMallCase(v: number) {
  if (v === 0) return <Text style={{ fontSize: 13, color: '#ccc' }}>—</Text>
  return <Text style={{ fontSize: 13, color: '#1B3A5C', fontWeight: 600 }}>{v}</Text>
}

// ══════════════════════════════════════════════════════════════════════════════
// 主頁面
// ══════════════════════════════════════════════════════════════════════════════
export default function MallMgmtDashboardPage() {
  const navigate  = useNavigate()
  const thisYear  = dayjs().year()
  const thisMonth = dayjs().month() + 1

  // ── 篩選狀態 ──────────────────────────────────────────────────────────────
  const [year,       setYear]       = useState<number>(thisYear)
  const [month,      setMonth]      = useState<number>(thisMonth)
  const [targetDate, setTargetDate] = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [activeTab,  setActiveTab]  = useState('dashboard')

  // ── Tab A：5 來源原始資料 ──────────────────────────────────────────────────
  const [mallPmData,              setMallPmData]              = useState<PMStats | null>(null)
  const [fullBldgPmData,          setFullBldgPmData]          = useState<PMStats | null>(null)
  const [mallFacilityData,        setMallFacilityData]        = useState<MallFIDashboardSummary | null>(null)
  const [mallFacilityMonthlyData, setMallFacilityMonthlyData] = useState<MallFIMonthlyDashboardSummary | null>(null)
  const [luqunData,               setLuqunData]               = useState<DashboardData | null>(null)

  const [loadingMallPm,       setLoadingMallPm]       = useState(false)
  const [loadingFullBldgPm,   setLoadingFullBldgPm]   = useState(false)
  const [loadingMallFacility, setLoadingMallFacility] = useState(false)
  const [loadingLuqun,        setLoadingLuqun]        = useState(false)

  const [errorMallPm,       setErrorMallPm]       = useState<string | null>(null)
  const [errorFullBldgPm,   setErrorFullBldgPm]   = useState<string | null>(null)
  const [errorMallFacility, setErrorMallFacility] = useState<string | null>(null)
  const [errorLuqun,        setErrorLuqun]        = useState<string | null>(null)

  // ── Tab C：每月累計（5 工項每月工時交叉表）──────────────────────────────────────
  const [monthlyHoursData, setMonthlyHoursData] = useState<MallMonthlyHoursData | null>(null)
  const [loadingMonthly,   setLoadingMonthly]   = useState(false)
  const [monthlyYear,      setMonthlyYear]      = useState<number>(thisYear)

  // ── Tab D：人員工時%（5 工項 × 人員交叉表）──────────────────────────────────────
  const [personHoursData,  setPersonHoursData]  = useState<MallPersonHoursData | null>(null)
  const [loadingPerson,    setLoadingPerson]    = useState(false)
  const [personYear,       setPersonYear]       = useState<number>(thisYear)

  // ── Tab B：每日累計（5 工項每日工時交叉表）──────────────────────────────────
  const [dailyHoursData, setDailyHoursData] = useState<MallDailyHoursData | null>(null)
  const [loadingDaily,   setLoadingDaily]   = useState(false)
  const [dailyMonth,     setDailyMonth]     = useState<number>(thisMonth)
  const [dailyYear,      setDailyYear]      = useState<number>(thisYear)

  // ── Tab E：每年累計（多年 × 5 工項總工時交叉表）──────────────────────────────────
  const [yearlyData,     setYearlyData]     = useState<MallMonthlyHoursData | null>(null)
  const [loadingYearly,  setLoadingYearly]  = useState(false)
  const [yearlyYear,     setYearlyYear]     = useState<number>(thisYear)

  // ── 主管交辦／緊急事件 stats ──────────────────────────────────────────────────
  const [otherTasksStats,   setOtherTasksStats]   = useState<Record<string, OtherTaskTypeStat> | null>(null)
  const [loadingOtherTasks, setLoadingOtherTasks] = useState(false)
  const [errorOtherTasks,   setErrorOtherTasks]   = useState<string | null>(null)

  // ── 匯出狀態 ──────────────────────────────────────────────────────────────
  const [exportLoading, setExportLoading] = useState(false)

  // ── 載入 Tab A ─────────────────────────────────────────────────────────────
  const loadMallPm = useCallback(async (y?: number, m?: number) => {
    setLoadingMallPm(true); setErrorMallPm(null)
    const yr = (y ?? year).toString()
    const mo = m !== undefined ? m : month
    try     { setMallPmData(await fetchMallPMStats(yr, mo > 0 ? mo : undefined)) }
    catch   { setErrorMallPm('商場例行維護載入失敗') }
    finally { setLoadingMallPm(false) }
  }, [year, month])

  const loadFullBldgPm = useCallback(async (y?: number, m?: number) => {
    setLoadingFullBldgPm(true); setErrorFullBldgPm(null)
    const yr = (y ?? year).toString()
    const mo = m !== undefined ? m : month
    try     { setFullBldgPmData(await fetchFullBldgPMStats(yr, mo > 0 ? mo : undefined)) }
    catch   { setErrorFullBldgPm('全棟例行維護載入失敗') }
    finally { setLoadingFullBldgPm(false) }
  }, [year, month])

  const loadMallFacility = useCallback(async (dt?: string) => {
    setLoadingMallFacility(true); setErrorMallFacility(null)
    try     { setMallFacilityData(await fetchMallFacilityDashboardSummary(dt ?? targetDate)) }
    catch   { setErrorMallFacility('商場工務巡檢載入失敗') }
    finally { setLoadingMallFacility(false) }
  }, [targetDate])

  const loadMallFacilityByMonth = useCallback(async (y?: number, m?: number) => {
    setLoadingMallFacility(true); setErrorMallFacility(null)
    const yr = y ?? year
    const mo = m !== undefined ? m : month
    const monthStr = mo > 0
      ? `${yr}-${String(mo).padStart(2, '0')}`
      : undefined  // 無月份時使用後端預設（當月）
    try     { setMallFacilityMonthlyData(await fetchMallFacilityMonthlyDashboard(monthStr)) }
    catch   { setErrorMallFacility('商場工務巡檢載入失敗') }
    finally { setLoadingMallFacility(false) }
  }, [year, month])

  const loadLuqun = useCallback(async (y?: number, m?: number) => {
    setLoadingLuqun(true); setErrorLuqun(null)
    try     { setLuqunData(await fetchLuqunDash(y ?? year, m ?? month)) }
    catch   { setErrorLuqun('商場工務報修載入失敗') }
    finally { setLoadingLuqun(false) }
  }, [year, month])

  const loadOtherTasks = useCallback(async (y?: number, m?: number) => {
    setLoadingOtherTasks(true); setErrorOtherTasks(null)
    try     { setOtherTasksStats(await fetchOtherTaskStats({ year: y ?? year, month: m ?? month })) }
    catch   { setErrorOtherTasks('主管交辦／緊急事件載入失敗') }
    finally { setLoadingOtherTasks(false) }
  }, [year, month])

  const loadAll = useCallback(() => {
    loadMallPm(); loadFullBldgPm(); loadMallFacility(); loadMallFacilityByMonth()
    loadLuqun(); loadOtherTasks()
  }, [loadMallPm, loadFullBldgPm, loadMallFacility, loadMallFacilityByMonth, loadLuqun, loadOtherTasks])

  useEffect(() => { loadAll() }, []) // eslint-disable-line

  // ── 載入 Tab C（每月累計）：GET /api/v1/mall/monthly-hours ─────────────────
  const loadMonthlyHours = useCallback(async (y?: number) => {
    const yr = y ?? monthlyYear
    setLoadingMonthly(true)
    try {
      const data = await fetchMallMonthlyHours(yr)
      setMonthlyHoursData(data)
    } catch { setMonthlyHoursData(null) }
    finally { setLoadingMonthly(false) }
  }, [monthlyYear])

  // ── 載入 Tab D（人員工時%）：GET /api/v1/mall/person-hours ─────────────────
  const loadPersonHours = useCallback(async (y?: number) => {
    const yr = y ?? personYear
    setLoadingPerson(true)
    try {
      const data = await fetchMallPersonHours(yr)
      setPersonHoursData(data)
    } catch { setPersonHoursData(null) }
    finally { setLoadingPerson(false) }
  }, [personYear])

  // ── 載入 Tab B（每日累計）：GET /api/v1/mall/daily-hours ──────────────────
  const loadDailyHours = useCallback(async (y?: number, m?: number) => {
    const dy = y ?? dailyYear
    const dm = m ?? dailyMonth
    if (!dm) return
    setLoadingDaily(true)
    try {
      const data = await fetchMallDailyHours(dy, dm)
      setDailyHoursData(data)
    } catch { setDailyHoursData(null) }
    finally { setLoadingDaily(false) }
  }, [dailyYear, dailyMonth])

  // ── 載入 Tab E（每年累計）：單年份 Running Total ────────────────────────────
  const loadYearlyHours = useCallback(async (yr?: number) => {
    const y = yr ?? yearlyYear
    setLoadingYearly(true)
    try {
      const data = await fetchMallMonthlyHours(y)
      setYearlyData(data)
    } catch { setYearlyData(null) }
    finally { setLoadingYearly(false) }
  }, [yearlyYear])

  // Tab 切換時懶載入
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'monthly'    && !monthlyHoursData)              loadMonthlyHours()
    if (key === 'person_pct' && !personHoursData)               loadPersonHours()
    if (key === 'ranking'    && !personHoursData)               loadPersonHours()
    if (key === 'daily'      && !dailyHoursData)                loadDailyHours()
    if (key === 'yearly'     && !yearlyData)                loadYearlyHours()
  }

  // ── Normalize ──────────────────────────────────────────────────────────────
  const mallPmSummary       = useMemo(() => normalizePM(mallPmData),                               [mallPmData])
  const fullBldgPmSummary   = useMemo(() => normalizePM(fullBldgPmData),                           [fullBldgPmData])
  // 月份統計優先；若無月統計（尚未載入）則 fallback 到日統計
  const mallFacilitySummary = useMemo(
    () => mallFacilityMonthlyData
      ? normalizeFacilityMonthly(mallFacilityMonthlyData)
      : normalizeFacility(mallFacilityData),
    [mallFacilityMonthlyData, mallFacilityData]
  )
  const luqunSummary        = useMemo(() => normalizeLuqun(luqunData),             [luqunData])
  const placeholderSummary = useMemo((): NormalizedSummary => ({ work_hours: 0, actual_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: true, category_breakdown: undefined }), [])
  const fullBldgInspSummary = placeholderSummary

  const summaryMap: Record<string, NormalizedSummary> = {
    mall_pm:          mallPmSummary,
    full_bldg_pm:     fullBldgPmSummary,
    mall_facility:    mallFacilitySummary,
    full_bldg_insp:   fullBldgInspSummary,
    luqun_repair:     luqunSummary,
    mall_supervisor:  normalizeOtherTask(otherTasksStats?.['上級交辦']),
    mall_emergency:   normalizeOtherTask(otherTasksStats?.['緊急事件']),
  }
  const loadingMap: Record<string, boolean> = {
    mall_pm: loadingMallPm, full_bldg_pm: loadingFullBldgPm, mall_facility: loadingMallFacility,
    full_bldg_insp: false,  luqun_repair: loadingLuqun,
    mall_supervisor: loadingOtherTasks, mall_emergency: loadingOtherTasks,
  }
  const errorMap: Record<string, string | null> = {
    mall_pm: errorMallPm, full_bldg_pm: errorFullBldgPm, mall_facility: errorMallFacility,
    full_bldg_insp: null, luqun_repair: errorLuqun,
    mall_supervisor: errorOtherTasks, mall_emergency: errorOtherTasks,
  }

  // ── 彙總 KPI ───────────────────────────────────────────────────────────────
  const allSummaries   = [mallPmSummary, fullBldgPmSummary, mallFacilitySummary, luqunSummary]
  const totalCases     = allSummaries.reduce((s, x) => s + (x?.case_count      ?? 0), 0)
  const totalCompleted = allSummaries.reduce((s, x) => s + (x?.completed_count ?? 0), 0)
  const totalAbnormal  = allSummaries.reduce((s, x) => s + (x?.abnormal_count  ?? 0), 0)
  const totalOverdue   = allSummaries.reduce((s, x) => s + (x?.overdue_count   ?? 0), 0)
  const totalWorkHours = Math.round(allSummaries.reduce((s, x) => s + (x?.work_hours ?? 0), 0) * 10) / 10
  const overallRate    = totalCases > 0 ? Math.round((totalCompleted / totalCases) * 100) : 0
  const isAnyLoading   = Object.values(loadingMap).some(Boolean)

  // ── 圖表資料 ───────────────────────────────────────────────────────────────
  const barData = SOURCE_CONFIG.map(c => {
    const s = summaryMap[c.key as keyof typeof summaryMap]
    return { name: c.label, 工項數: s?.case_count ?? 0, 完成數: s?.completed_count ?? 0, fill: c.color }
  }).filter(d => d.工項數 > 0)

  const rateBarData = SOURCE_CONFIG.map(c => {
    const s = summaryMap[c.key as keyof typeof summaryMap]
    if (!s || s.is_placeholder) return null
    return { name: c.label, 完成率: s.completion_rate, fill: c.color }
  }).filter(Boolean) as { name: string; 完成率: number; fill: string }[]

  const pieData = SOURCE_CONFIG.map(c => {
    const s = summaryMap[c.key as keyof typeof summaryMap]
    return { name: c.label, value: s?.work_hours ?? 0, fill: c.color }
  }).filter(d => d.value > 0)

  const trendData = (luqunData?.trend_12m ?? []).map(t => ({
    label: t.label, 總案件: t.total, 已結案: t.completed,
  }))

  // ── Tab B：buildMallDailyCols 在 JSX 裡宣告（依 dailyHoursData 動態生成）──────

  // ── Tab C：buildMallMonthlyCols 在 JSX 裡宣告（依 monthlyHoursData 動態生成）─────

    // ── Tab D/E：人員資料（/mall/person-hours，五項來源）────────────────────────
  const personRanking = useMemo(() => {
    const persons = personHoursData?.persons ?? []
    const totals  = personHoursData?.person_totals ?? []
    const rows    = personHoursData?.rows ?? []
    const grand   = totals.reduce((s, h) => s + h, 0)
    return persons.map((name, i) => ({
      key:         i,
      rank:        i + 1,
      name,
      total_hours: totals[i] ?? 0,
      pct:         grand > 0 ? Math.round(((totals[i] ?? 0) / grand) * 1000) / 10 : 0,
      cats:        rows.map(r => ({ category: r.category, pct: r.pct_by_person[i] ?? 0 })),
    }))
  }, [personHoursData])

  const totalPersonHours = personHoursData?.person_totals?.reduce((s, h) => s + h, 0) ?? 0

  // 人員來源分解資料（供 TabRanking 堆疊 BarChart 使用，顯示順序為降冪 → reverse 後正確）
  const MALL_3CATS = ['現場報修', '例行維護', '每日巡檢'] as const
  const MALL_CAT_HEX: Record<string, string> = {
    '現場報修': '#FA8C16',
    '例行維護': '#1B3A5C',
    '每日巡檢': '#722ED1',
  }
  const breakdownData = useMemo(() =>
    [...personRanking].reverse().map(p => {
      const obj: Record<string, number | string> = { name: p.name }
      MALL_3CATS.forEach(cat => {
        const c = p.cats.find(c => c.category === cat)
        obj[cat] = c ? Math.round(p.total_hours * c.pct / 100 * 10) / 10 : 0
      })
      return obj
    })
  , [personRanking]) // eslint-disable-line

  // ── 費用摘要：直接從已載入的 luqunData 取 kpi ────────────────────────────────
  const kpi      = luqunData?.kpi ?? null
  const ytdLabel = month > 0 ? `累計至 ${month} 月` : '全年'

  // ── 篩選選項 ───────────────────────────────────────────────────────────────
  const yearOptions  = [2024, 2025, 2026, 2027].map(y => ({ value: y, label: `${y} 年` }))
  const monthOptions = [{ value: 0, label: '全年' }, ...Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: `${i + 1} 月` }))]
  const dailyMonthOptions = Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: `${i + 1} 月` }))

  // ── 各工項計算口徑說明（Tooltip，仿 hotel/overview）──────────────────────
  const ce = React.createElement
  const MALL_5CAT_TOOLTIPS: Record<string, React.ReactNode> = {
    現場報修: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      ce('b', null, '商場工務報修'), '（luqun-repair/dashboard）', ce('br'),
      '以 ', ce('code', null, '_stat_dt'), ' 口徑歸屬日期：', ce('br'),
      '・已結案且 ', ce('code', null, 'completed_at'), ' 有值 → 以 completed_at 歸屬', ce('br'),
      '・其餘 → 以 ', ce('code', null, 'occurred_at'), '（事件發生日）歸屬', ce('br'),
      '・排除狀態為「取消」的案件', ce('br'),
      ce('span', { style: { color: '#ccc', fontSize: 11 } },
        '已結案狀態：結案／已辦驗／已驗收／已結案／完修／已完成／完成'),
    ),
    上級交辦: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      ce('b', null, '主管交辦'), '（hotel/other-tasks，task_type = 上級交辦）', ce('br'),
      '以 ', ce('code', null, 'year / month'), ' 篩選建立日期歸屬', ce('br'),
      '件數 = 本期 上級交辦 筆數；工時 = SUM(work_hours)',
    ),
    緊急事件: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      ce('b', null, '緊急事件'), '（hotel/other-tasks，task_type = 緊急事件）', ce('br'),
      '以 ', ce('code', null, 'year / month'), ' 篩選建立日期歸屬', ce('br'),
      '件數 = 本期 緊急事件 筆數；工時 = SUM(work_hours)',
    ),
    例行維護: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      '① ', ce('b', null, '商場例行維護'), '（mall/periodic-maintenance）', ce('br'),
      '　以 ', ce('code', null, 'scheduled_date'), ' 落在目標月份的保養項目數', ce('br'),
      '② ', ce('b', null, '全棟例行維護'), '（mall/full-building-maintenance）', ce('br'),
      '　以 ', ce('code', null, 'scheduled_date'), ' 落在目標月份的保養項目數', ce('br'),
      ce('b', null, '總和 = ①＋②'),
    ),
    每日巡檢: ce('div', { style: { fontSize: 12, lineHeight: 1.9 } },
      '① ', ce('b', null, '商場工務巡檢'), '（mall-facility-inspection）', ce('br'),
      '　與 Dashboard 相同計算方式：每天 = 實際登錄場次 + 缺漏場次', ce('br'),
      '　共 5 張巡檢表（4F / 3F / 1F~3F / 1F / B1F~B4F），每表每天應巡一次', ce('br'),
      '　過去月份所有天均計入；當月僅計至今日', ce('br'),
      '② ', ce('b', null, '整棟巡檢'), '（full-building-inspection）', ce('br'),
      '　以實際 ', ce('code', null, 'inspection_date'), ' 批次數計算', ce('br'),
      ce('b', null, '總和 = ①＋②'),
    ),
  }

  // ── PPTX 匯出 ────────────────────────────────────────────────────────────
  const handleExportPptx = async () => {
    setExportLoading(true)
    try {
      const source_cards = SOURCE_CONFIG.map(cfg => {
        const s = summaryMap[cfg.key] ?? { case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, work_hours: 0, actual_hours: 0 }
        return {
          source_name:     cfg.label,
          source_key:      cfg.key,
          case_count:      s.case_count,
          completed_count: s.completed_count,
          completion_rate: s.completion_rate,
          abnormal_count:  s.abnormal_count,
          overdue_count:   s.overdue_count,
          work_hours:      s.work_hours,
          actual_hours:    s.actual_hours ?? 0,
        }
      })
      const payload: MallPptxPayload = {
        kpi_summary: {
          total_cases:      totalCases,
          completed_cases:  totalCompleted,
          total_work_hours: totalWorkHours,
          abnormal_count:   totalAbnormal,
          overdue_count:    totalOverdue,
        },
        source_cards,
        repair_costs: {
          outsource_fee:   kpi?.annual_outsource_fee   ?? 0,
          maintenance_fee: kpi?.annual_maintenance_fee ?? 0,
          deduction_fee:   kpi?.annual_deduction_fee   ?? 0,
          month_total_fee: (kpi?.annual_outsource_fee ?? 0) + (kpi?.annual_maintenance_fee ?? 0),
          period_label:    ytdLabel,
        },
      }
      await exportMallOverviewPptx(year, month > 0 ? month : new Date().getMonth() + 1, payload)
    } catch (e) {
      console.error('PPTX 匯出失敗', e)
    } finally {
      setExportLoading(false)
    }
  }

  // ════════════════════════════════════════════════════════════════════════════
  // TAB A：Dashboard 總覽
  // ════════════════════════════════════════════════════════════════════════════
  const TabDashboard = (
    <>
      {/* 篩選列 */}
      <Card size="small" style={{ marginBottom: 16, background: '#f9fbff' }}>
        <Row gutter={[16, 8]} align="middle">
          <Col><Text type="secondary" style={{ fontSize: 14 }}>工務篩選：</Text></Col>
          <Col>
            <Select value={year} options={yearOptions} style={{ width: 100 }}
              onChange={(v) => {
                setYear(v)
                loadMallPm(v, month); loadFullBldgPm(v, month)
                loadMallFacilityByMonth(v, month); loadLuqun(v, month)
              }}
            />
          </Col>
          <Col>
            <Select value={month} options={monthOptions} style={{ width: 90 }}
              onChange={(v) => {
                setMonth(v)
                loadMallPm(year, v); loadFullBldgPm(year, v)
                loadMallFacilityByMonth(year, v); loadLuqun(year, v)
              }}
            />
          </Col>
          <Col><Divider type="vertical" /></Col>
          <Col><Text type="secondary" style={{ fontSize: 14 }}>巡檢日期：</Text></Col>
          <Col>
            <DatePicker
              value={dayjs(targetDate, 'YYYY/MM/DD')} format="YYYY/MM/DD" allowClear={false}
              onChange={(d) => { if (d) { const ds = d.format('YYYY/MM/DD'); setTargetDate(ds); loadMallFacility(ds) } }}
            />
          </Col>
          <Col>
            <Button size="small" onClick={() => { const t = dayjs().format('YYYY/MM/DD'); setTargetDate(t); loadMallFacility(t) }}>今日</Button>
          </Col>
          <Col flex="auto" />
          <Col>
            <Button icon={isAnyLoading ? undefined : <ReloadOutlined />} onClick={loadAll} loading={isAnyLoading}>全部重新整理</Button>
          </Col>
        </Row>
      </Card>

      {/* 彙總 KPI */}
      <Divider orientation="left" plain style={{ fontSize: 15, color: '#888', margin: '4px 0 12px' }}>主管摘要</Divider>
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #1B3A5C' }}>
            <Statistic
              title={<Tooltip title="商場例行維護 + 全棟例行維護 + 商場工務巡檢 + 整棟巡檢 + 商場工務報修之工項/案件總和"><span style={{ fontSize: 13, color: '#888', cursor: 'help' }}>本期總工項 <QuestionCircleOutlined style={{ color: '#bbb' }} /></span></Tooltip>}
              value={totalCases} suffix="筆"
              valueStyle={{ fontSize: 24, color: '#1B3A5C', fontWeight: 700 }}
              prefix={<BarChartOutlined style={{ fontSize: 16, marginRight: 4 }} />}
            />
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #52C41A' }}>
            <Statistic title={<Text style={{ fontSize: 13, color: '#888' }}>已完成工項</Text>} value={totalCompleted} suffix="筆"
              valueStyle={{ fontSize: 24, fontWeight: 700, color: '#52C41A' }}
              prefix={<CheckCircleOutlined style={{ fontSize: 16, marginRight: 4 }} />}
            />
            <Text type="secondary" style={{ fontSize: 13 }}>完成率 {overallRate}%</Text>
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #FA8C16' }}>
            <Statistic
              title={<Tooltip title="PM 實際保養工時（start/end_time）+ 巡檢工時 + 商場報修工時"><span style={{ fontSize: 13, color: '#888', cursor: 'help' }}>本期工時合計 <QuestionCircleOutlined style={{ color: '#bbb' }} /></span></Tooltip>}
              value={totalWorkHours} suffix="HR"
              valueStyle={{ fontSize: 24, fontWeight: 700, color: '#FA8C16' }}
              prefix={<ClockCircleOutlined style={{ fontSize: 16, marginRight: 4 }} />}
            />
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${totalAbnormal > 0 ? '#FF4D4F' : '#52C41A'}` }}>
            <Statistic title={<Text style={{ fontSize: 13, color: '#888' }}>異常/未結案件</Text>} value={totalAbnormal} suffix="件"
              valueStyle={{ fontSize: 24, fontWeight: 700, color: totalAbnormal > 0 ? '#FF4D4F' : '#52C41A' }}
              prefix={<WarningOutlined style={{ fontSize: 16, marginRight: 4 }} />}
            />
            {totalAbnormal === 0 && <Tag color="success" style={{ marginTop: 4, fontSize: 13 }}>全部正常</Tag>}
          </Card>
        </Col>
        <Col flex="1">
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${totalOverdue > 0 ? '#C0392B' : '#52C41A'}` }}>
            <Statistic title={<Text style={{ fontSize: 13, color: '#888' }}>逾期未保養</Text>} value={totalOverdue} suffix="項"
              valueStyle={{ fontSize: 24, fontWeight: 700, color: totalOverdue > 0 ? '#C0392B' : '#52C41A' }}
              prefix={<ExclamationCircleOutlined style={{ fontSize: 16, marginRight: 4 }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* 各來源卡片 — 第一列：維護 / 巡檢 */}
      <Divider orientation="left" plain style={{ fontSize: 15, color: '#888', margin: '4px 0 12px' }}>各來源本期狀態</Divider>
      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        {SOURCE_CONFIG_ROW1.map((cfg) => {
          const s = summaryMap[cfg.key]
          return (
            <Col key={cfg.key} xs={24} sm={12} md={6}>
              <SourceStatusCard
                source_key={cfg.key}
                source_name={cfg.label}
                source_color={cfg.color}
                case_count={s?.case_count ?? 0}
                completed_count={s?.completed_count ?? 0}
                work_hours={s?.work_hours ?? 0}
                actual_hours={cfg.showPmHours ? (s?.actual_hours ?? 0) : undefined}
                completion_rate={s?.completion_rate ?? 0}
                abnormal_count={s?.abnormal_count ?? 0}
                overdue_count={s?.overdue_count ?? 0}
                status_label={`完成率 ${(s?.completion_rate ?? 0).toFixed(1)}%`}
                is_placeholder={s?.is_placeholder ?? true}
                loading={loadingMap[cfg.key]}
                error={errorMap[cfg.key]}
                onClick={() => navigate(cfg.route)}
                icon={cfg.icon}
                cardSize="small"
                titleFontSize={16}
                statFontSize={22}
                infoFontSize={17}
              />
            </Col>
          )
        })}
      </Row>
      {/* 各來源卡片 — 第二列：報修 / 交辦 / 緊急事件 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {SOURCE_CONFIG_ROW2.map((cfg) => {
          const s = summaryMap[cfg.key]
          return (
            <Col key={cfg.key} xs={24} sm={12} md={8}>
              <SourceStatusCard
                source_key={cfg.key}
                source_name={cfg.label}
                source_color={cfg.color}
                case_count={s?.case_count ?? 0}
                completed_count={s?.completed_count ?? 0}
                work_hours={s?.work_hours ?? 0}
                actual_hours={cfg.showPmHours ? (s?.actual_hours ?? 0) : undefined}
                completion_rate={s?.completion_rate ?? 0}
                abnormal_count={s?.abnormal_count ?? 0}
                overdue_count={s?.overdue_count ?? 0}
                status_label={`完成率 ${(s?.completion_rate ?? 0).toFixed(1)}%`}
                is_placeholder={s?.is_placeholder ?? true}
                loading={loadingMap[cfg.key]}
                error={errorMap[cfg.key]}
                onClick={() => navigate(cfg.route)}
                icon={cfg.icon}
                cardSize="small"
                titleFontSize={16}
                statFontSize={22}
                infoFontSize={17}
              />
            </Col>
          )
        })}
      </Row>

      {/* 商場報修費用摘要（商場工務 luqun-repair dashboard kpi）*/}
      <Divider orientation="left" plain style={{ fontSize: 15, color: '#888', margin: '4px 0 12px' }}>
        商場報修費用摘要
        <Text type="secondary" style={{ fontSize: 13, marginLeft: 8 }}>（{year} 年 {ytdLabel}）</Text>
      </Divider>
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {/* 委外 + 維修費用 */}
        <Col xs={24} sm={8}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #FA8C16' }} loading={loadingLuqun}>
            {!kpi ? (
              <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: 14 }}>數據準備中</div>
            ) : (
              <>
                <Statistic
                  title={
                    <Tooltip title={`委外費用 $${(kpi.annual_outsource_fee ?? 0).toLocaleString()} ／ 維修費用 $${(kpi.annual_maintenance_fee ?? 0).toLocaleString()}`}>
                      <span style={{ fontSize: 13, color: '#888', cursor: 'help' }}>
                        委外+維修費用（{ytdLabel}）<QuestionCircleOutlined style={{ color: '#bbb', marginLeft: 3 }} />
                      </span>
                    </Tooltip>
                  }
                  value={kpi.annual_fee ?? 0}
                  formatter={(v) => `$${Number(v).toLocaleString()}`}
                  valueStyle={{ fontSize: 22, fontWeight: 700, color: '#FA8C16' }}
                  prefix={<DashboardOutlined style={{ fontSize: 16, marginRight: 4 }} />}
                />
                <div style={{ marginTop: 6, fontSize: 13, color: '#888' }}>
                  委外 <Text strong style={{ color: '#FA8C16' }}>${(kpi.annual_outsource_fee ?? 0).toLocaleString()}</Text>
                  <Divider type="vertical" />
                  維修 <Text strong style={{ color: '#FA8C16' }}>${(kpi.annual_maintenance_fee ?? 0).toLocaleString()}</Text>
                </div>
              </>
            )}
          </Card>
        </Col>

        {/* 扣款費用 */}
        <Col xs={24} sm={8}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #C0392B' }} loading={loadingLuqun}>
            {!kpi ? (
              <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: 14 }}>數據準備中</div>
            ) : (
              <Statistic
                title={<span style={{ fontSize: 13, color: '#888' }}>扣款費用（{ytdLabel}）</span>}
                value={kpi.annual_deduction_fee ?? 0}
                formatter={(v) => `$${Number(v).toLocaleString()}`}
                valueStyle={{ fontSize: 22, fontWeight: 700, color: '#C0392B' }}
                prefix={<ExclamationCircleOutlined style={{ fontSize: 16, marginRight: 4 }} />}
              />
            )}
          </Card>
        </Col>

        {/* 扣款專櫃 */}
        <Col xs={24} sm={8}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #D4380D' }} loading={loadingLuqun}>
            {!kpi ? (
              <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: 14 }}>數據準備中</div>
            ) : (
              <>
                <Statistic
                  title={
                    <Tooltip title={(kpi.annual_counter_store_names ?? []).length > 0
                      ? (kpi.annual_counter_store_names ?? []).join('、')
                      : '本期無扣款專櫃'}>
                      <span style={{ fontSize: 13, color: '#888', cursor: 'help' }}>
                        扣款專櫃（{ytdLabel}）<QuestionCircleOutlined style={{ color: '#bbb', marginLeft: 3 }} />
                      </span>
                    </Tooltip>
                  }
                  value={kpi.annual_counter_stores ?? 0}
                  suffix="家"
                  valueStyle={{ fontSize: 22, fontWeight: 700, color: '#D4380D' }}
                  prefix={<ShopOutlined style={{ fontSize: 16, marginRight: 4 }} />}
                />
                <div style={{ marginTop: 6, fontSize: 13, color: '#888' }}>
                  扣款合計 <Text strong style={{ color: '#D4380D' }}>${(kpi.annual_counter_fee ?? 0).toLocaleString()}</Text>
                </div>
              </>
            )}
          </Card>
        </Col>
      </Row>

      {/* 決策圖表 */}
      <Divider orientation="left" plain style={{ fontSize: 15, color: '#888', margin: '4px 0 12px' }}>決策分析圖表</Divider>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={<><BarChartOutlined /> 各來源工項/案件數比較</>} size="small">
            {barData.length === 0 ? <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>暫無資料</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 30 }}>
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 13 }} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 13 }} />
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <RcTooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 13 }} />
                  <Bar dataKey="工項數" name="工項/案件總數" radius={[0, 4, 4, 0]}>
                    {barData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Bar>
                  <Bar dataKey="完成數" fill="#52C41A" opacity={0.7} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={<><BarChartOutlined /> 各來源完成率（%）</>} size="small">
            {rateBarData.length === 0 ? <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>暫無資料</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={rateBarData} layout="vertical" margin={{ left: 10, right: 30 }}>
                  <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 13 }} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 13 }} />
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
        <Col xs={24} lg={16}>
          <Card title={<><LineChartOutlined /> 商場報修 — 12 個月案件趨勢</>} size="small"
            extra={<Text type="secondary" style={{ fontSize: 13 }}>{year} 年{month > 0 ? ` ${month} 月` : '（全年）'}</Text>}>
            {trendData.length === 0 || loadingLuqun ? (
              <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>{loadingLuqun ? '載入中…' : '暫無資料'}</div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendData} margin={{ left: 0, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 13 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 13 }} />
                  <RcTooltip /><Legend iconSize={10} wrapperStyle={{ fontSize: 14 }} />
                  <Line type="monotone" dataKey="總案件" stroke="#FA8C16" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  <Line type="monotone" dataKey="已結案" stroke="#52C41A" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={<><BarChartOutlined /> 各來源工時占比</>} size="small"
            extra={<Tooltip title="PM 工時為實際保養時間（start/end_time）；報修為 Ragic 花費工時欄位；巡檢為記錄工時"><QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} /></Tooltip>}>
            {pieData.length === 0 ? <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>暫無工時資料</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75}>
                    {pieData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Pie>
                  <RcTooltip formatter={(v, n) => [`${v} HR`, n]} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 13 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      <Alert type="info" showIcon message="資料說明"
        description={<ul style={{ margin: 0, paddingLeft: 20, fontSize: 14 }}>
          <li>工時口徑：PM 為實際保養工時（start/end_time）；商場工務巡檢為巡檢工時記錄；商場工務報修為 Ragic 花費工時欄位。</li>
          <li>各來源資料為獨立統計，不重複計算。</li>
          <li>整棟巡檢已納入每日巡檢統計；若無記錄則不計入。</li>
        </ul>}
      />
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // TAB B：每日累計（5 工項 × 每日工時交叉表，比照 work-category-analysis）
  // ════════════════════════════════════════════════════════════════════════════
  function buildMallDailyCols(): ColumnsType<MallDailyRow & { key: number }> {
    const { days = [], weekdays = [] } = dailyHoursData ?? {}
    return [
      {
        title: '工項類別', dataIndex: 'category', fixed: 'left' as const, width: 100,
        render: renderMallCategory,
      },
      ...days.map((d, i) => ({
        title: (
          <div style={{ textAlign: 'center' as const, lineHeight: 1.2 }}>
            <div style={{ fontSize: 12 }}>{d}</div>
            <div style={{ fontSize: 11, color: '#888' }}>{weekdays[i]}</div>
          </div>
        ),
        key: `d${d}`, width: 38, align: 'center' as const,
        render: (_: unknown, row: MallDailyRow & { key: number }) =>
          renderMallCase(row.cases?.[i] ?? 0),
      })),
      {
        title: '合計', dataIndex: 'cases_total', key: 'cases_total', width: 62, align: 'center' as const,
        render: (v: number, row: MallDailyRow & { key: number }) => (
          <Text strong style={{ color: row.category === 'TOTAL' ? '#1B3A5C' : '#333', fontSize: 13 }}>
            {v ?? 0}
          </Text>
        ),
      },
      {
        title: '%', dataIndex: 'cases_pct', key: 'cases_pct', width: 54, align: 'center' as const,
        render: (v: number, row: MallDailyRow & { key: number }) => (
          <Text style={{
            color: row.category === 'TOTAL' ? '#888' : '#FA8C16',
            fontWeight: row.category !== 'TOTAL' ? 600 : 400,
            fontSize: 13,
          }}>
            {(v ?? 0).toFixed(1)}%
          </Text>
        ),
      },
    ]
  }

  const TabDaily = (
    <>
      {/* 控制列 */}
      <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
        <Row gutter={[12, 8]} align="middle">
          <Col><Text strong style={{ fontSize: 15 }}>每日累計案件數</Text></Col>
          <Col>
            <Select value={dailyYear} options={yearOptions} style={{ width: 100 }}
              onChange={(v) => { setDailyYear(v); loadDailyHours(v, dailyMonth) }} />
          </Col>
          <Col>
            <Select value={dailyMonth} options={dailyMonthOptions} style={{ width: 90 }}
              onChange={(v) => { setDailyMonth(v); loadDailyHours(dailyYear, v) }} />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => loadDailyHours()} loading={loadingDaily}>
              重新整理
            </Button>
          </Col>
          <Col flex="auto" />
          <Col>
            <Button
              icon={<DownloadOutlined />}
              size="small"
              disabled={!dailyHoursData}
              onClick={() => {
                if (!dailyHoursData) return
                const headers = ['工項類別', ...dailyHoursData.days.map(d => `${d}日`), '案件數', '%']
                const rows = dailyHoursData.rows.map(r => [
                  r.category,
                  ...dailyHoursData.days.map((_, i) => r.cases?.[i] ?? 0),
                  r.cases_total,
                  `${(r.cases_pct ?? 0).toFixed(1)}%`,
                ])
                exportCSV(`商場管理_每日累計_${dailyYear}年${dailyMonth}月.csv`, headers, rows)
              }}
            >匯出 CSV</Button>
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 14 }}>{dailyYear} 年 {dailyMonth} 月</Text>
          </Col>
        </Row>
      </Card>

      {/* 工項說明 Badge 列 */}
      <Space wrap style={{ marginBottom: 12 }}>
        {(['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢'] as const).map(cat => (
          <Space key={cat} size={2}>
            {renderMallCategory(cat)}
            <Tooltip title={MALL_5CAT_TOOLTIPS[cat]} overlayStyle={{ maxWidth: 440 }}>
              <Text style={{ fontSize: 11, cursor: 'help', color: '#bbb' }}>ⓘ</Text>
            </Tooltip>
          </Space>
        ))}
        <Text type="secondary" style={{ fontSize: 13 }}>
          上級交辦 <Text strong style={{ color: '#C0392B' }}>{otherTasksStats?.['上級交辦']?.total ?? '—'} 件</Text>
          {' ／ '}
          緊急事件 <Text strong style={{ color: '#D4380D' }}>{otherTasksStats?.['緊急事件']?.total ?? '—'} 件</Text>
        </Text>
      </Space>

      <Spin spinning={loadingDaily}>
        {(!dailyHoursData || !dailyHoursData.days.length) && !loadingDaily ? (
          <Alert message="請選擇月份以查看每日累計案件數" type="info" showIcon style={{ marginTop: 8 }} />
        ) : (
          <Card
            title={
              <Space size={8} align="center">
                <Text strong>每日累計案件數</Text>
                <Tooltip title="現場報修件數：已結案以完工日計算，未結案以報修日計算。與 Dashboard 工作量（含前期尚未結案）計算方式不同，數字會有出入。">
                  <Text style={{ fontSize: 12, color: '#999', cursor: 'help' }}>ⓘ 計算說明</Text>
                </Tooltip>
              </Space>
            }
            extra={<Text type="secondary">{dailyYear} 年 {dailyMonth} 月</Text>}
            bodyStyle={{ padding: '6px 0' }}
          >
            <Table<MallDailyRow & { key: number }>
              dataSource={(dailyHoursData?.rows ?? []).map((r, i) => ({ ...r, key: i }))}
              columns={buildMallDailyCols()}
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
              rowClassName={(r) => r.category === 'TOTAL' ? 'mall-daily-total-row' : ''}
            />
          </Card>
        )}
      </Spin>
      <style>{`.mall-daily-total-row td { background: #f5f5f5 !important; font-weight: 600; }`}</style>
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // TAB C：每月累計（5 工項 × 12 月工時交叉表）
  // ════════════════════════════════════════════════════════════════════════════

  function buildMallMonthlyCols(): ColumnsType<MallMonthlyRow> {
    return [
      {
        title: '工項類別', dataIndex: 'category', fixed: 'left', width: 100,
        render: renderMallCategory,
      },
      ...Array.from({ length: 12 }, (_, i) => {
        const m = i + 1
        const isFuture = monthlyYear > thisYear || (monthlyYear === thisYear && m > thisMonth)
        return {
          title: `${m}月`,
          key:   `m${m}`,
          width: 58,
          align: 'center' as const,
          render: (_: unknown, row: MallMonthlyRow) =>
            isFuture
              ? <Text style={{ color: '#ccc', fontSize: 13 }}>—</Text>
              : renderMallCase(row.cases?.[i] ?? 0),
        }
      }),
      {
        title: '合計', dataIndex: 'cases_total', key: 'cases_total', width: 64, align: 'center' as const,
        render: (v: number, row: MallMonthlyRow) => (
          <Text strong style={{ color: row.category === 'TOTAL' ? '#1B3A5C' : '#333', fontSize: 13 }}>
            {v ?? 0}
          </Text>
        ),
      },
      {
        title: '%', dataIndex: 'cases_pct', key: 'cases_pct', width: 56, align: 'center' as const,
        render: (v: number, row: MallMonthlyRow) => (
          <Text style={{
            color:      row.category === 'TOTAL' ? '#888' : '#FA8C16',
            fontWeight: row.category !== 'TOTAL' ? 600 : 400,
            fontSize:   13,
          }}>
            {(v ?? 0).toFixed(1)}%
          </Text>
        ),
      },
    ]
  }

  const TabMonthly = (
    <>
      <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
        <Row gutter={[12, 8]} align="middle">
          <Col><Text strong style={{ fontSize: 15 }}>每月累計案件數</Text></Col>
          <Col>
            <Select
              value={monthlyYear}
              options={yearOptions}
              style={{ width: 100 }}
              onChange={(v) => { setMonthlyYear(v); loadMonthlyHours(v) }}
            />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => loadMonthlyHours()} loading={loadingMonthly}>
              重新整理
            </Button>
          </Col>
          <Col flex="auto" />
          <Col>
            <Button
              icon={<DownloadOutlined />}
              size="small"
              disabled={!monthlyHoursData}
              onClick={() => {
                if (!monthlyHoursData) return
                const headers = ['工項類別', ...Array.from({length:12}, (_,i)=>`${i+1}月`), '案件數', '%']
                const rows = monthlyHoursData.rows.map(r => [
                  r.category,
                  ...Array.from({length:12}, (_,i) => r.cases?.[i] ?? 0),
                  r.cases_total,
                  `${(r.cases_pct ?? 0).toFixed(1)}%`,
                ])
                exportCSV(`商場管理_每月累計_${monthlyYear}年.csv`, headers, rows)
              }}
            >匯出 CSV</Button>
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 14 }}>{monthlyYear} 年</Text>
          </Col>
        </Row>
      </Card>

      <Space wrap style={{ marginBottom: 12 }}>
        {(['現場報修','上級交辦','緊急事件','例行維護','每日巡檢'] as const).map(cat => (
          <Space key={cat} size={2}>
            {renderMallCategory(cat)}
            <Tooltip title={MALL_5CAT_TOOLTIPS[cat]} overlayStyle={{ maxWidth: 440 }}>
              <Text style={{ fontSize: 11, cursor: 'help', color: '#bbb' }}>ⓘ</Text>
            </Tooltip>
          </Space>
        ))}
        <Text type="secondary" style={{ fontSize: 13 }}>
          上級交辦 <Text strong style={{ color: '#C0392B' }}>{otherTasksStats?.['上級交辦']?.total ?? '—'} 件 / {otherTasksStats?.['上級交辦']?.work_hours ?? '—'} HR</Text>
          {' ／ '}
          緊急事件 <Text strong style={{ color: '#D4380D' }}>{otherTasksStats?.['緊急事件']?.total ?? '—'} 件 / {otherTasksStats?.['緊急事件']?.work_hours ?? '—'} HR</Text>
        </Text>
      </Space>

      <Spin spinning={loadingMonthly}>
        {!monthlyHoursData && !loadingMonthly ? (
          <Alert message="請選擇年份以查看每月累計案件數" type="info" showIcon />
        ) : (
          <Card
            title={
              <Space size={8} align="center">
                <Text strong>每月累計案件數</Text>
                <Tooltip title="現場報修件數：已結案以完工月計算，未結案以報修月計算。與 Dashboard 工作量（含前期尚未結案）計算方式不同，數字會有出入。">
                  <Text style={{ fontSize: 12, color: '#999', cursor: 'help' }}>ⓘ 計算說明</Text>
                </Tooltip>
              </Space>
            }
            extra={<Text type="secondary">{monthlyYear} 年</Text>}
            bodyStyle={{ padding: '6px 0' }}
          >
            <Table
              dataSource={(monthlyHoursData?.rows ?? []).map((r, i) => ({ ...r, key: i }))}
              columns={buildMallMonthlyCols()}
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
              rowClassName={(r: MallMonthlyRow) => r.category === 'TOTAL' ? 'mall-monthly-total-row' : ''}
            />
          </Card>
        )}
      </Spin>
      <style>{`.mall-monthly-total-row td { background: #f5f5f5 !important; font-weight: 600; }`}</style>
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // TAB E：每年累計（單年 Running Total — 比照 hotel/overview TabDYearly）
  // ════════════════════════════════════════════════════════════════════════════

  type MallRow5Y = { key: string; category: string; cases: number[]; total: number; cases_pct: number }

  function buildMallYearlyCols(): ColumnsType<MallRow5Y> {
    return [
      {
        title: '工項類別', dataIndex: 'category', fixed: 'left' as const, width: 100,
        render: renderMallCategory,
      },
      ...Array.from({ length: 12 }, (_, i) => {
        const m = i + 1
        const isFuture = yearlyYear > thisYear || (yearlyYear === thisYear && m > thisMonth)
        return {
          title: `${m}月`,
          key:   `m${m}`,
          width: 60,
          align: 'center' as const,
          render: (_: unknown, row: MallRow5Y) =>
            isFuture
              ? <Text style={{ color: '#ccc', fontSize: 13 }}>—</Text>
              : <Text style={{ fontSize: 13, color: row.category === 'TOTAL' ? '#1B3A5C' : '#333', fontWeight: row.category === 'TOTAL' ? 700 : 400 }}>
                  {row.cases?.[i] ?? 0}
                </Text>,
        }
      }),
      {
        title: '案件數', dataIndex: 'total', key: 'total', width: 68, align: 'center' as const,
        render: (v: number, row: MallRow5Y) => (
          <Text strong style={{ color: row.category === 'TOTAL' ? '#1B3A5C' : '#333', fontSize: 13 }}>{v ?? 0}</Text>
        ),
      },
      {
        title: '%', dataIndex: 'cases_pct', key: 'cases_pct', width: 56, align: 'center' as const,
        render: (v: number, row: MallRow5Y) => (
          <Text style={{
            color:      row.category === 'TOTAL' ? '#888' : '#FA8C16',
            fontWeight: row.category !== 'TOTAL' ? 600 : 400,
            fontSize:   13,
          }}>
            {(v ?? 0).toFixed(1)}%
          </Text>
        ),
      },
    ]
  }

  function TabYearly() {
    if (!yearlyData) return (
      <Spin spinning={loadingYearly}>
        <Alert message="切換至此 Tab 後自動載入" type="info" showIcon />
      </Spin>
    )

    // 轉為累計（Running Total）：每月值 = 1 月到該月的加總
    const toCumulative = (arr: number[]): number[] => {
      let sum = 0
      return arr.map(v => { sum += v; return sum })
    }

    const MALL_5CATS_ORDER = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢'] as const

    const catCases: Record<string, number[]> = {}
    MALL_5CATS_ORDER.forEach(cat => {
      const found = yearlyData!.rows.find(r => r.category === cat)
      catCases[cat] = toCumulative(found?.cases ?? Array(12).fill(0))
    })

    // 全年合計 = 12 月累計值（各類別總和）
    const grandTotal = MALL_5CATS_ORDER.reduce((s, cat) => s + (catCases[cat][11] ?? 0), 0)

    const tableRows: MallRow5Y[] = MALL_5CATS_ORDER.map(cat => {
      const cases = catCases[cat]
      const total = cases[11] ?? 0
      const cases_pct = grandTotal > 0 ? Math.round(total / grandTotal * 1000) / 10 : 0
      return { key: cat, category: cat, cases, total, cases_pct }
    })

    // TOTAL 列：每月所有類別累計之和
    const totalCases = Array.from({ length: 12 }, (_, i) =>
      MALL_5CATS_ORDER.reduce((s, cat) => s + (catCases[cat][i] ?? 0), 0)
    )
    tableRows.push({ key: 'TOTAL', category: 'TOTAL', cases: totalCases, total: grandTotal, cases_pct: 100 })

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
                  setLoadingYearly(true)
                  fetchMallMonthlyHours(v).then(setYearlyData).finally(() => setLoadingYearly(false))
                }}
              />
            </Col>
            <Col>
              <Button
                icon={<ReloadOutlined />}
                size="small"
                loading={loadingYearly}
                onClick={() => {
                  setLoadingYearly(true)
                  fetchMallMonthlyHours(yearlyYear).then(setYearlyData).finally(() => setLoadingYearly(false))
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
          {(['現場報修','上級交辦','緊急事件','例行維護','每日巡檢'] as const).map(cat => (
            <Space key={cat} size={2}>
              {renderMallCategory(cat)}
              <Tooltip title={MALL_5CAT_TOOLTIPS[cat]} overlayStyle={{ maxWidth: 440 }}>
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
          <Table<MallRow5Y>
            dataSource={tableRows}
            columns={buildMallYearlyCols()}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            rowClassName={(r) => r.category === 'TOTAL' ? 'mall-yearly-total-row' : ''}
            style={{ fontSize: 14 }}
          />
        </Card>
        <style>{`.mall-yearly-total-row td { background: #f5f5f5 !important; font-weight: 600; }`}</style>
      </>
    )
  }

  // ════════════════════════════════════════════════════════════════════════════
  // TAB D：人員工時%（5 工項 × 人員交叉表，格式比照 WCA Tab D）
  // ════════════════════════════════════════════════════════════════════════════

  function buildMallPersonCols(): ColumnsType<MallPersonRow & { key: number }> {
    const persons = personHoursData?.persons ?? []
    const pctColor = (v: number) =>
      v >= 30 ? '#FF4D4F' : v >= 15 ? '#FA8C16' : v > 0 ? '#52C41A' : '#ccc'
    return [
      {
        title: '工項類別', dataIndex: 'category', fixed: 'left', width: 100,
        render: renderMallCategory,
      },
      ...persons.map((p, i) => ({
        title: <Text style={{ fontSize: 13 }}>{p}</Text>,
        key:   `p${i}`,
        width: 72,
        align: 'center' as const,
        render: (_: unknown, row: MallPersonRow & { key: number }) => {
          const v = row.pct_by_person[i] ?? 0
          const c = pctColor(v)
          return (
            <Text style={{ fontSize: 13, color: c, fontWeight: v >= 15 ? 600 : 400 }}>
              {v > 0 ? `${v.toFixed(1)}%` : '-'}
            </Text>
          )
        },
      })),
    ]
  }

  const TabPersonPct = (
    <>
      <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
        <Row gutter={[12, 8]} align="middle">
          <Col><Text strong style={{ fontSize: 15 }}>人員工時佔比</Text></Col>
          <Col>
            <Select
              value={personYear}
              options={yearOptions}
              style={{ width: 100 }}
              onChange={(v) => { setPersonYear(v); loadPersonHours(v) }}
            />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => loadPersonHours()} loading={loadingPerson}>
              重新整理
            </Button>
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 14 }}>{personYear} 年 · Top 15 人員</Text>
          </Col>
        </Row>
      </Card>

      <Alert
        type="info" showIcon
        description="人員識別規則：現場報修 = 結案人（acceptor）、例行維護 = 執行人員（executor_name，可多人分攤）、每日巡檢 = 巡檢人員（inspector_name）。上級交辦／緊急事件（hotel/other-tasks）目前無人員欄位，工時以 work_hours 計入彙總。"
        style={{ marginBottom: 12 }}
      />

      <Spin spinning={loadingPerson}>
        {!personHoursData && !loadingPerson ? (
          <Alert message="請選擇年份以查看人員工時佔比" type="info" showIcon />
        ) : !personHoursData?.persons.length ? (
          <Alert message="本年度暫無人員工時資料" type="warning" showIcon />
        ) : (
          <Card
            title={<Text strong>人員工時佔比 (%)</Text>}
            extra={<Text type="secondary">各工項類別 · {personHoursData.persons.length} 位人員</Text>}
            bodyStyle={{ padding: '6px 0' }}
          >
            <Table
              dataSource={(personHoursData?.rows ?? []).map((r, i) => ({ ...r, key: i }))}
              columns={buildMallPersonCols()}
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
            />
          </Card>
        )}
      </Spin>

      <Card size="small" title="其他來源人員資料入口" style={{ marginTop: 12 }}>
        <Row gutter={[8, 8]}>
          {[
            { label: '商場例行維護 — 各批次執行人員', route: '/mall/periodic-maintenance',           color: '#1B3A5C' },
            { label: '全棟例行維護 — 各批次執行人員', route: '/mall/full-building-maintenance',      color: '#4BA8E8' },
            { label: '商場工務巡檢 — 各樓層巡檢人員', route: '/mall-facility-inspection/dashboard',  color: '#722ED1' },
            { label: '整棟巡檢 — 各樓層巡檢人員',     route: '/full-building-inspection/dashboard', color: '#52C41A' },
          ].map(s => (
            <Col key={s.route} xs={24} sm={12}>
              <Button type="link" icon={<RightOutlined />} style={{ color: s.color }}
                onClick={() => navigate(s.route)}>
                {s.label}
              </Button>
            </Col>
          ))}
        </Row>
      </Card>
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // TAB E：人員排名
  // ════════════════════════════════════════════════════════════════════════════
  const pctColor = (v: number) => v >= 30 ? '#FF4D4F' : v >= 15 ? '#FA8C16' : v > 0 ? '#52C41A' : '#ccc'

  const rankingCols: ColumnsType<typeof personRanking[0]> = [
    {
      title: '排名', dataIndex: 'rank', width: 55, align: 'center',
      render: (v: number) => {
        const medal: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }
        return medal[v]
          ? <span style={{ fontSize: 20 }}>{medal[v]}</span>
          : <Text strong style={{ color: '#999' }}>#{v}</Text>
      },
    },
    { title: '人員', dataIndex: 'name', width: 110, render: (v: string) => <Text strong>{v}</Text> },
    {
      title: '全年工時 (HR)', dataIndex: 'total_hours', width: 140, align: 'right',
      sorter: (a, b) => a.total_hours - b.total_hours, defaultSortOrder: 'descend',
      render: (v: number) => (
        <Text strong style={{ fontSize: 18, color: '#1B3A5C' }}>
          {v.toFixed(1)}<Text style={{ fontSize: 13, color: '#888', marginLeft: 2 }}>HR</Text>
        </Text>
      ),
    },
    {
      title: '占比%', width: 190, align: 'center',
      render: (_: unknown, r: typeof personRanking[0]) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Progress percent={r.pct} size="small" showInfo={false} strokeColor={pctColor(r.pct)} style={{ flex: 1 }} />
          <Text style={{ fontSize: 14, color: pctColor(r.pct), fontWeight: 600, minWidth: 42 }}>{r.pct.toFixed(1)}%</Text>
        </div>
      ),
    },
    {
      title: '來源分解', width: 220, align: 'center',
      render: (_: unknown, r: typeof personRanking[0]) => (
        <Tooltip title={
          <div style={{ fontSize: 12 }}>
            {r.cats.filter(c => c.pct > 0).map(c => (
              <div key={c.category}>{c.category}：{c.pct.toFixed(1)}%</div>
            ))}
          </div>
        }>
          <Text style={{ color: '#4BA8E8', cursor: 'pointer', fontSize: 12 }}>
            {r.cats.filter(c => c.pct > 0).map(c => c.category).join(' · ')}
          </Text>
        </Tooltip>
      ),
    },
  ]

  const TabRanking = (
    <>
      <Alert type="info" showIcon
        description="人員工時排名彙整現場報修、例行維護、每日巡檢（及上級交辦、緊急事件）五項來源（Top-15，依全年合計工時降冪）。「來源分解」欄顯示各工項占該工項總工時的百分比（hover 查看）。"
        style={{ marginBottom: 12 }} />

      {!personHoursData && !loadingPerson ? (
        <Alert message="尚未載入人員工時資料，請切換至此 Tab 後稍候" type="warning" showIcon />
      ) : personRanking.length === 0 ? (
        <Alert message="本年度無人員工時排名資料" type="warning" showIcon />
      ) : (
        <>
          <Card size="small" title={<><TrophyOutlined /> 人員工時排名（五項來源合計）</>} style={{ marginBottom: 12 }}>
            <ResponsiveContainer width="100%" height={Math.max(180, personRanking.length * 28)}>
              <BarChart data={[...personRanking].reverse()} layout="vertical" margin={{ left: 10, right: 50 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 13 }} unit="H" />
                <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 13 }} />
                <RcTooltip formatter={(v: number, _name, props) => [
                  `${(v as number).toFixed(1)} HR（全年 ${props.payload.pct?.toFixed(1) ?? 0}%）`,
                  '合計工時',
                ]} />
                <Bar dataKey="total_hours" name="工時(HR)" radius={[0, 4, 4, 0]}>
                  {[...personRanking].reverse().map((_, i) => (
                    <Cell key={i} fill={['#FA8C16','#4BA8E8','#52C41A','#722ED1','#FF4D4F','#13C2C2','#1B3A5C','#EB2F96'][i % 8]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {/* 來源分解堆疊橫向 Bar Chart */}
          <Card size="small" title={<><BarChartOutlined /> 人員工時分解（HR）</>} style={{ marginBottom: 12 }}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={breakdownData} layout="vertical" margin={{ left: 10, right: 50 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 12 }} unit="H" />
                <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 12 }} />
                <RcTooltip formatter={(v: number, name) => [`${Number(v).toFixed(1)} HR`, name as string]} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                {MALL_3CATS.map((cat, ci) => (
                  <Bar
                    key={cat} dataKey={cat} stackId="src" fill={MALL_CAT_HEX[cat]} name={cat}
                    radius={ci === MALL_3CATS.length - 1 ? [0, 4, 4, 0] : [0, 0, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title={<Text strong>人員工時排名明細</Text>} bodyStyle={{ padding: '6px 0' }}>
            <Table
              dataSource={personRanking}
              columns={rankingCols}
              size="small"
              pagination={{ pageSize: 20, showTotal: t => `共 ${t} 人` }}
              summary={() => (
                <Table.Summary fixed>
                  <Table.Summary.Row style={{ background: '#f0f4f8' }}>
                    <Table.Summary.Cell index={0} colSpan={2}><Text strong>合計</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={2} align="right">
                      <Text strong style={{ color: '#1B3A5C' }}>{totalPersonHours.toFixed(1)} HR</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={3} align="center"><Text strong>100%</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={4} />
                  </Table.Summary.Row>
                </Table.Summary>
              )}
            />
          </Card>
        </>
      )}
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // Tab Items 定義
  // ════════════════════════════════════════════════════════════════════════════
  const tabLabelStyle = { fontSize: 16 } as const
  const tabItems = [
    { key: 'dashboard',  label: <span style={tabLabelStyle}><LineChartOutlined /> A. Dashboard</span>, children: TabDashboard },
    { key: 'daily',      label: <span style={tabLabelStyle}><TableOutlined />     B. 每日累計</span>,  children: TabDaily },
    { key: 'monthly',    label: <span style={tabLabelStyle}><TableOutlined />     C. 每月累計</span>,  children: TabMonthly },
    { key: 'yearly',     label: <span style={tabLabelStyle}><CalendarOutlined />  D. 每年累計</span>,  children: <TabYearly /> },
    { key: 'person_pct', label: <span style={tabLabelStyle}><TeamOutlined />      人員工時%</span>,    children: TabPersonPct },
    { key: 'ranking',    label: <span style={tabLabelStyle}><TrophyOutlined />    人員排名</span>,     children: TabRanking },
  ]

  // ════════════════════════════════════════════════════════════════════════════
  // Render
  // ════════════════════════════════════════════════════════════════════════════
  return (
    <div style={{ padding: '0 4px 40px' }}>
      <style>{`
        .monthly-future-row td { color: #bbb !important; background: #fafafa !important; }
      `}</style>

      <Breadcrumb style={{ marginBottom: 12 }} items={[
        { title: <HomeOutlined /> },
        { title: NAV_GROUP.mall },
        { title: NAV_PAGE.mallMgmtDashboard },
      ]} />

      <Card bodyStyle={{ padding: '12px 16px' }} style={{ marginBottom: 12 }}>
        <Row justify="space-between" align="middle" gutter={[0, 8]}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              <ShopOutlined style={{ marginRight: 6 }} />
              {NAV_PAGE.mallMgmtDashboard}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              商場例行維護 · 全棟例行維護 · 工務巡檢 · 整棟巡檢 · 工務報修 — 整合總覽
            </Text>
          </Col>
          <Col>
            <Space wrap>
              <Select value={year} options={yearOptions} style={{ width: 100 }} size="small"
                onChange={(v) => {
                  setYear(v)
                  loadMallPm(v, month); loadFullBldgPm(v, month)
                  loadMallFacilityByMonth(v, month); loadLuqun(v, month)
                }}
              />
              <Select value={month} options={monthOptions} style={{ width: 90 }} size="small"
                onChange={(v) => {
                  setMonth(v)
                  loadMallPm(year, v); loadFullBldgPm(year, v)
                  loadMallFacilityByMonth(year, v); loadLuqun(year, v)
                }}
              />
              <Tag color="default" style={{ fontSize: 11 }}>巡檢日期：{targetDate}</Tag>
              <Button
                size="small"
                icon={<FilePptOutlined />}
                loading={exportLoading}
                disabled={month === 0}
                style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', color: '#fff', border: 'none' }}
                onClick={async () => {
                  if (month === 0) return
                  setExportLoading(true)
                  try {
                    const sources = SOURCE_CONFIG.map(c => {
                      const s = summaryMap[c.key as keyof typeof summaryMap]
                      return {
                        source_name:     c.label,
                        source_key:      c.key,
                        case_count:      Math.max(0, s?.case_count      ?? 0),
                        completed_count: s?.completed_count ?? 0,
                        completion_rate: Math.round((s?.completion_rate ?? 0) * 10) / 10,
                        abnormal_count:  s?.abnormal_count  ?? 0,
                        overdue_count:   s?.overdue_count   ?? 0,
                        work_hours:      Math.max(0, s?.work_hours  ?? 0),
                        actual_hours:    s?.actual_hours ?? 0,
                      }
                    })
                    const payload: MallPptxPayload = {
                      kpi_summary: {
                        total_cases:      totalCases,
                        completed_cases:  totalCompleted,
                        total_work_hours: Math.round(totalWorkHours * 10) / 10,
                        abnormal_count:   totalAbnormal,
                        overdue_count:    totalOverdue,
                      },
                      source_cards: sources,
                      repair_costs: {
                        outsource_fee:   kpi?.annual_outsource_fee   ?? 0,
                        maintenance_fee: kpi?.annual_maintenance_fee ?? 0,
                        deduction_fee:   kpi?.annual_deduction_fee   ?? 0,
                        month_total_fee: (kpi?.month_outsource_fee   ?? 0)
                                       + (kpi?.month_maintenance_fee ?? 0),
                        period_label:    ytdLabel,
                      },
                    }
                    await exportMallOverviewPptx(year, month, payload)
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

      <Tabs
        activeKey={activeTab}
        onChange={handleTabChange}
        size="small"
        items={tabItems}
        style={{ background: '#fff', padding: '0 16px 16px', borderRadius: 8 }}
      />
    </div>
  )
}
