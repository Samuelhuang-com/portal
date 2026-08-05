/**
 * ★ 金旭分析 Dashboard（/jinxu/dashboard）
 * 規格書：§13.2
 *
 * KPI 兩排共 8 張：第一排訂房、第二排帳務（4 欄 Row、size="small"，
 * 對齊 CLAUDE.md 受保護版型）。
 *
 * ⚠️ 母體標示（§11.4）：訂房 KPI 下方固定顯示「已排除取消與虛擬訂房」。
 * ⚠️ 只匯入單一 source_type 時，另一區塊**整區隱藏**，不可顯示 0 或空圖表。
 */
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Card, Col, Empty, Row, Space, Spin, Statistic, Tag, Typography,
} from 'antd'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'
import type { Dayjs } from 'dayjs'

import {
  fetchCancellationMonthly, fetchCoverage, fetchDepositSummary, fetchImportStatus,
  fetchPaymentSummary, fetchResvByChannel, fetchResvSummary, fetchRevenueBySubject,
  fetchRevenueSummary,
} from '@/api/jinxu'
import type {
  CancellationMonthRow, Coverage, DepositSummary, ImportStatus, PaymentSummary,
  ResvGroupResult, ResvSummary, RevenueSummary, SubjectRow,
} from '@/types/jinxu'
import FilterBar, { toIso } from '../components/FilterBar'
import SharePie from '../components/SharePie'
import { CHART_PALETTE, GROUP_COLORS, fmtInt, fmtMoney, fmtPct } from '../components/constants'

const { Title, Text } = Typography

export default function JinxuDashboard() {
  const nav = useNavigate()
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<ImportStatus | null>(null)
  const [cov, setCov] = useState<Coverage | null>(null)
  const [rev, setRev] = useState<RevenueSummary | null>(null)
  const [pay, setPay] = useState<PaymentSummary | null>(null)
  const [dep, setDep] = useState<DepositSummary | null>(null)
  const [resv, setResv] = useState<ResvSummary | null>(null)
  const [chan, setChan] = useState<ResvGroupResult | null>(null)
  const [groups, setGroups] = useState<SubjectRow[]>([])
  const [cancelMonth, setCancelMonth] = useState<CancellationMonthRow[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    const start_date = toIso(range?.[0]), end_date = toIso(range?.[1])
    try {
      const st = await fetchImportStatus()
      setStatus(st)
      const hasLedger = st.sources.FCR02_LEDGER?.has_data
      const hasResv = st.sources.RESV_DETAIL?.has_data

      setCov(await fetchCoverage(start_date, end_date))

      if (hasLedger) {
        setRev(await fetchRevenueSummary({ start_date, end_date }))
        setPay(await fetchPaymentSummary(start_date, end_date))
        setDep(await fetchDepositSummary(start_date, end_date))
        setGroups((await fetchRevenueBySubject({ start_date, end_date }, 'group')).items)
      } else {
        setRev(null); setPay(null); setDep(null); setGroups([])
      }

      if (hasResv) {
        setResv(await fetchResvSummary({ start_date, end_date }))
        setChan(await fetchResvByChannel({ start_date, end_date }))
        try {
          setCancelMonth((await fetchCancellationMonthly({ start_date, end_date })).items)
        } catch {
          setCancelMonth([]) // 無 jinxu_cancel_view 權限時靜默略過
        }
      } else {
        setResv(null); setChan(null); setCancelMonth([])
      }
    } finally {
      setLoading(false)
    }
  }, [range])

  useEffect(() => { void load() }, [load])

  const hasLedger = !!status?.sources.FCR02_LEDGER?.has_data
  const hasResv = !!status?.sources.RESV_DETAIL?.has_data

  if (loading && !status) return <Spin style={{ margin: 48 }} />

  if (!hasLedger && !hasResv) {
    return (
      <Card>
        <Empty description="尚未匯入任何金旭資料">
          <a onClick={() => nav('/jinxu/import')}>前往資料匯入</a>
        </Empty>
      </Card>
    )
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 4 }}>★ 金旭分析 Dashboard</Title>
      <FilterBar range={range} onChange={setRange} onReload={load}
                 periodLabel={cov?.period_label} />

      {/* 資料涵蓋提示 */}
      <Space direction="vertical" size="small" style={{ width: '100%', marginBottom: 16 }}>
        <Space wrap>
          {(['FCR02_LEDGER', 'RESV_DETAIL'] as const).map((k) => {
            const s = status?.sources[k]
            return s?.has_data ? (
              <Tag key={k} color="blue">
                {s.label} {fmtInt(s.row_count)} 筆（{s.date_start} ~ {s.date_end}）
              </Tag>
            ) : (
              <Tag key={k} color="default">{s?.label ?? k}：尚未匯入</Tag>
            )
          })}
        </Space>
        {cov && !cov.yoy_available && (
          <Alert type="info" showIcon
            message={`目前僅有 ${cov.years_covered.join('、')} 年度資料，同期比較（YoY）需匯入前一年度後才能使用。`} />
        )}
        {!status?.cross_analysis_available && (
          <Alert type="warning" showIcon
            message="需同時匯入「客帳帳目明細表」與「訂房狀況表」，才能使用訂價 vs 實收交叉分析。" />
        )}
      </Space>

      {/* ── 第一排 KPI：訂房 ── */}
      {hasResv && resv && (
        <>
          <Row gutter={16} style={{ marginBottom: 8 }}>
            <Col span={6}>
              <Card size="small"><Statistic title="訂房筆數" value={resv.reservation_count} /></Card>
            </Col>
            <Col span={6}>
              <Card size="small"><Statistic title="房晚數" value={resv.room_nights} /></Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="平均房價 ADR" value={resv.adr} precision={0} prefix="$" />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="取消率" value={resv.cancel_rate_by_count} precision={2} suffix="%"
                           valueStyle={{ color: '#cf1322' }} />
              </Card>
            </Col>
          </Row>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 16 }}>
            {resv.population_note}；平均住宿 {resv.avg_billable_nights} 晚（Day Use 計 1 晚）
          </Text>
        </>
      )}

      {/* ── 第二排 KPI：帳務 ── */}
      {hasLedger && rev && (
        <>
          <Row gutter={16} style={{ marginBottom: 8 }}>
            <Col span={6}>
              <Card size="small">
                <Statistic title="期間總收入（淨額）" value={rev.revenue_net} precision={0} prefix="$" />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="期間總抵充" value={rev.settlement_total} precision={0} prefix="$" />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="沖帳率（筆數）" value={rev.reversal_rate_by_count}
                           precision={2} suffix="%" />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small"><Statistic title="交易筆數" value={rev.transaction_count} /></Card>
            </Col>
          </Row>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 16 }}>
            {rev.note}
          </Text>
        </>
      )}

      {/* ── 主軸摘要卡 ── */}
      <Row gutter={16}>
        {hasResv && chan && (
          <Col span={8}>
            <Card size="small" title="訂房與通路" style={{ marginBottom: 16, cursor: 'pointer' }}
                  onClick={() => nav('/jinxu/reservation')}>
              {/* 摘要卡空間窄，關掉圖例只留切片內的 %；完整名稱請點進訂房頁 */}
              <SharePie
                data={chan.items}
                nameOf={(r) => r.label}
                valueOf={(r) => r.room_nights}
                keyOf={(r) => r.key || r.label}
                topN={6}
                height={220}
                unit=" 房晚"
                showLegend={false}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                依房晚數，前 6 大通路＋其他（未合併同 OTA）
              </Text>
            </Card>
          </Col>
        )}
        {hasLedger && groups.length > 0 && (
          <Col span={8}>
            <Card size="small" title="收入結構" style={{ marginBottom: 16, cursor: 'pointer' }}
                  onClick={() => nav('/jinxu/revenue')}>
              <SharePie
                data={groups}
                nameOf={(g) => g.label}
                valueOf={(g) => g.amount}
                keyOf={(g) => g.key}
                colorOf={(g, i) => GROUP_COLORS[g.key] || CHART_PALETTE[i % CHART_PALETTE.length]}
                valueFormatter={fmtMoney}
                height={220}
                showLegend={false}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>依科目大類（淨額）</Text>
            </Card>
          </Col>
        )}
        {hasLedger && pay && (
          <Col span={8}>
            <Card size="small" title="付款方式" style={{ marginBottom: 16, cursor: 'pointer' }}
                  onClick={() => nav('/jinxu/payment')}>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={pay.by_macro} layout="vertical"
                          margin={{ left: 48, right: 16, top: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tickFormatter={(v) => `${Math.round(v / 10000)}萬`} />
                  <YAxis type="category" dataKey="label" width={64} />
                  <RcTooltip formatter={(v: number) => fmtMoney(v)} />
                  <Bar dataKey="amount" fill="#667eea" />
                </BarChart>
              </ResponsiveContainer>
              <Text type="secondary" style={{ fontSize: 12 }}>{pay.note}</Text>
            </Card>
          </Col>
        )}
      </Row>

      <Row gutter={16}>
        {hasLedger && dep && (
          <Col span={12}>
            <Card size="small" title="預收訂金" style={{ marginBottom: 16, cursor: 'pointer' }}
                  onClick={() => nav('/jinxu/deposit')}>
              <Row gutter={8}>
                <Col span={8}><Statistic title="發生" value={dep.inflow_amount} precision={0} prefix="$" /></Col>
                <Col span={8}><Statistic title="沖銷" value={dep.outflow_amount} precision={0} prefix="$" /></Col>
                <Col span={8}>
                  <Statistic title="未沖餘額" value={dep.net_balance} precision={0} prefix="$"
                             valueStyle={{ color: dep.net_balance < 0 ? '#cf1322' : undefined }} />
                </Col>
              </Row>
              <Alert type="warning" showIcon style={{ marginTop: 12 }} message={dep.warning} />
            </Card>
          </Col>
        )}
        {cancelMonth.length > 0 && (
          <Col span={12}>
            <Card size="small" title="逐月取消率" style={{ marginBottom: 16, cursor: 'pointer' }}
                  onClick={() => nav('/jinxu/reservation?tab=cancellation')}>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={cancelMonth}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis tickFormatter={(v) => `${v}%`} />
                  <RcTooltip formatter={(v: number) => fmtPct(v, 2)} />
                  <Legend />
                  <Line type="monotone" dataKey="cancel_rate_by_count" name="取消率(筆數)" stroke="#cf1322" />
                  <Line type="monotone" dataKey="cancel_rate_by_room_nights" name="取消率(房晚)" stroke="#e67e22" />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  )
}
