/**
 * 庫存管理 › 領用單（規格 docs/SPEC_stock_management.md §7，Phase 4a 2026-11-17）
 *
 * 一頁四種單據：領用／退料／調撥／報廢
 *   - 領用：只能領「可用量 > 0」的料號；送出即保留數量；倉庫設定需核准時先給部門主管核准；倉管發料過帳
 *   - 退料：必須對應已過帳的領用單，不得超過「已領 − 已退」；倉管收料過帳
 *   - 調撥／報廢：倉管開單即過帳（D29），可作廢（反向異動）
 * 資料範圍（D27）：開單者只看所屬部門的倉；倉管（stock_issue_post）看同公司全部
 * 單位成本與金額只給倉管、庫存檢視者看（後端已遮蔽）
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Drawer, Dropdown, Empty, Input, InputNumber, Modal, Row, Select,
  Space, Statistic, Switch, Table, Tag, Typography, message,
} from 'antd'
import { DeleteOutlined, DownOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import StandardRangePicker, { type StandardRange } from '@/components/StandardRangePicker'
import {
  approveIssue, cancelIssue, createIssue, errMsg, fetchAvailable, fetchIssue, fetchIssueCostCenters, fetchIssueMeta,
  fetchIssueSummary, fetchIssues, fetchReturnable, postIssue, rejectIssue, submitIssue, updateIssue, voidIssue,
  type AvailableItem, type IssueAction, type IssueDoc, type IssueDocType, type IssueInput, type IssueMeta,
  type IssueSummary, type ReturnableLine,
} from '@/api/stock'
import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'

const { Text } = Typography
const money = (v: number | null | undefined) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)
const num = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: 4 }))

const TYPE_LABEL: Record<IssueDocType, string> = { issue: '領用單', return: '退料單', transfer: '調撥單', scrap: '報廢單' }
const TYPE_COLOR: Record<IssueDocType, string> = { issue: 'blue', return: 'cyan', transfer: 'purple', scrap: 'volcano' }
const STATUS_COLOR: Record<string, string> = {
  draft: 'default', pending_approval: 'gold', approved: 'blue', posted: 'green', cancelled: 'default', rejected: 'red', voided: 'default',
}
const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿' }, { value: 'pending_approval', label: '待核准' }, { value: 'approved', label: '待發料／待收料' },
  { value: 'posted', label: '已過帳' }, { value: 'cancelled', label: '已取消' }, { value: 'rejected', label: '已退回' },
  { value: 'voided', label: '已作廢' },
]

// ── 開單／修改 Modal ─────────────────────────────────────────────────────────
interface EditLine { key: string; item_id?: number; qty?: number; ref_line_id?: number; note?: string }
let seq = 0
const newKey = () => `n${++seq}`

function IssueEditor({ code, meta, open, docType, editing, refIssue, onClose, onDone }: {
  code: string; meta: IssueMeta; open: boolean; docType: IssueDocType; editing: IssueDoc | null; refIssue: IssueDoc | null
  onClose: () => void; onDone: (id: number) => void
}) {
  const isReturn = docType === 'return'
  const keeperOnly = docType === 'transfer' || docType === 'scrap'
  const whOptions = keeperOnly ? meta.all_warehouses : meta.my_warehouses
  const [whId, setWhId] = useState<number | undefined>()
  const [toWhId, setToWhId] = useState<number | undefined>()
  const [docDate, setDocDate] = useState<Dayjs>(dayjs())
  const [postDate, setPostDate] = useState<Dayjs>(dayjs())
  const [requester, setRequester] = useState('')
  const [purpose, setPurpose] = useState('')
  const [ccId, setCcId] = useState<number | undefined>()
  const [account, setAccount] = useState('')
  const [lines, setLines] = useState<EditLine[]>([])
  const [avail, setAvail] = useState<AvailableItem[]>([])
  const [returnable, setReturnable] = useState<ReturnableLine[]>([])
  const [ccs, setCcs] = useState<{ id: number; label: string; department_name: string; is_mine: boolean }[]>([])
  const [saving, setSaving] = useState(false)

  // 初始化
  useEffect(() => {
    if (!open) return
    if (editing) {
      setWhId(editing.warehouse_id); setToWhId(editing.to_warehouse_id ?? undefined); setDocDate(dayjs(editing.doc_date))
      setRequester(editing.requester_name ?? ''); setPurpose(editing.purpose ?? ''); setCcId(editing.cost_center_id ?? undefined)
      setAccount(editing.account_code ?? '')
      setLines((editing.lines ?? []).map((l) => ({ key: newKey(), item_id: l.item_id, qty: l.qty, ref_line_id: l.ref_line_id ?? undefined, note: l.note ?? undefined })))
    } else {
      const first = isReturn && refIssue ? refIssue.warehouse_id : whOptions.length === 1 ? whOptions[0].id : undefined
      setWhId(first); setToWhId(undefined); setDocDate(dayjs()); setRequester(meta.user_name)
      setPurpose(''); setCcId(undefined); setAccount('')
      setLines(isReturn ? [] : [{ key: newKey() }])
    }
    setPostDate(dayjs())
  }, [open, editing, isReturn, refIssue, meta.user_name, whOptions])

  // 可領量（依倉）＋成本中心
  useEffect(() => {
    if (!open || !whId || isReturn) { setAvail([]); return }
    fetchAvailable(code, whId).then((r) => setAvail(r.data)).catch((e) => message.error(errMsg(e, '讀取可領料號失敗')))
    if (docType === 'issue') {
      fetchIssueCostCenters(code, whId).then((r) => {
        setCcs(r.data.items)
        if (!editing) setCcId((cur) => cur ?? r.data.default_id ?? undefined)
      }).catch(() => setCcs([]))
    }
  }, [open, whId, code, docType, isReturn, editing])

  // 退料：原領用單可退量
  const refId = editing?.ref_issue_id ?? refIssue?.id
  useEffect(() => {
    if (!open || !isReturn || !refId) { setReturnable([]); return }
    fetchReturnable(code, refId).then((r) => {
      setReturnable(r.data)
      if (!editing) setLines(r.data.filter((x) => x.returnable > 0).map((x) => ({ key: newKey(), ref_line_id: x.ref_line_id, qty: undefined })))
    }).catch((e) => message.error(errMsg(e, '讀取可退品項失敗')))
  }, [open, isReturn, refId, code, editing])

  const availMap = useMemo(() => new Map(avail.map((a) => [a.item_id, a])), [avail])
  const retMap = useMemo(() => new Map(returnable.map((r) => [r.ref_line_id, r])), [returnable])
  // 草稿修改時，草稿自己的量不算在可用量內（送出才保留）
  const setLine = (key: string, patch: Partial<EditLine>) => setLines((ls) => ls.map((l) => (l.key === key ? { ...l, ...patch } : l)))

  const save = async (then: 'submit' | 'post' | null) => {
    if (!whId) { message.warning('請選擇倉庫'); return }
    if (docType === 'transfer' && !toWhId) { message.warning('請選擇調入倉'); return }
    if (docType === 'scrap' && !purpose.trim()) { message.warning('請填寫報廢原因'); return }
    const use = lines.filter((l) => (l.qty ?? 0) > 0)
    if (!use.length) { message.warning('請至少輸入一筆數量'); return }
    if (!isReturn && use.some((l) => !l.item_id)) { message.warning('有明細尚未選料號'); return }
    const body: IssueInput = {
      doc_type: docType, warehouse_id: whId, to_warehouse_id: docType === 'transfer' ? toWhId : null,
      doc_date: docDate.format('YYYY-MM-DD'), requester_name: docType === 'issue' ? requester : null,
      purpose: purpose || null, cost_center_id: docType === 'issue' ? ccId ?? null : null, account_code: account || null,
      ref_issue_id: isReturn ? refId ?? null : null,
      lines: use.map((l) => ({ item_id: l.item_id, qty: l.qty!, ref_line_id: l.ref_line_id ?? null, note: l.note || null })),
      then, post_date: then === 'post' ? postDate.format('YYYY-MM-DD') : null,
    }
    setSaving(true)
    try {
      const r = editing ? await updateIssue(code, editing.id, body) : await createIssue(code, body)
      message.success(`${TYPE_LABEL[docType]} ${r.data.doc_no}：${then === 'submit' ? '已送出' : then === 'post' ? '已過帳' : '已存草稿'}`)
      onDone(r.data.id)
    } catch (e) {
      message.error(errMsg(e, '存檔失敗'))
    } finally {
      setSaving(false)
    }
  }

  const itemCols: ColumnsType<EditLine> = [
    { title: '料號', key: 'item', render: (_: unknown, l) => (
      <Select showSearch style={{ width: '100%' }} placeholder={whId ? '輸入料號或品名' : '請先選倉庫'} value={l.item_id}
        optionFilterProp="label" disabled={!whId}
        onChange={(v) => setLine(l.key, { item_id: v })}
        options={avail.map((a) => ({
          value: a.item_id, label: `${a.item_code} ${a.item_name}${a.spec ? `（${a.spec}）` : ''}`,
          disabled: lines.some((x) => x.key !== l.key && x.item_id === a.item_id),
        }))}
        notFoundContent={whId ? '這個倉沒有可用庫存的料號' : undefined} />) },
    { title: '可用量', key: 'avail', width: 110, align: 'right', render: (_: unknown, l) => {
      const a = l.item_id ? availMap.get(l.item_id) : undefined
      return a ? `${num(a.available)} ${a.unit ?? ''}` : '—'
    } },
    { title: '數量', key: 'qty', width: 130, render: (_: unknown, l) => {
      const a = l.item_id ? availMap.get(l.item_id) : undefined
      return <InputNumber min={0} max={a?.available} value={l.qty} style={{ width: '100%' }} onChange={(v) => setLine(l.key, { qty: v ?? undefined })} />
    } },
    { title: '備註', key: 'note', width: 180, render: (_: unknown, l) => <Input value={l.note} onChange={(e) => setLine(l.key, { note: e.target.value })} /> },
    { title: '', key: 'del', width: 40, render: (_: unknown, l) => (
      <Button type="text" danger icon={<DeleteOutlined />} onClick={() => setLines((ls) => ls.filter((x) => x.key !== l.key))} />) },
  ]
  const returnCols: ColumnsType<EditLine> = [
    { title: '料號', key: 'item', render: (_: unknown, l) => { const r = retMap.get(l.ref_line_id!); return r ? `${r.item_code} ${r.item_name}` : '—' } },
    { title: '已領', key: 'issued', width: 90, align: 'right', render: (_: unknown, l) => num(retMap.get(l.ref_line_id!)?.issued_qty) },
    { title: '已退', key: 'returned', width: 90, align: 'right', render: (_: unknown, l) => num(retMap.get(l.ref_line_id!)?.returned_qty) },
    { title: '可退', key: 'returnable', width: 90, align: 'right', render: (_: unknown, l) => {
      const r = retMap.get(l.ref_line_id!); return r ? `${num(r.returnable)} ${r.unit ?? ''}` : '—'
    } },
    { title: '退料數量', key: 'qty', width: 130, render: (_: unknown, l) => (
      <InputNumber min={0} max={retMap.get(l.ref_line_id!)?.returnable} value={l.qty} style={{ width: '100%' }}
        onChange={(v) => setLine(l.key, { qty: v ?? undefined })} />) },
  ]

  const title = `${editing ? '修改' : '新增'}${TYPE_LABEL[docType]}${editing ? ` ${editing.doc_no}` : ''}`
  const whSel = whOptions.find((w) => w.id === whId) as IssueMeta['my_warehouses'][number] | undefined
  return (
    <Modal open={open} title={title} width={980} onCancel={onClose} destroyOnClose
      footer={(
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button loading={saving} onClick={() => save(null)}>存草稿</Button>
          {!keeperOnly && <Button type="primary" loading={saving} onClick={() => save('submit')}>存檔並送出</Button>}
          {keeperOnly && (
            <>
              <DatePicker value={postDate} onChange={(d) => d && setPostDate(d)} allowClear={false} />
              <Button type="primary" loading={saving} onClick={() => save('post')}>存檔並過帳</Button>
            </>
          )}
        </Space>
      )}>
      {whOptions.length === 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message={keeperOnly ? '這家公司沒有可用的倉庫' : '您所屬的部門沒有倉庫（請確認「使用者管理」的部門設定，或請倉管在「庫存主檔設定」建立部門倉）'} />)}
      {isReturn && refIssue && <Alert type="info" showIcon style={{ marginBottom: 12 }} message={`退回原領用單 ${refIssue.doc_no}（${refIssue.warehouse_name}）`} />}
      <Space wrap style={{ marginBottom: 12 }}>
        <Select placeholder={docType === 'transfer' ? '調出倉' : '倉庫'} style={{ width: 240 }} value={whId} disabled={isReturn}
          onChange={(v) => { setWhId(v); setLines([{ key: newKey() }]); setCcId(undefined) }}
          options={whOptions.map((w) => ({ value: w.id, label: w.department_name ? `${w.name}（${w.department_name}）` : w.name,
            disabled: w.status !== 'active' }))} />
        {docType === 'transfer' && (
          <Select placeholder="調入倉" style={{ width: 240 }} value={toWhId} onChange={setToWhId}
            options={meta.all_warehouses.filter((w) => w.id !== whId).map((w) => ({
              value: w.id, label: w.department_name ? `${w.name}（${w.department_name}）` : w.name, disabled: w.status !== 'active' }))} />)}
        <DatePicker value={docDate} onChange={(d) => d && setDocDate(d)} allowClear={false} />
        {docType === 'issue' && <Input addonBefore="領用人" style={{ width: 220 }} value={requester} onChange={(e) => setRequester(e.target.value)} />}
      </Space>
      {whSel?.issue_requires_approval && docType === 'issue' && <Alert type="info" showIcon style={{ marginBottom: 12 }} message="這個倉的領用單需部門主管核准後才能發料" />}
      {docType === 'issue' && (
        <Space wrap style={{ marginBottom: 12 }}>
          <Select allowClear showSearch optionFilterProp="label" placeholder="成本中心" style={{ width: 320 }} value={ccId} onChange={setCcId}
            options={ccs.map((c) => ({ value: c.id, label: `${c.label}（${c.department_name}）` }))} />
          <Input placeholder="會科（選填）" style={{ width: 160 }} value={account} onChange={(e) => setAccount(e.target.value)} />
        </Space>
      )}
      <Input.TextArea rows={2} style={{ marginBottom: 12 }} value={purpose} onChange={(e) => setPurpose(e.target.value)}
        placeholder={docType === 'scrap' ? '報廢原因（必填）' : docType === 'return' ? '退料原因' : docType === 'transfer' ? '調撥說明' : '用途說明'} />
      {isReturn ? (
        <Table<EditLine> size="small" rowKey="key" pagination={false} dataSource={lines} columns={returnCols}
          locale={{ emptyText: <Empty description="原領用單已無可退品項" /> }} />
      ) : (
        <>
          <Table<EditLine> size="small" rowKey="key" pagination={false} dataSource={lines} columns={itemCols} />
          <Button type="dashed" icon={<PlusOutlined />} style={{ marginTop: 8 }} disabled={!whId}
            onClick={() => setLines((ls) => [...ls, { key: newKey() }])}>加一筆</Button>
        </>
      )}
    </Modal>
  )
}

// ── 主頁 ─────────────────────────────────────────────────────────────────────
export default function StockIssuesPage() {
  const { companies, code, setCode, error } = useStockCompany()
  const [meta, setMeta] = useState<IssueMeta | null>(null)
  const [summary, setSummary] = useState<IssueSummary | null>(null)
  const [rows, setRows] = useState<IssueDoc[]>([])
  const [loading, setLoading] = useState(false)
  const [range, setRange] = useState<StandardRange>(null)
  const [docType, setDocType] = useState<IssueDocType | undefined>()
  const [status, setStatus] = useState<string[]>([])
  const [mine, setMine] = useState(false)
  const [detail, setDetail] = useState<IssueDoc | null>(null)
  const [editor, setEditor] = useState<{ type: IssueDocType; editing: IssueDoc | null; ref: IssueDoc | null } | null>(null)
  const [reasonFor, setReasonFor] = useState<{ action: 'reject' | 'cancel' | 'void'; doc: IssueDoc } | null>(null)
  const [reason, setReason] = useState('')
  const [postFor, setPostFor] = useState<IssueDoc | null>(null)
  const [postDate, setPostDate] = useState<Dayjs>(dayjs())
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!code) return
    setMeta(null)
    fetchIssueMeta(code).then((r) => setMeta(r.data)).catch((e) => message.error(errMsg(e, '讀取領用單設定失敗')))
  }, [code])

  const params = useMemo(() => (range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}), [range])
  const load = useCallback(async () => {
    if (!code) return
    setLoading(true)
    try {
      const [l, s] = await Promise.all([
        fetchIssues(code, { ...params, doc_type: docType, status: status.length ? status : undefined, mine }),
        fetchIssueSummary(code, params),
      ])
      setRows(l.data); setSummary(s.data)
    } catch (e) { message.error(errMsg(e, '讀取單據失敗')) } finally { setLoading(false) }
  }, [code, params, docType, status, mine])
  useEffect(() => { load() }, [load])

  const openDetail = async (id: number) => {
    try { setDetail((await fetchIssue(code, id)).data) } catch (e) { message.error(errMsg(e, '讀取單據失敗')) }
  }
  const afterAction = async (id?: number) => {
    await load()
    if (id) await openDetail(id)
  }
  const run = async (fn: () => Promise<{ data: { doc_no: string; status_label?: string } }>, ok: string) => {
    setBusy(true)
    try { const r = await fn(); message.success(`${r.data.doc_no}：${r.data.status_label ?? ok}`); return true }
    catch (e) { message.error(errMsg(e, '操作失敗')); return false }
    finally { setBusy(false) }
  }
  const doAction = async (a: IssueAction, d: IssueDoc) => {
    if (a === 'edit') { const full = d.lines ? d : (await fetchIssue(code, d.id)).data; setEditor({ type: d.doc_type, editing: full, ref: null }); return }
    if (a === 'return') { setEditor({ type: 'return', editing: null, ref: d }); return }
    if (a === 'reject' || a === 'cancel' || a === 'void') { setReason(''); setReasonFor({ action: a, doc: d }); return }
    if (a === 'post') { setPostDate(dayjs()); setPostFor(d); return }
    if (a === 'submit' && await run(() => submitIssue(code, d.id), '已送出')) afterAction(d.id)
    if (a === 'approve' && await run(() => approveIssue(code, d.id), '已核准')) afterAction(d.id)
  }
  const doReason = async () => {
    if (!reasonFor) return
    const { action, doc } = reasonFor
    if (action !== 'cancel' && !reason.trim()) { message.warning('請填寫原因'); return }
    const fn = action === 'reject' ? () => rejectIssue(code, doc.id, reason.trim())
      : action === 'void' ? () => voidIssue(code, doc.id, reason.trim()) : () => cancelIssue(code, doc.id, reason.trim())
    if (await run(fn, '完成')) { setReasonFor(null); afterAction(doc.id) }
  }
  const doPost = async () => {
    if (!postFor) return
    if (await run(() => postIssue(code, postFor.id, postDate.format('YYYY-MM-DD')), '已過帳')) { const id = postFor.id; setPostFor(null); afterAction(id) }
  }

  const ACTION_LABEL: Record<IssueAction, string> = {
    edit: '修改', submit: '送出', cancel: '取消', approve: '核准', reject: '退回', void: '作廢', return: '開退料單',
    post: detail?.doc_type === 'issue' ? '發料過帳' : detail?.doc_type === 'return' ? '收料過帳' : '過帳',
  }
  const createMenu = [
    ...(meta?.can_create ? [{ key: 'issue', label: '領用單' }] : []),
    ...(meta?.can_post ? [{ key: 'transfer', label: '調撥單' }, { key: 'scrap', label: '報廢單' }] : []),
  ]

  const columns: ColumnsType<IssueDoc> = [
    { title: '單號', dataIndex: 'doc_no', width: 170 },
    { title: '類型', dataIndex: 'doc_type', width: 80, render: (v: IssueDocType) => <Tag color={TYPE_COLOR[v]}>{TYPE_LABEL[v].replace('單', '')}</Tag> },
    { title: '日期', dataIndex: 'doc_date', width: 100 },
    { title: '倉庫', key: 'wh', render: (_: unknown, r) => (r.doc_type === 'transfer' ? `${r.warehouse_name} → ${r.to_warehouse_name ?? ''}` : r.warehouse_name) },
    { title: '領用人／開單', key: 'who', width: 120, render: (_: unknown, r) => r.requester_name || r.created_by || '—' },
    { title: '用途／原因', dataIndex: 'purpose', ellipsis: true, render: (v: string | null) => v || '—' },
    { title: '品項', dataIndex: 'line_count', width: 60, align: 'right' },
    ...(meta?.can_see_cost ? [{ title: '金額', dataIndex: 'total_amount', width: 110, align: 'right' as const, render: (v: number | null, r: IssueDoc) => (r.status === 'posted' || r.status === 'voided' ? money(v) : '—') }] : []),
    { title: '狀態', key: 'status', width: 90, render: (_: unknown, r) => <Tag color={STATUS_COLOR[r.status]}>{r.status_label}</Tag> },
  ]

  if (error) return <Alert type="error" showIcon message={error} />
  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}><Card size="small"><Statistic title="期間已發料領用單" value={summary?.issue_count ?? 0} /></Card></Col>
        <Col span={6}><Card size="small">{summary?.issue_amount == null
          ? <Statistic title="期間領用金額" value="—" />
          : <Statistic title="期間領用金額" value={summary.issue_amount} prefix="$" precision={0} />}</Card></Col>
        <Col span={6}><Card size="small"><Statistic title="待核准" value={summary?.pending_approval ?? 0}
          valueStyle={{ color: (summary?.pending_approval ?? 0) > 0 ? '#d48806' : undefined }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="待發料／待收料" value={summary?.pending_post ?? 0}
          valueStyle={{ color: (summary?.pending_post ?? 0) > 0 ? '#1677ff' : undefined }} /></Card></Col>
      </Row>
      <Space wrap style={{ marginBottom: 12 }}>
        <StockCompanySelect companies={companies} value={code} onChange={setCode} />
        <StandardRangePicker value={range} anchor={summary?.data_end ?? null} onChange={setRange} />
        <Select allowClear placeholder="單據類型" style={{ width: 120 }} value={docType} onChange={setDocType}
          options={(Object.keys(TYPE_LABEL) as IssueDocType[]).map((k) => ({ value: k, label: TYPE_LABEL[k] }))} />
        <Select mode="multiple" allowClear placeholder="狀態" style={{ minWidth: 200 }} value={status} onChange={setStatus} options={STATUS_OPTIONS} />
        <Space size={4}><Switch size="small" checked={mine} onChange={setMine} /><Text>只看我開的</Text></Space>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新讀取</Button>
        {createMenu.length > 0 && meta && (
          <Dropdown menu={{ items: createMenu, onClick: ({ key }) => setEditor({ type: key as IssueDocType, editing: null, ref: null }) }}>
            <Button type="primary" icon={<PlusOutlined />}>新增 <DownOutlined /></Button>
          </Dropdown>
        )}
      </Space>
      {meta && !meta.can_post && meta.my_warehouses.length === 0 && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="您所屬的部門目前沒有倉庫，無法開領用單。請確認「使用者管理」的部門設定，或請倉管建立部門倉。" />)}
      <Table<IssueDoc> size="small" rowKey="id" loading={loading} dataSource={rows} columns={columns} pagination={{ pageSize: 30 }}
        onRow={(r) => ({ onClick: () => openDetail(r.id), style: { cursor: 'pointer' } })} />

      <Drawer open={!!detail} width={760} onClose={() => setDetail(null)}
        title={detail ? (
          <Space>
            <Tag color={TYPE_COLOR[detail.doc_type]}>{detail.doc_type_label}</Tag>
            <span>{`${detail.warehouse_name}：${detail.doc_no}`}</span>
            <Tag color={STATUS_COLOR[detail.status]}>{detail.status_label}</Tag>
          </Space>) : ''}
        extra={detail && (
          <Space>
            {detail.actions.map((a) => (
              <Button key={a} size="small" loading={busy} danger={a === 'reject' || a === 'void' || a === 'cancel'}
                type={a === 'post' || a === 'approve' || a === 'submit' ? 'primary' : 'default'} onClick={() => doAction(a, detail)}>
                {ACTION_LABEL[a]}
              </Button>))}
          </Space>)}>
        {detail && (
          <>
            <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="單據日期">{detail.doc_date}</Descriptions.Item>
              <Descriptions.Item label="過帳日">{detail.posted_date ?? '—'}</Descriptions.Item>
              <Descriptions.Item label={detail.doc_type === 'transfer' ? '調出倉' : '倉庫'}>{detail.warehouse_name}</Descriptions.Item>
              <Descriptions.Item label={detail.doc_type === 'transfer' ? '調入倉' : '部門'}>
                {detail.doc_type === 'transfer' ? detail.to_warehouse_name : detail.department_name || '—'}</Descriptions.Item>
              {detail.doc_type === 'issue' && <Descriptions.Item label="領用人">{detail.requester_name || '—'}</Descriptions.Item>}
              {detail.doc_type === 'issue' && <Descriptions.Item label="成本中心">{detail.cost_center_name || '—'}</Descriptions.Item>}
              {detail.doc_type === 'return' && <Descriptions.Item label="原領用單" span={2}>{detail.ref_issue_no ?? '—'}</Descriptions.Item>}
              <Descriptions.Item label={detail.doc_type === 'scrap' ? '報廢原因' : '用途說明'} span={2}>{detail.purpose || '—'}</Descriptions.Item>
              {meta?.can_see_cost && <Descriptions.Item label="過帳金額" span={2}><b>{detail.status === 'posted' || detail.status === 'voided' ? money(detail.total_amount) : '—'}</b></Descriptions.Item>}
              <Descriptions.Item label="開單">{`${detail.created_by ?? ''} ${detail.created_at ?? ''}`}</Descriptions.Item>
              <Descriptions.Item label="核准">{detail.approved_by ? `${detail.approved_by} ${detail.approved_at ?? ''}` : '—'}</Descriptions.Item>
              <Descriptions.Item label="過帳">{detail.posted_by ? `${detail.posted_by} ${detail.posted_at ?? ''}` : '—'}</Descriptions.Item>
              <Descriptions.Item label="取消／退回／作廢">{detail.closed_by ? `${detail.closed_by}：${detail.close_reason ?? ''}` : '—'}</Descriptions.Item>
            </Descriptions>
            <Table size="small" rowKey="id" pagination={false} dataSource={detail.lines ?? []}
              columns={[
                { title: '料號', key: 'item', render: (_: unknown, l) => `${l.item_code} ${l.item_name}${l.spec ? `（${l.spec}）` : ''}` },
                { title: '數量', key: 'qty', width: 100, align: 'right', render: (_: unknown, l) => `${num(l.qty)} ${l.unit ?? ''}` },
                ...(detail.status === 'pending_approval' || detail.status === 'approved' || detail.status === 'draft'
                  ? [{ title: '目前可用', dataIndex: 'available', width: 90, align: 'right' as const, render: num }] : []),
                ...(meta?.can_see_cost ? [
                  { title: '單價', dataIndex: 'unit_cost', width: 90, align: 'right' as const, render: money },
                  { title: '金額', dataIndex: 'amount', width: 100, align: 'right' as const, render: money },
                ] : []),
                { title: '備註', dataIndex: 'note', width: 140, render: (v: string | null) => v || '—' },
              ]} />
            {(detail.returns?.length ?? 0) > 0 && (
              <div style={{ marginTop: 16 }}>
                <Text strong>退料紀錄：</Text>
                <Space wrap>{detail.returns!.map((r) => <a key={r.id} onClick={() => openDetail(r.id)}>{`${r.doc_no}（${r.status_label}）`}</a>)}</Space>
              </div>)}
          </>
        )}
      </Drawer>

      {meta && editor && (
        <IssueEditor code={code} meta={meta} open docType={editor.type} editing={editor.editing} refIssue={editor.ref}
          onClose={() => setEditor(null)} onDone={(id) => { setEditor(null); afterAction(id) }} />)}

      <Modal open={!!reasonFor} onCancel={() => setReasonFor(null)} onOk={doReason} confirmLoading={busy}
        okButtonProps={{ danger: true }}
        title={reasonFor ? `${reasonFor.action === 'reject' ? '退回' : reasonFor.action === 'void' ? '作廢' : '取消'} ${reasonFor.doc.doc_no}` : ''}
        okText={reasonFor?.action === 'reject' ? '退回' : reasonFor?.action === 'void' ? '作廢' : '取消單據'}>
        {reasonFor?.action === 'void' && <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="作廢會產生反向異動（庫存不足會擋下）。" />}
        {reasonFor && reasonFor.action !== 'void' && reasonFor.doc.doc_type === 'issue' && reasonFor.doc.status !== 'draft' &&
          <Alert type="info" showIcon style={{ marginBottom: 12 }} message="保留的數量會釋放回可用量。" />}
        <Input.TextArea rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
          placeholder={reasonFor?.action === 'cancel' ? '原因（選填）' : '原因（必填）'} />
      </Modal>

      <Modal open={!!postFor} onCancel={() => setPostFor(null)} onOk={doPost} confirmLoading={busy}
        title={postFor ? `${postFor.doc_type === 'issue' ? '發料過帳' : postFor.doc_type === 'return' ? '收料過帳' : '過帳'} ${postFor.doc_no}` : ''}
        okText="過帳">
        <Space direction="vertical">
          <Text>{postFor?.doc_type === 'issue' ? '確認已把東西交給領用人，扣除庫存。' : postFor?.doc_type === 'return' ? '確認已收到退回的東西，加回庫存。' : '確認過帳。'}</Text>
          <Space><Text>異動日期</Text><DatePicker value={postDate} onChange={(d) => d && setPostDate(d)} allowClear={false} /></Space>
        </Space>
      </Modal>
    </div>
  )
}
