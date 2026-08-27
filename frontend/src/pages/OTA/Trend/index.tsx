/**
 * OTA 口碑分析 — 趨勢與雙館比較
 * Route: /ota/trend    Permission: ota_trend_view
 *
 * 規格書：`docs/SPEC_ota_reviews.md` §9（P5）
 *
 * 【與 Dashboard 的分工】
 *   Dashboard  回答「現在如何」—— KPI、當期主題分佈
 *   本頁       回答「跟誰比、怎麼變」—— 時間軸、館別、平台三個維度交叉
 *
 * ⚠️ **雙館比較不可以「每館各跑一次分析再併排」**。
 *    那樣各館的主題定義不同、時間軸不對齊，根本不可比。
 *    正確做法是「全集團共用一套定義，再算每個維度的表現」——
 *    這也是後端 `/stats/monthly` 一次回所有館別的原因。
 *
 * ⚠️ 期間篩選一律 `StandardRangePicker`，`anchor` 取**評論資料最後一天**
 *    而非 `dayjs()`（CLAUDE.md §8.2）。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Card, Col, Empty, Row, Segmented, Select, Space, Spin, Table,
  Tag, Tooltip, Typography, message,
} from 'antd'
import { QuestionCircleOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip as ReTooltip, XAxis, YAxis,
} from 'recharts'

import StandardRangePicker from '@/components/StandardRangePicker'
import { MultiCodeSelect, ScopeText, describeCodes, hotelOptions, platformOptions, toParam }
  from '../filterScope'
import TopicRotationHeatmap from '../TopicRotationHeatmap'
import {
  fetchDataRange, fetchHotelOptions, fetchMonthly, fetchPlatformOptions,
  fetchPlatformStats, fetchTopicRotation,
} from '@/api/ota'
import type {
  HotelOption, MonthlyPoint, PlatformOption, PlatformStat,
  TopicRotationBasis, TopicRotationResult,
} from '@/types/ota'

const { Text, Paragraph } = Typography

// ⚠️ 品牌色（CLAUDE.md 受保護元素），不要改
const SERIES_COLORS = ['#1B3A5C', '#4BA8E8', '#52c41a', '#faad14', '#eb2f96', '#722ed1']

// 樣本數低於這個值的月份，畫面上要標出來 —— 平均分會被單一評論帶著跑
const THIN_SAMPLE = 5

type ChartMode = 'score' | 'count'

interface CompareRow {
  hotel_code: string
  hotel_name: string
  platform: string
  platform_label: string
  avg_score_10: number | null
  count: number
}

const OtaTrendPage: React.FC = () => {
  const [hotels, setHotels] = useState<HotelOption[]>([])
  const [platforms, setPlatforms] = useState<PlatformOption[]>([])
  // ⚠️ 2026-08-25 改多選：空陣列 ＝ 全部
  const [hotelCodes, setHotelCodes] = useState<string[]>([])
  const [platformCodes, setPlatformCodes] = useState<string[]>([])
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [dataEnd, setDataEnd] = useState('')
  const [mode, setMode] = useState<ChartMode>('score')

  const [monthly, setMonthly] = useState<MonthlyPoint[]>([])
  const [platformStats, setPlatformStats] = useState<PlatformStat[]>([])
  const [loading, setLoading] = useState(false)

  // ⭐ 主題輪動（2026-08-27）
  // ⚠️ 預設 `negative` —— 這張圖是拿來找問題的。切成 `all` 之後名次會被
  //    常態被稱讚的主題（早餐、服務）洗掉，負面訊號反而看不見。
  const [rotation, setRotation] = useState<TopicRotationResult | null>(null)
  const [rotationBasis, setRotationBasis] = useState<TopicRotationBasis>('negative')
  const [rotationTopN, setRotationTopN] = useState(10)
  // ⚠️ 全螢幕放大的是**整張 Card** 而不是熱力圖本身 ——
  //    否則 basis 與「顯示主題數」兩個控制項會留在 Card 的 extra 沒被放大，
  //    進了全螢幕就調不到（理由見 TopicRotationHeatmap 的 `fullscreenRef`）。
  const rotationCardRef = useRef<HTMLDivElement>(null)

  const filters = useMemo(() => ({
    hotel_code: toParam(hotelCodes),
    platform: toParam(platformCodes),
    // range 為 null ＝「全部」，不帶起迄由後端套完整範圍（§8.3）
    ...(range
      ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') }
      : {}),
  }), [hotelCodes, platformCodes, range])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rangeInfo, mon, plat, rot] = await Promise.all([
        fetchDataRange(toParam(hotelCodes) || ''),
        fetchMonthly(filters),
        // ⚠️ 平台對照**不帶 platform 篩選** —— 篩了就只剩一根長條，
        //    這張圖的重點就是各平台之間的落差。
        fetchPlatformStats({ hotel_code: toParam(hotelCodes),
          ...(range
            ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') }
            : {}) }),
        // ⚠️ 輪動圖**要**帶 platform 篩選（與平台對照相反）——
        //    它問的是「這個範圍裡客訴重心怎麼移」，篩選就是那個範圍的定義。
        fetchTopicRotation(filters, { basis: rotationBasis, top_n: rotationTopN }),
      ])
      setDataEnd(rangeInfo.end)
      setMonthly(mon)
      setPlatformStats(plat)
      setRotation(rot)
    } catch {
      message.error('載入趨勢資料失敗')
    } finally {
      setLoading(false)
    }
  }, [hotelCodes, filters, range, rotationBasis, rotationTopN])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    fetchHotelOptions().then(setHotels).catch(() => undefined)
    fetchPlatformOptions().then(setPlatforms).catch(() => undefined)
  }, [])

  /** 長表 → recharts 寬表。全集團共用一條時間軸，各館是不同的線。 */
  const { rows, seriesNames } = useMemo(() => {
    const names = [...new Set(monthly.map((m) => m.hotel_name || m.hotel_code))]
    const byMonth = new Map<string, Record<string, string | number | null>>()
    monthly.forEach((m) => {
      const key = m.hotel_name || m.hotel_code
      const row = byMonth.get(m.review_month) ?? { month: m.review_month }
      row[key] = mode === 'score' ? m.avg_score_10 : m.count
      row[`${key}__count`] = m.count
      byMonth.set(m.review_month, row)
    })
    return {
      rows: [...byMonth.values()].sort(
        (a, b) => String(a.month).localeCompare(String(b.month))),
      seriesNames: names,
    }
  }, [monthly, mode])

  /**
   * ⭐ 各平台長條圖的資料（2026-08-23 修，與 Dashboard 同一個 bug）。
   *
   * ⚠️ `/stats/platform` 是 `group_by(platform, hotel_code)` —— 回的是
   *    「平台 × 飯店」交叉。只拿 `platform_label` 當名稱的話，
   *    兩間飯店會變成兩根一模一樣叫「Agoda」的長條。
   */
  const platformChart = useMemo(() => {
    const codes = new Set(platformStats.map((p) => p.hotel_code).filter(Boolean))
    const needHotel = codes.size > 1
    return platformStats.map((p) => ({
      name: needHotel
        ? `${p.platform_label}\n${hotels.find((h) => h.value === p.hotel_code)?.label || p.hotel_code}`
        : p.platform_label,
      分數: p.avg_score_10,
      則數: p.count,
    }))
  }, [platformStats, hotels])

  /** 館別 × 平台的交叉表。**這是「雙館比較」真正有用的那張表**。 */
  const compareRows: CompareRow[] = useMemo(
    () => platformStats
      .filter((p) => p.hotel_code)
      .map((p) => ({
        hotel_code: p.hotel_code,
        hotel_name: hotels.find((h) => h.value === p.hotel_code)?.label || p.hotel_code,
        platform: p.platform,
        platform_label: p.platform_label,
        avg_score_10: p.avg_score_10 ?? null,
        count: p.count,
      }))
      .sort((a, b) => a.hotel_code.localeCompare(b.hotel_code)
        || a.platform.localeCompare(b.platform)),
    [platformStats, hotels],
  )

  /** 目前的篩選條件，給 context bar 與卡片標題共用（理由同 Dashboard）。 */
  const scope = useMemo(() => {
    const hotelLabel = describeCodes(hotelCodes, hotelOptions(hotels), '全部飯店')
    const platformLabel = describeCodes(
      platformCodes, platformOptions(platforms), '全部平台')
    const periodLabel = range
      ? `${range[0].format('YYYY-MM-DD')} ~ ${range[1].format('YYYY-MM-DD')}`
      : '全部期間'
    const parts: string[] = []
    if (hotelCodes.length) parts.push(hotelLabel)
    if (platformCodes.length) parts.push(platformLabel)
    return {
      hotelLabel,
      platformLabel,
      periodLabel,
      isFiltered: hotelCodes.length > 0 || platformCodes.length > 0 || Boolean(range),
      titleSuffix: parts.length ? `（${parts.join('・')}）` : '',
    }
  }, [hotelCodes, platformCodes, hotels, platforms, range])


  /**
   * ⭐ 各館的負評／警示彙總（2026-08-23）。
   *
   * 資料來自 `/stats/monthly` 的 `negative_count` / `alert_open_count`，
   * 那兩個欄位與 Dashboard KPI 是**同一組條件**算出來的 —— 兩邊的數字
   * 必須對得起來，否則使用者會同時不信任兩個畫面。
   *
   * ⚠️ 放在**趨勢圖旁邊**而不是另開一張卡：看折線時最想知道的就是
   *    「這條線背後有幾則負評、幾件還沒處理」。分開放就要來回看兩個地方。
   */
  const hotelSummary = useMemo(() => {
    const byHotel = new Map<string, { name: string; neg: number; alert: number; total: number }>()
    monthly.forEach((m) => {
      const name = m.hotel_name || m.hotel_code
      const cur = byHotel.get(name) ?? { name, neg: 0, alert: 0, total: 0 }
      cur.neg += m.negative_count
      cur.alert += m.alert_open_count
      cur.total += m.count
      byHotel.set(name, cur)
    })
    return [...byHotel.values()]
  }, [monthly])

  // 樣本太少的月份 —— 拿來提醒，不是拿來隱藏
  const thinMonths = useMemo(
    () => monthly.filter((m) => m.count > 0 && m.count < THIN_SAMPLE),
    [monthly],
  )

  const compareColumns: ColumnsType<CompareRow> = [
    { title: '飯店', dataIndex: 'hotel_name', width: 150,
      render: (v: string) => <b>{v}</b> },
    { title: '平台', dataIndex: 'platform_label', width: 130,
      render: (v: string) => <Tag>{v}</Tag> },
    {
      title: '平均分（10 分制）', dataIndex: 'avg_score_10', width: 160,
      sorter: (a, b) => (a.avg_score_10 ?? 0) - (b.avg_score_10 ?? 0),
      render: (v: number | null) => (v === null ? <Text type="secondary">—</Text> : (
        <Text strong style={{
          color: v >= 8 ? '#52c41a' : v >= 6 ? '#faad14' : '#cf1322',
        }}>
          {v.toFixed(2)}
        </Text>
      )),
    },
    {
      title: '則數', dataIndex: 'count', width: 110,
      sorter: (a, b) => a.count - b.count,
      render: (v: number) => (
        v < THIN_SAMPLE
          ? <Space size={4}>
              <Text>{v}</Text>
              <Tag color="warning">樣本少</Tag>
            </Space>
          : <Text>{v}</Text>
      ),
    },
  ]

  return (
    <div>
      {/* ⚠️ 有篩選時整條換底色 —— 給「掃過去」的眼睛看的，
          只寫一行小字的話掃視的人不會停下來讀 */}
      <Card
        size="small"
        style={{
          marginBottom: 16,
          background: scope.isFiltered ? '#f0f7ff' : undefined,
          borderLeft: scope.isFiltered ? '4px solid #4BA8E8' : undefined,
        }}
      >
        <Row gutter={12} align="middle">
          <Col>
            <MultiCodeSelect
              value={hotelCodes} onChange={setHotelCodes}
              options={hotelOptions(hotels)} placeholder="全部飯店"
            />
          </Col>
          <Col>
            <MultiCodeSelect
              value={platformCodes} onChange={setPlatformCodes}
              options={platformOptions(platforms)} placeholder="全部平台"
            />
          </Col>
          <Col>
            {/* ⚠️ anchor 取資料最後一天，不是今天（CLAUDE.md §8.2） */}
            <StandardRangePicker
              value={range} anchor={dataEnd} onChange={setRange}
              footerNote="基準日為評論資料的最後一天"
            />
          </Col>
          <Col flex="auto" />
          <Col>
            {dataEnd && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                資料最後更新至 {dataEnd}
              </Text>
            )}
          </Col>
          <Col>
            {/* ⚠️ 這段原本是頁面頂端的常駐 Alert（2026-08-23 收進來）。
                它講的是「怎麼讀這一頁」—— 那種說明**看過一次就夠了**，
                每次進來都佔掉三行版面是負擔不是幫助。
                收進 `?` 之後：想知道的人點得到，不想知道的人躲得掉。 */}
            <Tooltip
              placement="bottomRight"
              title={
                <span>
                  <b>這一頁比的是「同一套標準下的不同維度」</b>
                  <br />
                  各館共用一條時間軸、一套主題定義，所以同一個月的兩條線可以直接比。
                  <br />
                  <br />
                  ⚠️ <b>各 OTA 分制不同</b>（Booking／Agoda 10 分制、
                  Tripadvisor／Google 5 分制），這裡一律換算成 10 分制之後才比。
                  <br />
                  <br />
                  ⚠️ <b>則數差距大時不要只看平均</b> ——
                  5 則評論的平均會被單一負評整個拉下來。
                </span>
              }
            >
              <QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} />
            </Tooltip>
          </Col>
        </Row>

        {/* ⭐ 目前統計範圍 —— 截圖出去時對方也看得到 */}
        <Row style={{ marginTop: 8 }}>
          <Col>
            <Space size={6} wrap>
              <Text type="secondary" style={{ fontSize: 12 }}>目前統計範圍：</Text>
              <Tag color={hotelCodes.length ? 'blue' : undefined}>
                <ScopeText codes={hotelCodes} options={hotelOptions(hotels)}
                           allLabel="全部飯店" />
              </Tag>
              <Tag color={platformCodes.length ? 'blue' : undefined}>
                <ScopeText codes={platformCodes} options={platformOptions(platforms)}
                           allLabel="全部平台" />
              </Tag>
              <Tag color={range ? 'blue' : undefined}>{scope.periodLabel}</Tag>
              {scope.isFiltered && (
                <Text style={{ fontSize: 12, color: '#4BA8E8' }}>
                  ← 已套用篩選，下方所有數字都只涵蓋這個範圍
                </Text>
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        <Card
          size="small"
          title={`月度趨勢・各館一條線${scope.titleSuffix}`}
          extra={
            <Space size={16} wrap>
              <Space size={12} wrap>
              {hotelSummary.map((h, i) => (
                <Space key={h.name} size={4}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8, borderRadius: 4,
                    background: SERIES_COLORS[i % SERIES_COLORS.length],
                  }} />
                  <Text style={{ fontSize: 12 }}>{h.name}</Text>
                  <Tooltip title="分數低於 6.0（與 Dashboard 的「負面評論」同條件）">
                    <Tag color={h.neg ? 'error' : 'default'} style={{ marginInlineEnd: 0 }}>
                      負評 {h.neg}
                    </Tag>
                  </Tooltip>
                  <Tooltip title="尚未處理的警示。⚠️ 警示不是負評的子集合，件數比負評多是正常的。">
                    <Tag color={h.alert ? 'warning' : 'default'} style={{ marginInlineEnd: 0 }}>
                      警示 {h.alert}
                    </Tag>
                  </Tooltip>
                </Space>
              ))}
            </Space>
              <Segmented<ChartMode>
                value={mode} onChange={setMode} size="small"
                options={[
                  { value: 'score', label: '平均分' },
                  { value: 'count', label: '評論則數' },
                ]}
              />
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          {rows.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="這個範圍沒有資料" />
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={rows} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis
                  domain={mode === 'score' ? [0, 10] : [0, 'auto']}
                  tick={{ fontSize: 12 }}
                />
                <ReTooltip
                  formatter={(v: number, name: string, entry) => {
                    if (mode === 'count') return [`${v} 則`, name]
                    const count = entry?.payload?.[`${name}__count`]
                    return [`${v?.toFixed(2)}（${count ?? 0} 則）`, name]
                  }}
                />
                <Legend />
                {seriesNames.map((name, i) => (
                  <Line
                    key={name} type="monotone" dataKey={name}
                    stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                    strokeWidth={2} dot={{ r: 3 }}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            ⚠️ 線段中斷代表那個月**沒有評論**，不是分數掉到 0（刻意不接續）。
            {thinMonths.length > 0 && (
              <>
                <br />
                ⚠️ 有 {thinMonths.length} 個月份的樣本少於 {THIN_SAMPLE} 則
                （{thinMonths.slice(0, 4).map((m) => m.review_month).join('、')}
                {thinMonths.length > 4 ? '…' : ''}），
                那幾個點的平均分容易被單一評論帶動，不要拿來下結論。
              </>
            )}
          </Text>
        </Card>

        {/* ⭐ 主題輪動（2026-08-27）。
            放在月度趨勢**正下方**而不是頁尾：看到某個月分數掉下來，
            下一個問題必然是「掉在哪一件事上」，兩張圖要在同一個視線範圍內。 */}
        <div ref={rotationCardRef} className="ota-rotation-fs">
        <Card
          size="small"
          title={`主題輪動・客訴重心怎麼移${scope.titleSuffix}`}
          extra={
            <Space size={12} wrap>
              <Segmented<TopicRotationBasis>
                value={rotationBasis} onChange={setRotationBasis} size="small"
                options={[
                  { value: 'negative', label: '只看負面' },
                  { value: 'all', label: '正負都看' },
                ]}
              />
              <Select
                size="small" value={rotationTopN} onChange={setRotationTopN}
                style={{ width: 110 }}
                options={[
                  { value: 5, label: '前 5 主題' },
                  { value: 10, label: '前 10 主題' },
                  { value: 15, label: '前 15 主題' },
                  { value: 30, label: '全部主題' },
                ]}
              />
              <Tooltip
                placement="bottomRight"
                title={
                  <span>
                    <b>這張圖看的是「重心」，不是「量」</b>
                    <br />
                    每一格是該主題佔那個月全部主題提及的比例。顏色由淡轉深
                    ＝ 那個月大家講的主要就是這件事。
                    <br />
                    <br />
                    ⚠️ <b>橫著看</b>才有意義：同一列的顏色從淡變深，
                    代表這個問題正在變成主要客訴。單看一格看不出輪動。
                    <br />
                    <br />
                    ⚠️ 樣本少的月份整欄會變灰 —— 那幾欄的名次容易被單一評論帶動。
                  </span>
                }
              >
                <QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} />
              </Tooltip>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <TopicRotationHeatmap
            data={rotation} basis={rotationBasis}
            fullscreenRef={rotationCardRef}
          />
        </Card>
        </div>

        <Row gutter={12}>
          <Col span={11}>
            <Card size="small" title={`各平台平均分${hotelCodes.length ? `（${scope.hotelLabel}）` : ''}`}
              style={{ height: '100%' }}>
              {platformStats.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="沒有資料" />
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart
                    data={platformChart}
                    margin={{ top: 8, right: 8, left: -20, bottom: 12 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    {/* 標籤可能兩行（平台 + 飯店），要自訂 tick 才畫得出換行 */}
                    <XAxis
                      dataKey="name" interval={0} height={40}
                      tick={({ x, y, payload }) => (
                        <g transform={`translate(${x},${y})`}>
                          {String(payload.value).split('\n').map((line, i) => (
                            <text
                              key={line} x={0} y={0} dy={14 + i * 13}
                              textAnchor="middle" fontSize={11}
                              fill={i === 0 ? '#333' : '#999'}
                            >
                              {line}
                            </text>
                          ))}
                        </g>
                      )}
                    />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
                    <ReTooltip
                      labelFormatter={(v: string) => String(v).replace('\n', ' · ')}
                      formatter={(v: number, name: string) =>
                        [name === '分數' && v != null ? v.toFixed(2) : v, name]}
                    />
                    <Bar dataKey="分數" fill="#4BA8E8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          <Col span={13}>
            <Card size="small" title={`館別 × 平台交叉表${scope.titleSuffix}`} style={{ height: '100%' }}>
              {compareRows.length === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="沒有資料 —— 至少要有兩個來源才比得出東西"
                />
              ) : (
                <Table<CompareRow>
                  rowKey={(r) => `${r.hotel_code}-${r.platform}`}
                  size="small" pagination={false}
                  dataSource={compareRows} columns={compareColumns}
                />
              )}
              <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
                同一間飯店在不同 OTA 分數落差大，通常不是服務有差，
                而是<b>客群不同</b>（商務 vs 自由行）或<b>該站的評分習慣不同</b>。
                要找可行動的問題，看 Dashboard 的主題分佈比看這張表有用。
              </Paragraph>
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  )
}

export default OtaTrendPage
