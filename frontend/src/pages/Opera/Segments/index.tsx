/**
 * 營運分析 — 市場區隔／房型別趨勢（/opera/segments）
 *
 * 決策依據：docs/EVAL_ohip_strategic_data.md §4.3（重寫後的順位 2'）
 *
 * ⚠️ 本頁資料來源是 **OPERA Cloud API 落地**，不是本模組其他頁的 TXT 上傳。
 *    這是「營運分析」裡唯一一頁來源不同的，所以：
 *      ① 標題旁的「?」開啟說明 Modal（內容取後端 `source.note`，不在前端寫死）
 *      ② 期間選擇器的 anchor 用**本模組資料的最後一天**，不是今天（CLAUDE.md §8.2）
 *
 * ⚠️ 市場區隔（Market Code）是飯店在 OPERA 自行設定的分類，
 *    與 TXT 的「散客／團體」四類**不是同一套分類**。本頁不做任何映射猜測。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, Divider, Empty, Modal, Progress, Radio, Row, Space, Spin,
  Statistic, Table, Tabs, Tag, Tooltip, Typography,
} from 'antd'
import {
  ApiOutlined, QuestionCircleOutlined, ReloadOutlined, SyncOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import dayjs from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip as RTooltip, XAxis, YAxis,
} from 'recharts'

import StandardRangePicker from '@/components/StandardRangePicker'
import {
  backfillNextChunk, fetchSegmentSyncStatus, fetchSegments,
} from '@/api/operaSegment'
import type {
  SegmentDimension, SegmentResult, SegmentRow, SegmentSyncStatus,
} from '@/api/operaSegment'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct,
} from '@/pages/Opera/components/formatters'

const { Title, Text } = Typography

/** 圖表配色：品牌主色系往外延伸，避免與既有頁面的狀態色衝突 */
const SERIES_COLORS = [
  '#1B3A5C', '#4BA8E8', '#667eea', '#764ba2', '#e67e22',
  '#16a085', '#c0392b', '#7f8c8d', '#2980b9', '#8e44ad',
]

/** 年增率的顯示：null 代表「去年沒有可比基準」，不是 0 */
const YoY: React.FC<{ value?: number | null; isNew?: boolean }> = ({ value, isNew }) => {
  if (isNew) return <Tag color={ACCENT}>去年沒有</Tag>
  if (value === null || value === undefined) return <Text type="secondary">{EMPTY}</Text>
  const up = value >= 0
  return (
    <Text style={{ color: up ? GREEN : RED }}>
      {up ? '▲' : '▼'} {fmtPct(Math.abs(value))}
    </Text>
  )
}

const OperaSegmentsPage: React.FC = () => {
  const [dimension, setDimension] = useState<SegmentDimension>('market_code')
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [dataEnd, setDataEnd] = useState<string>('')
  const [data, setData] = useState<SegmentResult | null>(null)
  const [sync, setSync] = useState<SegmentSyncStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [backfilling, setBackfilling] = useState(false)
  const [error, setError] = useState('')
  const [helpOpen, setHelpOpen] = useState(false)

  const loadSync = useCallback(async () => {
    try {
      const s = await fetchSegmentSyncStatus()
      setSync(s)
      // ⚠️ anchor 取「本模組資料的最後一天」而不是今天（CLAUDE.md §8.2）——
      //    本模組的增量排程一天跑一次且刻意不含今天，用 dayjs() 當基準
      //    會讓「本月」選到還沒有資料的日子，使用者會誤以為資料缺漏。
      if (s.data_range.end) setDataEnd(s.data_range.end)
      return s
    } catch {
      return null
    }
  }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      // ⚠️ 每次都重抓 sync status，不要用既有的 `sync` 短路 ——
      //    畫面上的「資料涵蓋」必須反映 DB 現況。回補一段之後 data_range 就變了，
      //    短路會讓它一直停在頁面第一次載入時的值，只有整頁 reload 才會更新。
      const s = await loadSync()
      const end = range ? range[1].format('YYYY-MM-DD') : (s?.data_range.end || '')
      const start = range ? range[0].format('YYYY-MM-DD') : (s?.data_range.start || '')
      if (!start || !end) {
        setData(null)
        return
      }
      setData(await fetchSegments({ start, end, dimension, compare_yoy: true }))
    } catch (e: any) {
      setError(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [range, dimension, loadSync])

  // ⚠️ 掛載時只跑 `load()` —— 它內部已經會呼叫 `loadSync()`，
  //    另外再放一個 loadSync 的 useEffect 會讓進頁面重複打兩次 /sync/status。
  useEffect(() => { load() }, [dimension, range])   // eslint-disable-line react-hooks/exhaustive-deps

  /** 補一段就重新整理進度，讓使用者看得到 pending 在減少 */
  const runBackfill = useCallback(async () => {
    setBackfilling(true)
    try {
      const r = await backfillNextChunk()
      setSync((prev) => (prev ? { ...prev, progress: r.progress } : prev))
      // ⚠️ `r.progress` 不含 data_range，但補完一段之後資料範圍就變了。
      //    不重抓的話「資料涵蓋」會停在補之前的值。
      if (r.done) await load()   // load 內部會重抓 sync
      else await loadSync()
    } catch (e: any) {
      setError(e?.response?.data?.detail || '回補失敗')
    } finally {
      setBackfilling(false)
    }
  }, [load, loadSync])

  const dimLabel = dimension === 'market_code' ? '市場區隔' : '房型'
  const summary = data?.summary

  const columns: ColumnsType<SegmentRow> = useMemo(() => [
    {
      title: dimLabel, dataIndex: dimension, width: 150, fixed: 'left',
      render: (v: string) => <Text strong>{v || EMPTY}</Text>,
    },
    {
      title: '房租營收', dataIndex: 'room_revenue', width: 130, align: 'right',
      render: (v: number) => <Text strong>{fmtMoney(v)}</Text>,
      sorter: (a, b) => a.room_revenue - b.room_revenue, defaultSortOrder: 'descend',
    },
    {
      title: '佔比', dataIndex: 'share', width: 90, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : fmtPct(v)),
    },
    {
      title: <Tooltip title="與去年同期相比。去年沒有可比基準時顯示「—」而非 0%">營收 YoY</Tooltip>,
      width: 110, align: 'right',
      render: (_, r) => <YoY value={r.yoy_room_revenue} isNew={r.is_new} />,
    },
    {
      title: 'ADR', dataIndex: 'adr', width: 110, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY :
        <Text style={{ color: BRAND }}>{fmtMoney(v)}</Text>),
      sorter: (a, b) => (a.adr || 0) - (b.adr || 0),
    },
    {
      title: 'ADR YoY', width: 110, align: 'right',
      render: (_, r) => <YoY value={r.yoy_adr} isNew={r.is_new} />,
    },
    {
      title: '售出房晚', dataIndex: 'rooms_sold', width: 100, align: 'right',
      render: (v: number) => fmtInt(v), sorter: (a, b) => a.rooms_sold - b.rooms_sold,
    },
    {
      title: '取消', dataIndex: 'cancelled_rooms', width: 90, align: 'right',
      render: (v: number) => (v ? <Text style={{ color: RED }}>{fmtInt(v)}</Text> : EMPTY),
    },
  ], [dimension, dimLabel])

  /** 逐月堆疊圖用的資料：把 by_dimension 攤平成一列一個月 */
  const chartData = useMemo(() => {
    if (!data?.trend?.length) return []
    return data.trend.map((t) => ({ month: t.month, ...t.by_dimension }))
  }, [data])

  const topKeys = useMemo(
    () => (data?.segments || []).slice(0, 10).map((s) => (s as any)[dimension] as string),
    [data, dimension],
  )

  const prog = sync?.progress
  const backfillDone = prog ? prog.pending_chunks === 0 : false

  /**
   * ⚠️ 優先取 sync status 的 source —— 歷史資料回補完成前 `data` 會是 null
   *    （沒有 data_range 就不查 /segments），而說明恰好是那時候最需要看的。
   */
  const sourceNote = sync?.source?.note || data?.source?.note || ''

  /**
   * 住房率／RevPAR 的分母口徑（v1.96.33）。
   * ⚠️ 依市場區隔看時分母是**全館**可售房 —— 房間不屬於任何一個 market。
   *    不標示的話「OTA 住房率 35.7%」會被讀成「OTA 自己房間的住房率」，
   *    實際語意是「OTA 吃掉了全館可售房的 35.7%」，各列相加才等於全館住房率。
   */
  const occupancyNote = sync?.source?.occupancy_note || data?.source?.occupancy_note || ''
  const denomLabel = dimension === 'market_code' ? '分母：全館可售房' : '分母：該房型可售房'

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
        <Space size={6} align="center">
          <Title level={4} style={{ margin: 0, color: BRAND }}>市場區隔分析</Title>
          {/* ⚠️ 這則說明是本頁的關鍵 —— 營運分析模組裡只有這一頁來源不同 */}
          {sourceNote && (
            <Tooltip title="資料來源說明">
              <Button
                type="text" size="small" aria-label="資料來源說明"
                icon={<QuestionCircleOutlined style={{ color: ACCENT, fontSize: 16 }} />}
                onClick={() => setHelpOpen(true)}
              />
            </Tooltip>
          )}
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>
          依市場區隔與房型看營收結構、逐月趨勢，以及與去年同期的比較。
        </Text>
      </Space>

      <Modal
        open={helpOpen}
        onCancel={() => setHelpOpen(false)}
        footer={null}
        width={520}
        title={
          <Space size={8}>
            <ApiOutlined style={{ color: ACCENT }} />
            <span>這一頁的資料來源與「營運分析」其他頁不同</span>
          </Space>
        }
      >
        <div
          style={{ lineHeight: 1.8 }}
          dangerouslySetInnerHTML={{
            __html: sourceNote.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'),
          }}
        />
        {/* 住房率分母口徑（v1.96.33）—— 與來源說明分開，兩者講的不是同一件事 */}
        {occupancyNote && (
          <>
            <Divider style={{ margin: '16px 0 12px' }} />
            <Text strong style={{ display: 'block', marginBottom: 6 }}>住房率與 RevPAR 的分母</Text>
            <div
              style={{ lineHeight: 1.8 }}
              dangerouslySetInnerHTML={{
                __html: occupancyNote.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'),
              }}
            />
          </>
        )}
      </Modal>

      {/* 回補進度：沒補完就一直顯示，補完自動消失 */}
      {prog && !backfillDone && (
        <Alert
          type="info" showIcon style={{ marginBottom: 16 }}
          message={`歷史資料回補中：已完成 ${prog.done_chunks} / ${prog.total_chunks} 段`}
          description={
            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Progress
                percent={Math.round((prog.done_chunks / Math.max(prog.total_chunks, 1)) * 100)}
                size="small" strokeColor={BRAND}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                每按一次補 {prog.chunk_days} 天（約 3～4 秒）。
                剩餘 {prog.pending_chunks} 段，預估 {prog.estimated_remaining_seconds} 秒。
                <br />
                ⚠️ 刻意不做成「一次補完兩年」—— 那會讓請求逾時。中斷了可以接著按，不必從頭來。
                {prog.next_chunk && <>　下一段：{prog.next_chunk.start} ～ {prog.next_chunk.end}</>}
              </Text>
              <Button type="primary" size="small" icon={<SyncOutlined />}
                      loading={backfilling} onClick={runBackfill}>
                補下一段
              </Button>
            </Space>
          }
        />
      )}

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap size={16}>
          <Radio.Group value={dimension} size="small" buttonStyle="solid"
                       onChange={(e) => setDimension(e.target.value)}>
            <Radio.Button value="market_code">市場區隔</Radio.Button>
            <Radio.Button value="room_type">房型</Radio.Button>
          </Radio.Group>
          {/* ⚠️ anchor 用資料最後一天，不是今天（CLAUDE.md §8.2） */}
          <StandardRangePicker value={range} anchor={dataEnd} onChange={setRange} />
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={load}>
            重新整理
          </Button>
          {/* ⚠️ 這一行直接讀 sync.data_range（DB 現況），不要用 dataEnd ——
              dataEnd 是給 anchor 用的 state，只在有值時才覆寫，會殘留舊值 */}
          {sync?.data_range.end && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              資料涵蓋 {sync.data_range.start} ～ {sync.data_range.end}
              　<Tooltip title="期間快捷（本月／今年…）以資料最後一天為基準，不是今天——否則會選到還沒有資料的日子">
                <Text type="secondary" style={{ fontSize: 12, textDecoration: 'underline dotted' }}>
                  為什麼不是今天？
                </Text>
              </Tooltip>
            </Text>
          )}
        </Space>
      </Card>

      {error && (
        <Alert type="error" showIcon message="載入失敗" description={error}
               style={{ marginBottom: 16 }} />
      )}

      <Spin spinning={loading}>
        {!data || !data.row_count ? (
          <Empty description={
            backfillDone ? '這個期間沒有資料' : '尚未回補歷史資料，請先按上方「補下一段」'
          } />
        ) : (
          <>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col xs={12} sm={8} md={5}>
                  <Statistic title="房租營收" value={summary?.room_revenue} precision={0}
                             valueStyle={{ color: BRAND }} />
                  <YoY value={summary?.yoy_room_revenue} />
                  <Text type="secondary" style={{ fontSize: 11 }}>　vs 去年同期</Text>
                </Col>
                <Col xs={12} sm={8} md={5}>
                  <Statistic title="ADR" value={summary?.adr ?? 0} precision={0}
                             valueStyle={{ color: BRAND }} />
                  <YoY value={summary?.yoy_adr} />
                  <Text type="secondary" style={{ fontSize: 11 }}>　加權，非逐日平均</Text>
                </Col>
                <Col xs={12} sm={8} md={5}>
                  <Statistic title="住房率" value={(summary?.occupancy ?? 0) * 100}
                             precision={1} suffix="%"
                             valueStyle={{ color: (summary?.occupancy ?? 0) >= 0.7 ? GREEN : ORANGE }} />
                  <YoY value={summary?.yoy_occupancy} />
                  {/* ⚠️ 分母口徑必須標在數字旁 —— 放進說明 Modal 沒人會去點 */}
                  {occupancyNote && (
                    <Tooltip title={occupancyNote.replace(/\*\*/g, '')}>
                      <Text type="secondary"
                            style={{ fontSize: 11, borderBottom: '1px dotted #bfbfbf', cursor: 'help' }}>
                        　{denomLabel}
                      </Text>
                    </Tooltip>
                  )}
                </Col>
                <Col xs={12} sm={8} md={4}>
                  <Statistic title={`${dimLabel}數`} value={data.segments.length}
                             valueStyle={{ color: GREY }} />
                </Col>
                <Col xs={12} sm={8} md={5}>
                  <Statistic title="RevPAR" value={summary?.revpar ?? 0} precision={0}
                             valueStyle={{ color: GREY }} />
                </Col>
              </Row>
            </Card>

            <Card size="small">
              <Tabs
                size="small"
                items={[
                  {
                    key: 'structure',
                    label: `${dimLabel}結構`,
                    children: (
                      <Table<SegmentRow>
                        size="small" rowKey={(r) => (r as any)[dimension] || ''}
                        columns={columns} dataSource={data.segments}
                        pagination={false} scroll={{ x: 950 }}
                      />
                    ),
                  },
                  {
                    key: 'trend',
                    label: '逐月趨勢',
                    children: chartData.length ? (
                      <div style={{ width: '100%', height: 380 }}>
                        <ResponsiveContainer>
                          <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="month" />
                            <YAxis tickFormatter={(v) => `${Math.round(v / 10000)}萬`} />
                            <RTooltip formatter={(v: number) => fmtMoney(v)} />
                            <Legend />
                            {topKeys.map((k, i) => (
                              <Bar key={k} dataKey={k} stackId="a"
                                   fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
                            ))}
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    ) : <Empty description="沒有足夠的月份資料" />,
                  },
                  {
                    key: 'adr',
                    label: '整體 ADR 走勢',
                    children: (
                      <div style={{ width: '100%', height: 380 }}>
                        <ResponsiveContainer>
                          <LineChart data={data.trend}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="month" />
                            <YAxis />
                            <RTooltip formatter={(v: number) => fmtMoney(v)} />
                            <Legend />
                            <Line type="monotone" dataKey="adr" name="ADR"
                                  stroke={BRAND} strokeWidth={2} dot={false} />
                            <Line type="monotone" dataKey="revpar" name="RevPAR"
                                  stroke={ACCENT} strokeWidth={2} dot={false} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    ),
                  },
                ]}
              />

              <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 12 }}>
                資料來源：{data.source.provider}　|　資料表：<Text code>{data.source.table}</Text>
                　|　本次讀取 {fmtInt(data.row_count)} 列
                {data.yoy_range && <>　|　同期基準：{data.yoy_range.start} ～ {data.yoy_range.end}</>}
              </Text>
            </Card>
          </>
        )}
      </Spin>
    </div>
  )
}

export default OperaSegmentsPage
