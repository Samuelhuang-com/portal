/**
 * 站台執行期設定（Runtime Config）
 *
 * 目的：同一份前端 build 部署到不同 Server（正式區／測試區／各分站）時，
 *       畫面上的標題文字可以不同，且**不需要重新 build、不需要重啟後端**。
 *
 * 設定來源：`GET /api/v1/site-config`（後端 `system_settings` 資料表）。
 *          由「系統設定 → 基本設定」頁面維護，僅系統管理員可修改。
 *
 * 三段文字**各自獨立、整段自由輸入**，前端不做任何組字：
 *   site_title     → 側邊欄標題 ＋ 瀏覽器分頁標題
 *   login_title    → 登入頁大標
 *   login_subtitle → 登入頁副標
 *
 * 2026-08-11 變更沿革：
 *   ① 原本讀 `public/config.json` → 改讀後端 API。
 *      `config.json` 屬於前端 build 產物，**每次重新部署前端都會被覆蓋回預設值**。
 *      改存 DB 後才真正與部署脫鉤，且各 Server 有各自的 `portal.db`。
 *   ② 原本只存「品牌名稱」再組出 `{brand}集團管理 Portal` → 改為三段整段可改。
 *      各 Server 想改的不一定只有前綴，組字規則反而變成限制。
 *
 * 載入時機：`main.tsx` 在 ReactDOM 掛載前 await `loadSiteConfig()`，
 *          避免畫面先閃過預設文字再跳成正確值。
 *
 * ⚠️ 這支 API 是**公開端點**（登入頁未認證時就要顯示文字），
 *    因此刻意用原生 fetch 而不是 `@/api/client`，避免帶上 JWT 與
 *    401 攔截器的跳轉副作用（此處在 React 掛載前執行，跳轉會很難追）。
 */

/** API 讀取失敗時的最後保底值。後端亦有一份同樣的常數（`site_config.py`）。 */
const DEFAULTS = {
  siteTitle: '維春集團管理 Portal',
  loginTitle: '集團管理 Portal',
  loginSubtitle: '維春集團內部作業與管理平台',
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

interface SiteConfigPayload {
  site_title?: string
  login_title?: string
  login_subtitle?: string
}

let siteTitle = DEFAULTS.siteTitle
let loginTitle = DEFAULTS.loginTitle
let loginSubtitle = DEFAULTS.loginSubtitle

/** 側邊欄標題／瀏覽器分頁標題 */
export const getSiteTitle = (): string => siteTitle

/** 登入頁大標 */
export const getLoginTitle = (): string => loginTitle

/** 登入頁副標 */
export const getLoginSubtitle = (): string => loginSubtitle

/** 套用後端回傳的設定；缺欄或空字串一律退回該欄預設值。 */
function apply(data: SiteConfigPayload): void {
  siteTitle = (data.site_title ?? '').trim() || DEFAULTS.siteTitle
  loginTitle = (data.login_title ?? '').trim() || DEFAULTS.loginTitle
  loginSubtitle = (data.login_subtitle ?? '').trim() || DEFAULTS.loginSubtitle
}

/**
 * 載入站台設定。
 * 任何失敗（後端未啟動、網路異常、回傳格式不正確）一律靜默退回預設值，
 * 不可因設定讀取失敗導致整個 Portal 無法啟動。
 */
export async function loadSiteConfig(): Promise<void> {
  try {
    // no-store：避免瀏覽器快取住舊設定，導致改了文字卻看不到變化。
    // 另一個實際原因：後端未啟動時 Vite proxy／SPA fallback 會回 index.html，
    // 這種 HTML 回應一旦被快取，後端起來後仍會拿到舊的假回應。
    const res = await fetch(`${API_BASE}/site-config`, { cache: 'no-store' })
    if (res.ok) {
      // ⚠️ 後端未註冊此路由時，SPA catch-all 會回 **200 + index.html**（不是 404），
      //    因此不能只看 res.ok，必須確認 content-type 真的是 JSON。
      const contentType = res.headers.get('content-type') ?? ''
      if (contentType.includes('application/json')) {
        apply((await res.json()) as SiteConfigPayload)
      }
    }
  } catch {
    // 靜默退回 DEFAULTS
  }
  document.title = siteTitle
}
