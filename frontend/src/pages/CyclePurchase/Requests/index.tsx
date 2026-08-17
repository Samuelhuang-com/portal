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
 * POST /requests 備用路徑。2026-08-17 起同一週期＋期別＋部門允許有多張單
 * （不再擋，只提醒，見下方 2026-08-17 說明），彙整時會自動加總同部門的
 * 多張單，不會漏算。
 *
 * 2026-07-17（第三次調整，請購單流程大改版，與 Samuel 確認）：
 * 拿掉送出／核准／退回。期別（period_label）不再由使用者輸入，一律由後端
 * 在建立當下蓋章為現在的月份，因此「產生本期請購單」與「新增請購單」都不
 * 再有期別輸入欄位。新增「關閉」功能（全部關閉／勾選關閉），關閉當月的
 * 請購單，關閉後不能再新增/編輯明細；也支援「重新開啟」已關閉的請購單。
 *
 * 2026-08-07（第四次調整，與 Samuel 確認）：
 * 新增「狀態」篩選（開放中／已關閉（人工）／關閉（系統）），對應後端的
 * close_state 參數。三選而非二選，是因為只分「開放中／已關閉」就回答不了
 * 「哪些單是沒人管、被系統關掉的」。沒有 close／view 權限的人看不到這個篩選器
 * ——他們的清單本來就只有開放中的單（後端硬過濾），顯示只會造成困惑。
 * 同時把期別下拉的選項改成累積式，否則篩了狀態之後期別選項會跟著縮水。
 *
 * 2026-08-08：表格最後加「最後更新」欄位（YYYY-MM-DD HH:mm，可排序）。
 * 這一頁是即時儲存，所以這個欄位等同於「最後有人動這張單是什麼時候」。
 * 後端 `_recompute_total()` 每次明細異動都會明確蓋 `updated_at`，
 * 不依賴 Column 的 onupdate（走 bulk update 時不一定會觸發）。
 *
 * 2026-08-08：狀態篩選**預設「開放中」**。日常最常做的事是「看這個月還有誰沒填」，
 * 預設全部會讓歷史的已關閉單淹沒當期的單，而且會越積越多。要看歷史就把篩選
 * 清掉（allowClear）或切到其他選項。連帶把期別下拉的初始選項用
 * `recentMonthOptions(6)` 墊底——否則第一次載入只會回傳當月的單，期別下拉
 * 就只剩當月，使用者得先去改狀態篩選才選得到上個月。
 *
 * 2026-08-09（部門範圍 + 品類接線，與 Samuel 確認；規格見
 * docs/SPEC_cycle_purchase_dept_scope.md）：
 * 「產生本期請購單」不再是「該公司底下每個啟用中部門都建一張」。實際會產生的
 * 範圍變成：適用公司 ∩ 適用部門 ∩「該週期品類下有啟用中料號的部門」。
 *  - 選完週期後**立刻顯示預覽**（GET /requests/generate-preview）：會產生哪些
 *    部門、哪些部門不會產生與原因。按下去之前就看得到結果，不用先產生再猜。
 *  - `generateRequestsForPeriod` 的回傳型別從 `CpRequest[]` 改成
 *    `{ requests, skipped }`。skipped 一定要顯示給使用者——買家看到「怎麼少了
 *    一張單」卻沒有任何說明的話，只會以為系統壞了。
 *
 * 2026-08-17（放寬手動新增的擋重，與 Samuel 確認）：「新增請購單」原本查到
 * 同週期＋期別＋部門已有一張單就拋錯擋掉，理由是當時 DB 有對應的
 * UniqueConstraint。該限制已於 2026-08-13（複製上期請購單功能）拿掉，DB 層
 * 本來就允許同部門同期多張單並存，這裡的擋重只是 app 層殘留的舊規則。改成
 * **只提醒不擋**：後端查到已有其他單會在 `createRequest` 的回傳多帶
 * `duplicate_warning` 文字，前端改用 `message.warning` 提示，單子照樣建立
 * 成功；彙整單那邊 `generate_summary_from_requests()` 本來就是撈同部門所有
 * 請購單加總數量，天然支援多張單，不需要跟著改。
 *
 * 2026-08-17（週期下拉排除停用／暫停）：`cycles`（頁面上方的 GET /cycles，
 * 不帶 status 篩選）保留給「篩選清單」跟「關閉請購單」用——這兩個是在
 * 看/清理已經存在的舊資料，週期就算後來被停用，過去掛在它底下的單還是要
 * 篩得到、關得掉。但「新增請購單」「產生本期請購單」「複製上期請購單」都是
 * 要建立新的請購行為，改用 `activeCycles`（前端過濾 `status === 'active'`）
 * 只給啟用中的週期選，不然選到已經停用的舊週期會建出沒人管的單。
 */
import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Modal, Select, Space, Table, Tag, Tooltip, Typography, message } from 'antd'
import {
  CopyOutlined, DeleteOutlined, EditOutlined, EyeOutlined, ExclamationCircleOutlined,
  LockOutlined, PlusOutlined, ThunderboltOutlined, UnlockOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import {
  closeAllRequests, closeRequests, copyRequest, createRequest, deleteRequest, generateRequestsForPeriod,
  getCopySourceCandidates, getCpDepartments, getCycles, getOpenRequestsForClose, getRequests,
  previewGenerateRequests, reopenRequests,
} from '@/api/cyclePurchase'
import type {
  CpCloseState, CpCopySourceCandidate, CpCycle, CpDepartment, CpGeneratePreview, CpRequest,
} from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'
import CloseStatusTag from '../components/CloseStatusTag'

const { Title, Text } = Typography

// 2026-07-17：拿掉送出/核准狀態機，狀態欄位只剩改版前的歷史殘留值（新資料
// 一律是 draft），畫面改用 is_closed 判斷開放中／已關閉，不再需要狀態對照表。
// 2026-08-07：狀態欄改用共用的 CloseStatusTag，區分人工關閉（灰「已關閉」）
// 與系統自動關閉（淺粉「關閉」）。另外，沒有 cycle_purchase_close／
// cycle_purchase_view 權限的人，**後端就不會回傳已關閉的單**，所以這個清單
// 對他們而言只會有「開放中」——前端不需要（也不應該）再做一次過濾。

// 「狀態」篩選選項（2026-08-07 新增）。
// 刻意分成人工／系統兩種關閉，與清單上的標籤一一對應——只分「開放中／已關閉」
// 的話，就沒辦法回答「哪些單是沒人管、被系統關掉的」這個問題。
// ⚠️ 不要改用 CpRequest.status 做篩選：那是改版前的殘留欄位（新資料一律 draft）。
const CLOSE_STATE_OPTIONS: { label: string; value: CpCloseState }[] = [
  { label: '開放中', value: 'open' },
  { label: '已關閉（人工）', value: 'closed_manual' },
  { label: '關閉（系統）', value: 'closed_auto' },
]

function currentYearMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function recentMonthOptions(count = 6) {
  const opts: string[] = []
  const now = new Date()
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    opts.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`)
  }
  return opts
}

/**
 * 後端回傳的 ISO 時間字串 → `YYYY-MM-DD HH:mm`（2026-08-08 新增）。
 *
 * 用字串切割而不是 `new Date()`：後端存的是**本地時間**（`datetime.now()`，
 * 不帶時區資訊），丟給 Date 解析再 format 會被當成 UTC 而位移 8 小時。
 * 直接切字串反而是正確的——顯示的就是資料庫裡實際的那個時間。
 */
function formatDateTime(v?: string | null): string {
  if (!v) return '—'
  // "2026-08-08T14:32:05.123456" → "2026-08-08 14:32"
  const [d, t] = v.split('T')
  if (!t) return d || '—'
  return `${d} ${t.slice(0, 5)}`
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpRequestsPage() {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('cycle_purchase_request')
  const canCreate = hasPermission('cycle_purchase_buyer')
  const canClose = hasPermission('cycle_purchase_close')
  // 後端對「已關閉的單」有硬過濾：沒有 close／view 權限的人清單裡只會有開放中的單。
  // 這種人看到狀態篩選器只會困惑（選了「已關閉」永遠是空的，容易被當成 bug 回報），
  // 所以整個藏起來。判斷條件要與後端 _can_see_closed() 保持一致。
  const canSeeClosed = canClose || hasPermission('cycle_purchase_view')

  const [rows, setRows] = useState<CpRequest[]>([])
  const [cycles, setCycles] = useState<CpCycle[]>([])
  const [departments, setDepartments] = useState<CpDepartment[]>([])
  const [cycleId, setCycleId] = useState<number | undefined>(undefined)
  const [periodLabel, setPeriodLabel] = useState<string | undefined>(undefined)
  // 2026-08-08：預設「開放中」。日常最常做的事是「看這個月還有誰沒填」，
  // 預設全部會讓歷史的已關閉單淹沒當期的單（而且會越積越多）。
  // 要看歷史就把篩選清掉或切到其他選項。
  const [closeState, setCloseState] = useState<CpCloseState | undefined>('open')
  // 期別下拉的選項（累積式，只增不減；理由見 load()）。
  // 2026-08-08：初始值先放最近 6 個月墊底。因為狀態篩選預設是「開放中」，
  // 第一次載入通常只會回傳當月的單，期別下拉就只剩當月——使用者會找不到
  // 「上個月」可選，還得先去改狀態篩選才行。沿用既有的 recentMonthOptions()，
  // 不必為此多打一支 API。
  const [periodOptions, setPeriodOptions] = useState<string[]>(() => recentMonthOptions(6))
  const [loading, setLoading] = useState(false)

  const [createModal, setCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createCycleId, setCreateCycleId] = useState<number | undefined>(undefined)
  const [createDeptId, setCreateDeptId] = useState<number | undefined>(undefined)

  // 2026-08-13 新增：複製上期請購單
  const [copyModal, setCopyModal] = useState(false)
  const [copying, setCopying] = useState(false)
  const [copyCycleId, setCopyCycleId] = useState<number | undefined>(undefined)
  const [copyDeptId, setCopyDeptId] = useState<number | undefined>(undefined)
  const [copyCandidates, setCopyCandidates] = useState<CpCopySourceCandidate[]>([])
  const [copyCandidatesLoading, setCopyCandidatesLoading] = useState(false)
  const [copySourceId, setCopySourceId] = useState<number | undefined>(undefined)

  const [generateModal, setGenerateModal] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generateCycleId, setGenerateCycleId] = useState<number | undefined>(undefined)
  // 2026-08-09：選完週期就先預覽「會產生哪些部門」，不用產生完才知道結果
  const [genPreview, setGenPreview] = useState<CpGeneratePreview | null>(null)
  const [genPreviewLoading, setGenPreviewLoading] = useState(false)

  // 關閉功能
  const [closeModal, setCloseModal] = useState(false)
  const [closing, setClosing] = useState(false)
  const [closeCycleId, setCloseCycleId] = useState<number | undefined>(undefined)
  const [closeCompany, setCloseCompany] = useState<string | undefined>(undefined)
  const [closeMonth, setCloseMonth] = useState<string>(currentYearMonth())
  const [openRequests, setOpenRequests] = useState<CpRequest[]>([])
  const [loadingOpen, setLoadingOpen] = useState(false)
  const [selectedCloseIds, setSelectedCloseIds] = useState<number[]>([])

  // 2026-08-17：`cycles`（全部狀態，含停用／暫停）留給「篩選清單」跟「關閉請購單」
  // 用——這兩個是在看/清理已經存在的舊資料，就算週期後來被停用，過去掛在
  // 它底下的單還是要篩得到、關得掉。但「新增請購單」「產生本期請購單」
  // 「複製上期請購單」這三個都是要建立新的請購行為，停用/暫停的週期選了也
  // 只會撞後端擋掉或建出沒人管的單，下拉選項只給啟用中的週期。
  const activeCycles = useMemo(() => cycles.filter((c) => c.status === 'active'), [cycles])

  const load = () => {
    setLoading(true)
    Promise.all([
      getRequests({ cycle_id: cycleId, period_label: periodLabel, close_state: closeState }),
      getCycles(),
      getCpDepartments({ is_active: true }),
    ])
      .then(([rRes, cRes, dRes]) => {
        setRows(rRes.data)
        setCycles(cRes.data)
        setDepartments(dRes.data)
        // 期別選項用「累積」而不是「當下 rows 現有的值」。
        // 原本是直接從 rows 推導，篩了狀態之後期別選項會跟著縮水——例如選了
        // 「開放中」，期別下拉就只剩當月，使用者反而選不回其他月份，等於把自己
        // 鎖在角落。累積式的選項只會增加不會減少，不需要為此多打一支 API。
        setPeriodOptions((prev) => {
          const merged = new Set(prev)
          rRes.data.forEach((r) => r.period_label && merged.add(r.period_label))
          return Array.from(merged).sort().reverse()
        })
      })
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [cycleId, periodLabel, closeState])

  const openCreate = () => {
    setCreateCycleId(undefined)
    setCreateDeptId(undefined)
    setCreateModal(true)
  }

  const handleCreate = async () => {
    if (!createCycleId || !createDeptId) { message.warning('請選擇週期與部門'); return }
    try {
      setCreating(true)
      const created = await createRequest({ cycle_id: createCycleId, department_id: createDeptId })
      // 2026-08-17：同部門本期已有單不再擋，只是提醒——後端查到會在
      // duplicate_warning 帶警告文字，這裡改用 warning 而不是 error 提示，
      // 因為單子已經建立成功了。
      if (created.data.duplicate_warning) {
        message.warning(created.data.duplicate_warning, 6)
      } else {
        message.success('已建立請購單')
      }
      setCreateModal(false)
      load()
      navigate(`/cycle-purchase/requests/${created.data.id}`)
    } catch (err: any) {
      message.error(errMsg(err, '建立失敗'))
    } finally {
      setCreating(false)
    }
  }

  const openCopy = () => {
    setCopyCycleId(undefined)
    setCopyDeptId(undefined)
    setCopyCandidates([])
    setCopySourceId(undefined)
    setCopyModal(true)
  }

  // 選完週期＋部門就抓可複製的來源清單（依 period_label 新到舊排序，只列有
  // 明細的單）。協理要求可以自由選任一過去期別，所以是下拉清單而不是只帶
  // 最近一次。
  useEffect(() => {
    if (!copyModal || !copyCycleId || !copyDeptId) {
      setCopyCandidates([])
      setCopySourceId(undefined)
      return
    }
    setCopyCandidatesLoading(true)
    getCopySourceCandidates({ cycle_id: copyCycleId, department_id: copyDeptId })
      .then((res) => {
        setCopyCandidates(res.data)
        setCopySourceId(res.data[0]?.id)
      })
      .catch((err) => message.error(errMsg(err, '載入可複製的請購單失敗')))
      .finally(() => setCopyCandidatesLoading(false))
  }, [copyModal, copyCycleId, copyDeptId])

  const handleCopy = async () => {
    if (!copySourceId) { message.warning('請選擇要複製的請購單'); return }
    setCopying(true)
    try {
      const res = await copyRequest(copySourceId)
      const { request, skipped_items } = res.data
      message.success(`已複製為新請購單 ${request.request_no}`)
      // 跳過的品項一定要講清楚，不能讓使用者以為自己複製全了
      if (skipped_items.length) {
        Modal.warning({
          title: `有 ${skipped_items.length} 個品項無法複製`,
          width: 560,
          content: (
            <Table
              dataSource={skipped_items}
              rowKey="item_code"
              size="small"
              pagination={false}
              style={{ marginTop: 12 }}
              columns={[
                { title: '料號', dataIndex: 'item_code', width: 120 },
                { title: '品名', dataIndex: 'item_name' },
                { title: '原因', dataIndex: 'reason' },
              ]}
            />
          ),
        })
      }
      setCopyModal(false)
      load()
      navigate(`/cycle-purchase/requests/${request.id}`)
    } catch (err: any) {
      message.error(errMsg(err, '複製失敗'))
    } finally {
      setCopying(false)
    }
  }

  const openGenerate = () => {
    setGenerateCycleId(undefined)
    setGenPreview(null)
    setGenerateModal(true)
  }

  /** 選完週期就抓預覽：會產生哪些部門、哪些不會與原因 */
  const handleGenerateCycleChange = async (id: number) => {
    setGenerateCycleId(id)
    setGenPreview(null)
    setGenPreviewLoading(true)
    try {
      const res = await previewGenerateRequests(id)
      setGenPreview(res.data)
    } catch (err: any) {
      // 預覽失敗不擋操作（後端仍會擋不合法的產生），但要講清楚預覽拿不到
      message.warning(errMsg(err, '無法取得預覽'))
    } finally {
      setGenPreviewLoading(false)
    }
  }

  const handleGenerate = async () => {
    if (!generateCycleId) { message.warning('請選擇週期'); return }
    try {
      setGenerating(true)
      const res = await generateRequestsForPeriod({ cycle_id: generateCycleId })
      const { requests, skipped } = res.data
      message.success(`已產生（或確認既有）${requests.length} 張本期請購單`)
      // 沒產生的部門一定要講原因，否則使用者只會覺得「怎麼少了一張」
      if (skipped.length) {
        Modal.info({
          title: `有 ${skipped.length} 個部門沒有產生請購單`,
          width: 560,
          content: (
            <Table
              dataSource={skipped}
              rowKey="department_id"
              size="small"
              pagination={false}
              style={{ marginTop: 12 }}
              columns={[
                { title: '公司', dataIndex: 'company', width: 100, render: (v: string | null) => v || '—' },
                { title: '部門', dataIndex: 'department_name', width: 130 },
                { title: '原因', dataIndex: 'reason' },
              ]}
            />
          ),
        })
      }
      setGenerateModal(false)
      setCycleId(generateCycleId)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '產生失敗'))
    } finally {
      setGenerating(false)
    }
  }

  const openCloseModal = () => {
    setCloseCycleId(cycleId)
    setCloseCompany(undefined)
    setCloseMonth(currentYearMonth())
    setOpenRequests([])
    setSelectedCloseIds([])
    setCloseModal(true)
  }

  useEffect(() => {
    if (!closeModal || !closeCycleId || !closeMonth) { setOpenRequests([]); return }
    setLoadingOpen(true)
    getOpenRequestsForClose({ cycle_id: closeCycleId, company: closeCompany, year_month: closeMonth })
      .then((res) => {
        setOpenRequests(res.data)
        setSelectedCloseIds(res.data.map((r) => r.id))
      })
      .catch((err) => message.error(errMsg(err, '載入開放中請購單失敗')))
      .finally(() => setLoadingOpen(false))
  }, [closeModal, closeCycleId, closeCompany, closeMonth])

  const handleCloseSelected = async () => {
    if (selectedCloseIds.length === 0) { message.warning('請至少勾選一張請購單'); return }
    setClosing(true)
    try {
      const res = await closeRequests(selectedCloseIds)
      message.success(`已關閉 ${res.data.length} 張請購單`)
      setCloseModal(false)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '關閉失敗'))
    } finally {
      setClosing(false)
    }
  }

  const handleCloseAll = async () => {
    if (!closeCycleId) { message.warning('請選擇週期'); return }
    setClosing(true)
    try {
      const res = await closeAllRequests({ cycle_id: closeCycleId, company: closeCompany, year_month: closeMonth })
      message.success(`已全部關閉，共 ${res.data.length} 張請購單`)
      setCloseModal(false)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '全部關閉失敗'))
    } finally {
      setClosing(false)
    }
  }

  const handleReopen = async (row: CpRequest) => {
    try {
      await reopenRequests([row.id])
      message.success(`已重新開啟 ${row.request_no}`)
      load()
    } catch (err: any) {
      message.error(errMsg(err, '重新開啟失敗'))
    }
  }

  // 2026-08-17 新增：刪除請購單。後端只放行「明細 0 筆＋未關閉＋未彙整」的空白單，
  // 前端不預先算 item_count（清單 API 沒帶這個欄位），有明細/已關閉/已彙整時
  // 後端會回清楚的錯誤原因，直接顯示給使用者，不用前端另外猜。
  const handleDelete = (row: CpRequest) => {
    Modal.confirm({
      title: `確定要刪除「${row.request_no}」？`,
      icon: <ExclamationCircleOutlined />,
      content: '只有明細 0 筆、未關閉、未彙整的空白單才能刪除；如果這張單其實有明細，會顯示原因並取消刪除。',
      okText: '刪除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteRequest(row.id)
          message.success(`已刪除 ${row.request_no}`)
          load()
        } catch (err: any) {
          message.error(errMsg(err, '刪除失敗'))
        }
      },
    })
  }

  const companyOptions = Array.from(new Set(departments.map((d) => d.company))).map((c) => ({ label: c, value: c }))

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>週期採購 — 請購單</Title>
        <Space>
          {canClose && (
            <Button icon={<LockOutlined />} onClick={openCloseModal}>關閉請購單</Button>
          )}
          {canCreate && (
            <Button icon={<ThunderboltOutlined />} onClick={openGenerate}>產生本期請購單</Button>
          )}
          {canCreate && (
            <Button icon={<CopyOutlined />} onClick={openCopy}>複製上期請購單</Button>
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
            options={periodOptions.map((p) => ({ label: p, value: p }))}
          />
          {canSeeClosed && (
            <Select
              allowClear
              placeholder="依狀態篩選"
              style={{ width: 160 }}
              value={closeState}
              onChange={setCloseState}
              options={CLOSE_STATE_OPTIONS}
            />
          )}
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
              key: 'is_closed',
              width: 90,
              render: (_: unknown, r: CpRequest) => (
                <CloseStatusTag
                  isClosed={r.is_closed}
                  closeKind={r.close_kind}
                  periodLabel={r.period_label}
                />
              ),
            },
            {
              // 2026-08-09 新增。改版前「已關閉且已彙整」「已關閉但還沒彙整」
              // 「彙整過又被退回」三種狀態在清單上長得一模一樣（都只有「已關閉」），
              // 但處置方式完全不同——第一種不用管、第二種要記得去彙整、第三種要去
              // 追為什麼被退。所以彙整獨立成一欄，不跟「狀態」（開放／關閉）混在一起。
              title: '彙整',
              key: 'is_summarized',
              width: 130,
              render: (_: unknown, r: CpRequest) => (
                <Space size={4} wrap>
                  {r.is_summarized ? (
                    <Tooltip
                      title={[
                        r.summary_batch_no ? `批次 ${r.summary_batch_no}` : null,
                        r.summarized_at ? `彙整於 ${formatDateTime(r.summarized_at)}` : null,
                      ].filter(Boolean).join('　') || undefined}
                    >
                      <Tag color="green" style={{ marginInlineEnd: 0 }}>已彙整</Tag>
                    </Tooltip>
                  ) : r.unsummarized_at ? (
                    <Tooltip
                      title={[
                        `退回於 ${formatDateTime(r.unsummarized_at)}`,
                        r.unsummarized_by_name ? `退回人 ${r.unsummarized_by_name}` : null,
                        r.unsummarize_reason ? `原因：${r.unsummarize_reason}` : null,
                      ].filter(Boolean).join('　')}
                    >
                      <Tag color="purple" style={{ marginInlineEnd: 0 }}>已退回彙整</Tag>
                    </Tooltip>
                  ) : (
                    <Text type="secondary">—</Text>
                  )}
                  {/* 已經重新彙整回去的，仍保留一個淡色「曾退回」痕跡：
                      目前狀態看前一個標籤，這個只表示這張單有過狀況、值得留意。 */}
                  {r.is_summarized && r.unsummarized_at && (
                    <Tooltip
                      title={[
                        `曾於 ${formatDateTime(r.unsummarized_at)} 被退回，之後又重新彙整`,
                        r.unsummarize_reason ? `當時原因：${r.unsummarize_reason}` : null,
                      ].filter(Boolean).join('　')}
                    >
                      <Tag style={{ marginInlineEnd: 0 }}>曾退回</Tag>
                    </Tooltip>
                  )}
                </Space>
              ),
            },
            { title: '填寫人', dataIndex: 'submitted_by_name', width: 100, render: (v?: string | null) => v || '—' },
            {
              title: '關閉人',
              dataIndex: 'closed_by_name',
              width: 100,
              // 系統自動關閉沒有經手人，顯示「系統」而不是「—」，
              // 否則看起來像資料缺漏
              render: (v: string | null | undefined, r: CpRequest) =>
                v || (r.close_kind === 'auto' ? '系統' : '—'),
            },
            {
              title: '最後更新',
              dataIndex: 'updated_at',
              width: 140,
              // 最後一次存檔的時間。這一頁是即時儲存（改一格存一格），所以這個
              // 欄位等同於「最後有人動這張單是什麼時候」。
              // 後端 _recompute_total() 會在每次明細異動時明確蓋 updated_at，
              // 不依賴 Column onupdate（bulk update 不一定會觸發）。
              sorter: (a: CpRequest, b: CpRequest) =>
                (a.updated_at || '').localeCompare(b.updated_at || ''),
              render: (v?: string | null) => formatDateTime(v),
            },
            {
              title: '操作',
              key: 'actions',
              width: 220,
              render: (_: unknown, r: CpRequest) => (
                <Space size="small">
                  <Button
                    size="small"
                    icon={canEdit && !r.is_closed ? <EditOutlined /> : <EyeOutlined />}
                    onClick={() => navigate(`/cycle-purchase/requests/${r.id}`)}
                  >
                    {canEdit && !r.is_closed ? '填寫' : '檢視'}
                  </Button>
                  {canClose && r.is_closed && (
                    <Button size="small" icon={<UnlockOutlined />} onClick={() => handleReopen(r)}>重新開啟</Button>
                  )}
                  {canEdit && !r.is_closed && !r.is_summarized && (
                    <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r)}>刪除</Button>
                  )}
                </Space>
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
        width={620}
        okButtonProps={{ disabled: !!genPreview && genPreview.departments.length === 0 }}
      >
        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>週期</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇週期"
            value={generateCycleId}
            onChange={handleGenerateCycleChange}
            options={activeCycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
        </div>
        <div style={{ color: '#888', fontSize: 12 }}>
          會依週期設定的「適用公司 ∩ 適用部門 ∩ 該品類下有啟用中料號的部門」，
          為每個適用部門建立一張本月（{currentYearMonth()}）的空白請購單（已存在的不會重複建立）。
        </div>

        {/* 2026-08-09：產生前預覽 —— 按下去之前就看得到會產生哪些部門 */}
        {genPreviewLoading && (
          <div style={{ marginTop: 16, color: '#888', fontSize: 12 }}>預覽計算中…</div>
        )}
        {genPreview && (
          <div style={{ marginTop: 16 }}>
            {genPreview.departments.length > 0 ? (
              <Alert
                type="success"
                showIcon
                message={`將產生 ${genPreview.departments.length} 個部門的請購單`}
                description={
                  <div style={{ marginTop: 4 }}>
                    {genPreview.departments.map((d) => (
                      <Tag key={d.department_id} style={{ marginBottom: 4 }}>
                        {d.company} / {d.department_name}
                      </Tag>
                    ))}
                  </div>
                }
              />
            ) : (
              <Alert
                type="warning"
                showIcon
                message="這個週期目前沒有任何可產生的部門"
                description="請回「週期設定」確認適用公司／適用部門／適用品類，以及料號主檔的部門歸屬。"
              />
            )}

            {genPreview.skipped.length > 0 && (
              <Alert
                type="info"
                showIcon
                style={{ marginTop: 12 }}
                message={`有 ${genPreview.skipped.length} 個部門不會產生`}
                description={
                  <div style={{ marginTop: 4, maxHeight: 160, overflowY: 'auto' }}>
                    {genPreview.skipped.map((sk) => (
                      <div key={sk.department_id} style={{ fontSize: 12 }}>
                        · {sk.company ? `${sk.company} / ` : ''}{sk.department_name}：{sk.reason}
                      </div>
                    ))}
                  </div>
                }
              />
            )}
          </div>
        )}
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
        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>週期</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇週期"
            value={createCycleId}
            onChange={setCreateCycleId}
            options={activeCycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>部門</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇部門"
            value={createDeptId}
            onChange={setCreateDeptId}
            options={departments.map((d) => ({ label: `${d.company} - ${d.dept_name}`, value: d.id }))}
          />
        </div>
        <div style={{ color: '#888', fontSize: 12 }}>
          會建立本月（{currentYearMonth()}）的請購單。同一週期＋期別＋部門就算已經有單
          （含「產生本期請購單」已經建過的），也可以再手動新增一張，不會被擋，
          只會提醒你已有既有單號；彙整時同部門的多張單會自動加總，不會漏算。
          週期下拉只列出「啟用中」的週期，停用／暫停的不會出現在這裡。
        </div>
      </Modal>

      <Modal
        title="複製上期請購單"
        open={copyModal}
        onOk={handleCopy}
        onCancel={() => setCopyModal(false)}
        okText="複製"
        cancelText="取消"
        confirmLoading={copying}
        okButtonProps={{ disabled: !copySourceId }}
        width={560}
      >
        <div style={{ marginTop: 16, marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>週期</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇週期"
            value={copyCycleId}
            onChange={(v) => { setCopyCycleId(v); setCopyDeptId(undefined) }}
            options={activeCycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <div style={{ marginBottom: 4 }}>部門</div>
          <Select
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇部門"
            value={copyDeptId}
            onChange={setCopyDeptId}
            options={departments.map((d) => ({ label: `${d.company} - ${d.dept_name}`, value: d.id }))}
          />
        </div>
        {copyCycleId && copyDeptId && (
          <div style={{ marginBottom: 8 }}>
            <div style={{ marginBottom: 4 }}>選擇要複製的請購單（依期別新到舊排序）</div>
            <Select
              style={{ width: '100%' }}
              loading={copyCandidatesLoading}
              placeholder="選擇來源請購單"
              value={copySourceId}
              onChange={setCopySourceId}
              notFoundContent={copyCandidatesLoading ? '載入中…' : '這個週期＋部門目前沒有可複製的請購單'}
              options={copyCandidates.map((c) => ({
                label: `${c.period_label}／${c.request_no}（${c.item_count} 項，$${c.total_amount}）${c.is_closed ? '' : '（開放中）'}`,
                value: c.id,
              }))}
            />
          </div>
        )}
        <div style={{ color: '#888', fontSize: 12 }}>
          會建立一張本月（{currentYearMonth()}）的新請購單，把來源單的品項與數量整批帶過來
          （單價會重新抓現在的價格）。就算本月已經有單也可以複製，不會受影響、也不會改到原本的單。
          停用或已不屬於這個部門的料號會被跳過，複製完成後會列出來提醒你。
          下拉選單只會列出「這個週期＋這個部門」過去曾經填過至少一個品項的請購單，空白單不會出現。
        </div>
      </Modal>

      <Modal
        title="關閉請購單"
        open={closeModal}
        onCancel={() => setCloseModal(false)}
        width={720}
        footer={[
          <Button key="cancel" onClick={() => setCloseModal(false)}>取消</Button>,
          <Button key="all" danger loading={closing} onClick={handleCloseAll}>全部關閉</Button>,
          <Button key="selected" type="primary" loading={closing} onClick={handleCloseSelected}>
            關閉勾選（{selectedCloseIds.length}）
          </Button>,
        ]}
      >
        <Space style={{ marginBottom: 12 }} wrap>
          <Select
            style={{ width: 200 }}
            showSearch
            optionFilterProp="label"
            placeholder="選擇週期"
            value={closeCycleId}
            onChange={setCloseCycleId}
            options={cycles.map((c) => ({ label: c.cycle_name, value: c.id }))}
          />
          <Select
            allowClear
            style={{ width: 160 }}
            placeholder="依公司篩選（不選＝全部）"
            value={closeCompany}
            onChange={setCloseCompany}
            options={companyOptions}
          />
          <Select
            style={{ width: 140 }}
            value={closeMonth}
            onChange={setCloseMonth}
            options={recentMonthOptions().map((m) => ({ label: m, value: m }))}
          />
        </Space>
        <Table
          dataSource={openRequests}
          rowKey="id"
          size="small"
          loading={loadingOpen}
          pagination={false}
          rowSelection={{
            selectedRowKeys: selectedCloseIds,
            onChange: (keys) => setSelectedCloseIds(keys as number[]),
          }}
          columns={[
            { title: '請購單號', dataIndex: 'request_no', width: 150 },
            { title: '公司', dataIndex: 'company', width: 100 },
            { title: '部門', dataIndex: 'department_name', width: 140 },
            { title: '填寫人', dataIndex: 'submitted_by_name', width: 100, render: (v?: string | null) => v || '—' },
            {
              title: '請購總金額',
              dataIndex: 'total_amount',
              width: 120,
              align: 'right',
              render: (v: number) => v?.toLocaleString(undefined, { minimumFractionDigits: 0 }),
            },
          ]}
        />
        <div style={{ color: '#888', fontSize: 12, marginTop: 8 }}>
          只列出目前「開放中」（尚未關閉）的請購單。「全部關閉」會關閉這個篩選條件下全部開放中的請購單
          （不受勾選影響）；「關閉勾選」只關閉目前打勾的列。
        </div>
      </Modal>
    </div>
  )
}
