/**
 * OTA 評論明細 Drawer
 *
 * 遵循 CLAUDE.md §7 ／ docs/WORK_JOURNAL_SPEC.md §9「明細 Drawer 強制規範」：
 *   - 寬度 480px
 *   - 標題列格式：[平台 Tag] [飯店：旅客暱稱] [🔗 在 {平台} 查看]
 *     連結**在標題列**，不放 body 底部
 *   - Body 分兩區：①基本欄位（Descriptions column=2）②明細欄位（column=1，逐項渲染 detail dict）
 *   - 狀態欄 → 彩色 Tag；空值 → —
 *
 * ⚠️ 等價替代（規格書 §9.3）：本模組沒有 Ragic，
 *    `ragic_url` → `review_url`（OTA 原始評論頁），
 *    「在 Ragic 查看」→「在 {平台名} 查看」。
 *    其餘規範完全照辦，色碼一樣是 #4BA8E8。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Descriptions, Drawer, Input, Select, Space, Spin, Tag, message,
} from 'antd'
import { LinkOutlined } from '@ant-design/icons'

import { fetchReviewDetail, updateAlert } from '@/api/ota'
import type { OtaReviewDetail } from '@/types/ota'

const { TextArea } = Input

// 情緒色彩映射（規格書 §9.4；新增後需登錄 docs/PROTECTED.md）
const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'success',
  neutral: 'default',
  negative: 'error',
}
const SENTIMENT_LABEL: Record<string, string> = {
  positive: '正面',
  neutral: '中立',
  negative: '負面',
}

const ALERT_LABEL: Record<string, string> = {
  open: '待處理',
  acknowledged: '已知悉',
  resolved: '已處理',
  ignored: '不處理',
}
const ALERT_COLOR: Record<string, string> = {
  open: 'error',
  acknowledged: 'warning',
  resolved: 'success',
  ignored: 'default',
}

const PLATFORM_COLOR: Record<string, string> = {
  booking: 'blue',
  expedia: 'gold',
  tripadvisor: 'green',
  agoda: 'purple',
  google: 'cyan',
}

/** 空值一律顯示破折號（§7 渲染規則） */
function dash(value?: string | null): React.ReactNode {
  return value && value !== '—' ? value : '—'
}

/** 依 key 決定 detail dict 的渲染方式 */
function renderDetailValue(key: string, value: string): React.ReactNode {
  if (!value || value === '—') return <span style={{ color: '#bfbfbf' }}>—</span>

  if (key === '情緒判定') {
    const code = Object.keys(SENTIMENT_LABEL).find((k) => SENTIMENT_LABEL[k] === value) || ''
    return <Tag color={SENTIMENT_COLOR[code] || 'default'}>{value}</Tag>
  }
  if (key === '主題標籤') {
    return (
      <Space size={4} wrap>
        {value.split('、').map((tag) => {
          const [name, polarity] = tag.split(':')
          return (
            <Tag key={tag} color={polarity === 'pos' ? 'success' : 'error'}>
              {name}
            </Tag>
          )
        })}
      </Space>
    )
  }
  if (key === '跨站重複' && value.startsWith('是')) {
    return <Tag color="default">{value}</Tag>
  }
  if (key === '評分') {
    return <span style={{ fontWeight: 600 }}>{value}</span>
  }
  if (key === '負面評語') {
    return <span style={{ whiteSpace: 'pre-wrap', color: '#cf1322' }}>{value}</span>
  }
  if (key === '正面評語') {
    return <span style={{ whiteSpace: 'pre-wrap', color: '#389e0d' }}>{value}</span>
  }
  return <span style={{ whiteSpace: 'pre-wrap' }}>{value}</span>
}


export interface ReviewDetailDrawerProps {
  reviewId: number | null
  open: boolean
  onClose: () => void
  /** 警示狀態更新後通知外層重新載入清單 */
  onUpdated?: () => void
  /** 是否顯示警示處理區（需 ota_alerts_view 權限的頁面才給 true） */
  allowAlertEdit?: boolean
}

const ReviewDetailDrawer: React.FC<ReviewDetailDrawerProps> = ({
  reviewId, open, onClose, onUpdated, allowAlertEdit = false,
}) => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<OtaReviewDetail | null>(null)
  const [alertStatus, setAlertStatus] = useState<string>('open')
  const [alertNote, setAlertNote] = useState<string>('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async (id: number) => {
    setLoading(true)
    try {
      const detail = await fetchReviewDetail(id)
      setData(detail)
      setAlertStatus(detail.alert_status || 'open')
      setAlertNote(detail.alert_note || '')
    } catch {
      message.error('載入評論明細失敗')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open && reviewId) load(reviewId)
  }, [open, reviewId, load])

  const handleSaveAlert = async () => {
    if (!reviewId) return
    setSaving(true)
    try {
      const updated = await updateAlert(reviewId, {
        alert_status: alertStatus,
        alert_note: alertNote,
      })
      setData(updated)
      message.success('已更新處理狀態')
      onUpdated?.()
    } catch {
      message.error('更新失敗')
    } finally {
      setSaving(false)
    }
  }

  const platformCode = data?.platform || ''
  const linkLabel = data ? `在 ${data.platform_label} 查看` : ''

  return (
    <Drawer
      width={480}
      open={open}
      onClose={onClose}
      destroyOnClose
      title={data && (
        // ── §7 MANDATORY 標題列：[平台 Tag] [飯店：暱稱] [🔗 在 {平台} 查看] ──
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <Tag color={PLATFORM_COLOR[platformCode] || 'default'} style={{ margin: 0 }}>
            {data.platform_label}
          </Tag>
          <span style={{ fontSize: 16, color: '#1B3A5C', fontWeight: 600 }}>
            {data.hotel_name}：<span style={{ fontWeight: 400 }}>{data.author}</span>
          </span>
          {data.review_url && (
            <a
              href={data.review_url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: 14, color: '#4BA8E8', display: 'flex',
                alignItems: 'center', gap: 3, fontWeight: 400,
              }}
            >
              <LinkOutlined /> {linkLabel}
            </a>
          )}
        </div>
      )}
    >
      <Spin spinning={loading}>
        {data && (
          <>
            {data.is_duplicate && (
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
                message="這則評論與其他平台的內容重複"
                description="已排除於所有統計之外，僅保留供追溯。原始資料未刪除。"
              />
            )}

            {/* ── ① 基本欄位 ──────────────────────────────────────── */}
            <Descriptions
              title="基本資料"
              column={2}
              size="small"
              bordered
              labelStyle={{ width: 88, background: '#f5f7fa', fontWeight: 500 }}
            >
              <Descriptions.Item label="飯店">{dash(data.hotel_name)}</Descriptions.Item>
              <Descriptions.Item label="平台">{dash(data.platform_label)}</Descriptions.Item>
              <Descriptions.Item label="評分">
                <span style={{ fontWeight: 600 }}>
                  {data.score_10 === null ? '—' : `${data.score_10.toFixed(1)} / 10`}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label="評論日期">{dash(data.review_date)}</Descriptions.Item>
              <Descriptions.Item label="情緒">
                {data.sentiment_label ? (
                  <Tag color={SENTIMENT_COLOR[data.sentiment_label] || 'default'}>
                    {SENTIMENT_LABEL[data.sentiment_label] || data.sentiment_label}
                  </Tag>
                ) : <span style={{ color: '#bfbfbf' }}>尚未分析</span>}
              </Descriptions.Item>
              <Descriptions.Item label="警示">
                {data.is_alert
                  ? <Tag color={ALERT_COLOR[data.alert_status] || 'default'}>
                      {ALERT_LABEL[data.alert_status] || data.alert_status}
                    </Tag>
                  : <span style={{ color: '#bfbfbf' }}>—</span>}
              </Descriptions.Item>
            </Descriptions>

            {/* ── ② 明細欄位（逐項渲染 detail dict）──────────────────── */}
            <Descriptions
              title="評論明細"
              column={1}
              size="small"
              bordered
              style={{ marginTop: 20 }}
              labelStyle={{ width: 96, background: '#f5f7fa', fontWeight: 500 }}
            >
              {Object.entries(data.detail).map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {renderDetailValue(key, value)}
                </Descriptions.Item>
              ))}
            </Descriptions>

            {/* ── ③ 警示處理（人工營運欄位，同步不會覆蓋）─────────────── */}
            {allowAlertEdit && data.is_alert && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontWeight: 600, color: '#1B3A5C', marginBottom: 10 }}>
                  處理狀態
                </div>
                <Space direction="vertical" style={{ width: '100%' }} size={10}>
                  <Select
                    value={alertStatus}
                    onChange={setAlertStatus}
                    style={{ width: '100%' }}
                    options={Object.entries(ALERT_LABEL).map(([value, label]) => ({ value, label }))}
                  />
                  <TextArea
                    value={alertNote}
                    onChange={(e) => setAlertNote(e.target.value)}
                    placeholder="處理備註（例：已請房務加強巡檢）"
                    rows={3}
                    maxLength={500}
                    showCount
                  />
                  <Button type="primary" loading={saving} onClick={handleSaveAlert} block>
                    儲存處理狀態
                  </Button>
                </Space>
              </div>
            )}
          </>
        )}
      </Spin>
    </Drawer>
  )
}

export default ReviewDetailDrawer
