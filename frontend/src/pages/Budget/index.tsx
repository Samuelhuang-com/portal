/**
 * 預算管理 Dashboard (SCR-01)
 * 顯示年度 KPI 總覽：總預算、實績、執行率、超支摘要、部門摘要
 */
import { useEffect, useState } from 'react'
import {
  Card,
  Col,
  Modal,
  Row,
  Statistic,
  Select,
  Table,
  Tag,
  Progress,
  Alert,
  Spin,
  Typography,
} from 'antd'
import {
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { getBudgetDashboard, getBudgetYears, type DashboardData, type BudgetYear } from '@/api/budget'

const { Title, Text } = Typography

const fmt = (n: number) =>
  new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 }).format(n)

// ── 列狀態 ──────────────────────────────────────────────────────────────────
type DeptRow = { exec_rate: number }

/** 部門摘要表列背景色 class */
const deptRowClass = (r: DeptRow) => {
  if (r.exec_rate >= 100) return 'budget-row-overrun'
  if (r.exec_rate >= 85)  return 'budget-row-near-overrun'
  return ''
}

/** 部門名稱前警示 Icon */
const DeptNameCell = ({ name, execRate }: { name: string; execRate: number }) => (
  <>
    {execRate >= 100 && (
      <WarningOutlined style={{ color: '#cf1322', marginRight: 5, fontSize: 13 }} />
    )}
    {execRate >= 85 && execRate < 100 && (
      <ExclamationCircleOutlined style={{ color: '#faad14', marginRight: 5, fontSize: 13 }} />
    )}
    {name}
  </>
)

const STORAGE_KEY = 'budget_dashboard_year_id'

export default function BudgetDashboardPage() {
  const [years, setYears] = useState<BudgetYear[]>([])
  const [yearId, setYearId] = useState<number>(1)
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [modalType, setModalType] = useState<'overrun' | 'near_overrun' | null>(null)

  useEffect(() => {
    getBudgetYears().then((r) => {
      setYears(r.data)
      if (r.data.length === 0) return
      const saved = Number(localStorage.getItem(STORAGE_KEY))
      const valid = saved && r.data.some((y) => y.id === saved)
      setYearId(valid ? saved : r.data[0].id)
    })
  }, [])

  const handleYearChange = (id: number) => {
    localStorage.setItem(STORAGE_KEY, String(id))
    setYearId(id)
  }

  useEffect(() => {
    setLoading(true)
    getBudgetDashboard(yearId)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false))
  }, [yearId])

  if (loading) return <Spin style={{ display: 'block', marginTop: 80 }} />

  const s = data?.summary
  const execRateColor =
    (s?.exec_rate ?? 0) >= 100 ? '#cf1322' : (s?.exec_rate ?? 0) >= 85 ? '#faad14' : '#3f8600'

  return (
    <div>
      {/* ── 超支警示 CSS ── */}
      <style>{`
        .budget-row-overrun td      { background-color: #fff1f0 !important; }
        .budget-row-near-overrun td { background-color: #fffbe6 !important; }
        .budget-row-overrun:hover td      { background-color: #ffe7e6 !important; }
        .budget-row-near-overrun:hover td { background-color: #fff3cd !important; }
        .budget-row-overrun-static td { background-color: #fff1f0 !important; }
        .budget-row-overrun-static:hover td { background-color: #ffe7e6 !important; }
      `}</style>

      {/* ── Header ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0 }}>預算管理 Dashboard</Title>
        <Select
          value={yearId}
          onChange={handleYearChange}
          style={{ width: 120 }}
          options={years.map((y) => ({ label: `${y.budget_year} 年`, value: y.id }))}
        />
      </div>

      {/* ── KPI Cards ── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="年度總預算"
              value={fmt(s?.total_budget ?? 0)}
              prefix={<DollarOutlined />}
              suffix="元"
              valueStyle={{ color: '#1B3A5C' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="年度總實績"
              value={fmt(s?.total_actual ?? 0)}
              prefix={<RiseOutlined />}
              suffix="元"
              valueStyle={{ color: '#4BA8E8' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="預算餘額"
              value={fmt(s?.variance ?? 0)}
              prefix={<FallOutlined />}
              suffix="元"
              valueStyle={{ color: (s?.variance ?? 0) >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">執行率</Text>
            </div>
            <Progress
              percent={s?.exec_rate ?? 0}
              strokeColor={execRateColor}
              format={(p) => `${p}%`}
            />
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <Tag
                color="red"
                style={{ cursor: (s?.overrun_count ?? 0) > 0 ? 'pointer' : 'default' }}
                onClick={() => (s?.overrun_count ?? 0) > 0 && setModalType('overrun')}
              >
                超支 {s?.overrun_count ?? 0} 項
              </Tag>
              <Tag
                color="orange"
                style={{ cursor: (s?.near_overrun_count ?? 0) > 0 ? 'pointer' : 'default' }}
                onClick={() => (s?.near_overrun_count ?? 0) > 0 && setModalType('near_overrun')}
              >
                即將超支 {s?.near_overrun_count ?? 0} 項
              </Tag>
            </div>
          </Card>
        </Col>
      </Row>

      {/* ── Data Quality Warning ── */}
      {data && (data.data_quality.dq_issue_count > 0 || data.data_quality.missing_amount_count > 0) && (
        <Alert
          style={{ marginTop: 16 }}
          type="warning"
          icon={<WarningOutlined />}
          showIcon
          message={
            `資料品質問題：公式異常 ${data.data_quality.dq_issue_count} 筆 ／ 金額缺漏 ${data.data_quality.missing_amount_count} 筆 ／ 未對應明細 ${data.data_quality.unresolved_plan_count} 筆`
          }
          description="請至「報表 → 資料品質」頁面查看明細，並人工修正後重新統計。"
        />
      )}

      {/* ── Department Summary ── */}
      <Card style={{ marginTop: 20 }} title="部門預算摘要">
        <Table
          dataSource={data?.dept_summary ?? []}
          rowKey="dept_name"
          size="small"
          pagination={false}
          rowClassName={(r) => deptRowClass(r as DeptRow)}
          columns={[
            {
              title: '部門',
              dataIndex: 'dept_name',
              key: 'dept_name',
              width: 140,
              render: (v: string, r) => (
                <DeptNameCell name={v} execRate={(r as DeptRow).exec_rate} />
              ),
            },
            {
              title: '年度預算',
              dataIndex: 'plan_budget',
              key: 'plan_budget',
              align: 'right',
              render: (v: number) => fmt(v),
            },
            {
              title: '年度實績',
              dataIndex: 'actual_amount',
              key: 'actual_amount',
              align: 'right',
              render: (v: number) => fmt(v),
            },
            {
              title: '預算餘額',
              dataIndex: 'variance',
              key: 'variance',
              align: 'right',
              render: (v: number) => (
                <span style={{ color: v >= 0 ? '#3f8600' : '#cf1322', fontWeight: v < 0 ? 600 : 400 }}>
                  {v < 0 && <WarningOutlined style={{ marginRight: 4, fontSize: 11 }} />}
                  {fmt(v)}
                </span>
              ),
            },
            {
              title: '執行率',
              dataIndex: 'exec_rate',
              key: 'exec_rate',
              width: 140,
              render: (v: number) => (
                <Progress
                  percent={Math.min(v, 100)}
                  size="small"
                  strokeColor={v >= 100 ? '#cf1322' : v >= 85 ? '#faad14' : '#3f8600'}
                  format={() => `${v}%`}
                />
              ),
            },
          ]}
        />
      </Card>

      {/* ── Overrun Items ── */}
      {(data?.overrun_items?.length ?? 0) > 0 && (
        <Card
          style={{ marginTop: 16, borderColor: '#ffccc7' }}
          headStyle={{ background: 'linear-gradient(135deg, #c0392b, #e74c3c, #e67e22)', color: '#fff' }}
          title={<span style={{ color: '#fff' }}><WarningOutlined style={{ marginRight: 6 }} />超支科目清單（共 {data!.overrun_items.length} 項）</span>}
        >
          <Table
            dataSource={data!.overrun_items}
            rowKey={(r) => `${r.dept_name}-${r.account_code_name}`}
            size="small"
            pagination={false}
            rowClassName={() => 'budget-row-overrun-static'}
            columns={[
              {
                title: '部門',
                dataIndex: 'dept_name',
                width: 120,
                render: (v: string) => (
                  <span><WarningOutlined style={{ color: '#cf1322', marginRight: 5, fontSize: 12 }} />{v}</span>
                ),
              },
              { title: '會計科目', dataIndex: 'account_code_name' },
              { title: '年度預算', dataIndex: 'annual_budget', align: 'right', render: (v: number) => fmt(v) },
              { title: '年度實績', dataIndex: 'annual_actual', align: 'right', render: (v: number) => <span style={{ color: '#cf1322', fontWeight: 600 }}>{fmt(v)}</span> },
              {
                title: '超支金額', dataIndex: 'annual_variance', align: 'right',
                render: (v: number) => (
                  <span style={{ color: '#cf1322', fontWeight: 700 }}>▲ {fmt(Math.abs(v))}</span>
                ),
              },
            ]}
          />
        </Card>
      )}

      {/* ── 超支明細 Modal ── */}
      <Modal
        open={modalType === 'overrun'}
        title={<><Tag color="red">超支科目</Tag> 明細 — 共 {data?.overrun_items?.length ?? 0} 項</>}
        onCancel={() => setModalType(null)}
        footer={null}
        width={780}
      >
        <Table
          dataSource={data?.overrun_items ?? []}
          rowKey={(r) => `${r.dept_name}-${r.account_code_name}`}
          size="small"
          pagination={false}
          columns={[
            { title: '部門', dataIndex: 'dept_name', width: 110 },
            { title: '會計科目', dataIndex: 'account_code_name' },
            {
              title: '年度預算',
              dataIndex: 'annual_budget',
              align: 'right' as const,
              render: (v: number) => fmt(v),
            },
            {
              title: '年度實績',
              dataIndex: 'annual_actual',
              align: 'right' as const,
              render: (v: number) => fmt(v),
            },
            {
              title: '超支金額',
              dataIndex: 'annual_variance',
              align: 'right' as const,
              render: (v: number) => (
                <span style={{ color: '#cf1322', fontWeight: 600 }}>{fmt(Math.abs(v))}</span>
              ),
            },
            {
              title: '超支率',
              key: 'overrun_rate',
              align: 'right' as const,
              render: (_: unknown, r) =>
                (r as { annual_budget: number; annual_actual: number }).annual_budget > 0
                  ? <span style={{ color: '#cf1322' }}>{(((r as { annual_budget: number; annual_actual: number }).annual_actual / (r as { annual_budget: number; annual_actual: number }).annual_budget - 1) * 100).toFixed(1)}%</span>
                  : '-',
            },
          ]}
        />
      </Modal>

      {/* ── 即將超支明細 Modal ── */}
      <Modal
        open={modalType === 'near_overrun'}
        title={<><Tag color="orange">即將超支科目</Tag> 明細（執行率 ≥ 85%）— 共 {data?.near_overrun_items?.length ?? 0} 項</>}
        onCancel={() => setModalType(null)}
        footer={null}
        width={780}
      >
        <Table
          dataSource={data?.near_overrun_items ?? []}
          rowKey={(r) => `${r.dept_name}-${r.account_code_name}`}
          size="small"
          pagination={false}
          columns={[
            { title: '部門', dataIndex: 'dept_name', width: 110 },
            { title: '會計科目', dataIndex: 'account_code_name' },
            {
              title: '年度預算',
              dataIndex: 'annual_budget',
              align: 'right' as const,
              render: (v: number) => fmt(v),
            },
            {
              title: '年度實績',
              dataIndex: 'annual_actual',
              align: 'right' as const,
              render: (v: number) => fmt(v),
            },
            {
              title: '剩餘預算',
              key: 'remaining',
              align: 'right' as const,
              render: (_: unknown, r) => {
                const row = r as { annual_budget: number; annual_actual: number }
                const remaining = row.annual_budget - row.annual_actual
                return <span style={{ color: '#faad14', fontWeight: 600 }}>{fmt(remaining)}</span>
              },
            },
            {
              title: '執行率',
              dataIndex: 'exec_rate',
              width: 120,
              render: (v: number) => (
                <Progress
                  percent={Math.min(v, 100)}
                  size="small"
                  strokeColor={v >= 100 ? '#cf1322' : v >= 85 ? '#faad14' : '#3f8600'}
                  format={() => `${v}%`}
                />
              ),
            },
          ]}
        />
      </Modal>
    </div>
  )
}
