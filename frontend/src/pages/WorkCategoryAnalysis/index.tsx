/**
 * ★工項類別分析 — 主管決策 Dashboard  (v2)
 *
 * 三層架構：
 *   第一層 KPI Cards  — 主管 10 秒掌握全局
 *   第二層 Charts     — 決策分析圖表
 *   第三層 Tables     — 每日/每月/人員明細表
 *
 * 資料整合：樂群工務 + 大直工務 + 房務保養
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Statistic, Typography, Breadcrumb,
  Select, Spin, Alert, Tabs, Table, Tag, Space, Badge,
  Progress, Divider, Tooltip,
} from 'antd'
import {
  HomeOutlined, BarChartOutlined, ArrowUpOutlined, ArrowDownOutlined,
  TeamOutlined, ClockCircleOutlined, WarningOutlined, TrophyOutlined,
  PieChartOutlined, LineChartOutlined, TableOutlined,
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
  CATEGORIES, SOURCE_LABELS, CATEGORY_COLORS, CATEGORY_TAG_COLORS, SOURCE_COLORS,
  type CategoryStats, type PersonRankingItem, type HoursRow, type PersonHoursRow,
} from '@/api/workCategoryAnalysis'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography
const { Option } = Select

// ── 常數 ──────────────────────────────────────────────────────────────────────
const MONTHS     = Array.from({ length: 12 }, (_, i) => i + 1)
const PIE_COLORS = ['#4BA8E8', '#52C41A', '#FF4D4F', '#FA8C16', '#722ED1']
const SOURCE_OPTIONS = [
  { value: 'all',        label: '全部來源' },
  { value: 'luqun',      label: '樂群工務' },
  { value: 'dazhi',      label: '大直工務' },
  { value: 'hotel_room', label: '房務保養' },
]

// ── 共用渲染 ───────────────────────────────────────────────────────────────────
function renderCategory(val: string) {
  if (val === 'TOTAL') return <Text strong style={{ color: '#1B3A5C' }}>TOTAL</Text>
  return <Tag color={CATEGORY_TAG_COLORS[val] ?? 'default'} style={{ fontSize: 11 }}>{val}</Tag>
}
function renderHour(v: number) {
  return <Text style={{ fontSize: 11, color: v > 0 ? '#1B3A5C' : '#ccc' }}>{v > 0 ? v.toFixed(1) : '-'}</Text>
}

// ── MoM 趨勢徽章 ──────────────────────────────────────────────────────────────
function MomBadge({ pct }: { pct: number | null }) {
  if (pct === null) return null
  const up = pct >= 0
  return (
    <Text style={{ fontSize: 12, color: up ? '#FF4D4F' : '#52C41A', marginLeft: 6 }}>
      {up ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
      {Math.abs(pct).toFixed(1)}%
    </Text>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// 主頁面
// ══════════════════════════════════════════════════════════════════════════════
export default function WorkCategoryAnalysisPage() {
  const thisYear  = dayjs().year()
  const thisMonth = dayjs().month() + 1

  // ── 篩選狀態 ──────────────────────────────────────────────────────────────
  const [years, setYears]       = useState<number[]>([])
  const [persons, setPersons]   = useState<string[]>([])
  const [year, setYear]         = useState<number>(thisYear)
  const [month, setMonth]       = useState<number>(thisMonth)
  const [sources, setSources]   = useState<string>('all')
  const [category, setCategory] = useState<string>('all')
  const [person, setPerson]     = useState<string>('all')

  // ── 資料狀態 ──────────────────────────────────────────────────────────────
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [stats, setStats]     = useState<CategoryStats | null>(null)

  // 載入年份
  useEffect(() => {
    fetchYears().then(r => {
      const ys = r.years.length ? r.years : [thisYear]
      setYears(ys)
    }).catch(() => setYears([thisYear]))
  }, [])  // eslint-disable-line

  // 載入人員清單（依 year + sources）
  useEffect(() => {
    fetchPersons(year, sources).then(r => setPersons(r.persons)).catch(() => {})
  }, [year, sources])

  // 載入主統計
  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const data = await fetchStats({ year, month, sources, category, person })
      setStats(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [year, month, sources, category, person])

  useEffect(() => { load() }, [load])

  const kpi   = stats?.kpi
  const conc  = stats?.concentration

  // ════════════════════════════════════════════════════════════════════════════
  // 第一層：KPI Cards
  // ════════════════════════════════════════════════════════════════════════════
  function KpiLayer() {
    if (!kpi) return null
    return (
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {/* 本月總工時 */}
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #1B3A5C' }}>
            <Statistic
              title={<Text style={{ fontSize: 11, color: '#888' }}>本期總工時</Text>}
              value={kpi.total_hours}
              suffix="HR"
              precision={1}
              valueStyle={{ fontSize: 22, color: '#1B3A5C', fontWeight: 700 }}
              prefix={<ClockCircleOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
            <MomBadge pct={kpi.mom_change_pct} />
          </Card>
        </Col>

        {/* 案件/工項數 */}
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #4BA8E8' }}>
            <Statistic
              title={<Text style={{ fontSize: 11, color: '#888' }}>案件/工項數</Text>}
              value={kpi.total_cases}
              suffix="筆"
              valueStyle={{ fontSize: 22, fontWeight: 700 }}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>{kpi.total_persons} 位人員</Text>
          </Card>
        </Col>

        {/* 平均人工時 */}
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #52C41A' }}>
            <Statistic
              title={<Text style={{ fontSize: 11, color: '#888' }}>平均人工時</Text>}
              value={kpi.avg_person_hours}
              suffix="HR"
              precision={1}
              valueStyle={{ fontSize: 22, fontWeight: 700, color: '#52C41A' }}
              prefix={<TeamOutlined style={{ fontSize: 14, marginRight: 4 }} />}
            />
          </Card>
        </Col>

        {/* 工時最高類別 */}
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #FA8C16' }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>工時最高類別</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <Tag color={CATEGORY_TAG_COLORS[kpi.top_category.name] ?? 'default'} style={{ fontSize: 12, margin: 0 }}>
                {kpi.top_category.name}
              </Tag>
              <Text strong style={{ fontSize: 18, color: '#FA8C16' }}>{kpi.top_category.pct}%</Text>
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>{kpi.top_category.hours} HR</Text>
          </Card>
        </Col>

        {/* 工時最高人員 */}
        <Col xs={12} sm={8} md={4}>
          <Card bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: '3px solid #722ED1' }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>工時最高人員</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
              <TrophyOutlined style={{ color: '#722ED1', fontSize: 14 }} />
              <Text strong style={{ fontSize: 16 }}>{kpi.top_person.name}</Text>
              <Text style={{ fontSize: 13, color: '#722ED1' }}>{kpi.top_person.pct}%</Text>
            </div>
            <Text type="secondary" style={{ fontSize: 11 }}>{kpi.top_person.hours} HR</Text>
          </Card>
        </Col>

        {/* 集中度警示 */}
        <Col xs={12} sm={8} md={4}>
          <Card
            bodyStyle={{ padding: '14px 16px' }}
            style={{ borderLeft: `3px solid ${conc?.is_concentrated ? '#FF4D4F' : '#52C41A'}` }}
          >
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>
              人力集中度
              {conc?.is_concentrated && (
                <Tooltip title="前 3 人工時佔比 > 70%，建議分散人力風險">
                  <WarningOutlined style={{ color: '#FF4D4F', marginLeft: 4 }} />
                </Tooltip>
              )}
            </div>
            <Text strong style={{ fontSize: 18, color: conc?.is_concentrated ? '#FF4D4F' : '#52C41A' }}>
              前3人 {conc?.top3_pct ?? 0}%
            </Text>
            <div style={{ marginTop: 4 }}>
              <Progress
                percent={conc?.top3_pct ?? 0}
                showInfo={false}
                strokeColor={conc?.is_concentrated ? '#FF4D4F' : '#52C41A'}
                size="small"
              />
            </div>
          </Card>
        </Col>
      </Row>
    )
  }

  // ── 來源卡片（KPI 延伸）────────────────────────────────────────────────────
  function SourceCards() {
    if (!kpi?.source_breakdown.length) return null
    return (
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {kpi.source_breakdown.map(s => (
          <Col key={s.source} xs={8} md={4}>
            <Card
              bodyStyle={{ padding: '10px 14px' }}
              style={{ borderLeft: `3px solid ${SOURCE_COLORS[s.source] ?? '#999'}` }}
            >
              <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>{s.label}</div>
              <Text strong style={{ fontSize: 16 }}>{s.hours} HR</Text>
              <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>{s.pct}%</Text>
            </Card>
          </Col>
        ))}
      </Row>
    )
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 第二層：圖表
  // ════════════════════════════════════════════════════════════════════════════

  // A. 類別趨勢折線圖
  function TrendChart() {
    const data = stats?.chart_data ?? []
    return (
      <Card
        title={<><LineChartOutlined /> 工項類別時數趨勢</>}
        extra={<Text type="secondary" style={{ fontSize: 12 }}>{month === 0 ? '全年月趨勢' : `${month}月日趨勢`}</Text>}
        style={{ marginBottom: 12 }}
        bodyStyle={{ padding: '12px 8px' }}
      >
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data} margin={{ top: 4, right: 20, left: -10, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} unit="H" />
            <RcTooltip formatter={(v: number) => [`${v.toFixed(1)} HR`]} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
            {CATEGORIES.map(c => (
              <Line key={c} type="monotone" dataKey={c} stroke={CATEGORY_COLORS[c]}
                strokeWidth={2} dot={false} activeDot={{ r: 3 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  // B. 類別占比圓餅圖
  function CategoryPieChart() {
    const data = (stats?.category_breakdown ?? []).filter(d => d.value > 0)
    return (
      <Card
        title={<><PieChartOutlined /> 類別工時占比</>}
        style={{ marginBottom: 12 }}
        bodyStyle={{ padding: '8px' }}
      >
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" cx="40%" cy="50%"
              outerRadius={75} label={({ name, pct }) => `${name} ${pct}%`}
              labelLine={false}
            >
              {data.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
            </Pie>
            <RcTooltip formatter={(v: number, name) => [`${v.toFixed(1)} HR`, name]} />
          </PieChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  // C. 人員工時排名（橫向 Bar）
  function PersonRankingChart() {
    const data = (stats?.person_ranking ?? []).slice(0, 12).reverse()
    if (!data.length) return (
      <Card title={<><TeamOutlined /> 人員工時排名</>} style={{ marginBottom: 12 }}>
        <Alert message="暫無人員資料" type="info" showIcon />
      </Card>
    )
    return (
      <Card
        title={<><TeamOutlined /> 人員工時排名</>}
        extra={<Text type="secondary" style={{ fontSize: 11 }}>整合三來源 · 前12名</Text>}
        style={{ marginBottom: 12 }}
        bodyStyle={{ padding: '8px' }}
      >
        <ResponsiveContainer width="100%" height={Math.max(200, data.length * 26)}>
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 40, left: 60, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10 }} unit="H" />
            <YAxis type="category" dataKey="person" tick={{ fontSize: 10 }} width={56} />
            <RcTooltip
              formatter={(v: number, _name, props) => {
                const item = props.payload
                return [`${v.toFixed(1)} HR (${item.pct}%)  ${item.top_category}`]
              }}
            />
            <Bar dataKey="hours" radius={[0, 4, 4, 0]}>
              {data.map((item: PersonRankingItem, i) => (
                <Cell key={i} fill={SOURCE_COLORS[item.sources?.[0] ?? 'luqun'] ?? '#4BA8E8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        {/* 來源圖例 */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 4 }}>
          {Object.entries(SOURCE_LABELS).map(([k, v]) => (
            <Space key={k} size={4}>
              <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: SOURCE_COLORS[k] }} />
              <Text style={{ fontSize: 11 }}>{v}</Text>
            </Space>
          ))}
        </div>
      </Card>
    )
  }

  // D. 類別 × 人員交叉（Stacked Bar）
  function CategoryPersonMatrix() {
    const data = (stats?.category_person_matrix ?? []).slice(0, 10)
    if (!data.length) return null
    return (
      <Card
        title={<><BarChartOutlined /> 類別 × 人員交叉分析</>}
        extra={<Text type="secondary" style={{ fontSize: 11 }}>各人員工時分布</Text>}
        style={{ marginBottom: 12 }}
        bodyStyle={{ padding: '8px' }}
      >
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 4, right: 20, left: -10, bottom: 30 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="person" tick={{ fontSize: 9 }} angle={-25} textAnchor="end" />
            <YAxis tick={{ fontSize: 10 }} unit="H" />
            <RcTooltip formatter={(v: number, name) => [`${v.toFixed(1)} HR`, name]} />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 10 }} />
            {CATEGORIES.map(c => (
              <Bar key={c} dataKey={c} stackId="a" fill={CATEGORY_COLORS[c]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </Card>
    )
  }

  // E. 來源別分析
  function SourceBreakdown() {
    const data = stats?.source_breakdown ?? []
    if (!data.length) return null
    return (
      <Card
        title="來源別工時分析"
        style={{ marginBottom: 12 }}
        bodyStyle={{ padding: '12px 16px' }}
      >
        {data.map(s => (
          <div key={s.source} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Space>
                <span style={{
                  display: 'inline-block', width: 10, height: 10, borderRadius: 2,
                  background: SOURCE_COLORS[s.source],
                }} />
                <Text strong>{s.label}</Text>
                <Tag color="default" style={{ fontSize: 10 }}>{s.top_category}</Tag>
              </Space>
              <Text>
                <Text strong>{s.hours}</Text>
                <Text type="secondary" style={{ fontSize: 11 }}> HR · {s.pct}% · {s.persons}人</Text>
              </Text>
            </div>
            <Progress
              percent={s.pct}
              strokeColor={SOURCE_COLORS[s.source]}
              showInfo={false}
              size="small"
            />
          </div>
        ))}
      </Card>
    )
  }

  // F. 人力集中度
  function ConcentrationCard() {
    if (!conc) return null
    const { top3_pct, top5_pct, top10_pct, total_persons, is_concentrated } = conc
    return (
      <Card
        title={
          <>
            人力負載集中度
            {is_concentrated && (
              <Badge dot style={{ marginLeft: 6 }}>
                <WarningOutlined style={{ color: '#FF4D4F', fontSize: 14 }} />
              </Badge>
            )}
          </>
        }
        bodyStyle={{ padding: '12px 16px' }}
        style={{ borderTop: `3px solid ${is_concentrated ? '#FF4D4F' : '#52C41A'}` }}
      >
        {is_concentrated && (
          <Alert
            message="人力集中度偏高：前 3 人工時超過 70%，建議分散人力風險"
            type="warning"
            showIcon
            style={{ marginBottom: 12, fontSize: 12 }}
          />
        )}
        {[['前 3 人', top3_pct], ['前 5 人', top5_pct], ['前 10 人', top10_pct]].map(([label, pct]) => (
          <div key={label as string} style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
              <Text style={{ fontSize: 12 }}>{label}</Text>
              <Text strong style={{ fontSize: 12, color: (pct as number) > 70 ? '#FF4D4F' : '#333' }}>{pct}%</Text>
            </div>
            <Progress
              percent={pct as number}
              strokeColor={(pct as number) > 70 ? '#FF4D4F' : '#FA8C16'}
              showInfo={false}
              size="small"
            />
          </div>
        ))}
        <Text type="secondary" style={{ fontSize: 11 }}>共 {total_persons} 位人員</Text>
      </Card>
    )
  }

  // ════════════════════════════════════════════════════════════════════════════
  // 第三層：表格
  // ════════════════════════════════════════════════════════════════════════════

  // 每日累計
  type DailyRow = HoursRow & { key: number }
  function buildDailyCols() {
    const { days = [], weekdays = [] } = stats?.daily_hours ?? {}
    return [
      {
        title: '工項類別', dataIndex: 'category', fixed: 'left' as const, width: 100,
        render: renderCategory,
      },
      ...days.map((d, i) => ({
        title: (
          <div style={{ textAlign: 'center' as const, lineHeight: 1.2 }}>
            <div style={{ fontSize: 10 }}>{d}</div>
            <div style={{ fontSize: 9, color: '#888' }}>{weekdays[i]}</div>
          </div>
        ),
        key: `d${d}`, width: 38, align: 'center' as const,
        render: (_: unknown, row: DailyRow) => renderHour(row.hours[i] ?? 0),
      })),
      {
        title: 'TOTAL', dataIndex: 'total', key: 'total', width: 60, align: 'center' as const,
        render: (v: number, row: DailyRow) => (
          <Text strong style={{ color: row.category === 'TOTAL' ? '#1B3A5C' : '#333' }}>{v.toFixed(1)}</Text>
        ),
      },
      {
        title: '%', dataIndex: 'pct', key: 'pct', width: 52, align: 'center' as const,
        render: (v: number, row: DailyRow) => (
          <Text style={{ color: row.category === 'TOTAL' ? '#888' : '#FA8C16', fontWeight: row.category !== 'TOTAL' ? 600 : 400 }}>
            {v.toFixed(1)}%
          </Text>
        ),
      },
    ] as ColumnsType<DailyRow>
  }

  // 每月累計
  type MonthlyRow = HoursRow & { key: number }
  const monthlyCols: ColumnsType<MonthlyRow> = [
    { title: '工項類別', dataIndex: 'category', fixed: 'left', width: 100, render: renderCategory },
    ...Array.from({ length: 12 }, (_, i) => {
      const m = i + 1
      const isFuture = year > thisYear || (year === thisYear && m > thisMonth)
      return {
        title: `${m}月`, key: `m${m}`, width: 58, align: 'center' as const,
        render: (_: unknown, row: MonthlyRow) => isFuture
          ? <Text style={{ color: '#ccc', fontSize: 11 }}>—</Text>
          : renderHour(row.hours[i] ?? 0),
      }
    }),
    {
      title: 'TOTAL', dataIndex: 'total', key: 'total', width: 64, align: 'center' as const,
      render: (v: number, row: MonthlyRow) => (
        <Text strong style={{ color: row.category === 'TOTAL' ? '#1B3A5C' : '#333' }}>{v.toFixed(1)}</Text>
      ),
    },
    {
      title: '%', dataIndex: 'pct', key: 'pct', width: 56, align: 'center' as const,
      render: (v: number, row: MonthlyRow) => (
        <Text style={{ color: row.category === 'TOTAL' ? '#888' : '#FA8C16', fontWeight: row.category !== 'TOTAL' ? 600 : 400 }}>
          {v.toFixed(1)}%
        </Text>
      ),
    },
  ]

  // 人員% 表
  type PersonHRow = PersonHoursRow & { key: number }
  function buildPersonCols(ps: string[]) {
    return [
      { title: '工項類別', dataIndex: 'category', fixed: 'left' as const, width: 100, render: renderCategory },
      ...ps.map((p, i) => ({
        title: <Text style={{ fontSize: 11 }}>{p}</Text>,
        key: `p${i}`, width: 72, align: 'center' as const,
        render: (_: unknown, row: PersonHRow) => {
          const v = row.pct_by_person[i] ?? 0
          const c = v >= 30 ? '#FF4D4F' : v >= 15 ? '#FA8C16' : v > 0 ? '#52C41A' : '#ccc'
          return <Text style={{ fontSize: 11, color: c, fontWeight: v >= 15 ? 600 : 400 }}>{v > 0 ? `${v.toFixed(1)}%` : '-'}</Text>
        },
      })),
    ] as ColumnsType<PersonHRow>
  }

  const daily   = stats?.daily_hours
  const monthly = stats?.monthly_hours
  const ph      = stats?.person_hours

  // ── Tab 設定 ───────────────────────────────────────────────────────────────
  const tabItems = [
    {
      key: 'dashboard',
      label: <><LineChartOutlined /> Dashboard</>,
      children: (
        <>
          <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>
            主管摘要
          </Divider>
          <KpiLayer />
          <SourceCards />

          <Divider orientation="left" plain style={{ fontSize: 13, color: '#888', margin: '4px 0 12px' }}>
            決策分析圖表
          </Divider>
          <Row gutter={[12, 12]}>
            <Col xs={24} lg={14}><TrendChart /></Col>
            <Col xs={24} lg={10}><CategoryPieChart /></Col>
          </Row>
          <Row gutter={[12, 12]}>
            <Col xs={24} lg={12}><PersonRankingChart /></Col>
            <Col xs={24} lg={12}><CategoryPersonMatrix /></Col>
          </Row>
          <Row gutter={[12, 12]}>
            <Col xs={24} sm={12}><SourceBreakdown /></Col>
            <Col xs={24} sm={12}><ConcentrationCard /></Col>
          </Row>
        </>
      ),
    },
    {
      key: 'daily',
      label: <><TableOutlined /> B. 每日累計</>,
      children: (
        (!daily || !daily.days.length) ? (
          <Alert message="請選擇月份（非全年）以查看每日累計工時" type="info" showIcon style={{ marginTop: 8 }} />
        ) : (
          <Card
            title={<Text strong>每日累計工時 (HR)</Text>}
            extra={<Text type="secondary">{year} 年 {month} 月</Text>}
            bodyStyle={{ padding: '6px 0' }}
          >
            <Table<DailyRow>
              dataSource={(daily.rows ?? []).map((r, i) => ({ ...r, key: i }))}
              columns={buildDailyCols()}
              pagination={false} size="small" scroll={{ x: 'max-content' }}
              rowClassName={r => r.category === 'TOTAL' ? 'wca-total-row' : ''}
            />
          </Card>
        )
      ),
    },
    {
      key: 'monthly',
      label: <><TableOutlined /> C. 每月累計</>,
      children: (
        <Card
          title={<Text strong>每月累計工時 (HR)</Text>}
          extra={<Text type="secondary">{year} 年</Text>}
          bodyStyle={{ padding: '6px 0' }}
        >
          <Table<MonthlyRow>
            dataSource={(monthly?.rows ?? []).map((r, i) => ({ ...r, key: i }))}
            columns={monthlyCols}
            pagination={false} size="small" scroll={{ x: 'max-content' }}
            rowClassName={r => r.category === 'TOTAL' ? 'wca-total-row' : ''}
          />
        </Card>
      ),
    },
    {
      key: 'person',
      label: <><TableOutlined /> D. 人員工時%</>,
      children: (
        (!ph || !ph.persons.length) ? (
          <Alert message="暫無人員工時資料" type="info" showIcon style={{ marginTop: 8 }} />
        ) : (
          <Card
            title={<Text strong>人員工時佔比 (%)</Text>}
            extra={<Text type="secondary">各工項類別 · {ph.persons.length} 位人員</Text>}
            bodyStyle={{ padding: '6px 0' }}
          >
            <Table<PersonHRow>
              dataSource={ph.rows.map((r, i) => ({ ...r, key: i }))}
              columns={buildPersonCols(ph.persons)}
              pagination={false} size="small" scroll={{ x: 'max-content' }}
            />
          </Card>
        )
      ),
    },
    // 人員排名詳細表
    {
      key: 'ranking',
      label: <><TrophyOutlined /> 人員排名</>,
      children: (
        <Card title={<Text strong>人員工時排名</Text>} bodyStyle={{ padding: '6px 0' }}>
          <Table<PersonRankingItem & { key: number }>
            dataSource={(stats?.person_ranking ?? []).map((r, i) => ({ ...r, key: i }))}
            columns={[
              { title: '排名', dataIndex: 'rank', width: 50, align: 'center' as const,
                render: (v: number) => <Text strong>{v}</Text> },
              { title: '人員', dataIndex: 'person', width: 90 },
              { title: '工時(HR)', dataIndex: 'hours', width: 80, align: 'right' as const,
                render: (v: number) => <Text strong style={{ color: '#1B3A5C' }}>{v.toFixed(1)}</Text>,
                sorter: (a, b) => a.hours - b.hours },
              { title: '占比%', dataIndex: 'pct', width: 70, align: 'center' as const,
                render: (v: number) => <Text style={{ color: '#FA8C16', fontWeight: 600 }}>{v}%</Text> },
              { title: '主要類別', dataIndex: 'top_category', width: 90,
                render: (v: string) => <Tag color={CATEGORY_TAG_COLORS[v] ?? 'default'} style={{ fontSize: 11 }}>{v}</Tag> },
              { title: '來源', dataIndex: 'source_labels', width: 130,
                render: (v: string[]) => <>{v.map(s => <Tag key={s} style={{ fontSize: 10 }}>{s}</Tag>)}</> },
            ] as ColumnsType<PersonRankingItem & { key: number }>}
            pagination={{ pageSize: 20, showSizeChanger: false }}
            size="small"
          />
        </Card>
      ),
    },
  ]

  // ══════════════════════════════════════════════════════════════════════════
  // Render
  // ══════════════════════════════════════════════════════════════════════════
  return (
    <div>
      <style>{`.wca-total-row td { background: #f5f5f5 !important; font-weight: 600; }`}</style>

      {/* Breadcrumb */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { href: '/dashboard', title: <HomeOutlined /> },
          { title: NAV_GROUP.luqun_repair },
          { title: NAV_PAGE.workCategoryAnalysis },
        ]}
      />

      {/* 標題 + 篩選列 */}
      <Card bodyStyle={{ padding: '12px 16px' }} style={{ marginBottom: 12 }}>
        <Row justify="space-between" align="middle" gutter={[0, 8]}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>★ {NAV_PAGE.workCategoryAnalysis}</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              樂群工務 + 大直工務 + 房務保養 · 主管決策 Dashboard
            </Text>
          </Col>
          <Col>
            <Space wrap>
              {/* 年度 */}
              <Select value={year} onChange={setYear} style={{ width: 82 }} size="small">
                {years.map(y => <Option key={y} value={y}>{y}</Option>)}
              </Select>
              {/* 月份 */}
              <Select value={month} onChange={setMonth} style={{ width: 78 }} size="small">
                <Option value={0}>全年</Option>
                {MONTHS.map(m => <Option key={m} value={m}>{m}月</Option>)}
              </Select>
              {/* 來源 */}
              <Select value={sources} onChange={v => { setSources(v); setPerson('all') }} style={{ width: 100 }} size="small">
                {SOURCE_OPTIONS.map(o => <Option key={o.value} value={o.value}>{o.label}</Option>)}
              </Select>
              {/* 類別 */}
              <Select value={category} onChange={setCategory} style={{ width: 90 }} size="small">
                <Option value="all">全部類別</Option>
                {CATEGORIES.map(c => <Option key={c} value={c}>{c}</Option>)}
              </Select>
              {/* 人員 */}
              <Select value={person} onChange={setPerson} style={{ width: 90 }} size="small" showSearch>
                <Option value="all">全部人員</Option>
                {persons.map(p => <Option key={p} value={p}>{p}</Option>)}
              </Select>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 類別圖例 */}
      <Row gutter={8} style={{ marginBottom: 10 }}>
        {CATEGORIES.map(cat => (
          <Col key={cat}><Tag color={CATEGORY_TAG_COLORS[cat]}>{cat}</Tag></Col>
        ))}
      </Row>

      {/* 錯誤提示 */}
      {error && <Alert message={error} type="error" style={{ marginBottom: 12 }} />}

      {/* 主體 */}
      <Spin spinning={loading}>
        <Tabs items={tabItems} size="small"
          style={{ background: '#fff', padding: '0 12px 12px', borderRadius: 8 }} />
      </Spin>
    </div>
  )
}
