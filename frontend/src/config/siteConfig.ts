/**
 * 站台執行期設定（Runtime Config）
 *
 * 目的：同一份前端 build 部署到不同 Server（正式區／測試區／各分站）時，
 *       品牌名稱可以不同，且**不需要重新 build、不需要重啟後端**。
 *
 * 設定來源：`public/config.json` → build 後位於 `dist/config.json`。
 *          部署後直接編輯該檔存檔，使用者重整瀏覽器即生效。
 *
 * ⚠️ 注意：`config.json` 屬於前端 build 產物的一部分，
 *          **每次重新部署前端後會被覆蓋回預設值**，部署流程需重新套用各站設定。
 *
 * 載入時機：`main.tsx` 在 ReactDOM 掛載前 await `loadSiteConfig()`，
 *          避免畫面先閃過預設品牌名稱再跳成正確值。
 */

/** 讀取失敗或未設定時的退回值 */
const DEFAULT_BRAND = '維春'

interface SiteConfigFile {
  brand?: string
}

let brand: string = DEFAULT_BRAND

/** 品牌名稱（例：維春） */
export const getBrand = (): string => brand

/** 側邊欄／瀏覽器分頁標題（例：維春集團管理 Portal） */
export const getSiteTitle = (): string => `${brand}集團管理 Portal`

/** 登入頁副標（例：維春集團內部作業與管理平台） */
export const getSiteSubtitle = (): string => `${brand}集團內部作業與管理平台`

/**
 * 載入 `config.json`。
 * 任何失敗（檔案不存在、JSON 格式錯誤、網路異常）一律靜默退回預設值，
 * 不可因設定檔問題導致整個 Portal 無法啟動。
 */
export async function loadSiteConfig(): Promise<void> {
  try {
    // no-store：避免瀏覽器／CDN 快取住舊設定，導致改檔後看不到變化
    const res = await fetch(`${import.meta.env.BASE_URL}config.json`, { cache: 'no-store' })
    if (res.ok) {
      const data = (await res.json()) as SiteConfigFile
      if (typeof data.brand === 'string' && data.brand.trim()) {
        brand = data.brand.trim()
      }
    }
  } catch {
    // 靜默退回 DEFAULT_BRAND
  }
  document.title = getSiteTitle()
}
