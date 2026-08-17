/**
 * 系統設定 — 公司/部門管理
 *
 * 2026-08-17 新增（與 Samuel 確認跨模組整合範圍後）：這裡管理的 Company／
 * RefDepartment（`backend/app/models/reference_data.py`，portal.db）是全站
 * 唯一真實來源，往後任何模組要用到「公司」「部門」都應該從這裡取得關聯，
 * 不要各自另建一份主檔（背景：合約管理／週期採購／飯店班表／商場班表／
 * 預算原本各自維護一份，互不相通，見 docs/TECH_SPEC.md「重要設計決策」）。
 *
 * 這頁的 UI／API 直接沿用既有 `Contract/Settings.tsx` 的 CompaniesTab／
 * DepartmentsTab（呼叫同一組 `@/api/referenceData` companiesApi/departmentsApi），
 * 只是抽成獨立頁面掛在「系統設定」底下，用新的 `settings_departments_manage`
 * 權限 key，不需要 `contract_admin`。合約設定裡原本的 Tab 刻意保留不動
 * （已在正常使用中，避免影響既有使用者），兩邊管理的是同一份資料。
 *
 * 目前只有週期採購模組接上鏡像同步（見 `cycle_purchase_department_sync.py`）；
 * 飯店班表／商場班表／預算模組尚未整合，是後續階段的工作。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Button, Card, Empty, Form, Input, Modal, Popconfirm, Select, Space, Table, Tabs, Tag, Typography, message,
} from 'antd'
import { EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { companiesApi, departmentsApi } from '@/api/referenceData'
import type { CompanyRecord, DepartmentRecord } from '@/api/referenceData'

const { Title, Text } = Typography

function CompaniesTab() {
  const [rows, setRows] = useState<CompanyRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editRecord, setEditRecord] = useState<CompanyRecord | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await companiesApi.list()).data) }
    catch { message.error('載入公司別失敗') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const openAdd = () => { setEditRecord(null); form.resetFields(); setModalOpen(true) }
  const openEdit = (r: CompanyRecord) => { setEditRecord(r); form.setFieldsValue({ name: r.name }); setModalOpen(true) }

  const handleOk = async () => {
    const { name } = await form.validateFields()
    setSaving(true)
    try {
      if (editRecord) {
        await companiesApi.update(editRecord.id, name)
        message.success('已更新')
      } else {
        await companiesApi.create(name)
        message.success('已新增')
      }
      setModalOpen(false)
      load()
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '操作失敗')
    } finally { setSaving(false) }
  }

  const handleToggle = async (r: CompanyRecord) => {
    try {
      await companiesApi.toggle(r.id)
      message.success(r.is_active ? '已停用' : '已啟用')
      load()
    } catch { message.error('操作失敗') }
  }

  const columns: ColumnsType<CompanyRecord> = [
    { title: '公司名稱', dataIndex: 'name', key: 'name' },
    {
      title: '狀態', dataIndex: 'is_active', key: 'is_active', width: 90,
      render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? '啟用' : '停用'}</Tag>,
    },
    {
      title: '操作', key: 'actions', width: 160,
      render: (_: any, r: CompanyRecord) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>修改</Button>
          <Popconfirm
            title={r.is_active ? '確認停用此公司？停用後不出現於下拉選單。' : '確認啟用此公司？'}
            onConfirm={() => handleToggle(r)} okText="確認" cancelText="取消"
          >
            <Button size="small" danger={r.is_active}>{r.is_active ? '停用' : '啟用'}</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Card>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between' }}>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增公司</Button>
      </div>
      <Table rowKey="id" size="small" columns={columns} dataSource={rows} loading={loading} pagination={false} locale={{ emptyText: <Empty description="尚無公司資料" /> }} />
      <Modal title={editRecord ? '修改公司別' : '新增公司別'} open={modalOpen}
        onOk={handleOk} onCancel={() => setModalOpen(false)} confirmLoading={saving} okText="儲存" cancelText="取消" destroyOnClose>
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="name" label="公司名稱" rules={[{ required: true, message: '請輸入公司名稱' }]}>
            <Input placeholder="例：大直" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

function DepartmentsTab() {
  const [rows, setRows] = useState<DepartmentRecord[]>([])
  const [companies, setCompanies] = useState<CompanyRecord[]>([])
  const [filterCompanyId, setFilterCompanyId] = useState<number | undefined>()
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editRecord, setEditRecord] = useState<DepartmentRecord | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const loadCompanies = useCallback(async () => {
    try { setCompanies((await companiesApi.list()).data) }
    catch { /* ignore */ }
  }, [])

  const load = useCallback(async (cid?: number) => {
    setLoading(true)
    try { setRows((await departmentsApi.list(cid)).data) }
    catch { message.error('載入部門別失敗') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadCompanies(); load() }, [load, loadCompanies])

  const handleFilterChange = (v: number | undefined) => { setFilterCompanyId(v); load(v) }

  const openAdd = () => { setEditRecord(null); form.resetFields(); setModalOpen(true) }
  const openEdit = (r: DepartmentRecord) => {
    setEditRecord(r)
    form.setFieldsValue({ name: r.name, company_id: r.company_id })
    setModalOpen(true)
  }

  const handleOk = async () => {
    const { name, company_id } = await form.validateFields()
    setSaving(true)
    try {
      if (editRecord) {
        await departmentsApi.update(editRecord.id, name, company_id)
        message.success('已更新')
      } else {
        await departmentsApi.create(name, company_id)
        message.success('已新增')
      }
      setModalOpen(false)
      load(filterCompanyId)
    } catch (e: any) {
      message.error(e?.response?.data?.detail ?? '操作失敗')
    } finally { setSaving(false) }
  }

  const handleToggle = async (r: DepartmentRecord) => {
    try {
      await departmentsApi.toggle(r.id)
      message.success(r.is_active ? '已停用' : '已啟用')
      load(filterCompanyId)
    } catch { message.error('操作失敗') }
  }

  const columns: ColumnsType<DepartmentRecord> = [
    { title: '歸屬公司', dataIndex: 'company_name', key: 'company_name', width: 120 },
    { title: '部門名稱', dataIndex: 'name', key: 'name' },
    {
      title: '狀態', dataIndex: 'is_active', key: 'is_active', width: 90,
      render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? '啟用' : '停用'}</Tag>,
    },
    {
      title: '操作', key: 'actions', width: 160,
      render: (_: any, r: DepartmentRecord) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>修改</Button>
          <Popconfirm
            title={r.is_active ? '確認停用此部門？' : '確認啟用此部門？'}
            onConfirm={() => handleToggle(r)} okText="確認" cancelText="取消"
          >
            <Button size="small" danger={r.is_active}>{r.is_active ? '停用' : '啟用'}</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <Card>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
        <Space>
          <Select allowClear placeholder="篩選公司別" style={{ width: 140 }}
            value={filterCompanyId} onChange={handleFilterChange}
            options={companies.map(c => ({ value: c.id, label: c.name }))} />
          <Button icon={<ReloadOutlined />} onClick={() => load(filterCompanyId)} loading={loading}>重整</Button>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openAdd}>新增部門</Button>
      </div>
      <Table rowKey="id" size="small" columns={columns} dataSource={rows} loading={loading} pagination={false} locale={{ emptyText: <Empty description="尚無部門資料" /> }} />
      <Modal title={editRecord ? '修改部門別' : '新增部門別'} open={modalOpen}
        onOk={handleOk} onCancel={() => setModalOpen(false)} confirmLoading={saving} okText="儲存" cancelText="取消" destroyOnClose>
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <Form.Item name="company_id" label="歸屬公司" rules={[{ required: true, message: '請選擇公司' }]}>
            <Select placeholder="請選擇公司" options={companies.map(c => ({ value: c.id, label: c.name }))} />
          </Form.Item>
          <Form.Item name="name" label="部門名稱" rules={[{ required: true, message: '請輸入部門名稱' }]}>
            <Input placeholder="例：資訊部" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

export default function CompanyDepartmentsPage() {
  return (
    <div>
      <Title level={4} style={{ margin: 0, marginBottom: 4 }}>系統設定 — 公司/部門管理</Title>
      <Text type="secondary" style={{ fontSize: 12 }}>
        全站公司/部門關聯的唯一真實來源。目前週期採購模組已接上鏡像同步（每次同步會自動更新公司/部門名稱，
        不會覆蓋週期採購自己維護的部門代碼／承辦人／啟用狀態）；其他模組尚未整合。
      </Text>
      <Card style={{ marginTop: 16 }}>
        <Tabs
          defaultActiveKey="companies"
          items={[
            { key: 'companies', label: '公司別', children: <CompaniesTab /> },
            { key: 'departments', label: '部門別', children: <DepartmentsTab /> },
          ]}
        />
      </Card>
    </div>
  )
}
