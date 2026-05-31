/**
 * 報修模組 PPT 匯出 — API 封裝
 * 對應後端 POST /api/v1/repair/ppt-export/export
 *
 * 支援模組：
 *   module="dazhi"  → 大直工務部
 *   module="luqun"  → 盧群商場工務報修
 */

export type RepairModule = 'dazhi' | 'luqun'

export interface RepairPptExportPayload {
  module: RepairModule
  year:   number
  month:  number
}

/** 下載檔名前綴：飯店工務報修 / 商場工務報修 */
const MODULE_FILENAME_PREFIX: Record<RepairModule, string> = {
  dazhi: '飯店工務報修',
  luqun: '商場工務報修',
}

/**
 * 觸發報修模組 PPTX 匯出並自動下載
 * 後端回傳 StreamingResponse（.pptx binary）
 */
export async function exportRepairPptx(payload: RepairPptExportPayload): Promise<void> {
  const token = localStorage.getItem('access_token')
  const res = await fetch('/api/v1/repair/ppt-export/export', {
    method:  'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization:  token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`匯出失敗：${res.status} ${text}`)
  }

  const prefix   = MODULE_FILENAME_PREFIX[payload.module] ?? payload.module
  const filename = `${prefix}${payload.month}月報告.pptx`

  const blob = await res.blob()
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
