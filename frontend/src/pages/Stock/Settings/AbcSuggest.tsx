/**
 * 庫存管理 › 庫存主檔設定 › 料號庫存設定 — ABC 分類建議（Phase 7，2026-11-17，SPEC §10）
 *
 * 依近 N 天「領用淨額」排序：累計佔比 80% 以內＝A、95% 以內＝B、其餘＝C（沒有領用＝C）。
 * 只建議，勾選後按「套用」才寫入；ABC 用在盤點頁的「循環盤點（只盤 A 類…）」。
 */
import { useEffect, useState } from 'react'
import { Alert, Button, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import { applyAbc, errMsg, fetchAbcSuggest, type AbcRow } from '@/api/stock'

const { Text } = Typography
const COLOR: Record<string, string> = { A: 'red', B: 'gold', C: 'default' }

export default function AbcSuggestModal({ code, open, onClose, onDone }: { code: string; open: boolean; onClose: () => void; onDone: () => void }) {
  const [days, setDays] = useState(90)
  const [rows, setRows] = useState<AbcRow[]>([])
  const [selected, setSelected] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetchAbcSuggest(code, days).then((r) => {
      setRows(r.data.rows); setSelected(r.data.rows.filter((x) => x.current !== x.suggested).map((x) => x.item_id))
    }).catch((e) => message.error(errMsg(e, '讀取 ABC 建議失敗'))).finally(() => setLoading(false))
  }, [open, code, days])

  const apply = async () => {
    const use = rows.filter((r) => selected.includes(r.item_id))
    if (!use.length) { message.warning('請勾選要套用的料號'); return }
    setSaving(true)
    try {
      const r = await applyAbc(code, use.map((x) => ({ item_id: x.item_id, abc_class: x.suggested })))
      message.success(`已套用 ${r.data.updated} 個料號的 ABC 分類`); onDone()
    } catch (e) { message.error(errMsg(e, '套用失敗')) } finally { setSaving(false) }
  }
  const cnt = (c: string) => rows.filter((r) => r.suggested === c).length

  return (
    <Modal open={open} title="ABC 分類建議" width={900} onCancel={onClose} onOk={apply} confirmLoading={saving}
      okText={`套用勾選（${selected.length}）`}>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        message="依領用淨額排序：累計 80% 以內＝A（每月循環盤點）、95% 以內＝B、其餘＝C。預設只勾選「建議與目前不同」的料號。" />
      <Space style={{ marginBottom: 12 }}>
        <Select style={{ width: 170 }} value={days} onChange={setDays} options={[30, 90, 180, 365].map((d) => ({ value: d, label: `依近 ${d} 天領用` }))} />
        <Text type="secondary">{`A ${cnt('A')}｜B ${cnt('B')}｜C ${cnt('C')}`}</Text>
      </Space>
      <Table<AbcRow> size="small" rowKey="item_id" loading={loading} dataSource={rows} pagination={{ pageSize: 50 }} scroll={{ y: 420 }}
        rowSelection={{ selectedRowKeys: selected, onChange: (k) => setSelected(k as number[]) }}
        columns={[
          { title: '料號', dataIndex: 'item_code', width: 110 },
          { title: '品名', key: 'n', render: (_: unknown, r) => `${r.item_name}${r.spec ? `（${r.spec}）` : ''}` },
          { title: '領用淨額', dataIndex: 'consume_amount', width: 110, align: 'right', render: (v: number) => (v ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—') },
          { title: '佔比', dataIndex: 'share', width: 70, align: 'right', render: (v: number) => (v ? `${(v * 100).toFixed(1)}%` : '—') },
          { title: '累計', dataIndex: 'cum_share', width: 70, align: 'right', render: (v: number) => (v ? `${(v * 100).toFixed(1)}%` : '—') },
          { title: '目前', dataIndex: 'current', width: 60, render: (v: string | null) => (v ? <Tag color={COLOR[v]}>{v}</Tag> : '—') },
          { title: '建議', dataIndex: 'suggested', width: 60, render: (v: string) => <Tag color={COLOR[v]}>{v}</Tag> },
        ]} />
    </Modal>
  )
}
