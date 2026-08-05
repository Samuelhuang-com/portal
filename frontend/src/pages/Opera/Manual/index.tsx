/**
 * 營運分析 — 使用手冊（/opera/manual）
 *
 * 互動功能：
 *   1. 左側目錄跟隨捲動高亮，點擊跳轉
 *   2. 全文搜尋：即時篩掉不相關章節並高亮命中字
 *   3. 「目前基準」「資料涵蓋」區塊即時讀取資料庫，不是寫死的範例數字
 *   4. 每個對應到實際頁面的章節，標題右側有「前往此功能」按鈕
 *   5. 章節狀態標籤（已實作／部分實作／規劃中），可只看未實作的
 *
 * 手冊內容全部在 content.ts，這裡只負責版面與互動。
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Anchor, Button, Card, Col, Descriptions, Empty, Input, Row, Space,
  Spin, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  ArrowRightOutlined, BookOutlined, BulbOutlined, ExclamationCircleOutlined,
  FunctionOutlined, PrinterOutlined, SearchOutlined,
} from '@ant-design/icons'

import { fetchOperaDashboard } from '@/api/opera'
import type { OperaDashboard } from '@/types/opera'
import BackToTop from '../components/BackToTop'
import {
  MANUAL, MANUAL_META, STATUS_META, subSectionText,
  type Block, type Section, type SubSection,
} from './content'
import {
  ACCENT, BRAND, EMPTY, GREEN, ORANGE, RED,
  fmtInt, fmtMoney, fmtPct, fmtPpt, fmtYoY, periodTagColor, trendColor,
} from '../components/formatters'

const { Title, Text, Paragraph } = Typography

/** 目錄吸附位置：Portal Header 為 sticky、實際高度 64px，再留 12px 空隙 */
const STICKY_TOP = 76

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
      <mark style={{ background: '#fff1b8', padding: '0 2px' }}>{text.slice(idx, idx + kw.length)}</mark>
      {highlight(text.slice(idx + kw.length), kw)}
    </>
  )
}

// ── 即時資料區塊 ─────────────────────────────────────────────────────────────

const LiveBaseline: React.FC<{ data: OperaDashboard | null; loading: boolean }> = ({ data, loading }) => {
  if (loading) return <Card size="small" style={{ marginBottom: 12 }}><Spin /></Card>
  if (!data?.has_data || !data.kpi) {
    return <Empty description="尚未匯入資料，因此還沒有基準值" style={{ margin: '12px 0' }} />
  }
  const k = data.kpi
  const c = k.current
  return (
    <Card
      size="small"
      style={{ marginBottom: 12, borderLeft: `3px solid ${ACCENT}`, background: '#f9fbff' }}
      title={
        <Space wrap>
          <Text strong style={{ color: BRAND }}>目前基準（即時）</Text>
          <Tag color={periodTagColor(k.period.period_type)}>{k.period.period_label}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>{`${k.period.start} ～ ${k.period.end}`}</Text>
        </Space>
      }
    >
      <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }} bordered>
        <Descriptions.Item label="房間營收（History）">
          <Text strong>{`$ ${fmtMoney(c.revenue)}`}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="售出房晚">{fmtInt(c.sold_rooms)}</Descriptions.Item>
        <Descriptions.Item label="計算可售房晚">{fmtInt(c.available_rooms)}</Descriptions.Item>
        <Descriptions.Item label="加權 ADR">
          <Text strong style={{ color: ACCENT }}>{`$ ${fmtMoney(c.adr)}`}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="加權住房率">
          <Text strong style={{ color: GREEN }}>{fmtPct(c.occupancy)}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="加權 RevPAR">
          <Text strong style={{ color: ORANGE }}>{`$ ${fmtMoney(c.revpar)}`}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="實體房晚">{fmtInt(c.inventory_rooms)}</Descriptions.Item>
        <Descriptions.Item label="OOO 房晚">{fmtInt(c.ooo_rooms)}</Descriptions.Item>
        <Descriptions.Item label="資料天數">{`${fmtInt(c.days)} 天`}</Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 10 }}>
        {k.has_compare_data ? (
          <Space wrap size={16}>
            <Text type="secondary" style={{ fontSize: 12 }}>{`vs ${k.period.compare_label}：`}</Text>
            <Text style={{ color: trendColor(k.yoy.revenue), fontSize: 12 }}>{`營收 ${fmtYoY(k.yoy.revenue)}`}</Text>
            <Text style={{ color: trendColor(k.yoy.adr), fontSize: 12 }}>{`ADR ${fmtYoY(k.yoy.adr)}`}</Text>
            <Text style={{ color: trendColor(k.yoy.occupancy_ppt), fontSize: 12 }}>
              {`住房率 ${fmtPpt(k.yoy.occupancy_ppt)}`}
            </Text>
            <Text style={{ color: trendColor(k.yoy.revpar), fontSize: 12 }}>{`RevPAR ${fmtYoY(k.yoy.revpar)}`}</Text>
          </Space>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            尚無去年同期資料，因此不顯示 YoY。補匯入去年的 History and Forecast 後即會出現。
          </Text>
        )}
      </div>

      <Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>
        驗算：{`${fmtMoney(c.revenue)} ÷ ${fmtInt(c.sold_rooms)} = ${fmtMoney(c.adr)}（ADR）　`}
        {`${fmtInt(c.sold_rooms)} ÷ ${fmtInt(c.available_rooms)} = ${fmtPct(c.occupancy)}（住房率）　`}
        {`${fmtInt(c.inventory_rooms)} − ${fmtInt(c.ooo_rooms)} = ${fmtInt(c.available_rooms)}（可售房晚）`}
      </Text>
    </Card>
  )
}

const LiveCoverage: React.FC<{ data: OperaDashboard | null; loading: boolean }> = ({ data, loading }) => {
  if (loading) return <Card size="small" style={{ marginBottom: 12 }}><Spin /></Card>
  const s = data?.status
  if (!s || !s.has_data) {
    return <Empty description="尚未匯入任何資料" style={{ margin: '12px 0' }} />
  }
  const rows = Object.entries(s.coverage_by_year)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([year, m]) => ({ year, ...m }))
  return (
    <Card size="small" style={{ marginBottom: 12, borderLeft: `3px solid ${ACCENT}`, background: '#f9fbff' }}>
      <Descriptions size="small" column={{ xs: 1, md: 3 }} bordered style={{ marginBottom: 12 }}>
        <Descriptions.Item label="Departure（住宿明細）">
          {s.departure.start ? `${s.departure.start} ～ ${s.departure.end}（${fmtInt(s.departure.rows)} 筆）` : EMPTY}
        </Descriptions.Item>
        <Descriptions.Item label="History（實績）">
          {s.history.start ? `${s.history.start} ～ ${s.history.end}（${fmtInt(s.history.rows)} 天）` : EMPTY}
        </Descriptions.Item>
        <Descriptions.Item label="Forecast（預測）">
          {s.forecast.start ? `${s.forecast.start} ～ ${s.forecast.end}（${fmtInt(s.forecast.rows)} 天）` : EMPTY}
        </Descriptions.Item>
      </Descriptions>
      <Table
        size="small"
        rowKey="year"
        pagination={false}
        dataSource={rows}
        columns={[
          { title: '年度', dataIndex: 'year', width: 90 },
          {
            title: 'Departure（筆）', dataIndex: 'Departure', align: 'right',
            render: (v?: number) => (v ? fmtInt(v) : <Tag>無</Tag>),
          },
          {
            title: 'History（天）', dataIndex: 'History', align: 'right',
            render: (v?: number) => (v ? fmtInt(v) : <Tag color="orange">缺</Tag>),
          },
          {
            title: 'Forecast（天）', dataIndex: 'Forecast', align: 'right',
            render: (v?: number) => (v ? fmtInt(v) : <Tag>無</Tag>),
          },
        ]}
      />
      {s.missing_history_years.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginTop: 12 }}
          message={`${s.missing_history_years.join('、')} 年度缺少 History and Forecast`}
          description="這些年度只有 Departure 資料，無法計算營收、ADR、住房率，也做不出 YoY 比較。"
        />
      )}
    </Card>
  )
}

// ── 區塊渲染 ─────────────────────────────────────────────────────────────────

interface BlockProps {
  block: Block
  keyword: string
  dashboard: OperaDashboard | null
  loading: boolean
}

const BlockView: React.FC<BlockProps> = ({ block, keyword, dashboard, loading }) => {
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
        <div
          style={{
            background: '#f6f8fa', border: '1px solid #e6ebf1', borderLeft: `3px solid ${ACCENT}`,
            borderRadius: 4, padding: '10px 14px', margin: '10px 0',
          }}
        >
          {block.items.map((it, i) => (
            <div key={i} style={{ fontFamily: 'Consolas, Monaco, monospace', fontSize: 13, lineHeight: 2 }}>
              <FunctionOutlined style={{ color: ACCENT, marginRight: 8 }} />
              {highlight(it, keyword)}
            </div>
          ))}
        </div>
      )

    case 'note':
      return (
        <Alert
          type="info"
          showIcon
          icon={<BulbOutlined />}
          style={{ margin: '10px 0' }}
          message={<span style={{ lineHeight: 1.9 }}>{renderInline(block.text, keyword)}</span>}
        />
      )

    case 'caution':
      return (
        <Alert
          type="warning"
          showIcon
          icon={<ExclamationCircleOutlined />}
          style={{ margin: '10px 0' }}
          message={<span style={{ lineHeight: 1.9 }}>{renderInline(block.text, keyword)}</span>}
        />
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
            dataSource={block.rows.map((r, i) => ({ __i: i, ...Object.fromEntries(r.map((c, j) => [`c${j}`, c])) }))}
            columns={block.head.map((h, j) => ({
              title: h,
              dataIndex: `c${j}`,
              width: j === 0 ? 200 : undefined,
              render: (v: string) => {
                // 對照表的狀態欄自動上色
                const meta = Object.values(STATUS_META).find((m) => m.label === v)
                if (meta) return <Tag color={meta.color}>{v}</Tag>
                return <span style={{ lineHeight: 1.8 }}>{renderInline(v || EMPTY, keyword)}</span>
              },
            }))}
          />
        </div>
      )

    case 'live':
      return block.kind === 'baseline'
        ? <LiveBaseline data={dashboard} loading={loading} />
        : <LiveCoverage data={dashboard} loading={loading} />

    default:
      return null
  }
}

// ── 章節 ─────────────────────────────────────────────────────────────────────

const SubSectionView: React.FC<{
  sub: SubSection
  keyword: string
  dashboard: OperaDashboard | null
  loading: boolean
}> = ({ sub, keyword, dashboard, loading }) => {
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
          <Button
            size="small"
            type="link"
            icon={<ArrowRightOutlined />}
            onClick={() => navigate(sub.route!)}
          >
            前往此功能
          </Button>
        )}
      </Space>

      {sub.gap && (
        <Alert
          type={sub.status === 'planned' ? 'info' : 'warning'}
          showIcon
          banner
          style={{ marginBottom: 10 }}
          message={<span style={{ fontSize: 13 }}>{renderInline(sub.gap, keyword)}</span>}
        />
      )}

      {sub.blocks.map((b, i) => (
        <BlockView key={i} block={b} keyword={keyword} dashboard={dashboard} loading={loading} />
      ))}
    </div>
  )
}

// ── 主頁面 ───────────────────────────────────────────────────────────────────

const OperaManualPage: React.FC = () => {
  const [keyword, setKeyword] = useState('')
  const [onlyTodo, setOnlyTodo] = useState(false)
  const [dashboard, setDashboard] = useState<OperaDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    (async () => {
      try {
        setDashboard(await fetchOperaDashboard())
      } catch (e: any) {
        // 手冊本身不依賴資料；讀不到就只有「即時」區塊顯示空狀態
        message.warning('無法讀取目前基準值，手冊其餘內容不受影響')
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  // ── 篩選：搜尋 + 只看未實作 ──────────────────────────────────────────────
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
              <Tag
                color={STATUS_META[sub.status].color}
                style={{ marginLeft: 4, transform: 'scale(0.85)' }}
              >
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
              placeholder="搜尋手冊內容（例如 ADR、可售房晚、OOO）"
              style={{ width: 300 }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <Tooltip title="只顯示「規劃中」與「部分實作」的章節，方便挑下一步要補什麼">
              <Space size={6}>
                <Switch size="small" checked={onlyTodo} onChange={setOnlyTodo} />
                <Text style={{ fontSize: 13 }}>只看待開發</Text>
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
            {`${MANUAL_META.basedOn}。標示「規劃中」的章節是 Excel 版有、Portal 版尚未實作的功能，`}
            內容保留作為後續開發的規格參考；完整差異見第 8 章。
          </Text>
        }
      />

      {(keyword || onlyTodo) && (
        <Alert
          // 「只看待開發」但沒有任何待開發章節時，是好消息不是錯誤，所以用 success
          type={shownSubs > 0 || (onlyTodo && !keyword) ? 'success' : 'warning'}
          showIcon
          style={{ marginBottom: 16 }}
          message={
            shownSubs > 0
              ? `符合條件的章節：${shownSubs} / ${totalSubs}`
              : onlyTodo && !keyword
                ? '目前沒有「規劃中」或「部分實作」的章節'
                : `找不到符合「${keyword}」的章節`
          }
          description={
            shownSubs === 0 && onlyTodo && !keyword
              ? '原 Excel 版手冊的 21 張工作表已全部在 Portal 實作完畢（2026-08-04）。日後新增規格時，這個開關可以繼續用來挑出待開發項目。'
              : undefined
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
            並用 alignSelf: flex-start 讓 Col 不被 Row 拉長 —— 否則 sticky 沒有
            可移動的空間就不會生效。Anchor 本身維持 affix={false}，避免雙重固定。 */}
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
              <Anchor
                affix={false}
                offsetTop={STICKY_TOP}
                getContainer={() => window}
                items={anchorItems}
              />
            )}
          </Card>
        </Col>

        {/* ── 右側內容 ─────────────────────────────────────────────────── */}
        <Col xs={24} lg={18} xl={19}>
          <div ref={contentRef}>
            {filtered.length === 0 ? (
              <Card><Empty description="沒有符合條件的章節" /></Card>
            ) : (
              filtered.map((sec) => (
                <Card
                  key={sec.id}
                  id={sec.id}
                  style={{ marginBottom: 16, scrollMarginTop: STICKY_TOP }}
                  title={<Text strong style={{ fontSize: 16, color: BRAND }}>{highlight(sec.title, keyword)}</Text>}
                >
                  {sec.intro && (
                    <Paragraph type="secondary" style={{ lineHeight: 1.9 }}>
                      {renderInline(sec.intro, keyword)}
                    </Paragraph>
                  )}
                  {sec.subs.map((sub) => (
                    <SubSectionView
                      key={sub.id}
                      sub={sub}
                      keyword={keyword}
                      dashboard={dashboard}
                      loading={loading}
                    />
                  ))}
                </Card>
              ))
            )}
          </div>
        </Col>
      </Row>

      <Card size="small" style={{ marginTop: 8, background: '#fafafa' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          這份報表的核心不是產出更多表，而是建立一致的量、價、庫存與住客口徑。
          管理上先用加權 ADR、加權住房率與加權 RevPAR 確認全貌，再用四象限與異常清單找原因；
          最後才回到通路、住客、房型與公司結構制定行動。
        </Text>
      </Card>

      <BackToTop />
    </div>
  )
}

export default OperaManualPage
