/**
 * 知識庫（LLM Wiki）主頁面
 * - 左：文章清單（SOP / Dev 分頁 + 搜尋）
 * - 右：文章 Markdown 內容顯示
 * - 浮動按鈕：AI 問答助手
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Layout,
  Menu,
  Input,
  Button,
  Tag,
  Drawer,
  Form,
  Select,
  message,
  Spin,
  Empty,
  Modal,
  Tooltip,
  Tabs,
  Space,
  Popconfirm,
  Typography,
  Badge,
  Dropdown,
  Segmented,
} from 'antd'
import type { MenuProps } from 'antd'
import {
  BookOutlined,
  SearchOutlined,
  PlusOutlined,
  RobotOutlined,
  SendOutlined,
  EditOutlined,
  DeleteOutlined,
  CodeOutlined,
  TagOutlined,
  UserOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  ExportOutlined,
  ImportOutlined,
  UnorderedListOutlined,
  ApartmentOutlined,
} from '@ant-design/icons'
import WikiGraph from './WikiGraph'
import dayjs from 'dayjs'
import {
  fetchWikiArticles,
  createWikiArticle,
  updateWikiArticle,
  deleteWikiArticle,
  askWiki,
  exportToObsidian,
  importFromObsidian,
  autoLinkArticles,
} from '@/api/wiki'
import type { ObsidianSyncResult } from '@/api/wiki'
import type { WikiArticle, WikiCategory } from '@/types/wiki'
import { useAuthStore } from '@/stores/authStore'

const { Sider, Content } = Layout
const { TextArea } = Input
const { Title, Paragraph, Text } = Typography

// ── Markdown 純文字渲染（不依賴外部套件）─────────────────────────────────────
function MarkdownRenderer({ content }: { content: string }) {
  const renderLine = (line: string, idx: number): React.ReactNode => {
    // Heading
    if (line.startsWith('### ')) return <h3 key={idx} style={{ color: '#1B3A5C', marginTop: 16, marginBottom: 8 }}>{line.slice(4)}</h3>
    if (line.startsWith('## '))  return <h2 key={idx} style={{ color: '#1B3A5C', marginTop: 20, marginBottom: 10, borderBottom: '2px solid #4BA8E8', paddingBottom: 4 }}>{line.slice(3)}</h2>
    if (line.startsWith('# '))   return <h1 key={idx} style={{ color: '#1B3A5C', marginTop: 24, marginBottom: 12 }}>{line.slice(2)}</h1>
    // Code block marker (handled in block pass)
    if (line === '') return <br key={idx} />
    // List
    if (/^[-*] /.test(line)) return <li key={idx} style={{ marginLeft: 20 }}>{inlineFormat(line.slice(2))}</li>
    if (/^\d+\. /.test(line)) return <li key={idx} style={{ marginLeft: 20, listStyleType: 'decimal' }}>{inlineFormat(line.replace(/^\d+\.\s+/, ''))}</li>
    // Blockquote
    if (line.startsWith('> ')) return <blockquote key={idx} style={{ borderLeft: '3px solid #4BA8E8', paddingLeft: 12, color: '#555', margin: '8px 0' }}>{inlineFormat(line.slice(2))}</blockquote>
    // Horizontal rule
    if (/^[-*]{3,}$/.test(line.trim())) return <hr key={idx} style={{ border: 'none', borderTop: '1px solid #e0e0e0', margin: '16px 0' }} />
    return <p key={idx} style={{ margin: '6px 0', lineHeight: 1.8 }}>{inlineFormat(line)}</p>
  }

  function inlineFormat(text: string): React.ReactNode {
    // Bold + italic
    const parts: React.ReactNode[] = []
    const regex = /(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g
    let last = 0, match
    while ((match = regex.exec(text)) !== null) {
      if (match.index > last) parts.push(text.slice(last, match.index))
      if (match[2]) parts.push(<strong key={match.index}><em>{match[2]}</em></strong>)
      else if (match[3]) parts.push(<strong key={match.index}>{match[3]}</strong>)
      else if (match[4]) parts.push(<em key={match.index}>{match[4]}</em>)
      else if (match[5]) parts.push(<code key={match.index} style={{ background: '#f0f4f8', padding: '1px 5px', borderRadius: 3, fontSize: '0.9em', fontFamily: 'monospace' }}>{match[5]}</code>)
      last = match.index + match[0].length
    }
    if (last < text.length) parts.push(text.slice(last))
    return parts.length > 0 ? <>{parts}</> : text
  }

  // Block-level pass: handle fenced code blocks
  const lines = content.split('\n')
  const elements: React.ReactNode[] = []
  let inCode = false
  let codeLang = ''
  let codeLines: string[] = []

  lines.forEach((line, idx) => {
    if (line.startsWith('```')) {
      if (!inCode) {
        inCode = true
        codeLang = line.slice(3).trim()
        codeLines = []
      } else {
        elements.push(
          <pre key={`code-${idx}`} style={{ background: '#1B3A5C', color: '#e8f4f8', padding: '12px 16px', borderRadius: 8, overflowX: 'auto', fontSize: 13, lineHeight: 1.6, margin: '12px 0' }}>
            {codeLang && <div style={{ color: '#4BA8E8', fontSize: 11, marginBottom: 6, textTransform: 'uppercase' }}>{codeLang}</div>}
            <code>{codeLines.join('\n')}</code>
          </pre>
        )
        inCode = false
        codeLines = []
        codeLang = ''
      }
      return
    }
    if (inCode) {
      codeLines.push(line)
      return
    }
    elements.push(renderLine(line, idx))
  })

  return (
    <div style={{ fontFamily: '-apple-system, "Noto Sans TC", sans-serif', fontSize: 15, color: '#333' }}>
      {elements}
    </div>
  )
}

// ── 分類設定 ───────────────────────────────────────────────────────────────────
const CATEGORIES: { key: WikiCategory; label: string; color: string; icon: React.ReactNode }[] = [
  { key: 'sop',  label: '員工 SOP',    color: '#1B3A5C', icon: <BookOutlined /> },
  { key: 'dev',  label: '開發者 Wiki', color: '#4BA8E8', icon: <CodeOutlined /> },
]

const TAGS_SUGGESTIONS: Record<string, string[]> = {
  sop: ['設備保養', '緊急處理', '日常作業', '安全規範', '清潔', '巡檢', '報修', '電氣', '空調', '消防'],
  dev: ['FastAPI', 'React', 'SQLite', 'Ragic', 'API設計', '資料庫', '部署', '除錯', '架構', '前端'],
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function WikiPage() {
  const user = useAuthStore((s) => s.user)

  // ── 視圖模式 ─────────────────────────────────────────────────────────────────
  const [viewMode, setViewMode] = useState<'list' | 'graph'>('list')

  // ── 文章清單狀態 ────────────────────────────────────────────────────────────
  const [activeCategory, setActiveCategory] = useState<'sop' | 'dev'>('sop')
  const [articles, setArticles] = useState<WikiArticle[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searchQ, setSearchQ] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  // ── 新增 / 編輯 Drawer ──────────────────────────────────────────────────────
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingArticle, setEditingArticle] = useState<WikiArticle | null>(null)
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)

  // ── Obsidian 同步 ────────────────────────────────────────────────────────────
  const [syncResultOpen, setSyncResultOpen] = useState(false)
  const [syncResult, setSyncResult] = useState<ObsidianSyncResult | null>(null)
  const [syncType, setSyncType] = useState<'export' | 'import'>('export')

  const handleObsidianSync = async (type: 'export' | 'import') => {
    setSyncing(true)
    setSyncType(type)
    try {
      const result = type === 'export' ? await exportToObsidian() : await importFromObsidian()
      setSyncResult(result)
      setSyncResultOpen(true)
      if (type === 'import') loadArticles()   // 匯入後刷新清單
    } catch (err: any) {
      message.error(`同步失敗：${err?.response?.data?.detail || err?.message || '未知錯誤'}`)
    } finally {
      setSyncing(false)
    }
  }

  const handleAutoLink = async () => {
    setSyncing(true)
    try {
      const result = await autoLinkArticles(false)
      message.success(`自動補連結完成：${result.updated} 篇已更新`)
      loadArticles()
    } catch (err: any) {
      message.error(`自動補連結失敗：${err?.response?.data?.detail || err?.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const syncMenuItems: MenuProps['items'] = [
    {
      key: 'auto-link',
      icon: <ApartmentOutlined />,
      label: '自動補充文章 [[連結]]',
      onClick: handleAutoLink,
    },
    { type: 'divider' },
    {
      key: 'export',
      icon: <ExportOutlined />,
      label: '匯出到 Obsidian（DB → .md）',
      onClick: () => handleObsidianSync('export'),
    },
    {
      key: 'import',
      icon: <ImportOutlined />,
      label: '從 Obsidian 匯入（.md → DB）',
      onClick: () => handleObsidianSync('import'),
    },
  ]

  // ── AI 問答 ──────────────────────────────────────────────────────────────────
  const [aiOpen, setAiOpen] = useState(false)
  const [aiQuestion, setAiQuestion] = useState('')
  const [aiAnswer, setAiAnswer] = useState('')
  const [aiSources, setAiSources] = useState<WikiArticle[]>([])
  const [aiLoading, setAiLoading] = useState(false)
  const [aiHistory, setAiHistory] = useState<{ q: string; a: string }[]>([])
  const aiEndRef = useRef<HTMLDivElement>(null)

  // ── 載入文章 ────────────────────────────────────────────────────────────────
  const loadArticles = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchWikiArticles({ category: activeCategory, q: searchQ, per_page: 50 })
      setArticles(res.items)
      setTotal(res.total)
      if (res.items.length > 0 && !selectedId) {
        setSelectedId(res.items[0].id)
      } else if (res.items.length === 0) {
        setSelectedId(null)
      }
    } catch {
      message.error('載入失敗')
    } finally {
      setLoading(false)
    }
  }, [activeCategory, searchQ])

  useEffect(() => { loadArticles() }, [loadArticles])

  // 切換分類時清空選取
  useEffect(() => { setSelectedId(null) }, [activeCategory])

  // ── 選取文章 ────────────────────────────────────────────────────────────────
  const selectedArticle = articles.find((a) => a.id === selectedId) ?? null

  // ── 新增 / 編輯 ──────────────────────────────────────────────────────────────
  const openCreate = () => {
    setEditingArticle(null)
    form.resetFields()
    form.setFieldsValue({ category: activeCategory, tags: [], is_published: true })
    setDrawerOpen(true)
  }

  const openEdit = (article: WikiArticle) => {
    setEditingArticle(article)
    form.setFieldsValue({
      title: article.title,
      body: article.body,
      category: article.category,
      tags: article.tags,
      summary: article.summary,
      is_published: article.is_published,
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      if (editingArticle) {
        await updateWikiArticle(editingArticle.id, values)
        message.success('文章已更新')
      } else {
        await createWikiArticle(values)
        message.success('文章已新增')
      }
      setDrawerOpen(false)
      loadArticles()
    } catch (err: any) {
      if (err?.errorFields) return   // form validation
      message.error('儲存失敗：' + (err?.response?.data?.detail || err?.message))
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteWikiArticle(id)
      message.success('已刪除')
      if (selectedId === id) setSelectedId(null)
      loadArticles()
    } catch {
      message.error('刪除失敗')
    }
  }

  // ── AI 問答 ──────────────────────────────────────────────────────────────────
  const handleAsk = async () => {
    if (!aiQuestion.trim()) return
    const q = aiQuestion.trim()
    setAiLoading(true)
    setAiQuestion('')
    try {
      const res = await askWiki({ question: q, category: activeCategory })
      setAiHistory((prev) => [...prev, { q, a: res.answer }])
      setAiSources(res.sources)
      setTimeout(() => aiEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch {
      message.error('AI 問答失敗，請稍後再試')
    } finally {
      setAiLoading(false)
    }
  }

  // ── 渲染 ─────────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#f0f4f8' }}>

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div style={{ background: '#fff', padding: '12px 24px', borderBottom: '1px solid #e8e8e8', display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <BookOutlined style={{ color: '#1B3A5C', fontSize: 20 }} />
          <span style={{ fontWeight: 700, fontSize: 18, color: '#1B3A5C' }}>知識庫</span>
          <Badge count={total} showZero style={{ backgroundColor: '#4BA8E8', marginLeft: 4 }} />
        </div>

        {/* 分類 Tabs */}
        <Tabs
          size="small"
          activeKey={activeCategory}
          onChange={(k) => setActiveCategory(k as 'sop' | 'dev')}
          style={{ marginBottom: 0 }}
          items={CATEGORIES.map((c) => ({
            key: c.key,
            label: <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>{c.icon}{c.label}</span>,
          }))}
        />

        <div style={{ flex: 1 }} />

        {/* 視圖切換 */}
        <Segmented
          value={viewMode}
          onChange={(v) => setViewMode(v as 'list' | 'graph')}
          options={[
            { value: 'list',  icon: <UnorderedListOutlined />, label: '清單' },
            { value: 'graph', icon: <ApartmentOutlined />,     label: '圖譜' },
          ]}
        />

        {viewMode === 'list' && (
          <>
            <Input.Search
              placeholder="搜尋文章…"
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onSearch={() => loadArticles()}
              allowClear
              style={{ width: 240 }}
              prefix={<SearchOutlined />}
            />
            <Button icon={<ReloadOutlined />} onClick={loadArticles} />
          </>
        )}
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}
          style={{ background: '#1B3A5C' }}>
          新增文章
        </Button>
        <Button
          icon={<RobotOutlined />}
          onClick={() => setAiOpen(true)}
          style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', color: '#fff', border: 'none' }}
        >
          AI 問答
        </Button>
        <Dropdown menu={{ items: syncMenuItems }} placement="bottomRight" disabled={syncing}>
          <Button icon={<SyncOutlined spin={syncing} />} loading={syncing}>
            {syncing ? '同步中…' : '同步 Obsidian'}
          </Button>
        </Dropdown>
      </div>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>

        {/* ── 圖譜視圖 ─────────────────────────────────────────────────────── */}
        {viewMode === 'graph' && (
          <div style={{ flex: 1, position: 'relative' }}>
            <WikiGraph
              category={activeCategory}
              onNodeClick={(id) => {
                setSelectedId(id)
                setViewMode('list')
              }}
            />
          </div>
        )}

        {/* ── 清單視圖 ─────────────────────────────────────────────────────── */}
        {viewMode === 'list' && (<>

        {/* ── 文章清單（左欄）─────────────────────────────────────────────── */}
        <div style={{ width: 280, background: '#fff', borderRight: '1px solid #e8e8e8', overflowY: 'auto', flexShrink: 0 }}>
          <Spin spinning={loading}>
            {articles.length === 0 ? (
              <Empty description="尚無文章" style={{ padding: 32 }}>
                <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openCreate}
                  style={{ background: '#1B3A5C' }}>新增第一篇</Button>
              </Empty>
            ) : (
              articles.map((article) => (
                <div
                  key={article.id}
                  onClick={() => setSelectedId(article.id)}
                  style={{
                    padding: '12px 16px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f0f0f0',
                    background: selectedId === article.id ? '#e8f4f8' : '#fff',
                    borderLeft: selectedId === article.id ? '3px solid #4BA8E8' : '3px solid transparent',
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 14, color: '#1B3A5C', lineHeight: 1.4, marginBottom: 4 }}>
                    {article.title}
                  </div>
                  {article.summary && (
                    <div style={{ fontSize: 12, color: '#888', lineHeight: 1.5, marginBottom: 6 }}>
                      {article.summary.slice(0, 60)}{article.summary.length > 60 ? '…' : ''}
                    </div>
                  )}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 4 }}>
                    {article.tags.slice(0, 3).map((t) => (
                      <Tag key={t} style={{ fontSize: 11, padding: '0 4px', margin: 0 }}>{t}</Tag>
                    ))}
                  </div>
                  <div style={{ fontSize: 11, color: '#aaa' }}>
                    {dayjs(article.updated_at).format('MM/DD HH:mm')}
                  </div>
                </div>
              ))
            )}
          </Spin>
        </div>

        {/* ── 文章內容（右欄）─────────────────────────────────────────────── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
          {selectedArticle ? (
            <div style={{ maxWidth: 860, margin: '0 auto' }}>
              {/* 標題列 */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 16 }}>
                <div style={{ flex: 1 }}>
                  <Title level={2} style={{ color: '#1B3A5C', marginBottom: 8 }}>
                    {selectedArticle.title}
                  </Title>
                  <Space wrap size={6}>
                    <Tag color={activeCategory === 'sop' ? '#1B3A5C' : '#4BA8E8'} style={{ color: '#fff' }}>
                      {activeCategory === 'sop' ? '員工 SOP' : '開發者 Wiki'}
                    </Tag>
                    {selectedArticle.tags.map((t) => (
                      <Tag key={t} icon={<TagOutlined />}>{t}</Tag>
                    ))}
                  </Space>
                  <div style={{ marginTop: 8, fontSize: 12, color: '#aaa', display: 'flex', gap: 16 }}>
                    <span><UserOutlined style={{ marginRight: 4 }} />{selectedArticle.author || '系統'}</span>
                    <span><ClockCircleOutlined style={{ marginRight: 4 }} />{dayjs(selectedArticle.updated_at).format('YYYY-MM-DD HH:mm')} 更新</span>
                  </div>
                </div>
                <Space>
                  <Tooltip title="編輯">
                    <Button icon={<EditOutlined />} onClick={() => openEdit(selectedArticle)} />
                  </Tooltip>
                  <Popconfirm title="確定刪除這篇文章？" onConfirm={() => handleDelete(selectedArticle.id)} okText="刪除" cancelText="取消" okButtonProps={{ danger: true }}>
                    <Tooltip title="刪除">
                      <Button icon={<DeleteOutlined />} danger />
                    </Tooltip>
                  </Popconfirm>
                </Space>
              </div>

              {/* Markdown 內容 */}
              <div style={{ background: '#fff', borderRadius: 8, padding: '24px 32px', boxShadow: '0 1px 4px rgba(0,0,0,0.08)', minHeight: 400 }}>
                <MarkdownRenderer content={selectedArticle.body} />
              </div>
            </div>
          ) : (
            <Empty
              image={<BookOutlined style={{ fontSize: 64, color: '#c0c0c0' }} />}
              description={
                <div style={{ color: '#aaa' }}>
                  <div style={{ fontSize: 16, marginBottom: 8 }}>選擇左側文章或新增第一篇</div>
                  <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ background: '#1B3A5C' }}>新增文章</Button>
                </div>
              }
              style={{ paddingTop: 80 }}
            />
          )}
        </div>
        </>)}  {/* ── end viewMode === 'list' ── */}
      </div>

      {/* ── 新增 / 編輯 Drawer ──────────────────────────────────────────────── */}
      <Drawer
        title={editingArticle ? '編輯文章' : '新增知識庫文章'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={700}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSave} loading={saving} style={{ background: '#1B3A5C' }}>
              {editingArticle ? '儲存變更' : '新增文章'}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="title" label="標題" rules={[{ required: true, message: '請填入標題' }]}>
            <Input placeholder="文章標題" maxLength={100} />
          </Form.Item>
          <Form.Item name="category" label="分類" rules={[{ required: true }]}>
            <Select options={[
              { value: 'sop', label: '員工 SOP 知識庫' },
              { value: 'dev', label: '開發者技術 Wiki' },
            ]} />
          </Form.Item>
          <Form.Item name="tags" label="標籤">
            <Select
              mode="tags"
              placeholder="選擇或輸入標籤（Enter 新增）"
              options={(form.getFieldValue('category') === 'dev' ? TAGS_SUGGESTIONS.dev : TAGS_SUGGESTIONS.sop).map((t) => ({ value: t, label: t }))}
            />
          </Form.Item>
          <Form.Item name="summary" label="摘要（選填，留空自動擷取）">
            <Input placeholder="一行摘要，顯示於清單預覽" maxLength={200} />
          </Form.Item>
          <Form.Item name="body" label="內文（Markdown 格式）" rules={[{ required: true, message: '請填入內文' }]}>
            <TextArea
              rows={20}
              placeholder={`# 標題\n\n## 說明\n\n內容使用 **Markdown** 格式。\n\n\`\`\`bash\n# 程式碼範例\necho hello\n\`\`\``}
              style={{ fontFamily: 'monospace', fontSize: 13 }}
            />
          </Form.Item>
          <Form.Item name="is_published" label="發佈狀態" valuePropName="checked">
            <Select options={[
              { value: true, label: '✅ 已發佈' },
              { value: false, label: '📝 草稿' },
            ]} />
          </Form.Item>
        </Form>
      </Drawer>

      {/* ── Obsidian 同步結果 Modal ─────────────────────────────────────────── */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {syncType === 'export' ? <ExportOutlined style={{ color: '#4BA8E8' }} /> : <ImportOutlined style={{ color: '#52c41a' }} />}
            <span>{syncType === 'export' ? '匯出到 Obsidian 完成' : '從 Obsidian 匯入完成'}</span>
          </div>
        }
        open={syncResultOpen}
        onCancel={() => setSyncResultOpen(false)}
        footer={<Button type="primary" onClick={() => setSyncResultOpen(false)} style={{ background: '#1B3A5C' }}>確定</Button>}
        width={480}
      >
        {syncResult && (
          <div style={{ lineHeight: 2 }}>
            <div style={{ fontSize: 13, color: '#555', marginBottom: 12 }}>
              <code style={{ fontSize: 11, color: '#888', background: '#f5f5f5', padding: '2px 6px', borderRadius: 3 }}>
                {syncResult.wiki_dir}
              </code>
            </div>
            {syncType === 'export' ? (
              <>
                <div>✅ 匯出／更新：<strong>{syncResult.exported}</strong> 篇</div>
                <div>⏭ 跳過（已是最新）：<strong>{syncResult.skipped}</strong> 篇</div>
              </>
            ) : (
              <>
                <div>✅ 新增：<strong>{syncResult.imported}</strong> 篇</div>
                <div>🔄 更新：<strong>{syncResult.updated}</strong> 篇</div>
                <div>⏭ 跳過（已是最新）：<strong>{syncResult.skipped}</strong> 篇</div>
              </>
            )}
            {syncResult.errors.length > 0 && (
              <div style={{ marginTop: 12, background: '#fff5f5', border: '1px solid #ffccc7', borderRadius: 6, padding: '8px 12px' }}>
                <div style={{ color: '#c0392b', fontWeight: 600, marginBottom: 4 }}>⚠️ {syncResult.errors.length} 個錯誤</div>
                {syncResult.errors.map((e, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#555' }}>• {e}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* ── AI 問答 Modal ────────────────────────────────────────────────────── */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <RobotOutlined style={{ color: '#764ba2' }} />
            <span>AI 知識庫問答</span>
            <Tag style={{ marginLeft: 4, fontSize: 11 }}>{activeCategory === 'sop' ? '員工 SOP' : '開發者 Wiki'}</Tag>
          </div>
        }
        open={aiOpen}
        onCancel={() => setAiOpen(false)}
        footer={null}
        width={660}
        styles={{ body: { padding: 0 } }}
      >
        {/* 對話記錄 */}
        <div style={{ height: 380, overflowY: 'auto', padding: '16px 20px', background: '#f8f9fa' }}>
          {aiHistory.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#aaa', paddingTop: 60 }}>
              <RobotOutlined style={{ fontSize: 40, marginBottom: 12, display: 'block' }} />
              <div>向 AI 提問，從知識庫找答案</div>
              <div style={{ fontSize: 12, marginTop: 8 }}>例如：「冷氣壞了怎麼辦？」或「API 認證怎麼設計？」</div>
            </div>
          ) : (
            aiHistory.map((h, idx) => (
              <div key={idx} style={{ marginBottom: 16 }}>
                {/* 問題 */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 6 }}>
                  <div style={{ background: '#1B3A5C', color: '#fff', padding: '8px 14px', borderRadius: '16px 16px 4px 16px', maxWidth: '80%', fontSize: 14 }}>
                    {h.q}
                  </div>
                </div>
                {/* 回答 */}
                <div style={{ display: 'flex', gap: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg, #667eea, #764ba2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 2 }}>
                    <RobotOutlined style={{ color: '#fff', fontSize: 14 }} />
                  </div>
                  <div style={{ background: '#fff', padding: '10px 14px', borderRadius: '4px 16px 16px 16px', maxWidth: '85%', fontSize: 14, lineHeight: 1.7, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                    <MarkdownRenderer content={h.a} />
                  </div>
                </div>
              </div>
            ))
          )}
          {aiLoading && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg, #667eea, #764ba2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <RobotOutlined style={{ color: '#fff', fontSize: 14 }} />
              </div>
              <div style={{ background: '#fff', padding: '10px 14px', borderRadius: '4px 16px 16px 16px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}>
                <Spin size="small" />
                <span style={{ marginLeft: 8, color: '#aaa', fontSize: 13 }}>思考中…</span>
              </div>
            </div>
          )}
          <div ref={aiEndRef} />
        </div>

        {/* 參考來源 */}
        {aiSources.length > 0 && (
          <div style={{ padding: '8px 20px', borderTop: '1px solid #f0f0f0', background: '#fff' }}>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>參考文章：</div>
            <Space wrap>
              {aiSources.map((s) => (
                <Tag
                  key={s.id}
                  style={{ cursor: 'pointer', fontSize: 12 }}
                  onClick={() => { setSelectedId(s.id); setAiOpen(false) }}
                >
                  {s.title}
                </Tag>
              ))}
            </Space>
          </div>
        )}

        {/* 輸入框 */}
        <div style={{ padding: '12px 20px', borderTop: '1px solid #f0f0f0', background: '#fff', display: 'flex', gap: 8 }}>
          <Input
            placeholder="輸入問題（Enter 送出）"
            value={aiQuestion}
            onChange={(e) => setAiQuestion(e.target.value)}
            onPressEnter={handleAsk}
            disabled={aiLoading}
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleAsk}
            loading={aiLoading}
            disabled={!aiQuestion.trim()}
            style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none' }}
          >
            送出
          </Button>
        </div>
      </Modal>
    </div>
  )
}
