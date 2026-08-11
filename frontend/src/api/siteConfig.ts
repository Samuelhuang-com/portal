/**
 * 站台基本設定 API。
 *
 * 注意：這裡是「設定頁」用的封裝，走已認證的 `apiClient`。
 * 前端啟動時讀取顯示文字的那一段在 `@/config/siteConfig`，
 * 刻意用原生 fetch（在 React 掛載前執行、且該端點為公開），兩者不共用。
 */
import apiClient from '@/api/client'

/** 三段顯示文字，各自獨立、整段自由輸入，後端不做組字。 */
export interface SiteConfigForm {
  /** 側邊欄標題 ＋ 瀏覽器分頁標題 */
  site_title: string
  /** 登入頁大標 */
  login_title: string
  /** 登入頁副標 */
  login_subtitle: string
}

export interface SiteConfigDetail extends SiteConfigForm {
  updated_at: string | null
  updated_by: string | null
}

/** 取得目前設定（含最後異動資訊）。需系統管理員。 */
export async function fetchSiteConfigDetail(): Promise<SiteConfigDetail> {
  const res = await apiClient.get<SiteConfigDetail>('/site-config/detail')
  return res.data
}

/** 更新三段顯示文字。需系統管理員。 */
export async function updateSiteConfig(payload: SiteConfigForm): Promise<SiteConfigDetail> {
  const res = await apiClient.put<SiteConfigDetail>('/site-config', payload)
  return res.data
}
