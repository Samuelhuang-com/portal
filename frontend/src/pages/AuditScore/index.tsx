/**
 * 稽核檢查統計（合併計分）
 * 公司 → 部門 → 年度合併達標率；稽核檢查與 KPO 各模組計算不變，合併＝達標項數合計 ÷ 子項數合計。
 */
import { useEffect, useState } from 'react'
import { Button, Card, Empty, InputNumber, Space, Table, Tooltip, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { exportAuditScore, getAuditScore, type AuditScoreBlock, type AuditScoreMonthly, type AuditScoreRow } from '@/api/auditScore'

const pct = (v: number | null) => (v == null ? '本年無' : `${(v * 100).toFixed(1)}%`)

// 每個月份一欄：直接顯示原模組的值（稽核：達標數/子項數；KPO：符合數/選定數）
function monthCell(items: AuditScoreMonthly[]) {
  if (!items.length) return <span style={{ color: '#999' }}>—</span>
  return (
    <div style={{ lineHeight: 1.6 }}>
      {items.map((m) => (
        <div key={`${m.source}-${m.source_sheet_id}`}>
          <span style={{ color: m.source === '稽核檢查' ? '#1B3A5C' : '#4BA8E8', fontWeight: 600 }}>
            {m.source === '稽核檢查' ? '稽核' : 'KPO'}
          </span>
          {` ${m.pass}/${m.sub}`}
          <span style={{ color: '#666' }}>
            {m.module_score == null
              ? '（本月無）'
              : m.source === '稽核檢查'
                ? `（${(m.module_score * 100).toFixed(1)}%）`
                : `（${m.module_score} 分）`}
          </span>
        </div>
      ))}
    </div>
  )
}

// 固定 1～12 月為欄；期別為 YYYY-MM，同月多期（YYYY-MM (2)）一併歸入該月
function monthColumns(year: number): ColumnsType<AuditScoreRow> {
  return Array.from({ length: 12 }, (_, i) => {
    const key = `${year}-${String(i + 1).padStart(2, '0')}`
    return {
      title: `${i + 1}月`,
      key: `m-${key}`,
      width: 130,
      align: 'center' as const,
      render: (_: unknown, r: AuditScoreRow) =>
        monthCell(r.monthly.filter((m) => m.period === key || m.period.startsWith(`${key} (`))),
    }
  })
}

const monthlyColumns: ColumnsType<AuditScoreMonthly> = [
  { title: '期別', dataIndex: 'period', width: 100 },
  { title: '來源模組', dataIndex: 'source', width: 110 },
  { title: '子項數（稽核）／選定數（KPO）', dataIndex: 'sub', width: 200, align: 'right' },
  { title: '達標數（稽核）／符合數（KPO）', dataIndex: 'pass', width: 200, align: 'right' },
  {
    title: '原模組分數', dataIndex: 'module_score', width: 130, align: 'right',
    render: (v: number | null, r) => {
      if (v == null) return '本月無'
      return r.source === '稽核檢查' ? `${(v * 100).toFixed(1)}%` : `${v} 分`
    },
  },
  { title: '原模組顯示', dataIndex: 'module_label', width: 200 },
  { title: '來源表單編號', dataIndex: 'source_sheet_id', width: 120, align: 'right' },
]

export default function AuditScorePage() {
  const [year, setYear] = useState<number>(new Date().getFullYear())
  const [blocks, setBlocks] = useState<AuditScoreBlock[]>([])
  const [loading, setLoading] = useState(false)

  const load = async (y: number) => {
    setLoading(true)
    try {
      const res = await getAuditScore(y)
      setBlocks(res.data.blocks)
    } catch {
      message.error('讀取稽核檢查統計失敗（需要「稽核檢查：查看」或「稽核檢查統計：查看」權限）')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(year) /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [year])

  const onExport = async () => {
    try {
      const res = await exportAuditScore(year)
      const url = URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `稽核檢查統計_${year}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      message.error('匯出失敗')
    }
  }

  const columns: ColumnsType<AuditScoreRow> = [
    { title: '部門', dataIndex: 'department', width: 140 },
    { title: '稽核子項數', dataIndex: 'audit_sub', width: 110, align: 'right' },
    { title: '稽核達標數', dataIndex: 'audit_pass', width: 110, align: 'right' },
    { title: 'KPO 選定項數', dataIndex: 'kpo_sub', width: 120, align: 'right' },
    { title: 'KPO 符合項數', dataIndex: 'kpo_pass', width: 120, align: 'right' },
    { title: '合計項數', dataIndex: 'total_sub', width: 110, align: 'right' },
    { title: '合計達標數', dataIndex: 'total_pass', width: 110, align: 'right' },
    {
      title: '合併達標率', dataIndex: 'rate', width: 130, align: 'right',
      render: (v: number | null, r) => (
        <Tooltip title={`稽核 ${r.audit_months} 個月、KPO ${r.kpo_months} 個月有資料（無資料的月份不計）`}>
          <span style={{ fontWeight: 600, color: v == null ? '#999' : '#1B3A5C' }}>{pct(v)}</span>
        </Tooltip>
      ),
    },
  ]

  return (
    <div>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space>
          <span>年度</span>
          <InputNumber value={year} min={2000} max={2100} onChange={(v) => v && setYear(v)} />
          <Button icon={<DownloadOutlined />} onClick={onExport}>匯出 Excel</Button>
        </Space>
      </Card>

      {!loading && blocks.length === 0 && <Empty description="本年度沒有可計分的資料" />}

      {blocks.map((blk) => (
        <Card key={blk.company_id} size="small" title={blk.company_name} style={{ marginBottom: 16 }}>
          <Table<AuditScoreRow>
            rowKey="department"
            size="small"
            loading={loading}
            columns={[columns[0], ...monthColumns(year), ...columns.slice(1)]}
            scroll={{ x: 1600 }}
            dataSource={blk.rows}
            pagination={false}
            expandable={{
              rowExpandable: (r) => r.monthly.length > 0,
              expandedRowRender: (r) => (
                <Table<AuditScoreMonthly>
                  rowKey={(m) => `${m.period}-${m.source}-${m.source_sheet_id}`}
                  size="small"
                  pagination={false}
                  columns={monthlyColumns}
                  dataSource={r.monthly}
                />
              ),
            }}
          />
        </Card>
      ))}
    </div>
  )
}
