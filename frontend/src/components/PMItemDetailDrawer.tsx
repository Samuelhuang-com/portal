/**
 * 週期保養（hotel/periodic-maintenance）項目明細 Drawer
 *
 * 2026-07-14 新增，2026-07-14 同日改版為多筆維修記錄列表版本。
 *
 * 原始設計（初版）：因原始遷移評估（docs/FEASIBILITY_hotel_pm_sheet6_11.md）誤判
 * Ragic Sheet 11 無巢狀子表格，只做了單筆「保養時間+附圖」版本。使用者實測記錄
 * （ragic_id 277/477）證實 Sheet 11 其實有巢狀子表格「維修記錄」，欄位與 mall_pm
 * Sheet24 完全相同（項次/維修記錄/時間開始/時間結束/保養人員），使用者確認要比照
 * mall_pm 的多筆維修記錄列表模式改版，故本檔案現改為與 MallPMItemWorklogDrawer.tsx
 * 結構相同（依專案既有慣例「複製而非共用」，各自獨立維護）。
 *
 * 遵循 CLAUDE.md §7／docs/WORK_JOURNAL_SPEC.md §9「明細 Drawer 強制規範（MANDATORY）」：
 *   - Drawer 寬度：480px（無附圖）/ 640px（有附圖）
 *   - 標題列格式：[類別 Tag] [來源模組：識別碼] [🔗 在 Ragic 查看]（連結在標題列，不放 body 底部）
 *   - Body 分區：①基本欄位（Descriptions column=2）②明細欄位（Descriptions column=1，逐渲染 detail dict）
 *     ③維修記錄明細（Table，子表資料）④附圖（Image.PreviewGroup，禁止另開新視窗）
 *
 * 資料來源：Ragic Sheet 11（週期保養日誌）單筆記錄；
 * 「維修記錄」巢狀子表格 → 本地 pm_item_worklog 表 → GET /items/{id}/worklogs
 * 「圖片上傳」欄位 → 本地 pm_batch_item.images_json → GET /items/{id}/db-images
 *
 * 開發規範：本模組任何顯示「保養時間」/「維修工時」欄位的項目表格，一律要能點擊該列開此 Drawer。
 */
import { useEffect, useState } from 'react'
import { Drawer, Table, Tag, Typography, Descriptions, Divider, Spin, Image } from 'antd'
import { LinkOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import type { ColumnsType } from 'antd/es/table'
import { fetchPMItemWorklogs, fetchPMItemImages, type PMWorklogItem, type PMImageItem } from '@/api/periodicMaintenance'
import type { PMItem } from '@/types/periodicMaintenance'

const { Text } = Typography

const RAGIC_ITEM_BASE = 'https://ap12.ragic.com/soutlet001/periodic-maintenance/11'

const CATEGORY_COLOR: Record<string, string> = {
  水電: '#1890FF', 空調: '#13C2C2', 消防: '#FA541C',
  弱電: '#FAAD14', 機修: '#722ED1', 裝修: '#52C41A',
}

const STATUS_CFG: Record<string, { label: string; color: string }> = {
  completed:         { label: '已完成', color: 'success' },
  in_progress:       { label: '進行中', color: 'processing' },
  scheduled:         { label: '已排定', color: 'warning' },
  unscheduled:       { label: '未排定', color: 'error' },
  overdue:           { label: '逾期',   color: 'error' },
  non_current_month: { label: '非本月', color: 'default' },
}

function fmtHours(hours: number | null | undefined): string {
  if (hours == null) return ''
  const h = Math.floor(hours)
  const m = Math.round((hours - h) * 60)
  if (h === 0) return `${m} 分`
  if (m === 0) return `${h} 時`
  return `${h} 時 ${m} 分`
}

export interface PMItemDetailDrawerProps {
  open:    boolean
  onClose: () => void
  item:    PMItem | null
}

export default function PMItemDetailDrawer({ open, onClose, item }: PMItemDetailDrawerProps) {
  const [worklogs,        setWorklogs]        = useState<PMWorklogItem[]>([])
  const [worklogsLoading, setWorklogsLoading] = useState(false)
  const [images,          setImages]          = useState<PMImageItem[]>([])
  const [imagesLoading,   setImagesLoading]   = useState(false)

  useEffect(() => {
    if (!open || !item) return
    setWorklogs([])
    setImages([])
    setWorklogsLoading(true)
    setImagesLoading(true)
    fetchPMItemWorklogs(item.ragic_id)
      .then(setWorklogs).catch(() => setWorklogs([])).finally(() => setWorklogsLoading(false))
    fetchPMItemImages(item.ragic_id)
      .then(setImages).catch(() => setImages([])).finally(() => setImagesLoading(false))
  }, [open, item])

  const worklogColumns: ColumnsType<PMWorklogItem> = [
    { title: '項次', dataIndex: 'seq_no', width: 56, align: 'center' },
    { title: '維修記錄', dataIndex: 'repair_note', render: (v: string) => v || <Text type="secondary">—</Text> },
    {
      title: '時間開始', dataIndex: 'start_time', width: 150,
      render: (v: string) => v ? dayjs(v).format('MM/DD HH:mm') : <Text type="secondary">—</Text>,
    },
    {
      title: '時間結束', dataIndex: 'end_time', width: 150,
      render: (v: string) => v ? dayjs(v).format('MM/DD HH:mm') : <Text type="secondary">—</Text>,
    },
    { title: '保養人員', dataIndex: 'staff_name', width: 100, render: (v: string) => v || <Text type="secondary">—</Text> },
  ]

  const hasImages = imagesLoading || images.length > 0
  const ragicUrl  = item?.ragic_id ? `${RAGIC_ITEM_BASE}/${item.ragic_id}` : ''

  const detail: Array<[string, string]> = item ? [
    ['項次', item.seq_no != null ? String(item.seq_no) : ''],
    ['頻率', item.frequency || ''],
    ['執行月份', item.exec_months_raw || ''],
    ['排定人員', item.scheduler_name || ''],
    ['維修工時', fmtHours(item.repair_hours)],
    ['異常說明', item.abnormal_flag ? (item.abnormal_note || '（無說明）') : ''],
  ] : []

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={hasImages ? 640 : 480}
      styles={{ body: { padding: '16px 20px' } }}
      title={item && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Tag color={CATEGORY_COLOR[item.category] ?? 'default'} style={{ margin: 0 }}>
            {item.category || '未分類'}
          </Tag>
          <span style={{ fontSize: 16, color: '#1B3A5C', fontWeight: 600 }}>
            週期保養：<span style={{ fontWeight: 400 }}>{item.task_name}</span>
          </span>
          {ragicUrl && (
            <a
              href={ragicUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 14, color: '#4BA8E8', display: 'flex', alignItems: 'center', gap: 3, fontWeight: 400 }}
            >
              <LinkOutlined /> 在 Ragic 查看
            </a>
          )}
        </div>
      )}
    >
      {item && (
        <>
          {/* ① 基本欄位區 */}
          <Descriptions
            bordered size="small" column={2}
            labelStyle={{ width: 90, background: '#f5f7fa', fontWeight: 500 }}
            contentStyle={{ background: '#fff' }}
          >
            <Descriptions.Item label="排定日期">{item.scheduled_date || '—'}</Descriptions.Item>
            <Descriptions.Item label="預估耗時">{item.estimated_minutes ? `${item.estimated_minutes} 分` : '—'}</Descriptions.Item>
            <Descriptions.Item label="執行人員">{item.executor_name || '—'}</Descriptions.Item>
            <Descriptions.Item label="狀態">
              <Tag color={STATUS_CFG[item.status]?.color ?? 'default'} style={{ margin: 0 }}>
                {STATUS_CFG[item.status]?.label ?? item.status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="備註" span={2}>
              {item.result_note || <Text type="secondary">—</Text>}
            </Descriptions.Item>
          </Descriptions>

          {/* ② 明細欄位區（原始 Ragic 欄位，逐一列出） */}
          <Divider style={{ margin: '16px 0 12px' }} />
          <Descriptions
            bordered size="small" column={1}
            labelStyle={{ width: 96, background: '#f5f7fa', fontWeight: 500 }}
            contentStyle={{ background: '#fff' }}
          >
            {detail.map(([k, v]) => (
              <Descriptions.Item key={k} label={k}>
                {!v
                  ? <Text type="secondary">—</Text>
                  : k === '異常說明'
                    ? <Tag color="error" style={{ margin: 0 }}>{v}</Tag>
                    : <Text>{v}</Text>}
              </Descriptions.Item>
            ))}
          </Descriptions>

          {/* ③ 維修記錄明細（子表） */}
          <Divider style={{ margin: '16px 0 8px' }} />
          <div style={{ fontWeight: 500, marginBottom: 8, color: '#555', fontSize: 15 }}>維修記錄明細</div>
          <Table<PMWorklogItem>
            rowKey="ragic_id"
            columns={worklogColumns}
            dataSource={worklogs}
            loading={worklogsLoading}
            pagination={false}
            size="small"
            locale={{ emptyText: '尚無維修記錄（同仁尚未於 Ragic 回填）' }}
          />

          {/* ④ 附圖區 */}
          {hasImages && (
            <>
              <Divider style={{ margin: '16px 0 8px' }} />
              <div style={{ fontWeight: 500, marginBottom: 8, color: '#555', fontSize: 15 }}>附圖</div>
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
        </>
      )}
    </Drawer>
  )
}
