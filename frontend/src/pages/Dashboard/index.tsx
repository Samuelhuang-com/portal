/**
 * 集團管理 Portal 首頁 — 總覽 Dashboard
 *
 * 版面規範（PROTECTED.md）：
 *  - KPI 卡片：4 欄 Row、Card size="small"、無 border
 *  - 品牌色：primary #1B3A5C、accent #4BA8E8
 *  - Breadcrumb：每頁頂部，不可移除
 *  - 工作狀態色：已完成=#52c41a, 進行中=#1677ff, 非本月=#8c8c8c, 待排程=#faad14
 *
 * 資料來源（Promise.allSettled 平行呼叫，互不依賴）：
 *  - GET /api/v1/dashboard/kpi              → 飯店客房保養 + 庫存 + 同步狀態
 *  - GET /api/v1/mall/dashboard/summary     → 商場巡檢（B1F/B2F/RF）+ 本月週期保養
 *  - GET /api/v1/security/dashboard/summary → 保全巡檢（7 Sheets）今日摘要
 *  - GET /api/v1/dashboard/graph            → 關聯圖譜（GraphView，ROW 4）
 *  - GET /api/v1/luqun-repair/dashboard     → 商場工務報修 KPI（year/month 篩選）
 *  - GET /api/v1/dazhi-repair/dashboard     → 飯店工務部 KPI（year/month 篩選）
 *  - GET /api/v1/hotel/daily-hours          → 飯店工項類別案件數（year/month 篩選）
 *  - GET /api/v1/mall/daily-hours           → 商場工項類別案件數（year/month 篩選）
 *  - GET /api/v1/work-category-analysis/stats → 明細分析工時表（year/month，sources=all）
 */
import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Typography, Tag, Table, Collapse,
  Spin, Tooltip, Progress, Space, Button, Breadcrumb, Divider, Badge, Select,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, CheckCircleOutlined,
  ClockCircleOutlined, SyncOutlined, ExclamationCircleOutlined,
  RightOutlined, SafetyOutlined, ShopOutlined,
  AlertOutlined, BuildOutlined, ToolOutlined,
  DollarOutlined, RiseOutlined, WarningOutlined, BankOutlined,
  ArrowUpOutlined, ArrowDownOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-tw'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

import { dashboardApi, type DashboardKPI, type SyncRecord, type DashboardTrend, type ClosureStats } from '@/api/dashboard'
import { fetchDashboardSummary } from '@/api/mallDashboard'
import { fetchSecurityDashboardSummary } from '@/api/securityPatrol'
import type { DashboardSummary as MallSummary } from '@/types/mallDashboard'
import type { SecurityDashboardSummary } from '@/types/securityPatrol'
import { fetchDashboard as fetchLuqunDashboard } from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhiDashboard } from '@/api/dazhiRepair'
import type { DashboardData as RepairDashboardData, TypeDistItem } from '@/types/luqunRepair'
import { getBudgetDashboard, type DashboardData as BudgetDashboardData } from '@/api/budget'
import {
  fetchStats,
  type CategoryStats, type HoursRow, type PersonHoursRow, type PersonRankingItem,
  CATEGORY_TAG_COLORS,
} from '@/api/workCategoryAnalysis'
import { fetchHotelDailyHours, type HotelDailyHoursData,
         fetchHotelMonthlyHours, type HotelMonthlyHoursData } from '@/api/hotelOverview'
import { fetchMallDailyHours, type MallDailyHoursData,
         fetchMallMonthlyHours, type MallMonthlyHoursData } from '@/api/mallOverview'
import ExecMetricsCard from '@/components/ExecMetrics'

dayjs.extend(relativeTime)
dayjs.locale('zh-tw')

const { Title, Text } = Typography

// ── PROTECTED 色彩常數（禁止修改）────────────────────────────────────────────
const C = {
  primary: '#1B3A5C',
  accent:  '#4BA8E8',
  success: '#52c41a',
  danger:  '#cf1322',
  warning: '#faad14',
  gray:    '#8c8c8c',
}

// ── 完成率 → 顏色輔助 ─────────────────────────────────────────────────────────
function rateColor(rate: number): string {
  if (rate >= 80) return C.success
  if (rate >= 50) return C.warning
  return C.danger
}

// ── 金額格式化 ─────────────────────────────────────────────────────────────────
const fmtMoney = (n: number) =>
  new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 }).format(n)

// ── 群組卡一句話結論 helper ────────────────────────────────────────────────────
function hotelConclusion(rm: DashboardKPI['room_maintenance'] | undefined, rate: number): string {
  if (!rm) return ''
  if (rate >= 80) return '本月客房保養進度良好，各項目狀態正常。'
  if (rate >= 50) return `完成率 ${rate.toFixed(1)}%，仍有 ${rm.pending} 項待排程、${rm.in_progress} 項進行中，建議持續追蹤。`
  return `客房保養完成率偏低（${rate.toFixed(1)}%），待排程與進行中項目較多，建議優先處理。`
}

function mallConclusion(mallData: MallSummary | null, rate: number): string {
  if (!mallData) return ''
  const overdue = mallData.pm.overdue_items
  if (rate >= 80 && overdue === 0) return '各樓層巡檢進度良好，本月週期保養無逾期。'
  if (overdue > 0 && rate < 80) return `樓層巡檢完成率 ${rate.toFixed(1)}%，本月週期保養有 ${overdue} 項逾期，請優先處理。`
  if (overdue > 0) return `本月週期保養有 ${overdue} 項逾期，建議優先處理。`
  return `樓層巡檢完成率 ${rate.toFixed(1)}%，進度尚可，請持續追蹤。`
}

function secConclusion(secData: SecurityDashboardSummary | null, rate: number): string {
  if (!secData) return ''
  const ab = secData.abnormal_items_all
  if (rate >= 80 && ab === 0) return '今日巡檢完成率良好，無異常項目。'
  if (ab > 0 && rate < 50) return `今日巡檢完成率偏低（${rate.toFixed(1)}%），且有 ${ab} 項異常，需優先追蹤。`
  if (ab > 0) return `今日有 ${ab} 項巡檢異常，建議確認處理進度。`
  return `今日巡檢完成率 ${rate.toFixed(1)}%，請確認未查項目。`
}

function budgetConclusion(bd: BudgetDashboardData | null): string {
  if (!bd) return '預算資料載入中…'
  const s = bd.summary
  const dq = bd.data_quality
  const totalDq = dq.dq_issue_count + dq.missing_amount_count + dq.unresolved_plan_count
  if (s.overrun_count > 0)
    return `本年度執行率 ${s.exec_rate.toFixed(1)}%，已有 ${s.overrun_count} 項超支，請優先追蹤。`
  if (s.near_overrun_count > 0)
    return `本年度執行率 ${s.exec_rate.toFixed(1)}%，有 ${s.near_overrun_count} 項即將超支，請注意預算控管。`
  if (totalDq > 0)
    return `預算執行率 ${s.exec_rate.toFixed(1)}%，資料品質仍有 ${totalDq} 項異常，建議優先修正。`
  return `本年度預算執行率 ${s.exec_rate.toFixed(1)}%，目前無超支風險，整體狀況正常。`
}

function repairSummaryText(data: RepairDashboardData | null): string {
  if (!data?.kpi) return ''
  const kpi = data.kpi
  const closeRate = kpi.total > 0 ? Math.round((kpi.completed / kpi.total) * 100) : null
  const topPending = data.top_uncompleted?.[0] as (typeof data.top_uncompleted[0] & { pending_days?: number }) | undefined
  const maxDays = topPending?.pending_days ?? null
  const typeTop = data.type_dist?.[0]
  if (kpi.uncompleted === 0) return '本月報修案件已全數結案，狀況良好。'
  if (maxDays != null && maxDays >= 14) return `結案率 ${closeRate}%，最久未結案達 ${maxDays} 天，建議優先跟進。`
  if (typeTop) return `目前 ${kpi.uncompleted} 件未結案，主要集中於「${typeTop.type}」類型。`
  return `目前有 ${kpi.uncompleted} 件未結案，請確認進度。`
}

// ── 同步狀態 Badge ────────────────────────────────────────────────────────────
function SyncBadge({ status }: { status: string }) {
  const map: Record<string, { status: 'success' | 'error' | 'processing' | 'warning' | 'default'; label: string }> = {
    success: { status: 'success',    label: '成功' },
    error:   { status: 'error',      label: '失敗' },
    running: { status: 'processing', label: '執行中' },
    partial: { status: 'warning',    label: '部分成功' },
  }
  const s = map[status] ?? { status: 'default', label: status }
  return <Badge status={s.status} text={s.label} />
}

// ── 快速入口連結 ──────────────────────────────────────────────────────────────
function QuickLink({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <span
      onClick={onClick}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 2,
        fontSize: 12, color: C.accent, cursor: 'pointer',
        padding: '2px 8px', borderRadius: 4,
        background: '#e6f4ff', marginRight: 4, marginBottom: 4,
        userSelect: 'none',
      }}
    >
      {label} <RightOutlined style={{ fontSize: 10 }} />
    </span>
  )
}

// ── 飯店每日累計表（Dashboard 用，邏輯與 HotelMgmtDashboard TAB B 相同）──────────
// ── exec 明細分析表：共用 helper + 4 個 table components ─────────────────────
const EXEC_T = {
  primary:   '#1B3A5C',
  warning:   '#faad14',
  textMuted: '#8c8c8c',
}

function execRenderHr(v: number) {
  if (v === 0) return <span style={{ color: '#ddd', fontSize: 14 }}>—</span>
  return <span style={{ fontSize: 14, color: v >= 8 ? '#cf1322' : v >= 4 ? '#fa8c16' : '#333' }}>{v.toFixed(1)}</span>
}

function execRenderCat(val: string) {
  if (val === 'TOTAL') return <Typography.Text strong style={{ color: EXEC_T.primary }}>TOTAL</Typography.Text>
  return <Tag color={CATEGORY_TAG_COLORS[val] ?? 'default'} style={{ fontSize: 13 }}>{val}</Tag>
}

type ExecHoursRow = HoursRow & { key: number }

function ExecDailyTable({ stats }: { stats: CategoryStats | null }) {
  const daily = stats?.daily_hours
  if (!daily || !daily.days.length)
    return <Typography.Text type="secondary" style={{ fontSize: 14 }}>請選擇月份（非全年）以查看每日累計</Typography.Text>
  const cols = [
    { title: '類別', dataIndex: 'category', fixed: 'left' as const, width: 100, render: execRenderCat },
    ...daily.days.map((d, i) => ({
      title: (
        <div style={{ textAlign: 'center' as const }}>
          <div style={{ fontSize: 12 }}>{d}</div>
          <div style={{ fontSize: 11, color: EXEC_T.textMuted }}>{daily.weekdays[i]}</div>
        </div>
      ),
      key: `d${d}`, width: 36, align: 'right' as const,
      render: (_: unknown, r: ExecHoursRow) => execRenderHr(r.hours[i] ?? 0),
    })),
    {
      title: 'TOTAL', dataIndex: 'total', key: 'tot', width: 58, align: 'right' as const,
      sorter: (a: ExecHoursRow, b: ExecHoursRow) => a.total - b.total,
      render: (v: number, r: ExecHoursRow) =>
        <Typography.Text strong style={{ color: r.category === 'TOTAL' ? EXEC_T.primary : undefined }}>{v.toFixed(1)}</Typography.Text>,
    },
    {
      title: '%', dataIndex: 'pct', key: 'pct', width: 50, align: 'right' as const,
      render: (v: number, r: ExecHoursRow) =>
        <Typography.Text style={{ color: r.category === 'TOTAL' ? EXEC_T.textMuted : EXEC_T.warning,
          fontWeight: r.category !== 'TOTAL' ? 600 : 400 }}>{v.toFixed(1)}%</Typography.Text>,
    },
  ]
  return (
    <Table<ExecHoursRow>
      dataSource={daily.rows.map((r, i) => ({ ...r, key: i }))}
      columns={cols} pagination={false} size="small" scroll={{ x: 'max-content' }}
      rowClassName={r => r.category === 'TOTAL' ? 'exec-total-row' : ''}
    />
  )
}

function ExecMonthlyTable({ stats }: { stats: CategoryStats | null }) {
  const monthly = stats?.monthly_hours
  const thisY = dayjs().year()
  const thisM = dayjs().month() + 1
  const yr = stats?.meta?.year ?? thisY
  const cols = [
    { title: '類別', dataIndex: 'category', fixed: 'left' as const, width: 100, render: execRenderCat },
    ...Array.from({ length: 12 }, (_, i) => {
      const m = i + 1
      const isFuture = yr > thisY || (yr === thisY && m > thisM)
      return {
        title: <span style={{ fontSize: 13 }}>{m}月</span>,
        key: `m${m}`, width: 56, align: 'right' as const,
        render: (_: unknown, r: ExecHoursRow) => isFuture
          ? <span style={{ color: '#ccc', fontSize: 14 }}>—</span>
          : execRenderHr(r.hours[i] ?? 0),
      }
    }),
    {
      title: 'TOTAL', dataIndex: 'total', key: 'tot', width: 62, align: 'right' as const,
      sorter: (a: ExecHoursRow, b: ExecHoursRow) => a.total - b.total,
      render: (v: number, r: ExecHoursRow) =>
        <Typography.Text strong style={{ color: r.category === 'TOTAL' ? EXEC_T.primary : undefined }}>{v.toFixed(1)}</Typography.Text>,
    },
    {
      title: '%', dataIndex: 'pct', key: 'pct', width: 54, align: 'right' as const,
      render: (v: number, r: ExecHoursRow) =>
        <Typography.Text style={{ color: r.category === 'TOTAL' ? EXEC_T.textMuted : EXEC_T.warning,
          fontWeight: r.category !== 'TOTAL' ? 600 : 400 }}>{v.toFixed(1)}%</Typography.Text>,
    },
  ]
  return (
    <Table<ExecHoursRow>
      dataSource={(monthly?.rows ?? []).map((r, i) => ({ ...r, key: i }))}
      columns={cols} pagination={false} size="small" scroll={{ x: 'max-content' }}
      rowClassName={r => r.category === 'TOTAL' ? 'exec-total-row' : ''}
    />
  )
}

type ExecPersonRow = PersonHoursRow & { key: number }

function ExecPersonTable({ stats }: { stats: CategoryStats | null }) {
  const ph = stats?.person_hours
  if (!ph || !ph.persons.length)
    return <Typography.Text type="secondary">暫無人員工時資料</Typography.Text>
  const cols = [
    { title: '類別', dataIndex: 'category', fixed: 'left' as const, width: 100, render: execRenderCat },
    ...ph.persons.map((p, i) => ({
      title: <span style={{ fontSize: 13 }}>{p}</span>,
      key: `p${i}`, width: 70, align: 'right' as const,
      render: (_: unknown, r: ExecPersonRow) => {
        const v = r.pct_by_person[i] ?? 0
        const c = v >= 30 ? '#cf1322' : v >= 15 ? '#fa8c16' : v > 0 ? '#52c41a' : EXEC_T.textMuted
        return <span style={{ fontSize: 14, color: c, fontWeight: v >= 15 ? 700 : 400 }}>
          {v > 0 ? `${v.toFixed(1)}%` : '–'}
        </span>
      },
    })),
  ]
  return (
    <Table<ExecPersonRow>
      dataSource={ph.rows.map((r, i) => ({ ...r, key: i }))}
      columns={cols} pagination={false} size="small" scroll={{ x: 'max-content' }}
    />
  )
}

type ExecRankRow = PersonRankingItem & { key: number }

function burdenLabel(avgHr: number): { text: string; color: string } {
  if (avgHr >= 3.0) return { text: '需關注', color: '#cf1322' }
  if (avgHr >= 2.5) return { text: '工時偏高', color: '#fa8c16' }
  return { text: '正常', color: '#52c41a' }
}

function ExecRankingTable({ stats }: { stats: CategoryStats | null }) {
  const ranking = stats?.person_ranking ?? []
  return (
    <Table<ExecRankRow>
      dataSource={ranking.map((r, i) => ({ ...r, key: i }))}
      columns={[
        { title: '#', dataIndex: 'rank', width: 44, align: 'center' as const,
          render: (v: number) => <Typography.Text strong style={{ color: EXEC_T.primary }}>{v}</Typography.Text> },
        { title: '人員', dataIndex: 'person', width: 88 },
        { title: 'HR', dataIndex: 'hours', width: 72, align: 'right' as const,
          sorter: (a: ExecRankRow, b: ExecRankRow) => a.hours - b.hours,
          defaultSortOrder: 'descend' as const,
          render: (v: number) => <Typography.Text strong>{v.toFixed(1)}</Typography.Text> },
        { title: '占比', dataIndex: 'pct', width: 62, align: 'right' as const,
          render: (v: number) => <Typography.Text style={{ color: EXEC_T.warning, fontWeight: 600 }}>{v}%</Typography.Text> },
        { title: '主要類別', dataIndex: 'top_category', width: 90,
          render: (v: string) => <Tag color={CATEGORY_TAG_COLORS[v] ?? 'default'} style={{ fontSize: 13 }}>{v}</Tag> },
        { title: '來源', dataIndex: 'source_labels', width: 130,
          render: (v: string[]) => <Space size={2}>{(v ?? []).map((s: string) => <Tag key={s} style={{ fontSize: 12, margin: 0 }}>{s}</Tag>)}</Space> },
      ]}
      pagination={{ pageSize: 15, showSizeChanger: false }}
      size="small"
    />
  )
}

function ExecBurdenTable({ stats }: { stats: CategoryStats | null }) {
  const ranking = stats?.person_ranking ?? []
  return (
    <>
      <Table<ExecRankRow>
        dataSource={ranking.map((r, i) => ({ ...r, key: i }))}
        columns={[
          { title: '人員', dataIndex: 'person', width: 88,
            render: (v: string) => <Typography.Text style={{ fontSize: 14 }}>{v}</Typography.Text> },
          { title: '工時(HR)', dataIndex: 'hours', width: 80, align: 'right' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => a.hours - b.hours,
            render: (v: number) => <Typography.Text strong style={{ fontSize: 14 }}>{v.toFixed(1)}</Typography.Text> },
          { title: '件數', dataIndex: 'cases', width: 62, align: 'right' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => (a.cases ?? 0) - (b.cases ?? 0),
            render: (v: number) => <Typography.Text style={{ fontSize: 14 }}>{v ?? 0}</Typography.Text> },
          { title: '均工時/件', dataIndex: 'avg_hr', width: 90, align: 'right' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => (a.avg_hr ?? 0) - (b.avg_hr ?? 0),
            render: (v: number) => <Typography.Text style={{ fontSize: 14 }}>{(v ?? 0).toFixed(1)}</Typography.Text> },
          { title: '主要類別', dataIndex: 'top_category', width: 90,
            render: (v: string) => <Tag color={CATEGORY_TAG_COLORS[v] ?? 'default'} style={{ fontSize: 13 }}>{v}</Tag> },
          { title: '判斷', key: 'burden', width: 88, align: 'center' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => (a.avg_hr ?? 0) - (b.avg_hr ?? 0),
            render: (_: unknown, r: ExecRankRow) => {
              const { text, color } = burdenLabel(r.avg_hr ?? 0)
              return <Tag color={color} style={{ fontSize: 13, fontWeight: 600 }}>{text}</Tag>
            } },
        ]}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        size="small"
        scroll={{ x: 'max-content' }}
      />
      <div style={{ marginTop: 6, color: '#aaa', fontSize: 12 }}>
        均工時/件：≥3.0HR 🔴需關注 · 2.5–3.0HR 🟠工時偏高 · &lt;2.5HR 🟢正常
      </div>
    </>
  )
}

// 飯店工項類別 → 路由對應
const HOTEL_CAT_ROUTES: Record<string, string> = {
  現場報修: '/dazhi-repair',
  例行維護: '/hotel/periodic-maintenance',
  每日巡檢: '/hotel/daily-inspection',
}

function HotelDailyTable({ data }: { data: HotelDailyHoursData }) {
  const navigate = useNavigate()
  const n = data.days.length
  const zeroes = (): number[] => Array(n).fill(0)
  const addH = (a?: number[], b?: number[]): number[] =>
    zeroes().map((_, i) => (a?.[i] ?? 0) + (b?.[i] ?? 0))
  const find = (name: string) => data.rows.find(r => r.category === name)
  const CATS = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢']
  const catCases: Record<string, number[]> = {
    現場報修: find('飯店工務部')?.cases ?? zeroes(),
    上級交辦: zeroes(),
    緊急事件: zeroes(),
    例行維護: addH(addH(find('客房保養管理')?.cases, find('飯店週期保養')?.cases), find('IHG客房保養')?.cases),
    每日巡檢: addH(find('飯店每日巡檢')?.cases, find('保全巡檢')?.cases),
  }
  const grandTotal = CATS.reduce((s, c) => s + catCases[c].reduce((a, b) => a + b, 0), 0)
  type DRow = { key: string; category: string; cases: number[]; total: number; pct: number }
  const rows: DRow[] = CATS.map(cat => {
    const cases = catCases[cat]
    const total = cases.reduce((a, b) => a + b, 0)
    return { key: cat, category: cat, cases, total, pct: grandTotal > 0 ? Math.round(total / grandTotal * 1000) / 10 : 0 }
  })
  const totalCases = data.days.map((_, i) => CATS.reduce((s, c) => s + (catCases[c][i] ?? 0), 0))
  rows.push({ key: 'TOTAL', category: 'TOTAL', cases: totalCases, total: totalCases.reduce((a, b) => a + b, 0), pct: 100 })

  const goTo = (cat: string) => { const r = HOTEL_CAT_ROUTES[cat]; if (r) navigate(r) }

  const columns = [
    {
      title: '工項類別', dataIndex: 'category', key: 'cat', fixed: 'left' as const, width: 90,
      render: (v: string) => {
        const route = HOTEL_CAT_ROUTES[v]
        return route
          ? <a onClick={() => navigate(route)} style={{ fontSize: 15, fontWeight: 600, color: '#1B3A5C' }}>{v}</a>
          : <Text style={{ fontSize: 15, fontWeight: v === 'TOTAL' ? 700 : 400 }}>{v}</Text>
      },
    },
    ...data.days.map((d, i) => ({
      title: (
        <div style={{ textAlign: 'center' as const, lineHeight: 1.2 }}>
          <div style={{ fontSize: 13 }}>{d}</div>
          <div style={{ fontSize: 12, color: '#aaa' }}>{data.weekdays[i]}</div>
        </div>
      ),
      key: `d${d}`, width: 38, align: 'center' as const,
      render: (_: unknown, row: DRow) => {
        const v = row.cases[i] ?? 0
        if (v === 0 || row.category === 'TOTAL' || !HOTEL_CAT_ROUTES[row.category])
          return <span style={{ fontSize: 14, color: v > 0 ? '#333' : '#ddd' }}>{v > 0 ? v : '—'}</span>
        return (
          <a onClick={() => goTo(row.category)}
            style={{ fontSize: 14, color: '#1B3A5C', fontWeight: 600, cursor: 'pointer' }}>
            {v}
          </a>
        )
      },
    })),
    {
      title: '案件數', key: 'total', width: 70, align: 'right' as const,
      render: (_: unknown, row: DRow) => {
        if (row.category === 'TOTAL' || !HOTEL_CAT_ROUTES[row.category] || row.total === 0)
          return <Text strong style={{ fontSize: 15, color: row.category === 'TOTAL' ? '#0d6b4e' : '#333' }}>{row.total}</Text>
        return (
          <a onClick={() => goTo(row.category)}
            style={{ fontSize: 15, fontWeight: 700, color: '#1B3A5C', cursor: 'pointer' }}>
            {row.total}
          </a>
        )
      },
    },
    {
      title: '%', key: 'pct', width: 54, align: 'right' as const,
      render: (_: unknown, row: DRow) => (
        <Text style={{ fontSize: 14, color: row.category === 'TOTAL' ? '#888' : '#FA8C16', fontWeight: row.category !== 'TOTAL' ? 600 : 400 }}>
          {row.pct.toFixed(1)}%
        </Text>
      ),
    },
  ]
  return (
    <>
      <Table dataSource={rows} columns={columns} pagination={false} size="small"
        scroll={{ x: 'max-content' }} rowClassName={(r) => r.category === 'TOTAL' ? 'dash-daily-total-row' : ''} />
      <style>{`.dash-daily-total-row td { background: #f5f5f5 !important; font-weight: 600; }`}</style>
    </>
  )
}

// 商場工項類別 → 路由對應
const MALL_CAT_ROUTES: Record<string, string> = {
  現場報修: '/luqun-repair',
  例行維護: '/mall/periodic-maintenance',
  每日巡檢: '/mall-facility-inspection',
}

// ── 商場每日累計表（Dashboard 用）────────────────────────────────────────────
function MallDailyTable({ data }: { data: MallDailyHoursData }) {
  const navigate = useNavigate()
  const rows = data.rows.map((r, i) => ({ ...r, key: i }))
  type DRow = typeof rows[0]

  const goTo = (cat: string) => { const r = MALL_CAT_ROUTES[cat]; if (r) navigate(r) }

  const columns = [
    {
      title: '工項類別', dataIndex: 'category', key: 'cat', fixed: 'left' as const, width: 90,
      render: (v: string) => {
        const route = MALL_CAT_ROUTES[v]
        return route
          ? <a onClick={() => navigate(route)} style={{ fontSize: 15, fontWeight: 600, color: '#1B3A5C' }}>{v}</a>
          : <Text style={{ fontSize: 15, fontWeight: v === 'TOTAL' ? 700 : 400 }}>{v}</Text>
      },
    },
    ...data.days.map((d, i) => ({
      title: (
        <div style={{ textAlign: 'center' as const, lineHeight: 1.2 }}>
          <div style={{ fontSize: 13 }}>{d}</div>
          <div style={{ fontSize: 12, color: '#aaa' }}>{data.weekdays[i]}</div>
        </div>
      ),
      key: `d${d}`, width: 38, align: 'center' as const,
      render: (_: unknown, row: DRow) => {
        const v = row.cases?.[i] ?? 0
        if (v === 0 || row.category === 'TOTAL' || !MALL_CAT_ROUTES[row.category])
          return <span style={{ fontSize: 14, color: v > 0 ? '#333' : '#ddd' }}>{v > 0 ? v : '—'}</span>
        return (
          <a onClick={() => goTo(row.category)}
            style={{ fontSize: 14, color: '#1B3A5C', fontWeight: 600, cursor: 'pointer' }}>
            {v}
          </a>
        )
      },
    })),
    {
      title: '案件數', key: 'total', width: 70, align: 'right' as const,
      render: (_: unknown, row: DRow) => {
        if (row.category === 'TOTAL' || !MALL_CAT_ROUTES[row.category] || (row.cases_total ?? 0) === 0)
          return <Text strong style={{ fontSize: 15, color: row.category === 'TOTAL' ? '#1B3A5C' : '#333' }}>{row.cases_total}</Text>
        return (
          <a onClick={() => goTo(row.category)}
            style={{ fontSize: 15, fontWeight: 700, color: '#1B3A5C', cursor: 'pointer' }}>
            {row.cases_total}
          </a>
        )
      },
    },
    {
      title: '%', key: 'pct', width: 54, align: 'right' as const,
      render: (_: unknown, row: DRow) => (
        <Text style={{ fontSize: 14, color: row.category === 'TOTAL' ? '#888' : '#FA8C16', fontWeight: row.category !== 'TOTAL' ? 600 : 400 }}>
          {(row.cases_pct ?? 0).toFixed(1)}%
        </Text>
      ),
    },
  ]
  return (
    <Table dataSource={rows} columns={columns} pagination={false} size="small"
      scroll={{ x: 'max-content' }} rowClassName={(r) => r.category === 'TOTAL' ? 'dash-daily-total-row' : ''} />
  )
}

// ── 預算管理摘要卡 ────────────────────────────────────────────────────────────
function BudgetSummaryCard({
  data, onNavigate,
}: {
  data: BudgetDashboardData | null
  onNavigate: (path: string) => void
}) {
  const s = data?.summary
  const dq = data?.data_quality

  const execColor = !s ? C.gray
    : s.exec_rate >= 100 ? C.danger
    : s.exec_rate >= 85  ? C.warning
    : C.success

  const totalDq = dq ? dq.dq_issue_count + dq.missing_amount_count + dq.unresolved_plan_count : 0

  return (
    <Card
      size="small"
      bordered={false}
      style={{ borderTop: `3px solid ${C.primary}`, marginBottom: 0 }}
    >
      {/* ── 標題列 ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BankOutlined style={{ color: C.primary, fontSize: 16 }} />
          <Text strong style={{ color: C.primary, fontSize: 15 }}>預算管理</Text>
          {data?.year && (
            <Tag color="default" style={{ fontSize: 11 }}>{data.year.budget_year} 年度</Tag>
          )}
        </div>
        <span
          onClick={() => onNavigate('/budget/dashboard')}
          style={{ fontSize: 11, color: C.accent, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 2 }}
        >
          查看詳情 <RightOutlined style={{ fontSize: 9 }} />
        </span>
      </div>

      {!s ? (
        <div style={{ color: C.gray, fontSize: 12, padding: '8px 0' }}>
          <ExclamationCircleOutlined style={{ marginRight: 4 }} />預算資料載入中…
        </div>
      ) : (
        <>
          {/* ── 一句話結論 ── */}
          <div style={{
            background: s.overrun_count > 0 ? '#fff1f0' : s.near_overrun_count > 0 ? '#fffbe6' : '#f6ffed',
            borderRadius: 6, padding: '6px 10px', marginBottom: 12,
            borderLeft: `3px solid ${s.overrun_count > 0 ? C.danger : s.near_overrun_count > 0 ? C.warning : C.success}`,
          }}>
            <Text style={{ fontSize: 12, color: s.overrun_count > 0 ? C.danger : s.near_overrun_count > 0 ? '#ad6800' : '#389e0d' }}>
              {budgetConclusion(data)}
            </Text>
          </div>

          {/* ── KPI 數字列 ── */}
          <Row gutter={[16, 8]}>
            {/* 年度總預算 */}
            <Col xs={12} sm={6} lg={4}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.primary }}>
                  {fmtMoney(s.total_budget)}
                </div>
                <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>年度總預算</div>
              </div>
            </Col>
            {/* 年度總實績 */}
            <Col xs={12} sm={6} lg={4}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: C.primary }}>
                  {fmtMoney(s.total_actual)}
                </div>
                <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>年度總實績</div>
              </div>
            </Col>
            {/* 預算餘額 */}
            <Col xs={12} sm={6} lg={4}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: s.variance >= 0 ? C.success : C.danger }}>
                  {s.variance >= 0
                    ? <><ArrowDownOutlined style={{ fontSize: 10 }} /> {fmtMoney(s.variance)}</>
                    : <><ArrowUpOutlined  style={{ fontSize: 10 }} /> {fmtMoney(Math.abs(s.variance))}</>
                  }
                </div>
                <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>預算餘額</div>
              </div>
            </Col>
            {/* 執行率 */}
            <Col xs={12} sm={6} lg={4}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: execColor, lineHeight: 1.2 }}>
                  {s.exec_rate.toFixed(1)}%
                </div>
                <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>執行率</div>
              </div>
            </Col>
            {/* 風險警示 */}
            <Col xs={24} sm={12} lg={8}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', height: '100%' }}>
                {s.overrun_count > 0 && (
                  <Tag
                    color="error"
                    icon={<RiseOutlined />}
                    style={{ fontSize: 11, cursor: 'pointer' }}
                    onClick={() => onNavigate('/budget/dashboard')}
                  >
                    超支 {s.overrun_count} 項
                  </Tag>
                )}
                {s.near_overrun_count > 0 && (
                  <Tag
                    color="warning"
                    icon={<WarningOutlined />}
                    style={{ fontSize: 11, cursor: 'pointer' }}
                    onClick={() => onNavigate('/budget/dashboard')}
                  >
                    即將超支 {s.near_overrun_count} 項
                  </Tag>
                )}
                {totalDq > 0 && (
                  <Tag
                    color="default"
                    style={{ fontSize: 11, cursor: 'pointer' }}
                    onClick={() => onNavigate('/budget/dashboard')}
                  >
                    資料異常 {totalDq} 筆
                  </Tag>
                )}
                {s.overrun_count === 0 && s.near_overrun_count === 0 && totalDq === 0 && (
                  <Tag color="success" style={{ fontSize: 11 }}>✓ 無超支風險</Tag>
                )}
              </div>
            </Col>
          </Row>

          {/* ── 執行率進度條 ── */}
          <Progress
            percent={Math.min(s.exec_rate, 100)}
            showInfo={false}
            strokeColor={execColor}
            size="small"
            style={{ marginTop: 10, marginBottom: 8 }}
          />

          {/* ── 快速入口 ── */}
          <div style={{ marginTop: 4 }}>
            <QuickLink label="預算 Dashboard"   onClick={() => onNavigate('/budget/dashboard')} />
            <QuickLink label="預算比較報表"      onClick={() => onNavigate('/budget/reports/budget-vs-actual')} />
            <QuickLink label="費用交易明細"      onClick={() => onNavigate('/budget/transactions')} />
          </div>
        </>
      )}
    </Card>
  )
}

// ── 今日重點摘要卡（P1-C）────────────────────────────────────────────────────
function TodaySummaryCard({
  totalAlerts, mallAbnormal, secAbnormal, hotelPending, repairPending, budgetAlert,
  mallRate, secRate, hotelRate,
  luqunData, dazhiData,
  budgetData,
}: {
  totalAlerts: number
  mallAbnormal: number
  secAbnormal: number
  hotelPending: number
  repairPending: number
  budgetAlert: number
  mallRate: number
  secRate: number
  hotelRate: number
  luqunData: RepairDashboardData | null
  dazhiData: RepairDashboardData | null
  budgetData: BudgetDashboardData | null
}) {
  // 找出完成率最低的群組
  const rateGroups = [
    { name: '商場巡檢', rate: mallRate },
    { name: '保全巡檢', rate: secRate },
    { name: '客房保養', rate: hotelRate },
  ]
  const lowestGroup = rateGroups.reduce((a, b) => a.rate < b.rate ? a : b)

  // 工務最久未結案
  const luqunMaxDays = (luqunData?.top_uncompleted?.[0] as any)?.pending_days ?? null
  const dazhiMaxDays = (dazhiData?.top_uncompleted?.[0] as any)?.pending_days ?? null
  const maxRepairDays = luqunMaxDays != null && dazhiMaxDays != null
    ? Math.max(luqunMaxDays, dazhiMaxDays)
    : (luqunMaxDays ?? dazhiMaxDays)

  // 組成重點列表
  type Item = { level: 'error' | 'warning' | 'success'; text: string }
  const items: Item[] = []

  if (totalAlerts > 0) {
    items.push({ level: 'error', text: `全域待關注共 ${totalAlerts} 項（商場 ${mallAbnormal}、保全 ${secAbnormal}、客房 ${hotelPending}、工務 ${repairPending}、預算 ${budgetAlert}）` })
  } else {
    items.push({ level: 'success', text: '今日全域無待關注項目，所有模組狀況正常。' })
  }

  if (lowestGroup.rate < 80) {
    items.push({ level: lowestGroup.rate < 50 ? 'error' : 'warning', text: `「${lowestGroup.name}」完成率最低（${lowestGroup.rate.toFixed(1)}%），建議優先追蹤。` })
  }

  if (maxRepairDays != null && maxRepairDays >= 7) {
    items.push({ level: maxRepairDays >= 14 ? 'error' : 'warning', text: `工務最久未結案已達 ${maxRepairDays} 天，請安排跟進。` })
  }

  if (budgetData && budgetData.summary.overrun_count > 0) {
    items.push({ level: 'error', text: `預算已有 ${budgetData.summary.overrun_count} 項超支，請優先確認超支科目。` })
  } else if (budgetData && budgetData.summary.near_overrun_count > 0) {
    items.push({ level: 'warning', text: `預算有 ${budgetData.summary.near_overrun_count} 項即將超支，建議主管關注。` })
  }

  if (secAbnormal > 0) {
    items.push({ level: 'warning', text: `今日保全巡檢異常 ${secAbnormal} 項，請確認異常處理進度。` })
  }

  const colorMap = { error: C.danger, warning: C.warning, success: C.success }
  const bgMap    = { error: '#fff1f0', warning: '#fffbe6', success: '#f6ffed' }

  return (
    <Card
      size="small"
      bordered={false}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertOutlined style={{ color: totalAlerts > 0 ? C.danger : C.success }} />
          <Text strong style={{ color: C.primary, fontSize: 14 }}>今日重點摘要</Text>
        </div>
      }
      style={{ marginBottom: 0 }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {items.slice(0, 5).map((item, i) => (
          <div
            key={i}
            style={{
              background: bgMap[item.level],
              borderLeft: `3px solid ${colorMap[item.level]}`,
              borderRadius: 4,
              padding: '5px 10px',
            }}
          >
            <Text style={{ fontSize: 12, color: colorMap[item.level] }}>
              {item.level === 'error' ? '⚠ ' : item.level === 'warning' ? '△ ' : '✓ '}
              {item.text}
            </Text>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ── 工務報修主管摘要卡（商場 / 飯店 共用）────────────────────────────────────
function RepairSummaryCard({
  label, data, color, accentColor, onNavigate, monthLabel, colLg,
}: {
  label:       string
  data:        RepairDashboardData | null
  color:       string
  accentColor: string
  onNavigate:  () => void
  monthLabel?: string  // e.g. "2026 / 5 月"
  colLg?:      number  // 覆寫 Col 的 lg span，預設 12
}) {
  const kpi         = data?.kpi
  const typeTop     = data?.type_dist?.[0]
  const topPending  = data?.top_uncompleted?.[0]

  // 結案率（本月）
  const closeRate = kpi && kpi.total > 0
    ? Math.round((kpi.completed / kpi.total) * 100)
    : null

  // 逾期警示：第一名未結案天數
  const maxPendingDays = (topPending as (typeof topPending & { pending_days?: number }) | undefined)?.pending_days ?? null

  return (
    <Col xs={24} lg={colLg ?? 12}>
      <Card
        size="small"
        bordered={false}
        style={{ borderTop: `3px solid ${color}`, height: '100%' }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ToolOutlined style={{ color, fontSize: 15 }} />
              <Text strong style={{ color, fontSize: 14 }}>{label}</Text>
              <Tag color="default" style={{ fontSize: 11, marginLeft: 4 }}>
                {monthLabel ?? `${dayjs().format('M')} 月`}
              </Tag>
            </div>
            <span
              onClick={onNavigate}
              style={{ fontSize: 11, color: accentColor, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 2 }}
            >
              查看詳情 <RightOutlined style={{ fontSize: 9 }} />
            </span>
          </div>
        }
      >
        {!kpi ? (
          <div style={{ color: C.gray, fontSize: 12, padding: '8px 0' }}>
            <ExclamationCircleOutlined style={{ marginRight: 4 }} />資料載入中…
          </div>
        ) : (
          <>
            {/* ── KPI 數字列 ── */}
            <Row gutter={[8, 8]} style={{ marginBottom: 10 }}>
              {/* 報修總數 */}
              <Col span={4}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color, lineHeight: 1.2 }}>
                    {kpi.total}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>報修總數</div>
                </div>
              </Col>
              {/* 結案數 */}
              <Col span={4}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: C.success, lineHeight: 1.2 }}>
                    {kpi.completed}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>已結案</div>
                </div>
              </Col>
              {/* 未結案 */}
              <Col span={4}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{
                    fontSize: 22, fontWeight: 700, lineHeight: 1.2,
                    color: kpi.uncompleted > 0 ? C.danger : C.success,
                  }}>
                    {kpi.uncompleted}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>未結案</div>
                </div>
              </Col>
              {/* 結案率 */}
              <Col span={4}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{
                    fontSize: 22, fontWeight: 700, lineHeight: 1.2,
                    color: closeRate == null ? C.gray
                      : closeRate >= 80 ? C.success
                      : closeRate >= 50 ? C.warning : C.danger,
                  }}>
                    {closeRate != null ? `${closeRate}%` : '—'}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>結案率</div>
                </div>
              </Col>
              {/* 平均結案天數 */}
              <Col span={4}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{
                    fontSize: 22, fontWeight: 700, lineHeight: 1.2,
                    color: kpi.avg_close_days == null ? C.gray
                      : kpi.avg_close_days <= 7 ? C.success
                      : kpi.avg_close_days <= 30 ? C.warning : C.danger,
                  }}>
                    {kpi.avg_close_days != null ? kpi.avg_close_days.toFixed(1) : '—'}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>均結案天</div>
                </div>
              </Col>
              {/* 工時 */}
              <Col span={4}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: accentColor, lineHeight: 1.2 }}>
                    {kpi.total_work_hours > 0 ? kpi.total_work_hours.toFixed(0) : '—'}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>工時(h)</div>
                </div>
              </Col>
            </Row>

            {/* ── 結案率進度條 ── */}
            <Progress
              percent={closeRate ?? 0}
              showInfo={false}
              strokeColor={
                closeRate == null ? C.gray
                  : closeRate >= 80 ? C.success
                  : closeRate >= 50 ? C.warning : C.danger
              }
              size="small"
              style={{ marginBottom: 8 }}
            />

            {/* ── 異常提醒 + 最高類型 ── */}
            <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {/* 最高報修類型 */}
              {typeTop && (
                <Tag color="blue" style={{ fontSize: 11 }}>
                  ↑ {typeTop.type} {typeTop.count} 件
                </Tag>
              )}
              {/* 逾期警示 */}
              {maxPendingDays != null && maxPendingDays >= 14 && (
                <Tag color="error" style={{ fontSize: 11 }}>
                  ⚠ 最久未結 {maxPendingDays} 天
                </Tag>
              )}
              {maxPendingDays != null && maxPendingDays >= 7 && maxPendingDays < 14 && (
                <Tag color="warning" style={{ fontSize: 11 }}>
                  ⚠ 最久未結 {maxPendingDays} 天
                </Tag>
              )}
              {kpi.uncompleted === 0 && (
                <Tag color="success" style={{ fontSize: 11 }}>✓ 全部結案</Tag>
              )}
            </div>

            {/* ── 一句話摘要（P1-B）── */}
            {repairSummaryText(data) && (
              <div style={{
                background: kpi.uncompleted === 0 ? '#f6ffed' : maxPendingDays != null && maxPendingDays >= 14 ? '#fff1f0' : '#fffbe6',
                borderLeft: `3px solid ${kpi.uncompleted === 0 ? C.success : maxPendingDays != null && maxPendingDays >= 14 ? C.danger : C.warning}`,
                borderRadius: 4, padding: '4px 8px',
              }}>
                <Text style={{
                  fontSize: 11,
                  color: kpi.uncompleted === 0 ? '#389e0d' : maxPendingDays != null && maxPendingDays >= 14 ? C.danger : '#ad6800',
                }}>
                  {repairSummaryText(data)}
                </Text>
              </div>
            )}

            {/* ── 當月金額 ── */}
            <Divider style={{ margin: '8px 0 6px' }} />
            <div style={{
              background: '#f0faff',
              border: `1px solid ${accentColor}44`,
              borderRadius: 6,
              padding: '6px 10px',
            }}>
              <div style={{
                textAlign: 'center', fontWeight: 600, fontSize: 15,
                color: accentColor, marginBottom: 6,
              }}>
                當月金額
                <span style={{ fontWeight: 400, fontSize: 14, color: C.gray }}>
                  {monthLabel ?? `${dayjs().format('YYYY 年 M 月')}`}
                </span>
              </div>
              {([
                ['委外+維修', (kpi.month_outsource_fee ?? 0) + (kpi.month_maintenance_fee ?? 0)],
                ['扣款費用',  kpi.month_deduction_fee ?? 0],
                ['扣款專櫃',  kpi.month_deduction_counter ?? 0],
              ] as [string, number][]).map(([lbl, val]) => (
                <div key={lbl} style={{
                  display: 'flex', justifyContent: 'space-between',
                  fontSize: 15, padding: '1px 0', color: '#555',
                }}>
                  <span>{lbl}</span>
                  <span style={{ color: val > 0 ? '#333' : C.gray }}>
                    {val > 0 ? fmtMoney(val) : '-'}
                  </span>
                </div>
              ))}
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                fontSize: 15, fontWeight: 700, borderTop: `1px solid ${accentColor}33`,
                marginTop: 4, paddingTop: 4, color: accentColor,
              }}>
                <span>當月小計</span>
                <span>{(kpi.month_total_fee ?? 0) > 0 ? fmtMoney(kpi.month_total_fee ?? 0) : '-'}</span>
              </div>
            </div>

          </>
        )}
      </Card>
    </Col>
  )
}
function GroupCardTitle({
  icon, label, color,
}: {
  icon: React.ReactNode; label: string; color: string
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ color, fontSize: 15 }}>{icon}</span>
      <Text strong style={{ color: C.primary, fontSize: 14 }}>{label}</Text>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// 主元件
// ══════════════════════════════════════════════════════════════════════════════
export default function DashboardPage() {
  const navigate = useNavigate()
  const today    = dayjs().format('YYYY/MM/DD')

  const [hotelKpi,    setHotelKpi]    = useState<DashboardKPI | null>(null)
  const [mallData,    setMallData]    = useState<MallSummary | null>(null)
  const [secData,     setSecData]     = useState<SecurityDashboardSummary | null>(null)
  const [trendData,   setTrendData]   = useState<DashboardTrend | null>(null)
  const [closureData, setClosureData] = useState<ClosureStats | null>(null)
  const [luqunData,   setLuqunData]   = useState<RepairDashboardData | null>(null)
  const [dazhiData,   setDazhiData]   = useState<RepairDashboardData | null>(null)
  const [budgetData,  setBudgetData]  = useState<BudgetDashboardData | null>(null)
  const [trendDays,   setTrendDays]   = useState<7 | 30>(7)
  const [loading,     setLoading]     = useState(true)
  const [refreshed,   setRefreshed]   = useState<Date>(new Date())

  // 年月篩選狀態（工務報修 + 工項比較表）
  const [selectedYear,   setSelectedYear]   = useState<number>(dayjs().year())
  const [selectedMonth,  setSelectedMonth]  = useState<number>(dayjs().month() + 1)
  const [execStats,        setExecStats]        = useState<CategoryStats | null>(null)
  const [hotelMonthlyData, setHotelMonthlyData] = useState<HotelMonthlyHoursData | null>(null)
  const [mallMonthlyData,  setMallMonthlyData]  = useState<MallMonthlyHoursData | null>(null)
  const [hotelDailyData,   setHotelDailyData]   = useState<HotelDailyHoursData | null>(null)
  const [mallDailyData,    setMallDailyData]    = useState<MallDailyHoursData | null>(null)
  // 受控 Collapse activeKey（全收合/全展開用）
  const ALL_DAILY_KEYS    = ['hotel-daily', 'mall-daily']
  const ALL_ANALYSIS_KEYS = ['exec-daily', 'exec-monthly', 'exec-burden']
  const [dailyKeys,    setDailyKeys]    = useState<string[]>([])
  const [analysisKeys, setAnalysisKeys] = useState<string[]>([])
  const allExpanded = dailyKeys.length + analysisKeys.length ===
    ALL_DAILY_KEYS.length + ALL_ANALYSIS_KEYS.length
  const toggleAll = () => {
    if (allExpanded) { setDailyKeys([]); setAnalysisKeys([]) }
    else             { setDailyKeys(ALL_DAILY_KEYS); setAnalysisKeys(ALL_ANALYSIS_KEYS) }
  }

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [hotel, mall, sec, trend, closure, luqun, dazhi, budget, hotelMon, mallMon, hotelDay, mallDay, execSt] =
        await Promise.allSettled([
          dashboardApi.kpi().then(r => r.data),
          fetchDashboardSummary(today),
          fetchSecurityDashboardSummary(today),
          dashboardApi.trend(trendDays).then(r => r.data),
          dashboardApi.closureStats().then(r => r.data),
          fetchLuqunDashboard(selectedYear, selectedMonth),
          fetchDazhiDashboard(selectedYear, selectedMonth),
          getBudgetDashboard().then(r => r.data),
          fetchHotelMonthlyHours(selectedYear),
          fetchMallMonthlyHours(selectedYear),
          fetchHotelDailyHours(selectedYear, selectedMonth),
          fetchMallDailyHours(selectedYear, selectedMonth),
          fetchStats({ year: selectedYear, month: selectedMonth, sources: 'all', category: 'all', person: 'all' }),
        ])
      if (hotel.status      === 'fulfilled') setHotelKpi(hotel.value)
      if (mall.status       === 'fulfilled') setMallData(mall.value)
      if (sec.status        === 'fulfilled') setSecData(sec.value)
      if (trend.status      === 'fulfilled') setTrendData(trend.value)
      if (closure.status    === 'fulfilled') setClosureData(closure.value)
      if (luqun.status      === 'fulfilled') setLuqunData(luqun.value)
      if (dazhi.status      === 'fulfilled') setDazhiData(dazhi.value as unknown as RepairDashboardData)
      if (budget.status     === 'fulfilled') setBudgetData(budget.value)
      if (hotelMon.status   === 'fulfilled') setHotelMonthlyData(hotelMon.value)
      if (mallMon.status    === 'fulfilled') setMallMonthlyData(mallMon.value)
      if (hotelDay.status   === 'fulfilled') setHotelDailyData(hotelDay.value)
      if (mallDay.status    === 'fulfilled') setMallDailyData(mallDay.value)
      if (execSt.status    === 'fulfilled') setExecStats(execSt.value)
      setRefreshed(new Date())
    } finally {
      setLoading(false)
    }
  }, [today, trendDays, selectedYear, selectedMonth])

  useEffect(() => { loadAll() }, [loadAll])

  // ── 工項類別比較表（飯店 vs 商場）────────────────────────────────────────────
  const categoryComparison = useMemo(() => {
    const CATS = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢']
    const mi = selectedMonth - 1

    // 飯店：多來源合併（與 HotelMgmtDashboard TAB C 相同邏輯）
    const hFind = (name: string) => hotelMonthlyData?.rows.find(r => r.category === name)
    const hc = (name: string) => hFind(name)?.cases[mi] ?? 0
    const hotelCatCases: Record<string, number> = {
      現場報修: hc('飯店工務部'),
      上級交辦: 0,
      緊急事件: 0,
      例行維護: hc('客房保養管理') + hc('飯店週期保養') + hc('IHG客房保養'),
      每日巡檢: hc('飯店每日巡檢') + hc('保全巡檢'),
    }

    // 商場：API 直接回傳五類名稱，直接 find
    const mFind = (name: string) => mallMonthlyData?.rows.find(r => r.category === name)
    const mc = (name: string) => mFind(name)?.cases[mi] ?? 0

    return CATS.map(cat => ({
      key:        cat,
      category:   cat,
      hotelCases: hotelCatCases[cat] ?? 0,
      mallCases:  mc(cat),
    }))
  }, [hotelMonthlyData, mallMonthlyData, selectedMonth])

  // ── 骨架畫面 ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ textAlign: 'center', paddingTop: 80 }}>
        <Spin size="large" tip="載入集團總覽…" />
      </div>
    )
  }

  // ── 衍生值計算 ────────────────────────────────────────────────────────────
  const rm  = hotelKpi?.room_maintenance
  const sys = hotelKpi?.system

  const mallRate  = mallData?.inspection?.completion_rate  ?? 0
  const secRate   = secData?.completion_rate_all          ?? 0
  const hotelRate = rm?.completion_rate                   ?? 0

  // 全域待關注：商場異常 + 商場PM逾期 + 保全異常 + 客房未完成 + 工務未結案 + 預算超支/即將超支
  const mallAbnormal  = (mallData?.inspection?.abnormal_items ?? 0) + (mallData?.pm?.overdue_items ?? 0)
  const secAbnormal   = secData?.abnormal_items_all ?? 0
  const hotelPending  = rm?.total_incomplete ?? 0
  const repairPending = (luqunData?.kpi?.uncompleted ?? 0) + (dazhiData?.kpi?.uncompleted ?? 0)
  const budgetAlert   = (budgetData?.summary?.overrun_count ?? 0) + (budgetData?.summary?.near_overrun_count ?? 0)
  const totalAlerts   = mallAbnormal + secAbnormal + hotelPending + repairPending + budgetAlert
  const alertColor    = totalAlerts > 0 ? C.danger : C.success

  // 同步狀態
  const syncOk    = sys?.last_sync_status === 'success'
  const syncColor = syncOk ? C.success : (sys?.last_sync_status ? C.danger : C.gray)

  // 近期同步欄位（保留原有設計）
  const syncColumns = [
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => <SyncBadge status={s} />,
    },
    {
      title: '方式', dataIndex: 'triggered_by', key: 'triggered_by', width: 65,
      render: (t: string) => {
        const m: Record<string, string> = { scheduler: '排程', manual: '手動', api: 'API' }
        return <Text type="secondary" style={{ fontSize: 12 }}>{m[t] ?? t}</Text>
      },
    },
    {
      title: '筆數', dataIndex: 'records_fetched', key: 'records_fetched', width: 55,
      render: (n: number | null) => (n != null ? n : '—'),
    },
    {
      title: '時間', dataIndex: 'started_at', key: 'started_at',
      render: (t: string | null) =>
        t ? (
          <Tooltip title={dayjs(t).format('YYYY-MM-DD HH:mm:ss')}>
            <Text type="secondary" style={{ fontSize: 12 }}>{dayjs(t).fromNow()}</Text>
          </Tooltip>
        ) : '—',
    },
    {
      title: '說明', dataIndex: 'error_msg', key: 'error_msg', ellipsis: true,
      render: (msg: string | null) =>
        msg ? <Text type="danger" style={{ fontSize: 11 }}>{msg}</Text> : null,
    },
  ]

  return (
    <div>
      {/* ── Breadcrumb（PROTECTED：每頁必有，不可移除）──────────────── */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <><HomeOutlined /> 首頁</> },
          { title: 'Dashboard' },
        ]}
      />

      {/* ── 頁頭 ─────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'flex-start',
        justifyContent: 'space-between', marginBottom: 16,
      }}>
        <div>
          <Title level={4} style={{ margin: 0, color: C.primary }}>集團管理總覽</Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {dayjs(today, 'YYYY/MM/DD').format('YYYY 年 MM 月 DD 日')} 即時概況
          </Text>
        </div>
        <Space direction="vertical" align="end" size={2}>
          {sys?.last_sync_at && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              <SyncOutlined style={{ marginRight: 4 }} />
              資料同步：{dayjs(sys.last_sync_at).format('MM/DD HH:mm')}
            </Text>
          )}
          <Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              更新於 {dayjs(refreshed).format('HH:mm:ss')}
            </Text>
            <Button size="small" icon={<ReloadOutlined />} onClick={loadAll} loading={loading}>
              重新整理
            </Button>
          </Space>
        </Space>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.3 — 工務報修主管摘要（飯店 + 商場 + 工項比較表）
      ══════════════════════════════════════════════════════════════ */}
      {/* Section Header — 工務報修 */}
      <Card
        size="small"
        bordered={false}
        style={{ borderTop: '3px solid #1B3A5C', marginBottom: 10 }}
        bodyStyle={{ padding: '10px 16px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ToolOutlined style={{ color: '#1B3A5C', fontSize: 16 }} />
            <Text strong style={{ color: '#1B3A5C', fontSize: 15 }}>工務報修</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {selectedYear} 年 {selectedMonth} 月
            </Text>
          </div>
        </div>
      </Card>

      {/* 年月篩選器 */}
      <Row justify="start" style={{ marginBottom: 8 }}>
        <Space>
          <Text type="secondary" style={{ fontSize: 13 }}>報修年月：</Text>
          <Select
            value={selectedYear}
            onChange={v => setSelectedYear(v)}
            style={{ width: 90 }}
            options={Array.from({ length: 3 }, (_, i) => {
              const y = dayjs().year() - i
              return { label: `${y} 年`, value: y }
            })}
          />
          <Select
            value={selectedMonth}
            onChange={v => setSelectedMonth(v)}
            style={{ width: 80 }}
            options={Array.from({ length: 12 }, (_, i) => ({
              label: `${i + 1} 月`, value: i + 1,
            }))}
          />
        </Space>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {/* 飯店工務部 */}
        <RepairSummaryCard
          label="飯店工務部"
          data={dazhiData}
          color="#0d6b4e"
          accentColor="#36b37e"
          onNavigate={() => navigate('/dazhi-repair')}
          monthLabel={`${selectedYear}/${String(selectedMonth).padStart(2, '0')}`}
          colLg={8}
        />
        {/* 商場工務報修 */}
        <RepairSummaryCard
          label="商場工務報修"
          data={luqunData}
          color="#1B3A5C"
          accentColor="#4BA8E8"
          onNavigate={() => navigate('/luqun-repair')}
          monthLabel={`${selectedYear}/${String(selectedMonth).padStart(2, '0')}`}
          colLg={8}
        />
        {/* 飯店/商場工項類別比較表 */}
        <Col xs={24} lg={8}>
          <Card
            size="small"
            title={
              <Space>
                <ToolOutlined style={{ color: C.primary }} />
                <Text strong style={{ color: C.primary, fontSize: 16 }}>
                  飯店／商場工項類別比較
                </Text>
              </Space>
            }
            style={{ borderTop: `3px solid ${C.primary}`, height: '100%' }}
          >
            <Table
              size="small"
              dataSource={categoryComparison}
              pagination={false}
              columns={[
                {
                  title: '工項類別',
                  dataIndex: 'category',
                  key: 'category',
                  width: 80,
                  render: (v: string) => <Text style={{ fontSize: 15 }}>{v}</Text>,
                },
                {
                  title: <Text style={{ fontSize: 15, color: '#0d6b4e' }}>飯店（件）</Text>,
                  dataIndex: 'hotelCases',
                  key: 'hotelCases',
                  align: 'right' as const,
                  render: (v: number) => (
                    <Text style={{ fontSize: 15, color: '#0d6b4e', fontWeight: 600 }}>{v}</Text>
                  ),
                },
                {
                  title: <Text style={{ fontSize: 15, color: C.primary }}>商場（件）</Text>,
                  dataIndex: 'mallCases',
                  key: 'mallCases',
                  align: 'right' as const,
                  render: (v: number) => (
                    <Text style={{ fontSize: 15, color: C.primary, fontWeight: 600 }}>{v}</Text>
                  ),
                },
                {
                  title: <Text style={{ fontSize: 15, color: '#555' }}>合計</Text>,
                  key: 'subtotal',
                  align: 'right' as const,
                  render: (_: unknown, r: { hotelCases: number; mallCases: number }) => (
                    <Text strong style={{ fontSize: 15 }}>{r.hotelCases + r.mallCases}</Text>
                  ),
                },
                {
                  title: <Text style={{ fontSize: 15, color: '#555' }}>占比</Text>,
                  key: 'pct',
                  align: 'right' as const,
                  render: (_: unknown, r: { hotelCases: number; mallCases: number }) => {
                    const grand = categoryComparison.reduce((s, x) => s + x.hotelCases + x.mallCases, 0)
                    const pct   = grand > 0 ? Math.round((r.hotelCases + r.mallCases) / grand * 100) : 0
                    return <Text style={{ fontSize: 15, color: pct >= 50 ? '#cf1322' : pct >= 20 ? '#fa8c16' : '#555' }}>{pct}%</Text>
                  },
                },
              ]}
              summary={() => {
                const totalHotel = categoryComparison.reduce((s, r) => s + r.hotelCases, 0)
                const totalMall  = categoryComparison.reduce((s, r) => s + r.mallCases,  0)
                const grand      = totalHotel + totalMall
                return (
                  <Table.Summary fixed>
                    <Table.Summary.Row style={{ background: '#f0f4f8', fontWeight: 700 }}>
                      <Table.Summary.Cell index={0}>
                        <Text strong style={{ fontSize: 15, color: '#555' }}>小計</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={1} align="right">
                        <Text strong style={{ fontSize: 15, color: '#0d6b4e' }}>{totalHotel}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={2} align="right">
                        <Text strong style={{ fontSize: 15, color: C.primary }}>{totalMall}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={3} align="right">
                        <Text strong style={{ fontSize: 15 }}>{grand}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={4} align="right">
                        <Text strong style={{ fontSize: 15 }}>100%</Text>
                      </Table.Summary.Cell>
                    </Table.Summary.Row>
                  </Table.Summary>
                )
              }}
            />
            {!hotelMonthlyData && !mallMonthlyData && (
              <div style={{ textAlign: 'center', color: '#bbb', padding: '12px 0', fontSize: 15 }}>
                數據載入中…
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.32 — 近12個月報修趨勢 + 報修類型分布（dazhiData，已載入）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 8 }}>
        {/* 左：近12個月報修趨勢 */}
        <Col xs={24} lg={14}>
          <Card title="近 12 個月報修趨勢（飯店工務部）" size="small" bodyStyle={{ padding: '12px 8px 8px' }}>
            {dazhiData?.trend_12m?.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={dazhiData.trend_12m} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={36} />
                  <RechartTooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="total"     stroke="#1B3A5C" strokeWidth={2} name="報修件數" dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="completed" stroke="#52C41A" strokeWidth={2} name="完成件數" dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb', fontSize: 13 }}>
                資料載入中…
              </div>
            )}
          </Card>
        </Col>

        {/* 右：報修類型分布 */}
        <Col xs={24} lg={10}>
          <Card title="報修類型分布（飯店工務部）" size="small" bodyStyle={{ padding: '12px 8px 8px' }}>
            {dazhiData?.type_dist?.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={dazhiData.type_dist as TypeDistItem[]}
                    dataKey="count"
                    nameKey="type"
                    cx="50%" cy="50%"
                    outerRadius={75}
                    label={({ type, percent }: { type: string; percent: number }) =>
                      percent > 0.04 ? `${type} ${(percent * 100).toFixed(0)}%` : ''
                    }
                    labelLine={false}
                  >
                    {(dazhiData.type_dist as TypeDistItem[]).map((_: TypeDistItem, idx: number) => (
                      <Cell key={idx} fill={['#1B3A5C','#4BA8E8','#52C41A','#FAAD14','#FF4D4F','#722ED1','#13C2C2','#FA8C16'][idx % 8]} />
                    ))}
                  </Pie>
                  <RechartTooltip formatter={(v: number, n: string) => [v, n]} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb', fontSize: 13 }}>
                資料載入中…
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.33 — 近12個月報修趨勢 + 報修類型分布（luqunData，已載入）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 8 }}>
        {/* 左：近12個月報修趨勢 */}
        <Col xs={24} lg={14}>
          <Card title="近 12 個月報修趨勢（商場工務報修）" size="small" bodyStyle={{ padding: '12px 8px 8px' }}>
            {luqunData?.trend_12m?.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={luqunData.trend_12m} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={36} />
                  <RechartTooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="total"     stroke="#1B3A5C" strokeWidth={2} name="報修件數" dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="completed" stroke="#52C41A" strokeWidth={2} name="完成件數" dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb', fontSize: 13 }}>
                資料載入中…
              </div>
            )}
          </Card>
        </Col>

        {/* 右：報修類型分布 */}
        <Col xs={24} lg={10}>
          <Card title="報修類型分布（商場工務報修）" size="small" bodyStyle={{ padding: '12px 8px 8px' }}>
            {luqunData?.type_dist?.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={luqunData.type_dist as TypeDistItem[]}
                    dataKey="count"
                    nameKey="type"
                    cx="50%" cy="50%"
                    outerRadius={75}
                    label={({ type, percent }: { type: string; percent: number }) =>
                      percent > 0.04 ? `${type} ${(percent * 100).toFixed(0)}%` : ''
                    }
                    labelLine={false}
                  >
                    {(luqunData.type_dist as TypeDistItem[]).map((_: TypeDistItem, idx: number) => (
                      <Cell key={idx} fill={['#1B3A5C','#4BA8E8','#52C41A','#FAAD14','#FF4D4F','#722ED1','#13C2C2','#FA8C16'][idx % 8]} />
                    ))}
                  </Pie>
                  <RechartTooltip formatter={(v: number, n: string) => [v, n]} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb', fontSize: 13 }}>
                資料載入中…
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.35 — 飯店 + 商場每日累計表（Collapse 預設折疊，與年月篩選連動）
      ══════════════════════════════════════════════════════════════ */}
      {/* 全收合 / 全展開 按鈕 */}
      <Row justify="start" style={{ marginBottom: 4 }}>
        <Button
          size="small"
          onClick={toggleAll}
          style={{ fontSize: 12, color: '#1B3A5C', borderColor: '#1B3A5C' }}
        >
          {allExpanded ? '⊖ 全收合' : '⊕ 全展開'}
        </Button>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: 8 }}>
        <Col xs={24}>
          <Collapse
            activeKey={dailyKeys}
            onChange={keys => setDailyKeys(keys as string[])}
            style={{ background: '#fff' }}
            items={[
              {
                key: 'hotel-daily',
                label: (
                  <Space>
                    <ToolOutlined style={{ color: '#0d6b4e' }} />
                    <Text strong style={{ color: '#0d6b4e', fontSize: 16 }}>
                      飯店每日累計案件數 — {selectedYear} 年 {selectedMonth} 月
                    </Text>
                  </Space>
                ),
                children: hotelDailyData
                  ? <HotelDailyTable data={hotelDailyData} />
                  : <div style={{ color: '#aaa', padding: '12px 0', textAlign: 'center' }}>資料載入中…</div>,
              },
              {
                key: 'mall-daily',
                label: (
                  <Space>
                    <ShopOutlined style={{ color: '#1B3A5C' }} />
                    <Text strong style={{ color: '#1B3A5C', fontSize: 16 }}>
                      商場每日累計案件數 — {selectedYear} 年 {selectedMonth} 月
                    </Text>
                  </Space>
                ),
                children: mallDailyData
                  ? <MallDailyTable data={mallDailyData} />
                  : <div style={{ color: '#aaa', padding: '12px 0', textAlign: 'center' }}>資料載入中…</div>,
              },
            ]}
          />
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.36 — 明細分析（工時表，仿 exec-dashboard，預設全收合）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Collapse
            activeKey={analysisKeys}
            onChange={keys => setAnalysisKeys(keys as string[])}
            style={{ background: '#fff' }}
            items={[
              {
                key: 'exec-daily',
                label: <Space><span>📅</span><Typography.Text strong style={{ fontSize: 16 }}>每日累計工時表 — {selectedYear} 年 {selectedMonth} 月</Typography.Text></Space>,
                children: <ExecDailyTable stats={execStats} />,
              },
              {
                key: 'exec-monthly',
                label: <Space><span>📆</span><Typography.Text strong style={{ fontSize: 16 }}>每月累計工時表 — {selectedYear} 年</Typography.Text></Space>,
                children: <ExecMonthlyTable stats={execStats} />,
              },
            ]}
          />
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.37 — 人員負荷與效率分析（獨立 Collapse）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Collapse
            activeKey={analysisKeys.includes('exec-burden') ? ['exec-burden'] : []}
            onChange={keys => {
              const rest = analysisKeys.filter(k => k !== 'exec-burden')
              setAnalysisKeys((keys as string[]).includes('exec-burden')
                ? [...rest, 'exec-burden']
                : rest)
            }}
            style={{ background: '#fff' }}
            items={[
              {
                key: 'exec-burden',
                label: <Space><span>🧮</span><Typography.Text strong style={{ fontSize: 16 }}>人員負荷與效率分析</Typography.Text></Space>,
                children: <ExecBurdenTable stats={execStats} />,
              },
            ]}
          />
        </Col>
      </Row>

      {/* ── HIDDEN_ROWS_04_TO_5 START: ROW 0.4~ROW5 暫時隱藏 ── */}
      {((): null => null)() /* HIDDEN */}

      {/* ── HIDDEN_ROW6_GRAPHVIEW: ROW 6 暫時隱藏 ── */}
    </div>
  )
}
