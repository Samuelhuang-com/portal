/**
 * 主題 × 情緒 發散長條（2026-08-25）
 *
 * 中間為 0，**負面提及往左紅、正面提及往右綠**。
 * 一眼看出哪個主題在扣分，點左半邊直接篩出那個主題的評論。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️ 只列「有負評」的主題，最多 8 個
 * ═══════════════════════════════════════════════════════════════════════
 * 這張圖是拿來**找問題**的。沒有人抱怨的主題列出來只是佔版面 ——
 * 後端 `get_topic_stats()` 已經是「負評多的排前面」，這裡取前 N 個即可。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️ 兩側各自用自己的最大值，不共用比例尺
 * ═══════════════════════════════════════════════════════════════════════
 * 正面提及通常遠多於負面（好評本來就比較多）。共用一把尺的話，
 * 負面那半永遠是一條看不見的線 —— 而那正是要看的東西。
 *
 * 代價是「左邊 3 格」與「右邊 3 格」的實際數量不同，
 * 所以**兩側都必須標數字**，長度只用來比較同一側的主題之間。
 * 這一點在 tooltip 裡有講。
 */
import React from 'react'
import { Card, Empty, Space, Tooltip, Typography } from 'antd'
import { PieChartOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import type { TopicStat } from '@/types/ota'

const { Text } = Typography

const MAX_TOPICS = 8
const COLOR_NEG = '#ff4d4f'
const COLOR_POS = '#52c41a'

export interface TopicDivergingBarProps {
  data: TopicStat[]
  loading?: boolean
  /**
   * 點某個主題。`polarity` 目前一律傳 'neg'（點的是左半邊）——
   * ⚠️ 後端清單的 `topic` 參數不分正負，所以點右半邊也只會篩出
   *    「提到這個主題的評論」而不是「說它好的評論」。
   *    與其做一個名實不符的互動，不如只讓左半邊可點。
   */
  onPick?: (topic: string) => void
  activeTopic?: string
}

export default function TopicDivergingBar(props: TopicDivergingBarProps) {
  const { data, loading, onPick, activeTopic } = props

  // ⚠️ 只留有負評的。後端已經照負評數排序，這裡不要重排 ——
  //    重排會讓「為什麼這個排在前面」變成兩個地方各說各話。
  const rows = data.filter((t) => t.negative_count > 0).slice(0, MAX_TOPICS)
  const maxNeg = Math.max(1, ...rows.map((t) => t.negative_count))
  const maxPos = Math.max(1, ...rows.map((t) => t.positive_count))

  return (
    <Card
      size="small"
      loading={loading}
      style={{ marginBottom: 16 }}
      title={
        <Space size={6}>
          <PieChartOutlined />
          <span>主題分布</span>
          <Tooltip
            placement="bottomLeft"
            title={
              <span>
                左紅＝<b>負面提及</b>，右綠＝正面提及。點左半邊可以把清單篩到那個主題。
                <br /><br />
                ⚠️ <b>兩側各自用自己的比例尺</b>，長度只能比較同一側的主題 ——
                好評本來就遠多於負評，共用一把尺的話負面那半會變成一條看不見的線，
                而那正是要看的東西。所以<b>兩側都標了數字</b>。
                <br /><br />
                只列<b>有負面提及</b>的主題（最多 {MAX_TOPICS} 個）——
                這張圖是拿來找問題的，沒人抱怨的主題列出來只是佔版面。
                <br /><br />
                ⚠️ 主題來自關鍵字字典＋AI 補判，<b>一則評論可以同時屬於多個主題</b>，
                所以各主題加起來會超過評論總數。
              </span>
            }
          >
            <QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} />
          </Tooltip>
        </Space>
      }
      extra={activeTopic && onPick ? <a onClick={() => onPick('')}>清除主題篩選</a> : undefined}
    >
      {rows.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="目前的條件下沒有負面主題（或評論還沒分析過）"
          style={{ margin: '8px 0' }}
        />
      ) : (
        <div>
          {rows.map((t) => {
            const active = activeTopic === t.topic
            return (
              <div
                key={t.topic}
                onClick={onPick ? () => onPick(t.topic) : undefined}
                style={{
                  display: 'flex', alignItems: 'center',
                  padding: '2px 6px', borderRadius: 4,
                  cursor: onPick ? 'pointer' : 'default',
                  background: active ? '#f0f7ff' : undefined,
                  outline: active ? '1px solid #4BA8E8' : undefined,
                }}
              >
                {/* 左：負面數字 + 往左長的條 */}
                <Text strong type="danger"
                      style={{ width: 34, textAlign: 'right', fontSize: 13, flexShrink: 0 }}>
                  {t.negative_count}
                </Text>
                <div style={{ flex: 1, display: 'flex', justifyContent: 'flex-end',
                              paddingLeft: 6, paddingRight: 4 }}>
                  <div style={{
                    width: `${(t.negative_count / maxNeg) * 100}%`,
                    height: 14, background: COLOR_NEG, borderRadius: '2px 0 0 2px',
                  }} />
                </div>

                {/* 中：主題名稱 */}
                <Text style={{ width: 66, textAlign: 'center', fontSize: 13, flexShrink: 0 }}>
                  {t.topic}
                </Text>

                {/* 右：往右長的條 + 正面數字 */}
                <div style={{ flex: 1, paddingLeft: 4, paddingRight: 6 }}>
                  <div style={{
                    width: `${(t.positive_count / maxPos) * 100}%`,
                    height: 14, background: COLOR_POS, borderRadius: '0 2px 2px 0',
                  }} />
                </div>
                <Text style={{ width: 34, fontSize: 13, flexShrink: 0, color: COLOR_POS }}>
                  {t.positive_count}
                </Text>
              </div>
            )
          })}

          {data.length > rows.length && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 6 }}>
              另有 {data.length - rows.length} 個主題沒有負面提及，未列出
            </Text>
          )}
        </div>
      )}
    </Card>
  )
}
