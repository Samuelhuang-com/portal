/**
 * ★ 營運分析 Dashboard（/opera/dashboard）
 * 規格書：docs/SPEC_opera_analytics.md §11.2、圖表 C1 / C2 / C3 / C8
 *
 * 資料口徑（決策 D7）：
 *   上半部 KPI 與圖表 → History and Forecast
 *   下半部住宿總覽     → Departure All
 *   兩區分開顯示並標註來源，不互相驗算房晚。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Badge, Button, Card, Col, Empty, Modal, Row, Select, Space,
  Spin, Statistic, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  BarChartOutlined, InfoCircleOutlined, QuestionCircleOutlined,
  ReloadOutlined, UploadOutlined,
} from '@ant-design/icons'
import {
  Bar, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart, Pie, PieChart,
  ReferenceLine, ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'

import { fetchOperaDashboard } from '@/api/opera'
import type { OperaDashboard } from '@/types/opera'
// 即時房況面板由「即時營運」模組提供（資料來源與本頁其他區塊不同，見元件內註解）
import LiveStatusPanel from '@/pages/Realtime/components/LiveStatusPanel'
import {
  ACCENT, BRAND, CHART_COLORS, EMPTY, GREEN, GREY, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct, fmtPpt, fmtYoY, periodTagColor, trendColor,
} from '../components/formatters'
import ComparisonTooltip from '../components/ComparisonTooltip'
import type { CompareMetric } from '../components/ComparisonTooltip'

const { Title, Text } = Typography

const CHART_HEIGHT = 280

// Tooltip 的「與去年同期增減」設定（元件說明見 components/ComparisonTooltip.tsx）
const MONTHLY_TOOLTIP_METRICS: CompareMetric[] = [
  { label: '營收', currentKey: '本年營收', compareKey: '去年營收', color: BRAND },
  { label: 'ADR', currentKey: '本年ADR', compareKey: '去年ADR', color: ORANGE },
]

const OCCUPANCY_TOOLTIP_METRICS: CompareMetric[] = [
  {
    label: '住房率',
    currentKey: '本年住房率',
    compareKey: '去年住房率',
    color: BRAND,
    diffMode: 'ppt',
    format: (v: number) => `${v.toFixed(1)}%`,
  },
]

const OperaDashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<OperaDashboard | null>(null)
  const [year, setYear] = useState<number | undefined>(undefined)
  const [stayHelpOpen, setStayHelpOpen] = useState(false)

  const load = useCallback(async (targetYear?: number) => {
    setLoading(true)
    try {
      const res = await fetchOperaDashboard(targetYear ? { year: targetYear } : {})
      setData(res)
      if (res.year && targetYear === undefined) setYear(res.year)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入營運分析 Dashboard 失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── C1：月營收 + ADR 雙軸 ────────────────────────────────────────────────
  const monthlyChart = useMemo(() => {
    if (!data?.monthly) return []
    return data.monthly.months.map((m) => ({
      label: m.label,
      本年營收: Math.round(m.current.revenue),
      去年營收: m.has_compare ? Math.round(m.compare.revenue) : null,
      本年ADR: Math.round(m.current.adr),
      去年ADR: m.has_compare ? Math.round(m.compare.adr) : null,
      本年住房率: Number((m.current.occupancy * 100).toFixed(1)),
      去年住房率: m.has_compare ? Number((m.compare.occupancy * 100).toFixed(1)) : null,
      periodLabel: m.period_label,
    }))
  }, [data])

  const hasCompare = useMemo(
    () => Boolean(data?.monthly?.months.some((m) => m.has_compare)),
    [data],
  )

  // ── C3：散客 vs 團體營收占比 ────────────────────────────────────────────
  const segmentChart = useMemo(
    () => (data?.segment?.segments || []).map((s) => ({ name: s.label, value: Math.round(s.revenue) })),
    [data],
  )

  const kpi = data?.kpi
  const period = kpi?.period
  const annualOccupancy = kpi ? Number((kpi.current.occupancy * 100).toFixed(1)) : 0

  // ── 尚未有資料 ──────────────────────────────────────────────────────────
  if (!loading && data && !data.has_data) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={4} style={{ color: BRAND }}>★ 營運分析 Dashboard</Title>
        <Card>
          <Empty description="尚未匯入任何 OPERA 資料">
            <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate('/opera/import')}>
              前往資料匯入
            </Button>
          </Empty>
        </Card>
      </div>
    )
  }

  return (
    <Spin spinning={loading}>
      <div style={{ padding: 24 }}>
        {/* ── 標題列 ─────────────────────────────────────────────────── */}
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space size={12} wrap>
              <Title level={4} style={{ margin: 0, color: BRAND }}>★ 營運分析 Dashboard</Title>
              {period && (
                <Tooltip title="完整期間才可與去年整期直接比較；部分期間一律只比去年同期 MTD／YTD">
                  <Tag color={periodTagColor(period.period_type)}>
                    {period.period_label} <InfoCircleOutlined />
                  </Tag>
                </Tooltip>
              )}
              {period && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {`${period.start} ～ ${period.end}　比較期：${period.compare_label}（${period.compare_start} ～ ${period.compare_end}）`}
                </Text>
              )}
            </Space>
          </Col>
          <Col>
            <Space>
              <Select
                value={year}
                style={{ width: 120 }}
                onChange={(v) => { setYear(v); load(v) }}
                options={(data?.available_years || []).map((y) => ({ value: y, label: `${y} 年` }))}
              />
              <Button icon={<ReloadOutlined />} onClick={() => load(year)}>重新整理</Button>
              <Button icon={<UploadOutlined />} onClick={() => navigate('/opera/import')}>資料匯入</Button>
            </Space>
          </Col>
        </Row>

        {/* ── OPERA 即時房況（OHIP API，2026-08-06）─────────────────────
            ⚠️ 這一區與底下所有區塊的資料來源與時點都不同，因此獨立成卡片並
               自帶來源標示。它不參與本頁既有的 load()／year 篩選，
               也不讀任何 opera_* 資料表。 */}
        <LiveStatusPanel />

        {/* ── 資料涵蓋提示 ───────────────────────────────────────────── */}
        {data?.status && (
          <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }} size={8}>
            {data.status.missing_history_years.length > 0 && (
              <Alert
                type="warning"
                showIcon
                message={`缺少 ${data.status.missing_history_years.join('、')} 年度的 History and Forecast 資料`}
                description="這些年度只有 Departure 資料，因此無法計算該年度的營收、ADR、住房率與 YoY 比較。請匯出對應年度的 History and Forecast TXT 後匯入。"
                action={
                  <Button size="small" type="primary" onClick={() => navigate('/opera/import')}>
                    前往匯入
                  </Button>
                }
              />
            )}
            <Card size="small" style={{ background: '#f9fbff' }}>
              <Row gutter={[16, 8]}>
                <Col xs={24} md={8}>
                  <Text type="secondary">Departure（住宿明細）：</Text>{' '}
                  <Text strong>
                    {data.status.departure.start ? `${data.status.departure.start} ～ ${data.status.departure.end}` : EMPTY}
                  </Text>{' '}
                  <Text type="secondary">{`（${fmtInt(data.status.departure.rows)} 筆）`}</Text>
                </Col>
                <Col xs={24} md={8}>
                  <Text type="secondary">History（實績）：</Text>{' '}
                  <Text strong>
                    {data.status.history.start ? `${data.status.history.start} ～ ${data.status.history.end}` : EMPTY}
                  </Text>{' '}
                  <Text type="secondary">{`（${fmtInt(data.status.history.rows)} 天）`}</Text>
                </Col>
                <Col xs={24} md={8}>
                  <Text type="secondary">Forecast（預測）：</Text>{' '}
                  <Text strong>
                    {data.status.forecast.start ? `${data.status.forecast.start} ～ ${data.status.forecast.end}` : EMPTY}
                  </Text>{' '}
                  <Text type="secondary">{`（${fmtInt(data.status.forecast.rows)} 天）`}</Text>
                </Col>
              </Row>
            </Card>
          </Space>
        )}

        {/* ── KPI 卡片（4 欄，size="small"，符合受保護版型）────────────── */}
        {kpi && (
          <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
            {[
              { title: '期間房間營收', value: fmtMoney(kpi.current.revenue), prefix: '$', yoy: kpi.yoy.revenue, color: BRAND },
              { title: '加權 ADR', value: fmtMoney(kpi.current.adr), prefix: '$', yoy: kpi.yoy.adr, color: ACCENT },
              { title: '加權住房率', value: fmtPct(kpi.current.occupancy), prefix: '', ppt: kpi.yoy.occupancy_ppt, color: GREEN },
              { title: '加權 RevPAR', value: fmtMoney(kpi.current.revpar), prefix: '$', yoy: kpi.yoy.revpar, color: ORANGE },
            ].map((item) => (
              <Col xs={24} sm={12} lg={6} key={item.title}>
                <Card size="small" bodyStyle={{ padding: '14px 16px' }} style={{ borderLeft: `3px solid ${item.color}` }}>
                  <Statistic
                    title={item.title}
                    value={item.value}
                    prefix={item.prefix}
                    valueStyle={{ color: item.color, fontSize: 24 }}
                  />
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    {!kpi.has_compare_data ? (
                      <Text type="secondary">無去年同期資料，暫不顯示 YoY</Text>
                    ) : item.ppt !== undefined ? (
                      <Text style={{ color: trendColor(item.ppt) }}>
                        {`${fmtPpt(item.ppt)}　vs ${kpi.period.compare_label}`}
                      </Text>
                    ) : (
                      <Text style={{ color: trendColor(item.yoy) }}>
                        {`${fmtYoY(item.yoy)}　vs ${kpi.period.compare_label}`}
                      </Text>
                    )}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        )}

        {/* ── C1：月營收 + ADR 雙軸 ──────────────────────────────────── */}
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={16}>
            <Card
              size="small"
              title={<Space><BarChartOutlined />月營收與 ADR</Space>}
              extra={<Text type="secondary" style={{ fontSize: 12 }}>資料來源：History and Forecast</Text>}
            >
              {monthlyChart.length === 0 ? (
                <Empty description="本年度尚無 History 資料" />
              ) : (
                <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                  <ComposedChart data={monthlyChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                    <YAxis
                      yAxisId="left"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v: number) => `${Math.round(v / 10000)}萬`}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 11 }}
                      tickFormatter={(v: number) => v.toLocaleString('en-US')}
                    />
                    <RcTooltip content={<ComparisonTooltip metrics={MONTHLY_TOOLTIP_METRICS} />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar yAxisId="left" dataKey="本年營收" fill={BRAND} barSize={18} />
                    {hasCompare && <Bar yAxisId="left" dataKey="去年營收" fill={GREY} barSize={18} />}
                    <Line yAxisId="right" type="monotone" dataKey="本年ADR" stroke={ORANGE} strokeWidth={2} dot={{ r: 3 }} />
                    {hasCompare && (
                      <Line yAxisId="right" type="monotone" dataKey="去年ADR" stroke={GREY} strokeWidth={1} strokeDasharray="4 3" dot={false} />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {/* ── C3：散客 vs 團體營收占比 ─────────────────────────────── */}
          <Col xs={24} lg={8}>
            <Card
              size="small"
              title="散客 vs 團體（營收占比）"
              extra={<Text type="secondary" style={{ fontSize: 12 }}>History</Text>}
            >
              {segmentChart.length === 0 || segmentChart.every((s) => s.value === 0) ? (
                <Empty description="尚無客層資料" />
              ) : (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      {/* ⚠️ isAnimationActive={false} 是必要的，不是效能微調：
                          App 跑在 React.StrictMode 下，開發模式的雙重掛載會取消
                          recharts 的進場動畫，而 Pie 的 sector 只在動畫啟動後才產生，
                          結果就是圓餅完全畫不出來（只剩標籤）。Bar／Line 不受影響。
                          2026-08-04 實測：專案既有頁面的圓餅圖也有同樣狀況。 */}
                      <Pie
                        data={segmentChart}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        isAnimationActive={false}
                        label={(e: any) => `${e.name} ${(e.percent * 100).toFixed(1)}%`}
                        labelLine={false}
                      >
                        {segmentChart.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <RcTooltip formatter={(v: any) => `$ ${Number(v).toLocaleString('en-US')}`} />
                    </PieChart>
                  </ResponsiveContainer>
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={data?.segment?.segments || []}
                    rowKey="key"
                    columns={[
                      { title: '客層', dataIndex: 'label', width: 60 },
                      { title: '房晚', dataIndex: 'rooms', align: 'right', render: fmtInt },
                      { title: 'ADR', dataIndex: 'adr', align: 'right', render: (v: number) => `$${fmtMoney(v)}` },
                    ]}
                  />
                </>
              )}
            </Card>
          </Col>
        </Row>

        {/* ── C2：住房率月趨勢 + 年度加權參考線 ───────────────────────── */}
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={16}>
            <Card
              size="small"
              title="住房率月趨勢"
              extra={
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {`虛線 = 期間加權住房率 ${annualOccupancy}%　資料來源：History and Forecast`}
                </Text>
              }
            >
              {monthlyChart.length === 0 ? (
                <Empty description="本年度尚無 History 資料" />
              ) : (
                <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
                  <LineChart data={monthlyChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}%`} domain={[0, 100]} />
                    <RcTooltip content={<ComparisonTooltip metrics={OCCUPANCY_TOOLTIP_METRICS} />} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <ReferenceLine
                      y={annualOccupancy}
                      stroke={RED}
                      strokeDasharray="5 4"
                      label={{ value: `期間加權 ${annualOccupancy}%`, position: 'right', fontSize: 11, fill: RED }}
                    />
                    <Line type="monotone" dataKey="本年住房率" stroke={BRAND} strokeWidth={2} dot={{ r: 3 }} />
                    {hasCompare && (
                      <Line type="monotone" dataKey="去年住房率" stroke={GREY} strokeWidth={1} strokeDasharray="4 3" dot={false} />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {/* ── 異常摘要 ─────────────────────────────────────────────── */}
          <Col xs={24} lg={8}>
            <Card
              size="small"
              title="營收異常摘要"
              extra={
                <Button type="link" size="small" onClick={() => navigate('/opera/revenue')}>
                  查看明細
                </Button>
              }
            >
              {!data?.anomaly_summary || data.anomaly_summary.total === 0 ? (
                <Empty description="期間內無營收異常" />
              ) : (
                <>
                  <Statistic
                    title="異常天數"
                    value={data.anomaly_summary.total}
                    suffix="天"
                    valueStyle={{ color: RED, fontSize: 24 }}
                  />
                  <div style={{ marginTop: 12 }}>
                    {Object.entries(data.anomaly_summary.type_counts)
                      .sort((a, b) => b[1] - a[1])
                      .map(([type, count]) => (
                        <div key={type} style={{ marginBottom: 6 }}>
                          <Badge color={ORANGE} />
                          <Text style={{ fontSize: 13 }}>{type}</Text>
                          <Text strong style={{ float: 'right' }}>{fmtInt(count)}</Text>
                        </div>
                      ))}
                  </div>
                </>
              )}
            </Card>
          </Col>
        </Row>

        {/* ── Departure 側總覽（來源不同，刻意分區）────────────────────── */}
        {data?.stay_summary && (
          <Card
            size="small"
            title={
              <Space size={6} align="center">
                <span>住宿明細總覽</span>
                <Tooltip title="資料來源說明">
                  <Button
                    type="text" size="small" aria-label="資料來源說明"
                    icon={<QuestionCircleOutlined style={{ color: ACCENT, fontSize: 16 }} />}
                    onClick={() => setStayHelpOpen(true)}
                  />
                </Tooltip>
              </Space>
            }
            extra={
              <Space>
                <Text type="secondary" style={{ fontSize: 12 }}>資料來源：Departure All</Text>
                <Button type="link" size="small" onClick={() => navigate('/opera/guest')}>
                  住客與通路分析
                </Button>
              </Space>
            }
          >
            <Modal
              open={stayHelpOpen}
              onCancel={() => setStayHelpOpen(false)}
              footer={null}
              width={520}
              title={
                <Space size={8}>
                  <InfoCircleOutlined style={{ color: ACCENT }} />
                  <span>本區與上方營收指標來自不同報表，房晚數字不可互相驗算</span>
                </Space>
              }
            >
              <div style={{ lineHeight: 1.8 }}>
                Departure 以退房日歸屬整段住宿；History and Forecast 以營業日逐日歸屬。
                營收一律以 History 為準，通路／房型／住客結構一律以 Departure 為準。
              </div>
            </Modal>
            <Row gutter={[12, 12]}>
              {(['room', 'reservation'] as const).map((basis) => {
                const s = data.stay_summary![basis]
                return (
                  <Col xs={24} md={12} key={basis}>
                    <Card size="small" bodyStyle={{ padding: '12px 16px' }} style={{ background: '#fafafa' }}>
                      <Text strong style={{ color: BRAND }}>{s.basis_label}</Text>
                      <Row gutter={8} style={{ marginTop: 8 }}>
                        <Col span={8}><Statistic title="筆數" value={s.records} valueStyle={{ fontSize: 18 }} /></Col>
                        <Col span={8}><Statistic title="房晚" value={s.room_nights} valueStyle={{ fontSize: 18 }} /></Col>
                        <Col span={8}><Statistic title="成人" value={s.adults} valueStyle={{ fontSize: 18 }} /></Col>
                      </Row>
                    </Card>
                  </Col>
                )
              })}
            </Row>
            <Text type="secondary" style={{ display: 'block', marginTop: 10, fontSize: 12 }}>
              {`住客識別涵蓋率 ${fmtPct(data.stay_summary.coverage.coverage)}
                （${fmtInt(data.stay_summary.coverage.identified)} / ${fmtInt(data.stay_summary.coverage.total)} 筆），
                其餘為 OPERA 已清除個資的紀錄，不納入住客回訪分析。`}
            </Text>
          </Card>
        )}
      </div>
    </Spin>
  )
}

export default OperaDashboardPage
