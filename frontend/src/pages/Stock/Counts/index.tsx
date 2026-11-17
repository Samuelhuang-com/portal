/**
 * 庫存管理 › 盤點（規格 docs/SPEC_stock_management.md §9，Phase 5 2026-11-17；桌面版，離線手機盤點待 D10 HTTPS）
 *
 * 流程：審核者「產生盤點表」（一倉一張，凍結帳面數、倉庫進入盤點中暫停過帳 D7）
 *   → 盤點人逐項輸入實盤數（盲盤 D8：看不到帳面數；可加入清單外料號）→ 送出
 *   → 審核者看差異（超過 5% 或 1,000 元標「建議複盤」）：退回重盤（可只清指定料號）或核准（寫盤盈虧、倉庫恢復）
 * 權限：stock_count_execute（限所屬部門的倉）、stock_count_review（產生、審核、取消；全部倉）
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Checkbox, DatePicker, Descriptions, Drawer, Input, InputNumber, Modal, Popconfirm, Radio, Select, Space, Switch,
  Table, Tag, Tooltip, Typography, message,
} from 'antd'
import { DownloadOutlined, PlusOutlined, ReloadOutlined, SaveOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import {
  addCountItem, approveCount, cancelCount, createCounts, errMsg, fetchCount, fetchCounts, fetchWarehouses, returnCount,
  saveCountEntries, searchCountItems, submitCount,
  type StockCountLineRow, type StockCountRow, type Warehouse,
} from '@/api/stock'
import { useAuthStore } from '@/stores/authStore'
import { exportRowsToExcel } from '@/utils/exportExcel'
import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'

const { Text } = Typography
const money = (v: number | null | undefined) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)
const num = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: 4 }))
const STATUS_COLOR: Record<string, string> = { counting: 'orange', submitted: 'gold', approved: 'green', cancelled: 'default' }
const STATUS_OPTIONS = [
  { value: 'counting', label: '盤點中' }, { value: 'submitted', label: '待審核' },
  { value: 'approved', label: '已核准' }, { value: 'cancelled', label: '已取消' },
]

// ── 產生盤點表 ────────────────────────────────────────────────────────────────
function CreateModal({ code, open, onClose, onDone }: { code: string; open: boolean; onClose: () => void; onDone: () => void }) {
  const [whs, setWhs] = useState<Warehouse[]>([])
  const [ids, setIds] = useState<number[]>([])
  const [date, setDate] = useState<Dayjs>(dayjs())
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [mode, setMode] = useState<'full' | 'cycle'>('full')
  const [abc, setAbc] = useState<string[]>(['A'])
  useEffect(() => {
    if (!open) return
    setDate(dayjs()); setNote(''); setMode('full'); setAbc(['A'])
    fetchWarehouses(code).then((r) => {
      const ok = r.data.filter((w) => w.status === 'active')
      setWhs(r.data); setIds(ok.filter((w) => w.has_moves).map((w) => w.id))
    }).catch((e) => message.error(errMsg(e, '讀取倉庫失敗')))
  }, [open, code])
  const save = async () => {
    if (!ids.length) { message.warning('請選倉庫'); return }
    if (mode === 'cycle' && !abc.length) { message.warning('循環盤點請選 ABC 類別'); return }
    setSaving(true)
    try {
      const r = await createCounts(code, { warehouse_ids: ids, count_date: date.format('YYYY-MM-DD'), note: note || null,
        abc_classes: mode === 'cycle' ? abc : null })
      if (r.data.created.length) message.success(`已產生 ${r.data.created.length} 張盤點表：${r.data.created.map((c) => c.count_no).join('、')}`)
      if (r.data.errors.length) Modal.warning({ title: '部分倉庫沒有產生', content: r.data.errors.join('\n') })
      onDone()
    } catch (e) { message.error(errMsg(e, '產生失敗')) } finally { setSaving(false) }
  }
  return (
    <Modal open={open} title="產生盤點表" onCancel={onClose} onOk={save} confirmLoading={saving} okText="產生" width={560}>
      <Alert type="warning" showIcon style={{ marginBottom: 12 }}
        message="產生後倉庫進入「盤點中」：不能開領用單、不能進貨入庫、不能調撥，直到盤點核准或取消。" />
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)} optionType="button"
            options={[{ value: 'full', label: '月底全盤' }, { value: 'cycle', label: '循環盤點（抽盤）' }]} />
          {mode === 'cycle' && <Checkbox.Group value={abc} onChange={(v) => setAbc(v as string[])} options={['A', 'B', 'C'].map((x) => ({ value: x, label: `${x} 類` }))} />}
        </Space>
        {mode === 'cycle' && <Text type="secondary">循環盤點只盤選定 ABC 類的料號（在「庫存主檔設定 › 料號庫存設定」設定），屬於額外抽盤，月結仍需月底全盤。</Text>}
        <Space><Text>盤點日</Text><DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} /></Space>
        <Text type="secondary">盤盈虧異動以盤點日入帳，並算在盤點日所屬月份的月結。</Text>
        <Select mode="multiple" style={{ width: '100%' }} placeholder="選擇倉庫（預設已勾有異動的倉）" value={ids} onChange={setIds}
          options={whs.map((w) => ({ value: w.id, disabled: w.status !== 'active',
            label: `${w.name}${w.department_name ? `（${w.department_name}）` : ''}${w.status === 'counting' ? '｜盤點中' : ''}` }))} />
        <Input placeholder="備註（選填）" value={note} onChange={(e) => setNote(e.target.value)} />
      </Space>
    </Modal>
  )
}

// ── 盤點表明細 ────────────────────────────────────────────────────────────────
type Edit = { qty?: number | null; note?: string }

function CountDrawer({ code, id, onClose, onChanged }: { code: string; id: number | null; onClose: () => void; onChanged: () => void }) {
  const [doc, setDoc] = useState<StockCountRow | null>(null)
  const [edits, setEdits] = useState<Record<number, Edit>>({})
  const [keyword, setKeyword] = useState('')
  const [onlyTodo, setOnlyTodo] = useState(false)
  const [onlyDiff, setOnlyDiff] = useState(false)
  const [busy, setBusy] = useState(false)
  const [fillZero, setFillZero] = useState(false)
  const [retOpen, setRetOpen] = useState(false)
  const [retReason, setRetReason] = useState('')
  const [retIds, setRetIds] = useState<number[]>([])
  const [search, setSearch] = useState<{ value: number; label: string }[]>([])

  const load = useCallback(async () => {
    if (!id) return
    try { setDoc((await fetchCount(code, id)).data); setEdits({}) } catch (e) { message.error(errMsg(e, '讀取盤點表失敗')) }
  }, [code, id])
  useEffect(() => { setDoc(null); setKeyword(''); setOnlyTodo(false); setOnlyDiff(false); setFillZero(false); load() }, [load])

  const dirty = Object.keys(edits).length
  const review = !!doc?.can_review || doc?.status === 'approved'
  const rows = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return (doc?.lines ?? []).filter((l) => {
      if (kw && !`${l.item_code} ${l.item_name} ${l.spec ?? ''}`.toLowerCase().includes(kw)) return false
      const q = edits[l.item_id]?.qty !== undefined ? edits[l.item_id].qty : l.counted_qty
      if (onlyTodo && q != null) return false
      if (onlyDiff && !(l.diff_qty)) return false
      return true
    })
  }, [doc, keyword, onlyTodo, onlyDiff, edits])

  const save = async (silent = false) => {
    if (!doc || !dirty) return true
    setBusy(true)
    try {
      const entries = Object.entries(edits).map(([k, v]) => ({
        item_id: Number(k),
        counted_qty: v.qty !== undefined ? v.qty ?? null : (doc.lines?.find((l) => l.item_id === Number(k))?.counted_qty ?? null),
        note: v.note ?? null,
      }))
      await saveCountEntries(code, doc.id, entries)
      if (!silent) message.success(`已儲存 ${entries.length} 項`)
      await load(); onChanged()
      return true
    } catch (e) { message.error(errMsg(e, '儲存失敗')); return false } finally { setBusy(false) }
  }
  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    try { await fn(); message.success(ok); await load(); onChanged() } catch (e) { message.error(errMsg(e, '操作失敗')) } finally { setBusy(false) }
  }
  const doSubmit = async () => { if (await save(true)) act(() => submitCount(code, doc!.id, fillZero), '已送出，等待審核') }
  const doReturn = async () => {
    if (!retReason.trim()) { message.warning('請填退回原因'); return }
    await act(() => returnCount(code, doc!.id, retReason.trim(), retIds), '已退回重盤'); setRetOpen(false)
  }
  const onSearch = async (kw: string) => {
    if (!doc || !kw.trim()) { setSearch([]); return }
    try {
      const r = await searchCountItems(code, doc.id, kw.trim())
      setSearch(r.data.map((x) => ({ value: x.item_id, label: `${x.item_code} ${x.item_name}${x.spec ? `（${x.spec}）` : ''}` })))
    } catch { setSearch([]) }
  }
  const exportSheet = () => {
    if (!doc) return
    exportRowsToExcel((doc.lines ?? []).map((l) => ({
      料號: l.item_code, 品名: l.item_name, 規格: l.spec ?? '', 單位: l.unit ?? '',
      ...(doc.show_book ? { 帳面數: l.book_qty ?? '' } : {}),
      實盤數: l.counted_qty ?? '', 備註: l.note ?? '',
    })), { filename: `盤點表_${doc.count_no}_${doc.warehouse_name}.xlsx`, sheetName: doc.count_no, colWidths: [14, 28, 18, 8, 10, 10, 20] })
  }

  const cols: ColumnsType<StockCountLineRow> = [
    { title: '料號', dataIndex: 'item_code', width: 110 },
    { title: '品名', key: 'name', render: (_: unknown, l) => (
      <Space size={4}>{`${l.item_name}${l.spec ? `（${l.spec}）` : ''}`}{l.added_manually && <Tag>盤點加入</Tag>}</Space>) },
    { title: '單位', dataIndex: 'unit', width: 60 },
    ...(doc?.show_book ? [{ title: '帳面數', dataIndex: 'book_qty', width: 90, align: 'right' as const, render: num }] : []),
    { title: '實盤數', key: 'qty', width: 130, render: (_: unknown, l) => {
      const e = edits[l.item_id]
      const v = e?.qty !== undefined ? e.qty : l.counted_qty
      if (!doc?.can_input) return <b>{num(l.counted_qty)}</b>
      return <InputNumber min={0} value={v ?? null} style={{ width: 110, background: e?.qty !== undefined ? '#fffbe6' : undefined }}
        onChange={(x) => setEdits((s) => ({ ...s, [l.item_id]: { ...s[l.item_id], qty: x } }))} />
    } },
    ...(review ? [
      { title: '差異', key: 'diff', width: 90, align: 'right' as const, render: (_: unknown, l: StockCountLineRow) =>
        (l.diff_qty == null ? '—' : <Text type={l.diff_qty < 0 ? 'danger' : l.diff_qty > 0 ? 'success' : undefined}>{l.diff_qty > 0 ? `+${num(l.diff_qty)}` : num(l.diff_qty)}</Text>) },
      { title: '差異金額', dataIndex: 'diff_amount', width: 110, align: 'right' as const, render: money },
      { title: '', key: 'rc', width: 80, render: (_: unknown, l: StockCountLineRow) =>
        (l.needs_recount && doc?.status !== 'approved' ? <Tooltip title="差異超過 5% 或 1,000 元"><Tag color="red">建議複盤</Tag></Tooltip> : null) },
    ] : []),
    { title: '盤點人', dataIndex: 'counted_by', width: 90, render: (v: string | null) => v || '—' },
    { title: '備註', key: 'note', width: 160, render: (_: unknown, l) => (doc?.can_input
      ? <Input size="small" value={edits[l.item_id]?.note ?? l.note ?? ''}
          onChange={(e) => setEdits((s) => ({ ...s, [l.item_id]: { ...s[l.item_id], note: e.target.value } }))} />
      : l.note || '—') },
  ]

  return (
    <Drawer open={!!id} width={1080} onClose={() => { if (dirty && !window.confirm('有尚未儲存的實盤數，確定離開？')) return; onClose() }}
      title={doc ? (
        <Space>
          <Tag color="blue">盤點表</Tag><span>{`${doc.warehouse_name}：${doc.count_no}`}</span>
          <Tag color={STATUS_COLOR[doc.status]}>{doc.status_label}</Tag>{doc.blind && <Tag>盲盤</Tag>}
          {doc.count_type === 'cycle' && <Tag color="purple">{`循環盤點 ${doc.abc_classes ?? ''}`}</Tag>}
        </Space>) : ''}
      extra={doc && (
        <Space>
          <Button icon={<DownloadOutlined />} onClick={exportSheet}>匯出 Excel</Button>
          {doc.can_input && <Button icon={<SaveOutlined />} type={dirty ? 'primary' : 'default'} disabled={!dirty} loading={busy}
            onClick={() => save()}>{`儲存${dirty ? `（${dirty}）` : ''}`}</Button>}
          {doc.can_input && (
            <Popconfirm title={<Space direction="vertical"><span>送出給主管審核？</span>
              <Checkbox checked={fillZero} onChange={(e) => setFillZero(e.target.checked)}>未盤的料號視為 0</Checkbox></Space>}
              onConfirm={doSubmit}>
              <Button type="primary" loading={busy}>送出</Button>
            </Popconfirm>)}
          {doc.can_review && <Button danger onClick={() => { setRetReason(''); setRetIds((doc.lines ?? []).filter((l) => l.needs_recount).map((l) => l.item_id)); setRetOpen(true) }}>退回重盤</Button>}
          {doc.can_review && (
            <Popconfirm title="核准後依差異寫盤盈虧並恢復倉庫，確定？" onConfirm={() => act(() => approveCount(code, doc.id), '已核准，盤盈虧已入帳')}>
              <Button type="primary" loading={busy}>核准盤盈虧</Button>
            </Popconfirm>)}
          {doc.can_cancel && (
            <Popconfirm title="取消盤點？不寫任何異動，倉庫恢復啟用" onConfirm={() => act(() => cancelCount(code, doc.id), '已取消')}>
              <Button danger type="text">取消盤點</Button>
            </Popconfirm>)}
        </Space>)}>
      {doc && (
        <>
          <Descriptions size="small" column={4} bordered style={{ marginBottom: 12 }}>
            <Descriptions.Item label="盤點日">{doc.count_date}</Descriptions.Item>
            <Descriptions.Item label="帳面凍結">{doc.cutoff_at}</Descriptions.Item>
            <Descriptions.Item label="進度">{`${doc.counted_count ?? 0} ／ ${doc.line_count}`}</Descriptions.Item>
            <Descriptions.Item label="建立">{doc.created_by ?? '—'}</Descriptions.Item>
            {doc.status === 'approved' && <>
              <Descriptions.Item label="差異品項">{doc.diff_count}</Descriptions.Item>
              <Descriptions.Item label="盤盈">{money(doc.gain_amount)}</Descriptions.Item>
              <Descriptions.Item label="盤虧">{money(doc.loss_amount)}</Descriptions.Item>
              <Descriptions.Item label="核准">{`${doc.approved_by ?? ''} ${doc.approved_at ?? ''}`}</Descriptions.Item>
            </>}
            {doc.close_reason && <Descriptions.Item label="退回／取消" span={4}>{`${doc.closed_by ?? ''}：${doc.close_reason}`}</Descriptions.Item>}
          </Descriptions>
          {doc.blind && !doc.show_book && <Alert type="info" showIcon style={{ marginBottom: 12 }} message="盲盤：請照實際數量填寫，帳面數與差異由主管在審核時查看。" />}
          <Space wrap style={{ marginBottom: 8 }}>
            <Input.Search allowClear placeholder="料號／品名" style={{ width: 220 }} value={keyword} onChange={(e) => setKeyword(e.target.value)} />
            <Space size={4}><Switch size="small" checked={onlyTodo} onChange={setOnlyTodo} /><span>只看未盤</span></Space>
            {review && <Space size={4}><Switch size="small" checked={onlyDiff} onChange={setOnlyDiff} /><span>只看有差異</span></Space>}
            {doc.can_input && (
              <Select showSearch filterOption={false} placeholder="加入清單外料號" style={{ width: 280 }} value={null}
                suffixIcon={<PlusOutlined />} onSearch={onSearch} options={search} notFoundContent="輸入料號或品名搜尋"
                onChange={(v: number) => act(() => addCountItem(code, doc.id, v), '已加入')} />)}
          </Space>
          <Table<StockCountLineRow> size="small" rowKey="id" dataSource={rows} columns={cols} pagination={{ pageSize: 100 }} scroll={{ y: 560 }} />
        </>
      )}
      <Modal open={retOpen} title="退回重盤" onCancel={() => setRetOpen(false)} onOk={doReturn} okText="退回" okButtonProps={{ danger: true }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input.TextArea rows={2} placeholder="退回原因（必填）" value={retReason} onChange={(e) => setRetReason(e.target.value)} />
          <Text type="secondary">要重盤的料號（會清掉實盤數；不選＝保留全部已盤數，只讓盤點人修改）</Text>
          <Select mode="multiple" style={{ width: '100%' }} value={retIds} onChange={setRetIds}
            options={(doc?.lines ?? []).map((l) => ({ value: l.item_id, label: `${l.item_code} ${l.item_name}${l.needs_recount ? '（建議複盤）' : ''}` }))} />
        </Space>
      </Modal>
    </Drawer>
  )
}

// ── 主頁 ─────────────────────────────────────────────────────────────────────
export default function StockCountsPage() {
  const { companies, code, setCode, error } = useStockCompany()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canReview = hasPermission('stock_count_review')
  const [rows, setRows] = useState<StockCountRow[]>([])
  const [loading, setLoading] = useState(false)
  const [period, setPeriod] = useState<Dayjs | null>(null)
  const [status, setStatus] = useState<string[]>([])
  const [createOpen, setCreateOpen] = useState(false)
  const [openId, setOpenId] = useState<number | null>(null)

  const load = useCallback(async () => {
    if (!code) return
    setLoading(true)
    try {
      setRows((await fetchCounts(code, { period: period?.format('YYYY-MM'), status: status.length ? status : undefined })).data)
    } catch (e) { message.error(errMsg(e, '讀取盤點表失敗')) } finally { setLoading(false) }
  }, [code, period, status])
  useEffect(() => { load() }, [load])

  if (error) return <Alert type="error" showIcon message={error} />
  return (
    <div>
      <Space wrap style={{ marginBottom: 12 }}>
        <StockCompanySelect companies={companies} value={code} onChange={setCode} />
        <DatePicker picker="month" placeholder="全部月份" value={period} onChange={setPeriod} />
        <Select mode="multiple" allowClear placeholder="狀態" style={{ minWidth: 200 }} value={status} onChange={setStatus} options={STATUS_OPTIONS} />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新讀取</Button>
        {canReview && <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>產生盤點表</Button>}
      </Space>
      <Table<StockCountRow> size="small" rowKey="id" loading={loading} dataSource={rows} pagination={{ pageSize: 30 }}
        onRow={(r) => ({ onClick: () => setOpenId(r.id), style: { cursor: 'pointer' } })}
        columns={[
          { title: '盤點單號', dataIndex: 'count_no', width: 170 },
          { title: '倉庫', dataIndex: 'warehouse_name' },
          { title: '盤點日', dataIndex: 'count_date', width: 100 },
          { title: '進度', key: 'p', width: 100, render: (_: unknown, r) => `${r.counted_count ?? 0} ／ ${r.line_count}` },
          { title: '狀態', key: 's', width: 190, render: (_: unknown, r) => (
            <Space size={2} wrap><Tag color={STATUS_COLOR[r.status]}>{r.status_label}</Tag>{r.blind && <Tag>盲盤</Tag>}
              {r.count_type === 'cycle' && <Tag color="purple">{`循環 ${r.abc_classes ?? ''}`}</Tag>}</Space>) },
          ...(canReview ? [
            { title: '盤盈', dataIndex: 'gain_amount', width: 100, align: 'right' as const, render: (v: number | null, r: StockCountRow) => (r.status === 'approved' ? money(v) : '—') },
            { title: '盤虧', dataIndex: 'loss_amount', width: 100, align: 'right' as const, render: (v: number | null, r: StockCountRow) => (r.status === 'approved' ? money(v) : '—') },
          ] : []),
          { title: '建立', key: 'c', width: 170, render: (_: unknown, r) => `${r.created_by ?? ''} ${r.created_at ?? ''}` },
        ]} />
      {code && <CreateModal code={code} open={createOpen} onClose={() => setCreateOpen(false)} onDone={() => { setCreateOpen(false); load() }} />}
      {code && <CountDrawer code={code} id={openId} onClose={() => setOpenId(null)} onChanged={load} />}
    </div>
  )
}
