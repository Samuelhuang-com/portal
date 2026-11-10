/**
 * 飯店每日巡檢 — 頁籤設定常數（2026-11-10 改版，比照 constants/mallFacilityInspection.ts）
 *
 * Ragic 來源：https://ap12.ragic.com/soutlet001/main-project-inspection（英迪格飯店工務巡檢）
 * 每個頁籤的 ragicUrl 指向現行（新）表；封存舊表（archive-old-data/31～40）的連結
 * 由後端依場次產生（新舊連結同時存在，見 backend/app/services/hotel_daily_inspection_sources.py）。
 */

export interface HotelDailyInspectionSheet {
  key:         string  // 頁籤 key（= hotel_di_inspection_batch.sheet_key）
  floor:       string  // 頁籤短名稱
  title:       string  // 完整標題
  ragicUrl:    string  // 現行 Ragic 表單 URL
  description: string  // 說明
  color:       string  // 卡片主色
}

const RAGIC = 'https://ap12.ragic.com/soutlet001/main-project-inspection'

export const HOTEL_DAILY_INSPECTION_SHEETS: Record<string, HotelDailyInspectionSheet> = {
  'rf': {
    key: 'rf', floor: 'RF', title: '飯店每日巡檢 - RF 樓層 早班巡檢',
    ragicUrl: `${RAGIC}/17`, description: '冷卻水塔、上水塔、熱水系統、鍋爐設備、RF瓦斯', color: '#1B3A5C',
  },
  '5f-10f': {
    key: '5f-10f', floor: '5-10F', title: '飯店每日巡檢 - 5-10F 客房公共區域',
    ragicUrl: `${RAGIC}/28`, description: '5～10 樓客房走道空調箱', color: '#4BA8E8',
  },
  '4f': {
    key: '4f', floor: '4F', title: '飯店每日巡檢 - 4F BAR-D公區',
    ragicUrl: `${RAGIC}/29`, description: '空調箱、BAR-D 飲水機／製冰機、燈光', color: '#52C41A',
  },
  'b1f-hv': {
    key: 'b1f-hv', floor: 'B1F 高壓機房', title: '飯店每日巡檢 - B1F 高壓機房',
    ragicUrl: `${RAGIC}/30`, description: '高壓機房 11 項', color: '#722ed1',
  },
  'b1f-office': {
    key: 'b1f-office', floor: 'B1F 辦公室／廚房瓦斯', title: '飯店每日巡檢 - B1F 晚班巡檢 辦公室公區、廚房瓦斯設備',
    ragicUrl: `${RAGIC}/31`, description: '辦公室公區、廚房瓦斯設備', color: '#13c2c2',
  },
  'b4f-water': {
    key: 'b4f-water', floor: 'B4F 下水塔', title: '飯店每日巡檢 - B4F 早班巡檢 下水塔',
    ragicUrl: `${RAGIC}/32`, description: '下水塔 7 項', color: '#d46b08',
  },
  'b4f-ac': {
    key: 'b4f-ac', floor: 'B4F 空調機房', title: '飯店每日巡檢 - B4F 晚班巡檢 空調機房',
    ragicUrl: `${RAGIC}/33`, description: '冰水主機等 13 項', color: '#eb2f96',
  },
}

export const HOTEL_DAILY_INSPECTION_SHEET_LIST = Object.values(HOTEL_DAILY_INSPECTION_SHEETS)

/** 頁籤標籤（Tabs 用，與 Ragic 表單名稱一致） */
export const HOTEL_DAILY_INSPECTION_TAB_LABELS: Record<string, string> = {
  'rf':         'RF 樓層 早班巡檢',
  '5f-10f':     '5-10F 客房公共區域',
  '4f':         '4F BAR-D公區',
  'b1f-hv':     'B1F 高壓機房',
  'b1f-office': 'B1F 晚班巡檢 辦公室公區 廚房瓦斯設備',
  'b4f-water':  'B4F 早班巡檢 下水塔',
  'b4f-ac':     'B4F 晚班巡檢 空調機房',
}
