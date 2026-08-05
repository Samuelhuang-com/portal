/**
 * 金旭分析 — 訂房明細 Drawer
 * CLAUDE.md §7 明細 Drawer 強制規範 ／ 規格書 §13.7
 *
 * 寬度 640px（比分錄寬）——要放住宿明細段與關聯分錄兩張表。
 *
 * ⚠️ 住客姓名一律顯示遮罩後版本，Drawer 內**不提供解遮罩**（§15.3）。
 * ⚠️ J17：關聯分錄不顯示備註欄。
 */
import { useEffect, useState } from 'react'
import { Alert, Descriptions, Drawer, Empty, Space, Spin, Table, Tag, Typography } from 'antd'
import { LinkOutlined } from '@ant-design/icons'
import { fetchResvDetail } from '@/api/jinxu'
import type { LedgerEntry, ReservationDetail, StaySegment } from '@/types/jinxu'
import { GROUP_COLORS, STATUS_COLORS, dash, fmtInt, fmtMoney, fmtPct, moneyStyle } from './constants'

const { Text } = Typography

interface Props {
  resvId: number | null
  open: boolean
  onClose: () => void
}

export default function ReservationDrawer({ resvId, open, onClose }: Props) {
  const [data, setData] = useState<ReservationDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  useEffect(() => {
    if (!open || !resvId) return
    setLoading(true)
    setShowRaw(false)
    fetchResvDetail(resvId).then(setData).finally(() => setLoading(false))
  }, [resvId, open])

  // ── 標題列（MANDATORY 格式）───────────────────────────────────────────────
  //    [狀態 Tag]  金旭訂房：[訂房號碼]  [🔗 原始資料列]
  const title = (
    <Space size="middle" wrap>
      {data && (
        <Tag color={STATUS_COLORS[data.status_code] || 'default'}>{data.status_label}</Tag>
      )}
      <Text strong>金旭訂房：{data?.booking_no || '—'}</Text>
      <a
        onClick={(e) => { e.preventDefault(); setShowRaw((v) => !v) }}
        style={{ color: '#4BA8E8' }}
        href="#raw"
      >
        <LinkOutlined /> 原始資料列
      </a>
    </Space>
  )

  const segCols = [
    { title: '#', dataIndex: 'seq_no', width: 44 },
    {
      title: '房型', dataIndex: 'room_type_code', width: 70,
      // J23：只顯示代碼，不顯示中文名（房務未提供正式對照表）
      render: (v: string) => <Tag>{v}</Tag>,
    },
    { title: '房數', dataIndex: 'rooms', align: 'right' as const, width: 60 },
    { title: '晚數', dataIndex: 'nights', align: 'right' as const, width: 60 },
    {
      title: '每晚金額', dataIndex: 'amount_per_night', align: 'right' as const, width: 95,
      render: (v: number) => fmtMoney(v),
    },
    {
      title: '每房單價', dataIndex: 'unit_rate', align: 'right' as const, width: 95,
      render: (v: number) => fmtMoney(v),
    },
    { title: '房晚', dataIndex: 'room_nights', align: 'right' as const, width: 60 },
    {
      title: '段總額', dataIndex: 'segment_amount', align: 'right' as const, width: 105,
      render: (v: number) => <Text strong>{fmtMoney(v)}</Text>,
    },
  ]

  const entryCols = [
    { title: '營業日', dataIndex: 'business_date', width: 100 },
    {
      title: '科目', dataIndex: 'subject_code', width: 155,
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
    { title: '帳單別', dataIndex: 'folio_type', width: 78, render: dash },
    {
      title: '沖帳', dataIndex: 'is_reversal', width: 66,
      render: (v: number) => (v ? <Tag color="error">沖帳</Tag> : '—'),
    },
  ]

  return (
    <Drawer title={title} open={open} onClose={onClose} width={640} destroyOnClose>
      {loading && <Spin />}
      {!loading && !data && <Empty description="查無資料" />}
      {!loading && data && (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* ① 基本欄位 */}
          <Descriptions title="基本欄位" column={2} size="small" bordered>
            <Descriptions.Item label="狀態">
              <Tag color={STATUS_COLORS[data.status_code] || 'default'}>{data.status_label}</Tag>
              {data.is_dummy === 1 && <Tag color="default">不計入統計</Tag>}
            </Descriptions.Item>
            <Descriptions.Item label="訂房類別">
              <Tag color={data.is_group ? 'purple' : 'blue'}>{dash(data.resv_type)}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="到達日">
              <Text strong>{dash(data.arrival_date)}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="退房日">
              <Text strong>{dash(data.departure_date)}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="住宿晚數">
              {/* J27：預設顯示 billable（Day Use 算 1 晚），括號附日期差 */}
              <Text strong>{fmtInt(data.billable_nights)} 晚</Text>
              {data.is_day_use === 1 && <Tag color="warning" style={{ marginLeft: 6 }}>Day Use</Tag>}
              <Text type="secondary" style={{ marginLeft: 6, fontSize: 12 }}>
                （日期差 {data.nights}）
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="住客">
              {dash(data.guest_name_masked)}
              {data.guest_is_placeholder === 1 && (
                <Tag color="default" style={{ marginLeft: 6 }}>非個人</Tag>
              )}
            </Descriptions.Item>
          </Descriptions>

          {/* ② 通路欄位 */}
          <Descriptions title="通路欄位" column={1} size="small" bordered>
            <Descriptions.Item label="合約/訂房公司">{dash(data.company_name)}</Descriptions.Item>
            <Descriptions.Item label="業務碼">{dash(data.rate_code)}</Descriptions.Item>
            <Descriptions.Item label="業務源">{dash(data.source_name)}</Descriptions.Item>
          </Descriptions>

          {/* 原始資料列 */}
          {showRaw && (
            <Descriptions title="原始資料列" column={1} size="small" bordered>
              <Descriptions.Item label="訂房號碼（業務鍵）">{data.booking_no}</Descriptions.Item>
              <Descriptions.Item label="訂房/登記狀況">{data.status_code}</Descriptions.Item>
              <Descriptions.Item label="到達日期">{data.arrival_date}</Descriptions.Item>
              <Descriptions.Item label="退房日期">{data.departure_date}</Descriptions.Item>
              <Descriptions.Item label="登記名稱（已遮罩）">
                {dash(data.guest_name_masked)}
              </Descriptions.Item>
              <Descriptions.Item label="合約/訂房公司">{dash(data.company_name)}</Descriptions.Item>
              <Descriptions.Item label="業務碼">{dash(data.rate_code)}</Descriptions.Item>
              <Descriptions.Item label="業務源">{dash(data.source_name)}</Descriptions.Item>
              <Descriptions.Item label="訂房類別">{dash(data.resv_type)}</Descriptions.Item>
              <Descriptions.Item label="住宿資料（拆段前）">
                {data.segments.map((s) => s.raw_segment).join(', ') || '—'}
              </Descriptions.Item>
            </Descriptions>
          )}

          {/* ③ 住宿明細段 */}
          <div>
            <Space>
              <Text strong>住宿明細段（{data.stay_segment_count} 段）</Text>
              {data.has_nights_mismatch === 1 && (
                <Tag color="warning">段晚數與住宿天數不符</Tag>
              )}
            </Space>
            {data.segments.length === 0 ? (
              <Empty description="無住宿資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <>
                <Table<StaySegment>
                  rowKey="seq_no"
                  size="small"
                  style={{ marginTop: 8 }}
                  pagination={false}
                  columns={segCols}
                  dataSource={data.segments}
                  summary={() => (
                    <Table.Summary.Row>
                      <Table.Summary.Cell index={0} colSpan={6}>
                        <Text strong>合計</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={6} align="right">
                        <Text strong>{fmtInt(data.total_room_nights)}</Text>
                      </Table.Summary.Cell>
                      <Table.Summary.Cell index={7} align="right">
                        <Text strong>{fmtMoney(data.total_quoted_amount)}</Text>
                      </Table.Summary.Cell>
                    </Table.Summary.Row>
                  )}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  每晚金額 = 該段一晚的總額（房數 × 單價）；段總額 = 每晚金額 × 晚數
                </Text>
              </>
            )}
          </div>

          {/* ④ 關聯帳務分錄 —— 未匯入 FCR02 時整區隱藏，不顯示空表 */}
          {data.ledger_available ? (
            <div>
              <Text strong>關聯帳務分錄（{data.ledger_entries.length} 筆）</Text>
              <Table<LedgerEntry>
                rowKey="id"
                size="small"
                style={{ marginTop: 8 }}
                pagination={false}
                scroll={{ y: 260 }}
                columns={entryCols}
                dataSource={data.ledger_entries}
              />
              {data.rate_comparison && (
                <Descriptions column={1} size="small" bordered style={{ marginTop: 12 }}>
                  <Descriptions.Item label="訂房報價合計">
                    <Text strong>{fmtMoney(data.rate_comparison.quoted_amount)}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="實收房租合計">
                    <Text strong>{fmtMoney(data.rate_comparison.actual_room_revenue)}</Text>
                  </Descriptions.Item>
                  <Descriptions.Item label="差異">
                    <Text strong style={moneyStyle(data.rate_comparison.gap)}>
                      {fmtMoney(data.rate_comparison.gap)}（{fmtPct(data.rate_comparison.gap_pct, 2)}）
                    </Text>
                  </Descriptions.Item>
                </Descriptions>
              )}
            </div>
          ) : (
            <Alert
              type="info"
              showIcon
              message="尚未匯入「客帳帳目明細表」，無法顯示關聯帳務分錄與訂價／實收比較"
            />
          )}
        </Space>
      )}
    </Drawer>
  )
}
