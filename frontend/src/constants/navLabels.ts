/**
 * 導覽文字常數 — 唯一真相來源 (Single Source of Truth)
 *
 * ⚠️  修改規則
 *   - 只改 label 值，絕對不能改 key、route、path 等路由相關欄位
 *   - 改完後 Menu、Breadcrumb、頁面 Title 會自動同步，不需分別修改
 *
 * 對應說明
 *   label  → 使用者看到的顯示文字（可自由修改）
 *   route  → React Router path，對應 router/index.tsx（不可修改）
 *   menuKey → Ant Design Menu key，對應 MainLayout menuItems（不可修改）
 *
 * 維護紀錄（請每次修改後補記）
 *   2026-04-11  初始建立；「客房保養明細」→「保養管理」
 *   2026-04-12  新增 periodicMaintenance（週期保養表）
 *   2026-04-13  新增 approvals（簽核管理）
 *   2026-04-13  新增 memos（公告牆）
 *   2026-04-14  新增 mall（商場管理群組）+ mallPeriodicMaintenance（商場週期保養表）
 *   2026-04-14  新增 b4fInspection（整棟工務每日巡檢 B4F）
 *   2026-04-14  新增 rfInspection（整棟工務每日巡檢 RF）
 *   2026-04-14  新增 b2fInspection（整棟工務每日巡檢 B2F）
 *   2026-04-14  新增 b1fInspection（整棟工務每日巡檢 B1F）
 *   2026-04-14  新增 mallDashboard（商場管理統計 Dashboard）
 *   2026-04-14  新增 security（保全管理群組）+ securityDashboard + 7 張保全巡檢 Sheet
 *   2026-04-15  新增 calendar（行事曆群組）—— 超級行事曆 Command Calendar
 *   2026-04-15  新增 mall_facility_inspection（春大直商場工務巡檢）+ 5 個樓層巡檢頁
 *   2026-04-15  新增 full_building_inspection（整棟巡檢）+ 4 個樓層巡檢頁（RF/B4F/B2F/B1F）
 *   2026-04-15  新增 luqun_repair（商場工務報修）完整模組 + Dashboard
 *   2026-04-15  新增 dazhi_repair（大直工務部）完整模組 + Dashboard
 *   2026-04-19  新增 budget（預算管理）Phase 1：Dashboard / Plans / Transactions / Masters / Reports
 *   2026-04-23  新增 workCategoryAnalysis（★工項類別分析）掛於 luqun_repair + dazhi_repair 下
 *   2026-04-23  新增 execDashboard（◆ 董事長簡報 Dashboard）黑金風格獨立新功能，route /exec-dashboard
 *   2026-04-24  新增 ihgRoomMaintenance（IHG客房保養）年度矩陣保養計畫，route /hotel/ihg-room-maintenance
 *   2026-04-28  新增 menuConfig（選單管理）動態改名＋排序＋5筆歷史，route /settings/menu-config
 *   2026-04-28  整合商場管理：mallDashboard 改名「商場週期保養」，將 6 個子頁面巡檢紀錄合併為 Tab
 *   2026-04-28  整合整棟巡檢：fullBuildingDashboard 改名「整棟巡檢」，移至商場管理群組下，RF/B4F/B2F/B1F 合併為 Tab
 *   2026-04-28  整合春大直商場工務巡檢：mallFacilityDashboard 改名「春大直工務巡檢」，移至商場管理群組下，5 個樓層巡檢紀錄合併為 Tab
 *   2026-04-28  /exec-dashboard 與 /work-category-analysis 從 luqun-repair / dazhi-repair 子層提升為獨立一階（Dashboard 正後方）
 *   2026-04-28  新增 fullBuildingMaintenance（全棟例行維護）Ragic Sheet 21，route /mall/full-building-maintenance
 *   2026-04-28  新增 mallPmGroup（商場例行維護）L2 群組，整合 mallDashboard + mallPeriodicMaintenance + fullBuildingMaintenance 為三層 menu
 *   2026-04-28  修正 applyMenuConfig 三層 merge 邏輯；DB seed 隱藏 custom_1777348120465；MenuConfig 設定頁支援三層 L3
 *   2026-04-28  新增 mallMgmtDashboard（商場管理 Dashboard）整合 5 來源總覽，route /mall/overview
 *   2026-04-29  新增 hotelDailyInspection（飯店每日巡檢）5 張 Sheet（RF/4F-10F/4F/2F/1F），route /hotel/daily-inspection
 *   2026-04-30  新增 hotelMeterReadings（每日數值登錄表）4 張 Sheet（全棟電錶/商場空調箱電錶/專櫃電錶/專櫃水錶），route /hotel/daily-meter-readings
 *   2026-04-30  整合保全巡檢：security 從群組（8 items）→ 單一入口 /security/dashboard；各 Sheet 改為頁面內外層 TAB；NAV_GROUP.security 改名「保全巡檢」
 *   2026-04-30  新增 hotelMgmtDashboard（★飯店管理 Dashboard）整合 6 來源總覽，route /hotel/overview
 *   2026-05-03  新增 decisionCockpit（決策駕駛艙）高階主管決策入口，整合三大模組精華，route /decision-cockpit
 *   2026-05-03  新增 wiki（知識庫）LLM Wiki 知識庫，含員工 SOP + 開發者 Wiki + AI 問答，route /wiki
 *   2026-05-04  新增 employeeManualExport（員工操作手冊匯出）系統設定群組，route /settings/employee-manual-export
 *   2026-05-07  新增 execWorkDashboard（集團工務決策駕駛艙）以工務決策視角為主，route /exec-work-dashboard
 *   2026-05-10  新增 knowledgeGraph（專案知識圖譜）graphify 整合，route /settings/knowledge-graph
 *   2026-05-13  新增 purchaseReport（請購單報表）核准請購單月報表，route /purchase-report/monthly
 *   2026-05-17  新增 staticPages（靜態頁面）docs/ 目錄 iframe 瀏覽器，route /settings/static-pages
 *   2026-05-19  新增 ragicFieldAudit（Ragic 欄位比對）欄位稽核工具，route /settings/ragic-field-audit
 *   2026-05-24  新增 pptExport（飯店 Dashboard PPT 匯出設定）Section Registry 架構，route /ppt-export
 *   2026-05-27  新增 contract（合約管理）Phase 1.3 Portal 集成，route /contract + /contract/vendors + /contract/settings
 *   2026-06-29  新增 hotelCalendar（飯店行事曆）+ mallCalendar（商場行事曆），route /hotel/calendar + /mall/calendar
 *   2026-07-03  新增 tutorialVideos（影音教學）一階選單，本地模組不對接 Ragic，route /tutorial-videos
 *   2026-08-11  新增 basicSettings（基本設定）站台名稱維護，route /settings/basic；同時移除 SITE_TITLE 常數
 */

// ── 系統標題 ──────────────────────────────────────────────────────────────────
// ⚠️ 系統標題已改為執行期設定（各 Server 品牌名稱可不同），請改用：
//      import { getSiteTitle } from '@/config/siteConfig'
//    設定值存在後端 system_settings 資料表（key = site.brand），
//    由「系統設定 → 基本設定」頁面維護。原本的 SITE_TITLE 常數已移除。

// ── 一級選單（群組） ──────────────────────────────────────────────────────────
export const NAV_GROUP = {
  dashboard:  'Dashboard',
  // 2026-08-14：原本的頂層「班表」群組已移除，拆為飯店管理底下的「飯店班表」
  // 與商場管理底下的「商場班表」兩個 L2 群組（見下方 hotelSchedule / mallSchedule）。
  contract:   '合約管理',           // ← 新增：合約管理（預算之前）
  budget:     '預算管理',         // ← 新增：預算管理（在 dashboard 之後、行事曆之前）
  calendar:   '行事曆',           // ← 新增：Command Calendar（在 dashboard 之後、hotel 之前）
  hotel:      '飯店管理',
  hotelSchedule:            '飯店班表',       // ← L2 群組：飯店管理底下（2026-08-14 由頂層「班表」搬入）
  mall:                     '商場管理',
  mallSchedule:             '商場班表',       // ← L2 群組：商場管理底下（2026-08-14 新增）
  mallPmGroup:              '商場例行維護',   // ← L2 群組：商場例行維護 + 全棟例行維護
  luqun_repair:             '商場工務報修',
  dazhi_repair:             '飯店工務報修',
  mall_facility_inspection:  '商場工務巡檢',
  full_building_inspection:  '整棟巡檢',
  security:                  '保全巡檢',
  warehouse:  '倉庫管理',
  reports:    '報表',
  approvals:  '簽核管理',
  memos:      '公告牆',
  wiki:             '知識庫',
  audit:            '稽核日誌',
  settings:         '系統設定',
  purchaseReport:         '請購單報表',        // ← 核准請購單月報表（財務/採購管理）
  claimReport:            '請款單報表',        // ← 核准請款單月報表（財務/採購管理）
  nichiyoPurchaseReport:  '日曜請購月報表',    // ← 日曜核准請購單月報表
  nichiyoClaimReport:     '日曜請款月報表',    // ← 日曜核准請款單月報表
  cyclePurchase:          '週採',              // ← 新增：週期採購管理（2026-07-10，獨立資料庫 cycle-purchase.db）
  opera:                  '營運分析',          // ← 新增：OPERA 營運分析（2026-08-04，檔案上傳型模組，非 Ragic 同步）
  jinxu:                  '金旭分析',          // ← 新增：金旭 PMS 分析（2026-08-05，第二個檔案上傳型模組，與 /opera 完全獨立）
  realtime:               '即時營運',          // ← 新增：OPERA Cloud API 直連（2026-08-06）。與 /opera/*（上傳 TXT）刻意分開：資料來源與時點不同
  ota:                    '口碑分析',          // ← 新增：OTA 評論分析（2026-08-21，外部網站擷取型）。刻意不併入「營運分析」：那組是 PMS 營收敏感權限，評論是公開資料
} as const

// ── 二級選單（頁面） ──────────────────────────────────────────────────────────
export const NAV_PAGE = {
  // 預算管理
  budgetDashboard:       '預算總覽 Dashboard',
  budgetPlans:           '預算主表',
  budgetTransactions:    '費用交易明細',
  budgetReport:          '預算比較報表',
  budgetDeptMaster:      '部門主檔',
  budgetAccountMaster:   '會計科目主檔',
  budgetItemMaster:      '預算項目主檔',
  budgetMappings:        '對照規則維護',

  // 行事曆
  calendarMain:          '行事曆總覽',    // 超級行事曆主頁
  hotelCalendar:         '飯店行事曆',   // ← 飯店行事曆（/hotel/calendar）
  mallCalendar:          '商場行事曆',   // ← 商場行事曆（/mall/calendar）

  // 飯店管理
  hotelMgmtDashboard:     '★ 飯店管理 Dashboard',  // ← 新增：6 來源整合總覽
  hotelDailyInspection:   '飯店每日巡檢',
  hotelMeterReadings:     '每日數值登錄表',
  roomMaintenance:        '客房保養',
  roomMaintenanceDetail:  '※1.1飯店客房保養管理',       // ← 原「客房保養明細」
  periodicMaintenance:    '飯店例行維護',
  ihgRoomMaintenance:     '2. IHG客房保養',             // ← 新增：年度矩陣保養
  otherTasks:             '主管交辦／緊急事件',          // ← 新增：主管交辦 + 緊急事件 2 TAB
  hotelRoutineMaintenance: '1.2 飯店例行維護',           // ← Sheet 11 平表版（含維修工時）
  repairs:                '報修管理',

  // 商場管理
  mallMgmtDashboard:          '商場管理 Dashboard',  // ← 新增：5 來源整合總覽
  mallDashboard:              '商場週期保養',
  mallPeriodicMaintenance:    '商場例行維護',
  fullBuildingMaintenance:    '全棟例行維護',   // ← 新增：Ragic Sheet 21
  b4fInspection:           '工務巡檢 - B4F',
  rfInspection:            '工務巡檢 - RF',
  b2fInspection:           '工務巡檢 - B2F',
  b1fInspection:           '工務巡檢 - B1F', //整棟工務每日巡檢

  // 商場工務報修
  luqunRepairDashboard:    '商場工務報修 Dashboard',

  // 飯店工務報修
  dazhiRepairDashboard:    '飯店工務報修 Dashboard',

  // ★工項類別分析
  workCategoryAnalysis:    '★工項類別分析',

  // 決策駕駛艙（高階主管決策入口，整合三大模組精華）
  decisionCockpit:         '決策駕駛艙',

  // 高階主管 Dashboard（新功能，獨立路由）
  execDashboard:           '高階主管 Dashboard',

  // 集團工務決策駕駛艙（工務決策視角，獨立路由）
  execWorkDashboard:       '集團決策 Dashboard',

  // 商場工務巡檢
  mallFacilityDashboard:   '商場工務巡檢',
  mallFacility4F:          '工務巡檢 - 4F',
  mallFacility3F:          '工務巡檢 - 3F',
  mallFacility1F3F:        '工務巡檢 - 1F ~ 3F',
  mallFacility1F:          '工務巡檢 - 1F',
  mallFacilityB1FB4F:      '工務巡檢 - B1F ~ B4F',

  // 整棟巡檢
  fullBuildingDashboard:   '整棟巡檢',
  fullBuildingRF:          '整棟巡檢 - RF',
  fullBuildingB4F:         '整棟巡檢 - B4F',
  fullBuildingB2F:         '整棟巡檢 - B2F',
  fullBuildingB1F:         '整棟巡檢 - B1F',

  // 保全管理
  securityDashboard:     '保全巡檢Dashboard',
  securityB1fB4f:        'B1F~B4F',
  security1f3f:          '1F ~ 3F (夜間)', //保全巡檢
  security5f10f:         '5F ~ 10F (夜間)',
  security4f:            '4F (夜間)',
  security1fHotel:       '1F (飯店大廳)',
  security1fClose:       '1F 閉店巡檢',
  security1fOpen:        '1F 開店準備',

  // 倉庫管理
  inventory:             '倉庫庫存',

  // 報表
  reportsGenerate:       '產生報表',
  reportsHistory:        '歷史報表',

  // 簽核管理
  approvalsList:         '簽核清單',
  approvalsNew:          '新增簽核單',

  // 公告牆
  memosList:             '公告清單',
  memosNew:              '新增公告',

  // 知識庫
  wikiMain:              '知識庫',

  // 系統設定
  basicSettings:            '基本設定',        // ← 新增：站台名稱等基本設定（2026-08-11）
  usersManage:              '使用者管理',
  rolesManage:              '角色管理',
  ragicConnections:         'Ragic 連線',
  ragicAppDirectory:        'Ragic 對應表',
  companyDepartments:       '公司/部門管理',   // ← route /settings/company-departments（2026-08-17 新增）
  ragicFieldAudit:          'Ragic 欄位比對',  // ← 新增：Ragic 與 Portal 欄位稽核
  menuConfig:               '選單管理',
  employeeManualExport:     '員工操作手冊匯出',
  knowledgeGraph:           '專案知識圖譜',
  staticPages:              '靜態頁面',
  repairUnfinishedReport:   '報修未完成報表',
  usageMonitor:             '使用監控',             // ← 2026-05-23 API 存取日誌統計

  // 請購單報表
  purchaseReportMonthly:    '核准請購單月報表',  // ← 品項級月報表，route /purchase-report/monthly


  // 請款單報表
  claimReportMonthly:       '核准請款單月報表',  // ← 品項級月報表，route /claim-report/monthly

  // 日曜請購月報表
  nichiyoPurchaseReportMonthly: '日曜核准請購單月報表',  // ← route /nichiyo-purchase-report/monthly

  // 日曜請款月報表
  nichiyoClaimReportMonthly: '日曜核准請款單月報表',  // ← route /nichiyo-claim-report/monthly

  // 飯店班表（本地 SQLite 模組，飯店管理 → 飯店班表）
  // ⚠️ 這裡的顯示名稱必須與 role_permissions.py PERMISSION_DEFINITIONS 的 label 一致，
  //    否則管理員在「權限設定」看到的名稱會與側邊欄不同（CLAUDE.md §3）。
  hotelScheduleOverview:     '班表總覽',        // ← route /hotel/schedule
  hotelScheduleCalendar:     '月曆式班表',       // ← route /hotel/schedule/calendar
  hotelScheduleImport:       '匯入班表',         // ← route /hotel/schedule/import
  hotelScheduleStaff:        '人員管理',         // ← route /hotel/schedule/staff
  hotelScheduleShifts:       '班別管理',         // ← route /hotel/schedule/shifts
  hotelScheduleDepartments:  '部門管理',         // ← route /hotel/schedule/departments
  hotelScheduleManual:       '操作手冊',         // ← route /hotel/schedule/manual

  // 商場班表（本地 SQLite 模組，商場管理 → 商場班表）
  mallScheduleOverview:      '班表總覽',        // ← route /mall/schedule
  mallScheduleCalendar:      '月曆式班表',       // ← route /mall/schedule/calendar
  mallScheduleImport:        '匯入班表',         // ← route /mall/schedule/import
  mallScheduleStaff:         '人員管理',         // ← route /mall/schedule/staff
  mallScheduleShifts:        '班別管理',         // ← route /mall/schedule/shifts
  mallScheduleDepartments:   '部門管理',         // ← route /mall/schedule/departments
  mallScheduleManual:        '操作手冊',         // ← route /mall/schedule/manual

  // 合約管理
  contractList:         '合約清單',             // ← route /contract
  contractDashboard:    'Dashboard',            // ← route /contract/dashboard
  contractImport:       '資料導入',             // ← route /contract/import
  contractVendors:      '廠商管理',             // ← route /contract/vendors
  contractSettings:     '合約設定',             // ← route /contract/settings
  contractExpiring:     '到期預警',             // ← route /contract/expiring (Phase 2)
  contractClaims:       '請款管理',             // ← route /contract/claims   (Phase 2)
  contractRenewals:     '續約管理',             // ← route /contract/renewals (Phase 3)
  contractCalendar:     '合約行事曆',           // ← route /contract/calendar  (G2)
  contractCompare:      '合約比較',             // ← route /contract/compare   (K5)
  contractManual:       '使用手冊',             // ← route /contract/manual（2026-08-14 新增，共用 contract_view 權限）

  // PPT 匯出設定（飯店 Dashboard，全公司共用設定，一階選單）
  pptExport:            '飯店 Dashboard PPT 匯出設定',  // ← route /ppt-export

  // AI 助理
  aiWorkorderAssistant: 'AI 工單查詢助理',               // ← route /ai-assistant

  // 影音教學（本地模組，不對接 Ragic）
  tutorialVideos:       '影音教學',                      // ← route /tutorial-videos

  // 週期採購（本地模組，獨立資料庫 cycle-purchase.db，不對接 Ragic）
  cyclePurchaseDashboard:      '週採 Dashboard',      // ← route /cycle-purchase/dashboard
  cyclePurchaseItems:          '料號主檔',            // ← route /cycle-purchase/items
  cyclePurchaseCycles:         '週期設定',            // ← route /cycle-purchase/cycles
  cyclePurchaseRequests:       '請購單',              // ← route /cycle-purchase/requests
  cyclePurchaseVendors:        '供應商主檔',          // ← route /cycle-purchase/masters/vendors
  cyclePurchaseCategories:     '類別主檔',            // ← route /cycle-purchase/masters/categories
  cyclePurchaseDepartments:    '部門主檔',            // ← route /cycle-purchase/masters/departments
  cyclePurchaseCostCenters:    '成本中心主檔',        // ← route /cycle-purchase/masters/cost-centers
  cyclePurchaseAccountCodes:   '會計科目主檔',        // ← route /cycle-purchase/masters/account-codes
  cyclePurchaseSummary:        '彙整單',              // ← route /cycle-purchase/summary
  cyclePurchasePOs:            '採購單',              // ← route /cycle-purchase/pos
  cyclePurchaseReceiving:       '驗收單',              // ← route /cycle-purchase/receiving
  cyclePurchaseReceivingReport: '進貨數量報表',        // ← route /cycle-purchase/receiving-report
  cyclePurchasePayments:        '請款單',              // ← route /cycle-purchase/payments
  cyclePurchaseAuditLog:        '異常稽核紀錄',        // ← route /cycle-purchase/audit-log
  cyclePurchaseManual:          '週採使用手冊',        // ← route /cycle-purchase/manual（2026-08-07 新增）

  // OPERA 營運分析（2026-08-04 新增；資料來源為人工上傳的 OPERA TXT，非 Ragic 同步）
  // ⚠️ 以下 label 必須與 role_permissions.py 的 PERMISSION_DEFINITIONS 完全一致
  operaDashboard:  '★ 營運分析 Dashboard',  // ← route /opera/dashboard
  operaRevenue:    '營收分析',              // ← route /opera/revenue
  operaGuest:      '住客與通路分析',        // ← route /opera/guest
  operaImport:     '資料匯入',              // ← route /opera/import
  // 2026-08-04：匯入紀錄併入「資料匯入」頁的 TAB，不再是獨立選單項；
  // 標籤保留給 TAB 標題與 /opera/batches 導向後的頁面使用。
  operaBatches:    '匯入紀錄',              // ← /opera/import?tab=batches
  operaLookup:     '歷史同期查詢',          // ← route /opera/lookup（2026-08-05 新增）
  operaForecast:   '房價預測',              // ← route /opera/forecast（2026-08-05 新增）
  // 2026-08-05：事件月曆併入房價預測頁的 TAB，選單不再有獨立項目。
  // 標籤保留給 TAB 標題、權限清單與 /opera/events 導向後的頁面使用。
  operaEvents:     '事件月曆',              // ← /opera/forecast?tab=events
  // 市場區隔／房型趨勢（2026-08-07）。⚠️ 資料來源是 OHIP API 落地，不是 TXT 上傳。
  // ⚠️ 這個字串必須與 role_permissions.py 的 opera_segment_view label 完全一致，
  //    否則管理員在「權限設定」看到的名稱與側邊欄不同（CLAUDE.md §3）。
  operaSegments:   '市場區隔分析',          // ← route /opera/segments
  // 訂房分析（2026-08-07）。⚠️ 母體與 operaGuest 不同：所有訂房 vs 已離店住客。
  // ⚠️ 這個字串必須與 role_permissions.py 的 opera_reservation_view label 完全一致。
  operaReservations: '訂房分析',           // ← route /opera/reservations
  // 訂房 Pace／Pickup（2026-08-13）。⚠️ 這一頁的歷史進度是以訂房日「回推」得出，
  //    與訂房分析的「現在狀態」可信度不同，所以另開權限 key。
  // ⚠️ 這個字串必須與 role_permissions.py 的 opera_pace_view label 完全一致。
  //    注意分隔號是全形「／」，不是半形 /。
  operaPace:       '訂房 Pace／Pickup',    // ← route /opera/pace
  operaSettings:   '分析門檻設定',          // ← route /opera/settings
  operaManual:     '使用手冊',              // ← route /opera/manual（共用 opera_view 權限）

  // ── 即時營運（2026-08-06 新增）────────────────────────────────────────────
  // 資料直接來自 OPERA Cloud（OHIP）REST API，**不是**上傳的 TXT。
  // 刻意獨立成一級選單，避免與 /opera/* 的上傳型資料在同一處被誤讀為同一時點。
  // 規格書：docs/SPEC_realtime_operations.md §8.1
  // ⚠️ 下列 label 必須與 role_permissions.py 的 PERMISSION_DEFINITIONS 完全一致。
  realtimeDashboard: '即時營運看板',        // ← route /realtime/dashboard
  realtimeRevenue:   '營收與結構分析',      // ← route /realtime/revenue
  realtimeCompare:   '與營運分析比對',      // ← route /realtime/compare
  realtimeLogs:      'API 呼叫紀錄',        // ← route /realtime/logs（共用 realtime_view）
  realtimeManual:    '使用手冊',            // ← route /realtime/manual（共用 realtime_view）

  // ── 金旭分析（2026-08-05 新增）────────────────────────────────────────────
  // ⚠️ 下列名稱必須與 backend/app/routers/role_permissions.py 的 PERMISSION_DEFINITIONS
  //    label 完全一致，否則管理員在「權限設定」看到的名稱會與側邊欄不同。
  jinxuDashboard:   '★ 金旭分析 Dashboard',  // ← route /jinxu/dashboard
  jinxuReservation: '訂房與通路分析',        // ← route /jinxu/reservation
  jinxuRevenue:     '收入結構分析',          // ← route /jinxu/revenue
  jinxuPayment:     '付款方式分析',          // ← route /jinxu/payment
  jinxuDeposit:     '預收訂金追蹤',          // ← route /jinxu/deposit
  jinxuImport:      '資料匯入',              // ← route /jinxu/import（含匯入紀錄 TAB）
  jinxuSettings:    '科目與門檻設定',        // ← route /jinxu/settings
  jinxuManual:      '使用手冊',              // ← route /jinxu/manual（共用 jinxu_view 權限）

  // ── 口碑分析（2026-08-21 新增）────────────────────────────────────────────
  // 資料來源：Booking／Expedia／Tripadvisor 的公開評論頁。規格書 docs/SPEC_ota_reviews.md
  // ⚠️ 下列字串必須與 role_permissions.py PERMISSION_DEFINITIONS 的 label 逐字相同，
  //    否則管理員在「權限設定」看到的名稱與側邊欄不同，會以為是兩個不同的東西。
  otaDashboard:     '★ 口碑分析 Dashboard',  // ← route /ota/dashboard（P5 交付）
  otaReviews:       '評論清單',              // ← route /ota/reviews
  otaAlerts:        '負評警示',              // ← route /ota/alerts（P4 交付）
  otaTrend:         '趨勢與雙館比較',        // ← route /ota/trend（P5 交付）
  otaSources:       'OTA 來源設定',          // ← route /ota/sources（含 CSV 匯入）
  otaTopics:        '主題字典維護',          // ← route /ota/topics（P4 交付）
} as const
