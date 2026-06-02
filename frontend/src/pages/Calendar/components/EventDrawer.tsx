/**
 * 行事曆 — 事件詳情抽屜
 * 點擊事件後從右側滑出，顯示事件完整資訊 + 深連結跳轉
 *
 * 若事件類型為 custom（自訂事件），footer 額外顯示「編輯」「刪除」按鈕。
 */
import { Drawer, Tag, Button, Space, Typography, Descriptions, Badge, Popconfirm } from 'antd'
import {
  CalendarOutlined, UserOutlined, LinkOutlined,
  TagOutlined, InfoCircleOutlined, EditOutlined, DeleteOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { CalendarEvent } from '@/types/calendar'
import { EVENT_TYPE_LABELS, ZONE_COLORS } from '@/types/calendar'

const { Title, Text } = Typography

// ── 狀態顏色映射 ───────────────────────────────────────────────────────────────
const STATUS_COLOR: Record<string, string> = {
  pending:   'warning',
  completed: 'success',
  abnormal:  'error',
  overdue:   'error',
}

interface EventDrawerProps {
  event:     CalendarEvent | null
  open:      boolean
  onClose:   () => void
  /** 僅 custom 事件有效：開啟編輯 Modal */
  onEdit?:   (event: CalendarEvent) => void
  /** 僅 custom 事件有效：確認後刪除 */
  onDelete?: (event: CalendarEvent) => void
}

export default function EventDrawer({
  event,
  open,
  onClose,
  onEdit,
  onDelete,
}: EventDrawerProps) {
  const navigate = useNavigate()
  const isCustom = event?.event_type === 'custom'

  const handleDeepLink = () => {
    if (event?.deep_link) {
      onClose()
      navigate(event.deep_link)
    }
  }

  // ── Footer ────────────────────────────────────────────────────────────────
  const renderFooter = () => {
    if (!event) return null

    const deepLinkBtn = event.deep_link ? (
      <Button
        type="primary"
        icon={<LinkOutlined />}
        onClick={handleDeepLink}
        block={!isCustom}
      >
        前往原模組查看
      </Button>
    ) : null

    if (!isCustom) return deepLinkBtn

    // 自訂事件：顯示編輯 + 刪除 + 深連結（通常 custom 沒有 deep_link，但防守）
    return (
      <Space direction="vertical" style={{ width: '100%' }} size={8}>
        <Space style={{ width: '100%' }}>
          <Button
            icon={<EditOutlined />}
            style={{ flex: 1 }}
            onClick={() => { onEdit?.(event); onClose() }}
          >
            編輯
          </Button>
          <Popconfirm
            title="確定要刪除此事件嗎？"
            description="刪除後無法復原"
            okText="確定刪除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => { onDelete?.(event); onClose() }}
          >
            <Button danger icon={<DeleteOutlined />} style={{ flex: 1 }}>
              刪除
            </Button>
          </Popconfirm>
        </Space>
        {deepLinkBtn}
      </Space>
    )
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
      footer={renderFooter()}
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
            {event.zone && (
              <Tag
                icon={<EnvironmentOutlined />}
                color={ZONE_COLORS[event.zone as keyof typeof ZONE_COLORS] || '#8c8c8c'}
              >
                {event.zone}
              </Tag>
            )}
            <Tag color={STATUS_COLOR[event.status] || 'default'}>
              {event.status_label || event.status}
            </Tag>
            {isCustom && (
              <Tag icon={<EditOutlined />} color="default">
                可編輯
              </Tag>
            )}
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
