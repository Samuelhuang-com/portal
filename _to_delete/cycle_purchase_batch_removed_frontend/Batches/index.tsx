/**
 * 週期採購 — 批次
 * 第二層：依週期設定的規則，產生實際要開放給各單位填寫的批次。
 * 批次號由後端自動產生（CP-YYYYMM-NNNN），不需手動輸入。
 */
import { useEffect, useState } from 'react'
import {
  Button, Card, DatePicker, Form, Input, Modal, Select, Space, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { createBatch, getBatches, getCycles, updateBatch } from '@/api/cyclePurchase'
import type { CpBatch, CpCycle } from '@/types/cyclePurchase'

const { Title } = Typography

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  open: { color: 'blue', label: '開放中' },
  closed: { color: 'orange', label: '已截止' },
  done: { color: 'green', label: '已完成' },
}

export default function CpBatchesPage() {
  const [rows, setRows] = useState<CpBatch[]>([])
  const [cycles, setCycles] = useState<CpCycle[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpBatch | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    Promise.all([getBatches(), getCycles({ status: 'active' })])
      .then(([bRes, cRes]) => {
        setRows(bRes.data)
        setCycles(cRes.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    setModalOpen(true)
  }

  const openEdit = (r: CpBatch) => {
    setEditing(r)
    form.setFieldsValue({
      ...r,
      open_date: dayjs(r.open_date),
      close_date: dayjs(r.close_date),
    })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        ...values,
        open_date: values.open_date.format('YYYY-MM-DD'),
        close_date: values.close_date.format('YYYY-MM-DD'),
      }
      if (editing) {
        await updateBatch(editing.id, payload)
        message.success('更新成功')
      } else {
        await createBatch(payload)
        message.success('新增成功，批次號已自動產生')
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 批次</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增批次</Button>
      </div>

      <Card>
        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '批次號', dataIndex: 'batch_no', width: 140 },
            { title: '所屬週期', dataIndex: 'cycle_name', width: 160 },
            { title: '批次名稱', dataIndex: 'batch_name' },
            { title: '開放日期', dataIndex: 'open_date', width: 110 },
            { title: '截止日期', dataIndex: 'close_date', width: 110 },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 90,
              render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
            },
            {
              title: '已產生請購單',
              dataIndex: 'requests_generated',
              width: 110,
              render: (v: boolean) => (v ? <Tag color="green">是</Tag> : <Tag color="default">否</Tag>),
            },
            {
              title: '操作',
              key: 'actions',
              width: 100,
              render: (_: unknown, r: CpBatch) => (
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? '編輯批次' : '新增批次'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="cycle_id" label="所屬週期設定" rules={[{ required: true }]}>
            <Select
              disabled={!!editing}
              showSearch
              optionFilterProp="label"
              options={cycles.map((c) => ({ label: `${c.cycle_code} ${c.cycle_name}`, value: c.id }))}
            />
          </Form.Item>
          <Form.Item name="batch_name" label="批次名稱" rules={[{ required: true }]}>
            <Input placeholder="如：2026年7月文具統購" />
          </Form.Item>
          <Space.Compact block>
            <Form.Item name="open_date" label="開放日期" rules={[{ required: true }]} style={{ width: '50%' }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="close_date" label="截止日期" rules={[{ required: true }]} style={{ width: '50%', marginLeft: 8 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space.Compact>
          {editing && (
            <Form.Item name="status" label="狀態">
              <Select
                options={[
                  { label: '草稿', value: 'draft' },
                  { label: '開放中', value: 'open' },
                  { label: '已截止', value: 'closed' },
                  { label: '已完成', value: 'done' },
                ]}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}
