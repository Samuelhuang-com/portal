/**
 * TAB C — 商場管理摘要
 * Phase 3：5 工項精華整合（+ 2 灰燈佔位）
 *
 * 來源                    API
 * 1. 商場例行維護          /mall/periodic-maintenance/stats
 * 2. 全棟例行維護          /mall/full-building-maintenance/stats
 * 3. 商場工務巡檢          /mall-facility-inspection/dashboard/monthly-summary
 * 4. 現場報修（樂群）      /luqun-repair/dashboard
 * 5. 上級交辦              → 灰燈（資料準備中）
 * 6. 緊急事件              → 灰燈（資料準備中）
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Progress, Row, Spin, Tag, Typography, Divider, Tooltip,
} from 'antd'
import { InfoCircleOutlined } from '@ant-design/icons'
import { fetchMallPMStats }                      from '@/api/mallPeriodicMaintenance'
import { fetchFullBldgPMStats }                  from '@/api/fullBuildingMaintenance'
import { fetchMallFacilityMonthlyDashboard }     from '@/api/mallFacilityInspection'
import { fetchDashboard as fetchLuqun }          from '@/api/luqunRepair'
import type { PMStats }                          from '@/types/periodicMaintenance'
import type { MallFIMonthlyDashboardSummary }    from '@/api/mallFacilityInspection'
import type { DashboardData as LuqunData }       from '@/types/luqunRepair'
import {
  calcModuleHealth, getTrafficLight,
  TRAFFIC_LIGHT_COLOR, TRAFFIC_LIGHT_LABEL, formatScore,
} from '../utils/healthScore'

const { Title, Text } = Typography

const T = {
  primary:   '#1B3A5C',
  bg:        '#f0f4f8',
  textMuted: '#8c8c8c',
}

interface TabMallProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface MallSourceState {
  loading:     boolean
  mallPM:      PMStats | null
  fullBldgPM:  PMStats | null
  facilityDI:  MallFIMonthlyDashboardSummary | null
  luqun:       LuqunData | null
}

// ── 各來源卡 ──────────────────────────────────────────────────────────────────

interface SourceMetrics {
  total:     number | null
  completed: number | null
  overdue:   number | null
  abnormal:  number | null
  compRate:  number | null
  extra?:    Array<{ label: string; value: string }>
}

function getMetricsMallPM(s: MallSourceState): SourceMetrics {
  if (!s.mallPM?.current_kpi) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
  const k = s.mallPM.current_kpi
  return {
    total:     k.total,
    completed: k.completed,
    overdue:   k.overdue,
    abnormal:  k.abnormal,
    compRate:  k.completion_rate,
    extra: [
      { label: '預估工時', value: `${Math.round(k.planned_minutes / 60)} hr` },
      { label: '實際工時', value: `${Math.round(k.actual_minutes  / 60)} hr` },
      { label: '逾期',    value: `${k.overdue} 項` },
    ],
  }
}

function getMetricsFullBldg(s: MallSourceState): SourceMetrics {
  if (!s.fullBldgPM?.current_kpi) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
  const k = s.fullBldgPM.current_kpi
  return {
    total:     k.total,
    completed: k.completed,
    overdue:   k.overdue,
    abnormal:  k.abnormal,
    compRate:  k.completion_rate,
    extra: [
      { label: '預估工時', value: `${Math.round(k.planned_minutes / 60)} hr` },
      { label: '實際工時', value: `${Math.round(k.actual_minutes  / 60)} hr` },
      { label: '逾期',    value: `${k.overdue} 項` },
    ],
  }
}

function getMetricsFacilityDI(s: MallSourceState): SourceMetrics {
  if (!s.facilityDI) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
  // 彙總各樓層
  const sheets = s.facilityDI.sheets
  if (!sheets || sheets.length === 0) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
  const totalCount   = sheets.reduce((a, sh) => a + sh.month_count,   0)
  const missingCount = sheets.reduce((a, sh) => a + sh.missing_count, 0)
  const expectedDays = sheets[0]?.expected_days ?? 30
  const totalExpected = expectedDays * sheets.length
  const compRate = totalExpected > 0
    ? Math.round(((totalExpected - missingCount * sheets.length) / totalExpected) * 100)
    : null
  return {
    total:     totalExpected,
    completed: totalCount,
    overdue:   missingCount,
    abnormal:  0,
    compRate:  compRate,
    extra:     sheets.map(sh => ({ label: sh.floor, value: `${sh.month_count} 筆` })),
  }
}

function getMetricsLuqun(s: MallSourceState): SourceMetrics {
  if (!s.luqun) return { total: null, completed: null, overdue: null, abnormal: null, compRate: null }
  const k = s.luqun.kpi
  const rate = k.total > 0 ? Math.round((k.completed / k.total) * 100) : null
  return {
    total:     k.total,
    completed: k.completed,
    overdue:   k.uncompleted,
    abnormal:  0,
    compRate:  rate,
    extra: [
      { label: '待驗收',  value: `${k.pending_verify} 件` },
      { label: '本月費用', value: `NT$ ${k.month_total_fee.toLocaleString()}` },
    ],
  }
}

// ── 來源卡定義 ────────────────────────────────────────────────────────────────
interface SourceCardConfig {
  key:       string
  title:     string
  color:     string
  gray?:     boolean   // 灰燈佔位（上級交辦/緊急事件）
  grayNote?: string
  getMetrics: (s: MallSourceState) => SourceMetrics
}

const SOURCE_CARDS: SourceCardConfig[] = [
  { key: 'mallPM',   title: '商場例行維護', color: '#4BA8E8', getMetrics: getMetricsMallPM   },
  { key: 'fullBldg', title: '全棟例行維護', color: '#1B3A5C', getMetrics: getMetricsFullBldg },
  { key: 'facility', title: '商場工務巡檢', color: '#13c2c2', getMetrics: getMetricsFacilityDI },
  { key: 'luqun',    title: '現場報修（樂群）', color: '#52c41a', getMetrics: getMetricsLuqun },
  { key: 'assign',   title: '上級交辦', color: '#8c8c8c', gray: true, grayNote: '資料接入中',
    getMetrics: () => ({ total: null, completed: null, overdue: null, abnormal: null, compRate: null }) },
  { key: 'urgent',   title: '緊急事件', color: '#ff4d4f', gray: true, grayNote: '資料接入中',
    getMetrics: () => ({ total: null, completed: null, overdue: null, abnormal: null, compRate: null }) },
]

// ── 來源卡 UI ─────────────────────────────────────────────────────────────────
function SourceCard({
  cfg, state, loading,
}: { cfg: SourceCardConfig; state: MallSourceState; loading: boolean }) {
  const m = cfg.getMetrics(state)

  if (cfg.gray) {
    return (
      <Card size="small" style={{ height: '100%', borderTop: `3px solid ${cfg.color}` }} bodyStyle={{ padding: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <Text strong style={{ fontSize: 13, color: T.primary }}>{cfg.title}</Text>
          <Tag color="default" style={{ fontSize: 11, margin: 0 }}>資料準備中</Tag>
        </div>
        <div style={{ textAlign: 'center', padding: '20px 0', color: T.textMuted, fontSize: 12 }}>
          <InfoCircleOutlined style={{ marginRight: 4 }} />{cfg.grayNote}
        </div>
      </Card>
    )
  }

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
    <Card size="small" style={{ height: '100%', borderTop: `3px solid ${cfg.color}` }} bodyStyle={{ padding: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <Text strong style={{ fontSize: 13, color: T.primary }}>{cfg.title}</Text>
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
          <div style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 2 }}>
              <Text type="secondary">完成率</Text>
              <Text strong style={{ color }}>{m.compRate}%</Text>
            </div>
            <Progress percent={m.compRate ?? 0} strokeColor={color} showInfo={false} size="small" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <Text type="secondary" style={{ fontSize: 11 }}>健康分數</Text>
            <Text strong style={{ fontSize: 16, color }}>{formatScore(health)}</Text>
          </div>
          {m.extra && m.extra.length > 0 && (
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
export default function TabMall({ year, month, monthStr, refreshKey }: TabMallProps) {
  const [st, setSt] = useState<MallSourceState>({
    loading: true, mallPM: null, fullBldgPM: null, facilityDI: null, luqun: null,
  })

  const load = useCallback(async () => {
    setSt(s => ({ ...s, loading: true }))
    const monthStr2 = `${year}-${String(month).padStart(2, '0')}`
    const [r1, r2, r3, r4] = await Promise.allSettled([
      fetchMallPMStats(String(year), month),
      fetchFullBldgPMStats(String(year), month),
      fetchMallFacilityMonthlyDashboard(monthStr2),
      fetchLuqun(year, month),
    ])
    setSt({
      loading:    false,
      mallPM:     r1.status === 'fulfilled' ? r1.value : null,
      fullBldgPM: r2.status === 'fulfilled' ? r2.value : null,
      facilityDI: r3.status === 'fulfilled' ? r3.value : null,
      luqun:      r4.status === 'fulfilled' ? r4.value : null,
    })
  }, [year, month, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  // 商場整體健康分數（排除灰燈）
  const subScores = SOURCE_CARDS.filter(c => !c.gray).map(cfg => {
    const m = cfg.getMetrics(st)
    if (m.compRate === null) return null
    return calcModuleHealth({
      total:     m.total     ?? 100,
      completed: m.completed ?? Math.round((m.compRate / 100) * 100),
      overdue:   m.overdue   ?? 0,
      anomaly:   m.abnormal  ?? 0,
    })
  })
  const validScores = subScores.filter(s => s !== null) as number[]
  const mallHealth  = validScores.length > 0
    ? Math.round(validScores.reduce((a, b) => a + b, 0) / validScores.length)
    : null
  const light = getTrafficLight(mallHealth)
  const color = TRAFFIC_LIGHT_COLOR[light]

  return (
    <div style={{ paddingBottom: 24 }}>
      {/* 商場整體健康分數 */}
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
                <span style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1 }}>{formatScore(mallHealth)}</span>
                {mallHealth !== null && <span style={{ fontSize: 11, color, opacity: 0.8 }}>/100</span>}
              </div>
              <div style={{ marginTop: 6, fontSize: 12, color: T.primary, fontWeight: 600 }}>商場管理健康分數</div>
              <Tag color={light === 'gray' ? 'default' : light === 'green' ? 'success' : light === 'yellow' ? 'warning' : 'error'} style={{ marginTop: 4 }}>
                {TRAFFIC_LIGHT_LABEL[light]}
              </Tag>
            </div>
          </Col>
          <Col flex={1}>
            <Title level={5} style={{ margin: '0 0 4px', color: T.primary }}>
              C. 商場管理摘要 — {monthStr}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              整合 6 工項：商場例行維護 · 全棟例行維護 · 商場工務巡檢 · 現場報修 · 上級交辦（準備中） · 緊急事件（準備中）
            </Text>
            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {SOURCE_CARDS.map((cfg, i) => {
                const score = cfg.gray ? null : subScores[i - (SOURCE_CARDS.slice(0, i).filter(c => !c.gray).length > i ? 0 : 0)]
                const l = getTrafficLight(cfg.gray ? null : validScores[SOURCE_CARDS.filter((c, idx) => !c.gray && idx <= i).length - 1] ?? null)
                const c2 = TRAFFIC_LIGHT_COLOR[l]
                return (
                  <Tooltip key={cfg.key} title={cfg.gray ? `${cfg.title}：資料準備中` : `${cfg.title}：${formatScore(cfg.gray ? null : validScores[i] ?? null)} 分`}>
                    <div style={{
                      width: 36, height: 36, borderRadius: '50%',
                      border: `3px solid ${cfg.gray ? '#8c8c8c' : c2}`,
                      background: `${cfg.gray ? '#8c8c8c' : c2}18`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700, color: cfg.gray ? '#8c8c8c' : c2, cursor: 'pointer',
                    }}>
                      {cfg.gray ? '—' : formatScore(validScores[SOURCE_CARDS.filter((c, idx) => !c.gray && idx < i).length] ?? null)}
                    </div>
                  </Tooltip>
                )
              })}
            </div>
          </Col>
        </Row>
      </Card>

      {/* 6 工項卡片 */}
      <Row gutter={[12, 12]}>
        {SOURCE_CARDS.map(cfg => (
          <Col key={cfg.key} xs={24} sm={12} lg={8}>
            <SourceCard cfg={cfg} state={st} loading={st.loading} />
          </Col>
        ))}
      </Row>
    </div>
  )
}
