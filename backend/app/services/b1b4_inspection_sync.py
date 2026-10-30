"""
整棟工務每日巡檢 - B1~B4（新樓層）同步服務（薄包裝）

資料來源：inspection_sources.SOURCES 中 floor == "b1b4" 的 Ragic Sheet。
同步邏輯集中在 inspection_sync_core.py。獨立表：b1b4_inspection_batch / b1b4_inspection_item。
"""
import logging

from app.models.b1b4_inspection import B1B4InspectionBatch, B1B4InspectionItem
from app.services.inspection_sync_core import sync_floor_sources
from app.services.sync_dispatcher import register

logger = logging.getLogger(__name__)

FLOOR = "b1b4"


@register("b1b4_inspection")
async def sync_from_ragic() -> dict:
    """從 B1~B4 所有來源 Sheet 同步場次與設備項目。"""
    return await sync_floor_sources(FLOOR, B1B4InspectionBatch, B1B4InspectionItem, log_tag="B1B4Sync")
