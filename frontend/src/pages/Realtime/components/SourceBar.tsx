/**
 * 即時營運 — 資料來源標示列（統一元件）
 *
 * 規格書：docs/SPEC_realtime_operations.md §9（強制規範）
 *
 * ⚠️ 業主 2026-08-06 明確要求：**畫面上要標示 API 執行資料**。
 *    每一個顯示 API 數字的頁面，底部都必須放這個元件 —— 不要各頁自己刻一份，
 *    否則欄位會漸漸不一致，使用者就無法用同一套方式判讀資料新鮮度。
 *
 * 最常被使用者看的兩個欄位是「抓取時間」與「本次狀態」，因此擺在最前面。
 */
import React from 'react'
import { Descriptions, Tag, Typography } from 'antd'
import { ApiOutlined, DatabaseOutlined, ThunderboltOutlined } from '@ant-design/icons'

import { BRAND, EMPTY } from '@/pages/Opera/components/formatters'

const { Text } = Typography

/** 各頁 source 物件的共同形狀（欄位有無視頁面而定，缺的就不顯示） */
export interface SourceMetaLike {
  provider?: string
  hotel_id?: string
  ext_system_code?: string
  endpoint?: string
  status_code?: number | null
  elapsed_ms?: number | null
  poll_count?: number | null
  request_id?: string
  from_cache?: boolean
  cache_ttl_seconds?: number
  cache_age_seconds?: number | null
  fetched_at?: string | null
  checked_at?: string
  segments?: number
  max_span_days?: number
  token?: { cached: boolean; expires_in_seconds: number }
  txt_source?: string
}

interface Props {
  source: SourceMetaLike | null | undefined
  /** 比對頁一律即時取數，不需要顯示快取欄位 */
  hideCache?: boolean
}

const SourceBar: React.FC<Props> = ({ source, hideCache }) => {
  if (!source) return null

  const s = source

  return (
    <Descriptions
      size="small"
      bordered
      column={{ xs: 1, sm: 2, md: 3, lg: 4 }}
      style={{ marginTop: 12 }}
      labelStyle={{ width: 110, fontSize: 12 }}
      contentStyle={{ fontSize: 12 }}
    >
      {/* ── 使用者最常看的兩欄，擺最前面 ── */}
      <Descriptions.Item label="抓取時間">
        <Text strong>{s.fetched_at ? s.fetched_at.replace('T', ' ') : EMPTY}</Text>
      </Descriptions.Item>

      {!hideCache && (
        <Descriptions.Item label="本次狀態">
          {s.from_cache ? (
            <Tag icon={<DatabaseOutlined />} color="default">
              快取命中（{s.cache_age_seconds ?? 0} 秒前
              {s.cache_ttl_seconds ? `，TTL ${s.cache_ttl_seconds} 秒` : ''}）
            </Tag>
          ) : (
            <Tag icon={<ThunderboltOutlined />} color="green">實際呼叫 API</Tag>
          )}
        </Descriptions.Item>
      )}

      <Descriptions.Item label="資料來源">
        <Tag icon={<ApiOutlined />} color={BRAND}>{s.provider || 'OPERA Cloud（OHIP API）'}</Tag>
      </Descriptions.Item>

      <Descriptions.Item label="飯店代碼">
        {s.hotel_id || EMPTY}
        {s.ext_system_code ? ` / ${s.ext_system_code}` : ''}
      </Descriptions.Item>

      <Descriptions.Item label="端點" span={2}>
        <Text code style={{ fontSize: 11 }}>{s.endpoint || EMPTY}</Text>
      </Descriptions.Item>

      <Descriptions.Item label="HTTP 狀態">
        {s.status_code
          ? <Tag color={s.status_code === 200 ? 'green' : 'red'}>{s.status_code}</Tag>
          : EMPTY}
      </Descriptions.Item>

      <Descriptions.Item label="回應耗時">
        {s.elapsed_ms !== null && s.elapsed_ms !== undefined ? `${s.elapsed_ms} ms` : EMPTY}
        {s.poll_count ? `（輪詢 ${s.poll_count} 次）` : ''}
      </Descriptions.Item>

      {/* Request Id 是開 Oracle 服務單的必要資訊，一定要可複製 */}
      <Descriptions.Item label="Request Id" span={2}>
        <Text copyable={!!s.request_id} style={{ fontSize: 11 }}>
          {s.request_id || EMPTY}
        </Text>
        <Text type="secondary" style={{ fontSize: 11, marginInlineStart: 8 }}>
          （向 Oracle 開服務單時需提供）
        </Text>
      </Descriptions.Item>

      {s.segments !== undefined && (
        <Descriptions.Item label="切段數">
          {s.segments} 段
          {s.max_span_days ? `（每段上限 ${s.max_span_days} 天）` : ''}
        </Descriptions.Item>
      )}

      {s.token && (
        <Descriptions.Item label="Token">
          {s.token.cached
            ? <Tag color="green">
                已快取，{Math.floor((s.token.expires_in_seconds || 0) / 60)} 分後換新
              </Tag>
            : <Tag>未快取</Tag>}
        </Descriptions.Item>
      )}

      {s.txt_source && (
        <Descriptions.Item label="TXT 來源" span={2}>
          <Text code style={{ fontSize: 11 }}>{s.txt_source}</Text>
        </Descriptions.Item>
      )}

      <Descriptions.Item label="檢查時間">
        {s.checked_at ? s.checked_at.replace('T', ' ') : EMPTY}
      </Descriptions.Item>
    </Descriptions>
  )
}

export default SourceBar
