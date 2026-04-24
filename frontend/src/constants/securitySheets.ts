/**
 * 保全巡檢 Sheet 設定常數
 * 對應後端 SHEET_CONFIGS
 */
export interface SecuritySheetConfig {
  key:  string
  id:   number
  name: string
  path: string
}

export const SECURITY_SHEETS: Record<string, SecuritySheetConfig> = {
  'b1f-b4f': {
    key:  'b1f-b4f',
    id:   1,
    name: '保全每日巡檢 - B1F~B4F夜間巡檢',
    path: 'security-patrol/1',
  },
  '1f-3f': {
    key:  '1f-3f',
    id:   2,
    name: '保全巡檢 - 1F ~ 3F (夜間巡檢)',
    path: 'security-patrol/2',
  },
  '5f-10f': {
    key:  '5f-10f',
    id:   3,
    name: '保全巡檢 - 5F ~ 10F (夜間巡檢)',
    path: 'security-patrol/3',
  },
  '4f': {
    key:  '4f',
    id:   4,
    name: '保全巡檢 - 4F (夜間巡檢)',
    path: 'security-patrol/4',
  },
  '1f-hotel': {
    key:  '1f-hotel',
    id:   5,
    name: '保全巡檢 - 1F夜間巡檢 (飯店大廳)',
    path: 'security-patrol/5',
  },
  '1f-close': {
    key:  '1f-close',
    id:   6,
    name: '保全巡檢 - 1F 閉店巡檢',
    path: 'security-patrol/6',
  },
  '1f-open': {
    key:  '1f-open',
    id:   9,
    name: '保全巡檢 - 1F 開店準備',
    path: 'security-patrol/9',
  },
}

export const SECURITY_SHEET_LIST = Object.values(SECURITY_SHEETS)
