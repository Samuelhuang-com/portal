"""庫存：領用／雜收單關聯商場工務報修（週採資料庫，2026-11-20）

Revision ID: cpstk8
Revises: cpstk7
Create Date: 2026-11-20

新增 stock_issue_repair_links（單據 ↔ 報修案件，軟關聯）。可重複執行。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "cpstk8"
down_revision: Union[str, None] = "cpstk7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("stock_issue_repair_links"):
        op.create_table(
            "stock_issue_repair_links",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("issue_id", sa.Integer(), sa.ForeignKey("stock_issues.id", ondelete="CASCADE"), nullable=False),
            sa.Column("repair_ragic_id", sa.String(50), nullable=False),
            sa.Column("repair_case_no", sa.String(100), nullable=True),
            sa.Column("repair_title", sa.Text(), nullable=True),
            sa.Column("repair_occurred", sa.Date(), nullable=True),
            sa.Column("created_by", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("issue_id", "repair_ragic_id", name="uq_stock_issue_repair"),
        )
        op.create_index("ix_stock_issue_repair_links_issue_id", "stock_issue_repair_links", ["issue_id"])
        op.create_index("ix_stock_issue_repair_links_repair_ragic_id", "stock_issue_repair_links", ["repair_ragic_id"])


def downgrade() -> None:
    if _has_table("stock_issue_repair_links"):
        op.drop_table("stock_issue_repair_links")
