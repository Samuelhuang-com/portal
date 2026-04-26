# Portal 功能地圖 (FEATURE_MAP)

> 用途：快速定位任何功能對應的後端/前端檔案，避免每次全程式掃描。
> 維護規則：每次新增模組時，在對應區塊補一行。

---

## 目錄
1. [核心架構](#核心架構)
2. [飯店管理](#飯店管理)
3. [商場管理](#商場管理)
4. [工務報修](#工務報修)
5. [跨案場分析](#跨案場分析)
6. [預算管理](#預算管理)
7. [保全管理](#保全管理)
8. [倉庫管理](#倉庫管理)
9. [流程與溝通](#流程與溝通)
10. [系統設定](#系統設定)
11. [資料同步](#資料同步)
12. [共用基礎設施](#共用基礎設施)
13. [待開發模組（缺口）](#待開發模組缺口)

---

## 核心架構

| 項目 | 路徑 |
|------|------|
| FastAPI 主程式 / 路由掛載 | `backend/app/main.py` |
| 全域設定 (env / Ragic keys) | `backend/app/core/config.py` |
| DB Session (SQLAlchemy) | `backend/app/core/database.py` |
| 預算 DB (獨立 SQLite) | `backend/app/core/budget_database.py` → `backend/budget_system_v1.sqlite` |
| JWT / 密碼工具 | `backend/app/core/security.py` |
| 台灣時區 helper | `backend/app/core/time.py` |
| 加密工具 | `backend/app/core/crypto.py` |
| 排程器設定 | `backend/app/core/scheduler.py` |
| 排程任務清單 | `backend/app/scheduler/jobs.py` |
| 權限依賴注入 | `backend/app/dependencies.py` (get_current_user, require_roles) |
| 前端路由定義 | `frontend/src/App.tsx` |
| Axios 封裝基底 | `frontend/src/api/client.ts` |
| Zustand Auth Store | `frontend/src/stores/authStore.ts` |
| 導航標籤常數 | `frontend/src/constants/navLabels.ts` |
| Sidebar / Header Layout | `frontend/src/components/Layout/MainLayout.tsx` |
| 受保護設計規格 | `docs/PROTECTED.md` |

---

## 飯店管理

### 客房保養（RoomMaintenance）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/room_maintenance.py` → `/api/v1/room-maintenance` |
| Model | `backend/app/models/room_maintenance.py` (RoomMaintenanceRecord) |
| Service / Sync | `backend/app/services/room_maintenance_sync.py`, `room_maintenance_service.py` |
| 前端頁面 | `frontend/src/pages/RoomMaintenance/index.tsx` |
| 前端 API | `frontend/src/api/roomMaintenance.ts` |
| 前端路由 | `/hotel/room-maintenance` |

### 客房保養明細（RoomMaintenanceDetail）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/room_maintenance_detail.py` → `/api/v1/room-maintenance-detail` |
| Model | `backend/app/models/room_maintenance_detail.py` |
| Sync | `backend/app/services/room_maintenance_detail_sync.py` |
| 前端頁面 | `frontend/src/pages/RoomMaintenanceDetail/index.tsx` |
| 前端路由 | `/hotel/room-maintenance-detail` |

### 飯店週期保養表（PeriodicMaintenance）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/periodic_maintenance.py` → `/api/v1/periodic-maintenance` |
| Model | `backend/app/models/periodic_maintenance.py` (PeriodicMaintenanceBatch + Item) |
| Sync | `backend/app/services/periodic_maintenance_sync.py` |
| Schema | `backend/app/schemas/periodic_maintenance.py` |
| 前端頁面 | `frontend/src/pages/PeriodicMaintenance/index.tsx`, `Detail.tsx` |
| 前端 API | `frontend/src/api/periodicMaintenance.ts` |
| 前端路由 | `/hotel/periodic-maintenance`, `/hotel/periodic-maintenance/:batchId` |

### IHG 客房保養（IHGRoomMaintenance）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/ihg_room_maintenance.py` → `/api/v1/ihg-room-maintenance` |
| Model | `backend/app/models/ihg_room_maintenance.py` (IHGRoomMaintenanceMaster + Detail) |
| Sync | `backend/app/services/ihg_room_maintenance_sync.py` |
| 前端頁面 | `frontend/src/pages/IHGRoomMaintenance/index.tsx` |
| 前端 API | `frontend/src/api/ihgRoomMaintenance.ts` |
| 前端路由 | `/hotel/ihg-room-maintenance` |
| Ragic 來源 | `ap12.ragic.com / soutlet001 / periodic-maintenance/4` |
| **缺口** | 季度視角 (`?view=quarter`)、IHG 代碼對照表 尚未開發 |

---

## 商場管理

### 商場 Dashboard
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/mall_dashboard.py` → `/api/v1/mall/dashboard` |
| Schema | `backend/app/schemas/mall_dashboard.py` |
| 前端頁面 | `frontend/src/pages/MallDashboard/index.tsx` |
| 前端路由 | `/mall/dashboard` |

### 商場週期保養表（MallPeriodicMaintenance）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/mall_periodic_maintenance.py` → `/api/v1/mall/periodic-maintenance` |
| Model | `backend/app/models/mall_periodic_maintenance.py` |
| Sync | `backend/app/services/mall_periodic_maintenance_sync.py` |
| 前端頁面 | `frontend/src/pages/MallPeriodicMaintenance/index.tsx`, `Detail.tsx` |
| 前端路由 | `/mall/periodic-maintenance`, `/mall/periodic-maintenance/:batchId` |

### 商場設施巡檢（MallFacilityInspection）
| 層次 | 路徑 |
|------|------|
| API Router (各樓) | `routers/b1f_inspection.py`, `b2f_inspection.py`, `b4f_inspection.py`, `rf_inspection.py` |
| Model (各樓) | `models/b1f_inspection.py`, `b2f_inspection.py`, `b4f_inspection.py`, `rf_inspection.py` |
| Sync (各樓) | `services/b1f_inspection_sync.py` … `rf_inspection_sync.py` |
| API prefix | `/api/v1/mall/b4f-inspection`, `/b2f-...`, `/b1f-...`, `/rf-...` |
| 前端頁面 | `frontend/src/pages/MallFacilityInspection/` (index + 4F / 3F / 1F3F / 1F / B1FB4F) |
| 前端路由 | `/mall-facility-inspection/dashboard`, `/4f`, `/3f`, `/1f-3f`, `/1f`, `/b1f-b4f` |
| 常數定義 | `frontend/src/constants/mallFacilityInspection.ts` |

### 整棟工務巡檢（FullBuildingInspection）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/full_building_inspection.py` |
| 前端頁面 | `frontend/src/pages/FullBuildingInspection/` (index + RF / B4F / B2F / B1F) |
| 前端路由 | `/full-building-inspection/dashboard`, `/rf`, `/b4f`, `/b2f`, `/b1f` |
| 常數定義 | `frontend/src/constants/fullBuildingInspection.ts` |

---

## 工務報修

### 樂群工務報修（LuqunRepair）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/luqun_repair.py` → `/api/v1/luqun-repair` |
| 端點清單 | `/dashboard`, `/detail`, `/stats/repair`, `/stats/fee`, `/stats/closing`, `/stats/type`, `/stats/room`, `/export`, `/filter-options`, `/years` |
| Model | `backend/app/models/luqun_repair.py` (LuqunRepairCase) |
| Service / 統計 | `backend/app/services/luqun_repair_service.py` (RepairCase, compute_dashboard) |
| Sync | `backend/app/services/luqun_repair_sync.py` |
| Schema | `backend/app/schemas/room_maintenance.py` (共用部分) |
| 前端頁面 | `frontend/src/pages/LuqunRepair/index.tsx` |
| 前端 API | `frontend/src/api/luqunRepair.ts` |
| 前端路由 | `/luqun-repair/dashboard` |
| Ragic 來源 | `ap12.ragic.com / soutlet001 / luqun-public-works-repair-reporting-system/6` |
| **缺口** | case_progress 雙欄位、work_type 結構化、completed_at timestamp、照片縮圖、匯出說明列 |

### 大直工務報修（DazhiRepair）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/dazhi_repair.py` → `/api/v1/dazhi-repair` |
| 端點清單 | `/dashboard`, `/detail`, `/stats/*`, `/export`, `/filter-options`, `/years` |
| Model | `backend/app/models/dazhi_repair.py` (DazhiRepairCase) |
| Service / 統計 | `backend/app/services/dazhi_repair_service.py` |
| Sync | `backend/app/services/dazhi_repair_sync.py` |
| 前端頁面 | `frontend/src/pages/DazhiRepair/index.tsx` |
| 前端 API | `frontend/src/api/dazhiRepair.ts` |
| 前端路由 | `/dazhi-repair/dashboard` |
| Ragic 來源 | `ap12.ragic.com / soutlet001 / lequun-public-works/4` |
| **缺口** | 缺 deduction_counter_name 欄位、case_progress 雙欄位、work_type 結構化 |

---

## 跨案場分析

### 工項類別分析（WorkCategoryAnalysis）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/work_category_analysis.py` → `/api/v1/work-category-analysis` |
| 端點 | `/years`, `/persons`, `/stats` |
| 資料來源 | LuqunRepairCase + DazhiRepairCase + RoomMaintenanceDetailRecord (三合一) |
| 類別邏輯 | `_CATEGORY_RULES`（關鍵字，待改結構化） |
| 前端頁面 | `frontend/src/pages/WorkCategoryAnalysis/index.tsx` |
| 前端 API | `frontend/src/api/workCategoryAnalysis.ts` |
| 前端路由 | `/work-category-analysis` |

### 主管簡報 Dashboard（ExecDashboard）
| 層次 | 路徑 |
|------|------|
| 前端頁面 | `frontend/src/pages/ExecDashboard/index.tsx` |
| 前端路由 | `/exec-dashboard` |
| 資料來源 | 呼叫 work_category_analysis + luqun/dazhi_repair APIs |

### 總覽 Dashboard
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/dashboard.py` → `/api/v1/dashboard` |
| 端點 | `/kpi`, `/summary`, `/graph`, `/trend`, `/closure-stats` |
| 前端頁面 | `frontend/src/pages/Dashboard/index.tsx` |
| 前端 API | `frontend/src/api/dashboard.ts`, `dashboardGraph.ts` |
| 前端路由 | `/dashboard` |

---

## 預算管理

### 預算系統（Budget）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/budget.py` → `/api/v1/budget` |
| 端點 | `/dashboard`, `/plans`, `/plans/{id}/details`, `/transactions`, `/reports/budget-vs-actual`, `/reports/data-quality`, `/masters/*`, `/mappings` |
| DB (獨立) | `backend/budget_system_v1.sqlite` |
| DB 管理 | `backend/app/core/budget_database.py` |
| 前端頁面 | `frontend/src/pages/Budget/` (index + Plans/ + Transactions/ + Reports/ + Masters/ + Mappings/) |
| 前端 API | `frontend/src/api/budget.ts` |
| 前端路由 | `/budget/dashboard`, `/plans`, `/plans/:planId`, `/transactions`, `/reports/budget-vs-actual`, `/masters/*`, `/mappings` |
| **缺口** | budget_usage_month (YYYY-MM)、財務解鎖留痕、超支警示視覺、分攤子表 |

---

## 保全管理

### 保全巡邏（SecurityPatrol）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/security_patrol.py` → `/api/v1/security/patrol` |
| Model | `backend/app/models/security_patrol.py` |
| Sync | `backend/app/services/security_patrol_sync.py` |
| Schema | `backend/app/schemas/security_patrol.py` |
| 前端頁面 | `frontend/src/pages/SecurityPatrol/index.tsx`, `Detail.tsx` |
| 前端 API | `frontend/src/api/securityPatrol.ts` |
| 前端路由 | `/security/patrol/:sheetKey`, `/security/patrol/:sheetKey/:batchId` |
| 常數 | `frontend/src/constants/securitySheets.ts` |

### 保全 Dashboard
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/security_dashboard.py` → `/api/v1/security/dashboard` |
| Schema | `backend/app/schemas/security_dashboard.py` |
| 前端頁面 | `frontend/src/pages/SecurityDashboard/index.tsx` |
| 前端路由 | `/security/dashboard` |

---

## 倉庫管理

### 庫存記錄（Inventory）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/inventory.py` → `/api/v1/inventory` |
| Model | `backend/app/models/inventory.py` |
| Service / Sync | `backend/app/services/inventory_service.py`, `inventory_sync.py` |
| Schema | `backend/app/schemas/inventory.py` |
| 前端頁面 | `frontend/src/pages/Inventory/index.tsx` |
| 前端 API | `frontend/src/api/inventory.ts` |
| 前端路由 | `/warehouse/inventory` |

---

## 流程與溝通

### 簽核系統（Approvals）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/approvals.py` → `/api/v1/approvals` |
| Model | `backend/app/models/approval.py` (Approval + Steps + Actions + Files) |
| Service | `backend/app/services/approval_service.py` |
| Schema | `backend/app/schemas/approval.py` |
| 前端頁面 | `frontend/src/pages/Approvals/List.tsx`, `New.tsx`, `Detail.tsx` |
| 前端 API | `frontend/src/api/approvals.ts` |
| 前端路由 | `/approvals/list`, `/approvals/new`, `/approvals/:id` |

### 公告系統（Memos）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/memos.py` → `/api/v1/memos` |
| Model | `backend/app/models/memo.py`, `memo_file.py` |
| Service | `backend/app/services/memo_service.py` |
| Schema | `backend/app/schemas/memo.py` |
| 前端頁面 | `frontend/src/pages/Memos/List.tsx`, `New.tsx`, `Detail.tsx` |
| 前端 API | `frontend/src/api/memos.ts` |
| 前端路由 | `/memos/list`, `/memos/new`, `/memos/:id` |

### 行事曆（Calendar）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/calendar.py` → `/api/v1/calendar` |
| Model | `backend/app/models/calendar_event.py` |
| Schema | `backend/app/schemas/calendar.py` |
| 前端頁面 | `frontend/src/pages/Calendar/index.tsx` |
| 前端 API | `frontend/src/api/calendar.ts` |
| 前端路由 | `/calendar` |

### 上傳（Uploads）
| 層次 | 路徑 |
|------|------|
| API Router | `backend/app/routers/uploads.py` → `/api/v1/upload` |
| 前端 API | `frontend/src/api/downloadFile.ts` |

---

## 系統設定

| 功能 | 後端路由 | 前端頁面 | 前端路由 |
|------|---------|---------|---------|
| 使用者管理 | `routers/users.py` `/api/v1/users` | `pages/Settings/Users.tsx` | `/settings/users` |
| 角色管理 | `routers/auth.py` (部分) | `pages/Settings/Roles.tsx` | `/settings/roles` |
| Ragic 連線管理 | `routers/ragic.py` `/api/v1/ragic` | `pages/Settings/RagicConnections.tsx` | `/settings/ragic-connections` |
| Ragic App 目錄 | `routers/ragic.py` | `pages/Settings/RagicAppDirectory.tsx` | `/settings/ragic-app-directory` |
| 模型 | `models/user.py`, `role.py`, `user_role.py`, `ragic_connection.py`, `ragic_app_directory.py` | — | — |
| Schema | `schemas/user.py`, `schemas/auth.py`, `schemas/ragic.py` | — | — |
| 前端 API | `api/users.ts`, `api/ragic.ts`, `api/tenants.ts` | — | — |

---

## 資料同步

| 項目 | 路徑 |
|------|------|
| 同步記錄主表 | `models/sync_log.py`, `models/module_sync_log.py` |
| 資料快照 | `models/data_snapshot.py` |
| Ragic Adapter (HTTP) | `services/ragic_adapter.py` |
| Ragic 資料服務 | `services/ragic_data_service.py` |
| 通用同步服務 | `services/sync_service.py` |
| 排程任務 | `scheduler/jobs.py` (APScheduler，各模組定時同步) |

---

## 共用基礎設施

| 項目 | 路徑 |
|------|------|
| 審計日誌 | `models/audit_log.py` |
| 租戶主檔 | `models/tenant.py`, `routers/tenants.py`, `schemas/tenant.py` |
| 共用 Schema | `schemas/common.py` |
| DB 初始化腳本 | `backend/init_db.py` |
| Seed 資料腳本 | `backend/scripts/seed.py` |
| Ragic 診斷 | `backend/diagnose_ragic.py` |

---

## 待開發模組（缺口）

> 來源：04-23 整合會議決議，詳見 `docs/DEV_LOG.md` 與 `04-23整合會議_差異分析.xlsx`

| 功能 | 預計路徑 | 優先級 | 對應會議決議 |
|------|---------|--------|------------|
| 事件單 (上級交辦/緊急事件) | `models/event_order.py`, `routers/event_orders.py` | P1 | §事件單與導覽 |
| 案件進度雙欄位 (case_progress) | `models/luqun_repair.py`, `dazhi_repair.py` | P1 | §案件雙欄位 |
| 作業類型結構化欄位 (work_type) | `models/luqun_repair.py`, `dazhi_repair.py` | P1 | §作業類型 |
| IHG 代碼對照表 | `models/ihg_code_reference.py`, `routers/ihg_codes.py` | P2 | §客房保養/巡檢 |
| IHG 保養表季度視角 | `routers/ihg_room_maintenance.py` (?view=quarter) | P1 | §客房保養/巡檢 |
| 預算使用月份欄位 (YYYY-MM) | `core/budget_database.py` budget_transactions | P2 | §預算與請款 |
| 財務解鎖/留痕機制 | `core/budget_database.py` budget_adjustments | P2 | §預算與請款 |
| 照片縮圖+放大 Modal | `frontend/pages/LuqunRepair/`, `DazhiRepair/` | P2 | §儀表板導覽 |
| 問號 Tooltip（KPI 說明） | 各前端儀表板頁面 | P2 | §儀表板導覽 |
| 五級權限矩陣 | `dependencies.py`, `models/role.py` | P2 | §數據品質與權限 |
