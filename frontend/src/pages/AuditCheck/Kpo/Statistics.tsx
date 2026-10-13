/**
 * 現場營運稽核 — 分數統計（財#1）
 * route: /audit-check/kpo/statistics     permissionKey: audit_check_view
 *
 * 2026-10-13 新增，比照系統建置稽核的「分數統計」（/audit-check/statistics）：
 *   - 分頁①「分數統計」：每家公司一個區塊，欄＝期別、列＝受稽部門；
 *     格子＝本期分數（大字）＋「N項符合 / M項選定」（小字，不顯示 %）；最後一列「查核完成」＝已查核項數/選定項數
 *   - 分頁②「缺失與建議清單」：不符合項＋查核備註（可選含未查核）
 *   - 篩選：公司／部門／期別（清單另有判定類型、關鍵字）；格子與清單列都可點擊進入該期期別頁
 *   - 匯出 Excel（整年度）
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button, Card, DatePicker, Empty, Input, Select, Space, Spin, Table, Tabs, Tag, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import { kpoStatisticsApi } from '@/api/auditKpo'
import type { KpoFlaggedRow, KpoStatBlock, KpoStatCell, KpoStatistics } from '@/api/auditKpo'
import { downloadFile } from '@/api/downloadFile'
import { scoreColor } from './Dashboard'

const { Title, Text } = Typography

interface StatRow { key: string; kind: 'dept' | 'completion'; name: string; cells: KpoStatCell[] }

const uniq = (a: string[]) => Array.from(new Set(a.filter(Boolean)))
const opts = (a: string[]) => a.map((v) => ({ value: v, label: v }))
function pickIdx<T>(arr: T[], keep: number[]): T[] { return keep.map((i) => arr[i]) }

export default function KpoStatisticsPage() {
  const navigate = useNavigate()
  const [year, setYear] = useState<number | undefined>(undefined)
  const [data, setData] = useState<KpoStatistics | null>(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await kpoStatisticsApi.get(year)
      setData(res.data)
      if (year === undefined) setYear(res.data.year)
    } catch {
      message.error('載入分數統計失敗')
    } finally {
      setLoading(false)
    }
  }, [year])
  useEffect(() => { load() }, [load])

  // ── 分數統計篩選（前端過濾）─────────────────────────────────────────────
  const [fCompany, setFCompany] = useState<number | undefined>()
  const [fDept, setFDept] = useState<string | undefined>()
  const [fPeriod, setFPeriod] = useState<string | undefined>()
  const allBlocks = data?.blocks ?? []
  const deptOpts = opts(uniq(allBlocks.filter((b) => !fCompany || b.company_id === fCompany)
    .flatMap((b) => b.rows.map((r) => r.name))).sort())
  const periodOpts = opts(uniq(allBlocks.flatMap((b) => b.periods)).sort())
  const shownBlocks = useMemo(() => allBlocks
    .filter((b) => !fCompany || b.company_id === fCompany)
    .map((b): KpoStatBlock | null => {
      const keep = b.periods.map((_, i) => i).filter((i) => !fPeriod || b.periods[i] === fPeriod)
      const rows = b.rows.filter((r) => !fDept || r.name === fDept).map((r) => ({ ...r, cells: pickIdx(r.cells, keep) }))
      if (!keep.length || (fDept && rows.length === 0)) return null
      return { ...b, rows, periods: pickIdx(b.periods, keep), completion: pickIdx(b.completion, keep) }
    })
    .filter((b): b is KpoStatBlock => b !== null), [allBlocks, fCompany, fDept, fPeriod])

  const openCell = (c?: KpoStatCell) => { if (c?.period_id) navigate(`/audit-check/kpo/periods/${c.period_id}`) }

  const renderBlock = (block: KpoStatBlock) => {
    const rows: StatRow[] = [
      ...block.rows.map((r) => ({ key: `d-${r.department_id}`, kind: 'dept' as const, name: r.name, cells: r.cells })),
      { key: 'completion', kind: 'completion' as const, name: '查核完成（已查核/選定）', cells: block.completion },
    ]
    const columns: ColumnsType<StatRow> = [
      {
        title: block.company_name, dataIndex: 'name', key: 'name', fixed: 'left', width: 200,
        render: (v: string, row) => <Text strong style={{ color: row.kind === 'dept' ? undefined : '#1B3A5C' }}>{v}</Text>,
      },
      ...block.periods.map((p, idx) => ({
        title: p, key: p, width: 160,
        onCell: (row: StatRow) => (row.cells[idx]?.period_id
          ? { onClick: () => openCell(row.cells[idx]), style: { cursor: 'pointer' } } : {}),
        render: (_: unknown, row: StatRow) => {
          const c = row.cells[idx]
          if (!c || (row.kind === 'dept' && !c.item_count)) return <Text type="secondary">{c?.label ?? '—'}</Text>
          if (row.kind === 'completion') {
            return (
              <div>
                <Text strong>{c.label}</Text>
                {c.score != null && <div style={{ fontSize: 12, color: '#64748b' }}>整期本期分數 {c.score}</div>}
              </div>
            )
          }
          const col = c.score == null ? undefined : scoreColor(c.score).fg
          return (
            <div>
              <Text strong style={{ color: col, fontSize: 15 }}>{c.score ?? '—'}</Text>
              <div style={{ fontSize: 12, color: '#64748b' }}>{c.label}</div>
            </div>
          )
        },
      })),
    ]
    return (
      <Card key={block.company_id} size="small" style={{ marginBottom: 16 }}>
        <Table<StatRow> size="small" bordered rowKey="key" columns={columns} dataSource={rows} pagination={false}
          scroll={{ x: 200 + block.periods.length * 160 }}
          rowClassName={(r) => (r.kind === 'dept' ? '' : 'kpo-stat-total-row')} />
      </Card>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0, color: '#1B3A5C' }}>現場營運稽核 — 分數統計</Title>
          <Text type="secondary">各部門逐期本期分數（得分÷滿分×100）與查核完成度</Text>
        </div>
        <Space>
          <DatePicker picker="year" allowClear={false} value={year ? dayjs(`${year}-01-01`) : undefined}
            onChange={(v) => { if (v) { setYear(v.year()); setFCompany(undefined); setFDept(undefined); setFPeriod(undefined) } }} />
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
          <Button icon={<DownloadOutlined />} disabled={!year}
            onClick={() => year && downloadFile(kpoStatisticsApi.exportUrl(year), `現場營運稽核-${year}分數統計.xlsx`)}>
            匯出 Excel
          </Button>
        </Space>
      </div>

      <Tabs items={[
        {
          key: 'scores', label: '分數統計',
          children: (
            <Spin spinning={loading}>
              <Space wrap style={{ marginBottom: 12 }}>
                <Select allowClear placeholder="全部公司" style={{ width: 150 }} value={fCompany}
                  options={allBlocks.map((b) => ({ value: b.company_id, label: b.company_name }))}
                  onChange={(v) => { setFCompany(v); setFDept(undefined) }} />
                <Select allowClear showSearch placeholder="全部部門" style={{ width: 150 }} value={fDept}
                  options={deptOpts} onChange={setFDept} />
                <Select allowClear placeholder="全部期別" style={{ width: 150 }} value={fPeriod}
                  options={periodOpts} onChange={setFPeriod} />
              </Space>
              {allBlocks.length === 0
                ? <Empty description={`${data?.year ?? ''} 年尚無稽核資料`} />
                : shownBlocks.length === 0
                  ? <Empty description="沒有符合篩選條件的資料" />
                  : shownBlocks.map(renderBlock)}
            </Spin>
          ),
        },
        { key: 'flagged', label: '缺失與建議清單', children: year ? <FlaggedTab year={year} /> : null },
      ]} />
      <style>{`.kpo-stat-total-row > td { background: #fafafa !important; }`}</style>
    </div>
  )
}

// ── 缺失與建議清單 ──────────────────────────────────────────────────────────
function FlaggedTab({ year }: { year: number }) {
  const navigate = useNavigate()
  const [rows, setRows] = useState<KpoFlaggedRow[]>([])
  const [loading, setLoading] = useState(false)
  const [includePending, setIncludePending] = useState(false)
  const [fCompany, setFCompany] = useState<string | undefined>()
  const [fDept, setFDept] = useState<string | undefined>()
  const [fPeriod, setFPeriod] = useState<string | undefined>()
  const [fResults, setFResults] = useState<string[]>([])
  const [kw, setKw] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows((await kpoStatisticsApi.flagged(year, includePending)).data)
    } catch {
      message.error('載入清單失敗')
    } finally {
      setLoading(false)
    }
  }, [year, includePending])
  useEffect(() => { load() }, [load])

  const shown = useMemo(() => {
    const k = kw.trim().toLowerCase()
    return rows.filter((r) =>
      (!fCompany || r.company_name === fCompany)
      && (!fDept || r.department_name === fDept)
      && (!fPeriod || r.period === fPeriod)
      && (fResults.length === 0 || fResults.includes(r.result_label))
      && (!k || `${r.item_no ?? ''} ${r.item_name} ${r.remark}`.toLowerCase().includes(k)))
  }, [rows, fCompany, fDept, fPeriod, fResults, kw])

  const columns: ColumnsType<KpoFlaggedRow> = [
    { title: '期別', dataIndex: 'period', width: 90 },
    { title: '公司', dataIndex: 'company_name', width: 100 },
    { title: '部門', dataIndex: 'department_name', width: 110 },
    {
      title: '稽核項目', key: 'item', width: 280,
      render: (_: unknown, r) => (
        <div style={{ whiteSpace: 'pre-wrap' }}>
          {r.is_key && <span style={{ color: '#faad14' }}>★ </span>}{r.item_no != null ? `${r.item_no}. ` : ''}{r.item_name}
        </div>
      ),
    },
    {
      title: '判定', dataIndex: 'result_label', width: 90,
      render: (v: string) => <Tag color={v === '不符合' ? 'red' : 'default'}>{v}</Tag>,
    },
    { title: '查核備註', dataIndex: 'remark', render: (v: string) => <div style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{v || '—'}</div> },
  ]

  return (
    <div>
      <Space wrap style={{ marginBottom: 12 }}>
        <Select value={includePending ? 'all' : 'fail'} style={{ width: 180 }}
          onChange={(v) => setIncludePending(v === 'all')}
          options={[{ value: 'fail', label: '只看不符合' }, { value: 'all', label: '不符合＋未查核' }]} />
        <Select allowClear placeholder="全部公司" style={{ width: 130 }} value={fCompany}
          options={opts(uniq(rows.map((r) => r.company_name)).sort())} onChange={(v) => { setFCompany(v); setFDept(undefined) }} />
        <Select allowClear showSearch placeholder="全部部門" style={{ width: 130 }} value={fDept}
          options={opts(uniq(rows.filter((r) => !fCompany || r.company_name === fCompany).map((r) => r.department_name)).sort())}
          onChange={setFDept} />
        <Select allowClear placeholder="全部期別" style={{ width: 120 }} value={fPeriod}
          options={opts(uniq(rows.map((r) => r.period)).sort())} onChange={setFPeriod} />
        <Select mode="multiple" allowClear maxTagCount="responsive" placeholder="判定（可多選）" style={{ width: 180 }}
          value={fResults} options={opts(uniq(rows.map((r) => r.result_label)))} onChange={setFResults} />
        <Input.Search allowClear placeholder="搜尋項目／備註" style={{ width: 200 }} onSearch={setKw}
          onChange={(e) => { if (!e.target.value) setKw('') }} />
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重整</Button>
        <Text type="secondary">共 {shown.length} 筆</Text>
      </Space>
      <Table<KpoFlaggedRow> size="small" bordered rowKey="line_id" loading={loading} columns={columns} dataSource={shown}
        onRow={(r) => ({
          onClick: () => navigate(`/audit-check/kpo/periods/${r.period_id}?line=${r.line_id}`),
          style: { cursor: 'pointer' },
        })}
        pagination={{ pageSize: 30, showSizeChanger: true }} scroll={{ x: 900 }} />
    </div>
  )
}
