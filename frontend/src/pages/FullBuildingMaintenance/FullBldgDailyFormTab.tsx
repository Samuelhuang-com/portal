/**
 * 全棟例行維護 — 每日巡檢表 TAB
 *
 * 2026-07-13 改版：原本此 TAB 掛的是「整棟巡檢」（Ragic full-building-inspection/1-4，
 * RF/B1F/B2F/B4F 固定巡檢清單）placeholder，從未實作本地同步，且資料結構與本模組
 * （全棟週期保養日誌，Ragic Sheet 21/28）完全無關，導致畫面永遠空白。
 *
 * 改為：依「排定日期」篩選當月批次（資料來源 Sheet28）中排定在指定日期的保養項目，
 * 呈現「當天該做哪些保養項目」的日檢視表 —— 與 Dashboard／批次明細頁共用同一套
 * 資料與 KPI 計算邏輯（後端 _calc_kpi / _calc_status），數字保證一致。
 */
import { useState, useCallback, useEffect } from 'react'
import {
  Alert, Button, Col, DatePicker, Row, Segmented, Statistic, Table, Tag, Typography,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import {
  fetchFullBldgPMDailyForm,
  type PMDailyFormResponse,
  type PMDailyFormView,
} from '@/api/fullBuildingMaintenance'
import type { PMItem } from '@/types/periodicMaintenance'
import PMItemWorklogDrawer from '@/components/PMItemWorklogDrawer'

const { Text } = Typography

// ── 狀態設定（與 Detail.tsx 對齊）──────────────────────────────────────────────
const STATUS_CFG: Record<string, { label: string; color: string }> = {
  completed:         { label: '已完成', color: '#52C41A' },
  in_progress:       { label: '進行中', color: '#4BA8E8' },
  scheduled:         { label: '已排定', color: '#FAAD14' },
  unscheduled:       { label: '未排定', color: '#FF4D4F' },
  overdue:           { label: '逾期',   color: '#C0392B' },
  non_current_month: { label: '非本月', color: '#999999' },
}

function fmtMinutes(mins: number): string {
  if (!mins) return '—'
  if (mins < 60) return `${mins} 分`
  return `${Math.floor(mins / 60)} 時 ${mins % 60} 分`
}

function fmtHours(hours: number | null | undefined): string {
  if (hours == null) return '—'
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  if (h === 0) return `${m} 分`
  if (m === 0) return `${h} 時`
  return `${h} 時 ${m} 分`
}

function fmtTimeRange(item: PMItem): string {
  if (item.repair_hours != null) return fmtHours(item.repair_hours)
  if (item.start_time && item.end_time) {
    const s = item.start_time.split(' ')[1] || item.start_time
    const e = item.end_time.split(' ')[1] || item.end_time
    return `${s} ~ ${e}`
  }
  if (item.start_time) return `${item.start_time.split(' ')[1] || item.start_time} 起`
  return '—'
}

/** 實際保養日期（取 start_time，缺則取 end_time 的日期部分），格式 MM/DD；尚未執行則 '—' */
function fmtActualDate(item: PMItem): string {
  const raw = (item.start_time || item.end_time || '').trim()
  if (!raw) return '—'
  const datePart = raw.split(' ')[0]
  const parts = datePart.split('/')
  return parts.length === 3 ? `${parts[1]}/${parts[2]}` : datePart
}

export default function FullBldgDailyFormTab() {
  const today = dayjs()
  const [view,            setView]            = useState<PMDailyFormView>('day')
  const [inspectionDate,  setInspectionDate]   = useState<string>(today.format('YYYY/MM/DD'))
  const [monthDate,       setMonthDate]        = useState<string>(today.format('YYYY/MM/01'))
  const [loading,  setLoading]  = useState(false)
  const [data,      setData]    = useState<PMDailyFormResponse | null>(null)

  // ── 保養項目明細 Drawer state（2026-07-13 重新設計，共用 PMItemWorklogDrawer）──────
  const [selectedPMItem, setSelectedPMItem] = useState<PMItem | null>(null)

  const load = useCallback(async (dateStr: string, viewMode: PMDailyFormView) => {
    setLoading(true)
    try {
      const res = await fetchFullBldgPMDailyForm(dateStr, viewMode)
      setData(res)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const activeDate = view === 'day' ? inspectionDate : monthDate

  useEffect(() => { load(activeDate, view) }, [load, activeDate, view])

  const rows = data?.rows ?? []
  const summary = data?.summary
  const isMonthView = view === 'month'

  const columns: ColumnsType<PMItem> = [
    { title: '類別', dataIndex: 'category', width: 90 },
    { title: '項目', dataIndex: 'task_name', width: 220 },
    ...(isMonthView
      ? [{ title: '排定日期', dataIndex: 'scheduled_date', width: 90, align: 'center' as const }]
      : []),
    { title: '頻率', dataIndex: 'frequency', width: 70, align: 'center' },
    {
      title: '預估耗時', dataIndex: 'estimated_minutes', width: 90, align: 'center',
      render: (v: number) => fmtMinutes(v),
    },
    {
      title: '狀態', dataIndex: 'status', width: 90, align: 'center',
      render: (s: string) => {
        const cfg = STATUS_CFG[s] || { label: s, color: '#666666' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '執行人員', dataIndex: 'executor_name', width: 100,
      render: (v: string) => v || <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
    {
      title: '保養日期', width: 90, align: 'center',
      render: (_: unknown, rec: PMItem) => <Text style={{ fontSize: 12 }}>{fmtActualDate(rec)}</Text>,
    },
    {
      title: '保養時間', width: 150,
      render: (_: unknown, rec: PMItem) => {
        const label = fmtTimeRange(rec)
        if (label === '—') return <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
        return (
          <Button
            type="link" size="small" style={{ padding: 0, height: 'auto', fontSize: 12 }}
            onClick={() => setSelectedPMItem(rec)}
          >
            {label}
          </Button>
        )
      },
    },
    {
      title: '異常說明', dataIndex: 'abnormal_note',
      render: (v: string) => v
        ? <Text type="danger" style={{ fontSize: 11, whiteSpace: 'pre-wrap' }}>{v}</Text>
        : <Text type="secondary" style={{ fontSize: 11 }}>—</Text>,
    },
  ]

  return (
    <div>
      <Row gutter={8} style={{ marginBottom: 16 }} align="middle">
        <Col>
          <Segmented
            value={view}
            options={[{ label: '當日', value: 'day' }, { label: '整月', value: 'month' }]}
            onChange={(v) => setView(v as PMDailyFormView)}
          />
        </Col>
        <Col>
          {isMonthView ? (
            <DatePicker
              picker="month"
              value={dayjs(monthDate, 'YYYY/MM/DD')}
              format="YYYY/MM"
              allowClear={false}
              onChange={(d) => { if (d) setMonthDate(d.startOf('month').format('YYYY/MM/DD')) }}
            />
          ) : (
            <DatePicker
              value={dayjs(inspectionDate, 'YYYY/MM/DD')}
              format="YYYY/MM/DD"
              allowClear={false}
              onChange={(d) => { if (d) setInspectionDate(d.format('YYYY/MM/DD')) }}
            />
          )}
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={() => load(activeDate, view)} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      {data && !data.batch_ragic_id && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message={`查無 ${data.period_month} 批次資料`}
          description="尚未從 Ragic 同步該月份的全棟週期保養日誌批次，請確認同步是否已執行。"
        />
      )}

      {summary && (
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={4}><Statistic title={isMonthView ? '本月項目' : '當日項目'} value={summary.total} /></Col>
          <Col span={4}><Statistic title="已完成" value={summary.completed} valueStyle={{ color: '#52C41A' }} /></Col>
          <Col span={4}><Statistic title="逾期" value={summary.overdue} valueStyle={{ color: '#C0392B' }} /></Col>
          <Col span={4}><Statistic title="異常" value={summary.abnormal} valueStyle={{ color: '#FF4D4F' }} /></Col>
          <Col span={4}><Statistic title="預估工時" value={fmtMinutes(summary.planned_minutes)} /></Col>
          <Col span={4}><Statistic title="保養時間" value={fmtMinutes(summary.actual_minutes)} /></Col>
        </Row>
      )}

      <Table<PMItem>
        dataSource={rows}
        rowKey={(r) => r.ragic_id}
        columns={columns}
        loading={loading}
        size="small"
        pagination={isMonthView ? { pageSize: 20, showTotal: (t: number) => `共 ${t} 項` } : false}
        bordered
        rowClassName={(r) => r.abnormal_flag ? 'row-abnormal' : ''}
        style={{ fontSize: 12 }}
        locale={{ emptyText: isMonthView ? '本月尚無保養項目' : '當日尚無排定保養項目' }}
      />

      <PMItemWorklogDrawer
        open={!!selectedPMItem}
        onClose={() => setSelectedPMItem(null)}
        item={selectedPMItem}
      />
    </div>
  )
}
