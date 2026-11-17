/**
 * 庫存管理 › 領用單 — 料號 QR 標籤列印（Phase 4b，2026-11-17，SPEC §7.4）
 *
 * QR 內容＝手機領用頁網址（/m/stock/issue?co=…&wh=…&item=料號）。
 * 用手機「內建相機」掃描就會開啟領用頁並帶出這個料號 —— 不需要網頁開相機，
 * 所以在 HTTP（正式區目前沒有 HTTPS）也能用，也不用裝 App。
 *
 * 標籤網址的開頭（主機位址）可改：倉管若在伺服器本機用 127.0.0.1 開 Portal，
 * 預設值會是手機連不到的位址，所以要改成手機能連到的網址（記在這台電腦的瀏覽器）。
 * 列印：A4、每列 3 張；用瀏覽器列印（可另存 PDF）。
 */
import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { Alert, Button, Input, InputNumber, Modal, QRCode, Select, Space, Table, Typography, message } from 'antd'
import { PrinterOutlined } from '@ant-design/icons'
import { errMsg, fetchAvailable, mobileIssueUrl, type AvailableItem, type IssueMeta } from '@/api/stock'

const { Text } = Typography
const BASE_KEY = 'stock_qr_base'

const PRINT_CSS = `
.stock-qr-print { display: none; }
@media print {
  @page { size: A4; margin: 8mm; }
  body > *:not(.stock-qr-print) { display: none !important; }
  .stock-qr-print { display: block !important; }
  .stock-qr-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm; }
  .stock-qr-label { border: 0.3mm dashed #999; padding: 2mm; height: 40mm; display: flex; gap: 2mm; align-items: center;
    page-break-inside: avoid; break-inside: avoid; font-family: sans-serif; overflow: hidden; }
  .stock-qr-label .t { font-size: 10pt; font-weight: 700; line-height: 1.2; }
  .stock-qr-label .s { font-size: 8pt; color: #333; line-height: 1.25; }
}`

function readBase(): string {
  try { return localStorage.getItem(BASE_KEY) || window.location.origin } catch { return window.location.origin }
}

interface Row extends AvailableItem { copies: number }

export default function QrLabelsModal({ code, meta, open, onClose }: { code: string; meta: IssueMeta; open: boolean; onClose: () => void }) {
  const whOptions = meta.can_post ? meta.all_warehouses : meta.my_warehouses
  const [whId, setWhId] = useState<number | undefined>()
  const [rows, setRows] = useState<Row[]>([])
  const [selected, setSelected] = useState<number[]>([])
  const [loading, setLoading] = useState(false)
  const [base, setBase] = useState(readBase)

  useEffect(() => {
    if (open && !whId && whOptions.length === 1) setWhId(whOptions[0].id)
  }, [open, whId, whOptions])
  useEffect(() => {
    if (!open || !whId) { setRows([]); return }
    setLoading(true)
    fetchAvailable(code, whId, undefined, true)
      .then((r) => { setRows(r.data.map((x) => ({ ...x, copies: 1 }))); setSelected(r.data.map((x) => x.item_id)) })
      .catch((e) => message.error(errMsg(e, '讀取料號失敗')))
      .finally(() => setLoading(false))
  }, [open, code, whId])

  const host = useMemo(() => { try { return new URL(base).hostname } catch { return '' } }, [base])
  const badBase = !host || ['localhost', '127.0.0.1', '::1'].includes(host)
  const whName = whOptions.find((w) => w.id === whId)?.name ?? ''
  const labels = rows.filter((r) => selected.includes(r.item_id)).flatMap((r) => Array.from({ length: Math.max(1, r.copies) }, () => r))

  const doPrint = () => {
    if (!labels.length) { message.warning('請勾選要列印的料號'); return }
    if (badBase) { message.warning('標籤網址要填手機連得到的位址'); return }
    try { localStorage.setItem(BASE_KEY, base) } catch { /* ignore */ }
    // 標籤在視窗開著時就已畫好（螢幕上隱藏、只在列印時顯示），不依賴 window.print 是否同步（Safari 為非同步）
    window.print()
  }

  return (
    <>
      <Modal open={open} title="列印料號 QR 標籤" width={860} onCancel={onClose}
        footer={(
          <Space>
            <Text type="secondary">{`共 ${labels.length} 張`}</Text>
            <Button onClick={onClose}>關閉</Button>
            <Button type="primary" icon={<PrinterOutlined />} onClick={doPrint} disabled={!labels.length}>列印</Button>
          </Space>)}>
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
          message="貼在貨架或物品上；同仁用手機內建相機掃描，就會開啟手機領用頁並帶出這個料號（需先登入 Portal）。" />
        <Space wrap style={{ marginBottom: 12 }}>
          <Select placeholder="倉庫" style={{ width: 240 }} value={whId} onChange={setWhId}
            options={whOptions.map((w) => ({ value: w.id, label: w.department_name ? `${w.name}（${w.department_name}）` : w.name }))} />
          <Input addonBefore="標籤網址" style={{ width: 380 }} value={base} onChange={(e) => setBase(e.target.value)}
            status={badBase ? 'error' : undefined} placeholder="http://60.248.96.78:8000" />
        </Space>
        {badBase && <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message="目前的網址手機連不到（本機位址）。請改成手機能開啟 Portal 的網址，例如正式區的對外網址。" />}
        <Table<Row> size="small" rowKey="item_id" loading={loading} dataSource={rows} pagination={false} scroll={{ y: 380 }}
          rowSelection={{ selectedRowKeys: selected, onChange: (k) => setSelected(k as number[]) }}
          columns={[
            { title: '料號', dataIndex: 'item_code', width: 120 },
            { title: '品名', key: 'name', render: (_: unknown, r) => `${r.item_name}${r.spec ? `（${r.spec}）` : ''}` },
            { title: '單位', dataIndex: 'unit', width: 70 },
            { title: '目前可用', dataIndex: 'available', width: 90, align: 'right' },
            { title: '張數', key: 'copies', width: 90, render: (_: unknown, r) => (
              <InputNumber size="small" min={1} max={50} value={r.copies} style={{ width: 70 }}
                onChange={(v) => setRows((rs) => rs.map((x) => (x.item_id === r.item_id ? { ...x, copies: v ?? 1 } : x)))} />) },
          ]} />
      </Modal>
      {open && createPortal(
        <div className="stock-qr-print">
          <style>{PRINT_CSS}</style>
          {whId && !badBase && (
            <div className="stock-qr-grid">
              {labels.map((r, i) => (
                <div className="stock-qr-label" key={`${r.item_id}-${i}`}>
                  <QRCode value={mobileIssueUrl(base, code, whId, r.item_code)} size={118} type="svg" bordered={false} />
                  <div>
                    <div className="t">{r.item_name}</div>
                    {r.spec && <div className="s">{r.spec}</div>}
                    <div className="s">{`料號 ${r.item_code}`}</div>
                    <div className="s">{`單位 ${r.unit ?? '—'}｜${whName}`}</div>
                  </div>
                </div>))}
            </div>)}
        </div>,
        document.body)}
    </>
  )
}
