/**
 * 飯店每日巡檢 — Sheet 設定常數
 * 對應 Ragic 各區域巡檢表 URL
 *
 * Ragic 來源：https://ap12.ragic.com/soutlet001/main-project-inspection
 */

export interface HotelDailyInspectionSheet {
  key:         string  // route key，對應 /hotel/daily-inspection/:key
  floor:       string  // 區域顯示名稱
  title:       string  // 頁面完整標題
  ragicUrl:    string  // 對應 Ragic 表單 URL
  description: string  // 頁面說明
  color:       string  // 卡片主色
}

export const HOTEL_DAILY_INSPECTION_SHEETS: Record<string, HotelDailyInspectionSheet> = {
  'rf': {
    key:         'rf',
    floor:       'RF',
    title:       '飯店每日巡檢 - RF',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/main-project-inspection/17',
    description: '飯店屋頂層設施每日例行巡檢',
    color:       '#1B3A5C',
  },
  '4f-10f': {
    key:         '4f-10f',
    floor:       '4F ~ 10F',
    title:       '飯店每日巡檢 - 4F-10F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/main-project-inspection/18',
    description: '飯店 4 樓至 10 樓設施每日例行巡檢',
    color:       '#4BA8E8',
  },
  '4f': {
    key:         '4f',
    floor:       '4F',
    title:       '飯店每日巡檢 - 4F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/main-project-inspection/19?PAGEID=BAG',
    description: '飯店 4 樓設施每日例行巡檢',
    color:       '#52C41A',
  },
  '2f': {
    key:         '2f',
    floor:       '2F',
    title:       '飯店每日巡檢 - 2F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/main-project-inspection/20',
    description: '飯店 2 樓設施每日例行巡檢',
    color:       '#722ed1',
  },
  '1f': {
    key:         '1f',
    floor:       '1F',
    title:       '飯店每日巡檢 - 1F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/main-project-inspection/21',
    description: '飯店 1 樓設施每日例行巡檢',
    color:       '#d46b08',
  },
}

export const HOTEL_DAILY_INSPECTION_SHEET_LIST = Object.values(HOTEL_DAILY_INSPECTION_SHEETS)
