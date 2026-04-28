/**
 * ExecMetrics — 主管指標共用元件
 *
 * 匯出：
 *   HeroKpi          — 單張大數字 KPI 卡（無狀態）
 *   ExecHeroLayer    — 6 KPI 卡網格（接受 props，無資料依賴）
 *   ExecSourceCards  — 來源小卡列（接受 props，無資料依賴）
 *   ExecMetricsCard  — 自帶資料的主管指標卡（供 Dashboard 使用）
 *
 * 資料來源：沿用 @/api/workCategoryAnalysis（fetchStats）
 * 限制：不新增 API / Service / 邏輯；exec-dashboard 原頁面使用同一套元件
 */
import { useEffect, useState, useCallback } from 'react'
import { Card, Spin } from 'antd'
import {
  ArrowUpOutlined, ArrowDownOutlined, TrophyOutlined,
  FundOutlined, RightOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons'
import { Typography } from 'antd'
import dayjs from 'dayjs'

import {
  fetchStats,
  SOURCE_LABELS,
  CATEGORY_COLORS,
  type KpiData,
  type ConcentrationData,
  type KpiSourceItem,
} from '@/api/workCategoryAnalysis'

const { Text } = Typography

// ── Design tokens（與 PROTECTED.md 一致）──────────────────────────────────────
const T = {
  primary:    '#1B3A5C',
  accent:     '#4BA8E8',
  success:    '#52c41a',
  danger:     '#cf1322',
  warning:    '#faad14',
  textMuted:  '#8c8c8c',
  red:        '#cf1322',
  green:      '#52c41a',
}

// ── 來源色（與 ExecDashboard 保持一致）────────────────────────────────────────
export const SOURCE_PIE_COLORS: Record<string, string> = {
  luqun:      '#1B3A5C',
  dazhi:      '#4BA8E8',
  hotel_room: '#722ED1',
}

// ══════════════════════════════════════════════════════════════════════════════
// HeroKpi — 單張大數字 KPI 卡
// ══════════════════════════════════════════════════════════════════════════════
export function HeroKpi({
  label, value, unit, sub, size = 36, color = T.primary, extra,
}: {
  label: string
  value: React.ReactNode
  unit?: string
  sub?: React.ReactNode
  size?: number
  color?: string
  extra?: React.ReactNode
}) {
  return (
    <Card
      size="small"
      bodyStyle={{ padding: '14px 18px' }}
      style={{ borderTop: `3px solid ${color}`, height: '100%' }}
    >
      <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 6, letterSpacing: '0.04em' }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, flexWrap: 'wrap' }}>
        <span style={{ fontSize: size, fontWeight: 800, color, lineHeight: 1.1, letterSpacing: '-1px' }}>
          {value}
        </span>
        {unit && <span style={{ fontSize: 13, color: T.textMuted }}>{unit}</span>}
        {extra}
      </div>
      {sub && <div style={{ fontSize: 11, color: T.textMuted, marginTop: 4 }}>{sub}</div>}
    </Card>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// ExecHeroLayer — 6 KPI 卡網格（props-based，供 ExecDashboard 與 ExecMetricsCard 共用）
// ══════════════════════════════════════════════════════════════════════════════
export function ExecHeroLayer({
  kpi, conc,
}: {
  kpi: KpiData
  conc: ConcentrationData
}) {
  void conc // conc 備用（一致性，未來可加集中度警示）
  const momPct   = kpi.mom_change_pct
  const momUp    = momPct !== null && momPct >= 0
  const momColor = momPct === null ? T.textMuted : momUp ? T.red : T.green
  const topSrc   = [...kpi.source_breakdown].sort((a, b) => b.hours - a.hours)[0]

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
      gap: 12,
      marginBottom: 16,
    }}>
      <HeroKpi
        label="本期總工時"
        value={kpi.total_hours.toFixed(1)}
        unit="HR"
        size={44}
        color={T.primary}
        sub={`${kpi.total_cases} 筆工項 · ${kpi.total_persons} 位人員`}
      />
      <HeroKpi
        label="人均工時"
        value={kpi.avg_person_hours.toFixed(1)}
        unit="HR / 人"
        size={38}
        color={T.accent}
        sub="人均負荷指標"
      />
      <HeroKpi
        label="最高工時類別"
        value={kpi.top_category.name}
        size={20}
        color={CATEGORY_COLORS[kpi.top_category.name] ?? T.primary}
        sub={`${kpi.top_category.hours} HR · 占 ${kpi.top_category.pct}%`}
      />
      <HeroKpi
        label="最高工時人員"
        value={kpi.top_person.name}
        size={20}
        color={T.primary}
        sub={`${kpi.top_person.hours} HR · 占 ${kpi.top_person.pct}%`}
        extra={<TrophyOutlined style={{ color: T.warning, fontSize: 16, marginLeft: 4 }} />}
      />
      <HeroKpi
        label="最高工時來源"
        value={topSrc ? topSrc.label : '–'}
        size={20}
        color="#722ED1"
        sub={topSrc ? `${topSrc.hours} HR · ${topSrc.pct}%` : ''}
      />
      <HeroKpi
        label="環比變化"
        value={
          momPct === null ? '–'
            : `${momUp ? '+' : ''}${momPct}%`
        }
        size={36}
        color={momColor}
        sub={kpi.prev_month_hours > 0 ? `對比上期 ${kpi.prev_month_hours} HR` : '無上期資料'}
        extra={momPct !== null
          ? (momUp
            ? <ArrowUpOutlined   style={{ color: momColor, fontSize: 18, marginLeft: 4 }} />
            : <ArrowDownOutlined style={{ color: momColor, fontSize: 18, marginLeft: 4 }} />)
          : undefined}
      />
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// ExecSourceCards — 來源小卡列（props-based）
// ══════════════════════════════════════════════════════════════════════════════
export function ExecSourceCards({ sourceBreakdown }: { sourceBreakdown: KpiSourceItem[] }) {
  if (!sourceBreakdown.length) return null
  return (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
      {sourceBreakdown.map(s => (
        <Card
          key={s.source}
          size="small"
          bodyStyle={{ padding: '8px 14px' }}
          style={{
            borderLeft: `3px solid ${SOURCE_PIE_COLORS[s.source] ?? T.accent}`,
            flex: '1 0 130px',
          }}
        >
          <div style={{ fontSize: 11, color: T.textMuted }}>
            {SOURCE_LABELS[s.source] ?? s.source}
          </div>
          <Text strong style={{ fontSize: 16, color: T.primary }}>{s.hours} HR</Text>
          <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>{s.pct}%</Text>
        </Card>
      ))}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// ExecMetricsCard — 自帶資料的主管指標摘要卡（Dashboard 使用）
// 沿用 fetchStats API，預設當月 / 全部來源，不新增任何 API
// ══════════════════════════════════════════════════════════════════════════════
export default function ExecMetricsCard({
  onNavigate,
}: {
  onNavigate: (path: string) => void
}) {
  const thisYear  = dayjs().year()
  const thisMonth = dayjs().month() + 1

  const [loading, setLoading] = useState(true)
  const [kpi,     setKpi]     = useState<KpiData | null>(null)
  const [conc,    setConc]    = useState<ConcentrationData | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchStats({
        year:     thisYear,
        month:    thisMonth,
        sources:  'all',
        category: 'all',
        person:   'all',
      })
      setKpi(data.kpi)
      setConc(data.concentration)
    } catch {
      // silent fail — dashboard 不因此卡住
    } finally {
      setLoading(false)
    }
  }, [thisYear, thisMonth])

  useEffect(() => { load() }, [load])

  return (
    <Card
      size="small"
      bordered={false}
      style={{ borderTop: `3px solid ${T.primary}` }}
    >
      {/* ── 標題列 ── */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', marginBottom: 12,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <FundOutlined style={{ color: T.primary, fontSize: 16 }} />
          <Text strong style={{ color: T.primary, fontSize: 15 }}>主管指標</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {thisYear} 年 {thisMonth} 月 · 樂群 / 大直 / 房務
          </Text>
        </div>
        <span
          onClick={() => onNavigate('/exec-dashboard')}
          style={{
            fontSize: 11, color: T.accent, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 2,
          }}
        >
          查看詳情 <RightOutlined style={{ fontSize: 9 }} />
        </span>
      </div>

      {/* ── 內容 ── */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '24px 0' }}>
          <Spin size="small" />
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>載入主管指標…</Text>
        </div>
      ) : !kpi || !conc ? (
        <div style={{ color: T.textMuted, fontSize: 12, padding: '8px 0' }}>
          <ExclamationCircleOutlined style={{ marginRight: 4 }} />主管指標資料暫無法載入
        </div>
      ) : (
        <>
          <ExecHeroLayer kpi={kpi} conc={conc} />
          <ExecSourceCards sourceBreakdown={kpi.source_breakdown} />
        </>
      )}
    </Card>
  )
}
