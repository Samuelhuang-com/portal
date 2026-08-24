/**
 * OTA 評論清單
 * Route: /ota/reviews    Permission: ota_reviews_view
 *
 * 規格書：`docs/SPEC_ota_reviews.md` §9.1
 *
 * ⚠️ 期間篩選一律用 StandardRangePicker，且 `anchor` 取自
 *    `GET /ota/stats/data-range` 的 `end`（評論資料最後一天），**不是今天**。
 *    OTA 評論落後現實好幾天，用今天當基準的「本月」會選到一片空白。
 *    （CLAUDE.md §8.2）
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Button, Card, Col, Input, InputNumber, Row, Select, Space, Switch, Table,
  Tag, Tooltip, Typography, message,
} from 'antd'
import { DownloadOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Dayjs } from 'dayjs'

import StandardRangePicker from '@/components/StandardRangePicker'
import { useUrlFilterDefaults } from '@/hooks/useUrlFilterDefaults'
import {
  downloadBlob, exportReviews, fetchDataRange, fetchHotelOptions,
  fetchPlatformOptions, fetchReviews,
} from '@/api/ota'
import type {
  HotelOption, OtaReviewRow, PlatformOption, ReviewFilters,
} from '@/types/ota'
import ReviewDetailDrawer from '../components/ReviewDetailDrawer'

const { Text } = Typography

const SENTIMENT_OPTIONS = [
  { value: 'positive', label: '正面' },
  { value: 'neutral', label: '中立' },
  { value: 'negative', label: '負面' },
]
const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'success', neutral: 'default', negative: 'error',
}
const SENTIMENT_LABEL: Record<string, string> = {
  positive: '正面', neutral: '中立', negative: '負面',
}
const PLATFORM_COLOR: Record<string, string> = {
  booking: 'blue', expedia: 'gold', tripadvisor: 'green', agoda: 'purple', google: 'cyan',
}

/** 分數色彩：低於 6 分紅字、8 分以上綠字。與 §7.4 警示門檻一致 */
function scoreColor(score: number | null): string {
  if (score === null) return '#bfbfbf'
  if (score < 6) return '#cf1322'
  if (score >= 8) return '#389e0d'
  return '#595959'
}

const OtaReviewsPage: React.FC = () => {
  const [rows, setRows] = useState<OtaReviewRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)

  // ⭐ 從 URL 帶進來的初值（Dashboard 的 KPI 卡點過來時會有）。
  //    ⚠️ 只在首次掛載讀一次，不做雙向同步 —— 見 useUrlFilterDefaults 的說明。
  const urlDefaults = useUrlFilterDefaults()

  // ⚠️ dataEnd 是 StandardRangePicker 的基準日，來自後端而非 dayjs()
  const [dataEnd, setDataEnd] = useState<string>('')
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(urlDefaults.range)

  const [hotelCode, setHotelCode] = useState(urlDefaults.hotelCode)
  const [platform, setPlatform] = useState(urlDefaults.platform)
  const [sentiment, setSentiment] = useState(urlDefaults.sentiment)
  // ⭐ 「分數低於 N」的篩選（2026-08-23）。門檻可輸入，不是寫死的 6.0 ——
  //    6.0 只是 Dashboard KPI 下鑽時帶進來的預設值。
  const [scoreBelow, setScoreBelow] = useState<number | null>(urlDefaults.scoreBelow)
  const [keyword, setKeyword] = useState('')
  const [keywordInput, setKeywordInput] = useState('')
  const [includeDuplicate, setIncludeDuplicate] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  const [hotels, setHotels] = useState<HotelOption[]>([])
  const [platforms, setPlatforms] = useState<PlatformOption[]>([])

  const [drawerId, setDrawerId] = useState<number | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  /** 組查詢參數：range 為 null（「全部」）時**不帶起迄**，由後端套用完整範圍 */
  const filters = useMemo<ReviewFilters>(() => ({
    hotel_code: hotelCode,
    platform,
    sentiment,
    keyword,
    // ⚠️ `?? undefined` 不是 `|| undefined` —— 0 是合法的門檻值
    score_below: scoreBelow ?? undefined,
    include_duplicate: includeDuplicate,
    ...(range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
  }), [hotelCode, platform, sentiment, scoreBelow, keyword, includeDuplicate, range])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchReviews({ ...filters, page, page_size: pageSize })
      setRows(res.rows)
      setTotal(res.total)
    } catch {
      message.error('載入評論失敗')
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    // 基準日與下拉選項只在進頁時載入一次
    fetchDataRange().then((r) => setDataEnd(r.end)).catch(() => undefined)
    fetchHotelOptions().then(setHotels).catch(() => undefined)
    fetchPlatformOptions().then(setPlatforms).catch(() => undefined)
  }, [])

  const handleSearch = () => {
    setKeyword(keywordInput.trim())
    setPage(1)
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const blob = await exportReviews(filters)
      const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '')
      downloadBlob(blob, `OTA評論_${stamp}.xlsx`)
    } catch {
      message.error('匯出失敗')
    } finally {
      setExporting(false)
    }
  }

  const columns: ColumnsType<OtaReviewRow> = [
    {
      title: '評論日期', dataIndex: 'review_date', width: 108,
      render: (value: string) => value || (
        <Tooltip title="原始頁未提供日期，或格式無法解析。這類評論不會進入月度趨勢。">
          <Text type="secondary">—</Text>
        </Tooltip>
      ),
    },
    { title: '飯店', dataIndex: 'hotel_name', width: 96 },
    {
      title: 'OTA', dataIndex: 'platform_label', width: 108,
      render: (label: string, row) => (
        <Tag color={PLATFORM_COLOR[row.platform] || 'default'}>{label}</Tag>
      ),
    },
    {
      title: '分數', dataIndex: 'score_10', width: 92, align: 'center',
      render: (score: number | null, row) => (
        score === null
          ? <Text type="secondary">—</Text>
          : (
            <Tooltip title={row.score_scale === 5
              ? `原始 ${row.score_raw?.toFixed(1)} 分（5 分制），已換算為 10 分制`
              : '原始即為 10 分制'}>
              <span style={{ color: scoreColor(score), fontWeight: 600 }}>
                {score.toFixed(1)}
              </span>
            </Tooltip>
          )
      ),
    },
    { title: '旅客', dataIndex: 'author', width: 110, ellipsis: true },
    {
      title: '留言摘要', dataIndex: 'summary', ellipsis: true,
      render: (text: string, row) => (
        <Space size={6}>
          {row.is_duplicate && <Tag color="default">重複</Tag>}
          <span>{text}</span>
        </Space>
      ),
    },
    {
      title: '情緒', dataIndex: 'sentiment_label', width: 82, align: 'center',
      render: (label: string) => (
        label
          ? <Tag color={SENTIMENT_COLOR[label] || 'default'}>{SENTIMENT_LABEL[label] || label}</Tag>
          : <Text type="secondary">—</Text>
      ),
    },
    {
      title: '主題', dataIndex: 'topics', width: 150,
      render: (topics: string[]) => (
        topics.length === 0
          ? <Text type="secondary">—</Text>
          : (
            <Space size={2} wrap>
              {topics.slice(0, 2).map((t) => {
                const [name, polarity] = t.split(':')
                return (
                  <Tag key={t} color={polarity === 'pos' ? 'success' : 'error'}>{name}</Tag>
                )
              })}
              {topics.length > 2 && <Text type="secondary">+{topics.length - 2}</Text>}
            </Space>
          )
      ),
    },
  ]

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[10, 10]} align="middle">
          <Col>
            <Select
              value={hotelCode} onChange={(v) => { setHotelCode(v); setPage(1) }}
              style={{ width: 140 }} placeholder="飯店"
              options={[{ value: '', label: '全部飯店' }, ...hotels]}
            />
          </Col>
          <Col>
            <Select
              value={platform} onChange={(v) => { setPlatform(v); setPage(1) }}
              style={{ width: 140 }} placeholder="OTA"
              options={[{ value: '', label: '全部 OTA' },
                ...platforms.map((p) => ({ value: p.value as string, label: p.label }))]}
            />
          </Col>
          <Col>
            <Select
              value={sentiment} onChange={(v) => { setSentiment(v); setPage(1) }}
              style={{ width: 120 }} placeholder="情緒"
              options={[{ value: '', label: '全部情緒' }, ...SENTIMENT_OPTIONS]}
            />
          </Col>
          <Col>
            {/* ⭐ 與 Dashboard 的「負面評論」KPI **完全同一個條件**（2026-08-23）。
                ⚠️ 這裡刻意不做成「情緒」下拉的一個選項 —— 兩者判定不同：
                   情緒看 sentiment_label（分析結果，未分析的是空的）、
                   這個看分數。混在同一個下拉裡會讓人以為它們是同一件事。 */}
            <Tooltip title="只看分數低於這個值的評論（不含等於）。留白＝不篩。填 6 時與 Dashboard 的「負面評論」是同一個條件，數字會一致。">
              <InputNumber
                value={scoreBelow}
                onChange={(v) => { setScoreBelow(v); setPage(1) }}
                min={0} max={10} step={0.5} precision={1}
                style={{ width: 140 }}
                placeholder="分數低於"
                prefix={<span style={{ color: '#999', fontSize: 12 }}>&lt;</span>}
                addonAfter="分"
              />
            </Tooltip>
          </Col>
          <Col>
            {/* ⚠️ anchor 取資料最後一天，不是今天（CLAUDE.md §8.2） */}
            <StandardRangePicker
              value={range}
              anchor={dataEnd}
              onChange={(v) => { setRange(v); setPage(1) }}
              footerNote="基準日為評論資料的最後一天（爬蟲與客人留言都會落後幾天）"
            />
          </Col>
          <Col flex="auto" style={{ minWidth: 200 }}>
            <Input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onPressEnter={handleSearch}
              placeholder="搜尋旅客、標題或留言內容"
              allowClear
              suffix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
            />
          </Col>
          <Col>
            <Space>
              <Button icon={<SearchOutlined />} onClick={handleSearch}>搜尋</Button>
              <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
              <Button
                icon={<DownloadOutlined />} onClick={handleExport} loading={exporting}
              >
                匯出 Excel
              </Button>
            </Space>
          </Col>
        </Row>

        <Row style={{ marginTop: 10 }}>
          <Col>
            <Space size={6}>
              <Switch
                size="small"
                checked={includeDuplicate}
                onChange={(v) => { setIncludeDuplicate(v); setPage(1) }}
              />
              <Text type="secondary" style={{ fontSize: 12 }}>
                顯示跨站重複的評論（同一位客人在多個平台留下的同一則留言；
                預設隱藏，統計一律不計入）
              </Text>
            </Space>
          </Col>
        </Row>
      </Card>

      <Table<OtaReviewRow>
        rowKey="id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={rows}
        onRow={(row) => ({
          onClick: () => { setDrawerId(row.id); setDrawerOpen(true) },
          style: {
            cursor: 'pointer',
            // 負評警示底色（沿用專案既有的未完成附表色）
            background: row.is_alert && row.alert_status === 'open' ? '#fff5f5' : undefined,
          },
        })}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: ['20', '50', '100', '200'],
          showTotal: (t) => `共 ${t.toLocaleString()} 則`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />

      <ReviewDetailDrawer
        reviewId={drawerId}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onUpdated={load}
      />
    </div>
  )
}

export default OtaReviewsPage
