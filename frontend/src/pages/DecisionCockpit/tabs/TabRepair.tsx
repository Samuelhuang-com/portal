/**
 * TAB D — 工務與報修
 * Phase 4：大直工務部 + 樂群工務報修 合併摘要 + 12 個月趨勢折線
 *
 * API:
 *   - /api/v1/dazhi-repair/dashboard
 *   - /api/v1/luqun-repair/dashboard
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Row, Spin, Alert, Tag, Typography, Divider,
  Statistic, Progress, Space,
} from 'antd'
import {
  CheckCircleOutlined, ClockCircleOutlined, WarningOutlined,
  DollarOutlined, ToolOutlined,
} from '@ant-design/icons'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartTooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { fetchDashboard as fetchDazhi } from '@/api/dazhiRepair'
import { fetchDashboard as fetchLuqun } from '@/api/luqunRepair'
import type { DashboardData as DazhiData } from '@/types/dazhiRepair'
import type { DashboardData as LuqunData } from '@/types/luqunRepair'
import {
  calcModuleHealth, calcRepairHealth, getTrafficLight,
  TRAFFIC_LIGHT_COLOR, TRAFFIC_LIGHT_LABEL, formatScore,
} from '../utils/healthScore'

const { Title, Text } = Typography

const T = {
  primary:   '#1B3A5C',
  accent:    '#4BA8E8',
  bg:        '#f0f4f8',
  textMuted: '#8c8c8c',
  success:   '#52c41a',
  warning:   '#faad14',
  danger:    '#ff4d4f',
}

interface TabRepairProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface RepairState {
  loading: boolean
  dazhi:   DazhiData | null
  luqun:   LuqunData | null
}

// ── KPI 格 ───────────────────────────────────────────────────────────────────
function KpiBox({ label, value, unit = '', color, icon }: {
  label: string; value: string | number; unit?: string
  color?: string; icon?: React.ReactNode
}) {
  return (
    <div style={{ textAlign: 'center', padding: '8px 4px' }}>
      <div style={{ fontSize: 10, color: T.textMuted, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: color ?? T.primary, lineHeight: 1 }}>
        {icon && <span style={{ marginRight: 3 }}>{icon}</span>}
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      {unit && <div style={{ fontSize: 10, color: T.textMuted }}>{unit}</div>}
    </div>
  )
}

// ── 單側工務摘要卡 ────────────────────────────────────────────────────────────
function RepairSideCard({
  title, color, data, loading,
}: {
  title: string; color: string; data: DazhiData | LuqunData | null; loading: boolean
}) {
  if (loading) return (
    <Card size="small" style={{ height: '100%', borderTop: `3px solid ${color}` }} bodyStyle={{ padding: 12 }}>
      <div style={{ textAlign: 'center', padding: 24 }}><Spin size="small" /></div>
    </Card>
  )

  const k = data?.kpi
  const rate = k && k.total > 0 ? Math.round((k.completed / k.total) * 100) : null
  const health = k ? calcModuleHealth({
    total:     k.total,
    completed: k.completed,
    overdue:   k.uncompleted,
    anomaly:   0,
  }) : null
  const light = getTrafficLight(health)
  const lColor = TRAFFIC_LIGHT_COLOR[light]

  // 12M 趨勢資料（月份點）
  const trend12m = (data as DazhiData | LuqunData | null)?.trend_12m ?? []
  const chartData = trend12m.map(pt => ({
    label:     pt.label,
    total:     pt.total,
    completed: pt.completed,
    rate:      pt.total > 0 ? Math.round((pt.completed / pt.total) * 100) : 0,
  }))

  return (
    <Card size="small" style={{ height: '100%', borderTop: `3px solid ${color}` }} bodyStyle={{ padding: 12 }}>
      {/* 標題列 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <Text strong style={{ fontSize: 14, color: T.primary }}>
          <ToolOutlined style={{ marginRight: 6, color }} />{title}
        </Text>
        <Space>
          <div style={{
            width: 44, height: 44, borderRadius: '50%',
            border: `3px solid ${lColor}`, background: `${lColor}18`,
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: lColor, lineHeight: 1 }}>{formatScore(health)}</span>
          </div>
          <Tag color={light === 'gray' ? 'default' : light === 'green' ? 'success' : light === 'yellow' ? 'warning' : 'error'}>
            {TRAFFIC_LIGHT_LABEL[light]}
          </Tag>
        </Space>
      </div>

      {!k ? (
        <div style={{ textAlign: 'center', padding: 16, color: T.textMuted, fontSize: 12 }}>資料準備中</div>
      ) : (
        <>
          {/* 完成率進度條 */}
          <div style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
              <Text type="secondary">本月完成率</Text>
              <Text strong style={{ color: lColor }}>{rate ?? '—'}%</Text>
            </div>
            <Progress percent={rate ?? 0} strokeColor={lColor} showInfo={false} size="small" />
          </div>

          {/* KPI 格 4×1 */}
          <Row gutter={[4, 0]}>
            <Col span={6}><KpiBox label="總件數" value={k.total} /></Col>
            <Col span={6}><KpiBox label="已完成" value={k.completed} color={T.success} icon={<CheckCircleOutlined />} /></Col>
            <Col span={6}><KpiBox label="未完成" value={k.uncompleted} color={k.uncompleted > 5 ? T.danger : T.warning} icon={<ClockCircleOutlined />} /></Col>
            <Col span={6}><KpiBox label="待驗收" value={k.pending_verify} color={k.pending_verify > 0 ? T.warning : T.textMuted} /></Col>
          </Row>

          <Divider style={{ margin: '8px 0' }} />

          {/* 費用 */}
          <Row gutter={4}>
            <Col span={12}>
              <KpiBox label="本月費用" value={`NT$ ${k.month_total_fee.toLocaleString()}`} unit="" color={T.primary} icon={<DollarOutlined />} />
            </Col>
            <Col span={12}>
              <KpiBox label="年度費用" value={`NT$ ${k.annual_fee.toLocaleString()}`} unit="" color={T.textMuted} />
            </Col>
          </Row>

          {/* 12 個月完成率趨勢 */}
          {chartData.length > 0 && (
            <>
              <Divider style={{ margin: '8px 0' }} />
              <div style={{ fontSize: 11, color: T.textMuted, marginBottom: 4 }}>近 12 個月完成率趨勢</div>
              <ResponsiveContainer width="100%" height={100}>
                <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="label" tick={{ fontSize: 9 }} />
                  <YAxis tick={{ fontSize: 9 }} domain={[0, 100]} unit="%" />
                  <RechartTooltip
                    formatter={(val: number) => [`${val}%`, '完成率']}
                    labelStyle={{ fontSize: 11 }}
                    contentStyle={{ fontSize: 11 }}
                  />
                  <Line
                    type="monotone" dataKey="rate" stroke={color}
                    strokeWidth={2} dot={false} name="完成率"
                  />
                </LineChart>
              </ResponsiveContainer>
            </>
          )}
        </>
      )}
    </Card>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// 主元件
// ════════════════════════════════════════════════════════════════════════════
export default function TabRepair({ year, month, monthStr, refreshKey }: TabRepairProps) {
  const [st, setSt] = useState<RepairState>({ loading: true, dazhi: null, luqun: null })

  const load = useCallback(async () => {
    setSt(s => ({ ...s, loading: true }))
    const [r1, r2] = await Promise.allSettled([fetchDazhi(year, month), fetchLuqun(year, month)])
    setSt({
      loading: false,
      dazhi:   r1.status === 'fulfilled' ? r1.value : null,
      luqun:   r2.status === 'fulfilled' ? r2.value : null,
    })
  }, [year, month, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const { loading, dazhi, luqun } = st

  const dazhiHealth = dazhi ? calcModuleHealth({ total: dazhi.kpi.total, completed: dazhi.kpi.completed, overdue: dazhi.kpi.uncompleted, anomaly: 0 }) : null
  const luqunHealth = luqun ? calcModuleHealth({ total: luqun.kpi.total, completed: luqun.kpi.completed, overdue: luqun.kpi.uncompleted, anomaly: 0 }) : null
  const { score: repairHealth, partial } = calcRepairHealth(dazhiHealth, luqunHealth)
  const light  = getTrafficLight(repairHealth)
  const lColor = TRAFFIC_LIGHT_COLOR[light]

  // 合計 KPI
  const totalCases = (dazhi?.kpi.total ?? 0) + (luqun?.kpi.total ?? 0)
  const totalComp  = (dazhi?.kpi.completed ?? 0) + (luqun?.kpi.completed ?? 0)
  const totalFee   = (dazhi?.kpi.month_total_fee ?? 0) + (luqun?.kpi.month_total_fee ?? 0)

  return (
    <div style={{ paddingBottom: 24 }}>

      {/* ── 工務整體健康分數 ─────────────────────────────────────────────── */}
      <Card style={{ marginBottom: 16, borderRadius: 8 }} bodyStyle={{ padding: '14px 24px' }}>
        <Row align="middle" gutter={24}>
          <Col>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: 80, height: 80, borderRadius: '50%',
                border: `5px solid ${lColor}`, background: `${lColor}18`,
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', margin: '0 auto',
              }}>
                <span style={{ fontSize: 22, fontWeight: 700, color: lColor, lineHeight: 1 }}>{formatScore(repairHealth)}</span>
                {repairHealth !== null && <span style={{ fontSize: 10, color: lColor, opacity: 0.8 }}>/100</span>}
              </div>
              <div style={{ marginTop: 4, fontSize: 11, color: T.primary, fontWeight: 600 }}>工務維護健康</div>
              <Tag color={light === 'gray' ? 'default' : light === 'green' ? 'success' : light === 'yellow' ? 'warning' : 'error'} style={{ marginTop: 2 }}>
                {TRAFFIC_LIGHT_LABEL[light]}
              </Tag>
              {partial && <div style={{ fontSize: 10, color: T.textMuted }}>部分計算</div>}
            </div>
          </Col>
          <Col flex={1}>
            <Title level={5} style={{ margin: '0 0 2px', color: T.primary }}>
              D. 工務與報修 — {monthStr}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              大直工務部（60%）+ 樂群工務報修（40%）加權平均
            </Text>
            <Row gutter={[16, 0]} style={{ marginTop: 8 }}>
              <Col><Statistic title="合計件數" value={totalCases} valueStyle={{ fontSize: 18, color: T.primary }} /></Col>
              <Col><Statistic title="合計完成" value={totalComp}  valueStyle={{ fontSize: 18, color: T.success }} /></Col>
              <Col><Statistic title="本月費用" value={`NT$ ${totalFee.toLocaleString()}`} valueStyle={{ fontSize: 18 }} /></Col>
            </Row>
          </Col>
        </Row>
      </Card>

      {/* ── 左右雙欄：大直 | 樂群 ──────────────────────────────────────── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <RepairSideCard title="大直工務部" color="#1B3A5C" data={dazhi} loading={loading} />
        </Col>
        <Col xs={24} lg={12}>
          <RepairSideCard title="樂群工務報修" color="#4BA8E8" data={luqun} loading={loading} />
        </Col>
      </Row>
    </div>
  )
}
