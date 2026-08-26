/**
 * OTA 負評警示
 * Route: /ota/alerts    Permission: ota_alerts_view
 *
 * 規格書：`docs/SPEC_ota_reviews.md` §7.4、§9.1
 *
 * 這頁要回答的問題是「**現在有哪些客訴還沒人處理**」，
 * 所以預設只顯示「待處理」，不是全部警示。
 *
 * ⚠️ 處理狀態是**人工營運欄位** —— 同步與重新分析都不會覆蓋它
 *    （`ota_ingest_service.upsert_reviews` 與 `ota_analysis_service._apply`
 *    都明確不碰）。使用者標了「已處理」，隔天排程不會把它變回去。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Button, Card, Col, Empty, Row, Segmented, Select, Space, Statistic,
  Table, Tag, Tooltip, Typography, message,
} from 'antd'
import { ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'

import StandardRangePicker from '@/components/StandardRangePicker'
import { useUrlFilterDefaults } from '@/hooks/useUrlFilterDefaults'
import { MultiCodeSelect, hotelOptions, toParam } from '../filterScope'
import AlertAgingBar from '../AlertAgingBar'
import AlertDailyStrip from '../AlertDailyStrip'
import {
  fetchAlertAging, fetchAlertDaily, fetchAlerts, fetchDataRange, fetchHotelOptions, fetchOverview, runAnalyze,
} from '@/api/ota'
import type {
  AlertDailyResult,
  AlertAgingResult,
  HotelOption, OtaOverview, OtaReviewRow, ReviewFilters,
} from '@/types/ota'
import ReviewDetailDrawer from '../components/ReviewDetailDrawer'

const { Text } = Typography

const STATUS_TABS = [
  { value: 'open', label: '待處理' },
  { value: 'acknowledged', label: '已知悉' },
  { value: 'resolved', label: '已處理' },
  { value: 'ignored', label: '不處理' },
  { value: '', label: '全部' },
]
const STATUS_META: Record<string, { color: string; label: string }> = {
  open: { color: 'error', label: '待處理' },
  acknowledged: { color: 'warning', label: '已知悉' },
  resolved: { color: 'success', label: '已處理' },
  ignored: { color: 'default', label: '不處理' },
}
const PLATFORM_COLOR: Record<string, string> = {
  booking: 'blue', expedia: 'gold', tripadvisor: 'green', agoda: 'purple', google: 'cyan',
}

function scoreColor(score: number | null): string {
  if (score === null) return '#bfbfbf'
  if (score < 6) return '#cf1322'
  if (score >= 8) return '#389e0d'
  return '#595959'
}

const OtaAlertsPage: React.FC = () => {
  const [rows, setRows] = useState<OtaReviewRow[]>([])
  const [total, setTotal] = useState(0)
  const [overview, setOverview] = useState<OtaOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  // ⭐ 從 URL 帶進來的初值（Dashboard 的「待處理警示」卡點過來時會有）
  const urlDefaults = useUrlFilterDefaults()

  // ⚠️ 預設 'open' —— 這一頁的重點就是「還沒處理的」。
  //    `buildFilterQuery` 不會輸出空值，所以 URL 裡有 alert_status 就一定
  //    是明確指定的；沒有就用預設。
  const [status, setStatus] = useState<string>(urlDefaults.alertStatus || 'open')
  // ⚠️ 2026-08-25 改多選：空陣列 ＝ 全部
  const [hotelCodes, setHotelCodes] = useState<string[]>(urlDefaults.hotelCodes)
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(urlDefaults.range)
  const [dataEnd, setDataEnd] = useState('')
  const [hotels, setHotels] = useState<HotelOption[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  // ⭐ 積壓天數分桶（2026-08-25）
  const [aging, setAging] = useState<AlertAgingResult | null>(null)
  const [agingLoading, setAgingLoading] = useState(false)
  // 目前被哪一桶篩著。⚠️ 這只是視覺標記 —— 真正的篩選條件是 `range`。
  //    使用者直接動期間選擇器時必須清掉，否則會標著一個已經不成立的桶。
  const [agingKey, setAgingKey] = useState('')

  // ⭐ 每日發生量條帶（2026-08-25）
  // ⚠️ 與積壓分桶**口徑不同**：這條算「當天發生」，那個算「還沒處理的存量」。
  //    元件的 tooltip 有講清楚；後端註解也有。
  const [daily, setDaily] = useState<AlertDailyResult | null>(null)
  const [dailyLoading, setDailyLoading] = useState(false)
  const [dailyDate, setDailyDate] = useState('')

  const [drawerId, setDrawerId] = useState<number | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const filters = useMemo<ReviewFilters>(() => ({
    hotel_code: toParam(hotelCodes),
    alert_status: status,
    ...(range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
  }), [hotelCodes, status, range])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [list, ov] = await Promise.all([
        fetchAlerts({ ...filters, page, page_size: pageSize }),
        fetchOverview({ hotel_code: toParam(hotelCodes) }),
      ])
      setRows(list.rows)
      setTotal(list.total)
      setOverview(ov)
    } catch {
      message.error('載入負評警示失敗')
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize, hotelCodes])

  useEffect(() => { load() }, [load])

  /**
   * 積壓分桶。
   *
   * ⚠️ **只依飯店篩選重載，不依 `range` 或 `status`**：
   *    - 依 `range` 的話，點了一桶就會把圖本身也篩掉（只剩那一桶有值），
   *      使用者就沒辦法比較各桶、也回不去 —— 圖表把自己吃掉了。
   *    - 依 `status` 的話，切到「已處理」會重打一次拿到同樣的數字
   *      （後端固定只算 open+acknowledged），純浪費。
   */
  const loadAging = useCallback(async () => {
    setAgingLoading(true)
    try {
      setAging(await fetchAlertAging({ hotel_code: toParam(hotelCodes) }))
    } catch {
      // ⚠️ 這張圖是輔助資訊，載不到不要蓋掉清單的錯誤訊息或擋住整頁
      setAging(null)
    } finally {
      setAgingLoading(false)
    }
  }, [hotelCodes])

  useEffect(() => { loadAging() }, [loadAging])

  /** 每日條帶。理由同 loadAging：**不依 `range`**，否則點一格就把圖自己吃掉。 */
  const loadDaily = useCallback(async () => {
    setDailyLoading(true)
    try {
      setDaily(await fetchAlertDaily({ hotel_code: toParam(hotelCodes), days: 60 }))
    } catch {
      setDaily(null)
    } finally {
      setDailyLoading(false)
    }
  }, [hotelCodes])

  useEffect(() => { loadDaily() }, [loadDaily])

  useEffect(() => {
    // ⚠️ anchor 取資料最後一天，不是今天（CLAUDE.md §8.2）
    fetchDataRange().then((r) => setDataEnd(r.end)).catch(() => undefined)
    fetchHotelOptions().then(setHotels).catch(() => undefined)
  }, [])

  /**
   * 點某一桶 → 換算成 review_date 區間塞進既有的期間篩選。
   *
   * ⚠️ 這裡**沒有新增任何後端參數** —— 積壓 N 天 ⇔ 留言日落在
   *    `[今天-max, 今天-min]`，用既有的 start／end 就表達得完整。
   */
  const handlePickBucket = (r: [Dayjs, Dayjs] | null, label: string) => {
    setRange(r)
    setAgingKey(r ? (aging?.buckets.find((x) => x.label === label)?.key ?? '') : '')
    // ⚠️ 兩張圖篩的是**同一個** range —— 選了積壓桶就要清掉每日條帶的高亮，
    //    否則畫面會同時標著兩個互相矛盾的選取狀態。
    setDailyDate('')
    setPage(1)
  }

  /** 點每日條帶的某一格 → 篩那一天。⚠️ 同理要清掉積壓桶的高亮。 */
  const handlePickDay = (r: [Dayjs, Dayjs] | null, d: string) => {
    setRange(r)
    setDailyDate(d)
    setAgingKey('')
    setPage(1)
  }

  /**
   * 使用者直接動期間選擇器。
   *
   * ⚠️ **必須清掉 `agingKey`** —— 不清的話畫面會標著「8–14 天」高亮，
   *    但清單其實已經被別的期間篩著了。**畫面說的跟實際做的不一樣，
   *    比沒有標示更糟。**
   */
  const handleRange = (r: [Dayjs, Dayjs] | null) => {
    setRange(r)
    setAgingKey('')
    setDailyDate('')
    setPage(1)
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const res = await runAnalyze(false)
      message.info(res.message)
      // 背景執行，給它一點時間再重載
      // ⚠️ 分析會產生新的警示，積壓圖也要跟著更新
      window.setTimeout(() => { load(); loadAging(); setAnalyzing(false) }, 8000)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail || '觸發分析失敗')
      setAnalyzing(false)
    }
  }

  const columns: ColumnsType<OtaReviewRow> = [
    {
      title: '狀態', dataIndex: 'alert_status', width: 96, align: 'center',
      render: (value: string) => {
        const meta = STATUS_META[value] || STATUS_META.open
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    {
      title: '評論日期', dataIndex: 'review_date', width: 106,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    { title: '飯店', dataIndex: 'hotel_name', width: 96 },
    {
      title: 'OTA', dataIndex: 'platform_label', width: 108,
      render: (label: string, row) => (
        <Tag color={PLATFORM_COLOR[row.platform] || 'default'}>{label}</Tag>
      ),
    },
    {
      title: '分數', dataIndex: 'score_10', width: 78, align: 'center',
      render: (score: number | null) => (
        score === null ? <Text type="secondary">—</Text>
          : <span style={{ color: scoreColor(score), fontWeight: 600 }}>{score.toFixed(1)}</span>
      ),
    },
    { title: '旅客', dataIndex: 'author', width: 100, ellipsis: true },
    {
      title: '問題摘要', dataIndex: 'summary', ellipsis: true,
      render: (text: string) => <span>{text}</span>,
    },
    {
      title: '主題', dataIndex: 'topics', width: 170,
      render: (topics: string[]) => (
        topics.length === 0
          ? <Text type="secondary">—</Text>
          : (
            <Space size={2} wrap>
              {topics.filter((t) => t.endsWith(':neg')).slice(0, 3).map((t) => (
                <Tag key={t} color="error">{t.split(':')[0]}</Tag>
              ))}
            </Space>
          )
      ),
    },
  ]

  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="待處理警示" value={overview?.alert_open_count ?? 0}
              valueStyle={{ color: (overview?.alert_open_count ?? 0) > 0 ? '#cf1322' : undefined }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="負評總數（低於 6 分）" value={overview?.negative_count ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="平均分數" precision={2}
              value={overview?.avg_score_10 ?? 0}
              suffix="/ 10"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="評論總數" value={overview?.total ?? 0} />
          </Card>
        </Col>
      </Row>

      {/* ⭐ 積壓天數（2026-08-25）。
          KPI 卡的「待處理 58」看不出裡面有沒有一件躺了三週 —— 這張圖回答那個。
          ⚠️ 只在「待處理／已知悉／全部」時顯示：切到「已處理」還畫積壓沒有意義。 */}
      {(status === 'open' || status === 'acknowledged' || status === '') && (
        <AlertAgingBar
          data={aging} loading={agingLoading}
          activeKey={agingKey} onPick={handlePickBucket}
        />
      )}

      {/* ⭐ 每日發生量（2026-08-25）。⚠️ 這條**不依 status 隱藏** ——
          它算的是「當天發生了幾件」，不論後來處理了沒，
          所以看「已處理」時它一樣有意義（那幾天確實出過事）。 */}
      <AlertDailyStrip
        data={daily} loading={dailyLoading}
        activeDate={dailyDate} onPick={handlePickDay}
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[10, 10]} align="middle">
          <Col>
            <Segmented
              value={status}
              onChange={(v) => { setStatus(String(v)); setPage(1) }}
              options={STATUS_TABS}
            />
          </Col>
          <Col>
            <MultiCodeSelect
              value={hotelCodes} onChange={(v) => { setHotelCodes(v); setPage(1) }}
              options={hotelOptions(hotels)} placeholder="全部飯店" width={180}
            />
          </Col>
          <Col>
            {/* ⚠️ anchor 取資料最後一天，不是今天 */}
            <StandardRangePicker
              value={range} anchor={dataEnd}
              onChange={handleRange}
              footerNote="基準日為評論資料的最後一天"
            />
          </Col>
          <Col flex="auto" />
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
              <Tooltip title="分析尚未處理的評論（背景執行）。已填的處理狀態不會被覆蓋。">
                <Button
                  icon={<ThunderboltOutlined />} onClick={handleAnalyze} loading={analyzing}
                >
                  執行分析
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      <Table<OtaReviewRow>
        rowKey="id" size="small" loading={loading}
        columns={columns} dataSource={rows}
        locale={{
          emptyText: (
            <Empty
              description={
                status === 'open'
                  ? '目前沒有待處理的警示 —— 若評論都還沒分析過，先按上方「執行分析」'
                  : '這個狀態下沒有資料'
              }
            />
          ),
        }}
        onRow={(row) => ({
          onClick: () => { setDrawerId(row.id); setDrawerOpen(true) },
          style: {
            cursor: 'pointer',
            background: row.alert_status === 'open' ? '#fff5f5' : undefined,
          },
        })}
        pagination={{
          current: page, pageSize, total, showSizeChanger: true,
          pageSizeOptions: ['20', '50', '100'],
          showTotal: (t) => `共 ${t.toLocaleString()} 則`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />

      {/* allowAlertEdit：這頁就是要處理警示，Drawer 要能改狀態 */}
      <ReviewDetailDrawer
        reviewId={drawerId} open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onUpdated={load}
        allowAlertEdit
      />
    </div>
  )
}

export default OtaAlertsPage
