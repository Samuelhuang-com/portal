/**
 * 商場工務報修 — 手機版 Dashboard（2026-09-13 新增）
 *
 * 路由：/m/luqun-repair       權限：luqun_repair_view（與桌面版同一個 key）
 * 資料：完全重用 fetchDashboard(year, month)，後端與 api/ 封裝都沒有任何修改。
 *
 * 與桌面版 /luqun-repair/dashboard 的關係：
 *   - 兩者打同一支 API、同一組參數 → **數字必須完全一致**，這是驗收基準。
 *   - 桌面版 pages/LuqunRepair/index.tsx 一行都沒有動。
 *
 * 手機版刻意捨棄的東西（不是漏做）：
 *   - Excel 匯出、柏拉圖分析、多欄統計表格 → 手機上做不好也用不到，留在桌面版
 *   - 樓層／處理狀況分布改用長條列，不畫圓餅（375px 寬的圓餅圖標籤無法閱讀）
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Card, Col, Collapse, Drawer, Empty, List, Row, Segmented,
  Select, Space, Spin, Tag, Typography,
} from 'antd'
import {
  ToolOutlined, CheckCircleOutlined, AuditOutlined, ClockCircleOutlined,
  ExclamationCircleOutlined, LinkOutlined, ReloadOutlined,
} from '@ant-design/icons'
import {
  Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer,
  Tooltip as RcTooltip, XAxis, YAxis,
} from 'recharts'
import dayjs from 'dayjs'

import { fetchDashboard, fetchYears } from '@/api/luqunRepair'
import type { DashboardData, RepairCase } from '@/types/luqunRepair'

const { Text, Title } = Typography

// ── 常數 ──────────────────────────────────────────────────────────────────────
// 與 pages/LuqunRepair/index.tsx 的 RAGIC_LUQUN_BASE 相同值。
// 刻意複製而非 export 共用，是為了這次改動完全不碰桌面版那支 131KB 的檔案；
// 之後若要收斂，再把它抽到 constants/ 下由兩邊共用。
const RAGIC_LUQUN_BASE = 'https://ap12.ragic.com/soutlet001/luqun-public-works-repair-reporting-system/6'
const ragicCaseUrl = (ragicId: string) => `${RAGIC_LUQUN_BASE}/${ragicId}`

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1)

const STATUS_COLOR: Record<string, string> = {
  '已驗收': '#52C41A', '已結案': '#52C41A', '結案': '#52C41A',
  '完修': '#52C41A', '已完成': '#52C41A', '完成': '#52C41A',
  '處理中': '#1890FF', '待維修': '#FAAD14', '待驗收': '#FAAD14',
  '待辦驗': '#FAAD14', '待協調': '#FF7A45', '待排除': '#FF4D4F',
  '取消': '#8C8C8C', '作廢': '#8C8C8C',
}
const statusColor = (s: string) => STATUS_COLOR[s] ?? '#8C8C8C'

const PIE_COLORS = ['#1B3A5C', '#4BA8E8', '#52C41A', '#FAAD14', '#FF7A45', '#13C2C2', '#8C8C8C']

const fmt    = (n: number) => (n ?? 0).toLocaleString('zh-TW')
const fmtDec = (n: number, d = 1) => (n ?? 0).toFixed(d)
const fmtMoney = (n: number) => `$${Math.round(n ?? 0).toLocaleString('zh-TW')}`

// ── KPI 卡（手機版：2 欄排列，字級縮小）──────────────────────────────────────
function MobileKpiCard({
  title, value, suffix, color, icon,
}: {
  title: string
  value: string | number
  suffix?: string
  color: string
  icon: React.ReactNode
}) {
  return (
    <Card
      size="small"
      styles={{ body: { padding: '10px 8px' } }}
      style={{ textAlign: 'center', borderTop: `3px solid ${color}`, height: '100%' }}
    >
      <div style={{ color, fontSize: 18, lineHeight: 1 }}>{icon}</div>
      <div style={{ color, fontSize: 22, fontWeight: 700, lineHeight: 1.3, marginTop: 2 }}>
        {value}
        {suffix && <span style={{ fontSize: 12, marginLeft: 2, fontWeight: 400 }}>{suffix}</span>}
      </div>
      <div style={{ color: '#666', fontSize: 11, marginTop: 2 }}>{title}</div>
    </Card>
  )
}

// ── 分布長條列（取代圓餅圖）─────────────────────────────────────────────────
function DistList({
  rows, colorOf,
}: {
  rows: Array<{ label: string; count: number }>
  colorOf?: (label: string) => string
}) {
  const max = Math.max(1, ...rows.map((r) => r.count))
  const total = rows.reduce((s, r) => s + r.count, 0)
  if (rows.length === 0) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="無資料" />
  return (
    <div>
      {rows.map((r) => {
        const color = colorOf ? colorOf(r.label) : '#4BA8E8'
        return (
          <div key={r.label} style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
              <span style={{ color: '#333' }}>{r.label || '未分類'}</span>
              <span style={{ color: '#666' }}>
                {fmt(r.count)} 件
                <span style={{ color: '#aaa', marginLeft: 6 }}>
                  {total > 0 ? `${((r.count / total) * 100).toFixed(0)}%` : '-'}
                </span>
              </span>
            </div>
            <div style={{ height: 6, background: '#f0f2f5', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${(r.count / max) * 100}%`, height: '100%', background: color }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── 案件明細 Drawer（底部彈出，遵循 CLAUDE.md §7 的標題列格式）──────────────
function MobileCaseDrawer({
  caseData, onClose,
}: { caseData: RepairCase | null; onClose: () => void }) {
  if (!caseData) return null

  const rows: Array<[string, React.ReactNode]> = [
    ['標題',     <strong key="t">{caseData.title || '—'}</strong>],
    ['報修人',   caseData.reporter_name || '—'],
    ['報修類型', caseData.repair_type ? <Tag key="ty">{caseData.repair_type}</Tag> : '—'],
    ['發生樓層', caseData.floor || '—'],
    ['發生時間', caseData.occurred_at || '—'],
    ['負責單位', caseData.responsible_unit || '—'],
    ['處理狀況', caseData.status
      ? <Tag key="st" color={statusColor(caseData.status)}>{caseData.status}</Tag>
      : '—'],
    ['花費工時', caseData.work_hours ? `${fmtDec(caseData.work_hours, 2)} hr` : '—'],
    ['委外費用', caseData.outsource_fee ? fmtMoney(caseData.outsource_fee) : '—'],
    ['維修費用', caseData.maintenance_fee ? fmtMoney(caseData.maintenance_fee) : '—'],
    ['費用合計', caseData.total_fee
      ? <strong key="fee">{fmtMoney(caseData.total_fee)}</strong>
      : '—'],
    ['扣款費用', caseData.deduction_fee ? fmtMoney(caseData.deduction_fee) : '—'],
    ['扣款專櫃', caseData.deduction_counter_name || '—'],
    ['驗收人',   caseData.acceptor || '—'],
    ['結案人',   caseData.closer || '—'],
    ['結案天數', caseData.close_days != null ? `${caseData.close_days} 天` : '—'],
    ['等待天數', caseData.pending_days != null ? `${caseData.pending_days} 天` : '—'],
    ['管理單位回應', caseData.mgmt_response || '—'],
  ]

  return (
    <Drawer
      open={!!caseData}
      onClose={onClose}
      placement="bottom"
      height="85%"
      destroyOnClose
      title={
        <div style={{ lineHeight: 1.4 }}>
          <Space size={6} wrap>
            <ToolOutlined style={{ color: '#1B3A5C' }} />
            <span style={{ fontSize: 14 }}>
              報修編號：{caseData.case_no || caseData.ragic_id}
            </span>
            <a
              href={ragicCaseUrl(caseData.ragic_id)}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#4BA8E8', fontSize: 12, whiteSpace: 'nowrap' }}
            >
              <LinkOutlined /> 在 Ragic 查看
            </a>
          </Space>
        </div>
      }
    >
      <div style={{ fontSize: 13 }}>
        {rows.map(([label, value]) => (
          <div
            key={label}
            style={{
              display: 'flex',
              padding: '8px 0',
              borderBottom: '1px solid #f0f0f0',
              gap: 12,
            }}
          >
            <div style={{ width: 88, flexShrink: 0, color: '#888' }}>{label}</div>
            <div style={{ flex: 1, wordBreak: 'break-word' }}>{value}</div>
          </div>
        ))}
      </div>
    </Drawer>
  )
}

// ── 案件清單（Top N）────────────────────────────────────────────────────────
function CaseList({
  cases, mode, onPick,
}: {
  cases: RepairCase[]
  mode: 'uncompleted' | 'fee' | 'hours'
  onPick: (c: RepairCase) => void
}) {
  if (!cases || cases.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="無資料" />
  }
  return (
    <List
      size="small"
      dataSource={cases}
      renderItem={(c) => (
        <List.Item
          onClick={() => onPick(c)}
          style={{ padding: '10px 0', cursor: 'pointer', alignItems: 'flex-start' }}
        >
          <div style={{ width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <Text style={{ fontSize: 13, fontWeight: 500 }} ellipsis>
                {c.title || c.case_no || c.ragic_id}
              </Text>
              <Text style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', color: '#1B3A5C' }}>
                {mode === 'fee'   && fmtMoney(c.total_fee)}
                {mode === 'hours' && `${fmtDec(c.work_hours, 1)} hr`}
                {mode === 'uncompleted' && (c.pending_days != null ? `${c.pending_days} 天` : '—')}
              </Text>
            </div>
            <Space size={4} wrap style={{ marginTop: 4 }}>
              <Tag style={{ margin: 0, fontSize: 11 }}>{c.case_no || c.ragic_id}</Tag>
              {c.repair_type && <Tag style={{ margin: 0, fontSize: 11 }}>{c.repair_type}</Tag>}
              {c.floor && <Tag style={{ margin: 0, fontSize: 11 }}>{c.floor}</Tag>}
              {c.status && (
                <Tag color={statusColor(c.status)} style={{ margin: 0, fontSize: 11 }}>
                  {c.status}
                </Tag>
              )}
            </Space>
          </div>
        </List.Item>
      )}
    />
  )
}

// ── 主頁面 ────────────────────────────────────────────────────────────────────
export default function MobileLuqunRepairDashboard() {
  const currentYear  = dayjs().year()
  const currentMonth = dayjs().month() + 1

  const [years, setYears] = useState<number[]>([currentYear])
  const [year,  setYear]  = useState<number>(currentYear)
  // 0 = 全年（與桌面版 fetchDashboard 的語意相同）
  const [month, setMonth] = useState<number>(currentMonth)

  const [data,    setData]    = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  const [topMode, setTopMode] = useState<'uncompleted' | 'fee' | 'hours'>('uncompleted')
  const [picked,  setPicked]  = useState<RepairCase | null>(null)

  useEffect(() => {
    fetchYears()
      .then((d) => {
        const ys = d.years ?? []
        setYears(ys.length > 0 ? ys : [currentYear])
      })
      .catch(() => { /* 年份取不到就沿用今年 */ })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const d = await fetchDashboard(year, month)
      setData(d)
    } catch (e: unknown) {
      setError((e as Error).message || '載入失敗')
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => { load() }, [load])

  const trendData = useMemo(
    () => (data?.trend_12m ?? []).map((p) => ({
      label: p.label, 總件數: p.total, 已完成: p.completed,
    })),
    [data],
  )

  const typePie = useMemo(() => {
    const list = [...(data?.type_dist ?? [])].sort((a, b) => b.count - a.count)
    if (list.length <= 6) return list.map((t) => ({ name: t.type || '未分類', value: t.count }))
    const top = list.slice(0, 5).map((t) => ({ name: t.type || '未分類', value: t.count }))
    const rest = list.slice(5).reduce((s, t) => s + t.count, 0)
    return [...top, { name: '其他', value: rest }]
  }, [data])

  const periodLabel = month > 0 ? `${year} 年 ${month} 月` : `${year} 年全年`

  // ── 篩選列（sticky）──────────────────────────────────────────────────────
  const filterBar = (
    <Card size="small" style={{ marginBottom: 12 }} styles={{ body: { padding: 8 } }}>
      <Row gutter={8} align="middle">
        <Col span={11}>
          <Select
            value={year}
            onChange={setYear}
            style={{ width: '100%' }}
            options={years.map((y) => ({ value: y, label: `${y} 年` }))}
          />
        </Col>
        <Col span={11}>
          <Select
            value={month}
            onChange={setMonth}
            style={{ width: '100%' }}
            options={[
              { value: 0, label: '全年' },
              ...MONTHS.map((m) => ({ value: m, label: `${m} 月` })),
            ]}
          />
        </Col>
        <Col span={2} style={{ textAlign: 'center' }}>
          <ReloadOutlined
            spin={loading}
            onClick={load}
            style={{ color: '#4BA8E8', fontSize: 16, cursor: 'pointer' }}
          />
        </Col>
      </Row>
    </Card>
  )

  if (error) {
    return (
      <div>
        {filterBar}
        <Alert type="error" showIcon message={`資料載入失敗：${error}`} />
      </div>
    )
  }

  if (loading && !data) {
    return (
      <div>
        {filterBar}
        <div style={{ textAlign: 'center', padding: 60 }}>
          <Spin size="large" tip="資料載入中..." />
        </div>
      </div>
    )
  }

  if (!data) {
    return <div>{filterBar}<Empty description="無資料" /></div>
  }

  const { kpi } = data

  return (
    <div>
      {filterBar}

      <Title level={5} style={{ margin: '0 0 8px', color: '#1B3A5C', fontSize: 14 }}>
        {periodLabel}
      </Title>

      {/* ── 主 KPI（2 欄）───────────────────────────────────────────────── */}
      <Row gutter={[8, 8]}>
        <Col xs={12}>
          <MobileKpiCard title="本月相關案件" value={fmt(kpi.total)}
            color="#1B3A5C" icon={<ToolOutlined />} />
        </Col>
        <Col xs={12}>
          <MobileKpiCard title="未完成件數" value={fmt(kpi.uncompleted)}
            color="#FF4D4F" icon={<ExclamationCircleOutlined />} />
        </Col>
        <Col xs={12}>
          <MobileKpiCard title="待辦驗件數" value={fmt(kpi.pending_verify)}
            color="#FAAD14" icon={<AuditOutlined />} />
        </Col>
        <Col xs={12}>
          <MobileKpiCard title="平均結案天數"
            value={kpi.avg_close_days != null ? fmtDec(kpi.avg_close_days, 1) : '—'}
            suffix="天" color="#4BA8E8" icon={<ClockCircleOutlined />} />
        </Col>
        <Col xs={12}>
          <MobileKpiCard title="本月工時統計" value={fmtDec(kpi.total_work_hours, 1)}
            suffix="hr" color="#13C2C2" icon={<ClockCircleOutlined />} />
        </Col>
        <Col xs={12}>
          <MobileKpiCard title="已完成件數" value={fmt(kpi.completed)}
            color="#52C41A" icon={<CheckCircleOutlined />} />
        </Col>
      </Row>

      {/* ── 更多指標 ───────────────────────────────────────────────────── */}
      <Collapse
        size="small"
        style={{ marginTop: 12, background: '#fff' }}
        items={[{
          key: 'more',
          label: <span style={{ fontSize: 13 }}>更多指標（費用 / 客房 / 扣款專櫃）</span>,
          children: (
            <div style={{ fontSize: 13 }}>
              {([
                ['客房報修件數',  `${fmt(kpi.room_cases)} 件`],
                ['當月費用合計',  fmtMoney(kpi.month_total_fee)],
                ['　委外費用',    fmtMoney(kpi.month_outsource_fee)],
                ['　維修費用',    fmtMoney(kpi.month_maintenance_fee)],
                ['當月扣款費用',  fmtMoney(kpi.month_deduction_fee)],
                [month > 0 ? `累計至 ${month} 月費用` : '全年費用', fmtMoney(kpi.annual_fee)],
                ['本月扣款專櫃',  `${fmt(kpi.total_counter_stores)} 家 / ${fmtMoney(kpi.total_counter_fee)}`],
              ] as Array<[string, string]>).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f5f5f5' }}>
                  <span style={{ color: '#888' }}>{k}</span>
                  <span style={{ fontWeight: 500 }}>{v}</span>
                </div>
              ))}
              {(kpi.counter_store_names ?? []).length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Space size={4} wrap>
                    {kpi.counter_store_names.map((n) => (
                      <Tag key={n} color="orange" style={{ margin: 0, fontSize: 11 }}>{n}</Tag>
                    ))}
                  </Space>
                </div>
              )}
            </div>
          ),
        }]}
      />

      {/* ── 近 12 個月趨勢 ─────────────────────────────────────────────── */}
      <Card size="small" title={<span style={{ fontSize: 13 }}>近 12 個月報修趨勢</span>}
        style={{ marginTop: 12 }} styles={{ body: { padding: '8px 4px' } }}>
        <ResponsiveContainer width="100%" height={190}>
          <BarChart data={trendData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
            <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={1} />
            <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
            <RcTooltip contentStyle={{ fontSize: 12 }} />
            <Bar dataKey="總件數" fill="#1B3A5C" radius={[2, 2, 0, 0]} />
            <Bar dataKey="已完成" fill="#52C41A" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* ── 報修類型分布 ──────────────────────────────────────────────── */}
      <Card size="small" title={<span style={{ fontSize: 13 }}>報修類型分布</span>}
        style={{ marginTop: 12 }} styles={{ body: { padding: 8 } }}>
        <ResponsiveContainer width="100%" height={170}>
          <PieChart>
            <Pie data={typePie} dataKey="value" nameKey="name"
              cx="50%" cy="50%" innerRadius={40} outerRadius={65} paddingAngle={1}>
              {typePie.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <RcTooltip contentStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ marginTop: 4 }}>
          {typePie.map((t, i) => (
            <div key={t.name} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, padding: '3px 0' }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: PIE_COLORS[i % PIE_COLORS.length], flexShrink: 0 }} />
              <span style={{ flex: 1, color: '#333' }}>{t.name}</span>
              <span style={{ color: '#666' }}>{fmt(t.value)} 件</span>
            </div>
          ))}
        </div>
      </Card>

      {/* ── 樓層 / 處理狀況分布 ───────────────────────────────────────── */}
      <Card size="small" title={<span style={{ fontSize: 13 }}>發生樓層分布</span>}
        style={{ marginTop: 12 }} styles={{ body: { padding: 12 } }}>
        <DistList rows={(data.floor_dist ?? []).map((f) => ({ label: f.floor, count: f.count }))} />
      </Card>

      <Card size="small" title={<span style={{ fontSize: 13 }}>處理狀況分布</span>}
        style={{ marginTop: 12 }} styles={{ body: { padding: 12 } }}>
        <DistList
          rows={(data.status_dist ?? []).map((s) => ({ label: s.status, count: s.count }))}
          colorOf={statusColor}
        />
      </Card>

      {/* ── Top 清單 ──────────────────────────────────────────────────── */}
      <Card size="small" style={{ marginTop: 12 }} styles={{ body: { padding: 12 } }}>
        <Segmented
          block
          size="small"
          value={topMode}
          onChange={(v) => setTopMode(v as typeof topMode)}
          options={[
            { label: '未完成', value: 'uncompleted' },
            { label: '費用高',  value: 'fee' },
            { label: '工時高',  value: 'hours' },
          ]}
        />
        <div style={{ marginTop: 8 }}>
          <CaseList
            mode={topMode}
            cases={
              topMode === 'fee'   ? (data.top_fee ?? []) :
              topMode === 'hours' ? (data.top_hours ?? []) :
                                    (data.top_uncompleted ?? [])
            }
            onPick={setPicked}
          />
        </div>
        <Text type="secondary" style={{ fontSize: 11 }}>
          點擊案件查看完整明細；完整清單與匯出請使用桌面版。
        </Text>
      </Card>

      <MobileCaseDrawer caseData={picked} onClose={() => setPicked(null)} />
    </div>
  )
}
