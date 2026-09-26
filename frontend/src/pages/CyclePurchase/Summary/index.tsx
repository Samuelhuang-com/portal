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
import FlowSteps from '@/pages/CyclePurchase/components/FlowSteps'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  DatePicker,
  Alert, Button, Card, Descriptions, Form, Input, InputNumber, Modal,
  Select, Space, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
// CLAUDE.md §8：任何「選一段期間」的篩選一律用這個共用元件，不要各模組自己刻
import StandardRangePicker from '@/components/StandardRangePicker'
import {
  CloudUploadOutlined, ExclamationCircleOutlined, LinkOutlined, LockOutlined, RollbackOutlined,
  ShoppingCartOutlined, SyncOutlined, UndoOutlined,
} from '@ant-design/icons'
import {
  cancelRagicPush, closeRequests, convertToPo, generateSummaryFromRequests, getCycles,
  getDepartmentBreakdown, getEligibleRequests, getExcludedRequests, getPendingRequests, getRagicPushedDateRange, getRagicPushedDocs,
  getRagicSummaryLink, getRequests, getSummarizedRequests, getSummary, getVendorGroups,
  pushSummaryToRagic, unsummarizeRequest, updateSummaryItem,
} from '@/api/cyclePurchase'
import type {
  CpCycle, CpDepartmentBreakdown, CpEligibleRequest, CpExcludedRequest, CpFailedVendor, CpNotPushedRow, CpPendingRequest,
  CpPushedDocument, CpPushToRagicResult, CpRagicDocRef, CpRagicPushedDoc, CpSummarizedRequest, CpSummary,
  CpVendorGroup,
} from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

/**
 * 2026-09-22 Samuel 裁示：「轉採購單」相關功能先隱藏（採購流程改由 Ragic 週採請購單處理）。
 * 隱藏範圍：①「依供應商分組（轉採購單）」卡片 ②彙整明細的「採購單號」欄
 * ③已拋轉 Ragic 清單的「轉採購單」欄。程式碼與後端 API 保留，要恢復把這個值改成 true。
 */
const SHOW_PO_CONVERT = false

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
  const [excludedRequests, setExcludedRequests] = useState<CpExcludedRequest[]>([])
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

  // 2026-09-15 新增：Ragic「週採匯總請購單」表單連結（右上角「在 Ragic 查看」）。
  // 網址一律跟後端要，前端不硬寫——表單位置的唯一真實來源是 config.py 的
  // RAGIC_CP_SUMMARY_*，兩邊各存一份之後 Ragic 搬家一定會有一邊忘了改。
  const [ragicLink, setRagicLink] = useState<string>('')

  useEffect(() => {
    getCycles().then((r) => setCycles(r.data)).catch(() => message.error('載入週期設定失敗'))
    // 拿不到連結就單純不顯示，不要跳錯誤訊息干擾主要流程
    getRagicSummaryLink().then((r) => setRagicLink(r.data?.url || '')).catch(() => setRagicLink(''))
  }, [])

  // ── 「已彙整 Ragic 請購單」TAB（2026-09-16 新增）─────────────────────────
  // 這一頁回答的問題跟「彙整作業」不同：不是「這期要買什麼」，而是
  // 「我到底推了哪些單到 Ragic、對應 Ragic 上的哪一張」。所以：
  //   - 一列＝一張 Ragic 單據（後端依 批次號＋廠商＋Ragic 單號 分組），不是一個彙整列
  //   - ⚠️ 這一頁讀的是 **Portal 自己資料庫**的拋轉紀錄，不是去 Ragic 現撈。
  //     Ragic 上看得到某張單 ≠ 這裡就要有 —— 直接打 Ragic API 建的測試單、
  //     或別台 Portal 推的單，本來就不會出現在這裡（下面的提示文字已寫明）。
  //   - 篩選用「拋轉日期」不是期別（8 月的期別可能 9 月才推）
  //   - 不受上面那排週期／期別／公司篩選影響，這一頁是獨立的查詢
  // 2026-09-25：有彙整權限的人預設停在「待彙整請購單」（TAB 最前面）
  const [activeTab, setActiveTab] = useState<string>(canBuy ? 'pending' : 'work')

  // ── 待彙整請購單 TAB（2026-09-25 Samuel 裁示）────────────────────────────
  // 全公司「已關閉、尚未彙整」的單，依 週期＋公司＋期別 分組，每組一顆
  // 「產生彙整」直接帶好條件開既有的產生彙整視窗。條件與左側選單「彙整單」
  // 紅點相同，兩邊數字一定對得上。只有 cycle_purchase_buyer 看得到（端點權限）。
  const [pendingRows, setPendingRows] = useState<CpPendingRequest[]>([])
  const [pendingLoading, setPendingLoading] = useState(false)
  const [pendingError, setPendingError] = useState<string>('')
  const [pendingLoaded, setPendingLoaded] = useState(false)

  const loadPending = () => {
    if (!canBuy) return
    setPendingLoading(true)
    setPendingError('')
    getPendingRequests()
      .then((r) => { setPendingRows(r.data); setPendingLoaded(true) })
      .catch((err) => {
        const m = errMsg(err, '載入待彙整請購單失敗')
        setPendingRows([])
        setPendingError(m)
      })
      .finally(() => setPendingLoading(false))
  }

  useEffect(() => {
    if (activeTab === 'pending') loadPending()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  const pendingGroups = useMemo(() => {
    const map = new Map<string, { key: string; cycleId: number; cycleName: string; company: string; period: string; overdue: boolean; rows: CpPendingRequest[] }>()
    pendingRows.forEach((r) => {
      const key = `${r.cycle_id}|${r.company}|${r.period_label}`
      if (!map.has(key)) {
        map.set(key, { key, cycleId: r.cycle_id, cycleName: r.cycle_name || `週期 #${r.cycle_id}`, company: r.company, period: r.period_label, overdue: !!r.is_overdue, rows: [] })
      }
      map.get(key)!.rows.push(r)
    })
    // 2026-09-25：逾期（逾期，不可拋）的組排到最後
    return Array.from(map.values()).sort((a, b) => Number(a.overdue) - Number(b.overdue))
  }, [pendingRows])
  // TAB 張數只算還能彙整的（與左側選單紅點一致）；逾期的另外標示
  const pendingActionable = pendingRows.filter((r) => !r.is_overdue).length
  const pendingOverdue = pendingRows.length - pendingActionable
  const [pushedDocs, setPushedDocs] = useState<CpRagicPushedDoc[]>([])
  const [pushedLoading, setPushedLoading] = useState(false)
  const [pushedRange, setPushedRange] = useState<[Dayjs, Dayjs] | null>(null)
  // StandardRangePicker 的 anchor：CLAUDE.md §8.2 規定要用「資料最後一天」而不是
  // 今天。拋轉是人工動作、不是每天都有，用今天當基準「本月」很容易框到一段完全
  // 沒有資料的區間，使用者會以為資料不見了。
  const [pushedAnchor, setPushedAnchor] = useState<string>('')
  // 載入失敗要留在畫面上。只丟一個 message.error 的話，使用者切過來時
  // toast 早就消失了，看到的是一張空表格——跟「真的沒有資料」長得一模一樣，
  // 於是會回報成「拋轉了但 TAB 沒出現」。2026-09-19 補。
  const [pushedError, setPushedError] = useState<string>('')

  useEffect(() => {
    getRagicPushedDateRange()
      .then((r) => setPushedAnchor(r.data?.end || ''))
      .catch(() => setPushedAnchor(''))
  }, [])

  const loadPushed = () => {
    setPushedLoading(true)
    // range 為 null ＝「全部」，照 §8.3 的語意不帶起迄，由後端回全部資料
    const params = pushedRange
      ? { start: pushedRange[0].format('YYYY-MM-DD'), end: pushedRange[1].format('YYYY-MM-DD') }
      : {}
    setPushedError('')
    getRagicPushedDocs(params)
      .then((r) => { setPushedDocs(r.data); setPushedError('') })
      .catch((err) => {
        const m = errMsg(err, '載入已彙整 Ragic 請購單失敗')
        setPushedDocs([])
        setPushedError(m)
        message.error(m)
      })
      .finally(() => setPushedLoading(false))
  }

  // 切到這個 TAB 才載入，避免使用者根本沒點就先打一支 API
  useEffect(() => {
    if (activeTab === 'pushed') loadPushed()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, pushedRange])

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

  // ── 2026-09-22：未選週期時顯示「當月彙整總覽」──────────────────────────
  // 原本一進頁面只有「請先選擇週期與期別」，要先篩選才看得到東西。
  // 改成：預設列出指定月份（預設當月）所有週期×公司的彙整單，點一列就帶入
  // 週期／期別／公司，顯示原本的明細畫面。GET /summary 只帶 period_label 即可跨週期查詢。
  const [overviewMonth, setOverviewMonth] = useState<string>(currentYearMonth())
  const [overviewRows, setOverviewRows] = useState<CpSummary[]>([])
  const [overviewLoading, setOverviewLoading] = useState(false)
  const loadOverview = () => {
    if (!overviewMonth) { setOverviewRows([]); return }
    setOverviewLoading(true)
    getSummary({ period_label: overviewMonth })
      .then((r) => setOverviewRows(r.data))
      .catch((err) => message.error(errMsg(err, '載入當月彙整失敗')))
      .finally(() => setOverviewLoading(false))
  }
  useEffect(() => { if (!cycleId) loadOverview() }, [cycleId, overviewMonth])

  type OverviewGroup = {
    key: string; cycle_id: number; cycle_name: string; company: string; period_label: string
    items: number; depts: number; vendors: number; qty: number; amount: number
    pushed: number; total: number; ragic_ids: string[]
    // 2026-09-25（0924 會議第 4 項）：「已拋轉 N 張」要講清楚是哪幾張、何時拋的
    ragic_docs: { id: string; url?: string | null; at?: string | null }[]
  }
  const overviewGroups = useMemo<OverviewGroup[]>(() => {
    const m = new Map<string, OverviewGroup & { _i: Set<number>; _d: Set<number>; _v: Set<number> }>()
    for (const r of overviewRows) {
      const key = `${r.cycle_id}|${r.company}|${r.period_label}`
      let g = m.get(key)
      if (!g) {
        g = {
          key, cycle_id: r.cycle_id,
          cycle_name: r.cycle_name || cycles.find((c) => c.id === r.cycle_id)?.cycle_name || `週期 #${r.cycle_id}`,
          company: r.company, period_label: r.period_label,
          items: 0, depts: 0, vendors: 0, qty: 0, amount: 0, pushed: 0, total: 0, ragic_ids: [], ragic_docs: [],
          _i: new Set(), _d: new Set(), _v: new Set(),
        }
        m.set(key, g)
      }
      g._i.add(r.item_id)
      if (r.department_id) g._d.add(r.department_id)
      if (r.vendor_id) g._v.add(r.vendor_id)
      const q = Number(r.adjusted_qty ?? r.demand_qty ?? 0)
      g.qty += q
      g.amount += q * Number(r.unit_price ?? 0)
      g.total += 1
      if (r.ragic_pushed) g.pushed += 1
      if (r.ragic_record_id && !g.ragic_ids.includes(r.ragic_record_id)) {
        g.ragic_ids.push(r.ragic_record_id)
        g.ragic_docs.push({ id: r.ragic_record_id, url: r.ragic_record_url, at: r.ragic_pushed_at })
      }
    }
    return Array.from(m.values())
      .map(({ _i, _d, _v, ...g }) => ({ ...g, items: _i.size, depts: _d.size, vendors: _v.size }))
      .sort((a, b) => a.company.localeCompare(b.company) || a.cycle_name.localeCompare(b.cycle_name))
  }, [overviewRows, cycles])

  const openGroup = (g: OverviewGroup) => {
    setCycleId(g.cycle_id)
    setPeriodOptions((prev) => (prev.includes(g.period_label) ? prev : [g.period_label, ...prev]))
    setPeriodLabel(g.period_label)
    setCompany(g.company)
  }
  const backToOverview = () => { setCycleId(undefined); setPeriodLabel(''); setCompany(undefined) }

  const companyOptions = useMemo(
    () => Array.from(new Set(rows.map((r) => r.company))),
    [rows],
  )

  // 目前篩選範圍的拋轉狀態。⚠️ 只有在「有用依公司篩選指定單一公司」時才有意義——
  // 拋轉的單位就是「週期＋期別＋公司」，沒指定公司時 rows 會混到兩家公司。
  const pushState = useMemo(() => {
    if (!rows.length) return { pushed: 0, total: 0, batchNo: null as string | null, ragicNos: [] as string[] }
    const pushedRows = rows.filter((r) => r.ragic_pushed)
    return {
      pushed: pushedRows.length,
      total: rows.length,
      batchNo: pushedRows.find((r) => r.ragic_push_batch_no)?.ragic_push_batch_no ?? null,
      ragicNos: Array.from(new Set(pushedRows.map((r) => r.ragic_record_id).filter((x): x is string => !!x))).sort(),
    }
  }, [rows])
  const rangePicked = !!cycleId && !!periodLabel.trim() && !!company
  const allPushed = rangePicked && pushState.total > 0 && pushState.pushed === pushState.total
  // 2026-09-25（0924 會議第 8 項）：期別早於本月＝逾期，不可拋（後端也會擋）
  const periodOverdue = !!periodLabel.trim() && periodLabel.trim() < currentYearMonth()

  const handlePushToRagic = () => {
    if (!cycleId || !periodLabel.trim() || !company) {
      message.warning('請先選擇週期／期別，並用「依公司篩選」指定單一公司後再拋轉')
      return
    }
    Modal.confirm({
      title: '拋轉到 Ragic「★週採請購單」',
      width: 600,
      content: (
        <div>
          <p>
            將把「{periodLabel.trim()}／{company}」範圍內的彙整列寫進 Ragic 的
            「★週採請購單」，由 Ragic 的簽核流程簽核。
          </p>
          <Alert
            type="info"
            showIcon
            message="依廠商拆單：一家廠商一張 Ragic 單"
            description={
              <span>
                同一次拋轉共用一個批次號，每家廠商各自是一張 Ragic 請購單、
                各有自己的編號，也各自簽核。<b>部門與會計課目逐列帶在子表上</b>，
                所以一張單可以橫跨多個部門（2026-09-20 起）。
                <br />
                下列列<b>不會</b>送出去，拋轉後會列出是哪幾筆：
                缺供應商、調整量為 0、以及 2026-07-16 之前沒有部門別的歷史彙整列。
                <br />
                <b>沒有單價的列照常送出</b>，單價與金額留空白，請到 Ragic 補填（該部門小計也會留空）。
              </span>
            }
          />
        </div>
      ),
      okText: '確定拋轉',
      cancelText: '取消',
      onOk: async () => {
        setPushing(true)
        try {
          const res = await pushSummaryToRagic({ cycle_id: cycleId, period_label: periodLabel.trim(), company })
          showPushResult(res.data)
          load()
        } catch (err: any) {
          // 2026-09-25（0924 會議第 6 項）：拋轉被擋的訊息會列出 Ragic 單號與重拋步驟，
          // 放 toast 幾秒就消失看不完，改用對話框。
          Modal.error({
            title: '無法拋轉',
            width: 560,
            content: <div style={{ whiteSpace: 'pre-line' }}>{errMsg(err, '拋轉失敗')}</div>,
          })
        } finally {
          setPushing(false)
        }
      },
    })
  }

  // 2026-09-15 新增：拋轉結果視窗。
  // ⚠️ **部分成功也是 HTTP 200**，所以不能只丟一行 message.success 就算了——
  //    成功幾張、哪幾筆沒送出去、哪家廠商失敗，三段都要讓使用者看到。
  //    這個模組吃過三次「單子憑空消失」的虧（見 CLAUDE.md 與退回請購單那次的結論），
  //    原則是：不要過濾掉，列出來並寫明原因。
  //    比照「退回請購單」的做法，三段合併成**一個** Modal，不要連跳好幾個。
  const showPushResult = (r: CpPushToRagicResult) => {
    const docs = r.documents ?? []
    const notPushed = r.not_pushed ?? []
    const failed = r.failed ?? []

    Modal.info({
      title: failed.length > 0 ? '拋轉完成（部分單據失敗）' : '拋轉完成',
      width: 720,
      okText: '知道了',
      content: (
        <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
          {r.is_stub && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 12 }}
              message="RAGIC_CP_SUMMARY_ENABLED=false，這是模擬結果，沒有真正寫入 Ragic"
            />
          )}
          <Descriptions bordered size="small" column={1} style={{ marginBottom: 12 }}>
            <Descriptions.Item label="批次號">{r.batch_no}</Descriptions.Item>
            <Descriptions.Item label="結果">{r.message}</Descriptions.Item>
          </Descriptions>

          {docs.length > 0 && (
            <>
              <Text strong>已寫入 Ragic 的單據（{docs.length} 張）</Text>
              <Table<CpPushedDocument>
                style={{ marginTop: 8, marginBottom: 12 }}
                dataSource={docs}
                /* ⚠️ 2026-09-18：拆單加了部門之後 vendor_id 不再唯一
                   （同一家廠商會有多張，一個部門一張），rowKey 必須帶部門 */
                rowKey={(d) => `${d.vendor_id ?? 'none'}-${d.department_id ?? 'none'}`}
                size="small"
                pagination={false}
                columns={[
                  { title: '廠商', dataIndex: 'vendor_name', width: 150, render: (v: string) => v || '—' },
                  { title: '部門', dataIndex: 'department_name', width: 150, render: (v: string) => v || '—' },
                  {
                    title: 'Ragic 單號',
                    key: 'no',
                    render: (_: unknown, d: CpPushedDocument) =>
                      d.ragic_record_url ? (
                        <a
                          href={d.ragic_record_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#4BA8E8', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                        >
                          <LinkOutlined /> {d.ragic_no || d.ragic_record_id}
                        </a>
                      ) : (d.ragic_no || d.ragic_record_id || '—'),
                  },
                  { title: '明細列數', dataIndex: 'line_count', width: 90, align: 'right' as const },
                ]}
              />
            </>
          )}

          {failed.length > 0 && (
            <>
              <Alert
                type="error"
                showIcon
                style={{ marginBottom: 8 }}
                message={`${failed.length} 張單寫入失敗（其他張已成功，這幾張可修正後重推）`}
              />
              <Table<CpFailedVendor>
                style={{ marginBottom: 12 }}
                dataSource={failed}
                rowKey={(f, i) => `${f.vendor_name ?? ''}-${f.department_name ?? ''}-${i}`}
                size="small"
                pagination={false}
                columns={[
                  { title: '廠商', dataIndex: 'vendor_name', width: 140, render: (v: string) => v || '—' },
                  { title: '部門', dataIndex: 'department_name', width: 100, render: (v: string) => v || '—' },
                  { title: '錯誤訊息', dataIndex: 'error' },
                ]}
              />
            </>
          )}

          {notPushed.length > 0 && (
            <>
              <Alert
                type="warning"
                showIcon
                style={{ marginBottom: 8 }}
                message={`${notPushed.length} 筆彙整列未拋轉`}
                description="這些列不會出現在 Ragic。請依「原因」欄修正（多半是到料號對照表補供應商與單價）後，用「取消拋轉→重推」或下一期再處理。"
              />
              <Table<CpNotPushedRow>
                dataSource={notPushed}
                rowKey={(x) => x.summary_id}
                size="small"
                pagination={false}
                columns={[
                  { title: '料號', dataIndex: 'item_code', width: 130 },
                  { title: '品名', dataIndex: 'item_name' },
                  { title: '部門', dataIndex: 'department_name', width: 100, render: (v: string) => v || '—' },
                  { title: '原因', dataIndex: 'reason', width: 260 },
                ]}
              />
            </>
          )}

          {(r.already_pushed_count ?? 0) > 0 && (
            <Text type="secondary" style={{ display: 'block', marginTop: 12 }}>
              另有 {r.already_pushed_count} 筆彙整列先前已拋轉過，本次略過。
            </Text>
          )}
        </div>
      ),
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

  /** 從「待彙整請購單」TAB 直接帶好 週期＋公司＋期別 開產生彙整視窗 */
  const openGenerateFor = (cid: number, comp: string, month: string) => {
    setGenCycleId(cid)
    setGenCompany(comp)
    setGenMonth(month)
    setEligibleRequests([])
    setSelectedRequestIds([])
    setGenerateModal(true)
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
      setExcludedRequests([])
      return
    }
    // 2026-09-25（0924 會議第 7 項）：同時抓「已彙整／已拋轉、所以不在清單裡」的單，
    // 讓第一次用的人知道為什麼選不到。失敗不影響主流程。
    getExcludedRequests({ cycle_id: genCycleId, company: genCompany, year_month: genMonth })
      .then((r) => setExcludedRequests(r.data))
      .catch(() => setExcludedRequests([]))
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
      // 2026-09-25：從「待彙整請購單」TAB 產生的話，切到彙整作業看結果
      // （上面已帶好週期/公司/期別）；回到待彙整 TAB 時會重新載入。
      if (activeTab === 'pending') setActiveTab('work')
      else if (pendingLoaded) loadPending()
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
      <FlowSteps />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 彙整單／匯總請購單</Title>
        <Space>
          {/* 2026-09-15 新增：沿用 CLAUDE.md §7 明細 Drawer 的「在 Ragic 查看」樣式
              （LinkOutlined ＋ 色碼 #4BA8E8 ＋ target="_blank"），放在模組右上角。
              ⚠️ 只連到表單層級，不是單筆——Ragic 的 UI 不吃網址篩選參數，而且
              ragic_record_id 存的是採購編號不是內部 id，詳見後端
              GET /summary/ragic-link 的說明。對帳看清單上的「Ragic 記錄」欄。 */}
          {ragicLink && (
            <a
              href={ragicLink}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: 14, color: '#4BA8E8', display: 'flex',
                alignItems: 'center', gap: 3, fontWeight: 400, marginRight: 4,
              }}
            >
              <LinkOutlined /> 在 Ragic 查看
            </a>
          )}
          {/* 這四顆都是「彙整作業」的動作，切到「已彙整 Ragic 請購單」那頁時
              它們沒有作用對象（那頁是獨立查詢、不吃上面的週期／期別篩選），
              所以隨 TAB 隱藏，避免使用者按了沒反應。 */}
          {activeTab === 'work' && (
            <>
          {canBuy && (
            <Tooltip
              title={
                !rangePicked
                  ? '請先選擇週期／期別，並用「依公司篩選」指定單一公司'
                  : periodOverdue && !allPushed
                    ? `期別 ${periodLabel.trim()} 已過，逾期，不可拋（週採每期只在當月拋轉一次）`
                  : allPushed
                    ? `這個範圍已經拋轉過了（批次 ${pushState.batchNo || '—'}${pushState.ragicNos.length ? `，Ragic 單 ${pushState.ragicNos.join('、')}` : ''}）。週採每期只拋一次；真的要重拋，請先在 Ragic 把單整筆退回，再按「取消拋轉」`
                    : undefined
              }
            >
              <Button
                icon={<CloudUploadOutlined />}
                loading={pushing}
                onClick={handlePushToRagic}
                disabled={!rangePicked || allPushed || periodOverdue}
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
            </>
          )}
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          ...(canBuy ? [{
            key: 'pending',
            label: `待彙整請購單${pendingLoaded ? `（${pendingActionable}${pendingOverdue ? `＋逾期 ${pendingOverdue}` : ''}）` : ''}`,
            children: (
              <>
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                  message="這裡列出全公司「已關閉、尚未彙整」的請購單，依 週期／公司／期別 分組"
                  description="按每組右邊的「產生彙整」會帶好條件打開產生彙整視窗，勾選後產生。還沒關閉的單不在這裡——要先到請購單頁關閉。"
                />
                {pendingError && (
                  <Alert type="error" showIcon style={{ marginBottom: 16 }} message={pendingError} />
                )}
                {pendingLoading && !pendingLoaded && <Card loading style={{ marginBottom: 16 }} />}
                {pendingLoaded && !pendingError && pendingGroups.length === 0 && (
                  <Card style={{ marginBottom: 16 }}>
                    <Text type="secondary">目前沒有待彙整的請購單。</Text>
                  </Card>
                )}
                {pendingGroups.map((g) => (
                  <Card
                    key={g.key}
                    size="small"
                    style={{ marginBottom: 16 }}
                    title={
                      <Space size={8} wrap>
                        <span>{g.cycleName}</span>
                        <Tag>{g.company}</Tag>
                        <Tag color={g.overdue ? 'default' : 'blue'}>{g.period}</Tag>
                        {g.overdue
                          ? <Tag color="red">逾期，不可拋</Tag>
                          : <Text type="secondary" style={{ fontWeight: 400 }}>{g.rows.length} 張待彙整</Text>}
                      </Space>
                    }
                    extra={
                      g.overdue ? (
                        // 2026-09-25（0924 會議第 8 項）：過了當月不能再彙整／拋轉，只留在畫面供查閱
                        <Tooltip title={`期別 ${g.period} 已過，週採每期只在當月彙整、拋轉一次`}>
                          <Button size="small" icon={<SyncOutlined />} disabled>產生彙整</Button>
                        </Tooltip>
                      ) : (
                        <Button
                          type="primary"
                          size="small"
                          icon={<SyncOutlined />}
                          onClick={() => openGenerateFor(g.cycleId, g.company, g.period)}
                        >
                          產生彙整
                        </Button>
                      )
                    }
                  >
                    <Table<CpPendingRequest>
                      dataSource={g.rows}
                      rowKey="id"
                      size="small"
                      pagination={false}
                      loading={pendingLoading}
                      columns={[
                        {
                          title: '請購單號', dataIndex: 'request_no', width: 160,
                          render: (v: string, r) => (
                            <a onClick={() => navigate(`/cycle-purchase/requests/${r.id}`)}>{v}</a>
                          ),
                        },
                        { title: '部門', dataIndex: 'department_name', width: 180, render: (v?: string | null) => v || '—' },
                        {
                          title: '已填品項', dataIndex: 'filled_item_count', width: 90, align: 'right' as const,
                          render: (v: number) => (v === 0 ? <Text type="warning">0（空白單）</Text> : v),
                        },
                        {
                          title: '請購總金額', dataIndex: 'total_amount', width: 120, align: 'right' as const,
                          render: (v: number) => Number(v || 0).toLocaleString(),
                        },
                        {
                          title: '關閉', key: 'closed', width: 220,
                          render: (_: unknown, r) => (
                            <span>
                              {r.close_kind === 'auto' ? '系統自動關閉' : (r.closed_by_name || '—')}
                              {r.closed_at ? <Text type="secondary">　{String(r.closed_at).replace('T', ' ').slice(0, 16)}</Text> : null}
                            </span>
                          ),
                        },
                        {
                          title: '備註', key: 'note',
                          render: (_: unknown, r) => (r.unsummarized_at ? <Tag color="orange">曾從彙整單退回</Tag> : null),
                        },
                      ]}
                    />
                  </Card>
                ))}
              </>
            ),
          }] : []),
          {
            key: 'work',
            label: '彙整作業',
            children: (
              <>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder="選擇週期"
            style={{ width: 200 }}
            allowClear
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

      {!cycleId ? (
        <Card
          title="當月彙整總覽"
          style={{ marginBottom: 16 }}
          extra={
            <Space>
              <Text type="secondary">期別</Text>
              <DatePicker
                picker="month"
                allowClear={false}
                value={overviewMonth ? dayjs(`${overviewMonth}-01`) : null}
                onChange={(d) => setOverviewMonth(d ? d.format('YYYY-MM') : currentYearMonth())}
              />
              <Button onClick={loadOverview}>重新整理</Button>
            </Space>
          }
        >
          <Table
            dataSource={overviewGroups}
            rowKey="key"
            size="small"
            loading={overviewLoading}
            pagination={false}
            locale={{ emptyText: `${overviewMonth} 還沒有任何彙整單` }}
            onRow={(g) => ({ onClick: () => openGroup(g), style: { cursor: 'pointer' } })}
            columns={[
              { title: '公司', dataIndex: 'company', width: 110 },
              { title: '週期', dataIndex: 'cycle_name' },
              { title: '期別', dataIndex: 'period_label', width: 100 },
              { title: '料號數', dataIndex: 'items', width: 80, align: 'right' as const },
              { title: '部門數', dataIndex: 'depts', width: 80, align: 'right' as const },
              { title: '供應商數', dataIndex: 'vendors', width: 90, align: 'right' as const },
              {
                title: '金額（未稅）', dataIndex: 'amount', width: 130, align: 'right' as const,
                render: (v: number) => Math.round(v).toLocaleString(),
              },
              {
                title: '拋轉 Ragic', key: 'pushed', width: 280,
                // 2026-09-25（0924 會議第 4 項）：原本只有「已拋轉（2 張）」，看不出是哪兩張、
                // 是不是自己這次拋的。改成逐張列 Ragic 單號（可點開）＋拋轉時間。
                render: (_: unknown, g: OverviewGroup) => {
                  if (g.pushed === 0) return <Tag>未拋轉</Tag>
                  const head = g.pushed < g.total
                    ? <Tag color="orange">{`部分拋轉 ${g.pushed}/${g.total} 列`}</Tag>
                    : <Tag color="green">{`已拋轉 ${g.ragic_docs.length} 張 Ragic 單`}</Tag>
                  return (
                    <div onClick={(e) => e.stopPropagation()}>
                      {head}
                      {g.ragic_docs.map((d) => (
                        <div key={d.id} style={{ fontSize: 12, marginTop: 2 }}>
                          {d.url
                            ? <a href={d.url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}><LinkOutlined /> {d.id}</a>
                            : <span>{d.id}</span>}
                          {d.at && <Text type="secondary" style={{ fontSize: 12 }}>　{String(d.at).replace('T', ' ').slice(0, 16)}</Text>}
                        </div>
                      ))}
                    </div>
                  )
                },
              },
            ]}
          />
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            點任一列查看該單明細；也可以用上方的週期／期別直接篩選。
          </Text>
        </Card>
      ) : !periodLabel.trim() ? (
        <Alert type="info" showIcon message="請選擇期別" />
      ) : (
        <>
          <Button style={{ marginBottom: 12 }} onClick={backToOverview}>← 返回當月總覽</Button>
          {SHOW_PO_CONVERT && (
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
                    // 2026-09-15 新增。2026-09-18 曾改成依「廠商＋部門」拆單，
                    // 2026-09-20 又改回**只依廠商**（部門逐列放進 Ragic 子表了）。
                    // 但這一欄仍然要把 ragic_docs 全部列出來不能只顯示第一張——
                    // 同一組（公司＋廠商）跨多個批次拋轉時還是會有多張單，
                    // 只顯示第一張的話其他張會靜默消失。
                    // 樣式沿用 CLAUDE.md §7 明細 Drawer 的「在 Ragic 查看」（LinkOutlined ＋ #4BA8E8）。
                    title: 'Ragic 單號',
                    key: 'ragic',
                    width: 210,
                    render: (_: unknown, g: CpVendorGroup) => {
                      const docs = g.ragic_docs ?? []
                      if (!g.ragic_pushed && docs.length === 0) return <Text type="secondary">—</Text>
                      // 舊資料可能沒有 ragic_docs（後端改版前拋轉的），退回單一欄位
                      const list: CpRagicDocRef[] = docs.length > 0
                        ? docs
                        : [{
                            ragic_record_id: g.ragic_record_id,
                            ragic_record_url: g.ragic_record_url,
                            ragic_push_batch_no: g.ragic_push_batch_no,
                            department_name: null,
                          }]
                      return (
                        <Space direction="vertical" size={0}>
                          {list.map((d, i) => {
                            if (!d.ragic_record_id) return null
                            const tip = `批次 ${d.ragic_push_batch_no || '—'}`
                              + (d.department_name ? `／${d.department_name}` : '')
                            // 2026-09-15 之前拋轉的列沒有 ragic_record_url（當時還沒這個欄位），
                            // 這種情況只顯示單號不給連結，不要給一個點了會 404 的假連結。
                            if (!d.ragic_record_url) {
                              return (
                                <Tooltip key={i} title={`${tip}（這張是舊版拋轉，沒有存單筆連結）`}>
                                  <span>{d.ragic_record_id}</span>
                                </Tooltip>
                              )
                            }
                            return (
                              <Tooltip key={i} title={tip}>
                                <a
                                  href={d.ragic_record_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style={{ color: '#4BA8E8', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                                >
                                  <LinkOutlined /> {d.ragic_record_id}
                                  {d.department_name && (
                                    <Text type="secondary" style={{ fontSize: 11 }}>（{d.department_name}）</Text>
                                  )}
                                </a>
                              </Tooltip>
                            )
                          })}
                        </Space>
                      )
                    },
                  },
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
          )}

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
                  // 2026-09-25：沒單價不再擋拋轉，單價與金額在 Ragic 填
                  render: (v?: number | null) => (v == null || Number(v) <= 0
                    ? <Tooltip title="沒有單價：拋轉時送空白，請到 Ragic 填單價與金額"><Text type="secondary">Ragic 填</Text></Tooltip>
                    : Number(v).toLocaleString()),
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
                // 2026-09-22 Samuel 裁示：轉採購單功能隱藏（見 SHOW_PO_CONVERT）
                ...(SHOW_PO_CONVERT ? [
                {
                  title: '採購單號',
                  dataIndex: 'po_no',
                  width: 140,
                  render: (v?: string | null, r?: CpSummary) =>
                    v && r?.po_id ? (
                      <a onClick={() => navigate(`/cycle-purchase/pos/${r.po_id}`)}>{v}</a>
                    ) : '—',
                }
                ] : []),
                {
                  /*
                    2026-09-19：原本只有一顆「已拋轉」Tag，看得出狀態卻看不出
                    **對到 Ragic 哪一張請購單**，使用者要再去別的 TAB 找。
                    這兩個值（ragic_record_id／ragic_record_url）本來就已經寫在
                    每一列上了（見 models/cycle_purchase_summary.py），只是沒顯示。
                    樣式沿用 CLAUDE.md §7 明細 Drawer 的「在 Ragic 查看」
                    （LinkOutlined ＋ 色碼 #4BA8E8 ＋ target="_blank"）。
                  */
                  title: 'Ragic 請購單',
                  dataIndex: 'ragic_pushed',
                  width: 190,
                  render: (v: boolean, r: CpSummary) => {
                    if (!v) return <Text type="secondary">—</Text>
                    const isStub = !!r.ragic_record_id?.startsWith('STUB-')
                    const tip = [
                      r.ragic_push_batch_no ? `批次 ${r.ragic_push_batch_no}` : null,
                      r.ragic_pushed_at ? dayjs(r.ragic_pushed_at).format('YYYY-MM-DD HH:mm') : null,
                    ].filter(Boolean).join('　')
                    if (isStub) {
                      return (
                        <Tooltip title={`${tip}（stub 假資料，Ragic 上沒有對應單據）`}>
                          <Tag color="default">已拋轉（stub）</Tag>
                        </Tooltip>
                      )
                    }
                    // 2026-09-15 之前拋轉的列沒有存 ragic_record_url，只顯示單號，
                    // 不要給一個點了會 404 的假連結
                    if (!r.ragic_record_url) {
                      return (
                        <Tooltip title={`${tip}（舊版拋轉，沒有存單筆連結）`}>
                          <Tag color="blue">{r.ragic_record_id || '已拋轉'}</Tag>
                        </Tooltip>
                      )
                    }
                    return (
                      <Tooltip title={tip}>
                        <a
                          href={r.ragic_record_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: '#4BA8E8', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                        >
                          <LinkOutlined /> {r.ragic_record_id}
                        </a>
                      </Tooltip>
                    )
                  },
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
              </>
            ),
          },
          {
            key: 'pushed',
            label: '已彙整 Ragic 請購單',
            children: (
              <>
                <Card style={{ marginBottom: 16 }}>
                  <Space wrap align="center">
                    <Text type="secondary">拋轉日期</Text>
                    {/* CLAUDE.md §8：共用元件，anchor 傳資料最後一天而不是今天 */}
                    <StandardRangePicker
                      value={pushedRange}
                      anchor={pushedAnchor}
                      onChange={setPushedRange}
                    />
                    <Button icon={<SyncOutlined />} onClick={loadPushed} loading={pushedLoading}>
                      重新整理
                    </Button>
                    {ragicLink && (
                      <a
                        href={ragicLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: '#4BA8E8', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                      >
                        <LinkOutlined /> 在 Ragic 開啟整張表單
                      </a>
                    )}
                  </Space>
                  {/* 2026-09-16 加：測試區與正式區都指向同一張 Ragic 表單（Samuel 裁示
                      維持現狀，不做環境隔離），所以 Ragic 上的單據是**所有環境的聯集**，
                      這份清單必然少於 Ragic 的清單。不寫在畫面上的話，每次有人比對就會
                      當成「資料漏了」回報——2026-09-16 已經發生過一次
                      （Ragic 5 筆 vs 本頁 2 筆，逐筆追出來是 2 筆串接測試單＋1 筆另一個
                      環境推的）。 */}
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      此清單只含<strong>本環境</strong>拋轉的單據，Ragic 上可能另有其他環境推的。
                      要確認某一張是誰推的，看 Ragic 的「拋轉批次號」欄，或比對本環境的週採稽核紀錄。
                    </Text>
                  </div>
                </Card>

                {pushedError && (
                  <Alert
                    type="error"
                    showIcon
                    style={{ marginBottom: 16 }}
                    message="載入失敗，下面的空白不代表沒有資料"
                    description={pushedError}
                  />
                )}

                <Card
                  title={`已拋轉到 Ragic 的請購單（${pushedDocs.length} 張）`}
                  loading={pushedLoading}
                  extra={
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      一列＝Ragic 上的一張請購單；拋轉依「廠商」拆單（一家廠商一張），同一批次會有多張
                    </Text>
                  }
                >
                  <Table<CpRagicPushedDoc>
                    dataSource={pushedDocs}
                    /* ⚠️ 2026-09-18 起拆單含部門，同一批次同一家廠商會有多張
                       Ragic 單，rowKey 少了 ragic_record_id 會撞 key（後端分組鍵
                       也是這三段，見 list_ragic_pushed_documents） */
                    rowKey={(d) =>
                      `${d.ragic_push_batch_no ?? ''}|${d.vendor_id ?? 'none'}|${d.ragic_record_id ?? ''}`}
                    size="small"
                    scroll={{ x: 1200 }}
                    locale={{
                      emptyText: pushedRange
                        ? '這段期間沒有拋轉過任何單據（可切換成「全部」看看）'
                        : '這台 Portal 還沒有任何已拋轉的單據。'
                          + 'Ragic 上看得到的單不一定會在這裡——直接打 Ragic API 建的測試單'
                          + '（批次號 TEST- 開頭）、或別台 Portal 推的單都不會列入。',
                    }}
                    columns={[
                      {
                        title: 'Ragic 單號',
                        key: 'no',
                        width: 170,
                        fixed: 'left' as const,
                        render: (_: unknown, d: CpRagicPushedDoc) => {
                          if (d.is_stub) {
                            return (
                              <Tooltip title="這筆是 2026-09-15 正式串接前的 stub 假資料，Ragic 上沒有對應單據">
                                <Tag color="default">stub</Tag>
                              </Tooltip>
                            )
                          }
                          if (!d.ragic_record_id) return <Text type="secondary">—</Text>
                          // 2026-09-15 之前拋轉的沒有存單筆網址，只顯示單號不給連結，
                          // 不要給一個點了會 404 的假連結
                          if (!d.ragic_record_url) {
                            return (
                              <Tooltip title="這張是舊版拋轉，沒有存單筆連結；可用右上角開整張表單再自行搜尋">
                                <span>{d.ragic_record_id}</span>
                              </Tooltip>
                            )
                          }
                          return (
                            <a
                              href={d.ragic_record_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: '#4BA8E8', display: 'inline-flex', alignItems: 'center', gap: 3 }}
                            >
                              <LinkOutlined /> {d.ragic_record_id}
                            </a>
                          )
                        },
                      },
                      {
                        title: '拋轉時間',
                        dataIndex: 'pushed_at',
                        width: 150,
                        sorter: (a: CpRagicPushedDoc, b: CpRagicPushedDoc) =>
                          (a.pushed_at || '').localeCompare(b.pushed_at || ''),
                        defaultSortOrder: 'descend' as const,
                        render: (v: string) => (v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '—'),
                      },
                      { title: '公司', dataIndex: 'company', width: 90 },
                      { title: '週期', dataIndex: 'cycle_name', width: 170, render: (v: string) => v || '—' },
                      { title: '期別', dataIndex: 'period_label', width: 90 },
                      {
                        title: '廠商',
                        dataIndex: 'vendor_name',
                        width: 140,
                        render: (v: string) => v || <Text type="secondary">—</Text>,
                      },
                      {
                        title: '部門',
                        key: 'depts',
                        width: 150,
                        render: (_: unknown, d: CpRagicPushedDoc) =>
                          d.department_names?.length
                            ? d.department_names.join('、')
                            : <Text type="secondary">—</Text>,
                      },
                      {
                        // 2026-09-25（0924 會議第 4 項）：這張 Ragic 單是由哪幾張請購單彙整來的
                        title: '包含請購單',
                        key: 'request_nos',
                        width: 170,
                        render: (_: unknown, d: CpRagicPushedDoc) =>
                          d.request_nos?.length
                            ? <span style={{ fontSize: 12 }}>{d.request_nos.join('、')}</span>
                            : <Text type="secondary">—</Text>,
                      },
                      { title: '料號筆數', dataIndex: 'item_count', width: 90, align: 'right' as const },
                      { title: '總數量', dataIndex: 'total_qty', width: 90, align: 'right' as const },
                      {
                        title: '金額（未稅）',
                        dataIndex: 'total_amount',
                        width: 130,
                        align: 'right' as const,
                        sorter: (a: CpRagicPushedDoc, b: CpRagicPushedDoc) =>
                          Number(a.total_amount) - Number(b.total_amount),
                        render: (v: number) => Number(v).toLocaleString(),
                      },
                      ...(SHOW_PO_CONVERT ? [
                      {
                        // 讓使用者一眼看出這張單的流程走到哪：拋轉只是送到 Ragic，
                        // 轉採購單是 Portal 這邊的下一步，兩件事互相獨立
                        title: '轉採購單',
                        key: 'converted',
                        width: 110,
                        render: (_: unknown, d: CpRagicPushedDoc) =>
                          d.all_converted
                            ? <Tag color="green">已全數轉單</Tag>
                            : d.converted_count > 0
                              ? <Tag color="blue">{`部分 ${d.converted_count}/${d.item_count}`}</Tag>
                              : <Tag>未轉單</Tag>,
                      }
                      ] : []),
                      {
                        title: '拋轉批次號',
                        dataIndex: 'ragic_push_batch_no',
                        width: 220,
                        render: (v: string) => v || '—',
                      },
                    ]}
                  />
                </Card>
              </>
            ),
          },
        ]}
      />

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

        {genCycleId && genCompany && genMonth && excludedRequests.length > 0 && (() => {
          const pushedN = excludedRequests.filter((x) => x.flow_status === 'pushed').length
          return (
            <Alert
              type={eligibleRequests.length === 0 ? 'warning' : 'info'}
              showIcon
              style={{ marginBottom: 12 }}
              message={
                `這個範圍另有 ${excludedRequests.length} 張請購單已經彙整過`
                + (pushedN ? `（其中 ${pushedN} 張已拋轉 Ragic）` : '')
                + '，所以不會出現在下面的清單'
              }
              description={
                <div>
                  <div style={{ fontSize: 12 }}>
                    {excludedRequests.map((x) =>
                      `${x.request_no}${x.department_name ? `（${x.department_name}）` : ''}${x.flow_status === 'pushed' ? '・已拋轉' : '・已彙整'}`,
                    ).join('、')}
                  </div>
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    週採每一期只拋轉一次。已拋轉的單若真的要重做，要先在 Ragic 整筆退回，再到彙整作業按「取消拋轉」→「退回請購單」。
                  </div>
                </div>
              }
            />
          )
        })()}
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
