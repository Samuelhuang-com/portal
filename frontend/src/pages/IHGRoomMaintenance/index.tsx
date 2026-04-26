/**
 * IHG 客房保養主頁
 *
 * 功能：
 *   - KPI 統計卡（全年應保養/已完成/未完成/逾期/完成率）
 *   - 年度保養矩陣表（房號 × 月份）
 *   - 狀態顏色：completed=綠 / overdue=紅 / scheduled=黃藍 / pending=灰
 *   - 點擊格子從右側滑出 Drawer 顯示完整明細
 *   - 篩選：年度 / 房號 / 樓層 / 狀態
 *   - 同步 Ragic 按鈕
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Breadcrumb, Button, Card, Col, Descriptions, Divider,
  Drawer, Row, Select, Segmented, Spin, Statistic, Table, Tag, Tooltip,
  Typography, message,
} from 'antd'
import {
  CheckCircleOutlined, ClockCircleOutlined,
  HomeOutlined, QuestionCircleOutlined, ReloadOutlined,
  SyncOutlined, ToolOutlined, WarningOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchIHGMatrix,
  fetchIHGStats,
  fetchIHGRecord,
  syncIHGFromRagic,
} from '@/api/ihgRoomMaintenance'
import type {
  CellStatus,
  IHGRecord,
  IHGStats,
  MatrixCell,
  MatrixRoom,
} from '@/types/ihgRoomMaintenance'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography

// ── 月份中文 ──────────────────────────────────────────────────────────────────
const MONTH_LABELS: Record<number, string> = {
  1:'1月', 2:'2月', 3:'3月', 4:'4月', 5:'5月', 6:'6月',
  7:'7月', 8:'8月', 9:'9月', 10:'10月', 11:'11月', 12:'12月',
}

// ── 季度映射 ──────────────────────────────────────────────────────────────────
const QUARTER_MAP: Record<number, string> = {
  1:'Q1', 2:'Q1', 3:'Q1',
  4:'Q2', 5:'Q2', 6:'Q2',
  7:'Q3', 8:'Q3', 9:'Q3',
  10:'Q4', 11:'Q4', 12:'Q4',
}

// ── 狀態設定 ──────────────────────────────────────────────────────────────────
const STATUS_CFG: Record<CellStatus, { label: string; bg: string; text: string; tagColor: string; icon: React.ReactNode }> = {
  completed: {
    label: '已完成', bg: '#f6ffed', text: '#389e0d', tagColor: 'success',
    icon: <CheckCircleOutlined />,
  },
  abnormal: {
    label: '異常', bg: '#fff7e6', text: '#d46b08', tagColor: 'warning',
    icon: <WarningOutlined />,
  },
  scheduled: {
    label: '本月應保養', bg: '#e6f4ff', text: '#1677ff', tagColor: 'processing',
    icon: <ClockCircleOutlined />,
  },
  pending: {
    label: '待保養', bg: '#fafafa', text: '#8c8c8c', tagColor: 'default',
    icon: <QuestionCircleOutlined />,
  },
}

// ── 年度選項 ──────────────────────────────────────────────────────────────────
const thisYear = dayjs().year()
const YEAR_OPTIONS = [thisYear - 1, thisYear, thisYear + 1].map((y) => ({
  value: String(y),
  label: `${y} 年`,
}))

// ── 矩陣格元件 ────────────────────────────────────────────────────────────────
function MatrixCellComp({
  cell,
  month,
  onClick,
}: {
  cell: MatrixCell | undefined
  month: number
  onClick: () => void
}) {
  const today = dayjs()
  const isCurrentMonth = today.month() + 1 === month && today.year() === thisYear

  if (!cell) {
    return (
      <div
        style={{
          minWidth: 68, height: 54, background: '#f5f5f5',
          borderRadius: 4, border: '1px dashed #d9d9d9',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, color: '#bfbfbf',
        }}
      >
        —
      </div>
    )
  }

  const cfg = STATUS_CFG[cell.status] ?? STATUS_CFG.pending

  // 計數摘要：有值時才顯示
  const totalChecks = (cell.normal_count ?? 0) + (cell.done_count ?? 0) + (cell.maint_count ?? 0)
  const hasChecks = totalChecks > 0

  const borderColor = isCurrentMonth ? '#1677ff' : `${cfg.text}44`
  const defaultShadow = isCurrentMonth ? '0 0 0 2px #1677ff40' : 'none'

  return (
    <Tooltip
      title={
        <div style={{ fontSize: 12 }}>
          <div>狀態：{cfg.label}</div>
          {hasChecks && (
            <div>
              正常 {cell.normal_count} ／ 完成 {cell.done_count} ／
              維護 {cell.maint_count} ／ 未檢查 {cell.unchecked_count ?? 0}
            </div>
          )}
          {cell.date && <div>日期：{cell.date}{cell.work_minutes ? ` (${cell.work_minutes}m)` : ''}</div>}
          {cell.assignee && <div>人員：{cell.assignee}</div>}
          {cell.completion_date && <div>完成：{cell.completion_date}</div>}
          {cell.notes && <div>備註：{cell.notes}</div>}
          <div style={{ marginTop: 4, color: '#aaa' }}>點擊查看詳情</div>
        </div>
      }
    >
      <div
        onClick={onClick}
        style={{
          minWidth: 76, height: 58, background: cfg.bg,
          borderRadius: 4,
          border: `1px solid ${borderColor}`,
          cursor: 'pointer',
          padding: '3px 5px',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          gap: 1,
          transition: 'box-shadow 0.15s',
          boxShadow: defaultShadow,
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.18)' }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = defaultShadow }}
      >
        {hasChecks ? (
          // 顯示計數摘要
          <>
            <span style={{ fontSize: 9, color: cfg.text, lineHeight: 1.4, fontWeight: 500, whiteSpace: 'nowrap' }}>
              正常 {cell.normal_count} / 完成 {cell.done_count}
            </span>
            <span style={{
              fontSize: 9,
              color: (cell.maint_count ?? 0) > 0 ? '#d46b08'
                   : (cell.unchecked_count ?? 0) > 0 ? '#faad14' : '#8c8c8c',
              fontWeight: ((cell.maint_count ?? 0) > 0 || (cell.unchecked_count ?? 0) > 0) ? 700 : 400,
              lineHeight: 1.4,
              whiteSpace: 'nowrap',
            }}>
              維護 {cell.maint_count ?? 0} / 未 {cell.unchecked_count ?? 0}
            </span>
            {cell.date && (
              <span style={{ fontSize: 9, color: '#999', lineHeight: 1.4 }}>
                {cell.date.replace(/^\d{4}\//, '')}
                {cell.work_minutes ? ` (${cell.work_minutes}m)` : ''}
              </span>
            )}
          </>
        ) : (
          // 無計數資料時，退回 icon + 日期
          <>
            <span style={{ fontSize: 13, color: cfg.text }}>{cfg.icon}</span>
            {cell.date && (
              <span style={{ fontSize: 9, color: '#999' }}>
                {cell.date.replace(/^\d{4}\//, '')}
                {cell.work_minutes ? ` (${cell.work_minutes}m)` : ''}
              </span>
            )}
          </>
        )}
      </div>
    </Tooltip>
  )
}

// ── 保養檢查欄位：忽略規則（與後端 _IGNORE_FIELD_NAMES / _is_check_field 同步）──
const IGNORE_FIELD_NAMES = new Set([
  '項目', '更換日期', '費用', '設備保養上傳照片', '設備',
  '保養月份', '保養人員', '保養時間起', '保養時間迄', '保養日期',
  '工時計算', '房號', '複核人員', '是否有陽台',
])

function isCheckField(key: string, value: unknown): boolean {
  if (IGNORE_FIELD_NAMES.has(key)) return false
  if (key.includes('上傳照片')) return false
  if (typeof value === 'string' && ['正常', '當時維護完成', '等待維護(待料中)', ''].includes(value)) return true
  if (value === null || value === undefined) return true
  return false
}

// ── 保養檢查項目面板（Drawer 內）────────────────────────────────────────────
type CheckValue = '正常' | '當時維護完成' | '等待維護(待料中)' | ''

const CHECK_FILTER_OPTIONS = [
  { label: 'ALL',  value: 'ALL'            },
  { label: '正常',  value: '正常'            },
  { label: '完成',  value: '當時維護完成'     },
  { label: '維護',  value: '等待維護(待料中)' },
  { label: '未檢查', value: '__UNCHECKED__'  },
]

function CheckItemsPanel({ rawFields }: { rawFields: Record<string, unknown> }) {
  const [filter, setFilter] = useState<string>('ALL')

  const allItems = useMemo(
    () =>
      Object.entries(rawFields)
        .filter(([k, v]) => isCheckField(k, v))
        .map(([k, v], i) => ({
          key: i,
          field: k,
          value: (typeof v === 'string' ? v : '') as CheckValue,
        })),
    [rawFields]
  )

  if (allItems.length === 0) return null

  const hasMaint = allItems.some(r => r.value === '等待維護(待料中)')

  const counts: Record<string, number> = {
    '正常':            allItems.filter(r => r.value === '正常').length,
    '當時維護完成':     allItems.filter(r => r.value === '當時維護完成').length,
    '等待維護(待料中)': allItems.filter(r => r.value === '等待維護(待料中)').length,
    '__UNCHECKED__':    allItems.filter(r => r.value === '').length,
  }

  const filtered = filter === 'ALL'
    ? allItems
    : filter === '__UNCHECKED__'
      ? allItems.filter(r => r.value === '')
      : allItems.filter(r => r.value === filter)

  return (
    <>
      <Divider
        orientation="left"
        style={{ fontSize: 12, color: hasMaint ? '#d46b08' : '#1677ff' }}
      >
        {hasMaint
          ? <WarningOutlined style={{ marginRight: 4 }} />
          : <CheckCircleOutlined style={{ marginRight: 4 }} />}
        {hasMaint ? '維護異常項目' : '保養檢查項目'}
        <span style={{ marginLeft: 8, fontSize: 11, fontWeight: 400, color: '#8c8c8c' }}>
          正常 {counts['正常']} ／ 完成 {counts['當時維護完成']} ／
          維護 {counts['等待維護(待料中)']} ／ 未檢查 {counts['__UNCHECKED__']}
        </span>
      </Divider>

      {/* 篩選 Segmented */}
      <Segmented
        size="small"
        value={filter}
        onChange={(v) => setFilter(v as string)}
        style={{ marginBottom: 8 }}
        options={CHECK_FILTER_OPTIONS.map((o) => {
          const cnt = o.value === 'ALL' ? allItems.length : (counts[o.value] ?? 0)
          const isWarn = o.value === '等待維護(待料中)'
          const isUnchecked = o.value === '__UNCHECKED__'
          return {
            value: o.value,
            label: (
              <span>
                {o.label}
                <span style={{
                  marginLeft: 4, fontSize: 10,
                  color: isWarn ? '#d46b08' : isUnchecked ? '#faad14' : '#8c8c8c',
                  fontWeight: (isWarn || isUnchecked) ? 700 : 400,
                }}>
                  {cnt}
                </span>
              </span>
            ),
          }
        })}
      />

      <Table
        size="small"
        dataSource={filtered}
        rowKey="key"
        pagination={false}
        style={{ marginBottom: 16 }}
        columns={[
          {
            title: '項目名稱',
            dataIndex: 'field',
            key: 'field',
            ellipsis: true,
            render: (f: string, row) => (
              <span style={{
                color: row.value === '等待維護(待料中)' ? '#d46b08'
                     : row.value === '' ? '#faad14' : undefined,
                fontWeight: row.value === '等待維護(待料中)' || row.value === '' ? 600 : undefined,
              }}>
                {f}
              </span>
            ),
          },
          {
            title: '狀態',
            dataIndex: 'value',
            key: 'value',
            width: 140,
            render: (v: string) => {
              if (v === '正常')          return <Tag color="success"><CheckCircleOutlined /> 正常</Tag>
              if (v === '當時維護完成')   return <Tag color="processing"><ClockCircleOutlined /> 當時維護完成</Tag>
              if (v === '等待維護(待料中)') return <Tag color="warning"><WarningOutlined /> 等待維護(待料中)</Tag>
              return <Tag color="default"><QuestionCircleOutlined /> 未檢查</Tag>
            },
          },
        ]}
      />
    </>
  )
}

// ── 季度視角型別與常數 ─────────────────────────────────────────────────────────
type QuarterName = 'Q1' | 'Q2' | 'Q3' | 'Q4'

const QUARTER_MONTHS_MAP: Record<QuarterName, number[]> = {
  Q1: [1, 2, 3],
  Q2: [4, 5, 6],
  Q3: [7, 8, 9],
  Q4: [10, 11, 12],
}

interface QuarterCellData {
  status: CellStatus
  normal_total: number
  done_total: number
  maint_total: number
  unchecked_total: number
  work_minutes_total: number   // 分鐘
  active_cells: { month: number; cell: MatrixCell }[]
}

interface QuarterRoomData {
  room_no: string
  floor: string
  quarters: Partial<Record<QuarterName, QuarterCellData>>
}

// ── 季度格元件 ────────────────────────────────────────────────────────────────
function QuarterCellComp({
  qdata,
  qname,
  onClick,
}: {
  qdata: QuarterCellData | undefined
  qname: QuarterName
  onClick: () => void
}) {
  const today = dayjs()
  const currentQ = (['Q1','Q2','Q3','Q4'] as QuarterName[])[Math.floor((today.month()) / 3)]
  const isCurrentQ = qname === currentQ

  if (!qdata || qdata.active_cells.length === 0) {
    return (
      <div style={{
        minWidth: 88, height: 66, background: '#f5f5f5',
        borderRadius: 4, border: '1px dashed #d9d9d9',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 10, color: '#bfbfbf',
      }}>—</div>
    )
  }

  const cfg = STATUS_CFG[qdata.status] ?? STATUS_CFG.pending
  const borderColor = isCurrentQ ? '#1677ff' : `${cfg.text}44`
  const defaultShadow = isCurrentQ ? '0 0 0 2px #1677ff40' : 'none'
  const hrs = qdata.work_minutes_total > 0 ? (qdata.work_minutes_total / 60).toFixed(2) : null

  return (
    <Tooltip title={
      <div style={{ fontSize: 12 }}>
        <div>狀態：{cfg.label}</div>
        <div>正常 {qdata.normal_total} ／ 完成 {qdata.done_total} ／ 維護 {qdata.maint_total} ／ 未檢查 {qdata.unchecked_total}</div>
        {hrs && <div>工時：{hrs} hr</div>}
        <div style={{ color: '#aaa', marginTop: 4 }}>
          {qdata.active_cells.map(a => MONTH_LABELS[a.month]).join('、')} 共 {qdata.active_cells.length} 筆
        </div>
        <div style={{ color: '#aaa' }}>點擊查看月份明細</div>
      </div>
    }>
      <div
        onClick={onClick}
        style={{
          minWidth: 88, height: 66, background: cfg.bg,
          borderRadius: 4, border: `1px solid ${borderColor}`,
          cursor: 'pointer', padding: '4px 6px',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center', gap: 2,
          transition: 'box-shadow 0.15s', boxShadow: defaultShadow,
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.18)' }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = defaultShadow }}
      >
        <span style={{ fontSize: 9, color: cfg.text, fontWeight: 600, lineHeight: 1.4, whiteSpace: 'nowrap' }}>
          正常 {qdata.normal_total} / 完成 {qdata.done_total}
        </span>
        <span style={{
          fontSize: 9, lineHeight: 1.4, whiteSpace: 'nowrap',
          color: qdata.maint_total > 0 ? '#d46b08' : qdata.unchecked_total > 0 ? '#faad14' : '#8c8c8c',
          fontWeight: (qdata.maint_total > 0 || qdata.unchecked_total > 0) ? 700 : 400,
        }}>
          維護 {qdata.maint_total} / 未 {qdata.unchecked_total}
        </span>
        {hrs && (
          <span style={{ fontSize: 9, color: '#4BA8E8', lineHeight: 1.4 }}>{hrs} hr</span>
        )}
        <span style={{ fontSize: 9, color: '#bbb', lineHeight: 1.4 }}>
          {qdata.active_cells.map(a => MONTH_LABELS[a.month]).join(' ')}
        </span>
      </div>
    </Tooltip>
  )
}

// ── 主元件 ────────────────────────────────────────────────────────────────────
export default function IHGRoomMaintenancePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const viewMode = (searchParams.get('view') === 'quarter' ? 'quarter' : 'month') as 'month' | 'quarter'

  const [year, setYear]         = useState<string>(String(thisYear))
  const [roomFilter, setRoomFilter]   = useState<string>('')
  const [floorFilter, setFloorFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')

  const [stats, setStats]       = useState<IHGStats | null>(null)
  const [matrix, setMatrix]     = useState<{ rooms: MatrixRoom[]; floors: string[]; month_hours: Partial<Record<number, number>> } | null>(null)
  const [loading, setLoading]   = useState(false)
  const [syncing, setSyncing]   = useState(false)

  // 月份 Drawer 狀態
  const [drawerOpen, setDrawerOpen]     = useState(false)
  const [drawerRecord, setDrawerRecord] = useState<IHGRecord | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [drawerCell, setDrawerCell]     = useState<{ room_no: string; month: number } | null>(null)

  // 季度彙整 Drawer 狀態
  const [qDrawerOpen, setQDrawerOpen]   = useState(false)
  const [qDrawerData, setQDrawerData]   = useState<{ room_no: string; qname: QuarterName; qdata: QuarterCellData } | null>(null)

  // ── 載入資料 ───────────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [s, m] = await Promise.all([
        fetchIHGStats(year),
        fetchIHGMatrix({
          year,
          room_no: roomFilter || undefined,
          floor: floorFilter || undefined,
          cell_status: statusFilter || undefined,
        }),
      ])
      setStats(s)
      setMatrix({ rooms: m.rooms, floors: m.floors, month_hours: m.month_hours ?? {} })
    } catch {
      message.error('載入 IHG 客房保養資料失敗')
    } finally {
      setLoading(false)
    }
  }, [year, roomFilter, floorFilter, statusFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  // ── 同步 ──────────────────────────────────────────────────────────────────
  const handleSync = async () => {
    setSyncing(true)
    try {
      const r = await syncIHGFromRagic()
      message.success(r.message || '同步已啟動，請稍後刷新')
      setTimeout(loadData, 4000)
    } catch {
      message.error('同步失敗')
    } finally {
      setSyncing(false)
    }
  }

  // ── 點擊格子 → 開啟右側 Drawer ──────────────────────────────────────────
  const handleCellClick = async (ragic_id: string, room_no: string, month: number) => {
    setDrawerCell({ room_no, month })
    setDrawerOpen(true)
    setDrawerRecord(null)
    setDrawerLoading(true)
    try {
      const rec = await fetchIHGRecord(ragic_id)
      setDrawerRecord(rec)
    } catch {
      message.error('載入明細失敗')
    } finally {
      setDrawerLoading(false)
    }
  }

  // ── 樓層選項 ──────────────────────────────────────────────────────────────
  const floorOptions = useMemo(
    () => (matrix?.floors ?? []).map((f) => ({ value: f, label: f })),
    [matrix]
  )

  // ── 季度聚合（前端計算，不需新 API）────────────────────────────────────────
  const quarterRooms = useMemo<QuarterRoomData[]>(() => {
    if (!matrix) return []
    return matrix.rooms.map((room) => {
      const quarters: Partial<Record<QuarterName, QuarterCellData>> = {}
      for (const [qname, months] of Object.entries(QUARTER_MONTHS_MAP) as [QuarterName, number[]][]) {
        const active_cells: { month: number; cell: MatrixCell }[] = []
        let normal_total = 0, done_total = 0, maint_total = 0, unchecked_total = 0, work_minutes_total = 0

        for (const m of months) {
          const cell = room.cells[String(m)]
          if (cell) {
            active_cells.push({ month: m, cell })
            normal_total    += cell.normal_count    ?? 0
            done_total      += cell.done_count      ?? 0
            maint_total     += cell.maint_count     ?? 0
            unchecked_total += cell.unchecked_count ?? 0
            work_minutes_total += cell.work_minutes ?? 0
          }
        }

        if (active_cells.length === 0) continue

        // 季度狀態：最嚴重優先
        let status: CellStatus = 'pending'
        if (maint_total > 0) {
          status = 'abnormal'
        } else if (normal_total + done_total > 0 && unchecked_total === 0) {
          status = 'completed'
        } else {
          // 若有當季月份→ scheduled
          const today = dayjs()
          const currentM = today.month() + 1
          const isCurrentQ = months.includes(currentM) && today.year() === Number(year)
          status = isCurrentQ ? 'scheduled' : 'pending'
        }

        quarters[qname] = { status, normal_total, done_total, maint_total, unchecked_total, work_minutes_total, active_cells }
      }
      return { room_no: room.room_no, floor: room.floor, quarters }
    })
  }, [matrix, year])

  // ── 季度 Table columns ──────────────────────────────────────────────────
  const quarterColumns: ColumnsType<QuarterRoomData> = [
    {
      title: '房號',
      dataIndex: 'room_no',
      key: 'room_no',
      fixed: 'left',
      width: 76,
      render: (rn: string, row: QuarterRoomData) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{rn}</div>
          <div style={{ fontSize: 10, color: '#999' }}>{row.floor}</div>
        </div>
      ),
    },
    ...(['Q1','Q2','Q3','Q4'] as QuarterName[]).map((qname) => {
      const qMonths = QUARTER_MONTHS_MAP[qname]
      const qHrs = qMonths.reduce((sum, m) => sum + (matrix?.month_hours?.[m] ?? 0), 0)
      return {
        title: (
          <div style={{ textAlign: 'center', fontSize: 11 }}>
            <div style={{ fontWeight: 600 }}>{qname}</div>
            <div style={{ color: '#999', fontSize: 9 }}>{qMonths.map(m => MONTH_LABELS[m]).join(' ')}</div>
            {qHrs > 0 && (
              <div style={{ fontSize: 9, color: '#4BA8E8', marginTop: 1 }}>
                {(qHrs / 60).toFixed(2)} hr
              </div>
            )}
          </div>
        ),
        key: qname,
        width: 100,
        render: (_: unknown, row: QuarterRoomData) => {
          const qdata = row.quarters[qname]
          return (
            <QuarterCellComp
              qdata={qdata}
              qname={qname}
              onClick={() => {
                if (qdata) setQDrawerData({ room_no: row.room_no, qname, qdata })
                if (qdata) setQDrawerOpen(true)
              }}
            />
          )
        },
      }
    }),
  ]

  // ── 矩陣 Table columns ───────────────────────────────────────────────────
  const columns: ColumnsType<MatrixRoom> = [
    {
      title: '房號',
      dataIndex: 'room_no',
      key: 'room_no',
      fixed: 'left',
      width: 76,
      render: (rn: string, row: MatrixRoom) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{rn}</div>
          <div style={{ fontSize: 10, color: '#999' }}>{row.floor}</div>
        </div>
      ),
    },
    // 月份欄
    ...([1,2,3,4,5,6,7,8,9,10,11,12] as const).map((month) => ({
      title: (() => {
        const hrs = matrix?.month_hours?.[month]
        return (
          <div style={{ textAlign: 'center', fontSize: 11 }}>
            <div style={{ color: '#999', fontSize: 9 }}>{QUARTER_MAP[month]}</div>
            <div>{MONTH_LABELS[month]}</div>
            {hrs !== undefined && (
              <div style={{ fontSize: 9, color: '#4BA8E8', marginTop: 1 }}>
                {hrs.toFixed(2)}hr
              </div>
            )}
          </div>
        )
      })(),
      key: `m${month}`,
      width: 76,
      render: (_: unknown, row: MatrixRoom) => {
        const cell = row.cells[String(month)]
        return (
          <MatrixCellComp
            cell={cell}
            month={month}
            onClick={() => {
              if (cell) handleCellClick(cell.ragic_id, row.room_no, month)
            }}
          />
        )
      },
    })),
  ]

  // ── KPI 卡顏色 ───────────────────────────────────────────────────────────
  const kpiCards = stats
    ? [
        { title: '全年應保養', value: stats.total_scheduled, color: '#1B3A5C', icon: <HomeOutlined /> },
        { title: '已完成',     value: stats.completed,       color: '#52c41a', icon: <CheckCircleOutlined /> },
        { title: '異常',       value: stats.abnormal,        color: '#d46b08', icon: <WarningOutlined /> },
        { title: '待保養',     value: stats.pending,         color: '#8c8c8c', icon: <ClockCircleOutlined /> },
        { title: '完成率',     value: `${stats.completion_rate}%`, color: '#4BA8E8', icon: <CheckCircleOutlined /> },
      ]
    : []

  return (
    <div style={{ padding: '0 4px' }}>
      {/* ── Breadcrumb ─────────────────────────────────────────────── */}
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <HomeOutlined /> },
          { title: NAV_GROUP.hotel },
          { title: NAV_PAGE.ihgRoomMaintenance },
        ]}
      />

      {/* ── 標題列 ─────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          {NAV_PAGE.ihgRoomMaintenance}
        </Title>
        <Button
          type="primary"
          icon={syncing ? <SyncOutlined spin /> : <SyncOutlined />}
          loading={syncing}
          onClick={handleSync}
        >
          同步 Ragic
        </Button>
      </div>

      {/* ── KPI 統計卡 ─────────────────────────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {kpiCards.map((k) => (
          <Col key={k.title} xs={12} sm={8} md={6} lg={4}>
            <Card size="small" style={{ borderTop: `3px solid ${k.color}` }}>
              <Statistic
                title={<span style={{ fontSize: 12 }}>{k.icon} {k.title}</span>}
                value={k.value}
                valueStyle={{ color: k.color, fontSize: 22 }}
              />
            </Card>
          </Col>
        ))}
        {stats && (
          <Col xs={24} sm={24} md={6} lg={4}>
            <Card size="small" style={{ borderTop: '3px solid #faad14', height: '100%', display: 'flex', alignItems: 'center' }}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                最後同步：{stats.synced_at ? dayjs(stats.synced_at).format('MM/DD HH:mm') : '尚未同步'}
              </Text>
            </Card>
          </Col>
        )}
      </Row>

      {/* ── 篩選列 ─────────────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>年度</Text>
            <Select
              value={year}
              onChange={setYear}
              options={YEAR_OPTIONS}
              style={{ width: 110, marginLeft: 8 }}
              size="small"
            />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>樓層</Text>
            <Select
              allowClear
              placeholder="全部樓層"
              value={floorFilter || undefined}
              onChange={(v) => setFloorFilter(v ?? '')}
              options={floorOptions}
              style={{ width: 110, marginLeft: 8 }}
              size="small"
            />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>狀態</Text>
            <Select
              allowClear
              placeholder="全部狀態"
              value={statusFilter || undefined}
              onChange={(v) => setStatusFilter(v ?? '')}
              options={[
                { value: 'completed', label: '已完成' },
                { value: 'abnormal',  label: '異常' },
                { value: 'scheduled', label: '本月應保養' },
                { value: 'pending',   label: '待保養' },
              ]}
              style={{ width: 130, marginLeft: 8 }}
              size="small"
            />
          </Col>
          <Col>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => { setRoomFilter(''); setFloorFilter(''); setStatusFilter('') }}
            >
              清除篩選
            </Button>
          </Col>
          <Col>
            <Segmented
              size="small"
              value={viewMode}
              onChange={(v) => {
                const newParams = new URLSearchParams(searchParams)
                if (v === 'quarter') {
                  newParams.set('view', 'quarter')
                } else {
                  newParams.delete('view')
                }
                setSearchParams(newParams)
              }}
              options={[
                { label: '月份', value: 'month' },
                { label: '季度', value: 'quarter' },
              ]}
            />
          </Col>
          <Col flex={1} style={{ textAlign: 'right' }}>
            {/* 圖例 */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              {(Object.entries(STATUS_CFG) as [CellStatus, typeof STATUS_CFG[CellStatus]][]).map(([k, v]) => (
                <span key={k} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                  <span style={{ width: 12, height: 12, background: v.bg, border: `1px solid ${v.text}66`, borderRadius: 2, display: 'inline-block' }} />
                  <span style={{ color: v.text }}>{v.label}</span>
                </span>
              ))}
            </div>
          </Col>
        </Row>
      </Card>

      {/* ── 矩陣表 ─────────────────────────────────────────────────── */}
      <Spin spinning={loading}>
        <Card
          size="small"
          title={
            <span style={{ fontSize: 13 }}>
              {year} 年度客房保養矩陣
              <span style={{ marginLeft: 8, fontSize: 11, color: '#4BA8E8', fontWeight: 400 }}>
                {viewMode === 'quarter' ? '季度視角' : '月份視角'}
              </span>
              {matrix && (
                <Text type="secondary" style={{ marginLeft: 12, fontSize: 11 }}>
                  共 {matrix.rooms.length} 個房號
                </Text>
              )}
            </span>
          }
        >
          {matrix && matrix.rooms.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>
              尚無資料，請點擊「同步 Ragic」載入資料
            </div>
          ) : viewMode === 'quarter' ? (
            <Table
              columns={quarterColumns}
              dataSource={quarterRooms}
              rowKey="room_no"
              size="small"
              pagination={false}
              scroll={{ x: 'max-content', y: 'calc(100vh - 340px)' }}
              sticky
              loading={loading}
              style={{ fontSize: 12 }}
            />
          ) : (
            <Table
              columns={columns}
              dataSource={matrix?.rooms ?? []}
              rowKey="room_no"
              size="small"
              pagination={false}
              scroll={{ x: 'max-content', y: 'calc(100vh - 340px)' }}
              sticky
              loading={loading}
              rowClassName={(_, index) => index % 2 === 0 ? '' : 'ant-table-row-striped'}
              style={{ fontSize: 12 }}
            />
          )}
        </Card>
      </Spin>

      {/* ── 保養明細 Drawer（右側滑入）────────────────────────────── */}
      <Drawer
        title={
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ToolOutlined style={{ color: '#1B3A5C' }} />
            {drawerCell
              ? `${drawerCell.room_no}  ${MONTH_LABELS[drawerCell.month]}保養明細`
              : '保養明細'}
          </span>
        }
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={520}
        destroyOnClose
      >
        {drawerLoading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin tip="載入中..." />
          </div>
        ) : drawerRecord ? (
          <>
            <Descriptions
              column={1}
              bordered
              size="small"
              labelStyle={{ width: 100, fontWeight: 500, background: '#f8f9fb' }}
              style={{ marginBottom: 16 }}
            >
              <Descriptions.Item label="房號">
                <strong>{drawerRecord.room_no}</strong>
                <span style={{ marginLeft: 8, color: '#999', fontSize: 12 }}>
                  {drawerRecord.floor}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="保養年月">
                {drawerRecord.maint_year}/{drawerRecord.maint_month}
              </Descriptions.Item>
              <Descriptions.Item label="保養日期">
                {drawerRecord.maint_date || '—'}
              </Descriptions.Item>

              <Descriptions.Item label="完成日期">
                {drawerRecord.completion_date || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="保養人員">
                {drawerRecord.assignee_name || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="複核人員">
                {drawerRecord.checker_name || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="保養類型">
                {drawerRecord.maint_type || '—'}
              </Descriptions.Item>
              {drawerRecord.raw_fields?.['工時計算'] !== undefined && (
                <Descriptions.Item label="工時計算">
                  {String(drawerRecord.raw_fields['工時計算']) || '—'}
                  <span style={{ marginLeft: 4, fontSize: 11, color: '#8c8c8c' }}>分鐘</span>
                </Descriptions.Item>
              )}
              {drawerRecord.notes && (
                <Descriptions.Item label="備註">
                  <span style={{ whiteSpace: 'pre-wrap' }}>{drawerRecord.notes}</span>
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* 子表格保養項目（Ragic 保養明細無「狀態/結果」欄，僅顯示項目與備註）*/}
            {drawerRecord.details.length > 0 && (
              <>
                <Divider orientation="left" style={{ fontSize: 12 }}>
                  保養項目明細
                </Divider>
                <Table
                  size="small"
                  dataSource={drawerRecord.details}
                  rowKey="ragic_id"
                  pagination={false}
                  style={{ marginBottom: 16 }}
                  columns={[
                    { title: '#', dataIndex: 'seq_no', key: 'seq', width: 36 },
                    { title: '項目', dataIndex: 'task_name', key: 'task' },
                    { title: '備註', dataIndex: 'notes', key: 'notes', ellipsis: true },
                  ]}
                />
              </>
            )}

            {/* 維護異常項目表格（有「等待維護(待料中)」欄位時才顯示，含 ALL/正常/完成/維護 篩選）*/}
            <CheckItemsPanel rawFields={drawerRecord.raw_fields} />

            {/* Ragic 原始欄位（欄位 mapping 確認用）*/}
            {Object.keys(drawerRecord.raw_fields).length > 0 && (
              <>
                <Divider orientation="left" style={{ fontSize: 12, color: '#999' }}>
                  Ragic 原始欄位（mapping 確認）
                </Divider>
                <div
                  style={{
                    maxHeight: 220, overflowY: 'auto', background: '#fafafa',
                    padding: 8, borderRadius: 4, fontSize: 11, fontFamily: 'monospace',
                    border: '1px solid #f0f0f0',
                  }}
                >
                  {Object.entries(drawerRecord.raw_fields).map(([k, v]) => (
                    <div key={k} style={{ marginBottom: 3, lineHeight: 1.6 }}>
                      <span style={{ color: '#4BA8E8' }}>{k}</span>
                      <span style={{ color: '#bbb' }}> = </span>
                      <span style={{ color: '#555' }}>{JSON.stringify(v)}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #f0f0f0' }}>
              <Text type="secondary" style={{ fontSize: 11 }}>
                Ragic ID：{drawerRecord.ragic_id}
                {drawerRecord.synced_at && (
                  <> ｜ 同步：{dayjs(drawerRecord.synced_at).format('MM/DD HH:mm')}</>
                )}
              </Text>
            </div>
          </>
        ) : (
          <div style={{ textAlign: 'center', color: '#999', padding: 40 }}>
            無法載入資料
          </div>
        )}
      </Drawer>

      {/* ── 季度彙整 Drawer ────────────────────────────────────────── */}
      <Drawer
        title={
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ToolOutlined style={{ color: '#1B3A5C' }} />
            {qDrawerData
              ? `${qDrawerData.room_no}  ${qDrawerData.qname} 季度彙整`
              : '季度彙整'}
          </span>
        }
        open={qDrawerOpen}
        onClose={() => setQDrawerOpen(false)}
        width={480}
        destroyOnClose
      >
        {qDrawerData && (
          <>
            {/* 季度合計摘要 */}
            <Descriptions
              column={2}
              bordered
              size="small"
              labelStyle={{ width: 80, fontWeight: 500, background: '#f8f9fb' }}
              style={{ marginBottom: 16 }}
            >
              <Descriptions.Item label="房號" span={2}>
                <strong>{qDrawerData.room_no}</strong>
              </Descriptions.Item>
              <Descriptions.Item label="季度">
                <Tag color={STATUS_CFG[qDrawerData.qdata.status].tagColor}>
                  {STATUS_CFG[qDrawerData.qdata.status].icon}{' '}
                  {STATUS_CFG[qDrawerData.qdata.status].label}
                </Tag>
                <span style={{ marginLeft: 6, fontWeight: 600 }}>{qDrawerData.qname}</span>
              </Descriptions.Item>
              <Descriptions.Item label="工時合計">
                {qDrawerData.qdata.work_minutes_total > 0
                  ? `${(qDrawerData.qdata.work_minutes_total / 60).toFixed(2)} hr`
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="正常">
                {qDrawerData.qdata.normal_total}
              </Descriptions.Item>
              <Descriptions.Item label="完成">
                {qDrawerData.qdata.done_total}
              </Descriptions.Item>
              <Descriptions.Item label="維護">
                <span style={{
                  color: qDrawerData.qdata.maint_total > 0 ? '#d46b08' : undefined,
                  fontWeight: qDrawerData.qdata.maint_total > 0 ? 700 : undefined,
                }}>
                  {qDrawerData.qdata.maint_total}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="未檢查">
                <span style={{
                  color: qDrawerData.qdata.unchecked_total > 0 ? '#faad14' : undefined,
                  fontWeight: qDrawerData.qdata.unchecked_total > 0 ? 700 : undefined,
                }}>
                  {qDrawerData.qdata.unchecked_total}
                </span>
              </Descriptions.Item>
            </Descriptions>

            <Divider orientation="left" style={{ fontSize: 12 }}>各月份明細</Divider>

            <Table
              size="small"
              dataSource={qDrawerData.qdata.active_cells}
              rowKey="month"
              pagination={false}
              style={{ marginBottom: 16 }}
              columns={[
                {
                  title: '月份',
                  dataIndex: 'month',
                  key: 'month',
                  width: 56,
                  render: (m: number) => <strong>{MONTH_LABELS[m]}</strong>,
                },
                {
                  title: '狀態',
                  key: 'status',
                  width: 100,
                  render: (_: unknown, row: { month: number; cell: MatrixCell }) => {
                    const cfg = STATUS_CFG[row.cell.status]
                    return <Tag color={cfg.tagColor}>{cfg.icon} {cfg.label}</Tag>
                  },
                },
                {
                  title: '正/完/維/未',
                  key: 'counts',
                  render: (_: unknown, row: { month: number; cell: MatrixCell }) => (
                    <span style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
                      {row.cell.normal_count}/{row.cell.done_count}/
                      <span style={{ color: (row.cell.maint_count ?? 0) > 0 ? '#d46b08' : undefined, fontWeight: (row.cell.maint_count ?? 0) > 0 ? 700 : undefined }}>
                        {row.cell.maint_count ?? 0}
                      </span>/
                      <span style={{ color: (row.cell.unchecked_count ?? 0) > 0 ? '#faad14' : undefined, fontWeight: (row.cell.unchecked_count ?? 0) > 0 ? 700 : undefined }}>
                        {row.cell.unchecked_count ?? 0}
                      </span>
                    </span>
                  ),
                },
                {
                  title: '工時',
                  key: 'work',
                  width: 58,
                  render: (_: unknown, row: { month: number; cell: MatrixCell }) =>
                    row.cell.work_minutes ? (
                      <span style={{ color: '#4BA8E8', fontSize: 11 }}>{row.cell.work_minutes}m</span>
                    ) : '—',
                },
                {
                  title: '',
                  key: 'action',
                  width: 52,
                  render: (_: unknown, row: { month: number; cell: MatrixCell }) => (
                    <Button
                      type="link"
                      size="small"
                      style={{ padding: 0 }}
                      onClick={() => {
                        setQDrawerOpen(false)
                        handleCellClick(row.cell.ragic_id, qDrawerData.room_no, row.month)
                      }}
                    >
                      查看
                    </Button>
                  ),
                },
              ]}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}
