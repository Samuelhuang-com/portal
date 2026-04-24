/**
 * 行事曆 — 事件詳情抽屜
 * 點擊事件後從右側滑出，顯示事件完整資訊 + 深連結跳轉
 */
import { Drawer, Tag, Button, Space, Typography, Descriptions, Badge } from 'antd'
import {
  CalendarOutlined, UserOutlined, LinkOutlined,
  TagOutlined, InfoCircleOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { CalendarEvent } from '@/types/calendar'
import { EVENT_TYPE_LABELS } from '@/types/calendar'

const { Title, Text } = Typography

// ── 狀態顏色映射 ───────────────────────────────────────────────────────────────
const STATUS_COLOR: Record<string, string> = {
  pending:   'warning',
  completed: 'success',
  abnormal:  'error',
  overdue:   'error',
}

const STATUS_ICON: Record<string, React.ReactNode> = {
  pending:   <Badge status="warning" />,
  completed: <Badge status="success" />,
  abnormal:  <Badge status="error" />,
  overdue:   <Badge status="error" />,
}

interface EventDrawerProps {
  event:    CalendarEvent | null
  open:     boolean
  onClose:  () => void
}

export default function EventDrawer({ event, open, onClose }: EventDrawerProps) {
  const navigate = useNavigate()

  const handleDeepLink = () => {
    if (event?.deep_link) {
      onClose()
      navigate(event.deep_link)
    }
  }

  return (
    <Drawer
      title={
        <Space>
          <CalendarOutlined />
          <span>事件詳情</span>
        </Space>
      }
      placement="right"
      width={420}
      open={open}
      onClose={onClose}
      footer={
        event?.deep_link ? (
          <Button
            type="primary"
            icon={<LinkOutlined />}
            onClick={handleDeepLink}
            block
          >
            前往原模組查看
          </Button>
        ) : null
      }
    >
      {event && (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 標題 */}
          <div>
            <div style={{
              width: 4,
              height: 24,
              backgroundColor: event.color,
              borderRadius: 2,
              display: 'inline-block',
              marginRight: 10,
              verticalAlign: 'middle',
            }} />
            <Title level={4} style={{ display: 'inline', verticalAlign: 'middle' }}>
              {event.title}
            </Title>
          </div>

          {/* 標籤列 */}
          <Space wrap>
            <Tag color={event.color} icon={<TagOutlined />}>
              {EVENT_TYPE_LABELS[event.event_type as keyof typeof EVENT_TYPE_LABELS] || event.event_type}
            </Tag>
            <Tag color={STATUS_COLOR[event.status] || 'default'}>
              {event.status_label || event.status}
            </Tag>
          </Space>

          {/* 詳情表格 */}
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={<><CalendarOutlined /> 日期</>}>
              {event.start}{event.end && event.end !== event.start ? ` ～ ${event.end}` : ''}
            </Descriptions.Item>

            <Descriptions.Item label={<><TagOutlined /> 來源模組</>}>
              {event.module_label}
            </Descriptions.Item>

            {event.responsible && (
              <Descriptions.Item label={<><UserOutlined /> 負責人</>}>
                {event.responsible}
              </Descriptions.Item>
            )}

            {event.description && (
              <Descriptions.Item label={<><InfoCircleOutlined /> 說明</>}>
                {event.description}
              </Descriptions.Item>
            )}

            {event.source_id && (
              <Descriptions.Item label="記錄 ID">
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {event.source_id}
                </Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Space>
      )}
    </Drawer>
  )
}
