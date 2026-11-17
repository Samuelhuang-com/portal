/**
 * 週期採購 — 部門主檔維護
 *
 * 2026-11-17（Samuel 裁示）：週採部門**一律從「系統設定 → 公司/部門管理」挑選**，
 * 禁止本地自建（新增時選「公司／部門」，公司別與部門名稱由主檔帶入、唯讀；
 * 只能維護部門代碼、承辦人、啟用）。主檔改名時後端會把已連結部門的名稱同步更新。
 * 下方 2026-07～09 的歷史說明（本地自建／同步停用／自行輸入公司別）已被本裁示取代。
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
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, LinkOutlined } from '@ant-design/icons'
import {
  createCpDepartment, getCpDepartments, getCpDepartmentLinkOptions, linkCpDepartment, updateCpDepartment,
  type CpDepartmentLinkOption,
} from '@/api/cyclePurchase'
import { usersApi, type UserOptionItem } from '@/api/users'
import type { CpDepartment } from '@/types/cyclePurchase'

const { Title } = Typography


export default function CpDepartmentsPage() {
  const [depts, setDepts] = useState<CpDepartment[]>([])
  const [userOptions, setUserOptions] = useState<UserOptionItem[]>([])
  // 2026-11-17：新增時從主檔挑「公司／部門」（只列尚未被週採部門連結者）
  const [linkOptions, setLinkOptions] = useState<CpDepartmentLinkOption[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpDepartment | null>(null)
  const [form] = Form.useForm()
  // 2026-11-17：未連結部門的「連結主檔」
  const [linking, setLinking] = useState<CpDepartment | null>(null)
  const [linkValue, setLinkValue] = useState<string | undefined>()
  const [linkSaving, setLinkSaving] = useState(false)
  // 2026-09-22：篩選列（前端篩選，清單本來就一次載入全部）＋ 筆數
  const [fKeyword, setFKeyword] = useState('')
  const [fCompany, setFCompany] = useState<string | undefined>()
  const [fOwner, setFOwner] = useState<'set' | 'unset' | undefined>()
  const [fActive, setFActive] = useState<'active' | 'inactive' | undefined>()
  const [fLink, setFLink] = useState<'linked' | 'unlinked' | undefined>()

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
      if (fLink === 'linked' && !d.source_department_id) return false
      if (fLink === 'unlinked' && d.source_department_id) return false
      if (kw && !`${d.dept_code} ${d.dept_name} ${d.owner_name ?? ''}`.toLowerCase().includes(kw)) return false
      return true
    })
  }, [depts, fKeyword, fCompany, fOwner, fActive, fLink])
  const hasFilter = !!(fKeyword.trim() || fCompany || fOwner || fActive || fLink)
  const resetFilters = () => {
    setFKeyword(''); setFCompany(undefined); setFOwner(undefined); setFActive(undefined); setFLink(undefined)
  }
  const unlinkedCount = useMemo(() => depts.filter((d) => !d.source_department_id).length, [depts])

  const load = () => {
    setLoading(true)
    getCpDepartmentLinkOptions().then((r) => setLinkOptions(r.data)).catch(() => {})
    usersApi.options().then(r => setUserOptions(r.data)).catch(() => {})
    getCpDepartments()
      .then((r) => setDepts(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
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

  const openLink = (d: CpDepartment) => {
    setLinking(d)
    // 預設帶出同名的主檔部門（若剛好只有一個）
    const same = linkOptions.filter((o) => !o.linked_to && o.dept_name.trim() === d.dept_name.trim())
    setLinkValue(same.length === 1 ? same[0].source_department_id : undefined)
  }

  const handleLink = async () => {
    if (!linking || !linkValue) return
    setLinkSaving(true)
    try {
      await linkCpDepartment(linking.id, linkValue)
      message.success('已連結主檔')
      setLinking(null)
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '連結失敗')
    } finally {
      setLinkSaving(false)
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
        // 公司別／部門名稱由主檔決定，不送
        await updateCpDepartment(editing.id, {
          dept_code: values.dept_code,
          owner_user_id: values.owner_user_id ?? null,
          is_active: values.is_active,
        })
        message.success('更新成功')
      } else {
        await createCpDepartment({
          source_department_id: values.source_department_id,
          dept_code: values.dept_code,
          owner_user_id: values.owner_user_id ?? null,
          is_active: values.is_active,
        })
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
          <Select
            placeholder="主檔連結"
            allowClear
            style={{ width: 120 }}
            value={fLink}
            onChange={setFLink}
            options={[{ label: '已連結', value: 'linked' }, { label: '未連結', value: 'unlinked' }]}
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
        {unlinkedCount > 0 && (
          <Typography.Text type="danger" style={{ display: 'block', marginBottom: 8 }}>
            有 {unlinkedCount} 筆部門尚未連結主檔，部門成員無法編輯其請購單；請先到「公司/部門管理」建立對應部門，再由管理員連結。
          </Typography.Text>
        )}
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
              title: '主檔連結',
              dataIndex: 'source_department_id',
              width: 90,
              render: (v?: string | null) => (v ? <Tag color="blue">已連結</Tag> : <Tag color="red">未連結</Tag>),
            },
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
              width: 260,
              render: (_: unknown, r: CpDepartment) => (
                <Space>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  {!r.source_department_id && (
                    <Button size="small" type="primary" ghost icon={<LinkOutlined />} onClick={() => openLink(r)}>
                      連結主檔
                    </Button>
                  )}
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
        title={linking ? `連結主檔：${linking.company}／${linking.dept_name}` : '連結主檔'}
        open={!!linking}
        onOk={handleLink}
        onCancel={() => setLinking(null)}
        okText="連結"
        cancelText="取消"
        okButtonProps={{ disabled: !linkValue, loading: linkSaving }}
      >
        <div style={{ marginTop: 16 }}>
          <Select
            style={{ width: '100%' }}
            showSearch
            allowClear
            placeholder="選擇「公司/部門管理」的部門"
            optionFilterProp="label"
            value={linkValue}
            onChange={setLinkValue}
            options={linkOptions
              .filter((o) => !o.linked_to)
              .map((o) => ({ value: o.source_department_id, label: `${o.company}／${o.dept_name}` }))}
          />
          <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            連結後部門名稱會改成主檔名稱（部門代碼、承辦人與既有單據不變）。找不到請先到「公司/部門管理」新增。
          </Typography.Text>
        </div>
      </Modal>

      <Modal
        title={editing ? '編輯部門' : '新增部門'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {editing ? (
            <Form.Item label="公司／部門" extra="由「系統設定 → 公司/部門管理」決定，這裡不能修改">
              <Input disabled value={`${editing.company}／${editing.dept_name}`} />
            </Form.Item>
          ) : (
            <Form.Item
              name="source_department_id"
              label="公司／部門"
              rules={[{ required: true, message: '請選擇公司／部門' }]}
              extra="選項來自「系統設定 → 公司/部門管理」（已建立過的部門不列出）。找不到請先到該頁新增部門"
            >
              <Select
                showSearch
                placeholder="選擇公司／部門"
                optionFilterProp="label"
                options={linkOptions
                  .filter((o) => !o.linked_to)
                  .map((o) => ({ value: o.source_department_id, label: `${o.company}／${o.dept_name}` }))}
              />
            </Form.Item>
          )}
          <Form.Item name="dept_code" label="部門代碼" rules={[{ required: true }]}>
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
