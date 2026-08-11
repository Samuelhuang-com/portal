/**
 * 系統設定 → 基本設定
 *
 * 目前只有「站台顯示文字」一組：三段各自獨立、整段自由輸入，系統不做任何組字。
 *   站台標題   → 側邊欄左上角 ＋ 瀏覽器分頁標題
 *   登入頁大標 → 登入頁卡片標題
 *   登入頁副標 → 登入頁卡片副標
 *
 * 設定存在後端 `system_settings` 資料表，因此**各 Server 各自獨立**，
 * 而且不會被前端重新部署覆蓋。
 *
 * 僅系統管理員可進入（路由層 SettingsGuard + PermissionGuard `system_admin_only`，
 * 後端 PUT 亦有 `Depends(is_system_admin)`）。
 */
import { useState, useEffect } from 'react'
import {
  Typography, Breadcrumb, Card, Form, Input, Button, Space, Alert, Spin, message, Divider,
} from 'antd'
import { HomeOutlined, SettingOutlined, SaveOutlined, BankOutlined } from '@ant-design/icons'
import { fetchSiteConfigDetail, updateSiteConfig } from '@/api/siteConfig'
import type { SiteConfigDetail, SiteConfigForm } from '@/api/siteConfig'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

const EMPTY: SiteConfigForm = { site_title: '', login_title: '', login_subtitle: '' }

export default function BasicSettingsPage() {
  const [form] = Form.useForm<SiteConfigForm>()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<SiteConfigDetail | null>(null)

  // 即時預覽用
  const [preview, setPreview] = useState<SiteConfigForm>(EMPTY)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await fetchSiteConfigDetail()
        if (cancelled) return
        const values: SiteConfigForm = {
          site_title: data.site_title,
          login_title: data.login_title,
          login_subtitle: data.login_subtitle,
        }
        setConfig(data)
        setPreview(values)
        form.setFieldsValue(values)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : '載入設定失敗')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [form])

  const onFinish = async (values: SiteConfigForm) => {
    setSaving(true)
    try {
      await updateSiteConfig({
        site_title: values.site_title.trim(),
        login_title: values.login_title.trim(),
        login_subtitle: values.login_subtitle.trim(),
      })
      message.success('已儲存，重新載入頁面套用新文字…')
      // 顯示文字在 React 掛載前就已讀取並快取在模組變數裡，
      // 側邊欄與登入頁不會自動重新渲染，因此直接整頁重載最單純可靠。
      setTimeout(() => window.location.reload(), 800)
    } catch (e) {
      setSaving(false)
      const detail =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || (e instanceof Error ? e.message : '儲存失敗'))
    }
  }

  const rules = (label: string) => [
    { required: true, message: `請輸入${label}` },
    { max: 40, message: '最多 40 個字' },
    {
      validator: (_: unknown, v: string) =>
        v && !v.trim() ? Promise.reject(new Error('不可只填空白')) : Promise.resolve(),
    },
  ]

  const restore = () => {
    if (!config) return
    const values: SiteConfigForm = {
      site_title: config.site_title,
      login_title: config.login_title,
      login_subtitle: config.login_subtitle,
    }
    form.setFieldsValue(values)
    setPreview(values)
  }

  return (
    <div style={{ padding: 24 }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <><HomeOutlined /> 首頁</> },
          { title: NAV_GROUP.settings },
          { title: NAV_PAGE.basicSettings },
        ]}
      />

      <Title level={3} style={{ marginTop: 0 }}>
        <SettingOutlined style={{ marginRight: 8 }} />
        {NAV_PAGE.basicSettings}
      </Title>

      {error && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }} message={error} />
      )}

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="站台顯示文字是各 Server 各自獨立的設定"
        description="設定存在這台 Server 的資料庫，不會同步到其他 Server，也不會被前端重新部署覆蓋。若要讓其他 Server 顯示不同文字，請分別到各站的這個頁面設定。"
      />

      <Spin spinning={loading}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          {/* ── 表單 ── */}
          <Card title="站台顯示文字" style={{ flex: '1 1 420px', minWidth: 380 }}>
            <Form
              form={form}
              layout="vertical"
              onFinish={onFinish}
              onValuesChange={(_, all) => setPreview({ ...EMPTY, ...all })}
            >
              <Form.Item
                name="site_title"
                label="站台標題"
                extra="顯示於側邊欄左上角與瀏覽器分頁。整段可自由輸入。"
                rules={rules('站台標題')}
              >
                <Input placeholder="例：維春集團管理 Portal" allowClear />
              </Form.Item>

              <Form.Item
                name="login_title"
                label="登入頁大標"
                extra="登入卡片上的主標題。"
                rules={rules('登入頁大標')}
              >
                <Input placeholder="例：集團管理 Portal" allowClear />
              </Form.Item>

              <Form.Item
                name="login_subtitle"
                label="登入頁副標"
                extra="登入卡片上的灰色小字。"
                rules={rules('登入頁副標')}
              >
                <Input placeholder="例：維春集團內部作業與管理平台" allowClear />
              </Form.Item>

              <Space>
                <Button
                  type="primary"
                  htmlType="submit"
                  icon={<SaveOutlined />}
                  loading={saving}
                >
                  儲存
                </Button>
                <Button onClick={restore} disabled={saving || !config}>
                  還原
                </Button>
              </Space>
            </Form>

            {config?.updated_at && (
              <Text type="secondary" style={{ display: 'block', marginTop: 16, fontSize: 12 }}>
                最後修改：{config.updated_at}
                {config.updated_by ? `　by ${config.updated_by}` : ''}
              </Text>
            )}
          </Card>

          {/* ── 即時預覽 ── */}
          <Card title="預覽" style={{ flex: '1 1 320px', minWidth: 300 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>側邊欄 / 瀏覽器分頁</Text>
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                height: 56, padding: '0 20px', marginTop: 8,
                border: '1px solid #f0f0f0', borderRadius: 6, background: '#fff',
                overflow: 'hidden',
              }}
            >
              <HomeOutlined style={{ fontSize: 20, color: '#1677ff' }} />
              <Text strong style={{ fontSize: 15, whiteSpace: 'nowrap' }}>
                {preview.site_title || '（未設定）'}
              </Text>
            </div>

            <Divider style={{ margin: '20px 0 12px' }} />

            <Text type="secondary" style={{ fontSize: 12 }}>登入頁</Text>
            <div
              style={{
                textAlign: 'center', marginTop: 8, padding: '20px 16px',
                border: '1px solid #f0f0f0', borderRadius: 6, background: '#fff',
              }}
            >
              <div
                style={{
                  width: 52, height: 52, borderRadius: 12,
                  background: 'linear-gradient(135deg, #1B3A5C, #4BA8E8)',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: 12,
                }}
              >
                <BankOutlined style={{ fontSize: 26, color: '#fff' }} />
              </div>
              <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
                {preview.login_title || '（未設定）'}
              </Title>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {preview.login_subtitle || '（未設定）'}
              </Text>
            </div>
          </Card>
        </div>
      </Spin>
    </div>
  )
}
