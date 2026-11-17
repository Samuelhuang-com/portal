/**
 * 庫存管理 — 使用須知（/stock/manual）
 *
 * 內容在 content.ts，這裡只負責版面：目錄、全文搜尋、區塊渲染、流程圖。
 *
 * 版面骨架比照 `pages/CyclePurchase/Manual`（複製而非引用，兩個模組彼此獨立）。
 * 差異：流程圖改用 `flow` 區塊直接在頁面上畫（FlowView），不經 Archify／docs-static iframe。
 *
 * 權限：開放給所有庫存使用者（MainLayout 用 permissionKeys OR 涵蓋全部庫存權限），
 *    不另立 permission key —— 須知是教人怎麼用的，卡權限會讓最需要它的人看不到（比照週採手冊）。
 */
import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Anchor, Button, Card, Col, Empty, Input, Row, Space, Table, Tag, Typography,
} from 'antd'
import {
  ArrowRightOutlined, BookOutlined, ExclamationCircleOutlined,
  InfoCircleOutlined, RightOutlined, RollbackOutlined, SearchOutlined, StopOutlined,
} from '@ant-design/icons'

import {
  MANUAL, MANUAL_META, subSectionText,
  type Block, type FlowStep, type Section, type SubSection,
} from './content'

const { Title, Text, Paragraph } = Typography

/** CLAUDE.md 受保護色：品牌主色／輔色／異常紅。刻意在本檔宣告而非跨模組 import。 */
const BRAND = '#1B3A5C'
const ACCENT = '#4BA8E8'
const RED = '#e74c3c'

/** Portal Header 為 sticky、實際高度 64px，再留 12px 空隙 */
const STICKY_TOP = 76

/** 流程圖框的配色（一般／完成／注意／終止） */
const TONE: Record<NonNullable<FlowStep['tone']>, { bg: string; border: string; head: string }> = {
  normal: { bg: '#ffffff', border: '#c9d6e3', head: BRAND },
  ok:     { bg: '#f6ffed', border: '#95de64', head: '#389e0d' },
  warn:   { bg: '#fffbe6', border: '#ffd666', head: '#d48806' },
  stop:   { bg: '#f5f5f5', border: '#d9d9d9', head: '#8c8c8c' },
}

// ── 行內樣式：**粗體** 與 `等寬` ─────────────────────────────────────────────
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

function highlight(text: string, keyword: string): React.ReactNode {
  if (!keyword) return text
  const idx = text.toLowerCase().indexOf(keyword.toLowerCase())
  if (idx < 0) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: '#fff1b8', padding: '0 2px' }}>
        {text.slice(idx, idx + keyword.length)}
      </mark>
      {text.slice(idx + keyword.length)}
    </>
  )
}

// ── 流程圖 ───────────────────────────────────────────────────────────────────

const FlowBox: React.FC<{ step: FlowStep; keyword: string }> = ({ step, keyword }) => {
  const c = TONE[step.tone ?? 'normal']
  return (
    <div style={{ width: 168, display: 'flex', flexDirection: 'column', alignItems: 'stretch' }}>
      <div style={{ height: 22, textAlign: 'center' }}>
        {step.who && (
          <Tag style={{ margin: 0, fontSize: 11, color: c.head, borderColor: c.border, background: '#fff' }}>
            {highlight(step.who, keyword)}
          </Tag>
        )}
      </div>
      <div style={{
        background: c.bg, border: `1.5px solid ${c.border}`, borderRadius: 8,
        padding: '8px 10px', minHeight: 64, marginTop: 4,
        display: 'flex', flexDirection: 'column', justifyContent: 'center', textAlign: 'center',
      }}>
        <Text strong style={{ fontSize: 13, color: c.head }}>{highlight(step.label, keyword)}</Text>
        {step.sub && (
          <Text type="secondary" style={{ fontSize: 11, lineHeight: 1.4, marginTop: 2 }}>
            {highlight(step.sub, keyword)}
          </Text>
        )}
      </div>
      {step.alt && (
        <div style={{
          marginTop: 6, border: `1px dashed ${RED}`, borderRadius: 6, padding: '4px 6px',
          fontSize: 11, color: RED, lineHeight: 1.4, background: '#fff5f5',
        }}>
          <RollbackOutlined style={{ marginInlineEnd: 4 }} />
          {highlight(step.alt, keyword)}
        </div>
      )}
    </div>
  )
}

const FlowView: React.FC<{ block: Extract<Block, { t: 'flow' }>; keyword: string }> = ({ block, keyword }) => (
  <div style={{
    border: '1px solid #e0e6ed', borderRadius: 8, padding: '12px 14px',
    marginBottom: 10, background: '#fafcff',
  }}>
    <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 8 }}>
      {highlight(block.title, keyword)}
    </Text>
    {block.rows.map((row, ri) => (
      <div key={ri} style={{ marginBottom: ri < block.rows.length - 1 ? 14 : 0 }}>
        {row.name && (
          <div style={{
            fontSize: 12, fontWeight: 600, color: BRAND, marginBottom: 4,
            borderInlineStart: `3px solid ${ACCENT}`, paddingInlineStart: 6,
          }}>
            {highlight(row.name, keyword)}
          </div>
        )}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', rowGap: 10 }}>
          {row.steps.map((s, si) => (
            <React.Fragment key={si}>
              <FlowBox step={s} keyword={keyword} />
              {si < row.steps.length - 1 && (
                <div style={{ width: 26, height: 90, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <RightOutlined style={{ color: ACCENT, fontSize: 14 }} />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    ))}
    {block.caption && (
      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 10 }}>
        {renderInline(block.caption, keyword)}
      </Text>
    )}
  </div>
)

// ── 區塊渲染 ─────────────────────────────────────────────────────────────────

const BlockView: React.FC<{ block: Block; keyword: string }> = ({ block, keyword }) => {
  switch (block.t) {
    case 'p':
      return <Paragraph style={{ marginBottom: 10 }}>{renderInline(block.text, keyword)}</Paragraph>

    case 'ul':
      return (
        <ul style={{ marginBottom: 10, paddingInlineStart: 22 }}>
          {block.items.map((it, i) => <li key={i} style={{ marginBottom: 4 }}>{renderInline(it, keyword)}</li>)}
        </ul>
      )

    case 'ol':
      return (
        <ol style={{ marginBottom: 10, paddingInlineStart: 22 }}>
          {block.items.map((it, i) => <li key={i} style={{ marginBottom: 4 }}>{renderInline(it, keyword)}</li>)}
        </ol>
      )

    case 'note':
      return (
        <Alert type="info" showIcon icon={<InfoCircleOutlined />} style={{ marginBottom: 10 }}
          message={<span style={{ fontSize: 13 }}>{renderInline(block.text, keyword)}</span>} />
      )

    case 'caution':
      return (
        <Alert type="warning" showIcon icon={<ExclamationCircleOutlined />} style={{ marginBottom: 10 }}
          message={<span style={{ fontSize: 13 }}>{renderInline(block.text, keyword)}</span>} />
      )

    case 'wrong':
      // 常見誤解：用受保護色 #fff5f5 / #ffccc7（CLAUDE.md 保護色）
      return (
        <div style={{
          background: '#fff5f5', border: '1px solid #ffccc7', borderRadius: 6,
          padding: '8px 12px', marginBottom: 10, fontSize: 13,
        }}>
          <StopOutlined style={{ color: RED, marginInlineEnd: 6 }} />
          {renderInline(block.text, keyword)}
        </div>
      )

    case 'table':
      return (
        <>
          <Table
            size="small"
            style={{ marginBottom: 10 }}
            pagination={false}
            rowKey="_k"
            dataSource={block.rows.map((r, i) => {
              const o: Record<string, string | number> = { _k: i }
              r.forEach((c, j) => { o[`c${j}`] = c })
              return o
            })}
            columns={block.head.map((h, j) => ({
              title: h || ' ',
              dataIndex: `c${j}`,
              width: j === 0 ? 160 : undefined,
              render: (v: string) => <span style={{ fontSize: 13 }}>{renderInline(v ?? '', keyword)}</span>,
            }))}
          />
          {block.caption && <Text type="secondary" style={{ fontSize: 12 }}>{renderInline(block.caption, keyword)}</Text>}
        </>
      )

    case 'flow':
      return <FlowView block={block} keyword={keyword} />

    default:
      return null
  }
}

// ── 主頁面 ───────────────────────────────────────────────────────────────────

const StockManualPage: React.FC = () => {
  const navigate = useNavigate()
  const [keyword, setKeyword] = useState('')

  /** 搜尋：只保留有命中的小節；章節若整章沒命中就整章不顯示 */
  const filtered: Section[] = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    if (!kw) return MANUAL
    return MANUAL
      .map((sec) => ({ ...sec, subs: sec.subs.filter((sub) => subSectionText(sub).toLowerCase().includes(kw)) }))
      .filter((sec) => sec.subs.length > 0 || sec.title.toLowerCase().includes(kw))
  }, [keyword])

  const hitCount = useMemo(() => filtered.reduce((n, s) => n + s.subs.length, 0), [filtered])

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
        <Space size={12} wrap>
          <BookOutlined style={{ color: ACCENT, fontSize: 20 }} />
          <Title level={4} style={{ margin: 0, color: BRAND }}>{MANUAL_META.title}</Title>
          <Tag>v{MANUAL_META.version}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>更新於 {MANUAL_META.updated}</Text>
        </Space>
        <Text type="secondary" style={{ fontSize: 13 }}>{MANUAL_META.subtitle}</Text>
      </Space>

      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="讀這份須知之前，先知道這件事"
        description={<span style={{ fontSize: 13 }}>{renderInline(MANUAL_META.disclaimer, '')}</span>}
      />

      <Row gutter={16}>
        <Col xs={24} md={6}>
          <div style={{ position: 'sticky', top: STICKY_TOP }}>
            <Card size="small" title="目錄">
              <Anchor
                affix={false}
                targetOffset={STICKY_TOP}
                items={filtered.map((sec) => ({
                  key: sec.id,
                  href: `#${sec.id}`,
                  title: <span style={{ fontSize: 13 }}>{sec.title}</span>,
                }))}
              />
            </Card>
          </div>
        </Col>

        <Col xs={24} md={18}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Input
              allowClear
              size="large"
              prefix={<SearchOutlined />}
              placeholder="搜尋須知內容，例如「月結」「退料」「盲盤」"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            {keyword && (
              <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
                命中 {hitCount} 個小節
              </Text>
            )}
          </Card>

          {filtered.length === 0 ? (
            <Empty description={`找不到與「${keyword}」相關的內容`} />
          ) : (
            filtered.map((sec) => (
              <Card
                key={sec.id}
                id={sec.id}
                size="small"
                style={{ marginBottom: 16, scrollMarginTop: STICKY_TOP }}
                title={<Text strong style={{ color: BRAND }}>{sec.title}</Text>}
              >
                {sec.intro && (
                  <Paragraph type="secondary" style={{ fontSize: 13 }}>{renderInline(sec.intro, keyword)}</Paragraph>
                )}
                {sec.subs.map((sub: SubSection) => (
                  <div key={sub.id} id={sub.id} style={{ marginBottom: 18 }}>
                    <Space size={8} wrap style={{ marginBottom: 6 }}>
                      <Text strong style={{ fontSize: 14 }}>{highlight(sub.title, keyword)}</Text>
                      {sub.route && (
                        <Button size="small" type="link" icon={<ArrowRightOutlined />}
                          onClick={() => navigate(sub.route!)} style={{ color: ACCENT, paddingInline: 4 }}>
                          前往此功能
                        </Button>
                      )}
                    </Space>
                    {sub.blocks.map((b, i) => <BlockView key={i} block={b} keyword={keyword} />)}
                  </div>
                ))}
              </Card>
            ))
          )}

          <Text type="secondary" style={{ fontSize: 12 }}>
            完整規格：<Text code style={{ fontSize: 11 }}>docs/SPEC_stock_management.md</Text>
          </Text>
        </Col>
      </Row>
    </div>
  )
}

export default StockManualPage
