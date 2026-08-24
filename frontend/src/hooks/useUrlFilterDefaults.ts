/**
 * 從 URL query 讀「篩選條件的初值」。
 *
 * 建立日期：2026-08-23
 * 用途：Dashboard 的 KPI 卡點擊後帶著條件跳到清單／警示頁。
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️ 只在「首次掛載」讀一次，**不做雙向同步**
 * ═══════════════════════════════════════════════════════════════════════
 * 「state 改了就寫回 URL、URL 改了就更新 state」聽起來很完整，
 * 但那是一個很容易寫出無限迴圈的模式 ——
 * 寫 URL 觸發 re-render → 讀 URL → setState → 寫 URL → …
 *
 * 而且它解決的問題其實不存在：**使用者進到頁面之後就用畫面上的篩選器**，
 * 沒有人會在那時候去改網址列。單向讀取已經涵蓋所有真實情境：
 *
 *   · 從 Dashboard 點過來        ✅ 讀得到
 *   · 把網址複製給同事           ✅ 對方看到一樣的畫面
 *   · 重新整理                   ✅ 條件還在
 *   · 上一頁                     ✅ 回到 Dashboard
 *
 * ═══════════════════════════════════════════════════════════════════════
 * ⚠️ 為什麼用 URL query 而不是 router state
 * ═══════════════════════════════════════════════════════════════════════
 * `navigate(path, { state })` 傳的東西**不會出現在網址列**：
 * 重新整理就消失、複製網址給別人是另一個畫面。
 * 這種「看起來能用但分享不了」的行為比不能點更讓人困惑。
 */
import { useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import dayjs, { type Dayjs } from 'dayjs'

export interface UrlFilterDefaults {
  hotelCode: string
  platform: string
  /** null 代表「全部期間」—— 與 StandardRangePicker 的語意一致（CLAUDE.md §8.3） */
  range: [Dayjs, Dayjs] | null
  /** 分數低於多少（null ＝ 不篩） */
  scoreBelow: number | null
  alertStatus: string
  sentiment: string
  /** 有沒有從 URL 帶任何條件進來（用來決定要不要顯示「從 Dashboard 帶入」的提示） */
  hasAny: boolean
}

/**
 * ⚠️ 日期要**驗證過**才用。網址是使用者可以隨手改的東西，
 *    `dayjs('隨便打的字')` 會產生 Invalid Date，
 *    然後被 format 成 "Invalid Date" 送進 API —— 後端收到看不懂的字串，
 *    症狀是「篩選之後一筆都沒有」，而不是明確的錯誤。
 */
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/

function parseDate(raw: string | null): Dayjs | null {
  if (!raw || !DATE_RE.test(raw)) return null
  // ⚠️ **不要用 `dayjs(raw, 'YYYY-MM-DD', true)` 的嚴格模式** ——
  //    那需要 `customParseFormat` plugin，而本專案沒有載入它。
  //    沒有 plugin 時第二個參數會被忽略，嚴格模式**根本沒生效**，
  //    看起來有防護其實沒有。用 regex 先擋格式，再用 isValid 擋
  //    「2026-02-31」這種格式對但日期不存在的。
  const value = dayjs(raw)
  return value.isValid() && value.format('YYYY-MM-DD') === raw ? value : null
}

function parseScore(raw: string | null): number | null {
  if (raw === null || raw.trim() === '') return null
  const value = Number(raw)
  return Number.isFinite(value) && value >= 0 && value <= 10 ? value : null
}

export function useUrlFilterDefaults(): UrlFilterDefaults {
  const { search } = useLocation()

  // ⚠️ 依 `search` 記憶即可 —— 它是字串，內容沒變就不會重算。
  //    依 `useSearchParams()` 回傳的物件會每次都是新的，等於沒有記憶。
  return useMemo(() => {
    const params = new URLSearchParams(search)
    const start = parseDate(params.get('start'))
    const end = parseDate(params.get('end'))

    return {
      hotelCode: params.get('hotel_code') || '',
      platform: params.get('platform') || '',
      // ⚠️ 起迄**兩個都有效**才成立。只有一邊的話當成「全部期間」，
      //    硬湊一個開放區間會讓畫面上的期間顯示與實際查詢不一致。
      range: start && end ? [start, end] : null,
      // ⚠️ 網址是使用者能隨手改的：非數字、負數、超過 10 一律當成沒帶。
      //    塞一個 NaN 進 API 的症狀是「篩選後一筆都沒有」而不是明確的錯誤。
      scoreBelow: parseScore(params.get('score_below')),
      alertStatus: params.get('alert_status') || '',
      sentiment: params.get('sentiment') || '',
      hasAny: [...params.keys()].length > 0,
    }
  }, [search])
}

/**
 * 反過來：把篩選條件組成 query string，給 Dashboard 產生下鑽連結用。
 *
 * ⚠️ 空值一律**不帶** —— `?hotel_code=&platform=` 這種網址讀回來是空字串，
 *    行為上等同沒帶，但看起來很像「有指定但值是空的」，很難判讀。
 */
export function buildFilterQuery(input: {
  hotelCode?: string
  platform?: string
  range?: [Dayjs, Dayjs] | null
  scoreBelow?: number | null
  alertStatus?: string
  sentiment?: string
}): string {
  const params = new URLSearchParams()
  if (input.hotelCode) params.set('hotel_code', input.hotelCode)
  if (input.platform) params.set('platform', input.platform)
  if (input.range) {
    params.set('start', input.range[0].format('YYYY-MM-DD'))
    params.set('end', input.range[1].format('YYYY-MM-DD'))
  }
  // ⚠️ 用 `!= null` 而不是 truthy —— `scoreBelow: 0` 是合法的篩選條件
  //    （「分數低於 0」查不到東西，但那是使用者的選擇，不該被靜默丟掉）
  if (input.scoreBelow != null) params.set('score_below', String(input.scoreBelow))
  if (input.alertStatus) params.set('alert_status', input.alertStatus)
  if (input.sentiment) params.set('sentiment', input.sentiment)
  const query = params.toString()
  return query ? `?${query}` : ''
}
