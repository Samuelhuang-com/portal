# CHANGELOG

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/)

---

## [1.39.38] - 2026-04-28

### Changed
- **mall/periodic-maintenance & mall/full-building-maintenance Dashboard** — TAB 名稱由「主管儀表板」改為「Dashboard」；新增第 5 個 KPI 卡片「保養時間」（`planned_minutes` 轉換為小時，藍色 `ClockCircleOutlined`）；原進度條旁的「預估工時」移除（資訊已整合至 KPI 卡）；KPI 卡欄寬由 `lg={6}` 調整為 `lg={4}` 以容納 5 欄

---

## [1.39.37] - 2026-04-28

### Fixed
- **側欄跨群組移動後重複顯示** — `applyMenuConfig` 的 `customL2Here` 過濾器改用全域 `baseL2Keys`（所有群組的 L2 keys），而非只有當前 L1 群組的 `baseL2KeysForParent`；修正跨群組移動的 base L2 項目（如 `/dazhi-repair/dashboard` 移至 `mall`）同時出現在 `movedHere` 與 `customL2Here`，造成側欄重複顯示的問題

---

## [1.39.36] - 2026-04-28

### Added
- **RagicAppDirectory 選單位置欄** — `settings/ragic-app-directory` 新增「選單位置」欄，從 `menuItems` 自動推導 `portalUrl` 對應的階層（一階/二階/三階）與選單名稱，Tag 顯示階層（藍=一階、綠=二階、橘=三階），下方顯示對應選單項目名稱；支援篩選與排序；新增 `buildPortalInfoMap()` 工具函式，選單結構異動時自動同步

---

## [1.39.35] - 2026-04-28

### Fixed
- **Menu 三層架構顯示錯誤** — 修正 `applyMenuConfig` 對 L2 群組（有 base children 的項目如 `mall-pm-group`）的處理：改為 merge 而非覆寫，確保 `/mall/dashboard`、`/mall/periodic-maintenance`、`/mall/full-building-maintenance` 三個子項目正確顯示於「商場例行維護」群組下
- **商場管理選單重複「商場例行維護」** — `main.py` 啟動時自動隱藏舊 `custom_1777348120465`（DB 中殘留的舊商場例行維護群組），消除側邊欄兩個同名 L2 群組並存的問題
- **Settings/MenuConfig 未顯示三階子項** — `DEFAULT_MENU_STRUCTURE` 擴充為三層（L1→L2→L3）；`buildWorkItems` 步驟② 處理 grandchildren；`itemMap` 步驟③ 納入 L3 keys；`全棟例行維護` 等三階系統模組現可在選單管理頁面正常顯示與設定

---

## [1.39.34] - 2026-04-28

### Added
- **全棟例行維護模組（新功能）** — Ragic Sheet 21（`periodic-maintenance/21`）同步；後端新增 `full_bldg_pm_batch` + `full_bldg_pm_batch_item` 資料表、`full_building_maintenance_sync.py`（子表格 A/B/C/D 四模式解析）、`full_building_maintenance.py` Router（`/api/v1/mall/full-building-maintenance`）；前端新增 `FullBuildingMaintenance` 頁面（主管儀表板 + 批次清單 + 批次明細 + ItemHistoryDrawer）、`fullBuildingMaintenance.ts` API client；`_auto_sync()` 納入全棟例行維護排程
- **Menu 三層架構重構（商場管理）** — `mall` 群組下新增 `mall-pm-group`（商場例行維護）L2 中間層，整合「商場週期保養（/mall/dashboard）」、「商場例行維護（/mall/periodic-maintenance）」、「全棟例行維護（/mall/full-building-maintenance）」為三層 sidebar；navLabels.ts 補 `mallPmGroup`、`fullBuildingMaintenance` 標籤

---

## [1.39.34] - 2026-04-28

### Fixed
- **三階項目跨 L2 移動失敗（mall-pm-group 類舊版 key）** — `buildWorkItems` Phase ④ 的 `extra` 過濾器移除 `c.menu_key.startsWith('custom_')` 限制，改為只排除 `structureKeys` 中的 base 項目；早期未帶 `custom_` 前綴的使用者建立項目（如 `mall-pm-group`）現可正確加入 itemMap，Phase ⑤ 才能找到父層並插入 reparented 項目
- **sidebar 同步修正** — `applyMenuConfig` 的 `customL2Here` 過濾條件同步調整，移除 `custom_` 前綴限制，改為排除 `baseL2KeysForParent`（當前 L1 的 base 子項）與 `baseL1Keys`，確保舊版 key 的 L2 項目也出現在側邊欄

---

## [1.39.33] - 2026-04-28

### Added
- **自訂選單「數據準備中」佔位頁** — 點擊 `custom_*` key 的選單項目（尚未對應實際模組）時，導向 `/data-preparing` 顯示旋轉圖示 + 「數據準備中 / 此功能模組正在建置」訊息；MainLayout Menu onClick 攔截 `custom_` 前綴，Router 新增對應路由

---

## [1.39.32] - 2026-04-28

### Changed
- **高階主管 Dashboard / ★工項類別分析 提升為一階** — `/exec-dashboard` 與 `/work-category-analysis` 從 `luqun-repair`、`dazhi-repair` 兩個群組的子項移除，改為獨立一階選單項目，位置緊接在 Dashboard 之後；兩個工務群組各自僅保留自身 Dashboard 子項

---

## [1.39.31] - 2026-04-28

### Fixed
- **base 模組掛到三階時顯示路由 key（如 `/mall/dashboard`）** — `applyMenuConfig` 的 `buildItem` 新增 `baseItemInfo` 查找表（遍歷 base L1/L2），label 優先序改為 `custom_label > base 原始 label > menu_key`，icon 同步取用 base 圖示

### Added
- **MenuConfig 刪除功能** — `custom_` 前綴項目右側新增紅色垃圾桶按鈕，搭配 `Popconfirm` 確認；若內含系統模組子項目，刪除時自動退回上一父層（`handleDeleteItem`）；pure custom 子項目則一併遞迴刪除

---

## [1.39.29] - 2026-04-28

### Fixed
- **新增 custom L2 不出現在側邊欄** — `applyMenuConfig` 在每個 base L1 的 children 中補入 `customL2Here`：從 `childrenByParent.get(parent.key)` 取出 `custom_` 前綴且 is_visible 的項目，以 `buildItem` 渲染（FileTextOutlined icon）後加入 children 並按 sort_order 排序
- **custom L2 移為 L3 後側邊欄可正確顯示** — base L2 的 grandchildren 注入邏輯原本就允許 custom_ 孫項目通過 filter，確認邏輯無誤

---

## [1.39.28] - 2026-04-28

### Changed
- **MenuConfig ↔ sidebar 同步架構重構** — 抽出 `computeReparentedL2()` 共用函式（export from MainLayout），`applyMenuConfig` 與 `buildWorkItems` 都呼叫同一份「哪個 L2 被換了父層」的判斷邏輯，不再各自維護，無法漂移
- **儲存後 MenuConfig 立即從 DB 重拉** — `handleSave` 在 `saveMenuConfig` 成功後呼叫 `fetchMenuConfig` 重建 items state，確保 MenuConfig 顯示與 DB 完全一致；同時發送 `menuConfigSaved` 事件讓 sidebar 同步

---

## [1.39.27] - 2026-04-28

### Fixed
- **MenuConfig 重新載入後移動過的項目回到原位** — `buildWorkItems` 新增 `reparentedL2` 邏輯：先掃 DB 找出 `parent_key` 與 base 結構不符的 L2 項目，建樹時從原 L1 排除，待 custom_ 項目注入後再插入新父層；解決「大直工務部 Dashboard / 樂群工務報修 Dashboard 移走後仍顯示在原群組」問題

---

## [1.39.26] - 2026-04-28

### Fixed
- **跨 L1 移動 base L2 項目後側邊欄不反映** — `applyMenuConfig` 新增 `reparentedBaseL2` 追蹤被換父層的 base L2 項目：
  - 原 L1 的 children 過濾時排除已移走的項目（避免在舊位置殘留）
  - 新 L1 的 children 注入被移來的項目（保留原始 icon 與 label）

---

## [1.39.25] - 2026-04-28

### Fixed
- **「移動到」按鈕完全無反應** — 根本原因：Select 的 `key` prop 包含 `moveOpen`，導致每次點擊時 key 變化觸發 remount，useState 重置，dropdown 永遠打不開。改用 Ant Design `Dropdown` + `Button` 取代 Select 偽裝按鈕，行為正確穩定；同時移除不再需要的 `moveOpen` state

---

## [1.39.24] - 2026-04-28

### Changed
- **選單管理結構同步機制重構** — `DEFAULT_MENU_STRUCTURE` 改為直接從 `MainLayout.menuItems` 派生（strip icon），不再手動維護第二份清單；sidebar 新增/移除路由後 MenuConfig 自動同步，「整棟巡檢」、「春大直商場工務巡檢」等已整合的舊 L1 群組不再出現

### Fixed
- `mall-facility-inspection`、`full-building-inspection` L1 群組殘留問題：因現在直接讀 menuItems，這兩個已不在 sidebar 的 L1 群組自然消失

---

## [1.39.23] - 2026-04-28

### Fixed
- **「移動到」按鈕不一定出現** — 移除一階項目「必須無子項目才顯示移動選項」的限制；一階項目現在永遠可選擇移到其他群組下（子項目一併跟著成為三階）
- **「移動到」重複選同一選項無反應** — Select 改用 `value={undefined}` 並加 `key` prop，確保每次開啟都重置選中狀態

---

## [1.39.22] - 2026-04-28

### Fixed
- **選單管理模組顯示已整合的舊路由** — 從 `DEFAULT_MENU_STRUCTURE` 的 `mall` 群組移除已整合為 Tab 的舊子路由（`/mall/b4f-inspection`、`/mall/rf-inspection`、`/mall/b2f-inspection`、`/mall/b1f-inspection`）
- **DB 殘留項目死而復生** — `buildWorkItems` 的 extra DB 注入邏輯改為只插入 `custom_` 前綴項目，非 custom 的 DB 殘留紀錄不再被撿回；使用者下次儲存後 DB 將自動清除舊紀錄

---

## [1.39.21] - 2026-04-28

### Fixed
- **側邊欄與選單管理模組不同步** — 儲存後立即透過 `menuConfigSaved` 自訂事件通知 `MainLayout` 重新載入，無需手動重新整理頁面
- **側邊欄多出基底項目（附圖二）** — `customL1` 注入邏輯改為只注入 `custom_` 前綴的使用者自建項目，防止 `mall-facility-inspection`、`full-building-inspection` 等基底 key 被錯誤注入為文件圖示獨立選單

---

## [1.39.20] - 2026-04-28

### Changed
- **春大直商場工務巡檢整合（商場管理）** — 將「春大直商場工務巡檢」獨立群組（原含 Dashboard + 4F/3F/1F~3F/1F/B1F~B4F 五個子頁面）整合為商場管理群組下的單一「春大直工務巡檢」入口
  - `MallFacilityInspection/index.tsx` 全面重寫：新增 `type="card"` 六 Tab 架構（統計總覽 / 4F / 3F / 1F~3F / 1F / B1F~B4F 巡檢紀錄）
  - 各樓層 Tab 共用 `FloorListTab` 元件；使用真實 API（`fetchMallFacilityBatches` + `syncMallFacilityFromRagic`）；懶載入，首次切入才掛載
  - 統計總覽 Tab 保留原有真實 API 呼叫（`fetchMallFacilityDashboardSummary` + `syncMallFacilityAllFromRagic`）
  - `MainLayout` 側邊欄「春大直商場工務巡檢」獨立群組移除；改於「商場管理」群組下新增 `/mall-facility-inspection/dashboard` 子項目（第三個，排於整棟巡檢之後）
  - `navLabels.ts` `mallFacilityDashboard` 改名為「春大直工務巡檢」
  - Breadcrumb 更新為「商場管理 › 春大直工務巡檢」
  - URL query param `?tab=summary|4f|3f|1f-3f|1f|b1f-b4f` 支援直接導航至指定 Tab

---

## [1.39.19] - 2026-04-28

### Changed
- **整棟巡檢整合（商場管理）** — 將「整棟巡檢」群組（原含 Dashboard + RF/B4F/B2F/B1F 四個獨立子頁面）整合為商場管理群組下的單一「整棟巡檢」入口
  - `FullBuildingInspection/index.tsx` 全面重寫：新增 `type="card"` 五 Tab 架構（統計總覽 / RF 巡檢 / B4F 巡檢 / B2F 巡檢 / B1F 巡檢）
  - 各樓層 Tab 共用 `FloorInspectionListTab` 元件（月份篩選、重新整理、同步 Ragic、場次列表）；懶載入，首次切入才掛載
  - `MainLayout` 側邊欄「整棟巡檢」獨立群組移除；改於「商場管理」群組下新增 `/full-building-inspection/dashboard` 子項目
  - `navLabels.ts` `fullBuildingDashboard` 改名為「整棟巡檢」（去除「Dashboard」後綴）
  - Breadcrumb 從原「整棟巡檢群組」更新為「商場管理 › 整棟巡檢」
  - URL query param `?tab=summary|rf|b4f|b2f|b1f` 支援直接導航至指定 Tab

---

## [1.39.18] - 2026-04-28

### Changed
- **商場管理整合（商場週期保養）** — 將「商場管理」群組原有的六個獨立子頁面（商場週期保養、B4F / RF / B2F / B1F 巡檢紀錄、Dashboard）整合為單一「商場週期保養」頁面
  - `MallDashboard/index.tsx` 全面重寫：新增 `type="card"` 六 Tab 架構（統計總覽 / 週期保養 / B4F 巡檢 / RF 巡檢 / B2F 巡檢 / B1F 巡檢）
  - 各巡檢 Tab 支援月份篩選、重新整理、同步 Ragic；切換 Tab 時懶載入資料（首次切入才呼叫 API）
  - `MainLayout` 側邊欄「商場管理」群組簡化為單一入口 `/mall/dashboard`，移除五個個別子選單
  - `navLabels.ts` `mallDashboard` 改名為「商場週期保養」
  - Detail 路由（`/:batchId`）與後端 API 不變，各模組明細頁保持原有功能

---

## [1.39.17] - 2026-04-28

### Added
- **選單管理（系統設定 → 選單管理）**
  - 新增 `menu_configs` / `menu_config_history` 資料表與後端 Router（`GET/PUT /api/v1/settings/menu-config`、`GET /api/v1/settings/menu-config/history`）
  - 前端新增 `/settings/menu-config` 頁面：拖拉調整一級群組與各子選單順序（`@dnd-kit/sortable`）、雙擊或點擊鉛筆 inline 改名、DragOverlay 懸浮預覽
  - 儲存時自動記錄變更差異（diff_json）與全量快照（snapshot_json），保留最近 5 筆歷史；右側 Drawer 顯示操作者、時間與詳細 diff
  - `MainLayout` 啟動時靜默拉取設定，動態合併自訂 label 與排序；拉取失敗時 fallback 至預設值不影響使用
  - 安裝 `@dnd-kit/core` v6、`@dnd-kit/sortable` v10、`@dnd-kit/utilities` v3
  - **新增選單**：「新增一階選單」按鈕（Header）與各群組內「新增子選單」按鈕，自動產生 `custom_${timestamp}` key，輸入顯示名稱即可建立
  - **隱藏/顯示**：每列新增眼睛圖示（`EyeOutlined`/`EyeInvisibleOutlined`）；隱藏父層時子層一併隱藏；隱藏項目以刪除線 + 灰底 + "已隱藏" Tag 標示；`MainLayout` 同步過濾 `is_visible: false` 項目不顯示於側邊欄
  - **跨層移動**：子項目可升為一階選單或移到其他父層下；無子項目的一階選單可降為任一父層的子選單；使用 `ArrowsAltOutlined` 圖示 + Ant Design `Select` Dropdown 操作
  - **三層結構支援**：選單管理與側邊欄均支援三層結構（一階群組 → 二階子選單 → 三階孫選單）；每個二階列新增「新增子選單」按鈕；移動選項涵蓋三層間任意升降；`MainLayout.applyMenuConfig` 及 `openKeys` 同步更新支援三層展開
  - **UI 整理**：新增圖示說明列（拖拉/改名/顯隱/移動）、各行顯示一/二/三階色票 Tag、新增按鈕依階層配色（藍/綠/橘）、Modal 標題顯示目標階層與父層名稱、修正更名 Bug（移除 onBlur 衝突、InputRef 型別、custom_ 項目清空邏輯）

---

## [1.39.16] - 2026-04-28

### Fixed
- **RagicAppDirectory（Ragic 應用程式對應表）**
  - 搜尋邏輯補入 `url` 欄位，現在可用 Ragic URL 路徑（如 `luqun-public-works-repair-reporting-system/6`）在 Search 框直接查到對應項目
  - Ragic URL 欄由純圖示改為「圖示 + 路徑文字（截斷）」，Tooltip 顯示完整 URL；欄寬 80 → 220px
  - 搜尋框 placeholder 補充提示「Ragic URL」可搜
  - `scroll.x` 1320 → 1460 配合欄寬調整

---

## [1.39.15] - 2026-04-27

### Added
- **共用元件 `src/components/ExecMetrics/index.tsx`**
  - 匯出 `HeroKpi`（單張 KPI 卡）、`ExecHeroLayer`（6 KPI 卡網格）、`ExecSourceCards`（來源小卡列）、`SOURCE_PIE_COLORS`
  - 預設匯出 `ExecMetricsCard`：自帶資料的主管指標摘要卡，沿用 `@/api/workCategoryAnalysis` fetchStats，不新增任何 API

### Changed
- **Dashboard（集團管理總覽）**
  - 原「預算管理」區塊暫時隱藏（`HIDDEN_BUDGET` 註解保留，程式碼與 API 路由不刪除）
  - 插入 `ExecMetricsCard` 至原預算管理位置（最上方）
- **ExecDashboard（高階主管 Dashboard）**
  - `HeroKpi`、`SOURCE_PIE_COLORS`、`HeroLayer`、`SourceCards` 改用共用元件，消除重複定義
  - 頁面顯示與行為與重構前完全一致

### Fixed
- `@/api/workCategoryAnalysis` `CategoryStats.meta` 型別補上 `last_sync_at?: string`，消除 ExecDashboard TS2339 錯誤

---

## [1.39.16] - 2026-04-26

### Added
- **dazhi + luqun 4.1 報修統計 — 新增「上月累計完成數（① - ②）」列**
  - 公式：上月累計未完成 - 上月未完成本月結案數 = 本月後仍滾存的未結案件數
  - 位置：插入在①（上月累計未完成）和②（本月結案數）之間
  - 可點擊展開明細：顯示從上月累計未完成中，本月未結案的案件清單

---

## [1.39.15] - 2026-04-26

### Fixed
- **大直工務部 — 本月工時統計 KPI 永遠顯示 0.00 hr**
  - 根因：`dazhi_repair_service.py` 讀工時欄位用 `raw.get("維修天數", "")` ，但 Ragic 實際欄位名為 `"維修天數(天)"`（含括號），導致永遠讀不到值
  - 修正：改為 `raw.get("維修天數(天)") or raw.get("維修天數", "")` 兼容兩種名稱
  - 修復後需執行一次手動同步（Settings → 同步大直工務部）讓 DB `work_hours` 欄位更新

---

## [1.39.14] - 2026-04-26

### Changed
- **dazhi + luqun Dashboard — 高工時/高費用 Top 10 加結案狀態圖示**
  - 每筆案件標題右側加小圖示：✅ 綠色 `CheckCircleOutlined`（已結案）/ 🕐 橘色 `ClockCircleOutlined`（未結案）
  - 滑鼠 hover 顯示 tooltip（「已結案」/「未結案」）
  - 不拆分清單，不動版型與其他模組

---

## [1.39.13] - 2026-04-26

### Fixed
- **大直工務部 明細 Tab — 報修詳情 Drawer 新增「維修圖片」顯示**
  - 找出根本原因：`DetailTab` 內的 inline Drawer（第 1704 行）從未包含「維修圖片」欄，先前修改均針對錯誤的 `CaseDetailDrawer` 函式元件
  - 在 `DetailTab` 新增 `drawerImages` / `drawerImgLoading` state + `useEffect` 呼叫 `fetchCaseImages`（DB-first）
  - inline Drawer 末尾新增「維修圖片」`Descriptions.Item`，支援縮圖預覽（`Image.PreviewGroup`）

---

## [1.39.12] - 2026-04-26

### Fixed
- **dazhi + luqun 報修詳情 Drawer — 維修圖片顯示邏輯修正**
  - 修正渲染順序：圖片優先顯示（`images.length > 0` 先判斷），loading spinner 只在「DB 無圖且正在抓 Ragic」時才出現
  - dazhi Drawer `useEffect`：若 `caseData.images` 已有資料則跳過 Ragic lazy-fetch；優先用 DB 圖片（`dbImages > liveImages`）
  - luqun Drawer 同步修正渲染順序（邏輯原已正確，統一調整呈現優先順序）

---

## [1.39.11] - 2026-04-26

### Fixed
- **Session 過期自動跳轉登入頁**
  - `PrivateRoute`：新增 JWT 過期主動偵測（掛載時、每 60 秒、切回分頁時），過期立即 `logout()` + 導向 `/login`
  - `apiClient`：401 攔截器改呼叫 `useAuthStore.getState().logout()` 同步清除 store；加入 `_redirecting` flag 避免同批次多次跳轉
  - `main.py`：靜態檔案服務改 SPA 模式，未知路徑一律回傳 `index.html`，修正直接存取前端路由（如 `/dazhi-repair/dashboard`）會 404 的問題

---

## [1.39.11] - 2026-04-26

### Fixed
- **大直工務部 `dazhi_repair_case` — 完整建置 images_json 鏈路**
  - Model：新增 `images_json TEXT` 欄位、`_parse_images_json()` 方法、`to_dict()` 加入 `"images"` 欄位
  - Sync：`dazhi_repair_sync.py` UPDATE & INSERT 路徑均寫入 `images_json = json.dumps(case.images)`
  - Migration：`main.py` 新增 `_migrate_dazhi_repair_images()`，啟動時自動為舊 DB 補欄位
  - Drawer 圖片顯示路徑：`caseData.images`（DB 同步值）→ lazy-fetch `/images/{ragic_id}`（即時 fallback）

---

## [1.39.10] - 2026-04-26

### Fixed
- **樂群報修詳情 Drawer — 維修圖片（三次修正）：改呼叫正確的 Ragic sheet**
  - 根本原因：圖片 attachment 欄位在 `lequn-public-works/8`（form view），不在清單 sheet `luqun-public-works-repair-reporting-system/6`；原端點呼叫 `/6`，永遠取不到圖片
  - 新增 `RAGIC_LUQUN_REPAIR_IMAGE_PATH=lequn-public-works/8`（.env + config.py）
  - 端點 `/case-images/{ragic_id}` 改用新的 `img_adapter`（指向 `/8`），邏輯與大直 `/images/{ragic_id}` 完全一致：Step1 找 numeric_id → Step2 fetch detail → Step3 解析圖片欄位
  - 搜尋欄位清單：`["上傳圖片", "上傳圖片.1", "維修照上傳", "維修照", "圖片"]`
  - 無圖時仍回傳 `raw_keys` + `img_like_fields` + `raw_data` 供診斷

---

## [1.39.9] - 2026-04-26

### Fixed
- **樂群報修詳情 Drawer — 維修圖片（二次修正）：lazy-fetch 直接向 Ragic 抓**
  - 根本原因：Ragic 圖片欄位在 main list 不保證存在，sync 時有可能抓不到
  - 後端：新增 `GET /api/v1/luqun-repair/case-images/{ragic_id}` 端點，直接呼叫 `adapter.fetch_one()` 解析圖片，不依賴 DB 或 cache
  - 前端 `CaseDetailDrawer`：`useEffect` 監控 `ragic_id`，若 `caseData.images` 為空則自動呼叫新端點；圖片載入中顯示 Spin；載入完顯示縮圖；「維修圖片」欄位始終顯示（改為固定 row）
  - `api/luqunRepair.ts`：新增 `fetchCaseImages()` 封裝函式

---

## [1.39.8] - 2026-04-26

### Added
- **KPI Tooltip — 各儀表板 KPI 卡新增「?」說明圖示**
  - 新增獨立說明檔：`constants/kpiDesc/luqunRepair.ts`、`dazhiRepair.ts`、`securityDashboard.ts`、`mallDashboard.ts`
  - 樂群、大直 `KpiCard` 元件加入 `desc` prop + `QuestionCircleOutlined` Tooltip；保全巡檢、商場管理同步套用
  - 完全不改動版型、顏色、欄位，僅在標題旁附加說明圖示
- **照片縮圖 + Modal — 樂群 / 大直報修 Drawer 圖片改為縮圖預覽**
  - 從文字連結（`<a>` 📷）升級為 72×72 縮圖（`antd Image`）+ `Image.PreviewGroup` 輪播放大
  - 大直保留 `imgLoading` loading 狀態，僅替換渲染方式

---

## [1.39.8] - 2026-04-26

### Fixed
- **樂群報修詳情 Drawer — 維修圖片不顯示（images 永遠空陣列）**
  - 根本原因：`LuqunRepairCase` ORM 的 `to_dict()` 回傳 `"images": []`，images 資料從未同步至 SQLite
  - `luqun_repair.py`：新增 `images_json` (Text, nullable) 欄位；`to_dict()` 改從 `_parse_images_json()` 讀取；`_parse_images_json()` 安全 JSON 解析，例外時回傳 `[]`
  - `main.py`：新增 `_migrate_luqun_repair_images()` — ALTER TABLE 補欄位，startup 自動執行
  - `luqun_repair_sync.py`：sync 時將 `case.images` 序列化為 JSON 存入 `images_json`（existing + insert 兩段均補上）

---

## [1.39.7] - 2026-04-26

### Fixed
- **樂群 金額統計 Tab — 扣款專櫃改為家數統計、排除月份小計**
  - 後端 `compute_fee_stats`：`deduction_counter` 從「費用加總」改為「當月唯一專櫃家數（整數）」；全年小計跨月去重；`month_totals` / `grand_total` 僅加三個金額欄位（委外/維修/扣款費用）
  - 前端 月份格顯示「N 家」、全年小計欄顯示「N 家」；月份小計行不含此欄（後端已排除）；drilldown Modal Tag 改顯示家數

---

## [1.39.6] - 2026-04-26

### Fixed
- **樂群 Dashboard — 扣款專櫃 KPI 卡改為全年統計**
  - `luqun_repair_service.py` 新增 `annual_counter_fee`、`annual_counter_store_names` 欄位（對應既有 `annual_deduction_counter` 年度邏輯）
  - `DashboardKpi` 介面（`types/luqunRepair.ts`）補上 `annual_counter_stores`、`annual_counter_fee`、`annual_counter_store_names` 型別宣告
  - 前端 KPI 卡、Modal 標題/Tag/dataSource 全部切換至全年欄位；「當月金額」摘要卡仍保留月度 `total_counter_stores`（語義正確）

---

## [1.39.5] - 2026-04-26

### Changed
- **工項類別分析 + 主管 Dashboard — 納入 IHG 客房保養工時**
  - `work_category_analysis.py` 新增第 4 個資料來源 `ihg_room`（`IHGRoomMaintenanceMaster`），零前端改動
  - 工時取自 `raw_json["工時計算"]`（分鐘 ÷ 60），與 IHG `/matrix` 端點同一計算邏輯
  - 類別固定為「例行維護」；日期優先取 `maint_date`，無效則以年/月第 1 日為 fallback
  - `SOURCE_LABELS` 新增 `ihg_room: "IHG客房保養"`
  - `_parse_sources("all")` / `_build_kpi()` / `_build_source_breakdown()` / `get_years()` 同步更新
  - `ExecDashboard` 與 `WorkCategoryAnalysis` 共用同一 `/stats` API，**無需前端修改，自動取得新數據**
  - 若 IHG API 回傳空值（無工時記錄），Dashboard 視為 0.00 hr，不影響其他分類統計

---

## [1.39.4] - 2026-04-26

### Added
- **IHG 客房保養 — 季度視角（`?view=quarter`）**
  - 前端 `useMemo` 對 `/matrix` 資料做季度聚合，無需新 API；每季彙總 `normal/done/maint/unchecked` 計數與工時
  - 新增 `QuarterCellComp`：88×66px 格子，顯示季度計數＋工時（hr）＋所涵蓋月份；狀態顏色與月份視角一致
  - 篩選列新增 **月份 ｜ 季度** `Segmented` 切換，更新 URL 參數 `?view=quarter`
  - 季度 Table header 顯示 Q1–Q4 及各季工時合計（hr）
  - 點擊季度格開啟**季度彙整 Drawer**：顯示合計統計摘要，各月份明細表含狀態 Tag、各計數、工時，「查看」按鈕穿透至月份明細 Drawer
  - Card 標題同步顯示「月份視角 / 季度視角」文字提示

---

## [1.39.6] - 2026-04-26

### Added
- **KPI 卡說明 Tooltip（樂群 & 大直工務報修 Dashboard）**
  - 每張 KPI 卡標題右側新增 `?` 圖示，hover 顯示說明文字，不影響原有版型與樣式
  - 說明文字獨立維護於 `frontend/src/constants/kpiDesc/luqunRepair.ts` 及 `dazhiRepair.ts`，方便各模組獨立調整
  - 涵蓋 6 張 KPI 卡：本月相關案件、已完成件數、未完成件數、平均結案天數、本月工時統計、客房報修件數

### Fixed
- IHG 保養表季度視角：確認已實作（`?view=quarter` URL 參數，前端聚合，不需新 API）；於 FEATURE_MAP 標記完成

---

## [1.39.3] - 2026-04-26

### Fixed
- **前端 API client 統一**：`securityPatrol.ts`、`mallFacilityInspection.ts` 改用 `apiClient`（帶 JWT interceptor），不再直接用裸 `axios`，確保 API 請求正確帶 `Authorization: Bearer` header
- **DEV bypass token 修正**：`Login/index.tsx` 的 `devLogin()` 改呼叫真實後端 `admin/admin1234`，不再寫入無效 `'dev-token'` 造成後續所有 API 返回 401
- **商場巡檢 0/0 = 0% 顯示修正**：
  - 後端 `FloorInspectionStats` schema 新增 `has_data: bool` 欄位，`_floor_stats_for_date()` 依 `len(batches) > 0` 設定
  - 前端 `FloorInspectionStats` 型別同步補上 `has_data: boolean`
  - 商場 Dashboard 樓層卡片：`has_data=false` 時改顯示「尚無資料」而非進度條 0%
  - KPI「已完成巡檢」sub-label：無資料時顯示「尚無巡檢資料」而非「完成率 0%」

## [1.39.2] - 2026-04-26

### Security
- **全域 API 身份驗證補強（安全性修正）**
  - 19 個業務 router 補上 `APIRouter(dependencies=[Depends(get_current_user)])`，未登入無法讀取任何業務資料
  - 受保護 router 清單：luqun_repair、dazhi_repair、ihg_room_maintenance、b1f/b2f/b4f/rf_inspection、periodic_maintenance、mall_periodic_maintenance、room_maintenance、room_maintenance_detail、security_patrol、security_dashboard、mall_dashboard、mall_facility_inspection、inventory、calendar、work_category_analysis、full_building_inspection
  - 30 個 sync/debug endpoint（`POST /sync`、`GET /debug-raw`、`GET /debug/ragic-raw`、`GET /raw-fields`、`GET /ping`、`GET /sync` 診斷版等）加上 `require_roles("system_admin", "module_manager")`，防止一般使用者觸發 Ragic 同步或讀取診斷資料

---

## [1.39.1] - 2026-04-24

### Changed
- **IHG 客房保養 — 矩陣格顯示優化與異常狀態**
  - 後端 `/matrix` endpoint：解析每筆記錄 `raw_json`，統計值為「正常」/「當時維護完成」/「等待維護(待料中)」的欄位數量，回傳 `normal_count`/`done_count`/`maint_count`
  - 若任一欄位 = 「等待維護(待料中)」（`maint_count > 0`），格子狀態覆蓋為 `abnormal`（橘色區隔，獨立於逾期紅）
  - 前端矩陣格由「圖示＋日期」改為顯示「正常 X / 完成 Y / 維護 Z ＋日期」計數摘要；維護數 > 0 時以橘色加粗顯示
  - 新增 `STATUS_CFG.abnormal`：bg `#fff7e6`、text `#d46b08`、tagColor `warning`
  - 明細 Drawer：有「等待維護(待料中)」欄位時，在 Ragic 原始欄位區塊上方顯示「維護異常項目」表格，異常列以橘色加粗標示

---

## [1.39.0] - 2026-04-24

### Added
- **IHG 客房保養模組（新功能）**
  - 後端 ORM：`ihg_rm_master`（保養主表）+ `ihg_rm_detail`（子表格明細），對應 Ragic `periodic-maintenance/4`
  - 同步服務：`ihg_room_maintenance_sync.py`，支援 Master + Detail 兩段同步，upsert 策略避免重複寫入
  - API Router：`/api/v1/ihg-room-maintenance`，端點：`/matrix`、`/stats`、`/records`、`/sync`、`/debug-raw`、`/{ragic_id}`
  - 前端頁面：`/hotel/ihg-room-maintenance`，年度保養矩陣表（房號×月份），KPI 統計卡，狀態顏色（已完成/逾期/本月應保養/未完成），點擊格子顯示明細 Modal
  - 篩選功能：年度 / 樓層 / 狀態
  - 同步按鈕：手動觸發 Ragic 同步，自動排程每 30 分鐘執行
  - 新增 `config.py`：`RAGIC_IHG_RM_SERVER_URL/ACCOUNT/SHEET_PATH`
  - Menu 位置：飯店管理 → 1. 飯店週期保養表 → **2. IHG客房保養**（緊接其後）
  - Ragic App Directory 更新：item 204 (`periodic-maintenance/4`) → 對應 `ihg_rm_master + ihg_rm_detail`

---

## [1.38.9] - 2026-04-25

### Changed
- **4.3 報修類型 Tab — 類別定義與說明文字同步更新（樂群 & 大直）**
  - `REPAIR_TYPE_ORDER`：新增 5 個類別（凍&藏類設備、內裝、廚房&吧台設備、會議設備、瓦斯類設備），插入於「專櫃」之後、「公區」之前
  - `REPAIR_TYPE_EXAMPLES`：所有類別內容依規格書 Markdown 表格全面更新（建築/衛廁/消防/機電/給排水/排煙/弱電/照明/公區/後勤空間 均有補充）
  - 前端欄位標題「內容舉例」→「MD內容」（LuqunRepair & DazhiRepair 皆更新）

## [1.38.8] - 2026-04-25

### Fixed
- **樂群工務報修 — 所有明細彈跳視窗統一加入「詳情」功能**
  - 委外+維修費用明細（全年）：寬度 900→1100、加詳情欄、加狀態欄、改分頁顯示、加 scroll
  - 扣款費用明細（全年）：寬度 760→1050、加詳情欄、加狀態欄、改分頁顯示、加 scroll
  - 費用明細（金額統計 drilldown）：寬度 800→1100、加詳情欄、加 scroll、新增 CaseDetailDrawer
  - CaseListModal：`scroll={{ x: 880 }}` 改為 `scroll={{ x: 'max-content' }}` 避免固定寬截斷

## [1.38.7] - 2026-04-25

### Fixed
- **報修詳情 — 管理單位回應 HTML 正確渲染**
  - `luqun_repair_service.py` 新增 `_ragic_html()` 函式：將 Ragic 以方括號儲存的 HTML tag（如 `[br]`、`[table]`、`[/td]`）還原為正常 HTML
  - `LuqunRepair/index.tsx` 詳情 Modal 與 Drawer 的「管理單位回應」欄位：改用 `dangerouslySetInnerHTML` 渲染，顯示格式化的 HTML 內容而非原始 tag 字串

## [1.38.6] - 2026-04-24

### Fixed
- **工項類別分析 / 高階主管 Dashboard — 時間規則與筆數對齊 luqun/dazhi dashboard**
  - `work_category_analysis.py` 新增 `_stat_dt_for(c)` 輔助函式
  - `_load_all` luqun / dazhi 段：year/month/day 改以 stat-month 為準（`completed_at` 優先，未完成用 `occurred_at`），與 luqun-repair/dazhi-repair dashboard 統計規則一致
  - `WorkCategoryAnalysis/index.tsx` 每月累計表（Tab C）：未來月份顯示 `—`
  - `ExecDashboard/index.tsx` 每月累計工時表：未來月份顯示 `—`

## [1.38.5] - 2026-04-24

### Fixed
- **大直工務部（dazhi-repair）時間規則修正，與樂群保持一致**
  - `dazhi_repair_service.py` 新增 `_completed_by` / `_completed_in` / `_closed_in` 輔助函式
  - `compute_repair_stats`：改以 `completed_at` 時間戳判斷完成，不再用 `is_completed_flag`（當前狀態）；跨月完工案件正確歸屬至完工月
  - `compute_closing_time`：改以 `_closed_in(c, y, m)` 判斷結案月，不再用 `filter_cases + is_completed_flag`
  - `query_detail`：年月篩選改用 `_stat_year/_stat_month`（完工月＋未完成報修月），與 Dashboard 邏輯一致
  - `DazhiRepair/index.tsx` Tab 4.1：未來月份欄位顯示 `—`，不顯示不合理數字
  - `DazhiRepair/index.tsx` Tab 4.2：小型／中大型表格未來月份欄位顯示 `—`

## [1.38.4] - 2026-04-23

### Fixed
- **大直工務部（lequn-public-works/8）欄位對應全面修正**
  - 依附圖「工程維修單 房務部查閱用」確認實際 Ragic 欄位
  - `dazhi_repair_service.py` 工時計算：改以 `維修天數`（天 ×24）為主欄位，`花費工時` 降為備用
    - 原邏輯：`花費工時` 優先 → `維修天數` 備用（但該 Ragic Sheet 無「花費工時」欄位，導致工時全部為 0）
  - `work_category_analysis.py` 大直人員：`c.responsible_unit`（反應單位=部門）→ `c.closer`（維修人員=執行人）
    - 原因：反應單位為「房務部」等部門名稱，維修人員才是「吳友仁」等個人姓名
  - `RagicAppDirectory.tsx` 對應表修正：
    - `LOCAL_TABLE_MAP`：新增 `88: 'dazhi_repair_case'`（lequn-public-works/8 為實際同步來源）
    - `PORTAL_DEFAULTS`：itemNo 87、88 改為「大直工務部 / /dazhi-repair/dashboard」（原錯標為樂群工務報修）

## [1.38.3] - 2026-04-23

### Fixed
- **工項類別分析 — 工時計算邏輯統一修正**
  - 工時來源改為：① `花費工時`（HR，直接用）→ ② `工務處理天數`（天 ×24）
  - 人員來源維持：`responsible_unit`（= Ragic `處理工務`）
  - `luqun_repair_service.py`：
    - `RK_WORK_HOURS = "花費工時"`（主欄位）；`__init__` 手動 fallback `工務處理天數 ×24`
  - `dazhi_repair_service.py`：
    - `RK_WORK_HOURS = "花費工時"`（主欄位）；`__init__` 手動 fallback `工務處理天數 / 維修天數 ×24`
    - 恢復 ×24 換算邏輯（上版錯誤移除，天數直存導致數值偏低）
  - `work_category_analysis.py`（Router）：aggregation 邏輯不變，僅更新注解

## [1.38.2] - 2026-04-23

### Fixed
- **工項類別分析 / 高階主管 Dashboard — 人員與工時欄位映射修正**
  - **原錯誤欄位**：人員 = `reporter_name`（報修同仁）；工時 = `花費工時`（luqun）/ `維修天數 × 24`（dazhi）
  - **現正確欄位**：人員 = `responsible_unit`（= Ragic `處理工務`）；工時 = `work_hours`（= Ragic `工務處理天數`）
  - `luqun_repair_service.py`：
    - `RK_WORK_HOURS` 改為 `"工務處理天數"`（原 `"花費工時"`），alias fallback 保留
    - `RK_RESPONSIBLE` alias 已含 `"處理工務"`（首位），無需改動
  - `dazhi_repair_service.py`：
    - `RK_WORK_HOURS` 改為 `"工務處理天數"`（原 `"維修天數"`），移除 `× 24` 轉換
    - `RK_RESPONSIBLE` alias 補入 `"處理工務"` 為首位（原首位 `"反應單位"` 降為備用）
  - `work_category_analysis.py`（Router）：
    - 樂群、大直 `_load_all` 中 `person` 改為 `c.responsible_unit`（原 `c.reporter_name`）
  - hotel_room（房務保養）來源不受影響（仍用 `staff_name`）

## [1.38.1] - 2026-04-23

### Changed
- **高階主管 Dashboard UI 調整**
  - 名稱：「◆ 工項工時 董事長 Dashboard」→「高階主管 Dashboard」
  - 主題：黑金深色背景 → Portal 標準風格（依 PROTECTED.md：白卡、`#1B3A5C` 主色、`#f0f4f8` 頁面背景）
  - 移除全域深色 CSS 覆寫（`.exec-db` 前綴），改用 Ant Design 標準 Card / Table / Collapse
  - 所有內容邏輯（KPI、圖表、表格、決策提示、篩選列）完全保留

## [1.38.0] - 2026-04-23

### Added
- **◆ 董事長簡報 Dashboard（全新獨立功能）**  route: `/exec-dashboard`
  - 既有 `★工項類別分析`（`/work-category-analysis`）完全保留，未修改任何邏輯
  - 資料層：直接沿用現有 `workCategoryAnalysis` API，零後端改動
  - 黑金駕駛艙三層設計：
    - 第一層 Hero KPI：本期總工時（48px 超大字）、人均工時、最高類別、最高人員、最高來源、MoM 環比（紅/綠箭頭）
    - 第二層 2×3 圖表：工項趨勢折線、類別 Donut、人員 Top10 橫柱（依來源著色）、類別×人員 Stacked、來源 Donut+快速卡、集中度進度條
    - 第三層 明細表格（Collapse 可收合）：每日累計、每月累計、人員工時%、人員排名詳細表（支援排序）
    - 自動決策提示：集中度 > 70% 🔴、現場報修 > 40% 🟡、環比 ±25% 🟡、分布正常 🟢
    - 五維篩選工具列（年/月/來源/類別/人員）
    - 全域 CSS 覆寫（深色表格 / Collapse / Select）僅作用於 `.exec-db` 前綴，不影響其他頁面

## [1.37.0] - 2026-04-23

### Changed / Added
- **★工項類別分析 → 升級為主管決策 Dashboard（v2）**
  - 架構原則：單一路由 `/work-category-analysis`，樂群/大直選單共用同一 page
  - 資料整合：三來源合一（樂群工務 + 大直工務 + 房務保養 `RoomMaintenanceDetailRecord`）
    - 房務保養 work_hours 單位為分鐘，自動 ÷60 轉小時；日期從 `maintain_date` string 解析
    - 工項類別：房務保養固定歸入「每日巡檢」；工務報修依 title/repair_type 關鍵字分類
  - 後端 Router 升級：`/stats` 回傳 7 大資料塊
    - `kpi`：總工時、案件數、人員數、平均人工時、最高類別、最高人員、來源占比、環比%
    - `chart_data`：5 類別趨勢折線（月份/日）
    - `category_breakdown`：類別占比（圓餅圖）
    - `person_ranking`：整合三來源人員排名（Top 20）
    - `category_person_matrix`：類別×人員交叉（Stacked Bar，Top 12 人）
    - `source_breakdown`：樂群/大直/房務各自工時、占比、案件數、人員數
    - `concentration`：前3/5/10人佔比、集中度風險警示
    - 表格資料支援 `sources`/`category`/`person` 複合篩選
  - 前端 Dashboard 三層版型：
    - 第一層（KPI Cards）：總工時+環比、案件數、平均人工時、最高類別、最高人員、集中度警示
    - 第二層（Charts）：趨勢圖、圓餅圖、人員排名橫柱圖、類別×人員 stacked bar、來源分析、集中度
    - 第三層（Tables）：每日累計、每月累計、人員工時%、人員排名詳細表
  - 篩選列：年度、月份、來源別、類別、人員（五維篩選）

## [1.36.0] - 2026-04-23

### Added
- **★工項類別分析 新功能模組**
  - 新增後端 `/api/v1/work-category-analysis/`（Router：`work_category_analysis.py`）
    - `GET /years`：整合樂群+大直有資料的年份清單
    - `GET /persons`：依總工時降冪排序的人員清單
    - `GET /stats`：主統計端點，回傳曲線圖/日累計/月累計/人員%四組資料
  - 工項類別分類邏輯：依 title/repair_type 關鍵字歸類為 現場報修／上級交辦／緊急事件／例行維護／每日巡檢；無匹配預設「現場報修」
  - 新增前端頁面 `WorkCategoryAnalysis`（`/work-category-analysis`）
    - A. Dashboard：5 類別折線圖（全年=月份趨勢；選月=日趨勢）
    - B. 每日累計工時表（1~30 日＋星期行＋TOTAL＋%）
    - C. 每月累計工時表（1~12 月＋TOTAL＋%）
    - D. 每月累計工時人員%表（動態人員清單）
  - Menu 掛載：分別加入「樂群工務報修」與「大直工務部」子選單，路由共用同一頁面

## [1.35.14] - 2026-04-24

### Fixed / Added — 樂群工務報修「扣款專櫃」全面修正

**問題根源：** `扣款專櫃` 欄位存放的是**專櫃名稱**（如"牪肉舖"），不是金額。
原程式 `_float("牪肉舖") = 0`，導致 Dashboard 永遠顯示 `$0`。

**後端 `luqun_repair_service.py`：**
- 新增 `RK_MGMT_RESPONSE = "管理單位回應"`
- 新增 `_parse_counter_stores()` helper：解析"多櫃"→讀管理單位回應逐行取店名
- `RepairCase` 新增 3 個欄位：`deduction_counter_name`、`counter_stores`、`mgmt_response`
- `deduction_counter` 保持 0（介面相容），不再錯誤轉換名稱為 float
- `compute_dashboard` 改為計算本月**有扣款的專櫃家數**（`total_counter_stores`）及列表
- `annual_counter_detail` 改用 `deduction_fee > 0 AND deduction_counter_name` 篩選

**前端 `luqunRepair.ts`：** 新增型別 `deduction_counter_name`、`counter_stores`、`mgmt_response`、`total_counter_stores`、`counter_store_names`、`kpi_counter_stores_detail`

**前端 `LuqunRepair/index.tsx`：**
- Dashboard 扣款專櫃卡片：顯示「X 家」（本月有扣款專櫃數）+ 前 2 家名稱
- 扣款專櫃明細彈窗：顯示店名 Tag + 管理單位回應 + 扣款費用
- `CASE_LIST_COLS`：新增「扣款專櫃」欄位（出現在所有 CaseListModal）
- `CaseDetailDrawer`：新增扣款專櫃、各專櫃（多櫃展開）、管理單位回應

## [1.35.13] - 2026-04-24

### Added / Fixed — 大直工務部 Dashboard 邏輯對齊樂群

**Excel 驗算（2026/04）：**
- 舊邏輯（occ月）：138筆，已完成 86，未完成 52
- 新邏輯（完工月）：142筆，已完成 **107**，未完成 **35**，跨月21筆，灰色地帶17筆

**後端 `dazhi_repair_service.py`：**
- `is_completed_flag`：移到 `completed_at` 解析之後，改為 `(completed_at is not None) or is_completed(status)`
- `filter_cases`：新增 `_stat_year/_stat_month` helper，直接讀 `completed_at`，繞過 ORM 舊 year/month 欄位

**後端 `dazhi_repair.py` ORM：**
- `is_completed_flag` property：改為 `(completed_at is not None) or is_completed`
- `to_dict()` `pending_days` 條件：改為 `completed_at is None`

**前端 `DazhiRepair/index.tsx`：**
- `CaseListModal`：新增 `extraColumns` / `tableSummary` 兩個 optional props（與樂群對齊）
- KPI「本月報修件數」→「本月相關案件」，加副標「完工月＋未完成報修月」
- KPI「已完成件數」副標加「依完工時間」；「未完成件數」加「無完工時間的案件」
- KPI「本月工時統計」副標改為「{X.XX} 天（維修天數×24 ÷24）」
- 「已完成案件」彈窗：加說明 Tag ＋「完工時間」額外欄位
- 「未完成案件」彈窗：加說明「完工時間為空的案件」

## [1.35.12] - 2026-04-24

### Fixed
- **樂群 Dashboard 本月工時統計 — 計算邏輯統一為 Σ花費工時**
  - 移除 `_work_metric`（混合「結案天數(天)」和「花費工時(hr)」，單位不一致）
  - 新邏輯：`total_work_hours = Σ(c.work_hours for c in this_month_cases)`，單位純 hr
  - `花費工時 ≈ 工務處理天數 × 24`，÷24 即可換算天數
  - 2026/04 預期值：**10990.15 hr（= 457.92 天）**，含 47 筆（38完成 + 9未完成）
  - KPI 副標改為「{X.XX} 天（花費工時 ÷24）」
  - 工時明細彈窗小計改為純 hr ＋換算天數雙行顯示
  - 「工時指標」extra column 改為「結案天數」（供對照驗算）

## [1.35.11] - 2026-04-24

### Fixed
- **樂群 Dashboard 未完成件數仍顯示 17 的根本原因修正**
  - 問題：Dashboard 讀 SQLite ORM（`load_cases_from_db`），ORM 的 `is_completed`欄位在舊 sync 時存的是 `False`（灰色地帶8筆）
  - 修正 1 — `luqun_repair.py` ORM `is_completed_flag` property：
    改為 `(self.completed_at is not None) or self.is_completed`，不再依賴儲存的 bool 欄位
  - 修正 2 — `luqun_repair_service.py` `filter_cases`：
    新增 `_stat_year/_stat_month` helper，直接從 `completed_at` 計算統計月份，
    繞過 ORM 物件中因舊 sync 導致的 `year/month` 欄位錯誤（跨月灰色地帶案件）
  - 修正 3 — ORM `to_dict()` `pending_days` 條件：改用 `completed_at is None`
  - 效果：2026/04 已完成 20→**38**，未完成 17→**9**，無需重新 sync 即生效

## [1.35.10] - 2026-04-24

### Changed
- **樂群 Dashboard 前端標籤與彈窗說明更新（對應新完工邏輯）**
  - KPI 卡片：「本月報修件數」→「本月相關案件」，副標「完工月＋未完成報修月」
  - KPI 卡片：「未完成件數」加副標「無完工時間的案件」
  - KPI 卡片：「已完成件數」副標加「依完工時間」
  - KPI 卡片：「本月工時統計」副標改為「Σ結案天數＋花費工時（擇一）」
  - 彈窗「本月相關案件」加口徑說明 Tag
  - 彈窗「已完成案件」加說明 Tag + 新增「完工時間」欄位（方便看跨月案件）
  - 彈窗「未完成案件」加說明 Tag「完工時間為空的案件」
  - 彈窗「結案天數明細」加說明「完工時間 − 報修日期」

## [1.35.9] - 2026-04-24

### Fixed
- **樂群工務報修 — 完工判定邏輯修正（灰色地帶問題）**
  - 原邏輯：`is_completed_flag = is_completed(status)`，只看狀態字串，「處理中/待辦驗」即使有完工時間也算未完成
  - 新邏輯：`is_completed_flag = (completed_at is not None) or is_completed(status)`
    - 有「完工時間」→ 無論處理狀況，一律算已完工
    - 狀態為「已辦驗/結案…」但無完工時間 → 仍算已完工（備用）
  - 2026/04 驗算：已完成 20→**38** 筆（+18，含跨月及灰色地帶），未完成 17→**9** 筆
  - 影響：`stat_year/stat_month`、`close_days`、`pending_days`、`top_uncompleted` 全部連動正確

- **樂群工務報修 Dashboard — `this_month_cases` 口徑修正**
  - 改用 `filter_cases(year, month)`（stat 完工月口徑），取代舊的 `occ_year/occ_month`
  - 已完成案件依「完工月份」歸屬，跨月完工案件正確計入

## [1.35.8] - 2026-04-23

### Fixed
- **樂群工務報修 Dashboard — 本月工時統計計算邏輯修正**
  - 原邏輯：`Σ(c.work_hours)` 其中 `work_hours` 可能 = 工務處理天數 × 24（天變小時，導致數字膨脹）
  - 新邏輯：有結案天數（`close_days >= 0`）→ 直接用結案天數；否則用花費工時（`work_hours`）
  - 公式：`本月工時統計 = Σ(close_days if close_days≥0 else work_hours)`，避免 × 24 重複膨脹

### Added
- **樂群工務報修 Dashboard — 工時明細彈窗新增欄位與小計**
  - 新增「花費工時(hr)」欄：顯示 Ragic「花費工時」欄位原始值
  - 新增「工時指標」欄：🔵 顯示結案天數（用於計算）／🟢 顯示花費工時（結案天數為空時）
  - 每頁底部自動顯示「本頁小計」
  - 最後一頁同時顯示「總計」（與 KPI 卡片數字一致可對帳）

## [1.35.7] - 2026-04-23

### Added
- **統一 Ragic 資料存取層 `ragic_data_service.py`**
  - `get_merged_records()`: 主表 + detail merge，採 stale-while-revalidate 快取策略
  - 主表快取 TTL 30s，完整合併快取 TTL 120s
  - `asyncio.Semaphore(10)` 限制並發；背景 `asyncio.create_task` 更新 detail
  - `parse_images()`: 解析 Ragic 附件欄位（HTML img/a tag / list / URL）
  - `safe_work_days_to_hours()`: 工作天數轉小時，上限 365 天防誤植
- **圖片欄位整合（Ragic → Portal）**
  - 大直/樂群 RepairCase 新增 `images` 欄位（`[{url, filename}]`）
  - Drawer 詳情頁：有圖片時顯示「📷 查看圖片」連結，點擊開新分頁
  - 無圖片時不顯示，不影響版型

### Fixed
- **花費工時異常（48624 hr）根本修正**
  - 原因：Ragic「工務處理天數」欄位回傳年份 2026 → 2026 × 24 = 48624 hr
  - 修正：`safe_work_days_to_hours()` 加上限 365 天，超過視為無效，改讀「花費工時」
- **luqun/dazhi `fetch_all_cases()` 改用 merged records**
  - 新增 `invalidate_cache()` 讓 sync 後可清快取

## [1.35.6] - 2026-04-23

### Fixed
- **大直工務部 — `completed_at` 欄位優先順序修正**
  - `RK_COMPLETED_AT` alias 鏈開頭加入 `"完工時間"`：`["完工時間", "維修日期", "結案時間", "完成時間"]`
  - 原來讀「維修日期」，現在優先讀 Ragic「完工時間」欄，找不到才回落「維修日期」
  - 影響模組：`/dazhi-repair/dashboard`、`/work-category-analysis`

- **樂群工務報修 — `occurred_at` 欄位優先順序修正**
  - `RK_OCCURRED_AT` alias 鏈開頭加入 `"報修日期"`：`["報修日期", "發生時間", "實際報修時間", ...]`
  - 原來讀「發生時間」，現在優先讀 Ragic「報修日期」欄，找不到才回落「發生時間」
  - 影響模組：`/luqun-repair/dashboard`、`/work-category-analysis`

- `/exec-dashboard` 不使用樂群/大直報修資料，不受影響

## [1.35.5] - 2026-04-23

### Fixed
- **大直/樂群工務報修 Dashboard — 未完成案件 Top 10 篩選邏輯修正**
  - 原邏輯：`not is_completed_flag`（狀態判斷），可能把有 `completed_at` 但狀態非結案的案件列入
  - 修正：改為 `completed_at is None`（只要有完工日期就排除），符合實際完工事實
  - `pending_days`（已等天數）同步修正：條件改為 `completed_at is None`，有完工時間的案件不再計算等待天數
  - 兩系統後端各 2 處（篩選 + pending_days），共 4 處最小修改

## [1.35.4] - 2026-04-23

### Fixed
- **樂群工務報修 Dashboard — 當月金額卡片數字與「金額統計」Tab 不一致**
  - 根本原因：`compute_dashboard` 的月份費用用 `occ_year/occ_month`（報修日期），但金額統計 Tab 用 `filter_cases(year, month)`（結案案件以結案月份為準），口徑不同
  - 修正：`month_outsource_fee` 等 5 個欄位改用 `filter_cases(all_cases, year, month)` 計算，與金額統計 Tab 完全一致
  - 大直工務部無此問題（`this_month_cases` 原本已用 `filter_cases`，不需修改）

## [1.35.3] - 2026-04-23

### Added
- **大直/樂群工務報修 Dashboard — 新增「當月金額」欄**
  - 保留原有年度費用卡片（大直 2 欄、樂群 3 欄）不變
  - 新增第 4 欄「當月金額」：在同一卡片內緊湊顯示 4 行（委外+維修 / 扣款費用 / 扣款專櫃 / 當月小計）
  - 依 Dashboard 查詢條件（年+月）即時篩選；無資料顯示 `-`
  - 數字來源與「金額統計」Tab 一致（`month_*` 欄位由後端 `compute_dashboard` 提供）
- **後端：`dazhi_repair_service` / `luqun_repair_service`**
  - `compute_dashboard` 新增 5 個當月費用欄位：`month_outsource_fee`、`month_maintenance_fee`、`month_deduction_fee`、`month_deduction_counter`、`month_total_fee`
- **前端型別：`DashboardKpi` 新增 5 個 `month_*` 欄位（兩個系統）**

## [1.35.2] - 2026-04-22

### Fixed
- **大直/樂群工務報修 — 所有彈跳視窗寬度調整，消除橫向捲動**
  - 委外+維修費用明細（全年）：760 → 900px，移除 `scroll={{ x: 600 }}`
  - 扣款費用明細（全年）：700 → 760px，移除 `scroll={{ x: 560 }}`
  - 扣款專櫃明細（全年，樂群）：移除 `scroll={{ x: 560 }}`（700px 本身已足）
  - 金額統計月份明細：720 → 800px，移除 `scroll={{ x: 560 }}`
  - 同步修復兩個檔案尾端殘留 null bytes（`TS1127` Invalid character 錯誤）

## [1.35.1] - 2026-04-22

### Fixed
- **大直工務部 Dashboard — TypeScript 編譯錯誤修復**
  - `types/dazhiRepair.ts`：檔案截斷修復，補全 `DetailQueryParams` / `DetailResult` / `FilterOptions` / `FeeKey` / `FeeMonthRow` / `FeeTotals` / `FeeStatsData` 型別匯出
  - `DazhiRepair/index.tsx`：`FeeStatsTab` 內 `FeeMonthRow` / `FeeTotals` 轉型由 `as Record<string, number>` 改為 `as unknown as Record<string, number>`（解決 TS2352 overlap 錯誤）
  - `npx tsc --noEmit` 確認零錯誤

## [1.35.0] - 2026-04-22

### Fixed
- **大直/樂群工務報修 — 「取消」案件污染統計數字根本修復**
  - 根本原因：「取消」放在 `COMPLETED_STATUSES`，導致 3 月開單 4 月取消的案件，在 3 月的 ⑤ 完成數被多計，且 4 月的 ① 上月未完成少算
  - 新增 `EXCLUDED_STATUSES = {"取消"}` 與 `is_excluded()` 函式，分離「中止」與「完成」語意
  - 從大直 `COMPLETED_STATUSES` 移除 `"取消"`
  - `RepairCase` 新增 `is_excluded_flag` 屬性，加入 `to_dict()` 供前端判斷
  - 所有統計 compute 函式（Dashboard / 4.1 / 4.2 / 4.3 / 4.4 / 金額統計）最前端加一行過濾：`all_cases = [c for c in all_cases if not c.is_excluded_flag]`
  - `query_detail` 明細總表不過濾，保留完整記錄（取消案件仍可查閱）
  - 大直、樂群兩個系統同步更新

## [1.34.9] - 2026-04-22

### Added
- **大直工務部 — 新增「金額統計」Tab（與樂群工務報修介面一致）**
  - 後端 `dazhi_repair_service.py`：新增 `compute_fee_stats()` 函式（委外費用/維修費用/扣款費用 × 12 個月交叉表 + 明細清單）
  - 後端 `dazhi_repair.py`：新增 `GET /stats/fee` 端點
  - 前端 `types/dazhiRepair.ts`：新增 `FeeStatsData` / `FeeMonthRow` / `FeeTotals` / `FeeKey` 型別
  - 前端 `api/dazhiRepair.ts`：新增 `fetchFeeStats()` 函式
  - 前端 `DazhiRepair/index.tsx`：新增 `FeeStatsTab` 元件（點擊格子展開月份明細 Modal）；Tab 由 6 個增為 7 個
  - 說明：大直工務部 Ragic Sheet 目前無費用欄位，金額均顯示為 0；待 Ragic 補上欄位後將自動顯示數據

## [1.34.8] - 2026-04-22

### Added
- **大直/樂群工務報修 4.1 報修統計 — 新增 ⑥ 本月未完成數欄位**
  - 公式：④ 本月報修項目數 − ⑤ 本月報修項目完成數
  - 原 ⑥ 本月報修項目完成率（%）改為 ⑦
  - 後端兩個 service 的 `compute_repair_stats()` 均加入 `this_month_uncompleted`
  - 前端 `MonthRepairStat` TypeScript 介面同步新增欄位
  - 兩個系統（大直/樂群）同步更新

## [1.34.7] - 2026-04-22

### Fixed
- **樂群工務報修 Dashboard KPI 與 Tab 4.1 數字不一致（統計口徑不同）**
  - 根本原因：`compute_dashboard()` 用 `filter_cases()`（完成案件以「結案月份」分類），Tab 4.1 `compute_repair_stats()` 用 `occ_year/occ_month`（永遠以「報修月份」分類）
  - 修正：`compute_dashboard()` 及近 12 月趨勢圖改用 `occ_year/occ_month` 篩選，口徑與 Tab 4.1 一致（「本月報修件數」= 該月份報修的案件，無論結案月份）
  - 修正前：Dashboard 4 月顯示 36 筆（含 4 筆 3 月報修、4 月結案）；修正後：32 筆（=Tab 4.1 ④）
- **樂群工務報修 4.4 客房報修表 Drawer 欄位空白**
  - 同大直工務部 v1.34.3 修復：`compute_room_repair_table()` 矩陣格子改存 `case.to_dict()`，而非僅 `{ragic_id, title, status}` 3 欄

## [1.34.6] - 2026-04-22

### Fixed
- **客房保養明細 CORS + 404 根本修復（307 redirect 繞過 Vite proxy）**
  - `main.py`：`FastAPI()` 加入 `redirect_slashes=False`，防止 FastAPI 對無尾斜線路徑發出 307，讓瀏覽器直接打後端觸發 CORS 封鎖
  - `.env`：`CORS_ORIGINS` 加入 `http://127.0.0.1:5173` 與 `http://127.0.0.1:4173`，確保即使直連後端仍可通過 CORS
  - `room_maintenance_detail.py`：根路由改為同時註冊 `GET ""` 與 `GET "/"`，解決 `redirect_slashes=False` 後 404 問題

## [1.34.5] - 2026-04-22

### Fixed
- **SQLite + OneDrive 鎖定衝突修復（「載入明細資料失敗」根本原因）**
  - `database.py`：SQLite 連線加入 `timeout=30` 及 `pool_pre_ping=True`，DB 被 OneDrive 短暫鎖定時等待而非立即失敗
  - `main.py` lifespan：啟動時明確執行 `PRAGMA journal_mode=WAL; busy_timeout=30000; synchronous=NORMAL`，確保讀寫不互鎖
  - `vite.config.ts`：proxy target 從 `http://localhost:8000` 改為 `http://127.0.0.1:8000`，避免 Windows 11 將 `localhost` 解析成 IPv6 `::1`
- **前端 catch block 加入 `console.error` 輸出**（便於瀏覽器 DevTools 診斷）
- **新增「重新載入」按鈕**（讀取本地 DB，不觸發 Ragic 同步）

## [1.34.4] - 2026-04-22

### Fixed
- **1.1 客房保養明細 — 移除啟動時自動同步 Ragic（根本修復「載入明細資料失敗」）**
  - 原 `main.py` 在 `lifespan` 啟動時執行 `await _auto_sync()`，阻塞伺服器就緒前的請求，導致前端進入頁面時 API 呼叫失敗
  - 移除啟動時立即同步，伺服器啟動後直接從本地 SQLite DB 回傳資料
  - 保留排程同步（每 30 分鐘）與手動「同步資料」按鈕，行為符合規格：進入系統先讀本地 DB，只有手動或排程才同步 Ragic

## [1.34.3] - 2026-04-21

### Fixed
- **大直工務部 4.4 本月客房報修表 — Drawer 資料全空根本修復**
  - 後端 `compute_room_repair_table`：矩陣格子由儲存 `{ragic_id, title, status}` 3 欄改為儲存 `case.to_dict()` 完整欄位，Drawer 才能顯示報修人、樓層、時間等所有資訊
  - 前端：`RoomCategoryEntry` 型別改為 `RepairCase` 別名；移除 `as any` 強轉
  - 前端：多筆案件格子（原本僅顯示 badge 無法點擊）改為逐筆列出並各自可點開 Drawer

## [1.34.2] - 2026-04-21

### Fixed
- **大直工務部 — Ragic 來源 Sheet 路徑修正（根本原因）**
  - `.env` / `config.py` / service 說明：`lequn-public-works/4` → `lequn-public-works/8`（PAGEID=fV8 不變）
  - 原本 Sheet 4 的欄位比 Sheet 8 少，導致同步回來的資料幾乎全空（只有標題、處理狀況）
- **Vite Preview Proxy 修正**
  - `vite.config.ts` 新增 `preview.proxy`（與 `server.proxy` 相同）
  - 修正前：`vite preview`（port 4173）的 `/api` 請求打到靜態檔案伺服器而非後端（port 8000）→ API 全部 404
  - 修正後：preview build 的 API 呼叫正確轉發至 FastAPI 後端

## [1.34.1] - 2026-04-21

### Fixed
- **大直工務部 — 狀態映射修正**
  - 後端：`COMPLETED_STATUSES` 新增 `"已辦驗"`（500 筆，21.5%）與 `"取消"`；原本這些案件被誤算為「未完成」，導致 Dashboard KPI 及完成率統計偏低
  - 前端：`STATUS_COLOR` / `STATUS_TAG_COLOR` 補入 9 個實際出現的狀態（`已辦驗`/`待修中`/`待料中`/`取消`/`委外處理`/`待辦驗`/`辦驗未通過`/`進行中`/`待確認`），避免狀態 Tag 顯示無色

## [1.34.0] - 2026-04-20

### Added
- **Dashboard 主管視角優化（P1）**
  - **P1-E 預算管理摘要卡（首頁最上方）**：從 `getBudgetDashboard()` 讀取年度總預算/總實績/餘額/執行率/超支件數/即將超支件數/資料品質異常，以獨立摘要卡置於 Dashboard 頂端；含執行率進度條、警示 Tag（超支/即將超支/資料異常）、一句話結論、快速入口（預算 Dashboard / 預算比較報表 / 費用交易明細）
  - **P1-C 今日重點摘要區塊**：動態聚合全域待關注、最低完成率群組、工務最久未結案天數、預算超支風險等 3-5 條重點，不需新 API；含紅/黃/綠三色層級顯示
  - **P1-D 全域待關注加入工務+預算子項**：`totalAlerts` 計算新增 `repairPending`（樂群+大直未結案）與 `budgetAlert`（超支+即將超支）；「全域待關注」KPI 卡新增「工務 N」/ 「預算 N」Tag
  - **P1-B 各群組卡一句話結論**：飯店/商場/保全管理三張群組卡各依資料動態產生一句結論（完成率/逾期/異常判讀）；樂群/大直工務報修摘要卡亦補上一句結論
- **P1-A Login 頁正式感優化**：
  - 頁面背景改為品牌漸層色（`#f0f4f8` → `#dce6f0`）
  - 新增集團 Logo 圓角方塊（品牌漸層 `#1B3A5C` → `#4BA8E8`）
  - 加入副標「維春集團內部作業與管理平台」
  - DEV / UAT 環境標示（`import.meta.env.MODE` 判斷）
  - 登入按鈕加入 `loading` 狀態（防重複提交）
  - 錯誤訊息改為 `duration: 4` 不自動快消
  - 開發模式登入按鈕改為 `import.meta.env.DEV` 條件顯示，正式/UAT 環境完全不可見

## [1.33.7] - 2026-04-20

### Added
- **商場工務每日巡檢本地 DB 化**
  - 新增 `MallFIBatch` / `MallFIItem` ORM 模型（`mall_fi_inspection_batch` / `mall_fi_inspection_item` 資料表）；`sheet_key` 欄位區分 5 張樓層 Sheet
  - 新增 `services/mall_facility_inspection_sync.py`：動態欄位偵測 Pivot 同步，支援 5 張 Sheet（4F/3F/1F~3F/1F/B1F~B4F）
  - `routers/mall_facility_inspection.py` 新增端點：
    - `POST /{sheet_key}/sync` — 指定樓層背景同步
    - `POST /sync/all` — 全部 5 張背景同步
    - `GET /{sheet_key}/stats` — 樓層 Dashboard 統計（最新場次 KPI + 異常清單 + 7 日趨勢）
    - `GET /{sheet_key}/batches` — 月份篩選場次清單（含 KPI）
    - `GET /dashboard/summary` — 跨 Sheet 統計（index.tsx Dashboard 用）
  - `main.py` 新增 `mall_fi_inspection` 模型 import + `_auto_sync()` 加入「商場工務巡檢」排程
  - 前端新增 `api/mallFacilityInspection.ts` API 封裝（5 個函式）
  - `InspectionFloorPage.tsx` 替換 3 個 TODO stub：`loadDashboard` / `loadBatches` / `handleSync` 全部接上真實 API；KPI 卡、完成率進度條、異常/待處理清單均顯示真實資料
  - `index.tsx` Dashboard 替換 `loadSummary` / `handleSync` TODO stub；跨 Sheet 統計合併靜態清單呈現
  - `RagicAppDirectory.tsx` `LOCAL_TABLE_MAP` 新增 item 51~55 對應 `mall_fi_inspection_batch` / `mall_fi_inspection_item`

## [1.33.6] - 2026-04-20

### Added
- **Ragic 對應表（系統設定 → Ragic 對應表）**
  - 新增 `RagicAppPortalAnnotation` SQLAlchemy 模型（`ragic_app_portal_annotations` 表）：以 `item_no`（序號 1~219）為主鍵，存放 `portal_name` / `portal_url` 兩個可編輯欄位
  - 後端 `routers/ragic.py` 新增兩支 endpoint：
    - `GET /api/v1/ragic/app-directory/annotations` — 取得所有 Portal 標註（鍵值格式）
    - `PUT /api/v1/ragic/app-directory/annotations/{item_no}` — 新增或更新單筆 Portal 標註（限 system_admin）
  - 前端新增 `pages/Settings/RagicAppDirectory.tsx`：嵌入 219 筆靜態清單；前兩欄可編輯 Portal 標註；已標註列藍底高亮；支援搜尋/類型/模組篩選
  - `router/index.tsx` 新增路由 `/settings/ragic-app-directory`
  - `MainLayout.tsx` 側欄「系統設定」群組新增「Ragic 對應表」（角色管理下方）
  - `navLabels.ts` 新增 `ragicAppDirectory: 'Ragic 對應表'`

## [1.33.9] - 2026-04-20

### Fixed
- **台灣時區統一（系統全面修正）**
  - 新增 `app/core/time.py`：定義 `TW_TZ = timezone(timedelta(hours=8))` 與 `twnow()` helper，所有後端時間戳記統一由此產生
  - 全面替換 34 個檔案中的 `datetime.now(timezone.utc).replace(tzinfo=None)` 與 `datetime.utcnow` → `twnow()`，涵蓋所有 sync services、ORM model `default=` 欄位、routers 的 `generated_at` 等
  - `ragic.py` `GET /sync-logs/recent` 的 `since` 過濾條件改用 `twnow()`，確保 24 小時篩選基準正確
  - 例外：`app/core/security.py` 的 JWT exp 繼續使用 UTC（PyJWT 標準規範）
  - 前端 `RagicConnections.tsx` `fmtTime()` 改為直接 regex 解析 ISO 字串（`MM/DD HH:MM`），不透過 `new Date()` 以避免 browser 將無 tz suffix 的 ISO string 當 UTC 解讀
  - `TECH_SPEC.md` 新增「Taiwan Time Policy」時區政策規格章節，含後端/前端正確與錯誤範例

## [1.33.6] - 2026-04-19

### Fixed
- **同步排程對齊整點（CronTrigger）**
  - `scheduler.py` 新增 `make_cron_trigger(minutes)` helper：< 60 分鐘用 `CronTrigger(minute='0,30',...)`；≥ 60 分鐘用 `CronTrigger(hour='*/N', minute='0')`，確保觸發時刻對齊時鐘整點
  - `main.py` / `scheduler.py` 的 `module_auto_sync` 與 `register_connection_job` 均改用 `make_cron_trigger`，移除 `IntervalTrigger` 依賴
  - `RagicConnections.tsx` Alert 說明更新：顯示各間隔對應的整點時刻範例

### Added
- **同步紀錄頁新增「立即同步」按鈕**
  - 後端新增 `POST /api/v1/ragic/sync-logs/trigger`：背景觸發一次所有硬編碼模組的完整同步，並寫入 `module_sync_log` 紀錄
  - 前端 `api/ragic.ts` 新增 `triggerAllModulesSync()` 函式
  - `RagicConnections.tsx` 同步紀錄卡片右上角新增「立即同步」按鈕；載入失敗改為顯示 warning message 而非靜默失敗

## [1.33.5] - 2026-04-19

### Added
- **同步排程設定頁 — 24 小時同步紀錄**
  - 新增 `ModuleSyncLog` ORM 表（`module_sync_log`）：記錄每次排程/手動同步的模組名稱、狀態、fetched/upserted 筆數、耗時、錯誤訊息、觸發方式
  - `main.py` 加入 `_run_and_log()` helper：任何 sync coroutine 執行後自動寫入 `module_sync_log`
  - `_auto_sync()` 重構：12 個模組全部改用 `await _run_and_log(模組名, coro())`，消除重複的 try/except 樣板
  - 後端新增 `GET /api/v1/ragic/sync-logs/recent?hours=24`：返回最近 N 小時內所有模組同步紀錄，依時間降序
  - 前端 `api/ragic.ts` 新增 `ModuleSyncLogOut` 型別 + `getRecentSyncLogs()` 函式
  - `RagicConnections.tsx` 頁面最下方新增「24 小時同步紀錄」Table：依 started_at 降序排列；欄位含模組名稱、狀態 Tag/Badge、開始時間、耗時、撈取/寫入筆數、錯誤數（Tooltip 顯示訊息）、觸發方式；支援狀態篩選、「重新整理」按鈕

## [1.33.4] - 2026-04-19

### Added
- **預算管理模組 Phase 1 補強**
  - **主檔停用/啟用 UI**：部門 / 會計科目 / 預算項目三個主檔維護頁各新增「停用/啟用」Popconfirm 按鈕；呼叫現有 PUT endpoint 設 `is_active=0/1`；表格新增「狀態」欄顯示啟用/停用 Tag
    - `AccountCodeUpdate` / `BudgetItemUpdate` Pydantic schema 新增 `is_active` 選填欄位（若 DB 尚無欄位須執行 `ALTER TABLE ... ADD COLUMN is_active INTEGER DEFAULT 1`）
  - **交易明細 Excel 匯出**：後端新增 `GET /budget/transactions/export`（pandas + openpyxl，自動欄寬，帶入目前篩選條件）；前端「費用交易明細」頁右上角新增「匯出 Excel」按鈕（含 loading 狀態）
  - **預算主表作廢 / 刪除**：後端新增 `DELETE /budget/plans/{plan_id}`（draft → 硬刪除含所有明細；open/closed/imported → 軟刪除 status='void'）；前端操作欄新增「刪除/作廢」Popconfirm 按鈕（void 狀態行禁用編輯 / 明細 / 作廢按鈕）；篩選下拉補上「已作廢」選項；PUT 合法 status 集合補上 `void`

## [1.33.3] - 2026-04-19

### Added / Fixed
- **Phase 2：Scheduler 橋接 + RagicConnections UI**
  - **後端 bug fix**：`ragic_adapter.py` 新增 `compute_checksum()` 靜態方法（SHA-256）；`sync_service.py` 修正 `RagicAdapter` 建構參數（`server_url` / 解密 `api_key_enc`）、改為 `async def`、加入 `triggered_by` 參數
  - **新增 `app/core/scheduler.py`**：全域 `AsyncIOScheduler` 單例 + `register_connection_job` / `deregister_connection_job` / `list_connection_jobs` helpers
  - **`main.py`**：移除本地 `_scheduler = AsyncIOScheduler()` 改從 `core.scheduler` import；加入 `_init_ragic_connection_jobs()` 於 lifespan startup 掃描所有 active RagicConnection 並建立各自排程任務；硬編碼模組 job ID 由 `room_maintenance_sync` 改為 `module_auto_sync`
  - **`routers/ragic.py` 擴充**：新增 `DELETE /connections/{id}`（軟刪除）、`PATCH /connections/{id}/active`（啟停切換）、`GET /scheduler/status`（列出已排程 jobs）；CREATE / UPDATE / DELETE / TOGGLE 操作後自動呼叫 `register_connection_job` / `deregister_connection_job`
  - **`schemas/ragic.py`**：新增 `RagicConnectionUpdate`（api_key 選填）
  - **新增 `frontend/src/api/ragic.ts`**：封裝所有 9 個 Ragic API endpoints 的 TypeScript 客戶端函式
  - **完整實作 `RagicConnections.tsx`**：取代佔位頁面；連線列表 Table + 新增/編輯 Modal（含 API Key 加密 + 選填更新）+ 軟刪除確認 + 啟停 Switch + 手動同步按鈕 + 同步日誌 Drawer（Timeline 時間軸）

---

## [1.33.2] - 2026-04-19

### Added
- **Phase 3：大直/樂群工務報修建立本地 DB** — 落實開發規則「所有 Ragic 同步必須持久化到本地 SQLite」
  - 新增 ORM 模型：`app/models/dazhi_repair.py`（`DazhiRepairCase` 表）、`app/models/luqun_repair.py`（`LuqunRepairCase` 表，含 `deduction_counter`/`occ_year`/`occ_month` 樂群專用欄位）
  - 兩張表均在 `app/main.py` lifespan 中透過 `Base.metadata.create_all()` 自動建立
  - 新增同步服務：`app/services/dazhi_repair_sync.py`、`app/services/luqun_repair_sync.py`（Ragic → SQLite upsert）
  - **大直/樂群 router 所有資料端點改讀本地 DB**（`/years`、`/filter-options`、`/dashboard`、`/stats/*`、`/detail`、`/export`），從 `async def + await svc.fetch_all_cases()` 改為 `def + load_cases_from_db(db)`
  - 兩個 router 各新增 `POST /sync`（背景觸發 Ragic→DB 同步）；原 `GET /sync` 保留為 Ragic 直連診斷端點
  - `_auto_sync()` 排程加入大直/樂群報修同步（每 30 分鐘）
  - ORM 模型加入 `is_completed_flag` property，確保現有統計函式無需修改即可讀取

---

## [1.33.1] - 2026-04-19

### Changed
- **Phase 1：所有模組手動同步改為背景執行** — 10 個模組 router 的 `POST /sync` endpoint 全部從 `await sync_from_ragic()` 改為 `BackgroundTasks.add_task(sync_from_ragic)`，API 立即回傳 `{"success": true, "message": "同步已在背景啟動"}`，不再阻塞畫面
  - 異動檔案：`room_maintenance`、`inventory`、`periodic_maintenance`、`mall_periodic_maintenance`、`security_patrol`、`room_maintenance_detail`、`b1f/b2f/b4f/rf_inspection`（共 10 個 router）
  - `room_maintenance` 的 `create_record` / `update_record` 寫入 Ragic 後觸發的 sync 亦改為背景執行
  - 前端同步按鍵行為不變（點按 → loading → 收到 200 即解鎖）
  - `/api/v1/ragic/connections/{id}/sync` 原已正確使用 BackgroundTasks，不動

---

## [1.33.0] - 2026-04-19

### Added
- **預算管理模組（Phase 1）** — 完整掛入 Portal 左側 Menu（Dashboard 下方）
  - **後端**：獨立 SQLite 連線模組 `budget_database.py`；預算 router 含 24 個 API endpoints
    - `GET /budget/dashboard` — 年度 KPI：總預算 / 實績 / 餘額 / 執行率 / 超支清單 / 部門摘要
    - `GET/POST/PUT /budget/plans` — 預算主表 CRUD（含狀態管理 draft/open/closed）
    - `GET/POST/PUT/DELETE /budget/plans/{id}/details` — 預算明細編列（12 個月欄位）
    - `GET/PUT /budget/transactions` — 交易明細查詢與修正（579 筆既有資料）
    - `GET/POST/PUT /budget/masters/departments` — 部門主檔 CRUD
    - `GET/POST/PUT /budget/masters/account-codes` — 會計科目主檔 CRUD
    - `GET/POST/PUT /budget/masters/budget-items` — 預算項目主檔 CRUD
    - `GET/POST/PUT/DELETE /budget/mappings` — 對照規則維護 CRUD
    - `GET /budget/reports/budget-vs-actual` — 預算比較報表（讀取 view，年度 / 月別模式）
    - `GET /budget/reports/data-quality` — 資料品質問題清單（#REF! / 金額缺漏 / 未對應明細）
  - **前端**：10 個頁面（Dashboard / Plans / Plan Detail / Transactions / BudgetVsActual / Departments / AccountCodes / BudgetItems / Mappings）
  - **權限**：`budget_view`（查詢）/ `budget_manage`（維護）/ `budget_admin`（管理）架構已建立
  - **資料**：使用 `budget_system_v1.sqlite`（2026 年度 579 筆交易 + 預算明細 133 筆）

---

## [1.32.2] - 2026-04-17

### Added
- **首頁 Dashboard — 工務報修主管摘要區（樂群 + 大直）**
  - 新增 ROW 1.5，位於 KPI 總覽與群組摘要之間，兩欄並排
  - 每欄顯示本月 6 大 KPI：報修總數、已結案、未結案、結案率（含色碼進度條）、平均結案天數、工時
  - 最高報修類型 Tag（`↑ 類型 N 件`）
  - 逾期警示 Tag：最久未結案件天數（≥14 天紅、≥7 天橘）
  - 點擊右上角「查看詳情」可直接跳轉各模組
  - 沿用 `/luqun-repair/dashboard` 及 `/dazhi-repair/dashboard` API，year=本年 month=本月
  - 最小侵入修改：僅新增 state、API 呼叫、`RepairSummaryCard` 元件，不影響既有任何元件

---

## [1.32.1] - 2026-04-17

### Fixed
- **樂群工務報修 — 統計月份歸屬修正（結案月份制）**
  - 原邏輯：所有案件的 `year / month` 均來自 `occurred_at`（報修月份）
  - 新邏輯：`is_completed=true AND completed_at ≠ null` 的案件改以 `completed_at`（結案月份）為準；未結案仍沿用 `occurred_at`
  - 新增 `occ_year / occ_month` 欄位（永遠來自 `occurred_at`），供 4.1 報修統計的「本月報修項目數」專用，確保報修量統計不受此規則影響
  - `compute_repair_stats` 中 `cases_up_to_prev / cases_up_to_this / this_month_cases` 改用 `occ_year / occ_month` 過濾，保持 4.1 報修統計的正確性
  - 具體案例 202604-032：occurred_at=2026/01/18、completed_at=2026/04/10 → 統計月份由 1 月改為 4 月（close_days=82 天，total_fee=17,955）
- **規格書更新**：新增 §3.5「統計月份歸屬規則」及案例說明；已知問題表加入本次修正記錄

---

## [1.32.0] - 2026-04-17

### Fixed
- **樂群工務報修 — 4.2 結案時間 統計數依規格書重新驗證**
  - 確認 `completed_at` 瀑布優先順序（完工時間→結案時間→結案日期→驗收時間→前端驗收時間→驗收日期）
  - 確認 `close_days = (completed_at − occurred_at) ÷ 86400`，需 `is_completed=true AND` 兩端日期均有值
  - 4.2 分類標準更新為：小型=`total_fee=0`；中大型=`total_fee>10000`（`is_large_repair()` 函式）

### Added
- **樂群工務報修 — 全模組統計數字可點擊查看明細**
  - Dashboard KPI 卡片（本月報修件數/已完成/未完成/平均結案天數/工時/客房）全部可點擊展開 `CaseListModal`
  - 4.1 報修統計表：①②④⑤ 格子均可點擊，展開對應案件清單
  - 4.2 結案時間：摘要卡三個指標（件數/天數/平均）可點擊；月份表所有非零格子可點擊
  - 4.3 報修類型：各月份格子、合計欄、月份合計列均可點擊
  - 新增 `CaseListModal` 共用元件（支援分頁、點選個別案件開啟詳情 Drawer）
- **Backend 各 compute 函式加入 cases 明細**
  - `compute_closing_time` — `stats_block` 加入 `cases` 欄位
  - `compute_repair_stats` — 各月加入 4 個 `*_detail` 欄位
  - `compute_type_stats` — 各類型加入 `monthly_detail` 欄位
  - `compute_dashboard` — 加入 6 個 `kpi_*_detail` 欄位

---

## [1.31.9] - 2026-04-17

### Fixed
- **樂群工務報修 — 結案判斷 Bug 修正**
  - 將 `已辦驗` 加入 `COMPLETED_STATUSES`，修正實際已結案案件被判定為未完成的問題
  - 根因：Ragic 資料中「處理狀況=已辦驗 + 驗收=結案」為完成狀態，但原集合缺少「已辦驗」，導致 `close_days` 全部回傳 null
  - 以 4 月 Excel 匯出資料驗證：修正後 6 筆結案案件平均結案天數 24.04 天（最短 2.98 天，最長 81.95 天）

### Added
- **樂群工務報修 — 功能規格書**（`樂群工務報修_功能規格書.docx`）
  - 涵蓋：Ragic 欄位映射、時間欄位計算規格（occurred_at / completed_at / is_completed / close_days）、金額計算規格（_float() / total_fee 公式）、API 端點清單、前端頁面規格、已知問題修正紀錄

---

## [1.31.8] - 2026-04-16

### Added
- **樂群工務報修 — 新增「金額統計」Tab**
  - 以交叉表格呈現 4 項費用（委外費用 / 維修費用 / 扣款費用 / 扣款專櫃）× 12 個月，以及項目全年小計、月份橫向小計、全年總計
  - 有金額的格子可點擊，彈出明細 Modal 顯示該費用類型在該月的所有案件（案號、標題、樓層、日期、狀態、費用金額）
  - 後端新增 `compute_fee_stats()` service 函數與 `GET /api/v1/luqun-repair/stats/fee` 端點，回傳 monthly_totals / fee_totals / month_totals / grand_total / monthly_detail
  - 前端新增 `FeeStatsData` TypeScript 型別、`fetchFeeStats()` API 函數、`FeeStatsTab` 元件

---

## [1.31.7] - 2026-04-16

### Fixed / Improved
- **樂群工務報修 Dashboard — 費用 KPI 改為全年累計**
  - 原本費用卡片使用「當月」資料，導致只有當月有費用的案件才計入（例如 4 月扣款費用 $0，但全年實際有 $17,955）
  - 改為使用**選定年度的全年合計**（不受月份篩選影響），與 Ragic 同步摘要的數字一致
  - 委外+維修費用卡片同時顯示委外費用與維修費用各自小計
  - 後端新增 `annual_fee`、`annual_outsource_fee`、`annual_maintenance_fee`、`annual_deduction_fee`、`annual_deduction_counter` 至 KPI 回應
- **樂群工務報修 Dashboard — 費用卡片點擊查看明細**
  - 三張費用卡片均可點擊，彈出 Ant Design Table Modal 顯示對應明細
  - 委外+維修費用明細：案件列表 + 委外費用、維修費用、總計三欄
  - 扣款費用明細：案件列表 + 扣款事項、扣款費用
  - 扣款專櫃明細：案件列表 + 扣款專櫃金額
  - 後端各類明細最多回傳 Top 20 筆

---

## [1.31.6] - 2026-04-16

### Fixed
- **樂群工務報修 — `_float()` 貨幣解析強化**：舊版只剝除 `$`/`,`/空白，遇到 `NT$440,509`、`TWD 440,509`、`440,509元` 等含非數字前後綴的值一律回傳 0，導致委外費用/維修費用/扣款費用等欄位全部計算為 $0
  - 改用 regex 萃取第一段合法數字（支援負號、千分位、小數點），完全忽略貨幣代碼前綴與單位後綴
  - 修正 `"扣款專櫃": []`（空陣列）不再拋出錯誤，正確回傳 0.0
  - 13 個單元測試全數通過（包含 NT$、TWD、元後綴、空 list/dict、負數、小數）
- **樂群工務報修 — Ragic 欄位別名更新**（依 record #533 實測值校正）
  - `RK_REPORTER` 首位別名改為 `報修同仁`（舊：報修人姓名）
  - `RK_OCCURRED_AT` 補充 `實際報修時間`
  - `RK_RESPONSIBLE` 補充 `處理工務`、`交辦主管`
  - `RK_STATUS` 補充 `問題狀態`（實測欄位名稱）
  - `RK_ACCEPT_STATUS` 首位別名改為 `驗收回應`
  - `RK_COMPLETED_AT` 首位別名改為 `完工時間`（實測欄位名稱）
  - `RK_ACCEPT_DATE` 首位別名改為 `驗收時間`、補充 `前端驗收時間`

---

## [1.31.5] - 2026-04-16

### Added
- **樂群工務報修 Dashboard — 費用明細 KPI 列**
  - Dashboard 新增第二 KPI 行（3 欄一排）：委外+維修費用 / 扣款費用 / 扣款專櫃
  - 後端 `compute_dashboard` 新增 `total_deduction_fee`、`total_deduction_counter` 欄位
  - 後端 `RepairCase` 新增 `deduction_counter`（扣款專櫃）欄位，對應 Ragic 欄位 `"扣款專櫃"`
  - TypeScript `DashboardKpi` 與 `RepairCase` 介面同步新增對應欄位
  - 原第一 KPI 行移除「費用總額」卡（已由第二行費用明細列取代，版面更清晰）

---

## [1.31.4] - 2026-04-16

### Added
- **樂群工務報修 — 功能與大直工務部對齊**
  - 頁面右上角新增「連線測試」（藍色）與「同步 Ragic」（紫色漸層）按鈕
  - 「連線測試」彈出 Ping Modal：顯示 Ragic URL、API Key 前綴、HTTP 狀態/耗時/記錄數，並以完整欄位表格呈現第一筆原始 JSON，方便比對欄位名稱
  - 「同步 Ragic」彈出 Sync Modal：顯示總筆數、無日期數、年份分布 Tags、最近 3 筆案件表、Ragic 欄位名稱 Tag 雲
  - 後端 `luqun_repair.py` 的 `/ping` 與 `/sync` 端點在前一版本已新增，本版將前端整合完成
- **樂群工務報修 4.4 本月客房報修表**
  - 樓層篩選改為 Button Pills（點選切換 primary/default，視覺更直覺）
  - 新增統計列：總報修數 / 涉及房間數 / 涉及樓層數
  - 表格 cell 可點擊，彈出 CaseDetailDrawer 檢視案件詳情

---

## [1.31.3] - 2026-04-16

### Fixed
- **大直工務部 — 全面修正 Ragic 欄位對應**（依 /ping 端點實測 record #2315 校正）
  - `報修單編號`（舊：報修編號）、`(備註/詳細說明)`（舊：標題）、`報修人`（舊：報修人姓名）
  - `維修地點`（舊：發生樓層）、`報修日期`（舊：發生時間）、`反應單位`（舊：負責單位）
  - `類型`（舊：報修類型，值為 JSON array）、`處理狀態`（舊：處理狀況）
  - `維修天數`（舊：花費工時，×24 轉為小時）、`維修日期`（舊：結案時間）
  - `維修人員`（舊：結案人）、`驗收人員`（舊：驗收者）、`處理說明`（舊：財務備註）
- 新增 `RK_ALIASES` 首位 alias = 實際欄位名，確保優先命中
- `COMPLETED_STATUSES` 補充「結案」為已確認的大直工務部完成狀態
- `REPAIR_TYPE_MAPPING` 補充蓮蓬頭、浴缸、花灑、水龍頭、面盆等衛廁類型

---

## [1.31.2] - 2026-04-16

### Added
- **大直工務部 — 同步 Ragic 按鈕**：頁面右上角新增「同步 Ragic」按鈕，點擊後即時從 Ragic 抓取全部資料並彈出診斷 Modal，顯示：抓取筆數、日期解析失敗數、年份分布、最近 3 筆案件、Ragic 實際欄位名稱清單，便於診斷欄位對應問題
- **後端** `dazhi_repair.py`：新增 `GET /api/v1/dazhi-repair/sync` 診斷端點

### Fixed
- **樂群工務報修 Dashboard**：KPI 7 張卡片同樣改用 flex 布局，修正 `md={24/7}` 非整數導致第 7 張換行的問題

---

## [1.31.1] - 2026-04-16

### Fixed
- **大直工務部** — Ragic 資料來源 PAGEID 修正：`uIw` → `fV8`（更新 `.env`、`config.py`、`dazhi_repair_service.py`，`fetch_all_cases` 和 `fetch_raw_fields` 均已傳遞 `PAGEID=fV8`）
- **大直工務部 Dashboard** — KPI 卡片 7 張改用 flex 布局（原 `Col md={24/7}` 為非整數導致第 7 張換行），現在確保所有統計卡片排在同一列

---

## [1.31.0] - 2026-04-15

### Added
- **大直工務部模組** — 完整新模組正式納入 Portal，左側 Menu 新增於「樂群工務報修」之後
  - 後端新增 `app/services/dazhi_repair_service.py`（Ragic 資料抓取、欄位清洗、狀態標準化、類型 mapping、房號解析、4.1~4.4 統計公式、Dashboard 統計）
  - 後端新增 `app/routers/dazhi_repair.py`（10 支 API：`/raw-fields`、`/years`、`/filter-options`、`/dashboard`、`/stats/repair`、`/stats/closing`、`/stats/type`、`/stats/room`、`/detail`、`/export`）
  - 後端更新 `app/main.py`：掛載 `dazhi_repair` router（prefix `/api/v1/dazhi-repair`）
  - 後端更新 `app/core/config.py`：新增 `RAGIC_DAZHI_REPAIR_*` 三個設定項
  - 後端更新 `.env`：新增 Ragic 大直工務部連線設定（ap12.ragic.com / soutlet001 / lequn-public-works/4）
  - 前端新增 `types/dazhiRepair.ts`（完整 TypeScript 型別定義）
  - 前端新增 `api/dazhiRepair.ts`（全部 API 封裝，含匯出 Excel URL 建構）
  - 前端新增 `pages/DazhiRepair/index.tsx`（主頁面，含 6 個 Tab：Dashboard / 4.1 / 4.2 / 4.3 / 4.4 / 大直工務部明細）
  - 前端更新 `constants/navLabels.ts`：新增 `dazhi_repair` 群組 + `dazhiRepairDashboard` 頁面標籤
  - 前端更新 `components/Layout/MainLayout.tsx`：左側 Menu 新增「大直工務部」群組
  - 前端更新 `router/index.tsx`：新增 `/dazhi-repair/dashboard` 路由
  - 資料來源：`https://ap12.ragic.com/soutlet001/lequn-public-works/4`

---

## [1.30.0] - 2026-04-15

### Added
- **樂群工務報修模組** — 完整新模組正式納入 Portal，左側 Menu 新增於「商場管理」之後
  - 後端新增 `app/services/luqun_repair_service.py`（Ragic 資料抓取、欄位清洗、狀態標準化、類型 mapping、房號解析、4.1~4.4 統計公式、Dashboard 統計）
  - 後端新增 `app/routers/luqun_repair.py`（8 支 API：`/years`、`/filter-options`、`/dashboard`、`/stats/repair`、`/stats/closing`、`/stats/type`、`/stats/room`、`/detail`、`/export`）
  - 後端更新 `app/main.py`：掛載 `luqun_repair` router（prefix `/api/v1/luqun-repair`）
  - 後端更新 `app/core/config.py`：新增 `RAGIC_LUQUN_REPAIR_*` 三個設定項
  - 後端更新 `.env`：新增 Ragic 樂群工務報修連線設定（ap12.ragic.com / soutlet001 / luqun-public-works-repair-reporting-system/6）
  - 前端新增 `types/luqunRepair.ts`（完整 TypeScript 型別定義）
  - 前端新增 `api/luqunRepair.ts`（全部 API 封裝，含匯出 Excel URL 建構）
  - 前端新增 `pages/LuqunRepair/index.tsx`（主頁面，含 6 個 Tab：Dashboard / 4.1 / 4.2 / 4.3 / 4.4 / 明細總表）
  - 前端更新 `constants/navLabels.ts`：新增 `luqun_repair` 群組 + `luqunRepairDashboard` 頁面標籤
  - 前端更新 `components/Layout/MainLayout.tsx`：左側 Menu 新增「樂群工務報修」群組
  - 前端更新 `router/index.tsx`：新增 `/luqun-repair/dashboard` 路由

---

## [1.29.0] - 2026-04-15

### Added
- **Dashboard 趨勢折線圖** — 後端新增 `GET /api/v1/dashboard/trend`（近 3~30 日，回傳商場巡檢/保全巡檢/客房保養三條完成率折線資料）；前端使用 recharts `LineChart` 呈現，支援 7 日 / 30 日切換（ROW 4）；無資料的日期點自動 null 斷線，不影響其他日期的連線
- **Dashboard 結案率追蹤** — 後端新增 `GET /api/v1/dashboard/closure-stats`（客房保養結案漏斗 + 商場/保全近 30 日異常數 + 簽核流程結案率）；前端新增 ROW 5，四欄卡片顯示「異常 → 已處理 → 已結案」進度與百分比
- `dashboard.ts` 新增 `TrendPoint`, `DashboardTrend`, `ClosureStats` 等型別與 `dashboardApi.trend()`, `dashboardApi.closureStats()` API 函數

---

## [1.28.1] - 2026-04-15

### Fixed
- **GraphView 新增春大直商場工務巡檢、整棟巡檢節點** — 後端 `/graph` 新增 `mall_facility`、`full_building` 2 個巡檢節點（Ragic 直連作業，alert=0）；新增 2 條 anomaly 邊連至對應保養節點；前端 `NODE_POSITIONS` 補上兩節點座標（y=515/615），GraphView 容器高度由 540px 升為 720px；節點總數 11→13、邊總數 8→10

---

## [1.28.0] - 2026-04-15

### Added
- **整棟巡檢** — 新增完整功能模組，整合 4 個樓層巡檢 Ragic 表單（RF / B4F / B2F / B1F）
  - 前端新增 `constants/fullBuildingInspection.ts`（4 個 Sheet 設定常數 + Ragic URL）
  - 前端新增 `pages/FullBuildingInspection/index.tsx`（模組 Dashboard：4 KPI 卡 + 樓層統計表 + Tabs）
  - 前端新增 `pages/FullBuildingInspection/InspectionFloorPage.tsx`（共用樓層元件：主管儀表板 + 巡檢紀錄 Tabs）
  - 前端新增 4 個樓層頁面：`RF.tsx` / `B4F.tsx` / `B2F.tsx` / `B1F.tsx`
  - 前端更新 `constants/navLabels.ts`：新增 `full_building_inspection` 群組 + 5 個頁面標籤
  - 前端更新 `MainLayout.tsx`：左側 Menu 新增群組（春大直商場工務巡檢之後、保全管理之前）
  - 前端更新 `router/index.tsx`：新增 `/full-building-inspection/*` 5 條路由
  - 前端更新 `pages/Dashboard/index.tsx`：ROW 2 新增整棟巡檢快速入口群組卡片
  - 後端新增 `routers/full_building_inspection.py`（`GET /sheets`，回傳 4 個 Sheet 設定）
  - 後端更新 `main.py`：掛載新 router

---

## [1.27.0] - 2026-04-15

### Added
- **春大直商場工務巡檢** — 新增完整功能模組，整合 5 個樓層巡檢 Ragic 表單
  - 前端新增 `constants/mallFacilityInspection.ts`（5 個 Sheet 設定常數 + Ragic URL）
  - 前端新增 `pages/MallFacilityInspection/index.tsx`（模組 Dashboard：樓層快速入口 + 摘要預留區）
  - 前端新增 `pages/MallFacilityInspection/InspectionFloorPage.tsx`（共用樓層巡檢頁元件，支援 iframe 內嵌 Ragic + 展開收合）
  - 前端新增 5 個樓層頁面：`4F.tsx` / `3F.tsx` / `1F3F.tsx` / `1F.tsx` / `B1FB4F.tsx`
  - 前端更新 `constants/navLabels.ts`：新增 `mall_facility_inspection` 群組 + 6 個頁面標籤
  - 前端更新 `MainLayout.tsx`：左側 Menu 新增群組（商場管理之後、保全管理之前）
  - 前端更新 `router/index.tsx`：新增 `/mall-facility-inspection/*` 6 條路由
  - 前端更新 `pages/Dashboard/index.tsx`：ROW 2.5 新增工務巡檢模組入口卡片
  - 後端新增 `routers/mall_facility_inspection.py`（`GET /sheets`，回傳 5 個 Sheet 設定）
  - 後端更新 `main.py`：掛載新 router

---

## [1.26.0] - 2026-04-15

### Changed
- **GraphView 全面升級為操作流程圖（Flow Diagram）**：從 Hub-Spoke 改為「巡檢→保養→簽核→公告」流程鏈
  - 改用 `@xyflow/react` v12（react-flow）套件，取代純 SVG 實作
  - 節點從 6 個擴展為 11 個（B1F/B2F/RF/B4F/保全/客房保養/飯店PM/商場PM/簽核/公告）
  - 邊從 hub-spoke 改為 8 條語意化關係邊，含 DB 直接關聯（Approval→Memo）與業務邏輯邊
  - 邊類型三種：`anomaly`（紅色虛線）、`escalation`（橙色虛線）、`workflow`（紫色實線+動畫）
  - 後端 `/graph` 端點完整重設計：個別計算各巡檢模組異常數、保養逾期/異常數、公告來源數
  - 新增 `MallPeriodicMaintenanceItem`、`SecurityPatrolItem` 到 dashboard.py 聚合查詢
  - 前端節點支援 hover 放大、alert badge、副標籤（逾期/異常分項）、點擊跳轉
  - 右下 MiniMap、左下縮放控制、左上圖例 Panel

---

## [1.25.0] - 2026-04-15

### Added
- **Dashboard 關聯圖譜（GraphView）**：Hub-Spoke SVG 視覺化，呈現各模組異常 / 待辦連結狀態
  - 後端新增 `GET /api/v1/dashboard/graph`（聚合 6 大模組待辦 / 異常計數，無新資料表）
  - 前端新增 `frontend/src/api/dashboardGraph.ts`（API 型別封裝）
  - 前端新增 `frontend/src/components/GraphView/index.tsx`（純 SVG Hub-Spoke，無外部套件）
  - `frontend/src/pages/Dashboard/index.tsx` 新增 ROW 4「模組關聯圖譜」區塊
  - 節點：客房保養、週期保養、商場巡檢、工務巡檢、簽核待辦、近期公告
  - 連線粗細 = alert 數量；節點色 = 狀態（normal/warning/danger）
  - 點擊節點可直接跳轉對應模組；每 60 秒自動刷新

---

## [1.24.0] - 2026-04-15

### Added
- **行事曆（Command Calendar）超級行事曆模組**：Portal 跨模組事件總覽中心，放置於左側 Menu `Dashboard` 之後
  - 後端新增 `backend/app/models/calendar_event.py`（自訂事件資料表 `calendar_custom_events`）
  - 後端新增 `backend/app/schemas/calendar.py`（Pydantic 型別定義）
  - 後端新增 `backend/app/routers/calendar.py`（聚合 API：`/api/v1/calendar/events`、`/today`、`/custom` CRUD）
  - 前端安裝 `@fullcalendar/react` v6.1.20（月/週/日/清單四種視圖）
  - 前端新增 `frontend/src/types/calendar.ts`、`frontend/src/api/calendar.ts`
  - 前端新增 `frontend/src/pages/Calendar/index.tsx`（主頁面：KPI 摘要列、篩選器、FullCalendar 視圖）
  - 前端新增 `frontend/src/pages/Calendar/components/TodayPanel.tsx`（今日重點側邊面板）
  - 前端新增 `frontend/src/pages/Calendar/components/EventDrawer.tsx`（事件詳情抽屜 + 深連結）
  - 整合六大事件來源：飯店週期保養、商場週期保養、保全巡檢、工務巡檢、簽核管理、公告牆
  - 支援自訂事件新增 / 編輯 / 刪除（`calendar_custom_events` 表）
  - `navLabels.ts` 新增 `calendar` 群組與 `calendarMain` 頁面常數
  - `MainLayout.tsx` 新增行事曆 Menu 項目（`CalendarOutlined` 圖示）
  - `router/index.tsx` 新增 `/calendar` 路由
  - `main.py` 新增 `calendar` router 註冊 + `calendar_event` model import

---

## [1.23.0] - 2026-04-14

### Changed
- **Portal 首頁 Dashboard 全面重組**：將 `/dashboard` 從「飯店 + 庫存」單一視角，升級為集團三群組（飯店 / 商場 / 保全）管理總覽首頁
  - `pages/Dashboard/index.tsx`：全新版面，零後端改動
    - **ROW 1 KPI 卡**：新增「商場巡檢完成率」、「保全巡檢完成率」KPI 卡，保留「客房保養完成率」；新增「全域待關注」彙總 Card（商場異常 + PM 逾期 + 保全異常 + 客房未完成合計）
    - **ROW 2 群組摘要卡**：飯店 / 商場 / 保全各一卡；商場卡含 B1F / B2F / RF 各樓層今日完成率 + 本月 PM 完成/逾期；保全卡含今日完成率 + 場次/異常件數 + 有問題 Sheet 列表（最多 3 筆）
    - **ROW 3 系統資訊**：近期同步紀錄（保留原有）+ 倉庫庫存概況（從 Bar Chart 縮為 Statistic + 前 4 類別列表）
    - 每個群組卡均附快速入口 QuickLink，直達各子模組
    - 3 支 API 以 `Promise.allSettled` 平行呼叫（`/dashboard/kpi`、`/mall/dashboard/summary`、`/security/dashboard/summary`），任一失敗不影響其他群組顯示
    - 完整遵守 PROTECTED.md：4 欄 KPI Row、`size="small"`、Breadcrumb 保留、品牌色 #1B3A5C / #4BA8E8、狀態色映射不變

---

## [1.22.2] - 2026-04-14

### Fixed
- **保全巡檢「異常說明%」欄位處理**：Ragic 的「異常說明」、「異常說明2」等欄位為文字備註，應顯示但不計入巡檢評分統計
  - `models/security_patrol.py`：`SecurityPatrolItem` 新增 `is_note BOOLEAN DEFAULT 0`
  - `services/security_patrol_sync.py`：`sync_sheet` 偵測 `item_name` 含「異常說明」→ `is_note=True`、`result_status='note'`、`abnormal_flag=False`，儲存原始文字
  - `routers/security_patrol.py`：`_calc_kpi` 改為僅計算 `is_note=False` 的評分項目；`get_stats` 中 `status_dist`、`recent_abnormal`、`recent_pending`、`abnormal_trend` 均加入 `is_note=False` 過濾
  - `routers/security_dashboard.py`：`_sheet_stats`、`get_issues`、`get_trend` 三處查詢全部加入 `is_note=False` 過濾
  - `schemas/security_patrol.py`：`PatrolItemOut` 新增 `is_note: bool = False`
  - `main.py`：新增 `_migrate_security_patrol_is_note()` 啟動遷移，自動新增欄位並回填現有異常說明記錄，無需重新同步
  - `types/securityPatrol.ts`：`PatrolItem` 新增 `is_note?: boolean`，`result_status` 聯集加入 `'note'`
  - `pages/SecurityPatrol/Detail.tsx`：備註項目以藍色文字 + 備註 Tag 顯示；新增篩選選項「備註說明」；頁腳顯示評分項與備註項分計數

---

## [1.22.1] - 2026-04-14

### Fixed
- **保全巡檢拍照欄位誤判為異常**：Ragic 的「拍照」、「拍照2」、「拍照3」等上傳欄位屬於表單必填項目，非巡檢評分點，空白時會被誤計為「異常」
  - `services/security_patrol_sync.py`：`_extract_check_items` 新增 `if "拍照" in str(key): continue` 過濾，未來同步自動排除所有拍照類欄位
  - `main.py`：新增 `_cleanup_security_patrol_photo_items()` 啟動遷移，刪除 `security_patrol_item` 中現有的拍照欄位記錄（271 筆）；下次重啟後立即生效，無需手動重新同步
  - 修正後各 Sheet 統計（`/stats`）及 Dashboard 摘要（`/dashboard/summary`、`/issues`、`/trend`）均自動套用正確計算

---

## [1.22.0] - 2026-04-14

### Added
- **保全巡檢功能**（Security Patrol）：支援 7 張 Ragic Sheet（security-patrol/1、2、3、4、5、6、9），統一模型架構
  - 後端模型：`models/security_patrol.py`（SecurityPatrolBatch + SecurityPatrolItem，以 sheet_key 區分 7 種 Sheet）
  - 同步服務：`services/security_patrol_sync.py`（動態欄位偵測 Pivot 架構，支援逐 Sheet 或全部同步）
  - Pydantic Schemas：`schemas/security_patrol.py`、`schemas/security_dashboard.py`
  - API Router（巡檢）：`routers/security_patrol.py`，prefix `/api/v1/security/patrol`
    - POST `/sync`：同步全部或指定 Sheet
    - GET `/sheets`：取得所有 Sheet 設定
    - GET `/{sheet_key}/batches`：場次清單（月份/日期篩選）
    - GET `/{sheet_key}/batches/{batch_id}`：場次明細（含 KPI + 項目清單）
    - GET `/{sheet_key}/stats`：全站統計（Dashboard 用）
    - GET `/{sheet_key}/items/item-history`：巡檢點近 N 日歷史
  - API Router（Dashboard）：`routers/security_dashboard.py`，prefix `/api/v1/security/dashboard`
    - GET `/summary`：今日各 Sheet KPI 摘要
    - GET `/issues`：異常/未完成清單（支援 Sheet 篩選）
    - GET `/trend`：近 N 日趨勢資料
  - `config.py`：新增 `RAGIC_SP_SERVER_URL`、`RAGIC_SP_ACCOUNT`
  - `main.py`：新增 router 註冊、model import、auto-sync 任務
  - 前端型別：`types/securityPatrol.ts`
  - 前端 API 封裝：`api/securityPatrol.ts`
  - 前端常數：`constants/securitySheets.ts`（7 張 Sheet 設定）
  - 前端 Dashboard 頁（`pages/SecurityDashboard/index.tsx`）：今日統計 + 異常清單 + 7日趨勢
  - 前端巡檢清單頁（`pages/SecurityPatrol/index.tsx`）：通用元件，依 sheetKey 顯示對應 Sheet
  - 前端巡檢明細頁（`pages/SecurityPatrol/Detail.tsx`）：場次 KPI + 巡檢點清單（篩選/搜尋）
  - 路由：新增 `/security/dashboard`、`/security/patrol/:sheetKey`、`/security/patrol/:sheetKey/:batchId`
  - Sidebar：新增「保全管理」群組（Dashboard + 7 子選單）
  - `navLabels.ts`：新增 `NAV_GROUP.security` + 8 個 `NAV_PAGE` 保全相關項目

---

## [1.21.0] - 2026-04-14

### Added
- **商場管理統計 Dashboard**（Mall Operations Monitoring Dashboard）：整合 B1F / B2F / RF 每日巡檢 + 商場週期保養資料，提供主管管理決策視圖
  - 後端 Schemas：`schemas/mall_dashboard.py`（DashboardSummary、FloorInspectionStats、InspectionSummary、PMSummary、IssueItem、TrendPoint 等）
  - API Router：`routers/mall_dashboard.py`，prefix `/api/v1/mall/dashboard`
    - GET `/summary`：今日巡檢 KPI（各樓層分析）+ 本月週期保養 KPI
    - GET `/issues`：異常 / 未完成 / 逾期項目清單（可依類型、樓層、狀態篩選）
    - GET `/trend`：近 7 / 30 日巡檢趨勢資料
  - 前端型別：`types/mallDashboard.ts`
  - 前端 API 封裝：`api/mallDashboard.ts`
  - 前端 Dashboard 頁（`pages/MallDashboard/index.tsx`）：
    - 8 張 KPI 卡（4 巡檢 + 4 保養，可點擊跳至對應清單）
    - 整體完成率進度條
    - 各樓層執行比較圖（完成率橫條圖 + 異常/未巡檢堆疊橫條圖）
    - 各樓層摘要卡（含快速連結）
    - 今日巡檢狀態圓餅圖
    - 本月保養狀態摘要
    - 近 7 / 30 日完成率折線趨勢圖
    - 每日異常件數長條趨勢圖
    - 重點追蹤清單（Tabs：全部 / 異常 / 未完成 / 逾期保養；含明細深連結）
  - 導覽：`NAV_PAGE.mallDashboard`，路由 `/mall/dashboard`，位於商場管理選單第一項（整棟工務每日巡檢 - B1F 之前）

---

## [1.20.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 B1F**：串接 Ragic Sheet 4（`soutlet001/full-building-inspection/4`），置於「商場管理」群組
  - 後端 ORM 模型：`b1f_inspection_batch` / `b1f_inspection_item`（`models/b1f_inspection.py`）
  - Pydantic Schemas：`B1FInspectionBatchOut`、`B1FInspectionItemOut`、`B1FInspectionBatchKPI`、`B1FInspectionStats` 等（`schemas/b1f_inspection.py`）
  - 同步服務：`services/b1f_inspection_sync.py`（動態欄位偵測，Sheet 4 欄位自動 pivot）
  - API Router：`/api/v1/mall/b1f-inspection`（8 個端點，同 RF/B2F 規格）
  - APScheduler：每 30 分鐘自動同步 B1F 資料
  - 前端型別：`types/b1fInspection.ts`
  - 前端 API 封裝：`api/b1fInspection.ts`
  - 前端儀表板（`pages/B1FInspection/index.tsx`）：4 KPI 卡 + 完成率進度條 + 7 日異常趨勢 + 狀態圓餅 + 預警清單 + 最新場次入口
  - 前端明細頁（`pages/B1FInspection/Detail.tsx`）：場次資訊卡 + 4 欄巡檢表格 + 狀態 Tab + 30 日歷史 Drawer
  - 導覽：`NAV_PAGE.b1fInspection`，路由 `/mall/b1f-inspection` 及 `/mall/b1f-inspection/:batchId`，MainLayout 商場管理群組新增項目

---

## [1.19.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 B2F**：串接 Ragic Sheet 3（`soutlet001/full-building-inspection/3`），置於「商場管理」群組
  - 後端 ORM 模型：`b2f_inspection_batch` / `b2f_inspection_item`（`models/b2f_inspection.py`）
  - Pydantic Schemas：`B2FInspectionBatchOut`、`B2FInspectionItemOut`、`B2FInspectionBatchKPI`、`B2FInspectionStats` 等（`schemas/b2f_inspection.py`）
  - 同步服務：`services/b2f_inspection_sync.py`（動態欄位偵測，Sheet 3 欄位自動 pivot）
  - API Router：`/api/v1/mall/b2f-inspection`（8 個端點，同 RF 規格）
  - APScheduler：每 30 分鐘自動同步 B2F 資料
  - 前端型別：`types/b2fInspection.ts`
  - 前端 API 封裝：`api/b2fInspection.ts`
  - 前端儀表板（`pages/B2FInspection/index.tsx`）：4 KPI 卡 + 完成率進度條 + 7 日異常趨勢 + 狀態圓餅 + 預警清單 + 最新場次入口
  - 前端明細頁（`pages/B2FInspection/Detail.tsx`）：場次資訊卡 + 4 欄巡檢表格 + 狀態 Tab + 30 日歷史 Drawer
  - 導覽：`NAV_PAGE.b2fInspection`，路由 `/mall/b2f-inspection` 及 `/mall/b2f-inspection/:batchId`，MainLayout 商場管理群組新增項目

---

## [1.18.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 RF**：串接 Ragic Sheet 1（`soutlet001/full-building-inspection/1`），置於「商場管理」群組
  - 後端 ORM 模型：`rf_inspection_batch` / `rf_inspection_item`（`models/rf_inspection.py`）
  - Pydantic Schemas：`RFInspectionBatchOut`、`RFInspectionItemOut`、`RFInspectionBatchKPI`、`RFInspectionStats` 等（`schemas/rf_inspection.py`）
  - 同步服務：`services/rf_inspection_sync.py`（**動態欄位偵測**：自動掃描 Ragic Row 欄位，排除場次 metadata 後全數 pivot 為巡檢項目，無需預定義欄位清單）
  - API Router：`/api/v1/mall/rf-inspection`（sync / batches / batches/{id} / batches/{id}/kpi / items / stats / items/item-history / debug/ragic-raw）
  - APScheduler：每次自動同步加入 RF 場次，log 顯示 `check_item_count`（本次偵測到欄位數）
  - 前端型別：`types/rfInspection.ts`（`RFInspectionResultStatus` + 8 個 interface）
  - 前端 API 封裝：`api/rfInspection.ts`（fetchRFBatches / fetchRFBatchDetail / fetchRFStats / syncRFFromRagic / fetchRFItemHistory）
  - 前端儀表板（`pages/RFInspection/index.tsx`）：4 KPI 卡 + 完成率進度條 + 7 日異常趨勢折線圖 + 狀態分布圓餅 + 異常/待處理 Alert 表格 + 最新場次速覽
  - 前端明細頁（`pages/RFInspection/Detail.tsx`）：場次資訊卡 + 4 欄巡檢表格 + 狀態 Tab + 項目歷史 Drawer（30 日月曆）
  - 導覽：`NAV_PAGE.rfInspection`，路由 `/mall/rf-inspection` 及 `/mall/rf-inspection/:batchId`，MainLayout 商場管理群組新增項目

---

## [1.17.0] - 2026-04-14

### Added
- **整棟工務每日巡檢 B4F**：串接 Ragic Sheet 2（`soutlet001/full-building-inspection/2`），置於「商場管理」群組

### Changed
- **B4F 架構重構（寬表格 Pivot v3）**：Ragic Sheet 2 為寬表格格式（一 Row = 一場次 + 35 設備欄位），改以 Pivot 方式同步
  - 後端 ORM：`b4f_inspection_batch`（ragic_id PK, start_time, end_time, work_hours）、`b4f_inspection_item`（`{batch_ragic_id}_{seq_no}` PK, item_name, result_status）
  - 同步服務：`CHECK_ITEMS` 清單定義 35 個設備欄位名稱，每欄 pivot 成一筆 item 記錄
  - Migration：`_migrate_b4f_flatten()` 自動識別並刪除舊版（v1 子表格 / v2 扁平）schema
  - `batch_id = ragic_id`（Ragic Row ID），移除 `batch_key`、`shift`、`zone`、`category` 等舊欄位
  - 前端 `Detail.tsx`：簡化為 4 欄（項次、巡檢項目、結果、原始值）+ 場次資訊卡（start_time/end_time/work_hours）
  - 前端 `api/b4fInspection.ts`：`fetchB4FBatchDetail` 改為 `status`/`search` 參數（移除舊 zone/category）
  - 導覽：`NAV_PAGE.b4fInspection`，路由 `/mall/b4f-inspection` 及 `/mall/b4f-inspection/:batchId`，MainLayout 商場管理群組新增 `SafetyOutlined` 選單項目

---

## [1.16.0] - 2026-04-14

### Added
- **商場週期保養表（1.2）**：仿照「飯店週期保養表」完整功能，串接 Ragic Sheet 18（`soutlet001/periodic-maintenance/18`）
  - 後端 ORM 模型：`mall_pm_batch` / `mall_pm_batch_item`（`models/mall_periodic_maintenance.py`）
  - 同步服務：`services/mall_periodic_maintenance_sync.py`（支援 A/B/C/D 四種子表格解析模式）
  - API Router：`/api/v1/mall/periodic-maintenance`（sync / batches / stats / items / task-history / debug）
  - `config.py`：新增 `RAGIC_MALL_PM_*` 四個設定常數（server/account/journal/items path）
  - 前端 API 封裝：`api/mallPeriodicMaintenance.ts`
  - 前端頁面：`pages/MallPeriodicMaintenance/index.tsx`（主管儀表板 + 批次清單 Tabs）、`Detail.tsx`（工單明細 + 進階篩選 + 歷史 Drawer）
  - 導覽：新增「商場管理」群組（`NAV_GROUP.mall`）、`NAV_PAGE.mallPeriodicMaintenance`，路由 `/mall/periodic-maintenance`

---

## [1.15.0] - 2026-04-13

### Added
- **富文字編輯器（圖文並茂）**：引入 `react-quill-new@3.8.3`（React 18 相容的 Quill.js fork），建立共用 `RichTextEditor` 元件（`frontend/src/components/Editor/RichTextEditor.tsx`）
- **圖片上傳 API**：新增後端 `POST /api/v1/upload/image` 端點，儲存至 `uploads/images/`，回傳 URL 供 Quill 插入；`GET /api/v1/upload/image/{filename}` 提供圖片服務
- **新增簽核單（Approvals/New）升級**：「說明」與「機敏資訊」欄位改為富文字編輯器，支援圖文混排
- **新增公告（Memos/New）升級**：「內文」改為富文字編輯器；新增「附件」上傳區塊，可一次選取多個檔案隨公告一起送出
- **公告附件系統**：新增 `MemoFile` ORM 表（`memo_file`）、`POST /api/v1/memos/{id}/files` 上傳端點、`GET /api/v1/memos/{id}/files/{file_id}` 下載端點；附件儲存至 `uploads/memo_files/`
- **公告詳情（Memos/Detail）升級**：附件清單顯示（檔名/大小/下載按鈕）；作者可在詳情頁追加附件；編輯 Modal 升級為富文字編輯器

---

## [1.14.6] - 2026-04-13

### Fixed
- **儀表板三處統計一致化**：KPI「已完成」、完成率、狀態分布圓餅圖，全部統一以「保養時間啟+迄均有值」為「完成」定義（含非本月項目）
  - `_calc_kpi.completed` = 全部項目中有啟+迄的數量（含非本月）
  - `_calc_kpi.completion_rate` = completed / total（全部項目）
  - `get_stats` status_distribution：非本月且有啟+迄的項目歸入「已完成」桶；非本月且無完成時間的項目不顯示
  - 前端進度條分母改為 `kpi.total`；批次清單標籤改為「已完成/全部」
  - `deriveBatchStatus` 批次完成判斷改用 `completed === total`

## [1.14.5] - 2026-04-12

### Fixed
- **週期保養表「已完成」統計錯誤修正**：`_calc_status()` 的「已完成」判斷從「只要 `end_time` 有值」改為「`start_time` AND `end_time` 均有值」，與 Detail 表格「完成」欄（`is_completed`）定義完全一致；此修正同步影響 KPI、完成率進度條、類別統計圖表、批次狀態判斷
- **`is_completed` DB 回填**：`migration` 函式加入 UPDATE 語句，啟動時自動將舊資料中「啟+迄均非空但 `is_completed=0`」的記錄補正為 `is_completed=1`
- **`_item_to_out` 動態計算**：`is_completed` 不再依賴 DB 存的舊值，改為每次動態從 `start_time AND end_time` 推導，確保 API 回傳值永遠正確

---

## [1.14.4] - 2026-04-12

### Changed
- **週期保養表 — Portal 改為純唯讀視圖**：移除工單回填 Drawer、編輯按鈕、PATCH endpoint；資料全部由 Ragic 同步提供，Portal 不再有任何覆寫能力
- **狀態判斷邏輯明確化**（純 Ragic 欄位，無 Portal 覆寫）：
  1. 非本月 — `exec_months_json` 有值且當月不在清單
  2. 已完成 — `保養時間迄`（end_time）有值
  3. 進行中 — `保養時間啟`（start_time）有值但無迄
  4. 逾期   — `排定日期` 有值且已過今天
  5. 已排定 — `排定日期` 有值
  6. 未排定 — 以上皆無
- **同步服務移除 portal_edited_at 保護**：每次同步全部以 Ragic 資料為準
- **is_completed 改為純唯讀顯示欄位**（sync 自動計算：start_time AND end_time 均有值），不再允許 Portal 手動設定
- 停用 `PMItemUpdate` Schema 及 `updatePMItem` API 函式

---

## [1.14.3] - 2026-04-12

### Added
- **週期保養表 — `is_completed` 完成標記欄位**：`pm_batch_item` 新增 `is_completed BOOLEAN DEFAULT 0` 欄位；Ragic 同步時自動計算（保養時間啟 + 保養時間迄均有值 → `True`）；Portal 回填 Drawer 亦可手動切換完成/未完成；表格新增「完成」圖示欄
- **DB 輕量移轉**：`main.py` 啟動時透過 `ALTER TABLE ADD COLUMN` 安全補丁現有 SQLite 表格（若欄位不存在才執行）
- **狀態計算改版**：`_calc_status()` 改以 `is_completed` 欄位判斷已完成狀態（兼容舊資料：`end_time` 有值亦視為完成）
- **`PMItemUpdate` Schema** 新增 `is_completed` 可選欄位；前端 `PMItem` 型別亦同步

---

## [1.14.2] - 2026-04-12

### Fixed
- **週期保養表 sync 根本修正**：子表格 key `_subtable_1011397` 以底線開頭，舊程式碼所有解析路徑均以 `startswith("_")` 跳過 → 新增方式D 專門處理 `_subtable_*` key，正確提取 `{"1":{row},"2":{row}...}` 子列；同步診斷 log 亦修正，不再略過 `_` 前綴 key

### Added
- **週期保養表明細 — 多重狀態篩選**：篩選列新增「狀態篩選（可複選）」Select，支援同時選取非本月、未排定等多個狀態；獨立「有排定日期」Checkbox 供跨狀態 cross-filter（例：非本月 + 有排定日期）；Tabs 新增「非本月」快速切換頁；多選啟用時顯示「複選篩選中」虛擬 Tab
- **週期保養表明細 — 保養項目歷史 Drawer**：點擊保養項目名稱 → 跨批次查詢近 12 個月執行歷史；12 格月曆（已完成=綠/異常=橙/逾期=紅/當月未排=黃/無批次=灰）；KPI 卡（完成次數/完成率/異常次數）；點選月格展開該月執行詳情（人員/時間/備註/狀態）
- **後端新端點** `GET /api/v1/periodic-maintenance/items/task-history?task_name=X&months=12`：依項目名稱跨批次查詢執行歷史，回傳月曆摘要 + 統計
- **前端型別** `PMItemHistorySummary`、`PMTaskHistoryStats`、`PMTaskHistory`；API 函式 `fetchPMTaskHistory`

---

## [1.14.1] - 2026-04-12

### Fixed
- **週期保養表 sync 重大修正**：Sheet 8 結構為「批次記錄含嵌入子表格列」，而非平表 item 列表；重寫 `sync_items_from_ragic()` 解析數字 key 子列（"1","2","3"…），item.ragic_id 改為 `"{batch_id}_{row_key}"` 格式（如 "5_1"）；移除舊 `_get_parent_id()` 函式；新增 `CK_NOTE="備註"` 欄位映射；舊格式空白記錄自動清除
- 後端 debug 端點：`GET /api/v1/periodic-maintenance/debug/ragic-raw` 方便確認 Ragic 回傳 key 結構

---

## [1.14.0] - 2026-04-12

### Added
- **週期保養表** 功能全面上線（Phase 1 + 2 + 3）
  - 後端 DB 模型：`pm_batch`（批次主表）+ `pm_batch_item`（項目明細），含 `portal_edited_at` 同步保護欄位
  - 後端 Pydantic Schemas：`PMBatchOut`, `PMItemOut`, `PMBatchKPI`, `PMBatchDetail`, `PMStats`, `PMItemUpdate`
  - 後端 Router（`/api/v1/periodic-maintenance`）：POST /sync、GET /batches、GET /batches/:id、GET /batches/:id/kpi、GET /items、GET /stats、PATCH /items/:id
  - 後端 `periodic_maintenance_sync.py`：Ragic ap12 Sheet 6（批次）+ Sheet 8（項目）同步；執行月份解析（"2月 5月 8月 11月" → [2,5,8,11]）；portal_edited_at 同步保護
  - 後端 `config.py` 新增 `RAGIC_PM_SERVER_URL`、`RAGIC_PM_JOURNAL_PATH`、`RAGIC_PM_ITEMS_PATH` 設定
  - `main.py` 整合週期保養自動同步（每 30 分鐘）
  - 前端型別定義：`periodicMaintenance.ts`（PMBatch, PMItem, PMItemStatus, PMBatchKPI, PMBatchDetail, PMStats, PMItemUpdate）
  - 前端 API 封裝：`periodicMaintenance.ts`（fetchPMBatches, fetchPMBatchDetail, fetchPMStats, updatePMItem, syncPMFromRagic）
  - 前端主頁 `pages/PeriodicMaintenance/index.tsx`：主管儀表板（KPI 4卡、完成率進度條、類別 BarChart、狀態 PieChart、逾期 Top10、本週即將到期）+ 批次清單 Tab
  - 前端明細頁 `pages/PeriodicMaintenance/Detail.tsx`：工單式頁面，KPI 6卡 + 完成率進度條、狀態 Tab 篩選（7 個）、類別/關鍵字篩選、色碼表格（未排定紅底、非本月灰底）、600px 右側 Drawer 回填（排程 + 執行記錄 + 異常旗標）
  - 前端路由：`/hotel/periodic-maintenance`、`/hotel/periodic-maintenance/:batchId`
  - Sidebar 新增「週期保養表」選單項目
  - `navLabels.ts` 新增 `periodicMaintenance` 常數

---

## [1.13.0] - 2026-04-11

### Added
- 「保養統計」Tab（Tab 5）：完整 Phase 1 + Phase 2 + Phase 3 統計分析功能
  - **Phase 1 — 完成率趨勢 + 高風險房間**
    - 近12月完成率 × 異常率雙軸折線趨勢圖（Recharts LineChart 雙 Y 軸）
    - KPI 六卡：當月完成率、12月均值趨勢、當月異常率、連續未保養房間數、全正常房間數、重複異常房間數
    - 高風險房間三子 Tab：連續未保養（≥2月）/ 重複異常（同項目連續2月X）/ 全正常（最近3筆均全V）
  - **Phase 2 — 異常項目分析**
    - 12 個檢查項目累計 X 次數水平橫條圖，依嚴重度色彩分層（紅/橙/黃/藍）
    - 右側明細排行表：項目名稱 + X次數 + 異常率%
  - **Phase 3 — 樓層分析 + 月份對比**
    - 各樓層當月完成率 vs 全期異常次數雙柱圖
    - 當月 / 上月 / 去年同月三期對比圖 + 明細列
- 後端新增 `GET /api/v1/room-maintenance-detail/maintenance-stats` 端點
  - 一次回傳所有統計資料（monthly_trend / check_item_stats / floor_stats / risk_rooms / comparison / kpi）
  - 支援 `months` 參數（1~36，預設 12）
- 前端新增 TypeScript Interface：`MaintenanceStatsResponse`、`MonthlyTrend`、`CheckItemStat`、`FloorStat`、`ConsecutiveMissedRoom`、`RepeatedAbnormalRoom`、`FullyOkRoom`、`MonthComparison`
- 前端新增 API 函式：`fetchMaintenanceStats(months)`
- 產出設計規格書：`保養統計功能設計規格書_v1.13.0.docx`

---

## [1.12.0] - 2026-04-11

### Added
- 導覽文字 SSOT：新增 `frontend/src/constants/navLabels.ts` 作為 Menu / Breadcrumb / 頁面 Title 的唯一真相來源
  - `SITE_TITLE`、`NAV_GROUP`、`NAV_PAGE` 三個常數物件涵蓋全站導覽文字
  - 修改任一文字只需改 `navLabels.ts`，三處自動同步，不需分別修改
  - `MainLayout.tsx` 已接入：Sidebar 標題、所有選單群組與頁面文字
  - `RoomMaintenanceDetail/index.tsx` 已接入：Breadcrumb 與頁面 Title
  - `docs/TECH_SPEC.md` 新增「導覽文字維護指南」章節，說明修改方法與維護紀錄

### Changed
- 「客房保養明細」顯示名稱 → 「保養管理」（路由 `/hotel/room-maintenance-detail` 不變）

---

## [1.11.0] - 2026-04-11

### Added
- 人員工時表統計：新增月份選擇器（YYYY/MM），可切換任意月份重新計算所有統計數字
  - 預設顯示最新月，選單由新到舊排列，最新月加「（最新）」標示
  - KPI 6 卡、排名圖、異常分析均依選定月份即時更新
  - 「較上月」卡片動態顯示上期月份名稱與上期工時
  - 「回到最新月」快捷按鈕（選非最新月時才顯示）
  - 趨勢圖保留完整12月，選定月柱子以深藍色（#1B3A5C）高亮，其他月淡藍

---

## [1.10.0] - 2026-04-11

### Fixed
- 人員工時表：修正 `useMemo` 在 early return 後呼叫違反 React Hooks 規則，導致 Tab 空白畫面
- 人員工時表：恢復原版 pivot 表格 `StaffHoursTab`（不可修改）

### Added
- 新增 Tab 4「人員工時表統計」（獨立元件 `StaffHoursDashboard`）
  - 主管 KPI 總覽：本月總工時 / 較上月% / 本月人均 / 最高人員 / 最低人員 / 異常波動人數
  - 趨勢圖：近12月柱狀圖 + 橘虛線（月均） / 本月人員橫向排名圖
  - 異常分析區：偏高+20%=紅 / 偏低-20%=橘 / 連續3月偏高=黃 / 趨近0=灰
  - 強化明細表：即時搜尋人員 / 三段排序（合計/本月/波動） / 匯出 CSV
  - 個人分析 Drawer：折線圖（個人 vs 全員均） + 月份格子 + 4 KPI
- 兩個工時 Tab 共用同一份 API 資料，切換任一個均自動首次載入

---

## [1.9.0] - 2026-04-10

### Added
- 人員工時表：新增「主管總覽」KPI 區（6 張卡）
  - 本月總工時、較上月環比 %、本月人均工時、本月最高/最低工時人員、異常波動人數
- 人員工時表：新增「趨勢分析圖」雙欄
  - A. 近 12 個月柱狀圖 + 橘色虛線（12 月平均）
  - B. 本月人員橫向排名長條圖（由低到高）
- 人員工時表：新增「異常分析區」
  - 工時異常偏高（+20%）→ 紅色、偏低（−20%）→ 橘色、連續3月偏高 → 黃色、趨近0 → 灰色
  - 全員無異常時顯示綠色 Alert
- 人員工時表：明細表加強功能
  - 搜尋人員欄位（即時篩選）
  - 排序切換（依合計 / 本月 / 波動幅度）
  - 匯出 CSV 按鈕（UTF-8 BOM，可直接用 Excel 開啟）
  - 人員欄位可點擊，開啟「個人工時分析 Drawer」
- 人員工時表：新增「個人工時分析 Drawer」（600px）
  - 4 張 KPI 卡（12月合計、月平均、最高月份、最低月份）
  - 近 12 月折線圖（個人工時 vs 全員月均，含圖例）
  - 月份格子圖（工時 vs 月均比率著色）
- 前端新增 recharts import（BarChart/LineChart/ResponsiveContainer/ReferenceLine）
- 前端新增 Segmented 元件（排序切換）

---

## [1.8.0] - 2026-04-10

### Added
- 客房保養明細：新增 `GET /api/v1/room-maintenance-detail/staff-hours?months=12` 端點
  - 依人員 × 月份 pivot 聚合，分鐘自動換算為小時（四捨五入兩位）
  - 回傳每人月份工時、每月全員合計、全期總計
- 客房保養明細：新增 Tab 3「人員工時表」pivot table
  - 欄：人員（固定左側）+ 近 12 個月 + 合計（固定右側）
  - 底部藍底「月合計」彙總列
  - 全期總計 Tag 顯示於右上角
  - 切換至 Tab 時自動載入（首次），可手動「重新載入」
- 前端型別新增 `StaffHoursRow`、`StaffHoursResponse`
- 前端 API 新增 `fetchStaffHours(months, date_from?, date_to?)`

---

## [1.7.0] - 2026-04-10

### Added
- 客房保養明細：`RoomHistoryDrawer` 月曆格子可點擊，展開顯示該月保養明細
  - 點擊月份格 → 在「保養記錄」上方插入該月明細卡片（保養日期 / 人員 / 工時 + 12 項 X/V 標籤）
  - 再次點擊同一月份或按「關閉」可收合
  - 月曆圖例右側新增提示文字「點擊月份可查看保養明細」

---

## [1.6.0] - 2026-04-10

### Added
- 客房保養明細：`GET /api/v1/room-maintenance-detail/room-history/{room_no}?months=12` 端點
  - 回傳近 N 個月月曆摘要（每月 serviced/record_count/work_hours_sum/latest_date/latest_staff/checks）
  - 回傳全部保養記錄（時序降冪）
  - Stats：total_records、last_serviced、consecutive_missed（連續未保養月數）、serviced_months
- 客房保養明細：前端 `RoomHistoryDrawer`（640px 右側抽屜）
  - 連續未保養 ≥2 月→紅色 Alert，=1 月→橘色 Warning
  - 3 格 KPI（保養記錄總數 / 近 12 月保養次數 / 連續未保養月數）
  - 近 12 個月保養月曆格子（綠=已保養、紅=未保養、灰=當月）
  - 完整保養記錄時間軸（紅點=有異常、綠點=全 OK，展開顯示異常項目 Tag）
- 客房保養明細：總表（Tab 1）與明細清單（Tab 2）房號欄位皆可點擊，開啟房間歷史追蹤 Drawer
- 前端型別新增 `MonthlyMaintenanceSummary`、`RoomHistoryStats`、`RoomHistoryResponse`
- 前端 API 新增 `fetchRoomHistory(room_no, months)`

---

## [1.5.0] - 2026-04-10

### Added
- 客房保養明細：新增 `Room` SQLAlchemy 主檔模型（`rooms` 表）及自動 seed（170 間，5F–10F）
- 客房保養明細：`GET /summary` 端點改支援日期區間（`date_from` / `date_to`）並整合全房間清單
- 客房保養明細：`/summary` 新增工時數合計（`work_hours_total`）、未保養房間數（`unserviced_count`）統計
- 客房保養明細：`GET /` 端點新增 `date_from` / `date_to` 篩選參數
- 客房保養明細：前端頁面全面重設計 — Tab 1「保養總表」（主管執行視圖）+ Tab 2「明細清單」
- 客房保養明細：Tab 1 日期區間篩選 → KPI 四卡（保養記錄總數/異常項次總數/全項目正常房間數/工時數）
- 客房保養明細：「異常項次總數」KPI 卡可點擊，自動篩選表格僅顯示有異常的房間
- 客房保養明細：「未保養房號」按鈕，切換顯示日期區間內未保養房間（灰底）
- 客房保養明細：總表依樓層 filter + 房號排序，未保養灰底、有異常淡紅底

---

## [1.4.0] - 2026-04-10

### Added
- 客房保養明細：新增 `RoomMaintenanceDetailRecord` SQLAlchemy 模型（`room_maintenance_detail_records` 表）
- 客房保養明細：Ragic → SQLite 同步服務（`room_maintenance_detail_sync.py`）— 指向 ap12.ragic.com/soutlet001/report2/2
- 客房保養明細：`GET /api/v1/room-maintenance-detail/` 列表端點（支援房號/人員/日期篩選+分頁）
- 客房保養明細：`GET /api/v1/room-maintenance-detail/summary` 總表端點（依日期×房號聚合，含 X/V 統計）
- 客房保養明細：`POST /api/v1/room-maintenance-detail/sync` 手動同步端點
- 客房保養明細：前端頁面 `pages/RoomMaintenanceDetail/index.tsx`（列表 + 總表 Button/Modal）
- 客房保養明細：Sidebar「飯店管理」新增「客房保養明細」選單項目
- 客房保養明細：路由 `/hotel/room-maintenance-detail`
- config：新增 `RAGIC_ROOM_DETAIL_SERVER_URL`、`RAGIC_ROOM_DETAIL_ACCOUNT`、`RAGIC_ROOM_DETAIL_PATH`
- AutoSync：新增客房保養明細同步至每 30 分鐘自動排程

---

## [1.3.0] - 2026-04-09

### Added
- Dashboard：新增 `GET /api/v1/dashboard/kpi` 聚合端點（客房保養 + 庫存 + 同步狀態）
- Dashboard：KPI 卡片列（完成率 / 未完成項目 / 庫存品項數 / 同步健康度）
- Dashboard：客房保養工作狀態 Donut 圓餅圖（recharts）
- Dashboard：庫存類別分析 Bar 圖（前 8 大類）
- Dashboard：重點關注房間表（incomplete > 0，依未完成數排序）
- Dashboard：近期同步紀錄表（最近 5 筆，含狀態 Badge、相對時間）
- Dashboard：整合重新整理按鈕 + 資料更新時間顯示

---

## [1.2.0] - 2026-04-09

### Added
- 倉庫庫存：新增 `InventoryRecord` SQLAlchemy 模型（`inventory_records` 表）
- 倉庫庫存：Ragic → SQLite 同步服務（`inventory_sync.py`）— 中文 key 解析
- 倉庫庫存：`GET /api/v1/inventory/` 列表、`/stats` KPI、`/sync` 手動同步端點
- 倉庫庫存：前端頁面 `pages/Inventory/index.tsx`（KPI 卡 + 篩選 + 唯讀表格）
- 倉庫庫存：Sidebar 新增「倉庫管理」群組及「倉庫庫存」選單項目
- 倉庫庫存：路由 `/warehouse/inventory`
- AutoSync：同時涵蓋客房保養與倉庫庫存兩個模組
- config：新增 `RAGIC_INVENTORY_PATH = ragicinventory/20008`

---

## [1.1.0] - 2026-04-09

### Added
- 客房保養：Ragic → SQLite 同步架構（`room_maintenance_sync.py`）
- 客房保養：`POST /sync` 手動同步端點
- 客房保養：APScheduler 每 30 分鐘自動同步
- 客房保養：管理圖表儀表板（recharts）— 完成率、狀態分佈、未完成柱狀圖、檢查頻率
- 客房保養：未檢查項目附表（反向顯示缺漏項目，橙紅底色）
- 系統設定：使用者管理、角色管理、Ragic 連線管理路由補齊

### Fixed
- JWT `create_access_token` 傳入 dict 導致 `sub` 字串化 → 401 的 bug
- Ragic 欄位 key 格式（`"1000006房號"` → 實際為純中文 `"房號"`）解析錯誤

## [1.0.0] - 2026-04-08

### Added
- FastAPI 後端：auth、users、tenants、ragic、dashboard、room_maintenance routers
- React 前端：Login、Dashboard、客房保養列表頁
- SQLAlchemy 同步模式（修正自 aiosqlite）
- JWT 認證（`decode_token` / `verify_token` 別名相容）
- Ragic API Adapter（修正 double base64 encoding bug）
