"""開發統計：dev_log_entries 新增 route（模組路由）

Revision ID: devlog2
Revises: devlog1
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "devlog2"
down_revision: Union[str, None] = "devlog1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("dev_log_entries")}
    if "route" not in cols:
        op.add_column("dev_log_entries", sa.Column("route", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("dev_log_entries", "route")
