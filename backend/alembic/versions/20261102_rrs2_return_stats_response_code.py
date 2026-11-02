"""退件統計：return_stats_step 新增 response_code（Ragic 簽核步驟代碼）

Revision ID: rrs2
Revises: rrs1
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "rrs2"
down_revision: Union[str, None] = "rrs1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("return_stats_step")}
    if "response_code" not in cols:
        op.add_column("return_stats_step", sa.Column("response_code", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("return_stats_step", "response_code")
