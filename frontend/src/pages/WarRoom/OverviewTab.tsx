/**
 * 戰情 KPI — 「值班總覽」TAB（2026-10-15 新增；規格 docs/SPEC_war_room.md §2）
 *
 * 每個巡檢模組一張卡：燈號（依今日狀態）、一句摘要、今日涵蓋率、近 7 日趨勢。
 *   - 異常 → 嚴重（紅）；截止時間後仍未填 → 警告（橘）；全部正常 → 綠；今日無排定 → 灰
 *   - 門檻：有異常即嚴重；超過「巡檢截止時間」仍未填即警告（設定在「告警」TAB）
 *   - 點卡片開明細抽屜，列出異常與未填的點位；點點位開設備履歷
 * 資料來源：GET /war-room/overview（與樓層巡檢圖 day_status 同一份口徑）。
 */
import React, { useCallback, useEffect, useState } from 'react'
import { Alert, Badge, Button, Card, Col, DatePicker, Drawer, Empty, Row, Space, Spin, Table, Tag, Tooltip, Typography } from 'antd'
import { LeftOutlined, ReloadOutlined, RightOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'
import { Line, LineChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'

import { fetchWarRoomOverview, type OverviewLevel, type WrOverview, type WrOverviewModule, type WrOverviewItem } from '@/api/warRoom'
import { fetchLastUpdated, type LastUpdatedResult } from '@/api/ragic'
import { AssetHistoryDrawer, type AssetTarget } from './AssetHistory'

const { Text } = Typography

/** 巡檢資料來源（後端 _LAST_UPDATED_SOURCES）：商場工務巡檢＋整棟巡檢四層 */
const FRESH_SOURCES = ['商場工務巡檢', 'B1F巡檢', 'B2F巡檢', 'B4F巡檢', 'RF巡檢']
/** 今天的看板每 60 秒自動更新 */
const AUTO_REFRESH_MS = 60 * 1000
/** 今天的資料庫最後寫入距今超過這個分鐘數，顯示「可能過期」警示（同步排程間隔若超過此值會持續誤報，需一併調整） */
const STALE_MINUTES = 120

const LEVEL_META: Record<OverviewLevel, { color: string; badge: 'error' | 'warning' | 'success' | 'default'; text: string }> = {
  critical: { color: '#e74c3c', badge: 'error', text: '嚴重' },
  warning:  { color: '#faad14', badge: 'warning', text: '警告' },
  ok:       { color: '#52c41a', badge: 'success', text: '正常' },
  none:     { color: '#bfbfbf', badge: 'default', text: '無排定' },
}
const STATUS_TEXT: Record<string, { text: string; color: string }> = {
  abnormal:  { text: '異常', color: 'red' },
  unchecked: { text: '未填', color: 'orange' },
  normal:    { text: '正常', color: 'green' },
  no_record: { text: '無紀錄', color: 'default' },
}

/** 近 7 日涵蓋率迷你折線（無資料的日子斷線） */
function Sparkline({ trend }: { trend: WrOverviewModule['trend'] }) {
  const data = trend.map(t => ({ d: t.date.slice(5), v: t.coverage, abnormal: t.abnormal, unchecked: t.unchecked }))
  if (!data.some(x => x.v !== null)) {
    return <Text type="secondary" style={{ fontSize: 12 }}>近 7 日無巡檢紀錄</Text>
  }
  return (
    <div style={{ width: '100%', height: 56 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <XAxis dataKey="d" hide />
          <YAxis domain={[0, 100]} hide />
          <RTooltip
            formatter={v => (v === null || v === undefined ? '—' : `${v}%`)}
            contentStyle={{ fontSize: 12 }}
          />
          <Line type="monotone" dataKey="v" stroke="#4BA8E8" strokeWidth={2} dot={{ r: 2 }} connectNulls={false} name="涵蓋率" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function ModuleCard({ m, onOpen }: { m: WrOverviewModule; onOpen: () => void }) {
  const meta = LEVEL_META[m.level]
  const t = m.today
  return (
    <Card
      size="small"
      hoverable
      onClick={onOpen}
      style={{ borderLeft: `4px solid ${meta.color}`, height: '100%' }}
      styles={{ body: { padding: 12 } }}
      title={
        <Space size={6} wrap>
          <Badge status={meta.badge} />
          <span>{m.label}</span>
          <Tag>{m.venue_label}</Tag>
        </Space>
      }
      extra={<RightOutlined style={{ color: '#888' }} />}
    >
      <div style={{ minHeight: 40, fontSize: 13, color: m.level === 'critical' ? '#c0392b' : undefined }}>
        {m.headline}
      </div>
      <Row gutter={8} style={{ marginTop: 8, textAlign: 'center' }}>
        <Col span={8}>
          <div style={{ fontSize: 20, fontWeight: 600, color: t.abnormal ? '#e74c3c' : '#1B3A5C' }}>{t.abnormal}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>異常</Text>
        </Col>
        <Col span={8}>
          <div style={{ fontSize: 20, fontWeight: 600, color: t.unchecked ? '#faad14' : '#1B3A5C' }}>{t.unchecked}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>未填</Text>
        </Col>
        <Col span={8}>
          <div style={{ fontSize: 20, fontWeight: 600, color: '#1B3A5C' }}>
            {t.coverage === null ? '—' : `${t.coverage}%`}
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>涵蓋率</Text>
        </Col>
      </Row>
      <div style={{ marginTop: 8 }}>
        <Tooltip title="近 7 日涵蓋率（已巡檢 ÷ 應巡檢）">
          <div><Sparkline trend={m.trend} /></div>
        </Tooltip>
      </div>
    </Card>
  )
}

export default function OverviewTab({ getContainer }: { getContainer?: () => HTMLElement }) {
  const [date, setDate] = useState<Dayjs>(dayjs())
  const [data, setData] = useState<WrOverview | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [refreshedAt, setRefreshedAt] = useState<Dayjs | null>(null)
  const [fresh, setFresh] = useState<LastUpdatedResult | null>(null)
  const [freshFailed, setFreshFailed] = useState(false)
  const [openKey, setOpenKey] = useState<string | null>(null)
  const [target, setTarget] = useState<AssetTarget | null>(null)

  const isToday = date.isSame(dayjs(), 'day')

  const load = useCallback(() => {
    setLoading(true)
    fetchWarRoomOverview(date.format('YYYY-MM-DD'))
      .then(d => { setData(d); setError(null); setRefreshedAt(dayjs()) })
      .catch(() => setError('連線失敗，無法取得最新資料'))
      .finally(() => setLoading(false))
    fetchLastUpdated(FRESH_SOURCES)
      .then(r => { setFresh(r); setFreshFailed(false) })
      .catch(() => setFreshFailed(true))
  }, [date])
  useEffect(() => { load() }, [load])

  // 今天：每 60 秒自動更新；頁面切到背景時不抓，回到前景時立即補抓
  useEffect(() => {
    if (!isToday) return
    const tick = () => { if (document.visibilityState === 'visible') load() }
    const t = window.setInterval(tick, AUTO_REFRESH_MS)
    document.addEventListener('visibilitychange', tick)
    return () => {
      window.clearInterval(t)
      document.removeEventListener('visibilitychange', tick)
    }
  }, [isToday, load])

  const lastWrite = fresh?.last_updated ? dayjs(fresh.last_updated) : null
  const staleMin = lastWrite && isToday ? dayjs().diff(lastWrite, 'minute') : null
  const isStale = staleMin !== null && staleMin > STALE_MINUTES

  const opened = data?.modules.find(m => m.module === openKey) ?? null
  const counts = data ? {
    critical: data.modules.filter(m => m.level === 'critical').length,
    warning: data.modules.filter(m => m.level === 'warning').length,
  } : null

  return (
    <div>
      <Space align="center" style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }} wrap>
        <Space wrap>
          <Space size={6}>
            <Button icon={<LeftOutlined />} aria-label="前一天" onClick={() => setDate(d => d.subtract(1, 'day'))} />
            <DatePicker value={date} allowClear={false} onChange={d => d && setDate(d)} style={{ width: 150 }} />
            <Button icon={<RightOutlined />} aria-label="後一天" disabled={!date.isBefore(dayjs(), 'day')}
                    onClick={() => setDate(d => d.add(1, 'day'))} />
            <Button onClick={() => setDate(dayjs())}>今天</Button>
          </Space>
          {data && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {data.is_today ? `即時；${data.deadline} 後仍未填即警告；每 60 秒自動更新` : '歷史日期（不自動更新）'}
              ｜畫面 {refreshedAt?.format('HH:mm:ss') ?? '—'}
              {lastWrite && `｜資料寫入 ${lastWrite.format('MM/DD HH:mm')}`}
              {freshFailed && '｜無法取得資料寫入時間'}
            </Text>
          )}
        </Space>
        <Space>
          {counts && (
            <>
              <Tag color="red">嚴重 {counts.critical}</Tag>
              <Tag color="orange">警告 {counts.warning}</Tag>
            </>
          )}
          <a onClick={load}><ReloadOutlined /> 重新整理</a>
        </Space>
      </Space>

      {error && (
        <Alert
          type="error" showIcon style={{ marginBottom: 12 }}
          message={data
            ? `${error}，目前顯示 ${refreshedAt?.format('HH:mm:ss')} 的資料，將於下次自動更新時重試`
            : `${error}，請稍後重新整理`}
        />
      )}
      {isStale && (
        <Alert
          type="warning" showIcon style={{ marginBottom: 12 }}
          message={`巡檢資料可能過期：資料庫最後寫入 ${lastWrite?.format('MM/DD HH:mm')}（${staleMin} 分鐘前），請確認 Ragic 同步排程`}
        />
      )}
      <Spin spinning={loading}>
        {data && data.modules.length === 0 && <Empty description="目前沒有巡檢模組" />}
        <Row gutter={[12, 12]}>
          {data?.modules.map(m => (
            <Col key={m.module} xs={24} sm={12} xl={8}>
              <ModuleCard m={m} onOpen={() => setOpenKey(m.module)} />
            </Col>
          ))}
        </Row>
      </Spin>

      <Drawer
        open={!!opened}
        width={560}
        onClose={() => setOpenKey(null)}
        getContainer={getContainer}
        title={opened && (
          <Space size={6} wrap>
            <Tag color="blue">值班總覽</Tag>
            <span>{opened.label}：{data?.date}</span>
          </Space>
        )}
      >
        {opened && (
          <>
            <div style={{ marginBottom: 12 }}>
              <Badge status={LEVEL_META[opened.level].badge} text={`${LEVEL_META[opened.level].text}｜${opened.headline}`} />
            </div>
            <Table<WrOverviewItem>
              size="small"
              rowKey={r => `${r.id}`}
              dataSource={opened.items}
              pagination={false}
              locale={{ emptyText: '今日沒有異常或未填的點位' }}
              onRow={r => ({ onClick: () => setTarget({ type: 'point', id: r.id, label: r.label }), style: { cursor: 'pointer' } })}
              columns={[
                { title: '樓層', dataIndex: 'floor_key', width: 70, render: (v: string) => v.toUpperCase() },
                { title: '點位', dataIndex: 'label' },
                { title: '群組', dataIndex: 'group_label', ellipsis: true },
                {
                  title: '狀態', dataIndex: 'status', width: 80,
                  render: (v: string) => <Tag color={STATUS_TEXT[v]?.color}>{STATUS_TEXT[v]?.text ?? v}</Tag>,
                },
              ]}
            />
            {opened.items_total > opened.items.length && (
              <Text type="secondary" style={{ fontSize: 12 }}>僅顯示前 {opened.items.length} 筆，共 {opened.items_total} 筆</Text>
            )}
          </>
        )}
      </Drawer>

      <AssetHistoryDrawer target={target} date={date.format('YYYY-MM-DD')} onClose={() => setTarget(null)} getContainer={getContainer} />
    </div>
  )
}
