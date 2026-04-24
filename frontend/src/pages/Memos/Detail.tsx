/**
 * 公告詳情頁
 * 路由：/memos/:id
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  Button, Card, Descriptions, Divider, Form, Input, List, Modal, Popconfirm, Radio, Space,
  Tag, Typography, Upload, message,
} from 'antd'
import {
  ArrowLeftOutlined, DeleteOutlined, EditOutlined, FolderOpenOutlined,
  LinkOutlined, PaperClipOutlined, UploadOutlined, DownloadOutlined, FileOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import dayjs from 'dayjs'
import { deleteMemo, fetchMemo, updateMemo, uploadMemoFiles, memoFileDownloadUrl } from '@/api/memos'
import { downloadFile, openFile } from '@/api/downloadFile'
import { useAuthStore } from '@/stores/authStore'
import type { MemoDetail, MemoFileItem } from '@/types/memo'
import RichTextEditor from '@/components/Editor/RichTextEditor'

const { Title, Text, Paragraph } = Typography

const VISIBILITY_LABEL: Record<string, string> = {
  org:        '全公司可見',
  restricted: '僅相關人員',
}
const VISIBILITY_COLOR: Record<string, string> = {
  org:        'blue',
  restricted: 'orange',
}

/** 將 bytes 格式化為人類可讀字串 */
function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export default function MemoDetailPage() {
  const { id }   = useParams<{ id: string }>()
  const navigate = useNavigate()
  const authUser = useAuthStore((s) => s.user)

  const [detail,  setDetail]  = useState<MemoDetail | null>(null)
  const [loading, setLoading] = useState(true)

  // 編輯 modal
  const [editOpen,  setEditOpen]  = useState(false)
  const [editForm]                = Form.useForm()
  const [editLoading, setEditLoading] = useState(false)
  const [editBody, setEditBody]   = useState('')

  // 補充附件上傳（已建立的公告追加附件）
  const [addFileList, setAddFileList]       = useState<UploadFile[]>([])
  const [uploadingFiles, setUploadingFiles] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const d = await fetchMemo(id)
      setDetail(d)
    } catch {
      message.error('載入失敗或無權限查閱')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  // ── 判斷是否為作者 ────────────────────────────────────────────────────────
  const isAuthor = detail?.author_id === authUser?.id

  // ── 編輯 ─────────────────────────────────────────────────────────────────
  const openEdit = () => {
    if (!detail) return
    editForm.setFieldsValue({
      title:      detail.title,
      doc_no:     detail.doc_no,
      recipient:  detail.recipient,
      visibility: detail.visibility,
    })
    setEditBody(detail.body)
    setEditOpen(true)
  }

  const submitEdit = async () => {
    const vals = await editForm.validateFields()
    setEditLoading(true)
    try {
      await updateMemo(id!, { ...vals, body: editBody })
      message.success('已更新')
      setEditOpen(false)
      load()
    } catch {
      message.error('更新失敗')
    } finally {
      setEditLoading(false)
    }
  }

  // ── 刪除 ─────────────────────────────────────────────────────────────────
  const handleDelete = async () => {
    try {
      await deleteMemo(id!)
      message.success('已刪除')
      navigate('/memos/list')
    } catch {
      message.error('刪除失敗')
    }
  }

  // ── 追加附件 ─────────────────────────────────────────────────────────────
  const handleAddFiles = async () => {
    if (addFileList.length === 0) return
    setUploadingFiles(true)
    try {
      const files = addFileList.map((f) => f.originFileObj as File).filter(Boolean)
      await uploadMemoFiles(id!, files)
      message.success('附件已上傳')
      setAddFileList([])
      load()
    } catch {
      message.error('附件上傳失敗')
    } finally {
      setUploadingFiles(false)
    }
  }

  if (loading) return <div style={{ padding: 24 }}>載入中…</div>
  if (!detail)  return <div style={{ padding: 24 }}>找不到公告或無權限查閱。</div>

  const attachments: MemoFileItem[] = detail.attachments ?? []

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: '0 auto' }}>
      {/* Header */}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/memos/list')}>
          返回公告牆
        </Button>
        {isAuthor && (
          <>
            <Button icon={<EditOutlined />} onClick={openEdit}>編輯</Button>
            <Popconfirm
              title="確定要刪除此公告？"
              onConfirm={handleDelete}
              okText="刪除"
              okButtonProps={{ danger: true }}
            >
              <Button danger icon={<DeleteOutlined />}>刪除</Button>
            </Popconfirm>
          </>
        )}
      </Space>

      <Card>
        {/* Meta 區 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
          <Tag color={VISIBILITY_COLOR[detail.visibility]}>
            {VISIBILITY_LABEL[detail.visibility]}
          </Tag>
          {detail.source === 'approval' && (
            <Tag color="green" icon={<LinkOutlined />}>
              來自簽核
            </Tag>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            {detail.author || '系統'}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {dayjs(detail.created_at).format('YYYY-MM-DD HH:mm')}
          </Text>
        </div>

        {/* 標題 */}
        <Title level={3} style={{ marginBottom: 4 }}>{detail.title}</Title>

        {/* 文號 / 收文者 */}
        {(detail.doc_no || detail.recipient) && (
          <Descriptions size="small" style={{ marginBottom: 12 }} column={2}>
            {detail.doc_no     && <Descriptions.Item label="文號">{detail.doc_no}</Descriptions.Item>}
            {detail.recipient  && <Descriptions.Item label="收文者">{detail.recipient}</Descriptions.Item>}
          </Descriptions>
        )}

        <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
          {/* 若 body 含 HTML tag，直接 render；否則 Paragraph 換行顯示 */}
          {/<[a-z][\s\S]*>/i.test(detail.body) ? (
            <div
              className="ql-editor"
              style={{ lineHeight: 1.8, color: '#111827', padding: 0 }}
              dangerouslySetInnerHTML={{ __html: detail.body }}
            />
          ) : (
            <Paragraph style={{ lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
              {detail.body || '（無內文）'}
            </Paragraph>
          )}
        </div>

        {/* 附件清單 */}
        {(attachments.length > 0 || isAuthor) && (
          <>
            <Divider orientation="left">
              <Space>
                <PaperClipOutlined />
                附件{attachments.length > 0 ? `（${attachments.length}）` : ''}
              </Space>
            </Divider>

            {attachments.length > 0 && (
              <List
                size="small"
                dataSource={attachments}
                renderItem={(f) => (
                  <List.Item
                    actions={[
                      <Button
                        key="open"
                        type="link"
                        size="small"
                        icon={<FolderOpenOutlined />}
                        onClick={() => openFile(memoFileDownloadUrl(id!, f.id), f.orig_name)}
                      >
                        開啟
                      </Button>,
                      <Button
                        key="dl"
                        type="link"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => downloadFile(memoFileDownloadUrl(id!, f.id), f.orig_name)}
                      >
                        下載
                      </Button>,
                    ]}
                  >
                    <Space>
                      <FileOutlined style={{ color: '#6b7280' }} />
                      <Text>{f.orig_name}</Text>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {fmtBytes(f.size_bytes)}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            )}

            {/* 作者可追加附件 */}
            {isAuthor && (
              <div style={{ marginTop: 12 }}>
                <Space wrap>
                  <Upload
                    multiple
                    beforeUpload={() => false}
                    fileList={addFileList}
                    onChange={({ fileList: fl }) => setAddFileList(fl)}
                    showUploadList={{ showPreviewIcon: false }}
                  >
                    <Button size="small" icon={<UploadOutlined />}>選擇附件</Button>
                  </Upload>
                  {addFileList.length > 0 && (
                    <Button
                      size="small"
                      type="primary"
                      loading={uploadingFiles}
                      onClick={handleAddFiles}
                    >
                      上傳 {addFileList.length} 個附件
                    </Button>
                  )}
                </Space>
              </div>
            )}
          </>
        )}

        {/* 來源連結 */}
        {detail.source === 'approval' && detail.source_id && (
          <div style={{ marginTop: 20, fontSize: 12, color: '#9ca3af' }}>
            來源：簽核單{' '}
            <Link to={`/approvals/${detail.source_id}`} style={{ color: '#2563eb' }}>
              #{detail.source_id.slice(0, 8)}…
            </Link>
          </div>
        )}
      </Card>

      {/* 編輯 Modal — 同樣使用富文字編輯器 */}
      <Modal
        title="✏️ 編輯公告"
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={submitEdit}
        okText="儲存"
        confirmLoading={editLoading}
        width={800}
        styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item label="主旨" name="title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="文號" name="doc_no">
            <Input placeholder="（選填）" />
          </Form.Item>
          <Form.Item label="收文者" name="recipient">
            <Input placeholder="（選填）" />
          </Form.Item>
          <Form.Item label="可見範圍" name="visibility">
            <Radio.Group>
              <Radio value="org">全公司可見</Radio>
              <Radio value="restricted">僅自己可見</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="內文">
            <RichTextEditor
              value={editBody}
              onChange={setEditBody}
              placeholder="請輸入公告內容…"
              minHeight={280}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
