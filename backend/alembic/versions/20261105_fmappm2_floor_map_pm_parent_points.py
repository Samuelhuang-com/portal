"""樓層巡檢圖：例行維護類改為母項點位＋子項停用；保養項目新增母項名稱／排定結束日期欄位（2026-11-05）

Revision ID: fmappm2
Revises: fmappm1
Create Date: 2026-11-05

1. mall_pm_batch_item 新增 parent_name、schedule_end_date；full_bldg_pm_batch_item 新增 schedule_end_date
   （nullable；Ragic Sheet24 加「項目母項名稱」「結束日期」、Sheet28 加「結束日期」並重新同步後才有值）
2. 新表 floor_map_disabled_sources（子項停用）
3. 商場例行維護／全棟例行維護：子項點位 → 母項點位（沿用已拖曳過的位置；原子項點位停用、不硬刪；
   已全部停用的子項轉為子項停用）
與啟動步驟 _ensure_floor_map_data 共用 pm_seed.ensure_pm_columns／convert_child_points，可重跑。
PostgreSQL 方言（CLAUDE.md §0）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fmappm2"
down_revision: Union[str, None] = "fmappm1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.services.floor_map.pm_seed import PM_ITEMS, TABLE, convert_child_points, ensure_pm_columns

    bind = op.get_bind()
    ensure_pm_columns(bind)
    if not sa.inspect(bind).has_table(TABLE):
        return
    for module in PM_ITEMS:
        convert_child_points(bind, module, tag="migration:fmappm2")


def downgrade() -> None:
    # 還原點位：刪除本次建立的母項點位、恢復被停用的原子項點位；子項停用表與欄位保留（資料，非結構必要）
    bind = op.get_bind()
    if sa.inspect(bind).has_table("floor_map_points"):
        bind.execute(sa.text(
            "DELETE FROM floor_map_points WHERE module IN ('mall_periodic_maintenance', 'mall_full_building_maintenance') "
            "AND created_by LIKE '%:fmappm2' AND updated_by = created_by"
        ))
        bind.execute(sa.text(
            "UPDATE floor_map_points SET is_active = true WHERE updated_by LIKE '%:fmappm2:retired'"
        ))
