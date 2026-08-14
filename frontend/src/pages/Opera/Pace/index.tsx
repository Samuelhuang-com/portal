/**
 * 營運分析 — 訂房 Pace／Pickup（/opera/pace）
 *
 * ⚠️ **本頁的歷史進度是「回推」出來的，這是理解所有數字的前提：**
 *    訂房同步（`opera_reservation_sync._upsert`）是整列覆寫、**無版本**，
 *    所以我們只有「每筆訂房**現在**長什麼樣」。本頁用 booking_date /
 *    cancellation_date 把現況往回切，**已含後續改期與取消的結果**。
 *    頂端那則說明由後端 `source.population` 帶出，前端不寫死，**不要拿掉**。
 *
 * ⚠️ 與「訂房分析」的差別：那邊看訂單「現在」長什麼樣，這邊多一個
 *    `as_of`（觀察時點）維度。兩邊的「在手訂房」在 as_of=今天 時應完全一致。
 *
 * ⚠️ 期間選擇器**刻意不用** StandardRangePicker —— 本頁是**未來導向**
 *    （看未來入住日的訂房進度），「本月／上月／去年」方向相反（CLAUDE.md §8.4）。
 *
 * ⚠️ 圖表一律用 recharts，**不引入 ECharts**（docs/SPEC_dynamic_visualization.md
 *    2026-08-08 決策：維持單一圖表庫，避免全站樣式分裂）。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Card, Col, DatePicker, Descriptions, Drawer, Empty, Popover, Radio,
  Row, Space, Spin, Statistic, Table, Tabs, Tag, Tooltip, Typography,
} from 'antd'
import { QuestionCircleOutlined, RiseOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis,
} from 'recharts'

import {
  fetchOtbMatrix, fetchPaceCurve, fetchPaceDataRange, fetchPaceDayDetail,
  fetchPacePickup, fetchPacePickupDimension,
} from '@/api/operaPace'
import type {
  CompareMode, CurveResult, DayDetailResult, OtbMatrixResult, OtbRow,
  PaceDataRange, PaceDimension, PickupDimensionResult, PickupResult, PickupRow,
} from '@/api/operaPace'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct, fmtYoY, shortDate, trendColor,
} from '@/pages/Opera/components/formatters'

const { Title, Text, Paragraph } = Typography
const { RangePicker } = DatePicker

const DIM_LABELS: Record<PaceDimension, string> = {
  market_code: '市場區隔', room_type: '房型', channel: '通路',
  rate_code: 'Rate Code', source_code: '來源',
}

const WINDOWS = [1, 3, 7, 14]
const WEEKDAY = ['一', '二', '三', '四', '五', '六', '日']

/** OTB 矩陣的熱圖底色。⚠️ null（觀察日還沒到）不上色，與 0 明確區分。 */
function heatStyle(v: number | null, max: number): React.CSSProperties {
  if (v === null || v === undefined) return { background: '#fafafa', color: '#bfbfbf' }
  if (!max) return {}
  const r = Math.min(v / max, 1)
  return { background: `rgba(75, 168, 232, ${(r * 0.55).toFixed(3)})` }
}

const OperaPacePage: React.FC = () => {
  // 入住日區間（未來導向）：預設今天 ～ 今天 + 90 天
  const [range, setRange] = useState<[Dayjs, Dayjs]>(
    [dayjs(), dayjs().add(90, 'day')])
  const [asOf, setAsOf] = useState<Dayjs>(dayjs())
  const [compare, setCompare] = useState<CompareMode>('weekday')
  const [win, setWin] = useState(7)
  const [dimension, setDimension] = useState<PaceDimension>('market_code')
  const [curveDate, setCurveDate] = useState<Dayjs>(dayjs().add(14, 'day'))

  const [meta, setMeta] = useState<PaceDataRange | null>(null)
  const [matrix, setMatrix] = useState<OtbMatrixResult | null>(null)
  const [curve, setCurve] = useState<CurveResult | null>(null)
  const [pickup, setPickup] = useState<PickupResult | null>(null)
  const [dim, setDim] = useState<PickupDimensionResult | null>(null)
  const [detail, setDetail] = useState<DayDetailResult | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [curveLoading, setCurveLoading] = useState(false)
  const [error, setError] = useState('')

  const params = useMemo(() => ({
    start: range[0].format('YYYY-MM-DD'),
    end: range[1].format('YYYY-MM-DD'),
    as_of: asOf.format('YYYY-MM-DD'),
  }), [range, asOf])

  useEffect(() => { fetchPaceDataRange().then(setMeta).catch(() => {}) }, [])

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [m, p, d] = await Promise.all([
        // ⚠️ 一定要帶 as_of 與 window，否則 pickup 欄會固定以「今天」計算，
        //    看歷史區間時永遠是 0（2026-08-13 runtime 測試發現）
        fetchOtbMatrix({ start: params.start, end: params.end, compare,
                         as_of: params.as_of, window: win }),
        fetchPacePickup({ ...params, window: win }),
        fetchPacePickupDimension({ ...params, dimension, window: win }),
      ])
      setMatrix(m); setPickup(p); setDim(d)
    } catch (err: any) {
      setError(err?.response?.data?.detail || '載入失敗')
    } finally { setLoading(false) }
  }, [params, compare, win, dimension])

  const loadCurve = useCallback(async () => {
    setCurveLoading(true)
    try {
      setCurve(await fetchPaceCurve({
        stay_date: curveDate.format('YYYY-MM-DD'), compare,
      }))
    } catch { setCurve(null) } finally { setCurveLoading(false) }
  }, [curveDate, compare])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadCurve() }, [loadCurve])

  const openDetail = useCallback(async (stayDate: string) => {
    setDrawerOpen(true); setDetail(null)
    try {
      setDetail(await fetchPaceDayDetail({
        stay_date: stayDate, window: win, as_of: params.as_of,
      }))
    } catch { setDetail(null) }
  }, [win, params.as_of])

  const maxOtb = useMemo(() => {
    if (!matrix) return 0
    let m = 0
    matrix.rows.forEach((r: OtbRow) => Object.values(r.otb).forEach((v) => {
      if (v !== null && v > m) m = v
    }))
    return m
  }, [matrix])

  // ── ① OTB 矩陣 ────────────────────────────────────────────────────────────
  const matrixCols: ColumnsType<OtbRow> = useMemo(() => {
    const leads = matrix?.leads || []
    return [
      {
        title: '入住日', dataIndex: 'stay_date', fixed: 'left', width: 118,
        render: (v: string, r) => (
          <Space size={4}>
            <span style={{ fontWeight: r.is_weekend ? 600 : 400 }}>{shortDate(v)}</span>
            <Tag color={r.is_weekend ? 'orange' : 'default'}>週{WEEKDAY[r.weekday]}</Tag>
          </Space>
        ),
      },
      ...leads.map((lead) => ({
        title: lead === 0 ? '當日' : `前 ${lead} 天`,
        dataIndex: ['otb', String(lead)],
        align: 'right' as const, width: 88,
        onCell: (r: OtbRow) => ({ style: heatStyle(r.otb[String(lead)], maxOtb) }),
        render: (v: number | null) =>
          // ⚠️ 觀察日還沒到 → 顯示 —，不是 0
          v === null || v === undefined ? EMPTY : fmtInt(v),
      })),
      {
        title: '目前在手', dataIndex: 'room_nights', align: 'right', width: 96,
        render: (v: number) => <b>{fmtInt(v)}</b>,
      },
      {
        title: '去年同提前期', dataIndex: 'ly_room_nights', align: 'right', width: 118,
        render: (v: number) => <span style={{ color: GREY }}>{fmtInt(v)}</span>,
      },
      {
        title: 'vs 去年', dataIndex: 'vs_ly', align: 'right', width: 96,
        render: (v: number | null) => (
          <span style={{ color: trendColor(v) }}>{fmtYoY(v)}</span>
        ),
      },
      {
        title: `${win} 日淨 Pickup`, dataIndex: 'pickup_net', align: 'right', width: 118,
        render: (v: number, r) => (
          <Tooltip title={`新增 ${fmtInt(r.pickup_new)}、取消 ${fmtInt(r.pickup_cancels)}`}>
            <span style={{ color: trendColor(v) }}>
              {v > 0 ? `+${fmtInt(v)}` : fmtInt(v)}
            </span>
          </Tooltip>
        ),
      },
    ]
  }, [matrix, maxOtb, win])

  // ── ③ Pickup ──────────────────────────────────────────────────────────────
  const pickupCols: ColumnsType<PickupRow> = [
    {
      title: '入住日', dataIndex: 'stay_date', width: 118,
      render: (v: string, r) => (
        // ⚠️ 飯店口徑的假日是週五、六，不含週日（後端 is_weekend 同一套判定）
        <Space size={4}>
          <span>{shortDate(v)}</span>
          <Tag color={r.weekday === 4 || r.weekday === 5 ? 'orange' : 'default'}>
            週{WEEKDAY[r.weekday]}
          </Tag>
        </Space>
      ),
    },
    {
      title: '新增', dataIndex: 'gross_new', align: 'right', width: 90,
      render: (v: number) => <span style={{ color: GREEN }}>+{fmtInt(v)}</span>,
    },
    {
      title: '取消', dataIndex: 'cancels', align: 'right', width: 90,
      render: (v: number) => (
        <span style={{ color: v ? RED : undefined }}>{v ? `−${fmtInt(v)}` : EMPTY}</span>
      ),
    },
    {
      title: '淨 Pickup', dataIndex: 'net', align: 'right', width: 106,
      render: (v: number) => (
        <b style={{ color: trendColor(v) }}>{v > 0 ? `+${fmtInt(v)}` : fmtInt(v)}</b>
      ),
    },
    { title: '期初在手', dataIndex: 'otb_before', align: 'right', width: 98,
      render: (v: number) => fmtInt(v) },
    { title: '期末在手', dataIndex: 'otb_after', align: 'right', width: 98,
      render: (v: number) => fmtInt(v) },
    {
      title: '檢核', dataIndex: 'verified', align: 'center', width: 76,
      render: (v: boolean) => (
        <Tooltip title="期末在手 − 期初在手 應等於淨 Pickup。不符代表回推邏輯有誤。">
          <Tag color={v ? 'success' : 'error'}>{v ? '通過' : '異常'}</Tag>
        </Tooltip>
      ),
    },
  ]

  const pickupChart = useMemo(() => (pickup?.rows || []).map((r) => ({
    date: shortDate(r.stay_date),
    新增: r.gross_new,
    取消: -r.cancels,
    淨: r.net,
  })), [pickup])

  const curveChart = useMemo(() => (curve?.points || []).map((p) => ({
    lead: p.lead_days,
    今年: p.room_nights,
    去年同期: p.ly_room_nights,
  })), [curve])

  const readiness = meta?.snapshot

  // ⚠️ 2026-08-13 runtime 測試發現：DB 內可能完全沒有「今天以後」的訂房
  //    （回補未跑完、增量同步沒排），一進頁全是 0 會被當成系統壞掉。
  //    **刻意不自動改預設區間** —— 本頁是未來導向，把預設偷偷換成歷史區間
  //    會掩蓋「資料不完整」這件事。改為明講，讓使用者自己決定要不要往回看。
  const dataLag = useMemo(() => {
    if (!meta?.has_data || !meta.end) return null
    const end = dayjs(meta.end)
    return end.isBefore(dayjs(), 'day') ? end : null
  }, [meta])

  return (
    <div>
      <Title level={4} style={{ marginBottom: 4 }}>
        <RiseOutlined style={{ color: BRAND, marginRight: 8 }} />
        訂房 Pace／Pickup
        {/* ⚠️ 回推失真聲明 —— 規格 §八 要求必須在畫面上看得到，內容由後端
            `source.population` / `source.precision` 帶出，前端不寫死。
            2026-08-13 依使用者要求從頁首 Alert 改為這顆「?」的 Popover：
            **可以收起來，但不可以拿掉**。 */}
        <Popover
          placement="bottomLeft"
          trigger={['click', 'hover']}
          title="這一頁的歷史進度是以訂房日回推得出"
          content={
            <div style={{ maxWidth: 520 }}>
              <div>{matrix?.source.population}</div>
              <div style={{ marginTop: 6 }}>{matrix?.source.precision}</div>
              {!!matrix?.unresolved_cancels && (
                <div style={{ marginTop: 6, color: ORANGE }}>
                  有 {fmtInt(matrix.unresolved_cancels)} 筆訂單狀態為取消但沒有取消日期，
                  無法定位時點，已從所有觀察點排除。
                </div>
              )}
              {/* ⚠️ 2026-08-13 實測：這是本頁與「訂房分析」數字對不起來的唯一原因，
                  不顯示的話使用者會找不到差異來源（實測 2024-09 那段差 10 房晚）。 */}
              {!!matrix?.missing_booking_date && (
                <div style={{ marginTop: 6, color: ORANGE }}>
                  有 {fmtInt(matrix.missing_booking_date)} 筆房晚<b>沒有訂房日</b>，
                  無法回推已排除 —— 這會讓本頁的「目前在手」比「訂房分析」
                  少這些數量，屬正常。
                </div>
              )}
            </div>
          }
        >
          <QuestionCircleOutlined
            style={{ color: ACCENT, fontSize: 16, marginLeft: 8, cursor: 'pointer' }}
          />
        </Popover>
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        未來每一天目前訂到什麼程度、最近幾天多訂了多少、跟去年同一個提前期比是快還是慢。
      </Paragraph>

      {/* ⚠️ 資料落後今天 —— 一定要明講，否則整頁 0 會被當成系統壞掉 */}
      {dataLag && (
        <Alert
          type="error" showIcon style={{ marginBottom: 12 }}
          message={`訂房資料只到 ${dataLag.format('YYYY-MM-DD')}，沒有今天以後的資料`}
          description={
            <>
              <div>
                本頁預設看「今天起 90 天」的訂房進度，但資料同步尚未跟上，
                所以表格會全部是 0 —— <b>這不是系統故障，是資料還沒進來。</b>
              </div>
              <div style={{ marginTop: 4 }}>
                請到「訂房分析」頁按「補下一段」完成歷史回補，
                並確認每日增量同步有在執行（同步工具的「訂房增量同步」）。
                想先看已有資料的區間，把上方「入住日區間」往回調即可。
              </div>
            </>
          }
        />
      )}

      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}

      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap size={16}>
          <Space size={6}>
            <Text type="secondary">入住日區間</Text>
            {/* ⚠️ 未來導向，刻意用原生 RangePicker（CLAUDE.md §8.4） */}
            <RangePicker
              value={range} allowClear={false}
              onChange={(v) => v && v[0] && v[1] && setRange([v[0], v[1]])}
            />
          </Space>
          <Space size={6}>
            <Tooltip title="以哪一天的眼光回看。預設今天。">
              <Text type="secondary">觀察日</Text>
            </Tooltip>
            <DatePicker
              value={asOf} allowClear={false}
              disabledDate={(d) => d && d > dayjs().endOf('day')}
              onChange={(v) => v && setAsOf(v)}
            />
          </Space>
          <Space size={6}>
            <Text type="secondary">Pickup 觀察窗</Text>
            <Radio.Group size="small" value={win} onChange={(e) => setWin(e.target.value)}>
              {WINDOWS.map((w) => (
                <Radio.Button key={w} value={w}>{w} 日</Radio.Button>
              ))}
            </Radio.Group>
          </Space>
          <Space size={6}>
            <Tooltip title="飯店需求跟著星期走，8/15 週六對去年 8/15 週四沒有可比性，所以預設同星期對齊。做固定日期的節慶比較時才選同日期。">
              <Text type="secondary">去年對齊</Text>
            </Tooltip>
            <Radio.Group size="small" value={compare}
                         onChange={(e) => setCompare(e.target.value)}>
              <Radio.Button value="weekday">同星期</Radio.Button>
              <Radio.Button value="date">同日期</Radio.Button>
            </Radio.Group>
          </Space>
        </Space>
      </Card>

      {matrix && (
        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="期間在手房晚" value={matrix.summary.room_nights}
                         valueStyle={{ color: BRAND }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="去年同提前期" value={matrix.summary.ly_room_nights}
                         valueStyle={{ color: GREY }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title={`${win} 日淨 Pickup`} value={pickup?.summary?.net ?? 0}
                prefix={(pickup?.summary.net ?? 0) > 0 ? '+' : ''}
                valueStyle={{ color: trendColor(pickup?.summary.net ?? 0) }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="新增 / 取消"
                value={`${fmtInt(pickup?.summary.gross_new)} / ${fmtInt(pickup?.summary.cancels)}`}
                valueStyle={{ fontSize: 20 }} />
            </Card>
          </Col>
        </Row>
      )}

      {pickup && !pickup.verify.all_passed && (
        <Alert
          type="error" showIcon style={{ marginBottom: 12 }}
          message="恆等式檢核未通過"
          description={
            <>
              <div>期末在手 − 期初在手 應等於淨 Pickup，以下日期不符，請回報：</div>
              <ul style={{ margin: '6px 0 0 18px' }}>
                {pickup.verify.warnings.map((w) => <li key={w}>{w}</li>)}
              </ul>
            </>
          }
        />
      )}

      <Spin spinning={loading}>
        <Tabs
          defaultActiveKey="matrix"
          items={[
            {
              key: 'matrix',
              label: '訂房進度總表',
              children: matrix ? (
                <Card size="small">
                  <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
                    每一格＝該入住日在「前 N 天」那個時點已經訂了多少房晚。
                    <b> 空白（—）代表那個觀察日還沒到，不是 0。</b>
                    點擊任一列可看該日 Pickup 的組成明細。
                  </Text>
                  <Table
                    rowKey="stay_date" size="small" columns={matrixCols}
                    dataSource={matrix.rows} scroll={{ x: 1180 }}
                    pagination={{ pageSize: 31, showSizeChanger: true }}
                    onRow={(r) => ({
                      onClick: () => openDetail(r.stay_date),
                      style: { cursor: 'pointer' },
                    })}
                  />
                </Card>
              ) : <Empty />,
            },
            {
              key: 'curve',
              label: '訂房曲線',
              children: (
                <Card size="small">
                  <Space style={{ marginBottom: 12 }} size={8}>
                    <Text type="secondary">入住日</Text>
                    <DatePicker value={curveDate} allowClear={false}
                                onChange={(v) => v && setCurveDate(v)} />
                    {curve && (
                      <Text type="secondary">
                        去年對照日：{curve.ly_stay_date}
                        （最終 {fmtInt(curve.ly_final)} 房晚）
                      </Text>
                    )}
                  </Space>
                  <Spin spinning={curveLoading}>
                    {curveChart.length ? (
                      <ResponsiveContainer width="100%" height={340}>
                        <LineChart data={curveChart}
                                   margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" />
                          {/* X 軸由左到右＝離入住日越來越近 */}
                          <XAxis dataKey="lead" reversed
                                 label={{ value: '入住日前幾天', position: 'insideBottom', offset: -4 }} />
                          <YAxis />
                          <RTooltip formatter={(v: any) => fmtInt(v)}
                                    labelFormatter={(l) => `入住日前 ${l} 天`} />
                          <Legend />
                          <ReferenceLine x={0} stroke={GREY} strokeDasharray="4 4" />
                          <Line type="monotone" dataKey="今年" stroke={BRAND}
                                strokeWidth={2} dot={false} />
                          <Line type="monotone" dataKey="去年同期" stroke={GREY}
                                strokeWidth={2} strokeDasharray="5 4" dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    ) : <Empty description="這個入住日還沒有訂房資料" />}
                  </Spin>
                  <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                    曲線越早往上爬＝訂得越早。今年的線在去年之上代表這一天賣得比去年快。
                    未來的入住日只畫到今天為止。
                  </Text>
                </Card>
              ),
            },
            {
              key: 'pickup',
              label: 'Pickup 明細',
              children: pickup ? (
                <Card size="small">
                  <Alert
                    type="info" showIcon style={{ marginBottom: 12 }}
                    message="新增與取消刻意分開列"
                    description="「新增 5」與「新增 20、取消 15」的淨值都是 +5，但後者代表需求不穩，處置完全不同。只看淨值會漏掉這件事。"
                  />
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={pickupChart}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <RTooltip formatter={(v: any) => fmtInt(Math.abs(Number(v)))} />
                      <Legend />
                      <ReferenceLine y={0} stroke={GREY} />
                      <Bar dataKey="新增" stackId="a" fill={GREEN} />
                      <Bar dataKey="取消" stackId="a" fill={RED} />
                    </BarChart>
                  </ResponsiveContainer>
                  <Table
                    rowKey="stay_date" size="small" columns={pickupCols}
                    dataSource={pickup.rows} style={{ marginTop: 12 }}
                    pagination={{ pageSize: 31, showSizeChanger: true }}
                    onRow={(r) => ({
                      onClick: () => openDetail(r.stay_date),
                      style: { cursor: 'pointer' },
                    })}
                  />
                </Card>
              ) : <Empty />,
            },
            {
              key: 'dim',
              label: <span>維度 Pickup <Tag color="orange">參考值</Tag></span>,
              children: dim ? (
                <Card size="small">
                  {/* ⚠️ 規格 §八第 3 點：必須標參考值 */}
                  <Alert
                    type="warning" showIcon style={{ marginBottom: 12 }}
                    message="這一頁是參考值，不是精確歸因"
                    description={dim.source.note}
                  />
                  <Space style={{ marginBottom: 12 }}>
                    <Radio.Group size="small" value={dimension}
                                 onChange={(e) => setDimension(e.target.value)}>
                      {(Object.keys(DIM_LABELS) as PaceDimension[]).map((k) => (
                        <Radio.Button key={k} value={k}>{DIM_LABELS[k]}</Radio.Button>
                      ))}
                    </Radio.Group>
                    {dim.coverage.ratio !== null && (
                      <Tag color={dim.coverage.is_low ? 'red' : 'default'}>
                        資料涵蓋 {fmtPct(dim.coverage.ratio)}
                      </Tag>
                    )}
                  </Space>
                  <Table
                    rowKey="key" size="small" dataSource={dim.rows}
                    pagination={false}
                    columns={[
                      { title: DIM_LABELS[dimension], dataIndex: 'key' },
                      { title: '新增', dataIndex: 'gross_new', align: 'right', width: 100,
                        render: (v: number) => <span style={{ color: GREEN }}>+{fmtInt(v)}</span> },
                      { title: '取消', dataIndex: 'cancels', align: 'right', width: 100,
                        render: (v: number) => (v ? <span style={{ color: RED }}>−{fmtInt(v)}</span> : EMPTY) },
                      { title: '淨 Pickup', dataIndex: 'net', align: 'right', width: 110,
                        render: (v: number) => <b style={{ color: trendColor(v) }}>{v > 0 ? `+${fmtInt(v)}` : fmtInt(v)}</b> },
                      { title: '期末在手', dataIndex: 'otb_after', align: 'right', width: 110,
                        render: (v: number) => fmtInt(v) },
                    ]}
                  />
                </Card>
              ) : <Empty />,
            },
            {
              key: 'snap',
              label: <span>快照精確版 {readiness && !readiness.ready && <Tag>累積中</Tag>}</span>,
              children: (
                <Card size="small">
                  {readiness?.ready ? (
                    <Alert type="success" showIcon
                           message="快照已累積足夠天數"
                           description="精確版 Pickup（含取消、No-show 與當時的房型／市場維度）可以開發了。見 docs/SPEC_opera_pace.md Phase 2。" />
                  ) : (
                    <>
                      {/* ⚠️ 規格 §九驗收：資料不足時顯示剩餘天數，不畫空圖 */}
                      <Alert
                        type="info" showIcon
                        message="精確版還在累積資料中"
                        description={
                          <>
                            <div>
                              每日快照從 {readiness?.first_snapshot_date || EMPTY} 開始，
                              目前累積 <b>{fmtInt(readiness?.distinct_snapshot_days)}</b> 天，
                              距離可用還需約 <b>{fmtInt(readiness?.remaining_days)}</b> 天。
                            </div>
                            <div style={{ marginTop: 6 }}>
                              精確版會改用每日快照（`ohip_inventory_snapshot`），
                              可以拿到 <b>當時</b> 的房型與市場區隔維度，以及 No-show，
                              不受本頁「回推」的三個失真影響。
                            </div>
                            <div style={{ marginTop: 6, color: GREY }}>
                              在此之前請使用前面四個分頁 —— 它們用訂房日回推，
                              資料可回溯兩年，而且去年同期對照今天就有。
                            </div>
                          </>
                        }
                      />
                      <Descriptions size="small" column={2} bordered style={{ marginTop: 12 }}>
                        <Descriptions.Item label="首次快照">
                          {readiness?.first_snapshot_date || EMPTY}
                        </Descriptions.Item>
                        <Descriptions.Item label="最近快照">
                          {readiness?.last_snapshot_date || EMPTY}
                        </Descriptions.Item>
                        <Descriptions.Item label="累積天數">
                          {fmtInt(readiness?.distinct_snapshot_days)} 天
                        </Descriptions.Item>
                        <Descriptions.Item label="已有最終值的入住日">
                          <Tooltip title="快照回看 7 天，lead_days 為負數的那些 —— 這才是 pickup 曲線有終點的天數。">
                            {fmtInt(readiness?.business_days_with_final)} 天
                          </Tooltip>
                        </Descriptions.Item>
                      </Descriptions>
                    </>
                  )}
                </Card>
              ),
            },
          ]}
        />
      </Spin>

      {/* ⚠️ CLAUDE.md §7 Drawer 明細。本模組非 Ragic 來源，「在 Ragic 查看」不適用。 */}
      <Drawer
        width={640} open={drawerOpen} onClose={() => setDrawerOpen(false)}
        title={detail ? (
          <Space>
            <Tag color="blue">Pickup 組成</Tag>
            <span>入住日：{detail.stay_date}</span>
            <Text type="secondary" style={{ fontWeight: 400, fontSize: 12 }}>
              {detail.from}（不含）～ {detail.to}
            </Text>
          </Space>
        ) : 'Pickup 組成'}
      >
        {!detail ? <Spin /> : (
          <>
            <Descriptions size="small" column={3} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="新增">
                <b style={{ color: GREEN }}>+{fmtInt(detail.summary.gross_new)}</b>
              </Descriptions.Item>
              <Descriptions.Item label="取消">
                <b style={{ color: RED }}>{detail.summary.cancels ? `−${fmtInt(detail.summary.cancels)}` : EMPTY}</b>
              </Descriptions.Item>
              <Descriptions.Item label="淨">
                <b style={{ color: trendColor(detail.summary.net) }}>
                  {detail.summary.net > 0 ? `+${fmtInt(detail.summary.net)}` : fmtInt(detail.summary.net)}
                </b>
              </Descriptions.Item>
            </Descriptions>

            <Title level={5}>新增訂單</Title>
            <Table
              rowKey="confirmation_no" size="small" pagination={false}
              dataSource={detail.added}
              locale={{ emptyText: '這段期間沒有新增' }}
              columns={[
                { title: '訂房編號', dataIndex: 'confirmation_no', width: 120 },
                { title: '訂房日', dataIndex: 'booking_date', width: 110 },
                { title: '提前期', dataIndex: 'lead_days', align: 'right', width: 80,
                  render: (v: number | null) => (v === null ? EMPTY : `${v} 天`) },
                { title: '房型', dataIndex: 'room_type', width: 90 },
                { title: '市場', dataIndex: 'market_code', width: 90 },
                { title: '房費', dataIndex: 'room_revenue', align: 'right',
                  render: (v: number | null) => (v === null ? EMPTY : `$${fmtMoney(v)}`) },
              ]}
            />

            <Title level={5} style={{ marginTop: 20 }}>取消訂單</Title>
            <Table
              rowKey="confirmation_no" size="small" pagination={false}
              dataSource={detail.cancelled}
              locale={{ emptyText: '這段期間沒有取消' }}
              columns={[
                { title: '訂房編號', dataIndex: 'confirmation_no', width: 120 },
                { title: '取消日', dataIndex: 'cancellation_date', width: 110 },
                { title: '原因碼', dataIndex: 'cancellation_reason_code', width: 100,
                  render: (v: string) => v || EMPTY },
                { title: '房型', dataIndex: 'room_type', width: 90 },
                { title: '市場', dataIndex: 'market_code', width: 90 },
                { title: '房費', dataIndex: 'room_revenue', align: 'right',
                  render: (v: number | null) => (v === null ? EMPTY : `$${fmtMoney(v)}`) },
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}

export default OperaPacePage
