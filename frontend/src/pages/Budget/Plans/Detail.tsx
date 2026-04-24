/**
 * 預算明細編列 (SCR-04)
 * 顯示單一預算主表的所有明細，支援 inline 新增/編輯
 */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Card,
  Descriptions,
  Form,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  message,
  Typography,
  Popconfirm,
  Input,
  Alert,
} from 'antd'
import {
  ArrowLeftOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import {
  getBudgetPlan,
  getBudgetPlanDetails,
  getAccountCodes,
  getBudgetItems,
  createBudgetPlanDetail,
  updateBudgetPlanDetail,
  deleteBudgetPlanDetail,
  type BudgetPlan,
  type BudgetPlanDetail,
  type AccountCode,
  type BudgetItem,
} from '@/api/budget'

const { Title } = Typography

const MONTH_LABELS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
const MONTH_FIELDS = [
  'month_01_budget','month_02_budget','month_03_budget',
  'month_04_budget','month_05_budget','month_06_budget',
  'month_07_budget','month_08_budget','month_09_budget',
  'month_10_budget','month_11_budget','month_12_budget',
] as const

const fmt = (n?: number | null) =>
  n != null ? new Intl.NumberFormat('zh-TW', { maximumFractionDigits: 0 }).format(n) : '-'

const STATUS_COLOR: Record<string, string> = {
  draft: 'blue', open: 'green', closed: 'default', imported_from_excel: 'cyan',
}
const STATUS_LABEL: Record<string, string> = {
  draft: '草稿', open: '開放', closed: '關帳', imported_from_excel: '匯入',
}

export default function BudgetPlanDetailPage() {
  const { planId } = useParams<{ planId: string }>()
  const navigate = useNavigate()

  const [plan, setPlan] = useState<BudgetPlan | null>(null)
  const [details, setDetails] = useState<BudgetPlanDetail[]>([])
  const [accounts, setAccounts] = useState<AccountCode[]>([])
  const [items, setItems] = useState<BudgetItem[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editDetail, setEditDetail] = useState<BudgetPlanDetail | null>(null)
  const [activeOnly, setActiveOnly] = useState(true)
  const [form] = Form.useForm()

  const id = Number(planId)

  const load = () => {
    setLoading(true)
    Promise.all([
      getBudgetPlan(id).then((r) => setPlan(r.data)),
      getBudgetPlanDetails(id, activeOnly).then((r) => setDetails(r.data)),
    ]).finally(() => setLoading(false))
  }

  useEffect(() => {
    getAccountCodes().then((r) => setAccounts(r.data))
    getBudgetItems().then((r) => setItems(r.data))
  }, [])

  useEffect(() => { load() }, [id, activeOnly])

  const isClosed = plan?.status === 'closed'

  const openCreate = () => {
    setEditDetail(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (d: BudgetPlanDetail) => {
    setEditDetail(d)
    form.setFieldsValue({
      standard_account_code_id: d.standard_account_code_id,
      standard_budget_item_id: d.standard_budget_item_id,
      raw_remark: d.raw_remark,
      ...MONTH_FIELDS.reduce((acc, f, i) => {
        acc[f] = (d as unknown as Record<string, unknown>)[f]
        return acc
      }, {} as Record<string, unknown>),
    })
    setModalOpen(true)
  }

  const handleDelete = async (d: BudgetPlanDetail) => {
    try {
      await deleteBudgetPlanDetail(id, d.id)
      message.success('已刪除')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '刪除失敗')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      // 計算 annual_budget
      const annual = MONTH_FIELDS.reduce((sum, f) => sum + (Number(values[f]) || 0), 0)
      values.annual_budget = annual

      if (editDetail) {
        await updateBudgetPlanDetail(id, editDetail.id, values)
        message.success('更新成功')
      } else {
        await createBudgetPlanDetail(id, { ...values, line_type: 'detail' })
        message.success('新增成功')
      }
      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
    }
  }

  // 計算合計列
  const totalRow = details.reduce(
    (acc, d) => {
      MONTH_FIELDS.forEach((f, i) => {
        acc[i] += Number((d as unknown as Record<string, unknown>)[f]) || 0
      })
      acc[12] += Number(d.annual_budget) || 0
      return acc
    },
    Array(13).fill(0) as number[],
  )

  const columns = [
    {
      title: '類型',
      dataIndex: 'line_type',
      width: 70,
      fixed: 'left' as const,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '會計科目',
      key: 'account',
      width: 160,
      fixed: 'left' as const,
      render: (_: unknown, r: BudgetPlanDetail) =>
        r.account_code_name || r.raw_account_code_name || '-',
    },
    {
      title: '預算項目',
      key: 'item',
      width: 160,
      fixed: 'left' as const,
      render: (_: unknown, r: BudgetPlanDetail) =>
        r.budget_item_name || r.raw_budget_item_name || '-',
    },
    ...MONTH_LABELS.map((label, i) => ({
      title: label,
      key: `m${i + 1}`,
      width: 80,
      align: 'right' as const,
      render: (_: unknown, r: BudgetPlanDetail) => fmt((r as unknown as Record<string, unknown>)[MONTH_FIELDS[i]] as number),
    })),
    {
      title: '年度合計',
      dataIndex: 'annual_budget',
      width: 110,
      align: 'right' as const,
      render: (v: number) => <strong>{fmt(v)}</strong>,
    },
    { title: '備註', dataIndex: 'raw_remark', width: 120 },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, r: BudgetPlanDetail) =>
        !isClosed && r.line_type === 'detail' ? (
          <Space>
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
            <Popconfirm
              title="確定刪除此明細？"
              onConfirm={() => handleDelete(r)}
              okText="刪除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        ) : null,
    },
  ]

  return (
    <div>
      {/* ── Breadcrumb / Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16, gap: 12 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/budget/plans')} />
        <Title level={4} style={{ margin: 0 }}>預算明細編列</Title>
      </div>

      {/* ── Plan Info ── */}
      {plan && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={{ xs: 1, sm: 2, md: 4 }}>
            <Descriptions.Item label="計畫代碼">{plan.plan_code}</Descriptions.Item>
            <Descriptions.Item label="計畫名稱">{plan.plan_name}</Descriptions.Item>
            <Descriptions.Item label="部門">{plan.dept_name}</Descriptions.Item>
            <Descriptions.Item label="狀態">
              <Tag color={STATUS_COLOR[plan.status]}>{STATUS_LABEL[plan.status] ?? plan.status}</Tag>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {isClosed && (
        <Alert
          type="warning"
          message="此預算已關帳，不可新增或修改明細。"
          style={{ marginBottom: 12 }}
          showIcon
        />
      )}

      {/* ── Toolbar ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space>
          <Select
            value={activeOnly}
            onChange={setActiveOnly}
            style={{ width: 140 }}
            options={[
              { label: '僅顯示有效明細', value: true },
              { label: '顯示全部', value: false },
            ]}
          />
        </Space>
        {!isClosed && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新增明細
          </Button>
        )}
      </div>

      {/* ── Detail Table ── */}
      <Card styles={{ body: { padding: 0 } }}>
        <Table
          dataSource={details}
          rowKey="id"
          loading={loading}
          size="small"
          scroll={{ x: 'max-content' }}
          pagination={false}
          columns={columns}
          summary={() => (
            <Table.Summary fixed="bottom">
              <Table.Summary.Row style={{ background: '#f0f4f8', fontWeight: 600 }}>
                <Table.Summary.Cell index={0} colSpan={3}>合計</Table.Summary.Cell>
                {totalRow.slice(0, 12).map((v, i) => (
                  <Table.Summary.Cell key={i} index={i + 3} align="right">
                    {fmt(v)}
                  </Table.Summary.Cell>
                ))}
                <Table.Summary.Cell index={15} align="right">{fmt(totalRow[12])}</Table.Summary.Cell>
                <Table.Summary.Cell index={16} colSpan={2} />
              </Table.Summary.Row>
            </Table.Summary>
          )}
        />
      </Card>

      {/* ── Add/Edit Modal ── */}
      <Modal
        title={editDetail ? '編輯預算明細' : '新增預算明細'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={700}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="standard_account_code_id" label="會計科目">
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              options={accounts.map((a) => ({ label: a.account_code_name, value: a.id }))}
              placeholder="選擇會計科目"
            />
          </Form.Item>
          <Form.Item name="standard_budget_item_id" label="預算項目">
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              options={items.map((a) => ({ label: a.budget_item_name, value: a.id }))}
              placeholder="選擇預算項目"
            />
          </Form.Item>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0 12px' }}>
            {MONTH_LABELS.map((label, i) => (
              <Form.Item key={i} name={MONTH_FIELDS[i]} label={label}>
                <InputNumber style={{ width: '100%' }} min={0} precision={0} />
              </Form.Item>
            ))}
          </div>
          <Form.Item name="raw_remark" label="備註">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
