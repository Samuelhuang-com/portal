/**
 * 關聯商場報修單挑選 Modal（領用單／雜收單用；來源：商場工務報修 報修清單總表）
 * 查詢條件：發生時間區間（StandardRangePicker）、報修編號、關鍵字（標題／報修人／房號／類型／樓層）
 * 勾選列＝關聯；點列本身開 RepairDrawer 看明細（勾選框點擊不開 Drawer）
 */
import { useEffect, useState } from 'react'
import { Button, Input, Modal, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import StandardRangePicker, { type StandardRange } from '@/components/StandardRangePicker'
import { errMsg, fetchRepairSearch, type RepairCase, type RepairLink, type RepairSearchParams } from '@/api/stock'
import RepairDrawer from './RepairDrawer'

const { Text } = Typography

const toLink = (c: RepairCase): RepairLink => ({ ragic_id: c.ragic_id, case_no: c.case_no, title: c.title, occurred_at: c.occurred_at })

export default function RepairPicker({ code, open, initial, onClose, onConfirm }: {
  code: string; open: boolean; initial: RepairLink[]; onClose: () => void; onConfirm: (links: RepairLink[]) => void
}) {
  const [kw, setKw] = useState('')
  const [caseNo, setCaseNo] = useState('')
  const [range, setRange] = useState<StandardRange>(null)
  const [rows, setRows] = useState<RepairCase[]>([])
  const [loading, setLoading] = useState(false)
  // 已勾選（含不在本次查詢結果中的項目，切換查詢不會丟失）
  const [picked, setPicked] = useState<Map<string, RepairLink>>(new Map())
  const [viewId, setViewId] = useState<string | null>(null)

  const query = async (p: RepairSearchParams) => {
    setLoading(true)
    try {
      const r = await fetchRepairSearch(code, { limit: 200, ...p })
      setRows(r.data)
    } catch (e) {
      message.error(errMsg(e, '查詢報修單失敗'))
    } finally {
      setLoading(false)
    }
  }

  const search = () => query({
    keyword: kw.trim() || undefined,
    case_no: caseNo.trim() || undefined,
    ...(range ? { start: range[0].format('YYYY-MM-DD'), end: range[1].format('YYYY-MM-DD') } : {}),
  })

  useEffect(() => {
    if (!open) return
    setPicked(new Map(initial.map((l) => [l.ragic_id, l])))
    setKw('')
    setCaseNo('')
    setRange(null)
    void query({ limit: 200 })
    // 只在開啟時載入一次；之後由使用者按「查詢」
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const setOne = (c: RepairCase, on: boolean) => setPicked((m) => {
    const n = new Map(m)
    if (on) n.set(c.ragic_id, toLink(c))
    else n.delete(c.ragic_id)
    return n
  })
  const removeId = (id: string) => setPicked((m) => {
    const n = new Map(m)
    n.delete(id)
    return n
  })

  const cols: ColumnsType<RepairCase> = [
    { title: '報修編號', dataIndex: 'case_no', width: 130 },
    { title: '發生時間', dataIndex: 'occurred_at', width: 110, render: (v: string | null) => v ?? '—' },
    { title: '報修內容', dataIndex: 'title', ellipsis: true },
    { title: '類型', dataIndex: 'repair_type', width: 100, render: (v: string | null) => v ?? '—' },
    { title: '樓層／房號', key: 'loc', width: 130, render: (_: unknown, c: RepairCase) => [c.floor, c.room_no].filter(Boolean).join(' ') || '—' },
    { title: '處理狀況', dataIndex: 'status', width: 100, render: (v: string | null) => (v ? <Tag>{v}</Tag> : '—') },
  ]

  return (
    <Modal open={open} title="關聯商場報修單" width={1000} onCancel={onClose}
      okText={`加入關聯（已選 ${picked.size} 筆）`} onOk={() => onConfirm([...picked.values()])}>
      <Space wrap style={{ marginBottom: 12 }}>
        <StandardRangePicker value={range} onChange={setRange} />
        <Input placeholder="報修編號" style={{ width: 160 }} value={caseNo} allowClear
          onChange={(e) => setCaseNo(e.target.value)} onPressEnter={search} />
        <Input placeholder="報修內容／標題／報修人／房號／類型" style={{ width: 320 }} value={kw} allowClear
          onChange={(e) => setKw(e.target.value)} onPressEnter={search} />
        <Button onClick={search} loading={loading}>查詢</Button>
      </Space>
      <Space wrap style={{ marginBottom: 8 }}>
        <Text>已選：</Text>
        {picked.size === 0 && <Text type="secondary">尚未選擇</Text>}
        {[...picked.values()].map((l) => (
          <Tag key={l.ragic_id} color="orange" closable onClose={() => removeId(l.ragic_id)}>
            {`${l.case_no ?? l.ragic_id}｜${l.title ?? ''}`}
          </Tag>))}
      </Space>
      <Table<RepairCase> size="small" rowKey="ragic_id" loading={loading} dataSource={rows} columns={cols}
        pagination={{ pageSize: 20 }}
        rowSelection={{
          selectedRowKeys: [...picked.keys()],
          onSelect: (rec, selected) => setOne(rec, selected),
          onSelectAll: (selected, _all, changeRows) => setPicked((m) => {
            const n = new Map(m)
            changeRows.forEach((c) => (selected ? n.set(c.ragic_id, toLink(c)) : n.delete(c.ragic_id)))
            return n
          }),
        }}
        onRow={(r) => ({
          onClick: (e) => {
            // 點勾選框不開 Drawer
            if ((e.target as HTMLElement).closest('.ant-checkbox-wrapper')) return
            setViewId(r.ragic_id)
          },
          style: { cursor: 'pointer' },
        })} />
      <RepairDrawer code={code} ragicId={viewId} onClose={() => setViewId(null)} />
    </Modal>
  )
}
