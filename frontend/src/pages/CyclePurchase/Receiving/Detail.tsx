/**
 * 週期採購 — 驗收單詳情／填寫頁（第四期，2026-07-11 新增）
 * 路由：/cycle-purchase/receiving/:id
 *
 * 只有草稿狀態可以編輯明細。畫面一進來就把這張採購單的每個明細行全部列出來
 * （可驗收明細，來自 GET /receiving/{id}/receivable-items，後端已經把「這張
 * 驗收單之前的累計已驗收量」跟「這張（草稿）驗收單目前已填的值」合併好），
 * 由填單人直接在每一列填本次驗收數量，比照請購單填寫頁「一次列出全部、
 * 逐列編輯」的 UX（不需要先「加入」才看得到）。
 *
 * is_final_for_item（預設 true）：這個料號本次驗收是否就結束了（不會再有
 * 後續驗收）。多數情況一次到齊維持預設即可；分批到貨時，中間批次要記得
 * 關掉這個開關，等最後一批再打開，送出時才會正確計算差異、不會被中途的
 * 部分到貨誤判成「差異」。
 *
 * 「預估差異」欄位是前端算好給填單人看的參考值（＝累計已驗收數量（含本次）
 * －訂購數量，only when 這個料號本次是最後一批），實際判定與擋下仍以後端
 * 送出時的計算為準（避免重複邏輯不同步）。
 */
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, Descriptions, Input, Popconfirm, Space, Switch, Table, Tag, Typography, message,
} from 'antd'
import { ArrowLeftOutlined, DeleteOutlined, SendOutlined } from '@ant-design/icons'
import {
  deleteReceivingItem, getReceivableItems, getReceiving, submitReceiving, upsertReceivingItem,
} from '@/api/cyclePurchase'
import type { CpReceivableItem, CpReceivingDetail, CpReceivingItem } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:       { color: 'default', label: '草稿' },
  completed:   { color: 'green',   label: '已完成（無差異）' },
  discrepancy: { color: 'orange',  label: '有差異' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

function estimatedVariance(row: CpReceivableItem, receivedQty: number, isFinal: boolean): number | null {
  if (!isFinal) return null
  return row.previously_received_qty + receivedQty - row.ordered_qty
}

export default function CpReceivingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const receivingId = Number(id)
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canReceive = hasPermission('cycle_purchase_receive')

  const [detail, setDetail] = useState<CpReceivingDetail | null>(null)
  const [rows, setRows] = useState<CpReceivableItem[]>([])
  const [loading, setLoading] = useState(true)
  const [savingRowId, setSavingRowId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const editable = canReceive && detail?.status === 'draft'

  const load = async () => {
    if (!receivingId) return
    setLoading(true)
    try {
      const d = (await getReceiving(receivingId)).data
      setDetail(d)
      if (d.status === 'draft') {
        const items = (await getReceivableItems(receivingId)).data
        setRows(items)
      }
    } catch (err: any) {
      message.error(errMsg(err, '載入失敗'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [receivingId])

  const filledCount = rows.filter((r) => (r.received_qty || 0) > 0).length

  const handleQtyChange = async (row: CpReceivableItem, qty: number | null) => {
    const newQty = qty ?? 0
    if (!row.receiving_item_id && newQty === 0) return // 尚未建立且維持 0，不需要呼叫後端
    setSavingRowId(row.po_item_id)
    try {
      await upsertReceivingItem(receivingId, {
        po_item_id: row.po_item_id,
        received_qty: newQty,
        is_final_for_item: row.is_final_for_item ?? true,
        variance_reason: row.variance_reason ?? null,
      })
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '更新驗收數量失敗'))
    } finally {
      setSavingRowId(null)
    }
  }

  const handleFinalToggle = async (row: CpReceivableItem, checked: boolean) => {
    if (!row.receiving_item_id) return // 還沒填數量，不需要動這個欄位
    setSavingRowId(row.po_item_id)
    try {
      await upsertReceivingItem(receivingId, {
        po_item_id: row.po_item_id,
        received_qty: row.received_qty ?? 0,
        is_final_for_item: checked,
        variance_reason: row.variance_reason ?? null,
      })
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '更新失敗'))
    } finally {
      setSavingRowId(null)
    }
  }

  const handleReasonBlur = async (row: CpReceivableItem, value: string) => {
    if (!row.receiving_item_id) return
    if ((row.variance_reason || '') === value) return // 沒有變更不必呼叫
    setSavingRowId(row.po_item_id)
    try {
      await upsertReceivingItem(receivingId, {
        po_item_id: row.po_item_id,
        received_qty: row.received_qty ?? 0,
        is_final_for_item: row.is_final_for_item ?? true,
        variance_reason: value.trim() || null,
      })
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '更新差異原因失敗'))
    } finally {
      setSavingRowId(null)
    }
  }

  const handleDeleteRow = async (row: CpReceivableItem) => {
    if (!row.receiving_item_id) return
    try {
      await deleteReceivingItem(receivingId, row.receiving_item_id)
      message.success('已刪除這筆明細（可再重新填數量）')
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '刪除失敗'))
    }
  }

  const handleSubmit = async () => {
    if (filledCount === 0) {
      message.warning('請至少填寫一筆驗收數量大於 0 的料號才能送出')
      return
    }
    const missingReason = rows.find((r) => {
      if (!r.receiving_item_id) return false
      const isFinal = r.is_final_for_item ?? true
      const variance = estimatedVariance(r, r.received_qty ?? 0, isFinal)
      return variance !== null && variance !== 0 && !(r.variance_reason && r.variance_reason.trim())
    })
    if (missingReason) {
      message.warning(`料號「${missingReason.item_code} ${missingReason.item_name}」驗收數量與訂購數量有差異，送出前必須填寫差異原因`)
      return
    }
    setSubmitting(true)
    try {
      const res = await submitReceiving(receivingId)
      message.success(res.data.status === 'discrepancy' ? '已送出（有差異，請留意採購單狀態）' : '已送出（無差異）')
      await load()
    } catch (err: any) {
      message.error(errMsg(err, '送出失敗'))
    } finally {
      setSubmitting(false)
    }
  }

  if (!detail) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/receiving')} style={{ marginBottom: 16 }}>
          返回清單
        </Button>
        <Card loading={loading} />
      </div>
    )
  }

  const draftColumns = [
    { title: '料號', dataIndex: 'item_code', width: 110 },
    { title: '品名', dataIndex: 'item_name' },
    { title: '單位', dataIndex: 'unit', width: 70 },
    { title: '訂購數量', dataIndex: 'ordered_qty', width: 90, align: 'right' as const },
    { title: '之前已驗收', dataIndex: 'previously_received_qty', width: 100, align: 'right' as const },
    { title: '剩餘（參考）', dataIndex: 'remaining_qty', width: 100, align: 'right' as const },
    {
      title: '本次驗收數量',
      key: 'received_qty',
      width: 130,
      render: (_: unknown, row: CpReceivableItem) =>
        editable ? (
          <Input
            type="number"
            min={0}
            defaultValue={row.received_qty ?? 0}
            disabled={savingRowId === row.po_item_id}
            onBlur={(e) => {
              const v = e.target.value === '' ? 0 : Number(e.target.value)
              if (v !== (row.received_qty ?? 0)) handleQtyChange(row, v)
            }}
            style={{ width: '100%' }}
          />
        ) : (row.received_qty ?? 0),
    },
    {
      title: '本次結束？',
      key: 'is_final_for_item',
      width: 100,
      align: 'center' as const,
      render: (_: unknown, row: CpReceivableItem) =>
        editable ? (
          <Switch
            checked={row.is_final_for_item ?? true}
            disabled={!row.receiving_item_id || savingRowId === row.po_item_id}
            onChange={(checked) => handleFinalToggle(row, checked)}
          />
        ) : (row.is_final_for_item ? '是' : '否'),
    },
    {
      title: '預估差異',
      key: 'estimated_variance',
      width: 100,
      align: 'right' as const,
      render: (_: unknown, row: CpReceivableItem) => {
        const v = estimatedVariance(row, row.received_qty ?? 0, row.is_final_for_item ?? true)
        if (v === null) return <Text type="secondary">（未結束）</Text>
        if (v === 0) return <Text type="secondary">0</Text>
        return <Text type="danger">{v > 0 ? `+${v}` : v}</Text>
      },
    },
    {
      title: '差異原因',
      key: 'variance_reason',
      width: 220,
      render: (_: unknown, row: CpReceivableItem) =>
        editable ? (
          <Input
            defaultValue={row.variance_reason || ''}
            disabled={!row.receiving_item_id || savingRowId === row.po_item_id}
            placeholder={row.receiving_item_id ? '有差異時必填' : '需先填驗收數量'}
            onBlur={(e) => handleReasonBlur(row, e.target.value)}
          />
        ) : (row.variance_reason || '—'),
    },
    ...(editable
      ? [{
          title: '操作',
          key: 'actions',
          width: 70,
          render: (_: unknown, row: CpReceivableItem) =>
            row.receiving_item_id ? (
              <Popconfirm title="確定刪除此明細？" onConfirm={() => handleDeleteRow(row)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ) : null,
        }]
      : []),
  ]

  const readonlyColumns = [
    { title: '料號', dataIndex: 'item_code', width: 110 },
    { title: '品名', dataIndex: 'item_name' },
    { title: '單位', dataIndex: 'unit', width: 70 },
    { title: '訂購數量', dataIndex: 'ordered_qty', width: 90, align: 'right' as const },
    { title: '之前已驗收', dataIndex: 'previously_received_qty', width: 100, align: 'right' as const },
    { title: '本次驗收數量', dataIndex: 'received_qty', width: 110, align: 'right' as const },
    {
      title: '本次結束？',
      dataIndex: 'is_final_for_item',
      width: 100,
      align: 'center' as const,
      render: (v: boolean) => (v ? '是' : '否'),
    },
    {
      title: '差異數量',
      dataIndex: 'variance_qty',
      width: 100,
      align: 'right' as const,
      render: (v?: number | null) => {
        if (v == null) return <Text type="secondary">—</Text>
        if (v === 0) return '0'
        return <Text type="danger">{v > 0 ? `+${v}` : v}</Text>
      },
    },
    { title: '差異原因', dataIndex: 'variance_reason', width: 220, render: (v?: string | null) => v || '—' },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/receiving')}>返回清單</Button>
          <Title level={4} style={{ margin: 0 }}>{detail.receiving_no}</Title>
          <Tag color={STATUS_TAG[detail.status]?.color}>{STATUS_TAG[detail.status]?.label || detail.status}</Tag>
        </Space>
        {editable && (
          <Button type="primary" icon={<SendOutlined />} loading={submitting} onClick={handleSubmit}>
            送出驗收單
          </Button>
        )}
      </Space>

      {detail.status === 'discrepancy' && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="這張驗收單有差異"
          description="請查看下方明細的「差異數量」與「差異原因」欄位。"
        />
      )}

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="採購單號">
            <a onClick={() => navigate(`/cycle-purchase/pos/${detail.po_id}`)}>{detail.po_no}</a>
          </Descriptions.Item>
          <Descriptions.Item label="公司">{detail.company}</Descriptions.Item>
          <Descriptions.Item label="供應商">{detail.vendor_name}</Descriptions.Item>
          <Descriptions.Item label="驗收日期">{detail.received_date}</Descriptions.Item>
          <Descriptions.Item label="驗收人員">{detail.receiver_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="備註">{detail.notes || '—'}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={detail.status === 'draft' ? `可驗收明細（已填 ${filledCount} 項）` : '驗收明細'}>
        {detail.status === 'draft' ? (
          rows.length === 0 ? (
            <Alert type="info" showIcon message="這張採購單沒有明細可以驗收" />
          ) : (
            <Table dataSource={rows} rowKey="po_item_id" size="small" pagination={false} columns={draftColumns as any} />
          )
        ) : (
          <Table
            dataSource={detail.items}
            rowKey="id"
            size="small"
            pagination={false}
            columns={readonlyColumns as any}
          />
        )}
      </Card>
    </div>
  )
}
