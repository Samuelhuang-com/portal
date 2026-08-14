/**
 * App Router
 */
import { useEffect } from 'react'
import { Routes, Route, Navigate, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

// ── JWT 過期判斷（純前端解碼，不送 request）──────────────────────────────────
function isJwtExpired(token: string | null): boolean {
  if (!token) return true
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return typeof payload.exp === 'number' && payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

import MainLayout from '@/components/Layout/MainLayout'
import { useMenuItemsContext } from '@/components/Layout/menuItemsContext'
import { getHomePageRoute, isRouteInMenu, firstRouteInMenu } from '@/utils/homePage'
import LoginPage           from '@/pages/Login'
import DashboardPage       from '@/pages/Dashboard'
import RoomMaintenancePage       from '@/pages/RoomMaintenance'
import RoomMaintenanceDetailPage from '@/pages/RoomMaintenanceDetail'
import InventoryPage             from '@/pages/Inventory'
import PeriodicMaintenancePage       from '@/pages/PeriodicMaintenance'
import PeriodicMaintenanceDetailPage from '@/pages/PeriodicMaintenance/Detail'
// 2026-07-14：hotel_routine_pm 安全下線（與 hotel/periodic-maintenance 重複，使用者確認
// 後者為正式模組）。import 保留但下方路由已停用，頁面檔案未刪，可隨時復原。
// import HotelRoutineMaintenancePage   from '@/pages/HotelRoutineMaintenance'
import MallMgmtDashboardPage             from '@/pages/MallMgmtDashboard'
import MallDashboardPage                 from '@/pages/MallDashboard'
import MallPeriodicMaintenancePage       from '@/pages/MallPeriodicMaintenance'
import MallPeriodicMaintenanceDetailPage from '@/pages/MallPeriodicMaintenance/Detail'
import B4FInspectionPage                 from '@/pages/B4FInspection'
import B4FInspectionDetailPage           from '@/pages/B4FInspection/Detail'
import RFInspectionPage                  from '@/pages/RFInspection'
import RFInspectionDetailPage            from '@/pages/RFInspection/Detail'
import B2FInspectionPage                 from '@/pages/B2FInspection'
import B2FInspectionDetailPage           from '@/pages/B2FInspection/Detail'
import B1FInspectionPage                 from '@/pages/B1FInspection'
import B1FInspectionDetailPage           from '@/pages/B1FInspection/Detail'
import SecurityDashboardPage             from '@/pages/SecurityDashboard'
import SecurityPatrolPage                from '@/pages/SecurityPatrol'
import SecurityPatrolDetailPage          from '@/pages/SecurityPatrol/Detail'
import UsersPage           from '@/pages/Settings/Users'
import RolesPage           from '@/pages/Settings/Roles'
import RagicConnectionsPage from '@/pages/Settings/RagicConnections'
import RagicAppDirectoryPage from '@/pages/Settings/RagicAppDirectory'
import BasicSettingsPage     from '@/pages/Settings/BasicSettings'
import MenuConfigPage        from '@/pages/Settings/MenuConfig'
import EmployeeManualExportPage from '@/pages/Settings/EmployeeManualExport'
import KnowledgeGraphPage        from '@/pages/Settings/KnowledgeGraph'
import StaticPagesPage           from '@/pages/Settings/StaticPages'
import RagicFieldAuditPage        from '@/pages/Settings/RagicFieldAudit'
import RepairUnfinishedReportPage from '@/pages/Settings/RepairUnfinishedReport'
import UsageMonitorPage           from '@/pages/Settings/UsageMonitor'
import ApprovalListPage   from '@/pages/Approvals/List'
import ApprovalNewPage    from '@/pages/Approvals/New'
import ApprovalDetailPage from '@/pages/Approvals/Detail'
import MemoListPage       from '@/pages/Memos/List'
import MemoNewPage        from '@/pages/Memos/New'
import MemoDetailPage     from '@/pages/Memos/Detail'
import CalendarPage       from '@/pages/Calendar'
import HotelCalendarPage  from '@/pages/HotelCalendar'
import MallCalendarPage   from '@/pages/MallCalendar'
import TutorialVideosPage from '@/pages/TutorialVideos'
// ── 飯店班表（飯店管理 → 飯店班表，2026-08-14 由頂層 /schedule 搬入）──────────
import ScheduleOverviewPage    from '@/pages/Schedule'
import ScheduleCalendarPage    from '@/pages/Schedule/Calendar'
import ScheduleImportPage      from '@/pages/Schedule/Import'
import ScheduleStaffPage       from '@/pages/Schedule/Staff'
import ScheduleShiftsPage      from '@/pages/Schedule/Shifts'
import ScheduleDepartmentsPage from '@/pages/Schedule/Departments'
import ScheduleManualPage      from '@/pages/Schedule/Manual'
// ── 商場班表（商場管理 → 商場班表，2026-08-14 新增）──────────────────────────
import MallScheduleOverviewPage    from '@/pages/MallSchedule'
import MallScheduleCalendarPage    from '@/pages/MallSchedule/Calendar'
import MallScheduleImportPage      from '@/pages/MallSchedule/Import'
import MallScheduleStaffPage       from '@/pages/MallSchedule/Staff'
import MallScheduleShiftsPage      from '@/pages/MallSchedule/Shifts'
import MallScheduleDepartmentsPage from '@/pages/MallSchedule/Departments'
import MallScheduleManualPage      from '@/pages/MallSchedule/Manual'
import MallFacilityInspectionDashboard from '@/pages/MallFacilityInspection'
import MallFacilityInspection4F        from '@/pages/MallFacilityInspection/4F'
import MallFacilityInspection3F        from '@/pages/MallFacilityInspection/3F'
import MallFacilityInspection1F3F      from '@/pages/MallFacilityInspection/1F3F'
import MallFacilityInspection1F        from '@/pages/MallFacilityInspection/1F'
import MallFacilityInspectionB1FB4F    from '@/pages/MallFacilityInspection/B1FB4F'
import FullBuildingInspectionDashboard from '@/pages/FullBuildingInspection'
import FullBuildingInspectionRF        from '@/pages/FullBuildingInspection/RF'
import FullBuildingInspectionB4F       from '@/pages/FullBuildingInspection/B4F'
import FullBuildingInspectionB2F       from '@/pages/FullBuildingInspection/B2F'
import FullBuildingInspectionB1F       from '@/pages/FullBuildingInspection/B1F'
import FullBuildingMaintenancePage       from '@/pages/FullBuildingMaintenance'
import FullBuildingMaintenanceDetailPage from '@/pages/FullBuildingMaintenance/Detail'
import LuqunRepairPage                 from '@/pages/LuqunRepair'
import DazhiRepairPage                 from '@/pages/DazhiRepair'
import WorkCategoryAnalysisPage        from '@/pages/WorkCategoryAnalysis'
import ExecDashboardPage               from '@/pages/ExecDashboard'
import DataPreparingPage              from '@/pages/DataPreparing'
import DecisionCockpitPage            from '@/pages/DecisionCockpit'
import ExecWorkDashboardPage           from '@/pages/ExecWorkDashboard'

// ── 核准請購單月報表 ────────────────────────────────────────────────────────────
import PurchaseReportPage              from '@/pages/PurchaseReport'

// ── 核准請款單月報表 ────────────────────────────────────────────────────────────
import ClaimReportPage                 from '@/pages/ClaimReport'

// ── 日曜核准請購單月報表 ─────────────────────────────────────────────────────────
import NichiyoPurchaseReportPage       from '@/pages/NichiyoPurchaseReport'

// ── 日曜核准請款單月報表 ─────────────────────────────────────────────────────────
import NichiyoClaimReportPage          from '@/pages/NichiyoClaimReport'

// ── 知識庫（LLM Wiki）──────────────────────────────────────────────────────────
import WikiPage                        from '@/pages/Wiki'

// ── AI 工單查詢助理 ────────────────────────────────────────────────────────────
import AIAssistantPage                 from '@/pages/AIAssistant'

// ── 飯店管理 Dashboard（跨模組總覽）───────────────────────────────────────────
import HotelMgmtDashboardPage          from '@/pages/HotelMgmtDashboard'

// ── 飯店每日巡檢 ───────────────────────────────────────────────────────────────
import HotelDailyInspectionDashboard   from '@/pages/HotelDailyInspection'

// ── 每日數值登錄表 ─────────────────────────────────────────────────────────────
import HotelMeterReadingsDashboard     from '@/pages/HotelMeterReadings'

// ── IHG 客房保養 ───────────────────────────────────────────────────────────────
import IHGRoomMaintenancePage          from '@/pages/IHGRoomMaintenance'

// ── 主管交辦／緊急事件 ─────────────────────────────────────────────────────────
import OtherTasksPage                  from '@/pages/OtherTasks'

// ── 飯店 Dashboard PPT 匯出設定 ────────────────────────────────────────────────
import HotelPptExportPage              from '@/pages/HotelPptExport'

// ── 預算管理 ──────────────────────────────────────────────────────────────────
import BudgetDashboardPage             from '@/pages/Budget'
import BudgetPlansPage                 from '@/pages/Budget/Plans'
import BudgetPlanDetailPage            from '@/pages/Budget/Plans/Detail'
import BudgetTransactionsPage          from '@/pages/Budget/Transactions'
import BudgetVsActualPage              from '@/pages/Budget/Reports/BudgetVsActual'
import BudgetDepartmentsPage           from '@/pages/Budget/Masters/Departments'
import BudgetAccountCodesPage          from '@/pages/Budget/Masters/AccountCodes'
import BudgetItemsPage                 from '@/pages/Budget/Masters/BudgetItems'
import BudgetMappingsPage              from '@/pages/Budget/Mappings'

// ── 週期採購（獨立資料庫 cycle-purchase.db，2026-07-10 新增）────────────────
import CpDashboardPage                 from '@/pages/CyclePurchase/Dashboard'
import CpItemsPage                     from '@/pages/CyclePurchase/Items'
import CpCyclesPage                    from '@/pages/CyclePurchase/Cycles'
import CpVendorsPage                   from '@/pages/CyclePurchase/Masters/Vendors'
import CpDepartmentsPage                from '@/pages/CyclePurchase/Masters/Departments'
import CpCostCentersPage               from '@/pages/CyclePurchase/Masters/CostCenters'
import CpAccountCodesPage              from '@/pages/CyclePurchase/Masters/AccountCodes'
import CpRequestsPage                   from '@/pages/CyclePurchase/Requests'
import CpRequestDetailPage              from '@/pages/CyclePurchase/Requests/Detail'
import CpSummaryPage                    from '@/pages/CyclePurchase/Summary'
import CpPOsPage                        from '@/pages/CyclePurchase/POs'
import CpPODetailPage                   from '@/pages/CyclePurchase/POs/Detail'
import CpReceivingListPage              from '@/pages/CyclePurchase/Receiving'
import CpReceivingDetailPage            from '@/pages/CyclePurchase/Receiving/Detail'
import CpReceivingReportPage            from '@/pages/CyclePurchase/Receiving/Report'
import CpPaymentListPage                from '@/pages/CyclePurchase/Payment'
import CpPaymentDetailPage              from '@/pages/CyclePurchase/Payment/Detail'
import CpAuditLogPage                   from '@/pages/CyclePurchase/AuditLog'
import CpManualPage                     from '@/pages/CyclePurchase/Manual'

// ── 合約管理 ──────────────────────────────────────────────────────────────────
import ContractPage            from '@/pages/Contract'
import ContractDashboardPage   from '@/pages/Contract/Dashboard'
import ContractImportPage      from '@/pages/Contract/Import'
import ContractExpiringPage    from '@/pages/Contract/Expiring'
import ContractClaimsPage      from '@/pages/Contract/Claims'
// 2026-07-21：「續約申請」獨立頁面已隱藏（見下方路由區塊註解），檔案保留未刪，故不 import。
import ContractCalendarPage    from '@/pages/Contract/CalendarView'
import ContractComparePage     from '@/pages/Contract/CompareContracts'
import VendorsPage             from '@/pages/Contract/Vendors'
import SettingsPage            from '@/pages/Contract/Settings'
import ContractManualPage      from '@/pages/Contract/Manual'
// ── 營運分析（OPERA，2026-08-04 新增）────────────────────────────────────────
import OperaDashboardPage      from '@/pages/Opera/Dashboard'
import OperaRevenuePage        from '@/pages/Opera/Revenue'
import OperaGuestPage          from '@/pages/Opera/Guest'
import OperaImportPage         from '@/pages/Opera/Import'
import OperaBatchesPage        from '@/pages/Opera/Batches'
import OperaSettingsPage       from '@/pages/Opera/Settings'
import OperaManualPage         from '@/pages/Opera/Manual'
// 房價預測（2026-08-05 新增）
import OperaLookupPage         from '@/pages/Opera/Lookup'
import OperaForecastPage       from '@/pages/Opera/Forecast'
// 市場區隔分析（2026-08-07）：⚠️ 資料來源是 OHIP API 落地，不是本模組其他頁的 TXT 上傳。
// 放在 /opera/* 是因為時間語意一致（都是落地的歷史資料），頁面上有標示來源。
import OperaSegmentsPage       from '@/pages/Opera/Segments'
// 訂房分析（2026-08-07）：⚠️ 母體與 /opera/guest 不同（所有訂房 vs 已離店住客）。
import OperaReservationsPage   from '@/pages/Opera/Reservations'
// 訂房 Pace／Pickup（2026-08-13）：⚠️ 讀同一批訂房資料，但多一個 as_of 觀察時點。
// 歷史進度是以訂房日「回推」得出（同步是整列覆寫、無版本），畫面上有標示。
import OperaPacePage           from '@/pages/Opera/Pace'
// ── 即時營運（2026-08-06）：資料直接來自 OPERA Cloud（OHIP）REST API，
//    與 /opera/*（人工上傳 TXT）完全獨立。規格書 docs/SPEC_realtime_operations.md
import RealtimeDashboardPage   from '@/pages/Realtime/Dashboard'
import RealtimeRevenuePage     from '@/pages/Realtime/Revenue'
import RealtimeComparePage     from '@/pages/Realtime/Compare'
import RealtimeLogsPage        from '@/pages/Realtime/Logs'
import RealtimeManualPage     from '@/pages/Realtime/Manual'
// 註：OperaEventsPage 已併入 Forecast 頁的 TAB，此處不再直接引用

// ── 金旭分析（2026-08-05）：與 /opera/* 完全獨立的第二個檔案上傳型模組 ──────
import JinxuDashboardPage      from '@/pages/JinXu/Dashboard'
import JinxuReservationPage    from '@/pages/JinXu/Reservation'
import JinxuRevenuePage        from '@/pages/JinXu/Revenue'
import JinxuPaymentPage        from '@/pages/JinXu/Payment'
import JinxuDepositPage        from '@/pages/JinXu/Deposit'
import JinxuImportPage         from '@/pages/JinXu/Import'
import JinxuSettingsPage       from '@/pages/JinXu/Settings'
import JinxuManualPage         from '@/pages/JinXu/Manual'

// ── 首頁重定向（讀取 menu-config 設定，fallback 到第一個有權限的 menu 項目）──────
// 首頁設定的儲存與選單走訪工具已移至 @/utils/homePage（2026-08-11）
// 這裡 re-export 舊常數名稱，維持既有 import 相容
export { HOME_PAGE_STORAGE_KEY } from '@/utils/homePage'

/**
 * 依 permission_key 優先序對應第一個可進入的路由。
 * 純資料，不含任何 JSX，可安全在 module 層級使用。
 */
const PERM_DEFAULT_ROUTES: { key: string; route: string }[] = [
  { key: 'decision_cockpit_view',             route: '/decision-cockpit' },
  { key: 'hotel_view',                        route: '/hotel/overview' },
  { key: 'mall_view',                         route: '/mall/overview' },
  { key: 'purchase_report_view',              route: '/purchase-report/monthly' },
  { key: 'claim_report_view',                 route: '/claim-report/monthly' },
  { key: 'nichiyo_purchase.view',             route: '/nichiyo-purchase-report/monthly' },
  { key: 'nichiyo_claim.view',                route: '/nichiyo-claim-report/monthly' },
  { key: 'contract_view',                     route: '/contract' },
  { key: 'contract_expiring_view',            route: '/contract/expiring' },
  { key: 'contract_claims_view',              route: '/contract/claims' },
  { key: 'budget_view',                       route: '/budget/dashboard' },
  { key: 'cycle_purchase_view',                route: '/cycle-purchase/dashboard' },
  { key: 'calendar_view',                     route: '/calendar' },
  { key: 'luqun_repair_view',                 route: '/luqun-repair/dashboard' },
  { key: 'dazhi_repair_view',                 route: '/dazhi-repair/dashboard' },
  { key: 'security_view',                     route: '/security/dashboard' },
  { key: 'approvals_view',                    route: '/approvals/list' },
  { key: 'memos_view',                        route: '/memos/list' },
  { key: 'exec_dashboard_view',               route: '/exec-dashboard' },
  { key: 'work_category_analysis_view',       route: '/work-category-analysis' },
  { key: 'tutorial_videos_view',              route: '/tutorial-videos' },
]

/**
 * 首頁判定（2026-08-11 改版）
 *
 * 舊行為：拿到 localStorage 的首頁設定就無條件導向，不檢查權限；且設定為
 * 全瀏覽器共用，換帳號會沿用別人的首頁 → 角色不同時會被送到無權限的頁面。
 *
 * 新行為：
 *   1. 首頁設定改為每帳號獨立（@/utils/homePage）
 *   2. 以 MainLayout 算好的「套用 menu-config + 權限過濾後」選單驗證設定值，
 *      該路由不在選單中即視為無效
 *   3. 無效或未設定 → 取選單最上面第一個可進入的頁面（群組取第一個子頁、
 *      排除系統設定群組），例如只有 OPERA 權限的帳號會進 /opera/dashboard
 *   4. 選單完全算不出來（menu-config API 失敗且無快取）→ 才退回 PERM_DEFAULT_ROUTES
 */
function HomeRedirect() {
  const user = useAuthStore((s) => s.user)
  const isSystemAdmin = !!(user?.roles?.includes('system_admin'))
  const { items: visibleMenu, loading: menuLoading } = useMenuItemsContext()

  // permissions 尚未從 /me 載入時等待（避免用空權限計算首頁）
  if (!isSystemAdmin && user?.permissions === undefined) {
    return null   // 等待 /me 回應，MainLayout 的 Skeleton 佔位
  }

  // 選單尚未算完時等待，否則會拿空選單誤判成「設定無效」
  if (menuLoading) {
    return null
  }

  const stored = getHomePageRoute(user?.id)

  // 設定值有效 = 該路由出現在使用者實際看得到的選單中
  if (stored && isRouteInMenu(visibleMenu, stored)) {
    return <Navigate to={stored} replace />
  }

  // 無效或未設定 → 選單最上面第一個可進入的頁面
  const firstRoute = firstRouteInMenu(visibleMenu)
  if (firstRoute) {
    return <Navigate to={firstRoute} replace />
  }

  // 選單為空（API 失敗且無快取）：依優先序選第一個有權限的 route
  const perms = user?.permissions ?? []
  const hasWildcard = perms.includes('*')
  const validRoutes = PERM_DEFAULT_ROUTES
    .filter(({ key }) => hasWildcard || perms.includes(key))
    .map(({ route }) => route)

  // 若真的什麼都沒有，進 /dashboard（no-permission screen 會顯示）
  return <Navigate to={validRoutes[0] ?? '/dashboard'} replace />
}

// ── Route Guards ──────────────────────────────────────────────────────────────
/**
 * 系統設定守衛 — 整個 settings group 的第一道防線。
 *
 * 2026-08-12 權限收斂改版：原本只認 system_admin 角色，導致「幫忙建帳號／派角色」
 * 只能靠 system_admin，連帶把 Opera／金旭／即時營運的營收資料一併送出去。
 * 改為「具備任一 settings_* 權限即可進入」，各頁再由自己的 PermissionGuard 細分。
 *
 * ⚠️ 必須等 /me 回傳 permissions 才能判斷，否則具備 settings_* 權限的使用者
 *    會在權限載入前被誤導回 /dashboard（system_admin 的 roles 在 JWT 裡，不必等）。
 */
const SETTINGS_PERMISSION_KEYS = [
  'settings_users_manage',
  'settings_roles_manage',
  'settings_menu_manage',
  'settings_ragic_manage',
]

function SettingsGuard({ children }: { children: React.ReactNode }) {
  const user          = useAuthStore((s) => s.user)
  const hasPermission = useAuthStore((s) => s.hasPermission)
  const isSystemAdmin = !!(user?.roles?.includes('system_admin'))

  if (!isSystemAdmin && user?.permissions === undefined) {
    return null   // 等 /me 回應，MainLayout 的 Skeleton 佔位
  }

  const canEnter = isSystemAdmin || SETTINGS_PERMISSION_KEYS.some((k) => hasPermission(k))
  return canEnter ? <>{children}</> : <Navigate to="/dashboard" replace />
}

/**
 * 細粒度權限守衛 — 檢查使用者是否具備指定的 permission_key。
 * - system_admin（permissions=["*"]）永遠通過
 * - permissions 尚未從 /me 載入時，以 roles 判斷 system_admin
 * - 無權限：顯示 403 提示頁，不跳轉（讓使用者知道頁面存在但無權限）
 *
 * 使用方式：
 *   <Route path="users" element={
 *     <PermissionGuard permissionKey="settings_users_manage">
 *       <UsersPage />
 *     </PermissionGuard>
 *   } />
 */
function PermissionGuard({
  permissionKey,
  children,
}: {
  permissionKey: string
  children: React.ReactNode
}) {
  const user          = useAuthStore((s) => s.user)
  const hasPermission = useAuthStore((s) => s.hasPermission)

  // permissions 尚未從 /me 載入（undefined）時先等待，避免誤顯示 403
  // system_admin 永遠不需等（roles 已在 JWT 裡）
  const isSystemAdmin = !!(user?.roles?.includes('system_admin'))
  if (!isSystemAdmin && user?.permissions === undefined) {
    return null  // MainLayout 的 Skeleton 佔位，等 /me 回應後再判斷
  }

  if (!hasPermission(permissionKey)) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '60vh',
          gap: 12,
        }}
      >
        <div style={{ fontSize: 48 }}>🔒</div>
        <div style={{ fontSize: 18, fontWeight: 600, color: '#1B3A5C' }}>存取被拒絕</div>
        <div style={{ color: '#64748b', fontSize: 14 }}>
          您沒有存取此頁面的權限（{permissionKey}）
        </div>
        <div style={{ color: '#94a3b8', fontSize: 12 }}>
          請聯絡系統管理員調整角色權限
        </div>
      </div>
    )
  }
  return <>{children}</>
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const token           = useAuthStore((s) => s.token)
  const logout          = useAuthStore((s) => s.logout)
  const navigate        = useNavigate()

  useEffect(() => {
    const checkExpiry = () => {
      if (isJwtExpired(token)) {
        logout()
        navigate('/login', { replace: true })
      }
    }

    checkExpiry()                                     // 掛載時立即檢查
    const timer = setInterval(checkExpiry, 60_000)   // 每 60 秒再檢查一次

    // 切換回分頁時重新確認（使用者放置很久再回來）
    const onVisible = () => {
      if (document.visibilityState === 'visible') checkExpiry()
    }
    document.addEventListener('visibilitychange', onVisible)

    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [token, logout, navigate])

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

// ── Router ────────────────────────────────────────────────────────────────────
export default function AppRouter() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected — all inside MainLayout */}
      <Route
        path="/"
        element={
          <PrivateRoute>
            <MainLayout />
          </PrivateRoute>
        }
      >
        <Route index element={<HomeRedirect />} />
        <Route path="dashboard" element={<DashboardPage />} />

        {/* ── ◆ 決策駕駛艙（高階主管決策入口，整合三大模組精華）────────── */}
        <Route path="decision-cockpit" element={
          <PermissionGuard permissionKey="decision_cockpit_view">
            <DecisionCockpitPage />
          </PermissionGuard>
        } />

        {/* ── 知識庫（LLM Wiki）─────────────────────────────────── */}
        <Route path="wiki" element={
          <PermissionGuard permissionKey="wiki_view">
            <WikiPage />
          </PermissionGuard>
        } />

        {/* ── AI 工單查詢助理 ───────────────────────────────────────── */}
        <Route path="ai-assistant" element={<AIAssistantPage />} />

        {/* ── 行事曆 ────────────────────────────────────────────────── */}
        <Route path="calendar" element={<CalendarPage />} />

        {/* ── 影音教學（本地模組，不對接 Ragic）────────────────────────── */}
        <Route path="tutorial-videos" element={
          <PermissionGuard permissionKey="tutorial_videos_view">
            <TutorialVideosPage />
          </PermissionGuard>
        } />

        {/* ── 舊路由相容（2026-08-14 班表拆分前的 /schedule/*）──────────
            班表已搬到 /hotel/schedule 與 /mall/schedule，舊書籤一律導到飯店班表。
            確認沒有人再用舊網址之後，這段可以移除。 */}
        <Route path="schedule/*" element={<Navigate to="/hotel/schedule" replace />} />

        {/* ── 飯店 Dashboard PPT 匯出設定（一階，全公司共用）────────── */}
        <Route path="ppt-export" element={
          <PermissionGuard permissionKey="hotel_overview_ppt_config">
            <HotelPptExportPage />
          </PermissionGuard>
        } />

        {/* ── 飯店管理 ──────────────────────────────────────────────── */}
        <Route path="hotel">
          <Route path="overview"                element={<HotelMgmtDashboardPage />} />
          <Route path="room-maintenance"        element={<RoomMaintenancePage />} />
          <Route path="room-maintenance-detail" element={<RoomMaintenanceDetailPage />} />
          <Route path="periodic-maintenance"             element={<PeriodicMaintenancePage />} />
          <Route path="periodic-maintenance/:batchId"    element={<PeriodicMaintenanceDetailPage />} />
          {/* 2026-07-14：hotel_routine_pm 安全下線，路由停用（頁面檔案未刪，可復原） */}
          {/* <Route path="routine-maintenance"              element={<HotelRoutineMaintenancePage />} /> */}
          <Route path="ihg-room-maintenance"    element={<IHGRoomMaintenancePage />} />
          <Route path="daily-inspection"        element={<HotelDailyInspectionDashboard />} />
          <Route path="daily-meter-readings"    element={<HotelMeterReadingsDashboard />} />
          <Route path="other-tasks"             element={<OtherTasksPage />} />
          <Route path="calendar"               element={<HotelCalendarPage />} />
          {/* ── 飯店班表（本地 SQLite 模組，不對接 Ragic）─────────────── */}
          <Route path="schedule">
            <Route index element={<ScheduleOverviewPage />} />
            <Route path="calendar"    element={<ScheduleCalendarPage />} />
            <Route path="import"      element={<ScheduleImportPage />} />
            <Route path="staff"       element={<ScheduleStaffPage />} />
            <Route path="shifts"      element={<ScheduleShiftsPage />} />
            <Route path="departments" element={<ScheduleDepartmentsPage />} />
            <Route path="manual"      element={<ScheduleManualPage />} />
          </Route>
        </Route>

        {/* ── 商場管理 ──────────────────────────────────────────────── */}
        <Route path="mall">
          <Route path="overview"                      element={<MallMgmtDashboardPage />} />
          <Route path="dashboard"                     element={<MallDashboardPage />} />
          <Route path="periodic-maintenance"                    element={<MallPeriodicMaintenancePage />} />
          <Route path="periodic-maintenance/:batchId"          element={<MallPeriodicMaintenanceDetailPage />} />
          <Route path="full-building-maintenance"              element={<FullBuildingMaintenancePage />} />
          <Route path="full-building-maintenance/:batchId"     element={<FullBuildingMaintenanceDetailPage />} />
          <Route path="b4f-inspection"                element={<B4FInspectionPage />} />
          <Route path="b4f-inspection/:batchId"       element={<B4FInspectionDetailPage />} />
          <Route path="rf-inspection"                 element={<RFInspectionPage />} />
          <Route path="rf-inspection/:batchId"        element={<RFInspectionDetailPage />} />
          <Route path="b2f-inspection"                element={<B2FInspectionPage />} />
          <Route path="b2f-inspection/:batchId"       element={<B2FInspectionDetailPage />} />
          <Route path="b1f-inspection"                element={<B1FInspectionPage />} />
          <Route path="b1f-inspection/:batchId"       element={<B1FInspectionDetailPage />} />
          {/* 主管交辦／緊急事件共用同一元件（飯店/商場雙入口） */}
          <Route path="other-tasks"             element={<OtherTasksPage />} />
          <Route path="calendar"               element={<MallCalendarPage />} />
          {/* ── 商場班表（本地 SQLite 模組，不對接 Ragic）─────────────── */}
          <Route path="schedule">
            <Route index element={<MallScheduleOverviewPage />} />
            <Route path="calendar"    element={<MallScheduleCalendarPage />} />
            <Route path="import"      element={<MallScheduleImportPage />} />
            <Route path="staff"       element={<MallScheduleStaffPage />} />
            <Route path="shifts"      element={<MallScheduleShiftsPage />} />
            <Route path="departments" element={<MallScheduleDepartmentsPage />} />
            <Route path="manual"      element={<MallScheduleManualPage />} />
          </Route>
        </Route>

        {/* ── 核准請購單月報表 ──────────────────────────────────────────── */}
        <Route path="purchase-report">
          <Route
            path="monthly"
            element={
              <PermissionGuard permissionKey="purchase_report_view">
                <PurchaseReportPage />
              </PermissionGuard>
            }
          />
          <Route index element={<Navigate to="monthly" replace />} />
        </Route>

        {/* ── 核准請款單月報表 ──────────────────────────────────────────── */}
        <Route path="claim-report">
          <Route
            path="monthly"
            element={
              <PermissionGuard permissionKey="claim_report_view">
                <ClaimReportPage />
              </PermissionGuard>
            }
          />
          <Route index element={<Navigate to="monthly" replace />} />
        </Route>

        {/* ── 日曜核准請購單月報表 ──────────────────────────────────────── */}
        <Route path="nichiyo-purchase-report">
          <Route
            path="monthly"
            element={
              <PermissionGuard permissionKey="nichiyo_purchase.view">
                <NichiyoPurchaseReportPage />
              </PermissionGuard>
            }
          />
          <Route index element={<Navigate to="monthly" replace />} />
        </Route>

        {/* ── 日曜核准請款單月報表 ──────────────────────────────────────── */}
        <Route path="nichiyo-claim-report">
          <Route
            path="monthly"
            element={
              <PermissionGuard permissionKey="nichiyo_claim.view">
                <NichiyoClaimReportPage />
              </PermissionGuard>
            }
          />
          <Route index element={<Navigate to="monthly" replace />} />
        </Route>

        {/* ── 預算管理 ──────────────────────────────────────────────────── */}
        <Route path="budget">
          <Route path="dashboard"                element={<BudgetDashboardPage />} />
          <Route path="plans"                    element={<BudgetPlansPage />} />
          <Route path="plans/:planId"            element={<BudgetPlanDetailPage />} />
          <Route path="transactions"             element={<BudgetTransactionsPage />} />
          <Route path="reports/budget-vs-actual" element={<BudgetVsActualPage />} />
          <Route path="masters/departments"      element={<BudgetDepartmentsPage />} />
          <Route path="masters/account-codes"    element={<BudgetAccountCodesPage />} />
          <Route path="masters/budget-items"     element={<BudgetItemsPage />} />
          <Route path="mappings"                 element={<BudgetMappingsPage />} />
        </Route>

        {/* ── 週期採購（獨立資料庫，2026-07-11 拿掉批次，改用 cycle+period_label）── */}
        <Route path="cycle-purchase">
          <Route path="dashboard"                element={<CpDashboardPage />} />
          <Route path="items"                    element={<CpItemsPage />} />
          <Route path="cycles"                   element={<CpCyclesPage />} />
          <Route path="masters/vendors"          element={<CpVendorsPage />} />
          <Route path="masters/departments"      element={<CpDepartmentsPage />} />
          <Route path="masters/cost-centers"     element={<CpCostCentersPage />} />
          <Route path="masters/account-codes"    element={<CpAccountCodesPage />} />
          <Route path="requests"                 element={<CpRequestsPage />} />
          <Route path="requests/:id"             element={<CpRequestDetailPage />} />
          <Route path="summary"                  element={<CpSummaryPage />} />
          <Route path="pos"                      element={<CpPOsPage />} />
          <Route path="pos/:id"                  element={<CpPODetailPage />} />
          <Route path="receiving"                 element={<CpReceivingListPage />} />
          <Route path="receiving/:id"              element={<CpReceivingDetailPage />} />
          <Route path="receiving-report"           element={<CpReceivingReportPage />} />
          <Route path="payments"                      element={<CpPaymentListPage />} />
          <Route path="payments/:id"                  element={<CpPaymentDetailPage />} />
          <Route path="audit-log"                     element={<CpAuditLogPage />} />
          {/* 使用手冊為靜態內容，開放給所有週採使用者（選單用 permissionKeys OR
              涵蓋全部 8 個週採權限）；與本區塊其他路由一致不加 PermissionGuard。 */}
          <Route path="manual"                        element={<CpManualPage />} />
        </Route>

        {/* ── 合約管理 ──────────────────────────────────────────────────── */}
        <Route path="contract" element={
          <PermissionGuard permissionKey="contract_view">
            <Outlet />
          </PermissionGuard>
        }>
          <Route index element={<ContractPage />} />
          <Route path="dashboard" element={<ContractDashboardPage />} />
          <Route path="expiring" element={
            <PermissionGuard permissionKey="contract_expiring_view">
              <ContractExpiringPage />
            </PermissionGuard>
          } />
          <Route path="claims" element={
            <PermissionGuard permissionKey="contract_claims_view">
              <ContractClaimsPage />
            </PermissionGuard>
          } />
          {/* 2026-07-21：「續約申請」路由已隱藏（改為「原合約複製續約」，見合約明細
              Drawer 的「上下層級」TAB）。ContractRenewalsPage 與後端端點保留未刪。 */}
          <Route path="calendar" element={
            <PermissionGuard permissionKey="contract_view">
              <ContractCalendarPage />
            </PermissionGuard>
          } />
          <Route path="compare" element={
            <PermissionGuard permissionKey="contract_view">
              <ContractComparePage />
            </PermissionGuard>
          } />
          <Route path="import" element={
            <PermissionGuard permissionKey="contract_create_edit">
              <ContractImportPage />
            </PermissionGuard>
          } />
          <Route path="vendors" element={<VendorsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="manual" element={<ContractManualPage />} />
        </Route>

        {/* ── 商場工務報修 ──────────────────────────────────────────────── */}
        <Route path="luqun-repair">
          <Route path="dashboard" element={<LuqunRepairPage />} />
          <Route index            element={<LuqunRepairPage />} />
        </Route>

        {/* ── 大直工務部 ────────────────────────────────────────────────── */}
        <Route path="dazhi-repair">
          <Route path="dashboard" element={<DazhiRepairPage />} />
          <Route index            element={<DazhiRepairPage />} />
        </Route>

        {/* ── ★工項類別分析（商場+大直共用）────────────────────────────── */}
        <Route path="work-category-analysis" element={<WorkCategoryAnalysisPage />} />

        {/* ── ◆ 董事長簡報 Dashboard（新功能，獨立路由）─────────────────── */}
        <Route path="exec-dashboard" element={<ExecDashboardPage />} />

        {/* ── 集團工務決策駕駛艙（工務決策視角，獨立路由）─────────────────── */}
        <Route path="exec-work-dashboard" element={
          <PermissionGuard permissionKey="exec_work_dashboard_view">
            <ExecWorkDashboardPage />
          </PermissionGuard>
        } />

        {/* ── 春大直商場工務巡檢 ────────────────────────────────────── */}
        <Route path="mall-facility-inspection">
          <Route path="dashboard"  element={<MallFacilityInspectionDashboard />} />
          <Route path="4f"         element={<MallFacilityInspection4F />} />
          <Route path="3f"         element={<MallFacilityInspection3F />} />
          <Route path="1f-3f"      element={<MallFacilityInspection1F3F />} />
          <Route path="1f"         element={<MallFacilityInspection1F />} />
          <Route path="b1f-b4f"    element={<MallFacilityInspectionB1FB4F />} />
        </Route>

        {/* ── 整棟巡檢 ──────────────────────────────────────────────── */}
        <Route path="full-building-inspection">
          <Route path="dashboard"  element={<FullBuildingInspectionDashboard />} />
          <Route path="rf"         element={<FullBuildingInspectionRF />} />
          <Route path="b4f"        element={<FullBuildingInspectionB4F />} />
          <Route path="b2f"        element={<FullBuildingInspectionB2F />} />
          <Route path="b1f"        element={<FullBuildingInspectionB1F />} />
        </Route>

        {/* ── 保全管理 ──────────────────────────────────────────────── */}
        <Route path="security">
          <Route path="dashboard"                      element={<SecurityDashboardPage />} />
          <Route path="patrol/:sheetKey"               element={<SecurityPatrolPage />} />
          <Route path="patrol/:sheetKey/:batchId"      element={<SecurityPatrolDetailPage />} />
        </Route>

        {/* ── 倉庫管理 ──────────────────────────────────────────────── */}
        <Route path="warehouse">
          <Route path="inventory" element={<InventoryPage />} />
        </Route>

        {/* ── 簽核管理 ──────────────────────────────────────────────── */}
        <Route path="approvals">
          <Route path="list"  element={<ApprovalListPage />} />
          <Route path="new"   element={<ApprovalNewPage />} />
          <Route path=":id"   element={<ApprovalDetailPage />} />
        </Route>

        {/* ── 公告牆 ────────────────────────────────────────────────── */}
        <Route path="memos">
          <Route path="list" element={<MemoListPage />} />
          <Route path="new"  element={<MemoNewPage />} />
          <Route path=":id"  element={<MemoDetailPage />} />
        </Route>

        {/* ── 營運分析（OPERA，資料來源為人工上傳的 OPERA TXT）────────────── */}
        <Route path="opera">
          <Route path="dashboard" element={
            <PermissionGuard permissionKey="opera_view">
              <OperaDashboardPage />
            </PermissionGuard>
          } />
          <Route path="revenue" element={
            <PermissionGuard permissionKey="opera_revenue_view">
              <OperaRevenuePage />
            </PermissionGuard>
          } />
          <Route path="guest" element={
            <PermissionGuard permissionKey="opera_guest_view">
              <OperaGuestPage />
            </PermissionGuard>
          } />
          <Route path="import" element={
            <PermissionGuard permissionKey="opera_import">
              <OperaImportPage />
            </PermissionGuard>
          } />
          {/* 2026-08-04：「匯入紀錄」併入「資料匯入」頁的 TAB。
              依 CLAUDE.md §5「不可移除現有路由」，此路由保留並導向新位置，
              舊書籤與外部連結不會壞掉。權限由目標頁的 PermissionGuard 負責。 */}
          <Route path="batches" element={<Navigate to="/opera/import?tab=batches" replace />} />
          {/* ── 房價預測（2026-08-05）──────────────────────────────────
              「歷史同期查詢」共用 opera_view：純唯讀歷史事實，與 Dashboard 同性質。
              「事件月曆」另開 opera_event_admin：權限清單是管理員唯一看得到自己在
              授權什麼的地方，掛在「分析門檻設定」底下會授權到名不符實的頁面。 */}
          <Route path="lookup" element={
            <PermissionGuard permissionKey="opera_view">
              <OperaLookupPage />
            </PermissionGuard>
          } />
          {/* 市場區隔分析（2026-08-07）：另開 opera_segment_view，不共用
              opera_revenue_view —— 兩者資料來源不同（API 落地 vs TXT 上傳）、
              口徑尚未完全對齊，共用權限會讓管理員以為授權的是同一份資料。 */}
          <Route path="segments" element={
            <PermissionGuard permissionKey="opera_segment_view">
              <OperaSegmentsPage />
            </PermissionGuard>
          } />
          {/* 訂房分析（2026-08-07）：另開 opera_reservation_view，不共用
              opera_guest_view —— 兩者**分析母體不同**（所有訂房 vs 已離店住客），
              共用權限會讓管理員以為授權的是同一份資料。 */}
          <Route path="reservations" element={
            <PermissionGuard permissionKey="opera_reservation_view">
              <OperaReservationsPage />
            </PermissionGuard>
          } />
          {/* 訂房 Pace／Pickup（2026-08-13）：另開 opera_pace_view，不共用
              opera_reservation_view —— 這一頁的數字是**回推**出來的（訂房同步
              整列覆寫、無版本），已含後續改期與取消，與那邊的「現在狀態」
              不是同一種可信度。 */}
          <Route path="pace" element={
            <PermissionGuard permissionKey="opera_pace_view">
              <OperaPacePage />
            </PermissionGuard>
          } />
          <Route path="forecast" element={
            <PermissionGuard permissionKey="opera_forecast_view">
              <OperaForecastPage />
            </PermissionGuard>
          } />
          {/* 2026-08-05：「事件月曆」併入「房價預測」頁的 TAB。
              依 CLAUDE.md §5「不可移除現有路由」，此路由保留並導向新位置，
              舊書籤與外部連結不會壞掉。權限由目標頁的 PermissionGuard 負責，
              頁內的新增／修改／刪除按鈕另由 opera_event_admin 控管。 */}
          <Route path="events" element={<Navigate to="/opera/forecast?tab=events" replace />} />
          <Route path="settings" element={
            <PermissionGuard permissionKey="opera_admin">
              <OperaSettingsPage />
            </PermissionGuard>
          } />
          <Route path="manual" element={
            <PermissionGuard permissionKey="opera_view">
              <OperaManualPage />
            </PermissionGuard>
          } />
        </Route>

        {/* ── 即時營運（2026-08-06）──────────────────────────────────────
            資料**直接來自 OPERA Cloud（OHIP）REST API**，不是上傳的 TXT。
            刻意與 /opera/* 分成兩個一級選單：兩者資料時點不同（API 即時 vs
            上傳落後數天），放同一群組會讓使用者以為是同一份資料。
            ⚠️ 每次查詢都會實際呼叫 OHIP（按量計費），權限預設不給任何既有角色。
            規格書：docs/SPEC_realtime_operations.md */}
        <Route path="realtime">
          <Route path="dashboard" element={
            <PermissionGuard permissionKey="realtime_view">
              <RealtimeDashboardPage />
            </PermissionGuard>
          } />
          {/* 營收走非同步 API（POST 啟動→輪詢→GET），單段約 3 秒且會切段，
              用量與延遲都比即時房況高，因此另開權限 */}
          <Route path="revenue" element={
            <PermissionGuard permissionKey="realtime_revenue">
              <RealtimeRevenuePage />
            </PermissionGuard>
          } />
          {/* 比對不走快取，每次實際呼叫兩支 API，因此權限與看板分開 */}
          <Route path="compare" element={
            <PermissionGuard permissionKey="realtime_compare">
              <RealtimeComparePage />
            </PermissionGuard>
          } />
          {/* 呼叫紀錄只讀本地 ohip_call_log，不呼叫 API，共用 realtime_view */}
          <Route path="logs" element={
            <PermissionGuard permissionKey="realtime_view">
              <RealtimeLogsPage />
            </PermissionGuard>
          } />
          {/* 使用手冊為靜態內容，共用 realtime_view */}
          <Route path="manual" element={
            <PermissionGuard permissionKey="realtime_view">
              <RealtimeManualPage />
            </PermissionGuard>
          } />
        </Route>

        {/* 2026-08-06：「OPERA API 串接」更名為「即時營運」，路由前綴 /opera-api → /realtime。
            依 CLAUDE.md §5「不可移除現有路由」，舊路由保留並導向新位置，舊書籤不會壞。
            權限由目標頁的 PermissionGuard 負責。 */}
        <Route path="opera-api">
          <Route path="live"    element={<Navigate to="/realtime/dashboard" replace />} />
          <Route path="revenue" element={<Navigate to="/realtime/revenue" replace />} />
          <Route path="compare" element={<Navigate to="/realtime/compare" replace />} />
        </Route>

        {/* ── 金旭分析（資料來源為人工上傳的金旭 xlsx）─────────────────────
            路由前綴 /jinxu/*，與 /opera/* 完全獨立，不共用端點或資料表。
            「取消與訂價落差分析」為 /jinxu/reservation 頁的 TAB，權限
            jinxu_cancel_view 在頁面內以 TAB 層級控管，不另立路由。 */}
        <Route path="jinxu">
          <Route path="dashboard" element={
            <PermissionGuard permissionKey="jinxu_view">
              <JinxuDashboardPage />
            </PermissionGuard>
          } />
          <Route path="reservation" element={
            <PermissionGuard permissionKey="jinxu_resv_view">
              <JinxuReservationPage />
            </PermissionGuard>
          } />
          <Route path="revenue" element={
            <PermissionGuard permissionKey="jinxu_revenue_view">
              <JinxuRevenuePage />
            </PermissionGuard>
          } />
          <Route path="payment" element={
            <PermissionGuard permissionKey="jinxu_payment_view">
              <JinxuPaymentPage />
            </PermissionGuard>
          } />
          <Route path="deposit" element={
            <PermissionGuard permissionKey="jinxu_deposit_view">
              <JinxuDepositPage />
            </PermissionGuard>
          } />
          <Route path="import" element={
            <PermissionGuard permissionKey="jinxu_import">
              <JinxuImportPage />
            </PermissionGuard>
          } />
          <Route path="settings" element={
            <PermissionGuard permissionKey="jinxu_admin">
              <JinxuSettingsPage />
            </PermissionGuard>
          } />
          {/* 使用手冊共用 jinxu_view：純唯讀說明頁，與 Dashboard 同性質 */}
          <Route path="manual" element={
            <PermissionGuard permissionKey="jinxu_view">
              <JinxuManualPage />
            </PermissionGuard>
          } />
        </Route>

        {/* ── 系統設定（僅限 system_admin + 各頁細粒度 permission）────────── */}
        <Route
          path="settings"
          element={<SettingsGuard><Outlet /></SettingsGuard>}
        >
          <Route path="basic" element={
            <PermissionGuard permissionKey="system_admin_only">
              <BasicSettingsPage />
            </PermissionGuard>
          } />
          <Route path="users" element={
            <PermissionGuard permissionKey="settings_users_manage">
              <UsersPage />
            </PermissionGuard>
          } />
          <Route path="roles" element={
            <PermissionGuard permissionKey="settings_roles_manage">
              <RolesPage />
            </PermissionGuard>
          } />
          <Route path="ragic-connections" element={
            <PermissionGuard permissionKey="settings_ragic_manage">
              <RagicConnectionsPage />
            </PermissionGuard>
          } />
          <Route path="ragic-app-directory" element={
            <PermissionGuard permissionKey="settings_ragic_manage">
              <RagicAppDirectoryPage />
            </PermissionGuard>
          } />
          <Route path="menu-config" element={
            <PermissionGuard permissionKey="settings_menu_manage">
              <MenuConfigPage />
            </PermissionGuard>
          } />
          <Route path="static-pages" element={
            <PermissionGuard permissionKey="settings_menu_manage">
              <StaticPagesPage />
            </PermissionGuard>
          } />
          <Route path="employee-manual-export" element={
            <EmployeeManualExportPage />
          } />
          <Route path="ragic-field-audit" element={
            <PermissionGuard permissionKey="ragic_field_audit_view">
              <RagicFieldAuditPage />
            </PermissionGuard>
          } />
          <Route path="repair-unfinished-report" element={
            <PermissionGuard permissionKey="repair_unfinished_report_view">
              <RepairUnfinishedReportPage />
            </PermissionGuard>
          } />
          <Route path="knowledge-graph" element={
            <PermissionGuard permissionKey="system_admin_only">
              <KnowledgeGraphPage />
            </PermissionGuard>
          } />
          <Route path="usage-monitor" element={
            <PermissionGuard permissionKey="system_admin_only">
              <UsageMonitorPage />
            </PermissionGuard>
          } />
        </Route>

        {/* 自訂選單佔位頁（custom_* key 點擊時導向此處）*/}
        <Route path="data-preparing" element={<DataPreparingPage />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
