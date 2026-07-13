/**
 * 週期採購 — 採購單詳情頁（第三期，2026-07-11 新增）
 * 路由：/cycle-purchase/pos/:id
 *
 * 只有草稿狀態可以編輯預計到貨日／備註。狀態機：draft -> issued -> cancelled
 * （issued 也可以直接 cancelled，例如供應商無法供貨）。
 *
 * 2026-07-11 提醒（尚未跟 Samuel 確認，先保守處理）：取消採購單目前不會
 * 自動把對應的彙整列狀態從 converted 改回 draft，避免自動改資料造成誤解。
 * 如果之後需要「取消後彙整列自動解鎖可重轉」，需要另外討論再實作。
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, DatePicker, Descriptions, Input, Popconfirm, Space, Table, Tag, Typography, message,
} from 'antd'
import { ArrowLeftOutlined, CheckOutlined, CloseOutlined, SaveOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getPo, setPoStatus, updatePo } from '@/api/cyclePurchase'
import type { CpPODetail } from '@/types/cyclePurchase'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography
const { TextArea } = Input

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  draft:     { color: 'default', label: '草稿' },
  issued:    { color: 'blue',    label: '已發出' },
  cancelled: { color: 'red',     label: '已取消' },
}

function errMsg(err: any, fallback: string) {
  return err?.response?.data?.detail || fallback
}

export default function CpPODetailPage() {
  const { id } = useParams<{ id: string }>()
  const poId = Number(id)
  const navigate = useNavigate()
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const canBuy = hasPermission('cycle_purchase_buyer')

  const [detail, setDetail] = useState<CpPODetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [notes, setNotes] = useState('')
  const [expectedDate, setExpectedDate] = useState<dayjs.Dayjs | null>(null)
  const [saving, setSaving] = useState(false)
  const [acting, setActing] = useState(false)

  const editable = canBuy && detail?.status === 'draft'

  const load = async () => {
    if (!poId) return
    setLoading(true)
    try {
      const d = (await getPo(poId)).data
      setDetail(d)
      setNotes(d.notes || '')
      setExpectedDate(d.expected_date ? dayjs(d.expected_date) : null)
    } catch (err: any) {
      message.error(errMsg(err, '載入失敗'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [poId])

  const handleSaveNotes = async () => {
    if (!detail) return
    setSaving(true)
    try {
      await updatePo(detail.id, {
        notes: notes.trim() || null,
        expected_date: expectedDate ? expectedDate.format('YYYY-MM-DD') : null,
      })
      message.success('已儲存')
      load()
    } catch (err: any) {
      message.error(errMsg(err, '儲存失敗'))
    } finally {
      setSaving(false)
    }
  }

  const handleIssue = async () => {
    if (!detail) return
    setActing(true)
    try {
      await setPoStatus(detail.id, 'issued')
      message.success('已發出')
      load()
    } catch (err: any) {
      message.error(errMsg(err, '發出失敗'))
    } finally {
      setActing(false)
    }
  }

  const handleCancel = async () => {
    if (!detail) return
    setActing(true)
    try {
      await setPoStatus(detail.id, 'cancelled')
      message.success('已取消')
      load()
    } catch (err: any) {
      message.error(errMsg(err, '取消失敗'))
    } finally {
      setActing(false)
    }
  }

  if (!detail) {
    return (
      <div>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/pos')} style={{ marginBottom: 16 }}>
          返回清單
        </Button>
        <Card loading={loading} />
      </div>
    )
  }

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cycle-purchase/pos')}>返回清單</Button>
          <Title level={4} style={{ margin: 0 }}>{detail.po_no}</Title>
          <Tag color={STATUS_TAG[detail.status]?.color}>{STATUS_TAG[detail.status]?.label || detail.status}</Tag>
        </Space>
        {canBuy && (
          <Space>
            {detail.status === 'draft' && (
              <Button type="primary" icon={<CheckOutlined />} loading={acting} onClick={handleIssue}>
                發出
              </Button>
            )}
            {(detail.status === 'draft' || detail.status === 'issued') && (
              <Popconfirm title="確定取消這張採購單？" onConfirm={handleCancel}>
                <Button danger icon={<CloseOutlined />} loading={acting}>取消採購單</Button>
              </Popconfirm>
            )}
          </Space>
        )}
      </Space>

      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={3} size="small" bordered>
          <Descriptions.Item label="週期">{detail.cycle_name}</Descriptions.Item>
          <Descriptions.Item label="期別">{detail.period_label}</Descriptions.Item>
          <Descriptions.Item label="公司">{detail.company}</Descriptions.Item>
          <Descriptions.Item label="供應商">{detail.vendor_name}</Descriptions.Item>
          <Descriptions.Item label="採購人員">{detail.buyer_name || '—'}</Descriptions.Item>
          <Descriptions.Item label="總金額">
            <Text strong>{Number(detail.total_amount).toLocaleString()}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="預計到貨日">
            {editable ? (
              <DatePicker
                style={{ width: 180 }}
                value={expectedDate}
                onChange={setExpectedDate}
                placeholder="選擇日期（選填）"
              />
            ) : (detail.expected_date || '—')}
          </Descriptions.Item>
          <Descriptions.Item label="備註" span={2}>
            {editable ? (
              <TextArea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="備註（選填）"
              />
            ) : (detail.notes || '—')}
          </Descriptions.Item>
        </Descriptions>
        {editable && (
          <div style={{ marginTop: 12, textAlign: 'right' }}>
            <Button icon={<SaveOutlined />} loading={saving} onClick={handleSaveNotes}>儲存預計到貨日／備註</Button>
          </div>
        )}
      </Card>

      {detail.status === 'cancelled' && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="這張採購單已取消"
          description="對應的彙整列仍維持「已轉採購單」狀態，不會自動解鎖回草稿；如需重新採購，請與系統管理員確認後續處理方式。"
        />
      )}

      <Card title="採購明細">
        <Table
          dataSource={detail.items}
          rowKey="id"
          size="small"
          pagination={false}
          columns={[
            { title: '料號', dataIndex: 'item_code', width: 110 },
            { title: '品名', dataIndex: 'item_name' },
            { title: '單位', dataIndex: 'unit', width: 70 },
            {
              title: '單價',
              dataIndex: 'unit_price',
              width: 100,
              align: 'right' as const,
              render: (v?: number | null) => (v == null ? '—' : Number(v).toLocaleString()),
            },
            { title: '訂購數量', dataIndex: 'ordered_qty', width: 100, align: 'right' as const },
            {
              title: '小計',
              dataIndex: 'subtotal',
              width: 110,
              align: 'right' as const,
              render: (v: number) => Number(v).toLocaleString(),
            },
          ]}
        />
      </Card>
    </div>
  )
}
