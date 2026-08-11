/**
 * 首頁（Home Page）設定共用工具
 *
 * 2026-08-11 調整原因：
 * 1. 舊版首頁設定共用單一 localStorage key（portal_home_page_route），同一瀏覽器
 *    換帳號登入會沿用前一位使用者的首頁 → 改為「每帳號獨立」。
 * 2. 舊版 HomeRedirect 拿到設定值就無條件導向，完全不檢查權限；因角色不同，
 *    該路由很可能對目前帳號無效 → 改以「過濾後的選單」驗證，無效時取選單
 *    最上面第一個可進入的頁面當首頁。
 */

/** 舊版共用 key，保留供一次性遷移使用 */
export const HOME_PAGE_STORAGE_KEY = 'portal_home_page_route'

/** 每帳號獨立的 localStorage key */
export function homePageKey(userId?: string | null): string {
  return userId ? `${HOME_PAGE_STORAGE_KEY}:${userId}` : HOME_PAGE_STORAGE_KEY
}

/**
 * 讀取目前帳號的首頁設定。
 * 若該帳號尚無設定但存在舊版共用 key，做一次性遷移（搬移後刪除舊 key）。
 * 遷移可能把別人的設定帶進來，但呼叫端會再以選單驗證有效性，無效即 fallback。
 */
export function getHomePageRoute(userId?: string | null): string | null {
  try {
    const key = homePageKey(userId)
    const own = localStorage.getItem(key)
    if (own) return own

    const legacy = localStorage.getItem(HOME_PAGE_STORAGE_KEY)
    if (legacy && key !== HOME_PAGE_STORAGE_KEY) {
      localStorage.setItem(key, legacy)
      localStorage.removeItem(HOME_PAGE_STORAGE_KEY)
      return legacy
    }
    return legacy
  } catch {
    return null
  }
}

/** 寫入目前帳號的首頁設定 */
export function saveHomePageRoute(userId: string | null | undefined, route: string): void {
  try {
    localStorage.setItem(homePageKey(userId), route)
  } catch {
    /* quota 滿時靜默略過 */
  }
}

// ── 選單走訪工具（吃 filterMenuByPermissions 之後的結果）────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyMenuItem = any

/** 只有以 / 開頭的 key 才是真實路由（custom_xxx 為自訂群組，不可直接導向） */
function isRoute(key: unknown): key is string {
  return typeof key === 'string' && key.startsWith('/')
}

/**
 * 該路由是否出現在使用者「過濾後的選單」中（含各層節點）。
 * 找不到 = 因角色權限或選單設定，此頁對目前帳號無效。
 */
export function isRouteInMenu(items: AnyMenuItem[], route: string): boolean {
  if (!route) return false
  for (const item of items ?? []) {
    if (item?.key === route) return true
    if (Array.isArray(item?.children) && isRouteInMenu(item.children, route)) return true
  }
  return false
}

/**
 * 取選單「最上面」第一個可進入的頁面。
 * - 依選單既有順序（已套用 menu-config 排序）由上而下
 * - 群組（有 children）遞迴取其第一個可進入的子頁
 * - 排除 excludeKeys（預設排除「系統設定」群組，避免 admin 被送進設定頁）
 */
export function firstRouteInMenu(
  items: AnyMenuItem[],
  excludeKeys: string[] = ['settings'],
): string | null {
  for (const item of items ?? []) {
    if (!item || excludeKeys.includes(item.key)) continue
    if (Array.isArray(item.children) && item.children.length > 0) {
      const child = firstRouteInMenu(item.children, excludeKeys)
      if (child) return child
      continue
    }
    if (isRoute(item.key)) return item.key
  }
  return null
}
