/**
 * 戰情 KPI — 工作總覽的視覺元件（2026-11-24）
 *   DotNumber    點陣（LED 式）大數字
 *   PillTrend    近 7 日圓角直條（今日深色強調）
 *   RiskScatter  人員散點圖：x＝實際工時、y＝逾期件數，紅區＝超過門檻
 *   DotScale     點狀評分：完成比例
 *   StatusPill   狀態膠囊（彩色圓點＋文字）
 *   ItemDrawer   單一工作的明細抽屜（含「開啟工作單」）
 * 配色沿用戰情 KPI 既有色：藍 #4BA8E8、深藍 #1B3A5C、紅 #e74c3c、橘 #faad14、綠 #52c41a、灰 #bfbfbf。
 */
import React from 'react'
import { Badge, Button, Descriptions, Drawer, Empty, Space, Tag, Tooltip, Typography } from 'antd'
import { Bar, BarChart, Cell, CartesianGrid, ReferenceArea, ResponsiveContainer, Scatter, ScatterChart, Tooltip as RTooltip, XAxis, YAxis, ZAxis } from 'recharts'

import type { WrWorkItem, WrWorkPerson } from '@/api/warRoom'

const { Text } = Typography

export const WR_BLUE = '#4BA8E8'
export const WR_NAVY = '#1B3A5C'
export const WR_RED = '#e74c3c'
export const WR_ORANGE = '#faad14'
export const WR_GREEN = '#52c41a'
export const WR_GREY = '#bfbfbf'

// 5×7 點陣字型（0–9）
const GLYPHS: Record<string, string[]> = {
  '0': ['01110', '10001', '10011', '10101', '11001', '10001', '01110'],
  '1': ['00100', '01100', '00100', '00100', '00100', '00100', '01110'],
  '2': ['01110', '10001', '00001', '00010', '00100', '01000', '11111'],
  '3': ['11111', '00010', '00100', '00010', '00001', '10001', '01110'],
  '4': ['00010', '00110', '01010', '10010', '11111', '00010', '00010'],
  '5': ['11111', '10000', '11110', '00001', '00001', '10001', '01110'],
  '6': ['00110', '01000', '10000', '11110', '10001', '10001', '01110'],
  '7': ['11111', '00001', '00010', '00100', '01000', '01000', '01000'],
  '8': ['01110', '10001', '10001', '01110', '10001', '10001', '01110'],
  '9': ['01110', '10001', '10001', '01111', '00001', '00010', '01100'],
}

/** 點陣大數字：以 SVG 圓點拼出數字，亮點為 color，暗點為淡色底 */
export function DotNumber({ value, color = WR_NAVY, dot = 5, gap = 3 }: { value: number | string; color?: string; dot?: number; gap?: number }) {
  const chars = String(value).split('')
  const step = dot + gap
  const cellW = 5 * step
  const width = chars.length * (cellW + step) - step
  const height = 7 * step - gap
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={String(value)}>
      {chars.map((ch, ci) => {
        const rows = GLYPHS[ch]
        if (!rows) return null
        const ox = ci * (cellW + step)
        return rows.map((row, ri) =>
          row.split('').map((bit, cj) => (
            <circle
              key={`${ci}-${ri}-${cj}`}
              cx={ox + cj * step + dot / 2}
              cy={ri * step + dot / 2}
              r={dot / 2}
              fill={color}
              opacity={bit === '1' ? 1 : 0.12}
            />
          )),
        )
      })}
    </svg>
  )
}

/** 近 7 日圓角直條：今日以深藍強調，其餘為藍 */
export function PillTrend({ trend }: { trend: { date: string; logged: number; rate: number | null; is_today: boolean }[] }) {
  const data = trend.map(t => ({ d: t.date.slice(5), v: t.logged, rate: t.rate, today: t.is_today }))
  return (
    <div style={{ width: '100%', height: 150 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <XAxis dataKey="d" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis hide allowDecimals={false} />
          <RTooltip
            formatter={(v: number, _n, p) => [`${v} 筆`, p?.payload?.rate === null ? '無完成狀態' : `完成率 ${p?.payload?.rate}%`]}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="v" name="已登錄" barSize={18} radius={[9, 9, 9, 9]} isAnimationActive={false}>
            {data.map(x => <Cell key={x.d} fill={x.today ? WR_NAVY : WR_BLUE} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** 人員散點圖：紅區＝逾期 ≥ 門檻 或 實際工時 ≥ 門檻；點擊人員開啟其明細 */
export function RiskScatter({
  people, thresholds, onPick,
}: {
  people: WrWorkPerson[]
  thresholds: { overdue: number; minutes: number }
  onPick: (p: WrWorkPerson) => void
}) {
  if (people.length === 0) return <Empty description="本月尚無具名人員" />
  const maxX = Math.max(thresholds.minutes * 1.15, ...people.map(p => p.actual_min))
  const maxY = Math.max(thresholds.overdue + 1, ...people.map(p => p.overdue)) + 1
  const pts = people.map(p => ({ ...p, x: p.actual_min, y: p.overdue, z: 1 }))
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.2)" />
          <XAxis type="number" dataKey="x" name="實際工時" domain={[0, maxX]} unit=" 分" tick={{ fontSize: 11 }} />
          <YAxis type="number" dataKey="y" name="逾期" domain={[0, maxY]} allowDecimals={false} tick={{ fontSize: 11 }} />
          <ZAxis type="number" dataKey="z" range={[120, 120]} />
          <ReferenceArea x1={thresholds.minutes} x2={maxX} y1={0} y2={maxY} fill={WR_RED} fillOpacity={0.08} stroke="none" />
          <ReferenceArea x1={0} x2={maxX} y1={thresholds.overdue} y2={maxY} fill={WR_RED} fillOpacity={0.08} stroke="none" />
          <RTooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (!active || !payload || !payload.length) return null
              const p = payload[0].payload as WrWorkPerson
              return (
                <div style={{ background: '#fff', color: '#333', border: '1px solid #e8e8e8', borderRadius: 8, padding: '8px 10px', fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.12)' }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{p.person}{p.risk && <Tag color="red" style={{ marginLeft: 6 }}>紅區</Tag>}</div>
                  <div>實際 {p.actual_min} 分（預估 {p.estimated_min} 分）</div>
                  <div>逾期 {p.overdue} 件　未完成 {p.open} 件　已完成 {p.done} 件</div>
                  <div style={{ color: WR_BLUE, marginTop: 4 }}>點擊查看明細</div>
                </div>
              )
            }}
          />
          <Scatter
            data={pts.filter(p => !p.risk)}
            fill={WR_BLUE}
            onClick={(d: { payload?: WrWorkPerson }) => d?.payload && onPick(d.payload)}
            cursor="pointer"
          />
          <Scatter
            data={pts.filter(p => p.risk)}
            fill={WR_RED}
            onClick={(d: { payload?: WrWorkPerson }) => d?.payload && onPick(d.payload)}
            cursor="pointer"
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

/** 點狀評分：10 個點，依完成比例填色（完成數 ÷ 已到期項目數） */
export function DotScale({ done, open }: { done: number; open: number }) {
  const total = done + open
  if (total === 0) return <Text type="secondary" style={{ fontSize: 12 }}>無完成紀錄</Text>
  const filled = Math.round((done / total) * 10)
  const rate = Math.round((done / total) * 100)
  return (
    <Tooltip title={`完成 ${done} / ${total}`}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
        <span style={{ display: 'inline-flex', gap: 3 }}>
          {Array.from({ length: 10 }).map((_, i) => (
            <span key={i} style={{ width: 8, height: 8, borderRadius: '50%', background: i < filled ? WR_GREEN : '#e8e8e8', display: 'inline-block' }} />
          ))}
        </span>
        <Text style={{ fontSize: 12 }}>{rate}%</Text>
      </span>
    </Tooltip>
  )
}

/** 狀態膠囊：彩色圓點＋文字（逾期＝紅、今日＝橘、即將＝藍、已完成＝綠） */
export function StatusPill({ item }: { item: WrWorkItem }) {
  if (item.state) {
    const color = item.state === '逾期' ? WR_RED : item.state === '今日' ? WR_ORANGE : WR_BLUE
    return <Badge color={color} text={item.state} />
  }
  if (item.status === '已完成') return <Badge color={WR_GREEN} text="已完成" />
  if (item.status === '未完成') return <Badge color={WR_ORANGE} text="未完成" />
  return <Badge color={WR_GREY} text="已登錄" />
}

/** 單一工作明細抽屜：欄位明細＋「開啟工作單」（有 Ragic 連結時） */
export function ItemDrawer({ item, onClose, getContainer }: { item: WrWorkItem | null; onClose: () => void; getContainer?: () => HTMLElement }) {
  return (
    <Drawer
      open={!!item}
      onClose={onClose}
      width={480}
      title={item ? `${item.source_label}：${item.task || '(無說明)'}` : ''}
      getContainer={getContainer}
      extra={
        item?.ragic_url ? (
          <Button type="primary" onClick={() => window.open(item.ragic_url, '_blank', 'noopener')}>開啟工作單</Button>
        ) : (
          <Tooltip title="此工作沒有 Ragic 連結"><Button disabled>開啟工作單</Button></Tooltip>
        )
      }
    >
      {item && (
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Space>
            <StatusPill item={item} />
            {item.is_estimated && <Tag>估（預估工時）</Tag>}
          </Space>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="日期">{item.date}</Descriptions.Item>
            <Descriptions.Item label="類別">{item.category}</Descriptions.Item>
            <Descriptions.Item label="人員">{item.persons}</Descriptions.Item>
            <Descriptions.Item label="工時">{item.work_min} 分</Descriptions.Item>
            {Object.entries(item.detail ?? {}).filter(([, v]) => v !== '').map(([k, v]) => (
              <Descriptions.Item key={k} label={k}>{v}</Descriptions.Item>
            ))}
          </Descriptions>
        </Space>
      )}
    </Drawer>
  )
}
