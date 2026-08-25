/**
 * OTA 模組共用的「多選篩選器」與「條件描述文字」
 *
 * 建立日期：2026-08-25
 *
 * ═══════════════════════════════════════════════════════════════════════
 * 為什麼抽成共用檔
 * ═══════════════════════════════════════════════════════════════════════
 * 飯店／平台的多選下拉出現在**四個頁面**（Dashboard、評論清單、
 * 負評警示、趨勢）。四份各寫各的，遲早會變成：
 *
 *   · 一頁選了三間顯示「瀚寓 +2」，另一頁顯示「3 間飯店」
 *   · 一頁的「全部」是空陣列，另一頁是 `['']`
 *   · 一頁 join(',') 一頁 join('，')（全形逗號 → 後端拆不開，靜默查無資料）
 *
 * 這與 2026-08-23 統一負評門檻（`NEGATIVE_SCORE_MAX`）是同一個理由：
 * **同一個概念在不同畫面上必須是同一份實作。**
 */
import React from 'react'
import { Select, Tooltip } from 'antd'
import type { HotelOption, PlatformOption } from '@/types/ota'

/** 標題裡最多列幾個名稱，超過改成「+N」 */
const TITLE_MAX_NAMES = 2

/**
 * 多選下拉。與 antd 原生 `Select` 的差別只有預設值，
 * 但**那些預設值就是重點** —— 四個頁面必須長得一樣、行為一樣。
 *
 * ⚠️ `maxTagCount="responsive"` 而不是固定數字：篩選列的寬度各頁不同，
 *    固定數字在窄的那頁會把版面撐爆。
 * ⚠️ 空陣列 ＝ 全部（不送 `hotel_code` 參數），與後端
 *    `split_codes("")` 回空 list、不加 `WHERE` 的語意一致。
 */
export function MultiCodeSelect(props: {
  value: string[]
  onChange: (value: string[]) => void
  options: { value: string; label: string }[]
  placeholder: string
  width?: number
}) {
  const { value, onChange, options, placeholder, width = 220 } = props
  return (
    <Select
      mode="multiple"
      allowClear
      value={value}
      onChange={onChange}
      options={options}
      placeholder={placeholder}
      style={{ minWidth: width }}
      maxTagCount="responsive"
      // ⚠️ 中文名稱要能用輸入法篩 —— 預設的 filterOption 比對的是 value
      //    （HANNS、HANNS_SUMMER），使用者打「瀚寓」會找不到任何東西。
      optionFilterProp="label"
    />
  )
}

/**
 * 把選取的代碼轉成畫面上的說明文字。
 *
 * | 選了幾個 | 顯示 |
 * |---------|------|
 * | 0（全部）| `allLabel`（例：「全部飯店」） |
 * | 1        | 「瀚寓」 |
 * | 2        | 「瀚寓、瀚寓夏天」 |
 * | 3 以上   | 「瀚寓、瀚寓夏天 +2」 |
 *
 * ⚠️ 用**名稱**不用代碼：畫面上出現 `HANNS_SUMMER` 對使用者沒有意義。
 * ⚠️ 找不到對應名稱時退回代碼本身，不要顯示 `undefined` ——
 *    來源被刪掉但評論還在時就會發生（評論不會連帶刪除）。
 */
export function describeCodes(
  codes: string[],
  options: { value: string; label: string }[],
  allLabel: string,
): string {
  if (!codes.length) return allLabel
  const names = codes.map(
    (code) => options.find((o) => o.value === code)?.label || code,
  )
  if (names.length <= TITLE_MAX_NAMES) return names.join('、')
  return `${names.slice(0, TITLE_MAX_NAMES).join('、')} +${names.length - TITLE_MAX_NAMES}`
}

/**
 * 標題旁邊的條件說明。選超過 `TITLE_MAX_NAMES` 個時，
 * 滑鼠移上去看得到完整清單 —— 「+2」本身沒有資訊，
 * 但完整清單塞在標題列會把版面撐爆。
 */
export function ScopeText(props: {
  codes: string[]
  options: { value: string; label: string }[]
  allLabel: string
}) {
  const { codes, options, allLabel } = props
  const short = describeCodes(codes, options, allLabel)
  if (codes.length <= TITLE_MAX_NAMES) return <>{short}</>
  const full = codes
    .map((code) => options.find((o) => o.value === code)?.label || code)
    .join('、')
  return (
    <Tooltip title={full}>
      <span style={{ borderBottom: '1px dotted #bbb', cursor: 'help' }}>{short}</span>
    </Tooltip>
  )
}

/** `HotelOption[]` → Select 的 options（統一在這裡轉，免得各頁欄位名寫錯） */
export function hotelOptions(hotels: HotelOption[]) {
  return hotels.map((h) => ({ value: h.value, label: h.label }))
}

export function platformOptions(platforms: PlatformOption[]) {
  return platforms.map((p) => ({ value: p.value, label: p.label }))
}

/**
 * 送給 API 的值：空陣列 → 不帶參數（`undefined`），否則逗號串接。
 *
 * ⚠️ **一律用半形逗號**。全形「，」後端 `split_codes()` 拆不開，
 *    症狀是「選了兩間卻查無資料」而且不會有任何錯誤。
 */
export function toParam(codes: string[]): string | undefined {
  return codes.length ? codes.join(',') : undefined
}
