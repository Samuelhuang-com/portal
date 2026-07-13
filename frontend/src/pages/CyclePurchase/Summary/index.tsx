/**
 * 週期採購 — 彙整單（第三期，2026-07-11 新增）
 * 路由：/cycle-purchase/summary
 *
 * 只彙總已核准（approved）的請購明細，草稿/已送出/已退回都不算進來。
 * 冪等：重複「產生彙整」不會覆寫已存在的彙整列，只會新增這次才第一次
 * 出現的（公司＋料號）組合。
 *
 * 頁面分兩段：
 *   1. 上方「依供應商分組」— 給「轉採購單」用，只列 draft 狀態的列，
 *      依公司＋供應商分組統計；沒有供應商的組別不能轉單（灰掉，附提示）。
 *   2. 下方彙整列明細表 — 可依公司／供應商／狀態篩選；draft 狀態的列可以
 *      點「調整」改調整量／調整原因（調整量≠需求量時後端會要求填原因）。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Button, Card, Descriptions, Form, Input, InputNumber, Modal,
  Select, Space, Table, Tag, Typography, message,
} from 'antd'
import { ExclamationCircleOutlined, ShoppingCartOutlined, SyncOutlined } from '@ant-design/icons'
import {
  convertToPo, generateSummary, getCycles, getRequests, getSummary, getVendorGroups, updateSummaryItem,
} from '@/api/cyclePurchase'
import type { CpCycle, CpSummary, CpVendorGroup } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  converted: { color: 'green',   label: '已轉採購單' },
}

function defaultPeriodLabel() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpSummaryPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canBuy = hasPermission('cycle_purchase_buyer')

  const [cycles, setCycles] = useState<CpCycle[]>([])
  const [cycleId, setCycleId] = useState<number | undefined>(undefined)
  const [periodLabel, setPeriodLabel] = useState<string>('')
  const [periodOptions, setPeriodOptions] = useState<string[]>([])
  const [company, setCompany] = useState<string | undefined>(undefined)

  const [rows, setRows] = useState<CpSummary[]>([])
  const [vendorGroups, setVendorGroups] = useState<CpVendorGroup[]>([])
  const [loading, setLoading] = useState(false)

  const [generateModal, setGenerateModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generateForm] = Form.useForm()

  const [adjustRow, setAdjustRow] = useState<CpSummary | null>(null)
  const [adjustQty, setAdjustQty] = useState<number>(0)
  const [adjustReason, setAdjustReason] = useState('')
  const [adjusting, setAdjusting] = useState(false)

  const [converting, setConverting] = useState<string | null>(null) // key = company|vendor_id

  useEffect(() => {
    getCycles().then((r) => setCycles(r.data)).catch(() => message.error('載入週期設定失敗'))
  }, [])

  // 依選定週期，抓一下這個週期底下已知的期別標籤（來自請購單），方便下拉選，
  // 但仍允許手動輸入新的期別（例如這期還沒產生過彙整）。
  useEffect(() => {
    if (!cycleId) { setPeriodOptions([]); return }
    getRequests({ cycle_id: cycleId })
      .then((r) => setPeriodOptions(Array.from(new Set(r.data.map((x) => x.period_label))).sort().reverse()))
      .catch(() => {})
  }, [cycleId])

  const load = () => {
    if (!cycleId || !periodLabel.trim()) { setRows([]); setVendorGroups([]); return }
    setLoading(true)
    Promise.all([
      getSummary({ cycle_id: cycleId, period_label: periodLabel.trim(), company }),
      getVendorGroups({ cycle_id: cycleId, period_label: periodLabel.trim(), company }),
    ])
      .then(([sRes, vRes]) => {
        setRows(sRes.data)
        setVendorGroups(vRes.data)
      })
      .catch((err) => message.error(errMsg(err, '載入失敗')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cycleId, periodLabel, company])

  const companyOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.company))),
    [rows],
  )

  const openGenerate = () => {
    generateForm.resetFields()
    generateForm.setFieldsValue({
      cycle_id: cycleId,
      period_label: periodLabel || defaultPeriodLabel(),
    })
    setGenerateModal(true)
  }

  const handleGenerate = async () => {
    try {
      const values = await generateForm.validateFields()
      setGenerating(true)
      const res = await generateSummary({ cycle_id: values.cycle_id, period_label: values.period_label })
      message.success(`已產生（或確認既有）${res.data.length} 筆彙整列`)
      setGenerateModal(false)
      setCycleId(values.cycle_id)
      setPeriodLabel(values.period_label)
    } catch (err: any) {
      if (err?.errorFields) return
      message.error(errMsg(err, '產生彙整失敗'))
    } finally {
      setGenerating(false)
    }
  }

  const openAdjust = (row: CpSummary) => {
    setAdjustRow(row)
    setAdjustQty(row.adjusted_qty)
    setAdjustReason(row.adjust_reason || '')
  }

  const handleAdjustSave = async () => {
    if (!adjustRow) return
    if (adjustQty !== adjustRow.demand_qty && !adjustReason.trim()) {
      message.warning('調整量與需求量不同，必須填寫調整原因')
      return
    }
    setAdjusting(true)
    try {
      await updateSummaryItem(adjustRow.id, { adjusted_qty: adjustQty, adjust_reason: adjustReason.trim() || null })
      message.success('已更新')
      setAdjustRow(null)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '更新失敗'))
    } finally {
      setAdjusting(false)
    }
  }

  const handleConvert = async (group: CpVendorGroup) => {
    if (!cycleId || !periodLabel.trim() || group.vendor_id == null) return
    const key = `${group.company}|${group.vendor_id}`
    setConverting(key)
    try {
      const res = await convertToPo({
        cycle_id: cycleId,
        period_label: periodLabel.trim(),
        company: group.company,
        vendor_id: group.vendor_id,
      })
      message.success(`已產生採購單 ${res.data.po_no}`)
      load()
      navigate(`/cycle-purchase/pos/${res.data.id}`)
    } catch (err: any) {
      message.error(errMsg(err, '轉採購單失敗'))
    } finally {
      setConverting(null)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 彙整單</Title>
        {canBuy && (
          <Button icon={<SyncOutlined />} onClick={openGenerate}>產生彙整</Button>
        )}
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder="選擇週期"
            style={{ width: 200 }}
            value={cycleId}
            onChange={(v) => { setCycleId(v); setPeriodLabel('') }}
            showSearch
            optionFilterProp="label"
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            placeholder="選擇或輸入期別"
            style={{ width: 160 }}
            value={periodLabel || undefined}
            onChange={(v) => setPeriodLabel(v || '')}
            showSearch
            allowClear
            disabled={!cycleId}
            options={periodOptions.map((p) => ({ label: p, value: p }))}
            onSearch={(v) => {
              // 允許輸入尚未出現在下拉選項裡的新期別
              if (v && !periodOptions.includes(v)) setPeriodOptions((prev) => [v, ...prev])
            }}
          />
          <Select
            allowClear
            placeholder="依公司篩選"
            style={{ width: 140 }}
            value={company}
            onChange={setCompany}
            options={companyOptions.map((c) => ({ label: c, value: c }))}
          />
        </Space>
      </Card>

      {(!cycleId || !periodLabel.trim()) ? (
        <Alert type="info" showIcon message="請先選擇週期與期別" />
      ) : (
        <>
          <Card title="依供應商分組（轉採購單）" style={{ marginBottom: 16 }} loading={loading}>
            {vendorGroups.length === 0 ? (
              <Text type="secondary">目前沒有草稿狀態的彙整列可以轉單（可能都已轉單，或這期還沒產生彙整）</Text>
            ) : (
              <Table
                dataSource={vendorGroups}
                rowKey={(g) => `${g.company}|${g.vendor_id ?? 'none'}`}
                size="small"
                pagination={false}
                columns={[
                  { title: '公司', dataIndex: 'company', width: 120 },
                  {
                    title: '供應商',
                    key: 'vendor',
                    render: (_: unknown, g: CpVendorGroup) =>
                      g.has_missing_vendor
                        ? <Tag icon={<ExclamationCircleOutlined />} color="warning">無供應商，需先到料號對照表補上</Tag>
                        : g.vendor_name,
                  },
                  { title: '料號筆數', dataIndex: 'item_count', width: 100, align: 'right' as const },
                  {
                    title: '金額（依目前調整量）',
                    dataIndex: 'total_amount',
                    width: 160,
                    align: 'right' as const,
                    render: (v: number) => Number(v).toLocaleString(),
                  },
                  {
                    title: '操作',
                    key: 'actions',
                    width: 140,
                    render: (_: unknown, g: CpVendorGroup) =>
                      canBuy ? (
                        <Button
                          size="small"
                          type="primary"
                          icon={<ShoppingCartOutlined />}
                          disabled={g.has_missing_vendor}
                          loading={converting === `${g.company}|${g.vendor_id}`}
                          onClick={() => handleConvert(g)}
                        >
                          轉採購單
                        </Button>
                      ) : null,
                  },
                ]}
              />
            )}
          </Card>

          <Card title="彙整列明細">
            <Table
              dataSource={rows}
              rowKey="id"
              loading={loading}
              size="small"
              pagination={{ pageSize: 20 }}
              columns={[
                { title: '公司', dataIndex: 'company', width: 100 },
                { title: '料號', dataIndex: 'item_code', width: 110 },
                { title: '品名', dataIndex: 'item_name' },
                { title: '單位', dataIndex: 'unit', width: 70 },
                {
                  title: '供應商',
                  dataIndex: 'vendor_name',
                  width: 140,
                  render: (v?: string | null) => v || <Text type="warning">（無）</Text>,
                },
                {
                  title: '單價',
                  dataIndex: 'unit_price',
                  width: 90,
                  align: 'right' as const,
                  render: (v?: number | null) => (v == null ? '—' : Number(v).toLocaleString()),
                },
                { title: '需求量', dataIndex: 'demand_qty', width: 90, align: 'right' as const },
                {
                  title: '調整量',
                  dataIndex: 'adjusted_qty',
                  width: 90,
                  align: 'right' as const,
                  render: (v: number, r: CpSummary) => (
                    <span>
                      {v}
                      {v !== r.demand_qty && <Tag color="orange" style={{ marginLeft: 4 }}>已調整</Tag>}
                    </span>
                  ),
                },
                {
                  title: '調整原因',
                  dataIndex: 'adjust_reason',
                  width: 160,
                  ellipsis: true,
                  render: (v?: string | null) => v || '—',
                },
                {
                  title: '狀態',
                  dataIndex: 'status',
                  width: 100,
                  render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
                },
                {
                  title: '採購單號',
                  dataIndex: 'po_no',
                  width: 140,
                  render: (v?: string | null, r?: CpSummary) =>
                    v && r?.po_id ? (
                      <a onClick={() => navigate(`/cycle-purchase/pos/${r.po_id}`)}>{v}</a>
                    ) : '—',
                },
                {
                  title: '操作',
                  key: 'actions',
                  width: 90,
                  render: (_: unknown, r: CpSummary) =>
                    canBuy && r.status === 'draft' ? (
                      <Button size="small" onClick={() => openAdjust(r)}>調整</Button>
                    ) : null,
                },
              ]}
            />
          </Card>
        </>
      )}

      <Modal
        title="產生彙整"
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
            extra="只會彙總這個週期＋期別下已核准（approved）的請購明細"
          >
            <Input placeholder="例如 2026-07" />
          </Form.Item>
        </Form>
        <div style={{ color: '#888', fontSize: 12 }}>
          冪等：已經產生過的（公司＋料號）組合不會被覆寫，只會新增這次才第一次出現的組合。
        </div>
      </Modal>

      <Modal
        title={adjustRow ? `調整彙整列 — ${adjustRow.item_code} ${adjustRow.item_name}` : '調整'}
        open={!!adjustRow}
        onOk={handleAdjustSave}
        onCancel={() => setAdjustRow(null)}
        okText="儲存"
        cancelText="取消"
        confirmLoading={adjusting}
      >
        {adjustRow && (
          <>
            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="需求量（各已核准請購單加總）">{adjustRow.demand_qty}</Descriptions.Item>
            </Descriptions>
            <Form layout="vertical">
              <Form.Item label="調整量">
                <InputNumber min={0} value={adjustQty} onChange={(v) => setAdjustQty(v ?? 0)} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                label="調整原因"
                required={adjustQty !== adjustRow.demand_qty}
                extra="調整量與需求量不同時必填（例如供應商缺貨、有最小訂購量限制）"
              >
                <TextArea
                  rows={3}
                  value={adjustReason}
                  onChange={(e) => setAdjustReason(e.target.value)}
                  placeholder="請說明調整原因"
                />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>
    </div>
  )
}
