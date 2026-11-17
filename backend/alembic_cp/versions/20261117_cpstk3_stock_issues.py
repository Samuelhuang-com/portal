"""庫存管理 Phase 4a 領用／退料／調撥／報廢（週採資料庫，2026-11-17）

Revision ID: cpstk3
Revises: cpstk2
Create Date: 2026-11-17

- stock_warehouses 加 issue_requires_approval（NOT NULL，server_default false）
- 新增 stock_issues / stock_issue_lines（app/models/stock.py；docs/SPEC_stock_management.md §7）
PostgreSQL 方言；可重複執行。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk3"
down_revision: Union[str, None] = "cpstk2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insp():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return _insp().has_table(name)


def _has_column(table: str, col: str) -> bool:
    return any(c["name"] == col for c in _insp().get_columns(table))


def upgrade() -> None:
    if not _has_column("stock_warehouses", "issue_requires_approval"):
        op.add_column("stock_warehouses", sa.Column("issue_requires_approval", sa.Boolean(), nullable=False,
                                                    server_default=sa.text("false")))

    if not _has_table("stock_issues"):
        op.create_table(
            "stock_issues",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("doc_no", sa.String(30), nullable=False, unique=True),
            sa.Column("doc_type", sa.String(20), nullable=False),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("to_warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("doc_date", sa.Date(), nullable=False),
            sa.Column("requester_user_id", sa.String(36), nullable=True),
            sa.Column("requester_name", sa.String(100), nullable=True),
            sa.Column("department_id", sa.String(30), nullable=True),
            sa.Column("department_name", sa.String(100), nullable=True),
            sa.Column("purpose", sa.Text(), nullable=True),
            sa.Column("cost_center_id", sa.Integer(), nullable=True),
            sa.Column("cost_center_name", sa.String(150), nullable=True),
            sa.Column("account_code", sa.String(50), nullable=True),
            sa.Column("ref_issue_id", sa.Integer(), sa.ForeignKey("stock_issues.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("line_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_amount", sa.Numeric(16, 2), nullable=False, server_default="0"),
            sa.Column("submitted_by", sa.String(100), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("approved_by", sa.String(100), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("posted_by", sa.String(100), nullable=True),
            sa.Column("posted_at", sa.DateTime(), nullable=True),
            sa.Column("posted_date", sa.Date(), nullable=True),
            sa.Column("closed_by", sa.String(100), nullable=True),
            sa.Column("closed_at", sa.DateTime(), nullable=True),
            sa.Column("close_reason", sa.Text(), nullable=True),
            sa.Column("created_by_user_id", sa.String(36), nullable=True),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_stock_issues_company_code", "stock_issues", ["company_code"])
        op.create_index("ix_stock_issues_company_type_status", "stock_issues", ["company_code", "doc_type", "status"])
        op.create_index("ix_stock_issues_wh", "stock_issues", ["warehouse_id"])
        op.create_index("ix_stock_issues_ref", "stock_issues", ["ref_issue_id"])

    if not _has_table("stock_issue_lines"):
        op.create_table(
            "stock_issue_lines",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("issue_id", sa.Integer(), sa.ForeignKey("stock_issues.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("reserved_qty", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("unit_cost", sa.Numeric(14, 4), nullable=True),
            sa.Column("amount", sa.Numeric(16, 2), nullable=True),
            sa.Column("ref_line_id", sa.Integer(), sa.ForeignKey("stock_issue_lines.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
        )
        op.create_index("ix_stock_issue_lines_issue_id", "stock_issue_lines", ["issue_id"])


def downgrade() -> None:
    if _has_table("stock_issue_lines"):
        op.drop_table("stock_issue_lines")
    if _has_table("stock_issues"):
        op.drop_table("stock_issues")
    if _has_column("stock_warehouses", "issue_requires_approval"):
        op.drop_column("stock_warehouses", "issue_requires_approval")
