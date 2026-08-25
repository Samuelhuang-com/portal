/**
 * 警示積壓天數分桶（2026-08-25）
 *
 * ═══════════════════════════════════════════════════════════════════════
 * 這張圖回答的問題
 * ═══════════════════════════════════════════════════════════════════════
 * **不是**「有幾件待處理」—— KPI 卡已經寫著 58 了。
 * 而是**「有幾件放太久」**。58 這個數字看不出裡面有沒有一件躺了三週。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️ 每根柱子都必須標數字，不能只靠長度
 * ═══════════════════════════════════════════════════════════════════════
 * 起算日是**客人留言那天**（2026-08-25 使用者裁示），所以第一次回補
 * 歷史評論之後，那幾百則舊評論會全部落在最後一桶。
 * 那不是 bug，是這個口徑的必然結果 —— 但它會讓最後一根柱子佔滿整條，
 * 前三根被壓成 1px。**數字寫在旁邊，長度就只是輔助。**
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️ 為什麼用 antd Progress 而不是圖表庫
 * ═══════════════════════════════════════════════════════════════════════
 * 四根橫條而已。recharts 要處理 ResponsiveContainer、margin、tick 格式、
 * 點擊事件的 payload —— 全部是為了畫四個矩形。
 * `docs/TABLER_UI_NOTES.md` §N.3 也記著：**要抄的是做法不是元件庫**。
 */
import React from 'react'
import { Card, Empty, Progress, Space, Tooltip, Typography } from 'antd'
import { ClockCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import type { AlertAgingResult } from '@/types/ota'

const { Text } = Typography

/** ⚠️ 這兩個色碼與工作狀態映射一致（PROTECTED.md）：逾期紅、正常藍 */
const COLOR_NORMAL = '#4BA8E8'
const COLOR_OVERDUE = '#ff4d4f'

export interface AlertAgingBarProps {
  data: AlertAgingResult | null
  loading?: boolean
  /**
   * 點某一桶時回呼，帶著換算好的日期區間。
   *
   * ⚠️ 積壓 N 天 ⇔ `review_date` 落在 `[as_of - max, as_of - min]`，
   *    所以呼叫端只要把它塞進既有的期間篩選就好，
   *    **後端清單 API 一個參數都不用加**。
   */
  onPick?: (range: [Dayjs, Dayjs] | null, label: string) => void
  /** 目前被選中的桶（讓使用者知道清單正被哪一段篩著） */
  activeKey?: string
}

export function bucketToRange(
  asOf: string, minDays: number | null, maxDays: number | null,
): [Dayjs, Dayjs] | null {
  const base = asOf ? dayjs(asOf) : dayjs()
  if (!base.isValid()) return null
  // 積壓天數越大 ⇒ 留言日期越早，所以 min/max 對應到 end/start 是**反過來**的
  const end = base.subtract(minDays ?? 0, 'day')
  // 最後一桶沒有上限 —— 起點放得夠早即可（OTA 評論不會早於 2000 年）
  const start = maxDays == null ? dayjs('2000-01-01') : base.subtract(maxDays, 'day')
  return [start, end]
}

export default function AlertAgingBar(props: AlertAgingBarProps) {
  const { data, loading, onPick, activeKey } = props
  const buckets = data?.buckets ?? []
  // ⚠️ 分母用**最大桶**不是總數：用總數的話，一桶佔 90% 時其他三桶全部貼底。
  //    這裡的長度只是相對比較，真正的數字寫在右邊。
  const max = Math.max(1, ...buckets.map((b) => b.count))
  const hasAny = buckets.some((b) => b.count > 0) || (data?.unknown_count ?? 0) > 0

  return (
    <Card
      size="small"
      loading={loading}
      style={{ marginBottom: 16 }}
      title={
        <Space size={6}>
          <ClockCircleOutlined />
          <span>積壓天數</span>
          <Tooltip
            placement="bottomLeft"
            title={
              <span>
                <b>從「客人留言那天」算到今天</b>
                <br />不是從我們抓到的那天算 —— 客人三週前抱怨就是積壓三週，
                跟爬蟲什麼時候跑到無關。
                <br /><br />
                只計入<b>待處理</b>與<b>已知悉</b>兩種狀態（未完成的工作）。
                <br /><br />
                ⚠️ <b>第一次回補歷史評論後</b>，舊評論會全部落在「15 天以上」——
                那是這個口徑的必然結果，不是計算錯誤。
              </span>
            }
          >
            <QuestionCircleOutlined style={{ color: '#bbb', cursor: 'help' }} />
          </Tooltip>
          {data?.as_of && (
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal' }}>
              基準日 {data.as_of}
            </Text>
          )}
        </Space>
      }
      extra={
        activeKey && onPick ? (
          <a onClick={() => onPick(null, '')}>清除篩選</a>
        ) : undefined
      }
    >
      {!hasAny ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="目前沒有待處理的警示"
          style={{ margin: '8px 0' }}
        />
      ) : (
        <div>
          {buckets.map((b) => {
            const color = b.is_overdue ? COLOR_OVERDUE : COLOR_NORMAL
            const active = activeKey === b.key
            const clickable = Boolean(onPick) && b.count > 0
            return (
              <div
                key={b.key}
                onClick={clickable
                  ? () => onPick?.(bucketToRange(data?.as_of || '', b.min_days, b.max_days), b.label)
                  : undefined}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '3px 6px', borderRadius: 4,
                  cursor: clickable ? 'pointer' : 'default',
                  background: active ? '#f0f7ff' : undefined,
                  outline: active ? `1px solid ${COLOR_NORMAL}` : undefined,
                }}
              >
                <Text style={{ width: 78, fontSize: 13, flexShrink: 0 }}
                      type={b.is_overdue && b.count > 0 ? 'danger' : undefined}>
                  {b.label}
                </Text>
                <Progress
                  percent={(b.count / max) * 100}
                  showInfo={false}
                  strokeColor={color}
                  size="small"
                  style={{ flex: 1, marginBottom: 0 }}
                />
                {/* ⚠️ 數字是主角。最後一桶塞滿時前三根只有 1px，全靠這裡看 */}
                <Text strong={b.count > 0}
                      type={b.is_overdue && b.count > 0 ? 'danger' : undefined}
                      style={{ width: 46, textAlign: 'right', fontSize: 13, flexShrink: 0 }}>
                  {b.count}
                </Text>
              </div>
            )
          })}

          {/* ⚠️ 這一行不可以省。日期解析不出來的評論不屬於任何桶，
              不講出來的話 sum(柱子) 會小於待處理總數，看起來像圖表算錯。 */}
          {(data?.unknown_count ?? 0) > 0 && (
            <Text type="secondary" style={{ fontSize: 12, display: 'block', marginTop: 6 }}>
              另有 {data?.unknown_count} 件的評論日期解析不出來，無法計算積壓天數
              （不含在上面四項內）
            </Text>
          )}
        </div>
      )}
    </Card>
  )
}
