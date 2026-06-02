/**
 * 合約管理 — Dashboard 頁面
 *
 * KPI 統計 + 圖表：
 *   Row 1 — 4 個合約 KPI 卡（生效中 / 年度總額 / 90天到期 / 高風險）
 *   Row 2 — 2 個請款 KPI 卡（當月請款金額 / 待審核筆數）
 *   Row 3 — 部門合約金額長條圖 + 合約狀態圓餅圖
 *   Row 4 — 即將到期合約列表 + 請款狀態分佈圓餅圖
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Row, Col, Card, Statistic, Typography, Breadcrumb,
  Empty, Spin, message, Select, Table, Tag, Badge, Tabs, Button,
} from 'antd'
import {
  HomeOutlined, FileProtectOutlined,
  ClockCircleOutlined, WarningOutlined, DollarOutlined,
  AlertOutlined, AuditOutlined,
  LineChartOutlined, FileExcelOutlined, TeamOutlined,
  QuestionCircleOutlined, ExportOutlined,
} from '@ant-design/icons'
import {
  VendorConcentrationChart,
  CostTrendChart,
  SummaryReportTab,
} from './AnalyticsTabs'
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'

import {
  fetchDashboardKPI, fetchDashboardByDept, fetchContractStats,
  fetchExpiringContracts, fetchClaimsStats,
} from '@/api/contract'
import { companiesApi } from '@/api/referenceData'
import type { CompanyOption } from '@/api/referenceData'
import { NAV_GROUP } from '@/constants/navLabels'

const { Option } = Select

// 顏色常數
const COLORS       = ['#1B3A5C', '#4BA8E8', '#52C41A', '#FAAD14', '#FF4D4F', '#722ED1']
const CLAIM_COLORS: Record<string, string> = {
  '待審核': '#FAAD14',
  '已核准': '#52C41A',
  '已拒絕': '#FF4D4F',
  '已付款': '#1B3A5C',
}

// 年度選項
const currentYear = new Date().getFullYear()
const yearOptions = [currentYear - 1, currentYear, currentYear + 1]

// 部門金額 Tooltip
const DeptTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  return (
    <div style={{ background: '#fff', border: '1px solid #d9d9d9', borderRadius: 6, padding: '8px 12px', fontSize: 13 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.dept}</div>
      <div>金額：${d.amount.toLocaleString('zh-TW')}</div>
      <div>合約數：{d.count} 份</div>
    </div>
  )
}

// 到期緊急程度
function urgencyColor(days: number) {
  if (days <= 30) return '#FF4D4F'
  if (days <= 60) return '#FA8C16'
  return '#FAAD14'
}
function urgencyTag(days: number) {
  if (days <= 30) return <Tag color="error">{days} 天</Tag>
  if (days <= 60) return <Tag color="warning">{days} 天</Tag>
  return <Tag color="gold">{days} 天</Tag>
}

export default function ContractDashboard() {
  const [kpi, setKpi]                   = useState<any>(null)
  const [deptData, setDeptData]         = useState<Array<{ dept: string; amount: number; count: number }>>([])
  const [statsByStatus, setStatsByStatus] = useState<Array<{ name: string; value: number }>>([])
  const [expiring, setExpiring]         = useState<any[]>([])
  const [claimsStats, setClaimsStats]   = useState<any>(null)
  const [claimsPieData, setClaimsPieData] = useState<Array<{ name: string; value: number }>>([])
  const [loading, setLoading]           = useState(false)
  const [budgetYear, setBudgetYear]     = useState<number>(currentYear)
  // 公司別篩選（部門金額圖）
  const [deptCompany, setDeptCompany]   = useState<string | undefined>(undefined)
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([])
  const navigate = useNavigate()

  // 載入公司別選項
  useEffect(() => {
    companiesApi.options()
      .then(res => setCompanyOptions(Array.isArray(res.data) ? res.data : []))
      .catch(() => {})
  }, [])

  // 只重新載入部門金額（公司篩選變更時）
  const loadDeptData = React.useCallback(async (year: number, company?: string) => {
    try {
      const deptResult = await fetchDashboardByDept(year, company)
      const sortedDept = [...(deptResult.items || [])].sort((a, b) => b.amount - a.amount)
      setDeptData(sortedDept)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadDeptData(budgetYear, deptCompany)
  }, [deptCompany, loadDeptData])

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const [kpiResult, deptResult, statsResult, expiringResult, claimsResult] = await Promise.all([
          fetchDashboardKPI(budgetYear),
          fetchDashboardByDept(budgetYear, deptCompany),
          fetchContractStats(),
          fetchExpiringContracts(90),
          fetchClaimsStats(),
        ])

        setKpi(kpiResult)

        const sortedDept = [...(deptResult.items || [])].sort((a, b) => b.amount - a.amount)
        setDeptData(sortedDept)

        const statusData = Object.entries(statsResult.by_status || {}).map(
          ([name, value]) => ({ name, value: value as number }),
        )
        setStatsByStatus(statusData)

        setExpiring(expiringResult.items || [])

        setClaimsStats(claimsResult)
        const claimsPie = Object.entries(claimsResult.by_status || {}).map(
          ([name, value]) => ({ name, value: value as number }),
        )
        setClaimsPieData(claimsPie)
      } catch (err) {
        message.error('載入數據失敗')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [budgetYear])

  // 到期合約 Table 欄位
  const expiringColumns = [
    {
      title: '合約編號',
      dataIndex: 'contract_id',
      key: 'contract_id',
      width: 130,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</span>,
    },
    {
      title: '合約名稱',
      dataIndex: 'contract_name',
      key: 'contract_name',
      ellipsis: true,
    },
    {
      title: '廠商',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      ellipsis: true,
      width: 120,
    },
    {
      title: '截止日',
      dataIndex: 'end_date',
      key: 'end_date',
      width: 100,
    },
    {
      title: '剩餘天數',
      dataIndex: 'remaining_days',
      key: 'remaining_days',
      width: 90,
      align: 'center' as const,
      render: (days: number) => urgencyTag(days),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 麵包屑 + 年度選擇器 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Breadcrumb>
          <Breadcrumb.Item><HomeOutlined /></Breadcrumb.Item>
          <Breadcrumb.Item>{NAV_GROUP.contract}</Breadcrumb.Item>
          <Breadcrumb.Item>Dashboard</Breadcrumb.Item>
        </Breadcrumb>
        <Select value={budgetYear} onChange={(val) => setBudgetYear(val)} style={{ width: 120 }}>
          {yearOptions.map((y) => (
            <Option key={y} value={y}>{y} 年</Option>
          ))}
        </Select>
      </div>

      <Spin spinning={loading}>

        {/* ── Row 1：合約 KPI ─────────────────────────────── */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="生效中合約"
                value={kpi?.active_contracts ?? '-'}
                valueStyle={{ color: '#1B3A5C' }}
                prefix={<FileProtectOutlined />}
                suffix="份"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="年度合約總額"
                value={kpi?.total_annual_amount ?? 0}
                prefix="$"
                precision={0}
                formatter={(v) => Number(v).toLocaleString('zh-TW')}
                valueStyle={{ color: '#1B3A5C' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card
              hoverable
              style={{ cursor: 'pointer' }}
              onClick={() => navigate('/contract/expiring')}
            >
              <Statistic
                title="90 天內到期"
                value={kpi?.expiring_in_90days ?? '-'}
                valueStyle={{ color: '#FAAD14' }}
                prefix={<ClockCircleOutlined />}
                suffix="份"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card>
              <Statistic
                title="高風險合約"
                value={kpi?.high_risk_count ?? '-'}
                valueStyle={{ color: '#FF4D4F' }}
                prefix={<WarningOutlined />}
                suffix="份"
              />
            </Card>
          </Col>
        </Row>

        {/* ── Row 2：請款 KPI ─────────────────────────────── */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12}>
            <Card>
              <Statistic
                title="當月請款金額"
                value={claimsStats?.monthly_amount ?? 0}
                prefix={<DollarOutlined style={{ color: '#722ED1' }} />}
                formatter={(v) => `$ ${Number(v).toLocaleString('zh-TW')}`}
                valueStyle={{ color: '#722ED1' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12}>
            <Card
              hoverable
              style={{ cursor: 'pointer' }}
              onClick={() => navigate('/contract/claims')}
            >
              <Statistic
                title="待審核請款"
                value={claimsStats?.pending_count ?? 0}
                valueStyle={{ color: '#FA8C16' }}
                prefix={<AuditOutlined />}
                suffix="筆"
              />
            </Card>
          </Col>
        </Row>

        {/* ── Row 3：圖表（部門金額 + 合約狀態）───────────── */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={14}>
            <Card
              title={`${budgetYear} 年各部門合約金額${deptCompany ? `（${deptCompany}）` : ''}`}
              extra={
                <Select
                  allowClear
                  showSearch
                  placeholder="篩選公司別"
                  style={{ width: 140 }}
                  size="small"
                  value={deptCompany}
                  optionFilterProp="label"
                  options={companyOptions}
                  onChange={(val) => setDeptCompany(val ?? undefined)}
                />
              }
            >
              {deptData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={deptData} layout="vertical" margin={{ top: 4, right: 40, left: 80, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" tickFormatter={(v) => `$${(v / 10000).toFixed(0)}萬`} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="dept" width={80} tick={{ fontSize: 11 }} />
                    <Tooltip content={<DeptTooltip />} />
                    <Bar dataKey="amount" fill="#4BA8E8" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Empty description={deptCompany ? `${deptCompany} 無部門合約資料` : '無部門資料'} style={{ padding: '40px 0' }} />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="合約狀態分佈">
              {statsByStatus.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie data={statsByStatus} dataKey="value" nameKey="name"
                      cx="50%" cy="50%" outerRadius={90}
                      label={({ name, value }) => `${name}: ${value}`} labelLine>
                      {statsByStatus.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [`${value} 份`, '合約數']} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="無狀態資料" style={{ padding: '40px 0' }} />
              )}
            </Card>
          </Col>
        </Row>

        {/* ── Row 4：到期列表 + 請款狀態圓餅圖 ───────────── */}
        <Row gutter={16}>
          <Col xs={24} lg={14}>
            <Card
              title={
                <span>
                  <AlertOutlined style={{ color: '#FAAD14', marginRight: 6 }} />
                  即將到期合約（90 天內）
                  {expiring.length > 0 && (
                    <Badge count={expiring.length} style={{ marginLeft: 8, backgroundColor: '#FAAD14' }} />
                  )}
                </span>
              }
            >
              {expiring.length > 0 ? (
                <Table
                  dataSource={expiring}
                  columns={expiringColumns}
                  rowKey="contract_id"
                  size="small"
                  pagination={false}
                  scroll={{ y: 240 }}
                  rowClassName={(record) =>
                    record.remaining_days <= 30 ? 'expiring-row-danger' : ''
                  }
                  onRow={(record) => ({
                    onClick: () => navigate(`/contract/expiring`),
                    style: { cursor: 'pointer' },
                  })}
                />
              ) : (
                <Empty description="90 天內無即將到期合約" style={{ padding: '32px 0' }} />
              )}
              <style>{`
                .expiring-row-danger td { background: #fff2f0 !important; }
              `}</style>
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title={
              <span>
                <DollarOutlined style={{ color: '#722ED1', marginRight: 6 }} />
                請款狀態分佈
              </span>
            }>
              {claimsPieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={claimsPieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      label={({ name, value }) => `${name}: ${value}`}
                      labelLine
                    >
                      {claimsPieData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={CLAIM_COLORS[entry.name] ?? '#8884d8'}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value, name, props) => {
                        const amt = claimsStats?.by_status_amount?.[props.payload.name] ?? 0
                        return [`${value} 筆 / $${Number(amt).toLocaleString('zh-TW')}`, name]
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <Empty description="尚無請款記錄" style={{ padding: '40px 0' }} />
              )}
            </Card>
          </Col>
        </Row>

      </Spin>

      {/* ── Phase J 分析 + 說明指南 Tabs ─────────────────── */}
      <Card style={{ marginTop: 24 }} bodyStyle={{ padding: '0 24px 24px' }}>
        <Tabs
          items={[
            {
              key: 'concentration',
              label: <span><TeamOutlined /> 廠商集中度分析</span>,
              children: <VendorConcentrationChart />,
            },
            {
              key: 'trend',
              label: <span><LineChartOutlined /> 成本趨勢圖</span>,
              children: <CostTrendChart companyOptions={companyOptions.map(c => c.label)} />,
            },
            {
              key: 'report',
              label: <span><FileExcelOutlined /> 月度/季度報表</span>,
              children: <SummaryReportTab />,
            },
            {
              key: 'guide',
              label: <span><QuestionCircleOutlined /> 說明指南</span>,
              children: (
                <div>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 8, paddingTop: 16,
                  }}>
                    <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                      合約管理系統操作暨技術手冊 v2.02.0
                    </Typography.Text>
                    <Button
                      size="small"
                      icon={<ExportOutlined />}
                      onClick={() => window.open('/docs-static/contract_manual.html', '_blank')}
                    >
                      新視窗開啟
                    </Button>
                  </div>
                  <iframe
                    src="/docs-static/contract_manual.html"
                    style={{
                      width: '100%',
                      height: 'calc(100vh - 280px)',
                      minHeight: 600,
                      border: '1px solid #e0e6ed',
                      borderRadius: 6,
                    }}
                    title="合約管理系統說明指南"
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
