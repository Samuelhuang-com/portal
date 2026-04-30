/**
 * 每日數值登錄表 — Sheet 設定常數
 * 對應 Ragic hotel-routine-inspection 各 Sheet URL
 *
 * Ragic 來源：https://ap12.ragic.com/soutlet001/hotel-routine-inspection
 * 注意：Sheet 13 不存在（跳號），直接從 12 跳到 14
 */

export interface HotelMeterReadingsSheet {
  key:         string  // route/tab key
  title:       string  // 頁面顯示標題
  ragicUrl:    string  // 對應 Ragic 表單 URL
  description: string  // 頁面說明
  color:       string  // 卡片主色（使用 portal 品牌色）
  unit:        string  // 儀表單位提示（電=度、水=噸）
}

export const HOTEL_METER_READINGS_SHEETS: Record<string, HotelMeterReadingsSheet> = {
  'building-electric': {
    key:         'building-electric',
    title:       '全棟電錶',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/11',
    description: '全棟電力儀表每日數值登錄',
    color:       '#1B3A5C',
    unit:        '度',
  },
  'mall-ac-electric': {
    key:         'mall-ac-electric',
    title:       '商場空調箱電錶',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/12',
    description: '商場空調箱電力儀表每日數值登錄',
    color:       '#4BA8E8',
    unit:        '度',
  },
  'tenant-electric': {
    key:         'tenant-electric',
    title:       '專櫃電錶',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/14',
    description: '專櫃電力儀表每日數值登錄',
    color:       '#52C41A',
    unit:        '度',
  },
  'tenant-water': {
    key:         'tenant-water',
    title:       '專櫃水錶',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/hotel-routine-inspection/15',
    description: '專櫃水量儀表每日數值登錄',
    color:       '#1890ff',
    unit:        '噸',
  },
}

export const HOTEL_METER_READINGS_SHEET_LIST = Object.values(HOTEL_METER_READINGS_SHEETS)

/** Tab 順序清單（固定 dashboard 第一，其餘依 SHEET_LIST 順序）*/
export const VALID_TABS = [
  'dashboard',
  ...HOTEL_METER_READINGS_SHEET_LIST.map((s) => s.key),
]
