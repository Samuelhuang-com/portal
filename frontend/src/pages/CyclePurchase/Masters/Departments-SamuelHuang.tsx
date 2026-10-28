/**
 * 週期採購 — 部門主檔維護
 *
 * 2026-09-22（Samuel）：部門全部改為本地自建，停用「週期採購部門」同步
 * （main.py／sync_tool.py／同步設定頁都已拿掉），本頁移除「來源」欄／篩選與
 * 「連結主檔部門」。下方 2026-08-17／09-01 的同步相關說明為歷史紀錄。
 * 2026-07-10 決策（已於 2026-08-17 反轉，見下方）：週期採購自建獨立部門
 * 主檔，不與 Budget／Contract 模組的部門主檔關聯。
 *
 * 2026-07-11 新增「承辦人」：owner_user_id 軟關聯到 portal.db 的 users.id，
 * 供 Dashboard「待辦提醒」判斷登入者屬於哪個週採部門用（見
 * cycle_purchase_request_service.get_dashboard_todos）。承辦人清單沿用既有
 * GET /users/options（任何登入者可呼叫，回傳啟用中使用者），不需要新增後端。
 *
 * 2026-08-17（反轉部分決策，與 Samuel 確認跨模組整合範圍後）：公司/部門
 * 關聯改為全站唯一真實來源「系統設定 → 公司/部門管理」（reference_data.py
 * Company/RefDepartment），這裡的部門主檔改成鏡像同步（見
 * cycle_purchase_department_sync.py）。
 *
 * 2026-09-01（Samuel 裁示）：**公司別（company）改回自行輸入**——公司對
 * 「公司名稱」並不統一，週採要用的公司字串不一定等於主檔的 Company.name。
 * 因此：
 *   - company：週採自維護（同步只在新增鏡像列時帶初始值，之後不碰），
 *     鏡像列也可編輯。
 *   - dept_name：仍由同步維護，鏡像列唯讀（後端 update_department 也會剔除，
 *     前端唯讀只是提示，不是唯一防線）。
 *   - 名稱自動比對只剩「部門名稱在週採未連結列中唯一命中」；重名部門
 *     不自動連結，用本頁編輯 Modal 的「連結主檔部門」下拉手動連結。
 *     **連上主檔，「同部門成員可編輯請購單」的權限鏈才會生效。**
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import {
  createCpDepartment, getCpDepartments, updateCpDepartment,
} from '@/api/cyclePurchase'
import { usersApi, type UserOptionItem } from '@/api/users'
import { companiesApi, type CompanyOption } from '@/api/referenceData'
import type { CpDepartment } from '@/types/cyclePurchase'

const { Title } = Typography


export default function CpDepartmentsPage() {
  const [depts, setDepts] = useState<CpDepartment[]>([])
  const [userOptions, setUserOptions] = useState<UserOptionItem[]>([])
  // 2026-09-22：公司別改用「系統設定 → 公司/部門管理」的公司下拉（只列啟用中）
  const [companyOptions, setCompanyOptions] = useState<CompanyOption[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpDepartment | null>(null)
  const [form] = Form.useForm()
  // 2026-09-22：篩選列（前端篩選，清單本來就一次載入全部）＋ 筆數
  const [fKeyword, setFKeyword] = useState('')
  const [fCompany, setFCompany] = useState<string | undefined>()
  const [fOwner, setFOwner] = useState<'set' | 'unset' | undefined>()
  const [fActive, setFActive] = useState<'active' | 'inactive' | undefined>()

  const companyFilterOptions = useMemo(
    () => Array.from(new Set(depts.map((d) => d.company))).sort().map((c) => ({ label: c, value: c })),
    [depts],
  )
  const filteredDepts = useMemo(() => {
    const kw = fKeyword.trim().toLowerCase()
    return depts.filter((d) => {
      if (fCompany && d.company !== fCompany) return false
      if (fOwner === 'set' && !d.owner_user_id) return false
      if (fOwner === 'unset' && d.owner_user_id) return false
      if (fActive === 'active' && !d.is_active) return false
      if (fActive === 'inactive' && d.is_active) return false
      if (kw && !`${d.dept_code} ${d.dept_name} ${d.owner_name ?? ''}`.toLowerCase().includes(kw)) return false
      return true
    })
  }, [depts, fKeyword, fCompany, fOwner, fActive])
  const hasFilter = !!(fKeyword.trim() || fCompany || fOwner || fActive)
  const resetFilters = () => {
    setFKeyword(''); setFCompany(undefined); setFOwner(undefined); setFActive(undefined)
  }

  const load = () => {
    setLoading(true)
    // 2026-09-22：部門改全部本地自建、停用同步，不再載入「連結主檔部門」選項
    usersApi.options().then(r => setUserOptions(r.data)).catch(() => {})
    getCpDepartments()
      .then((r) => setDepts(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    companiesApi.options().then(r => setCompanyOptions(r.data)).catch(() => {})
  }, [])

  const toggleActive = async (d: CpDepartment) => {
    try {
      await updateCpDepartment(d.id, { is_active: !d.is_active })
      message.success(d.is_active ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true })
    setModalOpen(true)
  }

  const openEdit = (d: CpDepartment) => {
    setEditing(d)
    form.setFieldsValue(d)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateCpDepartment(editing.id, values)
        message.success('更新成功')
      } else {
        await createCpDepartment(values)
        message.success('新增成功')
      }
      setModalOpen(false)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail) message.error(detail)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 部門主檔</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增部門</Button>
      </div>

      <Card>
        <Space wrap style={{ marginBottom: 12 }}>
          <Input.Search
            placeholder="搜尋部門代碼／名稱／承辦人"
            allowClear
            style={{ width: 240 }}
            value={fKeyword}
            onChange={(e) => setFKeyword(e.target.value)}
          />
          <Select
            placeholder="公司別"
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 150 }}
            value={fCompany}
            onChange={setFCompany}
            options={companyFilterOptions}
          />
          <Select
            placeholder="承辦人"
            allowClear
            style={{ width: 120 }}
            value={fOwner}
            onChange={setFOwner}
            options={[{ label: '已設定', value: 'set' }, { label: '未設定', value: 'unset' }]}
          />
          <Select
            placeholder="狀態"
            allowClear
            style={{ width: 110 }}
            value={fActive}
            onChange={setFActive}
            options={[{ label: '啟用', value: 'active' }, { label: '停用', value: 'inactive' }]}
          />
          {hasFilter && <Button onClick={resetFilters}>清除篩選</Button>}
          <Typography.Text type="secondary">
            {hasFilter
              ? <>篩選結果 <Typography.Text strong>{filteredDepts.length}</Typography.Text> 筆／全部 {depts.length} 筆</>
              : <>共 <Typography.Text strong>{depts.length}</Typography.Text> 筆</>}
            {'（啟用 '}{filteredDepts.filter((d) => d.is_active).length}{'、停用 '}
            {filteredDepts.filter((d) => !d.is_active).length}{'）'}
          </Typography.Text>
        </Space>
        <Table
          dataSource={filteredDepts}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '公司別', dataIndex: 'company', width: 140 },
            { title: '部門代碼', dataIndex: 'dept_code', width: 100 },
            { title: '部門名稱', dataIndex: 'dept_name' },
            {
              title: '承辦人',
              dataIndex: 'owner_name',
              width: 120,
              render: (v?: string | null) => v || <Tag>未設定</Tag>,
            },
            {
              title: '狀態',
              dataIndex: 'is_active',
              width: 80,
              render: (v: boolean) => (v ? <Tag color="green">啟用</Tag> : <Tag color="default">停用</Tag>),
            },
            {
              title: '操作',
              key: 'actions',
              width: 160,
              render: (_: unknown, r: CpDepartment) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active ? '確定停用此部門？' : '確定啟用此部門？'}
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

      <Modal
        title={editing ? '編輯部門' : '新增部門'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="company" label="公司別" rules={[{ required: true, message: '請選擇公司別' }]}
            extra="選項來自「系統設定 → 公司/部門管理」的公司別（停用的不列出）">
            <Select
              showSearch
              placeholder="選擇公司別"
              optionFilterProp="label"
              options={companyOptions.map(o => ({ value: o.value, label: o.label }))}
            />
          </Form.Item>
          <Form.Item name="dept_code" label="部門代碼" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dept_name" label="部門名稱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="owner_user_id"
            label="承辦人"
            extra="供 Dashboard「待辦提醒」判斷這個部門還沒填的請購單要提醒誰"
          >
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="選擇承辦人（選填）"
              options={userOptions.map((u) => ({ label: u.label, value: u.user_id }))}
            />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
