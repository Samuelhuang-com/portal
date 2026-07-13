/**
 * 週期採購 — 請款單清單（第五期，2026-07-11 新增）
 * 路由：/cycle-purchase/payments
 *
 * 「新增請款單」流程：先選一張採購單（狀態限 issued／partial_received／
 * received，draft／cancelled 的採購單還沒到貨或已取消，不能請款），選定後
 * 載入這張採購單底下「還沒被任何請款單涵蓋、且已送出」的驗收單清單，
 * 勾選要合併請款的驗收單（可複選，例如同一張發票涵蓋分好幾次到貨的貨款），
 * 填發票資訊後建立。建立後（草稿）系統自動試算費用分攤明細，導到詳情頁。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Button, Card, DatePicker, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography, message,
} from 'antd'
import { EyeOutlined, PlusOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { createPayment, getPayableReceivings, getPayments, getPos } from '@/api/cyclePurchase'
import type { CpPO, CpPayableReceiving, CpPayment } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  submitted: { color: 'blue',    label: '已送出' },
  paying:    { color: 'gold',    label: '付款中' },
  paid:      { color: 'green',   label: '已付款' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpPaymentListPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canFinance = hasPermission('cycle_purchase_finance')

  const [rows, setRows] = useState<CpPayment[]>([])
  const [company, setCompany] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  const [createModal, setCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [eligiblePos, setEligiblePos] = useState<CpPO[]>([])
  const [payableReceivings, setPayableReceivings] = useState<CpPayableReceiving[]>([])
  const [loadingReceivings, setLoadingReceivings] = useState(false)
  const [selectedReceivingIds, setSelectedReceivingIds] = useState<number[]>([])
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    getPayments({ company, status })
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
    form.setFieldsValue({ invoice_date: dayjs() })
    setPayableReceivings([])
    setSelectedReceivingIds([])
    setCreateModal(true)
    try {
      const [issued, partial, received] = await Promise.all([
        getPos({ status: 'issued' }).then((r) => r.data),
        getPos({ status: 'partial_received' }).then((r) => r.data),
        getPos({ status: 'received' }).then((r) => r.data),
      ])
      setEligiblePos([...issued, ...partial, ...received])
    } catch (err: any) {
      message.error(errMsg(err, '載入可請款的採購單失敗'))
    }
  }

  const handlePoChange = async (poId: number) => {
    setSelectedReceivingIds([])
    setPayableReceivings([])
    setLoadingReceivings(true)
    try {
      const rec = (await getPayableReceivings(poId)).data
      setPayableReceivings(rec)
    } catch (err: any) {
      message.error(errMsg(err, '載入可請款的驗收單失敗'))
    } finally {
      setLoadingReceivings(false)
    }
  }

  const selectedTotal = useMemo(
    () => payableReceivings
      .filter((r) => selectedReceivingIds.includes(r.receiving_id))
      .reduce((sum, r) => sum + Number(r.estimated_amount), 0),
    [payableReceivings, selectedReceivingIds],
  )

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      if (selectedReceivingIds.length === 0) {
        message.warning('請至少勾選一張驗收單')
        return
      }
      setCreating(true)
      const res = await createPayment({
        po_id: values.po_id,
        receiving_ids: selectedReceivingIds,
        invoice_no: values.invoice_no.trim(),
        invoice_date: values.invoice_date.format('YYYY-MM-DD'),
        invoice_amount: values.invoice_amount,
        notes: values.notes?.trim() || null,
      })
      message.success(`已建立請款單 ${res.data.payment_no}`)
      setCreateModal(false)
      navigate(`/cycle-purchase/payments/${res.data.id}`)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(errMsg(err, '建立請款單失敗'))
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 請款單</Title>
        {canFinance && (
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增請款單</Button>
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
            style={{ width: 160 }}
            value={status}
            onChange={setStatus}
            options={[
              { label: '草稿', value: 'draft' },
              { label: '已送出', value: 'submitted' },
              { label: '付款中', value: 'paying' },
              { label: '已付款', value: 'paid' },
            ]}
          />
        </Space>

        <Table<CpPayment>
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '請款單號', dataIndex: 'payment_no', width: 160 },
            {
              title: '採購單號',
              dataIndex: 'po_no',
              width: 160,
              render: (v?: string | null, r?: CpPayment) =>
                v && r ? <a onClick={() => navigate(`/cycle-purchase/pos/${r.po_id}`)}>{v}</a> : '—',
            },
            { title: '公司', dataIndex: 'company', width: 110 },
            { title: '供應商', dataIndex: 'vendor_name', width: 140 },
            { title: '發票號碼', dataIndex: 'invoice_no', width: 130 },
            { title: '發票日期', dataIndex: 'invoice_date', width: 110 },
            {
              title: '發票金額',
              dataIndex: 'invoice_amount',
              width: 110,
              align: 'right',
              render: (v: number) => Number(v).toLocaleString(),
            },
            {
              title: '分攤總額',
              dataIndex: 'total_allocated',
              width: 110,
              align: 'right',
              render: (v?: number | null) => (v == null ? '—' : Number(v).toLocaleString()),
            },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 100,
              render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
            },
            {
              title: '操作',
              key: 'actions',
              width: 90,
              render: (_: unknown, r: CpPayment) => (
                <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/cycle-purchase/payments/${r.id}`)}>
                  檢視
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="新增請款單"
        open={createModal}
        onOk={handleCreate}
        onCancel={() => setCreateModal(false)}
        okText="建立"
        cancelText="取消"
        confirmLoading={creating}
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="po_id"
            label="採購單"
            rules={[{ required: true, message: '請選擇採購單' }]}
            extra="只能選狀態為「已發出」「部分到貨」或「已完成到貨」的採購單"
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="選擇要請款的採購單"
              onChange={handlePoChange}
              options={eligiblePos.map((p) => ({
                label: `${p.po_no}（${p.company} / ${p.vendor_name}）`,
                value: p.id,
              }))}
              notFoundContent={eligiblePos.length === 0 ? '目前沒有可請款的採購單' : undefined}
            />
          </Form.Item>

          <Form.Item label="要合併請款的驗收單" required>
            {loadingReceivings ? (
              <Text type="secondary">載入中…</Text>
            ) : payableReceivings.length === 0 ? (
              <Alert type="info" showIcon message="請先選擇採購單" description="選擇採購單後會列出還沒被請款的已送出驗收單。" />
            ) : (
              <>
                <Table<CpPayableReceiving>
                  dataSource={payableReceivings}
                  rowKey="receiving_id"
                  size="small"
                  pagination={false}
                  rowSelection={{
                    selectedRowKeys: selectedReceivingIds,
                    onChange: (keys) => setSelectedReceivingIds(keys as number[]),
                  }}
                  columns={[
                    { title: '驗收單號', dataIndex: 'receiving_no', width: 140 },
                    { title: '驗收日期', dataIndex: 'received_date', width: 110 },
                    {
                      title: '狀態',
                      dataIndex: 'status',
                      width: 100,
                      render: (v: string) => (v === 'discrepancy' ? <Tag color="orange">有差異</Tag> : <Tag color="green">完成</Tag>),
                    },
                    {
                      title: '估算金額（參考）',
                      dataIndex: 'estimated_amount',
                      align: 'right' as const,
                      render: (v: number) => Number(v).toLocaleString(),
                    },
                  ]}
                />
                <div style={{ marginTop: 8, textAlign: 'right' }}>
                  <Text type="secondary">已勾選 {selectedReceivingIds.length} 張，估算金額合計 {selectedTotal.toLocaleString()}（僅供參考，實際請以發票金額為準）</Text>
                </div>
              </>
            )}
          </Form.Item>

          <Form.Item name="invoice_no" label="發票號碼" rules={[{ required: true, message: '請輸入發票號碼' }]}>
            <Input placeholder="例如 AB12345678" />
          </Form.Item>
          <Form.Item name="invoice_date" label="發票日期" rules={[{ required: true, message: '請選擇發票日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="invoice_amount" label="發票金額" rules={[{ required: true, message: '請輸入發票金額' }]}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="notes" label="備註（選填）">
            <TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
