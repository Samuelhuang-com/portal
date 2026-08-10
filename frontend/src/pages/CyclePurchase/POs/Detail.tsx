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
 *
 * 2026-08-09（上面那件事已與 Samuel 確認，新增「退回彙整單」）：
 * **「取消」與「退回彙整單」是兩個不同動作，不要混用：**
 *   - **取消**：這批本期不買了。彙整列**維持鎖定**（維持原本行為，沒有改）。
 *   - **退回彙整單**：採購單作廢，且把對應的彙整列**解鎖回 draft**、清掉 po_id，
 *     讓買家重新調整調整量後再轉一張新的採購單（新單號，舊單保留為已取消供追溯）。
 *
 * ⚠️ 順帶修掉一個既有死鎖：改版前「取消」不解鎖彙整列，加上採購單原本的
 *    UniqueConstraint 不分狀態，導致取消後既不能重新轉單、彙整列也退不回請購單
 *    ——那批彙整列等於永久鎖死。所以 cancelled 狀態**也保留「退回彙整單」入口**，
 *    讓既有的死鎖資料有解套路徑。
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert, Button, Card, DatePicker, Descriptions, Form, Input, Modal, Popconfirm,
  Space, Table, Tag, Typography, message,
} from 'antd'
import {
  ArrowLeftOutlined, CheckOutlined, CloseOutlined, RollbackOutlined, SaveOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { getPo, revertPoToSummary, setPoStatus, updatePo } from '@/api/cyclePurchase'
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
  const [revertModal, setRevertModal] = useState(false)
  const [revertReason, setRevertReason] = useState('')
  const [reverting, setReverting] = useState(false)

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

  // 2026-08-09：退回彙整單。與「取消」是兩個不同動作，差別見檔案開頭說明。
  const handleRevert = async () => {
    if (!detail) return
    if (!revertReason.trim()) {
      message.warning('請填寫退回原因')
      return
    }
    setReverting(true)
    try {
      const res = await revertPoToSummary(detail.id, { reason: revertReason.trim() })
      message.success(res.data.message)
      setRevertModal(false)
      setRevertReason('')
      if (res.data.next_step) {
        Modal.info({
          title: '退回完成，接下來',
          width: 560,
          content: <div style={{ whiteSpace: 'pre-wrap' }}>{res.data.next_step}</div>,
          okText: '知道了',
        })
      }
      load()
    } catch (err: any) {
      message.error(errMsg(err, '退回失敗'))
    } finally {
      setReverting(false)
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
            {/* 退回彙整單：draft／issued 都能退；cancelled 也保留入口，因為改版前
                「取消」不會解鎖彙整列，那些舊資料的彙整列還鎖著，要靠這裡解套。 */}
            {(detail.status === 'draft' || detail.status === 'issued' || detail.status === 'cancelled') && (
              <Button
                icon={<RollbackOutlined />}
                loading={reverting}
                onClick={() => { setRevertReason(''); setRevertModal(true) }}
              >
                退回彙整單
              </Button>
            )}
            {(detail.status === 'draft' || detail.status === 'issued') && (
              <Popconfirm
                title="確定取消這張採購單？"
                description="取消後彙整列仍維持鎖定。若要重新調整再轉單，請改用「退回彙整單」。"
                onConfirm={handleCancel}
              >
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
          description={
            detail.items.length === 0
              ? '這張單已經退回彙整單：明細已清空、對應的彙整列已解鎖回草稿，可以重新調整後再轉出一張新的採購單（退回原因見上方備註）。'
              : '「取消」不會解鎖對應的彙整列（它們仍是「已轉採購單」）。若要重新調整再轉單，請按上方的「退回彙整單」。'
          }
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

      <Modal
        title={`退回彙整單 — ${detail.po_no}`}
        open={revertModal}
        onOk={handleRevert}
        onCancel={() => { setRevertModal(false); setRevertReason('') }}
        okText="確定退回"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        confirmLoading={reverting}
        width={620}
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="這個動作會做三件事"
          description={(
            <ol style={{ paddingLeft: 18, margin: 0 }}>
              <li>這張採購單標為<b>已取消</b>（單號保留供追溯）</li>
              <li><b>刪除採購明細</b>（內容會完整記在稽核紀錄裡）</li>
              <li>對應的彙整列<b>解鎖回草稿</b>，可以重新調整後再轉出一張<b>新</b>的採購單</li>
            </ol>
          )}
        />
        {detail.status === 'issued' && (
          <Alert
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            message="這張採購單已經發出（issued）"
            description="退回不會通知供應商，記得自行聯繫對方作廢。"
          />
        )}
        <Form layout="vertical">
          <Form.Item label="退回原因" required extra="會寫進採購單備註與稽核紀錄">
            <TextArea
              rows={3}
              value={revertReason}
              onChange={(e) => setRevertReason(e.target.value)}
              placeholder="例如：數量算錯要重新調整、供應商報價變動、部門需求變更"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
