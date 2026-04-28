/**
 * 樂群工務報修 — 主模組頁面
 *
 * 包含 6 個 Tab：
 *   Dashboard | 4.1 報修 | 4.2 結案時間 | 4.3 報修類型 | 4.4 本月客房報修表 | 春大直-報修清單總表
 *
 * 查詢條件（年/月）置於頁面頂部，各 Tab 共享。
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Statistic, Table, Tag, Button, Space,
  Typography, Breadcrumb, Select, Spin, Alert, Tabs, Modal,
  Tooltip, Badge, Drawer, Descriptions, message,
  Empty, Divider, Progress, Image,
} from 'antd'
import {
  HomeOutlined, ReloadOutlined, ToolOutlined,
  CheckCircleOutlined, ClockCircleOutlined, ExclamationCircleOutlined,
  DashboardOutlined, FileTextOutlined, DownloadOutlined,
  WarningOutlined, DollarOutlined, SearchOutlined,
  SyncOutlined, ApiOutlined, QuestionCircleOutlined,
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
  fetchYears, fetchFilterOptions, buildExportUrl,
  fetchSync, fetchPing, fetchFeeStats, fetchCaseImages,
} from '@/api/luqunRepair'
import type { SyncResult, PingResult, SyncFeeTotals } from '@/api/luqunRepair'
import type {
  DashboardData, RepairStatsData, ClosingTimeData, TypeStatsData,
  RoomRepairTableData, DetailResult, FilterOptions, RepairCase,
} from '@/types/luqunRepair'
import { NAV_GROUP } from '@/constants/navLabels'
import { LUQUN_KPI_DESC } from '@/constants/kpiDesc/luqunRepair'

const { Title, Text } = Typography
const { Option } = Select

// ── 常數 ──────────────────────────────────────────────────────────────────────
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)
const STATUS_COLOR: Record<string, string> = {
  '已驗收': '#52C41A', '已結案': '#52C41A', '結案': '#52C41A',
  '完修': '#52C41A', '已完成': '#52C41A', '完成': '#52C41A',
  '處理中': '#1890FF', '待維修': '#FAAD14', '待驗收': '#FAAD14',
  '待協調': '#FF7A45', '待排除': '#FF4D4F',
}
const STATUS_TAG_COLOR: Record<string, string> = {
  '已驗收': 'success', '已結案': 'success', '結案': 'success',
  '完修': 'success', '已完成': 'success', '完成': 'success',
  '處理中': 'processing', '待維修': 'warning', '待驗收': 'warning',
  '待協調': 'orange', '待排除': 'error', default: 'default',
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
  { title: '扣款專櫃', dataIndex: 'deduction_counter_name', width: 100,
    render: (v: string) => v ? <Tag color="orange" style={{ fontSize: 11 }}>{v}</Tag> : null },
]

function CaseListModal({
  title, cases, open, onClose, extra,
  extraColumns,
  tableSummary,
  width,
}: {
  title: React.ReactNode
  cases: RepairCase[]
  open: boolean
  onClose: () => void
  extra?: React.ReactNode
  extraColumns?: import('antd/es/table').ColumnsType<RepairCase>
  tableSummary?: (pageData: readonly RepairCase[]) => React.ReactNode
  width?: number
}) {
  const [drawerCase, setDrawerCase] = useState<RepairCase | null>(null)
  return (
    <>
      <Modal
        title={title}
        open={open}
        onCancel={onClose}
        footer={<Button onClick={onClose}>關閉</Button>}
        width={width ?? 1020}
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
              scroll={{ x: 'max-content' }}
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
  title, value, suffix = '', color, icon, sub, onClick, desc,
}: {
  title: string; value: string | number; suffix?: string
  color: string; icon: React.ReactNode; sub?: string
  onClick?: () => void
  desc?: string  // KPI 卡說明，顯示為 ? Tooltip
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
      <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
        {title}
        {desc && (
          <Tooltip title={desc} placement="top">
            <QuestionCircleOutlined
              style={{ color: '#bbb', fontSize: 11, marginLeft: 4, cursor: 'help' }}
              onClick={e => e.stopPropagation()}
            />
          </Tooltip>
        )}
      </div>
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
  // 圖片 lazy-fetch：caseData.images 為空時直接向 Ragic 抓 detail 取圖
  const [liveImages, setLiveImages] = useState<Array<{ url: string; filename: string }> | null>(null)
  const [imgLoading, setImgLoading] = useState(false)

  useEffect(() => {
    setLiveImages(null)
    if (!caseData) return
    if ((caseData.images ?? []).length > 0) return  // DB 已有圖，不需要再抓
    // DB 無圖 → 直接從 Ragic 抓 detail
    setImgLoading(true)
    fetchCaseImages(caseData.ragic_id)
      .then(res => setLiveImages(res.images))
      .catch(() => setLiveImages([]))
      .finally(() => setImgLoading(false))
  }, [caseData?.ragic_id])

  if (!caseData) return null

  const displayImages = (caseData.images ?? []).length > 0
    ? caseData.images
    : (liveImages ?? [])

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
        <Descriptions.Item label="扣款專櫃">
          {caseData.deduction_counter_name
            ? <Tag color="orange">{caseData.deduction_counter_name}</Tag>
            : '-'}
        </Descriptions.Item>
        {(caseData.counter_stores ?? []).length > 1 && (
          <Descriptions.Item label="各專櫃">
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {caseData.counter_stores.map((s, i) => (
                <Tag key={i} color="orange" style={{ fontSize: 11 }}>{s}</Tag>
              ))}
            </div>
          </Descriptions.Item>
        )}
        {caseData.mgmt_response && (
          <Descriptions.Item label="管理單位回應">
            <div
              style={{ fontSize: 11, color: '#444', lineHeight: 1.7, maxHeight: 260, overflowY: 'auto' }}
              // eslint-disable-next-line react/no-danger
              dangerouslySetInnerHTML={{ __html: caseData.mgmt_response }}
            />
          </Descriptions.Item>
        )}
        <Descriptions.Item label="財務備註">{caseData.finance_note || '-'}</Descriptions.Item>
        <Descriptions.Item label="維修圖片" span={2}>
          {displayImages.length > 0
            ? (
              <Image.PreviewGroup>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {displayImages.map((img, i) => (
                    <Image key={i} width={72} height={72} src={img.url}
                      alt={img.filename || `圖片${i + 1}`}
                      style={{ objectFit: 'cover', borderRadius: 4, cursor: 'pointer' }} />
                  ))}
                </div>
              </Image.PreviewGroup>
            )
            : imgLoading
              ? <Spin size="small" tip="載入圖片…" />
              : <Text style={{ color: '#bbb', fontSize: 12 }}>無圖片</Text>
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
  const [feeModal, setFeeModal] = useState<'fee' | 'deduction' | 'counter' | null>(null)
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
          annual_fee_detail, annual_deduction_detail, annual_counter_detail,
          kpi_total_detail, kpi_completed_detail, kpi_uncompleted_detail,
          kpi_counter_stores_detail,
          kpi_close_days_detail, kpi_room_detail, kpi_hours_detail } = data

  return (
    <div>
      {/* KPI 卡片 — 6 張一排，全部可點擊查看明細 */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'nowrap', overflowX: 'auto' }}>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="本月相關案件" value={fmt(kpi.total)} color="#1B3A5C" icon={<ToolOutlined />}
            sub="完工月＋未完成報修月" onClick={() => setKpiModal('total')}
            desc={LUQUN_KPI_DESC['本月相關案件']} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="已完成件數" value={fmt(kpi.completed)} color="#52C41A" icon={<CheckCircleOutlined />}
            sub={`完成率 ${kpi.total > 0 ? fmtDec(kpi.completed / kpi.total * 100) : '-'}% ｜ 依完工時間`}
            onClick={() => setKpiModal('completed')}
            desc={LUQUN_KPI_DESC['已完成件數']} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="未完成件數" value={fmt(kpi.uncompleted)} color="#FF4D4F" icon={<ExclamationCircleOutlined />}
            sub="無完工時間的案件" onClick={() => setKpiModal('uncompleted')}
            desc={LUQUN_KPI_DESC['未完成件數']} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="平均結案天數" value={kpi.avg_close_days != null ? fmtDec(kpi.avg_close_days, 1) : '-'}
            suffix="天" color="#4BA8E8" icon={<ClockCircleOutlined />}
            onClick={() => setKpiModal('close_days')}
            desc={LUQUN_KPI_DESC['平均結案天數']} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="本月工時統計" value={fmtDec(kpi.total_work_hours, 2)} suffix="hr"
            color="#13C2C2" icon={<ClockCircleOutlined />}
            sub={`${fmtDec(kpi.total_work_hours / 24, 2)} 天（花費工時 ÷24）`}
            onClick={() => setKpiModal('hours')}
            desc={LUQUN_KPI_DESC['本月工時統計']} />
        </div>
        <div style={{ flex: '1 1 0', minWidth: 110 }}>
          <KpiCard title="客房報修件數" value={fmt(kpi.room_cases)} color="#FA8C16" icon={<HomeOutlined />}
            onClick={() => setKpiModal('room')}
            desc={LUQUN_KPI_DESC['客房報修件數']} />
        </div>
      </div>

      {/* KPI 明細 Modals */}
      <CaseListModal title={<><ToolOutlined style={{ color: '#1B3A5C', marginRight: 8 }} />本月相關案件</>}
        cases={kpi_total_detail ?? []} open={kpiModal === 'total'} onClose={() => setKpiModal(null)}
        extra={<Space><Tag color="blue">共 {kpi.total} 筆</Tag><Tag color="default" style={{ fontSize: 11 }}>有完工時間者依完工月、未完成依報修月</Tag></Space>} />
      <CaseListModal title={<><CheckCircleOutlined style={{ color: '#52C41A', marginRight: 8 }} />已完成案件</>}
        cases={kpi_completed_detail ?? []} open={kpiModal === 'completed'} onClose={() => setKpiModal(null)}
        extra={<Space><Tag color="success">已完成 {kpi.completed} 筆</Tag><Tag color="default" style={{ fontSize: 11 }}>有完工時間者一律視為完工（含跨月案件）</Tag></Space>}
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
        extra={
          <Space wrap>
            <Tag color="cyan">花費工時合計 {fmtDec(kpi.total_work_hours, 2)} hr</Tag>
            <Tag color="blue">{fmtDec(kpi.total_work_hours / 24, 2)} 天（÷24換算）</Tag>
          </Space>
        }
        extraColumns={[{
          title: '結案天數(天)', dataIndex: 'close_days', width: 90, align: 'right' as const,
          render: (v: number | null) => v != null && v >= 0
            ? <span style={{ color: '#4BA8E8' }}>{fmtDec(v, 2)}</span>
            : <span style={{ color: '#ccc' }}>-</span>,
        }, {
          title: '花費工時(hr)', dataIndex: 'work_hours', width: 95, align: 'right' as const,
          render: (v: number) => v > 0
            ? <span style={{ color: '#13C2C2' }}>{fmtDec(v, 2)}</span>
            : <span style={{ color: '#ccc' }}>-</span>,
        }]}
        width={1140}
        tableSummary={(pageData) => {
          const pageHr   = pageData.reduce((s, c) => s + (c.work_hours || 0), 0)
          const pageDays = pageHr / 24
          const isLastPage = pageData.length < 20
          return (
            <Table.Summary fixed>
              <Table.Summary.Row style={{ background: '#e6fffb', fontWeight: 600 }}>
                <Table.Summary.Cell index={0} colSpan={5}>
                  {isLastPage
                    ? <span style={{ color: '#13C2C2' }}>本頁小計 / 總計</span>
                    : <span style={{ color: '#666' }}>本頁小計</span>}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={5} align="right">
                  <span style={{ color: '#ccc' }}>-</span>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={6} align="right">
                  <span style={{ color: '#ccc' }}>-</span>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={7} align="right">
                  <span style={{ color: '#4BA8E8', fontSize: 11 }}>{fmtDec(pageHr/24, 2)} 天</span>
                </Table.Summary.Cell>
                <Table.Summary.Cell index={8} align="right">
                  <span style={{ color: '#13C2C2', fontWeight: 700 }}>{fmtDec(pageHr, 2)} hr</span>
                  {isLastPage && (
                    <div style={{ color: '#389e0d', fontSize: 11, marginTop: 2, fontWeight: 700 }}>
                      總計 {fmtDec(kpi.total_work_hours, 2)} hr
                    </div>
                  )}
                </Table.Summary.Cell>
                <Table.Summary.Cell index={9} />
              </Table.Summary.Row>
            </Table.Summary>
          )
        }}
      />
      <CaseListModal title={<><HomeOutlined style={{ color: '#FA8C16', marginRight: 8 }} />客房報修案件</>}
        cases={kpi_room_detail ?? []} open={kpiModal === 'room'} onClose={() => setKpiModal(null)}
        extra={<Tag color="orange">共 {kpi.room_cases} 筆</Tag>} />

      {/* 年度費用 KPI + 當月金額 — 4 張一排 */}
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
              {fmtMoney(kpi.annual_deduction_fee ?? kpi.total_deduction_fee)}
            </div>
            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>扣款費用</div>
            <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>全年扣款費用合計</div>
            <div style={{ color: '#bbb', fontSize: 10, marginTop: 3 }}>點擊查看明細</div>
          </Card>
        </div>

        {/* 扣款專櫃（全年家數 + 金額） */}
        <div style={{ flex: '1 1 0', cursor: 'pointer' }} onClick={() => setFeeModal('counter')}>
          <Card size="small" style={{ textAlign: 'center', borderTop: '3px solid #FA8C16', transition: 'box-shadow .15s' }}
            hoverable>
            <div style={{ color: '#FA8C16', fontSize: 26, marginBottom: 2 }}><DollarOutlined /></div>
            <div style={{ color: '#FA8C16', fontSize: 22, fontWeight: 700, lineHeight: 1.3 }}>
              {kpi.annual_counter_stores ?? 0} 家
            </div>
            {(kpi.annual_counter_fee ?? 0) > 0 && (
              <div style={{ color: '#FA8C16', fontSize: 16, fontWeight: 600 }}>
                {fmtMoney(kpi.annual_counter_fee ?? 0)}
              </div>
            )}
            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>扣款專櫃</div>
            <div style={{ color: '#999', fontSize: 11, marginTop: 2 }}>
              {kpi.annual_counter_store_names?.length
                ? kpi.annual_counter_store_names.slice(0, 2).join('、') + (kpi.annual_counter_store_names.length > 2 ? '…' : '')
                : '全年無扣款專櫃'}
            </div>
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
                  {(kpi.total_counter_stores ?? 0) > 0
                    ? `${kpi.total_counter_stores} 家${(kpi.total_counter_fee ?? 0) > 0 ? ` / ${fmtMoney(kpi.total_counter_fee ?? 0)}` : ''}`
                    : '-'}
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
        width={1100}
      >
        <div style={{ marginBottom: 10 }}>
          <Tag color="purple" style={{ fontSize: 13 }}>委外費用合計：{fmtMoney(kpi.annual_outsource_fee)}</Tag>
          <Tag color="blue"   style={{ fontSize: 13 }}>維修費用合計：{fmtMoney(kpi.annual_maintenance_fee)}</Tag>
          <Tag color="geekblue" style={{ fontSize: 13 }}>總計：{fmtMoney(kpi.annual_fee)}</Tag>
          <Tag style={{ fontSize: 12 }}>共 {annual_fee_detail?.length ?? 0} 筆</Tag>
        </div>
        <Table
          size="small"
          dataSource={annual_fee_detail ?? []}
          rowKey="ragic_id"
          scroll={{ x: 900 }}
          pagination={{ pageSize: 20, showSizeChanger: false, showTotal: t => `共 ${t} 筆` }}
          columns={[
            { title: '報修編號', dataIndex: 'case_no',          width: 130, fixed: 'left' as const },
            { title: '標題',     dataIndex: 'title',             width: 200, ellipsis: true },
            { title: '樓層',     dataIndex: 'floor',             width: 70 },
            { title: '日期',     dataIndex: 'occurred_at',       width: 120 },
            { title: '狀態',     dataIndex: 'status',            width: 90,
              render: (s: string) => statusTag(s) },
            { title: '委外費用', dataIndex: 'outsource_fee',     width: 100, align: 'right' as const,
              render: (v: number) => v > 0 ? <span style={{ color: '#722ED1' }}>{fmtMoney(v)}</span> : '-' },
            { title: '維修費用', dataIndex: 'maintenance_fee',   width: 100, align: 'right' as const,
              render: (v: number) => v > 0 ? <span style={{ color: '#1890ff' }}>{fmtMoney(v)}</span> : '-' },
            { title: '總計',     dataIndex: 'total_fee',         width: 100, align: 'right' as const,
              render: (v: number) => <strong style={{ color: '#722ED1' }}>{fmtMoney(v)}</strong> },
            { title: '', width: 60, fixed: 'right' as const,
              render: (_: unknown, rec: RepairCase) => (
                <Button size="small" type="link" onClick={() => setDrawerCase(rec)}>詳情</Button>
              ) },
          ]}
        />
      </Modal>

      {/* ── 扣款費用 明細 Modal ──────────────────────────────────────────────── */}
      <Modal
        title={<><DollarOutlined style={{ color: '#FF4D4F', marginRight: 8 }} />扣款費用明細（全年）</>}
        open={feeModal === 'deduction'}
        onCancel={() => setFeeModal(null)}
        footer={<Button onClick={() => setFeeModal(null)}>關閉</Button>}
        width={1050}
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
              scroll={{ x: 860 }}
              pagination={{ pageSize: 20, showSizeChanger: false, showTotal: t => `共 ${t} 筆` }}
              columns={[
                { title: '報修編號', dataIndex: 'case_no',        width: 130, fixed: 'left' as const },
                { title: '標題',     dataIndex: 'title',           width: 200, ellipsis: true },
                { title: '日期',     dataIndex: 'occurred_at',     width: 120 },
                { title: '狀態',     dataIndex: 'status',          width: 90,
                  render: (s: string) => statusTag(s) },
                { title: '扣款事項', dataIndex: 'deduction_item',  width: 140, ellipsis: true },
                { title: '扣款費用', dataIndex: 'deduction_fee',   width: 110, align: 'right' as const,
                  render: (v: number) => <strong style={{ color: '#FF4D4F' }}>{fmtMoney(v)}</strong> },
                { title: '', width: 60, fixed: 'right' as const,
                  render: (_: unknown, rec: RepairCase) => (
                    <Button size="small" type="link" onClick={() => setDrawerCase(rec)}>詳情</Button>
                  ) },
              ]}
            />
          )
        }
      </Modal>

      {/* ── 扣款專櫃 明細 Modal（全年）─────────────────────────────────────── */}
      <Modal
        title={<><DollarOutlined style={{ color: '#FA8C16', marginRight: 8 }} />扣款專櫃明細（全年 {year}年）</>}
        open={feeModal === 'counter'}
        onCancel={() => setFeeModal(null)}
        footer={<Button onClick={() => setFeeModal(null)}>關閉</Button>}
        width={1050}
      >
        <div style={{ marginBottom: 10 }}>
          <Tag color="orange" style={{ fontSize: 13 }}>全年 {kpi.annual_counter_stores ?? 0} 家</Tag>
          {(kpi.annual_counter_store_names?.length ?? 0) > 0 && (
            <Tag color="default" style={{ fontSize: 11 }}>
              {kpi.annual_counter_store_names!.join('、')}
            </Tag>
          )}
          <Tag style={{ fontSize: 12 }}>{annual_counter_detail?.length ?? 0} 筆案件</Tag>
        </div>
        {(annual_counter_detail?.length ?? 0) === 0
          ? <Empty description="全年無扣款專櫃資料" />
          : (
            <Table
              size="small"
              dataSource={annual_counter_detail}
              rowKey="ragic_id"
              scroll={{ x: 900 }}
              pagination={{ pageSize: 20, showSizeChanger: false, showTotal: t => `共 ${t} 筆` }}
              columns={[
                { title: '報修編號', dataIndex: 'case_no',               width: 130, fixed: 'left' as const },
                { title: '標題',     dataIndex: 'title',                  width: 180, ellipsis: true },
                { title: '日期',     dataIndex: 'occurred_at',            width: 120 },
                { title: '扣款專櫃', dataIndex: 'deduction_counter_name', width: 120,
                  render: (v: string) => v
                    ? <Tag color="orange">{v}</Tag>
                    : '-' },
                { title: '管理單位回應', dataIndex: 'mgmt_response', width: 180, ellipsis: true,
                  render: (v: string) => v ? <span style={{ fontSize: 11, color: '#666' }}>{v}</span> : '-' },
                { title: '扣款費用', dataIndex: 'deduction_fee', width: 100, align: 'right' as const,
                  render: (v: number) => v > 0 ? <strong style={{ color: '#FA8C16' }}>{fmtMoney(v)}</strong> : '-' },
                { title: '', width: 60, fixed: 'right' as const,
                  render: (_: unknown, rec: RepairCase) => (
                    <Button size="small" type="link" onClick={() => setDrawerCase(rec)}>詳情</Button>
                  ) },
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
                    <div style={{ fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4, color: '#1B3A5C' }}>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.title || c.case_no || '-'}
                      </span>
                      {c.is_completed
                        ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12, flexShrink: 0 }} title="已結案" />
                        : <ClockCircleOutlined style={{ color: '#fa8c16', fontSize: 12, flexShrink: 0 }} title="未結案" />
                      }
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
                    <div style={{ fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 4, color: '#1B3A5C' }}>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.title || c.case_no || '-'}
                      </span>
                      {c.is_completed
                        ? <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12, flexShrink: 0 }} title="已結案" />
                        : <ClockCircleOutlined style={{ color: '#fa8c16', fontSize: 12, flexShrink: 0 }} title="未結案" />
                      }
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

      {/* 報修詳情 Drawer */}
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
    { key: 'prev_remaining',             detailKey: 'prev_remaining_detail',       label: '③ 上月累計完成數（① - ②）' },
    { key: 'cum_completion_rate',                                                   label: '④ 累計項目完成率（%）', isPct: true },
    { key: 'this_month_total',           detailKey: 'this_month_total_detail',     label: '⑤ 本月報修項目數' },
    { key: 'this_month_completed',       detailKey: 'this_month_completed_detail', label: '⑥ 本月報修項目完成數' },
    { key: 'this_month_uncompleted', detailKey: 'this_month_uncompleted_detail',   label: '⑦ 本月未完成數' },
    { key: 'this_month_completion_rate',                                            label: '⑧ 本月報修項目完成率（%）', isPct: true },
  ]

  // 未來月份判定：選擇的年份超過今年，或同年但月份超過當前月份
  const _now = new Date()
  const _curYear  = _now.getFullYear()
  const _curMonth = _now.getMonth() + 1
  const isFutureMonth = (m: number) =>
    year > _curYear || (year === _curYear && m > _curMonth)

  return (
    <div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#1B3A5C', color: '#fff' }}>
              <th style={{ padding: '8px 12px', textAlign: 'left', minWidth: 220, position: 'sticky', left: 0, background: '#1B3A5C', zIndex: 1 }}>
                統計項目
              </th>
              {MONTHS.map(m => (
                <th key={m} style={{
                  padding: '8px 8px', textAlign: 'center', minWidth: 72,
                  background: m === focusMonth ? '#4BA8E8' : '#1B3A5C',
                  fontWeight: m === focusMonth ? 700 : 400,
                  opacity: isFutureMonth(m) ? 0.5 : 1,
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
                  // 未來月份：全部顯示「—」，不可點擊
                  if (isFutureMonth(m)) {
                    return (
                      <td key={m} style={{
                        padding: '8px 8px', textAlign: 'center',
                        borderBottom: '1px solid #eee',
                        background: m === focusMonth ? '#E6F7FF' : ri % 2 === 0 ? '#fff' : '#f8f9fb',
                        color: '#ccc', fontSize: 12,
                      }}>
                        —
                      </td>
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
// Tab: 4.2 結案時間
// ═════════════════════════════════════════════════════════════════════════════
function ClosingTimeTab({ year, month }: { year: number; month: number | null }) {
  const [data, setData]         = useState<ClosingTimeData | null>(null)
  const [loading, setLoading]   = useState(false)
  const [modal, setModal]       = useState<{ title: string; cases: RepairCase[] } | null>(null)

  useEffect(() => {
    setLoading(true)
    fetchClosingStats(year, month ?? undefined)
      .then(setData)
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }, [year, month])

  if (loading) return <Spin />
  if (!data)   return <Empty />

  const openModal = (title: string, cases: RepairCase[]) => setModal({ title, cases })

  // ── 摘要卡（可點擊三個欄位）────────────────────────────────────────────────
  const BlockCard = ({ label, block, color }: {
    label: string
    block: ClosingTimeData['small']
    color: string
  }) => (
    <Card size="small" title={<span style={{ color }}>{label}</span>}
      style={{ marginBottom: 16, borderTop: `3px solid ${color}` }}>
      <Row gutter={24}>
        <Col span={8}>
          <div style={{ cursor: block.cases.length > 0 ? 'pointer' : 'default' }}
            onClick={() => block.cases.length > 0 && openModal(`${label} — 結案案件`, block.cases)}>
            <Statistic title="本期結案項目數" value={block.closed_count} suffix="件"
              valueStyle={{ color: block.cases.length > 0 ? color : undefined }} />
            {block.cases.length > 0 && <div style={{ color: '#bbb', fontSize: 10 }}>點擊查看明細</div>}
          </div>
        </Col>
        <Col span={8}>
          <div style={{ cursor: block.cases.length > 0 ? 'pointer' : 'default' }}
            onClick={() => block.cases.length > 0 && openModal(`${label} — 天數明細`, block.cases)}>
            <Statistic title="結案天數總計" value={fmtDec(block.total_days, 1)} suffix="天"
              valueStyle={{ color: block.cases.length > 0 ? color : undefined }} />
            {block.cases.length > 0 && <div style={{ color: '#bbb', fontSize: 10 }}>點擊查看明細</div>}
          </div>
        </Col>
        <Col span={8}>
          <div style={{ cursor: block.cases.length > 0 ? 'pointer' : 'default' }}
            onClick={() => block.cases.length > 0 && openModal(`${label} — 平均天數明細`, block.cases)}>
            <Statistic title="平均每項結案天數"
              value={block.avg_days != null ? fmtDec(block.avg_days, 2) : '-'}
              suffix={block.avg_days != null ? '天' : ''}
              valueStyle={{ color: block.cases.length > 0 ? color : undefined }} />
            {block.cases.length > 0 && <div style={{ color: '#bbb', fontSize: 10 }}>點擊查看明細</div>}
          </div>
        </Col>
      </Row>
    </Card>
  )

  // 未來月份判定
  const _now42 = new Date()
  const _curYear42  = _now42.getFullYear()
  const _curMonth42 = _now42.getMonth() + 1
  const isFutureMonth42 = (m: number) =>
    year > _curYear42 || (year === _curYear42 && m > _curMonth42)

  return (
    <div>
      <Alert type="info" showIcon
        message={`分類依據：${data.classification_note}`}
        style={{ marginBottom: 16 }} />

      <BlockCard label="A. 小型報修結案（total_fee = 0）" block={data.small} color="#4BA8E8" />
      <BlockCard label="B. 中大型報修結案（total_fee > 10,000）" block={data.large} color="#722ED1" />

      {/* 月份詳細表 — 所有非零數字可點擊 */}
      <Card size="small" title="各月份結案時間明細（點擊數字查看案件）" style={{ marginBottom: 16 }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ background: '#1B3A5C', color: '#fff' }}>
                <th style={{ padding: '6px 8px', textAlign: 'center' }}>月份</th>
                <th colSpan={3} style={{ padding: '6px 8px', textAlign: 'center', borderRight: '1px solid #4BA8E8' }}>小型報修</th>
                <th colSpan={3} style={{ padding: '6px 8px', textAlign: 'center' }}>中大型報修</th>
              </tr>
              <tr style={{ background: '#2a4f7c', color: '#cce4ff', fontSize: 11 }}>
                <th style={{ padding: '4px 8px' }} />
                {['結案件數', '天數合計', '平均天數', '結案件數', '天數合計', '平均天數'].map((h, i) => (
                  <th key={i} style={{ padding: '4px 8px', textAlign: 'center', borderRight: i === 2 ? '1px solid #4BA8E8' : undefined }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MONTHS.map((m, ri) => {
                const rowBg = m === month ? '#E6F7FF' : ri % 2 === 0 ? '#fff' : '#f8f9fb'

                // 未來月份：整列顯示 —
                if (isFutureMonth42(m)) {
                  return (
                    <tr key={m} style={{ background: rowBg }}>
                      <td style={{ padding: '6px 8px', textAlign: 'center', fontWeight: 600, color: '#aaa' }}>{m} 月</td>
                      {Array.from({ length: 6 }).map((_, i) => (
                        <td key={i} style={{
                          padding: '6px 8px', textAlign: 'center', color: '#ccc', fontSize: 12,
                          borderRight: i === 2 ? '1px solid #e8e8e8' : undefined,
                        }}>—</td>
                      ))}
                    </tr>
                  )
                }

                const md    = data.monthly[m]
                const s     = md?.small
                const l     = md?.large
                const clickStyle = (cases: RepairCase[] | undefined) =>
                  cases && cases.length > 0
                    ? { cursor: 'pointer', color: '#1B3A5C', fontWeight: 700, textDecoration: 'underline dotted' }
                    : {}
                return (
                  <tr key={m} style={{ background: rowBg, fontWeight: m === month ? 600 : 400 }}>
                    <td style={{ padding: '6px 8px', textAlign: 'center', fontWeight: 600 }}>{m} 月</td>
                    {/* 小型 */}
                    <td style={{ padding: '6px 8px', textAlign: 'center', ...clickStyle(s?.cases) }}
                      onClick={() => s?.cases?.length && openModal(`${m}月 小型結案`, s.cases)}>
                      {s?.closed_count ? s.closed_count : '-'}
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'center', ...clickStyle(s?.cases) }}
                      onClick={() => s?.cases?.length && openModal(`${m}月 小型結案`, s.cases)}>
                      {s?.closed_count ? fmtDec(s.total_days, 1) : '-'}
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'center', borderRight: '1px solid #e8e8e8', ...clickStyle(s?.cases) }}
                      onClick={() => s?.cases?.length && openModal(`${m}月 小型結案`, s.cases)}>
                      {s?.avg_days != null ? fmtDec(s.avg_days, 2) : '-'}
                    </td>
                    {/* 中大型 */}
                    <td style={{ padding: '6px 8px', textAlign: 'center', ...clickStyle(l?.cases) }}
                      onClick={() => l?.cases?.length && openModal(`${m}月 中大型結案`, l.cases)}>
                      {l?.closed_count ? l.closed_count : '-'}
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'center', ...clickStyle(l?.cases) }}
                      onClick={() => l?.cases?.length && openModal(`${m}月 中大型結案`, l.cases)}>
                      {l?.closed_count ? fmtDec(l.total_days, 1) : '-'}
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'center', ...clickStyle(l?.cases) }}
                      onClick={() => l?.cases?.length && openModal(`${m}月 中大型結案`, l.cases)}>
                      {l?.avg_days != null ? fmtDec(l.avg_days, 2) : '-'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      <Card size="small" title="未完成事項說明（原因 / 待協助事項）">
        <div style={{ color: '#999', fontSize: 12 }}>本區塊供人工填寫說明。</div>
      </Card>

      {/* 統一明細 Modal */}
      <CaseListModal
        title={modal?.title ?? ''}
        cases={modal?.cases ?? []}
        open={!!modal}
        onClose={() => setModal(null)}
        extra={<Tag color="blue">共 {modal?.cases.length ?? 0} 筆</Tag>}
      />
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 4.3 報修類型
// ═════════════════════════════════════════════════════════════════════════════
function RepairTypeTab({ year, focusMonth }: { year: number; focusMonth: number | null }) {
  const [data, setData]     = useState<TypeStatsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [modal, setModal]   = useState<{ title: string; cases: RepairCase[] } | null>(null)

  useEffect(() => {
    setLoading(true)
    fetchTypeStats(year, focusMonth ?? undefined)
      .then(setData)
      .catch(() => message.error('載入失敗'))
      .finally(() => setLoading(false))
  }, [year, focusMonth])

  if (loading) return <Spin />
  if (!data)   return <Empty />

  return (
    <div>
      {/* 摘要卡 */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col>
          <Card size="small">
            <Statistic title="今年累計件數" value={data.year_total} suffix="件" />
          </Card>
        </Col>
        {focusMonth != null && (
          <>
            <Col>
              <Card size="small">
                <Statistic
                  title={`${focusMonth > 1 ? focusMonth - 1 : 12} 月件數`}
                  value={data.rows.reduce((s, r) => s + r.prev_month, 0)}
                  suffix="件"
                />
              </Card>
            </Col>
            <Col>
              <Card size="small">
                <Statistic title={`${focusMonth} 月件數`} value={data.rows.reduce((s, r) => s + r.this_month, 0)} suffix="件" />
              </Card>
            </Col>
          </>
        )}
      </Row>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ background: '#1B3A5C', color: '#fff' }}>
              <th style={{ padding: '8px 10px', textAlign: 'left', minWidth: 80, position: 'sticky', left: 0, background: '#1B3A5C', zIndex: 1 }}>類別</th>
              <th style={{ padding: '8px 10px', textAlign: 'left', minWidth: 200 }}>MD內容</th>
              {MONTHS.map(m => (
                <th key={m} style={{
                  padding: '8px 6px', textAlign: 'center', minWidth: 44,
                  background: m === focusMonth ? '#4BA8E8' : '#1B3A5C',
                }}>
                  {m}月
                </th>
              ))}
              <th style={{ padding: '8px 6px', textAlign: 'center', minWidth: 56 }}>合計</th>
              <th style={{ padding: '8px 6px', textAlign: 'center', minWidth: 64 }}>年度佔比</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, ri) => {
              const hasData = row.row_total > 0
              // 合計欄也可點擊：收集該類型全年所有案件
              const allRowCases = Object.values(row.monthly_detail ?? {}).flat()
              return (
                <tr key={row.type} style={{
                  background: ri % 2 === 0 ? '#fff' : '#f8f9fb',
                  color: hasData ? '#333' : '#bbb',
                }}>
                  <td style={{
                    padding: '7px 10px', fontWeight: hasData ? 600 : 400, color: '#1B3A5C',
                    position: 'sticky', left: 0, background: ri % 2 === 0 ? '#fff' : '#f8f9fb', zIndex: 1,
                  }}>
                    {row.type}
                  </td>
                  <td style={{ padding: '7px 10px', fontSize: 11, color: '#666' }}>{row.example}</td>
                  {MONTHS.map(m => {
                    const cnt     = row.monthly[m] || 0
                    const detail  = row.monthly_detail?.[m] ?? []
                    const canClick = cnt > 0 && detail.length > 0
                    return (
                      <td key={m}
                        onClick={() => canClick && setModal({ title: `${m}月 ${row.type}（${cnt} 件）`, cases: detail })}
                        style={{
                          padding: '7px 6px', textAlign: 'center',
                          background: m === focusMonth ? '#E6F7FF' : ri % 2 === 0 ? '#fff' : '#f8f9fb',
                          fontWeight: m === focusMonth && cnt > 0 ? 700 : 400,
                          color: cnt > 0 ? '#1B3A5C' : '#ccc',
                          cursor: canClick ? 'pointer' : 'default',
                          textDecoration: canClick ? 'underline dotted' : undefined,
                        }}>
                        {cnt > 0 ? cnt : '-'}
                      </td>
                    )
                  })}
                  <td
                    onClick={() => allRowCases.length > 0 && setModal({ title: `${row.type} 全年（${row.row_total} 件）`, cases: allRowCases })}
                    style={{
                      padding: '7px 6px', textAlign: 'center', fontWeight: 600, color: '#333',
                      cursor: allRowCases.length > 0 ? 'pointer' : 'default',
                      textDecoration: allRowCases.length > 0 ? 'underline dotted' : undefined,
                    }}>
                    {row.row_total || '-'}
                  </td>
                  <td style={{ padding: '7px 6px', textAlign: 'center', color: '#666' }}>
                    {row.row_total > 0 ? `${row.cum_pct}%` : '-'}
                  </td>
                </tr>
              )
            })}
            {/* 合計行 */}
            <tr style={{ background: '#1B3A5C', color: '#fff', fontWeight: 600 }}>
              <td style={{ padding: '8px 10px', position: 'sticky', left: 0, background: '#1B3A5C', zIndex: 1 }}>合計</td>
              <td />
              {MONTHS.map(m => {
                const total = data.rows.reduce((s, r) => s + (r.monthly[m] || 0), 0)
                const allMonthCases = data.rows.flatMap(r => r.monthly_detail?.[m] ?? [])
                return (
                  <td key={m}
                    onClick={() => allMonthCases.length > 0 && setModal({ title: `${m}月 全類型（${total} 件）`, cases: allMonthCases })}
                    style={{
                      padding: '8px 6px', textAlign: 'center',
                      background: m === focusMonth ? '#2a6fad' : '#1B3A5C',
                      cursor: allMonthCases.length > 0 ? 'pointer' : 'default',
                      textDecoration: allMonthCases.length > 0 ? 'underline dotted' : undefined,
                    }}>
                    {total > 0 ? total : '-'}
                  </td>
                )
              })}
              <td style={{ padding: '8px 6px', textAlign: 'center' }}>{data.year_total}</td>
              <td style={{ padding: '8px 6px', textAlign: 'center' }}>100%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <CaseListModal title={modal?.title ?? ''} cases={modal?.cases ?? []}
        open={!!modal} onClose={() => setModal(null)}
        extra={<Tag color="blue">共 {modal?.cases.length ?? 0} 筆</Tag>} />
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 4.4 本月客房報修表
// ═════════════════════════════════════════════════════════════════════════════
function RoomRepairTab({ year, month }: { year: number; month: number }) {
  const [data, setData]             = useState<RoomRepairTableData | null>(null)
  const [loading, setLoading]       = useState(false)
  const [activeFloor, setFloor]     = useState<string | null>(null)
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

  const filteredRows = activeFloor
    ? data.rows.filter(r => r.floor === activeFloor)
    : data.rows

  return (
    <div>
      {/* 統計卡 */}
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', borderTop: '3px solid #1B3A5C' }}>
            <div style={{ fontSize: 11, color: '#999' }}>客房報修總件數</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#1B3A5C' }}>{data.total_room_cases}</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', borderTop: '3px solid #52C41A' }}>
            <div style={{ fontSize: 11, color: '#999' }}>涉及房號數</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#52C41A' }}>{data.rows.length}</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', borderTop: '3px solid #4BA8E8' }}>
            <div style={{ fontSize: 11, color: '#999' }}>涉及樓層數</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#4BA8E8' }}>{data.floors_with_data.length}</div>
          </Card>
        </Col>
      </Row>

      {/* 樓層篩選 — Button pills */}
      {data.floors_with_data.length > 0 && (
        <Space style={{ marginBottom: 12 }} wrap>
          <Text strong>樓層篩選：</Text>
          <Button
            size="small"
            type={activeFloor === null ? 'primary' : 'default'}
            onClick={() => setFloor(null)}
          >
            全部（{data.total_room_cases}）
          </Button>
          {data.floors_with_data.map(f => {
            const cnt = data.rows.filter(r => r.floor === f).length
            return (
              <Button
                key={f}
                size="small"
                type={activeFloor === f ? 'primary' : 'default'}
                onClick={() => setFloor(f)}
              >
                {f}（{cnt}）
              </Button>
            )
          })}
        </Space>
      )}

      {filteredRows.length === 0
        ? <Empty description="本月無客房報修資料" />
        : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ background: '#1B3A5C', color: '#fff' }}>
                  <th style={{ padding: '8px 10px', textAlign: 'center', minWidth: 70, position: 'sticky', left: 0, background: '#1B3A5C', zIndex: 1 }}>房號</th>
                  {data.categories.map(cat => (
                    <th key={cat} style={{ padding: '8px 6px', textAlign: 'center', minWidth: 80 }}>{cat}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((row, ri) => (
                  <tr key={row.room_no} style={{ background: ri % 2 === 0 ? '#fff' : '#f8f9fb' }}>
                    <td style={{
                      padding: '6px 10px', textAlign: 'center', fontWeight: 600, color: '#1B3A5C',
                      position: 'sticky', left: 0, background: ri % 2 === 0 ? '#fff' : '#f8f9fb', zIndex: 1,
                    }}>
                      {row.room_no}
                      <div style={{ fontSize: 10, color: '#999' }}>{row.floor}</div>
                    </td>
                    {data.categories.map(cat => {
                      const entries = row.categories[cat] || []
                      if (entries.length === 0) {
                        return <td key={cat} style={{ padding: '6px 6px', textAlign: 'center', color: '#eee' }}>-</td>
                      }
                      return (
                        <td key={cat} style={{ padding: '4px 6px', verticalAlign: 'top' }}>
                          {entries.slice(0, 2).map(e => (
                            <Tooltip key={e.ragic_id} title={`${e.title}（${e.status}）點擊查看詳情`}>
                              <Tag
                                color={e.status && STATUS_COLOR[e.status] ? undefined : 'default'}
                                onClick={() => setDrawerCase(e as unknown as RepairCase)}
                                style={{
                                  fontSize: 11, marginBottom: 2, display: 'block',
                                  cursor: 'pointer', maxWidth: '100%',
                                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                                }}
                              >
                                {e.title.length > 8 ? e.title.slice(0, 8) + '…' : e.title}
                              </Tag>
                            </Tooltip>
                          ))}
                          {entries.length > 2 && (
                            <Tag style={{ fontSize: 10, cursor: 'pointer' }}
                              onClick={() => setDrawerCase(entries[0] as unknown as RepairCase)}>
                              +{entries.length - 2}
                            </Tag>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      }

      {data.unknown_room_cases.length > 0 && (
        <Card size="small" title={`未判定房號案件（${data.unknown_room_cases.length} 筆）`} style={{ marginTop: 16 }}>
          {data.unknown_room_cases.map(c => (
            <Tag key={c.ragic_id} style={{ margin: 4, cursor: 'pointer' }}
              onClick={() => setDrawerCase(c as unknown as RepairCase)}>
              {c.title || c.case_no}
            </Tag>
          ))}
        </Card>
      )}

      <CaseDetailDrawer caseData={drawerCase} onClose={() => setDrawerCase(null)} />
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// Tab: 金額統計
// ═════════════════════════════════════════════════════════════════════════════
const FEE_DEFS = [
  { key: 'outsource_fee'   as const, label: '委外費用', color: '#1890ff' },
  { key: 'maintenance_fee' as const, label: '維修費用', color: '#52C41A' },
  { key: 'deduction_fee'   as const, label: '扣款費用', color: '#FF4D4F' },
  { key: 'deduction_counter' as const, label: '扣款專櫃', color: '#FA8C16' },
]
const MONTH_NUMS = [1,2,3,4,5,6,7,8,9,10,11,12]

function FeeStatsTab({ year }: { year: number }) {
  const [data,    setData]    = useState<import('@/types/luqunRepair').FeeStatsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)
  // 明細 Modal 狀態：{ feeKey, month, label }
  const [drilldown, setDrilldown] = useState<{
    feeKey: typeof FEE_DEFS[number]['key']
    month: number
    feeLabel: string
    color: string
  } | null>(null)
  const [drawerCase, setDrawerCase] = useState<RepairCase | null>(null)

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

  // ── 組合 Table columns ───────────────────────────────────────────────────
  type RowData = {
    key:   string
    label: string
    color: string
    isTotal: boolean
    [month: number]: number
    annual: number
  }

  const tableData: RowData[] = [
    ...FEE_DEFS.map(fd => ({
      key:     fd.key,
      label:   fd.label,
      color:   fd.color,
      isTotal: false,
      ...Object.fromEntries(MONTH_NUMS.map(m => [m, data.monthly_totals[m]?.[fd.key] ?? 0])),
      annual: data.fee_totals[fd.key] ?? 0,
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
      const fd = FEE_DEFS.find(f => f.key === row.key)!
      const displayVal = fd.key === 'deduction_counter' ? `${val} 家` : fmtMoney(val)
      return (
        <span
          style={cellStyle(val, fd.color, true)}
          onClick={() => setDrilldown({ feeKey: fd.key, month: m, feeLabel: fd.label, color: fd.color })}
        >
          {displayVal}
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
      render: (val: number, row: RowData) => {
        if (row.isTotal) {
          return <strong style={{ color: row.color, fontSize: 13 }}>{fmtMoney(val)}</strong>
        }
        if (row.key === 'deduction_counter') {
          return <strong style={{ color: row.color, fontSize: 13 }}>{val > 0 ? `${val} 家` : '-'}</strong>
        }
        return <strong style={{ color: row.color, fontSize: 13 }}>{fmtMoney(val)}</strong>
      },
    },
  ]

  // ── 明細 Modal ────────────────────────────────────────────────────────────
  const drillCases = drilldown
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
        rowClassName={(row) => row.isTotal ? 'fee-total-row' : ''}
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
        width={1100}
      >
        {drilldown && (
          <>
            <div style={{ marginBottom: 10 }}>
              <Tag color="blue">共 {drillCases.length} 筆</Tag>
              <Tag style={{ background: drilldown.color + '15', borderColor: drilldown.color, color: drilldown.color }}>
                {drilldown.feeKey === 'deduction_counter'
                  ? `${data.monthly_totals[drilldown.month]?.[drilldown.feeKey] ?? 0} 家`
                  : `合計：${fmtMoney(data.monthly_totals[drilldown.month]?.[drilldown.feeKey] ?? 0)}`}
              </Tag>
            </div>
            {drillCases.length === 0
              ? <Empty description="本月無此費用資料" />
              : (
                <Table
                  size="small"
                  dataSource={drillCases}
                  rowKey="ragic_id"
                  scroll={{ x: 900 }}
                  pagination={{ pageSize: 20, showSizeChanger: false, showTotal: t => `共 ${t} 筆` }}
                  columns={[
                    { title: '報修編號', dataIndex: 'case_no',     width: 130, fixed: 'left' as const },
                    { title: '標題',     dataIndex: 'title',        width: 200, ellipsis: true },
                    { title: '樓層',     dataIndex: 'floor',        width: 70 },
                    { title: '日期',     dataIndex: 'occurred_at',  width: 120 },
                    { title: '狀態',     dataIndex: 'status',       width: 90,
                      render: (s: string) => statusTag(s) },
                    {
                      title: drilldown.feeLabel,
                      dataIndex: drilldown.feeKey,
                      width: 120,
                      align: 'right' as const,
                      render: (v: number, record: RepairCase) => {
                        const amount = drilldown.feeKey === 'deduction_counter'
                          ? (record as unknown as Record<string, number>)['deduction_fee'] ?? 0
                          : v
                        return <strong style={{ color: drilldown.color }}>{fmtMoney(amount)}</strong>
                      },
                    },
                    { title: '', width: 60, fixed: 'right' as const,
                      render: (_: unknown, rec: RepairCase) => (
                        <Button size="small" type="link" onClick={() => setDrawerCase(rec)}>詳情</Button>
                      ) },
                  ]}
                />
              )
            }
          </>
        )}
      </Modal>

      {/* 報修詳情 Drawer */}
      <CaseDetailDrawer caseData={drawerCase} onClose={() => setDrawerCase(null)} />

      {/* 說明文字 */}
      <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
        💡 點擊有金額的格子可查看該月該費用類型的案件明細
      </div>
    </div>
  )
}


// ═════════════════════════════════════════════════════════════════════════════
// Tab: 春大直 - 報修清單總表（明細）
// ═════════════════════════════════════════════════════════════════════════════
function DetailTab({
  year, month, filterOptions,
}: {
  year: number; month: number | null; filterOptions: FilterOptions | null
}) {
  const [data, setData]         = useState<DetailResult | null>(null)
  const [loading, setLoading]   = useState(false)
  const [page, setPage]         = useState(1)
  const [repairType, setRepairType] = useState<string | null>(null)
  const [floor, setFloor]       = useState<string | null>(null)
  const [status, setStatus]     = useState<string | null>(null)
  const [keyword, setKeyword]   = useState('')
  const [drawerCase, setDrawerCase] = useState<RepairCase | null>(null)

  const load = useCallback(async (pg = 1) => {
    setLoading(true)
    try {
      const result = await fetchDetail({
        year:        year || undefined,
        month:       month || undefined,
        repair_type: repairType || undefined,
        floor:       floor || undefined,
        status:      status || undefined,
        keyword:     keyword || undefined,
        page:        pg,
        page_size:   50,
      })
      setData(result)
      setPage(pg)
    } catch {
      message.error('載入失敗')
    } finally {
      setLoading(false)
    }
  }, [year, month, repairType, floor, status, keyword])

  useEffect(() => { load(1) }, [year, month])  // 年月變動時重新查詢

  const columns: ColumnsType<RepairCase> = [
    { title: '報修編號', dataIndex: 'case_no', width: 100, ellipsis: true },
    {
      title: '標題', dataIndex: 'title', width: 200, ellipsis: true,
      render: (v, row) => (
        <a onClick={() => setDrawerCase(row)} style={{ cursor: 'pointer' }}>{v || '-'}</a>
      ),
    },
    { title: '報修人', dataIndex: 'reporter_name', width: 80 },
    {
      title: '類型', dataIndex: 'repair_type', width: 70,
      render: v => <Tag style={{ fontSize: 11 }}>{v || '-'}</Tag>,
    },
    { title: '樓層', dataIndex: 'floor_normalized', width: 60 },
    { title: '發生時間', dataIndex: 'occurred_at', width: 130, sorter: true },
    { title: '負責單位', dataIndex: 'responsible_unit', width: 80, ellipsis: true },
    { title: '工時(hr)', dataIndex: 'work_hours', width: 70, align: 'right', render: (v: number) => fmtDec(v, 2) },
    {
      title: '處理狀況', dataIndex: 'status', width: 90,
      render: statusTag,
    },
    {
      title: '委外費用', dataIndex: 'outsource_fee', width: 90, align: 'right',
      render: v => v > 0 ? fmtMoney(v) : '-',
    },
    {
      title: '維修費用', dataIndex: 'maintenance_fee', width: 90, align: 'right',
      render: v => v > 0 ? fmtMoney(v) : '-',
    },
    {
      title: '結案天數', dataIndex: 'close_days', width: 80, align: 'right',
      render: v => v != null ? `${fmtDec(v, 1)} 天` : '-',
    },
    {
      title: '扣款專櫃', dataIndex: 'deduction_counter_name', width: 100,
      render: (v: string) => v ? <Tag color="orange" style={{ fontSize: 11 }}>{v}</Tag> : null,
    },
    {
      title: '扣款費用', dataIndex: 'deduction_fee', width: 90, align: 'right' as const,
      render: (v: number) => v > 0 ? <span style={{ color: '#FA8C16', fontWeight: 600 }}>{fmtMoney(v)}</span> : '-',
    },
  ]

  const exportUrl = buildExportUrl({
    year:        year || undefined,
    month:       month || undefined,
    repair_type: repairType || undefined,
    floor:       floor || undefined,
    status:      status || undefined,
    keyword:     keyword || undefined,
  })

  return (
    <div>
      {/* 搜尋列 */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select placeholder="報修類型" allowClear style={{ width: 110 }}
            value={repairType ?? undefined} onChange={v => setRepairType(v ?? null)}>
            {filterOptions?.repair_types.map(t => <Option key={t} value={t}>{t}</Option>)}
          </Select>
          <Select placeholder="發生樓層" allowClear style={{ width: 100 }}
            value={floor ?? undefined} onChange={v => setFloor(v ?? null)}>
            {filterOptions?.floors.map(f => <Option key={f} value={f}>{f}</Option>)}
          </Select>
          <Select placeholder="處理狀況" allowClear style={{ width: 110 }}
            value={status ?? undefined} onChange={v => setStatus(v ?? null)}>
            {filterOptions?.statuses.map(s => <Option key={s} value={s}>{s}</Option>)}
          </Select>
          <input
            placeholder="關鍵字（編號/標題/報修人）"
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load(1)}
            style={{ padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, width: 200, fontSize: 13 }}
          />
          <Button type="primary" icon={<SearchOutlined />} onClick={() => load(1)} loading={loading}>查詢</Button>
          <Button onClick={() => { setRepairType(null); setFloor(null); setStatus(null); setKeyword('') }}>重設</Button>
          <Button
            icon={<DownloadOutlined />}
            href={exportUrl}
            target="_blank"
            style={{ marginLeft: 8 }}
          >
            匯出 Excel
          </Button>
        </Space>
      </Card>

      <Table
        dataSource={data?.items || []}
        columns={columns}
        rowKey="ragic_id"
        loading={loading}
        size="small"
        scroll={{ x: 1200 }}
        pagination={{
          current:   page,
          pageSize:  50,
          total:     data?.total || 0,
          showTotal: (t) => `共 ${t} 筆`,
          onChange:  (pg) => load(pg),
          showSizeChanger: false,
        }}
        onRow={row => ({ onClick: () => setDrawerCase(row), style: { cursor: 'pointer' } })}
      />

      {/* 詳情 Drawer */}
      <Drawer
        title={`報修詳情：${drawerCase?.case_no || ''}`}
        open={drawerCase != null}
        onClose={() => setDrawerCase(null)}
        width={520}
      >
        {drawerCase && (
          <Descriptions column={1} bordered size="small" labelStyle={{ width: 120, fontWeight: 500 }}>
            <Descriptions.Item label="報修編號">{drawerCase.case_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="標題">{drawerCase.title || '-'}</Descriptions.Item>
            <Descriptions.Item label="報修人姓名">{drawerCase.reporter_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="報修類型">{drawerCase.repair_type || '-'}</Descriptions.Item>
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
            <Descriptions.Item label="結案天數">{drawerCase.close_days != null ? `${fmtDec(drawerCase.close_days, 1)} 天` : '-'}</Descriptions.Item>
            <Descriptions.Item label="扣款事項">{drawerCase.deduction_item || '-'}</Descriptions.Item>
            <Descriptions.Item label="扣款費用">{drawerCase.deduction_fee > 0 ? fmtMoney(drawerCase.deduction_fee) : '-'}</Descriptions.Item>
            <Descriptions.Item label="扣款專櫃">
              {drawerCase.deduction_counter_name
                ? <Tag color="orange">{drawerCase.deduction_counter_name}</Tag>
                : '-'}
            </Descriptions.Item>
            {(drawerCase.counter_stores ?? []).length > 1 && (
              <Descriptions.Item label="各專櫃">
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {drawerCase.counter_stores!.map((s, i) => (
                    <Tag key={i} color="orange" style={{ fontSize: 11 }}>{s}</Tag>
                  ))}
                </div>
              </Descriptions.Item>
            )}
            {drawerCase.mgmt_response && (
              <Descriptions.Item label="管理單位回應">
                <div
                  style={{ fontSize: 11, color: '#444', lineHeight: 1.7, maxHeight: 260, overflowY: 'auto' }}
                  // eslint-disable-next-line react/no-danger
                  dangerouslySetInnerHTML={{ __html: drawerCase.mgmt_response }}
                />
              </Descriptions.Item>
            )}
            <Descriptions.Item label="財務備註">{drawerCase.finance_note || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  )
}

// ═════════════════════════════════════════════════════════════════════════════
// 主頁面
// ═════════════════════════════════════════════════════════════════════════════
export default function LuqunRepairPage() {
  const currentYear  = dayjs().year()
  const currentMonth = dayjs().month() + 1

  const [years, setYears]               = useState<number[]>([currentYear])
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null)

  // 共享查詢條件
  const [year,  setYear]  = useState(currentYear)
  const [month, setMonth] = useState<number | null>(currentMonth)

  // 各 Tab 使用的「已提交」查詢條件（點查詢後才更新）
  const [queryYear,  setQueryYear]  = useState(currentYear)
  const [queryMonth, setQueryMonth] = useState<number | null>(currentMonth)

  const [activeTab, setActiveTab] = useState('dashboard')

  // ── 同步 / 連線測試 ────────────────────────────────────────────────────────
  const [syncing,       setSyncing]       = useState(false)
  const [syncResult,    setSyncResult]    = useState<SyncResult | null>(null)
  const [syncModalOpen, setSyncModalOpen] = useState(false)

  const [pinging,       setPinging]       = useState(false)
  const [pingResult,    setPingResult]    = useState<PingResult | null>(null)
  const [pingModalOpen, setPingModalOpen] = useState(false)

  const handleSync = useCallback(async () => {
    setSyncing(true)
    try {
      const r = await fetchSync()
      setSyncResult(r)
      setSyncModalOpen(true)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      message.error(`同步失敗：${msg}`)
    } finally {
      setSyncing(false)
    }
  }, [])

  const handlePing = useCallback(async () => {
    setPinging(true)
    try {
      const r = await fetchPing()
      setPingResult(r)
      setPingModalOpen(true)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      message.error(`連線測試失敗：${msg}`)
    } finally {
      setPinging(false)
    }
  }, [])

  useEffect(() => {
    fetchYears().then(d => {
      const ys = d.years
      setYears(ys.length > 0 ? ys : [currentYear])
    }).catch(() => {})

    fetchFilterOptions().then(setFilterOptions).catch(() => {})
  }, [])

  const handleQuery = () => {
    setQueryYear(year)
    setQueryMonth(month)
  }

  const handleReset = () => {
    setYear(currentYear)
    setMonth(currentMonth)
    setQueryYear(currentYear)
    setQueryMonth(currentMonth)
  }

  const tabItems = [
    {
      key: 'dashboard',
      label: <><DashboardOutlined /> Dashboard</>,
      children: <DashboardTab year={queryYear} month={queryMonth ?? currentMonth} />,
    },
    {
      key: 'repair-stats',
      label: '4.1 報修',
      children: <RepairStatsTab year={queryYear} focusMonth={queryMonth} />,
    },
    {
      key: 'closing-time',
      label: '4.2 結案時間',
      children: <ClosingTimeTab year={queryYear} month={queryMonth} />,
    },
    {
      key: 'repair-type',
      label: '4.3 報修類型',
      children: <RepairTypeTab year={queryYear} focusMonth={queryMonth} />,
    },
    {
      key: 'room-repair',
      label: '4.4 本月客房報修表',
      children: <RoomRepairTab year={queryYear} month={queryMonth ?? currentMonth} />,
    },
    {
      key: 'fee-stats',
      label: '金額統計',
      children: <FeeStatsTab year={queryYear} />,
    },
    {
      key: 'detail',
      label: '報修清單總表',
      children: (
        <DetailTab
          year={queryYear}
          month={queryMonth}
          filterOptions={filterOptions}
        />
      ),
    },
  ]

  return (
    <div>
      {/* 麵包屑 */}
      <Breadcrumb
        style={{ marginBottom: 12 }}
        items={[
          { href: '/dashboard', title: <HomeOutlined /> },
          { title: NAV_GROUP.luqun_repair },
          { title: 'Dashboard' },
        ]}
      />

      {/* 頁面標題 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ToolOutlined style={{ fontSize: 24, color: '#1B3A5C' }} />
          <div>
            <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>樂群工務報修</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>春大直 - 報修清單總表</Text>
          </div>
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
            style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', border: 'none', color: '#fff' }}
          >
            同步 Ragic
          </Button>
        </Space>
      </div>

      {/* ── Ping Modal ─────────────────────────────────────────────────────── */}
      <Modal
        title={<><ApiOutlined style={{ color: '#4BA8E8', marginRight: 8 }} />樂群工務報修 — 連線測試結果</>}
        open={pingModalOpen}
        onCancel={() => setPingModalOpen(false)}
        footer={<Button onClick={() => setPingModalOpen(false)}>關閉</Button>}
        width={760}
      >
        {pingResult && (
          <div>
            <div style={{ background: '#f5f5f5', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontFamily: 'monospace', fontSize: 12 }}>
              🔗 {pingResult.ragic_base_url}
            </div>
            <div style={{ marginBottom: 12 }}>
              <Tag color="blue">API Key: {pingResult.api_key_prefix}</Tag>
              {pingResult.pageid && <Tag color="purple">PAGEID: {pingResult.pageid}</Tag>}
            </div>
            {pingResult.results.map((r, i) => (
              <Card key={i} size="small" style={{ marginBottom: 12, borderColor: r.error ? '#ff4d4f' : '#52c41a' }}>
                <Space wrap>
                  <Tag color={r.error ? 'error' : 'success'}>{r.test}</Tag>
                  {r.status_code && <Tag color={r.status_code === 200 ? 'success' : 'error'}>HTTP {r.status_code}</Tag>}
                  <Tag>{r.elapsed_ms} ms</Tag>
                  {r.record_count != null && <Tag color="blue">記錄數: {r.record_count}</Tag>}
                  {r.error && <Text type="danger" style={{ fontSize: 12 }}>{r.error}</Text>}
                  {r.tip   && <Text type="warning" style={{ fontSize: 12 }}>{r.tip}</Text>}
                </Space>
                {r.first_record_raw && Object.keys(r.first_record_raw).length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <Text strong style={{ fontSize: 12 }}>第一筆原始欄位（ID: {r.first_record_id}）</Text>
                    <div style={{ maxHeight: 320, overflowY: 'auto', marginTop: 6 }}>
                      <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ background: '#1B3A5C', color: '#fff' }}>
                            <th style={{ padding: '4px 8px', textAlign: 'left', width: '40%' }}>欄位名稱</th>
                            <th style={{ padding: '4px 8px', textAlign: 'left' }}>值</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(r.first_record_raw).map(([k, v], j) => (
                            <tr key={j} style={{ background: j % 2 === 0 ? '#fafafa' : '#fff' }}>
                              <td style={{ padding: '3px 8px', fontFamily: 'monospace', color: '#1B3A5C', borderBottom: '1px solid #f0f0f0' }}>{k}</td>
                              <td style={{ padding: '3px 8px', fontFamily: 'monospace', borderBottom: '1px solid #f0f0f0', wordBreak: 'break-all' }}>
                                {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </Modal>

      {/* ── Sync Modal ─────────────────────────────────────────────────────── */}
      <Modal
        title={<><SyncOutlined style={{ color: '#764ba2', marginRight: 8 }} />樂群工務報修 — Ragic 同步摘要</>}
        open={syncModalOpen}
        onCancel={() => setSyncModalOpen(false)}
        footer={<Button onClick={() => setSyncModalOpen(false)}>關閉</Button>}
        width={680}
      >
        {syncResult && (
          <div>
            <Space wrap style={{ marginBottom: 12 }}>
              <Tag color="blue" style={{ fontSize: 13, padding: '2px 10px' }}>總筆數：{syncResult.total_parsed}</Tag>
              <Tag color="orange" style={{ fontSize: 13, padding: '2px 10px' }}>無日期：{syncResult.no_date_count}</Tag>
            </Space>

            {/* 費用診斷 */}
            {syncResult.fee_totals && (
              <div style={{ marginBottom: 14, padding: '10px 12px', background: '#fafafa', borderRadius: 8, border: '1px solid #e8e8e8' }}>
                <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>💰 費用合計（全部資料）</Text>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {([
                    ['委外費用',      (syncResult.fee_totals as SyncFeeTotals).outsource_fee,              '#1890ff'],
                    ['維修費用',      (syncResult.fee_totals as SyncFeeTotals).maintenance_fee,            '#52c41a'],
                    ['委外+維修',     (syncResult.fee_totals as SyncFeeTotals).outsource_plus_maintenance, '#722ED1'],
                    ['扣款費用',      (syncResult.fee_totals as SyncFeeTotals).deduction_fee,              '#ff4d4f'],
                    ['扣款專櫃',      (syncResult.fee_totals as SyncFeeTotals).deduction_counter,          '#fa8c16'],
                  ] as [string, number, string][]).map(([label, val, color]) => (
                    <div key={label} style={{ textAlign: 'center', minWidth: 90, padding: '4px 8px', background: '#fff', borderRadius: 6, border: `1px solid ${color}30` }}>
                      <div style={{ color, fontWeight: 700, fontSize: 14 }}>${val.toLocaleString('zh-TW')}</div>
                      <div style={{ color: '#666', fontSize: 11 }}>{label}</div>
                    </div>
                  ))}
                </div>
                {syncResult.fee_samples && syncResult.fee_samples.length > 0 && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 11, color: '#888' }}>▶ 非零費用樣本（前5筆）— 可確認原始 Ragic 格式</summary>
                    <div style={{ marginTop: 6, maxHeight: 200, overflowY: 'auto' }}>
                      <table style={{ width: '100%', fontSize: 10, borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ background: '#1B3A5C', color: '#fff' }}>
                            <th style={{ padding: '3px 6px', textAlign: 'left' }}>編號</th>
                            <th style={{ padding: '3px 6px', textAlign: 'right' }}>委外(解析)</th>
                            <th style={{ padding: '3px 6px', textAlign: 'left' }}>委外(原始)</th>
                            <th style={{ padding: '3px 6px', textAlign: 'right' }}>維修(解析)</th>
                            <th style={{ padding: '3px 6px', textAlign: 'left' }}>維修(原始)</th>
                            <th style={{ padding: '3px 6px', textAlign: 'right' }}>扣款(解析)</th>
                            <th style={{ padding: '3px 6px', textAlign: 'left' }}>扣款(原始)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {syncResult.fee_samples.map((s, i) => (
                            <tr key={i} style={{ background: i % 2 === 0 ? '#fafafa' : '#fff' }}>
                              <td style={{ padding: '2px 6px', borderBottom: '1px solid #f0f0f0', fontFamily: 'monospace' }}>{s.case_no}</td>
                              <td style={{ padding: '2px 6px', borderBottom: '1px solid #f0f0f0', textAlign: 'right', color: '#1890ff' }}>{s.outsource_fee}</td>
                              <td style={{ padding: '2px 6px', borderBottom: '1px solid #f0f0f0', fontFamily: 'monospace', color: '#888' }}>{String(s._raw_outsource ?? '')}</td>
                              <td style={{ padding: '2px 6px', borderBottom: '1px solid #f0f0f0', textAlign: 'right', color: '#52c41a' }}>{s.maintenance_fee}</td>
                              <td style={{ padding: '2px 6px', borderBottom: '1px solid #f0f0f0', fontFamily: 'monospace', color: '#888' }}>{String(s._raw_maintenance ?? '')}</td>
                              <td style={{ padding: '2px 6px', borderBottom: '1px solid #f0f0f0', textAlign: 'right', color: '#ff4d4f' }}>{s.deduction_fee}</td>
                              <td style={{ padding: '2px 6px', borderBottom: '1px solid #f0f0f0', fontFamily: 'monospace', color: '#888' }}>{String(s._raw_deduction ?? '')}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </details>
                )}
              </div>
            )}

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

      {/* 查詢列 */}
      <QueryBar
        year={year}
        month={month}
        years={years}
        onYearChange={setYear}
        onMonthChange={setMonth}
        onQuery={handleQuery}
        onReset={handleReset}
        showMonth={true}
        monthRequired={false}
      />

      {/* Tab 切換 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        type="card"
        size="small"
        style={{ background: '#fff', padding: '0 0 16px' }}
        tabBarStyle={{ marginBottom: 16 }}
      />
    </div>
  )
}
