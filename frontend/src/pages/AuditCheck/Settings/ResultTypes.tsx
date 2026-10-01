/**
 * 稽核檢查 — 判定類型設定（字色語意由使用者自訂）
 * route: /audit-check/settings/result-types     permissionKey: audit_check_admin
 *
 * 背景：Excel 原本用「紅字＝扣分、藍字＝建議、黑字＝正常」的慣例，語意寫死在
 * 人的習慣裡。2026-09-20 使用者裁示改由使用者自行決定與選擇，因此做成主檔：
 *   - label / color        顯示名稱與文字色
 *   - counts_as_pass       是否計入「達標項數」（決定分數）
 *   - include_in_summary   是否列入「缺失」自動彙整與缺失清單
 *   - is_default           新格子的預設判定（全表只會有一筆）
 *
 * 系統內建三筆（達標／扣分／建議）可改名、改色、改語意，但不可刪除，
 * 避免既有資料的 result_code 失去對應。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, ColorPicker, Form, Input, InputNumber, Modal, Popconfirm,
  Space, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'

import { resultTypesApi } from '@/api/auditCheck'
import type { ResultType } from '@/api/auditCheck'

const { Title, Text } = Typography

export default function AuditResultTypesPage() {
  const [rows, setRows] = useState<ResultType[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ResultType | null>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await resultTypesApi.list()
      setRows(res.data)
    } catch {
      message.error('載入判定類型失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openAdd = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({
      color: '#262626',
      counts_as_pass: true,
      include_in_summary: false,
      is_default: false,
      sort_order: (rows.length + 1) * 10,
    })
    setModalOpen(true)
  }

  const openEdit = (row: ResultType) => {
    setEditing(row)
    form.setFieldsValue({
      code: row.code,
      label: row.label,
      color: row.color,
      counts_as_pass: row.counts_as_pass,
      include_in_summary: row.include_in_summary,
      is_default: row.is_default,
      sort_order: row.sort_order,
    })
    setModalOpen(true)
  }

  const save = async () => {
    const v = await form.validateFields()
    const color = typeof v.color === 'string' ? v.color : v.color?.toHexString?.() ?? '#262626'
    try {
      if (editing) {
        await resultTypesApi.update(editing.id, { ...v, color })
      } else {
        await resultTypesApi.create({ ...v, color })
      }
      message.success('已儲存')
      setModalOpen(false)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    }
  }

  const toggle = async (row: ResultType) => {
    try {
      await resultTypesApi.toggle(row.id)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '操作失敗')
    }
  }

  const remove = async (row: ResultType) => {
    try {
      await resultTypesApi.remove(row.id)
      message.success('已刪除')
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '刪除失敗')
    }
  }

  const columns: ColumnsType<ResultType> = [
    {
      title: '顯示樣式',
      key: 'preview',
      width: 180,
      render: (_: unknown, r: ResultType) => (
        <Space>
          <Tag style={{ color: r.color, borderColor: r.color }}>{r.label}</Tag>
          {r.is_default && <Tag color="blue">預設</Tag>}
          {!r.is_active && <Tag>停用</Tag>}
        </Space>
      ),
    },
    { title: '代碼', dataIndex: 'code', key: 'code', width: 110 },
    { title: '色碼', dataIndex: 'color', key: 'color', width: 100 },
    {
      title: '計入達標',
      dataIndex: 'counts_as_pass',
      key: 'counts_as_pass',
      width: 110,
      render: (v: boolean) => (v ? <Tag color="success">計入</Tag> : <Tag color="error">不計入（扣分）</Tag>),
    },
    {
      title: '列入缺失彙整',
      dataIndex: 'include_in_summary',
      key: 'include_in_summary',
      width: 130,
      render: (v: boolean) => (v ? <Tag color="warning">列入</Tag> : <Text type="secondary">—</Text>),
    },
    { title: '排序', dataIndex: 'sort_order', key: 'sort_order', width: 70 },
    {
      title: '操作',
      key: 'actions',
      width: 230,
      render: (_: unknown, r: ResultType) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>修改</Button>
          <Popconfirm
            title={r.is_active ? '停用後不會出現在填寫選項，既有資料不受影響。' : '確認啟用？'}
            onConfirm={() => toggle(r)} okText="確認" cancelText="取消"
          >
            <Button size="small" danger={r.is_active}>{r.is_active ? '停用' : '啟用'}</Button>
          </Popconfirm>
          {r.is_system ? (
            <Tooltip title="系統內建，不可刪除（可改名、改色、改語意或停用）">
              <Button size="small" type="text" disabled icon={<DeleteOutlined />} />
            </Tooltip>
          ) : (
            <Popconfirm title="確認刪除？已被稽核資料使用時無法刪除。" onConfirm={() => remove(r)} okText="刪除" cancelText="取消">
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
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>稽核檢查 — 判定類型設定</Title>
          <Text type="secondary">自訂每種判定的名稱、顏色，以及是否算達標、是否列入缺失</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增判定類型</Button>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="這裡的設定會立刻影響分數"
        description={
          <span>
            「計入達標」關掉的類型就是扣分項：各部門分數 ＝ 計入達標的格子數 ÷ 有填評語的格子數。
            把既有類型的「計入達標」改掉，會連同歷史期別的分數一起重算（分數是即時計算，不是存下來的數字）。
          </span>
        }
      />

      <Card>
        <Table<ResultType>
          size="small"
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={false}
        />
      </Card>

      <Modal
        title={editing ? `修改判定類型 — ${editing.label}` : '新增判定類型'}
        open={modalOpen}
        onOk={save}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          {!editing && (
            <Form.Item
              name="code"
              label="代碼"
              rules={[
                { required: true, message: '請輸入代碼' },
                { pattern: /^[a-z][a-z0-9_]{1,19}$/, message: '小寫英文開頭，可含數字與底線，2～20 字元' },
              ]}
              extra="建立後不可修改，資料以此對應"
            >
              <Input placeholder="例：pending" />
            </Form.Item>
          )}
          <Form.Item name="label" label="顯示名稱" rules={[{ required: true, message: '請輸入名稱' }]}>
            <Input placeholder="例：待改善" />
          </Form.Item>
          <Form.Item name="color" label="文字顏色" rules={[{ required: true }]}>
            <ColorPicker format="hex" showText />
          </Form.Item>
          <Form.Item name="counts_as_pass" label="計入達標項數" valuePropName="checked"
            extra="關閉 ＝ 此判定視為未達標（扣分）">
            <Switch checkedChildren="計入" unCheckedChildren="扣分" />
          </Form.Item>
          <Form.Item name="include_in_summary" label="列入缺失彙整" valuePropName="checked"
            extra="開啟 ＝ 出現在稽核單的「缺失」列與缺失清單報表">
            <Switch />
          </Form.Item>
          <Form.Item name="is_default" label="設為新格子的預設判定" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} max={9999} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
