"""
整棟工務每日巡檢 - B2F 同步服務（薄包裝）

資料來源：inspection_sources.SOURCES 中 floor == "b2f" 的所有 Ragic Sheet
（含封存來源）。同步邏輯集中在 inspection_sync_core.py。
"""
import logging

from app.models.b2f_inspection import B2FInspectionBatch, B2FInspectionItem
from app.services.inspection_sync_core import sync_floor_sources
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

FLOOR = "b2f"


@register("b2f_inspection")
async def sync_from_ragic() -> dict:
    """從 B2F 所有來源 Sheet 同步場次與設備項目。"""
    return await sync_floor_sources(FLOOR, B2FInspectionBatch, B2FInspectionItem, log_tag="B2FSync")
