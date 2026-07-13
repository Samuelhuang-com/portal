/**
 * 行事曆 — 事件詳情抽屜
 *
 * 2026-07-13 改版，補上「明細 Drawer 強制規範」（CLAUDE.md §7 / WORK_JOURNAL_SPEC.md §9）
 * 原本缺少的項目：明細欄位區（detail dict）、附圖區（mall_pm / full_pm）、Drawer 寬度
 * 依附圖切換 480/640px。
 *
 * 標題列：[區域 Tag]  [module_label]：[identifier]  [🔗 在 Ragic 查看]
 * Body  ：① 基本資訊 Descriptions（column=2） ② 明細欄位區 Descriptions（column=1，
 *          逐渲染 detail dict） ③ 附圖區（僅 mall_pm / full_pm 且有 image_item_id 時）
 * Footer：前往原模組查看 / custom 事件：編輯、刪除
 */
import { useEffect, useState } from 'react'
import { Drawer, Tag, Button, Space, Typography, Descriptions, Popconfirm, Image, Spin, Divider } from 'antd'
import {
  LinkOutlined, EditOutlined, DeleteOutlined, EnvironmentOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { CalendarEvent, CalendarZone } from '@/types/calendar'
import { EVENT_TYPE_LABELS, ZONE_COLORS } from '@/types/calendar'
import { fetchMallPMItemImages, type PMImageItem as MallPMImageItem } from '@/api/mallPeriodicMaintenance'
import { fetchFullBldgPMItemImages, type PMImageItem as FullBldgPMImageItem } from '@/api/fullBuildingMaintenance'

const { Text } = Typography

// ── 明細欄位區狀態欄渲染（比照 §9.3「狀態欄 → 彩色 Tag」規則）───────────────────
const DETAIL_STATUS_TAG: Record<string, { color: string; label: string }> = {
  已完成: { color: 'success',    label: '已完成' },
  進行中: { color: 'processing', label: '進行中' },
  已排定: { color: 'warning',    label: '已排定' },
  未排定: { color: 'error',      label: '未排定' },
  逾期:   { color: 'error',      label: '逾期'   },
  非本月: { color: 'default',    label: '非本月' },
  預排:   { color: 'processing', label: '預排'   },
}

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

  // ── 附圖區（僅 mall_pm / full_pm，且事件帶有 image_item_id 時才查詢）──────────
  // 遵循 §9.3「有附圖模組：使用 Image.PreviewGroup，禁止另開新視窗」規範。
  const [images,        setImages]        = useState<(MallPMImageItem | FullBldgPMImageItem)[]>([])
  const [imagesLoading, setImagesLoading]  = useState(false)

  const canHaveImages = !!event?.image_item_id && (event?.event_type === 'mall_pm' || event?.event_type === 'full_pm')

  useEffect(() => {
    if (!open || !event || !canHaveImages) {
      setImages([])
      return
    }
    setImages([])
    setImagesLoading(true)
    const fetcher = event.event_type === 'mall_pm' ? fetchMallPMItemImages : fetchFullBldgPMItemImages
    fetcher(event.image_item_id)
      .then(setImages)
      .catch(() => setImages([]))
      .finally(() => setImagesLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, event?.id, canHaveImages])

  const hasImages = canHaveImages && (imagesLoading || images.length > 0)

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

  const detailEntries = event ? Object.entries(event.detail || {}) : []

  return (
    <Drawer
      title={drawerTitle}
      placement="right"
      width={hasImages ? 640 : 480}
      open={open}
      onClose={onClose}
      footer={footer}
    >
      {event && (
        <Space direction="vertical" style={{ width: '100%' }} size={16}>

          {/* ── ① 基本資訊（Descriptions column=2，見 §9.3） ─────────────────── */}
          <Descriptions
            title="基本資訊"
            column={2}
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

            {event.source_id && (
              <Descriptions.Item label="記錄 ID">
                <Text type="secondary" style={{ fontSize: 11 }}>{event.source_id}</Text>
              </Descriptions.Item>
            )}

            {event.description && (
              <Descriptions.Item label="說明" span={2}>{event.description}</Descriptions.Item>
            )}
          </Descriptions>

          {/* ── ② 明細欄位區（detail dict 逐一渲染，Descriptions column=1，見 §9.3） ── */}
          {detailEntries.length > 0 && (
            <>
              <Divider style={{ margin: '0' }} />
              <Descriptions
                title="明細欄位"
                column={1}
                size="small"
                bordered
                labelStyle={{ width: 90, whiteSpace: 'nowrap' }}
              >
                {detailEntries.map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>
                    {!v
                      ? <Text type="secondary">—</Text>
                      : k === '完成狀況'
                        ? <Tag color={DETAIL_STATUS_TAG[v]?.color ?? 'default'} style={{ margin: 0 }}>
                            {DETAIL_STATUS_TAG[v]?.label ?? v}
                          </Tag>
                        : k === '異常說明'
                          ? <Tag color="error" style={{ margin: 0 }}>{v}</Tag>
                          : <Text>{v}</Text>}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </>
          )}

          {/* ── ③ 附圖區（僅 mall_pm / full_pm，見 §9.3「禁止另開新視窗」） ─────── */}
          {hasImages && (
            <>
              <Divider style={{ margin: '0' }} />
              <div style={{ fontWeight: 500, marginBottom: 4, color: '#555', fontSize: 15 }}>附圖</div>
              {imagesLoading ? (
                <div style={{ textAlign: 'center', padding: 16 }}><Spin size="small" /></div>
              ) : (
                <Image.PreviewGroup>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                    {images.map((img, i) => (
                      <Image
                        key={i}
                        src={img.url}
                        alt={img.filename || `圖片 ${i + 1}`}
                        width={120}
                        height={90}
                        style={{ objectFit: 'cover', borderRadius: 4, border: '1px solid #e8e8e8', cursor: 'pointer' }}
                        fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
                      />
                    ))}
                  </div>
                </Image.PreviewGroup>
              )}
            </>
          )}

          {/* ── Ragic 連結（標題列已放一份，此處補完整說明文字，維持既有可讀性） ── */}
          {ragicUrl && (
            <>
              <Divider style={{ margin: '0' }} />
              <a
                href={ragicUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#4BA8E8' }}
              >
                <LinkOutlined style={{ marginRight: 4 }} />在 Ragic 查看原始記錄
              </a>
            </>
          )}

        </Space>
      )}
    </Drawer>
  )
}
