/**
 * 即時營運 — 營收與結構分析（/realtime/revenue）
 *
 * 規格書：docs/SPEC_realtime_operations.md §8.3
 * 使用手冊：docs/MANUAL_realtime_operations.md §4
 *
 * ⚠️ 這一頁刻意**不複製**「營運分析」既有的圖表，只做 TXT 版**做不到**的四件事：
 *      ① 房型別營收／ADR（TXT 只有全館）
 *      ② 市場區隔別營收（TXT 完全沒有）
 *      ③ 取消率（TXT 沒有 cancelledRooms，算不出來）
 *      ④ out of service 房（TXT 只有 OOO）
 *
 * ⚠️ 走**非同步** API：POST 啟動 → 輪詢 → GET，實測單段約 3 秒。
 *    超過 94 天自動切段，查一年（4 段）約 12 秒 —— 所以查詢是**手動觸發**，
 *    不做自動載入，避免使用者一進頁面就卡 12 秒。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, DatePicker, Descriptions, Empty, Row, Space, Spin,
  Statistic, Table, Tabs, Tag, Tooltip, Typography,
} from 'antd'
import {
  ApiOutlined, DatabaseOutlined, SearchOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'

import { fetchApiRevenue } from '@/api/realtime'
import SourceBar from '../components/SourceBar'
import type {
  ApiRevenueDay, ApiRevenueGroupRow, ApiRevenueResult,
} from '@/types/realtime'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct,
} from '@/pages/Opera/components/formatters'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

/**
 * 非同步 API 單段上限的**預設顯示值**；超過會自動切段，要讓使用者知道會變慢。
 * ⚠️ 真正的上限由後端決定（先試 400、被拒降回 94），查詢後改用 `source.max_span_days`。
 */
const DEFAULT_MAX_SPAN = 400

/** 秒 → 「X 分 Y 秒」 */
const fmtCountdown = (sec: number): string =>
  `${Math.floor(sec / 60)} 分 ${String(sec % 60).padStart(2, '0')} 秒`

const RealtimeRevenuePage: React.FC = () => {
  const [range, setRange] = useState<[Dayjs, Dayjs]>(() => [
    dayjs().subtract(1, 'month').startOf('month'),
    dayjs().subtract(1, 'month').endOf('month'),
  ])
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ApiRevenueResult | null>(null)
  const [error, setError] = useState('')
  /**
   * 距離可以再次取數還剩幾秒。
   * ⚠️ 這是 **OPERA 端的硬規定**（相同條件的非同步查詢最短間隔 30 分鐘），
   *    不是 Portal 自訂的節流。Portal 只是在本地先擋下，
   *    免得使用者按了之後被 OPERA 拒絕，還白白消耗一次計費呼叫。
   */
  const [cooldown, setCooldown] = useState(0)

  const maxSpan = data?.source?.max_span_days ?? DEFAULT_MAX_SPAN
  const days = range ? range[1].diff(range[0], 'day') + 1 : 0
  const segments = Math.max(Math.ceil(days / maxSpan), 1)

  // 每秒倒數。歸零後按鈕自動恢復可按，不需要使用者重整頁面。
  useEffect(() => {
    if (cooldown <= 0) return
    const t = setInterval(() => setCooldown((c) => Math.max(c - 1, 0)), 1000)
    return () => clearInterval(t)
  }, [cooldown])

  const run = useCallback(async (force = false) => {
    if (!range) return
    setLoading(true)
    setError('')
    try {
      const res = await fetchApiRevenue({
        start: range[0].format('YYYY-MM-DD'),
        end: range[1].format('YYYY-MM-DD'),
        // 一次把兩個維度都要回來，省得使用者分兩次查（分兩次 = 兩倍 API 呼叫）
        group_by: ['MarketCode', 'RoomType'],
        force,
      })
      setData(res)
      setCooldown(res.source?.cooldown_remaining_seconds ?? 0)
    } catch (e: any) {
      // 429 = 冷卻未過（後端本地擋下，沒有真的打 OHIP），Retry-After 是剩餘秒數
      if (e?.response?.status === 429) {
        const retry = Number(e.response.headers?.['retry-after'])
        setCooldown(Number.isFinite(retry) && retry > 0 ? retry : 1800)
      }
      setError(e?.response?.data?.detail || '查詢營收失敗')
    } finally {
      setLoading(false)
    }
  }, [range])

  const summary = data?.summary
  const src = data?.source

  // 全館逐日：把 groupBy 拆出來的列合併回每日一列
  const houseDays = useMemo(() => {
    if (!data?.days?.length) return []
    const byDate = new Map<string, ApiRevenueDay>()
    for (const d of data.days) {
      const cur = byDate.get(d.business_date)
      if (!cur) {
        byDate.set(d.business_date, { ...d })
        continue
      }
      for (const k of ['rooms_sold', 'room_revenue', 'total_revenue',
        'cancelled_rooms', 'arrival_rooms', 'departure_rooms'] as const) {
        const a = cur[k], b = d[k]
        if (a !== null && b !== null) (cur[k] as number) = a + b
        else if (a === null) (cur[k] as any) = b
      }
    }
    const rows = Array.from(byDate.values())
    for (const r of rows) {
      r.adr = (r.room_revenue !== null && r.rooms_sold) ? r.room_revenue / r.rooms_sold : null
      r.revpar = (r.room_revenue !== null && r.available_rooms) ? r.room_revenue / r.available_rooms : null
      r.occupancy = (r.rooms_sold !== null && r.available_rooms) ? r.rooms_sold / r.available_rooms : null
    }
    return rows.sort((a, b) => a.business_date.localeCompare(b.business_date))
  }, [data])

  const dayColumns: ColumnsType<ApiRevenueDay> = [
    { title: '日期', dataIndex: 'business_date', width: 120, fixed: 'left' },
    { title: '房租營收', dataIndex: 'room_revenue', width: 130, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : <Text strong>{fmtMoney(v)}</Text>) },
    { title: '總營收', dataIndex: 'total_revenue', width: 130, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : fmtMoney(v)) },
    { title: 'ADR', dataIndex: 'adr', width: 110, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : <Text style={{ color: BRAND }}>{fmtMoney(v)}</Text>) },
    { title: 'RevPAR', dataIndex: 'revpar', width: 110, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : fmtMoney(v)) },
    { title: '住房率', dataIndex: 'occupancy', width: 90, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY :
        <Text style={{ color: v >= 0.8 ? GREEN : v >= 0.5 ? ACCENT : ORANGE }}>{fmtPct(v)}</Text>) },
    { title: '售出', dataIndex: 'rooms_sold', width: 80, align: 'right', render: (v) => fmtInt(v) },
    { title: '可售', dataIndex: 'available_rooms', width: 80, align: 'right', render: (v) => fmtInt(v) },
    {
      title: <Tooltip title="TXT 報表沒有這個欄位">取消 <Tag color={ACCENT}>新</Tag></Tooltip>,
      dataIndex: 'cancelled_rooms', width: 100, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY :
        <Text style={{ color: v > 0 ? RED : GREY }}>{fmtInt(v)}</Text>),
    },
    { title: '到達', dataIndex: 'arrival_rooms', width: 80, align: 'right', render: (v) => fmtInt(v) },
    { title: '離店', dataIndex: 'departure_rooms', width: 80, align: 'right', render: (v) => fmtInt(v) },
  ]

  const groupColumns = (key: 'market_code' | 'room_type', label: string): ColumnsType<ApiRevenueGroupRow> => [
    { title: label, dataIndex: key, width: 160, fixed: 'left',
      render: (v: string) => <Text strong>{v || EMPTY}</Text> },
    { title: '房租營收', dataIndex: 'room_revenue', width: 140, align: 'right',
      render: (v: number) => <Text strong>{fmtMoney(v)}</Text>,
      sorter: (a, b) => a.room_revenue - b.room_revenue, defaultSortOrder: 'descend' },
    { title: '佔比', width: 100, align: 'right',
      render: (_, r) => {
        const total = summary?.room_revenue || 0
        return total ? fmtPct(r.room_revenue / total) : EMPTY
      } },
    { title: 'ADR', dataIndex: 'adr', width: 110, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : fmtMoney(v)),
      sorter: (a, b) => (a.adr || 0) - (b.adr || 0) },
    { title: '售出房晚', dataIndex: 'rooms_sold', width: 100, align: 'right',
      render: (v: number) => fmtInt(v), sorter: (a, b) => a.rooms_sold - b.rooms_sold },
    { title: '取消', dataIndex: 'cancelled_rooms', width: 90, align: 'right',
      render: (v: number) => (v ? <Text style={{ color: RED }}>{fmtInt(v)}</Text> : EMPTY) },
    { title: '到達', dataIndex: 'arrival_rooms', width: 90, align: 'right', render: (v) => fmtInt(v) },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0, color: BRAND }}>營收與結構分析</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          資料來自 OPERA Cloud 非同步營收 API。本頁只做「營運分析」<Text strong>做不到</Text>的分析，
          不重複既有圖表。
        </Text>
      </Space>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="這一頁的價值在於 TXT 報表沒有的四件事"
        description={
          <Space direction="vertical" size={2}>
            <span>① <Text strong>房型別</Text>營收與 ADR —— 上傳的 TXT 只有全館合計</span>
            <span>② <Text strong>市場區隔別</Text>營收 —— TXT 完全沒有這個維度</span>
            <span>③ <Text strong>取消率</Text> —— TXT 沒有 `cancelledRooms`，算不出來</span>
            <span>④ <Text strong>out of service 房</Text> —— TXT 只有 OOO，分不出維修與停售</span>
          </Space>
        }
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap size={16}>
          <RangePicker
            value={range}
            onChange={(v) => v && setRange(v as [Dayjs, Dayjs])}
            allowClear={false}
          />
          <Button type="primary" icon={<SearchOutlined />} loading={loading}
                  onClick={() => run(false)}>
            查詢
          </Button>
          {data && (
            <Tooltip
              title={cooldown > 0
                ? `OPERA 規定相同查詢條件最短間隔 30 分鐘，還需等待 ${fmtCountdown(cooldown)}。
                   想馬上看新資料的話，可以改一下查詢區間 —— 條件不同就不受此限。`
                : '重新向 OPERA 取數，不使用快取'}
            >
              {/* Tooltip 包 disabled 按鈕時需要一層 span，否則不會觸發 */}
              <span>
                <Button size="small" onClick={() => run(true)} loading={loading}
                        disabled={cooldown > 0}>
                  {cooldown > 0
                    ? `重查冷卻中（${fmtCountdown(cooldown)}）`
                    : '略過快取重查'}
                </Button>
              </span>
            </Tooltip>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            {days} 天
            {segments > 1 && (
              <Text type="warning" style={{ fontSize: 12 }}>
                　⚠️ 超過 {maxSpan} 天，會切成 <Text strong>{segments}</Text> 段查詢，
                每段約 3 秒（預估 {segments * 3} 秒）
              </Text>
            )}
          </Text>
        </Space>
      </Card>

      {error && (
        <Alert
          type={cooldown > 0 ? 'warning' : 'error'}
          showIcon
          message={cooldown > 0 ? '這組條件還在冷卻中' : '查詢失敗'}
          description={error}
          style={{ marginBottom: 16 }}
        />
      )}

      {data?.source?.span_downgraded && (
        <Alert
          type="info" showIcon style={{ marginBottom: 16 }}
          message="查詢區間上限已自動降為 94 天"
          description={
            <span>
              曾嘗試以 {data.source.preferred_span_days ?? 400} 天為單段查詢但被 OPERA 拒絕，
              研判此環境的 OPERA Cloud 版本低於 23.2。系統已自動改用 94 天切段，
              功能不受影響，只是段數較多、查詢較慢。
            </span>
          }
        />
      )}

      {data && !data.configured && (
        <Alert type="info" showIcon message="OPERA API 尚未設定完成"
               description={<span>後端缺少：<Text code>{data.missing.join('、')}</Text></span>} />
      )}

      <Spin spinning={loading} tip={`查詢中（${segments} 段，約 ${segments * 3} 秒）…`}>
        {data?.configured && summary && (
          <>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={12} sm={8} md={4}>
                  <Statistic title="房租營收" value={summary.room_revenue} precision={0}
                             valueStyle={{ color: BRAND }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    總營收 {fmtMoney(summary.total_revenue)}
                  </Text>
                </Col>
                <Col xs={12} sm={8} md={4}>
                  <Statistic title="ADR" value={summary.adr ?? 0} precision={0}
                             valueStyle={{ color: BRAND }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>加權，非逐日平均</Text>
                </Col>
                <Col xs={12} sm={8} md={4}>
                  <Statistic title="RevPAR" value={summary.revpar ?? 0} precision={0}
                             valueStyle={{ color: BRAND }} />
                </Col>
                <Col xs={12} sm={8} md={4}>
                  <Statistic title="住房率"
                             value={(summary.occupancy ?? 0) * 100} precision={1} suffix="%"
                             valueStyle={{ color: (summary.occupancy ?? 0) >= 0.7 ? GREEN : ORANGE }} />
                </Col>
                <Col xs={12} sm={8} md={4}>
                  <Statistic title="取消率"
                             value={(summary.cancel_rate ?? 0) * 100} precision={2} suffix="%"
                             valueStyle={{ color: RED }} />
                  <Tag color={ACCENT} style={{ fontSize: 10 }}>TXT 算不出來</Tag>
                </Col>
                <Col xs={12} sm={8} md={4}>
                  <Statistic title="其他收入" value={summary.other_revenue} precision={0}
                             valueStyle={{ color: GREY }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>總營收 − 房租</Text>
                </Col>
              </Row>
            </Card>

            {data.notes?.length > 0 && (
              <Alert
                type="warning" showIcon style={{ marginBottom: 16 }}
                message="這批資料的欄位狀況"
                description={
                  <ul style={{ margin: 0, paddingInlineStart: 20 }}>
                    {data.notes.map((n) => <li key={n}>{n}</li>)}
                  </ul>
                }
              />
            )}

            <Card size="small">
              <Tabs
                size="small"
                items={[
                  {
                    key: 'daily',
                    label: '逐日',
                    children: (
                      <Table<ApiRevenueDay>
                        size="small" rowKey="business_date"
                        columns={dayColumns} dataSource={houseDays}
                        pagination={{ pageSize: 31, showSizeChanger: false }}
                        scroll={{ x: 1200 }}
                      />
                    ),
                  },
                  {
                    key: 'roomType',
                    label: <span>房型別 <Tag color={ACCENT}>TXT 沒有</Tag></span>,
                    children: data.by_room_type?.length ? (
                      <Table<ApiRevenueGroupRow>
                        size="small" rowKey={(r) => r.room_type || ''}
                        columns={groupColumns('room_type', '房型')}
                        dataSource={data.by_room_type}
                        pagination={false} scroll={{ x: 800 }}
                      />
                    ) : <Empty description="此區間沒有房型別資料" />,
                  },
                  {
                    key: 'market',
                    label: <span>市場區隔 <Tag color={ACCENT}>TXT 沒有</Tag></span>,
                    children: data.by_market?.length ? (
                      <>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          依 OPERA 的 Market Code 分組。這個維度可用來判斷「散客 vs 團體」，
                          但<Text strong>語意不完全等同</Text>於 TXT 的四類拆分，請先確認貴飯店的 market code 設定。
                        </Text>
                        <Table<ApiRevenueGroupRow>
                          size="small" rowKey={(r) => r.market_code || ''}
                          columns={groupColumns('market_code', '市場區隔')}
                          dataSource={data.by_market}
                          pagination={false} scroll={{ x: 800 }}
                          style={{ marginTop: 8 }}
                        />
                      </>
                    ) : <Empty description="此區間沒有市場區隔資料" />,
                  },
                ]}
              />

              <SourceBar source={src} />
            </Card>
          </>
        )}

        {!data && !loading && !error && (
          <Empty description="選好區間後按「查詢」" />
        )}
      </Spin>
    </div>
  )
}

export default RealtimeRevenuePage
