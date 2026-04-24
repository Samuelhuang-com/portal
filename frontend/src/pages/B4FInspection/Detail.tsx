/**
 * 整棟工務每日巡檢 - B4F  批次明細頁（唯讀）【寬表格 Pivot 架構 v3】
 * Route: /mall/b4f-inspection/:batchId
 */
import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Breadcrumb, Button, Card, Col, Drawer, Row, Space,
  Table, Tag, Typography, message, Statistic, Divider,
  Tooltip,
} from 'antd'
import {
  ArrowLeftOutlined, ReloadOutlined, SearchOutlined,
  WarningOutlined, HistoryOutlined, CheckCircleOutlined,
  CloseCircleOutlined, MinusCircleOutlined, FilterOutlined,
  CalendarOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import { Input, Select } from 'antd'
import type { ColumnsType } from 'antd/es/table'

import { fetchB4FBatchDetail, fetchB4FItemHistory } from '@/api/b4fInspection'
import type {
  InspectionBatchDetail, InspectionItem, InspectionResultStatus,
  InspectionItemHistory, InspectionDailySummary,
} from '@/types/b4fInspection'

const { Title, Text } = Typography

// ── 狀態設定 ──────────────────────────────────────────────────────────────────
const STATUS_CFG: Record<string, { label: string; color: string; rowBg?: string; tagColor: string }> = {
  normal:    { label: '正常',   color: '#52C41A', tagColor: 'success' },
  abnormal:  { label: '異常',   color: '#FF4D4F', rowBg: '#fff1f0', tagColor: 'error' },
  pending:   { label: '待處理', color: '#FAAD14', rowBg: '#fff7e6', tagColor: 'warning' },
  unchecked: { label: '未巡檢', color: '#999999', rowBg: '#fafafa', tagColor: 'default' },
  no_record: { label: '無記錄', color: '#cccccc', tagColor: 'default' },
}

// ── 篩選 Tab ──────────────────────────────────────────────────────────────────
const STATUS_TABS = [
  { key: 'all',       label: '全部' },
  { key: 'normal',    label: '正常' },
  { key: 'abnormal',  label: '異常' },
  { key: 'pending',   label: '待處理' },
  { key: 'unchecked', label: '未巡檢' },
]

// ══════════════════════════════════════════════════════════════════════════════
// ItemHistoryDrawer — 近 30 日巡檢歷史
// ══════════════════════════════════════════════════════════════════════════════
function ItemHistoryDrawer({
  open, onClose, historyData, loading,
}: {
  open: boolean
  onClose: () => void
  historyData: InspectionItemHistory | null
  loading: boolean
}) {
  const [selectedDay, setSelectedDay] = useState<string | null>(null)

  const { item_name, daily_summary, stats } = historyData ?? {
    item_name: '',
    daily_summary: [],
    stats: { total_days: 30, normal_days: 0, abnormal_days: 0 },
  }

  const selectedDayData: InspectionDailySummary | undefined = selectedDay
    ? daily_summary.find(ds => ds.inspection_date === selectedDay)
    : undefined

  function DayCell({ ds }: { ds: InspectionDailySummary }) {
    const isSelected = selectedDay === ds.inspection_date
    let bg = '#fafafa', borderColor = '#e8e8e8', textColor = '#bbb'
    let icon = <MinusCircleOutlined style={{ color: '#bbb', fontSize: 15 }} />

    if (!ds.has_record) {
      // 無記錄，維持灰色
    } else if (ds.result_status === 'normal') {
      bg = '#f6ffed'; borderColor = '#b7eb8f'; textColor = '#389e0d'
      icon = <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 15 }} />
    } else if (ds.result_status === 'abnormal') {
      bg = '#fff1f0'; borderColor = '#ffa39e'; textColor = '#cf1322'
      icon = <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 15 }} />
    } else if (ds.result_status === 'pending') {
      bg = '#fff7e6'; borderColor = '#ffe58f'; textColor = '#d46b08'
      icon = <WarningOutlined style={{ color: '#faad14', fontSize: 15 }} />
    } else if (ds.result_status === 'unchecked' && ds.is_today) {
      bg = '#f0f5ff'; borderColor = '#adc6ff'; textColor = '#2f54eb'
      icon = <CalendarOutlined style={{ color: '#4BA8E8', fontSize: 15 }} />
    }

    const [, mm, dd] = ds.inspection_date.split('/')

    return (
      <Tooltip title={!ds.has_record
        ? `${ds.inspection_date}：無記錄`
        : `${ds.inspection_date}：${STATUS_CFG[ds.result_status]?.label ?? ds.result_status} — 點擊查看`
      }>
        <div
          onClick={() => ds.has_record && setSelectedDay(p => p === ds.inspection_date ? null : ds.inspection_date)}
          style={{
            background: bg,
            border: isSelected ? '2px solid #1B3A5C' : `1px solid ${borderColor}`,
            borderRadius: 6, padding: '5px 3px', textAlign: 'center',
            minWidth: 52, cursor: ds.has_record ? 'pointer' : 'default',
            transition: 'all .15s',
            boxShadow: isSelected ? '0 2px 10px rgba(27,58,92,0.2)' : undefined,
            transform: isSelected ? 'scale(1.06)' : undefined,
          }}
        >
          <div style={{ fontSize: 10, color: isSelected ? '#1B3A5C' : textColor, fontWeight: 600 }}>
            {mm}/{dd}
          </div>
          {icon}
        </div>
      </Tooltip>
    )
  }

  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined style={{ color: '#1B3A5C' }} />
          <Tag color="blue" style={{ fontSize: 13 }}>{item_name || '—'}</Tag>
          巡檢歷史
        </Space>
      }
      width={640}
      open={open}
      onClose={() => { onClose(); setSelectedDay(null) }}
      loading={loading}
      styles={{ body: { padding: '16px 20px' } }}
    >
      {/* KPI */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="近30日正常天數"
              value={`${stats.normal_days} / ${stats.total_days}`}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52C41A', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="正常率"
              value={stats.total_days > 0
                ? Math.round(stats.normal_days / stats.total_days * 100) : 0}
              suffix="%"
              valueStyle={{
                color: stats.normal_days / stats.total_days >= 0.9 ? '#52C41A'
                  : stats.normal_days / stats.total_days >= 0.7 ? '#FAAD14' : '#FF4D4F',
                fontSize: 18,
              }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="異常天數"
              value={stats.abnormal_days}
              prefix={<WarningOutlined />}
              valueStyle={{ color: stats.abnormal_days > 0 ? '#FF4D4F' : '#52C41A', fontSize: 18 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 30 日日曆 */}
      <Divider orientation="left" orientationMargin={0}>
        <Text type="secondary" style={{ fontSize: 12 }}>近 30 日日曆（點擊查看明細）</Text>
      </Divider>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 20 }}>
        {daily_summary.map(ds => (
          <DayCell key={ds.inspection_date} ds={ds} />
        ))}
      </div>

      {/* 選取日明細 */}
      {selectedDayData && (
        <>
          <Divider orientation="left" orientationMargin={0}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {selectedDayData.inspection_date} 執行記錄
            </Text>
          </Divider>
          <Card size="small" style={{
            background: selectedDayData.result_status === 'normal' ? '#f6ffed' : '#fff7e6',
          }}>
            <Row gutter={[12, 8]}>
              <Col span={12}>
                <Text type="secondary">巡檢人員：</Text>
                <Text>{selectedDayData.inspector_name || '—'}</Text>
              </Col>
              <Col span={12}>
                <Text type="secondary">開始時間：</Text>
                <Text>{selectedDayData.start_time || '—'}</Text>
              </Col>
              <Col span={24}>
                <Text type="secondary">巡檢結果：</Text>
                <Tag color={STATUS_CFG[selectedDayData.result_status]?.tagColor}>
                  {selectedDayData.result_raw || STATUS_CFG[selectedDayData.result_status]?.label || '—'}
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
export default function B4FInspectionDetailPage() {
  const { batchId } = useParams<{ batchId: string }>()
  const navigate    = useNavigate()

  const [detail, setDetail]   = useState<InspectionBatchDetail | null>(null)
  const [loading, setLoading] = useState(false)

  const [activeTab, setActiveTab]         = useState('all')
  const [searchText, setSearchText]       = useState('')
  const [statusFilters, setStatusFilters] = useState<string[]>([])

  const [historyOpen, setHistoryOpen]       = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyData, setHistoryData]       = useState<InspectionItemHistory | null>(null)

  const loadDetail = useCallback(async () => {
    if (!batchId) return
    setLoading(true)
    try {
      const data = await fetchB4FBatchDetail(batchId)
      setDetail(data)
    } catch {
      message.error('載入巡檢資料失敗')
    } finally {
      setLoading(false)
    }
  }, [batchId])

  useEffect(() => { loadDetail() }, [loadDetail])

  async function openHistory(itemName: string) {
    setHistoryOpen(true)
    setHistoryLoading(true)
    setHistoryData(null)
    try {
      const data = await fetchB4FItemHistory(itemName, 30)
      setHistoryData(data)
    } catch {
      message.error('載入歷史記錄失敗')
    } finally {
      setHistoryLoading(false)
    }
  }

  // ── 篩選邏輯 ──────────────────────────────────────────────────────────────
  const filteredItems = (detail?.items ?? []).filter(item => {
    if (statusFilters.length > 0) {
      if (!statusFilters.includes(item.result_status)) return false
    } else if (activeTab !== 'all' && item.result_status !== activeTab) {
      return false
    }
    if (searchText) {
      const q = searchText.toLowerCase()
      if (!item.item_name.toLowerCase().includes(q)) return false
    }
    return true
  })

  // Tab 計數
  const tabCounts: Record<string, number> = { all: detail?.items.length ?? 0 }
  for (const it of detail?.items ?? []) {
    tabCounts[it.result_status] = (tabCounts[it.result_status] ?? 0) + 1
  }

  const isAdvanced = statusFilters.length > 0

  // ── 表格欄位 ──────────────────────────────────────────────────────────────
  const columns: ColumnsType<InspectionItem> = [
    {
      title: '項次',
      dataIndex: 'seq_no',
      width: 60,
      align: 'center',
      render: (v) => <Text type="secondary">{v}</Text>,
    },
    {
      title: '巡檢項目',
      dataIndex: 'item_name',
      render: (v: string) => (
        <Button
          type="link" size="small"
          style={{ padding: 0, height: 'auto', fontWeight: 600, textAlign: 'left' }}
          onClick={() => openHistory(v)}
        >
          {v}
          <HistoryOutlined style={{ marginLeft: 4, fontSize: 11, color: '#4BA8E8' }} />
        </Button>
      ),
    },
    {
      title: '巡檢結果',
      dataIndex: 'result_status',
      width: 100,
      align: 'center',
      render: (v: InspectionResultStatus, rec) => {
        const cfg = STATUS_CFG[v] ?? { label: v, tagColor: 'default' }
        return (
          <Tooltip title={rec.result_raw || cfg.label}>
            <Tag color={cfg.tagColor}>{cfg.label}</Tag>
          </Tooltip>
        )
      },
    },
    {
      title: '原始值',
      dataIndex: 'result_raw',
      width: 100,
      render: (v) => v
        ? <Text style={{ fontSize: 12 }}>{v}</Text>
        : <Text type="secondary">—</Text>,
    },
  ]

  const kpi = detail?.kpi
  const kpiCards = kpi ? [
    { label: '總項目',  value: kpi.total,     color: '#1B3A5C' },
    { label: '正常',    value: kpi.normal,    color: '#52C41A' },
    { label: '異常',    value: kpi.abnormal,  color: '#FF4D4F' },
    { label: '待處理',  value: kpi.pending,   color: '#FAAD14' },
    { label: '未巡檢',  value: kpi.unchecked, color: '#999999' },
    { label: '正常率',  value: `${kpi.normal_rate}%`,
      color: kpi.normal_rate >= 90 ? '#52C41A' : kpi.normal_rate >= 70 ? '#FAAD14' : '#FF4D4F' },
  ] : []

  const batch = detail?.batch

  return (
    <div style={{ padding: '0 0 32px' }}>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: '商場管理' },
          { title: <a onClick={() => navigate('/mall/b4f-inspection')}>整棟工務每日巡檢 - B4F</a> },
          { title: batch?.inspection_date ?? batchId },
        ]}
      />

      {/* 頁首 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/mall/b4f-inspection')}>
            返回列表
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            {batch?.inspection_date ?? '巡檢明細'}
            {batch?.inspector_name && (
              <Text type="secondary" style={{ fontSize: 14, marginLeft: 8, fontWeight: 400 }}>
                巡檢人員：{batch.inspector_name}
              </Text>
            )}
          </Title>
        </Space>
        <Button icon={<ReloadOutlined />} onClick={loadDetail} loading={loading}>
          重新整理
        </Button>
      </div>

      {/* 場次資訊 */}
      {batch && (
        <Card size="small" style={{ marginBottom: 16, background: '#fafcff' }}>
          <Row gutter={[16, 4]}>
            <Col xs={12} sm={6}>
              <Space size={4}>
                <ClockCircleOutlined style={{ color: '#4BA8E8' }} />
                <Text type="secondary">開始：</Text>
                <Text>{batch.start_time || '—'}</Text>
              </Space>
            </Col>
            <Col xs={12} sm={6}>
              <Space size={4}>
                <ClockCircleOutlined style={{ color: '#4BA8E8' }} />
                <Text type="secondary">結束：</Text>
                <Text>{batch.end_time || '—'}</Text>
              </Space>
            </Col>
            <Col xs={12} sm={6}>
              <Space size={4}>
                <Text type="secondary">工時：</Text>
                <Text>{batch.work_hours || '—'}</Text>
              </Space>
            </Col>
            <Col xs={12} sm={6}>
              <Space size={4}>
                <Text type="secondary">巡檢人員：</Text>
                <Text strong>{batch.inspector_name || '—'}</Text>
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* KPI Cards */}
      <Row gutter={12} style={{ marginBottom: 20 }}>
        {kpiCards.map(c => (
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
                <Text>巡檢完成率</Text>
                <div style={{
                  flex: 1, height: 12, background: '#f0f0f0', borderRadius: 6, overflow: 'hidden',
                }}>
                  <div style={{
                    width: `${kpi.completion_rate}%`, height: '100%',
                    background: kpi.completion_rate >= 90 ? '#52C41A'
                      : kpi.completion_rate >= 60 ? '#FAAD14' : '#FF4D4F',
                    borderRadius: 6, transition: 'width 0.5s',
                  }} />
                </div>
                <Text strong style={{ minWidth: 48, textAlign: 'right' }}>
                  {kpi.completion_rate}%
                </Text>
              </div>
            </Card>
          </Col>
        )}
      </Row>

      {/* 篩選區 */}
      <Card
        size="small"
        style={{ marginBottom: 16, borderColor: isAdvanced ? '#4BA8E8' : undefined }}
      >
        <Space wrap>
          <Input
            placeholder="搜尋巡檢項目"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            allowClear
            style={{ width: 220 }}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>共 {filteredItems.length} 筆</Text>
        </Space>

        {/* 進階狀態複選 */}
        <div style={{
          marginTop: 10, paddingTop: 10, borderTop: '1px dashed #e0e0e0',
          display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap',
        }}>
          <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
            <FilterOutlined style={{ marginRight: 4 }} />
            狀態複選：
          </Text>
          <Select
            mode="multiple"
            placeholder="選擇狀態（空白 = 使用 Tab）"
            value={statusFilters}
            onChange={setStatusFilters}
            allowClear
            style={{ minWidth: 280, flex: 1 }}
            maxTagCount="responsive"
            options={STATUS_TABS.filter(t => t.key !== 'all').map(t => ({
              value: t.key,
              label: (
                <span>
                  <Tag color={STATUS_CFG[t.key]?.tagColor} style={{ margin: '0 4px 0 0', fontSize: 11 }}>
                    {t.label}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>({tabCounts[t.key] ?? 0})</Text>
                </span>
              ),
            }))}
          />
          {isAdvanced && (
            <Button size="small" onClick={() => setStatusFilters([])}>清除複選</Button>
          )}
        </div>
      </Card>

      {/* 狀態 Tabs + 表格 */}
      <Card bodyStyle={{ padding: 0 }}>
        <div style={{ borderBottom: '1px solid #f0f0f0', padding: '0 16px', display: 'flex', gap: 0, overflowX: 'auto' }}>
          {STATUS_TABS.map(t => {
            const isActive = statusFilters.length === 0 && activeTab === t.key
            const count = tabCounts[t.key]
            return (
              <div
                key={t.key}
                onClick={() => { setStatusFilters([]); setActiveTab(t.key) }}
                style={{
                  padding: '12px 16px', fontSize: 14, cursor: 'pointer', whiteSpace: 'nowrap',
                  borderBottom: isActive ? '2px solid #1B3A5C' : '2px solid transparent',
                  color: isActive ? '#1B3A5C' : '#595959',
                  fontWeight: isActive ? 600 : 400,
                  transition: 'all .2s',
                }}
              >
                {t.label}
                {count !== undefined && (
                  <Tag style={{ marginLeft: 4, fontSize: 11 }}
                    color={count > 0 && ['abnormal', 'pending'].includes(t.key) ? 'error' : undefined}
                  >
                    {count ?? 0}
                  </Tag>
                )}
              </div>
            )
          })}
          {statusFilters.length > 0 && (
            <div style={{
              padding: '12px 16px', fontSize: 14, cursor: 'default', whiteSpace: 'nowrap',
              borderBottom: '2px solid #4BA8E8', color: '#4BA8E8', fontWeight: 600,
            }}>
              複選篩選中
            </div>
          )}
        </div>

        <Table<InspectionItem>
          loading={loading}
          dataSource={filteredItems}
          rowKey="ragic_id"
          columns={columns}
          size="small"
          pagination={{ pageSize: 35, showTotal: n => `共 ${n} 筆` }}
          onRow={rec => ({
            style: { background: STATUS_CFG[rec.result_status]?.rowBg },
          })}
        />
      </Card>

      {/* 歷史 Drawer */}
      <ItemHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        historyData={historyData}
        loading={historyLoading}
      />
    </div>
  )
}
