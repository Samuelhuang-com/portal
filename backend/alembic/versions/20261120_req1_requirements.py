"""requirements 需求表＋dev_log_entries.requirement_id（2026-11-20，開發統計需求管理）

Revision ID: req1
Revises: stk2
Create Date: 2026-11-20

需求與變更一對一：dev_log_entries.requirement_id 指向 requirements.id（可空）。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "req1"
down_revision: Union[str, None] = "stk2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, col: str) -> bool:
    return any(c["name"] == col for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if "requirements" not in inspect(op.get_bind()).get_table_names():
        op.create_table(
            "requirements",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(300), nullable=False, server_default=""),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("requester", sa.String(120), nullable=True),
            sa.Column("module", sa.String(120), nullable=False, server_default=""),
            sa.Column("status", sa.String(20), nullable=False, server_default="待評估"),
            sa.Column("priority", sa.String(10), nullable=False, server_default="中"),
            sa.Column("jira_key", sa.String(60), nullable=True, unique=True),
            sa.Column("created_by", sa.String(120), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_by", sa.String(120), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_requirements_status", "requirements", ["status"])
    if not _has_column("dev_log_entries", "requirement_id"):
        op.add_column("dev_log_entries", sa.Column("requirement_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_dev_log_entries_requirement_id", "dev_log_entries", "requirements",
                              ["requirement_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_dev_log_entries_requirement_id", "dev_log_entries", ["requirement_id"])


def downgrade() -> None:
    if _has_column("dev_log_entries", "requirement_id"):
        op.drop_index("ix_dev_log_entries_requirement_id", table_name="dev_log_entries")
        op.drop_constraint("fk_dev_log_entries_requirement_id", "dev_log_entries", type_="foreignkey")
        op.drop_column("dev_log_entries", "requirement_id")
    if "requirements" in inspect(op.get_bind()).get_table_names():
        op.drop_index("ix_requirements_status", table_name="requirements")
        op.drop_table("requirements")
