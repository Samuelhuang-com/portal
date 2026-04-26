/**
 * 大直工務部 — 主模組頁面
 *
 * 包含 7 個 Tab：
 *   Dashboard | 4.1 報修 | 4.2 結案時間 | 4.3 報修類型 | 4.4 本月客房報修表 | 金額統計 | 大直工務部
 *
 * 查詢條件（年/月）置於頁面頂部，各 Tab 共享。
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Select, Spin, Alert, Tabs,
  Tooltip, Badge, Drawer, Descriptions, message, Modal,
  Empty, Divider, Progress,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, ToolOutlined,
  CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, FileTextOutlined, DownloadOutlined,
  WarningOutlined, DollarOutlined, SearchOutlined, BuildOutlined,
  SyncOutlined, ApiOutlined,
} from '@ant-design/icons'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RcTooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell,
} from 'recharts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchDashboard, fetchRepairStats, fetchClosingStats,
  fetchTypeStats, fetchRoomRepairTable, fetchDetail,
  fetchYears, fetchFilterOptions, buildExportUrl, fetchSync, fetchPing,
  fetchFeeStats, fetchCaseImages,
} from '@/api/dazhiRepair'
import type { SyncResult, PingResult, CaseImageItem } from '@/api/dazhiRepair'
import type {
  DashboardData, RepairStatsData, ClosingTimeData, TypeStatsData,
  RoomRepairTableData, DetailResult, FilterOptions, RepairCase,
  FeeStatsData,
} from '@/types/dazhiRepair'
import { NAV_GROUP } from '@/constants/navLabels'

const { Title, Text } = Typography
const { Option } = Select

// ── 常數 ──────────────────────────────────────────────────────────────────────
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)
const STATUS_COLOR: Record<string, string> = {
  '已驗收': '#52C41A', '已結案': '#52C41A', '結案': '#52C41A',
  '完修': '#52C41A', '已完成': '#52C41A', '完成': '#52C41A',
  '已辦驗': '#52C41A',
  '處理中': '#1890FF', '進行中': '#1890FF', '委外處理': '#1890FF',
  '待維修': '#FAAD14', '待驗收': '#FAAD14', '待修中': '#FAAD14',
  '待料中': '#FAAD14', '待辦驗': '#FAAD14', '待確認': '#FAAD14',
  '待協調': '#FF7A45', '待排除': '#FF4D4F', '辦驗未通過': '#FF4D4F',
  '取消': '#8C8C8C',
}
const STATUS_TAG_COLOR: Record<string, string> = {
  '已驗收': 'success', '已結案': 'success', '結案': 'success',
  '完修': 'success', '已完成': 'success', '完成': 'success',
  '已辦驗': 'success',
  '處理中': 'processing', '進行中': 'processing', '委外處理': 'processing',
  '待維修': 'warning', '待驗收': 'warning', '待修中': 'warning',
  '待料中': 'warning', '待辦驗': 'warning', '待確認': 'warning',
  '待協調': 'orange', '待排除': 'error', '辦驗未通過': 'error',
  '取消': 'default',
}
const PIE_COLORS = ['#1B3A5C', '#4BA8E8', '#52C41A', '#FAAD14', '#FF4D4F', '#722ED1', '#13C2C2', '#FA8C16']

// ── 工具函式 ──────────────────────────────────────────────────────────────────
const fmt = (n: number | null | undefined) =>
  n == null ? '-' : n.toLocaleString('zh-TW', { minimumFractionDigits: 0, maximumFractionDigits: 0 })

const fmtDec = (n: number | null | undefined, d = 1) =>
  n == null ? '-' : n.toFixed(d)

const fmtMoney = (n: number | null | undefined) =>
  n == null ? '-' : `$${n.toLocaleString('zh-TW')}`

const statusTag = (status: string) => {
  const color = STATUS_TAG_COLOR[status] ?? 'default'
  return <Tag color={color}>{status || '-'}</Tag>
}

// ═════════════════════════════════════════════════════════════════════════════
// 共用：案件清單 Modal（所有統計數字點擊後共用）
// ═════════════════════════════════════════════════════════════════════════════
const CASE_LIST_COLS: import('antd/es/table').ColumnsType<RepairCase> = [
  { title: '報修編號', dataIndex: 'case_no', width: 110, fixed: 'left' as const },
  { title: '標題',     dataIndex: 'title',   width: 180, ellipsis: true },
  { title: '樓層',     dataIndex: 'floor',   width: 70 },
  { title: '報修時間', dataIndex: 'occurred_at', width: 120 },
  { title: '狀態',     dataIndex: 'status',  width: 90,
    render: (v: string) => <Tag color={STATUS_TAG_COLOR[v] ?? 'default'}>{v || '-'}</Tag> },
  { title: '結案天數', dataIndex: 'close_days', width: 90, align: 'right' as const,
    render: (v: number | null) => v != null ? `${fmtDec(v, 1)} 天` : '-' },
  { title: '費用合計', dataIndex: 'total_fee', width: 120, align: 'right' as const,
    render: (v: number) => v > 0 ? <span style={{ color: '#722ED1', fontWeight: 600 }}>{fmtMoney(v)}</span> : '-' },
]

function CaseListModal({
  title, cases, open, onClose, extra,
  extraColumns,
  tableSummary,
}: {
  title: React.ReactNode
  cases: RepairCase[]
  open: boolean
  onClose: () => void
  extra?: React.ReactNode
  extraColumns?: import('antd/es/table').ColumnsType<RepairCase>
  tableSummary?: (pageData: readonly RepairCase[]) => React.ReactNode
}) {
  const [drawerCase, setDrawerCase] = useState<RepairCase | null>(null)
  return (
    <>
      <Modal
        title={title}
        open={open}
        onCancel={onClose}
        footer={<Button onClick={onClose}>關閉</Button>}
        width={1020}
        destroyOnClose
      >
        {extra && <div style={{ marginBottom: 10 }}>{extra}</div>}
        {cases.length === 0
          ? <Empty description="無相關案件" />
          : (
            <Table
              size="small"
              dataSource={cases}
              rowKey="ragic_id"
              scroll={{ x: 880 }}
              pagination={{ pageSize: 20, showSizeChanger: false, showTotal: t => `共 ${t} 筆` }}
              summary={tableSummary}
              columns={[
                ...CASE_LIST_COLS,
                ...(extraColumns ?? []),
                {
                  title: '詳情', width: 60, fixed: 'right' as const,
                  render: (_: unknown, rec: RepairCase) => (
                    <Button size="small" type="link" onClick={() => setDrawerCase(rec)}>詳情</Button>
                  )
                },
              ]}
            />
          )
        }
      </Modal>
      <CaseDetailDrawer caseData={drawerCase} onClose={() => setDrawerCase(null)} />
    </>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// KPI 卡片子元件
// ═════════════════════════════════════════════════════════════════════════════
function KpiCard({
  title, value, suffix = '', color, icon, sub, onClick,
}: {
  title: string; value: string | number; suffix?: string
  color: string; icon: React.ReactNode; sub?: string
  onClick?: () => void
}) {
  return (
    <Card
      size="small"
      hoverable={!!onClick}
      onClick={onClick}
      style={{ textAlign: 'center', borderTop: `3px solid ${color}`, cursor: onClick ? 'pointer' : 'default' }}
    >
      <div style={{ color, fontSize: 26, marginBottom: 2 }}>{icon}</div>
      <div style={{ color, fontSize: 28, fontWeight: 700, lineHeight: 1.2 }}>
        {value}
        {suffix && <span style={{ fontSize: 13, marginLeft: 4, fontWeight: 400 }}>{suffix}</span>}
      </div>
      <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>{title}</div>
      {sub && <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>{sub}</div>}
      {onClick && <div style={{ color: '#bbb', fontSize: 10, marginTop: 3 }}>點擊查看明細</div>}
    </Card>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// 查詢列子元件
// ═════════════════════════════════════════════════════════════════════════════
function QueryBar({
  year, month, years, onYearChange, onMonthChange, onQuery, onReset, loading,
  showMonth = true, monthRequired = false,
}: {
  year: number; month: number | null; years: number[]
  onYearChange: (y: number) => void; onMonthChange: (m: number | null) => void
  onQuery: () => void; onReset: () => void; loading?: boolean
  showMonth?: boolean; monthRequired?: boolean
}) {
  return (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Space wrap>
        <Space>
          <Text strong>年度：</Text>
          <Select value={year} style={{ width: 100 }} onChange={onYearChange}>
            {years.map(y => <Option key={y} value={y}>{y} 年</Option>)}
          </Select>
        </Space>
        {showMonth && (
          <Space>
            <Text strong>月份：</Text>
            <Select
              value={month ?? 0}
              style={{ width: 110 }}
              onChange={(v) => onMonthChange(v === 0 ? null : v)}
            >
              {!monthRequired && <Option value={0}>全年</Option>}
              {MONTHS.map(m => <Option key={m} value={m}>{m} 月</Option>)}
            </Select>
          </Space>
        )}
        <Button type="primary" icon={<SearchOutlined />} onClick={onQuery} loading={loading}>
          查詢
        </Button>
        <Button onClick={onReset}>重設</Button>
      </Space>
    </Card>
  )
}

// ── 共用：報修詳情 Drawer ─────────────────────────────────────────────────────
function CaseDetailDrawer({
  caseData, onClose,
}: { caseData: RepairCase | null; onClose: () => void }) {
  const [liveImages, setLiveImages] = useState<CaseImageItem[]>([])
  const [imgLoading, setImgLoading] = useState(false)

  useEffect(() => {
    if (!caseData?.ragic_id) { setLiveImages([]); return }
    setImgLoading(true)
    fetchCaseImages(caseData.ragic_id)
      .then(imgs => setLiveImages(imgs))
      .catch(() => setLiveImages([]))
      .finally(() => setImgLoading(false))
  }, [caseData?.ragic_id])

  if (!caseData) return null
  const images = liveImages.length > 0 ? liveImages : (caseData.images ?? [])

  return (
    <Drawer
      title={
        <Space>
          <ToolOutlined style={{ color: '#1B3A5C' }} />
          <span>報修詳情：{caseData.case_no || caseData.ragic_id}</span>
        </Space>
      }
      open={!!caseData}
      onClose={onClose}
      width={520}
      destroyOnClose
    >
      <Descriptions column={1} bordered size="small" labelStyle={{ width: 120, fontWeight: 500, background: '#f8f9fb' }}>
        <Descriptions.Item label="報修編號">{caseData.case_no || '-'}</Descriptions.Item>
        <Descriptions.Item label="標題"><strong>{caseData.title || '-'}</strong></Descriptions.Item>
        <Descriptions.Item label="報修人姓名">{caseData.reporter_name || '-'}</Descriptions.Item>
        <Descriptions.Item label="報修類型"><Tag>{caseData.repair_type || '-'}</Tag></Descriptions.Item>
        <Descriptions.Item label="發生樓層">{caseData.floor || '-'}</Descriptions.Item>
        <Descriptions.Item label="發生時間">{caseData.occurred_at || '-'}</Descriptions.Item>
        <Descriptions.Item label="負責單位">{caseData.responsible_unit || '-'}</Descriptions.Item>
        <Descriptions.Item label="花費工時">
          {caseData.work_hours > 0 ? `${fmtDec(caseData.work_hours, 2)} hr` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="處理狀況">{statusTag(caseData.status)}</Descriptions.Item>
        <Descriptions.Item label="委外費用">{caseData.outsource_fee > 0 ? fmtMoney(caseData.outsource_fee) : '-'}</Descriptions.Item>
        <Descriptions.Item label="維修費用">{caseData.maintenance_fee > 0 ? fmtMoney(caseData.maintenance_fee) : '-'}</Descriptions.Item>
        <Descriptions.Item label="總費用">
          <strong style={{ color: caseData.total_fee > 0 ? '#722ED1' : '#333' }}>
            {caseData.total_fee > 0 ? fmtMoney(caseData.total_fee) : '-'}
          </strong>
        </Descriptions.Item>
        <Descriptions.Item label="驗收者">{caseData.acceptor || '-'}</Descriptions.Item>
        <Descriptions.Item label="驗收">{caseData.accept_status || '-'}</Descriptions.Item>
        <Descriptions.Item label="結案人">{caseData.closer || '-'}</Descriptions.Item>
        <Descriptions.Item label="結案時間">{caseData.completed_at || '-'}</Descriptions.Item>
        <Descriptions.Item label="結案天數">
          {caseData.close_days != null ? `${fmtDec(caseData.close_days, 1)} 天` : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="扣款事項">{caseData.deduction_item || '-'}</Descriptions.Item>
        <Descriptions.Item label="扣款費用">
          {caseData.deduction_fee > 0 ? fmtMoney(caseData.deduction_fee) : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="財務備註">{caseData.finance_note || '-'}</Descriptions.Item>
        <Descriptions.Item label="維修圖片">
          {imgLoading
            ? <span style={{ color: '#aaa', fontSize: 12 }}>圖片載入中…</span>
            : images.length > 0
              ? <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {images.map((img, i) => (
                    <a key={i} href={img.url} target="_blank" rel="noopener noreferrer"
                      style={{ fontSize: 13, color: '#1677ff', display: 'flex', alignItems: 'center', gap: 4 }}>
                      📷 {img.filename || `圖片${i + 1}`}
                    </a>
                  ))}
                </div>
              : <span style={{ color: '#ccc', fontSize: 12 }}>-</span>
          }
        </Descriptions.Item>
      </Descriptions>
    </Drawer>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: Dashboard
// ═════════════════════════════════════════════════════════════════════════════
function DashboardTab({
  year, month,
}: { year: number; month: number }) {
  // ── 所有 hooks 必須在任何 early return 之前宣告（Rules of Hooks）──────────
  const [data, setData]       = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [drawerCase, setDrawerCase] = useState<RepairCase | null>(null)
  const [feeModal, setFeeModal] = useState<'fee' | 'deduction' | null>(null)
  const [kpiModal, setKpiModal] = useState<'total' | 'completed' | 'uncompleted' | 'close_days' | 'room' | 'hours' | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const d = await fetchDashboard(year, month)
      setData(d)
    } catch (e: unknown) {
      setError((e as Error).message || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => { load() }, [load])

  // ── Early returns（必須在所有 hooks 之後）─────────────────────────────────
  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" tip="資料載入中..." /></div>
  if (error)   return <Alert type="error" message={`資料載入失敗：${error}`} showIcon />
  if (!data)   return <Empty description="請選擇查詢條件" />

  const { kpi, trend_12m, type_dist, floor_dist, status_dist, top_uncompleted, top_fee, top_hours,
          annual_fee_detail, annual_deduction_detail,
          kpi_total_detail, kpi_completed_detail, kpi_uncompleted_detail,
          kpi_close_days_detail, kpi_room_detail, kpi_hours_detail } = data

  return (
    <div>
      {/* KPI 卡片 — 6 張一排，全部可點擊查看明細 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'nowrap', overflowX: 'auto' }}>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="本月相關案件" value={fmt(kpi.total)} color="#1B3A5C" icon={<ToolOutlined />}
            sub="完工月＋未完成報修月" onClick={() => setKpiModal('total')} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="已完成件數" value={fmt(kpi.completed)} color="#52C41A" icon={<CheckCircleOutlined />}
            sub={`完成率 ${kpi.total > 0 ? fmtDec(kpi.completed / kpi.total * 100) : '-'}% ｜ 依完工時間`}
            onClick={() => setKpiModal('completed')} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="未完成件數" value={fmt(kpi.uncompleted)} color="#FF4D4F" icon={<ExclamationCircleOutlined />}
            sub="無完工時間的案件" onClick={() => setKpiModal('uncompleted')} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="平均結案天數" value={kpi.avg_close_days != null ? fmtDec(kpi.avg_close_days, 1) : '-'}
            suffix="天" color="#4BA8E8" icon={<ClockCircleOutlined />}
            onClick={() => setKpiModal('close_days')} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="本月工時統計" value={fmtDec(kpi.total_work_hours, 2)} suffix="hr"
            color="#13C2C2" icon={<ClockCircleOutlined />}
            sub={`${fmtDec(kpi.total_work_hours / 24, 2)} 天（維修天數×24 ÷24）`}
            onClick={() => setKpiModal('hours')} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="客房報修件數" value={fmt(kpi.room_cases)} color="#FA8C16" icon={<HomeOutlined />}
            onClick={() => setKpiModal('room')} />
        </div>
      </div>

      {/* KPI 明細 Modals */}
      <CaseListModal title={<><ToolOutlined style={{ color: '#1B3A5C', marginRight: 8 }} />本月相關案件</>}
        cases={kpi_total_detail ?? []} open={kpiModal === 'total'} onClose={() => setKpiModal(null)}
        extra={<Space><Tag color="blue">共 {kpi.total} 筆</Tag><Tag color="default" style={{ fontSize: 11 }}>口徑：有完工時間依完工月、未完成依報修月</Tag></Space>} />
      <CaseListModal title={<><CheckCircleOutlined style={{ color: '#52C41A', marginRight: 8 }} />已完成案件</>}
        cases={kpi_completed_detail ?? []} open={kpiModal === 'completed'} onClose={() => setKpiModal(null)}
        extra={<Space><Tag color="success">已完成 {kpi.completed} 筆</Tag><Tag color="default" style={{ fontSize: 11 }}>有完工時間一律視為完工（含跨月案件）</Tag></Space>}
        extraColumns={[{
          title: '完工時間', dataIndex: 'completed_at', width: 110, align: 'center' as const,
          render: (v: string) => v
            ? <span style={{ color: '#52C41A', fontWeight: 600, fontSize: 11 }}>{v}</span>
            : <span style={{ color: '#ccc' }}>-</span>,
        }]}
      />
      <CaseListModal title={<><ExclamationCircleOutlined style={{ color: '#FF4D4F', marginRight: 8 }} />未完成案件</>}
        cases={kpi_uncompleted_detail ?? []} open={kpiModal === 'uncompleted'} onClose={() => setKpiModal(null)}
        extra={<Space><Tag color="error">未完成 {kpi.uncompleted} 筆</Tag><Tag color="default" style={{ fontSize: 11 }}>完工時間為空的案件</Tag></Space>} />
      <CaseListModal title={<><ClockCircleOutlined style={{ color: '#4BA8E8', marginRight: 8 }} />結案天數明細（已完成）</>}
        cases={kpi_close_days_detail ?? []} open={kpiModal === 'close_days'} onClose={() => setKpiModal(null)}
        extra={<Space><Tag color="blue">平均 {kpi.avg_close_days != null ? fmtDec(kpi.avg_close_days, 1) : '-'} 天</Tag><Tag color="default" style={{ fontSize: 11 }}>完工時間 − 報修日期</Tag></Space>} />
      <CaseListModal title={<><ClockCircleOutlined style={{ color: '#13C2C2', marginRight: 8 }} />工時明細</>}
        cases={kpi_hours_detail ?? []} open={kpiModal === 'hours'} onClose={() => setKpiModal(null)}
        extra={<Space><Tag color="cyan">維修天數合計 {fmtDec(kpi.total_work_hours, 2)} hr</Tag><Tag color="blue">{fmtDec(kpi.total_work_hours / 24, 2)} 天（÷24）</Tag></Space>} />
      <CaseListModal title={<><HomeOutlined style={{ color: '#FA8C16', marginRight: 8 }} />客房報修案件</>}
        cases={kpi_room_detail ?? []} open={kpiModal === 'room'} onClose={() => setKpiModal(null)}
        extra={<Tag color="orange">共 {kpi.room_cases} 筆</Tag>} />

      {/* 年度費用 KPI + 當月金額 — 3 張一排 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
        {/* 委外+維修費用（全年） */}
        <div style={{ flex: '1 1 0', cursor: 'pointer' }} onClick={() => setFeeModal('fee')}>
          <Card size="small" style={{ textAlign: 'center', borderTop: '3px solid #722ED1', transition: 'box-shadow .15s' }}
            hoverable>
            <div style={{ color: '#722ED1', fontSize: 26, marginBottom: 2 }}><DollarOutlined /></div>
            <div style={{ color: '#722ED1', fontSize: 28, fontWeight: 700, lineHeight: 1.2 }}>
              {fmtMoney(kpi.annual_fee ?? kpi.total_fee)}
            </div>
            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>委外+維修費用</div>
            <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>
              委外 {fmtMoney(kpi.annual_outsource_fee)} ／ 維修 {fmtMoney(kpi.annual_maintenance_fee)}
            </div>
            <div style={{ color: '#bbb', fontSize: 10, marginTop: 3 }}>點擊查看明細</div>
          </Card>
        </div>

        {/* 扣款費用（全年） */}
        <div style={{ flex: '1 1 0', cursor: 'pointer' }} onClick={() => setFeeModal('deduction')}>
          <Card size="small" style={{ textAlign: 'center', borderTop: '3px solid #FF4D4F', transition: 'box-shadow .15s' }}
            hoverable>
            <div style={{ color: '#FF4D4F', fontSize: 26, marginBottom: 2 }}><DollarOutlined /></div>
            <div style={{ color: '#FF4D4F', fontSize: 28, fontWeight: 700, lineHeight: 1.2 }}>
              {fmtMoney(kpi.annual_deduction_fee ?? 0)}
            </div>
            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>扣款費用</div>
            <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>全年扣款費用合計</div>
            <div style={{ color: '#bbb', fontSize: 10, marginTop: 3 }}>點擊查看明細</div>
          </Card>
        </div>

        {/* 當月金額（依年+月篩選） */}
        <div style={{ flex: '1 1 0' }}>
          <Card size="small" style={{ borderTop: '3px solid #13C2C2' }}>
            <div style={{ color: '#13C2C2', fontSize: 13, fontWeight: 700, marginBottom: 8, textAlign: 'center' }}>
              當月金額　<span style={{ color: '#bbb', fontSize: 11, fontWeight: 400 }}>{year}年{month}月</span>
            </div>
            <div style={{ fontSize: 12, lineHeight: 2 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>委外+維修</span>
                <span style={{ color: '#722ED1', fontWeight: 600 }}>
                  {(kpi.month_outsource_fee || kpi.month_maintenance_fee)
                    ? fmtMoney((kpi.month_outsource_fee ?? 0) + (kpi.month_maintenance_fee ?? 0))
                    : '-'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>扣款費用</span>
                <span style={{ color: '#FF4D4F', fontWeight: 600 }}>
                  {kpi.month_deduction_fee ? fmtMoney(kpi.month_deduction_fee) : '-'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#888' }}>扣款專櫃</span>
                <span style={{ color: '#FA8C16', fontWeight: 600 }}>
                  {kpi.month_deduction_counter ? fmtMoney(kpi.month_deduction_counter) : '-'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #f0f0f0', marginTop: 2, paddingTop: 2 }}>
                <span style={{ color: '#333', fontWeight: 600 }}>當月小計</span>
                <span style={{ color: '#52C41A', fontWeight: 700 }}>
                  {kpi.month_total_fee ? fmtMoney(kpi.month_total_fee) : '-'}
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* ── 委外+維修費用 明細 Modal ─────────────────────────────────────────── */}
      <Modal
        title={<><DollarOutlined style={{ color: '#722ED1', marginRight: 8 }} />委外+維修費用明細（全年）</>}
        open={feeModal === 'fee'}
        onCancel={() => setFeeModal(null)}
        footer={<Button onClick={() => setFeeModal(null)}>關閉</Button>}
        width={900}
      >
        <div style={{ marginBottom: 10 }}>
          <Tag color="purple" style={{ fontSize: 13 }}>委外費用合計：{fmtMoney(kpi.annual_outsource_fee)}</Tag>
          <Tag color="blue"   style={{ fontSize: 13 }}>維修費用合計：{fmtMoney(kpi.annual_maintenance_fee)}</Tag>
          <Tag color="geekblue" style={{ fontSize: 13 }}>總計：{fmtMoney(kpi.annual_fee)}</Tag>
        </div>
        <Table
          size="small"
          dataSource={annual_fee_detail ?? []}
          rowKey="ragic_id"
          pagination={false}
          columns={[
            { title: '報修編號', dataIndex: 'case_no', width: 120 },
            { title: '標題',     dataIndex: 'title',   width: 180, ellipsis: true },
            { title: '樓層',     dataIndex: 'floor',   width: 80 },
            { title: '日期',     dataIndex: 'occurred_at', width: 120 },
            { title: '委外費用', dataIndex: 'outsource_fee',   width: 100, align: 'right' as const,
              render: (v: number) => v > 0 ? <span style={{ color: '#722ED1' }}>{fmtMoney(v)}</span> : '-' },
            { title: '維修費用', dataIndex: 'maintenance_fee', width: 100, align: 'right' as const,
              render: (v: number) => v > 0 ? <span style={{ color: '#1890ff' }}>{fmtMoney(v)}</span> : '-' },
            { title: '總計',     dataIndex: 'total_fee', width: 100, align: 'right' as const,
              render: (v: number) => <strong style={{ color: '#722ED1' }}>{fmtMoney(v)}</strong> },
          ]}
        />
      </Modal>

      {/* ── 扣款費用 明細 Modal ──────────────────────────────────────────────── */}
      <Modal
        title={<><DollarOutlined style={{ color: '#FF4D4F', marginRight: 8 }} />扣款費用明細（全年）</>}
        open={feeModal === 'deduction'}
        onCancel={() => setFeeModal(null)}
        footer={<Button onClick={() => setFeeModal(null)}>關閉</Button>}
        width={760}
      >
        <div style={{ marginBottom: 10 }}>
          <Tag color="red" style={{ fontSize: 13 }}>扣款費用合計：{fmtMoney(kpi.annual_deduction_fee)}</Tag>
          <Tag style={{ fontSize: 12 }}>共 {annual_deduction_detail?.length ?? 0} 筆</Tag>
        </div>
        {(annual_deduction_detail?.length ?? 0) === 0
          ? <Empty description="全年無扣款費用資料" />
          : (
            <Table
              size="small"
              dataSource={annual_deduction_detail}
              rowKey="ragic_id"
              pagination={false}
              columns={[
                { title: '報修編號', dataIndex: 'case_no',        width: 120 },
                { title: '標題',     dataIndex: 'title',           width: 180, ellipsis: true },
                { title: '日期',     dataIndex: 'occurred_at',     width: 120 },
                { title: '扣款事項', dataIndex: 'deduction_item',  width: 120, ellipsis: true },
                { title: '扣款費用', dataIndex: 'deduction_fee',   width: 110, align: 'right' as const,
                  render: (v: number) => <strong style={{ color: '#FF4D4F' }}>{fmtMoney(v)}</strong> },
              ]}
            />
          )
        }
      </Modal>

      {/* 圖表區 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {/* 近12月趨勢 */}
        <Col xs={24} lg={14}>
          <Card title="近 12 個月報修趨勢" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trend_12m} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={1} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <RcTooltip />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="total"     stroke="#1B3A5C" strokeWidth={2} name="報修件數" dot={{ r: 3 }} />
                <Line type="monotone" dataKey="completed" stroke="#52C41A" strokeWidth={2} name="完成件數" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* 報修類型分布 */}
        <Col xs={24} lg={10}>
          <Card title="報修類型分布" size="small">
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={type_dist} dataKey="count" nameKey="type" cx="50%" cy="50%"
                  outerRadius={75} label={({ type, percent }) =>
                    percent > 0.04 ? `${type} ${(percent * 100).toFixed(0)}%` : ''
                  } labelLine={false}>
                  {type_dist.map((_, idx) => (
                    <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <RcTooltip formatter={(v, n) => [v, n]} />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {/* 樓層分布 */}
        <Col xs={24} md={12}>
          <Card title="發生樓層分布" size="small">
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={floor_dist.slice(0, 10)} layout="vertical" margin={{ left: 20, right: 20 }}>
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="floor" width={60} tick={{ fontSize: 11 }} />
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <RcTooltip />
                <Bar dataKey="count" fill="#4BA8E8" name="件數" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* 處理狀況分布 */}
        <Col xs={24} md={12}>
          <Card title="處理狀況分布" size="small">
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={status_dist} layout="vertical" margin={{ left: 40, right: 20 }}>
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="status" width={70} tick={{ fontSize: 11 }} />
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <RcTooltip />
                <Bar dataKey="count" name="件數" radius={[0, 4, 4, 0]}>
                  {status_dist.map((item, idx) => (
                    <Cell key={idx} fill={STATUS_COLOR[item.status] || '#AAAAAA'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      {/* 快速摘要區 */}
      <Row gutter={[16, 16]}>
        {/* 未完成 Top */}
        <Col xs={24} lg={8}>
          <Card title={<><WarningOutlined style={{ color: '#FF4D4F', marginRight: 6 }} />未完成案件 Top 10</>}
            size="small"
            extra={<span style={{ fontSize: 11, color: '#999' }}>依未完成天數排序</span>}>
            {top_uncompleted.length === 0
              ? <Empty description="無未完成案件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              : top_uncompleted.map((c, i) => (
                <div key={c.ragic_id}
                  onClick={() => setDrawerCase(c)}
                  style={{
                    padding: '6px 0', borderBottom: '1px solid #f0f0f0',
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                    cursor: 'pointer',
                  }}>
                  <Badge count={i + 1} style={{ background: '#FF4D4F', minWidth: 22, fontSize: 11 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1B3A5C' }}>
                      {c.title || c.case_no || '-'}
                    </div>
                    <div style={{ fontSize: 11, color: '#999', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span>{c.occurred_at}</span>
                      <span>·</span>
                      {statusTag(c.status)}
                      {c.pending_days != null && (
                        <Tag color={c.pending_days >= 30 ? 'red' : c.pending_days >= 7 ? 'orange' : 'default'}
                          style={{ marginLeft: 4, fontSize: 10, padding: '0 4px', lineHeight: '16px' }}>
                          已等 {c.pending_days} 天
                        </Tag>
                      )}
                    </div>
                  </div>
                </div>
              ))
            }
          </Card>
        </Col>

        {/* 高費用 Top */}
        <Col xs={24} lg={8}>
          <Card title={<><DollarOutlined style={{ color: '#722ED1', marginRight: 6 }} />高費用案件 Top 10</>} size="small">
            {top_fee.length === 0
              ? <Empty description="本期無費用案件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              : top_fee.map((c, i) => (
                <div key={c.ragic_id}
                  onClick={() => setDrawerCase(c)}
                  style={{
                    padding: '6px 0', borderBottom: '1px solid #f0f0f0',
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                    cursor: 'pointer',
                  }}>
                  <Badge count={i + 1} style={{ background: '#722ED1', minWidth: 22, fontSize: 11 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1B3A5C' }}>
                      {c.title || c.case_no || '-'}
                    </div>
                    <div style={{ fontSize: 11, color: '#722ED1', fontWeight: 600 }}>
                      {fmtMoney(c.total_fee)}
                    </div>
                  </div>
                </div>
              ))
            }
          </Card>
        </Col>

        {/* 高工時 Top */}
        <Col xs={24} lg={8}>
          <Card title={<><ClockCircleOutlined style={{ color: '#4BA8E8', marginRight: 6 }} />高工時案件 Top 10</>} size="small">
            {top_hours.length === 0
              ? <Empty description="本期無工時資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              : top_hours.map((c, i) => (
                <div key={c.ragic_id}
                  onClick={() => setDrawerCase(c)}
                  style={{
                    padding: '6px 0', borderBottom: '1px solid #f0f0f0',
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                    cursor: 'pointer',
                  }}>
                  <Badge count={i + 1} style={{ background: '#4BA8E8', minWidth: 22, fontSize: 11 }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#1B3A5C' }}>
                      {c.title || c.case_no || '-'}
                    </div>
                    <div style={{ fontSize: 11, color: '#4BA8E8', fontWeight: 600 }}>
                      工時 {fmtDec(c.work_hours, 2)} hr
                    </div>
                  </div>
                </div>
              ))
            }
          </Card>
        </Col>
      </Row>

      <CaseDetailDrawer caseData={drawerCase} onClose={() => setDrawerCase(null)} />
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 4.1 報修統計
// ═════════════════════════════════════════════════════════════════════════════
function RepairStatsTab({ year, focusMonth }: { year: number; focusMonth: number | null }) {
  const [data, setData]     = useState<RepairStatsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [modal, setModal]   = useState<{ title: string; cases: RepairCase[] } | null>(null)

  const _now = new Date()
  const currentYear41  = _now.getFullYear()
  const currentMonth41 = _now.getMonth() + 1
  const isFutureMonth = (m: number) =>
    year > currentYear41 || (year === currentYear41 && m > currentMonth41)

  useEffect(() => {
    setLoading(true)
    fetchRepairStats(year)
      .then(setData)
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }, [year])

  if (loading) return <Spin />
  if (!data)   return <Empty />

  // 欄位定義：key（值）、detailKey（明細陣列）、label、isPct
  const rows: { key: string; detailKey?: string; label: string; isPct?: boolean }[] = [
    { key: 'prev_uncompleted',           detailKey: 'prev_uncompleted_detail',     label: '① 上月累計未完成項目數' },
    { key: 'closed_from_prev',           detailKey: 'closed_from_prev_detail',     label: '② 上月未完成，本月結案數' },
    { key: 'cum_completion_rate',                                                   label: '③ 累計項目完成率（%）', isPct: true },
    { key: 'this_month_total',           detailKey: 'this_month_total_detail',     label: '④ 本月報修項目數' },
    { key: 'this_month_completed',       detailKey: 'this_month_completed_detail', label: '⑤ 本月報修項目完成數' },
    { key: 'this_month_uncompleted',                                                label: '⑥ 本月未完成數' },
    { key: 'this_month_completion_rate',                                            label: '⑦ 本月報修項目完成率（%）', isPct: true },
  ]

  return (
    <div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#1B3A5C', color: '#fff' }}>
              <th style={{ padding: '8px 12px', textAlign: 'left', minWidth: 220, position: 'sticky', left: 0, background: '#1B3A5C', zIndex: 1 }}>
                商場報修維護事項
              </th>
              {MONTHS.map(m => (
                <th key={m} style={{
                  padding: '8px 8px', textAlign: 'center', minWidth: 72,
                  background: m === focusMonth ? '#4BA8E8' : '#1B3A5C',
                  fontWeight: m === focusMonth ? 700 : 400,
                }}>
                  {m} 月
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={row.key} style={{ background: ri % 2 === 0 ? '#fff' : '#f8f9fb' }}>
                <td style={{
                  padding: '8px 12px', fontWeight: 500, color: '#1B3A5C',
                  borderBottom: '1px solid #eee', position: 'sticky', left: 0,
                  background: ri % 2 === 0 ? '#fff' : '#f8f9fb', zIndex: 1,
                }}>
                  {row.label}
                </td>
                {MONTHS.map(m => {
                  if (isFutureMonth(m)) {
                    return (
                      <td key={m} style={{
                        padding: '8px 8px', textAlign: 'center',
                        borderBottom: '1px solid #eee',
                        background: ri % 2 === 0 ? '#fff' : '#f8f9fb',
                        color: '#ccc',
                      }}>—</td>
                    )
                  }
                  const stat = data.months[m]
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  const val = stat ? (stat as any)[row.key] : null
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  const detail: RepairCase[] = (row.detailKey && stat) ? (stat as any)[row.detailKey] ?? [] : []
                  const canClick = !row.isPct && detail.length > 0
                  const display = val == null ? '-'
                    : row.isPct ? `${fmtDec(val as number)}%`
                    : fmt(val as number)
                  return (
                    <td key={m}
                      onClick={() => canClick && setModal({ title: `${m}月 ${row.label}`, cases: detail })}
                      style={{
                        padding: '8px 8px', textAlign: 'center',
                        borderBottom: '1px solid #eee',
                        background: m === focusMonth ? '#E6F7FF' : ri % 2 === 0 ? '#fff' : '#f8f9fb',
                        fontWeight: m === focusMonth ? 600 : 400,
                        cursor: canClick ? 'pointer' : 'default',
                        color: row.isPct && val != null
                          ? (val as number) >= 80 ? '#52C41A' : (val as number) >= 50 ? '#FAAD14' : '#FF4D4F'
                          : canClick ? '#1B3A5C' : undefined,
                        textDecoration: canClick ? 'underline dotted' : undefined,
                      }}>
                      {display}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 未完成事項說明區塊 */}
      <Card size="small" title="未完成事項說明（原因 / 待協助事項）" style={{ marginTop: 20 }}>
        <div style={{ color: '#999', fontSize: 12, padding: '4px 0' }}>
          本區塊供人工填寫說明，可依需要另行整合 Ragic 備註欄位。
        </div>
      </Card>

      <CaseListModal title={modal?.title ?? ''} cases={modal?.cases ?? []}
        open={!!modal} onClose={() => setModal(null)}
        extra={<Tag color="blue">共 {modal?.cases.length ?? 0} 筆</Tag>} />
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 4.2 結案時間統計
// ═════════════════════════════════════════════════════════════════════════════
function ClosingTimeTab({ year, month }: { year: number; month: number | null }) {
  const [data, setData]       = useState<ClosingTimeData | null>(null)
  const [loading, setLoading] = useState(false)

  const _now42 = new Date()
  const currentYear42  = _now42.getFullYear()
  const currentMonth42 = _now42.getMonth() + 1
  const isFutureMonth42 = (m: number) =>
    year > currentYear42 || (year === currentYear42 && m > currentMonth42)

  useEffect(() => {
    setLoading(true)
    fetchClosingStats(year, month ?? undefined)
      .then(setData)
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }, [year, month])

  if (loading) return <Spin />
  if (!data)   return <Empty />

  const renderBlock = (block: { closed_count: number; total_days: number; avg_days: number | null }, label: string) => (
    <Row gutter={16} style={{ marginBottom: 8 }}>
      <Col span={8}>
        <Statistic title="本月結案項目數" value={block.closed_count} />
      </Col>
      <Col span={8}>
        <Statistic title="結案天數總計" value={fmtDec(block.total_days, 1)} suffix="天" />
      </Col>
      <Col span={8}>
        <Statistic title="平均每項結案天數" value={block.avg_days != null ? fmtDec(block.avg_days, 2) : '-'} suffix="天" />
      </Col>
    </Row>
  )

  return (
    <div>
      {/* 小型 */}
      <Card
        title="商場小型報修結案時間統計（無費用或總工核可）"
        size="small"
        style={{ marginBottom: 16 }}
        headStyle={{ background: '#f0f4f8', fontWeight: 600 }}
      >
        {renderBlock(data.small, '小型')}
        <Divider style={{ margin: '12px 0' }} />
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#e6f0fa' }}>
                <th style={{ padding: '6px 10px', textAlign: 'left', minWidth: 120 }}>統計項目</th>
                {MONTHS.map(m => (
                  <th key={m} style={{
                    padding: '6px 8px', textAlign: 'center', minWidth: 56,
                    background: m === month ? '#bae7ff' : '#e6f0fa',
                    fontWeight: m === month ? 700 : 400,
                  }}>{m}月</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(['closed_count', 'total_days', 'avg_days'] as const).map((key, idx) => {
                const labels = ['本月結案項目數', '結案天數總計', '平均每項結案天數']
                return (
                  <tr key={key} style={{ background: idx % 2 === 0 ? '#fff' : '#f9f9f9' }}>
                    <td style={{ padding: '6px 10px', borderBottom: '1px solid #f0f0f0' }}>{labels[idx]}</td>
                    {MONTHS.map(m => {
                      if (isFutureMonth42(m)) {
                        return (
                          <td key={m} style={{
                            padding: '6px 8px', textAlign: 'center',
                            borderBottom: '1px solid #f0f0f0',
                            color: '#ccc',
                          }}>—</td>
                        )
                      }
                      const v = data.monthly[m]?.small?.[key]
                      return (
                        <td key={m} style={{
                          padding: '6px 8px', textAlign: 'center',
                          borderBottom: '1px solid #f0f0f0',
                          background: m === month ? '#e6f7ff' : undefined,
                        }}>
                          {v == null ? '-' : key === 'avg_days' ? fmtDec(v, 2) : key === 'total_days' ? fmtDec(v, 1) : v}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 中大型 */}
      <Card
        title="商場中大型報修結案時間統計（費用經店主管以上核可）"
        size="small"
        style={{ marginBottom: 16 }}
        headStyle={{ background: '#f0f4f8', fontWeight: 600 }}
      >
        {renderBlock(data.large, '中大型')}
        <Divider style={{ margin: '12px 0' }} />
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#faf0e6' }}>
                <th style={{ padding: '6px 10px', textAlign: 'left', minWidth: 120 }}>統計項目</th>
                {MONTHS.map(m => (
                  <th key={m} style={{
                    padding: '6px 8px', textAlign: 'center', minWidth: 56,
                    background: m === month ? '#ffd591' : '#faf0e6',
                    fontWeight: m === month ? 700 : 400,
                  }}>{m}月</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(['closed_count', 'total_days', 'avg_days'] as const).map((key, idx) => {
                const labels = ['本月結案項目數', '結案天數總計', '平均每項結案天數']
                return (
                  <tr key={key} style={{ background: idx % 2 === 0 ? '#fff' : '#f9f9f9' }}>
                    <td style={{ padding: '6px 10px', borderBottom: '1px solid #f0f0f0' }}>{labels[idx]}</td>
                    {MONTHS.map(m => {
                      if (isFutureMonth42(m)) {
                        return (
                          <td key={m} style={{
                            padding: '6px 8px', textAlign: 'center',
                            borderBottom: '1px solid #f0f0f0',
                            color: '#ccc',
                          }}>—</td>
                        )
                      }
                      const v = data.monthly[m]?.large?.[key]
                      return (
                        <td key={m} style={{
                          padding: '6px 8px', textAlign: 'center',
                          borderBottom: '1px solid #f0f0f0',
                          background: m === month ? '#fff7e6' : undefined,
                        }}>
                          {v == null ? '-' : key === 'avg_days' ? fmtDec(v, 2) : key === 'total_days' ? fmtDec(v, 1) : v}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <div style={{ marginTop: 8, padding: '10px 14px', background: '#fffbe6', borderRadius: 6, border: '1px solid #ffe58f' }}>
        <Text strong style={{ fontSize: 12 }}>分類說明：</Text>
        <Text style={{ fontSize: 12, color: '#666', marginLeft: 8 }}>{data.classification_note}</Text>
      </div>
      <div style={{ marginTop: 12, padding: '12px 16px', background: '#fffbe6', borderRadius: 6, border: '1px solid #ffe58f' }}>
        <Text strong>未完成事項說明（原因 / 待協助事項）</Text>
        <div style={{ marginTop: 8, color: '#666', fontSize: 13 }}>（可在此記錄本月未完成的原因說明與待協助事項）</div>
      </div>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 4.3 報修類型統計
// ═════════════════════════════════════════════════════════════════════════════
function RepairTypeTab({ year, month }: { year: number; month: number | null }) {
  const [data, setData]       = useState<TypeStatsData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchTypeStats(year, month ?? undefined)
      .then(setData)
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }, [year, month])

  if (loading) return <Spin />
  if (!data)   return <Empty />

  const focusM = data.focus_month

  return (
    <div>
      {/* 摘要列 */}
      {focusM && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999' }}>上月累計件數</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#1B3A5C' }}>
                {data.rows.reduce((s, r) => s + (r.monthly[focusM > 1 ? focusM - 1 : 12] || 0), 0)}
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999' }}>本月件數</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#4BA8E8' }}>
                {data.rows.reduce((s, r) => s + (r.monthly[focusM] || 0), 0)}
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999' }}>今年累計</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#52C41A' }}>
                {data.year_total}
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999' }}>類型數</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#FA8C16' }}>
                {data.rows.filter(r => r.row_total > 0).length}
              </div>
            </Card>
          </Col>
        </Row>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#1B3A5C', color: '#fff' }}>
              <th style={{ padding: '8px 12px', textAlign: 'left', minWidth: 70, position: 'sticky', left: 0, background: '#1B3A5C' }}>類別</th>
              <th style={{ padding: '8px 12px', textAlign: 'left', minWidth: 200 }}>MD內容</th>
              {MONTHS.map(m => (
                <th key={m} style={{
                  padding: '8px 6px', textAlign: 'center', minWidth: 44,
                  background: m === focusM ? '#4BA8E8' : '#1B3A5C',
                }}>
                  {m}月
                </th>
              ))}
              <th style={{ padding: '8px 8px', textAlign: 'center', minWidth: 54, background: '#2d5580' }}>合計</th>
              <th style={{ padding: '8px 8px', textAlign: 'center', minWidth: 60, background: '#2d5580' }}>今年累計%</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, rowIdx) => (
              <tr key={row.type} style={{ background: rowIdx % 2 === 0 ? '#fafafa' : '#fff' }}>
                <td style={{
                  padding: '6px 12px', fontWeight: 600, color: '#1B3A5C',
                  borderBottom: '1px solid #e8e8e8',
                  position: 'sticky', left: 0, background: rowIdx % 2 === 0 ? '#fafafa' : '#fff',
                }}>
                  {row.type}
                </td>
                <td style={{ padding: '6px 12px', color: '#666', borderBottom: '1px solid #e8e8e8', fontSize: 11 }}>
                  {row.example}
                </td>
                {MONTHS.map(m => {
                  const v = row.monthly[m] || 0
                  const isFocus = m === focusM
                  return (
                    <td key={m} style={{
                      padding: '6px 6px', textAlign: 'center',
                      borderBottom: '1px solid #e8e8e8',
                      background: isFocus ? '#e6f7ff' : undefined,
                      color: v > 0 ? '#1B3A5C' : '#ccc',
                      fontWeight: isFocus && v > 0 ? 700 : 400,
                    }}>
                      {v || '-'}
                    </td>
                  )
                })}
                <td style={{
                  padding: '6px 8px', textAlign: 'center', fontWeight: 700,
                  borderBottom: '1px solid #e8e8e8', color: '#1B3A5C',
                  background: '#f0f4f8',
                }}>
                  {row.row_total || '-'}
                </td>
                <td style={{
                  padding: '6px 8px', textAlign: 'center',
                  borderBottom: '1px solid #e8e8e8', color: '#52C41A',
                  background: '#f0f4f8',
                }}>
                  {row.row_total > 0 ? `${row.cum_pct}%` : '-'}
                </td>
              </tr>
            ))}
            {/* 合計行 */}
            <tr style={{ background: '#1B3A5C', color: '#fff', fontWeight: 700 }}>
              <td style={{ padding: '7px 12px', position: 'sticky', left: 0, background: '#1B3A5C' }}>合計</td>
              <td />
              {MONTHS.map(m => {
                const total = data.rows.reduce((s, r) => s + (r.monthly[m] || 0), 0)
                return (
                  <td key={m} style={{
                    padding: '7px 6px', textAlign: 'center',
                    background: m === focusM ? '#4BA8E8' : '#1B3A5C',
                  }}>
                    {total || '-'}
                  </td>
                )
              })}
              <td style={{ padding: '7px 8px', textAlign: 'center', background: '#2d5580' }}>{data.year_total}</td>
              <td style={{ padding: '7px 8px', textAlign: 'center', background: '#2d5580' }}>100%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 4.4 本月客房報修表
// ═════════════════════════════════════════════════════════════════════════════
function RoomRepairTab({ year, month }: { year: number; month: number | null }) {
  const [data, setData]           = useState<RoomRepairTableData | null>(null)
  const [loading, setLoading]     = useState(false)
  const [activeFloor, setFloor]   = useState<string | null>(null)
  const [drawerCase, setDrawerCase] = useState<RepairCase | null>(null)

  const effectiveMonth = month ?? new Date().getMonth() + 1

  useEffect(() => {
    setLoading(true)
    fetchRoomRepairTable(year, effectiveMonth)
      .then(d => { setData(d); setFloor(null) })
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }, [year, effectiveMonth])

  if (loading) return <Spin />
  if (!data)   return <Empty description="請選擇年月" />

  // 篩選樓層
  const filteredRows = activeFloor
    ? data.rows.filter(r => r.floor === activeFloor)
    : data.rows

  return (
    <div>
      {/* 樓層篩選 */}
      {data.floors_with_data.length > 0 && (
        <Space style={{ marginBottom: 12 }} wrap>
          <Text strong>樓層篩選：</Text>
          <Button
            size="small"
            type={activeFloor == null ? 'primary' : 'default'}
            onClick={() => setFloor(null)}
          >全部</Button>
          {data.floors_with_data.map(f => (
            <Button
              key={f} size="small"
              type={activeFloor === f ? 'primary' : 'default'}
              onClick={() => setFloor(f)}
            >
              {f}
            </Button>
          ))}
        </Space>
      )}

      <div style={{ marginBottom: 8, color: '#666', fontSize: 12 }}>
        共 {data.total_room_cases} 筆客房報修（{year} 年 {effectiveMonth} 月）
      </div>

      {filteredRows.length === 0 ? (
        <Empty description="本月無客房報修資料" />
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', fontSize: 11, minWidth: 900 }}>
            <thead>
              <tr style={{ background: '#1B3A5C', color: '#fff' }}>
                <th style={{ padding: '6px 10px', minWidth: 60, position: 'sticky', left: 0, background: '#1B3A5C' }}>樓層</th>
                <th style={{ padding: '6px 10px', minWidth: 60, position: 'sticky', left: 60, background: '#1B3A5C' }}>房號</th>
                {data.categories.map(cat => (
                  <th key={cat} style={{ padding: '6px 8px', minWidth: 70, textAlign: 'center' }}>{cat}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((row, rIdx) => (
                <tr key={row.room_no} style={{ background: rIdx % 2 === 0 ? '#fafafa' : '#fff' }}>
                  <td style={{
                    padding: '5px 10px', fontWeight: 600, color: '#4BA8E8',
                    borderBottom: '1px solid #f0f0f0',
                    position: 'sticky', left: 0, background: rIdx % 2 === 0 ? '#fafafa' : '#fff',
                  }}>
                    {row.floor}
                  </td>
                  <td style={{
                    padding: '5px 10px', fontWeight: 600,
                    borderBottom: '1px solid #f0f0f0',
                    position: 'sticky', left: 60, background: rIdx % 2 === 0 ? '#fafafa' : '#fff',
                  }}>
                    {row.room_no}
                  </td>
                  {data.categories.map(cat => {
                    const entries = (row.categories[cat] || [])
                    return (
                      <td key={cat} style={{
                        padding: '4px 6px', borderBottom: '1px solid #f0f0f0',
                        verticalAlign: 'top', maxWidth: 120,
                        background: entries.length > 0 ? '#fff7e6' : undefined,
                      }}>
                        {entries.length === 0 ? null : entries.length === 1 ? (
                          <Tooltip title={`${entries[0].title} [${entries[0].status}]`}>
                            <div style={{
                              fontSize: 10, color: '#1B3A5C', cursor: 'pointer',
                              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                            }}
                              onClick={() => setDrawerCase(entries[0] as RepairCase)}>
                              {entries[0].title}
                            </div>
                          </Tooltip>
                        ) : (
                          <Tooltip title={entries.map(e => `${e.title} [${e.status}]`).join('\n')}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                              {entries.map((e, idx) => (
                                <div key={e.ragic_id ?? idx}
                                  onClick={() => setDrawerCase(e as RepairCase)}
                                  style={{
                                    fontSize: 10, color: '#FA8C16', cursor: 'pointer',
                                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                    padding: '1px 0',
                                    borderBottom: idx < entries.length - 1 ? '1px solid #ffe0a0' : undefined,
                                  }}>
                                  {idx + 1}. {e.title}
                                </div>
                              ))}
                            </div>
                          </Tooltip>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.unknown_room_cases.length > 0 && (
        <div style={{ marginTop: 16, padding: '12px 16px', background: '#fff5f5', borderRadius: 6, border: '1px solid #ffccc7' }}>
          <Text strong style={{ color: '#cf1322' }}>未判定房號案件（{data.unknown_room_cases.length} 筆）</Text>
          <div style={{ marginTop: 8 }}>
            {data.unknown_room_cases.map(c => (
              <Tag key={c.ragic_id}
                onClick={() => setDrawerCase(c)}
                style={{ cursor: 'pointer', marginBottom: 4 }}>
                {c.title || c.case_no}
              </Tag>
            ))}
          </div>
        </div>
      )}

      <CaseDetailDrawer caseData={drawerCase} onClose={() => setDrawerCase(null)} />
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 金額統計
// ═════════════════════════════════════════════════════════════════════════════
const FEE_DEFS_DAZHI = [
  { key: 'outsource_fee'   as const, label: '委外費用', color: '#1890ff' },
  { key: 'maintenance_fee' as const, label: '維修費用', color: '#52C41A' },
  { key: 'deduction_fee'   as const, label: '扣款費用', color: '#FF4D4F' },
]
const MONTH_NUMS = [1,2,3,4,5,6,7,8,9,10,11,12]

function FeeStatsTab({ year }: { year: number }) {
  const [data,    setData]    = useState<FeeStatsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)
  const [drilldown, setDrilldown] = useState<{
    feeKey: typeof FEE_DEFS_DAZHI[number]['key']
    month: number
    feeLabel: string
    color: string
  } | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const d = await fetchFeeStats(year)
      setData(d)
    } catch (e: unknown) {
      setError((e as Error).message || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [year])

  useEffect(() => { load() }, [load])

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" tip="載入中..." /></div>
  if (error)   return <Alert type="error" message={`載入失敗：${error}`} showIcon />
  if (!data)   return <Empty description="無資料" />

  type RowData = {
    key:   string
    label: string
    color: string
    isTotal: boolean
    [month: number]: number
    annual: number
  }

  const tableData: RowData[] = [
    ...FEE_DEFS_DAZHI.map(fd => ({
      key:     fd.key,
      label:   fd.label,
      color:   fd.color,
      isTotal: false,
      ...Object.fromEntries(MONTH_NUMS.map(m => [m, (data.monthly_totals[m] as unknown as Record<string, number>)?.[fd.key] ?? 0])),
      annual: (data.fee_totals as unknown as Record<string, number>)[fd.key] ?? 0,
    } as RowData)),
    {
      key:     'month_total',
      label:   '月份小計',
      color:   '#1B3A5C',
      isTotal: true,
      ...Object.fromEntries(MONTH_NUMS.map(m => [m, data.month_totals[m] ?? 0])),
      annual: data.grand_total,
    } as RowData,
  ]

  const cellStyle = (val: number, color: string, clickable: boolean): React.CSSProperties => ({
    textAlign: 'right',
    cursor: clickable && val > 0 ? 'pointer' : 'default',
    color:  clickable && val > 0 ? color : val === 0 ? '#ccc' : '#1B3A5C',
    fontWeight: clickable && val > 0 ? 600 : 400,
    transition: 'color .15s',
  })

  const monthColumns = MONTH_NUMS.map(m => ({
    title: `${m}月`,
    dataIndex: m,
    key: `m${m}`,
    width: 90,
    align: 'right' as const,
    render: (val: number, row: RowData) => {
      if (row.isTotal) {
        return <span style={{ color: '#1B3A5C', fontWeight: 700 }}>{val > 0 ? fmtMoney(val) : '-'}</span>
      }
      if (val <= 0) return <span style={{ color: '#ddd' }}>-</span>
      const fd = FEE_DEFS_DAZHI.find(f => f.key === row.key)!
      return (
        <span
          style={cellStyle(val, fd.color, true)}
          onClick={() => setDrilldown({ feeKey: fd.key, month: m, feeLabel: fd.label, color: fd.color })}
        >
          {fmtMoney(val)}
        </span>
      )
    },
  }))

  const columns = [
    {
      title: '費用項目',
      dataIndex: 'label',
      key: 'label',
      fixed: 'left' as const,
      width: 100,
      render: (label: string, row: RowData) => (
        <span style={{ fontWeight: row.isTotal ? 700 : 600, color: row.color }}>
          {label}
        </span>
      ),
    },
    ...monthColumns,
    {
      title: '全年小計',
      dataIndex: 'annual',
      key: 'annual',
      fixed: 'right' as const,
      width: 110,
      align: 'right' as const,
      render: (val: number, row: RowData) => (
        <strong style={{ color: row.color, fontSize: 13 }}>{fmtMoney(val)}</strong>
      ),
    },
  ]

  const drillCases: RepairCase[] = drilldown
    ? (data.monthly_detail[`${drilldown.month}_${drilldown.feeKey}`] ?? [])
    : []

  return (
    <div>
      <Table
        dataSource={tableData}
        columns={columns}
        rowKey="key"
        size="small"
        bordered
        pagination={false}
        scroll={{ x: 1400 }}
        rowClassName={(row: RowData) => row.isTotal ? 'fee-total-row' : ''}
        style={{ marginBottom: 16 }}
        rowHoverable={false}
        onHeaderRow={() => ({ style: { background: '#1B3A5C', color: '#fff' } })}
      />

      {/* 費用明細 Modal */}
      <Modal
        title={
          <span>
            <DollarOutlined style={{ color: drilldown?.color, marginRight: 8 }} />
            <span style={{ color: drilldown?.color }}>{drilldown?.feeLabel}</span>
            <span style={{ color: '#888', fontWeight: 400 }}>
              {' '}— {year} 年 {drilldown?.month} 月 明細
            </span>
          </span>
        }
        open={drilldown != null}
        onCancel={() => setDrilldown(null)}
        footer={<Button onClick={() => setDrilldown(null)}>關閉</Button>}
        width={800}
      >
        {drilldown && (
          <>
            <div style={{ marginBottom: 10 }}>
              <Tag color="blue">共 {drillCases.length} 筆</Tag>
              <Tag style={{ background: (drilldown.color) + '15', borderColor: drilldown.color, color: drilldown.color }}>
                合計：{fmtMoney((data.monthly_totals[drilldown.month] as unknown as Record<string, number>)?.[drilldown.feeKey] ?? 0)}
              </Tag>
            </div>
            {drillCases.length === 0
              ? <Empty description="本月無此費用資料" />
              : (
                <Table
                  size="small"
                  dataSource={drillCases}
                  rowKey="ragic_id"
                  pagination={false}
                  columns={[
                    { title: '報修編號', dataIndex: 'case_no',    width: 120 },
                    { title: '標題',     dataIndex: 'title',      width: 180, ellipsis: true },
                    { title: '樓層',     dataIndex: 'floor',      width: 70 },
                    { title: '日期',     dataIndex: 'occurred_at',width: 110 },
                    { title: '狀態',     dataIndex: 'status',     width: 90,
                      render: (s: string) => statusTag(s) },
                    {
                      title: drilldown.feeLabel,
                      dataIndex: drilldown.feeKey,
                      width: 110,
                      align: 'right' as const,
                      render: (v: number) => (
                        <strong style={{ color: drilldown.color }}>{fmtMoney(v)}</strong>
                      ),
                    },
                  ]}
                />
              )
            }
          </>
        )}
      </Modal>

      <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
        💡 點擊有金額的格子可查看該月該費用類型的案件明細
      </div>
      <div style={{ color: '#aaa', fontSize: 11, marginTop: 4 }}>
        ℹ️ 大直工務部目前 Ragic 無「委外費用」/「維修費用」/「扣款費用」欄位，待 Ragic 補上後數字將自動顯示。
      </div>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 大直工務部（明細資料）
// ═════════════════════════════════════════════════════════════════════════════
function DetailTab({
  year, month, years,
}: { year: number; month: number | null; years: number[] }) {
  const [filterOpts, setFilterOpts] = useState<FilterOptions>({ repair_types: [], floors: [], statuses: [] })
  const [result, setResult]         = useState<DetailResult | null>(null)
  const [loading, setLoading]       = useState(false)
  const [drawerCase, setDrawerCase] = useState<RepairCase | null>(null)

  // 搜尋條件
  const [qYear,   setQYear]   = useState<number | undefined>(year || undefined)
  const [qMonth,  setQMonth]  = useState<number | undefined>(month ?? undefined)
  const [qType,   setQType]   = useState<string | undefined>()
  const [qFloor,  setQFloor]  = useState<string | undefined>()
  const [qStatus, setQStatus] = useState<string | undefined>()
  const [qKw,     setQKw]     = useState<string>('')
  const [page,    setPage]    = useState(1)
  const pageSize = 50

  useEffect(() => {
    fetchFilterOptions().then(setFilterOpts).catch(() => {})
  }, [])

  const doQuery = useCallback((pg = 1) => {
    setLoading(true)
    setPage(pg)
    fetchDetail({
      year: qYear, month: qMonth,
      repair_type: qType, floor: qFloor, status: qStatus,
      keyword: qKw || undefined,
      page: pg, page_size: pageSize,
      sort_by: 'occurred_at', sort_desc: true,
    })
      .then(setResult)
      .catch(() => message.error('查詢失敗'))
      .finally(() => setLoading(false))
  }, [qYear, qMonth, qType, qFloor, qStatus, qKw])

  useEffect(() => { doQuery(1) }, [doQuery])

  const columns: ColumnsType<RepairCase> = [
    { title: '報修編號', dataIndex: 'case_no', width: 110, ellipsis: true,
      render: (v, row) => <a onClick={() => setDrawerCase(row)} style={{ color: '#1B3A5C' }}>{v || row.ragic_id}</a> },
    { title: '標題', dataIndex: 'title', ellipsis: true, minWidth: 180,
      render: (v, row) => <a onClick={() => setDrawerCase(row)} style={{ color: '#333' }}>{v || '-'}</a> },
    { title: '類型', dataIndex: 'repair_type', width: 80 },
    { title: '樓層', dataIndex: 'floor', width: 70, ellipsis: true },
    { title: '報修人', dataIndex: 'reporter_name', width: 80, ellipsis: true },
    { title: '發生時間', dataIndex: 'occurred_at', width: 130, sorter: true },
    { title: '負責單位', dataIndex: 'responsible_unit', width: 80, ellipsis: true },
    { title: '工時(hr)', dataIndex: 'work_hours', width: 70, align: 'right', render: (v: number) => fmtDec(v, 2) },
    {
      title: '處理狀況', dataIndex: 'status', width: 90,
      render: (v: string) => statusTag(v),
    },
    {
      title: '費用', dataIndex: 'total_fee', width: 90, align: 'right',
      render: (v: number) => v > 0 ? <span style={{ color: '#722ED1' }}>{fmtMoney(v)}</span> : '-',
      sorter: true,
    },
    { title: '結案天數', dataIndex: 'close_days', width: 80, align: 'right',
      render: (v: number | null) => v != null ? `${fmtDec(v, 1)}天` : '-', sorter: true },
  ]

  const exportUrl = buildExportUrl({ year: qYear, month: qMonth, repair_type: qType, floor: qFloor, status: qStatus, keyword: qKw || undefined })

  return (
    <div>
      {/* 搜尋列 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Row gutter={[8, 8]} align="middle">
          <Col xs={12} sm={6} md={4}>
            <Select value={qYear} placeholder="年度" allowClear style={{ width: '100%' }} onChange={setQYear}>
              {years.map(y => <Option key={y} value={y}>{y} 年</Option>)}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select value={qMonth} placeholder="月份" allowClear style={{ width: '100%' }} onChange={setQMonth}>
              {MONTHS.map(m => <Option key={m} value={m}>{m} 月</Option>)}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select value={qType} placeholder="報修類型" allowClear style={{ width: '100%' }} onChange={setQType}>
              {filterOpts.repair_types.map(t => <Option key={t} value={t}>{t}</Option>)}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select value={qFloor} placeholder="樓層" allowClear style={{ width: '100%' }} onChange={setQFloor}>
              {filterOpts.floors.map(f => <Option key={f} value={f}>{f}</Option>)}
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Select value={qStatus} placeholder="處理狀況" allowClear style={{ width: '100%' }} onChange={setQStatus}>
              {filterOpts.statuses.map(s => <Option key={s} value={s}>{s}</Option>)}
            </Select>
          </Col>
          <Col xs={12} sm={8} md={6}>
            <input
              value={qKw}
              onChange={e => setQKw(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doQuery(1)}
              placeholder="關鍵字（編號/標題/報修人）"
              style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }}
            />
          </Col>
          <Col xs={24} sm={6} md={4}>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={() => doQuery(1)}>搜尋</Button>
              <Button onClick={() => { setQYear(undefined); setQMonth(undefined); setQType(undefined); setQFloor(undefined); setQStatus(undefined); setQKw('') }}>清除</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 操作列 */}
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text style={{ fontSize: 13, color: '#666' }}>
          共 {result?.total ?? 0} 筆資料
        </Text>
        <Button
          icon={<DownloadOutlined />} size="small"
          onClick={() => window.open(exportUrl, '_blank')}
        >
          匯出 Excel
        </Button>
      </div>

      <Table
        dataSource={result?.items || []}
        columns={columns}
        rowKey="ragic_id"
        loading={loading}
        size="small"
        scroll={{ x: 1200 }}
        pagination={{
          current: page,
          pageSize,
          total: result?.total || 0,
          showSizeChanger: false,
          showTotal: (t) => `共 ${t} 筆`,
          onChange: (p) => doQuery(p),
        }}
        onRow={(row) => ({
          onClick: () => setDrawerCase(row),
          style: { cursor: 'pointer' },
        })}
        rowClassName={(row) => row.is_completed ? '' : 'ant-table-row-uncompleted'}
      />

      {/* 點擊列詳情 Drawer */}
      <Drawer
        title={
          <Space>
            <ToolOutlined style={{ color: '#1B3A5C' }} />
            <span>報修詳情：{drawerCase?.case_no || drawerCase?.ragic_id}</span>
          </Space>
        }
        open={!!drawerCase}
        onClose={() => setDrawerCase(null)}
        width={520}
        destroyOnClose
      >
        {drawerCase && (
          <Descriptions column={1} bordered size="small" labelStyle={{ width: 120, fontWeight: 500, background: '#f8f9fb' }}>
            <Descriptions.Item label="報修編號">{drawerCase.case_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="標題"><strong>{drawerCase.title || '-'}</strong></Descriptions.Item>
            <Descriptions.Item label="報修人姓名">{drawerCase.reporter_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="報修類型"><Tag>{drawerCase.repair_type || '-'}</Tag></Descriptions.Item>
            <Descriptions.Item label="發生樓層">{drawerCase.floor || '-'}</Descriptions.Item>
            <Descriptions.Item label="發生時間">{drawerCase.occurred_at || '-'}</Descriptions.Item>
            <Descriptions.Item label="負責單位">{drawerCase.responsible_unit || '-'}</Descriptions.Item>
            <Descriptions.Item label="花費工時">{drawerCase.work_hours > 0 ? `${fmtDec(drawerCase.work_hours, 2)} hr` : '-'}</Descriptions.Item>
            <Descriptions.Item label="處理狀況">{statusTag(drawerCase.status)}</Descriptions.Item>
            <Descriptions.Item label="委外費用">{fmtMoney(drawerCase.outsource_fee)}</Descriptions.Item>
            <Descriptions.Item label="維修費用">{fmtMoney(drawerCase.maintenance_fee)}</Descriptions.Item>
            <Descriptions.Item label="總費用"><strong>{fmtMoney(drawerCase.total_fee)}</strong></Descriptions.Item>
            <Descriptions.Item label="驗收者">{drawerCase.acceptor || '-'}</Descriptions.Item>
            <Descriptions.Item label="驗收">{drawerCase.accept_status || '-'}</Descriptions.Item>
            <Descriptions.Item label="結案人">{drawerCase.closer || '-'}</Descriptions.Item>
            <Descriptions.Item label="結案時間">{drawerCase.completed_at || '-'}</Descriptions.Item>
            <Descriptions.Item label="結案天數">
              {drawerCase.close_days != null ? `${fmtDec(drawerCase.close_days, 1)} 天` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="扣款事項">{drawerCase.deduction_item || '-'}</Descriptions.Item>
            <Descriptions.Item label="扣款費用">{fmtMoney(drawerCase.deduction_fee)}</Descriptions.Item>
            <Descriptions.Item label="財務備註">{drawerCase.finance_note || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// 主頁元件
// ═════════════════════════════════════════════════════════════════════════════
export default function DazhiRepairPage() {
  const now = new Date()
  const [years, setYears]   = useState<number[]>([now.getFullYear()])
  const [year,  setYear]    = useState(now.getFullYear())
  const [month, setMonth]   = useState<number | null>(now.getMonth() + 1)
  const [activeTab, setTab] = useState('dashboard')

  // 已套用到各 Tab 的查詢參數（點查詢按鈕後才更新）
  const [appliedYear,  setAppliedYear]  = useState(now.getFullYear())
  const [appliedMonth, setAppliedMonth] = useState<number | null>(now.getMonth() + 1)

  // 同步 Ragic 診斷
  const [syncing,     setSyncing]    = useState(false)
  const [syncResult,  setSyncResult] = useState<SyncResult | null>(null)
  const [syncModalOpen, setSyncModal] = useState(false)

  // 連線 Ping 測試
  const [pinging,    setPinging]   = useState(false)
  const [pingResult, setPingResult] = useState<PingResult | null>(null)
  const [pingModalOpen, setPingModal] = useState(false)

  useEffect(() => {
    fetchYears()
      .then(r => {
        setYears(r.years)
        if (r.years.length > 0) {
          setYear(r.years[0])
          setAppliedYear(r.years[0])
        }
      })
      .catch(() => {})
  }, [])

  const handleQuery = () => {
    setAppliedYear(year)
    setAppliedMonth(month)
  }

  const handleReset = () => {
    setYear(now.getFullYear())
    setMonth(now.getMonth() + 1)
    setAppliedYear(now.getFullYear())
    setAppliedMonth(now.getMonth() + 1)
  }

  const handlePing = async () => {
    setPinging(true)
    try {
      const result = await fetchPing()
      setPingResult(result)
      setPingModal(true)
    } catch (e: unknown) {
      message.error(`Ping 失敗：${(e as Error).message}`)
    } finally {
      setPinging(false)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      const result = await fetchSync()
      setSyncResult(result)
      setSyncModal(true)
      // 同步後更新年份清單
      fetchYears()
        .then(r => { if (r.years.length > 0) setYears(r.years) })
        .catch(() => {})
    } catch (e: unknown) {
      message.error(`同步失敗：${(e as Error).message || '請確認後端服務是否正常'}`)
    } finally {
      setSyncing(false)
    }
  }

  const tabItems = [
    {
      key: 'dashboard',
      label: <><DashboardOutlined /> Dashboard</>,
      children: (
        <DashboardTab
          year={appliedYear}
          month={appliedMonth ?? now.getMonth() + 1}
        />
      ),
    },
    {
      key: 'repair-stats',
      label: '4.1 報修',
      children: (
        <RepairStatsTab
          year={appliedYear}
          focusMonth={appliedMonth}
        />
      ),
    },
    {
      key: 'closing-time',
      label: '4.2 結案時間',
      children: (
        <ClosingTimeTab
          year={appliedYear}
          month={appliedMonth}
        />
      ),
    },
    {
      key: 'repair-type',
      label: '4.3 報修類型',
      children: (
        <RepairTypeTab
          year={appliedYear}
          month={appliedMonth}
        />
      ),
    },
    {
      key: 'room-repair',
      label: '4.4 本月客房報修表',
      children: (
        <RoomRepairTab
          year={appliedYear}
          month={appliedMonth}
        />
      ),
    },
    {
      key: 'fee-stats',
      label: '金額統計',
      children: <FeeStatsTab year={appliedYear} />,
    },
    {
      key: 'detail',
      label: <><FileTextOutlined /> 大直工務部</>,
      children: (
        <DetailTab
          year={appliedYear}
          month={appliedMonth}
          years={years}
        />
      ),
    },
  ]

  return (
    <div style={{ padding: '0 0 24px' }}>
      {/* 麵包屑 */}
      <Breadcrumb style={{ marginBottom: 12 }}>
        <Breadcrumb.Item><HomeOutlined /></Breadcrumb.Item>
        <Breadcrumb.Item>大直工務部</Breadcrumb.Item>
        <Breadcrumb.Item>Dashboard</Breadcrumb.Item>
      </Breadcrumb>

      {/* 頁面標題 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BuildOutlined style={{ fontSize: 22, color: '#1B3A5C' }} />
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>大直工務部</Title>
          <Tag color="blue">{appliedYear} 年{appliedMonth ? ` ${appliedMonth} 月` : ' 全年'}</Tag>
        </div>
        <Space>
          <Button
            icon={<ApiOutlined />}
            loading={pinging}
            onClick={handlePing}
            style={{ borderColor: '#4BA8E8', color: '#4BA8E8' }}
          >
            連線測試
          </Button>
          <Button
            icon={<SyncOutlined spin={syncing} />}
            loading={syncing}
            onClick={handleSync}
            style={{
              background: 'linear-gradient(135deg, #667eea, #764ba2)',
              border: 'none', color: '#fff',
            }}
          >
            同步 Ragic
          </Button>
        </Space>
      </div>

      {/* 查詢列 */}
      <QueryBar
        year={year}
        month={month}
        years={years}
        onYearChange={setYear}
        onMonthChange={setMonth}
        onQuery={handleQuery}
        onReset={handleReset}
      />

      {/* Tab 區 */}
      <Card bodyStyle={{ padding: '16px 16px' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setTab}
          items={tabItems}
          type="card"
          size="small"
        />
      </Card>

      {/* 連線 Ping 測試 Modal */}
      <Modal
        title={<Space><ApiOutlined style={{ color: '#4BA8E8' }} /><span>Ragic 連線測試結果</span></Space>}
        open={pingModalOpen}
        onCancel={() => setPingModal(false)}
        footer={<Button type="primary" onClick={() => setPingModal(false)}>關閉</Button>}
        width={640}
      >
        {pingResult && (
          <div style={{ fontSize: 13 }}>
            <div style={{ marginBottom: 10, background: '#f5f5f5', padding: '6px 10px', borderRadius: 4, fontSize: 11 }}>
              <span style={{ color: '#999' }}>測試 URL：</span>
              <span style={{ color: '#1B3A5C' }}>{pingResult.ragic_base_url}</span>
              {'  '}
              <Tag color="blue">PAGEID={pingResult.pageid}</Tag>
              <Tag color="default">API Key: {pingResult.api_key_prefix}</Tag>
            </div>
            {pingResult.results.map((r, i) => {
              const isOk = !r.error && r.status_code === 200 && (r.record_count ?? 0) > 0
              const hasError = !!r.error
              const badStatus = !r.error && r.status_code !== 200
              return (
                <Card key={i} size="small" style={{
                  marginBottom: 10,
                  borderLeft: `4px solid ${isOk ? '#52C41A' : hasError ? '#FF4D4F' : '#FAAD14'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <Space>
                      <Tag color={r.test === 'with_pageid' ? 'purple' : 'default'}>
                        {r.test === 'with_pageid' ? `帶 PAGEID=${pingResult.pageid}` : '不帶 PAGEID'}
                      </Tag>
                      {r.status_code && <Tag color={r.status_code === 200 ? 'green' : 'red'}>HTTP {r.status_code}</Tag>}
                      <span style={{ color: '#999', fontSize: 11 }}>{r.elapsed_ms} ms</span>
                    </Space>
                    {isOk && <Tag color="success">✓ 正常（{r.record_count} 筆）</Tag>}
                    {hasError && <Tag color="error">✗ 失敗</Tag>}
                    {badStatus && <Tag color="warning">⚠ 狀態異常</Tag>}
                  </div>
                  {r.error ? (
                    <div>
                      <div style={{ color: '#FF4D4F', marginBottom: 4 }}>{r.error}</div>
                      {r.tip && <Alert type="warning" message={r.tip} showIcon style={{ fontSize: 11 }} />}
                    </div>
                  ) : (
                    <div>
                      <div style={{ color: '#666', fontSize: 11, marginBottom: 6 }}>
                        body_type: <code>{r.body_type}</code>　record_count: <strong>{r.record_count}</strong>
                        {r.first_record_id && <span>　record_id: <code>{r.first_record_id}</code></span>}
                      </div>
                      {r.record_count === 0 && !r.error && (
                        <Alert type="warning" showIcon style={{ fontSize: 11, marginBottom: 6 }}
                          message="Ragic 回應 200 但沒有資料。可能是此 Sheet/PAGEID 沒有資料，或 API Key 無讀取權限（Ragic 有時會用空 200 代替 403）" />
                      )}
                      {/* 第一筆原始 JSON — 供欄位比對 */}
                      {r.first_record_raw && Object.keys(r.first_record_raw).length > 0 && (
                        <div>
                          <div style={{ fontWeight: 600, marginBottom: 4, color: '#1B3A5C', fontSize: 12 }}>
                            第一筆原始欄位（Record #{r.first_record_id}）
                          </div>
                          <div style={{
                            background: '#f8f9fb', border: '1px solid #e8e8e8', borderRadius: 4,
                            padding: 8, maxHeight: 320, overflowY: 'auto',
                          }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                              <thead>
                                <tr style={{ background: '#1B3A5C', color: '#fff' }}>
                                  <th style={{ padding: '4px 8px', textAlign: 'left', width: '35%' }}>欄位名稱 (key)</th>
                                  <th style={{ padding: '4px 8px', textAlign: 'left' }}>欄位值 (value)</th>
                                </tr>
                              </thead>
                              <tbody>
                                {Object.entries(r.first_record_raw).map(([k, v], idx) => {
                                  const valStr = v === null ? 'null'
                                    : typeof v === 'object' ? JSON.stringify(v)
                                    : String(v)
                                  const isEmpty = valStr === '' || valStr === 'null'
                                  return (
                                    <tr key={k} style={{ background: idx % 2 === 0 ? '#fff' : '#fafafa' }}>
                                      <td style={{
                                        padding: '4px 8px', borderBottom: '1px solid #f0f0f0',
                                        fontWeight: 600, color: '#1B3A5C', whiteSpace: 'nowrap',
                                      }}>
                                        {k}
                                      </td>
                                      <td style={{
                                        padding: '4px 8px', borderBottom: '1px solid #f0f0f0',
                                        color: isEmpty ? '#ccc' : '#333',
                                        wordBreak: 'break-all',
                                      }}>
                                        {isEmpty ? '（空）' : valStr}
                                      </td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              )
            })}
            <Alert type="info" showIcon style={{ fontSize: 11, marginTop: 8 }}
              message="診斷說明：「帶 PAGEID」有資料 = 正常。「帶 PAGEID」無資料但「不帶 PAGEID」有資料 = PAGEID 設定錯誤。兩者都 timeout = 後端無法連到 Ragic。兩者都 0 筆 = API Key 無權限。" />
          </div>
        )}
      </Modal>

      {/* 同步診斷 Modal */}
      <Modal
        title={
          <Space>
            <ApiOutlined style={{ color: '#667eea' }} />
            <span>Ragic 同步診斷結果</span>
          </Space>
        }
        open={syncModalOpen}
        onCancel={() => setSyncModal(false)}
        footer={<Button onClick={() => setSyncModal(false)}>關閉</Button>}
        width={680}
      >
        {syncResult && (
          <div>
            <Space wrap style={{ marginBottom: 12 }}>
              <Tag color="blue" style={{ fontSize: 13, padding: '2px 10px' }}>總筆數：{syncResult.total_parsed}</Tag>
              <Tag color="orange" style={{ fontSize: 13, padding: '2px 10px' }}>無日期：{syncResult.no_date_count}</Tag>
            </Space>

            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 12 }}>年份分佈</Text>
              <div style={{ marginTop: 6 }}>
                {Object.entries(syncResult.year_distribution).map(([yr, cnt]) => (
                  <Tag key={yr} color="geekblue" style={{ marginBottom: 4 }}>{yr} 年：{cnt} 筆</Tag>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 12 }}>
              <Text strong style={{ fontSize: 12 }}>最近 3 筆</Text>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', marginTop: 6 }}>
                <thead>
                  <tr style={{ background: '#1B3A5C', color: '#fff' }}>
                    <th style={{ padding: '4px 8px', textAlign: 'left' }}>ID</th>
                    <th style={{ padding: '4px 8px', textAlign: 'left' }}>編號</th>
                    <th style={{ padding: '4px 8px', textAlign: 'left' }}>標題</th>
                    <th style={{ padding: '4px 8px', textAlign: 'left' }}>日期</th>
                    <th style={{ padding: '4px 8px', textAlign: 'left' }}>狀態</th>
                  </tr>
                </thead>
                <tbody>
                  {syncResult.recent_samples.map((s, i) => (
                    <tr key={i} style={{ background: i % 2 === 0 ? '#fafafa' : '#fff' }}>
                      <td style={{ padding: '3px 8px', borderBottom: '1px solid #f0f0f0', fontFamily: 'monospace', fontSize: 11 }}>{s.ragic_id}</td>
                      <td style={{ padding: '3px 8px', borderBottom: '1px solid #f0f0f0' }}>{s.case_no}</td>
                      <td style={{ padding: '3px 8px', borderBottom: '1px solid #f0f0f0' }}>{s.title}</td>
                      <td style={{ padding: '3px 8px', borderBottom: '1px solid #f0f0f0' }}>{s.occurred_at}</td>
                      <td style={{ padding: '3px 8px', borderBottom: '1px solid #f0f0f0' }}>
                        <Tag color="blue" style={{ fontSize: 11 }}>{s.status}</Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div>
              <Text strong style={{ fontSize: 12 }}>Ragic 欄位清單</Text>
              <div style={{ marginTop: 6, maxHeight: 150, overflowY: 'auto' }}>
                {syncResult.field_names.map((f, i) => (
                  <Tag key={i} style={{ marginBottom: 4, fontFamily: 'monospace', fontSize: 11 }}>{f}</Tag>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 12, background: '#f5f5f5', borderRadius: 6, padding: '6px 10px', fontFamily: 'monospace', fontSize: 11 }}>
              🔗 {syncResult.ragic_url}
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
