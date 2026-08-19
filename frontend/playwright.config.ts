/**
 * Playwright E2E 設定 — Portal 前端 Smoke Test
 *
 * 執行方式（在 frontend/ 目錄下）：
 *   npm run test:e2e            # 無頭執行
 *   npm run test:e2e:ui         # 開 Playwright UI 模式（除錯用）
 *   npm run test:e2e:report     # 開啟上次的 HTML 報告
 *
 * 前置條件：
 *   1. 後端已啟動（127.0.0.1:8000）—— 不自動拉起，見下方說明
 *   2. frontend/e2e/.env 已填好 E2E_USER / E2E_PASS（見 e2e/.env.example）
 *
 * 前端 dev server 會自動處理：webServer + reuseExistingServer
 *   - 5300 已經開著 → 直接沿用，不重開（不會搶 port）
 *   - 5300 沒開      → 自動執行 npm run dev，測試結束後關掉
 *
 * 後端刻意不自動拉起：啟動方式依環境而異（venv 路徑、正式區是 NSSM 服務），
 * 由測試代管風險高於效益。後端沒起來時 helpers.ts 的前置探測會直接講明原因。
 */
import { defineConfig, devices } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

// ── 讀取 e2e/.env（不引入 dotenv 套件，避免多一個相依）─────────────────────
// 該檔已被專案根目錄 .gitignore 的 `.env` 規則涵蓋，不會進版控。
const envFile = path.resolve(__dirname, 'e2e/.env')
if (fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf-8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$/)
    if (m && !line.trim().startsWith('#') && !process.env[m[1]]) {
      process.env[m[1]] = m[2].replace(/^["']|["']$/g, '')
    }
  }
}

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5300'

// 只有指向本機時才自動拉 dev server。
// 若把 E2E_BASE_URL 指到測試區／正式區，絕不能在本機另外開一個 dev server
// ——那會變成「測試連遠端、卻順手在本機起了一個沒人用的服務」。
const IS_LOCAL = /^https?:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(BASE_URL)

export default defineConfig({
  testDir: './e2e',

  // Dashboard 頁一次平行呼叫 7 支 API，給寬鬆一點的 timeout
  timeout: 90_000,
  expect: { timeout: 15_000 },

  // 後端目前是單一 worker（見 docs：async def 阻塞問題），
  // 平行測試會互相排隊造成偽陽性失敗，固定序列執行。
  fullyParallel: false,
  workers: 1,
  retries: 0,

  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],

  // 前端 dev server：已開著就沿用，沒開才自己拉起來
  webServer: IS_LOCAL
    ? {
        command: 'npm run dev',
        url: BASE_URL,
        reuseExistingServer: true,   // ← 關鍵：不會與既有的 npm run dev 搶 port
        timeout: 120_000,            // 冷啟動 + OneDrive 目錄，給寬一點
        stdout: 'ignore',
        stderr: 'pipe',
      }
    : undefined,

  use: {
    baseURL: BASE_URL,

    // ⚠️ 必設。Playwright 預設 actionTimeout = 0（永不逾時），
    //    定位不到的元素會無聲卡住直到整個 hook 逾時，錯誤還會指到別的地方。
    actionTimeout: 15_000,
    navigationTimeout: 30_000,

    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    locale: 'zh-TW',
    timezoneId: 'Asia/Taipei',
    viewport: { width: 1600, height: 1000 },
    // 自簽憑證 / 內網環境用
    ignoreHTTPSErrors: true,
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
})
