"""
整棟工務每日巡檢 - B1F 同步服務（薄包裝）

資料來源：inspection_sources.SOURCES 中 floor == "b1f" 的所有 Ragic Sheet
（含封存來源）。同步邏輯集中在 inspection_sync_core.py。
"""
import logging

from app.models.b1f_inspection import B1FInspectionBatch, B1FInspectionItem
from app.services.inspection_sync_core import sync_floor_sources
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

FLOOR = "b1f"


@register("b1f_inspection")
async def sync_from_ragic() -> dict:
    """從 B1F 所有來源 Sheet 同步場次與設備項目。"""
    return await sync_floor_sources(FLOOR, B1FInspectionBatch, B1FInspectionItem, log_tag="B1FSync")
