/**
 * 工作日誌單筆明細 Drawer（獨立元件）— 2026-10-05 新增，供「人員動線」TAB 使用
 *
 * 呈現規則完全比照 shared.tsx::DayPersonCollapse 內建的 Drawer（CLAUDE.md §7）：
 *  - 標題列：[Category Tag]  [source_label]：[identifier]  [🔗 在 Ragic 查看]
 *  - identifier：報修編號 > 日誌編號 > 房號 > ragic_id
 *  - 兩區 Descriptions（基本欄位／明細欄位）、維修記錄子表、附圖 Image.PreviewGroup
 *
 * DayPersonCollapse 仍用自己內建的 Drawer（不動既有頁面）；兩者若要合併為一份，另案處理。
 */
import React, { useEffect, useState } from 'react'
import { Typography, Tag, Table, Drawer, Descriptions, Divider, Spin, Image } from 'antd'
import { LinkOutlined } from '@ant-design/icons'

import {
  fetchJournalImages, IMAGE_CAPABLE_SOURCES,
  type JournalRow, type CaseImageItem,
  CATEGORY_COLOR,
} from '@/api/workJournal'

const { Text } = Typography

const STATUS_COLOR: Record<string, string> = {
  '已完成': '#52c41a', '已修復': '#52c41a', '已結案': '#52c41a', '已調整': '#52c41a', '已固定': '#52c41a',
  '完成':   '#52c41a',
  '待辦驗': '#faad14', '未完成': '#faad14', '進行中': '#1677ff',
}

export default function JournalRowDrawer({
  row, onClose, extra, getContainer,
}: {
  row: JournalRow | null
  onClose: () => void
  /** 額外的基本欄位（例：人員動線的「定位依據」），接在基本欄位最後 */
  extra?: { label: string; value: React.ReactNode }[]
  /** 掛載容器（全螢幕時須掛在全螢幕元素內才看得到）；省略＝document.body */
  getContainer?: () => HTMLElement
}) {
  const [images, setImages] = useState<CaseImageItem[]>([])
  const [imgLoading, setImgLoading] = useState(false)

  useEffect(() => {
    setImages([])
    if (!row || !row.ragic_id || !IMAGE_CAPABLE_SOURCES.has(row.source)) return
    let alive = true
    setImgLoading(true)
    fetchJournalImages(row.source, row.ragic_id)
      .then(imgs => { if (alive) setImages(imgs) })
      .catch(() => { if (alive) setImages([]) })
      .finally(() => { if (alive) setImgLoading(false) })
    return () => { alive = false }
  }, [row])

  const d = row?.detail ?? {}
  const identifier = d['報修編號'] || d['日誌編號'] || d['房號'] || row?.ragic_id || ''

  return (
    <Drawer
      open={!!row}
      onClose={onClose}
      getContainer={getContainer ?? undefined}
      width={row && IMAGE_CAPABLE_SOURCES.has(row.source) ? 640 : 480}
      styles={{ body: { padding: '16px 20px' } }}
      title={row && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Tag color={CATEGORY_COLOR[row.category as keyof typeof CATEGORY_COLOR]} style={{ margin: 0 }}>
            {row.category}
          </Tag>
          <span style={{ fontSize: 16, color: '#1B3A5C', fontWeight: 600 }}>
            {row.source_label}
            {identifier && <>：<span style={{ fontWeight: 400 }}>{identifier}</span></>}
          </span>
          {!!row.ragic_url && (
            <a
              href={row.ragic_url}
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
      {row && (
        <>
          <Typography.Title level={5} style={{ margin: '0 0 12px', color: '#1B3A5C' }}>
            {row.task}
          </Typography.Title>
          <Descriptions
            bordered size="small" column={1}
            labelStyle={{ width: 100, background: '#f5f7fa', fontWeight: 500 }}
            contentStyle={{ background: '#fff' }}
          >
            <Descriptions.Item label="人員">{row.person}</Descriptions.Item>
            <Descriptions.Item label="來源">{row.source_label}</Descriptions.Item>
            {row.source === 'other_tasks' && !!row.venue && (
              <Descriptions.Item label="歸屬">
                <Tag color={row.venue === '飯店' ? '#1565C0' : '#2E7D32'} style={{ margin: 0 }}>{row.venue}</Tag>
              </Descriptions.Item>
            )}
            {row.work_min != null && (
              <Descriptions.Item label="工時(min)">
                <Text strong style={{ color: '#1B3A5C' }}>{row.work_min}</Text>
              </Descriptions.Item>
            )}
            {!!(row.start_dt || row.start_time) && (
              <Descriptions.Item label="時間起">{row.start_dt || row.start_time}</Descriptions.Item>
            )}
            {!!(row.end_dt || row.end_time) && (
              <Descriptions.Item label="時間迄">{row.end_dt || row.end_time}</Descriptions.Item>
            )}
            {!!row.remark && (
              <Descriptions.Item label="備註"><Text style={{ color: '#666' }}>{row.remark}</Text></Descriptions.Item>
            )}
            {!!row.report && (
              <Descriptions.Item label="回報事項"><Text style={{ color: '#d46b08' }}>{row.report}</Text></Descriptions.Item>
            )}
            {(extra ?? []).map(e => (
              <Descriptions.Item key={e.label} label={e.label}>{e.value}</Descriptions.Item>
            ))}
          </Descriptions>

          {Object.keys(d).length > 0 && (
            <>
              <Divider style={{ margin: '16px 0 12px' }} />
              <Descriptions
                bordered size="small" column={1}
                labelStyle={{ width: 96, background: '#f5f7fa', fontWeight: 500, fontSize: 15 }}
                contentStyle={{ background: '#fff', fontSize: 15 }}
              >
                {Object.entries(d).map(([k, v]) => {
                  let content: React.ReactNode
                  if (!v) content = <Text type="secondary">—</Text>
                  else if (k === '處理狀況' || k === '完成狀況' || k === '狀態')
                    content = <Tag color={STATUS_COLOR[v] ?? 'default'} style={{ margin: 0 }}>{v}</Tag>
                  else if (k === '報修類型') content = <Tag style={{ margin: 0 }}>{v}</Tag>
                  else if (k === '總費用') content = <Text strong style={{ fontSize: 16 }}>${v}</Text>
                  else if (k.includes('費用')) content = <Text>${v}</Text>
                  else if (k === '標題') content = <Text strong style={{ fontSize: 16 }}>{v}</Text>
                  else content = <Text>{v}</Text>
                  return <Descriptions.Item key={k} label={k}>{content}</Descriptions.Item>
                })}
              </Descriptions>
            </>
          )}

          {(row.detail_records?.length ?? 0) > 0 && (
            <>
              <Divider style={{ margin: '16px 0 8px' }} />
              <div style={{ fontWeight: 500, marginBottom: 8, color: '#555', fontSize: 15 }}>維修記錄明細</div>
              <Table
                size="small"
                pagination={false}
                dataSource={(row.detail_records ?? []).map((r, i) => ({ ...r, key: i }))}
                scroll={{ x: 'max-content' }}
                columns={[
                  { title: '項次', dataIndex: '項次', key: 'seq', width: 44, align: 'center' as const,
                    render: (v: string) => <Text style={{ fontSize: 13, color: '#888' }}>{v || '—'}</Text> },
                  ...((row.detail_records ?? []).some(r => r['狀態']) ? [{
                    title: '狀態', dataIndex: '狀態', key: 'status', width: 64, align: 'center' as const,
                    render: (v: string) => v
                      ? <Tag color={STATUS_COLOR[v] ?? 'default'} style={{ margin: 0 }}>{v}</Tag>
                      : <Text style={{ color: '#ccc' }}>—</Text>,
                  }] : []),
                  { title: '維修記錄', dataIndex: '維修記錄', key: 'record', width: 160,
                    render: (v: string) => <Text style={{ fontSize: 13 }}>{v || '—'}</Text> },
                  { title: '時間開始', dataIndex: '時間開始', key: 'start', width: 128, align: 'center' as const,
                    render: (v: string) => <Text style={{ fontSize: 12, color: '#666' }}>{v || '—'}</Text> },
                  { title: '時間結束', dataIndex: '時間結束', key: 'end', width: 128, align: 'center' as const,
                    render: (v: string) => <Text style={{ fontSize: 12, color: '#666' }}>{v || '—'}</Text> },
                  { title: '維修人員', dataIndex: '維修人員', key: 'person', width: 72, align: 'center' as const,
                    render: (v: string) => <Text style={{ fontSize: 13 }}>{v || '—'}</Text> },
                ]}
              />
            </>
          )}

          {(imgLoading || images.length > 0) && (
            <>
              <Divider style={{ margin: '16px 0 8px' }} />
              <div style={{ fontWeight: 500, marginBottom: 8, color: '#555', fontSize: 15 }}>維修圖片</div>
              {imgLoading
                ? <div style={{ textAlign: 'center', padding: 16 }}><Spin size="small" /></div>
                : (
                  <Image.PreviewGroup preview={getContainer ? { getContainer } : undefined}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {images.map((img, i) => (
                        <Image
                          key={i}
                          src={img.url}
                          alt={img.filename || `圖片 ${i + 1}`}
                          width={120}
                          height={90}
                          style={{ objectFit: 'cover', borderRadius: 4, border: '1px solid #e8e8e8', cursor: 'pointer' }}
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
