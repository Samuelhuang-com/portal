/**
 * K2 — SLA 達成率追蹤 Tab
 * 合約 Drawer → SLA 追蹤
 */
import React, { useState, useEffect, useCallback } from 'react'
import {
  Table, Button, Space, Modal, Form, Input, Select, InputNumber,
  Popconfirm, Tag, message, Typography, Empty, Tabs, DatePicker,
  Progress, Statistic, Row, Col, Card,
} from 'antd'
import {
  PlusOutlined, DeleteOutlined, ReloadOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts'
import dayjs from 'dayjs'
import type {
  SlaMetric, SlaMetricCreate, SlaRecord, SlaMetricSummary,
} from '@/types/contract'
import {
  fetchSlaMetrics, createSlaMetric, deleteSlaMetric,
  fetchSlaSummary, createSlaRecord, deleteSlaRecord,
} from '@/api/contract'
import { slaMetricTypesApi } from '@/api/referenceData'
import type { SlaMetricTypeOption } from '@/api/referenceData'

const { Text } = Typography

const PERIOD_OPTIONS = [
  { value: 'monthly', label: '月度' },
  { value: 'quarterly', label: '季度' },
  { value: 'annual', label: '年度' },
]
const UNIT_OPTIONS = ['%', '小時', '天', '次', 'ms']

// ── 達成率環形指示 ──────────────────────────────────────────────────────────

function AchievementBadge({ rate }: { rate?: number | null }) {
  if (rate == null) return <Text type="secondary">尚無記錄</Text>
  const color = rate >= 90 ? '#52c41a' : rate >= 70 ? '#faad14' : '#ff4d4f'
  return (
    <Progress
      type="circle"
      percent={rate}
      size={56}
      strokeColor={color}
      format={p => <span style={{ fontSize: 12, fontWeight: 700 }}>{p}%</span>}
    />
  )
}

// ── 單一指標的趨勢圖 ────────────────────────────────────────────────────────

function MetricTrendChart({ metric }: { metric: SlaMetricSummary }) {
  if (!metric.trend.length) {
    return <Empty description="尚無記錄" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ padding: 24 }} />
  }
  const data = metric.trend.map(t => ({
    period: t.period,
    actual: Number(t.actual),
    target: Number(t.target),
  }))
  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="period" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v: number, n: string) => [
          `${v}${metric.target_unit}`,
          n === 'actual' ? '實際值' : '目標值',
        ]} />
        <ReferenceLine
          y={metric.target_value}
          stroke="#ff4d4f"
          strokeDasharray="4 2"
          label={{ value: `目標 ${metric.target_value}${metric.target_unit}`, fill: '#ff4d4f', fontSize: 10 }}
        />
        <Line type="monotone" dataKey="actual" stroke="#4BA8E8" strokeWidth={2}
          dot={(props: any) => {
            const { cx, cy, payload } = props
            return (
              <circle key={payload.period} cx={cx} cy={cy} r={4}
                fill={payload.actual >= metric.target_value ? '#52c41a' : '#ff4d4f'}
                stroke="white" strokeWidth={1} />
            )
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── 主元件 ──────────────────────────────────────────────────────────────────

export default function ContractSlaTab({
  contractId, open,
}: { contractId: string; open: boolean }) {
  const [summary, setSummary] = useState<{ metrics: SlaMetricSummary[]; overall?: number | null } | null>(null)
  const [metrics, setMetrics] = useState<SlaMetric[]>([])
  const [loading, setLoading] = useState(false)
  const [typeOptions, setTypeOptions] = useState<SlaMetricTypeOption[]>([])
  const [addMetricOpen, setAddMetricOpen] = useState(false)
  const [addRecordOpen, setAddRecordOpen] = useState<number | null>(null)  // metric_id
  const [saving, setSaving] = useState(false)
  const [metricForm] = Form.useForm()
  const [recordForm] = Form.useForm()

  const load = useCallback(async () => {
    if (!open) return
    setLoading(true)
    try {
      const [sum, met, types] = await Promise.all([
        fetchSlaSummary(contractId),
        fetchSlaMetrics(contractId),
        slaMetricTypesApi.options(),
      ])
      setSummary({ metrics: sum.metrics, overall: sum.overall_achievement_rate })
      setMetrics(met.metrics)
      setTypeOptions(types.data)
    } catch {
      message.error('載入 SLA 資料失敗')
    } finally {
      setLoading(false)
    }
  }, [contractId, open])

  useEffect(() => { load() }, [load])

  const handleAddMetric = async () => {
    try {
      const v = await metricForm.validateFields()
      setSaving(true)
      const payload: SlaMetricCreate = {
        metric_name: v.metric_name,
        metric_type: v.metric_type || '自訂',
        target_value: v.target_value,
        target_unit: v.target_unit || '%',
        measurement_period: v.measurement_period || 'monthly',
        description: v.description,
      }
      await createSlaMetric(contractId, payload)
      message.success('已新增 SLA 指標')
      setAddMetricOpen(false)
      metricForm.resetFields()
      load()
    } catch (err: any) {
      if (err?.response?.data?.detail) message.error(err.response.data.detail)
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteMetric = async (id: number) => {
    try {
      await deleteSlaMetric(contractId, id)
      message.success('已刪除指標（相關記錄一併刪除）')
      load()
    } catch {
      message.error('刪除失敗')
    }
  }

  const handleAddRecord = async () => {
    if (addRecordOpen == null) return
    try {
      const v = await recordForm.validateFields()
      setSaving(true)
      await createSlaRecord(contractId, {
        metric_id: addRecordOpen,
        period_label: v.period_label,
        period_start: v.period_start.format('YYYY-MM-DD'),
        period_end: v.period_end.format('YYYY-MM-DD'),
        actual_value: v.actual_value,
        notes: v.notes,
      })
      message.success('已登錄達成記錄')
      setAddRecordOpen(null)
      recordForm.resetFields()
      load()
    } catch (err: any) {
      if (err?.response?.data?.detail) message.error(err.response.data.detail)
    } finally {
      setSaving(false)
    }
  }

  const isEmpty = !metrics.length && !loading

  return (
    <>
      {/* 空白引導（Modal 仍在下方 render，點擊可正常開啟） */}
      {isEmpty && (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Empty description="尚未設定 SLA 指標" image={Empty.PRESENTED_IMAGE_SIMPLE}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => { metricForm.resetFields(); setAddMetricOpen(true) }}
            >
              新增第一個 SLA 指標
            </Button>
          </Empty>
        </div>
      )}

      {/* 總覽 KPI */}
      {!isEmpty && summary && (
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Card size="small">
              <Statistic title="整體達成率" value={summary.overall ?? '—'}
                suffix={summary.overall != null ? '%' : ''}
                valueStyle={{ color: (summary.overall ?? 0) >= 90 ? '#52c41a' : '#fa8c16', fontSize: 20 }} />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic title="指標數量" value={metrics.length} suffix="個" />
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small">
              <Statistic
                title="未達標指標"
                value={summary.metrics.filter(m => (m.achievement_rate ?? 100) < 100).length}
                suffix="個"
                valueStyle={{ color: summary.metrics.some(m => (m.achievement_rate ?? 100) < 100) ? '#ff4d4f' : '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {!isEmpty && (
        <Space style={{ marginBottom: 12 }}>
          <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>重新載入</Button>
          <Button size="small" type="primary" icon={<PlusOutlined />}
            onClick={() => { metricForm.resetFields(); setAddMetricOpen(true) }}>
            新增指標
          </Button>
        </Space>
      )}

      {/* 各指標卡片 */}
      {(summary?.metrics || []).map(m => (
        <Card
          key={m.metric_id}
          size="small"
          style={{ marginBottom: 12 }}
          title={
            <Space>
              <Text strong>{m.metric_name}</Text>
              <Tag>{m.metric_type}</Tag>
              <Tag color="blue">{PERIOD_OPTIONS.find(p => p.value === m.measurement_period)?.label}</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>
                目標：{m.target_value}{m.target_unit}
              </Text>
            </Space>
          }
          extra={
            <Space>
              <AchievementBadge rate={m.achievement_rate} />
              <Button size="small" icon={<PlusOutlined />}
                onClick={() => { recordForm.resetFields(); setAddRecordOpen(m.metric_id) }}>
                登錄
              </Button>
              <Popconfirm title="確定刪除此指標及所有記錄？"
                onConfirm={() => handleDeleteMetric(m.metric_id)}
                okText="刪除" cancelText="取消">
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </Space>
          }
        >
          <Row gutter={8}>
            <Col span={4}>
              <Text type="secondary" style={{ fontSize: 12 }}>已記錄 {m.record_count} 期 / 達標 {m.achieved_count} 期</Text>
            </Col>
            <Col span={20}>
              <MetricTrendChart metric={m} />
            </Col>
          </Row>
        </Card>
      ))}

      {/* 新增指標 Modal */}
      <Modal title="新增 SLA 指標" open={addMetricOpen}
        onOk={handleAddMetric} onCancel={() => setAddMetricOpen(false)}
        confirmLoading={saving} okText="新增" cancelText="取消" destroyOnClose width={520}>
        <Form form={metricForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="metric_name" label="指標名稱" rules={[{ required: true }]}>
            <Input placeholder="例：系統可用率" />
          </Form.Item>
          <Space style={{ width: '100%' }} size={8}>
            <Form.Item name="metric_type" label="指標類型" style={{ flex: 1 }}>
              <Select
                placeholder="選擇指標類型"
                options={typeOptions}
                allowClear
              />
            </Form.Item>
            <Form.Item name="measurement_period" label="衡量週期" style={{ flex: 1 }} initialValue="monthly">
              <Select options={PERIOD_OPTIONS} />
            </Form.Item>
          </Space>
          <Space style={{ width: '100%' }} size={8}>
            <Form.Item name="target_value" label="目標值" style={{ flex: 1 }} rules={[{ required: true }]}>
              <InputNumber style={{ width: '100%' }} min={0} precision={2} />
            </Form.Item>
            <Form.Item name="target_unit" label="單位" initialValue="%">
              <Select
                options={UNIT_OPTIONS.map(u => ({ value: u, label: u }))}
                popupMatchSelectWidth={false}
                style={{ minWidth: 72 }}
              />
            </Form.Item>
          </Space>
          <Form.Item name="description" label="說明">
            <Input.TextArea rows={2} placeholder="指標定義說明（可選）" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 登錄達成記錄 Modal */}
      <Modal
        title={`登錄達成記錄：${metrics.find(m => m.id === addRecordOpen)?.metric_name || ''}`}
        open={addRecordOpen != null}
        onOk={handleAddRecord} onCancel={() => setAddRecordOpen(null)}
        confirmLoading={saving} okText="確認登錄" cancelText="取消" destroyOnClose width={480}
      >
        <Form form={recordForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="period_label" label="期間標籤" rules={[{ required: true }]}
            tooltip="如：2026-01（月度）或 2026-Q1（季度）">
            <Input placeholder="2026-01" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="period_start" label="期間起" rules={[{ required: true }]} style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="period_end" label="期間迄" rules={[{ required: true }]} style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Space>
          <Form.Item name="actual_value" label="實際達成值" rules={[{ required: true }]}>
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              precision={2}
              addonAfter={metrics.find(m => m.id === addRecordOpen)?.target_unit || '%'}
            />
          </Form.Item>
          <Form.Item name="notes" label="備註（未達標原因等）">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
