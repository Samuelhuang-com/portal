/**
 * 週期採購 — 請款單詳情頁（第五期，2026-07-11 新增）
 * 路由：/cycle-purchase/payments/:id
 *
 * 只有草稿狀態可以編輯發票資訊／調整分攤明細。狀態機：draft -> submitted ->
 * paying -> paid（只能依序推進，不能跳過或倒退）。
 *
 * 分攤明細的 suggested_amount 是系統建立當下試算的值，之後不會再變動（供
 * 追溯對照）；allocated_amount 預設等於試算值，草稿狀態下可以點「調整」
 * 個別修改（不同於試算值時必須填調整原因），比照彙整單「調整量」的設計。
 *
 * 送出前系統會檢查「分攤金額加總」是否等於「發票金額」，不符時必須先在
 * 上方「發票資訊」填寫差異原因（amount_diff_reason）並儲存才能送出。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, DatePicker, Descriptions, Input, InputNumber, Modal, Space, Table, Tag, Typography, message,
} from 'antd'
import { ArrowLeftOutlined, EditOutlined, SaveOutlined, SendOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  getPayment, setPaymentStatus, submitPayment, updateAllocationItem, updatePayment,
} from '@/api/cyclePurchase'
import type { CpPaymentAllocation, CpPaymentDetail } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  submitted: { color: 'blue',    label: '已送出' },
  paying:    { color: 'gold',    label: '付款中' },
  paid:      { color: 'green',   label: '已付款' },
}

const NEXT_STATUS: Record<string, { status: 'paying' | 'paid'; label: string }> = {
  submitted: { status: 'paying', label: '轉為付款中' },
  paying:    { status: 'paid',   label: '標記已付款' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpPaymentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const paymentId = Number(id)
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canFinance = hasPermission('cycle_purchase_finance')

  const [detail, setDetail] = useState<CpPaymentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [advancing, setAdvancing] = useState(false)
  const [saving, setSaving] = useState(false)

  const [invoiceNo, setInvoiceNo] = useState('')
  const [invoiceDate, setInvoiceDate] = useState<dayjs.Dayjs | null>(null)
  const [invoiceAmount, setInvoiceAmount] = useState<number>(0)
  const [notes, setNotes] = useState('')
  const [diffReason, setDiffReason] = useState('')

  const [adjustRow, setAdjustRow] = useState<CpPaymentAllocation | null>(null)
  const [adjustAmount, setAdjustAmount] = useState<number>(0)
  const [adjustReason, setAdjustReason] = useState('')
  const [adjusting, setAdjusting] = useState(false)

  const editable = canFinance && detail?.status === 'draft'

  const load = async () => {
    if (!paymentId) return
    setLoading(true)
    try {
      const d = (await getPayment(paymentId)).data
      setDetail(d)
      setInvoiceNo(d.invoice_no)
      setInvoiceDate(dayjs(d.invoice_date))
      setInvoiceAmount(Number(d.invoice_amount))
      setNotes(d.notes || '')
      setDiffReason(d.amount_diff_reason || '')
    } catch (err: any) {
      message.error(errMsg(err, '載入失敗'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [paymentId])

  const totalAllocated = useMemo(
    () => (detail?.allocations || []).reduce((sum, a) => sum + Number(a.allocated_amount), 0),
    [detail],
  )
  const diff = useMemo(() => totalAllocated - invoiceAmount, [totalAllocated, invoiceAmount])

  const handleSaveHeader = async () => {
    if (!detail) return
    setSaving(true)
    try {
      await updatePayment(detail.id, {
        invoice_no: invoiceNo.trim(),
        invoice_date: invoiceDate ? invoiceDate.format('YYYY-MM-DD') : undefined,
        invoice_amount: invoiceAmount,
        notes: notes.trim() || null,
        amount_diff_reason: diffReason.trim() || null,
      })
      message.success('已儲存')
      load()
    } catch (err: any) {
      message.error(errMsg(err, '儲存失敗'))
    } finally {
      setSaving(false)
    }
  }

  const openAdjust = (row: CpPaymentAllocation) => {
    setAdjustRow(row)
    setAdjustAmount(Number(row.allocated_amount))
    setAdjustReason(row.adjust_reason || '')
  }

  const handleAdjustSave = async () => {
    if (!adjustRow || !detail) return
    if (adjustAmount !== Number(adjustRow.suggested_amount) && !adjustReason.trim()) {
      message.warning('分攤金額與系統試算值不同時，必須填寫調整原因')
      return
    }
    setAdjusting(true)
    try {
      await updateAllocationItem(detail.id, adjustRow.id, {
        allocated_amount: adjustAmount,
        adjust_reason: adjustReason.trim() || null,
      })
      message.success('已調整')
      setAdjustRow(null)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '調整失敗'))
    } finally {
      setAdjusting(false)
    }
  }

  const handleSubmit = async () => {
    if (!detail) return
    if (diff !== 0 && !diffReason.trim()) {
      message.warning('分攤金額加總與發票金額不符，請先在上方「發票資訊」填寫差異原因並儲存')
      return
    }
    setSubmitting(true)
    try {
      const res = await submitPayment(detail.id)
      message.success(`已送出（${res.data.payment_no}）`)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '送出失敗'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleAdvance = async () => {
    if (!detail) return
    const next = NEXT_STATUS[detail.status]
    if (!next) return
    setAdvancing(true)
    try {
      await setPaymentStatus(detail.id, next.status)
      message.success(`已${next.label}`)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '狀態變更失敗'))
    } finally {
      setAdvancing(false)
    }
  }

  if (!detail) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/payments')} style={{ marginBottom: 16 }}>
          返回清單
        </Button>
        <Card loading={loading} />
      </div>
    )
  }

  const nextAction = NEXT_STATUS[detail.status]

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/payments')}>返回清單</Button>
          <Title level={4} style={{ margin: 0 }}>{detail.payment_no}</Title>
          <Tag color={STATUS_TAG[detail.status]?.color}>{STATUS_TAG[detail.status]?.label || detail.status}</Tag>
        </Space>
        {canFinance && (
          <Space>
            {detail.status === 'draft' && (
              <Button type="primary" icon={<SendOutlined />} loading={submitting} onClick={handleSubmit}>
                送出請款單
              </Button>
            )}
            {nextAction && (
              <Button type="primary" loading={advancing} onClick={handleAdvance}>
                {nextAction.label}
              </Button>
            )}
          </Space>
        )}
      </Space>

      {diff !== 0 && detail.status === 'draft' && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="分攤金額加總與發票金額不符"
          description={`分攤總額 ${totalAllocated.toLocaleString()}，發票金額 ${invoiceAmount.toLocaleString()}，差異 ${diff > 0 ? '+' : ''}${diff.toLocaleString()}。送出前請在下方填寫差異原因並儲存。`}
        />
      )}

      <Card title="發票資訊" style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="採購單號">
            <a onClick={() => navigate(`/cycle-purchase/pos/${detail.po_id}`)}>{detail.po_no}</a>
          </Descriptions.Item>
          <Descriptions.Item label="公司">{detail.company}</Descriptions.Item>
          <Descriptions.Item label="供應商">{detail.vendor_name}</Descriptions.Item>
          <Descriptions.Item label="發票號碼">
            {editable ? (
              <Input value={invoiceNo} onChange={(e) => setInvoiceNo(e.target.value)} />
            ) : detail.invoice_no}
          </Descriptions.Item>
          <Descriptions.Item label="發票日期">
            {editable ? (
              <DatePicker style={{ width: '100%' }} value={invoiceDate} onChange={setInvoiceDate} />
            ) : detail.invoice_date}
          </Descriptions.Item>
          <Descriptions.Item label="發票金額">
            {editable ? (
              <InputNumber min={0} style={{ width: '100%' }} value={invoiceAmount} onChange={(v) => setInvoiceAmount(v ?? 0)} />
            ) : Number(detail.invoice_amount).toLocaleString()}
          </Descriptions.Item>
          <Descriptions.Item label="分攤總額">
            <Text strong>{totalAllocated.toLocaleString()}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="財務處理人員">{detail.processor_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="差異原因">
            {editable ? (
              <Input value={diffReason} onChange={(e) => setDiffReason(e.target.value)} placeholder="分攤總額與發票金額不符時必填" />
            ) : (detail.amount_diff_reason || '—')}
          </Descriptions.Item>
          <Descriptions.Item label="備註" span={3}>
            {editable ? (
              <TextArea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
            ) : (detail.notes || '—')}
          </Descriptions.Item>
        </Descriptions>
        {editable && (
          <div style={{ marginTop: 12, textAlign: 'right' }}>
            <Button icon={<SaveOutlined />} loading={saving} onClick={handleSaveHeader}>儲存發票資訊</Button>
          </div>
        )}
      </Card>

      <Card title="涵蓋的驗收單" style={{ marginBottom: 16 }}>
        <Table
          dataSource={detail.receivings}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            {
              title: '驗收單號',
              dataIndex: 'receiving_no',
              render: (v?: string | null, r?: any) =>
                v ? <a onClick={() => navigate(`/cycle-purchase/receiving/${r.receiving_id}`)}>{v}</a> : '—',
            },
            { title: '驗收日期', dataIndex: 'received_date', width: 130 },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 100,
              render: (v?: string | null) => (v === 'discrepancy' ? <Tag color="orange">有差異</Tag> : <Tag color="green">完成</Tag>),
            },
          ]}
        />
      </Card>

      <Card title="費用分攤明細">
        <Table
          dataSource={detail.allocations}
          rowKey="id"
          size="small"
          pagination={false}
          summary={(pageData) => {
            const sum = pageData.reduce((s, r) => s + Number(r.allocated_amount), 0)
            return (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={4}><Text strong>合計</Text></Table.Summary.Cell>
                <Table.Summary.Cell index={1} />
                <Table.Summary.Cell index={2} align="right"><Text strong>{sum.toLocaleString()}</Text></Table.Summary.Cell>
                <Table.Summary.Cell index={3} colSpan={2} />
              </Table.Summary.Row>
            )
          }}
          columns={[
            {
              title: '部門',
              dataIndex: 'department_name',
              render: (v?: string | null) => v || <Text type="secondary">未歸屬（需手動指定）</Text>,
            },
            { title: '成本中心', dataIndex: 'cost_center_name', render: (v?: string | null) => v || '—' },
            { title: '會計科目', dataIndex: 'account_code_label', render: (v?: string | null) => v || '—' },
            {
              title: '系統試算值',
              dataIndex: 'suggested_amount',
              width: 120,
              align: 'right' as const,
              render: (v: number) => Number(v).toLocaleString(),
            },
            {
              title: '實際分攤金額',
              dataIndex: 'allocated_amount',
              width: 120,
              align: 'right' as const,
              render: (v: number) => Number(v).toLocaleString(),
            },
            { title: '調整原因', dataIndex: 'adjust_reason', render: (v?: string | null) => v || '—' },
            ...(editable
              ? [{
                  title: '操作',
                  key: 'actions',
                  width: 80,
                  render: (_: unknown, row: CpPaymentAllocation) => (
                    <Button size="small" icon={<EditOutlined />} onClick={() => openAdjust(row)}>調整</Button>
                  ),
                }]
              : []),
          ]}
        />
      </Card>

      <Modal
        title={adjustRow ? `調整分攤金額 — ${adjustRow.department_name || '未歸屬'}` : '調整'}
        open={!!adjustRow}
        onOk={handleAdjustSave}
        onCancel={() => setAdjustRow(null)}
        okText="儲存"
        cancelText="取消"
        confirmLoading={adjusting}
      >
        {adjustRow && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="系統試算值">{Number(adjustRow.suggested_amount).toLocaleString()}</Descriptions.Item>
            </Descriptions>
            <div>
              <Text>實際分攤金額</Text>
              <InputNumber min={0} value={adjustAmount} onChange={(v) => setAdjustAmount(v ?? 0)} style={{ width: '100%', marginTop: 4 }} />
            </div>
            <div>
              <Text>調整原因（與試算值不同時必填）</Text>
              <TextArea rows={2} value={adjustReason} onChange={(e) => setAdjustReason(e.target.value)} style={{ marginTop: 4 }} />
            </div>
          </Space>
        )}
      </Modal>
    </div>
  )
}
