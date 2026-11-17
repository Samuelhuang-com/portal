"""庫存管理 Phase 5 盤點、月結（週採資料庫，2026-11-17）

Revision ID: cpstk6
Revises: cpstk5
Create Date: 2026-11-17

- stock_warehouses 加 count_blind（NOT NULL，server_default true；D8 盲盤）
- 新增 stock_counts / stock_count_lines / stock_periods（app/models/stock.py；docs/SPEC_stock_management.md §8.6、§9）
PostgreSQL 方言；可重複執行。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk6"
down_revision: Union[str, None] = "cpstk5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insp():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _insp().has_table(name)


def _has_column(table: str, col: str) -> bool:
    return any(c["name"] == col for c in _insp().get_columns(table))


def upgrade() -> None:
    if not _has_column("stock_warehouses", "count_blind"):
        op.add_column("stock_warehouses", sa.Column("count_blind", sa.Boolean(), nullable=False, server_default=sa.text("true")))

    if not _has_table("stock_counts"):
        op.create_table(
            "stock_counts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("count_no", sa.String(30), nullable=False, unique=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("period", sa.String(7), nullable=False),
            sa.Column("count_date", sa.Date(), nullable=False),
            sa.Column("cutoff_at", sa.DateTime(), nullable=False),
            sa.Column("blind", sa.Boolean(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="counting"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("line_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("diff_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("gain_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
            sa.Column("loss_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("submitted_by", sa.String(100), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("approved_by", sa.String(100), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("closed_by", sa.String(100), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("close_reason", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_stock_counts_company_code", "stock_counts", ["company_code"])
        op.create_index("ix_stock_counts_company_period", "stock_counts", ["company_code", "period"])
        op.create_index("ix_stock_counts_wh_status", "stock_counts", ["warehouse_id", "status"])

    if not _has_table("stock_count_lines"):
        op.create_table(
            "stock_count_lines",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("count_id", sa.Integer(), sa.ForeignKey("stock_counts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("book_qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("book_avg_cost", sa.Numeric(14, 4), nullable=False),
            sa.Column("counted_qty", sa.Numeric(14, 4), nullable=True),
            sa.Column("counted_by", sa.String(100), nullable=True),
            sa.Column("counted_at", sa.DateTime(), nullable=True),
            sa.Column("added_manually", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("unit_cost", sa.Numeric(14, 4), nullable=True),
            sa.Column("adj_qty", sa.Numeric(14, 4), nullable=True),
            sa.Column("adj_amount", sa.Numeric(16, 2), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.UniqueConstraint("count_id", "item_id", name="uq_stock_count_line_item"),
        )
        op.create_index("ix_stock_count_lines_count_id", "stock_count_lines", ["count_id"])

    if not _has_table("stock_periods"):
        op.create_table(
            "stock_periods",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("period", sa.String(7), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("closed_by", sa.String(100), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("revalue_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("revalue_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
            sa.Column("reopen_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reopened_by", sa.String(100), nullable=True),
            sa.Column("reopened_at", sa.DateTime(), nullable=True),
            sa.Column("reopen_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("company_code", "period", name="uq_stock_period_company"),
        )


def downgrade() -> None:
    for t in ("stock_count_lines", "stock_counts", "stock_periods"):
        if _has_table(t):
            op.drop_table(t)
    if _has_column("stock_warehouses", "count_blind"):
        op.drop_column("stock_warehouses", "count_blind")
