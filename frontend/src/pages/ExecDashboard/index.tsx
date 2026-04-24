/**
 * 高階主管 Dashboard  (/exec-dashboard)
 *
 * Portal 標準風格三層駕駛艙設計：
 *   第一層  Hero KPI 區    — 6 大指標超大數字
 *   第二層  決策圖表區      — 2×3 卡片式圖表
 *   第三層  明細分析區      — 可收合表格
 *
 * ⚠️  本頁為「新功能」，獨立於 /work-category-analysis（原功能完全保留）
 *     資料層：直接沿用現有 workCategoryAnalysis API，不新增/修改後端邏輯
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { Breadcrumb, Card, Collapse, Divider, Progress, Select, Space, Spin, Statistic, Table, Tag, Tooltip, Typography } from 'antd'
import {
  ArrowUpOutlined, ArrowDownOutlined,
  MinusOutlined, FireOutlined, CheckCircleOutlined,
  HomeOutlined, FundOutlined,
  TeamOutlined, ClockCircleOutlined, WarningOutlined, TrophyOutlined,
} from '@ant-design/icons'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid,
  Tooltip as RcTooltip, ResponsiveContainer, Legend,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchYears, fetchPersons, fetchStats,
  CATEGORIES, SOURCE_LABELS, CATEGORY_COLORS, CATEGORY_TAG_COLORS,
  type CategoryStats, type PersonRankingItem, type HoursRow, type PersonHoursRow,
} from '@/api/workCategoryAnalysis'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Text, Title } = Typography

// ══════════════════════════════════════════════════════════════════════════════
// Portal 標準設計 Token（依 PROTECTED.md）
// ══════════════════════════════════════════════════════════════════════════════
const T = {
  primary:    '#1B3A5C',
  accent:     '#4BA8E8',
  bg:         '#f0f4f8',
  success:    '#52c41a',
  danger:     '#cf1322',
  warning:    '#faad14',
  textSecond: '#595959',
  textMuted:  '#8c8c8c',
  border:     '#d9d9d9',
  cardBg:     '#ffffff',
  // 輔助（不在 PROTECTED 但符合系統一致性）
  red:        '#cf1322',
  amber:      '#faad14',
  green:      '#52c41a',
  blue:       '#1B3A5C',
}

const SOURCE_PIE_COLORS: Record<string, string> = {
  luqun:      '#1B3A5C',
  dazhi:      '#4BA8E8',
  hotel_room: '#722ED1',
}

const PIE_COLORS  = ['#4BA8E8', '#52C41A', '#FF4D4F', '#FA8C16', '#722ED1']
const MONTHS      = Array.from({ length: 12 }, (_, i) => i + 1)
const SRC_OPTIONS = [
  { value: 'all',        label: '全部來源' },
  { value: 'luqun',      label: '樂群工務' },
  { value: 'dazhi',      label: '大直工務' },
  { value: 'hotel_room', label: '房務保養' },
]

// ══════════════════════════════════════════════════════════════════════════════
// 決策提示
// ══════════════════════════════════════════════════════════════════════════════
interface AlertItem { level: 'red' | 'amber' | 'green'; msg: string }

function generateAlerts(data: CategoryStats | null): AlertItem[] {
  if (!data) return []
  const alerts: AlertItem[] = []
  const { concentration, category_breakdown, kpi } = data

  if (concentration.top3_pct > 70)
    alerts.push({ level: 'red',   msg: `⚠️ 人力高度集中：前 3 人工時佔 ${concentration.top3_pct}%，建議分散風險` })
  else if (concentration.top3_pct > 50)
    alerts.push({ level: 'amber', msg: `⚡ 前 3 人工時佔比 ${concentration.top3_pct}%，略偏集中` })
  else
    alerts.push({ level: 'green', msg: `✓ 人力分布正常（前 3 人佔比 ${concentration.top3_pct}%）` })

  const repairItem = category_breakdown.find(c => c.name === '現場報修')
  if (repairItem && repairItem.pct > 50)
    alerts.push({ level: 'red',   msg: `⚠️ 現場報修占比過高（${repairItem.pct}%），例行維護比重偏低` })
  else if (repairItem && repairItem.pct > 40)
    alerts.push({ level: 'amber', msg: `⚡ 現場報修占比 ${repairItem.pct}%，注意維護 / 巡檢比例` })

  if (kpi.mom_change_pct !== null) {
    if (kpi.mom_change_pct > 25)
      alerts.push({ level: 'amber', msg: `📈 本期工時環比 +${kpi.mom_change_pct}%，工作量大幅增加` })
    else if (kpi.mom_change_pct < -25)
      alerts.push({ level: 'amber', msg: `📉 本期工時環比 ${kpi.mom_change_pct}%，注意工作量下滑` })
  }
  return alerts
}

function AlertBar({ alerts }: { alerts: AlertItem[] }) {
  if (!alerts.length) return null
  const colorMap: Record<string, string>  = { red: T.red,   amber: T.amber,              green: T.green }
  const bgMap:    Record<string, string>  = { red: '#fff1f0', amber: '#fffbe6',            green: '#f6ffed' }
  const bdMap:    Record<string, string>  = { red: '#ffccc7', amber: '#ffe58f',            green: '#b7eb8f' }
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
      {alerts.map((a, i) => (
        <div key={i} style={{
          background:   bgMap[a.level],
          border:       `1px solid ${bdMap[a.level]}`,
          borderRadius: 6,
          padding:      '5px 12px',
          fontSize:     12,
          color:        colorMap[a.level],
          display:      'flex', alignItems: 'center', gap: 6,
        }}>
          {a.level === 'red'   && <FireOutlined />}
          {a.level === 'amber' && <MinusOutlined />}
          {a.level === 'green' && <CheckCircleOutlined />}
          {a.msg}
        </div>
      ))}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// Hero KPI 卡片（大數字）
// ══════════════════════════════════════════════════════════════════════════════
function HeroKpi({ label, value, unit, sub, size = 36, color = T.primary, extra }:
  { label: string; value: React.ReactNode; unit?: string; sub?: React.ReactNode; size?: number; color?: string; extra?: React.ReactNode }) {
  return (
    <Card
      size="small"
      bodyStyle={{ padding: '14px 18px' }}
      style={{ borderTop: `3px solid ${color}`, height: '100%' }}
    >
      <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 6, letterSpacing: '0.04em' }}>{label}</div>
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
// Donut 圖（recharts PieChart innerRadius）
// ══════════════════════════════════════════════════════════════════════════════
function DonutChart({ data, colors }: { data: { name: string; value: number; pct: number }[]; colors: string[] }) {
  const filtered = data.filter(d => d.value > 0)
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={filtered}
          dataKey="value"
          nameKey="name"
          cx="42%"
          cy="50%"
          innerRadius={52}
          outerRadius={82}
          paddingAngle={2}
        >
          {filtered.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
        </Pie>
        <RcTooltip formatter={(v: number, name) => [`${v.toFixed(1)} HR`, name]} />
        <Legend
          layout="vertical"
          align="right"
          verticalAlign="middle"
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, color: T.textSecond }}
          formatter={(v: string, entry: { payload?: { pct?: number } }) => `${v}  ${entry?.payload?.pct ?? 0}%`}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// 主頁面
// ══════════════════════════════════════════════════════════════════════════════
export default function ExecDashboardPage() {
  const thisYear  = dayjs().year()
  const thisMonth = dayjs().month() + 1

  const [years,    setYears]    = useState<number[]>([])
  const [persons,  setPersons]  = useState<string[]>([])
  const [year,     setYear]     = useState<number>(thisYear)
  const [month,    setMonth]    = useState<number>(thisMonth)
  const [sources,  setSources]  = useState<string>('all')
  const [category, setCategory] = useState<string>('all')
  const [person,   setPerson]   = useState<string>('all')
  const [loading,  setLoading]  = useState(false)
  const [stats,    setStats]    = useState<CategoryStats | null>(null)

  useEffect(() => {
    fetchYears().then(r => setYears(r.years.length ? r.years : [thisYear])).catch(() => setYears([thisYear]))
  }, [])  // eslint-disable-line

  useEffect(() => {
    fetchPersons(year, sources).then(r => setPersons(r.persons)).catch(() => {})
  }, [year, sources])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchStats({ year, month, sources, category, person })
      setStats(data)
    } finally {
      setLoading(false)
    }
  }, [year, month, sources, category, person])

  useEffect(() => { load() }, [load])

  const kpi    = stats?.kpi
  const conc   = stats?.concentration
  const alerts = useMemo(() => generateAlerts(stats), [stats])

  // ── 篩選工具列 ────────────────────────────────────────────────────────────
  function FilterBar() {
    return (
      <Card size="small" bodyStyle={{ padding: '10px 16px' }} style={{ marginBottom: 14 }}>
        <Space wrap size={8}>
          <Text style={{ fontSize: 12, color: T.textMuted }}>篩選：</Text>
          <Select value={year} onChange={setYear} size="small" style={{ width: 82 }}>
            {years.map(y => <Select.Option key={y} value={y}>{y}</Select.Option>)}
          </Select>
          <Select value={month} onChange={setMonth} size="small" style={{ width: 78 }}>
            <Select.Option value={0}>全年</Select.Option>
            {MONTHS.map(m => <Select.Option key={m} value={m}>{m}月</Select.Option>)}
          </Select>
          <Select value={sources} onChange={v => { setSources(v); setPerson('all') }} size="small" style={{ width: 100 }}>
            {SRC_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}
          </Select>
          <Select value={category} onChange={setCategory} size="small" style={{ width: 90 }}>
            <Select.Option value="all">全部類別</Select.Option>
            {CATEGORIES.map(c => <Select.Option key={c} value={c}>{c}</Select.Option>)}
          </Select>
          <Select value={person} onChange={setPerson} size="small" style={{ width: 90 }} showSearch>
            <Select.Option value="all">全部人員</Select.Option>
            {persons.map(p => <Select.Option key={p} value={p}>{p}</Select.Option>)}
          </Select>
          <Text style={{ fontSize: 11, color: T.textMuted }}>
            {stats?.meta.total_rows ?? '–'} 筆工時記錄
          </Text>
        </Space>
      </Card>
    )
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 第一層：Hero KPI
  // ════════════════════════════════════════════════════════════════════════════
  function HeroLayer() {
    if (!kpi || !conc) return null
    const momPct  = kpi.mom_change_pct
    const momUp   = momPct !== null && momPct >= 0
    const momColor = momPct === null ? T.textMuted : momUp ? T.red : T.green
    const topSrc  = [...(kpi.source_breakdown)].sort((a, b) => b.hours - a.hours)[0]

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
              ? <ArrowUpOutlined style={{ color: momColor, fontSize: 18, marginLeft: 4 }} />
              : <ArrowDownOutlined style={{ color: momColor, fontSize: 18, marginLeft: 4 }} />)
            : undefined}
        />
      </div>
    )
  }

  // 來源摘要小卡
  function SourceCards() {
    if (!kpi?.source_breakdown.length) return null
    return (
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        {kpi.source_breakdown.map(s => (
          <Card key={s.source} size="small" bodyStyle={{ padding: '8px 14px' }}
            style={{ borderLeft: `3px solid ${SOURCE_PIE_COLORS[s.source] ?? T.accent}`, flex: '1 0 130px' }}>
            <div style={{ fontSize: 11, color: T.textMuted }}>{s.label}</div>
            <Text strong style={{ fontSize: 16, color: T.primary }}>{s.hours} HR</Text>
            <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>{s.pct}%</Text>
          </Card>
        ))}
      </div>
    )
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 第二層：圖表
  // ════════════════════════════════════════════════════════════════════════════

  function TrendCard() {
    const data = stats?.chart_data ?? []
    return (
      <Card size="small"
        title={<Text strong>📈 工項類別趨勢</Text>}
        extra={<Text type="secondary" style={{ fontSize: 11 }}>{month === 0 ? '全年月趨勢' : `${month}月日趨勢`}</Text>}
        style={{ height: '100%' }}
      >
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 4, right: 12, left: -16, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} unit="H" />
            <RcTooltip formatter={(v: number) => [`${v.toFixed(1)} HR`]} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: 11 }} />
            {CATEGORIES.map(c => (
              <Line key={c} type="monotone" dataKey={c} stroke={CATEGORY_COLORS[c]}
                strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  function CatDonutCard() {
    const data = stats?.category_breakdown ?? []
    return (
      <Card size="small"
        title={<Text strong>🟠 類別工時分布</Text>}
        extra={<Text type="secondary" style={{ fontSize: 11 }}>各類占比</Text>}
        style={{ height: '100%' }}
      >
        <DonutChart data={data} colors={PIE_COLORS} />
      </Card>
    )
  }

  function PersonBarCard() {
    const data = (stats?.person_ranking ?? []).slice(0, 10).reverse()
    return (
      <Card size="small"
        title={<><TeamOutlined /> <Text strong>人員工時 Top 10</Text></>}
        extra={<Text type="secondary" style={{ fontSize: 11 }}>整合三來源</Text>}
        style={{ height: '100%' }}
      >
        {!data.length
          ? <Text type="secondary" style={{ fontSize: 12 }}>暫無資料</Text>
          : (
            <ResponsiveContainer width="100%" height={Math.max(180, data.length * 22)}>
              <BarChart data={data} layout="vertical" margin={{ top: 4, right: 36, left: 58, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 9 }} unit="H" />
                <YAxis type="category" dataKey="person" tick={{ fontSize: 10 }} width={54} />
                <RcTooltip formatter={(v: number, _n, p) => [`${v.toFixed(1)} HR (${p.payload.pct}%)  ${p.payload.top_category}`]} />
                <Bar dataKey="hours" radius={[0, 4, 4, 0]}>
                  {data.map((item: PersonRankingItem, i) => (
                    <Cell key={i} fill={SOURCE_PIE_COLORS[item.sources?.[0] ?? 'luqun'] ?? T.accent} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )
        }
        <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
          {Object.entries(SOURCE_LABELS).map(([k, v]) => (
            <Space key={k} size={4}>
              <span style={{ display: 'inline-block', width: 9, height: 9, borderRadius: 2,
                background: SOURCE_PIE_COLORS[k] ?? T.accent }} />
              <Text style={{ fontSize: 11 }}>{v}</Text>
            </Space>
          ))}
        </div>
      </Card>
    )
  }

  function MatrixCard() {
    const data = (stats?.category_person_matrix ?? []).slice(0, 10)
    return (
      <Card size="small"
        title={<Text strong>⚡ 類別 × 人員交叉</Text>}
        extra={<Text type="secondary" style={{ fontSize: 11 }}>工時分布</Text>}
        style={{ height: '100%' }}
      >
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 4, right: 12, left: -16, bottom: 28 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="person" tick={{ fontSize: 8 }} angle={-20} textAnchor="end" />
            <YAxis tick={{ fontSize: 9 }} unit="H" />
            <RcTooltip formatter={(v: number, n) => [`${v.toFixed(1)} HR`, n]} />
            <Legend iconSize={8} wrapperStyle={{ fontSize: 10 }} />
            {CATEGORIES.map(c => <Bar key={c} dataKey={c} stackId="a" fill={CATEGORY_COLORS[c]} />)}
          </BarChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  function SourceCard() {
    const raw  = stats?.source_breakdown ?? []
    const data = raw.map(s => ({ name: s.label, value: s.hours, pct: s.pct }))
    const srcC = Object.values(SOURCE_PIE_COLORS)
    return (
      <Card size="small"
        title={<Text strong>🏢 來源別工時</Text>}
        extra={<Text type="secondary" style={{ fontSize: 11 }}>各單位負荷</Text>}
        style={{ height: '100%' }}
      >
        {!data.length
          ? <Text type="secondary">暫無資料</Text>
          : (
            <>
              <DonutChart data={data} colors={srcC} />
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                {raw.map((s, i) => (
                  <Tooltip key={s.source} title={`${s.cases} 筆 · ${s.persons} 人 · 主項：${s.top_category}`}>
                    <Tag color="default" style={{ cursor: 'pointer', fontSize: 11 }}>
                      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                        background: srcC[i % srcC.length], marginRight: 4 }} />
                      {s.label} {s.pct}%
                    </Tag>
                  </Tooltip>
                ))}
              </div>
            </>
          )
        }
      </Card>
    )
  }

  function ConcentrationCard() {
    if (!conc) return null
    const bars = [
      { label: '前 3 人', pct: conc.top3_pct,  warn: conc.top3_pct > 50,  danger: conc.top3_pct > 70 },
      { label: '前 5 人', pct: conc.top5_pct,  warn: conc.top5_pct > 65,  danger: conc.top5_pct > 80 },
      { label: '前 10 人', pct: conc.top10_pct, warn: conc.top10_pct > 85, danger: false },
    ]
    return (
      <Card size="small"
        title={
          <Space>
            <Text strong>🔍 人力集中度</Text>
            {conc.is_concentrated && <WarningOutlined style={{ color: T.danger }} />}
          </Space>
        }
        extra={<Text type="secondary" style={{ fontSize: 11 }}>{conc.total_persons} 位人員</Text>}
        style={{ borderTop: `3px solid ${conc.is_concentrated ? T.danger : T.success}`, height: '100%' }}
      >
        {bars.map(b => {
          const strokeColor = b.danger ? T.danger : b.warn ? T.warning : T.success
          return (
            <div key={b.label} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <Text style={{ fontSize: 12 }}>{b.label}</Text>
                <Text strong style={{ fontSize: 13, color: strokeColor }}>{b.pct}%</Text>
              </div>
              <Progress percent={b.pct} strokeColor={strokeColor} showInfo={false} size="small" />
            </div>
          )
        })}
        {conc.is_concentrated && (
          <div style={{ color: T.danger, fontSize: 11, marginTop: 4, background: '#fff1f0',
            border: '1px solid #ffccc7', borderRadius: 4, padding: '4px 8px' }}>
            ⚠️ 人力高度集中，前 3 人工時 &gt; 70%
          </div>
        )}
      </Card>
    )
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 第三層：表格
  // ════════════════════════════════════════════════════════════════════════════
  type HoursTableRow = HoursRow & { key: number }

  function renderHr(v: number) {
    return <span style={{ fontSize: 11, textAlign: 'right', display: 'block' }}>
      {v > 0 ? v.toFixed(1) : '–'}
    </span>
  }
  function renderCat(val: string) {
    if (val === 'TOTAL') return <Text strong style={{ color: T.primary }}>TOTAL</Text>
    return <Tag color={CATEGORY_TAG_COLORS[val] ?? 'default'} style={{ fontSize: 10 }}>{val}</Tag>
  }

  function DailyTable() {
    const daily = stats?.daily_hours
    if (!daily || !daily.days.length) return (
      <Text type="secondary" style={{ fontSize: 12 }}>請選擇月份（非全年）以查看每日累計</Text>
    )
    const cols: ColumnsType<HoursTableRow> = [
      { title: '類別', dataIndex: 'category', fixed: 'left', width: 100, render: renderCat },
      ...daily.days.map((d, i) => ({
        title: (
          <div style={{ textAlign: 'center' as const }}>
            <div style={{ fontSize: 9 }}>{d}</div>
            <div style={{ fontSize: 8, color: T.textMuted }}>{daily.weekdays[i]}</div>
          </div>
        ),
        key: `d${d}`, width: 36, align: 'right' as const,
        render: (_: unknown, r: HoursTableRow) => renderHr(r.hours[i] ?? 0),
      })),
      {
        title: 'TOTAL', dataIndex: 'total', key: 'tot', width: 58, align: 'right' as const,
        sorter: (a: HoursTableRow, b: HoursTableRow) => a.total - b.total,
        render: (v: number, r: HoursTableRow) =>
          <Text strong style={{ color: r.category === 'TOTAL' ? T.primary : undefined }}>{v.toFixed(1)}</Text>,
      },
      {
        title: '%', dataIndex: 'pct', key: 'pct', width: 50, align: 'right' as const,
        render: (v: number, r: HoursTableRow) =>
          <Text style={{ color: r.category === 'TOTAL' ? T.textMuted : T.warning,
            fontWeight: r.category !== 'TOTAL' ? 600 : 400 }}>{v.toFixed(1)}%</Text>,
      },
    ]
    return (
      <Table<HoursTableRow>
        dataSource={daily.rows.map((r, i) => ({ ...r, key: i }))}
        columns={cols}
        pagination={false}
        size="small"
        scroll={{ x: 'max-content' }}
        rowClassName={r => r.category === 'TOTAL' ? 'exec-total-row' : ''}
      />
    )
  }

  function MonthlyTable() {
    const monthly = stats?.monthly_hours
    const cols: ColumnsType<HoursTableRow> = [
      { title: '類別', dataIndex: 'category', fixed: 'left', width: 100, render: renderCat },
      ...Array.from({ length: 12 }, (_, i) => {
        const m = i + 1
        const isFuture = year > thisYear || (year === thisYear && m > thisMonth)
        return {
          title: <span style={{ fontSize: 10 }}>{m}月</span>,
          key: `m${m}`, width: 56, align: 'right' as const,
          render: (_: unknown, r: HoursTableRow) => isFuture
            ? <span style={{ color: '#ccc', fontSize: 11 }}>—</span>
            : renderHr(r.hours[i] ?? 0),
        }
      }),
      {
        title: 'TOTAL', dataIndex: 'total', key: 'tot', width: 62, align: 'right' as const,
        sorter: (a: HoursTableRow, b: HoursTableRow) => a.total - b.total,
        render: (v: number, r: HoursTableRow) =>
          <Text strong style={{ color: r.category === 'TOTAL' ? T.primary : undefined }}>{v.toFixed(1)}</Text>,
      },
      {
        title: '%', dataIndex: 'pct', key: 'pct', width: 54, align: 'right' as const,
        render: (v: number, r: HoursTableRow) =>
          <Text style={{ color: r.category === 'TOTAL' ? T.textMuted : T.warning,
            fontWeight: r.category !== 'TOTAL' ? 600 : 400 }}>{v.toFixed(1)}%</Text>,
      },
    ]
    return (
      <Table<HoursTableRow>
        dataSource={(monthly?.rows ?? []).map((r, i) => ({ ...r, key: i }))}
        columns={cols}
        pagination={false}
        size="small"
        scroll={{ x: 'max-content' }}
        rowClassName={r => r.category === 'TOTAL' ? 'exec-total-row' : ''}
      />
    )
  }

  type PersonHRow = PersonHoursRow & { key: number }
  function PersonTable() {
    const ph = stats?.person_hours
    if (!ph || !ph.persons.length) return <Text type="secondary">暫無人員工時資料</Text>
    const cols: ColumnsType<PersonHRow> = [
      { title: '類別', dataIndex: 'category', fixed: 'left', width: 100, render: renderCat },
      ...ph.persons.map((p, i) => ({
        title: <span style={{ fontSize: 10 }}>{p}</span>,
        key: `p${i}`, width: 70, align: 'right' as const,
        render: (_: unknown, r: PersonHRow) => {
          const v = r.pct_by_person[i] ?? 0
          const c = v >= 30 ? T.danger : v >= 15 ? T.warning : v > 0 ? T.success : T.textMuted
          return <span style={{ fontSize: 11, color: c, fontWeight: v >= 15 ? 700 : 400 }}>
            {v > 0 ? `${v.toFixed(1)}%` : '–'}
          </span>
        },
      })),
    ]
    return (
      <Table<PersonHRow>
        dataSource={ph.rows.map((r, i) => ({ ...r, key: i }))}
        columns={cols}
        pagination={false}
        size="small"
        scroll={{ x: 'max-content' }}
      />
    )
  }

  function RankingTable() {
    return (
      <Table<PersonRankingItem & { key: number }>
        dataSource={(stats?.person_ranking ?? []).map((r, i) => ({ ...r, key: i }))}
        columns={[
          { title: '#', dataIndex: 'rank', width: 44, align: 'center' as const,
            render: (v: number) => <Text strong style={{ color: T.primary }}>{v}</Text> },
          { title: '人員', dataIndex: 'person', width: 88 },
          { title: 'HR', dataIndex: 'hours', width: 72, align: 'right' as const,
            sorter: (a, b) => a.hours - b.hours, defaultSortOrder: 'descend' as const,
            render: (v: number) => <Text strong>{v.toFixed(1)}</Text> },
          { title: '占比', dataIndex: 'pct', width: 62, align: 'right' as const,
            render: (v: number) => <Text style={{ color: T.warning, fontWeight: 600 }}>{v}%</Text> },
          { title: '主要類別', dataIndex: 'top_category', width: 90,
            render: (v: string) => <Tag color={CATEGORY_TAG_COLORS[v] ?? 'default'} style={{ fontSize: 10 }}>{v}</Tag> },
          { title: '來源', dataIndex: 'source_labels', width: 130,
            render: (v: string[]) => <Space size={2}>{v.map(s => <Tag key={s} style={{ fontSize: 9, margin: 0 }}>{s}</Tag>)}</Space> },
        ] as ColumnsType<PersonRankingItem & { key: number }>}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        size="small"
      />
    )
  }

  const collapseItems = [
    { key: 'daily',   label: '📅 每日累計工時表',   children: <DailyTable /> },
    { key: 'monthly', label: '📆 每月累計工時表',   children: <MonthlyTable /> },
    { key: 'person',  label: '🧑‍💼 人員工時佔比表', children: <PersonTable /> },
    { key: 'ranking', label: '🏆 人員排名詳細表',   children: <RankingTable /> },
  ]

  // ══════════════════════════════════════════════════════════════════════════
  // Render
  // ══════════════════════════════════════════════════════════════════════════
  return (
    <div>
      {/* TOTAL 列樣式 */}
      <style>{`.exec-total-row td { background: #fafafa !important; font-weight: 600; }`}</style>

      {/* Breadcrumb */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { href: '/dashboard', title: <HomeOutlined /> },
          { title: NAV_GROUP.luqun_repair },
          { title: NAV_PAGE.execDashboard },
        ]}
      />

      {/* 標題 */}
      <div style={{ marginBottom: 14 }}>
        <Title level={4} style={{ margin: 0 }}>
          <FundOutlined style={{ marginRight: 8, color: T.primary }} />
          {NAV_PAGE.execDashboard}
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          樂群工務 · 大直工務 · 房務保養 — 整合工時決策分析
        </Text>
      </div>

      {/* 篩選列 */}
      <FilterBar />

      <Spin spinning={loading}>
        {/* 決策提示 */}
        <AlertBar alerts={alerts} />

        {/* ─ 第一層 KPI ─ */}
        <Divider orientation="left" plain style={{ fontSize: 12, color: T.textMuted, margin: '4px 0 12px' }}>
          主管指標
        </Divider>
        <HeroLayer />
        <SourceCards />

        {/* ─ 第二層 圖表 ─ */}
        <Divider orientation="left" plain style={{ fontSize: 12, color: T.textMuted, margin: '8px 0 12px' }}>
          決策圖表
        </Divider>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 12, marginBottom: 16 }}>
          <TrendCard />
          <CatDonutCard />
          <PersonBarCard />
          <MatrixCard />
          <SourceCard />
          <ConcentrationCard />
        </div>

        {/* ─ 第三層 表格 ─ */}
        <Divider orientation="left" plain style={{ fontSize: 12, color: T.textMuted, margin: '8px 0 12px' }}>
          明細分析（可收合）
        </Divider>
        <Collapse defaultActiveKey={['daily', 'monthly', 'person', 'ranking']} items={collapseItems} />
      </Spin>
    </div>
  )
}
