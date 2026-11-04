"""
樓層巡檢圖 Provider — 商場例行維護（mall_periodic_maintenance，頁面 /mall/periodic-maintenance）

資料：mall_pm_batch／mall_pm_batch_item（Ragic periodic-maintenance/18、/24）
判定與裁示：見 periodic_maintenance_common.py、docs/SPEC_floor_map_periodic_maintenance.md
"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.models.mall_periodic_maintenance import MallPeriodicMaintenanceBatch, MallPeriodicMaintenanceItem
from app.services.floor_map.pm_seed import PM_FLOORS
from app.services.floor_map.providers.periodic_maintenance_common import PeriodicMaintenanceFloorMapProvider


class MallPeriodicMaintenanceProvider(PeriodicMaintenanceFloorMapProvider):
    module          = "mall_periodic_maintenance"
    label           = "商場例行維護"
    view_permission = "mall_periodic_maintenance_view"
    edit_permission = "mall_periodic_maintenance_floor_map_edit"
    floors          = PM_FLOORS["mall_periodic_maintenance"]
    default_floor   = "1f"
    batch_model     = MallPeriodicMaintenanceBatch
    item_model      = MallPeriodicMaintenanceItem

    def _item_url(self, item: Any) -> str:
        # 與模組畫面同一套規則（優先 Sheet 24 該筆項目）
        from app.routers.mall_periodic_maintenance import _item_ragic_url
        return _item_ragic_url(item.ragic_id, getattr(item, "sheet24_id", None))

    def _full_date(self, scheduled_date: str, period_month: str) -> date | None:
        from app.routers.mall_periodic_maintenance import _reconstruct_full_date
        return _reconstruct_full_date(scheduled_date, period_month)
