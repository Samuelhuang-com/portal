/**
 * 庫存管理 › 庫存主檔設定 › 月結（規格 §8.5、§8.6，Phase 5 2026-11-17）
 *
 * 月結：先跑檢查（前月都已月結、月份已過完、有異動或有庫存的倉都已核准盤點〔空倉免盤〕、沒有盤點中的倉、
 *       沒有未核准／未發料的領用單、沒有未處理的「來源已異動」進貨）→ 通過才能月結。
 *       月結時依月加權平均（D3）寫「月結成本調整」異動（數量 0、只調金額），之後該月不能再有任何異動。
 * 反月結：必填原因，每個月份限一次，只能反最近一個已月結月份。
 * 權限：stock_period_close
 */
import { useCallback, useEffect, useState } from 'react'
import { Alert, Button, DatePicker, Input, List, Modal, Space, Table, Tag, Typography, message } from 'antd'
import { LockOutlined, ReloadOutlined, UnlockOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import {
  checkPeriod, closePeriod, errMsg, fetchPeriods, reopenPeriod, type PeriodCheck, type StockPeriodRow,
} from '@/api/stock'

const { Text } = Typography
const money = (v: number | null | undefined) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)

export default function PeriodsTab({ code, canClose }: { code: string; canClose: boolean }) {
  const [rows, setRows] = useState<StockPeriodRow[]>([])
  const [loading, setLoading] = useState(false)
  const [checkFor, setCheckFor] = useState<string | null>(null)
  const [check, setCheck] = useState<PeriodCheck | null>(null)
  const [checking, setChecking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [reopenFor, setReopenFor] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [other, setOther] = useState<Dayjs | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await fetchPeriods(code)).data) } catch (e) { message.error(errMsg(e, '讀取月結狀態失敗')) } finally { setLoading(false) }
  }, [code])
  useEffect(() => { load() }, [load])

  const openCheck = async (period: string) => {
    setCheckFor(period); setCheck(null); setChecking(true)
    try { setCheck((await checkPeriod(code, period)).data) } catch (e) { message.error(errMsg(e, '檢查失敗')) } finally { setChecking(false) }
  }
  const doClose = async () => {
    if (!checkFor) return
    setBusy(true)
    try {
      const r = await closePeriod(code, checkFor)
      message.success(`${checkFor} 已月結；成本調整 ${r.data.revalue_count} 筆，合計 ${money(r.data.revalue_amount)}`)
      setCheckFor(null); load()
    } catch (e) { message.error(errMsg(e, '月結失敗')) } finally { setBusy(false) }
  }
  const doReopen = async () => {
    if (!reopenFor || !reason.trim()) { message.warning('請填反月結原因'); return }
    setBusy(true)
    try { await reopenPeriod(code, reopenFor, reason.trim()); message.success(`${reopenFor} 已反月結`); setReopenFor(null); load() }
    catch (e) { message.error(errMsg(e, '反月結失敗')) } finally { setBusy(false) }
  }

  const latestClosed = rows.filter((r) => r.status === 'closed').map((r) => r.period).sort().pop()

  return (
    <>
      <Space wrap style={{ marginBottom: 12 }}>
        <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
        {canClose && (
          <>
            <DatePicker picker="month" placeholder="其他月份" value={other} onChange={setOther} />
            <Button disabled={!other} onClick={() => other && openCheck(other.format('YYYY-MM'))}>檢查／月結</Button>
          </>)}
        <Text type="secondary">月結後該月不能再新增或作廢任何單據；要更正請在下個月開單，或反月結（每月限一次）。</Text>
      </Space>
      <Table<StockPeriodRow> size="small" rowKey="period" loading={loading} dataSource={rows} pagination={false}
        columns={[
          { title: '月份', dataIndex: 'period', width: 100, render: (v: string) => <b>{v}</b> },
          { title: '狀態', dataIndex: 'status', width: 110, render: (v: string, r) => (v === 'closed'
            ? <Tag color="green" icon={<LockOutlined />}>已月結</Tag>
            : <Tag color={r.reopen_count ? 'orange' : 'default'}>{r.reopen_count ? '已反月結' : '未月結'}</Tag>) },
          { title: '有異動', dataIndex: 'has_moves', width: 80, render: (v: boolean) => (v ? '是' : '—') },
          { title: '月結', key: 'c', width: 200, render: (_: unknown, r) => (r.closed_by ? `${r.closed_by} ${r.closed_at ?? ''}` : '—') },
          { title: '成本調整', key: 'rv', width: 160, render: (_: unknown, r) => (r.closed_at ? `${r.revalue_count} 筆｜${money(r.revalue_amount)}` : '—') },
          { title: '反月結', key: 'ro', render: (_: unknown, r) => (r.reopen_count ? `${r.reopened_by ?? ''}：${r.reopen_reason ?? ''}` : '—') },
          ...(canClose ? [{ title: '', key: 'op', width: 120, render: (_: unknown, r: StockPeriodRow) => (r.status === 'closed'
            ? (r.period === latestClosed && !r.reopen_count
              ? <Button size="small" icon={<UnlockOutlined />} onClick={() => { setReason(''); setReopenFor(r.period) }}>反月結</Button> : null)
            : <Button size="small" type="primary" icon={<LockOutlined />} onClick={() => openCheck(r.period)}>月結</Button>) }] : []),
        ]} />

      <Modal open={!!checkFor} title={`月結 ${checkFor ?? ''}`} width={680} onCancel={() => setCheckFor(null)}
        footer={(
          <Space>
            <Button onClick={() => setCheckFor(null)}>關閉</Button>
            <Button type="primary" icon={<LockOutlined />} disabled={!check?.ok} loading={busy} onClick={doClose}>確認月結</Button>
          </Space>)}>
        {checking && <Text>檢查中…</Text>}
        {check && (check.ok
          ? <Alert type="success" showIcon style={{ marginBottom: 12 }} message="檢查通過，可以月結"
              description="月結會依月加權平均寫入成本調整異動，之後這個月份不能再有任何異動。" />
          : <Alert type="error" showIcon style={{ marginBottom: 12 }} message="還不能月結"
              description={<List size="small" dataSource={check.problems} renderItem={(p) => <List.Item style={{ padding: '2px 0' }}>{p}</List.Item>} />} />)}
        {check && (
          <Table size="small" rowKey="warehouse_id" pagination={false} dataSource={check.warehouses}
            columns={[
              { title: '倉庫', dataIndex: 'warehouse_name' },
              { title: '盤點', dataIndex: 'status', width: 140, render: (v: string) => (
                <Tag color={v === '已盤點' ? 'green' : v === '免盤（空倉）' ? 'default' : 'red'}>{v}</Tag>) },
            ]} />)}
      </Modal>

      <Modal open={!!reopenFor} title={`反月結 ${reopenFor ?? ''}`} onCancel={() => setReopenFor(null)} onOk={doReopen}
        okText="反月結" okButtonProps={{ danger: true }} confirmLoading={busy}>
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message="每個月份只能反月結一次。反月結後可補單或作廢，完成後請再月結（成本調整會自動重算）。" />
        <Input.TextArea rows={3} placeholder="反月結原因（必填，會留紀錄）" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
    </>
  )
}
