/**
 * 庫存管理 › 庫存（規格 docs/SPEC_stock_management.md §8.3，Phase 2 2026-11-17）
 *
 * 庫存總覽：公司 × 倉 × 料號（帳上數、保留數、可用數、平均單價、庫存金額、提醒）
 * 點列 → 料號庫存卡 Drawer（該倉該料號的所有異動，逐筆結存）
 * 進銷存月報於 Phase 5（月結）加入。
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Col, Descriptions, Drawer, Input, Row, Select, Space, Statistic, Switch, Table, Tag, Typography, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  errMsg, fetchBalance, fetchCategories, fetchStockCard, fetchWarehouses,
  type BalanceResp, type BalanceRow, type StockCardMove, type StockCardResp, type Warehouse,
} from '@/api/stock'
import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'

const { Text } = Typography
const num = (v: number | null | undefined, d = 2) => (v == null ? '—' : v.toLocaleString(undefined, { maximumFractionDigits: d }))
const money = (v: number | null | undefined) => (v == null ? '—' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)

export default function StockBalancePage() {
  const { companies, code, setCode, error } = useStockCompany()
  const [warehouses, setWarehouses] = useState<Warehouse[]>([])
  const [categories, setCategories] = useState<{ id: number; label: string }[]>([])
  const [warehouseId, setWarehouseId] = useState<number | undefined>()
  const [categoryId, setCategoryId] = useState<number | undefined>()
  const [keyword, setKeyword] = useState('')
  const [lowOnly, setLowOnly] = useState(false)
  const [deadOnly, setDeadOnly] = useState(false)
  const [data, setData] = useState<BalanceResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [card, setCard] = useState<StockCardResp | null>(null)
  const [cardOpen, setCardOpen] = useState(false)

  useEffect(() => {
    if (!code) return
    setWarehouseId(undefined); setCategoryId(undefined)
    fetchWarehouses(code).then((r) => setWarehouses(r.data)).catch(() => setWarehouses([]))
    fetchCategories(code).then((r) => setCategories(r.data)).catch(() => setCategories([]))
  }, [code])

  const load = useCallback(async () => {
    if (!code) return
    setLoading(true)
    try {
      const r = await fetchBalance(code, {
        warehouse_id: warehouseId, category_id: categoryId, keyword: keyword.trim() || undefined,
        low_only: lowOnly || undefined, dead_only: deadOnly || undefined,
      })
      setData(r.data)
    } catch (e) {
      message.error(errMsg(e, '讀取庫存失敗'))
    } finally {
      setLoading(false)
    }
  }, [code, warehouseId, categoryId, keyword, lowOnly, deadOnly])
  useEffect(() => { load() }, [code, warehouseId, categoryId, lowOnly, deadOnly]) // eslint-disable-line react-hooks/exhaustive-deps

  const openCard = async (r: BalanceRow) => {
    setCardOpen(true); setCard(null)
    try {
      const res = await fetchStockCard(code, r.warehouse_id, r.item_id)
      setCard(res.data)
    } catch (e) {
      message.error(errMsg(e, '讀取庫存卡失敗'))
    }
  }

  const columns: ColumnsType<BalanceRow> = useMemo(() => [
    { title: '倉庫', dataIndex: 'warehouse_name', width: 120,
      render: (v: string, r) => <Space size={4}>{v}{r.warehouse_status === 'counting' && <Tag color="orange">盤點中</Tag>}</Space> },
    { title: '料號', dataIndex: 'item_code', width: 120 },
    { title: '品名', dataIndex: 'item_name', ellipsis: true,
      render: (v: string, r) => <Space direction="vertical" size={0}><span>{v}</span>{r.spec && <Text type="secondary" style={{ fontSize: 12 }}>{r.spec}</Text>}</Space> },
    { title: '類別', dataIndex: 'category', width: 180, ellipsis: true, render: (v: string) => v || '—' },
    { title: '單位', dataIndex: 'unit', width: 60, render: (v: string | null) => v || '—' },
    { title: '帳上數', dataIndex: 'qty', width: 90, align: 'right', render: (v: number) => <b>{num(v, 4)}</b>,
      sorter: (a, b) => a.qty - b.qty },
    { title: '保留', dataIndex: 'reserved_qty', width: 70, align: 'right', render: (v: number) => (v ? num(v, 4) : '—') },
    { title: '可用', dataIndex: 'available_qty', width: 90, align: 'right', render: (v: number) => num(v, 4) },
    { title: '安全量', key: 'minmax', width: 90, align: 'right',
      render: (_: unknown, r) => (r.min_stock == null && r.max_stock == null ? '—' : `${r.min_stock ?? '—'}～${r.max_stock ?? '—'}`) },
    { title: '平均單價', dataIndex: 'avg_cost', width: 100, align: 'right', render: money },
    { title: '庫存金額', dataIndex: 'amount', width: 110, align: 'right', render: money, sorter: (a, b) => a.amount - b.amount },
    { title: '最後異動', dataIndex: 'last_move_at', width: 100, render: (v: string | null) => v || '—' },
    { title: '提醒', key: 'flags', width: 150,
      render: (_: unknown, r) => (
        <Space size={2} wrap>
          {r.is_low && <Tag color="red">低於安全量</Tag>}
          {r.is_over && <Tag color="purple">超過上限</Tag>}
          {r.is_dead && <Tag color="default">呆滯</Tag>}
        </Space>
      ) },
  ], [])

  const cardColumns: ColumnsType<StockCardMove> = [
    { title: '日期', dataIndex: 'moved_at', width: 95 },
    { title: '類型', dataIndex: 'move_type_label', width: 80, render: (v: string, m) => <Tag color={(m.in_qty ?? 0) > 0 ? 'green' : 'volcano'}>{v}</Tag> },
    { title: '單號', dataIndex: 'source_no', width: 140, render: (v: string | null) => v || '—' },
    { title: '入', dataIndex: 'in_qty', width: 70, align: 'right', render: (v: number | null) => (v == null ? '' : num(v, 4)) },
    { title: '出', dataIndex: 'out_qty', width: 70, align: 'right', render: (v: number | null) => (v == null ? '' : num(v, 4)) },
    { title: '結存', dataIndex: 'balance_qty', width: 80, align: 'right', render: (v: number) => <b>{num(v, 4)}</b> },
    { title: '單價', dataIndex: 'unit_cost', width: 80, align: 'right', render: money },
    { title: '結存金額', dataIndex: 'balance_amount', width: 100, align: 'right', render: money },
  ]

  if (error) return <Alert type="error" showIcon message={error} />

  const s = data?.summary
  return (
    <div>
      <Row gutter={12} style={{ marginBottom: 12 }}>
        <Col span={6}><Card size="small"><Statistic title="料號數" value={s?.items ?? 0} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="庫存金額（未稅）" value={s?.amount ?? 0} prefix="$" precision={0} /></Card></Col>
        <Col span={6}><Card size="small" hoverable onClick={() => setLowOnly((v) => !v)} style={{ borderColor: lowOnly ? '#1B3A5C' : undefined }}>
          <Statistic title="低於安全量" value={s?.low ?? 0} valueStyle={{ color: (s?.low ?? 0) > 0 ? '#cf1322' : undefined }} /></Card></Col>
        <Col span={6}><Card size="small" hoverable onClick={() => setDeadOnly((v) => !v)} style={{ borderColor: deadOnly ? '#1B3A5C' : undefined }}>
          <Statistic title={`呆滯料（${data?.dead_days ?? 90} 天無異動）`} value={s?.dead ?? 0} /></Card></Col>
      </Row>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <StockCompanySelect companies={companies} value={code} onChange={setCode} />
          <Select allowClear placeholder="倉庫（全部）" style={{ width: 180 }} value={warehouseId} onChange={setWarehouseId}
            options={warehouses.map((w) => ({ value: w.id, label: w.status === 'inactive' ? `${w.name}（停用）` : w.name }))} />
          <Select allowClear showSearch optionFilterProp="label" placeholder="類別" style={{ width: 240 }} value={categoryId} onChange={setCategoryId}
            options={categories.map((c) => ({ value: c.id, label: c.label }))} />
          <Input.Search allowClear placeholder="料號／品名" style={{ width: 200 }} value={keyword}
            onChange={(e) => setKeyword(e.target.value)} onSearch={load} />
          <Space size={4}><Switch size="small" checked={lowOnly} onChange={setLowOnly} /><span>只看低於安全量</span></Space>
          <Space size={4}><Switch size="small" checked={deadOnly} onChange={setDeadOnly} /><span>只看呆滯</span></Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
          <Text type="secondary">共 {data?.rows.length ?? 0} 列{data?.data_end ? `｜最後異動 ${data.data_end}` : ''}</Text>
        </Space>
      </Card>
      {warehouses.length === 0 && !loading && (
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
          message="這家公司還沒有倉庫。請到「庫存管理 › 庫存主檔設定」建立倉庫並完成期初開帳。" />
      )}
      <Table<BalanceRow> size="small" rowKey={(r) => `${r.warehouse_id}-${r.item_id}`} loading={loading}
        dataSource={data?.rows ?? []} columns={columns} pagination={{ pageSize: 50, showSizeChanger: false }}
        onRow={(r) => ({ onClick: () => openCard(r), style: { cursor: 'pointer' } })} />

      <Drawer open={cardOpen} width={640} onClose={() => { setCardOpen(false); setCard(null) }}
        title={card ? (
          <Space>
            <Tag color="blue">{card.warehouse.name}</Tag>
            <span>{`料號庫存卡：${card.item.item_code}`}</span>
          </Space>
        ) : '載入中…'}>
        {card && (
          <>
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="品名"><b>{card.item.item_name}</b></Descriptions.Item>
              <Descriptions.Item label="規格">{card.item.spec || '—'}</Descriptions.Item>
              <Descriptions.Item label="倉庫部門">{card.warehouse.department_name || '—'}</Descriptions.Item>
              <Descriptions.Item label="帳上數">{card.balance ? `${num(card.balance.qty, 4)} ${card.item.unit ?? ''}` : '—'}</Descriptions.Item>
              <Descriptions.Item label="保留數">{card.balance ? num(card.balance.reserved_qty, 4) : '—'}</Descriptions.Item>
              <Descriptions.Item label="平均單價">{money(card.balance?.avg_cost)}</Descriptions.Item>
              <Descriptions.Item label="庫存金額"><b>{money(card.balance?.amount)}</b></Descriptions.Item>
              <Descriptions.Item label="安全量">{card.item.min_stock ?? '—'}～{card.item.max_stock ?? '—'}</Descriptions.Item>
            </Descriptions>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>異動明細（{card.moves.length} 筆）</div>
            <Table<StockCardMove> size="small" rowKey="id" dataSource={card.moves} columns={cardColumns}
              pagination={false} scroll={{ y: 420 }} />
          </>
        )}
      </Drawer>
    </div>
  )
}
