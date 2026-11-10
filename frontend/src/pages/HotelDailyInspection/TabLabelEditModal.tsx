/**
 * 飯店每日巡檢 — 編輯頁籤名稱 Modal（2026-11-10）
 *
 * Samuel 裁示：頁籤名稱開放在頁面上直接修改（權限 hotel_daily_inspection_tab_label_edit，需明確指派），
 * 改過的名稱套用到整個頁面。欄位留空＝回到預設名稱（Ragic 表單名稱）。
 */
import { useState } from 'react'
import { Form, Input, Modal, Typography } from 'antd'

const { Text } = Typography

export interface TabLabelEditModalProps {
  open:     boolean
  order:    string[]
  labels:   Record<string, string>
  defaults: Record<string, string>
  onCancel: () => void
  onSave:   (labels: Record<string, string | null>) => Promise<void>
}

export default function TabLabelEditModal({ open, order, labels, defaults, onCancel, onSave }: TabLabelEditModalProps) {
  const [form] = Form.useForm<Record<string, string>>()
  const [saving, setSaving] = useState(false)

  // destroyOnClose：每次開啟重新掛載，initialValues 即為目前名稱（與預設相同的顯示為空白）
  const initialValues = Object.fromEntries(order.map((k) => [k, labels[k] === defaults[k] ? '' : labels[k]]))

  const handleOk = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      await onSave(Object.fromEntries(order.map((k) => [k, (values[k] ?? '').trim() || null])))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title="編輯頁籤名稱"
      okText="儲存"
      cancelText="取消"
      confirmLoading={saving}
      onOk={handleOk}
      onCancel={onCancel}
      destroyOnClose
    >
      <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>
        留空＝使用預設名稱。儲存後頁籤、Dashboard 卡片、月曆格、每日巡檢表一起更新，所有使用者都會看到。
      </Text>
      <Form form={form} layout="vertical" preserve={false} initialValues={initialValues}>
        {order.map((k) => (
          <Form.Item
            key={k}
            name={k}
            label={<span>預設：<Text type="secondary">{defaults[k]}</Text></span>}
            rules={[{ max: 100, message: '最多 100 字' }]}
            style={{ marginBottom: 10 }}
          >
            <Input placeholder={defaults[k]} allowClear maxLength={100} />
          </Form.Item>
        ))}
      </Form>
    </Modal>
  )
}
