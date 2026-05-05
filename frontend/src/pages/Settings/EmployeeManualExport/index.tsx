/**
 * 員工操作手冊匯出頁面
 * 路由：/settings/employee-manual-export
 *
 * 功能：
 *  1. 選擇模組
 *  2. 選擇文件種類（可多選）
 *  3. 選擇匯出格式（目前支援 ZIP）
 *  4. 產生手冊
 *  5. 下載 ZIP
 *  6. NotebookLM 使用提示詞複製
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Card, Checkbox, Button, Spin, Alert, Typography, Space,
  Row, Col, Tag, Divider, Tooltip, message, Steps, Badge,
} from 'antd'
import {
  FileTextOutlined,
  DownloadOutlined,
  CopyOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  BookOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { ModuleInfo, ExportStatus } from '@/types/employeeManualExport'
import { DOC_TYPE_OPTIONS } from '@/types/employeeManualExport'
import {
  fetchModuleList,
  generateManual,
  fetchExportStatus,
  downloadManualZip,
} from '@/api/employeeManualExport'

const { Title, Text, Paragraph } = Typography

// ── NotebookLM 提示詞 ────────────────────────────────────────────────────────
const NOTEBOOKLM_PROMPT = `你是一位企業內部教育訓練講師。
我上傳的是 Ragic Portal 的員工操作手冊知識包。
請根據這些資料，幫我製作一份給一般員工使用的操作手冊。

要求：
1. 使用繁體中文。
2. 語氣簡單、清楚、親切。
3. 適合非資訊人員閱讀。
4. 每個功能請用「用途、操作步驟、注意事項、常見問題」呈現。
5. 不要自行假設系統沒有寫到的功能。
6. 如果資料不足，請列出需要補充的內容。
7. 請另外產生一份 5 到 8 分鐘的語音教學腳本。`

// ── 文件種類分組 ─────────────────────────────────────────────────────────────
const DOC_GROUPS = [
  {
    label: '📖 基本文件',
    keys: ['manual', 'supervisor', 'faq'],
    desc: '員工操作手冊、主管導覽、常見問題，適合日常查詢',
  },
  {
    label: '🎓 教育訓練',
    keys: ['training', 'voice', 'newbie'],
    desc: '教育訓練講稿、語音腳本、新人教學，適合上課與引導',
  },
  {
    label: '🔧 異常處理',
    keys: ['troubleshoot'],
    desc: '異常狀況處理手冊，適合遇到問題時查詢',
  },
]

// ── 主頁面元件 ───────────────────────────────────────────────────────────────
export default function EmployeeManualExportPage() {
  const [modules, setModules] = useState<ModuleInfo[]>([])
  const [loadingModules, setLoadingModules] = useState(true)

  // 使用者選擇
  const [selectedModule, setSelectedModule] = useState<string | null>(null)
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([
    'manual', 'supervisor', 'faq', 'training', 'voice', 'newbie', 'troubleshoot',
  ])

  // 匯出狀態
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [downloading, setDownloading] = useState(false)

  // 載入模組清單
  useEffect(() => {
    fetchModuleList()
      .then(setModules)
      .catch(() => message.error('載入模組清單失敗，請重新整理'))
      .finally(() => setLoadingModules(false))
  }, [])

  // 選擇模組後查詢匯出狀態
  const handleSelectModule = useCallback(async (key: string) => {
    setSelectedModule(key)
    setExportStatus(null)
    setLoadingStatus(true)
    try {
      const status = await fetchExportStatus(key)
      setExportStatus(status)
    } catch {
      // 若查詢失敗，視為尚未產生
      setExportStatus({ module_key: key, has_export: false, files: [], generated_at: null, download_url: null })
    } finally {
      setLoadingStatus(false)
    }
  }, [])

  // 產生手冊
  const handleGenerate = async () => {
    if (!selectedModule) {
      message.warning('請先選擇要產生操作手冊的模組')
      return
    }
    if (selectedDocTypes.length === 0) {
      message.warning('請至少選擇一種文件類型')
      return
    }
    setGenerating(true)
    try {
      const result = await generateManual({
        module_key: selectedModule,
        doc_types: selectedDocTypes,
        export_format: 'zip',
      })
      message.success(`✅ 已成功產生 ${result.generated_files.length} 份文件！`)
      // 重新查詢狀態
      const status = await fetchExportStatus(selectedModule)
      setExportStatus(status)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '產生失敗，請稍後再試'
      message.error(msg)
    } finally {
      setGenerating(false)
    }
  }

  // 下載 ZIP
  const handleDownload = async () => {
    if (!selectedModule || !exportStatus?.has_export) return
    const mod = modules.find(m => m.key === selectedModule)
    setDownloading(true)
    try {
      await downloadManualZip(selectedModule, mod?.name ?? selectedModule)
      message.success('ZIP 下載成功！請上傳到 NotebookLM')
    } catch {
      message.error('下載失敗，請稍後再試')
    } finally {
      setDownloading(false)
    }
  }

  // 複製 NotebookLM 提示詞
  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(NOTEBOOKLM_PROMPT).then(() => {
      message.success('提示詞已複製到剪貼簿！')
    }).catch(() => {
      message.error('複製失敗，請手動選取複製')
    })
  }

  // 切換全選/全不選文件種類
  const handleSelectAllDocs = (checked: boolean) => {
    setSelectedDocTypes(checked ? DOC_TYPE_OPTIONS.map(d => d.key) : [])
  }

  const selectedModuleInfo = modules.find(m => m.key === selectedModule)

  return (
    <div style={{ padding: '24px', maxWidth: 960 }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>

        {/* 頁頭 */}
        <div>
          <Title level={3} style={{ marginBottom: 4 }}>
            <BookOutlined style={{ marginRight: 8, color: '#1B3A5C' }} />
            員工操作手冊匯出
          </Title>
          <Text type="secondary">
            選擇模組後，自動產生適合員工閱讀的操作手冊文件包，可上傳至 NotebookLM 製作教育訓練內容。
          </Text>
        </div>

        {/* Step 1：選擇模組 */}
        <Card
          title={<><span style={{ color: '#4BA8E8', marginRight: 6 }}>Step 1</span> 選擇要產生手冊的模組</>}
          size="small"
        >
          {loadingModules ? (
            <Spin tip="載入模組清單中…" />
          ) : (
            <Row gutter={[12, 12]}>
              {modules.map(mod => (
                <Col key={mod.key} xs={24} sm={12} md={8}>
                  <Card
                    size="small"
                    hoverable
                    style={{
                      cursor: 'pointer',
                      borderColor: selectedModule === mod.key ? '#4BA8E8' : undefined,
                      background: selectedModule === mod.key ? '#f0f8ff' : undefined,
                    }}
                    onClick={() => handleSelectModule(mod.key)}
                  >
                    <Space direction="vertical" size={2} style={{ width: '100%' }}>
                      <Space>
                        {selectedModule === mod.key && (
                          <CheckCircleOutlined style={{ color: '#4BA8E8' }} />
                        )}
                        <Text strong style={{ fontSize: 13 }}>{mod.name}</Text>
                      </Space>
                      <Text type="secondary" style={{ fontSize: 11 }}>{mod.menu_path}</Text>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Card>

        {/* Step 2：選擇文件種類 */}
        <Card
          title={<><span style={{ color: '#4BA8E8', marginRight: 6 }}>Step 2</span> 選擇要產生的文件種類（可多選）</>}
          size="small"
          extra={
            <Button size="small" type="link" onClick={() => handleSelectAllDocs(selectedDocTypes.length < DOC_TYPE_OPTIONS.length)}>
              {selectedDocTypes.length === DOC_TYPE_OPTIONS.length ? '全部取消' : '全部選取'}
            </Button>
          }
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            {DOC_GROUPS.map(group => (
              <div key={group.label}>
                <Text strong style={{ fontSize: 13 }}>{group.label}</Text>
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>{group.desc}</Text>
                <div style={{ marginTop: 8 }}>
                  <Space wrap>
                    {group.keys.map(key => {
                      const opt = DOC_TYPE_OPTIONS.find(d => d.key === key)!
                      return (
                        <Checkbox
                          key={key}
                          checked={selectedDocTypes.includes(key)}
                          onChange={e => {
                            setSelectedDocTypes(prev =>
                              e.target.checked ? [...prev, key] : prev.filter(k => k !== key)
                            )
                          }}
                        >
                          {opt.label}
                          <Text type="secondary" style={{ fontSize: 11, marginLeft: 4 }}>
                            （{opt.filename}）
                          </Text>
                        </Checkbox>
                      )
                    })}
                  </Space>
                </div>
              </div>
            ))}
          </Space>
        </Card>

        {/* Step 3：匯出格式 */}
        <Card
          title={<><span style={{ color: '#4BA8E8', marginRight: 6 }}>Step 3</span> 匯出格式</>}
          size="small"
        >
          <Space>
            <Tag color="blue" icon={<FileTextOutlined />}>Markdown（.md）</Tag>
            <Tag color="green" icon={<DownloadOutlined />}>ZIP 全包下載</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              所有文件均以 Markdown 格式產生，並打包成 ZIP 壓縮檔供下載。
            </Text>
          </Space>
        </Card>

        {/* 產生狀態與操作按鈕 */}
        <Card size="small">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">

            {/* 選擇模組資訊 */}
            {selectedModuleInfo && (
              <Alert
                type="info"
                showIcon
                message={`已選擇模組：${selectedModuleInfo.name}`}
                description={selectedModuleInfo.menu_path}
              />
            )}

            {/* 匯出狀態 */}
            {loadingStatus && <Spin tip="查詢匯出狀態中…" />}
            {!loadingStatus && exportStatus && (
              <div>
                {exportStatus.has_export ? (
                  <Alert
                    type="success"
                    showIcon
                    icon={<CheckCircleOutlined />}
                    message="已有產生好的操作手冊"
                    description={
                      <Space direction="vertical" size={2}>
                        <Text style={{ fontSize: 12 }}>
                          產生時間：{exportStatus.generated_at
                            ? new Date(exportStatus.generated_at).toLocaleString('zh-TW')
                            : '不明'}
                        </Text>
                        <Space wrap>
                          {exportStatus.files.map(f => (
                            <Tag key={f} icon={<FileTextOutlined />} color="default">{f}</Tag>
                          ))}
                        </Space>
                      </Space>
                    }
                  />
                ) : (
                  <Alert
                    type="warning"
                    showIcon
                    message="尚未產生操作手冊"
                    description="請點選「產生手冊」按鈕，系統會自動產生所有文件。"
                  />
                )}
              </div>
            )}

            {/* 操作按鈕 */}
            <Space wrap>
              <Button
                type="primary"
                icon={generating ? <SyncOutlined spin /> : <ThunderboltOutlined />}
                onClick={handleGenerate}
                loading={generating}
                disabled={!selectedModule || selectedDocTypes.length === 0}
                style={{ background: '#1B3A5C' }}
              >
                {generating ? '產生中…' : '產生手冊'}
              </Button>

              <Button
                icon={downloading ? <SyncOutlined spin /> : <DownloadOutlined />}
                onClick={handleDownload}
                loading={downloading}
                disabled={!exportStatus?.has_export}
                type="default"
              >
                {downloading ? '下載中…' : '下載 ZIP'}
              </Button>

              {exportStatus?.has_export && (
                <Tooltip title="重新產生會覆蓋既有文件">
                  <Button
                    icon={<SyncOutlined />}
                    onClick={handleGenerate}
                    loading={generating}
                    disabled={!selectedModule}
                    size="small"
                  >
                    重新產生
                  </Button>
                </Tooltip>
              )}
            </Space>
          </Space>
        </Card>

        {/* NotebookLM 提示詞 */}
        <Card
          title={
            <Space>
              <BookOutlined style={{ color: '#667eea' }} />
              <span>NotebookLM 使用提示詞</span>
              <Tag color="purple">複製後貼入 NotebookLM</Tag>
            </Space>
          }
          size="small"
          extra={
            <Button
              icon={<CopyOutlined />}
              onClick={handleCopyPrompt}
              type="primary"
              ghost
              size="small"
            >
              複製提示詞
            </Button>
          }
        >
          <Paragraph>
            <Text type="secondary" style={{ fontSize: 12 }}>
              下載 ZIP 後，請上傳到 NotebookLM，再使用以下提示詞讓 AI 幫您整理成完整的教育訓練內容：
            </Text>
          </Paragraph>
          <div
            style={{
              background: '#f5f5f5',
              border: '1px solid #d9d9d9',
              borderRadius: 6,
              padding: '12px 16px',
              fontFamily: 'monospace',
              fontSize: 13,
              lineHeight: 1.8,
              whiteSpace: 'pre-wrap',
              color: '#333',
            }}
          >
            {NOTEBOOKLM_PROMPT}
          </div>

          <Divider style={{ margin: '16px 0 12px' }} />
          <Text type="secondary" style={{ fontSize: 12 }}>
            💡 使用流程：
            <ol style={{ marginTop: 4, paddingLeft: 20 }}>
              <li>點選「產生手冊」→「下載 ZIP」</li>
              <li>前往 <a href="https://notebooklm.google.com" target="_blank" rel="noreferrer">notebooklm.google.com</a> 建立新筆記本</li>
              <li>上傳 ZIP 內的所有 .md 文件</li>
              <li>在聊天框貼入上方提示詞，開始生成內容</li>
            </ol>
          </Text>
        </Card>

      </Space>
    </div>
  )
}
