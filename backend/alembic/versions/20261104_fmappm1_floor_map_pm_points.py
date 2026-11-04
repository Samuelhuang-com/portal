"""樓層巡檢圖：商場例行維護／全棟例行維護的待定位點位（2026-11-04）

Revision ID: fmappm1
Revises: devlog2
Create Date: 2026-11-04

新增 TAB「樓層巡檢圖」到 /mall/periodic-maintenance 與 /mall/full-building-maintenance。
點位清單來自 Samuel 提供的兩份 Excel（services/floor_map/pm_seed.py），全部「待定位」排在圖左上，
上線後在畫面上拖曳定位。只在該模組一筆點位都沒有時寫入（與啟動步驟 _ensure_floor_map_data 共用
seed_pm_points，兩邊可重跑、不會重複）。不改任何資料表結構。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fmappm1"
down_revision: Union[str, None] = "devlog2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.services.floor_map.pm_seed import PM_ITEMS, TABLE, seed_pm_points

    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE):
        return
    for module in PM_ITEMS:
        seed_pm_points(bind, module, tag="migration:fmappm1")


def downgrade() -> None:
    # 只移除本次寫入、且使用者尚未在畫面上動過的點（updated_by 仍是寫入標記）
    bind = op.get_bind()
    if sa.inspect(bind).has_table("floor_map_points"):
        bind.execute(sa.text(
            "DELETE FROM floor_map_points "
            "WHERE module IN ('mall_periodic_maintenance', 'mall_full_building_maintenance') "
            "AND created_by IN ('migration:fmappm1', 'startup:mall_periodic_maintenance', "
            "'startup:mall_full_building_maintenance') AND updated_by = created_by"
        ))
