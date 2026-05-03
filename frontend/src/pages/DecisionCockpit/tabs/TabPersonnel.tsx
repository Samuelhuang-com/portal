/**
 * TAB E — 人員工時與效率
 * Phase 4：飯店 + 商場 Top 人員排行（年度統計）+ 月工時趨勢
 *
 * ⚠️  person-hours API 為年度統計，月份篩選無效
 *     UI 標示「※ 人員排行為全年統計」
 *
 * API:
 *   - /api/v1/hotel/monthly-hours?year={year}
 *   - /api/v1/hotel/person-hours?year={year}
 *   - /api/v1/mall/monthly-hours?year={year}
 *   - /api/v1/mall/person-hours?year={year}
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Row, Spin, Alert, Tag, Typography, Divider, Space,
} from 'antd'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartTooltip, Legend, ResponsiveContainer,
  LineChart, Line,
} from 'recharts'
import { fetchHotelPersonHours, fetchHotelMonthlyHours } from '@/api/hotelOverview'
import { fetchMallPersonHours,  fetchMallMonthlyHours  } from '@/api/mallOverview'
import type { HotelPersonHoursData, HotelMonthlyHoursData } from '@/api/hotelOverview'
import type { MallPersonHoursData,  MallMonthlyHoursData  } from '@/api/mallOverview'

const { Title, Text } = Typography

const T = {
  primary:   '#1B3A5C',
  accent:    '#4BA8E8',
  bg:        '#f0f4f8',
  textMuted: '#8c8c8c',
}

const MONTH_NAMES = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

interface TabPersonnelProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface PersonnelState {
  loading:       boolean
  hotelPerson:   HotelPersonHoursData | null
  hotelMonthly:  HotelMonthlyHoursData | null
  mallPerson:    MallPersonHoursData | null
  mallMonthly:   MallMonthlyHoursData | null
}

// ── Top-10 人員橫向 Bar ───────────────────────────────────────────────────────
function PersonBarChart({ persons, totals, color, title }: {
  persons: string[]; totals: number[]; color: string; title: string
}) {
  const TOP = 10
  const paired = persons.map((p, i) => ({ name: p, hours: totals[i] ?? 0 }))
    .sort((a, b) => b.hours - a.hours)
    .slice(0, TOP)

  if (paired.length === 0) return (
    <div style={{ textAlign: 'center', padding: 24, color: T.textMuted, fontSize: 12 }}>無人員工時資料</div>
  )

  return (
    <div>
      <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 6 }}>
        {title}（{paired.length} 人，全年合計工時 hr）
      </div>
      <ResponsiveContainer width="100%" height={Math.max(160, paired.length * 24)}>
        <BarChart data={paired} layout="vertical" margin={{ top: 0, right: 40, left: 60, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10 }} unit="hr" />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={55} />
          <RechartTooltip formatter={(v: number) => [`${v.toFixed(1)} hr`]} contentStyle={{ fontSize: 11 }} />
          <Bar dataKey="hours" fill={color} radius={[0, 3, 3, 0]} name="工時" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── 月工時趨勢折線 ────────────────────────────────────────────────────────────
function MonthlyTrendChart({ data, color, title }: {
  data: Array<{ month: number; total: number }>; color: string; title: string
}) {
  if (data.length === 0) return (
    <div style={{ textAlign: 'center', padding: 16, color: T.textMuted, fontSize: 12 }}>無月工時資料</div>
  )
  const chartData = data.map(d => ({ name: MONTH_NAMES[d.month - 1], total: d.total }))
  return (
    <div>
      <div style={{ fontSize: 12, color: T.textMuted, marginBottom: 6 }}>{title}</div>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 9 }} />
          <YAxis tick={{ fontSize: 9 }} unit="hr" />
          <RechartTooltip formatter={(v: number) => [`${v.toFixed(1)} hr`]} contentStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="total" stroke={color} strokeWidth={2} dot={{ r: 3 }} name="工時" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════════════
// 主元件
// ════════════════════════════════════════════════════════════════════════════
export default function TabPersonnel({ year, month, monthStr, refreshKey }: TabPersonnelProps) {
  const [st, setSt] = useState<PersonnelState>({
    loading: true, hotelPerson: null, hotelMonthly: null, mallPerson: null, mallMonthly: null,
  })

  const load = useCallback(async () => {
    setSt(s => ({ ...s, loading: true }))
    const [r1, r2, r3, r4] = await Promise.allSettled([
      fetchHotelPersonHours(year),
      fetchHotelMonthlyHours(year),
      fetchMallPersonHours(year),
      fetchMallMonthlyHours(year),
    ])
    setSt({
      loading:      false,
      hotelPerson:  r1.status === 'fulfilled' ? r1.value : null,
      hotelMonthly: r2.status === 'fulfilled' ? r2.value : null,
      mallPerson:   r3.status === 'fulfilled' ? r3.value : null,
      mallMonthly:  r4.status === 'fulfilled' ? r4.value : null,
    })
  }, [year, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const { loading, hotelPerson, hotelMonthly, mallPerson, mallMonthly } = st

  // 彙總月工時（各來源相加）
  const hotelMonthlyTotal = hotelMonthly?.months.map((m, i) => ({
    month: m,
    total: Math.round((hotelMonthly.rows.reduce((s, r) => s + (r.hours[i] ?? 0), 0)) * 10) / 10,
  })) ?? []

  const mallMonthlyTotal = mallMonthly?.months.map((m, i) => ({
    month: m,
    total: Math.round((mallMonthly.rows.reduce((s, r) => s + (r.hours[i] ?? 0), 0)) * 10) / 10,
  })) ?? []

  if (loading) return (
    <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  )

  return (
    <div style={{ paddingBottom: 24 }}>

      {/* 說明提示 */}
      <Alert
        type="info"
        showIcon
        message={`E. 人員工時與效率 — ${year} 年度統計`}
        description={`※ 人員排行為全年統計（${year} 年），不受月份篩選（${monthStr}）影響。月工時趨勢同為全年度。`}
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[16, 16]}>

        {/* ── 飯店人員排行 ──────────────────────────────────────────────── */}
        <Col xs={24} lg={12}>
          <Card
            size="small"
            style={{ borderTop: `3px solid ${T.primary}` }}
            title={<Text strong style={{ color: T.primary }}>飯店人員工時排行 Top 10</Text>}
            bodyStyle={{ padding: 12 }}
          >
            {hotelPerson ? (
              <PersonBarChart
                persons={hotelPerson.persons}
                totals={hotelPerson.person_totals}
                color={T.primary}
                title="飯店 6 來源合計"
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 24, color: T.textMuted, fontSize: 12 }}>資料準備中</div>
            )}
          </Card>
        </Col>

        {/* ── 商場人員排行 ──────────────────────────────────────────────── */}
        <Col xs={24} lg={12}>
          <Card
            size="small"
            style={{ borderTop: `3px solid ${T.accent}` }}
            title={<Text strong style={{ color: T.accent }}>商場人員工時排行 Top 10</Text>}
            bodyStyle={{ padding: 12 }}
          >
            {mallPerson ? (
              <PersonBarChart
                persons={mallPerson.persons}
                totals={mallPerson.persons.map((_, i) =>
                  Math.round(mallPerson.rows.reduce((s, r) => s + (r.pct_by_person[i] ?? 0), 0) * 10) / 10
                )}
                color={T.accent}
                title="商場 5 工項合計工時佔比"
              />
            ) : (
              <div style={{ textAlign: 'center', padding: 24, color: T.textMuted, fontSize: 12 }}>資料準備中</div>
            )}
          </Card>
        </Col>

        {/* ── 月工時趨勢（飯店）──────────────────────────────────────────── */}
        <Col xs={24} lg={12}>
          <Card
            size="small"
            style={{ borderTop: `3px solid ${T.primary}` }}
            title={<Text strong style={{ color: T.primary }}>飯店月工時趨勢（{year} 年）</Text>}
            bodyStyle={{ padding: 12 }}
          >
            <MonthlyTrendChart
              data={hotelMonthlyTotal}
              color={T.primary}
              title="各月份合計工時（hr）"
            />
          </Card>
        </Col>

        {/* ── 月工時趨勢（商場）──────────────────────────────────────────── */}
        <Col xs={24} lg={12}>
          <Card
            size="small"
            style={{ borderTop: `3px solid ${T.accent}` }}
            title={<Text strong style={{ color: T.accent }}>商場月工時趨勢（{year} 年）</Text>}
            bodyStyle={{ padding: 12 }}
          >
            <MonthlyTrendChart
              data={mallMonthlyTotal}
              color={T.accent}
              title="各月份合計工時（hr）"
            />
          </Card>
        </Col>

      </Row>
    </div>
  )
}
