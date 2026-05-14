/**
 * Ragic 同步管理頁面
 * 路徑：/settings/ragic-connections
 *
 * 功能：顯示 24 小時內的同步紀錄 + 緊急立即同步按鍵
 *        自動同步間隔改由 sync_tool.py 獨立工具管理
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ReloadOutlined,
  SyncOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { getRecentSyncLogs, triggerAllModulesSync, type ModuleSyncLogOut } from '../../api/ragic'
import { triggerPurchaseSync } from '../../api/purchaseReport'

const { Title, Text } = Typography

// 狀態顏色 + 標籤
const STATUS_TAG: Record<string, { color: string; label: string }> = {
  success: { color: 'success', label: '成功' },
  error:   { color: 'error',   label: '失敗' },
  partial: { color: 'warning', label: '部分' },
  running: { color: 'processing', label: '執行中' },
}

// 格式化時間（後端存台灣時間，直接解析字串，不經 Date 物件避免 UTC 轉換）
function fmtTime(iso: string): string {
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
  const [syncLogs, setSyncLogs]       = useState<ModuleSyncLogOut[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [triggering, setTriggering]   = useState(false)

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
      await Promise.allSettled([
        triggerAllModulesSync(),
        triggerPurchaseSync(false),
      ])
      message.success('已在背景啟動所有模組同步（含核准請購單），約 1–2 分鐘後點擊「重新整理」可查看結果')
    } catch {
      message.error('觸發失敗，請確認後端服務狀態')
    } finally {
      setTriggering(false)
    }
  }

  useEffect(() => {
    loadSyncLogs()
  }, [loadSyncLogs])

  return (
    <div>
      {/* 頁面標題 */}
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>Ragic 同步紀錄</Title>
        <Text style={{ color: '#64748b' }}>
          顯示 24 小時內的模組同步狀態。自動同步間隔請於 sync_tool.py 獨立工具設定。
        </Text>
      </div>

      {/* 24 小時同步紀錄 */}
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
  )
}

export default RagicConnections
