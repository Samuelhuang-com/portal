/**
 * 開發統計（設定 → 開發統計）
 * 資料：CHANGELOG 條目（上傳匯入，只新增）；開始／結束時間可手動編輯。
 * 2026-11-20：新增「需求」分頁（需求清單、需求×模組矩陣、Jira CSV 匯入）；條目可綁定需求（一對一）。
 */
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import { Button, Card, Col, DatePicker, Form, Input, Modal, Row, Select, Space, Statistic, Switch, Table, Tabs, Tag, message } from 'antd'
import { PlusOutlined, UploadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis,
} from 'recharts'
import {
  createRequirement, getDevLogEntries, getDevLogStats, getRequirements, importDevLog, importJiraCsv,
  patchDevLogEntry, patchRequirement, syncDevLogGit,
  type DevLogItem, type DevLogStats, type DevRequirement, type RequirementPriority, type RequirementStatus,
  type RequirementSummary,
} from '@/api/devLog'

const FMT = 'YYYY-MM-DD HH:mm'

// 專案色系：品牌色 #1B3A5C、輔色 #4BA8E8，其餘為同色系延伸
const PALETTE = ['#1B3A5C', '#4BA8E8', '#7C5CFF', '#22C55E', '#F59E0B', '#EF4444', '#14B8A6', '#EC4899']
const CAT_LABEL: Record<string, string> = { Added: '新增', Changed: '變更', Fixed: '修復', Known: '已知問題' }
const REQ_STATUS_OPTIONS = (['待評估', '進行中', '已完成', '退回'] as RequirementStatus[]).map((v) => ({ label: v, value: v }))
const PRIORITY_OPTIONS = (['高', '中', '低'] as RequirementPriority[]).map((v) => ({ label: v, value: v }))
const STATUS_COLOR: Record<string, string> = { 待評估: 'default', 進行中: 'processing', 已完成: 'success', 退回: 'error' }
const PRIORITY_COLOR: Record<string, string> = { 高: 'red', 中: 'orange', 低: 'blue' }

function GlassCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card
      size="small"
      title={title}
      styles={{ body: { padding: 12 } }}
      style={{ borderRadius: 12, boxShadow: '0 4px 18px rgba(27,58,92,0.08)', overflow: 'hidden' }}
    >
      {children}
    </Card>
  )
}

function errText(e: unknown, fallback: string): string {
  const d = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => (x && typeof x === 'object' && 'msg' in x ? String((x as { msg: unknown }).msg) : String(x))).join('；')
  return fallback
}

export default function DevStatsPage() {
  const [stats, setStats] = useState<DevLogStats | null>(null)
  const [items, setItems] = useState<DevLogItem[]>([])
  const [module, setModule] = useState<string | undefined>(undefined)
  const [month, setMonth] = useState<string | undefined>(undefined)
  const [unknownOnly, setUnknownOnly] = useState(false)
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<DevLogItem | null>(null)
  const [form] = Form.useForm()
  const fileRef = useRef<HTMLInputElement>(null)
  const [importing, setImporting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [unboundOnly, setUnboundOnly] = useState(false)
  const [reqData, setReqData] = useState<RequirementSummary | null>(null)
  const [reqEditing, setReqEditing] = useState<DevRequirement | 'new' | null>(null)
  const [reqForm] = Form.useForm()
  const [savingReq, setSavingReq] = useState(false)
  const jiraRef = useRef<HTMLInputElement>(null)
  const [importingJira, setImportingJira] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [s, l, r] = await Promise.all([
        getDevLogStats({ module, month }),
        getDevLogEntries({ module, month, unknown_only: unknownOnly, unbound_only: unboundOnly }),
        getRequirements(),
      ])
      setStats(s.data)
      setItems(l.data.items)
      setReqData(r.data)
    } catch {
      message.error('讀取開發統計失敗（需要「開發統計：查看」權限）')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [module, month, unknownOnly, unboundOnly])

  const moduleOptions = useMemo(
    () => (stats?.by_module ?? []).map((m) => ({ label: m.module, value: m.module })), [stats])
  const monthOptions = useMemo(
    () => (stats?.by_month ?? []).map((m) => ({ label: m.month, value: m.month })), [stats])

  const openEdit = (it: DevLogItem) => {
    setEditing(it)
    form.setFieldsValue({
      start_at: it.start_at ? dayjs(it.start_at, FMT) : null,
      end_at: it.end_at ? dayjs(it.end_at, FMT) : null,
      time_note: it.time_note,
    })
  }

  const saveEdit = async () => {
    if (!editing) return
    const v = await form.validateFields()
    const start = v.start_at ? (v.start_at as dayjs.Dayjs).format(FMT) : null
    const end = v.end_at ? (v.end_at as dayjs.Dayjs).format(FMT) : null
    try {
      await patchDevLogEntry(editing.id, { start_at: start, end_at: end, time_note: v.time_note ?? '' })
      message.success('已儲存')
      setEditing(null)
      load()
    } catch (e: unknown) {
      message.error(errText(e, '儲存失敗'))
    }
  }

  const onPickFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''   // 允許再次選同一個檔案
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.md')) {
      message.error('請選擇 CHANGELOG.md 檔案')
      return
    }
    setImporting(true)
    try {
      const res = await importDevLog(file)
      message.success(`解析 ${res.data.parsed} 筆，新增 ${res.data.added} 筆，既有 ${res.data.skipped_existing} 筆保留不覆寫`)
      load()
    } catch (err: unknown) {
      message.error(errText(err, '匯入失敗（需要「開發統計：管理」權限）'))
    } finally {
      setImporting(false)
    }
  }

  const onSyncGit = async () => {
    setSyncing(true)
    try {
      const res = await syncDevLogGit()
      message.success(`git 共 ${res.data.commits} 筆 commit，新增 ${res.data.added} 筆，既有 ${res.data.skipped_existing} 筆保留不覆寫`)
      load()
    } catch (err: unknown) {
      message.error(errText(err, '從 git 同步失敗（需要「開發統計：管理」權限）'))
    } finally {
      setSyncing(false)
    }
  }

  const reqItems = reqData?.items ?? []
  const reqOptions = reqItems.map((r) => ({ label: `${r.req_no}　${r.title}`, value: r.id }))

  const onBindChange = async (it: DevLogItem, requirementId: number | null) => {
    try {
      await patchDevLogEntry(it.id, { requirement_id: requirementId })
      message.success(requirementId ? '已綁定需求' : '已解除綁定')
      load()
    } catch (e: unknown) {
      message.error(errText(e, '綁定失敗（需要「開發統計：管理」權限）'))
    }
  }

  const openNewReq = () => {
    setReqEditing('new')
    reqForm.resetFields()
    reqForm.setFieldsValue({ status: '待評估', priority: '中' })
  }

  const openEditReq = (r: DevRequirement) => {
    setReqEditing(r)
    reqForm.setFieldsValue({
      title: r.title, description: r.description, requester: r.requester,
      module: r.module, status: r.status, priority: r.priority,
    })
  }

  const saveReq = async () => {
    const v = await reqForm.validateFields()
    const body = {
      title: v.title as string,
      description: v.description ?? null,
      requester: v.requester ?? null,
      module: v.module ?? null,
      status: v.status as RequirementStatus,
      priority: v.priority as RequirementPriority,
    }
    setSavingReq(true)
    try {
      if (reqEditing === 'new') await createRequirement(body)
      else if (reqEditing) await patchRequirement(reqEditing.id, body)
      message.success('需求已儲存')
      setReqEditing(null)
      load()
    } catch (e: unknown) {
      message.error(errText(e, '儲存需求失敗（需要「開發統計：管理」權限）'))
    } finally {
      setSavingReq(false)
    }
  }

  const onPickJira = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv')) {
      message.error('請選擇 Jira 匯出的 CSV 檔案')
      return
    }
    setImportingJira(true)
    try {
      const d = (await importJiraCsv(file)).data
      const unmapped = d.unmapped_statuses.length ? `；未對應的狀態已設為「待評估」：${d.unmapped_statuses.join('、')}` : ''
      message.success(`讀取 ${d.rows} 筆，新增 ${d.added} 筆，既有 ${d.skipped_existing} 筆保留不覆寫，略過 ${d.skipped_invalid} 筆${unmapped}`, 8)
      load()
    } catch (err: unknown) {
      message.error(errText(err, 'Jira CSV 匯入失敗（需要「開發統計：管理」權限）'))
    } finally {
      setImportingJira(false)
    }
  }

  const reqColumns: ColumnsType<DevRequirement> = [
    { title: '需求編號', dataIndex: 'req_no', width: 110 },
    { title: '狀態', dataIndex: 'status', width: 100, render: (v: string) => <Tag color={STATUS_COLOR[v]}>{v}</Tag> },
    { title: '優先度', dataIndex: 'priority', width: 80, render: (v: string) => <Tag color={PRIORITY_COLOR[v]}>{v}</Tag> },
    { title: '標題', dataIndex: 'title', ellipsis: true },
    { title: '提出人', dataIndex: 'requester', width: 110, render: (v: string) => v || '—' },
    { title: '需求模組', dataIndex: 'module', width: 130, render: (v: string) => v || '—' },
    { title: '變更數', dataIndex: 'change_count', align: 'right', width: 90 },
    { title: '涉及模組', dataIndex: 'modules', width: 240,
      render: (v: string[]) => (v.length ? v.map((m) => <Tag key={m}>{m}</Tag>) : '—') },
    { title: '已記錄工時（小時）', dataIndex: 'hours', align: 'right', width: 150 },
    { title: '最後變更', dataIndex: 'last_change_at', width: 150, render: (v: string | null) => v || '—' },
    { title: '', key: 'op', width: 80, render: (_: unknown, r) => <Button size="small" onClick={() => openEditReq(r)}>編輯</Button> },
  ]

  const matrixCount = (rid: number, mod: string) =>
    (reqData?.matrix ?? []).find((m) => m.requirement_id === rid && m.module === mod)?.count ?? 0

  const matrixColumns: ColumnsType<DevRequirement> = [
    { title: '需求', key: 'req', width: 280, render: (_: unknown, r: DevRequirement) => `${r.req_no}　${r.title}` },
    ...(reqData?.modules ?? []).map((m) => ({
      title: m,
      key: `mod-${m}`,
      align: 'right' as const,
      width: 110,
      render: (_: unknown, r: DevRequirement) => {
        const n = matrixCount(r.id, m)
        return n ? n : <span style={{ color: '#bbb' }}>—</span>
      },
    })),
    { title: '合計', key: 'total', align: 'right' as const, width: 90, render: (_: unknown, r: DevRequirement) => <b>{r.change_count}</b> },
  ]

  const matrixRows = reqItems.filter((r) => r.change_count > 0)

  const columns: ColumnsType<DevLogItem> = [
    { title: '版本日期', dataIndex: 'entry_date', width: 110 },
    { title: '類型', dataIndex: 'category', width: 90, render: (v: string) => <Tag>{v}</Tag> },
    { title: '模組', dataIndex: 'module', width: 140 },
    { title: '路由', dataIndex: 'route', width: 200, render: (v: string) => v
      ? <a href={v} target="_blank" rel="noreferrer">{v}</a>
      : <Tag color="default">路由未知</Tag> },
    { title: '標題', dataIndex: 'title', ellipsis: true },
    { title: '開始時間', dataIndex: 'start_at', width: 150, render: (v: string | null) => v || '—' },
    { title: '結束時間', dataIndex: 'end_at', width: 150, render: (v: string | null) => v || '—' },
    { title: '時間說明', dataIndex: 'time_note', ellipsis: true, width: 240, render: (v: string) => v || '—' },
    { title: '需求', dataIndex: 'requirement_id', width: 210, render: (_: unknown, r: DevLogItem) => (
      <Select allowClear showSearch size="small" style={{ width: 200 }} placeholder="未綁定"
        value={r.requirement_id ?? undefined} options={reqOptions} optionFilterProp="label"
        onChange={(v: number | undefined) => onBindChange(r, v ?? null)} />) },
    { title: '', key: 'op', width: 80, render: (_: unknown, r) => <Button size="small" onClick={() => openEdit(r)}>編輯時間</Button> },
  ]

  const moduleColumns: ColumnsType<DevLogStats['by_module'][number]> = [
    { title: '模組', dataIndex: 'module' },
    { title: '條目數', dataIndex: 'entries', align: 'right', width: 100 },
    { title: '有時間', dataIndex: 'with_time', align: 'right', width: 100 },
    { title: '已記錄工時（小時）', dataIndex: 'hours', align: 'right', width: 160 },
  ]

  return (
    <div>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <input ref={fileRef} type="file" accept=".md,text/markdown" style={{ display: 'none' }} onChange={onPickFile} />
          <Button icon={<UploadOutlined />} loading={importing} onClick={() => fileRef.current?.click()}>
            匯入 CHANGELOG.md
          </Button>
          <Button loading={syncing} onClick={onSyncGit}>從 git 同步</Button>
          <Select allowClear placeholder="模組" style={{ minWidth: 180 }} value={module} onChange={setModule} options={moduleOptions} />
          <Select allowClear placeholder="月份" style={{ minWidth: 120 }} value={month} onChange={setMonth} options={monthOptions} />
          <Space>只看時間未知<Switch checked={unknownOnly} onChange={setUnknownOnly} /></Space>
          <Space>只看未綁定需求<Switch checked={unboundOnly} onChange={setUnboundOnly} /></Space>
        </Space>
      </Card>

      <Tabs
        defaultActiveKey="stats"
        items={[
          {
            key: 'stats',
            label: '統計',
            children: (
              <>
        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col span={6}><Card size="small"><Statistic title="條目數" value={stats?.total ?? 0} /></Card></Col>
          <Col span={6}><Card size="small"><Statistic title="有時間" value={stats?.with_time ?? 0} /></Card></Col>
          <Col span={6}><Card size="small"><Statistic title="時間未知" value={stats?.unknown ?? 0} /></Card></Col>
          <Col span={6}><Card size="small"><Statistic title="同時有開始與結束" value={stats?.with_range ?? 0} /></Card></Col>
        </Row>

        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col span={12}>
            <GlassCard title="每月條目趨勢">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={stats?.by_month ?? []} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="gEntries" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#1B3A5C" stopOpacity={0.55} />
                      <stop offset="100%" stopColor="#1B3A5C" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="gTimed" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4BA8E8" stopOpacity={0.6} />
                      <stop offset="100%" stopColor="#4BA8E8" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5eaf1" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
                  <RTooltip />
                  <Legend />
                  <Area type="monotone" dataKey="entries" name="條目數" stroke="#1B3A5C" fill="url(#gEntries)" strokeWidth={2} animationDuration={900} />
                  <Area type="monotone" dataKey="with_time" name="有時間" stroke="#4BA8E8" fill="url(#gTimed)" strokeWidth={2} animationDuration={1200} />
                </AreaChart>
              </ResponsiveContainer>
            </GlassCard>
          </Col>
          <Col span={12}>
            <GlassCard title="類型分布">
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={Object.entries(stats?.by_category ?? {}).map(([k, v]) => ({ name: CAT_LABEL[k] ?? k, value: v }))}
                    dataKey="value" nameKey="name" innerRadius={62} outerRadius={100} paddingAngle={3}
                    animationDuration={900} label={(e) => `${e.name} ${e.value}`}
                  >
                    {Object.keys(stats?.by_category ?? {}).map((_, i) => (
                      <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                    ))}
                  </Pie>
                  <RTooltip />
                </PieChart>
              </ResponsiveContainer>
            </GlassCard>
          </Col>
        </Row>

        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col span={12}>
            <GlassCard title="模組條目數 Top 10">
              <ResponsiveContainer width="100%" height={Math.max(260, (stats?.by_module.slice(0, 10).length ?? 0) * 32 + 40)}>
                <BarChart data={(stats?.by_module ?? []).slice(0, 10)} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
                  <defs>
                    <linearGradient id="gBar" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#1B3A5C" />
                      <stop offset="100%" stopColor="#4BA8E8" />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5eaf1" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12 }} allowDecimals={false} />
                  <YAxis type="category" dataKey="module" width={130} tick={{ fontSize: 12 }} />
                  <RTooltip />
                  <Bar dataKey="entries" name="條目數" fill="url(#gBar)" radius={[0, 8, 8, 0]} animationDuration={900} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          </Col>
          <Col span={12}>
            <GlassCard title="模組已記錄工時（小時）">
              <ResponsiveContainer width="100%" height={Math.max(260, (stats?.by_module.filter((m) => m.hours > 0).length ?? 0) * 32 + 40)}>
                <BarChart data={(stats?.by_module ?? []).filter((m) => m.hours > 0).slice(0, 10)} layout="vertical" margin={{ top: 4, right: 24, left: 8, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5eaf1" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis type="category" dataKey="module" width={130} tick={{ fontSize: 12 }} />
                  <RTooltip />
                  <Bar dataKey="hours" name="工時（小時）" radius={[0, 8, 8, 0]} animationDuration={900}>
                    {(stats?.by_module ?? []).filter((m) => m.hours > 0).slice(0, 10).map((_, i) => (
                      <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {(stats?.by_module ?? []).every((m) => m.hours === 0) && (
                <div style={{ textAlign: 'center', color: '#999', marginTop: 8 }}>尚無同時有開始與結束時間的條目</div>
              )}
            </GlassCard>
          </Col>
        </Row>

        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col span={14}>
            <Card size="small" title="依模組">
              <Table rowKey="module" size="small" pagination={false} columns={moduleColumns} dataSource={stats?.by_module ?? []} />
            </Card>
          </Col>
          <Col span={10}>
            <Card size="small" title="依月份">
              <Table
                rowKey="month" size="small" pagination={false}
                columns={[
                  { title: '月份', dataIndex: 'month' },
                  { title: '條目數', dataIndex: 'entries', align: 'right' },
                  { title: '有時間', dataIndex: 'with_time', align: 'right' },
                ]}
                dataSource={stats?.by_month ?? []}
              />
            </Card>
          </Col>
        </Row>
              </>
            ),
          },
          {
            key: 'requirements',
            label: '需求',
            children: (
              <>
                <Card size="small" style={{ marginBottom: 12 }}>
                  <Space wrap>
                    <input ref={jiraRef} type="file" accept=".csv,text/csv" style={{ display: 'none' }} onChange={onPickJira} />
                    <Button type="primary" icon={<PlusOutlined />} onClick={openNewReq}>新增需求</Button>
                    <Button icon={<UploadOutlined />} loading={importingJira} onClick={() => jiraRef.current?.click()}>匯入 Jira CSV</Button>
                    <span style={{ color: '#888' }}>建立與編輯限管理者；未綁定需求的變更共 {reqData?.unbound_entries ?? 0} 筆</span>
                  </Space>
                </Card>
                <Row gutter={12} style={{ marginBottom: 12 }}>
                  <Col span={6}><Card size="small"><Statistic title="需求數" value={reqItems.length} /></Card></Col>
                  <Col span={6}><Card size="small"><Statistic title="進行中" value={reqData?.status_counts['進行中'] ?? 0} /></Card></Col>
                  <Col span={6}><Card size="small"><Statistic title="已完成" value={reqData?.status_counts['已完成'] ?? 0} /></Card></Col>
                  <Col span={6}><Card size="small"><Statistic title="未綁定需求的變更" value={reqData?.unbound_entries ?? 0} /></Card></Col>
                </Row>
                <Card size="small" title="需求清單" style={{ marginBottom: 12 }}>
                  <Table<DevRequirement> rowKey="id" size="small" columns={reqColumns} dataSource={reqItems}
                    pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }} scroll={{ x: 1400 }} />
                </Card>
                <Card size="small" title="需求 × 模組（變更數）">
                  <Table<DevRequirement> rowKey="id" size="small" pagination={false} columns={matrixColumns}
                    dataSource={matrixRows} scroll={{ x: 'max-content' }} />
                </Card>
              </>
            ),
          },
          {
            key: 'entries',
            label: '條目',
            children: (
              <>
        <Card size="small" title="條目（可編輯開始／結束時間）">
          <Table<DevLogItem> rowKey="id" size="small" loading={loading} columns={columns} dataSource={items}
            pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }} scroll={{ x: 1420 }} />
        </Card>
              </>
            ),
          },
        ]}
      />

      <Modal
        open={reqEditing !== null}
        title={reqEditing === 'new' ? '新增需求' : reqEditing ? `編輯需求：${reqEditing.req_no}` : ''}
        onOk={saveReq} onCancel={() => setReqEditing(null)} okText="儲存"
        confirmLoading={savingReq} destroyOnClose
      >
        <Form form={reqForm} layout="vertical">
          <Form.Item name="title" label="標題" rules={[{ required: true, message: '請輸入標題' }]}>
            <Input maxLength={300} />
          </Form.Item>
          <Form.Item name="description" label="說明">
            <Input.TextArea rows={4} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="requester" label="提出人"><Input maxLength={120} /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="module" label="需求模組"><Input maxLength={120} placeholder="例如：商場工務" /></Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="status" label="狀態" rules={[{ required: true }]}><Select options={REQ_STATUS_OPTIONS} /></Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="priority" label="優先度" rules={[{ required: true }]}><Select options={PRIORITY_OPTIONS} /></Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal open={editing !== null} title={editing ? `編輯時間：${editing.title}` : ''} onOk={saveEdit} onCancel={() => setEditing(null)} okText="儲存">
        <Form form={form} layout="vertical">
          <Form.Item name="start_at" label="開始時間">
            <DatePicker showTime format={FMT} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="end_at" label="結束時間">
            <DatePicker showTime format={FMT} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="time_note" label="時間說明（來源或修改原因）">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
