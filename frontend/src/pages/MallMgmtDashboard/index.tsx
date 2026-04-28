/**
 * 商場管理 Dashboard — 整合總覽（含 5 Tab）
 *
 * Tab 結構（對應 work-category-analysis 風格）：
 *   A. Dashboard    — 5 來源 KPI 卡片 + 各來源狀態卡 + 圖表
 *   B. 每日累計     — 大直工務報修：選月日別統計（occupied_at 聚合）
 *   C. 每月累計     — 商場 PM / 全棟 PM / 大直報修：月 × 來源完成率矩陣
 *   D. 人員工時%    — 大直報修 top_hours 人員工時佔比（Dashboard API 已包含）
 *   E. 人員排名     — 大直報修工時前排名人員列表
 *
 * 資料限制說明：
 *   - 商場 PM / 全棟 PM / 商場工務巡檢 / 整棟巡檢 目前 Dashboard API 未提供人員維度
 *   - 人員工時相關 Tab 以大直工務報修資料為主，其餘來源提示至個別模組查看
 *   - 不新增任何 Backend API，全部沿用既有 endpoint
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Row, Col, Card, Statistic, Typography, Breadcrumb,
  Select, Space, Tooltip, DatePicker, Button,
  Progress, Alert, Tag, Tabs, Table, Divider, Badge,
  Spin,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, ShopOutlined,
  ClockCircleOutlined, WarningOutlined, CheckCircleOutlined,
  ExclamationCircleOutlined, BarChartOutlined, ToolOutlined,
  RightOutlined, DashboardOutlined, QuestionCircleOutlined,
  CalendarOutlined, SafetyOutlined, TrophyOutlined,
  TableOutlined, LineChartOutlined, TeamOutlined,
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
import { fetchMallPMStats, fetchMallPMBatches }          from '@/api/mallPeriodicMaintenance'
import { fetchFullBldgPMStats, fetchFullBldgPMBatches }  from '@/api/fullBuildingMaintenance'
import { fetchMallFacilityDashboardSummary }             from '@/api/mallFacilityInspection'
import {
  fetchDashboard as fetchDazhiDash,
  fetchDetail    as fetchDazhiDetail,
} from '@/api/dazhiRepair'

// ── Types ──────────────────────────────────────────────────────────────────────
import type { PMStats, PMBatchListItem }      from '@/types/periodicMaintenance'
import type { MallFIDashboardSummary }        from '@/api/mallFacilityInspection'
import type { DashboardData, RepairCase }     from '@/types/dazhiRepair'

import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

// ── Normalize 共用型別 ────────────────────────────────────────────────────────
export interface NormalizedSummary {
  work_hours:       number
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
  { key: 'mall_pm',        label: '商場例行維護', color: '#1B3A5C', icon: <CalendarOutlined />, route: '/mall/periodic-maintenance' },
  { key: 'full_bldg_pm',  label: '全棟例行維護', color: '#4BA8E8', icon: <ToolOutlined />,     route: '/mall/full-building-maintenance' },
  { key: 'mall_facility', label: '商場工務巡檢', color: '#722ED1', icon: <SafetyOutlined />,   route: '/mall-facility-inspection/dashboard' },
  { key: 'full_bldg_insp',label: '整棟巡檢',     color: '#52C41A', icon: <SafetyOutlined />,   route: '/full-building-inspection/dashboard' },
] as const

// 第二列：報修 / 交辦 / 緊急事件
const SOURCE_CONFIG_ROW2 = [
  { key: 'dazhi_repair',    label: '大直工務報修', color: '#FA8C16', icon: <WarningOutlined />,          route: '/dazhi-repair/dashboard' },
  { key: 'mall_supervisor', label: '商場主管交辦', color: '#C0392B', icon: <ExclamationCircleOutlined />, route: '/dashboard' },
  { key: 'mall_emergency',  label: '商場緊急事件', color: '#D4380D', icon: <WarningOutlined />,           route: '/dashboard' },
] as const

const SOURCE_CONFIG = [...SOURCE_CONFIG_ROW1, ...SOURCE_CONFIG_ROW2] as const

// ── Normalize 函式 ─────────────────────────────────────────────────────────────
function normalizePM(data: PMStats | null) {
  const kpi = data?.current_kpi
  return {
    work_hours:      kpi ? Math.round((kpi.planned_minutes / 60) * 10) / 10 : 0,
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
  if (!data?.sheets?.length) return { work_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: !data, category_breakdown: undefined }
  const sheets = data.sheets
  const total_items    = sheets.reduce((s, sh) => s + sh.total_items,    0)
  const checked_items  = sheets.reduce((s, sh) => s + sh.checked_items,  0)
  const abnormal_items = sheets.reduce((s, sh) => s + sh.abnormal_items + sh.pending_items, 0)
  const total_minutes  = sheets.reduce((s, sh) => s + (sh.total_minutes ?? 0), 0)
  return {
    work_hours:      Math.round((total_minutes / 60) * 10) / 10,
    case_count:      total_items,
    completed_count: checked_items,
    completion_rate: total_items > 0 ? Math.round((checked_items / total_items) * 100) : 0,
    abnormal_count:  abnormal_items,
    overdue_count:   0,
    is_placeholder:  false,
    category_breakdown: sheets.map(sh => ({ name: sh.title, count: sh.total_items, rate: sh.completion_rate })),
  }
}

function normalizeDazhi(data: DashboardData | null) {
  if (!data) return { work_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: true, category_breakdown: undefined }
  const kpi = data.kpi
  const case_count = kpi.total
  return {
    work_hours:      Math.round((kpi.total_work_hours ?? 0) * 10) / 10,
    case_count,
    completed_count: kpi.completed,
    completion_rate: case_count > 0 ? Math.round((kpi.completed / case_count) * 100) : 0,
    abnormal_count:  kpi.uncompleted,
    overdue_count:   0,
    is_placeholder:  false,
    category_breakdown: data.type_dist?.map(t => ({ name: t.type, count: t.count, rate: case_count > 0 ? Math.round((t.count / case_count) * 100) : 0 })),
  }
}

// ── 來源卡片子元件 ─────────────────────────────────────────────────────────────
function SourceCard({
  config, summary, loading, error,
}: {
  config:   typeof SOURCE_CONFIG[number]
  summary:  NormalizedSummary | null
  loading:  boolean
  error:    string | null
}) {
  const navigate = useNavigate()
  const color = config.color
  return (
    <Card
      size="small"
      title={<Space><span style={{ color }}>{config.icon}</span><Text strong style={{ color, fontSize: 13 }}>{config.label}</Text></Space>}
      extra={<Button type="link" size="small" icon={<RightOutlined />} style={{ color }} onClick={() => navigate(config.route)}>詳情</Button>}
      style={{ borderTop: `3px solid ${color}`, height: '100%' }}
      loading={loading}
    >
      {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 8 }} />}
      {(!summary || summary.is_placeholder) && !loading && !error && (
        <div style={{ textAlign: 'center', color: '#bbb', padding: '20px 0', fontSize: 12 }}>數據準備中</div>
      )}
      {summary && !summary.is_placeholder && (
        <>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Statistic title={<Text style={{ fontSize: 11, color: '#888' }}>工項/案件數</Text>} value={summary.case_count} suffix="筆" valueStyle={{ fontSize: 20, color }} />
            </Col>
            <Col span={12}>
              <Statistic title={<Text style={{ fontSize: 11, color: '#888' }}>已完成</Text>} value={summary.completed_count} suffix="筆" valueStyle={{ fontSize: 20, color: '#52C41A' }} />
            </Col>
          </Row>
          <div style={{ marginTop: 10 }}>
            <Progress percent={summary.completion_rate} size="small"
              strokeColor={{ from: summary.completion_rate < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
              format={(p) => `完成率 ${p}%`} />
          </div>
          <Row gutter={[8, 0]} style={{ marginTop: 8 }}>
            {summary.abnormal_count > 0 && <Col span={12}><Text type="secondary" style={{ fontSize: 11 }}>異常：</Text><Text style={{ fontSize: 11, color: '#FF4D4F', fontWeight: 600 }}>{summary.abnormal_count}</Text></Col>}
            {summary.overdue_count  > 0 && <Col span={12}><Text type="secondary" style={{ fontSize: 11 }}>逾期：</Text><Text style={{ fontSize: 11, color: '#C0392B', fontWeight: 600 }}>{summary.overdue_count}</Text></Col>}
            {summary.work_hours     > 0 && <Col span={12}><Text type="secondary" style={{ fontSize: 11 }}>工時：</Text><Text style={{ fontSize: 11, color, fontWeight: 600 }}>{summary.work_hours} HR</Text></Col>}
          </Row>
        </>
      )}
    </Card>
  )
}

// ── Monthly 輔助：把 PM 批次列表轉成月份 → kpi map ─────────────────────────────
function buildPMMonthMap(batches: PMBatchListItem[]): Record<number, { total: number; completed: number; rate: number; overdue: number }> {
  const map: Record<number, { total: number; completed: number; rate: number; overdue: number }> = {}
  batches.forEach(b => {
    const m = parseInt(b.batch.period_month?.split('/')[1] ?? '0', 10)
    if (m >= 1 && m <= 12) map[m] = { total: b.kpi.total, completed: b.kpi.completed, rate: b.kpi.completion_rate, overdue: b.kpi.overdue }
  })
  return map
}

// ── 每日累計：把 dazhi detail 記錄按日聚合 ────────────────────────────────────
interface DailyAgg { date: string; day: number; total: number; completed: number; work_hours: number }
function aggregateByDay(cases: RepairCase[]): DailyAgg[] {
  const map: Record<string, DailyAgg> = {}
  cases.forEach(c => {
    const d = c.occurred_at ? c.occurred_at.slice(0, 10) : null
    if (!d) return
    if (!map[d]) map[d] = { date: d, day: parseInt(d.slice(8, 10), 10), total: 0, completed: 0, work_hours: 0 }
    map[d].total++
    if (c.is_completed) map[d].completed++
    map[d].work_hours = Math.round((map[d].work_hours + (c.work_hours ?? 0)) * 10) / 10
  })
  return Object.values(map).sort((a, b) => a.date.localeCompare(b.date))
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
  const [month,      setMonth]      = useState<number>(0)
  const [targetDate, setTargetDate] = useState<string>(dayjs().format('YYYY/MM/DD'))
  const [activeTab,  setActiveTab]  = useState('dashboard')

  // ── Tab A：5 來源原始資料 ──────────────────────────────────────────────────
  const [mallPmData,       setMallPmData]       = useState<PMStats | null>(null)
  const [fullBldgPmData,   setFullBldgPmData]   = useState<PMStats | null>(null)
  const [mallFacilityData, setMallFacilityData] = useState<MallFIDashboardSummary | null>(null)
  const [dazhiData,        setDazhiData]        = useState<DashboardData | null>(null)

  const [loadingMallPm,       setLoadingMallPm]       = useState(false)
  const [loadingFullBldgPm,   setLoadingFullBldgPm]   = useState(false)
  const [loadingMallFacility, setLoadingMallFacility] = useState(false)
  const [loadingDazhi,        setLoadingDazhi]        = useState(false)

  const [errorMallPm,       setErrorMallPm]       = useState<string | null>(null)
  const [errorFullBldgPm,   setErrorFullBldgPm]   = useState<string | null>(null)
  const [errorMallFacility, setErrorMallFacility] = useState<string | null>(null)
  const [errorDazhi,        setErrorDazhi]        = useState<string | null>(null)

  // ── Tab C：每月累計 extra 資料 ─────────────────────────────────────────────
  const [mallPmBatches,     setMallPmBatches]     = useState<PMBatchListItem[]>([])
  const [fullBldgPmBatches, setFullBldgPmBatches] = useState<PMBatchListItem[]>([])
  const [loadingMonthly,    setLoadingMonthly]    = useState(false)

  // ── Tab B：每日累計 dazhi detail ───────────────────────────────────────────
  const [dailyCases,    setDailyCases]    = useState<RepairCase[]>([])
  const [loadingDaily,  setLoadingDaily]  = useState(false)
  const [dailyMonth,    setDailyMonth]    = useState<number>(thisMonth)
  const [dailyYear,     setDailyYear]     = useState<number>(thisYear)

  // ── 載入 Tab A ─────────────────────────────────────────────────────────────
  const loadMallPm = useCallback(async () => {
    setLoadingMallPm(true); setErrorMallPm(null)
    try     { setMallPmData(await fetchMallPMStats()) }
    catch   { setErrorMallPm('商場例行維護載入失敗') }
    finally { setLoadingMallPm(false) }
  }, [])

  const loadFullBldgPm = useCallback(async () => {
    setLoadingFullBldgPm(true); setErrorFullBldgPm(null)
    try     { setFullBldgPmData(await fetchFullBldgPMStats()) }
    catch   { setErrorFullBldgPm('全棟例行維護載入失敗') }
    finally { setLoadingFullBldgPm(false) }
  }, [])

  const loadMallFacility = useCallback(async (dt?: string) => {
    setLoadingMallFacility(true); setErrorMallFacility(null)
    try     { setMallFacilityData(await fetchMallFacilityDashboardSummary(dt ?? targetDate)) }
    catch   { setErrorMallFacility('商場工務巡檢載入失敗') }
    finally { setLoadingMallFacility(false) }
  }, [targetDate])

  const loadDazhi = useCallback(async (y?: number, m?: number) => {
    setLoadingDazhi(true); setErrorDazhi(null)
    try     { setDazhiData(await fetchDazhiDash(y ?? year, m ?? month)) }
    catch   { setErrorDazhi('大直工務報修載入失敗') }
    finally { setLoadingDazhi(false) }
  }, [year, month])

  const loadAll = useCallback(() => {
    loadMallPm(); loadFullBldgPm(); loadMallFacility(); loadDazhi()
  }, [loadMallPm, loadFullBldgPm, loadMallFacility, loadDazhi])

  useEffect(() => { loadAll() }, []) // eslint-disable-line

  // ── 載入 Tab C（每月累計）──────────────────────────────────────────────────
  const loadMonthly = useCallback(async (y?: number) => {
    setLoadingMonthly(true)
    const yr = y ?? year
    try {
      const [pm, fbpm] = await Promise.all([
        fetchMallPMBatches(String(yr)),
        fetchFullBldgPMBatches(String(yr)),
      ])
      setMallPmBatches(pm)
      setFullBldgPmBatches(fbpm)
    } catch { /* silent */ }
    finally { setLoadingMonthly(false) }
  }, [year])

  // ── 載入 Tab B（每日累計）──────────────────────────────────────────────────
  const loadDaily = useCallback(async (y?: number, m?: number) => {
    const dy = y ?? dailyYear
    const dm = m ?? dailyMonth
    if (!dm) return
    setLoadingDaily(true)
    try {
      const res = await fetchDazhiDetail({ year: dy, month: dm, page: 1, page_size: 500 })
      setDailyCases(res.items ?? [])
    } catch { setDailyCases([]) }
    finally { setLoadingDaily(false) }
  }, [dailyYear, dailyMonth])

  // Tab 切換時懶載入
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'monthly' && mallPmBatches.length === 0) loadMonthly()
    if (key === 'daily'   && dailyCases.length   === 0) loadDaily()
  }

  // ── Normalize ──────────────────────────────────────────────────────────────
  const mallPmSummary       = useMemo(() => normalizePM(mallPmData),               [mallPmData])
  const fullBldgPmSummary   = useMemo(() => normalizePM(fullBldgPmData),           [fullBldgPmData])
  const mallFacilitySummary = useMemo(() => normalizeFacility(mallFacilityData),   [mallFacilityData])
  const dazhiSummary        = useMemo(() => normalizeDazhi(dazhiData),             [dazhiData])
  const placeholderSummary = useMemo((): NormalizedSummary => ({ work_hours: 0, case_count: 0, completed_count: 0, completion_rate: 0, abnormal_count: 0, overdue_count: 0, is_placeholder: true, category_breakdown: undefined }), [])
  const fullBldgInspSummary = placeholderSummary

  const summaryMap: Record<string, NormalizedSummary> = {
    mall_pm:          mallPmSummary,
    full_bldg_pm:     fullBldgPmSummary,
    mall_facility:    mallFacilitySummary,
    full_bldg_insp:   fullBldgInspSummary,
    dazhi_repair:     dazhiSummary,
    mall_supervisor:  placeholderSummary,
    mall_emergency:   placeholderSummary,
  }
  const loadingMap: Record<string, boolean> = {
    mall_pm: loadingMallPm, full_bldg_pm: loadingFullBldgPm, mall_facility: loadingMallFacility,
    full_bldg_insp: false,  dazhi_repair: loadingDazhi, mall_supervisor: false, mall_emergency: false,
  }
  const errorMap: Record<string, string | null> = {
    mall_pm: errorMallPm, full_bldg_pm: errorFullBldgPm, mall_facility: errorMallFacility,
    full_bldg_insp: null, dazhi_repair: errorDazhi, mall_supervisor: null, mall_emergency: null,
  }

  // ── 彙總 KPI ───────────────────────────────────────────────────────────────
  const allSummaries   = [mallPmSummary, fullBldgPmSummary, mallFacilitySummary, dazhiSummary]
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

  const trendData = (dazhiData?.trend_12m ?? []).map(t => ({
    label: t.label, 總案件: t.total, 已結案: t.completed,
  }))

  // ── Tab B：每日累計資料 ─────────────────────────────────────────────────────
  const dailyAggData = useMemo(() => aggregateByDay(dailyCases), [dailyCases])

  // ── Tab C：每月累計資料 ─────────────────────────────────────────────────────
  const mallPmMonthMap     = useMemo(() => buildPMMonthMap(mallPmBatches),     [mallPmBatches])
  const fullBldgPmMonthMap = useMemo(() => buildPMMonthMap(fullBldgPmBatches), [fullBldgPmBatches])
  const dazhiMonthMap      = useMemo(() => {
    const map: Record<number, { total: number; completed: number }> = {}
    ;(dazhiData?.trend_12m ?? []).forEach(t => { if (t.month) map[t.month] = { total: t.total, completed: t.completed } })
    return map
  }, [dazhiData])

  const monthlyRows = useMemo(() =>
    Array.from({ length: 12 }, (_, i) => {
      const m = i + 1
      const pmRow   = mallPmMonthMap[m]
      const fbpmRow = fullBldgPmMonthMap[m]
      const dzRow   = dazhiMonthMap[m]
      return {
        key:  m,
        month: m,
        pm_total:      pmRow?.total      ?? 0,
        pm_completed:  pmRow?.completed  ?? 0,
        pm_rate:       pmRow?.rate       ?? 0,
        pm_overdue:    pmRow?.overdue    ?? 0,
        fb_total:      fbpmRow?.total    ?? 0,
        fb_completed:  fbpmRow?.completed ?? 0,
        fb_rate:       fbpmRow?.rate     ?? 0,
        fb_overdue:    fbpmRow?.overdue  ?? 0,
        dz_total:      dzRow?.total      ?? 0,
        dz_completed:  dzRow?.completed  ?? 0,
        dz_rate:       dzRow ? (dzRow.total > 0 ? Math.round((dzRow.completed / dzRow.total) * 100) : 0) : 0,
      }
    })
  , [mallPmMonthMap, fullBldgPmMonthMap, dazhiMonthMap])

  // ── Tab D/E：人員資料（大直工務 top_hours）────────────────────────────────
  const personRanking = useMemo(() => {
    const all = [...(dazhiData?.top_hours ?? [])]
    // 以 acceptor（結案人）聚合工時
    const map: Record<string, { name: string; work_hours: number; cases: number }> = {}
    all.forEach(c => {
      const name = c.acceptor || c.closer || '未知'
      if (!map[name]) map[name] = { name, work_hours: 0, cases: 0 }
      map[name].work_hours = Math.round((map[name].work_hours + (c.work_hours ?? 0)) * 10) / 10
      map[name].cases++
    })
    return Object.values(map)
      .sort((a, b) => b.work_hours - a.work_hours)
      .map((r, i) => ({ ...r, rank: i + 1, key: i }))
  }, [dazhiData])

  const totalPersonHours = personRanking.reduce((s, r) => s + r.work_hours, 0)

  // ── 篩選選項 ───────────────────────────────────────────────────────────────
  const yearOptions  = [2024, 2025, 2026, 2027].map(y => ({ value: y, label: `${y} 年` }))
  const monthOptions = [{ value: 0, label: '全年' }, ...Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: `${i + 1} 月` }))]
  const dailyMonthOptions = Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: `${i + 1} 月` }))

  // ════════════════════════════════════════════════════════════════════════════
  // TAB A：Dashboard 總覽
  // ════════════════════════════════════════════════════════════════════════════
  const TabDashboard = (
    <>
      {/* 篩選列 */}
      <Card size="small" style={{ marginBottom: 16, background: '#f9fbff' }}>
        <Row gutter={[16, 8]} align="middle">
          <Col><Text type="secondary" style={{ fontSize: 12 }}>大直工務篩選：</Text></Col>
          <Col>
            <Select value={year} options={yearOptions} style={{ width: 100 }} onChange={(v) => { setYear(v); loadDazhi(v, month) }} />
          </Col>
          <Col>
            <Select value={month} options={monthOptions} style={{ width: 90 }} onChange={(v) => { setMonth(v); loadDazhi(year, v) }} />
          </Col>
          <Col><Divider type="vertical" /></Col>
          <Col><Text type="secondary" style={{ fontSize: 12 }}>工務巡檢日期：</Text></Col>
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
      <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>主管摘要</Divider>
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #1B3A5C' }}>
            <Statistic
              title={<Tooltip title="商場例行維護 + 全棟例行維護 + 商場工務巡檢 + 大直工務報修之工項/案件總和"><span style={{ fontSize: 11, color: '#888', cursor: 'help' }}>本期總工項 <QuestionCircleOutlined style={{ color: '#bbb' }} /></span></Tooltip>}
              value={totalCases} suffix="筆"
              valueStyle={{ fontSize: 22, color: '#1B3A5C', fontWeight: 700 }}
              prefix={<BarChartOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #52C41A' }}>
            <Statistic title={<Text style={{ fontSize: 11, color: '#888' }}>已完成工項</Text>} value={totalCompleted} suffix="筆"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: '#52C41A' }}
              prefix={<CheckCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>完成率 {overallRate}%</Text>
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #4BA8E8' }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 6 }}>整體完成率</div>
            <Progress type="circle" percent={overallRate} width={60}
              strokeColor={{ from: overallRate < 50 ? '#FF4D4F' : '#FAAD14', to: '#52C41A' }}
              format={(p) => <span style={{ fontSize: 14, fontWeight: 700 }}>{p}%</span>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #FA8C16' }}>
            <Statistic
              title={<Tooltip title="PM 計劃工時（預估）+ 巡檢工時 + 大直報修工時"><span style={{ fontSize: 11, color: '#888', cursor: 'help' }}>本期工時合計 <QuestionCircleOutlined style={{ color: '#bbb' }} /></span></Tooltip>}
              value={totalWorkHours} suffix="HR"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: '#FA8C16' }}
              prefix={<ClockCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${totalAbnormal > 0 ? '#FF4D4F' : '#52C41A'}` }}>
            <Statistic title={<Text style={{ fontSize: 11, color: '#888' }}>異常/未結案件</Text>} value={totalAbnormal} suffix="件"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: totalAbnormal > 0 ? '#FF4D4F' : '#52C41A' }}
              prefix={<WarningOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
            {totalAbnormal === 0 && <Tag color="success" style={{ marginTop: 4, fontSize: 11 }}>全部正常</Tag>}
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${totalOverdue > 0 ? '#C0392B' : '#52C41A'}` }}>
            <Statistic title={<Text style={{ fontSize: 11, color: '#888' }}>逾期未保養</Text>} value={totalOverdue} suffix="項"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: totalOverdue > 0 ? '#C0392B' : '#52C41A' }}
              prefix={<ExclamationCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* 各來源卡片 — 第一列：維護 / 巡檢 */}
      <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>各來源本期狀態</Divider>
      <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
        {SOURCE_CONFIG_ROW1.map((cfg) => (
          <Col key={cfg.key} xs={24} sm={12} md={6}>
            <SourceCard config={cfg}
              summary={summaryMap[cfg.key]}
              loading={loadingMap[cfg.key]}
              error={errorMap[cfg.key]}
            />
          </Col>
        ))}
      </Row>
      {/* 各來源卡片 — 第二列：報修 / 交辦 / 緊急事件 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {SOURCE_CONFIG_ROW2.map((cfg) => (
          <Col key={cfg.key} xs={24} sm={12} md={8}>
            <SourceCard config={cfg}
              summary={summaryMap[cfg.key]}
              loading={loadingMap[cfg.key]}
              error={errorMap[cfg.key]}
            />
          </Col>
        ))}
      </Row>

      {/* 決策圖表 */}
      <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>決策分析圖表</Divider>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={<><BarChartOutlined /> 各來源工項/案件數比較</>} size="small">
            {barData.length === 0 ? <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>暫無資料</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={barData} layout="vertical" margin={{ left: 10, right: 30 }}>
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <RcTooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
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
                  <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
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
          <Card title={<><LineChartOutlined /> 大直工務報修 — 12 個月案件趨勢</>} size="small"
            extra={<Text type="secondary" style={{ fontSize: 11 }}>{year} 年{month > 0 ? ` ${month} 月` : '（全年）'}</Text>}>
            {trendData.length === 0 || loadingDazhi ? (
              <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>{loadingDazhi ? '載入中…' : '暫無資料'}</div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={trendData} margin={{ left: 0, right: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <RcTooltip /><Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="總案件" stroke="#FA8C16" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                  <Line type="monotone" dataKey="已結案" stroke="#52C41A" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title={<><BarChartOutlined /> 各來源工時占比</>} size="small"
            extra={<Tooltip title="PM 工時為計劃分鐘換算；報修為實際工時；巡檢為記錄工時"><QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} /></Tooltip>}>
            {pieData.length === 0 ? <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 0' }}>暫無工時資料</div> : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75}>
                    {pieData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Pie>
                  <RcTooltip formatter={(v, n) => [`${v} HR`, n]} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      <Alert type="info" showIcon message="資料說明"
        description={<ul style={{ margin: 0, paddingLeft: 20, fontSize: 12 }}>
          <li>工時口徑：PM 為計劃工時（預估）；商場工務巡檢為巡檢工時記錄；大直工務報修為案件實際工時。</li>
          <li>各來源資料為獨立統計，不重複計算。</li>
          <li>整棟巡檢後端 API 建置中，暫不顯示資料。</li>
        </ul>}
      />
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // TAB B：每日累計（大直工務報修日別）
  // ════════════════════════════════════════════════════════════════════════════
  const dailyCols: ColumnsType<DailyAgg & { key: number }> = [
    {
      title: '日期', dataIndex: 'date', width: 110,
      render: (v: string) => <Text style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '星期', width: 65, align: 'center',
      render: (_: unknown, r: DailyAgg) => {
        const wd = ['日','一','二','三','四','五','六'][dayjs(r.date).day()]
        const isWeekend = dayjs(r.date).day() === 0 || dayjs(r.date).day() === 6
        return <Text style={{ fontSize: 12, color: isWeekend ? '#FF4D4F' : '#333' }}>週{wd}</Text>
      },
    },
    {
      title: '報修案件數', dataIndex: 'total', width: 100, align: 'center',
      sorter: (a: DailyAgg, b: DailyAgg) => a.total - b.total,
      render: (v: number) => <Text strong style={{ color: v > 0 ? '#1B3A5C' : '#ccc' }}>{v > 0 ? v : '—'}</Text>,
    },
    {
      title: '已結案', dataIndex: 'completed', width: 80, align: 'center',
      render: (v: number) => <Text style={{ fontSize: 12, color: '#52C41A' }}>{v > 0 ? v : '—'}</Text>,
    },
    {
      title: '結案率', width: 110, align: 'center',
      render: (_: unknown, r: DailyAgg) => {
        if (!r.total) return <Text style={{ color: '#ccc' }}>—</Text>
        const pct = Math.round((r.completed / r.total) * 100)
        return <Progress percent={pct} size="small" format={(p) => `${p}%`} strokeColor={pct >= 80 ? '#52C41A' : '#FAAD14'} />
      },
    },
    {
      title: '工時 (HR)', dataIndex: 'work_hours', width: 90, align: 'right',
      sorter: (a: DailyAgg, b: DailyAgg) => a.work_hours - b.work_hours,
      render: (v: number) => <Text strong style={{ color: v > 0 ? '#FA8C16' : '#ccc', fontSize: 12 }}>{v > 0 ? `${v} HR` : '—'}</Text>,
    },
  ]

  const TabDaily = (
    <>
      <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
        <Row gutter={[12, 8]} align="middle">
          <Col><Text strong style={{ fontSize: 13 }}>大直工務報修 日別統計</Text></Col>
          <Col>
            <Select value={dailyYear} options={yearOptions} style={{ width: 100 }}
              onChange={(v) => { setDailyYear(v); loadDaily(v, dailyMonth) }} />
          </Col>
          <Col>
            <Select value={dailyMonth} options={dailyMonthOptions} style={{ width: 90 }}
              onChange={(v) => { setDailyMonth(v); loadDaily(dailyYear, v) }} />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => loadDaily()} loading={loadingDaily}>重新整理</Button>
          </Col>
          <Col flex="auto" />
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>共 {dailyAggData.length} 個有記錄日</Text>
          </Col>
        </Row>
      </Card>

      <Alert type="warning" showIcon
        description="每日累計目前僅統計大直工務報修案件（以報修發生日聚合）。商場 PM、全棟 PM、工務巡檢等模組以批次/場次為單位，無每日工項分解，請至個別模組查看。"
        style={{ marginBottom: 12 }} />

      {dailyAggData.length > 0 && (
        <Card size="small" title={<><LineChartOutlined /> 報修案件日趨勢</>} style={{ marginBottom: 12 }}>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={dailyAggData} margin={{ left: 0, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" tick={{ fontSize: 10 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <RcTooltip
                formatter={(v, n) => [v, n === '案件數' ? '報修案件數' : '已結案']}
                labelFormatter={(l) => `${dailyYear}/${String(dailyMonth).padStart(2,'0')}/${String(l).padStart(2,'0')}`}
              />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="total"     name="案件數" fill="#FA8C16" radius={[3,3,0,0]} />
              <Bar dataKey="completed" name="已結案" fill="#52C41A" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <Spin spinning={loadingDaily}>
        <Card title={<Text strong>日別明細 — {dailyYear}/{String(dailyMonth).padStart(2,'0')}</Text>} bodyStyle={{ padding: '6px 0' }}>
          {dailyAggData.length === 0 && !loadingDaily ? (
            <Alert message="本月無報修記錄，或尚未選擇月份" type="info" showIcon style={{ margin: 12 }} />
          ) : (
            <Table<DailyAgg & { key: number }>
              dataSource={dailyAggData.map((r, i) => ({ ...r, key: i }))}
              columns={dailyCols}
              size="small"
              pagination={{ pageSize: 35, showTotal: t => `共 ${t} 日有記錄` }}
              summary={(rows) => {
                const t   = rows.reduce((s, r) => s + r.total,      0)
                const com = rows.reduce((s, r) => s + r.completed,  0)
                const wh  = Math.round(rows.reduce((s, r) => s + r.work_hours, 0) * 10) / 10
                const pct = t > 0 ? Math.round((com / t) * 100) : 0
                return (
                  <Table.Summary fixed>
                    <Table.Summary.Row style={{ background: '#f5f5f5', fontWeight: 600 }}>
                      <Table.Summary.Cell index={0} colSpan={2}><Text strong>合計</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={2} align="center"><Text strong>{t}</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={3} align="center"><Text strong style={{ color: '#52C41A' }}>{com}</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={4} align="center"><Text strong style={{ color: pct >= 80 ? '#52C41A' : '#FA8C16' }}>{pct}%</Text></Table.Summary.Cell>
                      <Table.Summary.Cell index={5} align="right"><Text strong style={{ color: '#FA8C16' }}>{wh} HR</Text></Table.Summary.Cell>
                    </Table.Summary.Row>
                  </Table.Summary>
                )
              }}
            />
          )}
        </Card>
      </Spin>
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // TAB C：每月累計
  // ════════════════════════════════════════════════════════════════════════════
  interface MonthlyRow {
    key: number; month: number
    pm_total: number; pm_completed: number; pm_rate: number; pm_overdue: number
    fb_total: number; fb_completed: number; fb_rate: number; fb_overdue: number
    dz_total: number; dz_completed: number; dz_rate: number
  }

  const monthlyCols: ColumnsType<MonthlyRow> = [
    {
      title: '月份', dataIndex: 'month', width: 60, fixed: 'left',
      render: (v: number) => {
        const isFuture = year > thisYear || (year === thisYear && v > thisMonth)
        return <Text style={{ fontSize: 12, color: isFuture ? '#bbb' : '#1B3A5C', fontWeight: 600 }}>{v} 月</Text>
      },
    },
    {
      title: <span style={{ color: '#1B3A5C' }}>商場例行維護</span>,
      children: [
        { title: '總計',   dataIndex: 'pm_total',     width: 60,  align: 'center', render: (v: number) => v > 0 ? <Text style={{ fontSize: 12 }}>{v}</Text> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '完成',   dataIndex: 'pm_completed', width: 60,  align: 'center', render: (v: number) => v > 0 ? <Text style={{ fontSize: 12, color: '#52C41A', fontWeight: 600 }}>{v}</Text> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '完成率', dataIndex: 'pm_rate',      width: 100, align: 'center', render: (v: number, r: MonthlyRow) => r.pm_total > 0 ? <Progress percent={v} size="small" format={(p) => `${p}%`} strokeColor={{ from: '#FAAD14', to: '#52C41A' }} /> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '逾期',   dataIndex: 'pm_overdue',   width: 55,  align: 'center', render: (v: number) => v > 0 ? <Badge count={v} color="#C0392B" /> : <Text style={{ color: '#ccc' }}>—</Text> },
      ],
    },
    {
      title: <span style={{ color: '#4BA8E8' }}>全棟例行維護</span>,
      children: [
        { title: '總計',   dataIndex: 'fb_total',     width: 60,  align: 'center', render: (v: number) => v > 0 ? <Text style={{ fontSize: 12 }}>{v}</Text> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '完成',   dataIndex: 'fb_completed', width: 60,  align: 'center', render: (v: number) => v > 0 ? <Text style={{ fontSize: 12, color: '#52C41A', fontWeight: 600 }}>{v}</Text> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '完成率', dataIndex: 'fb_rate',      width: 100, align: 'center', render: (v: number, r: MonthlyRow) => r.fb_total > 0 ? <Progress percent={v} size="small" format={(p) => `${p}%`} strokeColor={{ from: '#FAAD14', to: '#52C41A' }} /> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '逾期',   dataIndex: 'fb_overdue',   width: 55,  align: 'center', render: (v: number) => v > 0 ? <Badge count={v} color="#C0392B" /> : <Text style={{ color: '#ccc' }}>—</Text> },
      ],
    },
    {
      title: <span style={{ color: '#FA8C16' }}>大直工務報修</span>,
      children: [
        { title: '案件數', dataIndex: 'dz_total',     width: 70,  align: 'center', render: (v: number) => v > 0 ? <Text style={{ fontSize: 12 }}>{v}</Text> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '已結案', dataIndex: 'dz_completed', width: 70,  align: 'center', render: (v: number) => v > 0 ? <Text style={{ fontSize: 12, color: '#52C41A', fontWeight: 600 }}>{v}</Text> : <Text style={{ color: '#ccc' }}>—</Text> },
        { title: '結案率', dataIndex: 'dz_rate',      width: 100, align: 'center', render: (v: number, r: MonthlyRow) => r.dz_total > 0 ? <Progress percent={v} size="small" format={(p) => `${p}%`} strokeColor={{ from: '#FAAD14', to: '#52C41A' }} /> : <Text style={{ color: '#ccc' }}>—</Text> },
      ],
    },
  ]

  const monthlyChartData = monthlyRows.map(r => ({
    name: `${r.month}月`,
    商場PM:  r.pm_rate,
    全棟PM:  r.fb_rate,
    大直報修: r.dz_rate,
  }))

  const TabMonthly = (
    <>
      <Card size="small" style={{ marginBottom: 12, background: '#f9fbff' }}>
        <Row gutter={[12, 8]} align="middle">
          <Col><Text strong style={{ fontSize: 13 }}>月別完成率矩陣</Text></Col>
          <Col>
            <Select value={year} options={yearOptions} style={{ width: 100 }}
              onChange={(v) => { setYear(v); loadMonthly(v); loadDazhi(v, month) }} />
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => loadMonthly()} loading={loadingMonthly}>重新整理</Button>
          </Col>
        </Row>
      </Card>

      <Alert type="info" showIcon
        description="商場/全棟例行維護資料來自各月批次完成率；大直工務報修來自 12 個月趨勢。商場工務巡檢及整棟巡檢目前 API 不提供月別彙總，請至個別模組查看。"
        style={{ marginBottom: 12 }} />

      <Card size="small" title={<><LineChartOutlined /> 月別完成率趨勢（%）</>} style={{ marginBottom: 12 }}>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={monthlyChartData} margin={{ left: 0, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis domain={[0, 100]} tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
            <RcTooltip formatter={(v) => [`${v}%`]} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="商場PM"  stroke="#1B3A5C" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="全棟PM"  stroke="#4BA8E8" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="大直報修" stroke="#FA8C16" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Spin spinning={loadingMonthly}>
        <Card title={<Text strong>月別彙總表 — {year} 年</Text>} bodyStyle={{ padding: '6px 0' }}>
          <Table<MonthlyRow>
            dataSource={monthlyRows}
            columns={monthlyCols as ColumnsType<MonthlyRow>}
            size="small" pagination={false} scroll={{ x: 'max-content' }}
            rowClassName={(r) => {
              const isFuture = year > thisYear || (year === thisYear && r.month > thisMonth)
              return isFuture ? 'monthly-future-row' : ''
            }}
            summary={() => {
              const tots = monthlyRows.reduce((acc, r) => ({
                pm_total: acc.pm_total + r.pm_total, pm_completed: acc.pm_completed + r.pm_completed,
                fb_total: acc.fb_total + r.fb_total, fb_completed: acc.fb_completed + r.fb_completed,
                dz_total: acc.dz_total + r.dz_total, dz_completed: acc.dz_completed + r.dz_completed,
              }), { pm_total: 0, pm_completed: 0, fb_total: 0, fb_completed: 0, dz_total: 0, dz_completed: 0 })
              const pmR = tots.pm_total > 0 ? Math.round((tots.pm_completed / tots.pm_total) * 100) : 0
              const fbR = tots.fb_total > 0 ? Math.round((tots.fb_completed / tots.fb_total) * 100) : 0
              const dzR = tots.dz_total > 0 ? Math.round((tots.dz_completed / tots.dz_total) * 100) : 0
              return (
                <Table.Summary fixed>
                  <Table.Summary.Row style={{ background: '#f0f4f8', fontWeight: 600 }}>
                    <Table.Summary.Cell index={0}><Text strong>全年合計</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={1}  align="center"><Text strong>{tots.pm_total}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={2}  align="center"><Text strong style={{ color: '#52C41A' }}>{tots.pm_completed}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={3}  align="center"><Text strong style={{ color: pmR >= 80 ? '#52C41A' : '#FA8C16' }}>{pmR}%</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={4} />
                    <Table.Summary.Cell index={5}  align="center"><Text strong>{tots.fb_total}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={6}  align="center"><Text strong style={{ color: '#52C41A' }}>{tots.fb_completed}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={7}  align="center"><Text strong style={{ color: fbR >= 80 ? '#52C41A' : '#FA8C16' }}>{fbR}%</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={8} />
                    <Table.Summary.Cell index={9}  align="center"><Text strong>{tots.dz_total}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={10} align="center"><Text strong style={{ color: '#52C41A' }}>{tots.dz_completed}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={11} align="center"><Text strong style={{ color: dzR >= 80 ? '#52C41A' : '#FA8C16' }}>{dzR}%</Text></Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              )
            }}
          />
        </Card>
      </Spin>
    </>
  )

  // ════════════════════════════════════════════════════════════════════════════
  // TAB D：人員工時%（大直工務報修 top_hours 彙整）
  // ════════════════════════════════════════════════════════════════════════════
  const personHoursPctData = useMemo(() => {
    if (!personRanking.length || !totalPersonHours) return []
    return personRanking.map(r => ({
      ...r,
      pct: totalPersonHours > 0 ? Math.round((r.work_hours / totalPersonHours) * 1000) / 10 : 0,
    }))
  }, [personRanking, totalPersonHours])

  const pctColor = (pct: number) => pct >= 30 ? '#FF4D4F' : pct >= 15 ? '#FA8C16' : pct > 0 ? '#52C41A' : '#ccc'

  const personPctCols: ColumnsType<typeof personHoursPctData[0]> = [
    { title: '排名',     dataIndex: 'rank',       width: 55,  align: 'center', render: (v: number) => <Text strong>#{v}</Text> },
    { title: '人員',     dataIndex: 'name',       width: 110, render: (v: string) => <Text strong>{v}</Text> },
    { title: '工時(HR)', dataIndex: 'work_hours', width: 90,  align: 'right',
      sorter: (a, b) => a.work_hours - b.work_hours,
      render: (v: number) => <Text strong style={{ color: '#FA8C16' }}>{v.toFixed(1)}</Text> },
    {
      title: '工時佔比%', dataIndex: 'pct', width: 180, align: 'center',
      sorter: (a, b) => a.pct - b.pct,
      render: (v: number) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Progress percent={v} size="small" showInfo={false} strokeColor={pctColor(v)} style={{ flex: 1 }} />
          <Text style={{ fontSize: 12, color: pctColor(v), fontWeight: 600, minWidth: 42 }}>{v.toFixed(1)}%</Text>
        </div>
      ),
    },
    { title: '案件數', dataIndex: 'cases', width: 70, align: 'center',
      render: (v: number) => <Badge count={v} color="#4BA8E8" /> },
  ]

  const TabPersonPct = (
    <>
      <Alert type="info" showIcon
        description="人員工時佔比目前以大直工務報修 Dashboard API 中的工時案件（top_hours）彙整。商場例行維護（executor_name）、全棟例行維護、工務巡檢（inspector_name）人員工時需至各模組批次明細查看，無法在此跨來源整合。"
        style={{ marginBottom: 12 }} />

      {personHoursPctData.length === 0 ? (
        <Alert message="大直工務報修無人員工時資料（本期無記錄或尚未載入）" type="warning" showIcon />
      ) : (
        <>
          <Card size="small" title={<><TeamOutlined /> 人員工時占比分布（大直工務報修）</>} style={{ marginBottom: 12 }}>
            <Row gutter={[16, 0]}>
              <Col xs={24} md={10}>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={personHoursPctData.slice(0, 8)} dataKey="work_hours" nameKey="name"
                      cx="50%" cy="50%" innerRadius={50} outerRadius={85}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                      {personHoursPctData.slice(0, 8).map((_, i) => (
                        <Cell key={i} fill={['#1B3A5C','#4BA8E8','#52C41A','#FA8C16','#722ED1','#FF4D4F','#13C2C2','#EB2F96'][i % 8]} />
                      ))}
                    </Pie>
                    <RcTooltip formatter={(v: number, n) => [`${v.toFixed(1)} HR`, n]} />
                    <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                  </PieChart>
                </ResponsiveContainer>
              </Col>
              <Col xs={24} md={14}>
                <div style={{ padding: '16px 0' }}>
                  {(() => {
                    const top3pct = personHoursPctData.slice(0, 3).reduce((s, r) => s + r.pct, 0)
                    return (
                      <>
                        {top3pct > 70 && (
                          <Alert message={`人力集中度偏高：前 3 人工時佔比 ${top3pct.toFixed(1)}%，建議分散風險`}
                            type="warning" showIcon style={{ marginBottom: 12 }} />
                        )}
                        {[1, 3, 5].map(n => {
                          const pct = personHoursPctData.slice(0, n).reduce((s, r) => s + r.pct, 0)
                          return (
                            <div key={n} style={{ marginBottom: 10 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                                <Text style={{ fontSize: 12 }}>前 {n} 人</Text>
                                <Text strong style={{ fontSize: 12, color: pct > 70 ? '#FF4D4F' : '#333' }}>{pct.toFixed(1)}%</Text>
                              </div>
                              <Progress percent={Math.min(pct, 100)} strokeColor={pct > 70 ? '#FF4D4F' : '#FA8C16'} showInfo={false} size="small" />
                            </div>
                          )
                        })}
                        <Text type="secondary" style={{ fontSize: 11 }}>共 {personHoursPctData.length} 位人員 · 合計 {totalPersonHours.toFixed(1)} HR</Text>
                      </>
                    )
                  })()}
                </div>
              </Col>
            </Row>
          </Card>

          <Card title={<Text strong>人員工時佔比明細</Text>} bodyStyle={{ padding: '6px 0' }}>
            <Table dataSource={personHoursPctData} columns={personPctCols} size="small"
              pagination={{ pageSize: 20, showTotal: t => `共 ${t} 人` }} />
          </Card>
        </>
      )}

      <Card size="small" title="其他來源人員資料入口" style={{ marginTop: 12 }}>
        <Row gutter={[8, 8]}>
          {[
            { label: '商場例行維護 — 各批次執行人員', route: '/mall/periodic-maintenance',        color: '#1B3A5C' },
            { label: '全棟例行維護 — 各批次執行人員', route: '/mall/full-building-maintenance',   color: '#4BA8E8' },
            { label: '商場工務巡檢 — 各樓層巡檢人員', route: '/mall-facility-inspection/dashboard', color: '#722ED1' },
            { label: '整棟巡檢 — 各樓層巡檢人員',     route: '/full-building-inspection/dashboard',color: '#52C41A' },
          ].map(s => (
            <Col key={s.route} xs={24} sm={12}>
              <Button type="link" icon={<RightOutlined />} style={{ color: s.color }} onClick={() => navigate(s.route)}>
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
  const rankingCols: ColumnsType<typeof personRanking[0]> = [
    {
      title: '排名', dataIndex: 'rank', width: 55, align: 'center',
      render: (v: number) => {
        const medal: Record<number, string> = { 1: '🥇', 2: '🥈', 3: '🥉' }
        return medal[v]
          ? <span style={{ fontSize: 18 }}>{medal[v]}</span>
          : <Text strong style={{ color: '#999' }}>#{v}</Text>
      },
    },
    { title: '人員', dataIndex: 'name', width: 110, render: (v: string) => <Text strong>{v}</Text> },
    {
      title: '工時 (HR)', dataIndex: 'work_hours', width: 120, align: 'right',
      sorter: (a, b) => a.work_hours - b.work_hours, defaultSortOrder: 'descend',
      render: (v: number) => (
        <Text strong style={{ fontSize: 16, color: '#1B3A5C' }}>
          {v.toFixed(1)}<Text style={{ fontSize: 11, color: '#888', marginLeft: 2 }}>HR</Text>
        </Text>
      ),
    },
    {
      title: '占比%', width: 190, align: 'center',
      render: (_: unknown, r: typeof personRanking[0]) => {
        const pct = totalPersonHours > 0 ? Math.round((r.work_hours / totalPersonHours) * 1000) / 10 : 0
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Progress percent={pct} size="small" showInfo={false} strokeColor={pctColor(pct)} style={{ flex: 1 }} />
            <Text style={{ fontSize: 12, color: pctColor(pct), fontWeight: 600, minWidth: 42 }}>{pct.toFixed(1)}%</Text>
          </div>
        )
      },
    },
    {
      title: '案件數', dataIndex: 'cases', width: 70, align: 'center',
      sorter: (a, b) => a.cases - b.cases,
      render: (v: number) => <Badge count={v} color="#4BA8E8" />,
    },
  ]

  const TabRanking = (
    <>
      <Alert type="info" showIcon
        description="人員工時排名以大直工務報修 Dashboard top_hours 資料彙整（以 acceptor/closer 欄位為人員識別）。其他來源（PM 執行人員、巡檢人員）請至各模組批次明細查看。"
        style={{ marginBottom: 12 }} />

      {personRanking.length === 0 ? (
        <Alert message="大直工務報修無人員排名資料（本期無記錄或尚未載入）" type="warning" showIcon />
      ) : (
        <>
          <Card size="small" title={<><TrophyOutlined /> 人員工時排名（大直工務報修）</>} style={{ marginBottom: 12 }}>
            <ResponsiveContainer width="100%" height={Math.max(180, personRanking.length * 28)}>
              <BarChart data={[...personRanking].reverse()} layout="vertical" margin={{ left: 10, right: 50 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} unit="H" />
                <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 11 }} />
                <RcTooltip formatter={(v: number, _name, props) => {
                  const pct = totalPersonHours > 0 ? ((props.payload.work_hours / totalPersonHours) * 100).toFixed(1) : 0
                  return [`${v.toFixed(1)} HR (${pct}%)`]
                }} />
                <Bar dataKey="work_hours" name="工時(HR)" radius={[0, 4, 4, 0]}>
                  {[...personRanking].reverse().map((_, i) => (
                    <Cell key={i} fill={['#FA8C16','#4BA8E8','#52C41A','#722ED1','#FF4D4F','#13C2C2','#1B3A5C','#EB2F96'][i % 8]} />
                  ))}
                </Bar>
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
                    <Table.Summary.Cell index={4} align="center">
                      <Text strong>{personRanking.reduce((s, r) => s + r.cases, 0)}</Text>
                    </Table.Summary.Cell>
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
  const tabItems = [
    { key: 'dashboard', label: <><LineChartOutlined /> A. Dashboard</>,  children: TabDashboard },
    { key: 'daily',     label: <><TableOutlined />     B. 每日累計</>,   children: TabDaily },
    { key: 'monthly',   label: <><TableOutlined />     C. 每月累計</>,   children: TabMonthly },
    { key: 'person_pct',label: <><TeamOutlined />      D. 人員工時%</>,  children: TabPersonPct },
    { key: 'ranking',   label: <><TrophyOutlined />    人員排名</>,      children: TabRanking },
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

      <Row align="middle" justify="space-between" style={{ marginBottom: 16 }}>
        <Col>
          <Space align="baseline">
            <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
              <ShopOutlined style={{ marginRight: 8 }} />
              {NAV_PAGE.mallMgmtDashboard}
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>Mall Management Overview · 5 來源整合</Text>
          </Space>
        </Col>
      </Row>

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
