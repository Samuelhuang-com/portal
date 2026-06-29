/**
 * 商場行事曆 — /mall/calendar
 * 只顯示 zone="商場" 的事件（mall_pm / inspection / pm_plan / custom）
 */
import VenueCalendarPage from '@/components/Calendar/VenueCalendarPage'

export default function MallCalendarPage() {
  return <VenueCalendarPage fixedZone="商場" />
}
