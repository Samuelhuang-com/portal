/**
 * 簽核詳情頁
 * 路由：/approvals/:id
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Badge, Button, Card, Col, Descriptions, Divider, Form, Input,
  List, Modal, Row, Space, Steps, Tag, Timeline, Typography, Upload, message,
} from 'antd'
import {
  ArrowLeftOutlined, CheckCircleOutlined, CloseCircleOutlined,
  DownloadOutlined, FolderOpenOutlined, PaperClipOutlined, PlusOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  doApprovalAction, fetchApproval, fileDownloadUrl, removeStep, uploadFiles,
} from '@/api/approvals'
import { downloadFile, openFile } from '@/api/downloadFile'
import type { ApprovalDetail, ApprovalStep } from '@/types/approval'

const { Title, Text, Paragraph } = Typography
const { TextArea } = Input

const STATUS_COLOR: Record<string, string> = {
  pending:  'blue',
  approved: 'green',
  rejected: 'red',
}
const STATUS_LABEL: Record<string, string> = {
  pending:  '待處理',
  approved: '已核准',
  rejected: '已退回',
}
const STEP_STATUS_MAP: Record<string, 'wait' | 'process' | 'finish' | 'error'> = {
  pending:  'process',
  approved: 'finish',
  rejected: 'error',
}

export default function ApprovalDetailPage() {
  const { id }   = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [detail, setDetail] = useState<ApprovalDetail | null>(null)
  const [loading, setLoading] = useState(true)

  // 簽核 modal
  const [actionModal, setActionModal] = useState(false)
  const [actionType,  setActionType]  = useState<'approve' | 'reject'>('approve')
  const [comment,     setComment]     = useState('')
  const [submitting,  setSubmitting]  = useState(false)

  // 附件上傳
  const [uploading, setUploading] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const d = await fetchApproval(id)
      setDetail(d)
    } catch {
      message.error('載入失敗')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  // ── 簽核動作 ──────────────────────────────────────────────────────────────

  const openAction = (type: 'approve' | 'reject') => {
    setActionType(type)
    setComment('')
    setActionModal(true)
  }

  const submitAction = async () => {
    if (!comment.trim()) { message.warning('請填寫意見'); return }
    setSubmitting(true)
    try {
      await doApprovalAction(id!, actionType, comment)
      message.success(actionType === 'approve' ? '已核准' : '已退回')
      setActionModal(false)
      load()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      message.error(e?.response?.data?.detail ?? '操作失敗')
    } finally {
      setSubmitting(false)
    }
  }

  // ── 移除關卡 ──────────────────────────────────────────────────────────────

  const handleRemoveStep = (step: ApprovalStep) => {
    Modal.confirm({
      title: `確定要移除「${step.approver_name}」的簽核關卡？`,
      onOk: async () => {
        try {
          await removeStep(id!, step.id)
          message.success('關卡已移除')
          load()
        } catch {
          message.error('移除失敗')
        }
      },
    })
  }

  // ── 附件上傳 ──────────────────────────────────────────────────────────────

  const handleUpload = async (file: File) => {
    setUploading(true)
    try {
      await uploadFiles(id!, [file])
      message.success('附件上傳成功')
      load()
    } catch {
      message.error('上傳失敗')
    } finally {
      setUploading(false)
    }
    return false   // 阻止 antd 自動上傳
  }

  if (loading) return <div style={{ padding: 24 }}>載入中…</div>
  if (!detail)  return <div style={{ padding: 24 }}>找不到此簽核單或無權限查閱。</div>

  const isClosed  = detail.status !== 'pending'
  const curStepObj = detail.steps.find((s) => s.step_order === detail.current_step)

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/approvals/list')}>
            返回清單
          </Button>
          <Title level={4} style={{ margin: 0 }}>📄 簽核詳情</Title>
        </Space>
        <Tag color={STATUS_COLOR[detail.status]} style={{ fontSize: 14, padding: '4px 12px' }}>
          {STATUS_LABEL[detail.status]}
        </Tag>
      </Row>

      {/* 待簽提示 + 按鈕 */}
      {detail.can_act && (
        <Alert
          type="warning"
          showIcon
          message="這份文件需要您簽核"
          description={`目前輪到您簽核（第 ${(detail.current_step ?? 0) + 1} 關）`}
          style={{ marginBottom: 16 }}
          action={
            <Space>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                onClick={() => openAction('approve')}
              >
                核准
              </Button>
              <Button
                danger
                icon={<CloseCircleOutlined />}
                onClick={() => openAction('reject')}
              >
                退回
              </Button>
            </Space>
          }
        />
      )}

      <Row gutter={16}>
        {/* 主資訊 */}
        <Col xs={24} lg={16}>
          <Card title="基本資訊" style={{ marginBottom: 16 }}>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="主旨" span={2}>{detail.subject}</Descriptions.Item>
              <Descriptions.Item label="申請人">{detail.requester}</Descriptions.Item>
              <Descriptions.Item label="申請部門">{detail.requester_dept || '—'}</Descriptions.Item>
              <Descriptions.Item label="送出時間">
                {dayjs(detail.submitted_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
              <Descriptions.Item label="可見範圍">{detail.view_scope}</Descriptions.Item>
            </Descriptions>

            <Divider orientation="left" plain>說明</Divider>
            <div
              style={{ background: '#f9fafb', borderRadius: 8, padding: 12, minHeight: 60 }}
              dangerouslySetInnerHTML={{ __html: detail.description || '（無說明）' }}
            />

            {detail.confidential && (
              <>
                <Divider orientation="left" plain>🔒 機敏資訊</Divider>
                <Paragraph style={{ background: '#fff7e6', borderRadius: 8, padding: 12 }}>
                  {detail.confidential}
                </Paragraph>
              </>
            )}
          </Card>

          {/* 附件 */}
          <Card
            title="📎 附件"
            style={{ marginBottom: 16 }}
            extra={
              !isClosed && (
                <Upload beforeUpload={handleUpload} showUploadList={false} multiple>
                  <Button size="small" icon={<PlusOutlined />} loading={uploading}>
                    上傳
                  </Button>
                </Upload>
              )
            }
          >
            {detail.attachments.length === 0 ? (
              <Text type="secondary">無附件</Text>
            ) : (
              <List
                size="small"
                dataSource={detail.attachments}
                renderItem={(f) => (
                  <List.Item
                    actions={[
                      <Button
                        key="open"
                        type="link"
                        size="small"
                        icon={<FolderOpenOutlined />}
                        onClick={() => openFile(fileDownloadUrl(detail.id, f.id), f.orig_name)}
                      >
                        開啟
                      </Button>,
                      <Button
                        key="dl"
                        type="link"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => downloadFile(fileDownloadUrl(detail.id, f.id), f.orig_name)}
                      >
                        下載
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={<PaperClipOutlined />}
                      title={f.orig_name}
                      description={`${(f.size_bytes / 1024).toFixed(1)} KB · ${f.uploaded_by} · ${dayjs(f.uploaded_at).format('MM-DD HH:mm')}`}
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>

          {/* 歷程 */}
          <Card title="📜 操作歷程">
            <Timeline
              items={detail.actions.map((a) => ({
                color: a.action === 'reject' ? 'red' : a.action === 'approve' ? 'green' : 'blue',
                children: (
                  <div>
                    <Text strong>{a.actor}</Text>
                    <Tag style={{ marginLeft: 8 }}>{a.action}</Tag>
                    <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                      {dayjs(a.created_at).format('YYYY-MM-DD HH:mm')}
                    </Text>
                    {a.note && <div style={{ color: '#6b7280', marginTop: 4 }}>{a.note}</div>}
                  </div>
                ),
              }))}
            />
          </Card>
        </Col>

        {/* 串簽關卡 */}
        <Col xs={24} lg={8}>
          <Card title="🔗 簽核關卡">
            <Steps
              direction="vertical"
              size="small"
              current={detail.current_step >= 0 ? detail.current_step : detail.steps.length}
              items={detail.steps.map((s) => ({
                title: (
                  <Space>
                    <span>{s.approver_name}</span>
                    {detail.can_manage && s.status === 'pending' && s.step_order !== detail.current_step && (
                      <Button
                        size="small"
                        danger
                        type="text"
                        onClick={() => handleRemoveStep(s)}
                        style={{ fontSize: 11 }}
                      >
                        移除
                      </Button>
                    )}
                  </Space>
                ),
                description: s.status !== 'pending'
                  ? `${STATUS_LABEL[s.status]} · ${dayjs(s.decided_at).format('MM-DD HH:mm')}${s.comment ? ' · ' + s.comment : ''}`
                  : '等待中',
                status: STEP_STATUS_MAP[s.status],
              }))}
            />
          </Card>
        </Col>
      </Row>

      {/* 簽核 Modal */}
      <Modal
        title={actionType === 'approve' ? '✅ 確認核准' : '❌ 確認退回'}
        open={actionModal}
        onCancel={() => setActionModal(false)}
        onOk={submitAction}
        okText={actionType === 'approve' ? '核准' : '退回'}
        okButtonProps={{
          danger: actionType === 'reject',
          loading: submitting,
        }}
      >
        <Form layout="vertical">
          <Form.Item label="簽核意見（必填）" required>
            <TextArea
              rows={4}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="請輸入簽核意見"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
