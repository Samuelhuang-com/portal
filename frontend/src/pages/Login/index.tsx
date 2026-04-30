/**
 * Login page
 */
import { useState } from 'react'
import { Form, Input, Button, Card, Typography, message, Tag } from 'antd'
import { UserOutlined, LockOutlined, BankOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography

// 環境標示
const ENV_TAG = import.meta.env.PROD
  ? null
  : import.meta.env.MODE === 'staging'
    ? <Tag color="orange" style={{ fontSize: 11, marginLeft: 6 }}>UAT</Tag>
    : <Tag color="blue"   style={{ fontSize: 11, marginLeft: 6 }}>DEV</Tag>

export default function LoginPage() {
  const navigate = useNavigate()
  const { setToken, setUser } = useAuthStore()
  const [submitting, setSubmitting] = useState(false)

  const onFinish = async (values: { identifier: string; password: string }) => {
    setSubmitting(true)
    try {
      // 後端 LoginRequest schema 使用 identifier（email 或 username 皆可）
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          identifier: values.identifier,
          password: values.password,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || '帳號或密碼錯誤，請確認後重試')
      }
      const data = await res.json()
      setToken(data.access_token)
      setUser({
        id:          data.user?.id          || '',
        email:       data.user?.email       || values.identifier,
        name:        data.user?.full_name   || values.identifier,
        full_name:   data.user?.full_name   || values.identifier,
        tenant_id:   data.user?.tenant_id   || '',
        tenant_name: data.user?.tenant_name || '',
        roles:       data.user?.roles       || [],
        permissions: data.user?.permissions || [],
        is_active:   data.user?.is_active   ?? true,
      })
      navigate('/dashboard')
    } catch (err: any) {
      message.error({ content: err.message || '登入失敗，請稍後再試', duration: 4 })
    } finally {
      setSubmitting(false)
    }
  }

  // Dev bypass — 僅 DEV 環境顯示（呼叫真實後端，避免 fake token 造成 API 401）
  const devLogin = () => {
    onFinish({ identifier: 'admin', password: 'admin1234' })
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f0f4f8 0%, #dce6f0 100%)',
      }}
    >
      <Card style={{ width: 400, boxShadow: '0 8px 32px rgba(27,58,92,0.12)', borderRadius: 12 }}>
        {/* ── 集團識別區 ── */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{
            width: 52, height: 52, borderRadius: 12,
            background: 'linear-gradient(135deg, #1B3A5C, #4BA8E8)',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: 12,
          }}>
            <BankOutlined style={{ fontSize: 26, color: '#fff' }} />
          </div>
          <div>
            <Title level={3} style={{ margin: 0, color: '#1B3A5C' }}>
              集團管理 Portal{ENV_TAG}
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              維春集團內部作業與管理平台
            </Text>
          </div>
        </div>

        {/* ── 登入表單 ── */}
        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="identifier"
            rules={[{ required: true, message: '請輸入帳號或 Email' }]}
          >
            <Input
              prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="帳號 / Email"
              size="large"
              autoComplete="username"
            />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: '請輸入密碼' }]}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
              placeholder="密碼"
              size="large"
              autoComplete="current-password"
            />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button
              type="primary"
              htmlType="submit"
              size="large"
              block
              loading={submitting}
              style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}
            >
              {submitting ? '登入中…' : '登入'}
            </Button>
          </Form.Item>
        </Form>

        {/* ── 說明文字 ── */}
        <div style={{ textAlign: 'center', marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            如有登入問題，請聯繫系統管理員
          </Text>
        </div>

        {/* ── Dev bypass（僅開發環境顯示）── */}
        {import.meta.env.DEV && (
          <div style={{ marginTop: 16, textAlign: 'center', borderTop: '1px dashed #f0f0f0', paddingTop: 12 }}>
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 6 }}>
              開發用捷徑
            </Text>
            <Button size="small" type="dashed" onClick={devLogin} style={{ fontSize: 11 }}>
              略過認證（Dev only）
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}
