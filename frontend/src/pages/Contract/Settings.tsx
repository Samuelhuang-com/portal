/**
 * 合約管理 — 設定頁面
 *
 * 功能：
 *  1. 預算科目管理（新增、查看、編輯、刪除）
 *  2. 通知設定
 *  3. 同步設定
 */
import { useEffect, useState } from 'react'
import {
  Card, Row, Col, Tabs, Form, Input, Select, Button, Switch, Divider,
  message, Typography, Breadcrumb, Space, Table, Tag, Popconfirm,
  Empty, Tooltip, Modal, InputNumber,
} from 'antd'
import { DatePicker } from 'antd'
import {
  SaveOutlined, ReloadOutlined, DeleteOutlined, PlusOutlined,
  AuditOutlined, EditOutlined, BarChartOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import type { BudgetCategoryRecord, BudgetAnalysisRecord } from '@/types/contract'
import {
  fetchBudgetCategories, createBudgetCategory, updateBudgetCategory,
  deleteBudgetCategory, syncContractsFromRagic, fetchBudgetAnalysis,
} from '@/api/contract'

const { Text } = Typography

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState('budget-categories')
  const [budgetCategories, setBudgetCategories] = useState<BudgetCategoryRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  // 新增科目 Modal
  const [addCatOpen, setAddCatOpen] = useState(false)
  const [addCatLoading, setAddCatLoading] = useState(false)
  const [addCatForm] = Form.useForm()

  // 編輯科目 Modal
  const [editCatOpen, setEditCatOpen] = useState(false)
  const [editCatLoading, setEditCatLoading] = useState(false)
  const [editCatRecord, setEditCatRecord] = useState<BudgetCategoryRecord | null>(null)
  const [editCatForm] = Form.useForm()

  // 同步狀態
  const [syncLoading, setSyncLoading] = useState(false)

  // 預算執行率分析
  const [analysisYear, setAnalysisYear] = useState<number>(new Date().getFullYear())
  const [analysisData, setAnalysisData] = useState<BudgetAnalysisRecord[]>([])
  const [analysisLoading, setAnalysisLoading] = useState(false)

  const loadBudgetAnalysis = async (year?: number) => {
    const y = year ?? analysisYear
    setAnalysisLoading(true)
    try {
      const rows = await fetchBudgetAnalysis(y)
      setAnalysisData(rows)
    } catch {
      message.error('無法載入預算執行率資料')
    } finally {
      setAnalysisLoading(false)
    }
  }

  // 加載預算科目
  const loadBudgetCategories = async () => {
    setLoading(true)
    try {
      const response = await fetchBudgetCategories()
      setBudgetCategories(response.items)
    } catch (error) {
      message.error('無法加載預算科目')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadBudgetCategories()
  }, [])

  // ── 新增科目 ────────────────────────────────────────────────────────────────
  const handleAddCategoryOk = async () => {
    try {
      const values = await addCatForm.validateFields()
      setAddCatLoading(true)
      const payload = {
        ...values,
        effective_date: values.effective_date?.format('YYYY-MM-DD'),
        is_enabled: values.is_enabled ?? true,
      }
      await createBudgetCategory(payload)
      message.success('預算科目已新增')
      setAddCatOpen(false)
      loadBudgetCategories()
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.response?.data?.detail ?? err?.message ?? '新增失敗')
    } finally {
      setAddCatLoading(false)
    }
  }

  // ── 編輯科目 ────────────────────────────────────────────────────────────────
  const openEditModal = (record: BudgetCategoryRecord) => {
    setEditCatRecord(record)
    editCatForm.setFieldsValue({
      budget_year: record.budget_year,
      dept: record.dept,
      category_l1: record.category_l1,
      category_l2: record.category_l2,
      accounting_code: record.accounting_code,
      payment_code: record.payment_code,
      maintain_unit: record.maintain_unit,
      is_enabled: record.is_enabled,
    })
    setEditCatOpen(true)
  }

  const handleEditCategoryOk = async () => {
    if (!editCatRecord) return
    try {
      const values = await editCatForm.validateFields()
      setEditCatLoading(true)
      await updateBudgetCategory(editCatRecord.id, values)
      message.success('預算科目已更新')
      setEditCatOpen(false)
      setEditCatRecord(null)
      loadBudgetCategories()
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(err?.response?.data?.detail ?? err?.message ?? '更新失敗')
    } finally {
      setEditCatLoading(false)
    }
  }

  // ── 刪除科目 ────────────────────────────────────────────────────────────────
  const handleDeleteCategory = async (record: BudgetCategoryRecord) => {
    try {
      await deleteBudgetCategory(record.id)
      message.success('預算科目已刪除')
      loadBudgetCategories()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? err?.message ?? '刪除失敗')
    }
  }

  // ── 立即同步 ────────────────────────────────────────────────────────────────
  const handleSync = async () => {
    setSyncLoading(true)
    try {
      const result = await syncContractsFromRagic()
      if (result.errors?.length) {
        message.warning(`同步完成，${result.synced} 筆成功，${result.errors.length} 筆失敗`)
      } else {
        message.success(`同步完成，共 ${result.synced} 筆`)
      }
      loadBudgetCategories()
    } catch (err: any) {
      message.error(err?.response?.data?.detail ?? err?.message ?? '同步失敗')
    } finally {
      setSyncLoading(false)
    }
  }

  // 預算科目表格欄位
  const budgetColumns: ColumnsType<BudgetCategoryRecord> = [
    { title: '預算年度', dataIndex: 'budget_year', key: 'budget_year', width: 100 },
    { title: '部門', dataIndex: 'dept', key: 'dept', width: 150, ellipsis: true },
    { title: '大項', dataIndex: 'category_l1', key: 'category_l1', width: 150, ellipsis: true },
    { title: '細項', dataIndex: 'category_l2', key: 'category_l2', width: 150, ellipsis: true },
    { title: '會計科目', dataIndex: 'accounting_code', key: 'accounting_code', width: 110 },
    {
      title: '狀態',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 90,
      render: (isEnabled) => (
        <Tag color={isEnabled ? 'green' : 'default'}>{isEnabled ? '啟用' : '停用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      fixed: 'right' as const,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="編輯">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEditModal(record)}
            />
          </Tooltip>
          <Tooltip title="刪除">
            <Popconfirm
              title="確認刪除"
              description={`確定要刪除「${record.category_l2}」科目嗎？此操作無法復原。`}
              onConfirm={() => handleDeleteCategory(record)}
              okText="刪除"
              okButtonProps={{ danger: true }}
              cancelText="取消"
            >
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px' }}>
      {/* 麵包屑 */}
      <Breadcrumb style={{ marginBottom: '16px' }}>
        <Breadcrumb.Item>
          <AuditOutlined /> 合約管理
        </Breadcrumb.Item>
        <Breadcrumb.Item>合約設定</Breadcrumb.Item>
      </Breadcrumb>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'budget-categories',
            label: '預算科目管理',
            children: (
              <Card>
                <Row style={{ marginBottom: '16px' }}>
                  <Col>
                    <Space>
                      <Button
                        icon={<ReloadOutlined />}
                        onClick={loadBudgetCategories}
                        loading={loading}
                      >
                        重新載入
                      </Button>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => { setAddCatOpen(true); addCatForm.resetFields() }}
                      >
                        新增科目
                      </Button>
                    </Space>
                  </Col>
                </Row>

                <Table<BudgetCategoryRecord>
                  columns={budgetColumns}
                  dataSource={budgetCategories}
                  loading={loading}
                  pagination={{
                    pageSize: 20,
                    showSizeChanger: true,
                    showTotal: (total) => `共 ${total} 筆`,
                  }}
                  rowKey="id"
                  scroll={{ x: 900 }}
                  locale={{ emptyText: <Empty description="無預算科目資料" /> }}
                />
              </Card>
            ),
          },
          {
            key: 'budget-analysis',
            label: (
              <span><BarChartOutlined /> 預算執行率</span>
            ),
            children: (
              <Card>
                {/* 工具列 */}
                <Row style={{ marginBottom: 16 }} align="middle" gutter={12}>
                  <Col>
                    <Select
                      value={analysisYear}
                      onChange={(v) => { setAnalysisYear(v); loadBudgetAnalysis(v) }}
                      style={{ width: 120 }}
                      options={[2024, 2025, 2026, 2027].map((y) => ({ label: `${y} 年`, value: y }))}
                    />
                  </Col>
                  <Col>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={() => loadBudgetAnalysis()}
                      loading={analysisLoading}
                    >
                      查詢
                    </Button>
                  </Col>
                </Row>

                <Table
                  columns={[
                    {
                      title: '大項',
                      dataIndex: 'category_l1',
                      key: 'category_l1',
                      width: 140,
                      ellipsis: true,
                    },
                    {
                      title: '細項',
                      dataIndex: 'category_l2',
                      key: 'category_l2',
                      width: 180,
                      ellipsis: true,
                    },
                    {
                      title: '會計科目',
                      dataIndex: 'accounting_code',
                      key: 'accounting_code',
                      width: 110,
                    },
                    {
                      title: '合約數',
                      dataIndex: 'contract_count',
                      key: 'contract_count',
                      width: 80,
                      align: 'right' as const,
                    },
                    {
                      title: '請款總額',
                      dataIndex: 'total_claimed',
                      key: 'total_claimed',
                      width: 130,
                      align: 'right' as const,
                      render: (v: number) => `$${v.toLocaleString('zh-TW', { minimumFractionDigits: 0 })}`,
                    },
                    {
                      title: '已付款',
                      dataIndex: 'paid_amount',
                      key: 'paid_amount',
                      width: 130,
                      align: 'right' as const,
                      render: (v: number) => (
                        <Text style={{ color: '#52c41a', fontWeight: v > 0 ? 600 : 400 }}>
                          ${v.toLocaleString('zh-TW', { minimumFractionDigits: 0 })}
                        </Text>
                      ),
                    },
                    {
                      title: '已核准',
                      dataIndex: 'approved_amount',
                      key: 'approved_amount',
                      width: 130,
                      align: 'right' as const,
                      render: (v: number) => (
                        <Text style={{ color: '#1677ff' }}>
                          ${v.toLocaleString('zh-TW', { minimumFractionDigits: 0 })}
                        </Text>
                      ),
                    },
                    {
                      title: '待審核',
                      dataIndex: 'pending_amount',
                      key: 'pending_amount',
                      width: 130,
                      align: 'right' as const,
                      render: (v: number) => (
                        <Text style={{ color: v > 0 ? '#faad14' : undefined }}>
                          ${v.toLocaleString('zh-TW', { minimumFractionDigits: 0 })}
                        </Text>
                      ),
                    },
                  ] as ColumnsType<BudgetAnalysisRecord>}
                  dataSource={analysisData}
                  loading={analysisLoading}
                  rowKey={(r) => `${r.category_l1}__${r.category_l2}__${r.accounting_code}`}
                  pagination={false}
                  scroll={{ x: 1050 }}
                  locale={{ emptyText: <Empty description="尚無資料，請先選擇年度後按「查詢」" /> }}
                  summary={(rows) => {
                    const totalClaimed = rows.reduce((s, r) => s + r.total_claimed, 0)
                    const totalPaid = rows.reduce((s, r) => s + r.paid_amount, 0)
                    const totalApproved = rows.reduce((s, r) => s + r.approved_amount, 0)
                    const totalPending = rows.reduce((s, r) => s + r.pending_amount, 0)
                    const fmt = (v: number) => `$${v.toLocaleString('zh-TW', { minimumFractionDigits: 0 })}`
                    return rows.length > 0 ? (
                      <Table.Summary fixed>
                        <Table.Summary.Row style={{ fontWeight: 700, background: '#fafafa' }}>
                          <Table.Summary.Cell index={0} colSpan={3}>合計</Table.Summary.Cell>
                          <Table.Summary.Cell index={3}>
                            <div style={{ textAlign: 'right' }}>{rows.reduce((s, r) => s + r.contract_count, 0)}</div>
                          </Table.Summary.Cell>
                          <Table.Summary.Cell index={4}>
                            <div style={{ textAlign: 'right' }}>{fmt(totalClaimed)}</div>
                          </Table.Summary.Cell>
                          <Table.Summary.Cell index={5}>
                            <div style={{ textAlign: 'right', color: '#52c41a' }}>{fmt(totalPaid)}</div>
                          </Table.Summary.Cell>
                          <Table.Summary.Cell index={6}>
                            <div style={{ textAlign: 'right', color: '#1677ff' }}>{fmt(totalApproved)}</div>
                          </Table.Summary.Cell>
                          <Table.Summary.Cell index={7}>
                            <div style={{ textAlign: 'right', color: '#faad14' }}>{fmt(totalPending)}</div>
                          </Table.Summary.Cell>
                        </Table.Summary.Row>
                      </Table.Summary>
                    ) : null
                  }}
                />
              </Card>
            ),
          },
          {
            key: 'notification',
            label: '通知設定',
            children: (
              <Card>
                <Form form={form} layout="vertical">
                  <Form.Item
                    label="合約即將到期通知"
                    tooltip="啟用時，系統會在合約到期前通知相關人員"
                  >
                    <Space>
                      <Switch defaultChecked />
                      <Text type="secondary">提前 30 天發送通知</Text>
                    </Space>
                  </Form.Item>

                  <Divider />

                  <Form.Item label="到期提醒收件人">
                    <Input.TextArea
                      placeholder="輸入多個電郵地址，以分號或逗號分隔"
                      rows={3}
                      defaultValue="admin@example.com; manager@example.com"
                    />
                  </Form.Item>

                  <Form.Item label="超支警告閾值">
                    <Input
                      type="number"
                      placeholder="輸入百分比（如 90 表示超支 90% 時警告）"
                      defaultValue={90}
                      suffix="%"
                    />
                  </Form.Item>

                  <Divider />

                  <Form.Item>
                    <Button type="primary" icon={<SaveOutlined />}>
                      儲存設定
                    </Button>
                  </Form.Item>
                </Form>
              </Card>
            ),
          },
          {
            key: 'sync',
            label: '同步設定',
            children: (
              <Card>
                <Form form={form} layout="vertical">
                  <Form.Item label="自動同步啟用">
                    <Space>
                      <Switch defaultChecked />
                      <Text type="secondary">每小時自動從 Ragic 同步資料</Text>
                    </Space>
                  </Form.Item>

                  <Form.Item label="同步間隔">
                    <Select defaultValue="60">
                      <Select.Option value="30">30 分鐘</Select.Option>
                      <Select.Option value="60">1 小時</Select.Option>
                      <Select.Option value="120">2 小時</Select.Option>
                      <Select.Option value="240">4 小時</Select.Option>
                      <Select.Option value="480">8 小時</Select.Option>
                    </Select>
                  </Form.Item>

                  <Form.Item label="同步錯誤重試次數">
                    <Input type="number" placeholder="輸入重試次數" defaultValue={3} />
                  </Form.Item>

                  <Divider />

                  <Form.Item>
                    <Space>
                      <Button type="primary" icon={<SaveOutlined />}>
                        儲存設定
                      </Button>
                      <Button onClick={handleSync} loading={syncLoading}>
                        立即同步
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>
              </Card>
            ),
          },
        ]}
      />

      {/* 編輯預算科目 Modal */}
      <Modal
        title="編輯預算科目"
        open={editCatOpen}
        onOk={handleEditCategoryOk}
        onCancel={() => { setEditCatOpen(false); setEditCatRecord(null) }}
        confirmLoading={editCatLoading}
        okText="確認更新"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        <Form form={editCatForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="budget_year"
                label="預算年度"
                rules={[{ required: true, message: '請輸入預算年度' }]}
              >
                <InputNumber style={{ width: '100%' }} min={2000} max={2100} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dept"
                label="部門"
                rules={[{ required: true, message: '請輸入部門' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category_l1"
                label="大項"
                rules={[{ required: true, message: '請輸入大項' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="category_l2"
                label="細項"
                rules={[{ required: true, message: '請輸入細項' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="accounting_code"
                label="會計科目"
                rules={[{ required: true, message: '請輸入會計科目' }]}
              >
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="payment_code" label="付款科目">
                <Input placeholder="選填" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="maintain_unit"
                label="維護單位"
                rules={[{ required: true, message: '請輸入維護單位' }]}
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="is_enabled" label="啟用狀態" valuePropName="checked">
            <Switch checkedChildren="啟用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 新增預算科目 Modal */}
      <Modal
        title="新增預算科目"
        open={addCatOpen}
        onOk={handleAddCategoryOk}
        onCancel={() => setAddCatOpen(false)}
        confirmLoading={addCatLoading}
        okText="確認新增"
        cancelText="取消"
        width={600}
        destroyOnClose
      >
        <Form form={addCatForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="budget_year"
                label="預算年度"
                rules={[{ required: true, message: '請輸入預算年度' }]}
              >
                <InputNumber style={{ width: '100%' }} min={2000} max={2100} placeholder="例：2026" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="dept"
                label="部門"
                rules={[{ required: true, message: '請輸入部門' }]}
              >
                <Input placeholder="請輸入部門名稱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category_l1"
                label="大項"
                rules={[{ required: true, message: '請輸入大項' }]}
              >
                <Input placeholder="例：固定費用" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="category_l2"
                label="細項"
                rules={[{ required: true, message: '請輸入細項' }]}
              >
                <Input placeholder="例：水電費" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="accounting_code"
                label="會計科目"
                rules={[{ required: true, message: '請輸入會計科目' }]}
              >
                <Input placeholder="例：6150001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="payment_code" label="付款科目">
                <Input placeholder="選填" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="maintain_unit"
                label="維護單位"
                rules={[{ required: true, message: '請輸入維護單位' }]}
              >
                <Input placeholder="例：財務部" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="effective_date" label="生效日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="is_enabled" label="啟用狀態" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="啟用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
