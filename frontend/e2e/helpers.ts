/**
 * E2E 共用工具 — 登入、API／console 收集器
 *
 * 設計原則：
 *  - 只做「觀測」，不對 Portal 做任何寫入操作
 *  - 不斷言顏色、版型、字級（docs/PROTECTED.md 的項目不用測試鎖死）
 */
import { expect, type Page, type Locator } from '@playwright/test'

export const API_RE = /\/api\/v1\//

export interface ApiCall {
  url: string
  method: string
  status: number
}

/**
 * 已知且與測試目的無關的 console 雜訊。
 * antd 5 的 deprecated 警告走 React 的 console.error，必須濾掉，
 * 否則每次 antd 升版測試就全紅。
 */
const IGNORED_CONSOLE: RegExp[] = [
  /\[antd:/i,
  /deprecated/i,
  /Support for defaultProps will be removed/i,
  /findDOMNode is deprecated/i,
  /ResizeObserver loop/i,
  /Download the React DevTools/i,
  /React Router Future Flag Warning/i,
]

/**
 * 掛上 API 回應與 console error 收集器。
 * 回傳的兩個陣列會就地累積，測試中直接讀取即可。
 */
export function attachCollectors(page: Page) {
  const apiCalls: ApiCall[] = []
  const consoleErrors: string[] = []

  page.on('response', (res) => {
    const url = res.url()
    if (API_RE.test(url)) {
      apiCalls.push({ url, method: res.request().method(), status: res.status() })
    }
  })

  page.on('console', (msg) => {
    if (msg.type() !== 'error') return
    const text = msg.text()
    if (IGNORED_CONSOLE.some((re) => re.test(text))) return
    consoleErrors.push(text)
  })

  // 未攔截的 JS 例外（React 崩潰會走這條）
  page.on('pageerror', (err) => {
    consoleErrors.push(`[pageerror] ${err.message}`)
  })

  return { apiCalls, consoleErrors }
}

/**
 * antd 按鈕的名稱比對式。要同時處理兩件事：
 *
 *  1. **自動插入空格**：antd 對「剛好兩個中文字」的按鈕會插一個空格
 *     （autoInsertSpaceInButton），「查詢」的可存取名稱其實是「查 詢」。
 *  2. **icon 會計入可存取名稱**：`<Button icon={<SearchOutlined />}>查詢</Button>`
 *     的名稱是「search 查 詢」而不是「查 詢」——antd 的 icon 是
 *     `<span role="img" aria-label="search">`，會被算進 accessible name。
 *
 * 因此**刻意不加 `^`／`$` 錨點**，只比對中文字之間可有空白。
 *   cjkButton('查詢') → /查\s*詢/
 */
export function cjkButton(text: string): RegExp {
  return new RegExp(text.split('').join('\\s*'))
}

/**
 * 取得某個 Tab 對應的內容區（panel）。
 *
 * ⚠️ **不要用 `.ant-tabs-tabpane-active` + `.first()`**：巢狀 Tabs 的作用中 pane
 *    可能在 DOM 中比外層更早出現，抓到哪一個會隨掛載時序改變，測試會時好時壞。
 *    改用 tab 的 `aria-controls` 精準對應。
 */
export async function panelOf(page: Page, tab: Locator): Promise<Locator> {
  const id = await tab.getAttribute('aria-controls')
  expect(id, 'Tab 沒有 aria-controls，無法對應到內容區').toBeTruthy()
  return page.locator(`[id="${id}"]`)
}

/**
 * 斷言內容區「有東西」。
 * ⚠️ 不用 `not.toBeEmpty()`：`<iframe>` 沒有文字也沒有子節點會被判定為空
 *    （exec-work-dashboard 的「統計基準說明」就是純 iframe）。
 *    改為「元素子節點數 + 文字長度 > 0」。
 */
export async function expectHasContent(scope: Locator, where: string): Promise<void> {
  const children = await scope.locator(':scope > *').count()
  const text = (await scope.innerText().catch(() => '')).trim()
  expect(children + text.length, `${where} 內容是空的`).toBeGreaterThan(0)
}

/**
 * 不納入「API 全 2xx」斷言的路徑。
 * 這些端點的非 2xx 是**設計上的預期行為**，不是故障。
 */
export const API_2XX_EXEMPT: RegExp[] = [
  // fetchCaseImages() 先打 /db-images，DB 沒圖時預期 404，再 fallback 到 /case-images
  /\/luqun-repair\/db-images\//,
  /\/dazhi-repair\/db-images\//,
]

/** 把 ApiCall 陣列排版成易讀的失敗訊息 */
export function formatCalls(calls: ApiCall[]): string {
  if (!calls.length) return '（無）'
  return calls.map((c) => `    ${c.status}  ${c.method}  ${stripOrigin(c.url)}`).join('\n')
}

export function stripOrigin(url: string): string {
  try {
    const u = new URL(url)
    return u.pathname + u.search
  } catch {
    return url
  }
}

/**
 * 以 e2e/.env 的帳密登入。
 * 登入表單來源：frontend/src/pages/Login/index.tsx
 *  - identifier 欄位 placeholder = 「帳號 / Email」
 *  - password   欄位 placeholder = 「密碼」
 *  - token 存於 localStorage['access_token']（authStore.ts）
 */
export async function login(page: Page): Promise<void> {
  const identifier = process.env.E2E_USER
  const password = process.env.E2E_PASS

  if (!identifier || !password) {
    throw new Error(
      '缺少 E2E_USER / E2E_PASS。請在 frontend/e2e/ 下複製 .env.example 為 .env 並填入帳密。'
    )
  }

  // ── 前置探測：先用 API 層確認「站台通 + 後端通 + 帳密對」───────────────
  // 不先做這一步的話，只要其中任何一環有問題，都會表現成「UI 卡住」，
  // 很難分辨是選擇器寫錯還是環境沒起來。
  const probe = await page.request
    .post('/api/v1/auth/login', {
      data: { identifier, password },
      failOnStatusCode: false,
      timeout: 20_000,
    })
    .catch((e: Error) => {
      throw new Error(
        `連不到 ${process.env.E2E_BASE_URL || 'http://127.0.0.1:5300'}/api/v1/auth/login。\n` +
          '請確認：① 前端 dev server 已啟動（npm run dev，:5300）\n' +
          '        ② 後端已啟動（uvicorn app.main:app --port 8000）\n' +
          `原始錯誤：${e.message}`
      )
    })

  if (probe.status() === 429) {
    throw new Error(
      '登入被 Rate Limit 擋下（5 次失敗鎖 5 分鐘）。等 5 分鐘或重啟後端後再跑。'
    )
  }
  if (probe.status() !== 200) {
    const body = await probe.text().catch(() => '')
    throw new Error(
      `帳密驗證失敗：HTTP ${probe.status()}\n` +
        `回應：${body.slice(0, 300)}\n` +
        '請確認 frontend/e2e/.env 的 E2E_USER / E2E_PASS。'
    )
  }

  const probeBody = (await probe.json().catch(() => ({}))) as {
    must_change_password?: boolean
    user?: { must_change_password?: boolean }
  }
  const mustChange = probeBody.must_change_password ?? probeBody.user?.must_change_password
  expect(
    mustChange,
    '此帳號被標記為「必須變更密碼」，登入後會被強制導向改密碼流程，無法用於 E2E。請改用其他帳號。'
  ).toBeFalsy()

  // ── UI 登入 ─────────────────────────────────────────────────────────────
  await page.goto('/login')

  // 限定在登入卡片內，避免抓到「忘記密碼」Modal 裡同 placeholder 的欄位
  const card = page.locator('.ant-card').first()
  const idInput = card.getByPlaceholder('帳號 / Email')
  const pwInput = card.getByPlaceholder('密碼')
  // ⚠️ antd 對「剛好兩個中文字」的按鈕會自動插入空格（autoInsertSpaceInButton），
  //    實際的可存取名稱是「登 入」而非「登入」。凡是兩字中文按鈕都要容忍中間的空白。
  const submit = card.getByRole('button', { name: /^登\s*入/ })

  await expect(idInput, '找不到登入頁的「帳號 / Email」欄位，登入頁可能沒渲染出來').toBeVisible()
  await expect(pwInput, '找不到登入頁的「密碼」欄位').toBeVisible()
  await expect(submit, '找不到「登入」按鈕').toBeVisible()

  await idInput.fill(identifier)
  await pwInput.fill(password)

  const [loginRes] = await Promise.all([
    page.waitForResponse((r) => r.url().includes('/api/v1/auth/login'), { timeout: 30_000 }),
    submit.click(),
  ])

  expect(
    loginRes.status(),
    `UI 登入回應 HTTP ${loginRes.status()}（API 層探測是通的，代表問題出在表單送出而非帳密）`
  ).toBe(200)

  // 登入後導向 '/'，由 HomeRedirect 依權限決定目標頁
  await expect(page, '登入後仍停在 /login，表單可能沒有成功送出').not.toHaveURL(/\/login/, {
    timeout: 20_000,
  })

  const token = await page.evaluate(() => localStorage.getItem('access_token'))
  expect(token, '登入後 localStorage 未寫入 access_token').toBeTruthy()
}

/** 呼叫需要 JWT 的 API（帶上 localStorage 裡的 token） */
export async function apiGet(page: Page, path: string) {
  return page.evaluate(async (p) => {
    const token = localStorage.getItem('access_token')
    const res = await fetch(p, { headers: { Authorization: `Bearer ${token}` } })
    let body: unknown = null
    try {
      body = await res.json()
    } catch {
      /* 非 JSON 回應 */
    }
    return { status: res.status, body }
  }, path)
}

/** 等頁面上所有 XHR 安靜下來；networkidle 逾時不視為失敗（輪詢型頁面可能永不 idle） */
export async function settle(page: Page, ms = 1500): Promise<void> {
  try {
    await page.waitForLoadState('networkidle', { timeout: 20_000 })
  } catch {
    /* 忽略：改用固定等待 */
  }
  await page.waitForTimeout(ms)
}
