/**
 * 選單管理頁面
 * 功能：
 *  - 一階群組與二階頁面均可拖拉排序
 *  - 雙擊或點擊鉛筆圖示 inline 編輯顯示名稱
 *  - 眼睛圖示切換顯示/隱藏（隱藏後側邊欄完全不顯示，隱藏父層時子層一併隱藏）
 *  - 下拉選單跨層移動（子項目升一階 / 移到不同群組；空的一階項目可降為子層）
 *  - 新增自訂一階選單或二階子選單（menu_key 自動產生）
 *  - 儲存後自動記錄歷史，最多保留最近 5 筆
 */
import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Card, Button, Input, Typography, Space, Tag, Tooltip, Drawer,
  Timeline, message, Spin, Divider, Badge, Alert, Modal, Dropdown,
  type InputRef, type MenuProps,
} from 'antd'
import {
  MenuOutlined, EditOutlined, CheckOutlined, CloseOutlined,
  HistoryOutlined, SaveOutlined, ReloadOutlined, InfoCircleOutlined,
  CaretRightOutlined, EyeOutlined, EyeInvisibleOutlined, PlusOutlined,
  ArrowsAltOutlined, DeleteOutlined,
} from '@ant-design/icons'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import {
  fetchMenuConfig,
  saveMenuConfig,
  fetchMenuConfigHistory,
  MenuConfigItem,
  MenuConfigHistoryItem,
} from '@/api/menuConfig'
import { menuItems, computeReparentedL2 } from '@/components/Layout/MainLayout'

const { Text, Title } = Typography

// ── 預設結構：直接從 MainLayout.menuItems 派生，icon（JSX）去除只保留 key + label ─
// 這樣 sidebar 改版時 MenuConfig 自動同步，不需要手動維護第二份清單
const DEFAULT_MENU_STRUCTURE = menuItems.map((item) => ({
  key: item.key as string,
  label: item.label as string,
  children: (item as any).children?.map((child: any) => ({
    key: child.key as string,
    label: child.label as string,
  })) as Array<{ key: string; label: string }> | undefined,
}))

// ── 工作用型別 ─────────────────────────────────────────────────────────────────
interface WorkItem {
  menu_key: string
  parent_key: string | null
  defaultLabel: string
  customLabel: string   // '' = 使用預設
  sort_order: number
  is_visible: boolean
  children: WorkItem[]
}

// ── 樹狀輔助：從任何層移除指定 key ───────────────────────────────────────────
function removeFromTree(items: WorkItem[], key: string): WorkItem[] {
  return items
    .filter((p) => p.menu_key !== key)
    .map((p) => ({
      ...p,
      children: p.children
        .filter((c) => c.menu_key !== key)
        .map((c) => ({
          ...c,
          children: c.children.filter((g) => g.menu_key !== key),
        })),
    }))
}

// ── 樹狀輔助：在指定 parentKey 下插入 item ───────────────────────────────────
function insertUnderParent(items: WorkItem[], parentKey: string, item: WorkItem): WorkItem[] {
  return items.map((p) => {
    if (p.menu_key === parentKey) {
      const lastOrder = p.children.length > 0
        ? Math.max(...p.children.map((c) => c.sort_order)) + 10 : 0
      return { ...p, children: [...p.children, { ...item, parent_key: parentKey, sort_order: lastOrder }] }
    }
    return {
      ...p,
      children: p.children.map((c) => {
        if (c.menu_key === parentKey) {
          const lastOrder = c.children.length > 0
            ? Math.max(...c.children.map((g) => g.sort_order)) + 10 : 0
          return { ...c, children: [...c.children, { ...item, parent_key: parentKey, sort_order: lastOrder }] }
        }
        return c
      }),
    }
  })
}

// ── 從 API 資料 + 預設結構 merge 出工作清單（支援三層）───────────────────────
function buildWorkItems(
  structure: typeof DEFAULT_MENU_STRUCTURE,
  configs: MenuConfigItem[],
): WorkItem[] {
  const configMap = new Map(configs.map((c) => [c.menu_key, c]))
  const structureKeys = new Set<string>()

  // ① 找出「被 DB 換了父層」的 base L2（與 MainLayout.applyMenuConfig 共用同一份邏輯）
  const reparentedMap = computeReparentedL2(
    structure.map((p) => ({ key: p.key, children: p.children?.map((c) => ({ key: c.key })) })),
    configs
  )
  // 轉成帶 origLabel 的完整格式，供後續插入時使用
  const reparentedL2 = new Map<string, { newParentKey: string; origLabel: string }>()
  structure.forEach((parent) => {
    (parent.children ?? []).forEach((child) => {
      const newParentKey = reparentedMap.get(child.key)
      if (newParentKey) {
        reparentedL2.set(child.key, { newParentKey, origLabel: child.label })
      }
    })
  })

  // ② 建立 base 樹（L1 + L2），re-parented 項目從原位置排除，但 key 仍加入 structureKeys
  const result: WorkItem[] = structure.map((parent, pi) => {
    structureKeys.add(parent.key)
    const pCfg = configMap.get(parent.key)
    const children = (parent.children ?? [])
      .filter((child) => !reparentedL2.has(child.key))  // 已換父層的從這裡移除
      .map((child, ci) => {
        structureKeys.add(child.key)
        const cCfg = configMap.get(child.key)
        return {
          menu_key: child.key,
          parent_key: parent.key,
          defaultLabel: child.label,
          customLabel: cCfg?.custom_label ?? '',
          sort_order: cCfg?.sort_order ?? ci * 10,
          is_visible: cCfg?.is_visible ?? true,
          children: [] as WorkItem[],
        }
      })
    // re-parented 的 key 也要加入 structureKeys（防止 extra 迴圈重複插入）
    ;(parent.children ?? []).forEach((child) => structureKeys.add(child.key))
    children.sort((a, b) => a.sort_order - b.sort_order)
    return {
      menu_key: parent.key,
      parent_key: null,
      defaultLabel: parent.label,
      customLabel: pCfg?.custom_label ?? '',
      sort_order: pCfg?.sort_order ?? pi * 10,
      is_visible: pCfg?.is_visible ?? true,
      children,
    }
  }).sort((a, b) => a.sort_order - b.sort_order)

  // ③ 建立 itemMap（用來掛 L3 及 re-parented 項目）
  const itemMap = new Map<string, WorkItem>()
  result.forEach((p) => {
    itemMap.set(p.menu_key, p)
    p.children.forEach((c) => itemMap.set(c.menu_key, c))
  })

  // ④ custom_ 項目：從 DB 插入（最多 3 輪以處理深層依賴）
  const extra = configs.filter((c) => !structureKeys.has(c.menu_key) && c.menu_key.startsWith('custom_'))
  for (let round = 0; round < 3; round++) {
    extra.forEach((cfg) => {
      if (itemMap.has(cfg.menu_key)) return
      const parentItem = cfg.parent_key ? itemMap.get(cfg.parent_key) : null
      if (cfg.parent_key && !parentItem) return
      const newItem: WorkItem = {
        menu_key: cfg.menu_key,
        parent_key: cfg.parent_key ?? null,
        defaultLabel: cfg.custom_label ?? cfg.menu_key,
        customLabel: cfg.custom_label ?? '',
        sort_order: cfg.sort_order,
        is_visible: cfg.is_visible,
        children: [],
      }
      if (!parentItem) {
        result.push(newItem)
      } else {
        parentItem.children.push(newItem)
        parentItem.children.sort((a, b) => a.sort_order - b.sort_order)
      }
      itemMap.set(cfg.menu_key, newItem)
    })
  }

  // ⑤ 將 re-parented 的 base L2 插入新父層
  //    此時 itemMap 已包含 custom_ L1，所以 newParentKey 是 custom_ 也能找到
  reparentedL2.forEach(({ newParentKey, origLabel }, menuKey) => {
    const newParent = itemMap.get(newParentKey)
    if (!newParent) return  // 新父層不存在（已被隱藏或刪除），略過
    const cfg = configMap.get(menuKey)
    const newItem: WorkItem = {
      menu_key: menuKey,
      parent_key: newParentKey,
      defaultLabel: origLabel,
      customLabel: cfg?.custom_label ?? '',
      sort_order: cfg?.sort_order ?? 9999,
      is_visible: cfg?.is_visible ?? true,
      children: [],
    }
    newParent.children.push(newItem)
    newParent.children.sort((a, b) => a.sort_order - b.sort_order)
    itemMap.set(menuKey, newItem)
  })

  return result.sort((a, b) => a.sort_order - b.sort_order)
}

// ── 把工作清單轉成 API 所需的 MenuConfigItem[]（遞迴、去重） ─────────────────
function flattenWorkItems(items: WorkItem[]): MenuConfigItem[] {
  const result: MenuConfigItem[] = []
  const seen = new Set<string>()

  const visit = (item: WorkItem, parentKey: string | null, order: number) => {
    if (seen.has(item.menu_key)) return
    seen.add(item.menu_key)
    result.push({
      menu_key: item.menu_key,
      parent_key: parentKey,
      custom_label: item.customLabel.trim() || null,
      sort_order: order,
      is_visible: item.is_visible,
    })
    item.children.forEach((child, ci) => visit(child, item.menu_key, ci * 10))
  }

  items.forEach((parent, pi) => visit(parent, null, pi * 10))
  return result
}

// ── Diff 摘要顯示 ─────────────────────────────────────────────────────────────
function parseDiff(diffJson: string): string {
  try {
    const diff: Array<{
      key: string
      action?: string
      label?: { from: string | null; to: string | null }
      order?: { from: number; to: number }
    }> = JSON.parse(diffJson)
    if (!diff.length) return '無變更'
    return diff
      .map((d) => {
        const parts: string[] = []
        if (d.label) parts.push(`名稱：「${d.label.from ?? '預設'}」→「${d.label.to ?? '預設'}」`)
        if (d.order) parts.push(`順序：${d.order.from} → ${d.order.to}`)
        if (d.action === 'added') parts.push('新增')
        return `${d.key}（${parts.join('；')}）`
      })
      .join('、')
  } catch {
    return diffJson
  }
}

// ── 單筆可拖拉列 ─────────────────────────────────────────────────────────────
interface SortableRowProps {
  item: WorkItem
  level: 1 | 2 | 3
  parentKey: string | null        // 直接父層 key（L1=null, L2=L1key, L3=L2key）
  grandparentKey: string | null   // 祖父層 key（L3 才有值）
  allTopLevel: WorkItem[]         // 全部 L1 項目（含其 children）
  onLabelChange: (key: string, value: string) => void
  onVisibleChange: (key: string, visible: boolean) => void
  onMoveItem: (key: string, newParentKey: string | null) => void
  onDeleteItem: (key: string) => void
}

function SortableRow({
  item,
  level,
  parentKey,
  grandparentKey,
  allTopLevel,
  onLabelChange,
  onVisibleChange,
  onMoveItem,
  onDeleteItem,
}: SortableRowProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.menu_key })

  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(item.customLabel)
  const inputRef = useRef<InputRef>(null)

  const paddingLeft = level === 1 ? 8 : level === 2 ? 24 : 48

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : item.is_visible ? 1 : 0.45,
  }

  const displayLabel = item.customLabel || item.defaultLabel
  const isModified = !!item.customLabel && item.customLabel !== item.defaultLabel

  const startEdit = () => {
    setDraft(item.customLabel || item.defaultLabel)
    setEditing(true)
    // InputRef.select() → 選取全部文字；需等 Input 渲染完才能呼叫
    setTimeout(() => inputRef.current?.select(), 50)
  }

  const confirmEdit = () => {
    const val = draft.trim()
    if (!val) { setEditing(false); return }  // 空值直接取消
    // custom_ 前綴項目沒有「系統預設」，永遠存入輸入值
    // 內建項目若輸入值與預設相同，清除 customLabel 讓系統 fallback 至預設
    const isCustom = item.menu_key.startsWith('custom_')
    onLabelChange(item.menu_key, (!isCustom && val === item.defaultLabel) ? '' : val)
    setEditing(false)
  }

  const cancelEdit = () => {
    setDraft(item.customLabel)
    setEditing(false)
  }

  // ── 移動選項 ──────────────────────────────────────────────────────────────
  // 全部 L2 items（從 allTopLevel 展開）
  const allL2 = allTopLevel.flatMap((p) => p.children)

  let moveOptions: { value: string; label: string }[] = []

  if (level === 1) {
    // 一階可移到任何其他一階下成為二階（帶子項目一起搬，子項目升格成三階）
    moveOptions = allTopLevel
      .filter((p) => p.menu_key !== item.menu_key)
      .map((p) => ({ value: p.menu_key, label: `⬇ 移到「${p.customLabel || p.defaultLabel}」下（二階）` }))
  } else if (level === 2) {
    moveOptions = [
      { value: '__top__', label: '⬆ 升為一階選單' },
      ...allTopLevel
        .filter((p) => p.menu_key !== parentKey)
        .map((p) => ({ value: p.menu_key, label: `→ 移到「${p.customLabel || p.defaultLabel}」下（二階）` })),
    ]
    // 無子項目時也可降為三階
    if (item.children.length === 0) {
      const otherL2 = allL2.filter((c) => c.menu_key !== item.menu_key)
      moveOptions.push(
        ...otherL2.map((c) => {
          const parentLabel = allTopLevel.find((p) => p.menu_key === c.parent_key)?.customLabel
            || allTopLevel.find((p) => p.menu_key === c.parent_key)?.defaultLabel || ''
          return {
            value: `__l3__${c.menu_key}`,
            label: `⬇ 移到「${parentLabel} > ${c.customLabel || c.defaultLabel}」下（三階）`,
          }
        })
      )
    }
  } else {
    // level === 3
    moveOptions = [
      { value: `__promote2__${grandparentKey}`, label: '⬆ 升為二階選單（回上層）' },
      { value: '__top__', label: '⬆⬆ 升為一階選單' },
      ...allL2
        .filter((c) => c.menu_key !== parentKey)
        .map((c) => {
          const pLabel = allTopLevel.find((p) => p.menu_key === c.parent_key)?.customLabel
            || allTopLevel.find((p) => p.menu_key === c.parent_key)?.defaultLabel || ''
          return { value: c.menu_key, label: `→ 移到「${pLabel} > ${c.customLabel || c.defaultLabel}」下（三階）` }
        }),
    ]
  }

  const handleMove = ({ key: val }: { key: string }) => {
    if (val === '__top__') {
      onMoveItem(item.menu_key, null)
    } else if (val.startsWith('__promote2__')) {
      onMoveItem(item.menu_key, val.replace('__promote2__', ''))
    } else if (val.startsWith('__l3__')) {
      onMoveItem(item.menu_key, val.replace('__l3__', ''))
    } else {
      onMoveItem(item.menu_key, val)
    }
  }

  const moveMenuItems: MenuProps['items'] = moveOptions.map((opt) => ({
    key: opt.value,
    label: opt.label,
  }))

  return (
    <div
      ref={setNodeRef}
      style={{
        ...style,
        display: 'flex',
        alignItems: 'center',
        padding: `${level === 1 ? 8 : 6}px 8px ${level === 1 ? 8 : 6}px ${paddingLeft}px`,
        background: isDragging
          ? '#e6f4ff'
          : !item.is_visible
            ? '#f5f5f5'
            : level === 1 ? '#fff' : level === 2 ? '#fafafa' : '#f5f8ff',
        border: '1px solid',
        borderColor: isDragging ? '#1677ff' : !item.is_visible ? '#d9d9d9' : '#f0f0f0',
        borderRadius: 6,
        marginBottom: 4,
        gap: 8,
        cursor: isDragging ? 'grabbing' : 'default',
      }}
    >
      {/* 拖拉把手 */}
      <span
        {...attributes}
        {...listeners}
        style={{ cursor: 'grab', color: '#bbb', fontSize: 16, lineHeight: 1, flexShrink: 0 }}
        title="拖拉調整順序"
      >
        <MenuOutlined />
      </span>

      {level >= 2 && (
        <CaretRightOutlined style={{ color: level === 3 ? '#aaa' : '#ccc', fontSize: level === 3 ? 8 : 10, flexShrink: 0 }} />
      )}

      {/* 名稱區 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        {editing ? (
          <Input
            ref={inputRef}
            size="small"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onPressEnter={confirmEdit}
            style={{ width: '100%', maxWidth: 280 }}
            autoFocus
          />
        ) : (
          <Space size={4} onDoubleClick={startEdit} style={{ cursor: 'text' }}>
            <Text
              strong={level === 1}
              delete={!item.is_visible}
              type={item.is_visible ? undefined : 'secondary'}
              style={{ fontSize: level === 1 ? 14 : 13 }}
            >
              {displayLabel}
            </Text>
            {isModified && (
              <Tag color="blue" style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px' }}>
                已改名
              </Tag>
            )}
            {!item.is_visible && (
              <Tag color="default" style={{ fontSize: 11, lineHeight: '18px', padding: '0 4px' }}>
                已隱藏
              </Tag>
            )}
          </Space>
        )}
      </div>

      {/* 階層 + 原始 key */}
      <Space size={4} style={{ flexShrink: 0 }}>
        <Tag
          style={{
            fontSize: 10, lineHeight: '16px', padding: '0 5px', margin: 0,
            background: level === 1 ? '#e6f4ff' : level === 2 ? '#f6ffed' : '#fff7e6',
            borderColor: level === 1 ? '#91caff' : level === 2 ? '#b7eb8f' : '#ffd591',
            color: level === 1 ? '#1677ff' : level === 2 ? '#389e0d' : '#d46b08',
          }}
        >
          {level === 1 ? '一階' : level === 2 ? '二階' : '三階'}
        </Tag>
        <Text type="secondary" style={{ fontSize: 11 }}>
          {item.menu_key}
        </Text>
      </Space>

      {/* 操作按鈕 */}
      {editing ? (
        <Space size={2}>
          <Button size="small" type="text" icon={<CheckOutlined style={{ color: '#52c41a' }} />} onClick={confirmEdit} />
          <Button size="small" type="text" icon={<CloseOutlined style={{ color: '#ff4d4f' }} />} onClick={cancelEdit} />
        </Space>
      ) : (
        // onPointerDown stopPropagation：防止 dnd-kit PointerSensor 在操作按鈕區啟動拖曳，
        // 避免移到 Dropdown overlay 時觸發 global pointerup 而吞掉選單點擊
        <Space size={2} onPointerDown={(e) => e.stopPropagation()}>
          {/* 改名 */}
          <Tooltip title="重新命名（雙擊也可）">
            <Button
              size="small" type="text"
              icon={<EditOutlined style={{ color: '#666' }} />}
              onClick={startEdit}
            />
          </Tooltip>

          {/* 顯示/隱藏 */}
          <Tooltip title={item.is_visible ? '隱藏此項目' : '顯示此項目'}>
            <Button
              size="small" type="text"
              icon={
                item.is_visible
                  ? <EyeOutlined style={{ color: '#666' }} />
                  : <EyeInvisibleOutlined style={{ color: '#bbb' }} />
              }
              onClick={() => onVisibleChange(item.menu_key, !item.is_visible)}
            />
          </Tooltip>

          {/* 跨層移動（有選項才顯示） */}
          {moveOptions.length > 0 && (
            <Dropdown
              menu={{ items: moveMenuItems, onClick: handleMove }}
              trigger={['click']}
              placement="bottomRight"
            >
              <Tooltip title="移動到...">
                <Button
                  size="small"
                  type="text"
                  icon={<ArrowsAltOutlined style={{ color: '#666' }} />}
                />
              </Tooltip>
            </Dropdown>
          )}

          {/* 刪除（只限自訂項目） */}
          {item.menu_key.startsWith('custom_') && (
            <Tooltip title="刪除此自訂項目">
              <Button
                size="small"
                type="text"
                icon={<DeleteOutlined style={{ color: '#ff4d4f' }} />}
                onClick={(e) => {
                  e.stopPropagation()
                  const hasBaseChildren = item.children.some(
                    (c) => !c.menu_key.startsWith('custom_'),
                  )
                  Modal.confirm({
                    title: hasBaseChildren
                      ? '刪除後，內含的系統模組項目將退回上層'
                      : '確定刪除此自訂選單項目？',
                    content: hasBaseChildren ? '自訂子項目也將一併刪除。' : undefined,
                    okText: '刪除',
                    okType: 'danger',
                    cancelText: '取消',
                    onOk: () => onDeleteItem(item.menu_key),
                  })
                }}
              />
            </Tooltip>
          )}
        </Space>
      )}
    </div>
  )
}

// ── 主頁面 ────────────────────────────────────────────────────────────────────
export default function MenuConfigPage() {
  const [items, setItems]               = useState<WorkItem[]>([])
  const [loading, setLoading]           = useState(true)
  const [saving, setSaving]             = useState(false)
  const [dirty, setDirty]               = useState(false)
  const [historyOpen, setHistoryOpen]   = useState(false)
  const [history, setHistory]           = useState<MenuConfigHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [activeId, setActiveId]         = useState<string | null>(null)

  // 新增選單 Modal
  const [addModal, setAddModal]         = useState<{ open: boolean; parentKey: string | null }>({ open: false, parentKey: null })
  const [addLabel, setAddLabel]         = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  )

  // ── 載入 ──────────────────────────────────────────────────────────────────
  const load = useCallback(async () => {
    setLoading(true)
    try {
      const configs = await fetchMenuConfig()
      setItems(buildWorkItems(DEFAULT_MENU_STRUCTURE, configs))
      setDirty(false)
    } catch {
      message.error('載入選單設定失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // ── 改名（支援三層）──────────────────────────────────────────────────────
  const handleLabelChange = useCallback((key: string, value: string) => {
    setItems((prev) => prev.map((parent) => {
      if (parent.menu_key === key) return { ...parent, customLabel: value }
      return {
        ...parent,
        children: parent.children.map((child) => {
          if (child.menu_key === key) return { ...child, customLabel: value }
          return {
            ...child,
            children: child.children.map((g) =>
              g.menu_key === key ? { ...g, customLabel: value } : g
            ),
          }
        }),
      }
    }))
    setDirty(true)
  }, [])

  // ── 顯示/隱藏（隱藏時三層一起隱藏）──────────────────────────────────────
  const handleVisibleChange = useCallback((key: string, visible: boolean) => {
    setItems((prev) => prev.map((parent) => {
      if (parent.menu_key === key) {
        return {
          ...parent,
          is_visible: visible,
          children: visible
            ? parent.children
            : parent.children.map((c) => ({
                ...c, is_visible: false,
                children: c.children.map((g) => ({ ...g, is_visible: false })),
              })),
        }
      }
      return {
        ...parent,
        children: parent.children.map((child) => {
          if (child.menu_key === key) {
            return {
              ...child,
              is_visible: visible,
              children: visible
                ? child.children
                : child.children.map((g) => ({ ...g, is_visible: false })),
            }
          }
          return {
            ...child,
            children: child.children.map((g) =>
              g.menu_key === key ? { ...g, is_visible: visible } : g
            ),
          }
        }),
      }
    }))
    setDirty(true)
  }, [])

  // ── 跨層移動（支援三層）──────────────────────────────────────────────────
  const handleMoveItem = useCallback((key: string, newParentKey: string | null) => {
    setItems((prev) => {
      // 先找到要移動的項目
      const movingItem =
        prev.find((p) => p.menu_key === key) ||
        prev.flatMap((p) => p.children).find((c) => c.menu_key === key) ||
        prev.flatMap((p) => p.children.flatMap((c) => c.children)).find((g) => g.menu_key === key)
      if (!movingItem) return prev

      // 從樹中移除
      let next = removeFromTree(prev, key)

      if (newParentKey === null) {
        // 升為頂層
        next = [...next, { ...movingItem, parent_key: null }]
      } else {
        // 插入至目標父層（L1 或 L2 均可）
        next = insertUnderParent(next, newParentKey, movingItem)
      }
      return next
    })
    setDirty(true)
  }, [])

  // ── 刪除自訂項目（non-custom 子項目退回上一層）────────────────────────────
  const handleDeleteItem = useCallback((key: string) => {
    setItems((prev) => {
      // 找出目標與其父層 key
      let targetItem: WorkItem | null = null
      let parentKey: string | null = null

      const l1 = prev.find((p) => p.menu_key === key)
      if (l1) { targetItem = l1; parentKey = null }

      if (!targetItem) {
        for (const p of prev) {
          const l2 = p.children.find((c) => c.menu_key === key)
          if (l2) { targetItem = l2; parentKey = p.menu_key; break }
        }
      }

      if (!targetItem) {
        for (const p of prev) {
          for (const c of p.children) {
            const l3 = c.children.find((g) => g.menu_key === key)
            if (l3) { targetItem = l3; parentKey = c.menu_key; break }
          }
          if (targetItem) break
        }
      }

      if (!targetItem) return prev

      // 收集非 custom_ 子項目（退回上層）
      const nonCustomChildren = targetItem.children.filter(
        (c) => !c.menu_key.startsWith('custom_'),
      )

      // 從樹中移除目標（含所有子項目）
      let next = removeFromTree(prev, key)

      // 退回上層：非 custom_ 子項目插入被刪項目的父層
      if (parentKey === null) {
        // 被刪的是 L1，其非 custom_ 子項目提升為 L1
        next = [
          ...next,
          ...nonCustomChildren.map((c) => ({ ...c, parent_key: null })),
        ]
      } else {
        for (const child of nonCustomChildren) {
          next = insertUnderParent(next, parentKey, child)
        }
      }

      return next
    })
    setDirty(true)
  }, [])

  // ── 新增選單 ──────────────────────────────────────────────────────────────
  const openAddModal = (parentKey: string | null) => {
    setAddLabel('')
    setAddModal({ open: true, parentKey })
  }

  const handleAddConfirm = () => {
    const label = addLabel.trim()
    if (!label) { message.warning('請輸入顯示名稱'); return }

    const newKey = `custom_${Date.now()}`
    const { parentKey } = addModal

    setItems((prev) => {
      if (parentKey === null) {
        // 新增頂層
        const maxOrder = prev.length > 0 ? Math.max(...prev.map((p) => p.sort_order)) + 10 : 0
        return [
          ...prev,
          {
            menu_key: newKey,
            parent_key: null,
            defaultLabel: label,
            customLabel: label,
            sort_order: maxOrder,
            is_visible: true,
            children: [],
          },
        ]
      } else {
        // 新增子項目
        return prev.map((p) => {
          if (p.menu_key !== parentKey) return p
          const maxOrder = p.children.length > 0
            ? Math.max(...p.children.map((c) => c.sort_order)) + 10
            : 0
          return {
            ...p,
            children: [
              ...p.children,
              {
                menu_key: newKey,
                parent_key: parentKey,
                defaultLabel: label,
                customLabel: label,
                sort_order: maxOrder,
                is_visible: true,
                children: [],
              },
            ],
          }
        })
      }
    })

    setDirty(true)
    setAddModal({ open: false, parentKey: null })
    message.success('已新增，記得點「儲存變更」')
  }

  // ── 拖拉排序（支援三層，同層同父才可互換）───────────────────────────────
  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)
    if (!over || active.id === over.id) return

    const activeKey = active.id as string
    const overKey   = over.id as string

    setItems((prev) => {
      // L1
      const l1Keys = prev.map((p) => p.menu_key)
      if (l1Keys.includes(activeKey) && l1Keys.includes(overKey)) {
        return arrayMove(prev, prev.findIndex((p) => p.menu_key === activeKey), prev.findIndex((p) => p.menu_key === overKey))
      }

      // L2（同父）
      for (const parent of prev) {
        const l2Keys = parent.children.map((c) => c.menu_key)
        if (l2Keys.includes(activeKey) && l2Keys.includes(overKey)) {
          return prev.map((p) =>
            p.menu_key !== parent.menu_key ? p : {
              ...p,
              children: arrayMove(p.children, p.children.findIndex((c) => c.menu_key === activeKey), p.children.findIndex((c) => c.menu_key === overKey)),
            }
          )
        }
      }

      // L3（同父）
      for (const parent of prev) {
        for (const child of parent.children) {
          const l3Keys = child.children.map((g) => g.menu_key)
          if (l3Keys.includes(activeKey) && l3Keys.includes(overKey)) {
            return prev.map((p) =>
              p.menu_key !== parent.menu_key ? p : {
                ...p,
                children: p.children.map((c) =>
                  c.menu_key !== child.menu_key ? c : {
                    ...c,
                    children: arrayMove(c.children, c.children.findIndex((g) => g.menu_key === activeKey), c.children.findIndex((g) => g.menu_key === overKey)),
                  }
                ),
              }
            )
          }
        }
      }

      return prev
    })
    setDirty(true)
  }, [])

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }

  // ── 儲存 ──────────────────────────────────────────────────────────────────
  const handleSave = async () => {
    setSaving(true)
    try {
      const payload = flattenWorkItems(items)
      await saveMenuConfig(payload)
      // 儲存後從 DB 重拉，確保 MenuConfig 顯示與 DB 一致（ground truth）
      const freshConfigs = await fetchMenuConfig()
      setItems(buildWorkItems(DEFAULT_MENU_STRUCTURE, freshConfigs))
      message.success('選單設定已儲存')
      setDirty(false)
      // 通知 sidebar 同步（同一份 DB，兩邊保持一致）
      window.dispatchEvent(new CustomEvent('menuConfigSaved'))
    } catch {
      message.error('儲存失敗，請再試一次')
    } finally {
      setSaving(false)
    }
  }

  // ── 歷史記錄 ──────────────────────────────────────────────────────────────
  const openHistory = async () => {
    setHistoryOpen(true)
    setHistoryLoading(true)
    try {
      const data = await fetchMenuConfigHistory()
      setHistory(data)
    } catch {
      message.error('無法載入歷史記錄')
    } finally {
      setHistoryLoading(false)
    }
  }

  // ── Modal 新增階層計算 ─────────────────────────────────────────────────────
  const addLevel: 1 | 2 | 3 = addModal.parentKey === null ? 1
    : items.some((p) => p.menu_key === addModal.parentKey) ? 2 : 3
  const addLevelLabel = addLevel === 1 ? '一階' : addLevel === 2 ? '二階' : '三階'
  const addParentLabel = (() => {
    if (!addModal.parentKey) return null
    const p = items.find((x) => x.menu_key === addModal.parentKey)
    if (p) return p.customLabel || p.defaultLabel
    const c = items.flatMap((x) => x.children).find((x) => x.menu_key === addModal.parentKey)
    return c ? c.customLabel || c.defaultLabel : addModal.parentKey
  })()

  const activeItem = activeId
    ? items.find((p) => p.menu_key === activeId) ||
      items.flatMap((p) => p.children).find((c) => c.menu_key === activeId) ||
      items.flatMap((p) => p.children.flatMap((c) => c.children)).find((g) => g.menu_key === activeId)
    : null

  const parentKeys = items.map((p) => p.menu_key)

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      {/* ── 頁頭 ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>選單管理</Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            支援一、二、三階結構 · 拖拉排序（同層）· 改名 · 顯示／隱藏 · 跨層移動 · 刪除自訂項目 · 儲存後重整生效
          </Text>
        </div>
        <Space wrap>
          <Button icon={<PlusOutlined />} onClick={() => openAddModal(null)}>
            新增一階選單
          </Button>
          <Button icon={<ReloadOutlined />} onClick={load} disabled={loading}>
            重置
          </Button>
          <Button icon={<HistoryOutlined />} onClick={openHistory}>
            變更記錄
          </Button>
          <Button
            type="primary" icon={<SaveOutlined />}
            loading={saving} disabled={!dirty} onClick={handleSave}
          >
            {dirty ? '儲存變更' : '已是最新'}
          </Button>
        </Space>
      </div>

      {/* ── 圖示說明列 ── */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '4px 20px',
        fontSize: 12, color: '#8c8c8c',
        padding: '6px 10px', background: '#fafafa',
        border: '1px solid #f0f0f0', borderRadius: 6, marginBottom: 12,
      }}>
        <Space size={4}><MenuOutlined style={{ color: '#bbb' }} /><span>拖拉排序</span></Space>
        <Space size={4}><EditOutlined style={{ color: '#666' }} /><span>改名（雙擊也可）</span></Space>
        <Space size={4}><EyeOutlined style={{ color: '#666' }} /><span>顯示／隱藏</span></Space>
        <Space size={4}><ArrowsAltOutlined style={{ color: '#666' }} /><span>跨層移動</span></Space>
        <Space size={4}><DeleteOutlined style={{ color: '#ff4d4f' }} /><span>刪除（自訂項目）</span></Space>
        <Space size={4}>
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#e6f4ff', border: '1px solid #91caff' }} />
          <span>一階</span>
        </Space>
        <Space size={4}>
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#f6ffed', border: '1px solid #b7eb8f' }} />
          <span>二階</span>
        </Space>
        <Space size={4}>
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: 2, background: '#fff7e6', border: '1px solid #ffd591' }} />
          <span>三階</span>
        </Space>
      </div>

      {dirty && (
        <Alert
          type="warning" showIcon
          message="有未儲存的變更，請記得點「儲存變更」"
          style={{ marginBottom: 10 }}
          closable
        />
      )}

      <Spin spinning={loading}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={parentKeys} strategy={verticalListSortingStrategy}>
            {items.map((parent) => (
              <Card
                key={parent.menu_key}
                size="small"
                style={{
                  marginBottom: 8,
                  borderColor: parent.is_visible ? '#d6e4ff' : '#d9d9d9',
                  borderLeft: `3px solid ${parent.is_visible ? '#4096ff' : '#bfbfbf'}`,
                  opacity: parent.is_visible ? 1 : 0.65,
                  transition: 'opacity 0.2s',
                }}
                bodyStyle={{ padding: '4px 8px 8px' }}
              >
                {/* L1 列 */}
                <SortableRow
                  item={parent}
                  level={1}
                  parentKey={null}
                  grandparentKey={null}
                  allTopLevel={items}
                  onLabelChange={handleLabelChange}
                  onVisibleChange={handleVisibleChange}
                  onMoveItem={handleMoveItem}
                  onDeleteItem={handleDeleteItem}
                />

                {/* L2 子層 */}
                {parent.children.length > 0 && (
                  <>
                    <Divider style={{ margin: '4px 0' }} />
                    <SortableContext
                      items={parent.children.map((c) => c.menu_key)}
                      strategy={verticalListSortingStrategy}
                    >
                      {parent.children.map((child) => (
                        <div key={child.menu_key}>
                          <SortableRow
                            item={child}
                            level={2}
                            parentKey={parent.menu_key}
                            grandparentKey={null}
                            allTopLevel={items}
                            onLabelChange={handleLabelChange}
                            onVisibleChange={handleVisibleChange}
                            onMoveItem={handleMoveItem}
                            onDeleteItem={handleDeleteItem}
                          />

                          {/* L3 孫層 */}
                          {child.children.length > 0 && (
                            <SortableContext
                              items={child.children.map((g) => g.menu_key)}
                              strategy={verticalListSortingStrategy}
                            >
                              {child.children.map((grand) => (
                                <SortableRow
                                  key={grand.menu_key}
                                  item={grand}
                                  level={3}
                                  parentKey={child.menu_key}
                                  grandparentKey={parent.menu_key}
                                  allTopLevel={items}
                                  onLabelChange={handleLabelChange}
                                  onVisibleChange={handleVisibleChange}
                                  onMoveItem={handleMoveItem}
                                  onDeleteItem={handleDeleteItem}
                                />
                              ))}
                            </SortableContext>
                          )}

                          {/* 新增三階選單 */}
                          <div style={{ paddingLeft: 48, paddingTop: 2, paddingBottom: 2 }}>
                            <Button
                              type="dashed" size="small" icon={<PlusOutlined />}
                              style={{ fontSize: 11, color: '#d46b08', borderColor: '#ffd591', background: '#fffbe6' }}
                              onClick={() => openAddModal(child.menu_key)}
                            >
                              新增三階選單
                            </Button>
                          </div>
                        </div>
                      ))}
                    </SortableContext>
                  </>
                )}

                {/* 新增二階選單 */}
                <div style={{ paddingLeft: 24, paddingTop: 6, paddingBottom: 2 }}>
                  <Button
                    type="dashed" size="small" icon={<PlusOutlined />}
                    style={{ fontSize: 11, color: '#389e0d', borderColor: '#b7eb8f', background: '#f6ffed' }}
                    onClick={() => openAddModal(parent.menu_key)}
                  >
                    新增二階選單
                  </Button>
                </div>
              </Card>
            ))}
          </SortableContext>

          <DragOverlay>
            {activeItem && (
              <div
                style={{
                  padding: '8px 12px',
                  background: '#1677ff',
                  color: '#fff',
                  borderRadius: 6,
                  boxShadow: '0 4px 16px rgba(22,119,255,0.3)',
                  fontWeight: 600,
                  fontSize: 14,
                  opacity: 0.9,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <MenuOutlined />
                {activeItem.customLabel || activeItem.defaultLabel}
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </Spin>

      {/* ── 新增選單 Modal ── */}
      <Modal
        title={
          <Space size={6}>
            <Tag style={{
              fontSize: 11, lineHeight: '18px',
              background: addLevel === 1 ? '#e6f4ff' : addLevel === 2 ? '#f6ffed' : '#fff7e6',
              borderColor: addLevel === 1 ? '#91caff' : addLevel === 2 ? '#b7eb8f' : '#ffd591',
              color: addLevel === 1 ? '#1677ff' : addLevel === 2 ? '#389e0d' : '#d46b08',
            }}>
              {addLevelLabel}
            </Tag>
            <span>新增{addLevelLabel}選單{addParentLabel ? `（加入「${addParentLabel}」下）` : ''}</span>
          </Space>
        }
        open={addModal.open}
        onOk={handleAddConfirm}
        onCancel={() => setAddModal({ open: false, parentKey: null })}
        okText="新增"
        cancelText="取消"
        width={400}
      >
        <div style={{ padding: '8px 0' }}>
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
            輸入顯示名稱（路由 key 自動產生為 <Text code style={{ fontSize: 11 }}>custom_時間戳</Text>，新增後可用箭頭圖示移動至正確位置）
          </Text>
          <Input
            autoFocus
            placeholder="例：採購管理、資產盤點..."
            value={addLabel}
            onChange={(e) => setAddLabel(e.target.value)}
            onPressEnter={handleAddConfirm}
            maxLength={50}
          />
        </div>
      </Modal>

      {/* ── 歷史記錄 Drawer ── */}
      <Drawer
        title={<Space><HistoryOutlined /><span>最近 5 次變更記錄</span></Space>}
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        width={480}
      >
        <Spin spinning={historyLoading}>
          {history.length === 0 && !historyLoading ? (
            <Text type="secondary">尚無變更記錄</Text>
          ) : (
            <Timeline
              items={history.map((h, idx) => ({
                color: idx === 0 ? 'blue' : 'gray',
                children: (
                  <div>
                    <Space direction="vertical" size={2} style={{ flex: 1, minWidth: 0 }}>
                      <Space size={4}>
                        <Badge color={idx === 0 ? 'blue' : 'default'} />
                        <Text strong style={{ fontSize: 13 }}>{h.changed_at}</Text>
                        <Tag color={idx === 0 ? 'blue' : 'default'} style={{ fontSize: 11 }}>
                          {idx === 0 ? '最新' : `第 ${idx + 1} 次`}
                        </Tag>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>操作者：{h.changed_by}</Text>
                      <div
                        style={{
                          marginTop: 4,
                          padding: '6px 10px',
                          background: '#f5f5f5',
                          borderRadius: 4,
                          fontSize: 12,
                          lineHeight: '1.6',
                          color: '#555',
                          wordBreak: 'break-all',
                        }}
                      >
                        {parseDiff(h.diff_json)}
                      </div>
                    </Space>
                  </div>
                ),
              }))}
            />
          )}
        </Spin>
      </Drawer>
    </div>
  )
}
