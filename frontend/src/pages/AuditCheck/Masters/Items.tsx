/**
 * 稽核檢查 — 檢查項主檔
 * route: /audit-check/masters/items     permissionKey: audit_check_admin
 *
 * 兩階結構：1 階大項（如「廠商/客戶管理」）→ 2 階子項（如「聯絡簿」）。
 *
 * ⚠️ 使用者裁示：主檔可自行新增、改名、停用；**一旦被任一期稽核單引用即鎖定**，
 *    不可改名或刪除，只能停用（保護歷史稽核資料）。後端同樣會擋，前端只是提示。
 * ⚠️ 名稱只填純項目名稱，不要寫「-工程.管理」這類部門後綴或
 *    「(飲水機.排煙.污水設備)」這類店別補充——那兩者是逐期、逐店不同的，
 *    在稽核單版面調整時才指定。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Space, Table, Tag,
  Tooltip, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined,
} from '@ant-design/icons'

import { itemsApi } from '@/api/auditCheck'
import type { AuditItem } from '@/api/auditCheck'

const { Title, Text } = Typography

export default function AuditItemsMasterPage() {
  const [rows, setRows] = useState<AuditItem[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<AuditItem | null>(null)
  const [parentFor, setParentFor] = useState<AuditItem | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await itemsApi.list(true)
      setRows(res.data)
    } catch {
      message.error('載入檢查項主檔失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openAdd = (parent?: AuditItem) => {
    setEditing(null)
    setParentFor(parent ?? null)
    form.resetFields()
    form.setFieldsValue({ sort_order: 0 })
    setModalOpen(true)
  }

  const openEdit = (row: AuditItem) => {
    setEditing(row)
    setParentFor(null)
    form.setFieldsValue({ name: row.name, description: row.description, sort_order: row.sort_order })
    setModalOpen(true)
  }

  const save = async () => {
    const v = await form.validateFields()
    try {
      if (editing) {
        await itemsApi.update(editing.id, v)
      } else {
        await itemsApi.create({ ...v, parent_id: parentFor?.id ?? null })
      }
      message.success('已儲存')
      setModalOpen(false)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    }
  }

  const toggle = async (row: AuditItem) => {
    try {
      await itemsApi.toggle(row.id)
      message.success(row.is_active ? '已停用' : '已啟用')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '操作失敗')
    }
  }

  const remove = async (row: AuditItem) => {
    try {
      await itemsApi.remove(row.id)
      message.success('已刪除')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '刪除失敗')
    }
  }

  const columns: ColumnsType<AuditItem> = [
    {
      title: '項目名稱',
      dataIndex: 'name',
      key: 'name',
      render: (v: string, row: AuditItem) => (
        <Space>
          <span style={{ fontWeight: row.parent_id == null ? 600 : 400, color: row.parent_id == null ? '#1B3A5C' : undefined }}>
            {v}
          </span>
          {row.in_use && <Tooltip title="已被稽核單引用，不可改名／刪除"><Tag color="blue">使用中</Tag></Tooltip>}
          {!row.is_active && <Tag>停用</Tag>}
        </Space>
      ),
    },
    { title: '說明', dataIndex: 'description', key: 'description', width: 280, render: (v) => v || '—' },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
    {
      title: '操作',
      key: 'actions',
      width: 300,
      render: (_: unknown, row: AuditItem) => (
        <Space size="small" wrap>
          {row.parent_id == null && (
            <Button size="small" icon={<PlusOutlined />} onClick={() => openAdd(row)}>新增子項</Button>
          )}
          <Tooltip title={row.in_use ? '已被稽核單引用，只能改說明與排序' : ''}>
            <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>修改</Button>
          </Tooltip>
          <Popconfirm
            title={row.is_active ? '確認停用？停用後不出現在勾選清單，歷史資料不受影響。' : '確認啟用？'}
            onConfirm={() => toggle(row)} okText="確認" cancelText="取消"
          >
            <Button size="small" danger={row.is_active}>{row.is_active ? '停用' : '啟用'}</Button>
          </Popconfirm>
          {!row.in_use && (
            <Popconfirm title="確認刪除？" onConfirm={() => remove(row)} okText="刪除" cancelText="取消">
              <Button size="small" type="text" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>稽核檢查 — 檢查項主檔</Title>
          <Text type="secondary">兩階結構：大項 → 子項；每期稽核單從這裡勾選</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openAdd()}>新增大項</Button>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="名稱只填純項目名稱"
        description="「-工程.管理」這類建議查核部門、「(飲水機.排煙.污水設備)」這類店別補充，都是逐期逐店不同的，請在稽核單的「版面調整」指定，不要寫進主檔名稱，否則跨月統計會對不齊。"
      />

      <Card>
        <Table<AuditItem>
          size="small"
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={false}
          expandable={{ defaultExpandAllRows: true, childrenColumnName: 'children' }}
        />
      </Card>

      <Modal
        title={editing ? '修改檢查項' : parentFor ? `新增子項 — ${parentFor.name}` : '新增大項'}
        open={modalOpen}
        onOk={save}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item
            name="name"
            label="項目名稱"
            rules={[{ required: true, message: '請輸入名稱' }]}
            extra={editing?.in_use ? '此項目已被稽核單引用，改名會被後端擋下（409）' : undefined}
          >
            <Input placeholder="例：聯絡簿" disabled={!!editing?.in_use} />
          </Form.Item>
          <Form.Item name="description" label="說明">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} max={9999} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
