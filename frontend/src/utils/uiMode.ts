/**
 * UI 模式（桌面殼層 / 手機殼層）偏好設定（2026-09-13 新增）
 *
 * 判讀優先序（由高到低）：
 *   1. 使用者明確選過 → localStorage `portal_ui_mode`
 *   2. 網址已指定     → /m/* 走手機殼層，其餘走桌面殼層（由 router 決定，不經過本檔）
 *   3. 以上皆無       → 依螢幕寬度建議一次（見 useIsMobile）
 *
 * 命名沿用專案既有慣例（portal_sider_width、portal_home_page_route:{userId}）。
 * 本設定刻意**不分帳號**：同一支手機換人登入，仍然應該待在手機殼層。
 */

export type UiMode = 'auto' | 'mobile' | 'desktop'

export const UI_MODE_STORAGE_KEY = 'portal_ui_mode'

/** 讀取偏好；未設定或讀取失敗一律回 'auto' */
export function getUiMode(): UiMode {
  try {
    const v = localStorage.getItem(UI_MODE_STORAGE_KEY)
    if (v === 'mobile' || v === 'desktop' || v === 'auto') return v
    return 'auto'
  } catch {
    return 'auto'
  }
}

/** 寫入偏好（quota 滿或隱私模式時靜默略過） */
export function setUiMode(mode: UiMode): void {
  try {
    localStorage.setItem(UI_MODE_STORAGE_KEY, mode)
  } catch {
    /* ignore */
  }
}

/**
 * 是否應該進手機殼層。
 * @param isNarrow 目前視窗是否小於 md 斷點（由 useIsMobile 提供）
 */
export function shouldUseMobileShell(isNarrow: boolean): boolean {
  const mode = getUiMode()
  if (mode === 'mobile') return true
  if (mode === 'desktop') return false
  return isNarrow
}
