/**
 * TAB A — 決策總覽
 *
 * Phase 2 實作內容：
 *   ① 集團健康分數（大圓）+ 飯店 / 商場 / 工務 三格子分數
 *   ② KPI 彙整列（總件數 / 已完成 / 未完成 / 待驗 / 本月費用）
 *   ③ 主管最該注意的 5 件事（規則式，無 AI）
 *
 * Phase 2 資料來源（全部 reuse 既有 API）：
 *   - /api/v1/dashboard/kpi        → 客房保養 KPI（有 completion_rate）
 *   - /api/v1/luqun-repair/dashboard → 樂群工務（total / completed / uncompleted）
 *   - /api/v1/dazhi-repair/dashboard → 大直工務（total / completed / uncompleted）
 *
 * 飯店完整健康 / 商場健康 → Phase 3（需 6 來源 + 5 工項 API）先顯示灰燈
 * 集團健康分數 → 工務健康已有，飯店 / 商場缺資料時標示「部分計算」
 */

import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Row, Spin, Statistic, Tag, Tooltip,
  Typography, Divider, Alert, Space, Badge,
} from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { dashboardApi }     from '@/api/dashboard'
import { fetchDashboard as fetchLuqun } from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhi } from '@/api/dazhiRepair'
import type { DashboardData as LuqunData } from '@/types/luqunRepair'
import type { DashboardData as DazhiData  } from '@/types/dazhiRepair'
import type { DashboardKPI }               from '@/api/dashboard'
import {
  calcModuleHealth,
  calcRepairHealth,
  calcGroupHealth,
  getTrafficLight,
  TRAFFIC_LIGHT_COLOR,
  TRAFFIC_LIGHT_LABEL,
  formatScore,
  type TrafficLight,
} from '../utils/healthScore'

const { Title, Text } = Typography

// ── 顏色 Token ───────────────────────────────────────────────────────────────
const T = {
  primary:   '#1B3A5C',
  accent:    '#4BA8E8',
  bg:        '#f0f4f8',
  cardBg:    '#ffffff',
  textMuted: '#8c8c8c',
  success:   '#52c41a',
  warning:   '#faad14',
  danger:    '#ff4d4f',
}

// ── Props ─────────────────────────────────────────────────────────────────────
interface TabOverviewProps {
  year:       number
  month:      number
  monthStr:   string
  refreshKey: number
}

// ── 聚合後的頁面資料型別 ──────────────────────────────────────────────────────
interface OverviewState {
  loading:   boolean
  error:     string | null
  luqun:     LuqunData | null
  dazhi:     DazhiData  | null
  dashKpi:   DashboardKPI | null
}

// ── 主管注意事項（規則式生成）────────────────────────────────────────────────
interface AlertItem {
  level:   'error' | 'warning' | 'info'
  icon:    React.ReactNode
  title:   string
  desc:    string
}

function buildAlerts(
  luqun:   LuqunData | null,
  dazhi:   DazhiData  | null,
  dashKpi: DashboardKPI | null,
): AlertItem[] {
  const alerts: AlertItem[] = []

  // 1. 工務逾期未完成件數
  const luqunUncomp = luqun?.kpi.uncompleted ?? 0
  const dazhiUncomp = dazhi?.kpi.uncompleted ?? 0
  const totalUncomp = luqunUncomp + dazhiUncomp
  if (totalUncomp > 0) {
    alerts.push({
      level: totalUncomp >= 10 ? 'error' : 'warning',
      icon:  <WarningOutlined />,
      title: `工務未完成報修 ${totalUncomp} 件`,
      desc:  `樂群 ${luqunUncomp} 件 · 大直 ${dazhiUncomp} 件，請確認處理進度`,
    })
  }

  // 2. 待驗件數
  const luqunPending = luqun?.kpi.pending_verify ?? 0
  const dazhiPending = dazhi?.kpi.pending_verify ?? 0
  const totalPending = luqunPending + dazhiPending
  if (totalPending > 0) {
    alerts.push({
      level: 'warning',
      icon:  <ClockCircleOutlined />,
      title: `待辦驗件 ${totalPending} 件尚未驗收`,
      desc:  `樂群 ${luqunPending} 件 · 大直 ${dazhiPending} 件，請安排驗收`,
    })
  }

  // 3. 客房保養未完成
  const roomIncomplete = dashKpi?.room_maintenance.total_incomplete ?? 0
  const roomTotal      = dashKpi?.room_maintenance.total ?? 0
  if (roomIncomplete > 0 && roomTotal > 0) {
    const rate = Math.round((roomIncomplete / roomTotal) * 100)
    alerts.push({
      level: rate >= 30 ? 'error' : 'warning',
      icon:  <ExclamationCircleOutlined />,
      title: `客房保養未完成 ${roomIncomplete} 項（${rate}%）`,
      desc:  `共 ${roomTotal} 筆保養工項，${roomIncomplete} 筆尚未完成，請關注重點房型`,
    })
  }

  // 4. 本月工務費用彙整提示
  const luqunFee = luqun?.kpi.month_total_fee ?? 0
  const dazhiFee = dazhi?.kpi.month_total_fee ?? 0
  const totalFee = luqunFee + dazhiFee
  if (totalFee > 0) {
    alerts.push({
      level: 'info',
      icon:  <InfoCircleOutlined />,
      title: `本月工務費用合計 NT$ ${totalFee.toLocaleString()}`,
      desc:  `樂群 NT$ ${luqunFee.toLocaleString()} · 大直 NT$ ${dazhiFee.toLocaleString()}`,
    })
  }

  // 5. 資料來源狀態提示（飯店/商場健康分數 Phase 3）
  alerts.push({
    level: 'info',
    icon:  <InfoCircleOutlined />,
    title: '飯店管理 & 商場管理健康分數尚在建置中',
    desc:  '完整 6 來源 / 5 工項健康分數將於 Phase 3 接入，目前僅顯示工務健康與客房保養',
  })

  // 最多回傳 5 條，依嚴重程度排序
  const order = { error: 0, warning: 1, info: 2 }
  return alerts.sort((a, b) => order[a.level] - order[b.level]).slice(0, 5)
}

// ── 健康分數大圓 ─────────────────────────────────────────────────────────────
function ScoreCircle({
  score, light, label, size = 'large', partial = false,
}: {
  score:   number | null
  light:   TrafficLight
  label:   string
  size?:   'large' | 'small'
  partial?: boolean
}) {
  const color   = TRAFFIC_LIGHT_COLOR[light]
  const isLarge = size === 'large'
  const dim     = isLarge ? 120 : 80
  const font    = isLarge ? 32 : 20
  const subFont = isLarge ? 13 : 11

  return (
    <div style={{ textAlign: 'center' }}>
      <div
        style={{
          width:        dim,
          height:       dim,
          borderRadius: '50%',
          border:       `${isLarge ? 6 : 4}px solid ${color}`,
          display:      'flex',
          flexDirection: 'column',
          alignItems:   'center',
          justifyContent: 'center',
          margin:       '0 auto',
          background:   `${color}18`,
          position:     'relative',
        }}
      >
        <span style={{ fontSize: font, fontWeight: 700, color, lineHeight: 1 }}>
          {formatScore(score)}
        </span>
        {score !== null && (
          <span style={{ fontSize: subFont, color, opacity: 0.8 }}>/ 100</span>
        )}
      </div>

      <div style={{ marginTop: 8, fontSize: isLarge ? 14 : 12, color: T.primary, fontWeight: 600 }}>
        {label}
      </div>
      <div style={{ marginTop: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
        <Badge color={color} />
        <Text style={{ fontSize: 12, color }}>
          {TRAFFIC_LIGHT_LABEL[light]}
        </Text>
        {partial && (
          <Tooltip title="部分來源尚未接入，分數為現有資料估算">
            <InfoCircleOutlined style={{ fontSize: 11, color: T.textMuted }} />
          </Tooltip>
        )}
      </div>
    </div>
  )
}

// ── KPI 彙整卡 ────────────────────────────────────────────────────────────────
function KpiCard({
  title, value, unit = '件', color, icon, tooltip,
}: {
  title:    string
  value:    number | string
  unit?:    string
  color?:   string
  icon?:    React.ReactNode
  tooltip?: string
}) {
  const content = (
    <Card size="small" style={{ background: T.bg, border: 'none', textAlign: 'center' }}>
      <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color: color ?? T.primary, lineHeight: 1 }}>
        {icon && <span style={{ marginRight: 4 }}>{icon}</span>}
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      <div style={{ fontSize: 11, color: T.textMuted, marginTop: 2 }}>{unit}</div>
    </Card>
  )
  return tooltip ? <Tooltip title={tooltip}>{content}</Tooltip> : content
}

// ════════════════════════════════════════════════════════════════════════════
// 主元件
// ════════════════════════════════════════════════════════════════════════════
export default function TabOverview({ year, month, monthStr, refreshKey }: TabOverviewProps) {
  const [state, setState] = useState<OverviewState>({
    loading: true, error: null, luqun: null, dazhi: null, dashKpi: null,
  })

  const load = useCallback(async () => {
    setState(s => ({ ...s, loading: true, error: null }))
    try {
      const [luqunRes, dazhiRes, kpiRes] = await Promise.allSettled([
        fetchLuqun(year, month),
        fetchDazhi(year, month),
        dashboardApi.kpi(),
      ])

      setState({
        loading:  false,
        error:    null,
        luqun:    luqunRes.status  === 'fulfilled' ? luqunRes.value          : null,
        dazhi:    dazhiRes.status  === 'fulfilled' ? dazhiRes.value          : null,
        dashKpi:  kpiRes.status    === 'fulfilled' ? kpiRes.value.data       : null,
      })
    } catch (e) {
      setState(s => ({ ...s, loading: false, error: String(e) }))
    }
  }, [year, month, refreshKey])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const { loading, error, luqun, dazhi, dashKpi } = state

  // ── 健康分數計算 ─────────────────────────────────────────────────────────
  const luqunHealth = luqun
    ? calcModuleHealth({
        total:     luqun.kpi.total,
        completed: luqun.kpi.completed,
        overdue:   luqun.kpi.uncompleted,
        anomaly:   0,
      })
    : null

  const dazhiHealth = dazhi
    ? calcModuleHealth({
        total:     dazhi.kpi.total,
        completed: dazhi.kpi.completed,
        overdue:   dazhi.kpi.uncompleted,
        anomaly:   0,
      })
    : null

  const { score: repairHealth, partial: repairPartial } = calcRepairHealth(dazhiHealth, luqunHealth)

  // 飯店：僅用客房保養 completion_rate 作為 Phase 2 代理（Phase 3 接入 6 來源）
  const roomRate   = dashKpi?.room_maintenance.completion_rate ?? null
  const hotelProxy = roomRate !== null
    ? calcModuleHealth({
        total:     dashKpi!.room_maintenance.total,
        completed: dashKpi!.room_maintenance.completed,
        overdue:   dashKpi!.room_maintenance.total_incomplete,
        anomaly:   0,
      })
    : null

  // 商場：Phase 3 再接入（目前灰燈）
  const mallHealth: number | null = null

  const { score: groupHealth, partial: groupPartial } = calcGroupHealth(
    hotelProxy, mallHealth, repairHealth,
  )

  // ── 燈號 ────────────────────────────────────────────────────────────────
  const groupLight  = getTrafficLight(groupHealth)
  const hotelLight  = getTrafficLight(hotelProxy)
  const mallLight   = getTrafficLight(mallHealth)    // gray
  const repairLight = getTrafficLight(repairHealth)

  // ── KPI 彙整 ─────────────────────────────────────────────────────────────
  const luqunTotal   = luqun?.kpi.total      ?? 0
  const dazhiTotal   = dazhi?.kpi.total      ?? 0
  const luqunComp    = luqun?.kpi.completed  ?? 0
  const dazhiComp    = dazhi?.kpi.completed  ?? 0
  const luqunUncomp  = luqun?.kpi.uncompleted ?? 0
  const dazhiUncomp  = dazhi?.kpi.uncompleted ?? 0
  const luqunPend    = luqun?.kpi.pending_verify ?? 0
  const dazhiPend    = dazhi?.kpi.pending_verify ?? 0
  const luqunFee     = luqun?.kpi.month_total_fee ?? 0
  const dazhiFee     = dazhi?.kpi.month_total_fee ?? 0

  const kpiTotal    = luqunTotal  + dazhiTotal
  const kpiComp     = luqunComp   + dazhiComp
  const kpiUncomp   = luqunUncomp + dazhiUncomp
  const kpiPend     = luqunPend   + dazhiPend
  const kpiFee      = luqunFee    + dazhiFee

  const overallCompRate = kpiTotal > 0 ? Math.round((kpiComp / kpiTotal) * 100) : null

  // ── 主管注意事項 ─────────────────────────────────────────────────────────
  const alerts = buildAlerts(luqun, dazhi, dashKpi)

  // ── 渲染 ─────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '80px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16, color: T.textMuted }}>載入決策總覽資料...</div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="資料載入失敗"
        description={error}
        style={{ margin: '24px 0' }}
        showIcon
      />
    )
  }

  return (
    <div style={{ paddingBottom: 24 }}>

      {/* ── ① 健康分數矩陣 ───────────────────────────────────────────────── */}
      <Card
        style={{ marginBottom: 16, borderRadius: 8 }}
        bodyStyle={{ padding: '20px 24px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={5} style={{ margin: 0, color: T.primary }}>
            集團健康分數矩陣
          </Title>
          <Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              查詢期間：{monthStr}
            </Text>
            {groupPartial && (
              <Tag icon={<InfoCircleOutlined />} color="default">
                部分計算（飯店 / 商場 Phase 3 接入）
              </Tag>
            )}
          </Space>
        </div>

        <Row gutter={[24, 24]} align="middle" justify="center">
          {/* 集團整體（大圓）*/}
          <Col xs={24} sm={6} style={{ textAlign: 'center' }}>
            <ScoreCircle
              score={groupHealth}
              light={groupLight}
              label="集團整體健康"
              size="large"
              partial={groupPartial}
            />
          </Col>

          <Col xs={0} sm={1}>
            <Divider type="vertical" style={{ height: 100 }} />
          </Col>

          {/* 三個子分數 */}
          <Col xs={24} sm={17}>
            <Row gutter={[16, 16]} justify="space-around">
              <Col xs={8}>
                <ScoreCircle
                  score={hotelProxy}
                  light={hotelLight}
                  label="飯店管理"
                  size="small"
                  partial={hotelProxy !== null}
                />
                <div style={{ textAlign: 'center', marginTop: 4, fontSize: 11, color: T.textMuted }}>
                  (僅客房保養，Phase 3 完整接入)
                </div>
              </Col>
              <Col xs={8}>
                <ScoreCircle
                  score={mallHealth}
                  light={mallLight}
                  label="商場管理"
                  size="small"
                />
                <div style={{ textAlign: 'center', marginTop: 4, fontSize: 11, color: T.textMuted }}>
                  (Phase 3 接入)
                </div>
              </Col>
              <Col xs={8}>
                <ScoreCircle
                  score={repairHealth}
                  light={repairLight}
                  label="工務維護"
                  size="small"
                  partial={repairPartial}
                />
                <div style={{ textAlign: 'center', marginTop: 4, fontSize: 11, color: T.textMuted }}>
                  (大直 60% + 樂群 40%)
                </div>
              </Col>
            </Row>
          </Col>
        </Row>
      </Card>

      {/* ── ② KPI 彙整列 ────────────────────────────────────────────────── */}
      <Card
        style={{ marginBottom: 16, borderRadius: 8 }}
        bodyStyle={{ padding: '16px 24px' }}
      >
        <Title level={5} style={{ margin: '0 0 12px', color: T.primary }}>
          工務 KPI 彙整（{monthStr}）
        </Title>
        <Row gutter={[12, 12]}>
          <Col xs={12} sm={4}>
            <KpiCard
              title="工務總件數"
              value={kpiTotal}
              tooltip="樂群 + 大直 本月總報修件數"
            />
          </Col>
          <Col xs={12} sm={4}>
            <KpiCard
              title="已完成"
              value={kpiComp}
              color={T.success}
              icon={<CheckCircleOutlined />}
              tooltip="本月已完成結案件數"
            />
          </Col>
          <Col xs={12} sm={4}>
            <KpiCard
              title="未完成"
              value={kpiUncomp}
              color={kpiUncomp > 5 ? T.danger : T.warning}
              icon={<ClockCircleOutlined />}
              tooltip="本月尚未完成件數（含逾期）"
            />
          </Col>
          <Col xs={12} sm={4}>
            <KpiCard
              title="待驗收"
              value={kpiPend}
              color={kpiPend > 0 ? T.warning : T.textMuted}
              icon={<SyncOutlined />}
              tooltip="已完工待驗收確認件數"
            />
          </Col>
          <Col xs={12} sm={4}>
            <KpiCard
              title="完成率"
              value={overallCompRate !== null ? `${overallCompRate}%` : '—'}
              unit=""
              color={
                overallCompRate === null ? T.textMuted
                : overallCompRate >= 80  ? T.success
                : overallCompRate >= 60  ? T.warning
                : T.danger
              }
              tooltip="本月完成件數 / 總件數"
            />
          </Col>
          <Col xs={12} sm={4}>
            <KpiCard
              title="本月費用"
              value={`NT$ ${kpiFee.toLocaleString()}`}
              unit=""
              tooltip="工務報修本月費用（外包 + 維修）"
            />
          </Col>
        </Row>

        {/* 客房保養 KPI 補充列 */}
        {dashKpi && (
          <>
            <Divider style={{ margin: '12px 0 8px' }} />
            <Row gutter={[12, 12]}>
              <Col xs={12} sm={4}>
                <KpiCard
                  title="客房保養總項"
                  value={dashKpi.room_maintenance.total}
                  tooltip="本期客房保養工項總計"
                />
              </Col>
              <Col xs={12} sm={4}>
                <KpiCard
                  title="保養已完成"
                  value={dashKpi.room_maintenance.completed}
                  color={T.success}
                  icon={<CheckCircleOutlined />}
                />
              </Col>
              <Col xs={12} sm={4}>
                <KpiCard
                  title="保養未完成"
                  value={dashKpi.room_maintenance.total_incomplete}
                  color={dashKpi.room_maintenance.total_incomplete > 0 ? T.warning : T.textMuted}
                  icon={<ExclamationCircleOutlined />}
                />
              </Col>
              <Col xs={12} sm={4}>
                <KpiCard
                  title="保養完成率"
                  value={`${Math.round(dashKpi.room_maintenance.completion_rate)}%`}
                  unit=""
                  color={
                    dashKpi.room_maintenance.completion_rate >= 80 ? T.success
                    : dashKpi.room_maintenance.completion_rate >= 60 ? T.warning
                    : T.danger
                  }
                />
              </Col>
            </Row>
          </>
        )}
      </Card>

      {/* ── ③ 主管最該注意的 5 件事 ────────────────────────────────────── */}
      <Card
        style={{ borderRadius: 8 }}
        bodyStyle={{ padding: '16px 24px' }}
      >
        <Title level={5} style={{ margin: '0 0 12px', color: T.primary }}>
          主管最該注意的 5 件事
        </Title>
        {alerts.length === 0 ? (
          <Alert
            type="success"
            icon={<CheckCircleOutlined />}
            showIcon
            message="本月各項指標均在正常範圍，無需特別關注"
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {alerts.map((a, i) => (
              <Alert
                key={i}
                type={a.level}
                icon={a.icon}
                showIcon
                message={
                  <Space>
                    <Text strong style={{ fontSize: 13 }}>
                      {i + 1}. {a.title}
                    </Text>
                  </Space>
                }
                description={
                  <Text type="secondary" style={{ fontSize: 12 }}>{a.desc}</Text>
                }
              />
            ))}
          </div>
        )}
      </Card>

    </div>
  )
}
