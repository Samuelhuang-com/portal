/**
 * 退件統計圖（2026-11-03）— 退件統計模組的第一個分頁「統計圖」
 * 資料來源：/return-dashboard/matrix（與退件Dashboard 相同口徑：全年退件率為有送件月份之月退件率平均）
 * 配色依 dataviz 調色盤：公司線用類別色 slot 1–3（藍／橘／青綠，已通過 CVD 與對比檢查）；
 * 送件用循序藍 step 250、退件用 status critical；熱力圖用循序藍 100→650。
 * 本頁只做淺色（portal 無深色主題）。
 */
import { useEffect, useMemo, useState } from 'react'
import { Card, Col, Empty, Row, Spin, Typography, message } from 'antd'
import {
  Bar, BarChart, CartesianGrid, LabelList, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { fetchReturnMatrix, type MatrixResult, type MonthCell } from '@/api/returnDashboard'

const { Text } = Typography

// ── 色盤（dataviz reference palette，light）────────────────────────────
const CAT = ['#2a78d6', '#eb6834', '#1baf7a']          // categorical slot 1–3（公司依固定順序）
const COMPANY_ORDER = ['樂群', '日曜', '台中']
const INK_PRIMARY = '#0b0b0b'
const INK_SECONDARY = '#52514e'
const INK_MUTED = '#898781'
const GRID = '#e1e0d9'
const SENT_COLOR = '#86b6ef'                           // sequential blue step 250
const RETURN_COLOR = '#d03b3b'                         // status critical
const HEAT = ['#cde2fb', '#86b6ef', '#3987e5', '#1c5cab', '#104281']   // sequential blue 100–650
const HEAT_LABELS = ['< 1%', '1–3%', '3–6%', '6–10%', '≥ 10%']

const pct = (r: number | null | undefined, digits = 1) =>
  (r == null ? '—' : `${(r * 100).toFixed(digits)}%`)

const companyColor = (name: string) => {
  const i = COMPANY_ORDER.indexOf(name)
  return i >= 0 ? CAT[i] : INK_MUTED
}

const heatBucket = (rate: number | null): number => {
  if (rate == null) return -1
  const p = rate * 100
  if (p < 1) return 0
  if (p < 3) return 1
  if (p < 6) return 2
  if (p < 10) return 3
  return 4
}

// 折線末端直接標籤（relief rule：青綠對比 < 3:1，需直接標籤）
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const endLabel = (name: string, color: string, lastIdx: number) => (props: any) => {
  // recharts 的 label 型別不接受 null，非末端點回傳空的 <g />
  if (props.index !== lastIdx || props.x == null || props.y == null) return <g />
  return (
    <text x={props.x + 8} y={props.y + 4} fill={color} fontSize={12} fontWeight={600}>{name}</text>
  )
}

interface ChartsPageProps {
  year: number
  formType: string
  companies: string[]
  rejectionApprover: string   // 退件簽核人（由 Dashboard 篩選列提供；空字串＝全部）
}

export default function ReturnChartsPage({ year, formType, companies, rejectionApprover }: ChartsPageProps) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<MatrixResult | null>(null)
  useEffect(() => {
    setLoading(true)
    fetchReturnMatrix(year, formType, companies, rejectionApprover)
      .then(setData)
      .catch(() => message.error('載入統計圖失敗'))
      .finally(() => setLoading(false))
  }, [year, formType, companies, rejectionApprover])

  const blocks = useMemo(() => data?.blocks ?? [], [data])

  // 折線：每月公司月退件率（％）＋合計（灰色虛線）
  const lineSeries = useMemo(() => {
    const names = blocks.map(b => b.company)
    const months = Array.from({ length: 12 }, (_, i) => {
      const row: Record<string, string | number | undefined> = { label: `${i + 1}月` }
      blocks.forEach(b => {
        const r = b.months[i]?.rate
        row[b.company] = r == null ? undefined : +(r * 100).toFixed(2)
      })
      const t = data?.months[i]?.rate
      row['合計'] = t == null ? undefined : +(t * 100).toFixed(2)
      return row
    })
    const lastIdx = (key: string) => {
      let idx = -1
      months.forEach((m, i) => { if (m[key] != null) idx = i })
      return idx
    }
    return { names, months, lastIdx }
  }, [blocks, data])

  // 長條：每月送件／退件（件數）
  const barData = useMemo(() => (data?.months ?? []).map(m => ({
    label: `${m.month}月`, 送件: m.sent, 退件: m.returned,
  })), [data])

  // 熱力圖：部門 × 月
  const heatRows = useMemo(() => blocks.flatMap(b =>
    b.rows.map(r => ({ key: `${b.company}-${r.department}`, label: `${b.company}·${r.department}`, company: b.company, cells: r.cells, year_rate: r.year_rate, year_sent: r.year_sent, year_returned: r.year_returned }))
  ), [blocks])

  // 排名：部門全年退件率（有送件者）
  const ranking = useMemo(() => heatRows
    .filter(r => r.year_rate != null)
    .map(r => ({ name: r.label, rate: +((r.year_rate as number) * 100).toFixed(2), sent: r.year_sent, returned: r.year_returned, company: r.company }))
    .sort((a, b) => b.rate - a.rate), [heatRows])

  const top = ranking[0]

  return (
    <div>
      <Spin spinning={loading}>
        {!data ? <Empty description="尚無資料" /> : (
          <>
            {/* KPI */}
            <Row gutter={12} style={{ marginBottom: 12 }}>
              {[
                { label: '全年送件', value: data.year_sent.toLocaleString(), color: INK_PRIMARY },
                { label: '全年退件', value: data.year_returned.toLocaleString(), color: RETURN_COLOR },
                { label: '全年退件率（月平均）', value: pct(data.year_rate), color: INK_PRIMARY },
                { label: '退件率最高部門', value: top ? `${top.name}　${top.rate.toFixed(1)}%` : '—', color: RETURN_COLOR, small: true },
              ].map(k => (
                <Col xs={12} md={6} key={k.label}>
                  <Card size="small" style={{ borderTop: '3px solid #1B3A5C' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>{k.label}</Text>
                    <div style={{ fontSize: k.small ? 16 : 26, fontWeight: 700, color: k.color, marginTop: 4, lineHeight: 1.3 }}>{k.value}</div>
                  </Card>
                </Col>
              ))}
            </Row>

            {/* 折線 + 長條 */}
            <Row gutter={12} style={{ marginBottom: 12 }}>
              <Col xs={24} lg={14}>
                <Card size="small" title="每月退件率趨勢（依公司）">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={lineSeries.months} margin={{ top: 16, right: 64, left: 0, bottom: 0 }}>
                      <CartesianGrid stroke={GRID} vertical={false} />
                      <XAxis dataKey="label" tick={{ fill: INK_SECONDARY, fontSize: 12 }} axisLine={{ stroke: '#c3c2b7' }} tickLine={false} />
                      <YAxis tickFormatter={v => `${v}%`} tick={{ fill: INK_MUTED, fontSize: 12 }} axisLine={false} tickLine={false} width={48} />
                      <Tooltip formatter={(v) => [`${Number(v).toFixed(1)}%`, '退件率']} />
                      <Legend verticalAlign="top" height={28} iconType="plainline" />
                      {lineSeries.names.map(n => (
                        <Line
                          key={n} type="monotone" dataKey={n} name={n}
                          stroke={companyColor(n)} strokeWidth={2.5}
                          dot={{ r: 4, fill: companyColor(n), strokeWidth: 0 }}
                          activeDot={{ r: 6 }} connectNulls={false}
                          label={endLabel(n, companyColor(n), lineSeries.lastIdx(n))}
                        />
                      ))}
                      <Line
                        key="合計" type="monotone" dataKey="合計" name="合計"
                        stroke={INK_SECONDARY} strokeWidth={1.75} strokeDasharray="6 4"
                        dot={false} connectNulls={false}
                        label={endLabel('合計', INK_SECONDARY, lineSeries.lastIdx('合計'))}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                  <Text type="secondary" style={{ fontSize: 12 }}>送件為 0 的月份不畫點（斷線），不計為 0%。</Text>
                </Card>
              </Col>
              <Col xs={24} lg={10}>
                <Card size="small" title="每月送件與退件件數">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={barData} margin={{ top: 16, right: 8, left: 0, bottom: 0 }} barGap={2}>
                      <CartesianGrid stroke={GRID} vertical={false} />
                      <XAxis dataKey="label" tick={{ fill: INK_SECONDARY, fontSize: 12 }} axisLine={{ stroke: '#c3c2b7' }} tickLine={false} />
                      <YAxis tick={{ fill: INK_MUTED, fontSize: 12 }} axisLine={false} tickLine={false} width={40} />
                      <Tooltip cursor={{ fill: 'rgba(11,11,11,0.04)' }} />
                      <Legend verticalAlign="top" height={28} iconType="square" />
                      <Bar dataKey="送件" fill={SENT_COLOR} radius={[4, 4, 0, 0]} maxBarSize={18} />
                      <Bar dataKey="退件" fill={RETURN_COLOR} radius={[4, 4, 0, 0]} maxBarSize={18} />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </Col>
            </Row>

            {/* 熱力圖 */}
            <Card size="small" title="部門 × 月 退件率熱力圖" style={{ marginBottom: 12 }}>
              {heatRows.length === 0 ? <Empty description="無資料" /> : (
                <div style={{ overflowX: 'auto' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '170px repeat(12, minmax(56px, 1fr)) 72px', gap: 3, minWidth: 900 }}>
                    <div />
                    {Array.from({ length: 12 }, (_, i) => (
                      <div key={`h${i}`} style={{ textAlign: 'center', fontSize: 12, color: INK_SECONDARY }}>{i + 1}月</div>
                    ))}
                    <div style={{ textAlign: 'center', fontSize: 12, color: INK_SECONDARY }}>全年</div>
                    {heatRows.map(r => (
                      <HeatRow key={r.key} label={r.label} cells={r.cells} yearRate={r.year_rate}
                        yearSent={r.year_sent} yearReturned={r.year_returned} />
                    ))}
                  </div>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>退件率：</Text>
                {HEAT_LABELS.map((l, i) => (
                  <span key={l} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, color: INK_SECONDARY }}>
                    <span style={{ width: 16, height: 12, background: HEAT[i], borderRadius: 2, display: 'inline-block' }} />{l}
                  </span>
                ))}
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, color: INK_SECONDARY }}>
                  <span style={{ width: 16, height: 12, background: '#f3f2ee', borderRadius: 2, display: 'inline-block' }} />無送件（—）
                </span>
              </div>
            </Card>

            {/* 排名 */}
            <Card size="small" title="各部門全年退件率排名（有送件者）">
              {ranking.length === 0 ? <Empty description="無資料" /> : (
                <ResponsiveContainer width="100%" height={Math.max(220, ranking.length * 30 + 40)}>
                  <BarChart data={ranking} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 4 }}>
                    <CartesianGrid stroke={GRID} horizontal={false} />
                    <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fill: INK_MUTED, fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" width={170} tick={{ fill: INK_PRIMARY, fontSize: 12 }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v, _n, p) => [`${Number(v).toFixed(1)}%（退件 ${p?.payload?.returned} ／ 送件 ${p?.payload?.sent}）`, '全年退件率']} />
                    <Bar dataKey="rate" fill="#2a78d6" radius={[0, 4, 4, 0]} maxBarSize={18}>
                      <LabelList dataKey="rate" position="right" formatter={(v: number) => `${v.toFixed(1)}%`}
                        style={{ fill: INK_PRIMARY, fontSize: 12, fontWeight: 600 }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </>
        )}
      </Spin>
    </div>
  )
}

function HeatRow({ label, cells, yearRate, yearSent, yearReturned }: {
  label: string; cells: MonthCell[]; yearRate: number | null; yearSent: number; yearReturned: number
}) {
  return (
    <>
      <div style={{ fontSize: 12, color: INK_PRIMARY, alignSelf: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={label}>{label}</div>
      {cells.map(c => {
        const b = heatBucket(c.rate)
        const bg = b < 0 ? '#f3f2ee' : HEAT[b]
        const fg = b >= 2 ? '#ffffff' : INK_PRIMARY
        const tip = `${label}　${c.month} 月\n送件 ${c.sent}／退件 ${c.returned}\n退件率 ${pct(c.rate)}`
        return (
          <div key={c.month} title={tip}
            style={{ background: bg, color: fg, borderRadius: 3, height: 30, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, cursor: 'default' }}>
            {b < 0 ? '—' : pct(c.rate)}
          </div>
        )
      })}
      <div title={`全年：送件 ${yearSent}／退件 ${yearReturned}`}
        style={{ fontSize: 12, fontWeight: 700, textAlign: 'center', alignSelf: 'center', color: INK_PRIMARY }}>
        {pct(yearRate)}
      </div>
    </>
  )
}
