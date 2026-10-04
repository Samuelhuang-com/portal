/**
 * 稽核檢查 — 稽核單矩陣編輯（模組主畫面）
 * route: /audit-check/sheets/:id     permissionKey: audit_check_view（編輯需 audit_check_edit）
 *
 * 版面刻意比照 Excel（財#3系統建置稽核）：同一張表格由上而下依序是
 *   稽核子項數 / 達標項數 / 各部門本期稽核分數 / 缺失 / 抽檢項（1 階 + 2 階）
 *   / 上期待補正項目 / 結果 / 稽核完成率
 * 讓長期使用 Excel 的稽核人員不需要重新學版面。
 *
 * ⚠️ 三列統計數字一律由後端即時計算，前端不重算也不可編輯（使用者裁示）。
 * ⚠️ 格子編輯一律走 CellDrawer（CLAUDE.md §7）。
 *
 * 2026-10-01 使用者要求：
 *   1. 表頭與左側檢查項固定（表格自己捲動，scroll.y + fixed left）
 *   2. 部門欄可用滑鼠拖曳調整順序（拖表頭）；左側檢查項可拖曳調整順序（拖 ⠿ 把手）
 *      — 大項之間互換時子項跟著走；子項只能在同一個大項內移動；只影響這一張稽核單
 *   3. 每一格多一個「建議」（CellDrawer 查核評語下方），固定藍字、與判定無關、不計分
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type React from 'react'
import {
  DndContext, PointerSensor, closestCenter, useSensor, useSensors,
  type CollisionDetection, type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext, arrayMove, horizontalListSortingStrategy, useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Button, Card, Checkbox, DatePicker, Empty, Input, InputNumber, Modal, Progress, Radio,
  Select, Space, Spin, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ArrowLeftOutlined, DownloadOutlined, EditOutlined, FileWordOutlined, HolderOutlined, LayoutOutlined, PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

import { itemsApi, refOptionsApi, sheetsApi } from '@/api/auditCheck'
import type {
  AuditItem, Cell, RefOption, ResultType, SheetDepartment, SheetDetail, SheetItem, SheetItemSpec,
} from '@/api/auditCheck'
import { downloadFile } from '@/api/downloadFile'
import { useAuthStore } from '@/stores/authStore'
import CellDrawer from './CellDrawer'
import { SUGGESTION_COLOR } from './suggestionColor'
import { RICH_TEXT_CSS, htmlToPlain, toDisplayHtml } from './richText'

const { Title, Text, Paragraph } = Typography


const COL_ITEM_WIDTH = 280
const COL_DEPT_WIDTH = 210

type RowKind = 'stat' | 'deficiency' | 'major' | 'minor' | 'pending' | 'result' | 'export'

interface MatrixRow {
  key: string
  kind: RowKind
  label: string
  item?: SheetItem
  statKey?: 'sub_count' | 'pass_count' | 'score'
}

// ── 拖曳（2026-10-01）────────────────────────────────────────────────────
// 檢查項列：只有拖 ⠿ 把手才會啟動，避免跟「點格子開 Drawer」衝突
const RowHandleContext = createContext<{
  setActivatorNodeRef?: (el: HTMLElement | null) => void
  listeners?: Record<string, unknown>
  attributes?: Record<string, unknown>
}>({})

function RowDragHandle() {
  const { setActivatorNodeRef, listeners, attributes } = useContext(RowHandleContext)
  if (!listeners) return null
  return (
    <span
      ref={setActivatorNodeRef}
      {...attributes}
      {...listeners}
      title="拖曳調整順序"
      style={{ cursor: 'grab', color: '#8c8c8c', touchAction: 'none', padding: '0 2px' }}
    >
      <HolderOutlined />
    </span>
  )
}

interface BodyRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  'data-row-key'?: string
}

function SortableItemRow(props: BodyRowProps & { rowId: string }) {
  const { rowId, ...rest } = props
  const {
    attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging,
  } = useSortable({ id: rowId })
  const ctx = useMemo(
    () => ({
      setActivatorNodeRef,
      listeners: listeners as Record<string, unknown> | undefined,
      attributes: attributes as unknown as Record<string, unknown>,
    }),
    [setActivatorNodeRef, listeners, attributes],
  )
  const style: React.CSSProperties = {
    ...rest.style,
    transform: CSS.Translate.toString(transform && { ...transform, x: 0 }),
    transition,
    ...(isDragging ? { position: 'relative', zIndex: 9, opacity: 0.85 } : {}),
  }
  return (
    <RowHandleContext.Provider value={ctx}>
      <tr {...rest} ref={setNodeRef} style={style} />
    </RowHandleContext.Provider>
  )
}

function BodyRow(props: BodyRowProps) {
  const key = props['data-row-key']
  if (typeof key === 'string' && key.startsWith('item-')) {
    return <SortableItemRow {...props} rowId={key} />
  }
  return <tr {...props} />
}

interface HeaderCellProps extends React.ThHTMLAttributes<HTMLTableCellElement> {
  'data-col-id'?: string
}

function SortableHeaderCell(props: HeaderCellProps & { colId: string }) {
  const { colId, ...rest } = props
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: colId })
  const style: React.CSSProperties = {
    ...rest.style,
    transform: CSS.Translate.toString(transform && { ...transform, y: 0 }),
    transition,
    cursor: 'grab',
    touchAction: 'none',
    ...(isDragging ? { position: 'relative', zIndex: 9, background: '#e6f4ff' } : {}),
  }
  return <th {...rest} ref={setNodeRef} style={style} {...attributes} {...listeners} />
}

function HeaderCell(props: HeaderCellProps) {
  const colId = props['data-col-id']
  if (colId) return <SortableHeaderCell {...props} colId={colId} />
  return <th {...props} />
}

const TABLE_COMPONENTS = {
  header: { cell: HeaderCell },
  body: { row: BodyRow },
}

/** 部門欄只跟部門欄碰撞、檢查項只跟檢查項碰撞 */
const sameKindCollision: CollisionDetection = (args) => {
  const prefix = String(args.active.id).split('-')[0] + '-'
  return closestCenter({
    ...args,
    droppableContainers: args.droppableContainers.filter((c) => String(c.id).startsWith(prefix)),
  })
}

function rateColor(rate: number | null): string {
  if (rate == null) return '#94a3b8'
  if (rate >= 1) return '#52c41a'
  if (rate >= 0.8) return '#4BA8E8'
  return '#cf1322'
}

export default function AuditSheetEditorPage() {
  const { id } = useParams<{ id: string }>()
  const sheetId = Number(id)
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('audit_check_edit')

  const [detail, setDetail] = useState<SheetDetail | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (!sheetId) return
    setLoading(true)
    try {
      const res = await sheetsApi.get(sheetId)
      setDetail(res.data)
    } catch {
      message.error('載入稽核單失敗')
    } finally {
      setLoading(false)
    }
  }, [sheetId])

  useEffect(() => { load() }, [load])

  // ── 索引 ────────────────────────────────────────────────────────────────
  const cellMap = useMemo(() => {
    const m = new Map<string, Cell>()
    detail?.cells.forEach((c) => m.set(`${c.sheet_item_id}-${c.sheet_department_id}`, c))
    return m
  }, [detail])

  const typeByCode = useMemo(() => {
    const m = new Map<string, ResultType>()
    detail?.result_types.forEach((t) => m.set(t.code, t))
    return m
  }, [detail])

  const scoreByDept = useMemo(() => {
    const m = new Map<number, { sub_count: number; pass_count: number; score: number | null; score_label: string }>()
    detail?.scores.forEach((s) => m.set(s.sheet_department_id, s))
    return m
  }, [detail])

  const reviewByDept = useMemo(() => {
    const m = new Map<number, { pending_text: string | null; pending_result: string; result_text: string | null; result_status: string; source_period: string | null }>()
    detail?.reviews.forEach((r) => m.set(r.sheet_department_id, r))
    return m
  }, [detail])

  const majorNameOf = useCallback((item: SheetItem): string => {
    if (!detail) return ''
    if (item.parent_sheet_item_id == null) return item.name
    const parent = detail.items.find((i) => i.id === item.parent_sheet_item_id)
    return parent?.name ?? ''
  }, [detail])

  // ── 表格列 ──────────────────────────────────────────────────────────────
  const rows: MatrixRow[] = useMemo(() => {
    if (!detail) return []
    const out: MatrixRow[] = [
      { key: 'stat-sub', kind: 'stat', label: '稽核子項數', statKey: 'sub_count' },
      { key: 'stat-pass', kind: 'stat', label: '達標項數', statKey: 'pass_count' },
      { key: 'stat-score', kind: 'stat', label: '各部門本期稽核分數', statKey: 'score' },
      { key: 'deficiency', kind: 'deficiency', label: '缺失' },
    ]
    detail.items.forEach((it) => {
      out.push({
        key: `item-${it.id}`,
        kind: it.level === 1 ? 'major' : 'minor',
        label: `${it.display_no ?? ''} ${it.name}${it.scope_note ?? ''}`.trim(),
        item: it,
      })
    })
    out.push({ key: 'pending', kind: 'pending', label: `${detail.reviews[0]?.source_period ?? '上期'}待補正項目` })
    out.push({ key: 'result', kind: 'result', label: '結果' })
    out.push({ key: 'export', kind: 'export', label: '匯出稽核檢查表' })
    return out
  }, [detail])

  // ── 格子 Drawer ─────────────────────────────────────────────────────────
  const [drawerItemId, setDrawerItemId] = useState<number | null>(null)
  const [drawerDeptIdx, setDrawerDeptIdx] = useState(0)

  const drawerItem = detail?.items.find((i) => i.id === drawerItemId) ?? null
  const drawerDept: SheetDepartment | null = detail?.departments[drawerDeptIdx] ?? null

  const openCell = (item: SheetItem, deptIdx: number) => {
    setDrawerItemId(item.id)
    setDrawerDeptIdx(deptIdx)
  }

  const navigateCell = (delta: number) => {
    if (!detail) return
    const next = drawerDeptIdx + delta
    if (next < 0 || next >= detail.departments.length) {
      message.info(delta > 0 ? '已是最後一欄' : '已是第一欄')
      return
    }
    setDrawerDeptIdx(next)
  }

  // ── 文字編輯 Modal（缺失 / 覆核）─────────────────────────────────────────
  const [textModal, setTextModal] = useState<{
    open: boolean
    kind: RowKind
    deptId: number
    title: string
    value: string
    code: string
  } | null>(null)

  const openTextModal = (kind: RowKind, dept: SheetDepartment) => {
    if (!canEdit || !detail) return
    if (kind === 'deficiency') {
      setTextModal({
        open: true, kind, deptId: dept.id,
        title: `缺失 — ${dept.name}`,
        value: dept.deficiency_override ?? dept.deficiency,
        code: '',
      })
      return
    }

    const rv = reviewByDept.get(dept.id)
    setTextModal({
      open: true, kind, deptId: dept.id,
      title: `${kind === 'pending' ? '待補正項目' : '覆核結果'} — ${dept.name}`,
      value: (kind === 'pending' ? rv?.pending_text : rv?.result_text) ?? '',
      code: (kind === 'pending' ? rv?.pending_result : rv?.result_status) ?? 'ok',
    })
  }

  const saveTextModal = async () => {
    if (!textModal || !detail) return
    try {
      let res
      if (textModal.kind === 'deficiency') {
        res = await sheetsApi.upsertDeficiency(detail.id, textModal.deptId, textModal.value.trim() || null)
      } else if (textModal.kind === 'pending') {
        res = await sheetsApi.upsertReview(detail.id, textModal.deptId, {
          pending_text: textModal.value,
        })
      } else {
        res = await sheetsApi.upsertReview(detail.id, textModal.deptId, {
          result_text: textModal.value, result_status: textModal.code,
        })
      }
      setDetail(res.data)
      setTextModal(null)
      message.success('已儲存')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    }
  }

  // ── 修改本期名稱（2026-09-27 裁示：只影響這一張稽核單，不動主檔與其他月份）──
  const [renameModal, setRenameModal] = useState<{ item: SheetItem; value: string } | null>(null)
  const [renaming, setRenaming] = useState(false)

  const saveRename = async () => {
    if (!renameModal || !detail) return
    const name = renameModal.value.trim()
    if (!name) {
      message.warning('名稱不可空白')
      return
    }
    setRenaming(true)
    try {
      const res = await sheetsApi.renameItem(detail.id, renameModal.item.id, name)
      setDetail(res.data)
      setRenameModal(null)
      message.success('已修改本期名稱')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    } finally {
      setRenaming(false)
    }
  }

  // ── 拖曳調整順序（2026-10-01）───────────────────────────────────────────
  /**
   * 目前版面原封不動轉成 layout API 的 items（含沒有子項的大項、scope_note、本期應查部門）。
   * ⚠️ 後端 apply_layout 是「完全取代」語意，沒帶到的列會連同評語一起被刪掉。
   */
  const currentSpecs = (d: SheetDetail): SheetItemSpec[] =>
    d.items
      .filter((i) => i.level === 2 || !d.items.some((c) => c.parent_sheet_item_id === i.id))
      .map((i) => ({
        item_id: i.item_id,
        scope_note: i.scope_note,
        target_department_ids: i.target_department_ids,
      }))

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))
  const [reordering, setReordering] = useState(false)

  const reorderDepartments = async (activeKey: string, overKey: string) => {
    if (!detail) return
    const keys = detail.departments.map((d) => `dept-${d.id}`)
    const from = keys.indexOf(activeKey)
    const to = keys.indexOf(overKey)
    if (from < 0 || to < 0 || from === to) return
    const prev = detail
    const departments = arrayMove(detail.departments, from, to)
    setDetail({ ...detail, departments })
    setReordering(true)
    try {
      const res = await sheetsApi.updateLayout(detail.id, {
        department_ids: departments.map((d) => d.department_id),
        items: currentSpecs(detail),
      })
      setDetail(res.data)
    } catch (e: any) {
      setDetail(prev)
      message.error(e?.response?.data?.detail ?? '調整部門順序失敗')
    } finally {
      setReordering(false)
    }
  }

  const reorderItems = async (activeId: number, overId: number) => {
    if (!detail) return
    const items = detail.items
    const act = items.find((i) => i.id === activeId)
    const ov = items.find((i) => i.id === overId)
    if (!act || !ov) return
    let majors = items.filter((i) => i.parent_sheet_item_id == null)
    const childMap = new Map<number, SheetItem[]>(
      majors.map((m) => [m.id, items.filter((c) => c.parent_sheet_item_id === m.id)]),
    )

    if (act.parent_sheet_item_id == null) {
      // 大項：落在別的大項（或它的子項）上 → 整組換位置
      const targetMajorId = ov.parent_sheet_item_id ?? ov.id
      const from = majors.findIndex((m) => m.id === act.id)
      const to = majors.findIndex((m) => m.id === targetMajorId)
      if (from < 0 || to < 0 || from === to) return
      majors = arrayMove(majors, from, to)
    } else {
      const pid = act.parent_sheet_item_id
      const siblings = childMap.get(pid) ?? []
      let to: number
      if (ov.id === pid) to = 0
      else if (ov.parent_sheet_item_id === pid) to = siblings.findIndex((s) => s.id === ov.id)
      else {
        message.warning('子項只能在同一個大項內移動')
        return
      }
      const from = siblings.findIndex((s) => s.id === act.id)
      if (from < 0 || to < 0 || from === to) return
      childMap.set(pid, arrayMove(siblings, from, to))
    }

    const flat = majors.flatMap((m) => [m, ...(childMap.get(m.id) ?? [])])
    const seen = new Set(flat.map((i) => i.id))
    items.forEach((i) => { if (!seen.has(i.id)) flat.push(i) })

    const prev = detail
    setDetail({ ...detail, items: flat })
    setReordering(true)
    try {
      const res = await sheetsApi.reorderItems(detail.id, flat.map((i) => i.id))
      setDetail(res.data)
    } catch (e: any) {
      setDetail(prev)
      message.error(e?.response?.data?.detail ?? '調整檢查項順序失敗')
    } finally {
      setReordering(false)
    }
  }

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return
    const a = String(active.id)
    const o = String(over.id)
    if (a.startsWith('dept-') && o.startsWith('dept-')) reorderDepartments(a, o)
    else if (a.startsWith('item-') && o.startsWith('item-')) reorderItems(Number(a.slice(5)), Number(o.slice(5)))
  }

  // ── 新增部門欄（2026-09-21 使用者要求：能直接在稽核單上加部門）──────────
  // 部門仍然只能從 settings/company-departments 主檔挑（CLAUDE.md §9 單一真實
  // 來源），這裡只是省掉「開版面調整 Modal → 在一大包設定裡找部門」那一步。
  const [deptModalOpen, setDeptModalOpen] = useState(false)
  const [deptOptions, setDeptOptions] = useState<RefOption[]>([])
  const [deptPicked, setDeptPicked] = useState<number[]>([])
  const [deptSaving, setDeptSaving] = useState(false)

  const openDeptModal = async () => {
    if (!detail) return
    try {
      setDeptOptions(await refOptionsApi.departments(detail.company_id))
      setDeptPicked([])
      setDeptModalOpen(true)
    } catch {
      message.error('載入部門主檔失敗')
    }
  }

  /**
   * 以「現有部門 ＋ 新勾選的」呼叫 layout API。
   * ⚠️ 檢查項一定要原封不動帶回去（含 scope_note 與本期應查部門），
   *    後端的 apply_layout 是「完全取代」語意，沒帶到的列會被刪掉，
   *    連同該列已填的評語一起消失。
   */
  const addDepartments = async () => {
    if (!detail || deptPicked.length === 0) return
    const specs = currentSpecs(detail)
    setDeptSaving(true)
    try {
      const res = await sheetsApi.updateLayout(detail.id, {
        department_ids: [...detail.departments.map((d) => d.department_id), ...deptPicked],
        items: specs,
      })
      setDetail(res.data)
      setDeptModalOpen(false)
      message.success(`已新增 ${deptPicked.length} 個部門欄`)
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '新增失敗')
    } finally {
      setDeptSaving(false)
    }
  }

  // ── 版面調整 ────────────────────────────────────────────────────────────
  const [layoutOpen, setLayoutOpen] = useState(false)
  const [allItems, setAllItems] = useState<AuditItem[]>([])
  const [depts, setDepts] = useState<RefOption[]>([])
  const [pickedItems, setPickedItems] = useState<number[]>([])
  const [pickedDepts, setPickedDepts] = useState<number[]>([])
  const [layoutSaving, setLayoutSaving] = useState(false)

  const openLayout = async () => {
    if (!detail) return
    try {
      const [i, d] = await Promise.all([itemsApi.list(), refOptionsApi.departments(detail.company_id)])
      setAllItems(i.data)
      setDepts(d)
      setPickedItems(detail.items.filter((x) => x.level === 2).map((x) => x.item_id))
      setPickedDepts(detail.departments.map((x) => x.department_id))
      setLayoutOpen(true)
    } catch {
      message.error('載入主檔失敗')
    }
  }

  const saveLayout = async () => {
    if (!detail) return
    if (pickedItems.length === 0 || pickedDepts.length === 0) {
      message.warning('檢查項與部門至少各選一項')
      return
    }
    const specs: SheetItemSpec[] = pickedItems.map((itemId) => {
      const existing = detail.items.find((x) => x.item_id === itemId)
      return {
        item_id: itemId,
        scope_note: existing?.scope_note ?? null,
        target_department_ids: existing?.target_department_ids ?? [],
      }
    })
    setLayoutSaving(true)
    try {
      const res = await sheetsApi.updateLayout(detail.id, {
        department_ids: pickedDepts,
        items: specs,
      })
      setDetail(res.data)
      setLayoutOpen(false)
      message.success('版面已更新')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '更新失敗')
    } finally {
      setLayoutSaving(false)
    }
  }

  // ── 抬頭欄位 ────────────────────────────────────────────────────────────
  const patchSheet = async (body: Record<string, unknown>) => {
    if (!detail) return
    try {
      const res = await sheetsApi.update(detail.id, body)
      setDetail(res.data)
      message.success('已儲存')
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '儲存失敗')
    }
  }

  const doExport = async () => {
    if (!detail) return
    await downloadFile(
      sheetsApi.exportUrl(detail.id),
      `${detail.title}-${detail.period}-${detail.company_name}.xlsx`,
    )
  }

  // ── 欄位定義 ────────────────────────────────────────────────────────────
  const columns: ColumnsType<MatrixRow> = useMemo(() => {
    if (!detail) return []
    const first: ColumnsType<MatrixRow>[number] = {
      title: '檢查項 / 統計',
      dataIndex: 'label',
      key: 'label',
      fixed: 'left',
      width: COL_ITEM_WIDTH,
      render: (_: unknown, row: MatrixRow) => {
        if (row.kind === 'major' || row.kind === 'minor') {
          const it = row.item!
          const renamed = !!it.master_name && it.master_name !== it.name
          return (
            <Space size={4} style={{ paddingLeft: row.kind === 'minor' ? 16 : 0 }} wrap>
              {canEdit && <RowDragHandle />}
              {row.kind === 'major'
                ? <Text strong style={{ color: '#1B3A5C' }}>{row.label}</Text>
                : <span>{row.label}</span>}
              {renamed && (
                <Tooltip title={`主檔名稱：${it.master_name}`}>
                  <Tag color="orange" style={{ margin: 0 }}>本期名稱</Tag>
                </Tooltip>
              )}
              {canEdit && (
                <Tooltip title="修改本期名稱（只影響這張稽核單）">
                  <Button
                    size="small"
                    type="text"
                    icon={<EditOutlined />}
                    onClick={() => setRenameModal({ item: it, value: it.name })}
                  />
                </Tooltip>
              )}
            </Space>
          )
        }
        return <Text strong style={{ color: row.kind === 'deficiency' ? '#cf1322' : undefined }}>{row.label}</Text>
      },
    }

    const deptCols = detail.departments.map((d, idx) => ({
      title: canEdit
        ? <span title="按住拖曳可調整部門順序"><HolderOutlined style={{ color: '#bfbfbf', marginRight: 4 }} />{d.name}</span>
        : d.name,
      key: `dept-${d.id}`,
      width: COL_DEPT_WIDTH,
      onHeaderCell: () => (canEdit ? { 'data-col-id': `dept-${d.id}` } : {}) as React.HTMLAttributes<HTMLElement>,
      render: (_: unknown, row: MatrixRow) => {
        if (row.kind === 'stat') {
          const sc = scoreByDept.get(d.id)
          if (!sc) return <Text type="secondary">—</Text>
          if (row.statKey === 'score') {
            if (sc.score == null) return <Text type="secondary">本月無</Text>
            const pct = Math.round(sc.score * 100)
            return (
              <Text strong style={{ color: sc.score >= 1 ? '#52c41a' : '#cf1322' }}>
                {sc.score.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')}（{pct}%）
              </Text>
            )
          }
          return <Text strong>{row.statKey === 'sub_count' ? sc.sub_count : sc.pass_count}</Text>
        }

        if (row.kind === 'deficiency') {
          const isOverride = !!d.deficiency_override
          return (
            <div
              onClick={() => openTextModal('deficiency', d)}
              style={{
                whiteSpace: 'pre-wrap', color: '#cf1322', fontSize: 12,
                cursor: canEdit ? 'pointer' : 'default', minHeight: 20,
              }}
            >
              {d.deficiency || <Text type="secondary">—</Text>}
              {isOverride && <Tag color="default" style={{ marginLeft: 4 }}>人工</Tag>}
            </div>
          )
        }

        if (row.kind === 'export') {
          return (
            <div style={{ textAlign: 'center' }}>
              <Button
                size="small"
                icon={<FileWordOutlined />}
                onClick={() => downloadFile(
                  sheetsApi.inspectionDocxUrl(detail.id, d.id),
                  `內部稽核檢查表-${detail.period}-${detail.company_name}-${d.name}.docx`,
                )}
              >
                匯出 Word
              </Button>
            </div>
          )
        }

        if (row.kind === 'pending' || row.kind === 'result') {
          const rv = reviewByDept.get(d.id)
          const text = (row.kind === 'pending' ? rv?.pending_text : rv?.result_text) ?? ''
          // 2026-10-03：待補正是題目、不判定 → 不上判定色；只有「結果」依判定上色
          const t = row.kind === 'result' ? typeByCode.get(rv?.result_status ?? 'ok') : undefined
          return (
            <div
              onClick={() => openTextModal(row.kind, d)}
              style={{
                whiteSpace: 'pre-wrap', fontSize: 12, color: t?.color,
                cursor: canEdit ? 'pointer' : 'default', minHeight: 20,
              }}
            >
              {text || <Text type="secondary">—</Text>}
            </div>
          )
        }

        // major / minor：查核評語
        const item = row.item!
        const c = cellMap.get(`${item.id}-${d.id}`)
        const t = c ? typeByCode.get(c.result_code) : undefined
        const isTarget = item.target_department_ids.includes(d.department_id)
        return (
          <div
            onClick={() => openCell(item, idx)}
            style={{
              fontSize: 12,
              // 2026-10-04：評語顏色由富文字自訂，判定不再改字色（底色／框線仍標示不達標）
              cursor: 'pointer',
              minHeight: 22,
              padding: '2px 4px',
              borderRadius: 4,
              background: t && !t.counts_as_pass ? '#fff5f5' : undefined,
              border: t && !t.counts_as_pass ? '1px solid #ffccc7'
                : (isTarget && !c ? '1px dashed #d9d9d9' : '1px solid transparent'),
            }}
          >
            {htmlToPlain(c?.comment)
              ? <div className="audit-rich" dangerouslySetInnerHTML={{ __html: toDisplayHtml(c?.comment) }} />
              : (!c?.suggestion && <Text type="secondary">{isTarget ? '（本期應查）' : '—'}</Text>)}
            {c?.suggestion && (
              <div style={{ color: SUGGESTION_COLOR, marginTop: htmlToPlain(c.comment) ? 4 : 0, whiteSpace: 'pre-wrap' }}>
                {c.suggestion}
              </div>
            )}
          </div>
        )
      },
    }))

    return [first, ...deptCols]
  }, [detail, cellMap, typeByCode, scoreByDept, reviewByDept, canEdit])

  if (!detail) {
    return <Spin spinning={loading}><Empty description="載入中" /></Spin>
  }

  const activeTypes = detail.result_types.filter((t) => t.is_active)

  return (
    <div>
      {/* ── 抬頭 ──────────────────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center' }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/audit-check')}>返回</Button>
          <div>
            <Title level={5} style={{ margin: 0, color: '#1B3A5C' }}>
              <Tag color="#1B3A5C">{detail.period}</Tag>
              {detail.title}
              <Tag color="blue" style={{ marginLeft: 8 }}>{detail.company_name}</Tag>
            </Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {detail.audited_label || '尚未設定查核日期'}
              {detail.executor_label ? ` ・ ${detail.executor_label}` : ''}
            </Text>
          </div>

          <div style={{ minWidth: 220 }}>
            <Progress
              percent={Math.round((detail.completion_rate ?? 0) * 100)}
              strokeColor={rateColor(detail.completion_rate)}
              size="small"
            />
            <Text type="secondary" style={{ fontSize: 12 }}>稽核完成率 {detail.completion_label}</Text>
          </div>

          <div style={{ marginLeft: 'auto' }}>
            <Space wrap>
              {canEdit && (
                <DatePicker
                  value={detail.audited_on ? dayjs(detail.audited_on) : null}
                  onChange={(v) => patchSheet({ audited_on: v ? v.format('YYYY-MM-DD') : null })}
                  placeholder="查核日期"
                />
              )}
              {canEdit && (
                <Select
                  value={detail.audited_session ?? undefined}
                  onChange={(v) => patchSheet({ audited_session: v ?? null })}
                  placeholder="時段"
                  allowClear
                  style={{ width: 96 }}
                  options={[{ value: '上午', label: '上午' }, { value: '下午', label: '下午' }]}
                />
              )}
              {canEdit && (
                <Select
                  value={detail.status}
                  onChange={(v) => patchSheet({ status: v })}
                  style={{ width: 120 }}
                  options={[
                    { value: 'draft', label: '草稿' },
                    { value: 'submitted', label: '已送出' },
                    { value: 'reviewed', label: '已覆核' },
                  ]}
                />
              )}
              {canEdit && (
                <Tooltip title="完成率「已完成數」的人工調整。本期有項目其實沒做到就填 -1，畫面會顯示成「3*3-1=8　8/9 = 88.9%」（比照 Excel 寫法）">
                  <InputNumber
                    value={detail.completion_adjust}
                    onChange={(v) => patchSheet({ completion_adjust: v ?? 0 })}
                    style={{ width: 120 }}
                    addonBefore="完成數±"
                    step={1}
                  />
                </Tooltip>
              )}
              {canEdit && (
                <Button type="primary" ghost icon={<PlusOutlined />} onClick={openDeptModal}>
                  新增部門欄
                </Button>
              )}
              {canEdit && <Button icon={<LayoutOutlined />} onClick={openLayout}>版面調整</Button>}
              <Button icon={<DownloadOutlined />} onClick={doExport}>匯出 Excel</Button>
              <Button icon={<ReloadOutlined />} onClick={load} loading={loading} />
            </Space>
          </div>
        </div>

        <div style={{ marginTop: 8 }}>
          <Space size={4} wrap>
            <Text type="secondary" style={{ fontSize: 12 }}>判定：</Text>
            {activeTypes.map((t) => (
              <Tag key={t.code} color={t.counts_as_pass ? 'default' : 'error'} style={{ color: t.color }}>
                {t.label}{t.counts_as_pass ? '' : '（不達標）'}
              </Tag>
            ))}
            <Tooltip title="可在「稽核期別」編輯中切換；關閉後覆核不計入各部門分數">
              <Tag color={detail.review_counts_in_score ? 'processing' : 'default'}>
                覆核{detail.review_counts_in_score ? '計入' : '不計入'}分數
              </Tag>
            </Tooltip>
          </Space>
        </div>
      </Card>

      {/* ── 矩陣 ──────────────────────────────────────────────────────── */}
      <Spin spinning={loading || reordering}>
        <DndContext sensors={sensors} collisionDetection={sameKindCollision} onDragEnd={onDragEnd}>
          <SortableContext
            items={detail.departments.map((d) => `dept-${d.id}`)}
            strategy={horizontalListSortingStrategy}
          >
            <SortableContext
              items={detail.items.map((i) => `item-${i.id}`)}
              strategy={verticalListSortingStrategy}
            >
              <Table<MatrixRow>
                size="small"
                bordered
                rowKey="key"
                columns={columns}
                dataSource={rows}
                pagination={false}
                components={TABLE_COMPONENTS}
                scroll={{
                  x: COL_ITEM_WIDTH + detail.departments.length * COL_DEPT_WIDTH,
                  y: 'calc(100vh - 300px)',
                }}
                rowClassName={(row) =>
                  row.kind === 'major' ? 'audit-row-major'
                    : row.kind === 'stat' ? 'audit-row-stat'
                      : row.kind === 'deficiency' ? 'audit-row-deficiency'
                        : row.kind === 'pending' ? 'audit-row-pending' : ''
                }
              />
            </SortableContext>
          </SortableContext>
        </DndContext>
      </Spin>

      <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8 }}>
        點任一格即可填寫評語與判定。評語留空 ＝ 該部門本期不查此項，不計入分數分母。
        三列統計數字由系統依評語與判定自動計算，不可手改。
        {canEdit && '按住部門表頭左右拖曳可調整部門順序；拖檢查項左側 ⠿ 可調整項目順序（子項限同一大項內）。'}
      </Paragraph>

      {/* ── 備註 ──────────────────────────────────────────────────────── */}
      <Card size="small" title="備註" style={{ marginTop: 12 }}>
        <Input.TextArea
          defaultValue={detail.remark ?? ''}
          rows={3}
          disabled={!canEdit}
          placeholder="表尾自由備註（如合約用印進度）"
          onBlur={(e) => {
            if (e.target.value !== (detail.remark ?? '')) patchSheet({ remark: e.target.value })
          }}
        />
      </Card>

      {/* ── Drawer / Modal ───────────────────────────────────────────── */}
      <Modal
        open={renameModal != null}
        title="修改本期名稱"
        onOk={saveRename}
        onCancel={() => setRenameModal(null)}
        okText="儲存"
        cancelText="取消"
        confirmLoading={renaming}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text type="secondary">
            只影響這張稽核單（{detail.period}・{detail.company_name}），不會改到檢查項主檔，
            也不會改到其他月份或另一家公司。
          </Text>
          <Input
            value={renameModal?.value ?? ''}
            maxLength={200}
            onChange={(e) => setRenameModal((m) => (m ? { ...m, value: e.target.value } : m))}
            onPressEnter={saveRename}
          />
          {renameModal?.item.master_name && renameModal.item.master_name !== renameModal.value && (
            <Button
              size="small"
              type="link"
              style={{ padding: 0 }}
              onClick={() => setRenameModal((m) => (m ? { ...m, value: m.item.master_name ?? m.value } : m))}
            >
              帶入主檔名稱：{renameModal.item.master_name}
            </Button>
          )}
        </Space>
      </Modal>

      <CellDrawer
        open={drawerItem != null && drawerDept != null}
        sheetId={detail.id}
        period={detail.period}
        companyName={detail.company_name}
        item={drawerItem}
        majorName={drawerItem ? majorNameOf(drawerItem) : ''}
        department={drawerDept}
        cell={drawerItem && drawerDept ? cellMap.get(`${drawerItem.id}-${drawerDept.id}`) : undefined}
        resultTypes={detail.result_types}
        readOnly={!canEdit}
        onClose={() => setDrawerItemId(null)}
        onSaved={(d) => setDetail(d)}
        onNavigate={navigateCell}
      />

      <Modal
        open={!!textModal?.open}
        title={textModal?.title}
        onOk={saveTextModal}
        onCancel={() => setTextModal(null)}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
      >
        <Input.TextArea
          value={textModal?.value ?? ''}
          rows={6}
          onChange={(e) => setTextModal((s) => (s ? { ...s, value: e.target.value } : s))}
        />
        {textModal?.kind === 'deficiency' ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            留空 ＝ 還原成系統自動彙整（依判定類型的「列入缺失彙整」設定）
          </Text>
        ) : textModal?.kind === 'pending' ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            待補正項目是覆核的題目，不需判定；分數只看「結果」（結果未填 ＝ 尚未覆核，不計入分數）
          </Text>
        ) : (
          <div style={{ marginTop: 12 }}>
            <Radio.Group
              value={textModal?.code}
              onChange={(e) => setTextModal((s) => (s ? { ...s, code: e.target.value } : s))}
              optionType="button"
              buttonStyle="solid"
            >
              {activeTypes.map((t) => (
                <Radio.Button key={t.code} value={t.code}>{t.label}</Radio.Button>
              ))}
            </Radio.Group>
          </div>
        )}
      </Modal>

      <Modal
        open={deptModalOpen}
        title="新增部門欄"
        onOk={addDepartments}
        confirmLoading={deptSaving}
        onCancel={() => setDeptModalOpen(false)}
        okText="新增"
        cancelText="取消"
        okButtonProps={{ disabled: deptPicked.length === 0 }}
        destroyOnClose
      >
        {(() => {
          const used = new Set(detail.departments.map((d) => d.department_id))
          const candidates = deptOptions.filter((d) => !used.has(d.id))
          if (candidates.length === 0) {
            return (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <div>
                    <div>「{detail.company_name}」底下的部門都已經在這張稽核單上了</div>
                    <Button type="link" onClick={() => navigate('/settings/company-departments')}>
                      前往「系統設定 → 公司/部門管理」新增部門
                    </Button>
                  </div>
                }
              />
            )
          }
          return (
            <div style={{ marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                只列出「{detail.company_name}」底下、還沒加進這張稽核單的部門
              </Text>
              <Select
                mode="multiple"
                value={deptPicked}
                onChange={setDeptPicked}
                style={{ width: '100%', marginTop: 8 }}
                placeholder="可一次選多個"
                options={candidates.map((d) => ({ value: d.id, label: d.name }))}
              />
              <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 10, marginBottom: 0 }}>
                新增的欄位會排在最後面，已填的評語不受影響。要調整順序或移除欄位請用「版面調整」。
                <br />
                找不到要的部門？部門主檔在「系統設定 → 公司/部門管理」，
                本模組不另建部門主檔。
              </Paragraph>
            </div>
          )
        })()}
      </Modal>

      <Modal
        open={layoutOpen}
        title="版面調整 — 本期抽檢項目與部門欄"
        onOk={saveLayout}
        confirmLoading={layoutSaving}
        onCancel={() => setLayoutOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={760}
        destroyOnClose
      >
        <div style={{ marginBottom: 12 }}>
          <Text strong>部門欄</Text>
          <Select
            mode="multiple"
            value={pickedDepts}
            onChange={setPickedDepts}
            style={{ width: '100%', marginTop: 6 }}
            options={depts.map((d) => ({ value: d.id, label: d.name }))}
          />
        </div>
        <Text strong>抽檢項目（已選 {pickedItems.length} 項）</Text>
        <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 6, padding: 12, marginTop: 6 }}>
          {allItems.filter((m) => m.is_active).map((major) => (
            <div key={major.id} style={{ marginBottom: 12 }}>
              <Text strong style={{ color: '#1B3A5C' }}>{major.name}</Text>
              <div style={{ paddingLeft: 16, marginTop: 4 }}>
                <Checkbox.Group
                  value={pickedItems}
                  onChange={(vals) => {
                    const others = pickedItems.filter(
                      (pid) => !(major.children ?? []).some((c) => c.id === pid),
                    )
                    setPickedItems([...others, ...(vals as number[])])
                  }}
                  options={(major.children ?? []).filter((c) => c.is_active).map((c) => ({ value: c.id, label: c.name }))}
                />
              </div>
            </div>
          ))}
        </div>
        {(() => {
          // 本張已有、但主檔已刪除／停用的子項：照舊保留，列在這裡讓人看得到也能自行取消
          const visible = new Set(
            allItems.filter((m) => m.is_active)
              .flatMap((m) => (m.children ?? []).filter((c) => c.is_active).map((c) => c.id)),
          )
          const hidden = detail
            ? detail.items.filter((x) => x.level === 2 && !visible.has(x.item_id))
            : []
          if (hidden.length === 0) return null
          return (
            <div style={{ border: '1px dashed #d9d9d9', borderRadius: 6, padding: 12, marginTop: 8 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                以下項目已從主檔刪除或停用，本張稽核單照舊保留；取消勾選才會從本張移除
              </Text>
              <div style={{ marginTop: 4 }}>
                <Checkbox.Group
                  value={pickedItems.filter((pid) => hidden.some((h) => h.item_id === pid))}
                  onChange={(vals) => {
                    const hiddenIds = hidden.map((h) => h.item_id)
                    const others = pickedItems.filter((pid) => !hiddenIds.includes(pid))
                    setPickedItems([...others, ...(vals as number[])])
                  }}
                  options={hidden.map((h) => ({ value: h.item_id, label: h.name }))}
                />
              </div>
            </div>
          )
        })()}
        <Tooltip title="移除的列或欄，其已填寫的評語會一併刪除">
          <Text type="warning" style={{ fontSize: 12 }}>⚠️ 取消勾選會連同該列／該欄已填的評語一起刪除</Text>
        </Tooltip>
      </Modal>

      <style>{`
        .audit-row-major > td { background: #f6f9fc !important; }
        .audit-row-stat > td { background: #fafafa !important; }
        .audit-row-deficiency > td { background: #fff5f5 !important; }
        .audit-row-pending > td { background: #f6ffed !important; }
        ${RICH_TEXT_CSS}
      `}</style>
    </div>
  )
}
