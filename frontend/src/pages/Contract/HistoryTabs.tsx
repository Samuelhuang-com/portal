/**
 * Phase H — 合約 Drawer 歷程 Tab 集合
 *
 * H2 — 變更歷程 (ContractChangeLogTab)
 * H3 — 付款計劃 (ContractPaymentScheduleTab)
 * H4 — 稽核日誌 (ContractAuditLogTab)
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Table, Button, Space, Modal, Form, Input, DatePicker,
  Popconfirm, Tag, message, Typography, InputNumber, Empty, Timeline,
  Tooltip,
} from 'antd'
import {
  PlusOutlined, CheckOutlined, DeleteOutlined, ReloadOutlined,
  ClockCircleOutlined, DollarOutlined, AuditOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import type { ContractChangeLog, PaymentSchedule, ContractAuditLog } from '@/types/contract'
import {
  fetchChangeLogs,
  fetchPaymentSchedules, createPaymentSchedule, updatePaymentSchedule, deletePaymentSchedule,
  fetchAuditLogs,
} from '@/api/contract'

const { Text } = Typography

// ── H2 — 變更歷程 Tab ─────────────────────────────────────────────────────────

export function ContractChangeLogTab({
  contractId, open,
}: { contractId: string; open: boolean }) {
  const [logs, setLogs] = useState<ContractChangeLog[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const res = await fetchChangeLogs(contractId, 200)
      setLogs(res.logs)
    } catch {
      message.error('載入變更歷程失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { load() }, [load])

  if (!logs.length && !loading) {
    return <Empty description="尚無變更記錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  // 依操作時間分組顯示
  const columns = [
    {
      title: '時間',
      dataIndex: 'operated_at',
      key: 'operated_at',
      width: 150,
      render: (v: string) => dayjs(v).format('MM/DD HH:mm'),
    },
    {
      title: '欄位',
      dataIndex: 'field_label',
      key: 'field_label',
      width: 120,
      render: (label: string, row: ContractChangeLog) => (
        <Text code style={{ fontSize: 12 }}>{label || row.field_name}</Text>
      ),
    },
    {
      title: '舊值',
      dataIndex: 'old_value',
      key: 'old_value',
      render: (v: string) => (
        <Text delete type="secondary" style={{ fontSize: 12 }}>{v ?? '—'}</Text>
      ),
    },
    {
      title: '新值',
      dataIndex: 'new_value',
      key: 'new_value',
      render: (v: string) => (
        <Text style={{ fontSize: 12, color: '#389e0d' }}>{v ?? '—'}</Text>
      ),
    },
    {
      title: '操作人',
      dataIndex: 'operator',
      key: 'operator',
      width: 100,
      render: (v: string) => <Tag>{v || '—'}</Tag>,
    },
  ]

  return (
    <Table
      dataSource={logs}
      columns={columns}
      rowKey="id"
      loading={loading}
      size="small"
      pagination={{ pageSize: 20 }}
    />
  )
}


// ── H3 — 分期付款計劃 Tab ─────────────────────────────────────────────────────

const STATUS_COLOR: Record<string, string> = {
  待付款: 'processing',
  已付款: 'success',
  逾期:   'error',
  取消:   'default',
}

export function ContractPaymentScheduleTab({
  contractId, open,
}: { contractId: string; open: boolean }) {
  const [schedules, setSchedules] = useState<PaymentSchedule[]>([])
  const [loading, setLoading] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const res = await fetchPaymentSchedules(contractId)
      setSchedules(res.schedules)
    } catch {
      message.error('載入付款計劃失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { load() }, [load])

  const handleAdd = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      await createPaymentSchedule(contractId, {
        milestone_name: values.milestone_name,
        due_date: values.due_date.format('YYYY-MM-DD'),
        amount: values.amount,
        notes: values.notes,
      })
      message.success('已新增付款里程碑')
      setAddOpen(false)
      form.resetFields()
      load()
    } catch (err: any) {
      if (err?.response?.data?.detail) message.error(err.response.data.detail)
    } finally {
      setSaving(false)
    }
  }

  const markPaid = async (ps: PaymentSchedule) => {
    try {
      await updatePaymentSchedule(contractId, ps.id, {
        status: '已付款',
        paid_date: dayjs().format('YYYY-MM-DD'),
      })
      message.success('已標記為已付款')
      load()
    } catch {
      message.error('操作失敗')
    }
  }

  const handleDelete = async (ps: PaymentSchedule) => {
    try {
      await deletePaymentSchedule(contractId, ps.id)
      message.success('已刪除')
      load()
    } catch {
      message.error('刪除失敗')
    }
  }

  // 總計
  const totalAmount = schedules.reduce((s, r) => s + r.amount, 0)
  const paidAmount  = schedules.filter(r => r.status === '已付款').reduce((s, r) => s + r.amount, 0)

  const columns = [
    {
      title: '里程碑',
      dataIndex: 'milestone_name',
      key: 'milestone_name',
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '應付日期',
      dataIndex: 'due_date',
      key: 'due_date',
      width: 110,
      render: (v: string, row: PaymentSchedule) => {
        const isOverdue = row.status === '逾期' || (row.status === '待付款' && dayjs(v).isBefore(dayjs(), 'day'))
        return <Text style={{ color: isOverdue ? '#ff4d4f' : undefined }}>{v}</Text>
      },
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      align: 'right' as const,
      render: (v: number) => <Text strong>${Number(v).toLocaleString('zh-TW')}</Text>,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => <Tag color={STATUS_COLOR[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '實際付款日',
      dataIndex: 'paid_date',
      key: 'paid_date',
      width: 110,
      render: (v: string) => v || '—',
    },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      render: (_: any, rec: PaymentSchedule) => (
        <Space>
          {rec.status === '待付款' && (
            <Popconfirm
              title="確認標記為已付款？"
              onConfirm={() => markPaid(rec)}
              okText="確認"
              cancelText="取消"
            >
              <Tooltip title="標記已付款">
                <Button size="small" type="primary" ghost icon={<CheckOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
          <Popconfirm
            title="確定刪除此里程碑？"
            onConfirm={() => handleDelete(rec)}
            okText="刪除"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button icon={<ReloadOutlined />} size="small" onClick={load} loading={loading}>重新載入</Button>
        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setAddOpen(true) }}>
          新增里程碑
        </Button>
        <Text type="secondary" style={{ fontSize: 12 }}>
          已付 ${paidAmount.toLocaleString('zh-TW')} / 共 ${totalAmount.toLocaleString('zh-TW')}
        </Text>
      </Space>

      <Table
        dataSource={schedules}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={false}
      />

      <Modal
        title="新增付款里程碑"
        open={addOpen}
        onOk={handleAdd}
        onCancel={() => setAddOpen(false)}
        confirmLoading={saving}
        okText="新增"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="milestone_name" label="里程碑名稱" rules={[{ required: true }]}>
            <Input placeholder="例：第一期款、尾款" />
          </Form.Item>
          <Form.Item name="due_date" label="應付日期" rules={[{ required: true, message: '請選擇日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="amount" label="應付金額（含稅）" rules={[{ required: true }]}>
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={0}
              formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(v) => Number(String(v).replace(/\$\s?|(,*)/g, '')) as 0}
            />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}


// ── H4 — 操作稽核日誌 Tab ─────────────────────────────────────────────────────

const ACTION_COLOR: Record<string, string> = {
  create: 'blue',
  update: 'geekblue',
  delete: 'red',
  approve: 'green',
  reject: 'orange',
  submit: 'cyan',
}

export function ContractAuditLogTab({
  contractId, open,
}: { contractId: string; open: boolean }) {
  const [logs, setLogs] = useState<ContractAuditLog[]>([])
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const res = await fetchAuditLogs(contractId, 200)
      setLogs(res.logs)
    } catch {
      message.error('載入稽核日誌失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { load() }, [load])

  if (!logs.length && !loading) {
    return <Empty description="尚無操作紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  const ACTION_LABELS: Record<string, string> = {
    create: '建立', update: '修改', delete: '刪除',
    approve: '核准', reject: '拒絕', submit: '送審',
  }

  return (
    <Timeline
      mode="left"
      style={{ paddingTop: 8 }}
      items={logs.map(log => ({
        key: log.id,
        color: log.result === 'error' ? 'red' : (ACTION_COLOR[log.action] || 'blue'),
        label: (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {dayjs(log.operated_at).format('MM/DD HH:mm')}
          </Text>
        ),
        children: (
          <div style={{ fontSize: 13 }}>
            <Space size={4}>
              <Tag color={ACTION_COLOR[log.action] || 'default'} style={{ fontSize: 11 }}>
                {ACTION_LABELS[log.action] || log.action}
              </Tag>
              <Text type="secondary">{log.resource}</Text>
              {log.resource_id && log.resource_id !== log.contract_id && (
                <Text type="secondary">#{log.resource_id}</Text>
              )}
              <Tag>{log.operator}</Tag>
            </Space>
            {log.payload_summary && (
              <div style={{ color: '#596780', fontSize: 12, marginTop: 2 }}>
                {log.payload_summary}
              </div>
            )}
            {log.result === 'error' && log.error_detail && (
              <div style={{ color: '#ff4d4f', fontSize: 11 }}>{log.error_detail}</div>
            )}
          </div>
        ),
      }))}
    />
  )
}
