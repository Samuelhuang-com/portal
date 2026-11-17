/**
 * 庫存管理 › 庫存 — 補貨建議（Phase 7，2026-11-17，SPEC §10）
 *
 * 可用量（帳上－保留）低於料號安全量（min_stock）的 倉×料號，建議補到上限（沒有上限補到安全量），
 * 換算成採購單位（無條件進位），附近 N 天月均用量與「可撐天數」。
 * 2026-11-17 Samuel 裁示：只做建議清單＋匯出，週採請購單仍由人開。安全量在週採料號主檔設定。
 */
import { useEffect, useState } from 'react'
import { Alert, Button, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { errMsg, fetchReplenishment, type ReplenishRow, type Warehouse } from '@/api/stock'
import { exportRowsToExcel } from '@/utils/exportExcel'

const { Text } = Typography
const num = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: 2 }))

export default function ReplenishmentModal({ code, warehouses, open, onClose }: {
  code: string; warehouses: Warehouse[]; open: boolean; onClose: () => void
}) {
  const [whId, setWhId] = useState<number | undefined>()
  const [days, setDays] = useState(90)
  const [rows, setRows] = useState<ReplenishRow[]>([])
  const [loading, setLoading] = useState(false)
  useEffect(() => {
    if (!open) return
    setLoading(true)
    fetchReplenishment(code, whId, days).then((r) => setRows(r.data.rows)).catch((e) => message.error(errMsg(e, '讀取補貨建議失敗')))
      .finally(() => setLoading(false))
  }, [open, code, whId, days])

  const doExport = () => exportRowsToExcel(rows.map((r) => ({
    倉庫: r.warehouse_name, 部門: r.department_name ?? '', 料號: r.item_code, 品名: r.item_name, 規格: r.spec ?? '', 庫存單位: r.unit ?? '',
    帳上: r.qty, 保留: r.reserved_qty, 可用: r.available, 安全量: r.min_stock, 上限: r.max_stock ?? '',
    建議補貨量: r.suggest_qty, 採購單位: r.purchase_unit ?? '', 換算: r.unit_ratio, 建議採購數: r.suggest_purchase_qty,
    [`月均用量（近${days}天）`]: r.monthly_use, 可撐天數: r.days_left ?? '', 預估金額: r.est_amount, 預設供應商: r.vendor_name ?? '',
  })), { filename: `補貨建議_${code}_${new Date().toISOString().slice(0, 10)}.xlsx`, sheetName: '補貨建議' })

  return (
    <Modal open={open} title="補貨建議" width={1180} onCancel={onClose}
      footer={<Space><Button onClick={onClose}>關閉</Button><Button type="primary" icon={<DownloadOutlined />} disabled={!rows.length} onClick={doExport}>匯出 Excel</Button></Space>}>
      <Alert type="info" showIcon style={{ marginBottom: 12 }}
        message="可用量低於安全量的料號；建議補到上限（沒有上限時補到安全量）。這裡只是建議，請依清單到週採開請購單。安全量／上限在週採料號主檔設定。" />
      <Space wrap style={{ marginBottom: 12 }}>
        <Select allowClear placeholder="全部倉庫" style={{ width: 220 }} value={whId} onChange={setWhId}
          options={warehouses.filter((w) => w.status !== 'inactive').map((w) => ({ value: w.id, label: w.name }))} />
        <Select style={{ width: 160 }} value={days} onChange={setDays}
          options={[30, 60, 90, 180].map((d) => ({ value: d, label: `用量看近 ${d} 天` }))} />
        <Text type="secondary">{`共 ${rows.length} 項｜預估金額 $${rows.reduce((s, r) => s + r.est_amount, 0).toLocaleString()}`}</Text>
      </Space>
      <Table<ReplenishRow> size="small" rowKey={(r) => `${r.warehouse_id}-${r.item_id}`} loading={loading} dataSource={rows}
        pagination={{ pageSize: 50 }} scroll={{ y: 460 }}
        columns={[
          { title: '倉庫', dataIndex: 'warehouse_name', width: 110 },
          { title: '料號', dataIndex: 'item_code', width: 100 },
          { title: '品名', key: 'n', render: (_: unknown, r) => `${r.item_name}${r.spec ? `（${r.spec}）` : ''}` },
          { title: '可用／安全量', key: 'a', width: 120, align: 'right', render: (_: unknown, r) => `${num(r.available)} ／ ${r.min_stock}` },
          { title: '建議補貨', key: 's', width: 120, align: 'right', render: (_: unknown, r) => <b>{`${num(r.suggest_qty)} ${r.unit ?? ''}`}</b> },
          { title: '採購數', key: 'p', width: 110, align: 'right', render: (_: unknown, r) => (
            r.purchase_unit && r.unit_ratio !== 1 ? <Tag color="blue">{`${r.suggest_purchase_qty} ${r.purchase_unit}`}</Tag> : `${r.suggest_purchase_qty} ${r.purchase_unit ?? ''}`) },
          { title: '月均用量', dataIndex: 'monthly_use', width: 90, align: 'right', render: num },
          { title: '可撐天數', dataIndex: 'days_left', width: 90, align: 'right', render: (v: number | null) => (
            v == null ? <Text type="secondary">無領用</Text> : <Text type={v < 7 ? 'danger' : undefined}>{num(v)}</Text>) },
          { title: '預估金額', dataIndex: 'est_amount', width: 100, align: 'right', render: (v: number) => `$${v.toLocaleString()}` },
          { title: '預設供應商', dataIndex: 'vendor_name', width: 140, ellipsis: true, render: (v: string | null) => v || '—' },
        ]} />
    </Modal>
  )
}
