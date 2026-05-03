/**
 * TAB B — 飯店管理摘要
 * Phase 3：6 來源精華整合
 *
 * 來源                    API
 * 1. 客房保養管理          /room-maintenance-detail/maintenance-stats
 * 2. 飯店週期保養          /periodic-maintenance/stats
 * 3. IHG 客房保養          /ihg-room-maintenance/stats
 * 4. 飯店每日巡檢          /hotel-daily-inspection/dashboard/monthly-summary
 * 5. 保全巡檢              /security/dashboard/monthly-summary
 * 6. 大直工務部            /dazhi-repair/dashboard
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Progress, Row, Spin, Alert, Tag, Typography,
  Statistic, Divider, Space, Tooltip,
} from 'antd'
import {
  CheckCircleOutlined, ExclamationCircleOutlined, InfoCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { fetchMaintenanceStats }           from '@/api/roomMaintenanceDetail'
import { fetchPMStats }                    from '@/api/periodicMaintenance'
import { fetchIHGStats }                   from '@/api/ihgRoomMaintenance'
import { fetchHotelDailyMonthlyDashboard } from '@/api/hotelDailyInspection'
import { fetchSecurityMonthlyDashboard }   from '@/api/securityPatrol'
import { fetchDashboard as fetchDazhi }    from '@/api/dazhiRepair'
import type { MaintenanceStatsResponse }   from '@/types/roomMaintenanceDetail'
import type { PMStats }                    from '@/types/periodicMaintenance'
import type { IHGStats }                   from '@/types/ihgRoomMaintenance'
import type { HotelDIMonthlyDashboard }    from '@/api/hotelDailyInspection'
import type { SecurityMonthlyDashboard }   from '@/api/securityPatrol'
import type { DashboardData as DazhiData } from '@/types/dazhiRepair'
import {
  calcModuleHealth, calcGroupHealth, getTrafficLight,
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

interface TabHotelProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface HotelSourceState {
  loading:  boolean
  roomStat: MaintenanceStatsResponse | null
  pmStat:   PMStats | null
  ihgStat:  IHGStats | null
  hotelDI:  HotelDIMonthlyDashboard | null
  security: SecurityMonthlyDashboard | null
  dazhi:    DazhiData | null
}

// ── 來源卡定義 ────────────────────────────────────────────────────────────────
interface SourceDef {
  key:   string
  title: string
  color: string
  getMetrics: (s: HotelSourceState) => {
    total:      number | null
    completed:  number | null
    overdue:    number | null
    abnormal:   number | null
    compRate:   number | null
    extra?:     Array<{ label: string; value: string }>
  }
}

const SOURCES: SourceDef[] = [
  {
    key: 'room', title: '客房保養管理', color: '#1B3A5C',
    getMetrics: (s) => {
      if (!s.roomStat) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
      const k = s.roomStat.kpi
      return {
        total:     null,
        completed: null,
        overdue:   k.consecutive_missed_rooms,
        abnormal:  null,
        compRate:  k.current_month_completion_rate,
        extra: [
          { label: '連續未保養房間', value: `${k.consecutive_missed_rooms} 間` },
          { label: '完全正常房間',   value: `${k.fully_ok_rooms} 間` },
          { label: '12M 平均完成率', value: `${Math.round(k.avg_completion_rate_12m)}%` },
        ],
      }
    },
  },
  {
    key: 'pm', title: '飯店週期保養', color: '#4BA8E8',
    getMetrics: (s) => {
      if (!s.pmStat?.current_kpi) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
      const k = s.pmStat.current_kpi
      return {
        total:     k.total,
        completed: k.completed,
        overdue:   k.overdue,
        abnormal:  k.abnormal,
        compRate:  k.completion_rate,
        extra: [
          { label: '預估工時', value: `${Math.round(k.planned_minutes / 60)} hr` },
          { label: '實際工時', value: `${Math.round(k.actual_minutes  / 60)} hr` },
        ],
      }
    },
  },
  {
    key: 'ihg', title: 'IHG 客房保養', color: '#722ed1',
    getMetrics: (s) => {
      if (!s.ihgStat) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
      const k = s.ihgStat
      return {
        total:     k.total_scheduled,
        completed: k.completed,
        overdue:   null,
        abnormal:  k.abnormal,
        compRate:  k.completion_rate,
        extra: [
          { label: '工時合計', value: `${k.work_hours.toFixed(1)} hr` },
          { label: '異常房間', value: `${k.abnormal} 間` },
        ],
      }
    },
  },
  {
    key: 'hotelDI', title: '飯店每日巡檢', color: '#13c2c2',
    getMetrics: (s) => {
      if (!s.hotelDI) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
      const k = s.hotelDI
      return {
        total:     k.total_items,
        completed: k.checked_items,
        overdue:   null,
        abnormal:  k.abnormal_items,
        compRate:  k.completion_rate,
        extra: [
          { label: '工時合計',  value: `${Math.round(k.total_minutes / 60)} hr` },
          { label: '異常項目', value: `${k.abnormal_items} 項` },
        ],
      }
    },
  },
  {
    key: 'security', title: '保全巡檢', color: '#fa8c16',
    getMetrics: (s) => {
      if (!s.security) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
      const k = s.security
      return {
        total:     k.total_items,
        completed: k.checked_items,
        overdue:   null,
        abnormal:  k.abnormal_items,
        compRate:  k.completion_rate,
        extra: [
          { label: '工時合計',  value: `${Math.round(k.total_minutes / 60)} hr` },
          { label: '異常項目', value: `${k.abnormal_items} 項` },
        ],
      }
    },
  },
  {
    key: 'dazhi', title: '大直工務部', color: '#52c41a',
    getMetrics: (s) => {
      if (!s.dazhi) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
      const k = s.dazhi.kpi
      const rate = k.total > 0 ? Math.round((k.completed / k.total) * 100) : null
      return {
        total:     k.total,
        completed: k.completed,
        overdue:   k.uncompleted,
        abnormal:  0,
        compRate:  rate,
        extra: [
          { label: '待驗收', value: `${k.pending_verify} 件` },
          { label: '本月費用', value: `NT$ ${k.month_total_fee.toLocaleString()}` },
        ],
      }
    },
  },
]

// ── 單張來源卡 ────────────────────────────────────────────────────────────────
function SourceCard({
  def, state, loading,
}: { def: SourceDef; state: HotelSourceState; loading: boolean }) {
  const m = def.getMetrics(state)
  const noData = m.compRate === null
  const health = noData ? null : calcModuleHealth({
    total:     m.total     ?? 100,
    completed: m.completed ?? Math.round((m.compRate! / 100) * 100),
    overdue:   m.overdue   ?? 0,
    anomaly:   m.abnormal  ?? 0,
  })
  const light = getTrafficLight(health)
  const color = TRAFFIC_LIGHT_COLOR[light]

  return (
    <Card
      size="small"
      style={{ height: '100%', borderTop: `3px solid ${def.color}` }}
      bodyStyle={{ padding: 12 }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <Text strong style={{ fontSize: 13, color: T.primary }}>{def.title}</Text>
        <Tag color={light === 'gray' ? 'default' : light === 'green' ? 'success' : light === 'yellow' ? 'warning' : 'error'}
          style={{ fontSize: 11, margin: 0 }}>
          {TRAFFIC_LIGHT_LABEL[light]}
        </Tag>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '16px 0' }}><Spin size="small" /></div>
      ) : noData ? (
        <div style={{ textAlign: 'center', padding: '12px 0', color: T.textMuted, fontSize: 12 }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />資料準備中
        </div>
      ) : (
        <>
          {/* 完成率進度條 */}
          <div style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
              <Text type="secondary">完成率</Text>
              <Text strong style={{ color }}>{m.compRate}%</Text>
            </div>
            <Progress
              percent={m.compRate ?? 0}
              strokeColor={color}
              showInfo={false}
              size="small"
            />
          </div>

          {/* 健康分數 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>健康分數</Text>
            <Text strong style={{ fontSize: 16, color }}>{formatScore(health)}</Text>
          </div>

          {/* 次要指標 */}
          {m.extra && (
            <>
              <Divider style={{ margin: '6px 0' }} />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 12px' }}>
                {m.extra.map(e => (
                  <div key={e.label} style={{ fontSize: 11 }}>
                    <Text type="secondary">{e.label}：</Text>
                    <Text strong>{e.value}</Text>
                  </div>
                ))}
              </div>
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
export default function TabHotel({ year, month, monthStr, refreshKey }: TabHotelProps) {
  const [st, setSt] = useState<HotelSourceState>({
    loading: true, roomStat: null, pmStat: null, ihgStat: null,
    hotelDI: null, security: null, dazhi: null,
  })

  const load = useCallback(async () => {
    setSt(s => ({ ...s, loading: true }))
    const [r1, r2, r3, r4, r5, r6] = await Promise.allSettled([
      fetchMaintenanceStats(year, month),
      fetchPMStats(String(year), month),
      fetchIHGStats(String(year), String(month)),
      fetchHotelDailyMonthlyDashboard(year, month),
      fetchSecurityMonthlyDashboard(year, month),
      fetchDazhi(year, month),
    ])
    setSt({
      loading:  false,
      roomStat: r1.status === 'fulfilled' ? r1.value : null,
      pmStat:   r2.status === 'fulfilled' ? r2.value : null,
      ihgStat:  r3.status === 'fulfilled' ? r3.value : null,
      hotelDI:  r4.status === 'fulfilled' ? r4.value : null,
      security: r5.status === 'fulfilled' ? r5.value : null,
      dazhi:    r6.status === 'fulfilled' ? r6.value : null,
    })
  }, [year, month, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  // ── 飯店整體健康分數（6 來源等權平均，有資料者計算）────────────────────
  const subScores = SOURCES.map(def => {
    const m = def.getMetrics(st)
    if (m.compRate === null) return null
    return calcModuleHealth({
      total:     m.total     ?? 100,
      completed: m.completed ?? Math.round((m.compRate / 100) * 100),
      overdue:   m.overdue   ?? 0,
      anomaly:   m.abnormal  ?? 0,
    })
  })
  const validScores = subScores.filter(s => s !== null) as number[]
  const hotelHealth = validScores.length > 0
    ? Math.round(validScores.reduce((a, b) => a + b, 0) / validScores.length)
    : null

  const light = getTrafficLight(hotelHealth)
  const color = TRAFFIC_LIGHT_COLOR[light]

  return (
    <div style={{ paddingBottom: 24 }}>

      {/* ── 飯店整體健康分數 ───────────────────────────────────────────── */}
      <Card style={{ marginBottom: 16, borderRadius: 8 }} bodyStyle={{ padding: '16px 24px' }}>
        <Row align="middle" gutter={24}>
          <Col>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: 96, height: 96, borderRadius: '50%',
                border: `5px solid ${color}`, background: `${color}18`,
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', margin: '0 auto',
              }}>
                <span style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1 }}>
                  {formatScore(hotelHealth)}
                </span>
                {hotelHealth !== null && <span style={{ fontSize: 11, color, opacity: 0.8 }}>/100</span>}
              </div>
              <div style={{ marginTop: 6, fontSize: 12, color: T.primary, fontWeight: 600 }}>
                飯店管理健康分數
              </div>
              <Tag color={light === 'gray' ? 'default' : light === 'green' ? 'success' : light === 'yellow' ? 'warning' : 'error'}
                style={{ marginTop: 4 }}>
                {TRAFFIC_LIGHT_LABEL[light]}
              </Tag>
              {validScores.length < 6 && (
                <div style={{ fontSize: 10, color: T.textMuted, marginTop: 2 }}>
                  部分計算（{validScores.length}/6 來源）
                </div>
              )}
            </div>
          </Col>
          <Col flex={1}>
            <Title level={5} style={{ margin: '0 0 4px', color: T.primary }}>
              B. 飯店管理摘要 — {monthStr}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              整合 6 大來源：客房保養管理 · 飯店週期保養 · IHG 客房保養 · 飯店每日巡檢 · 保全巡檢 · 大直工務部
            </Text>
            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {subScores.map((score, i) => {
                const l = getTrafficLight(score)
                const c = TRAFFIC_LIGHT_COLOR[l]
                return (
                  <Tooltip key={i} title={`${SOURCES[i].title}：${formatScore(score)} 分`}>
                    <div style={{
                      width: 36, height: 36, borderRadius: '50%',
                      border: `3px solid ${c}`, background: `${c}18`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700, color: c, cursor: 'pointer',
                    }}>
                      {formatScore(score)}
                    </div>
                  </Tooltip>
                )
              })}
            </div>
          </Col>
        </Row>
      </Card>

      {/* ── 6 來源卡片 ──────────────────────────────────────────────────── */}
      <Row gutter={[12, 12]}>
        {SOURCES.map(def => (
          <Col key={def.key} xs={24} sm={12} lg={8}>
            <SourceCard def={def} state={st} loading={st.loading} />
          </Col>
        ))}
      </Row>
    </div>
  )
}
