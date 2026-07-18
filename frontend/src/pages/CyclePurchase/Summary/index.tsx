/**
 * 週期採購 — 彙整單／匯總請購單（第三期，2026-07-11 新增；2026-07-16 改版）
 * 路由：/cycle-purchase/summary
 *
 * 只彙總已關閉（is_closed=True）的請購明細，還沒關閉的不算進來（2026-07-17
 * 起請購單流程拿掉送出／核准，「關閉」取代「已核准」成為彙整的前提條件，
 * 見後端 services/cycle_purchase_request_service.py 開頭第三次調整說明）。
 * 冪等：重複「產生彙整」不會覆寫已存在的彙整列，只會新增這次才第一次
 * 出現的（公司＋料號＋部門）組合。
 *
 * 2026-07-16 改版重點（見後端 models/cycle_purchase_summary.py 開頭說明）：
 *   - 彙整粒度從「公司＋料號」改成「公司＋料號＋部門」，可以呈現部門別。
 *     2026-07-16 之前產生的舊列沒有部門別（顯示「歷史資料，未拆分部門」）。
 *   - 新增「匯總請購單（部門別＋小計）」卡片：依料號分組，展開底下各部門
 *     的調整量與小計，比照 0715 會議討論的設計方向。
 *   - 新增「拋轉 Ragic」按鈕：把整個週期＋期別＋公司範圍推送到 Ragic 產生
 *     一張新的「匯總請購單」（目前為 stub，Ragic 端表單尚未建立，見後端
 *     cycle_purchase_ragic_push.py 開頭說明）。
 *
 * 頁面分三段：
 *   1. 上方「依供應商分組」— 給「轉採購單」用，只列 draft 狀態的列，
 *      依公司＋供應商分組統計；沒有供應商的組別不能轉單（灰掉，附提示）。
 *   2. 中間「匯總請購單（部門別＋小計）」— 依料號分組，子表列部門別＋小計，
 *      並提供「拋轉 Ragic」入口。
 *   3. 下方彙整列明細表 — 可依公司／供應商／狀態篩選；draft 狀態的列可以
 *      點「調整」改調整量／調整原因（調整量≠需求量時後端會要求填原因）。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Button, Card, Descriptions, Form, Input, InputNumber, Modal,
  Select, Space, Table, Tag, Typography, message,
} from 'antd'
import {
  CloudUploadOutlined, ExclamationCircleOutlined, ShoppingCartOutlined, SyncOutlined,
} from '@ant-design/icons'
import {
  convertToPo, generateSummaryFromRequests, getCycles, getDepartmentBreakdown, getEligibleRequests,
  getRequests, getSummary, getVendorGroups, pushSummaryToRagic, updateSummaryItem,
} from '@/api/cyclePurchase'
import type {
  CpCycle, CpDepartmentBreakdown, CpEligibleRequest, CpSummary, CpVendorGroup,
} from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  converted: { color: 'green',   label: '已轉採購單' },
}

function currentYearMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

// 2026-07-16 改版：「產生彙整」不再讓使用者手動輸入期別字串（會有打字不一致
// 的問題），改成從固定的「最近 N 個月」清單裡選——月份本身只是用來篩選
// 「哪個月的請購單」，彙整單真正的期別標籤由後端從勾選的請購單本身的
// period_label 讀出來（見 api/cyclePurchase.ts、後端 service 開頭第三次
// 調整說明；2026-07-17 之前是從 approved_at 換算，現在直接用 period_label）。
function recentMonthOptions(count = 6) {
  const now = new Date()
  const opts: string[] = []
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    opts.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  return opts
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
  const [breakdown, setBreakdown] = useState<CpDepartmentBreakdown[]>([])
  const [loading, setLoading] = useState(false)
  const [pushing, setPushing] = useState(false)

  const [generateModal, setGenerateModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genCycleId, setGenCycleId] = useState<number | undefined>(undefined)
  const [genCompany, setGenCompany] = useState<string | undefined>(undefined)
  const [genMonth, setGenMonth] = useState<string>('')
  const [genCompanyOptions, setGenCompanyOptions] = useState<string[]>([])
  const [eligibleRequests, setEligibleRequests] = useState<CpEligibleRequest[]>([])
  const [loadingEligible, setLoadingEligible] = useState(false)
  const [selectedRequestIds, setSelectedRequestIds] = useState<number[]>([])

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
    if (!cycleId || !periodLabel.trim()) { setRows([]); setVendorGroups([]); setBreakdown([]); return }
    setLoading(true)
    Promise.all([
      getSummary({ cycle_id: cycleId, period_label: periodLabel.trim(), company }),
      getVendorGroups({ cycle_id: cycleId, period_label: periodLabel.trim(), company }),
      getDepartmentBreakdown({ cycle_id: cycleId, period_label: periodLabel.trim(), company }),
    ])
      .then(([sRes, vRes, bRes]) => {
        setRows(sRes.data)
        setVendorGroups(vRes.data)
        setBreakdown(bRes.data)
      })
      .catch((err) => message.error(errMsg(err, '載入失敗')))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cycleId, periodLabel, company])

  const companyOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.company))),
    [rows],
  )

  const handlePushToRagic = () => {
    if (!cycleId || !periodLabel.trim() || !company) {
      message.warning('請先選擇週期／期別，並用「依公司篩選」指定單一公司後再拋轉')
      return
    }
    Modal.confirm({
      title: '拋轉到 Ragic「匯總請購單」',
      content: (
        <div>
          <p>將把「{periodLabel.trim()}／{company}」範圍內的彙整列組成一份匯總請購單，推送到 Ragic。</p>
          <Alert
            type="warning"
            showIcon
            message="Ragic 端「匯總請購單」表單目前尚未建立，這是預留串接的 stub，會回傳模擬結果，不是真正寫入 Ragic 的記錄。"
          />
        </div>
      ),
      okText: '確定拋轉',
      cancelText: '取消',
      onOk: async () => {
        setPushing(true)
        try {
          const res = await pushSummaryToRagic({ cycle_id: cycleId, period_label: periodLabel.trim(), company })
          if (res.data.is_stub) {
            message.warning(`（Stub）${res.data.message}，批次號 ${res.data.batch_no}`)
          } else {
            message.success(`已拋轉：${res.data.message}（${res.data.batch_no}）`)
          }
          load()
        } catch (err: any) {
          message.error(errMsg(err, '拋轉失敗'))
        } finally {
          setPushing(false)
        }
      },
    })
  }

  const openGenerate = () => {
    setGenCycleId(cycleId)
    setGenCompany(company)
    setGenMonth(currentYearMonth())
    setEligibleRequests([])
    setSelectedRequestIds([])
    setGenerateModal(true)
  }

  // 依選定的週期，抓這個週期底下出現過的公司，供「產生彙整」視窗的公司下拉選用
  // （跟頁面上方「依公司篩選」是分開的兩個狀態，開視窗當下先預帶頁面上的值）。
  useEffect(() => {
    if (!generateModal || !genCycleId) { setGenCompanyOptions([]); return }
    getRequests({ cycle_id: genCycleId })
      .then((r) => setGenCompanyOptions(Array.from(new Set(r.data.map((x) => x.company))).sort()))
      .catch(() => {})
  }, [generateModal, genCycleId])

  // 週期＋公司＋月份都選好後，載入這個範圍內「已關閉、尚未被彙整過」的請購單，
  // 預設全選，使用者可以手動取消勾選不想這次納入的單。
  useEffect(() => {
    if (!generateModal || !genCycleId || !genCompany || !genMonth) {
      setEligibleRequests([])
      setSelectedRequestIds([])
      return
    }
    setLoadingEligible(true)
    getEligibleRequests({ cycle_id: genCycleId, company: genCompany, year_month: genMonth })
      .then((r) => {
        setEligibleRequests(r.data)
        setSelectedRequestIds(r.data.map((x) => x.id))
      })
      .catch((err) => message.error(errMsg(err, '載入可彙整清單失敗')))
      .finally(() => setLoadingEligible(false))
  }, [generateModal, genCycleId, genCompany, genMonth])

  const handleGenerate = async () => {
    if (!selectedRequestIds.length) {
      message.warning('請至少勾選一張請購單')
      return
    }
    setGenerating(true)
    try {
      const res = await generateSummaryFromRequests({ request_ids: selectedRequestIds })
      message.success(`已產生（或累加）${res.data.length} 筆彙整列`)
      setGenerateModal(false)
      if (genCycleId) setCycleId(genCycleId)
      if (genCompany) setCompany(genCompany)
      // 彙整單的期別是系統從勾選的請購單本身的 period_label 讀出來的，
      // 就等於這次篩選用的月份，直接用它切到對應畫面。
      setPeriodLabel(genMonth)
    } catch (err: any) {
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
        <Title level={4} style={{ margin: 0 }}>週期採購 — 彙整單／匯總請購單</Title>
        <Space>
          {canBuy && (
            <Button
              icon={<CloudUploadOutlined />}
              loading={pushing}
              onClick={handlePushToRagic}
              disabled={!cycleId || !periodLabel.trim() || !company}
            >
              拋轉 Ragic
            </Button>
          )}
          {canBuy && (
            <Button icon={<SyncOutlined />} onClick={openGenerate}>產生彙整</Button>
          )}
        </Space>
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
              <Table<CpVendorGroup>
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

          <Card
            title="匯總請購單（部門別＋小計）"
            style={{ marginBottom: 16 }}
            loading={loading}
            extra={<Text type="secondary">依料號分組，展開各部門的調整量與小計；拋轉 Ragic 會以此範圍為準</Text>}
          >
            {breakdown.length === 0 ? (
              <Text type="secondary">這期還沒有彙整列可以呈現</Text>
            ) : (
              <Table<CpDepartmentBreakdown>
                dataSource={breakdown}
                rowKey={(g) => `${g.company}|${g.item_id}`}
                size="small"
                pagination={false}
                expandable={{
                  defaultExpandAllRows: false,
                  expandedRowRender: (g) => (
                    <Table
                      dataSource={g.departments}
                      rowKey="summary_id"
                      size="small"
                      pagination={false}
                      columns={[
                        {
                          title: '部門別',
                          dataIndex: 'department_name',
                          render: (v?: string | null) => v || <Text type="secondary">（歷史資料，未拆分部門）</Text>,
                        },
                        { title: '需求量', dataIndex: 'demand_qty', width: 90, align: 'right' as const },
                        { title: '調整量', dataIndex: 'adjusted_qty', width: 90, align: 'right' as const },
                        {
                          title: '部門小計',
                          dataIndex: 'subtotal',
                          width: 120,
                          align: 'right' as const,
                          render: (v: number) => Number(v).toLocaleString(),
                        },
                        {
                          title: '狀態',
                          dataIndex: 'status',
                          width: 100,
                          render: (v: string) => <Tag color={STATUS_TAG[v]?.color}>{STATUS_TAG[v]?.label || v}</Tag>,
                        },
                      ]}
                    />
                  ),
                }}
                columns={[
                  { title: '公司', dataIndex: 'company', width: 100 },
                  { title: '料號', dataIndex: 'item_code', width: 110 },
                  { title: '品名', dataIndex: 'item_name' },
                  { title: '單位', dataIndex: 'unit', width: 70 },
                  {
                    title: '廠商',
                    dataIndex: 'vendor_name',
                    width: 140,
                    render: (v: string | null | undefined, g: CpDepartmentBreakdown) =>
                      g.has_missing_vendor
                        ? <Tag icon={<ExclamationCircleOutlined />} color="warning">無供應商</Tag>
                        : v,
                  },
                  { title: '部門數', key: 'dept_count', width: 80, align: 'right' as const, render: (_: unknown, g: CpDepartmentBreakdown) => g.departments.length },
                  { title: '總調整量', dataIndex: 'total_adjusted_qty', width: 100, align: 'right' as const },
                  {
                    title: '總金額',
                    dataIndex: 'total_amount',
                    width: 130,
                    align: 'right' as const,
                    render: (v: number) => Number(v).toLocaleString(),
                  },
                ]}
              />
            )}
          </Card>

          <Card title="彙整列明細">
            <Table<CpSummary>
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
                  title: '部門別',
                  dataIndex: 'department_name',
                  width: 120,
                  render: (v?: string | null) => v || <Text type="secondary">（歷史資料）</Text>,
                },
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
                  title: 'Ragic 拋轉',
                  dataIndex: 'ragic_pushed',
                  width: 110,
                  render: (v: boolean, r: CpSummary) =>
                    v ? (
                      <Tag color="blue" title={r.ragic_push_batch_no || undefined}>
                        已拋轉{r.ragic_record_id?.startsWith('STUB-') ? '（stub）' : ''}
                      </Tag>
                    ) : (
                      <Text type="secondary">—</Text>
                    ),
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
        okText={`產生（已選 ${selectedRequestIds.length} 筆）`}
        cancelText="取消"
        confirmLoading={generating}
        width={720}
        okButtonProps={{ disabled: !selectedRequestIds.length }}
      >
        <Space wrap style={{ marginBottom: 12 }}>
          <Select
            placeholder="選擇週期"
            style={{ width: 200 }}
            value={genCycleId}
            onChange={(v) => { setGenCycleId(v); setGenCompany(undefined) }}
            showSearch
            optionFilterProp="label"
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            placeholder="選擇公司"
            style={{ width: 160 }}
            value={genCompany}
            onChange={setGenCompany}
            disabled={!genCycleId}
            options={genCompanyOptions.map((c) => ({ label: c, value: c }))}
          />
          <Select
            placeholder="選擇期別"
            style={{ width: 160 }}
            value={genMonth || undefined}
            onChange={(v) => setGenMonth(v || '')}
            options={recentMonthOptions().map((m) => ({ label: m, value: m }))}
          />
        </Space>

        {(!genCycleId || !genCompany || !genMonth) ? (
          <Alert type="info" showIcon message="請先選擇週期／公司／期別，會列出這個範圍內已關閉、尚未被彙整過的請購單" />
        ) : (
          <Table<CpEligibleRequest>
            dataSource={eligibleRequests}
            rowKey="id"
            size="small"
            loading={loadingEligible}
            pagination={false}
            scroll={{ y: 320 }}
            locale={{ emptyText: '這個範圍內沒有已關閉、尚未被彙整過的請購單' }}
            rowSelection={{
              selectedRowKeys: selectedRequestIds,
              onChange: (keys) => setSelectedRequestIds(keys as number[]),
            }}
            columns={[
              { title: '請購單號', dataIndex: 'request_no', width: 140 },
              { title: '部門', dataIndex: 'department_name', width: 110, render: (v?: string | null) => v || '—' },
              { title: '填寫人', dataIndex: 'submitted_by_name', width: 100, render: (v?: string | null) => v || '—' },
              { title: '關閉人', dataIndex: 'closed_by_name', width: 100, render: (v?: string | null) => v || '—' },
              {
                title: '關閉時間',
                dataIndex: 'closed_at',
                width: 150,
                render: (v?: string | null) => (v ? new Date(v).toLocaleString() : '—'),
              },
              {
                title: '請購總額',
                dataIndex: 'total_amount',
                width: 110,
                align: 'right' as const,
                render: (v: number) => Number(v).toLocaleString(),
              },
            ]}
          />
        )}

        <div style={{ color: '#888', fontSize: 12, marginTop: 12 }}>
          只列出已關閉（is_closed）且還沒被彙整過的請購單；勾選後才會被納入這次彙整，
          彙整過的請購單就不會再出現在這個清單裡，不用擔心重複彙整。期別標籤由系統依勾選的
          請購單本身的期別自動判斷，不用手動輸入。
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
              <Descriptions.Item label="需求量（各已關閉請購單加總）">{adjustRow.demand_qty}</Descriptions.Item>
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
