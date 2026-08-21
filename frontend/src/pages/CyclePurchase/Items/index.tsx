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
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select, Space,
  Switch, Table, Tag, Typography, message, Divider,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, ApartmentOutlined, DeleteOutlined } from '@ant-design/icons'
import {
  createItem, createItemMapping, deleteItemMapping, getCpAccountCodes, getCpDepartments, getItem,
  getItems, getVendors, updateItem, updateItemMapping,
} from '@/api/cyclePurchase'
import type {
  CpAccountCode, CpDepartment, CpItem, CpItemDetail, CpItemMapping, CpVendor,
} from '@/types/cyclePurchase'

const { Title, Text } = Typography

const CATEGORY_OPTIONS = [
  { label: '工務', value: '工務' },
  { label: '清潔用品', value: '清潔用品' },
  { label: '文具印刷', value: '文具印刷' },
  { label: '營業用品', value: '營業用品' },
]

export default function CpItemsPage() {
  const [items, setItems] = useState<CpItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage] = useState(20)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [vendors, setVendors] = useState<CpVendor[]>([])
  const [departments, setDepartments] = useState<CpDepartment[]>([])
  // 2026-08-21 新增：會計科目掛在料號對照表（公司＋部門），這裡撈主檔供下拉選單用。
  const [accountCodes, setAccountCodes] = useState<CpAccountCode[]>([])

  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpItem | null>(null)
  const [form] = Form.useForm()
  // 2026-08-17 新增：編輯料號 Modal 內直接可編／新增公司+部門（見下方
  // openEdit／handleSubmit 說明）。這兩個 state 記錄「目前這個料號有幾筆
  // 對照」，用來決定要不要在這個 Modal 顯示可編輯欄位。
  const [editItemMappings, setEditItemMappings] = useState<CpItemMapping[]>([])
  const [editSingleMapping, setEditSingleMapping] = useState<CpItemMapping | null>(null)
  const editCompany = Form.useWatch('company', form)

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
  const editDepartmentOptions = useMemo(
    () => departments
      .filter((d) => d.company === editCompany)
      .map((d) => ({ label: d.dept_name, value: d.id })),
    [departments, editCompany],
  )

  const load = () => {
    setLoading(true)
    getItems({ q, page, per_page: perPage })
      .then((r) => {
        setItems(r.data.items)
        setTotal(r.data.total)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [page, q])
  useEffect(() => { getVendors({ is_active: true }).then((r) => setVendors(r.data)) }, [])
  useEffect(() => { getCpDepartments({ is_active: true }).then((r) => setDepartments(r.data)) }, [])
  useEffect(() => { getCpAccountCodes({ is_active: true }).then((r) => setAccountCodes(r.data)) }, [])

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
    setEditItemMappings([])
    setEditSingleMapping(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, is_cycle_item: true, default_qty: 0, moq: 0 })
    setModalOpen(true)
  }

  // 2026-08-17：改成 async，多打一次 getItem 撈這個料號目前的對照筆數。
  // 只有 0～1 筆時才把公司/部門欄位顯示成可編輯（見下方表單），>1 筆（少數
  // 共用料號）不知道要編輯哪一筆，維持原本「請到料號對照管理」的路徑。
  const openEdit = async (item: CpItem) => {
    setEditing(item)
    form.resetFields()
    form.setFieldsValue(item)
    setModalOpen(true)
    try {
      const r = await getItem(item.id)
      const mappings = r.data.mappings || []
      setEditItemMappings(mappings)
      if (mappings.length === 1) {
        setEditSingleMapping(mappings[0])
        form.setFieldsValue({
          company: mappings[0].company,
          department_id: mappings[0].department_id,
          // 2026-08-21：會計科目也存在對照表上，一併帶進表單（同上，只有 0～1
          // 筆對照時才可在這裡直接編輯）。
          account_code_id: mappings[0].account_code_id ?? undefined,
        })
      } else {
        setEditSingleMapping(null)
      }
    } catch {
      setEditItemMappings([])
      setEditSingleMapping(null)
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      // company／department_id／account_code_id 是這裡的便利欄位，不屬於
      // ItemUpdate/ItemCreate schema，要拆開來另外走料號對照的 API；
      // company_departments／account_code_labels 是列表顯示用的衍生欄位，
      // 會被 form.setFieldsValue(item) 帶進表單，送出前也要拿掉。
      const {
        company, department_id, account_code_id,
        company_departments, account_code_labels,
        ...itemValues
      } = values as any
      let itemId: number
      if (editing) {
        await updateItem(editing.id, itemValues)
        itemId = editing.id
        message.success('更新成功')
      } else {
        const res = await createItem(itemValues)
        itemId = res.data.id
        message.success('新增成功')
      }

      // 只有 0～1 筆對照時欄位才會出現在表單上；company/department_id 都有值
      // 才動作，任一沒填就當作「這次不設定」，不強迫一定要填。
      if (editItemMappings.length <= 1 && company && department_id) {
        // 2026-08-21：會計科目也一起送。account_code_id 清空時要送 null（不是
        // undefined），否則後端 exclude_unset 會當成「這次沒動到」而清不掉。
        const nextAccountCodeId = account_code_id ?? null
        if (editSingleMapping) {
          if (
            editSingleMapping.company !== company
            || editSingleMapping.department_id !== department_id
            || (editSingleMapping.account_code_id ?? null) !== nextAccountCodeId
          ) {
            await updateItemMapping(itemId, editSingleMapping.id, {
              company, department_id, account_code_id: nextAccountCodeId,
            })
          }
        } else {
          await createItemMapping(itemId, {
            company, department_id, account_code_id: nextAccountCodeId, is_confirmed: false,
          })
        }
      }

      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
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
          <Input.Search
            placeholder="搜尋料號／品名"
            allowClear
            style={{ width: 220 }}
            onSearch={(v) => { setPage(1); setQ(v) }}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增料號</Button>
        </Space>
      </div>

      <Card>
        <Table
          dataSource={items}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{
            current: page,
            pageSize: perPage,
            total,
            onChange: setPage,
            showTotal: (t) => `共 ${t} 筆`,
          }}
          columns={[
            { title: '集團料號', dataIndex: 'item_code', width: 120 },
            { title: '品名', dataIndex: 'item_name' },
            { title: '類別', dataIndex: 'category', width: 100 },
            {
              title: '公司/部門',
              dataIndex: 'company_departments',
              width: 160,
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
              render: (v: string[] | undefined) =>
                v && v.length
                  ? <Space size={[4, 4]} wrap>{v.map((ac) => <Tag key={ac} color="blue">{ac}</Tag>)}</Space>
                  : <Tag color="orange">未設定</Tag>,
            },
            { title: '單位', dataIndex: 'unit', width: 70 },
            { title: '預設供應商', dataIndex: 'default_vendor_name', width: 140 },
            { title: '參考單價', dataIndex: 'unit_price', width: 90, render: (v) => v != null ? `$${Number(v).toFixed(2)}` : '—' },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
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
      <Modal
        title={editing ? '編輯料號' : '新增料號'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Space.Compact block>
            <Form.Item name="item_code" label="集團料號" rules={[{ required: true }]} style={{ width: '50%' }}>
              <Input placeholder="新編碼，不沿用原公司料號" />
            </Form.Item>
            <Form.Item name="category" label="類別" style={{ width: '50%', marginLeft: 8 }}>
              <Select options={CATEGORY_OPTIONS} allowClear />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="item_name" label="品名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="spec" label="規格">
            <Input />
          </Form.Item>

          {/* 2026-08-17 新增：公司/部門。這個欄位其實存在「料號對照」子表，
              一個料號可能對到多組公司/部門（少數共用料號）。只有 0～1 筆對照
              時才在這裡直接編輯，>1 筆時不知道要編輯哪一筆，改顯示現有對照
              清單＋跳到「料號對照」管理的按鈕。 */}
          {editItemMappings.length <= 1 ? (
            <Space.Compact block>
              <Form.Item
                name="company"
                label="公司"
                style={{ width: '50%' }}
                extra={editItemMappings.length === 0 ? '留空 = 先不設定，之後可在「料號對照」新增' : undefined}
                rules={[{
                  validator: (_, value) =>
                    form.getFieldValue('department_id') && !value
                      ? Promise.reject(new Error('請選公司'))
                      : Promise.resolve(),
                }]}
              >
                <Select
                  allowClear
                  showSearch
                  placeholder="選擇公司"
                  options={companyOptions}
                  onChange={() => form.setFieldValue('department_id', undefined)}
                />
              </Form.Item>
              <Form.Item
                name="department_id"
                label="部門"
                style={{ width: '50%', marginLeft: 8 }}
                rules={[{
                  validator: (_, value) =>
                    form.getFieldValue('company') && !value
                      ? Promise.reject(new Error('請選部門'))
                      : Promise.resolve(),
                }]}
              >
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={editCompany ? '選擇部門' : '請先選公司'}
                  disabled={!editCompany}
                  options={editDepartmentOptions}
                />
              </Form.Item>
            </Space.Compact>
          ) : (
            <Form.Item label="公司/部門">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  這個料號目前對到 {editItemMappings.length} 組公司/部門，請到「料號對照」管理，不在這裡直接編輯。
                </Text>
                <Space wrap>
                  {editItemMappings.map((m) => (
                    <Tag key={m.id}>
                      {m.company}／{m.department_name || '未設定'}
                      {m.account_code_label ? `／${m.account_code_label}` : ''}
                    </Tag>
                  ))}
                </Space>
                <Button
                  size="small"
                  icon={<ApartmentOutlined />}
                  onClick={() => { setModalOpen(false); if (editing) openMappings(editing) }}
                >
                  前往料號對照管理
                </Button>
              </Space>
            </Form.Item>
          )}

          {/* 2026-08-21 新增：會計科目。跟公司/部門一樣存在「料號對照」子表
              （因為《設料號明細表》的會科是按部門欄位填的，同一料號在不同部門
              可能記到不同科目，例：E0204002 軌道燈 工程部 621601／營業部 1142），
              所以同樣只在 0～1 筆對照時才在這裡直接編輯。請購單建立明細時會自動
              帶入這個科目當快照，請購單畫面不再讓填單人手選。 */}
          {editItemMappings.length <= 1 && (
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
          )}

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
