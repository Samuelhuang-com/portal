/**
 * 戰情 KPI — 「告警」TAB（2026-10-10 新增；規格 docs/SPEC_war_room.md §7）
 *
 * 先看清單、再決定要不要寄信：
 *   1. 列出 A1～A5 偵測結果（只讀，不寄信）
 *   2. 勾選 → 「預覽寄送」（乾跑：只顯示會寄給誰、寄哪些）→ 確認後才真的寄
 *   3. 自動寄送預設關閉（設定裡 auto_send），排程由 sync_tool 的「戰情告警-*」執行
 * 收件人依館別（.env WAR_ROOM_ALERT_EMAIL_HOTEL／_MALL），且須在 WAR_ROOM_ALLOWED_EMAILS 內。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Col, DatePicker, Drawer, Form, InputNumber, Modal, Row, Segmented, Select, Space,
  Statistic, Switch, Table, Tag, Tooltip, Typography, message,
} from 'antd'
import { ReloadOutlined, SendOutlined, SettingOutlined, HistoryOutlined } from '@ant-design/icons'
import dayjs, { type Dayjs } from 'dayjs'

import {
  fetchWarRoomAlertLog, fetchWarRoomAlertSettings, fetchWarRoomAlerts, saveWarRoomAlertSettings, sendWarRoomAlerts,
  type AlertLevel, type WrAlert, type WrAlertLogEntry, type WrAlertSendResult, type WrAlertSettings, type WrAlerts,
} from '@/api/warRoom'
import { AssetHistoryDrawer, type AssetTarget } from './AssetHistory'

const { Text } = Typography

const LEVEL_COLOR: Record<AlertLevel, string> = { critical: 'red', warning: 'orange', info: 'blue' }
const VENUE_OPTS = [
  { label: '全部', value: 'all' }, { label: '飯店', value: 'hotel' }, { label: '商場', value: 'mall' }, { label: '整棟', value: 'both' },
]

export default function AlertsTab({ getContainer }: { getContainer?: () => HTMLElement }) {
  const [date, setDate] = useState<Dayjs>(dayjs())
  const [data, setData] = useState<WrAlerts | null>(null)
  const [loading, setLoading] = useState(false)
  const [venue, setVenue] = useState('all')
  const [types, setTypes] = useState<string[]>([])
  const [levels, setLevels] = useState<string[]>([])
  const [onlyDue, setOnlyDue] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [force, setForce] = useState(false)
  const [preview, setPreview] = useState<WrAlertSendResult | null>(null)
  const [sending, setSending] = useState(false)
  const [target, setTarget] = useState<AssetTarget | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [logOpen, setLogOpen] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    fetchWarRoomAlerts(date.format('YYYY-MM-DD'))
      .then(d => { setData(d); setSelected(s => s.filter(k => d.alerts.some(a => a.key === k))) })
      .catch(() => message.error('載入告警失敗'))
      .finally(() => setLoading(false))
  }, [date])
  useEffect(load, [load])

  const rows = useMemo(() => (data?.alerts ?? []).filter(a =>
    (venue === 'all' || a.venue === venue) &&
    (!types.length || types.includes(a.type)) &&
    (!levels.length || levels.includes(a.level)) &&
    (!onlyDue || a.due)), [data, venue, types, levels, onlyDue])

  const openPreview = async () => {
    try {
      setPreview(await sendWarRoomAlerts(selected, true, force))
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '預覽失敗')
    }
  }
  const confirmSend = async () => {
    setSending(true)
    try {
      const r = await sendWarRoomAlerts(selected, false, force)
      if (r.errors.length) message.warning(`寄出 ${r.sent_mails} 封，${r.errors.length} 封失敗：${r.errors[0]}`)
      else message.success(`已寄出 ${r.sent_mails} 封，涵蓋 ${r.sent_alerts} 項告警`)
      setPreview(null); setSelected([]); load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '寄送失敗')
    } finally { setSending(false) }
  }

  const s = data?.summary
  const rc = data?.recipients
  const noRecipient = rc && !rc.hotel.length && !rc.mall.length

  return (
    <div>
      <Space wrap style={{ marginBottom: 8, width: '100%', justifyContent: 'space-between' }}>
        <Space wrap>
          <DatePicker size="small" value={date} allowClear={false} onChange={v => v && setDate(v)} getPopupContainer={getContainer} />
          <Segmented size="small" value={venue} onChange={v => setVenue(v as string)} options={VENUE_OPTS} />
          <Select size="small" mode="multiple" allowClear placeholder="類型" style={{ minWidth: 150 }} value={types}
                  onChange={setTypes} getPopupContainer={getContainer} maxTagCount="responsive"
                  options={Object.entries(data?.type_labels ?? {}).map(([k, v]) => ({ value: k, label: `${k} ${v}` }))} />
          <Select size="small" mode="multiple" allowClear placeholder="等級" style={{ minWidth: 120 }} value={levels}
                  onChange={setLevels} getPopupContainer={getContainer}
                  options={[{ value: 'critical', label: '嚴重' }, { value: 'warning', label: '警告' }, { value: 'info', label: '資訊' }]} />
          <Switch size="small" checked={onlyDue} onChange={setOnlyDue} /><Text style={{ fontSize: 12 }}>只看待通知</Text>
        </Space>
        <Space wrap>
          <Button size="small" icon={<ReloadOutlined />} onClick={load} loading={loading}>重新偵測</Button>
          <Button size="small" icon={<HistoryOutlined />} onClick={() => setLogOpen(true)}>寄送紀錄</Button>
          <Button size="small" icon={<SettingOutlined />} onClick={() => setSettingsOpen(true)}>設定</Button>
        </Space>
      </Space>

      <Row gutter={[8, 8]} style={{ marginBottom: 8 }}>
        {[['全部', s?.total, '#1B3A5C'], ['嚴重', s?.critical, '#e74c3c'], ['警告', s?.warning, '#fa8c16'],
          ['資訊', s?.info, '#4BA8E8'], ['待通知', s?.due, '#722ed1']].map(([t, v, c]) => (
          <Col key={t as string} xs={12} md={4}>
            <Card size="small"><Statistic title={t as string} value={(v as number) ?? 0} valueStyle={{ color: c as string, fontSize: 22 }} /></Card>
          </Col>
        ))}
        <Col xs={24} md={4}>
          <Card size="small" styles={{ body: { padding: 8, fontSize: 12 } }}>
            <div>模式：{data?.auto_send ? <Tag color="red" style={{ margin: 0 }}>自動寄送中</Tag> : <Tag style={{ margin: 0 }}>乾跑（不自動寄）</Tag>}</div>
            <div style={{ marginTop: 4 }}>飯店收件 {rc?.hotel.length ?? 0}｜商場收件 {rc?.mall.length ?? 0}</div>
          </Card>
        </Col>
      </Row>

      {noRecipient && (
        <Alert type="warning" showIcon style={{ marginBottom: 8 }}
               message="尚未設定收件人（或不在白名單）"
               description="請在後端 .env 設定 WAR_ROOM_ALERT_EMAIL_HOTEL／WAR_ROOM_ALERT_EMAIL_MALL（須同時在 WAR_ROOM_ALLOWED_EMAILS 內），重啟後端。清單仍可查看，但無法寄信。" />
      )}
      {!!rc?.ignored.length && (
        <Alert type="info" showIcon style={{ marginBottom: 8 }} message={`以下收件人不在白名單，已略過：${rc.ignored.join('、')}`} />
      )}

      <Space style={{ marginBottom: 8 }} wrap>
        <Button type="primary" size="small" icon={<SendOutlined />} disabled={!selected.length || !!noRecipient} onClick={openPreview}>
          預覽寄送（{selected.length}）
        </Button>
        <Button size="small" onClick={() => setSelected(rows.filter(a => a.due).map(a => a.key))}>勾選目前清單中的待通知</Button>
        <Button size="small" onClick={() => setSelected([])} disabled={!selected.length}>清除勾選</Button>
        <Checkbox checked={force} onChange={e => setForce(e.target.checked)}>強制再寄（忽略已通知）</Checkbox>
      </Space>

      <Table<WrAlert>
        size="small" rowKey="key" loading={loading} dataSource={rows}
        pagination={{ pageSize: 20, showSizeChanger: false, size: 'small' }}
        rowSelection={{ selectedRowKeys: selected, onChange: k => setSelected(k as string[]), preserveSelectedRowKeys: true }}
        scroll={{ x: 900 }}
        columns={[
          { title: '等級', dataIndex: 'level', width: 64, render: (_: unknown, a) => <Tag color={LEVEL_COLOR[a.level]} style={{ margin: 0 }}>{a.level_label}</Tag> },
          { title: '館別', dataIndex: 'venue_label', width: 60 },
          { title: '類型', width: 150, render: (_: unknown, a) => <span>{a.type} {a.type_label}</span> },
          {
            title: '告警', render: (_: unknown, a) => (
              <div>
                <div style={{ fontWeight: 600 }}>{a.title}</div>
                <div style={{ color: '#6b7280', fontSize: 12 }}>{a.detail}</div>
              </div>
            ),
          },
          { title: '位置', width: 80, render: (_: unknown, a) => a.room || (a.floor ? a.floor.toUpperCase() : '—') },
          { title: '起算', width: 100, dataIndex: 'since', render: (v: string, a) => <span>{(v || '—').slice(0, 10)}{a.wait_days != null ? <Text type="secondary"> ({a.wait_days}天)</Text> : null}</span> },
          {
            title: '上次通知', width: 100, dataIndex: 'last_sent',
            render: (v: string, a) => v
              ? <Tooltip title={a.due ? '已到再次通知的時間' : '尚在去重期間'}><span>{v}{a.due ? <Tag color="purple" style={{ marginLeft: 4 }}>可再寄</Tag> : null}</span></Tooltip>
              : <Tag color="purple" style={{ margin: 0 }}>未通知</Tag>,
          },
          {
            title: '查看', width: 150, fixed: 'right' as const, render: (_: unknown, a) => (
              <Space size={4}>
                {a.room && <Button size="small" type="link" style={{ padding: 0 }} onClick={() => setTarget({ type: 'room', room: a.room })}>房間履歷</Button>}
                {a.ref.kind === 'point' && typeof a.ref.point_id === 'number' && (
                  <Button size="small" type="link" style={{ padding: 0 }} onClick={() => setTarget({ type: 'point', id: a.ref.point_id as number })}>設備履歷</Button>
                )}
                {a.ref.ragic_url && <a href={a.ref.ragic_url as string} target="_blank" rel="noreferrer">Ragic</a>}
              </Space>
            ),
          },
        ]}
      />

      <Modal
        open={!!preview} title="預覽寄送（尚未寄出）" onCancel={() => setPreview(null)} getContainer={getContainer} width={640}
        okText="確認寄出" cancelText="取消" okButtonProps={{ danger: true, loading: sending, disabled: !preview?.plans.length }}
        onOk={confirmSend}
      >
        {!preview?.plans.length ? <Alert type="warning" message={preview?.message ?? '沒有可寄的對象'} /> : preview.plans.map((p, i) => (
          <Card key={i} size="small" style={{ marginBottom: 8 }}
                title={<span>{p.venues.map(v => (v === 'hotel' ? '飯店' : '商場')).join('＋')} 收件人（{p.emails.length}）· {p.count} 項</span>}>
            <div style={{ fontSize: 12, marginBottom: 6 }}>{p.emails.join('、')}</div>
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, maxHeight: 160, overflow: 'auto' }}>
              {p.titles.map((t, j) => <li key={j}>{t}</li>)}
            </ul>
          </Card>
        ))}
        <Text type="secondary" style={{ fontSize: 12 }}>按「確認寄出」才會真的寄信，並記錄為已通知。</Text>
      </Modal>

      <AssetHistoryDrawer target={target} date={date.format('YYYY-MM-DD')} onClose={() => setTarget(null)} getContainer={getContainer} />
      <SettingsDrawer open={settingsOpen} onClose={() => { setSettingsOpen(false); load() }} getContainer={getContainer} />
      <LogDrawer open={logOpen} onClose={() => setLogOpen(false)} getContainer={getContainer} />
    </div>
  )
}

function SettingsDrawer({ open, onClose, getContainer }: { open: boolean; onClose: () => void; getContainer?: () => HTMLElement }) {
  const [form] = Form.useForm<WrAlertSettings>()
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    if (open) fetchWarRoomAlertSettings().then(v => form.setFieldsValue(v)).catch(() => message.error('載入設定失敗'))
  }, [open, form])
  const save = async () => {
    setSaving(true)
    try {
      await saveWarRoomAlertSettings(form.getFieldsValue(true))
      message.success('已儲存'); onClose()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err.response?.data?.detail ?? '儲存失敗')
    } finally { setSaving(false) }
  }
  return (
    <Drawer open={open} onClose={onClose} width={420} title="告警設定" getContainer={getContainer}
            extra={<Button type="primary" loading={saving} onClick={save}>儲存</Button>}>
      <Form form={form} layout="vertical" size="small">
        <Form.Item label="A1 報修久未完成：警告天數（≥）" name="repair_warn_days"><InputNumber min={1} max={365} /></Form.Item>
        <Form.Item label="A1 報修久未完成：嚴重天數（≥）" name="repair_critical_days"><InputNumber min={1} max={365} /></Form.Item>
        <Form.Item label="A1 嚴重等級重複通知間隔（天）" name="repeat_critical_days"><InputNumber min={1} max={30} /></Form.Item>
        <Form.Item label="A2 巡檢未填：截止時間（HH:MM，今日過此時間才算）" name="inspect_deadline"><InputNumber style={{ display: 'none' }} /></Form.Item>
        <Form.Item label="A2 巡檢截止時間" name="inspect_deadline" getValueProps={(v: string) => ({ value: v })}>
          <Select options={['16:00', '17:00', '18:00', '19:00', '20:00', '21:00'].map(v => ({ value: v, label: v }))} getPopupContainer={getContainer} />
        </Form.Item>
        <Form.Item label="A4 IHG 保養異常：往回看幾天" name="ihg_lookback_days"><InputNumber min={1} max={14} /></Form.Item>
        <Form.Item label="A5 同房反覆報修：次數（≥）" name="room_repeat_count"><InputNumber min={2} max={20} /></Form.Item>
        <Form.Item label="A5 統計區間（天）" name="room_repeat_days"><InputNumber min={7} max={180} /></Form.Item>
        <Form.Item label="啟用的告警類型">
          {['A1', 'A2', 'A3', 'A4', 'A5'].map(k => (
            <Form.Item key={k} name={['enabled', k]} valuePropName="checked" noStyle>
              <Checkbox>{k}</Checkbox>
            </Form.Item>
          ))}
        </Form.Item>
        <Form.Item label="自動寄送（排程）" name="auto_send" valuePropName="checked"
                   extra="關閉＝排程只偵測、不寄信（乾跑）。打開後，sync_tool 的「戰情告警-嚴重掃描／每日彙整」才會真的寄出。">
          <Switch />
        </Form.Item>
      </Form>
    </Drawer>
  )
}

function LogDrawer({ open, onClose, getContainer }: { open: boolean; onClose: () => void; getContainer?: () => HTMLElement }) {
  const [log, setLog] = useState<WrAlertLogEntry[]>([])
  useEffect(() => { if (open) fetchWarRoomAlertLog().then(setLog).catch(() => setLog([])) }, [open])
  return (
    <Drawer open={open} onClose={onClose} width={560} title="寄送紀錄" getContainer={getContainer}>
      <Table<WrAlertLogEntry> size="small" rowKey={(r) => r.at + r.by} dataSource={log} pagination={{ pageSize: 15, size: 'small' }}
        columns={[
          { title: '時間', dataIndex: 'at', width: 130 },
          { title: '方式', dataIndex: 'mode', width: 70, render: (v: string) => ({ manual: '手動', scan: '嚴重掃描', daily: '每日彙整' } as Record<string, string>)[v] ?? v },
          { title: '操作者', dataIndex: 'by', ellipsis: true },
          { title: '告警', dataIndex: 'alerts', width: 56 },
          { title: '信件', dataIndex: 'mails', width: 56 },
        ]}
        expandable={{ expandedRowRender: r => <Text style={{ fontSize: 12 }}>收件：{r.recipients.join('、')}</Text> }} />
    </Drawer>
  )
}
