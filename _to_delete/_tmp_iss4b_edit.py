import sys, os
p = os.path.join(sys.argv[1], 'pages/Stock/Issues/index.tsx'); s = open(p, encoding='utf-8').read()
def rep(a, b):
    global s
    if s.count(a) != 1: raise SystemExit(f"anchor {s.count(a)}: {a[:70]!r}")
    s = s.replace(a, b)
rep(""" * 單位成本與金額只給倉管、庫存檢視者看（後端已遮蔽）
 */""", """ * 單位成本與金額只給倉管、庫存檢視者看（後端已遮蔽）
 * Phase 4b（2026-11-17）：領用範本（開單時套用／存成範本）、列印料號 QR 標籤（掃描開手機領用頁 /m/stock/issue）
 */""")
rep("import { DeleteOutlined, DownOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'",
    "import { DeleteOutlined, DownOutlined, PlusOutlined, QrcodeOutlined, ReloadOutlined, SaveOutlined, SnippetsOutlined } from '@ant-design/icons'")
rep("""  type IssueSummary, type ReturnableLine,
} from '@/api/stock'
""", """  type IssueSummary, type IssueTemplate, type ReturnableLine, fetchIssueTemplates,
} from '@/api/stock'
import { SaveTemplateModal, TemplatesModal } from './Templates'
import QrLabelsModal from './QrLabels'
""")
# editor state
rep("""  const [ccs, setCcs] = useState<{ id: number; label: string; department_name: string; is_mine: boolean }[]>([])
  const [saving, setSaving] = useState(false)
""", """  const [ccs, setCcs] = useState<{ id: number; label: string; department_name: string; is_mine: boolean }[]>([])
  const [saving, setSaving] = useState(false)
  const [templates, setTemplates] = useState<IssueTemplate[]>([])
  const [saveTplOpen, setSaveTplOpen] = useState(false)
""")
# load templates with warehouse (issue only)
rep("""    if (docType === 'issue') {
      fetchIssueCostCenters(code, whId).then((r) => {""", """    if (docType === 'issue') {
      fetchIssueTemplates(code, whId).then((r) => setTemplates(r.data)).catch(() => setTemplates([]))
      fetchIssueCostCenters(code, whId).then((r) => {""")
# apply template function: place before save
rep("""  const save = async (then: 'submit' | 'post' | null) => {""", """  const applyTemplate = (id: number) => {
    const t = templates.find((x) => x.id === id)
    if (!t) return
    const ok = t.lines.filter((l) => availMap.has(l.item_id))
    const miss = t.lines.length - ok.length
    setLines(ok.map((l) => ({ key: newKey(), item_id: l.item_id, qty: Math.min(l.qty, availMap.get(l.item_id)!.available) })))
    if (miss) message.warning(`範本中有 ${miss} 筆料號目前沒有可用庫存，已略過`)
  }

  const save = async (then: 'submit' | 'post' | null) => {""")
# footer: save as template
rep("""          <Button onClick={onClose}>取消</Button>
          <Button loading={saving} onClick={() => save(null)}>存草稿</Button>""", """          <Button onClick={onClose}>取消</Button>
          {docType === 'issue' && (
            <Button icon={<SaveOutlined />} disabled={!whId || !lines.some((l) => l.item_id && (l.qty ?? 0) > 0)}
              onClick={() => setSaveTplOpen(true)}>存成範本</Button>)}
          <Button loading={saving} onClick={() => save(null)}>存草稿</Button>""")
# template select in cost-center row
rep("""          <Input placeholder="會科（選填）" style={{ width: 160 }} value={account} onChange={(e) => setAccount(e.target.value)} />
        </Space>
      )}""", """          <Input placeholder="會科（選填）" style={{ width: 160 }} value={account} onChange={(e) => setAccount(e.target.value)} />
          {templates.length > 0 && (
            <Select placeholder="套用領用範本" style={{ width: 200 }} value={null} onChange={(v: number) => applyTemplate(v)}
              suffixIcon={<SnippetsOutlined />}
              options={templates.map((t) => ({ value: t.id, label: `${t.name}（${t.lines.length} 項）` }))} />)}
        </Space>
      )}""")
# render SaveTemplateModal at the end of editor modal (before closing </Modal> of editor) -> append after the add-line button block
rep("""            onClick={() => setLines((ls) => [...ls, { key: newKey() }])}>加一筆</Button>
        </>
      )}
""", """            onClick={() => setLines((ls) => [...ls, { key: newKey() }])}>加一筆</Button>
        </>
      )}
      <SaveTemplateModal code={code} warehouseId={whId} lines={lines} open={saveTplOpen}
        onClose={() => { setSaveTplOpen(false); if (whId) fetchIssueTemplates(code, whId).then((r) => setTemplates(r.data)).catch(() => undefined) }} />
""")
# page state + toolbar
rep("""  const [postFor, setPostFor] = useState<IssueDoc | null>(null)
""", """  const [postFor, setPostFor] = useState<IssueDoc | null>(null)
  const [tplOpen, setTplOpen] = useState(false)
  const [qrOpen, setQrOpen] = useState(false)
""")
rep("""            <Button type="primary" icon={<PlusOutlined />}>新增 <DownOutlined /></Button>
          </Dropdown>
        )}
""", """            <Button type="primary" icon={<PlusOutlined />}>新增 <DownOutlined /></Button>
          </Dropdown>
        )}
        {meta?.can_create && <Button icon={<SnippetsOutlined />} onClick={() => setTplOpen(true)}>領用範本</Button>}
        {meta && (meta.can_create || meta.can_post) && <Button icon={<QrcodeOutlined />} onClick={() => setQrOpen(true)}>QR 標籤</Button>}
""")
rep("""      {meta && editor && (""", """      {meta && <TemplatesModal code={code} meta={meta} open={tplOpen} onClose={() => setTplOpen(false)} />}
      {meta && <QrLabelsModal code={code} meta={meta} open={qrOpen} onClose={() => setQrOpen(false)} />}
      {meta && editor && (""")
open(p, 'w', encoding='utf-8').write(s); print("ok issues")
