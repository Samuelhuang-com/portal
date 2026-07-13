/**
 * 商場行事曆 — /mall/calendar
 * 顯示 zone="商場" 的事件，另外也納入 zone="公區"（全棟例行維護 full_pm、
 * 全棟主管排定 pm_plan 都掛在這個 zone，2026-07-13 修正前這裡漏接，導致
 * mall/full-building-maintenance 模組的排定日期完全不會出現在這個行事曆）。
 * 事件類型：mall_pm / full_pm / pm_plan / custom
 */
import VenueCalendarPage from '@/components/Calendar/VenueCalendarPage'

export default function MallCalendarPage() {
  return <VenueCalendarPage fixedZone="商場" />
}
