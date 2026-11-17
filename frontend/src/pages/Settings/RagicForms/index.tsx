/**
 * 系統設定 › Ragic 表單關聯（規格 docs/SPEC_stock_management.md §4.3）
 * 2026-11-17 Phase 1 建立於庫存管理，同日依 Samuel 裁示搬到系統設定，並開放 settings_ragic_forms_manage 編輯表單設定
 *
 * TAB 1「表單關聯」：公司 × 部門 × 請購單／採購單／請款單（表單名稱、在 Ragic 開啟、同步筆數、最後同步時間）
 * TAB 2「採購單」：Ragic 採購單同步結果，點列開明細 Drawer（CLAUDE.md §7）
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Drawer, Form, Input, Modal, Popconfirm, Row, Select, Space, Statistic, Switch, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import { EditOutlined, LinkOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  createSheetConfig, fetchPurchaseOrder, fetchPurchaseOrders, fetchRagicForms, resetSheetConfig, updateSheetConfig,
  type FormKey, type PurchaseOrderDetail, type PurchaseOrderRow, type RagicFormCell, type RagicFormRow, type RagicFormsResp,
} from '@/api/ragicForms'
import { useAuthStore } from '@/stores/authStore'

const errMsg = (e: unknown, fallback: string) => {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

/** 編輯目標：既有設定（cell）或「未設定」格要新增（module＋部門） */
type EditTarget =
  | { mode: 'edit'; row: RagicFormRow; key: FormKey; cell: RagicFormCell }
  | { mode: 'create'; row: RagicFormRow; key: FormKey; module: string }

const { Text } = Typography
const FORM_KEYS: { key: FormKey; label: string }[] = [
  { key: 'purchase', label: '請購單' },
  { key: 'po', label: '採購單' },
  { key: 'claim', label: '請款單' },
]
const COMPANY_COLOR: Record<string, string> = { 樂群: 'blue', 日曜: 'orange', 台中: 'green' }

const money = (v: number | null) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)

function FormCell({ cell, canManage, onEdit, onCreate }: {
  cell: RagicFormCell | null; canManage: boolean; onEdit: () => void; onCreate: () => void
}) {
  if (!cell) {
    return (
      <Space size={4}>
        <Tag color="red">未設定</Tag>
        {canManage && <Button size="small" type="link" icon={<PlusOutlined />} onClick={onCreate}>設定</Button>}
      </Space>
    )
  }
  return (
    <Space direction="vertical" size={0}>
      <Space size={4}>
        <a href={cell.url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>
          <LinkOutlined /> {cell.form_name}
        </a>
        {!cell.is_active && <Tag>同步已暫停</Tag>}
        {cell.manual_override && <Tooltip title="路徑為手動設定，系統啟動時不會改回預設值"><Tag color="gold">手動</Tag></Tooltip>}
        {canManage && <Button size="small" type="text" icon={<EditOutlined />} onClick={onEdit} />}
      </Space>
      <Text type="secondary" style={{ fontSize: 12 }}>{cell.path}{cell.detail_path !== cell.path ? `（內頁 ${cell.detail_path}）` : ''}</Text>
      <Text style={{ fontSize: 12 }}>
        {cell.records.toLocaleString()} 筆{cell.last_sync_at ? `｜同步 ${cell.last_sync_at}` : '｜尚未同步'}
      </Text>
    </Space>
  )
}

function FormsTab() {
  const [data, setData] = useState<RagicFormsResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [company, setCompany] = useState<string | undefined>()
  const [dept, setDept] = useState('')
  const [onlyMissing, setOnlyMissing] = useState(false)
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canManage = hasPermission('settings_ragic_forms_manage')
  const [target, setTarget] = useState<EditTarget | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<{ list_path: string; detail_path: string; is_active: boolean }>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchRagicForms()
      setData(res.data)
    } catch {
      message.error('讀取 Ragic 表單關聯失敗')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { load() }, [load])

  const rows = useMemo(() => (data?.rows ?? []).filter((r) =>
    (!company || r.company === company)
    && (!dept || r.department.includes(dept.trim()))
    && (!onlyMissing || !r.purchase || !r.po || !r.claim)), [data, company, dept, onlyMissing])

  const stat = useMemo(() => {
    const all = data?.rows ?? []
    return {
      depts: all.length,
      purchase: all.filter((r) => r.purchase).length,
      po: all.filter((r) => r.po).length,
      claim: all.filter((r) => r.claim).length,
    }
  }, [data])

  const columns: ColumnsType<RagicFormRow> = [
    {
      title: '公司別', dataIndex: 'company', width: 130,
      render: (v: string, r) => <Space size={4}><Tag color={COMPANY_COLOR[v]}>{v}</Tag><Text type="secondary">{r.company_alias}</Text></Space>,
    },
    { title: '部門', dataIndex: 'department', width: 140 },
    ...FORM_KEYS.map(({ key, label }) => ({
      title: label, key, render: (_: unknown, r: RagicFormRow) => (
        <FormCell cell={r[key]} canManage={canManage}
          onEdit={() => openEdit(r, key)} onCreate={() => openCreate(r, key)} />
      ),
    })),
  ]

  function openEdit(row: RagicFormRow, key: FormKey) {
    const cell = row[key]
    if (!cell) return
    setTarget({ mode: 'edit', row, key, cell })
    form.setFieldsValue({ list_path: cell.path, detail_path: cell.detail_path, is_active: cell.is_active })
  }

  function openCreate(row: RagicFormRow, key: FormKey) {
    const mod = data?.modules.find((m) => m.company === row.company && m.form_type === key)
    if (!mod) return
    setTarget({ mode: 'create', row, key, module: mod.module })
    form.setFieldsValue({ list_path: '', detail_path: '', is_active: true })
  }

  async function onSave() {
    if (!target) return
    const v = await form.validateFields()
    setSaving(true)
    try {
      if (target.mode === 'edit') {
        await updateSheetConfig(target.cell.config_id, {
          list_path: v.list_path, detail_path: v.detail_path || v.list_path, is_active: v.is_active,
        })
      } else {
        await createSheetConfig({
          module: target.module, display_name: target.row.department,
          list_path: v.list_path, detail_path: v.detail_path || undefined, is_active: v.is_active,
        })
      }
      message.success('已儲存；下次同步起生效')
      setTarget(null)
      load()
    } catch (e) {
      message.error(errMsg(e, '儲存失敗'))
    } finally {
      setSaving(false)
    }
  }

  async function onReset() {
    if (target?.mode !== 'edit') return
    setSaving(true)
    try {
      await resetSheetConfig(target.cell.config_id)
      message.success('已還原為程式預設路徑')
      setTarget(null)
      load()
    } catch (e) {
      message.error(errMsg(e, '還原失敗'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}><Card size="small"><Statistic title="公司 × 部門" value={stat.depts} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="已設定請購單" value={stat.purchase} suffix={`/ ${stat.depts}`} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="已設定採購單" value={stat.po} suffix={`/ ${stat.depts}`} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="已設定請款單" value={stat.claim} suffix={`/ ${stat.depts}`} /></Card></Col>
      </Row>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select allowClear placeholder="公司別" style={{ width: 140 }} value={company} onChange={setCompany}
            options={(data?.companies ?? []).map((c) => ({ value: c, label: `${c}（${data?.company_alias[c] ?? ''}）` }))} />
          <Input allowClear placeholder="部門" style={{ width: 160 }} value={dept} onChange={(e) => setDept(e.target.value)} />
          <Space size={4}><Switch size="small" checked={onlyMissing} onChange={setOnlyMissing} /><span>只看缺表單</span></Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
          <Text type="secondary">共 {rows.length} 列</Text>
        </Space>
      </Card>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        message={canManage
          ? '可直接修改或補設定表單路徑（標示「手動」的不會被系統預設值覆蓋）；「未設定」代表該部門此類表單的 Ragic 網址尚未確認（SPEC D14）。'
          : '「未設定」代表該部門此類表單的 Ragic 網址尚未確認（SPEC D14）；修改需「Ragic 表單關聯：編輯」權限。'} />
      <Table<RagicFormRow> size="small" rowKey={(r) => `${r.company}-${r.department}`} loading={loading}
        dataSource={rows} columns={columns} pagination={false} />

      <Modal
        open={!!target}
        title={target ? `${target.mode === 'edit' ? '修改' : '新增'}表單設定：${target.row.company}／${target.row.department}／${FORM_KEYS.find((f) => f.key === target.key)?.label}` : ''}
        onCancel={() => setTarget(null)}
        destroyOnClose
        footer={[
          target?.mode === 'edit' && target.cell.manual_override ? (
            <Popconfirm key="reset" title="還原為程式預設的表單路徑？" onConfirm={onReset}>
              <Button loading={saving}>還原預設</Button>
            </Popconfirm>
          ) : null,
          <Button key="cancel" onClick={() => setTarget(null)}>取消</Button>,
          <Button key="ok" type="primary" loading={saving} onClick={onSave}>儲存</Button>,
        ]}
      >
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message="改路徑會讓同步改讀另一張 Ragic 表；已同步的舊資料保留不刪。存檔後標示「手動」，系統啟動時不會改回預設值。" />
        <Form form={form} layout="vertical">
          <Form.Item name="list_path" label="清單路徑（可貼完整 Ragic 網址）" rules={[{ required: true, message: '請輸入表單路徑' }]}>
            <Input placeholder="例：new-tab/11 或 https://ap12.ragic.com/soutlet001/new-tab/11" />
          </Form.Item>
          <Form.Item name="detail_path" label="內頁路徑（空白＝同清單路徑）">
            <Input placeholder="通常與清單路徑相同" />
          </Form.Item>
          <Form.Item name="is_active" label="同步" valuePropName="checked">
            <Switch checkedChildren="啟用" unCheckedChildren="暫停" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

function PurchaseOrdersTab() {
  const [rows, setRows] = useState<PurchaseOrderRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [company, setCompany] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [includeDeleted, setIncludeDeleted] = useState(false)
  const [detail, setDetail] = useState<PurchaseOrderDetail | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchPurchaseOrders({ company, keyword: keyword.trim() || undefined, include_deleted: includeDeleted })
      setRows(res.data.rows)
      setTotal(res.data.total)
    } catch {
      message.error('讀取採購單失敗')
    } finally {
      setLoading(false)
    }
  }, [company, keyword, includeDeleted])
  useEffect(() => { load() }, [company, includeDeleted]) // eslint-disable-line react-hooks/exhaustive-deps

  const openDetail = async (id: number) => {
    setDrawerOpen(true)
    setDetail(null)
    try {
      const res = await fetchPurchaseOrder(id)
      setDetail(res.data)
    } catch {
      message.error('讀取採購單明細失敗')
    }
  }

  const columns: ColumnsType<PurchaseOrderRow> = [
    { title: '公司別', dataIndex: 'company', width: 80, render: (v: string) => <Tag color={COMPANY_COLOR[v]}>{v}</Tag> },
    { title: '部門', dataIndex: 'department', width: 110 },
    {
      title: '採購編號', dataIndex: 'po_no', width: 160,
      render: (v: string, r) => <Space size={4}>{v || '—'}{r.is_ragic_deleted && <Tag color="red">Ragic 已刪除</Tag>}</Space>,
    },
    { title: '日期', key: 'date', width: 100, render: (_: unknown, r) => r.apply_date || r.arrival_date || '—' },
    { title: '申請人', dataIndex: 'requester', width: 100, render: (v: string | null) => v || '—' },
    { title: '用途說明', dataIndex: 'purpose', ellipsis: true, render: (v: string | null) => v || '—' },
    { title: '擬定廠商', dataIndex: 'vendor_name', width: 180, ellipsis: true, render: (v: string | null) => v || '—' },
    { title: '小計（未稅）', dataIndex: 'subtotal', width: 110, align: 'right', render: money },
    { title: '品項', dataIndex: 'item_count', width: 60, align: 'right' },
    { title: '來源請購單號', dataIndex: 'source_pr_no', width: 170, render: (v: string | null) => v || '—' },
  ]

  const identifier = detail ? (detail.detail['採購編號'] || detail.ragic_id) : ''

  return (
    <>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select allowClear placeholder="公司別" style={{ width: 120 }} value={company} onChange={setCompany}
            options={['樂群', '日曜', '台中'].map((c) => ({ value: c, label: c }))} />
          <Input.Search allowClear placeholder="採購編號／用途／廠商／申請人" style={{ width: 280 }}
            value={keyword} onChange={(e) => setKeyword(e.target.value)} onSearch={load} />
          <Space size={4}><Switch size="small" checked={includeDeleted} onChange={setIncludeDeleted} /><span>含 Ragic 已刪除</span></Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
          <Text type="secondary">共 {total.toLocaleString()} 張{total > rows.length ? `（顯示前 ${rows.length} 張）` : ''}</Text>
        </Space>
      </Card>
      <Table<PurchaseOrderRow> size="small" rowKey="id" loading={loading} dataSource={rows} columns={columns}
        pagination={{ pageSize: 50, showSizeChanger: false }}
        onRow={(r) => ({ onClick: () => openDetail(r.id), style: { cursor: 'pointer' } })} />

      <Drawer
        open={drawerOpen}
        width={640}
        onClose={() => { setDrawerOpen(false); setDetail(null) }}
        title={detail ? (
          <Space>
            <Tag color={COMPANY_COLOR[detail.company]}>{detail.company}</Tag>
            <span>{`${detail.department} 採購單：${identifier}`}</span>
            {detail.ragic_url && (
              <a href={detail.ragic_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>
                <LinkOutlined /> 在 Ragic 查看
              </a>
            )}
          </Space>
        ) : '載入中…'}
      >
        {detail && (
          <>
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="狀態">
                {detail.is_ragic_deleted ? <Tag color="red">Ragic 已刪除</Tag> : <Tag color="green">正常</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="擬定廠商"><b>{detail.vendor_name || '—'}</b></Descriptions.Item>
              <Descriptions.Item label="小計（未稅）">{money(detail.subtotal)}</Descriptions.Item>
              <Descriptions.Item label="營業稅">{money(detail.tax)}</Descriptions.Item>
              <Descriptions.Item label="總計"><b>{money(detail.total)}</b></Descriptions.Item>
              <Descriptions.Item label="最後同步">{detail.last_sync_at || '—'}</Descriptions.Item>
            </Descriptions>

            <div style={{ fontWeight: 600, marginBottom: 6 }}>品項</div>
            <Table size="small" rowKey="id" pagination={false} dataSource={detail.items} style={{ marginBottom: 16 }}
              columns={[
                { title: '項次', dataIndex: 'seq', width: 50, render: (v: number | null) => v ?? '—' },
                {
                  title: '產品名稱', dataIndex: 'product_name',
                  render: (v: string | null, i) => (
                    <Space direction="vertical" size={0}>
                      <span>{v || '—'}</span>
                      {i.item_code && <Text type="secondary" style={{ fontSize: 12 }}>料號 {i.item_code}</Text>}
                      {i.remark && <Text type="secondary" style={{ fontSize: 12 }}>{i.remark}</Text>}
                    </Space>
                  ),
                },
                { title: '數量', key: 'qty', width: 80, align: 'right', render: (_: unknown, i) => `${i.qty_raw ?? '—'} ${i.unit ?? ''}` },
                { title: '單價', dataIndex: 'unit_price', width: 90, align: 'right', render: money },
                { title: '金額', dataIndex: 'amount', width: 90, align: 'right', render: money },
              ]} />

            <div style={{ fontWeight: 600, marginBottom: 6 }}>明細欄位</div>
            <Descriptions size="small" column={1} bordered>
              {Object.entries(detail.detail).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>
                  {!v ? '—'
                    : k === '總計' ? <b>{`$${v}`}</b>
                    : k === '小計' || k === '營業稅' ? `$${v}`
                    : k === '採購編號' ? <b>{v}</b>
                    : k === 'Ragic 狀態' ? <Tag color={v === '正常' ? 'green' : 'red'}>{v}</Tag>
                    : <span style={{ whiteSpace: 'pre-wrap' }}>{v}</span>}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </>
        )}
      </Drawer>
    </>
  )
}

export default function RagicFormsPage() {
  return (
    <div>
      <Tabs
        items={[
          { key: 'forms', label: '表單關聯', children: <FormsTab /> },
          { key: 'po', label: '採購單', children: <PurchaseOrdersTab /> },
        ]}
      />
    </div>
  )
}
