/**
 * 週期採購 — 週期設定
 * 第一層：定義請購規則、頻率、開放天數、截止日、適用品類與適用單位。
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import { createCycle, getCycles, updateCycle } from '@/api/cyclePurchase'
import type { CpCycle } from '@/types/cyclePurchase'

const { Title } = Typography

const FREQUENCY_OPTIONS = [
  { label: '每月一次', value: 'monthly' },
  { label: '雙週一次', value: 'biweekly' },
  { label: '每兩個月一次', value: 'bimonthly' },
  { label: '自訂', value: 'custom' },
]

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '啟用' },
  inactive: { color: 'default', label: '停用' },
  paused: { color: 'orange', label: '暫停' },
}

export default function CpCyclesPage() {
  const [rows, setRows] = useState<CpCycle[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpCycle | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getCycles().then((r) => setRows(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ frequency: 'monthly', auto_generate: false, status: 'active' })
    setModalOpen(true)
  }

  const openEdit = (r: CpCycle) => {
    setEditing(r)
    form.setFieldsValue(r)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateCycle(editing.id, values)
        message.success('更新成功')
      } else {
        await createCycle(values)
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 週期設定</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增週期設定</Button>
      </div>

      <Card>
        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '週期代碼', dataIndex: 'cycle_code', width: 120 },
            { title: '週期名稱', dataIndex: 'cycle_name' },
            {
              title: '頻率',
              dataIndex: 'frequency',
              width: 100,
              render: (v: string) => FREQUENCY_OPTIONS.find((f) => f.value === v)?.label || v,
            },
            { title: '開放規則', dataIndex: 'open_rule', width: 160 },
            { title: '截止規則', dataIndex: 'close_rule', width: 160 },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 90,
              render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
            },
            {
              title: '操作',
              key: 'actions',
              width: 100,
              render: (_: unknown, r: CpCycle) => (
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? '編輯週期設定' : '新增週期設定'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={600}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Space.Compact block>
            <Form.Item name="cycle_code" label="週期代碼" rules={[{ required: true }]} style={{ width: '50%' }}>
              <Input placeholder="如 GP-MONT-STATIONERY" disabled={!!editing} />
            </Form.Item>
            <Form.Item name="frequency" label="請購頻率" rules={[{ required: true }]} style={{ width: '50%', marginLeft: 8 }}>
              <Select options={FREQUENCY_OPTIONS} />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="cycle_name" label="週期名稱" rules={[{ required: true }]}>
            <Input placeholder="如：每月文具統購" />
          </Form.Item>
          <Form.Item name="open_rule" label="開放規則說明">
            <Input placeholder="如：每月第 1 日開放" />
          </Form.Item>
          <Form.Item name="close_rule" label="截止規則說明">
            <Input placeholder="如：開放後 5 天截止" />
          </Form.Item>
          <Form.Item name="applicable_categories" label="適用品類（逗號分隔）">
            <Input placeholder="如：文具印刷,清潔用品" />
          </Form.Item>
          <Form.Item name="applicable_scope" label="適用公司／部門（逗號分隔，或 all）">
            <Input placeholder="all 或 日曜天地,春大直" />
          </Form.Item>
          <Form.Item name="reminder_rule" label="提醒規則說明">
            <Input.TextArea rows={2} placeholder="如：開放通知、截止前 1 天提醒、逾期未填提醒" />
          </Form.Item>
          <Space size="large">
            <Form.Item name="auto_generate" label="自動產生批次" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="status" label="狀態" style={{ width: 160 }}>
              <Select
                options={[
                  { label: '啟用', value: 'active' },
                  { label: '停用', value: 'inactive' },
                  { label: '暫停', value: 'paused' },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
