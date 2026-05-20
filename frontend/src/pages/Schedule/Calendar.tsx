/**
 * 月曆式班表頁
 * 路由：/schedule/calendar
 * 呈現：縱向人員 × 橫向日期（類 Excel 班表格式）
 * 與 index.tsx 表格式相同，但獨立頁面，提供更大螢幕空間
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Button, Card, Col, Row, Select, Space, Spin, Table, Tag, Tooltip, Typography,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import {
  fetchSchedules, fetchScheduleTable,
  fetchShifts, fetchDepartments,
} from '@/api/schedule'
import type {
  Schedule, ScheduleTableData, ShiftType, Department,
} from '@/types/schedule'

const { Title } = Typography

const NOW = new Date()
const DEFAULT_YEAR  = NOW.getFullYear()
const DEFAULT_MONTH = NOW.getMonth() + 1
const MONTHS = Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1} 月`, value: i + 1 }))
const YEARS  = Array.from({ length: 5  }, (_, i) => {
  const y = DEFAULT_YEAR - 2 + i
  return { label: `${y} 年`, value: y }
})

export default function ScheduleCalendarPage() {
  const [year, setYear]   = useState(DEFAULT_YEAR)
  const [month, setMonth] = useState(DEFAULT_MONTH)

  const [schedules, setSchedules]   = useState<Schedule[]>([])
  const [shiftList, setShiftList]   = useState<ShiftType[]>([])
  const [deptList, setDeptList]     = useState<Department[]>([])
  const [tableData, setTableData]   = useState<ScheduleTableData | null>(null)
  const [loading, setLoading]       = useState(false)
  const [filterDept, setFilterDept] = useState<string | undefined>()

  const currentSchedule = schedules.find(
    s => s.schedule_year === year && s.schedule_month === month
  )

  const load = useCallback(async () => {
    const [sList, shList, dList] = await Promise.all([
      fetchSchedules({ year }),
      fetchShifts(),
      fetchDepartments(),
    ])
    setSchedules(sList)
    setShiftList(shList)
    setDeptList(dList)
  }, [year])

  const loadTable = useCallback(async () => {
    if (!currentSchedule) { setTableData(null); return }
    setLoading(true)
    try {
      const data = await fetchScheduleTable(currentSchedule.id)
      setTableData(data)
    } finally {
      setLoading(false)
    }
  }, [currentSchedule])

  useEffect(() => { load() }, [load])
  useEffect(() => { loadTable() }, [loadTable])

  const shiftColorMap: Record<string, string> = Object.fromEntries(
    shiftList.map(s => [s.code, s.color])
  )

  // ── 篩選部門 ─────────────────────────────────────────────
  const filteredRows = (tableData?.rows ?? []).filter(r =>
    !filterDept ||
    deptList.find(d => d.id === filterDept)?.name === r.department_name
  )

  // ── 動態欄位 ─────────────────────────────────────────────
  const buildColumns = () => {
    if (!tableData?.headers?.length) return []
    const { headers, days_in_month } = tableData

    const cols: any[] = [
      {
        title: '人員',
        dataIndex: 'staff_name',
        fixed: 'left',
        width: 120,
        render: (v: string, r: any) => (
          <div>
            <div style={{ fontWeight: 600 }}>{v}</div>
            {r.department_name && (
              <div style={{ fontSize: 11, color: '#6b7280' }}>{r.department_name}</div>
            )}
            {r.employment_type && r.employment_type !== '正職' && (
              <Tag color="orange" style={{ fontSize: 10 }}>{r.employment_type}</Tag>
            )}
          </div>
        ),
      },
    ]

    headers.forEach(h => {
      const isWeekend = h.weekday === '六' || h.weekday === '日'
      cols.push({
        title: (
          <div style={{ textAlign: 'center', lineHeight: 1.3, padding: '2px 0' }}>
            <div style={{ fontWeight: 700, fontSize: 12, color: isWeekend ? '#ef4444' : '#1e293b' }}>
              {h.day}
            </div>
            <div style={{ fontSize: 10, color: isWeekend ? '#ef4444' : '#94a3b8' }}>
              {h.weekday}
            </div>
          </div>
        ),
        key: `d${h.day}`,
        width: 44,
        align: 'center' as const,
        onHeaderCell: () => ({
          style: { background: isWeekend ? '#fef2f2' : undefined, padding: '4px 2px' },
        }),
        onCell: () => ({ style: { padding: '3px 2px' } }),
        render: (_: any, row: any) => {
          const cell = row.cells?.[h.day]
          if (!cell) {
            return (
              <div style={{
                width: 34, height: 24, borderRadius: 3,
                background: isWeekend ? '#fef2f2' : '#f8fafc',
              }} />
            )
          }
          return (
            <Tooltip title={`${cell.shift_code}（${(cell.work_minutes / 60).toFixed(0)}hr）`}>
              <Tag
                color={cell.color}
                style={{
                  minWidth: 34, textAlign: 'center', fontSize: 11,
                  fontWeight: 600, padding: '1px 4px', cursor: 'default',
                }}
              >
                {cell.shift_code}
              </Tag>
            </Tooltip>
          )
        },
      })
    })

    // 統計欄
    cols.push(
      {
        title: <div style={{ textAlign: 'center', fontSize: 11 }}>出勤</div>,
        dataIndex: 'work_days',
        fixed: 'right', width: 56, align: 'center' as const,
        render: (v: number) => <Tag color="blue" style={{ fontSize: 11 }}>{v}天</Tag>,
      },
      {
        title: <div style={{ textAlign: 'center', fontSize: 11 }}>工時</div>,
        dataIndex: 'work_minutes',
        fixed: 'right', width: 60, align: 'center' as const,
        render: (v: number) => (
          <span style={{ fontSize: 11, color: '#374151' }}>{(v / 60).toFixed(0)}hr</span>
        ),
      },
    )

    return cols
  }

  return (
    <div style={{ padding: '24px' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>月曆式班表</Title>
        </Col>
        <Col>
          <Space>
            <Select value={year} onChange={v => { setYear(v) }} style={{ width: 100 }} options={YEARS} />
            <Select value={month} onChange={v => { setMonth(v) }} style={{ width: 90 }} options={MONTHS} />
            <Select
              allowClear placeholder="部門篩選" style={{ width: 120 }}
              value={filterDept} onChange={setFilterDept}
              options={deptList.map(d => ({ label: d.name, value: d.id }))}
            />
            <Button icon={<ReloadOutlined />} onClick={loadTable}>重新整理</Button>
          </Space>
        </Col>
      </Row>

      <Card
        bodyStyle={{ padding: '8px 12px', overflowX: 'auto' }}
        title={
          currentSchedule
            ? `${year} 年 ${month} 月 — ${currentSchedule.title}`
            : `${year} 年 ${month} 月（無班表資料）`
        }
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
          </div>
        ) : !tableData?.schedule ? (
          <div style={{ textAlign: 'center', padding: 60, color: '#aaa' }}>
            {year} 年 {month} 月尚無班表，請先匯入 Excel 班表。
          </div>
        ) : (
          <>
            {/* 班別圖例 */}
            <div style={{ marginBottom: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {shiftList.filter(s => s.is_active).map(s => (
                <Tag key={s.code} color={s.color} style={{ fontWeight: 600 }}>
                  {s.code} {s.name} {s.start_time}–{s.end_time}
                </Tag>
              ))}
            </div>
            <Table
              rowKey="staff_name"
              columns={buildColumns()}
              dataSource={filteredRows}
              pagination={false}
              size="small"
              scroll={{
                x: Math.max(800, 120 + (tableData?.days_in_month ?? 31) * 44 + 120),
              }}
              bordered
              rowClassName={(_, idx) => idx % 2 === 0 ? '' : 'ant-table-row-level-1'}
            />
          </>
        )}
      </Card>
    </div>
  )
}
