/**
 * 住宿明細 Drawer（CLAUDE.md §7 強制規範）
 *
 * 標題列格式：
 *   [通路 Tag]  住宿明細：[房號]-[退房日]   🔗 原始資料列
 *
 * identifier 取值優先序：房號 > 訂房編號 > raw_id
 * 「原始資料列」必須放在標題列，不可放 Drawer body 底部。
 */
import React, { useState } from 'react'
import { Descriptions, Drawer, Space, Tag, Typography } from 'antd'
import { LinkOutlined } from '@ant-design/icons'

import type { StayRow } from '@/types/opera'
import RawRowModal from './RawRowModal'
import { ACCENT, BRAND, EMPTY, fmtInt, fmtText } from './formatters'

const { Text } = Typography

interface Props {
  open: boolean
  stay: StayRow | null
  onClose: () => void
}

/** 明細欄位的渲染規則：狀態欄 → 彩色 Tag；金額欄 → $ 前綴；空值 → — */
function renderDetailValue(key: string, value: string): React.ReactNode {
  const v = (value ?? '').trim()
  if (v === '') return <Text type="secondary">{EMPTY}</Text>

  if (key === '訂房狀態') {
    return <Tag color={v === 'CHECKED OUT' ? 'green' : 'blue'}>{v}</Tag>
  }
  if (key === 'VIP') {
    return <Tag color="gold">{v}</Tag>
  }
  if (key === '通路') {
    return <Tag color={v === '直客／未標註' ? 'default' : 'blue'}>{v}</Tag>
  }
  if (key === '住客') {
    return v === '（已清除）'
      ? <Text type="secondary">{v}</Text>
      : <Text>{v}</Text>
  }
  if (key.includes('費用') || key.includes('金額') || key.includes('營收')) {
    return <Text strong>{`$ ${v}`}</Text>
  }
  return <Text>{v}</Text>
}

const StayDetailDrawer: React.FC<Props> = ({ open, stay, onClose }) => {
  const [rawOpen, setRawOpen] = useState(false)

  if (!stay) {
    return <Drawer open={open} onClose={onClose} width={480} title="住宿明細" />
  }

  // identifier 取值優先序（規格書 §11.5）
  const identifier =
    stay.detail?.['房號']
    || stay.room_no
    || stay.detail?.['訂房編號']
    || String(stay.raw_id)

  const title = (
    <Space size={8} wrap>
      <Tag color={stay.channel === '直客／未標註' ? 'default' : 'blue'}>{stay.channel}</Tag>
      <Text strong style={{ color: BRAND }}>
        {`住宿明細：${identifier}-${stay.departure_date}`}
      </Text>
      {stay.raw_id > 0 && (
        <a
          onClick={(e) => { e.preventDefault(); setRawOpen(true) }}
          style={{ color: ACCENT }}
        >
          <LinkOutlined /> 原始資料列
        </a>
      )}
    </Space>
  )

  return (
    <>
      <Drawer open={open} onClose={onClose} width={480} title={title} destroyOnClose={false}>
        {/* ① 基本欄位 */}
        <Descriptions size="small" column={1} bordered title="基本欄位">
          <Descriptions.Item label="退房日">{fmtText(stay.departure_date)}</Descriptions.Item>
          <Descriptions.Item label="入住日">{fmtText(stay.arrival_date)}</Descriptions.Item>
          <Descriptions.Item label="房號">{fmtText(stay.room_no)}</Descriptions.Item>
          <Descriptions.Item label="房型">
            {stay.room_category_label ? <Tag color="cyan">{stay.room_category_label}</Tag> : EMPTY}
          </Descriptions.Item>
          <Descriptions.Item label="住宿晚數">{fmtInt(stay.nights)}</Descriptions.Item>
          <Descriptions.Item label="房數">{fmtInt(stay.no_of_rooms)}</Descriptions.Item>
          <Descriptions.Item label="房晚">
            <Text strong>{fmtInt(stay.room_nights)}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="成人／兒童">
            {`${fmtInt(stay.adults)} ／ ${fmtInt(stay.child_count)}`}
          </Descriptions.Item>
        </Descriptions>

        {/* ② 明細欄位 */}
        <Descriptions
          size="small"
          column={1}
          bordered
          title="明細欄位"
          style={{ marginTop: 16 }}
        >
          {Object.entries(stay.detail || {}).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {renderDetailValue(key, value)}
            </Descriptions.Item>
          ))}
        </Descriptions>

        <Text type="secondary" style={{ display: 'block', marginTop: 12, fontSize: 12 }}>
          資料來源：Departure All（本模組不以 Departure 推估營收，營收一律以 History and Forecast 為準）
        </Text>
      </Drawer>

      <RawRowModal
        open={rawOpen}
        sourceType="DEPARTURE"
        rawId={stay.raw_id}
        onClose={() => setRawOpen(false)}
      />
    </>
  )
}

export default StayDetailDrawer
