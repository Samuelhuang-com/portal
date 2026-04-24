/**
 * 預算比較報表 (SCR-17)
 */
import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Col,
  Input,
  Progress,
  Row,
  Select,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import {
  getBudgetVsActual,
  getBudgetPlans,
  getDepartments,
  type BudgetPlan,
  type Department,
} from '@/api/budget'

const { Title } = Typography

const fmt = (n?: number | null) =>
  n != null ? new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 }).format(n) : '-'

export default function BudgetVsActualPage() {
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState<Record<string, unknown>[]>([])
  const [total, setTotal] = useState(0)
  const [plans, setPlans] = useState<BudgetPlan[]>([])
  const [depts, setDepts] = useState<Department[]>([])

  const [viewType, setViewType] = useState<'total' | 'monthly'>('total')
  const [filterPlan, setFilterPlan] = useState<string | undefined>()
  const [filterDept, setFilterDept] = useState<string | undefined>()
  const [filterAccount, setFilterAccount] = useState<string>('')

  useEffect(() => {
    getBudgetPlans().then((r) => setPlans(r.data))
    getDepartments().then((r) => setDepts(r.data))
  }, [])

  const search = () => {
    setLoading(true)
    getBudgetVsActual({
      view_type: viewType,
      plan_code: filterPlan,
      dept_name: filterDept,
      account_code_name: filterAccount || undefined,
    })
      .then((r) => {
        setItems(r.data.items as Record<string, unknown>[])
        setTotal(r.data.total)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { search() }, [viewType])

  const totalColumns = [
    { title: '部門', dataIndex: 'dept_name', key: 'dept_name', width: 100 },
    { title: '計畫', dataIndex: 'plan_name', key: 'plan_name', width: 160, ellipsis: true },
    { title: '會計科目', dataIndex: 'account_code_name', key: 'account', ellipsis: true },
    {
      title: '年度預算',
      dataIndex: 'annual_budget',
      key: 'annual_budget',
      align: 'right' as const,
      render: (v: number) => fmt(v),
    },
    {
      title: '年度實績',
      dataIndex: 'annual_actual',
      key: 'annual_actual',
      align: 'right' as const,
      render: (v: number) => fmt(v),
    },
    {
      title: '預算餘額',
      dataIndex: 'annual_variance',
      key: 'annual_variance',
      align: 'right' as const,
      render: (v: number) => (
        <span style={{ color: v < 0 ? '#cf1322' : '#3f8600' }}>{fmt(v)}</span>
      ),
    },
    {
      title: '執行率',
      key: 'exec_rate',
      width: 140,
      render: (_: unknown, r: Record<string, unknown>) => {
        const b = Number(r.annual_budget) || 0
        const a = Number(r.annual_actual) || 0
        const rate = b > 0 ? Math.round((a / b) * 1000) / 10 : 0
        return (
          <Progress
            percent={Math.min(rate, 100)}
            size="small"
            format={() => `${rate}%`}
            strokeColor={rate >= 100 ? '#cf1322' : rate >= 85 ? '#faad14' : '#3f8600'}
          />
        )
      },
    },
  ]

  const monthlyColumns = [
    { title: '部門', dataIndex: 'dept_name', key: 'dept_name', width: 90 },
    { title: '會計科目', dataIndex: 'account_code_name', key: 'account', width: 140, ellipsis: true },
    { title: '月份', dataIndex: 'month_num', key: 'month_num', width: 60, render: (v: number) => `${v}月` },
    { title: '月預算', dataIndex: 'budget_amount', key: 'budget', align: 'right' as const, render: (v: number) => fmt(v) },
    { title: '月實績', dataIndex: 'actual_amount', key: 'actual', align: 'right' as const, render: (v: number) => fmt(v) },
    {
      title: '差異',
      dataIndex: 'variance_amount',
      key: 'variance',
      align: 'right' as const,
      render: (v: number) => (
        <span style={{ color: v < 0 ? '#cf1322' : '#3f8600' }}>{fmt(v)}</span>
      ),
    },
  ]

  return (
    <div>
      <Title level={4}>預算比較報表</Title>

      {/* ── Filters ── */}
      <Card style={{ marginBottom: 12 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col>
            <Select
              value={viewType}
              onChange={setViewType}
              style={{ width: 130 }}
              options={[
                { label: '年度彙總', value: 'total' },
                { label: '月別明細', value: 'monthly' },
              ]}
            />
          </Col>
          <Col>
            <Select
              placeholder="選擇預算計畫"
              allowClear
              style={{ width: 200 }}
              value={filterPlan}
              onChange={setFilterPlan}
              showSearch
              optionFilterProp="label"
              options={plans.map((p) => ({ label: p.plan_code, value: p.plan_code }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="選擇部門"
              allowClear
              style={{ width: 110 }}
              value={filterDept}
              onChange={setFilterDept}
              options={depts.map((d) => ({ label: d.dept_name, value: d.dept_name }))}
            />
          </Col>
          <Col flex="auto">
            <Input
              placeholder="搜尋會計科目"
              prefix={<SearchOutlined />}
              value={filterAccount}
              onChange={(e) => setFilterAccount(e.target.value)}
              allowClear
            />
          </Col>
          <Col>
            <Button type="primary" onClick={search}>查詢</Button>
          </Col>
        </Row>
      </Card>

      {/* ── Summary Tag ── */}
      <div style={{ marginBottom: 8 }}>
        <Tag>共 {total} 筆</Tag>
      </div>

      {/* ── Table ── */}
      <Card>
        {loading ? (
          <Spin style={{ display: 'block', margin: '60px auto' }} />
        ) : (
          <Table
            dataSource={items}
            rowKey={(r, i) => String(i)}
            size="small"
            pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }}
            columns={viewType === 'total' ? totalColumns : monthlyColumns}
            scroll={{ x: 900 }}
          />
        )}
      </Card>
    </div>
  )
}
