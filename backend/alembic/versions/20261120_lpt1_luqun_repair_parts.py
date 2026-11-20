"""商場工務報修：工務零件／專櫃零件子表＋父層零件合計欄位（2026-11-20）

Revision ID: lpt1
Revises: req1
Create Date: 2026-11-20

新增 luqun_repair_site_part、luqun_repair_counter_part 兩張表；
luqun_repair_case 新增 site_parts_fee、counter_parts_fee、counter_sign、counter_est_hours。
對應 app/models/luqun_repair.py。PostgreSQL 方言，冪等（已存在就跳過）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "lpt1"
down_revision: Union[str, None] = "req1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables():
    return inspect(op.get_bind()).get_table_names()


def _has_column(table: str, col: str) -> bool:
    return any(c["name"] == col for c in inspect(op.get_bind()).get_columns(table))


def _part_table(name: str, with_counter_cols: bool) -> None:
    if name in _tables():
        return
    cols = [
        sa.Column("ragic_id", sa.String(50), primary_key=True),
        sa.Column("parent_ragic_id", sa.String(50), nullable=False, server_default=""),
        sa.Column("seq", sa.String(20), nullable=False, server_default=""),
        sa.Column("part_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("part_no", sa.String(100), nullable=False, server_default=""),
        sa.Column("qty", sa.String(50), nullable=False, server_default=""),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0"),
    ]
    if with_counter_cols:
        cols += [
            sa.Column("issue_date", sa.Date(), nullable=True),
            sa.Column("subtotal", sa.Float(), nullable=False, server_default="0"),
        ]
    cols.append(sa.Column("synced_at", sa.DateTime(), nullable=True))
    op.create_table(name, *cols)
    op.create_index(f"ix_{name}_parent_ragic_id", name, ["parent_ragic_id"])


def upgrade() -> None:
    _part_table("luqun_repair_site_part", with_counter_cols=False)
    _part_table("luqun_repair_counter_part", with_counter_cols=True)

    if not _has_column("luqun_repair_case", "site_parts_fee"):
        op.add_column("luqun_repair_case", sa.Column("site_parts_fee", sa.Float(), nullable=False, server_default="0"))
    if not _has_column("luqun_repair_case", "counter_parts_fee"):
        op.add_column("luqun_repair_case", sa.Column("counter_parts_fee", sa.Float(), nullable=False, server_default="0"))
    if not _has_column("luqun_repair_case", "counter_sign"):
        op.add_column("luqun_repair_case", sa.Column("counter_sign", sa.String(100), nullable=False, server_default=""))
    if not _has_column("luqun_repair_case", "counter_est_hours"):
        op.add_column("luqun_repair_case", sa.Column("counter_est_hours", sa.String(50), nullable=False, server_default=""))


def downgrade() -> None:
    for col in ("counter_est_hours", "counter_sign", "counter_parts_fee", "site_parts_fee"):
        if _has_column("luqun_repair_case", col):
            op.drop_column("luqun_repair_case", col)
    for name in ("luqun_repair_counter_part", "luqun_repair_site_part"):
        if name in _tables():
            op.drop_table(name)
