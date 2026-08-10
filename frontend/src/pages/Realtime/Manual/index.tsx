/**
 * 即時營運 — 使用手冊（/realtime/manual）
 *
 * 規格書：docs/SPEC_realtime_operations.md §13 階段 6
 * 內容來源：docs/MANUAL_realtime_operations.md（結構化後放在 content.ts）
 *
 * 互動功能：
 *   1. 左側目錄，點擊跳轉
 *   2. 全文搜尋：篩掉不相關小節並高亮命中字
 *   3. 對應到實際頁面的小節，標題右側有「前往此功能」按鈕
 *
 * ⚠️ 刻意**不重用** `pages/Opera/Manual/index.tsx` ——
 *    那一份有「即時抓資料庫數字」「章節實作狀態」等本模組不需要的功能（584 行），
 *    重用會把兩個模組綁在一起，違反 SPEC §1 的獨立原則。
 *    這裡只做手冊真正需要的：目錄、搜尋、渲染。
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
import { ACCENT, BRAND, ORANGE, RED } from '@/pages/Opera/components/formatters'

const { Title, Text, Paragraph } = Typography

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

const RealtimeManualPage: React.FC = () => {
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
        description={MANUAL_META.disclaimer}
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
              placeholder="搜尋手冊內容，例如「取消率」「快取」「差異」"
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
            完整版文件：<Text code style={{ fontSize: 11 }}>docs/MANUAL_realtime_operations.md</Text>
            　開發規格：<Text code style={{ fontSize: 11 }}>docs/SPEC_realtime_operations.md</Text>
          </Text>
        </Col>
      </Row>
    </div>
  )
}

export default RealtimeManualPage
