/**
 * Main application layout with sidebar navigation
 * ⚠️  選單文字請勿在此直接修改，統一至 @/constants/navLabels.ts 修改
 * ✅  執行期自訂 label 與排序由 /api/v1/settings/menu-config 動態載入
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { Layout, Menu, Typography, Avatar, Dropdown, Space, theme } from 'antd'
import {
  DashboardOutlined,
  CalendarOutlined,
  HomeOutlined,
  ShopOutlined,
  ToolOutlined,
  FileTextOutlined,
  SettingOutlined,
  AuditOutlined,
  SafetyOutlined,
  NotificationOutlined,
  PlusCircleOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  MenuOutlined,
  ApiOutlined,
  DatabaseOutlined,
  DollarOutlined,
  BarChartOutlined,
  FundOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { SITE_TITLE, NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import { fetchMenuConfig, MenuConfigItem } from '@/api/menuConfig'

const { Header, Sider, Content } = Layout
const { Text } = Typography

// ── Menu 定義 ─────────────────────────────────────────────────────────────────
// ⚠️  修改文字請去 src/constants/navLabels.ts，不要改這裡的 label 值
// ⚠️  此陣列是 MenuConfig 選單管理的唯一來源，新增/移除路由請同時維護此處
export const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: NAV_GROUP.dashboard,
  },
  // ── 高階主管 Dashboard（dashboard 正後方，獨立一階）────────────────────────
  {
    key: '/exec-dashboard',
    icon: <FundOutlined />,
    label: NAV_PAGE.execDashboard,
  },
  // ── ★工項類別分析（高階主管 Dashboard 之後，獨立一階）──────────────────────
  {
    key: '/work-category-analysis',
    icon: <BarChartOutlined />,
    label: NAV_PAGE.workCategoryAnalysis,
  },
  // ── 預算管理（dashboard 之後）──────────────────────────────────────────────
  {
    key: 'budget',
    icon: <DollarOutlined />,
    label: NAV_GROUP.budget,
    children: [
      { key: '/budget/dashboard',           icon: <DashboardOutlined />,  label: NAV_PAGE.budgetDashboard },
      { key: '/budget/plans',               icon: <FileTextOutlined />,   label: NAV_PAGE.budgetPlans },
      { key: '/budget/transactions',        icon: <DatabaseOutlined />,   label: NAV_PAGE.budgetTransactions },
      { key: '/budget/reports/budget-vs-actual', icon: <AuditOutlined />, label: NAV_PAGE.budgetReport },
      { key: '/budget/masters/departments', icon: <SettingOutlined />,    label: NAV_PAGE.budgetDeptMaster },
      { key: '/budget/masters/account-codes', icon: <SettingOutlined />,  label: NAV_PAGE.budgetAccountMaster },
      { key: '/budget/masters/budget-items', icon: <SettingOutlined />,   label: NAV_PAGE.budgetItemMaster },
      { key: '/budget/mappings',            icon: <ApiOutlined />,        label: NAV_PAGE.budgetMappings },
    ],
  },
  // ── 行事曆（dashboard 之後、hotel 之前）────────────────────────────────────
  {
    key: '/calendar',
    icon: <CalendarOutlined />,
    label: NAV_GROUP.calendar,
  },
  {
    key: 'hotel',
    icon: <HomeOutlined />,
    label: NAV_GROUP.hotel,
    children: [
      // { key: '/hotel/room-maintenance',        icon: <ToolOutlined />, label: NAV_PAGE.roomMaintenance },
      { key: '/hotel/room-maintenance-detail',  icon: <ToolOutlined />,    label: NAV_PAGE.roomMaintenanceDetail },
      { key: '/hotel/periodic-maintenance',     icon: <FileTextOutlined />, label: NAV_PAGE.periodicMaintenance },
      { key: '/hotel/ihg-room-maintenance',     icon: <ToolOutlined />,    label: NAV_PAGE.ihgRoomMaintenance },
      // { key: '/hotel/repairs',                 icon: <ToolOutlined />, label: NAV_PAGE.repairs },
    ],
  },
  {
    key: 'mall',
    icon: <ShopOutlined />,
    label: NAV_GROUP.mall,
    children: [
      // ── 商場管理 Dashboard（整合 5 來源總覽，置於群組最頂）─────────────
      { key: '/mall/overview', icon: <DashboardOutlined />, label: NAV_PAGE.mallMgmtDashboard },
      // ── 商場例行維護（L2 群組）→ 三個 L3 子項目 ──────────────────────
      {
        key: 'mall-pm-group',
        icon: <FileTextOutlined />,
        label: NAV_GROUP.mallPmGroup,
        children: [
          { key: '/mall/dashboard',                    icon: <DashboardOutlined />, label: NAV_PAGE.mallDashboard },
          { key: '/mall/periodic-maintenance',         icon: <FileTextOutlined />, label: NAV_PAGE.mallPeriodicMaintenance },
          { key: '/mall/full-building-maintenance',    icon: <ToolOutlined />,     label: NAV_PAGE.fullBuildingMaintenance },
        ],
      },
      { key: '/full-building-inspection/dashboard',   icon: <SafetyOutlined />,   label: NAV_PAGE.fullBuildingDashboard },
      { key: '/mall-facility-inspection/dashboard',   icon: <ToolOutlined />,     label: NAV_PAGE.mallFacilityDashboard },
    ],
  },
  // ── 樂群工務報修（商場管理之後）──────────────────────────────────────────
  // ⚠️  /exec-dashboard 與 /work-category-analysis 已移至頂層一階（Dashboard 正後方）
  {
    key: 'luqun-repair',
    icon: <ToolOutlined />,
    label: NAV_GROUP.luqun_repair,
    children: [
      { key: '/luqun-repair/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.luqunRepairDashboard },
    ],
  },
  // ── 大直工務部（樂群工務報修之後）──────────────────────────────────────────
  // ⚠️  /exec-dashboard 與 /work-category-analysis 已移至頂層一階（Dashboard 正後方）
  {
    key: 'dazhi-repair',
    icon: <ToolOutlined />,
    label: NAV_GROUP.dazhi_repair,
    children: [
      { key: '/dazhi-repair/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.dazhiRepairDashboard },
    ],
  },
  // 春大直商場工務巡檢已整合至商場管理群組，不再獨立顯示
  // 整棟巡檢已整合至商場管理群組，不再獨立顯示
  {
    key: 'security',
    icon: <SafetyOutlined />,
    label: NAV_GROUP.security,
    children: [
      { key: '/security/dashboard',                  icon: <DashboardOutlined />, label: NAV_PAGE.securityDashboard },
      { key: '/security/patrol/b1f-b4f',             icon: <SafetyOutlined />,   label: NAV_PAGE.securityB1fB4f },
      { key: '/security/patrol/1f-3f',               icon: <SafetyOutlined />,   label: NAV_PAGE.security1f3f },
      { key: '/security/patrol/5f-10f',              icon: <SafetyOutlined />,   label: NAV_PAGE.security5f10f },
      { key: '/security/patrol/4f',                  icon: <SafetyOutlined />,   label: NAV_PAGE.security4f },
      { key: '/security/patrol/1f-hotel',            icon: <SafetyOutlined />,   label: NAV_PAGE.security1fHotel },
      { key: '/security/patrol/1f-close',            icon: <SafetyOutlined />,   label: NAV_PAGE.security1fClose },
      { key: '/security/patrol/1f-open',             icon: <SafetyOutlined />,   label: NAV_PAGE.security1fOpen },
    ],
  },
  // {
  //   key: 'warehouse',
  //   icon: <DatabaseOutlined />,
  //   label: NAV_GROUP.warehouse,
  //   children: [
  //     { key: '/warehouse/inventory', icon: <DatabaseOutlined />, label: NAV_PAGE.inventory },
  //   ],
  // },
  // {
  //   key: 'reports',
  //   icon: <FileTextOutlined />,
  //   label: NAV_GROUP.reports,
  //   children: [
  //     { key: '/reports/generate', label: NAV_PAGE.reportsGenerate },
  //     { key: '/reports/history',  label: NAV_PAGE.reportsHistory },
  //   ],
  // },
  {
    key: 'approvals',
    icon: <AuditOutlined />,
    label: NAV_GROUP.approvals,
    children: [
      { key: '/approvals/list', icon: <FileTextOutlined />,  label: NAV_PAGE.approvalsList },
      { key: '/approvals/new',  icon: <FileTextOutlined />,  label: NAV_PAGE.approvalsNew  },
    ],
  },
  {
    key: 'memos',
    icon: <NotificationOutlined />,
    label: NAV_GROUP.memos,
    children: [
      { key: '/memos/list', icon: <NotificationOutlined />, label: NAV_PAGE.memosList },
      { key: '/memos/new',  icon: <PlusCircleOutlined />,   label: NAV_PAGE.memosNew  },
    ],
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: NAV_GROUP.settings,
    children: [
      { key: '/settings/users',               icon: <UserOutlined />,    label: NAV_PAGE.usersManage },
      { key: '/settings/roles',               icon: <SettingOutlined />, label: NAV_PAGE.rolesManage },
      { key: '/settings/ragic-app-directory', icon: <DatabaseOutlined />, label: NAV_PAGE.ragicAppDirectory },
      { key: '/settings/ragic-connections',   icon: <ApiOutlined />,     label: NAV_PAGE.ragicConnections },
      { key: '/settings/menu-config',         icon: <MenuOutlined />,    label: '選單管理' },
    ],
  },
]

// ── 共用：計算「哪個 base L2 被換了父層」───────────────────────────────────────
// 回傳 Map<menu_key, new_parent_key>，供 applyMenuConfig 與 MenuConfig 共用
export function computeReparentedL2(
  base: Array<{ key: string; children?: Array<{ key: string }> }>,
  configs: MenuConfigItem[]
): Map<string, string> {
  const baseL2Keys = new Set(base.flatMap((p) => (p.children ?? []).map((c) => c.key)))
  const result = new Map<string, string>()
  configs.forEach((cfg) => {
    if (!baseL2Keys.has(cfg.menu_key) || !cfg.parent_key) return
    const origParent = base.find((p) => p.children?.some((c) => c.key === cfg.menu_key))
    if (origParent && cfg.parent_key !== origParent.key) {
      result.set(cfg.menu_key, cfg.parent_key)
    }
  })
  return result
}

// ── 套用 MenuConfig 覆蓋設定（label + sort_order，支援三層）──────────────────
// 回傳深拷貝後的 items，不修改原始 menuItems 常數
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function applyMenuConfig(base: any[], configs: MenuConfigItem[]): any[] {
  if (!configs.length) return base

  const cfgMap = new Map(configs.map((c) => [c.menu_key, c]))
  const baseL1Keys = new Set(base.map((p) => p.key))
  const baseL2Keys = new Set(base.flatMap((p) => (p.children ?? []).map((c: any) => c.key)))

  // 以 parent_key 為索引，收集所有 DB 中的子項
  const childrenByParent = new Map<string, MenuConfigItem[]>()
  configs.forEach((cfg) => {
    if (cfg.parent_key) {
      if (!childrenByParent.has(cfg.parent_key)) childrenByParent.set(cfg.parent_key, [])
      childrenByParent.get(cfg.parent_key)!.push(cfg)
    }
  })

  // 建立 base 項目的 label / icon 對照表，讓 buildItem 可查回原始標籤
  // 解決：base 模組被移到三階時，label 顯示 key（如 /mall/dashboard）的問題
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const baseItemInfo = new Map<string, { label: any; icon?: any }>()
  base.forEach((p: any) => {
    baseItemInfo.set(p.key, { label: p.label, icon: p.icon })
    ;(p.children ?? []).forEach((c: any) => {
      baseItemInfo.set(c.key, { label: c.label, icon: c.icon })
    })
  })

  // 從 DB config 建出一個 menu item（可能含三層）
  // 優先序：custom_label > base 結構的原始 label > menu_key
  const buildItem = (cfg: MenuConfigItem): any => {
    const grandchildren = (childrenByParent.get(cfg.menu_key) ?? [])
      .filter((g) => g.is_visible !== false)
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((g) => buildItem(g))
    const base = baseItemInfo.get(cfg.menu_key)
    return {
      key: cfg.menu_key,
      label: cfg.custom_label || base?.label || cfg.menu_key,
      icon: base?.icon ?? <FileTextOutlined />,
      ...(grandchildren.length > 0 ? { children: grandchildren } : {}),
    }
  }

  // 找出「被 DB 換了父層」的 base L2 項目（複用共用函式）
  const reparentedBaseL2 = computeReparentedL2(base, configs)

  // 套用到預設 base（L1 + L2），並補充 L3
  const cloned = base
    .filter((parent) => {
      const cfg = cfgMap.get(parent.key)
      return cfg === undefined || cfg.is_visible !== false
    })
    .map((parent) => ({
      ...parent,
      label: cfgMap.get(parent.key)?.custom_label || parent.label,
      children: parent.children
        ? (() => {
            // base L2：排除已被移走的，保留其餘並套用 label/排序
            const baseChildren = [...parent.children]
              .filter((child: any) => {
                if (reparentedBaseL2.has(child.key)) return false  // 已移到別的 L1
                const cfg = cfgMap.get(child.key)
                return cfg === undefined || cfg.is_visible !== false
              })
              .map((child: any) => {
                // L3：DB 中 parent_key === child.key 且不在 base 裡的項目
                const dbGrandchildren = (childrenByParent.get(child.key) ?? [])
                  .filter((g) => !baseL1Keys.has(g.menu_key) && !baseL2Keys.has(g.menu_key) && g.is_visible !== false)
                  .sort((a, b) => a.sort_order - b.sort_order)
                  .map((g) => buildItem(g))

                // 若 child 本身是群組（base 已有子項目），合併而非覆寫：
                // 保留 base 子項目（可套用 DB 的 label/visibility），再附加 DB 中額外新增的子項
                if (Array.isArray(child.children) && child.children.length > 0) {
                  const baseGcKeys = new Set((child.children as any[]).map((g: any) => g.key))
                  const extraDbGc = dbGrandchildren.filter((g: any) => !baseGcKeys.has(g.key))
                  const mergedGc = [
                    ...(child.children as any[])
                      .filter((g: any) => {
                        const gcfg = cfgMap.get(g.key)
                        return gcfg === undefined || gcfg.is_visible !== false
                      })
                      .map((g: any) => ({
                        ...g,
                        label: cfgMap.get(g.key)?.custom_label || g.label,
                      })),
                    ...extraDbGc,
                  ].sort((a: any, b: any) => {
                    const ao = cfgMap.get(a.key)?.sort_order ?? 9999
                    const bo = cfgMap.get(b.key)?.sort_order ?? 9999
                    return ao - bo
                  })
                  return {
                    ...child,
                    label: cfgMap.get(child.key)?.custom_label || child.label,
                    children: mergedGc,
                  }
                }

                return {
                  ...child,
                  label: cfgMap.get(child.key)?.custom_label || child.label,
                  ...(dbGrandchildren.length > 0 ? { children: dbGrandchildren } : {}),
                }
              })

            // 從其他 L1 移來的 base L2 項目（保留原始 icon）
            const movedHere = [...reparentedBaseL2.entries()]
              .filter(([, newParent]) => newParent === parent.key)
              .flatMap(([key]) => {
                const cfg = cfgMap.get(key)
                if (cfg?.is_visible === false) return []
                const origItem = base.flatMap((p: any) => p.children ?? []).find((c: any) => c.key === key)
                if (!origItem) return []
                const grandchildren = (childrenByParent.get(key) ?? [])
                  .filter((g) => !baseL1Keys.has(g.menu_key) && !baseL2Keys.has(g.menu_key) && g.is_visible !== false)
                  .sort((a, b) => a.sort_order - b.sort_order)
                  .map((g) => buildItem(g))
                return [{
                  ...origItem,
                  label: cfg?.custom_label || origItem.label,
                  ...(grandchildren.length > 0 ? { children: grandchildren } : {}),
                }]
              })

            // DB 中此 L1 下、不在 base structure 裡的額外 L2 項目
            // （包含 custom_ 自訂項目，以及舊版無前綴的使用者項目如 mall-pm-group）
            // ⚠️  必須用全域 baseL2Keys（所有群組的 L2），而非只有本群組的 base L2，
            //     否則跨群組移過來的 base L2 項目（如 /dazhi-repair/dashboard → mall）
            //     會同時出現在 movedHere 與 customL2Here，造成側欄重複顯示。
            const customL2Here = (childrenByParent.get(parent.key) ?? [])
              .filter((c) =>
                !baseL2Keys.has(c.menu_key) &&
                !baseL1Keys.has(c.menu_key) &&
                c.is_visible !== false
              )
              .sort((a, b) => a.sort_order - b.sort_order)
              .map((c) => buildItem(c))

            return [...baseChildren, ...movedHere, ...customL2Here]
              .sort((a: any, b: any) => {
                const ao = cfgMap.get(a.key)?.sort_order ?? 9999
                const bo = cfgMap.get(b.key)?.sort_order ?? 9999
                return ao - bo
              })
          })()
        : undefined,
    }))
    .sort((a: any, b: any) => {
      const ao = cfgMap.get(a.key)?.sort_order ?? 9999
      const bo = cfgMap.get(b.key)?.sort_order ?? 9999
      return ao - bo
    })

  // 注入 DB 中有但不在 base 的自訂一階選單（只有 custom_ 前綴才是使用者建立的）
  const customL1 = configs
    .filter((c) => !c.parent_key && !baseL1Keys.has(c.menu_key) && c.is_visible !== false && c.menu_key.startsWith('custom_'))
    .sort((a, b) => a.sort_order - b.sort_order)

  customL1.forEach((cfg) => {
    const children = (childrenByParent.get(cfg.menu_key) ?? [])
      .filter((c) => c.is_visible !== false)
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((c) => buildItem(c))
    cloned.push({
      key: cfg.menu_key,
      label: cfg.custom_label || cfg.menu_key,
      icon: <FileTextOutlined />,
      ...(children.length > 0 ? { children } : {}),
    })
  })

  return cloned.sort((a: any, b: any) => {
    const ao = cfgMap.get(a.key)?.sort_order ?? 9999
    const bo = cfgMap.get(b.key)?.sort_order ?? 9999
    return ao - bo
  })
}

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)
  const { token: designToken } = theme.useToken()

  // ── 系統設定選單僅限 system_admin 可見 ────────────────────────────────────
  const isSystemAdmin = !!(user?.roles?.includes('system_admin'))

  // base items：非 system_admin 時過濾掉 settings 群組
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const baseItems = useMemo<any[]>(
    () => isSystemAdmin ? menuItems : menuItems.filter((item) => item.key !== 'settings'),
    [isSystemAdmin]
  )

  // 初始值也要過濾，避免頁面重整時短暫閃現 settings 選單：
  // 直接從 localStorage token 解出 roles，不依賴非同步的 user state。
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [dynamicMenuItems, setDynamicMenuItems] = useState<any[]>(() => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return menuItems.filter((item) => item.key !== 'settings')
      const payload = JSON.parse(atob(token.split('.')[1]))
      const ok = Array.isArray(payload.roles) && payload.roles.includes('system_admin')
      return ok ? menuItems : menuItems.filter((item) => item.key !== 'settings')
    } catch {
      return menuItems.filter((item) => item.key !== 'settings')
    }
  })

  // 啟動時拉取 menu config，靜默套用（失敗不影響正常使用）
  const loadMenuConfig = useCallback(async () => {
    try {
      const configs = await fetchMenuConfig()
      setDynamicMenuItems(
        configs.length > 0 ? applyMenuConfig(baseItems, configs) : baseItems
      )
    } catch {
      // 拉取失敗：回退至 baseItems（已依角色過濾）
      setDynamicMenuItems(baseItems)
    }
  }, [baseItems])

  useEffect(() => {
    loadMenuConfig()
    const handler = () => loadMenuConfig()
    window.addEventListener('menuConfigSaved', handler)
    return () => window.removeEventListener('menuConfigSaved', handler)
  }, [loadMenuConfig])

  // 自動展開當前路徑對應的 submenu（支援三層）
  const openKeys = [
    // L1 → 找到有 L2 子項目匹配的
    ...dynamicMenuItems
      .filter((item) => item.children?.some((c: any) =>
        location.pathname.startsWith(c.key) ||
        c.children?.some((g: any) => location.pathname.startsWith(g.key))
      ))
      .map((item) => item.key),
    // L2 → 找到有 L3 子項目匹配的
    ...dynamicMenuItems.flatMap((item) =>
      (item.children ?? [])
        .filter((c: any) => c.children?.some((g: any) => location.pathname.startsWith(g.key)))
        .map((c: any) => c.key)
    ),
  ]

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: '個人資料' },
      { type: 'divider' as const },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '登出',
        danger: true,
        onClick: () => { logout(); navigate('/login') },
      },
    ],
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* ── Sider ─────────────────────────────────────────────────────── */}
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={220}
        style={{
          background: designToken.colorBgContainer,
          borderRight: `1px solid ${designToken.colorBorderSecondary}`,
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        {/* Logo */}
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? '0' : '0 20px',
            borderBottom: `1px solid ${designToken.colorBorderSecondary}`,
            overflow: 'hidden',
          }}
        >
          <HomeOutlined style={{ fontSize: 20, color: designToken.colorPrimary }} />
          {!collapsed && (
            <Text strong style={{ marginLeft: 10, fontSize: 15, whiteSpace: 'nowrap' }}>
              {SITE_TITLE}
            </Text>
          )}
        </div>

        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          defaultOpenKeys={openKeys}
          items={dynamicMenuItems}
          style={{ border: 'none', marginTop: 8 }}
          onClick={({ key }) => {
            // 自訂選單（尚無對應模組）→ 導向「數據準備中」佔位頁
            if (key.startsWith('custom_')) navigate('/data-preparing')
            else navigate(key)
          }}
        />
      </Sider>

      {/* ── Main ──────────────────────────────────────────────────────── */}
      <Layout style={{ marginLeft: collapsed ? 80 : 220, transition: 'margin-left 0.2s' }}>
        {/* Header */}
        <Header
          style={{
            background: designToken.colorBgContainer,
            borderBottom: `1px solid ${designToken.colorBorderSecondary}`,
            padding: '0 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 100,
          }}
        >
          <div
            style={{ cursor: 'pointer', fontSize: 18 }}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>

          <Dropdown menu={userMenu} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} size="small" />
              <Text>{user?.full_name || user?.name || 'Admin'}</Text>
            </Space>
          </Dropdown>
        </Header>

        {/* Page content */}
        <Content style={{ padding: 24, minHeight: 'calc(100vh - 56px)' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
