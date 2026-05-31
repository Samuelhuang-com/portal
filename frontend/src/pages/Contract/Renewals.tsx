/**
 * 合約續約管理頁面
 *
 * 功能：
 *  - 列出所有續約申請（可依狀態篩選）
 *  - 管理員核准 / 拒絕
 *  - 申請人可撤回自己的待審核申請
 */
import { useEffect, useState, useCallback } from 'react'
import {
  Card, Table, Tag, Button, Space, Select, Drawer, Descriptions,
  message, Breadcrumb, Typography, Popconfirm, Modal, Form, Input, Empty,
  Tooltip,
} from 'antd'
import {
  AuditOutlined, CheckOutlined, CloseOutlined, UndoOutlined,
  ReloadOutlined, EyeOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { fetchAllRenewals, reviewRenewal } from '@/api/contract'
import type { RenewalRecord } from '@/types/contract'

const { Text } = Typography

const STATUS_COLOR: Record<string, string> = {
  待審核: 'gold',
  已核准: 'green',
  已拒絕: 'red',
  已撤回: 'default',
}

function fmtMoney(v: number | null) {
  if (v == null) return '—（同原合約）'
  return `$${Number(v).toLocaleString('zh-TW', { minimumFractionDigits: 0 })}`
}

function fmtDate(s: string | null) {
  if (!s) return '—'
  return s.slice(0, 10)
}

export default function RenewalsPage() {
  const [data, setData] = useState<RenewalRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)

  // 明細 Drawer
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selected, setSelected] = useState<RenewalRecord | null>(null)

  // 審核 Modal
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject' | 'withdraw'>('approve')
  const [reviewTarget, setReviewTarget] = useState<RenewalRecord | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewForm] = Form.useForm()

  const load = useCallback(async (p = page, st = statusFilter) => {
    setLoading(true)
    try {
      const res = await fetchAllRenewals({ page: p, size: 20, status: st })
      setData(res.items)
      setTotal(res.total)
    } catch {
      message.error('無法載入續約申請')
    } finally {
      setLoading(false)
    }
  }, [page, statusFilter])

  useEffect(() => { load() }, [load])

  const openReview = (record: RenewalRecord, action: 'approve' | 'reject' | 'withdraw') => {
    setReviewTarget(record)
    setReviewAction(action)
    reviewForm.resetFields()
    setReviewOpen(true)
  }

  const handleReview = async () => {
    const values = await reviewForm.validateFields()
    if (!reviewTarget) return
    setReviewLoading(true)
    try {
      await reviewRenewal(reviewTarget.id, {
        action: reviewAction,
        review_comment: values.review_comment,
      })
      const actionLabel = { approve: '核准', reject: '拒絕', withdraw: '撤回' }[reviewAction]
      message.success(`已${actionLabel}續約申請 #${reviewTarget.id}`)
      setReviewOpen(false)
      load(page, statusFilter)
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '操作失敗')
    } finally {
      setReviewLoading(false)
    }
  }

  const columns: ColumnsType<RenewalRecord> = [
    {
      title: '申請編號',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      render: (id) => `#${id}`,
    },
    {
      title: '合約編號',
      dataIndex: 'contract_id',
      key: 'contract_id',
      width: 140,
      ellipsis: true,
    },
    {
      title: '續約期間',
      key: 'period',
      width: 200,
      render: (_, r) => `${r.renewal_start_date} ～ ${r.renewal_end_date}`,
    },
    {
      title: '續約金額',
      dataIndex: 'new_amount',
      key: 'new_amount',
      width: 140,
      render: fmtMoney,
    },
    {
      title: '申請人',
      dataIndex: 'applicant',
      key: 'applicant',
      width: 100,
    },
    {
      title: '申請部門',
      dataIndex: 'applicant_dept',
      key: 'applicant_dept',
      width: 110,
      ellipsis: true,
      render: (v) => v || '—',
    },
    {
      title: '申請時間',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (v) => fmtDate(v),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (s) => <Tag color={STATUS_COLOR[s] ?? 'default'}>{s}</Tag>,
    },
    {
      title: '審核人',
      dataIndex: 'reviewer',
      key: 'reviewer',
      width: 90,
      render: (v) => v || '—',
    },
    {
      title: '操作',
      key: 'actions',
      width: 160,
      fixed: 'right' as const,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看明細">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => { setSelected(record); setDrawerOpen(true) }}
            />
          </Tooltip>
          {record.status === '待審核' && (
            <>
              <Tooltip title="核准">
                <Button
                  type="text"
                  size="small"
                  style={{ color: '#52c41a' }}
                  icon={<CheckOutlined />}
                  onClick={() => openReview(record, 'approve')}
                />
              </Tooltip>
              <Tooltip title="拒絕">
                <Button
                  type="text"
                  size="small"
                  danger
                  icon={<CloseOutlined />}
                  onClick={() => openReview(record, 'reject')}
                />
              </Tooltip>
              <Tooltip title="撤回申請">
                <Popconfirm
                  title="確認撤回此續約申請？"
                  onConfirm={() => openReview(record, 'withdraw')}
                  okText="撤回"
                  cancelText="取消"
                >
                  <Button type="text" size="small" icon={<UndoOutlined />} />
                </Popconfirm>
              </Tooltip>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      <Breadcrumb style={{ marginBottom: 16 }}>
        <Breadcrumb.Item><AuditOutlined /> 合約管理</Breadcrumb.Item>
        <Breadcrumb.Item>續約管理</Breadcrumb.Item>
      </Breadcrumb>

      <Card>
        <Space style={{ marginBottom: 16 }}>
          <Select
            allowClear
            placeholder="篩選狀態"
            style={{ width: 130 }}
            value={statusFilter}
            onChange={(v) => { setStatusFilter(v); setPage(1); load(1, v) }}
            options={[
              { value: '待審核', label: '待審核' },
              { value: '已核准', label: '已核准' },
              { value: '已拒絕', label: '已拒絕' },
              { value: '已撤回', label: '已撤回' },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => load(page, statusFilter)}>
            重新整理
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="id"
          scroll={{ x: 1200 }}
          pagination={{
            current: page,
            pageSize: 20,
            total,
            showTotal: (t) => `共 ${t} 筆`,
            onChange: (p) => { setPage(p); load(p, statusFilter) },
          }}
          locale={{ emptyText: <Empty description="尚無續約申請" /> }}
        />
      </Card>

      {/* 明細 Drawer */}
      <Drawer
        title={
          <Space>
            <Tag color="blue">續約申請</Tag>
            <span>{`合約：${selected?.contract_id ?? ''}`}</span>
            {selected && (
              <Tag color={STATUS_COLOR[selected.status] ?? 'default'}>{selected.status}</Tag>
            )}
          </Space>
        }
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        destroyOnClose
      >
        {selected && (
          <>
            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="申請編號">{`#${selected.id}`}</Descriptions.Item>
              <Descriptions.Item label="合約編號">{selected.contract_id}</Descriptions.Item>
              <Descriptions.Item label="申請人">{selected.applicant}</Descriptions.Item>
              <Descriptions.Item label="申請部門">{selected.applicant_dept || '—'}</Descriptions.Item>
              <Descriptions.Item label="申請時間">{fmtDate(selected.created_at)}</Descriptions.Item>
            </Descriptions>

            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}
              title="續約內容">
              <Descriptions.Item label="續約起日">{selected.renewal_start_date}</Descriptions.Item>
              <Descriptions.Item label="續約迄日">{selected.renewal_end_date}</Descriptions.Item>
              <Descriptions.Item label="續約金額">{fmtMoney(selected.new_amount)}</Descriptions.Item>
              <Descriptions.Item label="續約原因">
                <Text style={{ whiteSpace: 'pre-wrap' }}>{selected.renewal_reason}</Text>
              </Descriptions.Item>
              {selected.remarks && (
                <Descriptions.Item label="備註">{selected.remarks}</Descriptions.Item>
              )}
            </Descriptions>

            {selected.reviewer && (
              <Descriptions column={1} size="small" bordered title="審核資訊">
                <Descriptions.Item label="審核人">{selected.reviewer}</Descriptions.Item>
                <Descriptions.Item label="審核時間">{fmtDate(selected.reviewed_at)}</Descriptions.Item>
                <Descriptions.Item label="審核意見">{selected.review_comment || '—'}</Descriptions.Item>
              </Descriptions>
            )}
          </>
        )}
      </Drawer>

      {/* 審核 Modal */}
      <Modal
        title={
          reviewAction === 'approve' ? '核准續約申請' :
          reviewAction === 'reject'  ? '拒絕續約申請' : '撤回續約申請'
        }
        open={reviewOpen}
        onOk={handleReview}
        onCancel={() => setReviewOpen(false)}
        confirmLoading={reviewLoading}
        okText={
          reviewAction === 'approve' ? '確認核准' :
          reviewAction === 'reject'  ? '確認拒絕' : '確認撤回'
        }
        okButtonProps={{ danger: reviewAction === 'reject' }}
        cancelText="取消"
        destroyOnClose
      >
        <Form form={reviewForm} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item
            name="review_comment"
            label="審核意見（選填）"
          >
            <Input.TextArea rows={3} placeholder="輸入審核意見或說明..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
