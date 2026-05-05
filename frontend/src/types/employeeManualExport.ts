// ── 員工操作手冊匯出 — TypeScript 型別定義 ─────────────────────────────────────

export interface ModuleInfo {
  key: string
  name: string
  description: string
  menu_path: string
}

export interface GenerateRequest {
  module_key: string
  doc_types: string[]
  export_format?: 'zip' | 'markdown'
}

export interface GenerateResult {
  module_key: string
  module_name: string
  generated_files: string[]
  export_path: string
  generated_at: string
  download_url: string
}

export interface ExportStatus {
  module_key: string
  module_name?: string
  has_export: boolean
  generated_at: string | null
  files: string[]
  download_url: string | null
}

// 文件種類定義（與後端 DOC_TYPE_MAP 對應）
export const DOC_TYPE_OPTIONS = [
  { key: 'manual',       label: '員工操作手冊',  filename: '01_員工操作手冊.md' },
  { key: 'supervisor',   label: '主管快速導覽',  filename: '02_主管快速導覽.md' },
  { key: 'faq',          label: '常見問題 FAQ',  filename: '03_常見問題FAQ.md' },
  { key: 'training',     label: '教育訓練講稿',  filename: '04_教育訓練講稿.md' },
  { key: 'voice',        label: '語音教學腳本',  filename: '05_語音教學腳本.md' },
  { key: 'newbie',       label: '新人入門教學',  filename: '06_新人入門教學.md' },
  { key: 'troubleshoot', label: '異常狀況處理',  filename: '07_異常狀況處理.md' },
] as const

export type DocTypeKey = typeof DOC_TYPE_OPTIONS[number]['key']
