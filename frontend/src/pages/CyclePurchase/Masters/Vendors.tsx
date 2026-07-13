/**
 * 週期採購 — 供應商主檔維護
 * 2026-07-10 決策：週期採購自建獨立供應商主檔，不與合約模組的 Vendors 共用。
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { createVendor, getVendors, updateVendor } from '@/api/cyclePurchase'
import type { CpVendor } from '@/types/cyclePurchase'

const { Title } = Typography

export default function CpVendorsPage() {
  const [vendors, setVendors] = useState<CpVendor[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpVendor | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getVendors().then((r) => setVendors(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const toggleActive = async (v: CpVendor) => {
    try {
      await updateVendor(v.id, { is_active: !v.is_active })
      message.success(v.is_active ? '已停用' : '已啟用')
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

  const openEdit = (v: CpVendor) => {
    setEditing(v)
    form.setFieldsValue(v)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateVendor(editing.id, values)
        message.success('更新成功')
      } else {
        await createVendor(values)
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 供應商主檔</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增供應商</Button>
      </div>

      <Card>
        <Table
          dataSource={vendors}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '代碼', dataIndex: 'vendor_code', width: 100 },
            { title: '供應商名稱', dataIndex: 'vendor_name' },
            { title: '統編', dataIndex: 'tax_id', width: 110 },
            { title: '聯絡人', dataIndex: 'contact_name', width: 100 },
            { title: '聯絡電話', dataIndex: 'contact_phone', width: 120 },
            { title: '付款條件', dataIndex: 'payment_terms', width: 120 },
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
              render: (_: unknown, r: CpVendor) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active ? '確定停用此供應商？' : '確定啟用此供應商？'}
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
        title={editing ? '編輯供應商' : '新增供應商'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="vendor_code" label="供應商代碼" rules={[{ required: true }]}>
            <Input disabled={!!editing} />
          </Form.Item>
          <Form.Item name="vendor_name" label="供應商名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="tax_id" label="統一編號">
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label="聯絡人">
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label="聯絡電話">
            <Input />
          </Form.Item>
          <Form.Item name="payment_terms" label="付款條件">
            <Input />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
