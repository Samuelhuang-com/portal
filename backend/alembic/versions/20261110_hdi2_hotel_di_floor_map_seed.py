"""樓層巡檢圖：飯店每日巡檢草稿點位

Revision ID: hdi2
Revises: hdi1
Create Date: 2026-11-10

2026-11-10 Samuel 裁示：飯店每日巡檢樓層巡檢圖照商場做法 —— 依 Excel 主項目自動放一版草稿點位，
再在畫面上拖到正確位置。點位清單在 services/floor_map/bootstrap.py 的 _SEED["hotel_daily_inspection"]
（啟動保底 _ensure_floor_map_data 用同一份）。
只在 floor_map_points 沒有任何 module='hotel_daily_inspection' 的點時寫入（可重跑，兩區各跑一次）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "hdi2"
down_revision: Union[str, None] = "hdi1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MODULE = "hotel_daily_inspection"


def upgrade() -> None:
    from app.services.floor_map.bootstrap import TABLE, _count, _seed
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE):
        return
    if _count(bind, MODULE) == 0:
        _seed(bind, MODULE)


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("floor_map_points"):
        bind.execute(sa.text("DELETE FROM floor_map_points WHERE module = :m AND placement IN ('draft','pending') "
                             "AND created_by = 'startup:hotel_daily_inspection'"), {"m": MODULE})
