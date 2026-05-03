/**
 * TAB I — 資料品質監控
 * Phase 6：欄位完整度（有負責人 ∩ 有工時 ∩ 有狀態）
 *
 * 計算來源（前端推算，無新 API）：
 *   - luqun/dazhi kpi：total / completed / work_hours 推算
 *   - PM stats：current_kpi.total / completed / planned_minutes
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Progress, Row, Spin, Tag, Typography, Tooltip, Table, Space,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { InfoCircleOutlined } from '@ant-design/icons'
import { fetchDashboard as fetchLuqun } from '@/api/luqunRepair'
import { fetchDashboard as fetchDazhi } from '@/api/dazhiRepair'
import { fetchPMStats }                 from '@/api/periodicMaintenance'
import { fetchMallPMStats }             from '@/api/mallPeriodicMaintenance'
import { fetchFullBldgPMStats }         from '@/api/fullBuildingMaintenance'
import type { DashboardData as LuqunData } from '@/types/luqunRepair'
import type { DashboardData as DazhiData  } from '@/types/dazhiRepair'
import type { PMStats }                     from '@/types/periodicMaintenance'
import { getTrafficLight, TRAFFIC_LIGHT_COLOR } from '../utils/healthScore'

const { Title, Text } = Typography

const T = {
  primary:   '#1B3A5C',
  textMuted: '#8c8c8c',
  success:   '#52c41a',
  warning:   '#faad14',
  danger:    '#ff4d4f',
}

interface TabDataQualityProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface QualityRow {
  key:        string
  group:      string
  module:     string
  total:      number | null
  withStatus: number | null   // 有狀態紀錄
  withHours:  number | null   // 有工時紀錄
  completeness: number | null // 0~100%
  note:       string
}

interface QState {
  loading:    boolean
  luqun:      LuqunData | null
  dazhi:      DazhiData  | null
  hotelPM:    PMStats | null
  mallPM:     PMStats | null
  fullBldgPM: PMStats | null
}

// ── 完整度評色 ────────────────────────────────────────────────────────────────
function rateColor(v: number | null): string {
  if (v === null) return T.textMuted
  if (v >= 80) return T.success
  if (v >= 60) return T.warning
  return T.danger
}

// ════════════════════════════════════════════════════════════════════════════
// 主元件
// ════════════════════════════════════════════════════════════════════════════
export default function TabDataQuality({ year, month, monthStr, refreshKey }: TabDataQualityProps) {
  const [st, setSt] = useState<QState>({
    loading: true, luqun: null, dazhi: null, hotelPM: null, mallPM: null, fullBldgPM: null,
  })

  const load = useCallback(async () => {
    setSt(s => ({ ...s, loading: true }))
    const [r1, r2, r3, r4, r5] = await Promise.allSettled([
      fetchLuqun(year, month),
      fetchDazhi(year, month),
      fetchPMStats(String(year), month),
      fetchMallPMStats(String(year), month),
      fetchFullBldgPMStats(String(year), month),
    ])
    setSt({
      loading:    false,
      luqun:      r1.status === 'fulfilled' ? r1.value : null,
      dazhi:      r2.status === 'fulfilled' ? r2.value : null,
      hotelPM:    r3.status === 'fulfilled' ? r3.value : null,
      mallPM:     r4.status === 'fulfilled' ? r4.value : null,
      fullBldgPM: r5.status === 'fulfilled' ? r5.value : null,
    })
  }, [year, month, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const { loading, luqun, dazhi, hotelPM, mallPM, fullBldgPM } = st

  // ── 推算各模組品質指標 ────────────────────────────────────────────────────
  const rows: QualityRow[] = []

  // 1. 樂群工務
  if (luqun) {
    const k = luqun.kpi
    const withStatus = k.completed + k.uncompleted   // 有明確狀態的
    const withHours  = k.total_work_hours > 0 ? Math.round(k.total_work_hours) : 0
    const comp = k.total > 0 ? Math.round(((k.completed + k.uncompleted) / k.total) * 100) : null
    rows.push({
      key: 'luqun', group: '工務報修', module: '樂群工務報修',
      total: k.total, withStatus: k.total, withHours: k.total_work_hours > 0 ? k.total : null,
      completeness: comp,
      note: `工時合計 ${k.total_work_hours.toFixed(1)} hr，費用登錄 ${k.month_total_fee > 0 ? '✓' : '✗'}`,
    })
  } else {
    rows.push({ key: 'luqun', group: '工務報修', module: '樂群工務報修', total: null, withStatus: null, withHours: null, completeness: null, note: '資料準備中' })
  }

  // 2. 大直工務
  if (dazhi) {
    const k = dazhi.kpi
    const comp = k.total > 0 ? Math.round(((k.completed + k.uncompleted) / k.total) * 100) : null
    rows.push({
      key: 'dazhi', group: '工務報修', module: '大直工務部',
      total: k.total, withStatus: k.total, withHours: k.total_work_hours > 0 ? k.total : null,
      completeness: comp,
      note: `工時合計 ${k.total_work_hours.toFixed(1)} hr，費用登錄 ${k.month_total_fee > 0 ? '✓' : '✗'}`,
    })
  } else {
    rows.push({ key: 'dazhi', group: '工務報修', module: '大直工務部', total: null, withStatus: null, withHours: null, completeness: null, note: '資料準備中' })
  }

  // 3. 飯店週期保養
  if (hotelPM?.current_kpi) {
    const k = hotelPM.current_kpi
    const withHoursCount = k.actual_minutes > 0 ? k.completed : null
    const comp = k.total > 0
      ? Math.round(((k.completed + k.in_progress + k.scheduled) / k.total) * 100)
      : null
    rows.push({
      key: 'hotelPM', group: '飯店保養', module: '飯店週期保養',
      total: k.total, withStatus: k.completed + k.in_progress + k.scheduled,
      withHours: withHoursCount,
      completeness: comp,
      note: `預估工時 ${Math.round(k.planned_minutes / 60)} hr，實際 ${Math.round(k.actual_minutes / 60)} hr`,
    })
  } else {
    rows.push({ key: 'hotelPM', group: '飯店保養', module: '飯店週期保養', total: null, withStatus: null, withHours: null, completeness: null, note: '資料準備中' })
  }

  // 4. 商場例行維護
  if (mallPM?.current_kpi) {
    const k = mallPM.current_kpi
    const comp = k.total > 0
      ? Math.round(((k.completed + k.in_progress + k.scheduled) / k.total) * 100)
      : null
    rows.push({
      key: 'mallPM', group: '商場保養', module: '商場例行維護',
      total: k.total, withStatus: k.completed + k.in_progress + k.scheduled,
      withHours: k.actual_minutes > 0 ? k.completed : null,
      completeness: comp,
      note: `預估 ${Math.round(k.planned_minutes / 60)} hr，實際 ${Math.round(k.actual_minutes / 60)} hr`,
    })
  } else {
    rows.push({ key: 'mallPM', group: '商場保養', module: '商場例行維護', total: null, withStatus: null, withHours: null, completeness: null, note: '資料準備中' })
  }

  // 5. 全棟例行維護
  if (fullBldgPM?.current_kpi) {
    const k = fullBldgPM.current_kpi
    const comp = k.total > 0
      ? Math.round(((k.completed + k.in_progress + k.scheduled) / k.total) * 100)
      : null
    rows.push({
      key: 'fullBldg', group: '商場保養', module: '全棟例行維護',
      total: k.total, withStatus: k.completed + k.in_progress + k.scheduled,
      withHours: k.actual_minutes > 0 ? k.completed : null,
      completeness: comp,
      note: `預估 ${Math.round(k.planned_minutes / 60)} hr，實際 ${Math.round(k.actual_minutes / 60)} hr`,
    })
  } else {
    rows.push({ key: 'fullBldg', group: '商場保養', module: '全棟例行維護', total: null, withStatus: null, withHours: null, completeness: null, note: '資料準備中' })
  }

  // ── 整體品質分數（有資料模組平均）──────────────────────────────────────
  const validComps = rows.map(r => r.completeness).filter(v => v !== null) as number[]
  const overallComp = validComps.length > 0
    ? Math.round(validComps.reduce((a, b) => a + b, 0) / validComps.length)
    : null

  const columns: ColumnsType<QualityRow> = [
    {
      title: '群組', dataIndex: 'group', key: 'group', width: 90,
      render: (v: string) => <Text type="secondary" style={{ fontSize: 11 }}>{v}</Text>,
    },
    {
      title: '模組', dataIndex: 'module', key: 'module', width: 130,
      render: (v: string) => <Text strong style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: '總筆數', dataIndex: 'total', key: 'total', width: 70, align: 'center',
      render: (v: number | null) => v !== null ? v : <Text type="secondary">—</Text>,
    },
    {
      title: '有狀態', dataIndex: 'withStatus', key: 'withStatus', width: 70, align: 'center',
      render: (v: number | null, row) => {
        if (v === null || row.total === null) return <Text type="secondary">—</Text>
        const pct = Math.round((v / row.total) * 100)
        return <span style={{ color: rateColor(pct) }}>{v} ({pct}%)</span>
      },
    },
    {
      title: '有工時', dataIndex: 'withHours', key: 'withHours', width: 70, align: 'center',
      render: (v: number | null) => v !== null
        ? <span style={{ color: T.success }}>{v} ✓</span>
        : <Text type="secondary">未登錄</Text>,
    },
    {
      title: '資料完整度',
      dataIndex: 'completeness', key: 'completeness', width: 160,
      render: (v: number | null) => {
        if (v === null) return <Tag color="default">資料準備中</Tag>
        const color = rateColor(v)
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Progress
              percent={v}
              strokeColor={color}
              showInfo={false}
              size="small"
              style={{ flex: 1 }}
            />
            <span style={{ fontSize: 12, fontWeight: 700, color, minWidth: 36 }}>{v}%</span>
          </div>
        )
      },
    },
    {
      title: '備註', dataIndex: 'note', key: 'note',
      render: (v: string) => <Text type="secondary" style={{ fontSize: 11 }}>{v}</Text>,
    },
  ]

  return (
    <div style={{ paddingBottom: 24 }}>

      {/* 整體品質評分 */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card size="small" style={{ textAlign: 'center', borderTop: `3px solid ${rateColor(overallComp)}` }}>
            <div style={{ fontSize: 36, fontWeight: 700, color: rateColor(overallComp) }}>
              {overallComp !== null ? `${overallComp}%` : '—'}
            </div>
            <div style={{ fontSize: 12, color: T.textMuted }}>整體資料完整度</div>
            {overallComp !== null && (
              <Tag
                color={overallComp >= 80 ? 'success' : overallComp >= 60 ? 'warning' : 'error'}
                style={{ marginTop: 4 }}
              >
                {overallComp >= 80 ? '良好' : overallComp >= 60 ? '需改善' : '待加強'}
              </Tag>
            )}
          </Card>
        </Col>
        <Col xs={24} sm={16}>
          <Card size="small" bodyStyle={{ padding: '12px 16px' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <InfoCircleOutlined style={{ marginRight: 4 }} />
              資料完整度計算說明
            </Text>
            <div style={{ marginTop: 6, fontSize: 12, lineHeight: 1.8 }}>
              • <strong>有狀態</strong>：案件已填寫「已完成 / 進行中 / 已排程」之一<br />
              • <strong>有工時</strong>：案件工時欄位 &gt; 0（有實際執行紀錄）<br />
              • <strong>完整度</strong>：有狀態件數 / 總件數 × 100%（工務模組）<br />
              • 查詢期間：{monthStr}（{validComps.length}/{rows.length} 模組有資料）
            </div>
          </Card>
        </Col>
      </Row>

      {/* 品質明細表 */}
      <Card
        title={<Text strong style={{ color: T.primary }}>I. 資料品質明細 — {monthStr}</Text>}
        style={{ borderRadius: 8 }}
        bodyStyle={{ padding: 0 }}
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
        ) : (
          <Table<QualityRow>
            dataSource={rows}
            columns={columns}
            rowKey="key"
            size="small"
            pagination={false}
            bordered
          />
        )}
      </Card>

    </div>
  )
}
