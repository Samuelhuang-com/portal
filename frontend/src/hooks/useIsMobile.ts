/**
 * useIsMobile — 手機寬度判斷（2026-09-13 新增）
 *
 * 用途：只用於「要不要建議使用者進手機殼層」這一類的一次性判斷，
 *       **不要**拿它在同一個畫面裡動態切換 Layout。
 *
 * 原因：Portal 的手機版與桌面版是兩組平行路由（/m/* 與 /*），各自有自己的
 *       Layout。若改用寬度動態切換，平板轉向、瀏覽器縮放、外接螢幕都會讓
 *       Layout 元件換掉 → 整棵 React 子樹卸載重掛 → 正在填的表單資料消失。
 *       網址路徑才是唯一真實來源。
 *
 * ⚠️ antd 的 Grid.useBreakpoint() 在首次 render 會回傳 {}（所有值都是
 *    undefined），所以必須用 `=== false` 判斷，不能寫 `!screens.md`，
 *    否則桌面使用者在第一個 frame 會被誤判成手機。
 */
import { Grid } from 'antd'

/** 螢幕寬度小於 antd md 斷點（768px）時為 true */
export function useIsMobile(): boolean {
  const screens = Grid.useBreakpoint()
  return screens.md === false
}

export default useIsMobile
