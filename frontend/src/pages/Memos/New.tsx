/**
 * 新增公告頁
 * 路由：/memos/new
 *
 * 功能：
 *  - 富文字編輯器（圖文並茂）
 *  - 附件上傳（建立後再分批 POST /{id}/files）
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button, Card, Form, Input, Radio, Space, Typography, Upload, message, Divider,
} from 'antd'
import { ArrowLeftOutlined, UploadOutlined, PaperClipOutlined } from '@ant-design/icons'
import type { UploadFile } from 'antd/es/upload/interface'
import { createMemo, uploadMemoFiles } from '@/api/memos'
import type { MemoCreatePayload } from '@/types/memo'
import RichTextEditor from '@/components/Editor/RichTextEditor'

const { Title, Text } = Typography

export default function MemoNewPage() {
  const navigate    = useNavigate()
  const [form]      = Form.useForm()
  const [submitting, setSubmitting] = useState(false)

  // 富文字內容（不透過 Form，避免 Quill 與 Ant Form.Item 衝突）
  const [body, setBody] = useState('')

  // 附件清單（不自動上傳，建立公告後再一起送）
  const [fileList, setFileList] = useState<UploadFile[]>([])

  const onFinish = async (vals: Omit<MemoCreatePayload, 'body'>) => {
    setSubmitting(true)
    try {
      // 1. 建立公告（帶入富文字 HTML）
      const created = await createMemo({ ...vals, body })

      // 2. 若有附件，逐一上傳
      if (fileList.length > 0) {
        const files = fileList.map((f) => f.originFileObj as File).filter(Boolean)
        try {
          await uploadMemoFiles(created.id, files)
        } catch {
          message.warning('公告已發布，但部分附件上傳失敗，請至詳情頁重新上傳')
          navigate(`/memos/${created.id}`)
          return
        }
      }

      message.success('公告已發布')
      navigate(`/memos/${created.id}`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      message.error(e?.response?.data?.detail ?? '發布失敗')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 960, margin: '0 auto' }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/memos/list')}>
          返回公告牆
        </Button>
        <Title level={4} style={{ margin: 0 }}>📢 新增公告</Title>
      </Space>

      <Card>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{ visibility: 'org', doc_no: '', recipient: '' }}
        >
          <Form.Item
            label="主旨"
            name="title"
            rules={[{ required: true, message: '請輸入公告主旨' }]}
          >
            <Input placeholder="請輸入公告主旨" />
          </Form.Item>

          <Form.Item label="文號（選填）" name="doc_no">
            <Input placeholder="例：(115)人資字第001號" />
          </Form.Item>

          <Form.Item label="收文者（選填）" name="recipient">
            <Input placeholder="例：全體同仁、各部門主管" />
          </Form.Item>

          <Form.Item label="可見範圍" name="visibility">
            <Radio.Group>
              <Radio value="org">
                <Space>
                  全公司可見
                  <Text type="secondary" style={{ fontSize: 12 }}>（所有登入者均可查看）</Text>
                </Space>
              </Radio>
              <Radio value="restricted">
                <Space>
                  僅自己可見
                  <Text type="secondary" style={{ fontSize: 12 }}>（僅發文者本人可查看）</Text>
                </Space>
              </Radio>
            </Radio.Group>
          </Form.Item>

          {/* 內文 — 富文字編輯器 */}
          <Form.Item label="內文（圖文並茂）">
            <RichTextEditor
              value={body}
              onChange={setBody}
              placeholder="請輸入公告內容，可插入圖片…"
              minHeight={320}
            />
          </Form.Item>

          <Divider orientation="left">
            <Space>
              <PaperClipOutlined />
              附件
            </Space>
          </Divider>

          {/* 附件 — 一般檔案上傳 */}
          <Form.Item
            help="支援任意格式，建立公告後一併上傳（PDF、Word、Excel、圖片…皆可）"
          >
            <Upload
              multiple
              beforeUpload={() => false}
              fileList={fileList}
              onChange={({ fileList: fl }) => setFileList(fl)}
            >
              <Button icon={<UploadOutlined />}>選擇附件</Button>
            </Upload>
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={submitting}>
                發布公告
              </Button>
              <Button onClick={() => navigate('/memos/list')}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
