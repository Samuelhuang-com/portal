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
import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Typography, Tag, Table, Collapse, Tabs, Segmented, DatePicker,
  Spin, Tooltip, Progress, Space, Button, Breadcrumb, Divider, Badge, Select, Drawer, Descriptions, Image,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, CheckCircleOutlined,
  ClockCircleOutlined, SyncOutlined, ExclamationCircleOutlined,
  RightOutlined, SafetyOutlined, ShopOutlined,
  AlertOutlined, BuildOutlined, ToolOutlined,
  DollarOutlined, RiseOutlined, WarningOutlined, BankOutlined,
  ArrowUpOutlined, ArrowDownOutlined, InfoCircleOutlined,
  FileExcelOutlined, UserOutlined, LinkOutlined,
  MinusCircleOutlined, FileUnknownOutlined, UserDeleteOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-tw'

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartTooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'

import { fetchDashboard as fetchLuqunDashboard, fetchRepairStats as fetchLuqunRepairStats } from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhiDashboard, fetchRepairStats as fetchDazhiRepairStats } from '@/api/dazhiRepair'
import type { DashboardData as RepairDashboardData, TypeDistItem } from '@/types/luqunRepair'
import type { RepairStatsData as DazhiRepairStatsData } from '@/types/dazhiRepair'
import type { RepairStatsData as LuqunRepairStatsData } from '@/types/luqunRepair'
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
import {
  fetchWorkJournalDaily, fetchWorkJournalRange, fetchJournalImages,
  getJournalExcelUrl,
  type WorkJournalDaily, type WorkJournalRange, type JournalRow, type CaseImageItem,
  CATEGORY_COLOR,
} from '@/api/workJournal'
import { fetchShiftsRange, type ShiftInfo, type ShiftsRangeData } from '@/api/schedule'
import { downloadFile } from '@/api/downloadFile'
import {
  fetchOtherTaskStats,
  type OtherTaskTypeStat,
} from '@/api/otherTasks'

import type { Dayjs } from 'dayjs'
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

function ColTip({ label, tip }: { label: string; tip: string }) {
  return (
    <Tooltip title={tip}>
      <span style={{ cursor: 'help', whiteSpace: 'nowrap' }}>
        {label} <InfoCircleOutlined style={{ fontSize: 11, color: '#aaa' }} />
      </span>
    </Tooltip>
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
          {
            title: <ColTip label="工時(HR)" tip="SUM(work_hours)：依人員加總，涵蓋飯店工務（大直）、商場工務（陸群）、IHG客房保養三個來源" />,
            dataIndex: 'hours', width: 90, align: 'right' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => a.hours - b.hours,
            render: (v: number) => <Typography.Text strong style={{ fontSize: 14 }}>{v.toFixed(1)}</Typography.Text>,
          },
          {
            title: <ColTip label="件數" tip="COUNT(work_hours > 0 的記錄數)：該人員負責的工時記錄筆數（含重複案件），用於計算均工時/件的分母" />,
            dataIndex: 'cases', width: 62, align: 'right' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => (a.cases ?? 0) - (b.cases ?? 0),
            render: (v: number) => <Typography.Text style={{ fontSize: 14 }}>{v ?? 0}</Typography.Text>,
          },
          {
            title: <ColTip label="均工時/件" tip="工時(HR) ÷ 件數，四捨五入至小數 1 位。反映每筆工作記錄平均耗時" />,
            dataIndex: 'avg_hr', width: 90, align: 'right' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => (a.avg_hr ?? 0) - (b.avg_hr ?? 0),
            render: (v: number) => <Typography.Text style={{ fontSize: 14 }}>{(v ?? 0).toFixed(1)}</Typography.Text>,
          },
          {
            title: <ColTip label="主要類別" tip="該人員在現場報修／上級交辦／緊急事件／例行維護／每日巡檢五類中，工時最高的類別" />,
            dataIndex: 'top_category', width: 90,
            render: (v: string) => <Tag color={CATEGORY_TAG_COLORS[v] ?? 'default'} style={{ fontSize: 13 }}>{v}</Tag>,
          },
          {
            title: <ColTip label="判斷" tip="依均工時/件判斷：≥ 3.0 HR → 需關注（紅）；2.5–3.0 HR → 工時偏高（橙）；< 2.5 HR → 正常（綠）" />,
            key: 'burden', width: 96, align: 'center' as const,
            sorter: (a: ExecRankRow, b: ExecRankRow) => (a.avg_hr ?? 0) - (b.avg_hr ?? 0),
            render: (_: unknown, r: ExecRankRow) => {
              const { text, color } = burdenLabel(r.avg_hr ?? 0)
              return <Tag color={color} style={{ fontSize: 13, fontWeight: 600 }}>{text}</Tag>
            },
          },
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

function HotelDailyTable({
  data,
  supervisorTotal = 0,
  emergencyTotal  = 0,
}: {
  data: HotelDailyHoursData
  supervisorTotal?: number
  emergencyTotal?:  number
}) {
  const navigate = useNavigate()
  const n = data.days.length
  const zeroes = (): number[] => Array(n).fill(0)
  const addH = (a?: number[], b?: number[]): number[] =>
    zeroes().map((_, i) => (a?.[i] ?? 0) + (b?.[i] ?? 0))
  const find = (name: string) => data.rows.find(r => r.category === name)
  const CATS = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢']
  const catCases: Record<string, number[]> = {
    現場報修: find('飯店工務部')?.cases ?? zeroes(),
    上級交辦: zeroes(),   // daily breakdown not available; monthly total shown in TOTAL column
    緊急事件: zeroes(),
    例行維護: addH(addH(find('客房保養管理')?.cases, find('飯店週期保養')?.cases), find('IHG客房保養')?.cases),
    每日巡檢: find('飯店每日巡檢')?.cases ?? zeroes(),
  }
  // Override monthly totals for 上級交辦 / 緊急事件
  const catMonthlyOverrides: Record<string, number> = {
    上級交辦: supervisorTotal,
    緊急事件: emergencyTotal,
  }
  // Effective totals per category (use monthly override for 上級交辦/緊急事件)
  const catEffectiveTotal = (cat: string) =>
    catMonthlyOverrides[cat] !== undefined ? catMonthlyOverrides[cat] : catCases[cat].reduce((a, b) => a + b, 0)
  const grandTotal = CATS.reduce((s, c) => s + catEffectiveTotal(c), 0)
  type DRow = { key: string; category: string; cases: number[]; total: number; pct: number }
  const rows: DRow[] = CATS.map(cat => {
    const cases = catCases[cat]
    const total = catEffectiveTotal(cat)
    return { key: cat, category: cat, cases, total, pct: grandTotal > 0 ? Math.round(total / grandTotal * 1000) / 10 : 0 }
  })
  const totalCases = data.days.map((_, i) => CATS.reduce((s, c) => s + (catCases[c][i] ?? 0), 0))
  const grandEffTotal = CATS.reduce((s, c) => s + catEffectiveTotal(c), 0)
  rows.push({ key: 'TOTAL', category: 'TOTAL', cases: totalCases, total: grandEffTotal, pct: 100 })

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
      title: '案件數', key: 'total', width: 80, align: 'right' as const,
      render: (_: unknown, row: DRow) => {
        // 上級交辦/緊急事件 only have monthly totals (no daily breakdown)
        if (catMonthlyOverrides[row.category] !== undefined) {
          return (
            <span>
              <Text strong style={{ fontSize: 15, color: '#722ed1' }}>{row.total}</Text>
              <Text style={{ fontSize: 10, color: '#aaa', marginLeft: 2 }}>月計</Text>
            </span>
          )
        }
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
              {/* 已結案 */}
              <Col span={3}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: C.success, lineHeight: 1.2 }}>
                    {kpi.completed}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>已結案</div>
                </div>
              </Col>
              {/* 待辦驗數 */}
              <Col span={3}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{
                    fontSize: 22, fontWeight: 700, lineHeight: 1.2,
                    color: (kpi.pending_verify ?? 0) > 0 ? C.warning : C.gray,
                  }}>
                    {kpi.pending_verify ?? 0}
                  </div>
                  <div style={{ fontSize: 11, color: C.gray, marginTop: 2 }}>待辦驗數</div>
                </div>
              </Col>
              {/* 未結案 */}
              <Col span={3}>
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
              <Col span={3}>
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
                    {kpi.total_work_hours > 0 ? kpi.total_work_hours.toFixed(2) : '—'}
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

// ── 工作日誌 TAB 元件（自給式：自行管理模式/日期/資料）────────────────────────
type JournalCategory = '現場報修' | '上級交辦' | '緊急事件' | '例行維護' | '每日巡檢'
const CAT_COLS: JournalCategory[] = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢']

type JournalMode = 'single' | 'range' | 'month' | 'person'

// 班別 Tag 渲染輔助
// shiftMap = undefined → 班表資料尚未載入，不顯示任何標記
// shiftMap = {}        → 已載入但該日無班表資料，仍不顯示（避免誤報）
// shiftMap 有資料      → 依 is_working 判斷顯示彩色代碼或紅色 ?
function ShiftTag({
  person,
  shiftMap,
}: {
  person:   string
  shiftMap: Record<string, ShiftInfo> | undefined
}) {
  // 警示 icon 共用樣式
  const warnTagStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: 16, padding: '0 4px',
    lineHeight: '20px', marginRight: 4, cursor: 'default',
  }

  // 「未指定」人員 → UserDeleteOutlined（身分不明）
  if (person === '未指定') return (
    <Tooltip title="人員未指定" placement="top">
      <Tag color="error" style={warnTagStyle}>
        <UserDeleteOutlined />
      </Tag>
    </Tooltip>
  )

  // 班表資料未載入或整日無班表 → 不顯示
  if (!shiftMap || Object.keys(shiftMap).length === 0) return null

  const info = shiftMap[person]

  // 有班表記錄 + 非上班班別 → MinusCircleOutlined（明確排休）
  if (info && !info.is_working) {
    const tipText = info.shift_name
      ? `${info.shift_code}（${info.shift_name}）— 非上班班別`
      : `${info.shift_code} — 非上班班別`
    return (
      <Tooltip title={tipText} placement="top">
        <Tag color="error" style={warnTagStyle}>
          <MinusCircleOutlined />
        </Tag>
      </Tooltip>
    )
  }

  // 無班表記錄（有工單卻沒排班）→ FileUnknownOutlined（查無記錄）
  if (!info) return (
    <Tooltip title="此日無班表記錄" placement="top">
      <Tag color="warning" style={warnTagStyle}>
        <FileUnknownOutlined />
      </Tag>
    </Tooltip>
  )

  // 正常上班班別 → 彩色班別代碼 + Tooltip 顯示班別名稱
  const tipText = info.shift_name
    ? `${info.shift_code}｜${info.shift_name}`
    : info.shift_code
  return (
    <Tooltip title={tipText} placement="top">
      <Tag
        style={{
          backgroundColor: info.shift_color,
          color: '#fff',
          fontWeight: 700,
          fontSize: 15,
          minWidth: 26,
          textAlign: 'center',
          padding: '0 5px',
          lineHeight: '20px',
          marginRight: 4,
          border: 'none',
          cursor: 'default',
        }}
      >
        {info.shift_code}
      </Tag>
    </Tooltip>
  )
}

// 單一日期的人員分組 Collapse（單日 or 區間內每天複用）
function DayPersonCollapse({
  persons,
  collapsed,
  shiftMap,
}: {
  persons:   WorkJournalDaily['persons']
  collapsed?: boolean
  shiftMap?:  Record<string, ShiftInfo>
}) {
  const [selectedRow, setSelectedRow] = useState<JournalRow | null>(null)
  const [drawerImages, setDrawerImages] = useState<CaseImageItem[]>([])
  const [imgLoading,   setImgLoading]   = useState(false)
  const [personActiveKeys, setPersonActiveKeys] = useState<string[]>(() =>
    persons.map((_, i) => `person-${i}`)
  )
  useEffect(() => {
    if (collapsed === undefined) return
    setPersonActiveKeys(collapsed ? [] : persons.map((_, i) => `person-${i}`))
  }, [collapsed]) // eslint-disable-line react-hooks/exhaustive-deps

  const journalColumns = [
    {
      title: '項次', dataIndex: 'seq', key: 'seq', width: 48, align: 'center' as const,
      render: (v: number) => <Text style={{ fontSize: 14, color: '#888' }}>{v}</Text>,
    },
    ...CAT_COLS.map(cat => ({
      title: <span style={{ fontSize: 13, color: CATEGORY_COLOR[cat as JournalCategory], whiteSpace: 'nowrap' as const }}>{cat}</span>,
      key: cat, width: 56, align: 'center' as const,
      render: (_: unknown, row: JournalRow) =>
        row.category === cat
          ? <span style={{ color: CATEGORY_COLOR[cat as JournalCategory], fontSize: 18, fontWeight: 700 }}>✓</span>
          : null,
    })),
    {
      title: '工作事項', dataIndex: 'task', key: 'task', width: 200,
      render: (v: string, row: JournalRow) => {
        const isHotel = _isHotelRow(row)
        return (
          <Text style={{ fontSize: 14 }}>
            <span style={{
              display: 'inline-block', marginRight: 4,
              fontSize: 11, fontWeight: 700, lineHeight: '16px',
              padding: '0 4px', borderRadius: 3,
              background: isHotel ? '#e8f4fd' : '#e8f5e9',
              color:      isHotel ? '#1565C0' : '#2E7D32',
            }}>{isHotel ? '飯' : '商'}</span>
            {v}
          </Text>
        )
      },
    },
    {
      title: '預估耗時(min)', dataIndex: 'est_min', key: 'est_min', width: 88, align: 'center' as const,
      render: (v: number | null) => v != null
        ? <Text style={{ fontSize: 14 }}>{v}</Text>
        : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '起', dataIndex: 'start_time', key: 'start', width: 52, align: 'center' as const,
      render: (v: string) => v ? <Text style={{ fontSize: 14 }}>{v}</Text> : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '迄', dataIndex: 'end_time', key: 'end', width: 52, align: 'center' as const,
      render: (v: string) => v ? <Text style={{ fontSize: 14 }}>{v}</Text> : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '工時(min)', dataIndex: 'work_min', key: 'wh', width: 72, align: 'center' as const,
      render: (v: number | null) => v != null
        ? <Text strong style={{ fontSize: 14, color: '#1B3A5C' }}>{v}</Text>
        : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '備註', dataIndex: 'remark', key: 'remark', width: 160,
      render: (v: string) => v ? <Text style={{ fontSize: 14, color: '#666' }}>{v}</Text> : null,
    },
    {
      title: '回報事項', dataIndex: 'report', key: 'report', width: 160,
      render: (v: string) => v ? <Text style={{ fontSize: 14, color: '#d46b08' }}>{v}</Text> : null,
    },
  ]

  if (!persons.length) return (
    <div style={{ textAlign: 'center', color: '#aaa', padding: '12px 0' }}>此日無工作記錄</div>
  )

  const STATUS_COLOR: Record<string, string> = {
    '已完成': '#52c41a', '已修復': '#52c41a', '已結案': '#52c41a', '已調整': '#52c41a', '已固定': '#52c41a',
    '待辦驗': '#faad14', '未完成': '#faad14', '進行中': '#1677ff',
  }

  const items = persons.map((p, idx) => {
    const totalWH = p.rows.reduce((acc, r) => acc + (r.work_min ?? 0), 0)
    const sources = [...new Set(p.rows.map(r => r.source_label))].join('、')
    return {
      key: `person-${idx}`,
      label: (
        <Space align="center">
          <ShiftTag person={p.person} shiftMap={shiftMap} />
          <Text strong style={{ fontSize: 16, color: p.person === '未指定' ? '#aaa' : '#1B3A5C' }}>
            {p.person}
          </Text>
          <Tag color="blue" style={{ fontSize: 13 }}>{p.rows.length} 項</Tag>
          {totalWH > 0 && <Tag color="geekblue" style={{ fontSize: 13 }}>{totalWH} min</Tag>}
          {sources && <Text type="secondary" style={{ fontSize: 13 }}>{sources}</Text>}
        </Space>
      ),
      children: (
        <Table
          size="small"
          dataSource={p.rows.map((r, i) => ({ ...r, key: i }))}
          columns={journalColumns}
          pagination={false}
          scroll={{ x: 'max-content' }}
          style={{ marginTop: 4 }}
          onRow={row => ({
            onClick: () => {
              const r = row as JournalRow
              setSelectedRow(r)
              setDrawerImages([])
              if (r.ragic_id && (r.source === 'dazhi' || r.source === 'luqun' || r.source === 'other_tasks')) {
                setImgLoading(true)
                fetchJournalImages(r.source, r.ragic_id)
                  .then(imgs => setDrawerImages(imgs))
                  .catch(() => setDrawerImages([]))
                  .finally(() => setImgLoading(false))
              }
            },
            style: { cursor: 'pointer' },
          })}
        />
      ),
    }
  })

  return (
    <>
      <Collapse
        activeKey={personActiveKeys}
        onChange={keys => setPersonActiveKeys(keys as string[])}
        items={items}
        style={{ background: '#fff' }}
      />
      <Drawer
        open={!!selectedRow}
        onClose={() => { setSelectedRow(null); setDrawerImages([]) }}
        title={
          selectedRow && (() => {
            // 取最有意義的識別碼：報修編號 > 日誌編號 > 房號 > ragic_id
            const d = selectedRow.detail ?? {}
            const identifier = d['報修編號'] || d['日誌編號'] || d['房號'] || selectedRow.ragic_id || ''
            return (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <Tag color={CATEGORY_COLOR[selectedRow.category as keyof typeof CATEGORY_COLOR]}
                     style={{ margin: 0 }}>
                  {selectedRow.category}
                </Tag>
                <span style={{ fontSize: 16, color: '#1B3A5C', fontWeight: 600 }}>
                  {selectedRow.source_label}
                  {identifier && <>：<span style={{ fontWeight: 400 }}>{identifier}</span></>}
                </span>
                {selectedRow.ragic_url && (
                  <a
                    href={selectedRow.ragic_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 14, color: '#4BA8E8', display: 'flex', alignItems: 'center', gap: 3, fontWeight: 400 }}
                  >
                    <LinkOutlined /> 在 Ragic 查看
                  </a>
                )}
              </div>
            )
          })()
        }
        width={480}
        styles={{ body: { padding: '16px 20px' } }}
      >
        {selectedRow && (
          <>
            <Typography.Title level={5} style={{ margin: '0 0 12px', color: '#1B3A5C' }}>
              {selectedRow.task}
            </Typography.Title>
            <Descriptions
              bordered
              size="small"
              column={1}
              labelStyle={{ width: 100, background: '#f5f7fa', fontWeight: 500 }}
              contentStyle={{ background: '#fff' }}
            >
              <Descriptions.Item label="人員">{selectedRow.person}</Descriptions.Item>
              <Descriptions.Item label="來源">{selectedRow.source_label}</Descriptions.Item>
              {selectedRow.source === 'other_tasks' && selectedRow.venue && (
                <Descriptions.Item label="歸屬">
                  <Tag color={selectedRow.venue === '飯店' ? '#1565C0' : '#2E7D32'} style={{ margin: 0 }}>
                    {selectedRow.venue}
                  </Tag>
                </Descriptions.Item>
              )}
              {selectedRow.work_min != null && (
                <Descriptions.Item label="工時(min)">
                  <Text strong style={{ color: '#1B3A5C' }}>{selectedRow.work_min}</Text>
                </Descriptions.Item>
              )}
              {(selectedRow.start_time || selectedRow.detail?.['保養時間起']) && (
                <Descriptions.Item label="保養時間起">
                  {selectedRow.start_time || selectedRow.detail?.['保養時間起']}
                </Descriptions.Item>
              )}
              {(selectedRow.end_time || selectedRow.detail?.['保養時間迄']) && (
                <Descriptions.Item label="保養時間迄">
                  {selectedRow.end_time || selectedRow.detail?.['保養時間迄']}
                </Descriptions.Item>
              )}
              {selectedRow.remark && (
                <Descriptions.Item label="備註">
                  <Text style={{ color: '#666' }}>{selectedRow.remark}</Text>
                </Descriptions.Item>
              )}
              {selectedRow.report && (
                <Descriptions.Item label="回報事項">
                  <Text style={{ color: '#d46b08' }}>{selectedRow.report}</Text>
                </Descriptions.Item>
              )}
            </Descriptions>

            {Object.keys(selectedRow.detail ?? {}).length > 0 && (
              <>
                <Divider style={{ margin: '16px 0 12px' }} />
                <Descriptions
                  bordered
                  size="small"
                  column={1}
                  labelStyle={{ width: 96, background: '#f5f7fa', fontWeight: 500, fontSize: 15 }}
                  contentStyle={{ background: '#fff', fontSize: 15 }}
                >
                  {Object.entries(selectedRow.detail).map(([k, v]) => {
                    const isEmpty = !v
                    // 費用欄：加 $ 符號
                    const isFee   = k.includes('費用')
                    // 狀況欄：彩色 Tag
                    const isStatus = k === '處理狀況' || k === '完成狀況' || k === '狀態'
                    // 類型欄：Tag
                    const isType  = k === '報修類型'
                    // 總費用：粗體
                    const isTotalFee = k === '總費用'
                    // 標題：粗體大字
                    const isTitle = k === '標題'

                    let content: React.ReactNode
                    if (isEmpty) {
                      content = <Text type="secondary">-</Text>
                    } else if (isStatus) {
                      content = <Tag color={STATUS_COLOR[v] ?? 'default'} style={{ margin: 0 }}>{v}</Tag>
                    } else if (isType) {
                      content = <Tag style={{ margin: 0 }}>{v}</Tag>
                    } else if (isTotalFee) {
                      content = <Text strong style={{ fontSize: 16 }}>${v}</Text>
                    } else if (isFee) {
                      content = <Text>${v}</Text>
                    } else if (isTitle) {
                      content = <Text strong style={{ fontSize: 16 }}>{v}</Text>
                    } else {
                      content = <Text>{v}</Text>
                    }
                    return (
                      <Descriptions.Item key={k} label={k}>{content}</Descriptions.Item>
                    )
                  })}
                </Descriptions>
              </>
            )}

            {/* 維修圖片（dazhi / luqun / other_tasks） */}
            {(imgLoading || drawerImages.length > 0) && (
              <>
                <Divider style={{ margin: '16px 0 8px' }} />
                <div style={{ fontWeight: 500, marginBottom: 8, color: '#555', fontSize: 15 }}>
                  維修圖片
                </div>
                {imgLoading
                  ? <div style={{ textAlign: 'center', padding: 16 }}><Spin size="small" /></div>
                  : (
                    <Image.PreviewGroup>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {drawerImages.map((img, i) => (
                          <Image
                            key={i}
                            src={img.url}
                            alt={img.filename || `圖片 ${i + 1}`}
                            width={120}
                            height={90}
                            style={{ objectFit: 'cover', borderRadius: 4, border: '1px solid #e8e8e8', cursor: 'pointer' }}
                            fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                          />
                        ))}
                      </div>
                    </Image.PreviewGroup>
                  )
                }
              </>
            )}

          </>
        )}
      </Drawer>
    </>
  )
}

export interface WJVenueStat { cases: number; hours: number }
export interface WJCatStat {
  cases: number; hours: number
  hotel: WJVenueStat
  mall:  WJVenueStat
}
export type WJStats = Record<string, WJCatStat>

const _HOTEL_SOURCES = new Set<string>(['dazhi', 'hotel_pm', 'ihg', 'hotel_di'])

/** 判斷工作日誌一行是否屬飯店。
 *  other_tasks 以 venue 欄位為準；其餘來源以 source 集合判斷。 */
function _isHotelRow(row: JournalRow): boolean {
  if (row.source === 'other_tasks') return row.venue === '飯店'
  return _HOTEL_SOURCES.has(row.source)
}

function _computeWJStats(days: WorkJournalDaily[]): WJStats {
  const stats: WJStats = {}
  const _empty = (): WJCatStat => ({ cases: 0, hours: 0, hotel: { cases: 0, hours: 0 }, mall: { cases: 0, hours: 0 } })
  days.forEach(d => d.persons.forEach(p => p.rows.forEach(r => {
    if (!stats[r.category]) stats[r.category] = _empty()
    const s = stats[r.category]
    const min = (r.work_min ?? 0) / 60
    s.cases++
    s.hours += min
    const venue = _isHotelRow(r) ? s.hotel : s.mall
    venue.cases++
    venue.hours += min
  })))
  Object.keys(stats).forEach(k => {
    stats[k].hours = Math.round(stats[k].hours * 10) / 10
    stats[k].hotel.hours = Math.round(stats[k].hotel.hours * 10) / 10
    stats[k].mall.hours  = Math.round(stats[k].mall.hours  * 10) / 10
  })
  return stats
}

function WorkJournalTab({ onStatsChange }: { onStatsChange?: (s: WJStats) => void }) {
  const [mode,      setMode]      = useState<JournalMode>('single')
  const [year,      setYear]      = useState<number>(dayjs().year())
  const [month,     setMonth]     = useState<number>(dayjs().month() + 1)
  const [day,       setDay]       = useState<number>(dayjs().date())
  const [rangeDates, setRangeDates] = useState<[Dayjs, Dayjs] | null>(null)
  const [monthDate,  setMonthDate]  = useState<Dayjs | null>(dayjs())
  const [singleData,      setSingleData]      = useState<WorkJournalDaily | null>(null)
  const [rangeData,       setRangeData]       = useState<WorkJournalRange | null>(null)
  const [shiftMapByDate,  setShiftMapByDate]  = useState<ShiftsRangeData>({})
  const [loading,         setLoading]         = useState(false)
  const [personFilter,     setPersonFilter]     = useState<string>('')
  const [personList,       setPersonList]       = useState<string[]>([])
  const [personSubMode,    setPersonSubMode]    = useState<'range'|'month'>('month')
  const [personRangeDates, setPersonRangeDates] = useState<[Dayjs, Dayjs] | null>(null)
  const [personMonthDate,  setPersonMonthDate]  = useState<Dayjs | null>(dayjs())
  const [globalCollapsed,  setGlobalCollapsed]  = useState(false)
  const [dateActiveKeys,   setDateActiveKeys]   = useState<string[]>([])

  const daysInMonth = dayjs(`${year}-${String(month).padStart(2,'0')}-01`).daysInMonth()
  const dayOptions  = Array.from({ length: daysInMonth }, (_, i) => ({ label: `${i + 1} 日`, value: i + 1 }))

  const handleLoad = useCallback(async () => {
    setLoading(true)
    try {
      setGlobalCollapsed(false)

      if (mode === 'single') {
        // 單日：格式化為 YYYY-MM-DD（班表 API 需要此格式）
        const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalDaily(year, month, day),
          fetchShiftsRange(dateStr, dateStr).catch(() => ({} as ShiftsRangeData)),
        ])
        setSingleData(journal)
        setRangeData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys([])

      } else if (mode === 'range' && rangeDates) {
        const from = rangeDates[0].format('YYYY-MM-DD')
        const to   = rangeDates[1].format('YYYY-MM-DD')
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalRange(from, to),
          fetchShiftsRange(from, to).catch(() => ({} as ShiftsRangeData)),
        ])
        setRangeData(journal)
        setSingleData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys(journal.days.map((_, i) => `day-${i}`))
        onStatsChange?.(_computeWJStats(journal.days))

      } else if (mode === 'month' && monthDate) {
        const from = monthDate.startOf('month').format('YYYY-MM-DD')
        const to   = monthDate.endOf('month').format('YYYY-MM-DD')
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalRange(from, to),
          fetchShiftsRange(from, to).catch(() => ({} as ShiftsRangeData)),
        ])
        setRangeData(journal)
        setSingleData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys(journal.days.map((_, i) => `day-${i}`))
        onStatsChange?.(_computeWJStats(journal.days))

      } else if (mode === 'person') {
        let from = '', to = ''
        if (personSubMode === 'range' && personRangeDates) {
          from = personRangeDates[0].format('YYYY-MM-DD')
          to   = personRangeDates[1].format('YYYY-MM-DD')
        } else if (personSubMode === 'month' && personMonthDate) {
          from = personMonthDate.startOf('month').format('YYYY-MM-DD')
          to   = personMonthDate.endOf('month').format('YYYY-MM-DD')
        }
        if (!from) return
        const [journal, shifts] = await Promise.all([
          fetchWorkJournalRange(from, to),
          fetchShiftsRange(from, to).catch(() => ({} as ShiftsRangeData)),
        ])
        setRangeData(journal)
        setSingleData(null)
        setShiftMapByDate(shifts)
        setDateActiveKeys(journal.days.map((_, i) => `pday-${i}`))
        onStatsChange?.(_computeWJStats(journal.days))
        const names: string[] = []
        const seen = new Set<string>()
        journal.days.forEach(dy => dy.persons.forEach(p => {
          if (!seen.has(p.person)) { names.push(p.person); seen.add(p.person) }
        }))
        setPersonList(names)
        if (names.length > 0 && !names.includes(personFilter)) setPersonFilter(names[0])
      }
    } catch {
      setSingleData(null)
      setRangeData(null)
      setShiftMapByDate({})
    } finally {
      setLoading(false)
    }
  }, [mode, year, month, day, rangeDates, monthDate, personSubMode, personRangeDates, personMonthDate, personFilter])

  // 掛載時自動載入當月份統計，供上方摘要卡片立即顯示；不觸碰表格狀態
  useEffect(() => {
    const from = dayjs().startOf('month').format('YYYY-MM-DD')
    const to   = dayjs().format('YYYY-MM-DD')
    fetchWorkJournalRange(from, to)
      .then(j => onStatsChange?.(_computeWJStats(j.days)))
      .catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 日期 pickers
  const renderPickers = () => {
    if (mode === 'single') return (
      <Space wrap>
        <Text type="secondary" style={{ fontSize: 15 }}>查詢日期：</Text>
        <Select value={year} onChange={v => setYear(v)} style={{ width: 90 }}
          options={Array.from({ length: 3 }, (_, i) => { const y = dayjs().year() - i; return { label: `${y} 年`, value: y } })} />
        <Select value={month} onChange={v => { setMonth(v); if (day > dayjs(`${year}-${String(v).padStart(2,'0')}-01`).daysInMonth()) setDay(1) }}
          style={{ width: 80 }}
          options={Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1} 月`, value: i + 1 }))} />
        <Select value={day} onChange={v => setDay(v)} style={{ width: 80 }} options={dayOptions} />
      </Space>
    )
    if (mode === 'range') return (
      <Space wrap>
        <Text type="secondary" style={{ fontSize: 15 }}>查詢區間（最多 31 天）：</Text>
        <DatePicker.RangePicker
          value={rangeDates}
          onChange={v => setRangeDates(v as [Dayjs, Dayjs] | null)}
          format="YYYY/MM/DD"
          style={{ width: 260 }}
          disabledDate={cur => cur && cur > dayjs().endOf('day')}
        />
      </Space>
    )
    if (mode === 'month') return (
      <Space wrap>
        <Text type="secondary" style={{ fontSize: 15 }}>查詢月份：</Text>
        <DatePicker
          picker="month"
          value={monthDate}
          onChange={v => setMonthDate(v)}
          format="YYYY 年 MM 月"
          style={{ width: 150 }}
          disabledDate={cur => cur && cur > dayjs().endOf('month')}
        />
      </Space>
    )
    // person mode
    return (
      <Space wrap>
        <Segmented
          size="small"
          value={personSubMode}
          onChange={v => { setPersonSubMode(v as 'range'|'month'); setRangeData(null); setPersonList([]) }}
          options={[{ label: '整月', value: 'month' }, { label: '區間', value: 'range' }]}
        />
        {personSubMode === 'month' ? (
          <DatePicker
            picker="month"
            value={personMonthDate}
            onChange={v => setPersonMonthDate(v)}
            format="YYYY 年 MM 月"
            style={{ width: 150 }}
            disabledDate={cur => cur && cur > dayjs().endOf('month')}
          />
        ) : (
          <DatePicker.RangePicker
            value={personRangeDates}
            onChange={v => setPersonRangeDates(v as [Dayjs, Dayjs] | null)}
            format="YYYY/MM/DD"
            style={{ width: 260 }}
            disabledDate={cur => cur && cur > dayjs().endOf('day')}
          />
        )}
        {personList.length > 0 && (
          <Select
            value={personFilter}
            onChange={v => setPersonFilter(v)}
            style={{ width: 120 }}
            placeholder="選擇人員"
            options={personList.map(p => ({ label: p, value: p }))}
            suffixIcon={<UserOutlined />}
          />
        )}
      </Space>
    )
  }

  // 結果摘要文字
  const renderSummary = () => {
    if (singleData) return (
      <Text type="secondary" style={{ fontSize: 14 }}>
        {singleData.date} ｜ 共 <Text strong>{singleData.total_rows}</Text> 筆
      </Text>
    )
    if (rangeData && mode !== 'person') return (
      <Text type="secondary" style={{ fontSize: 14 }}>
        {rangeData.date_from} ～ {rangeData.date_to} ｜ 共 <Text strong>{rangeData.total_rows}</Text> 筆（{rangeData.days.length} 天）
      </Text>
    )
    if (rangeData && mode === 'person' && personFilter) {
      const personRows = rangeData.days.reduce((acc, d) => {
        const p = d.persons.find(p => p.person === personFilter)
        return acc + (p?.rows.length ?? 0)
      }, 0)
      return (
        <Text type="secondary" style={{ fontSize: 14 }}>
          <UserOutlined style={{ marginRight: 4 }} /><Text strong>{personFilter}</Text>
          　{rangeData.date_from} ～ {rangeData.date_to} ｜ 共 <Text strong>{personRows}</Text> 筆（{rangeData.days.length} 天）
        </Text>
      )
    }
    return null
  }

  // 結果區域
  const renderResult = () => {
    if (loading) return (
      <div style={{ textAlign: 'center', paddingTop: 60 }}>
        <Spin tip="載入工作日誌…" />
      </div>
    )

    // 單日
    if (singleData) {
      if (singleData.total_rows === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          {singleData.date} 無工作記錄
        </div>
      )
      return (
        <DayPersonCollapse
          persons={singleData.persons}
          collapsed={globalCollapsed}
          shiftMap={shiftMapByDate[singleData.date.replace(/\//g, '-')]}
        />
      )
    }

    // 人員模式
    if (mode === 'person' && rangeData) {
      if (!personFilter) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          請選擇人員後按下「查詢」
        </div>
      )
      const filteredDays = rangeData.days
        .map(daily => ({
          ...daily,
          persons: daily.persons.filter(p => p.person === personFilter),
        }))
        .filter(daily => daily.persons.length > 0)

      if (filteredDays.length === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          {personFilter} 在此區間內無工作記錄
        </div>
      )
      const personDateItems = filteredDays.map((daily, di) => {
        const personRows = daily.persons[0]?.rows ?? []
        const dayMin = personRows.reduce((a, r) => a + (r.work_min ?? 0), 0)
        const rowCount = personRows.length
        return {
          key: `pday-${di}`,
          label: (
            <Space wrap style={{ rowGap: 4 }}>
              <Text strong style={{ fontSize: 16, color: '#1B3A5C' }}>{daily.date}</Text>
              <Tag color="blue">{rowCount} 項</Tag>
              {dayMin > 0 && <Tag color="geekblue">{dayMin} min</Tag>}
              {CAT_COLS.map(cat => {
                const cnt = personRows.filter(r => r.category === cat).length
                return cnt > 0 ? (
                  <Tag key={cat} color={CATEGORY_TAG_COLORS[cat] ?? 'default'}
                       style={{ fontSize: 13, margin: 0 }}>{cat} {cnt}</Tag>
                ) : null
              })}
            </Space>
          ),
          children: (
            <DayPersonCollapse
              persons={daily.persons}
              shiftMap={shiftMapByDate[daily.date.replace(/\//g, '-')]}
            />
          ),
        }
      })
      return (
        <Collapse
          activeKey={dateActiveKeys}
          onChange={keys => setDateActiveKeys(keys as string[])}
          items={personDateItems}
          style={{ background: '#f0f4f8' }}
        />
      )
    }

    // 區間 / 整月
    if (rangeData) {
      if (rangeData.total_rows === 0) return (
        <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
          查詢區間內無工作記錄
        </div>
      )
      const dateItems = rangeData.days.map((daily, di) => {
        const totalWH = daily.persons.reduce(
          (acc, p) => acc + p.rows.reduce((a, r) => a + (r.work_min ?? 0), 0), 0
        )
        const allRows = daily.persons.flatMap(p => p.rows)
        return {
          key: `day-${di}`,
          label: (
            <Space wrap style={{ rowGap: 4 }}>
              <Text strong style={{ fontSize: 16, color: '#1B3A5C' }}>{daily.date}</Text>
              <Tag color="blue">{daily.total_rows} 筆</Tag>
              {totalWH > 0 && <Tag color="geekblue">{totalWH} min</Tag>}
              <Text type="secondary" style={{ fontSize: 14 }}>{daily.persons.length} 位人員</Text>
              {CAT_COLS.map(cat => {
                const cnt = allRows.filter(r => r.category === cat).length
                return cnt > 0 ? (
                  <Tag key={cat} color={CATEGORY_TAG_COLORS[cat] ?? 'default'}
                       style={{ fontSize: 13, margin: 0 }}>{cat} {cnt}</Tag>
                ) : null
              })}
            </Space>
          ),
          children: (
            <DayPersonCollapse
              persons={daily.persons}
              shiftMap={shiftMapByDate[daily.date.replace(/\//g, '-')]}
            />
          ),
        }
      })
      return (
        <Collapse
          activeKey={dateActiveKeys}
          onChange={keys => setDateActiveKeys(keys as string[])}
          items={dateItems}
          style={{ background: '#f0f4f8' }}
        />
      )
    }

    return (
      <div style={{ textAlign: 'center', paddingTop: 40, color: '#aaa', fontSize: 16 }}>
        請選擇日期後按下「查詢」
      </div>
    )
  }

  return (
    <div style={{ paddingBottom: 24 }}>
      {/* 模式切換 */}
      <div style={{ marginBottom: 12 }}>
        <Segmented
          value={mode}
          onChange={v => {
            setMode(v as JournalMode)
            setSingleData(null); setRangeData(null)
            setPersonList([]); setPersonFilter('')
          }}
          options={[
            { label: '單日',  value: 'single' },
            { label: '區間',  value: 'range' },
            { label: '整月',  value: 'month' },
            { label: <Space size={4}><UserOutlined />人員</Space>, value: 'person' },
          ]}
        />
      </div>

      {/* 日期選擇器 + 查詢按鈕 */}
      <Card size="small" style={{ marginBottom: 12, background: '#fafafa' }}>
        <Space wrap>
          {renderPickers()}
          <Button type="primary" icon={<ReloadOutlined />} onClick={handleLoad} loading={loading}>
            查詢
          </Button>
          {/* 縮合/展開按鈕：有資料才顯示 */}
          {(singleData || rangeData) && (
            <Button
              size="small"
              onClick={() => {
                const next = !globalCollapsed
                setGlobalCollapsed(next)
                if (rangeData) {
                  const prefix = mode === 'person' ? 'pday' : 'day'
                  setDateActiveKeys(next ? [] : rangeData.days.map((_, i) => `${prefix}-${i}`))
                }
              }}
            >
              {globalCollapsed ? '全部展開' : '全部縮合'}
            </Button>
          )}
          {/* Excel 匯出按鈕：有資料才顯示 */}
          {(singleData || rangeData) && (() => {
            let from = '', to = '', exportPerson: string | undefined
            if (mode === 'single' && singleData) {
              const d = singleData.date.replace(/\//g, '-')
              from = d; to = d
            } else if ((mode === 'range' || mode === 'month') && rangeData) {
              from = rangeData.date_from; to = rangeData.date_to
            } else if (mode === 'person' && rangeData) {
              from = rangeData.date_from; to = rangeData.date_to
              exportPerson = personFilter || undefined
            }
            if (!from) return null
            const label = exportPerson ? `${exportPerson}_${from}_${to}` : `${from}_${to}`
            return (
              <Button
                icon={<FileExcelOutlined />}
                style={{ color: '#52c41a', borderColor: '#52c41a' }}
                onClick={() => downloadFile(
                  getJournalExcelUrl(from, to, exportPerson),
                  `工作日誌_${label}.xlsx`,
                )}
              >
                匯出 Excel
              </Button>
            )
          })()}
          {renderSummary()}
        </Space>
      </Card>

      {/* 結果 */}
      {renderResult()}
    </div>
  )
}


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
  const [execStatsYear,    setExecStatsYear]    = useState<CategoryStats | null>(null)  // 全年（month=0），供每月累計表用
  const [dazhiRepairStats, setDazhiRepairStats] = useState<DazhiRepairStatsData | null>(null)
  const [luqunRepairStats, setLuqunRepairStats] = useState<LuqunRepairStatsData | null>(null)
  const [hotelMonthlyData, setHotelMonthlyData] = useState<HotelMonthlyHoursData | null>(null)
  const [mallMonthlyData,  setMallMonthlyData]  = useState<MallMonthlyHoursData | null>(null)
  const [hotelDailyData,   setHotelDailyData]   = useState<HotelDailyHoursData | null>(null)
  const [mallDailyData,    setMallDailyData]    = useState<MallDailyHoursData | null>(null)
  // 主管交辦／緊急事件 stats
  const [otherTasksStats, setOtherTasksStats] = useState<Record<string, OtherTaskTypeStat> | null>(null)
  // 工作日誌 TAB 類別統計（從表格資料直接加總，確保上方摘要卡片與表格數字一致）
  const [wjStats, setWjStats] = useState<WJStats>({})
  // 受控 Collapse activeKey（全收合/全展開用）
  // 頁籤狀態
  const [activeTab, setActiveTab] = useState<string>('overview')

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
      const [luqun, dazhi, hotelMon, mallMon, hotelDay, mallDay, execSt, execStYr, dazhiSt, luqunSt, otherSt] =
        await Promise.allSettled([
          fetchLuqunDashboard(selectedYear, selectedMonth),
          fetchDazhiDashboard(selectedYear, selectedMonth),
          fetchHotelMonthlyHours(selectedYear),
          fetchMallMonthlyHours(selectedYear),
          fetchHotelDailyHours(selectedYear, selectedMonth),
          fetchMallDailyHours(selectedYear, selectedMonth),
          fetchStats({ year: selectedYear, month: selectedMonth, sources: 'all', category: 'all', person: 'all' }),
          fetchStats({ year: selectedYear, month: 0,             sources: 'all', category: 'all', person: 'all' }),
          fetchDazhiRepairStats(selectedYear),
          fetchLuqunRepairStats(selectedYear),
          fetchOtherTaskStats({ year: selectedYear, month: selectedMonth }),
        ])
      if (luqun.status     === 'fulfilled') setLuqunData(luqun.value)
      if (dazhi.status     === 'fulfilled') setDazhiData(dazhi.value as unknown as RepairDashboardData)
      if (hotelMon.status  === 'fulfilled') setHotelMonthlyData(hotelMon.value)
      if (mallMon.status   === 'fulfilled') setMallMonthlyData(mallMon.value)
      if (hotelDay.status  === 'fulfilled') setHotelDailyData(hotelDay.value)
      if (mallDay.status   === 'fulfilled') setMallDailyData(mallDay.value)
      if (execSt.status    === 'fulfilled') setExecStats(execSt.value)
      if (execStYr.status  === 'fulfilled') setExecStatsYear(execStYr.value)
      if (dazhiSt.status   === 'fulfilled') setDazhiRepairStats(dazhiSt.value)
      if (luqunSt.status   === 'fulfilled') setLuqunRepairStats(luqunSt.value)
      if (otherSt.status   === 'fulfilled') setOtherTasksStats(otherSt.value)
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

    // 飯店：使用 daily-hours 月加總，與 HotelMgmtDashboard Tab B 口徑完全一致
    // （monthly-hours 的 IHG 用不重複房號數，daily 用原始記錄加總，兩者可能不同）
    const dFind = (name: string) => hotelDailyData?.rows.find(r => r.category === name)
    const hd = (name: string) => {
      const row = dFind(name)
      return row ? row.cases.reduce((a: number, b: number) => a + b, 0) : 0
    }
    const hotelCatCases: Record<string, number> = {
      現場報修: hd('飯店工務部'),
      // 上級交辦/緊急事件 依 venue 欄位分開：.hotel = venue=飯店的件數
      上級交辦: otherTasksStats?.['上級交辦']?.hotel ?? 0,
      緊急事件: otherTasksStats?.['緊急事件']?.hotel ?? 0,
      例行維護: hd('客房保養管理') + hd('飯店週期保養') + hd('IHG客房保養'),
      每日巡檢: hd('飯店每日巡檢'),
    }

    // 商場：monthly-hours cases[mi]（商場無 IHG 口徑差異問題）
    const mFind = (name: string) => mallMonthlyData?.rows.find(r => r.category === name)
    const mc = (name: string) => mFind(name)?.cases[mi] ?? 0

    const mallCatCases: Record<string, number> = {
      現場報修: mc('現場報修'),
      // 上級交辦/緊急事件 依 venue 欄位分開：.mall = venue=商場的件數
      上級交辦: otherTasksStats?.['上級交辦']?.mall ?? 0,
      緊急事件: otherTasksStats?.['緊急事件']?.mall ?? 0,
      例行維護: mc('例行維護'),
      每日巡檢: mc('每日巡檢'),
    }

    return CATS.map(cat => ({
      key:        cat,
      category:   cat,
      hotelCases: hotelCatCases[cat] ?? 0,
      mallCases:  mallCatCases[cat] ?? 0,
    }))
  }, [hotelDailyData, mallMonthlyData, otherTasksStats, selectedMonth])

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
  // P0 fix: 分子(execStats工時) 與 分母(execStats件數) 必須同一資料集，
  // 不可混用 repair dashboard 件數（含 work_hours=0 的案件）作分母
  const execTotalCases  = execStats?.kpi?.total_cases ?? 0
  const avgHrPerCase    = execTotalCases > 0 ? Math.round(totalHours / execTotalCases * 10) / 10 : 0
  const hotelCasePct    = totalCases > 0 ? Math.round((dKpi?.total ?? 0) / totalCases * 100) : 0
  const mallCasePct     = totalCases > 0 ? Math.round((lKpi?.total ?? 0) / totalCases * 100) : 0
  // 待辦驗數（直接來自 repair dashboard KPI）
  const dazhiPendingVerify = dKpi?.pending_verify ?? 0
  const luqunPendingVerify = lKpi?.pending_verify ?? 0
  // 上期未結（來自 /stats/repair，取選定月的 prev_uncompleted）
  const dazhiPrevUncomp = dazhiRepairStats?.months[selectedMonth]?.prev_uncompleted ?? 0
  const luqunPrevUncomp = luqunRepairStats?.months[selectedMonth]?.prev_uncompleted ?? 0

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

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        style={{ marginTop: 4 }}
        items={[
          {
            key: 'overview',
            label: '集團工務概覽',
            children: (
              <>
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
            <Tooltip title="來源：工項分析模組（work-category-analysis）
僅含有工時記錄的案件（work_hours > 0）
數值可能低於各模組工時加總">
              <Statistic
                title={<Text style={{ fontSize: 12, color: C.gray }}>本月總工時 ℹ</Text>}
                value={totalHours}
                precision={1}
                suffix="HR"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: C.accent }}
              />
            </Tooltip>
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

      {/* ── 集團 KPI Row 2：待辦驗數 + 上期未結 ─────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {/* 飯店待辦驗數 */}
        <Col xs={12} sm={8} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.warning}`, textAlign: 'center' }}>
            <Tooltip title="待客戶驗收確認的飯店工務案件數">
              <Statistic
                title={<Text style={{ fontSize: 12, color: C.gray }}>飯店待辦驗數</Text>}
                value={dazhiPendingVerify}
                suffix="件"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: dazhiPendingVerify > 0 ? C.warning : C.success }}
              />
            </Tooltip>
          </Card>
        </Col>
        {/* 商場待辦驗數 */}
        <Col xs={12} sm={8} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.warning}`, textAlign: 'center' }}>
            <Tooltip title="待客戶驗收確認的商場工務案件數">
              <Statistic
                title={<Text style={{ fontSize: 12, color: C.gray }}>商場待辦驗數</Text>}
                value={luqunPendingVerify}
                suffix="件"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: luqunPendingVerify > 0 ? C.warning : C.success }}
              />
            </Tooltip>
          </Card>
        </Col>
        {/* 飯店上期未結 */}
        <Col xs={12} sm={8} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.danger}`, textAlign: 'center' }}>
            <Tooltip title={`${selectedYear} 年 ${selectedMonth} 月的上期遺留未結案件（來源：/stats/repair prev_uncompleted）`}>
              <Statistic
                title={<Text style={{ fontSize: 12, color: C.gray }}>飯店上期未結</Text>}
                value={dazhiPrevUncomp}
                suffix="件"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: dazhiPrevUncomp > 0 ? C.danger : C.success }}
              />
            </Tooltip>
          </Card>
        </Col>
        {/* 商場上期未結 */}
        <Col xs={12} sm={8} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: `3px solid ${C.danger}`, textAlign: 'center' }}>
            <Tooltip title={`${selectedYear} 年 ${selectedMonth} 月的上期遺留未結案件（來源：/stats/repair prev_uncompleted）`}>
              <Statistic
                title={<Text style={{ fontSize: 12, color: C.gray }}>商場上期未結</Text>}
                value={luqunPrevUncomp}
                suffix="件"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: luqunPrevUncomp > 0 ? C.danger : C.success }}
              />
            </Tooltip>
          </Card>
        </Col>
      </Row>

      {/* ── 集團 KPI Row 3：主管交辦 + 緊急事件 件數/工時 ──────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {/* 上級交辦 件數 */}
        <Col xs={12} sm={6} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: '3px solid #722ed1', textAlign: 'center' }}>
            <Tooltip title="來源：hotel/other-tasks（task_type = 上級交辦），以建立日期 year/month 篩選">
              <Statistic
                title={<Text style={{ fontSize: 12, color: C.gray }}>上級交辦 件數 ℹ</Text>}
                value={otherTasksStats?.['上級交辦']?.total ?? 0}
                suffix="件"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: '#722ed1' }}
              />
            </Tooltip>
          </Card>
        </Col>
        {/* 上級交辦 工時 */}
        <Col xs={12} sm={6} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: '3px solid #722ed1', textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>上級交辦 工時</Text>}
              value={otherTasksStats?.['上級交辦']?.work_hours ?? 0}
              precision={1}
              suffix="HR"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: '#9254de' }}
            />
          </Card>
        </Col>
        {/* 緊急事件 件數 */}
        <Col xs={12} sm={6} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: '3px solid #cf1322', textAlign: 'center' }}>
            <Tooltip title="來源：hotel/other-tasks（task_type = 緊急事件），以建立日期 year/month 篩選">
              <Statistic
                title={<Text style={{ fontSize: 12, color: C.gray }}>緊急事件 件數 ℹ</Text>}
                value={otherTasksStats?.['緊急事件']?.total ?? 0}
                suffix="件"
                valueStyle={{ fontSize: 22, fontWeight: 700, color: '#cf1322' }}
              />
            </Tooltip>
          </Card>
        </Col>
        {/* 緊急事件 工時 */}
        <Col xs={12} sm={6} md={6} lg={6}>
          <Card size="small" bordered={false} style={{ borderTop: '3px solid #cf1322', textAlign: 'center' }}>
            <Statistic
              title={<Text style={{ fontSize: 12, color: C.gray }}>緊急事件 工時</Text>}
              value={otherTasksStats?.['緊急事件']?.work_hours ?? 0}
              precision={1}
              suffix="HR"
              valueStyle={{ fontSize: 22, fontWeight: 700, color: '#f5222d' }}
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
              <ResponsiveContainer width="100%" height={240}>
                <PieChart margin={{ top: 24, right: 48, bottom: 24, left: 48 }}>
                  <Pie
                    data={dazhiData.type_dist as TypeDistItem[]}
                    dataKey="count"
                    nameKey="type"
                    cx="50%" cy="50%"
                    outerRadius={65}
                    label={({ type, percent }: { type: string; percent: number }) =>
                      percent > 0.04 ? `${type} ${(percent * 100).toFixed(0)}%` : ''
                    }
                    labelLine={true}
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
              <ResponsiveContainer width="100%" height={240}>
                <PieChart margin={{ top: 24, right: 48, bottom: 24, left: 48 }}>
                  <Pie
                    data={luqunData.type_dist as TypeDistItem[]}
                    dataKey="count"
                    nameKey="type"
                    cx="50%" cy="50%"
                    outerRadius={65}
                    label={({ type, percent }: { type: string; percent: number }) =>
                      percent > 0.04 ? `${type} ${(percent * 100).toFixed(0)}%` : ''
                    }
                    labelLine={true}
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
                  ? <HotelDailyTable
                      data={hotelDailyData}
                      supervisorTotal={otherTasksStats?.['上級交辦']?.total ?? 0}
                      emergencyTotal={otherTasksStats?.['緊急事件']?.total ?? 0}
                    />
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
                children: <ExecMonthlyTable stats={execStatsYear} />,
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
              </>
            ),
          },
          {
            key: 'journal',
            label: '工作日誌',
            children: (
              <>
                {/* 主管交辦／緊急事件 本期摘要（來源：工作日誌表格加總）*/}
                <Card
                  size="small"
                  style={{ marginBottom: 12, borderLeft: `3px solid ${CATEGORY_COLOR['上級交辦']}` }}
                  bodyStyle={{ padding: '10px 16px' }}
                >
                  <Row align="middle" gutter={[16, 8]}>
                    <Col flex="none">
                      <Text strong style={{ fontSize: 13, color: C.primary }}>
                        <AlertOutlined style={{ marginRight: 6, color: CATEGORY_COLOR['上級交辦'] }} />
                        主管交辦／緊急事件
                      </Text>
                    </Col>
                    <Col flex="auto">
                      <Space size={20} wrap>
                        {(['上級交辦', '緊急事件'] as const).map(cat => {
                          const s = wjStats[cat]
                          return (
                            <Space key={cat} size={4} style={{ alignItems: 'baseline' }}>
                              <Tag color={CATEGORY_TAG_COLORS[cat]} style={{ margin: 0 }}>{cat}</Tag>
                              <Text strong style={{ color: CATEGORY_COLOR[cat], fontSize: 15 }}>
                                {s ? s.cases : '—'} 件
                              </Text>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                飯{s ? s.hotel.cases : 0} 場{s ? s.mall.cases : 0}
                              </Text>
                              <Text type="secondary" style={{ fontSize: 13 }}>
                                {s ? `${s.hours} HR` : '—'}
                              </Text>
                            </Space>
                          )
                        })}
                        <Text
                          type="secondary"
                          style={{ fontSize: 11, cursor: 'pointer', textDecoration: 'underline' }}
                          onClick={() => window.open('/hotel/other-tasks', '_self')}
                        >
                          → 查看明細
                        </Text>
                      </Space>
                    </Col>
                  </Row>
                </Card>
                {/* 現場報修 / 例行維護 / 每日巡檢 本期摘要（來源：工作日誌表格加總）*/}
                {(() => {
                  const CAT_DEFS: Array<{ key: keyof typeof CATEGORY_COLOR }> = [
                    { key: '現場報修' },
                    { key: '例行維護' },
                    { key: '每日巡檢' },
                  ]
                  return (
                    <Card
                      size="small"
                      style={{ marginBottom: 12, borderLeft: `3px solid ${CATEGORY_COLOR['現場報修']}` }}
                      bodyStyle={{ padding: '10px 16px' }}
                    >
                      <Row align="middle" gutter={[16, 8]}>
                        <Col flex="none">
                          <Text strong style={{ fontSize: 13, color: C.primary }}>
                            <ToolOutlined style={{ marginRight: 6, color: CATEGORY_COLOR['現場報修'] }} />
                            工務作業
                          </Text>
                        </Col>
                        <Col flex="auto">
                          <Space size={20} wrap>
                            {CAT_DEFS.map(({ key }) => {
                              const s = wjStats[key]
                              return (
                                <Space key={key} size={4} style={{ alignItems: 'baseline' }}>
                                  <Tag color={CATEGORY_TAG_COLORS[key]} style={{ margin: 0 }}>{key}</Tag>
                                  <Text strong style={{ color: CATEGORY_COLOR[key], fontSize: 15 }}>
                                    {s ? s.cases : '—'} 件
                                  </Text>
                                  <Text type="secondary" style={{ fontSize: 12 }}>
                                    飯{s ? s.hotel.cases : 0} 場{s ? s.mall.cases : 0}
                                  </Text>
                                  <Text type="secondary" style={{ fontSize: 13 }}>
                                    {s ? `${s.hours} HR` : '—'}
                                  </Text>
                                </Space>
                              )
                            })}
                          </Space>
                        </Col>
                      </Row>
                    </Card>
                  )
                })()}
                <WorkJournalTab onStatsChange={setWjStats} />
              </>
            ),
          },
          {
            key: 'methodology',
            label: '統計基準說明',
            children: (
              <iframe
                src="/report-count-methodology.html"
                style={{ width: '100%', height: 'calc(100vh - 180px)', border: 'none', borderRadius: 8 }}
                title="統計基準說明"
              />
            ),
          },
        ]}
      />
    </div>
  )
}
