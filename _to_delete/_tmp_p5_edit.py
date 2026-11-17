import sys, os
root=sys.argv[1]
def ed(rel, reps):
    p=os.path.join(root,rel); s=open(p,encoding='utf-8').read()
    for a,b in reps:
        if s.count(a)!=1: raise SystemExit(f"{rel}: anchor {s.count(a)}: {a[:70]!r}")
        s=s.replace(a,b)
    open(p,'w',encoding='utf-8').write(s); print('ok',rel)
ed('pages/Stock/Settings/index.tsx',[
 ("import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'\n",
  "import StockCompanySelect, { useStockCompany } from '../StockCompanySelect'\nimport PeriodsTab from './Periods'\n"),
 ("      ? { name: '', department_id: undefined, keeper_name: '', status: 'active', notes: '', issue_requires_approval: false }",
  "      ? { name: '', department_id: undefined, keeper_name: '', status: 'active', notes: '', issue_requires_approval: false, count_blind: true }"),
 ("notes: w.notes ?? '', issue_requires_approval: w.issue_requires_approval })",
  "notes: w.notes ?? '', issue_requires_approval: w.issue_requires_approval, count_blind: w.count_blind })"),
 ("""    { title: '領用核准', dataIndex: 'issue_requires_approval', width: 90, render: (v: boolean) => (v ? <Tag color="gold">需核准</Tag> : '—') },
""","""    { title: '領用核准', dataIndex: 'issue_requires_approval', width: 90, render: (v: boolean) => (v ? <Tag color="gold">需核准</Tag> : '—') },
    { title: '盤點', dataIndex: 'count_blind', width: 80, render: (v: boolean) => (v ? <Tag>盲盤</Tag> : '明盤') },
"""),
 ("""            <Switch />
          </Form.Item>
          <Form.Item name="status" label="狀態">""","""            <Switch />
          </Form.Item>
          <Form.Item name="count_blind" label="盲盤" valuePropName="checked"
            extra="開啟（預設）：盤點人看不到帳面數，只填實際數量，差異由主管審核時查看（D8）">
            <Switch />
          </Form.Item>
          <Form.Item name="status" label="狀態">"""),
 ("""  const canOpen = hasPermission('stock_opening_manage')
""","""  const canOpen = hasPermission('stock_opening_manage')
  const canClose = hasPermission('stock_period_close')
"""),
 ("""          { key: 'opening', label: '期初開帳', children: <OpeningTab code={code} canOpen={canOpen} canManage={canManage} /> },
""","""          { key: 'opening', label: '期初開帳', children: <OpeningTab code={code} canOpen={canOpen} canManage={canManage} /> },
          ...(canClose ? [{ key: 'periods', label: '月結', children: <PeriodsTab code={code} canClose={canClose} /> }] : []),
"""),
])
ed('router/index.tsx',[
 ("import StockIssuesPage                 from '@/pages/Stock/Issues'\n",
  "import StockIssuesPage                 from '@/pages/Stock/Issues'\nimport StockCountsPage                 from '@/pages/Stock/Counts'\nimport StockMonthlyReportPage          from '@/pages/Stock/MonthlyReport'\n"),
 ("  { key: 'stock_issue_create',                route: '/stock/issues' },\n",
  "  { key: 'stock_issue_create',                route: '/stock/issues' },\n  { key: 'stock_count_execute',               route: '/stock/counts' },\n  { key: 'stock_count_review',                route: '/stock/counts' },\n  { key: 'stock_period_close',                route: '/stock/settings' },\n"),
 ("""                <StockIssuesPage />
              </PermissionGuard>
            }
          />
""","""                <StockIssuesPage />
              </PermissionGuard>
            }
          />
          <Route
            path="counts"
            element={
              <PermissionGuard permissionKey="stock_count_execute" anyOf={['stock_count_execute', 'stock_count_review']}>
                <StockCountsPage />
              </PermissionGuard>
            }
          />
          <Route
            path="monthly-report"
            element={
              <PermissionGuard permissionKey="stock_balance_view">
                <StockMonthlyReportPage />
              </PermissionGuard>
            }
          />
"""),
 ("<PermissionGuard permissionKey=\"stock_settings_manage\" anyOf={['stock_settings_manage', 'stock_opening_manage']}>",
  "<PermissionGuard permissionKey=\"stock_settings_manage\" anyOf={['stock_settings_manage', 'stock_opening_manage', 'stock_period_close']}>"),
])
ed('components/Layout/MainLayout.tsx',[
 ("""      'stock_issue_create', 'stock_issue_approve', 'stock_issue_post'],""",
  """      'stock_issue_create', 'stock_issue_approve', 'stock_issue_post', 'stock_count_execute', 'stock_count_review', 'stock_period_close'],"""),
 ("""      { key: '/stock/balance', icon: <TableOutlined />, label: NAV_PAGE.stockBalance, permissionKey: 'stock_balance_view' },
""","""      { key: '/stock/balance', icon: <TableOutlined />, label: NAV_PAGE.stockBalance, permissionKey: 'stock_balance_view' },
      { key: '/stock/monthly-report', icon: <FileSearchOutlined />, label: NAV_PAGE.stockMonthlyReport, permissionKey: 'stock_balance_view' },
"""),
 ("""        permissionKeys: ['stock_issue_create', 'stock_issue_approve', 'stock_issue_post'] },
""","""        permissionKeys: ['stock_issue_create', 'stock_issue_approve', 'stock_issue_post'] },
      { key: '/stock/counts', icon: <FileDoneOutlined />, label: NAV_PAGE.stockCounts,
        permissionKeys: ['stock_count_execute', 'stock_count_review'] },
"""),
 ("""        permissionKeys: ['stock_settings_manage', 'stock_opening_manage'] },""",
  """        permissionKeys: ['stock_settings_manage', 'stock_opening_manage', 'stock_period_close'] },"""),
])
ed('constants/navLabels.ts',[
 ("  stockIssues:                   '領用單',              // ← route /stock/issues（2026-11-17，庫存管理 Phase 4a：領用／退料／調撥／報廢）\n",
  "  stockIssues:                   '領用單',              // ← route /stock/issues（2026-11-17，庫存管理 Phase 4a：領用／退料／調撥／報廢）\n  stockCounts:                   '盤點',                // ← route /stock/counts（2026-11-17，庫存管理 Phase 5）\n  stockMonthlyReport:            '進銷存月報',          // ← route /stock/monthly-report（2026-11-17，庫存管理 Phase 5）\n"),
])
