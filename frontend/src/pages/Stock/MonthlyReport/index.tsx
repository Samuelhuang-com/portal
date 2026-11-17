/**
 * 庫存管理 › 進銷存月報（規格 docs/SPEC_stock_management.md §8.3，Phase 5 2026-11-17）
 *
 * 料號一列：期初＋本月進貨／期初開帳／領用／退料／調撥進出／報廢／盤盈虧／月結成本調整＝期末（數量＋金額）。
 * 周轉天數（Phase 7）＝平均庫存金額（期初＋期末）÷2 ÷ 每日領用淨額；本月沒有領用不計。
 * 期初＝月初以前所有異動加總；已月結的月份金額為月加權平均（D3），未月結的月份是即時移動平均。
 * 月份預設為「資料最後一個有異動的月份」（不是今天，CLAUDE.md §8.2 同一原則）。單月選擇不適用 StandardRangePicker（§8.4）。
 * 權限：stock_balance_view
 * 全螢幕（2026-11-17）：沿用戰情 KPI 做法（Fullscreen API＋彈出層掛在容器內，下拉選單在全螢幕中才看得到）
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Button, ConfigProvider, DatePicker, Input, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { DownloadOutlined, FullscreenExitOutlined, FullscreenOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { type Dayjs } from 'dayjs'
import { errMsg, fetchMonthlyReport, fetchWarehouses, type MonthlyReportResp, type Warehouse } from '@/api/stock'
import { exportRowsToExcel } from '@/utils/exportExcel'
import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'

const { Text } = Typography
type Row = MonthlyReportResp['rows'][number]
const n = (v: unknown) => (typeof v === 'number' ? v : 0)
const fmtQ = (v: number) => (v === 0 ? '' : v.toLocaleString(undefined, { maximumFractionDigits: 4 }))
const fmtA = (v: number) => (v === 0 ? '' : `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`)

export default function StockMonthlyReportPage() {
  const { companies, code, setCode, error } = useStockCompany()
  const [period, setPeriod] = useState<Dayjs>(dayjs())
  const [whs, setWhs] = useState<Warehouse[]>([])
  const [whId, setWhId] = useState<number | undefined>()
  const [data, setData] = useState<MonthlyReportResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [showAmt, setShowAmt] = useState(true)
  const anchored = useRef<string>('')   // 每家公司只在第一次載入時跳到「資料最後月份」
  const rootRef = useRef<HTMLDivElement>(null)
  const [isFs, setIsFs] = useState(false)
  useEffect(() => {
    const on = () => setIsFs(!!rootRef.current && document.fullscreenElement === rootRef.current)
    document.addEventListener('fullscreenchange', on)
    return () => document.removeEventListener('fullscreenchange', on)
  }, [])
  const toggleFs = () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined)
    else rootRef.current?.requestFullscreen().catch(() => message.warning('瀏覽器不允許全螢幕'))
  }
  const popup = useCallback(() => rootRef.current ?? document.body, [])

  useEffect(() => {
    if (!code) return
    setWhId(undefined)
    fetchWarehouses(code).then((r) => setWhs(r.data)).catch(() => setWhs([]))
  }, [code])

  useEffect(() => {
    if (!code) return
    let alive = true
    setLoading(true)
    fetchMonthlyReport(code, period.format('YYYY-MM'), whId).then((r) => {
      if (!alive) return
      const last = r.data.last_period
      if (anchored.current !== code) {
        anchored.current = code
        if (last && last !== r.data.period) { setPeriod(dayjs(`${last}-01`)); return }
      }
      setData(r.data)
    }).catch((e) => message.error(errMsg(e, '讀取月報失敗'))).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [code, period, whId])

  const rows = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return (data?.rows ?? []).filter((r) => !kw || `${r.item_code} ${r.item_name}`.toLowerCase().includes(kw))
  }, [data, keyword])

  const cell = (q: number, a: number) => (
    <Space direction="vertical" size={0} style={{ alignItems: 'flex-end', width: '100%' }}>
      <span>{fmtQ(q)}</span>
      {showAmt && <Text type="secondary" style={{ fontSize: 12 }}>{fmtA(a)}</Text>}
    </Space>)

  const cols = data?.columns ?? []
  const columns: ColumnsType<Row> = [
    ...(whId ? [] : [{ title: '倉庫', dataIndex: 'warehouse_name', width: 110, fixed: 'left' as const }]),
    { title: '料號', dataIndex: 'item_code', width: 110, fixed: 'left' },
    { title: '品名', key: 'name', width: 180, fixed: 'left', render: (_: unknown, r) => `${r.item_name}${r.spec ? `（${r.spec}）` : ''}` },
    { title: '單位', dataIndex: 'unit', width: 60 },
    { title: '期初', key: 'open', width: 100, align: 'right', render: (_: unknown, r) => cell(r.open_qty, r.open_amt) },
    ...cols.map((c) => ({
      title: c.label, key: c.key, width: 100, align: 'right' as const,
      render: (_: unknown, r: Row) => cell(n(r[`${c.key}_qty`]), n(r[`${c.key}_amt`])),
    })),
    { title: '期末', key: 'close', width: 110, align: 'right', fixed: 'right',
      render: (_: unknown, r) => <b>{cell(r.close_qty, r.close_amt)}</b> },
    { title: '周轉天數', dataIndex: 'turnover_days', width: 90, align: 'right', fixed: 'right',
      sorter: (a, b) => (a.turnover_days ?? 1e9) - (b.turnover_days ?? 1e9),
      render: (v: number | null) => (v == null ? <Text type="secondary">—</Text> : <Text type={v > 90 ? 'danger' : undefined}>{v.toLocaleString()}</Text>) },
  ]

  const total = (k: string) => rows.reduce((s, r) => s + n(r[k]), 0)
  const doExport = () => {
    if (!data) return
    exportRowsToExcel(rows.map((r) => {
      const o: Record<string, string | number> = { 倉庫: r.warehouse_name, 料號: r.item_code, 品名: r.item_name, 規格: r.spec ?? '', 單位: r.unit ?? '',
        期初數量: r.open_qty, 期初金額: r.open_amt }
      for (const c of cols) { o[`${c.label}數量`] = n(r[`${c.key}_qty`]); o[`${c.label}金額`] = n(r[`${c.key}_amt`]) }
      o['期末數量'] = r.close_qty; o['期末金額'] = r.close_amt; o['周轉天數'] = r.turnover_days ?? ''
      return o
    }), { filename: `進銷存月報_${code}_${data.period}.xlsx`, sheetName: data.period })
  }

  if (error) return <Alert type="error" showIcon message={error} />
  return (
    <ConfigProvider getPopupContainer={popup}>
    <div ref={rootRef} style={isFs ? { background: '#f0f4f8', height: '100vh', overflow: 'auto', padding: 16 } : undefined}>
      <Space wrap style={{ marginBottom: 12 }}>
        <StockCompanySelect companies={companies} value={code} onChange={setCode} />
        <DatePicker picker="month" allowClear={false} value={period} onChange={(d) => d && setPeriod(d)} />
        <Select allowClear placeholder="全部倉庫" style={{ width: 200 }} value={whId} onChange={setWhId}
          options={whs.map((w) => ({ value: w.id, label: w.name }))} />
        <Input.Search allowClear placeholder="料號／品名" style={{ width: 200 }} value={keyword} onChange={(e) => setKeyword(e.target.value)} />
        <Space size={4}><Switch size="small" checked={showAmt} onChange={setShowAmt} /><span>顯示金額</span></Space>
        <Button icon={<ReloadOutlined />} onClick={() => setPeriod((p) => p.clone())} loading={loading}>重新讀取</Button>
        <Button icon={<DownloadOutlined />} onClick={doExport} disabled={!rows.length}>匯出 Excel</Button>
        <Button type={isFs ? 'default' : 'primary'} ghost={!isFs} icon={isFs ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          onClick={toggleFs}>{isFs ? '離開全螢幕' : '全螢幕'}</Button>
        {data && (data.closed ? <Tag color="green">已月結（月加權平均）</Tag> : <Tag color="orange">未月結（即時移動平均）</Tag>)}
      </Space>
      <Table<Row> size="small" rowKey={(r) => `${r.warehouse_id}-${r.item_id}`} loading={loading} dataSource={rows}
        columns={columns} pagination={{ pageSize: 100 }} scroll={{ x: 1500, y: isFs ? 'calc(100vh - 230px)' : 620 }}
        summary={() => (rows.length ? (
          <Table.Summary fixed>
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={whId ? 3 : 4}><b>{`合計金額（${rows.length} 項）`}</b></Table.Summary.Cell>
              <Table.Summary.Cell index={1} align="right">{fmtA(total('open_amt'))}</Table.Summary.Cell>
              {cols.map((c, i) => <Table.Summary.Cell key={c.key} index={i + 2} align="right">{fmtA(total(`${c.key}_amt`))}</Table.Summary.Cell>)}
              <Table.Summary.Cell index={cols.length + 2} align="right"><b>{fmtA(total('close_amt'))}</b></Table.Summary.Cell>
              <Table.Summary.Cell index={cols.length + 3} />
            </Table.Summary.Row>
          </Table.Summary>) : null)} />
      <Text type="secondary" style={{ fontSize: 12 }}>
        期末＝期初＋各欄加總（出庫為負數）。已月結月份的「成本調整」＝月加權平均與平時移動平均的差額。周轉天數＝平均庫存金額 ÷ 每日領用淨額，超過 90 天標紅（囤貨偏多）。
      </Text>
    </div>
    </ConfigProvider>
  )
}
