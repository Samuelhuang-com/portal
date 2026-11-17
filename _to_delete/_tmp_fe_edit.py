import sys, os
root = sys.argv[1]
def ed(rel, reps):
    p = os.path.join(root, rel); s = open(p, encoding='utf-8').read()
    for a, b in reps:
        if s.count(a) != 1:
            raise SystemExit(f"{rel}: anchor count {s.count(a)}: {a[:60]}")
        s = s.replace(a, b)
    open(p, 'w', encoding='utf-8').write(s); print("ok", rel)

ed('router/index.tsx', [
 ("import StockReceiptsPage               from '@/pages/Stock/Receipts'\n",
  "import StockReceiptsPage               from '@/pages/Stock/Receipts'\nimport StockIssuesPage                 from '@/pages/Stock/Issues'\n"),
 ("  { key: 'stock_receipt_view',                route: '/stock/receipts' },\n",
  "  { key: 'stock_receipt_view',                route: '/stock/receipts' },\n  { key: 'stock_issue_create',                route: '/stock/issues' },\n"),
 ("""                <StockReceiptsPage />
              </PermissionGuard>
            }
          />
""", """                <StockReceiptsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="issues"
            element={
              <PermissionGuard permissionKey="stock_issue_create" anyOf={['stock_issue_create', 'stock_issue_approve', 'stock_issue_post']}>
                <StockIssuesPage />
              </PermissionGuard>
            }
          />
"""),
])
ed('components/Layout/MainLayout.tsx', [
 ("    permissionKeys: ['stock_balance_view', 'stock_settings_manage', 'stock_opening_manage', 'stock_receipt_view', 'stock_receipt_confirm'],",
  "    permissionKeys: ['stock_balance_view', 'stock_settings_manage', 'stock_opening_manage', 'stock_receipt_view', 'stock_receipt_confirm',\n      'stock_issue_create', 'stock_issue_approve', 'stock_issue_post'],"),
 ("""        permissionKeys: ['stock_receipt_view', 'stock_receipt_confirm'] },
""", """        permissionKeys: ['stock_receipt_view', 'stock_receipt_confirm'] },
      { key: '/stock/issues', icon: <SwapOutlined />, label: NAV_PAGE.stockIssues,
        permissionKeys: ['stock_issue_create', 'stock_issue_approve', 'stock_issue_post'] },
"""),
])
ed('constants/navLabels.ts', [
 ("  stockReceipts:                 '進貨匯入',            // ← route /stock/receipts（2026-11-17，庫存管理 Phase 3）\n",
  "  stockReceipts:                 '進貨匯入',            // ← route /stock/receipts（2026-11-17，庫存管理 Phase 3）\n  stockIssues:                   '領用單',              // ← route /stock/issues（2026-11-17，庫存管理 Phase 4a：領用／退料／調撥／報廢）\n"),
])
ed('pages/Stock/Settings/index.tsx', [
 ("      ? { name: '', department_id: undefined, keeper_name: '', status: 'active', notes: '' }\n      : { name: w.name, department_id: w.department_id ?? undefined, keeper_name: w.keeper_name ?? '', status: w.status === 'inactive' ? 'inactive' : 'active', notes: w.notes ?? '' })",
  "      ? { name: '', department_id: undefined, keeper_name: '', status: 'active', notes: '', issue_requires_approval: false }\n      : { name: w.name, department_id: w.department_id ?? undefined, keeper_name: w.keeper_name ?? '', status: w.status === 'inactive' ? 'inactive' : 'active', notes: w.notes ?? '', issue_requires_approval: w.issue_requires_approval })"),
 ("""          <Form.Item name="keeper_name" label="倉管人員"><Input maxLength={100} /></Form.Item>
""", """          <Form.Item name="keeper_name" label="倉管人員"><Input maxLength={100} /></Form.Item>
          <Form.Item name="issue_requires_approval" label="領用需主管核准" valuePropName="checked"
            extra="開啟後，這個倉的領用單送出後要由該部門有「領用單：核准」權限的人核准，倉管才能發料（預設不需要）">
            <Switch />
          </Form.Item>
"""),
 ("""    { title: '倉管', dataIndex: 'keeper_name', render: (v: string | null) => v || '—' },
""", """    { title: '倉管', dataIndex: 'keeper_name', render: (v: string | null) => v || '—' },
    { title: '領用核准', dataIndex: 'issue_requires_approval', width: 90, render: (v: boolean) => (v ? <Tag color="gold">需核准</Tag> : '—') },
"""),
])
