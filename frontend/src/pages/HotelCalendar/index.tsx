/**
 * 飯店行事曆 — /hotel/calendar
 * 只顯示 zone="飯店" 的事件（hotel_pm / pm_plan / custom）
 */
import VenueCalendarPage from '@/components/Calendar/VenueCalendarPage'

export default function HotelCalendarPage() {
  return <VenueCalendarPage fixedZone="飯店" />
}
