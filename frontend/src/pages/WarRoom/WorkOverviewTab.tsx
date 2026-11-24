/**
 * 戰情 KPI — 「工作總覽」TAB（2026-11-24；規劃 claude/plan_war_room_work_overview.md）
 *
 * 版面：標題列（月份／重新整理／深色）→ 點陣大數字（完成率、逾期）→ KPI 卡 → 近 7 日圓角直條
 *       → 完成率環 → 已排定／最近完成（含「查看明細」「開啟工作單」）→ 人員散點圖（紅區）＋排行（點狀評分）
 *   - 工時口徑＝工作日誌（具名人員）；實際與預估分開
 *   - 完成率只計有完成狀態且已到期的項目；每日巡檢只顯示已登錄筆數
 * 資料來源：GET /war-room/work-overview?month=YYYY-MM（後端 60 秒快取）
 */
import React, { useCallback, useEffect, useState } from 'react'
import { Alert, Button, Card, Col, ConfigProvider, DatePicker, Drawer, Empty, Progress, Row, Space, Spin, Statistic, Switch, Table, Tag, Typography, theme } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import { fetchWarRoomWorkOverview, type WrWorkItem, type WrWorkOverview, type WrWorkPerson } from '@/api/warRoom'
import { DotNumber, DotScale, ItemDrawer, PillTrend, RiskScatter, StatusPill, WR_BLUE, WR_NAVY, WR_RED } from './WorkOverviewWidgets'

const { Text } = Typography

/** 與後端 60 秒快取對齊 */
const AUTO_REFRESH_MS = 60 * 1000

function fmtMin(n: number): string {
  return `${n.toLocaleString('zh-TW')} 分`
}

function ItemLabel({ item }: { item: WrWorkItem }) {
  return (
    <Space size={6} wrap>
      <Tag>{item.source_label}</Tag>
      <Text>{item.task || '(無說明)'}</Text>
      {item.is_estimated && <Tag>估</Tag>}
    </Space>
  )
}

export default function WorkOverviewTab() {
  const [month, setMonth] = useState<Dayjs>(dayjs())
  const [data, setData] = useState<WrWorkOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dark, setDark] = useState(false)
  const [item, setItem] = useState<WrWorkItem | null>(null)
  const [person, setPerson] = useState<WrWorkPerson | null>(null)

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
  const total = data?.rings.find(r => r.category === '總計')
  const rateText = total?.rate === null || total?.rate === undefined ? '—' : String(total.rate)
  const muted = dark ? 'rgba(255,255,255,0.45)' : undefined

  return (
    <ConfigProvider theme={{ algorithm: dark ? theme.darkAlgorithm : theme.defaultAlgorithm }}>
      <div style={{ background: dark ? '#141414' : undefined, padding: dark ? 16 : 0, borderRadius: 8 }}>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Space style={{ justifyContent: 'space-between', width: '100%' }} wrap>
            <Space>
              <Text strong>月份</Text>
              <DatePicker picker="month" value={month} allowClear={false} onChange={v => v && setMonth(v)} />
              <Button icon={<ReloadOutlined />} onClick={() => void load(month)} loading={loading}>重新整理</Button>
            </Space>
            <Space>
              {data && <Text type="secondary" style={{ fontSize: 12 }}>資料至 {data.data_end}　更新於 {data.generated_at}</Text>}
              <Switch checked={dark} onChange={setDark} checkedChildren="深色" unCheckedChildren="淺色" />
            </Space>
          </Space>

          {error && <Alert type="warning" showIcon message={error} />}
          {!data && loading && <Spin />}

          {data && k && (
            <>
              <Card size="small">
                <Row gutter={[24, 16]} align="middle">
                  <Col xs={24} md={12}>
                    <div style={{ color: muted, fontSize: 12 }}>本月完成率</div>
                    <Space align="end">
                      <DotNumber value={rateText} color={dark ? WR_BLUE : WR_NAVY} />
                      <Text style={{ fontSize: 20, color: muted }}>%</Text>
                    </Space>
                  </Col>
                  <Col xs={24} md={12}>
                    <div style={{ color: muted, fontSize: 12 }}>逾期未做（保養）</div>
                    <DotNumber value={k.overdue_count} color={k.overdue_count > 0 ? WR_RED : (dark ? WR_BLUE : WR_NAVY)} />
                  </Col>
                </Row>
              </Card>

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
                    valueStyle={{ color: k.overdue_count > 0 ? WR_RED : undefined }} /></Card>
                </Col>
              </Row>

              <Card size="small" title="近 7 日已登錄工作（筆）">
                <PillTrend trend={data.trend} />
              </Card>

              <Card size="small" title="完成率（本月、已到期項目）">
                <Row gutter={[16, 16]}>
                  {data.rings.map(r => (
                    <Col xs={12} sm={8} md={4} key={r.category} style={{ textAlign: 'center' }}>
                      <Progress
                        type="circle"
                        size={96}
                        percent={r.rate ?? 0}
                        format={() => (r.rate === null ? '—' : `${r.rate}%`)}
                        strokeColor={r.category === '總計' ? WR_BLUE : undefined}
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
                          { title: '狀態', width: 90, render: (_: unknown, r: WrWorkItem) => <StatusPill item={r} /> },
                          { title: '排定日', dataIndex: 'date', width: 100 },
                          { title: '工作', render: (_: unknown, r: WrWorkItem) => <ItemLabel item={r} /> },
                          { title: '負責人', width: 100, render: (_: unknown, r: WrWorkItem) => r.planned_person || r.persons },
                          { title: '操作', width: 90, render: (_: unknown, r: WrWorkItem) => <Button size="small" type="link" onClick={() => setItem(r)}>查看明細</Button> },
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
                          { title: '工作', render: (_: unknown, r: WrWorkItem) => <ItemLabel item={r} /> },
                          { title: '人員', dataIndex: 'persons', width: 100 },
                          { title: '操作', width: 90, render: (_: unknown, r: WrWorkItem) => <Button size="small" type="link" onClick={() => setItem(r)}>查看明細</Button> },
                        ]}
                      />
                    )}
                  </Card>
                </Col>
              </Row>

              <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                  <Card size="small" title="人員負荷（紅區＝逾期或工時超過門檻）" extra={<Text type="secondary" style={{ fontSize: 12 }}>點擊人員看明細</Text>}>
                    <RiskScatter people={data.people} thresholds={data.thresholds} onPick={setPerson} />
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card size="small" title="人員排行（實際＋預估）">
                    {data.ranking.length === 0 ? <Empty description="本月尚無具名人員工時" /> : (
                      <Table<WrWorkOverview['ranking'][number]>
                        size="small"
                        pagination={false}
                        rowKey="person"
                        dataSource={data.ranking}
                        onRow={r => ({ onClick: () => setPerson(data.people.find(p => p.person === r.person) ?? null), style: { cursor: 'pointer' } })}
                        columns={[
                          { title: '人員', dataIndex: 'person', render: (v: string) => {
                            const p = data.people.find(x => x.person === v)
                            return <Space>{v}{p?.risk && <Tag color="red">紅區</Tag>}</Space>
                          } },
                          { title: '實際', dataIndex: 'actual_min', render: (v: number) => fmtMin(v) },
                          { title: '預估', dataIndex: 'estimated_min', render: (v: number) => fmtMin(v) },
                          { title: '完成', render: (_: unknown, r: { done: number; open: number }) => <DotScale done={r.done} open={r.open} /> },
                        ]}
                      />
                    )}
                  </Card>
                </Col>
              </Row>
            </>
          )}
        </Space>

        <ItemDrawer item={item} onClose={() => setItem(null)} />
        <Drawer
          open={!!person}
          onClose={() => setPerson(null)}
          width={560}
          title={person ? `${person.person}：本月工作` : ''}
        >
          {person && (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Space wrap>
                {person.risk && <Tag color="red">紅區</Tag>}
                <Text>實際 {fmtMin(person.actual_min)}</Text>
                <Text type="secondary">預估 {fmtMin(person.estimated_min)}</Text>
                <Text>逾期 {person.overdue}</Text>
              </Space>
              <Table<WrWorkItem>
                size="small"
                pagination={{ pageSize: 10, hideOnSinglePage: true }}
                rowKey={r => `${r.date}-${r.source}-${r.task}`}
                dataSource={person.items}
                columns={[
                  { title: '日期', dataIndex: 'date', width: 100 },
                  { title: '工作', render: (_: unknown, r: WrWorkItem) => <ItemLabel item={r} /> },
                  { title: '狀態', width: 90, render: (_: unknown, r: WrWorkItem) => <StatusPill item={r} /> },
                  { title: '工時', dataIndex: 'work_min', width: 80, render: (v: number) => `${v} 分` },
                  { title: '操作', width: 90, render: (_: unknown, r: WrWorkItem) => <Button size="small" type="link" onClick={() => setItem(r)}>查看明細</Button> },
                ]}
              />
            </Space>
          )}
        </Drawer>
      </div>
    </ConfigProvider>
  )
}
