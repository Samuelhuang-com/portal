/**
 * 週期採購 — 週期設定
 * 第一層：定義請購規則、頻率、開放天數、截止日、適用品類與適用單位。
 *
 * 2026-08-09（部門範圍 + 品類接線，與 Samuel 確認；規格見
 * docs/SPEC_cycle_purchase_dept_scope.md）：
 *
 * 1. **「適用公司／部門」拆成兩個欄位。** 改版前是單一自由文字輸入框，標籤寫
 *    「適用公司／部門」，但後端 `_applicable_departments()` 從來只比對公司 ——
 *    填部門名稱會篩出 0 筆並拋錯。現在拆成「適用公司」（multi-select）＋
 *    「適用部門」（multi-select，選項依已選公司連動過濾）。
 *
 * 2. **三個範圍欄位一律改成 multi-select，不讓使用者手打。** applicable_scope 與
 *    applicable_categories 都要跟主檔做字串比對，與彙整單 2026-07-16 踩過的
 *    「期別字串打不一致 → 查到 0 筆 → 誤以為沒資料」是同一種病灶。選項來自
 *    GET /cycles/options（部門主檔 distinct company、料號主檔 distinct category）。
 *
 * 3. **適用部門留空 = 該公司全部啟用中部門**（舊資料自動相容）。UI 上用 placeholder
 *    與說明文字講清楚，不要讓人以為留空是「都不適用」。
 *
 * 4. **儲存時的兩段式確認**：縮小範圍後，之前已產生給「現在不適用部門」的空白單
 *    會變成清單雜訊。按儲存 → 先打 previewOrphanRequests 拿到會被刪掉的單號 →
 *    列出來讓使用者確認 → 確認後才送 PUT ?delete_orphans=true。
 *    **刪資料一定要先讓人看到刪什麼**，不做靜默清除。
 *    判準（後端把關）：明細 0 筆 + 未關閉 + 未彙整，三者全部成立才刪。
 *
 * 5. 資料模型上這三個欄位都是「逗號分隔字串」，表單用陣列操作比較好寫，
 *    因此在 openEdit / handleSubmit 兩處做字串 ↔ 陣列轉換（csvToArr / arrToCsv）。
 *    部門是 id 陣列（數字），公司與品類是名稱陣列（字串）。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, Modal, Select, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import {
  createCycle, getCpDepartments, getCycleOptions, getCycles, previewOrphanRequests, updateCycle,
} from '@/api/cyclePurchase'
import type { CpCycle, CpDepartment, CpOrphanRequest } from '@/types/cyclePurchase'

const { Title, Text } = Typography

const FREQUENCY_OPTIONS = [
  { label: '每月一次', value: 'monthly' },
  { label: '雙週一次', value: 'biweekly' },
  { label: '每兩個月一次', value: 'bimonthly' },
  { label: '自訂', value: 'custom' },
]

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  active: { color: 'green', label: '啟用' },
  inactive: { color: 'default', label: '停用' },
  paused: { color: 'orange', label: '暫停' },
}

// ── 逗號分隔字串 ↔ 陣列 ──────────────────────────────────────────────────────
const csvToArr = (v?: string | null): string[] =>
  (v || '').split(',').map((s) => s.trim()).filter(Boolean)

const csvToIds = (v?: string | null): number[] =>
  csvToArr(v).map((s) => Number(s)).filter((n) => Number.isFinite(n))

const arrToCsv = (v?: (string | number)[] | null): string | null =>
  v && v.length ? v.join(',') : null

// 表單內部用的型別（陣列版），送出前轉回逗號分隔字串
type CycleFormValues = Omit<
  Partial<CpCycle>,
  'applicable_scope' | 'applicable_categories' | 'applicable_department_ids'
> & {
  applicable_scope?: string[]
  applicable_categories?: string[]
  applicable_department_ids?: number[]
}

export default function CpCyclesPage() {
  const [rows, setRows] = useState<CpCycle[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState<CpCycle | null>(null)
  const [form] = Form.useForm<CycleFormValues>()

  // 下拉選項來源
  const [companies, setCompanies] = useState<string[]>([])
  const [categories, setCategories] = useState<string[]>([])
  const [departments, setDepartments] = useState<CpDepartment[]>([])

  // 表單目前選到的公司（用來連動過濾部門選項）
  const selectedCompanies = Form.useWatch('applicable_scope', form)

  const load = useCallback(() => {
    setLoading(true)
    getCycles().then((r) => setRows(r.data)).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    getCycleOptions().then((r) => {
      setCompanies(r.data.companies)
      setCategories(r.data.categories)
    })
    getCpDepartments({ is_active: true }).then((r) => setDepartments(r.data))
  }, [load])

  // 部門選項依已選公司過濾；沒選公司就全部列出（等同「不限公司」）
  const departmentOptions = useMemo(() => {
    const picked = selectedCompanies || []
    const pool = picked.length
      ? departments.filter((d) => picked.includes(d.company))
      : departments
    return pool.map((d) => ({
      label: `${d.company} / ${d.dept_name}`,
      value: d.id,
    }))
  }, [departments, selectedCompanies])

  const deptNameOf = useCallback(
    (id: number) => {
      const d = departments.find((x) => x.id === id)
      return d ? `${d.company} / ${d.dept_name}` : `部門 #${id}`
    },
    [departments],
  )

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ frequency: 'monthly', auto_generate: false, status: 'active' })
    setModalOpen(true)
  }

  const openEdit = (r: CpCycle) => {
    setEditing(r)
    form.setFieldsValue({
      ...r,
      applicable_scope: csvToArr(r.applicable_scope),
      applicable_categories: csvToArr(r.applicable_categories),
      applicable_department_ids: csvToIds(r.applicable_department_ids),
    } as CycleFormValues)
    setModalOpen(true)
  }

  /** 把表單的陣列值轉回後端要的逗號分隔字串 */
  const toPayload = (values: CycleFormValues): Partial<CpCycle> => ({
    ...values,
    applicable_scope: arrToCsv(values.applicable_scope),
    applicable_categories: arrToCsv(values.applicable_categories),
    applicable_department_ids: arrToCsv(values.applicable_department_ids),
  })

  /** 真正送出（deleteOrphans 由呼叫端決定） */
  const doSave = async (payload: Partial<CpCycle>, deleteOrphans: boolean) => {
    setSaving(true)
    try {
      if (editing) {
        const res = await updateCycle(editing.id, payload, deleteOrphans)
        const removed = res.data.deleted_orphan_count
        message.success(removed ? `更新成功，已刪除 ${removed} 張孤兒空白請購單` : '更新成功')
      } else {
        await createCycle(payload as Omit<CpCycle, 'id' | 'created_at' | 'updated_at'>)
        message.success('新增成功')
      }
      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      message.error(detail || '儲存失敗')
    } finally {
      setSaving(false)
    }
  }

  /**
   * 儲存流程：
   *   新增 → 直接存（沒有既有請購單，不會有孤兒）
   *   編輯 → 先預覽孤兒空白單；有的話彈確認框，讓使用者看清楚要刪哪幾張再決定
   */
  const handleSubmit = async () => {
    let values: CycleFormValues
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    const payload = toPayload(values)

    if (!editing) {
      await doSave(payload, false)
      return
    }

    let orphans: CpOrphanRequest[] = []
    let protectedCount = 0
    try {
      const res = await previewOrphanRequests(editing.id, payload)
      orphans = res.data.orphans
      protectedCount = res.data.protected_count
    } catch (err: any) {
      // 預覽失敗不擋儲存，但要讓使用者知道這次不會順便清理
      message.warning('無法預覽受影響的請購單，本次儲存將不清理孤兒空白單')
      await doSave(payload, false)
      return
    }

    if (!orphans.length) {
      if (protectedCount > 0) {
        message.info(`有 ${protectedCount} 張不再適用部門的請購單因為已填寫／已關閉／已彙整而保留`)
      }
      await doSave(payload, false)
      return
    }

    Modal.confirm({
      title: '這次調整會刪掉以下空白請購單',
      icon: <ExclamationCircleOutlined />,
      width: 620,
      okText: `確認儲存並刪除 ${orphans.length} 張`,
      okButtonProps: { danger: true },
      cancelText: '取消',
      content: (
        <div>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message="只會刪除「完全沒填明細、尚未關閉、也還沒被彙整」的空白單"
            description={
              protectedCount > 0
                ? `另有 ${protectedCount} 張不再適用部門的請購單因為已填寫／已關閉／已彙整而保留，不會被刪除。`
                : undefined
            }
          />
          <div style={{ maxHeight: 260, overflowY: 'auto' }}>
            <Table
              dataSource={orphans}
              rowKey="id"
              size="small"
              pagination={false}
              columns={[
                { title: '請購單號', dataIndex: 'request_no', width: 150 },
                { title: '期別', dataIndex: 'period_label', width: 90 },
                { title: '公司', dataIndex: 'company', width: 100 },
                {
                  title: '部門',
                  dataIndex: 'department_name',
                  render: (v: string | null) => v || '—',
                },
              ]}
            />
          </div>
        </div>
      ),
      onOk: () => doSave(payload, true),
    })
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 週期設定</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增週期設定</Button>
      </div>

      <Card>
        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '週期代碼', dataIndex: 'cycle_code', width: 120 },
            { title: '週期名稱', dataIndex: 'cycle_name' },
            {
              title: '頻率',
              dataIndex: 'frequency',
              width: 100,
              render: (v: string) => FREQUENCY_OPTIONS.find((f) => f.value === v)?.label || v,
            },
            {
              title: '適用公司',
              dataIndex: 'applicable_scope',
              width: 150,
              render: (v: string | null) => {
                const arr = csvToArr(v)
                if (!arr.length || arr[0].toLowerCase() === 'all') return <Tag>不限</Tag>
                return <>{arr.map((c) => <Tag key={c}>{c}</Tag>)}</>
              },
            },
            {
              title: '適用部門',
              dataIndex: 'applicable_department_ids',
              width: 200,
              render: (v: string | null) => {
                const ids = csvToIds(v)
                if (!ids.length) return <Tag>全部部門</Tag>
                return <>{ids.map((id) => <Tag key={id}>{deptNameOf(id)}</Tag>)}</>
              },
            },
            {
              title: '適用品類',
              dataIndex: 'applicable_categories',
              width: 160,
              render: (v: string | null) => {
                const arr = csvToArr(v)
                if (!arr.length) return <Tag>不限</Tag>
                return <>{arr.map((c) => <Tag key={c}>{c}</Tag>)}</>
              },
            },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 90,
              render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
            },
            {
              title: '操作',
              key: 'actions',
              width: 100,
              render: (_: unknown, r: CpCycle) => (
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title={editing ? '編輯週期設定' : '新增週期設定'}
        open={modalOpen}
        onOk={handleSubmit}
        confirmLoading={saving}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Space.Compact block>
            <Form.Item name="cycle_code" label="週期代碼" rules={[{ required: true }]} style={{ width: '50%' }}>
              <Input placeholder="如 GP-MONT-STATIONERY" disabled={!!editing} />
            </Form.Item>
            <Form.Item name="frequency" label="請購頻率" rules={[{ required: true }]} style={{ width: '50%', marginLeft: 8 }}>
              <Select options={FREQUENCY_OPTIONS} />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="cycle_name" label="週期名稱" rules={[{ required: true }]}>
            <Input placeholder="如：每月文具統購" />
          </Form.Item>
          <Form.Item name="open_rule" label="開放規則說明">
            <Input placeholder="如：每月第 1 日開放" />
          </Form.Item>
          <Form.Item name="close_rule" label="截止規則說明">
            <Input placeholder="如：開放後 5 天截止" />
          </Form.Item>

          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message="適用範圍決定「產生本期請購單」會建立哪些部門的單"
            description={
              <Text type="secondary" style={{ fontSize: 12 }}>
                實際產生 = 適用公司 ∩ 適用部門 ∩「該品類下有啟用中料號的部門」。
                三個欄位留空都代表「不限」；勾選了但該品類下沒有料號的部門不會產生，
                產生時會列出原因。
              </Text>
            }
          />

          <Form.Item
            name="applicable_scope"
            label="適用公司"
            extra="留空 = 不限公司"
          >
            <Select
              mode="multiple"
              allowClear
              placeholder="留空 = 不限公司"
              options={companies.map((c) => ({ label: c, value: c }))}
            />
          </Form.Item>
          <Form.Item
            name="applicable_department_ids"
            label="適用部門"
            extra="留空 = 上面所選公司底下的全部啟用中部門；選項會依「適用公司」連動過濾"
          >
            <Select
              mode="multiple"
              allowClear
              placeholder="留空 = 全部部門"
              options={departmentOptions}
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item
            name="applicable_categories"
            label="適用品類"
            extra="留空 = 不限品類；同時決定請購單「可選料號」的範圍"
          >
            <Select
              mode="multiple"
              allowClear
              placeholder="留空 = 不限品類"
              options={categories.map((c) => ({ label: c, value: c }))}
            />
          </Form.Item>

          <Form.Item name="reminder_rule" label="提醒規則說明">
            <Input.TextArea rows={2} placeholder="如：開放通知、截止前 1 天提醒、逾期未填提醒" />
          </Form.Item>
          <Space size="large">
            <Form.Item name="auto_generate" label="自動產生批次" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="status" label="狀態" style={{ width: 160 }}>
              <Select
                options={[
                  { label: '啟用', value: 'active' },
                  { label: '停用', value: 'inactive' },
                  { label: '暫停', value: 'paused' },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
