/**
 * 樓層巡檢圖 — 四種點位狀態（唯一定義處，DEV_SPEC §5.2、§7.3）
 * 不得在模組內另訂顏色或增加狀態。
 */
export type FloorMapStatus = 'normal' | 'abnormal' | 'unchecked' | 'no_record'

export const FLOOR_MAP_STATUS: Record<FloorMapStatus, { color: string; label: string; mark: string }> = {
  normal:    { color: '#52C41A', label: '正常',   mark: '✓' },
  abnormal:  { color: '#FF4D4F', label: '異常',   mark: '!' },
  unchecked: { color: '#FAAD14', label: '未填',   mark: '?' },
  no_record: { color: '#bfbfbf', label: '無紀錄', mark: '—' },
}

export const FLOOR_MAP_STATUS_KEYS = Object.keys(FLOOR_MAP_STATUS) as FloorMapStatus[]

export type FloorMapPlacement = 'confirmed' | 'draft' | 'pending'

export const PLACEMENT_LABEL: Record<FloorMapPlacement, string> = {
  confirmed: '已校正',
  draft:     '草稿（概估位置）',
  pending:   '待定位',
}
