/**
 * 集團管理 Portal 首頁 — 總覽 Dashboard
 *
 * 版面規範（PROTECTED.md）：
 *  - KPI 卡片：4 欄 Row、Card size="small"、無 border
 *  - 品牌色：primary #1B3A5C、accent #4BA8E8
 *  - Breadcrumb：每頁頂部，不可移除
 *  - 工作狀態色：已完成=#52c41a, 進行中=#1677ff, 非本月=#8c8c8c, 待排程=#faad14
 *
 * 資料來源（3 個現有 API，Promise.allSettled 平行呼叫，互不依賴）：
 *  - GET /api/v1/dashboard/kpi            → 飯店客房保養 + 庫存 + 同步狀態
 *  - GET /api/v1/mall/dashboard/summary   → 商場巡檢（B1F/B2F/RF）+ 本月週期保養
 *  - GET /api/v1/security/dashboard/summary → 保全巡檢（7 Sheets）今日摘要
 *  - GET /api/v1/dashboard/graph          → 關聯圖譜（GraphView，ROW 4）
 */
import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Typography, Tag, Table,
  Spin, Tooltip, Progress, Space, Button, Breadcrumb, Divider, Badge,
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
} from 'recharts'

import { dashboardApi, type DashboardKPI, type SyncRecord, type DashboardTrend, type ClosureStats } from '@/api/dashboard'
import { fetchDashboardSummary } from '@/api/mallDashboard'
import { fetchSecurityDashboardSummary } from '@/api/securityPatrol'
import type { DashboardSummary as MallSummary } from '@/types/mallDashboard'
import type { SecurityDashboardSummary } from '@/types/securityPatrol'
import { fetchDashboard as fetchLuqunDashboard } from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhiDashboard } from '@/api/dazhiRepair'
import type { DashboardData as RepairDashboardData } from '@/types/luqunRepair'
import { getBudgetDashboard, type DashboardData as BudgetDashboardData } from '@/api/budget'
import ExecMetricsCard from '@/components/ExecMetrics'
import GraphView from '@/components/GraphView'

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

// ── 工務報修主管摘要卡（樂群 / 大直 共用）────────────────────────────────────
function RepairSummaryCard({
  label, data, color, accentColor, onNavigate,
}: {
  label:       string
  data:        RepairDashboardData | null
  color:       string
  accentColor: string
  onNavigate:  () => void
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
    <Col xs={24} lg={12}>
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
                {dayjs().format('M')} 月
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
          </>
        )}
      </Card>
    </Col>
  )
}

// ── 群組卡片標題列 ────────────────────────────────────────────────────────────
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

  // 取得本月年/月
  const curYear  = dayjs().year()
  const curMonth = dayjs().month() + 1

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [hotel, mall, sec, trend, closure, luqun, dazhi, budget] = await Promise.allSettled([
        dashboardApi.kpi().then(r => r.data),
        fetchDashboardSummary(today),
        fetchSecurityDashboardSummary(today),
        dashboardApi.trend(trendDays).then(r => r.data),
        dashboardApi.closureStats().then(r => r.data),
        fetchLuqunDashboard(curYear, curMonth),
        fetchDazhiDashboard(curYear, curMonth),
        getBudgetDashboard().then(r => r.data),
      ])
      if (hotel.status   === 'fulfilled') setHotelKpi(hotel.value)
      if (mall.status    === 'fulfilled') setMallData(mall.value)
      if (sec.status     === 'fulfilled') setSecData(sec.value)
      if (trend.status   === 'fulfilled') setTrendData(trend.value)
      if (closure.status === 'fulfilled') setClosureData(closure.value)
      if (luqun.status   === 'fulfilled') setLuqunData(luqun.value)
      if (dazhi.status   === 'fulfilled') setDazhiData(dazhi.value as unknown as RepairDashboardData)
      if (budget.status  === 'fulfilled') setBudgetData(budget.value)
      setRefreshed(new Date())
    } finally {
      setLoading(false)
    }
  }, [today, trendDays, curYear, curMonth])

  useEffect(() => { loadAll() }, [loadAll])

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

  const mallRate  = mallData?.inspection.completion_rate  ?? 0
  const secRate   = secData?.completion_rate_all          ?? 0
  const hotelRate = rm?.completion_rate                   ?? 0

  // 全域待關注：商場異常 + 商場PM逾期 + 保全異常 + 客房未完成 + 工務未結案 + 預算超支/即將超支
  const mallAbnormal  = (mallData?.inspection.abnormal_items ?? 0) + (mallData?.pm.overdue_items ?? 0)
  const secAbnormal   = secData?.abnormal_items_all ?? 0
  const hotelPending  = rm?.total_incomplete ?? 0
  const repairPending = (luqunData?.kpi?.uncompleted ?? 0) + (dazhiData?.kpi?.uncompleted ?? 0)
  const budgetAlert   = (budgetData?.summary.overrun_count ?? 0) + (budgetData?.summary.near_overrun_count ?? 0)
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
          ROW 0 — 主管指標（ExecMetricsCard，沿用 exec-dashboard 同一套 API）
          ── HIDDEN_BUDGET START ── 預算管理摘要卡暫時隱藏，程式碼與 API 保留，
          待完整預算功能確認後移除此註解並恢復下方 BudgetSummaryCard Row ──
      ══════════════════════════════════════════════════════════════ */}
      {/*
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <BudgetSummaryCard data={budgetData} onNavigate={navigate} />
        </Col>
      </Row>
      ── HIDDEN_BUDGET END ──
      */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <ExecMetricsCard onNavigate={navigate} />
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.3 — 工務報修主管摘要（樂群 + 大直）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <RepairSummaryCard
          label="樂群工務報修"
          data={luqunData}
          color="#1B3A5C"
          accentColor="#4BA8E8"
          onNavigate={() => navigate('/luqun-repair')}
        />
        <RepairSummaryCard
          label="大直工務部"
          data={dazhiData}
          color="#0d6b4e"
          accentColor="#36b37e"
          onNavigate={() => navigate('/dazhi-repair')}
        />
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 0.5 — 今日重點摘要（P1-C）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <TodaySummaryCard
            totalAlerts={totalAlerts}
            mallAbnormal={mallAbnormal}
            secAbnormal={secAbnormal}
            hotelPending={hotelPending}
            repairPending={repairPending}
            budgetAlert={budgetAlert}
            mallRate={mallRate}
            secRate={secRate}
            hotelRate={hotelRate}
            luqunData={luqunData}
            dazhiData={dazhiData}
            budgetData={budgetData}
          />
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 1 — KPI 總覽卡（PROTECTED：4 欄、size="small"、無 border）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>

        {/* 商場巡檢完成率 */}
        <Col xs={24} sm={12} lg={6}>
          <Card
            size="small" bordered={false}
            style={{
              background: '#f6ffed',
              borderLeft: `4px solid ${rateColor(mallRate)}`,
              cursor: 'pointer',
            }}
            onClick={() => navigate('/mall/dashboard')}
          >
            <Statistic
              title={<><ShopOutlined style={{ color: rateColor(mallRate) }} /> 商場巡檢完成率</>}
              value={mallData ? mallRate : '—'}
              suffix={mallData ? '%' : ''}
              precision={mallData ? 1 : 0}
              valueStyle={{ color: rateColor(mallRate), fontSize: 28 }}
            />
            <Progress
              percent={mallRate} showInfo={false}
              strokeColor={rateColor(mallRate)} size="small"
              style={{ marginTop: 6 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {mallData
                ? `${mallData.inspection.checked_items} / ${mallData.inspection.total_items} 項已查`
                : '資料未載入'}
            </Text>
          </Card>
        </Col>

        {/* 保全巡檢完成率 */}
        <Col xs={24} sm={12} lg={6}>
          <Card
            size="small" bordered={false}
            style={{
              background: '#fff7e6',
              borderLeft: `4px solid ${rateColor(secRate)}`,
              cursor: 'pointer',
            }}
            onClick={() => navigate('/security/dashboard')}
          >
            <Statistic
              title={<><SafetyOutlined style={{ color: rateColor(secRate) }} /> 保全巡檢完成率</>}
              value={secData ? secRate : '—'}
              suffix={secData ? '%' : ''}
              precision={secData ? 1 : 0}
              valueStyle={{ color: rateColor(secRate), fontSize: 28 }}
            />
            <Progress
              percent={secRate} showInfo={false}
              strokeColor={rateColor(secRate)} size="small"
              style={{ marginTop: 6 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {secData
                ? `今日 ${secData.total_batches_all} 場次、異常 ${secData.abnormal_items_all} 項`
                : '資料未載入'}
            </Text>
          </Card>
        </Col>

        {/* 客房保養完成率 */}
        <Col xs={24} sm={12} lg={6}>
          <Card
            size="small" bordered={false}
            style={{
              background: '#e6f4ff',
              borderLeft: `4px solid ${rateColor(hotelRate)}`,
              cursor: 'pointer',
            }}
            onClick={() => navigate('/hotel/room-maintenance')}
          >
            <Statistic
              title={<><BuildOutlined style={{ color: rateColor(hotelRate) }} /> 客房保養完成率</>}
              value={rm ? hotelRate : '—'}
              suffix={rm ? '%' : ''}
              precision={rm ? 1 : 0}
              valueStyle={{ color: rateColor(hotelRate), fontSize: 28 }}
            />
            <Progress
              percent={hotelRate} showInfo={false}
              strokeColor={rateColor(hotelRate)} size="small"
              style={{ marginTop: 6 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {rm ? `${rm.completed} / ${rm.total} 間已完成` : '資料未載入'}
            </Text>
          </Card>
        </Col>

        {/* 全域待關注 */}
        <Col xs={24} sm={12} lg={6}>
          <Card
            size="small" bordered={false}
            style={{ borderLeft: `4px solid ${alertColor}` }}
          >
            <Statistic
              title={<><AlertOutlined style={{ color: alertColor }} /> 全域待關注</>}
              value={totalAlerts}
              suffix="項"
              valueStyle={{ color: alertColor, fontSize: 28 }}
            />
            <div style={{ marginTop: 6, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {mallAbnormal > 0 && (
                <Tag color="error" style={{ fontSize: 11 }}>商場 {mallAbnormal}</Tag>
              )}
              {secAbnormal > 0 && (
                <Tag color="warning" style={{ fontSize: 11 }}>保全 {secAbnormal}</Tag>
              )}
              {hotelPending > 0 && (
                <Tag color="processing" style={{ fontSize: 11 }}>客房 {hotelPending}</Tag>
              )}
              {repairPending > 0 && (
                <Tag color="orange" style={{ fontSize: 11 }}>工務 {repairPending}</Tag>
              )}
              {budgetAlert > 0 && (
                <Tag color="volcano" style={{ fontSize: 11 }}>預算 {budgetAlert}</Tag>
              )}
              {totalAlerts === 0 && (
                <Text style={{ fontSize: 12, color: C.success }}>
                  <CheckCircleOutlined style={{ marginRight: 4 }} />無異常 🎉
                </Text>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 2 — 群組摘要卡
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>

        {/* ── 飯店管理 ─────────────────────────────────────────────── */}
        <Col xs={24} lg={8}>
          <Card
            size="small" bordered={false}
            title={<GroupCardTitle icon={<BuildOutlined />} label="飯店管理" color={C.primary} />}
            style={{ height: '100%' }}
          >
            {rm ? (
              <>
                {/* ── 一句話結論（P1-B）── */}
                <div style={{
                  background: hotelRate >= 80 ? '#f6ffed' : hotelRate >= 50 ? '#fffbe6' : '#fff1f0',
                  borderLeft: `3px solid ${rateColor(hotelRate)}`,
                  borderRadius: 4, padding: '4px 8px', marginBottom: 10,
                }}>
                  <Text style={{ fontSize: 11, color: rateColor(hotelRate) }}>
                    {hotelConclusion(rm, hotelRate)}
                  </Text>
                </div>

                {/* 客房保養進度 */}
                <div style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text style={{ fontSize: 13 }}>客房保養完成率</Text>
                    <Text strong style={{ color: rateColor(hotelRate) }}>
                      {hotelRate.toFixed(1)}%
                    </Text>
                  </div>
                  <Progress
                    percent={hotelRate} showInfo={false}
                    strokeColor={rateColor(hotelRate)} size="small"
                  />
                  <div style={{ marginTop: 6 }}>
                    <Tag color="success"    style={{ fontSize: 11 }}>已完成 {rm.completed}</Tag>
                    <Tag color="warning"    style={{ fontSize: 11 }}>待排程 {rm.pending}</Tag>
                    <Tag color="processing" style={{ fontSize: 11 }}>進行中 {rm.in_progress}</Tag>
                  </div>
                </div>
                <Divider style={{ margin: '10px 0 8px' }} />
              </>
            ) : (
              <div style={{ padding: '8px 0', color: C.gray, fontSize: 12, marginBottom: 8 }}>
                <ExclamationCircleOutlined style={{ marginRight: 4 }} />飯店資料未載入
              </div>
            )}
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              快速入口
            </Text>
            <QuickLink label="客房保養"    onClick={() => navigate('/hotel/room-maintenance')} />
            <QuickLink label="保養明細"    onClick={() => navigate('/hotel/room-maintenance-detail')} />
            <QuickLink label="週期保養表"  onClick={() => navigate('/hotel/periodic-maintenance')} />
          </Card>
        </Col>

        {/* ── 商場管理 ─────────────────────────────────────────────── */}
        <Col xs={24} lg={8}>
          <Card
            size="small" bordered={false}
            title={<GroupCardTitle icon={<ShopOutlined />} label="商場管理" color={C.accent} />}
            style={{ height: '100%' }}
          >
            {mallData ? (
              <>
                {/* ── 一句話結論（P1-B）── */}
                <div style={{
                  background: mallRate >= 80 && mallData.pm.overdue_items === 0 ? '#f6ffed' : mallData.pm.overdue_items > 0 ? '#fff1f0' : '#fffbe6',
                  borderLeft: `3px solid ${mallRate >= 80 && mallData.pm.overdue_items === 0 ? C.success : mallData.pm.overdue_items > 0 ? C.danger : C.warning}`,
                  borderRadius: 4, padding: '4px 8px', marginBottom: 10,
                }}>
                  <Text style={{
                    fontSize: 11,
                    color: mallRate >= 80 && mallData.pm.overdue_items === 0 ? '#389e0d' : mallData.pm.overdue_items > 0 ? C.danger : '#ad6800',
                  }}>
                    {mallConclusion(mallData, mallRate)}
                  </Text>
                </div>

                {/* 各樓層巡檢完成率 */}
                {mallData.inspection.by_floor.map(floor => (
                  <div key={floor.floor} style={{ marginBottom: 5 }}>
                    <div style={{
                      display: 'flex', alignItems: 'center',
                      justifyContent: 'space-between',
                    }}>
                      <Text style={{ fontSize: 12, width: 38, flexShrink: 0 }}>
                        {floor.floor_label}
                      </Text>
                      <Progress
                        percent={floor.completion_rate}
                        strokeColor={{ '0%': C.accent, '100%': C.success }}
                        style={{ flex: 1, margin: '0 8px' }}
                        size="small"
                      />
                      <Text style={{
                        fontSize: 12, width: 36, textAlign: 'right', flexShrink: 0,
                        color: rateColor(floor.completion_rate),
                      }}>
                        {floor.completion_rate.toFixed(0)}%
                      </Text>
                      {floor.abnormal_items > 0 && (
                        <Tag color="error" style={{ fontSize: 10, marginLeft: 4, flexShrink: 0 }}>
                          異{floor.abnormal_items}
                        </Tag>
                      )}
                    </div>
                  </div>
                ))}
                {/* 週期保養摘要 */}
                <Divider style={{ margin: '8px 0' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text style={{ fontSize: 12 }}>本月週期保養</Text>
                  <Space size={4}>
                    <Tag color="success" style={{ fontSize: 11 }}>
                      完成 {mallData.pm.completed_items}/{mallData.pm.total_items}
                    </Tag>
                    {mallData.pm.overdue_items > 0 && (
                      <Tag color="error" style={{ fontSize: 11 }}>
                        逾期 {mallData.pm.overdue_items}
                      </Tag>
                    )}
                  </Space>
                </div>
                <Divider style={{ margin: '8px 0' }} />
              </>
            ) : (
              <div style={{ padding: '8px 0', color: C.gray, fontSize: 12, marginBottom: 8 }}>
                <ExclamationCircleOutlined style={{ marginRight: 4 }} />商場資料未載入
              </div>
            )}
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              快速入口
            </Text>
            <QuickLink label="商場 Dashboard"  onClick={() => navigate('/mall/dashboard')} />
            <QuickLink label="B1F 巡檢"        onClick={() => navigate('/mall/b1f-inspection')} />
            <QuickLink label="B2F 巡檢"        onClick={() => navigate('/mall/b2f-inspection')} />
            <QuickLink label="RF 巡檢"         onClick={() => navigate('/mall/rf-inspection')} />
            <QuickLink label="週期保養"         onClick={() => navigate('/mall/periodic-maintenance')} />
          </Card>
        </Col>

        {/* ── 春大直商場工務巡檢 ───────────────────────────────────── */}
        <Col xs={24} lg={8}>
          <Card
            size="small" bordered={false}
            title={<GroupCardTitle icon={<ToolOutlined />} label="春大直商場工務巡檢" color="#1B3A5C" />}
            style={{ height: '100%' }}
          >
            <div style={{ padding: '8px 0', color: '#8c8c8c', fontSize: 12, marginBottom: 8 }}>
              各樓層工務設施每日例行巡檢（4F / 3F / 1F~3F / 1F / B1F~B4F）
            </div>
            <Divider style={{ margin: '8px 0' }} />
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              快速入口
            </Text>
            <QuickLink label="工務巡檢 Dashboard" onClick={() => navigate('/mall-facility-inspection/dashboard')} />
            <QuickLink label="4F 巡檢"           onClick={() => navigate('/mall-facility-inspection/4f')} />
            <QuickLink label="3F 巡檢"           onClick={() => navigate('/mall-facility-inspection/3f')} />
            <QuickLink label="1F~3F 巡檢"        onClick={() => navigate('/mall-facility-inspection/1f-3f')} />
            <QuickLink label="B1F~B4F 巡檢"      onClick={() => navigate('/mall-facility-inspection/b1f-b4f')} />
          </Card>
        </Col>

        {/* ── 整棟巡檢 ─────────────────────────────────────────────── */}
        <Col xs={24} lg={8}>
          <Card
            size="small" bordered={false}
            title={<GroupCardTitle icon={<BuildOutlined />} label="整棟巡檢" color="#1B3A5C" />}
            style={{ height: '100%' }}
          >
            <div style={{ padding: '8px 0', color: '#8c8c8c', fontSize: 12, marginBottom: 8 }}>
              整棟工務設施每日例行巡檢（RF / B4F / B2F / B1F）
            </div>
            <Divider style={{ margin: '8px 0' }} />
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              快速入口
            </Text>
            <QuickLink label="整棟巡檢 Dashboard" onClick={() => navigate('/full-building-inspection/dashboard')} />
            <QuickLink label="RF 巡檢"           onClick={() => navigate('/full-building-inspection/rf')} />
            <QuickLink label="B4F 巡檢"          onClick={() => navigate('/full-building-inspection/b4f')} />
            <QuickLink label="B2F 巡檢"          onClick={() => navigate('/full-building-inspection/b2f')} />
            <QuickLink label="B1F 巡檢"          onClick={() => navigate('/full-building-inspection/b1f')} />
          </Card>
        </Col>

        {/* ── 保全管理 ─────────────────────────────────────────────── */}
        <Col xs={24} lg={8}>
          <Card
            size="small" bordered={false}
            title={<GroupCardTitle icon={<SafetyOutlined />} label="保全管理" color="#722ed1" />}
            style={{ height: '100%' }}
          >
            {secData ? (
              <>
                {/* ── 一句話結論（P1-B）── */}
                <div style={{
                  background: secRate >= 80 && secData.abnormal_items_all === 0 ? '#f6ffed' : secData.abnormal_items_all > 0 && secRate < 50 ? '#fff1f0' : '#fffbe6',
                  borderLeft: `3px solid ${secRate >= 80 && secData.abnormal_items_all === 0 ? C.success : secData.abnormal_items_all > 0 && secRate < 50 ? C.danger : C.warning}`,
                  borderRadius: 4, padding: '4px 8px', marginBottom: 10,
                }}>
                  <Text style={{
                    fontSize: 11,
                    color: secRate >= 80 && secData.abnormal_items_all === 0 ? '#389e0d' : secData.abnormal_items_all > 0 && secRate < 50 ? C.danger : '#ad6800',
                  }}>
                    {secConclusion(secData, secRate)}
                  </Text>
                </div>

                {/* 整體完成率 */}
                <div style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <Text style={{ fontSize: 13 }}>今日巡檢完成率</Text>
                    <Text strong style={{ color: rateColor(secRate) }}>{secRate.toFixed(1)}%</Text>
                  </div>
                  <Progress
                    percent={secRate} showInfo={false}
                    strokeColor={rateColor(secRate)} size="small"
                  />
                  <div style={{ marginTop: 6 }}>
                    <Tag color="blue"    style={{ fontSize: 11 }}>場次 {secData.total_batches_all}</Tag>
                    <Tag color="error"   style={{ fontSize: 11 }}>異常 {secData.abnormal_items_all}</Tag>
                    <Tag color="default" style={{ fontSize: 11 }}>
                      未查 {secData.total_items_all - secData.checked_items_all}
                    </Tag>
                  </div>
                </div>

                {/* 有問題的 Sheet 列表（最多 3 筆） */}
                {secData.sheets
                  .filter(s => s.has_data && (s.abnormal_items > 0 || s.unchecked_items > 0))
                  .slice(0, 3)
                  .map(sheet => (
                    <div
                      key={sheet.sheet_key}
                      style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '4px 0', borderBottom: '1px solid #f0f0f0',
                      }}
                    >
                      <Text
                        ellipsis
                        style={{ fontSize: 11, maxWidth: 130 }}
                        title={sheet.sheet_name}
                      >
                        {sheet.sheet_name
                          .replace('保全巡檢 - ', '')
                          .replace('保全每日巡檢 - ', '')}
                      </Text>
                      <Space size={2}>
                        {sheet.abnormal_items > 0 && (
                          <Tag color="error"   style={{ fontSize: 10 }}>異{sheet.abnormal_items}</Tag>
                        )}
                        {sheet.unchecked_items > 0 && (
                          <Tag color="default" style={{ fontSize: 10 }}>未{sheet.unchecked_items}</Tag>
                        )}
                      </Space>
                    </div>
                  ))}

                <Divider style={{ margin: '8px 0' }} />
              </>
            ) : (
              <div style={{ padding: '8px 0', color: C.gray, fontSize: 12, marginBottom: 8 }}>
                <ExclamationCircleOutlined style={{ marginRight: 4 }} />保全資料未載入
              </div>
            )}
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
              快速入口
            </Text>
            <QuickLink label="保全 Dashboard" onClick={() => navigate('/security/dashboard')} />
            <QuickLink label="B1F~B4F 巡檢"  onClick={() => navigate('/security/patrol/b1f-b4f')} />
            <QuickLink label="1F~3F 巡檢"    onClick={() => navigate('/security/patrol/1f-3f')} />
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 3 — 系統資訊：近期同步紀錄（全寬）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Card
            size="small" bordered={false}
            title={
              <span>
                <SyncOutlined style={{ color: syncColor, marginRight: 6 }} />
                近期同步紀錄
              </span>
            }
            extra={
              sys?.last_sync_at ? (
                <Tooltip title={dayjs(sys.last_sync_at).format('YYYY-MM-DD HH:mm:ss')}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    最後同步：{dayjs(sys.last_sync_at).fromNow()}
                  </Text>
                </Tooltip>
              ) : null
            }
          >
            <Table
              size="small"
              dataSource={sys?.recent_syncs as SyncRecord[] ?? []}
              columns={syncColumns}
              rowKey="id"
              pagination={false}
              scroll={{ y: 200 }}
              locale={{ emptyText: '尚無同步紀錄' }}
            />
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 4 — 趨勢折線圖（三模組完成率，7D / 30D 切換）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Card
            size="small"
            bordered={false}
            title={
              <span style={{ color: C.primary, fontWeight: 700 }}>
                📈 完成率趨勢
              </span>
            }
            extra={
              <Space>
                <Button
                  size="small"
                  type={trendDays === 7 ? 'primary' : 'default'}
                  onClick={() => setTrendDays(7)}
                  style={{ fontSize: 12 }}
                >
                  近 7 日
                </Button>
                <Button
                  size="small"
                  type={trendDays === 30 ? 'primary' : 'default'}
                  onClick={() => setTrendDays(30)}
                  style={{ fontSize: 12 }}
                >
                  近 30 日
                </Button>
              </Space>
            }
          >
            {trendData && trendData.trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <LineChart
                  data={trendData.trend.map(p => ({
                    ...p,
                    dateLabel: p.date.slice(5),   // "MM/DD"
                    mall_completion:     p.mall_has_data     ? p.mall_completion     : null,
                    security_completion: p.security_has_data ? p.security_completion : null,
                    hotel_completion:    p.hotel_has_data    ? p.hotel_completion    : null,
                  }))}
                  margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="dateLabel" tick={{ fontSize: 11 }} />
                  <YAxis
                    domain={[0, 100]}
                    tickFormatter={(v: number) => `${v}%`}
                    tick={{ fontSize: 11 }}
                    width={40}
                  />
                  <RechartTooltip
                    formatter={(value: unknown, name: string) => {
                      if (value == null) return ['—', name]
                      const labels: Record<string, string> = {
                        mall_completion:     '商場巡檢',
                        security_completion: '保全巡檢',
                        hotel_completion:    '客房保養',
                      }
                      return [`${value}%`, labels[name] ?? name]
                    }}
                    labelFormatter={(l: string) => `日期：${l}`}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Legend
                    formatter={(value: string) => {
                      const labels: Record<string, string> = {
                        mall_completion:     '商場巡檢完成率',
                        security_completion: '保全巡檢完成率',
                        hotel_completion:    '客房保養完成率',
                      }
                      return <span style={{ fontSize: 12 }}>{labels[value] ?? value}</span>
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="mall_completion"
                    stroke={C.accent}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    connectNulls={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="security_completion"
                    stroke="#722ed1"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    connectNulls={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="hotel_completion"
                    stroke={C.primary}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 0', color: C.gray, fontSize: 13 }}>
                <ExclamationCircleOutlined style={{ marginRight: 6 }} />
                趨勢資料載入中…
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 5 — 結案率追蹤（異常 → 已處理 → 已結案）
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24}>
          <Card
            size="small"
            bordered={false}
            title={
              <span style={{ color: C.primary, fontWeight: 700 }}>
                🔒 結案率追蹤
              </span>
            }
            extra={
              <Text type="secondary" style={{ fontSize: 11 }}>
                異常件 → 已處理 → 已結案
              </Text>
            }
          >
            {closureData ? (
              <Row gutter={[16, 12]}>

                {/* 客房保養結案 */}
                <Col xs={24} sm={12} lg={6}>
                  <div style={{
                    padding: '12px 16px',
                    background: '#f6ffed',
                    borderRadius: 8,
                    borderLeft: `4px solid ${rateColor(closureData.hotel.closure_rate)}`,
                  }}>
                    <Text strong style={{ fontSize: 13, color: C.primary, display: 'block', marginBottom: 8 }}>
                      <BuildOutlined style={{ marginRight: 6 }} />客房保養
                    </Text>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>有異常</Text>
                      <Tag color="error" style={{ fontSize: 11 }}>{closureData.hotel.issue_count}</Tag>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>進行中</Text>
                      <Tag color="processing" style={{ fontSize: 11 }}>{closureData.hotel.in_progress}</Tag>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>已結案</Text>
                      <Tag color="success" style={{ fontSize: 11 }}>{closureData.hotel.closed}</Tag>
                    </div>
                    <Progress
                      percent={closureData.hotel.closure_rate}
                      strokeColor={rateColor(closureData.hotel.closure_rate)}
                      size="small"
                      format={p => <span style={{ fontSize: 11 }}>{p}%</span>}
                    />
                    <Text type="secondary" style={{ fontSize: 11 }}>結案率</Text>
                  </div>
                </Col>

                {/* 商場巡檢異常 */}
                <Col xs={24} sm={12} lg={6}>
                  <div style={{
                    padding: '12px 16px',
                    background: '#e6f4ff',
                    borderRadius: 8,
                    borderLeft: `4px solid ${C.accent}`,
                  }}>
                    <Text strong style={{ fontSize: 13, color: C.primary, display: 'block', marginBottom: 8 }}>
                      <ShopOutlined style={{ marginRight: 6 }} />商場巡檢
                    </Text>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>近 30 日異常</Text>
                      <Tag color="error" style={{ fontSize: 11 }}>
                        {closureData.mall_inspection.abnormal_count}
                      </Tag>
                    </div>
                    <div style={{ marginTop: 8, padding: '6px 0', borderTop: '1px solid #f0f0f0' }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {closureData.mall_inspection.note}
                      </Text>
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Button
                        size="small" type="link" style={{ padding: 0, fontSize: 11 }}
                        onClick={() => navigate('/approvals')}
                      >
                        前往簽核追蹤 →
                      </Button>
                    </div>
                  </div>
                </Col>

                {/* 保全巡檢異常 */}
                <Col xs={24} sm={12} lg={6}>
                  <div style={{
                    padding: '12px 16px',
                    background: '#f9f0ff',
                    borderRadius: 8,
                    borderLeft: `4px solid #722ed1`,
                  }}>
                    <Text strong style={{ fontSize: 13, color: C.primary, display: 'block', marginBottom: 8 }}>
                      <SafetyOutlined style={{ marginRight: 6 }} />保全巡檢
                    </Text>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>近 30 日異常</Text>
                      <Tag color="error" style={{ fontSize: 11 }}>
                        {closureData.security_inspection.abnormal_count}
                      </Tag>
                    </div>
                    <div style={{ marginTop: 8, padding: '6px 0', borderTop: '1px solid #f0f0f0' }}>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {closureData.security_inspection.note}
                      </Text>
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Button
                        size="small" type="link" style={{ padding: 0, fontSize: 11 }}
                        onClick={() => navigate('/approvals')}
                      >
                        前往簽核追蹤 →
                      </Button>
                    </div>
                  </div>
                </Col>

                {/* 簽核流程結案 */}
                <Col xs={24} sm={12} lg={6}>
                  <div style={{
                    padding: '12px 16px',
                    background: '#fff7e6',
                    borderRadius: 8,
                    borderLeft: `4px solid ${rateColor(closureData.approvals.closure_rate)}`,
                  }}>
                    <Text strong style={{ fontSize: 13, color: C.primary, display: 'block', marginBottom: 8 }}>
                      <CheckCircleOutlined style={{ marginRight: 6 }} />簽核流程
                    </Text>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>待審核</Text>
                      <Tag color="warning" style={{ fontSize: 11 }}>{closureData.approvals.pending}</Tag>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>已通過</Text>
                      <Tag color="success" style={{ fontSize: 11 }}>{closureData.approvals.approved}</Tag>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>已駁回</Text>
                      <Tag color="default" style={{ fontSize: 11 }}>{closureData.approvals.rejected}</Tag>
                    </div>
                    <Progress
                      percent={closureData.approvals.closure_rate}
                      strokeColor={rateColor(closureData.approvals.closure_rate)}
                      size="small"
                      format={p => <span style={{ fontSize: 11 }}>{p}%</span>}
                    />
                    <Text type="secondary" style={{ fontSize: 11 }}>結案率（已決議）</Text>
                  </div>
                </Col>

              </Row>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px 0', color: C.gray, fontSize: 13 }}>
                <ExclamationCircleOutlined style={{ marginRight: 6 }} />
                結案資料載入中…
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* ══════════════════════════════════════════════════════════════
          ROW 6 — 關聯圖譜 GraphView（全寬）
          各模組異常 / 待辦的 Hub-Spoke 視覺化，每 60 秒自動刷新
      ══════════════════════════════════════════════════════════════ */}
      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card
            size="small"
            bordered={false}
            title={
              <span style={{ color: C.primary, fontWeight: 700 }}>
                🔗 模組關聯圖譜
              </span>
            }
            extra={
              <Text type="secondary" style={{ fontSize: 11 }}>
                點擊節點進入模組 · 每 60 秒自動更新
              </Text>
            }
          >
            <GraphView refreshInterval={60_000} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
