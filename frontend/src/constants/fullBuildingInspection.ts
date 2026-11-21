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
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/5',
    description: '整棟工務 RF 層（屋頂層）設施每日例行巡檢',
    color:       '#1B3A5C',
  },
  b4f: {
    key:         'b4f',
    floor:       'B4F',
    title:       '整棟工務每日巡檢 - B4F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/9',
    description: '整棟工務 B4F 地下 4 樓設施每日例行巡檢',
    color:       '#4BA8E8',
  },
  b2f: {
    key:         'b2f',
    floor:       'B2F',
    title:       '整棟工務每日巡檢 - B2F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/7',
    description: '整棟工務 B2F 地下 2 樓設施每日例行巡檢',
    color:       '#52C41A',
  },
  b1f: {
    key:         'b1f',
    floor:       'B1F',
    title:       '整棟工務每日巡檢 - B1F',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/6',
    description: '整棟工務 B1F 地下 1 樓設施每日例行巡檢',
    color:       '#722ed1',
  },
  b1b4: {
    key:         'b1b4',
    floor:       'B1~B4',
    title:       '整棟巡檢 - B1-B4F抽排風設備',
    ragicUrl:    'https://ap12.ragic.com/soutlet001/full-building-inspection/8',
    description: '整棟工務 B1～B4 抽排風設備每日例行巡檢（新樓層，獨立表）',
    color:       '#fa8c16',
  },
}

export const FULL_BUILDING_INSPECTION_SHEET_LIST = Object.values(FULL_BUILDING_INSPECTION_SHEETS)

// ── 各樓層對應的 Ragic 表單（「Ragic 表單」連結列、子表 TAB 使用；B4F 含四張子表）──

export interface RagicSheetLink {
  sourceKey: string  // 來源 Sheet 鍵（同 inspection_sources.py 的 sheet_key，如 b4f_9）
  label:     string  // 表單名稱（與 Ragic 表單內容一致）
  url:       string  // Ragic 表單網址
}

const RAGIC_FBI_BASE = 'https://ap12.ragic.com/soutlet001/full-building-inspection'

export const FULL_BUILDING_RAGIC_SHEET_LINKS: Record<string, RagicSheetLink[]> = {
  rf: [
    { sourceKey: 'rf_5', label: 'RF冷卻水塔、上水塔', url: `${RAGIC_FBI_BASE}/5` },
  ],
  b1f: [
    { sourceKey: 'b1f_6', label: 'B1F發電機、高壓機房、電信、瓦斯設備', url: `${RAGIC_FBI_BASE}/6` },
  ],
  b2f: [
    { sourceKey: 'b2f_7', label: 'B2F油脂截流槽', url: `${RAGIC_FBI_BASE}/7` },
  ],
  b4f: [
    { sourceKey: 'b4f_9',  label: 'B4F 冰水主機、冰水泵、冷卻水泵', url: `${RAGIC_FBI_BASE}/9` },
    { sourceKey: 'b4f_10', label: 'B4F 連續壁',                     url: `${RAGIC_FBI_BASE}/10` },
    { sourceKey: 'b4f_11', label: 'B4F 汙廢水',                     url: `${RAGIC_FBI_BASE}/11` },
    { sourceKey: 'b4f_12', label: 'B4F 下水塔',                     url: `${RAGIC_FBI_BASE}/12` },
  ],
  b1b4: [
    { sourceKey: 'b1b4_8', label: 'B1-B4F抽排風設備', url: `${RAGIC_FBI_BASE}/8` },
  ],
}

// ── 多 Sheet 來源（與 backend app/services/inspection_sources.py 的 SOURCES 同步維護）──
// 場次 ID 格式：{sheet_key}_{Ragic Row ID}，例：b4f_9_0
export const INSPECTION_SHEET_PATHS: Record<string, string> = {
  rf_1:   'archive-old-data/19',
  rf_5:   'full-building-inspection/5',
  b1f_4:  'archive-old-data/22',
  b1f_6:  'full-building-inspection/6',
  b2f_3:  'archive-old-data/21',
  b2f_7:  'full-building-inspection/7',
  b4f_2:  'archive-old-data/20',
  b4f_9:  'full-building-inspection/9',
  b4f_10: 'full-building-inspection/10',
  b4f_11: 'full-building-inspection/11',
  b4f_12: 'full-building-inspection/12',
  b1b4_8: 'full-building-inspection/8',
}

/** 場次 ID → Ragic 原始紀錄直連網址（找不到來源時回空字串）。 */
export function ragicRecordUrl(batchId: string): string {
  const idx = batchId.lastIndexOf('_')
  if (idx <= 0) return ''
  const path = INSPECTION_SHEET_PATHS[batchId.slice(0, idx)]
  return path ? `https://ap12.ragic.com/soutlet001/${path}/${batchId.slice(idx + 1)}` : ''
}
