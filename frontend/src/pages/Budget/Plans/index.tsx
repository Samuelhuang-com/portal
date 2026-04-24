/**
 * 預算主表清單 (SCR-02)
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  message,
} from 'antd'
import { PlusOutlined, EditOutlined, UnorderedListOutlined, StopOutlined } from '@ant-design/icons'
import {
  getBudgetPlans,
  getBudgetYears,
  getDepartments,
  createBudgetPlan,
  updateBudgetPlan,
  deleteBudgetPlan,
  type BudgetPlan,
  type BudgetYear,
  type Department,
} from '@/api/budget'

const STATUS_COLOR: Record<string, string> = {
  draft: 'blue',
  open: 'green',
  closed: 'default',
  imported_from_excel: 'cyan',
  void: 'red',
}
const STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  open: '開放',
  closed: '關帳',
  imported_from_excel: '匯入',
  void: '已作廢',
}

export default function BudgetPlansPage() {
  const navigate = useNavigate()
  const [plans, setPlans] = useState<BudgetPlan[]>([])
  const [years, setYears] = useState<BudgetYear[]>([])
  const [depts, setDepts] = useState<Department[]>([])
  const [loading, setLoading] = useState(false)
  const [filterYear, setFilterYear] = useState<number | undefined>()
  const [filterStatus, setFilterStatus] = useState<string | undefined>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editPlan, setEditPlan] = useState<BudgetPlan | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getBudgetPlans({ year_id: filterYear, status: filterStatus })
      .then((r) => setPlans(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getBudgetYears().then((r) => setYears(r.data))
    getDepartments().then((r) => setDepts(r.data))
  }, [])

  useEffect(() => { load() }, [filterYear, filterStatus])

  const openCreate = () => {
    setEditPlan(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (plan: BudgetPlan) => {
    setEditPlan(plan)
    form.setFieldsValue({
      plan_name: plan.plan_name,
      status: plan.status,
      notes: plan.notes,
    })
    setModalOpen(true)
  }

  const handleVoid = async (plan: BudgetPlan) => {
    try {
      await deleteBudgetPlan(plan.id)
      message.success(plan.status === 'draft' ? '已刪除' : '已作廢')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editPlan) {
        await updateBudgetPlan(editPlan.id, values)
        message.success('更新成功')
      } else {
        await createBudgetPlan(values)
        message.success('新增成功')
      }
      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Select
            placeholder="選擇年度"
            allowClear
            style={{ width: 120 }}
            value={filterYear}
            onChange={setFilterYear}
            options={years.map((y) => ({ label: `${y.budget_year} 年`, value: y.id }))}
          />
          <Select
            placeholder="狀態篩選"
            allowClear
            style={{ width: 120 }}
            value={filterStatus}
            onChange={setFilterStatus}
            options={[
              { label: '草稿', value: 'draft' },
              { label: '開放', value: 'open' },
              { label: '關帳', value: 'closed' },
              { label: '匯入', value: 'imported_from_excel' },
              { label: '已作廢', value: 'void' },
            ]}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新增預算主表
        </Button>
      </div>

      <Card>
        <Table
          dataSource={plans}
          rowKey="id"
          loading={loading}
          size="small"
          columns={[
            { title: '計畫代碼', dataIndex: 'plan_code', key: 'plan_code', width: 180 },
            { title: '計畫名稱', dataIndex: 'plan_name', key: 'plan_name' },
            { title: '年度', dataIndex: 'budget_year', key: 'budget_year', width: 80 },
            { title: '部門', dataIndex: 'dept_name', key: 'dept_name', width: 100 },
            { title: '類型', dataIndex: 'plan_type', key: 'plan_type', width: 80 },
            {
              title: '狀態',
              dataIndex: 'status',
              key: 'status',
              width: 90,
              render: (s: string) => (
                <Tag color={STATUS_COLOR[s] ?? 'default'}>{STATUS_LABEL[s] ?? s}</Tag>
              ),
            },
            {
              title: '操作',
              key: 'actions',
              width: 200,
              render: (_: unknown, record: BudgetPlan) => (
                <Space>
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    disabled={record.status === 'void'}
                    onClick={() => openEdit(record)}
                  >
                    編輯
                  </Button>
                  <Button
                    size="small"
                    icon={<UnorderedListOutlined />}
                    disabled={record.status === 'void'}
                    onClick={() => navigate(`/budget/plans/${record.id}`)}
                  >
                    明細
                  </Button>
                  <Tooltip
                    title={record.status === 'draft' ? '草稿直接刪除' : '將狀態改為「已作廢」'}
                  >
                    <Popconfirm
                      title={
                        record.status === 'draft'
                          ? '確定刪除此草稿預算？（不可復原）'
                          : '確定作廢此預算主表？（status 改為 void，資料保留）'
                      }
                      onConfirm={() => handleVoid(record)}
                      okText="確定"
                      cancelText="取消"
                      disabled={record.status === 'void'}
                    >
                      <Button
                        size="small"
                        danger
                        icon={<StopOutlined />}
                        disabled={record.status === 'void'}
                      >
                        {record.status === 'draft' ? '刪除' : '作廢'}
                      </Button>
                    </Popconfirm>
                  </Tooltip>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editPlan ? '編輯預算主表' : '新增預算主表'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editPlan && (
            <>
              <Form.Item
                name="plan_code"
                label="計畫代碼"
                rules={[{ required: true, message: '請輸入計畫代碼' }]}
              >
                <Input placeholder="例：ADMIN_OPEX_2026_V2" />
              </Form.Item>
              <Form.Item
                name="budget_year_id"
                label="年度"
                rules={[{ required: true, message: '請選擇年度' }]}
              >
                <Select
                  options={years.map((y) => ({ label: `${y.budget_year} 年`, value: y.id }))}
                  placeholder="選擇年度"
                />
              </Form.Item>
              <Form.Item
                name="dept_id"
                label="部門"
                rules={[{ required: true, message: '請選擇部門' }]}
              >
                <Select
                  options={depts.map((d) => ({ label: d.dept_name, value: d.id }))}
                  placeholder="選擇部門"
                />
              </Form.Item>
              <Form.Item name="plan_type" label="類型" initialValue="OPEX">
                <Select
                  options={[
                    { label: 'OPEX（費用預算）', value: 'OPEX' },
                    { label: 'CAPEX（資本支出）', value: 'CAPEX' },
                  ]}
                />
              </Form.Item>
            </>
          )}
          <Form.Item
            name="plan_name"
            label="計畫名稱"
            rules={[{ required: true, message: '請輸入計畫名稱' }]}
          >
            <Input />
          </Form.Item>
          {editPlan && (
            <Form.Item name="status" label="狀態">
              <Select
                options={[
                  { label: '草稿', value: 'draft' },
                  { label: '開放', value: 'open' },
                  { label: '關帳', value: 'closed' },
                ]}
              />
            </Form.Item>
          )}
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
