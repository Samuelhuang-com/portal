"""商場工務巡檢樓層圖：4F 的待定位點位（配電室、預冷空調箱）

Revision ID: mallfi2
Revises: mallfi1
Create Date: 2026-10-30

2026-10-30 Samuel 裁示：商場工務巡檢新增 4F（現行 Sheet 27）。圖尚未提供，地圖空白，
但資料要出現，因此新增兩個待定位點位（座標暫定，之後可在編輯點位拖曳）。
只在該 source_ref 尚未有點位時寫入（可重跑）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.time import twnow

revision: str = "mallfi2"
down_revision: Union[str, None] = "mallfi1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "floor_map_points"
MODULE = "mall_facility_inspection"

# (label, source_ref, 待定位序號)
_SEED = [
    ("配電室",     "4f|配電室",     0),
    ("預冷空調箱", "4f|預冷空調箱", 1),
]


def _q(i: int) -> tuple[float, float]:
    return 0.04, round(0.07 + 0.065 * i, 3)


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE):
        return
    now = twnow()
    tbl = sa.table(TABLE, *(sa.column(c) for c in (
        "module", "floor_key", "x", "y", "label", "source_ref", "placement", "note",
        "sort_order", "is_active", "created_by", "updated_by", "created_at", "updated_at",
    )))
    rows = []
    for i, (label, ref, pos) in enumerate(_SEED):
        exists = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {TABLE} WHERE module = :m AND source_ref = :r"),
            {"m": MODULE, "r": ref},
        ).scalar() or 0
        if exists:
            continue
        x, y = _q(pos)
        rows.append({
            "module": MODULE, "floor_key": "4f", "x": x, "y": y, "label": label, "source_ref": ref,
            "placement": "pending", "note": "待定位：4F 底圖尚未提供，請用編輯點位拖到正確位置",
            "sort_order": 100 + i, "is_active": True,
            "created_by": "migration:mallfi2", "updated_by": "migration:mallfi2",
            "created_at": now, "updated_at": now,
        })
    if rows:
        op.bulk_insert(tbl, rows)


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(TABLE):
        bind.execute(sa.text(f"DELETE FROM {TABLE} WHERE module = :m AND created_by = 'migration:mallfi2'"),
                     {"m": MODULE})
