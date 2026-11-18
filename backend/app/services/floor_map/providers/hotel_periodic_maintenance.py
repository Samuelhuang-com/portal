"""
樓層巡檢圖 Provider — 飯店例行維護（hotel_periodic_maintenance，頁面 /hotel/periodic-maintenance）

2026-11-18 新增。資料：pm_batch／pm_batch_item（Ragic Sheet 11，2026-07-14 起為正式來源）。
點位清單：myDoc/平面圖/飯店例行維護_樓層維護圖.xlsx（pm_seed.PM_ITEMS／PM_PARENTS 轉出）。
飯店清單的「樓層」欄：Excel 標準值優先，其餘依項目名稱推定（1F／4樓／B1／RF 等），仍不可判定者不放點，
母項列在「未對應」，由 Samuel 在畫面上新增點位並拖曳定位。（2026-11-18 修正：原本全部不放點，畫面沒有可編輯的點位。）
判定與裁示：見 periodic_maintenance_common.py、docs/SPEC_floor_map_periodic_maintenance.md
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.models.periodic_maintenance import PeriodicMaintenanceBatch, PeriodicMaintenanceItem
from app.services.floor_map.pm_seed import PM_FLOORS
from app.services.floor_map.providers.periodic_maintenance_common import PeriodicMaintenanceFloorMapProvider


class HotelPeriodicMaintenanceProvider(PeriodicMaintenanceFloorMapProvider):
    module          = "hotel_periodic_maintenance"
    label           = "飯店例行維護"
    view_permission = "hotel_periodic_maintenance_view"
    edit_permission = "hotel_periodic_maintenance_floor_map_edit"
    floors          = PM_FLOORS["hotel_periodic_maintenance"]
    default_floor   = "1f"
    batch_model     = PeriodicMaintenanceBatch
    item_model      = PeriodicMaintenanceItem

    def _item_url(self, item: Any) -> str:
        # 與模組畫面同一套規則（Sheet 11 項目 _ragicId 直連）
        from app.routers.periodic_maintenance import _ITEM_RAGIC_BASE
        return f"{_ITEM_RAGIC_BASE}/{item.ragic_id}" if item.ragic_id else ""

    def _full_date(self, scheduled_date: str, period_month: str) -> date | None:
        from app.routers.periodic_maintenance import _reconstruct_full_date
        return _reconstruct_full_date(scheduled_date, period_month)
