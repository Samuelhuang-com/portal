/**
 * 部門管理頁
 * 路由：/schedule/departments
 * 權限：schedule_admin
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Button, Card, Form, Input, InputNumber, Modal, Space,
  Switch, Table, Tag, message, Popconfirm, Typography,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { fetchDepartments, createDepartment, updateDepartment, deleteDepartment } from '@/api/schedule'
import type { Department, DepartmentInput } from '@/types/schedule'

const { Title } = Typography

export default function DepartmentsPage() {
  const [data, setData]       = useState<Department[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing]     = useState<Department | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await fetchDepartments()) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const openAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ sort_order: 0, is_active: true })
    setModalOpen(true)
  }

  const openEdit = (row: Department) => {
    setEditing(row)
    form.setFieldsValue({ ...row })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields() as DepartmentInput
      if (editing) {
        await updateDepartment(editing.id, values)
        message.success('部門已更新')
      } else {
        await createDepartment(values)
        message.success('部門已新增')
      }
      setModalOpen(false)
      load()
    } catch { /* form validation */ }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteDepartment(id)
      message.success('部門已刪除')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失敗')
    }
  }

  const columns: ColumnsType<Department> = [
    { title: '排序', dataIndex: 'sort_order', width: 70 },
    { title: '部門名稱', dataIndex: 'name', width: 150 },
    { title: '備註', dataIndex: 'remark', render: v => v || '—' },
    {
      title: '狀態', dataIndex: 'is_active', width: 80,
      render: v => v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作', width: 120,
      render: (_, row) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>編輯</Button>
          <Popconfirm title="確認刪除此部門？" onConfirm={() => handleDelete(row.id)} okText="確認" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />}>刪除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={<Title level={4} style={{ margin: 0 }}>部門管理</Title>}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增部門</Button>}
      >
        <Table rowKey="id" columns={columns} dataSource={data} loading={loading} pagination={false} size="small" />
      </Card>

      <Modal
        title={editing ? '編輯部門' : '新增部門'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        okText="儲存" cancelText="取消" destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="部門名稱" rules={[{ required: true, message: '請輸入部門名稱' }]}>
            <Input placeholder="如：飯店、商場、工務" />
          </Form.Item>
          <Form.Item name="remark" label="備註">
            <Input placeholder="選填" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序（數字越小越前）">
            <InputNumber min={0} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="is_active" label="狀態" valuePropName="checked">
            <Switch checkedChildren="啟用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
