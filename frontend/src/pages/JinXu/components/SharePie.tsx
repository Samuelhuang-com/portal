/**
 * 佔比圓餅圖（金旭分析共用）
 *
 * 解決三個原本的問題：
 *   1. **沒有標籤** —— 原本只有滑鼠移過去才看得到，靜態截圖／列印完全讀不出來。
 *      改成「切片內顯示 %」＋「右側圖例顯示名稱與 %」雙軌。
 *   2. **佔比分母錯誤** —— 原本 `items.slice(0, 10)` 直接畫，recharts 會用「前 10 名
 *      的和」當分母，於是 Agoda 在圖上看起來像 25%，實際佔全部只有 22.6%。
 *      本元件一律用**全部資料的總和**當分母，並把第 N 名之後的合併成「其他」，
 *      讓圓餅加總必定等於 100%。
 *   3. **長名稱擠爆版面** —— 通路名稱最長 38 字（`Trip.com Travel Singapore Pte. Ltd- 預付`），
 *      圖例做截斷並用 title 屬性保留全名。
 *
 * 切片內的 % 只在佔比夠大時才畫（預設 ≥ 4%），否則小切片的文字會互相重疊。
 */
import React, { useMemo } from 'react'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { Empty, Typography } from 'antd'

import { CHART_PALETTE, fmtInt } from './constants'

const { Text } = Typography

/** 切片內顯示 % 的最低門檻，低於此值不畫（避免小切片文字重疊） */
const MIN_LABEL_PCT = 0.04
/** 圖例名稱截斷長度 */
const LEGEND_MAX_CHARS = 18
const OTHER_KEY = '__other__'

export interface SharePieDatum {
  key: string
  label: string
  value: number
  color: string
  /** 被合併進「其他」的項目數（僅其他那一片有值） */
  mergedCount?: number
}

interface Props<T> {
  data: T[]
  /** 取顯示名稱 */
  nameOf: (item: T) => string
  /** 取數值 */
  valueOf: (item: T) => number
  /** 取唯一鍵（預設用名稱） */
  keyOf?: (item: T) => string
  /** 取顏色（不給則依序套用共用色盤） */
  colorOf?: (item: T, index: number) => string
  /** 前 N 名單獨顯示，其餘合併為「其他」。預設 8 */
  topN?: number
  height?: number
  /** 數值格式化，預設千分位整數 */
  valueFormatter?: (v: number) => string
  /** 數值單位，顯示在 tooltip，例如「房晚」 */
  unit?: string
  /** 是否顯示右側圖例，預設 true。空間很小的摘要卡可關掉 */
  showLegend?: boolean
}

/** 切片內的百分比標籤 */
interface SliceLabelProps {
  cx: number
  cy: number
  midAngle: number
  innerRadius: number
  outerRadius: number
  percent: number
}

function renderSliceLabel(props: SliceLabelProps): React.ReactNode {
  const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props
  if (!percent || percent < MIN_LABEL_PCT) return null
  const RADIAN = Math.PI / 180
  const r = innerRadius + (outerRadius - innerRadius) * 0.62
  const x = cx + r * Math.cos(-midAngle * RADIAN)
  const y = cy + r * Math.sin(-midAngle * RADIAN)
  return (
    <text
      x={x}
      y={y}
      fill="#fff"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight={600}
      style={{ pointerEvents: 'none' }}
    >
      {`${(percent * 100).toFixed(1)}%`}
    </text>
  )
}

export default function SharePie<T>({
  data,
  nameOf,
  valueOf,
  keyOf,
  colorOf,
  topN = 8,
  height = 300,
  valueFormatter = fmtInt,
  unit = '',
  showLegend = true,
}: Props<T>) {
  const slices: SharePieDatum[] = useMemo(() => {
    // ⚠️ 分母用**全部**資料，不是只用前 N 名——否則佔比會被放大
    const sorted = [...data].sort((a, b) => valueOf(b) - valueOf(a))
    const head = sorted.slice(0, topN)
    const tail = sorted.slice(topN)

    const out: SharePieDatum[] = head.map((it, i) => ({
      key: keyOf ? keyOf(it) : nameOf(it),
      label: nameOf(it) || '（未指定）',
      value: valueOf(it),
      color: colorOf ? colorOf(it, i) : CHART_PALETTE[i % CHART_PALETTE.length],
    }))

    if (tail.length > 0) {
      const rest = tail.reduce((n, it) => n + valueOf(it), 0)
      if (rest > 0) {
        out.push({
          key: OTHER_KEY,
          label: `其他（${tail.length} 項）`,
          value: rest,
          color: '#bfbfbf',
          mergedCount: tail.length,
        })
      }
    }
    return out
  }, [data, nameOf, valueOf, keyOf, colorOf, topN])

  const total = useMemo(() => slices.reduce((n, s) => n + s.value, 0), [slices])

  if (slices.length === 0 || total <= 0) {
    return <Empty description="無資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={slices}
          dataKey="value"
          nameKey="label"
          cx={showLegend ? '35%' : '50%'}
          cy="50%"
          outerRadius={Math.min(height * 0.36, 110)}
          // recharts 的 PieLabel 型別是 (props: any) => ReactNode；
          // 這裡宣告明確參數型別，any 可指派過去，不需要轉型
          label={(props: SliceLabelProps) => renderSliceLabel(props)}
          labelLine={false}
          isAnimationActive={false}
        >
          {slices.map((s) => <Cell key={s.key} fill={s.color} />)}
        </Pie>

        <Tooltip
          formatter={(v: number, name: string) => [
            `${valueFormatter(v)}${unit}（${((v / total) * 100).toFixed(2)}%）`,
            name,
          ]}
        />

        {showLegend && (
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            width={230}
            iconType="circle"
            iconSize={9}
            formatter={(value: string, entry: unknown) => {
              const payload = (entry as { payload?: SharePieDatum })?.payload
              const v = payload?.value ?? 0
              const pct = total ? (v / total) * 100 : 0
              const short =
                value.length > LEGEND_MAX_CHARS
                  ? `${value.slice(0, LEGEND_MAX_CHARS)}…`
                  : value
              return (
                <span title={value} style={{ fontSize: 12 }}>
                  {short}
                  <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>
                    {pct.toFixed(1)}%
                  </Text>
                </span>
              )
            }}
          />
        )}
      </PieChart>
    </ResponsiveContainer>
  )
}
