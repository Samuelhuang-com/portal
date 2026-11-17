"""庫存管理 Phase 4b 領用範本（週採資料庫，2026-11-17）

Revision ID: cpstk5
Revises: cpstk4
Create Date: 2026-11-17

新增 stock_issue_templates / stock_issue_template_lines（app/models/stock.py；docs/SPEC_stock_management.md §7）。
PostgreSQL 方言；可重複執行（表已存在就跳過）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk5"
down_revision: Union[str, None] = "cpstk4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("stock_issue_templates"):
        op.create_table(
            "stock_issue_templates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_by_user_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_by", sa.String(100), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("warehouse_id", "name", name="uq_stock_issue_tpl_wh_name"),
        )
        op.create_index("ix_stock_issue_templates_company_code", "stock_issue_templates", ["company_code"])
    if not _has_table("stock_issue_template_lines"):
        op.create_table(
            "stock_issue_template_lines",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("template_id", sa.Integer(), sa.ForeignKey("stock_issue_templates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_stock_issue_template_lines_template_id", "stock_issue_template_lines", ["template_id"])


def downgrade() -> None:
    if _has_table("stock_issue_template_lines"):
        op.drop_table("stock_issue_template_lines")
    if _has_table("stock_issue_templates"):
        op.drop_table("stock_issue_templates")
