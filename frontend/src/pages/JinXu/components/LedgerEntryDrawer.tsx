/**
 * 金旭分析 — 交易分錄明細 Drawer
 * CLAUDE.md §7 明細 Drawer 強制規範 ／ 規格書 §13.7
 *
 * 本模組資料來源非 Ragic，故「🔗 在 Ragic 查看」替換為「🔗 原始資料列」，
 * 其餘規範完全比照（標題列格式、分區、彩色 Tag、$ 前綴、空值 —、粗體）。
 *
 * ⚠️ J17：FCR02 的「備註」欄全站不顯示。後端不回傳，此處也不得新增。
 */
import { useEffect, useState } from 'react'
import { Descriptions, Drawer, Space, Table, Tag, Typography, Spin, Empty } from 'antd'
import { LinkOutlined } from '@ant-design/icons'
import { fetchLedgerEntry } from '@/api/jinxu'
import type { LedgerEntry, LedgerEntryDetail } from '@/types/jinxu'
import { GROUP_COLORS, STATUS_COLORS, dash, fmtMoney, moneyStyle } from './constants'

const { Text } = Typography

interface Props {
  entryId: number | null
  open: boolean
  onClose: () => void
}

export default function LedgerEntryDrawer({ entryId, open, onClose }: Props) {
  const [data, setData] = useState<LedgerEntryDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  useEffect(() => {
    if (!open || !entryId) return
    setLoading(true)
    setShowRaw(false)
    fetchLedgerEntry(entryId)
      .then(setData)
      .finally(() => setLoading(false))
  }, [entryId, open])

  // ── 標題列（MANDATORY 格式）───────────────────────────────────────────────
  //    [科目大類 Tag]  金旭客帳分錄：[create_seq]  [🔗 原始資料列]
  const title = (
    <Space size="middle" wrap>
      {data && (
        <Tag color={GROUP_COLORS[data.subject_group] || '#bdc3c7'}>
          {data.subject_group_label}
        </Tag>
      )}
      <Text strong>金旭客帳分錄：{data?.create_seq || '—'}</Text>
      <a
        onClick={(e) => { e.preventDefault(); setShowRaw((v) => !v) }}
        style={{ color: '#4BA8E8' }}
        href="#raw"
      >
        <LinkOutlined /> 原始資料列
      </a>
    </Space>
  )

  const relatedCols = [
    { title: '營業日', dataIndex: 'business_date', width: 105 },
    {
      title: '科目', dataIndex: 'subject_code', width: 150,
      render: (_: unknown, r: LedgerEntry) => (
        <Tag color={GROUP_COLORS[r.subject_group] || '#bdc3c7'}>
          {r.subject_code}.{r.subject_name}
        </Tag>
      ),
    },
    {
      title: '金額', dataIndex: 'amount', align: 'right' as const, width: 110,
      render: (v: number) => <Text strong style={moneyStyle(v)}>{fmtMoney(v)}</Text>,
    },
    { title: '帳單別', dataIndex: 'folio_type', width: 80, render: dash },
    {
      title: '沖帳', dataIndex: 'is_reversal', width: 70,
      render: (v: number) => (v ? <Tag color="error">沖帳</Tag> : '—'),
    },
  ]

  return (
    <Drawer title={title} open={open} onClose={onClose} width={480} destroyOnClose>
      {loading && <Spin />}
      {!loading && !data && <Empty description="查無資料" />}
      {!loading && data && (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* ① 基本欄位 */}
          <Descriptions title="基本欄位" column={1} size="small" bordered>
            <Descriptions.Item label="營業日">
              <Text strong>{dash(data.business_date)}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="建檔時間">{dash(data.created_at_text)}</Descriptions.Item>
            <Descriptions.Item label="班別">{dash(data.shift)}</Descriptions.Item>
            <Descriptions.Item label="操作員">{dash(data.operator_id)}</Descriptions.Item>
            <Descriptions.Item label="房號">
              {dash(data.room_no)}{' '}
              {data.room_kind !== 'GUEST' && <Tag color="default">非客房</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="科目">
              <Text strong>
                <Tag color={GROUP_COLORS[data.subject_group] || '#bdc3c7'}>
                  {data.subject_code}.{data.subject_name}
                </Tag>
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="金額">
              <Text strong style={moneyStyle(data.amount)}>{fmtMoney(data.amount)}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="帳單別">
              <Tag>{dash(data.folio_type)}</Tag>
            </Descriptions.Item>
          </Descriptions>

          {/* ② 明細欄位 */}
          <Descriptions title="明細欄位" column={1} size="small" bordered>
            <Descriptions.Item label="帳單名稱">{dash(data.folio_name)}</Descriptions.Item>
            <Descriptions.Item label="帳單序號">{dash(data.folio_seq)}</Descriptions.Item>
            <Descriptions.Item label="訂房號碼">{dash(data.booking_no)}</Descriptions.Item>
            <Descriptions.Item label="單據號碼">{dash(data.document_no)}</Descriptions.Item>
            <Descriptions.Item label="應收代碼">{dash(data.ar_code)}</Descriptions.Item>
            <Descriptions.Item label="轉帳單號">{dash(data.transfer_no)}</Descriptions.Item>
            <Descriptions.Item label="沖帳標記">
              {data.is_reversal ? <Tag color="error">沖帳</Tag> : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="純記錄分錄">
              {data.is_memo_only ? <Tag color="default">是（不計入收入）</Tag> : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="房間類別">
              <Tag color={data.room_kind === 'GUEST' ? 'blue' : 'default'}>
                {data.room_kind === 'GUEST' ? '客房' : '非客房'}
              </Tag>
            </Descriptions.Item>
          </Descriptions>

          {/* 原始資料列（取代「在 Ragic 查看」） */}
          {showRaw && (
            <Descriptions title="原始資料列" column={1} size="small" bordered>
              <Descriptions.Item label="建檔時間（業務鍵）">{data.create_seq}</Descriptions.Item>
              <Descriptions.Item label="日期（營業日）">{data.business_date}</Descriptions.Item>
              <Descriptions.Item label="班別">{dash(data.shift)}</Descriptions.Item>
              <Descriptions.Item label="ID">{dash(data.operator_id)}</Descriptions.Item>
              <Descriptions.Item label="房號">{dash(data.room_no)}</Descriptions.Item>
              <Descriptions.Item label="帳單名稱">{dash(data.folio_name)}</Descriptions.Item>
              <Descriptions.Item label="科目">
                {data.subject_code}.{data.subject_name}
              </Descriptions.Item>
              <Descriptions.Item label="金額">{data.amount}</Descriptions.Item>
              <Descriptions.Item label="訂房號碼">{dash(data.booking_no)}</Descriptions.Item>
              <Descriptions.Item label="帳單別">{dash(data.folio_type)}</Descriptions.Item>
            </Descriptions>
          )}

          {/* 關聯訂房 */}
          {data.reservation && (
            <Descriptions title="關聯訂房" column={1} size="small" bordered>
              <Descriptions.Item label="訂房號碼">
                <Text strong>{data.reservation.booking_no}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="狀態">
                <Tag color={STATUS_COLORS[data.reservation.status_code] || 'default'}>
                  {data.reservation.status_label}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="住客">
                {dash(data.reservation.guest_name_masked)}
              </Descriptions.Item>
              <Descriptions.Item label="住宿期間">
                {data.reservation.arrival_date} ~ {data.reservation.departure_date}
              </Descriptions.Item>
              <Descriptions.Item label="通路">
                {dash(data.reservation.company_name)}
              </Descriptions.Item>
            </Descriptions>
          )}

          {/* 同訂房的其他分錄 */}
          {data.related_entries && data.related_entries.length > 0 && (
            <div>
              <Text strong>同訂房其他分錄（{data.related_entries.length} 筆）</Text>
              <Table
                rowKey="id"
                size="small"
                style={{ marginTop: 8 }}
                pagination={false}
                scroll={{ y: 240 }}
                columns={relatedCols}
                dataSource={data.related_entries}
              />
            </div>
          )}
        </Space>
      )}
    </Drawer>
  )
}
