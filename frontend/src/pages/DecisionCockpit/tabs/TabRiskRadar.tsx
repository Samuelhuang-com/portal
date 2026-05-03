/**
 * TAB F — 異常與風險雷達
 * Phase 5：各模組燈號矩陣（完成率 / 逾期率 / 異常率）
 *
 * 所有 API 全部重用：
 *   - /luqun-repair/dashboard
 *   - /dazhi-repair/dashboard
 *   - /room-maintenance-detail/maintenance-stats
 *   - /periodic-maintenance/stats
 *   - /ihg-room-maintenance/stats
 *   - /hotel-daily-inspection/dashboard/monthly-summary
 *   - /security/dashboard/monthly-summary
 *   - /mall/periodic-maintenance/stats
 *   - /mall/full-building-maintenance/stats
 *   - /mall-facility-inspection/dashboard/monthly-summary
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Row, Spin, Tag, Typography, Tooltip,
  Table, Badge,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { fetchDashboard as fetchLuqun }          from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhi }          from '@/api/dazhiRepair'
import { fetchMaintenanceStats }                 from '@/api/roomMaintenanceDetail'
import { fetchPMStats }                          from '@/api/periodicMaintenance'
import { fetchIHGStats }                         from '@/api/ihgRoomMaintenance'
import { fetchHotelDailyMonthlyDashboard }       from '@/api/hotelDailyInspection'
import { fetchSecurityMonthlyDashboard }         from '@/api/securityPatrol'
import { fetchMallPMStats }                      from '@/api/mallPeriodicMaintenance'
import { fetchFullBldgPMStats }                  from '@/api/fullBuildingMaintenance'
import { fetchMallFacilityMonthlyDashboard }     from '@/api/mallFacilityInspection'
import {
  calcModuleHealth, getTrafficLight,
  TRAFFIC_LIGHT_COLOR, TRAFFIC_LIGHT_LABEL, formatScore,
  type TrafficLight,
} from '../utils/healthScore'

const { Title, Text } = Typography

const T = {
  primary:   '#1B3A5C',
  accent:    '#4BA8E8',
  bg:        '#f0f4f8',
  textMuted: '#8c8c8c',
}

interface TabRiskRadarProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface ModuleRow {
  key:         string
  group:       string
  module:      string
  compRate:    number | null   // 0~100
  overdueRate: number | null   // 0~100
  abnRate:     number | null   // 0~100
  health:      number | null   // 0~100
  light:       TrafficLight
  detail?:     string
}

// ── 燈號格渲染 ────────────────────────────────────────────────────────────────
function LightCell({ value, rate, suffix = '%' }: { value: number | null; rate?: boolean; suffix?: string }) {
  if (value === null) {
    return <Badge color="#8c8c8c" text={<Text type="secondary" style={{ fontSize: 12 }}>—</Text>} />
  }
  const light = rate
    ? getTrafficLight(value)
    : value >= 80 ? 'green' : value >= 60 ? 'yellow' : 'red'
  const color = TRAFFIC_LIGHT_COLOR[light as TrafficLight]
  return (
    <span style={{ fontWeight: 600, color, fontSize: 13 }}>
      {value}{suffix}
    </span>
  )
}

function HealthCell({ score }: { score: number | null }) {
  const light = getTrafficLight(score)
  const color = TRAFFIC_LIGHT_COLOR[light]
  return (
    <Tag
      color={light === 'gray' ? 'default' : light === 'green' ? 'success' : light === 'yellow' ? 'warning' : 'error'}
      style={{ fontWeight: 700, fontSize: 12 }}
    >
      {formatScore(score)} {score !== null ? TRAFFIC_LIGHT_LABEL[light] : '資料準備中'}
    </Tag>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// 主元件
// ════════════════════════════════════════════════════════════════════════════
export default function TabRiskRadar({ year, month, monthStr, refreshKey }: TabRiskRadarProps) {
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState<ModuleRow[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    const monthStr2 = `${year}-${String(month).padStart(2, '0')}`

    const [rLuqun, rDazhi, rRoom, rPM, rIHG, rHotelDI, rSecurity, rMallPM, rFullBldg, rFacility] =
      await Promise.allSettled([
        fetchLuqun(year, month),
        fetchDazhi(year, month),
        fetchMaintenanceStats(year, month),
        fetchPMStats(String(year), month),
        fetchIHGStats(String(year), String(month)),
        fetchHotelDailyMonthlyDashboard(year, month),
        fetchSecurityMonthlyDashboard(year, month),
        fetchMallPMStats(String(year), month),
        fetchFullBldgPMStats(String(year), month),
        fetchMallFacilityMonthlyDashboard(monthStr2),
      ])

    const newRows: ModuleRow[] = []

    // ── 飯店群組 ────────────────────────────────────────────────────────────
    // 1. 客房保養
    if (rRoom.status === 'fulfilled') {
      const k = rRoom.value.kpi
      const comp = k.current_month_completion_rate
      const abn  = k.current_month_abnormal_rate
      const h    = calcModuleHealth({ total: 100, completed: comp, overdue: 0, anomaly: abn })
      newRows.push({
        key: 'room', group: '飯店管理', module: '客房保養管理',
        compRate: Math.round(comp), overdueRate: k.consecutive_missed_rooms > 0 ? Math.round(k.consecutive_missed_rooms) : 0,
        abnRate: Math.round(abn), health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'room', group: '飯店管理', module: '客房保養管理', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 2. 飯店週期保養
    if (rPM.status === 'fulfilled' && rPM.value.current_kpi) {
      const k = rPM.value.current_kpi
      const h = calcModuleHealth({ total: k.total, completed: k.completed, overdue: k.overdue, anomaly: k.abnormal })
      newRows.push({
        key: 'pm', group: '飯店管理', module: '飯店週期保養',
        compRate: Math.round(k.completion_rate), overdueRate: k.total > 0 ? Math.round((k.overdue / k.total) * 100) : 0,
        abnRate: k.total > 0 ? Math.round((k.abnormal / k.total) * 100) : 0,
        health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'pm', group: '飯店管理', module: '飯店週期保養', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 3. IHG 客房保養
    if (rIHG.status === 'fulfilled') {
      const k = rIHG.value
      const h = calcModuleHealth({ total: k.total_scheduled, completed: k.completed, overdue: 0, anomaly: k.abnormal })
      newRows.push({
        key: 'ihg', group: '飯店管理', module: 'IHG 客房保養',
        compRate: Math.round(k.completion_rate), overdueRate: null,
        abnRate: k.total_scheduled > 0 ? Math.round((k.abnormal / k.total_scheduled) * 100) : 0,
        health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'ihg', group: '飯店管理', module: 'IHG 客房保養', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 4. 飯店每日巡檢
    if (rHotelDI.status === 'fulfilled') {
      const k = rHotelDI.value
      const h = calcModuleHealth({ total: k.total_items, completed: k.checked_items, overdue: 0, anomaly: k.abnormal_items })
      newRows.push({
        key: 'hotelDI', group: '飯店管理', module: '飯店每日巡檢',
        compRate: Math.round(k.completion_rate), overdueRate: null,
        abnRate: k.total_items > 0 ? Math.round((k.abnormal_items / k.total_items) * 100) : 0,
        health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'hotelDI', group: '飯店管理', module: '飯店每日巡檢', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 5. 保全巡檢
    if (rSecurity.status === 'fulfilled') {
      const k = rSecurity.value
      const h = calcModuleHealth({ total: k.total_items, completed: k.checked_items, overdue: 0, anomaly: k.abnormal_items })
      newRows.push({
        key: 'security', group: '飯店管理', module: '保全巡檢',
        compRate: Math.round(k.completion_rate), overdueRate: null,
        abnRate: k.total_items > 0 ? Math.round((k.abnormal_items / k.total_items) * 100) : 0,
        health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'security', group: '飯店管理', module: '保全巡檢', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 6. 大直工務部
    if (rDazhi.status === 'fulfilled') {
      const k = rDazhi.value.kpi
      const rate = k.total > 0 ? Math.round((k.completed / k.total) * 100) : null
      const h = calcModuleHealth({ total: k.total, completed: k.completed, overdue: k.uncompleted, anomaly: 0 })
      newRows.push({
        key: 'dazhi', group: '飯店管理', module: '大直工務部',
        compRate: rate, overdueRate: k.total > 0 ? Math.round((k.uncompleted / k.total) * 100) : 0,
        abnRate: 0, health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'dazhi', group: '飯店管理', module: '大直工務部', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // ── 商場群組 ────────────────────────────────────────────────────────────
    // 7. 商場例行維護
    if (rMallPM.status === 'fulfilled' && rMallPM.value.current_kpi) {
      const k = rMallPM.value.current_kpi
      const h = calcModuleHealth({ total: k.total, completed: k.completed, overdue: k.overdue, anomaly: k.abnormal })
      newRows.push({
        key: 'mallPM', group: '商場管理', module: '商場例行維護',
        compRate: Math.round(k.completion_rate), overdueRate: k.total > 0 ? Math.round((k.overdue / k.total) * 100) : 0,
        abnRate: k.total > 0 ? Math.round((k.abnormal / k.total) * 100) : 0,
        health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'mallPM', group: '商場管理', module: '商場例行維護', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 8. 全棟例行維護
    if (rFullBldg.status === 'fulfilled' && rFullBldg.value.current_kpi) {
      const k = rFullBldg.value.current_kpi
      const h = calcModuleHealth({ total: k.total, completed: k.completed, overdue: k.overdue, anomaly: k.abnormal })
      newRows.push({
        key: 'fullBldg', group: '商場管理', module: '全棟例行維護',
        compRate: Math.round(k.completion_rate), overdueRate: k.total > 0 ? Math.round((k.overdue / k.total) * 100) : 0,
        abnRate: k.total > 0 ? Math.round((k.abnormal / k.total) * 100) : 0,
        health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'fullBldg', group: '商場管理', module: '全棟例行維護', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 9. 商場工務巡檢
    if (rFacility.status === 'fulfilled') {
      const sheets = rFacility.value.sheets ?? []
      const total   = sheets.length * 30
      const missing = sheets.reduce((a, s) => a + s.missing_count, 0)
      const comp    = total > 0 ? Math.round(((total - missing) / total) * 100) : null
      const h       = comp !== null ? calcModuleHealth({ total, completed: total - missing, overdue: missing, anomaly: 0 }) : null
      newRows.push({
        key: 'facility', group: '商場管理', module: '商場工務巡檢',
        compRate: comp, overdueRate: total > 0 ? Math.round((missing / total) * 100) : null,
        abnRate: 0, health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'facility', group: '商場管理', module: '商場工務巡檢', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    // 10. 現場報修（樂群）
    if (rLuqun.status === 'fulfilled') {
      const k = rLuqun.value.kpi
      const rate = k.total > 0 ? Math.round((k.completed / k.total) * 100) : null
      const h = calcModuleHealth({ total: k.total, completed: k.completed, overdue: k.uncompleted, anomaly: 0 })
      newRows.push({
        key: 'luqun', group: '商場管理', module: '現場報修（樂群）',
        compRate: rate, overdueRate: k.total > 0 ? Math.round((k.uncompleted / k.total) * 100) : 0,
        abnRate: 0, health: h, light: getTrafficLight(h),
      })
    } else {
      newRows.push({ key: 'luqun', group: '商場管理', module: '現場報修（樂群）', compRate: null, overdueRate: null, abnRate: null, health: null, light: 'gray' })
    }

    setRows(newRows)
    setLoading(false)
  }, [year, month, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const columns: ColumnsType<ModuleRow> = [
    {
      title: '群組', dataIndex: 'group', key: 'group', width: 80,
      render: (v: string) => <Text type="secondary" style={{ fontSize: 11 }}>{v}</Text>,
      onCell: (row, idx) => {
        const groupRows = rows.filter(r => r.group === row.group)
        const first = rows.findIndex(r => r.group === row.group)
        return idx === first ? { rowSpan: groupRows.length } : { rowSpan: 0 }
      },
    },
    {
      title: '模組', dataIndex: 'module', key: 'module', width: 130,
      render: (v: string) => <Text strong style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '完成率', dataIndex: 'compRate', key: 'compRate', width: 80, align: 'center',
      render: (v: number | null) => <LightCell value={v} rate />,
      sorter: (a, b) => (a.compRate ?? -1) - (b.compRate ?? -1),
    },
    {
      title: '逾期率', dataIndex: 'overdueRate', key: 'overdueRate', width: 80, align: 'center',
      render: (v: number | null) => {
        if (v === null) return <Text type="secondary">—</Text>
        const light = v <= 5 ? 'green' : v <= 20 ? 'yellow' : 'red'
        const color = TRAFFIC_LIGHT_COLOR[light as TrafficLight]
        return <span style={{ color, fontWeight: 600, fontSize: 13 }}>{v}%</span>
      },
    },
    {
      title: '異常率', dataIndex: 'abnRate', key: 'abnRate', width: 80, align: 'center',
      render: (v: number | null) => {
        if (v === null) return <Text type="secondary">—</Text>
        const light = v === 0 ? 'green' : v <= 10 ? 'yellow' : 'red'
        const color = TRAFFIC_LIGHT_COLOR[light as TrafficLight]
        return <span style={{ color, fontWeight: 600, fontSize: 13 }}>{v}%</span>
      },
    },
    {
      title: '健康分數', dataIndex: 'health', key: 'health', width: 130, align: 'center',
      render: (_, row) => <HealthCell score={row.health} />,
      sorter: (a, b) => (a.health ?? -1) - (b.health ?? -1),
    },
  ]

  // 需特別關注的模組
  const alertRows = rows.filter(r => r.light === 'red' || r.light === 'yellow')

  return (
    <div style={{ paddingBottom: 24 }}>

      {/* 摘要燈號統計 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {(['green', 'yellow', 'red', 'gray'] as TrafficLight[]).map(l => {
          const count = rows.filter(r => r.light === l).length
          const color = TRAFFIC_LIGHT_COLOR[l]
          return (
            <Col key={l} xs={12} sm={6}>
              <Card size="small" style={{ textAlign: 'center', borderTop: `3px solid ${color}` }} bodyStyle={{ padding: '12px 8px' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color }}>{count}</div>
                <div style={{ fontSize: 12, color }}>●&nbsp;{TRAFFIC_LIGHT_LABEL[l]}</div>
              </Card>
            </Col>
          )
        })}
      </Row>

      {/* 燈號矩陣表格 */}
      <Card
        title={
          <Text strong style={{ color: T.primary }}>
            F. 異常與風險雷達 — {monthStr} 燈號矩陣
          </Text>
        }
        style={{ borderRadius: 8 }}
        bodyStyle={{ padding: 0 }}
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
        ) : (
          <Table<ModuleRow>
            dataSource={rows}
            columns={columns}
            rowKey="key"
            size="small"
            pagination={false}
            bordered
            rowClassName={row =>
              row.light === 'red'    ? 'ant-table-row-red'
              : row.light === 'yellow' ? 'ant-table-row-yellow'
              : ''
            }
          />
        )}
      </Card>

      <style>{`
        .ant-table-row-red td { background: #fff1f0 !important; }
        .ant-table-row-yellow td { background: #fffbe6 !important; }
      `}</style>
    </div>
  )
}
