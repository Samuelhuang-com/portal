/**
 * 金旭 PMS 分析 — 使用手冊（/jinxu/manual）
 *
 * 互動功能（仿 /opera/manual）：
 *   1. 左側目錄跟隨捲動高亮，點擊跳轉
 *   2. 全文搜尋：即時篩掉不相關章節並高亮命中字
 *   3. 「資料涵蓋」「目前基準」區塊即時讀資料庫，不是寫死的範例數字
 *   4. 對應到實際頁面的章節，標題右側有「前往此功能」按鈕
 *   5. 章節狀態標籤（已實作／部分實作／規劃中），可只看未完成的
 *
 * 手冊內容全部在 content.ts，這裡只負責版面與互動。
 *
 * ⚠️ 刻意不從 Opera/Manual 匯入任何東西——業主指定兩個模組完全獨立。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Anchor, Button, Card, Col, Descriptions, Empty, Input, Row, Space,
  Spin, Statistic, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  ArrowRightOutlined, BookOutlined, BulbOutlined, ExclamationCircleOutlined,
  FunctionOutlined, PrinterOutlined, SearchOutlined,
} from '@ant-design/icons'

import { fetchImportStatus, fetchResvSummary, fetchRevenueSummary } from '@/api/jinxu'
import type { ImportStatus, ResvSummary, RevenueSummary } from '@/types/jinxu'
import BackToTop from '../components/BackToTop'
import { fmtInt } from '../components/constants'
import {
  MANUAL, MANUAL_META, STATUS_META, subSectionText,
  type Block, type Section, type SubSection,
} from './content'

const { Title, Text, Paragraph } = Typography

/** 目錄吸附位置：Portal Header 為 sticky、實際高度 64px，再留 12px 空隙 */
const STICKY_TOP = 76
const BRAND = '#1B3A5C'
const ACCENT = '#4BA8E8'
const EMPTY_TEXT = '—'

/** 手冊即時資料（三支 API 各自獨立，任一支失敗不影響其他區塊） */
interface LiveData {
  status: ImportStatus | null
  revenue: RevenueSummary | null
  resv: ResvSummary | null
}

// ── 行內樣式標記：**粗體** 與 `等寬` ────────────────────────────────────────
// 手冊內容量大，用兩個最常用的 Markdown 記號就夠了，不值得為此引入 markdown 套件。
function renderInline(text: string, keyword: string): React.ReactNode {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean)
  return tokens.map((tok, i) => {
    if (tok.startsWith('**') && tok.endsWith('**')) {
      return <Text strong key={i}>{highlight(tok.slice(2, -2), keyword)}</Text>
    }
    if (tok.startsWith('`') && tok.endsWith('`')) {
      return <Text code key={i} style={{ fontSize: 12 }}>{highlight(tok.slice(1, -1), keyword)}</Text>
    }
    return <React.Fragment key={i}>{highlight(tok, keyword)}</React.Fragment>
  })
}

/** 搜尋命中高亮 */
function highlight(text: string, keyword: string): React.ReactNode {
  const kw = keyword.trim()
  if (!kw) return text
  const idx = text.toLowerCase().indexOf(kw.toLowerCase())
  if (idx < 0) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: '#fff1b8', padding: '0 2px' }}>
        {text.slice(idx, idx + kw.length)}
      </mark>
      {highlight(text.slice(idx + kw.length), kw)}
    </>
  )
}

// ── 即時資料區塊 ─────────────────────────────────────────────────────────────

const LiveCoverage: React.FC<{ live: LiveData; loading: boolean }> = ({ live, loading }) => {
  if (loading) return <Card size="small" style={{ marginBottom: 12 }}><Spin /></Card>
  const s = live.status
  if (!s) return <Empty description="無法讀取資料涵蓋範圍" style={{ margin: '12px 0' }} />

  const ledger = s.sources.FCR02_LEDGER
  const resv = s.sources.RESV_DETAIL
  return (
    <Card
      size="small"
      style={{ marginBottom: 12, borderLeft: `3px solid ${ACCENT}`, background: '#f9fbff' }}
      title={<Text strong style={{ color: BRAND }}>目前資料涵蓋（即時）</Text>}
    >
      <Descriptions size="small" column={{ xs: 1, md: 2 }} bordered style={{ marginBottom: 12 }}>
        <Descriptions.Item label={ledger?.label ?? '客帳帳目明細表'}>
          {ledger?.has_data
            ? `${ledger.date_start} ～ ${ledger.date_end}（${fmtInt(ledger.row_count)} 筆分錄）`
            : <Tag color="orange">尚未匯入</Tag>}
        </Descriptions.Item>
        <Descriptions.Item label={resv?.label ?? '訂房狀況表'}>
          {resv?.has_data
            ? `${resv.date_start} ～ ${resv.date_end}（${fmtInt(resv.row_count)} 訂房 / ${fmtInt(resv.child_count ?? 0)} 住宿段）`
            : <Tag color="orange">尚未匯入</Tag>}
        </Descriptions.Item>
      </Descriptions>
      <Space wrap>
        <Tag color={s.cross_analysis_available ? 'success' : 'default'}>
          訂價 vs 實收交叉分析：{s.cross_analysis_available ? '可用' : '需兩份都匯入'}
        </Tag>
        <Tag color={s.yoy_available ? 'success' : 'warning'}>
          同期比較 YoY：{s.yoy_available ? '可用' : '資料不足（僅單一年度）'}
        </Tag>
        {s.years_covered.length > 0 && <Tag>年度 {s.years_covered.join('、')}</Tag>}
      </Space>
      {!s.yoy_available && (
        <Alert
          type="warning"
          showIcon
          style={{ marginTop: 12 }}
          message="目前只有單一年度資料，所有同期比較（YoY）功能都無法使用"
          description="請向金旭補匯出前一年度的兩份報表後再上傳。"
        />
      )}
    </Card>
  )
}

const LiveBaseline: React.FC<{ live: LiveData; loading: boolean }> = ({ live, loading }) => {
  if (loading) return <Card size="small" style={{ marginBottom: 12 }}><Spin /></Card>
  const { revenue, resv } = live
  if (!revenue && !resv) {
    return <Empty description="尚未匯入資料，因此還沒有基準值" style={{ margin: '12px 0' }} />
  }
  return (
    <Card
      size="small"
      style={{ marginBottom: 12, borderLeft: `3px solid ${ACCENT}`, background: '#f9fbff' }}
      title={<Text strong style={{ color: BRAND }}>目前基準（即時，全期間）</Text>}
    >
      <Row gutter={16}>
        {revenue && (
          <>
            <Col xs={12} md={6}>
              <Statistic title="總收入（淨額）" value={revenue.revenue_net} precision={0} prefix="$" />
            </Col>
            <Col xs={12} md={6}>
              <Statistic title="沖帳率（筆數）" value={revenue.reversal_rate_by_count}
                         precision={2} suffix="%" />
            </Col>
          </>
        )}
        {resv && (
          <>
            <Col xs={12} md={6}>
              <Statistic title="平均房價 ADR" value={resv.adr} precision={0} prefix="$" />
            </Col>
            <Col xs={12} md={6}>
              <Statistic title="取消率" value={resv.cancel_rate_by_count}
                         precision={2} suffix="%" valueStyle={{ color: '#cf1322' }} />
            </Col>
          </>
        )}
      </Row>
      {resv && (
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 8 }}>
          {resv.population_note}；平均住宿 {resv.avg_billable_nights} 晚（Day Use 計 1 晚）
        </Text>
      )}
      {revenue && (
        <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
          {revenue.note}
        </Text>
      )}
    </Card>
  )
}

// ── 區塊渲染 ─────────────────────────────────────────────────────────────────

const BlockView: React.FC<{
  block: Block
  keyword: string
  live: LiveData
  loading: boolean
}> = ({ block, keyword, live, loading }) => {
  switch (block.t) {
    case 'p':
      return (
        <Paragraph style={{ marginBottom: 10, lineHeight: 1.9 }}>
          {renderInline(block.text, keyword)}
        </Paragraph>
      )

    case 'sub':
      return (
        <Text strong style={{ display: 'block', margin: '14px 0 6px', color: BRAND }}>
          {highlight(block.title, keyword)}
        </Text>
      )

    case 'ul':
      return (
        <ul style={{ paddingLeft: 22, marginBottom: 10, lineHeight: 1.9 }}>
          {block.items.map((it, i) => <li key={i}>{renderInline(it, keyword)}</li>)}
        </ul>
      )

    case 'ol':
      return (
        <ol style={{ paddingLeft: 22, marginBottom: 10, lineHeight: 1.9 }}>
          {block.items.map((it, i) => <li key={i}>{renderInline(it, keyword)}</li>)}
        </ol>
      )

    case 'formula':
      return (
        <div style={{
          background: '#f6f8fa', border: '1px solid #e6ebf1', borderLeft: `3px solid ${ACCENT}`,
          borderRadius: 4, padding: '10px 14px', margin: '10px 0',
        }}>
          {block.items.map((it, i) => (
            <div key={i} style={{
              fontFamily: 'Consolas, Monaco, monospace', fontSize: 13, lineHeight: 2,
            }}>
              <FunctionOutlined style={{ color: ACCENT, marginRight: 8 }} />
              {highlight(it, keyword)}
            </div>
          ))}
        </div>
      )

    case 'note':
      return (
        <Alert type="info" showIcon icon={<BulbOutlined />} style={{ margin: '10px 0' }}
               message={<span style={{ lineHeight: 1.9 }}>{renderInline(block.text, keyword)}</span>} />
      )

    case 'caution':
      return (
        <Alert type="warning" showIcon icon={<ExclamationCircleOutlined />} style={{ margin: '10px 0' }}
               message={<span style={{ lineHeight: 1.9 }}>{renderInline(block.text, keyword)}</span>} />
      )

    case 'table':
      return (
        <div style={{ margin: '12px 0' }}>
          {block.caption && (
            <Text type="secondary" style={{ display: 'block', marginBottom: 6, fontSize: 12 }}>
              {highlight(block.caption, keyword)}
            </Text>
          )}
          <Table
            size="small"
            pagination={false}
            bordered
            rowKey={(_, i) => String(i)}
            dataSource={block.rows.map((r, i) => ({
              __i: i, ...Object.fromEntries(r.map((c, j) => [`c${j}`, c])),
            }))}
            columns={block.head.map((h, j) => ({
              title: h,
              dataIndex: `c${j}`,
              width: j === 0 ? 200 : undefined,
              render: (v: string) => {
                // 對照表的狀態欄自動上色
                const meta = Object.values(STATUS_META).find((m) => m.label === v)
                if (meta) return <Tag color={meta.color}>{v}</Tag>
                return <span style={{ lineHeight: 1.8 }}>{renderInline(v || EMPTY_TEXT, keyword)}</span>
              },
            }))}
          />
        </div>
      )

    case 'live':
      return block.kind === 'coverage'
        ? <LiveCoverage live={live} loading={loading} />
        : <LiveBaseline live={live} loading={loading} />

    default:
      return null
  }
}

// ── 章節 ─────────────────────────────────────────────────────────────────────

const SubSectionView: React.FC<{
  sub: SubSection
  keyword: string
  live: LiveData
  loading: boolean
}> = ({ sub, keyword, live, loading }) => {
  const navigate = useNavigate()
  const meta = sub.status ? STATUS_META[sub.status] : null

  return (
    <div id={sub.id} style={{ scrollMarginTop: STICKY_TOP, marginBottom: 28 }}>
      <Space wrap align="center" style={{ marginBottom: 8 }}>
        <Title level={5} style={{ margin: 0, color: BRAND }}>
          {highlight(sub.title, keyword)}
        </Title>
        {meta && <Tag color={meta.color}>{meta.label}</Tag>}
        {sub.route && (
          <Button size="small" type="link" icon={<ArrowRightOutlined />}
                  onClick={() => navigate(sub.route!)}>
            前往此功能
          </Button>
        )}
      </Space>

      {sub.gap && (
        <Alert
          type={sub.status === 'planned' ? 'info' : 'warning'}
          showIcon banner style={{ marginBottom: 10 }}
          message={<span style={{ fontSize: 13 }}>{renderInline(sub.gap, keyword)}</span>}
        />
      )}

      {sub.blocks.map((b, i) => (
        <BlockView key={i} block={b} keyword={keyword} live={live} loading={loading} />
      ))}
    </div>
  )
}

// ── 主頁面 ───────────────────────────────────────────────────────────────────

const JinxuManualPage: React.FC = () => {
  const [keyword, setKeyword] = useState('')
  const [onlyTodo, setOnlyTodo] = useState(false)
  const [live, setLive] = useState<LiveData>({ status: null, revenue: null, resv: null })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      // 手冊本身不依賴資料；讀不到就只有「即時」區塊顯示空狀態。
      // 三支 API 分開 try，避免其中一支無權限就整片空白。
      let status: ImportStatus | null = null
      let revenue: RevenueSummary | null = null
      let resv: ResvSummary | null = null
      try { status = await fetchImportStatus() } catch { /* 無 jinxu_view 不會走到這頁 */ }
      try { revenue = await fetchRevenueSummary({}) } catch { /* ignore */ }
      try { resv = await fetchResvSummary({}) } catch { /* ignore */ }
      if (!status && !revenue && !resv) {
        message.warning('無法讀取即時數據，手冊其餘內容不受影響')
      }
      setLive({ status, revenue, resv })
      setLoading(false)
    })()
  }, [])

  // ── 篩選：搜尋 + 只看未完成 ──────────────────────────────────────────────
  const filtered: Section[] = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return MANUAL.map((sec) => {
      const subs = sec.subs.filter((sub) => {
        if (onlyTodo && sub.status !== 'planned' && sub.status !== 'partial') return false
        if (!kw) return true
        return subSectionText(sub).toLowerCase().includes(kw)
          || sec.title.toLowerCase().includes(kw)
      })
      return { ...sec, subs }
    }).filter((sec) => sec.subs.length > 0)
  }, [keyword, onlyTodo])

  const totalSubs = useMemo(() => MANUAL.reduce((n, s) => n + s.subs.length, 0), [])
  const shownSubs = useMemo(() => filtered.reduce((n, s) => n + s.subs.length, 0), [filtered])

  const anchorItems = useMemo(
    () => filtered.map((sec) => ({
      key: sec.id,
      href: `#${sec.id}`,
      title: sec.title,
      children: sec.subs.map((sub) => ({
        key: sub.id,
        href: `#${sub.id}`,
        title: (
          <span style={{ fontSize: 12 }}>
            {sub.title}
            {sub.status && sub.status !== 'done' && (
              <Tag color={STATUS_META[sub.status].color}
                   style={{ marginLeft: 4, transform: 'scale(0.85)' }}>
                {STATUS_META[sub.status].label}
              </Tag>
            )}
          </span>
        ),
      })),
    })),
    [filtered],
  )

  const handlePrint = useCallback(() => {
    if (keyword || onlyTodo) {
      message.info('目前有套用篩選，列印出來的只會是篩選後的內容')
    }
    window.print()
  }, [keyword, onlyTodo])

  return (
    <div style={{ padding: 24 }}>
      {/* ── 標題列 ──────────────────────────────────────────────────────── */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 12 }} gutter={[12, 12]}>
        <Col>
          <Space align="center" wrap>
            <BookOutlined style={{ fontSize: 22, color: BRAND }} />
            <Title level={4} style={{ margin: 0, color: BRAND }}>{MANUAL_META.title}</Title>
            <Tag>{MANUAL_META.version}</Tag>
          </Space>
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {`${MANUAL_META.subtitle}　｜　最後更新 ${MANUAL_META.updated}`}
            </Text>
          </div>
        </Col>
        <Col>
          <Space wrap>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="搜尋手冊內容（例如 沖帳、取消率、遮罩、夜次）"
              style={{ width: 320 }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <Tooltip title="只顯示「規劃中」與「部分實作」的章節，方便挑出還缺什麼資料或確認">
              <Space size={6}>
                <Switch size="small" checked={onlyTodo} onChange={setOnlyTodo} />
                <Text style={{ fontSize: 13 }}>只看待補</Text>
              </Space>
            </Tooltip>
            <Button icon={<PrinterOutlined />} onClick={handlePrint}>列印</Button>
          </Space>
        </Col>
      </Row>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={MANUAL_META.disclaimer}
        description={
          <Text type="secondary" style={{ fontSize: 12 }}>
            {`${MANUAL_META.basedOn}。標示「部分實作」或「規劃中」的章節，`}
            代表該功能受限於金旭報表缺欄位、或某個語意尚未經相關單位確認；完整清單見第 11 章。
          </Text>
        }
      />

      {(keyword || onlyTodo) && (
        <Alert
          type={shownSubs > 0 ? 'success' : 'warning'}
          showIcon
          style={{ marginBottom: 16 }}
          message={
            shownSubs > 0
              ? `符合條件的章節：${shownSubs} / ${totalSubs}`
              : onlyTodo && !keyword
                ? '目前沒有「規劃中」或「部分實作」的章節'
                : `找不到符合「${keyword}」的章節`
          }
          action={
            <Button size="small" onClick={() => { setKeyword(''); setOnlyTodo(false) }}>
              清除篩選
            </Button>
          }
        />
      )}

      <Row gutter={16}>
        {/* ── 左側目錄（跟著捲動固定在畫面上）──────────────────────────────
            Portal 的捲動容器是 window（Content 本身不捲），Header 是 sticky、
            實際高度 64px。因此把 sticky 放在 Col 上、top 給 76（64 + 12 留白），
            並用 alignSelf: flex-start 讓 Col 不被 Row 拉長——否則 sticky 沒有
            可移動的空間就不會生效。Anchor 本身維持 affix={false} 避免雙重固定。 */}
        <Col
          xs={0}
          lg={6}
          xl={5}
          style={{ position: 'sticky', top: STICKY_TOP, alignSelf: 'flex-start', zIndex: 5 }}
        >
          <Card
            size="small"
            title="目錄"
            bodyStyle={{ maxHeight: `calc(100vh - ${STICKY_TOP + 72}px)`, overflowY: 'auto' }}
          >
            {anchorItems.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="無符合章節" />
            ) : (
              <Anchor affix={false} offsetTop={STICKY_TOP}
                      getContainer={() => window} items={anchorItems} />
            )}
          </Card>
        </Col>

        {/* ── 右側內容 ─────────────────────────────────────────────────── */}
        <Col xs={24} lg={18} xl={19}>
          {filtered.length === 0 ? (
            <Card><Empty description="沒有符合條件的章節" /></Card>
          ) : (
            filtered.map((sec) => (
              <Card
                key={sec.id}
                id={sec.id}
                style={{ marginBottom: 16, scrollMarginTop: STICKY_TOP }}
                title={
                  <Text strong style={{ fontSize: 16, color: BRAND }}>
                    {highlight(sec.title, keyword)}
                  </Text>
                }
              >
                {sec.intro && (
                  <Paragraph type="secondary" style={{ lineHeight: 1.9 }}>
                    {renderInline(sec.intro, keyword)}
                  </Paragraph>
                )}
                {sec.subs.map((sub) => (
                  <SubSectionView key={sub.id} sub={sub} keyword={keyword}
                                  live={live} loading={loading} />
                ))}
              </Card>
            ))
          )}
        </Col>
      </Row>

      <Card size="small" style={{ marginTop: 8, background: '#fafafa' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          這個模組的價值不在多產幾張報表，而在把金旭兩份 xlsx 的口徑固定下來：
          什麼算收入、什麼是母體、哪些數字對得上報表、哪些只是估計值。
          遇到數字看不懂，順序是先查第 3 章的口徑定義，再查第 9 章的對帳，最後看第 11 章是不是已知限制。
        </Text>
      </Card>

      <BackToTop />
    </div>
  )
}

export default JinxuManualPage
