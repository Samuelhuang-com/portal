# 路由 → 功能對照表（Route Feature Map）

> 最後更新：2026-05-04
> 用途：快速查詢任何前端路由對應到哪個功能模組，以及後端 API 前綴。

---

## 前端路由對照表

| 前端路由 | 功能名稱 | 後端 API 前綴 | 主要權限 key | 前端頁面檔案 |
|---|---|---|---|---|
| /dashboard | 系統首頁 Dashboard | /api/v1/dashboard | 無 | pages/Dashboard/index.tsx |
| /exec-dashboard | 高階主管 Dashboard | /api/v1/dashboard | exec_dashboard_view | pages/ExecDashboard/index.tsx |
| /decision-cockpit | 決策駕駛艙 | /api/v1/dashboard（多來源） | decision_cockpit_view | pages/DecisionCockpit/index.tsx |
| /work-category-analysis | 工項類別分析 | /api/v1/（多來源） | work_category_analysis_view | pages/WorkCategoryAnalysis/index.tsx |
| /calendar | 行事曆 | /api/v1/calendar | calendar_view | pages/Calendar/index.tsx |
| /wiki | 知識庫 | /api/v1/wiki | 無 | pages/Wiki/index.tsx |
| /approvals | 簽核清單 | /api/v1/approvals | approvals_view | pages/Approvals/List.tsx |
| /memos | 公告清單 | /api/v1/memos | memos_view | pages/Memos/List.tsx |
| /hotel/overview | ★ 飯店管理 Dashboard | /api/v1/hotel/overview | hotel_view | pages/HotelMgmtDashboard/index.tsx |
| /hotel/room-maintenance | 客房保養 | /api/v1/room-maintenance | hotel_room_maintenance_view | pages/RoomMaintenance/index.tsx |
| /hotel/room-maintenance-detail | 客房保養管理 | /api/v1/room-maintenance-detail | hotel_room_maintenance_view | pages/RoomMaintenanceDetail/index.tsx |
| /hotel/periodic-maintenance | 飯店週期保養表 | /api/v1/periodic-maintenance | hotel_periodic_maintenance_view | pages/PeriodicMaintenance/index.tsx |
| /hotel/ihg-room-maintenance | IHG 客房保養 | /api/v1/ihg-room-maintenance | hotel_ihg_room_maintenance_view | pages/IHGRoomMaintenance/index.tsx |
| /hotel/daily-inspection | 飯店每日巡檢 | /api/v1/hotel/daily-inspection | hotel_daily_inspection_view | pages/HotelDailyInspection/index.tsx |
| /hotel/daily-meter-readings | 每日數值登錄表 | /api/v1/hotel/meter-readings | hotel_meter_readings_view | pages/HotelMeterReadings/index.tsx |
| /mall/overview | 商場管理 Dashboard | /api/v1/mall/overview | mall_overview_view | pages/MallMgmtDashboard/index.tsx |
| /mall/dashboard | 商場週期保養統計 | /api/v1/mall/dashboard | mall_dashboard_view | pages/MallDashboard/index.tsx |
| /mall/periodic-maintenance | 商場例行維護 | /api/v1/mall/periodic-maintenance | mall_periodic_maintenance_view | pages/MallPeriodicMaintenance/index.tsx |
| /mall/full-building-maintenance | 全棟例行維護 | /api/v1/mall/full-building-maintenance | mall_full_building_maintenance_view | pages/FullBuildingMaintenance/index.tsx |
| /mall/facility-inspection | 春大直工務巡檢 | /api/v1/mall-facility-inspection | mall_facility_inspection_view | pages/MallFacilityInspection/index.tsx |
| /mall/full-building-inspection | 整棟巡檢 | /api/v1/full-building-inspection | mall_full_building_inspection_view | pages/FullBuildingInspection/index.tsx |
| /luqun-repair/dashboard | 樂群工務報修 | /api/v1/luqun-repair | luqun_repair_view | pages/LuqunRepair/index.tsx |
| /dazhi-repair/dashboard | 大直工務部 | /api/v1/dazhi-repair | dazhi_repair_view | pages/DazhiRepair/index.tsx |
| /security/dashboard | 保全巡檢 | /api/v1/security/dashboard | security_dashboard_view | pages/SecurityDashboard/index.tsx |
| /budget/dashboard | 預算管理總覽 | /api/v1/budget | budget_view | pages/Budget/index.tsx |
| /settings/users | 使用者管理 | /api/v1/users | settings_users_manage | pages/Settings/Users.tsx |
| /settings/roles | 角色管理 | /api/v1/roles | settings_roles_manage | pages/Settings/Roles.tsx |
| /settings/ragic-connections | Ragic 連線 | /api/v1/ragic | settings_ragic_manage | pages/Settings/RagicConnections.tsx |
| /settings/ragic-app-directory | Ragic 對應表 | /api/v1/ragic | settings_ragic_manage | pages/Settings/RagicAppDirectory.tsx |
| /settings/menu-config | 選單管理 | /api/v1/settings/menu-config | settings_menu_manage | pages/Settings/MenuConfig/index.tsx |
| /settings/employee-manual-export | 員工操作手冊匯出 | /api/v1/employee-manual-export | employee_manual_export_view | pages/Settings/EmployeeManualExport/index.tsx |

---

## 後端 API 前綴對照表

| API 前綴 | 功能模組 | Router 檔案 |
|---|---|---|
| /api/v1/auth | 認證 | routers/auth.py |
| /api/v1/users | 使用者 | routers/users.py |
| /api/v1/roles | 角色 | routers/roles.py |
| /api/v1/role-permissions | 角色權限 | routers/role_permissions.py |
| /api/v1/ragic | Ragic 整合 | routers/ragic.py |
| /api/v1/dashboard | 首頁 Dashboard | routers/dashboard.py |
| /api/v1/hotel/overview | 飯店管理 Dashboard | routers/hotel_overview.py |
| /api/v1/room-maintenance | 客房保養 | routers/room_maintenance.py |
| /api/v1/room-maintenance-detail | 客房保養明細 | routers/room_maintenance_detail.py |
| /api/v1/periodic-maintenance | 飯店週期保養 | routers/periodic_maintenance.py |
| /api/v1/ihg-room-maintenance | IHG 客房保養 | routers/ihg_room_maintenance.py |
| /api/v1/hotel/daily-inspection | 飯店每日巡檢 | routers/hotel_daily_inspection.py |
| /api/v1/hotel/meter-readings | 每日數值登錄表 | routers/hotel_meter_readings.py |
| /api/v1/mall/overview | 商場管理 Dashboard | routers/mall_overview.py |
| /api/v1/mall/dashboard | 商場週期保養統計 | routers/mall_dashboard.py |
| /api/v1/mall/periodic-maintenance | 商場例行維護 | routers/mall_periodic_maintenance.py |
| /api/v1/mall/full-building-maintenance | 全棟例行維護 | routers/full_building_maintenance.py |
| /api/v1/mall-facility-inspection | 春大直工務巡檢 | routers/mall_facility_inspection.py |
| /api/v1/full-building-inspection | 整棟巡檢 | routers/full_building_inspection.py |
| /api/v1/luqun-repair | 樂群工務報修 | routers/luqun_repair.py |
| /api/v1/dazhi-repair | 大直工務部 | routers/dazhi_repair.py |
| /api/v1/security/patrol | 保全巡檢記錄 | routers/security_patrol.py |
| /api/v1/security/dashboard | 保全巡檢統計 | routers/security_dashboard.py |
| /api/v1/budget | 預算管理 | routers/budget.py |
| /api/v1/wiki | 知識庫 | routers/wiki.py |
| /api/v1/employee-manual-export | 員工操作手冊匯出 | routers/employee_manual_export.py |
| /api/v1/settings/menu-config | 選單管理 | routers/menu_config.py |
| /api/v1/approvals | 簽核管理 | routers/approvals.py |
| /api/v1/memos | 公告牆 | routers/memos.py |
| /api/v1/calendar | 行事曆 | routers/calendar.py |
| /api/v1/inventory | 倉庫庫存 | routers/inventory.py |
