import sys, os
p = os.path.join(sys.argv[1], 'pages/Stock/Receipts/index.tsx'); s = open(p, encoding='utf-8').read()
def rep(a, b):
    global s
    if s.count(a) != 1: raise SystemExit(f"anchor {s.count(a)}: {a[:60]!r}")
    s = s.replace(a, b)
rep("import { CheckOutlined, LinkOutlined, ReloadOutlined, StopOutlined, SyncOutlined } from '@ant-design/icons'",
    "import {\n  CheckCircleOutlined, CheckOutlined, FieldTimeOutlined, LinkOutlined, ReloadOutlined, RollbackOutlined, StopOutlined, SyncOutlined,\n} from '@ant-design/icons'")
rep("      title: '操作', key: 'act', width: mode === 'open' ? 210 : 110, fixed: 'right' as const,",
    "      title: '操作', key: 'act', width: mode === 'open' ? 110 : 64, align: 'center' as const, fixed: 'right' as const,")
rep("""            <Space size={0}>
              <Button size="small" type="link" onClick={stop(() => setConfirmLines([r]))}>確認入庫</Button>
              <Button size="small" type="link" danger onClick={stop(() => openMark('non_stock', [r.id]))}>確認不入庫</Button>
              <Button size="small" type="link" onClick={stop(() => openMark('pre_opening', [r.id]))}>開帳前</Button>
            </Space>)""",
"""            <Space size={0}>
              <Tooltip title="確認入庫"><Button size="small" type="text" aria-label="確認入庫"
                icon={<CheckCircleOutlined style={{ color: '#52c41a', fontSize: 16 }} />} onClick={stop(() => setConfirmLines([r]))} /></Tooltip>
              <Tooltip title="確認不入庫"><Button size="small" type="text" aria-label="確認不入庫"
                icon={<StopOutlined style={{ color: '#ff4d4f', fontSize: 16 }} />} onClick={stop(() => openMark('non_stock', [r.id]))} /></Tooltip>
              <Tooltip title="開帳前不入庫"><Button size="small" type="text" aria-label="開帳前不入庫"
                icon={<FieldTimeOutlined style={{ color: '#8c8c8c', fontSize: 16 }} />} onClick={stop(() => openMark('pre_opening', [r.id]))} /></Tooltip>
            </Space>)""")
rep("""            <Button size="small" type="link" onClick={(e) => e.stopPropagation()}>改回待確認</Button>""",
"""            <Tooltip title="改回待確認"><Button size="small" type="text" aria-label="改回待確認"
              icon={<RollbackOutlined style={{ color: '#4BA8E8', fontSize: 16 }} />} onClick={(e) => e.stopPropagation()} /></Tooltip>""")
open(p, 'w', encoding='utf-8').write(s); print("ok")
