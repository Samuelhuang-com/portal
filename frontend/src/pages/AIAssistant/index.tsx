/**
 * AI 工單查詢助理頁面
 * 路由：/ai-assistant
 * 佈局：左側對話區 + 右側歷史問答面板
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Card, Input, Button, Table, Tag, Typography, Space, Alert,
  Spin, Empty, Tooltip, List, Badge,
} from 'antd'
import {
  SendOutlined, RobotOutlined, UserOutlined, ClearOutlined,
  ReloadOutlined, HistoryOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { queryWorkorder, getAIHistory, type ChatMessage, type RepairRow, type HistoryItem } from '@/api/ai'

const { Text, Paragraph } = Typography
const { TextArea } = Input

// ── 建議問題清單 ──────────────────────────────────────────────────────────────
const SUGGESTED_QUESTIONS = [
  '本月共有幾件未結案工單？',
  '飯店 B1 上個月有哪些報修記錄？',
  '超過 30 天未結案的工單有哪些？',
  '本年度平均結案天數是多少？',
  '商場本月費用最高的工單是哪些？',
]

// ── 對話訊息型別 ──────────────────────────────────────────────────────────────
interface UIMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  hasTable?: boolean
  tableData?: RepairRow[]
  totalCount?: number | null
  loading?: boolean
  error?: boolean
  fromHistory?: boolean
}

// ── 工單表格欄位定義 ──────────────────────────────────────────────────────────
const TABLE_COLUMNS: ColumnsType<RepairRow> = [
  {
    title: '地點',
    dataIndex: 'location',
    key: 'location',
    width: 60,
    render: (v: string) => (
      <Tag color={v === '飯店' ? 'blue' : 'purple'}>{v}</Tag>
    ),
  },
  {
    title: '案號',
    dataIndex: 'case_no',
    key: 'case_no',
    width: 120,
    render: (v: string) => <Text code style={{ fontSize: 12 }}>{v || '—'}</Text>,
  },
  {
    title: '標題',
    dataIndex: 'title',
    key: 'title',
    ellipsis: true,
  },
  {
    title: '樓層',
    dataIndex: 'floor',
    key: 'floor',
    width: 60,
  },
  {
    title: '狀態',
    dataIndex: 'status',
    key: 'status',
    width: 70,
    render: (v: string) => (
      <Tag color={v === '已結案' ? 'green' : 'red'}>{v}</Tag>
    ),
  },
  {
    title: '報修日期',
    dataIndex: 'occurred_at',
    key: 'occurred_at',
    width: 95,
    render: (v: string) => v || '—',
  },
  {
    title: '結案天數',
    dataIndex: 'close_days',
    key: 'close_days',
    width: 80,
    render: (v: number | null) =>
      v != null ? (
        <Text type={v > 30 ? 'danger' : undefined}>{v} 天</Text>
      ) : '—',
  },
  {
    title: '費用',
    dataIndex: 'total_fee',
    key: 'total_fee',
    width: 90,
    render: (v: number) =>
      v > 0 ? `NT$${v.toLocaleString()}` : '—',
  },
]

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function AIAssistant() {
  const [messages, setMessages] = useState<UIMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const msgIdRef = useRef(0)
  const bottomRef = useRef<HTMLDivElement>(null)

  const nextId = () => ++msgIdRef.current

  // 自動捲到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 載入歷史記錄
  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const data = await getAIHistory(30)
      setHistoryItems(data)
    } catch {
      // 靜默失敗，不中斷使用者操作
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  // 從歷史記錄載入 Q&A 到對話視窗（不重新呼叫 API）
  const loadHistoryItem = (item: HistoryItem) => {
    const userMsg: UIMessage = {
      id: nextId(), role: 'user', content: item.question, fromHistory: true,
    }
    const assistantMsg: UIMessage = {
      id: nextId(), role: 'assistant', content: item.answer,
      hasTable: item.has_table, tableData: item.table_data,
      totalCount: item.total_count, fromHistory: true,
    }
    setMessages(prev => [...prev, userMsg, assistantMsg])
  }

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || loading) return

    const userMsg: UIMessage = { id: nextId(), role: 'user', content: question }
    const loadingMsg: UIMessage = {
      id: nextId(), role: 'assistant', content: '', loading: true,
    }

    setMessages(prev => [...prev, userMsg, loadingMsg])
    setInput('')
    setLoading(true)

    // 組裝歷史（排除 loading 狀態與歷史載入的訊息）
    const history: ChatMessage[] = messages
      .filter(m => !m.loading && !m.error && !m.fromHistory)
      .map(m => ({ role: m.role, content: m.content }))

    try {
      const res = await queryWorkorder({ question, messages: history })
      setMessages(prev =>
        prev.map(m =>
          m.id === loadingMsg.id
            ? {
                ...m,
                loading: false,
                content: res.answer,
                hasTable: res.has_table,
                tableData: res.table_data,
                totalCount: res.total_count,
              }
            : m
        )
      )
      // 刷新歷史列表（新增了一筆）
      fetchHistory()
    } catch (err: unknown) {
      const errMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || '查詢失敗，請稍後再試'
      setMessages(prev =>
        prev.map(m =>
          m.id === loadingMsg.id
            ? { ...m, loading: false, content: errMsg, error: true }
            : m
        )
      )
    } finally {
      setLoading(false)
    }
  }, [loading, messages, fetchHistory])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const clearHistory = () => {
    setMessages([])
    setInput('')
  }

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 16px 24px' }}>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 16 }}>
        <Space align="center">
          <RobotOutlined style={{ fontSize: 22, color: '#4BA8E8' }} />
          <Text strong style={{ fontSize: 18 }}>AI 工單查詢助理</Text>
        </Space>
        <Text type="secondary" style={{ display: 'block', marginTop: 4, fontSize: 13 }}>
          以自然語言查詢工務維修工單，支援飯店工務部和商場工務報修資料
        </Text>
      </div>

      {/* 主內容：左側對話 + 右側歷史 */}
      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>

        {/* ── 左側：對話區 ── */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* 對話視窗 */}
          <Card
            style={{ marginBottom: 12, minHeight: 400, maxHeight: 560, overflowY: 'auto' }}
            styles={{ body: { padding: '16px' } }}
          >
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <RobotOutlined style={{ fontSize: 40, color: '#d9d9d9', marginBottom: 16 }} />
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="請在下方輸入您的問題，或點選建議問題開始查詢"
                />
                <div style={{ marginTop: 16 }}>
                  <Space wrap>
                    {SUGGESTED_QUESTIONS.map(q => (
                      <Button
                        key={q}
                        size="small"
                        onClick={() => sendMessage(q)}
                        style={{ borderColor: '#4BA8E8', color: '#4BA8E8' }}
                      >
                        {q}
                      </Button>
                    ))}
                  </Space>
                </div>
              </div>
            ) : (
              <>
                {messages.map(msg => (
                  <div
                    key={msg.id}
                    style={{
                      display: 'flex',
                      flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                      alignItems: 'flex-start',
                      marginBottom: 16,
                      gap: 8,
                    }}
                  >
                    {/* 頭像 */}
                    <div
                      style={{
                        width: 32, height: 32, borderRadius: '50%',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0,
                        background: msg.role === 'user' ? '#1B3A5C' : '#4BA8E8',
                        color: '#fff', fontSize: 14,
                      }}
                    >
                      {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    </div>

                    {/* 訊息內容 */}
                    <div
                      style={{
                        maxWidth: '82%',
                        background: msg.role === 'user' ? '#1B3A5C' : (msg.fromHistory ? '#f0f7ff' : '#f5f7fa'),
                        color: msg.role === 'user' ? '#fff' : '#333',
                        borderRadius: msg.role === 'user' ? '12px 2px 12px 12px' : '2px 12px 12px 12px',
                        padding: '10px 14px',
                        border: msg.fromHistory ? '1px dashed #4BA8E8' : undefined,
                      }}
                    >
                      {msg.loading ? (
                        <Space>
                          <Spin size="small" />
                          <Text type="secondary">AI 查詢中…</Text>
                        </Space>
                      ) : msg.error ? (
                        <Alert message={msg.content} type="error" showIcon style={{ border: 'none', background: 'transparent', padding: 0 }} />
                      ) : (
                        <>
                          <Paragraph
                            style={{
                              margin: 0,
                              whiteSpace: 'pre-wrap',
                              color: msg.role === 'user' ? '#fff' : undefined,
                            }}
                          >
                            {msg.content}
                          </Paragraph>

                          {/* 工單表格 */}
                          {msg.hasTable && msg.tableData && msg.tableData.length > 0 && (
                            <div style={{ marginTop: 12 }}>
                              {msg.totalCount != null && msg.totalCount > msg.tableData.length && (
                                <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
                                  共 {msg.totalCount} 筆，顯示前 {msg.tableData.length} 筆
                                </Text>
                              )}
                              <Table<RepairRow>
                                dataSource={msg.tableData}
                                columns={TABLE_COLUMNS}
                                rowKey="case_no"
                                size="small"
                                pagination={false}
                                scroll={{ x: 700 }}
                                style={{ background: '#fff', borderRadius: 6 }}
                              />
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={bottomRef} />
              </>
            )}
          </Card>

          {/* 輸入區 */}
          <Card styles={{ body: { padding: '12px 16px' } }}>
            <Space.Compact style={{ width: '100%' }}>
              <TextArea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="輸入問題，例如：本月飯店未結案工單有幾件？（Enter 送出，Shift+Enter 換行）"
                autoSize={{ minRows: 1, maxRows: 4 }}
                disabled={loading}
                style={{ borderRadius: '6px 0 0 6px', resize: 'none' }}
              />
              <Button
                type="primary"
                icon={<SendOutlined />}
                onClick={() => sendMessage(input)}
                loading={loading}
                disabled={!input.trim()}
                style={{ height: 'auto', borderRadius: '0 6px 6px 0', background: '#1B3A5C', borderColor: '#1B3A5C' }}
              >
                送出
              </Button>
            </Space.Compact>
            <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                查詢範圍依您的帳號權限自動限縮
              </Text>
              {messages.length > 0 && (
                <Tooltip title="清除對話記錄">
                  <Button
                    size="small"
                    icon={<ClearOutlined />}
                    onClick={clearHistory}
                    type="text"
                  >
                    清除對話
                  </Button>
                </Tooltip>
              )}
            </div>
          </Card>
        </div>

        {/* ── 右側：歷史問答 ── */}
        <div style={{ width: 300, flexShrink: 0 }}>
          <Card
            title={
              <Space>
                <HistoryOutlined style={{ color: '#4BA8E8' }} />
                <span>歷史問答</span>
                {historyItems.length > 0 && (
                  <Badge count={historyItems.length} style={{ backgroundColor: '#4BA8E8' }} />
                )}
              </Space>
            }
            extra={
              <Tooltip title="重新整理">
                <Button
                  size="small"
                  type="text"
                  icon={<ReloadOutlined spin={historyLoading} />}
                  onClick={fetchHistory}
                />
              </Tooltip>
            }
            styles={{ body: { padding: 0, maxHeight: 560, overflowY: 'auto' } }}
          >
            {historyLoading && historyItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 24 }}>
                <Spin size="small" />
              </div>
            ) : historyItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 16px' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>尚無查詢記錄</Text>
              </div>
            ) : (
              <List
                dataSource={historyItems}
                renderItem={item => (
                  <List.Item
                    onClick={() => loadHistoryItem(item)}
                    style={{
                      padding: '10px 16px',
                      cursor: 'pointer',
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#f0f7ff')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <div style={{ width: '100%' }}>
                      {/* 問題文字 */}
                      <Paragraph
                        ellipsis={{ rows: 2 }}
                        style={{ margin: 0, fontSize: 13, color: '#1B3A5C', lineHeight: 1.4 }}
                      >
                        {item.question}
                      </Paragraph>
                      {/* 時間 + 快取標記 + 表格標記 */}
                      <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <Text type="secondary" style={{ fontSize: 11 }}>{item.created_at}</Text>
                        {item.from_cache && (
                          <Tooltip title="本次命中快取，未呼叫 AI">
                            <ThunderboltOutlined style={{ fontSize: 10, color: '#faad14' }} />
                          </Tooltip>
                        )}
                        {item.has_table && (
                          <Tag style={{ fontSize: 10, padding: '0 4px', lineHeight: '16px', margin: 0 }} color="blue">表格</Tag>
                        )}
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            )}
          </Card>
          <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 6, textAlign: 'center' }}>
            點擊任一條紀錄可載入至對話視窗
          </Text>
        </div>

      </div>
    </div>
  )
}
