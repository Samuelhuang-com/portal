# Portal 功能模組清單（Feature Inventory）

> 最後更新：2026-05-04
> 用途：記錄所有已上線功能的 module_key、路由、權限、Ragic 來源，供操作手冊匯出、文件管理使用。

---

## 格式說明

| 欄位 | 說明 |
|---|---|
| module_key | 功能識別碼（英文小寫 + 底線），對應 employee_manual_export_service.py 的 MODULE_REGISTRY |
| 模組名稱 | 使用者看到的功能名稱 |
| 前端路由 | React Router path |
| 後端 API 前綴 | FastAPI router prefix |
| 主要權限 key | 查看此功能所需的 permission key |
| Ragic 來源 | 對應 Ragic 表單 URL（若有） |
| 狀態 | 上線 / 開發中 / 規劃中 |

---

## 一、Dashboard 類

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| exec_dashboard | 高階主管 Dashboard | /exec-dashboard | exec_dashboard_view | 無（彙整各模組） | ✅ 上線 |
| hotel_mgmt_dashboard | ★ 飯店管理 Dashboard | /hotel/overview | hotel_view | 無（彙整各模組） | ✅ 上線 |
| mall_mgmt_dashboard | 商場管理 Dashboard | /mall/overview | mall_overview_view | 無（彙整各模組） | ✅ 上線 |
| decision_cockpit | 決策駕駛艙 | /decision-cockpit | decision_cockpit_view | 無（彙整各模組） | ✅ 上線 |

---

## 二、飯店管理

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| room_maintenance | 客房保養 | /hotel/room-maintenance | hotel_room_maintenance_view | 飯店客房保養 Ragic Sheet | ✅ 上線 |
| room_maintenance_detail | 飯店客房保養管理 | /hotel/room-maintenance-detail | hotel_room_maintenance_view | 同上 | ✅ 上線 |
| periodic_maintenance | 飯店週期保養表 | /hotel/periodic-maintenance | hotel_periodic_maintenance_view | 週期保養 Ragic Sheet | ✅ 上線 |
| ihg_room_maintenance | IHG 客房保養 | /hotel/ihg-room-maintenance | hotel_ihg_room_maintenance_view | IHG 客房保養 Ragic Sheet | ✅ 上線 |
| hotel_daily_inspection | 飯店每日巡檢 | /hotel/daily-inspection | hotel_daily_inspection_view | 飯店每日巡檢 5 張 Sheet | ✅ 上線 |
| hotel_meter_readings | 每日數值登錄表 | /hotel/daily-meter-readings | hotel_meter_readings_view | 電錶/水錶 4 張 Sheet | ✅ 上線 |

---

## 三、商場管理

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| mall_periodic_maintenance | 商場例行維護 | /mall/periodic-maintenance | mall_periodic_maintenance_view | 商場週期保養 Ragic Sheet | ✅ 上線 |
| full_building_maintenance | 全棟例行維護 | /mall/full-building-maintenance | mall_full_building_maintenance_view | 全棟維護 Ragic Sheet 21 | ✅ 上線 |
| mall_facility_inspection | 春大直工務巡檢 | /mall/facility-inspection | mall_facility_inspection_view | 商場工務巡檢 5 張 Sheet | ✅ 上線 |
| full_building_inspection | 整棟巡檢 | /mall/full-building-inspection | mall_full_building_inspection_view | 整棟巡檢 4 張 Sheet | ✅ 上線 |

---

## 四、工務報修

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| luqun_repair | 樂群工務報修 | /luqun-repair/dashboard | luqun_repair_view | 樂群報修 Ragic Sheet | ✅ 上線 |
| dazhi_repair | 大直工務部 | /dazhi-repair/dashboard | dazhi_repair_view | 大直報修 Ragic Sheet | ✅ 上線 |
| work_category_analysis | 工項類別分析 | /work-category-analysis | work_category_analysis_view | 同報修 Sheet | ✅ 上線 |

---

## 五、保全管理

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| security_patrol | 保全巡檢 | /security/dashboard | security_dashboard_view | 保全巡檢 7 張 Sheet | ✅ 上線 |

---

## 六、協作工具

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| approvals | 簽核管理 | /approvals | approvals_view | 無（Portal 內建） | ✅ 上線 |
| memos | 公告牆 | /memos | memos_view | 無（Portal 內建） | ✅ 上線 |
| calendar | 行事曆 | /calendar | calendar_view | 無（Portal 內建） | ✅ 上線 |
| wiki | 知識庫 | /wiki | 無（全員可用） | 無（Portal 內建） | ✅ 上線 |

---

## 七、財務管理

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| budget | 預算管理 | /budget/dashboard | budget_view | 無（獨立 SQLite） | ✅ 上線 |

---

## 八、系統設定

| module_key | 模組名稱 | 前端路由 | 主要權限 key | Ragic 來源 | 狀態 |
|---|---|---|---|---|---|
| settings_users | 使用者管理 | /settings/users | settings_users_manage | 無 | ✅ 上線 |
| settings_roles | 角色管理 | /settings/roles | settings_roles_manage | 無 | ✅ 上線 |
| settings_ragic | Ragic 設定 | /settings/ragic-connections | settings_ragic_manage | 無 | ✅ 上線 |
| settings_menu | 選單管理 | /settings/menu-config | settings_menu_manage | 無 | ✅ 上線 |
| employee_manual_export | 員工操作手冊匯出 | /settings/employee-manual-export | employee_manual_export_view | 無（Portal 自動產生） | ✅ 上線 |

---

## 附錄：員工操作手冊支援模組一覽

以下模組已在 `employee_manual_export_service.py` 的 `MODULE_REGISTRY` 中建立知識內容，
可透過員工操作手冊匯出功能產生文件：

| module_key | 模組名稱 |
|---|---|
| exec_dashboard | 高階主管 Dashboard |
| hotel_mgmt_dashboard | 飯店管理 Dashboard |
| mall_mgmt_dashboard | 商場管理 Dashboard |
| decision_cockpit | 決策駕駛艙 |
| security_patrol | 保全巡檢 |
| room_maintenance | 報修管理（客房保養） |
| hotel_daily_inspection | 飯店每日巡檢 |
| mall_periodic_maintenance | 商場例行維護 |
| full_building_maintenance | 全棟例行維護 |
