"""樓層巡檢圖：mall_floor_map_points 點位表＋草稿點位

Revision ID: mflmap
Revises: audchkt
Create Date: 2026-10-04

背景
────────────────────────────────────────────────────────────────────────────
商場工務巡檢新增「樓層巡檢圖」TAB（規格 docs/SPEC_floor_plan_inspection.md）。
純新增一張表，不動任何既有表。PostgreSQL 方言（CLAUDE.md §0）。

草稿點位（2026-10-04 使用者裁示「依 Excel 機房位置放草稿」）
────────────────────────────────────────────────────────────────────────────
來源：myDoc/平面圖/20261003飯店及商場空調設備位置及供應區域.xlsx（商場、與 2.2 每日巡檢表
有對應 Ragic 欄位的設備）。位置只是依「機房位置／供應區域」在底圖上概估：
  - 能從底圖認出區域的（如 3-04、3-06、卸貨區、停車場）→ 放在該區附近
  - 底圖上看不出位置的（如「2F空調機房」「1F廁所後方」）→ 排在圖左上「待定位」一列
現場要用「編輯點位」拖到正確位置。

⚠️ 可重跑：
   - 表／索引先檢查存在才建（main.py 的 create_all 可能已先建表）
   - 草稿只在「整張表一筆都沒有」時才寫入；有人放過點就不再動
   兩區（測試／正式網路不通）各自跑一次 alembic upgrade 即各自有草稿。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.time import twnow


revision: str = "mflmap"
down_revision: Union[str, None] = "audchkt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "mall_floor_map_points"


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _ensure_index(name: str, table: str, cols: list) -> None:
    existing = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, cols, unique=False)


_PENDING = "待定位：底圖上看不出「{loc}」位置，請用編輯點位拖到正確位置"
_DRAFT   = "草稿：依空調設備位置表的機房位置「{loc}」概估，請現場校正"


def _q(i: int) -> tuple[float, float]:
    """「待定位」一列的位置（圖左上往下排）。"""
    return 0.04, round(0.07 + 0.065 * i, 3)


# floor_key, x, y, label, code, sheet_key, item, location_desc, supply_area, pending?
_SEED = [
    # ── 3F ───────────────────────────────────────────────────────────────
    ("3f", 0.33, 0.27, "靜電機",          "靜電機",  "3f",      "靜電機",     "3-04空調機房",   "3-01.3-02.3-03.3-04.2-04", False),
    ("3f", 0.37, 0.31, "AH-R33 空調箱",   "AH-R33",  "1f-3f",   "空調箱",     "3-04空調機房",   "3-04", False),
    ("3f", 0.23, 0.60, "AH-R31 空調箱",   "AH-R31",  "1f-3f",   "空調箱",     "3F九華樓廚房",   "3-01+3-02a+3-02b", False),
    ("3f", 0.66, 0.62, "AH-R34 空調箱",   "AH-R34",  "1f-3f",   "空調箱",     "3-06空調機房",   "3-05a+3-05b+3-06(部分使用)", False),
    # ── 2F ───────────────────────────────────────────────────────────────
    ("2f", 0.80, 0.62, "AH-R26 空調箱",   "AH-R26",  "1f-3f",   "空調箱",     "2F雅室廚房",     "2-05+06+公區", False),
    ("2f", 0.85, 0.57, "AH-R27 空調箱（供 1F）", "AH-R27", "1f-3f", "空調箱",  "2F雅室廚房",     "1-11+12+公區", False),
    ("2f", None, 0,    "AH-R21 空調箱（供 1F）", "AH-R21", "1f-3f", "空調箱",  "2F空調機房",     "1-01+02+公區", True),
    ("2f", None, 1,    "AH-R23 空調箱（供 1F）", "AH-R23", "1f-3f", "空調箱",  "2F空調機房",     "1-03+04+公區", True),
    ("2f", None, 2,    "AH-R22 空調箱",   "AH-R22",  "1f-3f",   "空調箱",     "2F空調機房",     "2-01+公區", True),
    ("2f", None, 3,    "AH-R24 空調箱",   "AH-R24",  "1f-3f",   "空調箱",     "2F空調機房",     "2-02+03+公區", True),
    ("2f", None, 4,    "AH-R25 空調箱",   "AH-R25",  "1f-3f",   "空調箱",     "2F空調機房",     "2-04+公區", True),
    # ── 1F ───────────────────────────────────────────────────────────────
    ("1f", None, 0,    "水洗機",          "水洗機",  "1f",      "水洗機",     "1F廁所後方",     "1F櫃位及中島", True),
    ("1f", None, 1,    "AH-R32 空調箱",   "AH-R32",  "1f-3f",   "空調箱",     "1FB梯",          "1F中島公區", True),
    ("1f", None, 2,    "PAH-R21 空調箱",  "PAH-R21", "1f-3f",   "空調箱",     "小後院廚房上方", "小後苑", True),
    # ── B1F ──────────────────────────────────────────────────────────────
    ("b1f", 0.26, 0.42, "SF-B12 送風機",  "SF-B12",  "b1f-b4f", "抽排風設備", "B1停車場",       "B1驗收區", False),
    ("b1f", 0.55, 0.62, "EF-B11 排風機",  "EF-B11",  "b1f-b4f", "抽排風設備", "B1停車場",       "B1停車場", False),
    ("b1f", None, 0,    "EF-HB12 排風機", "EF-HB12", "b1f-b4f", "抽排風設備", "B1機房",         "B1垃圾處理室", True),
    ("b1f", None, 1,    "EF-RB11 排風機", "EF-RB11", "b1f-b4f", "抽排風設備", "B1機房",         "B1垃圾處理室", True),
    ("b1f", None, 2,    "電信設備",       None,      "b1f-b4f", "電信設備",   "未登載",         None, True),
    # ── B2F～B4F ─────────────────────────────────────────────────────────
    ("b2f", 0.55, 0.55, "EF-B21 排風機",  "EF-B21",  "b1f-b4f", "抽排風設備", "B2停車場",       "B2停車場", False),
    ("b3f", 0.55, 0.55, "EF-B31 排風機",  "EF-B31",  "b1f-b4f", "抽排風設備", "B3停車場",       "B3停車場", False),
    ("b4f", 0.55, 0.55, "EF-B41 排風機",  "EF-B41",  "b1f-b4f", "抽排風設備", "B4停車場",       "B4停車場", False),
]


def upgrade() -> None:
    if not _has_table(TABLE):
        op.create_table(
            TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("floor_key", sa.String(length=20), nullable=False, comment="樓層 key：1f / 2f / 3f / b1f / b2f / b3f / b4f"),
            sa.Column("x", sa.Float(), nullable=False, comment="水平位置比例 0～1（左→右）"),
            sa.Column("y", sa.Float(), nullable=False, comment="垂直位置比例 0～1（上→下）"),
            sa.Column("label", sa.String(length=100), nullable=False, comment="顯示名稱"),
            sa.Column("equipment_code", sa.String(length=50), nullable=True, comment="設備編號"),
            sa.Column("sheet_key", sa.String(length=20), nullable=False, comment="Ragic 來源 Sheet"),
            sa.Column("item", sa.String(length=50), nullable=False, comment="設備組（2.2 每日巡檢表的項目）"),
            sa.Column("location_desc", sa.String(length=100), nullable=True, comment="機房位置"),
            sa.Column("supply_area", sa.String(length=200), nullable=True, comment="供應區域"),
            sa.Column("note", sa.String(length=300), nullable=True, comment="備註"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("updated_by", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    _ensure_index("ix_mall_floor_map_points_floor", TABLE, ["floor_key", "is_active"])

    bind = op.get_bind()
    count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {TABLE}")).scalar() or 0
    if count:
        return

    now = twnow()
    tbl = sa.table(
        TABLE,
        *(sa.column(c) for c in (
            "floor_key", "x", "y", "label", "equipment_code", "sheet_key", "item",
            "location_desc", "supply_area", "note", "sort_order", "is_active",
            "created_by", "updated_by", "created_at", "updated_at",
        )),
    )
    rows = []
    for i, (fk, x, y, label, code, sk, item, loc, supply, pending) in enumerate(_SEED):
        if pending:
            x, y = _q(int(y))
            note = _PENDING.format(loc=loc)
        else:
            note = _DRAFT.format(loc=loc)
        rows.append({
            "floor_key": fk, "x": x, "y": y, "label": label, "equipment_code": code,
            "sheet_key": sk, "item": item, "location_desc": loc, "supply_area": supply,
            "note": note, "sort_order": i, "is_active": True,
            "created_by": "migration:mflmap", "updated_by": "migration:mflmap",
            "created_at": now, "updated_at": now,
        })
    op.bulk_insert(tbl, rows)


def downgrade() -> None:
    if _has_table(TABLE):
        op.drop_table(TABLE)
