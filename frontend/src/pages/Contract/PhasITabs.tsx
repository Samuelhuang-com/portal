/**
 * Phase I — 合約 Drawer Tab 集合
 *
 * I1 — 審核關卡 (ContractApprovalStagesTab)
 * I2 — 驗收記錄 (ContractAcceptancesTab)
 * I3 — 保證金追蹤 (ContractDepositsTab)
 * I4 — 財務摘要卡（CostSummaryCard，嵌入基本資訊 Tab 頂部）
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Table, Button, Space, Modal, Form, Input, Select, DatePicker,
  Popconfirm, Tag, message, Typography, InputNumber, Empty,
  Steps, Card, Statistic, Row, Col, Tooltip, Alert,
} from 'antd'
import {
  CheckOutlined, CloseOutlined, PlusOutlined, DeleteOutlined,
  ReloadOutlined, DollarOutlined, SafetyOutlined, AuditOutlined,
  CheckCircleOutlined, ClockCircleOutlined, StopOutlined,
  BankOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import type {
  ApprovalStage, Acceptance, AcceptanceCreate, Deposit, DepositCreate, CostSummary,
} from '@/types/contract'
import {
  fetchApprovalStages, approveStage, rejectStage,
  fetchAcceptances, createAcceptance, updateAcceptance, deleteAcceptance,
  fetchDeposits, createDeposit, updateDeposit, deleteDeposit,
  fetchCostSummary,
} from '@/api/contract'

const { Text, Title } = Typography

// ─────────────────────────────────────────────────────────────────────────────
// I1 — 審核關卡 Tab
// ─────────────────────────────────────────────────────────────────────────────

const STAGE_STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  待審核: { color: 'processing', icon: <ClockCircleOutlined /> },
  已核准: { color: 'success',    icon: <CheckCircleOutlined /> },
  已拒絕: { color: 'error',      icon: <CloseOutlined /> },
  已取消: { color: 'default',    icon: <StopOutlined /> },
}

export function ContractApprovalStagesTab({
  contractId, open, contractStatus,
}: { contractId: string; open: boolean; contractStatus: string }) {
  const [stages, setStages] = useState<ApprovalStage[]>([])
  const [loading, setLoading] = useState(false)
  const [reviewModal, setReviewModal] = useState<{ stageId: number; action: 'approve' | 'reject' } | null>(null)
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const res = await fetchApprovalStages(contractId)
      setStages(res.stages)
    } catch {
      message.error('載入審核關卡失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { load() }, [load])

  const handleReview = async () => {
    if (!reviewModal) return
    setSaving(true)
    try {
      if (reviewModal.action === 'approve') {
        const r = await approveStage(contractId, reviewModal.stageId, comment)
        if (r.contract_promoted) {
          message.success('關卡核准！所有關卡已通過，合約已升為「生效中」')
        } else {
          message.success('關卡核准，等待下一關卡審核')
        }
      } else {
        await rejectStage(contractId, reviewModal.stageId, comment)
        message.warning('關卡已拒絕，合約退回草稿')
      }
      setReviewModal(null)
      setComment('')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    } finally {
      setSaving(false)
    }
  }

  if (!stages.length && !loading) {
    return (
      <Empty
        description={
          contractStatus === '審核中'
            ? '此合約未設定多層審核關卡，使用原有單階段審核流程'
            : '尚無審核關卡記錄（送審後自動建立）'
        }
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    )
  }

  // Steps 顯示
  const currentStep = stages.findIndex(s => s.status === '待審核')
  const stepsItems = stages.map(s => {
    const cfg = STAGE_STATUS_CONFIG[s.status] || { color: 'default', icon: null }
    return {
      title: s.stage_name,
      status: s.status === '已核准' ? 'finish' as const
            : s.status === '已拒絕' ? 'error' as const
            : s.status === '待審核' ? 'process' as const
            : 'wait' as const,
      description: (
        <div style={{ fontSize: 12 }}>
          {s.reviewer && <div>審核人：{s.reviewer}</div>}
          {s.reviewed_at && <div>{dayjs(s.reviewed_at).format('MM/DD HH:mm')}</div>}
          {s.comment && <div style={{ color: '#596780' }}>{s.comment}</div>}
          {s.status === '待審核' && (
            <Space size={4} style={{ marginTop: 4 }}>
              <Button
                size="small" type="primary" ghost icon={<CheckOutlined />}
                onClick={() => { setComment(''); setReviewModal({ stageId: s.id, action: 'approve' }) }}
              >核准</Button>
              <Button
                size="small" danger ghost icon={<CloseOutlined />}
                onClick={() => { setComment(''); setReviewModal({ stageId: s.id, action: 'reject' }) }}
              >拒絕</Button>
            </Space>
          )}
        </div>
      ),
    }
  })

  return (
    <>
      <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading} style={{ marginBottom: 16 }}>
        重新載入
      </Button>
      <Steps
        direction="vertical"
        current={currentStep === -1 ? stages.length : currentStep}
        items={stepsItems}
      />

      <Modal
        title={reviewModal?.action === 'approve' ? '核准此審核關卡' : '拒絕此審核關卡'}
        open={!!reviewModal}
        onOk={handleReview}
        onCancel={() => setReviewModal(null)}
        confirmLoading={saving}
        okText={reviewModal?.action === 'approve' ? '確認核准' : '確認拒絕'}
        okButtonProps={{ danger: reviewModal?.action === 'reject' }}
        cancelText="取消"
        destroyOnClose
      >
        <Form layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item label="審核意見（選填）">
            <Input.TextArea
              rows={3}
              value={comment}
              onChange={e => setComment(e.target.value)}
              placeholder={reviewModal?.action === 'approve' ? '如：符合規範，同意通過' : '如：條款需修訂，請重新提交'}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}


// ─────────────────────────────────────────────────────────────────────────────
// I2 — 驗收記錄 Tab
// ─────────────────────────────────────────────────────────────────────────────

const ACCEPTANCE_STATUS_COLOR: Record<string, string> = {
  待驗收: 'default',
  已驗收: 'success',
  驗收失敗: 'error',
}

export function ContractAcceptancesTab({
  contractId, open,
}: { contractId: string; open: boolean }) {
  const [acceptances, setAcceptances] = useState<Acceptance[]>([])
  const [loading, setLoading] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const res = await fetchAcceptances(contractId)
      setAcceptances(res.acceptances)
    } catch {
      message.error('載入驗收記錄失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { load() }, [load])

  const handleAdd = async () => {
    try {
      const v = await form.validateFields()
      setSaving(true)
      const payload: AcceptanceCreate = {
        acceptance_name: v.acceptance_name,
        acceptance_date: v.acceptance_date.format('YYYY-MM-DD'),
        accepted_by: v.accepted_by,
        status: v.status || '待驗收',
        period_start: v.period_start ? v.period_start.format('YYYY-MM-DD') : undefined,
        period_end:   v.period_end   ? v.period_end.format('YYYY-MM-DD')   : undefined,
        notes: v.notes,
      }
      await createAcceptance(contractId, payload)
      message.success('已新增驗收記錄')
      setAddOpen(false)
      form.resetFields()
      load()
    } catch (err: any) {
      if (err?.response?.data?.detail) message.error(err.response.data.detail)
    } finally {
      setSaving(false)
    }
  }

  const markStatus = async (acc: Acceptance, newStatus: string) => {
    try {
      await updateAcceptance(contractId, acc.id, { status: newStatus })
      message.success(`已更新為「${newStatus}」`)
      load()
    } catch {
      message.error('更新失敗')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteAcceptance(contractId, id)
      message.success('已刪除')
      load()
    } catch {
      message.error('刪除失敗')
    }
  }

  const columns = [
    {
      title: '驗收項目',
      dataIndex: 'acceptance_name',
      key: 'acceptance_name',
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '驗收日期',
      dataIndex: 'acceptance_date',
      key: 'acceptance_date',
      width: 110,
    },
    {
      title: '服務期間',
      key: 'period',
      width: 180,
      render: (_: any, rec: Acceptance) =>
        rec.period_start ? `${rec.period_start} ~ ${rec.period_end || ''}` : '—',
    },
    {
      title: '驗收人',
      dataIndex: 'accepted_by',
      key: 'accepted_by',
      width: 100,
      render: (v: string) => <Tag>{v || '—'}</Tag>,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => <Tag color={ACCEPTANCE_STATUS_COLOR[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      render: (_: any, rec: Acceptance) => (
        <Space size={4}>
          {rec.status === '待驗收' && (
            <>
              <Tooltip title="標記已驗收">
                <Button size="small" type="primary" ghost icon={<CheckOutlined />}
                  onClick={() => markStatus(rec, '已驗收')} />
              </Tooltip>
              <Tooltip title="標記驗收失敗">
                <Button size="small" danger ghost icon={<CloseOutlined />}
                  onClick={() => markStatus(rec, '驗收失敗')} />
              </Tooltip>
            </>
          )}
          <Popconfirm title="確定刪除？" onConfirm={() => handleDelete(rec.id)} okText="刪除" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>重新載入</Button>
        <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setAddOpen(true) }}>
          新增驗收記錄
        </Button>
      </Space>
      <Table dataSource={acceptances} columns={columns} rowKey="id" loading={loading} size="small" pagination={false} />

      <Modal title="新增驗收記錄" open={addOpen} onOk={handleAdd} onCancel={() => setAddOpen(false)}
        confirmLoading={saving} okText="新增" cancelText="取消" destroyOnClose width={560}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="acceptance_name" label="驗收項目名稱" rules={[{ required: true }]}>
            <Input placeholder="例：2026 年 Q1 清潔服務驗收" />
          </Form.Item>
          <Form.Item name="acceptance_date" label="驗收日期" rules={[{ required: true, message: '請選擇日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="accepted_by" label="驗收人" rules={[{ required: true }]}>
            <Input placeholder="驗收人帳號或姓名" />
          </Form.Item>
          <Form.Item name="status" label="初始狀態" initialValue="待驗收">
            <Select options={['待驗收','已驗收','驗收失敗'].map(s => ({ value: s, label: s }))} />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="period_start" label="服務期間起" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="period_end" label="服務期間迄" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}


// ─────────────────────────────────────────────────────────────────────────────
// I3 — 保證金追蹤 Tab
// ─────────────────────────────────────────────────────────────────────────────

const DEPOSIT_STATUS_COLOR: Record<string, string> = {
  保留中:   'processing',
  申請退還: 'warning',
  已退還:   'success',
  已沒收:   'error',
}
const DEPOSIT_TYPES = ['履約保證金', '投標保證金', '其他']

export function ContractDepositsTab({
  contractId, open,
}: { contractId: string; open: boolean }) {
  const [deposits, setDeposits] = useState<Deposit[]>([])
  const [loading, setLoading] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const res = await fetchDeposits(contractId)
      setDeposits(res.deposits)
    } catch {
      message.error('載入保證金資料失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { load() }, [load])

  const handleAdd = async () => {
    try {
      const v = await form.validateFields()
      setSaving(true)
      const payload: DepositCreate = {
        deposit_type:         v.deposit_type || '履約保證金',
        deposit_amount:       v.deposit_amount,
        deposit_date:         v.deposit_date.format('YYYY-MM-DD'),
        expected_return_date: v.expected_return_date.format('YYYY-MM-DD'),
        bank_name: v.bank_name,
        notes:     v.notes,
      }
      await createDeposit(contractId, payload)
      message.success('已新增保證金記錄')
      setAddOpen(false)
      form.resetFields()
      load()
    } catch (err: any) {
      if (err?.response?.data?.detail) message.error(err.response.data.detail)
    } finally {
      setSaving(false)
    }
  }

  const markReturned = async (dep: Deposit) => {
    try {
      await updateDeposit(contractId, dep.id, {
        status: '已退還',
        actual_return_date: dayjs().format('YYYY-MM-DD'),
      })
      message.success('已標記為已退還')
      load()
    } catch {
      message.error('操作失敗')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteDeposit(contractId, id)
      message.success('已刪除')
      load()
    } catch {
      message.error('刪除失敗')
    }
  }

  const totalDeposit = deposits.filter(d => d.status === '保留中' || d.status === '申請退還')
    .reduce((s, d) => s + d.deposit_amount, 0)

  const columns = [
    {
      title: '類型',
      dataIndex: 'deposit_type',
      key: 'deposit_type',
      width: 110,
      render: (v: string) => <Tag icon={<SafetyOutlined />}>{v}</Tag>,
    },
    {
      title: '金額',
      dataIndex: 'deposit_amount',
      key: 'deposit_amount',
      width: 120,
      align: 'right' as const,
      render: (v: number) => <Text strong>${Number(v).toLocaleString('zh-TW')}</Text>,
    },
    {
      title: '存入日',
      dataIndex: 'deposit_date',
      key: 'deposit_date',
      width: 100,
    },
    {
      title: '預計退還日',
      dataIndex: 'expected_return_date',
      key: 'expected_return_date',
      width: 110,
      render: (v: string, rec: Deposit) => {
        const daysLeft = dayjs(v).diff(dayjs(), 'day')
        const warn = rec.status === '保留中' && daysLeft <= 30 && daysLeft >= 0
        return (
          <Tooltip title={warn ? `距今 ${daysLeft} 天` : undefined}>
            <Text style={{ color: warn ? '#fa8c16' : undefined }}>{v}</Text>
          </Tooltip>
        )
      },
    },
    {
      title: '銀行',
      dataIndex: 'bank_name',
      key: 'bank_name',
      render: (v: string) => v || '—',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => <Tag color={DEPOSIT_STATUS_COLOR[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 110,
      render: (_: any, rec: Deposit) => (
        <Space size={4}>
          {rec.status === '保留中' && (
            <Popconfirm title="確認標記為已退還？" onConfirm={() => markReturned(rec)} okText="確認" cancelText="取消">
              <Tooltip title="標記已退還">
                <Button size="small" type="primary" ghost icon={<CheckOutlined />} />
              </Tooltip>
            </Popconfirm>
          )}
          <Popconfirm title="確定刪除？" onConfirm={() => handleDelete(rec.id)} okText="刪除" cancelText="取消">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>重新載入</Button>
        <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setAddOpen(true) }}>
          新增保證金
        </Button>
        {totalDeposit > 0 && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            保留中合計：${totalDeposit.toLocaleString('zh-TW')}
          </Text>
        )}
      </Space>
      <Table dataSource={deposits} columns={columns} rowKey="id" loading={loading} size="small" pagination={false} />

      <Modal title="新增保證金記錄" open={addOpen} onOk={handleAdd} onCancel={() => setAddOpen(false)}
        confirmLoading={saving} okText="新增" cancelText="取消" destroyOnClose width={520}>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="deposit_type" label="保證金類型" initialValue="履約保證金">
            <Select options={DEPOSIT_TYPES.map(t => ({ value: t, label: t }))} />
          </Form.Item>
          <Form.Item name="deposit_amount" label="金額" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} precision={0}
              formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(v) => Number(String(v).replace(/\$\s?|(,*)/g, '')) as 0} />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="deposit_date" label="存入日期" rules={[{ required: true, message: '請選擇' }]} style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="expected_return_date" label="預計退還日" rules={[{ required: true, message: '請選擇' }]} style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item name="bank_name" label="銀行名稱">
            <Input placeholder="例：台灣銀行" />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}


// ─────────────────────────────────────────────────────────────────────────────
// I4 — 財務摘要卡（嵌入基本資訊 Tab 頂部）
// ─────────────────────────────────────────────────────────────────────────────

export function CostSummaryCard({
  contractId, open,
}: { contractId: string; open: boolean }) {
  const [summary, setSummary] = useState<CostSummary | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !contractId) return
    setLoading(true)
    fetchCostSummary(contractId)
      .then(setSummary)
      .catch(() => {/* 靜默失敗，不影響主要資訊 */})
      .finally(() => setLoading(false))
  }, [contractId, open])

  if (!summary && !loading) return null

  const fmt = (n?: number | null) =>
    n != null ? `$${Number(n).toLocaleString('zh-TW', { minimumFractionDigits: 0 })}` : '—'

  const pctColor = summary
    ? summary.claimed_percentage >= 100 ? '#ff4d4f'
    : summary.claimed_percentage >= 80  ? '#fa8c16'
    : '#52c41a'
    : '#52c41a'

  return (
    <Card
      size="small"
      style={{ marginBottom: 16, borderColor: '#4BA8E8' }}
      title={<Space><DollarOutlined style={{ color: '#4BA8E8' }} /><Text strong style={{ color: '#1B3A5C' }}>財務摘要</Text></Space>}
      loading={loading}
    >
      <Row gutter={12}>
        <Col span={6}>
          <Statistic title="合約總額" value={summary?.total_amount} formatter={v => fmt(Number(v))} valueStyle={{ fontSize: 15 }} />
        </Col>
        <Col span={6}>
          <Statistic
            title={summary?.is_monthly_contract ? '年化金額（月費×12）' : '月攤提'}
            value={summary?.annual_amount ?? summary?.monthly_amortization}
            formatter={v => fmt(Number(v))}
            valueStyle={{ fontSize: 15 }}
          />
        </Col>
        <Col span={6}>
          <Statistic
            title="請款比例"
            value={summary?.claimed_percentage ?? 0}
            suffix="%"
            precision={1}
            valueStyle={{ fontSize: 15, color: pctColor }}
          />
        </Col>
        <Col span={6}>
          <Statistic title="剩餘額度" value={summary?.remaining_amount} formatter={v => fmt(Number(v))}
            valueStyle={{ fontSize: 15, color: (summary?.remaining_amount ?? 0) < 0 ? '#ff4d4f' : undefined }} />
        </Col>
      </Row>
      {summary?.is_monthly_contract && (
        <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 6 }}>
          月費合約 · 合約期間 {summary.duration_months} 個月（{summary.duration_days} 天）
        </Text>
      )}
      {(summary?.claimed_percentage ?? 0) >= 80 && (
        <Alert
          type={(summary?.claimed_percentage ?? 0) >= 100 ? 'error' : 'warning'}
          message={`請款金額已達合約總額的 ${summary?.claimed_percentage?.toFixed(1)}%，請注意預算使用情況`}
          style={{ marginTop: 8, padding: '4px 10px', fontSize: 12 }}
          showIcon
        />
      )}
    </Card>
  )
}
