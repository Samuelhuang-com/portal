/**
 * 分數分布橫條（2026-08-25）
 *
 * ═══════════════════════════════════════════════════════════════════════
 * 這排橫條在解決什麼
 * ═══════════════════════════════════════════════════════════════════════
 * 在這之前，要看低分評論得自己在「低分」欄**打一個數字**。
 * 那等於要求使用者先知道分布長怎樣，才問得出問題。
 *
 * 改成「一眼看見分布，而且點哪條就篩哪一段」—— Trustpilot／Amazon
 * 的星等分布條是同一個做法，它同時是圖也是篩選器。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️ 最後一格「低於 6 分」＝ Dashboard 的「負面評論」KPI
 * ═══════════════════════════════════════════════════════════════════════
 * 邊界綁 `NEGATIVE_SCORE_MAX`（後端），所以那一格的數字**應該**等於
 * Dashboard 上的負面評論數。這是刻意的 —— 兩個畫面可以互相驗證。
 * 對不起來就是有一邊的條件寫錯了。
 *
 * ⚠️ 這支與 `AlertAgingBar` 長得像但**沒有抽成共用元件**：
 *    兩者的「格」語意不同（分數區間 vs 天數區間）、點擊換算的目標參數
 *    不同（min_score+score_below vs start+end）、顏色規則也不同
 *    （這裡是低分紅、那裡是久了紅）。硬抽會變成一堆 if。
 */
import React from 'react'
import { Card, Empty, Progress, Space, Tooltip, Typography } from 'antd'
import { BarChartOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import type { ScoreBucket, ScoreDistributionResult } from '@/types/ota'

const { Text } = Typography

/** ⚠️ 與工作狀態色彩映射一致（PROTECTED.md）：負評紅、其餘藍 */
const COLOR_NORMAL = '#4BA8E8'
const COLOR_NEGATIVE = '#ff4d4f'

export interface ScoreFilterPatch {
  /** 後端 `>=`。undefined ＝ 不帶 */
  min_score?: number
  /** 後端 `<`（半開區間的上界）。undefined ＝ 不帶 */
  score_below?: number
}

/**
 * 把一格換算成清單的篩選參數。
 *
 * ⚠️ **一律用 `min_score` + `score_below`，不要用 `max_score`。**
 *    後端 `max_score` 是 `<=` —— 用它的話「8–9」與「9–10」都會含 9.0，
 *    兩格加起來比總數還多，而且點兩格看到同一筆評論。
 *    `score_below` 是 `<`，正好表達半開區間 `[lo, hi)`。
 */
export function bucketToScoreFilter(b: ScoreBucket): ScoreFilterPatch {
  return {
    min_score: b.min_score ?? undefined,
    score_below: b.max_score ?? undefined,
  }
}

export interface ScoreDistributionBarProps {
  data: ScoreDistributionResult | null
  loading?: boolean
  /** 點某一格。傳 null 代表「清除」 */
  onPick?: (patch: ScoreFilterPatch | null, key: string) => void
  activeKey?: string
}

export default function ScoreDistributionBar(props: ScoreDistributionBarProps) {
  const { data, loading, onPick, activeKey } = props
  const buckets = data?.buckets ?? []
  // ⚠️ 分母用**最大格**不是總數 —— OTA 分數高度集中在 8–10，
  //    用總數的話低分那幾格永遠是看不見的一條線。
  const max = Math.max(1, ...buckets.map((b) => b.count))
  const hasAny = buckets.some((b) => b.count > 0) || (data?.no_score_count ?? 0) > 0

  return (
    <Card
      size="small"
      loading={loading}
      style={{ marginBottom: 16 }}
      title={
        <Space size={6}>
          <BarChartOutlined />
          <span>分數分布</span>
          <Tooltip
            placement="bottomLeft"
            title={
              <span>
                點任一列可以把清單篩到那個分數區間。
                <br /><br />
                區間是<b>半開</b>的（<code>9 – 10</code> 含 9.0 不含⋯⋯
                最高那格含滿分 10.0）—— 這樣每則評論只會落在一格，
                各格加起來剛好等於總數。
                <br /><br />
                ⚠️ <b>各 OTA 分制不同</b>（Booking／Agoda／Trip.com 10 分制、
                Tripadvisor 5 分制），這裡一律換算成 10 分制之後才分格。
                <br /><br />
                最後一格「低於 6 分」與 Dashboard 的「負面評論」是<b>同一個條件</b>，
                兩邊數字應該一致。
              </span>
            }
          >
            <QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} />
          </Tooltip>
          {(data?.total ?? 0) > 0 && (
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
              共 {data?.total.toLocaleString()} 則
            </Text>
          )}
        </Space>
      }
      extra={activeKey && onPick ? <a onClick={() => onPick(null, '')}>清除分數篩選</a> : undefined}
    >
      {!hasAny ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="目前的條件下沒有評論"
          style={{ margin: '8px 0' }}
        />
      ) : (
        <div>
          {buckets.map((b) => {
            const color = b.is_negative ? COLOR_NEGATIVE : COLOR_NORMAL
            const active = activeKey === b.key
            const clickable = Boolean(onPick) && b.count > 0
            const pct = (data?.total ?? 0) > 0
              ? (b.count / (data?.total ?? 1)) * 100 : 0
            return (
              <div
                key={b.key}
                onClick={clickable ? () => onPick?.(bucketToScoreFilter(b), b.key) : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '3px 6px', borderRadius: 4,
                  cursor: clickable ? 'pointer' : 'default',
                  background: active ? '#f0f7ff' : undefined,
                  outline: active ? `1px solid ${COLOR_NORMAL}` : undefined,
                }}
              >
                <Text style={{ width: 78, fontSize: 13, flexShrink: 0 }}
                      type={b.is_negative && b.count > 0 ? 'danger' : undefined}>
                  {b.label}
                </Text>
                <Progress
                  percent={(b.count / max) * 100}
                  showInfo={false}
                  strokeColor={color}
                  size="small"
                  style={{ flex: 1, marginBottom: 0 }}
                />
                {/* ⚠️ 數字是主角 —— 分數集中在高分區時，低分那幾格只有 1px */}
                <Text strong={b.count > 0}
                      type={b.is_negative && b.count > 0 ? 'danger' : undefined}
                      style={{ width: 46, textAlign: 'right', fontSize: 13, flexShrink: 0 }}>
                  {b.count}
                </Text>
                {/* 佔比：判斷「負評多不多」要看比例，不是絕對數 */}
                <Text type="secondary"
                      style={{ width: 44, textAlign: 'right', fontSize: 12, flexShrink: 0 }}>
                  {pct >= 0.1 ? `${pct.toFixed(0)}%` : ''}
                </Text>
              </div>
            )
          })}

          {/* ⚠️ 不可省。抓不到分數的評論不屬於任何一格，
              不講的話 sum(格) < 總筆數，看起來像圖表算錯。 */}
          {(data?.no_score_count ?? 0) > 0 && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 6 }}>
              另有 {data?.no_score_count} 則沒有分數（來源站台的分制判讀不出來），
              不含在上面五項內
            </Text>
          )}
        </div>
      )}
    </Card>
  )
}
