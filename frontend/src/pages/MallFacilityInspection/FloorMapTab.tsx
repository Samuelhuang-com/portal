/**
 * ［相容層］商場工務巡檢「樓層巡檢圖」TAB
 *
 * 2026-10-04 共用化後，實作移到 components/FloorPlanMap/FloorMapWorkspace（CLAUDE.md §12、
 * docs/DEV_SPEC_floor_plan_map.md）。index.tsx 已直接使用共用元件；這支只保留檔名以免外部 import 失敗。
 */
import FloorMapWorkspace from '@/components/FloorPlanMap/FloorMapWorkspace'

export default function FloorMapTab() {
  return <FloorMapWorkspace module="mall_facility_inspection" />
}
