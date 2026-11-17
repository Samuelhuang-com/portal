"""Ragic 採購單兩張表（庫存管理 Phase 1，2026-11-17）

Revision ID: stk1
Revises: rs1
Create Date: 2026-11-17

新增 ragic_purchase_orders / ragic_purchase_order_items，
對應 app/models/ragic_purchase_order.py（docs/SPEC_stock_management.md §11）。PostgreSQL 方言。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "stk1"
down_revision: Union[str, None] = "rs1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    # 冪等：main.py／sync_tool 的 create_all 可能已先建表，已存在就跳過（避免 DuplicateTable）
    if not _has_table("ragic_purchase_orders"):
        op.create_table(
            "ragic_purchase_orders",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("company", sa.String(20), nullable=False, server_default=""),
            sa.Column("sheet_module", sa.String(50), nullable=False, server_default=""),
            sa.Column("department_display", sa.String(50), nullable=False, server_default=""),
            sa.Column("department_raw", sa.String(50), nullable=True),
            sa.Column("ragic_sheet_path", sa.String(100), nullable=False, server_default=""),
            sa.Column("ragic_record_id", sa.String(30), nullable=False, server_default=""),
            sa.Column("po_no", sa.String(50), nullable=False, server_default=""),
            sa.Column("source_pr_no", sa.String(50), nullable=True),
            sa.Column("requester", sa.String(50), nullable=True),
            sa.Column("apply_date", sa.Date(), nullable=True),
            sa.Column("arrival_date", sa.Date(), nullable=True),
            sa.Column("purpose", sa.Text(), nullable=True),
            sa.Column("vendor_name", sa.String(200), nullable=True),
            sa.Column("vendor_code", sa.String(50), nullable=True),
            sa.Column("subtotal", sa.Numeric(14, 2), nullable=True),
            sa.Column("tax", sa.Numeric(14, 2), nullable=True),
            sa.Column("total", sa.Numeric(14, 2), nullable=True),
            sa.Column("payment_terms", sa.String(200), nullable=True),
            sa.Column("receiver", sa.String(100), nullable=True),
            sa.Column("is_ragic_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("source_hash", sa.String(64), nullable=False, server_default=""),
            sa.Column("ragic_data_ts", sa.BigInteger(), nullable=True),
            sa.Column("raw_data_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("sync_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("ragic_sheet_path", "ragic_record_id", name="uq_rpo_sheet_record"),
        )
        op.create_index("ix_rpo_company_dept", "ragic_purchase_orders", ["company", "department_display"])
        op.create_index("ix_rpo_po_no", "ragic_purchase_orders", ["po_no"])

    if not _has_table("ragic_purchase_order_items"):
        op.create_table(
            "ragic_purchase_order_items",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("order_id", sa.Integer(), nullable=False),
            sa.Column("ragic_row_id", sa.String(30), nullable=False, server_default=""),
            sa.Column("seq", sa.Integer(), nullable=True),
            sa.Column("item_code", sa.String(50), nullable=True),
            sa.Column("product_name", sa.Text(), nullable=True),
            sa.Column("qty", sa.Numeric(14, 4), nullable=True),
            sa.Column("qty_raw", sa.String(50), nullable=True),
            sa.Column("unit", sa.String(50), nullable=True),
            sa.Column("remark", sa.Text(), nullable=True),
            sa.Column("unit_price", sa.Numeric(14, 4), nullable=True),
            sa.Column("amount", sa.Numeric(14, 2), nullable=True),
            sa.Column("item_dept", sa.String(50), nullable=True),
            sa.Column("sync_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("order_id", "ragic_row_id", name="uq_rpoi_order_row"),
        )
        op.create_index("ix_rpoi_order_id", "ragic_purchase_order_items", ["order_id"])


def downgrade() -> None:
    if _has_table("ragic_purchase_order_items"):
        op.drop_table("ragic_purchase_order_items")
    if _has_table("ragic_purchase_orders"):
        op.drop_table("ragic_purchase_orders")
