import sys, os
root=sys.argv[1]
def ed(rel, reps):
    p=os.path.join(root,rel); s=open(p,encoding='utf-8').read()
    for a,b in reps:
        if s.count(a)!=1: raise SystemExit(f"{rel}: anchor {s.count(a)}: {a[:60]!r}")
        s=s.replace(a,b)
    open(p,'w',encoding='utf-8').write(s); print('ok',rel)
ed('router/index.tsx',[
 ("import MobileAuditCheckSheet from '@/pages/Mobile/AuditCheckSheet'\n",
  "import MobileAuditCheckSheet from '@/pages/Mobile/AuditCheckSheet'\nimport MobileStockIssue from '@/pages/Mobile/StockIssue'\n"),
 ("""        {/* 手機分支內走錯路徑 → 回手機首頁，不要掉回桌面版 */}""",
  """        {/* 庫存領用（2026-11-17，Phase 4b）：沿用桌面 permission key；料號 QR 標籤掃描後開這頁 */}
        <Route path="stock/issue" element={
          <PermissionGuard permissionKey="stock_issue_create" anyOf={['stock_issue_create', 'stock_issue_post']}>
            <MobileStockIssue />
          </PermissionGuard>
        } />
        {/* 手機分支內走錯路徑 → 回手機首頁，不要掉回桌面版 */}"""),
])
ed('components/Layout/mobileMenuItems.tsx',[
 ("import { AuditOutlined, ToolOutlined } from '@ant-design/icons'","import { AuditOutlined, InboxOutlined, ToolOutlined } from '@ant-design/icons'"),
 ("""    permissionKey: 'audit_check_view',
  },
]""","""    permissionKey: 'audit_check_view',
  },
  {
    // 2026-11-17 庫存管理 Phase 4b：手機領用（沿用桌面 key；倉管走桌面版）
    key: '/m/stock/issue',
    label: '領用',
    icon: <InboxOutlined />,
    permissionKey: 'stock_issue_create',
  },
]"""),
])
