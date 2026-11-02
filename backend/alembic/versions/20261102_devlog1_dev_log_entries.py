"""開發統計：dev_log_entries

Revision ID: devlog1
Revises: rrs2
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "devlog1"
down_revision: Union[str, None] = "rrs2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("dev_log_entries"):
        op.create_table(
            "dev_log_entries",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("source_key", sa.String(300), nullable=False, unique=True),
            sa.Column("entry_date", sa.Date(), nullable=False),
            sa.Column("category", sa.String(30), nullable=False, server_default=""),
            sa.Column("title", sa.String(300), nullable=False, server_default=""),
            sa.Column("module", sa.String(120), nullable=False, server_default=""),
            sa.Column("start_at", sa.DateTime(), nullable=True),
            sa.Column("end_at", sa.DateTime(), nullable=True),
            sa.Column("time_note", sa.Text(), nullable=True),
            sa.Column("updated_by", sa.String(120), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_dev_log_entry_date", "dev_log_entries", ["entry_date"])
        op.create_index("ix_dev_log_module", "dev_log_entries", ["module"])


def downgrade() -> None:
    op.drop_index("ix_dev_log_module", table_name="dev_log_entries")
    op.drop_index("ix_dev_log_entry_date", table_name="dev_log_entries")
    op.drop_table("dev_log_entries")
