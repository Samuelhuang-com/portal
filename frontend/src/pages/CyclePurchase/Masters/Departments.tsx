/**
 * 週期採購 — 部門主檔維護
 * 2026-07-10 決策：週期採購自建獨立部門主檔，不與 Budget／Contract 模組的
 * 部門主檔關聯（三套主檔目前彼此獨立）。
 *
 * 2026-07-11 新增「承辦人」：owner_user_id 軟關聯到 portal.db 的 users.id，
 * 供 Dashboard「待辦提醒」判斷登入者屬於哪個週採部門用（見
 * cycle_purchase_request_service.get_dashboard_todos）。承辦人清單沿用既有
 * GET /users/options（任何登入者可呼叫，回傳啟用中使用者），不需要新增後端。
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { createCpDepartment, getCpDepartments, updateCpDepartment } from '@/api/cyclePurchase'
import { usersApi, type UserOptionItem } from '@/api/users'
import type { CpDepartment } from '@/types/cyclePurchase'

const { Title } = Typography

export default function CpDepartmentsPage() {
  const [depts, setDepts] = useState<CpDepartment[]>([])
  const [userOptions, setUserOptions] = useState<UserOptionItem[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpDepartment | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    Promise.all([getCpDepartments(), usersApi.options()])
      .then(([dRes, uRes]) => {
        setDepts(dRes.data)
        setUserOptions(uRes.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const toggleActive = async (d: CpDepartment) => {
    try {
      await updateCpDepartment(d.id, { is_active: !d.is_active })
      message.success(d.is_active ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true })
    setModalOpen(true)
  }

  const openEdit = (d: CpDepartment) => {
    setEditing(d)
    form.setFieldsValue(d)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateCpDepartment(editing.id, values)
        message.success('更新成功')
      } else {
        await createCpDepartment(values)
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 部門主檔</Title>
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
            { title: '公司別', dataIndex: 'company', width: 140 },
            { title: '部門代碼', dataIndex: 'dept_code', width: 100 },
            { title: '部門名稱', dataIndex: 'dept_name' },
            {
              title: '承辦人',
              dataIndex: 'owner_name',
              width: 120,
              render: (v?: string | null) => v || <Tag>未設定</Tag>,
            },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              render: (v: boolean) => (v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>),
            },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: CpDepartment) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active ? '確定停用此部門？' : '確定啟用此部門？'}
                    onConfirm={() => toggleActive(r)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button size="small" danger={r.is_active} icon={r.is_active ? <StopOutlined /> : <CheckCircleOutlined />}>
                      {r.is_active ? '停用' : '啟用'}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? '編輯部門' : '新增部門'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="company" label="公司別" rules={[{ required: true }]}>
            <Input placeholder="如：日曜天地／春大直" />
          </Form.Item>
          <Form.Item name="dept_code" label="部門代碼" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dept_name" label="部門名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="owner_user_id"
            label="承辦人"
            extra="供 Dashboard「待辦提醒」判斷這個部門還沒填的請購單要提醒誰"
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="選擇承辦人（選填）"
              options={userOptions.map((u) => ({ label: u.label, value: u.user_id }))}
            />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
