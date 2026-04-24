/**
 * 整棟巡檢 — Sheet 設定常數
 * 對應 Ragic full-building-inspection 各樓層巡檢表 URL
 *
 * Ragic 來源：https://ap12.ragic.com/soutlet001/full-building-inspection
 */

export interface FullBuildingInspectionSheet {
  key:         string  // route key，對應 /full-building-inspection/:key
  floor:       string  // 樓層顯示名稱
  title:       string  // 頁面完整標題
  ragicUrl:    string  // 對應 Ragic 表單 URL
  description: string  // 頁面說明
  color:       string  // 主色
}

export const FULL_BUILDING_INSPECTION_SHEETS: Record<string, FullBuildingInspectionSheet> = {
  rf: {
    key:         'rf',
    floor:       'RF',
    title:       '整棟工務每日巡檢 - RF',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/1?PAGEID=i4T',
    description: '整棟工務 RF 層（屋頂層）設施每日例行巡檢',
    color:       '#1B3A5C',
  },
  b4f: {
    key:         'b4f',
    floor:       'B4F',
    title:       '整棟工務每日巡檢 - B4F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/2?PAGEID=i4T',
    description: '整棟工務 B4F 地下 4 樓設施每日例行巡檢',
    color:       '#4BA8E8',
  },
  b2f: {
    key:         'b2f',
    floor:       'B2F',
    title:       '整棟工務每日巡檢 - B2F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/3?PAGEID=i4T',
    description: '整棟工務 B2F 地下 2 樓設施每日例行巡檢',
    color:       '#52C41A',
  },
  b1f: {
    key:         'b1f',
    floor:       'B1F',
    title:       '整棟工務每日巡檢 - B1F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/4?PAGEID=i4T',
    description: '整棟工務 B1F 地下 1 樓設施每日例行巡檢',
    color:       '#722ed1',
  },
}

export const FULL_BUILDING_INSPECTION_SHEET_LIST = Object.values(FULL_BUILDING_INSPECTION_SHEETS)
