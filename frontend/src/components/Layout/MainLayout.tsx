/**
 * Main application layout with sidebar navigation
 * ⚠️  選單文字請勿在此直接修改，統一至 @/constants/navLabels.ts 修改
 * ✅  執行期自訂 label 與排序由 /api/v1/settings/menu-config 動態載入
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Layout, Menu, Typography, Avatar, Dropdown, Space, theme, Skeleton, Modal, Button, Form, Input, Alert } from 'antd'
import { useIdleTimeout } from '@/hooks/useIdleTimeout'
import {
  ApartmentOutlined,
  DashboardOutlined,
  HistoryOutlined,
  LineChartOutlined,
  CalendarOutlined,
  HomeOutlined,
  ShopOutlined,
  AppstoreOutlined,
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
  PieChartOutlined,
  FundOutlined,
  RadarChartOutlined,
  ReadOutlined,
  BookOutlined,
  AlertOutlined,
  ScheduleOutlined,
  RiseOutlined,
  TeamOutlined,
  ClockCircleOutlined,
  UploadOutlined,
  TableOutlined,
  FilePptOutlined,
  SyncOutlined,
  SwapOutlined,
  FileSearchOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  PlayCircleOutlined,
  FileDoneOutlined,
  ShoppingCartOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import { getSiteTitle } from '@/config/siteConfig'
import { fetchMenuConfig, MenuConfigItem } from '@/api/menuConfig'
import { MenuItemsContext } from '@/components/Layout/menuItemsContext'
import { resolveIcon } from '@/constants/iconMap'
import { authApi } from '@/api/auth'

// ── 內部型別：帶 permissionKey 的 menu item ───────────────────────────────────
interface MenuItem {
  key: string
  icon?: React.ReactNode
  label: React.ReactNode
  // 靜態預設權限：null = 公開；有值 = 需具備此 key 才顯示
  // 【新模組開發規則】開發期間設 'system_admin_only'，測試後改為正確 key
  permissionKey?: string | null
  // 2026-07-19 新增：多個 key 符合任一個即可顯示（OR 邏輯）。
  // 用於「查看範圍」比「編輯範圍」寬的模組（例如只勾週期採購請購權限的人
  // 也要能展開週採選單），優先權高於 permissionKey（兩者擇一設定即可）。
  permissionKeys?: string[]
  children?: MenuItem[]
}

const { Header, Sider, Content } = Layout
const { Text } = Typography

// ── Menu 定義 ─────────────────────────────────────────────────────────────────
// ⚠️  修改文字請去 src/constants/navLabels.ts，不要改這裡的 label 值
// ⚠️  此陣列是 MenuConfig 選單管理的唯一來源，新增/移除路由請同時維護此處
// ⚠️  新增模組時 permissionKey 設為 'system_admin_only'，測試完成後改為正確 key
//     並在角色管理頁面授予對應角色
export const menuItems: MenuItem[] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: NAV_GROUP.dashboard,
  },
  // ── 決策駕駛艙（dashboard 正後方，高階主管決策入口）─────────────────────────
  {
    key: '/decision-cockpit',
    icon: <RadarChartOutlined />,
    label: NAV_PAGE.decisionCockpit,
    permissionKey: 'decision_cockpit_view',
  },
  // ── 高階主管 Dashboard（dashboard 正後方，獨立一階）────────────────────────
  {
    key: '/exec-dashboard',
    icon: <FundOutlined />,
    label: NAV_PAGE.execDashboard,
    permissionKey: 'exec_dashboard_view',
  },
  // ── 集團工務決策駕駛艙（高階主管 Dashboard 之後，獨立一階）────────────────
  {
    key: '/exec-work-dashboard',
    icon: <RadarChartOutlined />,
    label: NAV_PAGE.execWorkDashboard,
    permissionKey: 'exec_work_dashboard_view',
  },
  // ── ★工項類別分析（高階主管 Dashboard 之後，獨立一階）──────────────────────
  {
    key: '/work-category-analysis',
    icon: <BarChartOutlined />,
    label: NAV_PAGE.workCategoryAnalysis,
    permissionKey: 'work_category_analysis_view',
  },
  // ── 核准請購單月報表（budget 之前，財務/採購管理）────────────────────────────
  {
    key: 'purchase-report',
    icon: <FileTextOutlined />,
    label: NAV_GROUP.purchaseReport,
    permissionKey: 'purchase_report_view',
    children: [
      { key: '/purchase-report/monthly', icon: <AuditOutlined />, label: NAV_PAGE.purchaseReportMonthly, permissionKey: 'purchase_report_view' },
    ],
  },
  // ── 核准請款單月報表（請購單報表之後，財務/採購管理）─────────────────────────
  {
    key: 'claim-report',
    icon: <FileTextOutlined />,
    label: NAV_GROUP.claimReport,
    permissionKey: 'purchase_report_view',
    children: [
      { key: '/claim-report/monthly', icon: <AuditOutlined />, label: NAV_PAGE.claimReportMonthly, permissionKey: 'purchase_report_view' },
    ],
  },
  // ── 日曜核准請購單月報表（財務/採購管理）────────────────────────────────────
  {
    key: 'nichiyo-purchase-report',
    icon: <FileTextOutlined />,
    label: NAV_GROUP.nichiyoPurchaseReport,
    permissionKey: 'nichiyo_purchase.view',
    children: [
      { key: '/nichiyo-purchase-report/monthly', icon: <AuditOutlined />, label: NAV_PAGE.nichiyoPurchaseReportMonthly, permissionKey: 'nichiyo_purchase.view' },
    ],
  },
  // ── 日曜核准請款單月報表（財務/採購管理）────────────────────────────────────
  {
    key: 'nichiyo-claim-report',
    icon: <FileTextOutlined />,
    label: NAV_GROUP.nichiyoClaimReport,
    permissionKey: 'nichiyo_claim.view',
    children: [
      { key: '/nichiyo-claim-report/monthly', icon: <AuditOutlined />, label: NAV_PAGE.nichiyoClaimReportMonthly, permissionKey: 'nichiyo_claim.view' },
    ],
  },
  // ── 預算管理（dashboard 之後）──────────────────────────────────────────────
  {
    key: 'budget',
    icon: <DollarOutlined />,
    label: NAV_GROUP.budget,
    permissionKey: 'budget_view',
    children: [
      { key: '/budget/dashboard',                icon: <DashboardOutlined />,  label: NAV_PAGE.budgetDashboard,     permissionKey: 'budget_view'   },
      { key: '/budget/plans',                    icon: <FileTextOutlined />,   label: NAV_PAGE.budgetPlans,         permissionKey: 'budget_view'   },
      { key: '/budget/transactions',             icon: <DatabaseOutlined />,   label: NAV_PAGE.budgetTransactions,  permissionKey: 'budget_manage' },
      { key: '/budget/reports/budget-vs-actual', icon: <AuditOutlined />,      label: NAV_PAGE.budgetReport,        permissionKey: 'budget_view'   },
      { key: '/budget/masters/departments',      icon: <SettingOutlined />,    label: NAV_PAGE.budgetDeptMaster,    permissionKey: 'budget_admin'  },
      { key: '/budget/masters/account-codes',    icon: <SettingOutlined />,    label: NAV_PAGE.budgetAccountMaster, permissionKey: 'budget_admin'  },
      { key: '/budget/masters/budget-items',     icon: <SettingOutlined />,    label: NAV_PAGE.budgetItemMaster,    permissionKey: 'budget_admin'  },
      { key: '/budget/mappings',                 icon: <ApiOutlined />,        label: NAV_PAGE.budgetMappings,      permissionKey: 'budget_admin'  },
    ],
  },
  // ── 週期採購（獨立資料庫 cycle-purchase.db，2026-07-10 新增）───────────────
  // 十大流程全部上線：料號主檔 → 週期設定 → 請購單 → 彙整單 → 採購單 →
  // 驗收單 → 請款單 → 稽核 → 4 張主檔 → Dashboard。
  {
    key: 'cyclePurchase',
    icon: <ShopOutlined />,
    label: NAV_GROUP.cyclePurchase,
    // 2026-07-19：父層改用 permissionKeys（OR），讓只勾「週期採購請購」
    // (cycle_purchase_request) 的一般填單人也能展開週採選單，不需要額外開放
    // 範圍較大的「週期採購管理」(cycle_purchase_view)。
    // 2026-08-07：同一個問題其實對驗收／請款／採購人員也成立，父層改成涵蓋
    // 全部 8 個週採權限——只要有任一週採權限就能展開選單，實際看得到哪幾個
    // 子項目仍由各子項目自己的 key 決定。
    permissionKeys: [
      'cycle_purchase_view', 'cycle_purchase_request', 'cycle_purchase_close',
      'cycle_purchase_buyer', 'cycle_purchase_receive', 'cycle_purchase_finance',
      'cycle_purchase_report', 'cycle_purchase_admin',
    ],
    children: [
      { key: '/cycle-purchase/dashboard',            icon: <DashboardOutlined />,  label: NAV_PAGE.cyclePurchaseDashboard,    permissionKey: 'cycle_purchase_view'  },
      { key: '/cycle-purchase/items',                icon: <DatabaseOutlined />,   label: NAV_PAGE.cyclePurchaseItems,        permissionKey: 'cycle_purchase_view'  },
      { key: '/cycle-purchase/cycles',                icon: <CalendarOutlined />,   label: NAV_PAGE.cyclePurchaseCycles,       permissionKey: 'cycle_purchase_admin' },
      // 2026-07-19：同上，只勾 cycle_purchase_request 的填單人也要能看到「請購單」子項目
      { key: '/cycle-purchase/requests',              icon: <FileTextOutlined />,   label: NAV_PAGE.cyclePurchaseRequests,     permissionKeys: ['cycle_purchase_view', 'cycle_purchase_request']  },
      // 2026-08-07：以下四項比照請購單改成 OR。原本都寫死 cycle_purchase_view，
      // 造成「只勾驗收權限的驗收人員看不到驗收單選單」——頁面內的按鈕判斷用的
      // 是 cycle_purchase_receive，選單卻要求 view，等於權限開了也進不去。
      // 採購單與彙整單同屬採購人員的作業範圍，一併掛 cycle_purchase_buyer。
      // 後端對應的讀取端點也已同步改用 require_any_permission()。
      { key: '/cycle-purchase/summary',                icon: <FileDoneOutlined />,   label: NAV_PAGE.cyclePurchaseSummary,      permissionKeys: ['cycle_purchase_view', 'cycle_purchase_buyer']    },
      { key: '/cycle-purchase/pos',                     icon: <ShoppingCartOutlined />, label: NAV_PAGE.cyclePurchasePOs,        permissionKeys: ['cycle_purchase_view', 'cycle_purchase_buyer']    },
      { key: '/cycle-purchase/receiving',        icon: <InboxOutlined />,        label: NAV_PAGE.cyclePurchaseReceiving,        permissionKeys: ['cycle_purchase_view', 'cycle_purchase_receive']  },
      { key: '/cycle-purchase/receiving-report', icon: <BarChartOutlined />,     label: NAV_PAGE.cyclePurchaseReceivingReport,  permissionKey: 'cycle_purchase_report' },
      { key: '/cycle-purchase/payments',   icon: <DollarOutlined />,       label: NAV_PAGE.cyclePurchasePayments,         permissionKeys: ['cycle_purchase_view', 'cycle_purchase_finance'] },
      { key: '/cycle-purchase/audit-log',  icon: <AuditOutlined />,        label: NAV_PAGE.cyclePurchaseAuditLog,         permissionKey: 'cycle_purchase_admin'  },
      { key: '/cycle-purchase/masters/vendors',       icon: <ShopOutlined />,       label: NAV_PAGE.cyclePurchaseVendors,      permissionKey: 'cycle_purchase_admin' },
      { key: '/cycle-purchase/masters/categories',    icon: <AppstoreOutlined />,   label: NAV_PAGE.cyclePurchaseCategories,   permissionKey: 'cycle_purchase_admin' },
      { key: '/cycle-purchase/masters/departments',   icon: <ApartmentOutlined />,  label: NAV_PAGE.cyclePurchaseDepartments,  permissionKey: 'cycle_purchase_admin' },
      { key: '/cycle-purchase/masters/cost-centers',  icon: <ApartmentOutlined />,  label: NAV_PAGE.cyclePurchaseCostCenters,  permissionKey: 'cycle_purchase_admin' },
      { key: '/cycle-purchase/masters/account-codes', icon: <SettingOutlined />,    label: NAV_PAGE.cyclePurchaseAccountCodes, permissionKey: 'cycle_purchase_admin' },
      // 使用手冊（2026-08-07）：與 Samuel 確認，開放給「所有週採使用者」——
      // 手冊是教人怎麼用的，卡權限會讓最需要它的填單人看不到，所以 OR 涵蓋
      // 全部 8 個週採權限，不另立新的 permission key。
      {
        key: '/cycle-purchase/manual',
        icon: <BookOutlined />,
        label: NAV_PAGE.cyclePurchaseManual,
        permissionKeys: [
          'cycle_purchase_view', 'cycle_purchase_request', 'cycle_purchase_close',
          'cycle_purchase_buyer', 'cycle_purchase_receive', 'cycle_purchase_finance',
          'cycle_purchase_report', 'cycle_purchase_admin',
        ],
      },
    ],
  },
  // ── 行事曆（dashboard 之後、hotel 之前）────────────────────────────────────
  {
    key: '/calendar',
    icon: <CalendarOutlined />,
    label: NAV_GROUP.calendar,
    permissionKey: 'calendar_view',
  },
  // ── 影音教學（本地模組，不對接 Ragic；行事曆之後、班表之前）─────────────────
  {
    key: '/tutorial-videos',
    icon: <PlayCircleOutlined />,
    label: NAV_PAGE.tutorialVideos,
    permissionKey: 'tutorial_videos_view',
  },
  // ── 2026-08-14：原本的頂層「班表」群組已移除，拆為兩個 L2 群組：
  //      飯店管理 → 飯店班表（本區塊往下找 hotel-schedule-group）
  //      商場管理 → 商場班表（本區塊往下找 mall-schedule-group）
  //    舊路由 /schedule/* 在 router/index.tsx 保留 redirect 到 /hotel/schedule。
  // ── 合約管理（飯店管理之前）────────────────────────────────────
  {
    key: 'contract',
    icon: <AuditOutlined />,
    label: NAV_GROUP.contract,
    permissionKey: 'contract_view',
    children: [
      { key: '/contract',            icon: <FileTextOutlined />,  label: NAV_PAGE.contractList,      permissionKey: 'contract_view'         },
      { key: '/contract/dashboard',  icon: <DashboardOutlined />, label: NAV_PAGE.contractDashboard, permissionKey: 'contract_view'         },
      { key: '/contract/expiring',   icon: <AlertOutlined />,     label: NAV_PAGE.contractExpiring,  permissionKey: 'contract_expiring_view' },
      { key: '/contract/claims',     icon: <DollarOutlined />,    label: NAV_PAGE.contractClaims,    permissionKey: 'contract_claims_view'    },
      // 2026-07-21：「續約申請」（簽核式申請流程）已改為「原合約複製續約」，本選單項目隱藏
      // （路由與權限一併移除，見 router/index.tsx、role_permissions.py；頁面檔案與後端端點保留不刪）。
      { key: '/contract/calendar',   icon: <CalendarOutlined />,  label: NAV_PAGE.contractCalendar,  permissionKey: 'contract_view'           },
      { key: '/contract/compare',    icon: <SwapOutlined />,      label: NAV_PAGE.contractCompare,   permissionKey: 'contract_view'           },
      { key: '/contract/import',     icon: <UploadOutlined />,    label: NAV_PAGE.contractImport,    permissionKey: 'contract_create_edit'    },
      { key: '/contract/vendors',    icon: <TeamOutlined />,      label: NAV_PAGE.contractVendors,   permissionKey: 'contract_vendor_manage' },
      { key: '/contract/settings',   icon: <SettingOutlined />,   label: NAV_PAGE.contractSettings,  permissionKey: 'contract_admin'        },
      // 使用手冊（2026-08-14）：比照週採手冊的精神，開放給所有看得到合約模組的人，
      // 不另立新的 permission key（合約模組整組已掛 contract_view，見本群組上層）。
      { key: '/contract/manual',     icon: <BookOutlined />,      label: NAV_PAGE.contractManual,    permissionKey: 'contract_view'         },
    ],
  },
  {
    key: 'hotel',
    icon: <HomeOutlined />,
    label: NAV_GROUP.hotel,
    permissionKey: 'hotel_view',
    children: [
      { key: '/hotel/overview',                 icon: <DashboardOutlined />, label: NAV_PAGE.hotelMgmtDashboard,   permissionKey: 'hotel_view'                       },
      // { key: '/hotel/room-maintenance',        icon: <ToolOutlined />, label: NAV_PAGE.roomMaintenance },
      { key: '/hotel/room-maintenance-detail',  icon: <ToolOutlined />,    label: NAV_PAGE.roomMaintenanceDetail, permissionKey: 'hotel_room_maintenance_view'      },
      { key: '/hotel/periodic-maintenance',     icon: <FileTextOutlined />, label: NAV_PAGE.periodicMaintenance,  permissionKey: 'hotel_periodic_maintenance_view'  },
      { key: '/hotel/ihg-room-maintenance',     icon: <ToolOutlined />,    label: NAV_PAGE.ihgRoomMaintenance,   permissionKey: 'hotel_ihg_room_maintenance_view'  },
      { key: '/hotel/daily-inspection',         icon: <SafetyOutlined />,  label: NAV_PAGE.hotelDailyInspection, permissionKey: 'hotel_daily_inspection_view'      },
      { key: '/hotel/daily-meter-readings',     icon: <DatabaseOutlined />, label: NAV_PAGE.hotelMeterReadings,   permissionKey: 'hotel_meter_readings_view'        },
      { key: '/hotel/other-tasks',              icon: <AlertOutlined />,   label: NAV_PAGE.otherTasks,           permissionKey: 'hotel_other_tasks_view'           },
      // 2026-07-14：hotel_routine_pm 安全下線（與 hotel/periodic-maintenance 重複，
      // 使用者確認後者為正式模組），選單項目移除，路由與後端註冊同步停用。
      // { key: '/hotel/routine-maintenance',      icon: <FileTextOutlined />, label: NAV_PAGE.hotelRoutineMaintenance, permissionKey: 'hotel_routine_pm_view'           },
      { key: '/hotel/calendar',                 icon: <CalendarOutlined />, label: NAV_PAGE.hotelCalendar,           permissionKey: 'hotel_calendar_view'             },
      // { key: '/hotel/repairs',                 icon: <ToolOutlined />, label: NAV_PAGE.repairs },
      // ── 飯店班表（L2 群組）───────────────────────────────────────────
      // 2026-08-14 由原本的頂層「班表」群組搬入。與商場班表是完全獨立的兩套資料。
      {
        key: 'hotel-schedule-group',
        icon: <ScheduleOutlined />,
        label: NAV_GROUP.hotelSchedule,
        permissionKey: 'hotel_schedule_view',
        children: [
          { key: '/hotel/schedule',             icon: <TableOutlined />,       label: NAV_PAGE.hotelScheduleOverview,    permissionKey: 'hotel_schedule_view'   },
          { key: '/hotel/schedule/calendar',    icon: <CalendarOutlined />,    label: NAV_PAGE.hotelScheduleCalendar,    permissionKey: 'hotel_schedule_view'   },
          { key: '/hotel/schedule/import',      icon: <UploadOutlined />,      label: NAV_PAGE.hotelScheduleImport,      permissionKey: 'hotel_schedule_manage' },
          { key: '/hotel/schedule/staff',       icon: <TeamOutlined />,        label: NAV_PAGE.hotelScheduleStaff,       permissionKey: 'hotel_schedule_admin'  },
          { key: '/hotel/schedule/shifts',      icon: <ClockCircleOutlined />, label: NAV_PAGE.hotelScheduleShifts,      permissionKey: 'hotel_schedule_admin'  },
          { key: '/hotel/schedule/departments', icon: <DatabaseOutlined />,    label: NAV_PAGE.hotelScheduleDepartments, permissionKey: 'hotel_schedule_admin'  },
          // 操作手冊不另立 permission key，沿用模組的 *_view（比照合約／週採慣例）
          { key: '/hotel/schedule/manual',      icon: <BookOutlined />,        label: NAV_PAGE.hotelScheduleManual,      permissionKey: 'hotel_schedule_view'   },
        ],
      },
    ],
  },
  // ── 飯店 Dashboard PPT 匯出設定（一階，全公司共用）──────────────────────────
  {
    key: '/ppt-export',
    icon: <FilePptOutlined />,
    label: NAV_PAGE.pptExport,
    permissionKey: 'hotel_overview_ppt_config',
  },
  {
    key: 'mall',
    icon: <ShopOutlined />,
    label: NAV_GROUP.mall,
    permissionKey: 'mall_view',
    children: [
      // ── 商場管理 Dashboard（整合 5 來源總覽，置於群組最頂）─────────────
      { key: '/mall/overview', icon: <DashboardOutlined />, label: NAV_PAGE.mallMgmtDashboard, permissionKey: 'mall_overview_view' },
      // ── 商場例行維護（L2 群組）→ 三個 L3 子項目 ──────────────────────
      {
        key: 'mall-pm-group',
        icon: <FileTextOutlined />,
        label: NAV_GROUP.mallPmGroup,
        children: [
          { key: '/mall/dashboard',                 icon: <DashboardOutlined />, label: NAV_PAGE.mallDashboard,            permissionKey: 'mall_dashboard_view'              },
          { key: '/mall/periodic-maintenance',      icon: <FileTextOutlined />,  label: NAV_PAGE.mallPeriodicMaintenance,  permissionKey: 'mall_periodic_maintenance_view'   },
          { key: '/mall/full-building-maintenance', icon: <ToolOutlined />,      label: NAV_PAGE.fullBuildingMaintenance,  permissionKey: 'mall_full_building_maintenance_view' },
        ],
      },
      { key: '/full-building-inspection/dashboard', icon: <SafetyOutlined />, label: NAV_PAGE.fullBuildingDashboard, permissionKey: 'mall_full_building_inspection_view' },
      { key: '/mall-facility-inspection/dashboard', icon: <ToolOutlined />,    label: NAV_PAGE.mallFacilityDashboard, permissionKey: 'mall_facility_inspection_view'      },
      { key: '/mall/other-tasks',                   icon: <AlertOutlined />,   label: NAV_PAGE.otherTasks,           permissionKey: 'mall_other_tasks_view'            },
      { key: '/mall/calendar',                      icon: <CalendarOutlined />, label: NAV_PAGE.mallCalendar,         permissionKey: 'mall_calendar_view'              },
      // ── 商場班表（L2 群組）───────────────────────────────────────────
      // 2026-08-14 新增。與飯店班表是完全獨立的兩套資料：班別、部門、人員主檔皆不互通，
      // 各自匯入且不做人員比對（兩邊人員可互相支援）。
      {
        key: 'mall-schedule-group',
        icon: <ScheduleOutlined />,
        label: NAV_GROUP.mallSchedule,
        permissionKey: 'mall_schedule_view',
        children: [
          { key: '/mall/schedule',             icon: <TableOutlined />,       label: NAV_PAGE.mallScheduleOverview,    permissionKey: 'mall_schedule_view'   },
          { key: '/mall/schedule/calendar',    icon: <CalendarOutlined />,    label: NAV_PAGE.mallScheduleCalendar,    permissionKey: 'mall_schedule_view'   },
          { key: '/mall/schedule/import',      icon: <UploadOutlined />,      label: NAV_PAGE.mallScheduleImport,      permissionKey: 'mall_schedule_manage' },
          { key: '/mall/schedule/staff',       icon: <TeamOutlined />,        label: NAV_PAGE.mallScheduleStaff,       permissionKey: 'mall_schedule_admin'  },
          { key: '/mall/schedule/shifts',      icon: <ClockCircleOutlined />, label: NAV_PAGE.mallScheduleShifts,      permissionKey: 'mall_schedule_admin'  },
          { key: '/mall/schedule/departments', icon: <DatabaseOutlined />,    label: NAV_PAGE.mallScheduleDepartments, permissionKey: 'mall_schedule_admin'  },
          { key: '/mall/schedule/manual',      icon: <BookOutlined />,        label: NAV_PAGE.mallScheduleManual,      permissionKey: 'mall_schedule_view'   },
        ],
      },
    ],
  },
  // ── 商場工務報修（商場管理之後）──────────────────────────────────────────
  // ⚠️  /exec-dashboard 與 /work-category-analysis 已移至頂層一階（Dashboard 正後方）
  {
    key: 'luqun-repair',
    icon: <ToolOutlined />,
    label: NAV_GROUP.luqun_repair,
    permissionKey: 'luqun_repair_view',
    children: [
      { key: '/luqun-repair/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.luqunRepairDashboard, permissionKey: 'luqun_repair_view' },
    ],
  },
  // ── 大直工務部（商場工務報修之後）──────────────────────────────────────────
  // ⚠️  /exec-dashboard 與 /work-category-analysis 已移至頂層一階（Dashboard 正後方）
  {
    key: 'dazhi-repair',
    icon: <ToolOutlined />,
    label: NAV_GROUP.dazhi_repair,
    permissionKey: 'dazhi_repair_view',
    children: [
      { key: '/dazhi-repair/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.dazhiRepairDashboard, permissionKey: 'dazhi_repair_view' },
    ],
  },
  // ── AI 工單查詢助理（開發期間預設不分配角色，須手動在權限設定開放）────────────
  {
    key: '/ai-assistant',
    icon: <RobotOutlined />,
    label: NAV_PAGE.aiWorkorderAssistant,
    permissionKey: 'ai_workorder_view',
  },
  // 春大直商場工務巡檢已整合至商場管理群組，不再獨立顯示
  // ── 保全巡檢（整合為單一入口，各 Sheet 改為頁面內 TAB）───────────────────────
  // 舊路由 /security/patrol/:sheetKey 保留可直接存取，但不顯示於選單
  {
    key: '/security/dashboard',
    icon: <SafetyOutlined />,
    label: NAV_GROUP.security,
    permissionKey: 'security_view',
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
    permissionKey: 'approvals_view',
    children: [
      { key: '/approvals/list', icon: <FileTextOutlined />, label: NAV_PAGE.approvalsList, permissionKey: 'approvals_view'   },
      { key: '/approvals/new',  icon: <FileTextOutlined />, label: NAV_PAGE.approvalsNew,  permissionKey: 'approvals_manage' },
    ],
  },
  {
    key: 'memos',
    icon: <NotificationOutlined />,
    label: NAV_GROUP.memos,
    permissionKey: 'memos_view',
    children: [
      { key: '/memos/list', icon: <NotificationOutlined />, label: NAV_PAGE.memosList, permissionKey: 'memos_view'   },
      { key: '/memos/new',  icon: <PlusCircleOutlined />,   label: NAV_PAGE.memosNew,  permissionKey: 'memos_manage' },
    ],
  },
  // ── 知識庫（LLM Wiki）────────────────────────────────────────────────────
  {
    key: '/wiki',
    icon: <ReadOutlined />,
    label: NAV_GROUP.wiki,
    // 2026-08-11：原本沒有 permissionKey，而 filterMenuByPermissions 視「沒設 = 公開」，
    // 導致知識庫對所有角色顯示。對應 role_permissions.py PERMISSION_DEFINITIONS 的 wiki_view。
    permissionKey: 'wiki_view',
  },
  // ── 營運分析（OPERA）─────────────────────────────────────────────────────
  // 2026-08-04 新增。Portal 首個「檔案上傳型」資料模組（人工上傳 OPERA TXT），
  // 不走 Ragic 同步，故不需登錄 sync_tool.py MODULES 與 RagicConnections.tsx。
  // 位置：業主指定放在側邊欄最下方、系統設定之前。
  {
    key: 'opera',
    icon: <FundOutlined />,
    label: NAV_GROUP.opera,
    permissionKey: 'opera_view',
    children: [
      { key: '/opera/dashboard', icon: <DashboardOutlined />, label: NAV_PAGE.operaDashboard, permissionKey: 'opera_view'         },
      { key: '/opera/revenue',   icon: <BarChartOutlined />,  label: NAV_PAGE.operaRevenue,   permissionKey: 'opera_revenue_view' },
      { key: '/opera/guest',     icon: <TeamOutlined />,      label: NAV_PAGE.operaGuest,     permissionKey: 'opera_guest_view'   },
      { key: '/opera/import',    icon: <UploadOutlined />,    label: NAV_PAGE.operaImport,    permissionKey: 'opera_import'       },
      // 2026-08-04：「匯入紀錄」併入「資料匯入」頁的 TAB，選單不再另立一項。
      // /opera/batches 路由仍保留（導向 /opera/import?tab=batches），舊書籤不會壞。
      // ── 房價預測（2026-08-05）：歷史同期查詢共用 opera_view（純唯讀歷史事實）──
      { key: '/opera/lookup',    icon: <HistoryOutlined />,   label: NAV_PAGE.operaLookup,    permissionKey: 'opera_view'          },
      { key: '/opera/forecast',  icon: <LineChartOutlined />, label: NAV_PAGE.operaForecast,  permissionKey: 'opera_forecast_view' },
      // 2026-08-05：「事件月曆」併入 /opera/forecast 的 TAB，故不再列於選單。
      //   /opera/events 路由仍保留（導向 /opera/forecast?tab=events），舊書籤不會壞。
      // ── 市場區隔分析（2026-08-07）──────────────────────────────────────
      // ⚠️ 資料來源是 OHIP API 落地，不是本模組其他頁的 TXT 上傳。
      //    放在營運分析是因為時間語意一致（都是落地的歷史資料），
      //    畫面上有標示來源。permissionKey 另開，不共用 opera_revenue_view。
      { key: '/opera/segments',  icon: <PieChartOutlined />,  label: NAV_PAGE.operaSegments,  permissionKey: 'opera_segment_view' },
      // ── 訂房分析（2026-08-07）──────────────────────────────────────────
      // ⚠️ 與上面的「住客與通路分析」**分析母體不同**（所有訂房 vs 已離店住客），
      //    不是同一份資料的兩個版本。因此另開 permissionKey，不共用 opera_guest_view。
      { key: '/opera/reservations', icon: <ScheduleOutlined />, label: NAV_PAGE.operaReservations, permissionKey: 'opera_reservation_view' },
      // ── 訂房 Pace／Pickup（2026-08-13）──────────────────────────────────
      // ⚠️ 與上面的「訂房分析」看的是同一批資料，但**多一個 as_of 觀察時點**：
      //    那邊看訂單「現在」長什麼樣，這邊看「某個過去時點看到的在手訂房」。
      //    因為數字是回推出來的（訂房同步整列覆寫、無版本），可信度與那邊不同，
      //    所以另開 permissionKey，不共用 opera_reservation_view。
      { key: '/opera/pace',      icon: <RiseOutlined />,      label: NAV_PAGE.operaPace,      permissionKey: 'opera_pace_view'    },
      { key: '/opera/settings',  icon: <SettingOutlined />,   label: NAV_PAGE.operaSettings,  permissionKey: 'opera_admin'        },
      { key: '/opera/manual',    icon: <ReadOutlined />,      label: NAV_PAGE.operaManual,    permissionKey: 'opera_view'         },
    ],
  },
  // ── 即時營運 ─────────────────────────────────────────────────────────────
  // 2026-08-06 新增。資料**直接來自 OPERA Cloud（OHIP）REST API**，不是上傳的 TXT。
  // 刻意與「營運分析」分成兩個一級選單：兩者資料時點不同（API 即時 vs 上傳落後數天），
  // 放在同一個群組會讓使用者以為是同一份資料。
  // 不走 Ragic 同步，故不需登錄 sync_tool.py MODULES 與 RagicConnections.tsx。
  // ⚠️ 每次查詢都會實際呼叫 OHIP（按呼叫量計費），權限預設不給任何既有角色。
  // 規格書：docs/SPEC_realtime_operations.md
  {
    key: 'realtime',
    icon: <ThunderboltOutlined />,
    label: NAV_GROUP.realtime,
    permissionKey: 'realtime_view',
    children: [
      { key: '/realtime/dashboard', icon: <DashboardOutlined />,  label: NAV_PAGE.realtimeDashboard, permissionKey: 'realtime_view'    },
      { key: '/realtime/revenue',   icon: <BarChartOutlined />,   label: NAV_PAGE.realtimeRevenue,   permissionKey: 'realtime_revenue' },
      { key: '/realtime/compare',   icon: <SwapOutlined />,       label: NAV_PAGE.realtimeCompare,   permissionKey: 'realtime_compare' },
      { key: '/realtime/logs',      icon: <FileSearchOutlined />, label: NAV_PAGE.realtimeLogs,      permissionKey: 'realtime_view'    },
      { key: '/realtime/manual',    icon: <ReadOutlined />,      label: NAV_PAGE.realtimeManual,    permissionKey: 'realtime_view'    },
    ],
  },
  // ── 金旭分析 ─────────────────────────────────────────────────────────────
  // 2026-08-05 新增。Portal 第二個「檔案上傳型」資料模組（人工上傳金旭 xlsx：
  // FCR02 客帳帳目明細表 + 訂房狀況表），不走 Ragic 同步。
  // 路由前綴 /jinxu/*，與 /opera/* 完全獨立、不共用任何端點或資料表（業主指定）。
  // 位置：緊接營運分析之後，兩個 PMS 分析模組相鄰。
  //
  // ⚠️ 「取消與訂價落差分析」（jinxu_cancel_view）刻意不列於此——它是
  //    /jinxu/reservation 頁的 TAB 而非獨立路由，但仍登錄於 PERMISSION_DEFINITIONS，
  //    否則管理員無從授權。
  {
    key: 'jinxu',
    icon: <FundOutlined />,
    label: NAV_GROUP.jinxu,
    permissionKey: 'jinxu_view',
    children: [
      { key: '/jinxu/dashboard',   icon: <DashboardOutlined />, label: NAV_PAGE.jinxuDashboard,   permissionKey: 'jinxu_view'         },
      { key: '/jinxu/reservation', icon: <TeamOutlined />,      label: NAV_PAGE.jinxuReservation, permissionKey: 'jinxu_resv_view'    },
      { key: '/jinxu/revenue',     icon: <BarChartOutlined />,  label: NAV_PAGE.jinxuRevenue,     permissionKey: 'jinxu_revenue_view' },
      { key: '/jinxu/payment',     icon: <LineChartOutlined />, label: NAV_PAGE.jinxuPayment,     permissionKey: 'jinxu_payment_view' },
      { key: '/jinxu/deposit',     icon: <HistoryOutlined />,   label: NAV_PAGE.jinxuDeposit,     permissionKey: 'jinxu_deposit_view' },
      { key: '/jinxu/import',      icon: <UploadOutlined />,    label: NAV_PAGE.jinxuImport,      permissionKey: 'jinxu_import'       },
      { key: '/jinxu/settings',    icon: <SettingOutlined />,   label: NAV_PAGE.jinxuSettings,    permissionKey: 'jinxu_admin'        },
      // 使用手冊共用 jinxu_view：純唯讀說明頁，另開 key 只會讓權限清單變長而無實質區隔
      { key: '/jinxu/manual',      icon: <ReadOutlined />,      label: NAV_PAGE.jinxuManual,      permissionKey: 'jinxu_view'         },
    ],
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: NAV_GROUP.settings,
    children: [
      { key: '/settings/basic',               icon: <SettingOutlined />,  label: NAV_PAGE.basicSettings,     permissionKey: 'system_admin_only' },
      { key: '/settings/users',               icon: <UserOutlined />,     label: NAV_PAGE.usersManage,       permissionKey: 'settings_users_manage' },
      { key: '/settings/roles',               icon: <SettingOutlined />,  label: NAV_PAGE.rolesManage,       permissionKey: 'settings_roles_manage' },
      { key: '/settings/ragic-app-directory', icon: <DatabaseOutlined />, label: NAV_PAGE.ragicAppDirectory, permissionKey: 'settings_ragic_manage' },
      { key: '/settings/company-departments', icon: <ApartmentOutlined />, label: NAV_PAGE.companyDepartments, permissionKey: 'settings_departments_manage' },
      { key: '/settings/ragic-connections',   icon: <ApiOutlined />,      label: NAV_PAGE.ragicConnections,  permissionKey: 'settings_ragic_manage' },
      { key: '/settings/ragic-field-audit',   icon: <AuditOutlined />,    label: NAV_PAGE.ragicFieldAudit,   permissionKey: 'ragic_field_audit_view' },
      { key: '/settings/menu-config',              icon: <MenuOutlined />,      label: NAV_PAGE.menuConfig,           permissionKey: 'settings_menu_manage' },
      { key: '/settings/static-pages',             icon: <FileTextOutlined />,  label: NAV_PAGE.staticPages,          permissionKey: 'settings_menu_manage' },
      { key: '/settings/employee-manual-export',   icon: <BookOutlined />,      label: NAV_PAGE.employeeManualExport, permissionKey: 'system_admin_only' },
      { key: '/settings/knowledge-graph',          icon: <ApartmentOutlined />, label: NAV_PAGE.knowledgeGraph,       permissionKey: 'system_admin_only' },
      { key: '/settings/repair-unfinished-report', icon: <AlertOutlined />,     label: NAV_PAGE.repairUnfinishedReport, permissionKey: 'repair_unfinished_report_view' },
      { key: '/settings/usage-monitor',            icon: <BarChartOutlined />,  label: NAV_PAGE.usageMonitor,           permissionKey: 'system_admin_only' },
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

  // 建立 base 項目的 label / icon / permissionKey 對照表，讓 buildItem 可查回原始標籤與權限
  // 解決：base 模組被移到三階時，label 顯示 key（如 /mall/dashboard）的問題
  // 同時保留 permissionKey，避免 reparented 項目因 buildItem 不帶 permissionKey
  // 而被 filterMenuByPermissions 誤判為公開（hasPermission(undefined) → true）
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const baseItemInfo = new Map<string, { label: any; icon?: any; permissionKey?: string | null }>()
  base.forEach((p: any) => {
    baseItemInfo.set(p.key, { label: p.label, icon: p.icon, permissionKey: p.permissionKey })
    ;(p.children ?? []).forEach((c: any) => {
      baseItemInfo.set(c.key, { label: c.label, icon: c.icon, permissionKey: c.permissionKey })
    })
  })

  // 從 DB config 建出一個 menu item（可能含三層）
  // 優先序：custom_label > base 結構的原始 label > menu_key
  // icon 優先序：icon_key(DB) > base 結構原始 icon > FileTextOutlined fallback
  // 若 icon_key='none'，resolveIcon 回傳 undefined，最終 icon 設為 null（明確隱藏）
  const buildItem = (cfg: MenuConfigItem): any => {
    const grandchildren = (childrenByParent.get(cfg.menu_key) ?? [])
      .filter((g) => g.is_visible !== false)
      .sort((a, b) => a.sort_order - b.sort_order)
      .map((g) => buildItem(g))
    const baseInfo = baseItemInfo.get(cfg.menu_key)
    const icon = resolveIcon(cfg.icon_key, baseInfo?.icon ?? <FileTextOutlined />)
    return {
      key: cfg.menu_key,
      label: cfg.custom_label || baseInfo?.label || cfg.menu_key,
      icon: icon !== undefined ? icon : null,
      ...(grandchildren.length > 0 ? { children: grandchildren } : {}),
      // 保留 base 原始 permissionKey，讓 filterMenuByPermissions 可在 DB permission_key=null 時 fallback
      ...(baseInfo?.permissionKey !== undefined ? { permissionKey: baseInfo.permissionKey } : {}),
    }
  }

  // 找出「被 DB 換了父層」的 base L2 項目（複用共用函式）
  const reparentedBaseL2 = computeReparentedL2(base, configs)

  // 找出「被降為二階」的 base L1 項目（原本是一階，DB 中有 parent_key）
  // 例：「保全管理」被移到「飯店管理」下成為 L2
  const reparentedBaseL1 = new Map<string, string>() // menu_key -> new_parent_key
  configs.forEach((cfg) => {
    if (cfg.parent_key && baseL1Keys.has(cfg.menu_key)) {
      reparentedBaseL1.set(cfg.menu_key, cfg.parent_key)
    }
  })

  // 套用到預設 base（L1 + L2），並補充 L3
  const cloned = base
    .filter((parent) => {
      if (reparentedBaseL1.has(parent.key)) return false  // 已降為二階，從 L1 移除
      const cfg = cfgMap.get(parent.key)
      return cfg === undefined || cfg.is_visible !== false
    })
    .map((parent) => {
      const pCfg = cfgMap.get(parent.key)
      const pIcon = resolveIcon(pCfg?.icon_key, parent.icon)
      return {
      ...parent,
      icon: pIcon !== undefined ? pIcon : null,
      label: pCfg?.custom_label || parent.label,
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
                  const cIcon2 = resolveIcon(cfgMap.get(child.key)?.icon_key, child.icon)
                  return {
                    ...child,
                    icon: cIcon2 !== undefined ? cIcon2 : null,
                    label: cfgMap.get(child.key)?.custom_label || child.label,
                    children: mergedGc,
                  }
                }

                const cIcon = resolveIcon(cfgMap.get(child.key)?.icon_key, child.icon)
                return {
                  ...child,
                  icon: cIcon !== undefined ? cIcon : null,
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
                const mIcon = resolveIcon(cfg?.icon_key, origItem.icon)
                return [{
                  ...origItem,
                  icon: mIcon !== undefined ? mIcon : null,
                  label: cfg?.custom_label || origItem.label,
                  ...(grandchildren.length > 0 ? { children: grandchildren } : {}),
                }]
              })

            // DB 中此 L1 下、不在 base structure 裡的額外 L2 項目
            // （包含 custom_ 自訂項目、舊版無前綴的使用者項目如 mall-pm-group，
            //   以及被降階的 base L1 項目如「保全管理」→「飯店管理」下）
            // ⚠️  必須用全域 baseL2Keys（所有群組的 L2），而非只有本群組的 base L2，
            //     否則跨群組移過來的 base L2 項目會同時出現在 movedHere 與 customL2Here。
            // ⚠️  reparentedBaseL1 的項目：雖是 baseL1Keys 成員，但已降階到此 L1 下，
            //     必須放行（且只放行移到「這個」L1 下的，防止出現在別的 L1）。
            const customL2Here = (childrenByParent.get(parent.key) ?? [])
              .filter((c) =>
                !baseL2Keys.has(c.menu_key) &&
                (!baseL1Keys.has(c.menu_key) || reparentedBaseL1.get(c.menu_key) === parent.key) &&
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
      }
    })
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
    const l1Icon = resolveIcon(cfg.icon_key, <FileTextOutlined />)
    cloned.push({
      key: cfg.menu_key,
      label: cfg.custom_label || cfg.menu_key,
      icon: l1Icon !== undefined ? l1Icon : null,
      ...(children.length > 0 ? { children } : {}),
    })
  })

  return cloned.sort((a: any, b: any) => {
    const ao = cfgMap.get(a.key)?.sort_order ?? 9999
    const bo = cfgMap.get(b.key)?.sort_order ?? 9999
    return ao - bo
  })
}

/**
 * 依使用者 permissions 過濾 menu items（applyMenuConfig 之後呼叫）。
 * - item.permissionKey 為 null/undefined → 公開顯示
 * - item.permissionKey 有值 → 使用者需具備該 key（或 "*"）才顯示
 * - item.permissionKeys（陣列）→ 符合其中任一 key 即顯示（OR 邏輯，2026-07-19 新增）
 * - DB config 的 permission_key 優先於靜態預設的 permissionKey/permissionKeys
 * - 父層的所有子項都被過濾掉時，父層本身也不顯示
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function filterMenuByPermissions(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  items: any[],
  permissions: string[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dbPermMap: Map<string, string | null>
// eslint-disable-next-line @typescript-eslint/no-explicit-any
): any[] {
  const hasPermission = (key: string | string[] | null | undefined): boolean => {
    if (!key || (Array.isArray(key) && key.length === 0)) return true // 無設定 = 公開
    if (permissions.includes('*')) return true                        // system_admin 萬用符
    const keys = Array.isArray(key) ? key : [key]
    return keys.some((k) => permissions.includes(k))
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const filterItem = (item: any): any | null => {
    // 優先用 DB 設定的 permission_key（非 null 才算有效覆蓋），否則 fallback 到靜態預設
    // ⚠️  DB 值為 null 代表「MenuConfig 頁面未設定」，不應蓋掉程式碼的靜態 permissionKey
    const dbVal = dbPermMap.has(item.key) ? dbPermMap.get(item.key) : undefined
    const effectiveKey: string | string[] | null | undefined =
      dbVal != null ? dbVal : (item.permissionKeys ?? item.permissionKey)

    if (Array.isArray(item.children) && item.children.length > 0) {
      const filteredChildren = item.children
        .map(filterItem)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .filter((c: any) => c !== null)

      // 群組：有子項才顯示，且群組本身也需通過權限
      if (filteredChildren.length === 0) return null
      if (!hasPermission(effectiveKey)) return null
      return { ...item, children: filteredChildren }
    }

    // 葉節點
    return hasPermission(effectiveKey) ? item : null
  }

  return items.map(filterItem).filter(Boolean)
}

// localStorage 快取 key — 儲存上次成功拉取的 MenuConfigItem[]
// 讓進系統時可立即套用，不必等 API 回應，消除選單閃爍
const MENU_CONFIG_CACHE_KEY = 'portal_menu_config_cache'

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)

  // ── Sider 可拖曳調整寬度（左右自由拉伸）─────────────────────────────────────
  const SIDER_WIDTH_KEY = 'portal_sider_width'
  const MIN_SIDER_WIDTH = 180
  const MAX_SIDER_WIDTH = 420
  const DEFAULT_SIDER_WIDTH = 220

  const [siderWidth, setSiderWidth] = useState<number>(() => {
    try {
      const saved = localStorage.getItem(SIDER_WIDTH_KEY)
      const parsed = saved ? parseInt(saved, 10) : NaN
      if (!Number.isNaN(parsed) && parsed >= MIN_SIDER_WIDTH && parsed <= MAX_SIDER_WIDTH) return parsed
    } catch { /* ignore */ }
    return DEFAULT_SIDER_WIDTH
  })
  const [isResizingSider, setIsResizingSider] = useState(false)
  const siderWidthRef = useRef(siderWidth)
  useEffect(() => { siderWidthRef.current = siderWidth }, [siderWidth])

  const handleSiderResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingSider(true)
  }, [])

  useEffect(() => {
    if (!isResizingSider) return
    const handleMouseMove = (e: MouseEvent) => {
      const next = Math.min(MAX_SIDER_WIDTH, Math.max(MIN_SIDER_WIDTH, e.clientX))
      setSiderWidth(next)
    }
    const handleMouseUp = () => {
      setIsResizingSider(false)
      try { localStorage.setItem(SIDER_WIDTH_KEY, String(siderWidthRef.current)) } catch { /* ignore */ }
    }
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    const prevCursor = document.body.style.cursor
    const prevUserSelect = document.body.style.userSelect
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = prevCursor
      document.body.style.userSelect = prevUserSelect
    }
  }, [isResizingSider])
  const navigate = useNavigate()
  const location = useLocation()
  const logout  = useAuthStore((s) => s.logout)
  const setUser = useAuthStore((s) => s.setUser)
  const user    = useAuthStore((s) => s.user)
  const { token: designToken } = theme.useToken()

  // ── 強制改密碼（OTP 登入後）──────────────────────────────────────────────────
  const [forcePwForm]       = Form.useForm()
  const [forcePwLoading,    setForcePwLoading]    = useState(false)
  const [forcePwError,      setForcePwError]      = useState<string | null>(null)
  const mustChangePw = !!user?.must_change_password

  const handleForceChangePw = async () => {
    try {
      const { new_password, confirm_password } = await forcePwForm.validateFields()
      if (new_password !== confirm_password) {
        setForcePwError('兩次輸入的密碼不一致')
        return
      }
      setForcePwLoading(true)
      setForcePwError(null)
      const { authApi: _authApi } = await import('@/api/auth')
      await _authApi.changePasswordForced(new_password)
      // 強制登出，使用者須以新密碼重新登入
      try { await _authApi.logout() } catch { /* ignore */ }
      logout()
      navigate('/login')
      // 使用 setTimeout 確保 navigate 完成後再顯示訊息
      setTimeout(() => {
        import('antd').then(({ message: msg }) => {
          msg.success('密碼已更新，請重新登入')
        })
      }, 300)
    } catch (err: any) {
      if (err?.errorFields) return // form validation error，不處理
      setForcePwError(err?.response?.data?.detail || err?.message || '更新失敗，請稍後再試')
    } finally {
      setForcePwLoading(false)
    }
  }

  // ── 閒置逾時自動登出 ─────────────────────────────────────────────────────────
  const handleIdleLogout = useCallback(async () => {
    try { await authApi.logout() } catch { /* ignore */ }
    logout()
    navigate('/login')
  }, [logout, navigate])

  const { warningVisible, countdown, resetTimer } = useIdleTimeout(
    handleIdleLogout,
    !!user, // 只在登入狀態下啟動
  )

  // 頁面重新整理後 permissions 為 undefined（JWT 不含 permissions），
  // 呼叫 /me 補回權限，讓非 system_admin 使用者的選單與守衛正常運作。
  // /me 成功後設 permissionsReadyRef.current = true，讓 loadMenuConfig 可以關掉 Skeleton。
  useEffect(() => {
    if (user?.id && user.permissions === undefined) {
      authApi.me().then((res) => {
        const me = res.data as any
        permissionsReadyRef.current = true   // 標記 permissions 已就緒
        setUser({
          id:          me.id          || user.id,
          email:       me.email       || user.email,
          name:        me.full_name   || user.name || '',
          full_name:   me.full_name   || '',
          tenant_id:   me.tenant_id   || '',
          tenant_name: me.tenant_name || '',
          roles:       Array.isArray(me.roles)       ? me.roles       : user.roles,
          permissions: Array.isArray(me.permissions) ? me.permissions : [],
          is_active:   me.is_active ?? true,
        })
      }).catch(() => {
        // token 已過期時 PrivateRoute 會處理登出
        // 呼叫失敗也要解鎖 Skeleton，否則 loading 永遠不結束
        permissionsReadyRef.current = true
        setMenuLoading(false)
        // 重要：/me 失敗時也必須把 permissions 從 undefined 改為 []，
        // 否則 PermissionGuard 的 `permissions === undefined` 判斷永遠為 true，
        // 頁面會永久空白（不顯示 403，也不顯示內容）。
        const currentUser = useAuthStore.getState().user
        if (currentUser && currentUser.permissions === undefined) {
          setUser({ ...currentUser, permissions: [] })
        }
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const isSystemAdmin = !!(user?.roles?.includes('system_admin'))
  // 取得 permissions 陣列（用於 filterMenuByPermissions）
  const userPermissions = useMemo<string[]>(
    () => user?.permissions ?? (isSystemAdmin ? ['*'] : []),
    [user?.permissions, isSystemAdmin]
  )

  // ── base items ────────────────────────────────────────────────────────────
  // 2026-08-12：原本這裡對非 system_admin 直接砍掉整個 settings 群組。
  // 權限收斂改版後，「能管帳號／角色」不再等於 system_admin，硬砍會讓具備
  // settings_users_manage / settings_roles_manage 的人看不到自己該用的頁面。
  //
  // 改為完全交給 filterMenuByPermissions 依 permissionKey 逐項過濾：
  //   * settings 群組本身沒有 permissionKey → 子項全被濾掉時群組自動隱藏
  //   * 群組內 4 頁掛 system_admin_only（基本設定／員工手冊／知識圖譜／使用監控），
  //     非 system_admin 沒有這個 key，仍然看不到
  // 效果等價於舊行為，但對持有 settings_* 權限的人正確開放。
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const baseItems = useMemo<any[]>(() => menuItems, [])

  // menuLoading：true  = 正在等待 API 回應（顯示 Skeleton）
  //              false = 已取得正確選單（顯示正確選單）
  // - system_admin：有快取時可立即顯示，無快取才顯示 Skeleton
  // - 非 admin、剛登入（permissions 已在 store）：loadMenuConfig 跑完即可關掉
  // - 非 admin、重新整理（permissions = undefined）：必須等 /me 回來再關
  const [menuLoading, setMenuLoading] = useState<boolean>(() => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return true
      const payload = JSON.parse(atob(token.split('.')[1]))
      const isAdmin = Array.isArray(payload.roles) && payload.roles.includes('system_admin')
      if (isAdmin) return !localStorage.getItem(MENU_CONFIG_CACHE_KEY)
      // 非 admin：一律顯示 Skeleton（等 loadMenuConfig 完成後關掉）
      // 但若 permissions 已在 store（剛登入），permissionsReadyRef 已為 true，
      // 因此 loadMenuConfig 完成後就可以直接關掉。
      return true
    } catch {
      return true
    }
  })

  // 初始值優先使用 localStorage 快取的 config，使進系統時立即顯示正確選單（無閃爍）。
  // 非 system_admin 使用者：JWT 不含 permissions，無法在 /me 回來前正確 filter，
  // 因此無快取時一律回傳空陣列，由 menuLoading Skeleton 佔位，等 loadMenuConfig 完成後填入。
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [dynamicMenuItems, setDynamicMenuItems] = useState<any[]>(() => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return []
      const payload = JSON.parse(atob(token.split('.')[1]))
      const isAdmin = Array.isArray(payload.roles) && payload.roles.includes('system_admin')

      const cached = localStorage.getItem(MENU_CONFIG_CACHE_KEY)

      if (isAdmin) {
        // system_admin：有 ['*'] 權限，快取可立即套用
        const filtered = menuItems  // admin 顯示全部（含 settings）
        if (cached) {
          const configs = JSON.parse(cached) as MenuConfigItem[]
          const dbPermMap = new Map<string, string | null>(
            configs.map((c) => [c.menu_key, c.permission_key])
          )
          const applied = configs.length > 0 ? applyMenuConfig(filtered, configs) : filtered
          return filterMenuByPermissions(applied, ['*'], dbPermMap)
        }
        return []
      }

      // 非 admin：JWT 無 permissions，必須等 /me + loadMenuConfig 完成後才能正確 filter
      // 不論有無快取，都先回傳空陣列，讓 Skeleton 佔位，避免閃爍一堆不該看到的項目
      return []
    } catch {
      return []
    }
  })

  // 世代計數器：確保只有最新的 loadMenuConfig 呼叫能更新 state（防止 race condition）
  const menuGenRef = useRef(0)

  // 非 admin 使用者：必須等 /me 回來後才知道真正的 permissions，才能關掉 Skeleton。
  // 已就緒條件：
  //   1. system_admin（永遠有 ['*'] 權限，無需等 /me）
  //   2. 剛登入（login response 已帶回 permissions，user.permissions !== undefined）
  //   3. /me 成功後由 setUser useEffect 設為 true
  const permissionsReadyRef = useRef(isSystemAdmin || user?.permissions !== undefined)

  // 啟動時拉取 menu config，套用後更新選單並寫入快取
  const loadMenuConfig = useCallback(async () => {
    const myGen = ++menuGenRef.current
    try {
      const configs = await fetchMenuConfig()
      if (myGen !== menuGenRef.current) return   // 已有更新的呼叫，丟棄此次結果
      // 成功後寫入快取，供下次進系統立即使用
      try { localStorage.setItem(MENU_CONFIG_CACHE_KEY, JSON.stringify(configs)) } catch { /* quota 滿時靜默略過 */ }
      // 建立 DB permission_key 覆蓋 Map（menu_key → permission_key）
      const dbPermMap = new Map<string, string | null>(
        configs.map((c) => [c.menu_key, c.permission_key])
      )
      const applied = configs.length > 0 ? applyMenuConfig(baseItems, configs) : baseItems
      setDynamicMenuItems(filterMenuByPermissions(applied, userPermissions, dbPermMap))
    } catch {
      if (myGen !== menuGenRef.current) return   // 同上，丟棄過期結果
      // 拉取失敗：嘗試從快取救援；完全無快取才 fallback 靜態 menuItems
      const cached = localStorage.getItem(MENU_CONFIG_CACHE_KEY)
      if (!cached) {
        setDynamicMenuItems(filterMenuByPermissions(baseItems, userPermissions, new Map()))
      }
      // 有快取時保持現有 dynamicMenuItems 不動（快取已在 useState 初始化時套用）
    } finally {
      // 非 admin 使用者必須等 permissionsReadyRef 為 true（/me 已回應）才關 Skeleton；
      // 否則第一次帶著空 userPermissions 跑完就關掉，選單會是空的，閃爍問題復現。
      if (myGen === menuGenRef.current && permissionsReadyRef.current) {
        setMenuLoading(false)
      }
    }
  }, [baseItems, userPermissions])

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

  // 供 Outlet 子元件（HomeRedirect）判斷首頁用：與側邊欄完全同一份選單
  const menuItemsCtxValue = useMemo(
    () => ({ items: dynamicMenuItems, loading: menuLoading }),
    [dynamicMenuItems, menuLoading]
  )

  const userMenu = {
    items: [
      { key: 'profile', icon: <UserOutlined />, label: '個人資料' },
      { type: 'divider' as const },
      {
        key: 'logout',
        icon: <LogoutOutlined />,
        label: '登出',
        danger: true,
        onClick: () => {
          // 登出時清除 menu config 快取（DB 資料快照，下個使用者應重新拉取）
          // 首頁設定（portal_home_page_route）屬於使用者偏好，保留不清除，
          // 跨帳號的無權限情況由頁面層 PermissionGuard 處理
          localStorage.removeItem(MENU_CONFIG_CACHE_KEY)
          logout()
          navigate('/login')
        },
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
        width={siderWidth}
        style={{
          background: designToken.colorBgContainer,
          borderRight: `1px solid ${designToken.colorBorderSecondary}`,
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          transition: isResizingSider ? 'none' : undefined,
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
              {getSiteTitle()}
            </Text>
          )}
        </div>

        {menuLoading ? (
          // 無快取（首次登入）：等待 API 期間顯示 Skeleton，不顯示靜態選單
          <div style={{ padding: '16px 20px' }}>
            {Array.from({ length: 10 }).map((_, i) => (
              <Skeleton.Input
                key={i}
                active
                size="small"
                style={{
                  width: i % 3 === 0 ? '60%' : '80%',
                  marginBottom: 14,
                  display: 'block',
                  borderRadius: 4,
                }}
              />
            ))}
          </div>
        ) : (
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
        )}

        {/* 拖曳把手：左右自由調整 Sider 寬度（收合時不顯示）───────────────── */}
        {!collapsed && (
          <div
            onMouseDown={handleSiderResizeStart}
            title="拖曳調整選單寬度"
            style={{
              position: 'absolute',
              top: 0,
              right: -3,
              width: 6,
              height: '100%',
              cursor: 'col-resize',
              zIndex: 101,
              background: isResizingSider ? designToken.colorPrimary : 'transparent',
              transition: isResizingSider ? 'none' : 'background 0.15s',
            }}
            onMouseEnter={(e) => {
              if (!isResizingSider) e.currentTarget.style.background = designToken.colorBorder
            }}
            onMouseLeave={(e) => {
              if (!isResizingSider) e.currentTarget.style.background = 'transparent'
            }}
          />
        )}
      </Sider>

      {/* ── Main ──────────────────────────────────────────────────────── */}
      <Layout style={{ marginLeft: collapsed ? 80 : siderWidth, transition: isResizingSider ? 'none' : 'margin-left 0.2s' }}>
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
          {/* 權限尚未載入（undefined）→ 等待中，不顯示錯誤 */}
          {/* 權限已載入但為空（[]）且非 system_admin → 無任何模組授權，顯示提示 */}
          {!isSystemAdmin && user?.permissions !== undefined && userPermissions.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '60vh',
              gap: 16,
              color: '#64748b',
            }}>
              <div style={{ fontSize: 56 }}>🔐</div>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#1B3A5C' }}>尚未設定任何功能權限</div>
              <div style={{ fontSize: 15, color: '#64748b' }}>您的帳號目前沒有任何模組的存取權限</div>
              <div style={{ fontSize: 14, color: '#94a3b8' }}>請洽系統管理員調整角色權限設定</div>
            </div>
          ) : (
            <MenuItemsContext.Provider value={menuItemsCtxValue}>
              <Outlet />
            </MenuItemsContext.Provider>
          )}
        </Content>
      </Layout>

      {/* ── 閒置逾時警告 Modal ──────────────────────────────────────────── */}
      <Modal
        open={warningVisible}
        closable={false}
        maskClosable={false}
        footer={null}
        width={420}
        centered
      >
        <div style={{ textAlign: 'center', padding: '8px 0 4px' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>⏱️</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#1B3A5C', marginBottom: 8 }}>
            閒置逾時提醒
          </div>
          <div style={{ fontSize: 14, color: '#64748b', marginBottom: 4 }}>
            您已閒置超過 15 分鐘，系統將在
          </div>
          <div style={{ fontSize: 32, fontWeight: 800, color: '#e74c3c', margin: '8px 0' }}>
            {countdown} 秒
          </div>
          <div style={{ fontSize: 14, color: '#64748b', marginBottom: 20 }}>
            後自動登出以保護您的帳號安全
          </div>
          <Button
            type="primary"
            size="large"
            block
            onClick={resetTimer}
            style={{ background: '#1B3A5C', borderColor: '#1B3A5C' }}
          >
            繼續使用
          </Button>
        </div>
      </Modal>

      {/* ── 強制改密碼 Modal（OTP 登入後，不可關閉）──────────────────────── */}
      <Modal
        open={mustChangePw}
        closable={false}
        maskClosable={false}
        keyboard={false}
        footer={null}
        width={440}
        centered
      >
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>🔑</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#1B3A5C', marginBottom: 4 }}>
            請設定新密碼
          </div>
          <div style={{ fontSize: 13, color: '#64748b' }}>
            您使用一次性密碼登入，必須立即設定新密碼才能繼續使用系統。
          </div>
        </div>
        {forcePwError && (
          <Alert type="error" message={forcePwError} showIcon style={{ marginBottom: 12 }} />
        )}
        <Form form={forcePwForm} layout="vertical" requiredMark={false}>
          <Form.Item
            name="new_password"
            label="新密碼"
            rules={[
              { required: true, message: '請輸入新密碼' },
              { min: 8, message: '至少 8 個字元' },
            ]}
          >
            <Input.Password placeholder="至少 8 個字元" size="large" />
          </Form.Item>
          <Form.Item
            name="confirm_password"
            label="確認新密碼"
            rules={[{ required: true, message: '請再次輸入新密碼' }]}
          >
            <Input.Password placeholder="再次輸入新密碼" size="large" />
          </Form.Item>
          <Button
            type="primary"
            size="large"
            block
            loading={forcePwLoading}
            onClick={handleForceChangePw}
            style={{ background: '#1B3A5C', borderColor: '#1B3A5C', marginTop: 4 }}
          >
            {forcePwLoading ? '更新中…' : '確認更新密碼'}
          </Button>
          <div style={{ marginTop: 8, fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
            設定完成後將自動跳轉至系統首頁
          </div>
        </Form>
      </Modal>
    </Layout>
  )
}
