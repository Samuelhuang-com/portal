/**
 * 庫存管理 › Dashboard（規格 docs/SPEC_stock_management.md §12.1，2026-11-17）
 *
 * 資料來源：GET /stock/dashboard（後端彙總）。錨點＝庫存異動最後一天（CLAUDE §8.2，不用今天）。
 * 期間用 StandardRangePicker，未選＝本月；倉庫、部門為篩選。待匯入清單是公司層級（清單只記部門名稱）。
 * 金額依成本權限顯示；盤盈虧金額只給有盤點審核權限的人看。三單差異數待 Phase 6 完成後顯示。
 */
import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Row, Select, Space, Statistic, Table, Typography, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import StandardRangePicker from '@/components/StandardRangePicker'
import {
  errMsg, fetchStockDashboard, fetchStockDepartments, fetchWarehouses,
  type StockDashboardResp, type StockDepartment, type Warehouse,
} from '@/api/stock'
import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'

const { Text, Title } = Typography

const cnt = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString())
const money = (v: number | null | undefined) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`)

function Kpi({ title, value, sub, danger }: { title: string; value: string; sub?: string; danger?: boolean }) {
  return (
    <Card size="small" style={{ height: '100%', borderColor: danger ? '#ffccc7' : undefined }}>
      <Statistic title={title} value={value} valueStyle={danger ? { color: '#cf1322' } : undefined} />
      {sub && <Text type="secondary" style={{ fontSize: 12 }}>{sub}</Text>}
    </Card>
  )
}

export default function StockDashboardPage() {
  const { companies, code, setCode, error } = useStockCompany()
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [whs, setWhs] = useState<Warehouse[]>([])
  const [depts, setDepts] = useState<StockDepartment[]>([])
  const [whId, setWhId] = useState<number | undefined>()
  const [deptId, setDeptId] = useState<string | undefined>()
  const [data, setData] = useState<StockDashboardResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    if (!code) return
    setWhId(undefined)
    setDeptId(undefined)
    setRange(null)
    fetchWarehouses(code).then((r) => setWhs(r.data)).catch(() => setWhs([]))
    fetchStockDepartments(code).then((r) => setDepts(r.data)).catch(() => setDepts([]))
  }, [code])

  useEffect(() => {
    if (!code) return
    let alive = true
    setLoading(true)
    fetchStockDashboard(code, {
      ...(range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
      warehouse_id: whId,
      department_id: deptId,
    })
      .then((r) => { if (alive) setData(r.data) })
      .catch((e) => { if (alive) message.error(errMsg(e, '讀取儀表板失敗')) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [code, range, whId, deptId, reloadKey])

  if (error) return <Alert type="error" showIcon message={error} />
  const d = data
  const flowRows = d ? [
    { key: 'rc', item: '進貨單（筆）', week: cnt(d.receipts.week.count), month: cnt(d.receipts.month.count), period: cnt(d.receipts.period.count) },
    { key: 'rq', item: '進貨數量（庫存單位）', week: cnt(d.receipts.week.stock_qty), month: cnt(d.receipts.month.stock_qty), period: cnt(d.receipts.period.stock_qty) },
    { key: 'ra', item: '進貨金額（未稅）', week: money(d.receipts.week.amount), month: money(d.receipts.month.amount), period: money(d.receipts.period.amount) },
    { key: 'ic', item: '領用單（筆）', week: cnt(d.issues.week.count), month: cnt(d.issues.month.count), period: cnt(d.issues.period.count) },
    { key: 'ia', item: '領用金額', week: money(d.issues.week.amount), month: money(d.issues.month.amount), period: money(d.issues.period.amount) },
  ] : []

  return (
    <div>
      <Space wrap style={{ marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>庫存 Dashboard</Title>
        <StockCompanySelect companies={companies} value={code} onChange={setCode} />
        <Select allowClear placeholder="倉庫（全部）" style={{ minWidth: 180 }} value={whId} onChange={setWhId}
          options={whs.map((w) => ({ value: w.id, label: w.name }))} />
        <Select allowClear placeholder="部門（全部）" style={{ minWidth: 160 }} value={deptId} onChange={setDeptId}
          options={depts.map((x) => ({ value: x.id, label: x.name }))} />
        <StandardRangePicker value={range} anchor={d?.data_end ?? ''} onChange={setRange} />
        <Button icon={<ReloadOutlined />} onClick={() => setReloadKey((k) => k + 1)} loading={loading}>重新整理</Button>
      </Space>

      {d && (
        <Space direction="vertical" style={{ width: '100%' }} size={8}>
          {!d.period_close.prev_closed && (
            <Alert type="warning" showIcon message={`上月（${d.period_close.prev_period}）尚未月結，本月數字可能不完整`} />
          )}
          {d.import.changed > 0 && (
            <Alert type="error" showIcon message={`有 ${d.import.changed} 筆來源已異動（已入庫的數量不會自動扣回）`}
              description={<a href="/stock/receipts">到進貨匯入處理</a>} />
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            錨點（庫存異動最後日）：{d.data_end ?? '尚無異動'}；本週、本月以錨點為終點；期間未選＝本月。
            {!d.meta.cost_visible && ' 金額欄位需要成本權限才會顯示。'}
          </Text>

          <Title level={5} style={{ margin: '8px 0 0' }}>進貨匯入</Title>
          <Row gutter={12}>
            <Col span={6}><Kpi title="待匯入（待確認）" value={cnt(d.import.pending)} /></Col>
            <Col span={6}><Kpi title="來源已異動" value={cnt(d.import.changed)} danger={d.import.changed > 0} /></Col>
            <Col span={6}><Kpi title="本週新進待匯入" value={cnt(d.import.new_week.count)} sub={`金額 ${money(d.import.new_week.amount)}`} /></Col>
            <Col span={6}><Kpi title="本月新進待匯入" value={cnt(d.import.new_month.count)} sub={`金額 ${money(d.import.new_month.amount)}`} /></Col>
          </Row>

          <Title level={5} style={{ margin: '8px 0 0' }}>進貨與領用</Title>
          <Table size="small" pagination={false} rowKey="key" dataSource={flowRows}
            columns={[
              { title: '項目', dataIndex: 'item' },
              { title: '本週', dataIndex: 'week', align: 'right' as const },
              { title: '本月', dataIndex: 'month', align: 'right' as const },
              { title: `期間（${d.filters.start}～${d.filters.end}）`, dataIndex: 'period', align: 'right' as const },
            ]} />

          <Title level={5} style={{ margin: '8px 0 0' }}>庫存</Title>
          <Row gutter={12}>
            <Col span={6}><Kpi title="庫存料號類別（納入庫存）" value={cnt(d.categories.stock_categories)} /></Col>
            <Col span={6}><Kpi title="期末庫存金額" value={money(d.balance.amount)} sub={`${cnt(d.balance.items)} 個有庫存的品項`} /></Col>
            <Col span={6}><Kpi title="低於安全量" value={cnt(d.balance.low)} danger={d.balance.low > 0} /></Col>
            <Col span={6}><Kpi title={`呆滯料（${d.balance.dead_days} 天無異動）`} value={cnt(d.balance.dead)} /></Col>
          </Row>
          <Row gutter={12} style={{ marginTop: 12 }}>
            <Col span={6}><Kpi title="待核准領用" value={cnt(d.issues.pending_approval)} /></Col>
            <Col span={6}><Kpi title="待發料" value={cnt(d.issues.pending_post)} /></Col>
            <Col span={6}><Kpi title="負庫存品項" value={cnt(d.balance.negative)} danger={d.balance.negative > 0} /></Col>
            <Col span={6}><Kpi title="三單差異數" value="—" sub="待 Phase 6（三單比對）完成後顯示" /></Col>
          </Row>

          <Title level={5} style={{ margin: '8px 0 0' }}>上月盤點（{d.counts.period}）</Title>
          <Row gutter={12}>
            <Col span={6}><Kpi title="盤點表張數" value={cnt(d.counts.tables)} sub={`已核准 ${cnt(d.counts.by_status.approved)}／待審核 ${cnt(d.counts.by_status.submitted)}／盤點中 ${cnt(d.counts.by_status.counting)}`} /></Col>
            <Col span={6}><Kpi title="盤點品項數" value={cnt(d.counts.lines)} sub={`有差異 ${cnt(d.counts.diff)} 筆`} /></Col>
            <Col span={6}><Kpi title="盤盈金額" value={d.meta.review_visible ? money(d.counts.gain_amount) : '—'} sub={d.meta.review_visible ? undefined : '需盤點審核權限'} /></Col>
            <Col span={6}><Kpi title="盤虧金額" value={d.meta.review_visible ? money(d.counts.loss_amount) : '—'} sub={d.meta.review_visible ? undefined : '需盤點審核權限'} /></Col>
          </Row>
        </Space>
      )}
    </div>
  )
}
