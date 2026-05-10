/**
 * 集團工務決策駕駛艙 — ExecWorkDashboard
 *
 * 以「集團管理總覽 Dashboard」為基礎，聚焦工務決策視角。
 * 不影響原始 Dashboard，雙頁面可同時並存比較。
 *
 * 資料來源（Promise.allSettled 平行呼叫，互不依賴）：
 *  - GET /api/v1/luqun-repair/dashboard       → 商場工務報修 KPI（year/month 篩選）
 *  - GET /api/v1/dazhi-repair/dashboard       → 飯店工務部 KPI（year/month 篩選）
 *  - GET /api/v1/hotel/monthly-hours          → 飯店工項類別月累計（year 篩選）
 *  - GET /api/v1/mall/monthly-hours           → 商場工項類別月累計（year 篩選）
 *  - GET /api/v1/hotel/daily-hours            → 飯店工項類別日累計（year/month 篩選）
 *  - GET /api/v1/mall/daily-hours             → 商場工項類別日累計（year/month 篩選）
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

import { fetchDashboard as fetchLuqunDashboard } from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhiDashboard } from '@/api/dazhiRepair'
import type { DashboardData as RepairDashboardData, TypeDistItem } from '@/types/luqunRepair'
import {
  fetchStats,
  type CategoryStats, type HoursRow, type PersonHoursRow, type PersonRankingItem,
  type CategorySourceMatrixItem,
  CATEGORY_TAG_COLORS,
} from '@/api/workCategoryAnalysis'
import { fetchHotelDailyHours, type HotelDailyHoursData,
         fetchHotelMonthlyHours, type HotelMonthlyHoursData } from '@/api/hotelOverview'
import { fetchMallDailyHours, type MallDailyHoursData,
         fetchMallMonthlyHours, type MallMonthlyHoursData } from '@/api/mallOverview'

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
// 飯店 vs 商場比較表
// ══════════════════════════════════════════════════════════════════════════════
interface UnitCompRow {
  key: string; unit: string; cases: number; hours: number
  completed: number; uncompleted: number; rate: number; topCat: string; isTotal?: boolean
}

function UnitComparisonTable({
  dazhiKpi, luqunKpi, sourceBreakdown, totalCases, totalHours,
  completedCases, uncompletedCases, completionRate,
}: {
  dazhiKpi: any; luqunKpi: any; sourceBreakdown: any[]
  totalCases: number; totalHours: number; completedCases: number
  uncompletedCases: number; completionRate: number
}) {
  const dSrc = sourceBreakdown.find((s: any) => s.source === 'dazhi') ?? { hours: 0, top_category: '-' }
  const lSrc = sourceBreakdown.find((s: any) => s.source === 'luqun') ?? { hours: 0, top_category: '-' }

  const rows: UnitCompRow[] = [
    {
      key: 'hotel', unit: '飯店（飯店工務）',
      cases:       dazhiKpi?.total      ?? 0,
      hours:       dSrc.hours,
      completed:   dazhiKpi?.completed  ?? 0,
      uncompleted: dazhiKpi?.uncompleted ?? 0,
      rate:        (dazhiKpi?.total ?? 0) > 0
                     ? Math.round((dazhiKpi.completed / dazhiKpi.total) * 100) : 0,
      topCat:      dSrc.top_category ?? '-',
    },
    {
      key: 'mall', unit: '商場（商場工務）',
      cases:       luqunKpi?.total      ?? 0,
      hours:       lSrc.hours,
      completed:   luqunKpi?.completed  ?? 0,
      uncompleted: luqunKpi?.uncompleted ?? 0,
      rate:        (luqunKpi?.total ?? 0) > 0
                     ? Math.round((luqunKpi.completed / luqunKpi.total) * 100) : 0,
      topCat:      lSrc.top_category ?? '-',
    },
    {
      key: 'total', unit: '合計',
      cases: totalCases, hours: totalHours,
      completed: completedCases, uncompleted: uncompletedCases,
      rate: completionRate, topCat: '-', isTotal: true,
    },
  ]

  const cols = [
    {
      title: '單位', dataIndex: 'unit', key: 'unit', width: 180,
      render: (v: string, r: UnitCompRow) => (
        <span style={{ fontWeight: r.isTotal ? 700 : 400, color: r.isTotal ? '#1B3A5C' : 'inherit' }}>
          {v}
        </span>
      ),
    },
    { title: '案件數', dataIndex: 'cases', key: 'cases', align: 'right' as const, width: 90 },
    {
      title: '工時（h）', dataIndex: 'hours', key: 'hours', align: 'right' as const, width: 100,
      render: (v: number) => v.toFixed(1),
    },
    {
      title: '完成件數', dataIndex: 'completed', key: 'completed', align: 'right' as const, width: 90,
      render: (v: number) => <span style={{ color: '#52c41a', fontWeight: 600 }}>{v}</span>,
    },
    {
      title: '未完成', dataIndex: 'uncompleted', key: 'uncompleted', align: 'right' as const, width: 80,
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#ff4d4f' : '#aaa', fontWeight: v > 0 ? 600 : 400 }}>{v}</span>
      ),
    },
    {
      title: '完成率', dataIndex: 'rate', key: 'rate', align: 'right' as const, width: 90,
      render: (v: number) => (
        <span style={{ color: v >= 80 ? '#52c41a' : v >= 60 ? '#faad14' : '#ff4d4f', fontWeight: 700 }}>
          {v}%
        </span>
      ),
    },
    {
      title: '主要工項', dataIndex: 'topCat', key: 'topCat', width: 120,
      render: (v: string) => (v && v !== '-')
        ? <Tag color="blue" style={{ fontSize: 12 }}>{v}</Tag>
        : <span style={{ color: '#bbb' }}>—</span>,
    },
  ]

  return (
    <Table
      dataSource={rows}
      columns={cols}
      pagination={false}
      size="small"
      rowClassName={(r: UnitCompRow) => r.isTotal ? 'exec-total-row' : ''}
      style={{ fontSize: 13 }}
    />
  )
}


// ══════════════════════════════════════════════════════════════════════════════
// 工項類別 × 單位矩陣
// ══════════════════════════════════════════════════════════════════════════════
function CategorySourceMatrix({ data }: { data: CategorySourceMatrixItem[] }) {
  const CATEGORY_COLOR: Record<string, string> = {
    '現場報修': '#1890ff', '上級交辦': '#722ed1', '緊急事件': '#ff4d4f',
    '例行維護': '#52c41a', '每日巡檢': '#faad14',
  }

  // summary row
  const total = data.reduce(
    (acc, r) => ({
      dazhi_cases: acc.dazhi_cases + r.dazhi_cases,
      luqun_cases: acc.luqun_cases + r.luqun_cases,
      total_cases: acc.total_cases + r.total_cases,
      dazhi_hours: +(acc.dazhi_hours + r.dazhi_hours).toFixed(1),
      luqun_hours: +(acc.luqun_hours + r.luqun_hours).toFixed(1),
      total_hours: +(acc.total_hours + r.total_hours).toFixed(1),
    }),
    { dazhi_cases: 0, luqun_cases: 0, total_cases: 0,
      dazhi_hours: 0, luqun_hours: 0, total_hours: 0 }
  )

  type MatrixRow = CategorySourceMatrixItem & { isTotal?: boolean }
  const tableData: MatrixRow[] = [
    ...data,
    { category: '合計', ...total, pct: 100, isTotal: true },
  ]

  const cols = [
    {
      title: '工項類別', dataIndex: 'category', key: 'category', width: 110,
      render: (v: string, r: MatrixRow) => r.isTotal
        ? <span style={{ fontWeight: 700, color: '#1B3A5C' }}>{v}</span>
        : <Tag color={CATEGORY_COLOR[v] ?? 'default'} style={{ fontSize: 12, margin: 0 }}>{v}</Tag>,
    },
    {
      title: '飯店件數', dataIndex: 'dazhi_cases', key: 'dazhi_cases',
      align: 'right' as const, width: 90,
      render: (v: number, r: MatrixRow) => (
        <span style={{ fontWeight: r.isTotal ? 700 : 400 }}>{v}</span>
      ),
    },
    {
      title: '商場件數', dataIndex: 'luqun_cases', key: 'luqun_cases',
      align: 'right' as const, width: 90,
      render: (v: number, r: MatrixRow) => (
        <span style={{ fontWeight: r.isTotal ? 700 : 400 }}>{v}</span>
      ),
    },
    {
      title: '合計件數', dataIndex: 'total_cases', key: 'total_cases',
      align: 'right' as const, width: 90,
      render: (v: number, r: MatrixRow) => (
        <span style={{ fontWeight: 700, color: r.isTotal ? '#1B3A5C' : '#333' }}>{v}</span>
      ),
    },
    {
      title: '件占比', dataIndex: 'pct', key: 'pct',
      align: 'right' as const, width: 80,
      render: (v: number, r: MatrixRow) => r.isTotal
        ? <span style={{ color: '#aaa' }}>100%</span>
        : <span style={{ color: '#1890ff', fontWeight: 600 }}>{v}%</span>,
    },
    {
      title: '飯店工時', dataIndex: 'dazhi_hours', key: 'dazhi_hours',
      align: 'right' as const, width: 90,
      render: (v: number, r: MatrixRow) => (
        <span style={{ fontWeight: r.isTotal ? 700 : 400 }}>{v.toFixed(1)}</span>
      ),
    },
    {
      title: '商場工時', dataIndex: 'luqun_hours', key: 'luqun_hours',
      align: 'right' as const, width: 90,
      render: (v: number, r: MatrixRow) => (
        <span style={{ fontWeight: r.isTotal ? 700 : 400 }}>{v.toFixed(1)}</span>
      ),
    },
    {
      title: '總工時', dataIndex: 'total_hours', key: 'total_hours',
      align: 'right' as const, width: 90,
      render: (v: number, r: MatrixRow) => (
        <span style={{ fontWeight: 700, color: r.isTotal ? '#1B3A5C' : '#333' }}>{v.toFixed(1)}</span>
      ),
    },
  ]

  return (
    <Table
      dataSource={tableData}
      columns={cols}
      rowKey="category"
      pagination={false}
      size="small"
      rowClassName={(r: MatrixRow) => r.isTotal ? 'exec-total-row' : ''}
      style={{ fontSize: 13 }}
    />
  )
}


// ══════════════════════════════════════════════════════════════════════════════
// 異常提醒區
// ══════════════════════════════════════════════════════════════════════════════
interface AlertItem {
  level: 'error' | 'warning' | 'info'
  icon:  string
  title: string
  desc:  string
}

function AlertPanel({
  execStats, totalCases, completedCases, uncompletedCases, completionRate,
}: {
  execStats: CategoryStats | null
  totalCases: number; completedCases: number; uncompletedCases: number; completionRate: number
}) {
  const alerts: AlertItem[] = []

  if (!execStats) return null

  // ① 未完成件數 > 0
  if (uncompletedCases > 0) {
    alerts.push({
      level: 'error', icon: '🔴',
      title: `未完成件數警示：${uncompletedCases} 件尚未結案`,
      desc:  `本月共 ${totalCases} 件，完成 ${completedCases} 件，剩餘 ${uncompletedCases} 件需追蹤。`,
    })
  }

  // ② 完成率偏低（< 60%）
  if (completionRate < 60 && totalCases > 0) {
    alerts.push({
      level: 'error', icon: '🔴',
      title: `完成率偏低：${completionRate}%（閾值 60%）`,
      desc:  '建議檢視未完成案件原因，確認是否需要調配人力。',
    })
  } else if (completionRate < 80 && totalCases > 0) {
    alerts.push({
      level: 'warning', icon: '🟠',
      title: `完成率注意：${completionRate}%（建議 > 80%）`,
      desc:  '完成率低於建議水準，請持續追蹤結案進度。',
    })
  }

  // ③ 工項類別集中（占比 > 60%）
  const catBreakdown = execStats.category_breakdown ?? []
  const dominantCat = catBreakdown.find((c: any) => c.pct > 60)
  if (dominantCat) {
    alerts.push({
      level: 'warning', icon: '🟡',
      title: `工項類別集中：${dominantCat.name} 占 ${dominantCat.pct}%`,
      desc:  `單一類別超過 60%，工務資源高度集中，建議評估類別分配是否合理。`,
    })
  }

  // ④ 人員超載（工時 > 80h）
  const ranking = execStats.person_ranking ?? []
  const overloaded = ranking.filter((p: any) => p.hours > 80)
  if (overloaded.length > 0) {
    const names = overloaded.map((p: any) => `${p.person}（${p.hours}h）`).join('、')
    alerts.push({
      level: 'warning', icon: '🟠',
      title: `人員超載警示：${overloaded.length} 人工時超過 80h`,
      desc:  `超載人員：${names}。建議重新分配任務以降低疲勞風險。`,
    })
  }

  // ⑤ 單日暴增（某日工時 > 月均 × 2）
  const dh = execStats.daily_hours
  if (dh?.days?.length && dh.rows?.length) {
    // 計算每日合計工時
    const dailyTotals = dh.days.map((_: number, i: number) =>
      dh.rows.reduce((sum: number, row: any) => sum + (row.hours[i] ?? 0), 0)
    )
    const activeDays = dailyTotals.filter((h: number) => h > 0)
    const avgDaily = activeDays.length > 0
      ? activeDays.reduce((a: number, b: number) => a + b, 0) / activeDays.length
      : 0
    const spikeThreshold = avgDaily * 2
    const spikeDays = dh.days
      .map((d: number, i: number) => ({ day: d, hours: dailyTotals[i] }))
      .filter((d: any) => d.hours > spikeThreshold && spikeThreshold > 0)
    if (spikeDays.length > 0) {
      const dayList = spikeDays.map((d: any) => `${d.day} 日（${d.hours.toFixed(1)}h）`).join('、')
      alerts.push({
        level: 'info', icon: '🔵',
        title: `單日工時暴增：${spikeDays.length} 天超過月均 2 倍（月均 ${avgDaily.toFixed(1)}h）`,
        desc:  `暴增日期：${dayList}。`,
      })
    }
  }

  if (alerts.length === 0) {
    return (
      <div style={{ padding: '12px 16px', color: '#52c41a', fontWeight: 600, fontSize: 14 }}>
        ✅ 本月無異常警示，工務運作正常。
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '4px 0' }}>
      {alerts.map((a, i) => (
        <div
          key={i}
          style={{
            padding: '10px 16px',
            borderRadius: 6,
            background: a.level === 'error' ? '#fff1f0' : a.level === 'warning' ? '#fff7e6' : '#e6f4ff',
            border: `1px solid ${a.level === 'error' ? '#ffccc7' : a.level === 'warning' ? '#ffd591' : '#91caff'}`,
          }}
        >
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 2 }}>
            {a.icon} {a.title}
          </div>
          <div style={{ fontSize: 13, color: '#666' }}>{a.desc}</div>
        </div>
      ))}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// 主元件
// ══════════════════════════════════════════════════════════════════════════════
export default function ExecWorkDashboardPage() {
  const navigate = useNavigate()

  const [luqunData,   setLuqunData]   = useState<RepairDashboardData | null>(null)
  const [dazhiData,   setDazhiData]   = useState<RepairDashboardData | null>(null)
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
  const ALL_ANALYSIS_KEYS = ['exec-daily', 'exec-monthly', 'exec-burden', 'unit-comparison', 'category-matrix', 'alerts']
  const [dailyKeys,    setDailyKeys]    = useState<string[]>([])
  const [analysisKeys, setAnalysisKeys] = useState<string[]>(['alerts'])
  const allExpanded = dailyKeys.length + analysisKeys.length ===
    ALL_DAILY_KEYS.length + ALL_ANALYSIS_KEYS.length
  const toggleAll = () => {
    if (allExpanded) { setDailyKeys([]); setAnalysisKeys([]) }
    else             { setDailyKeys(ALL_DAILY_KEYS); setAnalysisKeys(ALL_ANALYSIS_KEYS) }
  }

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [luqun, dazhi, hotelMon, mallMon, hotelDay, mallDay, execSt] =
        await Promise.allSettled([
          fetchLuqunDashboard(selectedYear, selectedMonth),
          fetchDazhiDashboard(selectedYear, selectedMonth),
          fetchHotelMonthlyHours(selectedYear),
          fetchMallMonthlyHours(selectedYear),
          fetchHotelDailyHours(selectedYear, selectedMonth),
          fetchMallDailyHours(selectedYear, selectedMonth),
          fetchStats({ year: selectedYear, month: selectedMonth, sources: 'all', category: 'all', person: 'all' }),
        ])
      if (luqun.status    === 'fulfilled') setLuqunData(luqun.value)
      if (dazhi.status    === 'fulfilled') setDazhiData(dazhi.value as unknown as RepairDashboardData)
      if (hotelMon.status === 'fulfilled') setHotelMonthlyData(hotelMon.value)
      if (mallMon.status  === 'fulfilled') setMallMonthlyData(mallMon.value)
      if (hotelDay.status === 'fulfilled') setHotelDailyData(hotelDay.value)
      if (mallDay.status  === 'fulfilled') setMallDailyData(mallDay.value)
      if (execSt.status   === 'fulfilled') setExecStats(execSt.value)
      setRefreshed(new Date())
    } finally {
      setLoading(false)
    }
  }, [selectedYear, selectedMonth])

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
        <Spin size="large" tip="載入工務決策駕駛艙…" />
      </div>
    )
  }

  // ── 集團工務 KPI 衍生值（Phase 3）─────────────────────────────────────────
  const dKpi = dazhiData?.kpi
  const lKpi = luqunData?.kpi
  const totalCases      = (dKpi?.total      ?? 0) + (lKpi?.total      ?? 0)
  const completedCases  = (dKpi?.completed  ?? 0) + (lKpi?.completed  ?? 0)
  const uncompletedCases= (dKpi?.uncompleted?? 0) + (lKpi?.uncompleted?? 0)
  const totalHours      = execStats?.kpi?.total_hours ?? 0
  const completionRate  = totalCases > 0 ? Math.round(completedCases  / totalCases * 100) : 0
  const avgHrPerCase    = totalCases > 0 ? Math.round(totalHours      / totalCases * 10) / 10 : 0
  const hotelCasePct    = totalCases > 0 ? Math.round((dKpi?.total ?? 0) / totalCases * 100) : 0
  const mallCasePct     = totalCases > 0 ? Math.round((lKpi?.total ?? 0) / totalCases * 100) : 0

  return (
    <div>
      {/* ── Breadcrumb（PROTECTED：每頁必有，不可移除）──────────────── */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <><HomeOutlined /> 首頁</> },
          { title: '集團決策 Dashboard' },
        ]}
      />

      {/* ── 頁頭 ─────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'flex-start',
        justifyContent: 'space-between', marginBottom: 16,
      }}>
        <div>
          <Title level={4} style={{ margin: 0, color: C.primary }}>集團決策 Dashboard</Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {dayjs().format('YYYY 年 MM 月 DD 日')} 工務決策視角
          </Text>
        </div>
        <Space direction="vertical" align="end" size={2}>
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
          ROW KPI — 集團工務 KPI Card（8 指標）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {/* 本月總案件數 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.primary}`, textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>本月總案件</Text>}
              value={totalCases}
              suffix="件"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: C.primary }}
            />
          </Card>
        </Col>
        {/* 本月總工時 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.accent}`, textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>本月總工時</Text>}
              value={totalHours}
              precision={1}
              suffix="HR"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: C.accent }}
            />
          </Card>
        </Col>
        {/* 完成件數 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.success}`, textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>完成件數</Text>}
              value={completedCases}
              suffix="件"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: C.success }}
            />
          </Card>
        </Col>
        {/* 未完成件數 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${uncompletedCases > 0 ? C.danger : C.success}`, textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>未完成件數</Text>}
              value={uncompletedCases}
              suffix="件"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: uncompletedCases > 0 ? C.danger : C.success }}
            />
          </Card>
        </Col>
        {/* 完成率 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${rateColor(completionRate)}`, textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>完成率</Text>}
              value={completionRate}
              suffix="%"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: rateColor(completionRate) }}
            />
          </Card>
        </Col>
        {/* 平均每件工時 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.warning}`, textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>均工時/件</Text>}
              value={avgHrPerCase}
              precision={1}
              suffix="HR"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: C.warning }}
            />
          </Card>
        </Col>
        {/* 飯店案件占比 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: '3px solid #0d6b4e', textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>飯店案件占比</Text>}
              value={hotelCasePct}
              suffix="%"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: '#0d6b4e' }}
            />
          </Card>
        </Col>
        {/* 商場案件占比 */}
        <Col xs={12} sm={8} md={6} lg={3}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.primary}`, textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>商場案件占比</Text>}
              value={mallCasePct}
              suffix="%"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: C.primary }}
            />
          </Card>
        </Col>
      </Row>

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


      {/* ══════════════════════════════════════════════════════════════
          ROW 0.38 — 飯店 vs 商場比較表
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Collapse
            activeKey={analysisKeys.includes('unit-comparison') ? ['unit-comparison'] : []}
            onChange={keys => {
              const rest = analysisKeys.filter(k => k !== 'unit-comparison')
              setAnalysisKeys((keys as string[]).includes('unit-comparison')
                ? [...rest, 'unit-comparison']
                : rest)
            }}
            style={{ background: '#fff' }}
            items={[
              {
                key: 'unit-comparison',
                label: (
                  <Space>
                    <span>🏢</span>
                    <Typography.Text strong style={{ fontSize: 16 }}>
                      飯店 vs 商場比較表 — {selectedYear} 年 {selectedMonth} 月
                    </Typography.Text>
                  </Space>
                ),
                children: execStats
                  ? (
                    <UnitComparisonTable
                      dazhiKpi={dazhiData?.kpi}
                      luqunKpi={luqunData?.kpi}
                      sourceBreakdown={execStats.source_breakdown ?? []}
                      totalCases={totalCases}
                      totalHours={totalHours}
                      completedCases={completedCases}
                      uncompletedCases={uncompletedCases}
                      completionRate={completionRate}
                    />
                  )
                  : <div style={{ color: '#aaa', padding: '12px 0', textAlign: 'center' }}>資料載入中…</div>,
              },
            ]}
          />
        </Col>
      </Row>


      {/* ══════════════════════════════════════════════════════════════
          ROW 0.39 — 工項類別 × 單位矩陣
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Collapse
            activeKey={analysisKeys.includes('category-matrix') ? ['category-matrix'] : []}
            onChange={keys => {
              const rest = analysisKeys.filter(k => k !== 'category-matrix')
              setAnalysisKeys((keys as string[]).includes('category-matrix')
                ? [...rest, 'category-matrix']
                : rest)
            }}
            style={{ background: '#fff' }}
            items={[
              {
                key: 'category-matrix',
                label: (
                  <Space>
                    <span>📊</span>
                    <Typography.Text strong style={{ fontSize: 16 }}>
                      工項類別 × 單位矩陣 — {selectedYear} 年 {selectedMonth} 月
                    </Typography.Text>
                  </Space>
                ),
                children: execStats?.category_source_matrix?.length
                  ? <CategorySourceMatrix data={execStats.category_source_matrix} />
                  : <div style={{ color: '#aaa', padding: '12px 0', textAlign: 'center' }}>資料載入中…</div>,
              },
            ]}
          />
        </Col>
      </Row>


      {/* ══════════════════════════════════════════════════════════════
          ROW 0.40 — 異常提醒區
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Collapse
            activeKey={analysisKeys.includes('alerts') ? ['alerts'] : []}
            onChange={keys => {
              const rest = analysisKeys.filter(k => k !== 'alerts')
              setAnalysisKeys((keys as string[]).includes('alerts')
                ? [...rest, 'alerts']
                : rest)
            }}
            style={{ background: '#fff' }}
            items={[
              {
                key: 'alerts',
                label: (
                  <Space>
                    <span>⚠️</span>
                    <Typography.Text strong style={{ fontSize: 16 }}>
                      異常提醒 — {selectedYear} 年 {selectedMonth} 月
                    </Typography.Text>
                  </Space>
                ),
                children: (
                  <AlertPanel
                    execStats={execStats}
                    totalCases={totalCases}
                    completedCases={completedCases}
                    uncompletedCases={uncompletedCases}
                    completionRate={completionRate}
                  />
                ),
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
