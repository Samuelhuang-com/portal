/**
 * 單日預測拆解 Drawer（CLAUDE.md §7 強制規範）
 *
 * 標題列格式：
 *   [星期 Tag]  預測明細：[YYYY-MM-DD]   🔗 對照實績
 *
 * 這個 Drawer 是整個預測功能可信度的核心：使用者必須看得到
 * 「這個數字是怎麼乘出來的」，才有辦法判斷該不該相信、哪裡該人工調整。
 * 無 Ragic 連結 —— 本模組資料來自人工上傳的 OPERA TXT，不是 Ragic 同步。
 */
import React from 'react'
import { Alert, Descriptions, Drawer, Space, Table, Tag, Typography } from 'antd'

import type { ForecastDayRow } from '@/types/opera'
import { ACCENT, BRAND, EMPTY, GREEN, ORANGE, RED, fmtMoney, fmtPct } from './formatters'

const { Text } = Typography

interface Props {
  open: boolean
  row: ForecastDayRow | null
  onClose: () => void
}

/** 係數偏離 1.0 越多顏色越明顯，讓使用者一眼看出是哪一項在推動預測 */
function factorColor(v: number): string {
  if (v >= 1.08) return GREEN
  if (v <= 0.92) return RED
  return 'inherit'
}

const ForecastDayDrawer: React.FC<Props> = ({ open, row, onClose }) => {
  if (!row) {
    return <Drawer open={open} onClose={onClose} width={520} title="預測明細" />
  }

  const b = row.breakdown

  const factorRows = [
    { key: 'baseline', name: '基準值', adr: b.baseline_adr, occ: b.baseline_occ, isBase: true,
      note: `錨定 ${b.anchor_date}（最近一年的加權值）` },
    { key: 'dow', name: `星期係數（${row.weekday_label}）`, adr: b.dow_adr, occ: b.dow_occ,
      note: '該星期別相對整體的倍數' },
    { key: 'month', name: `月份係數（${Number(row.business_date.slice(5, 7))} 月）`,
      adr: b.month_adr, occ: b.month_occ, note: '已扣除星期效應，避免重複解釋' },
    { key: 'growth', name: `年成長（${b.years_from_anchor >= 0 ? '+' : ''}${b.years_from_anchor.toFixed(2)} 年）`,
      adr: b.growth_adr, occ: b.growth_occ, note: '以錨點為起算，往前推或往回推' },
    { key: 'event', name: '事件係數', adr: b.event_adr, occ: b.event_occ,
      note: row.events.length ? row.events.map((e) => e.name).join('、') : '此日無事件' },
  ]

  const title = (
    <Space size={8} wrap>
      <Tag color={row.weekday >= 4 ? ORANGE : ACCENT}>{row.weekday_label}</Tag>
      <Text strong style={{ color: BRAND }}>{`預測明細：${row.business_date}`}</Text>
      {row.is_history && <Tag color="blue">已有實績</Tag>}
    </Space>
  )

  return (
    <Drawer open={open} onClose={onClose} width={520} title={title}>
      {/* ① 基本欄位 */}
      <Descriptions size="small" column={1} bordered title="預測結果">
        <Descriptions.Item label="預測 ADR">
          <Text strong>{`$ ${fmtMoney(row.predicted_adr)}`}</Text>
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            {`區間 $${fmtMoney(row.adr_lower)} ~ $${fmtMoney(row.adr_upper)}`}
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="預測住房率">
          <Text strong>{fmtPct(row.predicted_occupancy)}</Text>
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            {`區間 ${fmtPct(row.occ_lower)} ~ ${fmtPct(row.occ_upper)}`}
          </Text>
        </Descriptions.Item>
        <Descriptions.Item label="預測售出房晚">
          {`${row.predicted_sold_rooms.toFixed(1)} ／ 可售 ${b.available_rooms.toFixed(0)}`}
        </Descriptions.Item>
        <Descriptions.Item label="預測營收">
          <Text strong>{`$ ${fmtMoney(row.predicted_revenue)}`}</Text>
        </Descriptions.Item>
      </Descriptions>

      {/* ② 明細欄位：係數拆解 */}
      <Descriptions size="small" column={1} bordered title="係數拆解" style={{ marginTop: 16 }}>
        <Descriptions.Item label="ADR 公式">
          <Text code style={{ fontSize: 12 }}>{b.formula_adr}</Text>
        </Descriptions.Item>
      </Descriptions>

      <Table
        size="small"
        rowKey="key"
        style={{ marginTop: 12 }}
        pagination={false}
        dataSource={factorRows}
        columns={[
          { title: '項目', dataIndex: 'name', width: 170 },
          {
            title: 'ADR',
            dataIndex: 'adr',
            width: 92,
            align: 'right',
            render: (v: number, r) =>
              r.isBase
                ? <Text strong>{`$${fmtMoney(v)}`}</Text>
                : <Text style={{ color: factorColor(v) }}>{`× ${v.toFixed(3)}`}</Text>,
          },
          {
            title: '住房率',
            dataIndex: 'occ',
            width: 92,
            align: 'right',
            render: (v: number, r) =>
              r.isBase
                ? <Text strong>{fmtPct(v)}</Text>
                : <Text style={{ color: factorColor(v) }}>{`× ${v.toFixed(3)}`}</Text>,
          },
          {
            title: '說明',
            dataIndex: 'note',
            render: (v: string) => <Text type="secondary" style={{ fontSize: 12 }}>{v || EMPTY}</Text>,
          },
        ]}
      />

      {/* ③ 對照 */}
      <Descriptions size="small" column={1} bordered title="對照" style={{ marginTop: 16 }}>
        <Descriptions.Item label="樸素基準">
          {row.naive
            ? (
              <Space direction="vertical" size={0}>
                <Text>{`$${fmtMoney(row.naive.predicted_adr)}　${fmtPct(row.naive.predicted_occupancy)}`}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {`取自 ${row.naive.reference_date}（去年同星期）`}
                </Text>
              </Space>
            )
            : <Text type="secondary">{EMPTY}（去年同期無資料）</Text>}
        </Descriptions.Item>
        <Descriptions.Item label="實際值">
          {row.actual
            ? (
              <Space direction="vertical" size={0}>
                <Text strong>{`$${fmtMoney(row.actual.adr)}　${fmtPct(row.actual.occupancy)}`}</Text>
                <Text
                  type="secondary"
                  style={{ fontSize: 12, color: Math.abs(row.actual.adr - row.predicted_adr) / (row.actual.adr || 1) > 0.15 ? RED : undefined }}
                >
                  {`預測誤差 ${row.actual.adr ? (((row.predicted_adr - row.actual.adr) / row.actual.adr) * 100).toFixed(1) : '—'}%`}
                </Text>
              </Space>
            )
            : <Text type="secondary">{EMPTY}（尚未發生）</Text>}
        </Descriptions.Item>
      </Descriptions>

      {row.events.length > 0 && (
        <Descriptions size="small" column={1} bordered title="套用的事件" style={{ marginTop: 16 }}>
          {row.events.map((e, i) => (
            <Descriptions.Item key={`${e.name}-${i}`} label={e.name}>
              <Space size={6} wrap>
                <Tag>{e.category}</Tag>
                <Text>{`ADR ×${e.adr_index.toFixed(2)}　住房率 ×${e.occ_index.toFixed(2)}`}</Text>
                <Tag color={e.source_label.includes('學習') ? 'blue' : 'default'}>{e.source_label}</Tag>
              </Space>
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}

      <Alert
        type="warning"
        showIcon
        style={{ marginTop: 16 }}
        message="單日預測的不確定性很大"
        description={
          '69 間房的飯店，一個 20 間房的團體就能讓住房率跳 29 個百分點。'
          + '做訂價與預算決策請看週／月的期間預測，不要只看單日。'
        }
      />
    </Drawer>
  )
}

export default ForecastDayDrawer
