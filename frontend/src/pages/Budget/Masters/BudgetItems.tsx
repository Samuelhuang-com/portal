/**
 * 預算項目主檔維護 (SCR-15)
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { getBudgetItems, createBudgetItem, updateBudgetItem, type BudgetItem } from '@/api/budget'

const { Title } = Typography

export default function BudgetItemsPage() {
  const [items, setItems] = useState<BudgetItem[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editItem, setEditItem] = useState<BudgetItem | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getBudgetItems().then((r) => setItems(r.data)).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const toggleActive = async (item: BudgetItem) => {
    try {
      await updateBudgetItem(item.id, { is_active: (item.is_active ?? 1) === 1 ? 0 : 1 })
      message.success((item.is_active ?? 1) === 1 ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const openCreate = () => {
    setEditItem(null)
    form.resetFields()
    form.setFieldsValue({ is_capex: false })
    setModalOpen(true)
  }

  const openEdit = (item: BudgetItem) => {
    setEditItem(item)
    form.setFieldsValue({
      budget_item_name: item.budget_item_name,
      normalized_name: item.normalized_name,
      is_capex: item.is_capex === 1,
      notes: item.notes,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = { ...values, is_capex: values.is_capex ? 1 : 0 }
      if (editItem) {
        await updateBudgetItem(editItem.id, payload)
        message.success('更新成功')
      } else {
        await createBudgetItem(payload)
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
        <Title level={4} style={{ margin: 0 }}>預算項目主檔維護</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增項目</Button>
      </div>
      <Card>
        <Table
          dataSource={items}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }}
          columns={[
            { title: '#', dataIndex: 'id', width: 60 },
            { title: '項目名稱', dataIndex: 'budget_item_name' },
            { title: '正規化鍵', dataIndex: 'normalized_name', ellipsis: true },
            {
              title: 'CAPEX',
              dataIndex: 'is_capex',
              width: 80,
              render: (v: number) => v ? <Tag color="purple">CAPEX</Tag> : null,
            },
            { title: '備註', dataIndex: 'notes', ellipsis: true },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              render: (v: number | undefined) =>
                (v ?? 1) ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>,
            },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: BudgetItem) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={(r.is_active ?? 1) === 1 ? '確定停用此項目？' : '確定啟用此項目？'}
                    onConfirm={() => toggleActive(r)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button
                      size="small"
                      danger={(r.is_active ?? 1) === 1}
                      icon={(r.is_active ?? 1) === 1 ? <StopOutlined /> : <CheckCircleOutlined />}
                    >
                      {(r.is_active ?? 1) === 1 ? '停用' : '啟用'}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editItem ? '編輯預算項目' : '新增預算項目'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="budget_item_name" label="項目名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="normalized_name" label="正規化鍵" rules={[{ required: true }]}>
            <Input placeholder="去除空白後標準鍵" />
          </Form.Item>
          <Form.Item name="is_capex" label="是否 CAPEX" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
