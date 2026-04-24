/**
 * 春大直商場工務巡檢 — Sheet 設定常數
 * 對應 Ragic 各樓層巡檢表 URL
 *
 * Ragic 來源：https://ap12.ragic.com/soutlet001/mall-facility-inspection
 */

export interface MallFacilityInspectionSheet {
  key:         string  // route key，對應 /mall-facility-inspection/:key
  floor:       string  // 樓層顯示名稱
  title:       string  // 頁面完整標題
  ragicUrl:    string  // 對應 Ragic 表單 URL
  description: string  // 頁面說明
  color:       string  // 卡片主色
}

export const MALL_FACILITY_INSPECTION_SHEETS: Record<string, MallFacilityInspectionSheet> = {
  '4f': {
    key:         '4f',
    floor:       '4F',
    title:       '商場工務每日巡檢 - 4F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/mall-facility-inspection/2?PAGEID=i4T',
    description: '春大直商場 4 樓工務設施每日例行巡檢',
    color:       '#1B3A5C',
  },
  '3f': {
    key:         '3f',
    floor:       '3F',
    title:       '商場工務每日巡檢 - 3F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/mall-facility-inspection/3?PAGEID=i4T',
    description: '春大直商場 3 樓工務設施每日例行巡檢',
    color:       '#4BA8E8',
  },
  '1f-3f': {
    key:         '1f-3f',
    floor:       '1F ~ 3F',
    title:       '商場工務每日巡檢 - 1F ~ 3F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/mall-facility-inspection/4?PAGEID=i4T',
    description: '春大直商場 1F 至 3F 工務設施每日例行巡檢',
    color:       '#52C41A',
  },
  '1f': {
    key:         '1f',
    floor:       '1F',
    title:       '商場工務每日巡檢 - 1F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/mall-facility-inspection/5?PAGEID=i4T',
    description: '春大直商場 1 樓工務設施每日例行巡檢',
    color:       '#722ed1',
  },
  'b1f-b4f': {
    key:         'b1f-b4f',
    floor:       'B1F ~ B4F',
    title:       '商場工務每日巡檢 - B1F ~ B4F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/mall-facility-inspection/7?PAGEID=i4T',
    description: '春大直商場地下 1 至 4 樓工務設施每日例行巡檢',
    color:       '#d46b08',
  },
}

export const MALL_FACILITY_INSPECTION_SHEET_LIST = Object.values(MALL_FACILITY_INSPECTION_SHEETS)
