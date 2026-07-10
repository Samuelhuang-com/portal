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
  Drawer, Row, Select, Segmented, Spin, Statistic, Table, Tag, Tabs, Tooltip,
  Typography, message,
} from 'antd'
import {
  CalendarOutlined, CheckCircleOutlined, ClockCircleOutlined,
  FileExcelOutlined, HomeOutlined, LinkOutlined, QuestionCircleOutlined,
  ReloadOutlined, TableOutlined, ToolOutlined, UnorderedListOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

import {
  fetchIHGMatrix,
  fetchIHGStats,
  fetchIHGRecord,
  fetchIHGSectionMatrix,
  fetchIHGCalendar,
  fetchIHGRecords,
  getIHGMatrixExportUrl,
} from '@/api/ihgRoomMaintenance'
import { downloadFile } from '@/api/downloadFile'
import type {
  CellStatus,
  CategoryStat,
  IHGRecord,
  IHGStats,
  MatrixCell,
  MatrixRoom,
  SectionMatrixResponse,
  SectionRoom,
  SectionValue,
  IHGCalendarResponse,
  IHGCalendarDayCell,
  IHGListItem,
  IHGListResponse,
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

  // 同房同月多筆記錄：逐筆列出日期＋分鐘，並顯示合計
  const isMulti = (cell.records?.length ?? 0) > 1
  const dateLines = isMulti ? (
    <>
      {cell.records.map((r) => (
        <span key={r.ragic_id} style={{ fontSize: 11, color: '#999', lineHeight: 1.4, whiteSpace: 'nowrap' }}>
          {(r.date || '').replace(/^\d{4}\//, '')}
          {r.work_minutes ? ` (${r.work_minutes}m)` : ''}
        </span>
      ))}
      <span style={{ fontSize: 11, color: '#4BA8E8', fontWeight: 600, lineHeight: 1.4, whiteSpace: 'nowrap' }}>
        {cell.record_count}筆 合計 {cell.work_minutes ?? 0}m
      </span>
    </>
  ) : cell.date ? (
    <span style={{ fontSize: 11, color: '#999', lineHeight: 1.4 }}>
      {cell.date.replace(/^\d{4}\//, '')}
      {cell.work_minutes ? ` (${cell.work_minutes}m)` : ''}
    </span>
  ) : null

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
          {isMulti ? (
            <>
              {cell.records.map((r, i) => (
                <div key={r.ragic_id}>
                  第{i + 1}筆：{r.date}{r.work_minutes ? ` (${r.work_minutes}m)` : ''}
                </div>
              ))}
              <div>合計：{cell.record_count} 筆／{cell.work_minutes ?? 0}m</div>
            </>
          ) : (
            cell.date && <div>日期：{cell.date}{cell.work_minutes ? ` (${cell.work_minutes}m)` : ''}</div>
          )}
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
          minWidth: 76, minHeight: 58, background: cfg.bg,
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
            <span style={{ fontSize: 11, color: cfg.text, lineHeight: 1.4, fontWeight: 500, whiteSpace: 'nowrap' }}>
              正常 {cell.normal_count} / 完成 {cell.done_count}
            </span>
            <span style={{
              fontSize: 11,
              color: (cell.maint_count ?? 0) > 0 ? '#d46b08'
                   : (cell.unchecked_count ?? 0) > 0 ? '#faad14' : '#8c8c8c',
              fontWeight: ((cell.maint_count ?? 0) > 0 || (cell.unchecked_count ?? 0) > 0) ? 700 : 400,
              lineHeight: 1.4,
              whiteSpace: 'nowrap',
            }}>
              維護 {cell.maint_count ?? 0} / 未 {cell.unchecked_count ?? 0}
            </span>
            {dateLines}
          </>
        ) : (
          // 無計數資料時，退回 icon + 日期
          <>
            <span style={{ fontSize: 15, color: cfg.text }}>{cfg.icon}</span>
            {dateLines}
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

// ── KPI 明細列型別 ────────────────────────────────────────────────────────────
interface KpiDetailRow {
  room_no: string; floor: string; month: number
  ragic_id: string; status: CellStatus
  date: string; assignee: string; completion_date: string
  normal_count: number; done_count: number
  maint_count: number; unchecked_count: number
  work_minutes: number | null
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
        <span style={{ fontSize: 11, color: cfg.text, fontWeight: 600, lineHeight: 1.4, whiteSpace: 'nowrap' }}>
          正常 {qdata.normal_total} / 完成 {qdata.done_total}
        </span>
        <span style={{
          fontSize: 11, lineHeight: 1.4, whiteSpace: 'nowrap',
          color: qdata.maint_total > 0 ? '#d46b08' : qdata.unchecked_total > 0 ? '#faad14' : '#8c8c8c',
          fontWeight: (qdata.maint_total > 0 || qdata.unchecked_total > 0) ? 700 : 400,
        }}>
          維護 {qdata.maint_total} / 未 {qdata.unchecked_total}
        </span>
        {hrs && (
          <span style={{ fontSize: 11, color: '#4BA8E8', lineHeight: 1.4 }}>{hrs} hr</span>
        )}
        <span style={{ fontSize: 11, color: '#bbb', lineHeight: 1.4 }}>
          {qdata.active_cells.map(a => MONTH_LABELS[a.month]).join(' ')}
        </span>
      </div>
    </Tooltip>
  )
}

// ── 區段值色碼設定 ────────────────────────────────────────────────────────────
const SECTION_VALUE_CFG: Record<SectionValue, { bg: string; text: string; label: string }> = {
  V:  { bg: '#f6ffed', text: '#389e0d', label: '已完成'       },
  '▲': { bg: '#fff7e6', text: '#d46b08', label: '當時維護完成' },
  X:  { bg: '#fff1f0', text: '#cf1322', label: '待料中'       },
}

// ── 客房保養表明細 TAB ────────────────────────────────────────────────────────
function SectionMatrixTab({
  defaultYear,
  onCellClick,
}: {
  defaultYear: string
  onCellClick: (ragicId: string, roomNo: string, monthNum: number) => void
}) {
  const [year,  setYear]  = useState<string>(defaultYear)
  const [month, setMonth] = useState<string>(String(dayjs().month() + 1).padStart(2, '0'))
  const [floor, setFloor] = useState<string>('')
  const [data,  setData]  = useState<SectionMatrixResponse | null>(null)
  const [loading, setLoading] = useState(false)

  // 所有樓層選項（固定）
  const ALL_FLOORS = ['5F','6F','7F','8F','9F','10F']

  const monthOptions = Array.from({ length: 12 }, (_, i) => ({
    value: String(i + 1).padStart(2, '0'),
    label: `${i + 1} 月`,
  }))

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchIHGSectionMatrix({
        year,
        month,
        floor: floor || undefined,
      })
      setData(res)
    } catch {
      message.error('載入區段矩陣資料失敗')
    } finally {
      setLoading(false)
    }
  }, [year, month, floor])

  useEffect(() => { loadData() }, [loadData])

  const categories = data?.categories ?? []

  // ── 欄位定義 ──────────────────────────────────────────────────────────────
  const columns: ColumnsType<SectionRoom> = [
    {
      title: '房號',
      dataIndex: 'room_no',
      key: 'room_no',
      fixed: 'left',
      width: 72,
      render: (rn: string, row: SectionRoom) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: 14 }}>{rn}</div>
          <div style={{ fontSize: 11, color: '#999' }}>{row.floor}</div>
        </div>
      ),
    },
    ...categories.map((cat) => ({
      title: (
        <div style={{ textAlign: 'center', fontSize: 12, lineHeight: 1.4 }}>
          <div style={{ fontWeight: 600 }}>{cat}</div>
        </div>
      ),
      key: cat,
      width: 88,
      render: (_: unknown, row: SectionRoom) => {
        // 無保養記錄的房間 → 未執行灰格
        if (!row.has_data) {
          return (
            <div
              style={{
                height: 36, background: '#f9f9f9', borderRadius: 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: '1px dashed #e0e0e0', color: '#bfbfbf', fontSize: 12,
              }}
            >
              未執行
            </div>
          )
        }
        const val = row.sections[cat] as SectionValue | undefined
        if (!val) {
          return (
            <div
              style={{
                height: 36, background: '#f5f5f5', borderRadius: 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, color: '#d9d9d9', border: '1px dashed #e8e8e8',
                cursor: 'pointer',
              }}
              onClick={() => row.ragic_id && onCellClick(row.ragic_id, row.room_no, Number(month))}
            >
              —
            </div>
          )
        }
        const cfg = SECTION_VALUE_CFG[val] ?? SECTION_VALUE_CFG['V']
        return (
          <Tooltip title={`${cat}：${cfg.label}（點擊查看明細）`}>
            <div
              style={{
                height: 36, background: cfg.bg, borderRadius: 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                border: `1px solid ${cfg.text}44`,
                fontWeight: 700, fontSize: 15, color: cfg.text,
                cursor: 'pointer',
                transition: 'box-shadow 0.15s',
              }}
              onClick={() => row.ragic_id && onCellClick(row.ragic_id, row.room_no, Number(month))}
              onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 8px rgba(0,0,0,0.18)' }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'none' }}
            >
              {val}
            </div>
          </Tooltip>
        )
      },
    })),
  ]

  // ── 統計摘要列 ────────────────────────────────────────────────────────────
  const renderSummary = () => {
    if (!data) return null
    const stats = data.category_stats
    return (
      <Table.Summary fixed="bottom">
        {/* 保養完成 TOTAL 列 */}
        <Table.Summary.Row style={{ background: '#f0f4f8', fontWeight: 600 }}>
          <Table.Summary.Cell index={0} colSpan={1}>
            <div style={{ fontSize: 11, color: '#1B3A5C', fontWeight: 700, textAlign: 'center' }}>
              完成<br />TOTAL
            </div>
          </Table.Summary.Cell>
          {categories.map((cat, i) => {
            const s: CategoryStat | undefined = stats[cat]
            return (
              <Table.Summary.Cell key={cat} index={i + 1}>
                <div style={{
                  textAlign: 'center', fontWeight: 700,
                  color: (s?.x_count ?? 0) > 0 ? '#cf1322'
                       : (s?.triangle_count ?? 0) > 0 ? '#d46b08' : '#389e0d',
                  fontSize: 14,
                }}>
                  {s?.v_count ?? 0}
                </div>
              </Table.Summary.Cell>
            )
          })}
        </Table.Summary.Row>
        {/* 完成率列 */}
        <Table.Summary.Row style={{ background: '#e6f4ff' }}>
          <Table.Summary.Cell index={0} colSpan={1}>
            <div style={{ fontSize: 11, color: '#1677ff', fontWeight: 700, textAlign: 'center' }}>
              完成率
            </div>
          </Table.Summary.Cell>
          {categories.map((cat, i) => {
            const s: CategoryStat | undefined = stats[cat]
            const rate = s?.rate ?? 0
            return (
              <Table.Summary.Cell key={cat} index={i + 1}>
                <div style={{
                  textAlign: 'center', fontWeight: 600,
                  color: rate >= 100 ? '#389e0d' : rate >= 80 ? '#d46b08' : '#cf1322',
                  fontSize: 12,
                }}>
                  {rate.toFixed(1)}%
                </div>
              </Table.Summary.Cell>
            )
          })}
        </Table.Summary.Row>
      </Table.Summary>
    )
  }

  return (
    <div>
      {/* 篩選列 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>年度</Text>
            <Select value={year} onChange={setYear}
              options={YEAR_OPTIONS} style={{ width: 110, marginLeft: 8 }} size="small" />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>月份</Text>
            <Select value={month} onChange={setMonth}
              options={monthOptions} style={{ width: 90, marginLeft: 8 }} size="small" />
          </Col>
          {/* 樓層快選按鈕 */}
          <Col>
            <Text type="secondary" style={{ fontSize: 12, marginRight: 8 }}>樓層</Text>
            {['', ...ALL_FLOORS].map((f) => (
              <Button
                key={f || 'all'}
                size="small"
                type={floor === f ? 'primary' : 'default'}
                onClick={() => setFloor(f)}
                style={{ marginRight: 4, minWidth: 42 }}
              >
                {f || '全部'}
              </Button>
            ))}
          </Col>
          <Col>
            <Button size="small" icon={<ReloadOutlined />}
              onClick={() => { setFloor(''); }}>清除篩選</Button>
          </Col>
          {/* 圖例 */}
          <Col flex={1}>
            <div style={{ display: 'flex', gap: 16, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              {(Object.entries(SECTION_VALUE_CFG) as [SectionValue, typeof SECTION_VALUE_CFG[SectionValue]][]).map(([k, v]) => (
                <span key={k} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                  <span style={{
                    width: 22, height: 22, background: v.bg, border: `1px solid ${v.text}66`,
                    borderRadius: 3, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    fontWeight: 700, color: v.text, fontSize: 12,
                  }}>{k}</span>
                  <span style={{ color: '#595959' }}>{v.label}</span>
                </span>
              ))}
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                <span style={{
                  width: 22, height: 22, background: '#f9f9f9', border: '1px dashed #e0e0e0',
                  borderRadius: 3, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  color: '#bfbfbf', fontSize: 11,
                }}>未執行</span>
                <span style={{ color: '#8c8c8c' }}>未執行</span>
              </span>
            </div>
          </Col>
        </Row>
      </Card>

      {/* 矩陣表 */}
      <Spin spinning={loading}>
        <Card
          size="small"
          title={
            <span style={{ fontSize: 13 }}>
              本月客房保養完成統計（{year} 年 {parseInt(month)} 月）
              {data && (
                <Text type="secondary" style={{ marginLeft: 12, fontSize: 11 }}>
                  共 {data.total_rooms} 間{data.rooms.filter(r => r.has_data).length !== data.total_rooms ? `，${data.rooms.filter(r => !r.has_data).length} 間未執行` : ''}
                </Text>
              )}
            </span>
          }
        >
          {data && data.rooms.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: '#999' }}>
              此月份尚無區段資料，請先同步 Ragic
            </div>
          ) : (
            <Table<SectionRoom>
              columns={columns}
              dataSource={data?.rooms ?? []}
              rowKey="room_no"
              size="small"
              pagination={false}
              scroll={{ x: 'max-content', y: 'calc(100vh - 360px)' }}
              sticky
              loading={loading}
              summary={renderSummary}
              rowClassName={(row, idx) =>
                !row.has_data ? 'ihg-row-no-data' : idx % 2 === 0 ? '' : 'ant-table-row-striped'
              }
            />
          )}
        </Card>
      </Spin>
    </div>
  )
}

// ── 月曆格 TAB ────────────────────────────────────────────────────────────────
function CalendarTab({
  defaultYear,
  defaultMonth,
  onRecordClick,
}: {
  defaultYear: string
  defaultMonth: string
  onRecordClick: (ragicId: string, roomNo: string) => void
}) {
  const [year,  setYear]  = useState<string>(defaultYear)
  const [month, setMonth] = useState<string>(defaultMonth)
  const [data,  setData]  = useState<IHGCalendarResponse | null>(null)
  const [loading, setLoading] = useState(false)

  // Cell Drawer：點擊某格後顯示該格所有記錄
  const [cellDrawer, setCellDrawer] = useState<{
    open: boolean
    floor: string
    day: string
    records: IHGListItem[]
    loading: boolean
  }>({ open: false, floor: '', day: '', records: [], loading: false })

  const monthOptions = Array.from({ length: 12 }, (_, i) => ({
    value: String(i + 1).padStart(2, '0'),
    label: `${i + 1} 月`,
  }))

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchIHGCalendar({ year, month })
      setData(res)
    } catch {
      message.error('載入月曆格資料失敗')
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => { loadData() }, [loadData])

  // 點擊格子
  const handleCellClick = async (floor: string, day: string, cell: IHGCalendarDayCell) => {
    if (!cell || cell.total === 0) return
    if (cell.ragic_ids.length === 1) {
      // 單筆直接開明細 Drawer
      onRecordClick(cell.ragic_ids[0], '')
      return
    }
    // 多筆先開清單 Drawer
    setCellDrawer({ open: true, floor, day, records: [], loading: true })
    try {
      const res = await fetchIHGRecords({
        year, month,
        floor: floor === 'TOTAL' ? undefined : floor,
        day,
        per_page: 100,
      })
      setCellDrawer(prev => ({ ...prev, records: res.data, loading: false }))
    } catch {
      message.error('載入記錄失敗')
      setCellDrawer(prev => ({ ...prev, loading: false }))
    }
  }

  const today = dayjs()
  const isCurrentMonth = Number(year) === today.year() && Number(month) === today.month() + 1
  const todayDay = isCurrentMonth ? today.date() : -1

  // 單格樣式
  const getCellCfg = (cell: IHGCalendarDayCell | undefined, day: number) => {
    const isFuture = isCurrentMonth && day > today.date()
    if (!cell || cell.total === 0) return { bg: 'transparent', text: '#bfbfbf', border: '1px dashed #e0e0e0', isFuture: false, isEmpty: true }
    if (isFuture) return { bg: '#fafafa', text: '#bfbfbf', border: '1px dashed #d9d9d9', isFuture: true, isEmpty: false }
    if (cell.abnormal > 0) return { bg: '#fff7e6', text: '#d46b08', border: '1px solid #ffc069', isFuture: false, isEmpty: false }
    if (cell.completed === cell.total) return { bg: '#f6ffed', text: '#52c41a', border: '1px solid #b7eb8f', isFuture: false, isEmpty: false }
    return { bg: '#e6f4ff', text: '#1677ff', border: '1px solid #91caff', isFuture: false, isEmpty: false }
  }

  if (!data && loading) {
    return <div style={{ padding: 60, textAlign: 'center' }}><Spin tip="載入中..." /></div>
  }

  const { max_day = 31, floors = [], kpi = { total_rooms: 0, completed: 0, abnormal: 0, pending: 0, completion_rate: 0 }, calendar = {} } = data ?? {}
  const days = Array.from({ length: max_day }, (_, i) => i + 1)
  const rowKeys = [...floors, 'TOTAL']

  return (
    <div>
      {/* ── KPI 卡 ──────────────────────────────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        {[
          { label: '本月應保養', value: kpi.total_rooms,      color: '#1B3A5C' },
          { label: '已完成',     value: kpi.completed,        color: '#52c41a' },
          { label: '異常',       value: kpi.abnormal,         color: '#d46b08' },
          { label: '待保養',     value: kpi.pending,          color: '#8c8c8c' },
          { label: '完成率',     value: `${kpi.completion_rate}%`, color: '#4BA8E8' },
        ].map(k => (
          <Col key={k.label} xs={12} sm={8} md={6} lg={4}>
            <Card size="small" style={{ borderTop: `3px solid ${k.color}` }}>
              <Statistic
                title={<span style={{ fontSize: 12 }}>{k.label}</span>}
                value={k.value}
                valueStyle={{ color: k.color, fontSize: 22 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* ── 篩選列 ──────────────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>年度</Text>
            <Select value={year} onChange={setYear} options={YEAR_OPTIONS}
              style={{ width: 110, marginLeft: 8 }} size="small" />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>月份</Text>
            <Select value={month} onChange={setMonth} options={monthOptions}
              style={{ width: 90, marginLeft: 8 }} size="small" />
          </Col>
          <Col flex={1}>
            <div style={{ display: 'flex', gap: 16, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              {([
                { bg: '#f6ffed', border: '#b7eb8f', text: '#52c41a', label: '全部完成' },
                { bg: '#e6f4ff', border: '#91caff', text: '#1677ff', label: '部分完成' },
                { bg: '#fff7e6', border: '#ffc069', text: '#d46b08', label: '異常'     },
                { bg: 'transparent', border: '#e0e0e0', text: '#bfbfbf', label: '無紀錄' },
              ] as const).map(l => (
                <span key={l.label} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                  <span style={{ width: 14, height: 14, background: l.bg, border: `1px solid ${l.border}`, borderRadius: 2, display: 'inline-block' }} />
                  <span style={{ color: l.text }}>{l.label}</span>
                </span>
              ))}
            </div>
          </Col>
        </Row>
      </Card>

      {/* ── 月曆格 ──────────────────────────────────────────────────── */}
      <Spin spinning={loading}>
        <Card size="small" style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', fontSize: 12, width: '100%', minWidth: `${64 + max_day * 46}px` }}>
            <thead>
              <tr>
                <th style={{
                  position: 'sticky', left: 0, background: '#f8f9fb', zIndex: 2,
                  padding: '6px 10px', border: '1px solid #e8e8e8',
                  fontWeight: 700, minWidth: 64, textAlign: 'center',
                }}>
                  樓層
                </th>
                {days.map(d => (
                  <th key={d} style={{
                    padding: '4px 0', border: '1px solid #e8e8e8', minWidth: 44,
                    background: d === todayDay ? '#e6f4ff' : '#f8f9fb',
                    color:      d === todayDay ? '#1677ff' : '#595959',
                    fontWeight: d === todayDay ? 700 : 400,
                    textAlign: 'center',
                    outline: d === todayDay ? '2px solid #1677ff' : undefined,
                  }}>
                    {d}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowKeys.map(fl => {
                const isTotal = fl === 'TOTAL'
                return (
                  <tr key={fl} style={{ background: isTotal ? '#f0f4f8' : 'white' }}>
                    <td style={{
                      position: 'sticky', left: 0, zIndex: 1,
                      background: isTotal ? '#e8edf2' : '#fafafa',
                      border: '1px solid #e8e8e8',
                      padding: '4px 8px',
                      fontWeight: isTotal ? 700 : 600,
                      textAlign: 'center',
                      color: isTotal ? '#1B3A5C' : '#262626',
                    }}>
                      {isTotal ? '合計' : fl}
                    </td>
                    {days.map(d => {
                      const cell = calendar[fl]?.[String(d)]
                      const cfg = getCellCfg(cell, d)
                      return (
                        <td key={d} style={{ padding: '2px', border: '1px solid #f0f0f0', background: '#fff' }}>
                          {cell && cell.total > 0 ? (
                            <Tooltip title={
                              <div style={{ fontSize: 11 }}>
                                <div>共 {cell.total} 筆</div>
                                {cell.completed > 0 && <div style={{ color: '#95de64' }}>完成 {cell.completed}</div>}
                                {cell.abnormal  > 0 && <div style={{ color: '#ffc069' }}>異常 {cell.abnormal}</div>}
                                {cell.pending   > 0 && <div style={{ color: '#91caff' }}>待保養 {cell.pending}</div>}
                                {!cfg.isFuture && <div style={{ color: '#aaa', marginTop: 2 }}>點擊查看</div>}
                              </div>
                            }>
                              <div
                                onClick={() => !cfg.isFuture && handleCellClick(fl, String(d), cell)}
                                style={{
                                  height: 38, borderRadius: 3,
                                  background: cfg.bg,
                                  border: cfg.border,
                                  color: cfg.text,
                                  cursor: cfg.isFuture ? 'default' : 'pointer',
                                  display: 'flex', flexDirection: 'column',
                                  alignItems: 'center', justifyContent: 'center',
                                  lineHeight: 1.3, fontWeight: 600,
                                  transition: 'box-shadow 0.15s',
                                  opacity: cfg.isFuture ? 0.5 : 1,
                                }}
                                onMouseEnter={(e) => { if (!cfg.isFuture) (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 6px rgba(0,0,0,0.18)' }}
                                onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.boxShadow = 'none' }}
                              >
                                {cell.abnormal > 0 ? (
                                  <span style={{ fontSize: 14 }}>⚠</span>
                                ) : cell.completed === cell.total ? (
                                  <span style={{ fontSize: 14 }}>✓</span>
                                ) : (
                                  <span style={{ fontSize: 11 }}>{cell.completed}/{cell.total}</span>
                                )}
                              </div>
                            </Tooltip>
                          ) : (
                            <div style={{
                              height: 38, display: 'flex', alignItems: 'center', justifyContent: 'center',
                              color: '#e0e0e0', fontSize: 12,
                            }}>—</div>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Card>
      </Spin>

      {/* ── Cell Drawer（多筆清單）──────────────────────────────────── */}
      <Drawer
        title={
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Tag color="#1B3A5C" style={{ margin: 0 }}>IHG保養</Tag>
            {cellDrawer.floor === 'TOTAL' ? '合計' : cellDrawer.floor}
            ／{year}/{month}/{cellDrawer.day}
          </span>
        }
        open={cellDrawer.open}
        onClose={() => setCellDrawer(prev => ({ ...prev, open: false }))}
        width={520}
        destroyOnClose
      >
        {cellDrawer.loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin tip="載入中..." /></div>
        ) : (
          <Table<IHGListItem>
            size="small"
            dataSource={cellDrawer.records}
            rowKey="ragic_id"
            pagination={false}
            columns={[
              {
                title: '房號', dataIndex: 'room_no', key: 'room_no', width: 64,
                render: (rn: string, row: IHGListItem) => (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontWeight: 700 }}>{rn}</div>
                    <div style={{ fontSize: 11, color: '#999' }}>{row.floor}</div>
                  </div>
                ),
              },
              {
                title: '狀態', key: 'status', width: 88,
                render: (_: unknown, row: IHGListItem) => (
                  row.is_completed
                    ? <Tag color="success"><CheckCircleOutlined /> 已完成</Tag>
                    : <Tag color="default"><ClockCircleOutlined /> 未完成</Tag>
                ),
              },
              { title: '保養人員', dataIndex: 'assignee_name', key: 'assignee', ellipsis: true,
                render: (a: string) => a || '—' },
              {
                title: '工時(分)', dataIndex: 'work_minutes', key: 'wm', width: 72,
                render: (m: number | null) => m != null
                  ? <span style={{ color: '#4BA8E8', fontWeight: 600 }}>{m}</span> : '—',
              },
              {
                title: '', key: 'action', width: 52,
                render: (_: unknown, row: IHGListItem) => (
                  <Button type="link" size="small" style={{ padding: 0 }}
                    onClick={() => {
                      setCellDrawer(prev => ({ ...prev, open: false }))
                      onRecordClick(row.ragic_id, row.room_no)
                    }}>
                    查看
                  </Button>
                ),
              },
            ]}
          />
        )}
      </Drawer>
    </div>
  )
}

// ── 每日明細 TAB ──────────────────────────────────────────────────────────────
function DailyTab({
  defaultYear,
  defaultMonth,
  onRecordClick,
}: {
  defaultYear: string
  defaultMonth: string
  onRecordClick: (ragicId: string, roomNo: string) => void
}) {
  const [year,   setYear]   = useState<string>(defaultYear)
  const [month,  setMonth]  = useState<string>(defaultMonth)
  const [day,    setDay]    = useState<string>('')
  const [floor,  setFloor]  = useState<string>('')
  const [status, setStatus] = useState<string>('')
  const [data,   setData]   = useState<IHGListResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [page,   setPage]   = useState(1)
  const PER_PAGE = 50

  const monthOptions = Array.from({ length: 12 }, (_, i) => ({
    value: String(i + 1).padStart(2, '0'),
    label: `${i + 1} 月`,
  }))

  const maxDay = dayjs(`${year}-${month}-01`).daysInMonth()
  const dayOptions = Array.from({ length: maxDay }, (_, i) => ({
    value: String(i + 1),
    label: `${i + 1} 日`,
  }))

  const ALL_FLOORS = ['5F','6F','7F','8F','9F','10F']

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchIHGRecords({
        year,
        month,
        day:     day    || undefined,
        floor:   floor  || undefined,
        status:  status || undefined,
        page,
        per_page: PER_PAGE,
      })
      setData(res)
    } catch {
      message.error('載入每日明細失敗')
    } finally {
      setLoading(false)
    }
  }, [year, month, day, floor, status, page])

  // 篩選條件變更時重置頁碼
  useEffect(() => { setPage(1) }, [year, month, day, floor, status])
  useEffect(() => { loadData() }, [loadData])

  const dailyCols: ColumnsType<IHGListItem> = [
    {
      title: '房號', dataIndex: 'room_no', key: 'room_no', width: 68, fixed: 'left',
      render: (rn: string, row: IHGListItem) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{rn}</div>
          <div style={{ fontSize: 11, color: '#999' }}>{row.floor}</div>
        </div>
      ),
    },
    {
      title: '保養日期', dataIndex: 'maint_date', key: 'date', width: 100,
      render: (d: string) => d || '—',
    },
    {
      title: '狀態', key: 'status', width: 92,
      render: (_: unknown, row: IHGListItem) => (
        row.is_completed
          ? <Tag color="success"><CheckCircleOutlined /> 已完成</Tag>
          : <Tag color="default"><ClockCircleOutlined /> 未完成</Tag>
      ),
    },
    {
      title: '保養人員', dataIndex: 'assignee_name', key: 'assignee', ellipsis: true,
      render: (a: string) => a || '—',
    },
    {
      title: '開始時間', dataIndex: 'start_time', key: 'start', width: 90,
      render: (t: string) => t || '—',
    },
    {
      title: '結束時間', dataIndex: 'end_time', key: 'end', width: 90,
      render: (t: string) => t || '—',
    },
    {
      title: '工時(分)', dataIndex: 'work_minutes', key: 'wm', width: 80,
      render: (m: number | null) => m != null
        ? <span style={{ color: '#4BA8E8', fontWeight: 600 }}>{m}</span> : '—',
    },
    {
      title: '備注', dataIndex: 'notes', key: 'notes', ellipsis: true,
      render: (n: string) => n || '—',
    },
    {
      title: '', key: 'action', width: 52, fixed: 'right',
      render: (_: unknown, row: IHGListItem) => (
        <Button type="link" size="small" style={{ padding: 0 }}
          onClick={(e) => { e.stopPropagation(); onRecordClick(row.ragic_id, row.room_no) }}>
          查看
        </Button>
      ),
    },
  ]

  return (
    <div>
      {/* ── 篩選列 ──────────────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[12, 8]} align="middle">
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>年度</Text>
            <Select value={year} onChange={setYear} options={YEAR_OPTIONS}
              style={{ width: 110, marginLeft: 8 }} size="small" />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>月份</Text>
            <Select value={month} onChange={setMonth} options={monthOptions}
              style={{ width: 90, marginLeft: 8 }} size="small" />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>日期</Text>
            <Select
              allowClear
              value={day || undefined}
              onChange={v => setDay(v ?? '')}
              placeholder="全部"
              options={dayOptions}
              style={{ width: 90, marginLeft: 8 }}
              size="small"
            />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>樓層</Text>
            <Select
              allowClear
              value={floor || undefined}
              onChange={v => setFloor(v ?? '')}
              placeholder="全部"
              options={ALL_FLOORS.map(f => ({ value: f, label: f }))}
              style={{ width: 90, marginLeft: 8 }}
              size="small"
            />
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 12 }}>狀態</Text>
            <Select
              allowClear
              value={status || undefined}
              onChange={v => setStatus(v ?? '')}
              placeholder="全部"
              options={[
                { value: 'completed', label: '已完成' },
                { value: 'pending',   label: '未完成' },
              ]}
              style={{ width: 110, marginLeft: 8 }}
              size="small"
            />
          </Col>
          <Col>
            <Button size="small" icon={<ReloadOutlined />}
              onClick={() => { setDay(''); setFloor(''); setStatus('') }}>
              清除篩選
            </Button>
          </Col>
        </Row>
      </Card>

      {/* ── 列表 ────────────────────────────────────────────────────── */}
      <Spin spinning={loading}>
        <Card
          size="small"
          title={
            <span style={{ fontSize: 13 }}>
              每日保養明細
              {data && (
                <Text type="secondary" style={{ marginLeft: 12, fontSize: 11 }}>
                  共 {data.total} 筆
                </Text>
              )}
            </span>
          }
        >
          <Table<IHGListItem>
            columns={dailyCols}
            dataSource={data?.data ?? []}
            rowKey="ragic_id"
            size="small"
            loading={loading}
            scroll={{ x: 'max-content', y: 'calc(100vh - 380px)' }}
            pagination={{
              current: page,
              pageSize: PER_PAGE,
              total: data?.total ?? 0,
              onChange: setPage,
              showSizeChanger: false,
              showTotal: (t) => `共 ${t} 筆`,
            }}
            onRow={(row) => ({
              onClick: () => onRecordClick(row.ragic_id, row.room_no),
              style: { cursor: 'pointer' },
            })}
          />
        </Card>
      </Spin>
    </div>
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
  const [matrix, setMatrix]     = useState<{ rooms: MatrixRoom[]; floors: string[]; month_hours: Partial<Record<number, number>>; month_orders: Partial<Record<number, number>> } | null>(null)
  const [loading, setLoading]   = useState(false)

  // 月份 Drawer 狀態
  const [drawerOpen, setDrawerOpen]     = useState(false)
  const [drawerRecord, setDrawerRecord] = useState<IHGRecord | null>(null)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [drawerCell, setDrawerCell]     = useState<{ room_no: string; month: number } | null>(null)

  // 季度彙整 Drawer 狀態
  const [qDrawerOpen, setQDrawerOpen]   = useState(false)
  const [qDrawerData, setQDrawerData]   = useState<{ room_no: string; qname: QuarterName; qdata: QuarterCellData } | null>(null)

  // KPI 卡片點擊明細 Drawer 狀態
  const [kpiDrawer, setKpiDrawer] = useState<{
    open: boolean; title: string; color: string
    filter: string | null; loading: boolean; rows: KpiDetailRow[]
  }>({ open: false, title: '', color: '#1B3A5C', filter: null, loading: false, rows: [] })

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
      setMatrix({ rooms: m.rooms, floors: m.floors, month_hours: m.month_hours ?? {}, month_orders: m.month_orders ?? {} })
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

  // ── 點擊 KPI 卡片 → 展開對應狀態的房號明細 ─────────────────────────────
  const handleKpiClick = async (filter: string, title: string, color: string) => {
    setKpiDrawer({ open: true, title, color, filter, loading: true, rows: [] })
    try {
      const m = await fetchIHGMatrix({
        year,
        cell_status: filter === 'all' ? undefined : filter,
      })
      const rows: KpiDetailRow[] = []
      for (const room of m.rooms) {
        for (const [monthStr, cell] of Object.entries(room.cells)) {
          if (!cell) continue
          rows.push({
            room_no: room.room_no,
            floor:   room.floor,
            month:   Number(monthStr),
            ragic_id: cell.ragic_id,
            status:   cell.status,
            date:             cell.date,
            assignee:         cell.assignee,
            completion_date:  cell.completion_date,
            normal_count:     cell.normal_count    ?? 0,
            done_count:       cell.done_count      ?? 0,
            maint_count:      cell.maint_count     ?? 0,
            unchecked_count:  cell.unchecked_count ?? 0,
            work_minutes:     cell.work_minutes,
          })
        }
      }
      rows.sort((a, b) => {
        const na = parseInt(a.room_no), nb = parseInt(b.room_no)
        if (na !== nb) return na - nb
        return a.month - b.month
      })
      setKpiDrawer(prev => ({ ...prev, loading: false, rows }))
    } catch {
      message.error('載入明細失敗')
      setKpiDrawer(prev => ({ ...prev, loading: false }))
    }
  }

  // ── 月曆格 / 每日明細 TAB 使用的通用 Record 點擊（不需知道月份）──────────
  const handleRecordClick = useCallback(async (ragicId: string, roomNo: string) => {
    setDrawerCell({ room_no: roomNo, month: 0 })
    setDrawerOpen(true)
    setDrawerRecord(null)
    setDrawerLoading(true)
    try {
      const rec = await fetchIHGRecord(ragicId)
      setDrawerRecord(rec)
    } catch {
      message.error('載入明細失敗')
    } finally {
      setDrawerLoading(false)
    }
  }, [])

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
          <div style={{ fontWeight: 600, fontSize: 15 }}>{rn}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{row.floor}</div>
        </div>
      ),
    },
    ...(['Q1','Q2','Q3','Q4'] as QuarterName[]).map((qname) => {
      const qMonths = QUARTER_MONTHS_MAP[qname]
      const qHrs = qMonths.reduce((sum, m) => sum + (matrix?.month_hours?.[m] ?? 0), 0)
      return {
        title: (
          <div style={{ textAlign: 'center', fontSize: 13 }}>
            <div style={{ fontWeight: 600 }}>{qname}</div>
            <div style={{ color: '#999', fontSize: 11 }}>{qMonths.map(m => MONTH_LABELS[m]).join(' ')}</div>
            {qHrs > 0 && (
              <div style={{ fontSize: 11, color: '#4BA8E8', marginTop: 1 }}>
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
          <div style={{ fontWeight: 600, fontSize: 15 }}>{rn}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{row.floor}</div>
        </div>
      ),
    },
    // 月份欄
    ...([1,2,3,4,5,6,7,8,9,10,11,12] as const).map((month) => ({
      title: (() => {
        const hrs    = matrix?.month_hours?.[month]
        const orders = matrix?.month_orders?.[month]
        return (
          <div style={{ textAlign: 'center', fontSize: 13 }}>
            <div style={{ color: '#999', fontSize: 11 }}>{QUARTER_MAP[month]}</div>
            <div>{MONTH_LABELS[month]}</div>
            {hrs !== undefined && (
              <div style={{ fontSize: 11, color: '#4BA8E8', marginTop: 1 }}>
                {hrs.toFixed(2)}hr
              </div>
            )}
            {orders !== undefined && orders > 0 && (
              <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                {orders} 單
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
        { title: '全年應保養', value: stats.total_scheduled, color: '#1B3A5C', icon: <HomeOutlined />,        filter: 'all'       },
        { title: '已完成',     value: stats.completed,       color: '#52c41a', icon: <CheckCircleOutlined />, filter: 'completed' },
        { title: '異常',       value: stats.abnormal,        color: '#d46b08', icon: <WarningOutlined />,     filter: 'abnormal'  },
        { title: '待保養',     value: stats.pending,         color: '#8c8c8c', icon: <ClockCircleOutlined />, filter: 'pending'   },
        { title: '完成率',     value: `${stats.completion_rate}%`, color: '#4BA8E8', icon: <CheckCircleOutlined />, filter: null  },
      ]
    : []

  // ── KPI 明細 Table columns（定義在 return 外，避免在 JSX 內宣告造成 TS 解析混亂）──
  const kpiCols: ColumnsType<KpiDetailRow> = [
    {
      title: '房號', dataIndex: 'room_no', key: 'room_no', width: 64, fixed: 'left',
      render: (rn: string, row: KpiDetailRow) => (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{rn}</div>
          <div style={{ fontSize: 10, color: '#999' }}>{row.floor}</div>
        </div>
      ),
    },
    {
      title: '月份', dataIndex: 'month', key: 'month', width: 52,
      render: (m: number) => <strong>{MONTH_LABELS[m]}</strong>,
    },
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 100,
      render: (s: CellStatus) => {
        const cfg = STATUS_CFG[s] ?? STATUS_CFG.pending
        return <Tag color={cfg.tagColor}>{cfg.icon} {cfg.label}</Tag>
      },
    },
    {
      title: '正/完/維/未', key: 'counts', width: 100,
      render: (_: unknown, row: KpiDetailRow) => (
        <span style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
          {row.normal_count} ／ {row.done_count} ／{' '}
          <span style={{ color: row.maint_count > 0 ? '#d46b08' : undefined, fontWeight: row.maint_count > 0 ? 700 : undefined }}>
            {row.maint_count}
          </span>
          {' '}／{' '}
          <span style={{ color: row.unchecked_count > 0 ? '#faad14' : undefined, fontWeight: row.unchecked_count > 0 ? 700 : undefined }}>
            {row.unchecked_count}
          </span>
        </span>
      ),
    },
    { title: '保養日期', dataIndex: 'date', key: 'date', width: 100, render: (d: string) => d || '—' },
    { title: '完成日期', dataIndex: 'completion_date', key: 'completion_date', width: 100, render: (d: string) => d || '—' },
    { title: '保養人員', dataIndex: 'assignee', key: 'assignee', ellipsis: true, render: (a: string) => a || '—' },
    {
      title: '', key: 'action', width: 52, fixed: 'right',
      render: (_: unknown, row: KpiDetailRow) => (
        <Button type="link" size="small" style={{ padding: 0 }}
          onClick={() => { setKpiDrawer(prev => ({ ...prev, open: false })); handleCellClick(row.ragic_id, row.room_no, row.month) }}
        >查看</Button>
      ),
    },
  ]

  // ── 年度矩陣 TAB 內容（抽出避免 TypeScript JSX parser 巢狀解析問題）──────────
  const matrixTabContent = (
              <div>
      {/* ── KPI 統計卡 ─────────────────────────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 20 }}>
        {kpiCards.map((k) => (
          <Col key={k.title} xs={12} sm={8} md={6} lg={4}>
            <Card
              size="small"
              hoverable={!!k.filter}
              onClick={() => k.filter && handleKpiClick(k.filter, k.title, k.color)}
              style={{
                borderTop: `3px solid ${k.color}`,
                cursor: k.filter ? 'pointer' : 'default',
                transition: 'box-shadow 0.2s',
              }}
            >
              <Statistic
                title={
                  <span style={{ fontSize: 12 }}>
                    {k.icon} {k.title}
                    {k.filter && (
                      <span style={{ marginLeft: 6, fontSize: 10, color: '#bfbfbf', fontWeight: 400 }}>
                        點擊查看
                      </span>
                    )}
                  </span>
                }
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
            <Button
              size="small"
              icon={<FileExcelOutlined />}
              onClick={() =>
                downloadFile(
                  getIHGMatrixExportUrl({
                    year,
                    room_no: roomFilter || undefined,
                    floor: floorFilter || undefined,
                    cell_status: statusFilter || undefined,
                  }),
                  `IHG客房保養_年度矩陣_${year}.xlsx`,
                )
              }
            >
              匯出 Excel
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
              size="middle"
              pagination={false}
              scroll={{ x: 'max-content', y: 'calc(100vh - 340px)' }}
              sticky
              loading={loading}
              style={{ fontSize: 14 }}
            />
          ) : (
            <Table
              columns={columns}
              dataSource={matrix?.rooms ?? []}
              rowKey="room_no"
              size="middle"
              pagination={false}
              scroll={{ x: 'max-content', y: 'calc(100vh - 340px)' }}
              sticky
              loading={loading}
              rowClassName={(_, index) => index % 2 === 0 ? '' : 'ant-table-row-striped'}
              style={{ fontSize: 14 }}
            />
          )}
        </Card>
      </Spin>
      </div>
  )

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
      </div>

      {/* ── TABs ───────────────────────────────────────────────────── */}
      <Tabs
        defaultActiveKey="matrix"
        size="middle"
        destroyInactiveTabPane
        items={[
          {
            key: 'matrix',
            label: <span><ToolOutlined /> 年度矩陣</span>,
            children: matrixTabContent,
      },
      {
        key: 'section-matrix',
        label: <span><TableOutlined /> 客房保養表明細</span>,
        children: (
          <SectionMatrixTab
            defaultYear={year}
            onCellClick={(ragicId, roomNo, monthNum) => handleCellClick(ragicId, roomNo, monthNum)}
          />
        ),
      },
      {
        key: 'calendar',
        label: <span><CalendarOutlined /> 月曆格</span>,
        children: (
          <CalendarTab
            defaultYear={year}
            defaultMonth={String(dayjs().month() + 1).padStart(2, '0')}
            onRecordClick={handleRecordClick}
          />
        ),
      },
      {
        key: 'daily',
        label: <span><UnorderedListOutlined /> 每日明細</span>,
        children: (
          <DailyTab
            defaultYear={year}
            defaultMonth={String(dayjs().month() + 1).padStart(2, '0')}
            onRecordClick={handleRecordClick}
          />
        ),
      },
      ]}
    />

      {/* ── 保養明細 Drawer（右側滑入）────────────────────────────── */}
      <Drawer
        title={
          <span style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Tag color="#1B3A5C" style={{ margin: 0 }}>IHG保養</Tag>
            <span>IHG客房保養：{drawerRecord?.room_no || drawerCell?.room_no || '—'}</span>
            {drawerRecord?.ragic_url && (
              <a
                href={drawerRecord.ragic_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#4BA8E8', fontSize: 13, display: 'flex', alignItems: 'center', gap: 3 }}
                onClick={e => e.stopPropagation()}
              >
                <LinkOutlined /> 在 Ragic 查看
              </a>
            )}
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
            {/* ① 基本欄位 */}
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
              <Descriptions.Item label="狀態">
                {drawerRecord.is_completed
                  ? <Tag color="green">已完成</Tag>
                  : <Tag color="red">未完成</Tag>}
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
              <Descriptions.Item label="保養時間起">
                {drawerRecord.start_time
                  || String(drawerRecord.raw_fields?.['保養時間起'] ?? '')
                  || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="保養時間迄">
                {drawerRecord.end_time
                  || String(drawerRecord.raw_fields?.['保養時間迄'] ?? '')
                  || '—'}
              </Descriptions.Item>
              <Descriptions.Item label="工時">
                {drawerRecord.work_minutes != null
                  ? <span style={{ color: '#4BA8E8', fontWeight: 600 }}>{drawerRecord.work_minutes} 分鐘</span>
                  : drawerRecord.raw_fields?.['工時計算']
                    ? <span style={{ color: '#4BA8E8', fontWeight: 600 }}>{String(drawerRecord.raw_fields['工時計算'])}</span>
                    : '—'}
              </Descriptions.Item>
              {drawerRecord.notes && (
                <Descriptions.Item label="備註">
                  <span style={{ whiteSpace: 'pre-wrap' }}>{drawerRecord.notes}</span>
                </Descriptions.Item>
              )}
            </Descriptions>

            {/* ② 明細欄位（detail dict 逐項渲染）*/}
            {drawerRecord.detail && Object.keys(drawerRecord.detail).length > 0 && (
              <>
                <Divider orientation="left" style={{ fontSize: 12 }}>
                  Ragic 原始明細
                </Divider>
                <Descriptions
                  column={1}
                  bordered
                  size="small"
                  labelStyle={{ width: 100, fontWeight: 500, background: '#f8f9fb' }}
                  style={{ marginBottom: 16 }}
                >
                  {Object.entries(drawerRecord.detail).map(([k, v]) => {
                    // 狀態欄 → 彩色 Tag
                    if (k === '狀態') {
                      const color = v === '已完成' ? 'green' : v === '未完成' ? 'red' : 'default'
                      return (
                        <Descriptions.Item key={k} label={k}>
                          <Tag color={color}>{v || '—'}</Tag>
                        </Descriptions.Item>
                      )
                    }
                    // 費用欄 → $ 前綴
                    if (k.includes('費用') || k.includes('金額')) {
                      return (
                        <Descriptions.Item key={k} label={k}>
                          {v ? `$${v}` : '—'}
                        </Descriptions.Item>
                      )
                    }
                    // 總費用/工時/標題 → 粗體
                    const isBold = k.includes('工時') || k.includes('總費用')
                    return (
                      <Descriptions.Item key={k} label={k}>
                        {v
                          ? isBold
                            ? <strong style={{ color: '#4BA8E8' }}>{v}</strong>
                            : v
                          : '—'}
                      </Descriptions.Item>
                    )
                  })}
                </Descriptions>
              </>
            )}

            {/* 子表格保養項目 */}
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

            {/* 維護異常項目表格 */}
            <CheckItemsPanel rawFields={drawerRecord.raw_fields} />

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
      {/* ── KPI 明細 Drawer ────────────────────────────────────────────── */}
      <Drawer
        title={
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: kpiDrawer.color, display: 'inline-block',
            }} />
            {kpiDrawer.title}
            {!kpiDrawer.loading && (
              <span style={{ fontSize: 12, color: '#8c8c8c', fontWeight: 400, marginLeft: 4 }}>
                共 {kpiDrawer.rows.length} 筆
              </span>
            )}
          </span>
        }
        open={kpiDrawer.open}
        onClose={() => setKpiDrawer(prev => ({ ...prev, open: false }))}
        width={640}
        destroyOnClose
      >
        {kpiDrawer.loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin tip="載入中..." />
          </div>
        ) : kpiDrawer.rows.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#999', padding: 60 }}>
            此篩選條件無資料
          </div>
        ) : (
          <Table
            size="small"
            dataSource={kpiDrawer.rows}
            rowKey={(r: KpiDetailRow) => `${r.room_no}-${r.month}`}
            pagination={{ pageSize: 20, showSizeChanger: false, showTotal: (t) => `共 ${t} 筆` }}
            scroll={{ x: 560 }}
            columns={kpiCols}

          />
        )}
      </Drawer>
    </div>
  )
}