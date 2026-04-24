/**
 * 行事曆 — 今日重點面板
 * 顯示今日各類型事件的清單，點擊可開啟詳情抽屜
 */
import { Card, List, Tag, Empty, Typography, Badge, Spin } from 'antd'
import {
  CalendarOutlined, WarningOutlined, CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import type { CalendarEvent, CalendarEventType } from '@/types/calendar'
import { EVENT_TYPE_LABELS, EVENT_TYPE_COLORS } from '@/types/calendar'

const { Text } = Typography

// ── 狀態圖示 ──────────────────────────────────────────────────────────────────
function StatusIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircleOutlined style={{ color: '#52c41a' }} />
  if (status === 'abnormal')  return <WarningOutlined style={{ color: '#ff4d4f' }} />
  if (status === 'overdue')   return <WarningOutlined style={{ color: '#ff4d4f' }} />
  return <ClockCircleOutlined style={{ color: '#faad14' }} />
}

interface TodayPanelProps {
  events:    CalendarEvent[]
  loading:   boolean
  onSelect:  (event: CalendarEvent) => void
}

// ── 事件類型優先排序 ───────────────────────────────────────────────────────────
const TYPE_ORDER: CalendarEventType[] = [
  'approval', 'hotel_pm', 'mall_pm', 'security', 'inspection', 'memo', 'custom',
]

export default function TodayPanel({ events, loading, onSelect }: TodayPanelProps) {
  if (loading) {
    return (
      <Card title={<><CalendarOutlined /> 今日重點</>} size="small">
        <div style={{ textAlign: 'center', padding: 32 }}>
          <Spin />
        </div>
      </Card>
    )
  }

  if (!events.length) {
    return (
      <Card title={<><CalendarOutlined /> 今日重點</>} size="small">
        <Empty description="今日暫無事件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    )
  }

  // 依類型分組
  const grouped: Partial<Record<CalendarEventType, CalendarEvent[]>> = {}
  for (const ev of events) {
    const t = ev.event_type as CalendarEventType
    if (!grouped[t]) grouped[t] = []
    grouped[t]!.push(ev)
  }

  const sortedTypes = TYPE_ORDER.filter((t) => grouped[t]?.length)

  return (
    <Card
      title={
        <span>
          <CalendarOutlined style={{ marginRight: 8 }} />
          今日重點
          <Badge
            count={events.length}
            size="small"
            style={{ marginLeft: 8, backgroundColor: '#1677ff' }}
          />
        </span>
      }
      size="small"
      bodyStyle={{ padding: '8px 0', maxHeight: 'calc(100vh - 300px)', overflowY: 'auto' }}
    >
      {sortedTypes.map((type) => {
        const typeEvents = grouped[type] || []
        const color      = EVENT_TYPE_COLORS[type]
        const label      = EVENT_TYPE_LABELS[type]

        return (
          <div key={type}>
            {/* 類型標題 */}
            <div style={{
              padding: '6px 16px',
              backgroundColor: '#fafafa',
              borderLeft: `3px solid ${color}`,
              fontSize: 12,
              fontWeight: 600,
              color: '#555',
            }}>
              {label}
              <Badge
                count={typeEvents.length}
                size="small"
                style={{ marginLeft: 6, backgroundColor: color }}
              />
            </div>

            {/* 事件清單 */}
            <List
              size="small"
              dataSource={typeEvents.slice(0, 5)}  // 每類最多顯示 5 筆
              renderItem={(ev) => (
                <List.Item
                  key={ev.id}
                  style={{ cursor: 'pointer', padding: '6px 16px' }}
                  onClick={() => onSelect(ev)}
                >
                  <List.Item.Meta
                    avatar={<StatusIcon status={ev.status} />}
                    title={
                      <Text
                        ellipsis
                        style={{ fontSize: 12, maxWidth: 160 }}
                        title={ev.title}
                      >
                        {ev.title.replace(/^\[[^\]]+\]\s*/, '')}
                      </Text>
                    }
                    description={
                      ev.responsible
                        ? <Text type="secondary" style={{ fontSize: 11 }}>{ev.responsible}</Text>
                        : undefined
                    }
                  />
                  <Tag color={ev.status === 'completed' ? 'success' : ev.status === 'abnormal' ? 'error' : 'warning'} style={{ fontSize: 10, margin: 0 }}>
                    {ev.status_label}
                  </Tag>
                </List.Item>
              )}
            />
            {typeEvents.length > 5 && (
              <div style={{ padding: '4px 16px', fontSize: 11, color: '#999' }}>
                ... 還有 {typeEvents.length - 5} 筆
              </div>
            )}
          </div>
        )
      })}
    </Card>
  )
}
