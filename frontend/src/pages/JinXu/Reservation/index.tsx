/**
 * 訂房與通路分析（/jinxu/reservation）— 規格書 §13.3
 * TAB：通路 / 房型 / 業務碼 / 月趨勢 / 取消分析 / 訂價vs實收 / 回訪 / 訂房明細
 *
 * ⚠️ 母體標示（§11.4）：每個 TAB 頂部固定顯示 population_note。取消佔 29.7%，
 *    使用者必須隨時看得到目前數字排除了什麼。
 * ⚠️ 取消分析／訂價vs實收／回訪 需 jinxu_cancel_view；無權限時該 TAB 不渲染。
 * ⚠️ J27：平均住宿晚數預設顯示 billable（Day Use 算 1 晚），可切換。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Card, Col, Empty, Radio, Row, Space, Statistic, Switch, Table, Tabs, Tag, Typography,
} from 'antd'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip as RcTooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import type { Dayjs } from 'dayjs'

import {
  fetchCancellation, fetchCancellationByChannel, fetchCancellationMonthly,
  fetchRateGap, fetchRepeatGuests, fetchResvByChannel, fetchResvByRateCode,
  fetchResvByRoomType, fetchResvList, fetchResvMonthly, fetchResvSummary,
  fetchStatusBreakdown,
} from '@/api/jinxu'
import type {
  CancellationGroupRow, CancellationMonthRow, CancellationSummary, NightsBasis,
  RateGapResult, RepeatGuestResult, Reservation, ResvGroupResult, ResvMonthRow,
  ResvSummary, RoomTypeRow, StatusRow,
} from '@/types/jinxu'
import FilterBar, { toIso } from '../components/FilterBar'
import ReservationDrawer from '../components/ReservationDrawer'
import SharePie from '../components/SharePie'
import {
  NIGHTS_BASIS_DEFAULT, NIGHTS_BASIS_OPTIONS, STATUS_COLORS,
  dash, fmtInt, fmtMoney, fmtPct, moneyStyle,
} from '../components/constants'

const { Text } = Typography

/** 母體提示條 —— 每個 TAB 頂部都要有 */
function PopNote({ text, extra }: { text?: string; extra?: string }) {
  if (!text) return null
  return (
    <Alert type="info" showIcon style={{ marginBottom: 12 }}
           message={<Space size="small" wrap><Tag color="blue">{text}</Tag>
             {extra && <Text type="secondary">{extra}</Text>}</Space>} />
  )
}

export default function JinxuReservation() {
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null)
  const [nightsBasis, setNightsBasis] = useState<NightsBasis>(NIGHTS_BASIS_DEFAULT)
  const [canCancelView, setCanCancelView] = useState(true)

  const [sum, setSum] = useState<ResvSummary | null>(null)
  const [chan, setChan] = useState<ResvGroupResult | null>(null)
  const [rooms, setRooms] = useState<{ items: RoomTypeRow[]; population_note: string; note: string } | null>(null)
  const [rate, setRate] = useState<ResvGroupResult | null>(null)
  const [monthly, setMonthly] = useState<{ items: ResvMonthRow[]; population_note: string } | null>(null)
  const [statuses, setStatuses] = useState<StatusRow[]>([])
  const [cancel, setCancel] = useState<CancellationSummary | null>(null)
  const [cancelChan, setCancelChan] = useState<CancellationGroupRow[]>([])
  const [cancelMonth, setCancelMonth] = useState<CancellationMonthRow[]>([])
  const [gap, setGap] = useState<RateGapResult | null>(null)
  const [repeat, setRepeat] = useState<RepeatGuestResult | null>(null)

  const [incCancel, setIncCancel] = useState(false)
  const [list, setList] = useState<Reservation[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [drawerId, setDrawerId] = useState<number | null>(null)

  const f = { start_date: toIso(range?.[0]), end_date: toIso(range?.[1]) }

  const load = useCallback(async () => {
    setSum(await fetchResvSummary(f))
    setChan(await fetchResvByChannel(f))
    setRooms(await fetchResvByRoomType(f))
    setRate(await fetchResvByRateCode(f))
    setMonthly(await fetchResvMonthly(f))
    setStatuses((await fetchStatusBreakdown(f.start_date, f.end_date)).items)
    try {
      setCancel(await fetchCancellation(f))
      setCancelChan((await fetchCancellationByChannel(f)).items)
      setCancelMonth((await fetchCancellationMonthly(f)).items)
      setGap(await fetchRateGap(f))
      setRepeat(await fetchRepeatGuests(f))
      setCanCancelView(true)
    } catch {
      setCanCancelView(false)   // 無 jinxu_cancel_view 權限 → 相關 TAB 不渲染
    }
  }, [range])

  const loadList = useCallback(async () => {
    const r = await fetchResvList({ ...f, include_cancelled: incCancel }, page, 50)
    setList(r.items); setTotal(r.total)
  }, [range, incCancel, page])

  useEffect(() => { void load() }, [load])
  useEffect(() => { void loadList() }, [loadList])

  const nightsKey = nightsBasis === 'billable' ? 'avg_billable_nights' : 'avg_nights'

  const groupCols = [
    { title: '名稱', dataIndex: 'label', render: dash },
    { title: '訂房數', dataIndex: 'reservation_count', align: 'right' as const, width: 90, render: fmtInt },
    { title: '房晚', dataIndex: 'room_nights', align: 'right' as const, width: 90, render: fmtInt },
    { title: '房晚佔比', dataIndex: 'room_nights_share_pct', align: 'right' as const, width: 95,
      render: (v: number) => fmtPct(v, 2) },
    { title: '報價總額', dataIndex: 'quoted_amount', align: 'right' as const, width: 140,
      render: (v: number) => fmtMoney(v) },
    { title: 'ADR', dataIndex: 'adr', align: 'right' as const, width: 110,
      render: (v: number) => <Text strong>{fmtMoney(v)}</Text> },
    { title: '平均晚數', dataIndex: nightsKey, align: 'right' as const, width: 100,
      render: (v: number) => v?.toFixed(2) ?? '—' },
  ]

  const items = [
    {
      key: 'channel', label: '通路',
      children: (
        <Card size="small">
          <PopNote text={chan?.population_note} extra={chan?.note} />
          {/* 佔比一律以「全部通路」為分母（含未進前 8 名者，合併為「其他」），
              否則 recharts 會用前 N 名的和當分母，把佔比放大。 */}
          <SharePie
            data={chan?.items ?? []}
            nameOf={(r) => r.label}
            valueOf={(r) => r.room_nights}
            keyOf={(r) => r.key || r.label}
            unit=" 房晚"
            height={320}
          />
          <Table rowKey="key" size="small" pagination={false}
                 dataSource={chan?.items ?? []} columns={groupCols} scroll={{ x: 900 }} />
        </Card>
      ),
    },
    {
      key: 'roomtype', label: '房型',
      children: (
        <Card size="small">
          <PopNote text={rooms?.population_note} extra={rooms?.note} />
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={rooms?.items ?? []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="room_type_code" />
              <YAxis />
              <RcTooltip formatter={(v: number) => fmtInt(v)} />
              <Bar dataKey="room_nights" name="房晚" fill="#1B3A5C" />
            </BarChart>
          </ResponsiveContainer>
          <Table rowKey="room_type_code" size="small" pagination={false} dataSource={rooms?.items ?? []}
            columns={[
              { title: '房型代碼', dataIndex: 'room_type_code', width: 100,
                render: (v: string) => <Tag>{v}</Tag> },
              { title: '訂房數', dataIndex: 'reservation_count', align: 'right', width: 100, render: fmtInt },
              { title: '住宿段數', dataIndex: 'segment_count', align: 'right', width: 100, render: fmtInt },
              { title: '房晚', dataIndex: 'room_nights', align: 'right', width: 100, render: fmtInt },
              { title: '房晚佔比', dataIndex: 'room_nights_share_pct', align: 'right', width: 100,
                render: (v: number) => fmtPct(v, 2) },
              { title: '報價總額', dataIndex: 'quoted_amount', align: 'right', width: 150,
                render: (v: number) => fmtMoney(v) },
              { title: 'ADR', dataIndex: 'adr', align: 'right', width: 110,
                render: (v: number) => <Text strong>{fmtMoney(v)}</Text> },
            ]} />
        </Card>
      ),
    },
    {
      key: 'ratecode', label: '業務碼',
      children: (
        <Card size="small">
          <PopNote text={rate?.population_note} />
          <Table rowKey="key" size="small" pagination={false}
                 dataSource={rate?.items ?? []} columns={groupCols} scroll={{ x: 900 }} />
        </Card>
      ),
    },
    {
      key: 'monthly', label: '月趨勢',
      children: (
        <Card size="small">
          <PopNote text={monthly?.population_note} />
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={monthly?.items ?? []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis yAxisId="l" />
              <YAxis yAxisId="r" orientation="right" tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
              <RcTooltip />
              <Legend />
              <Line yAxisId="l" type="monotone" dataKey="room_nights" name="房晚" stroke="#1B3A5C" />
              <Line yAxisId="r" type="monotone" dataKey="adr" name="ADR" stroke="#4BA8E8" />
            </LineChart>
          </ResponsiveContainer>
          <Table rowKey="month" size="small" pagination={false} dataSource={monthly?.items ?? []}
            columns={[{ title: '月份', dataIndex: 'month', width: 110 }, ...groupCols.slice(1)]} scroll={{ x: 900 }} />
        </Card>
      ),
    },
    {
      key: 'status', label: '狀態分布',
      children: (
        <Card size="small">
          <Table rowKey="status_code" size="small" pagination={false} dataSource={statuses}
            columns={[
              { title: '狀態碼', dataIndex: 'status_code', width: 110,
                render: (v: string, r: StatusRow) => (
                  <Tag color={STATUS_COLORS[v] || 'default'}>{r.label}</Tag>) },
              { title: '筆數', dataIndex: 'count', align: 'right', width: 100, render: fmtInt },
              { title: '佔比', dataIndex: 'share_pct', align: 'right', width: 90,
                render: (v: number) => fmtPct(v, 2) },
              { title: '房晚', dataIndex: 'room_nights', align: 'right', width: 100, render: fmtInt },
              { title: '統計處理', dataIndex: 'excluded_from_stats', width: 130,
                render: (v: boolean) => (v ? <Tag color="default">不計入統計</Tag> : '—') },
            ]} />
        </Card>
      ),
    },
  ]

  if (canCancelView) {
    items.push(
      {
        key: 'cancellation', label: '取消分析',
        children: (
          <Card size="small">
            <PopNote text={cancel?.population_note} />
            <Alert type="warning" showIcon style={{ marginBottom: 16 }} message={cancel?.note} />
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}><Card size="small">
                <Statistic title="取消率（筆數）" value={cancel?.cancel_rate_by_count ?? 0}
                           precision={2} suffix="%" valueStyle={{ color: '#cf1322' }} /></Card></Col>
              <Col span={6}><Card size="small">
                <Statistic title="取消率（房晚）" value={cancel?.cancel_rate_by_room_nights ?? 0}
                           precision={2} suffix="%" /></Card></Col>
              <Col span={6}><Card size="small">
                <Statistic title="取消損失報價" value={cancel?.cancelled_quoted_amount ?? 0}
                           precision={0} prefix="$" /></Card></Col>
              <Col span={6}><Card size="small">
                <Statistic title="未到（No Show）" value={cancel?.no_show_count ?? 0}
                           suffix={`（${fmtPct(cancel?.no_show_rate ?? 0, 2)}）`} /></Card></Col>
            </Row>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={cancelMonth}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" /><YAxis tickFormatter={(v) => `${v}%`} />
                <RcTooltip formatter={(v: number) => fmtPct(v, 2)} /><Legend />
                <Line type="monotone" dataKey="cancel_rate_by_count" name="取消率(筆數)" stroke="#cf1322" />
                <Line type="monotone" dataKey="cancel_rate_by_room_nights" name="取消率(房晚)" stroke="#e67e22" />
              </LineChart>
            </ResponsiveContainer>
            <Text strong style={{ display: 'block', margin: '16px 0 8px' }}>依通路取消率</Text>
            <Table rowKey="key" size="small" pagination={false} dataSource={cancelChan} scroll={{ x: 900 }}
              columns={[
                { title: '通路', dataIndex: 'label', render: dash },
                { title: '總訂房', dataIndex: 'total_count', align: 'right', width: 90, render: fmtInt },
                { title: '取消數', dataIndex: 'cancelled_count', align: 'right', width: 90, render: fmtInt },
                { title: '取消率(筆數)', dataIndex: 'cancel_rate_by_count', align: 'right', width: 120,
                  render: (v: number) => <Text style={{ color: v > 30 ? '#cf1322' : undefined }}>{fmtPct(v, 1)}</Text> },
                { title: '取消率(房晚)', dataIndex: 'cancel_rate_by_room_nights', align: 'right', width: 120,
                  render: (v: number) => fmtPct(v, 1) },
                { title: '損失報價', dataIndex: 'cancelled_quoted_amount', align: 'right', width: 150,
                  render: (v: number) => fmtMoney(v) },
              ]} />
          </Card>
        ),
      },
      {
        key: 'rategap', label: '訂價 vs 實收',
        children: (
          <Card size="small">
            {!gap?.available ? (
              <Empty description={gap?.reason ?? '需同時匯入兩份報表'} />
            ) : (
              <>
                <Alert type="info" showIcon style={{ marginBottom: 16 }}
                  message={<Space direction="vertical" size={0}>
                    <Text>{gap.note}</Text>
                    <Text type="secondary">{gap.subject_scope}｜{gap.gap_definition}</Text>
                  </Space>} />
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={6}><Card size="small">
                    <Statistic title="可比對筆數" value={gap.matched_count} /></Card></Col>
                  <Col span={6}><Card size="small">
                    <Statistic title="逐筆完全相符" value={gap.exact_match_pct} precision={2} suffix="%" />
                    <Text type="secondary">{fmtInt(gap.exact_match_count)} 筆</Text></Card></Col>
                  <Col span={6}><Card size="small">
                    <Statistic title="整體差異" value={gap.gap_pct} precision={2} suffix="%"
                               valueStyle={{ color: gap.gap_pct < 0 ? '#cf1322' : '#3f8600' }} /></Card></Col>
                  <Col span={6}><Card size="small">
                    <Statistic title="差異金額" value={gap.gap_total} precision={0} prefix="$"
                               valueStyle={moneyStyle(gap.gap_total)} /></Card></Col>
                </Row>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart margin={{ left: 24, right: 24, top: 8, bottom: 24 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" dataKey="quoted_amount" name="訂價"
                           tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                    <YAxis type="number" dataKey="actual_amount" name="實收"
                           tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                    <ZAxis range={[30, 30]} />
                    <RcTooltip formatter={(v: number) => fmtMoney(v)} />
                    <Scatter data={gap.flagged} fill="#e67e22" />
                  </ScatterChart>
                </ResponsiveContainer>
                <Text strong style={{ display: 'block', margin: '8px 0' }}>
                  差異超過門檻者（{fmtInt(gap.flagged_count)} 筆，僅列前 {gap.flagged.length} 筆）
                </Text>
                <Table rowKey="booking_no" size="small" dataSource={gap.flagged} scroll={{ x: 1000 }}
                  pagination={{ pageSize: 20 }}
                  columns={[
                    { title: '訂房號碼', dataIndex: 'booking_no', width: 100 },
                    { title: '到達日', dataIndex: 'arrival_date', width: 105 },
                    { title: '通路', dataIndex: 'company_name', ellipsis: true },
                    { title: '房型', dataIndex: 'room_type_codes', width: 110, render: dash },
                    { title: '房晚', dataIndex: 'room_nights', align: 'right', width: 70 },
                    { title: '訂價', dataIndex: 'quoted_amount', align: 'right', width: 120,
                      render: (v: number) => fmtMoney(v) },
                    { title: '實收', dataIndex: 'actual_amount', align: 'right', width: 120,
                      render: (v: number) => fmtMoney(v) },
                    { title: '差異', dataIndex: 'gap', align: 'right', width: 120,
                      render: (v: number) => <Text strong style={moneyStyle(v)}>{fmtMoney(v)}</Text> },
                  ]} />
              </>
            )}
          </Card>
        ),
      },
      {
        key: 'repeat', label: '回訪住客',
        children: (
          <Card size="small">
            <PopNote text={repeat?.population_note} />
            <Alert type="warning" showIcon style={{ marginBottom: 16 }} message={repeat?.note} />
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}><Card size="small">
                <Statistic title="相異住客" value={repeat?.unique_guests ?? 0} /></Card></Col>
              <Col span={6}><Card size="small">
                <Statistic title="回訪住客" value={repeat?.repeat_guests ?? 0} /></Card></Col>
              <Col span={6}><Card size="small">
                <Statistic title="回訪客佔比" value={repeat?.repeat_guest_rate ?? 0}
                           precision={2} suffix="%" /></Card></Col>
              <Col span={6}><Card size="small">
                <Statistic title="回訪住宿佔比" value={repeat?.repeat_stay_rate ?? 0}
                           precision={2} suffix="%" /></Card></Col>
            </Row>
            <Table rowKey={(r) => r.guest_name_masked + r.first_arrival} size="small"
              dataSource={repeat?.items ?? []} pagination={{ pageSize: 20 }} scroll={{ x: 900 }}
              columns={[
                { title: '住客（已遮罩）', dataIndex: 'guest_name_masked', render: dash },
                { title: '入住次數', dataIndex: 'visit_count', align: 'right', width: 100,
                  render: (v: number) => <Text strong>{v}</Text> },
                { title: '房晚', dataIndex: 'room_nights', align: 'right', width: 90, render: fmtInt },
                { title: '報價總額', dataIndex: 'quoted_amount', align: 'right', width: 140,
                  render: (v: number) => fmtMoney(v) },
                { title: '首次到達', dataIndex: 'first_arrival', width: 110 },
                { title: '最近到達', dataIndex: 'last_arrival', width: 110 },
                { title: '使用通路數', dataIndex: 'channel_count', align: 'right', width: 110 },
              ]} />
          </Card>
        ),
      },
    )
  }

  items.push({
    key: 'list', label: '訂房明細',
    children: (
      <Card size="small">
        <Space style={{ marginBottom: 12 }} wrap>
          <Text>含取消訂房</Text>
          <Switch checked={incCancel} onChange={(v) => { setIncCancel(v); setPage(1) }} />
          <Tag color={incCancel ? 'orange' : 'blue'}>
            {incCancel ? '母體：含取消訂房，已排除虛擬訂房' : '母體：已排除取消與虛擬訂房'}
          </Tag>
        </Space>
        <Table<Reservation> rowKey="id" size="small" dataSource={list} scroll={{ x: 1300 }}
          onRow={(r) => ({ onClick: () => setDrawerId(r.id), style: { cursor: 'pointer' } })}
          columns={[
            { title: '狀態', dataIndex: 'status_code', width: 100,
              render: (v: string, r: Reservation) => (
                <Tag color={STATUS_COLORS[v] || 'default'}>{r.status_label}</Tag>) },
            { title: '到達日', dataIndex: 'arrival_date', width: 105 },
            { title: '退房日', dataIndex: 'departure_date', width: 105 },
            { title: '晚數', dataIndex: nightsBasis === 'billable' ? 'billable_nights' : 'nights',
              align: 'right', width: 75,
              render: (v: number, r: Reservation) => (
                <>{v}{r.is_day_use === 1 && <Tag color="warning" style={{ marginLeft: 4 }}>DU</Tag>}</>) },
            { title: '訂房號碼', dataIndex: 'booking_no', width: 100 },
            { title: '住客（已遮罩）', dataIndex: 'guest_name_masked', width: 200, ellipsis: true, render: dash },
            { title: '通路', dataIndex: 'company_name', ellipsis: true, render: dash },
            { title: '業務碼', dataIndex: 'rate_code', width: 150, ellipsis: true, render: dash },
            { title: '類別', dataIndex: 'resv_type', width: 70,
              render: (v: string) => <Tag color={v === 'GIT' ? 'purple' : 'blue'}>{dash(v)}</Tag> },
            { title: '段數', dataIndex: 'stay_segment_count', align: 'right', width: 70 },
            { title: '房晚', dataIndex: 'total_room_nights', align: 'right', width: 75 },
            { title: '報價總額', dataIndex: 'total_quoted_amount', align: 'right', width: 130,
              render: (v: number) => <Text strong>{fmtMoney(v)}</Text> },
          ]}
          pagination={{ current: page, pageSize: 50, total, showSizeChanger: false,
                        onChange: setPage, showTotal: (t) => `共 ${fmtInt(t)} 筆` }} />
      </Card>
    ),
  })

  return (
    <div>
      <FilterBar range={range} onChange={setRange} onReload={() => { void load(); void loadList() }}
        extra={
          <Space>
            <Text type="secondary">住宿晚數口徑</Text>
            <Radio.Group value={nightsBasis} size="small" optionType="button"
                         onChange={(e) => setNightsBasis(e.target.value)}>
              {NIGHTS_BASIS_OPTIONS.map((o) => (
                <Radio.Button key={o.value} value={o.value}>{o.label}</Radio.Button>))}
            </Radio.Group>
          </Space>
        } />
      {sum && (
        <Row gutter={16} style={{ marginBottom: 8 }}>
          <Col span={6}><Card size="small"><Statistic title="訂房筆數" value={sum.reservation_count} /></Card></Col>
          <Col span={6}><Card size="small"><Statistic title="房晚數" value={sum.room_nights} /></Card></Col>
          <Col span={6}><Card size="small">
            <Statistic title="平均房價 ADR" value={sum.adr} precision={0} prefix="$" /></Card></Col>
          <Col span={6}><Card size="small">
            <Statistic title="平均住宿晚數"
                       value={nightsBasis === 'billable' ? sum.avg_billable_nights : sum.avg_nights}
                       precision={2} suffix="晚" /></Card></Col>
        </Row>
      )}
      {sum && <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 16 }}>
        {sum.population_note}｜{sum.nights_note}
      </Text>}
      <Tabs items={items} />
      <ReservationDrawer resvId={drawerId} open={drawerId !== null} onClose={() => setDrawerId(null)} />
    </div>
  )
}
