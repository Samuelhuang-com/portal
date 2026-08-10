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
 * 2026-08-09 新增「退回請購單」：已經彙整過的請購單，若這一期要取消或發現
 * 某張單不該納入，可以一張一張退回未彙整狀態（退回原因必填）。退回後後端會
 * 依「剩下仍為已彙整」的請購單**重算**受影響的草稿彙整列需求量（不是反向
 * 扣減，因為彙整列沒有記錄量是哪幾張單貢獻的）。已轉採購單／已拋轉 Ragic／
 * 請購單已重新開啟這三種情況會被擋下，清單上會直接顯示擋下原因。
 * 見後端 services/cycle_purchase_summary_service.py 開頭「第四次調整」說明。
 *
 * 2026-08-09 拋轉 Ragic 兩項調整（Ragic 端表單開始建置前先補起來）：
 *   - **擋重複拋轉**：同一個週期＋期別＋公司拋轉過就不能再推（後端回 422），
 *     按鈕會 disable 並在 tooltip 說明原因。改版前按兩次會在 Ragic 產生兩張
 *     內容不同的同期單據，Ragic 端無從判斷哪張才算數。
 *   - **新增「取消拋轉」**：清掉該範圍的拋轉標記，可以重新拋轉。同時解掉一個
 *     死結——`ragic_pushed=True` 是「退回請購單」的擋下條件之一，改版前一旦
 *     按了拋轉，那一期的請購單就再也退不回去了（而拋轉目前還只是 stub，
 *     等於被一個假動作鎖死）。
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
  Select, Space, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  CloudUploadOutlined, ExclamationCircleOutlined, LockOutlined, RollbackOutlined,
  ShoppingCartOutlined, SyncOutlined, UndoOutlined,
} from '@ant-design/icons'
import {
  cancelRagicPush, closeRequests, convertToPo, generateSummaryFromRequests, getCycles,
  getDepartmentBreakdown, getEligibleRequests, getRequests, getSummarizedRequests, getSummary,
  getVendorGroups, pushSummaryToRagic, unsummarizeRequest, updateSummaryItem,
} from '@/api/cyclePurchase'
import type {
  CpCycle, CpDepartmentBreakdown, CpEligibleRequest, CpSummarizedRequest, CpSummary, CpVendorGroup,
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
  // 「關閉並納入」會呼叫 POST /requests/close，那支要的是 cycle_purchase_close，
  // 與彙整用的 cycle_purchase_buyer 是不同權限——買家不一定關得了單，所以要分開判斷。
  const canClose = hasPermission('cycle_purchase_close')

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
  // 2026-08-09：取消拋轉。已拋轉的範圍不能重推（後端會擋），要重推得先取消；
  // 取消同時也解開「已拋轉就不能退回請購單」的限制。
  const [cancelPushModal, setCancelPushModal] = useState(false)
  const [cancelPushReason, setCancelPushReason] = useState('')
  const [cancellingPush, setCancellingPush] = useState(false)

  const [generateModal, setGenerateModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [genCycleId, setGenCycleId] = useState<number | undefined>(undefined)
  const [genCompany, setGenCompany] = useState<string | undefined>(undefined)
  const [genMonth, setGenMonth] = useState<string>('')
  const [genCompanyOptions, setGenCompanyOptions] = useState<string[]>([])
  const [eligibleRequests, setEligibleRequests] = useState<CpEligibleRequest[]>([])
  const [loadingEligible, setLoadingEligible] = useState(false)
  const [selectedRequestIds, setSelectedRequestIds] = useState<number[]>([])
  const [closingRequestId, setClosingRequestId] = useState<number | null>(null)

  // 2026-08-09：退回請購單。與「產生彙整」是鏡像操作，所以視窗裡的
  // 週期／公司／期別三個選擇器沿用同一套狀態命名習慣，但獨立一組。
  const [unsumModal, setUnsumModal] = useState(false)
  const [unsumCycleId, setUnsumCycleId] = useState<number | undefined>(undefined)
  const [unsumCompany, setUnsumCompany] = useState<string | undefined>(undefined)
  const [unsumMonth, setUnsumMonth] = useState<string>('')
  const [unsumCompanyOptions, setUnsumCompanyOptions] = useState<string[]>([])
  const [summarizedRequests, setSummarizedRequests] = useState<CpSummarizedRequest[]>([])
  const [loadingSummarized, setLoadingSummarized] = useState(false)
  const [unsumTarget, setUnsumTarget] = useState<CpSummarizedRequest | null>(null)
  const [unsumReason, setUnsumReason] = useState('')
  const [unsummarizing, setUnsummarizing] = useState(false)

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

  // 目前篩選範圍的拋轉狀態。⚠️ 只有在「有用依公司篩選指定單一公司」時才有意義——
  // 拋轉的單位就是「週期＋期別＋公司」，沒指定公司時 rows 會混到兩家公司。
  const pushState = useMemo(() => {
    if (!rows.length) return { pushed: 0, total: 0, batchNo: null as string | null }
    const pushedRows = rows.filter((r) => r.ragic_pushed)
    return {
      pushed: pushedRows.length,
      total: rows.length,
      batchNo: pushedRows.find((r) => r.ragic_push_batch_no)?.ragic_push_batch_no ?? null,
    }
  }, [rows])
  const rangePicked = !!cycleId && !!periodLabel.trim() && !!company
  const allPushed = rangePicked && pushState.total > 0 && pushState.pushed === pushState.total

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

  const handleCancelPush = async () => {
    if (!cycleId || !periodLabel.trim() || !company) return
    if (!cancelPushReason.trim()) {
      message.warning('請填寫取消拋轉的原因')
      return
    }
    setCancellingPush(true)
    try {
      const res = await cancelRagicPush({
        cycle_id: cycleId, period_label: periodLabel.trim(), company,
        reason: cancelPushReason.trim(),
      })
      message.success(res.data.message)
      setCancelPushModal(false)
      setCancelPushReason('')
      if (res.data.next_step) {
        Modal.info({
          title: '已取消拋轉',
          width: 560,
          content: <div style={{ whiteSpace: 'pre-wrap' }}>{res.data.next_step}</div>,
          okText: '知道了',
        })
      }
      load()
    } catch (err: any) {
      message.error(errMsg(err, '取消拋轉失敗'))
    } finally {
      setCancellingPush(false)
    }
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

  // 週期＋公司＋月份都選好後，載入這個範圍內「尚未被彙整過」的請購單。
  // 2026-08-09 起**未關閉的單也會列出來**（can_summarize=false），但不會被自動勾選，
  // 也不能手動勾——只是讓使用者看得到「那張單就在那裡，只差一個關閉動作」。
  const loadEligible = (opts?: { autoSelectIds?: number[] }) => {
    if (!generateModal || !genCycleId || !genCompany || !genMonth) {
      setEligibleRequests([])
      setSelectedRequestIds([])
      return
    }
    setLoadingEligible(true)
    getEligibleRequests({ cycle_id: genCycleId, company: genCompany, year_month: genMonth })
      .then((r) => {
        setEligibleRequests(r.data)
        const selectable = r.data.filter((x) => x.can_summarize).map((x) => x.id)
        // 剛按過「關閉並納入」的話只補勾那幾張，不要把使用者先前取消勾選的又勾回來
        setSelectedRequestIds((prev) =>
          opts?.autoSelectIds
            ? Array.from(new Set([...prev, ...opts.autoSelectIds])).filter((id) => selectable.includes(id))
            : selectable,
        )
      })
      .catch((err) => message.error(errMsg(err, '載入可彙整清單失敗')))
      .finally(() => setLoadingEligible(false))
  }

  useEffect(() => { loadEligible() }, [generateModal, genCycleId, genCompany, genMonth])

  // 「關閉並納入」：關閉那張單之後重載清單並自動勾起來。規則沒有放寬——還是先關閉
  // 才彙整，只是不用為了按一個關閉跳去請購單頁再走回來。
  const handleCloseAndInclude = async (row: CpEligibleRequest) => {
    setClosingRequestId(row.id)
    try {
      await closeRequests([row.id])
      message.success(`已關閉 ${row.request_no}，並勾選納入這次彙整`)
      loadEligible({ autoSelectIds: [row.id] })
    } catch (err: any) {
      message.error(errMsg(err, '關閉失敗'))
    } finally {
      setClosingRequestId(null)
    }
  }

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

  // ── 退回請購單（2026-08-09 新增）─────────────────────────────────────────
  const openUnsummarize = () => {
    setUnsumCycleId(cycleId)
    setUnsumCompany(company)
    setUnsumMonth(periodLabel.trim() || currentYearMonth())
    setSummarizedRequests([])
    setUnsumTarget(null)
    setUnsumReason('')
    setUnsumModal(true)
  }

  useEffect(() => {
    if (!unsumModal || !unsumCycleId) { setUnsumCompanyOptions([]); return }
    getRequests({ cycle_id: unsumCycleId })
      .then((r) => setUnsumCompanyOptions(Array.from(new Set(r.data.map((x) => x.company))).sort()))
      .catch(() => {})
  }, [unsumModal, unsumCycleId])

  const loadSummarized = () => {
    if (!unsumModal || !unsumCycleId || !unsumCompany || !unsumMonth) {
      setSummarizedRequests([])
      return
    }
    setLoadingSummarized(true)
    getSummarizedRequests({ cycle_id: unsumCycleId, company: unsumCompany, year_month: unsumMonth })
      .then((r) => setSummarizedRequests(r.data))
      .catch((err) => message.error(errMsg(err, '載入已彙整請購單失敗')))
      .finally(() => setLoadingSummarized(false))
  }

  useEffect(() => { loadSummarized() }, [unsumModal, unsumCycleId, unsumCompany, unsumMonth])

  const handleUnsummarize = async () => {
    if (!unsumTarget) return
    if (!unsumReason.trim()) {
      message.warning('請填寫退回原因')
      return
    }
    setUnsummarizing(true)
    try {
      const res = await unsummarizeRequest({ request_id: unsumTarget.id, reason: unsumReason.trim() })
      message.success(res.data.message)
      // 用**一個** Modal 同時交代「下一步」與「要複查的項目」。
      // warnings 不是失敗（動作已成功），next_step 是流程指引——分成兩個 Modal 會疊在
      // 一起，使用者只會關掉不看。2026-08-09：next_step 是因為退回後「要改內容就重新
      // 開啟，但改完記得再關閉」這件事沒有任何地方講過，實際害人卡住過一次。
      const { next_step: nextStep, warnings } = res.data
      if (nextStep || warnings.length) {
        const show = warnings.length ? Modal.warning : Modal.info
        show({
          title: warnings.length ? '退回完成，有需要複查的項目' : '退回完成，接下來',
          width: 640,
          content: (
            <div>
              {warnings.length > 0 && (
                <>
                  <div style={{ marginBottom: 4 }}>以下彙整列的調整量是人工設定過的，已保留未變動：</div>
                  <ul style={{ paddingLeft: 18, margin: '0 0 12px' }}>
                    {warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </>
              )}
              {nextStep && (
                <div style={{ whiteSpace: 'pre-wrap', color: '#666' }}>{nextStep}</div>
              )}
            </div>
          ),
          okText: '知道了',
        })
      }
      setUnsumTarget(null)
      setUnsumReason('')
      loadSummarized()
      load()
    } catch (err: any) {
      message.error(errMsg(err, '退回失敗'))
    } finally {
      setUnsummarizing(false)
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
            <Tooltip
              title={
                !rangePicked
                  ? '請先選擇週期／期別，並用「依公司篩選」指定單一公司'
                  : allPushed
                    ? `這個範圍已經拋轉過了（批次 ${pushState.batchNo || '—'}），要重推請先按「取消拋轉」`
                    : undefined
              }
            >
              <Button
                icon={<CloudUploadOutlined />}
                loading={pushing}
                onClick={handlePushToRagic}
                disabled={!rangePicked || allPushed}
              >
                拋轉 Ragic
              </Button>
            </Tooltip>
          )}
          {/* 2026-08-09：取消拋轉。只在該範圍確實有已拋轉的列時才出現——
              它同時是「重推」與「解開退回請購單限制」的唯一入口。 */}
          {canBuy && rangePicked && pushState.pushed > 0 && (
            <Button
              icon={<UndoOutlined />}
              loading={cancellingPush}
              onClick={() => { setCancelPushReason(''); setCancelPushModal(true) }}
            >
              取消拋轉
            </Button>
          )}
          {canBuy && (
            <Button icon={<RollbackOutlined />} onClick={openUnsummarize}>退回請購單</Button>
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
            locale={{ emptyText: '這個範圍內沒有尚未被彙整過的請購單' }}
            rowSelection={{
              selectedRowKeys: selectedRequestIds,
              onChange: (keys) => setSelectedRequestIds(keys as number[]),
              // 未關閉的單不能勾（規則沒放寬，只是讓它看得見）
              getCheckboxProps: (r) => ({ disabled: !r.can_summarize }),
            }}
            columns={[
              { title: '請購單號', dataIndex: 'request_no', width: 140 },
              { title: '部門', dataIndex: 'department_name', width: 110, render: (v?: string | null) => v || '—' },
              {
                title: '可否彙整',
                key: 'can_summarize',
                width: 210,
                render: (_: unknown, r: CpEligibleRequest) =>
                  r.can_summarize ? (
                    <Space size={4}>
                      <Tag color="green" style={{ marginInlineEnd: 0 }}>可彙整</Tag>
                      {r.unsummarized_at && (
                        <Tooltip title={r.unsummarize_reason ? `退回原因：${r.unsummarize_reason}` : '這張單曾被退回過'}>
                          <Tag style={{ marginInlineEnd: 0 }}>曾退回</Tag>
                        </Tooltip>
                      )}
                    </Space>
                  ) : (
                    <Space size={4} wrap>
                      <Tooltip title={r.block_reason || undefined}>
                        <Tag color="warning" style={{ marginInlineEnd: 0 }}>未關閉</Tag>
                      </Tooltip>
                      {canClose ? (
                        <Button
                          size="small"
                          icon={<LockOutlined />}
                          loading={closingRequestId === r.id}
                          onClick={() => handleCloseAndInclude(r)}
                        >
                          關閉並納入
                        </Button>
                      ) : (
                        <Text type="secondary" style={{ fontSize: 12 }}>需關閉權限</Text>
                      )}
                    </Space>
                  ),
              },
              { title: '填寫人', dataIndex: 'submitted_by_name', width: 100, render: (v?: string | null) => v || '—' },
              {
                title: '關閉時間',
                dataIndex: 'closed_at',
                width: 150,
                render: (v: string | null | undefined, r: CpEligibleRequest) =>
                  r.can_summarize ? (v ? new Date(v).toLocaleString() : '—') : <Text type="secondary">尚未關閉</Text>,
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
          列出這個範圍內<b>還沒被彙整過</b>的請購單。<b>未關閉的單也會列出來但不能勾選</b>——
          關閉代表「這張單的數量已經定案」，開放中的單彙整完還能被改，數字會默默對不上。
          需要的話按該列的「關閉並納入」直接關掉並勾起來，不必跳回請購單頁。
          彙整過的請購單不會再出現在這個清單裡，不用擔心重複彙整；期別標籤由系統依勾選的
          請購單本身的期別自動判斷，不用手動輸入。
        </div>
      </Modal>

      <Modal
        title="取消拋轉 Ragic"
        open={cancelPushModal}
        onOk={handleCancelPush}
        onCancel={() => { setCancelPushModal(false); setCancelPushReason('') }}
        okText="確定取消拋轉"
        cancelText="返回"
        confirmLoading={cancellingPush}
        width={620}
      >
        <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
          <Descriptions.Item label="範圍">{periodLabel.trim()}／{company}</Descriptions.Item>
          <Descriptions.Item label="原拋轉批次">{pushState.batchNo || '—'}</Descriptions.Item>
          <Descriptions.Item label="已拋轉彙整列">{pushState.pushed} 筆</Descriptions.Item>
        </Descriptions>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="會做什麼"
          description={(
            <ul style={{ paddingLeft: 18, margin: 0 }}>
              <li>清掉這個範圍的<b>拋轉標記</b>，之後可以重新拋轉</li>
              <li>連帶<b>解開「已拋轉就不能退回請購單」</b>的限制</li>
              <li><b>不會</b>動到彙整列本身的調整量、狀態或已轉的採購單</li>
            </ul>
          )}
        />
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="Ragic 端目前是模擬的（stub）"
          description="現在 Ragic 那邊還沒有真的記錄，所以清掉標記就結束。等 Ragic 表單建好、真的會寫入之後，取消拋轉還要另外決定 Ragic 那筆記錄怎麼處理。"
        />
        <Form layout="vertical">
          <Form.Item label="取消原因" required extra="會寫進異常稽核紀錄">
            <TextArea
              rows={3}
              value={cancelPushReason}
              onChange={(e) => setCancelPushReason(e.target.value)}
              placeholder="例如：數量要重新調整、拋轉範圍選錯、需要退回某張請購單"
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="退回請購單（把已彙整的請購單改回未彙整）"
        open={unsumModal}
        onCancel={() => setUnsumModal(false)}
        footer={<Button onClick={() => setUnsumModal(false)}>關閉</Button>}
        width={860}
      >
        <Space wrap style={{ marginBottom: 12 }}>
          <Select
            placeholder="選擇週期"
            style={{ width: 200 }}
            value={unsumCycleId}
            onChange={(v) => { setUnsumCycleId(v); setUnsumCompany(undefined) }}
            showSearch
            optionFilterProp="label"
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            placeholder="選擇公司"
            style={{ width: 160 }}
            value={unsumCompany}
            onChange={setUnsumCompany}
            disabled={!unsumCycleId}
            options={unsumCompanyOptions.map((c) => ({ label: c, value: c }))}
          />
          <Select
            placeholder="選擇期別"
            style={{ width: 160 }}
            value={unsumMonth || undefined}
            onChange={(v) => setUnsumMonth(v || '')}
            options={recentMonthOptions().map((m) => ({ label: m, value: m }))}
          />
        </Space>

        {(!unsumCycleId || !unsumCompany || !unsumMonth) ? (
          <Alert type="info" showIcon message="請先選擇週期／公司／期別，會列出這個範圍內已經被彙整過的請購單" />
        ) : (
          <Table<CpSummarizedRequest>
            dataSource={summarizedRequests}
            rowKey="id"
            size="small"
            loading={loadingSummarized}
            pagination={false}
            scroll={{ y: 320 }}
            locale={{ emptyText: '這個範圍內沒有已彙整的請購單' }}
            columns={[
              { title: '請購單號', dataIndex: 'request_no', width: 130 },
              { title: '部門', dataIndex: 'department_name', width: 110, render: (v?: string | null) => v || '—' },
              { title: '填寫人', dataIndex: 'submitted_by_name', width: 90, render: (v?: string | null) => v || '—' },
              { title: '彙整批次', dataIndex: 'summary_batch_no', width: 180, render: (v?: string | null) => v || '—' },
              {
                title: '彙整時間',
                dataIndex: 'summarized_at',
                width: 150,
                render: (v?: string | null) => (v ? new Date(v).toLocaleString() : '—'),
              },
              {
                title: '請購總額',
                dataIndex: 'total_amount',
                width: 100,
                align: 'right' as const,
                render: (v: number) => Number(v).toLocaleString(),
              },
              {
                title: '操作',
                key: 'actions',
                width: 220,
                render: (_: unknown, r: CpSummarizedRequest) =>
                  r.can_unsummarize ? (
                    <Button
                      size="small"
                      danger
                      icon={<RollbackOutlined />}
                      onClick={() => { setUnsumTarget(r); setUnsumReason('') }}
                    >
                      退回
                    </Button>
                  ) : (
                    <Tag color="default" title={r.block_reason || undefined}>
                      不能退回：{r.block_reason}
                    </Tag>
                  ),
              },
            ]}
          />
        )}

        <div style={{ color: '#888', fontSize: 12, marginTop: 12 }}>
          退回後這張請購單會回到「已關閉、未彙整」狀態，重新出現在「產生彙整」的可勾選清單裡；
          彙整列的需求量會由系統依剩下仍為已彙整的請購單重新計算。已轉採購單、已拋轉 Ragic、
          或請購單已被重新開啟的，不能退回（原因會直接顯示在該列）。退回不會改變請購單的關閉狀態。
        </div>
      </Modal>

      <Modal
        title={unsumTarget ? `確認退回 — ${unsumTarget.request_no}` : '確認退回'}
        open={!!unsumTarget}
        onOk={handleUnsummarize}
        onCancel={() => { setUnsumTarget(null); setUnsumReason('') }}
        okText="確定退回"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        confirmLoading={unsummarizing}
      >
        {unsumTarget && (
          <>
            <Descriptions column={1} size="small" bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="部門">{unsumTarget.department_name || '—'}</Descriptions.Item>
              <Descriptions.Item label="彙整批次">{unsumTarget.summary_batch_no || '—'}</Descriptions.Item>
              <Descriptions.Item label="請購總額">{Number(unsumTarget.total_amount).toLocaleString()}</Descriptions.Item>
            </Descriptions>
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message="退回後，這張單所涵蓋料號的草稿彙整列需求量會被重新計算；已被人工調整過的調整量會保留不變，並在退回結果中提醒你複查。"
            />
            <Form layout="vertical">
              <Form.Item label="退回原因" required extra="會記錄在請購單與稽核紀錄裡">
                <TextArea
                  rows={3}
                  value={unsumReason}
                  onChange={(e) => setUnsumReason(e.target.value)}
                  placeholder="例如：本期取消採購、該部門需求有誤需重新填寫"
                />
              </Form.Item>
            </Form>
          </>
        )}
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
