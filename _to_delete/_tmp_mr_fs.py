import sys, os
p=os.path.join(sys.argv[1],'pages/Stock/MonthlyReport/index.tsx'); s=open(p,encoding='utf-8').read()
def rep(a,b):
    global s
    if s.count(a)!=1: raise SystemExit(f"anchor {s.count(a)}: {a[:60]!r}")
    s=s.replace(a,b)
rep(" * 權限：stock_balance_view\n */"," * 權限：stock_balance_view\n * 全螢幕（2026-11-17）：沿用戰情 KPI 做法（Fullscreen API＋彈出層掛在容器內，下拉選單在全螢幕中才看得到）\n */")
rep("import { useEffect, useMemo, useRef, useState } from 'react'","import { useCallback, useEffect, useMemo, useRef, useState } from 'react'")
rep("import { Alert, Button, DatePicker, Input, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'\nimport { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'",
    "import { Alert, Button, ConfigProvider, DatePicker, Input, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'\nimport { DownloadOutlined, FullscreenExitOutlined, FullscreenOutlined, ReloadOutlined } from '@ant-design/icons'")
rep("""  const anchored = useRef<string>('')   // 每家公司只在第一次載入時跳到「資料最後月份」
""","""  const anchored = useRef<string>('')   // 每家公司只在第一次載入時跳到「資料最後月份」
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
""")
rep("""  return (
    <div>
      <Space wrap style={{ marginBottom: 12 }}>
        <StockCompanySelect""","""  return (
    <ConfigProvider getPopupContainer={popup}>
    <div ref={rootRef} style={isFs ? { background: '#f0f4f8', height: '100vh', overflow: 'auto', padding: 16 } : undefined}>
      <Space wrap style={{ marginBottom: 12 }}>
        <StockCompanySelect""")
rep("""        <Button icon={<DownloadOutlined />} onClick={doExport} disabled={!rows.length}>匯出 Excel</Button>""",
"""        <Button icon={<DownloadOutlined />} onClick={doExport} disabled={!rows.length}>匯出 Excel</Button>
        <Button type={isFs ? 'default' : 'primary'} ghost={!isFs} icon={isFs ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          onClick={toggleFs}>{isFs ? '離開全螢幕' : '全螢幕'}</Button>""")
rep("""        columns={columns} pagination={{ pageSize: 100 }} scroll={{ x: 1500, y: 620 }}""",
"""        columns={columns} pagination={{ pageSize: 100 }} scroll={{ x: 1500, y: isFs ? 'calc(100vh - 230px)' : 620 }}""")
rep("""        期末＝期初＋各欄加總（出庫為負數）。已月結月份的「成本調整」＝月加權平均與平時移動平均的差額。
      </Text>
    </div>
  )""","""        期末＝期初＋各欄加總（出庫為負數）。已月結月份的「成本調整」＝月加權平均與平時移動平均的差額。
      </Text>
    </div>
    </ConfigProvider>
  )""")
open(p,'w',encoding='utf-8').write(s); print('ok')
