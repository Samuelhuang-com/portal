/**
 * 費用交易明細清單 (SCR-08 / SCR-09)
 * 查詢、篩選、編輯交易明細
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { EditOutlined, SearchOutlined, WarningOutlined, DownloadOutlined } from '@ant-design/icons'
import {
  getTransactions,
  getTransaction,
  updateTransaction,
  exportTransactions,
  getDepartments,
  getAccountCodes,
  getBudgetItems,
  getBudgetYears,
  type BudgetTransaction,
  type Department,
  type AccountCode,
  type BudgetItem,
  type BudgetYear,
} from '@/api/budget'

const { Title } = Typography

const fmt = (n?: number | null) =>
  n != null ? new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 }).format(n) : '-'

export default function BudgetTransactionsPage() {
  const [transactions, setTransactions] = useState<BudgetTransaction[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [years, setYears] = useState<BudgetYear[]>([])
  const [depts, setDepts] = useState<Department[]>([])
  const [accounts, setAccounts] = useState<AccountCode[]>([])
  const [items, setItems] = useState<BudgetItem[]>([])

  const [filters, setFilters] = useState<{
    year_id?: number
    dept_id?: number
    month_num?: number
    amount_missing?: boolean
    search?: string
  }>({})
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)

  const [exportLoading, setExportLoading] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editTxn, setEditTxn] = useState<BudgetTransaction | null>(null)
  const [editForm] = Form.useForm()

  const handleExport = async () => {
    setExportLoading(true)
    try {
      const res = await exportTransactions({
        year_id: filters.year_id,
        dept_id: filters.dept_id,
        month_num: filters.month_num,
        amount_missing: filters.amount_missing,
        search: filters.search,
      })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'budget_transactions.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch {
      message.error('匯出失敗')
    } finally {
      setExportLoading(false)
    }
  }

  const load = useCallback(() => {
    setLoading(true)
    getTransactions({
      ...filters,
      limit: pageSize,
      offset: (page - 1) * pageSize,
    })
      .then((r) => {
        setTransactions(r.data.items)
        setTotal(r.data.total)
      })
      .finally(() => setLoading(false))
  }, [filters, page, pageSize])

  useEffect(() => {
    getBudgetYears().then((r) => setYears(r.data))
    getDepartments().then((r) => setDepts(r.data))
    getAccountCodes().then((r) => setAccounts(r.data))
    getBudgetItems().then((r) => setItems(r.data))
  }, [])

  useEffect(() => { load() }, [load])

  const openEdit = async (record: BudgetTransaction) => {
    const r = await getTransaction(record.id)
    setEditTxn(r.data)
    editForm.setFieldsValue({
      dept_id: r.data.dept_id,
      month_num: r.data.month_num,
      account_code_id: r.data.account_code_id,
      budget_item_id: r.data.budget_item_id,
      description: r.data.description,
      amount_ex_tax: r.data.amount_ex_tax,
      requester: r.data.requester,
      note_1: r.data.note_1,
    })
    setEditModalOpen(true)
  }

  const handleEditSubmit = async () => {
    if (!editTxn) return
    try {
      const values = await editForm.validateFields()
      await updateTransaction(editTxn.id, values)
      message.success('更新成功')
      setEditModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <Title level={4} style={{ margin: 0 }}>費用交易明細</Title>
        <Button
          icon={<DownloadOutlined />}
          loading={exportLoading}
          onClick={handleExport}
        >
          匯出 Excel
        </Button>
      </div>

      {/* ── Filter Bar ── */}
      <Card style={{ marginBottom: 12 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col>
            <Select
              placeholder="年度"
              allowClear
              style={{ width: 110 }}
              value={filters.year_id}
              onChange={(v) => setFilters((f) => ({ ...f, year_id: v }))}
              options={years.map((y) => ({ label: `${y.budget_year} 年`, value: y.id }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="部門"
              allowClear
              style={{ width: 110 }}
              value={filters.dept_id}
              onChange={(v) => setFilters((f) => ({ ...f, dept_id: v }))}
              options={depts.map((d) => ({ label: d.dept_name, value: d.id }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="月份"
              allowClear
              style={{ width: 90 }}
              value={filters.month_num}
              onChange={(v) => setFilters((f) => ({ ...f, month_num: v }))}
              options={Array.from({ length: 12 }, (_, i) => ({
                label: `${i + 1} 月`,
                value: i + 1,
              }))}
            />
          </Col>
          <Col>
            <Select
              placeholder="金額問題"
              allowClear
              style={{ width: 130 }}
              value={filters.amount_missing}
              onChange={(v) => setFilters((f) => ({ ...f, amount_missing: v }))}
              options={[
                { label: '僅缺漏金額', value: true },
                { label: '正常資料', value: false },
              ]}
            />
          </Col>
          <Col flex="auto">
            <Input
              placeholder="搜尋說明 / 請購人 / 預算項目"
              prefix={<SearchOutlined />}
              value={filters.search}
              onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
              allowClear
            />
          </Col>
          <Col>
            <Button type="primary" onClick={() => { setPage(1); load() }}>查詢</Button>
          </Col>
        </Row>
      </Card>

      {/* ── Table ── */}
      <Card>
        <Table
          dataSource={transactions}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 1400 }}
          pagination={{
            total,
            current: page,
            pageSize,
            onChange: (p) => setPage(p),
            showTotal: (t) => `共 ${t} 筆`,
            showSizeChanger: false,
          }}
          rowClassName={(r) => r.amount_missing_flag ? 'ant-table-row-danger' : ''}
          columns={[
            { title: '#', dataIndex: 'id', key: 'id', width: 60 },
            { title: '年度', dataIndex: 'budget_year', key: 'budget_year', width: 70 },
            { title: '部門', dataIndex: 'dept_name', key: 'dept_name', width: 90 },
            { title: '月份', dataIndex: 'month_num', key: 'month_num', width: 60, render: (v: number) => v ? `${v}月` : '-' },
            { title: '會計科目', dataIndex: 'account_code_name', key: 'account', width: 140, render: (v, r: BudgetTransaction) => v || r.raw_account_code_name || '-' },
            { title: '預算項目', dataIndex: 'budget_item_name', key: 'item', width: 140, render: (v, r: BudgetTransaction) => v || r.raw_budget_item_name || '-' },
            { title: '說明', dataIndex: 'description', key: 'description', ellipsis: true },
            {
              title: '未稅金額',
              dataIndex: 'amount_ex_tax',
              key: 'amount',
              width: 110,
              align: 'right',
              render: (v: number, r: BudgetTransaction) =>
                r.amount_missing_flag ? (
                  <Tag icon={<WarningOutlined />} color="red">缺漏</Tag>
                ) : (
                  fmt(v)
                ),
            },
            { title: '請購人', dataIndex: 'requester', key: 'requester', width: 90 },
            {
              title: '操作',
              key: 'actions',
              width: 70,
              render: (_: unknown, r: BudgetTransaction) => (
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>
                  修正
                </Button>
              ),
            },
          ]}
        />
      </Card>

      {/* ── Edit Modal ── */}
      <Modal
        title={`修正交易 #${editTxn?.id}`}
        open={editModalOpen}
        onOk={handleEditSubmit}
        onCancel={() => setEditModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={560}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="dept_id" label="部門">
                <Select
                  options={depts.map((d) => ({ label: d.dept_name, value: d.id }))}
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="month_num" label="月份">
                <Select
                  options={Array.from({ length: 12 }, (_, i) => ({
                    label: `${i + 1} 月`,
                    value: i + 1,
                  }))}
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="account_code_id" label="會計科目">
                <Select
                  showSearch
                  optionFilterProp="label"
                  options={accounts.map((a) => ({ label: a.account_code_name, value: a.id }))}
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="budget_item_id" label="預算項目">
                <Select
                  showSearch
                  optionFilterProp="label"
                  options={items.map((a) => ({ label: a.budget_item_name, value: a.id }))}
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="description" label="說明">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="amount_ex_tax" label="未稅金額">
                <InputNumber style={{ width: '100%' }} precision={0} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="requester" label="請購人">
                <Input />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item name="note_1" label="備註">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <style>{`
        .ant-table-row-danger td { background: #fff1f0 !important; }
      `}</style>
    </div>
  )
}
