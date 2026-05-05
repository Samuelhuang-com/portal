/**
 * MonthlyCalendarGrid — 通用月曆格元件
 *
 * 將任意「列 × 日」資料渲染成月曆格表格，供各模組 Dashboard 複用。
 *
 * 標準後端 cell 資料格式（各模組 GET /calendar 回傳）：
 *   { has_record, completion_rate, abnormal_count, pending_count }
 *
 * 使用範例（最簡）：
 *   <MonthlyCalendarGrid year={2026} month={5} maxDay={31} rows={calRows} />
 *
 * 使用範例（客製化 cell）：
 *   <MonthlyCalendarGrid
 *     year={2026} month={5} maxDay={31} rows={rows}
 *     rowHeaderLabel="類別"
 *     renderCell={(day, data) => data?.total ?? '—'}
 *   />
 */
import React from 'react'
import { Row, Col, Space, Tooltip, Typography } from 'antd'
import dayjs from 'dayjs'

const { Text } = Typography

// ── 標準 cell 資料型別 ────────────────────────────────────────────────────────

export interface CalendarCellData {
  has_record:      boolean
  completion_rate: number
  abnormal_count:  number
  pending_count:   number
}

export interface CalendarRow {
  key:   string
  label: string
  daily: Record<string, CalendarCellData>   // key = "1" ~ "31"
}

// ── 圖例項目型別 ──────────────────────────────────────────────────────────────

export interface LegendItem {
  dot:   string
  color: string
  label: string
  bg:    string
}

// ── 預設圖例 ──────────────────────────────────────────────────────────────────

export const DEFAULT_LEGEND: LegendItem[] = [
  { dot: '✓', color: '#52C41A', label: '完成',       bg: '#f6ffed' },
  { dot: '⚠', color: '#FF4D4F', label: '有異常/待處理', bg: '#fff1f0' },
  { dot: '●', color: '#4BA8E8', label: '進行中',     bg: '#e6f7ff' },
  { dot: '—', color: '#ccc',    label: '無紀錄',     bg: '#fff'    },
]

// ── 預設 cellStyle ────────────────────────────────────────────────────────────

export function defaultCellStyle(
  _day: number,
  data: CalendarCellData | undefined,
): React.CSSProperties {
  if (!data?.has_record) return {}
  if (data.abnormal_count > 0 || data.pending_count > 0) return { background: '#fff1f0' }
  if (data.completion_rate >= 100) return { background: '#f6ffed' }
  return { background: '#e6f7ff' }
}

// ── 預設 renderCell ───────────────────────────────────────────────────────────

export function defaultRenderCell(
  _day: number,
  data: CalendarCellData | undefined,
): React.ReactNode {
  if (!data?.has_record) {
    return <span style={{ color: '#ccc', fontSize: 14 }}>—</span>
  }
  if (data.abnormal_count > 0 || data.pending_count > 0) {
    return (
      <Tooltip
        title={`異常 ${data.abnormal_count} 待處理 ${data.pending_count} 完成率 ${data.completion_rate}%`}
      >
        <span style={{ color: '#FF4D4F', fontSize: 16, cursor: 'default' }}>⚠</span>
      </Tooltip>
    )
  }
  if (data.completion_rate >= 100) {
    return (
      <Tooltip title="完成率 100%">
        <span style={{ color: '#52C41A', fontSize: 14, cursor: 'default' }}>✓</span>
      </Tooltip>
    )
  }
  return (
    <Tooltip title={`完成率 ${data.completion_rate}%`}>
      <span style={{ color: '#4BA8E8', fontSize: 12, cursor: 'default' }}>
        {data.completion_rate}%
      </span>
    </Tooltip>
  )
}

// ── Props ─────────────────────────────────────────────────────────────────────

export interface MonthlyCalendarGridProps {
  year:            number
  month:           number
  maxDay:          number
  rows:            CalendarRow[]
  rowHeaderLabel?: string                                                     // 預設「巡檢區域」
  renderCell?:     (day: number, data: CalendarCellData | undefined) => React.ReactNode
  cellStyle?:      (day: number, data: CalendarCellData | undefined) => React.CSSProperties
  legend?:         LegendItem[]                                               // 傳 [] 可隱藏圖例
}

// ── 主元件 ────────────────────────────────────────────────────────────────────

export default function MonthlyCalendarGrid({
  year,
  month,
  maxDay,
  rows,
  rowHeaderLabel = '巡檢區域',
  renderCell     = defaultRenderCell,
  cellStyle      = defaultCellStyle,
  legend         = DEFAULT_LEGEND,
}: MonthlyCalendarGridProps) {
  const days        = Array.from({ length: maxDay }, (_, i) => i + 1)
  const todayYear   = dayjs().year()
  const todayMonth  = dayjs().month() + 1
  const todayDay    = dayjs().date()

  const isWeekend = (day: number) => {
    const d = new Date(year, month - 1, day)
    return d.getDay() === 0 || d.getDay() === 6
  }

  const isToday = (day: number) =>
    year === todayYear && month === todayMonth && day === todayDay

  return (
    <div>
      {/* 表格 */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{
          borderCollapse: 'collapse',
          tableLayout:    'fixed',
          fontSize:       12,
          width:          '100%',
        }}>
          <thead>
            <tr>
              <th style={{
                width: '12%', minWidth: 80, textAlign: 'left', padding: '4px 8px',
                background: '#f0f4f8', border: '1px solid #e8e8e8',
                fontWeight: 600, color: '#1B3A5C',
              }}>
                {rowHeaderLabel}
              </th>
              {days.map((d) => (
                <th key={d} style={{
                  textAlign:  'center',
                  padding:    '3px 1px',
                  background: isToday(d) ? '#1B3A5C' : isWeekend(d) ? '#f9f0ff' : '#f0f4f8',
                  border:     '1px solid #e8e8e8',
                  color:      isToday(d) ? '#fff' : isWeekend(d) ? '#722ed1' : '#333',
                  fontWeight: isToday(d) ? 700 : 400,
                  overflow:   'hidden',
                }}>
                  {d}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td style={{
                  padding:    '4px 8px',
                  border:     '1px solid #e8e8e8',
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                  background: '#fafafa',
                }}>
                  {row.label}
                </td>
                {days.map((d) => {
                  const data = row.daily[String(d)]
                  return (
                    <td key={d} style={{
                      textAlign: 'center',
                      padding:   '3px 1px',
                      border:    '1px solid #e8e8e8',
                      overflow:  'hidden',
                      ...cellStyle(d, data),
                    }}>
                      {renderCell(d, data)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 圖例 */}
      {legend.length > 0 && (
        <Row gutter={12} style={{ marginTop: 8 }}>
          {legend.map((item) => (
            <Col key={item.label}>
              <Space size={4}>
                <span style={{
                  display:     'inline-block',
                  width:       18,
                  height:      18,
                  lineHeight:  '18px',
                  textAlign:   'center',
                  background:  item.bg,
                  border:      '1px solid #e8e8e8',
                  fontSize:    12,
                  color:       item.color,
                  borderRadius: 2,
                }}>
                  {item.dot}
                </span>
                <Text type="secondary" style={{ fontSize: 11 }}>{item.label}</Text>
              </Space>
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}
