/**
 * Main application layout with sidebar navigation
 * ⚠️  選單文字請勿在此直接修改，統一至 @/constants/navLabels.ts 修改
 * ✅  執行期自訂 label 與排序由 /api/v1/settings/menu-config 動態載入
 */
import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { Layout, Menu, Typography, Avatar, Dropdown, Space, theme, Skeleton } from 'antd'
import {
  ApartmentOutlined,
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
  MenuOutlined,
  ApiOutlined,
  DatabaseOutlined,
  DollarOutlined,
  BarChartOutlined,
  FundOutlined,
  RadarChartOutlined,
  ReadOutlined,
  BookOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { SITE_TITLE, NAV_GROUP, NAV_PAGE } from '@/constants/navLabels'
import { fetchMenuConfig, MenuConfigItem } from '@/api/menuConfig'
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
  // ── 行事曆（dashboard 之後、hotel 之前）────────────────────────────────────
  {
    key: '/calendar',
    icon: <CalendarOutlined />,
    label: NAV_GROUP.calendar,
    permissionKey: 'calendar_view',
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
      // { key: '/hotel/repairs',                 icon: <ToolOutlined />, label: NAV_PAGE.repairs },
    ],
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
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: NAV_GROUP.settings,
    children: [
      { key: '/settings/users',               icon: <UserOutlined />,     label: NAV_PAGE.usersManage,       permissionKey: 'settings_users_manage' },
      { key: '/settings/roles',               icon: <SettingOutlined />,  label: NAV_PAGE.rolesManage,       permissionKey: 'settings_roles_manage' },
      { key: '/settings/ragic-app-directory', icon: <DatabaseOutlined />, label: NAV_PAGE.ragicAppDirectory, permissionKey: 'settings_ragic_manage' },
      { key: '/settings/ragic-connections',   icon: <ApiOutlined />,      label: NAV_PAGE.ragicConnections,  permissionKey: 'settings_ragic_manage' },
      { key: '/settings/menu-config',              icon: <MenuOutlined />,      label: NAV_PAGE.menuConfig,           permissionKey: 'settings_menu_manage' },
      { key: '/settings/static-pages',             icon: <FileTextOutlined />,  label: NAV_PAGE.staticPages,          permissionKey: 'settings_menu_manage' },
      { key: '/settings/employee-manual-export',   icon: <BookOutlined />,      label: NAV_PAGE.employeeManualExport, permissionKey: 'system_admin_only' },
      { key: '/settings/knowledge-graph',          icon: <ApartmentOutlined />, label: NAV_PAGE.knowledgeGraph,       permissionKey: 'system_admin_only' },
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
 * - DB config 的 permission_key 優先於靜態預設的 permissionKey
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
  const hasPermission = (key: string | null | undefined): boolean => {
    if (!key) return true                     // 無設定 = 公開
    if (permissions.includes('*')) return true // system_admin 萬用符
    return permissions.includes(key)
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const filterItem = (item: any): any | null => {
    // 優先用 DB 設定的 permission_key（非 null 才算有效覆蓋），否則 fallback 到靜態預設
    // ⚠️  DB 值為 null 代表「MenuConfig 頁面未設定」，不應蓋掉程式碼的靜態 permissionKey
    const dbVal = dbPermMap.has(item.key) ? dbPermMap.get(item.key) : undefined
    const effectiveKey: string | null | undefined =
      dbVal != null ? dbVal : item.permissionKey

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
  const navigate = useNavigate()
  const location = useLocation()
  const logout  = useAuthStore((s) => s.logout)
  const setUser = useAuthStore((s) => s.setUser)
  const user    = useAuthStore((s) => s.user)
  const { token: designToken } = theme.useToken()

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
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── 系統設定選單僅限 system_admin 可見 ────────────────────────────────────
  const isSystemAdmin = !!(user?.roles?.includes('system_admin'))
  // 取得 permissions 陣列（用於 filterMenuByPermissions）
  const userPermissions = useMemo<string[]>(
    () => user?.permissions ?? (isSystemAdmin ? ['*'] : []),
    [user?.permissions, isSystemAdmin]
  )

  // base items：非 system_admin 時過濾掉 settings 群組（保留舊行為 + 被 filter 再次過濾）
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const baseItems = useMemo<any[]>(
    () => isSystemAdmin ? menuItems : menuItems.filter((item) => item.key !== 'settings'),
    [isSystemAdmin]
  )

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
          // 登出時清除 menu config 快取與首頁設定，防止帳號切換時殘留前一位使用者的設定
          localStorage.removeItem(MENU_CONFIG_CACHE_KEY)
          localStorage.removeItem('portal_home_page_route')
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
            <Outlet />
          )}
        </Content>
      </Layout>
    </Layout>
  )
}
