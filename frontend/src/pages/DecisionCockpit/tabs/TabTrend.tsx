/**
 * TAB G — 趨勢分析
 * Phase 5：日度趨勢折線 + 飯店/商場年度月工時趨勢
 *
 * API:
 *   - /api/v1/dashboard/trend?days=30   (日度完成率趨勢)
 *   - /api/v1/hotel/monthly-hours?year  (飯店月工時)
 *   - /api/v1/mall/monthly-hours?year   (商場月工時)
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Col, Row, Spin, Typography, Segmented,
} from 'antd'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartTooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { dashboardApi }            from '@/api/dashboard'
import { fetchHotelMonthlyHours }  from '@/api/hotelOverview'
import { fetchMallMonthlyHours }   from '@/api/mallOverview'
import type { DashboardTrend }     from '@/api/dashboard'
import type { HotelMonthlyHoursData } from '@/api/hotelOverview'
import type { MallMonthlyHoursData  } from '@/api/mallOverview'

const { Title, Text } = Typography

const T = {
  primary:   '#1B3A5C',
  accent:    '#4BA8E8',
  bg:        '#f0f4f8',
  textMuted: '#8c8c8c',
  success:   '#52c41a',
  warning:   '#faad14',
}

const MONTH_NAMES = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']

interface TabTrendProps {
  year: number; month: number; monthStr: string; refreshKey: number
}

interface TrendState {
  loading:      boolean
  trend:        DashboardTrend | null
  hotelMonthly: HotelMonthlyHoursData | null
  mallMonthly:  MallMonthlyHoursData | null
}

export default function TabTrend({ year, month, monthStr, refreshKey }: TabTrendProps) {
  const [days, setDays] = useState<number>(30)
  const [st, setSt] = useState<TrendState>({
    loading: true, trend: null, hotelMonthly: null, mallMonthly: null,
  })

  const load = useCallback(async () => {
    setSt(s => ({ ...s, loading: true }))
    const [r1, r2, r3] = await Promise.allSettled([
      dashboardApi.trend(days),
      fetchHotelMonthlyHours(year),
      fetchMallMonthlyHours(year),
    ])
    setSt({
      loading:      false,
      trend:        r1.status === 'fulfilled' ? r1.value.data : null,
      hotelMonthly: r2.status === 'fulfilled' ? r2.value : null,
      mallMonthly:  r3.status === 'fulfilled' ? r3.value : null,
    })
  }, [year, days, refreshKey]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const { loading, trend, hotelMonthly, mallMonthly } = st

  // ── 日度趨勢：hotel_completion + security_completion + mall_completion ──
  const dailyData = (trend?.trend ?? []).map(pt => ({
    date:     pt.date.slice(5),  // MM-DD
    飯店巡檢:  pt.hotel_has_data  ? Math.round(pt.hotel_completion)    : null,
    商場巡檢:  pt.mall_has_data   ? Math.round(pt.mall_completion)     : null,
    保全巡檢:  pt.security_has_data ? Math.round(pt.security_completion) : null,
  }))

  // ── 月工時趨勢：飯店 + 商場合計 ────────────────────────────────────────
  const monthlyData = MONTH_NAMES.map((name, idx) => {
    const mNum = idx + 1
    const hIdx = hotelMonthly?.months.indexOf(mNum) ?? -1
    const mIdx = mallMonthly?.months.indexOf(mNum) ?? -1
    const hotelTotal = hIdx >= 0
      ? Math.round(hotelMonthly!.rows.reduce((s, r) => s + (r.hours[hIdx] ?? 0), 0) * 10) / 10
      : null
    const mallTotal = mIdx >= 0
      ? Math.round(mallMonthly!.rows.reduce((s, r) => s + (r.hours[mIdx]  ?? 0), 0) * 10) / 10
      : null
    return { name, 飯店工時: hotelTotal, 商場工時: mallTotal }
  })

  // 目前月份標記
  const currentMonthName = MONTH_NAMES[month - 1]

  if (loading) return (
    <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  )

  return (
    <div style={{ paddingBottom: 24 }}>

      {/* ── ① 日度完成率趨勢 ─────────────────────────────────────────────── */}
      <Card
        style={{ marginBottom: 16, borderRadius: 8 }}
        bodyStyle={{ padding: '16px 24px' }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Text strong style={{ color: T.primary }}>巡檢完成率日度趨勢</Text>
            <Segmented
              size="small"
              value={days}
              onChange={v => setDays(Number(v))}
              options={[
                { label: '近 7 日',  value: 7  },
                { label: '近 30 日', value: 30 },
              ]}
            />
          </div>
        }
      >
        {dailyData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 24, color: T.textMuted }}>暫無資料</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={dailyData} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={days <= 7 ? 0 : 4} />
              <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} unit="%" />
              <RechartTooltip
                formatter={(v: unknown) => v !== null && v !== undefined ? [`${v}%`] : ['無資料']}
                contentStyle={{ fontSize: 11 }}
              />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="飯店巡檢"  stroke={T.primary}  strokeWidth={2} dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="商場巡檢"  stroke={T.accent}   strokeWidth={2} dot={false} connectNulls={false} />
              <Line type="monotone" dataKey="保全巡檢"  stroke={T.warning}  strokeWidth={2} dot={false} connectNulls={false} />
              <ReferenceLine y={80} stroke={T.success} strokeDasharray="4 4" label={{ value: '目標 80%', position: 'right', fontSize: 10, fill: T.success }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* ── ② 月工時趨勢 ────────────────────────────────────────────────── */}
      <Card
        style={{ borderRadius: 8 }}
        bodyStyle={{ padding: '16px 24px' }}
        title={
          <Text strong style={{ color: T.primary }}>
            飯店 / 商場月工時趨勢（{year} 年）
          </Text>
        }
      >
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={monthlyData} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} unit="hr" />
            <RechartTooltip
              formatter={(v: unknown) => v !== null && v !== undefined ? [`${v} hr`] : ['無資料']}
              contentStyle={{ fontSize: 11 }}
            />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
            {/* 目前月份垂直標線 */}
            <ReferenceLine
              x={currentMonthName}
              stroke={T.accent}
              strokeDasharray="4 4"
              label={{ value: '當月', position: 'top', fontSize: 10, fill: T.accent }}
            />
            <Line type="monotone" dataKey="飯店工時" stroke={T.primary} strokeWidth={2} dot={{ r: 4 }} connectNulls={false} />
            <Line type="monotone" dataKey="商場工時" stroke={T.accent}  strokeWidth={2} dot={{ r: 4 }} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

    </div>
  )
}
