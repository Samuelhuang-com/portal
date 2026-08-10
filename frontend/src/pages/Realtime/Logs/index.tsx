/**
 * 即時營運 — API 呼叫紀錄（/realtime/logs）
 *
 * 規格書：docs/SPEC_realtime_operations.md §8.1
 * 使用手冊：docs/MANUAL_realtime_operations.md §6
 *
 * ⚠️ **只記錄實際發出的呼叫，快取命中不會出現在這裡。**
 *    OHIP 按呼叫量計費，這張表的用途就是看真實用量 ——
 *    如果把快取命中也記進來，用量統計會失真。
 *
 * 本頁不呼叫任何 OHIP API（純讀本地 `ohip_call_log`），所以自己不會增加用量。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Col, Row, Space, Statistic, Table, Tag, Typography, message,
} from 'antd'
import { FileSearchOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import { fetchOhipCallLogs } from '@/api/realtime'
import type { OhipCallLogRow } from '@/types/realtime'
import { ACCENT, BRAND, EMPTY, GREEN, GREY, RED, fmtInt } from '@/pages/Opera/components/formatters'

const { Title, Text } = Typography

const PAGE_SIZE = 50

const RealtimeLogsPage: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState<OhipCallLogRow[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  const load = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const res = await fetchOhipCallLogs({ limit: PAGE_SIZE, offset: (p - 1) * PAGE_SIZE })
      setRows(res.items)
      setTotal(res.total)
      setPage(p)
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '載入 API 呼叫紀錄失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(1) }, [load])

  // 本頁只統計「目前這一頁」的資料 —— 標示清楚，避免被誤讀成全期統計
  const stats = useMemo(() => {
    const ok = rows.filter((r) => r.success).length
    const fail = rows.length - ok
    const elapsed = rows.filter((r) => r.elapsed_ms > 0).map((r) => r.elapsed_ms)
    const avg = elapsed.length
      ? Math.round(elapsed.reduce((a, b) => a + b, 0) / elapsed.length)
      : 0
    const today = new Date().toISOString().slice(0, 10)
    const todayCount = rows.filter((r) => (r.called_at || '').startsWith(today)).length
    return { ok, fail, avg, todayCount }
  }, [rows])

  const columns: ColumnsType<OhipCallLogRow> = [
    { title: '時間', dataIndex: 'called_at', width: 170, fixed: 'left',
      render: (v: string) => (v ? v.replace('T', ' ') : EMPTY) },
    { title: '結果', dataIndex: 'success', width: 90,
      render: (v: boolean, r) => (
        <Tag color={v ? 'green' : 'red'}>{v ? r.status_code : '失敗'}</Tag>
      ) },
    { title: '端點', dataIndex: 'endpoint', width: 320,
      render: (v: string) => <Text code style={{ fontSize: 11 }}>{v}</Text> },
    { title: '查詢區間', width: 190,
      render: (_, r) => (r.date_start ? `${r.date_start} ~ ${r.date_end}` : EMPTY) },
    { title: '耗時', dataIndex: 'elapsed_ms', width: 100, align: 'right',
      render: (v: number) => (v ? (
        <Text style={{ color: v > 5000 ? RED : v > 2000 ? ACCENT : GREY }}>{fmtInt(v)} ms</Text>
      ) : EMPTY) },
    { title: '觸發者', dataIndex: 'triggered_by', width: 200,
      render: (v: string) => v || <Text type="secondary">排程</Text> },
    { title: 'Request Id', dataIndex: 'request_id', width: 290,
      render: (v: string) => (v
        ? <Text copyable style={{ fontSize: 11 }}>{v}</Text>
        : EMPTY) },
    { title: '錯誤', dataIndex: 'error',
      render: (v: string) => (v
        ? <Text type="danger" style={{ fontSize: 11 }}>{v}</Text>
        : EMPTY) },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
        <Col>
          <Space direction="vertical" size={4}>
            <Title level={4} style={{ margin: 0, color: BRAND }}>API 呼叫紀錄</Title>
            <Text type="secondary" style={{ fontSize: 12 }}>
              每一次實際發出的 OPERA 查詢。本頁不呼叫 API，不會增加用量。
            </Text>
          </Space>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={() => load(page)} loading={loading}>
            重新整理
          </Button>
        </Col>
      </Row>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="快取命中不會出現在這裡"
        description={
          <span>
            若 5 分鐘內開了 10 次即時看板，這裡<Text strong>只會有 1 筆</Text> ——
            後面 9 次用的是快取，沒有真的呼叫 OPERA。
            這是刻意的：OHIP <Text strong>按呼叫次數計費</Text>，
            記錄快取命中會讓用量統計失真。
          </span>
        }
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col xs={12} sm={6}>
            <Statistic title="累計呼叫次數" value={total} valueStyle={{ color: BRAND }} />
            <Text type="secondary" style={{ fontSize: 11 }}>全部紀錄</Text>
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="今日呼叫" value={stats.todayCount} valueStyle={{ color: ACCENT }} />
            <Text type="secondary" style={{ fontSize: 11 }}>僅計本頁範圍</Text>
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="本頁成功 / 失敗"
                       value={`${stats.ok} / ${stats.fail}`}
                       valueStyle={{ color: stats.fail ? RED : GREEN }} />
          </Col>
          <Col xs={12} sm={6}>
            <Statistic title="本頁平均耗時" value={stats.avg} suffix="ms"
                       valueStyle={{ color: stats.avg > 3000 ? RED : BRAND }} />
            <Text type="secondary" style={{ fontSize: 11 }}>非同步營收約 3000 ms</Text>
          </Col>
        </Row>
      </Card>

      <Card size="small">
        <Table<OhipCallLogRow>
          size="small"
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          scroll={{ x: 1400 }}
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showSizeChanger: false,
            onChange: (p) => load(p),
            showTotal: (t) => `共 ${fmtInt(t)} 筆`,
          }}
        />
      </Card>
    </div>
  )
}

export default RealtimeLogsPage
