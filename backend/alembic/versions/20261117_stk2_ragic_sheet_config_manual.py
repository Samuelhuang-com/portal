"""ragic_sheet_config.manual_override（2026-11-17，系統設定 › Ragic 表單關聯可編輯）

Revision ID: stk2
Revises: stk1
Create Date: 2026-11-17

手動修改或新增的表單設定標 manual_override=True，啟動 seed 不再把路徑改回預設值。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "stk2"
down_revision: Union[str, None] = "stk1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, col: str) -> bool:
    return any(c["name"] == col for c in inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_column("ragic_sheet_config", "manual_override"):
        op.add_column(
            "ragic_sheet_config",
            sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    if _has_column("ragic_sheet_config", "manual_override"):
        op.drop_column("ragic_sheet_config", "manual_override")
