/**
 * H1 — 合約範本管理 Tab
 * 顯示在 Settings → 合約範本
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Table, Button, Space, Modal, Form, Input, Select, Switch,
  Popconfirm, Tag, message, Tooltip, Typography,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons'
import type { ContractTemplate, ContractTemplateCreate } from '@/types/contract'
import {
  fetchTemplates, createTemplate, updateTemplate, deleteTemplate,
} from '@/api/contract'

const { Text } = Typography

const CONTRACT_TYPES = [
  '定額月費', '浮動', '一次性', '框架', '服務', '維護', '租賃', '採購', '其他',
]
const RISK_LEVELS = ['低', '中', '高', '關鍵']
const BUDGET_SOURCES = ['年度預算', '追加預算', '專案預算']

export default function TemplatesTab() {
  const [templates, setTemplates] = useState<ContractTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchTemplates(false)
      setTemplates(res.templates)
    } catch {
      message.error('載入範本失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    setEditingId(null)
    form.resetFields()
    form.setFieldsValue({
      default_currency: 'TWD',
      default_notification_days: 30,
      default_auto_renewal: false,
      default_needs_purchase_order: false,
      default_require_acceptance: false,
      default_risk_level: '中',
      default_budget_source: '年度預算',
      is_enabled: true,
    })
    setModalOpen(true)
  }

  const openEdit = (rec: ContractTemplate) => {
    setEditingId(rec.id)
    form.setFieldsValue(rec)
    setModalOpen(true)
  }

  const handleOk = async () => {
    try {
      const values = await form.validateFields() as ContractTemplateCreate
      setSaving(true)
      if (editingId) {
        await updateTemplate(editingId, values)
        message.success('範本已更新')
      } else {
        await createTemplate(values)
        message.success('範本已新增')
      }
      setModalOpen(false)
      load()
    } catch (err: any) {
      if (err?.response?.data?.detail) {
        message.error(err.response.data.detail)
      }
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteTemplate(id)
      message.success('已刪除')
      load()
    } catch {
      message.error('刪除失敗')
    }
  }

  const columns = [
    {
      title: '範本名稱',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <FileTextOutlined style={{ color: '#4BA8E8' }} />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '合約類型',
      dataIndex: 'contract_type',
      key: 'contract_type',
      width: 100,
      render: (v: string) => <Tag>{v || '—'}</Tag>,
    },
    {
      title: '說明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '預設風險',
      dataIndex: 'default_risk_level',
      key: 'default_risk_level',
      width: 90,
      render: (v: string) => {
        const colorMap: Record<string, string> = { 低: 'success', 中: 'warning', 高: 'error', 關鍵: 'error' }
        return <Tag color={colorMap[v] || 'default'}>{v}</Tag>
      },
    },
    {
      title: '通知天數',
      dataIndex: 'default_notification_days',
      key: 'default_notification_days',
      width: 90,
      align: 'center' as const,
      render: (v: number) => `${v} 天`,
    },
    {
      title: '狀態',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 80,
      render: (v: boolean) =>
        v ? <Tag color="success">啟用</Tag> : <Tag color="default">停用</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, rec: ContractTemplate) => (
        <Space>
          <Tooltip title="編輯">
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(rec)} />
          </Tooltip>
          <Popconfirm
            title="確定刪除此範本？"
            onConfirm={() => handleDelete(rec.id)}
            okText="刪除"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新載入</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增範本</Button>
      </Space>

      <Table
        dataSource={templates}
        columns={columns}
        rowKey="id"
        loading={loading}
        size="small"
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={editingId ? '編輯合約範本' : '新增合約範本'}
        open={modalOpen}
        onOk={handleOk}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText={editingId ? '確認更新' : '新增'}
        cancelText="取消"
        width={640}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="範本名稱" rules={[{ required: true, message: '請輸入範本名稱' }]}>
            <Input placeholder="例：月費維護合約" />
          </Form.Item>
          <Form.Item name="contract_type" label="合約類型" rules={[{ required: true, message: '請選擇合約類型' }]}>
            <Select options={CONTRACT_TYPES.map(t => ({ value: t, label: t }))} placeholder="選擇類型" />
          </Form.Item>
          <Form.Item name="description" label="說明">
            <Input.TextArea rows={2} placeholder="可選填範本用途說明" />
          </Form.Item>

          <Form.Item label="預設欄位值" style={{ marginBottom: 0 }}>
            <Space wrap>
              <Form.Item name="default_currency" label="幣別" style={{ marginBottom: 8 }}>
                <Select style={{ width: 90 }}>
                  <Select.Option value="TWD">TWD</Select.Option>
                  <Select.Option value="USD">USD</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item name="default_notification_days" label="通知天數" style={{ marginBottom: 8 }}>
                <Input type="number" style={{ width: 90 }} suffix="天" />
              </Form.Item>
              <Form.Item name="default_risk_level" label="風險等級" style={{ marginBottom: 8 }}>
                <Select style={{ width: 90 }} options={RISK_LEVELS.map(r => ({ value: r, label: r }))} />
              </Form.Item>
              <Form.Item name="default_budget_source" label="預算來源" style={{ marginBottom: 8 }}>
                <Select style={{ width: 130 }} options={BUDGET_SOURCES.map(s => ({ value: s, label: s }))} />
              </Form.Item>
            </Space>
          </Form.Item>

          <Space wrap style={{ marginBottom: 16 }}>
            <Form.Item name="default_auto_renewal" valuePropName="checked" label="自動續約" style={{ marginBottom: 0 }}>
              <Switch size="small" />
            </Form.Item>
            <Form.Item name="default_needs_purchase_order" valuePropName="checked" label="需請購單" style={{ marginBottom: 0 }}>
              <Switch size="small" />
            </Form.Item>
            <Form.Item name="default_require_acceptance" valuePropName="checked" label="需驗收" style={{ marginBottom: 0 }}>
              <Switch size="small" />
            </Form.Item>
            <Form.Item name="is_enabled" valuePropName="checked" label="啟用" style={{ marginBottom: 0 }}>
              <Switch size="small" />
            </Form.Item>
          </Space>

          <Form.Item name="default_pricing_method" label="計價方式（預設）">
            <Input placeholder="例：固定金額" />
          </Form.Item>
          <Form.Item name="default_remarks" label="預設備註範本">
            <Input.TextArea rows={3} placeholder="新增合約時自動填入的備註文字" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
