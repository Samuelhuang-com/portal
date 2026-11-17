"""庫存管理 Phase 2 庫存核心 5 張表（週採資料庫，2026-11-17）

Revision ID: cpstk1
Revises: cpco4
Create Date: 2026-11-17

stock_warehouses / stock_item_settings / stock_moves / stock_balances / stock_openings，
對應 app/models/stock.py（docs/SPEC_stock_management.md §8、§11）。PostgreSQL 方言。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk1"
down_revision: Union[str, None] = "cpco4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    # 冪等：main.py 啟動時 CyclePurchaseBase.metadata.create_all 可能已先建表
    if not _has_table("stock_warehouses"):
        op.create_table(
            "stock_warehouses",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("company_code", sa.String(10), sa.ForeignKey("cycle_purchase_companies.code", ondelete="RESTRICT"), nullable=False),
            sa.Column("department_id", sa.String(30), nullable=True),
            sa.Column("department_name", sa.String(100), nullable=True),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("keeper_name", sa.String(100), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("company_code", "name", name="uq_stock_wh_company_name"),
        )
        op.create_index("ix_stock_warehouses_company_code", "stock_warehouses", ["company_code"])

    if not _has_table("stock_item_settings"):
        op.create_table(
            "stock_item_settings",
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("is_stock_item", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("purchase_unit", sa.String(20), nullable=True),
            sa.Column("unit_ratio", sa.Numeric(14, 4), nullable=False, server_default="1"),
            sa.Column("abc_class", sa.String(1), nullable=True),
            sa.Column("updated_by", sa.String(100), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table("stock_moves"):
        op.create_table(
            "stock_moves",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("unit_cost", sa.Numeric(14, 4), nullable=False),
            sa.Column("amount", sa.Numeric(16, 2), nullable=False),
            sa.Column("move_type", sa.String(20), nullable=False),
            sa.Column("source_type", sa.String(30), nullable=False),
            sa.Column("source_id", sa.String(50), nullable=True),
            sa.Column("source_no", sa.String(50), nullable=True),
            sa.Column("moved_at", sa.Date(), nullable=False),
            sa.Column("period", sa.String(7), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_stock_moves_wh_item", "stock_moves", ["warehouse_id", "item_id", "moved_at"])
        op.create_index("ix_stock_moves_company_period", "stock_moves", ["company_code", "period"])
        op.create_index("ix_stock_moves_source", "stock_moves", ["source_type", "source_id"])

    if not _has_table("stock_balances"):
        op.create_table(
            "stock_balances",
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("reserved_qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("avg_cost", sa.Numeric(14, 4), nullable=False),
            sa.Column("amount", sa.Numeric(16, 2), nullable=False),
            sa.Column("last_move_at", sa.Date(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if not _has_table("stock_openings"):
        op.create_table(
            "stock_openings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("doc_no", sa.String(30), nullable=False, unique=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("opening_date", sa.Date(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("line_count", sa.Integer(), nullable=False),
            sa.Column("total_amount", sa.Numeric(16, 2), nullable=False),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("voided_by", sa.String(100), nullable=True),
            sa.Column("voided_at", sa.DateTime(), nullable=True),
            sa.Column("void_reason", sa.Text(), nullable=True),
        )
        op.create_index("ix_stock_openings_company_code", "stock_openings", ["company_code"])


def downgrade() -> None:
    for t in ("stock_openings", "stock_balances", "stock_moves", "stock_item_settings", "stock_warehouses"):
        if _has_table(t):
            op.drop_table(t)
