/**
 * Ragic 同步排程設定頁面
 * 路徑：/settings/ragic-connections
 *
 * 功能：設定各模組的自動同步間隔（使用現有 .env 連線設定）
 *        + 顯示 24 小時內的同步紀錄
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Radio,
  Row,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  SaveOutlined,
  SyncOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import apiClient from '../../api/client'
import { getRecentSyncLogs, triggerAllModulesSync, type ModuleSyncLogOut } from '../../api/ragic'

const { Title, Text, Paragraph } = Typography

// 預設間隔選項
const INTERVAL_OPTIONS = [
  { value: 15,  label: '15 分鐘' },
  { value: 30,  label: '30 分鐘' },
  { value: 60,  label: '1 小時' },
  { value: 120, label: '2 小時' },
  { value: 240, label: '4 小時' },
  { value: 480, label: '8 小時' },
]

// 各模組顯示名稱
const MODULE_NAMES = [
  '客房保養', '倉庫庫存', '客房保養明細', '飯店週期保養表',
  '商場週期保養表', 'B4F/RF/B2F/B1F 工務巡檢',
  '保全巡檢', '大直工務報修', '樂群工務報修',
]

// 狀態顏色 + 標籤
const STATUS_TAG: Record<string, { color: string; label: string }> = {
  success: { color: 'success', label: '成功' },
  error:   { color: 'error',   label: '失敗' },
  partial: { color: 'warning', label: '部分' },
  running: { color: 'processing', label: '執行中' },
}

// 格式化時間（後端存台灣時間，直接解析字串，不經 Date 物件避免 UTC 轉換）
function fmtTime(iso: string): string {
  // iso 格式：「2026-04-20T20:16:00」或「2026-04-20 20:16:00」
  const m = iso.match(/(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (!m) return iso
  return `${m[1]}/${m[2]} ${m[3]}:${m[4]}`
}

const SYNC_LOG_COLUMNS: ColumnsType<ModuleSyncLogOut> = [
  {
    title: '模組',
    dataIndex: 'module_name',
    key: 'module_name',
    width: 120,
    fixed: 'left',
  },
  {
    title: '狀態',
    dataIndex: 'status',
    key: 'status',
    width: 80,
    render: (s: string) => {
      const { color, label } = STATUS_TAG[s] ?? { color: 'default', label: s }
      return <Badge status={color as any} text={<Tag color={color}>{label}</Tag>} />
    },
    filters: [
      { text: '成功', value: 'success' },
      { text: '失敗', value: 'error' },
      { text: '部分', value: 'partial' },
    ],
    onFilter: (v, r) => r.status === v,
  },
  {
    title: '開始時間',
    dataIndex: 'started_at',
    key: 'started_at',
    width: 130,
    render: fmtTime,
    defaultSortOrder: 'descend',
    sorter: (a, b) => a.started_at.localeCompare(b.started_at),
  },
  {
    title: '耗時(秒)',
    dataIndex: 'duration_sec',
    key: 'duration_sec',
    width: 80,
    align: 'right' as const,
    render: (v: number | null) => v != null ? v.toFixed(1) : '—',
  },
  {
    title: '撈取',
    dataIndex: 'fetched',
    key: 'fetched',
    width: 60,
    align: 'right' as const,
  },
  {
    title: '寫入',
    dataIndex: 'upserted',
    key: 'upserted',
    width: 60,
    align: 'right' as const,
  },
  {
    title: '錯誤',
    dataIndex: 'errors_count',
    key: 'errors_count',
    width: 60,
    align: 'right' as const,
    render: (v: number, r: ModuleSyncLogOut) =>
      v > 0 ? (
        <Tooltip title={r.error_msg ?? '未知錯誤'}>
          <span style={{ color: '#cf1322', cursor: 'help' }}>
            <WarningOutlined style={{ marginRight: 4 }} />{v}
          </span>
        </Tooltip>
      ) : <span style={{ color: '#8c8c8c' }}>0</span>,
  },
  {
    title: '觸發',
    dataIndex: 'triggered_by',
    key: 'triggered_by',
    width: 80,
    render: (v: string) => v === 'manual'
      ? <Tag color="geekblue">手動</Tag>
      : <Tag color="default">排程</Tag>,
  },
]

const RagicConnections: React.FC = () => {
  const [currentInterval, setCurrentInterval] = useState<number | null>(null)
  const [selectedInterval, setSelectedInterval] = useState<number>(30)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [syncLogs, setSyncLogs] = useState<ModuleSyncLogOut[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [triggering, setTriggering] = useState(false)

  const loadSyncLogs = useCallback(() => {
    setLogsLoading(true)
    getRecentSyncLogs(24)
      .then(data => setSyncLogs(data))
      .catch(() => message.warning('無法載入同步紀錄，請確認後端是否已重啟'))
      .finally(() => setLogsLoading(false))
  }, [])

  const handleTriggerSync = async () => {
    setTriggering(true)
    try {
      await triggerAllModulesSync()
      message.success('已在背景啟動同步，約 1–2 分鐘後點擊「重新整理」可查看結果')
    } catch {
      message.error('觸發失敗，請確認後端服務狀態')
    } finally {
      setTriggering(false)
    }
  }

  // 載入目前設定
  useEffect(() => {
    setLoading(true)
    apiClient
      .get<{ interval_minutes: number }>('/ragic/scheduler/module-interval')
      .then(r => {
        setCurrentInterval(r.data.interval_minutes)
        setSelectedInterval(r.data.interval_minutes)
      })
      .catch(() => {
        // 無法取得時用預設值
        setCurrentInterval(30)
        setSelectedInterval(30)
      })
      .finally(() => setLoading(false))

    // 同時載入同步紀錄
    loadSyncLogs()
  }, [loadSyncLogs])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      await apiClient.post('/ragic/scheduler/module-interval', {
        interval_minutes: selectedInterval,
      })
      setCurrentInterval(selectedInterval)
      setSaved(true)
      message.success(`自動同步間隔已更新為 ${INTERVAL_OPTIONS.find(o => o.value === selectedInterval)?.label}`)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      message.error('儲存失敗，請稍後再試')
    } finally {
      setSaving(false)
    }
  }

  const isDirty = selectedInterval !== currentInterval

  return (
    <div>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>Ragic 同步排程設定</Title>
        <Text style={{ color: '#64748b' }}>設定各模組從 Ragic 自動同步資料的頻率</Text>
      </div>

      <Row gutter={[16, 16]}>
        {/* 間隔設定卡片 */}
        <Col xs={24} md={14}>
          <Card
            bordered={false}
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
            title={
              <Space>
                <ClockCircleOutlined style={{ color: '#4BA8E8' }} />
                <span>自動同步間隔</span>
                {currentInterval !== null && (
                  <Tag color="blue">目前：{INTERVAL_OPTIONS.find(o => o.value === currentInterval)?.label ?? `${currentInterval} 分鐘`}</Tag>
                )}
              </Space>
            }
          >
            {loading ? (
              <div style={{ textAlign: 'center', padding: 32 }}>
                <Spin />
              </div>
            ) : (
              <>
                <Paragraph style={{ color: '#64748b', marginBottom: 20 }}>
                  選擇各模組定時從 Ragic 拉取並更新本地資料庫的間隔。
                  間隔越短，資料越即時，但對 Ragic API 的呼叫次數也越多。
                </Paragraph>

                <Radio.Group
                  value={selectedInterval}
                  onChange={e => setSelectedInterval(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <Row gutter={[8, 8]}>
                    {INTERVAL_OPTIONS.map(opt => (
                      <Col xs={12} sm={8} key={opt.value}>
                        <Radio.Button
                          value={opt.value}
                          style={{
                            width: '100%',
                            textAlign: 'center',
                            borderRadius: 8,
                            height: 44,
                            lineHeight: '42px',
                          }}
                        >
                          {opt.label}
                        </Radio.Button>
                      </Col>
                    ))}
                  </Row>
                </Radio.Group>

                <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Button
                    type="primary"
                    icon={saved ? <CheckCircleOutlined /> : <SaveOutlined />}
                    onClick={handleSave}
                    loading={saving}
                    disabled={!isDirty || saving}
                    style={{
                      background: saved ? '#52c41a' : '#1B3A5C',
                      borderColor: saved ? '#52c41a' : '#1B3A5C',
                    }}
                  >
                    {saved ? '已套用' : '套用設定'}
                  </Button>
                  {isDirty && !saving && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      ⚠ 尚未儲存
                    </Text>
                  )}
                </div>

                <Alert
                  style={{ marginTop: 16 }}
                  type="info"
                  showIcon
                  message="整點對齊執行"
                  description={
                    <>
                      排程依整點時刻觸發，例如：
                      15 分鐘 → :00/:15/:30/:45；
                      30 分鐘 → :00/:30；
                      1 小時 → 每小時整點。
                      <br />
                      ⚠ 此為記憶體設定，服務重啟後恢復預設 30 分鐘。如需永久變更，請修改 main.py。
                    </>
                  }
                />
              </>
            )}
          </Card>
        </Col>

        {/* 涵蓋模組清單 */}
        <Col xs={24} md={10}>
          <Card
            bordered={false}
            style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
            title={
              <Space>
                <SyncOutlined style={{ color: '#4BA8E8' }} />
                <span>涵蓋模組</span>
              </Space>
            }
          >
            <Paragraph style={{ color: '#64748b', marginBottom: 12, fontSize: 13 }}>
              以下模組共用同一排程間隔，連線參數來自伺服器 .env 設定：
            </Paragraph>
            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              {MODULE_NAMES.map(name => (
                <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 13 }} />
                  <Text style={{ fontSize: 13 }}>{name}</Text>
                </div>
              ))}
            </Space>

            <div
              style={{
                marginTop: 16,
                padding: '10px 14px',
                background: '#f0f4f8',
                borderRadius: 8,
              }}
            >
              <Text style={{ fontSize: 12, color: '#64748b' }}>
                如需新增或修改 Ragic 連線帳號 / API Key，
                請聯絡系統管理員修改 <code>.env</code> 設定檔。
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 24 小時同步紀錄 */}
      <div style={{ marginTop: 24 }}>
        <Card
          bordered={false}
          style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
          title={
            <Space>
              <SyncOutlined style={{ color: '#4BA8E8' }} />
              <span>24 小時同步紀錄</span>
              <Tag color="default">{syncLogs.length} 筆</Tag>
            </Space>
          }
          extra={
            <Space>
              <Button
                size="small"
                icon={<SyncOutlined spin={triggering} />}
                loading={triggering}
                onClick={handleTriggerSync}
              >
                立即同步
              </Button>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={logsLoading}
                onClick={loadSyncLogs}
              >
                重新整理
              </Button>
            </Space>
          }
        >
          <Table<ModuleSyncLogOut>
            dataSource={syncLogs}
            columns={SYNC_LOG_COLUMNS}
            rowKey="id"
            loading={logsLoading}
            size="small"
            pagination={{ pageSize: 20, showSizeChanger: false, showTotal: t => `共 ${t} 筆` }}
            scroll={{ x: 700 }}
            locale={{ emptyText: '尚無同步紀錄（排程執行後才會顯示）' }}
            rowClassName={(r) => r.status === 'error' ? 'sync-log-row-error' : ''}
          />
        </Card>
      </div>
    </div>
  )
}

export default RagicConnections
