/**
 * 稽核總覽 Dashboard
 * route: /audit-check/dashboard     permissionKey: audit_check_view
 *
 * 2026-10-12 裁示：「財#3 系統建置稽核」與「財#1 現場營運稽核」整合成同一個 Dashboard。
 *   - 獨立頁、選單新增「Dashboard」（不取代 /audit-check 期別清單）
 *   - 兩種稽核分數「並列」（每個部門兩行）；不算綜合分
 *   - 年度 × 公司 › 部門 × 1~12 月熱度矩陣；顏色沿用 KPO：≥90 綠、70~89 黃、<70 紅
 *   - 摘要卡、月度趨勢、最低分前 5 名、待改善清單（財#3 缺失類判定＋財#1 不符合項）
 *   - 部門對應鍵＝公司別＋部門名稱（兩邊部門主檔不同）；對不上的部門自成一列
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card, Col, Empty, Popover, Radio, Row, Select, Space, Spin, Statistic, Table, Tag, Typography, message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { BankOutlined, ReloadOutlined } from '@ant-design/icons'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { overviewApi } from '@/api/auditCheck'
import type { AuditOverview, OverviewImprovement, OverviewLine, OverviewMonth, OverviewRow } from '@/api/auditCheck'
import { scoreColor } from './Kpo/Dashboard'

const { Title, Text } = Typography

type Kind = 'f3' | 'f1'
const KIND_META: Record<Kind, { label: string; short: string; color: string; tag: string }> = {
  f3: { label: '財#3 系統建置稽核', short: '財#3', color: '#1B3A5C', tag: 'blue' },
  f1: { label: '財#1 現場營運稽核', short: '財#1', color: '#d46b08', tag: 'orange' },
}
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)
const CELL: React.CSSProperties = { padding: '4px 6px', textAlign: 'center', borderBottom: '1px solid #f0f0f0', whiteSpace: 'nowrap' }
const fmt = (v: number | null | undefined) => (v == null ? '—' : Number.isInteger(v) ? String(v) : v.toFixed(1))

export default function AuditOverviewDashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState<AuditOverview | null>(null)
  const [year, setYear] = useState<number | undefined>(undefined)
  const [companyId, setCompanyId] = useState<number | 'all'>('all')
  const [kindFilter, setKindFilter] = useState<'all' | Kind>('all')
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)

  const load = useCallback(async (y?: number) => {
    setLoading(true)
    try {
      const res = await overviewApi.get(y)
      setData(res.data)
      setYear(res.data.year)
    } catch {
      message.error('載入 Dashboard 失敗')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => { load() }, [load])

  const kinds: Kind[] = kindFilter === 'all' ? ['f3', 'f1'] : [kindFilter]
  const rows = useMemo(
    () => (data?.rows ?? []).filter((r) => companyId === 'all' || r.company_id === companyId),
    [data, companyId])
  // 分數矩陣只列「有被稽核」的部門：目前顯示的稽核類型（財#3／財#1）全年都沒有分數者不出現（2026-10-12）
  const byCompany = useMemo(() => {
    const m = new Map<number, { name: string; rows: OverviewRow[] }>()
    rows.filter((r) => kinds.some((k) => r[k].avg != null)).forEach((r) => {
      if (!m.has(r.company_id)) m.set(r.company_id, { name: r.company_name, rows: [] })
      m.get(r.company_id)!.rows.push(r)
    })
    return Array.from(m.entries())
  }, [rows, kinds])

  // 摘要／趨勢／最低分隨公司篩選連動（前端依 rows 重算；財#1、財#3 各自計）
  const stat = useMemo(() => {
    const calc = (k: Kind) => {
      const aud = rows.filter((r) => r[k].avg != null)
      const ids = new Set<string>()
      aud.forEach((r) => Object.values(r[k].months).forEach((m) => m.items.forEach((i) => ids.add(i.label))))
      const monthAvg = aud.flatMap((r) => Object.values(r[k].months).map((m) => m.avg).filter((v): v is number => v != null))
      const low = aud.length ? aud.reduce((a, b) => ((b[k].avg as number) < (a[k].avg as number) ? b : a)) : null
      const trend = MONTHS.map((mo) => {
        const vals = aud.map((r) => r[k].months[String(mo)]?.avg).filter((v): v is number => v != null)
        return vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10 : null
      })
      const lowest5 = [...aud].sort((a, b) => (a[k].avg as number) - (b[k].avg as number)).slice(0, 5)
      return {
        periods: ids.size, depts: aud.length, trend, lowest5, low,
        avg: monthAvg.length ? Math.round((monthAvg.reduce((a, b) => a + b, 0) / monthAvg.length) * 10) / 10 : null,
      }
    }
    return { f3: calc('f3'), f1: calc('f1') }
  }, [rows])

  const improvements = useMemo(() => (data?.improvements ?? []).filter((i) =>
    (companyId === 'all' || data?.companies.find((c) => c.company_id === companyId)?.company_name === i.company_name)
    && (kindFilter === 'all' || i.type === kindFilter)), [data, companyId, kindFilter])

  const toggle = (id: number) => setCollapsed((prev) => {
    const n = new Set(prev); if (n.has(id)) n.delete(id); else n.add(id); return n
  })

  const openImprovement = (r: OverviewImprovement) => {
    if (r.type === 'f1' && r.period_id != null) {
      navigate(`/audit-check/kpo/periods/${r.period_id}${r.line_id != null ? `?line=${r.line_id}` : ''}`)
    } else if (r.type === 'f3' && r.sheet_id != null) {
      navigate(`/audit-check/sheets/${r.sheet_id}?item=${r.sheet_item_id ?? ''}&dept=${r.sheet_department_id ?? ''}`)
    }
  }

  const go = (k: Kind, id: number) => navigate(k === 'f3' ? `/audit-check/sheets/${id}` : `/audit-check/kpo/periods/${id}`)

  const cell = (k: Kind, m: OverviewMonth | undefined) => {
    if (!m) return <td style={CELL} />
    const v = m.avg
    const c = v == null ? { bg: '#f5f5f5', fg: '#8c8c8c' } : scoreColor(v)
    const body = (
      <div style={{ background: c.bg, color: c.fg, borderRadius: 4, padding: '2px 0', minWidth: 44, fontWeight: 600, cursor: 'pointer' }}>
        {fmt(v)}{m.count > 1 && <sup style={{ fontWeight: 400, marginLeft: 2 }}>×{m.count}</sup>}
      </div>
    )
    if (m.items.length === 1) return <td style={CELL} onClick={() => go(k, m.items[0].id)}>{body}</td>
    return (
      <td style={CELL}>
        <Popover title={`同月 ${m.items.length} 期（取平均 ${fmt(v)}）`} trigger="click" content={
          <Space direction="vertical" size={4}>
            {m.items.map((p) => (
              <a key={p.id} onClick={() => go(k, p.id)}>{p.label}　分數 {fmt(p.score)}</a>
            ))}
          </Space>}>
          {body}
        </Popover>
      </td>
    )
  }

  const lineCells = (k: Kind, ln: OverviewLine) => (
    <>
      {MONTHS.map((mo) => <FragmentCell key={mo} node={cell(k, ln.months[String(mo)])} />)}
      <td style={CELL}>{ln.count || ''}</td>
      <td style={{ ...CELL, fontWeight: 600, color: ln.avg == null ? undefined : scoreColor(ln.avg).fg }}>{ln.avg == null ? '' : fmt(ln.avg)}</td>
    </>
  )

  const trendData = MONTHS.map((mo, i) => ({ month: `${mo}月`, f3: stat.f3.trend[i], f1: stat.f1.trend[i] }))

  const impCols: ColumnsType<OverviewImprovement> = [
    { title: '類型', dataIndex: 'type', width: 80, render: (v: Kind) => <Tag color={KIND_META[v].tag}>{KIND_META[v].short}</Tag> },
    { title: '期別', dataIndex: 'period', width: 90 },
    { title: '公司', dataIndex: 'company_name', width: 90 },
    { title: '部門', dataIndex: 'department_name', width: 110 },
    { title: '稽核項目', dataIndex: 'item', width: 260, render: (v: string) => <div style={{ whiteSpace: 'pre-wrap' }}>{v}</div> },
    { title: '判定', dataIndex: 'result', width: 90, render: (v: string) => <Tag color="red">{v}</Tag> },
    { title: '評語／查核備註', dataIndex: 'content', render: (v: string) => <div style={{ whiteSpace: 'pre-wrap' }}>{v || '—'}</div> },
    { title: '', width: 70, render: (_, r) => <a onClick={(e) => { e.stopPropagation(); openImprovement(r) }}>明細</a> },
  ]

  const summaryCard = (k: Kind) => {
    const s = stat[k]
    return (
      <Card size="small" title={<Tag color={KIND_META[k].tag}>{KIND_META[k].label}</Tag>} style={{ height: '100%' }}>
        <Row gutter={[8, 8]}>
          <Col span={12}><Statistic title="年度已稽核期別" value={s.periods} /></Col>
          <Col span={12}><Statistic title="年度平均分數" value={fmt(s.avg)}
            valueStyle={s.avg != null ? { color: scoreColor(s.avg).fg } : undefined} /></Col>
          <Col span={12}><Statistic title="受稽部門數" value={s.depts} /></Col>
          <Col span={12}>
            <Statistic title="最低分單位" value={s.low ? fmt(s.low[k].avg) : '—'}
              valueStyle={s.low ? { color: scoreColor(s.low[k].avg as number).fg } : undefined} />
            {s.low && <Text type="secondary" style={{ fontSize: 12 }}>{s.low.company_name}｜{s.low.department_name}</Text>}
          </Col>
        </Row>
      </Card>
    )
  }

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }} wrap>
        <Title level={4} style={{ margin: 0 }}>稽核總覽 Dashboard　{data ? `${data.year} 年` : ''}</Title>
        <Space wrap>
          <Select style={{ width: 100 }} value={year} loading={loading}
            options={(data?.years ?? []).map((y) => ({ value: y, label: `${y} 年` }))}
            onChange={(y) => { setCompanyId('all'); load(y) }} />
          <Select style={{ width: 140 }} value={companyId} onChange={setCompanyId}
            options={[{ value: 'all', label: '全部公司' },
              ...(data?.companies ?? []).map((c) => ({ value: c.company_id, label: c.company_name }))]} />
          <Radio.Group value={kindFilter} onChange={(e) => setKindFilter(e.target.value)} optionType="button" buttonStyle="solid"
            options={[{ value: 'all', label: '全部' }, { value: 'f3', label: '財#3 系統建置' }, { value: 'f1', label: '財#1 現場營運' }]} />
          <a onClick={() => load(year)} title="重新整理"><ReloadOutlined /></a>
        </Space>
      </Space>

      <Spin spinning={loading}>
        <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
          {kinds.map((k) => <Col key={k} xs={24} md={kinds.length === 1 ? 24 : 10}>{summaryCard(k)}</Col>)}
          <Col xs={24} md={kinds.length === 1 ? 24 : 4}>
            <Card size="small" title="待改善" style={{ height: '100%' }}>
              <Statistic title="年度待改善項目" value={improvements.length} valueStyle={{ color: improvements.length ? '#cf1322' : undefined }} />
            </Card>
          </Col>
        </Row>

        <Card size="small" title="分數矩陣（公司 › 部門 × 月份）" style={{ marginBottom: 12 }}>
          {byCompany.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={`${data?.year ?? ''} 年尚無稽核資料`} />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 980, fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#fafafa' }}>
                    <th style={{ ...CELL, textAlign: 'left', position: 'sticky', left: 0, background: '#fafafa', minWidth: 190 }}>公司 › 部門</th>
                    {MONTHS.map((m) => <th key={m} style={CELL}>{m} 月</th>)}
                    <th style={CELL}>期別數</th>
                    <th style={CELL}>年度平均</th>
                  </tr>
                </thead>
                <tbody>
                  {byCompany.map(([cid, grp]) => (
                    <FragmentRows key={cid}>
                      <tr onClick={() => toggle(cid)} style={{ cursor: 'pointer', background: '#eef3f8' }}>
                        <td colSpan={15} style={{ ...CELL, textAlign: 'left', fontWeight: 600, color: '#1B3A5C' }}>
                          <BankOutlined /> {collapsed.has(cid) ? '▸' : '▾'} {grp.name}
                          <Text type="secondary" style={{ marginLeft: 8, fontWeight: 400, fontSize: 12 }}>{grp.rows.length} 個部門</Text>
                        </td>
                      </tr>
                      {!collapsed.has(cid) && grp.rows.map((r) => (
                        <FragmentRows key={`${cid}-${r.department_name}`}>
                          {kinds.map((k, idx) => (
                            <tr key={k} style={idx === kinds.length - 1 ? undefined : { background: '#fff' }}>
                              <td style={{ ...CELL, textAlign: 'left', position: 'sticky', left: 0, background: '#fff', paddingLeft: 24 }}>
                                {idx === 0 ? <b style={{ marginRight: 8 }}>{r.department_name}</b> : <span style={{ display: 'inline-block', width: 0 }} />}
                                <Tag color={KIND_META[k].tag} style={{ marginRight: 0 }}>{KIND_META[k].short}</Tag>
                              </td>
                              {lineCells(k, r[k])}
                            </tr>
                          ))}
                        </FragmentRows>
                      ))}
                    </FragmentRows>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div style={{ marginTop: 8 }}>
            <Space size={8} wrap>
              <Text type="secondary" style={{ fontSize: 12 }}>格子＝分數（同月多期取平均，×n 為期數；點格子開啟單據）</Text>
              <Tag style={{ background: '#d9f7be', color: '#237804', border: 0 }}>≥ 90</Tag>
              <Tag style={{ background: '#fff1b8', color: '#ad6800', border: 0 }}>70 ~ 89</Tag>
              <Tag style={{ background: '#ffccc7', color: '#a8071a', border: 0 }}>&lt; 70</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>留白＝該月未稽核；兩種稽核分數並列、不合計</Text>
            </Space>
          </div>
        </Card>

        <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
          <Col xs={24} lg={14}>
            <Card size="small" title="月度平均分數趨勢" style={{ height: '100%' }}>
              <div style={{ width: '100%', height: 260 }}>
                <ResponsiveContainer>
                  <LineChart data={trendData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip formatter={(v) => (v == null ? '—' : String(v))} />
                    <Legend />
                    {kinds.map((k) => (
                      <Line key={k} type="monotone" dataKey={k} name={KIND_META[k].label}
                        stroke={KIND_META[k].color} strokeWidth={2} connectNulls dot />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card size="small" title="最低分前 5 名（年度平均）" style={{ height: '100%' }}>
              <Space direction="vertical" style={{ width: '100%' }} size={10}>
                {kinds.map((k) => (
                  <div key={k}>
                    <Tag color={KIND_META[k].tag}>{KIND_META[k].label}</Tag>
                    {stat[k].lowest5.length === 0 ? <Text type="secondary">無資料</Text> : stat[k].lowest5.map((r, i) => (
                      <div key={`${r.company_id}-${r.department_name}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                        <span>{i + 1}. {r.company_name}｜{r.department_name}</span>
                        <b style={{ color: scoreColor(r[k].avg as number).fg }}>{fmt(r[k].avg)}</b>
                      </div>
                    ))}
                  </div>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>

        <Card size="small" title={`待改善清單（財#3 缺失類判定＋財#1 不符合項，點擊開啟該明細）　共 ${improvements.length} 筆`}>
          <Table<OverviewImprovement> size="small" rowKey={(r) => `${r.type}-${r.period}-${r.company_name}-${r.department_name}-${r.item}`}
            columns={impCols} dataSource={improvements} scroll={{ x: 900 }}
            onRow={(r) => ({ onClick: () => openImprovement(r), style: { cursor: 'pointer' } })}
            pagination={{ pageSize: 20, showSizeChanger: false }} />
        </Card>
      </Spin>
    </div>
  )
}

function FragmentRows({ children }: { children: React.ReactNode }) { return <>{children}</> }
function FragmentCell({ node }: { node: React.ReactNode }) { return <>{node}</> }
