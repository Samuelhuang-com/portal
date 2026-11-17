import sys, os
root=sys.argv[1]
def ed(rel, reps):
    p=os.path.join(root,rel); s=open(p,encoding='utf-8').read()
    for a,b in reps:
        if s.count(a)!=1: raise SystemExit(f"{rel}: anchor {s.count(a)}: {a[:70]!r}")
        s=s.replace(a,b)
    open(p,'w',encoding='utf-8').write(s); print('ok',rel)

ed('pages/Stock/Balance/index.tsx',[
 ("import { ReloadOutlined } from '@ant-design/icons'","import { ReloadOutlined, ShoppingOutlined } from '@ant-design/icons'"),
 ("import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'\n",
  "import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'\nimport ReplenishmentModal from './Replenishment'\n"),
 ("  const [cardOpen, setCardOpen] = useState(false)\n","  const [cardOpen, setCardOpen] = useState(false)\n  const [repOpen, setRepOpen] = useState(false)\n"),
 ("""          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
          <Text type="secondary">共 {data?.rows.length ?? 0} 列""","""          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新整理</Button>
          <Button icon={<ShoppingOutlined />} onClick={() => setRepOpen(true)}>補貨建議</Button>
          <Text type="secondary">共 {data?.rows.length ?? 0} 列"""),
 ("""      </Drawer>
    </div>
  )
}""","""      </Drawer>
      {code && <ReplenishmentModal code={code} warehouses={warehouses} open={repOpen} onClose={() => setRepOpen(false)} />}
    </div>
  )
}"""),
])
ed('pages/Stock/Settings/index.tsx',[
 ("import PeriodsTab from './Periods'\n","import PeriodsTab from './Periods'\nimport AbcSuggestModal from './AbcSuggest'\n"),
 ("  const [editing, setEditing] = useState<StockItem | null>(null)\n","  const [editing, setEditing] = useState<StockItem | null>(null)\n  const [abcOpen, setAbcOpen] = useState(false)\n"),
 ("""    { title: '安全量', key: 'minmax', width: 90,""","""    { title: 'ABC', dataIndex: 'abc_class', width: 60, render: (v: string | null) => (v ? <Tag color={v === 'A' ? 'red' : v === 'B' ? 'gold' : 'default'}>{v}</Tag> : '—') },
    { title: '安全量', key: 'minmax', width: 90,"""),
 ("""          <Text type="secondary">共 {rows.length} 個料號，納入庫存 {stockCount} 個</Text>""",
  """          {canManage && <Button onClick={() => setAbcOpen(true)}>ABC 分類建議</Button>}
          <Text type="secondary">共 {rows.length} 個料號，納入庫存 {stockCount} 個</Text>"""),
])
# ItemsTab return fragment end: add modal before the 2nd '    </>' (ItemsTab). Do via targeted anchor on the abc form item region end.
p=os.path.join(root,'pages/Stock/Settings/index.tsx'); s=open(p,encoding='utf-8').read()
i=s.index('<Form.Item name="abc_class" label="ABC 分類（循環盤點用，可空白）">')
j=s.index('\n    </>', i)
s=s[:j]+"\n      <AbcSuggestModal code={code} open={abcOpen} onClose={() => setAbcOpen(false)} onDone={() => { setAbcOpen(false); load() }} />"+s[j:]
open(p,'w',encoding='utf-8').write(s); print('ok abc modal')

ed('pages/Stock/Counts/index.tsx',[
 ("""import {
  Alert, Button, Checkbox, DatePicker, Descriptions, Drawer, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch,
  Table, Tag, Tooltip, Typography, message,
} from 'antd'""","""import {
  Alert, Button, Checkbox, DatePicker, Descriptions, Drawer, Input, InputNumber, Modal, Popconfirm, Radio, Select, Space, Switch,
  Table, Tag, Tooltip, Typography, message,
} from 'antd'"""),
 ("""  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => {
    if (!open) return
    setDate(dayjs()); setNote('')""","""  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [mode, setMode] = useState<'full' | 'cycle'>('full')
  const [abc, setAbc] = useState<string[]>(['A'])
  useEffect(() => {
    if (!open) return
    setDate(dayjs()); setNote(''); setMode('full'); setAbc(['A'])"""),
 ("""    if (!ids.length) { message.warning('請選倉庫'); return }
    setSaving(true)
    try {
      const r = await createCounts(code, { warehouse_ids: ids, count_date: date.format('YYYY-MM-DD'), note: note || null })""",
  """    if (!ids.length) { message.warning('請選倉庫'); return }
    if (mode === 'cycle' && !abc.length) { message.warning('循環盤點請選 ABC 類別'); return }
    setSaving(true)
    try {
      const r = await createCounts(code, { warehouse_ids: ids, count_date: date.format('YYYY-MM-DD'), note: note || null,
        abc_classes: mode === 'cycle' ? abc : null })"""),
 ("""        <Space><Text>盤點日</Text><DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} /></Space>""",
  """        <Space wrap>
          <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)} optionType="button"
            options={[{ value: 'full', label: '月底全盤' }, { value: 'cycle', label: '循環盤點（抽盤）' }]} />
          {mode === 'cycle' && <Checkbox.Group value={abc} onChange={(v) => setAbc(v as string[])} options={['A', 'B', 'C'].map((x) => ({ value: x, label: `${x} 類` }))} />}
        </Space>
        {mode === 'cycle' && <Text type="secondary">循環盤點只盤選定 ABC 類的料號（在「庫存主檔設定 › 料號庫存設定」設定），屬於額外抽盤，月結仍需月底全盤。</Text>}
        <Space><Text>盤點日</Text><DatePicker value={date} onChange={(d) => d && setDate(d)} allowClear={false} /></Space>"""),
 ("""          <Tag color={STATUS_COLOR[doc.status]}>{doc.status_label}</Tag>{doc.blind && <Tag>盲盤</Tag>}""",
  """          <Tag color={STATUS_COLOR[doc.status]}>{doc.status_label}</Tag>{doc.blind && <Tag>盲盤</Tag>}
          {doc.count_type === 'cycle' && <Tag color="purple">{`循環盤點 ${doc.abc_classes ?? ''}`}</Tag>}"""),
 ("""            <Space size={2}><Tag color={STATUS_COLOR[r.status]}>{r.status_label}</Tag>{r.blind && <Tag>盲盤</Tag>}</Space>) },""",
  """            <Space size={2} wrap><Tag color={STATUS_COLOR[r.status]}>{r.status_label}</Tag>{r.blind && <Tag>盲盤</Tag>}
              {r.count_type === 'cycle' && <Tag color="purple">{`循環 ${r.abc_classes ?? ''}`}</Tag>}</Space>) },"""),
 ("""          { title: '狀態', key: 's', width: 140, render""","""          { title: '狀態', key: 's', width: 190, render"""),
])
ed('pages/Stock/MonthlyReport/index.tsx',[
 (""" * 期初＝月初以前所有異動加總；""",""" * 周轉天數（Phase 7）＝平均庫存金額（期初＋期末）÷2 ÷ 每日領用淨額；本月沒有領用不計。
 * 期初＝月初以前所有異動加總；"""),
 ("""    { title: '期末', key: 'close', width: 110, align: 'right', fixed: 'right',
      render: (_: unknown, r) => <b>{cell(r.close_qty, r.close_amt)}</b> },""","""    { title: '期末', key: 'close', width: 110, align: 'right', fixed: 'right',
      render: (_: unknown, r) => <b>{cell(r.close_qty, r.close_amt)}</b> },
    { title: '周轉天數', dataIndex: 'turnover_days', width: 90, align: 'right', fixed: 'right',
      sorter: (a, b) => (a.turnover_days ?? 1e9) - (b.turnover_days ?? 1e9),
      render: (v: number | null) => (v == null ? <Text type="secondary">—</Text> : <Text type={v > 90 ? 'danger' : undefined}>{v.toLocaleString()}</Text>) },"""),
 ("""      o['期末數量'] = r.close_qty; o['期末金額'] = r.close_amt""","""      o['期末數量'] = r.close_qty; o['期末金額'] = r.close_amt; o['周轉天數'] = r.turnover_days ?? ''"""),
 ("""              <Table.Summary.Cell index={cols.length + 2} align="right"><b>{fmtA(total('close_amt'))}</b></Table.Summary.Cell>""",
  """              <Table.Summary.Cell index={cols.length + 2} align="right"><b>{fmtA(total('close_amt'))}</b></Table.Summary.Cell>
              <Table.Summary.Cell index={cols.length + 3} />"""),
 ("""        期末＝期初＋各欄加總（出庫為負數）。已月結月份的「成本調整」＝月加權平均與平時移動平均的差額。""",
  """        期末＝期初＋各欄加總（出庫為負數）。已月結月份的「成本調整」＝月加權平均與平時移動平均的差額。周轉天數＝平均庫存金額 ÷ 每日領用淨額，超過 90 天標紅（囤貨偏多）。"""),
])
