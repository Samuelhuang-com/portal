/**
 * Main application layout with sidebar navigation
 * ⚠️  選單文字請勿在此直接修改，統一至 @/constants/navLabels.ts 修改
 */
import { useState } from 'react'
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
  ApiOutlined,
  DatabaseOutlined,
  DollarOutlined,
  BarChartOutlined,
  FundOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { SITE_TITLE, NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'

const { Header, Sider, Content } = Layout
const { Text } = Typography

// ── Menu 定義 ─────────────────────────────────────────────────────────────────
// ⚠️  修改文字請去 src/constants/navLabels.ts，不要改這裡的 label 值
const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: NAV_GROUP.dashboard,
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
      { key: '/mall/dashboard',            icon: <DashboardOutlined />, label: NAV_PAGE.mallDashboard },
      { key: '/mall/periodic-maintenance', icon: <FileTextOutlined />, label: NAV_PAGE.mallPeriodicMaintenance },
      { key: '/mall/b4f-inspection',       icon: <SafetyOutlined />,   label: NAV_PAGE.b4fInspection },
      { key: '/mall/rf-inspection',        icon: <SafetyOutlined />,   label: NAV_PAGE.rfInspection },
      { key: '/mall/b2f-inspection',       icon: <SafetyOutlined />,   label: NAV_PAGE.b2fInspection },
      { key: '/mall/b1f-inspection',       icon: <SafetyOutlined />,   label: NAV_PAGE.b1fInspection },
    ],
  },
  // ── 樂群工務報修（商場管理之後）──────────────────────────────────────────
  {
    key: 'luqun-repair',
    icon: <ToolOutlined />,
    label: NAV_GROUP.luqun_repair,
    children: [
      { key: '/luqun-repair/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.luqunRepairDashboard },
      { key: '/work-category-analysis', icon: <BarChartOutlined />,  label: NAV_PAGE.workCategoryAnalysis },
      { key: '/exec-dashboard',         icon: <FundOutlined />,      label: NAV_PAGE.execDashboard },
    ],
  },
  // ── 大直工務部（樂群工務報修之後）──────────────────────────────────────────
  {
    key: 'dazhi-repair',
    icon: <ToolOutlined />,
    label: NAV_GROUP.dazhi_repair,
    children: [
      { key: '/dazhi-repair/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.dazhiRepairDashboard },
      { key: '/work-category-analysis', icon: <BarChartOutlined />,  label: NAV_PAGE.workCategoryAnalysis },
      { key: '/exec-dashboard',         icon: <FundOutlined />,      label: NAV_PAGE.execDashboard },
    ],
  },
  // ── 春大直商場工務巡檢（商場管理之後、整棟巡檢之前）──────────────────────
  {
    key: 'mall-facility-inspection',
    icon: <ToolOutlined />,
    label: NAV_GROUP.mall_facility_inspection,
    children: [
      { key: '/mall-facility-inspection/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.mallFacilityDashboard },
      { key: '/mall-facility-inspection/4f',        icon: <SafetyOutlined />,   label: NAV_PAGE.mallFacility4F },
      { key: '/mall-facility-inspection/3f',        icon: <SafetyOutlined />,   label: NAV_PAGE.mallFacility3F },
      { key: '/mall-facility-inspection/1f-3f',     icon: <SafetyOutlined />,   label: NAV_PAGE.mallFacility1F3F },
      { key: '/mall-facility-inspection/1f',        icon: <SafetyOutlined />,   label: NAV_PAGE.mallFacility1F },
      { key: '/mall-facility-inspection/b1f-b4f',   icon: <SafetyOutlined />,   label: NAV_PAGE.mallFacilityB1FB4F },
    ],
  },
  // ── 整棟巡檢（春大直商場工務巡檢之後、保全管理之前）──────────────────────
  {
    key: 'full-building-inspection',
    icon: <SafetyOutlined />,
    label: NAV_GROUP.full_building_inspection,
    children: [
      { key: '/full-building-inspection/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.fullBuildingDashboard },
      { key: '/full-building-inspection/rf',        icon: <SafetyOutlined />,   label: NAV_PAGE.fullBuildingRF },
      { key: '/full-building-inspection/b4f',       icon: <SafetyOutlined />,   label: NAV_PAGE.fullBuildingB4F },
      { key: '/full-building-inspection/b2f',       icon: <SafetyOutlined />,   label: NAV_PAGE.fullBuildingB2F },
      { key: '/full-building-inspection/b1f',       icon: <SafetyOutlined />,   label: NAV_PAGE.fullBuildingB1F },
    ],
  },
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
      { key: '/settings/users',              icon: <UserOutlined />,    label: NAV_PAGE.usersManage },
      { key: '/settings/roles',              icon: <SettingOutlined />, label: NAV_PAGE.rolesManage },
      { key: '/settings/ragic-app-directory', icon: <DatabaseOutlined />, label: NAV_PAGE.ragicAppDirectory },
      { key: '/settings/ragic-connections', icon: <ApiOutlined />,     label: NAV_PAGE.ragicConnections },
    ],
  },
]

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)
  const { token: designToken } = theme.useToken()

  // 自動展開當前路徑對應的 submenu
  const openKeys = menuItems
    .filter((item) => item.children?.some((c) => location.pathname.startsWith(c.key)))
    .map((item) => item.key)

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
          items={menuItems}
          style={{ border: 'none', marginTop: 8 }}
          onClick={({ key }) => navigate(key)}
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