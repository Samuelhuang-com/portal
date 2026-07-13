/**
 * 週期採購 — 請購單詳情／填寫／簽核頁
 * 路由：/cycle-purchase/requests/:id
 *
 * 狀態機：draft -> submitted -> approved / rejected
 * rejected 可再編輯明細、重新送出（不是死路，2026-07-11 與 Samuel 確認的修復）。
 * 可選料號僅限「該請購單所屬公司」有料號對照的啟用中料號（available-items）。
 * 會計科目由填單人在明細逐行手動選，單價快照取自該公司的料號對照單價，
 * 不是集團參考價，因為兩家公司實際成交價可能不同。
 *
 * 2026-07-11（與 Samuel 討論後的 UX 改版，拿掉「批次」的同時一併調整）：
 * 原本是「選料號 -> 加入明細」一筆一筆加。Samuel 的訴求是：一進頁面就把
 * 「週期採購 — 料號主檔」裡該公司可選的料號全部列出來，由填單人直接在
 * 每一列填數量，預設 0（本次不購買），不需要先「加入」才看得到。
 * 料號依類別分組（Collapse），並提供搜尋框，因為單一公司常見料號可能有
 * 數百筆。實作上：數量從 0 改成 >0 時才即時呼叫後端「新增明細」；已存在的
 * 明細改數量（含改回 0，代表「本次不購買」但保留這筆列的紀錄）呼叫「更新
 * 明細」；會計科目要等這筆料號已經有明細列（數量曾經 >0 過）才能選。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Badge, Button, Card, Collapse, Descriptions, Form, Input, InputNumber,
  Modal, Popconfirm, Select, Space, Table, Tag, Typography, message,
} from 'antd'
import {
  ArrowLeftOutlined, CheckOutlined, CloseOutlined, DeleteOutlined, SearchOutlined, SendOutlined,
} from '@ant-design/icons'
import {
  addRequestItem, approveRequest, deleteRequestItem, getAvailableItems,
  getCostCenters, getCpAccountCodes, getRequest, rejectRequest, submitRequest,
  updateRequest, updateRequestItem,
} from '@/api/cyclePurchase'
import type {
  CpAccountCode, CpAvailableItem, CpCostCenter, CpRequestDetail, CpRequestItem,
} from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  submitted: { color: 'blue',    label: '已送出' },
  approved:  { color: 'green',   label: '已核准' },
  rejected:  { color: 'red',     label: '已退回' },
}

const UNCATEGORIZED = '（未分類）'

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
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
  const canApprove = hasPermission('cycle_purchase_approve')

  const [detail, setDetail] = useState<CpRequestDetail | null>(null)
  const [availableItems, setAvailableItems] = useState<CpAvailableItem[]>([])
  const [accountCodes, setAccountCodes] = useState<CpAccountCode[]>([])
  const [costCenters, setCostCenters] = useState<CpCostCenter[]>([])
  const [loading, setLoading] = useState(true)
  const [savingItemId, setSavingItemId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [activeKeys, setActiveKeys] = useState<string[]>([])

  // 簽核退回 modal
  const [rejectModal, setRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [acting, setActing] = useState(false)

  const editable = canEdit && !!detail && (detail.status === 'draft' || detail.status === 'rejected')

  const load = async () => {
    if (!requestId) return
    setLoading(true)
    try {
      const d = (await getRequest(requestId)).data
      setDetail(d)
      const [avail, codes, ccs] = await Promise.all([
        getAvailableItems(requestId).then((r) => r.data),
        getCpAccountCodes({ is_active: true }).then((r) => r.data),
        getCostCenters({ department_id: d.department_id, is_active: true }).then((r) => r.data),
      ])
      setAvailableItems(avail)
      setAccountCodes(codes)
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

  const filteredRows = useMemo(() => {
    if (!search.trim()) return mergedRows
    const kw = search.trim().toLowerCase()
    return mergedRows.filter(
      (r) => r.item_code.toLowerCase().includes(kw) || r.item_name.toLowerCase().includes(kw),
    )
  }, [mergedRows, search])

  const groupedByCategory = useMemo(() => {
    const groups = new Map<string, MergedRow[]>()
    for (const r of filteredRows) {
      const cat = r.category || UNCATEGORIZED
      if (!groups.has(cat)) groups.set(cat, [])
      groups.get(cat)!.push(r)
    }
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [filteredRows])

  const filledCount = mergedRows.filter((r) => (r.requestItem?.request_qty || 0) > 0).length

  // 搜尋時自動展開有符合結果的分類；清空搜尋則不強制收合使用者已手動展開的分類。
  useEffect(() => {
    if (search.trim()) {
      setActiveKeys(groupedByCategory.map(([c]) => c))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

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
    } catch (err: any) {
      message.error(errMsg(err, '更新數量失敗'))
    } finally {
      setSavingItemId(null)
    }
  }

  const handleAccountChange = async (row: MergedRow, accountCodeId: number | null) => {
    if (!row.requestItem) return
    setSavingItemId(row.item_id)
    try {
      await updateRequestItem(requestId, row.requestItem.id, { account_code_id: accountCodeId })
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '更新會計科目失敗'))
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
    } catch (err: any) {
      message.error(errMsg(err, '刪除失敗'))
    }
  }

  const handleCostCenterChange = async (ccId: number | null) => {
    try {
      await updateRequest(requestId, { cost_center_id: ccId })
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '更新成本中心失敗'))
    }
  }

  const handleSubmit = async () => {
    setActing(true)
    try {
      await submitRequest(requestId)
      message.success('已送出，等待簽核')
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '送出失敗'))
    } finally {
      setActing(false)
    }
  }

  const handleApprove = async () => {
    setActing(true)
    try {
      await approveRequest(requestId)
      message.success('已核准')
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '核准失敗'))
    } finally {
      setActing(false)
    }
  }

  const handleReject = async () => {
    if (!rejectReason.trim()) { message.warning('請填寫退回原因'); return }
    setActing(true)
    try {
      await rejectRequest(requestId, rejectReason.trim())
      message.success('已退回')
      setRejectModal(false)
      setRejectReason('')
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '退回失敗'))
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
    {
      title: '會計科目',
      key: 'account_code_id',
      width: 200,
      render: (_: unknown, row: MergedRow) =>
        editable ? (
          <Select
            allowClear
            style={{ width: '100%' }}
            placeholder={row.requestItem ? '選擇會計科目' : '需先填數量'}
            disabled={!row.requestItem || savingItemId === row.item_id}
            value={row.requestItem?.account_code_id ?? undefined}
            onChange={(v) => handleAccountChange(row, v ?? null)}
            options={accountCodes.map((c) => ({ label: `${c.code} ${c.name}`, value: c.id }))}
          />
        ) : (row.requestItem?.account_code_label || '—'),
    },
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
          <Tag color={STATUS_TAG[detail.status]?.color}>{STATUS_TAG[detail.status]?.label || detail.status}</Tag>
        </Space>
        <Space>
          {editable && (
            <Button type="primary" icon={<SendOutlined />} loading={acting} onClick={handleSubmit}>
              送出請購單
            </Button>
          )}
          {canApprove && detail.status === 'submitted' && (
            <>
              <Button danger icon={<CloseOutlined />} onClick={() => setRejectModal(true)}>退回</Button>
              <Button type="primary" icon={<CheckOutlined />} loading={acting} onClick={handleApprove}>核准</Button>
            </>
          )}
        </Space>
      </Space>

      {detail.status === 'rejected' && detail.reject_reason && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="已退回，請修改後重新送出"
          description={`退回原因：${detail.reject_reason}`}
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
          <Descriptions.Item label="送出人">
            {detail.submitted_by_name ? `${detail.submitted_by_name}（${detail.submitted_at?.slice(0, 16)}）` : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="簽核人" span={3}>
            {detail.approved_by_name ? `${detail.approved_by_name}（${detail.approved_at?.slice(0, 16)}）` : '—'}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title={
          <Space>
            <span>請購明細</span>
            <Badge count={filledCount} showZero color="blue" overflowCount={999} title="已填數量的料號筆數" />
          </Space>
        }
        extra={
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="搜尋料號／品名"
            style={{ width: 240 }}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        }
      >
        {mergedRows.length === 0 ? (
          <Alert type="info" showIcon message="這個公司目前沒有任何有料號對照的啟用中料號可以選" />
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

      <Modal
        title="退回請購單"
        open={rejectModal}
        onOk={handleReject}
        onCancel={() => setRejectModal(false)}
        okText="確定退回"
        okButtonProps={{ danger: true, loading: acting }}
        cancelText="取消"
      >
        <Form layout="vertical">
          <Form.Item label="退回原因" required>
            <TextArea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="請說明退回原因，填單人將依此修改後重新送出"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
