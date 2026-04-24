/**
 * 部門主檔維護 (SCR-13)
 */
import { useEffect, useState } from 'react'
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import {
  getDepartments,
  createDepartment,
  updateDepartment,
  type Department,
} from '@/api/budget'

const { Title } = Typography

export default function DepartmentsPage() {
  const [depts, setDepts] = useState<Department[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editDept, setEditDept] = useState<Department | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getDepartments(false).then((r) => setDepts(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const toggleActive = async (d: Department) => {
    try {
      await updateDepartment(d.id, { is_active: d.is_active === 1 ? 0 : 1 })
      message.success(d.is_active === 1 ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const openCreate = () => {
    setEditDept(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, sort_order: 0 })
    setModalOpen(true)
  }

  const openEdit = (d: Department) => {
    setEditDept(d)
    form.setFieldsValue({
      dept_code: d.dept_code,
      dept_name: d.dept_name,
      dept_group: d.dept_group,
      sort_order: d.sort_order,
      is_active: d.is_active === 1,
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = { ...values, is_active: values.is_active ? 1 : 0 }
      if (editDept) {
        await updateDepartment(editDept.id, payload)
        message.success('更新成功')
      } else {
        await createDepartment(payload)
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
        <Title level={4} style={{ margin: 0 }}>部門主檔維護</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增部門</Button>
      </div>

      <Card>
        <Table
          dataSource={depts}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '代碼', dataIndex: 'dept_code', width: 90 },
            { title: '名稱', dataIndex: 'dept_name' },
            { title: '群組', dataIndex: 'dept_group', width: 100 },
            { title: '排序', dataIndex: 'sort_order', width: 70 },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              render: (v: number) => v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>,
            },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: Department) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active === 1 ? '確定停用此部門？' : '確定啟用此部門？'}
                    onConfirm={() => toggleActive(r)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button
                      size="small"
                      danger={r.is_active === 1}
                      icon={r.is_active === 1 ? <StopOutlined /> : <CheckCircleOutlined />}
                    >
                      {r.is_active === 1 ? '停用' : '啟用'}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editDept ? '編輯部門' : '新增部門'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="dept_code" label="部門代碼" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dept_name" label="部門名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dept_group" label="部門群組">
            <Select
              allowClear
              options={[
                { label: 'OPEX', value: 'OPEX' },
                { label: 'CAPEX', value: 'CAPEX' },
              ]}
            />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber style={{ width: '100%' }} min={0} />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
