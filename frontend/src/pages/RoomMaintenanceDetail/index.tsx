/**
 * 客房保養明細頁面
 *
 * Tab 1「保養總表」— 執行主管視圖
 *   日期區間 → KPI 四卡 → 全房間表格（可點擊房號查看歷史）
 *   異常項次卡可點擊篩選 / 「未保養房號」按鈕切換顯示
 *
 * Tab 2「明細清單」— 作業人員視圖
 *   12 欄 X/V 明細表格，支援搜尋篩選
 *
 * RoomHistoryDrawer（右側抽屜）
 *   點擊任意房號 → 顯示近 12 個月「保養月曆」+ 完整記錄時間軸
 *   清楚呈現「X 月未保養、Y 月是否補齊」的追蹤資訊
 */
import { useEffect, useState, useCallback, useMemo } from 'react'
import {
  Table, Space, Button, Input, Row, Col, Card,
  Typography, message, Breadcrumb, Tag, Tooltip,
  Statistic, DatePicker, Tabs, Badge, Drawer,
  Timeline, Alert, Divider, Segmented, Select,
} from 'antd'
import {
  ReloadOutlined, HomeOutlined, SyncOutlined,
  SearchOutlined, ToolOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
  WarningOutlined, StopOutlined,
  CalendarOutlined, HistoryOutlined,
  MinusCircleOutlined, ClockCircleOutlined,
  RiseOutlined, FallOutlined, UserOutlined,
  TrophyOutlined, BarChartOutlined, DownloadOutlined,
  LineChartOutlined, TeamOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import dayjs from 'dayjs'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RcTooltip, ResponsiveContainer,
  ReferenceLine, LineChart, Line, Legend, Cell,
} from 'recharts'

import {
  fetchRoomDetailRecords,
  fetchRoomDetailSummary,
  fetchRoomHistory,
  fetchStaffHours,
  fetchMaintenanceStats,
  syncRoomDetailFromRagic,
} from '@/api/roomMaintenanceDetail'
import type {
  RoomMaintenanceDetailRecord,
  RoomSummaryRow,
  RoomSummaryStats,
  RoomMaintenanceDetailFilters,
  MonthlyMaintenanceSummary,
  RoomHistoryResponse,
  StaffHoursResponse,
  MaintenanceStatsResponse,
  ConsecutiveMissedRoom,
  RepeatedAbnormalRoom,
  FullyOkRoom,
} from '@/types/roomMaintenanceDetail'
import { CHECK_FIELD_LABELS, CHECK_FIELD_KEYS } from '@/types/roomMaintenanceDetail'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

// ═══════════════════════════════════════════════════════════════════
// 輔助函式 & 元件
// ═══════════════════════════════════════════════════════════════════

function CheckTag({ value }: { value: string | undefined | null }) {
  const v = (value || '').toUpperCase()
  if (v === 'V') return <Tag icon={<CheckCircleOutlined />} color="success" style={{ margin: 0 }}>V</Tag>
  if (v === 'X') return <Tag icon={<CloseCircleOutlined />} color="error" style={{ margin: 0 }}>X</Tag>
  return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
}

function parseMinutes(val: string | null | undefined): number {
  if (!val) return 0
  const m = val.match(/[\d.]+/)
  return m ? parseFloat(m[0]) : 0
}

function fmtMinutes(min: number): string {
  if (min <= 0) return '0 分鐘'
  if (min < 60) return `${min.toFixed(1)} 分鐘`
  const h = Math.floor(min / 60)
  const r = Math.round(min % 60)
  return `${h}h ${r}m (${min.toFixed(0)} 分)`
}

// ═══════════════════════════════════════════════════════════════════
// RoomHistoryDrawer — 房間保養歷史抽屜
// ═══════════════════════════════════════════════════════════════════

function RoomHistoryDrawer({
  open,
  onClose,
  historyData,
  loading,
}: {
  open: boolean
  onClose: () => void
  historyData: RoomHistoryResponse | null
  loading: boolean
}) {
  // ── Hooks 必須在所有 early return 之前 ──────────────────────────
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null)

  const { room, monthly_summary, records, stats } = historyData ?? {
    room: { floor: '', room_no: '' },
    monthly_summary: [],
    records: [],
    stats: { total_records: 0, last_serviced: null, consecutive_missed: 0, serviced_months: 0, total_months: 12 },
  }

  const selectedMonthRecords = useMemo(() => {
    if (!selectedMonth) return []
    return records.filter(r => r.maintain_date.startsWith(selectedMonth))
  }, [records, selectedMonth])

  const handleMonthClick = (monthLabel: string) => {
    setSelectedMonth(p => p === monthLabel ? null : monthLabel)
  }

  if (!historyData && !loading) return null

  // ── 月曆格子（可點擊） ───────────────────────────────────────────
  function MonthCell({ ms }: { ms: MonthlyMaintenanceSummary }) {
    const isSelected = selectedMonth === ms.month_label
    let bg = '#fafafa', borderColor = '#e8e8e8', textColor = '#aaa'
    let icon = <MinusCircleOutlined style={{ color: '#bbb', fontSize: 16 }} />

    if (ms.serviced) {
      bg = '#f6ffed'; borderColor = '#b7eb8f'; textColor = '#389e0d'
      icon = <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />
    } else if (!ms.is_current) {
      bg = '#fff2f0'; borderColor = '#ffa39e'; textColor = '#cf1322'
      icon = <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />
    }

    return (
      <Tooltip
        title={
          ms.serviced
            ? `${ms.month_label}：${ms.record_count} 筆，工時 ${ms.work_hours_sum} 分 — 點擊查看明細`
            : ms.is_current
            ? `${ms.month_label}：當月尚無記錄`
            : `${ms.month_label}：未保養`
        }
      >
        <div
          onClick={() => handleMonthClick(ms.month_label)}
          style={{
            background: bg,
            border: isSelected ? `2px solid #1B3A5C` : `1px solid ${borderColor}`,
            borderRadius: 6,
            padding: '6px 4px',
            textAlign: 'center',
            minWidth: 68,
            cursor: 'pointer',
            transition: 'all .15s',
            boxShadow: isSelected ? '0 2px 10px rgba(27,58,92,0.25)' : undefined,
            transform: isSelected ? 'scale(1.06)' : undefined,
          }}
        >
          <div style={{ fontSize: 11, color: isSelected ? '#1B3A5C' : textColor, fontWeight: 600, marginBottom: 2 }}>
            {ms.month_label}
          </div>
          {icon}
          {ms.serviced && (
            <div style={{ fontSize: 10, color: textColor, marginTop: 2 }}>
              {ms.record_count} 筆
            </div>
          )}
        </div>
      </Tooltip>
    )
  }

  // ── 記錄時間軸 ───────────────────────────────────────────────────
  const timelineItems = records.map((r) => {
    const abnormals = CHECK_FIELD_KEYS.filter(f => (r[f] || '').toUpperCase() === 'X')
    const hasX = abnormals.length > 0
    return {
      color: hasX ? 'red' : 'green',
      dot: hasX
        ? <WarningOutlined style={{ fontSize: 14, color: '#ff4d4f' }} />
        : <CheckCircleOutlined style={{ fontSize: 14, color: '#52c41a' }} />,
      children: (
        <div style={{
          background: hasX ? '#fff5f5' : '#f6ffed',
          border: `1px solid ${hasX ? '#ffa39e' : '#b7eb8f'}`,
          borderRadius: 6,
          padding: '8px 12px',
          marginBottom: 4,
        }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Text strong style={{ fontSize: 13 }}>{r.maintain_date}</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>{r.staff_name}</Text>
            </Col>
            <Col>
              <Text type="secondary" style={{ fontSize: 12 }}>{r.work_hours}</Text>
            </Col>
          </Row>
          {/* 異常項目 */}
          {hasX && (
            <div style={{ marginTop: 4 }}>
              <Text type="danger" style={{ fontSize: 11 }}>異常：</Text>
              <Space size={2} wrap>
                {abnormals.map(f => (
                  <Tag key={f} color="error" style={{ fontSize: 11, margin: 0 }}>
                    {CHECK_FIELD_LABELS[f]}
                  </Tag>
                ))}
              </Space>
            </div>
          )}
          {/* 全部 OK 簡顯 */}
          {!hasX && (
            <div style={{ marginTop: 2 }}>
              <Text style={{ fontSize: 11, color: '#52c41a' }}>
                ✓ 全 12 項正常
              </Text>
            </div>
          )}
        </div>
      ),
    }
  })

  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined style={{ color: '#1B3A5C' }} />
          <span>
            房號 <Tag color="blue" style={{ fontSize: 14 }}>{room.room_no}</Tag>
            <Tag color="geekblue">{room.floor}</Tag> 保養歷史
          </span>
        </Space>
      }
      width={640}
      open={open}
      onClose={onClose}
      loading={loading}
      styles={{ body: { padding: '16px 20px' } }}
    >
      {/* ── 連續未保養警示 ──────────────────────────────────── */}
      {stats.consecutive_missed >= 2 && (
        <Alert
          type="error"
          showIcon
          icon={<WarningOutlined />}
          message={`連續 ${stats.consecutive_missed} 個月未保養！`}
          description="請安排補保養並追蹤完成情況。"
          style={{ marginBottom: 16 }}
        />
      )}
      {stats.consecutive_missed === 1 && (
        <Alert
          type="warning"
          showIcon
          message="上個月未保養，請確認本月是否已安排。"
          style={{ marginBottom: 16 }}
        />
      )}

      {/* ── KPI 三格 ───────────────────────────────────────── */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="保養記錄總數"
              value={stats.total_records}
              suffix="筆"
              valueStyle={{ color: '#1B3A5C', fontSize: 20 }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="近 12 月保養次數"
              value={`${stats.serviced_months} / ${stats.total_months}`}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#4BA8E8', fontSize: 20 }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="連續未保養月數"
              value={stats.consecutive_missed}
              suffix="月"
              prefix={<ClockCircleOutlined />}
              valueStyle={{
                color: stats.consecutive_missed >= 2 ? '#cf1322'
                  : stats.consecutive_missed === 1 ? '#fa8c16'
                  : '#52c41a',
                fontSize: 20,
              }}
            />
          </Card>
        </Col>
      </Row>

      {stats.last_serviced && (
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary">上次保養日期：</Text>
          <Tag color="blue">{stats.last_serviced}</Tag>
        </div>
      )}

      {/* ── 近 12 個月保養月曆 ─────────────────────────────── */}
      <Card
        title={<><CalendarOutlined /> 近 {stats.total_months} 個月保養月曆</>}
        size="small"
        style={{ marginBottom: 16 }}
      >
        <Row gutter={[6, 6]}>
          {monthly_summary.map((ms) => (
            <Col key={ms.month_label}>
              <MonthCell ms={ms} />
            </Col>
          ))}
        </Row>
        <Divider style={{ margin: '10px 0 6px' }} />
        <Row justify="space-between" align="middle">
          <Col>
            <Space size={16}>
              <Space size={4}><div style={{ width: 12, height: 12, background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 2 }} /><Text type="secondary" style={{ fontSize: 11 }}>已保養</Text></Space>
              <Space size={4}><div style={{ width: 12, height: 12, background: '#fff2f0', border: '1px solid #ffa39e', borderRadius: 2 }} /><Text type="secondary" style={{ fontSize: 11 }}>未保養</Text></Space>
              <Space size={4}><div style={{ width: 12, height: 12, background: '#fafafa', border: '1px solid #e8e8e8', borderRadius: 2 }} /><Text type="secondary" style={{ fontSize: 11 }}>當月</Text></Space>
            </Space>
          </Col>
          <Col>
            <Text type="secondary" style={{ fontSize: 11 }}>
              <CalendarOutlined /> 點擊月份可查看保養明細
            </Text>
          </Col>
        </Row>
      </Card>

      {/* ── 點選月份後的明細展開 ─────────────────────────────── */}
      {selectedMonth && (
        <Card
          size="small"
          style={{ marginBottom: 16, border: '2px solid #1B3A5C' }}
          title={
            <Space>
              <CalendarOutlined style={{ color: '#1B3A5C' }} />
              <Text strong style={{ color: '#1B3A5C' }}>{selectedMonth} 保養明細</Text>
              {selectedMonthRecords.length > 0
                ? <Tag color="blue">{selectedMonthRecords.length} 筆</Tag>
                : <Tag color="default">無記錄</Tag>
              }
            </Space>
          }
          extra={
            <Button size="small" type="text" onClick={() => setSelectedMonth(null)}>
              關閉 ✕
            </Button>
          }
        >
          {selectedMonthRecords.length === 0 ? (
            <div style={{ padding: '8px 0', textAlign: 'center' }}>
              <Text type="secondary">本月無保養記錄</Text>
            </div>
          ) : (
            <div>
              {selectedMonthRecords.map((r, idx) => {
                const abnormals = CHECK_FIELD_KEYS.filter(f => (r[f] || '').toUpperCase() === 'X')
                const hasX = abnormals.length > 0
                return (
                  <div key={r.ragic_id} style={{
                    background: hasX ? '#fff5f5' : '#f6ffed',
                    border: `1px solid ${hasX ? '#ffccc7' : '#b7eb8f'}`,
                    borderRadius: 6,
                    padding: '10px 14px',
                    marginBottom: idx < selectedMonthRecords.length - 1 ? 10 : 0,
                  }}>
                    {/* 基本資訊 */}
                    <Row gutter={16} style={{ marginBottom: 10 }}>
                      <Col xs={12} sm={8}>
                        <Text type="secondary" style={{ fontSize: 11 }}>保養日期</Text>
                        <div><Text strong style={{ fontSize: 13 }}>{r.maintain_date}</Text></div>
                      </Col>
                      <Col xs={12} sm={8}>
                        <Text type="secondary" style={{ fontSize: 11 }}>保養人員</Text>
                        <div><Text strong style={{ fontSize: 13 }}>{r.staff_name || '—'}</Text></div>
                      </Col>
                      <Col xs={24} sm={8}>
                        <Text type="secondary" style={{ fontSize: 11 }}>工時</Text>
                        <div><Text style={{ fontSize: 13 }}>{r.work_hours || '—'}</Text></div>
                      </Col>
                    </Row>
                    <Divider style={{ margin: '6px 0' }} />
                    {/* 12 項檢查 */}
                    <Row gutter={[8, 6]}>
                      {CHECK_FIELD_KEYS.map(f => {
                        const val = (r[f] || '').toUpperCase()
                        const isX = val === 'X'
                        return (
                          <Col key={f} xs={8} sm={6} md={4}>
                            <div style={{
                              background: isX ? '#fff1f0' : '#fff',
                              border: `1px solid ${isX ? '#ffa39e' : '#e8e8e8'}`,
                              borderRadius: 4,
                              padding: '3px 6px',
                              textAlign: 'center',
                            }}>
                              <div style={{ fontSize: 10, color: '#888', marginBottom: 2 }}>
                                {CHECK_FIELD_LABELS[f]}
                              </div>
                              <CheckTag value={r[f]} />
                            </div>
                          </Col>
                        )
                      })}
                    </Row>
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      )}

      {/* ── 保養記錄時間軸 ──────────────────────────────────── */}
      <Card
        title={<><HistoryOutlined /> 保養記錄（共 {records.length} 筆）</>}
        size="small"
      >
        {records.length === 0 ? (
          <Text type="secondary">目前無保養記錄</Text>
        ) : (
          <div style={{ maxHeight: 480, overflowY: 'auto', paddingRight: 4 }}>
            <Timeline items={timelineItems} style={{ marginTop: 8 }} />
          </div>
        )}
      </Card>
    </Drawer>
  )
}

// ═══════════════════════════════════════════════════════════════════
// 總表欄位定義（帶 onRoomClick）
// ═══════════════════════════════════════════════════════════════════

function buildSummaryColumns(
  onRoomClick: (roomNo: string) => void,
): ColumnsType<RoomSummaryRow> {
  return [
    {
      title: '樓層',
      dataIndex: 'floor',
      key: 'floor',
      width: 70,
      fixed: 'left',
      filters: ['5F','6F','7F','8F','9F','10F'].map(f => ({ text: f, value: f })),
      onFilter: (value, r) => r.floor === value,
      render: (v: string) => <Tag color="geekblue">{v}</Tag>,
    },
    {
      title: '房號',
      dataIndex: 'room_no',
      key: 'room_no',
      width: 80,
      fixed: 'left',
      render: (v: string, r: RoomSummaryRow) => (
        <Tooltip title="點擊查看保養歷史">
          <a
            onClick={() => onRoomClick(v)}
            style={{ fontWeight: r.serviced ? 700 : 400, color: r.serviced ? '#1677ff' : '#aaa' }}
          >
            {v}
          </a>
        </Tooltip>
      ),
    },
    {
      title: '保養日期',
      dataIndex: 'maintain_date',
      key: 'maintain_date',
      width: 110,
      sorter: (a, b) => (a.maintain_date || '').localeCompare(b.maintain_date || ''),
      render: (v: string | null) => v ? <Text>{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: '保養人員',
      dataIndex: 'staff_name',
      key: 'staff_name',
      width: 95,
      render: (v: string | null) => v || <Text type="secondary">—</Text>,
    },
    {
      title: '工時',
      dataIndex: 'work_hours',
      key: 'work_hours',
      width: 115,
      render: (v: string | null) => v ? <Text type="secondary">{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: '異常項目',
      key: 'abnormal_items',
      width: 200,
      render: (_: unknown, r: RoomSummaryRow) => {
        if (!r.serviced) return <Tag color="default">未保養</Tag>
        const abnormals = Object.entries(r.checks)
          .filter(([, v]) => v.toUpperCase() === 'X')
          .map(([label]) => <Tag key={label} color="error" style={{ marginBottom: 2 }}>{label}</Tag>)
        return abnormals.length > 0
          ? <Space size={2} wrap>{abnormals}</Space>
          : <Tag icon={<CheckCircleOutlined />} color="success">全 OK</Tag>
      },
    },
    {
      title: '異常數',
      dataIndex: 'abnormal_count',
      key: 'abnormal_count',
      width: 75,
      align: 'center',
      sorter: (a, b) => a.abnormal_count - b.abnormal_count,
      render: (v: number, r: RoomSummaryRow) => {
        if (!r.serviced) return <Text type="secondary">—</Text>
        return v > 0
          ? <Badge count={v} color="red" />
          : <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
      },
    },
    {
      title: '狀態',
      key: 'status',
      width: 90,
      fixed: 'right',
      render: (_: unknown, r: RoomSummaryRow) => {
        if (!r.serviced) return <Tag color="default" icon={<StopOutlined />}>未保養</Tag>
        if (r.abnormal_count > 0) return <Tag color="error" icon={<WarningOutlined />}>有異常</Tag>
        return <Tag color="success" icon={<CheckCircleOutlined />}>正常</Tag>
      },
    },
  ]
}

// ═══════════════════════════════════════════════════════════════════
// 明細清單欄位（帶 onRoomClick）
// ═══════════════════════════════════════════════════════════════════

function buildDetailColumns(
  onRoomClick: (roomNo: string) => void,
): ColumnsType<RoomMaintenanceDetailRecord> {
  return [
    {
      title: '保養日期',
      dataIndex: 'maintain_date',
      key: 'maintain_date',
      width: 110,
      fixed: 'left',
      sorter: (a, b) => a.maintain_date.localeCompare(b.maintain_date),
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '房號',
      dataIndex: 'room_no',
      key: 'room_no',
      width: 80,
      fixed: 'left',
      render: (v: string) => (
        <Tooltip title="點擊查看保養歷史">
          <a onClick={() => onRoomClick(v)}><Tag color="blue" style={{ cursor: 'pointer' }}>{v}</Tag></a>
        </Tooltip>
      ),
    },
    {
      title: '保養人員',
      dataIndex: 'staff_name',
      key: 'staff_name',
      width: 100,
    },
    {
      title: '工時',
      dataIndex: 'work_hours',
      key: 'work_hours',
      width: 115,
      render: (v: string) => <Text type="secondary">{v}</Text>,
    },
    ...CHECK_FIELD_KEYS.map((field) => ({
      title: CHECK_FIELD_LABELS[field],
      dataIndex: field,
      key: field,
      width: 78,
      align: 'center' as const,
      render: (v: string) => <CheckTag value={v} />,
    })),
    {
      title: '建立日期',
      dataIndex: 'created_date',
      key: 'created_date',
      width: 155,
      render: (v: string) => <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text>,
    },
  ]
}

// ═══════════════════════════════════════════════════════════════════
// KPI 卡片
// ═══════════════════════════════════════════════════════════════════

function KpiCard({
  title, value, color, icon, active, clickable, suffix, onClick,
}: {
  title: string; value: number | string; color: string; icon: React.ReactNode
  active?: boolean; clickable?: boolean; suffix?: string; onClick?: () => void
}) {
  return (
    <Card
      size="small"
      hoverable={clickable}
      onClick={clickable ? onClick : undefined}
      style={{
        cursor: clickable ? 'pointer' : 'default',
        border: active ? `2px solid ${color}` : '1px solid #f0f0f0',
        transition: 'all .2s',
        background: active ? `${color}18` : '#fff',
      }}
    >
      <Statistic
        title={
          <Space>
            {icon}
            <span>{title}</span>
            {clickable && <Text type="secondary" style={{ fontSize: 10 }}>可點擊篩選</Text>}
          </Space>
        }
        value={value}
        suffix={suffix}
        valueStyle={{ color, fontSize: 22, fontWeight: 700 }}
      />
    </Card>
  )
}

// ═══════════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════════════
// 保養統計 Tab（Phase 1 完成率趨勢 + Phase 2 異常項目 + Phase 3 樓層/對比）
// ═══════════════════════════════════════════════════════════════════

function MaintenanceStatsDashboard({
  data,
  loading,
  onReload,
}: {
  data: MaintenanceStatsResponse | null
  loading: boolean
  onReload: () => void
}) {
  const [riskTab, setRiskTab] = useState<'missed' | 'abnormal' | 'ok'>('missed')

  // ── 安全取出資料 ─────────────────────────────────────────────────
  const months     = data?.months           ?? []
  const trend      = data?.monthly_trend    ?? []
  const checkItems = data?.check_item_stats ?? []
  const floorStats = data?.floor_stats      ?? []
  const riskRooms  = data?.risk_rooms       ?? { consecutive_missed: [], repeated_abnormal: [], fully_ok: [] }
  const comparison = data?.comparison
  const kpi        = data?.kpi

  // ── 圖表資料 ─────────────────────────────────────────────────────
  const trendData = trend.map(t => ({
    month:      t.month_label,
    label:      t.month_label.slice(-2) + '月',
    completion: t.completion_rate,
    abnormal:   t.abnormal_rate,
    hours:      +(t.work_hours_total / 60).toFixed(1),
    serviced:   t.serviced_count,
  }))

  const checkChartData = checkItems.map(c => ({
    label:   c.label,
    x_count: c.abnormal_count,
    rate:    c.abnormal_rate,
  }))

  const floorChartData = floorStats.map(f => ({
    floor:      f.floor,
    completion: f.completion_rate,
    abnormal:   f.abnormal_count,
    rooms:      f.total_rooms,
  }))

  const compData = comparison ? [
    {
      name:       `當月\n${comparison.current_month.month_label}`,
      completion: comparison.current_month.completion_rate,
      abnormal:   comparison.current_month.abnormal_count,
      hours:      +(comparison.current_month.work_hours_total / 60).toFixed(1),
    },
    {
      name:       `上月\n${comparison.prev_month.month_label}`,
      completion: comparison.prev_month.completion_rate,
      abnormal:   comparison.prev_month.abnormal_count,
      hours:      +(comparison.prev_month.work_hours_total / 60).toFixed(1),
    },
    {
      name:       `去年同月\n${comparison.same_month_last_year.month_label}`,
      completion: comparison.same_month_last_year.completion_rate,
      abnormal:   comparison.same_month_last_year.abnormal_count,
      hours:      +(comparison.same_month_last_year.work_hours_total / 60).toFixed(1),
    },
  ] : []

  const latestYm = months[months.length - 1] ?? ''

  // ── Early return（hooks 全部呼叫完畢後）──────────────────────────
  if (!data && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Button icon={<ReloadOutlined />} onClick={onReload} type="primary">
          載入保養統計
        </Button>
      </div>
    )
  }

  // ── 趨勢方向指示 ─────────────────────────────────────────────────
  const trendIcon =
    kpi?.trend_direction === 'up'   ? <RiseOutlined style={{ color: '#52c41a' }} /> :
    kpi?.trend_direction === 'down' ? <FallOutlined  style={{ color: '#ff4d4f' }} /> :
    <MinusCircleOutlined style={{ color: '#8c8c8c' }} />

  // ── 高風險房間表格欄位 ───────────────────────────────────────────
  const missedCols: ColumnsType<ConsecutiveMissedRoom> = [
    { title: '樓層', dataIndex: 'floor',   width: 70 },
    { title: '房號', dataIndex: 'room_no', width: 80, render: (v: string) => <Text strong>{v}</Text> },
    {
      title: '連續未保養', dataIndex: 'missed_months', width: 100, align: 'center',
      render: (v: number) => (
        <Tag color={v >= 3 ? 'red' : 'orange'} style={{ fontWeight: 700 }}>
          {v} 個月
        </Tag>
      ),
      sorter: (a, b) => b.missed_months - a.missed_months,
      defaultSortOrder: 'ascend',
    },
    {
      title: '最後保養日', dataIndex: 'last_serviced', render: (v: string | null) =>
        v ? <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text> : <Text type="secondary">從未保養</Text>,
    },
  ]

  const abnormalCols: ColumnsType<RepeatedAbnormalRoom> = [
    { title: '樓層', dataIndex: 'floor',       width: 70 },
    { title: '房號', dataIndex: 'room_no',     width: 80, render: (v: string) => <Text strong>{v}</Text> },
    {
      title: '重複異常項目', dataIndex: 'field_label', width: 130,
      render: (v: string) => <Tag color="volcano">{v}</Tag>,
    },
    {
      title: '連續月數', dataIndex: 'consecutive_months', width: 80, align: 'center',
      render: (v: number) => <Badge count={v} style={{ backgroundColor: '#ff4d4f' }} />,
    },
  ]

  const okCols: ColumnsType<FullyOkRoom> = [
    { title: '樓層', dataIndex: 'floor',   width: 70 },
    { title: '房號', dataIndex: 'room_no', width: 80, render: (v: string) => <Text strong style={{ color: '#389e0d' }}>{v}</Text> },
    {
      title: '連續全正常', dataIndex: 'ok_record_count', width: 110, align: 'center',
      render: (v: number) => <Tag color="success" icon={<CheckCircleOutlined />}>{v} 筆記錄</Tag>,
    },
    {
      title: '最後保養日', dataIndex: 'last_serviced', render: (v: string | null) =>
        v ? <Text style={{ fontSize: 12, color: '#389e0d' }}>{v}</Text> : <Text type="secondary">—</Text>,
    },
  ]

  return (
    <div>
      {/* ── 一、主管 KPI 六卡 ─────────────────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #1B3A5C' }}>
            <Statistic
              title={<Space><HomeOutlined /><Tag color="blue" style={{ margin: 0 }}>{latestYm}</Tag>完成率</Space>}
              value={kpi?.current_month_completion_rate ?? 0} precision={1} suffix="%"
              valueStyle={{ color: '#1B3A5C', fontSize: 20 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: `3px solid ${(kpi?.current_month_completion_rate ?? 0) >= (kpi?.avg_completion_rate_12m ?? 0) ? '#52c41a' : '#ff4d4f'}` }}>
            <Statistic
              title={<Space>{trendIcon}趨勢（vs均）</Space>}
              value={kpi?.avg_completion_rate_12m ?? 0} precision={1} suffix="% 均"
              valueStyle={{ color: '#4BA8E8', fontSize: 20 }} />
            <Text type="secondary" style={{ fontSize: 11 }}>近{months.length}月平均完成率</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #ff7a45' }}>
            <Statistic
              title={<Space><WarningOutlined />當月異常率</Space>}
              value={kpi?.current_month_abnormal_rate ?? 0} precision={1} suffix="%"
              valueStyle={{ color: (kpi?.current_month_abnormal_rate ?? 0) > 30 ? '#cf1322' : '#fa8c16', fontSize: 20 }} />
            <Text type="secondary" style={{ fontSize: 11 }}>有X項目的房間比例</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: `3px solid ${(kpi?.consecutive_missed_rooms ?? 0) > 0 ? '#ff4d4f' : '#52c41a'}` }}>
            <Statistic
              title={<Space><ExclamationCircleOutlined />連續未保養</Space>}
              value={kpi?.consecutive_missed_rooms ?? 0} suffix="間"
              valueStyle={{ color: (kpi?.consecutive_missed_rooms ?? 0) > 0 ? '#cf1322' : '#52c41a', fontSize: 20 }} />
            <Text type="secondary" style={{ fontSize: 11 }}>連續≥2月無記錄</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #52c41a' }}>
            <Statistic
              title={<Space><TrophyOutlined style={{ color: '#faad14' }} />全正常房間</Space>}
              value={kpi?.fully_ok_rooms ?? 0} suffix="間"
              valueStyle={{ color: '#389e0d', fontSize: 20 }} />
            <Text type="secondary" style={{ fontSize: 11 }}>最近3筆均全V</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #722ed1' }}>
            <Statistic
              title={<Space><ToolOutlined />重複異常房間</Space>}
              value={riskRooms.repeated_abnormal.length} suffix="間"
              valueStyle={{ color: riskRooms.repeated_abnormal.length > 0 ? '#722ed1' : '#52c41a', fontSize: 20 }} />
            <Text type="secondary" style={{ fontSize: 11 }}>同項目連續2月X</Text>
          </Card>
        </Col>
      </Row>

      {/* ── 二、月別完成率趨勢（Phase 1）──────────────────────────── */}
      <Card
        title={<><LineChartOutlined /> 近 {months.length} 個月完成率 × 異常率趨勢</>}
        size="small"
        style={{ marginBottom: 16 }}
        extra={
          <Button size="small" icon={<ReloadOutlined />} onClick={onReload} loading={loading}>
            重新載入
          </Button>
        }
      >
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={trendData} margin={{ top: 10, right: 40, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} />
            <YAxis
              yAxisId="left" domain={[0, 100]} tickFormatter={(v: number) => `${v}%`}
              tick={{ fontSize: 10 }} label={{ value: '完成率', angle: -90, position: 'insideLeft', fontSize: 10 }}
            />
            <YAxis
              yAxisId="right" orientation="right" domain={[0, 100]}
              tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 10 }}
              label={{ value: '異常率', angle: 90, position: 'insideRight', fontSize: 10 }}
            />
            <RcTooltip
              formatter={(value: number, name: string) => [
                `${value.toFixed(1)}%`,
                name === 'completion' ? '完成率' : '異常率',
              ]}
            />
            <Legend
              formatter={(v: string) => v === 'completion' ? '保養完成率 %' : '異常率（有X房間）%'}
              iconSize={10} wrapperStyle={{ fontSize: 11 }}
            />
            <ReferenceLine yAxisId="left" y={100} stroke="#52c41a" strokeDasharray="4 2"
              label={{ value: '100%', fill: '#52c41a', fontSize: 9, position: 'insideTopRight' }} />
            <Line yAxisId="left"  type="monotone" dataKey="completion" stroke="#1B3A5C" strokeWidth={2.5}
              dot={{ r: 4 }} activeDot={{ r: 6 }}
              label={{ position: 'top', fontSize: 9, formatter: (v: number) => v > 0 ? `${v}%` : '' }} />
            <Line yAxisId="right" type="monotone" dataKey="abnormal"   stroke="#ff4d4f" strokeWidth={1.5}
              strokeDasharray="5 3" dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
        <Text type="secondary" style={{ fontSize: 10, float: 'right' }}>
          藍實線 = 完成率（左軸）；紅虛線 = 異常率（右軸）
        </Text>
      </Card>

      {/* ── 三、異常項目分析（Phase 2）──────────────────────────────── */}
      <Card
        title={<><BarChartOutlined /> 異常項目排行（近 {months.length} 個月累計 X 次數）</>}
        size="small"
        style={{ marginBottom: 16 }}
      >
        <Row gutter={16}>
          <Col xs={24} md={14}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={checkChartData} layout="vertical" margin={{ top: 4, right: 56, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={82} />
                <RcTooltip
                  formatter={(v: number, name: string) => [v, name === 'x_count' ? 'X 次數' : '異常率 %']}
                />
                <Bar dataKey="x_count" radius={[0, 4, 4, 0]}
                  label={{ position: 'right', fontSize: 10, formatter: (v: number) => v > 0 ? v : '' }}>
                  {checkChartData.map((entry, i) => (
                    <Cell
                      key={entry.label}
                      fill={i === 0 ? '#cf1322' : i <= 2 ? '#ff7a45' : i <= 5 ? '#ffa940' : '#4BA8E8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Col>
          <Col xs={24} md={10}>
            <div style={{ padding: '8px 0' }}>
              <Text strong style={{ fontSize: 13, color: '#1B3A5C', display: 'block', marginBottom: 8 }}>
                異常率明細（X次數 / 總記錄數）
              </Text>
              {checkItems.map((item, i) => (
                <div key={item.field_name} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '4px 8px', marginBottom: 4,
                  background: i === 0 ? '#fff1f0' : i <= 2 ? '#fff7e6' : '#f9f9f9',
                  borderRadius: 6, border: `1px solid ${i === 0 ? '#ffccc7' : i <= 2 ? '#ffd591' : '#e8e8e8'}`,
                }}>
                  <Space size={6}>
                    <Text style={{ fontSize: 11, color: '#666', width: 20, textAlign: 'right' }}>
                      {i + 1}.
                    </Text>
                    <Text style={{ fontSize: 12, fontWeight: i < 3 ? 600 : 400 }}>{item.label}</Text>
                  </Space>
                  <Space size={6}>
                    <Tag color={i === 0 ? 'red' : i <= 2 ? 'orange' : 'default'} style={{ margin: 0, fontSize: 11 }}>
                      {item.abnormal_count} 次
                    </Tag>
                    <Text type="secondary" style={{ fontSize: 11 }}>{item.abnormal_rate}%</Text>
                  </Space>
                </div>
              ))}
            </div>
          </Col>
        </Row>
      </Card>

      {/* ── 四、樓層分析 + 月份對比（Phase 3）──────────────────────── */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        {/* 樓層分析 */}
        <Col xs={24} md={14}>
          <Card title={<><BarChartOutlined /> 各樓層當月完成率 + 全期異常次數</>} size="small">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={floorChartData} margin={{ top: 10, right: 40, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="floor" tick={{ fontSize: 11 }} />
                <YAxis
                  yAxisId="left" domain={[0, 100]} tickFormatter={(v: number) => `${v}%`}
                  tick={{ fontSize: 10 }}
                />
                <YAxis
                  yAxisId="right" orientation="right"
                  tick={{ fontSize: 10 }}
                  label={{ value: '異常次', angle: 90, position: 'insideRight', fontSize: 9 }}
                />
                <RcTooltip
                  formatter={(v: number, name: string) => [
                    name === 'completion' ? `${v}%` : `${v} 次`,
                    name === 'completion' ? '當月完成率' : '全期異常項次',
                  ]}
                />
                <Legend
                  formatter={(v: string) => v === 'completion' ? '當月完成率 %' : '全期異常項次'}
                  iconSize={10} wrapperStyle={{ fontSize: 11 }}
                />
                <Bar yAxisId="left"  dataKey="completion" fill="#1B3A5C" opacity={0.85} radius={[4, 4, 0, 0]}
                  label={{ position: 'top', fontSize: 9, formatter: (v: number) => `${v}%` }} />
                <Bar yAxisId="right" dataKey="abnormal"   fill="#ff7a45" opacity={0.7}  radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        {/* 月份對比 */}
        <Col xs={24} md={10}>
          <Card title={<><CalendarOutlined /> 月份對比（當月 / 上月 / 去年同月）</>} size="small">
            {compData.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={compData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                    <YAxis domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 10 }} />
                    <RcTooltip formatter={(v: number) => [`${v}%`, '完成率']} />
                    <Bar dataKey="completion" radius={[4, 4, 0, 0]}
                      label={{ position: 'top', fontSize: 9, formatter: (v: number) => `${v}%` }}>
                      {compData.map((entry, i) => (
                        <Cell key={entry.name} fill={i === 0 ? '#1B3A5C' : i === 1 ? '#4BA8E8' : '#adc6ff'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                {/* 對比明細表 */}
                <Divider style={{ margin: '8px 0' }} />
                {compData.map((row, i) => (
                  <div key={row.name} style={{
                    display: 'flex', justifyContent: 'space-between',
                    padding: '3px 6px', borderRadius: 4,
                    background: i === 0 ? '#e6f0fa' : 'transparent',
                  }}>
                    <Text style={{ fontSize: 11, color: i === 0 ? '#1B3A5C' : '#666', fontWeight: i === 0 ? 700 : 400 }}>
                      {row.name.replace('\n', ' ')}
                    </Text>
                    <Space size={10}>
                      <Text style={{ fontSize: 11 }}>完成率 <strong>{row.completion}%</strong></Text>
                      <Text style={{ fontSize: 11 }}>異常 <strong style={{ color: '#ff4d4f' }}>{row.abnormal}</strong> 次</Text>
                      <Text style={{ fontSize: 11 }}>工時 <strong>{row.hours}h</strong></Text>
                    </Space>
                  </div>
                ))}
              </>
            ) : (
              <Text type="secondary">載入中…</Text>
            )}
          </Card>
        </Col>
      </Row>

      {/* ── 五、高風險房間明細（Phase 1B）───────────────────────────── */}
      <Card
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: riskRooms.consecutive_missed.length > 0 ? '#ff4d4f' : '#8c8c8c' }} />
            <span>高風險房間明細</span>
            <Badge count={riskRooms.consecutive_missed.length + riskRooms.repeated_abnormal.length} style={{ backgroundColor: '#ff4d4f' }} />
          </Space>
        }
        size="small"
      >
        <Tabs
          activeKey={riskTab}
          onChange={v => setRiskTab(v as typeof riskTab)}
          size="small"
          items={[
            {
              key: 'missed',
              label: (
                <Space size={4}>
                  <StopOutlined style={{ color: '#ff4d4f' }} />
                  連續未保養
                  <Badge count={riskRooms.consecutive_missed.length} style={{ backgroundColor: '#ff4d4f' }} />
                </Space>
              ),
              children: riskRooms.consecutive_missed.length === 0 ? (
                <Alert type="success" showIcon message="目前無連續未保養房間（≥2月）" />
              ) : (
                <Table<ConsecutiveMissedRoom>
                  rowKey="room_no"
                  columns={missedCols}
                  dataSource={riskRooms.consecutive_missed}
                  size="small" pagination={false}
                  rowClassName={r => r.missed_months >= 3 ? 'row-abnormal' : ''}
                />
              ),
            },
            {
              key: 'abnormal',
              label: (
                <Space size={4}>
                  <WarningOutlined style={{ color: '#722ed1' }} />
                  重複異常項目
                  <Badge count={riskRooms.repeated_abnormal.length} style={{ backgroundColor: '#722ed1' }} />
                </Space>
              ),
              children: riskRooms.repeated_abnormal.length === 0 ? (
                <Alert type="success" showIcon message="近2月無重複異常項目" />
              ) : (
                <Table<RepeatedAbnormalRoom>
                  rowKey={r => `${r.room_no}-${r.field_name}`}
                  columns={abnormalCols}
                  dataSource={riskRooms.repeated_abnormal}
                  size="small" pagination={false}
                />
              ),
            },
            {
              key: 'ok',
              label: (
                <Space size={4}>
                  <TrophyOutlined style={{ color: '#52c41a' }} />
                  全正常房間
                  <Badge count={riskRooms.fully_ok.length} style={{ backgroundColor: '#52c41a' }} />
                </Space>
              ),
              children: riskRooms.fully_ok.length === 0 ? (
                <Alert type="info" showIcon message="目前無近3筆記錄全正常的房間" />
              ) : (
                <Table<FullyOkRoom>
                  rowKey="room_no"
                  columns={okCols}
                  dataSource={riskRooms.fully_ok}
                  size="small" pagination={false}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

// 人員工時表 Tab（原版 pivot — 不可修改）
// ═══════════════════════════════════════════════════════════════════

function fmtHours(h: number): string {
  if (h <= 0) return '—'
  return `${h.toFixed(2)}h`
}

/** CSV 匯出 */
function exportCSV(months: string[], rows: import('@/types/roomMaintenanceDetail').StaffHoursRow[], mtotals: Record<string, number>, grandTotal: number) {
  const headers = ['人員', ...months, '合計(h)']
  const lines = ['\ufeff' + headers.join(',')]
  rows.forEach(r => {
    lines.push([r.staff_name, ...months.map(ym => (r.monthly_hours[ym] ?? 0).toFixed(2)), r.total_hours.toFixed(2)].join(','))
  })
  lines.push(['月合計', ...months.map(ym => (mtotals[ym] ?? 0).toFixed(2)), grandTotal.toFixed(2)].join(','))
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url
  a.download = `人員工時表_${dayjs().format('YYYYMMDD')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── 原版 StaffHoursTab（不可修改） ──────────────────────────────────
function StaffHoursTab({
  data,
  loading,
  onReload,
}: {
  data: StaffHoursResponse | null
  loading: boolean
  onReload: () => void
}) {
  if (!data && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Button icon={<ReloadOutlined />} onClick={onReload}>載入人員工時表</Button>
      </div>
    )
  }

  const months     = data?.months          ?? []
  const rows       = data?.rows            ?? []
  const mtotals    = data?.month_totals    ?? {}
  const grandTotal = data?.grand_total_hours ?? 0

  type PivotRow = { staff_name: string; [month: string]: string | number }

  const columns: ColumnsType<PivotRow> = [
    {
      title: '人員',
      dataIndex: 'staff_name',
      key: 'staff_name',
      fixed: 'left',
      width: 100,
      render: (v: string) => (
        v === '__total__'
          ? <Text strong style={{ color: '#1B3A5C' }}>月合計</Text>
          : <Text strong>{v}</Text>
      ),
    },
    ...months.map(ym => ({
      title: (
        <div style={{ textAlign: 'center' as const, fontSize: 11 }}>
          <div style={{ fontWeight: 600 }}>{ym.replace('/', '\n')}</div>
        </div>
      ),
      dataIndex: ym,
      key: ym,
      width: 80,
      align: 'center' as const,
      render: (v: number, record: PivotRow) => {
        if (v <= 0) return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        const isTotalRow = record.staff_name === '__total__'
        return (
          <Text style={{ fontSize: 12, fontWeight: isTotalRow ? 700 : 400, color: isTotalRow ? '#1B3A5C' : v >= 1 ? '#389e0d' : '#4BA8E8' }}>
            {v.toFixed(2)}h
          </Text>
        )
      },
    })),
    {
      title: '合計',
      dataIndex: 'total_hours',
      key: 'total_hours',
      fixed: 'right',
      width: 90,
      align: 'center' as const,
      render: (v: number, record: PivotRow) => {
        const isTotalRow = record.staff_name === '__total__'
        if (v <= 0) return <Text type="secondary">—</Text>
        return <Tag color={isTotalRow ? 'blue' : 'geekblue'} style={{ fontWeight: 700, fontSize: 12 }}>{v.toFixed(2)}h</Tag>
      },
    },
  ]

  const tableData: PivotRow[] = rows.map(r => {
    const row: PivotRow = { staff_name: r.staff_name, total_hours: r.total_hours }
    months.forEach(ym => { row[ym] = r.monthly_hours[ym] ?? 0 })
    return row
  })
  const totalRow: PivotRow = { staff_name: '__total__', total_hours: grandTotal }
  months.forEach(ym => { totalRow[ym] = mtotals[ym] ?? 0 })
  const allRows = [...tableData, totalRow]

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 12 }}>
        <Col>
          <Space>
            <Text strong>近 12 個月人員工時彙總</Text>
            <Tag color="blue">單位：小時（h）</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>明細欄位為分鐘，此處已換算為小時</Text>
          </Space>
        </Col>
        <Col>
          <Space>
            <Tag color="geekblue" style={{ fontSize: 13 }}>總計 {grandTotal.toFixed(2)}h</Tag>
            <Button size="small" icon={<ReloadOutlined />} onClick={onReload} loading={loading}>重新載入</Button>
          </Space>
        </Col>
      </Row>
      <Card size="small">
        <Table<PivotRow>
          rowKey="staff_name"
          columns={columns}
          dataSource={allRows}
          loading={loading}
          size="small"
          scroll={{ x: Math.max(900, 100 + months.length * 80 + 90) }}
          pagination={false}
          rowClassName={r => r.staff_name === '__total__' ? 'row-total' : ''}
        />
      </Card>
      <style>{`
        .row-total td { background-color: #e6f4ff !important; }
        .row-total:hover td { background-color: #bae0ff !important; }
      `}</style>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
// 人員工時表統計 Tab — 主管總覽 + 趨勢圖 + 異常分析 + 下鑽
// ═══════════════════════════════════════════════════════════════════

// ── 個人分析 Drawer ───────────────────────────────────────────────
function StaffPersonalDrawer({
  open, onClose, staffName, data,
}: {
  open: boolean
  onClose: () => void
  staffName: string | null
  data: StaffHoursResponse | null
}) {
  if (!staffName || !data) return null
  const row    = data.rows.find(r => r.staff_name === staffName)
  const months = data.months
  if (!row) return null

  const personalHours  = months.map(ym => row.monthly_hours[ym] ?? 0)
  const activeMonths   = personalHours.filter(h => h > 0)
  const avgH           = activeMonths.length > 0 ? activeMonths.reduce((a, b) => a + b, 0) / activeMonths.length : 0
  const maxH           = Math.max(...personalHours)
  const maxMonth       = months[personalHours.indexOf(maxH)] ?? ''
  const minActive      = activeMonths.length > 0 ? Math.min(...activeMonths) : 0
  const minMonth       = months[personalHours.indexOf(minActive)] ?? ''

  // 月均與全員平均比較
  const chartData = months.map(ym => {
    const staffH     = row.monthly_hours[ym] ?? 0
    const totalH     = data.month_totals[ym] ?? 0
    const activeN    = data.rows.filter(r => (r.monthly_hours[ym] ?? 0) > 0).length
    const teamAvg    = activeN > 0 ? totalH / activeN : 0
    return { month: ym.slice(-2) + '月', ym, staff: staffH, teamAvg }
  })

  return (
    <Drawer
      title={
        <Space>
          <UserOutlined style={{ color: '#1B3A5C' }} />
          <span style={{ color: '#1B3A5C', fontWeight: 700 }}>{staffName}</span>
          <Text type="secondary" style={{ fontSize: 13 }}>個人工時分析</Text>
        </Space>
      }
      width={600}
      open={open}
      onClose={onClose}
      styles={{ body: { padding: '16px 20px' } }}
    >
      {/* KPI */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        {[
          { label: '近12月合計', value: `${row.total_hours.toFixed(2)}h`, color: '#1B3A5C' },
          { label: '月平均工時', value: `${avgH.toFixed(2)}h`,           color: '#4BA8E8' },
          { label: '最高月份',   value: `${maxMonth} (${maxH.toFixed(2)}h)`, color: '#52c41a' },
          { label: '最低月份',   value: `${minMonth} (${minActive.toFixed(2)}h)`, color: '#fa8c16' },
        ].map(item => (
          <Col span={12} key={item.label} style={{ marginBottom: 8 }}>
            <Card size="small">
              <Statistic title={item.label} value={item.value}
                valueStyle={{ color: item.color, fontSize: 16, fontWeight: 700 }} />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 折線圖：個人 vs 全員平均 */}
      <Card title={<><LineChartOutlined /> 近 {months.length} 個月工時趨勢</>} size="small" style={{ marginBottom: 12 }}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} unit="h" />
            <RcTooltip formatter={(v: number, name: string) => [`${v.toFixed(2)}h`, name === 'staff' ? staffName : '全員平均']} />
            <Legend formatter={(v: string) => v === 'staff' ? staffName : '全員平均'} iconSize={10} wrapperStyle={{ fontSize: 11 }} />
            <Line type="monotone" dataKey="staff"   stroke="#1B3A5C" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="teamAvg" stroke="#4BA8E8" strokeWidth={1.5} strokeDasharray="4 2" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* 月份明細 */}
      <Card title={<><CalendarOutlined /> 月份工時明細</>} size="small">
        <Row gutter={[8, 6]}>
          {months.map(ym => {
            const h = row.monthly_hours[ym] ?? 0
            const teamAvg = (() => {
              const total  = data.month_totals[ym] ?? 0
              const active = data.rows.filter(r => (r.monthly_hours[ym] ?? 0) > 0).length
              return active > 0 ? total / active : 0
            })()
            const ratio = teamAvg > 0 ? h / teamAvg : 1
            let bg = '#fafafa', border = '#e8e8e8', tc = '#aaa'
            if (h > 0 && ratio >= 1.2) { bg = '#fff7e6'; border = '#ffd591'; tc = '#d46b08' }
            else if (h > 0 && ratio >= 0.8) { bg = '#f6ffed'; border = '#b7eb8f'; tc = '#389e0d' }
            else if (h > 0) { bg = '#e6f4ff'; border = '#91caff'; tc = '#1677ff' }
            return (
              <Col span={6} key={ym}>
                <div style={{ background: bg, border: `1px solid ${border}`, borderRadius: 6, padding: '4px 6px', textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: '#888' }}>{ym}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: tc }}>{h > 0 ? `${h.toFixed(2)}h` : '—'}</div>
                </div>
              </Col>
            )
          })}
        </Row>
      </Card>
    </Drawer>
  )
}

// ── 人員工時表統計主元件（所有 hooks 在 early return 之前）────────
function StaffHoursDashboard({
  data,
  loading,
  onReload,
}: {
  data: StaffHoursResponse | null
  loading: boolean
  onReload: () => void
}) {
  // ── 所有 hooks 必須無條件排在最頂部 ─────────────────────────────
  const [staffSearch,    setStaffSearch]    = useState('')
  const [sortBy,         setSortBy]         = useState<'total' | 'current' | 'change'>('total')
  const [selectedStaff,  setSelectedStaff]  = useState<string | null>(null)
  const [selectedMonth,  setSelectedMonth]  = useState<string>('')   // '' → 自動取最新月

  // 安全取出資料（data 為 null 時用空值）
  const months     = data?.months          ?? []
  const rows       = data?.rows            ?? []
  const mtotals    = data?.month_totals    ?? {}
  const grandTotal = data?.grand_total_hours ?? 0

  // 月份指標 — 使用者可自選月份，預設為最新月
  const latestMonth   = months.length > 0 ? months[months.length - 1] : ''
  const curMonth      = (selectedMonth && months.includes(selectedMonth)) ? selectedMonth : latestMonth
  const curMonthIdx   = months.indexOf(curMonth)
  const prevMonth     = curMonthIdx > 0 ? months[curMonthIdx - 1] : ''
  const prevPrevMonth = curMonthIdx > 1 ? months[curMonthIdx - 2] : ''

  const curTotal  = mtotals[curMonth]  ?? 0
  const prevTotal = mtotals[prevMonth] ?? 0
  const momChange = prevTotal > 0 ? ((curTotal - prevTotal) / prevTotal * 100) : 0
  const curActive = rows.filter(r => (r.monthly_hours[curMonth] ?? 0) > 0)
  const avgHours  = curActive.length > 0 ? curTotal / curActive.length : 0
  const sortedCur = [...curActive].sort((a, b) => (b.monthly_hours[curMonth] ?? 0) - (a.monthly_hours[curMonth] ?? 0))
  const topStaff    = sortedCur[0]    ?? null
  const bottomStaff = sortedCur[sortedCur.length - 1] ?? null

  // 異常偵測（useMemo — 在 hooks 頂部，不在 early return 後）
  type AnomalyKind = 'surge' | 'drop' | 'persistent_high' | 'near_zero'
  interface Anomaly { name: string; kind: AnomalyKind; cur: number; prev: number; pct: number }
  const anomalies = useMemo<Anomaly[]>(() => {
    if (!data) return []
    const out: Anomaly[] = []
    rows.forEach(r => {
      const cur  = r.monthly_hours[curMonth]      ?? 0
      const prev = r.monthly_hours[prevMonth]     ?? 0
      const pp   = r.monthly_hours[prevPrevMonth] ?? 0
      const pct  = prev > 0 ? ((cur - prev) / prev * 100) : (cur > 0 ? 999 : 0)
      if (cur > 0 && cur < 0.5)
        out.push({ name: r.staff_name, kind: 'near_zero', cur, prev, pct })
      else if (pct > 20 && prev > 0)
        out.push({ name: r.staff_name, kind: 'surge', cur, prev, pct })
      else if (pct < -20 && prev > 0)
        out.push({ name: r.staff_name, kind: 'drop', cur, prev, pct })
      if (avgHours > 0 && cur > avgHours * 1.5 && prev > avgHours * 1.5 && pp > avgHours * 1.5 &&
          !out.find(a => a.name === r.staff_name && a.kind === 'persistent_high'))
        out.push({ name: r.staff_name, kind: 'persistent_high', cur, prev, pct })
    })
    return out
  }, [data, rows, curMonth, prevMonth, prevPrevMonth, avgHours])

  // 圖表資料
  const activeMonthCount = months.filter(ym => (mtotals[ym] ?? 0) > 0).length
  const overallAvg       = activeMonthCount > 0 ? grandTotal / activeMonthCount : 0
  const trendData  = months.map(ym => ({ month: ym.replace('/', '/'), total: +(mtotals[ym] ?? 0).toFixed(2) }))
  const rankingData = [...rows]
    .filter(r => (r.monthly_hours[curMonth] ?? 0) > 0)
    .sort((a, b) => (a.monthly_hours[curMonth] ?? 0) - (b.monthly_hours[curMonth] ?? 0))
    .map(r => ({ name: r.staff_name, hours: +(r.monthly_hours[curMonth] ?? 0).toFixed(2) }))

  // 強化明細表資料（搜尋+排序）
  type PivotRow = { staff_name: string; [k: string]: string | number }
  const filteredRows = useMemo<PivotRow[]>(() => {
    if (!data) return []
    let result = [...rows]
    if (staffSearch.trim()) result = result.filter(r => r.staff_name.includes(staffSearch.trim()))
    if (sortBy === 'total')   result.sort((a, b) => b.total_hours - a.total_hours)
    if (sortBy === 'current') result.sort((a, b) => (b.monthly_hours[curMonth] ?? 0) - (a.monthly_hours[curMonth] ?? 0))
    if (sortBy === 'change')  result.sort((a, b) => {
      const pa = Math.abs(((a.monthly_hours[curMonth] ?? 0) - (a.monthly_hours[prevMonth] ?? 0)) / (a.monthly_hours[prevMonth] || 1))
      const pb = Math.abs(((b.monthly_hours[curMonth] ?? 0) - (b.monthly_hours[prevMonth] ?? 0)) / (b.monthly_hours[prevMonth] || 1))
      return pb - pa
    })
    return result.map(r => {
      const row: PivotRow = { staff_name: r.staff_name, total_hours: r.total_hours }
      months.forEach(ym => { row[ym] = r.monthly_hours[ym] ?? 0 })
      return row
    })
  }, [data, rows, staffSearch, sortBy, curMonth, prevMonth, months])

  // ── Early return（hooks 已全部呼叫完畢）───────────────────────────
  if (!data && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Button icon={<ReloadOutlined />} onClick={onReload}>載入人員工時統計</Button>
      </div>
    )
  }

  // ── 衍生常數 ─────────────────────────────────────────────────────
  const totalRow: PivotRow = { staff_name: '__total__', total_hours: grandTotal }
  months.forEach(ym => { totalRow[ym] = mtotals[ym] ?? 0 })
  const allTableRows = [...filteredRows, totalRow]

  const anomalyStyle: Record<AnomalyKind, { color: string; bg: string; label: string; icon: React.ReactNode }> = {
    surge:           { color: '#cf1322', bg: '#fff1f0', label: '工時異常偏高',  icon: <RiseOutlined /> },
    drop:            { color: '#d46b08', bg: '#fff7e6', label: '工時異常偏低',  icon: <FallOutlined /> },
    persistent_high: { color: '#ad6800', bg: '#fffbe6', label: '連續3月偏高',   icon: <WarningOutlined /> },
    near_zero:       { color: '#8c8c8c', bg: '#f5f5f5', label: '工時趨近於零',  icon: <ExclamationCircleOutlined /> },
  }

  const pivotColumns: ColumnsType<PivotRow> = [
    {
      title: '人員', dataIndex: 'staff_name', key: 'staff_name', fixed: 'left', width: 100,
      render: (v: string) => v === '__total__'
        ? <Text strong style={{ color: '#1B3A5C' }}>月合計</Text>
        : <Tooltip title="點擊查看個人歷史趨勢"><a onClick={() => setSelectedStaff(v)} style={{ fontWeight: 600 }}><UserOutlined style={{ marginRight: 4 }} />{v}</a></Tooltip>,
    },
    ...months.map(ym => ({
      title: <div style={{ textAlign: 'center' as const, fontSize: 11, fontWeight: 600 }}>{ym}</div>,
      dataIndex: ym, key: ym, width: 80, align: 'center' as const,
      render: (v: number, rec: PivotRow) => {
        if (v <= 0) return <Text type="secondary" style={{ fontSize: 11 }}>—</Text>
        const isTotal = rec.staff_name === '__total__'
        return <Text style={{ fontSize: 12, fontWeight: isTotal ? 700 : 400, color: isTotal ? '#1B3A5C' : v >= 1 ? '#389e0d' : '#4BA8E8' }}>{v.toFixed(2)}h</Text>
      },
    })),
    {
      title: '合計', dataIndex: 'total_hours', key: 'total_hours', fixed: 'right', width: 90, align: 'center' as const,
      render: (v: number, rec: PivotRow) => {
        if (v <= 0) return <Text type="secondary">—</Text>
        return <Tag color={rec.staff_name === '__total__' ? 'blue' : 'geekblue'} style={{ fontWeight: 700 }}>{v.toFixed(2)}h</Tag>
      },
    },
  ]

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div>
      {/* ── 月份選擇器 ──────────────────────────────────────────── */}
      <Card size="small" style={{ marginBottom: 16, background: '#f8fafc', border: '1px solid #d0e6f7' }}>
        <Row align="middle" gutter={16}>
          <Col>
            <Space>
              <CalendarOutlined style={{ color: '#1B3A5C', fontSize: 16 }} />
              <Text strong style={{ color: '#1B3A5C' }}>分析月份</Text>
            </Space>
          </Col>
          <Col>
            <Select
              value={curMonth}
              onChange={(v: string) => setSelectedMonth(v)}
              style={{ width: 140 }}
              options={[...months].reverse().map(ym => ({
                label: ym === latestMonth ? `${ym}（最新）` : ym,
                value: ym,
              }))}
              placeholder="選擇月份"
            />
          </Col>
          {curMonth !== latestMonth && (
            <Col>
              <Button size="small" onClick={() => setSelectedMonth('')}>
                回到最新月（{latestMonth}）
              </Button>
            </Col>
          )}
          <Col flex="auto" style={{ textAlign: 'right' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              KPI、排名圖、異常分析均依選定月份重新計算　　趨勢圖顯示完整12月（藍色 = 選定月）
            </Text>
          </Col>
        </Row>
      </Card>

      {/* ── 一、主管 KPI 總覽 ────────────────────────────────────── */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #1B3A5C' }}>
            <Statistic title={<Space><BarChartOutlined /><Tag color="blue" style={{ margin: 0 }}>{curMonth}</Tag>總工時</Space>}
              value={curTotal} precision={2} suffix="h"
              valueStyle={{ color: '#1B3A5C', fontSize: 20 }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: `3px solid ${momChange >= 0 ? '#52c41a' : '#ff4d4f'}` }}>
            <Statistic
              title={<Space>{momChange >= 0 ? <RiseOutlined style={{ color: '#52c41a' }} /> : <FallOutlined style={{ color: '#ff4d4f' }} />}較 {prevMonth || '上月'}</Space>}
              value={Math.abs(momChange)} precision={1} suffix="%" prefix={momChange >= 0 ? '+' : '−'}
              valueStyle={{ color: momChange >= 0 ? '#52c41a' : '#ff4d4f', fontSize: 20 }} />
            {prevTotal > 0 && <Text type="secondary" style={{ fontSize: 11 }}>上月 {prevTotal.toFixed(2)}h</Text>}
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #4BA8E8' }}>
            <Statistic title={<Space><TeamOutlined />本月人均</Space>}
              value={avgHours} precision={2} suffix="h"
              valueStyle={{ color: '#4BA8E8', fontSize: 20 }} />
            <Text type="secondary" style={{ fontSize: 11 }}>{curActive.length} 人有記錄</Text>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #389e0d' }}>
            <Statistic title={<Space><TrophyOutlined style={{ color: '#faad14' }} />本月最高</Space>}
              value={topStaff ? (topStaff.monthly_hours[curMonth] ?? 0) : 0} precision={2} suffix="h"
              valueStyle={{ color: '#389e0d', fontSize: 20 }} />
            {topStaff && <Text type="secondary" style={{ fontSize: 11 }}>{topStaff.staff_name}</Text>}
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: '3px solid #fa8c16' }}>
            <Statistic title={<Space><UserOutlined />本月最低</Space>}
              value={bottomStaff ? (bottomStaff.monthly_hours[curMonth] ?? 0) : 0} precision={2} suffix="h"
              valueStyle={{ color: '#fa8c16', fontSize: 20 }} />
            {bottomStaff && <Text type="secondary" style={{ fontSize: 11 }}>{bottomStaff.staff_name}</Text>}
          </Card>
        </Col>
        <Col xs={24} sm={12} md={4}>
          <Card size="small" style={{ borderTop: `3px solid ${anomalies.length > 0 ? '#ff4d4f' : '#52c41a'}` }}>
            <Statistic title={<Space><ExclamationCircleOutlined />異常波動</Space>}
              value={anomalies.length} suffix="人"
              valueStyle={{ color: anomalies.length > 0 ? '#cf1322' : '#52c41a', fontSize: 20 }} />
            <Text type="secondary" style={{ fontSize: 11 }}>±20% 或連續偏高</Text>
          </Card>
        </Col>
      </Row>

      {/* ── 二、趨勢圖 + 排名圖 ────────────────────────────────────── */}
      <Row gutter={12} style={{ marginBottom: 16 }}>
        <Col xs={24} md={14}>
          <Card title={<><BarChartOutlined /> 近 {months.length} 個月總工時趨勢</>} size="small">
            <ResponsiveContainer width="100%" height={210}>
              <BarChart data={trendData} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={0} />
                <YAxis tick={{ fontSize: 10 }} unit="h" />
                <RcTooltip formatter={(v: number) => [`${v.toFixed(2)}h`, '總工時']} />
                {overallAvg > 0 && (
                  <ReferenceLine y={overallAvg} stroke="#fa8c16" strokeDasharray="4 2"
                    label={{ value: `均 ${overallAvg.toFixed(1)}h`, fill: '#fa8c16', fontSize: 10, position: 'insideTopRight' }} />
                )}
                <Bar dataKey="total" radius={[4, 4, 0, 0]}
                  label={{ position: 'top', fontSize: 9, formatter: (v: number) => v > 0 ? `${v}h` : '' }}>
                  {trendData.map((entry) => (
                    <Cell
                      key={entry.month}
                      fill={entry.month === curMonth ? '#1B3A5C' : '#4BA8E8'}
                      fillOpacity={entry.month === curMonth ? 1 : 0.7}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <Text type="secondary" style={{ fontSize: 10, float: 'right' }}>橘虛線 = 12月平均 {overallAvg.toFixed(2)}h</Text>
          </Card>
        </Col>
        <Col xs={24} md={10}>
          <Card title={<><TeamOutlined /> {curMonth} 人員工時排名</>} size="small">
            {rankingData.length === 0
              ? <Text type="secondary">本月無資料</Text>
              : (
                <ResponsiveContainer width="100%" height={210}>
                  <BarChart data={rankingData} layout="vertical" margin={{ top: 4, right: 44, left: 8, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 10 }} unit="h" />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={52} />
                    <RcTooltip formatter={(v: number) => [`${v.toFixed(2)}h`, '工時']} />
                    <Bar dataKey="hours" fill="#1B3A5C" radius={[0, 4, 4, 0]}
                      label={{ position: 'right', fontSize: 10, formatter: (v: number) => `${v}h` }} />
                  </BarChart>
                </ResponsiveContainer>
              )
            }
          </Card>
        </Col>
      </Row>

      {/* ── 三、異常分析 ───────────────────────────────────────────── */}
      {anomalies.length > 0 ? (
        <Card
          title={<><ExclamationCircleOutlined style={{ color: '#ff4d4f' }} /> {curMonth} 異常分析（共 {anomalies.length} 筆）</>}
          size="small" style={{ marginBottom: 16 }}
        >
          <Row gutter={[8, 8]}>
            {anomalies.map((a, i) => {
              const s = anomalyStyle[a.kind]
              return (
                <Col key={i} xs={24} sm={12} md={8} lg={6}>
                  <div style={{ background: s.bg, border: `1px solid ${s.color}50`, borderRadius: 8, padding: '8px 12px' }}>
                    <Space><span style={{ color: s.color }}>{s.icon}</span>
                      <Text strong style={{ color: s.color, fontSize: 12 }}>{a.name}</Text>
                    </Space>
                    <div style={{ marginTop: 4 }}><Tag color="default" style={{ fontSize: 10 }}>{s.label}</Tag></div>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      本月 {a.cur.toFixed(2)}h{a.prev > 0 && ` | 上月 ${a.prev.toFixed(2)}h`}
                      {a.kind !== 'near_zero' && a.prev > 0 &&
                        <span style={{ color: s.color, marginLeft: 4 }}>({a.pct >= 0 ? '+' : ''}{a.pct.toFixed(0)}%)</span>}
                    </Text>
                  </div>
                </Col>
              )
            })}
          </Row>
          <Divider style={{ margin: '10px 0 6px' }} />
          <Space size={16}>
            {([['#fff1f0','#cf1322','偏高+20%'],['#fff7e6','#d46b08','偏低-20%'],['#fffbe6','#ad6800','連續3月偏高'],['#f5f5f5','#8c8c8c','趨近於零']] as [string,string,string][]).map(([bg, c, label]) => (
              <Space key={label} size={4}>
                <div style={{ width: 10, height: 10, background: bg, border: `1px solid ${c}`, borderRadius: 2 }} />
                <Text type="secondary" style={{ fontSize: 11 }}>{label}</Text>
              </Space>
            ))}
          </Space>
        </Card>
      ) : (rows.length > 0 &&
        <Alert type="success" showIcon message={`${curMonth} 人員工時均無異常波動`} style={{ marginBottom: 16 }} />
      )}

      {/* ── 四、強化明細表 ──────────────────────────────────────────── */}
      <Card
        title={<><BarChartOutlined /> 人員工時明細（可搜尋 / 排序 / 匯出）</>}
        size="small"
        extra={
          <Space wrap>
            <Input placeholder="搜尋人員" prefix={<SearchOutlined />} value={staffSearch}
              onChange={e => setStaffSearch(e.target.value)} allowClear style={{ width: 110 }} size="small" />
            <Segmented size="small" value={sortBy} onChange={v => setSortBy(v as typeof sortBy)}
              options={[{ label: '依合計', value: 'total' }, { label: '本月', value: 'current' }, { label: '波動', value: 'change' }]} />
            <Tooltip title="匯出 CSV（可用 Excel 開啟）">
              <Button size="small" icon={<DownloadOutlined />} onClick={() => exportCSV(months, rows, mtotals, grandTotal)}>匯出</Button>
            </Tooltip>
            <Button size="small" icon={<ReloadOutlined />} onClick={onReload} loading={loading}>重新載入</Button>
          </Space>
        }
      >
        <div style={{ marginBottom: 8 }}>
          <Space>
            <Tag color="blue">單位：小時（h）</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>點擊人員姓名可查看個人歷史趨勢</Text>
          </Space>
        </div>
        <Table<PivotRow>
          rowKey="staff_name" columns={pivotColumns} dataSource={allTableRows}
          loading={loading} size="small" pagination={false}
          scroll={{ x: Math.max(900, 100 + months.length * 80 + 90) }}
          rowClassName={r => r.staff_name === '__total__' ? 'row-total' : ''}
        />
      </Card>

      {/* 個人 Drawer */}
      <StaffPersonalDrawer open={!!selectedStaff} onClose={() => setSelectedStaff(null)}
        staffName={selectedStaff} data={data} />

      <style>{`
        .row-total td { background-color: #e6f4ff !important; }
        .row-total:hover td { background-color: #bae0ff !important; }
      `}</style>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════
// 主頁面
// ═══════════════════════════════════════════════════════════════════

type TableFilter = 'all' | 'abnormal' | 'unserviced'

export default function RoomMaintenanceDetailPage() {

  // ── 總表狀態 ────────────────────────────────────────────────────
  const [summaryData,    setSummaryData]    = useState<RoomSummaryRow[]>([])
  const [summaryStats,   setSummaryStats]   = useState<RoomSummaryStats>({
    total_records: 0, total_abnormal: 0, fully_ok_count: 0,
    work_hours_total: 0, unserviced_count: 0,
  })
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [dateRange,      setDateRange]      = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null])
  const [tableFilter,    setTableFilter]    = useState<TableFilter>('all')

  // ── 明細列表狀態 ─────────────────────────────────────────────────
  const [records,       setRecords]       = useState<RoomMaintenanceDetailRecord[]>([])
  const [total,         setTotal]         = useState(0)
  const [listLoading,   setListLoading]   = useState(false)
  const [listFilters,   setListFilters]   = useState<RoomMaintenanceDetailFilters>({ page: 1, per_page: 50 })
  const [roomNoInput,   setRoomNoInput]   = useState('')
  const [staffInput,    setStaffInput]    = useState('')
  const [listDateRange, setListDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null])

  // ── 房間歷史 Drawer 狀態 ─────────────────────────────────────────
  const [historyOpen,    setHistoryOpen]    = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyData,    setHistoryData]    = useState<RoomHistoryResponse | null>(null)

  // ── 人員工時表狀態 ────────────────────────────────────────────────
  const [staffHoursData,    setStaffHoursData]    = useState<StaffHoursResponse | null>(null)
  const [staffHoursLoading, setStaffHoursLoading] = useState(false)

  // ── 保養統計狀態 ──────────────────────────────────────────────────
  const [maintStatsData,    setMaintStatsData]    = useState<MaintenanceStatsResponse | null>(null)
  const [maintStatsLoading, setMaintStatsLoading] = useState(false)

  // ── 共用 ──────────────────────────────────────────────────────────
  const [syncing,    setSyncing]    = useState(false)
  const [activeTab,  setActiveTab]  = useState('summary')

  // ── 載入總表 ──────────────────────────────────────────────────────
  const loadSummary = useCallback(async (from?: string, to?: string) => {
    setSummaryLoading(true)
    try {
      const res = await fetchRoomDetailSummary(from, to)
      setSummaryData(res.data)
      setSummaryStats(res.stats)
    } catch (err) {
      console.error('[RoomMaintenanceDetail] loadSummary error:', err)
      message.error('載入總表資料失敗，請確認後端服務是否正常執行後點擊「重新載入」')
    } finally {
      setSummaryLoading(false)
    }
  }, [])

  // ── 載入明細列表 ──────────────────────────────────────────────────
  const loadRecords = useCallback(async (f: RoomMaintenanceDetailFilters) => {
    setListLoading(true)
    try {
      const res = await fetchRoomDetailRecords(f)
      setRecords(res.data)
      setTotal(res.meta?.total ?? res.data.length)
    } catch (err) {
      console.error('[RoomMaintenanceDetail] loadRecords error:', err)
      message.error('載入明細資料失敗，請確認後端服務是否正常執行後點擊「重新載入」')
    } finally {
      setListLoading(false)
    }
  }, [])

  // ── 載入人員工時表 ────────────────────────────────────────────────
  const loadStaffHours = useCallback(async () => {
    setStaffHoursLoading(true)
    try {
      const res = await fetchStaffHours(12)
      setStaffHoursData(res)
    } catch {
      message.error('載入人員工時表失敗')
    } finally {
      setStaffHoursLoading(false)
    }
  }, [])

  // ── 載入保養統計 ──────────────────────────────────────────────────
  const loadMaintStats = useCallback(async () => {
    setMaintStatsLoading(true)
    try {
      const res = await fetchMaintenanceStats(12)
      setMaintStatsData(res)
    } catch {
      message.error('載入保養統計失敗')
    } finally {
      setMaintStatsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSummary()
    loadRecords(listFilters)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // 切換到人員工時表 / 統計 Tab 時自動載入（首次才載入）
  useEffect(() => {
    const isStaffTab = activeTab === 'staff-hours' || activeTab === 'staff-hours-stats'
    if (isStaffTab && !staffHoursData && !staffHoursLoading) {
      loadStaffHours()
    }
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  // 切換到保養統計 Tab 時自動載入（首次才載入）
  useEffect(() => {
    if (activeTab === 'maintenance-stats' && !maintStatsData && !maintStatsLoading) {
      loadMaintStats()
    }
  }, [activeTab]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 開啟房間歷史 Drawer ───────────────────────────────────────────
  const openRoomHistory = useCallback(async (roomNo: string) => {
    setHistoryOpen(true)
    setHistoryLoading(true)
    setHistoryData(null)
    try {
      const res = await fetchRoomHistory(roomNo, 12)
      setHistoryData(res)
    } catch {
      message.error(`載入房號 ${roomNo} 歷史失敗`)
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  // ── 欄位定義（memorized） ─────────────────────────────────────────
  const summaryColumns = useMemo(() => buildSummaryColumns(openRoomHistory), [openRoomHistory])
  const detailColumns  = useMemo(() => buildDetailColumns(openRoomHistory),  [openRoomHistory])

  // ── 日期區間（總表） ──────────────────────────────────────────────
  const handleDateRangeChange = (vals: [dayjs.Dayjs | null, dayjs.Dayjs | null] | null) => {
    const range: [dayjs.Dayjs | null, dayjs.Dayjs | null] = vals ?? [null, null]
    setDateRange(range)
    setTableFilter('all')
    loadSummary(range[0]?.format('YYYY/MM/DD'), range[1]?.format('YYYY/MM/DD'))
  }

  // ── KPI 篩選 ──────────────────────────────────────────────────────
  const handleAbnormalClick   = () => setTableFilter(p => p === 'abnormal'   ? 'all' : 'abnormal')
  const handleUnservicedClick = () => setTableFilter(p => p === 'unserviced' ? 'all' : 'unserviced')

  // ── 同步 ──────────────────────────────────────────────────────────
  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await syncRoomDetailFromRagic()
      if (res.errors?.length) message.warning(`同步完成，有 ${res.errors.length} 筆錯誤`)
      else message.success(`同步完成：共 ${res.fetched} 筆，更新 ${res.upserted} 筆`)
      const from = dateRange[0]?.format('YYYY/MM/DD')
      const to   = dateRange[1]?.format('YYYY/MM/DD')
      await loadSummary(from, to)
      await loadRecords(listFilters)
    } catch { message.error('同步失敗') }
    finally { setSyncing(false) }
  }

  // ── 明細搜尋 ──────────────────────────────────────────────────────
  const handleListSearch = () => {
    const f: RoomMaintenanceDetailFilters = {
      ...listFilters, page: 1,
      room_no:    roomNoInput   || undefined,
      staff_name: staffInput    || undefined,
      date_from:  listDateRange[0]?.format('YYYY/MM/DD') || undefined,
      date_to:    listDateRange[1]?.format('YYYY/MM/DD') || undefined,
    }
    setListFilters(f)
    loadRecords(f)
  }
  const handleListReset = () => {
    setRoomNoInput(''); setStaffInput(''); setListDateRange([null, null])
    const f: RoomMaintenanceDetailFilters = { page: 1, per_page: listFilters.per_page }
    setListFilters(f); loadRecords(f)
  }
  const handleListTableChange = (p: TablePaginationConfig) => {
    const f: RoomMaintenanceDetailFilters = {
      ...listFilters, page: p.current ?? 1, per_page: p.pageSize ?? 50,
    }
    setListFilters(f); loadRecords(f)
  }

  // ── 篩選後的總表資料 ──────────────────────────────────────────────
  const filteredSummary = useMemo(() => {
    if (tableFilter === 'abnormal')   return summaryData.filter(r => r.serviced && r.abnormal_count > 0)
    if (tableFilter === 'unserviced') return summaryData.filter(r => !r.serviced)
    return summaryData
  }, [summaryData, tableFilter])

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { href: '/dashboard', title: <><HomeOutlined /><span>首頁</span></> },
          { title: <><ToolOutlined /><span>{NAV_GROUP.hotel}</span></> },
          { title: NAV_PAGE.roomMaintenanceDetail },
        ]}
      />

      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col><Title level={4} style={{ margin: 0 }}>{NAV_PAGE.roomMaintenanceDetail}</Title></Col>
        <Col>
          <Space>
            <Tooltip title="從本地資料庫重新載入（不連線 Ragic）">
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  const from = dateRange[0]?.format('YYYY/MM/DD')
                  const to   = dateRange[1]?.format('YYYY/MM/DD')
                  loadSummary(from, to)
                  loadRecords(listFilters)
                }}
              >
                重新載入
              </Button>
            </Tooltip>
            <Tooltip title="從 Ragic 重新同步保養明細資料">
              <Button icon={<SyncOutlined spin={syncing} />} loading={syncing} onClick={handleSync}>
                同步資料
              </Button>
            </Tooltip>
          </Space>
        </Col>
      </Row>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          /* ════════════════════════════════════════════════
             Tab 1：保養總表（主管視圖）
             ════════════════════════════════════════════════ */
          {
            key: 'summary',
            label: <span><HomeOutlined /> 保養總表</span>,
            children: (
              <div>
                {/* 日期區間 */}
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={16} align="middle">
                    <Col>
                      <Text strong style={{ marginRight: 8 }}>日期區間：</Text>
                      <RangePicker
                        format="YYYY/MM/DD"
                        value={dateRange}
                        onChange={v => handleDateRangeChange(v as [dayjs.Dayjs | null, dayjs.Dayjs | null] | null)}
                        allowClear
                        placeholder={['起始日期', '結束日期']}
                        style={{ width: 260 }}
                      />
                    </Col>
                    {dateRange[0] && (
                      <Col>
                        <Tag color="blue">
                          {dateRange[0].format('YYYY/MM/DD')} ～ {dateRange[1]?.format('YYYY/MM/DD') || '今日'}
                        </Tag>
                      </Col>
                    )}
                    <Col>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        （房號可點擊查看保養歷史追蹤）
                      </Text>
                    </Col>
                  </Row>
                </Card>

                {/* KPI 四卡 */}
                <Row gutter={12} style={{ marginBottom: 16 }}>
                  <Col xs={24} sm={12} md={6}>
                    <KpiCard title="保養記錄總數" value={summaryStats.total_records}
                      color="#1B3A5C" icon={<ToolOutlined />} suffix="筆" />
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <KpiCard title="異常項次總數" value={summaryStats.total_abnormal}
                      color={summaryStats.total_abnormal > 0 ? '#cf1322' : '#52c41a'}
                      icon={<WarningOutlined />} suffix="次"
                      clickable active={tableFilter === 'abnormal'}
                      onClick={handleAbnormalClick} />
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <KpiCard title="全項目正常房間數" value={summaryStats.fully_ok_count}
                      color="#52c41a" icon={<CheckCircleOutlined />} suffix="間" />
                  </Col>
                  <Col xs={24} sm={12} md={6}>
                    <KpiCard title="工時數"
                      value={fmtMinutes(summaryStats.work_hours_total)}
                      color="#4BA8E8" icon={<ClockCircleOutlined />} />
                  </Col>
                </Row>

                {/* 操作列 */}
                <Row justify="space-between" align="middle" style={{ marginBottom: 10 }}>
                  <Col>
                    <Space>
                      <Button
                        type={tableFilter === 'unserviced' ? 'primary' : 'default'}
                        danger={tableFilter !== 'unserviced'}
                        icon={<StopOutlined />}
                        onClick={handleUnservicedClick}
                      >
                        未保養房號（{summaryStats.unserviced_count} 間）
                      </Button>
                      {tableFilter !== 'all' && (
                        <Button onClick={() => setTableFilter('all')}>顯示全部</Button>
                      )}
                    </Space>
                  </Col>
                  <Col>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      顯示 {filteredSummary.length} / {summaryData.length} 間
                    </Text>
                  </Col>
                </Row>

                {/* 總表表格 */}
                <Card size="small">
                  <Table<RoomSummaryRow>
                    rowKey="room_no"
                    columns={summaryColumns}
                    dataSource={filteredSummary}
                    loading={summaryLoading}
                    size="small"
                    scroll={{ x: 870, y: 560 }}
                    pagination={{
                      pageSize: 50, showSizeChanger: true,
                      pageSizeOptions: ['50','100','200'],
                      showTotal: t => `共 ${t} 間`,
                    }}
                    rowClassName={(r: RoomSummaryRow) => {
                      if (!r.serviced) return 'row-unserviced'
                      if (r.abnormal_count > 0) return 'row-abnormal'
                      return ''
                    }}
                  />
                </Card>
              </div>
            ),
          },

          /* ════════════════════════════════════════════════
             Tab 2：明細清單（作業視圖）
             ════════════════════════════════════════════════ */
          {
            key: 'detail',
            label: <span><ToolOutlined /> 明細清單</span>,
            children: (
              <div>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={12} align="middle" wrap>
                    <Col xs={24} sm={8} md={4}>
                      <Input placeholder="房號" value={roomNoInput}
                        onChange={e => setRoomNoInput(e.target.value)}
                        onPressEnter={handleListSearch} allowClear />
                    </Col>
                    <Col xs={24} sm={8} md={4}>
                      <Input placeholder="保養人員" value={staffInput}
                        onChange={e => setStaffInput(e.target.value)}
                        onPressEnter={handleListSearch} allowClear />
                    </Col>
                    <Col xs={24} sm={12} md={7}>
                      <RangePicker format="YYYY/MM/DD" value={listDateRange}
                        onChange={v => setListDateRange((v as [dayjs.Dayjs|null, dayjs.Dayjs|null] | null) ?? [null,null])}
                        allowClear placeholder={['起始日期','結束日期']} style={{ width: '100%' }} />
                    </Col>
                    <Col>
                      <Space>
                        <Button type="primary" icon={<SearchOutlined />} onClick={handleListSearch}>搜尋</Button>
                        <Button icon={<ReloadOutlined />} onClick={handleListReset}>重置</Button>
                      </Space>
                    </Col>
                  </Row>
                </Card>
                <Card size="small">
                  <Table<RoomMaintenanceDetailRecord>
                    rowKey="ragic_id"
                    columns={detailColumns}
                    dataSource={records}
                    loading={listLoading}
                    size="small"
                    scroll={{ x: 1700 }}
                    pagination={{
                      current: listFilters.page, pageSize: listFilters.per_page,
                      total, showSizeChanger: true,
                      pageSizeOptions: ['20','50','100','200'],
                      showTotal: t => `共 ${t} 筆`,
                    }}
                    onChange={handleListTableChange}
                    rowClassName={r =>
                      CHECK_FIELD_KEYS.some(f => (r[f] || '').toUpperCase() === 'X') ? 'row-abnormal' : ''
                    }
                  />
                </Card>
              </div>
            ),
          },

          /* ════════════════════════════════════════════════
             Tab 3：保養統計（完成率趨勢 + 異常項目 + 樓層分析）
             ════════════════════════════════════════════════ */
          {
            key: 'maintenance-stats',
            label: <span><LineChartOutlined /> 保養統計</span>,
            children: (
              <MaintenanceStatsDashboard
                data={maintStatsData}
                loading={maintStatsLoading}
                onReload={loadMaintStats}
              />
            ),
          },

          /* ── 分隔線（視覺區隔，不可點擊） ── */
          {
            key: 'divider-hours',
            disabled: true,
            label: (
              <span style={{
                display: 'inline-block',
                width: 1,
                height: 16,
                background: '#d9d9d9',
                margin: '0 6px',
                verticalAlign: 'middle',
                cursor: 'default',
              }} />
            ),
            children: null,
          },

          /* ════════════════════════════════════════════════
             Tab 4：人員工時表（原版月報 pivot — 不可修改）
             ════════════════════════════════════════════════ */
          {
            key: 'staff-hours',
            label: <span><ClockCircleOutlined /> 人員工時表</span>,
            children: (
              <StaffHoursTab
                data={staffHoursData}
                loading={staffHoursLoading}
                onReload={loadStaffHours}
              />
            ),
          },

          /* ════════════════════════════════════════════════
             Tab 5：人員工時表統計（主管總覽 + 圖表 + 異常 + 下鑽）
             ════════════════════════════════════════════════ */
          {
            key: 'staff-hours-stats',
            label: <span><BarChartOutlined /> 人員工時表統計</span>,
            children: (
              <StaffHoursDashboard
                data={staffHoursData}
                loading={staffHoursLoading}
                onReload={loadStaffHours}
              />
            ),
          },
        ]}
      />

      {/* ── 房間保養歷史 Drawer ─────────────────────────────── */}
      <RoomHistoryDrawer
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        historyData={historyData}
        loading={historyLoading}
      />

      {/* 全域樣式 */}
      <style>{`
        .row-unserviced td { background-color: #f5f5f5 !important; color: #aaa !important; }
        .row-unserviced:hover td { background-color: #ebebeb !important; }
        .row-abnormal td { background-color: #fff5f5 !important; }
        .row-abnormal:hover td { background-color: #ffe8e8 !important; }
      `}</style>
    </div>
  )
}
