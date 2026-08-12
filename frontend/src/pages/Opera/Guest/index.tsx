/**
 * 住客與通路分析（/opera/guest）
 * 規格書：docs/SPEC_opera_analytics.md §11.4、§11.10、圖表 C9～C13
 *
 * TAB：住宿明細 / 通路 / 房型 / Rate Code / 公司 / 回訪與長住
 * 資料來源一律為 Departure All（決策 D7）。
 * 維度統計支援雙口徑切換（決策 D5）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col,  Empty, Input, Modal, Radio, Row, Select,
  Space, Spin, Switch, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  InfoCircleOutlined, QuestionCircleOutlined, ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LabelList,
  Pie, PieChart, ReferenceLine, ResponsiveContainer, Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'

import {
  fetchCheckoutTime, fetchDimensionStats, fetchGuestFilterOptions, fetchGuestMix,
  fetchLongStay, fetchLosBuckets, fetchRepeatGuests, fetchRoomUsage, fetchStayDetail,
  fetchStays, fetchStayWeekday,
} from '@/api/opera'
import type { DimensionParams, OperaDimension } from '@/api/opera'
import type {
  CheckoutTimeResult, DimensionResult, GuestMixResult, LongStayResult, LosBucketResult,
  OperaBasis, RepeatGuestResult, RoomUsageResult, StayRow, StayWeekdayResult,
} from '@/types/opera'
import BackToTop from '../components/BackToTop'
import StandardRangePicker from '@/components/StandardRangePicker'
import StayDetailDrawer from '../components/StayDetailDrawer'
import {
  ACCENT, BRAND, CHART_COLORS, EMPTY, GREEN, ORANGE, RED,
  fmtInt, fmtPct,
} from '../components/formatters'

const { Title, Text } = Typography

const SOURCE_NOTE = '資料來源：Departure All'
/** 標題旁「?」的說明內容（原本是頁面頂端的固定 Alert，內容未變） */
const SOURCE_HEADLINE = `${SOURCE_NOTE}　｜　本頁不含營收金額`
const SOURCE_DETAIL = 'Departure 報表的 BALANCE 欄位在實測資料中全為 0，無法推估單筆訂房營收。營收、ADR、住房率請看「營收分析」（來源：History and Forecast）。'
const CHART_HEIGHT = 300

const BASIS_TIP = (
  <div style={{ maxWidth: 320 }}>
    <b>以房數計</b>：只計 <code>NO_OF_ROOMS = 1</code> 的列，與 OPERA footer 的房數口徑一致。<br />
    <b>以訂單計</b>：計入全部列（含 <code>NO_OF_ROOMS = 0</code>）。<br />
    <br />
    實測有 36.6% 的列 <code>NO_OF_ROOMS = 0</code>，其語意（share／次要訂房？）尚待 OPERA 顧問確認，
    因此兩種口徑並存，避免預設其中一種造成誤讀。
  </div>
)

const OperaGuestPage: React.FC = () => {
  const [tab, setTab] = useState('stays')
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  // 快捷區間的錨點 = Departure 的資料最後一天（本頁資料來源是 Departure）
  const [dataEnd, setDataEnd] = useState<string>('')
  const [basis, setBasis] = useState<OperaBasis>('room')
  const [helpOpen, setHelpOpen] = useState(false)
  /** 目前開著的是哪一個 TAB 的說明；null = 沒開 */
  const [tabHelpKey, setTabHelpKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // 住宿明細
  const [stays, setStays] = useState<StayRow[]>([])
  const [stayTotal, setStayTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [search, setSearch] = useState('')
  const [channelFilter, setChannelFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [options, setOptions] = useState<{ channel: string[]; room_category: string[]; rate_code: string[] }>({
    channel: [], room_category: [], rate_code: [],
  })

  // 維度
  const [dimData, setDimData] = useState<Record<string, DimensionResult | null>>({})
  const [repeat, setRepeat] = useState<RepeatGuestResult | null>(null)
  const [longStay, setLongStay] = useState<LongStayResult | null>(null)
  const [losBuckets, setLosBuckets] = useState<LosBucketResult | null>(null)
  const [excludePerson, setExcludePerson] = useState(true)
  /** 長住拆解：依 Rate Code／通路／房型 */
  const [longStaySplit, setLongStaySplit] = useState<Record<string, DimensionResult | null>>({})
  /** 作業排程 TAB：退房時間分布 + 入退房星期 */
  const [checkoutTime, setCheckoutTime] = useState<CheckoutTimeResult | null>(null)
  const [stayWeekday, setStayWeekday] = useState<StayWeekdayResult | null>(null)
  /** 房號使用 TAB */
  const [roomUsage, setRoomUsage] = useState<RoomUsageResult | null>(null)
  /** 客群結構（併在房型 TAB 內） */
  const [guestMix, setGuestMix] = useState<GuestMixResult | null>(null)

  const [drawerStay, setDrawerStay] = useState<StayRow | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const rangeParams = useMemo(
    () => (range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
    [range],
  )

  // ── 初始化日期範圍與篩選選項 ────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const opt = await fetchGuestFilterOptions()
        setOptions({ channel: opt.channel, room_category: opt.room_category, rate_code: opt.rate_code })
        setDataEnd(opt.end)
        if (!range) setRange([dayjs(opt.start), dayjs(opt.end)])
      } catch {
        /* 靜默：主畫面仍可運作 */
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadStays = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchStays({
        ...rangeParams, basis, page, page_size: pageSize,
        search, channel: channelFilter, room_category: categoryFilter,
      })
      setStays(res.items)
      setStayTotal(res.total)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入住宿明細失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis, page, pageSize, search, channelFilter, categoryFilter])

  const loadDimension = useCallback(async (dim: OperaDimension, limit = 0) => {
    setLoading(true)
    try {
      const extra: DimensionParams = { ...rangeParams, basis, limit }
      if (dim === 'group') extra.exclude_person = excludePerson
      const res = await fetchDimensionStats(dim, extra)
      setDimData((prev) => ({ ...prev, [dim]: res }))
      // 房型 TAB 同時載入 LOS 分桶與客群結構（都是房型相關的判讀依據）
      if (dim === 'room_category') {
        const [lb, gm] = await Promise.all([
          fetchLosBuckets({ ...rangeParams, basis }),
          fetchGuestMix({ ...rangeParams, basis }),
        ])
        setLosBuckets(lb)
        setGuestMix(gm)
      }
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入統計失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis, excludePerson])

  const loadGuestTab = useCallback(async () => {
    setLoading(true)
    try {
      const [rp, ls] = await Promise.all([
        fetchRepeatGuests({ ...rangeParams, basis }),
        fetchLongStay({ ...rangeParams, basis }),
      ])
      setRepeat(rp)
      setLongStay(ls)
      // 長住拆解：用同一個門檻去打三個維度
      const t = ls.threshold
      const [byRate, byChannel, byCategory] = await Promise.all([
        fetchDimensionStats('rate_code', { ...rangeParams, basis, min_nights: t, limit: 10 }),
        fetchDimensionStats('channel', { ...rangeParams, basis, min_nights: t, limit: 10 }),
        fetchDimensionStats('room_category', { ...rangeParams, basis, min_nights: t, limit: 10 }),
      ])
      setLongStaySplit({ rate_code: byRate, channel: byChannel, room_category: byCategory })
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入住客統計失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis])

  const loadOpsTab = useCallback(async () => {
    setLoading(true)
    try {
      const [ct, sw] = await Promise.all([
        fetchCheckoutTime({ ...rangeParams, basis }),
        fetchStayWeekday({ ...rangeParams, basis }),
      ])
      setCheckoutTime(ct)
      setStayWeekday(sw)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入作業排程統計失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis])

  const loadRoomUsage = useCallback(async () => {
    setLoading(true)
    try {
      setRoomUsage(await fetchRoomUsage({ ...rangeParams, basis }))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入房號使用分析失敗')
    } finally {
      setLoading(false)
    }
  }, [rangeParams, basis])

  useEffect(() => {
    if (!range) return
    if (tab === 'stays') loadStays()
    else if (tab === 'channel') loadDimension('channel')
    else if (tab === 'room_category') loadDimension('room_category')
    else if (tab === 'rate_code') loadDimension('rate_code', 15)
    else if (tab === 'company') loadDimension('company', 20)
    else if (tab === 'payment') loadDimension('payment')
    else if (tab === 'group') loadDimension('group', 30)
    else if (tab === 'ops') loadOpsTab()
    else if (tab === 'rooms') loadRoomUsage()
    else if (tab === 'guest') loadGuestTab()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, range, basis, page, pageSize, search, channelFilter, categoryFilter, excludePerson])

  const openStayDrawer = useCallback(async (row: StayRow) => {
    setDrawerStay(row)
    setDrawerOpen(true)
    try {
      setDrawerStay(await fetchStayDetail(row.id))
    } catch {
      /* 列表資料已足夠顯示 */
    }
  }, [])

  // ── 住宿明細欄位 ────────────────────────────────────────────────────────
  const stayColumns: ColumnsType<StayRow> = [
    { title: '退房日', dataIndex: 'departure_date', width: 110, fixed: 'left' },
    { title: '入住日', dataIndex: 'arrival_date', width: 110 },
    { title: '房號', dataIndex: 'room_no', width: 80 },
    {
      title: '房型', dataIndex: 'room_category_label', width: 80,
      render: (v: string) => (v ? <Tag color="cyan">{v}</Tag> : EMPTY),
    },
    { title: '晚數', dataIndex: 'nights', width: 70, align: 'right', render: fmtInt },
    { title: '房晚', dataIndex: 'room_nights', width: 70, align: 'right', render: (v: number) => <Text strong>{fmtInt(v)}</Text> },
    { title: '成人', dataIndex: 'adults', width: 60, align: 'right', render: fmtInt },
    // ⚠️ dataIndex 是 child_count 不是 children —— antd Table 會把 record.children
    //    當成子列陣列，數字值會讓整頁崩潰（見 types/opera.ts StayRow 說明）
    { title: '兒童', dataIndex: 'child_count', width: 60, align: 'right', render: fmtInt },
    {
      title: '通路', dataIndex: 'channel', width: 160,
      render: (v: string) => <Tag color={v === '直客／未標註' ? 'default' : 'blue'}>{v}</Tag>,
    },
    { title: 'Rate Code', dataIndex: 'rate_code', width: 120, render: (v: string) => v || EMPTY },
    { title: '付款', dataIndex: 'payment_desc', width: 80, render: (v: string) => v || EMPTY },
    {
      title: '住客（遮罩）', dataIndex: 'guest_name_masked', width: 180,
      render: (v: string, r) => (r.is_purged ? <Text type="secondary">{v}</Text> : v || EMPTY),
    },
  ]

  // ── C9：通路 Pareto ─────────────────────────────────────────────────────
  // 圖只畫前 PARETO_TOP_N 名（長尾通路的長條在畫面上只有 1~2 px，標籤反而會
  // 互相重疊到看不懂）；累計占比仍以「全部通路」為分母計算，所以 Pareto 的
  // 判讀不受影響。完整清單在下方表格。
  const PARETO_TOP_N = 15
  const truncateLabel = (s: string, max = 14) => (s.length > max ? `${s.slice(0, max)}…` : s)

  const renderPareto = (data: DimensionResult | null | undefined) => {
    if (!data || data.items.length === 0) return <Empty description="期間內無資料" />
    const shown = data.items.slice(0, PARETO_TOP_N)
    const chartData = shown.map((i) => ({
      key: i.key,
      值: data.metric === 'room_nights' ? i.room_nights : i.records,
      累計占比: Number((i.cumulative_share * 100).toFixed(1)),
    }))
    return (
      <>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 50, left: 0, bottom: 70 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
            <XAxis
              dataKey="key"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: string) => truncateLabel(v)}
              angle={-35}
              textAnchor="end"
              interval={0}
              height={90}
            />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}%`} />
            <RcTooltip
              formatter={(v: any, n: string) => [n === '累計占比' ? `${v}%` : Number(v).toLocaleString('en-US'), n === '值' ? data.metric_label : n]}
              labelFormatter={(l: string) => l}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <ReferenceLine yAxisId="right" y={80} stroke={RED} strokeDasharray="5 4" label={{ value: '80%', position: 'right', fontSize: 11, fill: RED }} />
            <Bar yAxisId="left" dataKey="值" name={data.metric_label} fill={BRAND} />
            <Line yAxisId="right" type="monotone" dataKey="累計占比" stroke={ORANGE} strokeWidth={2} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
        {data.items.length > PARETO_TOP_N && (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {`圖表僅顯示前 ${PARETO_TOP_N} 名（共 ${data.items.length} 項），累計占比仍以全部項目為分母；完整清單見下方表格。`}
          </Text>
        )}
      </>
    )
  }

  const dimensionTable = (data: DimensionResult | null | undefined) => (
    <Table
      rowKey="key"
      size="small"
      dataSource={data?.items || []}
      scroll={{ x: 900 }}
      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 項` }}
      columns={[
        { title: data?.dimension_label || '項目', dataIndex: 'key', width: 240, fixed: 'left' },
        { title: '訂房筆數', dataIndex: 'records', align: 'right', render: fmtInt, sorter: (a, b) => a.records - b.records },
        { title: '房晚', dataIndex: 'room_nights', align: 'right', render: fmtInt, sorter: (a, b) => a.room_nights - b.room_nights },
        {
          title: (
            <Tooltip title="平均住宿天數 = 房晚 ÷ 訂房筆數（以房數計時筆數即房數）">
              <span>平均 LOS <InfoCircleOutlined style={{ color: ACCENT, fontSize: 11 }} /></span>
            </Tooltip>
          ),
          dataIndex: 'avg_los',
          align: 'right',
          render: (v: number) => (v ? `${v.toFixed(2)} 晚` : EMPTY),
          sorter: (a, b) => a.avg_los - b.avg_los,
        },
        {
          title: (
            <Tooltip title="住一晚就退房的訂房占該項目的比例；比例高代表房務翻房壓力大">
              <span>一晚住宿占比 <InfoCircleOutlined style={{ color: ACCENT, fontSize: 11 }} /></span>
            </Tooltip>
          ),
          dataIndex: 'one_night_share',
          align: 'right',
          render: (v: number, r) => (
            <Tooltip title={`${fmtInt(r.one_night_records)} 筆 / ${fmtInt(r.records)} 筆`}>
              <span>{fmtPct(v)}</span>
            </Tooltip>
          ),
          sorter: (a, b) => a.one_night_share - b.one_night_share,
        },
        { title: '成人', dataIndex: 'adults', align: 'right', render: fmtInt },
        { title: '占比', dataIndex: 'share', align: 'right', render: (v: number) => fmtPct(v) },
        { title: '累計占比', dataIndex: 'cumulative_share', align: 'right', render: (v: number) => fmtPct(v) },
      ]}
    />
  )

  // ── C15：LOS 分桶（房型 TAB）────────────────────────────────────────────
  const renderLosBuckets = () => {
    if (!losBuckets || losBuckets.buckets.length === 0) return <Empty description="期間內無資料" />
    return (
      <>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={losBuckets.buckets} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
            <RcTooltip
              formatter={(v: any, n: string) => [Number(v).toLocaleString('en-US'), n === 'records' ? '訂房筆數' : n]}
            />
            <Bar dataKey="records" name="訂房筆數" fill={BRAND}>
              {losBuckets.buckets.map((b, i) => (
                <Cell key={i} fill={b.is_long_stay ? ORANGE : BRAND} />
              ))}
              <LabelList
                dataKey="records"
                position="top"
                formatter={(v: any) => Number(v).toLocaleString('en-US')}
                style={{ fontSize: 11 }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {`桶界依「分析門檻設定」的長住門檻 ${losBuckets.threshold} 晚推導，橘色為長住區間；`}
          {`期間平均 LOS ${losBuckets.avg_los} 晚　${SOURCE_NOTE}`}
        </Text>
        <Table
          size="small"
          rowKey="label"
          style={{ marginTop: 12 }}
          pagination={false}
          dataSource={losBuckets.buckets}
          columns={[
            {
              title: '住宿天數', dataIndex: 'label', width: 120,
              render: (v: string, r) => (r.is_long_stay ? <Tag color="orange">{v}</Tag> : v),
            },
            { title: '訂房筆數', dataIndex: 'records', align: 'right', render: fmtInt },
            { title: '房晚', dataIndex: 'room_nights', align: 'right', render: fmtInt },
            { title: '占比', dataIndex: 'share', align: 'right', render: (v: number) => fmtPct(v) },
          ]}
        />
      </>
    )
  }

  // ── C10：房型圓餅 ───────────────────────────────────────────────────────
  const renderPie = (data: DimensionResult | null | undefined) => {
    if (!data || data.items.length === 0) return <Empty description="期間內無資料" />
    const pieData = data.items.map((i) => ({
      name: i.key,
      value: data.metric === 'room_nights' ? i.room_nights : i.records,
    }))
    return (
      <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
        <PieChart>
          {/* ⚠️ isAnimationActive={false} 是必要的，不是效能微調：App 跑在
              React.StrictMode 下，開發模式的雙重掛載會取消 recharts 的進場動畫，
              而 Pie 的 sector 只在動畫啟動後才產生 → 圓餅完全畫不出來（只剩標籤）。
              Bar／Line 不受影響。2026-08-04 實測確認。 */}
          <Pie
            data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%"
            outerRadius={100}
            isAnimationActive={false}
            label={(e: any) => (e.percent > 0.03 ? `${e.name} ${(e.percent * 100).toFixed(1)}%` : '')}
            labelLine={false}
          >
            {pieData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
          </Pie>
          <RcTooltip formatter={(v: any) => Number(v).toLocaleString('en-US')} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  // ── C11：Rate Code 橫向長條 ─────────────────────────────────────────────
  const renderHorizontalBar = (data: DimensionResult | null | undefined) => {
    if (!data || data.items.length === 0) return <Empty description="期間內無資料" />
    const chartData = data.items.map((i) => ({
      key: i.key,
      值: data.metric === 'room_nights' ? i.room_nights : i.records,
    }))
    return (
      <ResponsiveContainer width="100%" height={Math.max(240, chartData.length * 28)}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 10, right: 60, left: 10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#eee" />
          <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
          <YAxis type="category" dataKey="key" tick={{ fontSize: 11 }} width={140} />
          <RcTooltip formatter={(v: any) => [Number(v).toLocaleString('en-US'), data.metric_label]} />
          <Bar dataKey="值" name={data.metric_label} fill={ACCENT} barSize={16}>
            <LabelList dataKey="值" position="right" formatter={(v: any) => Number(v).toLocaleString('en-US')} style={{ fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )
  }

  const basisControl = (
    <Space>
      <Text>統計口徑</Text>
      <Tooltip title={BASIS_TIP}>
        <InfoCircleOutlined style={{ color: ACCENT }} />
      </Tooltip>
      <Radio.Group size="small" value={basis} onChange={(e) => { setBasis(e.target.value); setPage(1) }}>
        <Radio.Button value="room">以房數計</Radio.Button>
        <Radio.Button value="reservation">以訂單計</Radio.Button>
      </Radio.Group>
    </Space>
  )

  /**
   * 各 TAB 的說明 —— 原本是每個 TAB 內一則固定 Alert，改收到 TAB 標籤旁的「?」。
   * **所有說明文字一字未改**，只是換了容器。
   *
   * ⚠️ 這裡只收「固定口徑說明」。以下**刻意不收**：
   *    ① 作業排程的「缺值占比 X%」—— 只在缺值偏高時才出現的資料品質警示，
   *       收進「?」等於把警示藏起來，看不到就不會去改善前台輸入品質。
   *    ② 團體 TAB 那顆「只看團體／全部顯示」Switch —— 是功能控制項不是說明，
   *       已移到「團體貢獻」卡片的 extra，留在畫面上。
   */
  const tabHelp = (key: string): { title: string; body: React.ReactNode } | null => {
    switch (key) {
      case 'company':
        return {
          title: '公司欄位母體偏小',
          body: '實測 Departure 資料中約 86% 的紀錄沒有填寫公司名稱，本頁統計僅涵蓋有填寫的部分。',
        }
      case 'group':
        // 這個 TAB 原本有兩則 Alert，合在同一個「?」裡，兩則原文都保留
        return {
          title: 'OPERA 的團體欄位混了兩種資料，系統已自動分離',
          body: (
            <>
              <div style={{ lineHeight: 1.9 }}>
                實測 <Text strong>GROUP_NAME</Text> 欄位同時放了「真正的團體名稱」與
                「OTA 訂房參考號 + 訂房人姓名」。系統會先剝掉開頭的參考號
                （例如 <Text code>392298933 中山醫學大學</Text> → <Text code>中山醫學大學</Text>），
                再判斷剩下的是否為個人姓名格式。
              </div>
              {dimData.group?.person_records ? (
                <div style={{ marginTop: 6 }}>
                  <Text type="secondary">
                    {`目前排除了 ${fmtInt(dimData.group.person_records)} 筆疑似個人訂房；可用「團體貢獻」卡片右上的開關切換。`}
                  </Text>
                </div>
              ) : null}
              <div style={{ marginTop: 12 }}>
                <Text strong>這裡的數字是 Departure 的產量，不是團體營收</Text>
              </div>
              <div style={{ lineHeight: 1.9 }}>
                團體 vs 散客的營收與房晚請看「★ 營運分析 Dashboard」的「散客 vs 團體」
                （來源是 History and Forecast，數字才是準的）。
                Departure 無法把房間營收精確歸到個別團體。
              </div>
            </>
          ),
        }
      case 'payment':
        return {
          title: 'PAYMENT_DESC 未必等於實際交易明細',
          body: '這個欄位可能是訂單預設或結帳方式，不代表每一筆實際金流。金流稽核請使用 OPERA 的 Payment Transaction 報表。',
        }
      case 'rooms':
        // ⚠️ 內文是後端帶出的 `inference_note`，不是寫死的字串
        return {
          title: '「疑似停用」是推論，不是事實',
          body: roomUsage?.inference_note || '',
        }
      case 'ops':
        return {
          title: '這一頁是給櫃台、房務、行李與交通排班用的',
          body: '退房時間看單日尖峰時段；入退房星期看一週的到店／離店節奏。兩者都是「事件」統計，不是各時段的在住房數。',
        }
      case 'guest':
        // ⚠️ 標題與內文都含實際數字，沒有資料時不給「?」（見 tabLabel）
        return repeat ? {
          title: `本分析僅涵蓋非「已清除」住客，母體佔比 ${fmtPct(repeat.coverage.coverage)}`,
          body: `期間共 ${fmtInt(repeat.coverage.total)} 筆住宿紀錄，其中 ${fmtInt(repeat.coverage.purged)} 筆的住客資料已被 OPERA 清除（Purged-Individual），無法識別身分，因此不納入回訪統計。`,
        } : null
      default:
        return null
    }
  }

  /**
   * TAB 標籤 ＋ 說明「?」。
   * ⚠️ `stopPropagation` 是必要的 —— 沒有它，點「?」會連帶切換到那個 TAB。
   */
  const tabLabel = (key: string, node: React.ReactNode) => {
    if (!tabHelp(key)) return node
    return (
      <Space size={4} align="center">
        {node}
        <Tooltip title="說明">
          <QuestionCircleOutlined
            style={{ color: ACCENT }}
            onClick={(e) => { e.stopPropagation(); setTabHelpKey(key) }}
          />
        </Tooltip>
      </Space>
    )
  }

  const activeTabHelp = tabHelpKey ? tabHelp(tabHelpKey) : null

  return (
    <Spin spinning={loading}>
      <div style={{ padding: 24 }}>
        <Modal
          open={!!activeTabHelp}
          onCancel={() => setTabHelpKey(null)}
          footer={null}
          width={520}
          title={
            <Space size={8}>
              <InfoCircleOutlined style={{ color: ACCENT }} />
              <span>{activeTabHelp?.title}</span>
            </Space>
          }
        >
          <div style={{ lineHeight: 1.8 }}>{activeTabHelp?.body}</div>
        </Modal>

        <Row justify="space-between" align="middle" style={{ marginBottom: 12 }}>
          <Col>
            <Space size={6} align="center">
              <Title level={4} style={{ margin: 0, color: BRAND }}>住客與通路分析</Title>
              <Tooltip title="資料來源說明">
                <Button
                  type="text" size="small" aria-label="資料來源說明"
                  icon={<QuestionCircleOutlined style={{ color: ACCENT, fontSize: 16 }} />}
                  onClick={() => setHelpOpen(true)}
                />
              </Tooltip>
            </Space>
          </Col>
          <Col>
            <Space wrap>
              {basisControl}
              <StandardRangePicker value={range} anchor={dataEnd} onChange={setRange} />
              <Button icon={<ReloadOutlined />} onClick={() => setTab((t) => t)}>重新整理</Button>
            </Space>
          </Col>
        </Row>

        <Modal
          open={helpOpen}
          onCancel={() => setHelpOpen(false)}
          footer={null}
          width={520}
          title={
            <Space size={8}>
              <InfoCircleOutlined style={{ color: ACCENT }} />
              <span>資料來源說明</span>
            </Space>
          }
        >
          <div style={{ lineHeight: 1.8 }}>
            <div>{SOURCE_HEADLINE}</div>
            <Text type="secondary">{SOURCE_DETAIL}</Text>
          </div>
        </Modal>

        <Tabs
          activeKey={tab}
          onChange={(k) => { setTab(k); setPage(1) }}
          items={[
            // ── 住宿明細 ──────────────────────────────────────────────────
            {
              key: 'stays',
              label: '住宿明細',
              children: (
                <Card size="small" title="住宿明細（點擊列開啟明細）">
                  <Space wrap style={{ marginBottom: 12 }}>
                    <Input.Search
                      allowClear
                      placeholder="搜尋房號／訂房編號／外部參考號"
                      style={{ width: 260 }}
                      onSearch={(v) => { setSearch(v); setPage(1) }}
                    />
                    <Select
                      allowClear placeholder="通路" style={{ width: 200 }}
                      value={channelFilter || undefined}
                      onChange={(v) => { setChannelFilter(v || ''); setPage(1) }}
                      options={options.channel.map((c) => ({ value: c, label: c }))}
                    />
                    <Select
                      allowClear placeholder="房型" style={{ width: 140 }}
                      value={categoryFilter || undefined}
                      onChange={(v) => { setCategoryFilter(v || ''); setPage(1) }}
                      options={options.room_category.map((c) => ({ value: c, label: c }))}
                    />
                  </Space>
                  <Table
                    rowKey="id"
                    size="small"
                    dataSource={stays}
                    columns={stayColumns}
                    scroll={{ x: 1300 }}
                    pagination={{
                      current: page,
                      pageSize,
                      total: stayTotal,
                      showSizeChanger: true,
                      showTotal: (t) => `共 ${t.toLocaleString('en-US')} 筆`,
                      onChange: (p, ps) => { setPage(p); setPageSize(ps) },
                    }}
                    onRow={(record) => ({ onClick: () => openStayDrawer(record), style: { cursor: 'pointer' } })}
                  />
                </Card>
              ),
            },

            // ── 通路 ─────────────────────────────────────────────────────
            {
              key: 'channel',
              label: '通路',
              children: (
                <>
                  <Card
                    size="small"
                    title="通路貢獻 Pareto（累計占比達 80% 的通路即為主力）"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.channel?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderPareto(dimData.channel)}
                  </Card>
                  <Card size="small" title="通路統計">{dimensionTable(dimData.channel)}</Card>
                </>
              ),
            },

            // ── 房型 ─────────────────────────────────────────────────────
            {
              key: 'room_category',
              label: '房型',
              children: (
                <>
                  <Card
                    size="small"
                    title="房型占比"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.room_category?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderPie(dimData.room_category)}
                  </Card>
                  <Card
                    size="small"
                    title="住宿天數（LOS）分佈"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.room_category?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderLosBuckets()}
                  </Card>
                  <Card size="small" title="房型統計" style={{ marginBottom: 12 }}>
                    {dimensionTable(dimData.room_category)}
                  </Card>

                  {/* 客群結構：每房人數分布 + 家庭客房型偏好 —— 都是房型判讀的依據，故併在同一 TAB */}
                  <Row gutter={[12, 12]}>
                    <Col xs={24} lg={10}>
                      <Card size="small" title="每房人數分布">
                        {!guestMix || guestMix.distribution.length === 0 ? <Empty description="無資料" /> : (
                          <>
                            <ResponsiveContainer width="100%" height={230}>
                              <BarChart data={guestMix.distribution} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="pax" tick={{ fontSize: 11 }} />
                                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
                                <RcTooltip
                                  formatter={(v: any) => [Number(v).toLocaleString('en-US'), '筆數']}
                                  labelFormatter={(l) => `${l} 人`}
                                />
                                <Bar dataKey="records" name="筆數" fill={BRAND}>
                                  <LabelList dataKey="records" position="top" formatter={(v: any) => Number(v).toLocaleString('en-US')} style={{ fontSize: 10 }} />
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {`平均每房 ${guestMix.persons_per_room.toFixed(2)} 人。影響早餐備量、備品消耗與加床需求。　${SOURCE_NOTE}`}
                            </Text>
                          </>
                        )}
                      </Card>
                    </Col>

                    <Col xs={24} lg={14}>
                      <Card
                        size="small"
                        title={`家庭客（帶兒童）房型偏好${guestMix ? `　${fmtInt(guestMix.family.records)} 筆／${fmtPct(guestMix.family.share)}` : ''}`}
                      >
                        {!guestMix || guestMix.family.records === 0 ? <Empty description="期間內無帶兒童的訂房" /> : (
                          <>
                            <Table
                              rowKey="room_category"
                              size="small"
                              pagination={false}
                              dataSource={guestMix.family.by_category}
                              columns={[
                                { title: '房型', dataIndex: 'room_category', width: 90 },
                                { title: '家庭客筆數', dataIndex: 'family_records', align: 'right', render: fmtInt },
                                { title: '該房型總筆數', dataIndex: 'total_records', align: 'right', render: fmtInt },
                                { title: '家庭客占比', dataIndex: 'family_share', align: 'right', render: (v: number) => fmtPct(v) },
                                {
                                  title: (
                                    <Tooltip title="該房型的家庭客占比 ÷ 全體家庭客占比。大於 1 代表家庭客特別偏好這個房型">
                                      <span>集中度 <InfoCircleOutlined style={{ color: ACCENT, fontSize: 11 }} /></span>
                                    </Tooltip>
                                  ),
                                  dataIndex: 'index',
                                  align: 'right',
                                  render: (v: number) => (
                                    <Text strong style={{ color: v >= 2 ? ORANGE : v >= 1 ? GREEN : undefined }}>
                                      {v.toFixed(2)}
                                    </Text>
                                  ),
                                  sorter: (a, b) => a.index - b.index,
                                  defaultSortOrder: 'descend',
                                },
                              ]}
                            />
                            <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                              {`家庭客平均住 ${guestMix.family.avg_los} 晚（全體 ${guestMix.family.overall_avg_los} 晚）、兒童共 ${fmtInt(guestMix.family.children)} 人。`}
                              集中度高的房型可優先配置嬰兒床、加床與兒童備品。
                            </Text>
                          </>
                        )}
                      </Card>
                    </Col>
                  </Row>
                </>
              ),
            },

            // ── Rate Code ────────────────────────────────────────────────
            {
              key: 'rate_code',
              label: 'Rate Code',
              children: (
                <>
                  <Card
                    size="small"
                    title="Rate Code Top 15"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.rate_code?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderHorizontalBar(dimData.rate_code)}
                  </Card>
                  <Card size="small" title="Rate Code 統計">{dimensionTable(dimData.rate_code)}</Card>
                </>
              ),
            },

            // ── 公司 ─────────────────────────────────────────────────────
            {
              key: 'company',
              label: tabLabel('company', '公司'),
              children: (
                <>
                  {/* 說明已收進 TAB 標籤旁的「?」 */}
                  <Card
                    size="small"
                    title="公司 Top 20"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.company?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderHorizontalBar(dimData.company)}
                  </Card>
                  <Card size="small" title="公司統計">{dimensionTable(dimData.company)}</Card>
                </>
              ),
            },

            // ── 團體 ─────────────────────────────────────────────────────
            {
              key: 'group',
              label: tabLabel('group', '團體'),
              children: (
                <>
                  {/* 說明已收進 TAB 標籤旁的「?」；
                      ⚠️ Switch 是功能控制項不是說明，移到卡片 extra 留在畫面上 */}
                  <Card
                    size="small"
                    title={excludePerson ? '團體貢獻（已排除個人訂房）' : '團體貢獻（含疑似個人訂房）'}
                    extra={
                      <Space size={12}>
                        <Switch
                          size="small"
                          checked={excludePerson}
                          onChange={setExcludePerson}
                          checkedChildren="只看團體"
                          unCheckedChildren="全部顯示"
                        />
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {`${dimData.group?.basis_label || ''}　${SOURCE_NOTE}`}
                        </Text>
                      </Space>
                    }
                    style={{ marginBottom: 12 }}
                  >
                    {renderHorizontalBar(dimData.group)}
                  </Card>
                  <Card size="small" title="團體統計">{dimensionTable(dimData.group)}</Card>
                </>
              ),
            },

            // ── 付款方式 ─────────────────────────────────────────────────
            {
              key: 'payment',
              label: tabLabel('payment', '付款方式'),
              children: (
                <>
                  <Card
                    size="small"
                    title="付款方式占比"
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${dimData.payment?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {renderPie(dimData.payment)}
                  </Card>
                  <Card size="small" title="付款方式統計">{dimensionTable(dimData.payment)}</Card>
                  {/* 說明已收進 TAB 標籤旁的「?」 */}
                </>
              ),
            },

            // ── 房號使用 ─────────────────────────────────────────────────
            {
              key: 'rooms',
              label: tabLabel('rooms', (
                <span>
                  房號使用
                  {roomUsage && roomUsage.suspected_inactive_count > 0 && (
                    <Tag color="red" style={{ marginLeft: 6 }}>{roomUsage.suspected_inactive_count}</Tag>
                  )}
                </span>
              )),
              children: (
                <>
                  {/* 說明已收進 TAB 標籤旁的「?」 */}

                  {roomUsage && (
                    <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                      {[
                        { title: '房間數', value: `${fmtInt(roomUsage.room_count)} 間`, color: BRAND },
                        { title: '平均每間銷售', value: `${roomUsage.avg_per_room} 次`, color: ACCENT },
                        {
                          title: '最忙 vs 最閒',
                          value: roomUsage.spread_ratio ? `${roomUsage.spread_ratio} 倍` : EMPTY,
                          color: ORANGE,
                        },
                        {
                          title: `疑似停用（連續 ≥ ${roomUsage.inactive_months_threshold} 個月零銷售）`,
                          value: `${fmtInt(roomUsage.suspected_inactive_count)} 間`,
                          color: roomUsage.suspected_inactive_count > 0 ? RED : GREEN,
                        },
                      ].map((it) => (
                        <Col xs={12} lg={6} key={it.title}>
                          <Card size="small" bodyStyle={{ padding: '12px 16px' }} style={{ borderLeft: `3px solid ${it.color}` }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>{it.title}</Text>
                            <div><Text strong style={{ fontSize: 20, color: it.color }}>{it.value}</Text></div>
                          </Card>
                        </Col>
                      ))}
                    </Row>
                  )}

                  <Card size="small" title="樓層使用比較" style={{ marginBottom: 12 }}>
                    {!roomUsage || roomUsage.floors.length === 0 ? <Empty description="期間內無資料" /> : (
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={roomUsage.floors} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                          <XAxis dataKey="floor" tick={{ fontSize: 12 }} tickFormatter={(v: string) => `${v} 樓`} />
                          <YAxis tick={{ fontSize: 11 }} />
                          <RcTooltip
                            formatter={(v: any) => [Number(v).toLocaleString('en-US'), '平均每間銷售次數']}
                            labelFormatter={(l) => `${l} 樓`}
                          />
                          <ReferenceLine
                            y={roomUsage.avg_per_room}
                            stroke={RED}
                            strokeDasharray="5 4"
                            label={{ value: `全館平均 ${roomUsage.avg_per_room}`, position: 'right', fontSize: 11, fill: RED }}
                          />
                          <Bar dataKey="avg_per_room" name="平均每間銷售次數" fill={BRAND}>
                            <LabelList dataKey="avg_per_room" position="top" style={{ fontSize: 11 }} />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      用「平均每間」比較才公平（各樓層房間數不同）。　{SOURCE_NOTE}
                    </Text>
                  </Card>

                  <Card size="small" title="房號逐月銷售（由少到多；■ = 該月有賣出、· = 該月完全沒賣）">
                    <Table
                      rowKey="room_no"
                      size="small"
                      dataSource={roomUsage?.rooms || []}
                      scroll={{ x: 1100 }}
                      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 間` }}
                      rowClassName={(r) => (r.suspected_inactive ? 'opera-room-inactive' : '')}
                      columns={[
                        {
                          title: '房號', dataIndex: 'room_no', width: 90, fixed: 'left',
                          render: (v: string, r) => (
                            r.suspected_inactive
                              ? <Tooltip title="末次銷售後連續多月零銷售"><Tag color="red">{v}</Tag></Tooltip>
                              : <Text strong>{v}</Text>
                          ),
                        },
                        { title: '樓層', dataIndex: 'floor', width: 70, render: (v: string) => `${v} 樓` },
                        {
                          title: '銷售次數', dataIndex: 'records', align: 'right', width: 100,
                          render: fmtInt, sorter: (a, b) => a.records - b.records, defaultSortOrder: 'ascend',
                        },
                        {
                          title: (
                            <Tooltip title="該房銷售次數 ÷ 全館平均。0.5 代表只有平均的一半">
                              <span>vs 平均 <InfoCircleOutlined style={{ color: ACCENT, fontSize: 11 }} /></span>
                            </Tooltip>
                          ),
                          dataIndex: 'vs_avg', align: 'right', width: 100,
                          render: (v: number) => (
                            <Text style={{ color: v < 0.5 ? RED : v < 0.8 ? ORANGE : undefined }}>{`${v.toFixed(2)}x`}</Text>
                          ),
                          sorter: (a, b) => a.vs_avg - b.vs_avg,
                        },
                        {
                          title: '逐月',
                          dataIndex: 'monthly',
                          width: 280,
                          render: (v: number[]) => (
                            <Tooltip title={(roomUsage?.months || []).map((m, i) => `${m}:${v[i]}`).join('  ')}>
                              <Text code style={{ fontSize: 11, letterSpacing: 1 }}>
                                {v.map((n) => (n > 0 ? '■' : '·')).join('')}
                              </Text>
                            </Tooltip>
                          ),
                        },
                        { title: '零銷售月數', dataIndex: 'zero_months', align: 'right', width: 110, render: fmtInt },
                        {
                          title: (
                            <Tooltip title="末次銷售之後連續幾個月完全沒賣，是判斷停用的主要依據">
                              <span>末次後連零 <InfoCircleOutlined style={{ color: ACCENT, fontSize: 11 }} /></span>
                            </Tooltip>
                          ),
                          dataIndex: 'trailing_zero_months', align: 'right', width: 120,
                          render: (v: number) => (v > 0 ? <Text strong style={{ color: v >= 3 ? RED : ORANGE }}>{`${v} 個月`}</Text> : EMPTY),
                          sorter: (a, b) => a.trailing_zero_months - b.trailing_zero_months,
                        },
                        {
                          title: (
                            <Tooltip title="該房零銷售、但全館住房率仍 ≥ 60% 的月份數。次數越多越不可能是「沒需求」">
                              <span>高住房率仍零銷售 <InfoCircleOutlined style={{ color: ACCENT, fontSize: 11 }} /></span>
                            </Tooltip>
                          ),
                          dataIndex: 'suspicious_zero_months', align: 'right', width: 150,
                          render: (v: number) => (v > 0 ? <Text style={{ color: ORANGE }}>{`${v} 個月`}</Text> : EMPTY),
                          sorter: (a, b) => a.suspicious_zero_months - b.suspicious_zero_months,
                        },
                        { title: '首次', dataIndex: 'first_month', width: 90 },
                        { title: '末次', dataIndex: 'last_month', width: 90 },
                      ]}
                    />
                    <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                      一間房若長期低於平均，可能是景觀、噪音、設備問題，或前台排房習慣。
                      按每間房平均銷售 {roomUsage?.avg_per_room ?? '—'} 次估算，
                      一間長期賣不掉的房，機會成本相當可觀——建議對照工程與房務紀錄逐間確認。
                    </Text>
                  </Card>
                </>
              ),
            },

            // ── 作業排程（退房時間 + 入退房星期）──────────────────────────
            // 這兩個分析的用途相同（櫃台、房務、行李與交通的人力安排），
            // 合成一個 TAB 比拆成兩個更好用，也避免 TAB 列過長。
            {
              key: 'ops',
              label: tabLabel('ops', '作業排程'),
              children: (
                <>
                  {/* 說明已收進 TAB 標籤旁的「?」 */}

                  <Row gutter={[12, 12]}>
                    {/* 退房時間分布 */}
                    <Col xs={24} lg={12}>
                      <Card
                        size="small"
                        title="退房時間分布"
                        extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${checkoutTime?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                      >
                        {!checkoutTime || checkoutTime.total_records === 0 ? (
                          <Empty description="期間內無資料" />
                        ) : (
                          <>
                            <ResponsiveContainer width="100%" height={260}>
                              <BarChart data={checkoutTime.buckets} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
                                <RcTooltip formatter={(v: any) => [Number(v).toLocaleString('en-US'), '筆數']} />
                                <Bar dataKey="records" name="筆數" fill={BRAND}>
                                  {checkoutTime.buckets.map((b, i) => (
                                    <Cell key={i} fill={b.label === '缺值' ? '#bfbfbf' : b.label === '13 點後' ? ORANGE : BRAND} />
                                  ))}
                                  <LabelList
                                    dataKey="records"
                                    position="top"
                                    formatter={(v: any) => Number(v).toLocaleString('en-US')}
                                    style={{ fontSize: 11 }}
                                  />
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                            <Table
                              size="small"
                              rowKey="label"
                              pagination={false}
                              style={{ marginTop: 8 }}
                              dataSource={checkoutTime.buckets}
                              columns={[
                                {
                                  title: '時段', dataIndex: 'label', width: 130,
                                  render: (v: string) => (v === '缺值' ? <Tag>{v}</Tag> : v === '13 點後' ? <Tag color="orange">{v}</Tag> : v),
                                },
                                { title: '筆數', dataIndex: 'records', align: 'right', render: fmtInt },
                                { title: '占比', dataIndex: 'share', align: 'right', render: (v: number) => fmtPct(v) },
                              ]}
                            />
                            {checkoutTime.missing_share > 0.05 ? (
                              <Alert
                                type="warning"
                                showIcon
                                style={{ marginTop: 8 }}
                                message={`缺值占比 ${fmtPct(checkoutTime.missing_share)}`}
                                description="缺值偏高時，應先改善前台輸入或報表欄位品質，再拿這張表做排班決策。"
                              />
                            ) : (
                              <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                                {`缺值 ${fmtInt(checkoutTime.missing_records)} 筆（${fmtPct(checkoutTime.missing_share)}），資料品質良好。`}
                                13 點後占比高可能反映 Late Check-out、會員禮遇或房務週轉壓力。
                              </Text>
                            )}
                          </>
                        )}
                      </Card>
                    </Col>

                    {/* 入退房星期 */}
                    <Col xs={24} lg={12}>
                      <Card
                        size="small"
                        title="入退房星期分布"
                        extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${stayWeekday?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                      >
                        {!stayWeekday || stayWeekday.total_arrival_rooms === 0 ? (
                          <Empty description="期間內無資料" />
                        ) : (
                          <>
                            <ResponsiveContainer width="100%" height={260}>
                              <ComposedChart data={stayWeekday.weekdays} margin={{ top: 20, right: 10, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
                                <RcTooltip formatter={(v: any, n: string) => [Number(v).toLocaleString('en-US'), n]} />
                                <Legend wrapperStyle={{ fontSize: 12 }} />
                                <Bar dataKey="arrival_rooms" name="到店房數" fill={GREEN} barSize={16} />
                                <Bar dataKey="departure_rooms" name="離店房數" fill={ORANGE} barSize={16} />
                                <Line type="monotone" dataKey="net_rooms" name="淨增減" stroke={BRAND} strokeWidth={2} dot={{ r: 3 }} />
                              </ComposedChart>
                            </ResponsiveContainer>
                            <Table
                              size="small"
                              rowKey="weekday"
                              pagination={false}
                              style={{ marginTop: 8 }}
                              dataSource={stayWeekday.weekdays}
                              columns={[
                                { title: '星期', dataIndex: 'label', width: 70 },
                                { title: '到店', dataIndex: 'arrival_rooms', align: 'right', render: fmtInt },
                                { title: '占比', dataIndex: 'arrival_share', align: 'right', render: (v: number) => fmtPct(v) },
                                { title: '離店', dataIndex: 'departure_rooms', align: 'right', render: fmtInt },
                                { title: '占比', dataIndex: 'departure_share', align: 'right', render: (v: number) => fmtPct(v) },
                                {
                                  title: '淨增減', dataIndex: 'net_rooms', align: 'right',
                                  render: (v: number) => (
                                    <Text style={{ color: v > 0 ? GREEN : v < 0 ? ORANGE : undefined }}>
                                      {`${v > 0 ? '+' : ''}${fmtInt(v)}`}
                                    </Text>
                                  ),
                                },
                              ]}
                            />
                            <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                              到店高峰安排接待、備房與交通；離店高峰安排結帳與清掃。
                              <Text strong> 這是按訂單的到店／離店事件統計，不是各星期的在住房晚。</Text>
                            </Text>
                          </>
                        )}
                      </Card>
                    </Col>
                  </Row>
                </>
              ),
            },

            // ── 回訪與長住 ────────────────────────────────────────────────
            {
              key: 'guest',
              label: tabLabel('guest', '回訪與長住'),
              children: (
                <>
                  {/* 說明已收進 TAB 標籤旁的「?」（沒有 repeat 資料時「?」不顯示） */}

                  <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                    {/* C12：回訪次數分布 */}
                    <Col xs={24} lg={12}>
                      <Card size="small" title="回訪次數分布">
                        {!repeat || repeat.total_guests === 0 ? <Empty description="期間內無可識別住客" /> : (
                          <>
                            <ResponsiveContainer width="100%" height={240}>
                              <BarChart data={repeat.distribution} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
                                <RcTooltip formatter={(v: any) => [Number(v).toLocaleString('en-US'), '住客數']} />
                                <Bar dataKey="guests" name="住客數" fill={BRAND} barSize={40}>
                                  <LabelList dataKey="guests" position="top" style={{ fontSize: 11 }} />
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {`可識別住客 ${fmtInt(repeat.total_guests)} 人，其中回訪 ${fmtInt(repeat.repeat_guests)} 人（${fmtPct(repeat.repeat_rate)}）　${SOURCE_NOTE}`}
                            </Text>
                          </>
                        )}
                      </Card>
                    </Col>

                    {/* C13：住宿晚數分布 */}
                    <Col xs={24} lg={12}>
                      <Card size="small" title="住宿晚數分布">
                        {!longStay || longStay.distribution.length === 0 ? <Empty description="期間內無資料" /> : (
                          <>
                            <ResponsiveContainer width="100%" height={240}>
                              <BarChart
                                data={longStay.distribution.filter((d) => d.nights <= 21)}
                                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                              >
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                                <XAxis dataKey="nights" tick={{ fontSize: 11 }} />
                                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => v.toLocaleString('en-US')} />
                                <RcTooltip formatter={(v: any) => [Number(v).toLocaleString('en-US'), '筆數']} labelFormatter={(l) => `${l} 晚`} />
                                <ReferenceLine
                                  x={longStay.threshold}
                                  stroke={RED}
                                  strokeDasharray="5 4"
                                  label={{ value: `長住門檻 ${longStay.threshold} 晚`, position: 'top', fontSize: 11, fill: RED }}
                                />
                                <Bar dataKey="records" name="筆數" fill={ACCENT}>
                                  {longStay.distribution.filter((d) => d.nights <= 21).map((d, i) => (
                                    <Cell key={i} fill={d.is_long_stay ? ORANGE : ACCENT} />
                                  ))}
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {`長住 ${fmtInt(longStay.long_records)} / ${fmtInt(longStay.total_records)} 筆（${fmtPct(longStay.long_rate)}）　僅顯示 21 晚以內　${SOURCE_NOTE}`}
                            </Text>
                          </>
                        )}
                      </Card>
                    </Col>
                  </Row>

                  {/* 長住客拆解：依 Rate Code／通路／房型 */}
                  <Card
                    size="small"
                    title={`長住客拆解（住宿晚數 ≥ ${longStay?.threshold ?? 7} 晚）`}
                    extra={<Text type="secondary" style={{ fontSize: 12 }}>{`${longStay?.basis_label || ''}　${SOURCE_NOTE}`}</Text>}
                    style={{ marginBottom: 12 }}
                  >
                    {!longStay || longStay.long_records === 0 ? (
                      <Empty description="期間內無長住紀錄" />
                    ) : (
                      <Row gutter={[12, 12]}>
                        {([
                          ['rate_code', 'Rate Code'],
                          ['channel', '通路'],
                          ['room_category', '房型'],
                        ] as const).map(([dim, label]) => {
                          const d = longStaySplit[dim]
                          return (
                            <Col xs={24} lg={8} key={dim}>
                              <Card size="small" type="inner" title={`依 ${label}`} bodyStyle={{ padding: 8 }}>
                                {!d || d.items.length === 0 ? (
                                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="無資料" />
                                ) : (
                                  <Table
                                    rowKey="key"
                                    size="small"
                                    pagination={false}
                                    dataSource={d.items.slice(0, 8)}
                                    columns={[
                                      { title: label, dataIndex: 'key', ellipsis: true },
                                      { title: '筆數', dataIndex: 'records', align: 'right', width: 64, render: fmtInt },
                                      { title: '房晚', dataIndex: 'room_nights', align: 'right', width: 70, render: fmtInt },
                                      {
                                        title: 'LOS', dataIndex: 'avg_los', align: 'right', width: 64,
                                        render: (v: number) => (v ? v.toFixed(1) : EMPTY),
                                      },
                                    ]}
                                  />
                                )}
                              </Card>
                            </Col>
                          )
                        })}
                      </Row>
                    )}
                    <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
                      門檻可在「分析門檻設定」調整；跨期比較請維持一致的門檻。
                      長住的營收與獲利需要逐訂單逐日營收資料，Departure 本身無法安全分配 History 營收。
                    </Text>
                  </Card>

                  <Card size="small" title="回訪住客（2 次以上）">
                    <Table
                      rowKey="guest_hash"
                      size="small"
                      dataSource={repeat?.top_guests || []}
                      pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 位` }}
                      columns={[
                        { title: '住客（遮罩）', dataIndex: 'guest_label', width: 220 },
                        { title: '識別碼', dataIndex: 'guest_hash', width: 140, render: (v: string) => <Text code style={{ fontSize: 11 }}>{v}</Text> },
                        { title: '入住次數', dataIndex: 'visits', align: 'right', render: (v: number) => <Text strong style={{ color: GREEN }}>{fmtInt(v)}</Text>, sorter: (a, b) => a.visits - b.visits },
                        { title: '總房晚', dataIndex: 'room_nights', align: 'right', render: fmtInt },
                        { title: '總住宿晚數', dataIndex: 'nights', align: 'right', render: fmtInt },
                        { title: '最近退房日', dataIndex: 'last_departure', width: 120 },
                      ]}
                    />
                  </Card>
                </>
              ),
            },
          ]}
        />

        <StayDetailDrawer open={drawerOpen} stay={drawerStay} onClose={() => setDrawerOpen(false)} />

        <BackToTop />
      </div>
    </Spin>
  )
}

export default OperaGuestPage
