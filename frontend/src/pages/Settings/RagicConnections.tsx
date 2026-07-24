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
  Tabs,
  Tag,
  Modal,
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
  SearchOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import {
  getRecentSyncLogs,
  triggerAllModulesSync,
  triggerSingleModuleSync,
  verifyModuleCount,
  verifyModuleDiff,
  type ModuleSyncLogOut,
  type VerifyCountResult,
  type VerifyDiffResult,
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
  '主管交辦／緊急事件', '週期保養預排', '飯店例行維護',
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

  // ── 資料比對 Tab 狀態 ────────────────────────────────────────────────────
  // 涵蓋範圍：大直/商場工務報修（原有）+ 工作日誌彙整用到的其餘 12 個來源模組
  // （2026-07-24 擴充，見 work_journal.py 彙整清單）。往後其他模組要接上比對，
  // 只需在 verifyModules 陣列加一筆設定，不需要改這個 TAB 的其他程式碼。
  const [verifyResults, setVerifyResults] = useState<Record<string, VerifyCountResult | null>>({})
  const [verifying, setVerifying] = useState<Record<string, boolean>>({})

  const [diffModalOpen, setDiffModalOpen] = useState(false)
  const [diffModuleName, setDiffModuleName] = useState('')
  const [diffResult, setDiffResult] = useState<VerifyDiffResult | null>(null)
  const [diffLoading, setDiffLoading] = useState(false)

  const handleShowDiff = async (key: string, name: string, apiPrefix: string) => {
    setDiffModuleName(name)
    setDiffResult(null)
    setDiffModalOpen(true)
    setDiffLoading(true)
    try {
      const result = await verifyModuleDiff(apiPrefix)
      setDiffResult(result)
    } catch {
      message.error('取得差異明細失敗')
      setDiffModalOpen(false)
    } finally {
      setDiffLoading(false)
    }
  }

  const handleVerify = async (key: string, apiPrefix: string) => {
    setVerifying(prev => ({ ...prev, [key]: true }))
    try {
      const result = await verifyModuleCount(apiPrefix)
      setVerifyResults(prev => ({ ...prev, [key]: result }))
      if (result.match) {
        message.success(`${result.module}：資料一致（${result.portal_count} 筆）`)
      } else {
        message.warning(`${result.module}：差異 ${result.diff > 0 ? '+' : ''}${result.diff} 筆`)
      }
    } catch {
      message.error('比對失敗，請確認後端服務狀態')
    } finally {
      setVerifying(prev => ({ ...prev, [key]: false }))
    }
  }

  const verifyModules = [
    { key: 'dazhi',        name: '飯店工務報修',      desc: 'lequn-public-works/8',                          apiPrefix: '/dazhi-repair',              ragicUrl: 'https://ap12.ragic.com/soutlet001/lequn-public-works/8?PAGEID=fV8' },
    { key: 'luqun',        name: '商場工務報修',      desc: 'luqun-public-works-repair-reporting-system/6', apiPrefix: '/luqun-repair',               ragicUrl: 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/6' },
    { key: 'hotel_pm',     name: '飯店週期保養',      desc: 'periodic-maintenance/11',                      apiPrefix: '/periodic-maintenance',       ragicUrl: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/11' },
    { key: 'ihg',          name: 'IHG客房保養',       desc: 'periodic-maintenance/4',                       apiPrefix: '/ihg-room-maintenance',       ragicUrl: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/4' },
    { key: 'mall_pm',      name: '商場週期保養',      desc: 'periodic-maintenance/18',                      apiPrefix: '/mall/periodic-maintenance',  ragicUrl: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/18' },
    { key: 'full_bldg_pm', name: '全棟例行維護',      desc: 'periodic-maintenance/21',                      apiPrefix: '/mall/full-building-maintenance', ragicUrl: 'https://ap12.ragic.com/soutlet001/periodic-maintenance/21' },
    { key: 'hotel_di',     name: '飯店每日巡檢',      desc: 'main-project-inspection/17~21（5張Sheet加總）', apiPrefix: '/hotel-daily-inspection',     ragicUrl: 'https://ap12.ragic.com/soutlet001/main-project-inspection/17' },
    { key: 'mall_fi',      name: '商場工務巡檢',      desc: 'mall-facility-inspection/2,3,4,5,7（5張Sheet加總）', apiPrefix: '/mall-facility-inspection', ragicUrl: 'https://ap12.ragic.com/soutlet001/mall-facility-inspection/2' },
    { key: 'hotel_mr',     name: '每日數值登錄',      desc: 'hotel-routine-inspection/11,12,14,15（4張Sheet加總）', apiPrefix: '/hotel-meter-readings', ragicUrl: 'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/11' },
    { key: 'b1f',          name: 'B1F巡檢',          desc: 'full-building-inspection/4',                   apiPrefix: '/mall/b1f-inspection',        ragicUrl: 'https://ap12.ragic.com/soutlet001/full-building-inspection/4' },
    { key: 'b2f',          name: 'B2F巡檢',          desc: 'full-building-inspection/3',                   apiPrefix: '/mall/b2f-inspection',        ragicUrl: 'https://ap12.ragic.com/soutlet001/full-building-inspection/3' },
    { key: 'b4f',          name: 'B4F巡檢',          desc: 'full-building-inspection/2',                   apiPrefix: '/mall/b4f-inspection',        ragicUrl: 'https://ap12.ragic.com/soutlet001/full-building-inspection/2' },
    { key: 'rf',           name: 'RF巡檢',           desc: 'full-building-inspection/1',                   apiPrefix: '/mall/rf-inspection',         ragicUrl: 'https://ap12.ragic.com/soutlet001/full-building-inspection/1' },
    { key: 'other_tasks',  name: '主管交辦／緊急事件', desc: 'other-tasks/1',                               apiPrefix: '/other-tasks',                ragicUrl: 'https://ap12.ragic.com/soutlet001/other-tasks/1' },
  ]

  const VerifyTab = (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Tag color="blue">管理員功能</Tag>
        <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
          即時向 Ragic 查詢筆數，與本地 DB 比對。每次比對約需 10–30 秒；多張 Sheet 彙總的模組（飯店每日巡檢／商場工務巡檢／每日數值登錄）需逐張查詢，會更久一些。
          涵蓋範圍為「工作日誌」彙整所用到的全部來源模組。
        </Typography.Text>
      </div>
      {verifyModules.map(({ key, name, desc, ragicUrl, apiPrefix }) => {
        const r = verifyResults[key] ?? null
        const loading = verifying[key] ?? false
        let statusTag = <Tag color="default">尚未比對</Tag>
        if (r) {
          if (r.match)         statusTag = <Tag color="success" icon={<CheckCircleOutlined />}>一致</Tag>
          else if (Math.abs(r.diff) <= 5) statusTag = <Tag color="warning" icon={<WarningOutlined />}>小差異</Tag>
          else                 statusTag = <Tag color="error"   icon={<CloseCircleOutlined />}>差異過大</Tag>
        }
        return (
          <Card
            key={key}
            size="small"
            style={{ marginBottom: 12, borderRadius: 8 }}
            styles={{ body: { padding: '16px 20px' } }}
          >
            <Row align="middle" gutter={16}>
              <Col flex="200px">
                <Space direction="vertical" size={2}>
                  <Typography.Text strong>{name}</Typography.Text>
                  <Typography.Text type="secondary" style={{ fontSize: 11 }}>{desc}</Typography.Text>
                </Space>
              </Col>
              <Col flex="1">
                {r ? (
                  <Row gutter={24} align="middle">
                    <Col>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>Portal DB</Typography.Text>
                      <div><Typography.Text strong style={{ fontSize: 20, color: '#1B3A5C' }}>{r.portal_count.toLocaleString()}</Typography.Text> <Typography.Text type="secondary">筆</Typography.Text></div>
                    </Col>
                    <Col>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>Ragic</Typography.Text>
                      <div><Typography.Text strong style={{ fontSize: 20, color: '#4BA8E8' }}>{r.ragic_count.toLocaleString()}</Typography.Text> <Typography.Text type="secondary">筆</Typography.Text></div>
                    </Col>
                    <Col>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>差異</Typography.Text>
                      <div>
                        <Typography.Text strong style={{ fontSize: 18, color: r.diff === 0 ? '#52C41A' : r.diff > 0 ? '#FAAD14' : '#FF4D4F' }}>
                          {r.diff > 0 ? `+${r.diff}` : r.diff}
                        </Typography.Text>
                      </div>
                    </Col>
                    <Col>{statusTag}</Col>
                    <Col>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                        {r.last_synced_at ? `上次同步：${r.last_synced_at.slice(5, 16).replace('T', ' ')}` : '尚無同步紀錄'}
                      </Typography.Text>
                    </Col>
                  </Row>
                ) : (
                  <Typography.Text type="secondary">點擊「比對」取得即時數量</Typography.Text>
                )}
              </Col>
              <Col>
                <Space>
                  <Button
                    icon={<SearchOutlined />}
                    loading={loading}
                    onClick={() => handleVerify(key, apiPrefix)}
                  >
                    比對
                  </Button>
                  {r && !r.match && (
                    <Button
                      size="small"
                      onClick={() => handleShowDiff(key, name, apiPrefix)}
                    >
                      查看差異
                    </Button>
                  )}
                  <Tooltip title="在 Ragic 查看原始資料">
                    <a href={ragicUrl} target="_blank" rel="noopener noreferrer">
                      <Button icon={<LinkOutlined />} size="small" />
                    </a>
                  </Tooltip>
                </Space>
              </Col>
            </Row>
          </Card>
        )
      })}
    </div>
  )

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>Ragic 同步管理</Title>
        <Text style={{ color: '#64748b' }}>
          顯示 24 小時內的模組同步狀態。自動同步間隔請於 sync_tool.py 獨立工具設定。
        </Text>
      </div>
      <Tabs
        defaultActiveKey="sync"
        items={[
          { key: 'sync',   label: '同步管理', children: (
            <div>
              <Card
                bordered={false}
                style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', marginBottom: 16 }}
                title={<Space><SyncOutlined style={{ color: '#4BA8E8' }} /><span>模組快速同步</span></Space>}
                extra={<Button size="small" icon={<SyncOutlined spin={triggering} />} loading={triggering} onClick={handleTriggerSync}>全部立即同步</Button>}
              >
                <Row gutter={[8, 8]}>
                  {ALL_MODULES.map(moduleName => {
                    const latest = latestModuleStatus[moduleName]
                    const isSyncing = syncingModules.has(moduleName)
                    return (
                      <Col key={moduleName} xs={12} sm={8} md={6} lg={4}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', borderRadius: 8, border: '1px solid #f0f0f0', background: '#fafafa', gap: 6 }}>
                          <Space size={4} style={{ minWidth: 0, flex: 1, overflow: 'hidden' }}>
                            <ModuleStatusIcon status={isSyncing ? 'running' : latest?.status} />
                            <Tooltip title={latest ? `上次：${fmtTime(latest.started_at)}　撈取 ${latest.fetched} / 寫入 ${latest.upserted}` : '尚無同步紀錄'}>
                              <Text style={{ fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 80, display: 'block' }}>{moduleName}</Text>
                            </Tooltip>
                          </Space>
                          <Button size="small" type="text" icon={<SyncOutlined spin={isSyncing} />} loading={isSyncing} onClick={() => handleSingleModuleSync(moduleName)} style={{ padding: '0 4px', flexShrink: 0 }} title={`立刻同步 ${moduleName}`} />
                        </div>
                      </Col>
                    )
                  })}
                </Row>
              </Card>
              <Card
                bordered={false}
                style={{ borderRadius: 12, boxShadow: '0 1px 4px rgba(0,0,0,0.06)' }}
                title={<Space><SyncOutlined style={{ color: '#4BA8E8' }} /><span>24 小時同步紀錄</span><Tag color="default">{syncLogs.length} 筆</Tag></Space>}
                extra={<Button size="small" icon={<ReloadOutlined />} loading={logsLoading} onClick={loadSyncLogs}>重新整理</Button>}
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
          )},
          { key: 'verify', label: '資料比對', children: VerifyTab },
        ]}
      />
      <Modal
        open={diffModalOpen}
        title={`${diffModuleName}｜差異明細`}
        onCancel={() => setDiffModalOpen(false)}
        footer={<Button onClick={() => setDiffModalOpen(false)}>關閉</Button>}
        width={620}
      >
        {diffLoading && <div style={{ textAlign: 'center', padding: 32 }}><SyncOutlined spin style={{ fontSize: 24 }} /> 正在比對，請稍候...</div>}
        {diffResult && !diffLoading && (
          <div>
            {diffResult.in_ragic_not_portal.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <Typography.Text strong style={{ color: '#d46b08' }}>
                  ⚠️ Ragic 有、Portal 缺少（{diffResult.in_ragic_not_portal.length} 筆）
                </Typography.Text>
                <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>這些記錄在 Ragic 存在但尚未同步到本地</Typography.Text>
                <Table
                  size="small"
                  style={{ marginTop: 8 }}
                  dataSource={diffResult.in_ragic_not_portal}
                  rowKey="ragic_id"
                  pagination={false}
                  columns={[
                    { title: 'Ragic ID', dataIndex: 'ragic_id', width: 100 },
                    {
                      title: '連結',
                      render: (_, row) => row.ragic_url
                        ? <a href={row.ragic_url} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>在 Ragic 查看 <LinkOutlined /></a>
                        : '—'
                    },
                  ]}
                />
              </div>
            )}
            {diffResult.in_portal_not_ragic.length > 0 && (
              <div>
                <Typography.Text strong style={{ color: '#cf1322' }}>
                  ❌ Portal 有、Ragic 已刪除（{diffResult.in_portal_not_ragic.length} 筆）
                </Typography.Text>
                <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>這些記錄在 Ragic 已不存在，但仍保留在本地 DB</Typography.Text>
                <Table
                  size="small"
                  style={{ marginTop: 8 }}
                  dataSource={diffResult.in_portal_not_ragic}
                  rowKey="ragic_id"
                  pagination={false}
                  columns={[
                    { title: 'Ragic ID', dataIndex: 'ragic_id', width: 100 },
                    { title: '案號', dataIndex: 'case_no', width: 120 },
                    { title: '標題', dataIndex: 'title', ellipsis: true },
                    { title: '狀態', dataIndex: 'status', width: 80 },
                  ]}
                />
              </div>
            )}
            {diffResult.in_ragic_not_portal.length === 0 && diffResult.in_portal_not_ragic.length === 0 && (
              <Typography.Text type="secondary">無差異</Typography.Text>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default RagicConnections
