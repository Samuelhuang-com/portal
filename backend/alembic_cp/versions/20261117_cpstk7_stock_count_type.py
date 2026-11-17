"""庫存管理 Phase 7 循環盤點：盤點表加「盤點類型」（週採資料庫，2026-11-17）

Revision ID: cpstk7
Revises: cpstk6
Create Date: 2026-11-17

stock_counts 加 count_type（NOT NULL，server_default 'full'）、abc_classes（nullable）。
循環盤點（只盤指定 ABC 類）屬於額外抽盤，月結仍要求月底全盤（count_type='full'）。可重複執行。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk7"
down_revision: Union[str, None] = "cpstk6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, col: str) -> bool:
    insp = inspect(op.get_bind())
    return insp.has_table(table) and any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    if not _has_column("stock_counts", "count_type"):
        op.add_column("stock_counts", sa.Column("count_type", sa.String(20), nullable=False, server_default="full"))
    if not _has_column("stock_counts", "abc_classes"):
        op.add_column("stock_counts", sa.Column("abc_classes", sa.String(10), nullable=True))


def downgrade() -> None:
    if _has_column("stock_counts", "abc_classes"):
        op.drop_column("stock_counts", "abc_classes")
    if _has_column("stock_counts", "count_type"):
        op.drop_column("stock_counts", "count_type")
