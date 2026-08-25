/**
 * OTA 口碑分析 — Dashboard
 * Route: /ota/dashboard    Permission: ota_view
 *
 * 規格書：`docs/SPEC_ota_reviews.md` §9（P5）
 *
 * 【這一頁在回答的四個問題】
 *   ① 整體評價現在如何、跟上個月比是升是降
 *   ② 客人最常抱怨什麼（主題分佈，負面優先）
 *   ③ 哪一個 OTA 的分數特別低（平台對照）
 *   ④ 有沒有待處理的負評警示
 *
 * ⚠️ 期間篩選一律用 `StandardRangePicker`，`anchor` 取**評論資料的最後一天**
 *    而不是 `dayjs()`（CLAUDE.md §8.2）。OTA 評論本來就落後現實好幾天 ——
 *    客人退房後才留言、爬蟲每日才跑一次。以今天為基準的「本月」會選到
 *    一片還沒有資料的日子，使用者會誤判成資料缺漏。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Card, Col, Empty, Progress, Row, Select, Space, Spin, Statistic,
  Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  ArrowDownOutlined, ArrowUpOutlined, MinusOutlined, QuestionCircleOutlined,
  RightOutlined, WarningOutlined,
} from '@ant-design/icons'
import type { CardProps } from 'antd'
import type { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip as ReTooltip, XAxis, YAxis,
} from 'recharts'

import { useNavigate } from 'react-router-dom'

import StandardRangePicker from '@/components/StandardRangePicker'
import { MultiCodeSelect, ScopeText, describeCodes, hotelOptions, toParam }
  from '../filterScope'
import { buildFilterQuery } from '@/hooks/useUrlFilterDefaults'
import { useAuthStore } from '@/stores/authStore'
import {
  fetchDataRange, fetchHotelOptions, fetchMonthly, fetchOverview,
  fetchPlatformStats, fetchTopicStats,
} from '@/api/ota'
import type {
  HotelOption, MonthlyPoint, OtaOverview, PlatformStat, TopicStat,
} from '@/types/ota'

const { Text, Paragraph } = Typography

// 折線圖的顏色。⚠️ 品牌色（CLAUDE.md 受保護元素），不要改。
const LINE_COLORS = ['#1B3A5C', '#4BA8E8', '#52c41a', '#faad14', '#eb2f96']

// ⚠️ 與後端 `ota_normalize.NEGATIVE_SCORE_MAX` 對應。
//    Dashboard 的「負面評論」KPI 是 `score_10 < 6.0`，下鑽時要帶同一個值，
//    否則清單的筆數會跟卡片上的數字對不起來。
const NEGATIVE_SCORE_MAX = 6.0

const OtaDashboardPage: React.FC = () => {
  const navigate = useNavigate()
  const hasPermission = useAuthStore((st) => st.hasPermission)

  const [hotels, setHotels] = useState<HotelOption[]>([])
  // ⚠️ 2026-08-25 改成多選：空陣列 ＝ 全部（與後端 split_codes('') 語意一致）
  const [hotelCodes, setHotelCodes] = useState<string[]>([])
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [dataEnd, setDataEnd] = useState('')

  const [overview, setOverview] = useState<OtaOverview | null>(null)
  const [monthly, setMonthly] = useState<MonthlyPoint[]>([])
  const [platformStats, setPlatformStats] = useState<PlatformStat[]>([])
  const [topics, setTopics] = useState<TopicStat[]>([])
  const [loading, setLoading] = useState(false)

  const filters = useMemo(() => ({
    hotel_code: toParam(hotelCodes),
    // ⚠️ range 為 null 代表「全部」（StandardRangePicker §8.3 的語意），
    //    這時**不帶** start/end，由後端套用完整資料範圍。
    ...(range
      ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') }
      : {}),
  }), [hotelCodes, range])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [rangeInfo, ov, mon, plat, top] = await Promise.all([
        fetchDataRange(toParam(hotelCodes) || ''),
        fetchOverview(filters),
        fetchMonthly(filters),
        fetchPlatformStats(filters),
        fetchTopicStats(filters),
      ])
      setDataEnd(rangeInfo.end)
      setOverview(ov)
      setMonthly(mon)
      setPlatformStats(plat)
      setTopics(top)
    } catch {
      message.error('載入統計失敗')
    } finally {
      setLoading(false)
    }
  }, [hotelCodes, filters])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    fetchHotelOptions().then(setHotels).catch(() => undefined)
  }, [])

  /**
   * 把 `[{月, 飯店, 分數}]` 轉成 recharts 要的寬表 `[{月, 飯店A: 分, 飯店B: 分}]`。
   *
   * ⚠️ 這是「雙館比較」的核心 —— **全集團共用一套時間軸**，
   *    不是每間飯店各畫一張圖再併排。各館各畫的話 X 軸不對齊，
   *    根本看不出「同一個月哪一館比較好」。
   */
  const { trendRows, hotelNames } = useMemo(() => {
    const names = [...new Set(monthly.map((m) => m.hotel_name || m.hotel_code))]
    const byMonth = new Map<string, Record<string, string | number | null>>()
    monthly.forEach((m) => {
      const row = byMonth.get(m.review_month) ?? { month: m.review_month }
      row[m.hotel_name || m.hotel_code] = m.avg_score_10
      // 筆數放進來給 tooltip 用 —— 只有 2 則評論的月份不該跟 200 則等重看待
      row[`${m.hotel_name || m.hotel_code}__count`] = m.count
      byMonth.set(m.review_month, row)
    })
    return {
      trendRows: [...byMonth.values()].sort(
        (a, b) => String(a.month).localeCompare(String(b.month))),
      hotelNames: names,
    }
  }, [monthly])

  /**
   * ⭐ 各平台長條圖的資料（2026-08-23 修）。
   *
   * ⚠️ **後端 `/stats/platform` 是 `group_by(platform, hotel_code)`** ——
   *    回的是「平台 × 飯店」的交叉，不是單純的平台清單。
   *
   *    初版只拿 `platform_label` 當 X 軸名稱，於是兩間飯店變成
   *    **兩根一模一樣叫「Agoda」的長條**，誰是誰完全看不出來。
   *    那不是「標籤不夠清楚」，是那張圖讀不出任何東西。
   *
   * ⚠️ 只有**真的有多間飯店**時才把飯店名加進標籤 ——
   *    篩選了單一飯店的時候每根都掛同一個名字，只是變吵。
   */
  const platformChart = useMemo(() => {
    const codes = new Set(platformStats.map((p) => p.hotel_code).filter(Boolean))
    const needHotel = codes.size > 1
    return platformStats.map((p) => {
      const hotelName = hotels.find((h) => h.value === p.hotel_code)?.label
        || p.hotel_code
      return {
        name: needHotel ? `${p.platform_label}\n${hotelName}` : p.platform_label,
        分數: p.avg_score_10,
        則數: p.count,
      }
    })
  }, [platformStats, hotels])

  /**
   * 目前的篩選條件，給 context bar 與卡片標題共用。
   *
   * ⚠️ 選了特定飯店時**畫面上必須看得出來** —— 不然有人截圖給別人，
   *    對方會把單館的數字當成全集團的。這比「看不懂」更危險：
   *    **看懂了但看錯對象**。
   */
  const scope = useMemo(() => {
    const hotelLabel = describeCodes(hotelCodes, hotelOptions(hotels), '全部飯店')
    const periodLabel = range
      ? `${range[0].format('YYYY-MM-DD')} ~ ${range[1].format('YYYY-MM-DD')}`
      : '全部期間'
    return {
      hotelLabel,
      periodLabel,
      isFiltered: hotelCodes.length > 0 || Boolean(range),
      // 卡片標題用的短版，例如「（瀚寓）」；全部飯店時不加，免得每張卡都掛一句廢話
      titleSuffix: hotelCodes.length ? `（${hotelLabel}）` : '',
    }
  }, [hotelCodes, hotels, range])


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

  /**
   * ⭐ KPI 下鑽（2026-08-23）。
   *
   * ⚠️ **數字必須一致才能連過去**。這是先前刻意延後這個功能的原因 ——
   *    Dashboard 的「負面評論」看分數、清單的「情緒」看 `sentiment_label`，
   *    兩套定義並存的時候點「24 則」可能看到 31 則，
   *    **比不能點還糟**：使用者會同時不信任這兩個數字。
   *    現在清單有了 `low_score_only`（與 KPI 同一個門檻），才安全。
   *
   * ⚠️ **沒有權限的卡片直接不可點**，而不是點了才撞權限牆。
   *    給一個點得下去卻走不通的入口，比沒有入口更惱人。
   */
  const drill = useMemo(() => {
    const base = { hotelCodes, range }
    return {
      reviews: hasPermission('ota_reviews_view')
        ? `/ota/reviews${buildFilterQuery(base)}` : '',
      // ⚠️ 門檻與後端的 `NEGATIVE_SCORE_MAX` 必須一致，否則點過去的筆數
      //    會跟卡片上的數字對不起來。前端沒有那個常數，所以在這裡寫明
      //    並註記來源 —— 後端改了這裡要跟著改。
      lowScore: hasPermission('ota_reviews_view')
        ? `/ota/reviews${buildFilterQuery({ ...base, scoreBelow: NEGATIVE_SCORE_MAX })}` : '',
      alerts: hasPermission('ota_alerts_view')
        ? `/ota/alerts${buildFilterQuery({ ...base, alertStatus: 'open' })}` : '',
    }
  }, [hotelCodes, range, hasPermission])

  /**
   * 可點的卡片給游標與 hover 提示；不可點的維持原樣。
   *
   * ⚠️ 回傳型別**寫明**成 `Partial<CardProps>` —— 讓它自己推導的話會得到
   *    `{hoverable, style, onClick} | {}` 這種聯集，展開進 JSX 時 TS 會抱怨
   *    「屬性不存在於其中一個成員」。
   */
  const clickable = (to: string): Partial<CardProps> => (to ? {
    hoverable: true,
    style: { cursor: 'pointer' },
    onClick: () => navigate(to),
  } : {})

  const momDelta = useMemo(() => {
    if (!overview?.this_month_avg || !overview?.last_month_avg) return null
    return overview.this_month_avg - overview.last_month_avg
  }, [overview])

  const topicRows = useMemo(
    () => [...topics].sort((a, b) => b.negative_count - a.negative_count),
    [topics],
  )
  const maxTopicCount = topicRows[0]?.total_count || 1

  const hasData = (overview?.total ?? 0) > 0

  return (
    <div>
      {/* ⚠️ 有篩選時整條換底色 + 左邊一道粗邊 —— 這是給「掃過去」的眼睛看的。
          只把條件寫成一行小字，掃視的人不會停下來讀。 */}
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
            {/* ⚠️ 不放「全部飯店」這個選項 —— 多選模式下它會變成
                 「可以跟其他飯店一起被選中」的怪東西。空陣列就是全部，
                 placeholder 講清楚即可。 */}
            <MultiCodeSelect
              value={hotelCodes} onChange={setHotelCodes}
              options={hotelOptions(hotels)} placeholder="全部飯店"
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
        </Row>

        {/* ⭐ 目前統計範圍 —— 截圖出去時對方也看得到這一行 */}
        <Row style={{ marginTop: 8 }}>
          <Col>
            <Space size={6} wrap>
              <Text type="secondary" style={{ fontSize: 12 }}>目前統計範圍：</Text>
              <Tag color={hotelCodes.length ? 'blue' : undefined}>
              <ScopeText codes={hotelCodes} options={hotelOptions(hotels)}
                         allLabel="全部飯店" />
            </Tag>
              <Tag color={range ? 'blue' : undefined}>{scope.periodLabel}</Tag>
              <Tag>{(overview?.total ?? 0).toLocaleString()} 則</Tag>
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
        {!hasData && !loading && (
          <Alert
            type="info" showIcon style={{ marginBottom: 16 }}
            message="這個範圍還沒有評論資料"
            description="到「來源設定」按立即同步，或用 CSV／HTML 匯入。若剛同步完，記得到「主題字典」按一次「重新分析全部」。"
          />
        )}

        {/* 可點的卡片要讓人知道它可點 —— 只有 hover 才發現的入口等於沒有 */}
        {(drill.reviews || drill.alerts) && (
          <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
            💡 點卡片可帶著目前的篩選條件跳到明細
          </Text>
        )}
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small" {...clickable(drill.reviews)}>
              <Statistic
                title={
                  <Space size={4}>
                    <span>評論總數</span>
                    {drill.reviews && <RightOutlined style={{ color: '#bbb', fontSize: 10 }} />}
                  </Space>
                }
                value={overview?.total ?? 0} suffix="則"
              />
            </Card>
          </Col>
          <Col span={6}>
            {/* ⚠️ 這張卡**刻意不做成可點的**（2026-08-23）。
                其他三張的語意是「看這些筆資料」，平均分數沒有對應的一群評論 ——
                硬連到趨勢頁的話點擊行為不一致，使用者猜不到會跳去哪。
                四張都可點看起來整齊，但那是為了整齊犧牲可預期性。 */}
            <Card size="small">
              <Statistic
                title="平均分數"
                value={overview?.avg_score_10 ?? 0}
                precision={2} suffix="/ 10"
                valueStyle={{
                  color: (overview?.avg_score_10 ?? 0) >= 8 ? '#52c41a'
                    : (overview?.avg_score_10 ?? 0) >= 6 ? '#faad14' : '#cf1322',
                }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" {...clickable(drill.lowScore)}>
              <Statistic
                title={
                  <Space size={4}>
                    <span>負面評論</span>
                    {drill.lowScore && <RightOutlined style={{ color: '#bbb', fontSize: 10 }} />}
                    <Tooltip title="分數低於 6.0 的評論。與下方「待處理警示」是兩套不同的判定，數量不會一致。">
                      <QuestionCircleOutlined style={{ color: '#bbb', fontSize: 12 }} />
                    </Tooltip>
                  </Space>
                }
                value={overview?.negative_count ?? 0} suffix="則"
                valueStyle={{ color: (overview?.negative_count ?? 0) ? '#cf1322' : undefined }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" {...clickable(drill.alerts)}>
              {/* ⚠️ 警示常常**比負評多**（實測 42 vs 24），看起來像算錯。
                  原因是 compute_alert 有三條獨立的路，警示不是負評的子集合。
                  沒有這個說明的話，使用者會開始懷疑整組數字。 */}
              <Statistic
                title={
                  <Space size={4}>
                    <span>待處理警示</span>
                    {drill.alerts && <RightOutlined style={{ color: '#bbb', fontSize: 10 }} />}
                    <Tooltip
                      title={
                        <span>
                          符合以下**任一條**且尚未處理的評論：
                          <br />① 分數低於 6.0
                          <br />② 判定為負面，且提到清潔／服務／設備
                          <br />③ 負評欄超過 100 字
                          <br />
                          <br />⚠️ 所以警示<b>不是</b>負面評論的子集合，
                          件數比負面評論多是正常的。
                        </span>
                      }
                    >
                      <QuestionCircleOutlined style={{ color: '#bbb', fontSize: 12 }} />
                    </Tooltip>
                  </Space>
                }
                value={overview?.alert_open_count ?? 0} suffix="件"
                prefix={(overview?.alert_open_count ?? 0) ? <WarningOutlined /> : undefined}
                valueStyle={{ color: (overview?.alert_open_count ?? 0) ? '#cf1322' : undefined }}
              />
            </Card>
          </Col>
        </Row>

        {/* ⚠️ 這裡原本有一則「警示比負評多是正常的」的常駐 Alert，
            2026-08-23 移除 —— **兩張卡的 tooltip 已經講過同一件事了**。
            警示幾乎永遠比負評多，所以那則橫幅實際上是每次都出現，
            變成一條沒有人會再讀的固定文字，還把主要內容往下擠。

            一次性的說明放 tooltip（想知道的人點得到），
            不要放常駐橫幅（不想知道的人躲不掉）。 */}
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <Card
              size="small"
              title={`本月 vs 上月${scope.titleSuffix}`}
              extra={
                <Tooltip title="以「評論資料的最後一天」所在月份為準，不是今天。OTA 評論落後現實好幾天，用今天判定會把還沒過完的月份跟完整月份相比。">
                  <Text type="secondary" style={{ fontSize: 12 }}>基準說明</Text>
                </Tooltip>
              }
            >
              <Row gutter={16}>
                <Col span={8}>
                  <Statistic
                    title="本月則數" value={overview?.this_month_count ?? 0}
                    suffix={<Text type="secondary" style={{ fontSize: 12 }}>
                      （上月 {overview?.last_month_count ?? 0}）
                    </Text>}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="本月平均" value={overview?.this_month_avg ?? 0} precision={2}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="與上月相比"
                    value={momDelta === null ? '—' : Math.abs(momDelta)}
                    precision={momDelta === null ? undefined : 2}
                    prefix={
                      momDelta === null ? <MinusOutlined />
                        : momDelta > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />
                    }
                    valueStyle={{
                      color: momDelta === null ? undefined
                        : momDelta > 0 ? '#52c41a' : momDelta < 0 ? '#cf1322' : undefined,
                    }}
                  />
                </Col>
              </Row>
              {/* ⚠️ 樣本太少的月份不要拿來下結論 */}
              {(overview?.this_month_count ?? 0) > 0
                && (overview?.this_month_count ?? 0) < 10 && (
                <Text type="warning" style={{ fontSize: 12 }}>
                  ⚠️ 本月只有 {overview?.this_month_count} 則，平均分容易被單一評論帶動
                </Text>
              )}
            </Card>
          </Col>

          <Col span={12}>
            <Card size="small" title={`各 OTA 平均分對照${scope.titleSuffix}`}>
              {platformStats.length === 0 ? (
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="沒有資料" />
              ) : (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={platformChart}
                    margin={{ top: 8, right: 8, left: -20, bottom: 12 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    {/* 標籤可能是兩行（平台 + 飯店），要自訂 tick 才畫得出換行 */}
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
              <Text type="secondary" style={{ fontSize: 12 }}>
                ⚠️ 各站分制不同，這裡比的是**換算成 10 分制之後**的分數。
                則數差距大時不要直接比平均 —— 滑鼠移上去看則數。
              </Text>
            </Card>
          </Col>
        </Row>

        <Card
          size="small"
          title={`月度分數趨勢${scope.titleSuffix}`}
          extra={<Space size={12} wrap>
              {hotelSummary.map((h, i) => (
                <Space key={h.name} size={4}>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8, borderRadius: 4,
                    background: LINE_COLORS[i % LINE_COLORS.length],
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
            </Space>}
          style={{ marginBottom: 16 }}
        >
          {trendRows.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="沒有資料" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trendRows} margin={{ top: 8, right: 16, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
                <ReTooltip
                  formatter={(v: number, name: string, entry) => {
                    const count = entry?.payload?.[`${name}__count`]
                    return [`${v?.toFixed(2)}（${count ?? 0} 則）`, name]
                  }}
                />
                <Legend />
                {hotelNames.map((name, i) => (
                  <Line
                    key={name} type="monotone" dataKey={name}
                    stroke={LINE_COLORS[i % LINE_COLORS.length]}
                    strokeWidth={2} dot={{ r: 3 }}
                    connectNulls={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            ⚠️ 線段中斷代表那個月沒有評論，**不是分數掉到 0** ——
            所以刻意不接續（`connectNulls=false`）。
          </Text>
        </Card>

        <Card size="small" title={`主題分佈・依負面提及排序${scope.titleSuffix}`}>
          {topicRows.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="還沒有主題標籤 —— 到「主題字典」按「重新分析全部」"
            />
          ) : (
            <Table<TopicStat>
              rowKey="topic" size="small" pagination={false} dataSource={topicRows}
              columns={[
                { title: '主題', dataIndex: 'topic', width: 110,
                  render: (v: string) => <b>{v}</b> },
                {
                  title: '負面', dataIndex: 'negative_count', width: 90,
                  sorter: (a, b) => a.negative_count - b.negative_count,
                  render: (v: number) => (v
                    ? <Tag color="error">{v} 則</Tag>
                    : <Text type="secondary">—</Text>),
                },
                {
                  title: '正面', dataIndex: 'positive_count', width: 90,
                  render: (v: number) => (v
                    ? <Tag color="success">{v} 則</Tag>
                    : <Text type="secondary">—</Text>),
                },
                {
                  title: '提及比重', dataIndex: 'total_count',
                  render: (v: number, row) => (
                    <Space size={8} style={{ width: '100%' }}>
                      <Progress
                        percent={Math.round((v / maxTopicCount) * 100)}
                        showInfo={false} size="small"
                        strokeColor={row.negative_count > row.positive_count
                          ? '#cf1322' : '#4BA8E8'}
                        style={{ width: 220 }}
                      />
                      <Text type="secondary">{v} 則</Text>
                    </Space>
                  ),
                },
              ]}
            />
          )}
          <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
            ⚠️ 一則評論可以同時屬於多個主題，所以各主題則數加總會**大於**評論總數。
            <br />
            ⚠️ 主題來自關鍵詞字典，**沒有關鍵詞就抓不到** ——
            看到某個主題是 0 則，先確認字典裡有沒有對應的詞，不要直接當成「客人沒抱怨」。
          </Paragraph>
        </Card>
      </Spin>
    </div>
  )
}

export default OtaDashboardPage
