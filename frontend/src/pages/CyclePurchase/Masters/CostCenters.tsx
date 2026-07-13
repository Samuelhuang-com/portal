/**
 * 週期採購 — 成本中心主檔維護（依附於部門主檔）
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { createCostCenter, getCostCenters, getCpDepartments, updateCostCenter } from '@/api/cyclePurchase'
import type { CpCostCenter, CpDepartment } from '@/types/cyclePurchase'

const { Title } = Typography

export default function CpCostCentersPage() {
  const [rows, setRows] = useState<CpCostCenter[]>([])
  const [depts, setDepts] = useState<CpDepartment[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpCostCenter | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    Promise.all([getCostCenters(), getCpDepartments({ is_active: true })])
      .then(([ccRes, deptRes]) => {
        setRows(ccRes.data)
        setDepts(deptRes.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const toggleActive = async (r: CpCostCenter) => {
    try {
      await updateCostCenter(r.id, { is_active: !r.is_active })
      message.success(r.is_active ? '已停用' : '已啟用')
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

  const openEdit = (r: CpCostCenter) => {
    setEditing(r)
    form.setFieldsValue(r)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateCostCenter(editing.id, values)
        message.success('更新成功')
      } else {
        await createCostCenter(values)
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 成本中心主檔</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增成本中心</Button>
      </div>

      <Card>
        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '所屬部門', dataIndex: 'department_name', width: 160 },
            { title: '成本中心代碼', dataIndex: 'cc_code', width: 120 },
            { title: '成本中心名稱', dataIndex: 'cc_name' },
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
              render: (_: unknown, r: CpCostCenter) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active ? '確定停用？' : '確定啟用？'}
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
        title={editing ? '編輯成本中心' : '新增成本中心'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="department_id" label="所屬部門" rules={[{ required: true }]}>
            <Select
              options={depts.map((d) => ({ label: `${d.company} / ${d.dept_name}`, value: d.id }))}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="cc_code" label="成本中心代碼" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="cc_name" label="成本中心名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
