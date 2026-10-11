/**
 * 現場營運稽核 — 年度 Dashboard（期別清單表格上方）
 *
 * 2026-10-11 裁示：年度 × 公司 × 部門 × 檢查期別（月份）× 分數，以「熱度矩陣」呈現。
 *   - 列＝公司 › 部門（列出全部啟用部門，沒稽核的整列留白）；欄＝1~12 月；格子＝本期分數
 *   - 同月多期 → 格子取該月各期「本期分數」平均
 *   - 顏色：≥90 綠、70~89 黃、<70 紅（70 屬黃）；沒稽核留白，不顯示 0
 *   - 右側：稽核期別數、年度平均；點格子 → 單期直接進該期別，多期列出讓使用者選
 *   - 摘要卡：年度已稽核期別數／年度平均分數／最低分部門／年度受稽部門數（隨公司篩選連動）
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Col, Collapse, Empty, Popover, Row, Select, Space, Spin, Statistic, Tag, Typography, message } from 'antd'
import { BankOutlined } from '@ant-design/icons'

import { kpoDashboardApi } from '@/api/auditKpo'
import type { KpoDashboard, KpoDashMonth } from '@/api/auditKpo'

const { Text } = Typography

/** 分數顏色門檻：≥90 綠、70~89 黃、<70 紅 */
export function scoreColor(v: number): { bg: string; fg: string } {
  if (v >= 90) return { bg: '#d9f7be', fg: '#237804' }
  if (v >= 70) return { bg: '#fff1b8', fg: '#ad6800' }
  return { bg: '#ffccc7', fg: '#a8071a' }
}
const fmt = (v: number | null) => (v == null ? '—' : Number.isInteger(v) ? String(v) : v.toFixed(1))

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)
const CELL: React.CSSProperties = { padding: '4px 6px', textAlign: 'center', borderBottom: '1px solid #f0f0f0', whiteSpace: 'nowrap' }

export default function AuditKpoDashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState<KpoDashboard | null>(null)
  const [year, setYear] = useState<number | undefined>(undefined)
  const [companyId, setCompanyId] = useState<number | 'all'>('all')
  const [loading, setLoading] = useState(false)
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set())

  const load = useCallback(async (y?: number) => {
    setLoading(true)
    try {
      const res = await kpoDashboardApi.get(y)
      setData(res.data)
      setYear(res.data.year)
    } catch {
      message.error('載入 Dashboard 失敗')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { load() }, [load])

  const companies = useMemo(
    () => (data?.companies ?? []).filter((c) => companyId === 'all' || c.company_id === companyId),
    [data, companyId])

  // 摘要卡（隨公司篩選連動）
  const summary = useMemo(() => {
    const rows = companies.flatMap((c) => c.rows.map((r) => ({ ...r, company: c.company_name })))
    const periodIds = new Set<number>()
    rows.forEach((r) => Object.values(r.months).forEach((m) => m.periods.forEach((p) => periodIds.add(p.period_id))))
    const cnt = rows.reduce((a, r) => a + r.period_count, 0)
    const sum = rows.reduce((a, r) => a + r.score_sum, 0)
    const audited = rows.filter((r) => r.avg != null)
    const lowest = audited.length ? audited.reduce((a, b) => ((b.avg as number) < (a.avg as number) ? b : a)) : null
    return {
      periods: periodIds.size, avg: cnt ? Math.round((sum / cnt) * 10) / 10 : null,
      lowest, deptCount: rows.length,
    }
  }, [companies])

  const toggle = (id: number) => setCollapsed((prev) => {
    const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n
  })

  const cell = (m: KpoDashMonth | undefined) => {
    if (!m) return <td style={CELL} />
    const v = m.avg
    const c = v == null ? { bg: '#f5f5f5', fg: '#8c8c8c' } : scoreColor(v)
    const body = (
      <div style={{ background: c.bg, color: c.fg, borderRadius: 4, padding: '2px 0', minWidth: 44, fontWeight: 600, cursor: 'pointer' }}>
        {fmt(v)}{m.count > 1 && <sup style={{ fontWeight: 400, marginLeft: 2 }}>×{m.count}</sup>}
      </div>
    )
    if (m.periods.length === 1) {
      return <td style={CELL} onClick={() => navigate(`/audit-check/kpo/periods/${m.periods[0].period_id}`)}>{body}</td>
    }
    return (
      <td style={CELL}>
        <Popover title={`同月 ${m.periods.length} 期（取平均 ${fmt(v)}）`} trigger="click" content={
          <Space direction="vertical" size={4}>
            {m.periods.map((p) => (
              <a key={p.period_id} onClick={() => navigate(`/audit-check/kpo/periods/${p.period_id}`)}>
                {p.period}　期別 #{p.period_id}　本期分數 {fmt(p.score100)}
              </a>
            ))}
          </Space>}>
          {body}
        </Popover>
      </td>
    )
  }

  return (
    <Collapse
      style={{ marginBottom: 12 }} defaultActiveKey={['dash']}
      items={[{
        key: 'dash',
        label: <b>年度 Dashboard　{data ? `${data.year} 年` : ''}</b>,
        extra: (
          <Space onClick={(e) => e.stopPropagation()}>
            <Select size="small" style={{ width: 90 }} value={year} loading={loading}
              options={(data?.years ?? []).map((y) => ({ value: y, label: `${y} 年` }))}
              onChange={(y) => { setCompanyId('all'); load(y) }} />
            <Select size="small" style={{ width: 140 }} value={companyId} onChange={setCompanyId}
              options={[{ value: 'all', label: '全部公司' },
                ...(data?.companies ?? []).map((c) => ({ value: c.company_id, label: c.company_name }))]} />
          </Space>),
        children: (
          <Spin spinning={loading}>
            <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
              <Col xs={12} md={6}><Card size="small"><Statistic title="年度已稽核期別數" value={summary.periods} /></Card></Col>
              <Col xs={12} md={6}><Card size="small"><Statistic title="年度平均分數" value={fmt(summary.avg)} /></Card></Col>
              <Col xs={12} md={6}>
                <Card size="small">
                  <Statistic title="最低分部門" value={summary.lowest ? fmt(summary.lowest.avg) : '—'}
                    valueStyle={summary.lowest ? { color: scoreColor(summary.lowest.avg as number).fg } : undefined}
                    suffix={summary.lowest ? <Text type="secondary" style={{ fontSize: 12 }}>{summary.lowest.company}｜{summary.lowest.department_name}</Text> : undefined} />
                </Card>
              </Col>
              <Col xs={12} md={6}><Card size="small"><Statistic title="年度受稽部門數" value={summary.deptCount} suffix={<Text type="secondary" style={{ fontSize: 12 }}>列</Text>} /></Card></Col>
            </Row>

            {companies.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`${data?.year ?? ''} 年尚無公司別稽核單`} />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 900, fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: '#fafafa' }}>
                      <th style={{ ...CELL, textAlign: 'left', position: 'sticky', left: 0, background: '#fafafa', minWidth: 150 }}>公司 › 部門</th>
                      {MONTHS.map((m) => <th key={m} style={CELL}>{m} 月</th>)}
                      <th style={CELL}>稽核期別數</th>
                      <th style={CELL}>年度平均</th>
                    </tr>
                  </thead>
                  <tbody>
                    {companies.map((c) => (
                      <FragmentRows key={c.company_id} company={c} isCollapsed={collapsed.has(c.company_id)}
                        onToggle={() => toggle(c.company_id)} cell={cell} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div style={{ marginTop: 8 }}>
              <Space size={8} wrap>
                <Text type="secondary" style={{ fontSize: 12 }}>格子＝本期分數（同月多期取平均，右上角 ×n 為期數；點格子開啟期別）</Text>
                <Tag style={{ background: '#d9f7be', color: '#237804', border: 0 }}>≥ 90</Tag>
                <Tag style={{ background: '#fff1b8', color: '#ad6800', border: 0 }}>70 ~ 89</Tag>
                <Tag style={{ background: '#ffccc7', color: '#a8071a', border: 0 }}>&lt; 70</Tag>
                <Text type="secondary" style={{ fontSize: 12 }}>留白＝該月未稽核</Text>
              </Space>
            </div>
          </Spin>),
      }]}
    />
  )
}

function FragmentRows(props: {
  company: KpoDashboard['companies'][number]; isCollapsed: boolean; onToggle: () => void
  cell: (m: KpoDashMonth | undefined) => React.ReactNode
}) {
  const { company: c, isCollapsed, onToggle, cell } = props
  const audited = c.rows.filter((r) => r.avg != null).length
  return (
    <>
      <tr onClick={onToggle} style={{ cursor: 'pointer', background: '#eef3f8' }}>
        <td colSpan={15} style={{ ...CELL, textAlign: 'left', fontWeight: 600, color: '#1B3A5C' }}>
          <BankOutlined /> {isCollapsed ? '▸' : '▾'} {c.company_name}
          <Text type="secondary" style={{ marginLeft: 8, fontWeight: 400, fontSize: 12 }}>已稽核 {audited} / {c.rows.length} 個部門</Text>
        </td>
      </tr>
      {!isCollapsed && c.rows.map((r) => (
        <tr key={r.department_id}>
          <td style={{ ...CELL, textAlign: 'left', position: 'sticky', left: 0, background: '#fff', paddingLeft: 24 }}>{r.department_name}</td>
          {MONTHS.map((m) => <FragmentCell key={m} node={cell(r.months[String(m)])} />)}
          <td style={CELL}>{r.period_count || ''}</td>
          <td style={{ ...CELL, fontWeight: 600, color: r.avg == null ? undefined : scoreColor(r.avg).fg }}>{r.avg == null ? '' : fmt(r.avg)}</td>
        </tr>
      ))}
    </>
  )
}

function FragmentCell({ node }: { node: React.ReactNode }) { return <>{node}</> }
