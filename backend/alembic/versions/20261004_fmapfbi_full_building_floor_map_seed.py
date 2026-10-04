"""樓層巡檢圖：整棟巡檢草稿點位

Revision ID: fmapfbi
Revises: fmapgen
Create Date: 2026-10-04

整棟巡檢導入樓層巡檢圖（DEV_SPEC §4.2、§9）。每個設備組一個點，共 10 點：
  - 底圖上看得出位置的 → placement='draft'（RF 冷卻水塔：圖上那排圓形設備；B1F 電力機房：「機電設備空間」）
  - 看不出位置的        → placement='pending'，排在圖左上一列
只在 floor_map_points 沒有任何 module='full_building_inspection' 的點時寫入（可重跑，兩區各跑一次）。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.time import twnow


revision: str = "fmapfbi"
down_revision: Union[str, None] = "fmapgen"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "floor_map_points"
MODULE = "full_building_inspection"


def _q(i: int) -> tuple[float, float]:
    return 0.04, round(0.07 + 0.065 * i, 3)


# floor_key, x, y(或待定位序號), label, source_ref, 機房位置, placement
_SEED = [
    ("rf",  0.57, 0.30, "冷卻水塔",                 "rf|冷卻水塔",                 "頂樓",           "draft"),
    ("rf",  None, 0,    "上水塔",                   "rf|上水塔",                   "頂樓",           "pending"),
    ("b1f", 0.64, 0.61, "電力機房",                 "b1f|電力機房",                "B1F機電設備空間", "draft"),
    ("b1f", None, 0,    "發電機",                   "b1f|發電機",                  "",               "pending"),
    ("b1f", None, 1,    "電信設備",                 "b1f|電信設備",                "",               "pending"),
    ("b2f", None, 0,    "油脂截流槽",               "b2f|油脂截流槽",              "",               "pending"),
    ("b4f", None, 0,    "冰水主機/冰水泵/冷卻水泵", "b4f|冰水主機/冰水泵/冷卻水泵", "B4冰水主機機房", "pending"),
    ("b4f", None, 1,    "連續壁",                   "b4f|連續壁",                  "",               "pending"),
    ("b4f", None, 2,    "汙廢水",                   "b4f|汙廢水",                  "",               "pending"),
    ("b4f", None, 3,    "下水塔",                   "b4f|下水塔",                  "",               "pending"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE):
        return
    n = bind.execute(sa.text(f"SELECT COUNT(*) FROM {TABLE} WHERE module = :m"), {"m": MODULE}).scalar() or 0
    if n:
        return
    now = twnow()
    tbl = sa.table(TABLE, sa.column("attrs", sa.JSON(none_as_null=True)), *(sa.column(c) for c in (
        "module", "floor_key", "x", "y", "label", "source_ref", "placement", "note",
        "sort_order", "is_active", "created_by", "updated_by", "created_at", "updated_at",
    )))
    rows = []
    for i, (fk, x, y, label, ref, loc, placement) in enumerate(_SEED):
        if placement == "pending":
            x, y = _q(int(y))
            note = "待定位：底圖上看不出位置，請用編輯點位拖到正確位置"
        else:
            note = f"草稿：依底圖{('「' + loc + '」') if loc else ''}概估，請現場校正"
        rows.append({
            "module": MODULE, "floor_key": fk, "x": x, "y": y, "label": label, "source_ref": ref,
            "placement": placement, "attrs": {"機房位置": loc} if loc else None, "note": note,
            "sort_order": i, "is_active": True,
            "created_by": "migration:fmapfbi", "updated_by": "migration:fmapfbi",
            "created_at": now, "updated_at": now,
        })
    op.bulk_insert(tbl, rows)


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(TABLE):
        bind.execute(sa.text(f"DELETE FROM {TABLE} WHERE module = :m AND created_by = 'migration:fmapfbi'"),
                     {"m": MODULE})
