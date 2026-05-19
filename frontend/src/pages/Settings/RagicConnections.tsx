/**
 * Ragic 同步管理頁面
 * 路徑：/settings/ragic-connections
 *
 * 功能：顯示 24 小時內的同步紀錄 + 全體立即同步 + 單一模組立即同步
 *        自動同步間隔改由 sync_tool.py 獨立工具管理
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  Col,
  Row,
  Space,
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
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import {
  getRecentSyncLogs,
  triggerAllModulesSync,
  triggerSingleModuleSync,
  type ModuleSyncLogOut,
} from '../../api/ragic'
import { triggerPurchaseSync } from '../../api/purchaseReport'

const { Title, Text } = Typography

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  success: { color: 'success', label: '成功' },
  error:   { color: 'error',   label: '失敗' },
  partial: { color: 'warning', label: '部分' },
  running: { color: 'processing', label: '執行中' },
}

const ALL_MODULES: string[] = [
  '客房保養', '倉庫庫存', '客房保養明細', '飯店週期保養',
  'B4F巡檢', 'RF巡檢', 'B2F巡檢', 'B1F巡檢',
  '商場週期保養', '全棟例行維護', '大直工務報修', '商場工務報修',
  '保全巡檢', '商場工務巡檢', '飯店每日巡檢', '每日數值登錄',
  'IHG客房保養', '核准請購單清單', '核准請款單清單',
  '日曜核准請購單清單', '日曜核准請款單清單',
]

function fmtTime(iso: string): string {
  const m = iso.match(/(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
  if (!m) return iso
  return `${m[1]}/${m[2]} ${m[3]}:${m[4]}`
}

function ModuleStatusIcon({ status }: { status?: string }) {
  if (!status) return <ClockCircleOutlined style={{ color: '#bfbfbf' }} />
  if (status === 'success') return <CheckCircleOutlined style={{ color: '#52c41a' }} />
  if (status === 'error')   return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
  if (status === 'partial') return <ExclamationCircleOutlined style={{ color: '#faad14' }} />
  return <SyncOutlined spin style={{ color: '#1677ff' }} />
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
  const [syncLogs, setSyncLogs]             = useState<ModuleSyncLogOut[]>([])
  const [logsLoading, setLogsLoading]       = useState(false)
  const [triggering, setTriggering]         = useState(false)
  const [syncingModules, setSyncingModules] = useState<Set<string>>(new Set())

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

  const handleSingleModuleSync = async (moduleName: string) => {
    setSyncingModules(prev => new Set(prev).add(moduleName))
    try {
      await triggerSingleModuleSync(moduleName)
      message.success(`${moduleName} 同步已在背景啟動，約 30 秒後重新整理可查看結果`)
    } catch {
      message.error(`${moduleName} 觸發失敗`)
    } finally {
      setSyncingModules(prev => {
        const next = new Set(prev)
        next.delete(moduleName)
        return next
      })
    }
  }

  const latestModuleStatus = useMemo(() => {
    const map: Record<string, ModuleSyncLogOut> = {}
    for (const log of syncLogs) {
      if (!map[log.module_name] ||
          log.started_at > map[log.module_name].started_at) {
        map[log.module_name] = log
      }
    }
    return map
  }, [syncLogs])

  useEffect(() => {
    loadSyncLogs()
  }, [loadSyncLogs])

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>Ragic 同步管理</Title>
        <Text style={{ color: '#64748b' }}>
          顯示 24 小時內的模組同步狀態。自動同步間隔請於 sync_tool.py 獨立工具設定。
        </Text>
      </div>

      <Card
        bordered={false}
        style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', marginBottom: 16 }}
        title={
          <Space>
            <SyncOutlined style={{ color: '#4BA8E8' }} />
            <span>模組快速同步</span>
          </Space>
        }
        extra={
          <Button
            size="small"
            icon={<SyncOutlined spin={triggering} />}
            loading={triggering}
            onClick={handleTriggerSync}
          >
            全部立即同步
          </Button>
        }
      >
        <Row gutter={[8, 8]}>
          {ALL_MODULES.map(moduleName => {
            const latest = latestModuleStatus[moduleName]
            const isSyncing = syncingModules.has(moduleName)
            return (
              <Col key={moduleName} xs={12} sm={8} md={6} lg={4}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 10px',
                  borderRadius: 8,
                  border: '1px solid #f0f0f0',
                  background: '#fafafa',
                  gap: 6,
                }}>
                  <Space size={4} style={{ minWidth: 0, flex: 1, overflow: 'hidden' }}>
                    <ModuleStatusIcon status={isSyncing ? 'running' : latest?.status} />
                    <Tooltip title={latest
                      ? `上次：${fmtTime(latest.started_at)}　撈取 ${latest.fetched} / 寫入 ${latest.upserted}`
                      : '尚無同步紀錄'
                    }>
                      <Text
                        style={{
                          fontSize: 12,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: 80,
                          display: 'block',
                        }}
                      >
                        {moduleName}
                      </Text>
                    </Tooltip>
                  </Space>
                  <Button
                    size="small"
                    type="text"
                    icon={<SyncOutlined spin={isSyncing} />}
                    loading={isSyncing}
                    onClick={() => handleSingleModuleSync(moduleName)}
                    style={{ padding: '0 4px', flexShrink: 0 }}
                    title={`立刻同步 ${moduleName}`}
                  />
                </div>
              </Col>
            )
          })}
        </Row>
      </Card>

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
          <Button
            size="small"
            icon={<ReloadOutlined />}
            loading={logsLoading}
            onClick={loadSyncLogs}
          >
            重新整理
          </Button>
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
