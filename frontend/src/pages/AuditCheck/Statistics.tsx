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
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Button, Card, DatePicker, Empty, Input, Select, Space, Spin, Table, Tabs, Tag, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useNavigate } from 'react-router-dom'

import { statisticsApi } from '@/api/auditCheck'
import type { FlaggedRow, Statistics, StatisticsBlock, StatisticsCell } from '@/api/auditCheck'
import { downloadFile } from '@/api/downloadFile'

const { Title, Text, Paragraph } = Typography

interface StatRow {
  key: string
  kind: 'header-time' | 'header-items' | 'dept' | 'completion'
  name: string
  cells: StatisticsCell[]
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

/** 2026-10-13：分數以「分子/分母」呈現，不轉百分比、不顯示 0.33 小數。
 *  部門格 label＝「N項 / P項達標」→ P/N；完成率 label＝「3*3-1=8　8/9 = 88.9%」→ 8/9，並去掉百分比。 */
function fractionOf(label: string): string | null {
  const m1 = label.match(/(\d+)項\s*\/\s*(\d+)項達標/)
  if (m1) return `${m1[2]}/${m1[1]}`
  const m2 = label.match(/(\d+)\s*\/\s*(\d+)/)
  return m2 ? `${m2[1]}/${m2[2]}` : null
}
const stripPct = (label: string) => label.replace(/\s*=\s*[\d.]+%\s*$/, '')

const uniq = (a: string[]) => Array.from(new Set(a.filter(Boolean)))
const opts = (a: string[]) => a.map((v) => ({ value: v, label: v }))
function pickIdx<T>(arr: T[], keep: number[]): T[] { return keep.map((i) => arr[i]) }

function scoreColor(score: number | null): string | undefined {
  if (score == null) return undefined
  return score >= 1 ? '#52c41a' : '#cf1322'
}

export default function AuditStatisticsPage() {
  const navigate = useNavigate()
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

  // 2026-10-13：分數統計篩選（公司／部門／期別）；前端過濾，不重打 API
  const [fCompany, setFCompany] = useState<number | undefined>()
  const [fDept, setFDept] = useState<string | undefined>()
  const [fPeriod, setFPeriod] = useState<string | undefined>()
  const allBlocks = data?.blocks ?? []
  const companyOpts = allBlocks.map((b) => ({ value: b.company_id, label: b.company_name }))
  const deptOpts = opts(uniq(allBlocks.filter((b) => !fCompany || b.company_id === fCompany).flatMap((b) => b.rows.map((r) => r.name))).sort())
  const periodOpts = opts(uniq(allBlocks.flatMap((b) => b.periods)).sort())
  const shownBlocks = useMemo(() => allBlocks
    .filter((b) => !fCompany || b.company_id === fCompany)
    .map((b): StatisticsBlock | null => {
      const keep = b.periods.map((_, i) => i).filter((i) => !fPeriod || b.periods[i] === fPeriod)
      const rows = b.rows.filter((r) => !fDept || r.name === fDept).map((r) => ({ ...r, cells: pickIdx(r.cells, keep) }))
      if (!keep.length || (fDept && rows.length === 0)) return null
      return {
        ...b, rows,
        periods: pickIdx(b.periods, keep), audited_labels: pickIdx(b.audited_labels, keep),
        major_items: pickIdx(b.major_items, keep), completion: pickIdx(b.completion, keep),
      }
    })
    .filter((b): b is StatisticsBlock => b !== null), [allBlocks, fCompany, fDept, fPeriod])

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
        // 2026-10-13：每個期別欄的格子（含稽核時間／項目／完成率）都可點擊，進入該期稽核單；部門格帶 ?dept=
        onCell: (row: StatRow) => {
          const sheetId = row.cells[idx]?.sheet_id ?? block.completion[idx]?.sheet_id
          if (!sheetId) return {}
          const dept = row.kind === 'dept' ? row.cells[idx]?.sheet_department_id : null
          return {
            onClick: () => navigate(`/audit-check/sheets/${sheetId}${dept ? `?dept=${dept}` : ''}`),
            style: { cursor: 'pointer' },
          }
        },
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
                {fractionOf(c.label) ?? c.score.toFixed(2)}
              </Text>
              <div style={{ fontSize: 12, color: '#64748b' }}>{stripPct(c.label)}</div>
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
                <Space wrap style={{ marginBottom: 12 }}>
                  <Select allowClear placeholder="全部公司" style={{ width: 150 }} value={fCompany}
                    options={companyOpts} onChange={(v) => { setFCompany(v); setFDept(undefined) }} />
                  <Select allowClear showSearch placeholder="全部部門" style={{ width: 150 }} value={fDept}
                    options={deptOpts} onChange={setFDept} />
                  <Select allowClear placeholder="全部期別" style={{ width: 150 }} value={fPeriod}
                    options={periodOpts} onChange={setFPeriod} />
                </Space>
                {!data || data.blocks.length === 0
                  ? <Empty description={`${year} 年尚無稽核資料`} />
                  : shownBlocks.length === 0
                    ? <Empty description="沒有符合篩選條件的資料" />
                    : shownBlocks.map(renderBlock)}
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
  const navigate = useNavigate()
  const [rows, setRows] = useState<FlaggedRow[]>([])
  const [loading, setLoading] = useState(false)
  const [onlyFailing, setOnlyFailing] = useState(false)
  // 2026-10-13：公司／部門／期別／判定類型／關鍵字（前端過濾）
  const [fCompany, setFCompany] = useState<string | undefined>()
  const [fDept, setFDept] = useState<string | undefined>()
  const [fPeriod, setFPeriod] = useState<string | undefined>()
  const [fResults, setFResults] = useState<string[]>([])
  const [kw, setKw] = useState('')

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

  const shown = useMemo(() => {
    const k = kw.trim().toLowerCase()
    return rows.filter((r) =>
      (!fCompany || r.company_name === fCompany)
      && (!fDept || r.department_name === fDept)
      && (!fPeriod || r.period === fPeriod)
      && (fResults.length === 0 || fResults.includes(r.result_label))
      && (!k || `${r.display_no} ${r.item_name} ${r.comment}`.toLowerCase().includes(k)))
  }, [rows, fCompany, fDept, fPeriod, fResults, kw])

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
      <Space wrap style={{ marginBottom: 12 }}>
        <Select
          value={onlyFailing ? 'failing' : 'all'}
          onChange={(v) => setOnlyFailing(v === 'failing')}
          style={{ width: 200 }}
          options={[
            { value: 'all', label: '全部（缺失 + 建議）' },
            { value: 'failing', label: '只看未達標' },
          ]}
        />
        <Select allowClear placeholder="全部公司" style={{ width: 130 }} value={fCompany}
          options={opts(uniq(rows.map((r) => r.company_name)).sort())} onChange={setFCompany} />
        <Select allowClear showSearch placeholder="全部部門" style={{ width: 130 }} value={fDept}
          options={opts(uniq(rows.filter((r) => !fCompany || r.company_name === fCompany).map((r) => r.department_name)).sort())} onChange={setFDept} />
        <Select allowClear placeholder="全部期別" style={{ width: 120 }} value={fPeriod}
          options={opts(uniq(rows.map((r) => r.period)).sort())} onChange={setFPeriod} />
        <Select mode="multiple" allowClear maxTagCount="responsive" placeholder="判定類型（可多選）" style={{ width: 220 }} value={fResults}
          options={opts(uniq(rows.map((r) => r.result_label)))} onChange={setFResults} />
        <Input.Search allowClear placeholder="搜尋檢查項／內容" style={{ width: 200 }} onSearch={setKw}
          onChange={(e) => { if (!e.target.value) setKw('') }} />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
        <Text type="secondary">共 {shown.length} 筆</Text>
      </Space>
      <Table<FlaggedRow>
        size="small"
        bordered
        rowKey={(r, i) => `${r.period}-${r.department_id}-${r.display_no}-${i}`}
        loading={loading}
        columns={columns}
        dataSource={shown}
        // 2026-10-13：每一列可點擊，進入該稽核單並定位到該項目／部門（同 Dashboard 待改善清單）
        onRow={(r) => (r.sheet_id ? {
          onClick: () => navigate(`/audit-check/sheets/${r.sheet_id}?item=${r.sheet_item_id ?? ''}&dept=${r.sheet_department_id ?? ''}`),
          style: { cursor: 'pointer' },
        } : {})}
        pagination={{ pageSize: 30, showSizeChanger: true }}
        scroll={{ x: 900 }}
      />
    </div>
  )
}
