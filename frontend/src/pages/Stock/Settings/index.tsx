/**
 * 庫存管理 › 庫存主檔設定（規格 docs/SPEC_stock_management.md §8.1、§8.7、§11，Phase 2 2026-11-17）
 *
 * TAB「倉庫」        公司 × 部門的倉庫（部門取 settings/company-departments）— stock_settings_manage
 * TAB「料號庫存設定」 週採料號是否納入庫存、採購單位換算（依勾選或類別批次）— stock_settings_manage
 * TAB「期初開帳」    上線第一個月以盤點結果當期初；倉庫有其他異動後就不能再開／作廢 — stock_opening_manage
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, DatePicker, Descriptions, Drawer, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch,
  Table, Tabs, Tag, Typography, message,
} from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import {
  bulkItemSetting, checkOpening, createOpening, createWarehouse, errMsg, fetchCategories, fetchOpening, fetchOpenings,
  fetchStockDepartments, fetchStockItems, fetchWarehouses, rebuildBalances, updateItemSetting, updateWarehouse, voidOpening,
  type Opening, type StockDepartment, type StockItem, type Warehouse, type WarehouseInput,
} from '@/api/stock'
import { useAuthStore } from '@/stores/authStore'
import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'

const { Text } = Typography
const money = (v: number | null | undefined) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)
const STATUS_TAG: Record<string, JSX.Element> = {
  active: <Tag color="green">啟用</Tag>, inactive: <Tag>停用</Tag>, counting: <Tag color="orange">盤點中</Tag>,
}

// ── 倉庫 ──────────────────────────────────────────────────────────────────────
function WarehousesTab({ code, canManage }: { code: string; canManage: boolean }) {
  const [rows, setRows] = useState<Warehouse[]>([])
  const [depts, setDepts] = useState<StockDepartment[]>([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<Warehouse | 'new' | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<WarehouseInput>()

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await fetchWarehouses(code)).data) } catch (e) { message.error(errMsg(e, '讀取倉庫失敗')) } finally { setLoading(false) }
  }, [code])
  useEffect(() => { load(); fetchStockDepartments(code).then((r) => setDepts(r.data)).catch(() => setDepts([])) }, [code, load])

  const open = (w: Warehouse | 'new') => {
    setEditing(w)
    form.setFieldsValue(w === 'new'
      ? { name: '', department_id: undefined, keeper_name: '', status: 'active', notes: '', issue_requires_approval: false }
      : { name: w.name, department_id: w.department_id ?? undefined, keeper_name: w.keeper_name ?? '', status: w.status === 'inactive' ? 'inactive' : 'active', notes: w.notes ?? '', issue_requires_approval: w.issue_requires_approval })
  }
  const save = async () => {
    const v = await form.validateFields()
    setSaving(true)
    try {
      if (editing === 'new') await createWarehouse(code, v)
      else if (editing) await updateWarehouse(code, editing.id, v)
      message.success('已儲存'); setEditing(null); load()
    } catch (e) { message.error(errMsg(e, '儲存失敗')) } finally { setSaving(false) }
  }

  const columns: ColumnsType<Warehouse> = [
    { title: '倉名', dataIndex: 'name', render: (v: string) => <b>{v}</b> },
    { title: '部門', dataIndex: 'department_name', render: (v: string | null) => v || <Text type="secondary">未指定</Text> },
    { title: '倉管', dataIndex: 'keeper_name', render: (v: string | null) => v || '—' },
    { title: '領用核准', dataIndex: 'issue_requires_approval', width: 90, render: (v: boolean) => (v ? <Tag color="gold">需核准</Tag> : '—') },
    { title: '狀態', dataIndex: 'status', width: 90, render: (v: string) => STATUS_TAG[v] ?? v },
    { title: '有庫存料號', dataIndex: 'item_count', width: 100, align: 'right' },
    { title: '庫存金額', dataIndex: 'amount', width: 120, align: 'right', render: money },
    { title: '備註', dataIndex: 'notes', ellipsis: true, render: (v: string | null) => v || '—' },
    ...(canManage ? [{ title: '', key: 'op', width: 60, render: (_: unknown, w: Warehouse) => (
      <Button size="small" type="text" icon={<EditOutlined />} disabled={w.status === 'counting'} onClick={() => open(w)} />) }] : []),
  ]
  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        {canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => open('new')}>新增倉庫</Button>}
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
        <Text type="secondary">每個「公司 × 部門」建議一個倉；有庫存的倉不能停用。</Text>
      </Space>
      <Table<Warehouse> size="small" rowKey="id" loading={loading} dataSource={rows} columns={columns} pagination={false} />
      <Modal open={!!editing} title={editing === 'new' ? '新增倉庫' : '修改倉庫'} onCancel={() => setEditing(null)}
        onOk={save} confirmLoading={saving} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="倉名" rules={[{ required: true, message: '請輸入倉名' }]}><Input maxLength={100} /></Form.Item>
          <Form.Item name="department_id" label="部門（公司/部門管理）">
            <Select allowClear showSearch optionFilterProp="label" options={depts.map((d) => ({ value: d.id, label: d.name }))} />
          </Form.Item>
          <Form.Item name="keeper_name" label="倉管人員"><Input maxLength={100} /></Form.Item>
          <Form.Item name="issue_requires_approval" label="領用需主管核准" valuePropName="checked"
            extra="開啟後，這個倉的領用單送出後要由該部門有「領用單：核准」權限的人核准，倉管才能發料（預設不需要）">
            <Switch />
          </Form.Item>
          <Form.Item name="status" label="狀態">
            <Select options={[{ value: 'active', label: '啟用' }, { value: 'inactive', label: '停用' }]} />
          </Form.Item>
          <Form.Item name="notes" label="備註"><Input.TextArea rows={2} /></Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ── 料號庫存設定 ──────────────────────────────────────────────────────────────
function ItemsTab({ code, canManage }: { code: string; canManage: boolean }) {
  const [rows, setRows] = useState<StockItem[]>([])
  const [categories, setCategories] = useState<{ id: number; label: string }[]>([])
  const [categoryId, setCategoryId] = useState<number | undefined>()
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<number[]>([])
  const [editing, setEditing] = useState<StockItem | null>(null)
  const [form] = Form.useForm<{ is_stock_item: boolean; purchase_unit: string; unit_ratio: number; abc_class: string }>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows((await fetchStockItems(code, { keyword: keyword.trim() || undefined, category_id: categoryId })).data)
      setSelected([])
    } catch (e) { message.error(errMsg(e, '讀取料號失敗')) } finally { setLoading(false) }
  }, [code, keyword, categoryId])
  useEffect(() => { fetchCategories(code).then((r) => setCategories(r.data)).catch(() => setCategories([])) }, [code])
  useEffect(() => { load() }, [code, categoryId]) // eslint-disable-line react-hooks/exhaustive-deps

  const bulk = async (is_stock_item: boolean, byCategory: boolean) => {
    try {
      const r = await bulkItemSetting(code, byCategory ? { category_id: categoryId, is_stock_item } : { item_ids: selected, is_stock_item })
      const skipped = r.data.skipped_with_stock
      message.success(`已更新 ${r.data.updated} 個料號${skipped.length ? `；${skipped.length} 個還有庫存未改：${skipped.slice(0, 5).join('、')}` : ''}`)
      load()
    } catch (e) { message.error(errMsg(e, '批次設定失敗')) }
  }
  const save = async () => {
    if (!editing) return
    const v = await form.validateFields()
    try {
      await updateItemSetting(code, editing.id, { ...v, purchase_unit: v.purchase_unit || null, abc_class: v.abc_class || null })
      message.success('已儲存'); setEditing(null); load()
    } catch (e) { message.error(errMsg(e, '儲存失敗')) }
  }

  const stockCount = rows.filter((r) => r.is_stock_item).length
  const columns: ColumnsType<StockItem> = [
    { title: '料號', dataIndex: 'item_code', width: 120 },
    { title: '品名', dataIndex: 'item_name', ellipsis: true },
    { title: '類別', dataIndex: 'category', width: 200, ellipsis: true, render: (v: string) => v || '—' },
    { title: '庫存單位', dataIndex: 'unit', width: 80, render: (v: string | null) => v || '—' },
    { title: '納入庫存', dataIndex: 'is_stock_item', width: 90, render: (v: boolean) => (v ? <Tag color="green">是</Tag> : <Tag>否</Tag>) },
    { title: '採購單位換算', key: 'ratio', width: 130,
      render: (_: unknown, r) => (r.purchase_unit ? `1 ${r.purchase_unit} ＝ ${r.unit_ratio} ${r.unit ?? ''}` : '—') },
    { title: '安全量', key: 'minmax', width: 90, render: (_: unknown, r) => (r.min_stock == null && r.max_stock == null ? '—' : `${r.min_stock ?? '—'}～${r.max_stock ?? '—'}`) },
    { title: '目前庫存', dataIndex: 'total_qty', width: 90, align: 'right', render: (v: number | null) => (v ? v.toLocaleString() : '—') },
    ...(canManage ? [{ title: '', key: 'op', width: 50, render: (_: unknown, r: StockItem) => (
      <Button size="small" type="text" icon={<EditOutlined />} onClick={() => {
        setEditing(r)
        form.setFieldsValue({ is_stock_item: r.is_stock_item, purchase_unit: r.purchase_unit ?? '', unit_ratio: r.unit_ratio, abc_class: r.abc_class ?? '' })
      }} />) }] : []),
  ]
  return (
    <>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        message="料號來自週採料號主檔；這裡只設定「是否納入庫存」與採購單位換算。安全量沿用料號主檔的最小／最大庫存量。未設定的料號預設納入庫存。" />
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select allowClear showSearch optionFilterProp="label" placeholder="類別" style={{ width: 260 }} value={categoryId} onChange={setCategoryId}
            options={categories.map((c) => ({ value: c.id, label: c.label }))} />
          <Input.Search allowClear placeholder="料號／品名／規格" style={{ width: 220 }} value={keyword} onChange={(e) => setKeyword(e.target.value)} onSearch={load} />
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
          <Text type="secondary">共 {rows.length} 個料號，納入庫存 {stockCount} 個</Text>
        </Space>
        {canManage && (
          <div style={{ marginTop: 8 }}>
            <Space wrap>
              <Text>已勾選 {selected.length} 個：</Text>
              <Button size="small" disabled={!selected.length} onClick={() => bulk(true, false)}>設為納入庫存</Button>
              <Button size="small" disabled={!selected.length} onClick={() => bulk(false, false)}>設為不納入</Button>
              <Text type="secondary">｜整個類別：</Text>
              <Popconfirm title="把這個類別的所有料號設為納入庫存？" disabled={!categoryId} onConfirm={() => bulk(true, true)}>
                <Button size="small" disabled={!categoryId}>類別全部納入</Button>
              </Popconfirm>
              <Popconfirm title="把這個類別的所有料號設為不納入庫存？（有庫存的會略過）" disabled={!categoryId} onConfirm={() => bulk(false, true)}>
                <Button size="small" disabled={!categoryId}>類別全部不納入</Button>
              </Popconfirm>
            </Space>
          </div>
        )}
      </Card>
      <Table<StockItem> size="small" rowKey="id" loading={loading} dataSource={rows} columns={columns}
        pagination={{ pageSize: 50, showSizeChanger: false }}
        rowSelection={canManage ? { selectedRowKeys: selected, onChange: (k) => setSelected(k as number[]) } : undefined} />
      <Modal open={!!editing} title={editing ? `料號庫存設定：${editing.item_code} ${editing.item_name}` : ''}
        onCancel={() => setEditing(null)} onOk={save} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="is_stock_item" label="納入庫存" valuePropName="checked"><Switch /></Form.Item>
          <Space>
            <Form.Item name="purchase_unit" label="採購單位（如：箱）"><Input maxLength={20} style={{ width: 140 }} /></Form.Item>
            <Form.Item name="unit_ratio" label={`1 採購單位＝幾個${editing?.unit ?? '庫存單位'}`} rules={[{ required: true }]}>
              <InputNumber min={0.0001} style={{ width: 160 }} />
            </Form.Item>
          </Space>
          <Form.Item name="abc_class" label="ABC 分類（循環盤點用，可空白）">
            <Select allowClear style={{ width: 120 }} options={['A', 'B', 'C'].map((v) => ({ value: v, label: v }))} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ── 期初開帳 ──────────────────────────────────────────────────────────────────
interface Line { key: number; item_id?: number; qty?: number; unit_cost?: number }

function OpeningTab({ code, canOpen, canManage }: { code: string; canOpen: boolean; canManage: boolean }) {
  const [rows, setRows] = useState<Opening[]>([])
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [items, setItems] = useState<StockItem[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [whId, setWhId] = useState<number | undefined>()
  const [whCheck, setWhCheck] = useState<{ allowed: boolean; reason: string } | null>(null)
  const [openDate, setOpenDate] = useState<Dayjs>(dayjs().endOf('month'))
  const [note, setNote] = useState('')
  const [lines, setLines] = useState<Line[]>([{ key: 1 }])
  const [saving, setSaving] = useState(false)
  const [detail, setDetail] = useState<Opening | null>(null)
  const [voiding, setVoiding] = useState<Opening | null>(null)
  const [voidReason, setVoidReason] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await fetchOpenings(code)).data) } catch (e) { message.error(errMsg(e, '讀取期初單失敗')) } finally { setLoading(false) }
  }, [code])
  useEffect(() => {
    load()
    fetchWarehouses(code).then((r) => setWarehouses(r.data)).catch(() => setWarehouses([]))
    fetchStockItems(code, { stock_only: true }).then((r) => setItems(r.data)).catch(() => setItems([]))
  }, [code, load])
  useEffect(() => {
    setWhCheck(null)
    if (whId) checkOpening(code, whId).then((r) => setWhCheck(r.data)).catch(() => setWhCheck(null))
  }, [code, whId])

  const itemMap = useMemo(() => new Map(items.map((i) => [i.id, i])), [items])
  const total = lines.reduce((s, l) => s + (l.qty ?? 0) * (l.unit_cost ?? 0), 0)
  const setLine = (key: number, patch: Partial<Line>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const startCreate = () => { setCreating(true); setWhId(undefined); setNote(''); setLines([{ key: Date.now() }]); setOpenDate(dayjs().endOf('month')) }
  const submit = async () => {
    const valid = lines.filter((l) => l.item_id && (l.qty ?? 0) > 0)
    if (!whId) { message.warning('請選擇倉庫'); return }
    if (!valid.length) { message.warning('請至少輸入一筆料號與數量'); return }
    setSaving(true)
    try {
      const r = await createOpening(code, {
        warehouse_id: whId, opening_date: openDate.format('YYYY-MM-DD'), note: note || undefined,
        lines: valid.map((l) => ({ item_id: l.item_id!, qty: l.qty!, unit_cost: l.unit_cost ?? 0 })),
      })
      message.success(`已過帳 ${r.data.doc_no}`); setCreating(false); load()
    } catch (e) { message.error(errMsg(e, '期初開帳失敗')) } finally { setSaving(false) }
  }
  const doVoid = async () => {
    if (!voiding || !voidReason.trim()) { message.warning('請填作廢原因'); return }
    try { await voidOpening(code, voiding.id, voidReason.trim()); message.success('已作廢'); setVoiding(null); setVoidReason(''); load() }
    catch (e) { message.error(errMsg(e, '作廢失敗')) }
  }
  const doRebuild = async () => {
    try {
      const r = await rebuildBalances(code)
      message.success(`已依異動帳重算 ${r.data.balances} 筆庫存${r.data.negative_points.length ? `（發現 ${r.data.negative_points.length} 個負庫存時點）` : ''}`)
    } catch (e) { message.error(errMsg(e, '重算失敗')) }
  }

  const columns: ColumnsType<Opening> = [
    { title: '單號', dataIndex: 'doc_no', width: 170, render: (v: string, r) => <a onClick={async () => setDetail((await fetchOpening(code, r.id)).data)}>{v}</a> },
    { title: '倉庫', dataIndex: 'warehouse_name' },
    { title: '期初日期', dataIndex: 'opening_date', width: 110 },
    { title: '料號數', dataIndex: 'line_count', width: 80, align: 'right' },
    { title: '金額', dataIndex: 'total_amount', width: 120, align: 'right', render: money },
    { title: '狀態', dataIndex: 'status', width: 90, render: (v: string) => (v === 'posted' ? <Tag color="green">已過帳</Tag> : <Tag>已作廢</Tag>) },
    { title: '建立', key: 'by', width: 170, render: (_: unknown, r) => `${r.created_by ?? ''} ${r.created_at ?? ''}` },
    ...(canOpen ? [{ title: '', key: 'op', width: 70, render: (_: unknown, r: Opening) => (r.status === 'posted'
      ? <Button size="small" danger type="link" onClick={() => setVoiding(r)}>作廢</Button> : null) }] : []),
  ]
  return (
    <>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        message="上線第一個月以月底盤點結果當期初（SPEC §8.7）。倉庫只要有期初以外的異動（進貨、領用…），就不能再開期初或作廢期初，之後只能用盤點調整。" />
      <Space style={{ marginBottom: 12 }}>
        {canOpen && <Button type="primary" icon={<PlusOutlined />} onClick={startCreate}>新增期初開帳單</Button>}
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
        {canManage && <Popconfirm title="依異動帳重新計算這家公司所有倉的庫存？（不改異動帳）" onConfirm={doRebuild}>
          <Button>重算庫存</Button></Popconfirm>}
      </Space>
      <Table<Opening> size="small" rowKey="id" loading={loading} dataSource={rows} columns={columns} pagination={{ pageSize: 20 }} />

      <Modal open={creating} title="新增期初開帳單（儲存即過帳）" width={860} onCancel={() => setCreating(false)}
        onOk={submit} okText="過帳" confirmLoading={saving} okButtonProps={{ disabled: whCheck?.allowed === false }} destroyOnClose>
        <Space wrap style={{ marginBottom: 12 }}>
          <Select placeholder="倉庫" style={{ width: 200 }} value={whId} onChange={setWhId}
            options={warehouses.filter((w) => w.status === 'active').map((w) => ({ value: w.id, label: w.name }))} />
          <DatePicker value={openDate} onChange={(d) => d && setOpenDate(d)} allowClear={false} />
          <Input placeholder="備註（例：2026-11 月底盤點）" style={{ width: 300 }} value={note} onChange={(e) => setNote(e.target.value)} />
        </Space>
        {whCheck && !whCheck.allowed && <Alert type="error" showIcon style={{ marginBottom: 12 }} message={`這個倉庫不能開期初：${whCheck.reason}`} />}
        <Table<Line> size="small" rowKey="key" pagination={false} dataSource={lines}
          columns={[
            { title: '料號', key: 'item', render: (_: unknown, l) => (
              <Select showSearch optionFilterProp="label" style={{ width: 360 }} value={l.item_id} placeholder="搜尋料號或品名"
                onChange={(v: number) => setLine(l.key, { item_id: v, unit_cost: l.unit_cost ?? (itemMap.get(v)?.unit_price ?? undefined) })}
                options={items.map((i) => ({ value: i.id, label: `${i.item_code} ${i.item_name}`,
                  disabled: lines.some((x) => x.key !== l.key && x.item_id === i.id) }))} />) },
            { title: '單位', key: 'unit', width: 60, render: (_: unknown, l) => (l.item_id ? itemMap.get(l.item_id)?.unit ?? '—' : '') },
            { title: '數量', key: 'qty', width: 120, render: (_: unknown, l) => (
              <InputNumber min={0} value={l.qty} onChange={(v) => setLine(l.key, { qty: v ?? undefined })} style={{ width: 110 }} />) },
            { title: '單價（未稅）', key: 'cost', width: 130, render: (_: unknown, l) => (
              <InputNumber min={0} value={l.unit_cost} onChange={(v) => setLine(l.key, { unit_cost: v ?? undefined })} style={{ width: 120 }} />) },
            { title: '金額', key: 'amt', width: 100, align: 'right', render: (_: unknown, l) => money((l.qty ?? 0) * (l.unit_cost ?? 0)) },
            { title: '', key: 'del', width: 40, render: (_: unknown, l) => (
              <Button size="small" type="text" icon={<DeleteOutlined />} disabled={lines.length === 1}
                onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))} />) },
          ]} />
        <Space style={{ marginTop: 8 }}>
          <Button icon={<PlusOutlined />} onClick={() => setLines((ls) => [...ls, { key: Date.now() }])}>加一列</Button>
          <Text>合計 <b>{money(total)}</b></Text>
          <Text type="secondary">單價預設帶料號主檔參考單價</Text>
        </Space>
      </Modal>

      <Modal open={!!voiding} title={voiding ? `作廢期初單 ${voiding.doc_no}` : ''} onCancel={() => setVoiding(null)} onOk={doVoid} okText="作廢" okButtonProps={{ danger: true }}>
        <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="作廢會產生反向異動，把這張單的數量全部扣回。" />
        <Input.TextArea rows={3} placeholder="作廢原因（必填）" value={voidReason} onChange={(e) => setVoidReason(e.target.value)} />
      </Modal>

      <Drawer open={!!detail} width={640} onClose={() => setDetail(null)}
        title={detail ? <Space><Tag color={detail.status === 'posted' ? 'green' : 'default'}>{detail.status === 'posted' ? '已過帳' : '已作廢'}</Tag><span>{`期初開帳：${detail.doc_no}`}</span></Space> : ''}>
        {detail && (
          <>
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="倉庫">{detail.warehouse_name}</Descriptions.Item>
              <Descriptions.Item label="期初日期">{detail.opening_date}</Descriptions.Item>
              <Descriptions.Item label="金額"><b>{money(detail.total_amount)}</b></Descriptions.Item>
              <Descriptions.Item label="備註">{detail.note || '—'}</Descriptions.Item>
              <Descriptions.Item label="建立">{`${detail.created_by ?? ''} ${detail.created_at ?? ''}`}</Descriptions.Item>
              {detail.status === 'voided' && <Descriptions.Item label="作廢">{`${detail.voided_by ?? ''}：${detail.void_reason ?? ''}`}</Descriptions.Item>}
            </Descriptions>
            <Table size="small" rowKey="item_id" pagination={false} dataSource={detail.lines ?? []}
              columns={[
                { title: '料號', dataIndex: 'item_code', width: 110 },
                { title: '品名', dataIndex: 'item_name' },
                { title: '數量', dataIndex: 'qty', width: 80, align: 'right', render: (v: number, l) => `${v} ${l.unit ?? ''}` },
                { title: '單價', dataIndex: 'unit_cost', width: 90, align: 'right', render: money },
                { title: '金額', dataIndex: 'amount', width: 100, align: 'right', render: money },
              ]} />
          </>
        )}
      </Drawer>
    </>
  )
}

export default function StockSettingsPage() {
  const { companies, code, setCode, error } = useStockCompany()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canManage = hasPermission('stock_settings_manage')
  const canOpen = hasPermission('stock_opening_manage')
  if (error) return <Alert type="error" showIcon message={error} />
  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <StockCompanySelect companies={companies} value={code} onChange={setCode} />
        <Text type="secondary">庫存資料依公司分開，切換公司後各 TAB 重新讀取</Text>
      </Space>
      {code && (
        <Tabs key={code} items={[
          { key: 'wh', label: '倉庫', children: <WarehousesTab code={code} canManage={canManage} /> },
          { key: 'items', label: '料號庫存設定', children: <ItemsTab code={code} canManage={canManage} /> },
          { key: 'opening', label: '期初開帳', children: <OpeningTab code={code} canOpen={canOpen} canManage={canManage} /> },
        ]} />
      )}
    </div>
  )
}
