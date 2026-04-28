/**
 * 商場週期保養表 — 批次明細頁（唯讀，資料來源全部為 Ragic）
 * Route: /mall/periodic-maintenance/:batchId
 */
import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Breadcrumb, Button, Card, Col, Drawer, Row, Select, Space,
  Table, Tag, Typography, message, Statistic, Divider,
  Checkbox, Tooltip, Alert,
} from 'antd'
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  SearchOutlined,
  WarningOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  MinusCircleOutlined,
  CalendarOutlined,
  FilterOutlined,
  CheckSquareOutlined,
  BorderOutlined,
} from '@ant-design/icons'
import { Input } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import { fetchMallPMBatchDetail, fetchMallPMTaskHistory } from '@/api/mallPeriodicMaintenance'
import type {
  PMBatchDetail, PMItem, PMItemStatus,
  PMTaskHistory, PMItemHistorySummary,
} from '@/types/periodicMaintenance'

const { Title, Text } = Typography
const { Option } = Select

// ── 狀態設定 ──────────────────────────────────────────────────────────────────
const STATUS_CFG: Record<string, { label: string; color: string; rowBg?: string }> = {
  completed:         { label: '已完成', color: '#52C41A' },
  in_progress:       { label: '進行中', color: '#4BA8E8' },
  scheduled:         { label: '已排定', color: '#FAAD14' },
  unscheduled:       { label: '未排定', color: '#FF4D4F', rowBg: '#fff5f5' },
  overdue:           { label: '逾期',   color: '#C0392B', rowBg: '#fff5f5' },
  non_current_month: { label: '非本月', color: '#999999', rowBg: '#f5f5f5' },
  no_batch:          { label: '無批次', color: '#cccccc' },
}

const STATUS_TABS: Array<{ key: string; label: string }> = [
  { key: 'all',               label: '全部' },
  { key: 'unscheduled',       label: '未排定' },
  { key: 'scheduled',         label: '已排定' },
  { key: 'in_progress',       label: '進行中' },
  { key: 'completed',         label: '已完成' },
  { key: 'overdue',           label: '逾期' },
  { key: 'abnormal',          label: '異常' },
  { key: 'non_current_month', label: '非本月' },
]

const STATUS_SELECT_OPTIONS = [
  { value: 'unscheduled',       label: '未排定' },
  { value: 'scheduled',         label: '已排定' },
  { value: 'in_progress',       label: '進行中' },
  { value: 'completed',         label: '已完成' },
  { value: 'overdue',           label: '逾期' },
  { value: 'non_current_month', label: '非本月' },
  { value: 'abnormal',          label: '異常 (旗標)' },
]

function fmtMinutes(mins: number): string {
  if (!mins) return '—'
  if (mins < 60) return `${mins} 分`
  return `${Math.floor(mins / 60)} 時 ${mins % 60} 分`
}

// ══════════════════════════════════════════════════════════════════════════════
// ItemHistoryDrawer
// ══════════════════════════════════════════════════════════════════════════════
function ItemHistoryDrawer({
  open, onClose, historyData, loading,
}: {
  open: boolean
  onClose: () => void
  historyData: PMTaskHistory | null
  loading: boolean
}) {
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null)

  const {
    task_name, category, frequency, exec_months_raw, monthly_summary, stats,
  } = historyData ?? {
    task_name: '', category: '', frequency: '', exec_months_raw: '',
    monthly_summary: [],
    stats: { total_months: 12, completed_months: 0, abnormal_count: 0 },
  }

  const selectedMonthData: PMItemHistorySummary | undefined = selectedMonth
    ? monthly_summary.find((ms) => ms.period_month === selectedMonth)
    : undefined

  function MonthCell({ ms }: { ms: PMItemHistorySummary }) {
    const isSelected = selectedMonth === ms.period_month
    let bg = '#fafafa', borderColor = '#e8e8e8', textColor = '#aaa'
    let icon = <MinusCircleOutlined style={{ color: '#bbb', fontSize: 16 }} />

    if (!ms.has_record) {
      // 無此批次
    } else if (ms.status === 'completed') {
      bg = '#f6ffed'; borderColor = '#b7eb8f'; textColor = '#389e0d'
      icon = <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
    } else if (ms.status === 'overdue') {
      bg = '#fff1f0'; borderColor = '#ffa39e'; textColor = '#cf1322'
      icon = <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
    } else if (ms.status === 'scheduled' || ms.status === 'in_progress') {
      bg = '#e6f4ff'; borderColor = '#91caff'; textColor = '#0958d9'
      icon = <CalendarOutlined style={{ color: '#1677ff', fontSize: 16 }} />
    } else if (ms.status === 'unscheduled' && ms.is_current) {
      bg = '#fff7e6'; borderColor = '#ffe58f'; textColor = '#d46b08'
      icon = <MinusCircleOutlined style={{ color: '#faad14', fontSize: 16 }} />
    }

    return (
      <Tooltip title={!ms.has_record ? `${ms.period_month}：無保養批次`
        : ms.status === 'completed' ? `${ms.period_month}：已完成 — 點擊查看`
        : `${ms.period_month}：${STATUS_CFG[ms.status]?.label ?? ms.status}`
      }>
        <div
          onClick={() => ms.has_record && setSelectedMonth(
            (p) => p === ms.period_month ? null : ms.period_month
          )}
          style={{
            background: bg,
            border: isSelected ? '2px solid #1B3A5C' : `1px solid ${borderColor}`,
            borderRadius: 6, padding: '6px 4px', textAlign: 'center',
            minWidth: 64, cursor: ms.has_record ? 'pointer' : 'default',
            transition: 'all .15s',
            boxShadow: isSelected ? '0 2px 10px rgba(27,58,92,0.25)' : undefined,
            transform: isSelected ? 'scale(1.06)' : undefined,
          }}
        >
          <div style={{ fontSize: 11, color: isSelected ? '#1B3A5C' : textColor, fontWeight: 600, marginBottom: 2 }}>
            {ms.period_month.slice(5)}月
          </div>
          {icon}
          {ms.has_record && ms.executor_name && (
            <div style={{ fontSize: 10, color: textColor, marginTop: 2 }}>
              {ms.executor_name.split('/')[0]}
            </div>
          )}
        </div>
      </Tooltip>
    )
  }

  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined style={{ color: '#1B3A5C' }} />
          <Tag color="blue" style={{ fontSize: 13 }}>{task_name || '—'}</Tag>
          保養歷史
        </Space>
      }
      width={620}
      open={open}
      onClose={() => { onClose(); setSelectedMonth(null) }}
      loading={loading}
      styles={{ body: { padding: '16px 20px' } }}
    >
      <Card size="small" style={{ marginBottom: 16, background: '#fafafa' }} bordered={false}>
        <Row gutter={[8, 4]}>
          <Col span={8}><Text type="secondary">類別：</Text><Text>{category || '—'}</Text></Col>
          <Col span={8}><Text type="secondary">頻率：</Text><Text>{frequency || '—'}</Text></Col>
          <Col span={8}><Text type="secondary">執行月份：</Text><Text>{exec_months_raw || '—'}</Text></Col>
        </Row>
      </Card>

      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="近 12 月完成次數"
              value={`${stats.completed_months} / ${stats.total_months}`}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52C41A', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="完成率"
              value={stats.total_months > 0 ? Math.round(stats.completed_months / stats.total_months * 100) : 0}
              suffix="%"
              valueStyle={{
                color: stats.completed_months / stats.total_months >= 0.8 ? '#52C41A'
                  : stats.completed_months / stats.total_months >= 0.5 ? '#FAAD14' : '#FF4D4F',
                fontSize: 18,
              }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="異常次數"
              value={stats.abnormal_count}
              prefix={<WarningOutlined />}
              valueStyle={{ color: stats.abnormal_count > 0 ? '#E67E22' : '#52C41A', fontSize: 18 }}
            />
          </Card>
        </Col>
      </Row>

      <Divider orientation="left" orientationMargin={0}>
        <Text type="secondary" style={{ fontSize: 12 }}>月曆（點擊月份查看明細）</Text>
      </Divider>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
        {monthly_summary.map((ms) => (
          <MonthCell key={ms.period_month} ms={ms} />
        ))}
      </div>

      {selectedMonthData && (
        <>
          <Divider orientation="left" orientationMargin={0}>
            <Text type="secondary" style={{ fontSize: 12 }}>{selectedMonthData.period_month} 執行記錄</Text>
          </Divider>
          {selectedMonthData.abnormal_flag && (
            <Alert
              type="warning" showIcon icon={<WarningOutlined />}
              message="本月有異常旗標"
              description={selectedMonthData.abnormal_note || '（無說明）'}
              style={{ marginBottom: 12 }}
            />
          )}
          <Card size="small" style={{ background: '#f6ffed' }}>
            <Row gutter={[12, 8]}>
              <Col span={12}><Text type="secondary">排定日期：</Text><Text>{selectedMonthData.scheduled_date || '—'}</Text></Col>
              <Col span={12}><Text type="secondary">執行人員：</Text><Text>{selectedMonthData.executor_name || '—'}</Text></Col>
              <Col span={12}>
                <Text type="secondary">開始時間：</Text>
                <Text>{selectedMonthData.start_time ? dayjs(selectedMonthData.start_time).format('MM/DD HH:mm') : '—'}</Text>
              </Col>
              <Col span={12}>
                <Text type="secondary">結束時間：</Text>
                <Text>{selectedMonthData.end_time ? dayjs(selectedMonthData.end_time).format('MM/DD HH:mm') : '—'}</Text>
              </Col>
              {selectedMonthData.result_note && (
                <Col span={24}><Text type="secondary">備註：</Text><Text>{selectedMonthData.result_note}</Text></Col>
              )}
              <Col span={24}>
                <Text type="secondary">狀態：</Text>
                <Tag color={STATUS_CFG[selectedMonthData.status]?.color}>
                  {STATUS_CFG[selectedMonthData.status]?.label ?? selectedMonthData.status}
                </Tag>
              </Col>
            </Row>
          </Card>
        </>
      )}
    </Drawer>
  )
}

// ══════════════════════════════════════════════════════════════════════════════
// Main Component
// ══════════════════════════════════════════════════════════════════════════════
export default function MallPeriodicMaintenanceDetailPage() {
  const { batchId } = useParams<{ batchId: string }>()
  const navigate    = useNavigate()

  const [detail, setDetail]   = useState<PMBatchDetail | null>(null)
  const [loading, setLoading] = useState(false)

  const [activeTab, setActiveTab]               = useState('all')
  const [categoryFilter, setCategoryFilter]     = useState<string>('')
  const [searchText, setSearchText]             = useState('')
  const [statusFilters, setStatusFilters]       = useState<string[]>([])
  const [onlyScheduled, setOnlyScheduled]       = useState(false)

  const [historyOpen, setHistoryOpen]           = useState(false)
  const [historyLoading, setHistoryLoading]     = useState(false)
  const [historyData, setHistoryData]           = useState<PMTaskHistory | null>(null)

  const loadDetail = useCallback(async () => {
    if (!batchId) return
    setLoading(true)
    try {
      const data = await fetchMallPMBatchDetail(batchId)
      setDetail(data)
    } catch {
      message.error('載入批次資料失敗')
    } finally {
      setLoading(false)
    }
  }, [batchId])

  useEffect(() => { loadDetail() }, [loadDetail])

  async function openHistory(taskName: string) {
    setHistoryOpen(true)
    setHistoryLoading(true)
    setHistoryData(null)
    try {
      const data = await fetchMallPMTaskHistory(taskName)
      setHistoryData(data)
    } catch {
      message.error('載入保養歷史失敗')
    } finally {
      setHistoryLoading(false)
    }
  }

  const filteredItems = (detail?.items ?? []).filter((item) => {
    if (statusFilters.length > 0) {
      const matches = statusFilters.some((sf) =>
        sf === 'abnormal' ? item.abnormal_flag : item.status === sf
      )
      if (!matches) return false
    } else {
      if (activeTab === 'abnormal') {
        if (!item.abnormal_flag) return false
      } else if (activeTab !== 'all') {
        if (item.status !== activeTab) return false
      }
    }
    if (onlyScheduled && !item.scheduled_date) return false
    if (categoryFilter && item.category !== categoryFilter) return false
    if (searchText) {
      const q = searchText.toLowerCase()
      if (
        !item.task_name.toLowerCase().includes(q) &&
        !item.location.toLowerCase().includes(q) &&
        !(item.executor_name || '').toLowerCase().includes(q)
      ) return false
    }
    return true
  })

  const tabCounts: Record<string, number> = { all: detail?.items.length ?? 0 }
  for (const it of detail?.items ?? []) {
    tabCounts[it.status] = (tabCounts[it.status] ?? 0) + 1
    if (it.abnormal_flag) tabCounts['abnormal'] = (tabCounts['abnormal'] ?? 0) + 1
  }

  const categoryOptions = Array.from(
    new Set((detail?.items ?? []).map((i) => i.category).filter(Boolean))
  )

  const isAdvancedFilter = statusFilters.length > 0 || onlyScheduled

  const columns: ColumnsType<PMItem> = [
    {
      title: '項次',
      dataIndex: 'seq_no',
      width: 60,
      align: 'center',
      render: (v: number) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '類別',
      dataIndex: 'category',
      width: 90,
      render: (v: string) => <Tag>{v || '—'}</Tag>,
    },
    {
      title: '保養項目',
      dataIndex: 'task_name',
      render: (v: string, rec) => (
        <Space direction="vertical" size={0}>
          <Button
            type="link"
            size="small"
            style={{ padding: 0, height: 'auto', fontWeight: 600, textAlign: 'left' }}
            onClick={() => openHistory(v)}
          >
            {v}
            <HistoryOutlined style={{ marginLeft: 4, fontSize: 11, color: '#4BA8E8' }} />
          </Button>
          {rec.location && (
            <Text type="secondary" style={{ fontSize: 12 }}>{rec.location}</Text>
          )}
        </Space>
      ),
    },
    {
      title: '頻率',
      dataIndex: 'frequency',
      width: 80,
      align: 'center',
      render: (v: string) => v || '—',
    },
    {
      title: '預估工時',
      dataIndex: 'estimated_minutes',
      width: 90,
      align: 'center',
      render: (v: number) => fmtMinutes(v),
    },
    {
      title: '排定日期',
      dataIndex: 'scheduled_date',
      width: 90,
      align: 'center',
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '執行人員',
      dataIndex: 'executor_name',
      width: 90,
      render: (v: string) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '保養時間',
      key: 'times',
      width: 140,
      render: (_: unknown, rec: PMItem) => {
        const st = rec.start_time ? dayjs(rec.start_time).format('MM/DD HH:mm') : null
        const et = rec.end_time   ? dayjs(rec.end_time).format('MM/DD HH:mm')   : null
        if (!st && !et) return <Text type="secondary">—</Text>
        return (
          <Space direction="vertical" size={0}>
            {st && <Text style={{ fontSize: 12 }}>啟：{st}</Text>}
            {et && <Text style={{ fontSize: 12 }}>迄：{et}</Text>}
          </Space>
        )
      },
    },
    {
      title: '完成',
      dataIndex: 'is_completed',
      width: 52,
      align: 'center',
      render: (v: boolean) => v
        ? <CheckSquareOutlined style={{ fontSize: 18, color: '#52C41A' }} />
        : <BorderOutlined style={{ fontSize: 18, color: '#d9d9d9' }} />,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      width: 80,
      align: 'center',
      render: (v: PMItemStatus, rec) => {
        const cfg = STATUS_CFG[v] ?? { label: v, color: '#666' }
        return (
          <Space size={4} direction="vertical" style={{ alignItems: 'center' }}>
            <Tag color={cfg.color} style={{ margin: 0 }}>{cfg.label}</Tag>
            {rec.abnormal_flag && (
              <Tag color="#E67E22" style={{ margin: 0, fontSize: 10 }}>異常</Tag>
            )}
          </Space>
        )
      },
    },
  ]

  const kpi = detail?.kpi
  const kpiCards = kpi ? [
    { label: '本月有效',  value: kpi.current_month_total, color: '#1B3A5C' },
    { label: '已完成',    value: kpi.completed,           color: '#52C41A' },
    { label: '已排定',    value: kpi.scheduled,           color: '#FAAD14' },
    { label: '未排定',    value: kpi.unscheduled,         color: '#FF4D4F' },
    { label: '逾期',      value: kpi.overdue,             color: '#C0392B' },
    { label: '異常旗標',  value: kpi.abnormal,            color: '#E67E22' },
  ] : []

  return (
    <div style={{ padding: '0 0 32px' }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: '商場管理' },
          { title: <a onClick={() => navigate('/mall/dashboard?tab=pm')}>商場週期保養</a> },
          { title: detail?.batch.journal_no ?? batchId },
        ]}
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/mall/dashboard?tab=pm')}>
            返回列表
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            {detail?.batch.journal_no ?? '批次明細'}
            {detail?.batch.period_month && (
              <Text type="secondary" style={{ fontSize: 14, marginLeft: 8 }}>
                {detail.batch.period_month}
              </Text>
            )}
          </Title>
        </Space>
        <Button icon={<ReloadOutlined />} onClick={loadDetail} loading={loading}>
          重新整理
        </Button>
      </div>

      {/* KPI Cards */}
      <Row gutter={12} style={{ marginBottom: 20 }}>
        {kpiCards.map((c) => (
          <Col key={c.label} xs={12} sm={8} md={4}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <Statistic
                title={c.label}
                value={c.value}
                valueStyle={{ color: c.color, fontSize: 22 }}
              />
            </Card>
          </Col>
        ))}
        {kpi && (
          <Col xs={24} style={{ marginTop: 8 }}>
            <Card size="small">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <Text>完成率</Text>
                <div style={{
                  flex: 1, height: 12, background: '#f0f0f0', borderRadius: 6, overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${kpi.completion_rate}%`, height: '100%',
                    background: kpi.completion_rate >= 80 ? '#52C41A'
                      : kpi.completion_rate >= 50 ? '#FAAD14' : '#FF4D4F',
                    borderRadius: 6, transition: 'width 0.5s',
                  }} />
                </div>
                <Text strong style={{ minWidth: 48, textAlign: 'right' }}>
                  {kpi.completion_rate}%
                </Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  預估總工時 {fmtMinutes(kpi.planned_minutes)}
                </Text>
              </div>
            </Card>
          </Col>
        )}
      </Row>

      {/* 篩選區 */}
      <Card
        size="small"
        style={{ marginBottom: 16, borderColor: isAdvancedFilter ? '#4BA8E8' : undefined }}
      >
        <Space wrap>
          <Input
            placeholder="搜尋項目名稱 / 地點 / 執行人員"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ width: 260 }}
          />
          <Select
            placeholder="類別"
            value={categoryFilter || undefined}
            onChange={(v) => setCategoryFilter(v ?? '')}
            allowClear
            style={{ width: 140 }}
          >
            {categoryOptions.map((cat) => (
              <Option key={cat} value={cat}>{cat}</Option>
            ))}
          </Select>
          <Text type="secondary" style={{ fontSize: 12 }}>共 {filteredItems.length} 筆</Text>
        </Space>

        <div style={{
          marginTop: 10, paddingTop: 10, borderTop: '1px dashed #e0e0e0',
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
          <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
            <FilterOutlined style={{ marginRight: 4 }} />
            狀態篩選（可複選）：
          </Text>
          <Select
            mode="multiple"
            placeholder="選擇一或多個狀態（空白 = 使用上方 Tab）"
            value={statusFilters}
            onChange={setStatusFilters}
            allowClear
            style={{ minWidth: 300, flex: 1 }}
            maxTagCount="responsive"
            options={STATUS_SELECT_OPTIONS.map((o) => ({
              value: o.value,
              label: (
                <span>
                  <Tag color={STATUS_CFG[o.value]?.color} style={{ margin: '0 4px 0 0', fontSize: 11 }}>
                    {o.label}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    ({tabCounts[o.value] ?? 0})
                  </Text>
                </span>
              ),
            }))}
          />
          <Tooltip title="篩選出有填寫排定日期的項目（無論任何狀態）">
            <Checkbox checked={onlyScheduled} onChange={(e) => setOnlyScheduled(e.target.checked)}>
              <Text style={{ fontSize: 12 }}>有排定日期</Text>
            </Checkbox>
          </Tooltip>
          {isAdvancedFilter && (
            <Button size="small" onClick={() => { setStatusFilters([]); setOnlyScheduled(false) }}>
              清除進階篩選
            </Button>
          )}
        </div>
      </Card>

      {/* 狀態 Tabs + 表格 */}
      <Card bodyStyle={{ padding: 0 }}>
        <div style={{ borderBottom: '1px solid #f0f0f0', padding: '0 16px', display: 'flex', gap: 0 }}>
          {[
            ...STATUS_TABS,
            ...(statusFilters.length > 0 ? [{ key: '__advanced__', label: '複選篩選中' }] : []),
          ].map((t) => {
            const isActive = statusFilters.length > 0
              ? t.key === '__advanced__'
              : activeTab === t.key
            const count = tabCounts[t.key]
            return (
              <div
                key={t.key}
                onClick={() => {
                  if (t.key !== '__advanced__') {
                    setStatusFilters([])
                    setActiveTab(t.key)
                  }
                }}
                style={{
                  padding: '12px 16px',
                  fontSize: 14,
                  cursor: 'pointer',
                  borderBottom: isActive ? '2px solid #1B3A5C' : '2px solid transparent',
                  color: isActive ? '#1B3A5C' : (t.key === '__advanced__' ? '#4BA8E8' : '#595959'),
                  fontWeight: isActive ? 600 : 400,
                  transition: 'all .2s',
                  whiteSpace: 'nowrap',
                }}
              >
                {t.label}
                {count !== undefined && (
                  <Tag
                    style={{ marginLeft: 4, fontSize: 11 }}
                    color={
                      t.key === '__advanced__' ? 'blue'
                        : count > 0 && !['all', 'completed', 'non_current_month'].includes(t.key)
                        ? 'default' : undefined
                    }
                  >
                    {count ?? 0}
                  </Tag>
                )}
              </div>
            )
          })}
        </div>

        <Table<PMItem>
          loading={loading}
          dataSource={filteredItems}
          rowKey="ragic_id"
          columns={columns}
          size="small"
          pagination={{ pageSize: 20, showTotal: (n) => `共 ${n} 筆` }}
          onRow={(rec) => ({
            style: { background: STATUS_CFG[rec.status]?.rowBg },
          })}
        />
      </Card>

      <ItemHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        historyData={historyData}
        loading={historyLoading}
      />
    </div>
  )
}
