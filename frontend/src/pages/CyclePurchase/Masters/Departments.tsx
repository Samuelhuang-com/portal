/**
 * 週期採購 — 部門主檔維護
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
import { useEffect, useState } from 'react'
import {
  Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined } from '@ant-design/icons'
import {
  createCpDepartment, getCpDepartments, updateCpDepartment,
  getCpDepartmentLinkOptions, linkCpDepartment, type CpDepartmentLinkOption,
} from '@/api/cyclePurchase'
import { usersApi, type UserOptionItem } from '@/api/users'
import type { CpDepartment } from '@/types/cyclePurchase'

const { Title } = Typography

export default function CpDepartmentsPage() {
  const [depts, setDepts] = useState<CpDepartment[]>([])
  const [userOptions, setUserOptions] = useState<UserOptionItem[]>([])
  const [linkOptions, setLinkOptions] = useState<CpDepartmentLinkOption[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpDepartment | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    Promise.all([getCpDepartments(), usersApi.options(), getCpDepartmentLinkOptions()])
      .then(([dRes, uRes, lRes]) => {
        setDepts(dRes.data)
        setUserOptions(uRes.data)
        setLinkOptions(lRes.data)
      })
      // link-options 需要 cycle_purchase_admin；沒有權限時整組 Promise.all 會
      // 失敗，所以個別容錯：清單照載，連結下拉留空（編輯 Modal 也只有 admin 開得了）
      .catch(() => {
        getCpDepartments().then(r => setDepts(r.data)).catch(() => {})
        usersApi.options().then(r => setUserOptions(r.data)).catch(() => {})
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

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
    form.setFieldsValue({ ...d, source_department_id: d.source_department_id ?? null })
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const { source_department_id, ...rest } = values
      if (editing) {
        await updateCpDepartment(editing.id, rest)
        // 連結有變才打 link 端點（含解除：清空下拉 → null）
        const before = editing.source_department_id ?? null
        const after = source_department_id ?? null
        if (before !== after) {
          await linkCpDepartment(editing.id, after)
        }
        message.success('更新成功')
      } else {
        await createCpDepartment(rest)
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
        <Table
          dataSource={depts}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          columns={[
            { title: '公司別', dataIndex: 'company', width: 140 },
            { title: '部門代碼', dataIndex: 'dept_code', width: 100 },
            { title: '部門名稱', dataIndex: 'dept_name' },
            {
              title: '來源',
              dataIndex: 'source_department_id',
              width: 90,
              render: (v?: string | null) =>
                v ? <Tag color="blue">同步</Tag> : <Tag>本地自建</Tag>,
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
          {editing?.source_department_id && (
            <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 12 }}>
              這筆部門已連結「系統設定 → 公司/部門管理」的主檔部門：部門名稱由同步維護（要改名請到該頁改）；
              公司別為週採自行輸入（2026-09-01 起），與主檔的公司名稱不必相同。
            </Typography.Paragraph>
          )}
          <Form.Item name="company" label="公司別" rules={[{ required: true }]}
            extra="週採自行輸入，不必與公司/部門管理的公司名稱一致">
            <Input placeholder="如：日曜天地／春大直" />
          </Form.Item>
          <Form.Item name="dept_code" label="部門代碼" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="dept_name" label="部門名稱" rules={[{ required: true }]}>
            <Input disabled={!!editing?.source_department_id} />
          </Form.Item>
          {/*
            連結主檔部門（2026-09-01）：company 改自行輸入後，同步的自動比對
            只剩「部門名稱唯一命中」，重名部門靠這裡手動連結。
            連上主檔，「同部門成員可編輯請購單」權限鏈才會生效。
            只在編輯時顯示（新增的本地部門，下次同步若名稱唯一會自動連結）。
          */}
          {editing && (
            <Form.Item
              name="source_department_id"
              label="連結主檔部門"
              extra="連結後「同部門成員可編輯請購單」才會生效；清空＝解除連結（退回僅承辦人可編）"
            >
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                placeholder="選擇公司/部門管理的部門（選填）"
                options={linkOptions.map(o => ({
                  value: o.source_department_id,
                  label: `${o.company}／${o.dept_name}`,
                  // 已被其他週採部門連結的不能再選（自己這筆除外）
                  disabled: !!o.linked_to && o.source_department_id !== (editing?.source_department_id ?? ''),
                }))}
                optionRender={(opt) => {
                  const o = linkOptions.find(x => x.source_department_id === opt.value)
                  return (
                    <span>
                      {opt.label}
                      {o?.linked_to && o.source_department_id !== (editing?.source_department_id ?? '') && (
                        <span style={{ fontSize: 11, color: '#94a3b8' }}>（已連結：{o.linked_to}）</span>
                      )}
                    </span>
                  )
                }}
              />
            </Form.Item>
          )}
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
