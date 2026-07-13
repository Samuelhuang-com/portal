/**
 * 週期採購 — 會計科目主檔維護
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { createCpAccountCode, getCpAccountCodes, updateCpAccountCode } from '@/api/cyclePurchase'
import type { CpAccountCode } from '@/types/cyclePurchase'

const { Title } = Typography

export default function CpAccountCodesPage() {
  const [rows, setRows] = useState<CpAccountCode[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpAccountCode | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getCpAccountCodes().then((r) => setRows(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const toggleActive = async (r: CpAccountCode) => {
    try {
      await updateCpAccountCode(r.id, { is_active: !r.is_active })
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

  const openEdit = (r: CpAccountCode) => {
    setEditing(r)
    form.setFieldsValue(r)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateCpAccountCode(editing.id, values)
        message.success('更新成功')
      } else {
        await createCpAccountCode(values)
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 會計科目主檔</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增會計科目</Button>
      </div>

      <Card>
        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '代碼', dataIndex: 'code', width: 120 },
            { title: '名稱', dataIndex: 'name' },
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
              render: (_: unknown, r: CpAccountCode) => (
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
        title={editing ? '編輯會計科目' : '新增會計科目'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="code" label="會計科目代碼" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name" label="會計科目名稱" rules={[{ required: true }]}>
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
