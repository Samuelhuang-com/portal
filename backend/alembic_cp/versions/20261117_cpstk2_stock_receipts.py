"""庫存管理 Phase 3 進貨匯入 4 張表（週採資料庫，2026-11-17）

Revision ID: cpstk2
Revises: cpstk1
Create Date: 2026-11-17

stock_import_lines / stock_receipts / stock_receipt_items / stock_item_aliases，
對應 app/models/stock.py（docs/SPEC_stock_management.md §6）。PostgreSQL 方言。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk2"
down_revision: Union[str, None] = "cpstk1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("stock_import_lines"):
        op.create_table(
            "stock_import_lines",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("source_type", sa.String(20), nullable=False),
            sa.Column("source_db_id", sa.Integer(), nullable=True),
            sa.Column("ragic_sheet_path", sa.String(100), nullable=False),
            sa.Column("ragic_record_id", sa.String(30), nullable=False),
            sa.Column("ragic_row_id", sa.String(30), nullable=False),
            sa.Column("doc_no", sa.String(50), nullable=True),
            sa.Column("po_no", sa.String(50), nullable=True),
            sa.Column("suspected_po_no", sa.String(50), nullable=True),
            sa.Column("department", sa.String(50), nullable=True),
            sa.Column("doc_date", sa.Date(), nullable=True),
            sa.Column("vendor_name", sa.String(200), nullable=True),
            sa.Column("item_code", sa.String(50), nullable=True),
            sa.Column("product_name", sa.Text(), nullable=True),
            sa.Column("qty", sa.Numeric(14, 4), nullable=True),
            sa.Column("qty_raw", sa.String(50), nullable=True),
            sa.Column("unit", sa.String(50), nullable=True),
            sa.Column("unit_price", sa.Numeric(14, 4), nullable=True),
            sa.Column("amount", sa.Numeric(16, 2), nullable=True),
            sa.Column("imported_qty", sa.Numeric(14, 4), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
            sa.Column("status_reason", sa.Text(), nullable=True),
            sa.Column("marked_by", sa.String(100), nullable=True),
            sa.Column("source_hash", sa.String(64), nullable=False, server_default=""),
            sa.Column("source_changed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("source_status", sa.String(20), nullable=False, server_default="ok"),
            sa.Column("refreshed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("source_type", "ragic_sheet_path", "ragic_record_id", "ragic_row_id",
                                name="uq_stock_import_line_src"),
        )
        op.create_index("ix_stock_import_lines_company_code", "stock_import_lines", ["company_code"])
        op.create_index("ix_stock_import_company_status", "stock_import_lines", ["company_code", "status"])
        op.create_index("ix_stock_import_po_no", "stock_import_lines", ["company_code", "po_no"])

    if not _has_table("stock_receipts"):
        op.create_table(
            "stock_receipts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("receipt_no", sa.String(30), nullable=False, unique=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("stock_warehouses.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("receipt_date", sa.Date(), nullable=False),
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
        op.create_index("ix_stock_receipts_company_code", "stock_receipts", ["company_code"])

    if not _has_table("stock_receipt_items"):
        op.create_table(
            "stock_receipt_items",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("stock_receipts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("import_line_id", sa.Integer(), sa.ForeignKey("stock_import_lines.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("purchase_qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("purchase_unit", sa.String(50), nullable=True),
            sa.Column("unit_ratio", sa.Numeric(14, 4), nullable=False),
            sa.Column("stock_qty", sa.Numeric(14, 4), nullable=False),
            sa.Column("unit_cost", sa.Numeric(14, 4), nullable=False),
            sa.Column("amount", sa.Numeric(16, 2), nullable=False),
            sa.Column("is_estimated_cost", sa.Boolean(), nullable=False),
            sa.Column("override_reason", sa.Text(), nullable=True),
        )
        op.create_index("ix_stock_receipt_items_receipt_id", "stock_receipt_items", ["receipt_id"])
        op.create_index("ix_stock_receipt_items_import_line_id", "stock_receipt_items", ["import_line_id"])

    if not _has_table("stock_item_aliases"):
        op.create_table(
            "stock_item_aliases",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("company_code", sa.String(10), nullable=False),
            sa.Column("normalized_name", sa.String(300), nullable=False),
            sa.Column("raw_name", sa.Text(), nullable=True),
            sa.Column("item_id", sa.Integer(), sa.ForeignKey("cycle_purchase_items.id", ondelete="CASCADE"), nullable=True),
            sa.Column("is_non_stock", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("confirmed_by", sa.String(100), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("company_code", "normalized_name", name="uq_stock_alias_company_name"),
        )


def downgrade() -> None:
    for t in ("stock_item_aliases", "stock_receipt_items", "stock_receipts", "stock_import_lines"):
        if _has_table(t):
            op.drop_table(t)
