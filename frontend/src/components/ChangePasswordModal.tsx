import { useState } from 'react'
import { Alert, Form, Input, Modal, message } from 'antd'
import { authApi } from '@/api/auth'

interface ChangePasswordModalProps {
  open: boolean
  /** 強制模式（must_change_password=True）：不可關閉、免填舊密碼；完成後由 onDone 處理（通常為登出） */
  forced?: boolean
  onClose?: () => void
  onDone?: () => void
}

/** 修改密碼共用 Modal，桌面版與手機版共用（2026-11-13） */
export default function ChangePasswordModal({ open, forced = false, onClose, onDone }: ChangePasswordModalProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      if (values.new_password !== values.confirm_password) {
        setError('兩次輸入的新密碼不一致')
        return
      }
      setLoading(true)
      setError(null)
      if (forced) {
        await authApi.changePasswordForced(values.new_password)
      } else {
        await authApi.changePassword(values.old_password, values.new_password)
        message.success('密碼已更新')
      }
      form.resetFields()
      onDone?.()
    } catch (err: any) {
      if (err?.errorFields) return
      setError(err?.response?.data?.detail || err?.message || '更新失敗，請稍後再試')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    form.resetFields()
    setError(null)
    onClose?.()
  }

  return (
    <Modal
      title={forced ? '請設定新密碼' : '修改密碼'}
      open={open}
      closable={!forced}
      maskClosable={!forced}
      keyboard={!forced}
      onOk={handleOk}
      onCancel={handleCancel}
      okText={forced ? '確認更新密碼' : '確認修改'}
      cancelText="取消"
      cancelButtonProps={forced ? { style: { display: 'none' } } : undefined}
      confirmLoading={loading}
      destroyOnClose
      centered
      width={420}
    >
      {forced && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="您使用預設或一次性密碼登入，必須先設定新密碼才能繼續使用系統。"
        />
      )}
      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}
      <Form form={form} layout="vertical" requiredMark={false}>
        {!forced && (
          <Form.Item name="old_password" label="舊密碼" rules={[{ required: true, message: '請輸入舊密碼' }]}>
            <Input.Password />
          </Form.Item>
        )}
        <Form.Item
          name="new_password"
          label="新密碼"
          rules={[{ required: true, message: '請輸入新密碼' }, { min: 8, message: '至少 8 個字元' }]}
        >
          <Input.Password placeholder="至少 8 個字元" />
        </Form.Item>
        <Form.Item name="confirm_password" label="確認新密碼" rules={[{ required: true, message: '請再次輸入新密碼' }]}>
          <Input.Password />
        </Form.Item>
      </Form>
    </Modal>
  )
}
