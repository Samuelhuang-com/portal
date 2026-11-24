/**
 * 戰情 KPI — 「工作總覽」TAB（2026-11-24；規劃 claude/plan_war_room_work_overview.md）
 *
 * 版面借鏡 Overview：KPI 列 → 完成率環（5 類＋總計）→ 最近完成／已排定（逾期、今日、即將）→ 人員排行。
 *   - 工時口徑＝工作日誌（具名人員）；實際與預估分開，排行兩欄並列
 *   - 完成率只計有「完成狀況」的項目（PM、報修）
 *   - 未來排定的報修：報修無排定日，不列入「已排定」；未完成報修計入待執行
 * 資料來源：GET /war-room/work-overview?month=YYYY-MM（後端 60 秒快取）
 */
import React, { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Card, Col, DatePicker, Empty, Progress, Row, Space, Spin, Statistic, Table, Tag, Tooltip, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import { fetchWarRoomWorkOverview, type WrWorkItem, type WrWorkOverview } from '@/api/warRoom'

const { Text } = Typography

/** 與後端 60 秒快取對齊 */
const AUTO_REFRESH_MS = 60 * 1000

const STATE_COLOR: Record<string, string> = { 逾期: 'red', 今日: 'orange', 即將: 'blue' }

function fmtMin(n: number): string {
  return `${n.toLocaleString('zh-TW')} 分`
}

function ItemTag({ item }: { item: WrWorkItem }) {
  return (
    <Space size={6} wrap>
      <Tag color="default">{item.source_label}</Tag>
      <Text>{item.task || '(無說明)'}</Text>
      {item.is_estimated && <Tooltip title="無實際工時，以預估工時計入"><Tag color="default">估</Tag></Tooltip>}
    </Space>
  )
}

export default function WorkOverviewTab() {
  const [month, setMonth] = useState<Dayjs>(dayjs())
  const [data, setData] = useState<WrWorkOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (m: Dayjs) => {
    setLoading(true)
    try {
      setData(await fetchWarRoomWorkOverview(m.format('YYYY-MM')))
      setError(null)
    } catch {
      setError('工作總覽載入失敗，已保留上一次資料')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load(month) }, [load, month])

  // 只有當月自動更新；切到背景暫停
  useEffect(() => {
    const isCurrent = month.format('YYYY-MM') === dayjs().format('YYYY-MM')
    if (!isCurrent) return
    const id = window.setInterval(() => {
      if (document.visibilityState === 'visible') void load(month)
    }, AUTO_REFRESH_MS)
    return () => window.clearInterval(id)
  }, [load, month])

  const k = data?.kpis

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }} wrap>
        <Space>
          <Text strong>月份</Text>
          <DatePicker picker="month" value={month} allowClear={false} onChange={v => v && setMonth(v)} />
          <Button icon={<ReloadOutlined />} onClick={() => void load(month)} loading={loading}>重新整理</Button>
        </Space>
        {data && <Text type="secondary" style={{ fontSize: 12 }}>資料至 {data.data_end}　更新於 {data.generated_at}</Text>}
      </Space>

      {error && <Alert type="warning" showIcon message={error} />}
      {!data && loading && <Spin />}

      {data && k && (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6}>
              <Card size="small"><Statistic title="本月實際工時" value={fmtMin(k.actual_min)} />
                <Text type="secondary" style={{ fontSize: 12 }}>預估 {fmtMin(k.estimated_min)}（未執行）</Text></Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small"><Statistic title="已登錄工作" value={k.logged_count} suffix="筆" /></Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small">
                <Statistic title="待執行" value={k.pending_pm_count + k.open_repairs_count} suffix="件" />
                <Text type="secondary" style={{ fontSize: 12 }}>排定未做 {k.pending_pm_count}　未完成報修 {k.open_repairs_count}</Text>
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card size="small"><Statistic title="逾期未做（保養）" value={k.overdue_count} suffix="件"
                valueStyle={{ color: k.overdue_count > 0 ? '#e74c3c' : undefined }} /></Card>
            </Col>
          </Row>

          <Card size="small" title="完成率（本月、已到期項目）">
            <Row gutter={[16, 16]}>
              {data.rings.map(r => (
                <Col xs={12} sm={8} md={4} key={r.category} style={{ textAlign: 'center' }}>
                  <Progress
                    type="circle"
                    size={96}
                    percent={r.rate ?? 0}
                    format={() => (r.rate === null ? '—' : `${r.rate}%`)}
                    strokeColor={r.category === '總計' ? '#4BA8E8' : undefined}
                  />
                  <div style={{ marginTop: 6 }}>{r.category}</div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {r.total ? `${r.done} / ${r.total}` : r.logged ? `已登錄 ${r.logged} 筆` : '無紀錄'}
                  </Text>
                </Col>
              ))}
            </Row>
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card size="small" title="已排定工作（逾期＋7 日內）">
                {data.upcoming.length === 0 ? <Empty description="沒有逾期或即將到期的項目" /> : (
                  <Table<WrWorkItem>
                    size="small"
                    pagination={false}
                    rowKey={r => `${r.date}-${r.source}-${r.task}-${r.persons}`}
                    dataSource={data.upcoming}
                    columns={[
                      { title: '狀態', dataIndex: 'state', width: 70,
                        render: (s: string) => <Tag color={STATE_COLOR[s] ?? 'default'}>{s}</Tag> },
                      { title: '排定日', dataIndex: 'date', width: 100 },
                      { title: '工作', render: (_: unknown, r: WrWorkItem) => <ItemTag item={r} /> },
                      { title: '負責人', dataIndex: 'planned_person', width: 100, render: (v: string, r: WrWorkItem) => v || r.persons },
                      { title: '預估', dataIndex: 'work_min', width: 80, render: (v: number) => `${v} 分` },
                    ]}
                  />
                )}
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card size="small" title="最近完成">
                {data.recent.length === 0 ? <Empty description="本月尚無完成紀錄" /> : (
                  <Table<WrWorkItem>
                    size="small"
                    pagination={false}
                    rowKey={r => `${r.date}-${r.source}-${r.task}-${r.persons}`}
                    dataSource={data.recent}
                    columns={[
                      { title: '日期', dataIndex: 'date', width: 100 },
                      { title: '工作', render: (_: unknown, r: WrWorkItem) => <ItemTag item={r} /> },
                      { title: '人員', dataIndex: 'persons', width: 110 },
                      { title: '實際', dataIndex: 'work_min', width: 80, render: (v: number) => `${v} 分` },
                    ]}
                  />
                )}
              </Card>
            </Col>
          </Row>

          <Card size="small" title="人員排行（實際＋預估）">
            {data.ranking.length === 0 ? <Empty description="本月尚無具名人員工時" /> : (
              <Table
                size="small"
                pagination={false}
                rowKey="person"
                dataSource={data.ranking}
                columns={[
                  { title: '人員', dataIndex: 'person' },
                  { title: '實際工時', dataIndex: 'actual_min', render: (v: number) => fmtMin(v) },
                  { title: '預估工時', dataIndex: 'estimated_min', render: (v: number) => fmtMin(v) },
                ]}
              />
            )}
          </Card>
        </>
      )}
    </Space>
  )
}
