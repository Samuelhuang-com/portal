"""
樓層巡檢圖 Provider 註冊表（DEV_SPEC §5）

新模組：新增 providers/{module}.py（繼承 FloorMapProvider），在下方 PROVIDERS 加一行。
"""
from __future__ import annotations

from app.services.floor_map.providers.base import FloorMapProvider
from app.services.floor_map.providers.full_building_inspection import FullBuildingInspectionProvider
from app.services.floor_map.providers.mall_facility_inspection import MallFacilityInspectionProvider

PROVIDERS: dict[str, FloorMapProvider] = {
    p.module: p
    for p in (
        MallFacilityInspectionProvider(),
        FullBuildingInspectionProvider(),
    )
}


def get_provider(module: str) -> FloorMapProvider | None:
    return PROVIDERS.get(module)
