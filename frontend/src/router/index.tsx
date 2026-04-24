/**
 * App Router
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

import MainLayout          from '@/components/Layout/MainLayout'
import LoginPage           from '@/pages/Login'
import DashboardPage       from '@/pages/Dashboard'
import RoomMaintenancePage       from '@/pages/RoomMaintenance'
import RoomMaintenanceDetailPage from '@/pages/RoomMaintenanceDetail'
import InventoryPage             from '@/pages/Inventory'
import PeriodicMaintenancePage       from '@/pages/PeriodicMaintenance'
import PeriodicMaintenanceDetailPage from '@/pages/PeriodicMaintenance/Detail'
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
import ApprovalListPage   from '@/pages/Approvals/List'
import ApprovalNewPage    from '@/pages/Approvals/New'
import ApprovalDetailPage from '@/pages/Approvals/Detail'
import MemoListPage       from '@/pages/Memos/List'
import MemoNewPage        from '@/pages/Memos/New'
import MemoDetailPage     from '@/pages/Memos/Detail'
import CalendarPage       from '@/pages/Calendar'
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
import LuqunRepairPage                 from '@/pages/LuqunRepair'
import DazhiRepairPage                 from '@/pages/DazhiRepair'
import WorkCategoryAnalysisPage        from '@/pages/WorkCategoryAnalysis'
import ExecDashboardPage               from '@/pages/ExecDashboard'

// ── IHG 客房保養 ───────────────────────────────────────────────────────────────
import IHGRoomMaintenancePage          from '@/pages/IHGRoomMaintenance'

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

// ── Route Guard ───────────────────────────────────────────────────────────────
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
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
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />

        {/* ── 行事曆 ────────────────────────────────────────────────── */}
        <Route path="calendar" element={<CalendarPage />} />

        {/* ── 飯店管理 ──────────────────────────────────────────────── */}
        <Route path="hotel">
          <Route path="room-maintenance"        element={<RoomMaintenancePage />} />
          <Route path="room-maintenance-detail" element={<RoomMaintenanceDetailPage />} />
          <Route path="periodic-maintenance"             element={<PeriodicMaintenancePage />} />
          <Route path="periodic-maintenance/:batchId"    element={<PeriodicMaintenanceDetailPage />} />
          <Route path="ihg-room-maintenance"    element={<IHGRoomMaintenancePage />} />
        </Route>

        {/* ── 商場管理 ──────────────────────────────────────────────── */}
        <Route path="mall">
          <Route path="dashboard"                     element={<MallDashboardPage />} />
          <Route path="periodic-maintenance"          element={<MallPeriodicMaintenancePage />} />
          <Route path="periodic-maintenance/:batchId" element={<MallPeriodicMaintenanceDetailPage />} />
          <Route path="b4f-inspection"                element={<B4FInspectionPage />} />
          <Route path="b4f-inspection/:batchId"       element={<B4FInspectionDetailPage />} />
          <Route path="rf-inspection"                 element={<RFInspectionPage />} />
          <Route path="rf-inspection/:batchId"        element={<RFInspectionDetailPage />} />
          <Route path="b2f-inspection"                element={<B2FInspectionPage />} />
          <Route path="b2f-inspection/:batchId"       element={<B2FInspectionDetailPage />} />
          <Route path="b1f-inspection"                element={<B1FInspectionPage />} />
          <Route path="b1f-inspection/:batchId"       element={<B1FInspectionDetailPage />} />
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

        {/* ── 樂群工務報修 ──────────────────────────────────────────────── */}
        <Route path="luqun-repair">
          <Route path="dashboard" element={<LuqunRepairPage />} />
          <Route index            element={<LuqunRepairPage />} />
        </Route>

        {/* ── 大直工務部 ────────────────────────────────────────────────── */}
        <Route path="dazhi-repair">
          <Route path="dashboard" element={<DazhiRepairPage />} />
          <Route index            element={<DazhiRepairPage />} />
        </Route>

        {/* ── ★工項類別分析（樂群+大直共用）────────────────────────────── */}
        <Route path="work-category-analysis" element={<WorkCategoryAnalysisPage />} />

        {/* ── ◆ 董事長簡報 Dashboard（新功能，獨立路由）─────────────────── */}
        <Route path="exec-dashboard" element={<ExecDashboardPage />} />

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

        {/* ── 系統設定 ────────────────────────────────────────────────── */}
        <Route path="settings">
          <Route path="users"              element={<UsersPage />} />
          <Route path="roles"              element={<RolesPage />} />
          <Route path="ragic-connections"    element={<RagicConnectionsPage />} />
          <Route path="ragic-app-directory" element={<RagicAppDirectoryPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  )
}
