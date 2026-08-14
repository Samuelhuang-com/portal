/**
 * 合約管理 — 使用手冊（/contract/manual）
 *
 * 內容在 content.ts，這裡只負責版面：目錄、全文搜尋、區塊渲染。
 *
 * ⚠️ 刻意**不重用** `pages/CyclePurchase/Manual`、`pages/Opera/Manual` 等其他模組的
 *    手冊頁面 —— 各模組彼此獨立，重用會讓其中一邊的改動波及另一邊。
 *    版面骨架與 CyclePurchase 版相同（複製而非引用），是刻意的重複。
 *
 * 權限：比照合約模組其他選單項目，掛 `contract_view`（見 MainLayout.tsx）——
 *    手冊是教人怎麼用的，不另立新的 permission key。
 */
import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Anchor, Button, Card, Col, Empty, Input, Row, Space, Table, Tag, Typography,
} from 'antd'
import {
  ArrowRightOutlined, BookOutlined, ExclamationCircleOutlined,
  InfoCircleOutlined, SearchOutlined, StopOutlined,
} from '@ant-design/icons'

import {
  MANUAL, MANUAL_META, subSectionText,
  type Block, type Section, type SubSection,
} from './content'

const { Title, Text, Paragraph } = Typography

/** CLAUDE.md 受保護色：品牌主色／輔色／異常紅。刻意在本檔宣告而非跨模組 import。 */
const BRAND = '#1B3A5C'
const ACCENT = '#4BA8E8'
const RED = '#e74c3c'

/** Portal Header 為 sticky、實際高度 64px，再留 12px 空隙 */
const STICKY_TOP = 76

// ── 行內樣式：**粗體** 與 `等寬` ─────────────────────────────────────────────
// 只用兩個最常見的 Markdown 記號就夠，不值得為此引入 markdown 套件。
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

// ── 區塊渲染 ─────────────────────────────────────────────────────────────────

const BlockView: React.FC<{ block: Block; keyword: string }> = ({ block, keyword }) => {
  switch (block.t) {
    case 'p':
      return (
        <Paragraph style={{ marginBottom: 10 }}>
          {renderInline(block.text, keyword)}
        </Paragraph>
      )

    case 'ul':
      return (
        <ul style={{ marginBottom: 10, paddingInlineStart: 22 }}>
          {block.items.map((it, i) => (
            <li key={i} style={{ marginBottom: 4 }}>{renderInline(it, keyword)}</li>
          ))}
        </ul>
      )

    case 'ol':
      return (
        <ol style={{ marginBottom: 10, paddingInlineStart: 22 }}>
          {block.items.map((it, i) => (
            <li key={i} style={{ marginBottom: 4 }}>{renderInline(it, keyword)}</li>
          ))}
        </ol>
      )

    case 'note':
      return (
        <Alert
          type="info" showIcon icon={<InfoCircleOutlined />}
          style={{ marginBottom: 10 }}
          message={<span style={{ fontSize: 13 }}>{renderInline(block.text, keyword)}</span>}
        />
      )

    case 'caution':
      return (
        <Alert
          type="warning" showIcon icon={<ExclamationCircleOutlined />}
          style={{ marginBottom: 10 }}
          message={<span style={{ fontSize: 13 }}>{renderInline(block.text, keyword)}</span>}
        />
      )

    case 'wrong':
      // 常見誤解／已知限制：用受保護色 #fff5f5 / #ffccc7（CLAUDE.md 保護色）
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
            rowKey={(_, i) => String(i)}
            dataSource={block.rows.map((r, i) => {
              const o: any = { _k: i }
              r.forEach((c, j) => { o[`c${j}`] = c })
              return o
            })}
            columns={block.head.map((h, j) => ({
              title: h || ' ',
              dataIndex: `c${j}`,
              width: j === 0 ? 180 : undefined,
              render: (v: string) => (
                <span style={{ fontSize: 13 }}>{renderInline(v ?? '', keyword)}</span>
              ),
            }))}
          />
          {block.caption && (
            <Text type="secondary" style={{ fontSize: 12 }}>{block.caption}</Text>
          )}
        </>
      )

    default:
      return null
  }
}

// ── 主頁面 ───────────────────────────────────────────────────────────────────

const ContractManualPage: React.FC = () => {
  const navigate = useNavigate()
  const [keyword, setKeyword] = useState('')

  /** 搜尋：只保留有命中的小節；章節若整章沒命中就整章不顯示 */
  const filtered: Section[] = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    if (!kw) return MANUAL
    return MANUAL
      .map((sec) => ({
        ...sec,
        subs: sec.subs.filter((sub) => subSectionText(sub).toLowerCase().includes(kw)),
      }))
      .filter((sec) => sec.subs.length > 0 || sec.title.toLowerCase().includes(kw))
  }, [keyword])

  const hitCount = useMemo(
    () => filtered.reduce((n, s) => n + s.subs.length, 0),
    [filtered],
  )

  return (
    <div style={{ padding: 24 }}>
      {/* ── 標題 ─────────────────────────────────────────────────────── */}
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
        message="讀這份手冊之前，先知道這件事"
        description={
          <span style={{ fontSize: 13 }}>{renderInline(MANUAL_META.disclaimer, '')}</span>
        }
      />

      <Row gutter={16}>
        {/* ── 左側目錄 ───────────────────────────────────────────────── */}
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

        {/* ── 右側內容 ───────────────────────────────────────────────── */}
        <Col xs={24} md={18}>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Input
              allowClear
              size="large"
              prefix={<SearchOutlined />}
              placeholder="搜尋手冊內容，例如「解約日」「費用分攤」「複製續約」"
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
                  <Paragraph type="secondary" style={{ fontSize: 13 }}>
                    {renderInline(sec.intro, keyword)}
                  </Paragraph>
                )}

                {sec.subs.map((sub: SubSection) => (
                  <div key={sub.id} id={sub.id} style={{ marginBottom: 18 }}>
                    <Space size={8} wrap style={{ marginBottom: 6 }}>
                      <Text strong style={{ fontSize: 14 }}>
                        {highlight(sub.title, keyword)}
                      </Text>
                      {sub.route && (
                        <Button
                          size="small" type="link" icon={<ArrowRightOutlined />}
                          onClick={() => navigate(sub.route!)}
                          style={{ color: ACCENT, paddingInline: 4 }}
                        >
                          前往此功能
                        </Button>
                      )}
                    </Space>
                    {sub.blocks.map((b, i) => (
                      <BlockView key={i} block={b} keyword={keyword} />
                    ))}
                  </div>
                ))}
              </Card>
            ))
          )}

          <Text type="secondary" style={{ fontSize: 12 }}>
            資料表欄位、ERD、API 端點速查等技術規格，請看 Dashboard 頁「說明指南」內嵌的
            <Text code style={{ fontSize: 11 }}>docs/contract_manual.html</Text>
            　技術手冊（跟這份使用手冊是兩份不同文件）。
          </Text>
        </Col>
      </Row>
    </div>
  )
}

export default ContractManualPage
