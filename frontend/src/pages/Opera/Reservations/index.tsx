/**
 * 營運分析 — 訂房分析（/opera/reservations）
 *
 * ⚠️ **本頁母體與「住客與通路分析」不同，這是理解所有數字的前提：**
 *      本頁      = 所有訂房（含未來、含取消）      ← OHIP rsvasync API
 *      住客分析  = 已離店的住客                    ← 人工上傳 TXT Departure 報表
 *    同一維度（例如通路佔比）兩邊數字不同是**正確的**，不是誰對誰錯。
 *    頂端那則說明由後端 `source.population` 帶出，前端不寫死，**不要拿掉**。
 *
 * ⚠️ 前三個 TAB 是 TXT **永遠做不到**的（沒有訂房日期、沒有取消、沒有未來），
 *    後三個是「訂單口徑」的對照，不是要取代住客分析。
 *
 * ⚠️ 低填充率的維度（`company_name` 實測僅 15%）做成排行榜會嚴重偏頗，
 *    所以每個維度統計都顯示 coverage，低於 50% 會出現警語。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, Empty, Progress, Radio, Row, Space, Spin,
  Statistic, Table, Tabs, Tag, Tooltip, Typography,
} from 'antd'
import { ApiOutlined, ReloadOutlined, SyncOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip as RTooltip, XAxis, YAxis,
} from 'recharts'

import StandardRangePicker from '@/components/StandardRangePicker'
import {
  backfillRsvChunk, fetchBlocks, fetchBookingWindow, fetchCancellations,
  fetchOnTheBooks, fetchRsvDimension, fetchRsvLos, fetchRsvSyncStatus,
} from '@/api/operaReservation'
import type {
  BlockResult, BookingWindowResult, CancellationResult, Coverage,
  DimensionResult, LosResult, OnTheBooksResult, RsvDimension, RsvSyncStatus,
} from '@/api/operaReservation'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct,
} from '@/pages/Opera/components/formatters'

const { Title, Text } = Typography

const DIM_LABELS: Record<RsvDimension, string> = {
  market_code: '市場區隔', rate_code: 'Rate Code', source_code: '來源',
  channel: '通路', room_type: '房型', travel_agent_name: '旅行社',
  company_name: '公司', group_name: '團體', nationality: '國別',
}

/** ⚠️ 填充率必須跟數字一起出現，不是可選的裝飾 */
const CoverageTag: React.FC<{ coverage?: Coverage }> = ({ coverage }) => {
  if (!coverage || coverage.ratio === null) return null
  const pct = fmtPct(coverage.ratio)
  return (
    <Tooltip title={`這個維度有 ${coverage.filled} / ${coverage.total} 筆有值。${
      coverage.is_low ? '不到一半，排行結果會偏頗，不要當成全貌。' : ''}`}>
      <Tag color={coverage.is_low ? 'red' : 'default'}>
        資料涵蓋 {pct}
      </Tag>
    </Tooltip>
  )
}

const OperaReservationsPage: React.FC = () => {
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [anchor, setAnchor] = useState('')
  const [dimension, setDimension] = useState<RsvDimension>('market_code')
  const [otbDim, setOtbDim] = useState<RsvDimension>('market_code')
  const [sync, setSync] = useState<RsvSyncStatus | null>(null)
  const [bw, setBw] = useState<BookingWindowResult | null>(null)
  const [cx, setCx] = useState<CancellationResult | null>(null)
  const [otb, setOtb] = useState<OnTheBooksResult | null>(null)
  const [dim, setDim] = useState<DimensionResult | null>(null)
  const [los, setLos] = useState<LosResult | null>(null)
  const [blk, setBlk] = useState<BlockResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [backfilling, setBackfilling] = useState<'reservation' | 'block' | null>(null)
  const [error, setError] = useState('')

  const loadSync = useCallback(async () => {
    try {
      const s = await fetchRsvSyncStatus()
      setSync(s)
      // ⚠️ 本模組含未來資料，過去導向的分析要用 last_past 當 anchor（CLAUDE.md §8.2）
      if (s.data_range.last_past) setAnchor(s.data_range.last_past)
      return s
    } catch { return null }
  }, [])

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const s = sync ?? (await loadSync())
      const end = range ? range[1].format('YYYY-MM-DD') : (s?.data_range.last_past || '')
      const start = range ? range[0].format('YYYY-MM-DD') : (s?.data_range.start || '')
      if (!start || !end) { setLoading(false); return }
      const [a, b, c, d, e, f] = await Promise.all([
        fetchBookingWindow({ start, end }),
        fetchCancellations({ start, end }),
        fetchOnTheBooks({ days_ahead: 90, dimension: otbDim }),
        fetchRsvDimension({ start, end, dimension }),
        fetchRsvLos({ start, end }),
        fetchBlocks({ start, end }),
      ])
      setBw(a); setCx(b); setOtb(c); setDim(d); setLos(e); setBlk(f)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '載入失敗')
    } finally { setLoading(false) }
  }, [range, dimension, otbDim, sync, loadSync])

  useEffect(() => { loadSync() }, [loadSync])
  useEffect(() => { load() }, [range, dimension, otbDim])   // eslint-disable-line

  const runBackfill = useCallback(async (ds: 'reservation' | 'block') => {
    setBackfilling(ds)
    try {
      const r = await backfillRsvChunk(ds)
      setSync((p) => (p ? { ...p, [ds]: r.progress } as RsvSyncStatus : p))
      if (r.done) await load()
    } catch (e: any) {
      setError(e?.response?.data?.detail || '回補失敗')
    } finally { setBackfilling(null) }
  }, [load])

  const population = bw?.source?.population || blk?.source?.population || ''

  const dimColumns: ColumnsType<any> = useMemo(() => [
    { title: DIM_LABELS[dimension], dataIndex: dimension, width: 160, fixed: 'left',
      render: (v: string) => <Text strong>{v || EMPTY}</Text> },
    { title: '房晚', dataIndex: 'room_nights', width: 90, align: 'right',
      render: fmtInt, sorter: (a, b) => a.room_nights - b.room_nights },
    { title: '訂房數', dataIndex: 'reservations', width: 90, align: 'right', render: fmtInt },
    { title: '房租營收', dataIndex: 'room_revenue', width: 130, align: 'right',
      render: (v: number) => <Text strong>{fmtMoney(v)}</Text>,
      sorter: (a, b) => (a.room_revenue || 0) - (b.room_revenue || 0),
      defaultSortOrder: 'descend' },
    { title: '佔比', dataIndex: 'share', width: 90, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : fmtPct(v)) },
    { title: 'ADR', dataIndex: 'adr', width: 110, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY :
        <Text style={{ color: BRAND }}>{fmtMoney(v)}</Text>) },
    { title: <Tooltip title="被取消的房晚，不計入上方營收">取消房晚</Tooltip>,
      dataIndex: 'cancelled_nights', width: 100, align: 'right',
      render: (v: number) => (v ? <Text style={{ color: RED }}>{fmtInt(v)}</Text> : EMPTY) },
  ], [dimension])

  const blockColumns: ColumnsType<any> = useMemo(() => {
    const cols: ColumnsType<any> = [
      { title: '團體', dataIndex: 'block_name', width: 200, fixed: 'left',
        render: (v: string, r: any) => (
          <Space direction="vertical" size={0}>
            <Text strong>{v || EMPTY}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>{r.block_code}</Text>
          </Space>) },
      { title: '期間', width: 190,
        render: (_: any, r: any) => `${r.start_date} ～ ${r.end_date}` },
      { title: '狀態', dataIndex: 'status', width: 80,
        render: (v: string, r: any) => (r.cancellation_date
          ? <Tag color="red">已取消</Tag>
          : <Tag color={v === 'ACT' ? 'green' : 'default'}>{v || EMPTY}</Tag>) },
      { title: '原始配房', dataIndex: 'original_rooms', width: 90, align: 'right', render: fmtInt },
      { title: '目前配房', dataIndex: 'current_rooms', width: 90, align: 'right', render: fmtInt },
      { title: <Tooltip title="OPERA 直接提供的實際成交房數，不是推算的">成交</Tooltip>,
        dataIndex: 'pickup_rooms', width: 90, align: 'right',
        render: (v: number) => <Text strong>{fmtInt(v)}</Text> },
      { title: 'pickup 率', dataIndex: 'pickup_rate', width: 100, align: 'right',
        render: (v: number | null) => (v === null ? EMPTY :
          <Text style={{ color: v >= 0.8 ? GREEN : v >= 0.5 ? ORANGE : RED }}>{fmtPct(v)}</Text>),
        sorter: (a, b) => (a.pickup_rate || 0) - (b.pickup_rate || 0) },
      { title: <Tooltip title="目前配房 − 成交。cut-off 時會釋出">未售</Tooltip>,
        dataIndex: 'unsold_rooms', width: 80, align: 'right',
        render: (v: number) => (v ? <Text style={{ color: ORANGE }}>{fmtInt(v)}</Text> : EMPTY) },
      { title: '房租營收', dataIndex: 'room_revenue', width: 120, align: 'right', render: fmtMoney },
      { title: '公司', dataIndex: 'company_name', width: 170, render: (v: string) => v || EMPTY },
    ]
    // ⚠️ 整批 cutOffDays 都是 0 → 這間飯店沒在用 cut-off，顯示一整排 0 只會誤導
    if (blk?.cutoff_in_use) {
      cols.splice(3, 0, { title: 'Cut-off(天)', dataIndex: 'cut_off_days',
        width: 100, align: 'right', render: (v: number | null) => (v ?? EMPTY) })
    }
    return cols
  }, [blk])

  const prog = sync
  const rsvPending = prog?.reservation?.pending_chunks ?? 0
  const blkPending = prog?.block?.pending_chunks ?? 0

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0, color: BRAND }}>訂房分析</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          訂房前置期、取消、在手訂房與團體 pickup —— 這些是上傳的 TXT 報表看不到的。
        </Text>
      </Space>

      {/* ⚠️ 母體說明：本頁最重要的一句話，由後端帶出，不要拿掉 */}
      {population && (
        <Alert
          type="warning" showIcon icon={<ApiOutlined />} style={{ marginBottom: 16 }}
          message="這一頁算的是「訂單」，不是「住過的人」"
          description={
            <span dangerouslySetInnerHTML={{
              __html: population.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'),
            }} />
          }
        />
      )}

      {(rsvPending > 0 || blkPending > 0) && (
        <Alert
          type="info" showIcon style={{ marginBottom: 16 }}
          message="歷史資料回補中"
          description={
            <Space direction="vertical" style={{ width: '100%' }} size={10}>
              {(['reservation', 'block'] as const).map((ds) => {
                const p = prog?.[ds]
                if (!p || p.pending_chunks === 0) return null
                return (
                  <Space key={ds} wrap size={12} style={{ width: '100%' }}>
                    <Text style={{ width: 60 }}>{ds === 'reservation' ? '訂房' : '團體'}</Text>
                    {/* ⚠️ 2026-08-13 改為天數口徑。舊版用段數，而「整段有沒有資料
                        就算補過」造成假性完成 —— 顯示 24/24 完成，實際 2025-08、
                        2025-11、2026-02 整月 0 筆。天數才看得出真實缺口。 */}
                    <Progress
                      percent={Math.round((p.covered_days / Math.max(p.total_days, 1)) * 100)}
                      size="small" strokeColor={BRAND} style={{ width: 220 }} />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      還缺 <b>{p.missing_days}</b> 天（共 {p.total_days} 天），
                      要補 {p.pending_chunks} 段、每段最多 {p.chunk_days} 天，
                      預估剩 {p.estimated_remaining_seconds} 秒
                    </Text>
                    <Button size="small" type="primary" icon={<SyncOutlined />}
                            loading={backfilling === ds}
                            onClick={() => runBackfill(ds)}>補下一段</Button>
                  </Space>
                )
              })}
              <Text type="secondary" style={{ fontSize: 12 }}>
                ⚠️ 刻意不做成「一次補完兩年」—— 那會讓請求逾時。中斷了可以接著按。
                想一次補完請用同步工具的「訂房歷史回補」（背景執行，不受逾時限制）。
              </Text>
            </Space>
          }
        />
      )}

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap size={16}>
          {/* ⚠️ anchor 用 last_past（已發生的最後一天），不是資料最後一天 ——
              本模組含未來資料，用 end 會讓「本月」選到還沒發生的日子 */}
          <StandardRangePicker value={range} anchor={anchor} onChange={setRange} />
          <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={load}>
            重新整理
          </Button>
          {sync?.data_range?.has_data && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              訂房 {fmtInt(sync.data_range.reservations)} 筆
              涵蓋 {sync.data_range.start} ～ {sync.data_range.end}
              （含未來；期間快捷以 {sync.data_range.last_past} 為基準）
            </Text>
          )}
        </Space>
      </Card>

      {error && <Alert type="error" showIcon message="載入失敗" description={error}
                       style={{ marginBottom: 16 }} />}

      <Spin spinning={loading}>
        <Card size="small">
          <Tabs
            size="small"
            items={[
              {
                key: 'bw',
                label: <span>訂房前置期 <Tag color={ACCENT}>TXT 沒有</Tag></span>,
                children: !bw?.stats?.count ? <Empty description="這個期間沒有資料" /> : (
                  <>
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                      <Col xs={12} md={5}><Statistic title="中位前置期"
                        value={bw.stats.median ?? 0} suffix="天" valueStyle={{ color: BRAND }} /></Col>
                      <Col xs={12} md={5}><Statistic title="平均"
                        value={bw.stats.mean ?? 0} precision={1} suffix="天" /></Col>
                      <Col xs={12} md={5}><Statistic title="四分位 P25 / P75"
                        value={`${bw.stats.p25 ?? '—'} / ${bw.stats.p75 ?? '—'}`} /></Col>
                      <Col xs={12} md={5}><Statistic title="最長"
                        value={bw.stats.max ?? 0} suffix="天" valueStyle={{ color: GREY }} /></Col>
                      <Col xs={12} md={4}><Statistic title="樣本" value={bw.stats.count} /></Col>
                    </Row>
                    <div style={{ width: '100%', height: 320 }}>
                      <ResponsiveContainer>
                        <BarChart data={bw.buckets}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="bucket" /><YAxis />
                          <RTooltip /><Legend />
                          <Bar dataKey="reservations" name="訂房數" fill={BRAND} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <Table size="small" rowKey="bucket" pagination={false}
                      dataSource={bw.buckets}
                      columns={[
                        { title: '前置期', dataIndex: 'bucket', width: 130 },
                        { title: '訂房數', dataIndex: 'reservations', width: 100, align: 'right', render: fmtInt },
                        { title: '佔比', dataIndex: 'share', width: 90, align: 'right',
                          render: (v: number | null) => (v === null ? EMPTY : fmtPct(v)) },
                        { title: '房晚', dataIndex: 'room_nights', width: 100, align: 'right', render: fmtInt },
                        { title: <Tooltip title="這一桶裡有多少比例最後被取消——「越早訂越容易取消嗎」看這欄">取消率</Tooltip>,
                          dataIndex: 'cancel_rate', width: 100, align: 'right',
                          render: (v: number | null) => (v === null ? EMPTY :
                            <Text style={{ color: v > 0.3 ? RED : GREY }}>{fmtPct(v)}</Text>) },
                      ]} />
                  </>
                ),
              },
              {
                key: 'cx',
                label: <span>取消分析 <Tag color={ACCENT}>TXT 沒有</Tag></span>,
                children: !cx ? <Empty /> : (
                  <>
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                      <Col xs={12} md={6}><Statistic title="取消率"
                        value={(cx.summary.cancel_rate ?? 0) * 100} precision={1} suffix="%"
                        valueStyle={{ color: RED }} /></Col>
                      <Col xs={12} md={6}><Statistic title="取消訂房"
                        value={cx.summary.cancelled} suffix={`/ ${cx.summary.reservations}`} /></Col>
                      <Col xs={12} md={6}><Statistic title="損失房晚"
                        value={cx.summary.lost_room_nights} valueStyle={{ color: ORANGE }} /></Col>
                      <Col xs={12} md={6}><Statistic title="取消提前期中位數"
                        value={cx.summary.median_notice_days ?? 0} suffix="天" /></Col>
                    </Row>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      取消率的分母是**所有訂房**（含取消）。取消提前期＝距離原訂到達日還有幾天才取消。
                    </Text>
                    <Table size="small" rowKey="reason_code" pagination={false}
                      style={{ marginTop: 12 }} dataSource={cx.reasons}
                      columns={[
                        { title: <Space>取消原因碼 <CoverageTag coverage={cx.coverage} /></Space>,
                          dataIndex: 'reason_code', width: 200 },
                        { title: '件數', dataIndex: 'count', width: 100, align: 'right', render: fmtInt },
                        { title: '佔比', dataIndex: 'share', width: 100, align: 'right',
                          render: (v: number | null) => (v === null ? EMPTY : fmtPct(v)) },
                      ]} />
                  </>
                ),
              },
              {
                key: 'otb',
                label: <span>在手訂房 <Tag color={ACCENT}>TXT 沒有</Tag></span>,
                children: !otb?.days?.length ? <Empty description="未來沒有已訂房晚" /> : (
                  <>
                    <Space wrap style={{ marginBottom: 12 }}>
                      <Radio.Group value={otbDim} size="small" buttonStyle="solid"
                                   onChange={(e) => setOtbDim(e.target.value)}>
                        {(['market_code', 'channel', 'room_type', 'rate_code'] as RsvDimension[])
                          .map((d) => <Radio.Button key={d} value={d}>{DIM_LABELS[d]}</Radio.Button>)}
                      </Radio.Group>
                      <CoverageTag coverage={otb.coverage} />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        未來 90 天已訂 {fmtInt(otb.summary.room_nights)} 房晚
                        （{fmtMoney(otb.summary.room_revenue)}）
                      </Text>
                    </Space>
                    <div style={{ width: '100%', height: 340 }}>
                      <ResponsiveContainer>
                        <LineChart data={otb.days}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="business_date" /><YAxis />
                          <RTooltip /><Legend />
                          <Line type="monotone" dataKey="room_nights" name="已訂房晚"
                                stroke={BRAND} strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </>
                ),
              },
              {
                key: 'dim',
                label: '維度統計',
                children: (
                  <>
                    <Space wrap style={{ marginBottom: 12 }}>
                      <Radio.Group value={dimension} size="small" buttonStyle="solid"
                                   onChange={(e) => setDimension(e.target.value)}>
                        {(Object.keys(DIM_LABELS) as RsvDimension[]).map((d) => (
                          <Radio.Button key={d} value={d}>{DIM_LABELS[d]}</Radio.Button>
                        ))}
                      </Radio.Group>
                      <CoverageTag coverage={dim?.coverage} />
                    </Space>
                    {dim?.coverage?.is_low && (
                      <Alert type="warning" showIcon style={{ marginBottom: 12 }}
                        message={`這個維度只有 ${fmtPct(dim.coverage.ratio || 0)} 的資料有值`}
                        description="排行結果會偏頗，請不要當成全貌。這是 OPERA 端的填寫狀況，不是系統問題。" />
                    )}
                    {dim?.rows?.length
                      ? <Table size="small" rowKey={(r) => String(r[dimension] || '')}
                          columns={dimColumns} dataSource={dim.rows}
                          pagination={false} scroll={{ x: 900 }} />
                      : <Empty description="這個期間沒有資料" />}
                  </>
                ),
              },
              {
                key: 'los',
                label: '住宿天數',
                children: los?.buckets?.length
                  ? <Table size="small" rowKey="bucket" pagination={false} dataSource={los.buckets}
                      columns={[
                        { title: '天數', dataIndex: 'bucket', width: 140 },
                        { title: '訂房數', dataIndex: 'reservations', width: 110, align: 'right', render: fmtInt },
                        { title: '佔比', dataIndex: 'share', width: 100, align: 'right',
                          render: (v: number | null) => (v === null ? EMPTY : fmtPct(v)) },
                        { title: '房晚', dataIndex: 'room_nights', width: 110, align: 'right', render: fmtInt },
                      ]} />
                  : <Empty />,
              },
              {
                key: 'blk',
                label: <span>團體 pickup <Tag color={ACCENT}>TXT 沒有</Tag></span>,
                children: !blk?.blocks?.length ? <Empty description="這個期間沒有團體" /> : (
                  <>
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                      <Col xs={12} md={5}><Statistic title="pickup 率"
                        value={(blk.summary.pickup_rate ?? 0) * 100} precision={1} suffix="%"
                        valueStyle={{ color: (blk.summary.pickup_rate ?? 0) >= 0.8 ? GREEN : ORANGE }} /></Col>
                      <Col xs={12} md={5}><Statistic title="目前配房"
                        value={blk.summary.current_rooms} /></Col>
                      <Col xs={12} md={5}><Statistic title="實際成交"
                        value={blk.summary.pickup_rooms} valueStyle={{ color: BRAND }} /></Col>
                      <Col xs={12} md={5}><Statistic title="未售（cut-off 會釋出）"
                        value={blk.summary.unsold_rooms} valueStyle={{ color: ORANGE }} /></Col>
                      <Col xs={12} md={4}><Statistic title="團體數"
                        value={blk.summary.block_count}
                        suffix={blk.summary.cancelled_blocks
                          ? `(${blk.summary.cancelled_blocks} 取消)` : ''} /></Col>
                    </Row>
                    {!blk.cutoff_in_use && (
                      <Alert type="info" showIcon style={{ marginBottom: 12 }}
                        message="這批團體的 cut-off 天數都是 0"
                        description="代表貴飯店目前沒有在使用 cut-off 機制，因此不顯示該欄位（顯示一整排 0 只會造成誤解）。pickup 率不受影響。" />
                    )}
                    <Table size="small" rowKey="block_id" columns={blockColumns}
                      dataSource={blk.blocks} pagination={{ pageSize: 20 }}
                      scroll={{ x: 1300 }} />
                  </>
                ),
              },
            ]}
          />
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 12 }}>
            資料來源：{bw?.source?.provider || blk?.source?.provider}
          </Text>
        </Card>
      </Spin>
    </div>
  )
}

export default OperaReservationsPage
