/**
 * 週期採購 — 驗收單清單（第四期，2026-07-11 新增）
 * 路由：/cycle-purchase/receiving
 *
 * 「新增驗收單」只能挑選狀態為 issued／partial_received 的採購單（received／
 * draft／cancelled 的採購單不能再建驗收單，後端也會擋，這裡先在前端把選項
 * 縮小，避免選了會被擋下的單）。建立後（草稿）導到詳情頁填明細。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button, Card, DatePicker, Form, Input, Modal, Select, Space, Table, Tag, Typography, message,
} from 'antd'
import { EyeOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { createReceiving, getPos, getReceivingList } from '@/api/cyclePurchase'
import type { CpPO, CpReceiving } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title } = Typography
const { TextArea } = Input

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:       { color: 'default', label: '草稿' },
  completed:   { color: 'green',   label: '已完成（無差異）' },
  discrepancy: { color: 'orange',  label: '有差異' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpReceivingListPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canReceive = hasPermission('cycle_purchase_receive')

  const [rows, setRows] = useState<CpReceiving[]>([])
  const [company, setCompany] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  const [createModal, setCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [eligiblePos, setEligiblePos] = useState<CpPO[]>([])
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getReceivingList({ company, status })
      .then((r) => setRows(r.data))
      .catch((err) => message.error(errMsg(err, '載入失敗')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [company, status])

  const companyOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.company).filter((c): c is string => !!c))),
    [rows],
  )

  const openCreate = async () => {
    form.resetFields()
    form.setFieldsValue({ received_date: dayjs() })
    setCreateModal(true)
    try {
      const [issued, partial] = await Promise.all([
        getPos({ status: 'issued' }).then((r) => r.data),
        getPos({ status: 'partial_received' }).then((r) => r.data),
      ])
      setEligiblePos([...issued, ...partial])
    } catch (err: any) {
      message.error(errMsg(err, '載入可驗收的採購單失敗'))
    }
  }

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      setCreating(true)
      const res = await createReceiving({
        po_id: values.po_id,
        received_date: values.received_date.format('YYYY-MM-DD'),
        notes: values.notes?.trim() || null,
      })
      message.success(`已建立驗收單 ${res.data.receiving_no}`)
      setCreateModal(false)
      navigate(`/cycle-purchase/receiving/${res.data.id}`)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(errMsg(err, '建立驗收單失敗'))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 驗收單</Title>
        {canReceive && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增驗收單</Button>
        )}
      </div>

      <Card>
        <Space wrap style={{ marginBottom: 12 }}>
          <Select
            allowClear
            placeholder="依公司篩選"
            style={{ width: 140 }}
            value={company}
            onChange={setCompany}
            options={companyOptions.map((c) => ({ label: c, value: c }))}
          />
          <Select
            allowClear
            placeholder="依狀態篩選"
            style={{ width: 180 }}
            value={status}
            onChange={setStatus}
            options={[
              { label: '草稿', value: 'draft' },
              { label: '已完成（無差異）', value: 'completed' },
              { label: '有差異', value: 'discrepancy' },
            ]}
          />
        </Space>

        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '驗收單號', dataIndex: 'receiving_no', width: 160 },
            {
              title: '採購單號',
              dataIndex: 'po_no',
              width: 160,
              render: (v?: string | null, r?: CpReceiving) =>
                v && r ? <a onClick={() => navigate(`/cycle-purchase/pos/${r.po_id}`)}>{v}</a> : '—',
            },
            { title: '公司', dataIndex: 'company', width: 110 },
            { title: '供應商', dataIndex: 'vendor_name', width: 140 },
            { title: '驗收日期', dataIndex: 'received_date', width: 110 },
            { title: '驗收人員', dataIndex: 'receiver_name', width: 100, render: (v?: string | null) => v || '—' },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 130,
              render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
            },
            {
              title: '操作',
              key: 'actions',
              width: 90,
              render: (_: unknown, r: CpReceiving) => (
                <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/cycle-purchase/receiving/${r.id}`)}>
                  檢視
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="新增驗收單"
        open={createModal}
        onOk={handleCreate}
        onCancel={() => setCreateModal(false)}
        okText="建立"
        cancelText="取消"
        confirmLoading={creating}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="po_id"
            label="採購單"
            rules={[{ required: true, message: '請選擇採購單' }]}
            extra="只能選狀態為「已發出」或「部分到貨」的採購單"
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="選擇要驗收的採購單"
              options={eligiblePos.map((p) => ({
                label: `${p.po_no}（${p.company} / ${p.vendor_name}）${p.status === 'partial_received' ? ' — 部分到貨中' : ''}`,
                value: p.id,
              }))}
              notFoundContent={eligiblePos.length === 0 ? '目前沒有可驗收的採購單（已發出或部分到貨）' : undefined}
            />
          </Form.Item>
          <Form.Item name="received_date" label="驗收日期" rules={[{ required: true, message: '請選擇驗收日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="備註（選填）">
            <TextArea rows={2} placeholder="例如：第一批到貨、供應商臨時通知延遲等" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
