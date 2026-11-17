/**
 * 庫存管理 › 進貨匯入（規格 docs/SPEC_stock_management.md §6，Phase 3 2026-11-17）
 *
 * TAB「待匯入清單」：Ragic 採購單／請款單品項（每一筆都要人工確認才入庫）
 *   - 重新整理：依 Ragic 已同步資料重新產生清單（來源被改／退回會標「來源已異動」，不自動扣庫存，D18）
 *     2026-11-17 D36：採購單／請款單同步成功後會自動跑一次（stock_import_service.refresh_after_sync），按鈕保留給手動更新
 *   - 勾選 → 確認入庫：選料號（品名對照＋相似度建議）、實收量、單位換算、入庫倉 → 產生進貨單並過帳
 *   - 標記不入庫／開帳前不入庫（D19 可依日期整批）
 * TAB「不入庫」：確認不入庫／開帳前不入庫／已對應採購單的 Ragic 品項（2026-11-17 從待匯入清單拆出），可改回待確認
 * TAB「進貨單」：已過帳的進貨單，可作廢（反向異動、回補可匯入量）
 * 每列可直接「確認入庫」「確認不入庫」「開帳前」（2026-11-17），也可勾選多筆批次處理
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Col, DatePicker, Descriptions, Drawer, Image, Input, InputNumber, Modal, Popconfirm, Row, Select,
  Space, Statistic, Switch, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  CheckCircleOutlined, CheckOutlined, FieldTimeOutlined, FileOutlined, FilePdfOutlined, LinkOutlined, PaperClipOutlined,
  ReloadOutlined, RollbackOutlined, StopOutlined, SyncOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import StandardRangePicker, { type StandardRange } from '@/components/StandardRangePicker'
import {
  ackChange, createReceipt, errMsg, fetchImport, fetchImports, fetchReceipt, fetchReceiptSummary, fetchReceipts,
  fetchStockItems, fetchWarehouses, markBefore, markImports, refreshImports, suggestItems, voidReceipt,
  type ImportAttachment, type ImportLine, type ImportListResp, type ItemSuggestion, type Receipt, type ReceiptSummary, type StockItem, type Warehouse,
} from '@/api/stock'
import { useAuthStore } from '@/stores/authStore'
import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'

const { Text } = Typography
const money = (v: number | null | undefined) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)
const num = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: 4 }))
const STATUS_COLOR: Record<string, string> = {
  pending: 'blue', partial: 'cyan', done: 'green', non_stock: 'default', pre_opening: 'default', linked_po: 'purple',
}
const STATUS_OPTIONS = [
  { value: 'pending', label: '待確認' }, { value: 'partial', label: '部分匯入' }, { value: 'done', label: '已匯入' },
  { value: 'non_stock', label: '不入庫' }, { value: 'pre_opening', label: '開帳前不入庫' }, { value: 'linked_po', label: '已對應採購單' },
]
const OPEN = ['pending', 'partial']
const CLOSED = ['non_stock', 'pre_opening', 'linked_po']
const REVERTIBLE = ['non_stock', 'pre_opening']
type ImportMode = 'open' | 'closed'

// ── 確認入庫 Modal ────────────────────────────────────────────────────────────
interface ConfirmRow {
  line: ImportLine
  item_id?: number
  purchase_qty?: number
  unit_ratio: number
  unit_price?: number | null
  override_reason?: string
  remember_ratio: boolean
  suggestions: ItemSuggestion[]
}

function ConfirmModal({ code, lines, open, onClose, onDone }: {
  code: string; lines: ImportLine[]; open: boolean; onClose: () => void; onDone: () => void
}) {
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [items, setItems] = useState<StockItem[]>([])
  const [whId, setWhId] = useState<number | undefined>()
  const [date, setDate] = useState<Dayjs>(dayjs())
  const [note, setNote] = useState('')
  const [rows, setRows] = useState<ConfirmRow[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setDate(dayjs()); setNote('')
    Promise.all([fetchWarehouses(code), fetchStockItems(code, { stock_only: true })]).then(([w, it]) => {
      const active = w.data.filter((x) => x.status === 'active')
      setWarehouses(active); setItems(it.data)
      const dept = lines[0]?.department ?? ''
      const guess = active.find((x) => x.department_name && dept && (x.department_name === dept || dept.includes(x.department_name) || x.department_name.includes(dept)))
        ?? active.find((x) => dept && x.name.includes(dept.replace(/部$/, '')))
      setWhId(guess?.id)
    }).catch((e) => message.error(errMsg(e, '讀取倉庫／料號失敗')))
    const init = lines.map((l) => ({
      line: l, purchase_qty: l.remaining_qty ?? undefined, unit_ratio: 1, unit_price: l.unit_price,
      remember_ratio: false, suggestions: [] as ItemSuggestion[],
    }))
    setRows(init)
    lines.forEach((l, idx) => {
      suggestItems(code, l.id).then((r) => {
        setRows((rs) => rs.map((x, i) => {
          if (i !== idx) return x
          const top = r.data[0]
          const auto = top && top.score >= 0.999 ? top : undefined
          return {
            ...x, suggestions: r.data, item_id: auto?.item_id,
            unit_ratio: auto && auto.purchase_unit && auto.purchase_unit === l.unit ? auto.unit_ratio : x.unit_ratio,
          }
        }))
      }).catch(() => undefined)
    })
  }, [open, code, lines])

  const itemMap = useMemo(() => new Map(items.map((i) => [i.id, i])), [items])
  const setRow = (idx: number, patch: Partial<ConfirmRow>) => setRows((rs) => rs.map((r, i) => (i === idx ? { ...r, ...patch } : r)))
  const total = rows.reduce((s, r) => s + (r.purchase_qty ?? 0) * (r.unit_price ?? 0), 0)

  const submit = async () => {
    if (!whId) { message.warning('請選擇入庫倉'); return }
    const bad = rows.find((r) => !r.item_id || !r.purchase_qty || r.purchase_qty <= 0)
    if (bad) { message.warning(`「${bad.line.product_name ?? ''}」請選料號並輸入實收數量`); return }
    setSaving(true)
    try {
      const res = await createReceipt(code, {
        warehouse_id: whId, receipt_date: date.format('YYYY-MM-DD'), note: note || undefined,
        lines: rows.map((r) => ({
          import_line_id: r.line.id, item_id: r.item_id!, purchase_qty: r.purchase_qty!, unit_ratio: r.unit_ratio || 1,
          unit_price: r.unit_price ?? null, override_reason: r.override_reason || null, remember_alias: true,
          remember_ratio: r.remember_ratio,
        })),
      })
      message.success(`已入庫：${res.data.receipt_no}（${money(res.data.total_amount)}）`)
      onDone()
    } catch (e) {
      message.error(errMsg(e, '入庫失敗'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} title={`確認入庫（${lines.length} 筆）`} width={1180} onCancel={onClose} onOk={submit} okText="過帳入庫"
      confirmLoading={saving} destroyOnClose>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select placeholder="入庫倉" style={{ width: 220 }} value={whId} onChange={setWhId}
          options={warehouses.map((w) => ({ value: w.id, label: w.department_name ? `${w.name}（${w.department_name}）` : w.name }))} />
        <DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} />
        <Input placeholder="備註" style={{ width: 300 }} value={note} onChange={(e) => setNote(e.target.value)} />
        <Text>合計（未稅）<b>{money(total)}</b></Text>
      </Space>
      {warehouses.length === 0 && <Alert type="warning" showIcon style={{ marginBottom: 8 }} message="這家公司沒有啟用中的倉庫，請先到「庫存主檔設定」建立。" />}
      <Table<ConfirmRow> size="small" rowKey={(r) => r.line.id} pagination={false} dataSource={rows} scroll={{ y: 460 }}
        columns={[
          { title: 'Ragic 品項', key: 'src', width: 230, render: (_: unknown, r) => (
            <Space direction="vertical" size={0}>
              <span>{r.line.product_name || '—'}</span>
              <Text type="secondary" style={{ fontSize: 12 }}>{r.line.source_label} {r.line.doc_no}</Text>
              {r.line.suspected_po_no && <Tag color="orange">疑似採購單 {r.line.suspected_po_no}</Tag>}
            </Space>) },
          { title: '料號', key: 'item', width: 300, render: (_: unknown, r, idx) => {
            const sugIds = new Set(r.suggestions.map((s) => s.item_id))
            return (
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Select showSearch optionFilterProp="label" style={{ width: 290 }} placeholder="選擇料號" value={r.item_id}
                  onChange={(v: number) => {
                    const sg = r.suggestions.find((s) => s.item_id === v)
                    const it = itemMap.get(v)
                    const pu = sg?.purchase_unit ?? it?.purchase_unit
                    const ratio = sg?.unit_ratio ?? it?.unit_ratio ?? 1
                    setRow(idx, { item_id: v, unit_ratio: pu && pu === r.line.unit ? ratio : r.unit_ratio })
                  }}
                  options={[
                    ...(r.suggestions.length ? [{ label: '建議', options: r.suggestions.map((s) => ({
                      value: s.item_id, label: `${s.item_code} ${s.item_name}（${s.reason}${s.score < 1 ? ` ${Math.round(s.score * 100)}%` : ''}）` })) }] : []),
                    { label: '全部料號', options: items.filter((i) => !sugIds.has(i.id)).map((i) => ({ value: i.id, label: `${i.item_code} ${i.item_name}` })) },
                  ]} />
                {r.item_id && <Text type="secondary" style={{ fontSize: 12 }}>庫存單位：{itemMap.get(r.item_id)?.unit ?? '—'}</Text>}
              </Space>)
          } },
          { title: '實收', key: 'qty', width: 150, render: (_: unknown, r, idx) => (
            <Space direction="vertical" size={0}>
              <InputNumber min={0} value={r.purchase_qty} onChange={(v) => setRow(idx, { purchase_qty: v ?? undefined })} style={{ width: 100 }}
                addonAfter={r.line.unit || undefined} />
              <Text type="secondary" style={{ fontSize: 12 }}>剩 {num(r.line.remaining_qty)}（原單 {r.line.qty_raw ?? '—'}）</Text>
            </Space>) },
          { title: '換算', key: 'ratio', width: 150, render: (_: unknown, r, idx) => (
            <Space direction="vertical" size={0}>
              <InputNumber min={0.0001} value={r.unit_ratio} onChange={(v) => setRow(idx, { unit_ratio: v ?? 1 })} style={{ width: 90 }} />
              <Checkbox checked={r.remember_ratio} onChange={(e) => setRow(idx, { remember_ratio: e.target.checked })}>記住換算</Checkbox>
            </Space>) },
          { title: '入庫數量', key: 'stock', width: 90, align: 'right', render: (_: unknown, r) =>
            <b>{num((r.purchase_qty ?? 0) * (r.unit_ratio || 1))}</b> },
          { title: '單價（未稅）', key: 'price', width: 120, render: (_: unknown, r, idx) => (
            <InputNumber min={0} value={r.unit_price ?? undefined} placeholder="空白＝參考價" onChange={(v) => setRow(idx, { unit_price: v ?? null })} style={{ width: 110 }} />) },
          { title: '疑似重複理由', key: 'ov', width: 150, render: (_: unknown, r, idx) => (r.line.suspected_po_no
            ? <Input size="small" placeholder="確認不是同一批貨" value={r.override_reason} onChange={(e) => setRow(idx, { override_reason: e.target.value })} />
            : <Text type="secondary">—</Text>) },
        ]} />
      <Text type="secondary" style={{ fontSize: 12 }}>確認後「Ragic 品名 → 料號」會記到品名對照表，下次自動帶出。單價以採購單位計，入庫單價＝單價 ÷ 換算。</Text>
    </Modal>
  )
}

// ── 待匯入清單 ────────────────────────────────────────────────────────────────
function ImportsTab({ code, canConfirm, onChanged, mode, version }: {
  code: string; canConfirm: boolean; onChanged: () => void; mode: ImportMode; version: number
}) {
  const [data, setData] = useState<ImportListResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [status, setStatus] = useState<string[]>(mode === 'open' ? OPEN : CLOSED)
  const [sourceType, setSourceType] = useState<string | undefined>()
  const [dept, setDept] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [range, setRange] = useState<StandardRange>(null)
  const [onlyChanged, setOnlyChanged] = useState(false)
  const [selected, setSelected] = useState<number[]>([])
  const [confirmLines, setConfirmLines] = useState<ImportLine[] | null>(null)
  const [detail, setDetail] = useState<ImportLine | null>(null)
  const [markOpen, setMarkOpen] = useState<'non_stock' | 'pre_opening' | null>(null)
  const [markIds, setMarkIds] = useState<number[]>([])
  const [markReason, setMarkReason] = useState('')
  const [rememberNs, setRememberNs] = useState(false)
  const [beforeOpen, setBeforeOpen] = useState(false)
  const [beforeDate, setBeforeDate] = useState<Dayjs | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetchImports(code, {
        status: status.length ? status : (mode === 'open' ? [...OPEN, 'done'] : CLOSED), source_type: sourceType, department: dept, keyword: keyword.trim() || undefined, only_changed: onlyChanged || undefined,
        ...(range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
      })
      setData(r.data); setSelected([])
    } catch (e) { message.error(errMsg(e, '讀取待匯入清單失敗')) } finally { setLoading(false) }
  }, [code, status, sourceType, dept, keyword, range, onlyChanged])
  useEffect(() => { load() }, [code, status, sourceType, dept, range, onlyChanged, version]) // eslint-disable-line react-hooks/exhaustive-deps

  const doRefresh = async () => {
    setRefreshing(true)
    try {
      const r = await refreshImports(code)
      message.success(`已更新：新增 ${r.data.inserted}、變動 ${r.data.updated}、匯入後被修改 ${r.data.changed_after_import}、Ragic 已無 ${r.data.missing}`)
      load(); onChanged()
    } catch (e) { message.error(errMsg(e, '重新整理失敗')) } finally { setRefreshing(false) }
  }
  const doMark = async () => {
    if (!markOpen) return
    try {
      const r = await markImports(code, { line_ids: markIds, status: markOpen, reason: markReason || undefined, remember_non_stock: rememberNs })
      message.success(`已標記 ${r.data.updated} 筆${r.data.skipped.length ? `；${r.data.skipped.length} 筆已匯入或已對應採購單，略過` : ''}`)
      setMarkOpen(null); setMarkReason(''); setRememberNs(false); load(); onChanged()
    } catch (e) { message.error(errMsg(e, '標記失敗')) }
  }
  const doRevert = async (ids: number[]) => {
    try {
      const r = await markImports(code, { line_ids: ids, status: 'pending' })
      message.success(`已改回待確認 ${r.data.updated} 筆，請到「待匯入清單」處理`); load(); onChanged()
    } catch (e) { message.error(errMsg(e, '操作失敗')) }
  }
  const openMark = (kind: 'non_stock' | 'pre_opening', ids: number[]) => {
    setMarkIds(ids); setMarkReason(''); setRememberNs(false); setMarkOpen(kind)
  }
  const doBefore = async () => {
    if (!beforeDate) { message.warning('請選日期'); return }
    try {
      const r = await markBefore(code, beforeDate.format('YYYY-MM-DD'))
      message.success(`已把 ${r.data.updated} 筆 ${beforeDate.format('YYYY-MM-DD')} 之前的待確認品項標為開帳前不入庫`)
      setBeforeOpen(false); load(); onChanged()
    } catch (e) { message.error(errMsg(e, '整批標記失敗')) }
  }
  const openDetail = async (id: number) => {
    try { setDetail((await fetchImport(code, id)).data) } catch (e) { message.error(errMsg(e, '讀取明細失敗')) }
  }
  const doAck = async (id: number) => {
    try { await ackChange(code, id); message.success('已確認'); setDetail(null); load(); onChanged() }
    catch (e) { message.error(errMsg(e, '操作失敗')) }
  }

  const rows = data?.rows ?? []
  const selectedLines = useMemo(() => rows.filter((r) => selected.includes(r.id)), [rows, selected])
  const columns: ColumnsType<ImportLine> = [
    { title: '來源', dataIndex: 'source_label', width: 70, render: (v: string, r) => <Tag color={r.source_type === 'ragic_po' ? 'geekblue' : 'gold'}>{v}</Tag> },
    { title: '單號', dataIndex: 'doc_no', width: 170, render: (v: string | null, r) => (
      <Space size={4}>
        <span>{v || '—'}</span>
        <Tooltip title="在 Ragic 開啟"><a href={r.ragic_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}
          onClick={(e) => e.stopPropagation()}><LinkOutlined /></a></Tooltip>
        {!!r.attachment_count && (
          <Tooltip title={`附件 ${r.attachment_count} 個，點開明細查看`}>
            <a style={{ color: '#4BA8E8' }} onClick={(e) => { e.stopPropagation(); openDetail(r.id) }}>
              <PaperClipOutlined />{r.attachment_count > 1 ? <span style={{ fontSize: 11 }}>{r.attachment_count}</span> : null}
            </a>
          </Tooltip>)}
      </Space>) },
    { title: '日期', dataIndex: 'doc_date', width: 95, render: (v: string | null) => v || '—' },
    { title: '部門', dataIndex: 'department', width: 90, render: (v: string | null) => v || '—' },
    { title: '廠商／受款者', dataIndex: 'vendor_name', width: 150, ellipsis: true, render: (v: string | null) => v || '—' },
    { title: '品名', dataIndex: 'product_name', ellipsis: true, render: (v: string | null, r) => (
      <Space size={4} wrap>
        <span>{v || '—'}</span>
        {r.po_no && r.source_type === 'ragic_claim' && <Tag color="purple">採購單 {r.po_no}</Tag>}
        {r.suspected_po_no && <Tag color="orange">疑似 {r.suspected_po_no}</Tag>}
      </Space>) },
    { title: '數量', key: 'qty', width: 90, align: 'right', render: (_: unknown, r) => `${r.qty_raw ?? '—'} ${r.unit ?? ''}` },
    { title: '單價', dataIndex: 'unit_price', width: 90, align: 'right', render: money },
    { title: '金額', dataIndex: 'amount', width: 100, align: 'right', render: money },
    { title: '已匯入', dataIndex: 'imported_qty', width: 70, align: 'right', render: (v: number) => (v ? num(v) : '—') },
    { title: '狀態', key: 'st', width: 150, render: (_: unknown, r) => (
      <Space size={2} wrap>
        <Tooltip title={r.status_reason || undefined}><Tag color={STATUS_COLOR[r.status]}>{r.status_label}</Tag></Tooltip>
        {r.source_status !== 'ok' && <Tag color="red">{r.source_status_label}</Tag>}
      </Space>) },
    ...(mode === 'closed' ? [
      { title: '原因', dataIndex: 'status_reason', width: 200, ellipsis: true, render: (v: string | null) => v || '—' },
      { title: '標記', key: 'marked', width: 140, render: (_: unknown, r: ImportLine) => (r.marked_by
        ? r.marked_by
        : <Text type="secondary">系統自動</Text>) },
    ] : []),
    ...(canConfirm ? [{
      title: '操作', key: 'act', width: mode === 'open' ? 110 : 64, align: 'center' as const, fixed: 'right' as const,
      render: (_: unknown, r: ImportLine) => {
        const stop = (fn: () => void) => (e: React.MouseEvent) => { e.stopPropagation(); fn() }
        if (mode === 'open') {
          if (!OPEN.includes(r.status)) return <Text type="secondary">—</Text>
          if (r.source_status !== 'ok') return <Tooltip title="Ragic 來源已異動／退回／刪除，請先開明細確認"><Text type="secondary">來源異動</Text></Tooltip>
          return (
            <Space size={0}>
              <Tooltip title="確認入庫"><Button size="small" type="text" aria-label="確認入庫"
                icon={<CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />} onClick={stop(() => setConfirmLines([r]))} /></Tooltip>
              <Tooltip title="確認不入庫"><Button size="small" type="text" aria-label="確認不入庫"
                icon={<StopOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />} onClick={stop(() => openMark('non_stock', [r.id]))} /></Tooltip>
              <Tooltip title="開帳前不入庫"><Button size="small" type="text" aria-label="開帳前不入庫"
                icon={<FieldTimeOutlined style={{ color: '#8c8c8c', fontSize: 16 }} />} onClick={stop(() => openMark('pre_opening', [r.id]))} /></Tooltip>
            </Space>)
        }
        if (!REVERTIBLE.includes(r.status)) return <Tooltip title="請款單已對應採購單，由系統判定，以採購單入庫（D15）"><Text type="secondary">—</Text></Tooltip>
        return (
          <Popconfirm title="改回待確認？之後要在「待匯入清單」重新確認" onConfirm={() => doRevert([r.id])}
            onPopupClick={(e) => e.stopPropagation()}>
            <Tooltip title="改回待確認"><Button size="small" type="text" aria-label="改回待確認"
              icon={<RollbackOutlined style={{ color: '#4BA8E8', fontSize: 16 }} />} onClick={(e) => e.stopPropagation()} /></Tooltip>
          </Popconfirm>)
      },
    }] : []),
  ]
  const statusOptions = STATUS_OPTIONS.filter((o) => (mode === 'open' ? [...OPEN, 'done'] : CLOSED).includes(o.value))

  const counts = data?.status_counts ?? {}
  return (
    <>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select mode="multiple" allowClear placeholder="狀態" style={{ minWidth: 220 }} value={status} onChange={setStatus}
            options={statusOptions.map((o) => ({ ...o, label: `${o.label}（${counts[o.value] ?? 0}）` }))} />
          <Select allowClear placeholder="來源" style={{ width: 110 }} value={sourceType} onChange={setSourceType}
            options={[{ value: 'ragic_po', label: '採購單' }, { value: 'ragic_claim', label: '請款單' }]} />
          <Select allowClear placeholder="部門" style={{ width: 130 }} value={dept} onChange={setDept}
            options={(data?.departments ?? []).map((d) => ({ value: d, label: d }))} />
          <StandardRangePicker value={range} anchor={data?.data_end} onChange={setRange} />
          <Input.Search allowClear placeholder="單號／品名／廠商" style={{ width: 200 }} value={keyword} onChange={(e) => setKeyword(e.target.value)} onSearch={load} />
          <Space size={4}><Switch size="small" checked={onlyChanged} onChange={setOnlyChanged} /><span>只看來源已異動（{data?.changed_count ?? 0}）</span></Space>
        </Space>
        <div style={{ marginTop: 8 }}>
          <Space wrap>
            {canConfirm && mode === 'open' && <Button icon={<SyncOutlined />} loading={refreshing} onClick={doRefresh}>從 Ragic 資料重新整理</Button>}
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新讀取</Button>
            {canConfirm && mode === 'open' && <>
              <Button type="primary" icon={<CheckOutlined />} disabled={!selectedLines.length} onClick={() => setConfirmLines(selectedLines)}>
                確認入庫（{selectedLines.length}）</Button>
              <Button icon={<StopOutlined />} disabled={!selectedLines.length} onClick={() => openMark('non_stock', selected)}>確認不入庫</Button>
              <Button disabled={!selectedLines.length} onClick={() => openMark('pre_opening', selected)}>標開帳前</Button>
              <Button onClick={() => setBeforeOpen(true)}>開帳前整批標記…</Button>
            </>}
            {canConfirm && mode === 'closed' && (
              <Popconfirm title={`把 ${selectedLines.length} 筆改回待確認？`} disabled={!selectedLines.length} onConfirm={() => doRevert(selected)}>
                <Button disabled={!selectedLines.length}>改回待確認（{selectedLines.length}）</Button>
              </Popconfirm>)}
            <Text type="secondary">共 {data?.total ?? 0} 筆{data?.refreshed_at ? `｜清單更新於 ${data.refreshed_at}` : '｜尚未產生清單，請先「從 Ragic 資料重新整理」'}</Text>
          </Space>
        </div>
      </Card>
      <Table<ImportLine> size="small" rowKey="id" loading={loading} dataSource={rows} columns={columns}
        pagination={{ pageSize: 50, showSizeChanger: false }} scroll={{ x: 1300 }}
        rowSelection={canConfirm ? {
          selectedRowKeys: selected, onChange: (k) => setSelected(k as number[]),
          getCheckboxProps: (r) => ({
            disabled: mode === 'open' ? !OPEN.includes(r.status) || r.source_status !== 'ok' : !REVERTIBLE.includes(r.status),
          }),
        } : undefined}
        onRow={(r) => ({ onClick: () => openDetail(r.id), style: { cursor: 'pointer' } })} />

      <ConfirmModal code={code} lines={confirmLines ?? []} open={!!confirmLines} onClose={() => setConfirmLines(null)}
        onDone={() => { setConfirmLines(null); load(); onChanged() }} />

      <Modal open={!!markOpen} title={markOpen === 'non_stock' ? `確認不入庫（${markIds.length} 筆）` : `標記開帳前不入庫（${markIds.length} 筆）`}
        onCancel={() => setMarkOpen(null)} onOk={doMark}>
        <Input.TextArea rows={2} placeholder="原因（例：工程費、服務費、一次性費用）" value={markReason} onChange={(e) => setMarkReason(e.target.value)} />
        {markOpen === 'non_stock' && (
          <Checkbox style={{ marginTop: 8 }} checked={rememberNs} onChange={(e) => setRememberNs(e.target.checked)}>
            記住這些品名，之後同名品項自動建議為不入庫</Checkbox>)}
      </Modal>
      <Modal open={beforeOpen} title="開帳前舊單據整批標記（D19）" onCancel={() => setBeforeOpen(false)} onOk={doBefore} okText="整批標記">
        <Alert type="info" showIcon style={{ marginBottom: 12 }} message="只會標記「待確認、尚未匯入」且單據日期早於所選日期的品項；已匯入的不受影響。" />
        <DatePicker value={beforeDate} onChange={setBeforeDate} placeholder="開帳日（不含）" />
      </Modal>

      <Drawer open={!!detail} width={640} onClose={() => setDetail(null)}
        title={detail ? (
          <Space>
            <Tag color={detail.source_type === 'ragic_po' ? 'geekblue' : 'gold'}>{detail.source_label}</Tag>
            <span>{`${detail.department ?? ''}：${detail.doc_no || detail.ragic_id}`}</span>
            <a href={detail.ragic_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}><LinkOutlined /> 在 Ragic 查看</a>
          </Space>) : ''}>
        {detail && (
          <>
            {detail.source_changed && (
              <Alert type="error" showIcon style={{ marginBottom: 12 }}
                message={`Ragic 來源${detail.source_status_label || '已異動'}（已入庫的數量不會自動扣回）`}
                description="請比對 Ragic 內容後決定：作廢對應的進貨單，或確認貨確實已收到。"
                action={canConfirm ? <Popconfirm title="確認已處理，清除這個標示？" onConfirm={() => doAck(detail.id)}><Button size="small">已處理</Button></Popconfirm> : undefined} />)}
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="狀態"><Tag color={STATUS_COLOR[detail.status]}>{detail.status_label}</Tag>{detail.status_reason ? ` ${detail.status_reason}` : ''}</Descriptions.Item>
              <Descriptions.Item label="品名"><b>{detail.product_name || '—'}</b></Descriptions.Item>
              <Descriptions.Item label="金額（未稅）"><b>{money(detail.amount)}</b></Descriptions.Item>
            </Descriptions>
            {canConfirm && OPEN.includes(detail.status) && detail.source_status === 'ok' && (
              <Space style={{ marginBottom: 16 }} wrap>
                <Button type="primary" icon={<CheckCircleOutlined />}
                  onClick={() => { setDetail(null); setConfirmLines([detail]) }}>確認入庫</Button>
                <Button danger icon={<StopOutlined />}
                  onClick={() => { setDetail(null); openMark('non_stock', [detail.id]) }}>確認不入庫</Button>
                <Button icon={<FieldTimeOutlined />}
                  onClick={() => { setDetail(null); openMark('pre_opening', [detail.id]) }}>開帳前不入庫</Button>
              </Space>)}
            <div style={{ fontWeight: 600, marginBottom: 6 }}>明細欄位</div>
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              {Object.entries(detail.detail ?? {}).map(([k, v]) => (
                <Descriptions.Item key={k} label={k}>
                  {!v ? '—' : k.startsWith('金額') || k.startsWith('單價') ? `$${v}` : <span style={{ whiteSpace: 'pre-wrap' }}>{v}</span>}
                </Descriptions.Item>))}
            </Descriptions>
            <AttachmentsSection items={detail.attachments ?? []} />
            <div style={{ fontWeight: 600, marginBottom: 6 }}>入庫紀錄</div>
            <Table size="small" rowKey={(r) => `${r.receipt_id}-${r.purchase_qty}`} pagination={false} dataSource={detail.receipts ?? []}
              locale={{ emptyText: '尚未入庫' }}
              columns={[
                { title: '進貨單', dataIndex: 'receipt_no', width: 170 },
                { title: '日期', dataIndex: 'receipt_date', width: 100 },
                { title: '實收', dataIndex: 'purchase_qty', width: 70, align: 'right' },
                { title: '入庫數量', dataIndex: 'stock_qty', width: 80, align: 'right' },
                { title: '金額', dataIndex: 'amount', width: 100, align: 'right', render: money },
                { title: '狀態', dataIndex: 'status', render: (v: string) => (v === 'posted' ? <Tag color="green">已過帳</Tag> : <Tag>已作廢</Tag>) },
              ]} />
          </>
        )}
      </Drawer>
    </>
  )
}

// ── 進貨單 ────────────────────────────────────────────────────────────────────
function ReceiptsTab({ code, canConfirm, version, onChanged }: { code: string; canConfirm: boolean; version: number; onChanged: () => void }) {
  const [rows, setRows] = useState<Receipt[]>([])
  const [loading, setLoading] = useState(false)
  const [range, setRange] = useState<StandardRange>(null)
  const [detail, setDetail] = useState<Receipt | null>(null)
  const [voiding, setVoiding] = useState<Receipt | null>(null)
  const [reason, setReason] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows((await fetchReceipts(code, range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {})).data)
    } catch (e) { message.error(errMsg(e, '讀取進貨單失敗')) } finally { setLoading(false) }
  }, [code, range])
  useEffect(() => { load() }, [load, version])

  const doVoid = async () => {
    if (!voiding || !reason.trim()) { message.warning('請填作廢原因'); return }
    try { await voidReceipt(code, voiding.id, reason.trim()); message.success('已作廢'); setVoiding(null); setReason(''); setDetail(null); load(); onChanged() }
    catch (e) { message.error(errMsg(e, '作廢失敗')) }
  }
  const dataEnd = rows.find((r) => r.status === 'posted')?.receipt_date ?? null

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <StandardRangePicker value={range} anchor={dataEnd} onChange={setRange} />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新讀取</Button>
      </Space>
      <Table<Receipt> size="small" rowKey="id" loading={loading} dataSource={rows} pagination={{ pageSize: 30 }}
        onRow={(r) => ({ onClick: async () => { try { setDetail((await fetchReceipt(code, r.id)).data) } catch (e) { message.error(errMsg(e, '讀取失敗')) } }, style: { cursor: 'pointer' } })}
        columns={[
          { title: '進貨單號', dataIndex: 'receipt_no', width: 180 },
          { title: '入庫日期', dataIndex: 'receipt_date', width: 110 },
          { title: '倉庫', dataIndex: 'warehouse_name' },
          { title: '品項數', dataIndex: 'line_count', width: 80, align: 'right' },
          { title: '金額（未稅）', dataIndex: 'total_amount', width: 130, align: 'right', render: money },
          { title: '狀態', dataIndex: 'status', width: 90, render: (v: string) => (v === 'posted' ? <Tag color="green">已過帳</Tag> : <Tag>已作廢</Tag>) },
          { title: '建立', key: 'by', width: 180, render: (_: unknown, r) => `${r.created_by ?? ''} ${r.created_at ?? ''}` },
        ]} />
      <Drawer open={!!detail} width={860} onClose={() => setDetail(null)}
        title={detail ? <Space><Tag color={detail.status === 'posted' ? 'green' : 'default'}>{detail.status === 'posted' ? '已過帳' : '已作廢'}</Tag><span>{`進貨單：${detail.receipt_no}`}</span></Space> : ''}
        extra={detail && canConfirm && detail.status === 'posted' ? <Button danger onClick={() => setVoiding(detail)}>作廢</Button> : undefined}>
        {detail && (
          <>
            <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="倉庫">{detail.warehouse_name}</Descriptions.Item>
              <Descriptions.Item label="入庫日期">{detail.receipt_date}</Descriptions.Item>
              <Descriptions.Item label="金額（未稅）"><b>{money(detail.total_amount)}</b></Descriptions.Item>
              <Descriptions.Item label="建立">{`${detail.created_by ?? ''} ${detail.created_at ?? ''}`}</Descriptions.Item>
              <Descriptions.Item label="備註" span={2}>{detail.note || '—'}</Descriptions.Item>
              {detail.status === 'voided' && <Descriptions.Item label="作廢" span={2}>{`${detail.voided_by ?? ''}：${detail.void_reason ?? ''}`}</Descriptions.Item>}
            </Descriptions>
            <Table size="small" rowKey="id" pagination={false} dataSource={detail.lines ?? []}
              columns={[
                { title: '來源', key: 'src', width: 180, render: (_: unknown, l) => (
                  <Space size={4}><Tag>{l.source_label}</Tag><a href={l.ragic_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>{l.doc_no} <LinkOutlined /></a></Space>) },
                { title: 'Ragic 品名', dataIndex: 'product_name', ellipsis: true },
                { title: '料號', key: 'item', width: 200, render: (_: unknown, l) => `${l.item_code} ${l.item_name}` },
                { title: '實收', key: 'pq', width: 80, align: 'right', render: (_: unknown, l) => `${l.purchase_qty} ${l.purchase_unit ?? ''}` },
                { title: '入庫', key: 'sq', width: 80, align: 'right', render: (_: unknown, l) => `${l.stock_qty} ${l.stock_unit ?? ''}` },
                { title: '單價', dataIndex: 'unit_cost', width: 80, align: 'right', render: (v: number, l) => <>{money(v)}{l.is_estimated_cost && <Tag color="orange" style={{ marginLeft: 4 }}>估</Tag>}</> },
                { title: '金額', dataIndex: 'amount', width: 90, align: 'right', render: money },
              ]} />
          </>
        )}
      </Drawer>
      <Modal open={!!voiding} title={voiding ? `作廢進貨單 ${voiding.receipt_no}` : ''} onCancel={() => setVoiding(null)} onOk={doVoid} okText="作廢" okButtonProps={{ danger: true }}>
        <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="作廢會產生反向異動扣回庫存（庫存不足會擋下），並把可匯入量回補到待匯入清單。" />
        <Input.TextArea rows={3} placeholder="作廢原因（必填）" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
    </>
  )
}

export default function StockReceiptsPage() {
  const { companies, code, setCode, error } = useStockCompany()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canConfirm = hasPermission('stock_receipt_confirm')
  const [summary, setSummary] = useState<ReceiptSummary | null>(null)
  const [version, setVersion] = useState(0)

  const loadSummary = useCallback(() => {
    if (!code) return
    fetchReceiptSummary(code).then((r) => setSummary(r.data)).catch(() => setSummary(null))
  }, [code])
  useEffect(() => { loadSummary() }, [loadSummary, version])
  const changed = () => setVersion((v) => v + 1)

  if (error) return <Alert type="error" showIcon message={error} />
  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}><Card size="small"><Statistic title={`本月進貨單（${summary?.month ?? ''}）`} value={summary?.receipt_count ?? 0} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="本月入庫金額（未稅）" value={summary?.amount ?? 0} prefix="$" precision={0} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="待確認品項" value={summary?.pending_lines ?? 0} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="來源已異動" value={summary?.changed_lines ?? 0}
          valueStyle={{ color: (summary?.changed_lines ?? 0) > 0 ? '#cf1322' : undefined }} /></Card></Col>
      </Row>
      <Space style={{ marginBottom: 8 }}>
        <StockCompanySelect companies={companies} value={code} onChange={setCode} />
        <Text type="secondary">待匯入清單＝Ragic 採購單品項＋沒有對應採購單的已核准請款單品項；每一筆都要人工確認入庫或不入庫，確認不入庫的收在「不入庫」TAB</Text>
      </Space>
      {code && (
        <Tabs key={code} items={[
          { key: 'imports', label: `待匯入清單${summary ? `（${summary.pending_lines}）` : ''}`,
            children: <ImportsTab mode="open" code={code} canConfirm={canConfirm} onChanged={changed} version={version} /> },
          { key: 'closed', label: '不入庫',
            children: <ImportsTab mode="closed" code={code} canConfirm={canConfirm} onChanged={changed} version={version} /> },
          { key: 'receipts', label: '進貨單', children: <ReceiptsTab code={code} canConfirm={canConfirm} version={version} onChanged={changed} /> },
        ]} />
      )}
    </div>
  )
}

/** Drawer「附件」：圖片用 Image.PreviewGroup 燈箱（CLAUDE.md §7），其他檔案（PDF、Word…）另開分頁下載。
 *  網址是 Ragic sims/file.jsp，瀏覽器需已登入 Ragic 才看得到（與報修模組相同）。 */
function AttachmentsSection({ items }: { items: ImportAttachment[] }) {
  const images = items.filter((a) => a.is_image)
  const files = items.filter((a) => !a.is_image)
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}><PaperClipOutlined /> 附件（{items.length}）</div>
      {items.length === 0 ? <Text type="secondary">Ragic 單據沒有附件</Text> : (
        <>
          {images.length > 0 && (
            <Image.PreviewGroup>
              <Space wrap size={8} style={{ marginBottom: files.length ? 10 : 0 }}>
                {images.map((a) => (
                  <Tooltip key={a.url} title={`${a.source}｜${a.filename}`}>
                    <Image src={a.url} width={96} height={96} style={{ objectFit: 'cover', borderRadius: 4, border: '1px solid #e0e6ed' }}
                      fallback="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='96' height='96'><rect width='96' height='96' fill='%23f5f5f5'/><text x='48' y='52' font-size='11' text-anchor='middle' fill='%23999'>無法載入</text></svg>" />
                  </Tooltip>))}
              </Space>
            </Image.PreviewGroup>)}
          {files.map((a) => (
            <div key={a.url} style={{ padding: '3px 0' }}>
              <a href={a.url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>
                {a.filename.toLowerCase().endsWith('.pdf') ? <FilePdfOutlined style={{ color: '#e74c3c' }} /> : <FileOutlined />} {a.filename}
              </a>
              <Text type="secondary" style={{ fontSize: 12, marginInlineStart: 8 }}>{a.source}</Text>
            </div>))}
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>需已登入 Ragic 才能開啟</Text>
        </>)}
    </div>
  )
}
