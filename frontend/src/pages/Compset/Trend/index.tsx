/**
 * 競品分析 — 價格軌跡
 * Route: /compset/trend    Permission: compset_trend_view
 *
 * 規格書：`docs/SPEC_compset_analysis.md` §9.3
 *
 * 【這一頁在回答的問題】
 *   固定一個入住日，看各家報價**隨著日子逼近**怎麼走。
 *   ＝「競品什麼時候降價的？」「他們在幾天前開始砍？」
 *
 * ⭐ 這張圖是 `snapshot_date` 進唯一鍵的唯一理由（SPEC §5.5）。
 *    如果只留「最新一筆」，整個模組就只會有現況、沒有軌跡，
 *    而軌跡才是能拿來訂 pricing 策略的東西。
 *
 * ⚠️ 橫軸是**快照日**（哪一天抓的），不是入住日。兩者很容易混淆，
 *    所以圖上與軸標都寫明。
 *
 * ⚠️ 線斷掉 ≠ 資料掉了。B／C 級是每 3 天／每週抓一次，本來就會有空檔；
 *    `connectNulls` 刻意開著把點接起來，但下方會說明取樣頻率。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Card, Col, DatePicker, Empty, Row, Space, Spin, Statistic, Table,
  Tag, Tooltip, Typography, message,
} from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { useSearchParams } from 'react-router-dom'
import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer,
  Tooltip as ReTooltip, XAxis, YAxis,
} from 'recharts'

import { fetchTrend } from '@/api/compset'
import type { PriceBasis, TrendResult } from '@/types/compset'
import { BasisSwitch, IndexValue, fmtMoney } from '../components'

const { Text, Paragraph } = Typography

// 品牌色開頭（CLAUDE.md 受保護元素），其餘為區分用的輔助色
const LINE_COLORS = ['#1B3A5C', '#4BA8E8', '#52c41a', '#faad14', '#eb2f96', '#722ed1']

const CompsetTrendPage: React.FC = () => {
  const [params] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<TrendResult | null>(null)
  const [basis, setBasis] = useState<PriceBasis>('pretax')
  const [stayDate, setStayDate] = useState<Dayjs>(() => {
    const q = params.get('stay_date')
    return q && dayjs(q).isValid() ? dayjs(q) : dayjs().add(7, 'day')
  })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setData(await fetchTrend({ stayDate: stayDate.format('YYYY-MM-DD') }))
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [stayDate])

  useEffect(() => { load() }, [load])

  /** 把 `series`（key 是 hotel_id）轉成 recharts 要的「一列一個快照日」。 */
  const chartData = useMemo(() => {
    if (!data) return []
    return data.snapshot_dates.map((snap) => {
      const row: Record<string, unknown> = { snapshot_date: snap.slice(5) }
      data.hotels.forEach((h) => {
        const pt = (data.series[h.id] || []).find((p) => p.snapshot_date === snap)
        row[`h_${h.id}`] = pt
          ? (basis === 'pretax' ? pt.price_pretax : pt.price_gross)
          : null
      })
      const stat = data.index_line.find((s) => s.snapshot_date === snap)
      row.index = stat ? (basis === 'pretax' ? stat.index_pretax : stat.index_gross) : null
      row.sample = stat?.sample_count ?? 0
      return row
    })
  }, [data, basis])

  const latest = data?.index_line.length
    ? data.index_line[data.index_line.length - 1] : null
  const earliest = data?.index_line.length ? data.index_line[0] : null

  /** 自己的價格從第一批到最新一批變了多少 —— 「我自己有沒有動」。 */
  const selfDelta = useMemo(() => {
    if (!earliest || !latest) return null
    const a = basis === 'pretax' ? earliest.self_pretax : earliest.self_gross
    const b = basis === 'pretax' ? latest.self_pretax : latest.self_gross
    if (a === null || b === null) return null
    return b - a
  }, [earliest, latest, basis])

  /** 競品中位數的變化 —— 「他們有沒有動」。 */
  const medianDelta = useMemo(() => {
    if (!earliest || !latest) return null
    const a = basis === 'pretax' ? earliest.median_pretax : earliest.median_gross
    const b = basis === 'pretax' ? latest.median_pretax : latest.median_gross
    if (a === null || b === null) return null
    return b - a
  }, [earliest, latest, basis])

  const nDays = data?.snapshot_dates.length ?? 0

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Typography.Title level={4} style={{ margin: 0 }}>價格軌跡</Typography.Title>
          <Text type="secondary">
            固定入住日 <b>{stayDate.format('YYYY-MM-DD')}</b>，看各家報價隨快照日的變化
          </Text>
        </Col>
        <Col>
          <Space wrap>
            <BasisSwitch value={basis} onChange={setBasis} />
            <Tooltip title="要觀察的入住日。這一頁是「同一天的房價，隨著日子逼近怎麼變」。">
              <DatePicker value={stayDate} allowClear={false}
                onChange={(v) => v && setStayDate(v)} />
            </Tooltip>
            <a onClick={load}><ReloadOutlined /> 重新整理</a>
          </Space>
        </Col>
      </Row>

      {nDays === 1 && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }}
          message="這個入住日只有一批快照，畫不出軌跡"
          description="軌跡要累積好幾天的抓取才看得出來。剛上線時是正常的，
            A 級每天一批，大約一週後就有形狀了。" />
      )}

      <Spin spinning={loading}>
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic title="最新價格指數"
                valueRender={() => <IndexValue stat={latest} basis={basis} />} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                共 {nDays} 批快照
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic title="我自己的變動" value={selfDelta === null ? '—' : fmtMoney(selfDelta)}
                valueStyle={{ color: selfDelta === null ? undefined
                  : selfDelta > 0 ? '#cf1322' : selfDelta < 0 ? '#389e0d' : undefined }}
                prefix={selfDelta !== null && selfDelta > 0 ? '+' : ''} />
              <Text type="secondary" style={{ fontSize: 12 }}>第一批 → 最新一批</Text>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic title="競品中位數的變動"
                value={medianDelta === null ? '—' : fmtMoney(medianDelta)}
                valueStyle={{ color: medianDelta === null ? undefined
                  : medianDelta > 0 ? '#cf1322' : medianDelta < 0 ? '#389e0d' : undefined }}
                prefix={medianDelta !== null && medianDelta > 0 ? '+' : ''} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                他們動了、我沒動 ＝ 指數會跑掉
              </Text>
            </Card>
          </Col>
        </Row>

        <Card title="各家報價軌跡" style={{ marginBottom: 16 }}
          extra={<Text type="secondary" style={{ fontSize: 12 }}>
            橫軸 ＝ <b>快照日</b>（哪一天抓的），不是入住日
          </Text>}>
          {chartData.length === 0
            ? <Empty description="這個入住日還沒有資料" />
            : (
              <ResponsiveContainer width="100%" height={340}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="snapshot_date" />
                  <YAxis domain={['auto', 'auto']} tickFormatter={(v) => fmtMoney(v)} />
                  <ReTooltip formatter={(v: any) => fmtMoney(v)} />
                  <Legend />
                  {data?.hotels.map((h, i) => (
                    <Line key={h.id} type="monotone" dataKey={`h_${h.id}`}
                      name={h.is_self ? `${h.name}（自己）` : h.name}
                      stroke={LINE_COLORS[i % LINE_COLORS.length]}
                      strokeWidth={h.is_self ? 3 : 1.5}
                      dot={{ r: h.is_self ? 4 : 2 }}
                      connectNulls />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            )}
        </Card>

        <Card title="價格指數軌跡"
          extra={<Text type="secondary" style={{ fontSize: 12 }}>
            1.00 ＝ 與競品中位數同價
          </Text>}>
          {chartData.length === 0
            ? <Empty description="尚無資料" />
            : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="snapshot_date" />
                  <YAxis domain={['auto', 'auto']} />
                  <ReferenceLine y={1} stroke="#999" strokeDasharray="4 4" />
                  <ReTooltip formatter={(v: any, _n: string, p: any) =>
                    [`${v?.toFixed?.(3) ?? v}（n=${p?.payload?.sample}）`, '價格指數']} />
                  <Line type="monotone" dataKey="index" name="價格指數"
                    stroke="#1B3A5C" strokeWidth={2} dot={{ r: 3 }} connectNulls />
                </LineChart>
              </ResponsiveContainer>
            )}
          <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
            指數變動有兩種可能：<b>我自己調價</b>，或<b>競品調價而我沒動</b>。
            上面三張卡片就是在分這兩件事。
            線上的空檔是取樣頻率造成的（B 級每 3 天、C 級每週各一次），不是資料掉了。
          </Paragraph>
        </Card>
      </Spin>
    </div>
  )
}

export default CompsetTrendPage
