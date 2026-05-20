/**
 * 班別管理頁
 * 路由：/schedule/shifts
 * 權限：schedule_admin
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Button, Card, Form, Input, InputNumber, Modal, Space,
  Switch, Table, Tag, ColorPicker, message, Popconfirm, Typography,
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { fetchShifts, createShift, updateShift, deleteShift } from '@/api/schedule'
import type { ShiftType, ShiftTypeInput } from '@/types/schedule'

const { Title } = Typography

export default function ShiftsPage() {
  const [data, setData]       = useState<ShiftType[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing]     = useState<ShiftType | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await fetchShifts())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ work_minutes: 480, is_overnight: false, color: '#6b7280', is_active: true })
    setModalOpen(true)
  }

  const openEdit = (row: ShiftType) => {
    setEditing(row)
    form.setFieldsValue({ ...row })
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields() as ShiftTypeInput
      if (editing) {
        await updateShift(editing.id, values)
        message.success('班別已更新')
      } else {
        await createShift(values)
        message.success('班別已新增')
      }
      setModalOpen(false)
      load()
    } catch {
      // form validation error
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteShift(id)
      message.success('班別已停用')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '操作失敗')
    }
  }

  const columns: ColumnsType<ShiftType> = [
    {
      title: '代碼',
      dataIndex: 'code',
      width: 80,
      render: (code, row) => <Tag color={row.color} style={{ fontWeight: 600, fontSize: 13 }}>{code}</Tag>,
    },
    { title: '名稱', dataIndex: 'name', width: 100 },
    {
      title: '上班時間',
      width: 100,
      render: (_, r) => r.start_time ? `${r.start_time} – ${r.end_time}` : '—',
    },
    {
      title: '工時（分鐘）',
      dataIndex: 'work_minutes',
      width: 110,
      render: v => `${v} 分 (${(v / 60).toFixed(1)} hr)`,
    },
    {
      title: '跨日',
      dataIndex: 'is_overnight',
      width: 70,
      render: v => v ? <Tag color="purple">跨日</Tag> : '—',
    },
    {
      title: '顏色',
      dataIndex: 'color',
      width: 70,
      render: (c) => <span style={{ display: 'inline-block', width: 22, height: 22, borderRadius: 4, background: c, border: '1px solid #ddd' }} />,
    },
    {
      title: '狀態',
      dataIndex: 'is_active',
      width: 80,
      render: v => v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作',
      width: 120,
      render: (_, row) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>編輯</Button>
          <Popconfirm title="確認停用此班別？" onConfirm={() => handleDelete(row.id)} okText="確認" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />}>停用</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Card
        title={<Title level={4} style={{ margin: 0 }}>班別管理</Title>}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增班別</Button>
        }
      >
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          pagination={false}
          size="small"
        />
      </Card>

      <Modal
        title={editing ? '編輯班別' : '新增班別'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="code" label="班別代碼" rules={[{ required: true, message: '請輸入代碼' }]}>
            <Input placeholder="如：N1、Y、E6" style={{ textTransform: 'uppercase' }} />
          </Form.Item>
          <Form.Item name="name" label="班別名稱" rules={[{ required: true, message: '請輸入名稱' }]}>
            <Input placeholder="如：日班、早班" />
          </Form.Item>
          <Space>
            <Form.Item name="start_time" label="上班時間">
              <Input placeholder="09:30" style={{ width: 100 }} />
            </Form.Item>
            <Form.Item name="end_time" label="下班時間">
              <Input placeholder="18:30" style={{ width: 100 }} />
            </Form.Item>
          </Space>
          <Form.Item name="work_minutes" label="預設工時（分鐘）">
            <InputNumber min={0} max={1440} style={{ width: 150 }} addonAfter="分鐘" />
          </Form.Item>
          <Form.Item name="color" label="顏色（Hex）">
            <Input placeholder="#3b82f6" style={{ width: 130 }} />
          </Form.Item>
          <Form.Item name="is_overnight" label="是否跨日" valuePropName="checked">
            <Switch checkedChildren="是" unCheckedChildren="否" />
          </Form.Item>
          <Form.Item name="is_active" label="狀態" valuePropName="checked">
            <Switch checkedChildren="啟用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
