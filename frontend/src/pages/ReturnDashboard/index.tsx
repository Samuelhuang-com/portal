import { useEffect, useMemo, useState } from 'react'
import { Button, Card, Drawer, Input, Select, Space, Spin, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DownOutlined, DownloadOutlined, FullscreenExitOutlined, FullscreenOutlined, LinkOutlined, RightOutlined } from '@ant-design/icons'
import {
  exportReturnMatrixExcel, fetchReturnDetail, fetchReturnMatrix,
  type DetailItem, type DetailResult, type MatrixResult, type MonthCell,
} from '@/api/returnDashboard'

const { Title, Text, Link } = Typography

const FORM_OPTIONS = [
  { value: '', label: '全部表單' },
  { value: 'purchase', label: '請購' },
  { value: 'claim', label: '請款' },
  { value: 'seal', label: '用印' },
]

const FORM_LABEL: Record<string, string> = { purchase: '請購', claim: '請款', seal: '用印' }

const OUTCOME_COLOR: Record<string, string> = {
  rejected: 'red', withdrawn: 'orange', approved: 'green', agreed: 'green', pending: 'blue', unknown: 'default',
}

const pct = (r: number | null) => (r == null ? '—' : `${(r * 100).toFixed(1)}%`)

interface FlatRow {
  key: string
  label: string
  kind: 'company' | 'dept' | 'total'
  company?: string
  dept?: string
  cells: MonthCell[]
  year_sent: number
  year_returned: number
  year_rate: number | null
}

interface DrawerState {
  title: string
  month: number
  kind: 'sent' | 'returned'
  company: string[]
  dept: string[]
}

export default function ReturnDashboardPage() {
  const thisYear = new Date().getFullYear()
  const years = [thisYear, thisYear - 1, thisYear - 2, thisYear - 3]
  const [year, setYear] = useState<number>(thisYear)
  const [formType, setFormType] = useState<string>('')
  const [companies, setCompanies] = useState<string[]>([])
  const [knownCompanies, setKnownCompanies] = useState<string[]>([])
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<MatrixResult | null>(null)

  const [drawer, setDrawer] = useState<DrawerState | null>(null)
  const [detail, setDetail] = useState<DetailResult | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [outcomeFilter, setOutcomeFilter] = useState<string>('')

  useEffect(() => {
    setLoading(true)
    fetchReturnMatrix(year, formType, companies)
      .then(res => {
        setData(res)
        // 公司選項：未篩選時記下全部公司，篩選後仍保留選項清單
        if (companies.length === 0) setKnownCompanies(res.blocks.map(b => b.company))
      })
      .catch(() => message.error('載入退件Dashboard失敗'))
      .finally(() => setLoading(false))
  }, [year, formType, companies])

  const rows = useMemo<FlatRow[]>(() => {
    if (!data) return []
    const out: FlatRow[] = []
    for (const b of data.blocks) {
      out.push({
        key: `c-${b.company}`, label: b.company, kind: 'company', company: b.company,
        cells: b.months, year_sent: b.year_sent, year_returned: b.year_returned, year_rate: b.year_rate,
      })
      if (collapsed.has(b.company)) continue
      for (const r of b.rows) {
        out.push({
          key: `d-${b.company}-${r.department}`, label: r.department, kind: 'dept',
          company: b.company, dept: r.department,
          cells: r.cells, year_sent: r.year_sent, year_returned: r.year_returned, year_rate: r.year_rate,
        })
      }
    }
    out.push({
      key: 'total', label: '合計', kind: 'total',
      cells: data.months, year_sent: data.year_sent, year_returned: data.year_returned, year_rate: data.year_rate,
    })
    return out
  }, [data, collapsed])

  const allCompanyNames = data ? data.blocks.map(b => b.company) : []

  async function onExport() {
    setExporting(true)
    try {
      const res = await exportReturnMatrixExcel(year, formType, companies)
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `退件Dashboard_${year}_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      message.error('匯出失敗（筆數可能超過上限，或沒有權限）')
    } finally {
      setExporting(false)
    }
  }
  const toggle = (c: string) => setCollapsed(prev => {
    const next = new Set(prev)
    if (next.has(c)) next.delete(c)
    else next.add(c)
    return next
  })

  async function openDetail(row: FlatRow, month: number, kind: 'sent' | 'returned') {
    const company = row.company ? [row.company] : companies
    const dept = row.dept ? [row.dept] : []
    const label = row.kind === 'total' ? '合計' : row.dept ? `${row.company}／${row.dept}` : row.company
    const title = `${label}　${year} 年 ${month} 月　${kind === 'sent' ? '送件明細' : '退件明細'}`
    setDrawer({ title, month, kind, company, dept })
    setKeyword('')
    setOutcomeFilter('')
    setDetail(null)
    setDetailLoading(true)
    try {
      setDetail(await fetchReturnDetail({ year, month, kind, company, dept, form_type: formType }))
    } catch {
      message.error('載入明細失敗')
    } finally {
      setDetailLoading(false)
    }
  }

  const filteredItems = useMemo<DetailItem[]>(() => {
    if (!detail) return []
    const kw = keyword.trim()
    return detail.items.filter(it => {
      if (outcomeFilter && it.outcome !== outcomeFilter) return false
      if (!kw) return true
      return [it.applicant, it.form_name, it.dept, it.company, it.rejection_note, it.rejection_approver, it.next_approver, it.ragic_record_id]
        .some(v => (v ?? '').includes(kw))
    })
  }, [detail, keyword, outcomeFilter])

  const outcomeOptions = useMemo(() => {
    const seen = new Map<string, string>()
    detail?.items.forEach(it => seen.set(it.outcome, it.outcome_label))
    return Array.from(seen, ([value, label]) => ({ value, label }))
  }, [detail])

  const CellView = ({ row, cell, month }: { row: FlatRow; cell: MonthCell | undefined; month: number }) => {
    if (!cell || cell.sent === 0) return <Text type="secondary">—</Text>
    return (
      <span>
        <Link onClick={() => openDetail(row, month, 'sent')}>{cell.sent}</Link>
        <Text type="secondary"> / </Text>
        {cell.returned > 0
          ? <Link style={{ color: '#cf1322' }} onClick={() => openDetail(row, month, 'returned')}>{cell.returned}</Link>
          : <Text type="secondary">0</Text>}
      </span>
    )
  }

  const columns: ColumnsType<FlatRow> = [
    {
      title: '公司 / 部門', dataIndex: 'label', fixed: 'left', width: 180,
      render: (v: string, r) => {
        if (r.kind === 'company') {
          const open = !collapsed.has(r.company!)
          return (
            <Button type="link" style={{ padding: 0, fontWeight: 600 }}
              icon={open ? <DownOutlined /> : <RightOutlined />}
              onClick={() => toggle(r.company!)}>
              {v}
            </Button>
          )
        }
        if (r.kind === 'total') return <Text strong>{v}</Text>
        return <span style={{ paddingLeft: 16 }}>{v}</span>
      },
    },
    ...Array.from({ length: 12 }, (_, i) => ({
      title: `${i + 1}月`,
      key: `m${i + 1}`,
      width: 90,
      align: 'center' as const,
      render: (_: unknown, r: FlatRow) => <CellView row={r} cell={r.cells[i]} month={i + 1} />,
    })),
    {
      title: '全年', key: 'year', width: 140, align: 'center', fixed: 'right',
      render: (_: unknown, r: FlatRow) => (
        <span>
          <Text strong>{r.year_sent}</Text>
          <Text type="secondary"> / </Text>
          <Text strong type={r.year_returned > 0 ? 'danger' : undefined}>{r.year_returned}</Text>
          <Tag style={{ marginLeft: 6 }}>{pct(r.year_rate)}</Tag>
        </span>
      ),
    },
  ]

  const detailColumns: ColumnsType<DetailItem> = [
    { title: '公司', dataIndex: 'company', width: 80 },
    { title: '部門', dataIndex: 'dept', width: 110 },
    { title: '表單', dataIndex: 'form_type', width: 70, render: (v: string) => FORM_LABEL[v] ?? v },
    { title: '表單名稱', dataIndex: 'form_name', width: 180, ellipsis: true },
    { title: '申請日期', dataIndex: 'apply_date', width: 110 },
    { title: '申請人', dataIndex: 'applicant', width: 100 },
    {
      title: '狀態', dataIndex: 'outcome_label', width: 100,
      render: (v: string, r) => <Tag color={OUTCOME_COLOR[r.outcome] ?? 'default'}>{v}</Tag>,
    },
    { title: '退件簽核人', dataIndex: 'rejection_approver', width: 110, render: (v: string | null) => v || '—' },
    { title: '退件原因', dataIndex: 'rejection_note', width: 260, ellipsis: true, render: (v: string | null) => v || '—' },
    { title: '下一位簽核人', dataIndex: 'next_approver', width: 150, ellipsis: true, render: (v: string | null) => v || '—' },
    { title: '金額', dataIndex: 'amount', width: 110, align: 'right',
      render: (v: number | null) => (v == null ? '—' : `$${v.toLocaleString()}`) },
    {
      title: 'Ragic', key: 'ragic', width: 130, fixed: 'right',
      render: (_: unknown, r) => r.ragic_url
        ? <a href={r.ragic_url} target="_blank" rel="noreferrer" style={{ color: '#4BA8E8' }}>
            <LinkOutlined /> 在 Ragic 查看 #{r.ragic_record_id}
          </a>
        : '—',
    },
  ]

  return (
    <div>
      <Title level={4} style={{ marginBottom: 4 }}>退件Dashboard</Title>
      <Text type="secondary">每格顯示「送件數 / 退件數」，點數字可看明細；退件 = 退件（拒絕）＋退簽。月份依申請日期計算。</Text>

      <Card style={{ margin: '16px 0' }} size="small">
        <Space wrap>
          <Select value={year} onChange={setYear} style={{ width: 120 }}
            options={years.map(y => ({ value: y, label: `${y} 年度` }))} />
          <Select value={formType} onChange={setFormType} style={{ width: 140 }} options={FORM_OPTIONS} />
          <Select mode="multiple" allowClear value={companies} onChange={setCompanies}
            placeholder="全部公司" style={{ minWidth: 220 }}
            options={knownCompanies.map(c => ({ value: c, label: c }))} />
          <Button onClick={() => setCollapsed(new Set())}>全部展開</Button>
          <Button onClick={() => setCollapsed(new Set(allCompanyNames))}>全部縮列</Button>
          <Button icon={<DownloadOutlined />} onClick={onExport} loading={exporting}>匯出 Excel</Button>
        </Space>
      </Card>

      <Spin spinning={loading}>
        <Table<FlatRow>
          rowKey="key"
          dataSource={rows}
          columns={columns}
          pagination={false}
          size="small"
          scroll={{ x: 1600 }}
          rowClassName={r => (r.kind === 'company' || r.kind === 'total' ? 'return-dashboard-company-row' : '')}
        />
      </Spin>

      <Drawer
        title={drawer?.title}
        open={!!drawer}
        onClose={() => setDrawer(null)}
        width={fullscreen ? '100vw' : 1200}
        destroyOnClose
        extra={
          <Button type="text"
            icon={fullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={() => setFullscreen(v => !v)}>
            {fullscreen ? '還原' : '全畫面'}
          </Button>
        }
      >
        <Space wrap style={{ marginBottom: 12 }}>
          <Input.Search allowClear placeholder="搜尋申請人、表單名稱、退件原因、簽核人、Ragic 編號"
            value={keyword} onChange={e => setKeyword(e.target.value)} style={{ width: 380 }} />
          <Select allowClear placeholder="狀態" value={outcomeFilter || undefined}
            onChange={v => setOutcomeFilter(v ?? '')} style={{ width: 140 }} options={outcomeOptions} />
          <Text type="secondary">
            共 {detail?.total ?? 0} 筆，目前顯示 {filteredItems.length} 筆
            {detail?.truncated ? `（僅載入前 2000 筆，請縮小篩選條件）` : ''}
          </Text>
        </Space>
        <Spin spinning={detailLoading}>
          <Table<DetailItem>
            rowKey="id"
            dataSource={filteredItems}
            columns={detailColumns}
            pagination={{ pageSize: 50, showSizeChanger: false }}
            size="small"
            scroll={{ x: 1600, y: fullscreen ? 'calc(100vh - 200px)' : undefined }}
          />
        </Spin>
      </Drawer>
    </div>
  )
}
