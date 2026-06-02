/**
 * 行事曆 — 事件詳情抽屜
 *
 * 標題列：[區域 Tag]  [module_label]：[identifier]  [🔗 在 Ragic 查看]
 * Body  ：① 基本資訊 Descriptions  ② 詳細說明 Descriptions
 * Footer：前往原模組查看 / custom 事件：編輯、刪除
 */
import { Drawer, Tag, Button, Space, Typography, Descriptions, Popconfirm } from 'antd'
import {
  LinkOutlined, EditOutlined, DeleteOutlined, EnvironmentOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { CalendarEvent, CalendarZone } from '@/types/calendar'
import { EVENT_TYPE_LABELS, ZONE_COLORS } from '@/types/calendar'

const { Text } = Typography

// ── 狀態 → Ant Design Tag color ───────────────────────────────────────────────
const STATUS_TAG: Record<string, { color: string; label: string }> = {
  pending:   { color: 'warning',    label: '待執行' },
  completed: { color: 'success',    label: '已完成' },
  abnormal:  { color: 'error',      label: '異常'   },
  overdue:   { color: 'error',      label: '逾期'   },
  預排:      { color: 'processing', label: '預排'   },
  已巡檢:    { color: 'success',    label: '已巡檢' },
  已發布:    { color: 'success',    label: '已發布' },
  待簽核:    { color: 'warning',    label: '待簽核' },
  已核准:    { color: 'success',    label: '已核准' },
  已退回:    { color: 'error',      label: '已退回' },
  自訂:      { color: 'default',    label: '自訂'   },
}

function StatusTag({ status, statusLabel }: { status: string; statusLabel: string }) {
  const cfg = STATUS_TAG[statusLabel] ?? STATUS_TAG[status] ?? { color: 'default', label: statusLabel || status }
  return <Tag color={cfg.color}>{cfg.label}</Tag>
}

function val(v?: string | null): React.ReactNode {
  return v?.trim() ? v : <Text type="secondary">—</Text>
}

function cleanTitle(title: string): string {
  return title.replace(/^\[.*?\]\s*/, '').trim() || title
}

interface EventDrawerProps {
  event:     CalendarEvent | null
  open:      boolean
  onClose:   () => void
  onEdit?:   (event: CalendarEvent) => void
  onDelete?: (event: CalendarEvent) => void
}

export default function EventDrawer({ event, open, onClose, onEdit, onDelete }: EventDrawerProps) {
  const navigate  = useNavigate()
  const isCustom  = event?.event_type === 'custom'

  const zoneColor   = event?.zone ? (ZONE_COLORS[event.zone as CalendarZone] ?? '#8c8c8c') : '#8c8c8c'
  const moduleLabel = event?.module_label?.replace(/（.*?）/, '') ?? ''
  const identifier  = event ? cleanTitle(event.title) : ''
  const ragicUrl    = event?.ragic_url ?? ''

  // ── 標題列 ──────────────────────────────────────────────────────────────────
  const drawerTitle = event ? (
    <Space size={8} wrap style={{ lineHeight: 1.8 }}>
      {event.zone && (
        <Tag icon={<EnvironmentOutlined />} color={zoneColor} style={{ margin: 0 }}>
          {event.zone}
        </Tag>
      )}
      <span style={{ fontWeight: 600 }}>
        {moduleLabel}{identifier ? `：${identifier}` : ''}
      </span>
      {ragicUrl && (
        <a
          href={ragicUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#4BA8E8', fontSize: 13 }}
        >
          <LinkOutlined style={{ marginRight: 3 }} />在 Ragic 查看
        </a>
      )}
    </Space>
  ) : '事件詳情'

  // ── Footer ──────────────────────────────────────────────────────────────────
  const footer = event ? (
    <Space direction="vertical" style={{ width: '100%' }} size={8}>
      {isCustom && (
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
            <Button danger icon={<DeleteOutlined />} style={{ flex: 1 }}>刪除</Button>
          </Popconfirm>
        </Space>
      )}
      {event.deep_link && (
        <Button
          type="primary"
          icon={<LinkOutlined />}
          block
          onClick={() => { onClose(); navigate(event.deep_link) }}
        >
          前往原模組查看
        </Button>
      )}
    </Space>
  ) : null

  return (
    <Drawer
      title={drawerTitle}
      placement="right"
      width={480}
      open={open}
      onClose={onClose}
      footer={footer}
    >
      {event && (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>

          {/* ── ① 基本資訊 ─────────────────────────────────────────────────── */}
          <Descriptions
            title="基本資訊"
            column={1}
            size="small"
            bordered
            labelStyle={{ width: 90, whiteSpace: 'nowrap' }}
          >
            <Descriptions.Item label="日期">
              {event.start}
              {event.end && event.end !== event.start ? ` ～ ${event.end}` : ''}
            </Descriptions.Item>

            <Descriptions.Item label="狀態">
              <StatusTag status={event.status} statusLabel={event.status_label} />
              {isCustom && (
                <Tag icon={<EditOutlined />} color="default" style={{ marginLeft: 4 }}>
                  可編輯
                </Tag>
              )}
            </Descriptions.Item>

            <Descriptions.Item label="來源模組">
              <Tag color={event.color}>
                {EVENT_TYPE_LABELS[event.event_type as keyof typeof EVENT_TYPE_LABELS] || event.event_type}
              </Tag>
            </Descriptions.Item>

            <Descriptions.Item label="區域">
              {event.zone
                ? <Tag color={zoneColor}>{event.zone}</Tag>
                : <Text type="secondary">—</Text>
              }
            </Descriptions.Item>

            <Descriptions.Item label="負責人">{val(event.responsible)}</Descriptions.Item>
          </Descriptions>

          {/* ── ② 詳細說明 ─────────────────────────────────────────────────── */}
          <Descriptions
            title="詳細說明"
            column={1}
            size="small"
            bordered
            labelStyle={{ width: 90, whiteSpace: 'nowrap' }}
          >
            {event.description && (
              <Descriptions.Item label="說明">{event.description}</Descriptions.Item>
            )}

            {event.source_id && (
              <Descriptions.Item label="記錄 ID">
                <Text type="secondary" style={{ fontSize: 11 }}>{event.source_id}</Text>
              </Descriptions.Item>
            )}

            {ragicUrl && (
              <Descriptions.Item label="Ragic 連結">
                <a
                  href={ragicUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#4BA8E8' }}
                >
                  <LinkOutlined style={{ marginRight: 4 }} />在 Ragic 查看原始記錄
                </a>
              </Descriptions.Item>
            )}
          </Descriptions>

        </Space>
      )}
    </Drawer>
  )
}
