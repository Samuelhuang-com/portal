/**
 * 靜態頁面管理
 * 列出 portal/docs/ 下的 HTML / PDF / MD 靜態說明文件，
 * 點擊後在右側預覽：
 *   .html / .htm → iframe
 *   .pdf         → iframe
 *   .md          → Markdown Viewer（react-markdown）
 */
import { useState, useEffect } from 'react'
import {
  Typography, Breadcrumb, List, Button, Spin, Alert, Empty, Tag,
} from 'antd'
import {
  HomeOutlined, FileTextOutlined, LinkOutlined, ReloadOutlined,
  FileMarkdownOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchStaticPages } from '@/api/staticPages'
import type { StaticPageItem } from '@/api/staticPages'

const { Title, Text } = Typography

// ── Markdown 樣式（GitHub 風格簡化版）────────────────────────────────────────
const MD_STYLE: React.CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '24px 32px',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  fontSize: 14,
  lineHeight: 1.8,
  color: '#24292f',
}

// ── 工具函式 ──────────────────────────────────────────────────────────────────
function getExt(filename: string) {
  return filename.split('.').pop()?.toLowerCase() ?? ''
}

function isMd(filename: string) {
  return getExt(filename) === 'md'
}

function extTag(filename: string) {
  const ext = getExt(filename)
  if (ext === 'pdf') return <Tag color="red">PDF</Tag>
  if (ext === 'md')  return <Tag color="green"><FileMarkdownOutlined /> MD</Tag>
  return <Tag color="blue">HTML</Tag>
}

// ── Markdown Viewer ───────────────────────────────────────────────────────────
function MarkdownViewer({ url }: { url: string }) {
  const [content, setContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(false)
    setContent(null)
    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.text()
      })
      .then(text => setContent(text))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [url])

  if (loading) return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Spin tip="載入文件中…" />
    </div>
  )
  if (error) return (
    <div style={{ padding: 24 }}>
      <Alert type="error" message="無法載入 Markdown 文件" showIcon />
    </div>
  )

  return (
    <div style={MD_STYLE}>
      <style>{`
        .md-body h1,
        .md-body h2,
        .md-body h3,
        .md-body h4 { color: #1B3A5C; font-weight: 600; margin: 1.2em 0 0.4em; }
        .md-body h1 { font-size: 1.8em; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3em; }
        .md-body h2 { font-size: 1.4em; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.2em; }
        .md-body h3 { font-size: 1.15em; }
        .md-body p  { margin: 0.6em 0; }
        .md-body ul,
        .md-body ol { padding-left: 1.8em; margin: 0.4em 0; }
        .md-body li { margin: 0.2em 0; }
        .md-body code {
          background: #f6f8fa; border: 1px solid #e1e4e8;
          border-radius: 4px; padding: 0.15em 0.4em;
          font-family: "SFMono-Regular", Consolas, monospace; font-size: 0.88em;
        }
        .md-body pre {
          background: #f6f8fa; border: 1px solid #e1e4e8;
          border-radius: 6px; padding: 14px 16px; overflow-x: auto;
        }
        .md-body pre code { background: none; border: none; padding: 0; }
        .md-body blockquote {
          border-left: 4px solid #4BA8E8; margin: 0.6em 0;
          padding: 0.4em 1em; background: #f0f8ff; border-radius: 0 4px 4px 0;
          color: #444;
        }
        .md-body table { border-collapse: collapse; width: 100%; margin: 0.8em 0; }
        .md-body th,
        .md-body td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
        .md-body th { background: #f6f8fa; font-weight: 600; }
        .md-body tr:nth-child(even) td { background: #fafafa; }
        .md-body a { color: #4BA8E8; text-decoration: none; }
        .md-body a:hover { text-decoration: underline; }
        .md-body hr { border: none; border-top: 1px solid #e5e7eb; margin: 1.2em 0; }
        .md-body img { max-width: 100%; border-radius: 4px; }
      `}</style>
      <div className="md-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content!}
        </ReactMarkdown>
      </div>
    </div>
  )
}

// ── 主頁面元件 ────────────────────────────────────────────────────────────────
export default function StaticPagesPage() {
  const [pages, setPages]       = useState<StaticPageItem[]>([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string | null>(null)
  const [selected, setSelected] = useState<StaticPageItem | null>(null)

  const loadPages = () => {
    setLoading(true)
    setError(null)
    fetchStaticPages()
      .then((data) => {
        setPages(data)
        if (data.length > 0 && !selected) {
          setSelected(data[0])
        }
      })
      .catch(() => setError('無法取得靜態頁面清單，請確認後端服務正常'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadPages()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* ── Breadcrumb ── */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { title: <HomeOutlined /> },
          { title: '系統設定' },
          { title: '靜態頁面' },
        ]}
      />

      {/* ── 標題列 ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>
          靜態頁面管理
        </Title>
        <Button
          size="small"
          icon={<ReloadOutlined />}
          onClick={loadPages}
          loading={loading}
        >
          重新整理
        </Button>
        <Text type="secondary" style={{ fontSize: 12 }}>
          管理 portal/docs/ 目錄下的 HTML / PDF / MD 說明文件
        </Text>
      </div>

      {error && (
        <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />
      )}

      {/* ── 主體：左側清單 + 右側預覽 ── */}
      <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 200px)', minHeight: 500 }}>

        {/* ── 左側：檔案清單 ── */}
        <div style={{
          width: 280,
          flexShrink: 0,
          background: '#fff',
          borderRadius: 8,
          border: '1px solid #e5e7eb',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{
            padding: '10px 14px',
            borderBottom: '1px solid #f0f0f0',
            background: '#f8fafc',
            fontSize: 12,
            color: '#667085',
            fontWeight: 600,
          }}>
            <FileTextOutlined style={{ marginRight: 6 }} />
            文件清單（{pages.length} 個）
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {loading ? (
              <div style={{ padding: 24, textAlign: 'center' }}>
                <Spin size="small" />
              </div>
            ) : pages.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="docs/ 目錄下尚無可瀏覽的檔案"
                style={{ padding: '24px 12px' }}
              />
            ) : (
              <List
                dataSource={pages}
                renderItem={(item) => {
                  const isActive = selected?.filename === item.filename
                  return (
                    <List.Item
                      key={item.filename}
                      style={{
                        padding: '10px 14px',
                        cursor: 'pointer',
                        background: isActive ? '#eff6ff' : 'transparent',
                        borderLeft: isActive ? '3px solid #1B3A5C' : '3px solid transparent',
                        transition: 'all 0.15s',
                      }}
                      onClick={() => setSelected(item)}
                    >
                      <div style={{ width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                          {extTag(item.filename)}
                        </div>
                        <Text
                          style={{
                            fontSize: 12,
                            color: isActive ? '#1B3A5C' : '#374151',
                            fontWeight: isActive ? 600 : 400,
                            wordBreak: 'break-all',
                            lineHeight: 1.5,
                          }}
                        >
                          {item.filename}
                        </Text>
                      </div>
                    </List.Item>
                  )
                }}
              />
            )}
          </div>
        </div>

        {/* ── 右側：預覽區 ── */}
        <div style={{
          flex: 1,
          background: '#fff',
          borderRadius: 8,
          border: '1px solid #e5e7eb',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}>
          {/* 預覽標題列 */}
          <div style={{
            padding: '10px 14px',
            borderBottom: '1px solid #f0f0f0',
            background: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 12,
            color: '#667085',
            flexShrink: 0,
          }}>
            {selected && isMd(selected.filename)
              ? <FileMarkdownOutlined />
              : <FileTextOutlined />
            }
            <Text style={{ fontSize: 12, flex: 1, color: '#374151' }}>
              {selected ? selected.filename : '請從左側選擇文件'}
            </Text>
            {selected && (
              <Button
                type="link"
                size="small"
                icon={<LinkOutlined />}
                href={selected.url}
                target="_blank"
                style={{ fontSize: 12, padding: 0 }}
              >
                另開新頁
              </Button>
            )}
          </div>

          {/* 預覽內容 */}
          {selected ? (
            isMd(selected.filename) ? (
              <MarkdownViewer key={selected.url} url={selected.url} />
            ) : (
              <iframe
                key={selected.url}
                src={selected.url}
                style={{ flex: 1, border: 'none', width: '100%' }}
                title={selected.filename}
              />
            )
          ) : (
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="從左側選擇文件以預覽"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
