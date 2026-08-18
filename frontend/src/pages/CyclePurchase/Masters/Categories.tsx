/**
 * 週期採購 — 類別主檔維護（2026-08-18 新增）
 *
 * 三層編碼（大分類英文 + 中分類 2 碼 + 細分類 2 碼 + 流水 3 碼），
 * 設計理由見 backend/app/models/cycle_purchase_category.py 檔頭。
 *
 * 畫面上要特別交代的兩件事：
 *  1. 「歸屬部門」留空 ＝ 不限部門（全公司共用）。春大直的文具用品（G 系列）
 *     就是這種：來源 Excel 分頁本來就叫「文具用品-所有部門需求」。
 *  2. 「類別字串」是與既有料號 `items.category` 對照用的鍵，不會因為補了
 *     細分類名稱就自動改寫。改這欄等於改對照關係，會讓料號數掉到 0，
 *     所以表單上有明確警告，並用「料號數」欄讓人立刻看得出來對不對得上。
 */
import { useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Form, Input, InputNumber, Modal, Popconfirm, Select,
  Space, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  PlusOutlined, EditOutlined, StopOutlined, CheckCircleOutlined, NumberOutlined,
} from '@ant-design/icons'
import {
  createCpCategory, getCpCategories, getCpCategoryNextCode, getCpDepartments,
  updateCpCategory,
} from '@/api/cyclePurchase'
import type { CpCategory, CpDepartment } from '@/types/cyclePurchase'

const { Title, Text } = Typography

export default function CpCategoriesPage() {
  const [categories, setCategories] = useState<CpCategory[]>([])
  const [depts, setDepts] = useState<CpDepartment[]>([])
  const [loading, setLoading] = useState(false)
  const [company, setCompany] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CpCategory | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    Promise.all([getCpCategories({ company, q: keyword || undefined }), getCpDepartments()])
      .then(([cRes, dRes]) => {
        setCategories(cRes.data)
        setDepts(dRes.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [company])

  const companies = useMemo(
    () => Array.from(new Set(depts.map((d) => d.company).filter(Boolean))),
    [depts],
  )

  // 「歸屬部門」下拉只列出**表單上當下選的公司**的部門——跨公司的部門選下去
  // 會產生一個永遠篩不到料號的類別，這正是 2026-08-17 週期設定踩過的坑。
  // 用 useWatch 盯著表單值，而不是外層的篩選條件：使用者在 Modal 裡改了公司，
  // 部門選項要跟著換，否則等於還是能選到別家公司的部門。
  const formCompany = Form.useWatch('company', form)
  const deptOptions = useMemo(
    () => depts
      .filter((d) => d.is_active && (!formCompany || d.company === formCompany))
      .map((d) => ({ label: `${d.company}／${d.dept_name}`, value: d.id })),
    [depts, formCompany],
  )

  const toggleActive = async (c: CpCategory) => {
    try {
      await updateCpCategory(c.id, { is_active: !c.is_active })
      message.success(c.is_active ? '已停用' : '已啟用')
      load()
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '操作失敗')
    }
  }

  const showNextCode = async (c: CpCategory) => {
    try {
      const { data } = await getCpCategoryNextCode(c.id)
      Modal.info({
        title: `${c.category_name} — 下一個可用料號`,
        width: 520,
        content: (
          <div style={{ marginTop: 12 }}>
            <p>
              前綴：<Text code>{data.code_prefix}</Text>　→　下一個料號：
              <Text code strong>{data.next_code}</Text>
            </p>
            <p style={{ marginBottom: 4 }}>已使用流水碼（{data.used_serials.length} 個）：</p>
            <Text type="secondary">{data.used_serials.join('、') || '（尚無）'}</Text>
            {data.gap_serials.length > 0 && (
              <Alert
                type="warning"
                showIcon
                style={{ marginTop: 12 }}
                message={`中間有跳號：${data.gap_serials.join('、')}`}
                description="跳號多半是當初刻意保留給某個品項的，這裡不會自動拿來當下一個號。要補號請自行指定。"
              />
            )}
          </div>
        ),
      })
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '查詢失敗')
    }
  }

  const openCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true, serial_width: 3, company })
    setModalOpen(true)
  }

  const openEdit = (c: CpCategory) => {
    setEditing(c)
    form.resetFields()
    form.setFieldsValue(c)
    setModalOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editing) {
        await updateCpCategory(editing.id, values)
        message.success('更新成功')
      } else {
        await createCpCategory(values)
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 類別主檔</Title>
        <Space>
          <Select
            allowClear
            placeholder="公司別"
            style={{ width: 160 }}
            value={company}
            onChange={setCompany}
            options={companies.map((c) => ({ label: c, value: c }))}
          />
          <Input.Search
            allowClear
            placeholder="搜尋類別／分類名稱"
            style={{ width: 220 }}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={load}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增類別</Button>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="料號編碼原則：大分類英文 + 中分類 2 碼 + 細分類 2 碼 + 流水 3 碼（如 E0101001）"
        description="「歸屬部門」留空代表不限部門、全公司共用（如文具用品）。「料號數」是目前類別字串對得上的啟用中料號筆數，顯示 0 表示這個類別還沒有料號在用。"
      />

      <Card>
        <Table
          dataSource={categories}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 50, showSizeChanger: true }}
          columns={[
            { title: '公司別', dataIndex: 'company', width: 110 },
            {
              title: '料號前綴',
              dataIndex: 'code_prefix',
              width: 100,
              render: (v: string) => <Text code>{v}</Text>,
            },
            {
              title: '大分類',
              width: 120,
              render: (_: unknown, r: CpCategory) => `${r.major_code}　${r.major_name}`,
            },
            {
              title: '中分類',
              width: 160,
              render: (_: unknown, r: CpCategory) => `${r.mid_code}　${r.mid_name}`,
            },
            {
              title: '細分類',
              width: 160,
              render: (_: unknown, r: CpCategory) =>
                r.sub_name ? `${r.sub_code}　${r.sub_name}` : (
                  <Tooltip title="來源 Excel 的類別字串只到中分類，細分類尚未命名">
                    <span>{r.sub_code}　<Tag color="orange">待命名</Tag></span>
                  </Tooltip>
                ),
            },
            { title: '類別字串', dataIndex: 'category_name' },
            {
              title: '歸屬部門',
              dataIndex: 'department_name',
              width: 120,
              render: (v?: string | null) => v || <Tag color="blue">不限部門</Tag>,
            },
            {
              title: '料號數',
              dataIndex: 'item_count',
              width: 80,
              align: 'right' as const,
              render: (v: number) => (v > 0 ? v : <Tag color="orange">0</Tag>),
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
              width: 230,
              render: (_: unknown, r: CpCategory) => (
                <Space>
                  <Button size="small" icon={<NumberOutlined />} onClick={() => showNextCode(r)}>下一碼</Button>
                  <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)}>編輯</Button>
                  <Popconfirm
                    title={r.is_active ? '確定停用此類別？' : '確定啟用此類別？'}
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
        title={editing ? '編輯類別' : '新增類別'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        okText="儲存"
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="company" label="公司別" rules={[{ required: true }]}>
            <Select
              showSearch
              placeholder="如：春大直／日曜天地"
              options={companies.map((c) => ({ label: c, value: c }))}
            />
          </Form.Item>
          <Form.Item
            name="department_id"
            label="歸屬部門"
            extra="留空 ＝ 不限部門（全公司共用，如文具用品）"
          >
            <Select allowClear showSearch optionFilterProp="label" options={deptOptions} />
          </Form.Item>

          <Space.Compact block>
            <Form.Item name="major_code" label="大分類代碼" rules={[{ required: true }]} style={{ width: '30%' }}>
              <Input placeholder="E／C／G／S" maxLength={5} />
            </Form.Item>
            <Form.Item name="major_name" label="大分類名稱" rules={[{ required: true }]} style={{ width: '70%' }}>
              <Input placeholder="工程／清潔／文具／營業用品" />
            </Form.Item>
          </Space.Compact>

          <Space.Compact block>
            <Form.Item name="mid_code" label="中分類代碼" rules={[{ required: true }]} style={{ width: '30%' }}>
              <Input placeholder="2 碼，如 01" maxLength={2} />
            </Form.Item>
            <Form.Item name="mid_name" label="中分類名稱" rules={[{ required: true }]} style={{ width: '70%' }}>
              <Input placeholder="如：空調備品" />
            </Form.Item>
          </Space.Compact>

          <Space.Compact block>
            <Form.Item name="sub_code" label="細分類代碼" rules={[{ required: true }]} style={{ width: '30%' }}>
              <Input placeholder="2 碼，如 01" maxLength={2} />
            </Form.Item>
            <Form.Item name="sub_name" label="細分類名稱" style={{ width: '70%' }}>
              <Input placeholder="如：濾網（來源未命名可留空）" />
            </Form.Item>
          </Space.Compact>

          <Form.Item
            name="category_name"
            label="類別字串"
            rules={[{ required: true }]}
            extra="⚠️ 這是與現有料號 items.category 對照用的鍵，改了會讓「料號數」掉到 0，非必要不要動"
          >
            <Input placeholder="如：空調備品-濾網" />
          </Form.Item>
          <Form.Item name="serial_width" label="流水碼位數" rules={[{ required: true }]}>
            <InputNumber min={1} max={6} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="is_active" label="是否啟用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
