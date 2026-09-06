/**
 * exportRowsToExcel — 前端直接產出 .xlsx（SheetJS）
 *
 * 2026-09-06 建立。用於「明細清單 Modal 右上角的匯出 Excel」，資料就是 Modal
 * 已經載入的清單狀態，不另打後端。
 *
 * 為什麼不走後端：
 *   這些清單的內容是「使用者剛才點的那一格 / 那張 KPI 卡片」篩出來的結果，
 *   後端既有的 export 端點（如 luqun-repair/export、dazhi-repair/export）吃的是
 *   year/month/type/floor/status/keyword 這類條件，表達不出「這批 cases」。
 *   再打一次後端等於把篩選邏輯重跑一遍，還要冒匯出內容與畫面不一致的風險。
 *
 * 需要底色、欄寬、凍結窗格的「全表匯出」仍走後端 openpyxl + downloadFile()，
 * 兩種模式並存是刻意的。
 *
 * 空值一律匯出成空儲存格，不要傳畫面上的佔位符「—」進來——那會讓 Excel 的
 * 篩選、排序、公式都要多處理一種字串。
 */
import { message } from 'antd'

/** Excel 工作表名稱：上限 31 字元，且不可含 [ ] : * ? / \ */
function sanitizeSheetName(name: string): string {
  return name.replace(/[[\]:*?/\\]/g, '').slice(0, 31) || '明細'
}

export interface ExportExcelOptions {
  /** 存檔檔名，需自行帶 .xlsx 副檔名 */
  filename: string
  /** 工作表名稱，預設「明細」。會自動去除非法字元並截到 31 字元 */
  sheetName?: string
  /** 各欄字元寬度，依 rows 第一列的 key 順序對應 */
  colWidths?: number[]
}

/**
 * 把資料列陣列產成 .xlsx 並觸發瀏覽器下載。
 *
 * @param rows 每列一個物件，物件的 key 就是 Excel 的標題列文字，順序即欄位順序
 * @returns 是否成功產檔（rows 為空時回傳 false 且不產檔）
 */
export async function exportRowsToExcel(
  rows: Record<string, string | number>[],
  { filename, sheetName = '明細', colWidths }: ExportExcelOptions,
): Promise<boolean> {
  if (!rows.length) {
    message.warning('沒有可匯出的資料')
    return false
  }
  try {
    // 動態載入：xlsx 約 900KB，不讓它進主 bundle
    const XLSX = await import('xlsx')
    const ws = XLSX.utils.json_to_sheet(rows)
    if (colWidths?.length) {
      ws['!cols'] = colWidths.map((wch) => ({ wch }))
    }
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, sanitizeSheetName(sheetName))
    XLSX.writeFile(wb, filename)
    return true
  } catch {
    message.error('匯出失敗，請稍後再試')
    return false
  }
}

/** 檔名用的日期戳：20260906 */
export function exportTimestamp(): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}`
}

/** antd column 定義中我們需要的兩個欄位（ColumnsType 是聯合型別，dataIndex 只存在於 ColumnType） */
interface ExportableColumn {
  title?: unknown
  dataIndex?: unknown
}

/**
 * 直接從 antd 的 columns 定義組出匯出用的資料列。
 *
 * 用於欄位會依呼叫端動態變動的清單（如 repair 兩頁的 CaseListModal，各觸發點會傳
 * 不同的 extraColumns），這樣匯出欄位自動跟著畫面走，不必在匯出函式裡再維護一份
 * 欄位對照表。
 *
 * 規則：
 *   - `title` 不是字串、或沒有 `dataIndex` 的欄位一律跳過
 *     → 「詳情」這種純按鈕欄會自動被排除，不需特別處理
 *   - 取原始值，不套用 column 的 render（render 回傳的是 JSX，不能寫進儲存格）
 *   - null / undefined → 空字串（空儲存格）
 */
export function rowsFromAntdColumns<T extends object>(
  data: readonly T[],
  columns: readonly ExportableColumn[],
): Record<string, string | number>[] {
  const usable = columns.filter(
    (c) => typeof c.title === 'string' && typeof c.dataIndex === 'string',
  ) as { title: string; dataIndex: string }[]

  return data.map((rec) => {
    const row: Record<string, string | number> = {}
    usable.forEach(({ title, dataIndex }) => {
      const v = (rec as Record<string, unknown>)[dataIndex]
      row[title] = v == null ? '' : (typeof v === 'number' ? v : String(v))
    })
    return row
  })
}
