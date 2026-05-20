/**
 * Ragic 與 Portal 欄位比對
 * 路徑：/settings/ragic-field-audit
 *
 * 功能：稽核 Ragic 表單與 Portal 模組之間的欄位對應關係，
 * 找出異常欄位、未對應欄位，並提供 KPI 計算來源追溯。
 */

import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Input,
  message,
  Modal,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Switch,
  Table,
  Tag,
  Tabs,
  Tooltip,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  AuditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
  WarningOutlined,
} from '@ant-design/icons'

import {
  fetchAuditSummary,
  fetchModules,
  fetchModuleDetail,
  fetchIssues,
  fetchKpiMappings,
  runAudit,
  exportExcel,
  resolveMappingIssue,
  fetchAuditRuns,
  syncRagicFields,
  setModuleRagicUrl,
  type AuditSummary,
  type ModuleOverview,
  type FieldMapping,
  type KpiMapping,
} from '@/api/ragicFieldAudit'

const { Title, Text, Link } = Typography
const { Search } = Input

// ── 顏色常數 ──────────────────────────────────────────────────────────────────
const COLOR = {
  brand:   '#1B3A5C',
  accent:  '#4BA8E8',
  sidebar: '#111827',
  bg:      '#f0f4f8',
}

// ── 狀態工具函數 ──────────────────────────────────────────────────────────────

function statusBadge(status: string) {
  const map: Record<string, { status: 'success' | 'warning' | 'error' | 'default'; text: string }> = {
    normal:      { status: 'success', text: '正常' },
    warning:     { status: 'warning', text: '注意' },
    error:       { status: 'error',   text: '異常' },
    not_audited: { status: 'default', text: '尚未比對' },
  }
  const cfg = map[status] ?? { status: 'default', text: status }
  return <Badge status={cfg.status} text={cfg.text} />
}

function mappingStatusTag(status: string) {
  const map: Record<string, { color: string; label: string }> = {
    normal:            { color: 'success',  label: '正常' },
    ragic_only:        { color: 'error',    label: 'Ragic 有 / Portal 無' },
    portal_only:       { color: 'orange',   label: 'Portal 有 / Ragic 無' },
    name_mismatch:     { color: 'gold',     label: '名稱疑似不同' },
    type_mismatch:     { color: 'red',      label: '型態不一致' },
    null_rate_high:    { color: 'volcano',  label: '空值率異常' },
    formula_unmarked:  { color: 'purple',   label: '公式欄位未標示' },
    subtable_unmarked: { color: 'magenta',  label: '子表格未處理' },
    unmapped:          { color: 'default',  label: '未建立 Mapping' },
  }
  const cfg = map[status] ?? { color: 'default', label: status }
  return <Tag color={cfg.color}>{cfg.label}</Tag>
}

function severityTag(sev: string | null) {
  if (!sev) return null
  const map: Record<string, { color: string; label: string }> = {
    high:   { color: 'error',   label: '高' },
    medium: { color: 'warning', label: '中' },
    low:    { color: 'default', label: '低' },
  }
  const cfg = map[sev] ?? { color: 'default', label: sev }
  return <Tag color={cfg.color}>{cfg.label}</Tag>
}

function traceStatusTag(ts: string) {
  const map: Record<string, { color: string; label: string }> = {
    traceable:   { color: 'success', label: '可追溯' },
    partial:     { color: 'warning', label: '部分可追溯' },
    untraceable: { color: 'error',   label: '無法追溯' },
    unknown:     { color: 'default', label: '未確認' },
  }
  const cfg = map[ts] ?? { color: 'default', label: ts }
  return <Tag color={cfg.color}>{cfg.label}</Tag>
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function RagicFieldAuditPage() {
  const [activeTab, setActiveTab] = useState('overview')
  const [summary, setSummary] = useState<AuditSummary | null>(null)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [runningAudit, setRunningAudit] = useState(false)

  const loadSummary = useCallback(async () => {
    setLoadingSummary(true)
    try {
      const data = await fetchAuditSummary()
      setSummary(data)
    } catch {
      message.error('載入摘要失敗')
    } finally {
      setLoadingSummary(false)
    }
  }, [])

  useEffect(() => { loadSummary() }, [loadSummary])

  const handleRunAudit = async () => {
    Modal.confirm({
      title: '執行欄位比對稽核',
      content: '系統將掃描本地 DB schema，與 Portal 設定進行比對，並生成/更新比對紀錄。此操作可能需要數秒，是否繼續？',
      okText: '執行',
      cancelText: '取消',
      onOk: async () => {
        setRunningAudit(true)
        try {
          const result = await runAudit('all')
          message.success(
            `比對完成！共比對 ${result.total_modules} 個模組，` +
            `新建 ${result.created_mappings} 筆 Mapping 紀錄。`
          )
          await loadSummary()
        } catch (e: any) {
          message.error(`比對失敗：${e?.response?.data?.detail || '請稍後再試'}`)
        } finally {
          setRunningAudit(false)
        }
      },
    })
  }

  const handleExport = async () => {
    try {
      await exportExcel()
      message.success('Excel 報告已下載')
    } catch {
      message.error('匯出失敗')
    }
  }

  return (
    <div style={{ padding: '24px', background: COLOR.bg, minHeight: '100vh' }}>
      {/* ── 頁面標題 ─────────────────────────────────────────────────────── */}
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <Title level={4} style={{ color: COLOR.brand, margin: 0 }}>
            <AuditOutlined style={{ marginRight: 8 }} />
            Ragic 與 Portal 欄位比對
          </Title>
          <Text type="secondary">
            稽核 Ragic 表單與 Portal 模組之間的欄位對應關係，找出異常欄位與未對應欄位
          </Text>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadSummary}
            loading={loadingSummary}
          >
            重新整理
          </Button>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleRunAudit}
            loading={runningAudit}
            style={{ background: COLOR.brand }}
          >
            執行比對
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleExport}
          >
            匯出報告
          </Button>
        </Space>
      </div>

      {/* ── KPI Card ─────────────────────────────────────────────────────── */}
      <Spin spinning={loadingSummary}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          {[
            {
              title: '已設定模組數',
              value: summary?.total_modules ?? '—',
              icon: <DatabaseOutlined style={{ color: COLOR.accent }} />,
              color: COLOR.brand,
            },
            {
              title: '已完成比對',
              value: summary?.audited_modules ?? '—',
              icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
              color: '#52c41a',
            },
            {
              title: '正常模組數',
              value: summary?.normal_modules ?? '—',
              icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
              color: '#52c41a',
            },
            {
              title: '異常模組數',
              value: summary?.error_modules ?? '—',
              icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
              color: '#ff4d4f',
            },
            {
              title: '未對應欄位數',
              value: summary?.unmapped_fields ?? '—',
              icon: <QuestionCircleOutlined style={{ color: '#faad14' }} />,
              color: '#faad14',
            },
            {
              title: '高風險異常數',
              value: summary?.high_risk_issues ?? '—',
              icon: <WarningOutlined style={{ color: '#ff4d4f' }} />,
              color: '#ff4d4f',
              highlight: (summary?.high_risk_issues ?? 0) > 0,
            },
          ].map((kpi, i) => (
            <Col xs={12} sm={8} md={4} key={i}>
              <Card
                size="small"
                bordered
                style={{
                  background: kpi.highlight ? '#fff5f5' : '#fff',
                  border: kpi.highlight ? '1px solid #ffccc7' : undefined,
                }}
              >
                <Statistic
                  title={<Text style={{ fontSize: 12 }}>{kpi.title}</Text>}
                  value={kpi.value}
                  prefix={kpi.icon}
                  valueStyle={{ color: kpi.color, fontSize: 20 }}
                />
              </Card>
            </Col>
          ))}
        </Row>
      </Spin>

      {/* 最近比對時間提示 */}
      {summary?.last_run_time && (
        <Alert
          type="info"
          showIcon
          message={`最近一次比對：${new Date(summary.last_run_time).toLocaleString('zh-TW')}　狀態：${summary.last_run_status === 'completed' ? '已完成' : summary.last_run_status}`}
          style={{ marginBottom: 16 }}
          closable
        />
      )}

      {/* ── 主要 Tab ─────────────────────────────────────────────────────── */}
      <Card bodyStyle={{ padding: '0 0 24px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          style={{ padding: '0 24px' }}
          items={[
            { key: 'overview',    label: '模組總覽',           children: <TabOverview /> },
            { key: 'mapping',     label: '欄位 Mapping 明細',  children: <TabMapping /> },
            { key: 'issues',      label: '異常清單',           children: <TabIssues onResolve={loadSummary} /> },
            { key: 'kpi',         label: 'KPI / Dashboard 追溯', children: <TabKpi /> },
            { key: 'export',      label: '匯出報告',           children: <TabExport onExport={handleExport} onRunAudit={handleRunAudit} runningAudit={runningAudit} /> },
          ]}
        />
      </Card>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// Tab 1：模組總覽
// ═══════════════════════════════════════════════════════════════════════════

function TabOverview() {
  const [data, setData] = useState<ModuleOverview[]>([])
  const [loading, setLoading] = useState(false)
  const [filterCompany, setFilterCompany] = useState<string>()
  const [filterStatus, setFilterStatus] = useState<string>()
  const [keyword, setKeyword] = useState('')
  const [detailRoute, setDetailRoute] = useState<string | null>(null)
  const [detailRagicUrl, setDetailRagicUrl] = useState<string>('')
  const [syncingItemNo, setSyncingItemNo] = useState<number | null>(null)
  // ── Ragic URL 設定 Modal ──
  const [urlModalOpen, setUrlModalOpen]   = useState(false)
  const [urlEditItem, setUrlEditItem]     = useState<ModuleOverview | null>(null)
  const [urlInputValue, setUrlInputValue] = useState('')
  const [urlSaving, setUrlSaving]         = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchModules({
        company: filterCompany,
        status: filterStatus,
        keyword: keyword || undefined,
      })
      setData(res.items)
    } catch {
      message.error('載入模組清單失敗')
    } finally {
      setLoading(false)
    }
  }, [filterCompany, filterStatus, keyword])

  useEffect(() => { load() }, [load])

  const handleSyncRagic = async (itemNo: number, ragicUrl: string) => {
    if (!ragicUrl) {
      message.warning('此模組尚無已知的 Ragic 表單 URL，請先確認 RAGIC_URL_MAP 設定')
      return
    }
    setSyncingItemNo(itemNo)
    try {
      const result = await syncRagicFields(itemNo, ragicUrl)
      const errNote = result.fetch_error ? `（注意：${result.fetch_error}）` : ''
      message.success(
        `同步完成！發現 ${result.ragic_field_count} 個 Ragic 欄位，` +
        `新增 ${result.synced_count} 筆、更新 ${result.updated_count} 筆。${errNote}`
      )
      await load()
    } catch (e: any) {
      message.error(`同步失敗：${e?.response?.data?.detail || '請確認 Ragic API 連線正常'}`)
    } finally {
      setSyncingItemNo(null)
    }
  }

  const openUrlModal = (mod: ModuleOverview) => {
    setUrlEditItem(mod)
    setUrlInputValue(mod.ragic_url || '')
    setUrlModalOpen(true)
  }

  const handleSaveRagicUrl = async () => {
    if (!urlEditItem) return
    setUrlSaving(true)
    try {
      await setModuleRagicUrl(urlEditItem.item_no, urlInputValue.trim())
      message.success(
        urlInputValue.trim()
          ? `Ragic URL 已儲存，可直接點擊連結或執行「同步欄位」。`
          : 'Ragic URL 已清除。'
      )
      setUrlModalOpen(false)
      await load()
    } catch (e: any) {
      message.error(`儲存失敗：${e?.response?.data?.detail || '請稍後重試'}`)
    } finally {
      setUrlSaving(false)
    }
  }

  const columns: ColumnsType<ModuleOverview> = [
    {
      title: '公司/據點',
      dataIndex: 'company',
      width: 90,
      render: (v) => <Tag>{v || '—'}</Tag>,
    },
    {
      title: 'Portal 模組名稱',
      dataIndex: 'portal_name',
      width: 160,
      render: (v, r) => (
        <a onClick={() => setDetailRoute(r.portal_route)} style={{ color: '#1B3A5C' }}>
          {v || r.module_name || '—'}
        </a>
      ),
    },
    {
      title: 'Portal 路由',
      dataIndex: 'portal_route',
      width: 220,
      render: (v) => <Text code style={{ fontSize: 11 }}>{v}</Text>,
    },
    {
      title: 'DB Table',
      dataIndex: 'local_tables',
      width: 200,
      render: (v: string[]) => v?.map((t) => <Tag key={t} style={{ fontSize: 11 }}>{t}</Tag>),
    },
    {
      title: 'DB 欄位數',
      dataIndex: 'portal_db_field_count',
      width: 80,
      align: 'center',
    },
    {
      title: 'API 欄位數',
      dataIndex: 'portal_api_field_count',
      width: 80,
      align: 'center',
    },
    {
      title: '前端欄位數',
      dataIndex: 'portal_fe_field_count',
      width: 80,
      align: 'center',
    },
    {
      title: '正常',
      dataIndex: 'normal_count',
      width: 60,
      align: 'center',
      render: (v) => v > 0 ? <Text style={{ color: '#52c41a' }}>{v}</Text> : '—',
    },
    {
      title: '異常',
      dataIndex: 'issue_count',
      width: 60,
      align: 'center',
      render: (v) => v > 0 ? <Text style={{ color: '#ff4d4f' }}>{v}</Text> : '—',
    },
    {
      title: '未對應',
      dataIndex: 'unmapped_count',
      width: 70,
      align: 'center',
      render: (v) => v > 0 ? <Text style={{ color: '#faad14' }}>{v}</Text> : '—',
    },
    {
      title: '最近比對',
      dataIndex: 'last_checked_at',
      width: 130,
      render: (v) => v ? new Date(v).toLocaleString('zh-TW', { dateStyle: 'short', timeStyle: 'short' }) : '—',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      width: 90,
      render: (v) => statusBadge(v),
    },
    {
      title: 'Ragic 連結',
      dataIndex: 'ragic_url',
      width: 120,
      align: 'center' as const,
      render: (v: string, r: ModuleOverview) => (
        <Space size={4}>
          {v ? (
            <Tooltip title={v}>
              <a href={v} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>
                <LinkOutlined /> 查看
              </a>
            </Tooltip>
          ) : (
            <Text type="secondary" style={{ fontSize: 11 }}>未設定</Text>
          )}
          <Tooltip title={v ? '編輯 Ragic URL' : '設定 Ragic URL'}>
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              style={{ color: v ? '#4BA8E8' : '#aaa' }}
              onClick={() => openUrlModal(r)}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: '操作',
      width: 180,
      render: (_, r) => (
        <Space size={4}>
          <Button
            size="small"
            onClick={() => { setDetailRoute(r.portal_route); setDetailRagicUrl(r.ragic_url || '') }}
          >
            查看明細
          </Button>
          <Tooltip title={r.ragic_url ? `從 Ragic 抓取欄位定義：${r.ragic_url}` : '請先設定此模組的 Ragic URL'}>
            <Button
              size="small"
              icon={<SyncOutlined />}
              loading={syncingItemNo === r.item_no}
              disabled={!r.ragic_url}
              onClick={() => handleSyncRagic(r.item_no, r.ragic_url)}
            >
              同步欄位
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ paddingTop: 16 }}>
      {/* 篩選列 */}
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          placeholder="公司/據點"
          allowClear
          style={{ width: 120 }}
          onChange={setFilterCompany}
          options={[
            { value: '飯店', label: '飯店' },
            { value: '商場', label: '商場' },
            { value: '全棟', label: '全棟' },
            { value: '資訊部', label: '資訊部' },
          ]}
        />
        <Select
          placeholder="狀態"
          allowClear
          style={{ width: 120 }}
          onChange={setFilterStatus}
          options={[
            { value: 'normal',      label: '正常' },
            { value: 'warning',     label: '注意' },
            { value: 'error',       label: '異常' },
            { value: 'not_audited', label: '尚未比對' },
          ]}
        />
        <Search
          placeholder="搜尋模組名稱 / 路由"
          allowClear
          style={{ width: 240 }}
          onSearch={setKeyword}
        />
        <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey={(r) => `${r.portal_route}_${r.item_no}`}
        loading={loading}
        size="small"
        scroll={{ x: 1700 }}
        pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 個模組` }}
        rowClassName={(r) =>
          r.status === 'error' ? 'row-error' :
          r.status === 'warning' ? 'row-warning' : ''
        }
      />

      {/* 明細 Drawer */}
      <ModuleDetailDrawer
        route={detailRoute}
        ragicUrl={detailRagicUrl}
        onClose={() => { setDetailRoute(null); setDetailRagicUrl('') }}
      />

      {/* Ragic URL 設定 Modal */}
      <Modal
        title={
          <Space>
            <LinkOutlined style={{ color: '#4BA8E8' }} />
            {urlEditItem?.ragic_url ? '編輯 Ragic 表單 URL' : '設定 Ragic 表單 URL'}
          </Space>
        }
        open={urlModalOpen}
        onCancel={() => setUrlModalOpen(false)}
        onOk={handleSaveRagicUrl}
        okText="儲存"
        cancelText="取消"
        confirmLoading={urlSaving}
        destroyOnClose
      >
        {urlEditItem && (
          <div style={{ marginBottom: 16 }}>
            <Text type="secondary">模組：</Text>
            <Text strong>{urlEditItem.portal_name || urlEditItem.module_name}</Text>
            <Text type="secondary" style={{ marginLeft: 8 }}>（{urlEditItem.portal_route}）</Text>
          </div>
        )}
        <Input
          placeholder="https://ap12.ragic.com/soutlet001/..."
          value={urlInputValue}
          onChange={(e) => setUrlInputValue(e.target.value)}
          allowClear
          prefix={<LinkOutlined style={{ color: '#aaa' }} />}
          style={{ marginBottom: 8 }}
        />
        <Alert
          type="info"
          showIcon
          style={{ fontSize: 12 }}
          message="填入 Ragic 表單的完整網址，儲存後即可使用「同步欄位」抓取 Ragic 所有欄位定義。此 URL 會持久化儲存，之後進入此頁面自動帶入。"
        />
        {urlInputValue && (
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>預覽連結：</Text>
            <a href={urlInputValue} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8', fontSize: 12, marginLeft: 8 }}>
              <LinkOutlined /> 在新分頁開啟確認
            </a>
          </div>
        )}
      </Modal>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// Tab 2：欄位 Mapping 明細（含 Drawer 選模組）
// ═══════════════════════════════════════════════════════════════════════════

function TabMapping() {
  const [modules, setModules] = useState<ModuleOverview[]>([])
  const [selectedRoute, setSelectedRoute] = useState<string>()
  const [selectedRagicUrl, setSelectedRagicUrl] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>()
  const [onlyIssues, setOnlyIssues] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [data, setData] = useState<FieldMapping[]>([])
  const [loading, setLoading] = useState(false)
  const [syncingTab2, setSyncingTab2] = useState(false)

  useEffect(() => {
    fetchModules().then((r) => setModules(r.items)).catch(() => {})
  }, [])

  const loadDetail = useCallback(async () => {
    if (!selectedRoute) return
    setLoading(true)
    try {
      const res = await fetchModuleDetail(selectedRoute)
      setData(res.items)
    } catch {
      message.error('載入欄位明細失敗')
    } finally {
      setLoading(false)
    }
  }, [selectedRoute])

  useEffect(() => { loadDetail() }, [loadDetail])

  const filtered = data.filter((d) => {
    if (onlyIssues && !['ragic_only', 'portal_only', 'name_mismatch', 'type_mismatch', 'null_rate_high', 'formula_unmarked', 'subtable_unmarked'].includes(d.mapping_status)) return false
    if (filterStatus && d.mapping_status !== filterStatus) return false
    if (keyword) {
      const kw = keyword.toLowerCase()
      return (d.portal_db_field || '').toLowerCase().includes(kw) ||
             (d.ragic_field_name || '').toLowerCase().includes(kw) ||
             (d.display_name || '').toLowerCase().includes(kw)
    }
    return true
  })

  const columns: ColumnsType<FieldMapping> = [
    {
      title: 'DB Table',
      dataIndex: 'portal_db_table',
      width: 200,
      render: (v) => <Text code style={{ fontSize: 11 }}>{v}</Text>,
    },
    {
      title: 'DB 欄位',
      dataIndex: 'portal_db_field',
      width: 160,
      render: (v) => <Text strong style={{ fontSize: 12 }}>{v}</Text>,
    },
    {
      title: 'API 欄位',
      dataIndex: 'portal_api_field',
      width: 140,
      render: (v) => v ? <Text code style={{ fontSize: 11 }}>{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: '前端欄位',
      dataIndex: 'portal_frontend_field',
      width: 100,
      render: (v) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '中文顯示名稱',
      dataIndex: 'display_name',
      width: 110,
      render: (v) => v || <Text type="secondary">—</Text>,
    },
    {
      title: 'Ragic 欄位名稱',
      dataIndex: 'ragic_field_name',
      width: 140,
      render: (v) => v || <Text type="secondary">—</Text>,
    },
    {
      title: 'Ragic 型態',
      dataIndex: 'ragic_field_type',
      width: 90,
      render: (v) => v ? <Tag>{v}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: '顯示',
      dataIndex: 'is_displayed',
      width: 55,
      align: 'center',
      render: (v) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#d9d9d9' }} />,
    },
    {
      title: '計算',
      dataIndex: 'is_calculated',
      width: 55,
      align: 'center',
      render: (v) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#d9d9d9' }} />,
    },
    {
      title: '篩選',
      dataIndex: 'is_filter',
      width: 55,
      align: 'center',
      render: (v) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#d9d9d9' }} />,
    },
    {
      title: '匯出',
      dataIndex: 'is_export',
      width: 55,
      align: 'center',
      render: (v) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <CloseCircleOutlined style={{ color: '#d9d9d9' }} />,
    },
    {
      title: '對應狀態',
      dataIndex: 'mapping_status',
      width: 160,
      render: (v) => mappingStatusTag(v),
    },
    {
      title: '異常說明',
      dataIndex: 'issue_message',
      ellipsis: true,
      render: (v) => v ? <Tooltip title={v}><Text type="warning" ellipsis style={{ maxWidth: 200 }}>{v}</Text></Tooltip> : '—',
    },
  ]

  const handleSyncTab2 = async () => {
    const mod = modules.find((m) => m.portal_route === selectedRoute)
    if (!mod?.ragic_url) {
      message.warning('此模組尚無設定 Ragic URL，無法同步欄位')
      return
    }
    setSyncingTab2(true)
    try {
      const result = await syncRagicFields(mod.item_no, mod.ragic_url)
      message.success(`同步完成！Ragic 欄位 ${result.ragic_field_count} 個，新增 ${result.synced_count} 筆、更新 ${result.updated_count} 筆`)
      await loadDetail()
    } catch (e: any) {
      message.error(`同步失敗：${e?.response?.data?.detail || '請確認 Ragic API 連線正常'}`)
    } finally {
      setSyncingTab2(false)
    }
  }

  return (
    <div style={{ paddingTop: 16 }}>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          placeholder="選擇模組"
          style={{ width: 320 }}
          value={selectedRoute}
          allowClear
          onClear={() => { setSelectedRoute(undefined); setSelectedRagicUrl(''); setData([]) }}
          onChange={(v: string) => {
            setSelectedRoute(v)
            const mod = modules.find((m) => m.portal_route === v)
            setSelectedRagicUrl(mod?.ragic_url || '')
          }}
          showSearch
          loading={modules.length === 0}
          filterOption={(input, opt) =>
            (opt?.label as string || '').toLowerCase().includes(input.toLowerCase())
          }
          options={
            // 過濾掉空路由、再去重（同路由多個 itemNo 的情況）
            Array.from(
              new Map(
                modules
                  .filter((m) => !!m.portal_route)
                  .map((m) => [
                    m.portal_route,
                    {
                      value: m.portal_route,
                      label: `${m.portal_name || m.module_name}（${m.portal_route}）`,
                    },
                  ])
              ).values()
            )
          }
        />
        {selectedRagicUrl && (
          <Tooltip title={`在 Ragic 查看表單：${selectedRagicUrl}`}>
            <a href={selectedRagicUrl} target="_blank" rel="noopener noreferrer" style={{ color: '#4BA8E8' }}>
              <LinkOutlined /> 在 Ragic 查看
            </a>
          </Tooltip>
        )}
        {selectedRoute && (
          <Button
            icon={<SyncOutlined />}
            loading={syncingTab2}
            disabled={!selectedRagicUrl}
            onClick={handleSyncTab2}
          >
            同步 Ragic 欄位
          </Button>
        )}
        <Select
          placeholder="對應狀態"
          allowClear
          style={{ width: 160 }}
          onChange={setFilterStatus}
          options={[
            { value: 'normal',      label: '正常' },
            { value: 'portal_only', label: 'Portal 有 / Ragic 無' },
            { value: 'type_mismatch', label: '型態不一致' },
            { value: 'unmapped',    label: '未建立 Mapping' },
          ]}
        />
        <Space>
          <Text>只看異常</Text>
          <Switch checked={onlyIssues} onChange={setOnlyIssues} />
        </Space>
        <Search
          placeholder="搜尋欄位名稱"
          allowClear
          style={{ width: 200 }}
          onSearch={setKeyword}
        />
      </Space>

      {!selectedRoute && (
        <Alert
          type="info"
          showIcon
          message="請先選擇模組，系統將自動顯示該模組的欄位對應明細。若尚未執行比對，將顯示從 DB schema 自動生成的草稿預覽。"
          style={{ marginBottom: 16 }}
        />
      )}

      <Table
        columns={columns}
        dataSource={filtered}
        rowKey={(r, i) => r.id ? `mapping-${r.id}` : `draft-${i}`}
        loading={loading}
        size="small"
        scroll={{ x: 1500 }}
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 筆欄位` }}
        rowClassName={(r) =>
          r.mapping_status === 'type_mismatch' ? 'row-error' :
          r.mapping_status !== 'normal' && r.mapping_status !== 'unmapped' ? 'row-warning' : ''
        }
      />
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// Tab 3：異常清單
// ═══════════════════════════════════════════════════════════════════════════

function TabIssues({ onResolve }: { onResolve: () => void }) {
  const [data, setData] = useState<FieldMapping[]>([])
  const [loading, setLoading] = useState(false)
  const [filterSeverity, setFilterSeverity] = useState<string>()
  const [filterResolved, setFilterResolved] = useState<boolean | undefined>(false)
  const [keyword, setKeyword] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchIssues({
        severity: filterSeverity,
        is_resolved: filterResolved,
        keyword: keyword || undefined,
      })
      setData(res.items)
    } catch {
      message.error('載入異常清單失敗')
    } finally {
      setLoading(false)
    }
  }, [filterSeverity, filterResolved, keyword])

  useEffect(() => { load() }, [load])

  const handleResolve = async (id: number | null, isResolved: boolean) => {
    if (!id) return
    try {
      await resolveMappingIssue(id, isResolved)
      message.success(isResolved ? '已標記為處理完成' : '已取消處理標記')
      await load()
      onResolve()
    } catch {
      message.error('操作失敗')
    }
  }

  const columns: ColumnsType<FieldMapping> = [
    {
      title: '嚴重程度',
      dataIndex: 'severity',
      width: 80,
      render: (v) => severityTag(v),
      sorter: (a, b) => {
        const ord: Record<string, number> = { high: 0, medium: 1, low: 2 }
        return (ord[a.severity ?? 'low'] ?? 9) - (ord[b.severity ?? 'low'] ?? 9)
      },
      defaultSortOrder: 'ascend',
    },
    {
      title: '公司/據點',
      dataIndex: 'company',
      width: 80,
      render: (v) => <Tag>{v || '—'}</Tag>,
    },
    {
      title: '模組名稱',
      dataIndex: 'module_name',
      width: 130,
    },
    {
      title: 'DB Table',
      dataIndex: 'portal_db_table',
      width: 180,
      render: (v) => <Text code style={{ fontSize: 11 }}>{v}</Text>,
    },
    {
      title: '欄位名稱',
      dataIndex: 'portal_db_field',
      width: 150,
      render: (v) => <Text strong>{v}</Text>,
    },
    {
      title: '異常類型',
      dataIndex: 'mapping_status',
      width: 160,
      render: (v) => mappingStatusTag(v),
    },
    {
      title: '問題說明',
      dataIndex: 'issue_message',
      ellipsis: { showTitle: false },
      render: (v) => (
        <Tooltip title={v}>
          <Text ellipsis style={{ maxWidth: 300 }}>{v || '—'}</Text>
        </Tooltip>
      ),
    },
    {
      title: '建議處理',
      dataIndex: 'suggestion',
      ellipsis: { showTitle: false },
      render: (v) => (
        <Tooltip title={v}>
          <Text type="secondary" ellipsis style={{ maxWidth: 250 }}>{v || '—'}</Text>
        </Tooltip>
      ),
    },
    {
      title: '是否已處理',
      dataIndex: 'is_resolved',
      width: 100,
      align: 'center',
      render: (v, r) => (
        <Switch
          size="small"
          checked={v}
          checkedChildren="已處理"
          unCheckedChildren="待處理"
          onChange={(checked) => handleResolve(r.id, checked)}
        />
      ),
    },
  ]

  const highCount = data.filter((d) => d.severity === 'high' && !d.is_resolved).length

  return (
    <div style={{ paddingTop: 16 }}>
      {highCount > 0 && (
        <Alert
          type="error"
          showIcon
          icon={<ExclamationCircleOutlined />}
          message={`目前有 ${highCount} 個高風險異常尚未處理，可能影響 Dashboard 數字或報表金額，請優先確認。`}
          style={{ marginBottom: 16 }}
        />
      )}

      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          placeholder="嚴重程度"
          allowClear
          style={{ width: 120 }}
          onChange={setFilterSeverity}
          options={[
            { value: 'high',   label: '高（影響數字）' },
            { value: 'medium', label: '中（影響查詢）' },
            { value: 'low',    label: '低（顯示名稱）' },
          ]}
        />
        <Select
          placeholder="處理狀態"
          style={{ width: 130 }}
          defaultValue={false}
          onChange={(v: boolean | string) => setFilterResolved(v === 'all' ? undefined : v as boolean)}
          options={[
            { value: false, label: '待處理' },
            { value: true,  label: '已處理' },
            { value: 'all', label: '全部' },
          ]}
        />
        <Search
          placeholder="搜尋模組 / 欄位 / 說明"
          allowClear
          style={{ width: 240 }}
          onSearch={setKeyword}
        />
        <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey={(r, i) => r.id ? `issue-${r.id}` : `i-${i}`}
        loading={loading}
        size="small"
        scroll={{ x: 1300 }}
        pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 個異常` }}
        rowClassName={(r) =>
          r.severity === 'high' && !r.is_resolved ? 'row-error' :
          r.severity === 'medium' && !r.is_resolved ? 'row-warning' : ''
        }
      />
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// Tab 4：KPI / Dashboard 計算追溯
// ═══════════════════════════════════════════════════════════════════════════

function TabKpi() {
  const [data, setData] = useState<KpiMapping[]>([])
  const [loading, setLoading] = useState(false)
  const [filterModule, setFilterModule] = useState<string>()
  const [filterTrace, setFilterTrace] = useState<string>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchKpiMappings({
        module_name: filterModule,
        trace_status: filterTrace,
      })
      setData(res.items)
    } catch {
      message.error('載入 KPI 追溯資料失敗')
    } finally {
      setLoading(false)
    }
  }, [filterModule, filterTrace])

  useEffect(() => { load() }, [load])

  const columns: ColumnsType<KpiMapping> = [
    {
      title: '模組名稱',
      dataIndex: 'module_name',
      width: 130,
    },
    {
      title: 'KPI 名稱',
      dataIndex: 'kpi_name',
      width: 150,
      render: (v) => <Text strong>{v}</Text>,
    },
    {
      title: '顯示位置',
      dataIndex: 'page_section',
      width: 100,
      render: (v) => v || '—',
    },
    {
      title: 'API Endpoint',
      dataIndex: 'api_endpoint',
      width: 220,
      render: (v) => v ? <Text code style={{ fontSize: 11 }}>{v}</Text> : '—',
    },
    {
      title: 'DB Table',
      dataIndex: 'db_table',
      width: 200,
      render: (v) => v ? <Text code style={{ fontSize: 11 }}>{v}</Text> : '—',
    },
    {
      title: '日期依據欄位',
      dataIndex: 'date_field',
      width: 120,
      render: (v) => v || '—',
    },
    {
      title: '計算公式',
      dataIndex: 'formula',
      ellipsis: { showTitle: false },
      render: (v) => (
        <Tooltip title={v}>
          <Text code ellipsis style={{ maxWidth: 200, fontSize: 11 }}>{v || '—'}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'Ragic 原始欄位',
      dataIndex: 'ragic_source_fields',
      width: 160,
      render: (v) => {
        if (!v) return '—'
        try {
          const arr = JSON.parse(v)
          return arr.map((f: string) => <Tag key={f} style={{ marginBottom: 2 }}>{f}</Tag>)
        } catch {
          return v
        }
      },
    },
    {
      title: '追溯狀態',
      dataIndex: 'trace_status',
      width: 120,
      render: (v) => traceStatusTag(v),
    },
    {
      title: '備註',
      dataIndex: 'issue_message',
      ellipsis: true,
      render: (v) => v || '—',
    },
  ]

  // 取得模組選項
  const moduleOptions = [...new Set(data.map((d) => d.module_name).filter(Boolean))].map((m) => ({
    value: m!,
    label: m!,
  }))

  return (
    <div style={{ paddingTop: 16 }}>
      <Alert
        type="info"
        showIcon
        message="此頁面記錄 Dashboard KPI 數值的計算來源，協助確認數字可追溯至 Ragic 原始欄位。若顯示「尚未確認」，表示仍需手工核對。"
        style={{ marginBottom: 16 }}
        closable
      />

      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          placeholder="模組名稱"
          allowClear
          style={{ width: 180 }}
          onChange={setFilterModule}
          options={moduleOptions}
        />
        <Select
          placeholder="追溯狀態"
          allowClear
          style={{ width: 140 }}
          onChange={setFilterTrace}
          options={[
            { value: 'traceable',   label: '可追溯' },
            { value: 'partial',     label: '部分可追溯' },
            { value: 'untraceable', label: '無法追溯' },
            { value: 'unknown',     label: '未確認' },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={load}>重新整理</Button>
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        rowKey={(r, i) => r.id ? `kpi-${r.id}` : `kpi-draft-${i}`}
        loading={loading}
        size="small"
        scroll={{ x: 1400 }}
        pagination={{ pageSize: 15, showTotal: (t) => `共 ${t} 個 KPI` }}
        rowClassName={(r) =>
          r.trace_status === 'untraceable' ? 'row-error' :
          r.trace_status === 'partial' ? 'row-warning' : ''
        }
      />
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// Tab 5：匯出報告
// ═══════════════════════════════════════════════════════════════════════════

function TabExport({
  onExport,
  onRunAudit,
  runningAudit,
}: {
  onExport: () => void
  onRunAudit: () => void
  runningAudit: boolean
}) {
  return (
    <div style={{ paddingTop: 24, maxWidth: 700 }}>
      <Alert
        type="info"
        showIcon
        message="匯出前請先確認已執行比對，否則報告可能缺少最新比對結果。"
        style={{ marginBottom: 24 }}
      />

      <Card title="Excel 稽核報告" style={{ marginBottom: 16 }}>
        <p>匯出內容包含以下 5 個工作表：</p>
        <ol>
          <li><strong>模組總覽</strong>：各模組的欄位數量與比對狀態</li>
          <li><strong>欄位 Mapping 明細</strong>：所有已比對欄位的對應關係</li>
          <li><strong>異常欄位清單</strong>：所有異常欄位與建議處理方式</li>
          <li><strong>KPI 計算追溯</strong>：Dashboard KPI 與 Ragic 原始欄位的關係</li>
          <li><strong>建議修正清單</strong>：依嚴重程度排序的待處理事項</li>
        </ol>
        <Space>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={onExport}
            style={{ background: '#1B3A5C' }}
          >
            下載 Excel 報告
          </Button>
          <Button
            icon={<PlayCircleOutlined />}
            onClick={onRunAudit}
            loading={runningAudit}
          >
            先執行比對再匯出
          </Button>
        </Space>
      </Card>

      <Card title="包含模組">
        <p style={{ color: '#888' }}>以下模組已有本地 DB 資料，將納入稽核報告：</p>
        {[
          { name: '保全巡檢', tables: 'security_patrol_batch / _item', route: '/security/dashboard' },
          { name: '商場工務報修', tables: 'luqun_repair_case', route: '/luqun-repair/dashboard' },
          { name: '飯店工務報修', tables: 'dazhi_repair_case', route: '/dazhi-repair/dashboard' },
          { name: '整棟工務巡檢（B1F-RF）', tables: 'b1f/b2f/b4f/rf_inspection_batch/_item', route: '/full-building-inspection/dashboard' },
          { name: '商場工務巡檢', tables: 'mall_fi_inspection_batch / _item', route: '/mall-facility-inspection/dashboard' },
          { name: '核准請購單月報表', tables: 'approved_purchase_requests / _items', route: '/purchase-report/monthly' },
          { name: '客房保養明細', tables: 'room_maintenance_detail_records', route: '/hotel/room-maintenance-detail' },
          { name: '每日數值登錄表', tables: 'hotel_mr_batch / hotel_mr_reading', route: '/hotel/daily-meter-readings' },
        ].map((m, i) => (
          <Descriptions key={i} size="small" bordered column={1} style={{ marginBottom: 8 }}>
            <Descriptions.Item label="模組">{m.name}</Descriptions.Item>
            <Descriptions.Item label="DB Table"><Text code style={{ fontSize: 11 }}>{m.tables}</Text></Descriptions.Item>
            <Descriptions.Item label="路由"><Text code style={{ fontSize: 11 }}>{m.route}</Text></Descriptions.Item>
          </Descriptions>
        ))}
      </Card>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════
// Module Detail Drawer（從 Tab 1 點擊觸發）
// ═══════════════════════════════════════════════════════════════════════════

function ModuleDetailDrawer({
  route,
  ragicUrl,
  onClose,
}: {
  route: string | null
  ragicUrl?: string
  onClose: () => void
}) {
  const [data, setData] = useState<FieldMapping[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!route) return
    setLoading(true)
    fetchModuleDetail(route)
      .then((r) => setData(r.items))
      .catch(() => message.error('載入明細失敗'))
      .finally(() => setLoading(false))
  }, [route])

  // 從 mapping 資料中取第一個非空的 ragic_url（若未從 props 傳入）
  const effectiveRagicUrl = ragicUrl || data.find((d) => d.ragic_url)?.ragic_url || ''

  const ragicFieldCount = data.filter((d) => d.ragic_field_name).length

  const columns: ColumnsType<FieldMapping> = [
    { title: 'DB Table',    dataIndex: 'portal_db_table',    width: 180, render: (v) => <Text code style={{ fontSize: 11 }}>{v || '—'}</Text> },
    { title: 'DB 欄位',    dataIndex: 'portal_db_field',    width: 140, render: (v) => v ? <Text strong>{v}</Text> : <Text type="secondary">—</Text> },
    { title: 'API 欄位',   dataIndex: 'portal_api_field',   width: 130, render: (v) => v ? <Text code style={{ fontSize: 11 }}>{v}</Text> : '—' },
    { title: '中文名稱',   dataIndex: 'display_name',       width: 100, render: (v) => v || '—' },
    { title: 'Ragic 欄位', dataIndex: 'ragic_field_name',   width: 140, render: (v) => v ? <Tag color="blue">{v}</Tag> : <Text type="secondary">未同步</Text> },
    { title: 'Ragic 型態', dataIndex: 'ragic_field_type',   width: 90,  render: (v) => v ? <Tag>{v}</Tag> : '—' },
    { title: '對應狀態',   dataIndex: 'mapping_status',     width: 150, render: (v) => mappingStatusTag(v) },
    {
      title: '問題說明',
      dataIndex: 'issue_message',
      ellipsis: true,
      render: (v) => v ? <Text type="warning">{v}</Text> : '—',
    },
  ]

  return (
    <Drawer
      title={
        <Space>
          <DatabaseOutlined style={{ color: '#4BA8E8' }} />
          <span>模組欄位明細</span>
          {route && <Text code style={{ fontSize: 12 }}>{route}</Text>}
          {effectiveRagicUrl && (
            <a
              href={effectiveRagicUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#4BA8E8', fontSize: 13 }}
            >
              <LinkOutlined /> 在 Ragic 查看
            </a>
          )}
        </Space>
      }
      width={900}
      open={!!route}
      onClose={onClose}
      bodyStyle={{ padding: 16 }}
      extra={
        ragicFieldCount > 0 && (
          <Tag color="blue">已同步 {ragicFieldCount} 個 Ragic 欄位</Tag>
        )
      }
    >
      <Spin spinning={loading}>
        {ragicFieldCount === 0 && (
          <Alert
            type="info"
            showIcon
            message="尚未同步 Ragic 欄位。請回到「模組總覽」Tab，點擊「同步欄位」按鈕抓取 Ragic 表單欄位定義。"
            style={{ marginBottom: 12 }}
            closable
          />
        )}
        <Table
          columns={columns}
          dataSource={data}
          rowKey={(r, i) => r.id ? `d-${r.id}` : `d-draft-${i}`}
          size="small"
          scroll={{ x: 1000 }}
          pagination={{ pageSize: 20 }}
          rowClassName={(r) =>
            r.mapping_status === 'type_mismatch' ? 'row-error' :
            r.mapping_status !== 'normal' && r.mapping_status !== 'unmapped' ? 'row-warning' : ''
          }
        />
      </Spin>
    </Drawer>
  )
}
