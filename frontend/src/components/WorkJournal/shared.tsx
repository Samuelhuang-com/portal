/**
 * 工作日誌共用渲染元件
 *
 * 自 ExecWorkDashboard/index.tsx 抽出（行為零變更），供以下頁面共用：
 *  - ExecWorkDashboard 工作日誌 TAB
 *  - LuqunRepair「未指定工作日誌」TAB
 *
 * 包含：
 *  - CAT_COLS / JournalCategory / JournalMode 共用型別與常數
 *  - ShiftTag           班別 Tag（含「未指定」警示 icon）
 *  - DayPersonCollapse  單一日期的人員分組 Collapse + 明細 Drawer（含 Ragic 連結、附圖 Lightbox）
 *  - isHotelRow         判斷工作日誌一行是否屬飯店
 */
import React, { useEffect, useState } from 'react'
import {
  Typography, Tag, Table, Collapse, Space, Tooltip,
  Drawer, Descriptions, Divider, Spin, Image,
} from 'antd'
import {
  UserDeleteOutlined, MinusCircleOutlined, FileUnknownOutlined, LinkOutlined,
} from '@ant-design/icons'

import {
  fetchJournalImages,
  type WorkJournalDaily, type JournalRow, type CaseImageItem,
  CATEGORY_COLOR,
} from '@/api/workJournal'
import type { ShiftInfo } from '@/api/schedule'

const { Text } = Typography

// ── 共用型別與常數 ─────────────────────────────────────────────────────────────
export type JournalCategory = '現場報修' | '上級交辦' | '緊急事件' | '例行維護' | '每日巡檢'
export const CAT_COLS: JournalCategory[] = ['現場報修', '上級交辦', '緊急事件', '例行維護', '每日巡檢']

export type JournalMode = 'single' | 'range' | 'month' | 'person' | 'unassigned'

// ── 飯店/商場判斷 ─────────────────────────────────────────────────────────────
const _HOTEL_SOURCES = new Set<string>(['dazhi', 'hotel_pm', 'ihg', 'hotel_di'])

/** 判斷工作日誌一行是否屬飯店。
 *  other_tasks 以 venue 欄位為準；其餘來源以 source 集合判斷。 */
export function isHotelRow(row: JournalRow): boolean {
  if (row.source === 'other_tasks') return row.venue === '飯店'
  return _HOTEL_SOURCES.has(row.source)
}

// 班別 Tag 渲染輔助
// shiftMap = undefined → 班表資料尚未載入，不顯示任何標記
// shiftMap = {}        → 已載入但該日無班表資料，仍不顯示（避免誤報）
// shiftMap 有資料      → 依 is_working 判斷顯示彩色代碼或紅色 ?
export function ShiftTag({
  person,
  shiftMap,
}: {
  person:   string
  shiftMap: Record<string, ShiftInfo> | undefined
}) {
  // 警示 icon 共用樣式
  const warnTagStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: 16, padding: '0 4px',
    lineHeight: '20px', marginRight: 4, cursor: 'default',
  }

  // 「未指定」人員 → UserDeleteOutlined（身分不明）
  if (person === '未指定') return (
    <Tooltip title="人員未指定" placement="top">
      <Tag color="error" style={warnTagStyle}>
        <UserDeleteOutlined />
      </Tag>
    </Tooltip>
  )

  // 班表資料未載入或整日無班表 → 不顯示
  if (!shiftMap || Object.keys(shiftMap).length === 0) return null

  const info = shiftMap[person]

  // 有班表記錄 + 非上班班別 → MinusCircleOutlined（明確排休）
  if (info && !info.is_working) {
    const tipText = info.shift_name
      ? `${info.shift_code}（${info.shift_name}）— 非上班班別`
      : `${info.shift_code} — 非上班班別`
    return (
      <Tooltip title={tipText} placement="top">
        <Tag color="error" style={warnTagStyle}>
          <MinusCircleOutlined />
        </Tag>
      </Tooltip>
    )
  }

  // 無班表記錄（有工單卻沒排班）→ FileUnknownOutlined（查無記錄）
  if (!info) return (
    <Tooltip title="此日無班表記錄" placement="top">
      <Tag color="warning" style={warnTagStyle}>
        <FileUnknownOutlined />
      </Tag>
    </Tooltip>
  )

  // 正常上班班別 → 彩色班別代碼 + Tooltip 顯示班別名稱
  const tipText = info.shift_name
    ? `${info.shift_code}｜${info.shift_name}`
    : info.shift_code
  return (
    <Tooltip title={tipText} placement="top">
      <Tag
        style={{
          backgroundColor: info.shift_color,
          color: '#fff',
          fontWeight: 700,
          fontSize: 15,
          minWidth: 26,
          textAlign: 'center',
          padding: '0 5px',
          lineHeight: '20px',
          marginRight: 4,
          border: 'none',
          cursor: 'default',
        }}
      >
        {info.shift_code}
      </Tag>
    </Tooltip>
  )
}

// 單一日期的人員分組 Collapse（單日 or 區間內每天複用）
export function DayPersonCollapse({
  persons,
  collapsed,
  shiftMap,
}: {
  persons:   WorkJournalDaily['persons']
  collapsed?: boolean
  shiftMap?:  Record<string, ShiftInfo>
}) {
  const [selectedRow, setSelectedRow] = useState<JournalRow | null>(null)
  const [drawerImages, setDrawerImages] = useState<CaseImageItem[]>([])
  const [imgLoading,   setImgLoading]   = useState(false)
  const [personActiveKeys, setPersonActiveKeys] = useState<string[]>(() =>
    persons.map((_, i) => `person-${i}`)
  )
  useEffect(() => {
    if (collapsed === undefined) return
    setPersonActiveKeys(collapsed ? [] : persons.map((_, i) => `person-${i}`))
  }, [collapsed]) // eslint-disable-line react-hooks/exhaustive-deps

  const journalColumns = [
    {
      title: '項次', dataIndex: 'seq', key: 'seq', width: 48, align: 'center' as const,
      render: (v: number) => <Text style={{ fontSize: 14, color: '#888' }}>{v}</Text>,
    },
    ...CAT_COLS.map(cat => ({
      title: <span style={{ fontSize: 13, color: CATEGORY_COLOR[cat as JournalCategory], whiteSpace: 'nowrap' as const }}>{cat}</span>,
      key: cat, width: 56, align: 'center' as const,
      render: (_: unknown, row: JournalRow) =>
        row.category === cat
          ? <span style={{ color: CATEGORY_COLOR[cat as JournalCategory], fontSize: 18, fontWeight: 700 }}>✓</span>
          : null,
    })),
    {
      title: '工作事項', dataIndex: 'task', key: 'task', width: 200,
      render: (v: string, row: JournalRow) => {
        const isHotel = isHotelRow(row)
        return (
          <Text style={{ fontSize: 14 }}>
            <span style={{
              display: 'inline-block', marginRight: 4,
              fontSize: 11, fontWeight: 700, lineHeight: '16px',
              padding: '0 4px', borderRadius: 3,
              background: isHotel ? '#e8f4fd' : '#e8f5e9',
              color:      isHotel ? '#1565C0' : '#2E7D32',
            }}>{isHotel ? '飯' : '商'}</span>
            {v}
          </Text>
        )
      },
    },
    {
      title: '預估耗時(min)', dataIndex: 'est_min', key: 'est_min', width: 88, align: 'center' as const,
      render: (v: number | null) => v != null
        ? <Text style={{ fontSize: 14 }}>{v}</Text>
        : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '起', dataIndex: 'start_time', key: 'start', width: 52, align: 'center' as const,
      render: (v: string) => v ? <Text style={{ fontSize: 14 }}>{v}</Text> : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '迄', dataIndex: 'end_time', key: 'end', width: 52, align: 'center' as const,
      render: (v: string) => v ? <Text style={{ fontSize: 14 }}>{v}</Text> : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '工時(min)', dataIndex: 'work_min', key: 'wh', width: 72, align: 'center' as const,
      render: (v: number | null) => v != null
        ? <Text strong style={{ fontSize: 14, color: '#1B3A5C' }}>{v}</Text>
        : <Text style={{ color: '#ccc', fontSize: 14 }}>—</Text>,
    },
    {
      title: '備註', dataIndex: 'remark', key: 'remark', width: 160,
      render: (v: string) => v ? <Text style={{ fontSize: 14, color: '#666' }}>{v}</Text> : null,
    },
    {
      title: '回報事項', dataIndex: 'report', key: 'report', width: 160,
      render: (v: string) => v ? <Text style={{ fontSize: 14, color: '#d46b08' }}>{v}</Text> : null,
    },
  ]

  if (!persons.length) return (
    <div style={{ textAlign: 'center', color: '#aaa', padding: '12px 0' }}>此日無工作記錄</div>
  )

  const STATUS_COLOR: Record<string, string> = {
    '已完成': '#52c41a', '已修復': '#52c41a', '已結案': '#52c41a', '已調整': '#52c41a', '已固定': '#52c41a',
    '待辦驗': '#faad14', '未完成': '#faad14', '進行中': '#1677ff',
  }

  const items = persons.map((p, idx) => {
    const totalWH = p.rows.reduce((acc, r) => acc + (r.work_min ?? 0), 0)
    const sources = [...new Set(p.rows.map(r => r.source_label))].join('、')
    return {
      key: `person-${idx}`,
      label: (
        <Space align="center">
          <ShiftTag person={p.person} shiftMap={shiftMap} />
          <Text strong style={{ fontSize: 16, color: p.person === '未指定' ? '#aaa' : '#1B3A5C' }}>
            {p.person}
          </Text>
          <Tag color="blue" style={{ fontSize: 13 }}>{p.rows.length} 項</Tag>
          {totalWH > 0 && <Tag color="geekblue" style={{ fontSize: 13 }}>{totalWH} min</Tag>}
          {sources && <Text type="secondary" style={{ fontSize: 13 }}>{sources}</Text>}
        </Space>
      ),
      children: (
        <Table
          size="small"
          dataSource={p.rows.map((r, i) => ({ ...r, key: i }))}
          columns={journalColumns}
          pagination={false}
          scroll={{ x: 'max-content' }}
          style={{ marginTop: 4 }}
          onRow={row => ({
            onClick: () => {
              const r = row as JournalRow
              setSelectedRow(r)
              setDrawerImages([])
              if (r.ragic_id && (r.source === 'dazhi' || r.source === 'luqun' || r.source === 'other_tasks')) {
                setImgLoading(true)
                fetchJournalImages(r.source, r.ragic_id)
                  .then(imgs => setDrawerImages(imgs))
                  .catch(() => setDrawerImages([]))
                  .finally(() => setImgLoading(false))
              }
            },
            style: { cursor: 'pointer' },
          })}
        />
      ),
    }
  })

  return (
    <>
      <Collapse
        activeKey={personActiveKeys}
        onChange={keys => setPersonActiveKeys(keys as string[])}
        items={items}
        style={{ background: '#fff' }}
      />
      <Drawer
        open={!!selectedRow}
        onClose={() => { setSelectedRow(null); setDrawerImages([]) }}
        title={
          selectedRow && (() => {
            // 取最有意義的識別碼：報修編號 > 日誌編號 > 房號 > ragic_id
            const d = selectedRow.detail ?? {}
            const identifier = d['報修編號'] || d['日誌編號'] || d['房號'] || selectedRow.ragic_id || ''
            return (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <Tag color={CATEGORY_COLOR[selectedRow.category as keyof typeof CATEGORY_COLOR]}
                     style={{ margin: 0 }}>
                  {selectedRow.category}
                </Tag>
                <span style={{ fontSize: 16, color: '#1B3A5C', fontWeight: 600 }}>
                  {selectedRow.source_label}
                  {identifier && <>：<span style={{ fontWeight: 400 }}>{identifier}</span></>}
                </span>
                {selectedRow.ragic_url && (
                  <a
                    href={selectedRow.ragic_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 14, color: '#4BA8E8', display: 'flex', alignItems: 'center', gap: 3, fontWeight: 400 }}
                  >
                    <LinkOutlined /> 在 Ragic 查看
                  </a>
                )}
              </div>
            )
          })()
        }
        width={480}
        styles={{ body: { padding: '16px 20px' } }}
      >
        {selectedRow && (
          <>
            <Typography.Title level={5} style={{ margin: '0 0 12px', color: '#1B3A5C' }}>
              {selectedRow.task}
            </Typography.Title>
            <Descriptions
              bordered
              size="small"
              column={1}
              labelStyle={{ width: 100, background: '#f5f7fa', fontWeight: 500 }}
              contentStyle={{ background: '#fff' }}
            >
              <Descriptions.Item label="人員">{selectedRow.person}</Descriptions.Item>
              <Descriptions.Item label="來源">{selectedRow.source_label}</Descriptions.Item>
              {selectedRow.source === 'other_tasks' && selectedRow.venue && (
                <Descriptions.Item label="歸屬">
                  <Tag color={selectedRow.venue === '飯店' ? '#1565C0' : '#2E7D32'} style={{ margin: 0 }}>
                    {selectedRow.venue}
                  </Tag>
                </Descriptions.Item>
              )}
              {selectedRow.work_min != null && (
                <Descriptions.Item label="工時(min)">
                  <Text strong style={{ color: '#1B3A5C' }}>{selectedRow.work_min}</Text>
                </Descriptions.Item>
              )}
              {(selectedRow.start_time || selectedRow.detail?.['保養時間起']) && (
                <Descriptions.Item label="保養時間起">
                  {selectedRow.start_time || selectedRow.detail?.['保養時間起']}
                </Descriptions.Item>
              )}
              {(selectedRow.end_time || selectedRow.detail?.['保養時間迄']) && (
                <Descriptions.Item label="保養時間迄">
                  {selectedRow.end_time || selectedRow.detail?.['保養時間迄']}
                </Descriptions.Item>
              )}
              {selectedRow.remark && (
                <Descriptions.Item label="備註">
                  <Text style={{ color: '#666' }}>{selectedRow.remark}</Text>
                </Descriptions.Item>
              )}
              {selectedRow.report && (
                <Descriptions.Item label="回報事項">
                  <Text style={{ color: '#d46b08' }}>{selectedRow.report}</Text>
                </Descriptions.Item>
              )}
            </Descriptions>

            {Object.keys(selectedRow.detail ?? {}).length > 0 && (
              <>
                <Divider style={{ margin: '16px 0 12px' }} />
                <Descriptions
                  bordered
                  size="small"
                  column={1}
                  labelStyle={{ width: 96, background: '#f5f7fa', fontWeight: 500, fontSize: 15 }}
                  contentStyle={{ background: '#fff', fontSize: 15 }}
                >
                  {Object.entries(selectedRow.detail).map(([k, v]) => {
                    const isEmpty = !v
                    // 費用欄：加 $ 符號
                    const isFee   = k.includes('費用')
                    // 狀況欄：彩色 Tag
                    const isStatus = k === '處理狀況' || k === '完成狀況' || k === '狀態'
                    // 類型欄：Tag
                    const isType  = k === '報修類型'
                    // 總費用：粗體
                    const isTotalFee = k === '總費用'
                    // 標題：粗體大字
                    const isTitle = k === '標題'

                    let content: React.ReactNode
                    if (isEmpty) {
                      content = <Text type="secondary">-</Text>
                    } else if (isStatus) {
                      content = <Tag color={STATUS_COLOR[v] ?? 'default'} style={{ margin: 0 }}>{v}</Tag>
                    } else if (isType) {
                      content = <Tag style={{ margin: 0 }}>{v}</Tag>
                    } else if (isTotalFee) {
                      content = <Text strong style={{ fontSize: 16 }}>${v}</Text>
                    } else if (isFee) {
                      content = <Text>${v}</Text>
                    } else if (isTitle) {
                      content = <Text strong style={{ fontSize: 16 }}>{v}</Text>
                    } else {
                      content = <Text>{v}</Text>
                    }
                    return (
                      <Descriptions.Item key={k} label={k}>{content}</Descriptions.Item>
                    )
                  })}
                </Descriptions>
              </>
            )}

            {/* 維修圖片（dazhi / luqun / other_tasks） */}
            {(imgLoading || drawerImages.length > 0) && (
              <>
                <Divider style={{ margin: '16px 0 8px' }} />
                <div style={{ fontWeight: 500, marginBottom: 8, color: '#555', fontSize: 15 }}>
                  維修圖片
                </div>
                {imgLoading
                  ? <div style={{ textAlign: 'center', padding: 16 }}><Spin size="small" /></div>
                  : (
                    <Image.PreviewGroup>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {drawerImages.map((img, i) => (
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
                  )
                }
              </>
            )}

          </>
        )}
      </Drawer>
    </>
  )
}
