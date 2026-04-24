/**
 * 對照規則維護 (SCR-12)
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Table, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import {
  getMappings,
  createMapping,
  updateMapping,
  deleteMapping,
  getDepartments,
  getAccountCodes,
  getBudgetItems,
  type BudgetMapping,
  type Department,
  type AccountCode,
  type BudgetItem,
} from '@/api/budget'

const { Title } = Typography

export default function MappingsPage() {
  const [mappings, setMappings] = useState<BudgetMapping[]>([])
  const [depts, setDepts] = useState<Department[]>([])
  const [accounts, setAccounts] = useState<AccountCode[]>([])
  const [items, setItems] = useState<BudgetItem[]>([])
  const [loading, setLoading] = useState(false)
  const [filterDept, setFilterDept] = useState<number | undefined>()
  const [modalOpen, setModalOpen] = useState(false)
  const [editMapping, setEditMapping] = useState<BudgetMapping | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getMappings(filterDept).then((r) => setMappings(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => {
    getDepartments().then((r) => setDepts(r.data))
    getAccountCodes().then((r) => setAccounts(r.data))
    getBudgetItems().then((r) => setItems(r.data))
  }, [])

  useEffect(() => { load() }, [filterDept])

  const openCreate = () => {
    setEditMapping(null)
    form.resetFields()
    form.setFieldsValue({ mapping_method: 'manual' })
    setModalOpen(true)
  }

  const openEdit = (m: BudgetMapping) => {
    setEditMapping(m)
    form.setFieldsValue({
      dept_id: m.dept_id,
      quarter_code: m.quarter_code,
      source_account_header: m.source_account_header,
      account_code_id: m.account_code_id,
      mapped_budget_item_name: m.mapped_budget_item_name,
      budget_item_id: m.budget_item_id,
      mapping_method: m.mapping_method,
      notes: m.notes,
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteMapping(id)
      message.success('已刪除')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '刪除失敗')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editMapping) {
        await updateMapping(editMapping.id, values)
        message.success('更新成功')
      } else {
        await createMapping(values)
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
          <Title level={4} style={{ margin: 0 }}>對照規則維護</Title>
          <Select
            placeholder="篩選部門"
            allowClear
            style={{ width: 120 }}
            value={filterDept}
            onChange={setFilterDept}
            options={depts.map((d) => ({ label: d.dept_name, value: d.id }))}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增規則</Button>
      </div>

      <Card>
        <Table
          dataSource={mappings}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }}
          columns={[
            { title: '#', dataIndex: 'id', width: 60 },
            { title: '部門', dataIndex: 'dept_name', width: 90 },
            { title: '原始科目標題', dataIndex: 'source_account_header', width: 160 },
            { title: '標準會計科目', dataIndex: 'account_code_name', width: 150 },
            { title: '對應預算項目', dataIndex: 'budget_item_name', ellipsis: true },
            { title: '方法', dataIndex: 'mapping_method', width: 120 },
            { title: '備註', dataIndex: 'notes', ellipsis: true },
            {
              title: '操作',
              key: 'actions',
              width: 100,
              render: (_: unknown, r: BudgetMapping) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
                  <Popconfirm
                    title="確定刪除此規則？"
                    onConfirm={() => handleDelete(r.id)}
                    okText="刪除"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                  >
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editMapping ? '編輯對照規則' : '新增對照規則'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="dept_id" label="適用部門">
            <Select
              allowClear
              options={depts.map((d) => ({ label: d.dept_name, value: d.id }))}
              placeholder="（空白 = 全部部門）"
            />
          </Form.Item>
          <Form.Item name="source_account_header" label="原始科目標題" rules={[{ required: true }]}>
            <Input placeholder="Excel 參數表中的科目欄位標題" />
          </Form.Item>
          <Form.Item name="account_code_id" label="對應標準會計科目">
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              options={accounts.map((a) => ({ label: a.account_code_name, value: a.id }))}
            />
          </Form.Item>
          <Form.Item name="mapped_budget_item_name" label="對應預算項目名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="budget_item_id" label="對應標準預算項目">
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              options={items.map((a) => ({ label: a.budget_item_name, value: a.id }))}
            />
          </Form.Item>
          <Form.Item name="quarter_code" label="季別">
            <Select
              allowClear
              options={['Q1','Q2','Q3','Q4'].map((q) => ({ label: q, value: q }))}
            />
          </Form.Item>
          <Form.Item name="mapping_method" label="對應方法">
            <Select options={[
              { label: 'manual（人工）', value: 'manual' },
              { label: 'excel_parameter（Excel 參數表）', value: 'excel_parameter' },
            ]} />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
