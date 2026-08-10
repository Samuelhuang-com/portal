/**
 * 即時營運 — 與「營運分析」比對（/realtime/compare）
 *
 * 規格書：docs/SPEC_realtime_operations.md §8.4
 * 使用手冊：docs/MANUAL_realtime_operations.md §5
 *
 * 目的：在把任何既有模組改成吃 API 之前，先證明**同一天、同一個欄位，兩邊數字一致**。
 *
 * ⚠️ 三個必須讓使用者看見的前提（畫面上都有寫）：
 *    ① API 是「現在看到的那一天」，TXT 是「匯出當下的那一天」——
 *       該日之後仍有異動的話，兩邊本來就會不同，**差異不等於錯誤**。
 *    ② 營收類欄位 API 不回傳，標示為「API 無此資料」，**不計入差異統計**。
 *    ③ TXT 側固定取 record_type=History；Forecast 是預測列，不是同一件事。
 *
 * ⚠️ 本頁每次查詢都會**實際呼叫 OHIP**（不走 5 分鐘快取）——比對是查證行為，
 *    必須拿當下真值。因此權限 `opera_api_compare` 與即時房況分開。
 */
import React, { useCallback, useState } from 'react'
import {
  Alert, Button, Card, Col, Descriptions, Empty, InputNumber, Row, Space,
  Statistic, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import {
  ApiOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  MinusCircleOutlined, SearchOutlined, StopOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

import { fetchApiTxtCompare } from '@/api/realtime'
import SourceBar from '../components/SourceBar'
import type { CompareField, CompareResult, CompareRow } from '@/types/realtime'
import {
  ACCENT, BRAND, EMPTY, GREEN, GREY, ORANGE, RED, fmtInt, fmtPct,
} from '@/pages/Opera/components/formatters'

const { Title, Text } = Typography

const STATUS_META: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
  match:           { color: GREEN,  text: '相符',        icon: <CheckCircleOutlined /> },
  diff:            { color: RED,    text: '不符',        icon: <ExclamationCircleOutlined /> },
  missing:         { color: GREY,   text: '一側缺值',    icon: <MinusCircleOutlined /> },
  api_unavailable: { color: ORANGE, text: 'API 無此資料', icon: <StopOutlined /> },
}

const RealtimeComparePage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<CompareResult | null>(null)
  const [error, setError] = useState('')

  const [daysBack, setDaysBack] = useState(30)
  const [daysAhead, setDaysAhead] = useState(0)
  const [tolerance, setTolerance] = useState(0)
  const [onlyDiff, setOnlyDiff] = useState(false)

  const run = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetchApiTxtCompare({
        days_back: daysBack, days_ahead: daysAhead, tolerance,
      })
      setData(res)
      if (res.configured && res.rows.length === 0) {
        message.info('查詢區間內兩邊都沒有資料')
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || '比對失敗')
    } finally {
      setLoading(false)
    }
  }, [daysBack, daysAhead, tolerance])

  const summary = data?.summary
  const rows = (data?.rows || []).filter((r) => (onlyDiff ? r.has_diff : true))

  // ── 展開後的逐欄明細 ──────────────────────────────────────────────────────
  const fieldColumns: ColumnsType<CompareField> = [
    { title: '欄位', dataIndex: 'label', width: 180 },
    {
      title: 'API', dataIndex: 'api', width: 110, align: 'right',
      render: (v: number | null, r) =>
        r.status === 'api_unavailable'
          ? <Text type="secondary" style={{ fontSize: 12 }}>—</Text>
          : (v === null ? EMPTY : fmtInt(v)),
    },
    {
      title: '上傳 TXT', dataIndex: 'txt', width: 110, align: 'right',
      render: (v: number | null) => (v === null ? EMPTY : fmtInt(v)),
    },
    {
      title: '差異', dataIndex: 'diff', width: 110, align: 'right',
      render: (v: number | null) => {
        if (v === null) return EMPTY
        if (v === 0) return <Text type="secondary">0</Text>
        return (
          <Text strong style={{ color: v > 0 ? ACCENT : RED }}>
            {v > 0 ? '+' : ''}{fmtInt(v)}
          </Text>
        )
      },
    },
    {
      title: '結果', dataIndex: 'status', width: 140,
      render: (v: string) => {
        const m = STATUS_META[v] || STATUS_META.missing
        return <Tag icon={m.icon} color={m.color}>{m.text}</Tag>
      },
    },
  ]

  const dayColumns: ColumnsType<CompareRow> = [
    { title: '日期', dataIndex: 'business_date', width: 130 },
    {
      title: '涵蓋', dataIndex: 'coverage', width: 130,
      render: (v: string) => {
        if (v === 'both') return <Tag color="default">兩邊都有</Tag>
        if (v === 'api_only') return <Tag color={ACCENT}>只有 API</Tag>
        return <Tag color={ORANGE}>只有 TXT</Tag>
      },
    },
    {
      title: '比對結果', width: 160,
      render: (_, r) => (r.has_diff
        ? <Tag icon={<ExclamationCircleOutlined />} color={RED}>有差異</Tag>
        : <Tag icon={<CheckCircleOutlined />} color={GREEN}>全部相符</Tag>),
    },
    {
      title: '差異欄位',
      render: (_, r) => {
        const diffs = r.fields.filter((f) => f.status === 'diff')
        if (!diffs.length) return <Text type="secondary">—</Text>
        return (
          <Space size={4} wrap>
            {diffs.map((f) => (
              <Tooltip key={f.label} title={`API ${fmtInt(f.api)}／TXT ${fmtInt(f.txt)}`}>
                <Tag color={RED}>{f.label} {f.diff! > 0 ? '+' : ''}{fmtInt(f.diff)}</Tag>
              </Tooltip>
            ))}
          </Space>
        )
      },
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size={4} style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0, color: BRAND }}>與營運分析比對</Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Phase 0-6 驗證工具：在把任何模組改成吃 API 之前，先證明同一天、同一欄位兩邊數字一致。
        </Text>
      </Space>

      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="讀這頁之前必須知道的三件事"
        description={
          <ol style={{ margin: 0, paddingInlineStart: 20 }}>
            <li>
              API 給的是「<Text strong>現在看到的那一天</Text>」，TXT 是「<Text strong>匯出當下的那一天</Text>」。
              若該日之後仍有異動（改房、取消、加房），兩邊本來就會不同——
              <Text strong>差異不等於錯誤</Text>，要看差異的方向與大小。
            </li>
            <li>
              營收類欄位 API <Text strong>不回傳</Text>，標示為「API 無此資料」，
              <Text strong>不計入差異統計</Text>，否則差異率會被灌爆而失去意義。
            </li>
            <li>
              TXT 側固定取 <Text code>record_type=History</Text>；
              Forecast 是預測列，與即時房況不是同一件事。
            </li>
          </ol>
        }
      />

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space wrap size={16}>
          <Space>
            <Text>往前</Text>
            <InputNumber min={0} max={61} value={daysBack} onChange={(v) => setDaysBack(v ?? 0)} style={{ width: 80 }} />
            <Text>天</Text>
          </Space>
          <Space>
            <Text>往後</Text>
            <InputNumber min={0} max={61} value={daysAhead} onChange={(v) => setDaysAhead(v ?? 0)} style={{ width: 80 }} />
            <Text>天</Text>
          </Space>
          <Space>
            <Tooltip title="差異在此範圍內視為相符。0 代表要求完全相同">
              <Text>容許誤差</Text>
            </Tooltip>
            <InputNumber min={0} value={tolerance} onChange={(v) => setTolerance(v ?? 0)} style={{ width: 90 }} />
          </Space>
          <Space>
            <Text>只看有差異的日期</Text>
            <Switch checked={onlyDiff} onChange={setOnlyDiff} />
          </Space>
          <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={run}>
            執行比對
          </Button>
          <Text type="secondary" style={{ fontSize: 12 }}>
            單次查詢上限 62 天（API 硬限制）；本頁不走快取，每次都實際呼叫
          </Text>
        </Space>
      </Card>

      {error && (
        <Alert type="error" showIcon message="比對失敗" description={error} style={{ marginBottom: 16 }} />
      )}

      {data && !data.configured && (
        <Alert
          type="info" showIcon
          message="OPERA API 尚未設定完成"
          description={<span>後端缺少：<Text code>{data.missing.join('、')}</Text></span>}
        />
      )}

      {data?.configured && summary && (
        <>
          <Card size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col xs={12} sm={8} md={4}>
                <Statistic
                  title="欄位相符率"
                  value={summary.match_rate !== null ? summary.match_rate * 100 : 0}
                  precision={1} suffix="%"
                  valueStyle={{ color: (summary.match_rate ?? 0) >= 0.99 ? GREEN : RED }}
                />
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {fmtInt(summary.fields_match)} / {fmtInt(summary.fields_match + summary.fields_diff)} 個可比對欄位
                </Text>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic title="有差異的日期" value={summary.days_with_diff}
                           valueStyle={{ color: summary.days_with_diff ? RED : GREEN }} />
                <Text type="secondary" style={{ fontSize: 11 }}>共 {summary.days_total} 天</Text>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic title="兩邊都有" value={summary.days_both} valueStyle={{ color: BRAND }} />
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic title="只有 API" value={summary.days_api_only}
                           valueStyle={{ color: summary.days_api_only ? ORANGE : GREY }} />
                <Text type="secondary" style={{ fontSize: 11 }}>TXT 還沒上傳</Text>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic title="只有 TXT" value={summary.days_txt_only}
                           valueStyle={{ color: summary.days_txt_only ? ORANGE : GREY }} />
                <Text type="secondary" style={{ fontSize: 11 }}>超出 API 查詢區間</Text>
              </Col>
              <Col xs={12} sm={8} md={4}>
                <Statistic title="API 無此資料" value={summary.fields_api_unavailable}
                           valueStyle={{ color: ORANGE }} />
                <Text type="secondary" style={{ fontSize: 11 }}>營收類，不計入相符率</Text>
              </Col>
            </Row>
          </Card>

          <Card
            size="small"
            title={
              <Space>
                <Text strong>逐日比對</Text>
                {data.range && <Tag>{data.range.start} ~ {data.range.end}</Tag>}
                {onlyDiff && <Tag color={RED}>只顯示有差異</Tag>}
              </Space>
            }
          >
            {rows.length === 0 ? (
              <Empty description={onlyDiff ? '沒有任何日期有差異' : '沒有資料'} />
            ) : (
              <Table<CompareRow>
                size="small"
                rowKey="business_date"
                columns={dayColumns}
                dataSource={rows}
                pagination={{ pageSize: 20, showSizeChanger: false }}
                expandable={{
                  expandedRowRender: (r) => (
                    <Table<CompareField>
                      size="small"
                      rowKey="label"
                      columns={fieldColumns}
                      dataSource={r.fields}
                      pagination={false}
                      rowClassName={(f) => (f.status === 'diff' ? 'compare-row-diff' : '')}
                    />
                  ),
                  rowExpandable: () => true,
                }}
              />
            )}

            <SourceBar source={data.source} hideCache />
          </Card>
        </>
      )}

      {!data && !loading && !error && (
        <Empty description="設定區間後按「執行比對」" />
      )}

      <style>{`.compare-row-diff > td { background: #fff5f5 !important; }`}</style>
    </div>
  )
}

export default RealtimeComparePage
