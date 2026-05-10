/**
 * 專案知識圖譜
 * 路由：/settings/knowledge-graph
 * 功能：觸發 graphify 分析整個 portal 專案，以互動式 HTML iframe 呈現結果
 */
import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Badge,
  Breadcrumb,
  Button,
  Card,
  Descriptions,
  Progress,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import {
  ApartmentOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { fetchGraphStatus, triggerGenerate, KnowledgeGraphStatus } from '@/api/knowledgeGraph'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Paragraph, Text } = Typography

// ── 狀態 Badge 設定 ───────────────────────────────────────────────────────────
const STATUS_CONFIG: Record<
  KnowledgeGraphStatus['status'],
  { color: string; label: string }
> = {
  idle:       { color: 'default', label: '尚未產生' },
  generating: { color: 'processing', label: '產生中…' },
  ready:      { color: 'success',    label: '已就緒' },
}

// ── 圖譜說明 ──────────────────────────────────────────────────────────────────
const FEATURE_TAGS = [
  'Python AST 解析',
  'TypeScript 結構分析',
  'Markdown 文件提取',
  'SQL Schema 關聯',
  'AI 概念聚類（Leiden）',
  '互動式 HTML 圖譜',
]

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function KnowledgeGraphPage() {
  const [status, setStatus] = useState<KnowledgeGraphStatus>({
    status: 'idle',
    generated_at: null,
    html_exists: false,
    error: null,
  })
  const [loading, setLoading] = useState(false)
  const [pollingProgress, setPollingProgress] = useState(0)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const progressRef = useRef(0)

  // 停止輪詢
  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    setPollingProgress(0)
    progressRef.current = 0
  }

  // 開始輪詢（每 3 秒查一次狀態）
  const startPolling = () => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      // 進度條動畫（模擬，最多到 90%，等待真正完成才跳到 100%）
      if (progressRef.current < 90) {
        progressRef.current += 2
        setPollingProgress(progressRef.current)
      }
      try {
        const st = await fetchGraphStatus()
        setStatus(st)
        if (st.status !== 'generating') {
          stopPolling()
          if (st.status === 'ready') setPollingProgress(100)
        }
      } catch {
        // 靜默忽略，繼續下次輪詢
      }
    }, 3000)
  }

  // 首次載入時查詢狀態
  useEffect(() => {
    fetchGraphStatus().then(setStatus).catch(console.error)
    return () => stopPolling()
  }, [])

  // 若狀態已是 generating（頁面重整後），自動繼續輪詢
  useEffect(() => {
    if (status.status === 'generating' && !pollRef.current) {
      startPolling()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status.status])

  // ── 觸發產生 ──────────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    setLoading(true)
    try {
      await triggerGenerate()
      setStatus((prev) => ({ ...prev, status: 'generating', error: null }))
      startPolling()
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        '觸發失敗，請稍後再試'
      setStatus((prev) => ({ ...prev, error: msg }))
    } finally {
      setLoading(false)
    }
  }

  const cfg = STATUS_CONFIG[status.status]
  const isGenerating = status.status === 'generating'
  const isReady = status.status === 'ready' && status.html_exists

  return (
    <div style={{ padding: '24px', maxWidth: 1400 }}>
      {/* ── Breadcrumb ── */}
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: NAV_GROUP.settings },
          { title: NAV_PAGE.knowledgeGraph },
        ]}
      />

      {/* ── 頁面標題 ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <ApartmentOutlined style={{ fontSize: 24, color: '#667eea' }} />
        <Title level={4} style={{ margin: 0 }}>
          {NAV_PAGE.knowledgeGraph}
        </Title>
        <Badge status={cfg.color as 'default' | 'processing' | 'success'} text={cfg.label} />
      </div>
      <Paragraph type="secondary" style={{ marginBottom: 24 }}>
        靜態程式碼分析工具 — 自動掃描 portal 後端（Python AST）與前端（TypeScript import）的模組、類別、函式及相依關係，產生可互動的知識圖譜。
      </Paragraph>

      {/* ── 功能標籤 ── */}
      <Space wrap style={{ marginBottom: 20 }}>
        {FEATURE_TAGS.map((tag) => (
          <Tag key={tag} color="geekblue">{tag}</Tag>
        ))}
      </Space>

      {/* ── 控制列 ── */}
      <Card
        style={{ marginBottom: 20 }}
        bodyStyle={{ padding: '16px 20px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <Tooltip title={isGenerating ? '圖譜產生中，請等待完成' : '分析整個 portal 專案（約需 2–5 分鐘）'}>
            <Button
              type="primary"
              icon={isGenerating ? <SyncOutlined spin /> : <ReloadOutlined />}
              loading={loading}
              disabled={isGenerating}
              onClick={handleGenerate}
              style={{
                background: 'linear-gradient(135deg, #667eea, #764ba2)',
                border: 'none',
              }}
            >
              {isGenerating ? '產生中…' : isReady ? '重新產生圖譜' : '產生圖譜'}
            </Button>
          </Tooltip>

          <Descriptions size="small" column={3} style={{ flex: 1 }}>
            <Descriptions.Item label="狀態">
              <Badge status={cfg.color as 'default' | 'processing' | 'success'} text={cfg.label} />
            </Descriptions.Item>
            <Descriptions.Item label="最後產生">
              {status.generated_at
                ? dayjs(status.generated_at).format('YYYY-MM-DD HH:mm')
                : '—'}
            </Descriptions.Item>
            <Descriptions.Item label="說明">
              <span style={{ color: '#64748b', fontSize: 12 }}>
                <InfoCircleOutlined style={{ marginRight: 4 }} />
                產生期間後端持續執行，可離開頁面後返回查看結果
              </span>
            </Descriptions.Item>
          </Descriptions>
        </div>

        {/* 進度條 */}
        {isGenerating && (
          <Progress
            percent={pollingProgress}
            status="active"
            strokeColor={{ from: '#667eea', to: '#764ba2' }}
            style={{ marginTop: 12 }}
          />
        )}
      </Card>

      {/* ── 錯誤提示 ── */}
      {status.error && (
        <Alert
          type="error"
          message="產生失敗"
          description={status.error}
          showIcon
          style={{ marginBottom: 20 }}
          action={
            <Button size="small" danger onClick={handleGenerate} disabled={isGenerating}>
              重試
            </Button>
          }
        />
      )}

      {/* ── 使用說明（尚未產生時顯示） ── */}
      {!isReady && !isGenerating && !status.error && (
        <Alert
          type="info"
          showIcon
          message="點選「產生圖譜」開始分析"
          description={
            <div style={{ lineHeight: 1.8 }}>
              <div>分析範圍：</div>
              <div style={{ color: '#64748b', fontSize: 12 }}>
                📂 <Text code>backend/</Text> — Python 模組、類別、函式、import 關係（ast 解析）
              </div>
              <div style={{ color: '#64748b', fontSize: 12 }}>
                📂 <Text code>frontend/src/</Text> — TypeScript 元件、Hook、函式、相對 import 關係
              </div>
              <div style={{ marginTop: 6, color: '#64748b', fontSize: 12 }}>
                首次產生約需 10–60 秒（依專案大小而定），結果會儲存供下次直接查看。
              </div>
            </div>
          }
          style={{ marginBottom: 20 }}
        />
      )}

      {/* ── 圖譜呈現（iframe） ── */}
      {isReady && (
        <Card
          title={
            <Space>
              <ApartmentOutlined style={{ color: '#667eea' }} />
              <span>互動式知識圖譜</span>
              {status.generated_at && (
                <Text type="secondary" style={{ fontSize: 12, fontWeight: 400 }}>
                  產生於 {dayjs(status.generated_at).format('YYYY-MM-DD HH:mm')}
                </Text>
              )}
            </Space>
          }
          bodyStyle={{ padding: 0 }}
          style={{ overflow: 'hidden' }}
        >
          <iframe
            src="/kg-files/graph.html"
            title="Portal 專案知識圖譜"
            style={{
              width: '100%',
              height: '78vh',
              border: 'none',
              display: 'block',
              background: '#0f172a',
            }}
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
            referrerPolicy="no-referrer"
          />
        </Card>
      )}
    </div>
  )
}
