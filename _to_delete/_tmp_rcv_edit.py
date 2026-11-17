import sys, os
root = sys.argv[1]
def ed(rel, reps):
    p = os.path.join(root, rel); s = open(p, encoding='utf-8').read()
    for a, b in reps:
        if s.count(a) != 1:
            raise SystemExit(f"{rel}: anchor count {s.count(a)}: {a[:70]!r}")
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8').write(s); print("ok", rel)

ed('api/stock.ts', [("  status_reason: string | null\n", "  status_reason: string | null\n  marked_by?: string | null\n")])

R = 'pages/Stock/Receipts/index.tsx'
ed(R, [
 # 檔頭說明
 (""" * TAB「進貨單」：已過帳的進貨單，可作廢（反向異動、回補可匯入量）
 */""", """ * TAB「不入庫」：確認不入庫／開帳前不入庫／已對應採購單的 Ragic 品項（2026-11-17 從待匯入清單拆出），可改回待確認
 * TAB「進貨單」：已過帳的進貨單，可作廢（反向異動、回補可匯入量）
 * 每列可直接「確認入庫」「確認不入庫」「開帳前」（2026-11-17），也可勾選多筆批次處理
 */"""),
 ("const OPEN = ['pending', 'partial']\n",
  "const OPEN = ['pending', 'partial']\nconst CLOSED = ['non_stock', 'pre_opening', 'linked_po']\nconst REVERTIBLE = ['non_stock', 'pre_opening']\ntype ImportMode = 'open' | 'closed'\n"),
 # props
 ("function ImportsTab({ code, canConfirm, onChanged }: { code: string; canConfirm: boolean; onChanged: () => void }) {",
  "function ImportsTab({ code, canConfirm, onChanged, mode, version }: {\n  code: string; canConfirm: boolean; onChanged: () => void; mode: ImportMode; version: number\n}) {"),
 ("  const [status, setStatus] = useState<string[]>(OPEN)\n",
  "  const [status, setStatus] = useState<string[]>(mode === 'open' ? OPEN : CLOSED)\n"),
 ("  const [confirmOpen, setConfirmOpen] = useState(false)\n",
  "  const [confirmLines, setConfirmLines] = useState<ImportLine[] | null>(null)\n"),
 ("  const [markOpen, setMarkOpen] = useState<'non_stock' | 'pre_opening' | null>(null)\n",
  "  const [markOpen, setMarkOpen] = useState<'non_stock' | 'pre_opening' | null>(null)\n  const [markIds, setMarkIds] = useState<number[]>([])\n"),
 ("""      const r = await fetchImports(code, {
        status, source_type""", """      const r = await fetchImports(code, {
        status: status.length ? status : (mode === 'open' ? [...OPEN, 'done'] : CLOSED), source_type"""),
 ("  useEffect(() => { load() }, [code, status, sourceType, dept, range, onlyChanged]) // eslint-disable-line react-hooks/exhaustive-deps",
  "  useEffect(() => { load() }, [code, status, sourceType, dept, range, onlyChanged, version]) // eslint-disable-line react-hooks/exhaustive-deps"),
 ("      const r = await markImports(code, { line_ids: selected, status: markOpen,",
  "      const r = await markImports(code, { line_ids: markIds, status: markOpen,"),
 ("""  const doRevert = async (id: number) => {
    try { await markImports(code, { line_ids: [id], status: 'pending' }); message.success('已改回待確認'); load(); onChanged() }
    catch (e) { message.error(errMsg(e, '操作失敗')) }
  }""", """  const doRevert = async (ids: number[]) => {
    try {
      const r = await markImports(code, { line_ids: ids, status: 'pending' })
      message.success(`已改回待確認 ${r.data.updated} 筆，請到「待匯入清單」處理`); load(); onChanged()
    } catch (e) { message.error(errMsg(e, '操作失敗')) }
  }
  const openMark = (kind: 'non_stock' | 'pre_opening', ids: number[]) => {
    setMarkIds(ids); setMarkReason(''); setRememberNs(false); setMarkOpen(kind)
  }"""),
 # 狀態欄移除「改回」，加操作欄
 ("""        {r.source_status !== 'ok' && <Tag color="red">{r.source_status_label}</Tag>}
        {canConfirm && ['non_stock', 'pre_opening'].includes(r.status) && (
          <Button size="small" type="link" onClick={(e) => { e.stopPropagation(); doRevert(r.id) }}>改回</Button>)}
      </Space>) },
  ]""", """        {r.source_status !== 'ok' && <Tag color="red">{r.source_status_label}</Tag>}
      </Space>) },
    ...(mode === 'closed' ? [
      { title: '原因', dataIndex: 'status_reason', width: 200, ellipsis: true, render: (v: string | null) => v || '—' },
      { title: '標記', key: 'marked', width: 140, render: (_: unknown, r: ImportLine) => (r.marked_by
        ? r.marked_by
        : <Text type="secondary">系統自動</Text>) },
    ] : []),
    ...(canConfirm ? [{
      title: '操作', key: 'act', width: mode === 'open' ? 210 : 110, fixed: 'right' as const,
      render: (_: unknown, r: ImportLine) => {
        const stop = (fn: () => void) => (e: React.MouseEvent) => { e.stopPropagation(); fn() }
        if (mode === 'open') {
          if (!OPEN.includes(r.status)) return <Text type="secondary">—</Text>
          if (r.source_status !== 'ok') return <Tooltip title="Ragic 來源已異動／退回／刪除，請先開明細確認"><Text type="secondary">來源異動</Text></Tooltip>
          return (
            <Space size={0}>
              <Button size="small" type="link" onClick={stop(() => setConfirmLines([r]))}>確認入庫</Button>
              <Button size="small" type="link" danger onClick={stop(() => openMark('non_stock', [r.id]))}>確認不入庫</Button>
              <Button size="small" type="link" onClick={stop(() => openMark('pre_opening', [r.id]))}>開帳前</Button>
            </Space>)
        }
        if (!REVERTIBLE.includes(r.status)) return <Tooltip title="請款單已對應採購單，由系統判定，以採購單入庫（D15）"><Text type="secondary">—</Text></Tooltip>
        return (
          <Popconfirm title="改回待確認？之後要在「待匯入清單」重新確認" onConfirm={() => doRevert([r.id])}
            onPopupClick={(e) => e.stopPropagation()}>
            <Button size="small" type="link" onClick={(e) => e.stopPropagation()}>改回待確認</Button>
          </Popconfirm>)
      },
    }] : []),
  ]
  const statusOptions = STATUS_OPTIONS.filter((o) => (mode === 'open' ? [...OPEN, 'done'] : CLOSED).includes(o.value))"""),
 ("            options={STATUS_OPTIONS.map((o) => ({ ...o, label: `${o.label}（${counts[o.value] ?? 0}）` }))} />",
  "            options={statusOptions.map((o) => ({ ...o, label: `${o.label}（${counts[o.value] ?? 0}）` }))} />"),
 ("""            {canConfirm && <Button icon={<SyncOutlined />} loading={refreshing} onClick={doRefresh}>從 Ragic 資料重新整理</Button>}
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新讀取</Button>
            {canConfirm && <>
              <Button type="primary" icon={<CheckOutlined />} disabled={!selectedLines.length} onClick={() => setConfirmOpen(true)}>
                確認入庫（{selectedLines.length}）</Button>
              <Button icon={<StopOutlined />} disabled={!selectedLines.length} onClick={() => setMarkOpen('non_stock')}>標不入庫</Button>
              <Button disabled={!selectedLines.length} onClick={() => setMarkOpen('pre_opening')}>標開帳前</Button>
              <Button onClick={() => setBeforeOpen(true)}>開帳前整批標記…</Button>
            </>}""", """            {canConfirm && mode === 'open' && <Button icon={<SyncOutlined />} loading={refreshing} onClick={doRefresh}>從 Ragic 資料重新整理</Button>}
            <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>重新讀取</Button>
            {canConfirm && mode === 'open' && <>
              <Button type="primary" icon={<CheckOutlined />} disabled={!selectedLines.length} onClick={() => setConfirmLines(selectedLines)}>
                確認入庫（{selectedLines.length}）</Button>
              <Button icon={<StopOutlined />} disabled={!selectedLines.length} onClick={() => openMark('non_stock', selected)}>確認不入庫</Button>
              <Button disabled={!selectedLines.length} onClick={() => openMark('pre_opening', selected)}>標開帳前</Button>
              <Button onClick={() => setBeforeOpen(true)}>開帳前整批標記…</Button>
            </>}
            {canConfirm && mode === 'closed' && (
              <Popconfirm title={`把 ${selectedLines.length} 筆改回待確認？`} disabled={!selectedLines.length} onConfirm={() => doRevert(selected)}>
                <Button disabled={!selectedLines.length}>改回待確認（{selectedLines.length}）</Button>
              </Popconfirm>)}"""),
 ("""          getCheckboxProps: (r) => ({ disabled: !OPEN.includes(r.status) || r.source_status !== 'ok' }),""",
  """          getCheckboxProps: (r) => ({
            disabled: mode === 'open' ? !OPEN.includes(r.status) || r.source_status !== 'ok' : !REVERTIBLE.includes(r.status),
          }),"""),
 ("""        pagination={{ pageSize: 50, showSizeChanger: false }}""",
  """        pagination={{ pageSize: 50, showSizeChanger: false }} scroll={{ x: 1300 }}"""),
 ("""      <ConfirmModal code={code} lines={selectedLines} open={confirmOpen} onClose={() => setConfirmOpen(false)}
        onDone={() => { setConfirmOpen(false); load(); onChanged() }} />""",
  """      <ConfirmModal code={code} lines={confirmLines ?? []} open={!!confirmLines} onClose={() => setConfirmLines(null)}
        onDone={() => { setConfirmLines(null); load(); onChanged() }} />"""),
 ("""      <Modal open={!!markOpen} title={markOpen === 'non_stock' ? `標記不入庫（${selected.length} 筆）` : `標記開帳前不入庫（${selected.length} 筆）`}""",
  """      <Modal open={!!markOpen} title={markOpen === 'non_stock' ? `確認不入庫（${markIds.length} 筆）` : `標記開帳前不入庫（${markIds.length} 筆）`}"""),
 # 主頁 Tabs
 ("""          { key: 'imports', label: '待匯入清單', children: <ImportsTab code={code} canConfirm={canConfirm} onChanged={changed} /> },""",
  """          { key: 'imports', label: `待匯入清單${summary ? `（${summary.pending_lines}）` : ''}`,
            children: <ImportsTab mode="open" code={code} canConfirm={canConfirm} onChanged={changed} version={version} /> },
          { key: 'closed', label: '不入庫',
            children: <ImportsTab mode="closed" code={code} canConfirm={canConfirm} onChanged={changed} version={version} /> },"""),
 ("        <Text type=\"secondary\">待匯入清單＝Ragic 採購單品項＋沒有對應採購單的已核准請款單品項；每一筆都要人工確認才入庫</Text>",
  "        <Text type=\"secondary\">待匯入清單＝Ragic 採購單品項＋沒有對應採購單的已核准請款單品項；每一筆都要人工確認入庫或不入庫，確認不入庫的收在「不入庫」TAB</Text>"),
])
