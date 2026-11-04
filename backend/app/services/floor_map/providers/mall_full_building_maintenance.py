"""
樓層巡檢圖 Provider — 全棟例行維護（mall_full_building_maintenance，頁面 /mall/full-building-maintenance）

資料：full_bldg_pm_batch／full_bldg_pm_batch_item（Ragic periodic-maintenance/21、/28）
判定與裁示：見 periodic_maintenance_common.py、docs/SPEC_floor_map_periodic_maintenance.md
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.models.full_building_maintenance import FullBldgPMBatch, FullBldgPMItem
from app.services.floor_map.pm_seed import PM_FLOORS
from app.services.floor_map.providers.periodic_maintenance_common import PeriodicMaintenanceFloorMapProvider


class MallFullBuildingMaintenanceProvider(PeriodicMaintenanceFloorMapProvider):
    module          = "mall_full_building_maintenance"
    label           = "全棟例行維護"
    view_permission = "mall_full_building_maintenance_view"
    edit_permission = "mall_full_building_maintenance_floor_map_edit"
    floors          = PM_FLOORS["mall_full_building_maintenance"]
    default_floor   = "1f"
    batch_model     = FullBldgPMBatch
    item_model      = FullBldgPMItem

    def _item_url(self, item: Any) -> str:
        # 與模組畫面同一套規則（Sheet 28 該筆項目）
        from app.routers.full_building_maintenance import _RAGIC_ITEM_BASE
        return f"{_RAGIC_ITEM_BASE}/{item.ragic_id}" if item.ragic_id else ""

    def _full_date(self, scheduled_date: str, period_month: str) -> date | None:
        from app.routers.full_building_maintenance import _reconstruct_full_date
        return _reconstruct_full_date(scheduled_date, period_month)
