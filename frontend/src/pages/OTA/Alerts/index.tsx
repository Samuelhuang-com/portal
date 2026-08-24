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
import {
  fetchAlerts, fetchDataRange, fetchHotelOptions, fetchOverview, runAnalyze,
} from '@/api/ota'
import type {
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
  const [hotelCode, setHotelCode] = useState(urlDefaults.hotelCode)
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(urlDefaults.range)
  const [dataEnd, setDataEnd] = useState('')
  const [hotels, setHotels] = useState<HotelOption[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  const [drawerId, setDrawerId] = useState<number | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const filters = useMemo<ReviewFilters>(() => ({
    hotel_code: hotelCode,
    alert_status: status,
    ...(range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
  }), [hotelCode, status, range])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [list, ov] = await Promise.all([
        fetchAlerts({ ...filters, page, page_size: pageSize }),
        fetchOverview({ hotel_code: hotelCode }),
      ])
      setRows(list.rows)
      setTotal(list.total)
      setOverview(ov)
    } catch {
      message.error('載入負評警示失敗')
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize, hotelCode])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    // ⚠️ anchor 取資料最後一天，不是今天（CLAUDE.md §8.2）
    fetchDataRange().then((r) => setDataEnd(r.end)).catch(() => undefined)
    fetchHotelOptions().then(setHotels).catch(() => undefined)
  }, [])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const res = await runAnalyze(false)
      message.info(res.message)
      // 背景執行，給它一點時間再重載
      window.setTimeout(() => { load(); setAnalyzing(false) }, 8000)
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
            <Select
              value={hotelCode} onChange={(v) => { setHotelCode(v); setPage(1) }}
              style={{ width: 140 }}
              options={[{ value: '', label: '全部飯店' }, ...hotels]}
            />
          </Col>
          <Col>
            {/* ⚠️ anchor 取資料最後一天，不是今天 */}
            <StandardRangePicker
              value={range} anchor={dataEnd}
              onChange={(v) => { setRange(v); setPage(1) }}
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
