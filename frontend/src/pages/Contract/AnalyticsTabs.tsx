/**
 * Phase J — 分析與體驗強化
 *
 * J1 — 廠商集中度分析 (VendorConcentrationChart)
 * J2 — 合約成本趨勢圖 (CostTrendChart)
 * J3 — 月度/季度報表  (SummaryReportTab)
 *
 * 這些元件掛載於 Contract/Dashboard.tsx 的新 Tabs 中。
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Table, Button, Space, Select, Tag, Typography, Card, Row, Col,
  Statistic, Alert, Spin, Empty, message, Radio,
} from 'antd'
import {
  DownloadOutlined, ReloadOutlined, WarningOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, Cell, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import type {
  VendorConcentrationItem,
  CostTrendPoint,
  SummaryReportRow,
} from '@/types/contract'
import {
  fetchVendorConcentration,
  fetchCostTrend,
  fetchSummaryReport,
  exportSummaryReport,
} from '@/api/contract'

const { Text } = Typography
const currentYear = new Date().getFullYear()
const YEAR_OPTIONS = [currentYear - 1, currentYear, currentYear + 1]

const fmtMoney = (v: number) =>
  `$${Number(v).toLocaleString('zh-TW', { minimumFractionDigits: 0 })}`

// ─────────────────────────────────────────────────────────────────────────────
// J1 — 廠商集中度分析
// ─────────────────────────────────────────────────────────────────────────────

export function VendorConcentrationChart() {
  const [data, setData] = useState<VendorConcentrationItem[]>([])
  const [loading, setLoading] = useState(false)
  const [budgetYear, setBudgetYear] = useState<number | undefined>(currentYear)
  const [threshold, setThreshold] = useState(30)
  const [grandTotal, setGrandTotal] = useState(0)
  const [highCount, setHighCount] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchVendorConcentration(budgetYear, threshold)
      setData(res.items)
      setGrandTotal(res.grand_total)
      setHighCount(res.high_concentration_count)
    } catch {
      message.error('載入廠商集中度失敗')
    } finally {
      setLoading(false)
    }
  }, [budgetYear, threshold])

  useEffect(() => { load() }, [load])

  const chartData = data.slice(0, 15).map(d => ({
    name: d.vendor_name.length > 8 ? d.vendor_name.slice(0, 8) + '…' : d.vendor_name,
    fullName: d.vendor_name,
    percentage: d.percentage,
    amount: d.total_amount,
    high: d.is_high_concentration,
  }))

  const columns = [
    { title: '廠商名稱', dataIndex: 'vendor_name', key: 'vendor_name',
      render: (v: string, rec: VendorConcentrationItem) => (
        <Space>
          {rec.is_high_concentration && <WarningOutlined style={{ color: '#ff4d4f' }} />}
          <Text strong={rec.is_high_concentration}>{v}</Text>
        </Space>
      ),
    },
    { title: '合約數', dataIndex: 'contract_count', key: 'contract_count', width: 80, align: 'center' as const },
    { title: '合約總額', dataIndex: 'total_amount', key: 'total_amount', width: 150, align: 'right' as const,
      render: (v: number) => fmtMoney(v),
    },
    { title: '佔比', dataIndex: 'percentage', key: 'percentage', width: 100, align: 'right' as const,
      render: (v: number, rec: VendorConcentrationItem) => (
        <Tag color={rec.is_high_concentration ? 'error' : v >= 15 ? 'warning' : 'default'}>
          {v.toFixed(1)}%
        </Tag>
      ),
    },
    { title: '集中度警示', dataIndex: 'is_high_concentration', key: 'warn', width: 100,
      render: (v: boolean) => v ? <Tag color="error">⚠ 過高</Tag> : <Tag color="success">正常</Tag>,
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select value={budgetYear} onChange={v => setBudgetYear(v)} style={{ width: 100 }} allowClear placeholder="全部年度">
          {YEAR_OPTIONS.map(y => <Select.Option key={y} value={y}>{y} 年</Select.Option>)}
        </Select>
        <Select value={threshold} onChange={setThreshold} style={{ width: 140 }}>
          <Select.Option value={20}>警示閾值：20%</Select.Option>
          <Select.Option value={30}>警示閾值：30%</Select.Option>
          <Select.Option value={40}>警示閾值：40%</Select.Option>
          <Select.Option value={50}>警示閾值：50%</Select.Option>
        </Select>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新載入</Button>
      </Space>

      {highCount > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message={`集中度警示：${highCount} 家廠商合約金額佔比超過 ${threshold}%，建議評估分散風險`}
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Statistic title="合約組合總額" value={grandTotal} formatter={v => fmtMoney(Number(v))} />
        </Col>
        <Col span={8}>
          <Statistic title="廠商數量" value={data.length} suffix="家" />
        </Col>
        <Col span={8}>
          <Statistic title="高集中度廠商" value={highCount} suffix={`家 (>${threshold}%)`}
            valueStyle={{ color: highCount > 0 ? '#ff4d4f' : undefined }} />
        </Col>
      </Row>

      <Spin spinning={loading}>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number, n, props) => [`${v.toFixed(1)}% (${fmtMoney(props.payload.amount)})`, '佔比']}
              labelFormatter={(l, items) => items[0]?.payload?.fullName || l} />
            <ReferenceLine y={threshold} stroke="#ff4d4f" strokeDasharray="4 2"
              label={{ value: `${threshold}%警示線`, fill: '#ff4d4f', fontSize: 11, position: 'right' }} />
            <Bar dataKey="percentage" name="佔比" isAnimationActive={false}
              label={{ position: 'top', formatter: (v: number) => `${v.toFixed(1)}%`, fontSize: 10 }}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.high ? '#ff4d4f' : '#4BA8E8'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Spin>

      <Table
        dataSource={data}
        columns={columns}
        rowKey="vendor_id"
        loading={loading}
        size="small"
        pagination={{ pageSize: 10 }}
        style={{ marginTop: 16 }}
        rowClassName={(r: VendorConcentrationItem) =>
          r.is_high_concentration ? 'ant-table-row-danger' : ''}
      />
    </div>
  )
}


// ─────────────────────────────────────────────────────────────────────────────
// J2 — 合約成本趨勢圖
// ─────────────────────────────────────────────────────────────────────────────

export function CostTrendChart({ companyOptions }: { companyOptions: string[] }) {
  const [data, setData] = useState<CostTrendPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [budgetYear, setBudgetYear] = useState(currentYear)
  const [granularity, setGranularity] = useState<'month' | 'quarter'>('month')
  const [company, setCompany] = useState<string | undefined>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchCostTrend({ budget_year: budgetYear, granularity, company })
      setData(res.data)
    } catch {
      message.error('載入成本趨勢失敗')
    } finally {
      setLoading(false)
    }
  }, [budgetYear, granularity, company])

  useEffect(() => { load() }, [load])

  const chartData = data.map(d => ({
    ...d,
    contract_amount: d.contract_amount / 10000,
    claimed_amount: d.claimed_amount / 10000,
  }))

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select value={budgetYear} onChange={setBudgetYear} style={{ width: 100 }}>
          {YEAR_OPTIONS.map(y => <Select.Option key={y} value={y}>{y} 年</Select.Option>)}
        </Select>
        <Radio.Group value={granularity} onChange={e => setGranularity(e.target.value)} buttonStyle="solid">
          <Radio.Button value="month">月</Radio.Button>
          <Radio.Button value="quarter">季</Radio.Button>
        </Radio.Group>
        <Select value={company} onChange={setCompany} style={{ width: 140 }} allowClear placeholder="全部公司">
          {companyOptions.map(c => <Select.Option key={c} value={c}>{c}</Select.Option>)}
        </Select>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新載入</Button>
      </Space>

      {data.length === 0 && !loading ? (
        <Empty description="此年度無資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Spin spinning={loading}>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ left: 10, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={v => `${v}萬`} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v: number, name: string) => [
                  `${(v).toFixed(1)} 萬`,
                  name === 'contract_amount' ? '新簽合約總額' : '已核准請款',
                ]}
              />
              <Legend formatter={(v) => v === 'contract_amount' ? '新簽合約總額' : '已核准請款'} />
              <Line type="monotone" dataKey="contract_amount" stroke="#1B3A5C" strokeWidth={2}
                dot={{ r: 4 }} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="claimed_amount" stroke="#4BA8E8" strokeWidth={2}
                strokeDasharray="5 3" dot={{ r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
          <Text type="secondary" style={{ fontSize: 11, display: 'block', textAlign: 'center' }}>
            金額單位：萬元（TWD）
          </Text>
        </Spin>
      )}
    </div>
  )
}


// ─────────────────────────────────────────────────────────────────────────────
// J3 — 月度/季度報表
// ─────────────────────────────────────────────────────────────────────────────

export function SummaryReportTab() {
  const [rows, setRows] = useState<SummaryReportRow[]>([])
  const [totals, setTotals] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [budgetYear, setBudgetYear] = useState(currentYear)
  const [periodType, setPeriodType] = useState<'monthly' | 'quarterly'>('monthly')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchSummaryReport(budgetYear, periodType)
      setRows(res.rows)
      setTotals(res.totals)
    } catch {
      message.error('載入報表失敗')
    } finally {
      setLoading(false)
    }
  }, [budgetYear, periodType])

  useEffect(() => { load() }, [load])

  const columns = [
    { title: '期間', dataIndex: 'label', key: 'label', width: 80,
      render: (v: string, r: SummaryReportRow) => <Text strong>{r.period === totals ? '' : v}</Text>,
    },
    { title: '新簽合約數', dataIndex: 'new_contracts', key: 'new_contracts', width: 100, align: 'center' as const },
    { title: '新簽金額（含稅）', dataIndex: 'new_amount', key: 'new_amount', align: 'right' as const,
      render: (v: number) => fmtMoney(v),
    },
    { title: '請款筆數', dataIndex: 'claim_count', key: 'claim_count', width: 90, align: 'center' as const },
    { title: '請款金額', dataIndex: 'claim_amount', key: 'claim_amount', align: 'right' as const,
      render: (v: number) => fmtMoney(v),
    },
    { title: '已核准金額', dataIndex: 'approved_amount', key: 'approved_amount', align: 'right' as const,
      render: (v: number) => <Text style={{ color: '#52c41a', fontWeight: 600 }}>{fmtMoney(v)}</Text>,
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select value={budgetYear} onChange={setBudgetYear} style={{ width: 100 }}>
          {YEAR_OPTIONS.map(y => <Select.Option key={y} value={y}>{y} 年</Select.Option>)}
        </Select>
        <Radio.Group value={periodType} onChange={e => setPeriodType(e.target.value)} buttonStyle="solid">
          <Radio.Button value="monthly">月度</Radio.Button>
          <Radio.Button value="quarterly">季度</Radio.Button>
        </Radio.Group>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新載入</Button>
        <Button
          type="primary" ghost
          icon={<DownloadOutlined />}
          onClick={() => exportSummaryReport(budgetYear, periodType)}
        >
          匯出 Excel
        </Button>
      </Space>

      {totals && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Statistic title="新簽合約總數" value={totals.new_contracts} suffix="份" /></Col>
          <Col span={6}><Statistic title="新簽金額" value={totals.new_amount} formatter={v => fmtMoney(Number(v))} /></Col>
          <Col span={6}><Statistic title="請款總筆數" value={totals.claim_count} suffix="筆" /></Col>
          <Col span={6}><Statistic title="已核准金額" value={totals.approved_amount} formatter={v => fmtMoney(Number(v))} valueStyle={{ color: '#52c41a' }} /></Col>
        </Row>
      )}

      <Table
        dataSource={rows}
        columns={columns}
        rowKey="period"
        loading={loading}
        size="small"
        pagination={false}
        summary={() =>
          totals ? (
            <Table.Summary fixed>
              <Table.Summary.Row style={{ fontWeight: 700, background: '#f0f4f8' }}>
                <Table.Summary.Cell index={0}>合計</Table.Summary.Cell>
                <Table.Summary.Cell index={1} align="center">{totals.new_contracts}</Table.Summary.Cell>
                <Table.Summary.Cell index={2} align="right">{fmtMoney(totals.new_amount)}</Table.Summary.Cell>
                <Table.Summary.Cell index={3} align="center">{totals.claim_count}</Table.Summary.Cell>
                <Table.Summary.Cell index={4} align="right">{fmtMoney(totals.claim_amount)}</Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right" style={{ color: '#52c41a' }}>{fmtMoney(totals.approved_amount)}</Table.Summary.Cell>
              </Table.Summary.Row>
            </Table.Summary>
          ) : null
        }
      />
    </div>
  )
}
