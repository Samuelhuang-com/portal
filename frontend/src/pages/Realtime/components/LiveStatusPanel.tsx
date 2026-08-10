/**
 * ★ OPERA 即時房況面板（OHIP API）
 *
 * 規劃文件：docs/OHIP_INTEGRATION.md
 *
 * ⚠️ 與 Dashboard 其他區塊的資料**來源不同、時點不同**：
 *      本面板  → 直接打 OPERA Cloud API，是「此刻」的房況
 *      其他區塊 → 人工上傳的 TXT 落地資料，會落後現實數天
 *    因此本面板一律以獨立卡片呈現，並在標題列與底部**明確標示 API 執行資料**，
 *    避免使用者誤以為整頁數字同一時點。
 *
 * ⚠️ 本面板**沒有** ADR / RevPAR / 營收 —— 2026-08-06 實測確認 OHIP 的
 *    getInventoryStatistics 不回傳營收類欄位（規劃文件 §4.3）。營收面仍看下方區塊。
 *
 * ⚠️ API 給的是「現在看到的那一天」，不是「那一天當時的樣子」，
 *    所以做不了 pickup / booking pace。本面板不宣稱有那個能力。
 */
import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Empty, Modal, Row, Space, Spin,
  Statistic, Table, Tabs, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  ApiOutlined, ClockCircleOutlined, DatabaseOutlined, FileSearchOutlined,
  ReloadOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import { fetchLiveStatus, fetchOhipCallLogs } from '@/api/realtime'
import SourceBar from './SourceBar'
import type {
  LiveDayRow, LiveStatusResult, OhipCallLogRow,
} from '@/types/realtime'
import { ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED, fmtInt, fmtPct } from '@/pages/Opera/components/formatters'

const { Text } = Typography

/** 住房率的色階：僅視覺提示，不代表任何營運門檻 */
function occColor(occ: number | null): string {
  if (occ === null || occ === undefined) return GREY
  if (occ >= 0.8) return GREEN
  if (occ >= 0.5) return ACCENT
  if (occ >= 0.3) return ORANGE
  return RED
}

function weekdayLabel(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return ['日', '一', '二', '三', '四', '五', '六'][d.getDay()] ?? ''
}

const LiveStatusPanel: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [data, setData] = useState<LiveStatusResult | null>(null)
  const [error, setError] = useState<string>('')

  const [logOpen, setLogOpen] = useState(false)
  const [logLoading, setLogLoading] = useState(false)
  const [logs, setLogs] = useState<OhipCallLogRow[]>([])
  const [logTotal, setLogTotal] = useState(0)

  const load = useCallback(async (force = false) => {
    if (force) setRefreshing(true)
    else setLoading(true)
    setError('')
    try {
      const res = await fetchLiveStatus({ force })
      setData(res)
    } catch (e: any) {
      setError(e?.response?.data?.detail || '無法取得 OPERA 即時房況')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const openLogs = useCallback(async () => {
    setLogOpen(true)
    setLogLoading(true)
    try {
      const res = await fetchOhipCallLogs({ limit: 100 })
      setLogs(res.items)
      setLogTotal(res.total)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入 API 呼叫紀錄失敗')
    } finally {
      setLogLoading(false)
    }
  }, [])

  // ── 尚未設定憑證 → 優雅降級，不擋住整個 Dashboard ──────────────────────────
  //
  // ⚠️ 這裡刻意用 `data.configured === false` 而不是 `!data.configured`：
  //    後端若因為任何原因沒帶到這個欄位（2026-08-05 就發生過：快取分支少了
  //    `configured` 與 `missing`），`!undefined` 會是 true 而誤入本分支，
  //    再讀 `data.missing.join()` 就丟 TypeError。本面板被營運分析 Dashboard
  //    直接嵌用，一丟例外整個 React 樹會被卸載 → **整頁空白**。
  //    「欄位沒帶到」應該當成未知而不是「未設定」，所以只認明確的 false。
  if (!loading && data && data.configured === false) {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Alert
          type="info"
          showIcon
          message="OPERA 即時房況尚未啟用"
          description={
            <span>
              後端缺少設定：
              <Text code>{data.missing?.length ? data.missing.join('、') : '（後端未回報明細）'}</Text>
              。設定方式見 <Text code>docs/OHIP_INTEGRATION.md</Text> §2。
              此區塊不影響下方既有的營運分析資料。
            </span>
          }
        />
      </Card>
    )
  }

  const today: LiveDayRow | undefined = data?.house?.[0]
  const src = data?.source

  // ── 逐日表格 ────────────────────────────────────────────────────────────────
  const dayColumns: ColumnsType<LiveDayRow> = [
    {
      title: '日期', dataIndex: 'business_date', width: 130, fixed: 'left',
      render: (v: string, r) => (
        <Space size={4}>
          <Text strong={r === today}>{v}</Text>
          <Tag color={r.is_weekend ? ORANGE : 'default'} style={{ marginInlineEnd: 0 }}>
            {weekdayLabel(v)}
          </Tag>
        </Space>
      ),
    },
    {
      title: '住房率', dataIndex: 'occupancy', width: 100, align: 'right',
      render: (v: number | null) => (
        <Text strong style={{ color: occColor(v) }}>{fmtPct(v)}</Text>
      ),
    },
    { title: '售出房', dataIndex: 'rooms_sold', width: 90, align: 'right',
      render: (v) => fmtInt(v) },
    { title: '可售房', dataIndex: 'available_rooms', width: 90, align: 'right',
      render: (v) => fmtInt(v) },
    { title: '總房數', dataIndex: 'inventory_rooms', width: 90, align: 'right',
      render: (v) => fmtInt(v) },
    { title: 'OOO', dataIndex: 'ooo_rooms', width: 80, align: 'right',
      render: (v: number | null) => (v ? <Text style={{ color: RED }}>{fmtInt(v)}</Text> : EMPTY) },
    { title: '到達', dataIndex: 'arrival_rooms', width: 80, align: 'right',
      render: (v) => fmtInt(v) },
    { title: '離店', dataIndex: 'departure_rooms', width: 80, align: 'right',
      render: (v) => fmtInt(v) },
    { title: '在店人數', dataIndex: 'people_in_house', width: 100, align: 'right',
      render: (v) => fmtInt(v) },
  ]

  const roomTypeColumns: ColumnsType<any> = [
    { title: '房型', dataIndex: 'label', width: 200, fixed: 'left' },
    ...(data?.house || []).map((d) => ({
      title: (
        <div style={{ textAlign: 'center' as const, lineHeight: 1.2 }}>
          <div>{d.business_date.slice(5)}</div>
          <Text type="secondary" style={{ fontSize: 11 }}>{weekdayLabel(d.business_date)}</Text>
        </div>
      ),
      dataIndex: d.business_date,
      width: 90,
      align: 'center' as const,
      render: (cell: { sold: number | null; avail: number | null } | undefined) => {
        if (!cell) return EMPTY
        return (
          <Tooltip title={`售出 ${fmtInt(cell.sold)}／可售 ${fmtInt(cell.avail)}`}>
            <Text>{fmtInt(cell.sold)}<Text type="secondary"> / {fmtInt(cell.avail)}</Text></Text>
          </Tooltip>
        )
      },
    })),
  ]

  const roomTypeRows = (data?.room_types || []).map((rt) => {
    const row: any = {
      key: rt.room_type,
      label: `${rt.room_type}　${rt.description}`,
    }
    rt.days.forEach((d) => {
      row[d.business_date] = { sold: d.rooms_sold, avail: d.available_rooms }
    })
    return row
  })

  // ── API 執行資料標示（使用者明確要求）──────────────────────────────────────
  const sourceBar = <SourceBar source={src} />

  return (
    <>
      <Card
        size="small"
        style={{ marginBottom: 16, borderColor: ACCENT }}
        title={
          <Space wrap>
            <ThunderboltOutlined style={{ color: ACCENT }} />
            <Text strong style={{ color: BRAND }}>OPERA 即時房況</Text>
            <Tag icon={<ApiOutlined />} color={ACCENT}>API 即時取數</Tag>
            {src?.fetched_at && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                <ClockCircleOutlined /> 資料時點 {src.fetched_at.replace('T', ' ')}
              </Text>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button size="small" icon={<FileSearchOutlined />} onClick={openLogs}>
              API 呼叫紀錄
            </Button>
            <Button
              size="small" type="primary" icon={<ReloadOutlined />}
              loading={refreshing} onClick={() => load(true)}
            >
              重新取數
            </Button>
          </Space>
        }
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="本區塊與下方分析的資料來源不同"
          description={
            <span>
              本區塊直接向 OPERA Cloud 取數，是<Text strong>此刻</Text>的房況；
              下方營收／ADR／RevPAR 來自<Text strong>人工上傳的報表</Text>，會落後數天。
              兩者<Text strong>時點不同，請勿混用比較</Text>。
              另外 OPERA 這支 API <Text strong>不提供營收類資料</Text>，故本區塊沒有 ADR／RevPAR。
            </span>
          }
        />

        <Spin spinning={loading}>
          {error ? (
            <Alert
              type="error" showIcon message="取得即時房況失敗" description={error}
              action={<Button size="small" onClick={() => load(true)}>重試</Button>}
            />
          ) : !today ? (
            <Empty description="沒有即時房況資料" />
          ) : (
            <>
              <Row gutter={16}>
                <Col xs={12} sm={12} md={6}>
                  <Statistic
                    title="今日住房率"
                    value={today.occupancy !== null ? today.occupancy * 100 : 0}
                    precision={1} suffix="%"
                    valueStyle={{ color: occColor(today.occupancy) }}
                  />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    售出 {fmtInt(today.rooms_sold)} ÷ 可售 {fmtInt((today.inventory_rooms ?? 0) - (today.ooo_rooms ?? 0))}
                  </Text>
                </Col>
                <Col xs={12} sm={12} md={6}>
                  <Statistic title="今日在店人數" value={today.people_in_house ?? 0}
                             valueStyle={{ color: BRAND }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>PeopleInHouse</Text>
                </Col>
                <Col xs={12} sm={12} md={6}>
                  <Statistic title="今日到達 / 離店"
                             value={`${fmtInt(today.arrival_rooms)} / ${fmtInt(today.departure_rooms)}`}
                             valueStyle={{ color: BRAND }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>房數</Text>
                </Col>
                <Col xs={12} sm={12} md={6}>
                  <Statistic title="今日可售房" value={today.available_rooms ?? 0}
                             valueStyle={{ color: today.available_rooms === 0 ? RED : BRAND }} />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    總房數 {fmtInt(today.inventory_rooms)}
                    {today.ooo_rooms ? `，OOO ${fmtInt(today.ooo_rooms)}` : ''}
                  </Text>
                </Col>
              </Row>

              <Tabs
                size="small"
                style={{ marginTop: 12 }}
                items={[
                  {
                    key: 'house',
                    label: '全館逐日',
                    children: (
                      <Table<LiveDayRow>
                        size="small"
                        rowKey="business_date"
                        columns={dayColumns}
                        dataSource={data?.house || []}
                        pagination={false}
                        scroll={{ x: 900 }}
                      />
                    ),
                  },
                  {
                    key: 'roomType',
                    label: `房型別（${data?.room_types?.length ?? 0}）`,
                    children: (
                      <>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          每格為「售出 / 可售」房數。房型粒度是上傳型報表沒有的資料。
                        </Text>
                        <Table
                          size="small"
                          rowKey="key"
                          columns={roomTypeColumns}
                          dataSource={roomTypeRows}
                          pagination={false}
                          scroll={{ x: 200 + (data?.house?.length ?? 0) * 90 }}
                          style={{ marginTop: 8 }}
                        />
                      </>
                    ),
                  },
                ]}
              />

              {sourceBar}
            </>
          )}
        </Spin>
      </Card>

      <Modal
        open={logOpen}
        onCancel={() => setLogOpen(false)}
        footer={null}
        width={1000}
        title={
          <Space>
            <FileSearchOutlined />
            <span>OHIP API 呼叫紀錄</span>
            <Tag>{logTotal} 筆</Tag>
          </Space>
        }
      >
        <Alert
          type="info" showIcon style={{ marginBottom: 12 }}
          message="只記錄實際發出的呼叫"
          description="快取命中不會出現在這裡 —— 那一次沒有真的呼叫 API。OHIP 按呼叫量計費，這張表用來看用量成長。"
        />
        <Table<OhipCallLogRow>
          size="small"
          rowKey="id"
          loading={logLoading}
          dataSource={logs}
          pagination={{ pageSize: 20, showSizeChanger: false }}
          scroll={{ x: 1100 }}
          columns={[
            { title: '時間', dataIndex: 'called_at', width: 170, fixed: 'left' },
            { title: '端點', dataIndex: 'endpoint', width: 300,
              render: (v: string) => <Text code style={{ fontSize: 11 }}>{v}</Text> },
            { title: '區間', width: 190,
              render: (_, r) => (r.date_start ? `${r.date_start} ~ ${r.date_end}` : EMPTY) },
            { title: '結果', dataIndex: 'success', width: 90,
              render: (v: boolean, r) => (
                <Tag color={v ? 'green' : 'red'}>{v ? r.status_code : '失敗'}</Tag>
              ) },
            { title: '耗時', dataIndex: 'elapsed_ms', width: 90, align: 'right',
              render: (v: number) => (v ? `${v} ms` : EMPTY) },
            { title: '觸發者', dataIndex: 'triggered_by', width: 180,
              render: (v: string) => v || <Text type="secondary">排程</Text> },
            { title: 'Request Id', dataIndex: 'request_id', width: 290,
              render: (v: string) => (v ? <Text copyable style={{ fontSize: 11 }}>{v}</Text> : EMPTY) },
            { title: '錯誤', dataIndex: 'error',
              render: (v: string) => (v ? <Text type="danger" style={{ fontSize: 11 }}>{v}</Text> : EMPTY) },
          ]}
        />
      </Modal>
    </>
  )
}

export default LiveStatusPanel
