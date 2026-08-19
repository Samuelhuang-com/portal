/**
 * Smoke Test — 集團決策 Dashboard（/exec-work-dashboard）
 *
 * 為什麼選這頁當第一個 E2E：
 *   本頁全部是 GET，沒有任何寫入操作，測試腳本不會污染資料。
 *
 * 本頁最關鍵的風險：
 *   index.tsx 用 Promise.allSettled 平行呼叫 7 支 API。
 *   任何一支掛掉都會被「吞掉」—— 頁面照樣渲染、不會白畫面，
 *   只是對應區塊悄悄變成 0 或空白。肉眼看不出來，只有攔 API 才抓得到。
 *   → L1-2 是本檔最重要的一條測試。
 *
 * 涵蓋範圍：
 *   第一層  L1-1 頁面渲染      L1-2 API 全 2xx
 *           L1-3 無 console error   L1-4 三個 Tab 可切換
 *   第二層  L2-5 年月篩選重打 API   L2-6 數值無 NaN/undefined
 *           L2-7 permissionKey 一致性（CLAUDE.md §3）
 *
 * 刻意不測（見 CLAUDE.md / docs/PROTECTED.md）：
 *   顏色、版型、字級、Sidebar 寬度 —— 保護靠規範與 code review，
 *   寫進斷言只會讓「保護」變成「凍結」，任何微調都得同步改測試。
 */
import { test, expect, type Page } from '@playwright/test'
import {
  attachCollectors, login, settle, apiGet, formatCalls, stripOrigin,
  panelOf, expectHasContent,
  type ApiCall,
} from './helpers'

const ROUTE = '/exec-work-dashboard'
const PAGE_TITLE = '集團決策 Dashboard'
const PERMISSION_KEY = 'exec_work_dashboard_view'

/** index.tsx 檔頭列出的 7 個資料來源 */
const EXPECTED_ENDPOINTS = [
  '/api/v1/luqun-repair/dashboard',
  '/api/v1/dazhi-repair/dashboard',
  '/api/v1/hotel/monthly-hours',
  '/api/v1/mall/monthly-hours',
  '/api/v1/hotel/daily-hours',
  '/api/v1/mall/daily-hours',
  '/api/v1/work-category-analysis/stats',
]

const MAIN_TABS = ['集團工務概覽', '工作日誌', '統計基準說明']

// 這頁載入成本高（7 支 API），共用同一個 page 依序跑，不要每個 test 重載
test.describe.configure({ mode: 'serial' })

let page: Page
let apiCalls: ApiCall[]
let consoleErrors: string[]

test.beforeAll(async ({ browser }) => {
  const context = await browser.newContext()
  page = await context.newPage()

  const collectors = attachCollectors(page)
  apiCalls = collectors.apiCalls
  consoleErrors = collectors.consoleErrors

  await login(page)
  await page.goto(ROUTE)
  await settle(page)
})

test.afterAll(async () => {
  await page?.context()?.close()
})

// ══════════════════════════════════════════════════════════════════════════
// 第一層 — 必做
// ══════════════════════════════════════════════════════════════════════════

test('L1-1 頁面載入：標題、麵包屑、三個主 Tab 都渲染出來（非白畫面 / 非 403）', async () => {
  await expect(page).toHaveURL(new RegExp(`${ROUTE}$`))

  // PermissionGuard 擋下時顯示「存取被拒絕」區塊而非頁面內容
  // （文案來源：frontend/src/router/index.tsx PermissionGuard）
  await expect(
    page.getByText('存取被拒絕', { exact: true }),
    `帳號沒有 ${PERMISSION_KEY} 權限，被 PermissionGuard 擋下。請先在「角色管理 → 權限設定」授予。`
  ).toHaveCount(0)

  await expect(page.getByRole('heading', { name: PAGE_TITLE })).toBeVisible()
  await expect(page.locator('.ant-breadcrumb')).toContainText(PAGE_TITLE)

  for (const name of MAIN_TABS) {
    await expect(page.getByRole('tab', { name, exact: true })).toBeVisible()
  }

  // KPI 卡片區至少渲染出一張
  await expect(page.locator('.ant-statistic').first()).toBeVisible()
})

test('L1-2 所有 /api/v1 回應皆為 2xx —— Promise.allSettled 會吞掉失敗，這條是本檔核心', async () => {
  expect(apiCalls.length, '完全沒有攔到任何 /api/v1 請求，頁面可能根本沒載入').toBeGreaterThan(0)

  const failed = apiCalls.filter((c) => c.status >= 400)
  expect(
    failed,
    `以下 API 回應非 2xx（畫面可能仍正常顯示，但數字是空的）：\n${formatCalls(failed)}`
  ).toEqual([])

  // 7 支來源是否真的都打了（少打 = 前端條件判斷改壞，也是一種靜默失敗）
  const calledPaths = apiCalls.map((c) => stripOrigin(c.url))
  const missing = EXPECTED_ENDPOINTS.filter((ep) => !calledPaths.some((p) => p.startsWith(ep)))
  expect(
    missing,
    `index.tsx 檔頭宣告的資料來源中，以下未被呼叫：\n    ${missing.join('\n    ')}\n` +
      `實際呼叫：\n${formatCalls(apiCalls)}`
  ).toEqual([])
})

test('L1-3 沒有 console error 與未攔截的 JS 例外', async () => {
  expect(
    consoleErrors,
    `頁面產生了 ${consoleErrors.length} 則 error：\n    ${consoleErrors.join('\n    ')}`
  ).toEqual([])
})

test('L1-4 三個主 Tab 都切得動，且各自渲染出內容', async () => {
  for (const name of MAIN_TABS) {
    const tab = page.getByRole('tab', { name, exact: true })
    await tab.click()
    await settle(page, 800)

    await expect(tab, `Tab「${name}」點擊後未成為 active`).toHaveAttribute('aria-selected', 'true')

    // 用 aria-controls 精準對應內容區（理由見 helpers.panelOf）
    const pane = await panelOf(page, tab)
    await expectHasContent(pane, `Tab「${name}」`)
  }

  // 回到概覽，供後續測試使用
  await page.getByRole('tab', { name: '集團工務概覽', exact: true }).click()
  await settle(page, 800)
})

// ══════════════════════════════════════════════════════════════════════════
// 第二層
// ══════════════════════════════════════════════════════════════════════════

test('L2-5 切換「報修年月」後，API 重新呼叫且帶對 year / month 參數', async () => {
  const filterZone = page.locator('.ant-space').filter({ hasText: '報修年月：' }).first()
  await expect(filterZone, '找不到「報修年月：」篩選器').toBeVisible()

  const monthSelect = filterZone.locator('.ant-select').nth(1)
  const current = Number((await monthSelect.innerText()).replace(/[^\d]/g, ''))
  const target = current === 1 ? 2 : current - 1

  // 只保留本次操作觸發的請求
  const before = apiCalls.length

  await monthSelect.click()
  await page
    .locator(`.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option[title="${target} 月"]`)
    .first()
    .click()
  await settle(page, 1200)

  const fresh = apiCalls.slice(before)
  expect(fresh.length, `切換月份為 ${target} 月後沒有觸發任何 API 重新呼叫`).toBeGreaterThan(0)

  // ⚠️ 只檢查帶「具體月份（1–12）」的請求。
  //    index.tsx 有兩個 fetchStats：一個帶 selectedMonth、另一個**刻意帶 month=0**
  //    （0 ＝ 全年，用來算年度累計）。把 month=0 也一起檢查會誤判。
  const withMonth = fresh.filter((c) => /[?&]month=([1-9]|1[0-2])(&|$)/.test(c.url))
  expect(withMonth.length, `重打的請求都沒有帶具體月份：\n${formatCalls(fresh)}`).toBeGreaterThan(0)

  const wrongMonth = withMonth.filter((c) => !new RegExp(`[?&]month=${target}(&|$)`).test(c.url))
  expect(
    wrongMonth,
    `以下請求的 month 參數不是 ${target}：\n${formatCalls(wrongMonth)}`
  ).toEqual([])

  const failedAfter = fresh.filter((c) => c.status >= 400)
  expect(failedAfter, `切換月份後有 API 失敗：\n${formatCalls(failedAfter)}`).toEqual([])
})

test('L2-6 展開所有摺疊區後，畫面數值沒有 NaN / undefined / Infinity，且統計表有 TOTAL 列', async () => {
  const pane = await panelOf(page, page.getByRole('tab', { name: '集團工務概覽', exact: true }))

  // ⚠️ 概覽頁的表格大多包在 antd Collapse 裡，摺疊時內容**根本不在 DOM**。
  //    不先展開的話：① TOTAL 列找不到 ② 數值檢查其實只掃到一小部分畫面。
  const collapsed = pane.locator('.ant-collapse-header[aria-expanded="false"]')
  for (let i = await collapsed.count(); i > 0; i = await collapsed.count()) {
    await collapsed.first().click()
    await settle(page, 400)
    if ((await collapsed.count()) >= i) break   // 點不動就停，避免無限迴圈
  }
  await settle(page, 600)

  const text = await pane.innerText()

  for (const bad of ['NaN', 'undefined', 'Infinity']) {
    const hit = text.split('\n').filter((l) => l.includes(bad))
    expect(
      hit,
      `畫面出現「${bad}」（多半是除以 0 或欄位名對不上）：\n    ${hit.join('\n    ')}`
    ).toEqual([])
  }

  await expect(
    pane.getByText('TOTAL', { exact: true }).first(),
    '每日/每月累計工時表的 TOTAL 列不見了'
  ).toBeVisible()
})

test(`L2-7 權限 key「${PERMISSION_KEY}」存在於後端 PERMISSION_DEFINITIONS（CLAUDE.md §3）`, async () => {
  // MainLayout.tsx 的 permissionKey 若在 role_permissions.py 沒有對應項目，
  // 該頁永遠不會出現在「角色管理 → 權限設定」，管理員無法為任何角色開放。
  const res = await apiGet(page, '/api/v1/role-permissions/keys')

  test.skip(
    res.status === 403,
    '測試帳號沒有 settings_roles_manage 權限，無法讀取權限 key 清單（不影響其他測試）'
  )
  expect(res.status, `GET /api/v1/role-permissions/keys 回應 ${res.status}`).toBe(200)

  const keys = res.body as Array<{ key: string; label: string; group: string }>
  const found = keys.find((k) => k.key === PERMISSION_KEY)

  expect(
    found,
    `role_permissions.py 的 PERMISSION_DEFINITIONS 缺少「${PERMISSION_KEY}」。` +
      'MainLayout.tsx 已經用了這個 key，兩邊必須一致，否則此頁永遠無法授權。'
  ).toBeTruthy()

  // label 必須與 navLabels.ts 一致，否則權限設定頁與側邊欄名稱不同會造成混淆
  expect(
    found!.label,
    `權限 label「${found!.label}」與 navLabels.ts 的「${PAGE_TITLE}」不一致`
  ).toBe(PAGE_TITLE)
})
