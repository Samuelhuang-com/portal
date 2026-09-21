/**
 * 週期採購 — 料號主檔（含料號對照表管理）
 *
 * ⚠️ 依規劃報告第四節資料治理結論：
 * 集團料號為新編碼，不沿用日曜天地／春大直既有 E/C/G/S 系列編碼。
 * 「料號對照」用來記錄每個集團料號在各公司的原始料號／品名／廠商／單價，
 * 新增對照前務必人工確認品名／廠商／單價一致，不可只憑代碼相同就視為同一品項。
 *
 * 2026-07-11 新增部門欄位：逐列核對兩家公司的「設料號明細表.xlsx」後確認，
 * 每家公司內部分頁（工務用／清潔用品／文具&印刷／營業用品）對應真實的
 * 功能性部門，同一公司內沒有任何料號橫跨兩個分頁。因此每一筆料號對照
 * 現在都必須指定「這個料號在這家公司屬於哪個部門」，請購單「可選料號」
 * 查詢會按公司＋部門篩選（見 cycle_purchase_request_service.get_available_items）。
 *
 * 2026-08-17 新增「公司/部門」欄：原本列表看不到公司/部門歸屬，要點進
 * 「料號對照」才看得到，導致連續兩次有人在「週期設定」誤選了別公司/部門
 * 的品類（見 cycle_purchase_service.get_cycle_options 與 Cycles/index.tsx
 * 開頭說明）。現在直接在列表帶出（來自後端 ItemOut.company_departments，
 * 衍生自料號對照表，非資料表欄位），選擇前就看得到歸屬。
 *
 * 2026-09-16 新增篩選列（類別／公司/部門／會計科目／供應商）與表格欄位排序，
 * 原本的「搜尋料號／品名」保留。列表是後端分頁，所以篩選與排序都送到後端
 * （cycle_purchase_service.list_items），不是只排當頁 20 筆。每個篩選都有
 * 「未設定」選項（"__none__" / 0），方便找出還沒設公司/部門、科目、供應商的料號。
 * 「供應商」篩選同時比對料號主檔的預設供應商與料號對照上的叫貨供應商。
 *
 * 2026-09-21 類別改接類別主檔（cycle-purchase/masters/categories）：
 * 原本「類別」下拉是這支檔案寫死的 4 個舊值（工務／清潔用品／文具印刷／營業用品），
 * 但資料存的是類別主檔的類別字串（如「客廁備品-衛生紙」），一編輯就被改壞，
 * 料號從請購單「可選料號」消失。現在：
 *   · 新增／編輯改用「公司 → 大分類 → 中分類 → 細分類」四層 Cascader，送 category_id，
 *     category 字串由後端從主檔帶入（前端不再送）。
 *   · 編輯既有料號時，**沒動到類別欄位就不送 category_id**——尚未回填對應的舊料號
 *     （category_id 為 null）存檔不會被清掉類別字串。
 *   · 列表「類別」欄顯示「代碼前綴 + 類別字串」；尚未對應主檔的顯示橘色「未對應」。
 *   · 篩選改成同一棵類別樹＋「未對應類別主檔」，可停在任一層（公司／大／中／細）：
 *     前端把該層底下所有細分類 id 以 category_ids 送後端。
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Button, Card, Cascader, Form, Input, InputNumber, Modal, Popconfirm, Select, Space,
  Switch, Table, Tag, Tooltip, Typography, message, Divider,
} from 'antd'
import type { SorterResult } from 'antd/es/table/interface'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, ApartmentOutlined, DeleteOutlined, ClearOutlined } from '@ant-design/icons'
import {
  createItem, createItemMapping, deleteItemMapping, getCpAccountCodes, getCpCategories, getCpDepartments,
  getItem, getItems, getVendors, updateItem, updateItemMapping,
} from '@/api/cyclePurchase'
import type {
  CpAccountCode, CpCategory, CpDepartment, CpItem, CpItemDetail, CpItemMapping, CpVendor,
} from '@/types/cyclePurchase'

const { Title, Text } = Typography

// 2026-09-21：類別改由類別主檔建樹（見檔頭），原本寫死的 CATEGORY_OPTIONS 已移除。
type CategoryNode = { label: string; value: string | number; disabled?: boolean; children?: CategoryNode[] }

/** 類別主檔 → 「公司 → 大分類 → 中分類 → 細分類」樹；葉節點 value＝類別 id */
function buildCategoryTree(categories: CpCategory[]): CategoryNode[] {
  const tree: CategoryNode[] = []
  const find = (list: CategoryNode[], value: string, label: string) => {
    let n = list.find((x) => x.value === value)
    if (!n) { n = { label, value, children: [] }; list.push(n) }
    return n
  }
  for (const c of categories) {
    const company = find(tree, c.company, c.company)
    const major = find(company.children!, `${c.company}|${c.major_code}`, `${c.major_code} ${c.major_name}`)
    const mid = find(major.children!, `${c.company}|${c.major_code}|${c.mid_code}`, `${c.mid_code} ${c.mid_name}`)
    mid.children!.push({
      label: `${c.sub_code} ${c.sub_name || '（細分類未命名）'}${c.is_active ? '' : '（停用）'}`,
      value: c.id,
      disabled: !c.is_active,
    })
  }
  return tree
}

/** 類別 id → Cascader 的完整路徑值 */
function categoryPathValue(categories: CpCategory[], id?: number | null): (string | number)[] | undefined {
  const c = id ? categories.find((x) => x.id === id) : undefined
  if (!c) return undefined
  return [c.company, `${c.company}|${c.major_code}`, `${c.company}|${c.major_code}|${c.mid_code}`, c.id]
}

/** Cascader 搜尋：任一層標籤含關鍵字即命中 */
const categorySearch = {
  filter: (input: string, path: CategoryNode[]) =>
    path.some((o) => String(o.label).toLowerCase().includes(input.toLowerCase())),
}

/**
 * 類別樹上任一層的路徑 → 該層底下所有細分類 id。
 * 路徑值格式見 categoryPathValue：[公司, "公司|大", "公司|大|中", 類別id]
 */
function categoryIdsUnder(categories: CpCategory[], path: (string | number)[]): number[] {
  const [company, major, mid, leaf] = path
  if (leaf !== undefined) return [Number(leaf)]
  return categories
    .filter((c) => c.company === company)
    .filter((c) => major === undefined || `${c.company}|${c.major_code}` === major)
    .filter((c) => mid === undefined || `${c.company}|${c.major_code}|${c.mid_code}` === mid)
    .map((c) => c.id)
}

// 類別篩選「尚未對應類別主檔」哨兵值（對應後端 category_id=0）
const CATEGORY_UNMAPPED = '__unmapped__'

// 篩選「未設定」哨兵值（與後端 cycle_purchase_service.ITEM_UNSET 一致）
const UNSET = '__none__'

/**
 * 編輯料號 Modal 裡那張對照表的一列。
 * id 有值 ＝ 後端已存在的對照列；沒有 ＝ 使用者剛按「新增一列」還沒存。
 * key 是畫面用的穩定 rowKey，不送後端。
 */
type MappingRow = {
  key: string
  id?: number
  company?: string
  department_id?: number
  account_code_id?: number | null
  original_unit_price?: number | null
}

let mappingRowSeq = 0
const newMappingRowKey = () => `new-${++mappingRowSeq}`

const toMappingRow = (m: CpItemMapping): MappingRow => ({
  key: `db-${m.id}`,
  id: m.id,
  company: m.company,
  department_id: m.department_id ?? undefined,
  account_code_id: m.account_code_id ?? null,
  original_unit_price:
    m.original_unit_price === null || m.original_unit_price === undefined
      ? null
      : Number(m.original_unit_price),
})

// 只比對這張表管得到的四個欄位。其餘欄位（原始料號／品名／廠商／已確認）
// 仍由「料號對照」Modal 維護，這裡送更新時走 exclude_unset 不會動到它們。
const mappingRowChanged = (a: MappingRow, b: MappingRow) =>
  a.company !== b.company
  || a.department_id !== b.department_id
  || (a.account_code_id ?? null) !== (b.account_code_id ?? null)
  || (a.original_unit_price ?? null) !== (b.original_unit_price ?? null)

export default function CpItemsPage() {
  const [items, setItems] = useState<CpItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [q, setQ] = useState('')
  const [searchText, setSearchText] = useState('')
  // 2026-09-16 新增：篩選與排序（後端處理）
  // 2026-09-21：類別篩選改成類別樹路徑（最後一層＝類別 id），或 [CATEGORY_UNMAPPED]
  const [fCategory, setFCategory] = useState<(string | number)[] | undefined>()
  const [categories, setCategories] = useState<CpCategory[]>([])
  const [fCompanyDept, setFCompanyDept] = useState<string[] | undefined>()
  const [fAccountCode, setFAccountCode] = useState<number | undefined>()
  const [fVendor, setFVendor] = useState<number | undefined>()
  const [sortBy, setSortBy] = useState<string | undefined>()
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | undefined>()
  const [loading, setLoading] = useState(false)
  const [vendors, setVendors] = useState<CpVendor[]>([])
  const [departments, setDepartments] = useState<CpDepartment[]>([])
  // 2026-08-21 新增：會計科目掛在料號對照表（公司＋部門），這裡撈主檔供下拉選單用。
  const [accountCodes, setAccountCodes] = useState<CpAccountCode[]>([])

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpItem | null>(null)
  const [form] = Form.useForm()
  // 2026-09-20 改版（0919 會議 N1）：編輯料號 Modal 內直接編一張「公司／部門／
  // 會計科目／原始單價」對照表。
  //   · mappingRows      ＝ 畫面上正在編的工作清單（含還沒存回後端的新列）
  //   · mappingRowsBase  ＝ 打開 Modal 當下的後端原始狀態，送出時用來 diff
  //                        （哪些要新增、哪些要更新、哪些被刪掉）
  // 2026-08-17 的舊作法是「只有 0～1 筆對照時才給編」，>1 筆只能看 Tag ——
  // 撐不住真實資料（一個料號＝一個公司＋多個部門＋多個科目），見下方表格註解。
  const [mappingRows, setMappingRows] = useState<MappingRow[]>([])
  const [mappingRowsBase, setMappingRowsBase] = useState<MappingRow[]>([])

  const [mappingItem, setMappingItem] = useState<CpItemDetail | null>(null)
  const [mappingModalOpen, setMappingModalOpen] = useState(false)
  const [mappingForm] = Form.useForm()
  const [editingMapping, setEditingMapping] = useState<CpItemMapping | null>(null)
  const mappingCompany = Form.useWatch('company', mappingForm)

  const companyOptions = useMemo(
    () => Array.from(new Set(departments.map((d) => d.company))).map((c) => ({ label: c, value: c })),
    [departments],
  )
  const departmentOptionsForCompany = useMemo(
    () => departments
      .filter((d) => d.company === mappingCompany)
      .map((d) => ({ label: d.dept_name, value: d.id })),
    [departments, mappingCompany],
  )
  const accountCodeOptions = useMemo(
    () => accountCodes.map((a) => ({ label: `${a.code} ${a.name}`, value: a.id })),
    [accountCodes],
  )
  // 對照表每一列的公司都可能不同，部門選單要按「那一列的公司」過濾，
  // 不能再用單一個 Form.useWatch('company')。
  const departmentOptionsOf = (company?: string) =>
    departments
      .filter((d) => d.company === company)
      .map((d) => ({ label: d.dept_name, value: d.id }))

  // 重複判斷鍵＝公司＋部門（2026-09-20 Samuel 裁示，不含會計科目）。
  // 回傳「與前面某列撞號」的那些列 key，畫面上標紅、送出時擋下。
  const duplicateRowKeys = useMemo(() => {
    const seen = new Map<string, string>()
    const dup = new Set<string>()
    for (const r of mappingRows) {
      if (!r.company || !r.department_id) continue
      const k = `${r.company}|${r.department_id}`
      const first = seen.get(k)
      if (first) { dup.add(r.key); dup.add(first) } else { seen.set(k, r.key) }
    }
    return dup
  }, [mappingRows])

  // 篩選列：公司 → 部門 兩層（可只選公司）
  const companyDeptFilterOptions = useMemo(
    () => [
      { label: '未設定（尚無料號對照）', value: UNSET },
      ...Array.from(new Set(departments.map((d) => d.company))).map((c) => ({
        label: c,
        value: c,
        children: departments
          .filter((d) => d.company === c)
          .map((d) => ({ label: d.dept_name, value: String(d.id) })),
      })),
    ],
    [departments],
  )
  const categoryTree = useMemo(() => buildCategoryTree(categories), [categories])
  const categoryFilterOptions = useMemo(
    () => [{ label: '未對應類別主檔', value: CATEGORY_UNMAPPED }, ...categoryTree],
    [categoryTree],
  )
  const hasFilter = !!(q || fCategory?.length || fCompanyDept?.length || fAccountCode !== undefined || fVendor !== undefined)

  const resetFilters = () => {
    setSearchText('')
    setQ('')
    setFCategory(undefined)
    setFCompanyDept(undefined)
    setFAccountCode(undefined)
    setFVendor(undefined)
    setPage(1)
  }

  const load = () => {
    setLoading(true)
    const [cdCompany, cdDept] = fCompanyDept ?? []
    getItems({
      q,
      page,
      per_page: perPage,
      category_id: fCategory?.[0] === CATEGORY_UNMAPPED ? 0 : undefined,
      category_ids: fCategory?.length && fCategory[0] !== CATEGORY_UNMAPPED
        ? categoryIdsUnder(categories, fCategory).join(',') || '-1'   // 該層沒有細分類 → 查無資料
        : undefined,
      company: cdCompany,
      department_id: cdDept ? Number(cdDept) : undefined,
      account_code_id: fAccountCode,
      vendor_id: fVendor,
      sort_by: sortOrder ? sortBy : undefined,
      sort_order: sortOrder === 'descend' ? 'desc' : 'asc',
    })
      .then((r) => {
        setItems(r.data.items)
        setTotal(r.data.total)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [page, q, fCategory, fCompanyDept, fAccountCode, fVendor, sortBy, sortOrder])
  useEffect(() => { getVendors({ is_active: true }).then((r) => setVendors(r.data)) }, [])
  useEffect(() => { getCpDepartments({ is_active: true }).then((r) => setDepartments(r.data)) }, [])
  useEffect(() => { getCpAccountCodes({ is_active: true }).then((r) => setAccountCodes(r.data)) }, [])
  // 含停用的類別一起撈：既有料號可能掛在已停用的類別上，要能顯示路徑（選單裡會 disabled）
  useEffect(() => { getCpCategories().then((r) => setCategories(r.data)) }, [])

  const toggleActive = async (item: CpItem) => {
    try {
      await updateItem(item.id, { is_active: !item.is_active })
      message.success(item.is_active ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const openCreate = () => {
    setEditing(null)
    setMappingRows([])
    setMappingRowsBase([])
    form.resetFields()
    form.setFieldsValue({ is_active: true, is_cycle_item: true, default_qty: 0, moq: 0 })
    setModalOpen(true)
  }

  // 2026-08-17：改成 async，多打一次 getItem 撈這個料號目前的對照列。
  // 2026-09-20：不再只在 0～1 筆時給編，整批都載進工作清單，直接在表格上編。
  const openEdit = async (item: CpItem) => {
    setEditing(item)
    form.resetFields()
    form.setFieldsValue({ ...item, category_cascade: categoryPathValue(categories, item.category_id) })
    setMappingRows([])
    setMappingRowsBase([])
    setModalOpen(true)
    try {
      const r = await getItem(item.id)
      const rows = (r.data.mappings || []).map(toMappingRow)
      setMappingRows(rows)
      setMappingRowsBase(rows)
    } catch {
      setMappingRows([])
      setMappingRowsBase([])
    }
  }

  // ── 對照表工作清單的增／刪／改 ──────────────────────────────────────────
  const addMappingRow = () =>
    setMappingRows((rows) => [...rows, { key: newMappingRowKey(), account_code_id: null, original_unit_price: null }])

  const removeMappingRow = (key: string) =>
    setMappingRows((rows) => rows.filter((r) => r.key !== key))

  const patchMappingRow = (key: string, patch: Partial<MappingRow>) =>
    setMappingRows((rows) => rows.map((r) => (r.key === key ? { ...r, ...patch } : r)))

  const handleSubmit = async () => {
    // ── 先把對照表本身檢查完，不要等料號都存好了才發現對照有問題 ──────────
    const incomplete = mappingRows.filter((r) => !r.company || !r.department_id)
    if (incomplete.length) {
      message.error('對照表有列沒選完公司或部門，請補齊或刪掉該列')
      return
    }
    if (duplicateRowKeys.size) {
      message.error('對照表有重複的「公司＋部門」，同一個料號的同一個公司＋部門只能有一列')
      return
    }

    try {
      const values = await form.validateFields()
      // company_departments／account_code_labels 是列表顯示用的衍生欄位，
      // 會被 form.setFieldsValue(item) 帶進表單，送出前要拿掉。
      // 2026-09-21：category 相關欄位一律不直接送；類別只送 category_id（由 Cascader 換算）。
      const {
        company_departments, account_code_labels,
        category, category_path, category_company, category_code_prefix, category_cascade,
        ...itemValues
      } = values as any
      // 新增一律送；編輯時只有動過類別欄位才送——沒動就不送，避免尚未回填 category_id
      // 的舊料號存檔時被清掉類別字串。
      if (!editing || form.isFieldTouched('category_cascade')) {
        itemValues.category_id = category_cascade?.length
          ? Number(category_cascade[category_cascade.length - 1])
          : null
      }
      let itemId: number
      if (editing) {
        await updateItem(editing.id, itemValues)
        itemId = editing.id
      } else {
        const res = await createItem(itemValues)
        itemId = res.data.id
      }

      // ── 對照表 diff ────────────────────────────────────────────────────
      // 順序刻意是「先刪、再改、最後新增」：後端唯一鍵是（料號＋公司＋部門），
      // 先把讓出位置的列處理掉，才不會在中途撞到自己等一下要刪的那列。
      // ⚠️ 已知例外：兩列互換部門（A:管理→行銷、B:行銷→管理）還是會撞，
      //    後端會回 409 講清楚是哪一組，使用者分兩次存即可。
      const baseById = new Map(mappingRowsBase.filter((r) => r.id).map((r) => [r.id!, r]))
      const keptIds = new Set(mappingRows.filter((r) => r.id).map((r) => r.id!))

      for (const b of mappingRowsBase) {
        if (b.id && !keptIds.has(b.id)) await deleteItemMapping(itemId, b.id)
      }
      for (const r of mappingRows) {
        if (!r.id) continue
        const b = baseById.get(r.id)
        if (b && !mappingRowChanged(r, b)) continue
        await updateItemMapping(itemId, r.id, {
          company: r.company!,
          department_id: r.department_id!,
          // 清空時要送 null（不是 undefined），否則後端 exclude_unset 會當成
          // 「這次沒動到」而清不掉。
          account_code_id: r.account_code_id ?? null,
          original_unit_price: r.original_unit_price ?? null,
        })
      }
      for (const r of mappingRows) {
        if (r.id) continue
        await createItemMapping(itemId, {
          company: r.company!,
          department_id: r.department_id!,
          account_code_id: r.account_code_id ?? null,
          original_unit_price: r.original_unit_price ?? null,
          is_confirmed: false,
        })
      }

      message.success(editing ? '更新成功' : '新增成功')
      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
      // 料號本身可能已經存好、對照才失敗，重載讓畫面回到真實狀態。
      load()
    }
  }

  // ── 料號對照表 ──────────────────────────────────────────────────────────────

  const openMappings = async (item: CpItem) => {
    const r = await getItem(item.id)
    setMappingItem(r.data)
    setEditingMapping(null)
    mappingForm.resetFields()
    mappingForm.setFieldsValue({ is_confirmed: false })
    setMappingModalOpen(true)
  }

  const refreshMappings = async () => {
    if (!mappingItem) return
    const r = await getItem(mappingItem.id)
    setMappingItem(r.data)
  }

  const openEditMapping = (m: CpItemMapping) => {
    setEditingMapping(m)
    mappingForm.setFieldsValue(m)
  }

  const submitMapping = async () => {
    if (!mappingItem) return
    try {
      const values = await mappingForm.validateFields()
      if (editingMapping) {
        await updateItemMapping(mappingItem.id, editingMapping.id, values)
        message.success('對照已更新')
      } else {
        await createItemMapping(mappingItem.id, values)
        message.success('對照已新增')
      }
      setEditingMapping(null)
      mappingForm.resetFields()
      refreshMappings()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
    }
  }

  const removeMapping = async (m: CpItemMapping) => {
    if (!mappingItem) return
    await deleteItemMapping(mappingItem.id, m.id)
    message.success('已刪除')
    refreshMappings()
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 料號主檔</Title>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增料號</Button>
        </Space>
      </div>

      <Card>
        {/* 2026-09-16 新增：篩選列（搜尋保留在最前面） */}
        <Space wrap style={{ marginBottom: 12 }}>
          <Input.Search
            placeholder="搜尋料號／品名"
            allowClear
            style={{ width: 220 }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onSearch={(v) => { setPage(1); setQ(v) }}
          />
          <Cascader
            placeholder="類別"
            allowClear
            changeOnSelect
            showSearch={categorySearch}
            style={{ width: 240 }}
            value={fCategory}
            onChange={(v) => { setPage(1); setFCategory(v && v.length ? (v as (string | number)[]) : undefined) }}
            options={categoryFilterOptions}
            displayRender={(labels) => labels.join(' / ')}
          />
          <Cascader
            placeholder="公司/部門"
            allowClear
            changeOnSelect
            style={{ width: 200 }}
            value={fCompanyDept}
            onChange={(v) => { setPage(1); setFCompanyDept(v && v.length ? (v as string[]) : undefined) }}
            options={companyDeptFilterOptions}
            displayRender={(labels) => labels.join('／')}
          />
          <Select
            placeholder="會計科目"
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 200 }}
            value={fAccountCode}
            onChange={(v) => { setPage(1); setFAccountCode(v) }}
            options={[{ label: '未設定', value: 0 }, ...accountCodeOptions]}
          />
          <Select
            placeholder="供應商"
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 200 }}
            value={fVendor}
            onChange={(v) => { setPage(1); setFVendor(v) }}
            options={[{ label: '未設定', value: 0 }, ...vendors.map((v) => ({ label: v.vendor_name, value: v.id }))]}
          />
          <Button icon={<ClearOutlined />} onClick={resetFilters} disabled={!hasFilter}>清除篩選</Button>
        </Space>

        <Table
          dataSource={items}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{
            current: page,
            pageSize: perPage,
            total,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 筆`,
          }}
          onChange={(pg, _filters, sorter, extra) => {
            if (extra.action === 'sort') {
              const s = (Array.isArray(sorter) ? sorter[0] : sorter) as SorterResult<CpItem>
              setSortBy(s.order ? String(s.field) : undefined)
              setSortOrder(s.order ?? undefined)
              setPage(1)
            } else if (extra.action === 'paginate') {
              setPage(pg.current ?? 1)
            }
          }}
          columns={[
            { title: '集團料號', dataIndex: 'item_code', width: 120, sorter: true, sortOrder: sortBy === 'item_code' ? sortOrder : null },
            { title: '品名', dataIndex: 'item_name', sorter: true, sortOrder: sortBy === 'item_name' ? sortOrder : null },
            {
              // 2026-09-21：顯示「代碼前綴 類別字串」，滑過看完整三層；未對應主檔標橘色
              title: '類別',
              dataIndex: 'category',
              width: 170,
              sorter: true,
              sortOrder: sortBy === 'category' ? sortOrder : null,
              render: (v: string | null | undefined, r: CpItem) =>
                r.category_id
                  ? (
                    <Tooltip title={`${r.category_company ?? ''}：${r.category_path ?? ''}`}>
                      <span><Text type="secondary">{r.category_code_prefix}</Text> {v}</span>
                    </Tooltip>
                  )
                  : v
                    ? <Tooltip title="類別字串尚未對應類別主檔，請編輯料號重新選擇類別"><Tag color="orange">未對應</Tag>{v}</Tooltip>
                    : <Tag color="default">未設定</Tag>,
            },
            {
              title: '公司/部門',
              dataIndex: 'company_departments',
              width: 160,
              sorter: true,
              sortOrder: sortBy === 'company_departments' ? sortOrder : null,
              render: (v: string[] | undefined) =>
                v && v.length
                  ? <Space size={[4, 4]} wrap>{v.map((cd) => <Tag key={cd}>{cd}</Tag>)}</Space>
                  : <Tag color="default">未設定</Tag>,
            },
            {
              // 2026-08-21 新增：科目存在料號對照表（公司＋部門），請購明細建立時
              // 自動帶入。這裡顯示是為了一眼看出哪些料號還沒設科目（未設定＝該筆
              // 請購沒有科目可分攤）。
              title: '會計科目',
              dataIndex: 'account_code_labels',
              width: 160,
              sorter: true,
              sortOrder: sortBy === 'account_code_labels' ? sortOrder : null,
              render: (v: string[] | undefined) =>
                v && v.length
                  ? <Space size={[4, 4]} wrap>{v.map((ac) => <Tag key={ac} color="blue">{ac}</Tag>)}</Space>
                  : <Tag color="orange">未設定</Tag>,
            },
            { title: '單位', dataIndex: 'unit', width: 80, sorter: true, sortOrder: sortBy === 'unit' ? sortOrder : null },
            { title: '預設供應商', dataIndex: 'default_vendor_name', width: 140, sorter: true, sortOrder: sortBy === 'default_vendor_name' ? sortOrder : null },
            { title: '參考單價', dataIndex: 'unit_price', width: 100, sorter: true, sortOrder: sortBy === 'unit_price' ? sortOrder : null, render: (v) => v != null ? `$${Number(v).toFixed(2)}` : '—' },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              sorter: true,
              sortOrder: sortBy === 'is_active' ? sortOrder : null,
              render: (v: boolean) => (v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>),
            },
            {
              title: '操作',
              key: 'actions',
              width: 260,
              render: (_: unknown, r: CpItem) => (
                <Space>
                  <Button size="small" icon={<ApartmentOutlined />} onClick={() => openMappings(r)}>料號對照</Button>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active ? '確定停用？' : '確定啟用？'}
                    onConfirm={() => toggleActive(r)}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button size="small" danger={r.is_active} icon={r.is_active ? <StopOutlined /> : <CheckCircleOutlined />}>
                      {r.is_active ? '停用' : '啟用'}
                    </Button>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      {/* 新增／編輯料號 */}
      {/* 2026-09-20：Modal 寬度 640 → 1040。公司／部門／會計科目／原始單價 排成
          一列之後，640 寬會讓每個下拉都窄到看不見完整的部門名與科目名。 */}
      <Modal
        title={editing ? '編輯料號' : '新增料號'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={1040}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Space.Compact block>
            <Form.Item name="item_code" label="集團料號" rules={[{ required: true }]} style={{ width: '50%' }}>
              <Input placeholder="新編碼，不沿用原公司料號" />
            </Form.Item>
            <Form.Item
              name="category_cascade"
              label="類別（公司 / 大分類 / 中分類 / 細分類）"
              style={{ width: '50%', marginLeft: 8 }}
              extra={editing && !editing.category_id && editing.category
                ? `目前類別「${editing.category}」尚未對應類別主檔，請重新選擇`
                : undefined}
            >
              <Cascader
                options={categoryTree}
                allowClear
                showSearch={categorySearch}
                placeholder="選到細分類"
                displayRender={(labels) => labels.join(' / ')}
              />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="item_name" label="品名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="spec" label="規格">
            <Input />
          </Form.Item>

          {/* ── 公司／部門／會計科目／原始單價 對照表 ───────────────────────
              2026-09-20 改版（0919 會議 N1）。原本這三個欄位是「只有 0～1 筆對照
              時才給編輯」的單組欄位，>1 筆就只能看 Tag、得跳到「料號對照」Modal。
              撐不住真實資料 —— 一個料號本來就是「一個公司 ＋ 多個部門 ＋ 多個科目」：
                五月花大捲筒衛生紙 #0105054 ＝ 春大直＋管理部＋6238 清潔費
                                          ＝ 春大直＋行銷部＋6241 雜項支出
              這也是「文具用品只有 4 個部門能請購」的原因（一個料號只設得了一個部門）。
              改成直接在這裡編一張表，每列一組。

              ⚠️ 重複的判斷鍵是「公司＋部門」，**不含會計科目**（2026-09-20 Samuel 裁示）。
                 請購單建立明細時是用 (公司, 部門) 去抓這筆對照來帶科目與單價
                 （request_service.add_request_item 的 .first()），一個部門掛兩個
                 科目那裡就會隨機挑一筆。要改成一部門多科目，得先決定請購單怎麼選。

              ⚠️ 「原始單價」放進這張表是刻意的：請購單的單價就是抓這一欄
                 （mapping.original_unit_price）。新增一列卻沒填單價，那個部門請購
                 出來沒價錢，彙整單會以「缺單價」擋下不拋轉。

              其餘欄位（原始料號／原始品名／原始廠商／已確認）仍在「料號對照」Modal
              維護；這裡送更新時走 exclude_unset，不會動到它們。 */}
          <Form.Item
            label="公司 / 部門 / 會計科目"
            style={{ marginBottom: 12 }}
            extra="一個料號可以對到多組公司＋部門，各自有自己的會計科目與單價。同一組公司＋部門只能有一列。"
          >
            <Table<MappingRow>
              size="small"
              rowKey="key"
              dataSource={mappingRows}
              pagination={false}
              locale={{ emptyText: '尚未設定任何公司／部門，請按下方「新增一列」' }}
              columns={[
                {
                  title: <span><span style={{ color: '#ff4d4f' }}>*</span> 公司</span>,
                  dataIndex: 'company',
                  width: 170,
                  render: (_: unknown, r: MappingRow) => (
                    <Select
                      style={{ width: '100%' }}
                      showSearch
                      placeholder="選擇公司"
                      status={duplicateRowKeys.has(r.key) ? 'error' : undefined}
                      value={r.company}
                      options={companyOptions}
                      // 換公司時部門一定要清掉：部門選單是依公司過濾的，
                      // 留著舊部門會存進一筆別家公司的部門 id。
                      onChange={(v) => patchMappingRow(r.key, { company: v, department_id: undefined })}
                    />
                  ),
                },
                {
                  title: <span><span style={{ color: '#ff4d4f' }}>*</span> 部門</span>,
                  dataIndex: 'department_id',
                  width: 170,
                  render: (_: unknown, r: MappingRow) => (
                    <Select
                      style={{ width: '100%' }}
                      showSearch
                      optionFilterProp="label"
                      placeholder={r.company ? '選擇部門' : '請先選公司'}
                      disabled={!r.company}
                      status={duplicateRowKeys.has(r.key) ? 'error' : undefined}
                      value={r.department_id}
                      // 2026-09-21：同公司其他列已選過的部門不再出現（自己這列目前的值保留）
                      options={departmentOptionsOf(r.company).filter((o) =>
                        o.value === r.department_id
                        || !mappingRows.some((x) => x.key !== r.key && x.company === r.company && x.department_id === o.value))}
                      onChange={(v) => patchMappingRow(r.key, { department_id: v })}
                    />
                  ),
                },
                {
                  title: '會計科目',
                  dataIndex: 'account_code_id',
                  render: (_: unknown, r: MappingRow) => (
                    <Select
                      style={{ width: '100%' }}
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      placeholder="留空 = 尚未設定"
                      value={r.account_code_id ?? undefined}
                      options={accountCodeOptions}
                      onChange={(v) => patchMappingRow(r.key, { account_code_id: v ?? null })}
                    />
                  ),
                },
                {
                  title: '原始單價',
                  dataIndex: 'original_unit_price',
                  width: 120,
                  render: (_: unknown, r: MappingRow) => (
                    <InputNumber
                      style={{ width: '100%' }}
                      min={0}
                      precision={2}
                      step={0.01}
                      placeholder="未設定"
                      value={r.original_unit_price ?? undefined}
                      onChange={(v) => patchMappingRow(r.key, { original_unit_price: v ?? null })}
                    />
                  ),
                },
                {
                  title: '',
                  key: 'actions',
                  width: 90,
                  render: (_: unknown, r: MappingRow) => (
                    <Space size={4}>
                      {duplicateRowKeys.has(r.key) && <Tag color="red">重複</Tag>}
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => removeMappingRow(r.key)}
                      />
                    </Space>
                  ),
                },
              ]}
            />
            <Space style={{ marginTop: 8 }}>
              <Button size="small" icon={<PlusOutlined />} onClick={addMappingRow}>新增一列</Button>
              {editing && (
                <Button
                  size="small"
                  icon={<ApartmentOutlined />}
                  onClick={() => { setModalOpen(false); openMappings(editing) }}
                >
                  原始料號／品名／廠商…（料號對照管理）
                </Button>
              )}
            </Space>
            {duplicateRowKeys.size > 0 && (
              <Text type="danger" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                有重複的「公司＋部門」（標紅那幾列），同一個料號的同一個公司＋部門只能有一列。請修正後再儲存。
              </Text>
            )}
          </Form.Item>

          <Space.Compact block>
            <Form.Item name="unit" label="單位" style={{ width: '25%' }}>
              <Input />
            </Form.Item>
            <Form.Item name="default_qty" label="批次預設數量" style={{ width: '25%', marginLeft: 8 }}>
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
            <Form.Item name="moq" label="最小訂購量" style={{ width: '25%', marginLeft: 8 }}>
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
            <Form.Item name="unit_price" label="參考單價" style={{ width: '25%', marginLeft: 8 }}>
              <InputNumber style={{ width: '100%' }} min={0} precision={2} step={0.01} />
            </Form.Item>
          </Space.Compact>
          <Space.Compact block>
            <Form.Item name="max_stock" label="最大庫存量（參考）" style={{ width: '50%' }}>
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
            <Form.Item name="min_stock" label="最小庫存量（參考）" style={{ width: '50%', marginLeft: 8 }}>
              <InputNumber style={{ width: '100%' }} min={0} />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="default_vendor_id" label="預設供應商">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={vendors.map((v) => ({ label: v.vendor_name, value: v.id }))}
            />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Space size="large">
            <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="is_cycle_item" label="週期採購專用" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* 料號對照表管理 */}
      <Modal
        title={mappingItem ? `料號對照 — ${mappingItem.item_code} ${mappingItem.item_name}` : '料號對照'}
        open={mappingModalOpen}
        onCancel={() => { setMappingModalOpen(false); setMappingItem(null) }}
        footer={null}
        width={760}
      >
        {mappingItem && (
          <>
            <Text type="secondary">
              ⚠️ 新增對照前請先確認公司原始品名／廠商／單價，兩家公司即使原始料號相同也可能是不同品項，不可自動合併。
              部門決定這個料號會出現在哪個部門的請購單「可選料號」清單裡，請依實際歸屬選擇，不要亂猜。
            </Text>
            <Table
              style={{ marginTop: 12 }}
              size="small"
              rowKey="id"
              dataSource={mappingItem.mappings}
              pagination={false}
              columns={[
                { title: '公司別', dataIndex: 'company', width: 100 },
                { title: '部門', dataIndex: 'department_name', width: 100, render: (v?: string | null) => v || <Tag>未設定</Tag> },
                { title: '原始料號', dataIndex: 'original_code', width: 100 },
                { title: '原始品名', dataIndex: 'original_name' },
                { title: '原始廠商', dataIndex: 'original_vendor_name', width: 120 },
                { title: '原始單價', dataIndex: 'original_unit_price', width: 90 },
                {
                  title: '會計科目',
                  dataIndex: 'account_code_label',
                  width: 140,
                  render: (v?: string | null) => v || <Tag color="orange">未設定</Tag>,
                },
                {
                  title: '已確認',
                  dataIndex: 'is_confirmed',
                  width: 80,
                  render: (v: boolean) => (v ? <Tag color="green">已確認</Tag> : <Tag color="orange">待確認</Tag>),
                },
                {
                  title: '操作',
                  key: 'actions',
                  width: 130,
                  render: (_: unknown, r: CpItemMapping) => (
                    <Space>
                      <Button size="small" icon={<EditOutlined />} onClick={() => openEditMapping(r)} />
                      <Popconfirm title="確定刪除此對照？" onConfirm={() => removeMapping(r)}>
                        <Button size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]}
            />

            <Divider />
            <Text strong>{editingMapping ? '編輯對照' : '新增對照'}</Text>
            <Form form={mappingForm} layout="vertical" style={{ marginTop: 12 }}>
              <Space.Compact block>
                <Form.Item name="company" label="公司別" rules={[{ required: true }]} style={{ width: '33%' }}>
                  <Select
                    showSearch
                    placeholder="選擇公司"
                    options={companyOptions}
                    onChange={() => mappingForm.setFieldValue('department_id', undefined)}
                  />
                </Form.Item>
                <Form.Item
                  name="department_id"
                  label="部門"
                  rules={[{ required: true, message: '請選擇部門' }]}
                  style={{ width: '33%', marginLeft: 8 }}
                >
                  <Select
                    showSearch
                    optionFilterProp="label"
                    placeholder={mappingCompany ? '選擇部門' : '請先選公司'}
                    disabled={!mappingCompany}
                    options={departmentOptionsForCompany}
                  />
                </Form.Item>
                <Form.Item name="original_unit_price" label="原始單價" style={{ width: '34%', marginLeft: 8 }}>
                  <InputNumber style={{ width: '100%' }} min={0} />
                </Form.Item>
              </Space.Compact>
              <Space.Compact block>
                <Form.Item name="original_code" label="原始料號" style={{ width: '50%' }}>
                  <Input />
                </Form.Item>
                <Form.Item name="original_vendor_name" label="原始廠商" style={{ width: '50%', marginLeft: 8 }}>
                  <Input />
                </Form.Item>
              </Space.Compact>
              <Form.Item name="original_name" label="原始品名">
                <Input />
              </Form.Item>
              {/* 2026-08-21 新增：會計科目按「公司＋部門」設定，請購單建立明細時
                  自動帶入當快照，請購單畫面不再讓填單人手選。 */}
              <Form.Item
                name="account_code_id"
                label="會計科目"
                extra="請購單會自動帶入這個科目，填單人不需要再選。留空 = 尚未設定。"
              >
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder="選擇會計科目"
                  options={accountCodeOptions}
                />
              </Form.Item>
              <Form.Item name="is_confirmed" label="已人工確認品名／廠商／單價相符" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Space>
                <Button type="primary" onClick={submitMapping}>
                  {editingMapping ? '更新對照' : '新增對照'}
                </Button>
                {editingMapping && (
                  <Button onClick={() => { setEditingMapping(null); mappingForm.resetFields() }}>取消編輯</Button>
                )}
              </Space>
            </Form>
          </>
        )}
      </Modal>
    </div>
  )
}
