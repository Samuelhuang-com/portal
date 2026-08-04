/**
 * 原始資料列 Modal
 *
 * OPERA 模組沒有 Ragic 連結，依 CLAUDE.md §7 的等效做法：
 * 明細 Drawer 標題列的「🔗 原始資料列」點擊後，以**內嵌 Modal**顯示該筆
 * 在原始資料層（opera_departure_raw / opera_history_forecast_raw）的完整欄位值。
 * 規範明訂不可另開新視窗。
 */
import React, { useCallback, useEffect, useState } from 'react'
import { Alert, Descriptions, Modal, Spin, Tag, Typography } from 'antd'

import { fetchRawRow } from '@/api/opera'
import type { OperaSourceType, RawRowResult } from '@/types/opera'
import { ACCENT, EMPTY } from './formatters'

const { Text } = Typography

interface Props {
  open: boolean
  sourceType: OperaSourceType
  rawId: number | null
  onClose: () => void
}

const RawRowModal: React.FC<Props> = ({ open, sourceType, rawId, onClose }) => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<RawRowResult | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!rawId) return
    setLoading(true)
    setError('')
    try {
      setData(await fetchRawRow(sourceType, rawId))
    } catch (e: any) {
      setError(e?.response?.data?.detail || '讀取原始資料列失敗')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [sourceType, rawId])

  useEffect(() => {
    if (open && rawId) load()
  }, [open, rawId, load])

  const merged = data && data.source_row_no_end > data.source_row_no

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={760}
      title={
        <span>
          <Tag color="default">原始資料層</Tag>
          <Text strong style={{ color: ACCENT }}>
            {sourceType === 'DEPARTURE' ? 'Departure All' : 'History and Forecast'} 原始資料列
          </Text>
        </span>
      }
    >
      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}

      <Spin spinning={loading}>
        {data && (
          <>
            <Descriptions size="small" column={2} bordered style={{ marginBottom: 12 }}>
              <Descriptions.Item label="批次編號">{data.batch_id}</Descriptions.Item>
              <Descriptions.Item label="TXT 列號">
                {merged
                  ? `${data.source_row_no} ～ ${data.source_row_no_end}（續行合併）`
                  : data.source_row_no}
              </Descriptions.Item>
              <Descriptions.Item label="業務鍵" span={2}>
                <Text code style={{ fontSize: 12 }}>{data.record_key || EMPTY}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="整列指紋" span={2}>
                <Text code style={{ fontSize: 12 }}>{data.row_hash}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="匯入時間" span={2}>{data.imported_at || EMPTY}</Descriptions.Item>
            </Descriptions>

            {merged && (
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                message="此筆由兩個實體列合併而成"
                description="OPERA 在 PROF_ATTACHED 含換行時會把一筆資料拆成 43 欄 + 3 欄兩列，匯入時已依規格書 §3.2 合併。"
              />
            )}

            <Descriptions
              size="small"
              column={1}
              bordered
              title="來源欄位（依 TXT 表頭順序）"
              labelStyle={{ width: 240, fontFamily: 'monospace', fontSize: 12 }}
            >
              {Object.entries(data.fields).map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {value === '' ? (
                    <Text type="secondary">{EMPTY}</Text>
                  ) : (
                    <Text style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{value}</Text>
                  )}
                </Descriptions.Item>
              ))}
            </Descriptions>

            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 12 }}
              message="個資保護"
              description="GUEST_NAME 顯示的是遮罩後版本，MEMBERSHIP_CARD_NO 一律為空 —— 原始姓名與會員卡號從未寫入資料庫（規格書 §13.1）。"
            />
          </>
        )}
      </Spin>
    </Modal>
  )
}

export default RawRowModal
