/**
 * 庫存管理 — 手機領用（Phase 4b，2026-11-17，docs/SPEC_stock_management.md §7.4、§12.2）
 *
 * 路由：/m/stock/issue      權限：沿用桌面 stock_issue_create（不新增 key；倉管 stock_issue_post 也可用）
 * 線上操作（不離線，D9）；API 與桌面「領用單」完全相同，規則（可用量、保留、部門範圍、核准）都由後端判斷。
 *
 * 進入方式：
 *   1. 底部選單「領用」
 *   2. 掃料號 QR 標籤（手機內建相機）→ /m/stock/issue?co=CH&wh=3&item=C0101001
 *      自動選公司、倉庫並加入該料號（數量 1），處理完就把參數從網址拿掉，重新整理不會重複加入。
 *
 * 手機版刻意捨棄（留在桌面）：退料、調撥、報廢、核准、發料、單價金額。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import {
  Alert, Button, Card, Drawer, Empty, Input, InputNumber, List, Popconfirm, Segmented, Select, Space, Spin, Tag, Typography, message,
} from 'antd'
import { DeleteOutlined, InboxOutlined, PlusOutlined, SendOutlined, SnippetsOutlined } from '@ant-design/icons'
import {
  cancelIssue, createIssue, errMsg, fetchAvailable, fetchIssue, fetchIssueCostCenters, fetchIssueMeta, fetchIssueTemplates,
  fetchIssues, type AvailableItem, type IssueDoc, type IssueMeta, type IssueTemplate,
} from '@/api/stock'
import { useStockCompany } from '@/pages/Stock/StockCompanySelect'

const { Text, Title } = Typography
const num = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: 4 }))
const STATUS_COLOR: Record<string, string> = {
  draft: 'default', pending_approval: 'gold', approved: 'blue', posted: 'green', cancelled: 'default', rejected: 'red', voided: 'default',
}
const WH_KEY = 'stock_m_wh'

interface Line { item_id: number; qty: number }

export default function MobileStockIssue() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { companies, code, setCode, error } = useStockCompany()
  const [tab, setTab] = useState<'new' | 'mine'>('new')
  const [meta, setMeta] = useState<IssueMeta | null>(null)
  const [whId, setWhId] = useState<number | undefined>()
  const [avail, setAvail] = useState<AvailableItem[]>([])
  const [availFor, setAvailFor] = useState<number | undefined>()   // avail 是哪個倉的（避免用到還沒載入的清單）
  const [loadingAvail, setLoadingAvail] = useState(false)
  const [lines, setLines] = useState<Line[]>([])
  const [purpose, setPurpose] = useState('')
  const [ccId, setCcId] = useState<number | undefined>()
  const [ccs, setCcs] = useState<{ id: number; label: string }[]>([])
  const [templates, setTemplates] = useState<IssueTemplate[]>([])
  const [saving, setSaving] = useState(false)
  const [mine, setMine] = useState<IssueDoc[]>([])
  const [loadingMine, setLoadingMine] = useState(false)
  const [detail, setDetail] = useState<IssueDoc | null>(null)
  const pendingItem = useRef<string | null>(params.get('item'))
  const pendingWh = useRef<number | null>(params.get('wh') ? Number(params.get('wh')) : null)
  const pendingCo = useRef<string | null>(params.get('co'))

  // QR 帶的公司：先切到該公司，切好之前不讀倉庫（否則會拿錯公司的倉庫與料號）
  useEffect(() => {
    const qc = pendingCo.current
    if (!qc || !companies.length) return
    if (!companies.some((c) => c.code === qc)) {
      message.warning('您沒有標籤上這家公司的庫存權限')
      pendingCo.current = null; pendingWh.current = null; pendingItem.current = null
      navigate('/m/stock/issue', { replace: true })
      return
    }
    if (qc !== code) setCode(qc)
  }, [companies, code, setCode, navigate])

  // 公司 → 可用倉庫
  useEffect(() => {
    if (!code) return
    if (pendingCo.current && pendingCo.current !== code) return
    pendingCo.current = null
    setMeta(null); setWhId(undefined); setLines([])
    fetchIssueMeta(code).then((r) => {
      setMeta(r.data)
      const list = r.data.my_warehouses.filter((w) => w.status === 'active')
      let saved: number | null = null
      try { saved = Number(localStorage.getItem(WH_KEY)) || null } catch { /* ignore */ }
      const pick = [pendingWh.current, saved].find((id) => id && list.some((w) => w.id === id)) ?? (list.length === 1 ? list[0].id : undefined)
      setWhId(pick ?? undefined)
      if (pendingWh.current && !list.some((w) => w.id === pendingWh.current)) {
        message.warning('標籤上的倉庫不是您所屬部門的倉，請自行選擇倉庫')
      }
      pendingWh.current = null
    }).catch((e) => message.error(errMsg(e, '讀取設定失敗')))
  }, [code])

  // 倉庫 → 可領料號、範本、成本中心
  useEffect(() => {
    setAvailFor(undefined)
    if (!code || !whId) { setAvail([]); setTemplates([]); return }
    try { localStorage.setItem(WH_KEY, String(whId)) } catch { /* ignore */ }
    setLoadingAvail(true)
    fetchAvailable(code, whId).then((r) => { setAvail(r.data); setAvailFor(whId) })
      .catch((e) => message.error(errMsg(e, '讀取料號失敗')))
      .finally(() => setLoadingAvail(false))
    fetchIssueTemplates(code, whId).then((r) => setTemplates(r.data)).catch(() => setTemplates([]))
    fetchIssueCostCenters(code, whId).then((r) => { setCcs(r.data.items); setCcId(r.data.default_id ?? undefined) }).catch(() => setCcs([]))
  }, [code, whId])

  const availMap = useMemo(() => new Map(avail.map((a) => [a.item_id, a])), [avail])

  // QR 帶的料號：料號清單載入後加入一次，並把參數從網址拿掉
  useEffect(() => {
    const ic = pendingItem.current
    if (!ic || !whId || !meta || availFor !== whId) return
    pendingItem.current = null
    navigate('/m/stock/issue', { replace: true })
    const a = avail.find((x) => x.item_code === ic)
    if (!a) { message.warning(`料號 ${ic} 在這個倉目前沒有可用庫存`); return }
    setLines((ls) => (ls.some((l) => l.item_id === a.item_id)
      ? ls.map((l) => (l.item_id === a.item_id ? { ...l, qty: Math.min(l.qty + 1, a.available) } : l))
      : [...ls, { item_id: a.item_id, qty: 1 }]))
    message.success(`已加入：${a.item_name}`)
  }, [avail, availFor, whId, meta, navigate])

  const addItem = (id: number) => {
    if (lines.some((l) => l.item_id === id)) { message.info('已在清單中'); return }
    setLines((ls) => [...ls, { item_id: id, qty: 1 }])
  }
  const applyTemplate = (id: number) => {
    const t = templates.find((x) => x.id === id)
    if (!t) return
    const ok = t.lines.filter((l) => availMap.has(l.item_id))
    setLines(ok.map((l) => ({ item_id: l.item_id, qty: Math.min(l.qty, availMap.get(l.item_id)!.available) })))
    const miss = t.lines.length - ok.length
    message.success(`已套用「${t.name}」${miss ? `（${miss} 筆目前沒有庫存，已略過）` : ''}`)
  }

  const submit = async () => {
    if (!whId) { message.warning('請選擇倉庫'); return }
    const use = lines.filter((l) => l.qty > 0)
    if (!use.length) { message.warning('請加入要領的料號'); return }
    setSaving(true)
    try {
      const r = await createIssue(code, {
        doc_type: 'issue', warehouse_id: whId, doc_date: dayjs().format('YYYY-MM-DD'),
        purpose: purpose || null, cost_center_id: ccId ?? null, requester_name: meta?.user_name ?? null,
        lines: use.map((l) => ({ item_id: l.item_id, qty: l.qty })), then: 'submit',
      })
      message.success(`已送出 ${r.data.doc_no}，${r.data.status === 'pending_approval' ? '等主管核准' : '等倉管發料'}`)
      setLines([]); setPurpose('')
      fetchAvailable(code, whId).then((x) => setAvail(x.data)).catch(() => undefined)
      setTab('mine')
    } catch (e) {
      message.error(errMsg(e, '送出失敗'))
    } finally { setSaving(false) }
  }

  const loadMine = useCallback(async () => {
    if (!code) return
    setLoadingMine(true)
    try { setMine((await fetchIssues(code, { doc_type: 'issue', mine: true })).data.slice(0, 50)) }
    catch (e) { message.error(errMsg(e, '讀取我的領用單失敗')) } finally { setLoadingMine(false) }
  }, [code])
  useEffect(() => { if (tab === 'mine') loadMine() }, [tab, loadMine])

  const openDetail = async (id: number) => {
    try { setDetail((await fetchIssue(code, id)).data) } catch (e) { message.error(errMsg(e, '讀取失敗')) }
  }
  const doCancel = async (d: IssueDoc) => {
    try { await cancelIssue(code, d.id, '手機取消'); message.success('已取消，保留的數量已釋放'); setDetail(null); loadMine() }
    catch (e) { message.error(errMsg(e, '取消失敗')) }
  }

  if (error) return <Alert type="error" showIcon message={error} />
  const whList = (meta?.my_warehouses ?? []).filter((w) => w.status === 'active')
  const whSel = whList.find((w) => w.id === whId)

  return (
    <div>
      <Title level={5} style={{ color: '#1B3A5C', marginTop: 0 }}><InboxOutlined /> 領用</Title>
      <Segmented block value={tab} onChange={(v) => setTab(v as 'new' | 'mine')} style={{ marginBottom: 12 }}
        options={[{ label: '開領用單', value: 'new' }, { label: '我的領用單', value: 'mine' }]} />

      {tab === 'new' && (
        <>
          <Space direction="vertical" style={{ width: '100%' }} size={8}>
            {companies.length > 1 && (
              <Select style={{ width: '100%' }} value={code || undefined} onChange={setCode}
                options={companies.map((c) => ({ value: c.code, label: c.name }))} />)}
            <Select style={{ width: '100%' }} placeholder="選擇倉庫" value={whId} onChange={(v) => { setWhId(v); setLines([]) }}
              notFoundContent="您所屬的部門沒有倉庫"
              options={whList.map((w) => ({ value: w.id, label: w.department_name ? `${w.name}（${w.department_name}）` : w.name }))} />
            {meta && whList.length === 0 && <Alert type="warning" showIcon message="您所屬的部門目前沒有倉庫，無法領用。請洽倉管。" />}
            {whSel?.issue_requires_approval && <Alert type="info" showIcon message="這個倉的領用單需主管核准後才發料" />}
            {templates.length > 0 && (
              <Select style={{ width: '100%' }} placeholder="套用常用範本" value={null} suffixIcon={<SnippetsOutlined />}
                onChange={(v: number) => applyTemplate(v)}
                options={templates.map((t) => ({ value: t.id, label: `${t.name}（${t.lines.length} 項）` }))} />)}
            <Select showSearch style={{ width: '100%' }} placeholder="搜尋料號或品名加入" value={null} disabled={!whId}
              optionFilterProp="label" suffixIcon={<PlusOutlined />} onChange={(v: number) => addItem(v)}
              notFoundContent={loadingAvail ? <Spin size="small" /> : '這個倉沒有可用庫存的料號'}
              options={avail.map((a) => ({ value: a.item_id, label: `${a.item_code} ${a.item_name}${a.spec ? ` ${a.spec}` : ''}` }))} />
          </Space>

          <List style={{ marginTop: 12 }} dataSource={lines}
            locale={{ emptyText: <Empty description="掃描料號標籤，或從上方搜尋加入" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            renderItem={(l) => {
              const a = availMap.get(l.item_id)
              return (
                <Card size="small" style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600 }}>{a?.item_name ?? `料號 ${l.item_id}`}</div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{`${a?.item_code ?? ''}｜可用 ${num(a?.available)} ${a?.unit ?? ''}`}</Text>
                    </div>
                    <InputNumber min={0} max={a?.available} value={l.qty} style={{ width: 90 }} inputMode="decimal"
                      onChange={(v) => setLines((ls) => ls.map((x) => (x.item_id === l.item_id ? { ...x, qty: v ?? 0 } : x)))} />
                    <Button type="text" danger icon={<DeleteOutlined />} aria-label="移除"
                      onClick={() => setLines((ls) => ls.filter((x) => x.item_id !== l.item_id))} />
                  </div>
                </Card>)
            }} />

          {lines.length > 0 && (
            <Space direction="vertical" style={{ width: '100%', marginTop: 4 }} size={8}>
              <Input.TextArea rows={2} placeholder="用途說明（選填）" value={purpose} onChange={(e) => setPurpose(e.target.value)} />
              {ccs.length > 0 && (
                <Select allowClear showSearch optionFilterProp="label" style={{ width: '100%' }} placeholder="成本中心"
                  value={ccId} onChange={setCcId} options={ccs.map((c) => ({ value: c.id, label: c.label }))} />)}
              <Button type="primary" block size="large" icon={<SendOutlined />} loading={saving} onClick={submit}>
                {`送出領用單（${lines.filter((l) => l.qty > 0).length} 項）`}
              </Button>
            </Space>)}
        </>
      )}

      {tab === 'mine' && (
        <Spin spinning={loadingMine}>
          <List dataSource={mine} locale={{ emptyText: <Empty description="還沒有領用單" /> }}
            renderItem={(d) => (
              <Card size="small" style={{ marginBottom: 8 }} onClick={() => openDetail(d.id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space direction="vertical" size={0}>
                    <Text strong>{d.doc_no}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>{`${d.doc_date}｜${d.warehouse_name}｜${d.line_count} 項`}</Text>
                  </Space>
                  <Tag color={STATUS_COLOR[d.status]}>{d.status_label}</Tag>
                </div>
              </Card>)} />
        </Spin>
      )}

      <Drawer open={!!detail} placement="bottom" height="75%" onClose={() => setDetail(null)}
        title={detail ? (
          <Space><Tag color="blue">領用單</Tag><span>{`${detail.warehouse_name}：${detail.doc_no}`}</span></Space>) : ''}
        extra={detail && detail.actions.includes('cancel') ? (
          <Popconfirm title="取消這張領用單？" onConfirm={() => doCancel(detail)}>
            <Button size="small" danger>取消</Button>
          </Popconfirm>) : undefined}>
        {detail && (
          <>
            <Space wrap style={{ marginBottom: 8 }}>
              <Tag color={STATUS_COLOR[detail.status]}>{detail.status_label}</Tag>
              <Text type="secondary">{detail.doc_date}</Text>
            </Space>
            {detail.purpose && <div style={{ marginBottom: 8 }}>{detail.purpose}</div>}
            {detail.close_reason && <Alert type="warning" showIcon style={{ marginBottom: 8 }} message={`${detail.closed_by ?? ''}：${detail.close_reason}`} />}
            <List dataSource={detail.lines ?? []} renderItem={(l) => (
              <List.Item>
                <List.Item.Meta title={l.item_name} description={l.item_code} />
                <Text strong>{`${num(l.qty)} ${l.unit ?? ''}`}</Text>
              </List.Item>)} />
          </>
        )}
      </Drawer>
    </div>
  )
}
