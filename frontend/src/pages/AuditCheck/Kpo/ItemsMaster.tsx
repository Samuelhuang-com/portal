/**
 * 現場營運稽核項目
 * route: /audit-check/kpo/items     permissionKey: audit_check_admin
 *
 * 各部門 16 項稽核項目（依 Excel「財#1稽核系統建構-整合」植入），可新增、編輯、停用、刪除。
 * 刪除不影響已選定在歷史期別的項目（期別內是快照）。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Space, Switch, Table, Tabs, Tag,
  Select, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'

import { kpoDeptApi, kpoItemApi } from '@/api/auditKpo'
import type { KpoDept, KpoItem } from '@/api/auditKpo'
import { refOptionsApi } from '@/api/auditCheck'
import type { RefOption } from '@/api/auditCheck'

const { Title, Text } = Typography

export default function AuditKpoItemsMasterPage() {
  const [depts, setDepts] = useState<KpoDept[]>([])
  const [items, setItems] = useState<KpoItem[]>([])
  const [activeDept, setActiveDept] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [d, i] = await Promise.all([kpoDeptApi.list(), kpoItemApi.list()])
      setDepts(d.data)
      setItems(i.data)
      setActiveDept((cur) => cur ?? d.data[0]?.id)
    } catch {
      message.error('載入 現場營運稽核項目失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => items.filter((i) => i.department_id === activeDept), [items, activeDept])
  const dept = depts.find((d) => d.id === activeDept)
  const rowSum = rows.filter((r) => r.is_active).reduce((a, b) => a + b.score, 0)

  // ── 項目 ────────────────────────────────────────────────────────────────
  const [itemOpen, setItemOpen] = useState(false)
  const [editing, setEditing] = useState<KpoItem | null>(null)
  const [itemForm] = Form.useForm()

  const openItem = (row?: KpoItem) => {
    setEditing(row ?? null)
    itemForm.resetFields()
    itemForm.setFieldsValue(row
      ? { item_no: row.item_no, is_key: row.is_key, name: row.name, score: row.score, method: row.method ?? '' }
      : { is_key: false, score: 5 })
    setItemOpen(true)
  }

  const saveItem = async () => {
    const v = await itemForm.validateFields()
    try {
      if (editing) {
        await kpoItemApi.update(editing.id, {
          item_no: v.item_no ?? null, is_key: v.is_key, name: v.name, score: v.score, method: v.method || null,
        })
      } else if (activeDept) {
        await kpoItemApi.create({
          department_id: activeDept, item_no: v.item_no ?? null, is_key: v.is_key,
          name: v.name, score: v.score, method: v.method || null,
        })
      }
      message.success('已儲存')
      setItemOpen(false)
      load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '儲存失敗')
    }
  }

  const toggle = async (row: KpoItem, is_active: boolean) => {
    try { await kpoItemApi.update(row.id, { is_active }); load() } catch { message.error('更新失敗') }
  }
  const remove = async (row: KpoItem) => {
    try { await kpoItemApi.remove(row.id); message.success('已刪除'); load() } catch { message.error('刪除失敗') }
  }

  // ── 部門 ────────────────────────────────────────────────────────────────
  // 2026-10-11 裁示：「公司別」先隱藏（選起來很怪）。部門只用名稱；改 true 即可恢復公司別／部門別連結欄位。
  const SHOW_COMPANY_FIELD = false
  const [deptOpen, setDeptOpen] = useState(false)
  const [deptEditing, setDeptEditing] = useState<KpoDept | null>(null)
  const [deptForm] = Form.useForm()
  const [companies, setCompanies] = useState<RefOption[]>([])
  const [refDepts, setRefDepts] = useState<RefOption[]>([])
  const formCompany: number | undefined = Form.useWatch('company_id', deptForm)

  useEffect(() => {
    refOptionsApi.companies().then(setCompanies).catch(() => message.error('載入公司別失敗'))
  }, [])
  useEffect(() => {
    if (!deptOpen || !formCompany) { setRefDepts([]); return }
    refOptionsApi.departments(formCompany).then(setRefDepts).catch(() => message.error('載入部門別失敗'))
  }, [deptOpen, formCompany])

  const openDept = (d?: KpoDept) => {
    setDeptEditing(d ?? null)
    deptForm.resetFields()
    deptForm.setFieldsValue(d
      ? {
          company_id: d.company_id ?? undefined, ref_department_id: d.ref_department_id ?? undefined,
          name: d.name, source_title: d.source_title ?? '', is_active: d.is_active,
        }
      : { is_active: true })
    setDeptOpen(true)
  }
  const saveDept = async () => {
    const v = await deptForm.validateFields()
    try {
      if (deptEditing) {
        const linked = !!deptEditing.ref_department_id
        await kpoDeptApi.update(deptEditing.id, {
          ...(linked ? {} : { name: v.name }),
          ...(SHOW_COMPANY_FIELD && v.ref_department_id && (v.ref_department_id !== deptEditing.ref_department_id || v.company_id !== deptEditing.company_id)
            ? { company_id: v.company_id, ref_department_id: v.ref_department_id } : {}),
          source_title: v.source_title || null, is_active: v.is_active,
        })
      } else {
        const res = await kpoDeptApi.create(SHOW_COMPANY_FIELD
          ? { company_id: v.company_id, ref_department_id: v.ref_department_id, source_title: v.source_title || null }
          : { name: (v.name ?? '').trim(), source_title: v.source_title || null })
        setActiveDept(res.data.id)
      }
      message.success('已儲存')
      setDeptOpen(false)
      load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '儲存失敗')
    }
  }

  const columns: ColumnsType<KpoItem> = [
    {
      title: '項數', width: 70, align: 'center',
      render: (_, r) => (r.is_key ? <Tag color="gold">★{r.item_no ?? ''}</Tag> : <span>{r.item_no ?? ''}</span>),
    },
    { title: '品質項目', dataIndex: 'name', render: (v: string) => <div style={{ whiteSpace: 'pre-wrap' }}>{v}</div> },
    { title: '分數', dataIndex: 'score', width: 64, align: 'right' },
    {
      title: '備註（查核方式）', dataIndex: 'method', width: 240,
      render: (v: string | null) => <div style={{ whiteSpace: 'pre-wrap', color: '#64748b' }}>{v ?? ''}</div>,
    },
    {
      title: '啟用', width: 70, align: 'center',
      render: (_, r) => <Switch size="small" checked={r.is_active} onChange={(c) => toggle(r, c)} />,
    },
    {
      title: '操作', width: 100, align: 'center',
      render: (_, r) => (
        <Space size={2}>
          <Button size="small" type="text" icon={<EditOutlined />} onClick={() => openItem(r)} />
          <Popconfirm title="刪除此稽核項目？" description={r.in_use ? '已被歷史期別選定；歷史期別的內容不受影響。' : undefined}
            okText="刪除" okButtonProps={{ danger: true }} onConfirm={() => remove(r)}>
            <Button size="small" type="text" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }} wrap>
        <div>
          <Title level={4} style={{ margin: 0 }}>現場營運稽核項目</Title>
          <Text type="secondary">依 Excel「財#1稽核系統建構-整合」建立；★ 重點項 10 分、其餘 5 分，每部門合計 100 分</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
          <Button onClick={() => openDept()}>新增部門</Button>
          <Button type="primary" icon={<PlusOutlined />} disabled={!activeDept} onClick={() => openItem()}>新增項目</Button>
        </Space>
      </Space>

      <Card size="small" loading={loading && depts.length === 0}>
        <Tabs
          activeKey={activeDept ? String(activeDept) : undefined}
          onChange={(k) => setActiveDept(Number(k))}
          items={depts.map((d) => ({
            key: String(d.id),
            label: <span style={d.is_active ? undefined : { color: '#aaa' }}>{d.display_name}（{d.item_count}）</span>,
          }))}
          tabBarExtraContent={dept ? <Button size="small" onClick={() => openDept(dept)}>編輯部門</Button> : null}
        />
        {dept?.source_title && <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>{dept.source_title}</Text>}
        {dept && rowSum !== 100 && (
          <Alert type="warning" showIcon style={{ marginBottom: 8 }}
            message={`啟用項目分數合計 ${rowSum} 分（Excel 規則為 100 分）`} />
        )}
        <Table rowKey="id" size="small" columns={columns} dataSource={rows} loading={loading}
          pagination={false} scroll={{ x: 800 }} />
      </Card>

      <Modal title={editing ? '編輯稽核項目' : `新增稽核項目 — ${dept?.display_name ?? ''}`} open={itemOpen}
        onCancel={() => setItemOpen(false)} onOk={saveItem} okText="儲存" destroyOnClose width={640}>
        <Form form={itemForm} layout="vertical">
          <Space size="large" align="start">
            <Form.Item name="item_no" label="項數"><InputNumber min={0} max={999} /></Form.Item>
            <Form.Item name="is_key" label="★ 重點項" valuePropName="checked">
              <Switch onChange={(c) => itemForm.setFieldValue('score', c ? 10 : 5)} />
            </Form.Item>
            <Form.Item name="score" label="分數" rules={[{ required: true }]}><InputNumber min={0} max={100} /></Form.Item>
          </Space>
          <Form.Item name="name" label="品質項目" rules={[{ required: true, message: '請輸入項目內容' }]}>
            <Input.TextArea autoSize={{ minRows: 3, maxRows: 10 }} />
          </Form.Item>
          <Form.Item name="method" label="備註（查核方式）"><Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} /></Form.Item>
        </Form>
      </Modal>

      <Modal title={deptEditing ? '編輯部門' : '新增部門'} open={deptOpen} onCancel={() => setDeptOpen(false)}
        onOk={saveDept} okText="儲存" destroyOnClose>
        <Form form={deptForm} layout="vertical">
          {SHOW_COMPANY_FIELD ? (
            <>
              <Form.Item name="company_id" label="公司別" rules={[{ required: !deptEditing || !!deptEditing.ref_department_id, message: '請選擇公司別' }]}>
                <Select placeholder="選擇公司別" showSearch optionFilterProp="label"
                  options={companies.map((c) => ({ value: c.id, label: c.name }))}
                  onChange={() => deptForm.setFieldValue('ref_department_id', undefined)} />
              </Form.Item>
              <Form.Item name="ref_department_id" label="部門別" rules={[{ required: !deptEditing || !!deptEditing.ref_department_id, message: '請選擇部門別' }]}>
                <Select placeholder={formCompany ? '選擇部門別' : '請先選擇公司別'} disabled={!formCompany}
                  showSearch optionFilterProp="label"
                  options={refDepts.map((d) => ({ value: d.id, label: d.name }))} />
              </Form.Item>
              {deptEditing && !deptEditing.ref_department_id && (
                <Alert type="info" showIcon style={{ marginBottom: 12 }}
                  message={`「${deptEditing.name}」是 Excel 植入、尚未連結部門主檔；請選擇公司別與部門別完成連結（連結後名稱以部門主檔為準）。`} />
              )}
            </>
          ) : (
            <Form.Item name="name" label="部門名稱" rules={[{ required: true, whitespace: true, message: '請輸入部門名稱' }]}>
              <Input maxLength={100} disabled={!!deptEditing?.ref_department_id} placeholder="例：營業部" />
            </Form.Item>
          )}
          <Form.Item name="source_title" label="備註（如會議定案日期）"><Input maxLength={200} /></Form.Item>
          {deptEditing && <Form.Item name="is_active" label="啟用" valuePropName="checked"><Switch /></Form.Item>}
        </Form>
      </Modal>
    </div>
  )
}
