/**
 * 新增簽核單頁
 * 路由：/approvals/new
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button, Card, Form, Input, Radio, Space, Tag, Typography, Upload, message,
  List, Avatar, AutoComplete,
} from 'antd'
import {
  ArrowLeftOutlined, DeleteOutlined, PlusOutlined, UploadOutlined, UserOutlined,
} from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import { createApprovalWithFiles, fetchApprovers } from '@/api/approvals'
import { useAuthStore } from '@/stores/authStore'
import type { ApproverIn, ApproverOption } from '@/types/approval'
import RichTextEditor from '@/components/Editor/RichTextEditor'

const { Title, Text } = Typography

export default function ApprovalNewPage() {
  const navigate  = useNavigate()
  const [form]    = Form.useForm()
  const user      = useAuthStore((s) => s.user)
  const [submitting, setSubmitting] = useState(false)

  // 富文字內容（說明 / 機敏資訊）
  const [description,  setDescription]  = useState('')
  const [confidential, setConfidential] = useState('')

  // 串簽人員清單
  const [chain, setChain]           = useState<ApproverIn[]>([])

  // 人員搜尋
  const [approverOpts, setApproverOpts] = useState<ApproverOption[]>([])
  const [searchVal, setSearchVal]   = useState('')
  const [selectedAppr, setSelectedAppr] = useState<ApproverOption | null>(null)

  // 附件
  const [fileList, setFileList]     = useState<UploadFile[]>([])

  // 載入人員選項
  useEffect(() => {
    const t = setTimeout(async () => {
      const res = await fetchApprovers(searchVal)
      setApproverOpts(res)
    }, 300)
    return () => clearTimeout(t)
  }, [searchVal])

  const addApprover = () => {
    if (!selectedAppr) { message.warning('請先選擇人員'); return }
    if (chain.some((c) => c.user_id === selectedAppr.user_id)) {
      message.warning('已在清單中')
      return
    }
    setChain((prev) => [...prev, { ...selectedAppr }])
    setSelectedAppr(null)
    setSearchVal('')
  }

  const removeApprover = (idx: number) => {
    setChain((prev) => prev.filter((_, i) => i !== idx))
  }

  const onFinish = async (vals: Record<string, unknown>) => {
    if (chain.length === 0) { message.error('至少需要一位簽核人員'); return }
    setSubmitting(true)
    try {
      const files = fileList.map((f) => f.originFileObj as File).filter(Boolean)
      const payload = {
        subject:        vals.subject as string,
        description,
        confidential,
        requester_dept: vals.requester_dept as string ?? '',
        view_scope:     vals.view_scope as 'org' | 'restricted' | 'top_secret',
        publish_memo:   vals.publish_memo ? 1 : 0,
        approver_chain: chain,
      }
      const created = await createApprovalWithFiles(payload, files)
      message.success('簽核單已送出')
      navigate(`/approvals/${created.id}`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      message.error(e?.response?.data?.detail ?? '送出失敗')
    } finally {
      setSubmitting(false)
    }
  }

  const scopeOptions = [
    { value: 'restricted',  label: '僅相關人員可見（Admin / 申請人 / 簽核人）' },
    { value: 'org',         label: '全公司可見' },
    { value: 'top_secret',  label: '🔴 極機密' },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: '0 auto' }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/approvals/list')}>
          返回清單
        </Button>
        <Title level={4} style={{ margin: 0 }}>📝 新增簽核單</Title>
      </Space>

      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{
          view_scope: 'restricted',
          publish_memo: false,
          requester: user?.full_name ?? '',
        }}
      >
        <Card style={{ marginBottom: 16 }}>
          <Form.Item label="申請人" name="requester">
            <Input disabled />
          </Form.Item>

          <Form.Item label="申請人部門" name="requester_dept">
            <Input placeholder="（選填）" />
          </Form.Item>

          <Form.Item
            label="主旨"
            name="subject"
            rules={[{ required: true, message: '請輸入主旨' }]}
          >
            <Input placeholder="請輸入主旨" />
          </Form.Item>

          <Form.Item label="可見範圍" name="view_scope">
            <Radio.Group>
              {scopeOptions.map((o) => (
                <Radio key={o.value} value={o.value}>{o.label}</Radio>
              ))}
            </Radio.Group>
          </Form.Item>

          {/* 說明 — 富文字編輯器 */}
          <Form.Item label="說明（圖文並茂）">
            <RichTextEditor
              value={description}
              onChange={setDescription}
              placeholder="請輸入說明內容，可插入圖片…"
              minHeight={240}
            />
          </Form.Item>

          {/* 機敏資訊 — 富文字編輯器 */}
          <Form.Item label="機敏資訊（Confidential）">
            <RichTextEditor
              value={confidential}
              onChange={setConfidential}
              placeholder="請輸入成本、報價等敏感資訊（僅有權限者可見）"
              minHeight={160}
            />
          </Form.Item>

          <Form.Item label="簽核完成後自動建立 Memo 公告" name="publish_memo" valuePropName="checked">
            <input type="checkbox" /> 開啟後，全部核准時同步到公告
          </Form.Item>
        </Card>

        {/* 串簽設定 */}
        <Card title="🔗 簽核關卡設定" style={{ marginBottom: 16 }}>
          <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
            <AutoComplete
              style={{ flex: 1 }}
              value={searchVal}
              onSearch={setSearchVal}
              onChange={setSearchVal}
              placeholder="搜尋人員（姓名 / Email）"
              options={approverOpts.map((o) => ({
                value: o.name,
                label: (
                  <Space>
                    <UserOutlined />
                    <span>{o.name}</span>
                    <Text type="secondary" style={{ fontSize: 12 }}>{o.email}</Text>
                  </Space>
                ),
                key: o.user_id,
              }))}
              onSelect={(val, opt) => {
                const found = approverOpts.find((o) => o.user_id === opt.key)
                if (found) setSelectedAppr(found)
                setSearchVal(val)
              }}
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={addApprover}>
              加入
            </Button>
          </Space.Compact>

          {chain.length === 0 ? (
            <div style={{ color: '#9ca3af', textAlign: 'center', padding: '16px 0' }}>
              尚未加入任何簽核人員
            </div>
          ) : (
            <List
              size="small"
              bordered
              dataSource={chain}
              renderItem={(item, idx) => (
                <List.Item
                  actions={[
                    <Button
                      key="del"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => removeApprover(idx)}
                    />,
                  ]}
                >
                  <List.Item.Meta
                    avatar={<Avatar size="small" icon={<UserOutlined />} />}
                    title={`第 ${idx + 1} 關：${item.name}`}
                    description={item.email}
                  />
                </List.Item>
              )}
            />
          )}
        </Card>

        {/* 附件 */}
        <Card title="📎 附件" style={{ marginBottom: 16 }}>
          <Upload
            multiple
            beforeUpload={() => false}
            fileList={fileList}
            onChange={({ fileList: fl }) => setFileList(fl)}
          >
            <Button icon={<UploadOutlined />}>選擇檔案</Button>
          </Upload>
        </Card>

        <Space>
          <Button type="primary" htmlType="submit" loading={submitting}>
            送出簽核單
          </Button>
          <Button onClick={() => navigate('/approvals/list')}>取消</Button>
        </Space>
      </Form>
    </div>
  )
}
