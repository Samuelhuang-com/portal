/**
 * 現場營運稽核 — 期別明細（公司 → 受稽部門 → 稽核項目 ＋ 小計）
 * route: /audit-check/kpo/periods/:id     permissionKey: audit_check_view（編輯需 audit_check_edit）
 *
 * 2026-10-11 起的層級（比照 audit-check）：期別 → 公司別稽核單 → 受稽部門 → 稽核項目。
 *   受稽部門在「新增公司別稽核單」時選（來源＝現場營運稽核項目的部門，與公司別無連動），
 *   之後可用「受稽部門」按鈕增減。
 * 流程：每個部門按「選擇項目」→ 從該部門主檔勾選本期要稽核的項目（通常 1★＋3 項＝25 分）
 *       → 逐項標記「符合／不符合」並填查核備註 → 小計由系統即時計算（不可手改）。
 * 小計欄位：選定項數（★n）／滿分／符合／不符合／未查核／得分／本期分數（得分÷滿分×100，不呈現 %）。
 *
 * 選定後的項目內容是**快照**：在明細 Drawer 內編輯只改本期，不影響主檔與其他期別；
 * 要改主檔請到「現場營運稽核項目」。
 *
 * 2026-10-10：
 *   - 每個部門表格下方加小計列（與頁首記分板同款，只是依部門呈現）
 *   - 部門、部門內的品質項目都可拖曳調整順序（只影響本期；需 audit_check_edit）
 *   - 「備註（查核方式）」改用稽核檢查的 Web 編輯器（RichTextEditor），
 *     點選項目列以明細 Drawer 呈現與編輯（CLAUDE.md §7 明細 Drawer 規範）
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type React from 'react'
import { DndContext, PointerSensor, closestCenter, useSensor, useSensors } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Button, Card, Checkbox, Col, Descriptions, Divider, Drawer, Empty, Form, Input, InputNumber, Modal,
  Popconfirm, Radio, Row, Select, Space, Spin, Statistic, Switch, Table, Tag, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ArrowLeftOutlined, BankOutlined, CheckSquareOutlined, ColumnHeightOutlined, DeleteOutlined, DownOutlined,
  EditOutlined, FileWordOutlined, HolderOutlined, PlusOutlined, ReloadOutlined, RightOutlined, SaveOutlined, TeamOutlined,
  VerticalAlignMiddleOutlined,
} from '@ant-design/icons'

import { downloadFile } from '@/api/downloadFile'
import { kpoDeptApi, kpoItemApi, kpoPeriodApi } from '@/api/auditKpo'
import type {
  KpoDept, KpoDeptBlock, KpoDeptHistory, KpoItem, KpoLine, KpoPeriodDetail, KpoSheetBlock, KpoSubtotal,
} from '@/api/auditKpo'
import { useAuthStore } from '@/stores/authStore'
import RichTextEditor from '../RichTextEditor'
import { RICH_TEXT_CSS, htmlToPlain, toDisplayHtml } from '../richText'
import SheetCreateModal from './SheetCreateModal'

const { Title, Text } = Typography

const EMPTY_SUBTOTAL: KpoSubtotal = {
  item_count: 0, key_count: 0, full_score: 0, pass_count: 0, fail_count: 0,
  pending_count: 0, earned_score: 0, rate: null, score100: null,
}

/** 本期分數：得分÷滿分×100 的整數（後端計算），不呈現 %；滿分 0 → — */
function fmtScore100(v: number | null): string {
  return v == null ? '—' : String(v)
}

/** 備註（查核方式）顯示：Web 編輯器產生的 HTML（舊資料為純文字，toDisplayHtml 會處理） */
function RichView({ html, color }: { html: string | null; color?: string }) {
  const h = toDisplayHtml(html)
  if (!h) return <span style={{ color: '#bfbfbf' }}>—</span>
  return <div className="audit-rich" style={{ color }} dangerouslySetInnerHTML={{ __html: h }} />
}

/** 記分板：選定項數（★n）／滿分／符合／不符合／未查核／得分／本期分數。部門、公司、整期三層共用 */
function ScoreRow({ s }: { s: KpoSubtotal }) {
  return (
    <Row gutter={[16, 8]}>
      <Col flex="1 1 130px"><Statistic title="選定項數" value={s.item_count} suffix={`（★${s.key_count}）`} /></Col>
      <Col flex="1 1 90px"><Statistic title="滿分" value={s.full_score} /></Col>
      <Col flex="1 1 90px"><Statistic title="符合" value={s.pass_count} valueStyle={{ color: '#389e0d' }} /></Col>
      <Col flex="1 1 90px"><Statistic title="不符合" value={s.fail_count} valueStyle={{ color: '#cf1322' }} /></Col>
      <Col flex="1 1 90px"><Statistic title="未查核" value={s.pending_count} /></Col>
      <Col flex="1 1 90px"><Statistic title="得分" value={s.earned_score} /></Col>
      <Col flex="1 1 100px"><Statistic title="本期分數" value={fmtScore100(s.score100)} valueStyle={{ color: '#1B3A5C', fontWeight: 600 }} /></Col>
    </Row>
  )
}

/** 部門小計列：與頁首記分板同款，只是依部門呈現 */
function DeptScoreboard({ s }: { s: KpoSubtotal }) {
  return (
    <Card size="small" style={{ marginTop: 8, background: '#fafafa' }}>
      <ScoreRow s={s} />
    </Card>
  )
}

// ── 拖曳排序元件（@dnd-kit，專案既有套件）───────────────────────────────
type HandleCtx = {
  setActivatorNodeRef: (el: HTMLElement | null) => void
  listeners: Record<string, unknown> | undefined
  disabled: boolean
} | null
const RowHandleContext = createContext<HandleCtx>(null)

function DragHandle({ title }: { title: string }) {
  const ctx = useContext(RowHandleContext)
  if (!ctx) return null
  return (
    <span
      ref={ctx.setActivatorNodeRef} {...(ctx.disabled ? {} : ctx.listeners)}
      title={ctx.disabled ? '' : title}
      onClick={(e) => e.stopPropagation()}
      style={{ cursor: ctx.disabled ? 'default' : 'grab', color: ctx.disabled ? '#d9d9d9' : '#8c8c8c', touchAction: 'none', padding: '0 4px' }}
    >
      <HolderOutlined />
    </span>
  )
}

/** antd Table 的可拖曳列（拖曳把手在列內的 <DragHandle/>） */
function SortableRow(props: React.HTMLAttributes<HTMLTableRowElement> & { 'data-row-key': number; disabled?: boolean }) {
  const { 'data-row-key': rowKey, disabled, style, children, ...rest } = props
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } =
    useSortable({ id: rowKey, disabled })
  const merged: React.CSSProperties = {
    ...style,
    transform: CSS.Transform.toString(transform ? { ...transform, scaleY: 1 } : null),
    transition,
    ...(isDragging ? { position: 'relative', zIndex: 9, background: '#e6f4ff' } : {}),
  }
  return (
    <RowHandleContext.Provider value={{ setActivatorNodeRef, listeners, disabled: !!disabled }}>
      <tr {...rest} ref={setNodeRef} style={merged} {...attributes}>{children}</tr>
    </RowHandleContext.Provider>
  )
}

/** 部門卡片：整張可拖曳排序，把手在標題列左側 */
function SortableDeptCard(props: {
  id: string; disabled: boolean; collapsed: boolean; onToggle: () => void
  title: React.ReactNode; extra?: React.ReactNode; children: React.ReactNode
}) {
  const { id, disabled, collapsed, onToggle, title, extra, children } = props
  const { setNodeRef, setActivatorNodeRef, attributes, listeners, transform, transition, isDragging } =
    useSortable({ id, disabled })
  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform ? { ...transform, scaleX: 1, scaleY: 1 } : null),
    transition,
    marginBottom: 12,
    ...(isDragging ? { position: 'relative', zIndex: 10, opacity: 0.9, boxShadow: '0 4px 14px rgba(0,0,0,.18)' } : {}),
  }
  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <Card size="small" styles={{ header: { background: '#fafafa' }, body: collapsed ? { display: 'none' } : undefined }}
        title={
          <Space wrap>
            <span
              ref={setActivatorNodeRef} {...(disabled ? {} : listeners)} title={disabled ? '' : '拖曳調整部門順序'}
              style={{ cursor: disabled ? 'default' : 'grab', color: disabled ? '#d9d9d9' : '#8c8c8c', touchAction: 'none' }}
            >
              <HolderOutlined />
            </span>
            <span onClick={onToggle} style={{ cursor: 'pointer' }}>{collapsed ? <RightOutlined /> : <DownOutlined />}</span>
            {title}
          </Space>
        }
        extra={extra}
      >
        {children}
      </Card>
    </div>
  )
}

function SubtotalTags({ s }: { s: KpoSubtotal }) {
  return (
    <Space size={[4, 4]} wrap>
      <Tag color="blue">選定 {s.item_count} 項</Tag>
      <Tag color="gold">★ {s.key_count}</Tag>
      <Tag>滿分 {s.full_score}</Tag>
      <Tag color="green">符合 {s.pass_count}</Tag>
      <Tag color="red">不符合 {s.fail_count}</Tag>
      <Tag>未查核 {s.pending_count}</Tag>
      <Tag color="geekblue">得分 {s.earned_score}</Tag>
      <Tag color="purple">本期分數 {fmtScore100(s.score100)}</Tag>
    </Space>
  )
}

export default function AuditKpoPeriodEditorPage() {
  const { id } = useParams()
  const periodId = Number(id)
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('audit_check_edit')
  const canAdmin = hasPermission('audit_check_admin')

  const [detail, setDetail] = useState<KpoPeriodDetail | null>(null)
  const [allDepts, setAllDepts] = useState<KpoDept[]>([])
  const [masterItems, setMasterItems] = useState<KpoItem[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [d, dp, it] = await Promise.all([
        kpoPeriodApi.get(periodId), kpoDeptApi.list(), kpoItemApi.list(),
      ])
      setDetail(d.data)
      setAllDepts(dp.data.filter((x) => x.is_active))
      setMasterItems(it.data.filter((x) => x.is_active))
    } catch {
      message.error('載入 現場營運稽核期別失敗')
    } finally {
      setLoading(false)
    }
  }, [periodId])

  useEffect(() => { load() }, [load])

  // ── 拖曳排序（公司稽核單內的部門、部門內項目）──────────────────────────
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))
  const deptKey = (sheetId: number, deptId: number) => `d-${sheetId}-${deptId}`
  const [collapsedDepts, setCollapsedDepts] = useState<Set<string>>(new Set())
  const toggleCollapsed = (key: string) => setCollapsedDepts((prev) => {
    const n = new Set(prev)
    if (n.has(key)) n.delete(key); else n.add(key)
    return n
  })
  const collapseAll = () => setCollapsedDepts(new Set(
    (detail?.sheets ?? []).flatMap((sh) => sh.departments.map((d) => deptKey(sh.id, d.department_id)))))
  const expandAll = () => setCollapsedDepts(new Set())

  const patchSheet = (sheetId: number, fn: (sh: KpoSheetBlock) => KpoSheetBlock) =>
    setDetail((cur) => (cur ? { ...cur, sheets: cur.sheets.map((sh) => (sh.id === sheetId ? fn(sh) : sh)) } : cur))

  const onDeptDragEnd = async (sheet: KpoSheetBlock, e: DragEndEvent) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const ids = sheet.departments.map((d) => deptKey(sheet.id, d.department_id))
    const from = ids.indexOf(String(active.id)); const to = ids.indexOf(String(over.id))
    if (from < 0 || to < 0) return
    const next = arrayMove(sheet.departments, from, to)
    patchSheet(sheet.id, (sh) => ({ ...sh, departments: next }))      // 先更新畫面
    try {
      const res = await kpoPeriodApi.setDeptOrder(periodId, sheet.id, next.map((d) => d.department_id))
      setDetail(res.data)
    } catch {
      message.error('儲存部門順序失敗')
      load()
    }
  }

  const onLinesDragEnd = async (sheet: KpoSheetBlock, block: KpoDeptBlock, e: DragEndEvent) => {
    const { active, over } = e
    if (!over || active.id === over.id) return
    const ids = block.lines.map((l) => l.id)
    const from = ids.indexOf(Number(active.id)); const to = ids.indexOf(Number(over.id))
    if (from < 0 || to < 0) return
    const next = arrayMove(block.lines, from, to)
    patchSheet(sheet.id, (sh) => ({
      ...sh,
      departments: sh.departments.map((b) => (b.department_id === block.department_id ? { ...b, lines: next } : b)),
    }))
    try {
      const res = await kpoPeriodApi.setLinesOrder(periodId, sheet.id, block.department_id, next.map((l) => l.id))
      setDetail(res.data)
    } catch {
      message.error('儲存項目順序失敗')
      load()
    }
  }

  // ── 選擇項目（每張公司稽核單、每個受稽部門各自選定）───────────────────────
  const [pickCtx, setPickCtx] = useState<{ sheetId: number; company: string; block: KpoDeptBlock } | null>(null)
  const [picked, setPicked] = useState<number[]>([])
  const [pickSaving, setPickSaving] = useState(false)

  const [pickHistory, setPickHistory] = useState<KpoDeptHistory | null>(null)

  const openPick = (sheet: KpoSheetBlock, block: KpoDeptBlock) => {
    setPickCtx({ sheetId: sheet.id, company: sheet.company_name, block })
    setPicked(block.lines.map((l) => l.source_item_id).filter((x): x is number => x != null))
    // 同公司、同部門在其他期別的歷史（期別數／分數／平均分數、各項目曾選過的期別＋判定）
    setPickHistory(null)
    kpoPeriodApi.deptHistory(periodId, sheet.id, block.department_id)
      .then((r) => setPickHistory(r.data))
      .catch(() => message.warning('載入歷史期別失敗（不影響選擇項目）'))
  }

  const pickItems = useMemo(
    () => masterItems.filter((i) => i.department_id === pickCtx?.block.department_id),
    [masterItems, pickCtx],
  )
  const pickSum = useMemo(() => {
    const sel = pickItems.filter((i) => picked.includes(i.id))
    return {
      count: sel.length, key: sel.filter((i) => i.is_key).length,
      score: sel.reduce((a, b) => a + b.score, 0),
    }
  }, [pickItems, picked])

  const savePick = async () => {
    if (!pickCtx) return
    // 取消勾選會一併移除該項已填的判定與備註 → 先提醒
    const dropped = pickCtx.block.lines.filter((l) => l.source_item_id != null && !picked.includes(l.source_item_id)
      && (l.result || l.remark))
    if (dropped.length > 0) {
      const ok = await new Promise<boolean>((resolve) => Modal.confirm({
        title: `取消勾選 ${dropped.length} 個已填判定／備註的項目？`,
        content: '這些項目的判定與查核備註會一併移除。',
        okText: '確定移除', okButtonProps: { danger: true }, cancelText: '返回',
        onOk: () => resolve(true), onCancel: () => resolve(false),
      }))
      if (!ok) return
    }
    setPickSaving(true)
    try {
      const res = await kpoPeriodApi.setSelection(periodId, pickCtx.sheetId, pickCtx.block.department_id, picked)
      setDetail(res.data)
      setPickCtx(null)
      message.success('已更新選定項目')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '儲存失敗')
    } finally {
      setPickSaving(false)
    }
  }

  // ── 公司稽核單：新增／調整受稽部門／刪除 ────────────────────────────────
  const [sheetModalOpen, setSheetModalOpen] = useState(false)
  const [deptEdit, setDeptEdit] = useState<KpoSheetBlock | null>(null)
  const [deptEditIds, setDeptEditIds] = useState<number[]>([])
  const [deptEditSaving, setDeptEditSaving] = useState(false)

  const openDeptEdit = (sh: KpoSheetBlock) => {
    setDeptEdit(sh)
    setDeptEditIds(sh.departments.map((d) => d.department_id))
  }
  const saveDeptEdit = async () => {
    if (!deptEdit) return
    if (deptEditIds.length === 0) { message.warning('至少保留一個受稽部門'); return }
    const removed = deptEdit.departments.filter((d) => !deptEditIds.includes(d.department_id) && d.lines.length > 0)
    if (removed.length > 0) {
      const ok = await new Promise<boolean>((resolve) => Modal.confirm({
        title: `移除 ${removed.length} 個已選定項目的部門？`,
        content: `${removed.map((d) => d.department_name).join('、')} 的選定項目、判定與備註會一併刪除。`,
        okText: '確定移除', okButtonProps: { danger: true }, cancelText: '返回',
        onOk: () => resolve(true), onCancel: () => resolve(false),
      }))
      if (!ok) return
    }
    setDeptEditSaving(true)
    try {
      const res = await kpoPeriodApi.setSheetDepartments(periodId, deptEdit.id, deptEditIds)
      setDetail(res.data)
      setDeptEdit(null)
      message.success('已更新受稽部門')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '儲存失敗')
    } finally {
      setDeptEditSaving(false)
    }
  }
  const removeSheet = async (sh: KpoSheetBlock) => {
    try {
      const res = await kpoPeriodApi.removeSheet(periodId, sh.id)
      setDetail(res.data)
      message.success(`已刪除「${sh.company_name}」稽核單`)
    } catch {
      message.error('刪除失敗')
    }
  }

  // ── 判定／備註（就地儲存）──────────────────────────────────────────────
  const patchLine = async (lineId: number, body: Parameters<typeof kpoPeriodApi.updateLine>[2]) => {
    try {
      const res = await kpoPeriodApi.updateLine(periodId, lineId, body)
      setDetail(res.data)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '儲存失敗')
    }
  }

  // ── 明細 Drawer：檢視／編輯本期項目內容（只影響本期）──────────────────────
  const [detailLine, setDetailLine] = useState<KpoLine | null>(null)
  const [detailCtx, setDetailCtx] = useState<{ company: string; dept: string } | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [method, setMethod] = useState('')
  const [remark, setRemark] = useState('')
  const [drawerSaving, setDrawerSaving] = useState(false)
  const [editForm] = Form.useForm()

  const openDetail = (ln: KpoLine, company: string, dept: string) => {
    setDetailLine(ln)
    setDetailCtx({ company, dept })
    setEditMode(false)
    setMethod(ln.method ?? '')
    setRemark(ln.remark ?? '')
  }
  const saveDetail = async () => {
    if (!detailLine) return
    const v = await editForm.validateFields()
    setDrawerSaving(true)
    try {
      const res = await kpoPeriodApi.updateLine(periodId, detailLine.id, {
        name: v.name, is_key: v.is_key, score: v.score, method: htmlToPlain(method) ? method : null,
        remark: htmlToPlain(remark) ? remark : '',
      })
      setDetail(res.data)
      const fresh = res.data.sheets.flatMap((sh) => sh.departments).flatMap((b) => b.lines)
        .find((l) => l.id === detailLine.id) ?? null
      setDetailLine(fresh)
      setEditMode(false)
      message.success('已儲存')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '儲存失敗')
    } finally {
      setDrawerSaving(false)
    }
  }

  const makeColumns = (company: string, dept: string): ColumnsType<KpoLine> => [
    { title: '', width: 34, align: 'center', render: () => <DragHandle title="拖曳調整項目順序" /> },
    {
      title: '項數', width: 70, align: 'center',
      render: (_, r) => (r.is_key ? <Tag color="gold">★{r.item_no ?? ''}</Tag> : <span>{r.item_no ?? ''}</span>),
    },
    { title: '品質項目', dataIndex: 'name', width: 200, render: (v: string) => <div style={{ whiteSpace: 'pre-wrap' }}>{v}</div> },
    { title: '分數', dataIndex: 'score', width: 64, align: 'right' },
    {
      title: '備註（查核方式）', dataIndex: 'method', width: 320,
      render: (v: string | null) => <RichView html={v} color="#64748b" />,
    },
    {
      title: '判定', width: 170, align: 'center',
      render: (_, r) => (
        <div onClick={(e) => e.stopPropagation()}>
        <Radio.Group size="small" value={r.result ?? ''} disabled={!canEdit} buttonStyle="solid"
          onChange={(e) => patchLine(r.id, { result: e.target.value })}>
          <Radio.Button value="pass"
            style={r.result === 'pass' ? { background: '#389e0d', borderColor: '#389e0d', color: '#fff' } : undefined}>符合</Radio.Button>
          <Radio.Button value="fail"
            style={r.result === 'fail' ? { background: '#cf1322', borderColor: '#cf1322', color: '#fff' } : undefined}>不符合</Radio.Button>
          <Radio.Button value="">—</Radio.Button>
        </Radio.Group>
        </div>
      ),
    },
    {
      title: '查核備註', width: 320,
      render: (_, r) => <RichView html={r.remark} />,
    },
    {
      title: '', width: 50, align: 'center',
      render: (_, r) => (
        <Button size="small" type="text" icon={<EditOutlined />} title="明細" onClick={(e) => { e.stopPropagation(); openDetail(r, company, dept) }} />
      ),
    },
  ]

  if (loading && !detail) return <Spin style={{ display: 'block', margin: '80px auto' }} />
  if (!detail) return <Empty description="查無此期別" />

  const total = detail.total ?? EMPTY_SUBTOTAL
  const deptCount = detail.sheets.reduce((n, sh) => n + sh.departments.length, 0)

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }} wrap>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/audit-check/kpo')}>返回</Button>
          <div>
            <Title level={4} style={{ margin: 0 }}>{detail.period}　{detail.title}</Title>
            {detail.note && <Text type="secondary">{detail.note}</Text>}
          </div>
        </Space>
        <Space>
          {canEdit && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setSheetModalOpen(true)}>新增公司稽核單</Button>
          )}
          <Button icon={<ColumnHeightOutlined />} onClick={expandAll}>全部展開</Button>
          <Button icon={<VerticalAlignMiddleOutlined />} onClick={collapseAll}>全部收合</Button>
          <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
        </Space>
      </Space>

      <Card size="small" style={{ marginBottom: 12 }} title={<Space><b>整期合計</b><Text type="secondary">{detail.sheets.length} 家公司・{deptCount} 個受稽部門</Text></Space>}>
        <ScoreRow s={total} />
      </Card>

      {detail.sheets.length === 0 && (
        <Card size="small">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未建立任何公司別稽核單">
            {canEdit && <Button type="primary" icon={<PlusOutlined />} onClick={() => setSheetModalOpen(true)}>新增公司稽核單</Button>}
          </Empty>
        </Card>
      )}

      {detail.sheets.map((sh) => (
        <Card
          key={sh.id} size="small" style={{ marginBottom: 16, borderColor: '#1B3A5C' }}
          styles={{ header: { background: '#eef3f8' } }}
          title={
            <Space wrap>
              <BankOutlined />
              <b style={{ color: '#1B3A5C' }}>{sh.company_name}</b>
              <Text type="secondary">{sh.departments.length} 個受稽部門</Text>
              <SubtotalTags s={sh.total} />
            </Space>
          }
          extra={
            <Space>
              {canEdit && <Button size="small" icon={<TeamOutlined />} onClick={() => openDeptEdit(sh)}>受稽部門</Button>}
              {canAdmin && (
                <Popconfirm title={`刪除「${sh.company_name}」稽核單？其選定項目與判定都會一併刪除`} okText="刪除"
                  okButtonProps={{ danger: true }} onConfirm={() => removeSheet(sh)}>
                  <Button size="small" danger type="text" icon={<DeleteOutlined />} />
                </Popconfirm>
              )}
            </Space>
          }
        >
          <Card size="small" style={{ marginBottom: 12, background: '#fafafa' }}>
            <ScoreRow s={sh.total} />
          </Card>

          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(ev) => onDeptDragEnd(sh, ev)}>
            <SortableContext items={sh.departments.map((d) => deptKey(sh.id, d.department_id))} strategy={verticalListSortingStrategy}>
              {sh.departments.map((block) => {
                const key = deptKey(sh.id, block.department_id)
                const hasLines = block.lines.length > 0
                const masterCount = masterItems.filter((i) => i.department_id === block.department_id).length
                return (
                  <SortableDeptCard
                    key={key} id={key} disabled={!canEdit}
                    collapsed={collapsedDepts.has(key)} onToggle={() => toggleCollapsed(key)}
                    title={
                      <Space wrap>
                        <b>{block.department_name}</b>
                        {hasLines ? <SubtotalTags s={block.subtotal} /> : <Text type="secondary">本期尚未選定項目</Text>}
                      </Space>
                    }
                    extra={(
                      <Space size="small">
                        {hasLines && (
                          <Button size="small" icon={<FileWordOutlined />}
                            onClick={() => downloadFile(
                              kpoPeriodApi.inspectionDocxUrl(detail.id, sh.id, block.department_id),
                              `內部稽核報告-${detail.period}-${sh.company_name}-${block.department_name}.docx`,
                            )}>匯出 Word</Button>
                        )}
                        {canEdit && (
                          <Button size="small" type="primary" ghost icon={<CheckSquareOutlined />}
                            onClick={() => openPick(sh, block)}>選擇項目</Button>
                        )}
                      </Space>
                    )}
                  >
                    {hasLines ? (
                      <>
                        <DndContext sensors={sensors} collisionDetection={closestCenter}
                          onDragEnd={(ev) => onLinesDragEnd(sh, block, ev)}>
                          <SortableContext items={block.lines.map((l) => l.id)} strategy={verticalListSortingStrategy}>
                            <Table rowKey="id" size="small" columns={makeColumns(sh.company_name, block.department_name)}
                              dataSource={block.lines} pagination={false} scroll={{ x: 1240 }}
                              components={{ body: { row: (rp: React.HTMLAttributes<HTMLTableRowElement> & { 'data-row-key': number }) => <SortableRow {...rp} disabled={!canEdit} /> } }}
                              onRow={(r) => ({ onClick: () => openDetail(r, sh.company_name, block.department_name), style: { cursor: 'pointer' } })} />
                          </SortableContext>
                        </DndContext>
                        <DeptScoreboard s={block.subtotal} />
                      </>
                    ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`請按「選擇項目」從 ${block.department_name} 的 ${masterCount} 項中選定本期稽核項目`} />}
                  </SortableDeptCard>
                )
              })}
            </SortableContext>
          </DndContext>
        </Card>
      ))}

      <SheetCreateModal
        open={sheetModalOpen} periodId={periodId} periodLabel={detail.period}
        usedCompanyIds={detail.sheets.map((sh) => sh.company_id)}
        onClose={() => setSheetModalOpen(false)}
        onCreated={(d) => { setDetail(d); setSheetModalOpen(false) }}
      />

      <Modal
        title={deptEdit ? `受稽部門 — ${deptEdit.company_name}` : ''}
        open={!!deptEdit} onCancel={() => setDeptEdit(null)} onOk={saveDeptEdit}
        confirmLoading={deptEditSaving} okText="儲存" destroyOnClose
      >
        <div style={{ marginBottom: 8 }}>
          <Text type="secondary">來源為「現場營運稽核項目」的部門，與公司別無連動；新增的部門排在最後，移除的部門其選定項目會一併刪除。</Text>
        </div>
        <Select
          mode="multiple" style={{ width: '100%' }} value={deptEditIds} onChange={setDeptEditIds}
          optionFilterProp="label"
          options={allDepts.map((d) => ({ value: d.id, label: d.display_name }))}
        />
      </Modal>

      <Modal
        title={pickCtx ? `選擇本期稽核項目 — ${pickCtx.company}｜${pickCtx.block.department_name}` : ''}
        open={!!pickCtx} width={820} onCancel={() => setPickCtx(null)}
        onOk={savePick} confirmLoading={pickSaving} okText="儲存選定" destroyOnClose
      >
        {pickHistory && (
          <div style={{ marginBottom: 8 }}>
            {pickHistory.period_count === 0 ? (
              <Text type="secondary">此部門在{pickCtx?.company}尚無其他期別的稽核紀錄</Text>
            ) : (
              <Space size={[6, 4]} wrap>
                <Tag color="purple">期別 {pickHistory.period_count} 期（{pickHistory.periods.map((p) => p.period).join('、')}）</Tag>
                <Tag color="geekblue">分數 {pickHistory.score_sum}</Tag>
                <Tag color="cyan">平均分數 {pickHistory.score_avg}</Tag>
              </Space>
            )}
          </div>
        )}
        <div style={{ marginBottom: 8 }}>
          <Tag color="blue">已選 {pickSum.count} 項</Tag>
          <Tag color="gold">★ {pickSum.key}</Tag>
          <Tag color="geekblue">滿分 {pickSum.score}</Tag>
          <Text type="secondary">（通常每部門每期 1★＋3 項＝25 分，僅供參考，不強制）</Text>
        </div>
        <Checkbox.Group value={picked} onChange={(v) => setPicked(v as number[])} style={{ width: '100%' }}>
          <Space direction="vertical" style={{ width: '100%' }} size={6}>
            {pickItems.map((i) => (
              <Checkbox key={i.id} value={i.id} style={{ alignItems: 'flex-start' }}>
                <span style={{ whiteSpace: 'pre-wrap' }}>
                  {i.is_key ? <Tag color="gold">★{i.item_no}</Tag> : <Tag>{i.item_no}</Tag>}
                  {i.name}　<Text type="secondary">{i.score} 分</Text>
                  {(pickHistory?.items[String(i.id)] ?? []).map((m) => (
                    <Tag key={m.period_id} style={{ marginLeft: 4 }}
                      color={m.result === 'pass' ? 'green' : m.result === 'fail' ? 'red' : 'default'}>
                      {m.period} {m.result === 'pass' ? '符合' : m.result === 'fail' ? '不符合' : '未查核'}
                    </Tag>
                  ))}
                </span>
              </Checkbox>
            ))}
          </Space>
        </Checkbox.Group>
      </Modal>

      <style>{RICH_TEXT_CSS}</style>
      <Drawer
        open={!!detailLine} onClose={() => { setDetailLine(null); setDetailCtx(null) }} width={640} destroyOnClose
        title={detailLine ? (
          <Space size="small" wrap>
            <Tag color="#1B3A5C">{detailCtx ? `${detailCtx.company}｜${detailCtx.dept}` : ''}</Tag>
            <span style={{ fontWeight: 600 }}>現場營運稽核：{detailLine.is_key ? '★' : ''}{detailLine.item_no ?? detailLine.id}</span>
          </Space>
        ) : ''}
        footer={canEdit && detailLine ? (
          <Space style={{ float: 'right' }}>
            {editMode ? (
              <>
                <Button onClick={() => { setEditMode(false); openDetail(detailLine, detailCtx?.company ?? '', detailCtx?.dept ?? '') }}>取消</Button>
                <Button type="primary" icon={<SaveOutlined />} loading={drawerSaving} onClick={saveDetail}>儲存</Button>
              </>
            ) : (
              <Button type="primary" icon={<EditOutlined />} onClick={() => setEditMode(true)}>編輯（只影響本期）</Button>
            )}
          </Space>
        ) : null}
      >
        {detailLine && (
          <>
            <Descriptions size="small" column={2} bordered>
              <Descriptions.Item label="公司別">{detailCtx?.company ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="受稽部門">{detailCtx?.dept ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="項數">{detailLine.item_no ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="重點項">{detailLine.is_key ? <Tag color="gold">★ 重點項</Tag> : '—'}</Descriptions.Item>
              <Descriptions.Item label="分數">{detailLine.score}</Descriptions.Item>
              <Descriptions.Item label="判定">
                {detailLine.result === 'pass' ? <Tag color="green">符合</Tag>
                  : detailLine.result === 'fail' ? <Tag color="red">不符合</Tag> : <Tag>未查核</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="查核備註" span={2}><RichView html={detailLine.remark} /></Descriptions.Item>
            </Descriptions>

            <Divider orientation="left" plain>明細</Divider>
            {editMode ? (
              <Form form={editForm} layout="vertical" key={detailLine.id}
                initialValues={{ name: detailLine.name, is_key: detailLine.is_key, score: detailLine.score }}>
                <Form.Item name="name" label="品質項目" rules={[{ required: true, message: '請輸入項目內容' }]}>
                  <Input.TextArea autoSize={{ minRows: 3, maxRows: 10 }} />
                </Form.Item>
                <Space size="large">
                  <Form.Item name="is_key" label="★ 重點項" valuePropName="checked"><Switch /></Form.Item>
                  <Form.Item name="score" label="分數" rules={[{ required: true }]}>
                    <InputNumber min={0} max={100} />
                  </Form.Item>
                </Space>
                <div style={{ marginBottom: 8 }}><Text strong>備註（查核方式）</Text></div>
                <RichTextEditor value={method} onChange={setMethod} minHeight={220} placeholder="查核方式、依據文件…" />
                <div style={{ margin: '16px 0 8px' }}><Text strong>查核備註</Text></div>
                <RichTextEditor value={remark} onChange={setRemark} minHeight={220} placeholder="查核結果、缺失說明…" />
              </Form>
            ) : (
              <>
                <div style={{ marginBottom: 4 }}><Text strong>品質項目</Text></div>
                <div style={{ whiteSpace: 'pre-wrap', marginBottom: 16 }}>{detailLine.name}</div>
                <div style={{ marginBottom: 4 }}><Text strong>備註（查核方式）</Text></div>
                <RichView html={detailLine.method} />
                <div style={{ margin: '16px 0 4px' }}><Text strong>查核備註</Text></div>
                <RichView html={detailLine.remark} />
              </>
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}
