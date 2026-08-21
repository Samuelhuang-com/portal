/**
 * 週期採購 — 請購單詳情／填寫頁
 * 路由：/cycle-purchase/requests/:id
 *
 * 2026-07-17（第三次調整，請購單流程大改版，與 Samuel 確認）：
 * 拿掉送出／簽核／退回，請購單建立後由填單人自行編輯，不需要送出給誰核准。
 * 關閉／重新開啟是獨立的權限（cycle_purchase_close），關閉後這張單才會出現在
 * 「彙整單」的可勾選清單裡（見週採彙整單頁面）。
 *
 * 2026-08-07（第四次調整，與 Samuel 確認）：
 * ~~能不能編輯看「還沒關閉」＋「還是當月」兩個條件~~ → 改成**只看 is_closed**。
 * 期別已過的單現在會被系統自動關閉（後端 auto_close_expired_requests），
 * 「過月」已經由 is_closed 涵蓋，再檢查一次是重複的；而「重新開啟」的意義就是
 * 讓過月的單能補改，若前端還卡當月，重新開啟後畫面仍唯讀，與後端行為不一致。
 * 標題列的狀態標籤改用共用的 CloseStatusTag，區分人工關閉（灰「已關閉」）與
 * 系統自動關閉（淺粉「關閉」）。
 *
 * 2026-08-07（UX 補強，Samuel 反映「只有關閉此請購單，沒有 Save 或送出」）：
 * 這一頁**本來就是即時儲存**——改數量／會計科目／成本中心都會立刻打 API，
 * 所以沒有 Save 按鈕是設計而不是遺漏；「送出」只顯示給沒有 cycle_purchase_close
 * 權限的填單人（有該權限的人看到的是「關閉此請購單」，底層同一個動作）。
 * 問題出在**畫面完全沒有回饋**，看起來就像改了沒存。因此在「請購明細」卡片
 * 標題列加上儲存狀態（儲存中…／已自動儲存 HH:mm／改動會自動儲存的說明）。
 * 與 Samuel 確認**維持即時儲存、不改成手動 Save**——改成手動會失去「填一半
 * 關網頁也不會丟資料」這個好處，要改需另排一次評估。
 * 同時在明細卡片加「全部展開／全部收合」（料號動輒數百筆、分好幾個類別）。
 *
 * 2026-08-08：明細卡片加「全部／只看已填」切換。料號清單是「該公司所有可選料號」，
 * 但一張單真正有填的通常只有十幾筆，核對「這個月要買什麼」時全部列出反而難看。
 * 與搜尋是 AND 關係。切到「只看已填」會自動全展開（篩完只剩十幾筆，收合著等於白按）；
 * 切回「全部」不強制收合——可能有數百筆，全開反而難用，交給使用者決定。
 * ⚠️ 在「只看已填」模式下把數量改成 0，那一列會立刻消失（它不再符合篩選條件）。
 * 這是篩選器的正常行為，但容易被誤認成資料掉了，所以標題列有一行提醒。
 *
 * 2026-07-11（與 Samuel 討論後的 UX 改版，拿掉「批次」的同時一併調整，
 * 這部分邏輯不受本次改版影響，仍然有效）：
 * 一進頁面就把「週期採購 — 料號主檔」裡該公司可選的料號全部列出來，由填單人
 * 直接在每一列填數量，預設 0（本次不購買），不需要先「加入」才看得到。
 * 料號依類別分組（Collapse），並提供搜尋框，因為單一公司常見料號可能有
 * 數百筆。實作上：數量從 0 改成 >0 時才即時呼叫後端「新增明細」；已存在的
 * 明細改數量（含改回 0，代表「本次不購買」但保留這筆列的紀錄）呼叫「更新
 * 明細」；~~會計科目要等這筆料號已經有明細列（數量曾經 >0 過）才能選~~
 * → 見下方 2026-08-21。
 *
 * 2026-08-21（與 Samuel 確認，移除會計科目欄）：
 * 協理提供的《設料號明細表》每一列都已標好會科代碼／名稱，科目屬於料號本身的
 * 屬性，不該每次請購重填。科目改掛在料號主檔的「料號對照表」上（公司＋部門層級，
 * 因為同一料號在不同部門可能記到不同科目，例：E0204002 軌道燈 工程部 621601
 * 修繕費-維修／營業部 1142 用品盤存），由後端在建立明細時自動帶入快照。
 * 因此**這一頁移除「會計科目」欄**，填單人只填數量。
 * ⚠️ `request_items.account_code_id` 欄位與付款分攤邏輯完全不變，只是不再由這裡
 * 手動指定；要改某個料號的科目請到「料號主檔 → 料號對照」。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Badge, Button, Card, Collapse, Descriptions, Input, InputNumber,
  Popconfirm, Segmented, Select, Space, Table, Typography, message,
} from 'antd'
import {
  ArrowLeftOutlined, CheckCircleOutlined, DeleteOutlined, DownOutlined, LoadingOutlined,
  LockOutlined, SearchOutlined, SendOutlined, UnlockOutlined, UpOutlined,
} from '@ant-design/icons'
import {
  addRequestItem, closeRequests, deleteRequestItem, getAvailableItems,
  getCostCenters, getRequest, reopenRequests,
  updateRequest, updateRequestItem,
} from '@/api/cyclePurchase'
import type {
  CpAvailableItem, CpCostCenter, CpRequestDetail, CpRequestItem,
} from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'
import CloseStatusTag from '../components/CloseStatusTag'

const { Title, Text } = Typography

const UNCATEGORIZED = '（未分類）'

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

function currentYearMonth() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

// 合併「可選料號」與「已在明細中的料號」成單一列表，供填單畫面一次列出全部使用。
interface MergedRow {
  item_id: number
  item_code: string
  item_name: string
  unit?: string | null
  category?: string | null
  unit_price?: number | null
  is_confirmed: boolean
  // 對應到的明細列（若尚未建立則為 undefined，qty 顯示為 0）
  requestItem?: CpRequestItem
}

export default function CpRequestDetailPage() {
  const { id } = useParams<{ id: string }>()
  const requestId = Number(id)
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canEdit = hasPermission('cycle_purchase_request')
  const canClose = hasPermission('cycle_purchase_close')

  const [detail, setDetail] = useState<CpRequestDetail | null>(null)
  const [availableItems, setAvailableItems] = useState<CpAvailableItem[]>([])
  const [costCenters, setCostCenters] = useState<CpCostCenter[]>([])
  const [loading, setLoading] = useState(true)
  const [savingItemId, setSavingItemId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [activeKeys, setActiveKeys] = useState<string[]>([])
  const [acting, setActing] = useState(false)
  // 2026-08-07：這一頁是「改一格存一格」的即時儲存，沒有 Save 按鈕。
  // 但原本畫面完全沒有回饋，使用者會以為改了沒存、跑來問「Save 在哪」。
  // 這裡記下最後一次成功寫入的時間，在明細卡片標題列顯示。
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  // 2026-08-08：料號清單是「該公司所有可選料號」，動輒數百筆，但一張單真正
  // 有填的通常只有十幾筆。要核對「這個月到底要買什麼」時，全部列出來反而難看。
  const [filledOnly, setFilledOnly] = useState(false)

  const isCurrentMonth = !!detail && detail.period_label === currentYearMonth()
  // 2026-08-07：可編輯條件**只看 is_closed**，不再要求當月。
  // 過月的單現在會被系統自動關閉（is_closed=True），月份檢查已被涵蓋；
  // 而「重新開啟」的意義就是讓過月的單能補改，若前端還卡當月，
  // 重新開啟後畫面仍是唯讀，跟後端行為不一致。
  const editable = canEdit && !!detail && !detail.is_closed
  const isAutoClosed = !!detail && detail.is_closed && detail.close_kind === 'auto'

  const load = async () => {
    if (!requestId) return
    setLoading(true)
    try {
      const d = (await getRequest(requestId)).data
      setDetail(d)
      // 2026-08-21：不再撈會計科目主檔——科目已改由料號對照表帶入，
      // 這個畫面沒有科目欄位了（見 itemColumns 註解）。
      const [avail, ccs] = await Promise.all([
        getAvailableItems(requestId).then((r) => r.data),
        getCostCenters({ department_id: d.department_id, is_active: true }).then((r) => r.data),
      ])
      setAvailableItems(avail)
      setCostCenters(ccs)
    } catch (err: any) {
      message.error(errMsg(err, '載入失敗'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [requestId])

  // ── 合併料號主檔可選清單 + 已填明細 ────────────────────────────────────────
  const mergedRows: MergedRow[] = useMemo(() => {
    const itemsByItemId = new Map<number, CpRequestItem>((detail?.items || []).map((it) => [it.item_id, it]))
    const rows = availableItems.map((a) => ({
      item_id: a.item_id,
      item_code: a.item_code,
      item_name: a.item_name,
      unit: a.unit,
      category: a.category,
      unit_price: a.unit_price,
      is_confirmed: a.is_confirmed,
      requestItem: itemsByItemId.get(a.item_id),
    }))
    // 明細裡若有料號已經不在「可選清單」（例如料號後來被停用），仍要顯示避免資料消失。
    const availableIds = new Set(availableItems.map((a) => a.item_id))
    for (const it of detail?.items || []) {
      if (!availableIds.has(it.item_id)) {
        rows.push({
          item_id: it.item_id,
          item_code: it.item_code,
          item_name: it.item_name,
          unit: it.unit,
          category: null,
          unit_price: it.unit_price,
          is_confirmed: true,
          requestItem: it,
        })
      }
    }
    return rows
  }, [availableItems, detail?.items])

  const isFilled = (r: MergedRow) => (r.requestItem?.request_qty || 0) > 0

  const filteredRows = useMemo(() => {
    let rows = mergedRows
    // 「只看已填」與搜尋是 AND 關係：兩個都設就是「已填的之中符合關鍵字的」
    if (filledOnly) rows = rows.filter(isFilled)
    const kw = search.trim().toLowerCase()
    if (kw) {
      rows = rows.filter(
        (r) => r.item_code.toLowerCase().includes(kw) || r.item_name.toLowerCase().includes(kw),
      )
    }
    return rows
  }, [mergedRows, search, filledOnly])

  const groupedByCategory = useMemo(() => {
    const groups = new Map<string, MergedRow[]>()
    for (const r of filteredRows) {
      const cat = r.category || UNCATEGORIZED
      if (!groups.has(cat)) groups.set(cat, [])
      groups.get(cat)!.push(r)
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [filteredRows])

  const filledCount = mergedRows.filter(isFilled).length

  // 「全部展開」按鈕在已經全開時要 disabled，否則按了沒反應會讓人以為壞了。
  // 用 length 比較就夠——activeKeys 的值一定來自 groupedByCategory，不會有多餘的 key。
  const allExpanded =
    groupedByCategory.length > 0 && activeKeys.length === groupedByCategory.length

  // 搜尋時自動展開有符合結果的分類；清空搜尋則不強制收合使用者已手動展開的分類。
  useEffect(() => {
    if (search.trim()) {
      setActiveKeys(groupedByCategory.map(([c]) => c))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  // 切到「只看已填」時自動全部展開——篩完通常只剩十幾筆，如果類別還是收合的，
  // 使用者會看到一堆空標題，等於白按。切回「全部」不強制收合（可能有數百筆，
  // 全開反而難用），讓使用者自己決定。
  useEffect(() => {
    if (filledOnly) {
      setActiveKeys(groupedByCategory.map(([c]) => c))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filledOnly])

  // ── 明細數量／會計科目變更 ──────────────────────────────────────────────────
  const handleQtyChange = async (row: MergedRow, qty: number | null) => {
    const newQty = qty || 0
    setSavingItemId(row.item_id)
    try {
      if (row.requestItem) {
        // 已經有明細列：直接更新數量（含改回 0，代表「本次不購買」但保留這筆列）
        await updateRequestItem(requestId, row.requestItem.id, { request_qty: newQty })
      } else if (newQty > 0) {
        // 尚未建立明細列，數量從 0 變成 >0 才建立
        await addRequestItem(requestId, { item_id: row.item_id, request_qty: newQty })
      } else {
        // 尚未建立且維持 0，不需要呼叫後端
        return
      }
      await load()
      setLastSavedAt(new Date())
    } catch (err: any) {
      message.error(errMsg(err, '更新數量失敗'))
    } finally {
      setSavingItemId(null)
    }
  }

  const handleDeleteItem = async (row: MergedRow) => {
    if (!row.requestItem) return
    try {
      await deleteRequestItem(requestId, row.requestItem.id);
      message.success('已刪除這筆明細（可再重新填數量）')
      await load()
      setLastSavedAt(new Date())
    } catch (err: any) {
      message.error(errMsg(err, '刪除失敗'))
    }
  }

  const handleCostCenterChange = async (ccId: number | null) => {
    try {
      await updateRequest(requestId, { cost_center_id: ccId })
      await load()
      setLastSavedAt(new Date())
    } catch (err: any) {
      message.error(errMsg(err, '更新成本中心失敗'))
    }
  }

  // 2026-07-18：一般填單人（只有 cycle_purchase_request 權限、沒有 cycle_purchase_close）
  // 看到的是「送出請購單」，買家/管理者（有 cycle_purchase_close 權限）看到的是「關閉此
  // 請購單」——底層是同一個關閉動作（is_closed=True），只是站在填單人角度換個說法叫「送出」，
  // 跟買家在請購單清單頁「關閉請購單」視窗的批次管理（全部關閉/選擇關閉）是同一套機制。
  const handleClose = async () => {
    setActing(true)
    try {
      await closeRequests([requestId])
      message.success(canClose ? '已關閉此請購單' : '已送出，這張請購單暫時無法再編輯')
      await load()
    } catch (err: any) {
      message.error(errMsg(err, canClose ? '關閉失敗' : '送出失敗'))
    } finally {
      setActing(false)
    }
  }

  const handleReopen = async () => {
    setActing(true)
    try {
      await reopenRequests([requestId])
      message.success('已重新開啟，可以再編輯')
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '重新開啟失敗'))
    } finally {
      setActing(false)
    }
  }

  if (!detail) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/requests')} style={{ marginBottom: 16 }}>
          返回清單
        </Button>
        <Card loading={loading} />
      </div>
    )
  }

  const itemColumns = [
    { title: '料號', dataIndex: 'item_code', width: 110 },
    { title: '品名', dataIndex: 'item_name' },
    { title: '單位', dataIndex: 'unit', width: 70 },
    {
      title: '單價',
      dataIndex: 'unit_price',
      width: 100,
      align: 'right' as const,
      render: (v?: number | null) => (v == null ? '—' : v.toLocaleString()),
    },
    {
      title: '數量',
      key: 'request_qty',
      width: 110,
      render: (_: unknown, row: MergedRow) =>
        editable ? (
          <InputNumber
            min={0}
            value={row.requestItem?.request_qty ?? 0}
            disabled={savingItemId === row.item_id}
            onChange={(nv) => handleQtyChange(row, nv)}
            style={{ width: '100%' }}
          />
        ) : (row.requestItem?.request_qty ?? 0),
    },
    // 2026-08-21（與 Samuel 確認）：移除「會計科目」欄。科目已改由料號主檔的
    // 「料號對照表」按公司＋部門設定，後端在建立明細時自動帶入快照
    // （cycle_purchase_request_service.add_request_item），填單人不需要、也不該
    // 逐行手選。request_items.account_code_id 欄位與付款分攤邏輯都維持不變。
    {
      title: '小計',
      key: 'subtotal',
      width: 100,
      align: 'right' as const,
      render: (_: unknown, row: MergedRow) =>
        row.requestItem ? Number(row.requestItem.subtotal).toLocaleString() : '—',
    },
    ...(editable
      ? [{
          title: '操作',
          key: 'actions',
          width: 70,
          render: (_: unknown, row: MergedRow) =>
            row.requestItem ? (
              <Popconfirm title="確定刪除此明細？" onConfirm={() => handleDeleteItem(row)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ) : null,
        }]
      : []),
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/requests')}>返回清單</Button>
          <Title level={4} style={{ margin: 0 }}>{detail.request_no}</Title>
          <CloseStatusTag
            isClosed={detail.is_closed}
            closeKind={detail.close_kind}
            periodLabel={detail.period_label}
          />
        </Space>
        <Space>
          {canClose && !detail.is_closed && (
            <Popconfirm
              title="確定要關閉這張請購單？"
              description="關閉後不能再新增/編輯明細，如需修改要先重新開啟"
              onConfirm={handleClose}
            >
              <Button icon={<LockOutlined />} loading={acting}>關閉此請購單</Button>
            </Popconfirm>
          )}
          {!canClose && canEdit && !detail.is_closed && (
            <Popconfirm
              title="確定要送出這張請購單？"
              description="送出後就不能再修改，如果之後還要改，要請有權限的人重新開啟"
              onConfirm={handleClose}
            >
              <Button type="primary" icon={<SendOutlined />} loading={acting}>送出請購單</Button>
            </Popconfirm>
          )}
          {canClose && detail.is_closed && (
            <Button icon={<UnlockOutlined />} loading={acting} onClick={handleReopen}>重新開啟</Button>
          )}
        </Space>
      </Space>

      {/* 2026-08-07：三種提示分開講。系統自動關閉最需要說清楚——使用者看到
          「關閉」但找不到是誰關的，要讓他知道那是月份過了、不是有人動了手腳。 */}
      {isAutoClosed && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="期別已過，這張請購單已由系統自動關閉"
          description={`這張請購單屬於「${detail.period_label}」，月份過了之後系統會自動關閉，沒有經手人。如果還需要補改，請找有「週期採購請購關閉」權限的人重新開啟——重新開啟之後就可以編輯，不受月份限制。`}
        />
      )}
      {detail.is_closed && !isAutoClosed && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="這張請購單已經關閉"
          description={
            detail.closed_by_name
              ? `由 ${detail.closed_by_name} 關閉。關閉後不能再編輯，如需修改請先請有權限的人重新開啟。`
              : '關閉後不能再編輯，如需修改請先請有權限的人重新開啟。'
          }
        />
      )}
      {!detail.is_closed && !isCurrentMonth && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="這是過去月份的請購單，目前是開放中"
          description={`這張請購單屬於「${detail.period_label}」。期別已過的單通常會被系統自動關閉，它還開放中，代表曾經被人重新開啟過——重新開啟的單不會再被自動關閉，需要人工關閉。`}
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="週期">{detail.cycle_name}</Descriptions.Item>
          <Descriptions.Item label="期別">{detail.period_label}</Descriptions.Item>
          <Descriptions.Item label="公司">{detail.company}</Descriptions.Item>
          <Descriptions.Item label="部門">{detail.department_name}</Descriptions.Item>
          <Descriptions.Item label="成本中心">
            {editable ? (
              <Select
                allowClear
                style={{ width: 200 }}
                placeholder="選擇成本中心（選填）"
                value={detail.cost_center_id ?? undefined}
                onChange={(v) => handleCostCenterChange(v ?? null)}
                options={costCenters.map((c) => ({ label: `${c.cc_code} ${c.cc_name}`, value: c.id }))}
              />
            ) : (detail.cost_center_name || '—')}
          </Descriptions.Item>
          <Descriptions.Item label="請購總金額">
            <Text strong>{Number(detail.total_amount).toLocaleString()}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="填寫人">
            {detail.submitted_by_name ? `${detail.submitted_by_name}（${detail.submitted_at?.slice(0, 16)}）` : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="關閉人" span={2}>
            {detail.closed_by_name ? `${detail.closed_by_name}（${detail.closed_at?.slice(0, 16)}）` : '—'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title={
          <Space wrap>
            <span>請購明細</span>
            <Badge count={filledCount} showZero color="blue" overflowCount={999} title="已填數量的料號筆數" />
            {/* 即時儲存的狀態回饋。沒有這個的話，使用者改完數量看不到任何反應，
                會以為沒存到——「Save 按鈕在哪」就是這樣被問出來的。 */}
            {filledOnly && editable && (
              <Text type="warning" style={{ fontSize: 12, fontWeight: 'normal' }}>
                （數量改成 0 的項目會立刻從這裡消失，要改回來請切換到「全部」）
              </Text>
            )}
            {editable && (savingItemId !== null ? (
              <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
                <LoadingOutlined /> 儲存中…
              </Text>
            ) : lastSavedAt ? (
              <Text type="success" style={{ fontSize: 12, fontWeight: 'normal' }}>
                <CheckCircleOutlined /> 已自動儲存 {lastSavedAt.toTimeString().slice(0, 5)}
              </Text>
            ) : (
              <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
                改動會自動儲存，不需要按儲存
              </Text>
            ))}
          </Space>
        }
        extra={
          <Space wrap>
            {/* 用 Segmented 而不是 Checkbox：兩個選項都有明確的名字，
                使用者一眼就知道現在是哪一種模式，不用推敲「打勾代表什麼」 */}
            <Segmented
              size="small"
              value={filledOnly ? 'filled' : 'all'}
              onChange={(v) => setFilledOnly(v === 'filled')}
              options={[
                { label: `全部（${mergedRows.length}）`, value: 'all' },
                { label: `只看已填（${filledCount}）`, value: 'filled' },
              ]}
            />
            {/* 料號動輒數百筆、分好幾個類別，一個個點開很累 */}
            <Button
              size="small"
              icon={<DownOutlined />}
              disabled={allExpanded}
              onClick={() => setActiveKeys(groupedByCategory.map(([c]) => c))}
            >
              全部展開
            </Button>
            <Button
              size="small"
              icon={<UpOutlined />}
              disabled={activeKeys.length === 0}
              onClick={() => setActiveKeys([])}
            >
              全部收合
            </Button>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="搜尋料號／品名"
              style={{ width: 240 }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </Space>
        }
      >
        {mergedRows.length === 0 ? (
          <Alert type="info" showIcon message="這個公司目前沒有任何有料號對照的啟用中料號可以選" />
        ) : groupedByCategory.length === 0 ? (
          // 篩完沒東西時，要講清楚是哪個條件篩掉的，否則使用者會以為料號不見了
          <Alert
            type="info"
            showIcon
            message={filledOnly && search.trim()
              ? `已填的項目裡沒有符合「${search.trim()}」的料號`
              : filledOnly
                ? '這張請購單目前還沒有填任何數量'
                : `沒有符合「${search.trim()}」的料號`}
            description={filledOnly ? '切換到「全部」就能看到所有可選料號並開始填寫。' : undefined}
            action={filledOnly ? (
              <Button size="small" onClick={() => setFilledOnly(false)}>切換到全部</Button>
            ) : undefined}
          />
        ) : (
          <Collapse
            activeKey={activeKeys}
            onChange={(keys) => setActiveKeys(Array.isArray(keys) ? keys : [keys])}
            items={groupedByCategory.map(([category, rows]) => ({
              key: category,
              label: (
                <Space>
                  <span>{category}</span>
                  <Text type="secondary">
                    （{rows.length} 項，已填 {rows.filter((r) => (r.requestItem?.request_qty || 0) > 0).length} 項）
                  </Text>
                </Space>
              ),
              children: (
                <Table
                  dataSource={rows}
                  rowKey="item_id"
                  size="small"
                  pagination={false}
                  columns={itemColumns as any}
                />
              ),
            }))}
          />
        )}
      </Card>
    </div>
  )
}
