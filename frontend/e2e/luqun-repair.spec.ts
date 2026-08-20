/**
 * E2E 深測 — 商場工務報修（/luqun-repair/dashboard）
 *
 * 安全性：本模組 API 全部是 GET（已逐一核對 src/api/luqunRepair.ts，
 * 無任何 POST/PUT/DELETE），測試不會污染資料。
 *
 * 刻意不涵蓋：
 *  - 「連線測試」按鈕（GET /ping）與 /sync、/raw-fields
 *    → 這三支會**即時打 Ragic**，納入 smoke test 會讓測試變慢、變不穩，
 *      還會消耗 Ragic API 額度。診斷工具適合手動用。
 *  - 圖片 Lightbox（Image.PreviewGroup）
 *    → 需要該筆案件真的有附圖，會把測試綁死在特定資料上。
 *  - 顏色、版型、字級（docs/PROTECTED.md 項目，理由見 exec-work-dashboard.spec.ts 檔頭）
 *
 * ⚠️ /db-images 的 404 是**預期行為**：fetchCaseImages() 先打 /db-images，
 *    DB 沒圖時預期 404，再 fallback 到 /case-images。已列入 API_2XX_EXEMPT。
 */
import { test, expect, type Page, type Locator } from '@playwright/test'
import {
  attachCollectors, login, settle, apiGet, formatCalls, stripOrigin,
  cjkButton, API_2XX_EXEMPT, panelOf, expectHasContent, type ApiCall,
} from './helpers'

const ROUTE = '/luqun-repair/dashboard'
const PAGE_TITLE = '商場工務報修'
const PERMISSION_KEY = 'luqun_repair_view'

/**
 * 8 個 Tab 與各自的資料來源。
 *
 * `manual: true` ＝ 該 Tab **不會**在切換時自動載入，要按「查詢」才發請求。
 * 「未指定工作日誌」（UnassignedJournalTab）就是這種：`handleLoad` 只掛在按鈕上，
 * 沒有 mount 時的 useEffect。這是刻意設計（避免每次切過去就打一次工作日誌查詢），
 * 不是 bug —— 測試要跟著按按鈕，不能假設切換就會有 API。
 */
const TABS: Array<{ label: string; name: RegExp; endpoint: string; manual?: boolean }> = [
  { label: 'Dashboard',        name: /Dashboard/,        endpoint: '/api/v1/luqun-repair/dashboard' },
  { label: '3.1 報修',          name: /3\.1\s*報修/,       endpoint: '/api/v1/luqun-repair/stats/repair' },
  { label: '3.2 結案時間',      name: /3\.2\s*結案時間/,    endpoint: '/api/v1/luqun-repair/stats/closing' },
  { label: '3.3 報修類型',      name: /3\.3\s*報修類型/,    endpoint: '/api/v1/luqun-repair/stats/type' },
  { label: '3.4 本月客房報修表', name: /3\.4\s*本月客房報修表/, endpoint: '/api/v1/luqun-repair/stats/room' },
  { label: '金額統計',          name: /金額統計/,          endpoint: '/api/v1/luqun-repair/stats/fee' },
  { label: '報修清單總表',      name: /報修清單總表/,       endpoint: '/api/v1/luqun-repair/detail' },
  { label: '未指定工作日誌',    name: /未指定工作日誌/,     endpoint: '/api/v1/work-journal/', manual: true },
]

/** 進站首屏一定會打的兩支 */
const BOOT_ENDPOINTS = [
  '/api/v1/luqun-repair/years',
  '/api/v1/luqun-repair/filter-options',
]

test.describe.configure({ mode: 'serial' })

let page: Page
let apiCalls: ApiCall[]
let consoleErrors: string[]

// ── 共用小工具 ──────────────────────────────────────────────────────────────

/**
 * 目前作用中的 Tab 內容區。
 *
 * ⚠️ 不用 `.ant-tabs-tabpane-active` + `.first()`：巢狀 Tabs 的作用中 pane
 *    可能在 DOM 中比外層更早出現，抓到哪一個會隨掛載時序改變。
 *    這裡取「被選取的 tab」再用 aria-controls 對應——外層 Tabs 的 tab bar
 *    一定排在自己的內容之前，因此 .first() 對 tab 元素是可靠的。
 */
async function activePane(): Promise<Locator> {
  const tab = page.getByRole('tab', { selected: true }).first()
  return panelOf(page, tab)
}

/** 頁面頂端的年月查詢列（QueryBar）。用「年度：」錨定，避免抓到清單頁自己的搜尋列 */
function queryBar(): Locator {
  return page.locator('.ant-card').filter({ hasText: '年度：' }).first()
}

/**
 * 報修清單總表自己的搜尋列。
 *
 * ⚠️ 不能用 `filter({ hasText: '關鍵字（編號/標題/報修人）' })`：
 *    那串字是 `<input>` 的 **placeholder 屬性**，不是文字內容，`hasText` 比對不到。
 *    改用 `filter({ has: ... })` 以「內含該輸入框」來鎖定卡片。
 *    （對照：queryBar() 的「年度：」是真的 <Text> 文字，hasText 可用。）
 */
function detailSearchBar(): Locator {
  return page
    .locator('.ant-card')
    .filter({ has: page.getByPlaceholder('關鍵字（編號/標題/報修人）') })
    .last()
}

async function switchTab(name: RegExp): Promise<void> {
  const tab = page.getByRole('tab', { name })
  await tab.click()
  await settle(page, 900)
  await expect(tab).toHaveAttribute('aria-selected', 'true')
}

/** 畫面上不該出現的計算殘骸 */
async function expectNoBadNumbers(scope: Locator, where: string): Promise<void> {
  const text = await scope.innerText()
  for (const bad of ['NaN', 'undefined', 'Infinity']) {
    const hit = text.split('\n').filter((l) => l.includes(bad))
    expect(hit, `${where} 出現「${bad}」：\n    ${hit.join('\n    ')}`).toEqual([])
  }
}

/** 取出這批呼叫中失敗的（排除設計上允許非 2xx 的端點） */
function failedCalls(calls: ApiCall[]): ApiCall[] {
  return calls.filter(
    (c) => c.status >= 400 && !API_2XX_EXEMPT.some((re) => re.test(c.url))
  )
}

/**
 * 建立「等待某支端點回應」的 waiter。
 *
 * ⚠️ 必須在**觸發動作之前**呼叫，之後再 await。
 *    不要改回「點完睡固定秒數再檢查」—— 那會隨機失敗：
 *    settle() 的 networkidle 在請求還沒發出時會立刻通過，剩下的固定等待
 *    只要遇上機器忙碌或後端稍慢就不夠（B-2 就是這樣紅過一次）。
 */
function waitForEndpoint(endpoint: string) {
  return page
    .waitForResponse((r) => stripOrigin(r.url()).startsWith(endpoint), { timeout: 30_000 })
    .catch(() => null)   // 逾時不直接拋，交給後面的斷言產生可讀的錯誤訊息
}

/** 從 antd Select 的下拉選單挑第 n 個選項，回傳選到的文字 */
async function pickSelectOption(select: Locator, index = 0): Promise<string> {
  await select.click()
  const dropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').last()
  const option = dropdown.locator('.ant-select-item-option').nth(index)
  await expect(option, '下拉選單沒有任何可選項目').toBeVisible()
  const label = (await option.innerText()).trim()
  await option.click()
  return label
}

// ── 進站 ────────────────────────────────────────────────────────────────────

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
// A. 基礎
// ══════════════════════════════════════════════════════════════════════════

test('A-1 頁面載入：標題、麵包屑、查詢列、8 個 Tab 都在（非白畫面 / 非 403）', async () => {
  await expect(page).toHaveURL(new RegExp(`${ROUTE}$`))

  await expect(
    page.getByText('存取被拒絕', { exact: true }),
    `帳號沒有 ${PERMISSION_KEY} 權限，被 PermissionGuard 擋下`
  ).toHaveCount(0)

  await expect(page.getByRole('heading', { name: PAGE_TITLE })).toBeVisible()
  await expect(page.locator('.ant-breadcrumb')).toContainText(PAGE_TITLE)

  // 查詢列：年度 / 月份 / 查詢 / 重設
  await expect(queryBar()).toBeVisible()
  await expect(queryBar().getByRole('button', { name: cjkButton('查詢') })).toBeVisible()
  await expect(queryBar().getByRole('button', { name: cjkButton('重設') })).toBeVisible()

  for (const t of TABS) {
    await expect(page.getByRole('tab', { name: t.name }), `找不到 Tab「${t.label}」`).toBeVisible()
  }
})

test('A-2 首屏 API 全 2xx，且 years / filter-options / dashboard 都有被呼叫', async () => {
  expect(apiCalls.length, '完全沒有攔到 /api/v1 請求').toBeGreaterThan(0)

  const failed = failedCalls(apiCalls)
  expect(failed, `以下 API 非 2xx：\n${formatCalls(failed)}`).toEqual([])

  const called = apiCalls.map((c) => stripOrigin(c.url))
  const expectBoot = [...BOOT_ENDPOINTS, '/api/v1/luqun-repair/dashboard']
  const missing = expectBoot.filter((ep) => !called.some((p) => p.startsWith(ep)))
  expect(
    missing,
    `首屏未呼叫：\n    ${missing.join('\n    ')}\n實際：\n${formatCalls(apiCalls)}`
  ).toEqual([])
})

test('A-3 沒有 console error 與未攔截的 JS 例外', async () => {
  expect(
    consoleErrors,
    `頁面產生了 ${consoleErrors.length} 則 error：\n    ${consoleErrors.join('\n    ')}`
  ).toEqual([])
})

test(`A-4 權限 key「${PERMISSION_KEY}」存在於後端 PERMISSION_DEFINITIONS 且 label 一致（CLAUDE.md §3）`, async () => {
  const res = await apiGet(page, '/api/v1/role-permissions/keys')
  test.skip(res.status === 403, '測試帳號沒有 settings_roles_manage 權限，跳過')
  expect(res.status).toBe(200)

  const keys = res.body as Array<{ key: string; label: string; group: string }>
  const found = keys.find((k) => k.key === PERMISSION_KEY)

  expect(
    found,
    `PERMISSION_DEFINITIONS 缺少「${PERMISSION_KEY}」，該頁將永遠無法授權`
  ).toBeTruthy()
  expect(
    found!.label,
    `權限 label「${found!.label}」與 navLabels.ts 的「${PAGE_TITLE}」不一致`
  ).toBe(PAGE_TITLE)
})

// ══════════════════════════════════════════════════════════════════════════
// B. 8 個 Tab 各自深測
// ══════════════════════════════════════════════════════════════════════════

TABS.forEach((t, i) => {
  test(`B-${i + 1} Tab「${t.label}」：切換成功、${t.endpoint} 被呼叫且 2xx、內容有渲染、數值無殘骸`, async () => {
    const before = apiCalls.length

    // 若該端點還沒被打過，就先掛好 waiter 再觸發動作（不能事後才等）。
    // 已經打過的（例如 Dashboard 在首屏就載入）再切回去不會重打，掛了只會白等 30 秒。
    const already = apiCalls.some((c) => stripOrigin(c.url).startsWith(t.endpoint))
    const waiter = already ? null : waitForEndpoint(t.endpoint)

    await switchTab(t.name)
    const pane = await activePane()

    // 手動載入型的 Tab 要先按「查詢」才會發請求（見 TABS 註解）
    if (t.manual) {
      await pane.getByRole('button', { name: cjkButton('查詢') }).first().click()
    }

    if (waiter) await waiter
    await settle(page, 800)

    // 該 Tab 的資料來源有沒有被打過（首次切換時觸發；Dashboard 在首屏就打過）
    const called = apiCalls.map((c) => stripOrigin(c.url))
    expect(
      called.some((p) => p.startsWith(t.endpoint)),
      `切到「${t.label}」後，${t.endpoint} 從未被呼叫。\n累計呼叫：\n${formatCalls(apiCalls)}`
    ).toBeTruthy()

    // 本次切換觸發的呼叫不能有失敗
    const fresh = apiCalls.slice(before)
    const failed = failedCalls(fresh)
    expect(failed, `切到「${t.label}」時 API 失敗：\n${formatCalls(failed)}`).toEqual([])

    // 內容有東西（表格 / 圖表 / 統計數字 至少有一個）
    await expectHasContent(pane, `Tab「${t.label}」`)
    const widgets = pane.locator('.ant-table, .ant-statistic, .recharts-wrapper, svg')
    expect(
      await widgets.count(),
      `Tab「${t.label}」沒有渲染出任何表格／圖表／統計數字`
    ).toBeGreaterThan(0)

    await expectNoBadNumbers(pane, `Tab「${t.label}」`)
  })
})

// ══════════════════════════════════════════════════════════════════════════
// C. 年月查詢列
// ══════════════════════════════════════════════════════════════════════════

test('C-1 切換年度後按「查詢」，API 帶對 year', async () => {
  await switchTab(TABS[0].name)   // 回 Dashboard

  const yearSelect = queryBar().locator('.ant-select').first()
  const before = apiCalls.length

  // 年度清單來自 /years，取第二個（若只有一年就沿用第一個）
  await yearSelect.click()
  const dropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').last()
  const count = await dropdown.locator('.ant-select-item-option').count()
  const target = (await dropdown.locator('.ant-select-item-option').nth(count > 1 ? 1 : 0).innerText())
    .replace(/[^\d]/g, '')
  await dropdown.locator('.ant-select-item-option').nth(count > 1 ? 1 : 0).click()

  await queryBar().getByRole('button', { name: cjkButton('查詢') }).click()
  await settle(page, 1200)

  const fresh = apiCalls.slice(before)
  const withYear = fresh.filter((c) => /[?&]year=/.test(c.url))
  expect(withYear.length, `按查詢後沒有任何帶 year 的請求：\n${formatCalls(fresh)}`).toBeGreaterThan(0)

  const wrong = withYear.filter((c) => !new RegExp(`[?&]year=${target}(&|$)`).test(c.url))
  expect(wrong, `以下請求的 year 不是 ${target}：\n${formatCalls(wrong)}`).toEqual([])
  expect(failedCalls(fresh), `查詢後 API 失敗：\n${formatCalls(failedCalls(fresh))}`).toEqual([])
})

test('C-2 月份選「全年」後查詢，請求不帶特定月份（month 省略或為 0）', async () => {
  const monthSelect = queryBar().locator('.ant-select').nth(1)
  const before = apiCalls.length

  await monthSelect.click()
  const dropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').last()
  await dropdown.locator('.ant-select-item-option', { hasText: '全年' }).first().click()

  await queryBar().getByRole('button', { name: cjkButton('查詢') }).click()
  await settle(page, 1200)

  const fresh = apiCalls.slice(before)
  expect(fresh.length, '選「全年」後沒有觸發任何請求').toBeGreaterThan(0)

  // QueryBar 把「全年」轉成 null，呼叫端不帶 month（Dashboard 端則帶 month=0）
  const badMonth = fresh.filter((c) => /[?&]month=([1-9]|1[0-2])(&|$)/.test(c.url))
  expect(
    badMonth,
    `選「全年」後仍有請求帶特定月份：\n${formatCalls(badMonth)}`
  ).toEqual([])
  expect(failedCalls(fresh), `全年查詢 API 失敗：\n${formatCalls(failedCalls(fresh))}`).toEqual([])
})

test('C-3 「重設」把年月還原成當年當月', async () => {
  await queryBar().getByRole('button', { name: cjkButton('重設') }).click()
  await settle(page, 1200)

  const now = new Date()
  await expect(queryBar().locator('.ant-select').first()).toContainText(String(now.getFullYear()))
  await expect(queryBar().locator('.ant-select').nth(1)).toContainText(`${now.getMonth() + 1} 月`)
})

// ══════════════════════════════════════════════════════════════════════════
// D. 報修清單總表（本模組最複雜的畫面）
// ══════════════════════════════════════════════════════════════════════════

test('D-0 切到清單並選「全年」，確保後續篩選測試有足夠資料', async () => {
  const monthSelect = queryBar().locator('.ant-select').nth(1)
  await monthSelect.click()
  await page
    .locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')
    .last()
    .locator('.ant-select-item-option', { hasText: '全年' })
    .first()
    .click()
  await queryBar().getByRole('button', { name: cjkButton('查詢') }).click()
  await settle(page, 1200)

  await switchTab(TABS[6].name)   // 報修清單總表

  const listPane = await activePane()
  await expect(listPane.locator('.ant-table')).toBeVisible()
  const rows = listPane.locator('.ant-table-tbody tr.ant-table-row')
  expect(
    await rows.count(),
    '全年範圍下清單仍為 0 筆，後續篩選測試無意義。請確認 Ragic 同步是否正常。'
  ).toBeGreaterThan(0)
})

test('D-1 分頁資訊：顯示「共 N 筆」且 N > 0', async () => {
  const total = (await activePane()).locator('.ant-pagination-total-text')
  await expect(total).toBeVisible()
  const n = Number((await total.innerText()).replace(/[^\d]/g, ''))
  expect(n, '總筆數解析不出數字或為 0').toBeGreaterThan(0)
})

test('D-2 「報修類型」篩選：API 帶 repair_type，且結果列的類型欄都符合', async () => {
  const before = apiCalls.length
  const typeSelect = detailSearchBar().locator('.ant-select').nth(0)
  const picked = await pickSelectOption(typeSelect, 0)

  await detailSearchBar().getByRole('button', { name: cjkButton('查詢') }).click()
  await settle(page, 1200)

  const fresh = apiCalls.slice(before).filter((c) => c.url.includes('/luqun-repair/detail'))
  expect(fresh.length, '按查詢後沒有打 /detail').toBeGreaterThan(0)
  expect(
    fresh.some((c) => /[?&]repair_type=/.test(c.url)),
    `/detail 請求沒有帶 repair_type：\n${formatCalls(fresh)}`
  ).toBeTruthy()
  expect(failedCalls(fresh), formatCalls(failedCalls(fresh))).toEqual([])

  // 回傳的每一列，類型欄都要等於所選類型
  const rows = (await activePane()).locator('.ant-table-tbody tr.ant-table-row')
  const n = await rows.count()
  if (n > 0) {
    const cells = await rows.locator('td').nth(3).allInnerTexts()
    const mismatched = cells.filter((c) => c.trim() !== picked)
    expect(
      mismatched,
      `篩選「${picked}」後仍出現其他類型：${[...new Set(mismatched)].join('、')}`
    ).toEqual([])
  }
})

test('D-3 「處理狀況」多選篩選：API 帶 status', async () => {
  const before = apiCalls.length
  const statusSelect = detailSearchBar().locator('.ant-select').nth(2)
  await pickSelectOption(statusSelect, 0)
  await page.keyboard.press('Escape')

  await detailSearchBar().getByRole('button', { name: cjkButton('查詢') }).click()
  await settle(page, 1200)

  const fresh = apiCalls.slice(before).filter((c) => c.url.includes('/luqun-repair/detail'))
  expect(
    fresh.some((c) => /[?&]status=/.test(c.url)),
    `/detail 請求沒有帶 status：\n${formatCalls(fresh)}`
  ).toBeTruthy()
  expect(failedCalls(fresh), formatCalls(failedCalls(fresh))).toEqual([])
})

test('D-4 關鍵字搜尋：API 帶 keyword', async () => {
  const before = apiCalls.length
  await detailSearchBar().getByPlaceholder('關鍵字（編號/標題/報修人）').fill('A')
  await detailSearchBar().getByRole('button', { name: cjkButton('查詢') }).click()
  await settle(page, 1200)

  const fresh = apiCalls.slice(before).filter((c) => c.url.includes('/luqun-repair/detail'))
  expect(
    fresh.some((c) => /[?&]keyword=/.test(c.url)),
    `/detail 請求沒有帶 keyword：\n${formatCalls(fresh)}`
  ).toBeTruthy()
  expect(failedCalls(fresh), formatCalls(failedCalls(fresh))).toEqual([])
})

test('D-5 「重設」清空清單頁的四個篩選條件', async () => {
  await detailSearchBar().getByRole('button', { name: cjkButton('重設') }).click()
  await settle(page, 600)

  await expect(detailSearchBar().getByPlaceholder('關鍵字（編號/標題/報修人）')).toHaveValue('')
  // 三個 Select 都回到 placeholder 狀態（沒有選中項）
  for (const i of [0, 1, 2]) {
    await expect(
      detailSearchBar().locator('.ant-select').nth(i).locator('.ant-select-selection-item'),
      `第 ${i + 1} 個篩選器沒有被重設`
    ).toHaveCount(0)
  }
})

test('D-6 「匯出 Excel」連結帶著目前的查詢條件（只檢查連結，不實際下載）', async () => {
  const link = detailSearchBar().getByRole('link', { name: /匯出 Excel/ })
  await expect(link).toBeVisible()

  const href = (await link.getAttribute('href')) ?? ''
  expect(href, '匯出連結沒有指向 luqun-repair/export').toContain('/luqun-repair/export')
  expect(/[?&]year=\d{4}/.test(href), '匯出連結沒有帶 year').toBeTruthy()
  // token 只驗證有帶，不印出內容
  expect(/[?&]token=/.test(href), '匯出連結沒有帶 token，下載會 401').toBeTruthy()
})

test('D-7 點「發生時間」欄標題會觸發伺服器端排序（API 帶 sort_by / sort_desc）', async () => {
  const before = apiCalls.length

  // antd 第一次點擊 sorter 欄位為 ascend → sort_desc=false
  await (await activePane()).locator('th.ant-table-column-has-sorters', { hasText: '發生時間' }).first().click()
  await settle(page, 1200)

  const fresh = apiCalls.slice(before).filter((c) => c.url.includes('/luqun-repair/detail'))
  expect(
    fresh.length,
    '點欄位標題後沒有打 /detail —— Table 的 onChange 可能又被拿掉了'
  ).toBeGreaterThan(0)

  const sorted = fresh.filter((c) => /[?&]sort_by=occurred_at/.test(c.url))
  expect(sorted.length, `/detail 請求沒有帶 sort_by=occurred_at：\n${formatCalls(fresh)}`).toBeGreaterThan(0)
  expect(
    sorted.some((c) => /[?&]sort_desc=false/.test(c.url)),
    `升冪排序時 sort_desc 應為 false：\n${formatCalls(sorted)}`
  ).toBeTruthy()
  expect(failedCalls(fresh), formatCalls(failedCalls(fresh))).toEqual([])
})

// ══════════════════════════════════════════════════════════════════════════
// E. 明細 Drawer（CLAUDE.md §7 MANDATORY 規範）
// ══════════════════════════════════════════════════════════════════════════

test('E-1 點擊列可開啟明細 Drawer，標題為「報修詳情：{編號}」', async () => {
  const firstRow = (await activePane()).locator('.ant-table-tbody tr.ant-table-row').first()
  await expect(firstRow, '清單沒有資料，無法測 Drawer').toBeVisible()
  await firstRow.click()

  const drawer = page.locator('.ant-drawer-content')
  // 沒有 DB 圖時會 fallback 去打 Ragic 取圖，給寬一點的等待
  await expect(drawer, 'Drawer 沒有開啟').toBeVisible({ timeout: 30_000 })
  await expect(page.locator('.ant-drawer-title')).toContainText('報修詳情：')
})

test('E-2 標題列有「在 Ragic 查看」連結，且指向 Ragic（§7：連結必須在標題列，不可放 body 底部）', async () => {
  const titleBar = page.locator('.ant-drawer-header')
  const ragicLink = titleBar.getByRole('link', { name: /在 Ragic 查看/ })

  await expect(ragicLink, '標題列找不到「在 Ragic 查看」連結').toBeVisible()

  const href = (await ragicLink.getAttribute('href')) ?? ''
  expect(href, `Ragic 連結的 href 不正確：${href}`).toContain('ragic.com')
  await expect(ragicLink, 'Ragic 連結應該開新分頁').toHaveAttribute('target', '_blank')
})

test('E-3 Drawer 明細欄位齊全（報修編號／標題／處理狀況／總費用／結案時間）', async () => {
  const body = page.locator('.ant-drawer-body')
  for (const label of ['報修編號', '標題', '處理狀況', '總費用', '結案時間', '維修圖片']) {
    await expect(
      body.getByText(label, { exact: true }).first(),
      `Drawer 缺少「${label}」欄位`
    ).toBeVisible()
  }

  await expectNoBadNumbers(body, '明細 Drawer')

  await page.locator('.ant-drawer-close').click()
  await expect(page.locator('.ant-drawer-content')).toBeHidden()
})
