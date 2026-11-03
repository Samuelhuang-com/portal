/**
 * 開發統計（設定 → 開發統計）
 * 資料：CHANGELOG 條目（上傳匯入，只新增）；開始／結束時間可手動編輯。
 */
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type ReactNode } from 'react'
import { Button, Card, Col, DatePicker, Form, Input, Modal, Row, Select, Space, Statistic, Switch, Table, Tabs, Tag, message } from 'antd'
import { UploadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis,
} from 'recharts'
import {
  getDevLogEntries, getDevLogStats, importDevLog, patchDevLogEntry, syncDevLogGit,
  type DevLogItem, type DevLogStats,
} from '@/api/devLog'

const FMT = 'YYYY-MM-DD HH:mm'

// 專案色系：品牌色 #1B3A5C、輔色 #4BA8E8，其餘為同色系延伸
const PALETTE = ['#1B3A5C', '#4BA8E8', '#7C5CFF', '#22C55E', '#F59E0B', '#EF4444', '#14B8A6', '#EC4899']
const CAT_LABEL: Record<string, string> = { Added: '新增', Changed: '變更', Fixed: '修復', Known: '已知問題' }

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

  const load = async () => {
    setLoading(true)
    try {
      const [s, l] = await Promise.all([
        getDevLogStats({ module, month }),
        getDevLogEntries({ module, month, unknown_only: unknownOnly }),
      ])
      setStats(s.data)
      setItems(l.data.items)
    } catch {
      message.error('讀取開發統計失敗（需要「開發統計：查看」權限）')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [module, month, unknownOnly])

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
            key: 'entries',
            label: '條目',
            children: (
              <>
        <Card size="small" title="條目（可編輯開始／結束時間）">
          <Table<DevLogItem> rowKey="id" size="small" loading={loading} columns={columns} dataSource={items}
            pagination={{ pageSize: 50, showTotal: (t) => `共 ${t} 筆` }} scroll={{ x: 1200 }} />
        </Card>
              </>
            ),
          },
        ]}
      />

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
