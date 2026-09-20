/**
 * 稽核檢查 — 分數統計
 * route: /audit-check/statistics     permissionKey: audit_check_view
 *
 * 對應 Excel 第三個 Sheet「財#3系統建置稽核-分數統計」：
 * 橫軸月份、縱軸部門，兩家公司各一張表；另加一個「缺失與建議清單」TAB，
 * 讓同一筆缺失可以跨月追蹤（Excel 做不到）。
 *
 * ⚠️ 年度選擇用原生 DatePicker picker="year"（§8.4 單期選擇，不用 StandardRangePicker）。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  Button, Card, DatePicker, Empty, Select, Space, Spin, Table, Tabs, Tag, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { statisticsApi } from '@/api/auditCheck'
import type { FlaggedRow, Statistics, StatisticsBlock } from '@/api/auditCheck'
import { downloadFile } from '@/api/downloadFile'

const { Title, Text, Paragraph } = Typography

interface StatRow {
  key: string
  kind: 'header-time' | 'header-items' | 'dept' | 'completion'
  name: string
  cells: { period: string; score: number | null; label: string }[]
  texts?: string[]
}

function buildRows(block: StatisticsBlock): StatRow[] {
  const rows: StatRow[] = [
    {
      key: 'time', kind: 'header-time', name: '稽核時間', cells: [],
      texts: block.audited_labels,
    },
    {
      key: 'items', kind: 'header-items', name: '稽核項目及抽查部門', cells: [],
      texts: block.major_items.map((m) => m.join('\n')),
    },
  ]
  block.rows.forEach((r) => {
    rows.push({ key: `d-${r.department_id}`, kind: 'dept', name: r.name, cells: r.cells })
  })
  rows.push({ key: 'completion', kind: 'completion', name: '稽核完成率', cells: block.completion })
  return rows
}

function scoreColor(score: number | null): string | undefined {
  if (score == null) return undefined
  return score >= 1 ? '#52c41a' : '#cf1322'
}

export default function AuditStatisticsPage() {
  const [year, setYear] = useState<number>(dayjs().year())
  const [data, setData] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await statisticsApi.get(year)
      setData(res.data)
    } catch {
      message.error('載入分數統計失敗')
    } finally {
      setLoading(false)
    }
  }, [year])

  useEffect(() => { load() }, [load])

  const renderBlock = (block: StatisticsBlock) => {
    const rows = buildRows(block)
    const columns: ColumnsType<StatRow> = [
      {
        title: block.company_name,
        dataIndex: 'name',
        key: 'name',
        fixed: 'left',
        width: 200,
        render: (v: string, row: StatRow) => (
          <Text strong style={{ color: row.kind === 'dept' ? undefined : '#1B3A5C' }}>{v}</Text>
        ),
      },
      ...block.periods.map((p, idx) => ({
        title: p,
        key: p,
        width: 200,
        render: (_: unknown, row: StatRow) => {
          if (row.kind === 'header-time' || row.kind === 'header-items') {
            return (
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>
                {row.texts?.[idx] || <Text type="secondary">—</Text>}
              </div>
            )
          }
          const c = row.cells[idx]
          if (!c) return <Text type="secondary">—</Text>
          if (c.score == null) return <Text type="secondary">{c.label}</Text>
          return (
            <div>
              <Text strong style={{ color: scoreColor(c.score) }}>
                {c.score.toFixed(2)}
              </Text>
              <div style={{ fontSize: 12, color: '#64748b' }}>{c.label}</div>
            </div>
          )
        },
      })),
    ]

    return (
      <Card key={block.company_id} size="small" style={{ marginBottom: 16 }}>
        <Table<StatRow>
          size="small"
          bordered
          rowKey="key"
          columns={columns}
          dataSource={rows}
          pagination={false}
          scroll={{ x: 200 + block.periods.length * 200 }}
          rowClassName={(row) => (row.kind === 'dept' ? '' : 'audit-stat-header-row')}
        />
      </Card>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>稽核檢查 — 分數統計</Title>
          <Text type="secondary">各部門逐月稽核分數與完成率</Text>
        </div>
        <Space>
          {/* §8.4：單一年度選擇，用原生 DatePicker */}
          <DatePicker
            picker="year"
            value={dayjs(`${year}-01-01`)}
            onChange={(v) => v && setYear(v.year())}
            allowClear={false}
          />
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => downloadFile(statisticsApi.exportUrl(year), `財#3系統建置稽核-${year}分數統計.xlsx`)}
          >
            匯出 Excel
          </Button>
        </Space>
      </div>

      <Tabs
        items={[
          {
            key: 'scores',
            label: '分數統計',
            children: (
              <Spin spinning={loading}>
                {data?.note && (
                  <Card size="small" style={{ marginBottom: 12, background: '#f6f9fc' }}>
                    <Paragraph style={{ marginBottom: 0, fontSize: 12, whiteSpace: 'pre-wrap' }}>
                      {data.note}
                    </Paragraph>
                  </Card>
                )}
                {!data || data.blocks.length === 0
                  ? <Empty description={`${year} 年尚無稽核資料`} />
                  : data.blocks.map(renderBlock)}
              </Spin>
            ),
          },
          {
            key: 'flagged',
            label: '缺失與建議清單',
            children: <FlaggedTab year={year} />,
          },
        ]}
      />

      <style>{`.audit-stat-header-row > td { background: #fafafa !important; }`}</style>
    </div>
  )
}

// ── 缺失與建議清單 ──────────────────────────────────────────────────────────
function FlaggedTab({ year }: { year: number }) {
  const [rows, setRows] = useState<FlaggedRow[]>([])
  const [loading, setLoading] = useState(false)
  const [onlyFailing, setOnlyFailing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await statisticsApi.flagged({ only_failing: onlyFailing })
      setRows(res.data.filter((r) => r.period.startsWith(String(year))))
    } catch {
      message.error('載入清單失敗')
    } finally {
      setLoading(false)
    }
  }, [onlyFailing, year])

  useEffect(() => { load() }, [load])

  const columns: ColumnsType<FlaggedRow> = [
    { title: '期別', dataIndex: 'period', key: 'period', width: 90 },
    { title: '公司', dataIndex: 'company_name', key: 'company_name', width: 100 },
    { title: '部門', dataIndex: 'department_name', key: 'department_name', width: 110 },
    {
      title: '檢查項', key: 'item', width: 220,
      render: (_: unknown, r: FlaggedRow) => `${r.display_no ? r.display_no + ' ' : ''}${r.item_name}`,
    },
    {
      title: '判定', dataIndex: 'result_label', key: 'result_label', width: 90,
      render: (v: string, r: FlaggedRow) => <Tag style={{ color: r.result_color }}>{v}</Tag>,
    },
    {
      title: '內容', dataIndex: 'comment', key: 'comment',
      render: (v: string) => <div style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{v}</div>,
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Select
          value={onlyFailing ? 'failing' : 'all'}
          onChange={(v) => setOnlyFailing(v === 'failing')}
          style={{ width: 200 }}
          options={[
            { value: 'all', label: '全部（缺失 + 建議）' },
            { value: 'failing', label: '只看未達標' },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
      </Space>
      <Table<FlaggedRow>
        size="small"
        bordered
        rowKey={(r, i) => `${r.period}-${r.department_id}-${r.display_no}-${i}`}
        loading={loading}
        columns={columns}
        dataSource={rows}
        pagination={{ pageSize: 30, showSizeChanger: true }}
        scroll={{ x: 900 }}
      />
    </div>
  )
}
