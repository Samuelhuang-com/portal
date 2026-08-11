/**
 * 選單 Context — 把 MainLayout 算好的「套用 menu-config + 權限過濾後」選單
 * 分享給 Outlet 內的子元件（目前使用者：router 的 HomeRedirect）。
 *
 * 2026-08-11 新增：首頁重定向必須依「使用者真正看得到的選單」判斷，
 * 不能自己再算一份（會與側邊欄順序不一致）。
 */
import { createContext, useContext } from 'react'

export interface MenuItemsContextValue {
  /** filterMenuByPermissions 之後的選單（順序＝側邊欄順序） */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  items: any[]
  /** true = 仍在等 menu-config / permissions，items 不可信 */
  loading: boolean
}

export const MenuItemsContext = createContext<MenuItemsContextValue>({
  items: [],
  loading: true,
})

export function useMenuItemsContext(): MenuItemsContextValue {
  return useContext(MenuItemsContext)
}
