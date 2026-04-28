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
 *   2026-04-15  新增 luqun_repair（樂群工務報修）完整模組 + Dashboard
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
 */

// ── 系統標題 ──────────────────────────────────────────────────────────────────
export const SITE_TITLE = '維春集團管理 Portal'

// ── 一級選單（群組） ──────────────────────────────────────────────────────────
export const NAV_GROUP = {
  dashboard:  'Dashboard',
  budget:     '預算管理',         // ← 新增：預算管理（在 dashboard 之後、行事曆之前）
  calendar:   '行事曆',           // ← 新增：Command Calendar（在 dashboard 之後、hotel 之前）
  hotel:      '飯店管理',
  mall:                     '商場管理',
  luqun_repair:             '樂群工務報修',
  dazhi_repair:             '大直工務部',
  mall_facility_inspection:  '春大直商場工務巡檢',
  full_building_inspection:  '整棟巡檢',
  security:                  '保全管理',
  warehouse:  '倉庫管理',
  reports:    '報表',
  approvals:  '簽核管理',
  memos:      '公告牆',
  audit:      '稽核日誌',
  settings:   '系統設定',
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

  // 飯店管理
  roomMaintenance:        '客房保養',
  roomMaintenanceDetail:  '※1.1飯店客房保養管理',       // ← 原「客房保養明細」
  periodicMaintenance:    '1. 飯店週期保養表',
  ihgRoomMaintenance:     '2. IHG客房保養',             // ← 新增：年度矩陣保養
  repairs:                '報修管理',

  // 商場管理
  mallDashboard:           '商場週期保養',
  mallPeriodicMaintenance: '1.2 商場週期保養',
  b4fInspection:           '工務巡檢 - B4F',
  rfInspection:            '工務巡檢 - RF',
  b2fInspection:           '工務巡檢 - B2F',
  b1fInspection:           '工務巡檢 - B1F', //整棟工務每日巡檢

  // 樂群工務報修
  luqunRepairDashboard:    '樂群工務報修 Dashboard',

  // 大直工務部
  dazhiRepairDashboard:    '大直工務部 Dashboard',

  // ★工項類別分析
  workCategoryAnalysis:    '★工項類別分析',

  // 高階主管 Dashboard（新功能，獨立路由）
  execDashboard:           '高階主管 Dashboard',

  // 春大直商場工務巡檢
  mallFacilityDashboard:   '春大直工務巡檢',
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

  // 系統設定
  usersManage:           '使用者管理',
  rolesManage:           '角色管理',
  ragicConnections:      'Ragic 連線',
  ragicAppDirectory:     'Ragic 對應表',
  menuConfig:            '選單管理',
} as const

// ── 型別輔助 ────────────────────────────────────────────────────────────────────────────
export type NavGroupKey = keyof typeof NAV_GROUP
export type NavPageKey  = keyof typeof NAV_PAGE