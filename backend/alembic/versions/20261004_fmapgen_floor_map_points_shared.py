"""樓層巡檢圖共用化：mall_floor_map_points → floor_map_points（加 module／source_ref／placement／attrs）

Revision ID: fmapgen
Revises: mflmap
Create Date: 2026-10-04

背景（docs/DEV_SPEC_floor_plan_map.md §4、§10）
────────────────────────────────────────────────────────────────────────────
第二個模組（整棟巡檢）導入前先共用化：所有模組的點位放同一張表，以 module 區分。
  - 改表名 mall_floor_map_points → floor_map_points
  - 新增 module／source_ref／placement／attrs
  - 回填：module='mall_facility_inspection'、source_ref=sheet_key|item、
          placement 依備註開頭（待定位→pending、草稿→draft、其餘 confirmed）、
          attrs={機房位置, 供應區域}
  - sheet_key／item 改為可空（新模組不填），舊四欄**保留不刪**（CLAUDE.md §5）

PostgreSQL 方言（CLAUDE.md §0）；回填用 Python 逐筆做，不寫方言相依 SQL。

⚠️ 可重跑，且涵蓋三種起始狀態：
   A. 只有舊表（正常升級）            → 改名
   B. 新舊都有（create_all 先建了新表）→ 舊表資料搬進新表（新表已有該模組資料就不搬），舊表保留
   C. 都沒有                          → 直接建新表
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fmapgen"
down_revision: Union[str, None] = "mflmap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD, NEW = "mall_floor_map_points", "floor_map_points"
MODULE = "mall_facility_inspection"


def _insp():
    return sa.inspect(op.get_bind())


def _cols(table: str) -> dict[str, dict]:
    return {c["name"]: c for c in _insp().get_columns(table)}


def _is_pg() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _create_new() -> None:
    op.create_table(
        NEW,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("module", sa.String(length=50), nullable=True, comment="模組代碼＝Provider.module"),
        sa.Column("floor_key", sa.String(length=20), nullable=False, comment="底圖 key"),
        sa.Column("x", sa.Float(), nullable=False, comment="比例座標 0～1（左→右）"),
        sa.Column("y", sa.Float(), nullable=False, comment="比例座標 0～1（上→下）"),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("equipment_code", sa.String(length=50), nullable=True),
        sa.Column("source_ref", sa.String(length=200), nullable=True, comment="資料來源參照"),
        sa.Column("placement", sa.String(length=20), nullable=True, comment="confirmed／draft／pending"),
        sa.Column("attrs", sa.JSON(), nullable=True, comment="模組自訂屬性"),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=100), nullable=True),
        sa.Column("updated_by", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("sheet_key", sa.String(length=20), nullable=True, comment="[舊] 已併入 source_ref"),
        sa.Column("item", sa.String(length=50), nullable=True, comment="[舊] 已併入 source_ref"),
        sa.Column("location_desc", sa.String(length=100), nullable=True, comment="[舊] 已併入 attrs"),
        sa.Column("supply_area", sa.String(length=200), nullable=True, comment="[舊] 已併入 attrs"),
        sa.PrimaryKeyConstraint("id"),
    )


def _placement_from_note(note: str | None) -> str:
    n = (note or "").strip()
    if n.startswith("待定位"):
        return "pending"
    if n.startswith("草稿"):
        return "draft"
    return "confirmed"


def _migrated(r: dict) -> dict:
    """舊表一列 → 新表一列（module／source_ref／placement／attrs 補齊）。"""
    attrs = {k: v for k, v in (("機房位置", r.get("location_desc")), ("供應區域", r.get("supply_area"))) if v}
    return {
        **r,
        "module":     MODULE,
        "source_ref": f"{r.get('sheet_key') or ''}|{r.get('item') or ''}",
        "placement":  _placement_from_note(r.get("note")),
        "attrs":      attrs or None,
    }


def upgrade() -> None:
    bind = op.get_bind()
    has_old, has_new = _insp().has_table(OLD), _insp().has_table(NEW)

    if has_old and not has_new:
        op.rename_table(OLD, NEW)                     # A
    elif not has_new:
        _create_new()                                 # C

    # ── 補欄位（新表若是 create_all 建的，這些都已存在）──────────────────────
    cols = _cols(NEW)
    for name, typ in (
        ("module", sa.String(length=50)), ("source_ref", sa.String(length=200)),
        ("placement", sa.String(length=20)), ("attrs", sa.JSON()),
        ("sheet_key", sa.String(length=20)), ("item", sa.String(length=50)),
        ("location_desc", sa.String(length=100)), ("supply_area", sa.String(length=200)),
    ):
        if name not in cols:
            op.add_column(NEW, sa.Column(name, typ, nullable=True))
    if _is_pg():
        cols = _cols(NEW)
        for name in ("sheet_key", "item"):
            if not cols[name]["nullable"]:
                op.alter_column(NEW, name, existing_type=cols[name]["type"], nullable=True)

    # attrs 必須帶 JSON 型別，否則 psycopg 無法綁定 dict
    new_t = sa.table(NEW, sa.column("attrs", sa.JSON(none_as_null=True)), *(sa.column(c) for c in (
        "id", "module", "floor_key", "x", "y", "label", "equipment_code", "source_ref", "placement",
        "note", "sort_order", "is_active", "created_by", "updated_by", "created_at", "updated_at",
        "sheet_key", "item", "location_desc", "supply_area",
    )))

    # ── B：新舊並存 → 搬資料 ────────────────────────────────────────────────
    if has_old and has_new:
        already = bind.execute(
            sa.text(f"SELECT COUNT(*) FROM {NEW} WHERE module = :m"), {"m": MODULE}
        ).scalar() or 0
        if not already:
            old_rows = bind.execute(sa.text(
                f"SELECT floor_key, x, y, label, equipment_code, sheet_key, item, location_desc, "
                f"supply_area, note, sort_order, is_active, created_by, updated_by, created_at, updated_at "
                f"FROM {OLD}"
            )).mappings().all()
            if old_rows:
                # 新表若是 create_all 建的，module／source_ref／placement 已是 NOT NULL，搬的時候就要填好
                op.bulk_insert(new_t, [_migrated(dict(r)) for r in old_rows])

    # ── 回填 ────────────────────────────────────────────────────────────────
    rows = bind.execute(sa.text(
        f"SELECT id, module, source_ref, placement, attrs, sheet_key, item, location_desc, supply_area, note "
        f"FROM {NEW} WHERE module IS NULL OR source_ref IS NULL OR placement IS NULL"
    )).mappings().all()
    for r in rows:
        values = {}
        if r["module"] is None:
            values["module"] = MODULE
        if r["source_ref"] is None:
            values["source_ref"] = f"{r['sheet_key'] or ''}|{r['item'] or ''}"
        if r["placement"] is None:
            values["placement"] = _placement_from_note(r["note"])
        if r["attrs"] is None and (r["location_desc"] or r["supply_area"]):
            values["attrs"] = {k: v for k, v in (("機房位置", r["location_desc"]), ("供應區域", r["supply_area"])) if v}
        if values:
            bind.execute(new_t.update().where(new_t.c.id == r["id"]).values(**values))

    if _is_pg():
        cols = _cols(NEW)
        for name in ("module", "source_ref", "placement"):
            if cols[name]["nullable"]:
                op.alter_column(NEW, name, existing_type=cols[name]["type"], nullable=False)

    existing = {i["name"] for i in _insp().get_indexes(NEW)}
    if "ix_floor_map_points_module_floor" not in existing:
        op.create_index("ix_floor_map_points_module_floor", NEW, ["module", "floor_key", "is_active"])


def downgrade() -> None:
    # 只做改名回去；新增欄位保留（不可移除欄位）
    if _insp().has_table(NEW) and not _insp().has_table(OLD):
        op.rename_table(NEW, OLD)
