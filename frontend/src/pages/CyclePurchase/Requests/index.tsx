/**
 * 週期採購 — 請購單清單
 *
 * 2026-07-11（與 Samuel 討論後拿掉「批次」）：
 * 請購單不再依批次自動產生，改成在這頁按「產生本期請購單」，依週期設定
 * 的 applicable_scope 一次幫所有適用公司的啟用中部門建立空白單。這個動作
 * 隨時可觸發、同一週期＋期別（如「2026-07」）冪等，不會重複建立，也沒有
 * 固定時間窗限制 —— 週採的範圍界線是「料號主檔」，不是時間窗。
 *
 * 「新增請購單」是備用手動路徑：正常情況請購單由「產生本期請購單」一次
 * 建好，這個按鈕給某個部門臨時需要補建一張的情境用，走後端原本就有的
 * POST /requests 備用路徑，同一週期＋期別＋部門只能有一張。
 */
import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import { EditOutlined, EyeOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { createRequest, generateRequestsForPeriod, getCpDepartments, getCycles, getRequests } from '@/api/cyclePurchase'
import type { CpCycle, CpDepartment, CpRequest } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title } = Typography

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  submitted: { color: 'blue',    label: '已送出' },
  approved:  { color: 'green',   label: '已核准' },
  rejected:  { color: 'red',     label: '已退回' },
}

// 預設期別標籤：本月，格式「YYYY-MM」，使用者仍可自行修改（如需要用「上半月/下半月」等其他標籤）。
function defaultPeriodLabel() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpRequestsPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('cycle_purchase_request')
  const canCreate = hasPermission('cycle_purchase_buyer')

  const [rows, setRows] = useState<CpRequest[]>([])
  const [cycles, setCycles] = useState<CpCycle[]>([])
  const [departments, setDepartments] = useState<CpDepartment[]>([])
  const [cycleId, setCycleId] = useState<number | undefined>(undefined)
  const [periodLabel, setPeriodLabel] = useState<string | undefined>(undefined)
  const [status, setStatus] = useState<string | undefined>(undefined)
  const [loading, setLoading] = useState(false)

  const [createModal, setCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form] = Form.useForm()

  const [generateModal, setGenerateModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generateForm] = Form.useForm()

  const load = () => {
    setLoading(true)
    Promise.all([
      getRequests({ cycle_id: cycleId, period_label: periodLabel, status }),
      getCycles(),
      getCpDepartments({ is_active: true }),
    ])
      .then(([rRes, cRes, dRes]) => {
        setRows(rRes.data)
        setCycles(cRes.data)
        setDepartments(dRes.data)
      })
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cycleId, periodLabel, status])

  const openCreate = () => {
    form.resetFields()
    setCreateModal(true)
  }

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      setCreating(true)
      const created = await createRequest({
        cycle_id: values.cycle_id,
        department_id: values.department_id,
        period_label: values.period_label,
      })
      message.success('已建立請購單')
      setCreateModal(false)
      load()
      navigate(`/cycle-purchase/requests/${created.data.id}`)
    } catch (err: any) {
      if (err?.errorFields) return // antd 表單驗證錯誤，不是 API 錯誤
      message.error(errMsg(err, '建立失敗'))
    } finally {
      setCreating(false)
    }
  }

  const openGenerate = () => {
    generateForm.resetFields()
    generateForm.setFieldsValue({ period_label: defaultPeriodLabel() })
    setGenerateModal(true)
  }

  const handleGenerate = async () => {
    try {
      const values = await generateForm.validateFields()
      setGenerating(true)
      const res = await generateRequestsForPeriod({
        cycle_id: values.cycle_id,
        period_label: values.period_label,
      })
      message.success(`已產生（或確認既有）${res.data.length} 張本期請購單`)
      setGenerateModal(false)
      setCycleId(values.cycle_id)
      setPeriodLabel(values.period_label)
      load()
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(errMsg(err, '產生失敗'))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 請購單</Title>
        <Space>
          {canCreate && (
            <Button icon={<ThunderboltOutlined />} onClick={openGenerate}>產生本期請購單</Button>
          )}
          {canCreate && (
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增請購單</Button>
          )}
        </Space>
      </div>

      <Card>
        <Space style={{ marginBottom: 12 }}>
          <Select
            allowClear
            placeholder="依週期篩選"
            style={{ width: 200 }}
            value={cycleId}
            onChange={setCycleId}
            showSearch
            optionFilterProp="label"
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            allowClear
            placeholder="依期別篩選"
            style={{ width: 140 }}
            value={periodLabel}
            onChange={setPeriodLabel}
            showSearch
            options={Array.from(new Set(rows.map((r) => r.period_label))).map((p) => ({ label: p, value: p }))}
          />
          <Select
            allowClear
            placeholder="依狀態篩選"
            style={{ width: 140 }}
            value={status}
            onChange={setStatus}
            options={[
              { label: '草稿', value: 'draft' },
              { label: '已送出', value: 'submitted' },
              { label: '已核准', value: 'approved' },
              { label: '已退回', value: 'rejected' },
            ]}
          />
        </Space>

        <Table
          dataSource={rows}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
          columns={[
            { title: '請購單號', dataIndex: 'request_no', width: 160 },
            { title: '週期', dataIndex: 'cycle_name', width: 140 },
            { title: '期別', dataIndex: 'period_label', width: 100 },
            { title: '公司', dataIndex: 'company', width: 110 },
            { title: '部門', dataIndex: 'department_name', width: 140 },
            {
              title: '請購總金額',
              dataIndex: 'total_amount',
              width: 120,
              align: 'right',
              render: (v: number) => v?.toLocaleString(undefined, { minimumFractionDigits: 0 }),
            },
            {
              title: '狀態',
              dataIndex: 'status',
              width: 90,
              render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
            },
            { title: '送出人', dataIndex: 'submitted_by_name', width: 100, render: (v?: string | null) => v || '—' },
            { title: '簽核人', dataIndex: 'approved_by_name', width: 100, render: (v?: string | null) => v || '—' },
            {
              title: '操作',
              key: 'actions',
              width: 100,
              render: (_: unknown, r: CpRequest) => (
                <Button
                  size="small"
                  icon={canEdit && (r.status === 'draft' || r.status === 'rejected') ? <EditOutlined /> : <EyeOutlined />}
                  onClick={() => navigate(`/cycle-purchase/requests/${r.id}`)}
                >
                  {canEdit && (r.status === 'draft' || r.status === 'rejected') ? '填寫' : '檢視'}
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="產生本期請購單"
        open={generateModal}
        onOk={handleGenerate}
        onCancel={() => setGenerateModal(false)}
        okText="產生"
        cancelText="取消"
        confirmLoading={generating}
      >
        <Form form={generateForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="cycle_id" label="週期" rules={[{ required: true, message: '請選擇週期' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="選擇週期"
              options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
            />
          </Form.Item>
          <Form.Item
            name="period_label"
            label="期別標籤"
            rules={[{ required: true, message: '請輸入期別標籤' }]}
            extra="如「2026-07」；同一週期＋期別已經產生過的部門不會重複建立"
          >
            <Input placeholder="例如 2026-07" />
          </Form.Item>
        </Form>
        <div style={{ color: '#888', fontSize: 12 }}>
          會依週期設定的「適用公司」，為每個啟用中部門建立一張空白請購單（已存在的不會重複建立）。
        </div>
      </Modal>

      <Modal
        title="新增請購單（手動備用路徑）"
        open={createModal}
        onOk={handleCreate}
        onCancel={() => setCreateModal(false)}
        okText="建立"
        cancelText="取消"
        confirmLoading={creating}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="cycle_id" label="週期" rules={[{ required: true, message: '請選擇週期' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="選擇週期"
              options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
            />
          </Form.Item>
          <Form.Item name="period_label" label="期別標籤" rules={[{ required: true, message: '請輸入期別標籤' }]}>
            <Input placeholder="例如 2026-07" />
          </Form.Item>
          <Form.Item name="department_id" label="部門" rules={[{ required: true, message: '請選擇部門' }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="選擇部門"
              options={departments.map((d) => ({ label: `${d.company} - ${d.dept_name}`, value: d.id }))}
            />
          </Form.Item>
        </Form>
        <div style={{ color: '#888', fontSize: 12 }}>
          同一週期＋期別＋部門只能有一張請購單；若「產生本期請購單」已經建過，這裡會顯示錯誤訊息。
        </div>
      </Modal>
    </div>
  )
}
