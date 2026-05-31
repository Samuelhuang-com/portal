/**
 * 請款 / 核銷管理頁面
 *
 * 路徑：/contract/claims
 * 功能：全局請款清單（分頁+篩選）、新增、編輯、刪除、Drawer 明細
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Card, Table, Tag, Button, Space, Typography, Breadcrumb,
  Row, Col, Select, Input, Modal, Form, InputNumber, Popconfirm,
  Tooltip, message, Drawer, Descriptions, DatePicker, Timeline, Badge, Alert,
  Upload, Image, Divider, Spin,
} from 'antd'
import {
  HomeOutlined, PlusOutlined, DeleteOutlined,
  ReloadOutlined, SearchOutlined, EditOutlined,
  CheckOutlined, CloseOutlined, DollarOutlined, RedoOutlined,
  HistoryOutlined, WarningOutlined, DownloadOutlined,
  PaperClipOutlined, FilePdfOutlined, FileImageOutlined, InboxOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TableProps } from 'antd/es/table'
import type { UploadProps } from 'antd'
import dayjs from 'dayjs'

import {
  fetchClaims, createClaim, updateClaim, deleteClaim, reviewClaim, fetchContracts,
  batchReviewClaims, exportClaimsExcel,
  fetchClaimAttachments, uploadClaimAttachment, deleteClaimAttachment, getAttachmentUrl,
  type ClaimRecord, type ClaimCreate, type ClaimReviewLogEntry,
} from '@/api/contract'
import type { ClaimAttachment } from '@/types/contract'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography
const { Option } = Select

// ── 常數 ──────────────────────────────────────────────────────────────────────
const CLAIM_TYPE_OPTIONS = ['請款', '核銷', '其他']
const STATUS_OPTIONS     = ['待審核', '已核准', '已拒絕', '已付款']

const STATUS_COLOR: Record<string, string> = {
  '待審核': 'default',
  '已核准': 'success',
  '已拒絕': 'error',
  '已付款': 'blue',
}

// 審核動作設定
const REVIEW_ACTIONS = {
  approve:   { label: '核准',   icon: <CheckOutlined />,  color: '#52C41A', btnType: 'primary'  as const, needComment: false },
  reject:    { label: '拒絕',   icon: <CloseOutlined />,  color: '#FF4D4F', btnType: 'default'  as const, needComment: true  },
  mark_paid: { label: '標記付款', icon: <DollarOutlined />, color: '#722ED1', btnType: 'default'  as const, needComment: false },
  resubmit:  { label: '重新送審', icon: <RedoOutlined />,   color: '#FAAD14', btnType: 'default'  as const, needComment: false },
} as const

type ReviewAction = keyof typeof REVIEW_ACTIONS

// 狀態可執行的動作
const STATUS_ACTIONS: Record<string, ReviewAction[]> = {
  '待審核': ['approve', 'reject'],
  '已核准': ['mark_paid'],
  '已拒絕': ['resubmit'],
  '已付款': [],
}

const ACTION_LOG_COLOR: Record<string, string> = {
  approve:   'green',
  reject:    'red',
  mark_paid: 'blue',
  resubmit:  'orange',
}

const fmtMoney = (n: number) =>
  n == null ? '-' : `$${n.toLocaleString('zh-TW')}`

const fmtDate = (d: string) => (d ? d.slice(0, 10) : '-')

// ═════════════════════════════════════════════════════════════════════════════
// 主元件
// ═════════════════════════════════════════════════════════════════════════════

export default function ClaimsPage() {
  const [items, setItems] = useState<ClaimRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({ page: 1, size: 20, total: 0 })

  // 篩選
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [contractSearch, setContractSearch] = useState('')

  // 新增 Modal
  const [addOpen, setAddOpen] = useState(false)
  const [addLoading, setAddLoading] = useState(false)
  const [addForm] = Form.useForm()

  // 編輯 Modal
  const [editOpen, setEditOpen] = useState(false)
  const [editLoading, setEditLoading] = useState(false)
  const [editRecord, setEditRecord] = useState<ClaimRecord | null>(null)
  const [editForm] = Form.useForm()

  // Drawer
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedClaim, setSelectedClaim] = useState<ClaimRecord | null>(null)
  // 附件
  const [attachments, setAttachments] = useState<ClaimAttachment[]>([])
  const [attachLoading, setAttachLoading] = useState(false)
  const [uploadingAttach, setUploadingAttach] = useState(false)

  const loadAttachments = useCallback(async (claimId: number) => {
    setAttachLoading(true)
    try {
      const list = await fetchClaimAttachments(claimId)
      setAttachments(list)
    } catch {
      setAttachments([])
    } finally {
      setAttachLoading(false)
    }
  }, [])

  const handleDeleteAttachment = async (id: number) => {
    try {
      await deleteClaimAttachment(id)
      setAttachments(prev => prev.filter(a => a.id !== id))
      message.success('附件已刪除')
    } catch {
      message.error('刪除失敗')
    }
  }

  // 審核 Modal
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewTarget, setReviewTarget] = useState<{ record: ClaimRecord; action: ReviewAction } | null>(null)
  const [reviewComment, setReviewComment] = useState('')

  // 批次審核
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [batchLoading, setBatchLoading] = useState(false)
  const [batchModalOpen, setBatchModalOpen] = useState(false)
  const [batchAction, setBatchAction] = useState<'approve' | 'reject'>('approve')
  const [batchComment, setBatchComment] = useState('')

  const handleBatchReview = useCallback(async () => {
    if (selectedRowKeys.length === 0) return
    setBatchLoading(true)
    try {
      const result = await batchReviewClaims(
        selectedRowKeys as number[],
        batchAction,
        batchComment || undefined,
      )
      message.success(
        `批次${batchAction === 'approve' ? '核准' : '拒絕'}完成：成功 ${result.success_count} 筆` +
        (result.skipped_count > 0 ? `，略過 ${result.skipped_count} 筆（狀態不符）` : '')
      )
      setSelectedRowKeys([])
      setBatchModalOpen(false)
      setBatchComment('')
      load(pagination.page, pagination.size)
    } catch {
      message.error('批次審核失敗，請稍後再試')
    } finally {
      setBatchLoading(false)
    }
  }, [selectedRowKeys, batchAction, batchComment, pagination])

  // 合約搜尋下拉（新增 Modal 用）
  const [contractOptions, setContractOptions] = useState<{ value: string; label: string }[]>([])
  const [contractSearchLoading, setContractSearchLoading] = useState(false)

  const handleContractSearch = useCallback(async (keyword: string) => {
    if (!keyword || keyword.length < 1) { setContractOptions([]); return }
    setContractSearchLoading(true)
    try {
      const resp = await fetchContracts({ search: keyword, size: 30 })
      setContractOptions(
        (resp.items ?? []).map((c: any) => ({
          value: c.contract_id,
          label: `${c.contract_id}　${c.contract_name ?? ''}`.trim(),
        }))
      )
    } catch { /* 靜默 */ } finally {
      setContractSearchLoading(false)
    }
  }, [])

  // ── 載入資料 ────────────────────────────────────────────────────────────────
  const load = useCallback(async (page: number, size: number) => {
    setLoading(true)
    try {
      const params: Record<string, any> = { page, size }
      if (statusFilter)    params.status      = statusFilter
      if (contractSearch)  params.contract_id = contractSearch
      const resp = await fetchClaims(params)
      setItems(resp.items)
      setPagination({ page, size, total: resp.total })
    } catch (err: any) {
      message.error(err?.message || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, contractSearch])

  useEffect(() => { load(1, pagination.size) }, [statusFilter, contractSearch])

  const handleTableChange: TableProps<ClaimRecord>['onChange'] = (pag) => {
    load(pag.current ?? 1, pag.pageSize ?? 20)
  }

  // ── 新增 ────────────────────────────────────────────────────────────────────
  const handleAddOk = async () => {
    try {
      const values = await addForm.validateFields()
      setAddLoading(true)
      const payload: ClaimCreate = {
        ...values,
        claim_date: values.claim_date?.format('YYYY-MM-DD'),
        amount: Number(values.amount),
      }
      await createClaim(payload)
      message.success('請款記錄已新增')
      setAddOpen(false)
      addForm.resetFields()
      load(1, pagination.size)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.response?.data?.detail ?? err?.message ?? '新增失敗')
    } finally {
      setAddLoading(false)
    }
  }

  // ── 編輯 ────────────────────────────────────────────────────────────────────
  const openEdit = (record: ClaimRecord) => {
    setEditRecord(record)
    editForm.setFieldsValue({
      claim_type:  record.claim_type,
      claim_date:  record.claim_date ? dayjs(record.claim_date) : null,
      invoice_no:  record.invoice_no,
      amount:      record.amount,
      status:      record.status,
      approver:    record.approver,
      remarks:     record.remarks,
    })
    setEditOpen(true)
  }

  const handleEditOk = async () => {
    if (!editRecord) return
    try {
      const values = await editForm.validateFields()
      setEditLoading(true)
      await updateClaim(editRecord.id, {
        ...values,
        claim_date: values.claim_date?.format('YYYY-MM-DD'),
      })
      message.success('已更新')
      setEditOpen(false)
      setEditRecord(null)
      load(pagination.page, pagination.size)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.response?.data?.detail ?? err?.message ?? '更新失敗')
    } finally {
      setEditLoading(false)
    }
  }

  // ── 刪除 ────────────────────────────────────────────────────────────────────
  const handleDelete = async (id: number) => {
    try {
      await deleteClaim(id)
      message.success('已刪除')
      load(pagination.page, pagination.size)
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? err?.message ?? '刪除失敗')
    }
  }

  // ── 審核操作 ────────────────────────────────────────────────────────────────
  const openReview = (record: ClaimRecord, action: ReviewAction) => {
    setReviewTarget({ record, action })
    setReviewComment('')
    setReviewOpen(true)
  }

  const handleReview = async () => {
    if (!reviewTarget) return
    setReviewLoading(true)
    try {
      await reviewClaim(reviewTarget.record.id, reviewTarget.action, reviewComment || undefined)
      message.success(`${REVIEW_ACTIONS[reviewTarget.action].label}成功`)
      setReviewOpen(false)
      // 若 Drawer 開著，更新 selectedClaim
      if (selectedClaim?.id === reviewTarget.record.id) setDrawerOpen(false)
      load(pagination.page, pagination.size)
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? '操作失敗')
    } finally {
      setReviewLoading(false)
    }
  }

  // ── 逾期判斷（待審核 > 7 天） ──────────────────────────────────────────────
  const isOverdue = (record: ClaimRecord) =>
    record.status === '待審核' &&
    dayjs().diff(dayjs(record.created_at), 'day') >= 7

  // ── 表格欄位 ────────────────────────────────────────────────────────────────
  const columns: ColumnsType<ClaimRecord> = [
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (s: string, record: ClaimRecord) => (
        <Space size={4}>
          <Tag color={STATUS_COLOR[s] ?? 'default'}>{s}</Tag>
          {isOverdue(record) && (
            <Tooltip title={`待審核已超過 ${dayjs().diff(dayjs(record.created_at), 'day')} 天`}>
              <WarningOutlined style={{ color: '#faad14', fontSize: 14 }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '類型',
      dataIndex: 'claim_type',
      key: 'claim_type',
      width: 80,
    },
    {
      title: '請款日期',
      dataIndex: 'claim_date',
      key: 'claim_date',
      width: 110,
      render: fmtDate,
      sorter: true,
    },
    {
      title: '合約編號',
      dataIndex: 'contract_id',
      key: 'contract_id',
      width: 130,
      ellipsis: true,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</span>,
    },
    {
      title: '合約名稱',
      dataIndex: 'contract_name',
      key: 'contract_name',
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '發票號碼',
      dataIndex: 'invoice_no',
      key: 'invoice_no',
      width: 130,
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      width: 130,
      align: 'right' as const,
      render: (v: number) => <span style={{ color: '#722ED1', fontWeight: 600 }}>{fmtMoney(v)}</span>,
    },
    {
      title: '核准人',
      dataIndex: 'approver',
      key: 'approver',
      width: 90,
      render: (v: string) => v || '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_, record) => {
        const actions = STATUS_ACTIONS[record.status] ?? []
        return (
          <Space size={4} onClick={(e) => e.stopPropagation()}>
            {actions.map((action) => {
              const cfg = REVIEW_ACTIONS[action]
              return (
                <Tooltip key={action} title={cfg.label}>
                  <Button
                    size="small"
                    type={cfg.btnType}
                    danger={action === 'reject'}
                    icon={cfg.icon}
                    onClick={() => openReview(record, action)}
                  >
                    {cfg.label}
                  </Button>
                </Tooltip>
              )
            })}
            <Tooltip title="編輯">
              <Button type="text" size="small" icon={<EditOutlined />}
                onClick={() => openEdit(record)} />
            </Tooltip>
            <Popconfirm
              title="確認刪除" description="確定要刪除此筆請款記錄嗎？"
              onConfirm={() => handleDelete(record.id)}
              okText="刪除" okButtonProps={{ danger: true }} cancelText="取消"
            >
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        )
      },
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 麵包屑 */}
      <Breadcrumb style={{ marginBottom: '16px' }}>
        <Breadcrumb.Item><HomeOutlined /> 首頁</Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_GROUP.contract}</Breadcrumb.Item>
        <Breadcrumb.Item>{NAV_PAGE.contractClaims}</Breadcrumb.Item>
      </Breadcrumb>

      <Title level={4} style={{ marginBottom: 16 }}>{NAV_PAGE.contractClaims}</Title>

      {/* 工具列 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col>
            <Input
              prefix={<SearchOutlined />}
              placeholder="合約編號 / 合約名稱"
              allowClear
              style={{ width: 200 }}
              value={contractSearch}
              onChange={(e) => setContractSearch(e.target.value)}
            />
          </Col>
          <Col>
            <Select
              placeholder="篩選狀態"
              allowClear
              style={{ width: 130 }}
              value={statusFilter}
              onChange={setStatusFilter}
            >
              {STATUS_OPTIONS.map(s => <Option key={s} value={s}>{s}</Option>)}
            </Select>
          </Col>
          <Col style={{ marginLeft: 'auto' }}>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={() => load(1, pagination.size)} loading={loading}>
                重新整理
              </Button>
              <Button
                icon={<DownloadOutlined />}
                onClick={() => exportClaimsExcel({
                  contract_id: contractSearch || undefined,
                  status: statusFilter,
                })}
              >
                匯出 Excel
              </Button>
              <Button
                type="primary" icon={<PlusOutlined />}
                onClick={() => { setAddOpen(true); addForm.resetFields() }}
              >
                新增請款
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 批次操作 Bar */}
      {selectedRowKeys.length > 0 && (
        <Alert
          style={{ marginBottom: 12 }}
          type="info"
          message={
            <Space>
              <span>已選取 <strong>{selectedRowKeys.length}</strong> 筆</span>
              <Button
                size="small" type="primary" icon={<CheckOutlined />}
                onClick={() => { setBatchAction('approve'); setBatchComment(''); setBatchModalOpen(true) }}
              >批次核准</Button>
              <Button
                size="small" danger icon={<CloseOutlined />}
                onClick={() => { setBatchAction('reject'); setBatchComment(''); setBatchModalOpen(true) }}
              >批次拒絕</Button>
              <Button size="small" onClick={() => setSelectedRowKeys([])}>取消選取</Button>
            </Space>
          }
        />
      )}

      {/* 表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={items}
          loading={loading}
          rowSelection={{
            selectedRowKeys,
            onChange: setSelectedRowKeys,
            getCheckboxProps: (record) => ({
              disabled: !['待審核'].includes(record.status),
            }),
          }}
          rowKey="id"
          pagination={{
            current: pagination.page,
            pageSize: pagination.size,
            total: pagination.total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 筆`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 900 }}
          rowClassName={(record) => isOverdue(record) ? 'row-overdue' : ''}
          onRow={(record) => ({
            onClick: () => {
              setSelectedClaim(record)
              setDrawerOpen(true)
              setAttachments([])
              loadAttachments(record.id)
            },
            style: { cursor: 'pointer' },
          })}
        />
      </Card>

      {/* 詳情 Drawer */}
      {selectedClaim && (
        <Drawer
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Tag color={STATUS_COLOR[selectedClaim.status] ?? 'default'}>{selectedClaim.status}</Tag>
              <span style={{ fontWeight: 600 }}>請款：#{selectedClaim.id}</span>
              <span style={{ color: '#595959' }}>（{selectedClaim.contract_id}）</span>
              {selectedClaim.contract_name && (
                <span style={{ color: '#595959', fontSize: 12 }}>　{selectedClaim.contract_name}</span>
              )}
            </div>
          }
          placement="right"
          width={480}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          bodyStyle={{ paddingBottom: 80 }}
        >
          <Descriptions column={1} bordered size="small" style={{ marginBottom: 20 }}>
            <Descriptions.Item label="類型">{selectedClaim.claim_type}</Descriptions.Item>
            <Descriptions.Item label="請款日期">{fmtDate(selectedClaim.claim_date)}</Descriptions.Item>
            <Descriptions.Item label="合約編號">{selectedClaim.contract_id}</Descriptions.Item>
            <Descriptions.Item label="合約名稱">{selectedClaim.contract_name || '—'}</Descriptions.Item>
            <Descriptions.Item label="發票號碼">{selectedClaim.invoice_no || '—'}</Descriptions.Item>
            <Descriptions.Item label="金額">
              <strong style={{ color: '#722ED1', fontSize: 15 }}>{fmtMoney(selectedClaim.amount)}</strong>
            </Descriptions.Item>
            <Descriptions.Item label="狀態">
              <Tag color={STATUS_COLOR[selectedClaim.status] ?? 'default'}>{selectedClaim.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="核准人">{selectedClaim.approver || '—'}</Descriptions.Item>
            <Descriptions.Item label="備註">{selectedClaim.remarks || '—'}</Descriptions.Item>
            <Descriptions.Item label="建立時間">{selectedClaim.created_at?.slice(0, 16) || '—'}</Descriptions.Item>
            <Descriptions.Item label="更新時間">{selectedClaim.updated_at?.slice(0, 16) || '—'}</Descriptions.Item>
          </Descriptions>

          {/* 審核時間軸 */}
          <div style={{ marginBottom: 8 }}>
            <Text strong><HistoryOutlined style={{ marginRight: 6 }} />審核軌跡</Text>
          </div>
          {(() => {
            const logs: ClaimReviewLogEntry[] = (() => {
              try { return JSON.parse(selectedClaim.review_log || '[]') } catch { return [] }
            })()
            if (!logs.length) {
              return <Text type="secondary" style={{ fontSize: 13 }}>尚無審核記錄</Text>
            }
            return (
              <Timeline
                items={logs.map((log) => ({
                  color: ACTION_LOG_COLOR[log.action] ?? 'gray',
                  children: (
                    <div style={{ fontSize: 13 }}>
                      <div>
                        <Tag color={ACTION_LOG_COLOR[log.action] ?? 'default'} style={{ marginBottom: 2 }}>
                          {REVIEW_ACTIONS[log.action as ReviewAction]?.label ?? log.action}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {log.from_status} → {log.to_status}
                        </Text>
                      </div>
                      <div style={{ color: '#595959' }}>
                        {log.actor}　{log.timestamp.replace('T', ' ')}
                      </div>
                      {log.comment && <div style={{ color: '#262626', marginTop: 2 }}>{log.comment}</div>}
                    </div>
                  ),
                }))}
              />
            )
          })()}

          {/* ── 附件區塊 ──────────────────────────────────────────── */}
          <Divider style={{ margin: '16px 0 12px' }} />
          <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Text strong><PaperClipOutlined style={{ marginRight: 4 }} />附件</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>（PDF / JPG / PNG / WEBP，單檔最大 20MB）</Text>
          </div>

          {/* 上傳區 */}
          <Upload.Dragger
            multiple={false}
            showUploadList={false}
            accept=".pdf,.jpg,.jpeg,.png,.webp"
            beforeUpload={async (file) => {
              if (!selectedClaim) return false
              setUploadingAttach(true)
              try {
                const att = await uploadClaimAttachment(selectedClaim.id, file)
                setAttachments(prev => [...prev, att])
                message.success(`${file.name} 上傳成功`)
              } catch {
                message.error('上傳失敗，請確認檔案格式與大小')
              } finally {
                setUploadingAttach(false)
              }
              return false  // 阻止 antd 內建上傳
            }}
            disabled={uploadingAttach}
            style={{ marginBottom: 12 }}
          >
            <p className="ant-upload-drag-icon">
              {uploadingAttach ? <Spin /> : <InboxOutlined />}
            </p>
            <p className="ant-upload-text" style={{ fontSize: 13 }}>
              {uploadingAttach ? '上傳中…' : '點擊或拖曳檔案到此處上傳'}
            </p>
          </Upload.Dragger>

          {/* 附件列表 */}
          <Spin spinning={attachLoading}>
            {attachments.length === 0 && !attachLoading && (
              <Text type="secondary" style={{ fontSize: 13 }}>尚未上傳任何附件</Text>
            )}
            <Image.PreviewGroup>
              {attachments.map(att => {
                const isImage = att.content_type.startsWith('image/')
                const isPdf   = att.content_type === 'application/pdf'
                const url     = getAttachmentUrl(att.download_url)
                return (
                  <div
                    key={att.id}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '6px 8px', borderRadius: 6,
                      background: '#fafafa', border: '1px solid #f0f0f0',
                      marginBottom: 6,
                    }}
                  >
                    {isImage ? (
                      <Image
                        width={36} height={36}
                        src={url}
                        style={{ objectFit: 'cover', borderRadius: 4 }}
                        preview={{ src: url }}
                      />
                    ) : (
                      <FilePdfOutlined style={{ fontSize: 28, color: '#f5222d' }} />
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: '#1B3A5C', fontSize: 13, fontWeight: 500 }}
                        title={att.original_filename}
                      >
                        {att.original_filename}
                      </a>
                      <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                        {(att.file_size / 1024).toFixed(0)} KB　{att.uploader}　{att.created_at.slice(0, 16)}
                      </div>
                    </div>
                    <Popconfirm
                      title="確認刪除此附件？"
                      onConfirm={() => handleDeleteAttachment(att.id)}
                      okText="刪除"
                      cancelText="取消"
                      okType="danger"
                    >
                      <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </div>
                )
              })}
            </Image.PreviewGroup>
          </Spin>
        </Drawer>
      )}

      {/* 審核 Modal */}
      <Modal
        title={
          reviewTarget ? (
            <span>
              {REVIEW_ACTIONS[reviewTarget.action].icon}
              <span style={{ marginLeft: 8 }}>
                {REVIEW_ACTIONS[reviewTarget.action].label}請款 #{reviewTarget.record.id}
              </span>
            </span>
          ) : '審核'
        }
        open={reviewOpen}
        onOk={handleReview}
        onCancel={() => setReviewOpen(false)}
        confirmLoading={reviewLoading}
        okText={reviewTarget ? REVIEW_ACTIONS[reviewTarget.action].label : '確認'}
        cancelText="取消"
        okButtonProps={{
          danger: reviewTarget?.action === 'reject',
          style: reviewTarget ? { backgroundColor: reviewTarget.action !== 'reject' ? REVIEW_ACTIONS[reviewTarget.action].color : undefined } : {},
        }}
        width={440}
      >
        {reviewTarget && (
          <div style={{ padding: '8px 0' }}>
            <p style={{ marginBottom: 12, color: '#595959' }}>
              合約：<strong>{reviewTarget.record.contract_name || reviewTarget.record.contract_id}</strong>
              　金額：<strong style={{ color: '#722ED1' }}>{fmtMoney(reviewTarget.record.amount)}</strong>
            </p>
            {(REVIEW_ACTIONS[reviewTarget.action].needComment || reviewTarget.action !== 'mark_paid') && (
              <div>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
                  意見{reviewTarget.action === 'reject' ? '（必填）' : '（選填）'}
                </label>
                <Input.TextArea
                  rows={3}
                  placeholder={reviewTarget.action === 'reject' ? '請說明拒絕原因' : '可填入備注說明'}
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                />
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* 新增 Modal */}
      <Modal
        title="新增請款記錄"
        open={addOpen}
        onOk={handleAddOk}
        onCancel={() => setAddOpen(false)}
        confirmLoading={addLoading}
        okText="確認新增"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        <Form form={addForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="contract_id" label="合約編號" rules={[{ required: true, message: '必填' }]}>
                <Select
                  showSearch
                  allowClear
                placeholder="輸入編號或名稱搜尋"
                  filterOption={false}
                  loading={contractSearchLoading}
                  options={contractOptions}
                  onSearch={handleContractSearch}
                  notFoundContent={contractSearchLoading ? '搜尋中…' : '無符合合約'}
                  onClear={() => setContractOptions([])}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="claim_type" label="類型" initialValue="請款">
                <Select>
                  {CLAIM_TYPE_OPTIONS.map(t => <Option key={t} value={t}>{t}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="claim_date" label="請款日期" rules={[{ required: true, message: '必填' }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="invoice_no" label="發票號碼">
                <Input placeholder="選填" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="amount" label="金額" rules={[{ required: true, message: '必填' }]}>
                <InputNumber
                  style={{ width: '100%' }} min={0} step={1000}
                  formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={v => (v?.replace(/\$\s?|(,*)/g, '') ?? '') as any}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="狀態" initialValue="待審核">
                <Select>
                  {STATUS_OPTIONS.map(s => <Option key={s} value={s}>{s}</Option>)}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="approver" label="核准人">
                <Input placeholder="選填" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="remarks" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 編輯 Modal */}
      <Modal
        title="編輯請款記錄"
        open={editOpen}
        onOk={handleEditOk}
        onCancel={() => { setEditOpen(false); setEditRecord(null) }}
        confirmLoading={editLoading}
        okText="確認更新"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="claim_type" label="類型">
                <Select>
                  {CLAIM_TYPE_OPTIONS.map(t => <Option key={t} value={t}>{t}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="claim_date" label="請款日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="invoice_no" label="發票號碼">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="amount" label="金額">
                <InputNumber
                  style={{ width: '100%' }} min={0} step={1000}
                  formatter={v => `$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={v => (v?.replace(/\$\s?|(,*)/g, '') ?? '') as any}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="status" label="狀態">
                <Select>
                  {STATUS_OPTIONS.map(s => <Option key={s} value={s}>{s}</Option>)}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="approver" label="核准人">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="remarks" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 批次審核 Modal */}
      <Modal
        title={batchAction === 'approve' ? `批次核准（${selectedRowKeys.length} 筆）` : `批次拒絕（${selectedRowKeys.length} 筆）`}
        open={batchModalOpen}
        onOk={handleBatchReview}
        onCancel={() => setBatchModalOpen(false)}
        confirmLoading={batchLoading}
        okText={batchAction === 'approve' ? '確認核准' : '確認拒絕'}
        okButtonProps={{ danger: batchAction === 'reject' }}
        cancelText="取消"
        destroyOnClose
      >
        <p style={{ color: '#595959', marginBottom: 12 }}>
          僅「待審核」狀態的請款才能被批次審核，其他狀態將略過。</p>
        <Input.TextArea
          placeholder="審核意見（選填）"
          rows={4}
          value={batchComment}
          onChange={e => setBatchComment(e.target.value)}
        />
      </Modal>
    </div>
  )
}
