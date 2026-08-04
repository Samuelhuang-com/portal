/**
 * 每日營收明細 Drawer（CLAUDE.md §7 強制規範）
 *
 * 標題列格式：
 *   [History/Forecast Tag]  每日營收：[YYYY-MM-DD]   🔗 原始資料列
 */
import React, { useState } from 'react'
import { Descriptions, Drawer, Space, Tag, Typography } from 'antd'
import { LinkOutlined } from '@ant-design/icons'

import type { RevenueDailyRow } from '@/types/opera'
import RawRowModal from './RawRowModal'
import { ACCENT, BRAND, EMPTY, RECORD_TYPE_TAG } from './formatters'

const { Text } = Typography

interface Props {
  open: boolean
  row: RevenueDailyRow | null
  onClose: () => void
}

const MONEY_KEYS = ['房間營收', '散客確定營收', '散客非確定營收', '團體確定營收', '團體非確定營收']

function renderDetailValue(key: string, value: string): React.ReactNode {
  const v = (value ?? '').trim()
  if (v === '') return <Text type="secondary">{EMPTY}</Text>

  if (key === '資料類型') {
    const tag = RECORD_TYPE_TAG[v] || { color: 'default', text: v }
    return <Tag color={tag.color}>{tag.text}</Tag>
  }
  if (MONEY_KEYS.includes(key)) {
    return <Text strong={key === '房間營收'}>{`$ ${v}`}</Text>
  }
  if (key === 'ADR' || key === 'RevPAR') {
    return <Text strong>{`$ ${v}`}</Text>
  }
  if (key === '住房率') {
    return <Text strong>{v}</Text>
  }
  return <Text>{v}</Text>
}

const RevenueDayDetailDrawer: React.FC<Props> = ({ open, row, onClose }) => {
  const [rawOpen, setRawOpen] = useState(false)

  if (!row) {
    return <Drawer open={open} onClose={onClose} width={480} title="每日營收明細" />
  }

  const typeTag = RECORD_TYPE_TAG[row.record_type] || { color: 'default', text: row.record_type }

  const title = (
    <Space size={8} wrap>
      <Tag color={typeTag.color}>{typeTag.text}</Tag>
      <Text strong style={{ color: BRAND }}>{`每日營收：${row.business_date}`}</Text>
      {row.raw_id > 0 && (
        <a onClick={(e) => { e.preventDefault(); setRawOpen(true) }} style={{ color: ACCENT }}>
          <LinkOutlined /> 原始資料列
        </a>
      )}
    </Space>
  )

  return (
    <>
      <Drawer open={open} onClose={onClose} width={480} title={title}>
        {/* ① 基本欄位 */}
        <Descriptions size="small" column={1} bordered title="基本欄位">
          <Descriptions.Item label="營業日">{row.business_date}</Descriptions.Item>
          <Descriptions.Item label="房間營收">
            <Text strong>{`$ ${Math.round(row.revenue).toLocaleString('en-US')}`}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="已售房晚">{row.sold_rooms.toLocaleString('en-US')}</Descriptions.Item>
          <Descriptions.Item label="可售房晚">{row.available_rooms.toLocaleString('en-US')}</Descriptions.Item>
          <Descriptions.Item label="ADR">
            <Text strong>{`$ ${Math.round(row.adr).toLocaleString('en-US')}`}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="住房率">
            <Text strong>{`${(row.occupancy * 100).toFixed(1)}%`}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="RevPAR">
            <Text strong>{`$ ${Math.round(row.revpar).toLocaleString('en-US')}`}</Text>
          </Descriptions.Item>
        </Descriptions>

        {/* ② 明細欄位 */}
        <Descriptions size="small" column={1} bordered title="明細欄位" style={{ marginTop: 16 }}>
          {Object.entries(row.detail || {}).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {renderDetailValue(key, value)}
            </Descriptions.Item>
          ))}
        </Descriptions>

        <Text type="secondary" style={{ display: 'block', marginTop: 12, fontSize: 12 }}>
          資料來源：History and Forecast。可售房晚 = 實體房數 − OOO（`CF_CALC_INV_ROOMS`）。
        </Text>
      </Drawer>

      <RawRowModal
        open={rawOpen}
        sourceType="HISTORY_FORECAST"
        rawId={row.raw_id}
        onClose={() => setRawOpen(false)}
      />
    </>
  )
}

export default RevenueDayDetailDrawer
